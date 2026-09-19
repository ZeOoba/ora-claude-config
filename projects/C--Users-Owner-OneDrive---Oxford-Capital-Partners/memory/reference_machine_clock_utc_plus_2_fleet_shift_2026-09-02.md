---
name: reference-machine-clock-utc-plus-2-fleet-shift-2026-09-02
description: "RESOLVED 2026-09-05 — the ORA laptop's clock is back on Eastern. For the 09-02 → 09-05 window it ran on Romance Standard Time (UTC+2), so cron slots in that window fired 6h earlier in ET terms — a host-state fact, not a task fault. The standing rule survives the resolution: check Get-TimeZone before diagnosing 'early'/'odd' fire times, and never retime a task to compensate."
metadata: 
  node_type: memory
  type: reference
  originSessionId: 94dccd75-e1d4-4515-be4a-ef287399a67f
  modified: 2026-09-05T19:56:59.249Z
---

**✅ RESOLVED 2026-09-05 15:09 EDT** (verified by `ora-health-guard` follow-up): `Get-TimeZone` now returns `Eastern Standard Time`, `BaseUtcOffset -05:00`, live offset `-04:00` (EDT). The skew window was therefore **2026-09-02 → 2026-09-05**; treat any host-local timestamp inside it as UTC+2, and anything after it as ET. `tzautoupdate` is Stopped/Manual (`Start=3`), so the clock did not drift on its own and did not correct on its own — both the change and the correction were manual, consistent with travel out of and back into ET. **The rule below still stands and was vindicated** — the shift did reverse itself exactly as predicted, so the standing instruction to flag rather than retime was the correct call; had any task been re-cronned to compensate, the fleet would now be 6h wrong in the other direction.

**Observed 2026-09-02 (fix pass after the 09-02a schematic refresh):** `Get-TimeZone` = `Romance Standard Time` (UTC+01:00 base, +02:00 in DST). `C:\Users\Owner\ora-pm-cron\cron.log` stamps read `-04:00` through 2026-08-28 and `+02:00` from 2026-09-02, so the change landed inside the 08-29 → 09-01 host outage window. Registry `lastRunAt` values written that day (e.g. `ora-pm-monthly-billing` 10:43) are UTC and correspond to 12:43 local / 06:43 ET.

**Why it matters:** `fleet-status.py`'s `most_recent_expected_fire_utc()` and the Desktop scheduler both evaluate cron in LOCAL time by doctrine. While the clock is on UTC+2, `ora-am-brief`'s `0 6 * * *` fires at 00:00 ET, `ora-pm-monthly-billing`'s `10 11 1 * *` at 05:10 ET, and so on across both fleets — 6h early relative to the ET slots every SKILL.md documents. Nothing is broken; the times are simply shifted.

**How to apply:**
- Before calling a fire time "early", "late", or "odd", run `Get-TimeZone` and compare against the `-04:00`/`-05:00` the task specs assume.
- Do NOT retime any task to compensate — the shift reverses itself when the clock returns to Eastern, and the registries would then be 6h off the other way. Flag, don't fix.
- The off-host GitHub Actions billing backup (ora-pm PR #24, `40 17 1 * *` UTC — retimed from 16:40 at PR review, head d686e4d 2026-09-03) is deliberately clock-independent; it is the one trigger unaffected by this.

**Aftermath — the flip BACK re-armed already-executed slots (verified 2026-09-05, CC registry).** 23 CC tasks stamped `lastRunAt` between 17:10Z and 20:12Z on Saturday 09-05, including crons that cannot fire on a Saturday (`ora-cc-snapshot-refresh` Mon-only, `ora-broker-touch-cadence` 2nd-of-month, `ora-entry-market-scan` Tue 1-7) and `ora-tenant-hubspot-reconciliation` (`15 8 1 * *`), which had ALREADY fired its 09-01 slot as catch-up on 09-02 (send-log 09-02T12:31+02:00) and now shows `lastScheduledFor: 2026-09-01T12:15:00Z` — the EDT reading of the same slot the UTC+2 clock had evaluated as 06:15Z. Mechanism [SPECULATIVE on internals, solid on timeline]: the scheduler re-evaluates local cron under the new offset, the stored slot no longer matches, and the "missed" slot fires again — the same class as [[reference_cron_retime_rearms_executed_slot]], triggered by a clock change instead of a cron edit. `block-sentinel.py` keys on ET date, so a per-date guard would NOT have stopped a 09-02 → 09-05 duplicate; a monthly/weekly task needs a per-period key. Expect a duplicate fire from every periodic task after any timezone change; do not read it as a task-specific bug.

Related: [[reference_lastruntime_restamped_on_modern_standby_resume]] (the other reason wall-clock task timing misleads on this laptop), [[project_automation_audit_rev21_2026-09-02]].
