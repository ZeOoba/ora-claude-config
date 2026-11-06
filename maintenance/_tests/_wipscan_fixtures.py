#!/usr/bin/env python3
"""Shared fixtures for the cross-repo-wip-scan test files (not itself a test: the
pre-push hook-tests gate discovers only test_*.py). Split out 2026-11-05 so the
F-9 OCC-freshness tests run as their own files, each inside the gate's per-file
budget, instead of one file blowing it under the gate's parallel load."""
import json as _json
import os
import shutil
import subprocess
import sys
import tempfile
import importlib.util

HOOKS_LIB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "..", "hooks", "tests", "lib")
sys.path.insert(0, os.path.abspath(HOOKS_LIB))
import gitfixture  # noqa: E402  (shared repo fixture -- open-items-tracker.md#OI-061)

MAINT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_spec = importlib.util.spec_from_file_location(
    "wipscan", os.path.join(MAINT, "cross-repo-wip-scan.py"))
wipscan = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(wipscan)

results = []


def expect(label, cond, detail=""):
    results.append((bool(cond), label))
    if not cond:
        print("  FAIL: %s %s" % (label, detail))


def run(cmd, cwd):
    subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=True)


def init_repo(path):
    """Shared template-and-copy blank repo relocated to `path` (must not exist)."""
    shutil.move(gitfixture.blank_repo(), path)
    return path


def finish(name):
    passed = sum(1 for ok, _ in results if ok)
    print("%s tests: %d/%d passed" % (name, passed, len(results)))
    sys.exit(0 if passed == len(results) else 1)


# Fixture pairs are BUILT ONCE per shape and handed out as directory copies plus one
# `git remote set-url` (2026-11-05): building each pair from scratch cost ~8-10 git
# spawns, and the suite went 30s -> 132s idle, past the pre-push hook-tests gate's
# 240s/480s budget under its 8-way parallel load. Copies are independent real repos;
# nothing asserted depends on a pair being freshly built rather than copied.
import atexit  # noqa: E402

_PAIR_TEMPLATES = {}
_TEMPLATE_ROOT = tempfile.mkdtemp(prefix="wipscan-tpl-")
atexit.register(shutil.rmtree, _TEMPLATE_ROOT, True)


def _copy_pair(key, build, td):
    if key not in _PAIR_TEMPLATES:
        base = os.path.join(_TEMPLATE_ROOT, "t%d" % len(_PAIR_TEMPLATES))
        os.makedirs(base)
        _PAIR_TEMPLATES[key] = build(base)
    src_local, src_origin = _PAIR_TEMPLATES[key]
    origin, local = os.path.join(td, "origin"), os.path.join(td, "local")
    shutil.copytree(src_origin, origin)
    shutil.copytree(src_local, local)
    run(["git", "remote", "set-url", "origin", origin], local)
    return local, origin


def make_origin_pair(td, canonical="main"):
    """(local, origin) -- `local` has `origin` wired as a real remote, with
    `origin/<canonical>` fetched and resolvable. Both start on `canonical`
    with one shared commit."""
    return _copy_pair(("origin", canonical),
                      lambda base: _build_origin_pair(base, canonical), td)


def _build_origin_pair(td, canonical):
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
    return _copy_pair(("snap", generated_at),
                      lambda base: _build_snap_pair(base, generated_at), td)


def _build_snap_pair(td, generated_at):
    local, origin = _build_origin_pair(td, "main")
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


