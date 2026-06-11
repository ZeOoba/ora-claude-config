"""Tests for eos-evidence-gate.py PreToolUse hook (Bash) -- NON-BLOCKING.

Run: python test-eos-evidence-gate.py
Stdlib only. ASCII-only. Self-contained.
"""

import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # hooks/ (test in hooks/tests/)
HOOK = os.path.join(HERE, "eos-evidence-gate.py")

REMINDER = (
    "[Engineering OS] No test/gate recorded this session - "
    "run the repo gate before committing code."
)


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


def test_commit_without_gate_reminds():
    tmp = tempfile.mkdtemp(prefix="eos-eg-")
    rc, out, err = run_hook(payload("s", "git commit -m x"), tmp)
    assert rc == 0, "expected exit 0, got %s (%s)" % (rc, err)
    assert REMINDER in out, "expected reminder, got %r" % out
    assert "deny" not in out, "must never deny, got %r" % out
    print("PASS test_commit_without_gate_reminds")


def test_commit_with_gate_silent():
    tmp = tempfile.mkdtemp(prefix="eos-eg-")
    sess_dir = os.path.join(tmp, "s")
    os.makedirs(sess_dir, exist_ok=True)
    with open(os.path.join(sess_dir, "gate-green"), "w") as fh:
        fh.write("")
    rc, out, err = run_hook(payload("s", "git commit -m x"), tmp)
    assert rc == 0, "expected exit 0, got %s" % rc
    assert out.strip() == "", "expected silent, got %r" % out
    print("PASS test_commit_with_gate_silent")


def test_non_commit_silent():
    tmp = tempfile.mkdtemp(prefix="eos-eg-")
    rc, out, err = run_hook(payload("s", "ls -la"), tmp)
    assert rc == 0, "expected exit 0, got %s" % rc
    assert out.strip() == "", "expected silent, got %r" % out
    print("PASS test_non_commit_silent")


def test_malformed_stdin_fails_open():
    tmp = tempfile.mkdtemp(prefix="eos-eg-")
    rc, out, err = run_hook("not json", tmp)
    assert rc == 0, "malformed stdin must exit 0, got %s" % rc
    assert "deny" not in out, "must never deny, got %r" % out
    print("PASS test_malformed_stdin_fails_open")


def test_empty_object_fails_open():
    tmp = tempfile.mkdtemp(prefix="eos-eg-")
    rc, out, err = run_hook(json.dumps({}), tmp)
    assert rc == 0, "empty object must exit 0, got %s" % rc
    print("PASS test_empty_object_fails_open")


if __name__ == "__main__":
    test_commit_without_gate_reminds()
    test_commit_with_gate_silent()
    test_non_commit_silent()
    test_malformed_stdin_fails_open()
    test_empty_object_fails_open()
    print("ALL EVIDENCE-GATE TESTS PASS")
