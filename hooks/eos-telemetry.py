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

# Record schema version. Bump ONLY when the record shape or a detector's
# meaning changes in a way the rollup must segment on.
#   1 (implicit, no field) -- blind era. Records predate `ts`; the dispatch
#     detector could not see the real `Agent` tool name, so task_dispatched
#     is uniformly false and MEANINGLESS. ~766 such records exist on disk.
#   2 -- dispatch detection fixed (2026-07-24) and capability self-declared.
SCHEMA_VERSION = 2

# Fields excluded when deciding whether a re-emission carries new information.
# `ts` is the emission clock and differs on every fire by construction, so
# comparing it would make every record "changed" and defeat the check.
VOLATILE_FIELDS = ("ts",)

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


def payload(record):
    """The part of a record that represents an OBSERVATION, ignoring when it
    was written. Two records with equal payloads say the same thing."""
    return {k: v for k, v in record.items() if k not in VOLATILE_FIELDS}


MAX_BYTES = 8 * 1024 * 1024  # 8MB -- see rotate_if_large()


def rotate_if_large(out_file, max_bytes=MAX_BYTES):
    """Archive the telemetry file once it crosses `max_bytes`, so neither disk
    nor the dedupe scan grows without bound.

    Why this is safe despite is_duplicate_of_last() scanning the WHOLE file:
    rotation's only side effect is that a session whose previous record landed
    before the rotation boundary will not find it, and will append one duplicate
    record. That is exactly the outcome the dedupe docstring already declares
    harmless -- "a duplicate is harmless (the rollup merges by session_id)" --
    while the outcome it calls unacceptable, a silently dropped record, cannot
    arise here. Rotation therefore trades an occasional harmless duplicate for a
    bounded O(filesize) scan.

    ARCHIVES, never deletes (standing invariant 6). Fails open in every branch:
    telemetry must never block a session, so any error leaves the file untouched
    and the caller proceeds exactly as before.

    Added 2026-09-06 (Automation Audit R22-5): the file had reached 2,164,334B
    with no rotation logic anywhere in this hook, and is read end-to-end on
    every SessionEnd.
    """
    try:
        if not os.path.isfile(out_file):
            return
        if os.path.getsize(out_file) < max_bytes:
            return
        arch_dir = os.path.join(os.path.dirname(out_file), "_archive")
        os.makedirs(arch_dir, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        dest = os.path.join(arch_dir, "%s-%s" % (stamp, os.path.basename(out_file)))
        os.replace(out_file, dest)
    except Exception:
        return


def is_duplicate_of_last(out_file, session_id, record):
    """True when `record` repeats this session's most recent record verbatim.

    SessionEnd fires on every resume/clear/compaction and each fire re-parses
    the ENTIRE transcript, so an unchanged session emits the same observation
    again and again -- 67% of the 569 duplicate records on the live file were
    byte-identical payloads carrying zero new information.

    Scans the WHOLE file rather than the tail: 7+ sessions interleave here, so
    this session's previous record is routinely many lines back. Comparing
    against the file's last line would miss it and duplicate anyway.

    FAILS TOWARD WRITING. Any error -- unreadable file, corrupt JSON, odd
    shape -- returns False so the record is still appended. A duplicate is
    harmless (the rollup merges by session_id); a silently dropped record is
    lost telemetry, which is the failure this hook exists to prevent.
    """
    if not session_id or not os.path.isfile(out_file):
        return False
    try:
        latest = None
        with open(out_file, "r", encoding="utf-8", errors="surrogateescape") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    prev = json.loads(line)
                except Exception:
                    continue  # a corrupt neighbour must not abort the scan
                if isinstance(prev, dict) and prev.get("session_id") == session_id:
                    latest = prev
        if latest is None:
            return False
        return payload(latest) == payload(record)
    except Exception:
        return False


def main():
    raw = sys.stdin.read()
    # NOT named `payload` -- that is a module-level function here, and
    # shadowing it would make any future payload(...) call inside main()
    # raise TypeError, which the fail-open wrapper would swallow, silently
    # killing telemetry emission.
    hook_input = json.loads(raw)
    if not isinstance(hook_input, dict):
        return

    transcript_path = hook_input.get("transcript_path")
    session_id = hook_input.get("session_id")
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
        # Explicit capability declaration. `ts` presence was only ever a PROXY
        # for "this emitter could detect subagent dispatch" -- a future change
        # that regressed a detector while still stamping `ts` would be silently
        # trusted by the rollup, reproducing the wrongly-low rate this whole
        # mechanism exists to prevent. The schema version is the direct signal.
        "schema": SCHEMA_VERSION,
        # DERIVED from the live constant, never a hand-maintained literal: a
        # literal would keep advertising "Agent" after DISPATCH_TOOLS lost it.
        # Sorted for stable, diffable output.
        "detectors": {"dispatch": sorted(DISPATCH_TOOLS)},
        # Emission timestamp. Retained as the backward-compatible cohort key
        # for the ~766 records written before `schema` existed.
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
    # Bound the file BEFORE the end-to-end dedupe scan below (R22-5). This is
    # the one and only place this module moves an existing file, and it is
    # deliberately kept above the append-only note that follows so that note
    # continues to describe the code it actually governs. Rotation is safe
    # against the concurrency property for two reasons: it is a single
    # os.replace (atomic on the same volume, so no reader ever sees a partial
    # file), and a session whose prior record was rotated away appends one
    # duplicate -- which the dedupe docstring already calls harmless.
    rotate_if_large(out_file)

    # Nothing observable changed since this session's last record -> writing
    # it again adds a line and no information. Append-only is preserved on
    # this path: the dedupe below only ever declines to write, it never
    # rewrites or removes an existing record, so it keeps the concurrency
    # property that has held 963 lines of interleaved multi-session appends
    # at zero corruption.
    if is_duplicate_of_last(out_file, session_id, record):
        return

    with open(out_file, "a", encoding="ascii") as fh:
        fh.write(json.dumps(record) + "\n")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # Fail open: telemetry must never block a session.
        pass
    sys.exit(0)
