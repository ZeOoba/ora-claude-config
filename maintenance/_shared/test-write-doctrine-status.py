#!/usr/bin/env python3
"""Tests for write-doctrine-status.py's memory_rc/memory_summary extension (2026-08-13).

Added when ora-cc-schematic-refresh was wired to give governor-drift-probe.py and
memory-integrity-probe.py a durable _state/ trace of their own, mirroring the doctrine
probe -- previously their results survived only inside the System Schematic artifact's
prose. Pure stdlib, hyphenated-module import idiom matches maintenance/_tests/test_hardening.py.
"""
import importlib.util
import json
import os
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
_MODULE_PATH = os.path.join(_HERE, "write-doctrine-status.py")


def _load():
    spec = importlib.util.spec_from_file_location("write_doctrine_status", _MODULE_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_build_snapshot_defaults_memory_probe_to_none():
    mod = _load()
    snap = mod.build_snapshot("pre-push", 0, "clean")
    assert snap["memory_probe"] == {"exit_code": None, "summary": None}, snap["memory_probe"]


def test_build_snapshot_carries_memory_probe_when_given():
    mod = _load()
    snap = mod.build_snapshot(
        "scheduled", 0, "clean",
        governor_rc=0, governor_summary="861 files scanned, consistent",
        memory_rc=1, memory_summary="2 orphan index links",
    )
    assert snap["memory_probe"] == {"exit_code": 1, "summary": "2 orphan index links"}
    assert snap["governor_probe"] == {"exit_code": 0, "summary": "861 files scanned, consistent"}


def test_write_status_round_trips_memory_fields():
    mod = _load()
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "doctrine-status.json")
        ok = mod.write_status(
            "scheduled", 0, "clean",
            governor_rc=0, governor_summary="ok",
            memory_rc=1, memory_summary="1 orphan",
            path=path,
        )
        assert ok is True
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        assert data["memory_probe"] == {"exit_code": 1, "summary": "1 orphan"}


def test_write_status_still_works_with_no_memory_args():
    """Pre-existing pre-push-gate call shape (no memory_rc/summary) must be unaffected."""
    mod = _load()
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "doctrine-status.json")
        ok = mod.write_status("pre-push", 1, "[MISSING] bare date", path=path)
        assert ok is True
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        assert data["memory_probe"] == {"exit_code": None, "summary": None}
        assert data["governor_probe"] == {"exit_code": None, "summary": None}
        assert data["doctrine_probe"] == {"exit_code": 1, "summary": "[MISSING] bare date"}


# ---- history array (added 2026-09-06) ----------------------------------------------

def _write_n(mod, path, n, rc_fn=lambda i: 0, source="pre-push"):
    for i in range(n):
        assert mod.write_status(source, rc_fn(i), "run %d" % i, path=path) is True
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def test_history_present_and_newest_first():
    mod = _load()
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "doctrine-status.json")
        data = _write_n(mod, path, 3, rc_fn=lambda i: i)  # rcs 0,1,2
        assert "history" in data
        assert [h["doctrine_rc"] for h in data["history"]] == [2, 1, 0], data["history"]
        assert data["history"][0]["last_check"] == data["last_check"]
        # governor/memory not run by this caller -> None in the record too
        assert data["history"][0]["governor_rc"] is None
        assert data["history"][0]["memory_rc"] is None
        assert data["history"][0]["guard_orphan_count"] == 0


def test_history_is_capped_at_history_max():
    mod = _load()
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "doctrine-status.json")
        data = _write_n(mod, path, mod.HISTORY_MAX + 7)
        assert len(data["history"]) == mod.HISTORY_MAX
        # oldest records fall off the tail, newest stays on top
        assert data["history"][0]["doctrine_summary"] == "run %d" % (mod.HISTORY_MAX + 6)


def test_legacy_file_without_history_is_seeded_from_its_snapshot():
    """Upgrade path: the pre-2026-09-06 file (top-level only) must not lose its last result."""
    mod = _load()
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "doctrine-status.json")
        legacy = mod.build_snapshot("pre-push", 1, "[MISSING] bare date")  # no history key
        with open(path, "w", encoding="utf-8") as f:
            json.dump(legacy, f)
        assert mod.write_status("scheduled", 0, "clean", governor_rc=0, governor_summary="ok", path=path)
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        assert len(data["history"]) == 2
        assert data["history"][1] == {
            "last_check": legacy["last_check"], "source": "pre-push",
            "doctrine_rc": 1, "governor_rc": None, "memory_rc": None,
            "doctrine_summary": "[MISSING] bare date", "governor_summary": None,
            "memory_summary": None, "guard_orphan_count": 0,
        }


def test_corrupt_prior_file_does_not_break_the_write():
    mod = _load()
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "doctrine-status.json")
        with open(path, "w", encoding="utf-8") as f:
            f.write("{not json")
        assert mod.write_status("pre-push", 0, "clean", path=path) is True
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        assert len(data["history"]) == 1


def test_history_record_truncates_long_summary():
    mod = _load()
    snap = mod.build_snapshot("pre-push", 1, "x" * 500)
    rec = mod._history_record(snap)
    assert len(rec["doctrine_summary"]) == mod._SUMMARY_MAX_CHARS
    assert rec["doctrine_summary"].endswith("...")
    # the top-level snapshot keeps the full line
    assert len(snap["doctrine_probe"]["summary"]) == 500


def test_summarize_history_counts_window_pass_fail():
    from datetime import datetime, timedelta
    mod = _load()
    now = datetime(2026, 9, 6, 12, 0, 0)
    def rec(days_ago, d=None, g=None, m=None, src="pre-push"):
        snap = mod.build_snapshot(src, d, "d", governor_rc=g, governor_summary="g",
                                  memory_rc=m, memory_summary="m",
                                  now=now - timedelta(days=days_ago))
        return mod._history_record(snap)
    data = {"history": [
        rec(1, d=0),                 # in window, doctrine pass
        rec(3, d=1),                 # in window, doctrine fail
        rec(5, d=0, g=0, m=2, src="scheduled"),  # in window, gov pass, mem fail
        rec(45, d=1, g=1),           # OUT of 30-day window, must not count
        {"last_check": "garbage", "doctrine_rc": 1},  # unparseable -> skipped
    ]}
    s = mod.summarize_history(data, since_days=30, now=now)
    assert s["checks_in_window"] == 3, s
    assert s["unparsed"] == 1
    assert s["probes"]["doctrine"] == {"ran": 3, "pass": 2, "fail": 1}, s["probes"]
    assert s["probes"]["governor"] == {"ran": 1, "pass": 1, "fail": 0}, s["probes"]
    assert s["probes"]["memory"] == {"ran": 1, "pass": 0, "fail": 1}, s["probes"]
    assert sorted(f["probe"] for f in s["fails"]) == ["doctrine", "memory"]


def test_summarize_history_falls_back_to_legacy_top_level():
    mod = _load()
    legacy = mod.build_snapshot("pre-push", 1, "[MISSING] bare date")  # no history key
    s = mod.summarize_history(legacy, since_days=30)
    assert s["records_total"] == 1
    assert s["probes"]["doctrine"] == {"ran": 1, "pass": 0, "fail": 1}


if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    failed = 0
    for t in tests:
        try:
            t()
            print("PASS", t.__name__)
        except AssertionError as e:
            failed += 1
            print("FAIL", t.__name__, "-", e)
        except Exception as e:
            failed += 1
            print("ERROR", t.__name__, "-", e)
    print("\n%d/%d passed" % (len(tests) - failed, len(tests)))
    sys.exit(1 if failed else 0)
