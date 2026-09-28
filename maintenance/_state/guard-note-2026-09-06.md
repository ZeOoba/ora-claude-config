# ora-task-integrity-guard — 2026-09-06 07:05 ET run — deliberate deviation note

**STEP 1.5 script 1 (`registry-membership-probe.py`) was deliberately NOT run this cycle.**

Reason: `memory/project_automation_audit_rev22_2026-09-05.md` (§1) documents that the frozen
`_state/registry-membership.json` / `.log` snapshot (ts `2026-09-03T10:53:28`, cc=36 ids
including `ora-pm-monthly-billing` and `ora-pm-daily-crons`) is the **only surviving proof**
those two money-moving tasks were ever registered (R22-1, pending Gabriel's call — no ruling
found in event_log.md as of this run). Running the probe overwrites that snapshot. The memory
note explicitly says do this deliberately, not casually inside an unattended run, so this guard
skipped it rather than destroy the evidence on Gabriel's behalf.

This IS a documented STEP-3 alarm condition under this guard's own doctrine ("any STEP 1.5
sub-step was SKIPPED rather than run-and-exited"), and is reported as such in today's alarm
email — this note exists so the skip is attributable to a reasoned decision, not a silent
failure, consistent with the same evidentiary-preservation principle.

All other STEP 1.5/2.5/2.75/2.8/2.9 sub-steps ran normally today. See today's alarm email for
full findings, including new phantom-dispatch evidence bearing on R22-1's open cause
investigation.

-- ora-task-integrity-guard, automated run
