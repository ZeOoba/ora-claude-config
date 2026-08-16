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
import time

LOG = os.path.join(os.path.expanduser("~"), ".claude", "projects",
                    "C--Users-Owner-OneDrive---Oxford-Capital-Partners",
                    "memory", "event_log.md")
ARCHIVE_DIR = os.path.join(os.path.dirname(LOG), "_archive")

HEADER_RE = re.compile(r"^## ", re.MULTILINE)

# Attempts at swapping the live log before giving up, and the attempt at which we
# also start trying the in-place path. Same shape and rationale as
# append-event-log.py's retry loop: Claude.exe (the Desktop app) can hold a read
# handle on event_log.md WITHOUT FILE_SHARE_DELETE for tens of minutes and then
# release it on its own, which blocks os.replace specifically while leaving plain
# reads and in-place writes working (Restart Manager diagnosis 2026-07-16 --
# memory/reference_event_log_app_handle_lock.md). Retrying alone does not clear
# that hold, so the in-place write is the path that actually gets through it.
REPLACE_ATTEMPTS = 6
INPLACE_FALLBACK_AFTER = 3


def archive_dir_for(log):
    """Archive directory that belongs to `log`.

    Derived from the target path, NOT from the module-level LOG constant: the
    original computed ARCHIVE_DIR once at import time, so `--log <somewhere
    else>` still wrote its archive into the real memory/_archive. That is not
    theoretical -- it fired on the first run of this file's own test suite,
    depositing a synthetic archive beside the live log."""
    return os.path.join(os.path.dirname(os.path.abspath(log)), "_archive")


def _guard_mtime(log, mtime_before):
    """Raise BlockingIOError if `log` moved under us since it was read."""
    if os.stat(log).st_mtime_ns != mtime_before:
        raise BlockingIOError(
            "event_log.md changed since it was read -- refusing to write stale content")


def _atomic_swap(log, new_live, mtime_before):
    _guard_mtime(log, mtime_before)
    tmp = log + ".tmp-rollover"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(new_live)
        os.replace(tmp, log)  # atomic on the same volume; consumes tmp on success
    except Exception:
        # os.replace is the only thing that consumes tmp, so a blocked attempt
        # orphans it -- and the in-place path writes straight to `log` and never
        # picks it up. append-event-log.py left a ~480KB orphan exactly this way
        # (2026-07-16) that read as unmerged data and cost a real investigation.
        # The content is re-derived from `new_live` each attempt, so it is scratch.
        try:
            os.remove(tmp)
        except Exception:
            pass
        raise
    return True


def _inplace_write(log, new_live, mtime_before):
    """Write through a handle that blocks rename but permits direct writes.
    Carries the same mtime guard plus a post-write read-back verify."""
    _guard_mtime(log, mtime_before)
    with open(log, "w", encoding="utf-8") as f:
        f.write(new_live)
    with open(log, encoding="utf-8") as f:
        if f.read() != new_live:
            raise IOError("in-place rollover read-back mismatch on %s" % log)
    return True


def write_live_log(log, new_live, mtime_before, attempts=REPLACE_ATTEMPTS):
    """Replace `log` with `new_live`. True on success, False if every attempt
    failed. Raises BlockingIOError -- WITHOUT retrying -- if a concurrent writer
    landed an append meanwhile.

    That last case is the hazard the retry itself introduces. `new_live` was
    computed from a read taken before the archive was written; if another session
    appends during the retry window, writing it would silently delete their entry
    from an append-only log. Every attempt therefore re-checks mtime and aborts
    rather than retrying, which is the same freshness guarantee append-event-log's
    _atomic_insert gets by re-reading inside its own mtime-guarded cycle."""
    for attempt in range(attempts):
        try_inplace = (attempt + 1) >= min(INPLACE_FALLBACK_AFTER, attempts)
        try:
            return _atomic_swap(log, new_live, mtime_before)
        except BlockingIOError:
            raise
        except Exception:
            if try_inplace:
                try:
                    return _inplace_write(log, new_live, mtime_before)
                except BlockingIOError:
                    raise
                except Exception:
                    pass
            time.sleep(0.2 * (attempt + 1))
    return False


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
    archive_dir = archive_dir_for(a.log)
    archive_path = os.path.join(archive_dir, "event_log_%s.md" % today)

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

    os.makedirs(archive_dir, exist_ok=True)
    with open(archive_path, "w", encoding="utf-8") as f:
        f.write(new_archive)

    backup = a.log + ".rollover-backup"
    with open(backup, "w", encoding="utf-8") as f:
        f.write(text)

    # The archive and backup are already on disk here, so a failed swap is not a
    # clean no-op: the archive duplicates content that is STILL live, and the
    # "refusing to overwrite existing archive file" guard above then rejects every
    # re-run -- a transient, self-clearing app handle lock would wedge rollover
    # until someone cleaned up by hand. So the scratch files must go.
    #
    # But they may only go once the live log is PROVEN intact. The in-place
    # fallback opens the log with mode "w", which truncates before any bytes
    # land, so a failure after that point leaves the log damaged and the backup
    # holding the only copy of the original. An earlier version of this function
    # deleted the backup unconditionally on the strength of "the live log is
    # untouched in all failure paths" -- true before the in-place path existed,
    # false after it. A probe drove an ENOSPC-shaped failure through it and the
    # log came back 0 bytes with backup and archive both gone: a recoverable
    # failure turned into total, unrecoverable loss of the canonical log.
    #
    # Restore first, verify, and only then discard. If the log cannot be put
    # back, keep EVERYTHING and say so loudly -- a wedged rollover is a nuisance,
    # a destroyed event_log.md is not recoverable from anywhere else on disk.
    def _unwind(reason):
        try:
            with open(a.log, encoding="utf-8") as fh:
                current = fh.read()
        except OSError:
            current = None

        restored = (current == text)
        if not restored:
            try:
                with open(a.log, "w", encoding="utf-8") as fh:
                    fh.write(text)
                with open(a.log, encoding="utf-8") as fh:
                    restored = (fh.read() == text)
            except OSError:
                restored = False

        if not restored:
            sys.stderr.write(
                "%s -- AND the live log could not be restored to its original "
                "content. The original is preserved at %s and the archived tail at "
                "%s; BOTH LEFT IN PLACE DELIBERATELY. Restore by hand before "
                "running rollover again.\n" % (reason, backup, archive_path))
            return

        for scratch in (archive_path, backup, a.log + ".tmp-rollover"):
            try:
                os.remove(scratch)
            except OSError:
                pass
        sys.stderr.write("%s -- live log verified intact; archive and backup removed "
                          "so a re-run is not blocked by the archive-exists guard\n" % reason)

    try:
        wrote = write_live_log(a.log, new_live, mtime_before)
    except BlockingIOError as e:
        _unwind("%s" % e)
        return 1
    if not wrote:
        _unwind("could not replace %s after %d attempts (atomic and in-place both "
                 "failed -- see memory/reference_event_log_app_handle_lock.md)"
                 % (a.log, REPLACE_ATTEMPTS))
        return 1

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
