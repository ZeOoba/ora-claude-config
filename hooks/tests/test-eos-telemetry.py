"""Tests for eos-telemetry.py SessionEnd hook.

Run: python test-eos-telemetry.py
Stdlib only. ASCII-only. Self-contained (creates its own temp dirs/files).
"""

import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # hooks/ (test in hooks/tests/)
HOOK = os.path.join(HERE, "eos-telemetry.py")


def run_hook(stdin_text, telemetry_dir, sessions_dir=None):
    """Run the hook as a subprocess. Returns (returncode, stdout, stderr)."""
    env = dict(os.environ)
    env["EOS_TELEMETRY_DIR"] = telemetry_dir
    if sessions_dir is not None:
        env["EOS_SESSIONS_DIR"] = sessions_dir
    proc = subprocess.run(
        [sys.executable, HOOK],
        input=stdin_text,
        capture_output=True,
        text=True,
        env=env,
    )
    return proc.returncode, proc.stdout, proc.stderr


def make_transcript(path):
    """Write a fake JSONL transcript with an Edit, a Bash 'npm run gate',
    an Agent tool_use, and an assistant text line containing 'Dispatch: Inline'."""
    lines = [
        # assistant message with a tool_use Edit
        {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": [
                    {
                        "type": "tool_use",
                        "name": "Edit",
                        "input": {"file_path": "C:/proj/foo.py"},
                    }
                ],
            },
        },
        # assistant message with a Bash tool_use running the gate
        {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": [
                    {
                        "type": "tool_use",
                        "name": "Bash",
                        "input": {"command": "npm run gate"},
                    }
                ],
            },
        },
        # assistant message dispatching a subagent. The tool is named
        # "Agent" -- "Task" has never appeared in any real transcript, so a
        # fixture built on that name certifies a dead branch.
        {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": [
                    {
                        "type": "tool_use",
                        "name": "Agent",
                        "input": {"description": "do thing"},
                    }
                ],
            },
        },
        # assistant text line with a lane declaration
        {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "Dispatch: Inline - claude-opus-4-8"}
                ],
            },
        },
        # a deliberately malformed line should be skipped, not crash
        "this is not json at all",
    ]
    with open(path, "w", encoding="ascii") as fh:
        for ln in lines:
            if isinstance(ln, str):
                fh.write(ln + "\n")
            else:
                fh.write(json.dumps(ln) + "\n")


def test_happy_path():
    tmp = tempfile.mkdtemp(prefix="eos-test-")
    transcript = os.path.join(tmp, "transcript.jsonl")
    tele_dir = os.path.join(tmp, "telemetry")
    make_transcript(transcript)

    stdin = json.dumps({"session_id": "test123", "transcript_path": transcript})
    rc, out, err = run_hook(stdin, tele_dir)
    assert rc == 0, "expected exit 0, got %s (stderr=%s)" % (rc, err)

    out_file = os.path.join(tele_dir, "lane-telemetry.jsonl")
    assert os.path.exists(out_file), "telemetry file was not created"
    with open(out_file, "r", encoding="ascii") as fh:
        data_lines = [l for l in fh.read().splitlines() if l.strip()]
    assert len(data_lines) == 1, "expected exactly 1 line, got %d" % len(data_lines)

    rec = json.loads(data_lines[0])
    assert rec["session_id"] == "test123", rec
    assert rec["edits"] >= 1, rec
    assert rec["bash_test_ran"] is True, rec
    assert rec["task_dispatched"] is True, rec
    assert rec["lane_declared"] is True, rec
    assert "C:/proj/foo.py" in rec["files"], rec
    print("PASS test_happy_path")


def test_malformed_stdin_fails_open():
    tmp = tempfile.mkdtemp(prefix="eos-test-")
    tele_dir = os.path.join(tmp, "telemetry")
    rc, out, err = run_hook("not json", tele_dir)
    assert rc == 0, "malformed stdin must exit 0, got %s" % rc
    assert out == "", "expected no stdout, got %r" % out
    print("PASS test_malformed_stdin_fails_open")


def test_empty_object_fails_open():
    tmp = tempfile.mkdtemp(prefix="eos-test-")
    tele_dir = os.path.join(tmp, "telemetry")
    rc, out, err = run_hook(json.dumps({}), tele_dir)
    assert rc == 0, "empty object must exit 0, got %s" % rc
    print("PASS test_empty_object_fails_open")


def test_missing_transcript_fails_open():
    tmp = tempfile.mkdtemp(prefix="eos-test-")
    tele_dir = os.path.join(tmp, "telemetry")
    stdin = json.dumps(
        {"session_id": "x", "transcript_path": os.path.join(tmp, "nope.jsonl")}
    )
    rc, out, err = run_hook(stdin, tele_dir)
    assert rc == 0, "missing transcript must exit 0, got %s" % rc
    # No code activity / unreadable -> nothing written
    out_file = os.path.join(tele_dir, "lane-telemetry.jsonl")
    assert not os.path.exists(out_file) or os.path.getsize(out_file) == 0, (
        "should not write telemetry for missing transcript"
    )
    print("PASS test_missing_transcript_fails_open")


def test_no_code_activity_skipped():
    """A transcript with only text (no edits, no bash test, no task) writes nothing."""
    tmp = tempfile.mkdtemp(prefix="eos-test-")
    transcript = os.path.join(tmp, "t.jsonl")
    tele_dir = os.path.join(tmp, "telemetry")
    with open(transcript, "w", encoding="ascii") as fh:
        fh.write(
            json.dumps(
                {
                    "type": "assistant",
                    "message": {
                        "role": "assistant",
                        "content": [{"type": "text", "text": "hello there"}],
                    },
                }
            )
            + "\n"
        )
    stdin = json.dumps({"session_id": "y", "transcript_path": transcript})
    rc, out, err = run_hook(stdin, tele_dir)
    assert rc == 0, rc
    out_file = os.path.join(tele_dir, "lane-telemetry.jsonl")
    assert not os.path.exists(out_file) or os.path.getsize(out_file) == 0, (
        "non-coding session should write nothing"
    )
    print("PASS test_no_code_activity_skipped")


def test_task_management_tools_are_not_dispatch():
    """TaskCreate/TaskUpdate/TaskList are todo-management tools, NOT subagent
    dispatch. A prefix or substring match on "Task" would silently inflate
    task_dispatched with todo churn -- detection must be exact-match."""
    tmp = tempfile.mkdtemp(prefix="eos-test-")
    transcript = os.path.join(tmp, "t.jsonl")
    tele_dir = os.path.join(tmp, "telemetry")
    lines = [
        # one real edit so the session still qualifies as a coding session
        {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": [
                    {
                        "type": "tool_use",
                        "name": "Edit",
                        "input": {"file_path": "C:/proj/bar.py"},
                    }
                ],
            },
        },
    ]
    # Real Task* management tools, plus two synthetic names that are proper
    # SUBSTRINGS of "Agent". The latter pin exact-match semantics regardless of
    # container type: if DISPATCH_TOOLS ever degrades to a bare string, `tname
    # in DISPATCH_TOOLS` becomes substring containment and these two match.
    for tool in ("TaskCreate", "TaskUpdate", "TaskList", "TaskGet",
                 "TaskOutput", "TaskStop", "Age", "gen"):
        lines.append(
            {
                "type": "assistant",
                "message": {
                    "role": "assistant",
                    "content": [
                        {"type": "tool_use", "name": tool, "input": {}}
                    ],
                },
            }
        )
    with open(transcript, "w", encoding="ascii") as fh:
        for ln in lines:
            fh.write(json.dumps(ln) + "\n")

    stdin = json.dumps({"session_id": "task-mgmt", "transcript_path": transcript})
    rc, out, err = run_hook(stdin, tele_dir)
    assert rc == 0, "expected exit 0, got %s (stderr=%s)" % (rc, err)

    out_file = os.path.join(tele_dir, "lane-telemetry.jsonl")
    with open(out_file, "r", encoding="ascii") as fh:
        rec = json.loads(fh.read().splitlines()[-1])
    assert rec["task_dispatched"] is False, (
        "Task* management tools must NOT count as subagent dispatch: %r" % rec
    )
    print("PASS test_task_management_tools_are_not_dispatch")


def test_override_used_surfaces_reason():
    tmp = tempfile.mkdtemp(prefix="eos-test-")
    transcript = os.path.join(tmp, "transcript.jsonl")
    tele_dir = os.path.join(tmp, "telemetry")
    sessions_dir = os.path.join(tmp, "sessions")
    make_transcript(transcript)

    sess_dir = os.path.join(sessions_dir, "test-override")
    os.makedirs(sess_dir, exist_ok=True)
    with open(os.path.join(sess_dir, "override"), "w", encoding="utf-8") as fh:
        fh.write("reason: applying planned fleet migration, plan doc pending")

    stdin = json.dumps({"session_id": "test-override", "transcript_path": transcript})
    rc, out, err = run_hook(stdin, tele_dir, sessions_dir)
    assert rc == 0, "expected exit 0, got %s (stderr=%s)" % (rc, err)

    out_file = os.path.join(tele_dir, "lane-telemetry.jsonl")
    with open(out_file, "r", encoding="ascii") as fh:
        rec = json.loads(fh.read().splitlines()[-1])
    assert rec["override_used"] is True, rec
    assert rec["override_reason"] == "reason: applying planned fleet migration, plan doc pending", rec
    assert rec["override_at"], "expected a non-empty override_at timestamp, got %r" % rec
    print("PASS test_override_used_surfaces_reason")


def test_override_used_no_reason_backward_compat():
    """Old-style 0-byte override files (pre-fix) must still surface override_used=True
    with a null reason, not crash telemetry."""
    tmp = tempfile.mkdtemp(prefix="eos-test-")
    transcript = os.path.join(tmp, "transcript.jsonl")
    tele_dir = os.path.join(tmp, "telemetry")
    sessions_dir = os.path.join(tmp, "sessions")
    make_transcript(transcript)

    sess_dir = os.path.join(sessions_dir, "test-empty-override")
    os.makedirs(sess_dir, exist_ok=True)
    open(os.path.join(sess_dir, "override"), "w").close()  # 0 bytes, old style

    stdin = json.dumps({"session_id": "test-empty-override", "transcript_path": transcript})
    rc, out, err = run_hook(stdin, tele_dir, sessions_dir)
    assert rc == 0, "expected exit 0, got %s (stderr=%s)" % (rc, err)

    out_file = os.path.join(tele_dir, "lane-telemetry.jsonl")
    with open(out_file, "r", encoding="ascii") as fh:
        rec = json.loads(fh.read().splitlines()[-1])
    assert rec["override_used"] is True, rec
    assert rec["override_reason"] is None, rec
    print("PASS test_override_used_no_reason_backward_compat")


def test_no_override_file():
    tmp = tempfile.mkdtemp(prefix="eos-test-")
    transcript = os.path.join(tmp, "transcript.jsonl")
    tele_dir = os.path.join(tmp, "telemetry")
    sessions_dir = os.path.join(tmp, "sessions")
    make_transcript(transcript)

    stdin = json.dumps({"session_id": "test-no-override", "transcript_path": transcript})
    rc, out, err = run_hook(stdin, tele_dir, sessions_dir)
    assert rc == 0, "expected exit 0, got %s (stderr=%s)" % (rc, err)

    out_file = os.path.join(tele_dir, "lane-telemetry.jsonl")
    with open(out_file, "r", encoding="ascii") as fh:
        rec = json.loads(fh.read().splitlines()[-1])
    assert rec["override_used"] is False, rec
    assert rec["override_reason"] is None, rec
    assert rec["override_at"] is None, rec
    print("PASS test_no_override_file")


if __name__ == "__main__":
    test_happy_path()
    test_malformed_stdin_fails_open()
    test_empty_object_fails_open()
    test_missing_transcript_fails_open()
    test_no_code_activity_skipped()
    test_task_management_tools_are_not_dispatch()
    test_override_used_surfaces_reason()
    test_override_used_no_reason_backward_compat()
    test_no_override_file()
    print("ALL TELEMETRY TESTS PASS")
