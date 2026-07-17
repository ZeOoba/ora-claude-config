"""Tests for eos-claude-md-guard.py PreToolUse hook (Edit|Write|MultiEdit).

Run: python test-eos-claude-md-guard.py
Stdlib only. ASCII-only source (payloads below may contain literal non-ASCII
test data). Self-contained (creates its own temp CLAUDE.md fixtures).
"""
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # hooks/ (test in hooks/tests/)
HOOK = os.path.join(HERE, "eos-claude-md-guard.py")


def _load_hook_module():
    """Import the hook script as a module (mirrors its own _load_probe()
    trick) so unit tests can call its internal helpers directly, without a
    subprocess -- needed because the mis-decode this test guards against is
    triggered by the OS/parent-process's inherited codepage, which a
    subprocess spawned from the test runner cannot be made to reproduce
    reliably (verified empirically: neither stripping PYTHONUTF8/
    PYTHONIOENCODING/LANG nor forcibly setting PYTHONIOENCODING=cp1252 in
    the child env changed this machine's actual stdin decode behavior, even
    though sys.stdin.encoding reports 'cp1252' in both cases). The live
    2026-07-17 incident (bare date silently landed in CLAUDE.md) confirmed
    the real bug directly: a harness-spawned hook process logged
    sys.stdin.encoding == 'cp1252' AND decoded an em-dash old_string into
    3-character mojibake ('\\xe2\\x80\\x94' misread a byte at a time),
    making current_text.count(old) == 0 and simulate_edit() return None --
    fail-open, so the violating edit landed. Testing the decode helper
    directly, independent of subprocess/OS encoding quirks, is the only
    reliable way to pin this down."""
    spec = importlib.util.spec_from_file_location("eos_claude_md_guard", HOOK)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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


def test_read_stdin_text_decodes_utf8_independent_of_locale():
    """Regression for the 2026-07-17 incident: a live harness-spawned hook
    process had sys.stdin.encoding == 'cp1252' (Windows ANSI codepage, not
    UTF-8), so any non-ASCII byte in the JSON payload -- CLAUDE.md's own
    em-dashes/arrows/etc are in nearly every real old_string -- got corrupted
    before json.loads ever saw it, silently defeating the guard. The module
    must expose a stdin-reader that decodes explicitly as UTF-8 off the raw
    buffer, not one that trusts sys.stdin's own (locale-dependent) text-mode
    encoding."""
    module = _load_hook_module()
    assert hasattr(module, "_read_stdin_text"), (
        "eos-claude-md-guard.py must expose _read_stdin_text() -- an explicit "
        "UTF-8 decode off sys.stdin.buffer, not sys.stdin.read() (whose "
        "encoding follows the parent process's inherited codepage and was "
        "observed as cp1252, not UTF-8, in the live 2026-07-17 incident)")

    # ensure_ascii=False is required: the default True would \\u-escape the
    # em-dash into pure ASCII before .encode(), so the payload bytes would
    # never actually contain a multi-byte UTF-8 sequence and this test would
    # pass even against the unfixed sys.stdin.read() -- caught by adversarial
    # review, which showed the test doesn't discriminate without this flag.
    payload = json.dumps({"old_string": "em dash — test"}, ensure_ascii=False)
    utf8_bytes = payload.encode("utf-8")

    class _FakeStdin:
        def __init__(self, data):
            self.buffer = io.BytesIO(data)

        def read(self):
            # Emulates the exact live failure mode: text-mode .read() using
            # a non-UTF-8 codepage silently corrupts multi-byte characters
            # instead of raising -- this must NOT be what the fix relies on.
            return self.buffer.getvalue().decode("cp1252")

    real_stdin = sys.stdin
    sys.stdin = _FakeStdin(utf8_bytes)
    try:
        text = module._read_stdin_text()
    finally:
        sys.stdin = real_stdin

    decoded = json.loads(text)
    assert decoded["old_string"] == "em dash — test", (
        "expected the em-dash to round-trip correctly via explicit UTF-8 "
        "decoding, got %r (this is exactly the mojibake shape observed live: "
        "a single U+2014 corrupted into 3 separate characters)" % decoded["old_string"])
    print("PASS test_read_stdin_text_decodes_utf8_independent_of_locale")


def test_edit_with_nonascii_context_producing_bare_date_denies():
    """End-to-end: an Edit whose old_string contains a non-ASCII character
    (an em-dash, as ubiquitous in real CLAUDE.md prose) must still be denied
    when it introduces a bare date. Feeds raw UTF-8 bytes on stdin (no
    text=True) so the payload's encoding on the wire is unambiguous."""
    fixture = "## Engineering OS\nsome doctrine text\nold line — with dash\n"
    path = make_claude_md(fixture)
    try:
        payload = {
            "tool_name": "Edit",
            "tool_input": {
                "file_path": path,
                "old_string": "old line — with dash",
                "new_string": "old line — with dash (ratified 2026-07-17)",
            },
        }
        env = dict(os.environ)
        env["EOS_CLAUDE_MD"] = path
        proc = subprocess.run(
            [sys.executable, HOOK],
            input=json.dumps(payload).encode("utf-8"),
            capture_output=True, env=env,
        )
        out = proc.stdout.decode("utf-8", "replace")
        assert proc.returncode == 0, "hook itself always exits 0, got %s" % proc.returncode
        assert '"permissionDecision": "deny"' in out or '"permissionDecision":"deny"' in out, (
            "an Edit whose context contains a non-ASCII character must still "
            "deny when it introduces a bare date, got %r" % out)
        assert "bare date 2026-07-17" in out, "expected bare-date reason text, got %r" % out
    finally:
        os.remove(path)
    print("PASS test_edit_with_nonascii_context_producing_bare_date_denies")


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
    test_read_stdin_text_decodes_utf8_independent_of_locale()
    test_edit_with_nonascii_context_producing_bare_date_denies()
    print("ALL EOS-CLAUDE-MD-GUARD TESTS PASS")
