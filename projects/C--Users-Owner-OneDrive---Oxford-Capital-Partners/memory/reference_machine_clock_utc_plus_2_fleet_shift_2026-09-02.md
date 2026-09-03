---
name: reference-machine-clock-utc-plus-2-fleet-shift-2026-09-02
description: "Since ~2026-09-02 the ORA laptop's Windows clock is on Romance Standard Time (UTC+2), so every scheduled-task cron slot fires 6h earlier in ET terms — a host-state fact, not a task fault; check Get-TimeZone before diagnosing 'early' or 'odd' fire times."
metadata: 
  node_type: memory
  type: reference
  originSessionId: 94dccd75-e1d4-4515-be4a-ef287399a67f
  modified: 2026-09-02T12:14:53.488Z
---

**Observed 2026-09-02 (fix pass after the 09-02a schematic refresh):** `Get-TimeZone` = `Romance Standard Time` (UTC+01:00 base, +02:00 in DST). `C:\Users\Owner\ora-pm-cron\cron.log` stamps read `-04:00` through 2026-08-28 and `+02:00` from 2026-09-02, so the change landed inside the 08-29 → 09-01 host outage window. Registry `lastRunAt` values written that day (e.g. `ora-pm-monthly-billing` 10:43) are UTC and correspond to 12:43 local / 06:43 ET.

**Why it matters:** `fleet-status.py`'s `most_recent_expected_fire_utc()` and the Desktop scheduler both evaluate cron in LOCAL time by doctrine. While the clock is on UTC+2, `ora-am-brief`'s `0 6 * * *` fires at 00:00 ET, `ora-pm-monthly-billing`'s `10 11 1 * *` at 05:10 ET, and so on across both fleets — 6h early relative to the ET slots every SKILL.md documents. Nothing is broken; the times are simply shifted.

**How to apply:**
- Before calling a fire time "early", "late", or "odd", run `Get-TimeZone` and compare against the `-04:00`/`-05:00` the task specs assume.
- Do NOT retime any task to compensate — the shift reverses itself when the clock returns to Eastern, and the registries would then be 6h off the other way. Flag, don't fix.
- The off-host GitHub Actions billing backup (ora-pm PR #24, `40 16 1 * *` UTC) is deliberately clock-independent; it is the one trigger unaffected by this.

Related: [[reference_lastruntime_restamped_on_modern_standby_resume]] (the other reason wall-clock task timing misleads on this laptop), [[project_automation_audit_rev21_2026-09-02]].
