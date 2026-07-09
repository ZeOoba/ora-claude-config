"""Session liveness reader for coordination guards.

Reads the fleet-session-hook.py mirror (obsidian-fleet-mirror/session-state.json)
as a fail-open ENRICHMENT signal: a session's PRESENCE in the dict means it is
still open (fleet-session-hook.py pops a session immediately on a clean
SessionEnd; a crashed session without SessionEnd is pruned after
SESSION_PRUNE_H=6 hours by fleet-session-hook.py's own next invocation).

ENRICHMENT ONLY, never a hard gate: fleet-session-hook.py is itself
fail-open/best-effort (it may silently not run, and its save_state()
load-mutate-replace cycle is unlocked -- a real, accepted, bounded race under
concurrent writers, which is exactly the two-sessions-open scenario this
module exists to detect). A caller MUST treat a read failure, or a stale/
empty result, the same as "no information" -- never as "definitely no other
session" or "definitely another session" -- and degrade to whatever
git-status-only behavior existed before consuming this module.

Stdlib only. ASCII-only. Windows (`python`).
"""
import json
import os

DEFAULT_STATE = "C:/Users/Owner/.claude/obsidian-fleet-mirror/session-state.json"


def other_active_sessions(own_sid, state_path=None):
    """Sessions present in session-state.json other than own_sid.

    Honors the ORA_FLEET_STATE env var override (same variable
    fleet-session-hook.py itself reads) when state_path is not given
    explicitly, so a non-default configuration can't silently desync
    writer and reader.

    Fail-open: any read/parse error (missing file, malformed JSON, wrong
    shape) returns [] -- never raises.

    Each item: {"sid": str, "status": str, "cwd": str, "lastAt": str}.
    """
    path = state_path or os.environ.get("ORA_FLEET_STATE") or DEFAULT_STATE
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
