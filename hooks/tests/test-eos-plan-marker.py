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


def test_native_plan_mode_path_creates_marker():
    """Native Claude Code plan-mode writes to ~/.claude/plans/*.md -- this must
    also count as an approved plan, not just the superpowers docs/ convention.
    Confirmed 2026-07-12: this session's own plan file wouldn't have cleared
    the gate before this fix."""
    tmp = tempfile.mkdtemp(prefix="eos-pm-")
    p = "C:/Users/Owner/.claude/plans/some-plan-slug.md"
    rc, out, err = run_hook(payload("s5", p), tmp)
    assert rc == 0, "expected exit 0, got %s (%s)" % (rc, err)
    marker = os.path.join(tmp, "s5", "plan-approved")
    assert os.path.exists(marker), "plan-approved marker not created for native plan-mode path"
    print("PASS test_native_plan_mode_path_creates_marker")


def test_native_plan_mode_path_backslash_creates_marker():
    tmp = tempfile.mkdtemp(prefix="eos-pm-")
    p = r"C:\Users\Owner\.claude\plans\some-plan-slug.md"
    rc, out, err = run_hook(payload("s6", p), tmp)
    assert rc == 0, "expected exit 0, got %s" % rc
    marker = os.path.join(tmp, "s6", "plan-approved")
    assert os.path.exists(marker), "plan-approved marker not created (backslash, native path)"
    print("PASS test_native_plan_mode_path_backslash_creates_marker")


def test_non_plan_path_no_marker():
    tmp = tempfile.mkdtemp(prefix="eos-pm-")
    rc, out, err = run_hook(payload("s3", "C:/proj/src/x.py"), tmp)
    assert rc == 0, "expected exit 0, got %s" % rc
    marker = os.path.join(tmp, "s3", "plan-approved")
    assert not os.path.exists(marker), "marker should not exist for non-plan path"
    print("PASS test_non_plan_path_no_marker")


def skill_payload(session_id, skill):
    return json.dumps(
        {"session_id": session_id, "tool_name": "Skill", "tool_input": {"skill": skill}}
    )


def test_lane_skill_creates_marker():
    """Invoking an Engineering OS lane skill (/build etc. via the Skill tool) IS
    the lane declaration -- it must clear the plan gate. Confirmed 2026-07-16:
    a /build session hit the gate mid-lane and was forced to override."""
    tmp = tempfile.mkdtemp(prefix="eos-pm-")
    rc, out, err = run_hook(skill_payload("s7", "build"), tmp)
    assert rc == 0, "expected exit 0, got %s (%s)" % (rc, err)
    marker = os.path.join(tmp, "s7", "plan-approved")
    assert os.path.exists(marker), "plan-approved marker not created for /build skill"
    with open(marker, "r", encoding="ascii") as fh:
        assert fh.read() == "lane:build", "marker should record the declaring lane"
    print("PASS test_lane_skill_creates_marker")


def test_all_lane_skills_create_marker():
    for i, skill in enumerate(("plan", "build", "debug", "refactor", "research", "ship")):
        tmp = tempfile.mkdtemp(prefix="eos-pm-")
        sid = "s8-%d" % i
        rc, out, err = run_hook(skill_payload(sid, skill), tmp)
        assert rc == 0, "expected exit 0 for %s, got %s" % (skill, rc)
        marker = os.path.join(tmp, sid, "plan-approved")
        assert os.path.exists(marker), "marker not created for lane skill %s" % skill
    print("PASS test_all_lane_skills_create_marker")


def test_non_lane_skill_no_marker():
    tmp = tempfile.mkdtemp(prefix="eos-pm-")
    rc, out, err = run_hook(skill_payload("s9", "tenant-email"), tmp)
    assert rc == 0, "expected exit 0, got %s" % rc
    marker = os.path.join(tmp, "s9", "plan-approved")
    assert not os.path.exists(marker), "non-lane skill must not create marker"
    print("PASS test_non_lane_skill_no_marker")


def test_skill_payload_without_skill_fails_open():
    tmp = tempfile.mkdtemp(prefix="eos-pm-")
    rc, out, err = run_hook(
        json.dumps({"session_id": "s10", "tool_name": "Skill", "tool_input": {}}), tmp
    )
    assert rc == 0, "Skill payload without skill name must exit 0, got %s" % rc
    marker = os.path.join(tmp, "s10", "plan-approved")
    assert not os.path.exists(marker), "no marker without a skill name"
    print("PASS test_skill_payload_without_skill_fails_open")


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
    test_native_plan_mode_path_creates_marker()
    test_native_plan_mode_path_backslash_creates_marker()
    test_non_plan_path_no_marker()
    test_lane_skill_creates_marker()
    test_all_lane_skills_create_marker()
    test_non_lane_skill_no_marker()
    test_skill_payload_without_skill_fails_open()
    test_malformed_stdin_fails_open()
    test_empty_object_fails_open()
    print("ALL PLAN-MARKER TESTS PASS")
