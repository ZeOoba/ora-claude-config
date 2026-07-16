---
name: routines-default-model
description: Standing default — all routines (scheduled cloud agents / Cron-based tasks) default to claude-sonnet-5 unless Gabriel specifies otherwise
metadata: 
  node_type: memory
  type: feedback
  originSessionId: a694579e-b67a-4036-a670-82fc537dc344
---

All routines — scheduled cloud agents created via the `schedule` skill / `CronCreate` mechanism — default to **claude-sonnet-5** as the model.

**Why:** Gabriel's standing instruction (2026-07-13). Generalizes the same standard already ratified for the LAMS/Cowork + CC/MCP scheduled-task fleet ([[reference_scheduled_task_model_standard]], set 2026-07-08) to the separate native routines/Cron mechanism (`CronCreate`/`CronList`/`CronDelete`, distinct from the `mcp__scheduled-tasks__*` dual-fleet system).

**How to apply:** When creating or updating a routine via the `schedule` skill or `CronCreate`, set the model to claude-sonnet-5 by default. Only deviate if Gabriel explicitly requests a different tier for that specific routine (e.g., the website-work opus override, [[feedback_website_model_tier]], is a separate, narrower carve-out and does not apply here unless the routine itself is website work).
