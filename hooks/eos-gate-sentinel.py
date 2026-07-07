"""Engineering OS gate sentinel -- PostToolUse hook for Bash.

When a test/gate command runs, drop a `gate-green` marker in the session dir
so the evidence gate knows a gate was exercised this session.

SAFETY INVARIANT: wrapped in try/except. On ANY error, prints nothing and
exits 0. Fail open.

Stdlib only. ASCII-only. Windows (`python`).
"""

import json
import os
import re
import sys

DEFAULT_SESSIONS_DIR = "C:/Users/Owner/.claude/hooks/sessions"

TEST_RE = re.compile(
    r"pytest|vitest|npm test|npm run gate|go test|cargo test|\btest-",
    re.IGNORECASE,
)


def main():
    raw = sys.stdin.read()
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        return

    session_id = payload.get("session_id")
    tool_input = payload.get("tool_input") or {}
    command = tool_input.get("command")
    if not isinstance(session_id, str) or not session_id:
        return
    if not isinstance(command, str) or not command:
        return

    if not TEST_RE.search(command):
        return

    sessions_dir = os.environ.get("EOS_SESSIONS_DIR") or DEFAULT_SESSIONS_DIR
    sess_dir = os.path.join(sessions_dir, session_id)
    os.makedirs(sess_dir, exist_ok=True)
    with open(os.path.join(sess_dir, "gate-green"), "w", encoding="ascii") as fh:
        fh.write("")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
