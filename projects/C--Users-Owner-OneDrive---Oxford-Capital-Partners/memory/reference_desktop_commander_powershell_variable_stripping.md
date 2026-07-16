---
name: reference_desktop_commander_powershell_variable_stripping
description: "Desktop Commander's start_process silently strips $variable tokens from PowerShell -Command strings — confirmed engine-wide 2026-07-12 (live-reproduced from Code CLI, both DC connections); cmd.exe with literal paths works instead."
metadata:
  node_type: memory
  type: reference
  originSessionId: local_d974d26b-0ebe-48de-844c-1c7dcdbaea04
---

Desktop Commander's `start_process` (interpreter: `powershell` or `pwsh`, `-Command "..."`) silently
strips `$variable` tokens out of the command string before execution — not an escaping error, not a
thrown exception. The variable reference simply vanishes, so a command like
`powershell -Command "Copy-Item $src $dst"` runs with `$src`/`$dst` gone from the string entirely,
usually producing a confusing downstream failure (missing arg, wrong path, or a silent no-op) rather
than a clear "variable not found" signal. Confirmed twice, not a one-off fluke.

**Workaround:** drop to `cmd.exe` with **literal, fully-expanded paths** (no shell variables) instead
of PowerShell interpolation. This has worked cleanly both times the PowerShell path failed.

**Practical implication:** when a `start_process` PowerShell command needs to reference a path or value
computed earlier in the session, resolve it to a literal string yourself before building the command —
do not hand `$var`-bearing `-Command` strings to Desktop Commander and expect them to survive.

Not yet root-caused (quoting layer between the MCP host and the spawned PowerShell process is the
likely suspect) — flagging the workaround now so it doesn't cost time a third time, not asserting the
mechanism.

**Scope check (2026-07-12): CONFIRMED engine-wide** — live-reproduced from a Claude Code CLI session, not
just inferred from shared config metadata. Repro command:
`powershell -Command "$testVar = 'CANARY-12345'; Write-Output $testVar"` (plus two more variations —
two path variables, and a numeric variable) run via `start_process`, 3 clean runs, all 3 stripped
`$testVar`/`$srcPath`/`$dstPath`/`$myCounter` from the command string before execution, leaving PowerShell
parse errors like `= : The term '=' is not recognized...` (the token before the `=` — and the variable
after `Write-Output` — both gone). Zero clean runs printed the expected value. Same result from a Code
CLI session as the two prior confirmations (both from Cowork).

**Correction to the "one shared server" framing:** the prior evidence (single `clientId`, single
`version`, cumulative `usageStats`) was read as "one shared DC server/config across Code and Cowork."
That's only half right. A Code CLI session actually has **two distinct, independently-running DC server
processes** reachable, not one:
- `mcp__Desktop_Commander__*` — the `.mcpb` **Desktop Extension**, `isDXT: true`, runs under the Claude
  Desktop app's bundled Electron/Node (`...Claude_1.20186.1.0.../Claude.exe`). Observed 2026-07-12 from
  Code CLI: `version 0.2.44`, `currentClient: {"name":"local-agent-mode-Desktop Commander","version":
  "1.0.0"}` — i.e. its `currentClient` field still shows the last Cowork/LAMS connection, not this Code
  session.
- `mcp__plugin_desktop-commander_desktop-commander__*` — the **Claude Code plugin** form, `isDXT: false`,
  runs under a separate system Node (WinGet install). Observed same moment: `version 0.2.45`,
  `currentClient: {"name":"claude-code","version":"2.1.205"}` — matching what the 2026-07-12 Cowork
  check assumed was "the" shared config.
- Both share the same `clientId` (`14a3bf63-…`) — that's a **persisted config value** (written to a
  shared config store/file on disk), not proof of one live process. Version numbers differ (0.2.44 vs
  0.2.45) and `currentClient` differs between them, confirming these are two separate running servers,
  not one.
- The `$var`-stripping bug reproduces **identically on both** — so the distinction doesn't matter for
  this bug's practical scope, but it does mean the earlier "single shared server" inference was
  imprecise and shouldn't be reused as-is for other scope questions. Open follow-up (not yet done): the
  "Extension host serves Cowork/LAMS, plugin form serves Code only" framing in
  [reference_desktop_commander_extension_slow_init.md](reference_desktop_commander_extension_slow_init.md)
  looks incomplete too — the Extension (`mcp__Desktop_Commander__*`) is clearly reachable from a Code CLI
  session (I called it directly above), just not the one Code's plugin config defaults to.

**Bottom line:** the `cmd.exe`-with-literal-paths workaround applies everywhere `start_process` builds a
PowerShell `-Command` string with a `$variable` — any surface (Code or Cowork), either DC connection.
No surface- or connection-specific carve-out.

**Related, distinct bug (2026-07-12):** a nested-double-quote `cmd.exe /c "..."` command (not a
`$variable` at all) also silently mangled an argument mid-session — see
[reference_desktop_commander_nested_quote_mangling.md](reference_desktop_commander_nested_quote_mangling.md).
Same suspect family (the MCP-host-to-shell quoting layer), confirmed only once so far — kept as a
separate note rather than merged into this one since the trigger condition differs.
