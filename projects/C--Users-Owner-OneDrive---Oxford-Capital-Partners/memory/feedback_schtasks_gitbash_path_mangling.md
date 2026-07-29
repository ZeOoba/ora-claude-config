---
name: schtasks-gitbash-path-mangling
description: schtasks is unusable from the Bash tool — MSYS path conversion mangles /Create-style flags into file paths; use PowerShell cmdlets (Register-ScheduledTask etc.) instead
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 46a85dfc-a400-4abf-91ca-96d829f85eca
  modified: 2026-07-29T18:55:44.339Z
---

`schtasks /Create /TN "..." ...` fails from the Bash tool with `ERROR: Invalid argument/option - 'C:/Program Files/Git/Create'` — Git Bash's MSYS path conversion rewrites the leading-slash flags (`/Create`, `/TN`, `/SC`) into filesystem paths before schtasks ever sees them. Hit live 2026-07-29 registering "ORA Fleet Heartbeat Push" (Phase-2 T6).

**Why:** MSYS2 argument conversion treats `/Word` tokens as POSIX paths and prefixes the Git installation root. Quoting doesn't reliably help; `MSYS_NO_PATHCONV=1` is shell-wide and easy to forget.

**How to apply:** never call `schtasks` from the Bash tool. Use the native PowerShell cmdlets via `powershell.exe -NoProfile -Command` — `New-ScheduledTaskAction`/`-Trigger`/`-SettingsSet` + `Register-ScheduledTask` (worked first try for the same task). For backbone-task restore specifically, don't hand-register at all: `maintenance/register-windows-backbone.ps1` restores all six from git-tracked XML snapshots. Related: [[bash-unquoted-windows-paths-collapse]], [[sed-windows-path-escapes]].
