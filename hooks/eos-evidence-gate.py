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

DEFAULT_SESSIONS_DIR = "C:/Users/Owner/.claude/hooks/sessions"

REMINDER = (
    "[Engineering OS] No test/gate recorded this session - "
    "run the repo gate before committing code."
)


# SHELL-TOOL SCOPE (cross-repo audit 2026-11-23, HIGH): PowerShell, Desktop Commander
# start_process / interact_with_process, the terminal panel's run_in_terminal and Windows-MCP
# PowerShell run git just
# like Bash, so this guard judges all of them (dispatcher chain "shell"). The command line is
# read through tool_call_paths.shell_text (interact_with_process carries it in `input`). If that
# lib cannot load, the scope degrades to the previous Bash-only behaviour, never wider.
try:
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"))
    from tool_call_paths import is_git_shell_tool as _is_shell_tool, shell_text as _shell_text  # noqa: E402
except Exception:  # noqa: BLE001
    sys.stderr.write("WARNING (%s, DEGRADED): tool_call_paths did not load -- this guard is "
                     "judging Bash ONLY; PowerShell / Desktop Commander / terminal git is "
                     "UNGUARDED until the lib is fixed.\n" % os.path.basename(__file__))
    def _is_shell_tool(tool_name):
        return tool_name == "Bash"

    def _shell_text(tool_name, tool_input):
        return tool_input.get("command") if isinstance(tool_input, dict) else None


def main():
    raw = sys.stdin.read()
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        return

    session_id = payload.get("session_id")
    tool_input = payload.get("tool_input") or {}
    command = _shell_text(payload.get("tool_name"), tool_input)
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
