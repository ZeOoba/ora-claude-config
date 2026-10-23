"""Is this hook payload's session scheduled/headless? (R-06 MCP delete gate)

WHY. Override tokens stand in for Gabriel's in-turn yes. A scheduled or headless session
has no human in the turn, so it must never mint or spend one; override_tokens.py states
that rule ("Scheduled/headless sessions must NEVER self-create one") but nothing enforced
it. This module gives gates the signal. session_liveness.py cannot: it reports OTHER live
sessions, not the kind of the current one.

SIGNALS, strongest first (verified on this machine 2026-10-19):
  1. The Claude Desktop session store. Each Desktop session has a record local_*.json
     whose `cliSessionId` equals the hook payload's session_id; a scheduled firing's
     record carries `scheduledTaskId` (maintenance/ground-truth-run-index.py joins on the
     same key). The store is the directory holding the CC scheduled-tasks.json, found by
     maintenance/_shared/store_discovery.py, the single discovery implementation.
  2. CLAUDE_CODE_ENTRYPOINT starting with "sdk" (headless `claude -p` / SDK launches).
     The interactive Desktop value observed is "claude-desktop"; a headless value has not
     been observed here (plan risk R3).
A plain interactive CLI session has no Desktop record and a non-sdk entrypoint: UNKNOWN.
FAIL CLOSED FOR DESKTOP (C1b). Every Desktop-hosted session (entrypoint "claude-desktop",
case-insensitive) has a record, and a scheduled session can tamper with its own record
(backdate mtime, pad past the size cap, add a BOM, wrap in a list, rename keys). So when
the entrypoint is claude-desktop and NO valid in-window record for this session is found
(whether or not any store is discoverable: blanking scheduled-tasks.json hides nothing,
because store_dirs() also globs the standard roots), the answer is SCHEDULED ("desktop session
with no readable record: fail closed"), never UNKNOWN. A matching record older than the
7-day window still counts as evidence of SCHEDULED (long-running scheduled sessions).
UNKNOWN is now returned ONLY for non-Desktop entrypoints without a record or an
empty/non-str session_id. UNKNOWN is a MISS, not a verdict:
callers must still NOT treat it as proof of an interactive session. Scheduled wins: any
record for the session carrying the scheduledTaskId key (any value) means SCHEDULED.
Residual: renaming only the scheduledTaskId key inside an otherwise valid in-window
record is indistinguishable from an interactive record.

BOUNDED DISCOVERY (C4). store_dirs() does not call discover_store() (unbounded recursive
glob; a directory-junction loop under claude-code-sessions made classify() hang past the
hook timeout, failing the gate open). It walks each standard root's claude-code-sessions
dir with os.scandir to depth <= 3, skipping symlinks/junctions, visiting each realpath
once, including dot-prefixed names, under a BUDGET_SECONDS wall clock. If the budget is
spent under claude-desktop with no scheduled record found, the answer is SCHEDULED
("store scan hit the time budget: fail closed").

KNOWN RESIDUAL (c): a session with unrestricted shell can move/hide its record dir
(e.g. beyond depth 3 or outside the standard roots) or forge store roots; the defense is
the Task 5 mint-guard, widened to refuse shell/file ops referencing claude-code-sessions
from scheduled sessions.

Fails open to UNKNOWN on any read error. Never raises.

ORA_SESSION_STORE_DIRS is a TEST SEAM ONLY (os.pathsep-separated). It must never be set
in settings.json's env block or any scheduled context; test-session-kind.py asserts the
tracked settings.json does not set it.

Stdlib only. ASCII-only. Windows (`python`).
"""
import json
import mmap
import os
import re
import sys
import time

SCHEDULED = "scheduled"
INTERACTIVE = "interactive"
UNKNOWN = "unknown"

ENV_STORE_DIRS = "ORA_SESSION_STORE_DIRS"
ENV_ENTRYPOINT = "CLAUDE_CODE_ENTRYPOINT"
HEADLESS_ENTRYPOINT_PREFIX = "sdk"
DESKTOP_ENTRYPOINT = "claude-desktop"
RECENT_SECONDS = 7 * 86400
MAX_RECORD_BYTES = 4 * 1024 * 1024
MAX_DEPTH = 3
BUDGET_SECONDS = 3.0
_TASK_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,128}$")

_HERE = os.path.dirname(os.path.abspath(__file__))
_SHARED = os.path.join(os.path.dirname(os.path.dirname(_HERE)), "maintenance", "_shared")


class _Budget(object):
    """Wall-clock budget shared by enumeration and the record scan. `hit` latches."""

    def __init__(self, seconds):
        self.deadline = time.time() + seconds
        self.hit = False

    def expired(self):
        if not self.hit and time.time() > self.deadline:
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


def _enum_dirs(base, budget):
    """base plus its sub-directories to depth <= MAX_DEPTH. No glob, no recursion into
    symlinks/junctions, dot-prefixed names included, each realpath visited once, bounded
    by the wall-clock budget."""
    out, seen = [], set()
    queue = [(base, 0)]
    while queue:
        if budget.expired():
            break
        path, depth = queue.pop(0)
        try:
            rp = os.path.normcase(os.path.realpath(path))
        except OSError:
            continue
        if rp in seen or not os.path.isdir(path):
            continue
        seen.add(rp)
        out.append(path)
        if depth >= MAX_DEPTH:
            continue
        try:
            with os.scandir(path) as it:
                for e in it:
                    try:
                        if e.is_dir(follow_symlinks=False) and not _is_link(e.path):
                            queue.append((e.path, depth + 1))
                    except OSError:
                        continue
        except OSError:
            continue
    return out


def _root_record_dirs(budget):
    """Record dirs under the standard Claude roots, independent of scheduled-tasks.json.

    Layout: <root>/claude-code-sessions/<group>/<group>/local_*.json. Bounded scandir
    walk (see _enum_dirs); the root list is store_discovery.store_bases, but
    discover_store() is NOT called (its unbounded recursive glob hangs on a junction
    loop; C4)."""
    bases = []
    try:
        if _SHARED not in sys.path:
            sys.path.insert(0, _SHARED)
        import store_discovery  # noqa: E402
        bases = list(store_discovery.store_bases("claude-code-sessions"))
    except BaseException:
        bases = []
    if not bases:
        appdata = os.environ.get("APPDATA") or os.path.join(
            os.path.expanduser("~"), "AppData", "Roaming")
        bases = [os.path.join(appdata, "Claude", "claude-code-sessions")]
    found = []
    for base in bases:
        try:
            found.extend(_enum_dirs(base, budget))
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
        key = os.path.normcase(os.path.abspath(d))
        if key not in seen:
            seen.add(key)
            uniq.append(d)
    return uniq


def _parse_record(raw):
    """Parsed dict from raw bytes (BOM tolerated), or None."""
    try:
        rec = json.loads(raw.decode("utf-8-sig"))
    except Exception:
        return None
    return rec if isinstance(rec, dict) else None


def _prefilter_needle(session_id):
    """Bytes a file must contain to be worth parsing, or None to parse everything.

    A plain ASCII uuid-like id appears verbatim in the JSON text. If the id has chars
    JSON would escape, no prefilter is applied."""
    try:
        if not all(32 < ord(c) < 127 and c not in ('"', chr(92)) for c in session_id):
            return None
        return session_id.encode("ascii")
    except Exception:
        return None


def _read_record(p, needle=None):
    """Parsed dict for a record file, or None. Tolerates a BOM; size-capped.

    With needle, files whose raw bytes lack it are skipped without a JSON parse.
    Residual: a record that spells its own id with JSON unicode escapes evades the
    prefilter (an unescaped-substring check cannot see it); Desktop sessions still fail
    closed, so this only matters for non-Desktop entrypoints. A backslash-u escape
    fallback is not viable: 726/726 live records contain such escapes in message text."""
    try:
        if os.path.getsize(p) > MAX_RECORD_BYTES:
            return None
        with open(p, "rb") as fh:
            if needle is not None:
                # mmap scan: no 0.5 MB copy per non-matching file (live store ~2x faster).
                try:
                    mm = mmap.mmap(fh.fileno(), 0, access=mmap.ACCESS_READ)
                except (ValueError, OSError):
                    mm = None
                if mm is not None:
                    try:
                        if mm.find(needle) < 0:
                            return None
                    finally:
                        mm.close()
            raw = fh.read()
    except Exception:
        return None
    return _parse_record(raw)


def _record_paths(d):
    """local_*.json regular files directly in d (scandir; links skipped)."""
    out = []
    try:
        with os.scandir(d) as it:
            for e in it:
                try:
                    n = e.name
                    if (n.startswith("local_") and n.endswith(".json")
                            and e.is_file(follow_symlinks=False)):
                        out.append(e.path)
                except OSError:
                    continue
    except OSError:
        pass
    return out


def scan_records(session_id, dirs=None, budget=None):
    """(fresh, stale): records whose cliSessionId == session_id, each newest first.

    fresh = within RECENT_SECONDS; stale = older (kept as evidence only). Stops reading
    once the budget (if any) is spent; budget.hit then latches."""
    if not isinstance(session_id, str) or not session_id:
        return [], []
    dirs = store_dirs(budget) if dirs is None else dirs
    now = time.time()
    needle = _prefilter_needle(session_id)
    fresh, stale = [], []
    for d in dirs:
        if budget is not None and budget.expired():
            break
        for p in _record_paths(d):
            if budget is not None and budget.expired():
                break
            try:
                mtime = os.path.getmtime(p)
            except OSError:
                continue
            rec = _read_record(p, needle)
            if rec is None or rec.get("cliSessionId") != session_id:
                continue
            (fresh if now - mtime <= RECENT_SECONDS else stale).append((mtime, rec))
    fresh.sort(key=lambda t: t[0], reverse=True)
    stale.sort(key=lambda t: t[0], reverse=True)
    return [r for _m, r in fresh], [r for _m, r in stale]


def find_records(session_id, dirs=None):
    """ALL recent records whose cliSessionId == session_id, newest first. [] on none."""
    return scan_records(session_id, dirs)[0]


def store_discoverable(dirs=None):
    """True when at least one store directory exists."""
    try:
        dirs = store_dirs() if dirs is None else dirs
        return any(os.path.isdir(d) for d in dirs)
    except Exception:
        return False


def find_record(session_id, dirs=None):
    """The newest recent record for session_id, or None. Prefer find_records()."""
    recs = find_records(session_id, dirs)
    return recs[0] if recs else None


def classify(session_id, env=None, dirs=None):
    """(kind, task_id, evidence). task_id comes only from a session record.

    Scheduled wins: if ANY record (fresh or stale) for this session carries the
    scheduledTaskId key (any value), the session is SCHEDULED, so a newer forged/duplicate
    record without the key cannot downgrade it. Desktop sessions with no valid in-window
    record fail closed to SCHEDULED (see module docstring).
    """
    env = os.environ if env is None else env
    budget = _Budget(BUDGET_SECONDS)
    try:
        dirs = store_dirs(budget) if dirs is None else dirs
    except Exception:
        dirs = []
    try:
        fresh, stale = scan_records(session_id, dirs, budget)
    except Exception:
        fresh, stale = [], []
    sched = [r for r in fresh + stale if "scheduledTaskId" in r]
    if sched:
        tid = None
        for r in sched:
            v = r.get("scheduledTaskId")
            if isinstance(v, str) and _TASK_ID_RE.match(v):
                tid = v
                break
        return SCHEDULED, tid, "session record carries scheduledTaskId"
    ep = env.get(ENV_ENTRYPOINT) or ""
    ep = ep.lower() if isinstance(ep, str) else ""
    if ep.startswith(HEADLESS_ENTRYPOINT_PREFIX):
        return SCHEDULED, None, "headless entrypoint"
    if ep == DESKTOP_ENTRYPOINT and budget.hit and isinstance(session_id, str) and session_id:
        return SCHEDULED, None, "desktop session, store scan hit the time budget: fail closed"
    if fresh:
        return INTERACTIVE, None, "session record without scheduledTaskId"
    if not isinstance(session_id, str) or not session_id:
        return UNKNOWN, None, "no session_id"
    if ep == DESKTOP_ENTRYPOINT:
        return SCHEDULED, None, "desktop session with no readable record: fail closed"
    return UNKNOWN, None, "no Desktop session record"
