#!/usr/bin/env python3
"""Collision-safe newest-first appender for memory/event_log.md.

WHY (2026-06-11): three concurrent sessions (Code x2 + Cowork handbacks) anchoring
Edit-tool replacements on the same event_log.md header produced three stale-anchor
collisions in one day. This helper makes the append a one-command operation with an
mtime-compare retry loop and an atomic os.replace — concurrent writers serialize
instead of erroring.

CONVENTION (single-writer doctrine, 2026-06-11): any session may APPEND an entry via
this script; only ONE session at a time should do structural edits (consolidation,
rollover) to the log. Entries must start with a dated '## YYYY-MM-DD — ' header and
are inserted as the NEWEST entry (directly above the first existing '## ').

Usage:
  python append-event-log.py --entry-file path\\to\\entry.md
  echo "## 2026-06-12 — title" | python append-event-log.py        (stdin)
Exit 0 = appended (header echoed), or SPOOLED for auto-drain when the log is locked
(the entry is parked under <log>.pending/ and replayed on the next run -- never lost).
Exit 1 = failed to BOTH append and spool.

SPOOL (2026-07-08): an OS file-handle lock (another process holding event_log.md open)
survives the mtime-retry loop and used to drop the append entirely. Now a run first
DRAINS any parked entries, then appends; if the lock never clears it SPOOLS the new
entry (oldest-first replay preserves newest-on-top order).
"""
import argparse
import os
import sys
import time

LOG = os.path.join(os.path.expanduser("~"), ".claude", "projects",
                   "C--Users-Owner-OneDrive---Oxford-Capital-Partners",
                   "memory", "event_log.md")


def insert_newest(content, entry):
    """Insert `entry` (must start '## ') above the first existing '## ' entry,
    skipping YAML frontmatter so a '## ' inside it is never used as the anchor.
    No existing entries -> append at end. Pure function."""
    if not entry.startswith("## "):
        raise ValueError("entry must start with a dated '## ' header")
    entry = entry.rstrip()
    body_start = 0
    if content.startswith("---\n"):
        end = content.find("\n---\n", 4)
        if end != -1:
            body_start = end + len("\n---\n")
    idx = None
    if content.startswith("## ", body_start):
        idx = body_start
    else:
        found = content.find("\n## ", body_start)
        if found != -1:
            idx = found + 1
    if idx is None:
        return content.rstrip() + "\n\n" + entry + "\n"
    return content[:idx].rstrip() + "\n\n" + entry + "\n\n" + content[idx:]


def spool_dir_for(log):
    """Directory holding entries that could not be written yet (lock contention)."""
    return log + ".pending"


def spool_entry(log, entry, now_ns):
    """Durably park `entry` for later draining. Filename is monotonic (ns) so a later
    drain replays oldest-first. Returns the spooled path."""
    d = spool_dir_for(log)
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, "%d.md" % now_ns)
    with open(p, "w", encoding="utf-8") as f:
        f.write(entry)
    return p


def _atomic_insert(log, entry):
    """One mtime-guarded read + newest-first insert + atomic replace. Returns True on
    success; raises on lock/other error (caller decides retry/spool)."""
    st_before = os.stat(log).st_mtime_ns
    with open(log, encoding="utf-8") as f:
        content = f.read()
    new = insert_newest(content, entry)
    if os.stat(log).st_mtime_ns != st_before:
        raise BlockingIOError("log changed mid-read")
    tmp = log + ".tmp-append"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(new)
    os.replace(tmp, log)  # atomic on the same volume
    return True


def drain_spool(log, attempts=3):
    """Replay spooled entries (oldest-first) into `log`. Stops at the first one that
    still can't be written -- leaves it and the rest for next time (nothing is lost).
    A malformed spooled entry is discarded so it can't wedge the queue forever.
    Returns the count successfully drained."""
    d = spool_dir_for(log)
    if not os.path.isdir(d):
        return 0
    drained = 0
    for name in sorted(n for n in os.listdir(d) if n.endswith(".md")):
        p = os.path.join(d, name)
        try:
            with open(p, encoding="utf-8") as f:
                entry = f.read().strip()
        except Exception:
            continue
        done = False
        for attempt in range(attempts):
            try:
                _atomic_insert(log, entry)
                done = True
                break
            except ValueError:  # malformed -> discard, don't wedge the queue
                done = True
                break
            except Exception:
                time.sleep(0.2 * (attempt + 1))
        if not done:
            break  # lock still held -- retry this + the rest on a later run
        try:
            os.remove(p)
        except Exception:
            pass
        drained += 1
    return drained


def main(argv=None):
    # Windows consoles default to cp1252; entries routinely contain em-dashes / arrows / box
    # glyphs. Reconfigure the std streams to UTF-8 so the success + diagnostic prints never raise
    # UnicodeEncodeError AFTER the atomic write has already succeeded (which would mask a good
    # append with a non-zero exit and break `&&` caller chains).
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except Exception:
            pass
    ap = argparse.ArgumentParser(description="Append a newest-first event_log entry.")
    ap.add_argument("--entry-file", help="file holding the entry markdown; stdin if omitted")
    ap.add_argument("--log", default=LOG, help="target log (default: canonical event_log.md)")
    a = ap.parse_args(argv)
    if a.entry_file:
        with open(a.entry_file, encoding="utf-8") as f:
            entry = f.read()
    else:
        entry = sys.stdin.read()
    entry = entry.strip()
    if not entry:
        sys.stderr.write("empty entry\n")
        return 1

    header = entry.splitlines()[0]

    # Drain anything parked by a prior locked run first, so pending entries land as
    # soon as the lock clears. They are older than this new entry, so they end up
    # below it (newest-on-top preserved).
    try:
        n = drain_spool(a.log)
        if n:
            print("drained %d spooled entr%s" % (n, "y" if n == 1 else "ies"))
    except Exception as e:
        sys.stderr.write("spool drain skipped: %s\n" % e)

    for attempt in range(6):
        try:
            _atomic_insert(a.log, entry)
            with open(a.log, encoding="utf-8") as f:
                if header in f.read():
                    print("appended: %s" % header)
                    return 0
        except ValueError:
            raise
        except Exception as e:
            sys.stderr.write("attempt %d: %s — retrying\n" % (attempt + 1, e))
        time.sleep(0.25 * (attempt + 1))

    # Lock never cleared: park the entry instead of losing it. It drains on the next
    # run (2026-07-08 -- a held event_log.md handle used to drop the append entirely).
    try:
        p = spool_entry(a.log, entry, time.time_ns())
        sys.stderr.write("SPOOLED to %s — log locked; will auto-drain next run.\n" % p)
        print("spooled (log locked): %s" % header)
        return 0
    except Exception as e:
        sys.stderr.write("FAILED to append AND to spool (%s) — append manually.\n" % e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
