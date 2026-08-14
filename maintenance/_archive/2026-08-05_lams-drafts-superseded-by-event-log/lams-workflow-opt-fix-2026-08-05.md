## 2026-08-05 — LAMS/Cowork: closed both workflow-optimization gaps from today's cadence+tag audit

Follow-up to the same-day "LAMS/Cowork fleet cadence + model-tag policy pass" entry. Gabriel asked
to fix both workflow-optimization notes from that audit's closing summary.

**1. Watchdog-threshold/heartbeat-cadence coupling now documented.** Added a standing section to
`reference_scheduled_task_model_standard.md` ("Cadence changes on watchdog-monitored tasks — check
external thresholds first"): before changing the cron cadence of any task an EXTERNAL monitor
depends on, verify the monitor's threshold exceeds the new inter-fire gap first — a cadence cut
without a matching widen produces a guaranteed false alarm every cycle, not just "slower
detection." Cites the `ora-cowork-heartbeat` precedent from earlier today. Also cross-referenced
into `automation-health-monitor` itself (v1.18, via `update_scheduled_task` description + surgical
edit_block edits to its SKILL.md body — the file was too large to safely retype whole via a single
`prompt` replace, so targeted insertions were used instead, each verified against the exact
pre-edit text): the Step 0.55 table row for `ora-cowork-heartbeat`'s own 16h beacon-freshness check
now notes it stays accurate only because this monitor's 11:15 ET run always follows the heartbeat's
same-morning ~05:57 ET fire — a timing coincidence, not a designed invariant — and a new Operational
Notes bullet tells the next editor to check both sides before any future cadence change to either
task.

**2. Tag-date-vs-revision drift detector added.** New Step 0.07 item 6 on `automation-health-monitor`
(v1.18): for each enabled LAMS task, compares the `[MODEL:]` tag's `set` date against the latest
`vX.Y (YYYY-MM-DD)` / "retimed YYYY-MM-DD" marker documented in the task's own description. A gap
>3 days classifies `MODEL-TAG-STALE-VS-REVISION` (ℹ️, cosmetic — independent of the existing
MODEL-STALE/MODEL-UNTAGGED standard-match check; a task can read current on one and stale on the
other). Wired into Step 1's Notion report and Step 4's chat summary as a separate count so it
doesn't inflate or hide behind the existing model-currency numbers. This is exactly the class of
gap that let 8 tasks' tags go 3-22 days stale against their own last edit before a manual sweep
caught it earlier today.

**Verification:** `list_scheduled_tasks` confirms `automation-health-monitor`'s description now
reads v1.18 with both changes summarized; `edit_block` outputs confirmed each surgical insertion
landed at the intended location with surrounding text unchanged. Memory file append confirmed via
read-back (tail 46 lines match intended content).

No cadence, cron, or model-standard-line changes in this pass — both fixes are additive
documentation/detection logic only.
