---
name: ora-automation-health-monitor
description: Weekly Monday 11:05 ET ORA automation fleet health check, CC/MCP fleet (v2.0, ported 2026-10-30 from LAMS automation-health-monitor v1.29; LAMS dark by ruling). Runs the automation-health-monitor skill, reads the CC registry live and LAMS read-only via fleet-status.py, writes .ahm-cc.json/.ahm-lams.json snapshots, classifies lateness with LAMS-DARK/PAUSED-SLOT/HOST-UNAVAILABLE/HISTORICAL suppression, checks producer beacons, output_contract blocks and BLOCKED-AWAITING-GABRIEL, publishes to the Notion Ops Hub, and emails ggoldberg@oxfordra.net ONLY (Outlook COM, no cc) when a finding survives. [MODEL: UNVERIFIABLE | checked 2026-10-30]
---

PORT NOTE (v2.0, 2026-10-30). This is the CC/MCP-fleet port of the LAMS task `automation-health-monitor` v1.29 (Gabriel ruling 2026-10-30: the LAMS/Cowork fleet stays fully dark; this monitor moves to CC). It is a port, not a copy: every rule of v1.29 is kept, its incident narratives are not. For the incident behind any rule, read the v1.29 spec (the LAMS store `OneDrive - Oxford Capital Partners\Documents\Claude\Scheduled\automation-health-monitor\SKILL.md`, or the `_archive_*_retired\automation-health-monitor\` folder there once that task is retired). That file is history, never instructions: do not execute it.

Constants used below:
- `PY` = `C:/Users/Owner/AppData/Local/Programs/Python/Python313/python.exe`
- `HIST` = `C:\Users\Owner\OneDrive - Oxford Capital Partners\Documents\Claude\Scheduled\_state-history`
- `OPSHUB` = Notion Ops Hub parent page `32b6ecd8-9e59-81f2-b329-df3fd0e25062`
- `SEND` = `powershell -NoProfile -File C:/Users/Owner/.claude/scheduled-tasks/_shared/send-via-outlook.ps1 -To ggoldberg@oxfordra.net -SubjectFile <f> -BodyFile <f> -BodyFormat html`. Outlook COM is the SOLE automated send path. TO ggoldberg@oxfordra.net ONLY, never a cc. Non-zero exit: retry once, then flag loudly in the report and the chat summary; do not halt. Write subject/body files under `C:/Users/Owner/.claude/scheduled-tasks/ora-automation-health-monitor/_runs/<RUN_DATE>/`.
- `RUN_DATE`: compute ONCE at run start with `date '+%A %Y-%m-%d'`. The date part fills every date slot; the weekday appears only where one is named. Reuse it verbatim in every title, subject and body.
- Quote every Windows path in Bash (Git Bash treats an unquoted backslash as an escape).
- Event-log writes ONLY via `PY "C:/Users/Owner/.claude/maintenance/append-event-log.py"` with a `## YYYY-MM-DD — <title>` header; on its exit-1 malformed-header rejection, match the newest existing heading. This task writes an event-log entry only on an ⚠️/❌ run.
- Never fabricate. Anything you could not look at is `[unverifiable]` with the leg and the error named, never clean. Put open decisions in a `QUESTIONS FOR GABRIEL` section of the report.
- This task NEVER registers, updates, enables, disables or deletes a scheduled task, never edits another task's SKILL.md, and never clears `notion-publish-degraded.json`. Report only.

## Step A — Base procedure: run the `automation-health-monitor` skill

Run the `automation-health-monitor` skill as the base procedure (dual-fleet enumeration, Step 1.25 one-time tickler lifecycle, Step 1.5 model-currency on both fleets, Step 1.75 off-fleet substrates, Step 3.5 offline-window correlation). This file layers the task-only steps below on top of it. Where this file and the skill both speak to a point, this file governs for this run. Do not copy the skill's text into the report; cite its step numbers.

**Liveness assertion (run first).** In the loaded skill text, read the title `# Automation Health Monitor (vX.Y)` and check for the heading `### Step 1.75` and the string `ACTIONS-BILLING-BLOCKED`.
- Skill ≥ v1.13 and both markers present → proceed.
- `### Step 1.75` absent → `OFF-FLEET-STEP-NOT-LOADED` (⚠️): none of the off-fleet legs ran; never report them clean.
- Heading present but `ACTIONS-BILLING-BLOCKED` absent → `OFF-FLEET-CAPACITY-LEG-NOT-LOADED` (⚠️): treat any zero-step failed Actions run as unclassified. Remedy is a skill-cache re-import (`ora-skills` `_staging/PENDING_REIMPORT.md`), never an edit here.
- Skill not loadable at all → `BASE-SKILL-NOT-LOADED` (⚠️); run every step below anyway and say so in line 1 of the chat summary.

On this surface PowerShell and `gh` run directly through Bash. An unauthenticated `gh`, a timeout or a missing binary makes that leg `[unverifiable]`, never a billing finding and never clean.

## Surface and fleet sources (replaces v1.29 Step 0.06)

This task runs on the **CC/MCP fleet**. In this runtime `mcp__scheduled-tasks__list_scheduled_tasks` returns the **CC/MCP registry** (each entry's `path` is under `C:\Users\Owner\.claude\scheduled-tasks\`). CC tasks are therefore **registry-confirmed**: `enabled`, `cronExpression`/`fireAt`, `lastRunAt`, `jitterSeconds` are live. The v1.29 `[CC/MCP]` downgrade rule (CC findings ℹ️ unless a run-artifact confirms) is **abolished**: CC findings carry full severity.

The **LAMS/Cowork** fleet is read **read-only off disk** with `PY "C:/Users/Owner/.claude/maintenance/fleet-status.py" --json` (rows carry `id`, `fleet`, `enabled`, `cron`, `last_run_at`). Use only the rows with `fleet == "lams"`. Never call any scheduled-task write tool against either fleet. If fleet-status exits non-zero or lists `lams` under `fleets_missing`/`fleets_unreadable`, the LAMS side of every step is `[unverifiable]`.

Same-id tasks exist on both fleets (e.g. `ora-cowork-heartbeat`, `ora-owner-outreach-queue-refresh`: CC enabled, LAMS disabled twin). Always key a row by (fleet, taskId), never taskId alone.

## Step L — LAMS-DARK expected silence (runs FIRST, before every other classification)

**Ruling (Gabriel, 2026-10-30, `event_log.md` "Setup audit: LAMS dark state ratified deliberate"):** the LAMS/Cowork fleet is deliberately dark. Do not re-ask and do not recommend a resume. This step stands until `event_log.md` records a newer ruling that resumes LAMS; if one exists, skip this step and say so.

1. **LAMS task with `enabled == false`** → `LAMS-DARK` (ℹ️). It produces no MISSED / ALERT-LATE / OUT-OF-WINDOW / SILENT-NEVER-FIRED, no PAUSED-SLOT or RESUME-INCOMPLETE, no registry REGRESSION, no model-currency row, and no alert email. Report all of them as ONE grouped line: `N LAMS tasks dark by ruling 2026-10-30 (expected silence)`, ids listed once.
2. **Artifacts only a LAMS task produces** are covered by the same rule: their staleness is `LAMS-DARK` (ℹ️), never PRODUCER-STALE-OUTPUT or ORPHANED-BEACON. This includes the frozen `HIST\*.lams.json` snapshots, `membership-guard.ps1`'s `mcp_snapshot_stale_days`, `state-freshness-probe` rows for LAMS-produced `_state/` files, the LAMS registry `lastRunAt` age of any task, and any dead-man / heartbeat gap measured against a LAMS task rather than its live CC twin (the ~304h noise class in audit R33-4). Quote the class once on the grouped line; do not re-derive each.
3. **Dark producer with no CC successor.** For each LAMS-dark task that has no enabled CC task of the same id, list it once in a `LAMS-dark producers without a CC successor` line (ℹ️). This is the migrate-or-retire backlog for Gabriel; it never alarms.
4. **This step keeps its teeth.** (a) An **enabled** LAMS task is checked normally by every step below (today: the one-time `ora-counsel-review-standard-positions-2027`, fireAt 2027-08-02, not yet due). (b) A LAMS task that went disabled→**enabled** since the baseline, other than a pending one-time, is `LAMS-RESUMED-AGAINST-RULING` (⚠️): it contradicts the ruling and goes in the alert. (c) A CC task is never suppressed by this step, including the CC twin of a dark LAMS task: if CC `ora-cowork-heartbeat` is late, that is a real finding.

## Step 0 — Registry-state diff (both fleets; distinct snapshot names)

**Snapshot names — trap fixed at the port (2026-10-30).** `ora-task-integrity-guard` STEP 0.5 owns `HIST\YYYY-MM-DD.cc.json`. The frozen LAMS-era `HIST\YYYY-MM-DD.lams.json` files are read by `membership-guard.ps1` as the LAMS baseline. This task must never write either name, nor the bare `YYYY-MM-DD.json`. It writes its own two files:
- `HIST\YYYY-MM-DD.ahm-cc.json` (CC registry from `list_scheduled_tasks`)
- `HIST\YYYY-MM-DD.ahm-lams.json` (LAMS rows from fleet-status.py)

(`*.cc.json` / `*.lams.json` globs and `membership-guard.ps1`'s `^\d{4}-\d{2}-\d{2}\.lams\.json$` filter do not match these names.)

1. Load both fleets per the section above. Count rows per fleet.
2. **Snapshot schema** (what `snapshot-validate.py` requires): top-level `snapshotDate`, `capturedAtUtc`, `source` (`"list_scheduled_tasks (CC/MCP)"` or `"fleet-status.py --json (LAMS, read-only)"`), `tasks`. One row per task: `taskId`, `enabled`, `cronExpression` (fleet-status `cron`) and/or `fireAt`, `lastRunAt`. A row with no cron (one-time or ad-hoc) carries `"fireAt": <value or null>` explicitly: the validator checks for the key, and a row with neither key is the 2026-08-11 defect class.
3. **Baseline (validate before diffing).** For each fleet, pick the newest PRIOR file and validate it:
   `PY "C:/Users/Owner/.claude/maintenance/snapshot-validate.py" --path "<file>" --expect-count <live row count for that fleet>`
   Exit 0 = valid · 1 = INVALID · 2 = could not look (a FAIL, never a pass). `snapshot-validate.py --newest-valid --fleet` accepts only `lams|cc` and would select the other producers' files, so do NOT use `--newest-valid` for this task's names. Instead list `HIST\*.ahm-cc.json` (or `*.ahm-lams.json`) newest-first, skip today's date and any `.dryrun.`, and run `--path` on each until one exits 0. Report every skipped file by name with its verbatim finding as a data-quality flag. Never substitute silently.
   **Bootstrap (no prior `.ahm-*` file yet, i.e. the first CC run):** seed the CC baseline from the newest valid `HIST\*.cc.json` (`snapshot-validate.py --dir "HIST" --fleet cc --newest-valid`) and the LAMS baseline from the newest valid `HIST\*.lams.json` (`--fleet lams --newest-valid`), read-only, and say in the report that the baseline was seeded from the sibling producers' files. If no seed validates, write today's snapshots and skip the diff for that fleet.
4. A `[ADVISORY] ROSTER-DELTA` line is the diff signal, not a defect: carry it into the report. `COUNT-MISMATCH-LARGE`, `PARSE-FAIL`, `ROW-NO-SCHEDULE` are real and disqualify that file as a baseline.
5. Diff by (fleet, taskId): enabled→disabled = REGRESSION (⚠️, unless Step L, a ratified pause in Step 0.5d, or a `RATIFIED` event_log line explains it); present→absent = DELETION (⚠️ unless a `RATIFIED` event_log line or `retire-pending.json` names it); new = informational; disabled→enabled on LAMS = Step L.4(b).
6. **Write today's two files in ONE write call each** (never chunk; if you must chunk, the first chunk must not contain the closing `]`/`}`). Overwrite if they exist. Then validate each from disk with `--path ... --expect-count`. On non-zero: rewrite once and re-validate; if it still fails keep the file and flag `SNAPSHOT-WRITE-INVALID` with the validator's text verbatim in the report and the chat summary.
7. Retention: keep the last 30 files per suffix; move older ones to `HIST\_archive\` (move, never delete).

## Step 0.03 — Multi-day outage headline

Compute ONCE. `lastConfirmedActivityUtc` = newest `lastRunAt` across ENABLED CC tasks whose cron fires at least daily (today: `ora-am-brief`, `ora-cowork-heartbeat`, `ora-pr-land-watch`), excluding this run's own dispatch. Cross-check against the newest `HIST` snapshot file dates. If `now − lastConfirmedActivityUtc > 24h` → `MULTI-DAY-OUTAGE-DETECTED`: one headline sentence naming the offline span, rendered as line 1 of the Notion page and of the chat summary. Every later step cites it by reference instead of re-deriving it. LAMS `lastRunAt` values are excluded from this computation (Step L).

## Step 0.08 — Dispatcher-throttle check (CC/MCP)

Run once: `PY "C:/Users/Owner/.claude/maintenance/dispatch-skip-probe.py" --window-hours 168 --json-out "C:/Users/Owner/.claude/maintenance/_state/dispatch-skip.json"` (168h = one weekly cycle).
- Exit 0 = no open DISPATCH-THROTTLED · 1 = at least one `[ACTION]` · 2 = could not look OR a dead confirmation leg. Read the header's `log_scan=` verdict: `ok` · `STALE-LOCATION` (logs moved; the module names the live path, so this is not a dead app) · `FROZEN` (every known location stale) · `BEHIND` · `MISSING` · `UNESTABLISHED`. A non-`ok` verdict: every row is still printed (`recordedSkips` is registry state); mark every log-derived line `[unverifiable]`, fall back to registry evidence (`recordedSkips`, `lastRunAt`, fleet-status.py), and read `SUMMARY open=N` for the real count. Never report the fleet clean on log silence.
- Read `ora-health-guard` A.0d's `log_liveness:` line in the Connector Pre-Flight beacon first; do not re-derive a verdict it already gives.
- Per throttled taskId: `DISPATCH-THROTTLED` (ℹ️). A later `Spawning new session` / `Confirmed task run` line for that id → `THROTTLED-THEN-RECOVERED` (ℹ️, not open). A recovery seen only as `lastRunAt` is `dispatch_confirmed_only`: route it to `phantom-dispatch-probe.py`, never read it as clean.
- A skip younger than ~90s at read time → `PROVISIONAL — re-evaluate next run`, Notion only, out of the email.
- **DRAIN PROVISIONALITY (binds every step).** While a drain is in progress — Step 0.03 declared an outage, or the probe shows a skip inside the last 90s — any beacon-derived NEGATIVE (the evidence is an absence: missing page, stale timestamp, unadvanced `lastRunAt`, empty Sent Items search) is `PROVISIONAL`, Notion only, out of the email. Positives and non-beacon findings (registry drop, parse failure, explicit error string) keep full severity. Ordering corollary: before recording a beacon negative, check the producer's own `lastRunAt` against its slot; if the producer has not run since its slot passed, the reader is ahead of the writer and the negative carries no information.
- Report the open count and the PROVISIONAL count separately. Same taskId DISPATCH-THROTTLED on 2 consecutive runs with no fresh output → escalate to `orphaned-task-forensics`. The `global_limit`/`per_task_limit` caps are dispatcher-internal with no user config (investigated 2026-08-11); do not search for one. Remedies are only staggering crons or a product-side change.

## Step 0.5 — Per-task expected-fire window (CC; plus any enabled LAMS task)

**Weekly-run rule.** Under the fleet once-a-week cap (Gabriel 2026-09-17/09-22) this task runs Mondays. "Since the last run" = the past 7 days. A beacon "due on day X" means its most recent due occurrence within the past 7 days. Daily freshness thresholds apply only to producers that are still daily or faster (`ora-am-brief`, `ora-cowork-heartbeat`, the Windows dead-man/heartbeat chain); every weekly producer gets **192h**.

For each enabled cron task compute the most recent `expectedFireTime` from `cronExpression` in America/New_York (EDT = UTC−4 from the second Sunday of March; EST = UTC−5 from the first Sunday of November; handle DOM+month conjunctive crons such as `40 10 5 1,4,6,9 *` explicitly). Classify `lastRunAt`:

| Class | Rule | Verdict |
|---|---|---|
| MISSED | `lastRunAt < expectedFireTime − 30 min` | ⚠️ |
| OUT-OF-WINDOW | `lastRunAt` not within ±60 min of any cron fire time in the past 7 days | ⚠️ |
| ALERT-LATE | `lastRunAt > expectedFireTime + 120 min` | ⚠️ |
| WARN-LATE | `+60 < delta ≤ +120 min` | ℹ️ |
| VERIFIED | `−30 ≤ delta ≤ +60 min` | ✅ |

`jitterSeconds` is part of the scheduled time, not lateness. Null `lastRunAt` with an elapsed slot: read the task's SKILL.md mtime at its registry `path`; mtime after the slot → `NOT-YET-DUE-POST-CREATION` (✅), else `SILENT-NEVER-FIRED` (⚠️). One-time tasks follow the skill's Step 1.25 (`enabled:false` + `lastRunAt` set = normal completion).

**Suppression order.** A raw finding must survive all of these, in this order, to reach ⚠️ or the email: **Step L** (LAMS-DARK) → **0.5d** (PAUSED-SLOT) → **0.5c** (HOST-UNAVAILABLE) → **0.5b** (HISTORICAL).

### 0.5d — PAUSED-SLOT
Only with a RATIFIED bounded pause, evidenced by (in order): a FleetPause restore ledger `maintenance/_state/YYYY-MM-DD_FleetPause_RestoreLedger_*.json`; a registered resume task (`ora-routine-pause-resume-*` / `ora-lams-routine-resume-*`, whose `fireAt` is the window end); or a pause instruction in `ops_decision_log.md`/`event_log.md`. A bare `enabled:false` is never enough. Suppress (ℹ️ `PAUSED-SLOT`) only when the slot is inside the window AND the task is on the pause roster. Teeth: a slot after the window end is never suppressed; a disable not covered by a ratified pause stays a Step 0 REGRESSION; a task still disabled after its window closed is `RESUME-INCOMPLETE` (⚠️) — the 2026-09-28 stalled resume left CC tasks in exactly this state, and those Gabriel deferred or held OFF on 2026-10-30 are named in that day's `event_log.md` "Stalled-resume triage" entry: report those ids as one ℹ️ line citing it, not as ⚠️. Report one grouped incident, and for each suppressed task one line on whether its missed output is made up next slot or is a period-bounded **content gap** (ℹ️, addressed to Gabriel).

### 0.5c — HOST-UNAVAILABLE
Unless Step 0.03 fired, establish `hostAvailableAt` (earliest confirmed dispatch of that day) from, in order: `ora-health-guard` A.0's wake-lateness alert, the Connector Pre-Flight beacon's `wake_cause`, or one run of `PY "C:/Users/Owner/.claude/maintenance/host-availability-report.py"`. A slot before `hostAvailableAt` whose `lastRunAt` is within 60 min after it → `HOST-UNAVAILABLE` (ℹ️, never emailed). More than 60 min after, or a slot that fell while the host was already up, keeps full severity. Report one grouped line. Retiming crons to dodge this was rejected 2026-08-14; do not propose it.

### 0.5b — HISTORICAL (weekly+ cadence only)
Run ONE `notion-search` for `Automation Health` scoped to `OPSHUB` (page_size 10, max_highlight_length 0). A weekly+ task's lateness finding is `HISTORICAL` (ℹ️, `carried forward, first reported YYYY-MM-DD`) when a prior page dated after that task's `lastRunAt` exists and its next slot has not arrived. State the basis without overclaiming ("a covering search confirmed dated pages exist; bodies not re-read"). Fetch one page only when its date is within ±1 slot and ambiguous. A newer missed slot is always fresh. On search failure use the unsuppressed verdict and say so. Pages written by the LAMS-era monitor under the same title count as prior reports.

## Step 0.55 — Producer-consumer beacon check

**ORPHANED-BEACON (run first).** Every producer below must be present AND enabled in the CC registry. A producer absent or disabled on CC, not explained by Step L, retire-pending.json or a 2026-10-30 hold, is `ORPHANED-BEACON` (⚠️, never skipped). A producer that is disabled by a recorded Gabriel deferral/hold → one ℹ️ line citing the record, and its beacon is not checked.

| Producer (block) | Beacon | Freshness / due |
|---|---|---|
| `ora-am-brief` Block A (rate) | Notion `Rate Snapshot — Current` `35e6ecd8-9e59-814f-ae22-fe99464084d1` | `prefetch_status` OK/SOURCE_DEGRADED and `fetched_at` = most recent weekday. Weekdays only. |
| `ora-am-brief` Block B (brief) | Ops Hub child `Daily Brief — YYYY-MM-DD` | Exists for the most recent day, not title-prefixed `🗑️`/`[DUPLICATE]`/`⚠️ [EMAIL FAILED]`. Daily. |
| `ora-am-brief` Block C (inbox) | Notion `Inbox Pre-Brief — YYYY-MM-DD` + `Claude_Workspace/_state/inbox-pre-brief-heartbeat.log` | Page exists for the most recent weekday and the log line has a terminal status (not stuck `ENTERED`). Weekdays only. |
| `ora-am-brief` Block D (cash) | Notion `Cash Position Snapshot — YYYY-MM-DD` | Exists. Mondays only. |
| `ora-health-guard` Block B (preflight) | PRIMARY Notion `3a56ecd8-9e59-8152-83b6-c61cec736f2b` (`last_run_et`, `status`, `failed_connectors`, `log_liveness`); backup Sent Items `✅`/`⚠️ ORA Connector Pre-Flight — <date>` | Updated on its most recent Monday slot (05:15 ET). |
| `ora-health-guard` Block A.0 (wake-lateness alert) | Email `🌙 Overnight machine-offline detected — …` | Not checked. If it and a same-day AM-cluster lateness finding coexist, they are ONE incident. |
| `ora-cowork-heartbeat` (CC twin) | Notion `35c6ecd8-9e59-81d5-8d2c-d08002458b78` — fetch by ID, never title-search | `last_edited_time` within 16h of its most recent 05:50 slot. |
| `ora-task-integrity-guard` | silent-on-healthy | `lastRunAt` within 8 days after its Mon 07:05 slot. **A2 beacon — ALARM ⚠️:** `~/.claude/maintenance/_state/registry-membership.log` newest line > 192h old, or `_state/fleet-heartbeat.json` `ts` > 48h old. |
| `ora-broker-touch-cadence` | Ops Hub STEP 5 completion row | Due on the 2nd of the month only (`40 13 2 * *`). |
| `ora-appsec-sweep` | Ops Hub completion row with both pinned repo SHAs (ora-pm + oxford-command-center) | Due Wednesdays only (`30 13 * * 3`). |

Retired from the v1.29 table at the port (do not check, do not flag): `ora-pm-ledger` Blocks A/C (CC task disabled; 2026-10-30 Gabriel deferral); `ora-underwrite-doctrine-staleness-check` and `ora-monday-sync` (LAMS-dark, Step L); `ora-health-guard-fail-aging-nudge` (retired 2026-09-22); `ora-setup-audit` (retired 2026-07-07). Re-add a row only when its producer is live on CC.

**Branching-awareness:** a beacon expected-skipped on a day its block does not run is not a finding. For each producer with a fresh `lastRunAt`, open its due beacons (one tool call each; on a tool failure log it and continue). Fresh run + stale/missing/duplicated due beacon → `PRODUCER-STALE-OUTPUT` (⚠️). **DRAIN GATE:** Step 0.08's drain provisionality binds every row.

## Step 0.55a — Notion publishing degraded → email-only

Apply before finalizing any missing-Notion-page finding from Steps 0.55, 0.56 or 0.9(b). Runs after the drain gate and Steps L / 0.5d / 0.5c; acts only on a finding they left standing. The rule block below is shared text and stays byte-identical across consumers. **Port note:** this task's own roster entry in the state file is still keyed `task_id: "automation-health-monitor"`, `fleet: "lams"`; treat that entry as covering this task until the roster is re-keyed.

> **NOTION-PUBLISH-DEGRADED → EMAIL-ONLY RULE (shared text, byte-identical in every consuming health check; OI-281 / OI-288).**
> State file, the single source of truth: `C:\Users\Owner\.claude\maintenance\_state\notion-publish-degraded.json`.
> 1. **Read the state file before judging any missing Notion output page.** Fail safe: if the file is missing or unreadable, is not valid JSON, or `active` is anything other than JSON `true`, this rule does not apply. Judge the missing page exactly as the rest of this file already says.
> 2. **Downgrade only.** This rule only ever softens a missing-page finding that the surrounding checks already raise without it. It never introduces a FAIL, STALE or [ACTION] that would exist only because the flag is active. The one deliberate exception is the flag-age review line in item 6.
> 3. **Delivery proof, not run proof.** When `active` is `true` and the producer is in `producers[]` (match `task_id`, and `notion_output` when a task has several entries), a missing Notion output page counts as delivered only if ONE `[OK] Sent` line in `C:\Users\Owner\.claude\scheduled-tasks\_shared\send-log.txt` satisfies all four conditions:
>    - its normalized subject matches `fallback_email_subject_pattern` (normalization, placeholders and undated subjects per the file's `matching` block);
>    - its normalized subject does NOT match `must_not_match`;
>    - its `bytes=` value is at least `min_bytes`;
>    - its send date is the expected date. Convert the logged ISO offset to ET first: the log carries `-04:00` and `+02:00` lines.
>
>    Outlook Sent Items may corroborate a line but never substitutes for one. The send-log is the only source that records body size.
>    - **All four hold** → report `EMAIL-ONLY (Notion degraded, OI-288) — <task_id>: <notion_output> for <date> delivered by email "<matched subject>" (<bytes> bytes)` as an Advisory row. It does NOT count toward FAIL/N, does NOT flip any subject to [ACTION], and does NOT enter any FAIL-aging ladder.
>    - **Pattern matches, but the line hits `must_not_match` or has `bytes` below `min_bytes`** → report `fallback notice without report body — <task_id>: "<subject>" (<bytes> bytes, min_bytes <min_bytes>)` and escalate the missing page exactly as before.
>    - **No matching line, or the pattern is `null`** → the producer did not deliver. Escalate exactly as before.
>    - **Could not look** (send-log unreadable) → escalate exactly as before. Never assume the email exists.
> 4. **Never cite "search-index lag"** as the cause of a missing page while `active` is `true`. The cause is the block quota. Say so.
> 5. **Never edit or clear the state file from a health check.** Clearing is a human or interactive-session action, per its `clear_when`.
> 6. **Flag-age review line.** On every run while `active` is `true`, emit the Advisory row `notion-publish-degraded flag active <N> days (since <since>, review_by <review_by>)`. N is today minus `since` in ET calendar days. Once today (ET) is later than `review_by`, emit the same line as a FAIL-level finding instead: it counts toward FAIL/N and flips the subject to [ACTION], so a human must re-confirm or clear the flag. A missing or unparseable `review_by` counts as passed. The flag-age line is excluded from FAIL-aging tracking, like the EMAIL-ONLY row: no FAIL-aging tracker (e.g. `ora-health-guard-fail-aging-nudge`) may age it as a stale probe FAIL.

Reporting: EMAIL-ONLY rows go in their own `## Notion degraded — email-only deliveries` subsection (✅-equivalent, never ⚠️, never emailed). A `fallback notice without report body` row, a null pattern, or no qualifying line is ⚠️ as before. The flag-age line is ℹ️ until `review_by`, ⚠️ after. Quote the state file's `dark_producers` list once.

## Step 0.56 — Declared `output_contract:` check

Strictly additive to Step 0.55; verdicts are independent and never merged. Enumerate contract-bearing tasks by reading the `output_contract:` frontmatter key from each ENABLED CC task's SKILL.md at its registry `path` (LAMS tasks: only if enabled, per Step L). Apply Step 0.55's ORPHANED-BEACON rule first. Per declared block, in order: evaluate `expected_on` with Step 0.5's cron walk (`cron`, `always: true`, or partial fields like `days_of_week` with the same branching-awareness); skip blocks not due; resolve the artifact with one call (`notion_page` by `page_id` → `notion-fetch` + `last_edited_time`; by `title_pattern` + `parent_id` → child search with `{DATE}` substituted; `sent_mail` → mailbox search for `subject_pattern` to `recipient`; `outlook_draft` → folder search; `file`/`path_pattern` → existence + mtime via Bash) within `freshness_window_hours`. Severity = the block's own `on_missing_severity` (no CC downgrade any more). Honor a declared `skip_condition:` by checking for its no-op/guard-exit signal before flagging. Report in a separate Contract-freshness column.

## Step 0.57 — BLOCKED-AWAITING-GABRIEL

Scope: only tasks whose current-window artifact Step 0.55 or 0.56 already fetched (zero new artifact fetches); any other task is `HOLD-CHECK-NOT-RUN`, never clean. Flag only when the SAME artifact carries BOTH (a) a WITHHELD-WORK marker — `HELD`, `held pending`, `was held`, `pending your confirmation`, `awaiting your confirmation`, or a `SKIPPED` causally tied to a hold (a bare `SKIPPED`/`0 results` is a healthy no-op) — AND (b) an ask (`QUESTIONS FOR GABRIEL` or equivalent). A `QUESTIONS FOR GABRIEL` section alone is routine and is NOT a finding. (a) with no ask → `HELD-NO-ASK` (⚠️). When both match, ONE lookback search on the same channel (latest 6 occurrences) counts consecutive runs carrying marker (a) on the same blocking subject: 1 → ℹ️ Notion only; 2+ → ⚠️ `BLOCKED-AWAITING-GABRIEL`, in the alert, with the count, cadence, elapsed span in cadence units, and the ask's first ~2 lines quoted verbatim. Step 0.5b never suppresses this; it gets louder with repetition. Report only: never answer or carry forward a decision. Drain gate applies.

## Step 0.9 — Ops Hub cross-reference

For each enabled task with a Notion-output side effect, search `OPSHUB` for its expected child-page title in the window. Flag: (a) `lastRunAt` older than `expectedFireTime − 30 min`, (b) no Notion output page in the window (subject to Step 0.55a), (d) a Step 0 regression, (e) Step 0.55 producer-stale-output, (f) Step 0.5 WARN-LATE/ALERT-LATE. (The v1.29 inbox-sweep checks — Step 0.75 and item (c) — are permanently retired: spend zero calls.)

## Step 0.95 — Duplicate-title detection + supersedes cross-link

After Step 0.9, `notion-search` the literal title `Automation Health — <RUN_DATE date>`. If ≥2 pages: log `DUPLICATE-TITLE-COLLISION` (ℹ️); determine the EARLIER page by its own body evidence or `created_time`; do not create a third page; append a `⤵ SUPERSEDED` line to the earlier page and a `⤴ SUPERSEDES` line under the Summary of the later one. Non-blocking: on failure log and continue.

## Step 1 — Notion publication (with publication-success guard)

Create one page under `OPSHUB` titled `Automation Health — <RUN_DATE date>` containing, in order:
- The Step 0.03 headline, if any (line 1).
- `Surface: CC/MCP (ora-automation-health-monitor v2.0, port of LAMS v1.29) · base skill vX.Y` and the liveness-assertion verdict.
- Summary line: `[V] verified | [W] warn-late | [F] flagged | [H] host-unavailable | [PS] paused-slot | [LD] lams-dark | [P] producer-stale | [M] model-stale/untagged | [R] registry regressions | window [UTC start → UTC end]`
- `LAMS-DARK` grouped line + `LAMS-dark producers without a CC successor` line (Step L).
- HOST-UNAVAILABLE and PAUSED-SLOT grouped lines (with stranded-output lines and any RESUME-INCOMPLETE separately).
- Per-task status (✅/ℹ️/⚠️/❌) in two sections: **CC/MCP fleet (registry-confirmed)** with a lateness column (`lastRunAt − expectedFireTime`, minutes), a beacon-freshness column and a contract-freshness column; **LAMS/Cowork fleet (fleet-status.py, read-only)** listing only enabled LAMS tasks and Step L.4 findings.
- Model-currency (the skill's Step 1.5, both fleets; LAMS-dark tasks excluded).
- Dispatcher-throttle subsection (open vs PROVISIONAL counts, `log_scan` verdict).
- Off-fleet substrates subsection (the skill's Step 1.75 results; any `[unverifiable]` leg named).
- BLOCKED-AWAITING-GABRIEL / HELD-NO-ASK / HOLD-CHECK-NOT-RUN.
- Registry diff (both fleets; baseline file names and any skipped baseline with its finding; `SNAPSHOT-WRITE-INVALID` if raised).
- QUESTIONS FOR GABRIEL (only if any) · Actions taken · audit window (UTC).

While `notion-publish-degraded.json` has `active: true`: attempt the create anyway; if it succeeds and verifies, add the Advisory row `Notion create succeeded — notion-publish-degraded.json may be clearable` (never edit the flag); if it fails, Step 3's email must carry the full report (a bare notice under 5,000 bytes fails the roster's `min_bytes`).

**Publication-success guard.** Capture `pages[0].id` and `url` from `notion-create-pages`. If the response has no page ID: first look for the page (recovery) — `notion-fetch` `OPSHUB` for an exact-title child, then `notion-search` the exact title (search lags; a miss alone is not proof). A match created at/after the call is this run's page: use it, do not retry. After a grace/quota notice with no match, do not retry: the create is UNVERIFIED → Step 3. Otherwise retry ONCE with the same content; never blind-retry. Quota errors → the `notion-quota-fallback` skill. Verify by `notion-fetch` of the returned ID (never `notion-search`): title matches and the ancestor path includes `OPSHUB`. Any failure → Step 3.

## Step 2 — Alert email (only when a finding survives suppression)

If any ⚠️/❌ survives (including off-fleet ⚠️/❌ such as `ACTIONS-BILLING-BLOCKED`, `OFF-FLEET-DISAPPEARED`, `BACKUP-FAILED`, `OFF-FLEET-STEP-NOT-LOADED`, and `LAMS-RESUMED-AGAINST-RULING`), send via `SEND` with subject `⚠️ ORA Automation Alert — <flagged class/task list> — <RUN_DATE date>`. Body: each flagged item with its class, and the Notion page link. ℹ️-only runs (model-currency, LAMS-DARK, throttle, HISTORICAL, HOST-UNAVAILABLE, PAUSED-SLOT, PROVISIONAL, OFF-FLEET-UNTRACKED) send nothing. Pre-authorized internal send under the routing canon.
**Cross-producer dedup:** before composing, one `outlook_email_search` of Sent Items for the run date against `🌙 Overnight machine-offline detected` and `[ORA Command Center] Mirror deploy`. On a same-day match add one body line naming that alert as the same root cause; still send.
**Confirm, do not assume:** after sending, search Sent Items for the subject and state in the chat summary whether delivery was independently confirmed; also confirm the `[OK] Sent` line in `C:\Users\Owner\.claude\scheduled-tasks\_shared\send-log.txt`.

## Step 3 — Publication-failure email (only if Step 1 failed after its one retry)

AUTO-SEND via `SEND`: subject `❌ ora-automation-health-monitor PUBLICATION FAILED — <RUN_DATE date>`; body = the full report (summary + per-task verdicts, ≥5,000 bytes), the Notion error, and the parent-ID verification result, tagged `AUTO-SENT — meta-failure path, no human-in-loop available`. This subject matches the degraded-flag roster's fallback pattern for this task.

## Step 4 — Chat summary (5–10 lines)

Line 1: the Step 0.03 headline if any, else the publication path (`Notion ✅` / `Notion ❌ → fallback email ✅/❌`). Then: verified/warn-late/flagged counts for CC; LAMS-DARK count + producers-without-successor count; HOST-UNAVAILABLE and PAUSED-SLOT lines (stated as NOT fleet defects; stranded outputs and RESUME-INCOMPLETE on their own line); top 3 latency outliers excluding HOST-UNAVAILABLE; producer-stale and contract-freshness flags; BLOCKED-AWAITING-GABRIEL (above the hygiene lines) with HOLD-CHECK-NOT-RUN count; model-currency count; throttle open/PROVISIONAL counts; off-fleet line (skill version, markers, findings, or `off-fleet: NOT CHECKED`); registry diff (deletions/regressions only) with both snapshot file names and validator verdicts; alert-email status and whether delivery was confirmed.

## Operational notes

- DST: all expected-fire computation is anchored to America/New_York.
- Run-artifact retention: keep `_runs/<date>/` for 30 days, then move it to `_runs/_archive/` (never delete).
- Spec changes follow `register-scheduled-task` § Editing a task's SKILL.md CONTENT; back up this file to `_skill-versions/SKILL.vX.Y-YYYY-MM-DD-<reason>.md` before any edit.

*Changelog: v2.0 (2026-10-30, Gabriel-directed, supervised) — ported from LAMS `automation-health-monitor` v1.29 to the CC/MCP fleet. Kept: every v1.29 rule. Changed: base skill liveness assertion now also covers a non-loadable skill; CC tasks are registry-confirmed (the `[CC/MCP]` downgrade and the Step 0.06 filesystem proxy are gone); LAMS is read via `fleet-status.py --json`, read-only; new Step L makes the ratified LAMS dark state expected silence with three teeth; snapshots renamed `.ahm-cc.json` / `.ahm-lams.json` so they collide with neither `ora-task-integrity-guard`'s `.cc.json` nor the frozen `.lams.json`, with a bootstrap from those files on the first run; Step 0.07 model-currency delegated to the skill's Step 1.5 (both fleets); throttle window widened to 168h for the weekly cadence; the Step 0.55 table re-based on live CC producers (pm-ledger, underwrite-doctrine-staleness-check, monday-sync, fail-aging-nudge rows dropped); alert subject `Cowork Automation Alert` → `ORA Automation Alert`; Step 0.75 removed (retired since 2026-06-10). Incident narratives and the v1.1–v1.29 changelog stay in the LAMS v1.29 file.*