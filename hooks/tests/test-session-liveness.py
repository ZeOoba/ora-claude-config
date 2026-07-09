"""Tests for hooks/lib/session_liveness.py.

Run: python test-session-liveness.py
Stdlib only. ASCII-only. Self-contained (creates its own temp state files).
"""
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # hooks/ (test in hooks/tests/)
LIB = os.path.join(HERE, "lib")
sys.path.insert(0, LIB)
from session_liveness import other_active_sessions  # noqa: E402


def write_state(d):
    fd, path = tempfile.mkstemp(suffix="_session-state.json")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(d, fh)
    return path


def test_missing_file_fails_open():
    result = other_active_sessions("own", state_path="C:/does/not/exist_xyz.json")
    assert result == [], "missing file must return [], got %r" % result
    print("PASS test_missing_file_fails_open")


def test_malformed_json_fails_open():
    fd, path = tempfile.mkstemp(suffix="_session-state.json")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write("not json")
    try:
        result = other_active_sessions("own", state_path=path)
        assert result == [], "malformed JSON must return [], got %r" % result
    finally:
        os.remove(path)
    print("PASS test_malformed_json_fails_open")


def test_wrong_shape_fails_open():
    path = write_state({"sessions": "not a dict"})
    try:
        result = other_active_sessions("own", state_path=path)
        assert result == [], "wrong-shape sessions must return [], got %r" % result
    finally:
        os.remove(path)
    print("PASS test_wrong_shape_fails_open")


def test_excludes_own_sid():
    path = write_state({"sessions": {"own": {"status": "working", "cwd": "C:/x", "lastAt": "t"}}})
    try:
        result = other_active_sessions("own", state_path=path)
        assert result == [], "own sid must be excluded, got %r" % result
    finally:
        os.remove(path)
    print("PASS test_excludes_own_sid")


def test_returns_other_sessions_with_fields():
    path = write_state({
        "sessions": {
            "own": {"status": "working", "cwd": "C:/mine", "lastAt": "t1"},
            "other1": {"status": "idle", "cwd": "C:/theirs", "lastAt": "t2"},
        }
    })
    try:
        result = other_active_sessions("own", state_path=path)
        assert len(result) == 1, "expected exactly 1 other session, got %r" % result
        assert result[0] == {"sid": "other1", "status": "idle", "cwd": "C:/theirs", "lastAt": "t2"}, (
            "unexpected fields: %r" % result[0])
    finally:
        os.remove(path)
    print("PASS test_returns_other_sessions_with_fields")


def test_malformed_session_entry_skipped():
    path = write_state({"sessions": {"own": {}, "bad": "not a dict", "other1": {"status": "working"}}})
    try:
        result = other_active_sessions("own", state_path=path)
        sids = [r["sid"] for r in result]
        assert sids == ["other1"], "malformed entry must be skipped, got %r" % result
    finally:
        os.remove(path)
    print("PASS test_malformed_session_entry_skipped")


if __name__ == "__main__":
    test_missing_file_fails_open()
    test_malformed_json_fails_open()
    test_wrong_shape_fails_open()
    test_excludes_own_sid()
    test_returns_other_sessions_with_fields()
    test_malformed_session_entry_skipped()
    print("ALL SESSION-LIVENESS TESTS PASS")
