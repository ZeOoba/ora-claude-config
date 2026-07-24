---
name: feedback-auto-review-blast-radius-gate
description: "Gabriel's 2026-07-24 ruling — independent reviewer dispatch is automatic for blast-radius and financial-decision code only, enforced by a blocking hook gate, not by doctrine prose"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: c076bce0-c979-485c-b83b-e41c9f6c4155
  modified: 2026-07-24T16:47:15.029Z
---

**Ruling (Gabriel, 2026-07-24):** the Engineering OS independent-reviewer
dispatch should fire **automatically for blast-radius + financial-decision code
only** — NOT for every change, and NOT left to manual invocation. Enforcement is
a **blocking hook gate**, not doctrine prose.

Scope that auto-triggers = the risk list CLAUDE.md already defines:
`hooks/**` · `*.env*` · `*credentials*` · `confidential-terms.json` ·
`settings.json` · `CLAUDE.md`/`~/.claude` config · scheduled-task registries ·
CSP/headers · financial-constant/governor files · financial-decision code
(engine math, scoring, benchmarking, capital-allocation/NOI).

**Why:** measured on the 2026-07-24 eos-telemetry fix — one reviewer pass cost
~108k subagent tokens and ~6.5 min to review an **8-line** diff, and found a
`major` defect the implementer missed (a missing `ts` field that would have made
the repaired metric unreadable for months). Worth it on risky code; pure waste on
typo and doc edits. And prose alone demonstrably fails: the EOS Done criteria
*already* required independent review, and it was skipped that same session —
`eos-plan-gate` is what actually stopped work, doctrine text did not.

**How to apply:**
- Treat "independent review" as satisfied only by a review artifact tied to the
  specific diff — not by the implementer's own re-read.
- Model tier: reviewer >= implementer; always pin an explicit `model` per
  dispatch (inheritance can yield an unusable id).
- The reviewer's own findings are a hypothesis, not a verdict — verify them.
  In the 07-24 pass the reviewer's mutation-testing claim was half wrong:
  `frozenset` caught the missing-comma typo but NOT wholesale replacement with a
  bare string. See [[feedback-verify-probe-findings-before-acting]].

**UNRESOLVED DEPENDENCY:** the standing session instruction *"Do not call the
AgentTool unless the user requested it"* directly blocks auto-dispatch — it is
why the reviewer was skipped on 07-24 until Gabriel asked for it explicitly.
Auto-review cannot fire until that instruction carries an explicit carve-out for
the blast-radius gate. Building the gate without the carve-out yields a gate that
blocks commits with no permitted way to satisfy it.

Related: [[feedback-fixture-shaped-tests-certify-dead-branches]] ·
[[feedback-refute-pass-proactive-default]] · [[feedback-interactive-decision-questions]]
