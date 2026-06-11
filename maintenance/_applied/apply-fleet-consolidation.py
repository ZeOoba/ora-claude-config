#!/usr/bin/env python3
r"""ORA fleet consolidation — STAGE 1 (safe deletions). Phase 3.

RUN WITH THE CLAUDE APP FULLY CLOSED (tray -> Exit). The app owns the scheduler registry
and reloads it on relaunch; live hand-edits get clobbered. This script aborts if claude.exe
is running. Idempotent + backed up + auto-discovers the registry (no hardcoded GUID, I4).

STAGE 1 (this script) removes ONLY the 2 unambiguous dead tasks — both already DISABLED
with an expired one-time fireAt, zero SKILL dependency, fully reversible from the backup:
  - hard-delete-zapier-trial-reminder   (Zapier retired; never ran; expired)
  - ora-quarterly-cron-restore-20260521 (already ran 2026-05-21; expired)

It will REFUSE to delete a task that is currently enabled (safety). The full 45 -> ~18
consolidation (the 6 SKILL.md merges from phase3-fleet-plan.md) is STAGE 2 — authored
separately, applied in the same app-closed manner.

After running: relaunch Claude, then `python ~/.claude/maintenance/fleet-status.py`.
"""
import os, sys, json, glob, subprocess, datetime, shutil

for _s in (sys.stdout, sys.stderr):
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

HOME = os.path.expanduser("~")

# Tasks to delete in Stage 1, each with the guard signature we REQUIRE before deleting.
DELETE = {
    "hard-delete-zapier-trial-reminder": {"must_be_disabled": True},
    "ora-quarterly-cron-restore-20260521": {"must_be_disabled": True},
}

def claude_running():
    try:
        out = subprocess.run(["tasklist"], capture_output=True, text=True).stdout.lower()
        return "claude.exe" in out
    except Exception:
        return True  # fail safe: if we can't tell, assume running and abort

def discover_registry():
    r"""Find the live LAMS registry GUID-agnostically from an EXTERNAL terminal OR inside the
    container. Claude is MSIX-packaged: externally the live registry is under
    %LOCALAPPDATA%\Packages\Claude*\LocalCache\Roaming\Claude\local-agent-mode-sessions\... ;
    in-container it appears under %APPDATA%\Claude\... (virtualized). Search both (no hardcoded GUID)."""
    la = os.environ.get("LOCALAPPDATA") or os.path.join(HOME, "AppData", "Local")
    ra = os.environ.get("APPDATA") or os.path.join(HOME, "AppData", "Roaming")
    bases = [
        os.path.join(la, "Packages", "Claude*", "LocalCache", "Roaming", "Claude", "local-agent-mode-sessions"),
        os.path.join(ra, "Claude", "local-agent-mode-sessions"),
    ]
    seen, scored = set(), []
    for base in bases:
        for p in glob.glob(os.path.join(base, "**", "scheduled-tasks.json"), recursive=True):
            rp = os.path.realpath(p)
            if rp in seen:
                continue
            seen.add(rp)
            try:
                n = len(json.load(open(p, encoding="utf-8")).get("scheduledTasks", []) or [])
                if n > 0:
                    scored.append((n, os.path.getmtime(p), p))
            except Exception:
                continue
    scored.sort(key=lambda t: (t[0], t[1]), reverse=True)
    return scored[0][2] if scored else None

def main():
    if claude_running():
        print("ABORT: claude.exe is running. Fully quit Claude (tray -> Exit) and re-run.")
        sys.exit(1)

    reg = discover_registry()
    if not reg:
        sys.stderr.write("[ACTION] fleet-consolidation: live LAMS registry not found. Nothing changed.\n")
        sys.exit(3)

    stamp = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
    bdir = os.path.join(HOME, ".claude", "backups", "fleet-consolidation-" + stamp)
    os.makedirs(bdir, exist_ok=True)
    shutil.copy2(reg, os.path.join(bdir, "LAMS__scheduled-tasks.json"))
    with open(os.path.join(bdir, "MANIFEST.txt"), "w", encoding="utf-8") as m:
        m.write("registry: %s\nbytes: %d\nsaved: %sZ\n" % (reg, os.path.getsize(reg),
                 datetime.datetime.utcnow().isoformat()))
    print("Backup: %s" % bdir)

    d = json.load(open(reg, encoding="utf-8"))
    tasks = d.get("scheduledTasks", [])
    before = len(tasks)
    by_id = {t.get("id"): t for t in tasks}

    keep, removed, refused, absent = [], [], [], []
    for tid, guard in DELETE.items():
        t = by_id.get(tid)
        if t is None:
            absent.append(tid)
        elif guard.get("must_be_disabled") and t.get("enabled", True):
            refused.append(tid)  # safety: never delete an enabled task

    del_ids = {tid for tid in DELETE if tid in by_id and tid not in refused}
    for t in tasks:
        if t.get("id") in del_ids:
            removed.append(t.get("id"))
        else:
            keep.append(t)

    if refused:
        print("REFUSED (currently enabled — not safe to auto-delete): %s" % ", ".join(refused))
    if absent:
        print("Already absent (idempotent skip): %s" % ", ".join(absent))

    if removed:
        d["scheduledTasks"] = keep
        with open(reg, "w", encoding="utf-8") as f:
            json.dump(d, f, indent=2)
        print("DELETED %d task(s): %s" % (len(removed), ", ".join(removed)))
    else:
        print("No deletions applied.")

    print("Tasks: %d -> %d. Relaunch Claude, then run fleet-status.py." % (before, len(keep)))
    print("STAGE 2 (45->~18 merges) is pending — see _brain-overhaul/phase3-fleet-plan.md.")
    sys.exit(0)

if __name__ == "__main__":
    main()
