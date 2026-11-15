# CC/MCP fleet — open-ended pause to "necessary only" (2026-11-09)

**Execute from:** Claude Code, native on-device (supervised). NOT a cloud-sandbox Cowork session.
**Authority:** Gabriel in-turn 2026-11-09 15:51 ET: "Pause all future scheduled tasks besides only those which are necessary."
**Scope:** CC/MCP fleet only. LAMS untouched (its single enabled task, ora-counsel-review-standard-positions-2027, is a one-shot that cannot fire before 2027-08-02).
**Type:** OPEN-ENDED pause. No resume task to register (register-scheduled-task: "a genuinely open-ended pause has no resume — say so explicitly"). No pause_windows.py capture (it records only resume-backed holds).

## Step 0 — surface + concurrency
1. Rule 3: confirm `list_scheduled_tasks` is in this session's tool registry; state "surface: native, CC/MCP fleet" from the `path` field.
2. `list_sessions`: stop if another live session is touching the scheduler.
3. Snapshot: `list_scheduled_tasks` → expected 49 enabled on CC before the pass.

## Step 1 — KEEP enabled (9). Do not touch.
| id | why necessary |
|---|---|
| ora-pm-monthly-billing | money-moving tenant billing (1st–3rd) |
| ora-pm-daily-crons | money-moving; lease critical-dates + delinquency check |
| ora-quarterly-estimate-check | Jan 15 estimated-tax installment (fires Jan 5) |
| ora-rep-hours-monthly | REP 750-hr contemporaneous log (tax status) |
| ora-wicomico-reassessment-reminder | one-shot 2027-01-08, MD reassessment appeal window |
| ora-jackson-boe-prep-reminder | one-shot 2027-06-15, Jackson Co BOE deadline 2027-07-12 |
| ora-live-branch-offbox-backup | daily off-box backup — data-loss protection |
| ora-cowork-heartbeat | dead-man chain; pausing trips the GitHub watchdog |
| ora-automation-health-monitor | fleet detector — never blanket-pause detectors |

## Step 2 — PAUSE (40). `update_scheduled_task {taskId, enabled:false}` ONLY.
Never pass `cronExpression` (re-enables). Never use the Cowork sidebar delete icon.

Data / reporting producers: ora-master-workbook-ingest, ora-cc-snapshot-refresh, ora-cc-acq-sync-weekly, ora-portfolio-desk-refresh, ora-doc-index-rebuild-monthly, ora-recovery-billing-monthly, ora-agent-usage-report-monthly, ora-closed-deal-variance-check
Daily Brief: ora-am-brief
Sourcing / market: ora-deal-sourcing-scan, ora-sourcing-construction-verify, ora-entry-market-scan, ora-passed-deal-tracker, ora-county-sales-monitor, ora-owner-outreach-queue-refresh, ora-broker-touch-cadence, ora-edge-mfg-scout-weekly, ora-edge-news-overlay-refresh
Website: ora-loopnet-listings-sync, ora-site-exposure-probe, ora-site-seo-crawl-weekly, ora-site-market-snapshot-refresh
Engineering / repo: ora-financial-code-integrity-sweep, ora-appsec-sweep, ora-full-gate-weekly, ora-prepush-gate-sweep, ora-checkout-merge-forward, ora-memory-commit-sweep, ora-pr-land-watch, ora-command-center-mirror-drift-check, ora-model-release-watch
Secondary guards: ora-health-guard, ora-task-integrity-guard, ora-doctrine-integrity-guard, ora-ground-truth-auditor
Housekeeping / annual: ora-weekly-hygiene, ora-cowork-settings-quarterly-review, ora-annual-budget-kickoff, ora-year-end-review
One-shot: ora-passed-deal-tracker-spec-sync-1113 (2026-11-13)

## Step 3 — verify (no "done" without it)
`list_scheduled_tasks`: enabled CC set == exactly the 9 KEEP ids; the 40 above show enabled:false. Paste the enabled list.
Confirm the KEEP money-moving tasks still carry their `offhost-backup:` frontmatter line (untouched, but check).
Append event_log via `python ~/.claude/maintenance/append-event-log.py`, header `## 2026-11-09 — CC fleet open-ended pause to necessary-only (40 paused, 9 kept)`.

## Known consequences (accepted by an open-ended pause)
- Daily Brief stops (incl. Eric's cc).
- ora-pr-land-watch queued "do Y once PR X lands" payloads will not run until re-enabled.
- ora-automation-health-monitor may report the 40 as quiet; that is the pause, not a fault.
- Re-enabling any task later: re-tag `[MODEL: … | checked <date>]` in the same pass (step 4b). Never re-enable ids in retire-pending.json.
