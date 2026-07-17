---
name: ora-hubspot-sync
description: HubSpot Note→Interaction backfill + Notion mirror, 2x/day (9 AM, 3 PM weekdays)
---

ORA HubSpot ↔ Notion sync task. Runs 9 AM and 3 PM weekdays.

**Phase 1 — HubSpot Note → Interaction backfill**
1. Query HubSpot (via `mcp__a3e380ce-*__search_crm_objects` or `get_crm_objects`) for Notes created or modified since the last run of this task (use a 7-hour lookback if lastRunAt is unavailable).
2. For each Note, check whether a corresponding Engagement/Interaction record exists on the same contact/deal/company with matching timestamp ±5 min.
3. If no matching Interaction exists, create one via `manage_crm_objects` — copy the Note body, attribution owner, associated objects (contact/deal/company), and timestamp.
4. Log created Interactions with their HubSpot IDs.

**Phase 2 — Mirror to Notion**
5. For each Note/Interaction processed in Phase 1, upsert a row to the Notion "HubSpot Activity Log" database (create it if it doesn't exist — schema: Date, Contact, Deal, Company, Owner, Note Summary, HubSpot Link, Interaction ID).
6. Dedupe on HubSpot Interaction ID.

**Phase 3 — Health check & logging**
7. Count: Notes scanned, Interactions created, Notion rows upserted, errors.
8. If errors > 0 OR Notes scanned but zero Interactions created (both signal broken sync), draft an Outlook alert email to ggoldberg@oxfordra.net with the error log. (Updated 2026-04-28: was ze@oxfordra.net.)
9. Append a one-line summary to `OneDrive/ORA/Logs/hubspot-sync.log` with ISO timestamp and counts.

**Guardrails**
- Never modify existing Interaction records — only create missing ones.
- Skip any Notes flagged private or marked confidential.
- If HubSpot MCP returns auth error, send Outlook alert and abort (don't retry loop).
- Keep run under 5 minutes — if queue > 50 notes, process first 50 and flag overflow in the log.

---

## 📬 EMAIL DELIVERY TO ggoldberg@oxfordra.net (mandatory final step — added 2026-04-16)

**In addition to** every output destination above (Notion HubSpot Activity Log, OneDrive log file, any existing alert drafts to ze@), deliver the full sync report as an Outlook email to **ggoldberg@oxfordra.net**. This is additive — preserve existing destinations and alert drafts.

Follow the procedure in `C:/Users/Owner/.claude/scheduled-tasks/_shared/EMAIL_DELIVERY.md`:

1. Compose the **full sync report** as HTML (Phase 1 counts: Notes scanned / Interactions created; Phase 2 Notion upsert count; Phase 3 error count + log tail). Include the run's ISO timestamp.
2. Write it to `C:/Users/Owner/AppData/Local/Temp/ora-hubspot-sync-email-body.html`.
3. Send via Bash:
   ```bash
   powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:/Users/Owner/.claude/scheduled-tasks/_shared/send-via-outlook.ps1" -To "ggoldberg@oxfordra.net" -Subject "[ORA] HubSpot Sync - $(date +%Y-%m-%d-%H%M)" -BodyFile "C:/Users/Owner/AppData/Local/Temp/ora-hubspot-sync-email-body.html" -BodyFormat html
   ```
   Note: subject includes `%H%M` because this task runs twice a day (9am and 3pm) — timestamp keeps subjects unique.
4. On non-zero exit: retry once, then append `⚠️ EMAIL DELIVERY FAILED` to the hubspot-sync.log and continue.
5. If errors > 0 OR Notes scanned but zero Interactions created: prefix subject with `[ORA ERROR]` so the failure is visible.

**This task's values:** `TASK_ID=ora-hubspot-sync` · `DISPLAY_NAME=HubSpot Sync`