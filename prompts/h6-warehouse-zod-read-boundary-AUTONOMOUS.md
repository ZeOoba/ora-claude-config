# MISSION (UNATTENDED): H6 / I2 — Warehouse → client Zod read boundary

You are running **FULLY AUTONOMOUS and UNATTENDED**. No human will read your output mid-run, answer a question, grant a permission, or approve a plan. Implement **H6** (audit finding `warehouse-read-boundary-bypasses-contracts`, HIGH; plan initiative **I2**): make every warehouse→client analytics payload cross a Zod contract, so the client stops re-declaring engine types and casting raw JSON. It is a **behavior-preserving structural refactor** — the structural blocker the evaluation flagged for future engines. Land it end-to-end with zero human interaction, or leave a durable, resumable draft PR + blocker if a Hard-Invariant/collision genuinely blocks it.

---

## 0. OVERRIDING PRECEDENCE RULE (read first)

No human will approve, answer, or permit anything. Where any instruction below conflicts with a **Hard Invariant** or a permission gate, **the gate wins**: DEFER the action as a written proposal (in the PR body + `memory/cc-autonomous-audit-pr28.md`) and continue with the safe work. Three things are forbidden:
- **NEVER pause / block / wait for a human.** A "pause for approval" is indistinguishable from a hang. Replace every such instinct with DEFER-WITH-PROPOSAL or a clean blocked-exit.
- **NEVER self-approve a gated action** (absence of objection ≠ permission).
- **NEVER auto-execute a Hard-Invariant action** (governor/financial-constant edit, confidential-term egress to a public surface, oxfordra.net/mirror deploy, scheduled-task registration, external-counterparty send, destructive/irreversible op).

The standing ORA Autonomy "pause-triggers" are SUSPENDED for this run — EXCEPT you still never *execute* a Hard-Invariant action. For any ambiguity that would normally make you ask one question: **do not ask** — pick the most defensible option, label it `[ASSUMPTION: … — rationale]`, log it in the PR body, and proceed.

**DEFINITION OF DONE (machine-checkable):** either (a) the refactor squash-merges to `origin/main` on observed-green CI, OR (b) a genuine unresolvable collision / Hard-Invariant boundary leaves it as a **draft PR with a recorded blocker** in the PR body + the memory file. Either way: a completion notification is sent and no process is left holding the WAL lock. A hang is the only failure mode that is unacceptable.

**Clear `eos-plan-gate` PROACTIVELY (this run makes many edits):** as the FIRST step, write your H6 implementation plan to `docs/superpowers/plans/<date>-h6-zod-read-boundary.md` inside the worktree (this arms the `plan-approved` marker) AND `touch hooks/sessions/<session-id>/override` (resolve `<session-id>` from the current session; sessions dir honors `EOS_SESSIONS_DIR`, else `C:/Users/Owner/.claude/hooks/sessions`). Do NOT loop trying to clear the gate any other way.

---

## 1. CONTEXT (load first)

Obey global `CLAUDE.md`, the session context, `memory/rules.md`, the Engineering OS lane doctrine, and the project memory **`memory/cc-autonomous-audit-pr28.md`** (the full campaign history — 9 prior PRs merged: H2/H3/H4/H5/H7/B2/B3/B5 + the calibration log; the ratifications; the **B1 repo-exemption**). Lane: **L4 refactor / L3 build hybrid** — announce it.

**Repo:** `C:/Users/Owner/oxford-command-center` · remote `ZeOoba/oxford-command-center` (PRIVATE, single-owner). Pushing + a PR is normal git surface (NOT a deploy).

**Reference artifacts (read them):** the audit report `docs/superpowers/specs/2026-06-13-cc-audit-report.md` (finding H6); the hardened plan `docs/superpowers/plans/2026-06-13-command-center-hardened-plan.md` (initiative **I2** + the hot-file schedule); and the **proven pattern** `src/contracts/acquisition.ts` + `server/warehouse/acquisition.ts` (`AcquisitionScore` is a Zod schema; the engine ends with `AcquisitionScore.parse(result)` before returning — mirror this). The rule you enforce: `architecture/coding-standards.md` — *"All server-to-client data must cross through a Zod schema in `src/contracts/`. Never pass raw JSON to the client as an implicit type. Use `.parse()` at boundaries."*

---

## 2. THE FINDING (verify against live code — file:line may have drifted)

- **`src/modules/intel/analytics-hooks.ts`** (~10–167) re-declares, with no shared source, the enums `HealthBand`/`AttentionBand`/`CapitalAction`/`AnomalySeverity`/`AnomalyKind`/`Quartile`/`NumericMetricKey` and the payload interfaces `PropertyScore`/`PeriodMetrics`/`GrowthPoint`/`SinceAcquisition`/`NoiDriver`/`NoiDecomposition`/`AnomalyFlag`/`MetricBenchmark`/`PropertyRank`/`PmScorecard`. The client receives every payload through **`fetchJson<T>` casts** (in `./hooks`) — an unchecked assertion.
- **`server/warehouse/api.ts`** (~150–215) emits every analytics route via raw `c.json(...)` with NO output schema. Routes (verify the exact list + envelopes): `/analytics/metrics`, `/analytics/growth`, `/analytics/drivers/:propertyId`, `/analytics/anomalies`, `/analytics/benchmarks`, `/analytics/scores`, `/analytics/pm-scorecards`, `/noi`.
- The engine return types live as plain TS in `server/warehouse/{scores,metrics,benchmarks,growth,drivers,anomalies,queries}.ts` — not Zod (unlike `acquisition.ts`). `src/contracts/warehouse.ts` already holds the WRITE-side contracts + the `CalibrationVerdict`/`CalibrationOutcome`/`InputsVersion` schemas — **leave those untouched; append the new read-side schemas near the other read types.**

**Fix:** promote the engine return types to Zod schemas in `contracts/warehouse.ts`; have the engines + `api.ts` `.parse` before `c.json` (mirroring `acquisition.ts`); have `analytics-hooks.ts` import the `z.infer` types + `.parse` responses; **delete the hand-redeclared interfaces.**

---

## 3. APPROACH (sequenced per plan I2)

1. **M4 is ALREADY DONE (PR #45, merged `fddee45`) — do NOT redo it.** `CapitalAction` is a single `z.enum` in `contracts/warehouse.ts`, re-exported by `intel-config.ts` + `analytics-hooks.ts`. First, **promote the REMAINING shared enums the same way** (`HealthBand`, `AttentionBand`, `AnomalySeverity`, `AnomalyKind`, `Quartile`, `NumericMetricKey`) — `z.enum` in contracts, re-exported from both sites — as a typecheck-only commit before the payload schemas. **Gotcha (avoid it):** `export type { X } from '…'` does NOT bind `X` locally, so a file that uses the enum (e.g. `analytics-hooks.ts`) needs `import type { X } from '@contracts/warehouse'` + a plain `export type { X };`, per how M4 fixed it.
2. **Promote payload schemas:** add `PeriodMetricsSchema`, `PropertyScoreSchema`, `GrowthPointSchema`, `SinceAcquisitionSchema`, `NoiDriverSchema`, `NoiDecompositionSchema`, `AnomalyFlagSchema`, `MetricBenchmarkSchema`, `PropertyRankSchema`, `PmScorecardSchema` + per-route envelope schemas; export `z.infer` types.
3. **Engines = source of truth:** in each engine file, replace the hand-written return type with `z.infer<typeof XSchema>`. Do NOT change engine LOGIC or output VALUES.
4. **Parse at the server boundary:** wrap each `api.ts` analytics response in `Schema.parse(...)` before `c.json(...)`.
5. **Parse at the client + delete redeclarations:** in `analytics-hooks.ts` import the schemas/`z.infer` types, replace every `fetchJson<T>` cast with a parse, and delete all hand-redeclared enums/interfaces. Keep the `WarehouseUnavailable`/503 handling.

---

## 4. THE CRITICAL CONSTRAINT — behavior-preserving (refactor, not a data change)

The analytics data **shapes and values must NOT change** — the schemas must match the CURRENT engine output EXACTLY (no field added/dropped/renamed, no loosening to `any`/`.passthrough()` to "make it pass"). **If a schema doesn't match the engine output, fix the SCHEMA to match reality — never the engine.**

**If you discover the engine output is actually WRONG** (a latent bug the schema would expose), do NOT silently change engine behavior to fit a "nicer" schema — that's a behavior change. **DEFER it**: encode the real current shape in the schema (so H6 stays behavior-preserving), and record the suspected bug as a written finding in the PR body + memory for a separate fix.

**TDD for a refactor:** write fidelity tests FIRST — for each engine, build a tmpdir-sqlite warehouse (pattern in `tests/unit/warehouse-actions.test.ts`), run the engine, assert `Schema.parse(out)` succeeds and round-trips identically (`parse(x)` deep-equals `x`). Watch them fail against missing schemas, then add the schemas. Assert each `api.ts` route's parsed envelope matches the engine output. Existing analytics + e2e smoke tests are the regression net (UI unchanged).

---

## 5. EXECUTION — self-gating adversarial workflow (no human checkpoint)

Use the campaign's proven **implement → 3-lens adversarial verify → harden** workflow (reusable scripts in `~/.claude/workflows/`; it caught real defects on H2/H3/B5). This is financial-decision-adjacent code, so the adversarial pass is **MANDATORY**. Verify lenses: **schema-fidelity** (each schema EXACTLY matches the engine output on a seeded DB — nothing loosened), **parse-safety/completeness** (every route `.parse`s before `c.json`; client `.parse`s; ZERO `fetchJson<T>` casts and ZERO hand-redeclared interfaces remain — grep for stragglers), **regression** (existing analytics/e2e green, engine LOGIC untouched, `CapitalAction` single-sourced).

**SELF-GATE:** the adversarial verify IS the approval gate — do NOT wait for a human. Bound it to **≤2 verify→harden rounds**; after round 2, freeze and record any unresolved objections as `RESIDUAL-RISK` notes in the PR. On STANDS (no new crit/high), proceed automatically to land.

---

## 6. HARD CONSTRAINTS

- **Isolated worktree, single-writer.** `git fetch`, then `git worktree add <path> -b feat/h6-warehouse-zod-boundary origin/main`. Never build on the shared checkout.
- **HOT FILES — autonomous collision handling.** `server/warehouse/api.ts` AND `src/contracts/warehouse.ts` are shared with an active parallel "acquisition Workbench" session. Work fast; `git fetch` + `git merge origin/main` between steps and before every push; land the M4 enum commit early. **If the parallel session pushes a conflicting change: rebase/merge and re-verify autonomously — never pause, never force-push shared history.** If a conflict is genuinely unresolvable or CI cannot reach green after a merge, STOP cleanly: leave the PR as a draft, record the exact blocker in the PR body + memory, send the §8 notification, and exit (do NOT hang, do NOT force).
- **DO NOT touch governors** (Invariant 4): `capital-config.ts` (DSCR 1.25 / LTV 0.40), `config/acquisition-ruleset.v1.json`, `intel-config.ts` weights — all ratified. If a "clean" schema seems to want a governor change, DEFER it (proposal), never edit it.
- **B1 exemption — do NOT re-flag.** Confidential deal terms may live in `src/data/seed-deals.ts` (private repo, owner-ratified). The egress guard still bars public surfaces. H6 touches no deal data; its diff is type schemas + tests (synthetic). No confidential scan needed for this repo (the pre-push hook was removed under B1) — but never put a real deal term in a committed test fixture; synthetic only.
- **Leave the calibration contracts untouched** in `contracts/warehouse.ts`.
- **No dev/preview server** (WAL lock) — verify via vitest + tmpdir sqlite only; stop every process you start on EVERY exit path and confirm nothing holds `finance.sqlite`.
- **Done quality:** TDD · typecheck 0 · lint 0 · `npm run governance` ✔ · full `npm run test` green (the harness is now per-file-isolated #40 + order-independent #42 → reliable) · the adversarial review · **evidence (pasted command output) before any "done" claim** · smallest behavior-preserving change.

---

## 7. LAND IT (autonomous, no /ship)

- Commit in logical steps (M4 enum typecheck-only first, then schemas+server parse, then client parse+delete), `git push` the feature branch after each so work is durable. End messages with `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.
- Open a **draft PR** NON-INTERACTIVELY: `gh pr create --draft --base main --title "<...>" --body-file <path>` — **NEVER bare `gh pr create --draft`** (it hangs on a TTY prompt; always pass `--title` AND `--body-file`).
- **Poll CI with a CONCRETE bound** (`gh pr checks` has no `--timeout`; `--watch` waits forever on a stuck check): a bounded non-watch loop calling `gh pr checks <pr>` every ~20s up to a hard cap (~20 min / fixed iterations), breaking on terminal state. On the cap with checks still pending → record CI UNVERIFIED + leave the PR draft (do not keep waiting).
- On observed-green CI: `gh pr merge <pr> --squash --delete-branch`. **Never self-deploy** (no `deploy:mirror`/`wrangler`/`netlify`). PR CI is the verification authority for this additive-but-broad change.

---

## 8. COMPLETION (every exit path — done OR blocked)

- **Fail-safe cleanup:** kill every process you started (release the WAL lock); confirm no dev server and nothing holds `finance.sqlite`; keep the worktree (committed+pushed) for resume or `git worktree remove` it.
- **Durable record:** update `memory/cc-autonomous-audit-pr28.md` — H6 **DONE** (PR #, merge SHA) or **BLOCKED** (the exact blocker + the draft PR URL). If H6 lands, note that the audit backlog is fully closed. Append any DEFERRED findings (latent engine bugs you surfaced) as new backlog items.
- **Notification (mandatory, the ONE pre-authorized send):** post a completion summary to the Notion Operations Hub (db id `32b6ecd8`, per the CLAUDE.md Notion canon; if the sub-page can't be resolved deterministically, skip Notion and record `Notion SKIPPED — target unresolved`) AND send one status email to `ggoldberg@oxfordra.net` ONLY via `C:/Users/Owner/.claude/scheduled-tasks/_shared/send-via-outlook.ps1` (COM path; on non-zero exit retry once then flag the Notion row — do NOT halt; never cc, never ze@). State: outcome (merged SHA / blocked + why), CI conclusion, any DEFERRED findings, residual risks, and confirmation no dev server is left running. This internal send is pre-authorized (Invariant 1 carve-out) — it is NOT a counterparty send.

## 9. DONE DEFINITION

Every warehouse analytics route returns a `Schema.parse(...)`-validated payload; `analytics-hooks.ts` imports `z.infer` types from `contracts/warehouse.ts` and parses every response with **zero hand-redeclared interfaces and zero `fetchJson<T>` casts**; `CapitalAction` + the shared enums are single-sourced; data shapes/values byte-identical (UI unchanged); governance/typecheck/lint/test green; adversarial review STANDS; CI green; squash-merged — OR a draft PR + recorded blocker if genuinely blocked. Memory updated, notification sent, no WAL lock left. The run never pauses, never self-approves a gate, never executes a Hard-Invariant action.
