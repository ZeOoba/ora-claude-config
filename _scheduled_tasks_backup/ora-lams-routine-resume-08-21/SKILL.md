---
name: ora-lams-routine-resume-08-21
description: One-time LAMS/Cowork fleet resume — Friday 2026-08-21 5:00 PM ET. Re-enables 25 of the 26 recurring Cowork tasks disabled by the 2026-08-17 bounded pause ("pause all routines until Friday 5pm"). Registered 2026-08-17 to close a verified gap: the CC/MCP half of that pause got a resume (ora-routine-pause-resume-08-21) but the LAMS half landed with none, leaving 27 tasks — including ora-cowork-heartbeat and automation-health-monitor, the two detectors that would otherwise report the outage — dark with nothing scheduled to wake them. Excludes ora-cam-data-backfill (spent one-time, fired 2026-08-15) AND ora-passed-deal-tracker (2026-08-21 ora-setup-audit finding: this LAMS copy was superseded by a deliberate 2026-08-15 migration to CC/MCP — LAMS has no Outlook COM access and this exact copy already failed to send once; it was left disabled rather than retired and would otherwise have been silently resurrected as a duplicate alongside the working CC/MCP copy). Does NOT re-stamp [MODEL:] dates per register-scheduled-task v2.12. [MODEL: claude-sonnet-5 | set 2026-08-17]
---

LAMS/COWORK FLEET RESUME — one-time, closes the 2026-08-17 bounded pause.

CONTEXT
On 2026-08-17 a "pause all routines until Friday 5pm" instruction was executed across both scheduled-task fleets. The CC/MCP half registered a resume (`ora-routine-pause-resume-08-21`). The LAMS/Cowork half did NOT — 27 tasks were disabled with nothing scheduled to re-enable them, including `ora-cowork-heartbeat` (the dead-man chain feeding Notion page 35c6ecd8… and the external GitHub watchdog) and `automation-health-monitor` itself. Because both detectors were inside the pause, neither could report its own outage. This task is that missing resume.

ACTION — re-enable each of the following 25 tasks via `update_scheduled_task` with `enabled: true`. Do them one at a time and record the result of each.

  ora-cowork-heartbeat
  automation-health-monitor
  ora-health-guard-fail-aging-nudge
  ora-monday-sync
  ora-lease-expiration-brief
  ora-tenant-contact-gap-sweep
  ora-owner-outreach-queue-refresh
  ora-insurance-renewal-monitor
  ora-skill-store-drift-check
  ora-ic-memo-pipeline-reconciliation
  ora-underwrite-doctrine-staleness-check
  ora-om-intake-ocr
  ora-stale-pipeline-nudge
  ora-critical-deadlines-scan
  ora-dd-critical-tracker
  ora-friday-closeout
  ora-session-sweep
  ora-consolidate-memory-monthly
  ora-skill-text-audit
  ora-capex-idea-stage-nudge
  ora-ar-export-freshness-nudge
  ora-replacement-cost-refresh
  ora-bearmode-refresh
  ora-gis-endpoint-liveping
  ora-exit-cap-spotcheck

DO NOT RE-ENABLE
  ora-cam-data-backfill — a one-time task that already fired 2026-08-15. It is spent, not paused. Re-enabling it would re-run a completed backfill. Leave it disabled; if anything, it is a candidate for retirement under the archive-first-delete-second ordering, which is out of scope here.

  ora-passed-deal-tracker — this LAMS copy is superseded. Gabriel ratified a deliberate migration to the CC/MCP fleet on 2026-08-15 (LAMS has no path to Outlook COM; this exact copy already failed live with "SEND FAILURE — no COM access"). It was left disabled rather than retired, which is why it was originally on this list — caught and removed by the 2026-08-21 ora-setup-audit before this task's first fire. The CC/MCP copy (ora-routine-pause-resume-08-21's list) is the one that resumes. This LAMS copy remains a retirement candidate under the archive-first ordering, out of scope here.

DO NOT RE-STAMP MODEL TAGS
Per `register-scheduled-task` v2.12: an automated bulk resume must NOT refresh `[MODEL: … | set|checked YYYY-MM-DD]` dates. The re-tag-on-enable rule binds a hand re-enable of a single task, not this. Leave every description exactly as found.

FLEET SAFETY
`update_scheduled_task` resolves to the fleet LOCAL to the session running it, and carries no fleet parameter. Before the first write, call `list_scheduled_tasks` and confirm via each entry's `path` field that these tasks resolve to the LAMS store (`...\Documents\Claude\Scheduled\{id}\`) and not the CC/MCP store (`~\.claude\scheduled-tasks\{id}\`). If the paths show CC/MCP, STOP — you are on the wrong surface and would be re-enabling the wrong copies. Report and halt rather than improvising.

VERIFY BEFORE REPORTING DONE
Call `list_scheduled_tasks` again and confirm all 26 show `enabled: true` with a sane `nextRunAt`. For any task whose cadence slot has already passed this cycle, note when it will actually next fire — a resumed weekly task may not run for up to 7 days, and that is expected, not a failure.

REPORT
Post a completion entry to the Notion Operations Hub (page 32b6ecd8-9e59-81ed-b571-dfc871ab9f25) titled "LAMS Fleet Resume — 2026-08-21" listing each task id, its enabled state, and its next fire time. Then attempt an email via Outlook COM:
  powershell -File "C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1"
  TO: ggoldberg@oxfordra.net ONLY. No cc.
  Subject: "LAMS fleet resumed — 26 tasks re-enabled — 2026-08-21"
On non-zero exit: retry once, then note the failure loudly in the Notion entry and continue. Do NOT halt — the LAMS fleet has historically had unreliable COM reach, so Notion is the delivery of record and an email failure is not a task failure.

IF ANY TASK FAILS TO RE-ENABLE
Do not silently skip it. List it explicitly in both the Notion entry and the email subject line with an [ACTION REQUIRED] prefix. A partial resume reported as complete is the exact failure shape that created this gap in the first place.