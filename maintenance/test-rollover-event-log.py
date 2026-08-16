#!/usr/bin/env python3
"""Tests for rollover-event-log.py — the structural event_log.md rollover.

Why this exists (2026-08-16): rollover-event-log.py performed a bare
`os.replace(tmp, log)` with no retry and no fallback, while writing its archive
file and backup BEFORE that replace. The Claude.exe handle lock
(memory/reference_event_log_app_handle_lock.md — a read handle without
FILE_SHARE_DELETE blocks os.replace but not direct reads/writes) therefore did
worse than fail: it left `event_log_<today>.md` on disk with the live log
UNCHANGED, and the archive-exists guard then refused every re-run. A transient,
self-clearing lock wedged rollover until someone cleaned up by hand.

These tests mirror test-append-event-log.py's lock reproduction (pure stdlib
ctypes, Windows) rather than approximating it, so they fail against the real
production failure mode and not a stand-in.

Run: python test-rollover-event-log.py   (exit 0 = all pass)
"""
import ctypes
import importlib.util
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))


def _load(name, filename):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, filename))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


rollover = _load("rollover_event_log", "rollover-event-log.py")

# --- lock reproduction, identical to test-append-event-log.py -------------------
_k32 = ctypes.WinDLL("kernel32", use_last_error=True)
GENERIC_READ = 0x80000000
FILE_SHARE_READ = 0x1
FILE_SHARE_WRITE = 0x2
OPEN_EXISTING = 3
INVALID_HANDLE_VALUE = -1


class _HoldWithoutDeleteShare:
    """Opens `path` without FILE_SHARE_DELETE for the block's duration -- blocks
    os.replace/os.rename onto that path while leaving direct read/write working."""

    def __init__(self, path):
        self.path = path
        self.handle = None

    def __enter__(self):
        self.handle = _k32.CreateFileW(
            self.path, GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_WRITE,
            None, OPEN_EXISTING, 0, None)
        if self.handle in (0, INVALID_HANDLE_VALUE):
            raise OSError("CreateFileW failed, GetLastError=%d" % ctypes.get_last_error())
        return self

    def __exit__(self, *exc):
        _k32.CloseHandle(self.handle)


FRONT = "---\nname: event_log\nmetadata:\n  modified: 2026-08-16T00:00:00.000Z\n---\n\n# ORA Event Log\n\nIntro prose.\n\n"


def _seed(n_entries=40, body_lines=20):
    """A log whose entries are newest-first, big enough to exceed keep_min."""
    out = [FRONT]
    for i in range(n_entries):
        out.append("## 2026-08-%02d -- entry %d\n\n" % ((i % 28) + 1, i))
        out.extend("- detail line %d for entry %d\n" % (j, i) for j in range(body_lines))
        out.append("\n")
    return "".join(out)


def _mklog(content):
    d = tempfile.mkdtemp(prefix="rollover_test_")
    p = os.path.join(d, "event_log.md")
    with open(p, "w", encoding="utf-8") as f:
        f.write(content)
    return d, p


FAILURES = []


def check(name, cond, detail=""):
    if cond:
        print("  PASS  %s" % name)
    else:
        print("  FAIL  %s %s" % (name, detail))
        FAILURES.append(name)


# --- 1. the archive must land beside the TARGET log, not the real memory dir ----
# ARCHIVE_DIR was module-level (derived from the hardcoded LOG), so --log pointed
# somewhere else still wrote the archive into the real memory/_archive.
print("archive dir follows --log")
d, p = _mklog(_seed())
try:
    rc = rollover.main(["--log", p, "--keep-min", "100"])
    check("main() exits 0", rc == 0, "(got %r)" % rc)
    archives = [f for f in os.listdir(d) if f == "_archive"]
    check("archive dir created beside the target log", archives == ["_archive"],
          "(dir listing: %r)" % sorted(os.listdir(d)))
    if archives:
        files = os.listdir(os.path.join(d, "_archive"))
        check("exactly one archive file written", len(files) == 1, "(got %r)" % files)
finally:
    shutil.rmtree(d, ignore_errors=True)

# --- 2. sanity: os.replace really is blocked under the hold --------------------
print("lock reproduction is real (not a no-op)")
d, p = _mklog(_seed())
try:
    tmp = p + ".probe"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write("x")
    blocked = False
    with _HoldWithoutDeleteShare(p):
        try:
            os.replace(tmp, p)
        except OSError:
            blocked = True
    check("os.replace blocked while handle held", blocked)
    if os.path.exists(tmp):
        os.remove(tmp)
finally:
    shutil.rmtree(d, ignore_errors=True)

# --- 3. rollover completes THROUGH the lock via the in-place fallback -----------
print("rollover survives the handle lock")
d, p = _mklog(_seed())
try:
    before = open(p, encoding="utf-8").read()
    with _HoldWithoutDeleteShare(p):
        rc = rollover.main(["--log", p, "--keep-min", "100"])
    check("main() exits 0 under lock", rc == 0, "(got %r)" % rc)
    after = open(p, encoding="utf-8").read()
    check("live log actually shrank", len(after) < len(before),
          "(before=%d after=%d)" % (len(before), len(after)))
    check("frontmatter preserved", after.startswith("---\nname: event_log"))
    check("pointer note appended", "rolled over" in after)
    check("no orphaned .tmp-rollover left", not os.path.exists(p + ".tmp-rollover"))
    check("no backup left behind on success", not os.path.exists(p + ".rollover-backup"))
finally:
    shutil.rmtree(d, ignore_errors=True)

# --- 4. a concurrent append must NOT be clobbered by the retry loop -------------
# The retry introduces a window the original didn't have: new_live was computed
# from a stale read, so writing it after someone else appended destroys their
# entry. Every attempt must re-check mtime and abort instead.
print("concurrent append aborts the write (no clobber)")
d, p = _mklog(_seed())
try:
    original = open(p, encoding="utf-8").read()
    new_live = "REPLACEMENT CONTENT\n"
    stale_mtime = os.stat(p).st_mtime_ns
    # someone else appends between the read and the write
    with open(p, "w", encoding="utf-8") as f:
        f.write(original + "\n## 2026-08-16 -- concurrent append\n- landed\n")
    raised = False
    try:
        rollover.write_live_log(p, new_live, stale_mtime)
    except BlockingIOError:
        raised = True
    except Exception as e:
        check("aborted with BlockingIOError", False, "(got %r)" % e)
    check("stale write refused", raised)
    now = open(p, encoding="utf-8").read()
    check("concurrent append survived", "concurrent append" in now)
    check("stale content never written", "REPLACEMENT CONTENT" not in now)
finally:
    shutil.rmtree(d, ignore_errors=True)

# --- 5. total write failure must not wedge the next run ------------------------
# If the live log could not be replaced, the archive it already wrote duplicates
# still-live content AND trips the archive-exists guard on re-run. Both must go.
print("failed write cleans up so a re-run is possible")
d, p = _mklog(_seed())
try:
    original = open(p, encoding="utf-8").read()
    real = rollover.write_live_log
    rollover.write_live_log = lambda *a, **k: False  # every path failed
    try:
        rc = rollover.main(["--log", p, "--keep-min", "100"])
    finally:
        rollover.write_live_log = real
    check("main() reports failure", rc == 1, "(got %r)" % rc)
    check("live log untouched", open(p, encoding="utf-8").read() == original)
    adir = os.path.join(d, "_archive")
    left = os.listdir(adir) if os.path.isdir(adir) else []
    check("archive file removed (re-run not wedged)", left == [], "(left: %r)" % left)
    check("no orphaned .tmp-rollover", not os.path.exists(p + ".tmp-rollover"))
    check("no orphaned backup", not os.path.exists(p + ".rollover-backup"))
    # and the proof it matters: a second run now gets as far as writing again
    rc2 = rollover.main(["--log", p, "--keep-min", "100"])
    check("re-run succeeds after cleanup", rc2 == 0, "(got %r)" % rc2)
finally:
    shutil.rmtree(d, ignore_errors=True)

# --- 6. regression: unlocked rollover still behaves --------------------------
print("regressions")
d, p = _mklog(_seed())
try:
    rc = rollover.main(["--log", p, "--keep-min", "100", "--dry-run"])
    check("--dry-run exits 0", rc == 0, "(got %r)" % rc)
    check("--dry-run wrote nothing", not os.path.isdir(os.path.join(d, "_archive")))
    short_d, short_p = _mklog(FRONT + "## 2026-08-16 -- only\n- one\n")
    try:
        rc = rollover.main(["--log", short_p, "--keep-min", "600"])
        check("short log is a no-op exit 0", rc == 0, "(got %r)" % rc)
    finally:
        shutil.rmtree(short_d, ignore_errors=True)
finally:
    shutil.rmtree(d, ignore_errors=True)

print()
if FAILURES:
    print("FAILED (%d): %s" % (len(FAILURES), ", ".join(FAILURES)))
    sys.exit(1)
print("all rollover-event-log tests passed")
sys.exit(0)
