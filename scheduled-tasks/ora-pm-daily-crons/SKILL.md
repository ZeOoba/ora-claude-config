---
name: ora-pm-daily-crons
description: Daily 9:40 AM ET ora-pm cron pinger (critical-dates-alerts + delinquency-check + Outlook-COM digest send) — supersedes the off-fleet Windows Task Scheduler task "ORA PM Crons" (OI-162). Retimed 09:00→09:40 on 2026-08-16 to clear a same-minute collision with LAMS ora-health-guard-fail-aging-nudge (0 9 * * 1-5) and to sit outside the 05:00–09:30 AM-pileup window (Automation Audit R13-6). [MODEL: claude-sonnet-5 | set 2026-08-16]
---

Run the ora-pm daily cron pinger by executing the EXISTING, already-tested PowerShell script — do not re-implement its logic, do not modify it:

powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Users\Owner\ora-pm-cron\ping-crons.ps1"

What this script does (for context only — you are invoking it, not reproducing it):
- POSTs to the deployed ora-pm Cloudflare Pages Worker's /api/cron/critical-dates-alerts and /api/cron/delinquency-check endpoints, authenticated with a Bearer token read from C:\Users\Owner\ora-pm-cron\cron-secret.txt.
- Logs every call (counters only, PII-redacted) to C:\Users\Owner\ora-pm-cron\cron.log.
- When either endpoint's JSON response carries a non-null `email` field, sends that digest via the canonical Outlook-COM sender to ggoldberg@oxfordra.net ONLY. The script is the sole sender — never draft or send a duplicate email yourself for this task.
- A send failure is logged and non-fatal; a POST failure is logged and non-fatal (next day's run retries; the Worker dedupes late-fee posting and alert history server-side, so no manual retry is needed here).

After running:
1. Read the last 5-10 lines of C:\Users\Owner\ora-pm-cron\cron.log and confirm both endpoints (critical-dates-alerts, delinquency-check) logged a result with TODAY's date.
2. Report the script's exit behavior (stdout lines) plus a one-line summary: counts posted, whether a digest send fired, and whether the send succeeded (look for "SEND OK" vs "SEND FAIL" in the log).
3. If today's date is NOT present in cron.log after running, or the script's own stdout shows an error, flag this loudly as a run failure — do not report success.

Context: this task supersedes the standalone Windows Task Scheduler task "ORA PM Crons" (same script, same 9:00 AM daily cadence), which has been disabled as of 2026-08-16 specifically so this fleet task is the sole trigger — do not re-enable that Windows task, and do not run the script from any other trigger.