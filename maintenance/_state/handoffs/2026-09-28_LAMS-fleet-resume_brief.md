# Handoff — LAMS/Cowork fleet resume (run Mon 2026-09-28)

**Run from: a native on-device Cowork session**: the Desktop app itself, or "Run this task → On your computer". Do NOT run it from a cloud-sandbox Cowork session or from Claude Code. Claude Code's scheduled-task tools reach only the CC fleet (confirmed 2026-09-22: every `path` there resolved under `~\.claude\scheduled-tasks\`).

**When:** Mon 2026-09-28, in the same attended sitting as the CC resume (`ora-routine-pause-resume-09-28` fires 10:00 ET; reminder 09:30). **Start by 10:30 ET**: the first LAMS Monday slot is `ora-monday-sync` at 10:35. Done by then, no Monday catch-up is needed (Step 4).

**Authority:** Gabriel, in-turn 2026-09-22: "write a LAMS resume handoff for 09-28". That settles the open item in `event_log.md` 2026-09-22 ("No LAMS resume is registered and the whole LAMS fleet is disabled"). This brief supersedes the "Do not re-enable anything" line in `2026-09-22_LAMS-once-weekly-cleanup_brief.md`, but only once that brief's Steps 1–2 are done. It also absorbs the 09-22 partial re-enable decision (outreach-queue-refresh, heartbeat, automation-health-monitor): those 3 ids are in the list below, and the call is idempotent if they are already on.

**Why this is a brief, not a registered one-time task:** a scheduled resume blocks on every `update_scheduled_task` approval prompt when nobody is present (OI-273, `event_log.md` 2026-09-12). You need to be at the machine either way, so run it by hand.

## State at writing (2026-09-22, LAMS registry read directly)
- 29 rows: 27 recurring (all `enabled:false`) + 2 one-time (`ora-counsel-review-standard-positions-2027` `enabled:true`, fires 2027-08-02; `ora-lams-fleet-resume-20260911` expired).
- No record of who disabled the LAMS fleet or when (`event_log.md` 2026-09-22). This is the first resume of that disable, not the end of a bounded pause.
- Only `automation-health-monitor` (`5 11 * * 1-5`) and `ora-health-guard-fail-aging-nudge` (`0 9 * * 1-5`) break the once-a-week cap. The cleanup brief handles both. `ora-cowork-heartbeat` (`50 5 * * *`) is the ratified daily exception.

## Step 0 — Surface assertion (register-scheduled-task Rule 3)
Search THIS session's tool registry for `list_scheduled_tasks`. If it is absent, STOP: wrong surface. If it is present, call it and confirm every `path` resolves under `...\Documents\Claude\Scheduled\`. State the verdict before any write. Keep this listing: it is the "before" snapshot for Step 3.

Progress marker (every step below writes one; `--fleet` is mandatory, since the 09-11 run omitted it):
`python C:\Users\Owner\.claude\maintenance\task-progress-marker.py write --fleet lams --task-id lams-resume-2026-09-28 --step 0 --of 5 --note "surface asserted"`

## Step 1 — Prerequisite: the once-weekly cleanup must be done first
Read `C:\Users\Owner\.claude\maintenance\_state\retire-pending.json` and check the Step 0 listing:
- (a) `pending` holds no entry with `fleet: "lams"`, **and**
- (b) the three retired ids (`ora-ar-export-freshness-nudge`, `ora-health-guard-fail-aging-nudge`, `ora-lams-fleet-resume-20260911`) are absent from the listing, **and**
- (c) `automation-health-monitor` shows cron `5 11 * * 1`.

If any check fails, run `2026-09-22_LAMS-once-weekly-cleanup_brief.md` Steps 1–3 now, in this session, exactly as written, and then re-check. If it cannot complete, carry on with this brief anyway, but: never re-enable any id still in `pending`; and if the AHM retime failed, pass `cronExpression: "5 11 * * 1"` **together with** `enabled: true` in ONE call for that id, so it does not come back at `1-5`. Report which path you took.

Marker: `--step 1 --of 5 --note "cleanup: done-before | done-now | partial <why>"`

## Step 2 — Re-enable (25 ids)
Call `update_scheduled_task(taskId, enabled: true)` for each id below. Pass ONLY `taskId` + `enabled`, and send the calls in as few turns as possible (each one needs an approval click). Skip any id Step 1 left in `pending`. An id that is already `enabled:true` is fine: the call is a no-op, so record it as "already on".

| # | taskId | cron | cadence |
|---|---|---|---|
| 1 | `ora-cowork-heartbeat` | `50 5 * * *` | **daily — ratified dead-man exception** |
| 2 | `automation-health-monitor` | `5 11 * * 1` | Mon (post-cleanup) |
| 3 | `ora-owner-outreach-queue-refresh` | `55 10 * * 1` | Mon |
| 4 | `ora-monday-sync` | `35 10 * * 1` | Mon |
| 5 | `ora-lease-expiration-brief` | `45 10 * * 1` | Mon |
| 6 | `ora-tenant-contact-gap-sweep` | `50 10 * * 1` | Mon |
| 7 | `ora-insurance-renewal-monitor` | `40 11 * * 1` | Mon |
| 8 | `ora-skill-store-drift-check` | `10 12 * * 1` | Mon |
| 9 | `ora-ic-memo-pipeline-reconciliation` | `30 10 * * 2` | Tue |
| 10 | `ora-om-intake-ocr` | `15 6 * * 3` | Wed |
| 11 | `ora-underwrite-doctrine-staleness-check` | `0 13 * * 3` | Wed |
| 12 | `ora-critical-deadlines-scan` | `5 9 * * 4` | Thu |
| 13 | `ora-dd-critical-tracker` | `35 9 * * 4` | Thu |
| 14 | `ora-stale-pipeline-nudge` | `15 10 * * 4` | Thu |
| 15 | `ora-hubspot-notion-contact-sync` | `45 13 * * 4` | Thu |
| 16 | `ora-friday-closeout` | `30 16 * * 5` | Fri |
| 17 | `ora-session-sweep` | `0 20 * * 0` | Sun |
| 18 | `ora-capex-idea-stage-nudge` | `15 12 1 * *` | monthly |
| 19 | `ora-consolidate-memory-monthly` | `0 5 2 * *` | monthly |
| 20 | `ora-loan-terms-reconciliation` | `20 13 6 * *` | monthly |
| 21 | `ora-skill-text-audit` | `45 9 15 * *` | monthly |
| 22 | `ora-replacement-cost-refresh` | `10 6 9 3,6,9,12 *` | quarterly |
| 23 | `ora-bearmode-refresh` | `25 6 9 3,6,9,12 *` | quarterly |
| 24 | `ora-gis-endpoint-liveping` | `35 6 9 3,6,9,12 *` | quarterly |
| 25 | `ora-exit-cap-spotcheck` | `45 6 9 3,6,9,12 *` | quarterly |

**Do NOT touch:** `ora-counsel-review-standard-positions-2027` (one-time, already enabled; leave it alone) · the three retired ids · anything not in this table. If the live registry has a recurring LAMS id that is missing from this table, report it and do not enable it.

**Do NOT change** any description, prompt, cron (except the Step 1 AHM fallback), or `[MODEL:]` tag or date. A resume is not a model observation (register-scheduled-task bounded-pause section). This overrides the 09-22 partial-enable note that said "Re-tag `[MODEL:]` at enable".

Marker: `--step 2 --of 5 --note "enabled N/25; already-on <ids>; skipped <ids>"`

## Step 3 — Verify
Call `list_scheduled_tasks` again and confirm:
- All 25 ids show `enabled:true` (minus Step 1 carve-outs), with each cron **identical** to the table. Any cron that moved is a defect, so report it.
- Every enabled recurring task fires at most once a week, except `ora-cowork-heartbeat`.
- `ora-counsel-review-standard-positions-2027` is unchanged. The three retired ids are absent.
- Re-check the `automation-health-monitor` and `ora-cowork-heartbeat` SKILL.md frontmatter for dropped non-owned keys (the update-call footgun).

Then run, from the same session:
- `python C:\Users\Owner\.claude\maintenance\_shared\pause_windows.py capture` to close the LAMS pause window in the durable record.
- `python C:\Users\Owner\.claude\maintenance\registry-membership-probe.py` twice. The second run must be clean. The probe regenerates the fleet summary in `session-context.md` and `_state/fleet-roster.md`. Expected: LAMS 25 live recurring + 1 pending one-time.

Marker: `--step 3 --of 5 --note "verified N/25; probe <clean|drift>"`

## Step 4 — Catch-up (only for slots already missed)
- **`ora-cowork-heartbeat`:** the cleanup brief's Step 2c re-enables it before 09-28, so normally it is already on and its 09-28 05:50 run has fired. Check `list_task_runs("ora-cowork-heartbeat", limit: 3)`. Only if there is no successful run today (Step 2c not done, or the app was closed at 05:50), `run_scheduled_task` it once now.
- **Monday slots:** for each Monday id (#2–#8) whose 09-28 fire time has **already passed** when Step 2 finished, `run_scheduled_task` it once. If Step 2 finished before 10:35, none of them are due; say so.
- Run order, one after another: `ora-monday-sync` → `ora-lease-expiration-brief` → `ora-tenant-contact-gap-sweep` → `ora-owner-outreach-queue-refresh` → `ora-insurance-renewal-monitor` → `ora-skill-store-drift-check` → **`automation-health-monitor` last**, so it sees the resumed fleet.
- WAIT rule (same as the CC resume): record the session id that `run_scheduled_task` returns, then poll `list_task_runs(taskId, limit: 3)` about every 2 minutes until that run is no longer "running". Cap each wait at 45 minutes; on a cap, record TIMEOUT and move on.
- **`ora-owner-outreach-queue-refresh`:** exit 3 = the unreleased-pack HALT (09-22 funnel repair), meaning "release needed". It is not a failure, so report it that way and do not re-run it. Outreach is DRAFT ONLY: nothing is mailed or sent to an owner.
- Do not catch up `ora-session-sweep` (Sun 09-27; next 10-04) or anything monthly or quarterly. None of those slots fell inside the window that matters.
- Outlook COM exit 3/4 during overlapping runs is probably contention, so report it as that. Do not re-run a task to force a send.

Marker: `--step 4 --of 5 --note "catch-up: <ok>/<due> ok; <timeout/fail ids>"`

## Step 5 — Record and report
1. Append one event via `python C:\Users\Owner\.claude\maintenance\append-event-log.py` (never Edit the log). Heading: `2026-09-28 — LAMS fleet resumed (N/25)`. Include the ids enabled or skipped, the Step 1 path taken, the verify result, the catch-up table, and the probe output. Mark the 09-22 entry "LAMS fleet fully disabled; Gabriel approves partial re-enable" **Execution: DONE (subsumed by this resume)**.
2. Send ONE email to `ggoldberg@oxfordra.net` only (no cc) via `powershell -File C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1`. Subject: `[ORA] LAMS fleet resumed — N/25 · catch-up M/K`. Prefix `[ACTION]` if any id is still disabled, any cron moved, or any catch-up run did not succeed. On a non-zero exit, retry once, then record the failure in the marker. A "succeeded" run status is not proof of output, so say that in the body.

Marker: `--step 5 --of 5 --note "done"`

## Stop conditions
- Step 0 fails → STOP, no writes.
- A write refers to an id that isn't in the registry, or a `path` outside `Documents\Claude\Scheduled\` → STOP and report. Never splice registry JSON.
- Never use the sidebar trash icon. To pause, use `update_scheduled_task(enabled:false)` or the Cowork toggle.

## Expected after-state
LAMS: 26 rows. 25 recurring are `enabled:true` (24 at once a week or less, plus the daily heartbeat) and 1 pending one-time (`ora-counsel-review-standard-positions-2027`). Dead-man chain live: heartbeat → Notion `35c6ecd8` → GitHub `ZeOoba/ora-cowork-watchdog`. `automation-health-monitor` next fires Mon 2026-10-05 11:05, or ran today via catch-up.
