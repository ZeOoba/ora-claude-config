---
name: reference-engineering-os-done-bar
description: "Full text of Engineering OS's 'Done' bar (L2-L7 completion criteria) — extracted verbatim from CLAUDE.md 2026-08-13 to relieve word-budget pressure; CLAUDE.md keeps a condensed pointer"
metadata:
  type: reference
  originSessionId: 5c8afbd3-8eaa-4e0c-9874-8c300884ab7c
  modified: 2026-10-30T22:20:00.000Z
---

Extracted verbatim 2026-08-13 (external-artifact-intake setup-improvement follow-up, Gabriel-approved) from CLAUDE.md's Engineering OS section, which had drifted to 1766 words — past the 1700 WARN threshold and outside the 1694–1755 "don't trim" band on the high side. No content was cut; this is a relocation (one fact, one home), not a trim — CLAUDE.md now carries a condensed pointer instead of the full clause.

**Done bar (L2–L7):**

Done = TDD (config/throwaway/generated exempt — ask) · typecheck 0 · lint 0 · full suite green (spurious-failure gotcha: `feedback_npm_test_intermittent_access_violation.md`) · repo gate · independent LOCAL review (`superpowers:requesting-code-review`); financial-decision code (engine math, scoring, benchmarking, capital-allocation/NOI) AND security-gate code (`hooks/**` override/auth/exit-code logic) AND shared-state writer code (anything that writes a ledger, event log, registry, feed/snapshot or tracker, or takes a lock -- the 2026-09-22 /insights sweep found the recurring first-draft defects there: event-log append races, missed M365 writer paths, the AR-feed eviction fix) ALSO get a MANDATORY adversarial REFUTE pass (optional cross-model escalation: [[reference_refute_cross_model_escalation]]) · evidence (command output) before any "done" claim · dev/preview servers STOPPED before returning (RAM) · smallest surgical change, assumptions surfaced.

**Editor note (moved from CLAUDE.md 2026-10-20 as a one-in-one-out trim; the setup-audit plugin tie-break it made room for was dropped at the 2026-10-30 sync to #379, plugin gone from the account per R33-5):** CLAUDE.md's Done bar line used to end with "Spec §7 points here too — do not duplicate." Spec §7 itself contains no such pointer (checked 2026-10-20), so do not re-add that sentence.

This clause is deliberately unmirrored elsewhere (was CLAUDE.md-only; now lives here with a pointer from CLAUDE.md) — do not also paste it into the Engineering OS spec file (`~/.claude/docs/superpowers/specs/2026-06-05-engineering-operating-system-design.md` §7) or any other doctrine file; a second copy is a second thing to keep in sync and CLAUDE.md/§7 both already point here.

**Downstream references that cite this concept (verified not exact-phrase-dependent, 2026-08-13 grep sweep — safe to relocate):** `ora-financial-code-integrity-sweep`, `ora-appsec-sweep`, `ora-pm-ledger` scheduled tasks; `open-items-tracker.md`. All restate the concept in their own words or reference "CLAUDE.md's Done bar" as a location, which still resolves correctly post-extraction.

**REFUTE routing (added 2026-10-01, from the refute-overlap investigation) — which tool satisfies the mandatory pass:**

| Situation | Use | Why |
|---|---|---|
| Financial-decision source in `oxford-command-center` (engine math, scoring, NOI, ingest, anything under `server/`/`scripts/` default-deny) | `refute-financial-change` Workflow (5 lenses: correctness · determinism · edges · sweep-completer · scope-auditor; Fable, per-lens opus fallback; `args.model:'opus'` only when Fable is unavailable) | Its `wf_<runId>` is the ONLY thing the `Refute-Reviewed:` commit trailer and CI `check:refute` accept (per commit). Nothing else attests. |
| Recurring sweep of financial commits | `ora-financial-code-integrity-sweep` scheduled task (already calls the Workflow, 3 lenses) | No change needed. |
| `~/.claude` guard/hook/probe code, shared-state writers, doctrine/skill edits, plans, factual claim sets — a REFUTE pass before commit | `adversarial-reviewer` agent (read-only; ALWAYS pass `model`, Fable floor for governor/financial/confidential) | Generic and ~5-10x cheaper per pass (agent ≈ 60-165K tokens vs Workflow median ≈ 570K); no attestation artifact. |
| Blast-radius PR about to merge (hooks, registries, multi-session checkout, verification claims in the commit message) | `adversarial-merge-gate` skill (5 mandates + permission/guard coverage, pinned SHA) | Its lenses (race, test-validity, blast-radius) are the ones the financial Workflow lacks: in the 2026-09-30 agent-tooling gate, test-validity found 2 MEDIUM coverage gaps and race found a crash that correctness missed. |
| Style / guideline conformance | `pr-review-toolkit:code-reviewer` / native `/code-review` | Not a refutation pass. |

Evidence behind "keep, don't merge" (2026-10-01): the Workflow has 56 persisted runs (2026-08-17..09-29), all completed, 0 tooling failures, 86% found a real defect (11 high, 36 medium, 9 low), median ≈ 570K tokens / 5.5 min, every run against `oxford-command-center`. `/verify` (a third copy of the Workflow's lens text, "keep in sync") had 1 recorded use and was retired 2026-10-01 on Gabriel's instruction (local copy: `~/.claude/archive/commands/verify.md`; git history is the durable copy); the forked `-opus` script is replaced by `args.model` (oxford-command-center PR #420, merged 2026-10-01; `model: 'opus'` only when Fable is unavailable, result carries `modelFloorMet`). If a future change adds a test-validity or race lens to the Workflow, trial it on 2-3 historical change sets first — the 86% find rate is an asset, don't perturb the prompt blind.

Related: [[reference_agent_skills_repo_intake_2026-08-13]] (the intake that surfaced this gap) · [[reference_claude_md_word_budget_is_a_floor]] · [[reference_refute_cross_model_escalation]].

## Non-trivial technical recommendations (moved from CLAUDE.md 2026-10-30)
Structure: current state → evidence → root cause → alternatives → ROI/confidence → risk → rollback — evidence over preference.
