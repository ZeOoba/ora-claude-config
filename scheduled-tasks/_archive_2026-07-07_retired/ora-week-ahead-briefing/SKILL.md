---
name: ora-week-ahead-briefing
description: Friday week-ahead briefing of deadlines and priorities.
---

Run the ora-week-ahead-briefing scheduled task. Open and follow this skill file EXACTLY — it is the authoritative, self-contained spec: C:\Users\Owner\OneDrive - Oxford Capital Partners\Documents\Claude\Scheduled\ora-week-ahead-briefing\SKILL.md

(Corrected 2026-07-07: this pointer previously read the "(1)"-suffixed OneDrive path, which has no `Documents\Claude\Scheduled` folder at all — verified the real, current spec lives at the no-suffix path above.)

Use the FULL python path for any python: C:/Users/Owner/AppData/Local/Programs/Python/Python313/python.exe . Email send = C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1 (SOLE send path; Composio fallback removed 2026-06-11 — on COM failure retry once then flag, do not halt). Follow the skill's recipient list and draft-vs-send rules.

HARD GUARDRAILS: never move money, modify financial models, or touch oxfordra.net; keep confidential deals off all external/egress surfaces (the confidentiality guard enforces this, fail-closed).