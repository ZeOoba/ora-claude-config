"""ORA Claude Code reliability telemetry -- SessionEnd hook.

Reads the SessionEnd hook JSON from stdin, parses the session transcript,
and (only for coding sessions) appends one telemetry record to
lane-telemetry.jsonl. Used to measure how often coding sessions declare a
lane, run a test, dispatch a subagent, show verification evidence, and
whether the session bypassed eos-plan-gate.py's plan requirement via an
override marker (and, if so, the reason recorded in that marker).

SAFETY INVARIANT: this hook FAILS OPEN. The entire body is wrapped in a
broad try/except. On ANY error -- bad stdin, missing field, unreadable file,
unexpected shape -- it prints nothing and exits 0. Telemetry must never
affect, slow, or block a session.

Stdlib only. ASCII-only.
"""

import json
import os
import re
import sys
from datetime import datetime, timezone

DEFAULT_DIR = "C:/Users/Owner/.claude/telemetry"
OUT_NAME = "lane-telemetry.jsonl"
DEFAULT_SESSIONS_DIR = "C:/Users/Owner/.claude/hooks/sessions"

EDIT_TOOLS = ("Edit", "Write", "MultiEdit")
# Subagent-dispatch tools. EXACT match only -- never a prefix/substring test:
# TaskCreate / TaskUpdate / TaskList / TaskGet / TaskOutput / TaskStop are
# todo-management tools and must not be counted as dispatch. "Task" is kept
# only as forward/backward insurance against a rename; it has never appeared
# in a real transcript, which is why this signal read 0% until 2026-07-24.
DISPATCH_TOOLS = frozenset(("Agent", "Task"))
BASH_TEST_RE = re.compile(
    r"pytest|vitest|npm test|npm run gate|go test|cargo test| test-",
    re.IGNORECASE,
)
LANE_TOKENS = ("Dispatch:", "lane L", "/build", "/debug", "/refactor",
               "/research", "/ship")
VERIFY_TOKENS = ("PASS", "exit=0", "tests pass", "verified")


def iter_tool_uses(obj):
    """Yield (tool_name, tool_input_dict) for any tool-use shapes in a parsed
    transcript object. Defensive across common Claude transcript shapes."""
    if not isinstance(obj, dict):
        return

    # Shape A: flat tool_name key.
    name = obj.get("tool_name")
    if isinstance(name, str) and name:
        inp = obj.get("tool_input") or obj.get("input") or {}
        yield name, inp if isinstance(inp, dict) else {}

    # Shape B/C: nested message.content[] blocks.
    msg = obj.get("message")
    content = None
    if isinstance(msg, dict):
        content = msg.get("content")
    if content is None:
        content = obj.get("content")
    if isinstance(content, list):
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_use" or block.get("name"):
                bname = block.get("name")
                if isinstance(bname, str) and bname:
                    binp = block.get("input") or {}
                    yield bname, binp if isinstance(binp, dict) else {}


def iter_text(obj):
    """Yield assistant text strings from a parsed transcript object."""
    if not isinstance(obj, dict):
        return
    msg = obj.get("message")
    content = None
    if isinstance(msg, dict):
        content = msg.get("content")
    if content is None:
        content = obj.get("content")
    if isinstance(content, str):
        yield content
    elif isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                txt = block.get("text")
                if isinstance(txt, str):
                    yield txt


def main():
    raw = sys.stdin.read()
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        return

    transcript_path = payload.get("transcript_path")
    session_id = payload.get("session_id")
    if not transcript_path or not os.path.isfile(transcript_path):
        return

    edits = 0
    files = set()
    bash_test_ran = False
    task_dispatched = False
    lane_declared = False
    verification_seen = False

    with open(transcript_path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue  # skip malformed lines

            for tname, tinput in iter_tool_uses(obj):
                if tname in EDIT_TOOLS:
                    edits += 1
                    fp = tinput.get("file_path")
                    if isinstance(fp, str) and fp:
                        files.add(fp)
                elif tname == "Bash":
                    cmd = tinput.get("command")
                    if isinstance(cmd, str) and BASH_TEST_RE.search(cmd):
                        bash_test_ran = True
                elif tname in DISPATCH_TOOLS:
                    task_dispatched = True

            for txt in iter_text(obj):
                if not lane_declared and any(tok in txt for tok in LANE_TOKENS):
                    lane_declared = True
                if not verification_seen and any(
                    tok in txt for tok in VERIFY_TOKENS
                ):
                    verification_seen = True

    # Not a coding session -> write nothing.
    if edits == 0 and not bash_test_ran and not task_dispatched:
        return

    out_dir = os.environ.get("EOS_TELEMETRY_DIR") or DEFAULT_DIR
    try:
        os.makedirs(out_dir, exist_ok=True)
    except Exception:
        return
    out_file = os.path.join(out_dir, OUT_NAME)

    override_used = False
    override_reason = None
    override_at = None
    try:
        sessions_dir = os.environ.get("EOS_SESSIONS_DIR") or DEFAULT_SESSIONS_DIR
        override_path = os.path.join(sessions_dir, session_id, "override")
        if os.path.isfile(override_path):
            override_used = True
            override_at = datetime.fromtimestamp(
                os.stat(override_path).st_mtime, tz=timezone.utc
            ).isoformat()
            with open(override_path, "r", encoding="utf-8", errors="replace") as fh:
                text = fh.read().strip()
            override_reason = text if text else None
    except Exception:
        pass  # a corrupt override file must not drop the rest of the record

    record = {
        # Emission timestamp. Required to segment records written after the
        # 2026-07-24 dispatch-detection fix from the blind-era backlog, which
        # is uniformly task_dispatched=false and would otherwise depress the
        # blended rate indefinitely. Specified in the EOS reliability-hardening
        # design but never implemented.
        "ts": datetime.now(timezone.utc).isoformat(),
        "session_id": session_id,
        "edits": edits,
        "files": sorted(files),
        "bash_test_ran": bash_test_ran,
        "task_dispatched": task_dispatched,
        "lane_declared": lane_declared,
        "verification_seen": verification_seen,
        "override_used": override_used,
        "override_reason": override_reason,
        "override_at": override_at,
    }
    with open(out_file, "a", encoding="ascii") as fh:
        fh.write(json.dumps(record) + "\n")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # Fail open: telemetry must never block a session.
        pass
    sys.exit(0)
