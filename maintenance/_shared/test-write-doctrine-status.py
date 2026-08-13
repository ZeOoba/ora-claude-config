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
