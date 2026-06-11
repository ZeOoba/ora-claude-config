"""Tests for eos-gate-sentinel.py PostToolUse hook (Bash).

Run: python test-eos-gate-sentinel.py
Stdlib only. ASCII-only. Self-contained.
"""

import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # hooks/ (test in hooks/tests/)
HOOK = os.path.join(HERE, "eos-gate-sentinel.py")


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


def payload(session_id, command):
    return json.dumps(
        {"session_id": session_id, "tool_input": {"command": command}}
    )


def test_gate_command_creates_marker():
    tmp = tempfile.mkdtemp(prefix="eos-gs-")
    rc, out, err = run_hook(payload("s", "npm run gate"), tmp)
    assert rc == 0, "expected exit 0, got %s (%s)" % (rc, err)
    marker = os.path.join(tmp, "s", "gate-green")
    assert os.path.exists(marker), "gate-green marker not created"
    print("PASS test_gate_command_creates_marker")


def test_various_test_commands_create_marker():
    for i, cmd in enumerate(
        ["pytest -q", "vitest run", "go test ./...", "cargo test",
         "npm test", "python test-foo.py"]
    ):
        tmp = tempfile.mkdtemp(prefix="eos-gs-")
        rc, out, err = run_hook(payload("s%d" % i, cmd), tmp)
        assert rc == 0, "%r expected exit 0, got %s" % (cmd, rc)
        marker = os.path.join(tmp, "s%d" % i, "gate-green")
        assert os.path.exists(marker), "%r should create gate-green" % cmd
    print("PASS test_various_test_commands_create_marker")


def test_non_test_command_no_marker():
    tmp = tempfile.mkdtemp(prefix="eos-gs-")
    rc, out, err = run_hook(payload("s", "ls -la"), tmp)
    assert rc == 0, "expected exit 0, got %s" % rc
    marker = os.path.join(tmp, "s", "gate-green")
    assert not os.path.exists(marker), "ls must not create gate-green"
    print("PASS test_non_test_command_no_marker")


def test_malformed_stdin_fails_open():
    tmp = tempfile.mkdtemp(prefix="eos-gs-")
    rc, out, err = run_hook("not json", tmp)
    assert rc == 0, "malformed stdin must exit 0, got %s" % rc
    print("PASS test_malformed_stdin_fails_open")


def test_empty_object_fails_open():
    tmp = tempfile.mkdtemp(prefix="eos-gs-")
    rc, out, err = run_hook(json.dumps({}), tmp)
    assert rc == 0, "empty object must exit 0, got %s" % rc
    print("PASS test_empty_object_fails_open")


if __name__ == "__main__":
    test_gate_command_creates_marker()
    test_various_test_commands_create_marker()
    test_non_test_command_no_marker()
    test_malformed_stdin_fails_open()
    test_empty_object_fails_open()
    print("ALL GATE-SENTINEL TESTS PASS")
