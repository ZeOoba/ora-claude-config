---
name: refute-gate-excludes-server-workbook
description: "The financial-code path scope has now gone stale TWICE (2026-07-24 warehouse files, 2026-08-11 server/workbook) — never trust a path-scoped git log returning empty; diff it against an unscoped log first"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 45979807-1a58-4473-b289-45e88fddcac4
  modified: 2026-08-11T22:18:29.162Z
---

**FIXED 2026-08-11** (both copies), but the *pattern* is what matters and it will recur.

`isFinancialSourcePath` in `scripts/check-refute-required.ts` (oxford-command-center) covered `src/analytics/`, `server/warehouse/`, the financial contracts, `server/overlay.ts` and two `src/brain` files — but **not `server/workbook/`**, even though `server/workbook/parse.ts` and `debt-service-crosscheck.ts` both sit in the `annualDebtService` chain feeding `server/warehouse/debt-scoring.ts` (DSCR) and `src/analytics/engine.ts`. The `ora-financial-code-integrity-sweep` SKILL.md scope list had the identical hole. Three commits touching the DSCR denominator (9ab137d, 59d1995, b9a58c2) merged without the gate ever requiring a refute trailer.

Fixed in commit `8da8223` (gate, + tests) and in the sweep's SKILL.md the same day.

**Why this recurs:** 2026-08-11 was the SECOND occurrence. The 2026-07-24 rebuild widened `warehouse` from a file list to a directory glob after the Debt & Maturity module landed off-list — but never asked which *other* directories hold financial code. The scope enumerates directories that existed when it was written, so a NEW financial directory is invisible by default, which is the opposite of the stated intent. Expect a third occurrence the next time financial code lands in a new directory.

**How to apply:** on any financial-code sweep, never trust a path-scoped `git log` that returns empty. Run the log WITHOUT path filters first and diff the two — commits in the window plus an empty scoped log means **the scope is stale, not the week clean**. On 2026-08-11 the scoped log was empty while four financial commits (900 insertions, incl. a 748-line new debt module) sat in the window; a literal reading would have reported CLEAN with a HIGH and three MEDIUMs present. The sweep's step 2a now mandates this two-log comparison. Related: [[verified-null-vs-inferred-null]], [[absence-claims-need-verification-before-building]], [[feedback-refute-pass-proactive-default]].
