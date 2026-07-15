"""Scheduled-task registry write-guard -- PreToolUse hook for Edit|Write|MultiEdit plus
Desktop Commander's write_file/edit_block (both the mcp__Desktop_Commander__ and
mcp__plugin_desktop-commander_desktop-commander__ tool-name prefixes). This guard is
purely path-based (blocks ANY write to the registry file regardless of content), so
unlike memory-index-guard.py it needs no edit-simulation logic -- just the file_path
fallback below. edit_block already shares Edit's "file_path" field name and worked
before this change; write_file's "path" field did not. Extended 2026-07-14, same day
as memory-index-guard.py's identical gap, proactively rather than after an incident --
see hooks/tests/test-registry-write-guard.py cases for the Desktop Commander coverage.

BLOCKS a direct Edit/Write/MultiEdit to either fleet's scheduled-task REGISTRY
backing file. The two registries are the ONLY source of truth for what is
scheduled, and they must be mutated ONLY through the supervised MCP tools
(mcp__scheduled-tasks__create_scheduled_task / update_scheduled_task) via the
register-scheduled-task skill. A direct JSON splice is how the documented
2026-06-09 "registered-but-unscheduled" incident happened -- a task landed in
the registry file but the scheduler never picked it up. This guard is that
incident's automated backstop.

Backing paths (GUIDs are per-app-session -> matched GUID-AGNOSTICALLY):
  CC/MCP    : ...\\Claude\\claude-code-sessions\\<guid>\\<guid>\\scheduled-tasks.json
  LAMS/Cowork: ...\\Claude\\local-agent-mode-sessions\\<guid>\\<guid>\\scheduled-tasks.json

What is NOT blocked (deliberately narrow -- precision over recall):
  * A task's SKILL.md under ~/.claude/scheduled-tasks/<id>/ -- editing a spec
    file is the SANCTIONED authoring path (the registry stores only filePath).
  * Any other scheduled-tasks.json NOT under a session-registry directory.
  * Every ordinary file.

SAFETY INVARIANT: this guard BLOCKS on a POSITIVE registry-path match (exit 2 +
stderr reason, the codebase's PreToolUse deny convention -- see
confidentiality-guard.py). On ANY internal error it FAILS OPEN (exit 0, ALLOW):
the whole body is wrapped in try/except so a bug here can never block a
legitimate edit. This mirrors shared-checkout-guard.py's fail-open posture, but
this hook denies on a confirmed hit rather than merely warning.

Stdlib only. ASCII-only. Windows (`python`).
"""

import json
import sys

REGISTRY_BASENAME = "scheduled-tasks.json"
# Path SEGMENTS (not substrings) that identify a session-registry directory. Segment
# membership avoids a false hit on a sibling dir like "claude-code-sessions-notes".
CC_SEGMENT = "claude-code-sessions"
LAMS_SEGMENT = "local-agent-mode-sessions"


def registry_fleet(file_path):
    """Return 'CC/MCP' or 'LAMS/Cowork' if `file_path` is a fleet registry backing
    file, else None. Pure string match: the target need not exist on disk, and the
    per-session GUID directories are matched structurally (any GUID)."""
    if not isinstance(file_path, str) or not file_path:
        return None
    parts = file_path.replace("\\", "/").lower().split("/")
    if not parts or parts[-1] != REGISTRY_BASENAME:
        return None
    if CC_SEGMENT in parts:
        return "CC/MCP"
    if LAMS_SEGMENT in parts:
        return "LAMS/Cowork"
    return None


def main():
    payload = json.loads(sys.stdin.read())
    if not isinstance(payload, dict):
        return
    tool_input = payload.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        return
    # Desktop Commander's write_file uses "path", not "file_path" -- edit_block
    # already matches native Edit's "file_path", so this fallback only changes
    # write_file's case.
    file_path = tool_input.get("file_path") or tool_input.get("path")
    fleet = registry_fleet(file_path)
    if fleet is None:
        return  # not a registry backing file -> allow

    reason = (
        "Direct write to the %s scheduled-task REGISTRY (scheduled-tasks.json) is "
        "blocked. The registry must be mutated ONLY via "
        "mcp__scheduled-tasks__create_scheduled_task / update_scheduled_task "
        "(use the register-scheduled-task skill). A hand-spliced registry entry "
        "is the documented 2026-06-09 'registered-but-unscheduled' failure: the "
        "task lands in the file but the scheduler never picks it up. To change a "
        "task's spec, edit its SKILL.md instead (the registry stores only its "
        "filePath)." % fleet
    )
    sys.stderr.write("BLOCKED (registry-write-guard): " + reason + "\n")
    sys.exit(2)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise  # a real block (exit 2) must propagate
    except Exception:
        pass  # fail open: any internal error must never block a tool call
    sys.exit(0)
