"""Engineering OS plan marker -- PostToolUse hook for Write|Edit.

When a plan file under docs/superpowers/plans/ (the superpowers convention) OR
~/.claude/plans/ (native Claude Code plan-mode's own output path) is written,
drop a `plan-approved` marker in the session dir so the plan gate stops
counting.

SAFETY INVARIANT: wrapped in try/except. On ANY error, prints nothing and
exits 0. Fail open.

Stdlib only. ASCII-only. Windows (`python`).
"""

import json
import os
import sys

DEFAULT_SESSIONS_DIR = "C:/Users/Owner/.claude/hooks/sessions"

PLAN_SUBSTR = (
    "docs/superpowers/plans/", "docs\\superpowers\\plans\\",
    ".claude/plans/", ".claude\\plans\\",
)


def main():
    raw = sys.stdin.read()
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        return

    session_id = payload.get("session_id")
    tool_input = payload.get("tool_input") or {}
    file_path = tool_input.get("file_path")
    if not isinstance(session_id, str) or not session_id:
        return
    if not isinstance(file_path, str) or not file_path:
        return

    if not any(sub in file_path for sub in PLAN_SUBSTR):
        return

    sessions_dir = os.environ.get("EOS_SESSIONS_DIR") or DEFAULT_SESSIONS_DIR
    sess_dir = os.path.join(sessions_dir, session_id)
    os.makedirs(sess_dir, exist_ok=True)
    with open(os.path.join(sess_dir, "plan-approved"), "w", encoding="ascii") as fh:
        fh.write("")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
