# Handoff — retire the LAMS twins of `ora-owner-outreach-queue-refresh` and `ora-cowork-heartbeat`

**Supersedes:** `2026-10-30_LAMS-outreach-twin-retire_brief.md`. Use this one brief for both twins.
**Execute from:** a **native on-device Cowork session**: the Cowork desktop app itself, or Cowork's "Run this task → On your computer". **NOT Claude Code.** In Claude Code, `delete_scheduled_task` resolves to the CC fleet, and these ids now exist there as the canonical copies, so running this brief from Claude Code would delete the live outreach task and the dead-man heartbeat. Also NOT a cloud-sandbox Cowork session, which carries none of the scheduled-task MCP tools.
**Ratified:** Gabriel, in-turn, 2026-10-30. The outreach twin was approved under "Start Phase 0", the heartbeat under "Migrate to CC fleet". Plan: Notion `4096ecd8-9e59-8150-8417-c1d9a30130e4` §10.
**Skill:** `register-scheduled-task`, RETIRE procedure, LAMS ordering: archive the folder first, drop the registry row second.

## Step 0 — surface assertion (Rule 3), before anything else
Search this session's tool registry for `list_scheduled_tasks`. If it is absent, STOP and do none of the steps below. If it is present, call it and STOP unless at least one returned row's `path` is under `…\Documents\Claude\Scheduled\`. That proves this session's fleet is LAMS. Also STOP if ANY returned row's `path` is under `.claude\scheduled-tasks\`. Those are CC rows, and a LAMS session never sees them, so this check costs nothing. If they appear, this session's deletes may resolve to the CC fleet. A session whose rows are all under `.claude\scheduled-tasks\` is Claude Code (the CC fleet), and must do nothing. State the verdict either way.

## Expected before (both ids)
| id | LAMS row | CC row (canonical — DO NOT TOUCH) |
|---|---|---|
| `ora-owner-outreach-queue-refresh` | `enabled:false`, cron `55 10 * * 1`, path `…\Documents\Claude\Scheduled\ora-owner-outreach-queue-refresh\SKILL.md` | `enabled:true`, path `C:\Users\Owner\.claude\scheduled-tasks\ora-owner-outreach-queue-refresh\SKILL.md` |
| `ora-cowork-heartbeat` | `enabled:false`, cron `50 5 * * *`, path `…\Documents\Claude\Scheduled\ora-cowork-heartbeat\SKILL.md` | `enabled:true`, path `C:\Users\Owner\.claude\scheduled-tasks\ora-cowork-heartbeat\SKILL.md` |

## Steps, one id at a time (complete every step for one id before starting the next; if a step fails, stop for that id)
1. Run `list_scheduled_tasks` and confirm that this id's row has a `path` under the LAMS store (`…\Documents\Claude\Scheduled\<id>\`). If no row for this id has a LAMS path, STOP for this id: the row you would delete is the canonical CC copy. Act ONLY on the LAMS row. Same-id collision: `delete_scheduled_task` resolves to this session's own fleet. Never "test" a delete, least of all against `ora-cowork-heartbeat`.
2. MOVE the folder (never delete it): `OneDrive - Oxford Capital Partners\Documents\Claude\Scheduled\<id>\` → `…\Scheduled\_archive_2026-10-30_retired-to-ccmcp\<id>\`. Confirm the move landed.
3. Drop the LAMS registry row with `delete_scheduled_task` from this native Cowork session. NEVER use the Scheduled-sidebar trash icon.
4. Verify with `python ~/.claude/maintenance/fleet-status.py`: duplicate registrations should be 0, and the CC copy should still show `on`.
5. Move that id's entry in `maintenance/_state/retire-pending.json` from `pending` to `_completed`. Append an event_log entry via `append-event-log.py` containing the literal token `RATIFIED <id>`.

## Expected after
- Both LAMS rows are gone and both LAMS folders are archived.
- Both CC copies are enabled and untouched.
- Both retire-pending entries are completed.

## Warning
`handoffs/2026-09-28_LAMS-fleet-resume_brief.md` lists both ids among the 25 tasks it re-enables. Carve both out; retire-pending already flags them.
