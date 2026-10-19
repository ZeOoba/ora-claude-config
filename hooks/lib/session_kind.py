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
Callers decide what UNKNOWN means. The delete gate treats it as interactive; the mint
guard does not block it.

Fails open to UNKNOWN on any read error. Never raises.

ORA_SESSION_STORE_DIRS is a TEST SEAM ONLY (os.pathsep-separated). It must never be set
in settings.json's env block or any scheduled context; test-session-kind.py asserts the
tracked settings.json does not set it.

Stdlib only. ASCII-only. Windows (`python`).
"""
import glob
import json
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
RECENT_SECONDS = 7 * 86400
MAX_RECORD_BYTES = 4 * 1024 * 1024
_TASK_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,128}$")

_HERE = os.path.dirname(os.path.abspath(__file__))
_SHARED = os.path.join(os.path.dirname(os.path.dirname(_HERE)), "maintenance", "_shared")


def store_dirs():
    """Directories holding local_*.json records. [] when discovery fails."""
    seam = os.environ.get(ENV_STORE_DIRS)
    if seam is not None:
        return [d for d in seam.split(os.pathsep) if d]
    try:
        if _SHARED not in sys.path:
            sys.path.insert(0, _SHARED)
        import store_discovery  # noqa: E402
        reg = store_discovery.discover_store("claude-code-sessions")
    except BaseException:
        return []
    return [os.path.dirname(reg)] if reg else []


def find_record(session_id, dirs=None):
    """The newest recent record whose cliSessionId == session_id, or None."""
    if not isinstance(session_id, str) or not session_id:
        return None
    dirs = store_dirs() if dirs is None else dirs
    now = time.time()
    for d in dirs:
        try:
            paths = glob.glob(os.path.join(d, "local_*.json"))
        except Exception:
            continue
        stamped = []
        for p in paths:
            try:
                mtime = os.path.getmtime(p)
            except OSError:
                continue
            if now - mtime <= RECENT_SECONDS:
                stamped.append((mtime, p))
        stamped.sort(reverse=True)
        for _mtime, p in stamped:
            try:
                if os.path.getsize(p) > MAX_RECORD_BYTES:
                    continue
                with open(p, "r", encoding="utf-8") as fh:
                    rec = json.load(fh)
            except Exception:
                continue
            if isinstance(rec, dict) and rec.get("cliSessionId") == session_id:
                return rec
    return None


def classify(session_id, env=None, dirs=None):
    """(kind, task_id, evidence). task_id comes only from a session record."""
    env = os.environ if env is None else env
    try:
        rec = find_record(session_id, dirs)
    except Exception:
        rec = None
    if isinstance(rec, dict):
        tid = rec.get("scheduledTaskId")
        if isinstance(tid, str) and tid:
            return (SCHEDULED, tid if _TASK_ID_RE.match(tid) else None,
                    "session record carries scheduledTaskId")
    ep = env.get(ENV_ENTRYPOINT) or ""
    if isinstance(ep, str) and ep.lower().startswith(HEADLESS_ENTRYPOINT_PREFIX):
        return SCHEDULED, None, "headless entrypoint"
    if isinstance(rec, dict):
        return INTERACTIVE, None, "session record without scheduledTaskId"
    if not isinstance(session_id, str) or not session_id:
        return UNKNOWN, None, "no session_id"
    return UNKNOWN, None, "no Desktop session record"
