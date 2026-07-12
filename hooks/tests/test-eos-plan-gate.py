"""Tests for eos-plan-gate.py PreToolUse hook (Edit|Write|MultiEdit).

Run: python test-eos-plan-gate.py
Stdlib only. ASCII-only. Self-contained (creates its own temp dirs).
"""

import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # hooks/ (test in hooks/tests/)
HOOK = os.path.join(HERE, "eos-plan-gate.py")


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


def test_four_code_edits_denies_on_fourth():
    tmp = tempfile.mkdtemp(prefix="eos-pg-")
    # 3 allows, 4th denies
    for i in range(3):
        rc, out, err = run_hook(payload("sess1", "C:/proj/x.py"), tmp)
        assert rc == 0, "edit %d expected exit 0, got %s (%s)" % (i, rc, err)
        assert out.strip() == "", "edit %d expected empty stdout, got %r" % (i, out)
    rc, out, err = run_hook(payload("sess1", "C:/proj/x.py"), tmp)
    assert rc == 0, "4th edit expected exit 0, got %s" % rc
    assert '"permissionDecision": "deny"' in out or \
        '"permissionDecision":"deny"' in out, "4th edit must deny, got %r" % out
    print("PASS test_four_code_edits_denies_on_fourth")


def test_non_code_path_always_allows():
    tmp = tempfile.mkdtemp(prefix="eos-pg-")
    for path in ["C:/proj/readme.md", "C:/proj/docs/x.py", "C:/proj/memory/y.ts"]:
        for _ in range(6):
            rc, out, err = run_hook(payload("sess2", path), tmp)
            assert rc == 0, "%s expected exit 0, got %s" % (path, rc)
            assert "deny" not in out, "%s must never deny, got %r" % (path, out)
    print("PASS test_non_code_path_always_allows")


def test_override_marker_allows_past_limit():
    """A non-empty override (a real reason) clears the gate. Content is now
    REQUIRED -- see test_empty_override_content_still_denies."""
    tmp = tempfile.mkdtemp(prefix="eos-pg-")
    sess_dir = os.path.join(tmp, "sess3")
    os.makedirs(sess_dir, exist_ok=True)
    with open(os.path.join(sess_dir, "override"), "w") as fh:
        fh.write("reason: applying a planned mechanical fix\n")
    for _ in range(8):
        rc, out, err = run_hook(payload("sess3", "C:/proj/x.py"), tmp)
        assert rc == 0, "override expected exit 0, got %s" % rc
        assert "deny" not in out, "override must never deny, got %r" % out
    print("PASS test_override_marker_allows_past_limit")


def test_empty_override_content_still_denies():
    """An override file that EXISTS but is empty/whitespace-only must NOT count
    as approval -- only real, non-empty content clears the gate. Closes the
    presence-only enforcement gap: PR #12 fixed the denial message but not this;
    76/79 real override markers were still empty even after that fix shipped."""
    tmp = tempfile.mkdtemp(prefix="eos-pg-")
    sess_dir = os.path.join(tmp, "sess6")
    os.makedirs(sess_dir, exist_ok=True)
    with open(os.path.join(sess_dir, "override"), "w") as fh:
        fh.write("   \n")  # whitespace-only -- same as truly empty
    for i in range(3):
        rc, out, err = run_hook(payload("sess6", "C:/proj/x.py"), tmp)
        assert rc == 0, "edit %d expected exit 0, got %s" % (i, rc)
    rc, out, err = run_hook(payload("sess6", "C:/proj/x.py"), tmp)
    assert '"permissionDecision": "deny"' in out or '"permissionDecision":"deny"' in out, (
        "4th edit with empty-content override must still deny, got %r" % out
    )
    print("PASS test_empty_override_content_still_denies")


def test_plan_approved_marker_allows_past_limit():
    tmp = tempfile.mkdtemp(prefix="eos-pg-")
    sess_dir = os.path.join(tmp, "sess4")
    os.makedirs(sess_dir, exist_ok=True)
    with open(os.path.join(sess_dir, "plan-approved"), "w") as fh:
        fh.write("")
    for _ in range(8):
        rc, out, err = run_hook(payload("sess4", "C:/proj/x.py"), tmp)
        assert rc == 0, "plan-approved expected exit 0, got %s" % rc
        assert "deny" not in out, "plan-approved must never deny, got %r" % out
    print("PASS test_plan_approved_marker_allows_past_limit")


def test_malformed_stdin_fails_open():
    tmp = tempfile.mkdtemp(prefix="eos-pg-")
    rc, out, err = run_hook("not json", tmp)
    assert rc == 0, "malformed stdin must exit 0, got %s" % rc
    assert "deny" not in out, "fail-open must not deny, got %r" % out
    print("PASS test_malformed_stdin_fails_open")


def test_empty_object_fails_open():
    tmp = tempfile.mkdtemp(prefix="eos-pg-")
    rc, out, err = run_hook(json.dumps({}), tmp)
    assert rc == 0, "empty object must exit 0, got %s" % rc
    assert "deny" not in out, "fail-open must not deny, got %r" % out
    print("PASS test_empty_object_fails_open")


def test_denial_message_requests_reason():
    """The 4th-edit denial must ask for a written reason, not a bare touch,
    so the override carries an audit trail. Must still name the override path."""
    tmp = tempfile.mkdtemp(prefix="eos-pg-")
    for _ in range(3):
        run_hook(payload("sess5", "C:/proj/x.py"), tmp)
    rc, out, err = run_hook(payload("sess5", "C:/proj/x.py"), tmp)
    assert rc == 0, "4th edit expected exit 0, got %s" % rc
    decoded = json.loads(out)
    reason_text = decoded["hookSpecificOutput"]["permissionDecisionReason"]
    override_path = os.path.join(tmp, "sess5", "override")
    assert override_path.replace("\\", "/") in reason_text.replace("\\", "/"), (
        "denial must name the override path, got %r" % reason_text
    )
    assert "reason" in reason_text.lower(), (
        "denial must ask for a written reason (not a bare touch), got %r" % reason_text
    )
    print("PASS test_denial_message_requests_reason")


if __name__ == "__main__":
    test_four_code_edits_denies_on_fourth()
    test_non_code_path_always_allows()
    test_override_marker_allows_past_limit()
    test_empty_override_content_still_denies()
    test_plan_approved_marker_allows_past_limit()
    test_malformed_stdin_fails_open()
    test_empty_object_fails_open()
    test_denial_message_requests_reason()
    print("ALL PLAN-GATE TESTS PASS")
