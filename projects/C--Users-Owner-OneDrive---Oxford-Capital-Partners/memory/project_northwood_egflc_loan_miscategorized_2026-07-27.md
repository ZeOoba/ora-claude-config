---
name: project_northwood_egflc_loan_miscategorized_2026-07-27
description: "Master Workbook's new $2.8M Northwood loan is booked as external debt but is actually internal (owed to EGFLLC) — inflates workbook's own LTV cells until Eric/Gabriel fix it"
metadata: 
  node_type: memory
  type: project
  originSessionId: ba3393eb-867c-4773-be60-0095ba1567b2
  modified: 2026-07-27T13:22:28.913Z
---

The Master Workbook's Loan Index and External Loans Summary carry a new $2,800,000 loan against **2203-2207 Northwood Dr** (6.99%, interest-only, matures 2031-10-01), entered under "WE PAY — Oxford Is Borrower" with counterparty labeled "2203 Northwood, LLC (2900 Loch Raven LLC)." Gabriel confirmed 2026-07-27 this loan is actually **internal — Northwood is paying EGFLLC**, not a third-party lender. It is not yet entered anywhere in Portfolio Summary — Internal (Internal Loan Journals).

**Why this matters:** because the loan sits in the External sheets, 00_Home's live "Portfolio LTV" cell and External Loans Summary's own net-external LTV cell both compute as if it were external debt — overstating gross-external LTV at 22.90% (true, flat figure ≈18.1%) and net-external LTV at 19.86% (true, flat figure ≈15.1%). Total debt ($17,983,618) is unaffected since it's just in the wrong bucket. DSCR (4.32×) is unaffected — internal loans are excluded from DSCR by convention ([[standards]] Entity/debt conventions section, added 2026-07-27) — so no DSCR correction is needed regardless of which sheet the loan lives in.

**How to apply:** until Eric/Gabriel move this loan entry into Internal Loan Journals and correct the counterparty label to EGFLLC, any read of the workbook's own 00_Home LTV cell, External Loans Summary's net-external LTV cell, or the External/Internal debt split must manually back out this $2,800,000 from External and add it to Internal before reporting. The `ora-master-workbook-ingest` 2026-07-27 run originally got this wrong (flagged it as external, proposed an incorrect DSCR correction to 3.54×) and had to publish a same-day correction to the Portfolio Intelligence Dashboard (3396ecd8), the 2026-07-26 Knowledge Base snapshot (3aa6ecd8), the DSOR change log (3706ecd8), and send a correction email to Gabriel. Do not repeat that mistake on the next ingest — check whether Eric/Gabriel have since fixed the workbook's own categorization before relying on the live LTV cells again.
