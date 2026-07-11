# ora-task-integrity-guard — run note 2026-07-10 (12:54 ET fire)

**Determination: ALARM SUPPRESSED — false-positive replay of an already-actioned, already-communicated retirement. No email sent.**

## Engine outputs
- **guard.ps1**: `{checked:34, restored:["ora-dashboard-refresh"], backed_up:["ora-site-exposure-probe"], missing_everywhere:[]}` — exit 0.
- **membership-guard.ps1**: `{enabled_total:30, disappeared:[], disabled:["ora-dashboard-refresh"], added:["ora-open-sessions-board","ora-site-exposure-probe","ora-command-center-mirror-drift-check","ora-week-ahead-briefing"], parse_miss:[], mcp_snapshot_stale_days:0}` — exit 0.

## Why no alarm email
Both alarm-triggering fields (`restored`, `disabled`) point ONLY to `ora-dashboard-refresh`, which was **intentionally retired 2026-07-07**:
- SKILL.md lives in `scheduled-tasks\_archive_2026-07-07_retired\ora-dashboard-refresh\SKILL.md`.
- Its deploy source (`oxford-perfection\ora-dashboard\`) was archived 2026-07-07; task HALTED (no longer deploying).
- Its Notion dashboard-refresh function is subsumed by `ora-master-workbook-ingest`.

Gabriel was **already emailed TWICE today** about this exact task by the morning `automation-health-monitor`/`ora-health-guard` run (11:07–11:15 ET): the original flagged it as late-firing, and the addendum reported it HALTED with a pause/retarget recommendation. See `_shared\_tmp_health_alert_20260710.txt` and `_tmp_health_alert_addendum_20260710.txt`.

Mechanics of the false positive (matches the STEP 0.5-documented 2026-07-09 replay pattern, different task):
- `guard.ps1` is add-only / newest-wins and does not know about retirement; it restored the archived SKILL.md at the still-present registry filePath — benign.
- `membership-guard.ps1` diffs against its own `membership-state.json` baseline, which had not yet absorbed the 07-07 retirement, so it flagged the retirement as a "newly disabled" transition — a lagging-baseline replay, not a new drop. `mcp_snapshot_stale_days:0` confirms today's MCP snapshot (STEP 0.5) is fresh; the staleness is on the membership-state side only.

`added` (4 tasks) are all legitimately live in `list_scheduled_tasks` today — not an alarm condition.

**Net: no genuine silent drop. `disappeared`/`missing_everywhere`/`parse_miss` all empty; `checked=34` (not zero). Suppressing the duplicate would be correct even under strict reading, since re-alarming an already-actioned + twice-emailed retirement is the documented anti-pattern.** The membership baseline will self-reconcile on the next run now that the retirement is in-state.

## STEP 2.5 model-currency (CC/MCP, informational)
14 tasks: 11 MODEL-UNVERIFIABLE, 3 MODEL-UNTAGGED (`canary-model-check-temp`, `ora-command-center-mirror-drift-check`, `ora-site-exposure-probe`), 0 STALE, 0 CURRENT. Standard = claude-sonnet-5. UNVERIFIABLE is the expected CC/MCP baseline (server-pinned model, per 2026-07-08 finding). The 3 UNTAGGED tasks are new since the last tagging pass — a future tagging sweep should stamp `[MODEL: UNVERIFIABLE | checked …]` on the two live ones (`ora-command-center-mirror-drift-check`, `ora-site-exposure-probe`); `canary-model-check-temp` is inert/disabled and can be ignored.
