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
import contextlib
import datetime
import importlib.util
import os
import re
import sys
import time

LOG = os.path.join(os.path.expanduser("~"), ".claude", "projects",
                    "C--Users-Owner-OneDrive---Oxford-Capital-Partners",
                    "memory", "event_log.md")
ARCHIVE_DIR = os.path.join(os.path.dirname(LOG), "_archive")

HEADER_RE = re.compile(r"^## ", re.MULTILINE)
# A DATED entry header -- the same pattern append-event-log.py uses (its
# ENTRY_HEADER_RE; test 4e pins the two together). A bare '## ' also matches
# body-text markdown headings, so it cannot prove an entry exists.
ENTRY_HEADER_RE = re.compile(r"^## \d{4}-\d{2}-\d{2}\b")

# _read_log_text() result for a log that is readable but not decodable as UTF-8
# anywhere except a truncated trailing character -- never something this script
# wrote, so it is treated as foreign/ambiguous and never overwritten.
_UNDECODABLE = object()

# How long main() waits for append-event-log's _log_lock before refusing to run.
ROLLOVER_LOCK_TIMEOUT_S = 5.0

# Logs whose content THIS process has truncated during the current run (set by
# _inplace_write immediately before open(log, "w")). _unwind restores only when
# this is set: the log's content alone ("unreadable", "a prefix of new_live")
# cannot tell our damage from another writer's (REFUTE P4/P9 on PR #400).
_OWN_TRUNCATION = set()


def _log_key(log):
    return os.path.normcase(os.path.abspath(log))


def _note_own_truncation(log):
    _OWN_TRUNCATION.add(_log_key(log))


def _own_truncation(log):
    return _log_key(log) in _OWN_TRUNCATION


def _append_log_lock(log, timeout):
    """append-event-log.py's own _log_lock (msvcrt byte-range lock on the
    `log + ".lock"` sidecar) -- imported, never reimplemented, so rollover and
    every appender queue on the SAME lock. Closes the gap between the mtime guard
    and os.replace / open("w") (REFUTE P2/P3/P8): an appender that honours the lock
    cannot land inside rollover's read-modify-write.

    Residual, stated plainly (REFUTE round 2, C9/C10):
      - append-event-log's lock is fail-open after its LOCK_ACQUIRE_TIMEOUT_S.
        Rollover's own hold is short when it succeeds (measured 0.66-0.84 s on a
        ~1.4 MB synthetic log under the Claude.exe read+write-share handle, which
        blocks only os.replace); the path that sleeps through all retries (~4.2 s
        of sleeps, ~4.5 s held) is a deny-write handle, where every attempt fails
        and the live log is never written.
      - An appender that does fail open and lands in the guard->replace gap: its
        own CLI entry is re-verified under the lock and retried, but entries it
        drains from the `.pending` spool (drain_spool) have no post-write verify
        and their spool file is deleted -- that is the silent-loss case
        (follow-up, not fixed here).
      - Writers that never take this lock at all -- the Edit/Write tools, and a
        git merge (e.g. checkout-merge-forward) touching the file -- are covered
        only by the mtime guard and _unwind's classification."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "append-event-log.py")
    spec = importlib.util.spec_from_file_location("_append_event_log_for_rollover", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod._log_lock(log, timeout=timeout)

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


def _stat_stamp(log):
    """Staleness token for `log`: (st_mtime_ns, st_size), captured at read time and
    re-checked before every write.

    mtime alone is not enough (2026-11-06): Windows' file-time clock ticks about
    every 15.6 ms, so an append landing in the same tick as rollover's read leaves
    st_mtime_ns unchanged and the guard waved the stale write through, deleting the
    append -- maintenance/test-rollover-event-log.py section 4 flaked ~3/6 on main
    for exactly this reason. An append always grows the file, so the size half
    catches the same-tick case. Residual: a same-size rewrite within one tick still
    matches -- appenders never do that (they only add), and neither does rollover."""
    st = os.stat(log)
    return (st.st_mtime_ns, st.st_size)


def _guard_mtime(log, stamp_before):
    """Raise BlockingIOError if `log` moved under us since it was read -- by
    mtime OR size (see _stat_stamp; the name is kept for callers and probes)."""
    if _stat_stamp(log) != stamp_before:
        raise BlockingIOError(
            "event_log.md changed since it was read -- refusing to write stale content")


def _atomic_swap(log, new_live, stamp_before):
    _guard_mtime(log, stamp_before)
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


def _inplace_write(log, new_live, stamp_before):
    """Write through a handle that blocks rename but permits direct writes.
    Carries the same (mtime, size) guard plus a post-write read-back verify."""
    _guard_mtime(log, stamp_before)
    # Flag ownership only AFTER open() succeeds: open(log, "w") is what truncates.
    # If it raises (sharing violation from a deny-write handle) nothing was
    # truncated, and a flag set before it would let _unwind restore over a foreign
    # writer later in the run (REFUTE round 2, C1).
    f = open(log, "w", encoding="utf-8")
    _note_own_truncation(log)       # `log` is now truncated: damage from here is ours
    with f:
        f.write(new_live)
    with open(log, encoding="utf-8") as f:
        if f.read() != new_live:
            raise IOError("in-place rollover read-back mismatch on %s" % log)
    return True


def write_live_log(log, new_live, stamp_before, attempts=REPLACE_ATTEMPTS):
    """Replace `log` with `new_live`. True on success, False if every attempt
    failed. Raises BlockingIOError -- WITHOUT retrying -- if a concurrent writer
    landed an append meanwhile.

    That last case is the hazard the retry itself introduces. `new_live` was
    computed from a read taken before the archive was written; if another session
    appends during the retry window, writing it would silently delete their entry
    from an append-only log. Every attempt therefore re-checks the read-time
    (mtime, size) stamp from _stat_stamp, passed in as `stamp_before`, and aborts
    rather than retrying, which is the same freshness guarantee append-event-log's
    _atomic_insert gets by re-reading inside its own mtime-guarded cycle."""
    for attempt in range(attempts):
        try_inplace = (attempt + 1) >= min(INPLACE_FALLBACK_AFTER, attempts)
        try:
            return _atomic_swap(log, new_live, stamp_before)
        except BlockingIOError:
            raise
        except Exception:
            if try_inplace:
                try:
                    return _inplace_write(log, new_live, stamp_before)
                except BlockingIOError:
                    raise
                except Exception:
                    pass
            time.sleep(0.2 * (attempt + 1))
    return False


def _read_log_text(log):
    """Read `log` the way text-mode open(..., encoding='utf-8') would, but
    tolerate a write cut off inside a multi-byte character.

    Returns the text (universal-newline normalised, same as the original read),
    None if the file cannot be read at all, or _UNDECODABLE if it holds invalid
    UTF-8 anywhere but an incomplete final character. A text-mode read raises
    UnicodeDecodeError on such a tail -- not OSError -- so the old _unwind crashed
    out of main() with the backup and archive on disk and a traceback instead of
    restoring the log this run had just truncated."""
    try:
        with open(log, "rb") as fh:
            raw = fh.read()
    except OSError:
        return None
    try:
        s = raw.decode("utf-8")
    except UnicodeDecodeError as e:
        # Only an incomplete sequence at the very end is a plausible cut-short
        # write of ours (we only ever write valid UTF-8).
        if e.reason != "unexpected end of data" or len(raw) - e.start > 3:
            return _UNDECODABLE
        try:
            s = raw[:e.start].decode("utf-8")
        except UnicodeDecodeError:
            return _UNDECODABLE
    return s.replace("\r\n", "\n").replace("\r", "\n")


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

    if a.dry_run:
        return _rollover(a)

    # Hold append-event-log's lock from the snapshot read through the swap and any
    # _unwind, so a lock-honouring append can neither land between the mtime guard
    # and the write nor between _unwind's read and its restore.
    _OWN_TRUNCATION.discard(_log_key(a.log))
    with contextlib.ExitStack() as stack:
        # Loading the module AND entering the lock both sit inside the try: the
        # lock opens the `.lock` sidecar on entry, and an OSError there (a
        # directory or an ACL in the way) escaped as a traceback (REFUTE round 2,
        # C5). Nothing has been written yet at this point, so refusing is clean.
        try:
            locked = stack.enter_context(_append_log_lock(a.log, ROLLOVER_LOCK_TIMEOUT_S))
        except Exception as e:
            sys.stderr.write("could not take append-event-log's _log_lock on %s.lock (%s) -- "
                             "refusing to roll over without it; nothing written\n" % (a.log, e))
            return 1
        if locked is False:
            sys.stderr.write("event_log.md is locked by an appender (%s.lock) -- refusing to "
                             "roll over; nothing written. Re-run once it's quiet.\n" % a.log)
            return 1
        try:
            return _rollover(a)
        finally:
            _OWN_TRUNCATION.discard(_log_key(a.log))


def _rollover(a):
    stamp_before = _stat_stamp(a.log)
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

    if _stat_stamp(a.log) != stamp_before:
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
    #
    # And restoring is only right when the damage is OURS. A BlockingIOError also
    # means another session appended meanwhile; writing `text` back then deletes
    # their entry from an append-only log -- the exact clobber write_live_log's
    # mtime guard exists to prevent (finding rollover-unwind-clobbers-concurrent-
    # append, 2026-11-05). So classify what is on disk before touching it:
    #   1. identical to `text`            -> intact; clear scratch.
    #   2. THIS run truncated the log (_inplace_write set the ownership flag) AND
    #      it reads back as a prefix of our `new_live` (empty / cut short)
    #                                     -> damage this run did; restore `text`.
    #      Content alone is never ownership proof (REFUTE P4/P9): an unreadable
    #      log, or another writer's own half-done in-place insert, is case 4.
    #   3. `text` has >= 1 dated entry and its whole entry body survives verbatim
    #      in the log                     -> a foreign write that kept every
    #      original entry; never overwrite. Clear archive + tmp (no wedge), KEEP
    #      the backup (headers alone never prove bodies; the next run's backup
    #      write replaces it).
    #   4. anything else                  -> ambiguous; never overwrite, keep all.
    def _remove(paths):
        for scratch in paths:
            try:
                os.remove(scratch)
            except OSError:
                pass

    def _keep_everything(reason, what, foreign_possible=True):
        sys.stderr.write(
            "%s -- AND %s. The original is preserved at %s and the archived tail at "
            "%s; BOTH LEFT IN PLACE DELIBERATELY. Restore by hand before "
            "running rollover again.\n" % (reason, what, backup, archive_path))
        if foreign_possible:
            sys.stderr.write(
                "WARNING: %s is the PRE-ROLLOVER snapshot. It does NOT contain any "
                "foreign entry another session wrote after this run read the log -- "
                "diff the live log against it and carry those entries over before "
                "restoring; never just copy the backup back.\n" % backup)

    def _unwind(reason):
        current = _read_log_text(a.log)

        if current == text:
            _remove((archive_path, backup, a.log + ".tmp-rollover"))
            sys.stderr.write("%s -- live log verified intact; archive and backup removed "
                              "so a re-run is not blocked by the archive-exists guard\n" % reason)
            return

        ours = (_own_truncation(a.log) and current is not None
                and current is not _UNDECODABLE and new_live.startswith(current))
        if ours:
            try:
                with open(a.log, "w", encoding="utf-8") as fh:
                    fh.write(text)
                restored = (_read_log_text(a.log) == text)
            except OSError:
                restored = False
            if not restored:
                # foreign_possible stays True: a restore that fails part-way can
                # interleave with another writer as easily as any other path (C7).
                _keep_everything(reason, "the live log could not be restored to its "
                                         "original content")
                return
            _remove((archive_path, backup, a.log + ".tmp-rollover"))
            sys.stderr.write("%s -- live log restored and verified intact; archive and "
                              "backup removed so a re-run is not blocked by the "
                              "archive-exists guard\n" % reason)
            return

        original_body = text[len(intro):]
        has_dated = any(ENTRY_HEADER_RE.match(ln) for ln in original_body.splitlines())
        if (current is not None and current is not _UNDECODABLE
                and has_dated and original_body in current):
            _remove((archive_path, a.log + ".tmp-rollover"))
            sys.stderr.write(
                "%s -- concurrent append preserved; rollover aborted. The live log "
                "still holds every original entry verbatim, so it was NOT overwritten; "
                "archive removed so a re-run is not blocked; pre-rollover backup kept "
                "at %s.\n" % (reason, backup))
            return

        # Say what is actually known (REFUTE round 2, C3): an unreadable or
        # undecodable read-back is NOT evidence of another writer, and when this
        # run truncated the log the damage may well be ours.
        if current is None:
            what = "the live log could not be read back to classify it (not overwritten)"
        elif current is _UNDECODABLE:
            what = "the live log is not valid UTF-8, so it cannot be classified (not overwritten)"
        else:
            what = "the live log holds content this run did not write (not overwritten)"
        if _own_truncation(a.log):
            what += ("; this run truncated it in place, so the damage may be ours -- "
                     "the backup holds the pre-rollover content")
        _keep_everything(reason, what)

    try:
        wrote = write_live_log(a.log, new_live, stamp_before)
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
