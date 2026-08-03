---
name: reference_scheduler_lastrunat_stamped_at_dispatch
description: "The Claude Desktop scheduler stamps lastRunAt at dispatch, not completion — a phantom dispatch that never confirms still advances it, so fleet-status.py reports silently-dead tasks as healthy"
metadata: 
  node_type: memory
  type: reference
  originSessionId: c9af9d3a-ea56-47fe-aff8-4f8c6e61b383
  modified: 2026-08-03T19:35:01.729Z
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

## How to detect it

Only an **output** check works. Registry state is compromised by construction.

- Grep `main.log` for `Spawning new session for scheduled task <id>` with no `Confirmed task run for: <id>` within ~10s, and/or `Cleared stale pending dispatch for: <id>`.
- Off-machine backstop **LIVE 2026-08-03**: `ZeOoba/ora-cowork-watchdog` → `.github/workflows/health-guard-beacon.yml` watches the Connector Pre-Flight beacon page `3a56ecd8-9e59-8152-83b6-c61cec736f2b` on cron `35 */4 * * *`, opens a `health-guard-alert` Issue past 26h. [PR #8](https://github.com/ZeOoba/ora-cowork-watchdog/pull/8) merged; verified by `workflow_dispatch` run [30846258326](https://github.com/ZeOoba/ora-cowork-watchdog/actions/runs/30846258326) — `Fetched 1 page(s)` (so `secrets.NOTION_TOKEN` **does** have the beacon page shared; that risk is closed), age math correct at 3.96h, verdict OK, no false-positive Issue. The refactored shared probe was regression-tested on the pre-existing `cowork-heartbeat.yml` in the same session (run 30846327172, still OK at threshold 16h) — its defaults are unchanged.
- On-machine: `ora-health-guard` Block B.3.5a now reads the beacon's prior `last_run_et` before overwriting it and escalates a >26h gap to a probe-equivalent FAIL.

Related: [[feedback_verify_registry_mutation_claims]] · [[feedback_verified_null_vs_inferred_null]] · [[reference_cc_scheduler_filepath_mechanism]]
