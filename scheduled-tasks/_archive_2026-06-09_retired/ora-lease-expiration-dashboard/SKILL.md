---
name: ora-lease-expiration-dashboard
description: Weekly lease-expiration dashboard + 180-day renewal escalation (idempotent HubSpot tasks + email).
---

Run the ora-lease-expiration-dashboard scheduled task. Open and follow this skill file EXACTLY — it is the authoritative, self-contained spec: C:\Users\Owner\OneDrive - Oxford Capital Partners (1)\Documents\Claude\Scheduled\ora-lease-expiration-dashboard\SKILL.md

Use the FULL python path for any python (bare `python` is NOT on PATH in scheduled sessions): C:/Users/Owner/AppData/Local/Programs/Python/Python313/python.exe . Email send = C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1 PRIMARY -> Composio OUTLOOK_SEND_EMAIL fallback (Outlook only, no Gmail). Follow the skill's own recipient list, idempotency check, and draft-vs-send rules.

HARD GUARDRAILS: never move money, modify financial models, or touch oxfordra.net; keep confidential deals off all external/egress surfaces (the confidentiality guard enforces this, fail-closed).