"""Scheduled-task update dropped-frontmatter-key warning -- PostToolUse hook for
mcp__scheduled-tasks__update_scheduled_task.

WHY THIS EXISTS (2026-08-13): reference_update_scheduled_task_drops_frontmatter_keys.md
documents OI-109 -- a `description`-only update_scheduled_task call silently
deleted the `output_contract` frontmatter block. The tool only knows its own
schema fields (name/description/cronExpression/fireAt/enabled/
notifyOnCompletion/prompt); anything else in frontmatter (output_contract,
custom tags, etc.) does not survive a round-trip through it. The standing
discipline is "diff vs HEAD after every call" -- done by hand. This hook
automates the diff at the point of call: it compares the top-level frontmatter
KEY SET before vs. after this specific update_scheduled_task call (using the
snapshot the companion PreToolUse guard, scheduled-task-update-preguard.py,
leaves behind) and warns immediately if any key present before is now missing.

It also MAINTAINS the sha ledger the PreToolUse half reads to detect hand-edit
desync -- recording this call's result as the new "last tool-mediated state"
regardless of whether a key was dropped, so the next hand-edit (if any) is
measured from here.

SAFETY INVARIANT: warn-only, and the tool call has already completed by the
time PostToolUse fires -- there is nothing left to block. Entire body wrapped
in try/except -- on ANY error it prints nothing and exits 0.

Stdlib only. ASCII-only. Windows (`python`).
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"))
from scheduled_task_frontmatter import (  # noqa: E402
    emit, frontmatter_keys, pre_snapshot_path, read_text, remove_file,
    sha256_of, skill_md_path, update_ledger,
)


def _read_stdin_text():
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

    after_text = read_text(path)
    if after_text is None:
        return  # task file unreadable post-call -- fail open, nothing to compare

    after_sha = sha256_of(after_text)
    # Ledger is updated UNLESS the tool call itself reported failure (adversarial
    # review finding N2, 2026-08-13): if update_scheduled_task errored, SKILL.md on
    # disk may still reflect a pre-call hand-edit rather than a real tool-mediated
    # write, and recording it as "last known tool-mediated state" would suppress the
    # preguard's hand-edit warning on the RETRY -- a one-shot false negative right
    # when the signal matters most. Shape is defensive (tool_response's exact schema
    # for MCP failures isn't pinned here): only a clear positive error signal skips
    # the update; anything ambiguous or absent falls through to the prior behavior
    # (always update), which is no worse than before this fix.
    tool_response = payload.get("tool_response")
    call_failed = False
    if isinstance(tool_response, dict):
        call_failed = bool(tool_response.get("is_error") or tool_response.get("isError")
                            or tool_response.get("error"))
    if not call_failed:
        # This call is now the newest known tool-mediated state, and the preguard's
        # hand-edit check on the NEXT call must be measured from here, not from
        # before this call ran.
        update_ledger(task_id, after_sha)

    snap_path = pre_snapshot_path(session_id, task_id)
    pre = None
    try:
        with open(snap_path, "r", encoding="utf-8") as fh:
            pre = json.load(fh)
    except Exception:
        pre = None
    remove_file(snap_path)  # one-shot: consumed whether or not it was readable

    if not isinstance(pre, dict):
        return  # no PRE snapshot (preguard didn't run, or already consumed) -- fail open

    pre_keys = pre.get("keys")
    if not isinstance(pre_keys, list) or not pre_keys:
        return  # preguard couldn't read a trustworthy key set either -- nothing to diff
    pre_keys = set(pre_keys)

    after_keys = frontmatter_keys(after_text)
    if after_keys is None:
        return  # malformed/no closing fence post-call -- cannot trust the diff

    dropped = sorted(pre_keys - after_keys)
    if not dropped:
        return

    msg = (
        "scheduled-task-update-postguard: update_scheduled_task just DROPPED "
        "frontmatter key(s) %s from `%s/SKILL.md`. update_scheduled_task only "
        "preserves its own schema fields (description/prompt/cronExpression/"
        "fireAt/enabled/notifyOnCompletion) -- any other top-level key is wiped "
        "on a round-trip, not merged. This is the OI-109 failure mode. Re-add "
        "the dropped key(s) by hand now. See "
        "reference_update_scheduled_task_drops_frontmatter_keys.md." % (
            ", ".join(dropped), task_id)
    )
    emit(msg, "PostToolUse")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass  # fail open: warn-only must never block, and the call already ran
    sys.exit(0)
