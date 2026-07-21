---
name: reference-fleet-throttle-skip-catchup-burst
description: "recordedSkips 'global_limit' events are the Desktop scheduler's own concurrency cap rejecting a task's fire attempt, with a ~60s auto-retry; NOT a cron misconfiguration. Diagnosed 2026-07-20 investigating why ora-deal-aging-sla kept 5/10 recent throttle-skips post-retime. Root cause: catch-up-burst -- app closed past several tasks' scheduled fire times, then multiple overdue tasks (across BOTH cc and lams registries) hit the same global concurrency ceiling within seconds of each other when the app reopened. Some tasks (ora-sofr-direct-prefetch, ora-deal-command-board) won a free slot after 1 retry; ora-deal-aging-sla lost 5 straight retries (~4 min) before going dormant until the app's next open, ~14h later. No config/cron fix exists for this -- it's the app's own scheduler arbitration, outside ~/.claude's control surface."
metadata:
  type: reference
  originSessionId: 41bfc8fa-2412-44b6-a527-f9a4631e86f5
  modified: 2026-07-21T14:16:59.149Z
---

**What the metric means.** `recordedSkips[taskId]` entries with `reason: "global_limit"` are written by
the Desktop app's own scheduler when a task's fire attempt is rejected because too many
scheduled-task sessions are already concurrently active (a machine-wide RAM/concurrency ceiling --
same "~5.7GB workstation ceiling" several SKILL.md files independently reference). The scheduler
auto-retries the same task roughly every 60 seconds; each failed retry appends another skip event.
`reason: "per_task_limit"` is a distinct, narrower throttle (seen on `ora-cc-schematic-refresh`,
2026-07-14) -- likely a same-task double-fire guard, not global contention.

**2026-07-20 investigation (Monday).** `fleet-status.py` showed 10 throttle-skip events in the
trailing 24h, 5 of them on `ora-deal-aging-sla` -- the top contributor even after that morning's
retime (09:20->09:25) had already fixed a genuine same-day cron collision with
`ora-site-exposure-probe` ([[project_2026-07-20_stale_audit_report_reconciliation]] context; see
also the fleet-status.py collision-detector fix landed the same session,
`reference_fleet_status_dual_read.md`). Direct inspection of both registries'
`recordedSkips` (CC: `...claude-code-sessions\...\scheduled-tasks.json`; LAMS: the
`local-agent-mode-sessions` sibling) showed:

- At 2026-07-20 14:52:25 UTC (10:52:25 ET) -- **90+ minutes after** `ora-deal-aging-sla`'s scheduled
  09:25 ET fire -- three tasks (`ora-sofr-direct-prefetch`, `ora-deal-command-board`,
  `ora-deal-aging-sla`) ALL hit `global_limit` within 6 milliseconds of each other. Classic
  catch-up-burst signature: the app had been closed/idle past all three tasks' AM-window fire
  times, and on reopen the scheduler tried to fire the whole overdue backlog at once.
- `ora-sofr-direct-prefetch` and `ora-deal-command-board` each recovered after exactly ONE retry
  (no further skip events logged for either).
- `ora-deal-aging-sla` did NOT recover -- it retried every ~60s and lost the concurrency race 4 more
  times (5 total, 14:52:25 through 14:56:25 UTC), then went dormant. Its `lastRunAt` shows
  2026-07-20T23:27:59Z (23:27:59 ET) -- it did not actually complete until the app's NEXT open,
  ~12.5 hours after the last recorded skip and ~14 hours after its scheduled 09:25 ET slot.
- The LAMS registry shows the identical shape on a different day: `ora-cowork-heartbeat` lost
  SEVEN straight `global_limit` retries in one historical burst (2026-07-13ish, already decayed out
  of the 24h window) before recovering; `automation-health-monitor` lost 3 in a row on 2026-07-20,
  starting ~13 minutes after the CC-fleet burst above -- consistent with one shared machine-wide
  concurrency ceiling contended by BOTH fleets, not two independent per-fleet limits.

**Why some tasks recover in 1 retry and others don't:** unknown at the arbitration-internals level
(the Desktop scheduler's queue/priority logic is closed-source, outside `~/.claude`). The evidence
only supports "some tasks reliably lose the race longer than others during a burst" -- not a
root-cause for WHY. Do not over-claim a mechanism here beyond what the timestamps show.

**Verdict: not a bug, no code fix applies.** This is expected behavior of the documented
"Scheduler doctrine" (session-context.md: both fleets fire only while the Desktop app is open;
closing it lets the whole overdue chain build up into a catch-up burst on next open). The
09:20->09:25 retime fixed a REAL, separate defect (literal same-day double-booking); this
throttle-skip residual is a structural side effect of how long the app sits closed before
reopening, not of `ora-deal-aging-sla`'s cron value. The only real lever is keeping the Desktop app
open/awake through the business day (already documented) -- there is nothing to patch in
`fleet-status.py`, the registry, or the SKILL.md.

**If this recurs:** don't re-derive from scratch -- check whether the flagged task's skip
timestamps cluster within seconds of OTHER tasks' skip timestamps (same burst) before assuming a
config problem. A lone task skipping repeatedly with NO neighboring skips at the same instant would
be a different, more suspicious pattern worth a fresh investigation.

**RECURRED 2026-07-21, confirming the pattern rather than a new problem.** A routine fleet-status
recheck the next day found the 24h count had moved 10->18. Same signature, different tasks and a
shorter delay: at 2026-07-21 13:46:48 UTC (09:46:48 ET) -- only ~21 minutes after `ora-am-brief`'s
06:00 ET slot and ~21 min after `ora-deal-aging-sla`'s 09:25 ET slot (both well overdue by then) --
`ora-am-brief`, `ora-deal-aging-sla`, and `check-dirty-files-session-pr` (the 30-min dirty-file
poller) all hit `global_limit` within 5 milliseconds of each other. `ora-am-brief` and
`ora-deal-aging-sla`'s new event each recovered/stopped after that single hit; `check-dirty-files-
session-pr` lost the race repeatedly instead -- 6 straight `global_limit` retries at ~60s intervals
(13:46:48 through 13:51:48 UTC) before dropping out of the recorded window, the same "some task
loses the race longer than the others" shape `ora-deal-aging-sla` showed on 07-20. Collisions stayed
clean (`{}`) throughout -- confirms the collision-detector fix holds independently of this separate,
expected throttle behavior. No new action taken; this entry exists precisely so a second occurrence
doesn't trigger a fresh investigation from zero.

Related: [[reference_fleet_status_dual_read]] (dual-registry read mechanics),
[[reference_lean_ram_toolkit]] (the RAM ceiling this throttle protects).
