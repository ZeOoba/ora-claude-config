# Obsidian Fleet Mirror

Live view of Claude tasks inside the Obsidian **BrainVault** (`C:\Users\Owner\Obsidian\BrainVault\_Claude\`).
Built 2026-06-03. Obsidian live-renders any vault file the instant it changes on disk, so the whole
design is just "write task state to a markdown file → Obsidian shows it."

## Two feeds

### A. Scheduled fleet  →  `_Claude\Claude Fleet.md`
- `write-fleet.ps1` reads the canonical LAMS registry (`scheduled-tasks.json`) and renders a markdown table.
- Driven by Windows Task Scheduler job **`ClaudeFleetMirror`** every 60s, via `run-hidden.vbs` (no window flash).
- Registry path is hardcoded but auto-discovers the newest non-empty `scheduled-tasks.json` under the LAMS
  root if the session UUID rotates. Reads the registry FILE directly — NOT the `scheduled-tasks` MCP
  (which points at the emptied claude-code-sessions registry and returns 0).

### B. In-session activity  →  `_Claude\Claude Session Tasks.md`
- `..\hooks\fleet-session-hook.py` runs on SessionStart / Stop / SessionEnd / PostToolUse(Bash|Task)
  (wired in `~\.claude\settings.json`, all `async:true` so they never slow a tool call).
- Shows active sessions (working vs idle) + a feed of background-Bash launches and subagent dispatches.
- State persisted in `session-state.json`. It is an activity mirror, not a precise "executing now" probe.

### Dashboard  →  `_Claude\Claude Tasks.md`
Transcludes both notes onto one page. Pin it in Obsidian for an always-on view.

## Remove everything
```powershell
Unregister-ScheduledTask -TaskName 'ClaudeFleetMirror' -Confirm:$false
```
Then delete this folder, the `_Claude` folder in the vault, the `fleet-session-hook.py` file, and the four
`fleet-session-hook` entries in `~\.claude\settings.json` (Stop + SessionEnd keys, and the appended
SessionStart / PostToolUse[Bash|Task] entries).

## Re-register the scheduled task
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Users\Owner\.claude\obsidian-fleet-mirror\register-task.ps1"
```
