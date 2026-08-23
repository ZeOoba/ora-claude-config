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

IN-PLACE FALLBACK (2026-07-16): diagnosed via Restart Manager that the Desktop app
(Claude.exe) can hold a long-lived read handle on event_log.md that blocks os.replace
(the atomic-insert rename step) specifically, while direct reads AND direct writes to
the same file keep working throughout -- see memory reference_event_log_app_handle_lock.md.
After INPLACE_FALLBACK_AFTER failed atomic-replace attempts, both the main retry loop
and drain_spool now also try an in-place write (same mtime-guard, plus a pre-write
backup and a post-write read-back verify) before giving up on that attempt. Spooling
is now the last resort only when BOTH paths fail.

RESIDUE (2026-07-16, same day): the two paths above each leaked a ~480KB scratch file
next to the log. os.replace is the only thing that consumes .tmp-append, so a blocked
atomic attempt orphaned it -- and the in-place fallback writes straight to the log and
never picks it up. Both are now cleaned up once their content is durably in the log
(the .inplace-backup only after its read-back verify passes, so failure paths keep it).
Orphans read as unmerged data and cost a real investigation to clear, which is the
actual harm -- the content was a pure duplicate both times.
"""
import argparse
import datetime
import os
import re
import subprocess
import sys
import time

# A real entry header is a DATED '## YYYY-MM-DD ...' line (see insert_newest's and
# this module's own docstrings). A bare '## ' prefix is NOT sufficient: entry
# bodies routinely contain markdown '## ' sub-headings (three such lines exist in
# the live event_log.md today), and treating every '## '-prefixed line as a new
# entry boundary silently splits a single entry into fragments -- which in turn
# makes is_duplicate_entry() compare fragments instead of the whole entry and
# miss an exact duplicate (found in code review, 2026-08-12).
ENTRY_HEADER_RE = re.compile(r"^## \d{4}-\d{2}-\d{2}\b")

LOG = os.path.join(os.path.expanduser("~"), ".claude", "projects",
                   "C--Users-Owner-OneDrive---Oxford-Capital-Partners",
                   "memory", "event_log.md")

# After this many failed atomic-replace attempts within a retry loop, also attempt
# the in-place fallback on each remaining attempt (rather than waiting for every
# attempt to exhaust before ever trying it).
INPLACE_FALLBACK_AFTER = 3

# Print a WARN (never blocks -- this script's whole design is "append must always
# succeed") once this many uncommitted '## ' entries have piled up against HEAD.
UNCOMMITTED_BACKLOG_WARN_AT = 4

# Print a WARN once the live log's total size exceeds this many bytes, regardless
# of commit status. 400_000 matches the largest of the 3 historical archived
# chunks (303,844B / 401,121B / 135,280B) -- Automation Audit R18-2 found the log
# went 35 days (7614 lines, 1.42MB) with no rollover because the only existing
# warning tracked uncommitted entry COUNT, not total file size, so nothing fired
# until someone remembered to run rollover-event-log.py by hand.
LOG_SIZE_WARN_AT = 400_000


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


def stamp_modified(content, when=None):
    """Refresh the frontmatter `modified:` timestamp. Pure when `when` is given.

    WHY THIS EXISTS (2026-08-16): the harness refreshes `modified:` only when IT
    writes a file via Edit/Write. A script write -- which is what this tool does --
    bypasses that, so every append left the field reading older than the file
    actually was, and the drift compounds silently: event_log.md had taken 8
    entries across 4 days while still claiming `modified: 2026-08-12T20:13:19Z`.
    Memory tooling uses that field to judge how current, and therefore how
    trustworthy, a file is, so a stale stamp makes the canonical append-only log
    look less reliable than it is.

    `when` is a parameter rather than an internal datetime.now() so this stays a
    pure, deterministically-testable function -- the same property insert_newest()
    documents about itself. Callers supply the clock.

    Deliberately conservative in two ways:
      * only the frontmatter block is rewritten, so a 'modified:' appearing in the
        BODY of an entry is never touched;
      * a file with no frontmatter, or frontmatter carrying no `modified:` key, is
        returned unchanged -- this does not invent a key the file never had.
    """
    if when is None:
        when = datetime.datetime.now(datetime.timezone.utc)
    stamp = when.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    if not content.startswith("---\n"):
        return content
    end = content.find("\n---\n", 4)
    if end == -1:
        return content
    head, rest = content[:end], content[end:]
    new_head, n = re.subn(r"(?m)^(\s*modified:[ \t]*).*$",
                          lambda m: m.group(1) + stamp, head, count=1)
    if n == 0:
        return content
    return new_head + rest


def normalize_entry(text):
    """Canonical form for duplicate comparison: LF endings, no per-line trailing
    whitespace, outer whitespace stripped. Two entries differing only in EOL or
    trailing spaces are the SAME entry here (a Cowork-prepared entry handed to
    Code routinely picks up CRLF on the way)."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = "\n".join(ln.rstrip() for ln in text.split("\n")).strip()
    # Collapse runs of blank lines so an entry re-prepared with different vertical
    # spacing still reads as the same entry. Markdown renders 2+ blanks identically,
    # so this cannot merge two genuinely different entries.
    while "\n\n\n" in text:
        text = text.replace("\n\n\n", "\n\n")
    return text


def entry_blocks(content):
    """Yield each dated-'## YYYY-MM-DD'-headed entry block from the log body,
    skipping YAML frontmatter (so a '## ' inside it is never treated as an entry).

    Matches on ENTRY_HEADER_RE, NOT a bare '## ' prefix -- a body-text markdown
    sub-heading (e.g. '## Cross-repo worktree staleness/collision sweep ...',
    present in the live log) must stay part of its parent entry, not start a new
    one."""
    body_start = 0
    if content.startswith("---\n"):
        end = content.find("\n---\n", 4)
        if end != -1:
            body_start = end + len("\n---\n")
    lines = content[body_start:].split("\n")
    idxs = [i for i, ln in enumerate(lines) if ENTRY_HEADER_RE.match(ln)]
    for k, i in enumerate(idxs):
        j = idxs[k + 1] if k + 1 < len(idxs) else len(lines)
        yield "\n".join(lines[i:j])


def is_duplicate_entry(content, entry):
    """True iff `entry` already exists in `content` as a whole, content-identical
    '## ' block.

    KEYS ON THE FULL BLOCK, NEVER THE HEADER ALONE -- repeated headers are
    legitimate and routine. The allow-hook-test-failure override protocol writes
    five entries in a single day under a byte-identical header, each with a
    different body; a header-based check would block mandatory mechanical
    record-keeping. Only an exact content match is a duplicate.

    Compares whole blocks rather than substring-searching, so a short entry whose
    text happens to appear inside a longer one is not a false positive."""
    n = normalize_entry(entry)
    if not n:
        return False
    return any(normalize_entry(b) == n for b in entry_blocks(content))


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


def _is_duplicate_fail_open(content, entry, allow_duplicate):
    """is_duplicate_entry(), but a check failure never blocks an append -- same
    fail-open contract the standalone guard had before it moved in here."""
    if allow_duplicate:
        return False
    try:
        return is_duplicate_entry(content, entry)
    except Exception:
        return False


def _atomic_insert(log, entry, allow_duplicate=False):
    """One mtime-guarded read + duplicate-check + newest-first insert + atomic
    replace. Returns True if written, False if a content-identical entry was
    already present (nothing written -- see is_duplicate_entry); raises on
    lock/other error (caller decides retry/spool).

    THE DUPLICATE CHECK LIVES HERE, INSIDE THE SAME MTIME-GUARDED CYCLE AS THE
    WRITE (2026-08-12 -- found in code review of the FIRST version of this
    guard, which read the log separately, before the retry loop, as a one-shot
    pre-check). That separate read was a TOCTOU window: two processes racing to
    append the SAME entry could both read before either wrote, both see
    "not a duplicate", and both write -- reproducing the exact double-append
    this guard exists to prevent. Checking here means every retry attempt
    re-reads and re-checks fresh content, so a concurrent writer that lands the
    same entry between this attempt and the last is caught on the next one; the
    mtime guard already forces a fresh read on any interleaving write, and the
    duplicate check now shares that same freshness guarantee instead of running
    once, before the loop starts. Verified with two real OS processes racing to
    append identical content against the same file (test_separate_processes...
    -style subprocess race, not thread interleaving) -- exactly one copy lands.

    THIS IS ALSO WHY drain_spool NEEDS NO SEPARATE DUPLICATE CHECK OF ITS OWN
    (closes a second, independent finding from the same review): it replays
    spooled entries through this same function, so a spooled entry that turns
    out to already be in the log (e.g. two locked runs both spooled the same
    content) is silently recognized and discarded here, not blindly rewritten."""
    st_before = os.stat(log).st_mtime_ns
    with open(log, encoding="utf-8") as f:
        content = f.read()
    if os.stat(log).st_mtime_ns != st_before:
        raise BlockingIOError("log changed mid-read")
    if _is_duplicate_fail_open(content, entry, allow_duplicate):
        return False
    new = stamp_modified(insert_newest(content, entry))
    tmp = log + ".tmp-append"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(new)
        os.replace(tmp, log)  # atomic on the same volume; consumes tmp on success
    except Exception:
        # os.replace is the ONLY thing that consumes tmp, so any failure here orphans
        # it -- and the in-place fallback that follows writes straight to `log` and
        # never picks it up (2026-07-16: a 480KB orphan sat next to event_log.md,
        # reading as unmerged data until a hash proved it a pure duplicate). The
        # content is re-derived from `log` on the next attempt, so it is pure scratch.
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise
    return True


def _inplace_insert(log, entry, allow_duplicate=False):
    """Fallback for when os.replace is blocked (e.g. another process holds `log`
    open without FILE_SHARE_DELETE -- proven 2026-07-16, see memory
    reference_event_log_app_handle_lock.md) but direct reads/writes to the same
    path still succeed. Same mtime-guard AND duplicate check as _atomic_insert
    (see its docstring -- the check must live on this path too, since
    _insert_or_inplace can fall back here after the atomic path raises, and a
    fresh read on this path needs the same freshness guarantee), PLUS a
    pre-write backup (so a partial/interrupted write is always recoverable;
    removed once the read-back verify proves it redundant) and a post-write
    read-back verify (so a silent corruption is never trusted as success).
    Returns True if written, False if already a content-identical duplicate
    (nothing written); raises on any check failure -- caller decides whether to
    retry or spool, and the backup is left on disk for recovery."""
    st_before = os.stat(log).st_mtime_ns
    with open(log, encoding="utf-8") as f:
        content = f.read()
    if os.stat(log).st_mtime_ns != st_before:
        raise BlockingIOError("log changed mid-read")
    if _is_duplicate_fail_open(content, entry, allow_duplicate):
        return False
    new = stamp_modified(insert_newest(content, entry))
    backup = log + ".inplace-backup"
    with open(backup, "w", encoding="utf-8") as f:
        f.write(content)
    with open(log, "w", encoding="utf-8") as f:
        f.write(new)
    with open(log, encoding="utf-8") as f:
        written = f.read()
    if written != new:
        raise IOError("in-place write verify mismatch -- backup at %s" % backup)
    # Verify passed, so `log` is known-good and the backup has discharged its purpose.
    # Removing it ONLY here keeps the net intact on every failure path: a partial write
    # or a failed verify never reaches this line, so the backup survives for recovery.
    try:
        os.remove(backup)
    except OSError:
        pass
    return True


def _insert_or_inplace(log, entry, try_inplace, allow_duplicate=False):
    """Try the atomic (os.replace) insert; if it fails (not a malformed-entry
    ValueError) and `try_inplace` is set, fall back to _inplace_insert. Returns
    True if written, False if recognized as a content-identical duplicate and
    correctly left unwritten (see _atomic_insert) -- both are successful,
    exception-free outcomes; only the caller needs to tell them apart. A
    ValueError from either path propagates immediately (malformed entry --
    retrying or falling back cannot help). If both paths fail, raises the
    ATOMIC path's exception, since that's the one callers already log
    per-attempt."""
    try:
        return _atomic_insert(log, entry, allow_duplicate)
    except ValueError:
        raise
    except Exception as atomic_exc:
        if not try_inplace:
            raise
        try:
            return _inplace_insert(log, entry, allow_duplicate)
        except ValueError:
            raise
        except Exception:
            raise atomic_exc


def drain_spool(log, attempts=3):
    """Replay spooled entries (oldest-first) into `log`. Stops at the first one that
    still can't be written -- leaves it and the rest for next time (nothing is lost).
    A malformed spooled entry is discarded so it can't wedge the queue forever.
    Returns the count successfully drained.

    DUPLICATE-SAFE WITHOUT ITS OWN CHECK (2026-08-12, closes a code-review finding):
    each spooled entry replays through _insert_or_inplace -> _atomic_insert /
    _inplace_insert, which now does its own duplicate check on every attempt (see
    _atomic_insert's docstring). A spooled entry that turns out to already be in
    `log` -- e.g. two locked runs both failed to write the SAME content and both
    spooled it -- is silently recognized and left unwritten rather than being
    blindly reinserted. Never pass allow_duplicate=True here: a queued, unattended
    replay is exactly the case where forcing a duplicate through has no one to
    confirm it. The return value is intentionally NOT inspected below -- both
    "wrote" (True) and "recognized as an existing duplicate" (False) are
    successful, exception-free outcomes, and either way the spool file has been
    durably resolved and can be removed."""
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
            try_inplace = (attempt + 1) >= min(INPLACE_FALLBACK_AFTER, attempts)
            try:
                _insert_or_inplace(log, entry, try_inplace)
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


def warn_if_uncommitted_backlog(log, threshold=UNCOMMITTED_BACKLOG_WARN_AT,
                                 size_threshold=LOG_SIZE_WARN_AT):
    """Best-effort, NEVER-BLOCKING nudge: if `threshold`+ '## '-headed entries
    are sitting uncommitted against HEAD, OR the live log has grown past
    `size_threshold` bytes (regardless of commit status), print a one-line
    WARN to stderr.

    2026-07-17: multiple concurrent sessions each append-without-committing
    over the same day, and the file accumulates into one large, tangled diff
    spanning unrelated sessions' work by the time anyone commits it -- exactly
    what made that day's own close-out entry hard to land cleanly (see
    memory/reference_event_log_uncommitted_backlog.md). This only counts
    '+## ' lines in `git diff HEAD -- <log>` (each is a newly appended entry
    header; existing entries are never modified by this script) -- it does
    NOT attempt to attribute lines to a specific session, and it never
    fails the append: any error here (not a git repo, git unavailable, no
    HEAD yet) is silently swallowed, matching this file's fail-open style
    everywhere else.

    2026-08-22 (Automation Audit R18-2): the count check above only ever
    fires when someone is actively appending without committing -- it says
    nothing about total file size, so a log that IS being committed regularly
    but never rolled over (structurally, not just left uncommitted) can still
    grow unbounded with no warning at all. That's exactly what happened here:
    35 days, 7614 lines, 1.42MB, no WARN ever printed. The size check below is
    independent of git state entirely (a plain os.path.getsize), so it fires
    even when the count check stays silent."""
    try:
        size = os.path.getsize(log)
        if size >= size_threshold:
            sys.stderr.write(
                "WARN: %s is %d bytes, past the %d-byte rollover threshold -- "
                "run maintenance/rollover-event-log.py to cut it back down.\n"
                % (os.path.basename(log), size, size_threshold)
            )
    except OSError:
        pass  # best-effort only -- must never affect the append's own success
    try:
        repo = os.path.dirname(os.path.abspath(log))
        # walk up to find a repo root cheaply -- git handles this natively
        proc = subprocess.run(
            ["git", "-C", repo, "diff", "HEAD", "--", log],
            # encoding pinned 2026-07-18: bare text=True decodes with the Windows
            # locale codec (cp1252), which chokes on the log's UTF-8 em-dashes in a
            # large diff (UnicodeDecodeError surfaced during the 07-18 rollover run).
            capture_output=True, encoding="utf-8", errors="replace", timeout=5,
        )
        if proc.returncode != 0:
            return
        added_headers = sum(
            1 for ln in proc.stdout.splitlines() if ln.startswith("+## ")
        )
        if added_headers >= threshold:
            sys.stderr.write(
                "WARN: %d entries appended since the last commit to %s -- "
                "consider committing soon so it doesn't grow into one large, "
                "multi-session diff (see the isolated-hunk technique in "
                "memory/reference_event_log_uncommitted_backlog.md if other "
                "sessions also have uncommitted entries mixed in).\n"
                % (added_headers, os.path.basename(log))
            )
    except Exception:
        pass  # best-effort only -- must never affect the append's own success


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
    ap.add_argument("--allow-duplicate", action="store_true",
                    help="append even if a content-identical entry already exists "
                         "(default: skip it and exit 0)")
    a = ap.parse_args(argv)
    if a.entry_file:
        with open(a.entry_file, encoding="utf-8") as f:
            entry = f.read()
    else:
        # Decode stdin as UTF-8 explicitly. A bare sys.stdin.read() uses the Windows
        # locale (cp1252), so a caller piping UTF-8 -- as both pre-push gates did --
        # gets it DOUBLE-ENCODED: the em dash's E2 80 94 arrives as three cp1252
        # characters and is re-encoded, producing "a<TM>" in the heading. Seven
        # override records landed in event_log.md that way before this was found
        # (2026-08-03). --entry-file always opened with an explicit encoding; stdin
        # did not. Callers should still prefer --entry-file, but the appender must not
        # silently corrupt input when they don't.
        try:
            entry = sys.stdin.buffer.read().decode("utf-8")
        except (AttributeError, UnicodeDecodeError):
            entry = sys.stdin.read()
    # Tolerate a leading UTF-8 BOM. PowerShell 5.1 `Set-Content -Encoding UTF8` prepends one
    # (U+FEFF), which str.strip() does NOT remove -- so a BOM'd --entry-file used to fail the
    # '## ' header check in insert_newest() (2026-07-17). lstrip it before validation; harmless
    # on BOM-free input and on the stdin path.
    entry = entry.lstrip("﻿").strip()
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

    # DUPLICATE GUARD (2026-08-12; hardened against a TOCTOU race found in code
    # review the same day -- see _atomic_insert's docstring for the full story).
    # The check is NOT a separate pre-read here: it happens inside
    # _insert_or_inplace, on the SAME mtime-guarded content this attempt is about
    # to write from, on every attempt of the loop below -- so a concurrent writer
    # that lands the identical entry between attempts is caught fresh next time,
    # not missed by a stale one-shot read taken before the loop started.
    #
    # Skipping cannot lose anything: a content-identical block is ALREADY in the
    # log, so the caller's intent is already satisfied. Exit stays 0 so `&&`
    # chains (both pre-push gates use them) never break -- consistent with this
    # script's "the append must always succeed" design. FAIL-OPEN by construction
    # (see _is_duplicate_fail_open): a check failure falls through to a normal
    # write attempt, never blocks one.
    for attempt in range(6):
        try_inplace = (attempt + 1) >= INPLACE_FALLBACK_AFTER
        try:
            wrote = _insert_or_inplace(a.log, entry, try_inplace, a.allow_duplicate)
            if not wrote:
                sys.stderr.write(
                    "SKIPPED: a content-identical entry is already in %s.\n"
                    "  Nothing was appended. Pass --allow-duplicate to force.\n"
                    % os.path.basename(a.log))
                print("skipped (duplicate): %s" % header)
                return 0
            with open(a.log, encoding="utf-8") as f:
                if header in f.read():
                    print("appended: %s" % header)
                    warn_if_uncommitted_backlog(a.log)
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
