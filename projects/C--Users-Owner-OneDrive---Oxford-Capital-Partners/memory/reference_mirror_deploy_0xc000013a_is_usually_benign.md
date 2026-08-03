---
name: reference_mirror_deploy_0xc000013a_is_usually_benign
description: "Mirror Deploy exiting 3221225786 (0xC000013A) is usually a benign reboot/Modern-Standby interruption — classify it, don't assume a broken pipeline"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 9719ed07-8b87-4594-8ed5-cda0de279ea1
  modified: 2026-08-03T16:05:19.951Z
---

`LastTaskResult = 3221225786` (`0xC000013A` = `STATUS_CONTROL_C_EXIT`) on the native **ORA Command Center - Mirror Deploy** task means the PowerShell process was **killed**, not that the deploy logic failed. On LAPTOP-CSHSCBE6 this is usually benign machine lifecycle: the laptop reboots near-daily and enters Modern Standby ~20x/day, and a run in flight during either transition dies this way. The next hourly fire re-bakes.

**Don't hand-reason it — run the classifier:**

```bash
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Users\Owner\oxford-command-center\scripts\mirror-run-classify.ps1
```

It returns a JSON `verdict`: `HEALTHY` · `BENIGN_INTERRUPTED` (record, stay silent) · `ALARM_UNEXPLAINED_KILL` · `ALARM_SILENT_INCOMPLETE` (rc=0 but the script never finished) · `ALARM_SCRIPT_FAILED` · `INDETERMINATE`. Logic lives in `scripts/lib/deploy-beacon.ps1`, tested by `scripts/deploy-beacon.smoke-test.ps1` (29 assertions, three real incidents as fixtures). Shipped 2026-08-03 in [PR #249](https://github.com/ZeOoba/oxford-command-center/pull/249).

**Three traps, each verified the hard way:**

1. **Run duration is NOT a detector.** The three real kills lasted 4s, 96s, and several hours; healthy runs take 5–19 min. No threshold separates them.
2. **The script cannot self-report this.** `deploy-mirror.ps1` alerts from a `try/catch`, which only fires on a throw. A kill skips it, so `Send-DeployFailureAlert` never runs and `data/outbox/` stays empty. Only an external check reading `LastTaskResult` sees it. Do not interpret "no alert email arrived" as "no failure."
3. **Never widen the 90s correlation window.** With Modern Standby ~20x/day, a wider window excuses every kill and silences the check permanently. Guarded by smoke-test scenarios 2g/2i/3c.

Not everything is benign: **2026-08-01 13:01:37** had zero System-log events between 12:58 and 13:05 and remains genuinely unexplained. That case is exactly what `ALARM_UNEXPLAINED_KILL` exists to catch.

Related: [[reference_command_center_mirror_deploy_gap.md]] (the 2026-07-09 stale-deploy incident, a different failure mode — that one was the pull, this one is not).
