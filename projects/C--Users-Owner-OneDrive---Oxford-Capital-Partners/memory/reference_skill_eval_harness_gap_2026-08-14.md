---
name: reference-skill-eval-harness-gap-2026-08-14
description: "PILOTED 2026-08-14, merged to ora-skills main + scheduled: golden-set regression harness for acquisition-underwriting at ora-skills/acquisition-underwriting-eval-harness/, registered as ora-acquisition-underwriting-eval-harness (daily doctrine-edit poll, CC/MCP fleet). Was the quality-over-time companion to ora-setup-audit's 'no invocation telemetry' gap; surfaced by evaluating the external code-review-graph repo's dated-CSV retrieval-eval harness pattern."
metadata: 
  node_type: memory
  type: project
  originSessionId: db8b3a1b-9d76-4e71-892b-34195876db85
  modified: 2026-08-14T21:37:28.730Z
---

# Skill/prompt effectiveness has no benchmark-over-time process

Surfaced 2026-08-14 while running `external-artifact-intake` on the external repo
`tirth8205/code-review-graph` (full intake record: `event_log.md`, 2026-08-14 entry). That
repo's own `evaluate/` harness re-runs fixed benchmarks against real OSS repos and writes
dated CSV snapshots (2026-05-25, 2026-08-02) scoring token efficiency, multi-hop retrieval
(MRR), and impact accuracy (precision/recall/F1) — a concrete pattern for measuring
whether a *change* to a retrieval/context system helped or hurt, repeatable over time.

**The gap:** ORA has no equivalent for its own skills. `ora-setup-audit`'s Guardrails
section already establishes that no invocation-count telemetry exists (`~/.claude.json#skillUsage`
and the CC/MCP-only JSONL transcripts are the same blind spot restated, confirmed
2026-08-13 forensics) — but that's a *usage-frequency* gap. This is the adjacent
*quality-over-time* gap: even where a skill clearly gets used (acquisition-underwriting,
loi-generation, lease-abstraction-pipeline), nothing snapshots how well it's performing
before/after a doctrine change (e.g. a scorecard-weight amendment, a new QC-gate rule) to
confirm the change was actually an improvement rather than just a plausible-sounding one.

**Why: ** the external repo's pattern only works because it has a stable, versioned
benchmark set (flask/fastapi/django/gin/httpx/express) to re-run against. ORA's
equivalent would need a small fixed set of past deals/leases/documents with known-correct
outputs (a golden set) to replay a skill against after any material doctrine edit — this
does not exist today for any ORA skill.

**How to apply:** flag as a candidate finding the next time `ora-setup-audit` runs (thread
4, token-bloat/self-monitoring sources, or a new thread) — not something to build
unilaterally off one external-repo comparison. Scope, if ratified, would likely start
narrow: pick one high-stakes, frequently-amended skill (acquisition-underwriting is the
obvious candidate given its Buy Box & Scorecard revision history) and build a small
golden-set regression check before generalizing.

Not a Hard Invariant, not urgent — logged so a fifth independent rediscovery of "we have
no way to tell if a skill change helped" doesn't happen (see [[project_setup_improvement_top5_plan_2026-07-18]]
for the sibling top-5 setup-improvement backlog this should eventually join).

**Scope ratified 2026-08-14 (Gabriel):** pilot on `acquisition-underwriting` only (highest-stakes,
most frequently revised); harness-only, no token-budget retrofit bundled in.

## PILOTED 2026-08-14 — location and how to re-run

Built at `ora-skills/acquisition-underwriting-eval-harness/`, merged to `ora-skills` main twice
same day: initial build (`d4a03e3`), then an E Fulton enrichment + follow-ups pass (`c7527d9`).
6-deal golden set — **3 scored (2 HIGH: Port Sheldon, Liberty; 1 MEDIUM: E Fulton), 3 LOW/
informational** (Hamilton, 1333 Research Rd, 470 McCormick) — `lib/diff_verdict.py` +
`lib/record_run.py` (27 unit tests, TDD), a `SKILL.md` orchestration runbook, and a passing
mutated-input self-test in `fixtures/`. Full doctrine, findings, and re-run procedure live in
that `SKILL.md` — do not duplicate here; this memory entry is a pointer, not the source of record.

**Re-runs automatically now.** Registered `ora-acquisition-underwriting-eval-harness` (CC/MCP
fleet, `14 12 * * *`, daily) — polls `acquisition-underwriting/SKILL.md`'s git SHA and only runs
the full replay on an actual doctrine edit; posts to the Notion Operations Hub only on a scored
FLAG. Manual re-run (via a Code session following the harness `SKILL.md`) still works too.

**Findings worth knowing before touching this again**, discovered running the actual build (not
anticipated in the original scope):
1. **RCT v03 date-boundary problem.** All 6 golden deals predate the skill's 2026-07-14 RCT v03
   replacement-cost recalibration. Diffing today's doctrine against the pre-recalibration
   archived scores produced huge false "deltas" that were just the already-ratified
   recalibration. Fixed by re-baselining `golden` to a fresh 2026-08-14 replay rather than the
   archived Notion score. **Practical consequence: this harness can only detect drift from
   2026-08-14 forward** — it has no doctrine-consistent baseline for the 06-09-to-08-14 window.
   A future pilot on a different skill should watch for the same class of boundary if that
   skill has also had a major recalibration since its candidate golden deals were screened.
2. **Replay nondeterminism is real and was measured, not assumed** — a 3-run repeatability
   check on the 2 HIGH-confidence deals found up to a 4.5-point Combined-score range on
   identical inputs/doctrine, which forced the tolerance from an initial 3.0 to 5.0 points.
   Anyone re-tuning this harness's tolerance should re-run the repeatability check rather than
   picking a number.
3. **Time-invariant facts vs. genuinely-frozen-unknown facts are different things when
   enriching a golden deal.** Closing E Fulton's Economics-blind-spot required distinguishing
   physical building specs (clear height, construction, per-building SF — legitimate to source
   from ANY point in time, since they don't change) from occupancy/tenancy data (a real unknown
   AT the 6/9 screen date — backfilling with later data would import hindsight and break the
   frozen-snapshot discipline). E Fulton tops out at MEDIUM confidence, not HIGH, because of this
   — 6 of 7 categories resolved, 1 stays null by design. Applies to any future enrichment pass on
   this or another skill's golden set.
4. **Headless `claude -p` CLI re-run path is a dead end in this environment, confirmed by direct
   test** — a nested subprocess has no persisted auth (`loggedIn: false`, no API key, parent
   OAuth doesn't carry over). Don't re-attempt it; ORA's scheduled-task fleet (runs inside the
   authenticated Desktop app) is the correct unattended-execution mechanism instead.

Kickoff prompt that started this build: session scratchpad
`2026-08-14_acquisition-underwriting-eval-harness_kickoff-prompt.md` (historical only now).
