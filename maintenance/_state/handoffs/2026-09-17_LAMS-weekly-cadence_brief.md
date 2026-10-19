# Handoff — LAMS/Cowork weekly-cadence retime (2026-09-17)

**Run from: a native on-device Cowork session** (the Desktop app itself, or "Run this task → On your computer"). Not a cloud-sandbox Cowork session, and not Claude Code: CC's `update_scheduled_task` resolves to the CC fleet only.

**Authority:** Gabriel, in-turn 2026-09-17: "I want all routines to run at most once per week." Scope covers Claude routines on both fleets plus ORA Windows tasks. Kept at current cadence: Daily Brief, dead-man/watchdog chain, merge-forward, mirror deploy.

## Step 0 — Surface assertion (register-scheduled-task Rule 3)
Search THIS session's tool registry for `list_scheduled_tasks`. If it is absent, STOP; this is the wrong surface. If present, call it and confirm the `path` fields resolve under `...\Documents\Claude\Scheduled\` (the LAMS fleet).

## Step 1 — Retime (2 tasks)
| taskId | before (cron) | after (cron) |
|---|---|---|
| `automation-health-monitor` | `5 11 * * 1-5` | `5 11 * * 1` (Mon 11:05) |
| `ora-health-guard-fail-aging-nudge` | `0 9 * * 1-5` | `0 9 * * 1` (Mon 09:00) |

**⚠ Footgun proven 2026-09-17 on CC:** `update_scheduled_task` with `cronExpression` alone RE-ENABLES a disabled task. For each call, read the task's current `enabled` first, then pass `cronExpression` AND `enabled: <that same value>` in the SAME call.

## Unchanged (do NOT touch)
- `ora-cowork-heartbeat` (`50 5 * * *`) is a dead-man chain exception and stays daily.
- `ora-ar-export-freshness-nudge` (`30 11 1,15 * *`): 1st/15th is already ≤ once per week.
- All other LAMS tasks are weekly or less frequent (per the 2026-09-14 roster). Re-confirm from the live `list_scheduled_tasks`. If any other recurring task fires more than once a week, report it; don't retime it unilaterally.

## Step 2 — Verify
Call `list_scheduled_tasks` and paste both entries (id, cron, enabled, nextRunAt). `enabled` must equal its pre-call value. Re-check each task's SKILL.md frontmatter for dropped non-owned keys (known `update_scheduled_task` behavior).

## Expected after-state
Both tasks fire Mondays only, with `enabled` unchanged. No other LAMS task changes.
