"""Engineering OS evidence gate -- PreToolUse hook for Bash. NON-BLOCKING.

Before a `git commit`, if no test/gate has been recorded this session
(no `gate-green` marker), print a plain-text reminder. This hook NEVER
denies or blocks -- it only ever reminds.

SAFETY INVARIANT: wrapped in try/except. On ANY error, prints nothing and
exits 0. Fail open.

Stdlib only. ASCII-only. Windows (`python`).
"""

import json
import os
import sys

DEFAULT_SESSIONS_DIR = os.path.expanduser("~/.claude/hooks/sessions")

REMINDER = (
    "[Engineering OS] No test/gate recorded this session - "
    "run the repo gate before committing code."
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

    if "git commit" not in command:
        return

    sessions_dir = os.environ.get("EOS_SESSIONS_DIR") or DEFAULT_SESSIONS_DIR
    marker = os.path.join(sessions_dir, session_id, "gate-green")
    if os.path.exists(marker):
        return  # gate recorded -> silent

    sys.stdout.write(REMINDER)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
