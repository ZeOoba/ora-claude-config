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

        lines.append(f"{label}: folders={len(folders)} registry_entries={len(entries)} "
                     f"unregistered={unregistered or '-'} orphaned={orphaned or '-'} "
                     f"archived={archived or '-'}")

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
        if not unregistered and not orphaned and not archived:
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
