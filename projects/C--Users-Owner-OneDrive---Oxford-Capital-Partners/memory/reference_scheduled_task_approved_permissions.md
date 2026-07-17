---
name: reference_scheduled_task_approved_permissions
description: A scheduled task registered without an approvedPermissions grant for the tools it calls runs but its tool calls silently fail unattended; lastRunAt still advances (dispatch ≠ completion)
metadata: 
  node_type: memory
  type: reference
  originSessionId: 6e7d1117-e68d-4f7b-a681-71073b399ac8
---

Each scheduled-task registry entry (LAMS/Cowork AND CC/MCP) carries an `approvedPermissions` array — `[{toolName: "..."}]` — listing the tools that task may call when running unattended. **If the grant is missing for a tool the task calls, the unattended run cannot complete that tool call: the write silently fails, but the registry `lastRunAt` still advances because the session was DISPATCHED (dispatch ≠ successful completion).** The task looks like it "ran" in `fleet-status.py`/`list_scheduled_tasks` while producing no output.

**Confirmed 2026-07-16/17 via `ora-cowork-heartbeat`:** its Notion beacon page ([[00_system_of_record]] dead-man switch, page `35c6ecd8-9e59-81d5-8d2c-d08002458b78`) went stale ~42h while the registry showed the task firing (lastRunAt advancing, 23 skips). Prior-session systematic-debugging reproduced the exact `notion-update-page` write on a throwaway page (ruling out a connector fault), then narrowed to a missing tool-approval. Verified directly: the `ora-cowork-heartbeat` registry entry had **NO `approvedPermissions`**, unlike every sibling that writes Notion successfully (`ora-stale-pipeline-nudge` → `[notion-create-pages]`; `automation-health-monitor`; `ora-skills-reimport-watch` → `[start_process]`).

**Diagnostic pattern:** a scheduled task with `lastRunAt` advancing but no downstream output → suspect a missing `approvedPermissions` grant first. Compare its `approvedPermissions` against a sibling task that calls the same tool and works. (Registry entry keys: `id, enabled, cronExpression, filePath, lastRunAt, approvedPermissions, notifySessionId, userSelectedFiles, userSelectedFolders`.)

**Fix is manual, UI-only:** re-approve/grant the tool for the task in Cowork's Scheduled Tasks UI. You canNOT splice the permission into the registry JSON (violates the register-only-via-`create_scheduled_task` doctrine, see [[reference_cc_scheduler_filepath_mechanism]]), and `update_scheduled_task` does not set it — the grant comes through the UI approval flow. Re-registering alone doesn't add it. Interim mitigation for a stale heartbeat: manually write the beacon timestamp from any Notion-capable surface to reset the external watchdog's 16h clock, but it re-alarms until the grant lands. Related: [[reference_fleet_status_dual_read]], [[feedback_verify_registry_mutation_claims]].
