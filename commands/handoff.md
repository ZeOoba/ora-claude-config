# /handoff

Transfer THIS conversation to a lean CLI session and quit the ~1.3 GB Claude desktop GUI.

## Action (do this immediately, nothing else)
Run exactly this one Bash command. It spawns a DETACHED standalone PowerShell window that survives this GUI closing:

```
powershell -NoProfile -Command "Start-Process powershell -ArgumentList '-NoExit','-Command','handoff'"
```

Then tell the user, in one line: "A lean CLI window is opening — it will close this GUI (~1.3 GB freed) and resume this exact conversation. Continue there." Do not wait for output; do not run anything else.

## How it works
- The detached window runs `handoff` from the PowerShell profile: it stops every Claude desktop process, then runs `claude --continue` to resume this conversation in a ~150 MB CLI window.
- Resumes Claude **Code** conversations in this workspace. Outlook (composio) stays in the GUI by design.
- This GUI session will end when the detached window quits it — that is expected.
