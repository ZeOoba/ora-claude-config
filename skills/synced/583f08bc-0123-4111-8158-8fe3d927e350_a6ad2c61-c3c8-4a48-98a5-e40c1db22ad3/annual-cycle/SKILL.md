---
name: annual-cycle
description: Year-end and annual planning cycle for Oxford Realty Advisors — twin to monthly-close. Use when the user mentions: year-end, annual close, annual budget, year in review, tax planning, annual report, 1099 cycle, K-1 prep, audit prep, year-end distribution, fiscal year close, annual cycle, or any task related to the firm's annual rhythm. Distinct from portfolio-reporting, which owns investor and portfolio reporting deliverables. Powers the ora-annual-budget-kickoff (Nov 1) and ora-year-end-review (Dec 15) scheduled tasks. v1.0
license: ORA Internal
---

# Annual Cycle

Coordinate the firm's annual rhythm: budget kickoff, year-end review, tax planning, audit prep, K-1 cycle, and LP year-end communications.

## Scope

Calendar-year and fiscal-year activities that occur on an annual basis. Excludes monthly close (see monthly-close skill). Quarterly LP letter previously routed to investor-relations, retired 2026-09-09 (Gabriel, in-turn) — no replacement owner assigned yet; treat as manual until re-routed.

## Triggers

Annual budget assembly, year-in-review, year-end tax planning, K-1 distribution cycle, annual audit prep, year-end LP distribution, fiscal-year financial close.

## Cycle Calendar

| Month | Activity | Trigger |
|-------|----------|---------|
| September | Tax planning prep — projected K-1 income by LP, distribution headroom for tax payments | manual / IR review |
| October 31 | Cowork audit refresh recommended | quarterly cadence |
| November 1 | Annual budget kickoff | ora-annual-budget-kickoff |
| November 30 | Vendor concentration audit, contract renewals review | manual via vendor-management |
| December 1–14 | Year-end distribution decision; final operating budget review | manual |
| December 15 | Year-in-review draft | ora-year-end-review |
| December 31 | Fiscal year close | monthly-close + manual |
| January 15 | 1099 prep deadline (mailing Jan 31) | accounting + vendor-management |
| February | LP K-1 prep with CPA | manual (investor-relations retired 2026-09-09) |
| March 15 | K-1 issuance to LPs (extended via 7004 if needed) | manual (investor-relations retired 2026-09-09) |
| April | LP communications post-K-1; tax-related Q&A | manual (investor-relations retired 2026-09-09) |

## Standard Workflows

### Annual Budget Assembly (November)
1. Pull TTM and 24-month P&L by property.
2. Apply rent steps from leases (deterministic).
3. Apply renewal probability × forecasted renewal rents (probability-weighted).
4. Layer in capex from capex-budgeting skill.
5. Apply OpEx growth assumptions (insurance, tax via tax-appeal pipeline, R&M).
6. Build per-property budget xlsx; consolidate to fund level.
7. Output: FY[YYYY+1] Operating Budget (xlsx) with executive summary memo (DOCX).

### Year-In-Review (December)
1. Full-year actuals vs. budget by property and consolidated.
2. AUM trajectory: starting AUM, deals closed, NOI growth, ending AUM.
3. Capital deployed YTD, capex completed.
4. LP distributions YTD; capital calls completed.
5. Forward look: next-year pipeline, capital plan, target deployment.
6. Output: Year-In-Review (DOCX, ORA Style) for LP communication and internal archive.

### Year-End Tax Planning (Sept–Dec)
1. Project taxable income per LP based on YTD activity and Q4 plan.
2. Surface tax-loss harvesting candidates (cost segregation, bonus depreciation, 1031 candidates).
3. Coordinate with CPA on 1031 timing if dispositions planned.
4. Output: tax planning memo (DOCX) for Gabriel.

### K-1 Cycle (Feb–March)
1. Coordinate with CPA on entity-level returns.
2. K-1 cover letter per LP — investor-relations (retired 2026-09-09) previously owned this template; use document-assembly or draft manually until re-routed.
3. K-1 distribution via secure channel; track receipt.

## Outputs

- All deliverables follow ORA Institutional Style Guide v1.0+
- File naming: YYYYMMDD_[Activity]_FY[YYYY]_v##.{docx,xlsx}
- Mirror to SharePoint /Annual/[FY]/

## Boundaries

- Tax planning is advisory only; CPA executes.
- LP communications require Gabriel approval before send.
- 1031 exchanges require explicit Gabriel decision.

## Dependencies

- monthly-close skill (rolls up monthly into annual)
- portfolio-reporting skill (year-end metrics)
- capex-budgeting skill (capital plan)
- ~~investor-relations skill (LP communications)~~ — retired 2026-09-09, no replacement assigned
- tax-appeal skill (tax assumptions)
- docx, xlsx, document-assembly skills
