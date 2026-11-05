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
    # Corrector went weekly (Fri) 2026-09-22: one cycle + 24h grace. At 72h it would read
    # as "has not run" 4 days out of every 7.
    expect("corrector-stale: threshold is 192h (weekly + 24h)", H == 192, repr(H))
    expect("corrector-stuck: escalates after 1 unsynced weekly run (7d, as before)",
           wipscan.CORRECTOR_UNSYNCED_ESCALATE_RUNS == 1, repr(wipscan.CORRECTOR_UNSYNCED_ESCALATE_RUNS))

    old = (_dt.datetime.now().astimezone() - _dt.timedelta(hours=H + 1)).isoformat(timespec="seconds")
    _write_state(sp, {"lastRun": old, "status": "NOOP_CLEAN", "consecutiveUnsynced": 0})
    r = _scan_with_state(repo, sp)
    expect("corrector-stale: lastRun older than threshold -> stuck even with streak 0",
           r.get("corrector_stuck") is True and "has not run" in (r.get("corrector_error") or ""),
           repr(r))
    expect("corrector-stale: report names last run",
           old[:10] in wipscan.format_report([r]), wipscan.format_report([r]))

    recent = (_dt.datetime.now().astimezone() - _dt.timedelta(hours=H - 1)).isoformat(timespec="seconds")
    # streak held below the escalation threshold so this isolates the RECENCY check
    _write_state(sp, {"lastRun": recent, "status": "BLOCKED_STAGED",
                      "consecutiveUnsynced": wipscan.CORRECTOR_UNSYNCED_ESCALATE_RUNS - 1})
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

# --- OCC shared-checkout freshness (2026-11-05, business-loops review F-9) ----------
# The shared oxford-command-center checkout sat on data/snapshot-2026-10-06 for ~4
# weeks, 103 commits behind origin/main; every reader of its portfolio.json read
# 2026-10-06 data while main held three newer snapshots. Nothing alarmed.
SNAP = "data/snapshots/portfolio.json"
OCC = r"C:\Users\Owner\oxford-command-center"


def _snap_doc(generated_at, extra="x"):
    return _json.dumps({"meta": {"asOf": "2026-10-23", "generatedAt": generated_at},
                        "leases": [extra]}, indent=1) + "\n"


def _write_snap(repo, doc):
    os.makedirs(os.path.join(repo, "data", "snapshots"), exist_ok=True)
    with open(os.path.join(repo, *SNAP.split("/")), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(doc)


def _commit_snap(repo, doc, msg="snapshot"):
    _write_snap(repo, doc)
    run(["git", "add", SNAP], repo)
    run(["git", "commit", "-q", "-m", msg], repo)


def snap_pair(td, generated_at="2026-10-26T14:52:49.296Z"):
    local, origin = make_origin_pair(td)
    _commit_snap(origin, _snap_doc(generated_at))
    run(["git", "fetch", "-q", "origin"], local)
    run(["git", "merge", "-q", "--ff-only", "origin/main"], local)
    return local, origin


def _scan_snap(local, **kw):
    wipscan.CANONICAL_BRANCH_OVERRIDE = {local: "main"}
    wipscan.SNAPSHOT_FRESHNESS_OVERRIDE = {local: SNAP}
    try:
        return wipscan.scan_repo(local, **kw)
    finally:
        wipscan.CANONICAL_BRANCH_OVERRIDE = None
        wipscan.SNAPSHOT_FRESHNESS_OVERRIDE = None


def _main_with(argv, repos, snap=True, canon=True):
    wipscan.KNOWN_REPOS_OVERRIDE = list(repos)
    wipscan.CANONICAL_BRANCH_OVERRIDE = {r: "main" for r in repos} if canon else {}
    wipscan.SNAPSHOT_FRESHNESS_OVERRIDE = {r: SNAP for r in repos} if snap else {}
    try:
        return wipscan.main(argv)
    finally:
        wipscan.KNOWN_REPOS_OVERRIDE = None
        wipscan.CANONICAL_BRANCH_OVERRIDE = None
        wipscan.SNAPSHOT_FRESHNESS_OVERRIDE = None


def _head(repo):
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True,
                          text=True).stdout.strip()


# config: OCC is declared, with a justified per-repo threshold and its snapshot path
expect("occ: canonical branch main", wipscan.DEFAULT_CANONICAL_BRANCH.get(OCC) == "main",
       repr(wipscan.DEFAULT_CANONICAL_BRANCH))
expect("occ: snapshot path declared",
       getattr(wipscan, "DEFAULT_SNAPSHOT_FRESHNESS", {}).get(OCC) == SNAP,
       repr(getattr(wipscan, "DEFAULT_SNAPSHOT_FRESHNESS", None)))
expect("occ: per-repo behind threshold 25 (~1 week of OCC main traffic)",
       wipscan.behind_threshold_for(OCC) == 25, repr(wipscan.behind_threshold_for(OCC)))
expect("~/.claude keeps the global threshold",
       wipscan.behind_threshold_for(r"C:\Users\Owner\.claude") == wipscan.BRANCH_BEHIND_THRESHOLD)
expect("map lookups are path-spelling insensitive (forward slashes, case, trailing sep)",
       wipscan.canonical_branch_for("c:/users/owner/oxford-command-center") == "main"
       and wipscan.snapshot_path_for("C:/Users/Owner/oxford-command-center/") == SNAP)

# in sync: same generatedAt, same content -> not stale
with tempfile.TemporaryDirectory() as td:
    local, origin = snap_pair(td)
    r = _scan_snap(local)
    expect("snap in-sync: snapshot_stale False", r.get("snapshot_stale") is False, repr(r))
    expect("snap in-sync: content matches origin",
           r.get("snapshot_content_matches_origin") is True, repr(r))
    expect("snap in-sync: no SNAPSHOT_STALE line",
           "SNAPSHOT_STALE" not in wipscan.format_report([r]), wipscan.format_report([r]))
    expect("snap in-sync: freshness-only main exits 0",
           _main_with(["--freshness-only"], [local]) == 0)

# the incident shape: origin/main has a newer snapshot, the checkout was never advanced
with tempfile.TemporaryDirectory() as td:
    local, origin = snap_pair(td, "2026-10-06T12:00:00.000Z")
    _commit_snap(origin, _snap_doc("2026-11-02T12:00:00.000Z", "y"), "newer snapshot")
    run(["git", "fetch", "-q", "origin"], local)
    r = _scan_snap(local)
    expect("snap trailing: snapshot_stale True", r.get("snapshot_stale") is True, repr(r))
    expect("snap trailing: both generatedAt surfaced",
           str(r.get("snapshot_local_generated_at")).startswith("2026-10-06")
           and str(r.get("snapshot_origin_generated_at")).startswith("2026-11-02"), repr(r))
    expect("snap trailing: lag 27 days in hours", r.get("snapshot_lag_hours") == 648.0, repr(r))
    rep = wipscan.format_report([r])
    expect("snap trailing: [ACTION] SNAPSHOT_STALE line names both stamps",
           "[ACTION] SNAPSHOT_STALE" in rep and "2026-10-06" in rep and "2026-11-02" in rep, rep)
    expect("any_snapshot_stale True", wipscan.any_snapshot_stale([r]) is True)
    expect("snap trailing: main exits 1", _main_with([], [local]) == 1)
    expect("snap trailing: freshness-only main exits 1",
           _main_with(["--freshness-only"], [local]) == 1)

# same generatedAt but different content (e.g. a redaction commit that kept the stamp)
with tempfile.TemporaryDirectory() as td:
    local, origin = snap_pair(td)
    _commit_snap(origin, _snap_doc("2026-10-26T14:52:49.296Z", "redacted"), "redact")
    run(["git", "fetch", "-q", "origin"], local)
    r = _scan_snap(local)
    expect("snap same-stamp diff content: stale", r.get("snapshot_stale") is True, repr(r))
    expect("snap same-stamp diff content: content_matches False",
           r.get("snapshot_content_matches_origin") is False, repr(r))
    expect("snap same-stamp diff content: report says content differs",
           "content differs" in wipscan.format_report([r]), wipscan.format_report([r]))

# CRLF working tree (core.autocrlf=true, as on the live OCC checkout) is NOT a content diff
with tempfile.TemporaryDirectory() as td:
    local, origin = snap_pair(td)
    run(["git", "config", "core.autocrlf", "true"], local)
    with open(os.path.join(local, *SNAP.split("/")), "w", encoding="utf-8", newline="\r\n") as fh:
        fh.write(_snap_doc("2026-10-26T14:52:49.296Z"))
    r = _scan_snap(local)
    expect("snap CRLF checkout: content matches (filters applied)",
           r.get("snapshot_content_matches_origin") is True
           and r.get("snapshot_stale") is False, repr(r))

# local working tree NEWER than origin (an uncommitted local extract) -> not stale
with tempfile.TemporaryDirectory() as td:
    local, origin = snap_pair(td)
    _write_snap(local, _snap_doc("2026-11-04T09:00:00.000Z", "local"))
    r = _scan_snap(local)
    expect("snap local newer: not stale", r.get("snapshot_stale") is False, repr(r))
    expect("snap local newer: flagged local_newer", r.get("snapshot_local_newer") is True, repr(r))

# unmeasurable -> stale with an error, never a silent clean
with tempfile.TemporaryDirectory() as td:
    local, origin = snap_pair(td)
    os.remove(os.path.join(local, *SNAP.split("/")))
    r = _scan_snap(local)
    expect("snap missing locally: stale + error", r.get("snapshot_stale") is True
           and "local" in (r.get("snapshot_error") or ""), repr(r))
    expect("snap missing: report says cannot determine",
           "cannot determine" in wipscan.format_report([r]), wipscan.format_report([r]))

    _write_snap(local, "not json{")
    r = _scan_snap(local)
    expect("snap unparseable locally: stale + error", r.get("snapshot_stale") is True
           and r.get("snapshot_error"), repr(r))

    _write_snap(local, _json.dumps({"meta": {"asOf": "2026-10-23"}}))
    r = _scan_snap(local)
    expect("snap no generatedAt: stale + error", r.get("snapshot_stale") is True
           and "generatedAt" in (r.get("snapshot_error") or ""), repr(r))

    _write_snap(local, _snap_doc("yesterday-ish"))
    r = _scan_snap(local)
    expect("snap unparseable generatedAt: stale + error", r.get("snapshot_stale") is True
           and "generatedAt" in (r.get("snapshot_error") or ""), repr(r))

    _write_snap(local, _snap_doc("2026-10-26T14:52:49"))   # naive vs aware: no crash
    r = _scan_snap(local)
    expect("snap naive generatedAt: stale + error, no crash", r.get("snapshot_stale") is True
           and r.get("snapshot_error"), repr(r))

with tempfile.TemporaryDirectory() as td:
    local, origin = make_origin_pair(td)       # origin has no snapshot at all
    _write_snap(local, _snap_doc("2026-10-26T14:52:49.296Z"))
    r = _scan_snap(local)
    expect("snap absent on origin/main: stale + error", r.get("snapshot_stale") is True
           and "origin/main" in (r.get("snapshot_error") or ""), repr(r))

with tempfile.TemporaryDirectory() as td:
    lone = init_repo(os.path.join(td, "lone"))
    _commit_snap(lone, _snap_doc("2026-10-26T14:52:49.296Z"))
    r = _scan_snap(lone)
    expect("snap with no origin ref: stale + error", r.get("snapshot_stale") is True
           and r.get("snapshot_error"), repr(r))

# repos without a snapshot declaration carry no snapshot keys
with tempfile.TemporaryDirectory() as td:
    local, origin = snap_pair(td)
    r = wipscan.scan_repo(local)
    expect("no snapshot declared: no snapshot keys", "snapshot_stale" not in r, repr(r))

# per-repo behind threshold: below it on main is not drift, at it is
with tempfile.TemporaryDirectory() as td:
    local, origin = snap_pair(td)
    for i in range(3):
        run(["git", "commit", "--allow-empty", "-q", "-m", "o%d" % i], origin)
    run(["git", "fetch", "-q", "origin"], local)
    wipscan.BEHIND_THRESHOLD_OVERRIDE = {local: 4}
    try:
        r = _scan_snap(local)
        expect("per-repo threshold: 3 behind < 4 -> no drift",
               r.get("branch_drift") is False and r.get("behind_threshold") == 4, repr(r))
        run(["git", "commit", "--allow-empty", "-q", "-m", "o3"], origin)
        run(["git", "fetch", "-q", "origin"], local)
        r = _scan_snap(local)
        expect("per-repo threshold: 4 behind -> drift", r.get("branch_drift") is True, repr(r))
        expect("per-repo threshold: report quotes the repo's own threshold",
               "(>= 4 threshold)" in wipscan.format_report([r]), wipscan.format_report([r]))
    finally:
        wipscan.BEHIND_THRESHOLD_OVERRIDE = None

# --freshness-only: WIP aging alone does not fail the probe; branch drift does
with tempfile.TemporaryDirectory() as td:
    local, origin = snap_pair(td)
    junk = os.path.join(local, "old-wip.txt")
    with open(junk, "w") as fh:
        fh.write("wip\n")
    old_ts = time.time() - 100 * 3600
    os.utime(junk, (old_ts, old_ts))
    expect("freshness-only: WIP-stale alone -> exit 0",
           _main_with(["--freshness-only"], [local]) == 0)
    expect("full scan: same repo -> exit 1 (WIP stale)", _main_with([], [local]) == 1)
    run(["git", "checkout", "-q", "-b", "data/snapshot-2026-10-06"], local)
    expect("freshness-only: off main -> exit 1",
           _main_with(["--freshness-only"], [local]) == 1)

# --repo: selects configured repos only; an unknown path fails closed (exit 2)
with tempfile.TemporaryDirectory() as td:
    a_td, b_td = tempfile.mkdtemp(dir=td), tempfile.mkdtemp(dir=td)
    a, _ = snap_pair(a_td)
    b, _ = snap_pair(b_td)
    run(["git", "checkout", "-q", "-b", "feature-z"], b)
    expect("--repo selects only the named repo (b drifts, a scanned alone -> 0)",
           _main_with(["--repo", a, "--freshness-only"], [a, b]) == 0)
    expect("--repo forward-slash spelling resolves to the configured key",
           _main_with(["--repo", b.replace("\\", "/"), "--freshness-only"], [a, b]) == 1)
    expect("--repo unknown path -> exit 2 (never a silent pass)",
           _main_with(["--repo", os.path.join(td, "nope"), "--freshness-only"], [a, b]) == 2)
    expect("--freshness-only on a repo with neither check declared -> exit 2",
           _main_with(["--repo", a, "--freshness-only"], [a], snap=False, canon=False) == 2)

# --fetch: refreshes origin/<canonical> first, so a newer snapshot the checkout never
# fetched is still caught; HEAD, branch and working tree are never touched
with tempfile.TemporaryDirectory() as td:
    local, origin = snap_pair(td, "2026-10-06T12:00:00.000Z")
    _commit_snap(origin, _snap_doc("2026-11-02T12:00:00.000Z", "y"), "newer snapshot")
    head_before = _head(local)
    expect("no --fetch: unfetched newer snapshot is not visible (documented limit)",
           _main_with(["--freshness-only"], [local]) == 0)
    expect("--fetch: newer snapshot caught -> exit 1",
           _main_with(["--freshness-only", "--fetch"], [local]) == 1)
    branch_after = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=local,
                                  capture_output=True, text=True).stdout.strip()
    expect("--fetch never moves HEAD or the branch (no pull/merge/reset)",
           _head(local) == head_before and branch_after == "main")
    expect("--fetch leaves the working-tree snapshot untouched",
           "2026-10-06" in open(os.path.join(local, *SNAP.split("/")), encoding="utf-8").read())

# a failing fetch is surfaced, never treated as clean
with tempfile.TemporaryDirectory() as td:
    local, origin = snap_pair(td)
    run(["git", "remote", "set-url", "origin", os.path.join(td, "gone")], local)
    wipscan.CANONICAL_BRANCH_OVERRIDE = {local: "main"}
    wipscan.SNAPSHOT_FRESHNESS_OVERRIDE = {local: SNAP}
    try:
        r = wipscan.scan_repo(local, fetch=True)
    finally:
        wipscan.CANONICAL_BRANCH_OVERRIDE = None
        wipscan.SNAPSHOT_FRESHNESS_OVERRIDE = None
    expect("--fetch failure: fetch_error recorded", bool(r.get("fetch_error")), repr(r))
    expect("--fetch failure: report has [ACTION] FETCH_FAILED",
           "[ACTION] FETCH_FAILED" in wipscan.format_report([r]), wipscan.format_report([r]))
    expect("--fetch failure: freshness-only exit 1 (unverified is not clean)",
           _main_with(["--freshness-only", "--fetch"], [local]) == 1)

passed = sum(1 for ok, _ in results if ok)
print("cross-repo-wip-scan tests: %d/%d passed" % (passed, len(results)))
sys.exit(0 if passed == len(results) else 1)
