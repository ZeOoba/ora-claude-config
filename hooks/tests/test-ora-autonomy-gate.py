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


def bash_payload(command):
    return {"tool_name": "Bash", "tool_input": {"command": command}}


def test_blocks_legacy_markers():
    for marker_path in [
        "C:/Users/Owner/website-canonical/src/index.html",
        "C:/Users/Owner/oxford-site/foo.html",
    ]:
        rc, out, err = run_hook(write_payload(marker_path))
        assert rc == 2, "%s expected block (exit 2), got %s (%s)" % (marker_path, rc, err)
    print("PASS test_blocks_legacy_markers")


def test_domain_form_markers_do_not_block_via_this_hook():
    """Gate 2's matching is whole-command/whole-path bare substring -- domain-form
    aliases (oxfordra.net, oxfordra_net) are deliberately NOT part of this hook's
    marker set, unlike confidentiality-guard.py's narrower path-only egress
    classifier. An earlier version of this fix (2026-07-12) unioned them in and an
    independent code review caught, empirically, that it caused false-positive hard
    blocks on routine operations (see the test_allows_* cases below) -- reverted."""
    for marker_path in [
        "C:/some/other/tree/oxfordra.net/page.html",
        "C:/some/other/tree/oxfordra_net/page.html",
    ]:
        rc, out, err = run_hook(write_payload(marker_path))
        assert rc == 0, (
            "%s must NOT block via ora-autonomy-gate (domain aliases are "
            "confidentiality-guard.py's concern, not Gate 2's), got %s (%s)"
            % (marker_path, rc, err)
        )
    print("PASS test_domain_form_markers_do_not_block_via_this_hook")


def test_allows_internal_email_with_redirect():
    """Regression (2026-07-12 code review finding): an ordinary internal email
    address followed by an output redirect must not trip Gate 2b."""
    rc, out, err = run_hook(bash_payload("echo notify ggoldberg@oxfordra.net > note.txt"))
    assert rc == 0, "internal email + redirect must not block, got %s (%s)" % (rc, err)
    print("PASS test_allows_internal_email_with_redirect")


def test_allows_curl_fetch_of_site():
    """A read/fetch of the live site (no write indicator applies to the site itself)
    must not block."""
    rc, out, err = run_hook(bash_payload("curl -s https://oxfordra.net > page.html"))
    assert rc == 0, "fetching the live site to a local file must not block, got %s (%s)" % (rc, err)
    print("PASS test_allows_curl_fetch_of_site")


def test_allows_internal_send_with_redirect():
    """The pre-authorized internal fleet send (invariant 1 carve-out) must not be
    blocked just because its own log redirect happens to contain the domain."""
    cmd = ('powershell -File send-via-outlook.ps1 -To ggoldberg@oxfordra.net '
           '-Subject "hi" -Body "hi" > send.log')
    rc, out, err = run_hook(bash_payload(cmd))
    assert rc == 0, "pre-authorized internal send + log redirect must not block, got %s (%s)" % (rc, err)
    print("PASS test_allows_internal_send_with_redirect")


def test_allows_file_mentioning_domain_in_name():
    rc, out, err = run_hook(write_payload("C:/Users/Owner/notes/re-oxfordra.net-seo.md"))
    assert rc == 0, "a file merely mentioning the domain in its name must not block, got %s (%s)" % (rc, err)
    print("PASS test_allows_file_mentioning_domain_in_name")


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
    test_domain_form_markers_do_not_block_via_this_hook()
    test_allows_internal_email_with_redirect()
    test_allows_curl_fetch_of_site()
    test_allows_internal_send_with_redirect()
    test_allows_file_mentioning_domain_in_name()
    test_non_site_path_allows()
    test_malformed_stdin_fails_open()
    print("ALL AUTONOMY-GATE TESTS PASS")
