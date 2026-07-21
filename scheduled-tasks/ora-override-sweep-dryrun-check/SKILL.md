---
name: ora-override-sweep-dryrun-check
description: One-time pre-flight dry-run of the new sweep-override-tokens.ps1 script (Block L of ora-weekly-hygiene), well before its first live unattended run that same evening. Self-disables after firing.
---

This is an automated scheduled-task run. The user is not present to answer questions — execute autonomously, never fabricate data, and if something is genuinely ambiguous, note it in the email rather than guessing.

CONTEXT: `maintenance/sweep-override-tokens.ps1` was added 2026-07-21 (commit d5fcaf7) and wired into `ora-weekly-hygiene` as Block L, which fires today (Sunday) at 20:00 ET and will run this script for the FIRST TIME live/unattended. This task is a one-time pre-flight sanity check, running hours earlier, so Gabriel has a review window before that first live run.

STEPS:
1. Run: `powershell -NoProfile -ExecutionPolicy Bypass -File C:\Users\Owner\.claude\maintenance\sweep-override-tokens.ps1 -DryRun`
2. Capture the full output, in particular the final summary line (format: `DRYRUN sweep done: no-ttl-window=Nh ttl-window=Nmin tokens-archived=N kept-live-session=N kept-in-window=N tokens-scanned=N sessions-scanned=N`).
3. Sanity-check the numbers are plausible: `tokens-archived` should be a small number (single digits to low tens — NOT hundreds, since the accumulated backlog was already manually cleared 2026-07-21; a large number here would suggest something is wrong with the age-window logic or live-session detection and Block L should NOT be trusted to run live tonight without review). `kept-live-session` + `kept-in-window` + `tokens-archived` should sum to `tokens-scanned`.
4. If the script errors, exits non-zero, or the numbers look implausible per step 3: flag this prominently as the email's headline — recommend disabling Block L (or the whole ora-weekly-hygiene 20:00 fire) via `update_scheduled_task` is NOT something to do autonomously; just flag it clearly for Gabriel's judgment call before 20:00 ET tonight.
5. Send exactly one email via the sole sanctioned path: `C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1`. TO ggoldberg@oxfordra.net ONLY (no cc). Subject: "ORA Override-Sweep Dry-Run Pre-Flight — 2026-07-26". Body: the full script output, the sanity-check verdict from step 3 (PASS/CONCERN), and a one-line reminder that Block L fires for real at 20:00 ET tonight as part of ora-weekly-hygiene. On a non-zero COM exit: retry once, then note the failure in the session log — do not treat send failure as task failure.
6. This task self-disables after firing (one-time). No further action needed from it — do not re-register or modify ora-weekly-hygiene from this task.