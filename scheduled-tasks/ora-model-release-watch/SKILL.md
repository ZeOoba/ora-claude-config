---
name: ora-model-release-watch
description: Weekly Monday ~11:20 AM ET — detects new Anthropic Claude model releases by reading this session's own system-prompt model-lineup statement and diffing against reference_model_release_checklist.md; on detection, updates that memory file, posts to Notion Ops Hub (32b6ecd8-9e59-81f2-b329-df3fd0e25062), and emails ggoldberg only with the concrete update checklist (settings.json, scheduled-task-standard memory, oxford-command-center + ora-pm sweep). Silent no-op when nothing changed. v1.0 2026-07-10. [MODEL: claude-opus-5 observed | checked 2026-08-12 via live-run transcript canary]
---

# ORA Model Release Watch (CC/MCP fleet)

**Purpose:** Detect when Anthropic ships a new Claude model, so Gabriel doesn't have to remember to ask about model-selection updates himself.

## Step 1 — Read the current model lineup from THIS session

The Claude Code harness states the current model lineup somewhere in this session's own system prompt / environment context (e.g. "You are powered by the model named X ... the most recent Claude models are ..." with exact model ID strings). Read that directly.

Do NOT source model IDs from:
- training-data recall of model names,
- the claude-api skill's cached model table (confirmed stale by over a month as of 2026-07-10 — it still listed claude-sonnet-4-6 after Sonnet 5 had already shipped and become the live default).

## Step 2 — Compare against the recorded baseline

Read `C:\Users\Owner\.claude\projects\C--Users-Owner-OneDrive---Oxford-Capital-Partners\memory\reference_model_release_checklist.md` → the "Current lineup as of <date>" line at the top. Compare the model ID set just read in Step 1 against this recorded set.

- **No new model ID present** (same IDs, regardless of date staleness): exit silently. Do not post to Notion, do not send email, do not touch any file. A clean week is silent by design — this is not a bug, don't "fix" it into a status ping.
- **A new model ID is present that is NOT in the recorded set** (a new Sonnet/Opus/Haiku/Fable-tier release, or an entirely new named tier): proceed to Step 3.

## Step 3 — On a detected release

1. Edit the "Current lineup as of <date>" line in `reference_model_release_checklist.md` to the new roster + today's date. Preserve the rest of that file (the "Where exact IDs live" inventory and the "Process on every new Claude model release" checklist below it) untouched — this is a targeted edit, not a rewrite.
2. Post a block to the Notion Operations Hub (parent page `32b6ecd8-9e59-81f2-b329-df3fd0e25062`, full UUID): old lineup → new lineup, plus the concrete checklist copied verbatim from `reference_model_release_checklist.md`'s "Process on every new Claude model release" section (that file is the source of truth — don't re-derive the checklist from scratch). If a Notion create-pages response comes back without a page ID (e.g. a grace-period/quota notice), search by the exact title before any retry — a match created at/after the create call is this run's page; never blind-retry a create (that produced a duplicate). Quota errors → `notion-quota-fallback` skill.
3. Send an email to `ggoldberg@oxfordra.net` ONLY (never cc — this is not the ora-am-brief Daily Brief's sanctioned exception) via the sole send path `C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1`. Subject: "New Claude model detected: <old lineup> -> <new lineup>". Body: same old→new summary + the checklist (bump `~/.claude/settings.json` top-level default + `reference_scheduled_task_model_standard.md` same day; leave CLAUDE.md/ora-skills alone — alias-based; sweep `C:\Users\Owner\oxford-command-center` (server/ai/*.ts, om-extract.ts, index.ts, .env) and `C:\Users\Owner\ora-pm` for hardcoded model-ID literals via the claude-api skill's `shared/model-migration.md`; re-run the CC/MCP canary check for the #48976-pattern gap).
   - Exit 2 (COM failure) or 4 (timeout): retry the send once, then flag loudly in the Notion completion row if it still fails — do NOT halt.
   - Exit 1 (usage error) or 3 (stuck Outlook wizard needing a human): do NOT retry — flag immediately in the Notion row.
   - Exit 5 or 6 (or any other code): do NOT retry and never resend (exit 6 = send state unknown — the message MAY have gone out) — flag immediately in the Notion row, per rules.md §2.

## Never fabricate

If this session's model-lineup statement is missing, ambiguous, or you're not confident you've read it correctly, do NOT guess or invent model IDs. Post a `QUESTIONS FOR GABRIEL` entry in the Notion completion row stating exactly what was unreadable, and stop there — do not silently skip the week without a record of why.

## This task's own model

This task runs on the CC/MCP fleet, which is server-pinned and does not reliably respect the creating session's model (confirmed via a canary test 2026-07-08 — matches community-reported Claude Code issue #48976; see `reference_scheduled_task_model_standard.md`). Do not claim a resolvable model ID for this task's own description tag — `[MODEL: UNVERIFIABLE]` is the correct, honest value; update only the "checked <date>" portion when you touch this file.

## Sibling references — don't duplicate their logic

- Full model-ID inventory + the update checklist: `memory/reference_model_release_checklist.md` — read and update it, don't reproduce its content from memory.
- LAMS/Cowork scheduled-task model-standard mechanics: `memory/reference_scheduled_task_model_standard.md` — a separate concern (that file tracks whether the *scheduled-task fleet itself* is on the current model; this task tracks whether Anthropic has released a new model at all). Don't conflate the two.
- Actual code migration once a release is confirmed is explicitly NOT this task's job — that goes through the claude-api skill's `shared/model-migration.md`, run by Gabriel or a session he directs.