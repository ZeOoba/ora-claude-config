#!/usr/bin/env python3
"""Tests for checkout-merge-forward.py -- the paired corrector to
cross-repo-wip-scan.py's branch-drift detection (open-items-tracker.md#OI-249,
candidate (a), 2026-09-09). Real throwaway git repos with a real local
"origin" remote (file-path clone) -- no mocked git, same convention as
test_check_branch_point.py and test_cross_repo_wip_scan.py.

Run: python _tests/test_checkout_merge_forward.py   (exit 0 = pass)
"""
import importlib.util
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(os.path.dirname(HERE), "checkout-merge-forward.py")

_spec = importlib.util.spec_from_file_location("cmf", SCRIPT)
cmf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cmf)

_results = []


def check(name, cond, detail=""):
    _results.append((bool(cond), name))
    if not cond:
        print("FAIL %s  %s" % (name, detail))
    else:
        print("PASS %s" % name)


def run(repo, *args, check_rc=True):
    p = subprocess.run(["git"] + list(args), cwd=repo, capture_output=True, text=True)
    if check_rc and p.returncode != 0:
        raise RuntimeError("git %s failed: %s" % (" ".join(args), p.stderr))
    return p


def write(repo, fname, text):
    with open(os.path.join(repo, fname), "w", encoding="utf-8") as fh:
        fh.write(text)


def commit(repo, msg, fname=None):
    fname = fname or (msg.replace(" ", "_") + ".txt")
    write(repo, fname, msg)
    run(repo, "add", fname)
    run(repo, "commit", "-q", "-m", msg, "--no-verify")


def make_pair(td, canonical="main"):
    """(local, origin) -- local is a real clone of origin, both on `canonical`
    with one shared commit, local's `origin/<canonical>` genuinely resolves."""
    origin = os.path.join(td, "origin")
    os.makedirs(origin)
    run(origin, "init", "-q", "-b", canonical)
    run(origin, "config", "user.email", "t@example.com")
    run(origin, "config", "user.name", "T")
    commit(origin, "base commit")

    local = os.path.join(td, "local")
    run(td, "clone", "-q", origin, local)
    run(local, "config", "user.email", "t@example.com")
    run(local, "config", "user.name", "T")
    return local, origin


# --- already up to date -> NOOP_CLEAN, no commit made -------------------------------
with tempfile.TemporaryDirectory() as td:
    local, origin = make_pair(td)
    before = run(local, "rev-parse", "HEAD").stdout.strip()
    r = cmf.sync(local, "main")
    check("noop: status NOOP_CLEAN", r["status"] == "NOOP_CLEAN", repr(r))
    check("noop: commits_merged 0", r["commits_merged"] == 0, repr(r))
    after = run(local, "rev-parse", "HEAD").stdout.strip()
    check("noop: HEAD unchanged", before == after, "before=%s after=%s" % (before, after))

# --- clean fast-forwardable drift -> MERGED, exactly N commits landed ---------------
with tempfile.TemporaryDirectory() as td:
    local, origin = make_pair(td)
    for i in range(3):
        commit(origin, "origin commit %d" % i, fname="o%d.txt" % i)
    r = cmf.sync(local, "main")
    check("merge: status MERGED", r["status"] == "MERGED", repr(r))
    check("merge: commits_merged == 3", r["commits_merged"] == 3, repr(r))
    check("merge: sha reported", bool(r["sha"]), repr(r))
    head = run(local, "rev-parse", "HEAD").stdout.strip()
    check("merge: HEAD actually moved to the reported sha", head == r["sha"], repr(r))
    check("merge: origin's new files are present",
          os.path.isfile(os.path.join(local, "o0.txt"))
          and os.path.isfile(os.path.join(local, "o2.txt")))
    check("merge: index is clean after (nothing left staged)",
          run(local, "diff", "--cached", "--name-only").stdout.strip() == "")
    check("merge: no unrelated file touched",
          not os.path.isfile(os.path.join(local, "should-not-exist.txt")))

    # A second run is a clean no-op -- proves the merge actually committed.
    r2 = cmf.sync(local, "main")
    check("merge: second run is NOOP_CLEAN", r2["status"] == "NOOP_CLEAN", repr(r2))

# --- dirty overlap: local uncommitted change to a path origin also touches ---------
with tempfile.TemporaryDirectory() as td:
    local, origin = make_pair(td)
    commit(origin, "origin changes shared.txt", fname="shared.txt")
    # Local has an UNCOMMITTED edit to the same path origin's new commit touches.
    write(local, "shared.txt", "local uncommitted edit, conflicts with the fetch\n")
    r = cmf.sync(local, "main")
    check("dirty-overlap: status BLOCKED_DIRTY_OVERLAP",
          r["status"] == "BLOCKED_DIRTY_OVERLAP", repr(r))
    check("dirty-overlap: local uncommitted edit preserved verbatim",
          open(os.path.join(local, "shared.txt")).read()
          == "local uncommitted edit, conflicts with the fetch\n")
    check("dirty-overlap: no MERGE_HEAD left behind",
          run(local, "rev-parse", "-q", "--verify", "MERGE_HEAD", check_rc=False).returncode != 0)
    check("dirty-overlap: local HEAD did not move past what it cloned",
          run(local, "rev-parse", "HEAD").stdout.strip()
          != run(origin, "rev-parse", "HEAD").stdout.strip())

# --- real textual conflict: both sides edit the SAME line, committed on both sides -
with tempfile.TemporaryDirectory() as td:
    local, origin = make_pair(td)
    write(origin, "conflict.txt", "origin version\n")
    run(origin, "add", "conflict.txt")
    run(origin, "commit", "-q", "-m", "origin edits conflict.txt")
    write(local, "conflict.txt", "local version\n")
    run(local, "add", "conflict.txt")
    run(local, "commit", "-q", "-m", "local edits conflict.txt", "--no-verify")
    head_before = run(local, "rev-parse", "HEAD").stdout.strip()

    r = cmf.sync(local, "main")
    check("conflict: status BLOCKED_CONFLICT", r["status"] == "BLOCKED_CONFLICT", repr(r))
    check("conflict: MERGE_HEAD cleaned up (abort ran)",
          run(local, "rev-parse", "-q", "--verify", "MERGE_HEAD", check_rc=False).returncode != 0)
    check("conflict: HEAD unchanged after abort",
          run(local, "rev-parse", "HEAD").stdout.strip() == head_before)
    check("conflict: working tree has no conflict markers left",
          "<<<<<<<" not in open(os.path.join(local, "conflict.txt")).read())
    check("conflict: index clean after abort",
          run(local, "diff", "--cached", "--name-only").stdout.strip() == "")

# --- another session's content already staged -> refuse before touching anything ---
with tempfile.TemporaryDirectory() as td:
    local, origin = make_pair(td)
    for i in range(2):
        commit(origin, "origin commit %d" % i, fname="p%d.txt" % i)
    write(local, "someone-elses-work.txt", "staged by another session\n")
    run(local, "add", "someone-elses-work.txt")
    head_before = run(local, "rev-parse", "HEAD").stdout.strip()

    r = cmf.sync(local, "main")
    check("staged-guard: status BLOCKED_STAGED", r["status"] == "BLOCKED_STAGED", repr(r))
    check("staged-guard: names the staged path", "someone-elses-work.txt" in r["detail"], repr(r))
    check("staged-guard: HEAD unchanged (never even fetched/merged)",
          run(local, "rev-parse", "HEAD").stdout.strip() == head_before)
    check("staged-guard: the stranger's staged content is still staged, untouched",
          "someone-elses-work.txt" in run(local, "diff", "--cached", "--name-only").stdout)

# --- not a git repo at all -----------------------------------------------------------
with tempfile.TemporaryDirectory() as td:
    not_repo = os.path.join(td, "not-a-repo")
    os.makedirs(not_repo)
    r = cmf.sync(not_repo, "main")
    check("not-a-repo: status ERROR", r["status"] == "ERROR", repr(r))

# --- main() exit codes ---------------------------------------------------------------
with tempfile.TemporaryDirectory() as td:
    local, origin = make_pair(td)
    rc = cmf.main(["--repo", local, "--canonical", "main"])
    check("main: exit 0 on NOOP_CLEAN", rc == 0, "got %r" % rc)

with tempfile.TemporaryDirectory() as td:
    local, origin = make_pair(td)
    commit(origin, "one more", fname="q.txt")
    rc = cmf.main(["--repo", local, "--canonical", "main"])
    check("main: exit 0 on MERGED", rc == 0, "got %r" % rc)

with tempfile.TemporaryDirectory() as td:
    local, origin = make_pair(td)
    write(local, "x.txt", "uncommitted\n")
    run(local, "add", "x.txt")
    rc = cmf.main(["--repo", local, "--canonical", "main"])
    check("main: exit 1 on BLOCKED_STAGED", rc == 1, "got %r" % rc)

passed = sum(1 for ok, _ in _results if ok)
print("\ncheckout-merge-forward tests: %d/%d passed" % (passed, len(_results)))
sys.exit(0 if passed == len(_results) else 1)
