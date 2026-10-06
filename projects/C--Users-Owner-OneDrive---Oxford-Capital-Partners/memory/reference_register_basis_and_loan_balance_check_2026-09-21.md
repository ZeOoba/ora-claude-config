---
name: reference-register-basis-and-loan-balance-check-2026-09-21
description: "Notion Property Register convention (Oxford-share basis, external loans linked), how tenants and loans are linked, and the monthly loan-balance check (calculator, terms file, task). Decided by Gabriel 2026-09-21."
metadata:
  node_type: memory
  type: reference
  originSessionId: cef05059-e4d1-433f-a9f0-1cd8455aefdb
---

**Register value/debt basis (Gabriel, 2026-09-21).** The Property Register shows ORA's **Oxford share**, matching the workbook's external-LTV method. Red Branch is $8,480,000 (was the 100% $16,960,000) and Broadway $2,730,000 (was $5,460,000); Total SF and tenant SF stay at 100% (physical). Only **external, third-party loans** are linked to Register rows (Banwick + Morrison, 29000 Information Lane, 3540 E 5th, 9050 Red Branch at ORA's 50% share). Internal and affiliate loans (Rarig, Livingston, Northwood/EGFLLC, EGFLLC-from-Oxford, Muirkirk-from-EG) stay unlinked because the Register LTV formula does not separate internal from external debt; receivables (Restoration Church note, 610 Northampton / 485 S. Walnut) are never linked to a property.

**Linking rules.** Every live Tenant DB row (Row Retired != YES) is linked to its Register row by address (42 + 96 = 138 rows on 2026-09-21); retired rows stay unlinked. Set the relation from the Register side (`Tenants` array). Columbus Suburban Construction stays LIVE in the Tenant DB for the collections claim but is deliberately unlinked so occupancy excludes it.

**Sepich split.** The 8-parcel aggregate is two rows: Banwick + Morrison (Symetra collateral, $6.2M C&W appraisal) and Zettler + Sepich Ln + 4595-4601 E 5th (value is a residual of the workbook aggregate, not an appraisal).

**Loan balance check.** `~/.claude/maintenance/loan_balance_check.py` recomputes expected balances from `~/.claude/data/loan-terms.json` (lender schedules parsed to lookup tables for Symetra x2 and Park National; documented anchors for Red Branch and Restoration; interest-only for 610 Northampton). Tests: `maintenance/_tests/test_loan_balance_check.py` (16 pass). Monthly CC-fleet task `ora-loan-balance-check` (21st, 11:35 ET, report-only, emails ggoldberg only) runs it against the Notion Loans DB. The terms file is refreshed ONLY from lender documents in a supervised session. The formula (monthly 30/360, r = rate/12) reproduced Symetra and NorthMarq schedules to the cent, but Park National uses 365/360 so it is a lookup, never a formula.

**Why:** the Loans DB held balances up to five payments stale, and the Register mixed 100% values with ORA-share debt. **How to apply:** before quoting an LTV or a balance, use the Oxford-share value with an external loan, or the lender schedule. Related: [[reference_corporate_settlement_folder_and_fact_base_gap]]; open items OI-337, OI-338 in `open-items-tracker.md`.
