---
name: scheduled-task-integrity-guard
description: RETIRED 2026-06-11 — migrated to CC fleet as ora-task-integrity-guard (12:54 ET); unattended Cowork sessions cannot run PowerShell. DISABLED, do not re-enable on this surface. (Was: daily self-healing guard 12:40 ET.)
---

Run the ORA scheduled-task integrity guard (re-registered 2026-06-10; v1.1 adds the registry-MEMBERSHIP check). Two engines, both deterministic PowerShell — do NOT reimplement either.

STEP 1 — FILE integrity: execute via Desktop Commander (bare `powershell` is NOT on PATH; use the full interpreter path):
C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\Users\Owner\OneDrive - Oxford Capital Partners (1)\Documents\Claude\Scheduled\scheduled-task-integrity-guard\guard.ps1"
guard.ps1 reads every scheduled-tasks.json registry under the packaged app store, builds active {id -> filePath}, restores any missing/stale SKILL.md from the newest surviving copy across three locations (canonical Documents\Claude\Scheduled, OneDrive governance mirror Claude_Workspace\00_Governance\Scheduled, local mirror C:\Users\Owner\.claude\_scheduled_tasks_backup), and refreshes both mirrors. Newest-wins; never deletes. Capture its single-line JSON stdout: {checked, restored:[], backed_up:[], missing_everywhere:[], ts}.

STEP 1b — REGISTRY MEMBERSHIP (v1.1, closes cross-audit gap B-prime — the 2026-06-09 silent-drop failure mode): execute:
C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\Users\Owner\OneDrive - Oxford Capital Partners (1)\Documents\Claude\Scheduled\scheduled-task-integrity-guard\membership-guard.ps1"
It snapshots enabled task IDs across BOTH fleets (LAMS Roaming json + the main store under the Packages LocalCache tree + ~/.claude), diffs vs yesterday's state (_state-history\membership-state.json), excludes one-time fireAt tasks by design, and prints single-line JSON: {ts, first_run, stores, enabled_total, disappeared:[], disabled:[], added:[], parse_miss:[]}.

STEP 2 — Evaluate both JSON outputs.
- ALARM conditions: guard.ps1 restored[] or missing_everywhere[] non-empty; OR membership disappeared[] or disabled[] non-empty.
- INFORMATIONAL (no email): added[] entries; first_run=true; empty diffs.
- If membership parse_miss[] is non-empty on TWO consecutive runs, treat as ALARM (a registry format changed — the guard may be blind).

STEP 3 — Email ONLY on an ALARM condition. Send path: Outlook COM via Desktop Commander C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1 (SOLE path; Composio fallback removed 2026-06-11 — on a non-zero COM exit, retry once, then DO NOT suppress the alarm condition so the next run re-alarms). From ggoldberg@oxfordra.net; To: ggoldberg@oxfordra.net ONLY (2026-05-15 routing directive, re-ratified 2026-06-10 — never cc egoldberg). Subject: "ORA Scheduled-Task Guard — {YYYY-MM-DD}: {summary, e.g. '2 restored, 1 DISAPPEARED'}". Body: restored ids (note which mirror), missing_everywhere ids (need manual reconstruction), and prominently any DISAPPEARED/DISABLED task ids with the store each vanished from — these are exactly the June-9-class silent drops this guard exists to catch. If NO alarm condition, send NOTHING — a clean healthy run is silent.

STEP 4 — On script error (non-zero exit or unparseable stdout from either engine), draft (do NOT send) a failure note to ggoldberg@oxfordra.net describing the error and stop.