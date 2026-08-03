---
name: project_northwood_egflc_loan_miscategorized_2026-07-27
description: "Master Workbook's new $2.8M Northwood loan is booked as external debt but is actually internal (owed to EGFLLC) — inflates workbook's own LTV cells until Eric/Gabriel fix it"
metadata: 
  node_type: memory
  type: project
  originSessionId: ba3393eb-867c-4773-be60-0095ba1567b2
  modified: 2026-08-03T23:58:46.948Z
---

The Master Workbook's Loan Index and External Loans Summary carry a new $2,800,000 loan against **2203-2207 Northwood Dr** (6.99%, interest-only, matures 2031-10-01), entered under "WE PAY — Oxford Is Borrower" with counterparty labeled "2203 Northwood, LLC (2900 Loch Raven LLC)." Gabriel confirmed 2026-07-27 this loan is actually **internal — Northwood is paying EGFLLC**, not a third-party lender. It is not yet entered anywhere in Portfolio Summary — Internal (Internal Loan Journals).

**Why this matters:** because the loan sits in the External sheets, 00_Home's live "Portfolio LTV" cell and External Loans Summary's own net-external LTV cell both compute as if it were external debt — overstating gross-external LTV at 22.90% (true, flat figure ≈18.1%) and net-external LTV at 19.86% (true, flat figure ≈15.1%). Total debt ($17,983,618) is unaffected since it's just in the wrong bucket. DSCR (4.32×) is unaffected — internal loans are excluded from DSCR by convention ([[standards]] Entity/debt conventions section, added 2026-07-27) — so no DSCR correction is needed regardless of which sheet the loan lives in.

## ✅ RESOLVED 2026-08-03 — the workbook is now correct; stop applying the manual back-out below.

Gabriel authorised direct Excel COM writes and ruled the two open questions: the interest groups with H6 on the **income** side of `Portfolio Summary — Internal!C16`, and the loan gets **its own journal** like every other internal loan. Applied: new `Rate_Northwood_EGFLLC` (6.99%) on Assumptions · new **"Northwood FROM EGFLLC"** accrual journal (modelled on the 2203 FROM EGFLLC interest-only precedent) · PSI row 10 with a LOOKUP-driven balance · `C16` extended to `=(H5+H6+H10)-(H7)` · Loan Index internal row · `tblExportLoansInternal` extended · external rows deleted from Loan Index and ELS.

**Both published LTV cells self-corrected — gross-external 23.26% → 18.41%, ELS net-external 20.17% → 15.32%.** Total Debt unchanged at $17,555,291 (bucket move only; note the level itself was restated from $17,940,509 earlier that day when WBC-008 removed a separate 3883 double-count). DSCR 4.25× untouched. Verified: 0 error cells across all 51 sheets. **Any consumer reading the workbook's own LTV cells can now trust them directly.**

**Still open (WBC-010) — the accrual start, and a question behind it.** Investigation on 2026-08-03 established: the loan was entered into the workbook **2026-07-17 between 13:07 and 19:43** (consecutive backups either side); **no Claude Log turn records adding it**; and there is **no $2,800,000 movement in any entity across all 21 months of Cash Data** — no funding event is recorded anywhere. A hypothesis that it duplicated the existing `2203 FROM EGFLLC` loan (same property, same EG Florida LLC counterparty) was **tested and refuted**: that loan is the original acquisition financing, opening 12/9 at $2,757,016 against the 2024-10-03 acquisition, running continuously through Aug-2026 and never moving by more than $500k, at a different rate (6.00% vs 6.99%) and principal. **They are distinct; internal debt of $7,313,492 is correct as booked.** What is unexplained is a $2.8M advance with no cash movement — and that answer determines the accrual start, which is why WBC-010 cannot be closed by lookup. The journal carries the correct balance with the start deliberately blank rather than invented; nothing downstream is affected, since PSI derives balance and interest independently of the journal dates.

Also: the borrower concentration table now totals 100% rather than 79.15%, so Banwick/Morrison reads 34.9% not 27.66% — a corrected measurement, not new risk (Northwood had sat in the denominator with no row of its own). Full record: [[00_system_of_record]] and the Open Workbook Corrections register (Notion `3b16ecd8-9e59-8153-8c9e-f264e301b3ca`).

---

**Historical record — the state that prevailed 2026-07-27 to 2026-08-03** (verified live against the workbook, `lastModifiedDateTime` 2026-08-02T16:01:17Z — week 2 unresolved). The loan remains in the External sheets, is still absent from Portfolio Summary — Internal, and its LTV cell still reads "- enter value." Current-run corrected figures: external **$10,627,017**, internal **$7,313,492**, total **$17,940,509** (unchanged), gross-external LTV **18.41%** (workbook cell reads 23.26%), net-external LTV **15.32%** (workbook cell reads 20.17%). Re-flagged to Gabriel in the 2026-08-03 ingest alert as a reminder, not a re-litigation of the ruling.

**How to apply:** until Eric/Gabriel move this loan entry into Internal Loan Journals and correct the counterparty label to EGFLLC, any read of the workbook's own 00_Home LTV cell, External Loans Summary's net-external LTV cell, or the External/Internal debt split must manually back out this $2,800,000 from External and add it to Internal before reporting. The `ora-master-workbook-ingest` 2026-07-27 run originally got this wrong (flagged it as external, proposed an incorrect DSCR correction to 3.54×) and had to publish a same-day correction to the Portfolio Intelligence Dashboard (3396ecd8), the 2026-07-26 Knowledge Base snapshot (3aa6ecd8), the DSOR change log (3706ecd8), and send a correction email to Gabriel. Do not repeat that mistake on the next ingest — check whether Eric/Gabriel have since fixed the workbook's own categorization before relying on the live LTV cells again.
