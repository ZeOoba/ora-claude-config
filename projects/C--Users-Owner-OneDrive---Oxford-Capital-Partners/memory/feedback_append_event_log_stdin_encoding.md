---
name: feedback-append-event-log-stdin-encoding
description: "append-event-log.py via a Bash heredoc piped to stdin mangles UTF-8 special characters (em-dashes, curly quotes) on this Windows machine — use --entry-file instead"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: a343c022-5606-4707-bfe3-198ca99c7ef4
---

Never pipe a heredoc containing UTF-8 special characters (em-dashes —, curly quotes, etc.) to `python maintenance/append-event-log.py` via stdin (`cat << 'EOF' | python append-event-log.py`) on this machine. Python's stdin decoding on Windows defaults to the console codepage (cp1252), not UTF-8, unless `PYTHONUTF8=1`/`PYTHONIOENCODING=utf-8` is set. An em-dash's correct UTF-8 bytes (`\xe2\x80\x94`) get misread as three separate cp1252 characters (â, €, ") and re-encoded as UTF-8 on write — genuine mojibake landing in the committed `event_log.md`, not just a display artifact.

**Why this matters:** this corrupted a live append to `event_log.md` on 2026-07-08 (16 mangled em-dash sequences in one entry) and was only caught by an independent post-write verification pass (reading the file back and spot-checking raw bytes), not by the append script itself — `append-event-log.py` has no encoding-integrity check on what it writes.

**How to apply:** write the entry to a UTF-8-encoded temp file first (e.g. via the `Write` tool, which handles encoding correctly) and pass it with `append-event-log.py --entry-file <path>` instead of piping through stdin. If stdin must be used for some reason, verify the result immediately afterward by reading the raw bytes around any non-ASCII character (`open(path,'rb').read()`) before trusting the append — do not just trust the script's "appended: ..." confirmation line, which itself is subject to the same corruption and can look plausible even when wrong.

See also [[feedback_sed_windows_path_escapes]] for a related Windows-shell-encoding class of gotcha (different tool, same root cause: this machine's default console/shell encoding is not UTF-8).
