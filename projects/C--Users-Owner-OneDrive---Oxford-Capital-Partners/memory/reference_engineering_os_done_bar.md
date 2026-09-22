---
name: reference-engineering-os-done-bar
description: "Full text of Engineering OS's 'Done' bar (L2-L7 completion criteria) — extracted verbatim from CLAUDE.md 2026-08-13 to relieve word-budget pressure; CLAUDE.md keeps a condensed pointer"
metadata:
  type: reference
  originSessionId: 5c8afbd3-8eaa-4e0c-9874-8c300884ab7c
  modified: 2026-08-13T23:09:20.496Z
---

Extracted verbatim 2026-08-13 (external-artifact-intake setup-improvement follow-up, Gabriel-approved) from CLAUDE.md's Engineering OS section, which had drifted to 1766 words — past the 1700 WARN threshold and outside the 1694–1755 "don't trim" band on the high side. No content was cut; this is a relocation (one fact, one home), not a trim — CLAUDE.md now carries a condensed pointer instead of the full clause.

**Done bar (L2–L7):**

Done = TDD (config/throwaway/generated exempt — ask) · typecheck 0 · lint 0 · full suite green (spurious-failure gotcha: `feedback_npm_test_intermittent_access_violation.md`) · repo gate · independent LOCAL review (`superpowers:requesting-code-review`); financial-decision code (engine math, scoring, benchmarking, capital-allocation/NOI) AND security-gate code (`hooks/**` override/auth/exit-code logic) AND shared-state writer code (anything that writes a ledger, event log, registry, feed/snapshot or tracker, or takes a lock -- the 2026-09-22 /insights sweep found the recurring first-draft defects there: event-log append races, missed M365 writer paths, the AR-feed eviction fix) ALSO get a MANDATORY adversarial REFUTE pass (optional cross-model escalation: [[reference_refute_cross_model_escalation]]) · evidence (command output) before any "done" claim · dev/preview servers STOPPED before returning (RAM) · smallest surgical change, assumptions surfaced.

This clause is deliberately unmirrored elsewhere (was CLAUDE.md-only; now lives here with a pointer from CLAUDE.md) — do not also paste it into the Engineering OS spec file (`~/.claude/docs/superpowers/specs/2026-06-05-engineering-operating-system-design.md` §7) or any other doctrine file; a second copy is a second thing to keep in sync and CLAUDE.md/§7 both already point here.

**Downstream references that cite this concept (verified not exact-phrase-dependent, 2026-08-13 grep sweep — safe to relocate):** `ora-financial-code-integrity-sweep`, `ora-appsec-sweep`, `ora-pm-ledger` scheduled tasks; `open-items-tracker.md`. All restate the concept in their own words or reference "CLAUDE.md's Done bar" as a location, which still resolves correctly post-extraction.

Related: [[reference_agent_skills_repo_intake_2026-08-13]] (the intake that surfaced this gap) · [[reference_claude_md_word_budget_is_a_floor]] · [[reference_refute_cross_model_escalation]].
