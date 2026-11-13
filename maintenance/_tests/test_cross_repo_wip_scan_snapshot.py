#!/usr/bin/env python3
"""cross-repo-wip-scan F-9 tests: OCC portfolio.json SNAPSHOT_STALE semantics
(config, trailing/same-stamp/CRLF/newer/unmeasurable, local-patch carve-out and its
REFUTE rounds 1-3)

Run: python _tests/test_cross_repo_wip_scan_snapshot.py   (exit 0 = pass). Real git fixtures, no mocked git
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

# --- REFUTE follow-ups (2026-11-05) -------------------------------------------------
# L1: an in-place local patch that keeps generatedAt (ar-import-headless.ts patchSnapshot)
# is a LOCAL modification, not "main replaced these bytes" -- unless main ALSO moved.
with tempfile.TemporaryDirectory() as td:
    local, origin = snap_pair(td)
    _write_snap(local, _snap_doc("2026-10-26T14:52:49.296Z", "ar-patched"))
    r = _scan_snap(local)
    expect("local patch, same stamp, HEAD==origin: NOT stale", r.get("snapshot_stale") is False, repr(r))
    expect("local patch: flagged snapshot_locally_modified",
           r.get("snapshot_locally_modified") is True, repr(r))
    expect("local patch: freshness-only exit 0", _main_with(["--freshness-only"], [local]) == 0)

    _commit_snap(origin, _snap_doc("2026-10-26T14:52:49.296Z", "redacted"), "redact")
    run(["git", "fetch", "-q", "origin"], local)
    r = _scan_snap(local)
    expect("local patch AND main moved bytes at same stamp: stale",
           r.get("snapshot_stale") is True and not r.get("snapshot_locally_modified"), repr(r))

# C2: a hash failure at equal stamps is unmeasurable -> stale with error
with tempfile.TemporaryDirectory() as td:
    local, origin = snap_pair(td)
    real_git = wipscan._git

    def _git_hash_fails(args, repo_path):
        if "hash-object" in args:
            return 128, ""
        return real_git(args, repo_path)

    wipscan._git = _git_hash_fails
    try:
        r = _scan_snap(local)
    finally:
        wipscan._git = real_git
    expect("hash-object failure at equal stamps: stale + error",
           r.get("snapshot_stale") is True and "hash" in (r.get("snapshot_error") or ""), repr(r))

# REFUTE round 2: a working tree holding an OLDER committed version at the same stamp
# (stash/checkout of the old file, a dev server persisting a stale copy) is stale even
# though HEAD's copy equals origin's -- it must not pass as a "local patch".
with tempfile.TemporaryDirectory() as td:
    local, origin = snap_pair(td)                 # commit A: stamp S, unredacted
    old_doc = _snap_doc("2026-10-26T14:52:49.296Z")
    _commit_snap(origin, _snap_doc("2026-10-26T14:52:49.296Z", "redacted"), "redact")  # B
    run(["git", "fetch", "-q", "origin"], local)
    run(["git", "merge", "-q", "--ff-only", "origin/main"], local)
    _write_snap(local, old_doc)                   # working tree reverted to A's bytes
    r = _scan_snap(local)
    expect("reverted-to-older copy at same stamp: stale",
           r.get("snapshot_stale") is True and r.get("snapshot_reverted_to_older") is True
           and not r.get("snapshot_locally_modified"), repr(r))
    expect("reverted-to-older: report says OLDER committed version",
           "OLDER committed version" in wipscan.format_report([r]), wipscan.format_report([r]))
    expect("reverted-to-older: freshness-only exit 1",
           _main_with(["--freshness-only"], [local]) == 1)

    real_git = wipscan._git

    def _git_log_fails(args, repo_path):
        if "log" in args:
            return 128, ""
        return real_git(args, repo_path)

    _write_snap(local, _snap_doc("2026-10-26T14:52:49.296Z", "ar-patched"))
    wipscan._git = _git_log_fails
    try:
        r = _scan_snap(local)
    finally:
        wipscan._git = real_git
    expect("history lookup failure during carve-out: stale + error (fails closed)",
           r.get("snapshot_stale") is True and "history" in (r.get("snapshot_error") or ""), repr(r))

# REFUTE round 3: a blob that only ever existed as a MERGE result (two consecutive
# merges each writing a same-stamp snapshot) must still be recognised as committed.
def _merge_writing(origin, branch, doc):
    run(["git", "checkout", "-q", "-b", branch], origin)
    run(["git", "commit", "--allow-empty", "-q", "-m", "side " + branch], origin)
    run(["git", "checkout", "-q", "main"], origin)
    run(["git", "merge", "-q", "--no-ff", "--no-commit", branch], origin)
    _write_snap(origin, doc)
    run(["git", "add", SNAP], origin)
    run(["git", "commit", "-q", "-m", "merge " + branch], origin)


with tempfile.TemporaryDirectory() as td:
    local, origin = snap_pair(td)
    stamp = "2026-10-26T14:52:49.296Z"
    x_doc = _snap_doc(stamp, "merge-only-X")
    _merge_writing(origin, "s1", x_doc)
    _merge_writing(origin, "s2", _snap_doc(stamp, "merge-only-Y"))
    run(["git", "fetch", "-q", "origin"], local)
    run(["git", "merge", "-q", "--ff-only", "origin/main"], local)
    _write_snap(local, x_doc)
    r = _scan_snap(local)
    expect("merge-only older blob at same stamp: stale (reverted_to_older)",
           r.get("snapshot_stale") is True and r.get("snapshot_reverted_to_older") is True, repr(r))

# (2026-11-12) post-#565 shape: origin/main no longer tracks the snapshot and data/ is
# gitignored; the checkout pulled that, and the refresh task writes the file in place.
# Freshness is then measured by age, not by comparison with a committed copy.
import datetime as _dt  # noqa: E402


def _untrack(repo):
    with open(os.path.join(repo, ".gitignore"), "a", encoding="utf-8", newline="\n") as fh:
        fh.write("/data/\n")
    run(["git", "rm", "-q", "--cached", SNAP], repo)
    run(["git", "add", ".gitignore"], repo)
    run(["git", "commit", "-q", "-m", "untrack snapshot"], repo)


def _iso(hours_ago):
    t = _dt.datetime.now(_dt.timezone.utc) - _dt.timedelta(hours=hours_ago)
    return t.strftime("%Y-%m-%dT%H:%M:%S.000Z")


with tempfile.TemporaryDirectory() as td:
    local, origin = snap_pair(td)
    _untrack(origin)
    run(["git", "pull", "-q", "--ff-only", "origin", "main"], local)
    _write_snap(local, _snap_doc(_iso(5)))
    r = _scan_snap(local)
    expect("untracked fresh (5h): not stale", r.get("snapshot_stale") is False, repr(r))
    expect("untracked fresh: no snapshot_error", r.get("snapshot_error") is None, repr(r))
    expect("untracked fresh: ref names the age rule", "untracked" in str(r.get("snapshot_ref")), repr(r))
    _write_snap(local, _snap_doc(_iso(120)))
    r = _scan_snap(local)
    expect("untracked old (120h): stale", r.get("snapshot_stale") is True, repr(r))
    expect("untracked old: lag hours ~120", 119 <= (r.get("snapshot_lag_hours") or 0) <= 121, repr(r))
    rep = wipscan.format_report([r])
    expect("untracked old: report points at the refresh tasks, not a pull",
           "a pull cannot fix this" in rep and "ora-lease-snapshot-refresh" in rep
           and "Advance the checkout" not in rep, rep)
    expect("untracked old: freshness-only main exits 1",
           _main_with(["--freshness-only"], [local]) == 1)

# Absent on origin but NOT gitignored locally (e.g. ref unfetched / file deleted on main
# without the ignore rule): unchanged behaviour -- unmeasurable, flagged as an error.
with tempfile.TemporaryDirectory() as td:
    local, origin = snap_pair(td)
    run(["git", "rm", "-q", SNAP], origin)
    run(["git", "commit", "-q", "-m", "delete snapshot"], origin)
    run(["git", "fetch", "-q", "origin"], local)
    r = _scan_snap(local)
    expect("absent-on-origin, still tracked locally: snapshot_error set",
           r.get("snapshot_error") is not None and r.get("snapshot_stale") is True, repr(r))

finish("cross-repo-wip-scan snapshot")
