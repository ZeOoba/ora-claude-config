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


# _git_path_state verdicts. Only the first two are findings.
STATE_UNCOMMITTED = "uncommitted"   # worktree differs from HEAD: content in NO commit
STATE_BEHIND = "behind"             # upstream advanced this path; we lack it
STATE_CLEAN = "clean"               # identical to HEAD, and not behind (may be AHEAD)


def _git_path_state(path, run=None):
    """Classify `path` as STATE_UNCOMMITTED / STATE_BEHIND / STATE_CLEAN, or
    None for "no verdict".

    None covers not-a-git-repo, no upstream, untracked, git missing, or any
    git failure, and is never a finding -- this probe's fail-open posture.

    THREE decisions here are load-bearing, each learned from a live run, not
    from reasoning about the code:

    1. UPSTREAM, not HEAD, for the behind test. The failure this exists to
       catch is a task merged to origin while the checkout the scheduler reads
       sits BEHIND -- in the confirmed ora-passed-deal-tracker case the
       on-disk file matched local HEAD (588ec1b) exactly and differed only
       from origin. A HEAD-only comparison calls that clean and misses the
       whole bug.
    2. `git diff`, never a byte compare against `git show`. core.autocrlf=true
       here, so a blob's LF never equals the worktree's CRLF; a raw comparison
       flagged 21 of ~32 CC tasks. Delegating to git applies git's own
       clean/smudge filters, so line endings and any future filter are handled
       by definition.
    3. DIRECTION (OI-182, added after the first live run of the shipped
       check). Comparing worktree-vs-upstream and flagging ANY difference is
       direction-blind: it cannot tell BEHIND (merged but not pulled -- the
       real bug) from AHEAD (committed locally, not yet pushed), and AHEAD is
       this checkout's normal resting state; it sat at ahead-24 the day this
       was written. The first live run produced 5 findings of which 2 were
       merely ahead. Those two are not false in the literal sense -- the file
       does differ from upstream, and unpushed does mean unbacked-up -- but
       folding them in with real drift is how a check earns the alarm fatigue
       that killed this same check's first cut. Direction is resolved against
       the MERGE-BASE: upstream is only "ahead of us" for a path if the
       upstream side changed it since the common ancestor.
    4. Same-day follow-up (independent review): DIVERGED-but-identical.
       base..upstream alone answers "did the PATH'S HISTORY diverge", not
       "does the CONTENT actually differ" -- confirmed live, upstream commits
       a fix and this checkout independently commits the byte-identical fix
       in its own unrelated commit, and base..upstream is non-empty even
       though nothing is actually missing. A worktree-vs-upstream CONTENT
       check settles it regardless of how the history got there.
    5. Same-day follow-up (independent review): UNTRACKED-BUT-PRESENT. `git
       diff --quiet HEAD -- path` exits 0 for an untracked file (confirmed
       live) -- diff never sees a path git isn't tracking; it does not signal
       "missing from HEAD" the way a deleted-and-still-tracked path does. A
       registered SKILL.md authored straight into the checkout and never
       `git add`ed would fall through as "worktree == HEAD" and read
       STATE_CLEAN -- exactly the "content the scheduler runs that git has
       never seen" case this whole check exists to name. `ls-files
       --error-unmatch` (rc1 = not in the index) runs FIRST to close that gap
       -- BUT gated on `os.path.isfile(path)` (decision 6): rc1 alone is
       ambiguous.
    6. Same-day follow-up (independent review, SECOND pass): the decision-5
       gate as first written conflated "untracked file PRESENT on disk" with
       "path ABSENT entirely" -- `ls-files --error-unmatch` returns rc1 for
       both, confirmed live, and cannot tell them apart on its own. Absent is
       NOT the same failure: a brand-new SKILL.md merged to origin and never
       pulled has nothing on disk to commit, so reporting STATE_UNCOMMITTED
       with "commit it or revert it" is actively wrong -- the truth is
       BEHIND and the fix is "pull". That is the OI-170 incident class
       applied to a NEW file rather than an edited one. The `isfile` guard
       splits the two: present-but-untracked reports here; absent falls
       through to step 1, where `diff --quiet HEAD` correctly reads 0
       (confirmed live) and the existing upstream logic takes it from
       there -- landing on BEHIND when upstream has the file, CLEAN/None
       otherwise.

    Order matters: the untracked and uncommitted tests run FIRST and
    short-circuit, because content the scheduler reads that exists in no
    commit at all is strictly worse than being behind, and should be reported
    as itself.

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

        # 0. UNTRACKED, but ONLY when the file actually EXISTS on disk.
        #    Independent review, second pass, caught the gap in the first
        #    version of this step: `ls-files --error-unmatch` returns rc1 for
        #    BOTH "untracked file present on disk" and "path absent
        #    entirely" -- confirmed live, it cannot tell the two apart. The
        #    first version treated both as STATE_UNCOMMITTED, which silently
        #    regressed a brand-new SKILL.md merged to origin and never
        #    pulled -- nothing on disk to commit, so "commit it or revert
        #    it" is actively wrong; the truth is BEHIND and the fix is
        #    "pull". That is the OI-170 incident class applied to a new file
        #    rather than an edited one -- precisely the case this whole
        #    check exists to name correctly, and step 0 was mislabeling it.
        #    The os.path.isfile() guard splits the two: present-but-untracked
        #    is reported HERE; absent falls through to step 1, where
        #    `diff --quiet HEAD` correctly reads 0 (confirmed live) and
        #    proceeds into the upstream logic, landing on BEHIND when
        #    upstream has the file and CLEAN/None otherwise -- exactly what
        #    the pre-step-0 version of this function already did right.
        lf = run(["git", "-C", root, "ls-files", "--error-unmatch", "--", path],
                 capture_output=True, timeout=15)
        if lf.returncode == 1 and os.path.isfile(path):
            return STATE_UNCOMMITTED
        if lf.returncode not in (0, 1):
            return None           # git failure -- no verdict, not "untracked"

        # 1. Tracked. Worktree vs HEAD: rc1 => a committed path has a local
        #    edit never committed. Reported on its own; no upstream needed.
        wt = run(["git", "-C", root, "diff", "--quiet", "HEAD", "--", path],
                 capture_output=True, timeout=30)
        if wt.returncode == 1:
            return STATE_UNCOMMITTED
        if wt.returncode != 0:
            return None          # git failure -- no verdict

        # 2. Worktree matches HEAD. Is upstream ahead of us for this path?
        up = run(["git", "-C", root, "rev-parse", "--abbrev-ref", "@{upstream}"],
                 capture_output=True, timeout=15)
        if up.returncode != 0:
            return STATE_CLEAN   # no upstream: cannot be behind anything
        ref = up.stdout.decode("utf-8", "replace").strip()
        if not ref:
            return STATE_CLEAN

        mb = run(["git", "-C", root, "merge-base", "HEAD", ref],
                 capture_output=True, timeout=15)
        if mb.returncode != 0:
            return None          # unrelated histories -- no verdict
        base = mb.stdout.decode("utf-8", "replace").strip()
        if not base:
            return None

        # base..upstream for this path: did upstream touch it since we diverged?
        # Empty (rc0) => upstream has nothing we lack => CLEAN (covers pure AHEAD).
        beh = run(["git", "-C", root, "diff", "--quiet", base, ref, "--", path],
                  capture_output=True, timeout=30)
        if beh.returncode == 0:
            return STATE_CLEAN
        if beh.returncode != 1:
            return None

        # Independent review (2026-08-16, same-day follow-up to OI-182) caught
        # what the base..upstream test alone misses: DIVERGENT commits that
        # produce byte-identical content. Confirmed live -- upstream commits a
        # fix, this checkout independently commits the byte-identical fix in
        # its OWN commit (no shared ancestry for that change), worktree ==
        # local HEAD == upstream's content. base..upstream is non-empty (the
        # PATH's history differs), so without this gate that reports BEHIND --
        # "upstream carries a change we don't have" -- which is false: nothing
        # is missing, and "pull the branch" fixes nothing. This is exactly the
        # false-positive class OI-182 exists to eliminate, just one git-graph
        # shape deeper than "purely ahead". A worktree-vs-upstream CONTENT
        # check (not commit-graph) is authoritative for what the scheduler
        # actually runs, so it is the real question regardless of history:
        wu = run(["git", "-C", root, "diff", "--quiet", ref, "--", path],
                 capture_output=True, timeout=30)
        if wu.returncode == 0:
            return STATE_CLEAN       # content identical despite divergent history
        if wu.returncode == 1:
            return STATE_BEHIND      # content genuinely differs -- real finding
        return None
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

    Catches two DISTINCT conditions, reported separately (OI-182) rather than
    folded together as the first cut did:
      STATE_UNCOMMITTED -- the bytes the scheduler reads exist in no commit.
      STATE_BEHIND      -- upstream advanced this path and we do not have it
                           (the OI-170 case: merged but never pulled).
    AHEAD of upstream is deliberately NOT a finding. See _git_path_state
    decision 3: ahead is this checkout's normal resting state, and alarming on
    it is how the check earns the alarm fatigue that killed its first cut.

    Unanswerable cases yield NO finding (see _git_path_state): a task folder
    outside any git repo -- which is exactly the LAMS/Cowork fleet's normal
    configuration, its SKILL.mds living under OneDrive -- is a legitimate
    setup, not drift. Only ENABLED entries, matching both sibling checks'
    convention. Pure given its injectable.

    Returns sorted ids, preserving the sibling checks' shape. Use
    find_stale_states() when the per-id reason is needed."""
    return sorted(find_stale_states(entries, state_fn=differs))


def find_stale_states(entries, state_fn=None):
    """{id: STATE_*} for ENABLED entries in a finding state. The reason-carrying
    form of find_stale_vs_git(); main() uses it to name each condition rather
    than reporting one undifferentiated bucket."""
    state_fn = state_fn or _git_path_state
    out = {}
    for e in entries:
        if not e.get("enabled"):
            continue
        fp = e.get("filePath") or ""
        if not fp:
            continue
        st = state_fn(fp)
        if st in (STATE_UNCOMMITTED, STATE_BEHIND):
            out[e["id"]] = st
    return out


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
        states = find_stale_states(entries)
        uncommitted = sorted(i for i, s in states.items() if s == STATE_UNCOMMITTED)
        behind = sorted(i for i, s in states.items() if s == STATE_BEHIND)
        stale = sorted(states)

        lines.append(f"{label}: folders={len(folders)} registry_entries={len(entries)} "
                     f"unregistered={unregistered or '-'} orphaned={orphaned or '-'} "
                     f"archived={archived or '-'} uncommitted={uncommitted or '-'} "
                     f"behind_upstream={behind or '-'}")

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
        if uncommitted:
            print(f"  [ACTION] UNCOMMITTED_VS_GIT in {label}: {', '.join(uncommitted)} -- "
                  "the SKILL.md on disk differs from HEAD, so the bytes the scheduler "
                  "actually reads exist in NO commit anywhere. Nothing reviews, backs "
                  "up, or reproduces this content. Commit it, or revert it.")
            bad = True
        if behind:
            print(f"  [ACTION] BEHIND_UPSTREAM in {label}: {', '.join(behind)} -- "
                  "upstream carries a change to this SKILL.md that this checkout does "
                  "not have. The scheduler reads the WORKING TREE, not git, so the task "
                  "is merged and still INERT until pulled. (ora-passed-deal-tracker "
                  "double-fire-guard failure mode: merged as b734674 while the live "
                  "file had zero hits for its own guard tokens.) Pull the branch.")
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
