"""Engineering OS plan gate -- PreToolUse hook for Edit|Write|MultiEdit.

Discourages editing many code files in a session with no plan. After 3 code
edits with no plan-approved/override marker, the 4th+ code edit is DENIED with
guidance to run /plan or /build (or touch an override marker).

SAFETY INVARIANT: the entire body is wrapped in try/except. On ANY error --
bad stdin, missing field, unreadable file -- it prints nothing and exits 0
(ALLOW). A bug must NEVER block a tool call.

Stdlib only. ASCII-only. Windows (`python`).
"""

import json
import os
import sys

DEFAULT_SESSIONS_DIR = os.path.expanduser("~/.claude/hooks/sessions")

CODE_EXTS = {
    ".py", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".go", ".rs",
    ".java", ".rb", ".php", ".c", ".cpp", ".h", ".hpp", ".css", ".scss",
    ".vue", ".svelte",
}

EXCLUDE_SUBSTR = (
    "/docs/", "\\docs\\", "/memory/", "\\memory\\",
    "/.superpowers/", "node_modules", "_smoke",
)

LIMIT = 3


def is_code_path(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    if ext not in CODE_EXTS:
        return False
    for sub in EXCLUDE_SUBSTR:
        if sub in file_path:
            return False
    return True


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

    if not is_code_path(file_path):
        return  # not a code path -> allow silently

    sessions_dir = os.environ.get("EOS_SESSIONS_DIR") or DEFAULT_SESSIONS_DIR
    sess_dir = os.path.join(sessions_dir, session_id)

    # Existing markers -> allow.
    if os.path.exists(os.path.join(sess_dir, "plan-approved")):
        return
    if os.path.exists(os.path.join(sess_dir, "override")):
        return

    os.makedirs(sess_dir, exist_ok=True)
    count_file = os.path.join(sess_dir, "code-edits.count")

    count = 0
    if os.path.isfile(count_file):
        try:
            with open(count_file, "r", encoding="ascii") as fh:
                count = int(fh.read().strip() or "0")
        except Exception:
            count = 0

    count += 1
    with open(count_file, "w", encoding="ascii") as fh:
        fh.write(str(count))

    if count > LIMIT:
        override_path = os.path.join(sess_dir, "override")
        reason = (
            "Engineering OS: 4+ code files edited with no plan this session. "
            "Run /plan or /build first, or `touch " + override_path +
            "` to proceed."
        )
        out = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }
        }
        sys.stdout.write(json.dumps(out))
    # count <= LIMIT -> allow silently.


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # Fail open: a bug must never block a tool call.
        pass
    sys.exit(0)
