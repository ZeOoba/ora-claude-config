---
name: reference-warehouse-basis-parsing
description: "Where each PM platform states accounting basis in its P&L export, and which ORA entities keep accrual vs cash books"
metadata: 
  node_type: memory
  type: reference
  originSessionId: cf99265a-5229-4f18-8517-6d992070b4bc
---

How the oxford-command-center warehouse recovers accounting **basis** from P&L exports, and the firm's actual book-basis split (verified 2026-06-13 closing the 8/32 unknown-basis gap; parser: `server/warehouse/parse/qb-excel.ts`). Basis matters because `scores.ts` G3 benchmarks each property ONLY against same-basis peers — a wrong/missing basis distorts the PM scorecard / capital-allocation health score.

**Where each source states basis (the parser reads all four):**
- **QuickBooks (in-cell)** — period header line `01/01/24 - 12/31/24  (cash basis)`. Most QB files.
- **QuickBooks Desktop "stripped" exports** — basis is in the Excel **PRINT HEADER** (`ws.headerFooter.oddHeader`, e.g. `&8 Accrual Basis&C…`), NOT in any cell. The row scan never sees it; the parser must read `headerFooter`. Header label `Jan - Dec 24`, no in-cell token. **This is the non-obvious gotcha** — a QB Desktop export can look basis-less while stating it in the print header.
- **Yardi** — metadata row `Book = Cash`.
- **AppFolio** — NO explicit basis token at all; the report **TYPE** is the signal: an AppFolio **"Cash Flow"** statement is cash-basis by definition (lines are cash receipts/disbursements). Parser infers `cash` from the row-1 title only when basis is otherwise unknown.

**ORA portfolio book-basis split (P&L exports, 32 committed imports):**
- **ACCRUAL** — **55 New Plant Ct (entity "EGFLLC" = Eric Goldberg Family LLC)** and **1851 South Club Solar, LLC**. Both confirmed by the print-header "Accrual Basis" token AND (55 New Plant) Depreciation/Amortization in the body. 1851 Solar is a rooftop solar PPA with no real estate (`rentableSf: null`).
- **CASH** — the rest of the portfolio P&Ls (1100 Rarig, 3540 E 5th, FVC, Yardi MD properties, AppFolio Northwood, etc.).

**Open follow-up (task_363d08be):** because 1851 Solar is SF-less, labeling it accrual pools it with 55 New Plant in the ratio-based `expenseEfficiency` cohort in `scores.ts`, giving 55 New Plant a spurious +5.0 efficiency (sub-threshold today). Fix = exclude SF-less/non-real-estate entities from efficiency cohorts. See [[pfi-build-canon]].
