---
name: obsidian-fleet-mirror
description: Live view of Claude scheduled-task fleet + in-session activity inside the Obsidian BrainVault
metadata: 
  node_type: memory
  type: reference
  originSessionId: 23942e61-2f8c-490c-b912-83f26dbf7aeb
---

Built 2026-06-03. Mirrors Claude task state into the Obsidian vault `C:\Users\Owner\Obsidian\BrainVault\_Claude\` (Obsidian live-renders files on disk change). Two feeds + a dashboard:

- **`Claude Fleet.md`** — the scheduled-task fleet. Written by `C:\Users\Owner\.claude\obsidian-fleet-mirror\write-fleet.ps1`, run every 60s by the **Windows Task Scheduler job `ClaudeFleetMirror`** (launched hidden via `run-hidden.vbs`). Reads the canonical LAMS `scheduled-tasks.json` directly (hardcoded path + auto-discovery fallback if the session UUID rotates) — NOT the `scheduled-tasks` MCP. See [[reference_tech]] for the registry path.
- **`Claude Session Tasks.md`** — in-session activity (active sessions working/idle + feed of background-Bash & subagent dispatches). Written by `C:\Users\Owner\.claude\hooks\fleet-session-hook.py`, wired into `~\.claude\settings.json` hooks on SessionStart / Stop / SessionEnd / PostToolUse(matcher `Bash|Task`), all `async:true`. State in `obsidian-fleet-mirror\session-state.json`.
- **`Claude Tasks.md`** — dashboard transcluding both.

Full docs + removal/re-register steps: `C:\Users\Owner\.claude\obsidian-fleet-mirror\README.md`. To remove: `Unregister-ScheduledTask -TaskName 'ClaudeFleetMirror' -Confirm:$false` + delete the folder, the `_Claude` vault folder, the hook .py, and the 4 `fleet-session-hook` entries in settings.json.
