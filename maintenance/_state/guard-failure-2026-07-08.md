# ORA Task Guard — SEND-PATH FAILURE — 2026-07-08

**Status:** Guard engines ran CLEAN, but the alarm email could NOT be delivered.
The alarm condition is REAL and remains UNSUPPRESSED — the next scheduled run will re-alarm.

## Alarm condition (would-have-been emailed)
- **disabled (newly non-empty):** `ora-weekly-sourcing-digest` — LAMS/Cowork registry
- disappeared=[], missing_everywhere=[], restored=[], parse_miss=[]  (no silent-drop; disablement only)
- Baseline is the 16.1-day-stale `mcp-fleet-snapshot:2026-06-22.json`; live CC/MCP registry was not in the merged store set this run.
- `ora-weekly-sourcing-digest` is a KNOWN purge item from the 2026-07-08 LAMS fleet audit — expected, not a surprise drop.

## Engine outputs (both exit 0, parseable — NOT a STEP-4 engine failure)
- guard.ps1: `{"checked":0,"restored":[],"backed_up":[],"missing_everywhere":[],"ts":"2026-07-08T12:55:15"}`
- membership-guard.ps1: `{"enabled_total":30,"disappeared":[],"disabled":["ora-weekly-sourcing-digest"],"added":["ora-lender-covenant-tracker","ora-debt-maturity-snapshot","ora-cash-position-snapshot"],"parse_miss":[],"mcp_snapshot_stale_days":16.1}`

## Why the send failed — REQUIRES HUMAN ACTION
- Outlook desktop is stuck on a **"New Profile"** wizard (process PID 42652, Responding=True, MainWindowTitle="New Profile").
- `send-via-outlook.ps1` (SOLE send path) hung on the blocked COM call on both the initial attempt (12:55) and the one retry — no OK entry written to send-log.txt.
- The send-log shows this has been failing ALL DAY 2026-07-08: repeated "TIMEOUT: COM call exceeded 15s" and "Outlook stuck on startup wizard" entries from 05:43 through 12:01. **This is a systemic send-path outage, not a one-off.**
- **FIX:** A human must open Outlook and dismiss/complete the profile wizard (select the existing M365 profile) so COM sends resume. Every ORA scheduled task that emails is currently blocked.

## Bug found (systematization candidate — NOT fixed, needs permission)
- `send-via-outlook.ps1` preflight regex is `'Welcome to Microsoft Outlook|Choose Profile'`. It does NOT match the current `"New Profile"` title, so the script fails to fast-exit (code 3) and instead HANGS ~2 min per call on the blocked COM job. Recommend adding `New Profile` (and possibly a generic `Profile`) to the preflight title match so it fast-fails exit 3 instead of hanging.

Written by ora-task-integrity-guard scheduled run, 2026-07-08 ~12:57 local.
