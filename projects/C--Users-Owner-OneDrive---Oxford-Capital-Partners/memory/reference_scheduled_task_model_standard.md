# LAMS/Cowork Scheduled-Task Model Standard

**Current standard: claude-sonnet-5**
**Set:** 2026-07-08 (rationale + mechanism: event_log.md, "2026-07-08 (cont.) — LAMS/Cowork scheduled-task fleet standardized onto claude-sonnet-5")

## Why this file exists

Scheduled tasks bind to whichever model created them at registration time (canary-tested 2026-07-08) — there is no live `model` field on `create_scheduled_task`/`update_scheduled_task`, no org/task setting that keeps a task current as new models ship, and no delete tool on this surface (UI-only, folder-destructive). Every model bump requires manually redoing the same disable → archive → delete (Gabriel, sidebar) → recreate → verify cycle per task. This file is the single source of truth for "what should the fleet be on right now," so that gap is *detectable* even though it isn't *self-healing*.

## Tagging convention

Every LAMS task's `description` field carries a trailing tag:

`[MODEL: <model-id> | set YYYY-MM-DD]`

Set at creation/recreation time. `automation-health-monitor`'s **Model-currency check** (added to the SKILL.md 2026-07-12; see correction note below) reads this tag off each LAMS task's `description` (already returned by `list_scheduled_tasks` — no extra tool call) and flags any task whose tag doesn't match this file's "Current standard" line as `MODEL-STALE` (ℹ️ informational — there's no forced-upgrade action to take automatically, only a manual recreate). The same step ALSO reads the CC/MCP fleet's `[MODEL: ...]` frontmatter tags — see the corrected CC/MCP note below.

> **CORRECTION 2026-07-12:** this file previously asserted the check was "Step 0.07" and already live. In fact the automation-health-monitor SKILL.md carried NO model-currency step at all until 2026-07-12 — the methodology was documented here but never implemented in the skill body (which only had Steps 1–4). The step was authored on 2026-07-12 (needs a Cowork Save-skill re-upload to deploy; see [[reference_scheduled_task_model_standard]] usage in the health monitor).

## To bump the standard

1. Update the **Current standard** line above.
2. For each task automation-health-monitor flags `MODEL-STALE`: disable → capture prompt → archive folder → Gabriel deletes registry entry via Scheduled sidebar → recreate with identical taskId/cron/prompt from a session on the new model → tag the new description → verify via `list_scheduled_tasks`. Full mechanics: event_log.md 2026-07-08 entry.
3. Log the bump to event_log.md.

## CC/MCP fleet — model is NOT settable, but IS observable (corrected 2026-07-12)

Earlier framing (2026-07-10) called the CC/MCP fleet "structurally uncoverable." That conflated two different things and is **corrected here**:

- **Not SETTABLE — true.** CC/MCP scheduled tasks run on a server-pinned model outside session/registry control (`ora-task-integrity-guard/SKILL.md:22`); there is no live `model` field to *choose*. A canary test (`.claude/scheduled-tasks/_canary-model-check-result.txt`) caught one task firing on `claude-opus-4-8` instead of the creating session's `claude-sonnet-5` default — confirming the #48976 pattern in practice.
- **But OBSERVABLE / COVERABLE — the "uncoverable" claim was wrong.** The health monitor CAN read each CC/MCP task's `~/.claude/scheduled-tasks/<id>/SKILL.md` frontmatter `[MODEL: ...]` tag (same read used to enumerate enabled tasks). This is *disproven-by-example*: `ora-cc-schematic-refresh` carries a real `[MODEL: claude-sonnet-5 | checked 2026-07-12]` tag — a concrete model id with a `checked` verb (an OBSERVATION of the pinned model), not `set`. So the CC/MCP currency check is a **tag-presence + observation-freshness** check (is the tag present and recently `checked`), NOT a match-the-standard check (the model can't be forced).

**Live CC/MCP tag distribution (observed 2026-07-12, ~19-task live fleet per `fleet-status.py`):** 12 tasks carry `[MODEL: UNVERIFIABLE | checked <date>]`; 1 (`ora-cc-schematic-refresh`) carries a real `claude-sonnet-5 | checked` id; the remaining (newer) tasks carry **no `[MODEL]` tag yet** — those are the real gap (untagged), not "uncoverable." Prior text said "11 UNVERIFIABLE"; the live count is 12. Re-check each release (see [[reference_model_release_checklist]]).

**RE-CHECK 2026-07-13 (via `list_scheduled_tasks`, live 19-task fleet):** every CC/MCP task now carries a tag — 18/19 `UNVERIFIABLE`, 1/19 (`ora-cc-schematic-refresh`) real `claude-sonnet-5`. The untagged gap noted above is closed; the "not settable, only observable via canary" limitation is unchanged — none of the 18 UNVERIFIABLE tasks can be confirmed on-standard without a per-task canary test.

## LAMS/Cowork fleet — tag coverage closed 2026-07-13

Audited the raw registry (`local-agent-mode-sessions\...\scheduled-tasks.json`, 21 enabled tasks) against each task's SKILL.md description. As of 2026-07-12 only 6/21 carried a `[MODEL:]` tag (`ora-cowork-heartbeat`, `ora-am-brief`, `ora-friday-closeout`, `ora-monday-sync`, `automation-health-monitor`, `ora-lease-expiration-brief` — all `claude-sonnet-5 | set 2026-07-08`). Gabriel approved tagging the remaining 15 (`ora-consolidate-memory-monthly`, `ora-skill-store-drift-check`, `ora-skill-text-audit`, `ora-om-intake-ocr`, `ora-owner-outreach-queue-refresh`, `ora-passed-deal-tracker`, `ora-replacement-cost-refresh`, `ora-bearmode-refresh`, `ora-cam-reconciliation-annual`, `ora-counsel-review-standard-positions`, `ora-stale-pipeline-nudge`, `ora-ar-export-freshness-nudge`, `ora-session-sweep`, `ora-gis-endpoint-liveping`, `ora-cam-data-backfill`) with `[MODEL: claude-sonnet-5 | set 2026-07-13]`. LAMS fleet is now 21/21 enabled tasks tagged, all claude-sonnet-5. 2 disabled tasks (`efulton-post-legalhold-consolidation`, `ora-tenant-db-dedup-remediation`) remain untagged — low priority while disabled.

**Caveat:** a `[MODEL: ... | set ...]` tag on a LAMS task records what the task was *intended*/tagged as at creation or tagging time — same as the pre-existing 6 — it does not itself force or re-verify the model the task actually fires on (still no live `model` field on `create_scheduled_task`/`update_scheduled_task`). Full confidence still requires the disable → recreate → verify cycle described above if drift is ever suspected.

Side finding, not fixed (out of scope, flagged for a separate pass): `ora-skill-text-audit\SKILL.md` has a duplicated frontmatter block (identical `---...---` header appears twice in the file).

**CORRECTION 2026-07-15:** the 2026-07-13 "21/21 tagged" claim above was stale — live `list_scheduled_tasks` on 2026-07-15 showed `ora-skill-store-drift-check` (pre-existing task, tag never actually applied despite the 2026-07-13 claim) and `ora-ic-memo-pipeline-reconciliation` (new task, created 2026-07-15, v1.0) both MODEL-UNTAGGED. Both tagged `[MODEL: claude-sonnet-5 | set 2026-07-15]` via `update_scheduled_task` same day. Fleet is 22/22 enabled LAMS tasks tagged as of 2026-07-15 (one task, `ora-counsel-review-standard-positions`, is a future one-time fire and was already tagged; `efulton-post-legalhold-consolidation` remains disabled/untagged, unchanged, low priority).

**SEPARATE FIX 2026-07-15 (not model-related, logged here since it touches the same automation-health-monitor / ora-task-integrity-guard pair):** both tasks' Step 0 / Step 0.5 were independently instructed to write their own fleet's daily snapshot to the identical bare `_state-history\YYYY-MM-DD.json` filename — a collision that let whichever fleet ran later in the day clobber the other's baseline (confirmed happening again in real time during this fix: ora-task-integrity-guard's 12:54 ET run overwrote a freshly-renamed `.lams.json` file with CC/MCP data before the corrected SKILL.md could take effect for that in-flight run). Both SKILL.mds and `membership-guard.ps1`'s read filter were repointed to fleet-exclusive suffixes (`.lams.json` / `.cc.json`); today's clobbered data was manually split back into the two correctly-named files. Confirm on the next automation-health-monitor run that ora-task-integrity-guard's next fire (tomorrow ~12:45 ET) wrote directly to `.cc.json` without incident.

**RE-CHECK 2026-07-15 (Gabriel re-affirmed the standing default in-turn):** live CC/MCP fleet via `list_scheduled_tasks` = 19 enabled tasks. One new task since the last audit, `ora-sofr-direct-prefetch` (registered 2026-07-15), was missing its `[MODEL:]` tag entirely — tagged `[MODEL: UNVERIFIABLE | checked 2026-07-15]` to close the gap, restoring 19/19 enabled tasks tagged (18 UNVERIFIABLE + 1 real `claude-sonnet-5` on `ora-cc-schematic-refresh`). No task was found firing on, or explicitly set to, a non-Sonnet-5 model. Reminder for future task creation: tag new CC/MCP tasks at registration time, not retroactively — see also [[feedback_routines_default_model]] for the parallel native-Cron/routines rule.
