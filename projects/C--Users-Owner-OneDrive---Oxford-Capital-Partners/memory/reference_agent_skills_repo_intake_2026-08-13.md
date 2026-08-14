---
name: reference-agent-skills-repo-intake-2026-08-13
description: "external-artifact-intake evaluation of addyosmani/agent-skills v0.6.6 — disposition and what was grafted where"
metadata:
  type: reference
  originSessionId: 5c8afbd3-8eaa-4e0c-9874-8c300884ab7c
  modified: 2026-08-13T22:57:42.909Z
---

Evaluated 2026-08-13 at Gabriel's request: local clone `Business/agent-skills-main/` of the public repo `addyosmani/agent-skills` (MIT, v0.6.6) — a DEFINE→PLAN→BUILD→VERIFY→REVIEW→SHIP skill/command pack for AI coding agents.

**Prior context:** `security-auditor` agent + `security-and-hardening` skill were already cherry-picked from this exact repo on 2026-07-18 (re-confirmed byte-identical this pass). Not re-litigated.

**Comparison finding:** the repo's 8-command lifecycle (`/spec /plan /build /test /review /webperf /code-simplify /ship`) and remaining 23 skills are superseded by ORA's existing Engineering OS (L1-L7 lane system) + the `superpowers` plugin (TDD, worktrees, plan-writing, systematic debugging) + `pr-review-toolkit` (code review, simplification) — same lifecycle shape, but ORA's has model-tier dispatch, worktree isolation, confidentiality gating, and a mandatory adversarial REFUTE pass the source repo lacks entirely. `webperf`/`web-performance-auditor.md` is superseded by the ORA-specific `website-perfection` skill.

**Adoption candidates ratified by Gabriel (all 4 offered, all 4 adopted):**
1. Cross-model (Gemini/Codex CLI) REFUTE escalation, from `doubt-driven-development` → [[reference_refute_cross_model_escalation]], pointed to from CLAUDE.md's Done bar bullet.
2. Hypothesis + confidence-% framing for ruling questions, from `interview-me` → folded into [[feedback_interactive_decision_questions]].
3. Trust-tier taxonomy for loaded external content (Trusted / Verify-before-acting / Untrusted), from `context-engineering` → [[rules]] §21.
4. Task-sizing gate (XS-XL, "and"-in-title signal, 5-file ceiling), from `planning-and-task-breakdown` → `~/.claude/commands/plan.md`.

**Setup-improvement candidates surfaced (not yet actioned — logged for later, not part of this graft):**
- `~/.claude/commands/debug.md` has no explicit line on treating scraped error/log output as untrusted data — now partially covered by [[rules]] §21's taxonomy, but `/debug` itself doesn't cite it.
- ORA's Definition-of-Done content lives inline in CLAUDE.md's dense Done-bar bullet, under active word-budget pressure (`reference_claude_md_word_budget_is_a_floor.md`) — could be extracted to its own reference file the way `standards.md`/`rules.md` already are, freeing CLAUDE.md words without losing content.
- `/ship`'s brain-mirror and ora-pm deploy checks are binary pass/fail (curl 200/302) with no quantified hold-vs-rollback threshold — low priority, no live-traffic targets today.

**Disposition: SUPERSEDED (framework) + 4 fragments FILED** to the homes listed above. The repo itself is not adopted, installed, or referenced as a running dependency — nothing in ORA's setup points back to the cloned directory.
