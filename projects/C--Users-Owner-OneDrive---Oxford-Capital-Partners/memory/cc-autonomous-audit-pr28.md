---
name: cc-autonomous-audit-pr28
description: oxford-command-center autonomous audit run (2026-06-13) — draft PR
metadata: 
  node_type: memory
  type: project
  originSessionId: a87ee512-2ea9-49e6-8f01-9181fc28c793
---

Autonomous audit→evaluate→plan→implement run on `ZeOoba/oxford-command-center`, completed 2026-06-14 (started 2026-06-13).

**PR [#28](https://github.com/ZeOoba/oxford-command-center/pull/28) — MERGED 2026-06-14** (squashed to `origin/main` as `4196dd1`, on top of #27's live engine; TA-1 acquisition tests dropped as superseded by #27; pre-push hook later removed via PR #32 per B1) contained:
- Deliverables under `docs/superpowers/`: 37-finding ranked audit, evaluation scorecard, 15-initiative hardened plan (extends the master plan), data-flywheel design, ratification backlog.
- **TA-2** — fix H4 scenario-value basis-mix (`src/analytics/engine.ts`): a Downside scenario could previously *raise* portfolio value / *lower* LTV.
- **TA-1** — additive characterization tests for the acquisition engine + NOI-reconcile DB join (zero production change).
- **Pre-push confidentiality hook** (`scripts/prepush-confidential-scan.mjs` + installer + 12 tests) — closes the gap that allowed audit H1; fail-closed on a real term hit, fail-safe on infra errors, installed into the shared `.git/hooks` (guards every worktree). Install via `npm run hooks:install`.

**GABRIEL'S DECISIONS (2026-06-14):**
- **B1 — DECIDED: KEEP + EXEMPT.** Gabriel chose to keep confidential deal terms in this private/single-owner repo's source (`src/data/seed-deals.ts`). The pre-push confidentiality hook (added in #28) was REMOVED (PR #32) and the repo exempted; no de-commit / history scrub. The `~/.claude/hooks/confidential-terms.json` **egress** guard is UNCHANGED — still bars deal terms from the public site, the `/dist/` mirror, Notion, and Outlook (the egress guard does NOT block internal repo writes/pushes anyway). **Future audits: do NOT re-flag committed deal terms in this repo as a finding — it is an owner-ratified exception.**
- **B4 — DONE: RATIFIED.** Gabriel ratified the acquisition scorecard v1.0 in-session 2026-06-14 (PR #27, `config/acquisition-ruleset.v1.json` `ratification:"ratified"`); engine live (fail-closed). Any future change = a new RULESET_VERSION + fresh Invariant-4 ratification. Do NOT re-ratify or modify.

**Still open:**
- **B2 — DONE** (PR #35, 2026-06-14): comps confidential-egress guard added at the top of `fetchDealComps`.
- **B3 — DONE** (Gabriel ratified Option B 2026-06-14, PR #39): two-tier LTV alert (info above the 40% governor / warning above 65%) + a cross-check test welding `ALERT_THRESHOLDS.ltvGovernor` to `CAPITAL_CONFIG.ltvCeiling` (and dscrWatch↔dscrFloor) so they can't silently drift. The governor constant itself was UNTOUCHED (conditions.ts stays client-pure; cross-check is test-time only).
- **B5 — DONE** (PR #44, 2026-06-14): exposed `floorIndeterminate` as a first-class `AcquisitionScore` field (the engine already computed it; only surfaced via `cappedAtT2`, which misses band-demotions). Purely additive + adversarial refute STANDS.

**Deferred YELLOW fixes (next PRs, each refute-gated):** ~~H2 `/noi` double-count~~ **(DONE PR #37 — coherent-batch NOI; adversarial review caught a backfill-CLI straggler, also fixed)**, ~~H5 noi-variance~~ **(DONE PR #35)**, ~~H6 warehouse-read bypasses Zod~~ **(DONE PR [#46](https://github.com/ZeOoba/oxford-command-center/pull/46) — squash `44f90df`, 2026-06-14)**, ~~H7 benchmarks SF-less~~ **(DONE PR #38)**, ~~H3 approve-path sign-flip~~ **(DONE PR #43 — sideHint constraint + manual-override-wins + gate now exercises approveImport; adversarial review caught & fixed a manual-override regression)**. **AUDIT BACKLOG FULLY CLOSED — all RED/YELLOW findings (H2–H7) + B1–B5 done.**

**H6 — DONE (PR #46, squash `44f90df`, 2026-06-14, fully-autonomous run):** warehouse→client Zod read boundary. Promoted the 10 analytics-engine return types + 7 route envelopes to Zod schemas in `src/contracts/warehouse.ts`; each `/analytics/*` route `.parse()`s before `c.json`; `analytics-hooks.ts` imports the `z.infer` types + parses every response (`fetchParsed`), deleting all hand-redeclared enums/interfaces (11 downstream intel consumers untouched via re-exports). Behavior-preserving; full local gate green (762 tests + 7 new fidelity tests), CI `gate` pass, independent opus adversarial review STANDS (no DEFER findings). Based on the M4 branch (#45, single-sourced `CapitalAction`) to avoid the collision — M4 squash-merged to main as `fddee45` mid-run, incorporated via a clean merge. **Two pre-existing client/server drifts caught & fixed to the engine shape: `PeriodMetrics.basis` and `PropertyScore.benchmarkCohortSize` (engine always emitted both; old client type silently dropped them).** **Scoped-out follow-on (NOT a finding):** `/noi`, `/imports`, `/issues` (served via `hooks.ts`, not `analytics-hooks.ts`) still cast `fetchJson<T>` — a future PR could extend the same boundary. **RESIDUAL-RISK (documented in PR):** server-side `.parse()` makes a future schema-breaking engine change a 500 instead of a silent wrong shape — intended contract enforcement (matches `acquisition.ts`), guarded by the fidelity tests. Test-harness flake fixed earlier by the chip session (per-file isolation #40 + order-independence #42).

**Test-harness flake found during H7 (NOT H7's fault):** `vitest.config.ts` uses `pool:'threads' / singleThread / isolate:false`, so cross-file module-state leakage flakes non-deterministically (observed: `warehouse-reconcile-noi-db.test.ts` ownership-overlay intermittently computed 95000 vs 47500 in the full suite; passed in isolation + on re-run). DBs are per-test tmpdirs → it's shared MODULE state, not a shared DB. Risk: flaky `gate:ci`. Flagged as a separate task.

**Biggest strategic gap (learn-from-data, scored 2.5/10):** calibration log **Phase 1 SHIPPED 2026-06-14** — [PR #34](https://github.com/ZeOoba/oxford-command-center/pull/34): the dated/reproducible verdict-logging foundation (migration 005 `calibration_inputs_version`/`calibration_verdict`/`calibration_outcome`, `server/warehouse/calibration.ts`, fail-open emit hook in `approveImport`; additive, touches ZERO governors). Independent adversarial review caught 3 inputs_version/dedup collisions + a confidence-cap defect — all fixed with repro TDD tests (the fingerprint now folds an ordered classification projection so a mapping reclassification forks the version). **Phase 2+ deferred** (no urgency until ≥1 horizon of outcomes elapses): the resolver, report fn, `/calibration` routes, React panels, offline re-fit script, and the quarterly `ora-calibration-snapshot` scheduled task. Spec: `docs/superpowers/specs/2026-06-13-calibration-log-design.md`.

**Kept for resume:** worktree `C:/Users/Owner/oxford-cc-wt-audit-20260613` (run ledger + intermediate artifacts in its untracked `_run/`).

**Reusable self-audit pipeline** saved to `~/.claude/workflows/` (`cc-audit-army.js`, `cc-eval-plan-premortem.js`, parameterized via `args.worktree`; README there). This is the data-flywheel's recurring re-audit mechanism — run it on a cadence against a fresh worktree. The autonomous driver prompt is `~/.claude/prompts/command-center-autonomous-review-v2.md`.

Single-writer note: a parallel session (`busy-maxwell`) was active on the shared checkout throughout; I stayed isolated in the worktree and never mutated their tree. See [[rules]] (worktree single-writer) and the CC build state docs.
