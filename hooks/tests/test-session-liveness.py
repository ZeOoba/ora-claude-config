"""Tests for hooks/lib/session_liveness.py.

Run: python test-session-liveness.py
Stdlib only. ASCII-only. Self-contained (creates its own temp state files/dirs).
"""
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # hooks/ (test in hooks/tests/)
LIB = os.path.join(HERE, "lib")
sys.path.insert(0, LIB)
from session_liveness import other_active_sessions  # noqa: E402


def write_state(d):
    """Legacy single-file fixture -- the OLD format other_active_sessions() reads via
    an explicit `state_path=` override."""
    fd, path = tempfile.mkstemp(suffix="_session-state.json")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(d, fh)
    return path


def write_sessions_dir(sessions):
    """A per-session-file fixture -- the NEW format other_active_sessions() reads via
    an explicit `sessions_dir=` override. `sessions` is {sid: session_dict}; each
    session_dict need not include "_sid" (the reader falls back to the filename)."""
    root = tempfile.mkdtemp(prefix="liveness-newfmt-")
    for sid, s in sessions.items():
        with open(os.path.join(root, sid + ".json"), "w", encoding="utf-8") as fh:
            json.dump(s, fh)
    return root


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


# ===================================================================================
# NEW FORMAT (2026-07-24): per-session-file directory, the format the redesigned
# fleet-session-hook.py actually writes now. An explicit `sessions_dir=` override
# (like the legacy tests' `state_path=` above) is deterministic regardless of
# whatever real machine state happens to exist.
# ===================================================================================

def test_new_format_missing_dir_fails_open():
    result = other_active_sessions("own", sessions_dir="C:/does/not/exist_xyz_dir")
    assert result == [], "missing directory must return [], got %r" % result
    print("PASS test_new_format_missing_dir_fails_open")


def test_new_format_malformed_file_skipped():
    root = write_sessions_dir({"own": {"status": "working"}})
    with open(os.path.join(root, "bad.json"), "w", encoding="utf-8") as fh:
        fh.write("not json")
    try:
        result = other_active_sessions("own", sessions_dir=root)
        assert result == [], "malformed sibling file must be skipped, got %r" % result
    finally:
        shutil.rmtree(root, ignore_errors=True)
    print("PASS test_new_format_malformed_file_skipped")


def test_new_format_excludes_own_sid():
    root = write_sessions_dir({"own": {"status": "working", "cwd": "C:/x", "lastAt": "t"}})
    try:
        result = other_active_sessions("own", sessions_dir=root)
        assert result == [], "own sid must be excluded, got %r" % result
    finally:
        shutil.rmtree(root, ignore_errors=True)
    print("PASS test_new_format_excludes_own_sid")


def test_new_format_returns_other_sessions_with_fields():
    root = write_sessions_dir({
        "own": {"status": "working", "cwd": "C:/mine", "lastAt": "t1"},
        "other1": {"status": "idle", "cwd": "C:/theirs", "lastAt": "t2"},
    })
    try:
        result = other_active_sessions("own", sessions_dir=root)
        assert len(result) == 1, "expected exactly 1 other session, got %r" % result
        assert result[0] == {"sid": "other1", "status": "idle", "cwd": "C:/theirs", "lastAt": "t2"}, (
            "unexpected fields: %r" % result[0])
    finally:
        shutil.rmtree(root, ignore_errors=True)
    print("PASS test_new_format_returns_other_sessions_with_fields")


def test_new_format_prefers_embedded_sid_over_filename():
    """A session file's OWN "_sid" field (written by fleet-session-hook.py's
    save_session()) is authoritative over the filename, matching how the writer
    actually recovers the true sid -- see _safe_filename()'s docstring."""
    root = tempfile.mkdtemp(prefix="liveness-sidfield-")
    with open(os.path.join(root, "sanitized_name.json"), "w", encoding="utf-8") as fh:
        json.dump({"_sid": "real-sid-with-slash", "status": "working", "cwd": "C:/x",
                   "lastAt": "t"}, fh)
    try:
        result = other_active_sessions("own", sessions_dir=root)
        assert result and result[0]["sid"] == "real-sid-with-slash", (
            "must use the embedded _sid, not the filename, got %r" % result)
    finally:
        shutil.rmtree(root, ignore_errors=True)
    print("PASS test_new_format_prefers_embedded_sid_over_filename")


def test_new_format_malformed_session_entry_skipped():
    root = write_sessions_dir({"own": {}, "other1": {"status": "working"}})
    with open(os.path.join(root, "bad.json"), "w", encoding="utf-8") as fh:
        json.dump("not a dict", fh)
    try:
        result = other_active_sessions("own", sessions_dir=root)
        sids = [r["sid"] for r in result]
        assert sids == ["other1"], "malformed entry must be skipped, got %r" % result
    finally:
        shutil.rmtree(root, ignore_errors=True)
    print("PASS test_new_format_malformed_session_entry_skipped")


def test_new_format_excludes_ended_sessions():
    """A status="ended" session's file deliberately persists for a while after a clean
    SessionEnd (fleet-session-hook.py 2026-07-24, so its recent-activity feed
    contribution survives instead of vanishing instantly) but must never be reported
    as an "other active session" here -- that would violate this module's documented
    presence-means-open contract and could make commit-provenance-guard.py /
    shared-checkout-guard.py wrongly treat a cleanly-finished session as still open."""
    root = write_sessions_dir({
        "other1": {"status": "working", "cwd": "C:/theirs", "lastAt": "t2"},
        "other2": {"status": "ended", "cwd": "C:/gone", "lastAt": "t3"},
    })
    try:
        result = other_active_sessions("own", sessions_dir=root)
        sids = [r["sid"] for r in result]
        assert sids == ["other1"], "ended session must be excluded, got %r" % result
    finally:
        shutil.rmtree(root, ignore_errors=True)
    print("PASS test_new_format_excludes_ended_sessions")


def test_new_format_empty_dir_is_trusted_not_treated_as_missing():
    """An EXISTING but empty sessions directory means 'genuinely no one else is here
    right now' -- a real, current answer, not something to second-guess by also
    checking the legacy file. (state_path= is intentionally NOT passed here -- if the
    empty-directory result were wrongly treated as 'try the old format instead', this
    test would still incidentally pass by falling through, which is exactly the bug
    this test guards against; asserting result == [] either way is the point.)"""
    root = tempfile.mkdtemp(prefix="liveness-empty-")
    try:
        result = other_active_sessions("own", sessions_dir=root)
        assert result == [], "empty existing directory must yield [], got %r" % result
    finally:
        shutil.rmtree(root, ignore_errors=True)
    print("PASS test_new_format_empty_dir_is_trusted_not_treated_as_missing")


# ===================================================================================
# PRECEDENCE (2026-07-24): an explicit override must win outright, with zero
# dependence on ambient machine/environment state -- this is what keeps every test
# above (and the two guards' own existing tests, which pass state_path= for their
# legacy fixtures) deterministic regardless of what does or doesn't exist on the real
# filesystem or in the real environment.
# ===================================================================================

def test_explicit_sessions_dir_ignores_env_state_path():
    root = write_sessions_dir({"other1": {"status": "working", "cwd": "C:/new", "lastAt": "t"}})
    old_path = write_state({"sessions": {"other2": {"status": "idle", "cwd": "C:/old", "lastAt": "t"}}})
    env_backup = os.environ.get("ORA_FLEET_STATE")
    os.environ["ORA_FLEET_STATE"] = old_path
    try:
        result = other_active_sessions("own", sessions_dir=root)
        sids = [r["sid"] for r in result]
        assert sids == ["other1"], (
            "explicit sessions_dir must be used, not the ORA_FLEET_STATE env var, got %r" % result)
    finally:
        if env_backup is None:
            os.environ.pop("ORA_FLEET_STATE", None)
        else:
            os.environ["ORA_FLEET_STATE"] = env_backup
        shutil.rmtree(root, ignore_errors=True)
        os.remove(old_path)
    print("PASS test_explicit_sessions_dir_ignores_env_state_path")


def test_explicit_state_path_skips_new_format_even_if_env_dir_exists():
    new_root = write_sessions_dir({"other1": {"status": "working", "cwd": "C:/new", "lastAt": "t"}})
    old_path = write_state({"sessions": {"other2": {"status": "idle", "cwd": "C:/old", "lastAt": "t"}}})
    env_backup = os.environ.get("ORA_FLEET_SESSIONS_DIR")
    os.environ["ORA_FLEET_SESSIONS_DIR"] = new_root
    try:
        result = other_active_sessions("own", state_path=old_path)
        sids = [r["sid"] for r in result]
        assert sids == ["other2"], (
            "explicit state_path must be used, not ORA_FLEET_SESSIONS_DIR, got %r" % result)
    finally:
        if env_backup is None:
            os.environ.pop("ORA_FLEET_SESSIONS_DIR", None)
        else:
            os.environ["ORA_FLEET_SESSIONS_DIR"] = env_backup
        shutil.rmtree(new_root, ignore_errors=True)
        os.remove(old_path)
    print("PASS test_explicit_state_path_skips_new_format_even_if_env_dir_exists")


if __name__ == "__main__":
    test_missing_file_fails_open()
    test_malformed_json_fails_open()
    test_wrong_shape_fails_open()
    test_excludes_own_sid()
    test_returns_other_sessions_with_fields()
    test_malformed_session_entry_skipped()
    test_new_format_missing_dir_fails_open()
    test_new_format_malformed_file_skipped()
    test_new_format_excludes_own_sid()
    test_new_format_returns_other_sessions_with_fields()
    test_new_format_prefers_embedded_sid_over_filename()
    test_new_format_malformed_session_entry_skipped()
    test_new_format_excludes_ended_sessions()
    test_new_format_empty_dir_is_trusted_not_treated_as_missing()
    test_explicit_sessions_dir_ignores_env_state_path()
    test_explicit_state_path_skips_new_format_even_if_env_dir_exists()
    print("ALL SESSION-LIVENESS TESTS PASS")
