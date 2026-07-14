---
name: canary-model-check-temp
description: One-time canary probe (2026-07-13) — determines which model the CC/MCP fleet actually executes scheduled tasks under, vs. the claude-sonnet-5 standard (reference_scheduled_task_model_standard.md). Writes result to _canary-model-check-result.txt. Self-disables after firing; safe to delete once read.
---

ORA CC/MCP Canary Model-Check — ONE-TIME diagnostic task, not a recurring automation.

PURPOSE: Determine which Claude model this CC/MCP scheduled task actually executes under, since the CC/MCP fleet's model is server-pinned and not independently settable (see memory/reference_scheduled_task_model_standard.md — prior canary evidence, 2026-07-08, found a task firing on claude-opus-4-8 instead of the expected claude-sonnet-5, matching community-reported Claude Code issue #48976).

GUARD: This task performs NO Notion writes, NO email, NO ORA data mutation of any kind. It only identifies itself and writes one result file.

STEP 1 — Identify your own model. Your system prompt states a line similar to "You are powered by the model named <X>. The exact model ID is <id>." Read that line verbatim from your own system prompt. Do NOT infer or guess a model from behavior or capability — report only what your system prompt literally states. If no such model-identity line exists in your system prompt, write "UNKNOWN — no model-identity line found in system prompt" rather than guessing.

STEP 2 — Write the result. Write (overwrite, don't append) a plain-text file at exactly this path: C:\Users\Owner\.claude\scheduled-tasks\_canary-model-check-result.txt

File contents (fill in the bracketed values, keep the key: value format, one per line):
fired_at: [current ISO-8601 timestamp with timezone offset]
model_id: [the exact model ID string from your system prompt, or UNKNOWN]
model_name: [the model name from your system prompt, or UNKNOWN]
expected: claude-sonnet-5
match: [YES if model_id equals claude-sonnet-5, NO otherwise, UNKNOWN if you could not determine model_id]
task_id: canary-model-check-temp

STEP 3 — Stop. Do nothing else — no Notion post, no email, no other file writes, no registry/config changes. Do not attempt to delete or modify your own scheduled-task registration; this one-time task auto-disables after firing and will be reviewed and removed manually by Gabriel's session afterward.