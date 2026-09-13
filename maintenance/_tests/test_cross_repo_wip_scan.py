#!/usr/bin/env python3
"""Tests for cross-repo-wip-scan.py -- the read-only, periodic check-in that
reports how long uncommitted work has been sitting in each known local repo
(2026-07-26, follow-on to a repo-housekeeping session that found ~21
uncommitted items nobody had been watching age), plus the branch-drift check
added 2026-09-09 (open-items-tracker.md#OI-249) for repos with a declared
canonical branch.

Run: python _tests/test_cross_repo_wip_scan.py   (exit 0 = pass)
Uses real throwaway `git init` fixture repos in tempdirs -- exercises the
real `git status --short` subprocess path, not a mock. The branch-drift
tests additionally wire a real local "origin" remote (a second throwaway
repo, added via `git remote add` + `git fetch`) so `origin/<branch>`
genuinely resolves -- no mocked git, same reasoning as check-branch-point.py's
own test suite.
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

# --- branch-drift: repo with no canonical branch declared is never flagged ---------
with tempfile.TemporaryDirectory() as td:
    plain = init_repo(os.path.join(td, "plain"))
    run(["git", "checkout", "-q", "-b", "feature-x"], plain)
    with open(os.path.join(plain, "f.txt"), "w") as f:
        f.write("f\n")
    run(["git", "add", "f.txt"], plain)
    run(["git", "commit", "-q", "-m", "seed"], plain)
    r = wipscan.scan_repo(plain)
    expect("no canonical declared: branch_drift absent/falsy",
           not r.get("branch_drift"), "got %r" % r)
    expect("no canonical declared: not in format_report's BRANCH_DRIFT lines",
           "BRANCH_DRIFT" not in wipscan.format_report([r]), wipscan.format_report([r]))


def make_origin_pair(td, canonical="main"):
    """(local, origin) -- `local` has `origin` wired as a real remote, with
    `origin/<canonical>` fetched and resolvable. Both start on `canonical`
    with one shared commit."""
    origin = init_repo(os.path.join(td, "origin"))
    run(["git", "checkout", "-q", "-b", canonical], origin)
    with open(os.path.join(origin, "base.txt"), "w") as f:
        f.write("base\n")
    run(["git", "add", "base.txt"], origin)
    run(["git", "commit", "-q", "-m", "base"], origin)

    local = os.path.join(td, "local")
    subprocess.run(["git", "clone", "-q", origin, local], check=True,
                   capture_output=True, text=True)
    return local, origin


# --- branch-drift: on canonical, in sync -> not drift -------------------------------
with tempfile.TemporaryDirectory() as td:
    local, origin = make_origin_pair(td)
    wipscan.CANONICAL_BRANCH_OVERRIDE = {local: "main"}
    try:
        r = wipscan.scan_repo(local)
    finally:
        wipscan.CANONICAL_BRANCH_OVERRIDE = None
    expect("in-sync main: current_branch main", r.get("current_branch") == "main", repr(r))
    expect("in-sync main: 0 commits behind", r.get("commits_behind_canonical") == 0, repr(r))
    expect("in-sync main: NOT branch_drift", r.get("branch_drift") is False, repr(r))
    expect("in-sync main: no [ACTION] BRANCH_DRIFT line",
           "BRANCH_DRIFT" not in wipscan.format_report([r]), wipscan.format_report([r]))

# --- branch-drift: on canonical, but far behind -> drift (behind-count alone) -------
with tempfile.TemporaryDirectory() as td:
    local, origin = make_origin_pair(td)
    for i in range(wipscan.BRANCH_BEHIND_THRESHOLD):
        with open(os.path.join(origin, "o%d.txt" % i), "w") as f:
            f.write(str(i))
        run(["git", "add", "o%d.txt" % i], origin)
        run(["git", "commit", "-q", "-m", "origin commit %d" % i], origin)
    run(["git", "fetch", "-q", "origin"], local)
    wipscan.CANONICAL_BRANCH_OVERRIDE = {local: "main"}
    try:
        r = wipscan.scan_repo(local)
    finally:
        wipscan.CANONICAL_BRANCH_OVERRIDE = None
    expect("behind-threshold: on main (identity matches)", r.get("current_branch") == "main", repr(r))
    expect("behind-threshold: commits_behind_canonical == threshold",
           r.get("commits_behind_canonical") == wipscan.BRANCH_BEHIND_THRESHOLD, repr(r))
    expect("behind-threshold: IS branch_drift", r.get("branch_drift") is True, repr(r))
    rep = wipscan.format_report([r])
    expect("behind-threshold: report says 'as expected, but N behind'",
           "as expected, but %d commit(s) behind" % wipscan.BRANCH_BEHIND_THRESHOLD in rep, rep)

# --- branch-drift: off canonical entirely, 0 behind -> drift (identity alone) -------
with tempfile.TemporaryDirectory() as td:
    local, origin = make_origin_pair(td)
    run(["git", "checkout", "-q", "-b", "feat/some-long-lived-branch"], local)
    wipscan.CANONICAL_BRANCH_OVERRIDE = {local: "main"}
    try:
        r = wipscan.scan_repo(local)
    finally:
        wipscan.CANONICAL_BRANCH_OVERRIDE = None
    expect("off-branch: current_branch is the feature branch",
           r.get("current_branch") == "feat/some-long-lived-branch", repr(r))
    expect("off-branch: commits_behind_canonical 0 (nothing new upstream)",
           r.get("commits_behind_canonical") == 0, repr(r))
    expect("off-branch: IS branch_drift even with 0 behind (identity mismatch alone)",
           r.get("branch_drift") is True, repr(r))
    rep = wipscan.format_report([r])
    expect("off-branch: report says on 'X', expected 'main'",
           "on 'feat/some-long-lived-branch', expected 'main'" in rep, rep)

# --- branch-drift: origin/<canonical> does not resolve -> uncertain, not clean ------
with tempfile.TemporaryDirectory() as td:
    lone = init_repo(os.path.join(td, "lone"))
    with open(os.path.join(lone, "x.txt"), "w") as f:
        f.write("x\n")
    run(["git", "add", "x.txt"], lone)
    run(["git", "commit", "-q", "-m", "seed"], lone)
    # No remote named "origin" at all -- origin/main cannot resolve.
    wipscan.CANONICAL_BRANCH_OVERRIDE = {lone: "main"}
    try:
        r = wipscan.scan_repo(lone)
    finally:
        wipscan.CANONICAL_BRANCH_OVERRIDE = None
    expect("no-origin: branch_drift_error set", bool(r.get("branch_drift_error")), repr(r))
    expect("no-origin: branch_drift True (unmeasurable is uncertain, not clean)",
           r.get("branch_drift") is True, repr(r))
    expect("no-origin: commits_behind_canonical is None (never measured)",
           r.get("commits_behind_canonical") is None, repr(r))
    rep = wipscan.format_report([r])
    expect("no-origin: report says cannot determine drift",
           "cannot determine drift" in rep, rep)

# --- any_branch_drift() aggregation + main() exit code wiring -----------------------
with tempfile.TemporaryDirectory() as td:
    clean_local, _ = make_origin_pair(td)
    drifted_td = tempfile.mkdtemp(dir=td)
    drifted_local, drifted_origin = make_origin_pair(drifted_td)
    run(["git", "checkout", "-q", "-b", "feature-y"], drifted_local)

    clean_r = wipscan.scan_repo(clean_local)
    clean_r["path"] = clean_local  # already true, kept explicit for clarity
    override_map = {clean_local: "main", drifted_local: "main"}
    wipscan.CANONICAL_BRANCH_OVERRIDE = override_map
    try:
        all_r = wipscan.scan_all([clean_local, drifted_local])
    finally:
        wipscan.CANONICAL_BRANCH_OVERRIDE = None
    expect("any_branch_drift: False over an all-clean set",
           wipscan.any_branch_drift([all_r[0]]) is False, repr(all_r[0]))
    expect("any_branch_drift: True once one repo drifts",
           wipscan.any_branch_drift(all_r) is True, repr(all_r))

    wipscan.KNOWN_REPOS_OVERRIDE = [drifted_local]
    wipscan.CANONICAL_BRANCH_OVERRIDE = {drifted_local: "main"}
    try:
        rc = wipscan.main()
    finally:
        wipscan.KNOWN_REPOS_OVERRIDE = None
        wipscan.CANONICAL_BRANCH_OVERRIDE = None
    expect("main: exit 1 when a repo has branch_drift even if not WIP-stale",
           rc == 1, "got %r" % rc)

# --- CORRECTOR_STUCK: checkout-merge-forward.py's consecutiveUnsynced streak --------
# (2026-09-12: the daily corrector returns BLOCKED_* silently by design; without
# a streak check nothing notices it has not landed a merge in weeks.)
import json as _json


def _write_state(path, obj):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(obj if isinstance(obj, str) else _json.dumps(obj))


def _scan_with_state(repo, state_path):
    wipscan.CORRECTOR_STATE_OVERRIDE = {repo: state_path}
    try:
        return wipscan.scan_repo(repo)
    finally:
        wipscan.CORRECTOR_STATE_OVERRIDE = None


import datetime as _dt
FRESH = _dt.datetime.now().astimezone().isoformat(timespec="seconds")


with tempfile.TemporaryDirectory() as td:
    repo = init_repo(os.path.join(td, "r"))
    sp = os.path.join(td, "state.json")
    N = wipscan.CORRECTOR_UNSYNCED_ESCALATE_RUNS

    _write_state(sp, {"lastRun": FRESH, "status": "BLOCKED_DIRTY_OVERLAP",
                      "consecutiveUnsynced": N - 1, "unsyncedSince": "2026-09-06T16:45:00-04:00",
                      "blockedPaths": ["a", "b"]})
    r = _scan_with_state(repo, sp)
    expect("corrector: below threshold -> not stuck", r.get("corrector_stuck") is False, repr(r))
    expect("corrector: streak surfaced", r.get("corrector_consecutive_unsynced") == N - 1, repr(r))

    _write_state(sp, {"lastRun": FRESH, "status": "BLOCKED_DIRTY_OVERLAP",
                      "consecutiveUnsynced": N, "unsyncedSince": "2026-09-05T16:45:00-04:00",
                      "blockedPaths": ["a", "b"]})
    r = _scan_with_state(repo, sp)
    expect("corrector: at threshold -> stuck", r.get("corrector_stuck") is True, repr(r))
    rep = wipscan.format_report([r])
    expect("corrector: report line names streak, since, and blocked-path count",
           "CORRECTOR_STUCK" in rep and ("%d consecutive" % N) in rep
           and "2026-09-05" in rep and "2 blocked path" in rep, rep)
    expect("any_corrector_stuck: True", wipscan.any_corrector_stuck([r]) is True)

    _write_state(sp, {"lastRun": FRESH, "status": "NOOP_CLEAN", "consecutiveUnsynced": 0})
    r = _scan_with_state(repo, sp)
    expect("corrector: synced -> not stuck, no report line",
           r.get("corrector_stuck") is False and "CORRECTOR" not in wipscan.format_report([r]),
           repr(r))

    os.remove(sp)
    r = _scan_with_state(repo, sp)
    expect("corrector: missing state file -> stuck (unmeasurable is not clean)",
           r.get("corrector_stuck") is True and r.get("corrector_error"), repr(r))
    expect("corrector: missing file report says cannot determine",
           "cannot determine" in wipscan.format_report([r]), wipscan.format_report([r]))

    _write_state(sp, {"lastRun": "x", "status": "BLOCKED_DIRTY_OVERLAP"})  # legacy shape
    r = _scan_with_state(repo, sp)
    expect("corrector: legacy state without counter -> stuck with error",
           r.get("corrector_stuck") is True and "consecutiveUnsynced" in (r.get("corrector_error") or ""),
           repr(r))

    _write_state(sp, "not json{")
    r = _scan_with_state(repo, sp)
    expect("corrector: corrupt state -> stuck with error",
           r.get("corrector_stuck") is True and r.get("corrector_error"), repr(r))

    plain = wipscan.scan_repo(repo)
    expect("corrector: repo with no corrector mapping carries no corrector keys",
           "corrector_stuck" not in plain, repr(plain))

    _write_state(sp, {"lastRun": FRESH, "status": "BLOCKED_STAGED", "consecutiveUnsynced": N + 3,
                      "unsyncedSince": "2026-09-01", "blockedPaths": None})
    wipscan.KNOWN_REPOS_OVERRIDE = [repo]
    wipscan.CORRECTOR_STATE_OVERRIDE = {repo: sp}
    try:
        rc = wipscan.main()
    finally:
        wipscan.KNOWN_REPOS_OVERRIDE = None
        wipscan.CORRECTOR_STATE_OVERRIDE = None
    expect("main: exit 1 when corrector stuck even if repo clean", rc == 1, "got %r" % rc)

# --- CORRECTOR_STUCK: a corrector that stopped RUNNING freezes its streak -----------
# (review finding 2026-09-12: disabled task / repeated BLOCKED_CLAIMED / dying before
# STEP 1 leaves consecutiveUnsynced frozen below threshold -> weekly scan clean forever.)
with tempfile.TemporaryDirectory() as td:
    repo = init_repo(os.path.join(td, "r"))
    sp = os.path.join(td, "state.json")
    H = wipscan.CORRECTOR_STALE_HOURS
    expect("corrector-stale: threshold is 72h", H == 72, repr(H))

    old = (_dt.datetime.now().astimezone() - _dt.timedelta(hours=H + 1)).isoformat(timespec="seconds")
    _write_state(sp, {"lastRun": old, "status": "NOOP_CLEAN", "consecutiveUnsynced": 0})
    r = _scan_with_state(repo, sp)
    expect("corrector-stale: lastRun older than threshold -> stuck even with streak 0",
           r.get("corrector_stuck") is True and "has not run" in (r.get("corrector_error") or ""),
           repr(r))
    expect("corrector-stale: report names last run",
           old[:10] in wipscan.format_report([r]), wipscan.format_report([r]))

    recent = (_dt.datetime.now().astimezone() - _dt.timedelta(hours=H - 1)).isoformat(timespec="seconds")
    _write_state(sp, {"lastRun": recent, "status": "BLOCKED_STAGED", "consecutiveUnsynced": 2})
    r = _scan_with_state(repo, sp)
    expect("corrector-stale: lastRun inside threshold -> not stuck",
           r.get("corrector_stuck") is False, repr(r))

    _write_state(sp, {"lastRun": "not-a-date", "status": "NOOP_CLEAN", "consecutiveUnsynced": 0})
    r = _scan_with_state(repo, sp)
    expect("corrector-stale: unparseable lastRun -> stuck (unmeasurable)",
           r.get("corrector_stuck") is True and "lastRun" in (r.get("corrector_error") or ""),
           repr(r))

    _write_state(sp, {"lastRun": "2026-09-12T16:45:00", "status": "NOOP_CLEAN",
                      "consecutiveUnsynced": 0})  # naive timestamp -> treated as local time
    r = wipscan._corrector_streak(sp, now=_dt.datetime(2026, 9, 13, 10, 0))
    expect("corrector-stale: naive lastRun compared as local time, not a crash",
           r.get("corrector_stuck") is False, repr(r))

    _write_state(sp, {"lastRun": FRESH, "status": "BLOCKED_STAGED", "consecutiveUnsynced": 9,
                      "unsyncedSince": "2026-09-01", "blockedPaths": None})
    rep = wipscan.format_report([_scan_with_state(repo, sp)])
    expect("corrector: BLOCKED_STAGED (no path list) omits the '?' path count",
           "?" not in rep and "CORRECTOR_STUCK" in rep, rep)

passed = sum(1 for ok, _ in results if ok)
print("cross-repo-wip-scan tests: %d/%d passed" % (passed, len(results)))
sys.exit(0 if passed == len(results) else 1)
