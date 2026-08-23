---
name: project_governor_drift_probe_dscr_scaling_multiplier_fix_2026-08-22
description: "governor-drift-probe.py DSCR changelog scaling-multiplier false positive FIXED (commit ecf7b42, main) + a real duplicate-work collision discovered mid-task: 3+ parallel sessions independently working the identical fix"
metadata:
  node_type: memory
  type: project
  originSessionId: fa20bb38-6bd1-40cd-94dd-85a41d1573c2
  modified: 2026-08-22T16:49:37.080Z
---

# governor-drift-probe DSCR-changelog-scaling-multiplier fix — landed, plus a duplicate-session finding

`deal-comparison/SKILL.md:153`'s v1.2 changelog entry (see [[event_log]] 2026-08-22 for
the full quoted text) narrates a past bug's computed-value scaling factor, not a
threshold — but `governor-drift-probe.py` misread it as a live governor declaration.
Blocked every push; overridden via `allow-hook-test-failure`
**8 times by at least 3 distinct sessions** across 2026-08-21/22 before this landed.

**Fixed** in `maintenance/governor-drift-probe.py` (`RE_DSCR_COMPUTED_SCALING` +
`_dscr_scaling_multiplier_spans()`) and pushed to `main` at commit `ecf7b42` — see
[[event_log]] 2026-08-22 for the full technical writeup (root cause, 3-round adversarial
review findings/fixes via `eos-review-gate.py`, 8 new regression tests, accepted
residuals). Full detail lives there; this memory exists for the second finding below.

## Why: recurring override churn was actively blocking pushes

**How to apply:** if `governor-drift-probe.py` or `test-governor-drift-probe.py` flags
again on a changelog/audit-note line describing a past bug's magnitude (not a governor
declaration), check whether it's a variant this fix's suppressor doesn't cover before
minting another override token — the accepted residuals (negation-blind, topic-blind
`RE_CHANGELOG_CONTEXT` gating) are documented in-code just above
`RE_DSCR_COMPUTED_SCALING`.

## The duplicate-session finding — the more important part to remember

While landing this fix, discovered **at least 2 other parallel sessions were
independently working the identical false positive at the same time**:

- A fully-formed, unmerged competing fix on branch `fix/governor-drift-probe-changelog-fp`
  (commit `2155fb4`, worktree `fix-governor-drift-probe-changelog-fp`) — a materially
  different design (a 3-signal line-wide gate: tilde-glued value + literal "corrected" +
  a separate plain-1.25 restatement, no proximity/adjacency requirement between the
  three signals). Inspected and found a plausible false-negative gap of its own (a real
  drift sharing a line with an unrelated "corrected"/"1.25" mention elsewhere would be
  masked, since none of its three signals are scoped to each other or to the value) —
  never adversarially reviewed before this discovery.
- A claim on the IDENTICAL `hooks-override-auth-governor-dscr-changelog` slug by session
  `8c98eacf`, claimed 2026-08-22T12:28:11 — 4 minutes into my own work on the same slug,
  with no `--force`/`prior_claim` trail, suggesting `claim_work.py`'s claim either
  silently overwrote mine or mine had already lapsed. Its recorded `paths` pointed under
  the OneDrive project folder rather than the actual `~/.claude` repo (its description
  said "currently uncommitted in shared checkout working tree", but the shared checkout
  had zero uncommitted changes to these files when checked) — strong evidence
  `claim_work.py` was run from the wrong `cwd` (the default project directory, not
  `~/.claude`).
- Neither session was reachable via `ListAgents`/`SendMessage` (not listed by a
  resolvable name in `ListAgents`'s peer-session output, despite ~16 peer sessions
  showing).

**Why:** the override-usage-log evidence (5 overrides by 3 sessions in the 24h before
this task started, then 3 MORE overrides by session `ebb79ea0` while this fix was in
flight) shows this false positive was actively, repeatedly hitting multiple concurrent
sessions — consistent with the SAME underlying user request (or a very similar one)
having been dispatched to 3+ parallel Claude Code sessions simultaneously, each
independently deciding to fix the root cause rather than override again.

**How to apply:** this is worth Gabriel's attention as a process question, not a code
question — was dispatching this fix to multiple parallel sessions intentional (e.g. a
deliberate race for speed) or an artifact of how work got queued/scheduled? If the
latter, tightening whatever dispatched it would save the token/wall-clock cost of 3
sessions independently re-deriving the same root cause and building competing fixes. See
[[event_log]] 2026-08-22 entry for the full incident detail. Also worth checking whether
`claim_work.py`'s claim-vs-refuse semantics behaved as documented here (a refusal was
expected against a live claim absent `--force`, but none was observed) —
[[reference_concurrent_session_duplicate_hardening_work]] may need a follow-up note.

Related: [[event_log]] · [[reference_concurrent_session_duplicate_hardening_work]] ·
[[reference_event_log_uncommitted_backlog]] (a SECOND collision hit while writing this
memory's own event_log entry — a concurrent session's commit clobbered the first
uncommitted append before it could be isolated; recovered by re-appending and
committing immediately via the direct-blob-write technique, no data lost, but it's a
second data point for how much concurrent-session activity this checkout is carrying
right now).
