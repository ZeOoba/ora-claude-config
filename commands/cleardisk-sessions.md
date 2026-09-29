# /cleardisk-sessions

Reclaim disk from the LAMS/Cowork session store's per-session `audit.jsonl` growth (98 files / 102 MB measured 2026-09-18, growing ~950 MB/quarter unattended) — the gap `/cleardisk` doesn't cover, since that command only clears npm/CLI caches and requires quitting the GUI first. This one does NOT require quitting the GUI and is safe to run alongside live work: it only ever touches `audit.jsonl` files whose mtime is 30+ days old (a live/recent session is never eligible), skips anything still locked by another process, and archives (gzip, verified byte-for-byte round-trip) before removing the original rather than deleting outright. Full safety model is in the script's own docstring — `C:\Users\Owner\.claude\maintenance\audit-log-sweep.py`. The unattended monthly counterpart is the `ora-audit-log-sweep` scheduled task (registered 2026-09-18); this command is for an on-demand check or reclaim in between its fires.

## Action

**Default (no argument) — DRY RUN, report only, nothing is touched.** Run exactly:
```
C:/Users/Owner/AppData/Local/Programs/Python/Python313/python.exe C:\Users\Owner\.claude\maintenance\audit-log-sweep.py
```
Read the JSON it prints and tell the user, in a couple lines: how many `audit.jsonl` files were scanned, how many are eligible (30+ days untouched), and how many MB that represents (`bytes_reclaimed` will be 0 in dry-run — report `eligible` and compute their size from the file listing if you want an MB figure, or just tell the user to pass `apply` to see the real reclaim). Do not archive anything yet.

**With the argument `apply`** (i.e. invoked as `/cleardisk-sessions apply`) — actually reclaim. Run exactly:
```
C:/Users/Owner/AppData/Local/Programs/Python/Python313/python.exe C:\Users\Owner\.claude\maintenance\audit-log-sweep.py --apply
```
Report the same numbers back, now with the real `archived` count and `bytes_reclaimed`. If `errors` is non-empty, show it verbatim — do not paraphrase or drop it.

Do not run with any other flag, and do not improvise a different sweep — this command exists specifically so reclaiming this one store doesn't require re-deriving the safe-bucket logic from scratch each time.

## Scope note

This does NOT touch `claude-code-sessions` (the CC/MCP fleet's own store) — that store carries no `audit.jsonl` files as of 2026-09-18, so the script doesn't scan it. It also never touches anything in a session directory besides `audit.jsonl` itself (transcripts, SKILL.md copies, other state are left alone). For npm/CLI cache reclaim, use `/cleardisk` instead — the two are independent and either can run without the other.
