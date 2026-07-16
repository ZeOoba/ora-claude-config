---
name: reference_desktop_commander_extension_slow_init
description: "The Claude Desktop \"Desktop Commander\" extension \"Unable to connect to extension server\" banner is usually a slow cold-start timeout, not a real failure — re-enable and wait 60s."
metadata: 
  node_type: memory
  type: reference
  originSessionId: dde67844-b05d-4f51-864c-ce44962927bf
---

Desktop Commander installed as a **Claude Desktop extension** (`.mcpb`, Settings → Extensions; dir `AppData/Roaming/Claude/Claude Extensions/ant.dir.gh.wonderwhy-er.desktopcommandermcp/`) can show a red **"Unable to connect to extension server. Please try disabling and re-enabling the extension."** banner even when the server actually comes up.

Root cause (observed 2026-07-09, fresh install): the server's `initialize` took **~36 seconds** on cold start (log `AppData/Roaming/Claude/logs/mcp-server-Desktop Commander.log` shows `Server started and connected successfully` then `initialize → result` ~36s later, and `tools/list` returning fine). Claude Desktop's connection banner times out well before that, so it reports failure while the server is still warming up.

**Fix:** toggle the extension Enabled off → wait ~5s → on (the banner's own suggestion), **then wait a full 60s before judging** — do not rapid-toggle. If it persists, fully quit Claude Desktop from the system tray and relaunch (the server spawns on app start). Node runtime is fine — it uses Claude Desktop's built-in Node (v24.18 present on this machine anyway).

**Only if it still won't connect after a clean quit-and-relaunch + 60s:** look for a stuck extension `node.exe` or reinstall the `.mcpb`.

Context: this extension is what serves the **Cowork / LAMS scheduled fleet** (the Claude Code *plugin* form of DC does not load in remote/headless scheduled Cowork runs — see [tech.md]). Cowork local-vs-remote MCP behavior detail: the plugin form won't load in remote/headless scheduled runs; the Desktop extension is bridged in by Claude Desktop's SDK layer.

**Correction (2026-07-12, live-verified):** the framing above previously read "the plugin form serves the
Code surface only," implying the Extension was Cowork/LAMS-exclusive and unreachable from Code. That's
wrong. A Code CLI session on this machine has **both** DC connections live simultaneously and both are
directly callable:
- `mcp__Desktop_Commander__*` — this Extension (`.mcpb`, `isDXT:true`) — confirmed reachable from Code CLI
  by direct call (`get_config`, `start_process`, `force_terminate` all succeeded from a Code session,
  2026-07-12).
- `mcp__plugin_desktop-commander_desktop-commander__*` — the Claude Code plugin (`isDXT:false`) — Code-only,
  as previously documented.

"Having both installed does not conflict (separate hosts)" undersold it — it's not just non-conflicting,
Code actively has both as usable tool namespaces at once. One trap this creates: the Extension's
`currentClient` field (via `get_config`) is **last-connection-wins**, not "who's asking right now" — when
called from a Code CLI session it still reported the prior Cowork/LAMS connection's identity
(`local-agent-mode-Desktop Commander`/`1.0.0`), not Code's. Don't use `currentClient` on the Extension
connection alone to infer which surface is currently active; check which tool-name prefix was called
instead. Cross-ref: [reference_desktop_commander_powershell_variable_stripping.md](reference_desktop_commander_powershell_variable_stripping.md)
(the `$var`-stripping bug repro that surfaced this).
