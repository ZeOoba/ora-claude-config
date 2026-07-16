# Feedback — Outlook Only, No Gmail

**Updated:** 2026-04-16

## Standing preference

Gabriel uses **Outlook (Microsoft 365) only** for email. Do NOT use Gmail for:
- Drafting scheduled-task reports
- Sending notifications
- Any communication automation
- Any "email delivery" wiring

## Implementation note

When scheduled tasks or skills need to send email on Gabriel's behalf, use **Outlook COM automation via PowerShell** (leverages the authenticated desktop Outlook profile — no OAuth, no app passwords, no token management).

Standard helper path: `C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1`

## Zapier status

Zapier account is **out of space** as of 2026-04-16 — do NOT recommend or design around Zapier Zaps for new automations. Use direct Outlook COM, Power Automate (if premium available), or local PowerShell scripts instead.

## History

- 2026-04-16: Created after Gabriel clarified Outlook-only preference while wiring email delivery into 17 scheduled tasks + 3 remote triggers.
