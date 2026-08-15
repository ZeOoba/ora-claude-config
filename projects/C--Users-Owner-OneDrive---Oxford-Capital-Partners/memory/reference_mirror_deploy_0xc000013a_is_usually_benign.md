---
name: reference_mirror_deploy_0xc000013a_is_usually_benign
description: "Mirror Deploy exiting 3221225786 (0xC000013A) is usually a benign reboot/Modern-Standby interruption — classify it, don't assume a broken pipeline"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 9719ed07-8b87-4594-8ed5-cda0de279ea1
  modified: 2026-08-04T16:07:45.869Z
---

`LastTaskResult = 3221225786` (`0xC000013A` = `STATUS_CONTROL_C_EXIT`) on the native **ORA Command Center - Mirror Deploy** task means the PowerShell process was **killed**, not that the deploy logic failed. On LAPTOP-CSHSCBE6 this is usually benign machine lifecycle: the laptop reboots near-daily and enters Modern Standby ~20x/day, and a run in flight during either transition dies this way. The next hourly fire re-bakes.

**Don't hand-reason it — run the classifier:**

```bash
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Users\Owner\oxford-command-center\scripts\mirror-run-classify.ps1
```

It returns a JSON `verdict`: `HEALTHY` · `BENIGN_INTERRUPTED` (record, stay silent) · `BENIGN_KILLED_AFTER_COMPLETION` (killed after this run's own success beacon — work published, mirror NOT stale, stay silent) · `ALARM_UNEXPLAINED_KILL` · `ALARM_SILENT_INCOMPLETE` (rc=0 but the script never finished) · `ALARM_SCRIPT_FAILED` · `INDETERMINATE`. Logic lives in `scripts/lib/deploy-beacon.ps1`, tested by `scripts/deploy-beacon.smoke-test.ps1` (64 assertions, four real incidents as fixtures). Shipped 2026-08-03 in [PR #249](https://github.com/ZeOoba/oxford-command-center/pull/249); freshness fix 2026-08-04 on branch `fix/beacon-stale-beacon-on-kill`.

**Three traps, each verified the hard way:**

1. **Run duration is NOT a detector.** The three real kills lasted 4s, 96s, and several hours; healthy runs take 5–19 min. No threshold separates them.
2. **The script cannot self-report this.** `deploy-mirror.ps1` alerts from a `try/catch`, which only fires on a throw. A kill skips it, so `Send-DeployFailureAlert` never runs and `data/outbox/` stays empty. Only an external check reading `LastTaskResult` sees it. Do not interpret "no alert email arrived" as "no failure."
3. **Never widen the 90s correlation window.** With Modern Standby ~20x/day, a wider window excuses every kill and silences the check permanently. Guarded by smoke-test scenarios 2g/2i/3c.

Not everything is benign. **Three `ALARM_UNEXPLAINED_KILL` cases so far, all within four days:**

1. **2026-08-01 13:01:37** — zero System-log events between 12:58 and 13:05.
2. **2026-08-03 20:05:26** — classifier returned `ALARM_UNEXPLAINED_KILL`, `correlatingEvent: null`, no power/session event in the 90s window. Machine was awake and in active interactive use throughout, so Modern Standby does not cover it. Found during the `ora-lease-snapshot-refresh` run, not by the drift-check task.
3. **2026-08-04 11:00:01** — run started 11:00:01, killed at 11:00:29 (28s in). Nearest power/session event was 09:51:33, **4,136s away**; the empty in-window result was re-run against an 08:00–13:00 window to prove it was a real null and not a failed query. **This one was initially MISREPORTED as `ALARM_SCRIPT_FAILED`** — see the defect note below.

**The 08-04 case was masked by a classifier defect, now fixed.** The run was killed before it could write a beacon, so the beacon on disk was still the 10:00 run's (completed/success). `Get-MirrorRunVerdict`'s rc≠0 branch tested only beacon *status*, never *freshness* — which the rc=0 branch had always tested — so a stale completed beacon short-circuited the kill to `ALARM_SCRIPT_FAILED` with the text "Script threw and reached its exit path (outcome=success)". That is self-contradictory, and it told the reader to expect a `Send-DeployFailureAlert` email that could not exist; under drift-check SKILL step 5 a missing self-alert reads as a broken send path and "the bigger finding", so the bad verdict sends you chasing a phantom send-path outage. **A wrong alarm is not a safe failure mode** — it consumed attention on an invented incident while the real third unexplained kill went unrecorded. Fixed 2026-08-04: rc≠0 now requires a beacon belonging to this run, and a new silent verdict `BENIGN_KILLED_AFTER_COMPLETION` covers a kill *after* this run's own success beacon. The 90s window was NOT touched.

**The 08-03 case pinned down what a kill actually costs, which the 08-01 entry never established.** The run baked and built fine — `public/snapshot.json` rewritten 20:01 with correct data, `dist/` at 20:04 — then died before `wrangler pages deploy` published. `wrangler pages deployment list` showed the newest production deployment still at the *previous* hour's commit, so **the kill silently discards the whole cycle: local `dist/` looks freshly built while the live site keeps serving the prior bake.** Do not infer publication from a fresh `dist/` or a fresh `public/snapshot.json` — neither is evidence anything shipped. `deployment list` is the only check that answers it, and it is read-only and safe to run. Beacon `status: "running"` + `outcome: null` is the matching local tell.

Consequence that day: a ratified workbook correction (Northwood loan external→internal, $2.8M bucket move) sat corrected locally but unpublished on brain.oxfordra.net for an extra hour. See [[reference_command_center_mirror_deploy_gap]].

**The third landed on 2026-08-04, so the "usually benign" framing in this file's title and description is now DUE for review — Gabriel's call, not a silent rewrite.** Three unexplained kills in four days is no longer a watch-item cluster. Two cautions before overturning the base rate: (a) this machine genuinely does reboot near-daily, so benign kills still outnumber these, and (b) the 08-04 case only surfaced because the classifier defect was found — meaning the true unexplained count for earlier periods may be *understated*, not overstated, and any earlier run classified `ALARM_SCRIPT_FAILED` on a kill code deserves re-reading. What is NOT in question: do not respond by widening the 90s correlation window.

Related: [[reference_command_center_mirror_deploy_gap.md]] (the 2026-07-09 stale-deploy incident, a different failure mode — that one was the pull, this one is not).
