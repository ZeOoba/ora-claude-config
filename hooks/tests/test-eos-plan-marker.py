"""Tests for eos-plan-marker.py PostToolUse hook (Write|Edit).

Run: python test-eos-plan-marker.py
Stdlib only. ASCII-only. Self-contained.
"""

import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # hooks/ (test in hooks/tests/)
HOOK = os.path.join(HERE, "eos-plan-marker.py")


def run_hook(stdin_text, sessions_dir):
    env = dict(os.environ)
    env["EOS_SESSIONS_DIR"] = sessions_dir
    proc = subprocess.run(
        [sys.executable, HOOK],
        input=stdin_text,
        capture_output=True,
        text=True,
        env=env,
    )
    return proc.returncode, proc.stdout, proc.stderr


def payload(session_id, file_path):
    return json.dumps(
        {"session_id": session_id, "tool_input": {"file_path": file_path}}
    )


def test_plan_path_creates_marker():
    tmp = tempfile.mkdtemp(prefix="eos-pm-")
    p = "C:/Users/x/.claude/docs/superpowers/plans/foo.md"
    rc, out, err = run_hook(payload("s1", p), tmp)
    assert rc == 0, "expected exit 0, got %s (%s)" % (rc, err)
    marker = os.path.join(tmp, "s1", "plan-approved")
    assert os.path.exists(marker), "plan-approved marker not created"
    print("PASS test_plan_path_creates_marker")


def test_plan_path_backslash_creates_marker():
    tmp = tempfile.mkdtemp(prefix="eos-pm-")
    p = r"C:\Users\x\.claude\docs\superpowers\plans\foo.md"
    rc, out, err = run_hook(payload("s2", p), tmp)
    assert rc == 0, "expected exit 0, got %s" % rc
    marker = os.path.join(tmp, "s2", "plan-approved")
    assert os.path.exists(marker), "plan-approved marker not created (backslash)"
    print("PASS test_plan_path_backslash_creates_marker")


def test_non_plan_path_no_marker():
    tmp = tempfile.mkdtemp(prefix="eos-pm-")
    rc, out, err = run_hook(payload("s3", "C:/proj/src/x.py"), tmp)
    assert rc == 0, "expected exit 0, got %s" % rc
    marker = os.path.join(tmp, "s3", "plan-approved")
    assert not os.path.exists(marker), "marker should not exist for non-plan path"
    print("PASS test_non_plan_path_no_marker")


def test_malformed_stdin_fails_open():
    tmp = tempfile.mkdtemp(prefix="eos-pm-")
    rc, out, err = run_hook("not json", tmp)
    assert rc == 0, "malformed stdin must exit 0, got %s" % rc
    print("PASS test_malformed_stdin_fails_open")


def test_empty_object_fails_open():
    tmp = tempfile.mkdtemp(prefix="eos-pm-")
    rc, out, err = run_hook(json.dumps({}), tmp)
    assert rc == 0, "empty object must exit 0, got %s" % rc
    print("PASS test_empty_object_fails_open")


if __name__ == "__main__":
    test_plan_path_creates_marker()
    test_plan_path_backslash_creates_marker()
    test_non_plan_path_no_marker()
    test_malformed_stdin_fails_open()
    test_empty_object_fails_open()
    print("ALL PLAN-MARKER TESTS PASS")
