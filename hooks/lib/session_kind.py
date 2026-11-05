"""Is this hook payload's session scheduled/headless? (R-06 MCP delete gate)

WHY. Override tokens stand in for Gabriel's in-turn yes. A scheduled or headless session
has no human in the turn, so it must never mint or spend one; override_tokens.py states
that rule ("Scheduled/headless sessions must NEVER self-create one") but nothing enforced
it. This module gives gates the signal. session_liveness.py cannot: it reports OTHER live
sessions, not the kind of the current one.

SIGNALS, strongest first (verified on this machine 2026-10-19 / 2026-10-23):
  1. The Claude session stores. Each Desktop (claude-code-sessions) and Cowork/LAMS
     (local-agent-mode-sessions) session has a record local_*.json whose `cliSessionId`
     equals the hook payload's session_id; a scheduled firing's record carries
     `scheduledTaskId` (maintenance/ground-truth-run-index.py joins on the same key). A hit
     in either store counts the same. Live layout: <root>/<store>/<g>/<g>/local_*.json,
     `cliSessionId` within the first 120 bytes, `scheduledTaskId` anywhere (up to ~1.2 MB
     in), ~1290 records / ~690 MB across both stores (2026-10-23); 1482 / 818 MB on
     2026-11-05, growing about +25 records a day (by creation time, 1207 of today's
     records existed at the first scan timeout, 2026-10-27 17:31Z).
  2. CLAUDE_CODE_ENTRYPOINT starting with "sdk" (headless `claude -p` / SDK launches).

ENTRYPOINT CLASSES (C4). CLAUDE_CODE_ENTRYPOINT is lower-cased and stripped.
  OPEN   = unset/empty, "cli", "vscode", "claude-vscode" (a human at a terminal or IDE;
           these have no session record). A miss here is UNKNOWN.
  sdk*   = headless: always SCHEDULED.
  CLOSED = EVERY other value ("claude-desktop", "local-agent", "github-action", "remote",
           "bench", "claude-desktop-3p", any future value). A miss here is SCHEDULED
           (fail closed): the session must prove it is interactive with a fresh record.
UNKNOWN is therefore returned ONLY for OPEN entrypoints. UNKNOWN is a MISS, not a verdict:
callers must still NOT treat it as proof of an interactive session.

VERDICT (classify), in order:
  1. Any SCHEDULED EVIDENCE for this session (below), fresh or stale -> SCHEDULED
     ("scheduled wins": a newer forged/duplicate plain record cannot downgrade it). The
     task id comes only from a cleanly parsed record whose scheduledTaskId is a safe str.
  2. sdk* entrypoint -> SCHEDULED.
  3. empty/non-str session_id -> CLOSED: SCHEDULED; OPEN: UNKNOWN.
  4. INCOMPLETE SCAN (time budget spent, or a record file/dir that exists but could not
     be read) -> CLOSED: SCHEDULED; OPEN: UNKNOWN. A partial scan NEVER yields
     INTERACTIVE. Rationale: a backdated real scheduled record (mtime set years back) or an
     older scheduled duplicate can sit in ANY unscanned file, and mtime is attacker-
     controlled, so no "covered every file newer than the match / inside the freshness
     window" rule proves that nothing unscanned could change the verdict (K23, T1-backdate).
  5. CLOSED and a FRESH file carrying b"scheduledTaskId" that is not valid UTF-8 (its
     owner cannot be read) -> SCHEDULED.
  6. A FRESH (mtime within RECENT_SECONDS) cleanly parsed record for this session without
     the key -> INTERACTIVE. A stale plain record is not proof.
  7. otherwise CLOSED: SCHEDULED ("no readable record: fail closed"); OPEN: UNKNOWN.

SCHEDULED EVIDENCE (C5). Judged per file on the full bytes (plain reads, no mmap), for
CANDIDATE files only (PREFIX SCAN below):
  - Parses (<= MAX_RECORD_BYTES, UTF-8 with optional BOM, or UTF-16/32 detected by a NUL in
    the first 4 bytes) to a dict: it is this session's iff cliSessionId == session_id
    after JSON unescaping; evidence iff it also has the scheduledTaskId key (any value).
    A cleanly parsed record of ANOTHER session is never evidence, whatever it contains.
  - Oversized, unparseable, undecodable, or not a dict (list-wrapped): evidence iff it
    contains b"scheduledTaskId" AND the session id, each plain or after unescaping
    `\\u00XX` ASCII escapes in the raw bytes (escape marker `\\u00[2-7]X`: the only way
    JSON can spell an id char or key letter other than literally).

PREFIX SCAN (C1/C2, round 2). Only the first PREFIX_BYTES (16 KB) of every record file is
read (open(..., 'rb').read; no mmap: an ACCESS_READ mapping blocked the app's own
writeFileSync of the record, C13). Live: cliSessionId sits within the first ~120 bytes of
every record. A file is a CANDIDATE iff its prefix
  - contains this session's id (plain bytes), or
  - contains b"\\u00" (a JSON escape could hide the id or a key), or
  - cannot be decoded as expected (NUL in the first 4 bytes = UTF-16/32, or invalid UTF-8;
    a multi-byte char cut by the prefix boundary is not invalid), or
  - has no '"cliSessionId"' key, or does not start (after BOM/whitespace) with '{'
    (list-wrapped or otherwise unusual), or
  - the id has JSON-escapable chars (no literal needle: every file is a candidate).
Non-candidate files are never read past the prefix, whatever their size (a 300 MB decoy
costs one 16 KB read). A candidate is then read in full, bounded by HARD_MAX_BYTES (64 MB):
a larger candidate is not read and counts as an unreadable file (incomplete scan), UNLESS
its prefix cleanly names ANOTHER session (C6, _names_other: object start, decodes, no NUL
in the first 4 bytes, no `\\u00` marker, exactly one '"cliSessionId"' key whose plain value
is not this session's id); such a file is skipped, so one large record of another session
cannot make every session SCHEDULED. A large record whose prefix names THIS session, or
is ambiguous (duplicate key, escape, list-wrapped, empty value), stays incomplete. The
soft budget is checked between files and between steps inside the judge.
An interactive verdict needs a complete pass: one open and one 16 KB read per file, a
full read + parse normally only for this session's own record(s). BUDGET_SECONDS stays
12 s as the inner SOFT budget (the dispatcher's per-guard timeout is 60 s; classify runs
only on delete-shaped MCP calls and on override/session-store path hits).

PARALLEL READ (OI-396, 2026-11-05). The cost of that pass is the open() itself, not the
bytes: Microsoft Defender's on-access scan runs inside CreateFile whenever a record is
opened while it is not in Defender's clean-file cache (the cache goes cold, for example,
after a security-intelligence update, 1-3 a day here, and for one file whenever it is
rewritten). Measured read-only on the live store (1482 records, 818 MB): a cold serial
pass took 31.1 s, 29.7 s of it in open() (~20 ms per record), and an immediate second
pass took 1.0 s. Serial, a cold pass ran past the 12 s budget AND the 20 s hard wall, so
attended Desktop deletes failed closed (2026-10-27, three times on 2026-11-05); the store
crossed that size around 2026-10-27.
OneDrive placeholders, directory junctions, locked records and disk I/O were ruled out by
the same measurement. The cold cost parallelizes (fresh files, this machine: 27.5 ms per
file serial, 3.0 ms per file of wall time with 8 readers, 2.6 ms with 16), so records are
now read by SCAN_WORKERS daemon threads (_inspect_all), dispatched newest mtime first.
Dispatch stops at the first scheduled evidence; readers already in flight finish their
current record. The outcomes are then folded newest first: the first scheduled evidence
decides, so evidence in ANY inspected record wins even when an earlier record was never
inspected; anything uninspected, unreadable or budget-cut leaves the scan incomplete. The
readers are DAEMON threads (a pool the interpreter joins at exit would hold a hook process
open past its timeout on one blocked read, and a hook timeout lets the delete through);
the coordinator joins them only until the soft-budget deadline and folds a snapshot, so a
reader that finishes later cannot change the verdict.

HARD WALL LIMIT AND RETRY (C5, round 3). The soft budget is only checked between
operations, so one blocking open()/read() could stall classify past the hook timeout.
classify() therefore runs each attempt (store enumeration + scan) in a daemon thread and
joins it with the remaining time of a HARD_JOIN_SECONDS (20 s) wall. A thread still
running at the wall is an INCOMPLETE scan (same verdict rule 4: CLOSED -> SCHEDULED,
OPEN -> UNKNOWN); the abandoned thread publishes only into a per-attempt box that is never
read again. Record reads run in the reader threads, which the attempt waits for only
until its soft budget, so the wall is now reached only when the attempt's own thread
blocks (store enumeration, a directory listing, or the inline read used when no reader
thread could be started): the evidence says "hard wall" then, and "time budget" when the
readers were merely slow. Once scheduled evidence is found, a reader still blocked on
another record holds classify until the soft budget; the verdict is unaffected (SCHEDULED
either way). Retry-once: when an attempt found NO
scheduled evidence, ended incomplete (budget, read error, internal error) and more than
JOIN_SLACK_SECONDS of wall time remains, one more full attempt runs with budget
min(BUDGET_SECONDS, remaining - JOIN_SLACK_SECONDS), so its budget ends before the join
gives up (before 2026-11-05 the two were equal, and a merely slow second attempt raced
the wall and was mislabelled a blocking read). Only that last attempt's result decides,
so a retry never turns a partial scan into INTERACTIVE. A retry re-reads records the first
attempt already opened at warm-cache cost. Scheduled evidence still stops the scan at once
(no retry). scan() and the scan_records/find_record(s) helpers stay synchronous single
attempts (their reads still use the reader threads).
RESIDUAL OF THE PREFIX SCAN. A record is attributed to a session by what its first 16 KB
say. A session that rewrites its OWN real record (pushes cliSessionId past 16 KB behind a
decoy '"cliSessionId"' of another session, renames keys, adds a later duplicate
cliSessionId key, which json.loads would let win) is residual class (a) below, defended
only by the mint-guard. Forged EXTRA records can still only push toward SCHEDULED.

BOUNDED DISCOVERY. store_dirs() does not call discover_store() (unbounded recursive glob;
a directory-junction loop made classify() hang past the hook timeout). It walks each
standard root's claude-code-sessions and local-agent-mode-sessions dir with os.scandir to
depth <= 3, skipping symlinks/junctions, visiting each realpath once, including
dot-prefixed names, under the BUDGET_SECONDS wall clock.

KNOWN RESIDUALS. (a) A session with unrestricted shell can rewrite its own record so it
no longer names itself (rename the scheduledTaskId key, change or duplicate-key the
cliSessionId value, push it past the prefix), or move/hide/delete it (beyond depth 3,
outside the standard roots, or renamed so it no longer matches local_*.json). While the
entry stays listed, ACL-deny and a path over MAX_PATH are caught as incomplete
(_still_listed), a record directory whose name ends in a dot is always unreadable (Win32
strips the dot, so a listing would read a same-named sibling or nothing), and store_dirs()
keeps every enumerated directory, case-sensitive siblings ('x', 'X') included (REFUTE
pass 2026-11-05). The defense is the Task 5 mint-guard (hooks/override-mint-guard.py), which
refuses shell/file ops naming the session store from scheduled sessions. Its
_SESSION_STORE_MARKERS currently lists ONLY "claude-code-sessions"; adding
"local-agent-mode-sessions" there is a separate follow-up (Cowork/LAMS sessions appear
not to run host hooks, so the marker gap is not known to be reachable). (b) Another
session's scheduled record that is corrupt AND mentions this session's id in its text
would count as evidence (false SCHEDULED; fails closed).

Never raises: internal errors are an incomplete scan (fail closed for CLOSED entrypoints).

ORA_SESSION_STORE_DIRS is a TEST SEAM ONLY (os.pathsep-separated). It must never be set
in settings.json's env block or any scheduled context; test-session-kind.py asserts the
tracked settings.json does not set it.

Stdlib only. ASCII-only. Windows (`python`).
"""
import codecs
import json
import os
import re
import sys
import threading
import time

SCHEDULED = "scheduled"
INTERACTIVE = "interactive"
UNKNOWN = "unknown"

ENV_STORE_DIRS = "ORA_SESSION_STORE_DIRS"
ENV_ENTRYPOINT = "CLAUDE_CODE_ENTRYPOINT"
HEADLESS_ENTRYPOINT_PREFIX = "sdk"
DESKTOP_ENTRYPOINT = "claude-desktop"
OPEN_ENTRYPOINTS = frozenset(("", "cli", "vscode", "claude-vscode"))
STORES = ("claude-code-sessions", "local-agent-mode-sessions")
RECENT_SECONDS = 7 * 86400
MAX_RECORD_BYTES = 4 * 1024 * 1024
PREFIX_BYTES = 16 * 1024
HARD_MAX_BYTES = 64 * 1024 * 1024
MAX_DEPTH = 3
BUDGET_SECONDS = 12.0
HARD_JOIN_SECONDS = 20.0
MAX_ATTEMPTS = 2
SCAN_WORKERS = 8
JOIN_SLACK_SECONDS = 0.1
_GONE = "_gone"    # outcome tag: the record vanished mid-scan (not an error)
_ERROR = "_error"  # outcome tag: the record exists but could not be read (incomplete)
_TASK_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,128}$")
_SCHED_KEY = b"scheduledTaskId"
_CLI_KEY = b'"cliSessionId"'
_ESC_PREFIX = chr(92).encode() + b"u00"
_BOM = b"\xef\xbb\xbf"
# A JSON escape of an ASCII char in 0x20-0x7F: the only way to spell an id char or a key
# letter other than literally. Backslash written as chr(92) for clarity.
_ESC_RE = re.compile(re.escape(chr(92).encode()) + rb"u00[2-7][0-9a-fA-F]")
# A "cliSessionId": "<value>" pair whose value has no quote, backslash or control byte.
_CLI_PAIR_RE = re.compile(rb'"cliSessionId"[ \t\r\n]*:[ \t\r\n]*"([^"\\\x00-\x1f]+)"')

_HERE = os.path.dirname(os.path.abspath(__file__))
_SHARED = os.path.join(os.path.dirname(os.path.dirname(_HERE)), "maintenance", "_shared")


class _Budget(object):
    """Monotonic-clock budget (immune to wall-clock steps) shared by enumeration and the record scan. `hit` latches."""

    def __init__(self, seconds):
        self.deadline = time.monotonic() + seconds
        self.hit = False

    def expired(self):
        if not self.hit and time.monotonic() > self.deadline:
            self.hit = True
        return self.hit


def _is_link(path):
    """True for symlinks and Windows directory junctions / any reparse point."""
    try:
        if os.path.islink(path):
            return True
        isj = getattr(os.path, "isjunction", None)
        if isj is not None and isj(path):
            return True
        attrs = getattr(os.lstat(path), "st_file_attributes", 0)
        return bool(attrs & 0x400)
    except OSError:
        return True


def _entry_is_link(e):
    """_is_link for a DirEntry, from the metadata the directory listing already returned
    (Windows: st_file_attributes is cached by scandir, no extra syscall)."""
    try:
        attrs = getattr(e.stat(follow_symlinks=False), "st_file_attributes", None)
    except OSError:
        return True
    if attrs is None:
        return _is_link(e.path)
    return e.is_symlink() or bool(attrs & 0x400)


def _enum_dirs(base, budget, seen=None):
    """base plus its sub-directories to depth <= MAX_DEPTH. No glob, no recursion into
    symlinks/junctions/reparse points, dot-prefixed names included, bounded by the
    wall-clock budget. Only base is realpath-deduplicated (against `seen`, shared across
    bases): below it no link is followed, so every child is a distinct real directory."""
    out = []
    seen = set() if seen is None else seen
    try:
        rp = os.path.normcase(os.path.realpath(base))
    except OSError:
        return out
    if rp in seen or not os.path.isdir(base):
        return out
    seen.add(rp)
    queue = [(base, 0)]
    while queue:
        if budget.expired():
            break
        path, depth = queue.pop(0)
        out.append(path)
        if depth >= MAX_DEPTH:
            continue
        try:
            with os.scandir(path) as it:
                for e in it:
                    try:
                        if e.is_dir(follow_symlinks=False) and not _entry_is_link(e):
                            queue.append((e.path, depth + 1))
                    except OSError:
                        continue
        except OSError:
            continue
    return out


def _store_bases():
    """Base dirs of every session store under every standard Claude root."""
    bases = []
    try:
        if _SHARED not in sys.path:
            sys.path.insert(0, _SHARED)
        import store_discovery  # noqa: E402
        for store in STORES:
            bases.extend(store_discovery.store_bases(store))
    except BaseException:
        bases = []
    if not bases:
        appdata = os.environ.get("APPDATA") or os.path.join(
            os.path.expanduser("~"), "AppData", "Roaming")
        bases = [os.path.join(appdata, "Claude", s) for s in STORES]
    return bases


def _root_record_dirs(budget):
    """Record dirs under the standard Claude roots, independent of scheduled-tasks.json.

    Layout: <root>/<store>/<group>/<group>/local_*.json for both STORES. Bounded scandir
    walk (see _enum_dirs); the root list is store_discovery.store_bases, but
    discover_store() is NOT called (its unbounded recursive glob hangs on a junction
    loop)."""
    found, seen = [], set()
    for base in _store_bases():
        try:
            found.extend(_enum_dirs(base, budget, seen))
        except Exception:
            continue
    return found


def store_dirs(budget=None):
    """Directories holding local_*.json records. [] when nothing is found."""
    seam = os.environ.get(ENV_STORE_DIRS)
    if seam is not None:
        return [d for d in seam.split(os.pathsep) if d]
    budget = _Budget(BUDGET_SECONDS) if budget is None else budget
    out = []
    try:
        out.extend(_root_record_dirs(budget))
    except BaseException:
        pass
    seen, uniq = set(), []
    for d in out:
        # Exact-string key. _enum_dirs already yields each real directory once (bases are
        # realpath-deduplicated, links are never followed). abspath() would apply Win32 name
        # normalization, folding a trailing-dot dir ('g.') into a same-named sibling ('g'),
        # and normcase() would fold case-sensitive siblings ('x', 'X'); either drops a real
        # record directory (REFUTE pass 2026-11-05).
        key = d
        if key not in seen:
            seen.add(key)
            uniq.append(d)
    return uniq


def _parse_record(raw):
    """Parsed dict from raw UTF-8 bytes (BOM tolerated), or None (unparseable, undecodable
    or not a dict)."""
    try:
        rec = json.loads(raw.decode("utf-8-sig"))
    except Exception:
        return None
    return rec if isinstance(rec, dict) else None


def _prefilter_needle(session_id):
    """Bytes of the id as JSON would write it literally, or None to parse every candidate.

    A plain ASCII uuid-like id appears verbatim in the JSON text. If the id has chars
    JSON would escape, no prefilter is applied."""
    try:
        if not all(32 < ord(c) < 127 and c not in ('"', chr(92)) for c in session_id):
            return None
        return session_id.encode("ascii")
    except Exception:
        return None


def _unescape_ascii(raw):
    """raw with every `\\u00XX` (XX in 0x20-0x7F) escape replaced by its byte."""
    return _ESC_RE.sub(lambda m: bytes([int(m.group(0)[2:], 16)]), raw)


def _decodes(buf):
    try:
        bytes(buf).decode("utf-8-sig")
        return True
    except UnicodeDecodeError:
        return False


class _TooBig(OSError):
    """A candidate record larger than HARD_MAX_BYTES: not read, counts as unreadable."""


def _names_other(prefix, session_id):
    """True when `prefix` cleanly attributes its record to ANOTHER session (C6): it starts
    (after BOM/whitespace) with '{', decodes as UTF-8 (a char cut at the end is allowed),
    has no NUL in the first 4 bytes and no `\\u00` escape marker, carries EXACTLY ONE
    '"cliSessionId"' key, and that key's plain string value is not session_id. Used only to
    skip an oversized candidate instead of marking the scan incomplete."""
    try:
        if b"\x00" in prefix[:4] or prefix.find(_ESC_PREFIX) >= 0:
            return False
        body = prefix[3:] if prefix.startswith(_BOM) else prefix
        if not body.lstrip().startswith(b"{"):
            return False
        codecs.getincrementaldecoder("utf-8")().decode(prefix, final=False)
        if prefix.count(_CLI_KEY) != 1:
            return False
        m = _CLI_PAIR_RE.search(prefix)
        if m is None:
            return False
        return m.group(1).decode("utf-8") != session_id
    except Exception:
        return False


def _is_candidate(prefix, needle, whole):
    """True when the file whose first bytes are `prefix` must be read in full and judged.
    whole: prefix is the entire file (so a truncated trailing UTF-8 char is invalid)."""
    if needle is None:
        return True
    if b"\x00" in prefix[:4]:
        return True  # UTF-16/32
    if prefix.find(needle) >= 0 or prefix.find(_ESC_PREFIX) >= 0:
        return True
    try:
        codecs.getincrementaldecoder("utf-8")().decode(prefix, final=whole)
    except UnicodeDecodeError:
        return True
    body = prefix[3:] if prefix.startswith(_BOM) else prefix
    if not body.lstrip().startswith(b"{"):
        return True
    return prefix.find(_CLI_KEY) < 0


def _judge(buf, fresh, session_id, needle, budget=None):
    """(verdict, task_id) for one record's bytes. verdict: None (not this session's, or
    nothing to learn), "sched", "plain" (this session, no key; task_id is the record),
    "undecodable_sched" (fresh, carries the key, owner unreadable), or "budget" (the
    budget ran out mid-judge; the scan is incomplete)."""
    def spent():
        return budget is not None and budget.expired()
    if b"\x00" in buf[:4]:
        # UTF-16/32 JSON (json.detect_encoding): normalize to UTF-8 bytes first.
        raw = bytes(buf)
        try:
            buf = raw.decode(json.detect_encoding(raw)).encode("utf-8")
        except Exception:
            return None, None
    has_id = needle is None or buf.find(needle) >= 0
    has_esc = _ESC_RE.search(buf) is not None
    rec = None
    if has_id or has_esc:
        if spent():
            return "budget", None
        if len(buf) <= MAX_RECORD_BYTES:
            rec = _parse_record(bytes(buf))
        if rec is not None:
            if rec.get("cliSessionId") != session_id:
                return None, None
            if "scheduledTaskId" in rec:
                v = rec.get("scheduledTaskId")
                return "sched", (v if isinstance(v, str) and _TASK_ID_RE.match(v) else None)
            if spent():
                return "budget", None
            return "plain", rec
    # Not a clean dict (oversized, unparseable, undecodable, list-wrapped) or no id at all.
    if not (has_id or has_esc or fresh):
        return None, None  # cannot name this session; the undecodable rule is fresh-only
    if spent():
        return "budget", None
    has_sched = buf.find(_SCHED_KEY) >= 0
    ub = None
    if has_esc:
        ub = _unescape_ascii(bytes(buf))
        has_sched = has_sched or ub.find(_SCHED_KEY) >= 0
    if not has_sched:
        return None, None
    if has_id or has_esc:
        ours = has_id or (ub is not None and ub.find(needle) >= 0)
        if ours:
            return "sched", None
    if fresh and not _decodes(buf):
        return "undecodable_sched", None
    return None, None


def _inspect(p, mtime, now, session_id, needle, budget=None):
    """Prefix-scan one file, then _judge() it if it is a candidate. Plain reads only (no
    mmap). Raises OSError on read errors and _TooBig for a candidate over HARD_MAX_BYTES."""
    fresh = now - mtime <= RECENT_SECONDS
    with open(p, "rb") as fh:
        head = fh.read(PREFIX_BYTES + 1)  # +1: tells "exactly PREFIX_BYTES" from "more"
        whole = len(head) <= PREFIX_BYTES
        if not _is_candidate(head, needle, whole):
            return None, None
        if whole:
            buf = head
        else:
            if os.fstat(fh.fileno()).st_size > HARD_MAX_BYTES:
                if _names_other(head[:PREFIX_BYTES], session_id):
                    return None, None  # C6: another session's oversized record
                raise _TooBig(p)
            if budget is not None and budget.expired():
                return "budget", None
            buf = head + fh.read(HARD_MAX_BYTES + 1 - len(head))
            if len(buf) > HARD_MAX_BYTES:
                if _names_other(head[:PREFIX_BYTES], session_id):
                    return None, None
                raise _TooBig(p)
    return _judge(buf, fresh, session_id, needle, budget)


def _still_listed(path):
    """True when `path`'s own name is still in its parent directory's listing although
    opening it by that name just failed as not-found: the entry exists but this path cannot
    reach it (a Win32 path over MAX_PATH, or a name ending in a dot, which Win32 strips), so
    it is UNREADABLE, not gone. False when the parent no longer lists the name
    or is itself gone (a record removed mid-scan is merely gone). Any other failure to
    list the parent counts as listed (fail closed). Never raises."""
    try:
        parent, name = os.path.split(path)
        if not name:
            return False
        want = os.path.normcase(name)
        with os.scandir(parent or ".") as it:
            for e in it:
                if os.path.normcase(e.name) == want:
                    return True
        return False
    except (FileNotFoundError, NotADirectoryError):
        return False
    except Exception:
        return True


def _record_paths(d):
    """(entries, errors): (mtime, path) for local_*.json regular files directly in d
    (scandir; links skipped; mtime from the listing's cached metadata on Windows).
    errors counts a d that exists but could not be listed -- including a d whose own
    parent still lists it although listing d by this path says not-found (_still_listed),
    and a d whose name ends in a dot, which Win32 strips, so listing it reads a different
    directory (a same-named sibling, silently) or none -- and entries whose metadata could
    not be read (a missing d or a file gone mid-scan is not an error)."""
    out, errors = [], 0
    name = os.path.basename(d.rstrip(chr(92) + "/"))
    if name.endswith(".") and name not in (".", ".."):
        return out, 1
    try:
        with os.scandir(d) as it:
            for e in it:
                n = e.name
                if not (n.startswith("local_") and n.endswith(".json")):
                    continue
                try:
                    if e.is_file(follow_symlinks=False):
                        out.append((e.stat(follow_symlinks=False).st_mtime, e.path))
                except FileNotFoundError:
                    continue
                except OSError:
                    errors += 1
    except (FileNotFoundError, NotADirectoryError):
        return out, errors + (1 if _still_listed(d) else 0)
    except OSError:
        return out, errors + 1
    return out, errors


class ScanResult(object):
    """Outcome of one store scan. complete is False when the budget ran out or a listed
    file/dir could not be read; only a complete scan may support INTERACTIVE."""

    def __init__(self):
        self.scheduled = False
        self.task_id = None
        self.fresh = []
        self.stale = []
        self.undecodable_sched = False
        self.unreadable = 0
        self.complete = False
        self.files = 0
        self.inspected = 0
        self.budget_hit = False  # set by _attempt: the soft budget ran out
        self.timed_out = False   # set by classify: the HARD_JOIN wall limit was reached


def _inspect_all(entries, now, session_id, needle, budget):
    """(outcomes, settled) for entries [(mtime, path), ...], sorted newest first.

    Up to SCAN_WORKERS daemon reader threads take the entries IN ORDER and _inspect() each.
    outcomes[i] is _inspect's (verdict, extra), (_GONE, None) or (_ERROR, None) -- a
    not-found entry its directory still lists, and any other failure to read entry i
    (BaseException included), is _ERROR -- or None when entry i was
    never inspected (budget spent, dispatch stopped at scheduled evidence, or its reader
    still busy). A "sched" outcome stops dispatch; readers already in flight finish their
    current record. The join waits for the readers until budget.deadline only: settled is
    False when a reader was still running then, and budget.hit is set. The returned list is a
    snapshot taken under the lock, so a reader that finishes later writes only into the
    original list, which nothing reads again. Never raises."""
    n = len(entries)
    outcomes = [None] * n
    if not n:
        return outcomes, True
    lock = threading.Lock()
    state = {"next": 0, "stop": False}

    def take():
        with lock:
            if state["stop"] or state["next"] >= n:
                return -1
            i = state["next"]
            state["next"] = i + 1
            return i

    def work():
        try:
            while True:
                i = take()
                if i < 0 or budget.expired():
                    return
                mtime, p = entries[i]
                try:
                    out = _inspect(p, mtime, now, session_id, needle, budget)
                except FileNotFoundError:
                    # Gone mid-scan, unless the directory still lists it (unreadable).
                    out = (_ERROR if _still_listed(p) else _GONE, None)
                except BaseException:
                    out = (_ERROR, None)
                with lock:
                    outcomes[i] = out
                    if out[0] == "sched":
                        state["stop"] = True
        except BaseException:
            return

    threads = []
    for _ in range(min(n, SCAN_WORKERS)):
        try:
            t = threading.Thread(target=work, name="session-kind-read")
            t.daemon = True
            t.start()
        except Exception:
            break
        threads.append(t)
    if not threads:
        work()  # no reader thread could start: read inline (classify's hard wall still applies)
    settled = True
    for t in threads:
        t.join(max(0.0, budget.deadline - time.monotonic()))
        if t.is_alive():
            settled = False
            break
    with lock:
        state["stop"] = True
        snap = list(outcomes)
    if not settled:
        budget.hit = True
    return snap, settled


def scan(session_id, dirs=None, budget=None):
    """Scan the stores for session_id: records are read in parallel (see _inspect_all), and
    the outcomes are folded newest mtime first; the first scheduled evidence decides."""
    res = ScanResult()
    if not isinstance(session_id, str) or not session_id:
        res.complete = True
        return res
    budget = _Budget(BUDGET_SECONDS) if budget is None else budget
    dirs = store_dirs(budget) if dirs is None else dirs
    needle = _prefilter_needle(session_id)
    entries = []
    for d in dirs:
        if budget.expired():
            break
        found, errors = _record_paths(d)
        res.unreadable += errors
        entries.extend(found)
    entries.sort(reverse=True)
    res.files = len(entries)
    now = time.time()
    outcomes, covered = _inspect_all(entries, now, session_id, needle, budget)
    for (mtime, _p), out in zip(entries, outcomes):
        if out is None:
            covered = False  # never inspected; scheduled evidence elsewhere still decides
            continue
        verdict, extra = out
        if verdict == _GONE:
            continue
        if verdict == _ERROR:
            res.unreadable += 1
            continue
        if verdict == "budget":
            covered = False
            continue
        res.inspected += 1
        if verdict == "sched":
            res.scheduled, res.task_id = True, extra
            break
        if verdict == "plain":
            (res.fresh if now - mtime <= RECENT_SECONDS else res.stale).append(extra)
        elif verdict == "undecodable_sched":
            res.undecodable_sched = True
    res.complete = covered and not budget.hit and res.unreadable == 0
    return res


def scan_records(session_id, dirs=None, budget=None):
    """(fresh, stale) plain records for session_id, newest first. Compatibility wrapper:
    stops at scheduled evidence, which is not returned here; prefer classify()."""
    res = scan(session_id, dirs, budget)
    return res.fresh, res.stale


def find_records(session_id, dirs=None):
    """Recent plain records whose cliSessionId == session_id, newest first. [] on none."""
    return scan_records(session_id, dirs)[0]


def store_discoverable(dirs=None):
    """True when at least one store directory exists."""
    try:
        dirs = store_dirs() if dirs is None else dirs
        return any(os.path.isdir(d) for d in dirs)
    except Exception:
        return False


def find_record(session_id, dirs=None):
    """The newest recent plain record for session_id, or None. Prefer classify()."""
    recs = find_records(session_id, dirs)
    return recs[0] if recs else None


def _entrypoint(env):
    ep = env.get(ENV_ENTRYPOINT) or ""
    return ep.strip().lower() if isinstance(ep, str) else ""


def _attempt(session_id, dirs, seconds):
    """One full store enumeration + scan under a fresh soft budget. Runs in the worker
    thread; touches no state shared with the caller (returns a new ScanResult)."""
    budget = _Budget(seconds)
    try:
        d = store_dirs(budget) if dirs is None else list(dirs)
        res = scan(session_id, d, budget)
    except Exception:
        res = ScanResult()
    res.budget_hit = budget.hit
    return res


def _bounded_attempt(session_id, dirs, seconds, wait):
    """_attempt in a daemon thread joined for at most `wait` seconds. Returns its
    ScanResult, or None when the thread is still running (a blocking open()/read() the
    soft budget cannot interrupt) or could not be started. The worker publishes only into
    its own per-call box and Event; after a timeout the caller never reads that box, so an
    abandoned worker (which may still hold a file handle) cannot affect the verdict."""
    box = {}
    done = threading.Event()

    def work():
        try:
            box["res"] = _attempt(session_id, dirs, seconds)
        except BaseException:
            box["res"] = None
        finally:
            done.set()
    try:
        t = threading.Thread(target=work, name="session-kind-scan")
        t.daemon = True
        t.start()
    except Exception:
        return None
    if not done.wait(max(0.0, wait)):
        return None
    return box.get("res")


def _scan_with_retry(session_id, dirs):
    """(res, attempts). Up to MAX_ATTEMPTS bounded attempts inside one HARD_JOIN_SECONDS
    wall: a retry runs only when the previous attempt found NO scheduled evidence, was
    incomplete (budget, read error, internal error) and wall time remains. Only the last
    attempt's result is used (a retry never merges a partial scan into INTERACTIVE), except
    that fresh-undecodable-with-key evidence from any attempt is kept (fail closed)."""
    deadline = time.monotonic() + HARD_JOIN_SECONDS
    res, attempts, undec = None, 0, False
    while attempts < MAX_ATTEMPTS:
        remaining = deadline - time.monotonic()
        if attempts and remaining <= JOIN_SLACK_SECONDS:
            break
        attempts += 1
        # The soft budget ends JOIN_SLACK_SECONDS before the join gives up, so an attempt
        # that is merely slow returns its own (budget) result instead of racing the wall.
        soft = min(BUDGET_SECONDS, remaining - JOIN_SLACK_SECONDS)
        r = _bounded_attempt(session_id, dirs, soft, remaining)
        if r is None:
            r = ScanResult()
            r.timed_out = True
        undec = undec or r.undecodable_sched
        res = r
        if r.scheduled or r.complete or r.timed_out:
            break
    res.undecodable_sched = undec
    return res, attempts


def classify(session_id, env=None, dirs=None):
    """(kind, task_id, evidence). task_id comes only from a session record.

    See the module docstring (VERDICT, HARD WALL LIMIT) for the exact order. Never
    raises."""
    env = os.environ if env is None else env
    ep = _entrypoint(env)
    closed = ep not in OPEN_ENTRYPOINTS
    label = ep or "cli"
    try:
        res, attempts = _scan_with_retry(session_id, dirs)
    except Exception:
        res, attempts = ScanResult(), 0
    if res.scheduled:
        return SCHEDULED, res.task_id, "session record carries scheduledTaskId"
    if ep.startswith(HEADLESS_ENTRYPOINT_PREFIX):
        return SCHEDULED, None, "headless entrypoint"
    if not isinstance(session_id, str) or not session_id:
        if closed:
            return SCHEDULED, None, "%s session with no session_id: fail closed" % label
        return UNKNOWN, None, "no session_id"
    if not res.complete:
        if res.timed_out:
            why = ("store scan incomplete: still running at the %.0f s hard wall limit "
                   "(blocked store I/O)" % HARD_JOIN_SECONDS)
        else:
            why = ("store scan hit the time budget" if res.budget_hit else
                   "store scan incomplete (unreadable record files or internal error)")
            why += "; %d of %d record files inspected" % (res.inspected, res.files)
        why += " after %d attempt%s" % (attempts, "" if attempts == 1 else "s")
        if closed:
            return SCHEDULED, None, "%s session, %s: fail closed" % (label, why)
        return UNKNOWN, None, why
    if closed and res.undecodable_sched:
        return SCHEDULED, None, ("%s session, a fresh undecodable record carries "
                                 "scheduledTaskId: fail closed" % label)
    if res.fresh:
        return INTERACTIVE, None, "session record without scheduledTaskId"
    if closed:
        return SCHEDULED, None, "%s session with no readable record: fail closed" % label
    return UNKNOWN, None, "no session record"
