---
name: reference-refute-cross-model-escalation
description: "Optional cross-model (Gemini/Codex CLI) escalation step for the mandatory adversarial REFUTE pass on financial-decision and security-gate code — detail referenced from CLAUDE.md's Done bar"
metadata:
  type: reference
  originSessionId: 5c8afbd3-8eaa-4e0c-9874-8c300884ab7c
  modified: 2026-08-13T22:57:29.389Z
---

Adopted 2026-08-13 from `addyosmani/agent-skills`'s `doubt-driven-development` skill (MIT) via external-artifact-intake evaluation, ratified by Gabriel. Extends — does not replace — CLAUDE.md's existing mandatory REFUTE pass for financial-decision code (engine math, scoring, benchmarking, capital-allocation/NOI) and security-gate code (`hooks/**` override/auth/exit-code logic).

**When to offer:** after the standing local adversarial REFUTE pass completes, in an interactive session, on financial/security-gate findings where a second, differently-architected model's blind spots would plausibly differ from the first reviewer's. Not a new gate — REFUTE already runs; this is an optional escalation on top of it, offered every time, never silently skipped.

**Protocol:**
1. Ask Gabriel: single-model REFUTE is done — want a cross-model second opinion (Gemini CLI, Codex CLI, manual external review, or skip)? Present per [[feedback_interactive_decision_questions]]'s interactive-question format.
2. If a CLI is picked: verify it's in PATH and actually runs (`which`/`--version`) before invoking — a stale binary can pass the PATH check and still fail on real input. Confirm the exact invocation (flags, auth) with Gabriel.
3. Pass **ARTIFACT + CONTRACT only** — never the CLAIM/conclusion (biases toward agreement), never session context, never confidential-deal terms (Hard Invariant 3 applies to what leaves this machine via a CLI call same as any other external surface).
4. Run in a **read-only sandbox** (`codex exec --sandbox read-only`, `gemini --approval-mode plan`, or equivalent) — the artifact under review could itself contain injected instructions the external CLI would otherwise execute against the workspace.
5. Never interpolate the artifact into a shell-quoted argument — pipe via stdin/heredoc to keep embedded backticks/`$()`/quotes inert.
6. If the CLI is unavailable or fails: surface the failure explicitly and offer manual/different-tool/skip — never silently fall back to single-model-only.
7. Non-interactive contexts (scheduled tasks, `/loop`, autonomous runs): skip cross-model and announce the skip in output. Never invoke an external CLI without Gabriel's explicit in-turn authorization — same bar as any other external send.

**Why it matters:** a single-model reviewer shares blind spots with the model that wrote the artifact; ORA's REFUTE pass currently has no mechanism for an architecturally-different second opinion on the highest-stakes code class (financial engines, security-gate hooks).

Related: [[rules]] §21 (trust tiers, same intake batch) · CLAUDE.md Engineering OS §"Done" bar (REFUTE clause, CLAUDE.md-only/unmirrored — this file is an *extension* pointer, not a duplicate of the clause itself) · [[reference_agent_skills_repo_intake_2026-08-13]].
