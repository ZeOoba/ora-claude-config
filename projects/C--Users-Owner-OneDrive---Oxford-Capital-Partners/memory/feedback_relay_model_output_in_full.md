---
name: feedback_relay_model_output_in_full
description: "Gabriel, 2026-09-18: when handing one model's output to another (Code -> Cowork, agent -> agent, model -> model), paste it IN FULL. A Cowork revision cited text that was not in what it received, because what it received was a summary."
metadata:
  node_type: memory
  type: feedback
  originSessionId: 94d37710-d72c-4c25-9000-53907e7e35d9
  modified: 2026-09-18
---

**Rule:** when relaying one model's output to another model — Code to Cowork, Cowork to Code,
parent to subagent, or one surface's draft to another for revision — **paste the artifact verbatim
and complete**. Do not summarize it, excerpt it, describe it ("the memo you produced earlier"),
or hand over a pointer to a file the receiving surface may not be able to read. If it is genuinely
too large to paste, say which parts were omitted and why, in the prompt itself.

**Why:** Gabriel, 2026-09-18 — a Cowork revision came back containing **a reference to text that
was not in the document**. The receiving model was working from a compressed version of the source,
so it filled the gap with something plausible instead of failing loudly. That is the expensive
failure shape: a lossy relay does not produce an error, it produces confident output built on
material the receiver never saw, and the defect only surfaces when someone checks the revision
against the original. Cross-surface work at ORA is routine (Code does filesystem/git/deploys,
Cowork does autonomous multi-step and scheduled runs), so this is a recurring exposure, not a
one-off.

**How to apply:**
- Relaying a draft for revision: paste the whole draft in the prompt. The receiving model cannot
  see your conversation, your file reads, or your scratchpad.
- Relaying findings between agents: pass the finding text, not "see my earlier analysis."
- A file path is not a relay. It only works if the target surface can read that exact path —
  verify, or paste the contents.
- On the receiving side: if a revision cites, quotes, or relies on text you cannot locate in what
  you were actually given, stop and say so rather than reconciling it. An unlocatable citation is
  evidence the input was truncated, not evidence you missed something.

Distinct from [[feedback_verify_before_repeating_session_claims]], which is about whether a relayed
*claim* is still true. This one is about whether the relayed *material* arrived intact — the facts
can be perfectly accurate and the relay still lossy. Related: [[feedback_subagent_anti_delegation]],
[[feedback_prompt_current_state_prose]].
