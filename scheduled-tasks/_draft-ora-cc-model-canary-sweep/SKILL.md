---
name: ora-cc-model-canary-sweep
description: "DRAFT, NOT REGISTERED — staged 2026-07-21 by automation-health-monitor as a workflow-optimization follow-up. Monthly (proposed: 1st, 07:00 ET) canary-test sweep of the CC/MCP fleet's server-pinned model — converts the 17/20 [MODEL: UNVERIFIABLE | checked <date>] tags from unknown to confirmed by actually invoking each task's model and reading back which model responded, instead of relying on frontmatter observation alone."
status: DRAFT — requires Code-surface review + registration (Cowork's create_scheduled_task cannot register CC/MCP fleet tasks; this file is staged content only)
---

# ORA CC/MCP Model Canary Sweep (DRAFT v0.1, 2026-07-21)

## Why this exists

automation-health-monitor's Step 1.5 model-currency check can read each CC/MCP task's `[MODEL: ...]` frontmatter tag, but per `reference_scheduled_task_model_standard.md` that tag is self-reported at authoring time, not independently verified — the model a CC/MCP task actually runs on is server-pinned and only confirmable via a canary test (see `.claude/scheduled-tasks/_canary-model-check-result.txt` precedent, which caught one task running `claude-opus-4-8` instead of its assumed `claude-sonnet-5`). As of the 2026-07-21 health check, 17 of 20 standing CC/MCP tasks carry `UNVERIFIABLE` — this sweep is the forced-verification path referenced in that report's workflow-optimization list.

## Proposed mechanism

1. For each enabled CC/MCP task folder under `~/.claude/scheduled-tasks/` (excluding `_archive_*`, `_shared`, and this draft's own folder), read its SKILL.md frontmatter to get the task's own self-identification convention.
2. Rather than re-running each full task (expensive, some are write-capable), inject a lightweight, read-only "identify yourself" probe: a one-off scheduled task (or a Code-surface loop) that fires immediately after each target task's next natural cron slot and asks the model in that session to state its own model ID string, then diffs it against the target task's frontmatter tag.
3. Write results to `~/.claude/maintenance/_state/cc-model-canary-<DATE>.json` (one row per task: expected tag, observed model, match/mismatch).
4. On mismatch, do NOT auto-fix (model is not settable) — flag in the canary-sweep Notion post + email ggoldberg only, matching the informational-only severity convention of the existing model-currency check.
5. Update each task's `[MODEL: <observed> | checked <DATE>]` tag with the confirmed value (currently `UNVERIFIABLE` placeholders) once verified.

## Open design questions for the registering session (Code surface)

- Whether probing every task monthly is worth the overhead vs. a rolling subset (e.g. 5 tasks/month, full coverage quarterly).
- Whether the "identify yourself" probe needs to run as a distinct one-off task per target, or can piggyback on each target's own next scheduled fire (lower overhead, but couples canary logic into every task's prompt).
- Confirm this doesn't trip any confidentiality/blast-radius gate before registering (governor/financial-code-adjacent tasks like ora-financial-code-integrity-sweep may warrant opus-floor confirmation per Engineering OS invariants, not just informational tagging).

## Status

Staged by Cowork (automation-health-monitor session, 2026-07-21). NOT live — no `create_scheduled_task` call has been made for this. Needs Gabriel + a Code-surface session to review the design questions above and register.
