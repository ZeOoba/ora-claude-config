#!/usr/bin/env python3
"""Tests for append-event-log.py — the collision-safe newest-first inserter.

Why this exists: 2026-06-11 saw three stale-anchor collisions in one day from
concurrent sessions Edit-anchoring the same event_log.md header. The helper's
pure function inserts a new '## ' entry immediately BEFORE the first existing
'## ' entry (newest-first), preserving frontmatter and intro prose.

Run: python test-append-event-log.py   (exit 0 = all pass)
"""
import ctypes
import importlib.util
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "ael", os.path.join(HERE, "append-event-log.py"))
ael = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ael)

results = []


def expect(label, cond, detail=""):
    results.append((bool(cond), label))
    if not cond:
        print("  FAIL: %s %s" % (label, detail))


DOC = ("---\nname: event_log\n---\n\n# ORA Event Log (append-only, newest first)\n\n"
       "Intro prose line.\n\n## 2026-06-10 — older entry\n- detail\n")
ENTRY = "## 2026-06-11 — new entry\n- new detail"

out = ael.insert_newest(DOC, ENTRY)
expect("inserts before first '## '", out.index("## 2026-06-11") < out.index("## 2026-06-10"))
expect("frontmatter preserved", out.startswith("---\nname: event_log\n---"))
expect("intro prose preserved before entry",
       out.index("Intro prose line.") < out.index("## 2026-06-11"))
expect("older entry intact", "## 2026-06-10 — older entry\n- detail" in out)
expect("blank-line separation", "\n\n## 2026-06-11" in out and "new detail\n\n## 2026-06-10" in out)

# no existing entries -> append at end
no_entries = "---\nx: y\n---\n\n# ORA Event Log\n\nIntro.\n"
out2 = ael.insert_newest(no_entries, ENTRY)
expect("no entries -> appended at end", out2.rstrip().endswith("- new detail"))
expect("no entries -> intro intact", "Intro." in out2)

# idempotence of shape: inserting twice keeps both, newest first
out3 = ael.insert_newest(out, "## 2026-06-12 — newest")
expect("second insert lands first",
       out3.index("## 2026-06-12") < out3.index("## 2026-06-11") < out3.index("## 2026-06-10"))

# entry must be a dated '## ' header
try:
    ael.insert_newest(DOC, "not a header")
    expect("rejects non-'## ' entry", False)
except ValueError:
    expect("rejects non-'## ' entry", True)

# '## ' inside frontmatter or intro must not be mistaken for an entry anchor
tricky = "---\ndescription: \"## not an entry\"\n---\n\n# ORA Event Log\n\n## 2026-06-09 — real\n"
out4 = ael.insert_newest(tricky, ENTRY)
expect("frontmatter '## ' not used as anchor",
       out4.index("## 2026-06-11") > out4.index('description'))
expect("real entry still after new one", out4.index("## 2026-06-11") < out4.index("## 2026-06-09"))

# --- in-place fallback (2026-07-16): reproduces the real production failure mode
# (Restart Manager identified Claude.exe holding event_log.md open, which blocks
# os.replace but not direct reads/writes -- memory reference_event_log_app_handle_lock.md)
# by opening our own temp log with a share mode that omits FILE_SHARE_DELETE. Pure
# stdlib (ctypes), Windows-only, matching this machine.

_k32 = ctypes.WinDLL("kernel32", use_last_error=True)
GENERIC_READ = 0x80000000
FILE_SHARE_READ = 0x1
FILE_SHARE_WRITE = 0x2
OPEN_EXISTING = 3
INVALID_HANDLE_VALUE = -1


class _HoldWithoutDeleteShare:
    """Opens `path` without FILE_SHARE_DELETE for the block's duration -- exactly
    what blocks os.replace/os.rename onto that path while leaves direct
    read/write untouched (proven against this same file in the 2026-07-16
    investigation)."""
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


def _make_temp_log(content):
    fd, path = tempfile.mkstemp(suffix="_event_log.md", text=True)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(content)
    return path


def _cleanup(path):
    for p in (path, path + ".tmp-append", path + ".inplace-backup"):
        if os.path.exists(p):
            os.remove(p)


log_seed = "---\nname: event_log\n---\n\n# Log\n\n## 2026-06-10 — older\n- d\n"
new_entry = "## 2026-07-16 — in-place fallback test\n- detail"

# sanity: os.replace really is blocked while the handle is held (confirms the
# simulation matches the real bug, not a no-op)
path = _make_temp_log(log_seed)
try:
    with _HoldWithoutDeleteShare(path):
        try:
            ael._atomic_insert(path, new_entry)
            expect("sanity: os.replace blocked while handle held", False,
                   "(expected PermissionError, atomic insert unexpectedly succeeded)")
        except ValueError:
            raise
        except Exception:
            expect("sanity: os.replace blocked while handle held", True)
finally:
    _cleanup(path)

# _inplace_insert on its own: writes through, backs up prior content, verifies
path = _make_temp_log(log_seed)
try:
    ael._inplace_insert(path, new_entry)
    with open(path, encoding="utf-8") as f:
        result = f.read()
    expect("_inplace_insert applies the entry", "in-place fallback test" in result)
    backup_path = path + ".inplace-backup"
    expect("_inplace_insert writes a backup of the PRIOR content",
           os.path.exists(backup_path) and open(backup_path, encoding="utf-8").read() == log_seed)
finally:
    _cleanup(path)

# _insert_or_inplace with try_inplace=True succeeds via fallback while the atomic
# path is blocked -- this is the actual production scenario
path = _make_temp_log(log_seed)
try:
    with _HoldWithoutDeleteShare(path):
        ok = ael._insert_or_inplace(path, new_entry, try_inplace=True)
        expect("_insert_or_inplace succeeds via in-place fallback under lock", ok is True)
    with open(path, encoding="utf-8") as f:
        result = f.read()
    expect("fallback result contains the new entry", "in-place fallback test" in result)
    expect("fallback result still has the older entry", "## 2026-06-10 — older" in result)
finally:
    _cleanup(path)

# _insert_or_inplace with try_inplace=False must NOT fall back -- it should
# propagate the atomic failure so callers can control when fallback kicks in
path = _make_temp_log(log_seed)
try:
    with _HoldWithoutDeleteShare(path):
        try:
            ael._insert_or_inplace(path, new_entry, try_inplace=False)
            expect("try_inplace=False propagates the atomic failure", False,
                   "(expected an exception, none raised)")
        except ValueError:
            raise
        except Exception:
            expect("try_inplace=False propagates the atomic failure", True)
    with open(path, encoding="utf-8") as f:
        result = f.read()
    expect("try_inplace=False leaves the log untouched", result == log_seed)
finally:
    _cleanup(path)

# malformed entry must raise ValueError immediately, even under lock, and never
# spool or fall back to in-place (retrying a bad entry can't fix it)
path = _make_temp_log(log_seed)
try:
    with _HoldWithoutDeleteShare(path):
        try:
            ael._insert_or_inplace(path, "not a header", try_inplace=True)
            expect("malformed entry raises ValueError even under lock", False)
        except ValueError:
            expect("malformed entry raises ValueError even under lock", True)
finally:
    _cleanup(path)

# end-to-end: main() must append via the fallback (not spool) when the log is
# locked for its whole run -- reproduces + regression-guards the 2026-07-16 incident
path = _make_temp_log(log_seed)
entry_fd, entry_path = tempfile.mkstemp(suffix=".md", text=True)
with os.fdopen(entry_fd, "w", encoding="utf-8") as f:
    f.write(new_entry)
try:
    with _HoldWithoutDeleteShare(path):
        rc = ael.main(["--entry-file", entry_path, "--log", path])
    expect("main() exits 0 under a full-run lock", rc == 0)
    with open(path, encoding="utf-8") as f:
        result = f.read()
    expect("main() appended the entry despite the lock (no data loss)",
           "in-place fallback test" in result)
    pending_dir = path + ".pending"
    spooled = os.path.isdir(pending_dir) and any(
        n.endswith(".md") for n in os.listdir(pending_dir))
    expect("main() did NOT spool -- the fallback made it unnecessary", not spooled)
finally:
    _cleanup(path)
    if os.path.exists(entry_path):
        os.remove(entry_path)
    pending_dir = path + ".pending"
    if os.path.isdir(pending_dir):
        for n in os.listdir(pending_dir):
            os.remove(os.path.join(pending_dir, n))
        os.rmdir(pending_dir)

passed = sum(1 for ok, _ in results if ok)
print("\nappend-event-log tests: %d/%d passed" % (passed, len(results)))
sys.exit(0 if passed == len(results) else 1)
