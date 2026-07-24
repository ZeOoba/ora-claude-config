---
name: feedback-fixture-shaped-tests-certify-dead-branches
description: "A hand-built test fixture can encode the same wrong tool/field name as the code, so the test passes green while the production branch is dead — verify names against real transcripts/payloads"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: c076bce0-c979-485c-b83b-e41c9f6c4155
  modified: 2026-07-24T16:27:59.538Z
---

When a hook or parser matches on a **tool name, event name, or payload field**, a
hand-authored test fixture can invent the same wrong name the code uses. The test
then passes forever while the production path never once fires.

Found 2026-07-24: `hooks/eos-telemetry.py` counted subagent dispatch with
`tname == "Task"`, and `hooks/tests/test-eos-telemetry.py` built its fixture with
`"name": "Task"` and asserted `task_dispatched is True`. Both agreed; both were
wrong. The real tool is **`Agent`** — across all 1,396 local transcripts `Task`
appeared as a tool name **0** times and `Agent` **672** times. The signal reported
0.0% across 679 sessions and was surfaced every day by `eos-telemetry-rollup.py`
as the "most-frequently-missing signal" — an artifact read as a behavior finding.

**Why:** a fixture is an assertion about the outside world, not a fact about it.
Green tests prove the parser handles the shape you imagined, not the shape the
harness emits. A 0% or 100% metric is the tell — real behavior is rarely absolute.

**How to apply:**
- Before trusting any name-matching predicate, grep **real** transcripts/payloads
  for the literal string. `~/.claude/projects/**/*.jsonl` holds ground truth here.
- Treat a perfectly 0% (or 100%) telemetry signal as a **suspected broken emitter**
  until proven otherwise — don't report it as a behavior gap.
- Verify a fix end-to-end by running old vs new against a **real** captured input,
  not only the fixture. (A/B on one transcript proved this one.)
- Beware near-miss siblings when widening a match: `TaskCreate`/`TaskUpdate`/
  `TaskList`/`TaskGet`/`TaskOutput`/`TaskStop` are todo tools, not dispatch — keep
  such matches **exact**, never prefix/substring.

Related: [[feedback-verify-probe-findings-before-acting]] ·
[[feedback-verify-subagent-safe-claims]] · [[reference-probe-scan-sets]]
