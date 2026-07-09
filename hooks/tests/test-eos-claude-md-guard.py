"""Tests for eos-claude-md-guard.py PreToolUse hook (Edit|Write|MultiEdit).

Run: python test-eos-claude-md-guard.py
Stdlib only. ASCII-only. Self-contained (creates its own temp CLAUDE.md fixtures).
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # hooks/ (test in hooks/tests/)
HOOK = os.path.join(HERE, "eos-claude-md-guard.py")

BASE = "## Engineering OS\nsome doctrine text\n"


def run_hook(payload, claude_md_path):
    env = dict(os.environ)
    env["EOS_CLAUDE_MD"] = claude_md_path
    proc = subprocess.run(
        [sys.executable, HOOK],
        input=json.dumps(payload), capture_output=True, text=True, env=env,
    )
    return proc.returncode, proc.stdout, proc.stderr


def make_claude_md(content):
    fd, path = tempfile.mkstemp(suffix="_CLAUDE.md", text=True)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(content)
    return path


def test_non_claude_md_path_silent():
    path = make_claude_md(BASE)
    try:
        rc, out, err = run_hook(
            {"tool_name": "Write", "tool_input": {"file_path": "C:/other/file.md", "content": "x"}},
            path,
        )
        assert rc == 0 and out.strip() == "", "non-CLAUDE.md path must be silent, got %r/%r" % (rc, out)
    finally:
        os.remove(path)
    print("PASS test_non_claude_md_path_silent")


def test_write_clean_allows():
    path = make_claude_md(BASE)
    try:
        rc, out, err = run_hook(
            {"tool_name": "Write", "tool_input": {"file_path": path, "content": BASE + "more text\n"}},
            path,
        )
        assert rc == 0, "clean Write expected exit 0, got %s (%s)" % (rc, err)
        assert "deny" not in out, "clean Write must not deny, got %r" % out
    finally:
        os.remove(path)
    print("PASS test_write_clean_allows")


def test_write_over_budget_denies():
    path = make_claude_md(BASE)
    try:
        over = BASE + ("word " * 1900)
        rc, out, err = run_hook(
            {"tool_name": "Write", "tool_input": {"file_path": path, "content": over}},
            path,
        )
        assert rc == 0, "hook itself always exits 0, got %s" % rc
        assert '"permissionDecision": "deny"' in out or '"permissionDecision":"deny"' in out, (
            "over-budget Write must deny, got %r" % out)
        assert "size budget exceeded" in out, "expected size-budget reason text, got %r" % out
    finally:
        os.remove(path)
    print("PASS test_write_over_budget_denies")


def test_write_bare_date_denies():
    path = make_claude_md(BASE)
    try:
        dated = BASE + "- ratified 2026-06-10, do not unify\n"
        rc, out, err = run_hook(
            {"tool_name": "Write", "tool_input": {"file_path": path, "content": dated}},
            path,
        )
        assert '"permissionDecision": "deny"' in out or '"permissionDecision":"deny"' in out, (
            "bare-date Write must deny, got %r" % out)
        assert "bare date 2026-06-10" in out, "expected bare-date reason text, got %r" % out
    finally:
        os.remove(path)
    print("PASS test_write_bare_date_denies")


def test_edit_clean_result_allows():
    path = make_claude_md(BASE + "old phrase here\n")
    try:
        rc, out, err = run_hook(
            {"tool_name": "Edit", "tool_input": {
                "file_path": path, "old_string": "old phrase here", "new_string": "new phrase here"}},
            path,
        )
        assert rc == 0 and "deny" not in out, "clean Edit must not deny, got %r" % out
    finally:
        os.remove(path)
    print("PASS test_edit_clean_result_allows")


def test_edit_producing_bare_date_denies():
    path = make_claude_md(BASE + "old phrase here\n")
    try:
        rc, out, err = run_hook(
            {"tool_name": "Edit", "tool_input": {
                "file_path": path, "old_string": "old phrase here",
                "new_string": "ratified 2026-06-10, do not unify"}},
            path,
        )
        assert '"permissionDecision": "deny"' in out or '"permissionDecision":"deny"' in out, (
            "Edit producing a bare date must deny, got %r" % out)
    finally:
        os.remove(path)
    print("PASS test_edit_producing_bare_date_denies")


def test_edit_ambiguous_match_fails_open():
    path = make_claude_md(BASE + "dup\ndup\n")
    try:
        rc, out, err = run_hook(
            {"tool_name": "Edit", "tool_input": {
                "file_path": path, "old_string": "dup", "new_string": "2026-06-10"}},
            path,
        )
        assert rc == 0 and "deny" not in out, (
            "ambiguous (2x) old_string match must fail open, not deny, got %r" % out)
    finally:
        os.remove(path)
    print("PASS test_edit_ambiguous_match_fails_open")


def test_multiedit_final_result_denies():
    path = make_claude_md(BASE + "alpha\nbeta\n")
    try:
        rc, out, err = run_hook(
            {"tool_name": "MultiEdit", "tool_input": {
                "file_path": path,
                "edits": [
                    {"old_string": "alpha", "new_string": "2026-06-10"},
                    {"old_string": "beta", "new_string": "unchanged"},
                ],
            }},
            path,
        )
        assert '"permissionDecision": "deny"' in out or '"permissionDecision":"deny"' in out, (
            "MultiEdit producing a bare date must deny, got %r" % out)
    finally:
        os.remove(path)
    print("PASS test_multiedit_final_result_denies")


def test_malformed_stdin_fails_open():
    path = make_claude_md(BASE)
    try:
        env = dict(os.environ)
        env["EOS_CLAUDE_MD"] = path
        proc = subprocess.run([sys.executable, HOOK], input="not json",
                              capture_output=True, text=True, env=env)
        assert proc.returncode == 0, "malformed stdin must exit 0, got %s" % proc.returncode
        assert "deny" not in proc.stdout, "fail-open must not deny, got %r" % proc.stdout
    finally:
        os.remove(path)
    print("PASS test_malformed_stdin_fails_open")


def test_missing_target_fails_open():
    rc, out, err = run_hook(
        {"tool_name": "Write", "tool_input": {"file_path": "C:/does/not/exist_xyz/CLAUDE.md",
                                               "content": "word " * 1900}},
        "C:/does/not/exist_xyz/CLAUDE.md",
    )
    assert rc == 0 and "deny" not in out, "missing target must fail open, got %r" % out
    print("PASS test_missing_target_fails_open")


if __name__ == "__main__":
    test_non_claude_md_path_silent()
    test_write_clean_allows()
    test_write_over_budget_denies()
    test_write_bare_date_denies()
    test_edit_clean_result_allows()
    test_edit_producing_bare_date_denies()
    test_edit_ambiguous_match_fails_open()
    test_multiedit_final_result_denies()
    test_malformed_stdin_fails_open()
    test_missing_target_fails_open()
    print("ALL EOS-CLAUDE-MD-GUARD TESTS PASS")
