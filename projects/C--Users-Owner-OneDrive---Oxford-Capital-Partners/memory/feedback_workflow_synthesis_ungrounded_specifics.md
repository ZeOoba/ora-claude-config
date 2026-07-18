---
name: workflow-synthesis-ungrounded-specifics
description: "A multi-stage planning Workflow (Verify->Synthesize->Pre-mortem->Harden) can inherit and sharpen a narrative count/ID across stages without it ever being grounded in a real artifact — verify the concrete list/file exists before handing a downstream session or subagent a write task keyed on that number"
metadata:
  node_type: memory
  type: feedback
  originSessionId: aa2dede5-5779-4690-8dd5-16870ad3964b
---

Before authorizing a downstream session (or subagent) to WRITE against a specific count/ID claim inherited from a multi-stage planning Workflow, require the concrete underlying artifact (the actual row list, file, or query result) — not just the narrative number.

**Why:** During the 2026-07-17 top-10 ROI execution (`wf_e973a636-f5b`, [[project scratchpad]]), the hardened plan's synthesis pass described "19 trusted-clean archived+duplicate Tenant DB rows + their claimed original row" as if it were verified staged data, complete with a manufactured item ID (`#5a-19`) that didn't match this environment's real tracking convention (everything legitimate uses `OI-NNN` in `open-items-tracker.md`). No such list ever existed anywhere — scratchpad, Notion, or memory. It was synthesis-stage narrative that gained false specificity by being re-summarized across the workflow's own Verify -> Synthesize -> Pre-mortem -> Harden passes, each one treating the prior stage's prose as settled fact. The downstream session (routed the task via cross-session handoff) correctly refused to guess on a production tenant-data write and searched exhaustively before escalating — the item closed unfounded with zero writes and no harm done, but it cost real handoff cycles and could have gone the other way with a less careful executor.

**How to apply:**
- When a planning Workflow's final report hands off an item with a specific count/list claim ("19 rows," "the 5 clean cases"), verify a primary artifact backs it (a file, a live query result, a row-level export) BEFORE writing the execution brief — don't propagate a synthesis-stage number as if it were already-staged data.
- A pseudo-ID that doesn't match the environment's real tracking convention (here: anything not `OI-NNN`) is itself a tell that the item may be workflow-invented rather than sourced from ground truth.
- This is distinct from [[feedback_verify_probe_findings_before_acting]] (a single probe's hypothesis) and [[feedback_verify_before_repeating_session_claims]] (another session's status claim) — this failure mode is specific to a MULTI-STAGE workflow's own internal synthesis inheriting and sharpening an ungrounded specific across its own passes, not an external claim.
- Net lesson for cross-session task routing generally: the routing/connector mechanics worked fine here — the friction was (a) an external quota ceiling (Notion SQL query quota) and (b) this ungrounded-handoff issue. Both are worth checking before blaming the routing itself when a handoff stalls.
