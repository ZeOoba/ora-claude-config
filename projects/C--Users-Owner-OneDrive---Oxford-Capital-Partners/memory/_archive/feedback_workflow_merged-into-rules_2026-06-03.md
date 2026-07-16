---
name: Workflow Preferences & Feedback
description: How Gabriel wants Claude to work — validated behaviors and corrections
type: feedback
originSessionId: b2cfdcff-b986-4e60-b23b-da66f9672e14
---
**Never overwrite existing configs without reading them first.**
Why: settings.json contains custom hooks, MCP permissions, and env vars. A blind overwrite destroys months of configuration.
How to apply: Always read settings.json, CLAUDE.md, and change-log.md before any write that touches them.

**Check what already exists before installing or creating anything.**
Why: Gabriel has ~70 skills (4 user-scope + 13 ORA Cowork OS + ~41 anthropic-skills marketplace + 4 plugin skills + a few others), 9 MCP connectors, and a fully configured system. Suggesting things he already has wastes time.
How to apply: ls ~/.claude/skills/ AND ls "OneDrive/Cowork OS/.claude/skills/" AND read settings.json at the start of any setup session. Source-of-truth for ORA-built skills is the Cowork OS path (git-tracked at github.com/ZeOoba/ora-skills).

**Don't suggest fake plugin systems or non-existent Claude Code features.**
Why: Claude Code has no /plugin command or marketplace. Prompts claiming otherwise waste session time.
How to apply: Stick to real extensibility mechanisms: skills, MCP servers, hooks, CLAUDE.md files.

**Proceed without asking on: file creation, file moves, folder creation.**
**Always ask before: file deletion, external communications, modifying financial models, sending emails.**
Why: Gabriel wants velocity on non-destructive actions, explicit confirmation on irreversible ones.

**Be direct about diminishing returns.**
Why: Gabriel doesn't want to add things for the sake of it. When the system is complete enough, say so.
How to apply: Flag when additional additions won't move the needle before building them.
