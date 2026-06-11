#!/usr/bin/env python3
r"""ORA scheduler maintenance — strip all Rube tool-approvals from the live
scheduled-task registries. Rube is shut down (EOL 2026-05-15); these approvals
are inert but the standing policy is "nothing related to Rube."

WHY A SCRIPT (and not done live from Claude Code):
The Claude app owns these registry files and rewrites them in memory as tasks
fire — editing them while the app runs gets clobbered. So this MUST run with the
app fully closed.

HOW TO RUN:
  1. Fully quit the Claude app (tray icon -> Exit; confirm no claude.exe remain).
  2. python "C:\Users\Owner\.claude\maintenance\scrub-rube-from-registry.py"
  3. Re-launch the Claude app.

It backs up every registry first and only removes approvedPermissions entries
that reference the Rube server id (d6315173) or a RUBE_ tool. Nothing else is
touched. Re-runnable / idempotent.
"""
import json, os, sys, subprocess, datetime

REGISTRIES = [
    r"C:\Users\Owner\AppData\Local\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Roaming\Claude\local-agent-mode-sessions\a6ad2c61-c3c8-4a48-98a5-e40c1db22ad3\583f08bc-0123-4111-8158-8fe3d927e350\scheduled-tasks.json",
    r"C:\Users\Owner\AppData\Local\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Roaming\Claude\claude-code-sessions\a6ad2c61-c3c8-4a48-98a5-e40c1db22ad3\583f08bc-0123-4111-8158-8fe3d927e350\scheduled-tasks.json",
]
RUBE_MARKERS = ("d6315173", "RUBE_")

def claude_running():
    try:
        out = subprocess.run(["tasklist"], capture_output=True, text=True).stdout.lower()
        return "claude.exe" in out
    except Exception:
        return False  # can't tell -> let user judge

def main():
    if claude_running():
        print("ABORT: claude.exe is still running. Fully quit the Claude app "
              "(tray -> Exit) and re-run. Editing the registry while the app is "
              "live would be clobbered.")
        sys.exit(1)

    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_dir = r"C:\Users\Owner\.claude\backups\registry-rube-scrub-" + stamp
    os.makedirs(backup_dir, exist_ok=True)
    total_removed = 0

    for reg in REGISTRIES:
        if not os.path.exists(reg):
            print("skip (missing):", reg)
            continue
        # backup, namespaced by the *-sessions parent so the two don't collide
        sess = reg.split(os.sep)[-4]
        with open(reg, encoding="utf-8") as f:
            data = json.load(f)
        with open(os.path.join(backup_dir, f"{sess}__scheduled-tasks.json"), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        removed_here = 0
        for t in data.get("scheduledTasks", []):
            perms = t.get("approvedPermissions")
            if not isinstance(perms, list):
                continue
            kept = [p for p in perms if not any(m in str(p) for m in RUBE_MARKERS)]
            if len(kept) != len(perms):
                removed_here += len(perms) - len(kept)
                print(f"  [{sess}] {t.get('id')}: removed {len(perms)-len(kept)} Rube approval(s)")
                t["approvedPermissions"] = kept

        with open(reg, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        total_removed += removed_here
        print(f"{sess}: {removed_here} Rube approval(s) removed.")

    print(f"\nDONE. {total_removed} Rube tool-approval(s) stripped. Backups: {backup_dir}")
    print("Re-launch the Claude app now.")

if __name__ == "__main__":
    main()
    
