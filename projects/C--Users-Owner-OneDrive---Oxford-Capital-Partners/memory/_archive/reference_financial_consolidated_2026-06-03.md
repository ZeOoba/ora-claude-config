---
name: financial-modeling-conventions
description: "Gabriel's approved default assumptions, model structure preferences, and calculation standards"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 8ffab475-017d-4acd-9f70-f4496936d089
---

# ORA Financial Modeling Conventions

## Hard Rules (from CLAUDE.md / investment criteria)
- DSCR ≥ 1.25× — hard acquisition governor (canonical per CLAUDE.md; corrected from 1.75 → 1.25 on 2026-06-03, G5)
- LTV ceiling: 40% self-imposed max
- Every deal model: NOI, Cap Rate, Yield on Cost, Levered/Unlevered IRR, Equity Multiple, DSCR
- Every acquisition: replacement cost analysis
- Rent comps denominated $/SF NNN unless otherwise specified
- All models include sensitivity tables
- 10-year projection horizon, fully dynamic assumptions

## Default Assumptions (update as Gabriel validates)

*These are starting points. Gabriel may override per deal. Update when he does.*

| Assumption | Default | Last Validated |
|-----------|---------|---------------|
| Vacancy/Credit Loss | — | pending |
| Annual Rent Escalation | — | pending |
| Expense Growth | — | pending |
| TI Allowance (new) | — | pending |
| TI Allowance (renewal) | — | pending |
| Leasing Commissions (new) | — | pending |
| Leasing Commissions (renewal) | — | pending |
| CapEx Reserve $/SF | — | pending |
| Exit Cap Rate Spread (vs entry) | — | pending |
| Replacement Cost Range | $85–$120/SF | 2026-04-09 |

## Model Structure Preferences
- Excel (.xlsx) is the single source of truth — never build financial models in markdown or other formats
- Assumptions on a dedicated tab, all inputs color-coded (blue = input, black = calculated)
- Summary tab with key metrics dashboard
- Sensitivity tables on NOI, exit cap, and interest rate
- Cash flow waterfall: gross potential rent → vacancy → EGI → expenses → NOI → debt service → BTCF

## Entity / Debt Conventions
- QuickBooks Desktop manages ~20 LLC company files
- Each property has its own LLC entity
- Debt service calculated per-entity

## History
- 2026-04-09: File created with baseline conventions from CLAUDE.md. Specific assumptions pending Gabriel's validation.
