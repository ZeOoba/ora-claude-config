---
name: ora-automation-health-monitor
description: Weekday check that the morning automation batch fired; drafts a failure alert if any task missed.
---

Run the ora-automation-health-monitor scheduled task. Open and follow this skill file EXACTLY — it is the authoritative, self-contained spec: C:\Users\Owner\OneDrive - Oxford Capital Partners (1)\Documents\Claude\Scheduled\ora-automation-health-monitor\SKILL.md

Note (2026-06-09): the live fleet was rebuilt — verify against the CURRENT task names (ora-am-brief, ora-pm-ledger, ora-health-guard, ora-setup-audit, ora-deal-sourcing-scan, plus the tasks restored 2026-06-09), not the old pre-migration names. Use the FULL python path for any python: C:/Users/Owner/AppData/Local/Programs/Python/Python313/python.exe . Email send = C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1 (SOLE send path; Composio fallback removed 2026-06-11 — on COM failure retry once then flag, do not halt). Draft (do NOT auto-send) any failure alert per the skill.

HARD GUARDRAILS: never move money, modify financial models, or touch oxfordra.net; keep confidential deals off all external/egress surfaces (the confidentiality guard enforces this, fail-closed).