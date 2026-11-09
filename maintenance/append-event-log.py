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

LOCK (2026-09-07): the mtime-guard above only protects the READ of `log` -- the WRITE
side stages through a FIXED path, `log + ".tmp-append"`, shared by every process. Two
sessions appending within the same instant both stat/write/os.replace that same tmp
name, and Windows can refuse the losing process's rename with WinError 5 ("Access is
denied") while the other still holds it open -- observed live this session: two retries
before the append landed. The existing retry loop already self-heals it, so nothing was
ever lost, but every such collision burns an attempt and a sleep for no reason other
than two processes racing the same filename. _log_lock() now wraps the read-modify-
write critical section in _atomic_insert and _inplace_insert, AND main()'s own
post-write verification read (found only once the multi-process test in
_tests/test_append_event_log_lock.py still saw retries with just the two insert
functions guarded -- that plain read holds `log` open without FILE_SHARE_DELETE just
like the write path does, so it reproduces the identical race if left unguarded), with
a real OS byte-range lock (msvcrt.locking on a `log + ".lock"` sidecar handle) so
concurrent runs of THIS SCRIPT queue for their turn instead of colliding on the tmp
path or on each other's reads. It is scoped
narrowly on purpose: it excludes other holders of this same lock, nothing else -- an
external process (the Desktop app) holding `log` itself open is untouched by it, so the
mtime-guard/retry/in-place-fallback/spool net above is still the thing that catches
that case and stays exactly as it was. Bounded by LOCK_ACQUIRE_TIMEOUT_S: if it can't
be acquired in time (contention or an unexpected holder), the attempt proceeds WITHOUT
the lock rather than blocking indefinitely -- this script's whole design is "the append
must always succeed," and the pre-existing retry loop is the fallback if the lock
itself is ever what's in the way. Uses msvcrt.locking (byte-range on an open handle),
not a bare O_CREAT|O_EXCL lockfile, deliberately: a byte-range lock is released by
Windows the instant the holding handle closes, including on a crash, so a dead writer
can never strand a stale lock the way an existence-based lockfile can. The `.lock` file
itself is never deleted (only unlocked) -- recreating it would itself race the next
locker in the same way the old `.tmp-append` collision did, so it is a small,
intentional, permanent sidecar next to `event_log.md`, not orphaned residue.
"""
import argparse
import contextlib
import datetime
import os
import re
import subprocess
import sys
import time

try:
    import msvcrt
    _HAVE_MSVCRT = True
except ImportError:  # pragma: no cover - this environment is Windows-only
    _HAVE_MSVCRT = False

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

# _log_lock(): how long to wait for the byte-range lock before giving up and
# proceeding without it (see the module docstring's LOCK section). Generous relative
# to a single read-modify-write (milliseconds in practice) but well inside the outer
# retry loop's own budget (6 attempts x up to ~1.5s of sleep), so a lock timeout still
# leaves room for that loop to do its job.
LOCK_ACQUIRE_TIMEOUT_S = 5.0
LOCK_POLL_INTERVAL_S = 0.05

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


@contextlib.contextmanager
def _log_lock(log, timeout=LOCK_ACQUIRE_TIMEOUT_S):
    """Cross-process exclusive lock serializing the read-modify-write critical
    section for `log` (see the module docstring's LOCK section for the full why).

    A byte-range lock on a dedicated `log + ".lock"` sidecar handle, acquired via
    msvcrt.locking -- NOT a bare O_CREAT|O_EXCL lockfile, because a bare lockfile's
    mere existence would need a staleness heuristic to recover from a crashed
    holder; a byte-range lock is released by the OS the moment the holding handle
    closes (including on a crash), so there is nothing to go stale.

    Polls LK_NBLCK rather than blocking on LK_LOCK so the wait is bounded by
    `timeout` and interruptible in the same style as the rest of this file's retry
    loops. On timeout, yields WITHOUT the lock held -- this function's job is to
    remove a common cause of retries, not to introduce a new way for an append to
    hang or fail; the caller's own retry loop is still the backstop.

    No-op on a non-Windows interpreter (there is none in this environment, but the
    test suite gates the same way around ctypes.WinDLL, so this matches).
    """
    if not _HAVE_MSVCRT:
        yield None
        return
    lock_path = log + ".lock"
    # "a+b" both creates the sidecar if absent and never truncates one another
    # process currently holds -- see the module docstring on why it is never
    # deleted, only unlocked.
    f = open(lock_path, "a+b")
    locked = False
    try:
        deadline = time.monotonic() + timeout
        while True:
            try:
                f.seek(0)
                msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
                locked = True
                break
            except OSError:
                if time.monotonic() >= deadline:
                    break
                time.sleep(LOCK_POLL_INTERVAL_S)
        # Yields whether the lock is actually held (None = no msvcrt). Existing
        # callers ignore it; rollover-event-log.py refuses to run on False.
        yield locked
    finally:
        if locked:
            try:
                f.seek(0)
                msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
            except OSError:
                pass
        f.close()


@contextlib.contextmanager
def _maybe_lock(log, lock_held):
    """_log_lock(log), or a no-op when the caller already holds it."""
    if lock_held:
        yield True
        return
    with _log_lock(log) as locked:
        yield locked


class MalformedEntryError(ValueError):
    """The ENTRY itself is malformed -- retrying or spooling cannot help, so this is the
    ONE error that skips the retry/spool net. A dedicated class (2026-11-08 audit
    event-log-unicodedecodeerror-is-valueerror): the net used to exempt every ValueError,
    and UnicodeDecodeError is a ValueError, so a log carrying one undecodable byte made
    main() raise with the entry neither appended nor spooled. Still a ValueError subclass
    so existing callers catching ValueError from insert_newest keep working."""


def insert_newest(content, entry):
    """Insert `entry` (must start '## ') above the first existing '## ' entry,
    skipping YAML frontmatter so a '## ' inside it is never used as the anchor.
    No existing entries -> append at end. Pure function."""
    if not entry.startswith("## "):
        raise MalformedEntryError("entry must start with a dated '## ' header")
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
    drain replays oldest-first. Returns the spooled path.

    Written to a non-.md staging name, then os.replace'd into place (2026-11-05,
    REFUTE finding #3): drain_spool lists only '*.md' and reads outside the lock, so
    a direct write could be seen half-done. A large entry would then be inserted
    truncated, verify as present, and have its spool file deleted."""
    d = spool_dir_for(log)
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, "%d.md" % now_ns)
    tmp = p + ".partial"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(entry)
    os.replace(tmp, p)
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


def _atomic_insert(log, entry, allow_duplicate=False, lock_held=False):
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
    content) is silently recognized and discarded here, not blindly rewritten.

    `lock_held=True` means the CALLER already holds _log_lock for `log` (drain_spool
    does, so its insert, re-read verify and spool-file delete share one hold); a
    second msvcrt byte-range lock from this same process would just time out."""
    with _maybe_lock(log, lock_held):
        st_before = os.stat(log).st_mtime_ns
        with open(log, encoding="utf-8") as f:
            content = f.read()
        if os.stat(log).st_mtime_ns != st_before:
            raise BlockingIOError("log changed mid-read")
        if _is_duplicate_fail_open(content, entry, allow_duplicate):
            return False
        new = stamp_modified(insert_newest(content, entry))
        # Unique per attempt (2026-09-07): a fixed ".tmp-append" name raced every
        # concurrent writer over the SAME staging path -- two sessions appending
        # within the same instant could both hold it open at once, and Windows
        # would refuse the loser's os.replace with WinError 5 (see the module
        # docstring's LOCK section). _log_lock above now serializes this whole
        # block across runs of this script, which removes that race for the
        # common case; the name stays unique anyway as defense in depth for any
        # write that reaches here unlocked (the lock's own timeout fallback, or a
        # future caller that bypasses it) -- two processes can no longer collide
        # on the SAME tmp path even if they overlap.
        tmp = "%s.tmp-append.%d.%d" % (log, os.getpid(), time.time_ns())
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


def _inplace_insert(log, entry, allow_duplicate=False, lock_held=False):
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
    retry or spool, and the backup is left on disk for recovery. `lock_held`: see
    _atomic_insert."""
    with _maybe_lock(log, lock_held):
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


def _insert_or_inplace(log, entry, try_inplace, allow_duplicate=False, lock_held=False):
    """Try the atomic (os.replace) insert; if it fails (not a MalformedEntryError)
    and `try_inplace` is set, fall back to _inplace_insert. Returns
    True if written, False if recognized as a content-identical duplicate and
    correctly left unwritten (see _atomic_insert) -- both are successful,
    exception-free outcomes; only the caller needs to tell them apart. A
    MalformedEntryError from either path propagates immediately (retrying or
    falling back cannot help); any other ValueError -- notably a UnicodeDecodeError
    reading the log -- is an ordinary failure that retries and, in main(), spools. If both paths fail, raises the
    ATOMIC path's exception, since that's the one callers already log
    per-attempt."""
    try:
        return _atomic_insert(log, entry, allow_duplicate, lock_held)
    except MalformedEntryError:
        raise
    except Exception as atomic_exc:
        if not try_inplace:
            raise
        try:
            return _inplace_insert(log, entry, allow_duplicate, lock_held)
        except MalformedEntryError:
            raise
        except Exception:
            raise atomic_exc


def _entry_present(log, entry, anchor=None):
    """True iff `entry`'s full normalized text is in `log` as whole lines. Never
    raises (an unreadable log is "not present" -- the caller then KEEPS the spool
    file, which is the safe direction).

    Deliberately NOT is_duplicate_entry(): that splits the log on ENTRY_HEADER_RE,
    so an entry whose body itself contains a dated '## YYYY-MM-DD' line would never
    compare equal to any single block and could never verify -- drain would re-insert
    it (the block dedup misses it too) on every run, forever. And NOT a header-only
    check: identical headers are routine (see is_duplicate_entry), so a header match
    can be another entry's and prove nothing about this one's body.

    A line-bounded match also has to END where an entry ends: the next non-blank line
    must be a dated entry header, rollover's '---' pointer rule, or end of file
    (REFUTE 2026-11-05, C3). Without that, a spooled entry that is a strict prefix of
    a longer existing entry, or that is quoted mid-body in another entry, read as
    present. Residual: a verbatim quote that sits at the very END of another entry's
    body still matches. Only a writer that ignores the lock can erase the entry
    between insert and this check, so that narrow case needs two coincidences.

    '---' counts only as rollover's pointer rule, i.e. when the next non-blank line
    starts '*Entries at and before' -- a plain horizontal rule inside a longer entry
    is not an entry boundary (merge-gate review of #420, probe I).

    `anchor`: the line insert_newest anchored on for the insert being verified (see
    _insert_anchor). insert_newest goes above the FIRST '## ' line whether or not it
    is dated, so when a log's first '## ' is undated or malformed ('## Conventions',
    '## 2026-11-1') the freshly inserted entry is followed by that line, not a dated
    header; without accepting it, verify failed and the retry wrote a second copy
    (merge-gate C3 on #420). Only passed for the post-insert verify, where it is the
    exact line read under the same lock hold; the pre-insert "already there" check
    stays strict, because a false "present" there deletes a spool file that was
    never written.
    """
    try:
        with open(log, encoding="utf-8") as f:
            content = f.read()
        hay = "\n" + normalize_entry(content) + "\n"
        needle = "\n" + normalize_entry(entry) + "\n"
        anchor = anchor.rstrip() if anchor else None
        i = hay.find(needle)
        while i != -1:
            rest = hay[i + len(needle):].lstrip("\n")
            first, _, after = rest.partition("\n")
            if (not rest or ENTRY_HEADER_RE.match(first)
                    or (anchor is not None and first.rstrip() == anchor)
                    or (first.strip() == "---"
                        and after.lstrip("\n").startswith("*Entries at and before"))):
                return True
            i = hay.find(needle, i + 1)
        return False
    except Exception:
        return False


def _insert_anchor(log):
    """The line insert_newest(content, ...) would insert above right now: the first
    '## ' line after any frontmatter (same rule as insert_newest), or None (no '## '
    line: the entry goes at the end, where EOF is already a boundary). Never raises."""
    try:
        with open(log, encoding="utf-8") as f:
            content = f.read()
        body_start = 0
        if content.startswith("---\n"):
            end = content.find("\n---\n", 4)
            if end != -1:
                body_start = end + len("\n---\n")
        if content.startswith("## ", body_start):
            idx = body_start
        else:
            found = content.find("\n## ", body_start)
            if found == -1:
                return None
            idx = found + 1
        return content[idx:].split("\n", 1)[0]
    except Exception:
        return None


def drain_spool(log, attempts=3, lock_timeout=None):
    """Replay spooled entries (oldest-first) into `log`. Stops at the first one that
    still can't be written -- leaves it and the rest for next time (nothing is lost).
    Returns the count successfully drained (written-and-verified, or verified as an
    already-present duplicate).

    VERIFY BEFORE DELETE, UNDER ONE LOCK HOLD (2026-11-05). This used to delete
    each spool file as soon as _insert_or_inplace returned, without checking the
    entry was in the log -- and that insert ran under _log_lock, which fails OPEN
    after LOCK_ACQUIRE_TIMEOUT_S. rollover-event-log.py holds that same lock across
    its snapshot-read -> swap, so a drain that timed out wrote UNLOCKED into
    rollover's window, rollover's swap (built from the pre-drain snapshot) landed on
    top, and the entry was gone from the log with its spool file already deleted;
    both processes exited 0 (reproduced by
    _tests/test_append_event_log_drain_verify.py). Now, per entry: take _log_lock
    once; insert with lock_held=True; re-read the log (_entry_present); delete the
    spool file only if the entry is there -- all inside that one hold, so no
    lock-honouring writer (rollover included) can land between write, verify and
    delete.

    REFUSES RATHER THAN FAILING OPEN. If the lock cannot be taken within
    `lock_timeout` (default LOCK_ACQUIRE_TIMEOUT_S), this returns immediately,
    writing nothing and keeping every spool file. The fail-open in _log_lock exists
    so the CALLER'S NEW entry always lands somewhere; a spooled entry is already
    durable on disk, so replaying it is never urgent and failing open buys nothing
    except the race above. The lock is a byte-range lock the OS drops when its
    holder dies, so it cannot go stale -- a refused drain simply retries on the next
    append. One timeout per drain, not one per attempt: a held lock is not going to
    clear in the 0.2 s retry sleeps. Trade-off: under that contention main()'s own
    newer entry still fails open and lands first, so the deferred older entries
    drain in ABOVE it next run (newest-on-top inverted for those few). Order is
    cosmetic; the entries are dated and none is lost.

    Spool files whose first line is not a dated ENTRY_HEADER_RE header are LEFT
    PARKED (with a stderr note) and skipped, not deleted: main() never spools one,
    so such a file came from somewhere else and is a human's call; skipping keeps
    it from wedging the queue behind it. A file that is empty after strip() holds
    nothing to lose and is removed.

    DUPLICATE-SAFE WITHOUT ITS OWN CHECK (2026-08-12): each replay goes through
    _insert_or_inplace -> _atomic_insert / _inplace_insert, which do their own
    duplicate check, so a spooled entry already in `log` (two locked runs spooled
    the same content) is recognized and left unwritten -- and then verifies as
    present here. Never pass allow_duplicate=True: an unattended replay is exactly
    the case where forcing a duplicate through has no one to confirm it."""
    d = spool_dir_for(log)
    if not os.path.isdir(d):
        return 0
    if lock_timeout is None:
        lock_timeout = LOCK_ACQUIRE_TIMEOUT_S
    drained = 0
    for name in sorted(n for n in os.listdir(d) if n.endswith(".md")):
        p = os.path.join(d, name)
        try:
            with open(p, encoding="utf-8") as f:
                entry = f.read().lstrip("﻿").strip()
        except Exception:
            continue
        if not entry:
            try:
                os.remove(p)
            except OSError:
                pass
            continue
        if not ENTRY_HEADER_RE.match(entry.splitlines()[0]):
            sys.stderr.write("spool: %s has no dated '## YYYY-MM-DD' header -- left "
                             "parked for manual review, not drained\n" % p)
            continue
        verified = refused = False
        for attempt in range(attempts):
            try_inplace = (attempt + 1) >= min(INPLACE_FALLBACK_AFTER, attempts)
            with _log_lock(log, timeout=lock_timeout) as locked:
                if locked is False:
                    refused = True
                elif _entry_present(log, entry):
                    # Already there (an earlier drain wrote it but could not delete
                    # the spool file, or another run landed the same text). Checked
                    # BEFORE inserting because the block dedup in _atomic_insert
                    # misses entries whose body has a dated '##' line, and would
                    # write those again on every replay (REFUTE finding #2).
                    verified = True
                    try:
                        os.remove(p)
                    except OSError:
                        pass
                else:
                    # Read under this same hold, so it is the line the insert below
                    # anchors on (no lock-honouring writer can move it in between).
                    anchor = _insert_anchor(log)
                    try:
                        _insert_or_inplace(log, entry, try_inplace, lock_held=True)
                    except Exception:
                        pass  # retry below; the entry is still safe in its spool file
                    else:
                        if _entry_present(log, entry, anchor):
                            verified = True
                            try:
                                os.remove(p)
                            except OSError:
                                pass  # entry is in the log; next drain dedups + retries
            if verified or refused:
                break
            time.sleep(0.2 * (attempt + 1))
        if not verified:
            if refused:
                sys.stderr.write("spool: %s.lock is held by another writer -- drain "
                                 "deferred, spooled entries kept for the next run\n" % log)
            else:
                sys.stderr.write("spool: could not write+verify %s after %d attempts -- "
                                 "kept for the next run\n" % (p, attempts))
            break  # keep this + the rest, oldest-first order, for a later run
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
    # Validate the header UP FRONT (2026-09-22, /insights). insert_newest() checks only the
    # '## ' prefix, so an undated '## Foo' was written yet is not an entry to entry_blocks()
    # (ENTRY_HEADER_RE), and a prefix-less entry surfaced as a raw ValueError traceback.
    if not ENTRY_HEADER_RE.match(header):
        sys.stderr.write(
            "REJECTED: first line must be a dated entry header '## YYYY-MM-DD — <title>'.\n"
            "  got: %r\n  Nothing was appended. Match the newest existing entry's heading.\n"
            % header[:120])
        return 1

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
            # This read must be lock-guarded too (2026-09-07): it is a plain
            # open()-for-read, which on Windows does NOT grant FILE_SHARE_DELETE
            # (see the module docstring's LOCK section, and _HoldWithoutDeleteShare
            # in test-append-event-log.py, which simulates exactly this share mode
            # to reproduce the blocked-os.replace bug). Left unguarded, this read
            # reproduces the very race _log_lock exists to close: a losing process
            # could hold this file open just long enough for a concurrent winner's
            # os.replace to hit WinError 5 against it -- found live via the new
            # multi-process test in _tests/test_append_event_log_lock.py, which
            # still saw retries with only _atomic_insert/_inplace_insert guarded.
            with _log_lock(a.log):
                with open(a.log, encoding="utf-8") as f:
                    if header in f.read():
                        print("appended: %s" % header)
                        warn_if_uncommitted_backlog(a.log)
                        return 0
        except MalformedEntryError:
            raise  # NOT ValueError: a UnicodeDecodeError reading the log must retry + spool
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
