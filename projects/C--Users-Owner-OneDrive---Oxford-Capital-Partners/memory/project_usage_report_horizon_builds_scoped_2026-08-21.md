---
name: project-usage-report-horizon-builds-scoped
description: "Scoped specs (not implementations) for the 3 ambitious \"on the horizon\" builds from the 2026-08-21 usage-insights report — self-healing fleet, adversarial pre-push review swarm, environment preflight agent. Each needs its own brainstorming + writing-plans pass in a future session."
metadata: 
  node_type: memory
  type: project
  originSessionId: 00eb97d5-5753-4335-93e9-891e19413564
  modified: 2026-08-21T21:53:53.535Z
---

Source: `~/.claude/usage-data/report-2026-08-21-163943.html`, "On the Horizon" section. Deliberately NOT implemented this session — each is a genuinely large build the report itself frames as multi-step, and the remediation task that produced this note explicitly required a scoped plan only, not code, for these three.

## 1. Self-healing fleet (alarm-to-PR pipeline)

**Problem:** scheduled guards/probes (doctrine-integrity, governor-drift, etc.) already detect drift/corruption reliably, but repair still routes through a human-attended session — an alarm fires, then waits for Gabriel or a session to notice and act.

**Scoped first session should decide, before any code:**
- Inventory: which of the ~34 CC/MCP + ~25 LAMS/Cowork scheduled tasks can emit a genuinely *repairable* alarm (a failing test reproduces the condition) vs. one that structurally needs human judgment (e.g. a confidential-deal call, a financial-model change)? This split determines scope — do NOT build a generic "auto-repair anything" pipeline.
- Classification contract: AUTO_REPAIRABLE / NEEDS_TRIAGE / INFORMATIONAL, and who/what assigns that label per alarm type.
- Repair contract: TDD-first (reproduce via a failing test, then fix, then prove green) — anything that can't produce a reproducing test downgrades to NEEDS_TRIAGE, never guesses.
- Isolation: every repair run in a fresh worktree off origin/main, pathspec-scoped commits only — this session's own work today is a concrete worked example of that discipline (PR #142, the commit-hygiene-guard change) worth using as the template.
- Open question to resolve in the planning session: does this run as a nightly scheduled task, or a `SessionStart`-triggered sweep, or both? Interacts with the existing "scheduler only fires while Desktop app is open" constraint (session-context.md) — an overnight pipeline needs the app kept open, which is a real operational ask, not just a code one.

**Risk if built carelessly:** an auto-repair pipeline that force-pushes or overrides gates unattended directly violates Hard Invariant 6 and the "never mint override tokens without explicit authorization" rule (item 3/isolated-commit skill, this same session) — any design MUST route confidence-below-100% cases to NEEDS_TRIAGE, never to a silent override.

## 2. Parallel adversarial pre-push review swarm

**Problem:** buggy code and wrong approaches are the #1 friction category (42 incidents) — caught late, after commit, rather than before push.

**Scoped first session should decide:**
- This session already built the narrow version of this for ONE class (commit-hygiene-guard.py's UNSCOPED STAGE advisory + the isolated-commit skill's step 4 independent-review requirement) — a full "swarm" generalizes that to N parallel critics (fact-checker, blast-radius auditor, completeness sweeper, base-branch checker) gating EVERY push, not just governance-code pushes.
- Must reuse, not duplicate, the existing `eos-review-gate.py` mandatory-review mechanism for `hooks/**`/financial code — a parallel swarm for ordinary code should not create a second, competing review-gate implementation.
- Hard performance constraint from the report: reviewers run concurrently, whole gate finishes under 90s — needs measurement against this repo's actual push-time budget (the hook-tests-gate alone can run 90s+ under load per this session's own observed timeout).
- Needs an explicit override-token path for genuine emergencies, logged to event_log.md — same posture as every other gate in this repo, not a new one.

**Risk if built carelessly:** stacking a new mandatory swarm on top of an ALREADY-frequently-overridden gate regime (this session used 2 override tokens in one sitting) makes the "guardrails blocking legitimate work" friction category (the report's OWN second-biggest complaint) worse, not better, unless scoped tightly to genuinely new failure classes.

## 3. Environment preflight / self-healing agent

**Problem:** ~26 of ~llate incidents are environmental, not intellectual (gate timeouts, MAX_PATH, contended claims, quota exhaustion, host-sleep late-fires) — no systematic preflight catches these before they cost a session.

**Scoped first session should decide:**
- Mine transcripts/event_log for the actual distinct blocker signatures FIRST (the report names several; there are certainly more) — do not guess at the list before measuring it.
- Classify each as AUTO_FIX / GUIDED_FIX / ACCEPT_AND_ROUTE_AROUND before writing any detector.
- `SessionStart` hook budget: must run in well under 10s and never block on informational findings — this repo already has a SessionStart doctrine-integrity-probe.py that takes measurable time (observed this session generating ~100 lines of output); a second SessionStart check needs to not compound that cost.
- Nightly deeper sweep is a SEPARATE scheduled task, not the SessionStart hook — same registration discipline as any other scheduled task (register-scheduled-task skill, dual-fleet awareness, single-writer registry check).

**Risk if built carelessly:** yet another SessionStart hook is exactly the kind of "add automation" the standing AUTOMATION BUDGET rule (rules.md §9) gates on P0-criticality — this needs the same quarterly-review justification bar as any other new scheduled task, not an exemption because it's about tooling health.

## Recommended sequencing

Do NOT build these in parallel. #2 (review swarm) most directly extends work already landed this session (isolated-commit skill, eos-review-gate usage) and is the cheapest next increment. #3 (preflight) requires a measurement pass before any design commitment. #1 (self-healing fleet) is the largest and most operationally risky — sequence it last, and only after #2 and #3 exist as building blocks (a repair pipeline needs both a review gate to validate its own fixes and a preflight layer to avoid repairing environmental noise as if it were a real bug).
