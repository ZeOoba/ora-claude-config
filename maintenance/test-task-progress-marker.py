#!/usr/bin/env python3
"""Tests for task-progress-marker.py -- qodo-code-review findings on PR #143:

  - "Marker path escapes state" (High/Security): --task-id was interpolated directly
    into a filesystem path with no validation, letting a crafted id write/delete a file
    outside the marker directory.
  - "Cross-fleet markers collide" (High/Correctness): markers were keyed by task_id
    alone, even though the same id can legitimately exist in both fleets.

Run: python test-task-progress-marker.py
"""
import importlib.util
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "task_progress_marker", os.path.join(HERE, "task-progress-marker.py"))
tpm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tpm)


def _fresh_marker_dir():
    d = tempfile.mkdtemp(prefix="tpm-test-")
    tpm.MARKER_DIR = os.path.join(d, "_state", "task-progress")
    return d


def test_path_traversal_rejected_unit():
    _fresh_marker_dir()
    for bad_id in ("../../../etc/passwd", "..\\..\\evil", "/etc/passwd",
                   "C:\\Users\\Owner\\.claude\\hooks\\some-file", "a/b", "a\\b", ".hidden"):
        try:
            tpm._marker_path("cc", bad_id)
            raise AssertionError(f"expected InvalidTaskId for task_id={bad_id!r}")
        except tpm.InvalidTaskId:
            pass
    print("  PASS test_path_traversal_rejected_unit")


def test_invalid_fleet_rejected_unit():
    _fresh_marker_dir()
    for bad_fleet in ("../escape", "CC", "cc/lams", "", "cc.."):
        try:
            tpm._marker_path(bad_fleet, "ora-am-brief")
            raise AssertionError(f"expected InvalidTaskId for fleet={bad_fleet!r}")
        except tpm.InvalidTaskId:
            pass
    print("  PASS test_invalid_fleet_rejected_unit")


def test_valid_ids_still_resolve_inside_marker_dir_unit():
    _fresh_marker_dir()
    for fleet in ("cc", "lams"):
        for task_id in ("ora-am-brief", "ora-routine-pause-resume-08-21", "task.v2"):
            p = tpm._marker_path(fleet, task_id)
            real_dir = os.path.realpath(tpm.MARKER_DIR)
            assert os.path.realpath(p).startswith(real_dir + os.sep), \
                f"resolved path escaped MARKER_DIR: {p!r}"
    print("  PASS test_valid_ids_still_resolve_inside_marker_dir_unit")


def test_write_load_clear_roundtrip_unit():
    _fresh_marker_dir()
    data = tpm.write_marker("cc", "ora-am-brief", 2, 5, note="halfway")
    assert data["fleet"] == "cc" and data["taskId"] == "ora-am-brief"
    loaded = tpm.load_marker("cc", "ora-am-brief")
    assert loaded is not None and loaded["step"] == 2 and loaded["totalSteps"] == 5
    assert tpm.clear_marker("cc", "ora-am-brief") is True
    assert tpm.load_marker("cc", "ora-am-brief") is None
    assert tpm.clear_marker("cc", "ora-am-brief") is False  # already gone
    print("  PASS test_write_load_clear_roundtrip_unit")


def test_cross_fleet_markers_do_not_collide_unit():
    """The real bug: the same task id exists in both fleets (a documented, supported
    case per fleet-status.py's find_cross_fleet_duplicates) with DIFFERENT progress."""
    _fresh_marker_dir()
    tpm.write_marker("cc", "shared-task-id", step=1, of=10, note="cc side, just started")
    tpm.write_marker("lams", "shared-task-id", step=9, of=10, note="lams side, nearly done")

    cc_marker = tpm.load_marker("cc", "shared-task-id")
    lams_marker = tpm.load_marker("lams", "shared-task-id")
    assert cc_marker["step"] == 1, f"cc marker corrupted by cross-fleet collision: {cc_marker}"
    assert lams_marker["step"] == 9, f"lams marker corrupted by cross-fleet collision: {lams_marker}"

    tpm.clear_marker("cc", "shared-task-id")
    assert tpm.load_marker("cc", "shared-task-id") is None
    # clearing the cc-fleet marker must NOT touch the lams-fleet marker of the same id
    assert tpm.load_marker("lams", "shared-task-id")["step"] == 9, \
        "clearing one fleet's marker deleted the other fleet's same-id marker"
    print("  PASS test_cross_fleet_markers_do_not_collide_unit")


def test_invalid_task_id_from_registry_treated_as_no_marker_unit():
    """find_stalled() sources task_id from the live scheduled-task registry, not a
    trusted CLI arg -- a malformed/missing id must degrade to 'no marker', not crash
    the whole stalled-marker sweep."""
    _fresh_marker_dir()
    assert tpm.load_marker("cc", "") is None
    assert tpm.load_marker("cc", None) is None
    assert tpm.load_marker("cc", "../escape") is None
    print("  PASS test_invalid_task_id_from_registry_treated_as_no_marker_unit")


def main():
    test_path_traversal_rejected_unit()
    test_invalid_fleet_rejected_unit()
    test_valid_ids_still_resolve_inside_marker_dir_unit()
    test_write_load_clear_roundtrip_unit()
    test_cross_fleet_markers_do_not_collide_unit()
    test_invalid_task_id_from_registry_treated_as_no_marker_unit()
    print("ALL TASK-PROGRESS-MARKER TESTS PASS")


if __name__ == "__main__":
    main()
