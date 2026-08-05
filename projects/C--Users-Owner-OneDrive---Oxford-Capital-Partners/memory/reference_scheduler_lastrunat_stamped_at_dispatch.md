---
name: reference_scheduler_lastrunat_stamped_at_dispatch
description: "The Claude Desktop scheduler stamps lastRunAt at dispatch, not completion — a phantom dispatch that never confirms still advances it, so fleet-status.py reports silently-dead tasks as healthy"
metadata: 
  node_type: memory
  type: reference
  originSessionId: c9af9d3a-ea56-47fe-aff8-4f8c6e61b383
  modified: 2026-08-05T19:58:03.910Z
---

**`lastRunAt` is written at DISPATCH, not at completion. A task that produced nothing can look freshly-run to every on-machine detector.**

Root-caused 2026-08-03 after `ora-health-guard` produced nothing on **2026-07-31, 08-01 and 08-02** — three consecutive days — and was found only because a human noticed its beacon page was four days stale.

## The mechanism

From `%APPDATA%\Claude\logs\main.log` / `main1.log` (`[CCDScheduledTasks]`):

```
07-31 08:50:44  Spawning new session for scheduled task ora-health-guard { lastRunAt: 2026-07-31T12:50:43Z, missed: 2026-07-31T09:15:00Z }
07-31 09:36:10  Cleared stale pending dispatch for: ora-health-guard        <-- no "Confirmed task run"
08-01 10:06:09  Spawning ... { lastRunAt: 2026-08-01T14:06:09Z }
08-01 10:22:07  Cleared stale pending dispatch
08-02 05:25:19  Spawning ... { lastRunAt: 2026-08-01T14:22:07Z, missed: undefined }
08-02 05:30:40  Cleared stale pending dispatch
08-03 11:29:26  Spawning ...  ->  11:29:30  Confirmed task run              <-- a healthy run confirms in ~4s
```

A dispatch issued while the desktop app is still starting never attaches and is garbage-collected minutes later. **But `lastRunAt` was already advanced at spawn, and the stale-clear advances it again** — 08-02's spawn carried `lastRunAt` = the 08-01 stale-clear timestamp (10:22:07 EDT = 14:22:07Z), which made it compute `missed: undefined` and never retry.

**The failure erases its own evidence on-machine.**

## What this invalidates

- **`fleet-status.py`'s missed-cycle list is a FLOOR, not a census.** It reads `lastRunAt`. It reported `ora-health-guard` healthy — and omitted it from the missed list — through the entire 3-day outage. Never quote a green fleet-status line as proof a task ran.
- Same for `lastRunAt` read directly from either registry, and for `recordedSkips` (health-guard had **zero** — it was never *skipped*, it was phantom-dispatched, a different and invisible class).
- **Fleet-wide, not health-guard-specific:** `Cleared stale pending dispatch` appears **115+ times across 20+ tasks** in those logs (top: ora-cowork-heartbeat 15, ora-aaos-expire-leases 14, ora-pm-ledger 10, ora-lease-snapshot-refresh 10, ora-aaos-publish-contracts 10).
- **Not the overnight-offline pattern.** On 07-31 the app was up and `ora-am-brief` / `ora-deal-aging-sla` / `ora-aaos-publish-contracts` all confirmed within 4-5s in the 09:39 wave. The failed 08:50:44 wave was 4 tasks spawned during app startup, all cleared stale together at 09:36. Do not misfile a phantom dispatch as a late wake — see [[reference_fleet_throttle_skip_catchup_burst]].

## Re-measured 2026-08-05 (Code session) — rate, spread, and a predictor

Re-run over `main1.log` + `main.log`, **2026-07-31 21:06 → 2026-08-05 15:07**:

- **74 `Confirmed task run` vs 55 `Cleared stale pending dispatch` — 43% of ALL dispatches never started.** By fleet: **CC/MCP 47 stale / 54 confirmed (47%)**, **LAMS/Cowork 8 / 20 (29%)**. It is not a CC-only bug.
- Worst: `ora-skill-cache-drift-alert` 10 · `ora-aaos-expire-leases` 7 · `ora-lease-snapshot-refresh` 5 · `ora-cowork-heartbeat` 4 (**the dead-man's own pulse**) · `ora-task-integrity-guard` 4 · `ora-aaos-publish-contracts` 4.
- **The stale-clear is what stamps `lastRunAt`** — not (only) the spawn. Registry values match the clear timestamp to the millisecond: guard `2026-08-05T11:20:22.767Z` = 07:20:22 ET clear; broker-touch `2026-08-02T17:55:29.045Z` = 13:55:29 ET clear.
- **⚠️ ROOT CAUSE FOUND same day — mostly self-inflicted.** ORA's own `stuck-session-watchdog.ps1` was killing the desktop app's Electron children: **155 `electron_renderer`**, 391 `electron_utility`, 88 `electron_gpu`, 4 `electron_main`. Its kill filter excluded only short command lines and `--resume=`; Electron's children are named `claude.exe`, carry 851–5016-char command lines, pass no `--resume=`, and are long-lived by design. Fixed `e441130` (exclude `--type=` and `WindowsApps\Claude_`; both fail safe toward not killing). **Re-measure the rate before quoting the 44% figure — it describes the broken state.**
- **The renderer is the mechanism, not merely a predictor** (superseding the first day's hedge, which conflated process COUNT with renderer PRESENCE): renderer present → **74 of 76 confirmed**; renderer absent → **0 of 53**. Network is a red herring: renderer absent + network fine = 31 stale/0 confirmed; renderer present + network DOWN = 0 stale/4 confirmed.
- **Renderer-absence signature (raw first-day measurement, kept for the method):** all **54/54** confirmed CC dispatches had an `electron_renderer` in the app's own `[process-memory]` top-list; **45/47** stale ones had **none** (median electron proc count 15 vs 5). This generalises "dispatched while the app was still starting" — the common factor is *renderer absent*, which also covers post-sleep and post-network-outage teardown. Not sufficient: 5 confirmed runs happened at electron(5) too. Failing spawns never reach `LocalSessions.checkTrust`; nothing is logged between `Spawning` and the ~10-min sweep that clears it.
- Triggers, CC fleet: 19/47 within 3 min of a `net::ERR_FAILED` burst · 12/47 within 20 min of `likely sleep: power_event`. Confirmed runs: 3/54 near a network error.
- **Do not assume the inverse.** A *confirmed* run can still produce nothing — `ora-health-guard` 2026-08-04 shows `Spawning 06:04:47` **and** `Confirmed task run 06:05:18`, ran end-to-end, but wrote no Notion beacon because Notion was down. Confirmed-but-no-output is a separate class — the confirm line proves the session *attached*, never that it produced anything. Both classes need an OUTPUT check; see [[feedback_verified_null_vs_inferred_null]].

## How to detect it

Only an **output** check works. Registry state is compromised by construction.

- **AUTOMATED since 2026-08-05 — `maintenance/phantom-dispatch-probe.py`** (20 unit tests, `test-phantom-dispatch-probe.py`). Pairs every `Spawning` against its `Confirmed task run for:` across `main.log`+`main1..4.log`, both fleets. Exit 0 clean · 1 phantom found · **2 = could not look** (logs unreadable — never conflated with clean). Runs from `fleet-deadman.ps1` (Windows Task Scheduler, daily 07:30) as check (4), deliberately OUTSIDE both fleets: `ora-task-integrity-guard` was itself phantom-dispatched on 08-04 AND 08-05, so an in-fleet check is silent exactly when it is needed. Findings land in `_state/phantom-dispatch.{log,json}` and in the desktop `FLEET-DOWN_ALERT.txt`.
  - Two classes: `cleared-stale` (the app garbage-collected it) and **`never-confirmed`** (spawn with no confirm *and* no stale-clear — the app never even collected it). Counting stale-clears alone MISSES the second class; it was 3 of 54 over the 94h to 08-05.
  - Gotcha baked into the tests: a healthy dispatch very often spawns AND confirms **inside the same log second**, and log lines carry no sub-second precision — sort spawn before confirm or every fast confirm reads as a phantom (this false positive shipped and was caught on live data, not by the tests).
- Manual equivalent: grep `main.log` for `Spawning new session for scheduled task <id>` with no `Confirmed task run for: <id>` within ~10s, and/or `Cleared stale pending dispatch for: <id>`.
- Off-machine backstop **LIVE 2026-08-03**: `ZeOoba/ora-cowork-watchdog` → `.github/workflows/health-guard-beacon.yml` watches the Connector Pre-Flight beacon page `3a56ecd8-9e59-8152-83b6-c61cec736f2b` on cron `35 */4 * * *`, opens a `health-guard-alert` Issue past 26h. [PR #8](https://github.com/ZeOoba/ora-cowork-watchdog/pull/8) merged; verified by `workflow_dispatch` run [30846258326](https://github.com/ZeOoba/ora-cowork-watchdog/actions/runs/30846258326) — `Fetched 1 page(s)` (so `secrets.NOTION_TOKEN` **does** have the beacon page shared; that risk is closed), age math correct at 3.96h, verdict OK, no false-positive Issue. The refactored shared probe was regression-tested on the pre-existing `cowork-heartbeat.yml` in the same session (run 30846327172, still OK at threshold 16h) — its defaults are unchanged.
- On-machine: `ora-health-guard` Block B.3.5a now reads the beacon's prior `last_run_et` before overwriting it and escalates a >26h gap to a probe-equivalent FAIL.

Related: [[feedback_verify_registry_mutation_claims]] · [[feedback_verified_null_vs_inferred_null]] · [[reference_cc_scheduler_filepath_mechanism]]
