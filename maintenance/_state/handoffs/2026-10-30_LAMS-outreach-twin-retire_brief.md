# Handoff — retire the LAMS twin of `ora-owner-outreach-queue-refresh`

**Execute from:** a **native on-device Cowork session** (the desktop app itself, or Claude Code "Run this task → On your computer"). NOT a cloud-sandbox Cowork session — it carries none of the scheduled-task MCP tools.
**Ratified:** Gabriel, in-turn 2026-10-30 ("Start Phase 0" of the Deal Sourcing Expansion Plan, Notion page `4096ecd8-9e59-8150-8417-c1d9a30130e4`).
**Skill:** `register-scheduled-task` — RETIRE, LAMS ordering (archive first, registry second).

## Step 0 — surface assertion (Rule 3), before anything else
Search this session's tool registry for `list_scheduled_tasks`. Absent → STOP; do neither step below. State the verdict.

## Expected before
- LAMS registry: `ora-owner-outreach-queue-refresh`, `enabled:false`, cron `55 10 * * 1`, path `…\Documents\Claude\Scheduled\ora-owner-outreach-queue-refresh\SKILL.md`.
- CC registry: same id, `enabled:true`, path `C:\Users\Owner\.claude\scheduled-tasks\ora-owner-outreach-queue-refresh\SKILL.md` — **canonical; do not touch.**

## Steps (one pass; do none if you cannot do all)
1. `list_scheduled_tasks` → confirm the entry whose `path` is the LAMS store. Act ONLY on that row.
2. MOVE (never delete) `OneDrive - Oxford Capital Partners\Documents\Claude\Scheduled\ora-owner-outreach-queue-refresh\` → `…\Scheduled\_archive_2026-10-30_retired-to-ccmcp\ora-owner-outreach-queue-refresh\`. Verify the move landed.
3. Drop the LAMS registry row (`delete_scheduled_task` from this native Cowork session, which resolves session-local to LAMS). Never the Scheduled-sidebar trash icon.
4. Verify with `python ~/.claude/maintenance/fleet-status.py`: duplicate registrations 0; CC copy still `on`.
5. Move this id's entry in `maintenance/_state/retire-pending.json` from `pending` to `_completed`; append an event_log entry via `append-event-log.py` containing the literal token `RATIFIED ora-owner-outreach-queue-refresh`.

## Expected after
LAMS row gone; LAMS folder archived; CC copy enabled and untouched; retire-pending entry completed.

## Warning
`handoffs/2026-09-28_LAMS-fleet-resume_brief.md` lists this id among the 25 to re-enable. Carve it out (retire-pending already flags it).
