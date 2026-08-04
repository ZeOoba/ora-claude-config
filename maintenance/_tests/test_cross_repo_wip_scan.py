#!/usr/bin/env python3
"""Tests for cross-repo-wip-scan.py -- the read-only, periodic check-in that
reports how long uncommitted work has been sitting in each known local repo
(2026-07-26, follow-on to a repo-housekeeping session that found ~21
uncommitted items nobody had been watching age).

Run: python _tests/test_cross_repo_wip_scan.py   (exit 0 = pass)
Uses real throwaway `git init` fixture repos in tempdirs -- exercises the
real `git status --short` subprocess path, not a mock.
"""
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import time

HOOKS_LIB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "..", "hooks", "tests", "lib")
sys.path.insert(0, os.path.abspath(HOOKS_LIB))
import gitfixture  # noqa: E402  (shared repo fixture -- open-items-tracker.md#OI-061)

MAINT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location(
    "wipscan", os.path.join(MAINT, "cross-repo-wip-scan.py"))
wipscan = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wipscan)

results = []


def expect(label, cond, detail=""):
    results.append((bool(cond), label))
    if not cond:
        print("  FAIL: %s %s" % (label, detail))


def run(cmd, cwd):
    subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=True)


def init_repo(path):
    """Shared template-and-copy fixture (open-items-tracker.md#OI-061), relocated to
    the caller's chosen `path` so every call site below -- and the
    tempfile.TemporaryDirectory() scope each sits in -- stays unchanged. Same shape as
    the hand-rolled version this replaces: init + user config, no commits. The 3 git
    spawns are now paid ONCE per process instead of on each of this file's 7 calls.

    blank_repo()'s user.email/user.name ("t@t.t"/"t") differ from the original's
    ("test@example.com"/"Test"); no assertion in this file inspects commit author
    identity, so that is not a behaviour change for anything actually tested here --
    every test only checks scan_repo()'s uncommitted_count/oldest_age_hours/stale
    output, never commit metadata.

    `path` must not already exist -- shutil.move() would nest the fixture INSIDE it
    instead of renaming onto it. Every caller passes a not-yet-existing subdirectory
    of a freshly made TemporaryDirectory, so this holds.
    """
    shutil.move(gitfixture.blank_repo(), path)
    return path


# --- missing repo (no .git at all) --------------------------------------------------
with tempfile.TemporaryDirectory() as td:
    not_a_repo = os.path.join(td, "not-a-repo")
    os.makedirs(not_a_repo)
    r = wipscan.scan_repo(not_a_repo)
    expect("missing: git_repo False", r["git_repo"] is False)
    expect("missing: stale True (missing is always surfaced)", r["stale"] is True)
    expect("missing: missing flag set", r.get("missing") is True)

# --- clean repo (no uncommitted changes) --------------------------------------------
with tempfile.TemporaryDirectory() as td:
    clean_repo = init_repo(os.path.join(td, "clean-repo"))
    with open(os.path.join(clean_repo, "a.txt"), "w") as f:
        f.write("hello\n")
    run(["git", "add", "a.txt"], clean_repo)
    run(["git", "commit", "-q", "-m", "seed"], clean_repo)
    r = wipscan.scan_repo(clean_repo)
    expect("clean: uncommitted_count 0", r["uncommitted_count"] == 0, "got %r" % r)
    expect("clean: not stale", r["stale"] is False, "got %r" % r)
    expect("clean: oldest_age_hours is None", r["oldest_age_hours"] is None, "got %r" % r)

# --- fresh uncommitted file: WIP, but under the staleness threshold ------------------
with tempfile.TemporaryDirectory() as td:
    fresh_repo = init_repo(os.path.join(td, "fresh-repo"))
    with open(os.path.join(fresh_repo, "new.txt"), "w") as f:
        f.write("new\n")
    r = wipscan.scan_repo(fresh_repo)
    expect("fresh: uncommitted_count 1", r["uncommitted_count"] == 1, "got %r" % r)
    expect("fresh: oldest_age_hours near 0", r["oldest_age_hours"] is not None
           and r["oldest_age_hours"] < 1.0, "got %r" % r)
    expect("fresh: NOT stale (under threshold)", r["stale"] is False, "got %r" % r)

# --- old uncommitted file: WIP, over the staleness threshold -> STALE ----------------
with tempfile.TemporaryDirectory() as td:
    stale_repo = init_repo(os.path.join(td, "stale-repo"))
    old_path = os.path.join(stale_repo, "old.txt")
    with open(old_path, "w") as f:
        f.write("old\n")
    old_ts = time.time() - (72 * 3600)  # 72h ago, past the 48h default threshold
    os.utime(old_path, (old_ts, old_ts))
    r = wipscan.scan_repo(stale_repo)
    expect("stale: uncommitted_count 1", r["uncommitted_count"] == 1, "got %r" % r)
    expect("stale: oldest_age_hours ~72", r["oldest_age_hours"] is not None
           and 70 <= r["oldest_age_hours"] <= 74, "got %r" % r)
    expect("stale: IS stale (over threshold)", r["stale"] is True, "got %r" % r)

# --- deleted tracked file: counts toward uncommitted_count, excluded from age -------
with tempfile.TemporaryDirectory() as td:
    del_repo = init_repo(os.path.join(td, "del-repo"))
    tracked = os.path.join(del_repo, "tracked.txt")
    with open(tracked, "w") as f:
        f.write("will be deleted\n")
    run(["git", "add", "tracked.txt"], del_repo)
    run(["git", "commit", "-q", "-m", "seed"], del_repo)
    os.remove(tracked)
    r = wipscan.scan_repo(del_repo)
    expect("deleted: counted in uncommitted_count", r["uncommitted_count"] == 1, "got %r" % r)
    expect("deleted: does not crash, oldest_age_hours is None (nothing to stat)",
           r["oldest_age_hours"] is None, "got %r" % r)
    # An unmeasurable age is an INFERRED null (we couldn't look), not a VERIFIED one
    # (we looked and it's fine) -- same distinction as
    # feedback_verified_null_vs_inferred_null.md, applied here deliberately:
    # scan_repo() treats "can't measure" as stale/uncertain rather than silently
    # passing it as clean, so a deletion pending commit still surfaces for a human
    # to look at rather than being invisible to this scan.
    expect("deleted: STALE (unmeasurable age is treated as uncertain, not clean)",
           r["stale"] is True, "got %r" % r)

# --- `now` injection is honored (deterministic age math) ----------------------------
with tempfile.TemporaryDirectory() as td:
    inj_repo = init_repo(os.path.join(td, "inj-repo"))
    p = os.path.join(inj_repo, "x.txt")
    with open(p, "w") as f:
        f.write("x\n")
    ts = time.time() - 3600  # 1h ago
    os.utime(p, (ts, ts))
    fixed_now = ts + (10 * 3600)  # pretend "now" is 10h after the file's mtime
    r = wipscan.scan_repo(inj_repo, now=fixed_now)
    expect("now-injection: oldest_age_hours reflects injected now, not real time",
           r["oldest_age_hours"] is not None and 9.9 <= r["oldest_age_hours"] <= 10.1,
           "got %r" % r)

# --- scan_all() / any_stale() / format_report() over a mixed set --------------------
with tempfile.TemporaryDirectory() as td:
    c = init_repo(os.path.join(td, "c"))
    run(["git", "commit", "--allow-empty", "-q", "-m", "seed"], c)
    s = init_repo(os.path.join(td, "s"))
    op = os.path.join(s, "o.txt")
    with open(op, "w") as f:
        f.write("o\n")
    old_ts = time.time() - (200 * 3600)
    os.utime(op, (old_ts, old_ts))
    m = os.path.join(td, "does-not-exist")
    os.makedirs(m)

    all_results = wipscan.scan_all([c, s, m])
    expect("scan_all: one result per repo, in order",
           [r["path"] for r in all_results] == [c, s, m], "got %r" % [r["path"] for r in all_results])
    expect("any_stale: True when the set includes a stale + a missing repo",
           wipscan.any_stale(all_results) is True)

    report = wipscan.format_report(all_results)
    expect("format_report: clean repo reported as clean", "clean    %s" % c in report, "got %r" % report)
    expect("format_report: stale repo flagged with [ACTION] STALE", "[ACTION] STALE %s" % s in report,
           "got %r" % report)
    expect("format_report: missing repo flagged with [ACTION] MISSING", "[ACTION] MISSING %s" % m in report,
           "got %r" % report)

    wipscan.KNOWN_REPOS_OVERRIDE = [c, s, m]
    try:
        rc = wipscan.main()
    finally:
        wipscan.KNOWN_REPOS_OVERRIDE = None
    expect("main: exit 1 when any repo is stale/missing", rc == 1, "got %r" % rc)

    wipscan.KNOWN_REPOS_OVERRIDE = [c]
    try:
        rc_clean = wipscan.main()
    finally:
        wipscan.KNOWN_REPOS_OVERRIDE = None
    expect("main: exit 0 when every scanned repo is clean", rc_clean == 0, "got %r" % rc_clean)

passed = sum(1 for ok, _ in results if ok)
print("cross-repo-wip-scan tests: %d/%d passed" % (passed, len(results)))
sys.exit(0 if passed == len(results) else 1)
