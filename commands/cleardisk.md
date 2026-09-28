# /cleardisk

Quit the Claude desktop GUI and reclaim regenerable npm/CLI disk caches (up to ~2.5 GB).

## Action (do this immediately, nothing else)
Run exactly this one Bash command. It spawns a DETACHED standalone PowerShell window that quits the GUI, then clears the caches:

```
powershell -NoProfile -Command "Start-Process powershell -ArgumentList '-NoExit','-Command','Stop-ClaudeGui; clear-disk'"
```

Then tell the user, in one line: "A window is opening — it will close this GUI and reclaim npm/CLI disk caches (the Outlook bridge is preserved)." Do not wait for output; do not run anything else.

## How it works
- The detached window runs `Stop-ClaudeGui` (frees ~1.3 GB), then `clear-disk` from the PowerShell profile.
- `clear-disk` clears the npm content cache and deletes non-core `_npx` CLI dirs, while PRESERVING the Outlook/`mcp-remote` bridge so it is not re-downloaded.
- Removed CLI tools (netlify, supabase, wrangler, etc.) simply re-fetch on next use — nothing breaks.
- This GUI session will end when the detached window quits it — that is expected.

## See also
For the LAMS/Cowork session-store's own disk growth (`audit.jsonl`, unrelated to the npm/CLI caches above and safe to run alongside live work, no GUI quit needed), use `/cleardisk-sessions` instead.
