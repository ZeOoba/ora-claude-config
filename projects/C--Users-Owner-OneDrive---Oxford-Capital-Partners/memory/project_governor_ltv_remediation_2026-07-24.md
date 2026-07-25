---
name: governor-ltv-remediation-2026-07-24
description: "PR #233 shipped all 7 sweep defects + 4 review-found fix defects; 3 open residuals incl. debt-scoring per-property ltv gap"
metadata: 
  node_type: memory
  type: project
  originSessionId: f2fb7cb1-e49a-4eb1-a9d3-c6a401ea51fb
  modified: 2026-07-24T23:53:35.430Z
---

# Governor-LTV False-Clearance Remediation (PR #233, 2026-07-24)

**Status: SHIPPED** — branch `fix/governor-ltv-false-clearance`, commit `50ffdec`, [PR #233](https://github.com/ZeOoba/oxford-command-center/pull/233), Refute-Reviewed trailer. 3062/3062 tests, typecheck 0, lint 0.

Full narrative: [[event-log]] 2026-07-24 entry. Sweep that found it: ora-financial-code-integrity-sweep weekly run, Notion Ops Hub row `3a76ecd8-9e59-8181-8ae4-fc133eeb1b96`.

**Why:** 2 of the 7 sweep defects were false clearances of the Hard-Invariant-4 40% aggregate-LTV ceiling — worst failure direction in the codebase. Gabriel ordered fixes same-day, then "committed/PR then pick up the low-LTV structural fix."

## OPEN residuals (verify current state before acting — PR may have merged/changed)

1. **debt-scoring.ts per-property ltv gap** — the same raw `ltv` column feeds `scoreDebtPositions`' ltvCeiling-breach + cash-out gate unguarded; a rate-cell column drift yields per-property "governors clear" signals feeding capital-allocation.ts. Round-7's `ltv==rate` collision check covers `computePortfolioAggregateLtv` ONLY. Spawned chip: `task_fe4b5d56`.
2. **refusedEmptySupersede invisible on the automated path** — POST /snapshot response and the backfill CLI surface a shrinkage-guard refusal, but `server/index.ts`'s reload hook only console.warns; a refusal freezes the book at its prior state with nothing downstream distinguishing "refused/stale" from "healthy". Reviewers flagged twice.
3. **Pre-existing lease-count reconcile mismatch** (exp 137, got 138) on origin/main — unrelated to this work, reproduced on clean main both before and after upstream `227bfd8` (which fixed lease-id stability but not this count).

## How to apply

- The shrinkage guard's semantics after 3 corrections: NET count shrinkage (written ∪ preserved-by-F-stale vs prior active), floor 2 rows, inclusive ≥50%, all-or-nothing refusal, `allowEmptySupersede` bypass. Do not "simplify" it back to id-overlap or raw incoming counts — each was a demonstrated defect.
- The LTV `[0,1.5]` bound lives ONLY on `BoundedLoanForSnapshotWrite` in debt-api.ts. Never move it to the shared `Loan` schema — `PortfolioSnapshot.parse()` validates all three writers and one bad cell would fail the entire snapshot.
- `RATE_LTV_COLLISION_EPSILON` exact-collision check reads `rate` internally in debt-maturity.ts; `rate` must never appear in that module's return shapes (confidentiality contract, pinned by test).
