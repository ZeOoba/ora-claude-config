---
name: ora-session-sweep
description: Weekly Sunday 20:00 session-index sweep — reads C:\Users\Owner\Obsidian\BrainVault\.claude\scripts\session-sweep-prompt.md and indexes new Cowork sessions into the BrainVault Sessions folder. Index-only, no external sends. v1.0 (2026-07-10). [MODEL: claude-sonnet-5 | set 2026-07-13]
---

Read and follow the instructions in `C:\Users\Owner\Obsidian\BrainVault\.claude\scripts\session-sweep-prompt.md` (the section below '## Task instructions') exactly.

If the file is missing or unreadable, do NOT improvise the sweep — log the failure to the Notion Ops Hub (32b6ecd8) and stop. Never fabricate session data; index only what list_sessions returns.