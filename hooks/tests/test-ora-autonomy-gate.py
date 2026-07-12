"""Tests for ora-autonomy-gate.py PreToolUse hook (Gate 2 -- website writes).

Run: python test-ora-autonomy-gate.py
Stdlib only. ASCII-only. Self-contained.

No existing test file covered this hook before 2026-07-12 (verified absent).
Written alongside the site-marker de-duplication fix (hooks/lib/site_markers.py)
to lock in both the pre-existing legacy-marker behavior and the newly-closed
domain-form-marker gap.
"""

import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOK = os.path.join(HERE, "ora-autonomy-gate.py")


def run_hook(payload_dict):
    proc = subprocess.run(
        [sys.executable, HOOK],
        input=json.dumps(payload_dict),
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stdout, proc.stderr


def write_payload(file_path):
    return {"tool_name": "Write", "tool_input": {"file_path": file_path, "content": "x"}}


def test_blocks_legacy_markers():
    for marker_path in [
        "C:/Users/Owner/website-canonical/src/index.html",
        "C:/Users/Owner/oxford-site/foo.html",
    ]:
        rc, out, err = run_hook(write_payload(marker_path))
        assert rc == 2, "%s expected block (exit 2), got %s (%s)" % (marker_path, rc, err)
    print("PASS test_blocks_legacy_markers")


def test_blocks_domain_form_markers():
    """confidentiality-guard.py already recognized these domain-form aliases before
    this fix; ora-autonomy-gate.py did not -- a live drift between the two guards
    where a domain-named path would be leak-scanned but not human-gated. Proves the
    shared hooks/lib/site_markers.py constant closes it."""
    for marker_path in [
        "C:/some/other/tree/oxfordra.net/page.html",
        "C:/some/other/tree/oxfordra_net/page.html",
    ]:
        rc, out, err = run_hook(write_payload(marker_path))
        assert rc == 2, "%s expected block (exit 2), got %s (%s)" % (marker_path, rc, err)
    print("PASS test_blocks_domain_form_markers")


def test_non_site_path_allows():
    rc, out, err = run_hook(write_payload("C:/proj/src/index.html"))
    assert rc == 0, "expected exit 0, got %s (%s)" % (rc, err)
    print("PASS test_non_site_path_allows")


def test_malformed_stdin_fails_open():
    proc = subprocess.run([sys.executable, HOOK], input="not json", capture_output=True, text=True)
    assert proc.returncode == 0, "malformed stdin must exit 0, got %s" % proc.returncode
    print("PASS test_malformed_stdin_fails_open")


if __name__ == "__main__":
    test_blocks_legacy_markers()
    test_blocks_domain_form_markers()
    test_non_site_path_allows()
    test_malformed_stdin_fails_open()
    print("ALL AUTONOMY-GATE TESTS PASS")
