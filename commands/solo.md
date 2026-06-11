# /solo

Hand off THIS session to a lean CLI **without closing the desktop GUI or any other running session**. Use this when you have multiple sessions open and only want to move this one.

## Action (do this immediately, nothing else)
Run exactly this one Bash command. It reads this session's id and spawns a DETACHED standalone PowerShell that moves only this session:

```
SID="$CLAUDE_CODE_SESSION_ID"; powershell -NoProfile -Command "Start-Process powershell -ArgumentList '-NoExit','-Command','handoff-solo $SID'"
```

Then tell the user, in one line: "A lean CLI window is opening — it will move ONLY this session (freeing ~130 MB) and leave the desktop and your other sessions running. Continue there." Do not wait for output; do not run anything else.

## How it works
- The detached window runs `handoff-solo <this-session-id>`: it kills ONLY this session's own GUI child process (matched by the unique session id), then runs `claude --resume <id>` to resume the conversation in a ~150 MB CLI window.
- The Electron shell and every other session keep running untouched. Killing by session-id UUID can never hit the shell or another session.
- Run `/solo` in each session you want to move — they each move independently.
- This session's GUI tab becomes orphaned once its process is killed; close that one tab when convenient.
- To instead reclaim the full ~1.3 GB by closing the WHOLE app, use `/handoff` (resume this one) or `/heavy` (fresh) — but those close all sessions.
