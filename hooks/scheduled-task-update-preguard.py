"""Scheduled-task update hand-edit warning -- PreToolUse hook for
mcp__scheduled-tasks__update_scheduled_task.

WHY THIS EXISTS (2026-08-13): reference_skill_description_registry_file_desync.md
documents a real failure mode -- a SKILL.md gets edited by hand (Edit/Write, or
Desktop Commander), OUTSIDE update_scheduled_task, and the registry/tool then has
a stale idea of that task's frontmatter. The NEXT update_scheduled_task call
rewrites the frontmatter from its own schema fields (see
lib/scheduled_task_frontmatter.py's module docstring), silently reverting the
hand-edit. This guard is the point-of-call warning for that: it detects, via a
persisted sha ledger, whether SKILL.md changed since the last TOOL-MEDIATED
update for this task id, and -- if so -- warns before the call proceeds that it
may be about to revert an un-synced hand-edit.

Companion half: scheduled-task-update-postguard.py (PostToolUse), which detects
the OTHER incident (OI-109: a dropped custom frontmatter key) and maintains the
same ledger this guard reads.

SAFETY INVARIANT: warn-only. Never denies (no permissionDecision "deny"/"ask"),
and the entire body is wrapped in try/except -- on ANY error it prints nothing
and exits 0 (ALLOW). This is a heuristic (sha-based) signal about a tool whose
correct, intentional use is far more common than the incident it flags, so
blocking on it would cost far more legitimate updates than it would ever save.

Stdlib only. ASCII-only. Windows (`python`).
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"))
from scheduled_task_frontmatter import (  # noqa: E402
    emit, frontmatter_keys, pre_snapshot_path, read_ledger,
    read_text, sha256_of, skill_md_path, write_json_atomic,
)


def _read_stdin_text():
    # Decode raw bytes as UTF-8 ourselves -- never trust sys.stdin's own encoding
    # (confirmed live elsewhere in this hooks/ tree: a harness-spawned process can
    # resolve sys.stdin.encoding to cp1252 instead of UTF-8).
    return sys.stdin.buffer.read().decode("utf-8")


def main():
    payload = json.loads(_read_stdin_text())
    if not isinstance(payload, dict):
        return
    if payload.get("tool_name") != "mcp__scheduled-tasks__update_scheduled_task":
        return  # belt-and-suspenders: correctness should depend on the settings.json
                 # matcher alone, but a future matcher typo should be inert, not noisy
    tool_input = payload.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        return
    task_id = tool_input.get("taskId")
    path = skill_md_path(task_id)
    if path is None:
        return
    session_id = payload.get("session_id")
    if not isinstance(session_id, str) or not session_id:
        session_id = "nosession"

    text = read_text(path)
    if text is None:
        return  # task file unreadable/missing -- nothing to compare, fail open

    sha = sha256_of(text)
    keys = frontmatter_keys(text)

    # Always leave a PRE snapshot for the PostToolUse half to diff against,
    # regardless of whether a hand-edit warning fires below. `keys` is a list
    # (None -> []) since json can't round-trip a set; the postguard treats an
    # empty/absent key list as "cannot trust the diff" and fails open.
    write_json_atomic(pre_snapshot_path(session_id, task_id),
                       {"sha": sha, "keys": sorted(keys) if keys is not None else []})

    ledger = read_ledger()
    entry = ledger.get(task_id)
    if not entry or not isinstance(entry, dict):
        return  # no prior tool-mediated update on record -- nothing to compare
    last_sha = entry.get("sha")
    if not last_sha or last_sha == sha:
        return  # unchanged since the last tool-mediated update -- no desync

    msg = (
        "scheduled-task-update-preguard: `%s/SKILL.md` has changed since the last "
        "update_scheduled_task call for this task -- likely a hand-edit (Edit/Write "
        "outside the tool). This update_scheduled_task call only carries "
        "description/prompt/cronExpression/fireAt/enabled/notifyOnCompletion, so it "
        "will REWRITE the frontmatter from those fields and may silently revert the "
        "hand-edit (any other frontmatter key, e.g. a custom one, is not "
        "reconstructed from what you pass here). If the hand-edit should survive, "
        "fold its intent into this call's `prompt`/`description` first, or reapply "
        "it after the update completes. See "
        "reference_skill_description_registry_file_desync.md." % task_id
    )
    emit(msg, "PreToolUse")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass  # fail open: warn-only must never block a tool call
    sys.exit(0)
