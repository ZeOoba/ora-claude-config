---
name: reference-fleet-throttle-skip-catchup-burst
description: "recordedSkips 'global_limit' events are the Desktop scheduler's own concurrency cap rejecting a task's fire attempt, with a ~60s auto-retry; NOT a cron misconfiguration. Diagnosed 2026-07-20 investigating why ora-deal-aging-sla kept 5/10 recent throttle-skips post-retime. Root cause: catch-up-burst -- app closed past several tasks' scheduled fire times, then multiple overdue tasks (across BOTH cc and lams registries) hit the same global concurrency ceiling within seconds of each other when the app reopened. Some tasks (ora-sofr-direct-prefetch, ora-deal-command-board) won a free slot after 1 retry; ora-deal-aging-sla lost 5 straight retries (~4 min) before going dormant until the app's next open, ~14h later. No config/cron fix exists for this -- it's the app's own scheduler arbitration, outside ~/.claude's control surface. 2026-08-12: a SECOND, distinct dark-fleet mechanism confirmed -- host S0 Modern Standby sleep with the Desktop app still OPEN (STANDBYIDLE was 3h on AC and DC). Check Kernel-Power events, not the process list, before concluding app-closure; and prove execution from work product, never lastRunAt."
metadata:
  type: reference
  originSessionId: 41bfc8fa-2412-44b6-a527-f9a4631e86f5
  modified: 2026-08-12T19:55:27.252Z
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

**RECURRED 2026-07-24, and surfaced a SECOND, distinct consequence: a burst does not preserve
intra-cluster ORDERING.** Everything above is about *whether* a task fires. This is about *what order*
two tasks fire in when both are overdue — which matters whenever one task's spec assumes another
already ran. `ora-sofr-direct-prefetch` (10:10 ET) is written assuming `ora-am-brief` (06:00 ET) wrote
the Rate Snapshot page hours earlier, so its idempotency check normally finds the page fresh and
no-ops. In the 07-24 burst both backfilled within ~90 seconds: am-brief started 14:35:28Z, the
prefetch read the page at 14:36:26Z, saw the *previous* day's values, patched them, and am-brief
superseded that patch ~4 minutes later with identical values at full precision. Harmless that run —
but the latent failure is a Block A write landing between the consumer's read and its write, failing
`old_str` and posting a FALSE failure alert. Fixed in `ora-sofr-direct-prefetch` v1.1 (STEP 2 reads
Block A's `fetched_at`; a mismatch that re-resolves to already-fresh is SUCCESS, not failure).
**Generalize before assuming this is one task's problem:** any producer/consumer pair inside the
05:00–09:30 AM cluster (`ora-health-guard` counted 16 tasks there on 07-24) carries the same
assumption risk. `ora-health-guard`'s own 2026-07-24 Block A.0 independently reached the same
conclusion — "the catch-up burst does not preserve the intended intra-cluster ordering" — after its
Block B mirror went out 40 min AFTER the am-brief Daily Brief it is supposed to precede.

**Also 2026-07-24: a burst can drop a slot entirely, with NO throttle-skip logged.** `ora-am-brief`
did not run at all on 2026-07-23 — confirmed by absence of a run transcript, absence of any
`recordedSkips` entry for that date, and no Daily Brief email; the Rate Snapshot's `fetched_at`
jumped 07-22 13:25 ET → 07-24 10:40 ET (~45h stale). On 07-24 the same 06:00 ET slot WAS backfilled
4h35m late. So "no skip entry" does NOT mean "the task ran" — a silently dropped slot leaves no
trace in `recordedSkips` at all, and `lastRunAt` is single-valued so it cannot evidence a prior day.
The exact backfill cutoff is UNKNOWN and should not be asserted (n=2). To establish whether a task
ran on a given past date, use run transcripts (`scheduled-task name="<id>"` in
`~/.claude/projects/<project>/*.jsonl`) or its email/page output — not the registry.

**2026-07-24: the FIRST confirmed instance of the "lone task, no neighbours" pattern this file
flags as worth a fresh investigation — and it is `per_task_limit`, not `global_limit`.**
`ora-task-integrity-guard` began skipping once every 60s at 12:21:22 ET, alone, with no other task
skipping in the same instant. Distinguishing marks vs the catch-up burst above: (a) reason code is
`per_task_limit` (same-task double-fire guard), not `global_limit`; (b) single task, not a cluster;
(c) it did NOT self-clear — it ran 20+ min, where all three prior `per_task_limit` cases on record
cleared in 1-3 min (`check-dirty-files-session-pr` 3.0 min, `ora-lease-expiration-brief` 1.0,
`ora-pm-ledger` 1.0).

Onset was ~60s after an `update_scheduled_task` cron retime (07:00 -> 07:05), which made the retime
the obvious suspect. A concurrent session dry-running this exact task was ruled OUT as the cause —
its first dry-run touch was 11 min AFTER onset. **Disable -> enable was tested as a remedy and
FAILED:** skips stopped dead during the disabled window (12:38:23 -> 12:42:23 gap, confirming
disable suppresses the attempt) and resumed at 1/min immediately on re-enable. So a stale re-arm
state is NOT the mechanism — re-arming reproduces it.

**Do not conclude "the retime caused it" without weighing machine load.** At the time of this
episode the workstation had **36 `claude.exe` processes and ~13 live sessions** — heavy saturation
of the same ceiling described at the top of this file. A plausible reading that fits every
observation equally well: the retime merely made the task *due*, and it then joined the retry queue
against a ceiling that stayed saturated for 20+ min because of concurrent session load. The
scheduler's arbitration is closed-source (see the "why some tasks recover in 1 retry" caveat above)
— the timestamps do not separate "retime-triggered" from "saturation-sustained," so do not assert
either as root cause. Per the top-of-file verdict, the documented lever remains machine load
([[reference_lean_ram_toolkit]]), not per-task config.

**Operational note:** `ora-task-integrity-guard` must stay ENABLED regardless — it is the SOLE
fleet-integrity runner (LAMS twin retired), so disabling it to silence the metric would blind the
exact check that catches registry loss. Its `nextRunAt` stayed correct (next day 07:14 ET)
throughout, so scheduled execution was never at risk; only the skip metric was polluted.

**RECURRED 2026-08-11, and surfaced a THIRD consequence: burst adjacency gets misread as a cadence
collision, and nearly bought a pointless retime.** ~28h outage (Mon ~12:42 ET → Tue ~17:01 ET); on
reopen, 19 CC tasks drained serially at ~5-min intervals 21:01Z→22:45Z, with **1,199 throttle skips
in 24h across 16 tasks**. `ora-cc-snapshot-refresh` (`15 6 * * 1`) and `ora-lease-snapshot-refresh`
(`40 7 * * 1-5`) both regenerated `portfolio.json` 6 minutes apart (22:39Z/22:45Z) on a **Tuesday**.
I reported that as cadence clustering and recommended staggering; Gabriel reasonably said to do it.
It was wrong — the two are on different day-sets and sit **85 minutes apart** on their only shared
day (Monday), and `fleet-status.py` reported `same-time collisions 0` across all 59 tasks on both
fleets. They were adjacent in the **drain queue**, which cron does not control. A retime would have
fixed nothing and would have discarded the deliberate 2026-07-27 thin-the-AM-window placement.

**Rule: close `lastRunAt` timestamps are NOT evidence of a cron collision.** Before proposing any
retime, confirm all four:
1. `python ~/.claude/maintenance/fleet-status.py` → `same-time collisions`. It reads BOTH fleets; the
   CC-only `list_scheduled_tasks` cannot see LAMS crons. Zero collisions ⇒ nothing to stagger.
2. Day-of-week of the run vs. the task's cron day-set — a Monday-only task running Tuesday evening
   did not run on cadence.
3. Trailing-24h throttle-skip volume — hundreds-to-thousands across a dozen-plus tasks ⇒ burst.
4. A serial ~5-min ladder across many *unrelated* tasks in `lastRunAt` ⇒ drain order, not coincidence.

**`ora-health-guard` Block A.0 DID alert on this outage — verified, not assumed.** Checked via the
mail store (the actual record of what went out), not the transcript:
`outlook-sent-probe.ps1 -SubjectFile <file containing exactly "Overnight machine-offline detected">`
returned `ALREADY_SENT` / exit 10, matching `🌙 Overnight machine-offline detected — ora-health-guard
woke 708min late — 2026-08-11`, `sentOn 2026-08-11T17:05:00` ET, to Gabriel, no cc. Threshold logic,
4-minute latency, and routing canon all correct — **A.0 is working; do not re-investigate it as a
defect.** That probe invocation is the reusable way to answer "did this task's alert actually fire on
date X" — the subject stem is deliberately undated and anchored at position 0, and `-OnDate` scopes
by Outlook's own `SentOn` (host clock = ET). Note the throttle-skip count is a METRIC, not an alarm
channel, and `missed single cycle (currently open)` was 0 — so nothing else was expected to surface.

**`automation-health-monitor` also alerted, and did NOT false-all-clear despite running 2nd in the
drain.** It ran 21:02:28Z (17:02 ET), ~103 min before the drain finished, and emailed
`⚠️ Cowork Automation Alert — ora-health-guard-fail-aging-nudge + CC/MCP dispatch-throttle 2026-08-11`
at 17:07:57 ET (probe: `ALREADY_SENT`). The "monitor runs too early in a burst to verify the batch"
concern is ALREADY MITIGATED by its **Step 0.03** (v1.18, added 2026-08-09 after the prior outage):
it classifies `MULTI-DAY-OUTAGE-DETECTED` and stamps the report "treat this run's findings as a
post-outage recovery snapshot, not a normal-cadence run." Do not re-raise this as a gap. Its v1.19
(same day, mtime 17:16 ET) added cross-producer alert dedup so its email and A.0's cross-reference
each other instead of arriving as two apparently independent discoveries.

**OPEN (unresolved 2026-08-11):** `ora-health-guard-fail-aging-nudge` was `global_limit`-skipped at
17:02:27 ET; the registry shows `lastRunAt 21:03:28Z` (17:03:28 ET) but the monitor, writing at
17:16 ET, recorded no same-day `lastRunAt`. Either a genuine ~60s retry (monitor false-positive,
self-healed) or a cleared-but-never-attached dispatch stamp
([[reference_scheduler_lastrunat_stamped_at_dispatch]]) — **not separable from registry data alone.**
Resolve via `main.log` retry lines after 17:02:27 plus a work-product check, never by trusting
`lastRunAt`.

The lever for burst adjacency is uptime (or a freshness short-circuit inside the task), **never** a
cron change, which the burst ignores by construction. And per
[[reference_cron_retime_rearms_executed_slot]] a needless retime is not free — it can duplicate-fire
an already-completed slot.

**RECURRED 2026-08-12 — and the mechanism was HOST SLEEP WITH THE APP STILL OPEN, which this file's
standing framing ("app closed → chain builds up → burst on reopen") does not cover.** Gabriel asked
why `ora-am-brief` "hadn't fired." It had — the distinguishing evidence:

- **Power log, not the process list, is the detector.** `Get-WinEvent` System / Kernel-Power +
  Power-Troubleshooter showed **zero power-state events from 2026-08-11 19:38:20 → 08-12 11:00:17 ET
  (15h22m)**. The machine sat in S0 Modern Standby overnight.
- **First fire after resume was 13 seconds later** (`ora-health-guard` 11:00:32 vs the 11:00:18
  resume). 10 CC tasks then backfilled 11:00:32–11:15:19 spanning cron slots 05:15→10:10. That
  13-second resume→fire coupling is the cleanest burst signature on record — the scheduler resumed
  the instant the host did.
- **The app was never closed.** Oldest `claude.exe` PIDs alive continuously since 08-11 17:01:19,
  i.e. across the entire dark window. So "is the Desktop app open?" is NOT sufficient to explain a
  burst — check power events before concluding app-closure. (The 08-11 burst above WAS app-closure:
  machine woke 16:59:36, app launched 17:01:19, drain began 17:01:36. Two consecutive late mornings,
  two *different* proximate mechanisms.)
- **Root cause is a power setting, and it is quantified:** `SUB_SLEEP / STANDBYIDLE` =
  `0x2a30` = **10800 s = 3 h idle on AC *and* DC**; `HIBERNATEIDLE` = 0 (disabled); scheme Balanced;
  only S0 Low Power Idle available (S1/S2/S3 all unavailable — Device Guard + firmware). So the host
  sleeps every night regardless of being plugged in, and stays dark past the 05:15/06:00/07:05 slots
  until touched.

**`lastRunAt` was NOT what proved it ran** — per [[reference_scheduler_lastrunat_stamped_at_dispatch]]
that value is stamped at dispatch (and again at stale-clear), so it cannot evidence execution. The
proof was an **output** check: the Rate Snapshot page carried `prefetch_status: OK` /
`fetched_at: 2026-08-12 11:20 ET` with a full Block A rewrite. Registry timestamps opened the
question; the work product closed it.

**Defect worth knowing: `ora-am-brief` mis-diagnoses its own late fire in its run note.** Its
2026-08-12 note asserts *"Desktop app opened ~11:04 after an overnight offline window."* Both halves
are wrong — the app was open throughout, and the resume was 11:00:17. The brief has no visibility
into power events or process lifetimes and is inferring app-closure from lateness alone. Treat that
sentence in any Block A run note as narrative, not evidence, and do not let it steer remediation
toward "remember to open the app" when the lever is the sleep timeout.

**Ruling (Gabriel, 2026-08-12): never sleep on AC** — `powercfg -change standby-timeout-ac 0`,
DC left at 3 h. Chosen over a 05:45 wake timer because wake timers are unreliable under S0 Modern
Standby, and over retiming the brief because retiming helps only one of the ~10 tasks in the
overnight window. Claude cannot apply this (system-setting change is operator-run by policy).

**APPLIED AND VERIFIED 2026-08-12 ~16:00 ET** — Gabriel ran it; `STANDBYIDLE` AC now reads
`0x00000000` (NEVER), DC unchanged at `0x2a30` (3 h), HIBERNATEIDLE 0/0. Two things this does NOT
close, so don't read the verified setting as proof the symptom is gone:
1. **On battery the original failure is fully intact** — DC is still 3 h by design. An overnight on
   battery reproduces the 08-12 dark window exactly.
2. **`UNATTENDSLEEP` could not be read** — the setting is hidden by default in this scheme
   (`powercfg /query` returns no index for it; revealing it needs
   `powercfg /attributes SUB_SLEEP 7bc4a2f9-d8fc-4469-b07b-33eb785aaca0 -ATTRIB_HIDE`). Irrelevant
   while AC never sleeps, but it becomes the governing timeout if anyone later adopts the
   wake-timer approach.

**The setting is verified; the FIX is not.** Confirmation requires observing an on-time 06:00 ET fire
— check `ora-am-brief`'s work product (Rate Snapshot `fetched_at`), not `lastRunAt`, on 2026-08-13.

Related: [[reference_fleet_status_dual_read]] (dual-registry read mechanics),
[[reference_lean_ram_toolkit]] (the RAM ceiling this throttle protects),
[[reference_cc_scheduler_filepath_mechanism]] (editing SKILL.md is the authoritative fix path).
