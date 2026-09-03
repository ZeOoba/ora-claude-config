---
name: ora-pm-monthly-billing
description: Monthly (1st, 11:10 AM ET) ora-pm billing trigger — POSTs to the deployed Cloudflare Pages Worker's /api/cron/monthly-billing via the existing trigger-billing.ps1 drain loop. Registered 2026-08-21 (OI-162 monthly half, closing the "never actually triggers" gap Gabriel confirmed against the charges table). Money-moving: posts rent/CAM charges and, once autopay enrollment ships (OI-068), debits enrolled tenants via Stripe. [MODEL: claude-sonnet-5 | set 2026-08-21]
offhost-backup: pending — ZeOoba/ora-pm PR #24 (feat/offhost-monthly-billing-backup → .github/workflows/monthly-billing-backup.yml, cron 40 17 1 * * UTC) OPEN and unmerged as of 2026-09-03, so this trigger is laptop-only until it merges. Declared 2026-09-03 under register-scheduled-task v2.19 rule 3b; re-check this line after any update_scheduled_task call (that call drops non-owned frontmatter keys).
---

Run the ora-pm monthly billing trigger by executing the EXISTING, already-tested PowerShell script — do not re-implement its logic, do not modify it:

powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Users\Owner\ora-pm\scripts\trigger-billing.ps1"

What this script does (for context only — you are invoking it, not reproducing it):
- POSTs to the deployed ora-pm Cloudflare Pages Worker's /api/cron/monthly-billing, authenticated with a Bearer token read from $env:ORA_PM_CRON_SECRET (User-scope env var on this machine, matches the CRON_SECRET Cloudflare Pages secret).
- Charge posting is a single bulk upsert with ON CONFLICT DO NOTHING on idempotency_key — a re-run or a retry cannot double-post the same charge.
- Drains the endpoint's `remaining` count in a bounded loop (MAX_INVOCATIONS=8, AUTOPAY_BATCH_LIMIT=8 leases/call = 64 autopay debits/run cap). Currently 0 leases are autopay-eligible in production (enrollment isn't reachable from the tenant portal yet — OI-068), so only the charge-posting path is exercised on this fire.
- Breaks loudly and exits non-zero if `remaining` fails to decrease between two calls (a lease whose Stripe call fails deterministically every attempt would otherwise re-occupy the same batch slot for the whole run) — this is a real failure, not a transient one; do not silently retry past what the script itself does.

After running:
1. Read the script's stdout for each invocation's `posted=... skipped=... errors=... chargeErrors=... autopayErrors=... remaining=...` line.
2. Report a one-line summary: total posted, any chargeErrors/autopayErrors, final `remaining` (should reach 0).
3. If the script exits non-zero, or `remaining` never reaches 0, flag this loudly — do not report success. This is a money-moving job; a partial or failed run needs a human look, not a quiet retry next month.
4. Send ONE summary via Outlook COM (C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1 — the sole send path) to ggoldberg@oxfordra.net ONLY (no cc). Subject: "ora-pm monthly billing — <posted> charges posted, remaining=<N>" (flip to "[ACTION]" prefix on any non-zero exit or nonzero final remaining). On COM send failure: retry once; if it still fails, do not halt — automation-health-monitor will catch a missed send, but note the failure in the run output anyway.

Context: this closes OI-162's monthly half. (OI-201, the stale ora-pm/README.md scheduler section, was fixed 2026-08-21 in commit `c311da7` and re-verified against the live registry 2026-09-02 — it is CLOSED, not a standing item for this task.) CRON_SECRET was rotated 2026-08-21 when this task was registered (the prior value had never been read by anything on the billing path — confirmed via the never-been-billed charges-table check) and $env:ORA_PM_CRON_SECRET / the Cloudflare Pages secret were set to match; C:\Users\Owner\ora-pm-cron\cron-secret.txt (used by the separate ora-pm-daily-crons task, same CRON_SECRET, different consumer file) was updated to the same new value in the same pass so that task keeps working.