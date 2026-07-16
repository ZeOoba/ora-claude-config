---
name: ora-intelligence-platform-master-plan
description: "The ratified-pending master plan extending the Command Center from decision-support to investment-intelligence; corrects the \"greenfield\" framing"
metadata: 
  node_type: memory
  type: project
  originSessionId: da8cf1a2-70af-476e-aba2-f2f1320c51bb
---

On 2026-06-13 a full Phase 0→3 strategic review + master plan was authored at `oxford-command-center/docs/superpowers/specs/2026-06-13-ora-intelligence-platform-master-plan.md` (status: plan only, no code until ratified).

**Core reframe (verify before treating any "build a warehouse from scratch" brief as valid):** The financial warehouse and deterministic intelligence are NOT greenfield — they are built, tested (483 tests green), and live on `main` (5-layer SQLite, 32 P&L files ingested; growth/drivers/anomalies/scores/benchmarks/PM engines; Intel module answer-first verdict→why→do). Priority 1 (Property Financial Intelligence) is ~70% done.

**The real gaps (build targets, ranked):** Acquisition Intelligence Engine = 0% (firm priority #1; port the ratified Buy Box scorecard from the `acquisition-underwriting` skill) · Debt/Refi = alerts only, workbook-sourced, no refi score · Leasing/Tenant intel = roster only (no risk/renewal/mark-to-market) · Forecast = absent · Market intel = macro only · Capital Allocation = 4-way action, not the 5-way Buy/Hold/Sell/Refi/Improve · AI = Q&A + deterministic daily template, no narrative/cadenced memos.

**Two structural integrity fixes that gate everything (Revision 1):** (1) two un-reconciled NOI sources — workbook `Property.noi` formula cells vs. warehouse ledger NOI, no tie-out; (2) cross-accounting-basis aggregation with `basis` stored but never surfaced/flagged. No new scoring engine ships until ledger NOI is reconciled and basis-disciplined.

**Roadmap (5 phases):** 1 Foundation/integrity → 2 Debt&Refi + AI narrative briefings → 3 Forecast + Leasing intel → 4 Acquisition engine + Property Quality → 5 Capital Allocation capstone + Market intel. Constraints honored: deterministic-compute/LLM-narrate-only; procurement stance (no CoStar — public+AI market data, confidence-tagged) [[procurement-stance-deepen-not-migrate]]; forecast is bounded ranges + human gate, never autopilot. See [[pfi-build-canon]] and [[cc-build-state]].

**Concurrent-development reality (2026-06-13) — `oxford-command-center` is MULTI-WRITER.** Gabriel actively co-develops it in parallel: a PR-based flow on `main` (squash-merges #11–#17) AND live file edits (build hardening — `ensure-deps.mjs` pregate + resilient server startup; warehouse-verify gate ratchets — score-band #16, unknown-basis ≤8 — and the `data-quality.ts` basis-coverage probe; the `isNoiIncomeClass`/`isOpex`/`NOI_INCOME_CLASSES` contract refactor). Code sessions MUST: stay disjoint from Gabriel's active surface (warehouse ingest/DQ + `server/index.ts` + the gate), re-read any shared file immediately before editing, commit with SPECIFIC paths (never blind `git add -A`), and **leave `main`/PR integration to Gabriel** (don't force-move main, merge, or push). The single-writer claim discipline (tech.md §2, originally for ora-skills/event_log) now applies to this repo too. **Phase 1a shipped** (basis discipline + NOI integrity gate, commit 631963e on `feat/pfi-phase-1-foundation`): basis first-class + partitioned scoring + transitive coherent-batch + one contract-sourced NOI def; 3 adversarial rounds fixed 5 real defects. Reusable `refute-financial-change` workflow saved in the repo's `.claude/workflows/`. Pending Gabriel's PR of 631963e to main.
