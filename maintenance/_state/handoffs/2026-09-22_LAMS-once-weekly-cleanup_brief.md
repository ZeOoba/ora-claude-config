# Handoff — LAMS/Cowork once-per-week cleanup (2026-09-22)

**Supersedes** `2026-09-17_LAMS-weekly-cadence_brief.md` (never applied). Do only this brief.

**Run from: a native on-device Cowork session**: the Desktop app itself, or "Run this task → On your computer". Do NOT run it from a cloud-sandbox Cowork session or from Claude Code. Claude Code's scheduled-task tools reach only the CC fleet.

**Authority:** Gabriel, in-turn 2026-09-22: "yes, do the CC fixes and write the LAMS handoff". This approves the fleet audit's rule that no routine except the Daily Brief runs more than once a week. The CC half is done: two tasks retimed and two expired one-time tasks retired (see `event_log.md` 2026-09-22).

## Step 0 — Surface assertion (register-scheduled-task Rule 3)
Search THIS session's tool registry for `list_scheduled_tasks`. If it is absent, STOP: this is the wrong surface. If it is present, call it and confirm that every `path` resolves under `...\Documents\Claude\Scheduled\`. State the verdict before any write.

## Step 1 — Retime (1 task)
| taskId | before | after |
|---|---|---|
| `automation-health-monitor` | `5 11 * * 1-5` | `5 11 * * 1` (Mon 11:05) |

**⚠ Footgun:** `update_scheduled_task` with `cronExpression` alone RE-ENABLES a disabled task. Read `enabled` first, then pass `cronExpression` + `enabled: <same value>` in ONE call. The whole LAMS fleet was `enabled:false` as of 2026-09-22, so expect to pass `false`.

## Step 2 — RETIRE (3 tasks) — LAMS order: ARCHIVE FIRST, DELETE SECOND
All three are in `~/.claude/maintenance/_state/retire-pending.json`.
| taskId | why |
|---|---|
| `ora-ar-export-freshness-nudge` | Superseded by CC `ora-ar-feed-sweep`. Ratified 2026-09-22. |
| `ora-health-guard-fail-aging-nudge` | Its 48h FAIL-aging check is vestigial once ora-health-guard runs weekly. Not the sole invoker of any script. |
| `ora-lams-fleet-resume-20260911` | Expired one-time task (fired 2026-09-11). |

For each one:
1. MOVE `...\Documents\Claude\Scheduled\<id>\` to `...\Documents\Claude\Scheduled\_archive_2026-09-22_retired\<id>\`.
2. VERIFY that the SKILL.md exists at the archive path.
3. Only then call `delete_scheduled_task(<id>)`. **Never use the sidebar trash icon.**

If a step fails partway, stop. Do not leave a registry row pointing at a moved folder.

After all three: move each entry from `pending` to `_completed` in `retire-pending.json` (with a `completed` date). Append one `RATIFIED` line naming the 3 ids via `python ~/.claude/maintenance/append-event-log.py`. Add the ids to the do-NOT-re-register list in `~/.claude/session-context.md`.

## Step 2b — (SUPERSEDED 2026-09-23: do NOT register a LAMS resume task)
The 09-28 LAMS resume is handled by the separate MANUAL brief
`maintenance/_state/handoffs/2026-09-28_LAMS-fleet-resume_brief.md`, run by hand in a native Cowork
session on Mon 09-28 by 10:30 ET. It covers the same 25 ids, requires this cleanup to be done first,
catches up the heartbeat and missed Monday slots, and is what both CC reminders
(`ora-routine-pause-resume-09-28` STEP 5, `ora-resume-0928-attend-reminder`) already point to.
Registering `ora-lams-fleet-resume-20260928` here as well would create a second, conflicting resume
path and two attended approval streams at 10:00. Reconciled with the session that wrote that brief
on 2026-09-23.

## Step 2c — Re-enable the heartbeat ONLY (Gabriel, 2026-09-23: "add the heartbeat exception")
The one exception to "re-enable nothing": `ora-cowork-heartbeat` goes back on now, so the dead-man chain (heartbeat → Notion `35c6ecd8` → GitHub `ZeOoba/ora-cowork-watchdog`) can see the LAMS fleet again for the 5 days before the 09-28 resume.
1. Call `update_scheduled_task("ora-cowork-heartbeat", enabled: true)`. Pass ONLY `taskId` + `enabled`. Keep the cron `50 5 * * *` (daily) and do not change the description or re-stamp `[MODEL:]`.
2. Call `run_scheduled_task("ora-cowork-heartbeat")` once, record the returned session id, and poll `list_task_runs("ora-cowork-heartbeat", limit: 3)` until that run is no longer "running" (cap: 30 min). This publishes a fresh beat today instead of waiting for tomorrow's 05:50.
3. If either call fails, stop and report. Do not touch any other task to compensate.

## Do NOT touch
- `ora-cowork-heartbeat` stays DAILY. Gabriel ruled on 2026-09-22 ("Keep heartbeat daily"), so it is the standing dead-man exception to the once-a-week cap.
- Do **not re-enable anything** in this pass **except `ora-cowork-heartbeat` (Step 2c)**. The rest of LAMS resumes together with CC on 2026-09-28 (Gabriel, 2026-09-23) via the manual brief `2026-09-28_LAMS-fleet-resume_brief.md`, not now.
- Any other LAMS recurring task that fires more than once a week: report it, don't change it. The expected set is empty.

## Step 3 — Verify, then report
Call `list_scheduled_tasks` and paste the following:
- `automation-health-monitor`: cron `5 11 * * 1`, with `enabled` unchanged.
- The three retired ids: absent from the list.
- The count of recurring tasks with `enabled:true` (expected: 1, namely `ora-cowork-heartbeat` with cron `50 5 * * *`).
- The Step 2c heartbeat run: session id and final status from `list_task_runs`.

Re-check the `automation-health-monitor` SKILL.md frontmatter for dropped non-owned keys.

## Expected after-state
LAMS has 26 registry rows (29 minus the 3 retired). Every recurring task fires once a week or less, except `ora-cowork-heartbeat`, which stays daily (Gabriel, 2026-09-22). `ora-cowork-heartbeat` is enabled (Step 2c). The other 24 recurring tasks stay disabled until the manual resume on 2026-09-28 (see `2026-09-28_LAMS-fleet-resume_brief.md`).
