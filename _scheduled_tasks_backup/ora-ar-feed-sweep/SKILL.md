---
name: ora-ar-feed-sweep
description: Weekly AR delinquency-feed sweep (Mon 8:20 AM, after ora-master-workbook-ingest 5:45/ora-cc-snapshot-refresh 6:21/ora-lease-snapshot-refresh 7:44) — copies Business/A.R. Reports/*.xlsx into oxford-command-center's data/ar/inbox and runs scripts/ar-import-headless.ts to keep tenantArrears/arBalances current for the arrears-*/ar-stale conditions and the daily brief's collections section. Guards: refuses to run against unmerged Phase 0 code (checks for server/ar/delinquency-bucketed.ts) or while the dev server is up (patch would be silently reverted). ggoldberg-only summary via Outlook COM. [MODEL: claude-sonnet-5 | set 2026-08-17]
---

You are running the weekly AR delinquency-feed sweep for Oxford Realty Advisors' oxford-command-center. This is an unattended scheduled task — no human is watching. Follow every step; do not improvise beyond what's written here.

## Repo

`C:\Users\Owner\oxford-command-center` — the live checkout on `main`. Do not touch any git branch, worktree, or PR. This task runs the checkout as-is.

## Guard 1 — refuse to run against unmerged/stale code

Check that `C:\Users\Owner\oxford-command-center\server\ar\delinquency-bucketed.ts` exists. This file only exists once PR #283 (feat/p4-pm-reconciliation, "activate the dark AR feed — Phase 0") has merged to main. If it does NOT exist:
- Do NOT run the importer — the pre-merge script only recognizes one of the three real xlsx formats and will misfire.
- Send a short email via Outlook COM (`C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1`) to `ggoldberg@oxfordra.net` ONLY: subject "AR feed sweep skipped — PR #283 not yet merged", body stating the guard tripped and PR #283 needs to land before this task can do anything.
- Stop. Do not proceed to any step below.

## Guard 2 — refuse to run while the dev server is up

Check whether `http://localhost:5173` responds (e.g. a `curl -s -o /dev/null -m 3` that exits 0 means it's up). `Brain` (server/brain.ts) loads `data/overlay.json` into memory once at server construction and never re-reads it — if the dev server is running when this sweep writes to `overlay.json`, that write gets silently reverted by the very next server-mediated overlay mutation, with no error anywhere.

If the server responds: do NOT run the importer. Send a short email via the same Outlook COM path to `ggoldberg@oxfordra.net` ONLY: subject "AR feed sweep skipped — dev server was running", body noting today's sweep was skipped and will retry next Monday; suggest stopping the dev server before the next scheduled slot if this recurs.

Both guards passing is a precondition for every step below.

## Step 1 — deliver fresh files into the inbox

Source: `C:\Users\Owner\OneDrive - Oxford Capital Partners\Business\A.R. Reports\*.xlsx` — read-only, COPY only, never move or modify (Hard Invariant 5).

Destination: `C:\Users\Owner\oxford-command-center\data\ar\inbox\`. Create it if absent. Copy every `.xlsx` file from the source into it, overwriting any same-named file already there (a fresher weekly export replacing last week's).

## Step 2 — run the importer

From `C:\Users\Owner\oxford-command-center`, run:

```
npx tsx scripts/ar-import-headless.ts
```

No environment variable overrides — this writes directly to the live `data/overlay.json` and `data/snapshots/portfolio.json`, which is the intended behavior now that both guards passed. Capture the full console output; exit code 0 is success (per-file quarantines are logged, not fatal), exit code 1 means the overlay write itself failed (treat as a real failure).

## Step 3 — report

Send one summary email via Outlook COM to `ggoldberg@oxfordra.net` ONLY (never cc anyone — this is not the Daily Brief exception). Subject: "AR feed sweep — <files written> written, <files in review> in review". Body, plain and factual, quoting the script's own final summary line verbatim plus:
- Any file that quarantined this run, with its stated reason verbatim — never paraphrase a quarantine reason.
- The count and total dollar value currently sitting in `data/ar/review-queue.json` (read the file; sum `d30+d60+d90+d90plus` per row).
- If the exit code was 1 (overlay write failed): state this as the headline, not a footnote — this is the failure mode that must never look like a quiet success.

Never fabricate a number. If any step in the console output is unclear or the review-queue file is missing/malformed, say so plainly in the email rather than guessing a count.

## What this task does NOT do

Does not resolve the review queue (that's the interactive `scripts/ar-import.ts`, a human-run tool). Does not touch git. Does not modify anything under `Business/`. Does not retry automatically on a guard trip — it reports and waits for next Monday.