---
name: reference-update-scheduled-task-drops-frontmatter-keys
description: "update_scheduled_task(description=...) rewrites a task's SKILL.md frontmatter and SILENTLY DELETES every top-level key it does not own — output_contract is the one that matters. Check and restore after every call."
metadata: 
  node_type: memory
  type: reference
  originSessionId: 633f8f1a-93f8-4fba-9b17-7ee3b81ce3cb
  modified: 2026-08-09T15:44:54.827Z
---

# `update_scheduled_task` silently drops non-owned frontmatter keys

**Confirmed live 2026-08-09**, twice, on the CC/MCP fleet.

`mcp__scheduled-tasks__update_scheduled_task(taskId, description=...)` does **not** write to the
registry — `scheduled-tasks.json` carries no `description` field at all (see
[[reference_scheduled_task_model_standard]]). It rewrites the task's
`~/.claude/scheduled-tasks/<id>/SKILL.md` **frontmatter**, emitting only the keys it knows
(`name`, `description`). **Every other top-level frontmatter key in that file is discarded.**

## What it cost

| Task | Key lost | Size |
|---|---|---|
| `ora-task-integrity-guard` | `output_contract` | 5 blocks, 53 lines |
| `ora-am-brief` | `output_contract` | 4 blocks, 52 lines |

Tracked as **OI-109**.

`output_contract` is not decorative. It declares each task's artifacts, freshness windows, and
`is_primary_health_signal` — the contract `automation-health-monitor` Step 0.56 uses to alarm
externally when a task's primary health signal goes missing. Deleting it silently disarms that
external alarm while the task keeps reporting clean. For `ora-task-integrity-guard` specifically,
the lost block was `block-cc-fleet-snapshot`, the guard's OWN declared primary health signal.

Three other tasks retagged the same day (`ora-skill-cache-drift-alert`,
`ora-cc-schematic-refresh`, `ora-lease-snapshot-refresh`) were unaffected **only because they have
no `output_contract`**. The blast radius is "whichever tasks happen to carry extra keys," which is
exactly the kind of silent, uneven damage that is easy to miss.

## The rule

**After ANY `update_scheduled_task` call that sets `description`, diff the task's SKILL.md
frontmatter against `git show HEAD:<path>` and restore any dropped top-level key.** Do not assume
the call is description-only just because that is the only field you passed.

Cheap check:

```bash
git -C ~/.claude diff --stat HEAD -- scheduled-tasks/<id>/SKILL.md
```

A description-only retag should show ~1-2 changed lines. Tens of deletions means a key was dropped.

## Restoring

Restore **surgically** — splice the block from `HEAD` into the CURRENT file. Do NOT
`git checkout` the file: its body may hold another session's newer edits, and on a fleet where
several sessions edit task specs concurrently (routine as of 2026-08) a wholesale revert destroys
their work. Working script pattern: read `git show HEAD:<relpath>`, extract the top-level key plus
its indented children, insert immediately before the closing `---` of the current file's
frontmatter. Verify afterwards that `git diff --stat HEAD` is back to the expected 1-2 lines.

## Prefer a direct file edit when you can

If the change is to the SKILL.md **body** (adding a STEP, editing procedure text), edit the file
directly with Edit/Write — that path does not touch frontmatter and cannot trigger this. Reserve
`update_scheduled_task` for what genuinely needs the MCP tool: `enabled`, `cronExpression`,
`fireAt`, and the `description` itself (which is also what `list_scheduled_tasks` returns and what
the model-tag classifier reads, so it does have to go through the tool).

Related: [[reference_scheduled_task_model_standard]] (the retag workflow that surfaced this),
[[feedback_verify_before_repeating_session_claims]] (verify after the write, never assume it landed).
