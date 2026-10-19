---
name: ora-quarterly-estimate-check
description: Quarterly estimated-tax check for Eric & Rebecca Goldberg (federal, MD, OH) — 110% safe harbor plus projection, ten days before each installment due date. Emails ggoldberg@oxfordra.net only. [MODEL: claude-opus-5-5 | set 2026-10-15]
---

# ORA quarterly estimated-tax check

Calculation and notification only. This task never pays, schedules or moves money (not money-moving under register-scheduled-task step 3b).

## — DOUBLE-FIRE ENTRY GUARD (run first)
python C:\Users\Owner\.claude\scheduled-tasks\_shared\block-sentinel.py claim --task ora-quarterly-estimate-check --block main --run-id <run_id> --period month --ttl-min 30
- Exit 10 = this month already completed; Exit 11 = another fire is live. Stand down: no calculation or file write, no email; report a NORMAL skip.
- Exit 0 = proceed.
After the run finishes (after the email sends): `... block-sentinel.py complete --task ora-quarterly-estimate-check --block main --run-id <run_id> --period month --email-sent-at <ISO8601>`. On abort, and on a send that still fails after its one retry: `... fail ... --error "<what broke>"` (never `complete` without a real `--email-sent-at` when an email was owed). Only the claim holder calls complete/fail. ALWAYS pass `--period month`.

## Run date
Compute once at start: `date '+%A %Y-%m-%d'`. Reuse that exact value in every title, subject and body.

## Inputs (all in `C:\Users\Owner\OneDrive - Oxford Capital Partners\Business\Taxes Estimated + Returns\_ora-tax-tools\`)
- `estimate_check.py` — the calculator (stdlib only).
- `estimates_config_<TAXYEAR>.json` — prior-year total tax per jurisdiction, installment dates, projection drivers. TAXYEAR = the year whose estimates are due (the January run uses the prior calendar year).
- `estimates_ledger.csv` — every credit and payment (date, jurisdiction, tax_year, amount, type, note). Gabriel maintains it; never invent a payment.

## Steps
1. Guard: if `estimates_config_<TAXYEAR>.json` is missing, email Gabriel "QUESTIONS FOR GABRIEL — no estimates config for TY<TAXYEAR>; copy last year's file and update prior-year tax from the filed returns" and stop.
2. Run:
   `C:/Users/Owner/AppData/Local/Programs/Python/Python313/python.exe estimate_check.py --config estimates_config_<TAXYEAR>.json --ledger estimates_ledger.csv --asof <run date> --out "..\outputs\<run date>_EstimatedTax_Check_v01.md"`
   Exit 1 means the next installment needs a payment; that is the normal case, not a failure. Exit 2 = input problem: report it.
3. If the config's prior-year figures are still marked DRAFT in its `source` field and the filed returns now exist in `Eric & Becca\`, add to QUESTIONS: "update prior_year_total_tax to the filed figures".
4. Email via Outlook COM: `powershell -File C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1` TO `ggoldberg@oxfordra.net` ONLY.
   Subject: `Estimated tax — pay $<federal next-due amount> federal / $<MD amount> MD by <due date> (<run date>)`.
   Body: the report's "Next due" lines for each jurisdiction, then the full report attached, then QUESTIONS FOR GABRIEL. On a non-zero exit: retry once, then record the failure loudly in the Notion completion row; do not halt.
5. Completion row: append a one-line status to the Operations Hub (`32b6ecd8…`) automation log per the fleet convention. Notion create without a page ID: look under the known parent before any retry (register-scheduled-task step 3, rule B).

## Never
- Never fabricate a payment, a prior-year figure or a projection driver. Missing data goes to QUESTIONS FOR GABRIEL.
- Never recommend paying more than the safe harbor. The stated purpose of this task is to stop idle overpayments ($220K / $173K / $25K in TY2023–TY2025).

## Siblings
Projection drivers come from `ORA_DeprSchedule_Portfolio_v1.0.xlsx` (Summary, "Federal depreciation reaching the 1040") and the TaxNOI action plan; update the config when either changes.
