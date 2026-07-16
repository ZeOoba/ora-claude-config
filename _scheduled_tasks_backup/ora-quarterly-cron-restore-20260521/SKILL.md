---
name: ora-quarterly-cron-restore-20260521
description: [ONE-TIME 2026-05-21 4:15 PM] Restore quarterly cron expressions for 3 tasks after manual one-time fires today. Self-archives.
---

## One-Time Cron Restoration — 2026-05-21

Three quarterly scheduled tasks were manually triggered today (2026-05-21) via one-time fireAt to catch up on missed Q1/Q2 runs. The fireAt mechanism clears the cron schedule. This task restores their recurring quarterly schedules.

### Step 1: Restore the 3 cron expressions

Use the `mcp__scheduled-tasks__update_scheduled_task` tool (load via ToolSearch with query "select:mcp__scheduled-tasks__update_scheduled_task") to update each task:

1. **ora-insurance-renewal-tracker**
   - cronExpression: `30 9 1 1,4,7,10 *`

2. **ora-tax-appeal-calendar**
   - cronExpression: `0 10 1 1,4,7,10 *`

3. **ora-cre-data-mcp-recheck**
   - cronExpression: `30 10 1 1,4,7,10 *`

### Step 2: Verify

After updating, call `mcp__scheduled-tasks__list_scheduled_tasks` and confirm:
- All 3 tasks show `cronExpression` (not `fireAt`)
- All 3 show `nextRunAt` of approximately 2026-07-01T13:xx UTC
- All 3 show `enabled: true`

### Step 3: Log completion

Use the Notion update-page tool (load via ToolSearch: "select:mcp__c5f4869f-7d3a-4472-a66a-8e61315feb51__notion-update-page") to append a brief note to Notion page ID `3676ecd89e59811cacbcc52eb74a0de5`:

Append: "**Cron Restore Completed [timestamp]:** ora-insurance-renewal-tracker, ora-tax-appeal-calendar, and ora-cre-data-mcp-recheck quarterly schedules restored. Next auto-fire: 2026-07-01."