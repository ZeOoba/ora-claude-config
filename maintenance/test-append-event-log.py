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
    # On success the backup has discharged its purpose and is removed (2026-07-16 --
    # it used to strand next to the log). The "backup survives a FAILED write" half of
    # the net is asserted in the residue block below.
    expect("_inplace_insert removes the backup once the write verifies",
           not os.path.exists(path + ".inplace-backup"))
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

# --- scratch-file residue (2026-07-16, same day as the fallback itself): both write
# paths leaked a ~480KB scratch file next to event_log.md. os.replace is the ONLY
# thing that consumes .tmp-append, so a blocked atomic attempt orphaned it -- and the
# in-place fallback that rescued the append writes straight to the log and never
# picked it up. Filenames are fixed, so at most one of each can strand; the harm is
# that an orphan reads as unmerged data and costs a real investigation to clear.

def _residue(path):
    """Scratch files still on disk next to `path`."""
    return sorted(s for s in (".tmp-append", ".inplace-backup")
                  if os.path.exists(path + s))


# a blocked atomic insert must not strand its scratch file
path = _make_temp_log(log_seed)
try:
    with _HoldWithoutDeleteShare(path):
        try:
            ael._atomic_insert(path, new_entry)
            expect("sanity: atomic insert blocked (residue test)", False,
                   "(expected PermissionError)")
        except ValueError:
            raise
        except Exception:
            pass
    expect("blocked _atomic_insert leaves no .tmp-append", _residue(path) == [], _residue(path))
finally:
    _cleanup(path)

# a verified in-place write makes its backup redundant -> no residue
path = _make_temp_log(log_seed)
try:
    ael._inplace_insert(path, new_entry)
    expect("verified _inplace_insert removes its .inplace-backup",
           _residue(path) == [], _residue(path))
finally:
    _cleanup(path)

# ...but a FAILED in-place write must KEEP the backup -- recovery is its whole purpose.
# Fails only the log's "w" open, so the backup is written and the log write then dies.
path = _make_temp_log(log_seed)
_real_open = open


def _open_failing_log_write(p, *a, **k):
    if p == path and a and a[0] == "w":
        raise PermissionError("simulated mid-write failure")
    return _real_open(p, *a, **k)


ael.open = _open_failing_log_write
try:
    try:
        ael._inplace_insert(path, new_entry)
        expect("failed _inplace_insert raises", False, "(no exception)")
    except ValueError:
        raise
    except Exception:
        expect("failed _inplace_insert raises", True)
finally:
    del ael.open
try:
    backup_path = path + ".inplace-backup"
    expect("failed _inplace_insert KEEPS its backup (recovery net intact)",
           os.path.exists(backup_path))
    expect("kept backup holds the prior content",
           os.path.exists(backup_path)
           and _real_open(backup_path, encoding="utf-8").read() == log_seed)
finally:
    _cleanup(path)

# the actual production scenario: fallback rescues the append under lock, no residue
path = _make_temp_log(log_seed)
try:
    with _HoldWithoutDeleteShare(path):
        ael._insert_or_inplace(path, new_entry, try_inplace=True)
    expect("in-place fallback under lock leaves no residue", _residue(path) == [], _residue(path))
finally:
    _cleanup(path)

# end-to-end regression for the 2026-07-16 incident: main() under a full-run lock
# appended correctly but stranded a 480KB .tmp-append next to the log
path = _make_temp_log(log_seed)
entry_fd, entry_path = tempfile.mkstemp(suffix=".md", text=True)
with os.fdopen(entry_fd, "w", encoding="utf-8") as f:
    f.write(new_entry)
try:
    with _HoldWithoutDeleteShare(path):
        rc = ael.main(["--entry-file", entry_path, "--log", path])
    expect("main() under lock exits 0 (residue test)", rc == 0)
    with open(path, encoding="utf-8") as f:
        expect("main() under lock still appended the entry", "in-place fallback test" in f.read())
    expect("main() under lock leaves no residue (2026-07-16 regression)",
           _residue(path) == [], _residue(path))
finally:
    _cleanup(path)
    if os.path.exists(entry_path):
        os.remove(entry_path)
    pending_dir = path + ".pending"
    if os.path.isdir(pending_dir):
        for n in os.listdir(pending_dir):
            os.remove(os.path.join(pending_dir, n))
        os.rmdir(pending_dir)

# --- warn_if_uncommitted_backlog(): 2026-07-17, the systematization follow-up
# from a session that hit event_log.md piling up multi-session uncommitted
# entries. Best-effort, never-blocking -- test both the WARN and the silent
# paths, and confirm it never raises regardless of git/repo state. ---
import io
import subprocess


def _run_git(args, cwd):
    subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True)


def _make_temp_git_repo():
    d = tempfile.mkdtemp(prefix="ael-warn-repo-")
    _run_git(["init", "-q"], d)
    _run_git(["config", "user.email", "t@t.t"], d)
    _run_git(["config", "user.name", "t"], d)
    return d


def _captured_stderr_of(fn, *a, **kw):
    old = sys.stderr
    sys.stderr = io.StringIO()
    try:
        fn(*a, **kw)
        return sys.stderr.getvalue()
    finally:
        sys.stderr = old


repo = _make_temp_git_repo()
log_path = os.path.join(repo, "event_log.md")
with open(log_path, "w", encoding="utf-8") as f:
    f.write(DOC)
_run_git(["add", "event_log.md"], repo)
_run_git(["commit", "-q", "-m", "base"], repo)

# below threshold: append 1 entry (< UNCOMMITTED_BACKLOG_WARN_AT), expect silence
content = open(log_path, encoding="utf-8").read()
open(log_path, "w", encoding="utf-8").write(
    ael.insert_newest(content, "## 2026-07-17 — entry 1\n- x"))
err = _captured_stderr_of(ael.warn_if_uncommitted_backlog, log_path)
expect("below threshold: no WARN", err == "", err)

# at threshold: append enough more entries to reach UNCOMMITTED_BACKLOG_WARN_AT
# total uncommitted headers, expect a WARN naming the count
for i in range(2, ael.UNCOMMITTED_BACKLOG_WARN_AT + 1):
    content = open(log_path, encoding="utf-8").read()
    open(log_path, "w", encoding="utf-8").write(
        ael.insert_newest(content, "## 2026-07-17 — entry %d\n- x" % i))
err = _captured_stderr_of(ael.warn_if_uncommitted_backlog, log_path)
expect("at threshold: WARN fires", "WARN" in err, err)
expect("WARN names the actual count",
       str(ael.UNCOMMITTED_BACKLOG_WARN_AT) in err, err)

# committing clears the backlog -> silence again
_run_git(["add", "event_log.md"], repo)
_run_git(["commit", "-q", "-m", "land the backlog"], repo)
err = _captured_stderr_of(ael.warn_if_uncommitted_backlog, log_path)
expect("after commit: backlog cleared, no WARN", err == "", err)

# mutation check: threshold math is not vacuous -- one entry short of
# threshold must NOT warn, confirming the >= boundary is exercised for real
content = open(log_path, encoding="utf-8").read()
for i in range(1, ael.UNCOMMITTED_BACKLOG_WARN_AT):
    content = ael.insert_newest(content, "## 2026-07-17 — pre-thresh %d\n- x" % i)
open(log_path, "w", encoding="utf-8").write(content)
err = _captured_stderr_of(ael.warn_if_uncommitted_backlog, log_path)
expect("one short of threshold: still silent (boundary is real, not off-by-one)",
       err == "", err)

# never a git repo -> silent, never raises
non_repo = tempfile.mkdtemp(prefix="ael-warn-norepo-")
non_repo_log = os.path.join(non_repo, "event_log.md")
with open(non_repo_log, "w", encoding="utf-8") as f:
    f.write(DOC)
try:
    err = _captured_stderr_of(ael.warn_if_uncommitted_backlog, non_repo_log)
    expect("non-repo path never raises and stays silent", err == "", err)
except Exception as e:
    expect("non-repo path never raises", False, str(e))

# main() still returns 0 and still appends even when the warn path is exercised
entry_fd, entry_path = tempfile.mkstemp(suffix=".md", text=True)
with os.fdopen(entry_fd, "w", encoding="utf-8") as f:
    f.write("## 2026-07-17 — via main()\n- x")
rc = ael.main(["--entry-file", entry_path, "--log", log_path])
expect("main() still exits 0 when the backlog warning also fires", rc == 0)
with open(log_path, encoding="utf-8") as f:
    expect("main() still appended the entry", "via main()" in f.read())
os.remove(entry_path)


passed = sum(1 for ok, _ in results if ok)
print("\nappend-event-log tests: %d/%d passed" % (passed, len(results)))
sys.exit(0 if passed == len(results) else 1)
