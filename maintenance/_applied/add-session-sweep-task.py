#!/usr/bin/env python3
"""Add ora-session-sweep to the LAMS scheduler registry.

RUN WITH CLAUDE DESKTOP FULLY CLOSED (tray → Exit).
The app owns the registry and reloads it on relaunch.
Re-runnable (idempotent — skips if task already present).
"""
import json, os, sys, time, shutil, datetime

LAMS = (
    r"C:\Users\Owner\AppData\Local\Packages\Claude_pzs8sxrjxfjjc"
    r"\LocalCache\Roaming\Claude\local-agent-mode-sessions"
    r"\a6ad2c61-c3c8-4a48-98a5-e40c1db22ad3"
    r"\583f08bc-0123-4111-8158-8fe3d927e350\scheduled-tasks.json"
)

TASK = {
    "id": "ora-session-sweep",
    "cronExpression": "0 20 * * 0",   # Sunday 20:00
    "enabled": True,
    "filePath": (
        r"C:\Users\Owner\OneDrive - Oxford Capital Partners (1)"
        r"\Documents\Claude\Scheduled\ora-session-sweep\SKILL.md"
    ),
    "createdAt": int(time.time() * 1000),
    "lastRunAt": None,
    "lastScheduledFor": None,
    "userSelectedFolders": [],
    "approvedPermissions": [],
}

# ── Safety: abort if Claude is running ──────────────────────────────────────
import subprocess
result = subprocess.run(
    ["tasklist", "/FI", "IMAGENAME eq claude.exe"],
    capture_output=True, text=True
)
if "claude.exe" in result.stdout.lower():
    print("ERROR: Claude Desktop is running. Exit it fully (tray → Exit) then re-run.")
    sys.exit(1)

# ── Backup ───────────────────────────────────────────────────────────────────
ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup = LAMS + f".bak_{ts}"
shutil.copy2(LAMS, backup)
print(f"Backup: {backup}")

# ── Load ─────────────────────────────────────────────────────────────────────
with open(LAMS, encoding="utf-8") as f:
    data = json.load(f)

tasks = data["scheduledTasks"]
existing_ids = {t["id"] for t in tasks}

if "ora-session-sweep" in existing_ids:
    print("Task already present — nothing to do.")
    sys.exit(0)

# ── Add ──────────────────────────────────────────────────────────────────────
tasks.append(TASK)
data["scheduledTasks"] = tasks

with open(LAMS, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)

print(f"Added: ora-session-sweep (Sunday 20:00)")
print(f"Total tasks now: {len(tasks)}")
print("Relaunch Claude Desktop to activate.")
