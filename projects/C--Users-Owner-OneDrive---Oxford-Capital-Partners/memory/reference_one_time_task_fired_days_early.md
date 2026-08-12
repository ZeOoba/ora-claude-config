---
name: reference-one-time-task-fired-days-early
description: "A one-time scheduled task can fire DAYS BEFORE its fireAt — proven 2026-08-12: ora-pm-ledger-retime-efficacy-check held fireAt 2026-08-19T16:30 ET and dispatched 2026-08-12T17:49 ET, 6d22h41m early. Its prompt asserted 'Today is 2026-08-19' as baked-in prose, so a task that trusted that text would have reported a 7-day efficacy verdict computed from a window that had not occurred. Always derive 'today' from the system clock, never from prompt text; and range-check any analysis window against the data's actual last record before computing."
metadata: 
  node_type: memory
  type: reference
  originSessionId: f27b89dc-0bd5-4512-b720-f8eefc5a0837
  modified: 2026-08-12T21:54:27.351Z
---

**The defect.** One-time tasks carry `fireAt` (epoch ms) instead of a cron. On 2026-08-12 the CC/MCP
registry entry for `ora-pm-ledger-retime-efficacy-check` read:

- `createdAt` = 2026-08-12T16:58:56 ET
- `fireAt`    = **2026-08-19T16:30:00 ET**
- actual dispatch = **2026-08-12T17:49 ET** — ~51 minutes after creation, **6d 22h 41m early**

The registration itself was correct (fireAt was exactly the intended +7 days). The scheduler fired it
anyway. Mechanism unknown and **not** asserted here — n=1, and the Desktop scheduler's arbitration is
closed-source (same caveat as [[reference_fleet_throttle_skip_catchup_burst]]). What is established is
only that the early fire happened and is reproducible from the registry values above.

**Why it matters far more than a normal mistimed run.** This class of task *analyses a date window*.
Its prompt carried `Today is 2026-08-19` as baked-in prose plus a mandated window of
`2026-08-13 → 2026-08-19` and even a pre-filled subject line (`<N> of 7 days missed`). Every one of
those was false at execution time — the send-log's latest record was 2026-08-12T16:11:46, so **0 of 7
days had elapsed**. A run that trusted its own prompt would have emitted a confident 7-day efficacy
verdict over an empty window. The prompt's own no-fabrication clause is what saved it, but only
because the clock was checked first.

**The rule.** Derive "today" from the system clock (`datetime.now()`), never from prompt text — this is
[[feedback_prompt_current_state_prose]] applied to the date field itself, which is the one field most
likely to be baked in and least likely to be questioned. Then range-check the requested window against
the data's actual last record *before* computing anything, and report a COVERAGE GAP rather than an
estimate when they don't overlap. A window entirely in the future is a null result to be reported, not
a number to be produced.

**Also worth carrying from the same run:** the mandated subject line presumed a computable answer.
When the honest finding is "cannot be computed," the subject must say so — emitting a fabricated `N`
to satisfy a template is the exact failure [[feedback_verified_null_vs_inferred_null]] warns about.

**Corroborated in the same run (no new investigation needed):** `ora-pm-ledger`'s pre-retime baseline
recomputed from the live send-log matches its recorded values exactly (9 delivered / 12 no-delivery of
21 days; 6 on-slot; 3 off-slot). And `recordedSkips` showed 107 suppressed dispatches on that task
alone (71 `per_task_limit`, 36 `global_limit`) — consistent with, and already fully explained by,
[[reference_fleet_throttle_skip_catchup_burst]]. Do not re-derive either.
