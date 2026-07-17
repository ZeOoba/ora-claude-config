"""Tests for commit-provenance-recorder.py PostToolUse hook.

Run: python test-commit-provenance-recorder.py
Stdlib only. ASCII-only. Self-contained (creates its own temp dirs).
Append-only / fail-open: the recorder NEVER blocks and never rewrites the file.
"""

import json
import os
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # hooks/
HOOK = os.path.join(HERE, "commit-provenance-recorder.py")


def run_hook(stdin_text, sessions_dir):
    env = dict(os.environ)
    env["COMMIT_PROVENANCE_SESSIONS_DIR"] = sessions_dir
    proc = subprocess.run(
        [sys.executable, HOOK], input=stdin_text,
        capture_output=True, text=True, env=env,
    )
    return proc.returncode, proc.stdout, proc.stderr


def sessions_tmp():
    return tempfile.mkdtemp(prefix="cpr-sess-")


def raw_lines(sessions_dir, sid):
    p = os.path.join(sessions_dir, sid, "touched-files.txt")
    if not os.path.exists(p):
        return []
    with open(p, encoding="utf-8") as fh:
        return [ln.strip() for ln in fh if ln.strip()]


def read_touched(sessions_dir, sid):
    """Just the path portion of each line (2026-07-17 format: path\\tepoch)."""
    return [ln.partition("\t")[0] for ln in raw_lines(sessions_dir, sid)]


def test_edit_payload_records_file_path():
    sess = sessions_tmp()
    target = "C:/Users/Owner/.claude/some/file.md"
    payload = json.dumps({"session_id": "s1", "tool_input": {"file_path": target}})
    rc, out, err = run_hook(payload, sess)
    assert rc == 0, "recorder must never block, got %s (%s)" % (rc, err)
    got = read_touched(sess, "s1")
    assert got == [os.path.normcase(os.path.abspath(target))], "got %r" % got
    print("PASS test_edit_payload_records_file_path")


def test_desktop_commander_payload_uses_path_field():
    """DC's write_file uses 'path', not 'file_path' -- the same gap
    registry-write-guard.py and memory-index-guard.py both had to close."""
    sess = sessions_tmp()
    target = "C:/Users/Owner/.claude/other/file.md"
    payload = json.dumps({"session_id": "s2", "tool_input": {"path": target}})
    rc, out, err = run_hook(payload, sess)
    assert rc == 0
    got = read_touched(sess, "s2")
    assert got == [os.path.normcase(os.path.abspath(target))], "got %r" % got
    print("PASS test_desktop_commander_payload_uses_path_field")


def test_repeated_writes_append_not_overwrite():
    """Append-only: no read-modify-write, so no race. Duplicates are expected
    and are deduped by the READER, not the writer."""
    sess = sessions_tmp()
    a = "C:/Users/Owner/.claude/a.md"
    b = "C:/Users/Owner/.claude/b.md"
    for t in (a, b, a):
        run_hook(json.dumps({"session_id": "s3", "tool_input": {"file_path": t}}), sess)
    got = read_touched(sess, "s3")
    assert len(got) == 3, "append-only must keep all 3 lines, got %r" % got
    assert os.path.normcase(os.path.abspath(b)) in got, "got %r" % got
    print("PASS test_repeated_writes_append_not_overwrite")


def test_malformed_stdin_fails_open():
    sess = sessions_tmp()
    rc, out, err = run_hook("not json", sess)
    assert rc == 0, "malformed stdin must exit 0, got %s" % rc
    print("PASS test_malformed_stdin_fails_open")


def test_missing_path_is_noop():
    sess = sessions_tmp()
    rc, out, err = run_hook(json.dumps({"session_id": "s4", "tool_input": {}}), sess)
    assert rc == 0
    assert read_touched(sess, "s4") == [], "no path -> nothing recorded"
    print("PASS test_missing_path_is_noop")


def test_line_carries_a_recent_timestamp():
    """2026-07-17: the recency-heuristic fix needs a per-touch timestamp, not
    just a bare path. Mutation check: reverting touch_line() to write a bare
    path (no tab) makes this test fail -- it is not a vacuous pass."""
    sess = sessions_tmp()
    target = "C:/Users/Owner/.claude/timed/file.md"
    before = time.time()
    rc, out, err = run_hook(
        json.dumps({"session_id": "s5", "tool_input": {"file_path": target}}), sess)
    after = time.time()
    assert rc == 0
    lines = raw_lines(sess, "s5")
    assert len(lines) == 1, "got %r" % lines
    assert "\t" in lines[0], "line must carry a tab-separated timestamp, got %r" % lines[0]
    path, _, ts_str = lines[0].partition("\t")
    assert path == os.path.normcase(os.path.abspath(target)), "got %r" % path
    ts = float(ts_str)
    assert before - 1 <= ts <= after + 1, (
        "timestamp must be roughly 'now', got %s (window %s..%s)" % (ts, before, after))
    print("PASS test_line_carries_a_recent_timestamp")


if __name__ == "__main__":
    test_edit_payload_records_file_path()
    test_desktop_commander_payload_uses_path_field()
    test_repeated_writes_append_not_overwrite()
    test_malformed_stdin_fails_open()
    test_missing_path_is_noop()
    test_line_carries_a_recent_timestamp()
    print("ALL COMMIT-PROVENANCE-RECORDER TESTS PASS")
