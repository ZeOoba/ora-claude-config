---
name: onedrive-cleanup
description: Weekly Sunday 9 PM ET reversible OneDrive cleanup — runs cleanup.ps1 to quarantine superseded/duplicate/junk/aged-scratch Claude outputs (never deletes live files), emails manifest to Gabriel + Eric, purges only quarantine folders older than 30 days.
---

Run the ORA OneDrive weekly cleanup. This is a reversible quarantine-and-report job — it MOVES flagged files, it does not delete live working files.

STEP 1 — Execute the deterministic engine via Desktop Commander (bare `powershell` is NOT on PATH; use the full interpreter path):
C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe -ExecutionPolicy Bypass -File "C:\Users\Owner\OneDrive - Oxford Capital Partners (1)\Documents\Claude\Scheduled\onedrive-cleanup\cleanup.ps1"

The engine (cleanup.ps1, the authoritative logic — do not reimplement it) scans Documents\Claude\Outputs and Documents\Claude\Workspace and MOVES flagged files into a dated, reversible quarantine at Documents\Claude\_Cowork_Quarantine\{YYYY-MM-DD}\ with a manifest.csv. Flag reasons: superseded-version (highest _v## kept), duplicate (exact SHA-256, newest kept), junk-or-empty (~$ locks, .tmp/.crdownload/.partial, Thumbs.db, .DS_Store, desktop.ini, zero-byte), aged-scratch (_old/_draft/scratch folders >30 days). PROTECTED and never moved: CLAUDE.md; anything under \References\ \_DoNotDelete\ \_Canonical\ \Scheduled\ \_Cowork_Quarantine\; filenames signalling executed/institutional records (executed, signed, PSA, lease, deed, loan, note, guaranty, estoppel, SNDA, mortgage, rent roll, pro forma, model, budget, appraisal, K-1, operating agreement); and any file modified within the last 14 days. The ONLY hard delete is purging quarantine date-folders older than 30 days.

STEP 2 — Capture the JSON summary printed on stdout. If quarantined_count > 0, read the manifest.csv in the dated quarantine folder.

STEP 3 — Email the report via Composio OUTLOOK_SEND_EMAIL (account_id outlook_icaco-sequel) from ggoldberg@oxfordra.net. To: ggoldberg@oxfordra.net; Cc: egoldberg@oxfordra.net. Subject: "ORA OneDrive Cleanup — {YYYY-MM-DD}". Body: counts by reason, bytes reclaimed, purge count, quarantine path, and the note that quarantined items auto-purge after 30 days. Attach manifest.csv when present.

STEP 4 — On script error (non-zero exit or PARSE failure), draft (do NOT send) a failure email to both principals describing the error, and stop.

Scope is intentionally limited to the two Claude folders; do not widen without explicit instruction.