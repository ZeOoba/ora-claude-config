# MISSION: H6 / I2 — Warehouse → client Zod read boundary (the structural fix)

You are implementing **H6** (audit finding `warehouse-read-boundary-bypasses-contracts`, severity HIGH; plan initiative **I2**) on the ORA command center. This is a **behavior-preserving structural refactor**: make every warehouse→client analytics payload cross a Zod contract, so the client stops re-declaring engine types and casting raw JSON. It is the structural blocker the evaluation flagged for cleanly absorbing future engines (refi/forecast/capital-allocation).

This task was deliberately deferred from a large audit-remediation campaign (7 prior fixes merged: H4/H5/H2/H7/B2/B3 + the calibration log; H3/B5 just landed) to its own dedicated session because it is multi-file and shares hot files with an active parallel session. Treat it as **L4 (refactor) with an L3 build flavor** — announce the lane, then proceed.

---

## 0. CONTEXT YOU MUST LOAD FIRST

Load and obey: global `CLAUDE.md`, the auto-loaded session context, `memory/rules.md`, the Engineering OS lane doctrine, and the project memory **`memory/cc-autonomous-audit-pr28.md`** (the full history of this campaign — what's done, the ratifications, the B1 repo-exemption). Everything here is subordinate to the Hard Invariants.

**Repo:** `C:/Users/Owner/oxford-command-center` · remote `ZeOoba/oxford-command-center` (PRIVATE, single-owner). TS/React+Vite front-end over a `server/warehouse` better-sqlite3 layer. Pushing + opening a PR is normal git surface (NOT a deploy).

**Reference artifacts (read these — they ground the work):**
- The audit report: `docs/superpowers/specs/2026-06-13-cc-audit-report.md` (finding H6).
- The hardened plan, initiative **I2**: `docs/superpowers/plans/2026-06-13-command-center-hardened-plan.md` (the sequencing + hot-file schedule).
- The **proven reference pattern**: `src/contracts/acquisition.ts` + `server/warehouse/acquisition.ts` — `AcquisitionScore` is a Zod schema, the engine returns it, and `scoreAcquisition` ends with `AcquisitionScore.parse(result)` before returning. Mirror this exactly for the warehouse engines.
- The standing rule you are enforcing — `architecture/coding-standards.md`: *"All server-to-client data must cross through a Zod schema in `src/contracts/`. Never pass raw JSON to the client as an implicit type. Use Zod `.parse()` at boundaries."* The warehouse read path violates this; H6 fixes it.

---

## 1. THE EXACT FINDING (verify against live code before acting — file:line may have drifted)

- **`src/modules/intel/analytics-hooks.ts`** (~lines 10–167) openly comments its response interfaces "mirror the engine return types verified against source" and **re-declares**, with no shared source: the enums `HealthBand` / `AttentionBand` / `CapitalAction` / `AnomalySeverity` / `AnomalyKind` / `Quartile` / `NumericMetricKey`, and the payload interfaces `PropertyScore` / `PeriodMetrics` / `GrowthPoint` / `SinceAcquisition` / `NoiDriver` / `NoiDecomposition` / `AnomalyFlag` / `MetricBenchmark` / `PropertyRank` / `PmScorecard`. The client receives every payload through **`fetchJson<T>` casts** (in `./hooks`) — an unchecked assertion, not a parse.
- **`server/warehouse/api.ts`** (~lines 150–215) emits every analytics route via raw `c.json(...)` with **NO output schema**. The analytics GET routes are roughly: `/analytics/metrics` (`propertyPeriodMetrics`), `/analytics/growth` (`growth` + `sinceAcquisition`), `/analytics/drivers/:propertyId` (`noiDecomposition`), `/analytics/anomalies` (`detectAnomalies`), `/analytics/benchmarks` (`benchmarkMetric` + `rankProperties`), `/analytics/scores` (`scoreProperties`), `/analytics/pm-scorecards` (`pmScorecards`), and `/noi` (`noiMatrix`). VERIFY the exact route list + envelope shapes (`{ metrics: [...] }`, `{ matrix: [...] }`, etc.) by reading the file.
- The engine return types live in TS in `server/warehouse/{scores,metrics,benchmarks,growth,drivers,anomalies,queries}.ts` — but as plain TS types/interfaces, **not** Zod schemas (unlike `acquisition.ts`). `src/contracts/warehouse.ts` already holds the WRITE-side contracts + the `CalibrationVerdict`/`CalibrationOutcome` schemas (from the calibration log — **leave those untouched**).

**The fix (from the finding + plan I2):** promote the engine return types into Zod schemas in `src/contracts/warehouse.ts`, have the server engines + `api.ts` `.parse` before `c.json` (mirroring `acquisition.ts`), and have `analytics-hooks.ts` import the `z.infer` types and `.parse` responses instead of casting — then **delete the hand-redeclared interfaces**.

---

## 2. APPROACH (sequenced per plan I2 — do it in this order)

1. **M4 is ALREADY DONE (PR #45, merged `fddee45`) — do NOT redo it.** `CapitalAction` is now a single `z.enum` in `contracts/warehouse.ts` (matching the `Classification` pattern), re-exported by `server/warehouse/intel-config.ts` + `src/modules/intel/analytics-hooks.ts`. Your first step is to **promote the REMAINING shared enums the same way** (`HealthBand`, `AttentionBand`, `AnomalySeverity`, `AnomalyKind`, `Quartile`, `NumericMetricKey`) — a `z.enum` in `contracts/warehouse.ts`, re-exported from both old sites — as a **typecheck-only commit** before the payload schemas. **Gotcha M4 hit (avoid it):** a `export type { X } from '…'` re-export does NOT put `X` into the file's local scope, so a file that USES the enum locally (e.g. `analytics-hooks.ts` in a `PropertyScore` field) needs a top-level `import type { X } from '@contracts/warehouse'` PLUS a plain `export type { X };` — not a bare `export … from`.
2. **Promote the payload schemas.** For each analytics return type, add a Zod schema to `contracts/warehouse.ts` (`PeriodMetricsSchema`, `PropertyScoreSchema`, `GrowthPointSchema`, `SinceAcquisitionSchema`, `NoiDriverSchema`, `NoiDecompositionSchema`, `AnomalyFlagSchema`, `MetricBenchmarkSchema`, `PropertyRankSchema`, `PmScorecardSchema`, plus per-route envelope schemas). Export `z.infer` types.
3. **Make the engines the source of truth.** In each `server/warehouse/{engine}.ts`, replace the hand-written return type with `z.infer<typeof XSchema>` (import from contracts) so the engine and the contract can never drift. Do NOT change the engine LOGIC or output VALUES.
4. **Parse at the server boundary.** In `api.ts`, wrap each analytics response in `Schema.parse(...)` before `c.json(...)`, exactly like `AcquisitionScore.parse`. A parse failure is a real server bug surfaced (it should never fire if the schemas match the engines).
5. **Parse at the client boundary + delete redeclarations.** In `analytics-hooks.ts`, import the `z.infer` types + the schemas from contracts, replace every `fetchJson<T>` cast with a parse of the response, and **delete all the hand-redeclared enums/interfaces**. Keep the `WarehouseUnavailable`/503 handling intact.

---

## 3. THE CRITICAL CONSTRAINT — behavior-preserving (this is a refactor, not a data change)

The analytics data **shapes and values must NOT change** — the client renders them today and the schemas must match the CURRENT output **exactly** (no field added, dropped, renamed, reordered-into-required, or loosened to `any`/`.passthrough()` to "make it pass"). If a schema doesn't match the engine output, **fix the schema to match reality**, never the engine.

**TDD discipline for a refactor:** write tests FIRST that pin the contract ⇄ engine fidelity — for each engine, build a tmpdir-sqlite warehouse (copy the pattern from `tests/unit/warehouse-actions.test.ts`), run the engine, and assert `Schema.parse(engineOutput)` succeeds and round-trips identically (`parse(x)` deep-equals `x`). Watch them fail against missing schemas, then add the schemas. Also assert each `api.ts` route's parsed envelope matches the engine output shape. The existing analytics tests + the e2e smoke test are your regression net — they must stay green (the rendered UI is unchanged).

---

## 4. EXECUTION — use the proven adversarial workflow

Prior fixes in this campaign used an **implement → 3-lens adversarial verify → harden** workflow (the same `~/.claude/workflows/` pattern; reusable scripts `cc-audit-army.js`/`cc-eval-plan-premortem.js` live there). It repeatedly caught real defects the implement pass missed (a backfill straggler on H2, a manual-override regression on H3, a contract-fixture break on B5). **Use it here** — H6 is the riskiest of the set. Suggested verify lenses:
- **schema-fidelity**: does each Zod schema EXACTLY match the current engine output — every field, nullability, enum member — with nothing loosened (`any`/`passthrough`/`optional` where the field is always present)? Diff each schema against the engine's real output on a seeded DB.
- **parse-safety / completeness**: does EVERY analytics route `.parse` before `c.json`, and does the client `.parse` every response with ZERO remaining `fetchJson<T>` casts and ZERO hand-redeclared interfaces left in `analytics-hooks.ts`? Grep for stragglers (other consumers, `as` casts).
- **regression**: do the existing analytics/e2e tests pass unchanged (UI identical)? Is the engine LOGIC untouched (only types)? Is `CapitalAction` now single-sourced everywhere?

This is financial-decision-adjacent (these payloads feed capital-allocation surfaces), so the adversarial pass is **mandatory** per the Engineering OS financial-code rule.

---

## 5. HARD CONSTRAINTS (non-negotiable)

- **Isolated worktree, single-writer.** Claim a fresh worktree off the LATEST `origin/main` (`git fetch` first; `git worktree add <path> -b feat/h6-warehouse-zod-boundary origin/main`). Never build on the shared checkout.
- **HOT FILES — collision-aware.** `server/warehouse/api.ts` AND `src/contracts/warehouse.ts` are shared with an **active parallel "acquisition Workbench" session**. The plan mandates ONE writer per hot file per window. So: **work fast, rebase frequently** (`git fetch` + `git merge origin/main` between steps), land the M4 enum commit early, and keep the PR moving. If the parallel session pushes a conflicting `api.ts`/`warehouse.ts` change, rebase and re-verify rather than force anything. Check open PRs + recent commits on those two files before and during the work.
- **DO NOT touch governors** (Hard Invariant 4): `server/warehouse/capital-config.ts` (DSCR 1.25 / LTV 0.40), `config/acquisition-ruleset.v1.json`, `server/warehouse/intel-config.ts` weights — all ratified. H6 touches none of them.
- **DO NOT re-flag confidential terms.** B1 is an owner-ratified exception: confidential deal terms may live in `src/data/seed-deals.ts` in this private repo. The egress guard still bars public surfaces. Don't touch or flag it.
- **Leave the calibration contracts alone.** `CalibrationVerdict`/`CalibrationOutcome`/`InputsVersion` schemas in `contracts/warehouse.ts` are recent and additive — don't disturb them; append the new analytics schemas near the other read-side types.
- **No dev/preview server** — `npm run dev`/`preview` holds the warehouse SQLite WAL lock and is forbidden; verify via vitest + tmpdir sqlite only. Stop any process you start before returning.
- **Done = TDD · typecheck 0 · lint 0 · `npm run governance` ✔ · full `npm run test` green** (the harness now runs per-file-isolated + order-independent, so the suite is reliable) · independent adversarial review · **evidence (pasted command output) before any "done" claim** · smallest behavior-preserving change.

---

## 6. LAND IT

- Commit in logical steps (M4 enum as its own typecheck-only commit first, then schemas+server parse, then client parse+delete). Descriptive messages; end with `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.
- Push to `ZeOoba/oxford-command-center`; open a **draft PR** NON-INTERACTIVELY: `gh pr create --draft --base main --title "..." --body-file <path>` (NEVER bare `gh pr create --draft` — it hangs on a TTY prompt).
- **Poll CI with a real bound** (`gh pr checks` has no `--timeout`): a bounded non-watch loop (`gh pr checks <pr>` every ~20s up to a hard cap), then squash-merge (`gh pr merge <pr> --squash --delete-branch`) only on observed-green CI. Never self-deploy.
- Update `memory/cc-autonomous-audit-pr28.md` (mark H6 done) when it lands — that closes the entire audit backlog.

## 7. DONE DEFINITION

Every warehouse analytics route returns a `Schema.parse(...)`-validated payload; `analytics-hooks.ts` imports `z.infer` types from `contracts/warehouse.ts` and parses every response with **zero hand-redeclared interfaces and zero `fetchJson<T>` casts**; `CapitalAction` (and the other shared enums) are single-sourced in contracts; the data shapes/values are byte-identical to before (UI unchanged); governance/typecheck/lint/test green; the adversarial review STANDS; CI green; squash-merged. The `coding-standards.md` "contracts are the only typed boundary" invariant is now actually enforced on the read side — and the planned engines can absorb cleanly.
