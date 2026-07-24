---
name: feedback-bash-unquoted-windows-paths-collapse
description: "Unquoted Windows backslash paths in a Bash command collapse silently — the INTERPRETER path breaks too, not just arguments; audit whole runbooks, not the one line that errored"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: fdaf1f4e-671e-48c1-a653-ddf0138a8150
  modified: 2026-07-24T16:26:20.867Z
---

In the Bash tool (Git Bash / POSIX sh) an **unquoted** backslash is an escape character, so any bare Windows path in a command word is destroyed before execution:
- `C:\Users\Owner\.claude\maintenance\x.py` → `C:UsersOwner.claudemaintenancex.py` → `Errno 2: No such file or directory`
- `C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe` → `C:WindowsSystem32WindowsPowerShellv1.0powershell.exe` → `command not found`

The non-obvious part: **quoting the `-File` argument does not save you — the interpreter path is its own command word.** A line like `C:\Windows\...\powershell.exe -File "C:\Users\...\x.ps1"` *looks* quoted and still fails. Fix: forward slashes, or double-quote every path including the interpreter.

**Why:** Found 2026-07-24 in `ora-task-integrity-guard/SKILL.md`. STEP 1.5's python lines had shipped 2026-07-16 with bare backslash script paths and had failed on first invocation *every run since* — each run's agent silently hand-corrected to forward slashes and moved on, so the defect never surfaced. On first fix I asserted "the PowerShell lines are safe because their paths sit inside double quotes"; testing that claim showed STEP 1, STEP 1.5 script 3, and the DRY-RUN line were all broken the same way. The one line that threw `Errno 2` was a third of the actual blast radius.

Testing gotcha that hid it: piping a failing command into `head`/`tail` returns the *pipe's* exit code, so a `command not found` reads as `EXIT=0` — see [[feedback_piped_gate_exit_masking]].

**How to apply:** When a documented command fails on a Windows path, do not fix only the line that errored — grep the whole runbook for every command literal and check the interpreter path too. When authoring any SKILL.md / runbook command for the Bash tool, write Windows paths forward-slashed or fully quoted. Distinct mechanism from [[feedback_sed_windows_path_escapes]] (that one is sed's replacement-string escape directives, this one is shell word escaping) — both silently corrupt rather than erroring loudly. A silently hand-corrected runbook command is invisible until someone runs it verbatim: agents patching around a broken instruction is itself the bug signal.
