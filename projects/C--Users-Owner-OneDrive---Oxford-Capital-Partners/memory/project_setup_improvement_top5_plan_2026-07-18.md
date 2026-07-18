---
name: project-setup-improvement-top5-plan-2026-07-18
description: "Fable-synthesized top-5 plan to improve the Claude Code/Cowork SETUP itself (not doc accuracy, not the separate operational punch-list) — closes the deal-decision flywheel, adds effect-verification (dispatch-vs-effect gap), a counterparty-aging SLA, an appsec sweep seeded from addyosmani/agent-skills cherry-picks, and write-guard hardening. Status: PLANNED, not yet executed as of 2026-07-18."
metadata: 
  node_type: memory
  type: project
  originSessionId: 5900e68d-2914-4c15-9f60-65efc5d0a2c2
---

# Claude Code/Cowork Setup Improvement — Top-5 Plan, 2026-07-18

Distinct from two other same-day artifacts: the accuracy remediation (event_log.md, same date) and the operational open-items plan (`project_artifact_content_top5_plan_2026-07-18.md`, currently executing in a parallel session). This pass asked: given the 3 artifacts' content, how should the SETUP ITSELF improve relative to Gabriel's stated priorities (acquisition velocity → operational optimization → institutional quality → comms/brand → knowledge capture)? Four Fable research passes (one per artifact + one evaluating `addyosmani/agent-skills` — a downloaded public skills library — for genuinely additive pieces) fed one Fable synthesis pass, which collapsed ~30 findings into 8 root causes and verified several against live ground truth before ranking (one finding, skill-drift-detection, turned out to already substantially exist — `ora-skill-store-drift-check` v1.10 — and was downgraded accordingly).

## Top 5, ranked by acquisition-velocity service + real-failure prevention over hygiene

1. **Close the deal-decision flywheel.** The decision ledger only writes on CLOSE/KILL — the actual volume (PASS/SKIP/DROP/PARK from SCREEN/verified-deal-recon/deal-flow-triage) is never captured, nothing reads it back into future screens, `ora-calibration-snapshot` has never fired, and underwriting defaults never get compared to post-close actuals. Every decision made today is discarded training data.
2. **Effect-verification layer.** One root cause behind 5 separate findings, including a confirmed real failure: automation only checks "did it fire" (`lastRunAt`), never "did it produce its declared output" — this exact gap is why the northridge/brockton summary email silently never sent while the task showed complete. Fix: per-task output contracts + a generalized automation-health-monitor + a probe-status ledger + an execution register (ratified ≠ built, closed).
3. **Counterparty-aging SLA.** Cheapest direct velocity win — a deal sat stalled 36-38 days on non-responsive counsel before a weekly board caught it reactively. New scheduled task computing per-deal outbound-ask aging, drafting (never sending) nudges past threshold.
4. **Appsec sweep, seeded from cherry-picked tooling.** `ora-pm` (live tenant portal, prior CRITICAL AR-ledger defect, a past confidential-terms leak via `.env.example`) has zero standing security coverage — Gabriel's existing security tooling is confidentiality/exposure-shaped only, no general appsec. Cherry-pick `security-auditor` agent + `security-and-hardening` skill from `addyosmani/agent-skills` (NOT the whole plugin — ~80% redundant with superpowers/pr-review-toolkit, and its commands collide with Engineering OS lane names); register a weekly sweep modeled on the existing financial-code-integrity-sweep.
5. **Write-guard architecture hardening.** The governance layer everything else trusts has a twice-independently-rediscovered Desktop Commander bypass class, no hard write-gate on its own config (`hooks/`, `settings.json`, `CLAUDE.md`), and session-collision prevention is honor-system despite documented duplicate-build incidents.

## Execution plans, sequencing, and Gabriel-decision gates

Full execution-ready plans (exact files/systems, done-when criteria) captured in this session's Fable synthesis output — condensed:

- **Plan 1** touches `ora-skills/acquisition-underwriting`, `verified-deal-recon`, `deal-decision-ledger.md`, `ora-calibration-snapshot`, and adds two post-close variance tasks (+6mo/+12mo) via `deal-retirement`. Gabriel gates: Save-skill reimport clicks, scheduled-task registrations, ratifying any proposed underwriting-default delta (Invariant 4 — proposals never auto-apply).
- **Plan 2** adds an `output_contract:` frontmatter block to the top ~10 write-producing tasks, generalizes `automation-health-monitor` to check artifact existence/freshness instead of a hand-maintained table, adds a `probe-status.json` beacon, and a new `memory/execution-register.md`. No hard Gabriel gate, but is a shared-`~/.claude`-surface edit requiring the single-writer check first. **Should land before Plans 3-4 register their tasks**, since those declare contracts from day one.
- **Plan 3** is a new `ora-deal-aging-sla` scheduled task (draft-only, Hard Invariant 1 — every nudge needs individual send confirmation). Gabriel gate: ratify the aging thresholds before first run ([SPECULATIVE] proposed: broker 5 business days, counsel 7, lender 7).
- **Plan 4**: cherry-pick 2 files from the zip into `~/.claude` (supervised config change, single-writer check), then a new weekly `ora-appsec-sweep` over `ora-pm` + `oxford-command-center`, Fable-pinned per the financial/security-gate model floor. First run manual/supervised before cron registration given known-defect history. Gabriel gate: approving the `~/.claude` additions + task registration. Note: B1/B4 of the CC autonomous audit are already decided KEEP-private — do not re-flag deal-terms privacy items.
- **Plan 5** touches `~/.claude/hooks/lib/`, `memory-index-guard.py`, `registry-write-guard.py`, adds a coverage meta-test, and a new PreToolUse hard gate reusing the existing session-scoped override-token mechanism (the old flat sentinel stays retired). Mandatory adversarial REFUTE pass (this is security-gate code). Gabriel gate: **explicit approval before landing** — modifies the permission layer that will thereafter bind all sessions including his own.

## Everything-else punch-list (grouped, nothing lost)

**Quick wins:** pin `ora-financial-code-integrity-sweep`'s refute pass to an explicit Fable subagent (currently violates the Fable-floor invariant); tier mechanical heartbeat/AAOS tasks to haiku; retire the RAM watchdog remnant; dedupe the double-registered searchfit-seo plugin; force off SEO skills beyond seo-audit/technical-seo/broken-links; add a velocity-first WIP rule to closeout doctrine.

**Coordination & alarms:** consolidate 3 dead-man limbs to one path terminating where Gabriel actually reads; build a cross-fleet handoff queue with >48h aging alarm; move event-log to per-session append-only journals + a compactor (3rd instance of the same write-contention class); session-suffix OI-IDs.

**Governance calibration:** track plan-gate override rate as a KPI (currently 41%, target <15%); build a connector intake gate (inventory probe + one-page vetting checklist); add a pre-fire dependency check for one-time tasks (partially mitigated already by the PENDING_REIMPORT ledger).

**Consistency & drift:** make the schematic refresh compute counts from source instead of hand-maintaining them; extract QC-gate/brand constants into a shared file via the existing SHARED_ROOT_DEPS mechanism (real incident: a 22-pt vs 16-pt QC-gate fork); add the live-worktrees leg to `ora-skill-store-drift-check`.

**Deal-lifecycle:** add a FINAL-document manifest step to `deal-retirement`.

**Zip leftovers:** `web-performance-auditor` agent — optional, install alongside Plan 4's cherry-pick, near-zero marginal cost; `observability-and-instrumentation` skill — mine for logging conventions only, do not adopt live; everything else in the zip (spec/plan/build/test/review/ship lifecycle skills, code-review, TDD, git-workflow) is ~80% redundant with superpowers + pr-review-toolkit and should NOT be installed.

**Key paths:** `~/.claude/hooks/` (guards, lib/, tests/) · `~/.claude/maintenance/_state/` (beacon pattern) · `~/.claude/scheduled-tasks/ora-financial-code-integrity-sweep/` and `ora-calibration-snapshot/` (models to copy) · `deal-decision-ledger.md`, `standards.md`, `open-items-tracker.md` · `C:/Users/Owner/ora-skills/` · `Claude_Workspace/00_Governance/Scheduled/automation-health-monitor/SKILL.md` and `ora-skill-store-drift-check/SKILL.md` · zip extracted at session scratchpad `agent-skills-main/agent-skills-main/` (agents/, skills/security-and-hardening/, agents/web-performance-auditor.md).
