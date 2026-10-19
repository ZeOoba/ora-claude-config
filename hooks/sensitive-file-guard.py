#!/usr/bin/env python3
r"""Sensitive-file write blocker -- PreToolUse; Python port of the inline settings.json
blocker (audit M65, shipped with R-06).

The inline bash blocker (settings.json PreToolUse matcher "Edit|Write") reads only
tool_input.file_path, so MultiEdit, NotebookEdit and Desktop Commander writes (which put
the target in "path") reach .env and credentials files ungated. This guard applies the
SAME pattern, (credentials|\.env|password) case-insensitive anywhere in the path, to
every target lib/tool_call_paths.write_targets() returns (all candidate path fields, so a
decoy field cannot steer it), and prints the SAME message. The inline blocker stays wired
through a 14-day soak and is removed by a separate PR.

WIRING: live coverage today is Edit/Write/MultiEdit only, through pretooluse-dispatcher.py
GUARD_CHAIN. NotebookEdit and Desktop Commander write_file/edit_block/move_file/write_pdf
coverage requires the deferred Task 7 settings.json entry (R-06); audit finding M65 stays
OPEN until that entry lands. Shell tools are out of scope; the inline blocker never
covered them.

FAILS OPEN on internal error and on unparseable input, exactly like the inline blocker
(its python one-liner prints "" on failure and the grep then passes).

Stdlib only. ASCII-only. Windows (`python`).
"""
import json
import os
import re
import sys

HOOKS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HOOKS_DIR, "lib"))

SENSITIVE_RE = re.compile(r"(credentials|\.env|password)", re.IGNORECASE)


def _main():
    try:
        payload = json.loads(sys.stdin.buffer.read().decode("utf-8"))
    except Exception:
        sys.exit(0)
    if not isinstance(payload, dict):
        sys.exit(0)
    import tool_call_paths as tcp  # noqa: E402
    for target in tcp.write_targets(payload.get("tool_name"), payload.get("tool_input")):
        raw = target.raw_path or ""
        if SENSITIVE_RE.search(raw):
            sys.stderr.write("BLOCKED: Cannot edit sensitive file: %s\n" % raw)
            sys.exit(2)
    sys.exit(0)


def main():
    try:
        _main()
    except SystemExit:
        raise
    except BaseException:  # noqa: BLE001 -- parity with the inline blocker: fail open
        sys.exit(0)


if __name__ == "__main__":
    main()
