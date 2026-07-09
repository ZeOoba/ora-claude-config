#!/usr/bin/env python3
"""Tests for the layer-2 status-file writer (_shared/write-doctrine-status.py) and its
wiring into hooks/git-prepush-doctrine-gate.py (audit Phase 3, 2026-07-08).

Run: python test_git_prepush_doctrine_gate.py     (from this directory)
Pure stdlib. ASCII-only output (Windows cp1252 console). Never writes to the real
maintenance/_state/doctrine-status.json or the real memory/event_log.md -- every test
uses a tempfile path or the module-level test seams (STATUS_PATH_OVERRIDE / EVENT_LOG_OVERRIDE).

Covers:
  - write_status(): valid parseable JSON with the expected keys, to a temp path.
  - write_status(): clean OVERWRITE on a second call (snapshot, not append).
  - write_status(): never raises on a bogus/unwritable path -> returns False, no file.
  - write_status(): governor_* and guard_orphans pass-through shapes.
  - summarize_probe_output(): pure summary derivation (clean / warn-count / MISSING).
  - decide(): pre-existing pure decision logic UNCHANGED by the edit.
  - end-to-end gate run: real probe run leaves a fresh, valid status file (via the
    STATUS_PATH_OVERRIDE seam), consistent with the gate's own exit code, no override log.
  - override logging: the event_log append path still fires, targeting the EVENT_LOG_OVERRIDE
    seam (never the canonical event_log.md), when log_override_use() is invoked.
"""
import importlib.util
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
MAINT = os.path.dirname(HERE)
CLAUDE_DIR = os.path.dirname(MAINT)
GATE_PATH = os.path.join(CLAUDE_DIR, "hooks", "git-prepush-doctrine-gate.py")
WRITER_PATH = os.path.join(MAINT, "_shared", "write-doctrine-status.py")
REAL_CLAUDE_MD = os.path.join(CLAUDE_DIR, "CLAUDE.md")

EXPECTED_KEYS = {"last_check", "source", "doctrine_probe", "governor_probe", "guard_orphans"}


def _load(path, modname):
    """Load a hyphenated-or-not sibling script by path (test_hardening.py idiom)."""
    spec = importlib.util.spec_from_file_location(modname, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


writer = _load(WRITER_PATH, "write_doctrine_status")
gate = _load(GATE_PATH, "git_prepush_doctrine_gate")


# --------------------------------------------------------------------------- #
# write_status() -- shape, keys, overwrite, best-effort failure
# --------------------------------------------------------------------------- #
def test_write_status_valid_json_and_keys():
    """write_status writes parseable JSON with exactly the documented keys."""
    fd, path = tempfile.mkstemp(suffix="_doctrine-status.json")
    os.close(fd)
    os.remove(path)  # let write_status create it fresh
    try:
        ok = writer.write_status(source="pre-push", doctrine_rc=0, doctrine_summary="clean",
                                 path=path)
        assert ok is True, "write_status should return True on success"
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        assert set(data.keys()) == EXPECTED_KEYS, "unexpected top-level keys: %s" % data.keys()
        assert data["source"] == "pre-push"
        assert data["doctrine_probe"] == {"exit_code": 0, "summary": "clean"}
        # pre-push never runs the governor probe -> None/None passthrough.
        assert data["governor_probe"] == {"exit_code": None, "summary": None}
        assert data["guard_orphans"] == []
        assert isinstance(data["last_check"], str) and "T" in data["last_check"], (
            "last_check should be an ISO8601 string, got %r" % data["last_check"])
        # ISO8601 must round-trip through fromisoformat.
        from datetime import datetime
        datetime.fromisoformat(data["last_check"])
        print("  PASS test_write_status_valid_json_and_keys")
    finally:
        if os.path.exists(path):
            os.remove(path)


def test_write_status_overwrites_not_appends():
    """A second write_status to the same path REPLACES the file (snapshot, not append)."""
    fd, path = tempfile.mkstemp(suffix="_doctrine-status.json")
    os.close(fd)
    try:
        writer.write_status(source="pre-push", doctrine_rc=1,
                            doctrine_summary="[MISSING] /old-thing", path=path)
        writer.write_status(source="scheduled", doctrine_rc=0, doctrine_summary="clean",
                            governor_rc=0, governor_summary="clean", path=path)
        with open(path, encoding="utf-8") as f:
            raw = f.read()
        data = json.loads(raw)  # must be a single dict, not concatenated JSON
        assert data["source"] == "scheduled", "second write did not overwrite source"
        assert data["doctrine_probe"]["exit_code"] == 0, "stale doctrine_rc survived overwrite"
        assert "old-thing" not in raw, "old summary text survived the overwrite (appended?)"
        assert data["governor_probe"] == {"exit_code": 0, "summary": "clean"}
        print("  PASS test_write_status_overwrites_not_appends")
    finally:
        if os.path.exists(path):
            os.remove(path)


def test_write_status_bad_path_returns_false_no_raise():
    """A path inside a directory that does not exist -> best-effort swallow: returns
    False, raises nothing, and creates no file."""
    d = tempfile.mkdtemp()
    bogus = os.path.join(d, "no-such-subdir", "doctrine-status.json")
    try:
        ok = writer.write_status(source="pre-push", doctrine_rc=0, doctrine_summary="clean",
                                 path=bogus)
        assert ok is False, "write to a nonexistent dir should return False, got %r" % ok
        assert not os.path.exists(bogus), "no file should have been created at the bogus path"
        print("  PASS test_write_status_bad_path_returns_false_no_raise")
    finally:
        # cleanup: only the temp root exists
        try:
            os.rmdir(d)
        except OSError:
            pass


def test_write_status_governor_and_guard_passthrough():
    """The future scheduled-task shape: governor_* populated + guard_orphans list
    pass through verbatim; None guard_orphans normalizes to []."""
    fd, path = tempfile.mkstemp(suffix="_doctrine-status.json")
    os.close(fd)
    try:
        orphans = ["[WARN] guard governor-drift-probe not run in 8d",
                   "[WARN] guard eos-telemetry stale"]
        writer.write_status(source="scheduled", doctrine_rc=0, doctrine_summary="clean",
                            governor_rc=1, governor_summary="[GOVERNOR DRIFT] DSCR 1.20",
                            guard_orphans=orphans, path=path)
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        assert data["source"] == "scheduled"
        assert data["governor_probe"] == {"exit_code": 1,
                                          "summary": "[GOVERNOR DRIFT] DSCR 1.20"}
        assert data["guard_orphans"] == orphans, "guard_orphans did not pass through verbatim"
        # None -> []
        writer.write_status(source="pre-push", doctrine_rc=0, doctrine_summary="clean",
                            guard_orphans=None, path=path)
        with open(path, encoding="utf-8") as f:
            data2 = json.load(f)
        assert data2["guard_orphans"] == [], "None guard_orphans should normalize to []"
        print("  PASS test_write_status_governor_and_guard_passthrough")
    finally:
        if os.path.exists(path):
            os.remove(path)


# --------------------------------------------------------------------------- #
# summarize_probe_output() -- pure summary derivation
# --------------------------------------------------------------------------- #
def test_summarize_probe_output():
    """rc==0 clean; rc==0 with [WARN]s -> count; rc!=0 -> last [MISSING] line; rc!=0
    with no [MISSING] -> generic."""
    assert gate.summarize_probe_output(0, "[OK] all good\n") == "clean"
    s = gate.summarize_probe_output(0, "[OK] x\n[WARN] a\n[WARN] b\n")
    assert s == "clean, 2 warning(s)", "warn-count summary wrong: %r" % s
    s = gate.summarize_probe_output(1, "[MISSING] /first\nnoise\n[MISSING] /last\n")
    assert s == "[MISSING] /last", "should pick the LAST [MISSING] line: %r" % s
    s = gate.summarize_probe_output(1, "some drift with no missing token\n")
    assert s == "drift (exit 1)", "generic drift summary wrong: %r" % s
    print("  PASS test_summarize_probe_output")


# --------------------------------------------------------------------------- #
# decide() -- pre-existing pure logic must be UNCHANGED by this edit
# --------------------------------------------------------------------------- #
def test_decide_logic_unchanged():
    """Regression guard: the decision table the audit relies on is intact."""
    assert gate.decide(0, False) == (0, False), "clean -> allow, no log"
    assert gate.decide(0, True) == (0, False), "clean + stray override -> allow, no log"
    assert gate.decide(1, True) == (0, True), "drift + override -> allow + LOG"
    assert gate.decide(1, False) == (1, False), "drift, no override -> BLOCK"
    print("  PASS test_decide_logic_unchanged")


# --------------------------------------------------------------------------- #
# end-to-end gate run -- real probe, status file via the seam, no override log
# --------------------------------------------------------------------------- #
def test_gate_end_to_end_writes_status():
    """gate.main() runs the REAL doctrine probe against the live CLAUDE.md and leaves a
    fresh, valid status file at STATUS_PATH_OVERRIDE, consistent with its own exit code,
    without logging any override (no sentinel present).

    Does NOT hard-assert exit 0: a parallel agent may hold CLAUDE.md mid-edit, so the
    probe could transiently report drift. The invariant tested is CONSISTENCY between the
    gate's exit code and the status file it leaves + validity of that file."""
    tmpdir = tempfile.mkdtemp()
    status_path = os.path.join(tmpdir, "doctrine-status.json")
    event_log = os.path.join(tmpdir, "event_log.md")
    open(event_log, "w", encoding="utf-8").close()  # seed so the appender could stat it
    prev_status, prev_log = gate.STATUS_PATH_OVERRIDE, gate.EVENT_LOG_OVERRIDE
    gate.STATUS_PATH_OVERRIDE = status_path
    gate.EVENT_LOG_OVERRIDE = event_log  # belt-and-suspenders; no sentinel -> unused anyway
    try:
        rc = gate.main()
        assert os.path.isfile(status_path), "gate.main() left no status file"
        with open(status_path, encoding="utf-8") as f:
            data = json.load(f)
        assert set(data.keys()) == EXPECTED_KEYS, "status file keys: %s" % data.keys()
        assert data["source"] == "pre-push"
        assert data["governor_probe"] == {"exit_code": None, "summary": None}, (
            "the pre-push gate must never populate governor_probe")
        assert isinstance(data["guard_orphans"], list)
        d_rc = data["doctrine_probe"]["exit_code"]
        assert isinstance(d_rc, int)
        # Consistency: gate exit code tracks the probe result (no override in play).
        if rc == 0:
            assert d_rc == 0, "gate returned 0 but status doctrine exit_code=%r" % d_rc
            assert data["doctrine_probe"]["summary"].startswith("clean"), (
                "clean run summary should start 'clean', got %r"
                % data["doctrine_probe"]["summary"])
        else:
            assert d_rc != 0, "gate returned %r but status doctrine exit_code=0" % rc
        # No override sentinel -> nothing appended to the (seam) event log.
        with open(event_log, encoding="utf-8") as f:
            log_txt = f.read()
        assert "Pre-push proceeded DESPITE doctrine drift" not in log_txt, (
            "no override should have been logged")
        print("  PASS test_gate_end_to_end_writes_status (gate rc=%d, doctrine exit_code=%d)"
              % (rc, d_rc))
    finally:
        gate.STATUS_PATH_OVERRIDE, gate.EVENT_LOG_OVERRIDE = prev_status, prev_log
        for p in (status_path, event_log):
            if os.path.exists(p):
                os.remove(p)
        try:
            os.rmdir(tmpdir)
        except OSError:
            pass


# --------------------------------------------------------------------------- #
# override logging -- still fires, targets the seam, never the canonical log
# --------------------------------------------------------------------------- #
def test_override_logging_uses_seam():
    """log_override_use() appends the override record through the real append-event-log.py
    to the EVENT_LOG_OVERRIDE target -- proving the pre-existing override-audit path is
    intact and (via the seam) never touches the canonical event_log.md."""
    fd, event_log = tempfile.mkstemp(suffix="_event_log.md")
    os.close(fd)  # exists + empty so the appender can stat/insert
    prev = gate.EVENT_LOG_OVERRIDE
    gate.EVENT_LOG_OVERRIDE = event_log
    try:
        gate.log_override_use()
        with open(event_log, encoding="utf-8") as f:
            txt = f.read()
        assert "Pre-push proceeded DESPITE doctrine drift" in txt, (
            "override record not appended to the seam log:\n%s" % txt)
        assert txt.lstrip().startswith("## "), "override entry must be a dated '## ' header"
        print("  PASS test_override_logging_uses_seam")
    finally:
        gate.EVENT_LOG_OVERRIDE = prev
        if os.path.exists(event_log):
            os.remove(event_log)


def test_gate_backcompat_int_probe_no_status_write():
    """main() stays compatible with the legacy bare-int run_doctrine_probe contract
    (the pre-existing hooks/tests/test-git-prepush-doctrine-gate.py stubs it as
    `lambda: 1`) AND a stubbed (non-real) probe run must NOT write a status snapshot --
    so a unit test never clobbers the real _state snapshot with a fake drift result.
    Fully isolated: temp OVERRIDE_DIR + event_log + status seams."""
    tmpdir = tempfile.mkdtemp()
    status_path = os.path.join(tmpdir, "doctrine-status.json")  # must stay ABSENT
    event_log = os.path.join(tmpdir, "event_log.md")
    with open(event_log, "w", encoding="utf-8") as f:
        f.write("# test\n\n## 2000-01-01 - seed\n\n- seed\n")
    override_dir = os.path.join(tmpdir, "overrides")
    os.makedirs(override_dir)
    prev = (gate.run_doctrine_probe, gate.OVERRIDE_DIR, gate.EVENT_LOG_OVERRIDE,
            gate.STATUS_PATH_OVERRIDE)
    gate.run_doctrine_probe = lambda: 1  # legacy bare-int stub -> force drift
    gate.OVERRIDE_DIR = override_dir
    gate.EVENT_LOG_OVERRIDE = event_log
    gate.STATUS_PATH_OVERRIDE = status_path  # a leaked write would land here (it must not)
    try:
        rc = gate.main()  # drift + no override -> BLOCK
        assert rc == 1, "legacy int stub, drift, no override -> exit 1, got %r" % rc
        assert not os.path.exists(status_path), (
            "a stubbed (non-real) probe run must NOT write a status snapshot")
        with open(os.path.join(override_dir, gate.OVERRIDE_NAME), "w") as f:
            f.write("x")  # fresh sentinel
        rc2 = gate.main()  # drift + fresh override -> allow + LOG
        assert rc2 == 0, "legacy int stub, drift, fresh override -> exit 0, got %r" % rc2
        assert not os.path.exists(status_path), (
            "override path with a stubbed probe must still not write a status snapshot")
        logged = open(event_log, encoding="utf-8").read()
        assert "Pre-push proceeded DESPITE doctrine drift" in logged, (
            "override use should still be logged via the seam")
        print("  PASS test_gate_backcompat_int_probe_no_status_write")
    finally:
        (gate.run_doctrine_probe, gate.OVERRIDE_DIR, gate.EVENT_LOG_OVERRIDE,
         gate.STATUS_PATH_OVERRIDE) = prev
        shutil.rmtree(tmpdir, ignore_errors=True)


TESTS = [
    test_write_status_valid_json_and_keys,
    test_write_status_overwrites_not_appends,
    test_write_status_bad_path_returns_false_no_raise,
    test_write_status_governor_and_guard_passthrough,
    test_summarize_probe_output,
    test_decide_logic_unchanged,
    test_gate_end_to_end_writes_status,
    test_override_logging_uses_seam,
    test_gate_backcompat_int_probe_no_status_write,
]


def main():
    assert os.path.isfile(REAL_CLAUDE_MD), "real CLAUDE.md not found: %s" % REAL_CLAUDE_MD
    assert os.path.isfile(GATE_PATH), "gate script not found: %s" % GATE_PATH
    assert os.path.isfile(WRITER_PATH), "status-writer module not found: %s" % WRITER_PATH
    failures = []
    for t in TESTS:
        try:
            t()
        except Exception as e:  # noqa: BLE001 - test runner surfaces every failure
            import traceback
            print("  FAIL %s: %s" % (t.__name__, e))
            traceback.print_exc()
            failures.append(t.__name__)
    print()
    if failures:
        print("FAILED (%d): %s" % (len(failures), ", ".join(failures)))
        return 1
    print("ALL GIT-PREPUSH-DOCTRINE-GATE TESTS PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
