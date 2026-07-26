---
name: reference-session-retro-evidence-rule
description: "Reusable end-of-session retro template (friction/invariants/CLAUDE.md-rules) gated by an evidence-citation + null-result requirement so it can't fabricate findings on a thin session"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 39e8bd0e-07dd-46b7-ac7f-f4e70bb11ab3
  modified: 2026-07-26T17:43:11.154Z
---

**The template.** A generic "Meta-Prompting Engineer" retro prompt (friction analysis →
extracted invariants → CLAUDE.md rule proposals) surfaced 2026-07-26. As originally
worded it had an unconditional three-header output contract with no requirement that
findings be grounded in anything — run on a session with little or no actual work, it
would still be structurally pressured to produce plausible-sounding friction patterns
and rules that never happened. Same failure shape as [[feedback_workflow_synthesis_ungrounded_specifics]]
and the exact thing [[feedback_artifact_citation_requirement]] already guards against
for published artifacts, just applied to a different output type (a self-retro instead
of a governance artifact).

**The fix — two additions, not a full rewrite:**
1. **Evidence-citation requirement.** Every claim in every section must cite a turn
   number, verbatim quote (≤15 words), tool-call name, or file path + diff hunk. An
   uncited claim is not a finding — omit it, don't soften it.
2. **Null-result exit path.** Each section may resolve to "No material [friction /
   decisions / rules] — insufficient session evidence." The schema must allow zero
   findings; a contract that always expects content is what forces fabrication on a
   thin session.

Also folded in: distinguish CORRECTIONS (user pushback) from CONFIRMATIONS (user
validated a non-obvious choice) — retros that only harvest corrections drift the
assistant away from approaches already proven to work, the same asymmetry the memory
system's own `feedback` type guards against. And: any proposed CLAUDE.md rule must be
checked against existing invariants/memory for overlap before being proposed — cite
what it would duplicate or extend, or state no existing rule covers it.

Full revised template text lives in the 2026-07-26 session transcript (originating
conversation); reproduce the structure above if drafting a fresh copy rather than
hunting for the transcript.

**Verdict on packaging:** evaluated as a candidate skill and rejected — this is a
tightening of the memory-writing discipline the auto-memory system already applies
every session (save-on-correction/confirmation, cite sources), not a distinct
workflow with its own triggers. A skill would add roster/routing overhead and risks
drifting out of sync with the memory system it disciplines. Kept as a reference note
instead — pull it up before running any end-of-session or cross-session retro prompt,
whether self-authored or pasted in by Gabriel.
