---
name: event-log-app-handle-lock
description: "Claude.exe (Desktop app) can hold event_log.md open for tens of minutes then self-release, blocking append-event-log.py's atomic os.replace while direct writes still work — the appender now self-heals via a built-in in-place fallback (2026-07-16)"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 1a905dab-bee0-465f-b364-7beeecd61271
---

Diagnosed 2026-07-16: `append-event-log.py` spooled every append for ~10 minutes (5 entries from 3+ sessions queued in `event_log.md.pending/`). Restart Manager identified the holder as **Claude.exe itself** (the Desktop app process, same pid/start-time across two re-checks minutes apart) — it held a read handle on `event_log.md` without FILE_SHARE_DELETE, which blocks `os.replace` (the appender's atomic-rename step) but NOT plain reads or in-place writes.

**Follow-up finding (same day, ~25 min later): the lock SELF-CLEARED**, no app restart. A fresh Restart Manager query on `event_log.md`, `MEMORY.md`, and `CLAUDE.md` all showed 0 holders, and a live append succeeded via the plain atomic path with zero retries. So this is a **transient** hold (some internal reader — plausibly the app's own live file-change-detection tailing memory/, given the "note: file was modified" reminders sessions see for this exact directory — eventually closes its handle), not a standing one requiring intervention. Revises the earlier "likely on app restart" guess in this file's first version.

**Hardening shipped 2026-07-16** (this was itself validated live: within ~2 minutes of landing, a concurrent session's append hit a real transient lock and used the new fallback for real — zero data loss, correct newest-first ordering, confirmed by diffing the resulting `.inplace-backup` against the current log). `append-event-log.py` no longer needs manual intervention for this failure mode:
- `_inplace_insert()`: same mtime-guard as the atomic path, PLUS a pre-write backup (`event_log.md.inplace-backup`, gitignored, overwritten each use — recoverable via the log's own git history anyway) and a post-write read-back verify.
- `_insert_or_inplace()`: tries the atomic path first; on any non-`ValueError` failure, if `try_inplace` is set, falls back to `_inplace_insert()`.
- Both the `main()` retry loop (6 attempts) and `drain_spool()`'s loop now pass `try_inplace=True` once `INPLACE_FALLBACK_AFTER` (3) failed atomic attempts have elapsed — spooling is now the last resort only when BOTH paths fail.
- TDD in `test-append-event-log.py`: reproduces the exact failure via `ctypes.CreateFileW` opened without `FILE_SHARE_DELETE` (pure stdlib, no pywin32) — confirms `os.replace` genuinely blocks under this hold, `_inplace_insert` succeeds through it, `try_inplace=False` still propagates (regression guard), malformed entries still raise `ValueError` immediately even under lock, and an end-to-end `main()` run under a full-duration lock appends via fallback with **zero spooling**.

**Residual manual procedure** (only needed if BOTH the atomic AND in-place paths fail — e.g. a genuinely read-only mount, not this failure mode): identify the holder via Restart Manager (RmStartSession/RmRegisterResources/RmGetList via PowerShell Add-Type), then drain by hand following the same backup + mtime-guard + verify discipline the code now automates. The spool mechanism itself is working as designed — never bypass it by hand-editing the log header. Related: [[feedback-append-event-log-stdin-encoding]].
