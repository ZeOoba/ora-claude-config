---
name: reference_ground_truth_auditor_pending_approval_mechanism_2026-09-12
description: "What writes to maintenance/_state/ground-truth-pending-approval/ (ora-ground-truth-auditor, by design) -- and a correction to an in-session claim that one of its drafts was fabricated"
metadata: 
  node_type: memory
  type: reference
  originSessionId: f9931a96-2f5d-4ca0-9f65-188f6d6b2792
  modified: 2026-09-12T22:03:18.540Z
---

`maintenance/_state/ground-truth-pending-approval/<date>/<run_id>/` is written by
**`ora-ground-truth-auditor`** (CC/MCP scheduled task, cron `0 4 * * *` ET) -- a
legitimate, spec-driven system, not an anomaly. Design:
`docs/superpowers/specs/2026-09-10-ground-truth-auditor-design.md`; runner:
`scheduled-tasks/ora-ground-truth-auditor/SKILL.md`; code:
`maintenance/ground-truth-run-index.py` / `ground-truth-side-effects.py`.

**What it does:** nightly re-derives every factual claim the previous 24h of fleet
runs made, from primary sources only (never a prior summary/log line), and reports
IDEMPOTENCY / CLAIM ACCURACY / STALENESS / FRESHNESS on one digest email to
`ggoldberg@oxfordra.net`. Per its own §7 (Hard Invariant 1 compliance): any correction
that would need a **retraction email or a published-page edit** is drafted in full to
`_state/ground-truth-pending-approval/<date>/<run_id>/` and **named in the digest**,
never sent or applied automatically. Systemic findings also get OI ids allocated via
`allocate-oi-id.py` (never hand-computed) and appear in the digest.

**Correction to an in-session claim (2026-09-12):** while fixing the
`ora-doctrine-integrity-guard` XREF-MISSING alarm on `session-context.md:20`
(-> [[reference_session_context_xref_probe_state_root_gap_2026-09-12]], if written),
a `correction-note.md` under this mechanism claimed "Filed OI-287." Checking
`open-items-tracker.md` at that moment found no OI-287 and the claim was reported to
Gabriel as false. It was not false -- it was **early**: the auditor's own run was
still composing its digest and had not yet reached its OI-filing step
(`oi-id-reservations.log` / digest for 2026-09-12 both show OI-278..OI-287 filed
20:48:26Z-20:52:55Z, all attributed to session `97171ad9`, the auditor's own run).
Re-checking minutes later confirmed all ten. **Lesson: an absence in a fast-moving
shared log during a run still in progress is a timing artifact, not proof of
fabrication -- re-check before repeating a "this claim is false" verdict**, same
principle as [[feedback_findings_decay_recheck_before_writing]] and
[[feedback_verify_before_repeating_session_claims]], applied here to a negative
finding rather than the usual positive one.

**Duplicate work note (RESOLVED):** OI-287's content ("session-context-xref-probe.py
search_roots() omits maintenance/_state ... line-20 pause bullet stale") is the
identical root cause independently diagnosed and already fixed in the same session,
minutes earlier, by hand (added `maintenance/_state/xref-extra-roots.json`, deleted
the stale session-context.md line-20 bullet, re-verified probe exit 0). OI-287 was
allocation-only (ledger + digest, no `open-items-tracker.md` row) when this was first
written; filed directly as CLOSED in
[open-items-tracker-history.md#OI-287](open-items-tracker-history.md#OI-287) the same
day, citing this fix, so it will not be independently re-worked.

**Also confirmed same day:** `worktrees/gtr-remediation` (branch
`fix/ground-truth-remediation-2026-09-12`) has genuine live uncommitted WIP -- a
modified `scheduled-tasks/ora-ground-truth-auditor/SKILL.md` and a new
`docs/superpowers/plans/2026-09-12-ground-truth-remediation.md` -- confirming another
session is actively remediating the rest of the 2026-09-12 digest batch
(OI-278..OI-286, OI-288) there. Left untouched on purpose; do not duplicate without
checking that worktree's state first.
