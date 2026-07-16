---
name: hard-delete-zapier-trial-reminder
description: [ONE-TIME 2026-05-31] Hard-delete zapier-trial-reminder. 30-day retention satisfied (fired 2026-05-01). Self-archives.
---

Delete the disabled scheduled task `zapier-trial-reminder` from the registry. Verify it is disabled and lastRunAt > 30 days. Use any available delete/remove API. Confirm via re-list. Self-disable this hard-delete task after success.