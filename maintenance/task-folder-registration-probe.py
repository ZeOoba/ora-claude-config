#!/usr/bin/env python3
"""ORA task-folder-registration probe -- catches SKILL.md folders that were
never wired into a live scheduler registry, and registry entries that point
at a SKILL.md that no longer exists.

WHY: registry-membership-probe.py alarms on a task DROPPING OUT of the
registry between two runs (a temporal diff against its own prior snapshot).
It cannot see a task that was NEVER in any snapshot -- a SKILL.md folder
authored on disk but whose create_scheduled_task call never happened (or
silently failed) sits invisible forever, since there is nothing in the
registry's history to diff against.

Confirmed case: ora-calibration-snapshot. SKILL.md authored 2026-06-22
(Notion registration spec written 2026-06-14), but never actually registered
via create_scheduled_task until 2026-07-11 -- 10 days after its 2026-07-01
quarterly due date. The quarterly cron correctly skipped straight to
2026-10-01 once registered; nothing ever fired for the missed window, and no
guard alarmed because the folder had no registry history to drop out of.
This probe reconciles CURRENT folder inventory against CURRENT registry
membership directly, independent of history, closing that gap.

Three checks, each fleet (cc/lams):
  UNREGISTERED          -- SKILL.md folder on disk, not self-declared
                           one-time/one-off, absent from the live registry.
  ORPHANED_REGISTRATION -- enabled registry entry whose filePath does not
                           exist on disk (would error at next fire).
  ARCHIVED_BUT_REGISTERED -- enabled registry entry whose filePath resolves
                           under an "_archive_*" directory segment (added
                           2026-08-14, closing a confirmed blind spot:
                           ora-cam-reconciliation-annual sat archived-but-
                           registered for ~2 months, 06-11 to 08-14, with
                           zero ORPHANED_REGISTRATION alarms in that window
                           -- the archived folder's SKILL.md still exists at
                           its new path, so the plain file-existence check
                           above can never catch this class on its own).

One-time/fired tasks (e.g. a diagnostic that auto-disables after firing) are
excluded from UNREGISTERED via a content heuristic -- they legitimately end
up folder-only, and registry-membership-probe.py already ignores them by
design ("One-time fireAt tasks are ignored -- they expire by design").

Exit 0 = clean. Exit 1 = [ACTION] gap detected in either fleet.
Run daily alongside registry-membership-probe.py (ora-task-integrity-guard).
"""
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "_shared"))
try:
    import store_discovery as _sd
except Exception:
    _sd = None  # fail-open: both discovery calls below return None

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

STATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_state")
LOG = os.path.join(STATE_DIR, "task-folder-registration.log")

ONE_TIME_MARKERS = ("one-time", "one-off")


def list_skill_folders(root):
    """{task_id: skill_md_path} for immediate subdirs of `root` that contain
    a SKILL.md file (archive/shared/state dirs never have one directly
    inside them, so no separate name-prefix filtering is needed). None if
    `root` itself is missing/unreadable; {} if it exists but has no task
    folders."""
    try:
        entries = os.listdir(root)
    except Exception:
        return None
    out = {}
    for name in entries:
        candidate = os.path.join(root, name, "SKILL.md")
        if os.path.isfile(candidate):
            out[name] = candidate
    return out


def is_one_time(skill_md_text):
    """True if the SKILL.md content self-declares as a one-time/one-off
    task. Simple case-insensitive substring heuristic -- deliberately loose
    (false negatives just mean a one-time task gets reconciled normally,
    which is harmless; the registry check below still won't flag it once
    it's fired and removed, since removal-without-a-folder isn't checked
    here). Pure."""
    if not skill_md_text:
        return False
    lowered = skill_md_text.lower()
    return any(marker in lowered for marker in ONE_TIME_MARKERS)


def read_registry_entries(path):
    """[{'id','filePath','enabled','cronExpression'}] from a
    scheduled-tasks.json, or None if unreadable."""
    try:
        d = json.load(open(path, encoding="utf-8"))
    except Exception:
        return None
    out = []
    for t in d.get("scheduledTasks", []) or []:
        out.append({
            "id": t.get("id") or "?",
            "filePath": t.get("filePath"),
            "enabled": bool(t.get("enabled")),
            "cronExpression": t.get("cronExpression"),
        })
    return out


def find_unregistered(folder_texts, registered_ids):
    """folder_texts: {id: skill_md_text}. registered_ids: set of ids present
    in ANY state in the live registry. Sorted ids on disk, absent from the
    registry, and not self-declared one-time. Pure."""
    return sorted(
        i for i, text in folder_texts.items()
        if i not in registered_ids and not is_one_time(text)
    )


def find_orphaned_registrations(entries, exists_fn=os.path.isfile):
    """entries: [{'id','filePath','enabled',...}]. Sorted ids of ENABLED
    entries whose filePath does not exist -- a dangling registration that
    will error at next fire. A disabled entry with a missing file is not
    actively dangerous (won't fire) so it's not flagged here. exists_fn
    injectable for tests."""
    return sorted(
        e["id"] for e in entries
        if e.get("enabled") and not exists_fn(e.get("filePath") or "")
    )


ARCHIVE_MARKER_PREFIX = "_archive"


def find_archived_registrations(entries):
    """entries: [{'id','filePath','enabled',...}]. Sorted ids of ENABLED
    entries whose filePath resolves under a directory segment starting with
    '_archive' -- a registered-but-archived task (folder moved to cold
    storage, registry entry never retired). Deliberately does NOT check
    file existence: an archived folder's SKILL.md still exists at its NEW
    path, so find_orphaned_registrations's os.path.isfile check cannot see
    this case at all -- confirmed blind spot, ora-cam-reconciliation-annual
    sat archived-but-registered for ~2 months (2026-06-11 to 2026-08-14)
    with zero ORPHANED_REGISTRATION alarms across every daily run in that
    window (see task-folder-registration.log). Mirrors the orphaned-check's
    own convention of only flagging ENABLED entries -- a disabled archived
    entry won't fire, so it's not actively dangerous. Pure."""
    out = []
    for e in entries:
        if not e.get("enabled"):
            continue
        fp = (e.get("filePath") or "").replace("\\", "/")
        if any(part.startswith(ARCHIVE_MARKER_PREFIX) for part in fp.split("/")):
            out.append(e["id"])
    return sorted(out)


def _git_differs_from_upstream(path, run=None):
    """True if `path` on disk differs from the branch's UPSTREAM ref.

    Returns None for "no verdict" -- not a git repo, path untracked, no
    upstream configured, git missing, or any git failure. None is never a
    finding, matching this probe's fail-open posture throughout.

    Two decisions here are load-bearing, both learned from a live false-alarm
    run (2026-08-16, 21 of ~32 CC tasks flagged by a first cut):

    1. UPSTREAM, not HEAD. The failure this check exists to catch is a task
       merged to origin while the checkout the scheduler reads sits BEHIND it
       -- in the confirmed ora-passed-deal-tracker case the on-disk file
       matched local HEAD (588ec1b) exactly, and only differed from origin.
       Comparing against HEAD calls that clean and misses the entire bug.
    2. `git diff`, not a byte compare against `git show`. This repo runs
       core.autocrlf=true, so a blob's LF bytes never equal the working
       tree's CRLF bytes and a raw comparison flags nearly every file. Asking
       git to diff applies the same clean/smudge filters git itself uses, so
       line endings and any future filter are handled by definition.

    Injectable `run` for tests."""
    import subprocess
    run = run or subprocess.run
    d = os.path.dirname(path) or "."
    try:
        top = run(["git", "-C", d, "rev-parse", "--show-toplevel"],
                  capture_output=True, timeout=15)
        if top.returncode != 0:
            return None
        root = top.stdout.decode("utf-8", "replace").strip()
        if not root:
            return None
        up = run(["git", "-C", root, "rev-parse", "--abbrev-ref", "@{upstream}"],
                 capture_output=True, timeout=15)
        if up.returncode != 0:
            return None          # no upstream -- nothing to be behind
        ref = up.stdout.decode("utf-8", "replace").strip()
        if not ref:
            return None
        r = run(["git", "-C", root, "diff", "--quiet", ref, "--", path],
                capture_output=True, timeout=30)
        if r.returncode == 0:
            return False         # identical to upstream
        if r.returncode == 1:
            return True          # differs
        return None              # 128 etc (untracked, bad ref) -- no verdict
    except Exception:
        return None              # fail-open, same posture as the whole probe


def find_stale_vs_git(entries, differs=None):
    """entries: [{'id','filePath','enabled',...}]. Sorted ids of ENABLED
    entries whose on-disk SKILL.md differs from its branch's UPSTREAM ref.

    WHY (OI-170, 2026-08-16): the scheduler resolves filePath against the LIVE
    WORKING TREE, not git. So a SKILL.md can be authored, reviewed, merged via
    PR and present on origin while the checkout the scheduler actually reads
    still holds the old bytes -- merged and inert, with nothing detecting it.
    Confirmed live: ora-passed-deal-tracker's two-layer double-fire guard
    merged as b734674 (PR #116 / c16667c) while the primary checkout sat at
    588ec1b, so the live file had ZERO hits for its own guard tokens. Every
    git-side check said the guard had shipped; it would have stayed inert
    through the 2026-09-15 06:30 ET dual-fleet fire had a human not looked.

    The three existing checks structurally cannot catch this. UNREGISTERED,
    ORPHANED_REGISTRATION and ARCHIVED_BUT_REGISTERED all reason about whether
    the filePath EXISTS (or where it lives); a merged-but-not-checked-out
    SKILL.md exists at exactly the right path with the wrong contents, which
    is clean by all three.

    Catches, symmetrically: merged-but-not-pulled (the OI-170 case), a local
    edit never committed/pushed, and reverted-in-tree.

    Unanswerable cases yield NO finding (see _git_differs_from_upstream): a
    task folder outside any git repo -- which is exactly the LAMS/Cowork
    fleet's normal configuration, its SKILL.mds living under OneDrive -- is a
    legitimate setup, not drift. Only ENABLED entries, matching both sibling
    checks' convention. Pure given its injectable."""
    differs = differs or _git_differs_from_upstream
    out = []
    for e in entries:
        if not e.get("enabled"):
            continue
        fp = e.get("filePath") or ""
        if not fp:
            continue
        if differs(fp) is True:   # None (no verdict) and False are both clean
            out.append(e["id"])
    return sorted(out)


def _read_text(path):
    try:
        return open(path, encoding="utf-8", errors="replace").read()
    except Exception:
        return ""


def main():
    if _sd is None:
        print("  WARN store_discovery unavailable -- probe cannot run.")
        return 0  # fail-open: a broken shared helper must never false-alarm

    bad = False
    lines = []
    for label in ("cc", "lams"):
        folder_root = _sd.skill_folder_root(label)
        registry_path = _sd.discover_store(_sd.store_name(label))

        folders = list_skill_folders(folder_root) if folder_root else None
        entries = read_registry_entries(registry_path) if registry_path else None

        print(f"{label}: folder_root={folder_root or '(unconfigured)'} "
              f"registry={registry_path or '(not found)'}")

        if folders is None:
            print(f"  WARN {label} skill-folder root not found -- skipping folder check.")
            lines.append(f"{label}: root_missing")
            continue
        if entries is None:
            print(f"  WARN {label} registry not found/unreadable -- skipping both checks.")
            lines.append(f"{label}: registry_missing")
            continue

        registered_ids = {e["id"] for e in entries}
        folder_texts = {i: _read_text(p) for i, p in folders.items()}

        unregistered = find_unregistered(folder_texts, registered_ids)
        orphaned = find_orphaned_registrations(entries)
        archived = find_archived_registrations(entries)
        stale = find_stale_vs_git(entries)

        lines.append(f"{label}: folders={len(folders)} registry_entries={len(entries)} "
                     f"unregistered={unregistered or '-'} orphaned={orphaned or '-'} "
                     f"archived={archived or '-'} stale_vs_git={stale or '-'}")

        if unregistered:
            print(f"  [ACTION] UNREGISTERED in {label}: {', '.join(unregistered)} -- "
                  "SKILL.md exists on disk but was never wired into the live registry "
                  "via create_scheduled_task. It will silently never fire until "
                  "registered. (ora-calibration-snapshot failure mode.)")
            bad = True
        if orphaned:
            print(f"  [ACTION] ORPHANED_REGISTRATION in {label}: {', '.join(orphaned)} -- "
                  "enabled registry entry points at a SKILL.md that no longer exists on "
                  "disk. Will error at next fire; retire the entry or restore the file.")
            bad = True
        if archived:
            print(f"  [ACTION] ARCHIVED_BUT_REGISTERED in {label}: {', '.join(archived)} -- "
                  "enabled registry entry's filePath resolves under an _archive_* directory. "
                  "The folder move never deregistered it, so it keeps firing/counting as "
                  "live. Retire the registry entry (or restore the folder to its live path "
                  "if the archive was a mistake). (ora-cam-reconciliation-annual failure mode.)")
            bad = True
        if stale:
            print(f"  [ACTION] STALE_VS_GIT in {label}: {', '.join(stale)} -- "
                  "the SKILL.md on disk differs from the blob committed at HEAD. The "
                  "scheduler reads the WORKING TREE, not git, so a task can be merged "
                  "and still inert: pull the branch into this checkout, or commit the "
                  "local edit. (ora-passed-deal-tracker double-fire-guard failure mode: "
                  "merged as b734674 while the live file had zero hits for its own "
                  "guard tokens.)")
            bad = True
        if not unregistered and not orphaned and not archived and not stale:
            print(f"  OK -- {label} folders and registry reconcile cleanly.")

    ts = datetime.datetime.now().isoformat(timespec="seconds")
    os.makedirs(STATE_DIR, exist_ok=True)
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(f"{ts} " + " | ".join(lines) + "\n")
    except Exception:
        pass

    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
