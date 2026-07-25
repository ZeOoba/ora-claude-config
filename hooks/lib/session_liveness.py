"""Session liveness reader for coordination guards.

Reads the fleet-session-hook.py mirror as a fail-open ENRICHMENT signal: a
session's PRESENCE, AND its status != "ended", means it is still open. A clean
SessionEnd no longer deletes the session's file (2026-07-24: it marks
status="ended" and keeps it around so its recent-activity feed contribution
survives a while longer) -- this reader excludes status=="ended" sessions
explicitly so file-presence-alone would otherwise wrongly read as "still
open". Either an ended or a crashed session's file is eventually removed by
the same SESSION_PRUNE_H=6-hour pruning, run as a side effect of
fleet-session-hook.py's own next invocation (render()'s directory scan) --
KNOWN EXCEPTION: a same-session straggler write landing AFTER SessionEnd's
(the module's documented accepted same-session race) can flip status back
away from "ended", making that already-finished session look open again
until the next prune sweep; see fleet-session-hook.py's own module docstring
for why this is accepted rather than fixed with a lock.

ENRICHMENT ONLY, never a hard gate: fleet-session-hook.py is itself
fail-open/best-effort (it may silently not run). A caller MUST treat a read
failure, or a stale/empty result, the same as "no information" -- never as
"definitely no other session" or "definitely another session" -- and degrade
to whatever git-status-only behavior existed before consuming this module.

STORAGE FORMAT (2026-07-24): fleet-session-hook.py migrated from one shared
session-state.json (load-mutate-replace, an unlocked race under concurrent
writers -- exactly the two-sessions-open scenario this module exists to
detect, ironically) to one file PER session under a sessions-state
directory, eliminating that race entirely (each session only ever touches
its own file). This reader now PREFERS that new per-session-file format
when the directory exists, and falls back to the old single-file format
otherwise -- so a machine that has not yet run the new fleet-session-hook.py
even once (or a test fixture still constructing the old shape) keeps
working unchanged. other_active_sessions()'s signature and return shape are
UNCHANGED by this migration; commit-provenance-guard.py and
shared-checkout-guard.py (the only two callers) needed zero changes.

Stdlib only. ASCII-only. Windows (`python`).
"""
import json
import os

DEFAULT_SESSIONS_DIR = "C:/Users/Owner/.claude/obsidian-fleet-mirror/session-state.d"
DEFAULT_STATE = "C:/Users/Owner/.claude/obsidian-fleet-mirror/session-state.json"


def _read_new_format(sessions_dir, own_sid):
    """Sessions present as their own file under `sessions_dir`, other than
    own_sid. Each session's file is written via atomic rename (temp file +
    os.replace) by fleet-session-hook.py, so a concurrent write is never
    visible here as a torn/partial read -- either the old or new full
    content, never a mix. Fail-open: any per-file read/parse error is
    skipped, not raised.

    A status="ended" session's file DELIBERATELY persists for a while after
    a clean SessionEnd (fleet-session-hook.py 2026-07-24: so its
    recent-activity feed contribution survives instead of vanishing
    instantly, cleaned up later by the same idle-timeout pruning every
    other session gets) -- it is explicitly excluded here so file-presence
    keeps meaning "still open", matching this module's documented
    contract, regardless of how much longer the file itself sticks around."""
    out = []
    try:
        names = os.listdir(sessions_dir)
    except Exception:
        return []
    for name in names:
        if not name.endswith(".json"):
            continue
        try:
            with open(os.path.join(sessions_dir, name), "r", encoding="utf-8") as fh:
                s = json.load(fh)
        except Exception:
            continue
        if not isinstance(s, dict):
            continue
        if s.get("status") == "ended":
            continue
        sid = s.get("_sid") or name[:-5]
        if sid == own_sid:
            continue
        out.append({
            "sid": sid,
            "status": s.get("status", "?"),
            "cwd": s.get("cwd", ""),
            "lastAt": s.get("lastAt", ""),
        })
    return out


def _read_old_format(path, own_sid):
    """Sessions present in a single legacy session-state.json, other than
    own_sid. Kept for backward compatibility with any caller/test still
    pointed at the pre-2026-07-24 shared-file format -- fleet-session-hook.py
    itself no longer writes this shape, but nothing else has to change in
    lockstep as long as this reader still understands it."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception:
        return []
    sessions = data.get("sessions") if isinstance(data, dict) else None
    if not isinstance(sessions, dict):
        return []
    out = []
    for sid, s in sessions.items():
        if sid == own_sid or not isinstance(s, dict):
            continue
        out.append({
            "sid": sid,
            "status": s.get("status", "?"),
            "cwd": s.get("cwd", ""),
            "lastAt": s.get("lastAt", ""),
        })
    return out


def other_active_sessions(own_sid, state_path=None, sessions_dir=None):
    """Sessions other than own_sid currently reported live by
    fleet-session-hook.py's mirror.

    An EXPLICIT `sessions_dir=` or `state_path=` argument is unambiguous and is
    honored directly, with no fallback and no dependence on ambient machine state --
    this is what makes both this function's own tests, and the two guards' existing
    tests that construct a legacy fixture via `state_path=`, fully deterministic
    regardless of what does or doesn't exist on the real filesystem. Only when
    NEITHER override is given (real production usage) does resolution fall back to
    environment variables and disk state: ORA_FLEET_SESSIONS_DIR (same variable
    fleet-session-hook.py itself reads) if that directory exists, else ORA_FLEET_STATE
    for the legacy single-file format -- so a non-default configuration can't silently
    desync writer and reader on either format.

    Fail-open: any read/parse error (missing file/dir, malformed JSON, wrong shape)
    returns [] -- never raises.

    Each item: {"sid": str, "status": str, "cwd": str, "lastAt": str}.
    """
    if sessions_dir is not None:
        return _read_new_format(sessions_dir, own_sid)
    if state_path is not None:
        return _read_old_format(state_path, own_sid)

    sdir = os.environ.get("ORA_FLEET_SESSIONS_DIR") or DEFAULT_SESSIONS_DIR
    try:
        is_dir = os.path.isdir(sdir)
    except Exception:
        is_dir = False
    if is_dir:
        return _read_new_format(sdir, own_sid)
    path = os.environ.get("ORA_FLEET_STATE") or DEFAULT_STATE
    return _read_old_format(path, own_sid)
