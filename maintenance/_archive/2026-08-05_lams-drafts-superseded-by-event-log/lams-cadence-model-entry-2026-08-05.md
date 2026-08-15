## 2026-08-05 — LAMS/Cowork fleet cadence + model-tag policy pass (Gabriel-directed, Cowork session)

Closes the loop the same-day CC/MCP entry ("CC/MCP fleet cadence policy: collapsed all >1x/day
tasks to daily") left open ("Not done — LAMS/Cowork fleet unreachable from Code-surface").
Same two ratified policies applied here: no LAMS/Cowork routine >1x/day; default claude-sonnet-5.

**Cadence audit** — pulled the live registry via `list_scheduled_tasks` (27 enabled recurring +
2 pending one-time + 1 disabled/fired one-time; composition matched the last known roster
exactly, no drift). 26/27 recurring tasks already ≤1x/day. One exception found, the same one
flagged going in: `ora-cowork-heartbeat` at 2x/day (05:50 + 17:50 ET) — the dead-man heartbeat
feeding Notion beacon `35c6ecd8…` → the GitHub Actions watchdog. Surfaced the tradeoff to
Gabriel via AskUserQuestion (keep 2x/day vs. collapse to 1x/day vs. collapse-and-flag-watchdog).

Gabriel initially chose the plain "reduce to 1x/day" option. Before executing, caught that this
introduces a new problem the option text underclaimed: the external GitHub Actions watchdog's
alert threshold is 16h, shorter than the 24h gap a single daily fire leaves — so a straight
cadence cut produces a **guaranteed daily false stale-alarm** (~8h before each fire), not merely
"slower detection" as originally framed. Re-surfaced the corrected tradeoff; Gabriel ruled to
proceed anyway ("cut to 1x/day now regardless"), accepting the daily false alarm as a known,
tolerable cost until the watchdog threshold is separately widened past 24h (repo:
ZeOoba/ora-cowork-watchdog — outside scheduler-MCP reach, not touched this pass, flagged as a
follow-up). Applied via `update_scheduled_task`: `50 5,17 * * *` -> `50 5 * * *` (kept the AM
slot). Description updated in the same call to record both the retime rationale and the known
watchdog-threshold gap. Verified via `list_scheduled_tasks`: next fire 2026-08-06 ~05:57 ET
(jittered), daily thereafter.

**Model-tag audit** — per `reference_scheduled_task_model_standard.md` (current standard
unchanged, claude-sonnet-5 since 2026-07-08). No task on this fleet carries a non-standard
model id (unlike CC/MCP, which has confirmed opus-5/fable drift on several tasks) — so no
LAMS task required the disable -> archive -> delete -> recreate cycle this pass. Found:
- 1 genuine `MODEL-UNTAGGED` gap: `ora-counsel-review-standard-positions-2027` (one-time,
  enabled, fires 2027-08-02) — in scope per the doctrine's LAMS-one-time-enabled row, tag
  was missing entirely. Added `[MODEL: claude-sonnet-5 | set 2026-08-05]`.
- 8 tasks with a tag date predating the task's own last content/prompt revision by 3-22 days
  (cosmetic only, no wrong-model implication): `automation-health-monitor` (22d),
  `ora-skill-store-drift-check` (19d), `ora-skill-text-audit` (16d), `ora-om-intake-ocr` (16d),
  `ora-lease-expiration-brief` (13d), `ora-monday-sync` (13d), `ora-friday-closeout` (10d),
  `ora-stale-pipeline-nudge` (3d). Gabriel approved re-tagging all 9 in one pass; applied via
  `update_scheduled_task` (description field only — no cron/prompt changes on the 8 recurring
  tasks). Verified via `list_scheduled_tasks`: all 9 now read `[MODEL: claude-sonnet-5 | set
  2026-08-05]`.

**Net:** LAMS/Cowork fleet is now 27/27 enabled recurring + 2/2 enabled one-time tasks tagged
claude-sonnet-5, current as of today. One standing cadence exception (`ora-cowork-heartbeat`,
now 1x/day per Gabriel's ruling) carries a known, accepted watchdog-threshold gap pending a
separate fix. Summary emailed to ggoldberg@oxfordra.net only, no cc, per routing canon.
