---
name: ora-lams-fleet-resume-20260911
description: One-time resume for the 2026-09-07 bounded pause of the LAMS/Cowork fleet — re-enables the 26 tasks paused pending Gabriel's 2026-09-11 16:01 ET instruction. Carve-outs (ora-cowork-heartbeat, automation-health-monitor) were never paused and are not touched. Does not re-stamp [MODEL:] tags. [MODEL: claude-sonnet-5 | set 2026-09-07]
---

This is the resume half of a bounded pause registered 2026-09-07 (register-scheduled-task v2.19/v2.20 bounded-pause procedure). It fires once, then disables itself.

CONTEXT: On 2026-09-07 Gabriel instructed pausing the LAMS/Cowork fleet until Friday 2026-09-11, 4:01 PM ET. 26 tasks were disabled via update_scheduled_task(enabled:false). Two tasks were deliberately carved out and left enabled the whole time: ora-cowork-heartbeat (dead-man chain) and automation-health-monitor (fleet health detector) — do NOT touch either of these; they were never paused.

TASK: Re-enable (update_scheduled_task, enabled:true) exactly these 26 task ids, and no others:
1. ora-consolidate-memory-monthly
2. ora-skill-store-drift-check
3. ora-skill-text-audit
4. ora-om-intake-ocr
5. ora-owner-outreach-queue-refresh
6. ora-replacement-cost-refresh
7. ora-bearmode-refresh
8. ora-friday-closeout
9. ora-lease-expiration-brief
10. ora-monday-sync
11. ora-stale-pipeline-nudge
12. ora-ar-export-freshness-nudge
13. ora-session-sweep
14. ora-gis-endpoint-liveping
15. ora-ic-memo-pipeline-reconciliation
16. ora-underwrite-doctrine-staleness-check
17. ora-exit-cap-spotcheck
18. ora-critical-deadlines-scan
19. ora-capex-idea-stage-nudge
20. ora-tenant-contact-gap-sweep
21. ora-health-guard-fail-aging-nudge
22. ora-dd-critical-tracker
23. ora-insurance-renewal-monitor
24. ora-counsel-review-standard-positions-2027
25. ora-loan-terms-reconciliation
26. ora-hubspot-notion-contact-sync

PRE-FLIGHT (before any write): read C:\Users\Owner\.claude\maintenance\_state\retire-pending.json. If any id above now appears in its "pending" array with fleet "lams", SKIP that id (do not re-enable it) and note the skip in the completion summary — a retirement may have been ratified during the pause window and must not be silently reversed. As of registration time (2026-09-07) that file's pending array was empty, so absent a change nothing should be skipped.

PROGRESS MARKERS (26 sequential side-effect steps — mandatory per register-scheduled-task step 4d): after each update_scheduled_task call, run:
python C:\Users\Owner\.claude\maintenance\task-progress-marker.py write --task-id ora-lams-fleet-resume-20260911 --step N --of 26 --note "<task id just re-enabled>"
where N is the 1-based index in the list above.

DO NOT re-stamp any [MODEL:] tag or "checked"/"set" date on the tasks you re-enable — a resume is not itself a model-currency observation (register-scheduled-task bounded-pause section: "A resume does NOT re-stamp [MODEL:] dates"). Leave descriptions exactly as they are; only flip enabled.

VERIFY: call list_scheduled_tasks after all 26 (or 26-minus-skips) updates. Confirm every targeted id shows enabled:true (except any skipped per the retire-pending check above), and confirm ora-cowork-heartbeat and automation-health-monitor still show enabled:true and were never touched.

REPORT: post a completion summary to the Notion Operations Hub (32b6ecd8) and send a COM email to ggoldberg@oxfordra.net ONLY (send-via-outlook.ps1; on non-zero exit, retry once, then flag loudly and do not halt) stating: count re-enabled, any ids skipped (with reason), and confirmation that both carve-outs remained enabled throughout. This task then auto-disables (one-time).