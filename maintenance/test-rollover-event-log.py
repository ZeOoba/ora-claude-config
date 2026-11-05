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


# --- 4b-4g. main()'s _unwind must not clobber a concurrent append ---------------
# Test 4 proves write_live_log REFUSES a stale write. But main() then calls
# _unwind, which saw `current != text` and wrote the pre-rollover snapshot back
# over the log -- deleting the very entry the refusal was protecting, then
# reporting the log "verified intact" (finding rollover-unwind-clobbers-concurrent-
# append, I-12a, 2026-11-05). _unwind must tell "damage this run did" (restore)
# from "someone else wrote" (never overwrite).

def _intro_and_body(content):
    i = content.index("\n## ") + 1
    return content[:i], content[i:]


def _insert_newest(content, entry):
    """Newest-first insert after the intro, plus a frontmatter stamp change -- the
    shape append-event-log._atomic_insert/stamp_modified produce, not an EOF append."""
    intro, body = _intro_and_body(content)
    intro = intro.replace("2026-08-16T00:00:00.000Z", "2026-11-05T12:00:00.000Z")
    return intro + entry + body


def _wrap_write(mutate):
    """Replace rollover.write_live_log with one that lets `mutate(log)` land a
    foreign write first, then calls the real function (whose mtime guard raises)."""
    real = rollover.write_live_log

    def wrapped(log, new_live, mtime_before, *a, **k):
        mutate(log)
        return real(log, new_live, mtime_before, *a, **k)
    rollover.write_live_log = wrapped
    return real


def _state(d, p):
    adir = os.path.join(d, "_archive")
    return {
        "log": (open(p, encoding="utf-8", errors="replace").read()
                if os.path.exists(p) else None),
        "backup": (open(p + ".rollover-backup", encoding="utf-8").read()
                   if os.path.exists(p + ".rollover-backup") else None),
        "archive": sorted(os.listdir(adir)) if os.path.isdir(adir) else [],
        "tmp": os.path.exists(p + ".tmp-rollover"),
    }


def _mark_own(log):
    """What the real _inplace_write does immediately before it truncates the log.
    A no-op on code that predates the ownership flag, so these fakes run on both."""
    getattr(rollover, "_note_own_truncation", lambda _log: None)(log)


FOREIGN = "## 2026-11-05 -- concurrent append\n\n- landed during the rollover window\n\n"

print("4b. concurrent newest-first append survives main()'s unwind")
d, p = _mklog(_seed())
try:
    original = open(p, encoding="utf-8").read()
    _, original_body = _intro_and_body(original)

    def _foreign(log):
        with open(log, encoding="utf-8") as f:
            cur = f.read()
        with open(log, "w", encoding="utf-8") as f:
            f.write(_insert_newest(cur, FOREIGN))
    real = _wrap_write(_foreign)
    try:
        rc = rollover.main(["--log", p, "--keep-min", "100"])
    finally:
        rollover.write_live_log = real
    s = _state(d, p)
    check("4b main() reports failure", rc == 1, "(got %r)" % rc)
    check("4b foreign entry survived", s["log"] is not None and "concurrent append" in s["log"])
    check("4b every original entry survived verbatim",
          s["log"] is not None and original_body in s["log"])
    check("4b log not reverted to the pre-rollover snapshot", s["log"] != original)
    check("4b archive removed (re-run not wedged)", s["archive"] == [], "(left: %r)" % s["archive"])
    check("4b no .tmp-rollover left", not s["tmp"])
    check("4b backup kept and holds the original", s["backup"] == original)
    rc2 = rollover.main(["--log", p, "--keep-min", "100"])
    check("4b re-run succeeds and keeps the foreign entry",
          rc2 == 0 and "concurrent append" in open(p, encoding="utf-8").read()
          + "".join(open(os.path.join(d, "_archive", f), encoding="utf-8").read()
                    for f in os.listdir(os.path.join(d, "_archive"))),
          "(rc2=%r)" % rc2)
finally:
    shutil.rmtree(d, ignore_errors=True)

print("4c. ambiguous foreign content is left untouched, scratch retained")
d, p = _mklog(_seed())
try:
    original = open(p, encoding="utf-8").read()
    ambiguous = _insert_newest(original, FOREIGN).replace(
        "- detail line 3 for entry 5\n", "- detail line 3 for entry 5 (edited)\n")

    def _edit(log):
        with open(log, "w", encoding="utf-8") as f:
            f.write(ambiguous)
    real = _wrap_write(_edit)
    try:
        rc = rollover.main(["--log", p, "--keep-min", "100"])
    finally:
        rollover.write_live_log = real
    s = _state(d, p)
    check("4c main() reports failure", rc == 1, "(got %r)" % rc)
    check("4c log left exactly as the foreign writer left it", s["log"] == ambiguous)
    check("4c backup retained with the original", s["backup"] == original)
    check("4c archive retained", len(s["archive"]) == 1, "(got %r)" % s["archive"])
finally:
    shutil.rmtree(d, ignore_errors=True)

print("4d. no dated headers: a superset is NOT proof -- keep everything")
UNDATED = FRONT + "".join(
    "## entry %d\n\n%s\n" % (i, "".join("- undated line %d of %d\n" % (j, i) for j in range(20)))
    for i in range(40))
for label, make in (
        ("superset", lambda cur: _insert_newest(cur, "## note -- foreign\n\n- x\n\n")),
        ("damaged", lambda cur: FRONT + "## entry 0\n\n- mangled\n")):
    d, p = _mklog(UNDATED)
    try:
        original = open(p, encoding="utf-8").read()
        forced = make(original)

        def _write_forced(log, forced=forced):
            with open(log, "w", encoding="utf-8") as f:
                f.write(forced)
        real = _wrap_write(_write_forced)
        try:
            rc = rollover.main(["--log", p, "--keep-min", "100"])
        finally:
            rollover.write_live_log = real
        s = _state(d, p)
        check("4d[%s] main() reports failure" % label, rc == 1, "(got %r)" % rc)
        check("4d[%s] log left untouched" % label, s["log"] == forced)
        check("4d[%s] backup retained" % label, s["backup"] == original)
        check("4d[%s] archive retained" % label, len(s["archive"]) == 1, "(got %r)" % s["archive"])
    finally:
        shutil.rmtree(d, ignore_errors=True)

print("4e. dated-header regex is the one append-event-log uses")
_append = _load("append_event_log_for_rollover_test", "append-event-log.py")
check("4e ENTRY_HEADER_RE pattern matches append-event-log's",
      getattr(rollover, "ENTRY_HEADER_RE", None) is not None
      and rollover.ENTRY_HEADER_RE.pattern == _append.ENTRY_HEADER_RE.pattern)


def _inplace_fault(write_after_truncate):
    """_atomic_swap blocked; _inplace_write truncates, lets `write_after_truncate`
    put bytes in the log, then fails like ENOSPC."""
    real_atomic, real_inplace = rollover._atomic_swap, rollover._inplace_write

    def _blocked(log, new_live, mtime_before):
        raise OSError("simulated app handle lock -- os.replace blocked")

    def _fault(log, new_live, mtime_before):
        _mark_own(log)  # the real _inplace_write marks ownership right before open("w")
        with open(log, "wb") as f:
            f.write(write_after_truncate(new_live))
        raise OSError(28, "simulated ENOSPC mid-write")
    rollover._atomic_swap, rollover._inplace_write = _blocked, _fault
    return real_atomic, real_inplace


def _as_written(s):
    """Bytes text-mode open(..., 'w', encoding='utf-8') would put on disk."""
    return s.replace("\n", os.linesep).encode("utf-8")


print("4f. partial write cut inside a multi-byte UTF-8 char is restored")
d, p = _mklog(_seed())
try:
    original = open(p, encoding="utf-8").read()

    def _cut_mid_char(new_live):
        b = _as_written(new_live)
        i = b.index("“".encode("utf-8"))   # the pointer note's opening quote
        return b[:i + 1]                          # one byte of a three-byte char
    saved = _inplace_fault(_cut_mid_char)
    try:
        try:
            rc = rollover.main(["--log", p, "--keep-min", "100"])
        except Exception as e:
            rc = "raised %s" % type(e).__name__
    finally:
        rollover._atomic_swap, rollover._inplace_write = saved
    s = _state(d, p)
    check("4f main() reports failure (no crash)", rc == 1, "(got %r)" % (rc,))
    check("4f live log restored to the original", s["log"] == original)
    check("4f scratch cleared after restore", s["backup"] is None and s["archive"] == [],
          "(backup:%s archive:%r)" % (s["backup"] is not None, s["archive"]))
finally:
    shutil.rmtree(d, ignore_errors=True)

print("4g. foreign append landing after OUR truncation: keep everything")
d, p = _mklog(_seed())
try:
    original = open(p, encoding="utf-8").read()
    holder = {}

    def _partial_plus_foreign(new_live):
        partial = new_live[:len(new_live) // 3]
        mixed = _insert_newest(partial, FOREIGN)
        holder["mixed"] = mixed
        return _as_written(mixed)
    saved = _inplace_fault(_partial_plus_foreign)
    try:
        rc = rollover.main(["--log", p, "--keep-min", "100"])
    finally:
        rollover._atomic_swap, rollover._inplace_write = saved
    s = _state(d, p)
    check("4g main() reports failure", rc == 1, "(got %r)" % rc)
    check("4g log left untouched (foreign entry not overwritten)", s["log"] == holder.get("mixed"))
    check("4g backup retained with the original", s["backup"] == original)
    check("4g archive retained", len(s["archive"]) == 1, "(got %r)" % s["archive"])
finally:
    shutil.rmtree(d, ignore_errors=True)

# --- 4h-4j. ownership comes from what THIS run did, not from the log's content --
# REFUTE pass on PR #400 (P4, P9): "unreadable" or "a prefix of new_live" is not
# proof the damage is ours. Only a run that actually truncated the log may restore.

print("4h. foreign append + transient unreadable read: keep everything (P4)")
d, p = _mklog(_seed())
try:
    original = open(p, encoding="utf-8").read()

    def _foreign_4h(log):
        with open(log, encoding="utf-8") as f:
            cur = f.read()
        with open(log, "w", encoding="utf-8") as f:
            f.write(_insert_newest(cur, FOREIGN))
    real = _wrap_write(_foreign_4h)
    real_read = rollover._read_log_text
    calls = {"n": 0}

    def _flaky_read(log):
        calls["n"] += 1
        return None if calls["n"] == 1 else real_read(log)
    rollover._read_log_text = _flaky_read
    try:
        rc = rollover.main(["--log", p, "--keep-min", "100"])
    finally:
        rollover.write_live_log = real
        rollover._read_log_text = real_read
    s = _state(d, p)
    check("4h main() reports failure", rc == 1, "(got %r)" % rc)
    check("4h foreign entry survived", s["log"] is not None and "concurrent append" in s["log"])
    check("4h backup retained with the original", s["backup"] == original)
    check("4h archive retained", len(s["archive"]) == 1, "(got %r)" % s["archive"])
finally:
    shutil.rmtree(d, ignore_errors=True)

print("4i. foreign in-place insert mid-write (short prefix of new_live): no restore (P9)")
for cut in (0, 20):
    d, p = _mklog(_seed())
    try:
        original = open(p, encoding="utf-8").read()
        foreign_full = _insert_newest(original, FOREIGN)

        def _foreign_truncating(log, cut=cut, foreign_full=foreign_full):
            with open(log, "w", encoding="utf-8") as f:   # another writer's in-place insert
                f.write(foreign_full[:cut])
        real = _wrap_write(_foreign_truncating)
        try:
            rc = rollover.main(["--log", p, "--keep-min", "100"])
        finally:
            rollover.write_live_log = real
        s = _state(d, p)
        check("4i[cut=%d] main() reports failure" % cut, rc == 1, "(got %r)" % rc)
        check("4i[cut=%d] log NOT overwritten by a restore" % cut,
              s["log"] == foreign_full[:cut], "(len %r)" % (len(s["log"] or ""),))
        check("4i[cut=%d] backup retained with the original" % cut, s["backup"] == original)
        check("4i[cut=%d] archive retained" % cut, len(s["archive"]) == 1, "(got %r)" % s["archive"])
    finally:
        shutil.rmtree(d, ignore_errors=True)

print("4j. keep-everything message warns the backup lacks foreign entries (P5)")
d, p = _mklog(_seed())
try:
    original = open(p, encoding="utf-8").read()
    ambiguous_4j = _insert_newest(original, FOREIGN).replace(
        "- detail line 3 for entry 5\n", "- detail line 3 for entry 5 (edited)\n")

    def _edit_4j(log):
        with open(log, "w", encoding="utf-8") as f:
            f.write(ambiguous_4j)
    real = _wrap_write(_edit_4j)
    import io as _io
    import contextlib as _ctx
    err = _io.StringIO()
    try:
        with _ctx.redirect_stderr(err):
            rc = rollover.main(["--log", p, "--keep-min", "100"])
    finally:
        rollover.write_live_log = real
    msg = err.getvalue()
    check("4j message says the backup lacks foreign entries",
          "does NOT contain" in msg and "foreign" in msg.lower(), "(stderr: %r)" % msg[-300:])
finally:
    shutil.rmtree(d, ignore_errors=True)


# --- 7. rollover holds append-event-log's own _log_lock (P2, P3, P8) -------------
# The mtime guard has a gap between its stat and os.replace / open("w"); an append
# landing there is silently lost with rc=0. The cure is the lock appenders already
# take: hold it from the snapshot read through the swap and _unwind.
import subprocess
import time as _time

_APPEND = os.path.join(HERE, "append-event-log.py")
_HOLDER = r'''
import importlib.util, sys
s = importlib.util.spec_from_file_location("ap", sys.argv[1]); m = importlib.util.module_from_spec(s)
s.loader.exec_module(m)
with m._log_lock(sys.argv[2], timeout=10):
    print("locked", flush=True)
    sys.stdin.read()
'''

print("7a. rollover refuses (writes nothing) while an appender holds the lock")
d, p = _mklog(_seed())
holder = subprocess.Popen([sys.executable, "-c", _HOLDER, _APPEND, p],
                          stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
try:
    check("7a holder acquired the lock", holder.stdout.readline().strip() == "locked")
    original = open(p, encoding="utf-8").read()
    saved_t = getattr(rollover, "ROLLOVER_LOCK_TIMEOUT_S", None)
    if saved_t is not None:
        rollover.ROLLOVER_LOCK_TIMEOUT_S = 0.5
    try:
        rc = rollover.main(["--log", p, "--keep-min", "100"])
    finally:
        if saved_t is not None:
            rollover.ROLLOVER_LOCK_TIMEOUT_S = saved_t
    s = _state(d, p)
    check("7a main() refuses", rc == 1, "(got %r)" % rc)
    check("7a log untouched", s["log"] == original)
    check("7a no archive, no backup written", s["archive"] == [] and s["backup"] is None,
          "(archive %r backup %s)" % (s["archive"], s["backup"] is not None))
finally:
    try:
        holder.stdin.close()
        holder.wait(timeout=20)
    except Exception:
        holder.kill()
    shutil.rmtree(d, ignore_errors=True)

print("7b. an append started mid-rollover waits for the lock and lands afterwards")
d, p = _mklog(_seed())
entry_file = os.path.join(d, "entry.md")
with open(entry_file, "w", encoding="utf-8") as f:
    f.write("## 2026-11-05 -- appended during rollover\n\n- waited for the lock\n")
procs = {}
try:
    real = rollover.write_live_log

    def _spawn_append_then_write(log, new_live, mtime_before, *a, **k):
        procs["p"] = subprocess.Popen(
            [sys.executable, _APPEND, "--log", log, "--entry-file", entry_file],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        _time.sleep(1.5)                      # appender is up and contending
        procs["waiting"] = procs["p"].poll() is None
        procs["mtime_still"] = os.stat(log).st_mtime_ns == mtime_before
        return real(log, new_live, mtime_before, *a, **k)
    rollover.write_live_log = _spawn_append_then_write
    try:
        rc = rollover.main(["--log", p, "--keep-min", "100"])
    finally:
        rollover.write_live_log = real
    out, errs = procs["p"].communicate(timeout=60)
    final = open(p, encoding="utf-8").read()
    check("7b appender was blocked while rollover held the lock",
          procs.get("waiting") and procs.get("mtime_still"),
          "(waiting=%r mtime_unchanged=%r)" % (procs.get("waiting"), procs.get("mtime_still")))
    check("7b rollover completed", rc == 0, "(got %r)" % rc)
    check("7b appender exited 0", procs["p"].returncode == 0,
          "(rc %r, stderr %r)" % (procs["p"].returncode, errs[-300:]))
    check("7b appended entry landed in the rolled-over log",
          "appended during rollover" in final and "rolled over" in final)
    adir = os.path.join(d, "_archive")
    check("7b archive written once", os.path.isdir(adir) and len(os.listdir(adir)) == 1)
finally:
    if "p" in procs and procs["p"].poll() is None:
        procs["p"].kill()
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

# --- 5b. a truncating in-place failure must stay RECOVERABLE --------------------
# The in-place fallback opens the log "w", truncating before any bytes land. A
# failure after that point leaves the log damaged, and the pre-write backup holds
# the only copy of the original. The first version of _unwind deleted it anyway
# ("the live log is untouched in all failure paths" -- true before the in-place
# path existed, false after): a probe drove an ENOSPC-shaped failure through it
# and got a 0-byte log with backup and archive both gone. Unrecoverable loss of
# the canonical log, caused by the recovery path itself.
print("truncating in-place failure stays recoverable")
d, p = _mklog(_seed())
try:
    original = open(p, encoding="utf-8").read()
    real_atomic, real_inplace = rollover._atomic_swap, rollover._inplace_write

    def _blocked(log, new_live, mtime_before):
        raise OSError("simulated app handle lock -- os.replace blocked")

    def _truncate_then_fail(log, new_live, mtime_before):
        _mark_own(log)  # the real _inplace_write marks ownership right before open("w")
        with open(log, "w", encoding="utf-8"):
            pass                      # truncated; zero bytes written
        raise OSError(28, "simulated ENOSPC after truncation")

    rollover._atomic_swap, rollover._inplace_write = _blocked, _truncate_then_fail
    try:
        rc = rollover.main(["--log", p, "--keep-min", "100"])
    finally:
        rollover._atomic_swap, rollover._inplace_write = real_atomic, real_inplace

    check("main() reports failure", rc == 1, "(got %r)" % rc)
    now = open(p, encoding="utf-8").read() if os.path.exists(p) else ""
    backup_left = os.path.exists(p + ".rollover-backup")
    adir = os.path.join(d, "_archive")
    archive_left = os.path.isdir(adir) and bool(os.listdir(adir))
    check("original content is recoverable somewhere",
          now == original or backup_left or archive_left,
          "(log==orig:%s backup:%s archive:%s)" % (now == original, backup_left, archive_left))
    check("live log restored in place", now == original,
          "(size %d, original %d)" % (len(now), len(original)))
    # and once restored, the scratch is cleaned so a re-run still works
    if now == original:
        check("scratch cleared after successful restore",
              not backup_left and not archive_left,
              "(backup:%s archive:%s)" % (backup_left, archive_left))
        rc2 = rollover.main(["--log", p, "--keep-min", "100"])
        check("re-run succeeds after restore", rc2 == 0, "(got %r)" % rc2)
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
