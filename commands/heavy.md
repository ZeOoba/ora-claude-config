# /heavy

Quit the ~1.3 GB Claude desktop GUI and open a FRESH lean CLI session in the ORA workspace.

## Action (do this immediately, nothing else)
Run exactly this one Bash command. It spawns a DETACHED standalone PowerShell window that survives this GUI closing:

```
powershell -NoProfile -Command "Start-Process powershell -ArgumentList '-NoExit','-Command','heavy'"
```

Then tell the user, in one line: "A fresh lean CLI window is opening — it will close this GUI (~1.3 GB freed) and start a new session in your workspace." Do not wait for output; do not run anything else.

## How it works
- The detached window runs `heavy` from the PowerShell profile: it stops every Claude desktop process, then launches a fresh `claude` CLI session (~150 MB) in the ORA workspace.
- Use `/handoff` instead if you want to CONTINUE the current conversation rather than start fresh.
- This GUI session will end when the detached window quits it — that is expected.
