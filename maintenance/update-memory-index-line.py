#!/usr/bin/env python3
"""Collision-safe single-line upsert for MEMORY.md (and similar memory index files).

WHY (2026-08-16): memory/ has no single-writer protocol -- flagged in
reference_memory_dir_not_in_single_writer_list_2026-08-14.md and deliberately
deferred to "next ora-setup-audit" rather than fixed ad hoc. In the meantime,
sessions doing a plain Read + Edit on MEMORY.md race: session A reads, session B
reads the same pre-edit content, both write back their own full-file snapshot,
and whichever writes LAST silently clobbers the other's lines -- no error, no
merge conflict, just a disappeared pointer. Observed live the same day: one
Automation Audit index line was dropped and manually re-added at least three
times in a single session by different concurrent writers.

Mirrors append-event-log.py's proven concurrency-safety pattern -- mtime-guarded
fresh read immediately before write, atomic os.replace with an in-place fallback
for the case where another process holds a blocking read handle, bounded retry
with backoff -- generalized from "insert the newest dated entry" to "upsert any
single line matched by a regex". Does not attempt event_log.md's cross-run disk
spool (a MEMORY.md pointer line is not irreplaceable history the way a dated
event-log entry is): on total failure after retries it prints the exact target
line so the caller can apply it by hand rather than silently losing it.

Usage:
  python update-memory-index-line.py --file MEMORY.md --match '<regex>' --line '<new line text>' [--anchor-after '<regex>']

  --match         Regex matched against existing lines (re.search, not anchored).
                   If found, that line is REPLACED with --line, in place.
  --anchor-after  If --match finds nothing, --line is inserted as a new line
                   immediately after the first line matching this regex. Required
                   whenever the target line might not exist yet -- omitting it and
                   having --match miss is a hard error, not a silent append at EOF.
  --line          The full replacement/new line text (no trailing newline needed).

Exit 0 = written, or the target line was already byte-identical (nothing to do).
Exit 1 = failed after retries -- prints the exact line for manual application.
"""
import argparse
import os
import re
import sys
import time


def upsert_line(content: str, match_re: str, new_line: str, anchor_after_re: str = None):
    """Replace the first line matching match_re with new_line, or if none matches,
    insert new_line immediately after the first line matching anchor_after_re.
    Returns (new_content, changed: bool). Pure function -- no I/O.

    Raises ValueError if match_re finds nothing AND either anchor_after_re is not
    given or it also finds nothing -- callers must know where a genuinely new line
    belongs; silently appending at end-of-file is exactly the kind of surprise
    this tool exists to avoid."""
    new_line = new_line.rstrip("\n")
    lines = content.split("\n")
    match_pat = re.compile(match_re)
    for i, ln in enumerate(lines):
        if match_pat.search(ln):
            if ln == new_line:
                return content, False
            lines[i] = new_line
            return "\n".join(lines), True
    if not anchor_after_re:
        raise ValueError(
            "no line matched --match, and no --anchor-after was given to place a new line"
        )
    anchor_pat = re.compile(anchor_after_re)
    for i, ln in enumerate(lines):
        if anchor_pat.search(ln):
            lines.insert(i + 1, new_line)
            return "\n".join(lines), True
    raise ValueError("neither --match nor --anchor-after matched any existing line")


def _write_atomic(path: str, content: str):
    tmp = path + ".tmp-upsert"
    try:
        with open(tmp, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
        os.replace(tmp, path)
    except Exception:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise


def _write_inplace(path: str, content: str):
    """Fallback for when os.replace is blocked by another process holding `path`
    open (same class of issue as event_log.md's app-handle-lock finding). Backs
    up first, writes in place, reads back to verify -- never trusts a silent
    corruption as success."""
    backup = path + ".inplace-backup"
    with open(path, encoding="utf-8") as f:
        original = f.read()
    with open(backup, "w", encoding="utf-8", newline="\n") as f:
        f.write(original)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    with open(path, encoding="utf-8") as f:
        written = f.read()
    if written != content:
        raise IOError("in-place write verify mismatch -- backup at %s" % backup)
    try:
        os.remove(backup)
    except OSError:
        pass


def _attempt(path: str, match_re: str, new_line: str, anchor_after_re: str, try_inplace: bool):
    """One mtime-guarded read + upsert + write. Returns True if written, False if
    already up to date (nothing written). Raises on lock/race/malformed input."""
    st_before = os.stat(path).st_mtime_ns
    with open(path, encoding="utf-8") as f:
        content = f.read()
    if os.stat(path).st_mtime_ns != st_before:
        raise BlockingIOError("file changed mid-read")
    new_content, changed = upsert_line(content, match_re, new_line, anchor_after_re)
    if not changed:
        return False
    try:
        _write_atomic(path, new_content)
    except ValueError:
        raise
    except Exception as atomic_exc:
        if not try_inplace:
            raise
        # Re-read + re-upsert against current content before the fallback write --
        # the atomic attempt above may have failed AFTER a concurrent writer's own
        # change landed, and writing the stale `new_content` would silently revert it.
        with open(path, encoding="utf-8") as f:
            fresh = f.read()
        new_content2, changed2 = upsert_line(fresh, match_re, new_line, anchor_after_re)
        if not changed2:
            return False
        try:
            _write_inplace(path, new_content2)
        except Exception:
            raise atomic_exc
    return True


def main(argv=None):
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except Exception:
            pass
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--file", required=True, help="path to the memory index file to edit")
    ap.add_argument("--match", required=True, help="regex matching the existing line to replace")
    ap.add_argument("--line", required=True, help="full replacement/new line text")
    ap.add_argument("--anchor-after", default=None,
                    help="regex to insert after when --match finds nothing")
    a = ap.parse_args(argv)

    if not os.path.isfile(a.file):
        sys.stderr.write("no such file: %s\n" % a.file)
        return 1

    for attempt in range(6):
        try_inplace = (attempt + 1) >= 3
        try:
            wrote = _attempt(a.file, a.match, a.line, a.anchor_after, try_inplace)
            if wrote:
                print("upserted: %s" % a.line)
            else:
                print("already up to date: %s" % a.line)
            return 0
        except ValueError as e:
            sys.stderr.write("FAILED (not retryable): %s\n" % e)
            return 1
        except Exception as e:
            sys.stderr.write("attempt %d: %s — retrying\n" % (attempt + 1, e))
        time.sleep(0.25 * (attempt + 1))

    sys.stderr.write(
        "FAILED after retries -- apply this line by hand to %s:\n  %s\n"
        % (a.file, a.line)
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
