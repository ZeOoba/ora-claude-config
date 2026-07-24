#!/usr/bin/env python3
"""ORA task-folder backup-completeness probe -- catches a substantive
non-SKILL.md file inside a scheduled-task folder that is silently INVISIBLE
to git (ignored, not just untracked), before a machine loss destroys it.

WHY: .gitignore's 2b rule ("ONLY SKILL.md is tracked; runtime state stays
ignored") uses a directory-level */* deny with a single !*/SKILL.md
negation. That correctly hides ephemeral state, but it ALSO silently hides
anything else dropped into a task folder by pattern accident -- an engine
script, a Gabriel-ratified reference file, whatever. Confirmed cases found
by manual audit 2026-07-24, not by any automated check: guard.ps1 and
membership-guard.ps1 (ora-task-integrity-guard's own engines) sat with ZERO
backup anywhere; ora-appsec-sweep/suppressions.md (a ratified suppression
list) and ora-pm-ledger/tenant_db_snapshot_diff.py (a 294-line engine) were
the same gap. All four were only found because someone happened to look --
exactly the reactive failure mode this probe exists to close.

Scope is CC/MCP only. `_scheduled_tasks_backup/` (the local mirror) has no
*/* deny -- everything under it is already trackable, so it's not at risk
the same way. LAMS task folders live purely in OneDrive, outside this git
repo -- OneDrive's own sync/versioning is their durability mechanism, not
ora-claude-config. _archive_*/ and _shared/ each have their own dedicated,
already-audited gitignore ladders (_shared/ additionally holds live
credentials and is deliberately never directory-negated) and are excluded
here to avoid duplicate/contradictory findings.

Two dispositions for any finding, both explicit -- never a silent third:
  1. Allow-list it in .gitignore (durable fix). The finding then disappears
     on its own next run, since git check-ignore reports it as no longer
     ignored -- no probe-side bookkeeping needed.
  2. Add it to _shared/task-folder-runtime-state-allowlist.json with a
     dated reason (deliberate runtime state, e.g. ora-open-sessions-board's
     answered.json). Only Gabriel adds entries there.

Exit 0 = clean (tracked, or on the reviewed-exempt list).
Exit 1 = [ACTION] UNBACKED finding(s) -- neither tracked nor exempt.
Run daily alongside task-folder-registration-probe.py (ora-task-integrity-guard).
"""
import json
import os
import subprocess
import sys
import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "_shared"))
try:
    import store_discovery as _sd
except Exception:
    _sd = None  # fail-open: discovery call below returns None

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

REPO_ROOT = os.path.dirname(os.path.abspath(__file__)).rsplit(os.sep + "maintenance", 1)[0]
ALLOWLIST_PATH = os.path.join(REPO_ROOT, "maintenance", "_shared",
                               "task-folder-runtime-state-allowlist.json")
STATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_state")
LOG = os.path.join(STATE_DIR, "task-folder-backup-completeness.log")

SKIP_ID_PREFIXES = ("_archive_",)
SKIP_IDS = ("_shared",)


def load_exempt_paths(path):
    """Set of repo-relative paths (forward-slashed) exempt from flagging, or
    an empty set if the allowlist is missing/unreadable (fail-open -- a
    broken allowlist file must never make every runtime-state file alarm
    at once)."""
    try:
        d = json.load(open(path, encoding="utf-8"))
    except Exception:
        return set()
    return {e["path"].replace("\\", "/") for e in d.get("exempt", []) if e.get("path")}


def list_candidate_files(folder_root):
    """[(task_id, abs_path, repo_rel_path)] for every file directly inside a
    scheduled-tasks/<id>/ folder except SKILL.md, skipping _archive_*/
    and _shared/ (each has its own dedicated gitignore ladder already).
    None if folder_root is missing/unreadable."""
    try:
        ids = os.listdir(folder_root)
    except Exception:
        return None
    out = []
    for task_id in ids:
        if task_id in SKIP_IDS or task_id.startswith(SKIP_ID_PREFIXES):
            continue
        task_dir = os.path.join(folder_root, task_id)
        if not os.path.isdir(task_dir):
            continue
        try:
            names = os.listdir(task_dir)
        except Exception:
            continue
        for name in names:
            if name == "SKILL.md":
                continue
            p = os.path.join(task_dir, name)
            if not os.path.isfile(p):
                continue
            rel = os.path.relpath(p, REPO_ROOT).replace("\\", "/")
            out.append((task_id, p, rel))
    return out


def is_git_ignored(repo_root, abs_path):
    """True if `git check-ignore` matches abs_path (exit 0). False if it
    exits 1 (not ignored -- tracked or trackable). None on any other
    failure (e.g. git unavailable) -- caller must fail-open on None."""
    try:
        r = subprocess.run(
            ["git", "check-ignore", "-q", abs_path],
            cwd=repo_root, capture_output=True, timeout=15,
        )
    except Exception:
        return None
    if r.returncode == 0:
        return True
    if r.returncode == 1:
        return False
    return None


def find_unbacked(candidates, exempt_paths, repo_root):
    """[(task_id, rel_path)] sorted -- ignored by git AND not on the exempt
    list. candidates: [(task_id, abs_path, rel_path)]."""
    out = []
    for task_id, abs_path, rel_path in candidates:
        if rel_path in exempt_paths:
            continue
        ignored = is_git_ignored(repo_root, abs_path)
        if ignored is None:
            continue  # fail-open: cannot determine, do not flag
        if ignored:
            out.append((task_id, rel_path))
    return sorted(out)


def main():
    if _sd is None:
        print("  WARN store_discovery unavailable -- probe cannot run.")
        return 0  # fail-open: a broken shared helper must never false-alarm

    folder_root = _sd.skill_folder_root("cc")
    print(f"cc: folder_root={folder_root or '(unconfigured)'} repo_root={REPO_ROOT}")

    if not folder_root:
        print("  WARN cc skill-folder root not configured -- skipping.")
        return 0

    candidates = list_candidate_files(folder_root)
    if candidates is None:
        print("  WARN cc skill-folder root not found -- skipping.")
        return 0

    exempt_paths = load_exempt_paths(ALLOWLIST_PATH)
    print(f"  {len(candidates)} non-SKILL.md file(s) found in task folders "
          f"(excluding _archive_*/_shared); {len(exempt_paths)} path(s) on the "
          f"reviewed-exempt list.")

    unbacked = find_unbacked(candidates, exempt_paths, REPO_ROOT)

    ts = datetime.datetime.now().isoformat(timespec="seconds")
    os.makedirs(STATE_DIR, exist_ok=True)
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(f"{ts} cc: checked={len(candidates)} exempt={len(exempt_paths)} "
                    f"unbacked={[r for _, r in unbacked] or '-'}\n")
    except Exception:
        pass

    if unbacked:
        for task_id, rel_path in unbacked:
            print(f"  [ACTION] UNBACKED in cc/{task_id}: {rel_path} -- git-ignored, not on "
                  "the reviewed-exempt list. Fix: allow-list in .gitignore (durable -- see "
                  "the existing per-file ladder, e.g. suppressions.md) or add to "
                  "task-folder-runtime-state-allowlist.json with a dated reason (deliberate "
                  "runtime state). (guard.ps1/suppressions.md failure mode, 2026-07-24.)")
        return 1

    print("  OK -- all non-SKILL.md task-folder files are tracked or reviewed-exempt.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
