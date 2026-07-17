---
name: ora-email-queue
description: Weekday 9am + 2pm email response queue — scan Outlook, enrich from Notion/HubSpot, draft replies, post to Email Response Queue DB. Runs twice daily via dual cron schedule.
---

Read the full task prompt from: C:\Users\Owner\OneDrive - Oxford Capital Partners (1)\Cowork OS\Claude\Scheduled\ora-email-queue\SKILL.md

Execute every instruction in that file exactly as written.

**Run-window detection:** Use the current local time to decide the afterDateTime:
- If current hour < 12 → morning run, afterDateTime = 8 hours ago (captures overnight)
- Else → afternoon run, afterDateTime = 5 hours ago (captures morning activity)

This replaces the separated `ora-email-queue-am` and `ora-email-queue-pm` tasks. One SKILL.md, two cron triggers (09:01 and 14:01 weekdays).
