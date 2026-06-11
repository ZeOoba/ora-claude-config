#!/usr/bin/env python3
r"""ORA scheduler maintenance (round 2) — additive cleanup + new task.

Does three things, all idempotent, with a backup first:
  1. LAMS: ADD (if missing) `ora-consolidate-memory-monthly` (monthly memory
     consolidation) and `ora-cc-implementation-verifier` (daily 07:45 read-only
     health check that emails a PASS/FAIL table). Idempotent — present tasks skipped.
  2. LAMS: DISABLE `hard-delete-zapier-trial-reminder` (no cron, Zapier retired — moot).
  3. CCS:  RETIRE both `ora-email-queue-am` + `ora-email-queue-pm` (superseded by
     LAMS inbox-pre-brief / outbox-qc-sweep) -> CCS registry emptied so the
     scheduled-tasks MCP stops showing the misleading 2-task fragment.

Healthy new tasks (distress-signal-monitor, pm-ar-export-freshness-check,
onedrive-cleanup) are intentionally LEFT ALONE — they fire on their first cron hit.

RUN WITH THE CLAUDE APP FULLY CLOSED (tray -> Exit). The app owns these registries
and must reload them on relaunch to pick up the new task. Re-runnable.
"""
import json, os, sys, subprocess, datetime, time

LAMS = r"C:\Users\Owner\AppData\Local\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Roaming\Claude\local-agent-mode-sessions\a6ad2c61-c3c8-4a48-98a5-e40c1db22ad3\583f08bc-0123-4111-8158-8fe3d927e350\scheduled-tasks.json"
CCS  = r"C:\Users\Owner\AppData\Local\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Roaming\Claude\claude-code-sessions\a6ad2c61-c3c8-4a48-98a5-e40c1db22ad3\583f08bc-0123-4111-8158-8fe3d927e350\scheduled-tasks.json"

NEW_TASKS = [
    {
        "id": "ora-consolidate-memory-monthly",
        "cronExpression": "0 5 2 * *",
        "enabled": True,
        "filePath": r"C:\Users\Owner\OneDrive - Oxford Capital Partners (1)\Documents\Claude\Scheduled\ora-consolidate-memory-monthly\SKILL.md",
        "createdAt": int(time.time() * 1000),
        "userSelectedFolders": [],
        "notifySessionId": None,
    },
    {
        "id": "ora-cc-implementation-verifier",
        "cronExpression": "45 7 * * *",
        "enabled": True,
        "filePath": r"C:\Users\Owner\OneDrive - Oxford Capital Partners (1)\Documents\Claude\Scheduled\ora-cc-implementation-verifier\SKILL.md",
        "createdAt": int(time.time() * 1000),
        "userSelectedFolders": [],
        "notifySessionId": None,
    },
]

def claude_running():
    try:
        return "claude.exe" in subprocess.run(["tasklist"], capture_output=True, text=True).stdout.lower()
    except Exception:
        return False

def load(p):
    with open(p, encoding="utf-8") as f: return json.load(f)
def save(p, d):
    with open(p, "w", encoding="utf-8") as f: json.dump(d, f, indent=2)

def main():
    if claude_running():
        print("ABORT: claude.exe is still running. Fully quit the Claude app (tray -> Exit) and re-run.")
        sys.exit(1)

    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    bdir = r"C:\Users\Owner\.claude\backups\scheduler-maint-" + stamp
    os.makedirs(bdir, exist_ok=True)

    # ---- LAMS ----
    if os.path.exists(LAMS):
        d = load(LAMS); save(os.path.join(bdir, "LAMS__scheduled-tasks.json"), d)
        tasks = d.setdefault("scheduledTasks", [])
        ids = {t.get("id") for t in tasks}
        for nt in NEW_TASKS:
            if nt["id"] in ids:
                print(f"LAMS: {nt['id']} already present — skipped add.")
            else:
                tasks.append(nt)
                print(f"LAMS: ADDED {nt['id']} (cron {nt['cronExpression']}).")
        for t in tasks:
            if t.get("id") == "hard-delete-zapier-trial-reminder" and t.get("enabled"):
                t["enabled"] = False
                print("LAMS: DISABLED hard-delete-zapier-trial-reminder.")
        save(LAMS, d)
        print(f"LAMS: now {len(tasks)} tasks, {sum(1 for t in tasks if t.get('enabled'))} enabled.")
    else:
        print("LAMS: registry missing — skipped.")

    # ---- CCS: email-queue am+pm are SUPERSEDED by LAMS inbox-pre-brief / outbox-qc-sweep ----
    if os.path.exists(CCS):
        d = load(CCS); save(os.path.join(bdir, "CCS__scheduled-tasks.json"), d)
        n = len(d.get("scheduledTasks", []))
        d["scheduledTasks"] = []
        save(CCS, d)
        print(f"CCS: RETIRED {n} superseded task(s) (email-queue am/pm) -> registry now 0 tasks. "
              f"The scheduled-tasks MCP will stop showing the stale 2-task fragment.")
    else:
        print("CCS: registry missing — skipped.")

    print(f"\nDONE. Backups: {bdir}. Relaunch the Claude app to load the new task.")

if __name__ == "__main__":
    main()
