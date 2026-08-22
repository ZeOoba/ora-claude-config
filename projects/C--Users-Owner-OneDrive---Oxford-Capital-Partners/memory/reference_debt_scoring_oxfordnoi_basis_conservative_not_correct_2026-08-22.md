---
name: reference-debt-scoring-oxfordnoi-basis-conservative-not-correct
description: "debt-scoring.ts's DSCR/debt-yield oxfordNoi fix (9cb6169) is deliberately kept despite evidence its premise is wrong -- it's conservative/fail-safe, not the technically-correct covenant basis"
metadata:
  type: reference
  originSessionId: 6fc6add8-c93f-4640-9f1d-8a6aa6be1ba7
  modified: 2026-08-22T21:54:50.839Z
---

`oxford-command-center/server/warehouse/debt-scoring.ts` computes DSCR/debt yield as `oxfordNoi / annualDebtService` (commit `9cb6169`, 2026-08-22 cc-audit-army fix, independently reviewed APPROVE WITH CONCERNS). The fix's code comment premise — "`debt_positions` carries only Oxford's own debt share on a jointly-owned property, so `annualDebtService` is already an Oxford-share figure" — was checked against actual source documents and **does not hold**.

## What was found

- Only two properties in `property-master.ts`'s `CANON_PROPERTIES` (Gabriel-ratified 2026-06-12) carry `ownershipPct < 1` with real external debt: **9050 Red Branch Rd** and **1900 N Broadway** (both 0.5, both via "Steve She — CRC").
- 9050 Red Branch's external loan (Woodmen of the World, borrower Muirkirk Properties LLC) has a documented **$4,500,000 original principal — the full facility amount**, per the actual Loan Agreement/Assumption and amortization schedule (source: a prior title/loan-diligence register, `loan_terms.xlsx`, not the workbook itself). Nothing in `parse.ts`'s `parseLoans()` (which reads `Loan Index` cells directly) divides by ownership share at ingestion.
- `pfi-build-canon.md`'s own stated design convention is **"100% property-level figures with an Oxford-share overlay"** — i.e., debt and NOI are meant to be tracked at the full property/entity level, with the Oxford-share adjustment layered on top for economic-interest reporting, not baked into the underlying obligation figures.

Taken together: `debt_positions`' balance/payment figures for these properties are very likely **100%-basis (full facility)**, not Oxford-share-only. A covenant-compliance DSCR test conventionally runs on the borrowing entity's full cash flow against its full debt service — matching the **pre-fix** behavior, not the fix's `oxfordNoi / full debtService` pairing.

## Why the fix is being KEPT anyway (Gabriel's ruling, 2026-08-22)

Reverting isn't required because the fix is **provably conservative regardless of which premise is correct**:

```
postfix_DSCR  = oxfordNoi / debtService = ownershipPct * correct_DSCR   (ownershipPct in (0,1])
=> postfix_DSCR <= correct_DSCR, always, for any noi >= 0 and debtService > 0
```

`ownershipPct` is bounded to `(0, 1]` both by the Zod schema (`z.number().gt(0).max(1)`) and by the hardcoded, ratification-gated `CANON_PROPERTIES` roster (today: 1, 0.5, 0.25 only) — so this holds unconditionally in practice, not just in theory. Same proof applies identically to debt yield (`oxfordNoi / balance`).

**Practical consequence:** the fix can only ever produce a false governor-**block** (flagging a property that would truly pass under the correct 100%/100% basis) — it can never produce a false **clearance** of a real DSCR/debt-yield breach. That satisfies Hard Invariant 4's actual concern (never silently clear a real governor breach) even though the number itself is not the textbook-correct DSCR.

## Open item, not urgent

The underlying ambiguity (is `debt_positions` really Oxford-share-only, or full-facility?) is still unresolved and worth a real answer eventually — confirm against the live Master Workbook's `Loan Index`/`External Loans Summary` tabs directly (the M365 connector's full-workbook read truncates before reaching those sheets for this particular file; a scoped/targeted read or a local synced copy would be needed). Low urgency given the fail-safe proof above holds regardless of the answer.

Related: [[project_governor_ltv_remediation_2026-07-24]].
