#!/usr/bin/env python3
"""Structural rollover for memory/event_log.md — moves the oldest entries to
a dated archive file, keeping the live log under memory-policy.md's ~1000-line
soft cap. This is a STRUCTURAL edit (single-writer doctrine, 2026-06-11):
unlike append-event-log.py, which any session may run concurrently, this
script should run alone -- check for other active sessions before running it.

WHY (2026-07-16): the live log crossed 3000 lines (3x the ~1000 soft cap)
with no dedicated rollover tool -- the 2026-07-09 rollover was done by hand.
This mirrors append-event-log.py's mtime-guard + atomic-replace + backup
pattern so a repeat rollover doesn't collide with a concurrent append.

Cut rule (memory-policy.md #4): keep roughly the most recent 600 lines live,
moving everything older to memory/_archive/event_log_<today>.md. The cut
lands on the first '## ' entry boundary at or after --keep-min lines, so no
entry is split across the live/archive boundary. No content is altered --
a straight cut, same as the 2026-07-09 rollover.

Usage:
  python rollover-event-log.py            # keep ~600 lines (default), run it
  python rollover-event-log.py --dry-run  # show what would move, change nothing
  python rollover-event-log.py --keep-min 800
"""
import argparse
import datetime
import os
import re
import sys

LOG = os.path.join(os.path.expanduser("~"), ".claude", "projects",
                    "C--Users-Owner-OneDrive---Oxford-Capital-Partners",
                    "memory", "event_log.md")
ARCHIVE_DIR = os.path.join(os.path.dirname(LOG), "_archive")

HEADER_RE = re.compile(r"^## ", re.MULTILINE)


def find_cut_index(lines, keep_min):
    """Return the 0-indexed line number of the first '## ' header at or
    after `keep_min` lines in -- the entry boundary where the archive cut
    lands. Raises ValueError if no such header exists (log too short)."""
    for i, line in enumerate(lines):
        if i >= keep_min and line.startswith("## "):
            return i
    raise ValueError("no header boundary found at or after keep_min=%d lines "
                      "-- log may be shorter than keep_min" % keep_min)


def split_frontmatter(text):
    """Return (frontmatter_and_intro, body_start_index_in_lines) -- the
    intro is everything before the first '## ' entry (frontmatter + the
    H1 + any preamble prose), which always stays in the live file."""
    lines = text.splitlines(keepends=True)
    for i, line in enumerate(lines):
        if line.startswith("## "):
            return "".join(lines[:i]), i
    raise ValueError("no '## ' entry found -- unexpected event_log.md shape")


def build_archive_content(archived_entries_text, today, cutoff_note):
    header = (
        "# Event Log Archive — entries rolled over %s\n\n"
        "Rolled over %s per memory-policy.md's rollover rule (live log "
        "crossed the ~1000-line soft cap; kept ~%s most recent lines). "
        "Newest-first, same as the live log. No content altered -- a "
        "straight cut of the live log's older entries.\n\n"
    ) % (today, today, cutoff_note)
    return header + archived_entries_text


def main(argv=None):
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--keep-min", type=int, default=600,
                     help="minimum lines to keep live before the next header boundary (default 600)")
    ap.add_argument("--dry-run", action="store_true",
                     help="show what would move without writing anything")
    ap.add_argument("--log", default=LOG)
    a = ap.parse_args(argv)

    if not os.path.isfile(a.log):
        sys.stderr.write("no such file: %s\n" % a.log)
        return 1

    mtime_before = os.stat(a.log).st_mtime_ns
    with open(a.log, encoding="utf-8") as f:
        text = f.read()

    intro, body_start = split_frontmatter(text)
    lines = text.splitlines(keepends=True)
    total = len(lines)

    if total <= a.keep_min:
        print("log is %d lines, at or under --keep-min %d -- nothing to roll over" % (total, a.keep_min))
        return 0

    try:
        cut = find_cut_index(lines, max(a.keep_min, body_start))
    except ValueError as e:
        sys.stderr.write("%s\n" % e)
        return 1

    live_entries = "".join(lines[body_start:cut])
    archived_entries = "".join(lines[cut:])

    today = datetime.date.today().isoformat()
    archive_path = os.path.join(ARCHIVE_DIR, "event_log_%s.md" % today)

    # Identify the oldest entry title staying live, for the pointer note.
    kept_headers = [l for l in lines[body_start:cut] if l.startswith("## ")]
    last_kept_title = kept_headers[-1].strip() if kept_headers else "(none)"

    pointer = (
        "\n---\n\n*Entries at and before “%s” rolled over %s to "
        "[_archive/event_log_%s.md](_archive/event_log_%s.md) per "
        "memory-policy.md's rollover rule.*\n"
    ) % (last_kept_title.lstrip("# ").strip(), today, today, today)

    new_live = intro + live_entries + pointer
    new_archive = build_archive_content(archived_entries, today, str(cut - body_start))

    print("total lines: %d" % total)
    print("keeping live: %d entry-lines (body_start=%d, cut=%d) + intro/pointer" % (cut - body_start, body_start, cut))
    print("archiving: %d lines -> %s" % (len(lines) - cut, archive_path))
    print("last kept entry: %s" % last_kept_title)

    if a.dry_run:
        print("--dry-run: no files written")
        return 0

    if os.path.exists(archive_path):
        sys.stderr.write("refusing to overwrite existing archive file: %s\n" % archive_path)
        sys.stderr.write("(a rollover already ran today -- if you need to re-run, archive it first)\n")
        return 1

    if os.stat(a.log).st_mtime_ns != mtime_before:
        sys.stderr.write("event_log.md changed since it was read -- aborting without writing "
                          "(another session is likely appending; re-run once it's quiet)\n")
        return 1

    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    with open(archive_path, "w", encoding="utf-8") as f:
        f.write(new_archive)

    backup = a.log + ".rollover-backup"
    with open(backup, "w", encoding="utf-8") as f:
        f.write(text)

    tmp = a.log + ".tmp-rollover"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(new_live)
    os.replace(tmp, a.log)

    with open(a.log, encoding="utf-8") as f:
        written = f.read()
    if written != new_live:
        sys.stderr.write("post-write verify MISMATCH -- backup preserved at %s, archive at %s\n"
                          % (backup, archive_path))
        return 1

    os.remove(backup)
    print("rollover complete: live log now %d lines, archive at %s" % (len(new_live.splitlines()), archive_path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
