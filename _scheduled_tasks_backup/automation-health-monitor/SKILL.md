---
name: automation-health-monitor
description: ORA automation fleet health check — weekdays 11:00 AM. v1.14 (2026-07-22): Step 0.55 `ora-health-guard` Block B row now PRIMARY-checks a new Notion beacon (`3a56ecd8-9e59-8152-83b6-c61cec736f2b`) instead of relying solely on an Outlook Sent Items search; added an informational row for `ora-health-guard`'s new Block A.0 wake-lateness immediate alert. Gabriel-directed workflow-optimization follow-up, additive only. v1.13 (2026-07-21): added `ora-monday-sync` [LAMS/Cowork] to the Step 0.55 producer-consumer table (Notion Ops Hub page `Monday Sync — YYYY-MM-DD` + Outlook Sent Items check, due Mondays only, cron `35 10 * * 1`; motivated by a 2026-07-20 fire that updated lastRunAt with no completed page/send — see Step 0.55 table row for the full incident note; additive table row only, Step 0.5/Step 0.56 logic untouched). v1.12 (2026-07-20): added `ora-appsec-sweep` [CC/MCP] to the Step 0.55 producer-consumer table (Notion Ops Hub completion row, due weekly on Wednesdays only, cron `30 13 * * 3`; first fire 2026-07-22; additive table row only, Step 0.5/0.56 logic untouched). v1.11 (2026-07-20): added `ora-underwrite-doctrine-staleness-check` [LAMS/Cowork] to the Step 0.55 producer-consumer table (Notion Ops Hub status post, due weekly on Wednesdays only; additive table row only, Step 0.5/0.56 logic untouched). v1.10 (2026-07-18): NEW Step 0.56 — additive check of per-task declared `output_contract:` frontmatter blocks (Plan 2 retrofit), reusing Step 0.5's expectedFireTime logic and Step 0.55's [CC/MCP] downgrade + ORPHANED-BEACON rules unchanged; new Contract-freshness column (Step 1) and summary line (Step 4); Step 0.55's table/rules untouched. v1.9 (2026-07-16): Step 0.55 producer-consumer table — added `ora-broker-touch-cadence` [CC/MCP] row (Notion Ops Hub completion posting, due monthly on the 2nd only; owed by the registering subagent). v1.8 (2026-07-16): Step 0.55 A2 freshness beacon — hard ⚠️ ALARM if registry-membership.log or fleet-heartbeat.json is >48h stale (the ora-task-integrity-guard STEP-1.5 pulse chain sat dark 07-09→07-16 with zero alarms; this beacon closes that class); guard row de-ambiguated (LAMS twin permanently retired). v1.7 (2026-07-15): fixed a Step 0 snapshot-filename collision with ora-task-integrity-guard's Step 0.5 (both wrote the bare _state-history\YYYY-MM-DD.json, clobbering each other and breaking membership-guard.ps1's LAMS fold-in) — this producer now writes/reads .lams.json exclusively. On top of v1.6 (2026-07-08): Step 0.07 model-currency self-check against reference_scheduled_task_model_standard.md, on top of v1.5 (ORPHANED-BEACON rule, producer-consumer beacons, dual-bounded lateness, publication-success guard, corrected LAMS fleet-scope). [MODEL: claude-sonnet-5 | set 2026-07-08]
---

PROMOTION NOTE (2026-07-08): This replaces the thin "rebuilt 2026-07-05" stub. Content is the orphaned v1.5 spec (previously at `ora-automation-health-monitor\SKILL.md`, now archived) with corrections: Step 0.06 was originally written assuming this task runs on the CC/MCP surface — fixed 2026-07-08 (it runs on LAMS/Cowork). Step 0.07 (model-currency check) is NEW as of 2026-07-08 (same day, second pass). Everything else is v1.5 verbatim. Hardcoded Notion page IDs have NOT been independently re-verified as part of this promotion — treat any Notion-fetch failure on those IDs as a signal to confirm the ID before assuming the page was deleted.

**[MCP ROUTING — normalized 2026-06-03]** Outlook email: `C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1` — the SOLE automated send path (Composio removed 2026-06-11; no fallback connector exists; on a non-zero COM exit retry once, then flag — do not halt). **KNOWN ISSUE (flagged 2026-07-08): search the Inbox/Sent Items for self-to-self ggoldberg@oxfordra.net automated-task emails before trusting this path — as of 2026-07-08 no such email was found since 2026-07-01 despite multiple tasks firing in that window (see ora-health-guard's 2026-07-08 OUTLOOK-COM-SEND-BROKEN alert, an Outlook-COM hang, exit 4). If this recurs, treat Step 2/3 sends below as unconfirmed and say so in the chat summary.** HubSpot: native `mcp__a3e380ce-…__*`. Notion: native `mcp__c5f4869f-…__notion-*`. QuickBooks: Desktop only (no live MCP). The prior `8a611864` Composio wrapper is no longer connected; Rube `d6315173` is retired — never reference either. ORA does not use Google Workspace.

Run the automation-health-monitor skill. Verify all Cowork scheduled tasks ran as expected.

---

## Step 0 — Registry-state diff

**FILENAME FIX (2026-07-15):** this producer and `ora-task-integrity-guard` (CC/MCP fleet) Step 0.5 were both instructed to write their own fleet's snapshot to the identical bare filename `_state-history\YYYY-MM-DD.json` — whichever ran later in the day clobbered the other's data, which also broke `membership-guard.ps1`'s fold-in of the LAMS baseline (it reads this producer's file believing it to be LAMS data). Fixed by giving this LAMS producer its own suffixed filename, `.lams.json`, permanently — never write the bare `YYYY-MM-DD.json` name again. `ora-task-integrity-guard`'s SKILL.md Step 0.5 was corrected in parallel to write `.cc.json`, and `membership-guard.ps1`'s read filter was updated to look for `.lams.json` specifically.

1. Load the live registry via `mcp__scheduled-tasks__list_scheduled_tasks`.
2. Load yesterday's snapshot from `C:\Users\Owner\OneDrive - Oxford Capital Partners\Documents\Claude\Scheduled\_state-history\YYYY-MM-DD.lams.json`. If not present, generate today's snapshot and skip diff (first run after this enhancement).
3. Diff today vs yesterday by `taskId`. Flag any of:
   - Task previously `enabled=true` and now `enabled=false` (accidental disable).
   - Task previously present and now absent (deletion).
   - Task newly present (creation, low-severity informational).
4. Persist today's snapshot to `_state-history\YYYY-MM-DD.lams.json` (overwrite if exists — never the bare `YYYY-MM-DD.json` name, see FILENAME FIX above).

## Step 0.06 — Dual-fleet (LAMS/CC-MCP) registry audit (CORRECTED 2026-07-08 for the surface this task runs on)

`mcp__scheduled-tasks__list_scheduled_tasks` in THIS runtime (Cowork) returns the **LAMS/Cowork fleet** — that IS "this fleet" for Step 0's diff, and it is already fully covered there. It is backed by `C:\Users\Owner\AppData\Roaming\Claude\local-agent-mode-sessions\a6ad2c61-c3c8-4a48-98a5-e40c1db22ad3\583f08bc-0123-4111-8158-8fe3d927e350\scheduled-tasks.json` (the `AppData\Local\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Roaming\...` path is the SAME file via MSIX virtualization — never count it twice, and never re-read this JSON directly in this step; Step 0 already has this data via the tool call).

The genuinely **separate** fleet is **CC/MCP**, which this Cowork runtime cannot query via any tool call — there is no `list_scheduled_tasks`-equivalent for it here.

1. Enumerate CC/MCP tasks via Desktop Commander `list_directory` on `C:\Users\Owner\.claude\scheduled-tasks\` (depth 1). Each subdirectory except `_archive_*` and `_shared` is a CC/MCP task folder.
2. For each, read the `SKILL.md` frontmatter `description` line — CC/MCP task authors have been putting live-state signals directly in that description (e.g. "Currently DISABLED pending recovery stabilization", "DEGRADED 2026-07-08"). Treat this as the best available proxy for enabled/cadence state.
3. This is a **filesystem/frontmatter proxy, not a live registry read** — it has no equivalent to `enabled`, `cronExpression`, or `lastRunAt` fields. Where a dated `last-run.json` or other dated run-artifact exists in the task's folder, use its date as a `lastRunAt` proxy; otherwise classify the task `CC-FLEET-STATE-UNVERIFIED` (ℹ️) rather than guessing MISSED/VERIFIED.
4. Flag any CC/MCP folder with no dated run-artifact AND no recent frontmatter update as a candidate for the ORPHANED-BEACON check in Step 0.55.
5. Report CC/MCP findings in Step 1 under a separate **CC/MCP fleet (filesystem-derived, not registry-confirmed)** subsection — do not merge its verdicts with the LAMS fleet's registry-confirmed verdicts.

## Step 0.07 — Model-currency self-check (NEW 2026-07-08)

**Purpose:** scheduled tasks bind to whatever model created/recreated them, permanently, with no auto-upgrade path (confirmed 2026-07-08 — see event_log.md same date). This step detects drift from the firm's current standard so it surfaces on the next health-check run instead of requiring manual rediscovery.

1. Read `C:\Users\Owner\.claude\projects\C--Users-Owner-OneDrive---Oxford-Capital-Partners\memory\reference_scheduled_task_model_standard.md` — extract the **Current standard** model id from its top line.
2. For each enabled LAMS task from Step 0's registry data, parse its `description` field for a trailing tag `[MODEL: <model-id> | set YYYY-MM-DD]`.
3. Classify:
   - **Tag matches current standard** → ✅ current, no report line needed.
   - **Tag present but mismatched** → `MODEL-STALE` (ℹ️ — informational, no forced action exists; recreation is a manual multi-step process per event_log.md).
   - **No tag at all** → `MODEL-UNTAGGED` (ℹ️ — likely a task created before this convention existed, or a fresh task never tagged; same informational severity).
4. Do NOT attempt to fix, retag, or recreate anything automatically in this step — report only. Retagging/recreating is a decision for Gabriel per the reference file's "To bump the standard" procedure.
5. Note in the report that the CC/MCP fleet is NOT covered by this check (per the reference file's known-gap section) — do not silently omit this caveat.

## Step 0.5 — Per-task expected-fire window (REWRITTEN v1.3)

For each enabled cron task, compute the most recent expected fire time `expectedFireTime` based on `cronExpression` interpreted in America/New_York. Walk backward from current time until the cron predicate is satisfied. Handle DST: EDT = UTC−4 from second Sunday of March; EST = UTC−5 from first Sunday of November. Handle DOM+month conjunctive crons (e.g., `0 9 1 1,4,7,10 *`) explicitly — v1.2 parser silently mishandled these.

For each enabled cron task, classify `lastRunAt` against `expectedFireTime` and the task's `jitterSeconds` budget:

| Classification | Rule | Verdict |
|---|---|---|
| **MISSED** | `lastRunAt < expectedFireTime − 30 min` | ⚠️ flag |
| **OUT-OF-WINDOW** | `lastRunAt` does NOT fall within ±60 min of ANY cron-predicate fire time in the past 7 days | ⚠️ flag (anomalous fire timing — catch-up after a missed cycle) |
| **ALERT-LATE** | `lastRunAt > expectedFireTime + 120 min` | ⚠️ flag (excessive lateness) |
| **WARN-LATE** | `expectedFireTime + 60 min < lastRunAt ≤ expectedFireTime + 120 min` | ℹ️ note (excessive lateness, no alert) |
| **VERIFIED** | `expectedFireTime − 30 min ≤ lastRunAt ≤ expectedFireTime + 60 min` | ✅ verified |

**Rationale:** v1.2's one-sided rule `Flag if lastRunAt < expectedFireTime − 30 min` caught missed fires but silently passed excessively-late fires. The 2026-05-14 deep audit revealed multiple tasks 3–5 hours late on 5/13 AND 5/14 (chronic AM dispatcher latency), and `ora-outbox-qc-sweep` firing 16.5 h outside its cron window — all silently passed by v1.2.

**OUT-OF-WINDOW detection algorithm:** generate the last 7 days of cron-predicate fire times (e.g., for `30 17 * * 1-5`: Mon-Fri 21:30 UTC); flag if `lastRunAt` is more than 60 min from the nearest of those.

## Step 0.55 — Producer-consumer beacon check (NEW v1.3)

Several scheduled tasks are *producers* whose downstream consumers depend on a beacon file or Notion page. The task can fire with fresh `lastRunAt` but produce stale/empty output — invisible to v1.2.

**Fleet-membership note (added 2026-07-08):** rows marked **[CC/MCP]** below can only be membership-checked via the Step 0.06 filesystem proxy (no live `enabled`/`lastRunAt`). If a [CC/MCP] producer's beacon is stale/missing, classify PRODUCER-STALE-OUTPUT as ℹ️ informational rather than ⚠️ unless Step 0.06 also shows a dated run-artifact confirming the producer actually fired.

Known producer-consumer chains (**updated 2026-06-03 for the Phase-3 Stage-2 merged fleet** — the former standalone producers `ora-treasury-yield-prefetch` / `ora-inbox-pre-brief` / `ora-daily-brief-6am` / `ora-cash-position-snapshot` are now BLOCKS inside `ora-am-brief`; `ora-notion-daily-digest` / `ora-outbox-qc-sweep` / `ora-eod-action-ledger` are blocks inside `ora-pm-ledger` [CC/MCP]; `ora-connector-preflight-guard` is a block inside `ora-health-guard` [CC/MCP]. The beacons each block produces are unchanged; only the producer *task* name changed. Verify the merged task's `lastRunAt`, then check each expected block-beacon):

| Producer task (block) | Beacon path / Notion page | Freshness check |
|---|---|---|
| `ora-am-brief` (Block A — rate) | Notion `Rate Snapshot — Current` page `35e6ecd8-9e59-814f-ae22-fe99464084d1` | `prefetch_status` is `OK`/`SOURCE_DEGRADED` AND `fetched_at` is today. **Weekdays only** — skip on Sat/Sun (Block A does not run weekends). *(Legacy `Claude_Workspace/_state/treasury-yields.json` is DEPRECATED — do not check it; Notion is canonical.)* |
| `ora-am-brief` (Block B — brief) | Notion Ops Hub child page `Daily Brief — YYYY-MM-DD` | Page exists, today, AND NOT title-prefixed `🗑️`/`[DUPLICATE]`/`⚠️ [EMAIL FAILED]`. **Every day** (Block B runs 7×/wk). |
| `ora-am-brief` (Block C — inbox) | Notion `Inbox Pre-Brief — YYYY-MM-DD` + `Claude_Workspace/_state/inbox-pre-brief-heartbeat.log` | Page exists today AND heartbeat log has today's line with terminal status (not stuck `ENTERED`). **Weekdays only.** |
| `ora-am-brief` (Block D — cash) | Notion page `Cash Position Snapshot — YYYY-MM-DD` | Page exists. **Mondays only** — skip Tue–Sun. |
| `ora-pm-ledger` (Block A — digest) [CC/MCP] | Notion Daily Digest send / Ops Hub digest entry | Sent/posted today. **Every day.** |
| `ora-pm-ledger` (Block C — EOD) [CC/MCP] | Cowork artifact `ORA EOD Action Ledger` + Ops Hub activity log | Refreshed today. **Every day.** |
| `ora-health-guard` (Block B — preflight) [CC/MCP] | **PRIMARY (v1.14, 2026-07-22):** Notion page `3a56ecd8-9e59-8152-83b6-c61cec736f2b` ("🔌 Connector Pre-Flight — Status", under Ops Hub) — one `notion-fetch`, check `last_run_et` is today and `status`/`failed_connectors` for content. Secondary/backup: Outlook mirror email subject `✅`/`⚠️ ORA Connector Pre-Flight — [today]` in Sent Items. | Beacon updated today (before ~06:00 ET). **Daily.** The Notion beacon is now the primary check — added after the 2026-07-22 audit found the Sent Items search came up empty despite the block having fired, forcing an unnecessary informational downgrade; the [CC/MCP] downgrade rule still applies if BOTH the beacon and the Sent Items search miss. |
| `ora-health-guard` Block A.0 (wake-lateness alert) [CC/MCP] (v1.14, 2026-07-22) | Standalone email `🌙 Overnight machine-offline detected — ora-health-guard woke {N}min late — [today]` | Informational only, not independently checked by this step — it is itself an immediate-alert mechanism (fires the moment ora-health-guard wakes >45min late, front-running this task's own ~11:05 ET discovery of the same catch-up burst). If both this alert and a same-day ALERT-LATE/OUT-OF-WINDOW finding on `ora-health-guard` or other AM-cluster tasks appear together, treat them as ONE incident, not two. |
| `ora-cowork-heartbeat` | Notion page `35c6ecd8-9e59-81d5-8d2c-d08002458b78` (fetch by ID — NEVER title-search; duplicates exist) | `last_edited_time` within last 16 hours (matches watchdog threshold). |
| `ora-task-integrity-guard` [CC/MCP] | (silent-on-healthy — no email beacon) | `lastRunAt` today after its 12:45 ET cron (Step 0.06 proxy). **A2 FRESHNESS BEACON (v1.8, 2026-07-16 — ALARM ⚠️, never ℹ️, overriding the [CC/MCP] downgrade note):** flag if `~/.claude/maintenance/_state/registry-membership.log`'s newest line is **> 48h old**, or `~/.claude/maintenance/_state/fleet-heartbeat.json`'s `ts` field is **> 48h old**. The guard's STEP 1.5 (added 2026-07-16) runs registry-membership-probe.py + emit-fleet-heartbeat.py + push-fleet-heartbeat.ps1 daily; a stale beacon means that pulse chain silently died again — it sat dark 2026-07-09→07-16 with zero alarms (external dead-man issue ora-claude-config#11 unread), and this beacon exists so that can never recur. The retired LAMS twin `scheduled-task-integrity-guard` is permanently absent (retired 2026-06-11) — do not look for it. |
| `ora-broker-touch-cadence` [CC/MCP] (added v1.9, 2026-07-16) | Notion Ops Hub row (parent page `32b6ecd8-9e59-81f2-b329-df3fd0e25062`), STEP 5 completion posting | Row posted today. **Due monthly on the 2nd ONLY (cron `40 13 2 * *`) — branching-awareness: NOT due on any other day of the month, do not flag missing on days 1 or 3–31.** [CC/MCP] downgrade note applies (ℹ️ informational unless Step 0.06 also shows a dated run-artifact confirming the producer fired). First fire 2026-08-02 — nothing to check before then. |
| `ora-underwrite-doctrine-staleness-check` (LAMS/Cowork, added v1.11, 2026-07-20) | Notion Ops Hub status post (parent page `32b6ecd8-9e59-81f2-b329-df3fd0e25062`) | Post exists today AND is de-duplicated against its own prior week's post (the task flags only NEWLY stale deals, so an unchanged week can legitimately post nothing new — check the task's own Notion history before flagging a silent week as PRODUCER-STALE-OUTPUT). **Due weekly on Wednesdays ONLY (cron `0 13 * * 3`) — branching-awareness: NOT due on any other day of the week, do not flag missing Thu–Tue.** LAMS-native task, checked directly via Step 0's registry data — no [CC/MCP] downgrade applies. Self-contained report-only task: no downstream consumer task depends on this beacon's output. First fire 2026-07-22 — nothing to check before then. |
| `ora-appsec-sweep` [CC/MCP] (added v1.12, 2026-07-20) | Notion Ops Hub completion row (parent page `32b6ecd8-9e59-81f2-b329-df3fd0e25062`) — result line CLEAN / N FINDINGS (worst: X) / TOOLING ERROR / PARTIAL | Row posted today with both pinned repo SHAs (ora-pm + oxford-command-center). **Due weekly on Wednesdays ONLY (cron `30 13 * * 3`) — branching-awareness: NOT due on any other day of the week, do not flag missing Thu–Tue.** [CC/MCP] downgrade note applies (ℹ️ informational unless Step 0.06 also shows a dated run-artifact confirming the sweep actually fired). Registered 2026-07-20 after a manual, Gabriel-supervised first run 2026-07-19 (OI-015 triaged and closed; real residual spun off as OI-022, tracked separately — not this beacon's concern). First fire 2026-07-22 — nothing to check before then. |
| `ora-monday-sync` (LAMS/Cowork, added v1.13, 2026-07-21) | Notion Ops Hub page titled `Monday Sync — YYYY-MM-DD` (parent page `32b6ecd8-9e59-81f2-b329-df3fd0e25062`) + Outlook Sent Items subject `ORA Monday Sync — YYYY-MM-DD` | Page exists dated to the run's week AND a corresponding Sent Items entry exists (search Sent Items, do not assume from exit code alone per the known COM-send caveat at the top of this file). **Due weekly on Mondays ONLY (cron `35 10 * * 1`) — branching-awareness: NOT due on any other day of the week, do not flag missing Tue–Sun.** LAMS-native task, checked directly via Step 0's registry data — no [CC/MCP] downgrade applies. **Motivating incident (2026-07-21):** the 2026-07-20 scheduled fire (3h39m late, correlated Monday machine-offline burst per that day's Automation Health report) updated the registry's `lastRunAt` but produced neither a Notion page nor a Sent Items entry — evidence that `lastRunAt` can advance independent of actual task completion. The gap went undetected until a second, one-day-late manual/catch-up run on 2026-07-21 discovered no "Monday Sync — 2026-07-20" page existed. This is exactly the PRODUCER-STALE-OUTPUT blind spot this table exists to catch; `ora-monday-sync` had no row here until this incident surfaced it. If this beacon goes stale again, route to `orphaned-task-forensics` rather than assuming a simple late-fire. |

**Branching-awareness (REQUIRED):** `ora-am-brief` and `ora-pm-ledger` branch internally by day-of-week. A beacon that is *expected-skipped today* (weekend Block A/C, non-Monday Block D, weekend Block B of pm-ledger's weekday-only outbox-QC) is **NOT** a PRODUCER-STALE-OUTPUT — do not flag it. Only flag a beacon missing on a day its block was due to run.

**RETIRED PRODUCER (removed 2026-07-14):** `ora-setup-audit` [CC/MCP] was dropped from this table — its task folder has sat under `~/.claude/scheduled-tasks/_archive_2026-07-07_retired/` since 2026-07-07 (deliberate retirement, not a drift), and the 2026-07-14 run correctly flagged it ORPHANED-BEACON per the rule below before this row was pulled. If the digest file `Claude_Workspace/00_Governance/outputs/YYYY-MM-DD_setup-self-audit.md` is ever needed again, re-add a row here only after the producer task is actually re-registered in a live fleet.

**ORPHANED-BEACON rule (v1.5, 2026-06-10 — run BEFORE the freshness loop):** verify every producer task named in this table is present AND enabled in one of the two live fleets (Step 0 registry data for LAMS; Step 0.06 filesystem proxy for CC/MCP). A producer listed here but absent from BOTH is **ORPHANED-BEACON** (⚠️ — ALWAYS reported, never silently skipped). Root cause: earlier versions iterated only over tasks WITH a fresh `lastRunAt`, so a task dropped from the registry vanished from this check entirely — that blind spot let the 2026-05-31→06-10 heartbeat outage pass two audits unflagged.

For each producer with a fresh `lastRunAt` (or CC/MCP run-artifact date per Step 0.06), open its DUE beacons and verify freshness. If fresh but a due beacon is stale/missing/duplicated, flag as **PRODUCER-STALE-OUTPUT** (⚠️, or ℹ️ for [CC/MCP] rows per the fleet-membership note above). Cap each beacon-check to one tool call; on failure, log and continue.

## Step 0.56 — Declared `output_contract:` check (NEW v1.10, Plan 2 retrofit, 2026-07-18)

**Purpose:** Step 0.55 above is a hand-maintained table — it only catches a stale beacon for a producer someone remembered to add a row for. A growing number of tasks now declare their own expected output machine-readably, as an `output_contract:` frontmatter block on their SKILL.md (schema first landed on `ora-deal-aging-sla`; see `memory/project_plan2_effect_verification_design_2026-07-18.md` for the design memo). This step checks those declarations. **This is strictly additive** — Step 0.55's table, its branching-awareness logic, its `[CC/MCP]` downgrade rule, and its ORPHANED-BEACON rule are all reused UNCHANGED (by reference, not by re-implementation) and are not replaced, reordered, or removed by this step. A task may legitimately appear in both Step 0.55's table and this step's contract check (e.g. `ora-broker-touch-cadence`, `ora-am-brief`'s blocks) — treat their verdicts independently; never merge or deduplicate findings between the two checks.

1. **Enumerate contract-bearing tasks.** LAMS fleet: for each enabled task from Step 0's registry data, read its SKILL.md (path already known from the registry) frontmatter for an `output_contract:` key. CC/MCP fleet: reuse Step 0.06's per-folder SKILL.md reads verbatim — no new tool call — and parse the same frontmatter key from content already in hand. A task with no `output_contract:` key is simply out of scope for this step (most tasks are not yet retrofitted; Plan 2, 2026-07-18, is a phased rollout — Step 0.55's table remains the only check for everything not yet retrofitted).

2. **ORPHANED-BEACON rule (reused verbatim from Step 0.55, run BEFORE the freshness loop):** before checking any block's freshness, verify the declaring task itself is present AND enabled in its fleet's live registry (Step 0 for LAMS; Step 0.06 filesystem proxy for CC/MCP) — identical verification, identical rule, as already applied to Step 0.55's producer table. A contract-bearing task absent from both fleets is **ORPHANED-BEACON** (⚠️, always reported, never silently skipped) — same severity and same never-skip discipline as Step 0.55.

3. **For each declared block**, in the order it appears in `output_contract.blocks`:
   a. **`expected_on` evaluation reuses Step 0.5's expectedFireTime/cron-walk-backward logic verbatim** — do not reimplement it a second time. `expected_on.cron` walks backward exactly as Step 0.5 does for the declaring task's own cadence to determine whether this block was due in the current audit window; `expected_on.always: true` is due every run (no branching, same treatment as an every-day Step 0.55 producer row); any other declared partial-cadence field (e.g. `days_of_week`) gets the same branching-awareness treatment already in force for Step 0.55/Step 0.9 — apply it, do not invent a new rule.
   b. If the block is NOT due this run per (a), skip it — no check, no flag. Same branching-awareness principle already governing Step 0.55 (a beacon expected-skipped today is not a flag).
   c. If due, resolve artifact existence + recency by `artifact.type`, one tool call per block (same one-call discipline as Step 0.55's beacon checks; log and continue on a tool failure rather than blocking the rest of the audit):
      - `notion_page` with a fixed `page_id` → `notion-fetch`; check `last_edited_time` is within `freshness_window_hours`.
      - `notion_page` with `title_pattern` + `parent_id` → search the parent's children for a title matching the pattern (substitute `{DATE}` with today) — same lookup method Step 0.9 already uses for its Notion cross-reference; check existence + recency within `freshness_window_hours`.
      - `sent_mail` → search the declared `mailbox` for `subject_pattern` (substitute `{DATE}`) to `recipient` within `freshness_window_hours`.
      - `outlook_draft` → search the declared `folder` for a draft matching the block's identifying fields within `freshness_window_hours`.
      - `file` (fixed `path`) or `file` with `path_pattern` (substitute `{DATE}`) → check existence + mtime at the resolved path within `freshness_window_hours` (Desktop Commander `get_file_info`).
   d. **Severity = the block's own `on_missing_severity`** (alarm/warn/info), **EXCEPT: the existing `[CC/MCP]` downgrade rule applies unchanged** — a CC/MCP-fleet task's contract block can only be confirmed via the Step 0.06 filesystem proxy, so downgrade alarm/warn to informational (ℹ️) unless Step 0.06 also shows a dated run-artifact confirming the declaring task actually fired, exactly as already applied to Step 0.55's producer-consumer table.
   e. A declared `skip_condition:` (if present) is read as a documented exception before flagging — same treatment it already receives on `ora-master-workbook-ingest`/`ora-broker-touch-cadence` today: check for the documented no-op/guard-exit signal before flagging a skip-condition block as missing.

4. Report contract-check verdicts separately from Step 0.55's table (see the new Contract-freshness column in Step 1 and the new summary line in Step 4) — do not fold them into the existing PRODUCER-STALE-OUTPUT counts.

## Step 0.6 — Null-lastRunAt creation-date evidence (NEW v1.3)

For any enabled cron task with `lastRunAt: null` whose most recent expected fire has elapsed:

1. Read SKILL.md mtime via `get_file_info` at `C:\Users\Owner\OneDrive - Oxford Capital Partners\Documents\Claude\Scheduled\<taskId>\SKILL.md`.
2. If `mtime > most_recent_expected_fire`, classify as **NOT-YET-DUE-POST-CREATION** (✅ informational).
3. If `mtime ≤ most_recent_expected_fire`, classify as **SILENT-NEVER-FIRED** (⚠️ flag).

## Step 0.75 — RETIRED (2026-06-10)

All four inbox-sweep tasks (`loopnet-autoreply`, `ora-broker-email-to-notion`, `ora-hubspot-note-to-interaction-log`, `direct-prospect-inquiry-draft`) are **PERMANENTLY RETIRED per Gabriel 2026-06-10**. Skip this step entirely — spend zero tool calls. NOT-IN-FLEET is their correct permanent state.

## Step 0.9 — Cross-reference Notion Operations Hub

For each non-inbox-sweep enabled task with a Notion-output side-effect, search Notion (parent `32b6ecd8-9e59-81f2-b329-df3fd0e25062`) for the expected child-page title pattern in the appropriate time window.

Flag any task with: (a) `lastRunAt` older than `expectedFireTime − 30 min`, (b) no corresponding Notion output page in the expected window, (c) inbox-sweep zero side-effect anomaly, (d) registry-state regression from Step 0, (e) producer-stale-output from Step 0.55, or (f) excessive lateness from Step 0.5 (WARN-LATE or ALERT-LATE).

## Step 0.95 — Duplicate-title detection (NEW v1.3)

After Step 0.9, run `notion-search` with the literal title `Automation Health — [today's date]`. If ≥2 pages return, log a `DUPLICATE-TITLE-COLLISION` informational note. Do NOT block publication.

---

## Step 1 — Notion Publication (with parent-id verified success guard, v1.3)

Post a status report page to Notion Operations Hub (parent page ID `32b6ecd8-9e59-81f2-b329-df3fd0e25062`) titled `Automation Health — [today's date]` with:
- Summary line: `[V] verified | [W] warn-late | [F] flagged | [P] producer-stale | [M] model-stale/untagged | [R] registry regressions | window [UTC start → UTC end]`
- Per-task status (✅ / ℹ️ / ⚠️ / ❌), split into **LAMS fleet (registry-confirmed)** and **CC/MCP fleet (filesystem-derived)** sections per Step 0.06.
- Lateness column showing each task's `lastRunAt − expectedFireTime` delta in minutes (LAMS fleet only — no equivalent field exists for CC/MCP).
- Beacon-freshness column for producer tasks.
- Contract-freshness column (Step 0.56): per declared `output_contract:` block, ✅/ℹ️/⚠️ verdict + which artifact type was checked; note `[CC/MCP]` downgrades same as the beacon column.
- Model-currency column (Step 0.07): current / MODEL-STALE / MODEL-UNTAGGED per LAMS task, with a one-line note that CC/MCP isn't covered.
- Registry-diff section.
- Actions taken.
- Audit window timestamp (UTC start → end).

**PUBLICATION-SUCCESS GUARD (v1.3):**

1. After calling `notion-create-pages`, capture `pages[0].id` and `pages[0].url`.
2. If response missing/errored/empty ID → retry ONCE with same content.
3. If second attempt also fails → jump to Step 3.
4. **Verify via direct fetch (NOT notion-search):** call `notion-fetch` with the create-pages-returned page ID; confirm matching title AND ancestor-path includes parent `32b6ecd8-9e59-81f2-b329-df3fd0e25062`. If fetch returns nothing or parent mismatch → publication failure → Step 3.
5. **Do NOT use `notion-search` for verification** — search-index propagation lag and same-title collisions produce false failures.

## Step 2 — Standard Flag Notification

If any task shows ⚠️ or ❌, send an Outlook email via the SOLE send path `C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1` to ggoldberg@oxfordra.net with subject `⚠️ Cowork Automation Alert — [Task Name(s)] [today's date]`. Body lists each flagged task with classification and the Notion audit page link. MODEL-STALE/MODEL-UNTAGGED (ℹ️) do NOT trigger this email on their own — informational-only findings surface in Notion, not via alert email, unless a ⚠️/❌ from another check also fired this run. Pre-authorized under the routing canon — auto-send permitted. On non-zero COM exit retry once, then flag in the Notion completion row. **Given the 2026-07-08 known-issue note above, also state explicitly in the chat summary whether this send could be independently confirmed (e.g., via a follow-up outlook_email_search) — do not assume success from exit code alone if the COM hang issue is still live.**

## Step 3 — Outlook Fallback Alert (auto-send on publication failure ONLY)

If Step 1 fails after one retry, AUTO-SEND an Outlook email via the SOLE send path:
- to: ggoldberg@oxfordra.net
- subject: `❌ ora-automation-health-monitor PUBLICATION FAILED — [today's date]`
- body: audit summary + per-task verdicts + Notion API error + parent-id verification result.
- Tag the email body with `AUTO-SENT — meta-failure path, no human-in-loop available`.

## Step 4 — Chat Summary

Print a 5–8 line summary in the chat. Line 1 must include the publication path (`Notion ✅` / `Notion ❌ → Outlook fallback ✅/❌`). Subsequent lines:
- Verified/warn-late/flagged counts, split LAMS vs CC/MCP.
- Top 3 latency outliers (taskId + delta in minutes), if any.
- Producer-stale-output flags, if any (note [CC/MCP] ones as informational per the fleet-membership note).
- Contract-freshness flags, if any (Step 0.56, declared `output_contract:` blocks only — separate from the producer-stale-output count above; note [CC/MCP] ones as informational per the same fleet-membership downgrade rule).
- Model-currency: count of MODEL-STALE/MODEL-UNTAGGED tasks, if any (name them); one-line CC/MCP-not-covered caveat.
- Registry diff (deletions, regressions only).
- Step 0.75 coverage note (permanently retired — one line, no probing).

Full details live in Notion (or the fallback email if Step 3 fired).

---

## Operational notes

- **DST handling:** all expected-fire computation is anchored to America/New_York.
- **Snapshot retention:** keep last 30 daily snapshots; archive month-end snapshots to `_state-history/_archive/YYYY-MM.json`.
- **Skill backups:** retain v1.1+ SKILL.md backups at `_state-history/_skill-versions/SKILL.vX.Y-YYYY-MM-DD-<reason>.md`.

*Changelog: v1.14 (2026-07-22) Step 0.55 `ora-health-guard` (Block B — preflight) row repointed to a new PRIMARY check — Notion beacon page `3a56ecd8-9e59-8152-83b6-c61cec736f2b` written by `ora-health-guard` B.3.5 (new that same day), Sent Items subject search demoted to secondary/backup — motivated by the 2026-07-22 run finding the Sent Items search came up empty despite the block having fired, forcing an unnecessary informational downgrade. Also added a new informational-only table row for `ora-health-guard` Block A.0 (new 2026-07-22 wake-lateness immediate alert — not independently checked by this step, cross-referenced so a same-day A.0 alert and an ALERT-LATE finding on the same AM cluster are read as one incident, not two). Both changes are Gabriel-directed workflow-optimization follow-ups to that day's own Automation Health report; additive only, Step 0.5/0.56 logic unchanged. v1.13 (2026-07-21) added `ora-monday-sync` [LAMS/Cowork] to the Step 0.55 producer-consumer table (Notion Ops Hub page `Monday Sync — YYYY-MM-DD` + Outlook Sent Items check, due Mondays only, cron `35 10 * * 1`). Motivated by an incident where the 2026-07-20 fire (correlated Monday machine-offline burst) updated the registry's `lastRunAt` but produced no Notion page or Sent Items entry — invisible to Step 0.5's lastRunAt-only lateness check; not discovered until a one-day-late catch-up run on 2026-07-21 found no prior page existed. Additive table row only — Step 0.5's expectedFireTime logic and Step 0.56's output_contract logic are unchanged. v1.12 (2026-07-20) added `ora-appsec-sweep` [CC/MCP] to the Step 0.55 producer-consumer table (Notion Ops Hub completion row, due weekly on Wednesdays only, cron `30 13 * * 3`; first fire 2026-07-22). Registered after its manual, Gabriel-supervised first run (2026-07-19) surfaced OI-015 (triaged and closed) and dependency-CVE fixes later merged to oxford-command-center main. Additive table row only — Step 0.5's expectedFireTime logic and Step 0.56's output_contract logic are unchanged. v1.11 (2026-07-20) added `ora-underwrite-doctrine-staleness-check` [LAMS/Cowork] to the Step 0.55 producer-consumer table (Notion Ops Hub status post, due weekly on Wednesdays only, cron `0 13 * * 3`; first fire 2026-07-22). Registered while re-underwriting 754 Old State Route 74 — flags live-pipeline UNDERWRITE/FULL workbooks and IC memos stamped with an acquisition-underwriting skill version older than the latest scorecard-affecting doctrine ratification, the exact gap that let 754's own 6/8/2026 IC Memo sit unflagged under a superseded Basis/Yield floor for five weeks. Additive table row only — Step 0.5's expectedFireTime logic and Step 0.56's output_contract logic are unchanged. v1.10 (2026-07-18) NEW Step 0.56 — additive check of per-task declared `output_contract:` SKILL.md frontmatter blocks (Plan 2 of the 2026-07-18 setup-improvement effort; design memo `memory/project_plan2_effect_verification_design_2026-07-18.md`), reusing Step 0.5's expectedFireTime/cron-walk-backward logic and Step 0.55's `[CC/MCP]` downgrade rule + ORPHANED-BEACON rule unchanged; adds a Contract-freshness column to Step 1's Notion report and a parallel summary line to Step 4's chat summary; Step 0.55's table, branching-awareness logic, and all prior rules are untouched (verified byte-identical aside from this new step and the two additive report/summary lines). v1.9 (2026-07-16) added `ora-broker-touch-cadence` [CC/MCP] to the Step 0.55 producer-consumer table (Notion Ops Hub completion row, due monthly on the 2nd only). v1.6 (2026-07-08, 2nd pass) Step 0.07 model-currency self-check against reference_scheduled_task_model_standard.md — MODEL-STALE/MODEL-UNTAGGED classification, wired into Step 1 Notion report and Step 4 chat summary; does not auto-fix, informational only. v1.5 (2026-06-10) ORPHANED-BEACON rule. v1.4 (2026-06-09) Step 0.06 dual-fleet audit (fleet-scope corrected 2026-07-08 — see PROMOTION NOTE at top). v1.3 (2026-05-14) dual-bounded lateness, producer-consumer beacons, mtime evidence, duplicate-title detection, publication-success guard rewrite. v1.2 (2026-05-08 evening) registry diff, expected-fire window, state persistence. v1.1 (2026-05-08) publication guard.*