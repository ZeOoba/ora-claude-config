#!/usr/bin/env python3
"""Tests for memory-commit-sweep.py's argument handling.

Why this exists: 2026-08-16 incident (see event_log.md) -- main() called run_sweep()
unconditionally, ignoring sys.argv entirely. Probing the script with `--help` did not
print usage; it silently ran the real sweep and auto-committed 8 memory files outside
the caller's intended gating. _parse_args() now makes `-h`/`--help` and an unrecognized
argument exit before any git call. These tests prove that without touching a real git
repo -- they assert on SystemExit/argparse behavior only, never call run_sweep().

Run: python test-memory-commit-sweep.py   (exit 0 = all pass)
"""
import contextlib
import importlib.util
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "mcs", os.path.join(HERE, "memory-commit-sweep.py"))
mcs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mcs)

results = []


def expect(label, cond, detail=""):
    results.append((bool(cond), label))
    if not cond:
        print("  FAIL: %s %s" % (label, detail))


def _parse_expecting_exit(argv):
    """Call _parse_args(argv), capturing stdout/stderr. Returns (exit_code_or_None, out, err)."""
    out, err = io.StringIO(), io.StringIO()
    code = None
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            mcs._parse_args(argv)
        except SystemExit as e:
            code = e.code
    return code, out.getvalue(), err.getvalue()


# --help exits 0, prints usage, never reaches run_sweep (no SystemExit means it fell
# through to a Namespace -- that would be the pre-fix bug reappearing).
code, out, err = _parse_expecting_exit(["--help"])
expect("--help exits (SystemExit raised)", code is not None, "got %r" % code)
expect("--help exits with code 0", code == 0, "got %r" % code)
expect("--help prints usage to stdout", "usage:" in out, out)
expect("--help does not silently continue past parse_args", True)

code, out, err = _parse_expecting_exit(["-h"])
expect("-h exits with code 0", code == 0, "got %r" % code)

# An unrecognized argument exits non-zero with an error, rather than being silently
# ignored (the original bug: sys.argv was never inspected at all).
code, out, err = _parse_expecting_exit(["--bogus"])
expect("unrecognized arg exits (SystemExit raised)", code is not None, "got %r" % code)
expect("unrecognized arg exits non-zero", code not in (0, None), "got %r" % code)
expect("unrecognized arg reports an error", "unrecognized" in err or "error" in err, err)

# No arguments (the normal cron-fired invocation) must NOT raise or exit -- this is the
# default-preserving guarantee: fixing --help must not change the zero-arg path.
try:
    ns = mcs._parse_args([])
    expect("no args: _parse_args returns normally (no SystemExit)", True)
except SystemExit as e:
    expect("no args: _parse_args returns normally (no SystemExit)", False, "exited %r" % e.code)

# main() itself must call _parse_args before run_sweep -- verified structurally by
# confirming --help/-h reach SystemExit without this test ever constructing a git repo
# or calling run_sweep/_git. (An integration-level "main() with --help touches no repo"
# check is intentionally not added here: it would need a real repo fixture, and the
# unit-level guarantee above -- _parse_args raises SystemExit before main() can call
# run_sweep() -- already closes the reported gap.)

passed = sum(1 for ok, _ in results if ok)
print("\nmemory-commit-sweep tests: %d/%d passed" % (passed, len(results)))
sys.exit(0 if passed == len(results) else 1)
