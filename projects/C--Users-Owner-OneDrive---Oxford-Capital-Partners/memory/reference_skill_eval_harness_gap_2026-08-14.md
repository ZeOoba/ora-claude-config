---
name: reference-skill-eval-harness-gap-2026-08-14
description: "Setup-improvement candidate for ora-setup-audit's next revision: no periodic, dated-snapshot benchmark exists for whether skill/prompting changes actually improve outcomes over time — ora-setup-audit's own Guardrails already document the adjacent 'no invocation telemetry' blind spot, this is the companion gap on the quality-over-time axis. Surfaced by evaluating the external code-review-graph repo's dated-CSV retrieval-eval harness pattern."
metadata: 
  node_type: memory
  type: project
  originSessionId: db8b3a1b-9d76-4e71-892b-34195876db85
  modified: 2026-08-14T19:05:05.178Z
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
most frequently revised); harness-only, no token-budget retrofit bundled in. Kickoff prompt
for a new `/build` session prepared at the session scratchpad
(`2026-08-14_acquisition-underwriting-eval-harness_kickoff-prompt.md`) — not yet run. Status
still CANDIDATE until that session actually lands the harness; update this line to PILOTED
with the harness's location once it does.
