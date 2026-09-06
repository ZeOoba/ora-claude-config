---
name: reference-lastruntime-restamped-on-modern-standby-resume
description: "A long wall-clock scheduled-task run on this laptop is almost always Modern Standby, not a hang — and Windows re-stamps LastRunTime on resume, which forged a false ALARM_SILENT_INCOMPLETE"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 51c284c7-491a-4b56-acb3-f1e531285125
  modified: 2026-09-05T19:58:45.178Z
---

**A scheduled task whose wall-clock span looks impossibly long on LAPTOP-CSHSCBE6 was probably ASLEEP, not hung.** Verify before treating duration as a defect. The machine enters Modern Standby ~20x/day.

Two independently misleading behaviours, both found 2026-08-25 on the CC mirror deploy:

1. **Windows re-stamps `LastRunTime` on resume.** The run launched 13:13:15 (TaskScheduler event 129, PID 20520), slept 13:15:30→15:22:22, and Windows then reported `LastRunTime = 15:22:23` — one second after the wake event. The operational-log 129/100 event holds the TRUE start; `Get-ScheduledTaskInfo`'s `LastRunTime` does not survive a suspension.
2. **`ExecutionTimeLimit` does not fire across the sleep.** The task is `PT30M` yet spanned 2h15m and completed rc=0. That combination is itself the tell: a PT30M limit plus a 2h15m span plus rc=0 is impossible unless the process was suspended.

3. **`LastTaskResult` is a TOMBSTONE on a disabled task, and is not an output test on an enabled one.** Found 2026-09-05 by an `ora-health-guard` follow-up that had reported three Windows tasks as "failing" off `Get-ScheduledTaskInfo` alone. Two of the three were not defects: `ORA Stuck-Session Watchdog` was returning 0 and running cleanly every 30 min by the time it was checked, and **`ORA PM Crons` is Disabled by design** (superseded by CC task `ora-pm-daily-crons`, OI-162) — its `2147943467` was frozen from its last enabled run on 2026-08-16 and had been quoted as if live. (It also decodes as `0x8007042B` ERROR_PROCESS_ABORTED, not `0x8007041D`; decode the hex, don't eyeball it.) Conversely `ORA Fleet Dead-Man` logged TaskScheduler **201/102 "successfully completed"** while writing nothing to `maintenance\fleet-deadman.log` for 2.5 days — success events and a benign-looking rc coexisting with zero production.

**The only trustworthy test is OUTPUT FRESHNESS.** Stat the artifact the task exists to write (`_state/fleet-heartbeat.json`, `fleet-deadman.log`, the Notion beacon) and compare it to now. Exit codes, `LastTaskResult`, `LastRunTime` and even event 201/102 are all proxies that fail independently on this laptop — this is [[feedback_verified_null_vs_inferred_null]] applied to Task Scheduler, and the same readability-vs-liveness split that `log_liveness.py` exists to enforce for the Desktop logs. Check `State` before quoting any result code, and never read `0xC000013A` as a failure without the output test ([[reference-mirror-deploy-0xc000013a-is-usually-benign]]).

**Do the arithmetic before diagnosing.** Pair System-log `506` (entering Modern Standby) / `507` (exiting) inside the run window and subtract. For the incident: 135.1 min wall-clock − 126.9 min suspended = **8.3 min of actual execution**, squarely in the healthy 5–19 min band. Note `507` and `506` can appear in the SAME second (a wake that immediately re-sleeps) — pair them in timestamp order or the total is wrong.

**Why this matters beyond one incident:** the mirror classifier compared the beacon's true `startedAt` against the re-stamped `LastRunTime`, saw 2h09m of skew, and emitted `ALARM_SILENT_INCOMPLETE` with the reason *"this run wrote no beacon"* — flatly false; the beacon's own `pid` matched the launch event. Fixed in [PR #305](https://github.com/ZeOoba/oxford-command-center/pull/305) (`5074204`, merged `34a0372`): correlate on the beacon's `finishedAt` vs the run's completion event (43ms apart, and neither is re-stamped), and subtract suspended minutes before the `ALARM_RUN_STUCK` threshold test.

⛔ **Do NOT "fix" a long run by adding a wall-clock timeout.** On this machine that kills every sleep-spanning run. Any duration bound needs the same suspension-awareness. This is the same trap as [[reference-am-cluster-late-wake-root-cause]] — stop re-deriving a hang hypothesis for what is machine lifecycle.

⚠️ **`fix/deploy-mirror-deploy-timeout` is an EMPTY branch** — 0 commits ahead of main, 111 behind, empty diff. The `ora-command-center-mirror-drift-check` SKILL.md points at it as "the relevant fix"; that pointer is wrong. There is no timeout work on it.

**Still open (not a cause of the above):** `npm run build:mirror` at `deploy-mirror.ps1:273` is an unbounded external call — the same shape [PR #248] bounded for the wrangler deploy in step 3. Real latent gap, needs suspension-aware bounding, awaiting Gabriel's call.

Related: [[reference-mirror-deploy-0xc000013a-is-usually-benign]], [[reference-command-center-mirror-deploy-gap]].
