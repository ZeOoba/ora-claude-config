#!/usr/bin/env python3
"""cross-repo-wip-scan F-9 tests: per-repo behind threshold and the CLI
(--freshness-only, --repo, --fetch, no git status in freshness-only mode)

Run: python _tests/test_cross_repo_wip_scan_cli.py   (exit 0 = pass). Real git fixtures, no mocked git
(two seams monkeypatch wipscan internals to force a git failure / spy on a call)."""
import os
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _wipscan_fixtures import (  # noqa: E402
    OCC, SNAP, _commit_snap, _head, _json, _main_with, _scan_snap, _snap_doc, _write_snap,
    expect, finish, init_repo, make_origin_pair, run, snap_pair, wipscan)

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

# C3: --freshness-only never runs `git status` on the inspected checkout
with tempfile.TemporaryDirectory() as td:
    local, origin = snap_pair(td)
    real_status = wipscan._git_status_short
    calls = []

    def _status_spy(repo_path):
        calls.append(repo_path)
        return real_status(repo_path)

    wipscan._git_status_short = _status_spy
    try:
        rc = _main_with(["--freshness-only"], [local])
        expect("freshness-only: git status not run", calls == [] and rc == 0, repr((calls, rc)))
        rc = _main_with([], [local])
        expect("full scan: git status still runs", calls == [local], repr(calls))
    finally:
        wipscan._git_status_short = real_status

finish("cross-repo-wip-scan cli")
