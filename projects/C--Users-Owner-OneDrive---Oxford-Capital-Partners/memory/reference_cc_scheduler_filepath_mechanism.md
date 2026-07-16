---
name: reference-cc-scheduler-filepath-mechanism
description: "CC/MCP scheduler registry stores only filePath (not prompt text) — editing a scheduled-task's SKILL.md at that path is the authoritative, effective way to change what it runs; no registry copy, no divergence. Scheduled-task specs are NOT git-versioned in the brain repo."
metadata: 
  node_type: memory
  type: reference
  originSessionId: 682f5096-5198-47fd-af17-4ab2bd5e1079
---

The CC/MCP scheduler registry (`C:\Users\Owner\AppData\Roaming\Claude\claude-code-sessions\a6ad2c61-…\583f08bc-…\scheduled-tasks.json`) stores per task ONLY: `id, cronExpression, enabled, filePath, createdAt, lastRunAt, cwd`. There is **NO stored prompt/instructions copy** — the scheduler reads the SKILL.md at `filePath` at fire time (confirmed 2026-07-12 by direct read of the `ora-weekly-hygiene` entry).

**Implications:**
1. Editing `~/.claude/scheduled-tasks/{id}/SKILL.md` IS the effective way to change a task's instructions — the change takes effect on the **next fire**, no `update_scheduled_task` needed for content-only edits.
2. **No file/registry divergence is possible for prompt content** — the registry holds only the path. (`list_scheduled_tasks`' "Read the path to see the current prompt" is literal: the file *is* the prompt.)
3. `update_scheduled_task`'s `prompt` param writes to that file; it does not create a second copy. Use it only when you want the tool to author the file for you.
4. Registry JSON is READ to understand mechanism only — **never edit it directly** ([[register-scheduled-task]] RULE 2).

**Separate finding (versioning gap):** scheduled-task SKILL.mds are NOT versioned in the brain repo (`github.com/ZeOoba/ora-claude-config`). Its `.gitignore` line 12 is `/*` (ignore-all + selective whitelist); `scheduled-tasks/` is not whitelisted and has no nested `.git`. Specs persist ONLY via OneDrive archive + session-transcript restoration — the root cause of the repeated `ora-weekly-hygiene` / `ora-pm-ledger` loss-and-restore incidents (see those files' RESTORATION NOTEs). A durable fix would whitelist the SKILL.mds (not the runtime `_state/`/`_unsent/`) — pending Gabriel's decision. See [[register-scheduled-task]].
