---
name: reference_desktop_commander_nested_quote_mangling
description: "Desktop Commander's start_process mangled a nested-double-quote cmd.exe /c command (silently injected a leading space into a quoted path argument) — confirmed once, 2026-07-12. Same quoting-layer family as the PowerShell $var-stripping bug but a distinct symptom; workaround is to write the command to a .bat file and execute that instead of inlining nested quotes."
metadata:
  node_type: memory
  type: reference
  originSessionId: local_d974d26b-0ebe-48de-844c-1c7dcdbaea04
---

**Confirmed once (2026-07-12), not yet twice** — logged now per Gabriel's instruction so the next
occurrence is recognized immediately rather than re-diagnosed from scratch. Promote to "confirmed
recurring" framing (like
[reference_desktop_commander_powershell_variable_stripping.md](reference_desktop_commander_powershell_variable_stripping.md))
if it happens again.

## What happened

A `start_process` call of the form:

```
cmd.exe /c "cd /d C:\Users\Owner\ora-skills && python tools\package_skills.py "C:\Users\Owner\AppData\...\outputs" parcel-data-recovery"
```

— i.e. an outer `cmd.exe /c "..."` wrapper containing a second, nested pair of double quotes around a
path argument — silently mis-parsed. The Python script received the path argument with a **leading
space** injected into it, producing:

```
OSError: [WinError 123] The filename, directory name, or volume label syntax is incorrect: ' C:\Users\Owner\AppData\Roaming\Claude\local-agent-mode-sessions\...\outputs'
```

Note the leading space before `C:`. No error or warning was raised at the `start_process` call itself —
the command "ran" and produced a real, wrong error string, no different in kind from the $var-stripping
bug's failure mode (confusing downstream failure rather than an upfront rejection).

## Suspected mechanism (not confirmed)

The outer `cmd.exe /c "..."` string and the inner quoted path both use `"`, so cmd's own quote-nesting
rules (and/or the MCP host's argument-passing layer) likely closed the outer string early or re-tokenized
around the inner quotes, corrupting the argument rather than rejecting the command outright. This is
plausibly the same "quoting layer between the MCP host and the spawned process" suspect named in the
PowerShell `$var` note, but the trigger condition here (nested `"..."` depth) is mechanically different
from that one (`$variable` interpolation), so treat them as two symptoms worth tracking separately until
there's evidence they share a root cause.

## Workaround (worked cleanly)

Don't inline a command with nested double quotes. Instead:
1. `write_file` the full command to a `.bat` (or `.ps1`) file — plain literal paths, no nested quoting
   inside the file itself, since each argument is on its own line/context.
2. `start_process` that script file directly (e.g. `cmd.exe /c C:\path\to\script.bat`), with no quotes
   needed around the invocation at all.
3. Delete the temp script file after use.

This has now worked once (packaging `parcel-data-recovery.skill` via `tools\package_skills.py`).

## Practical implication

Any Desktop Commander shell command that needs a quoted argument INSIDE an already-quoted wrapper
(`cmd.exe /c "... "arg with spaces" ..."`, or the PowerShell equivalent) is suspect. Prefer: (a) commands
with no spaces in any argument (so quoting is unnecessary), or (b) writing the command to a script file
and executing the file, over (c) hand-nesting quotes in a single inline command string.
