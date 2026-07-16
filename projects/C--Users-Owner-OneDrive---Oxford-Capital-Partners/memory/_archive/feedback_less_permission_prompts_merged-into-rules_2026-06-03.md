---
name: Always run less-permission-prompts
description: Standing preference — run the less-permission-prompts skill whenever Gabriel starts a session or whenever new common tool calls would generate permission friction
type: feedback
originSessionId: 2d0449c2-82ea-4f58-939b-fbe53506a978
---
Gabriel always wants the `less-permission-prompts` skill run to keep the settings.json allowlist current.

**Why:** Gabriel wants Claude to work without pausing for approval on routine read-only Bash/MCP calls. Permission friction slows multi-step work. He confirmed this on 2026-04-16 after I offered to run the skill.

**How to apply:**
- Offer to run `less-permission-prompts` proactively at the start of new projects or after a session with many permission prompts.
- When Gabriel says "set up this project" or "reduce friction," invoke this skill as part of the response.
- Does NOT mean bypass all permissions — only expands the allowlist for safe, read-only, already-used commands. Never adds destructive operations (rm, push --force, etc.) to the allowlist without explicit approval.
