"""Commit-provenance recorder -- PostToolUse hook for Edit|Write|MultiEdit plus
Desktop Commander's write_file/edit_block (both the mcp__Desktop_Commander__ and
mcp__plugin_desktop-commander_desktop-commander__ prefixes).

Records WHAT THIS SESSION EDITED so that commit-provenance-guard.py (PreToolUse,
Bash) can recognise another live session's work and refuse to sweep it into a
commit. Half of a two-part guard; useless alone. Full rationale:
docs/superpowers/specs/2026-07-16-commit-provenance-guard-design.md

Writes one `<absolute, normcase-normalised path>\t<epoch-seconds>` line per
touch to
  hooks/sessions/<session_id>/touched-files.txt

APPEND-ONLY BY DESIGN. It never reads the file back and never rewrites it, so
concurrent sessions cannot race here -- deliberately unlike
fleet-session-hook.py's unlocked load-mutate-replace cycle, which its own
session_liveness.py docstring flags as "a real, accepted, bounded race under
concurrent writers". Duplicate lines are EXPECTED and are deduped-to-latest by
the reader.

SAFETY INVARIANT: this hook has no opinions and no failure mode. It never blocks
anything (PostToolUse cannot), and the whole body is wrapped in try/except -- on
ANY error it exits 0 silently. A bug here degrades the guard to "no information",
which the guard treats as ALLOW.

norm() / sessions_dir() / TOUCHED_BASENAME live in hooks/lib/commit_provenance.py
so this hook and commit-provenance-guard.py cannot drift on the on-disk format.

Stdlib only. ASCII-only. Windows (`python`).
"""

import json
import os
import sys

LIB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib")
sys.path.insert(0, LIB_DIR)
from commit_provenance import sessions_dir, touch_line, TOUCHED_BASENAME  # noqa: E402


def main():
    payload = json.loads(sys.stdin.read())
    if not isinstance(payload, dict):
        return
    tool_input = payload.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        return
    # Desktop Commander's write_file uses "path"; edit_block and native Edit use
    # "file_path" -- same fallback registry-write-guard.py settled on.
    file_path = tool_input.get("file_path") or tool_input.get("path")
    if not isinstance(file_path, str) or not file_path:
        return
    session_id = payload.get("session_id")
    if not isinstance(session_id, str) or not session_id:
        return

    sess_dir = os.path.join(sessions_dir(), session_id)
    os.makedirs(sess_dir, exist_ok=True)
    with open(os.path.join(sess_dir, TOUCHED_BASENAME), "a", encoding="utf-8") as fh:
        fh.write(touch_line(file_path))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass  # fail open: a recorder bug must never affect a tool call
    sys.exit(0)
