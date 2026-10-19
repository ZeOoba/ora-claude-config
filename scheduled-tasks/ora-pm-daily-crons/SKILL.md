---
name: ora-pm-daily-crons
description: Daily 9:40 AM ET ora-pm cron pinger (critical-dates-alerts + delinquency-check + Outlook-COM digest send) — supersedes the off-fleet Windows Task Scheduler task "ORA PM Crons" (OI-162). Retimed 09:00→09:40 on 2026-08-16 to clear a same-minute collision with LAMS ora-health-guard-fail-aging-nudge (0 9 * * 1-5) and to sit outside the 05:00–09:30 AM-pileup window (Automation Audit R13-6). [MODEL: claude-sonnet-5-5 | set 2026-10-06]
offhost-backup: ZeOoba/ora-pm .github/workflows/delinquency-backup.yml (cron 10 16 * * * UTC, live since 2026-09-12) — delinquency-check ONLY. Live per register-scheduled-task v2.24 step 3b's three proofs: on main + active (PR #25 merged f756687), repo secret ORA_PM_CRON_SECRET present by name (set 2026-09-12T23:35Z), first real run success https://github.com/ZeOoba/ora-pm/actions/runs/34725864211 (HTTP 200, late_fees_posted=0, delinquent_count=68). Idempotent against this laptop trigger: one late fee per lease per month (existing-fee guard + unique idempotency_key), so a double fire posts 0. critical-dates-alerts is deliberately excluded (writes dedup rows before returning a digest only this laptop's Outlook-COM run can deliver; not money-moving). Closes OI-229; automation-health-monitor v1.10 re-verifies weekdays. Do not narrow the money-moving definition to clear this line. Re-check after any update_scheduled_task call (that call drops non-owned frontmatter keys).
---

Run the ora-pm daily cron pinger by executing the EXISTING, already-tested PowerShell script — do not re-implement its logic, do not modify it:

powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Users\Owner\ora-pm-cron\ping-crons.ps1"

What this script does (for context only — you are invoking it, not reproducing it):
- POSTs to the deployed ora-pm Cloudflare Pages Worker's /api/cron/critical-dates-alerts and /api/cron/delinquency-check endpoints, authenticated with a Bearer token read from C:\Users\Owner\ora-pm-cron\cron-secret.txt.
- Logs every call (counters only, PII-redacted) to C:\Users\Owner\ora-pm-cron\cron.log.
- When either endpoint's JSON response carries a non-null `email` field, sends that digest via the canonical Outlook-COM sender to ggoldberg@oxfordra.net ONLY. The script is the sole sender — never draft or send a duplicate email yourself for this task.
- OI-278 (2026-09-13): while delinquency-check returns `payments_feed_absent: true`, the script tracks that in C:\Users\Owner\ora-pm-cron\payments-feed-state.json and emails the PAYMENTS FEED ABSENT digest only on the first absent run, every 7 days after, or whenever late_fees_posted > 0. Other days it logs `SEND SUPPRESSED reason=suppressed-repeat tracked=OI-278` instead of sending. That is expected and is NOT a send failure. When the feed returns, it also sends a one-time "PAYMENTS FEED RESTORED - OI-278 can be closed" email.
- A send failure is logged and non-fatal; a POST failure is logged and non-fatal (next day's run retries; the Worker dedupes late-fee posting and alert history server-side, so no manual retry is needed here).

After running:
1. Read the last 5-10 lines of C:\Users\Owner\ora-pm-cron\cron.log and confirm both endpoints (critical-dates-alerts, delinquency-check) logged a result with TODAY's date.
2. Report the script's exit behavior (stdout lines) plus a one-line summary: counts posted, whether a digest send fired, and whether the send succeeded (look for "SEND OK" vs "SEND FAIL" in the log; "SEND SUPPRESSED ... tracked=OI-278" means the repeat notice was deliberately held back. Report it as suppressed, not failed. If you see "PAYMENTS FEED RESTORED" or "FEED STATE WRITE FAILED", call it out on its own line).
3. If today's date is NOT present in cron.log after running, or the script's own stdout shows an error, flag this loudly as a run failure — do not report success.

Context: this task supersedes the standalone Windows Task Scheduler task "ORA PM Crons" (same script, same 9:00 AM daily cadence), which has been disabled as of 2026-08-16 specifically so this fleet task is the sole trigger — do not re-enable that Windows task, and do not run the script from any other trigger.