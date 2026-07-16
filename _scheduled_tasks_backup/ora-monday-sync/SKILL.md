---
name: ora-monday-sync
description: Monday week-ahead operations sync — Mondays 7:30 AM. [MODEL: claude-sonnet-5 | set 2026-07-08]
---

You are running the ORA Monday Sync for Gabriel Goldberg, Oxford Realty Advisors. Purpose: one week-ahead operational picture before the week starts.

1. Outlook calendar (ggoldberg@oxfordra.net): list this week's meetings/deadlines.
2. Notion Acquisition Pipeline (bcfe4a03): active deals by stage, items with dates falling this week (DD deadlines, LOI/PSA dates).
3. Notion Operations Hub (32b6ecd8): open/flagged items from last week's completion rows, including any SEND FAILED flags — surface those first.
4. If today is the first Monday after the 1st of the month: check the Monthly Close database for the current month; if no rows exist, flag MONTHLY CLOSE NOT STARTED at the top.
5. Produce a compact sync: top 3 priorities, calendar, deal deadlines, carried-over items, automation health notes. Institutional register.
6. Post to Notion Operations Hub titled "Monday Sync — [date]".
7. Send via the SOLE send path — Outlook COM: powershell -ExecutionPolicy Bypass -File "C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1" -To "ggoldberg@oxfordra.net" -Subject "ORA Monday Sync — [date]" -Body [sync] -Html — via the host-exec bridge (Desktop Commander MCP) if available. Routing canon: ggoldberg@oxfordra.net ONLY, no cc. On failure or missing bridge: retry once, flag SEND FAILED loudly in the Notion row, continue — do NOT halt. Never send outside oxfordra.net.