---
name: reference-portfolio-json-notion-seed-fallback-regression
description: "A failed Notion deals fetch makes lease-snapshot-drift-check silently write seed placeholder deals, and the material-change gate reads that data wipe as real portfolio movement"
metadata: 
  node_type: memory
  type: project
  originSessionId: 250df728-ca91-42a4-b710-648ea8cc54dc
  modified: 2026-08-09T15:44:30.932Z
---

When `scripts/lease-snapshot-drift-check.ts` (oxford-command-center) can't reach Notion it prints
`[notion-deals] live fetch failed, using seed: fetch failed`, **still exits 0**, and still writes
`data/snapshots/portfolio.json` — with the live deal pipeline replaced by the hardcoded seed set.

Observed 2026-08-09 07:40 ET run: `deals` 20 → 6, `counterparties` 15 → 14 (Stearns Bank record
dropped), `leases` 138 → 138 unchanged. Field-level damage is seed placeholders overwriting real
values (`estPrice: 1400000 → null`, `location: "1333 Research Road" → "TBD"`, stage flips like
E. Fulton Dead→Candidate). The 6 survivors are the seed ids: `fvc-11153`, `e-fulton-street`,
`banwick-morrison-refi`, `2146-enterprise-twinsburg`, `1333-research-road`, `pendleton-trade-center`.

**Why it matters:** `ora-lease-snapshot-refresh`'s material-change gate only filters
`meta.generatedAt`. A seed-fallback wipe is a large non-timestamp diff, so the gate classifies it as
"real portfolio data moved" and the task's own spec then says commit. Since the 2026-08-09 auto-push
directive that commit also gets pushed to `origin/main` — so one transient `fetch failed` can publish
a 14-deal pipeline wipe to the shared remote unattended. Exit 0 also means the task's routing sends
no Notion post and no email, so it would land silently.

**FIXED 2026-08-09** — [PR #265](https://github.com/ZeOoba/oxford-command-center/pull/265)
(Gabriel-directed, same day — option 3: guard the spec *and* fix the script).
Three layers, all verified green (typecheck 0, lint 0, 3315/3315 tests) plus a live A/B against the
production workbook — degraded run exits 1 with `portfolio.json` byte-identical, healthy run exits 0
with 20 deals / 15 counterparties / 0 error flags:
1. `server/sources/notion-deals.ts` — `loadDeals()` now returns `{deals, degraded}` instead of a bare
   `Deal[]`, so a fetch failure is no longer indistinguishable from a legitimately seed-only pipeline.
   `not-configured` (no token) is deliberately NOT an error; dev servers keep working unflagged.
2. `server/workbook/parse.ts` — a data-losing degradation raises an **error-severity** `dataQuality`
   flag, which `evaluateReconciliationGate` (PR #252) already refuses to write on in both CLI
   writers. Silent Exit 0 → loud Exit 1 on the existing Notion+email routing.
   `requireLiveDealsSource` separately refuses a token-less write (the config-regression half).
3. `server/brain.ts` — the live server is a **third** writer of this file and runs neither gate;
   `persist()` now declines the mirror write when the deals pipeline is degraded while still serving
   in memory. Found by the REFUTE pass, not by the original diagnosis.

**How to apply:** the failure mode is now self-alarming, so treat any `Notion deals pipeline
unavailable` Exit 1 as "refresh skipped, data safe" — usually a transient Notion hiccup, not
corruption. Never `--force` it: forcing writes the placeholders the guard exists to prevent. The
spec's section-shrink guard is the belt-and-braces layer — before committing any material diff,
compare `len(deals)`/`len(counterparties)` against `git show HEAD:data/snapshots/portfolio.json`; a
*drop* is a degraded write, never portfolio movement. Note `json.load(open(path))` fails on this file
under cp1252 — pass `encoding='utf-8'`.

Related: [[reference-parseleases-vacancy-block-phantom-leases-2026-08-03]] (the other class of bad
write to this same file, closed by the checkSnapshot gate — which does **not** cover the deals
section), [[reference-command-center-snapshot-is-tracked-not-ignored]].
