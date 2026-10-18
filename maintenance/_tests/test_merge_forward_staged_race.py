#!/usr/bin/env python3
"""Staged-set recheck between `merge --no-commit` and `commit` (M51).
Real throwaway git repos, same convention as test_checkout_merge_forward.py.
Run: python _tests/test_merge_forward_staged_race.py   (exit 0 = pass)
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
cmf.CLAIMS_DIR_OVERRIDE = tempfile.mkdtemp(prefix="cmf-race-claims-")
cmf.ABORT_RETRY_SECONDS = 0
REAL_GIT = cmf._git
_results = []


def check(name, cond, detail=""):
    _results.append(bool(cond))
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else "  " + detail))


def run(repo, *args):
    p = subprocess.run(["git"] + list(args), cwd=repo, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError("git %s failed: %s" % (" ".join(args), p.stderr))
    return p


def write(repo, fname, text):
    with open(os.path.join(repo, fname), "w", encoding="utf-8") as fh:
        fh.write(text)


def commit(repo, fname, text):
    write(repo, fname, text)
    run(repo, "add", fname)
    run(repo, "commit", "-q", "-m", "add " + fname, "--no-verify")


def make_pair(td):
    origin = os.path.join(td, "origin")
    os.makedirs(origin)
    run(origin, "init", "-q", "-b", "main")
    run(origin, "config", "user.email", "t@example.com")
    run(origin, "config", "user.name", "T")
    commit(origin, "shared.txt", "base\n")
    local = os.path.join(td, "local")
    run(td, "clone", "-q", origin, local)
    run(local, "config", "user.email", "t@example.com")
    run(local, "config", "user.name", "T")
    return local, origin


def install_race(stage_fn, fail_reset=False):
    """Wrap cmf._git: right after the merge call succeeds, a 'foreign session' stages work."""
    def racing(args, repo):
        if fail_reset and args[:1] == ["reset"]:
            return 1, "", "boom"
        res = REAL_GIT(args, repo)
        if args[:2] == ["merge", "--no-commit"] and res[0] == 0:
            stage_fn(repo)
        return res
    cmf._git = racing


def restore_git():
    cmf._git = REAL_GIT


def commit_files(repo):
    return run(repo, "diff", "--name-only", "HEAD^1", "HEAD").stdout.split()


# 1. Foreign NEW file staged during the window is NOT swept into the merge commit.
with tempfile.TemporaryDirectory() as td:
    local, origin = make_pair(td)
    commit(origin, "incoming.txt", "from origin\n")
    def stage_new(repo):
        write(repo, "foreign.txt", "session B work\n")
        run(repo, "add", "foreign.txt")
    install_race(stage_new)
    try:
        r = cmf.sync(local, "main")
    finally:
        restore_git()
    check("new file: status stays MERGED", r["status"] == "MERGED", repr(r))
    check("new file: foreign path reported", r.get("unstaged_foreign") == ["foreign.txt"], repr(r))
    check("new file: merge commit has incoming only", "foreign.txt" not in commit_files(local)
          and "incoming.txt" in commit_files(local), repr(commit_files(local)))
    check("new file: content preserved on disk",
          open(os.path.join(local, "foreign.txt"), encoding="utf-8").read() == "session B work\n")
    st = run(local, "status", "--porcelain").stdout
    check("new file: left untracked, not lost", "?? foreign.txt" in st, st)

# 2. Foreign MODIFICATION of a tracked file stays in the worktree, unstaged.
with tempfile.TemporaryDirectory() as td:
    local, origin = make_pair(td)
    commit(origin, "incoming.txt", "from origin\n")
    def stage_mod(repo):
        write(repo, "shared.txt", "base\nsession B edit\n")
        run(repo, "add", "shared.txt")
    install_race(stage_mod)
    try:
        r = cmf.sync(local, "main")
    finally:
        restore_git()
    check("modified: status MERGED", r["status"] == "MERGED", repr(r))
    check("modified: not in merge commit", "shared.txt" not in commit_files(local), repr(commit_files(local)))
    check("modified: edit preserved", "session B edit" in open(os.path.join(local, "shared.txt"), encoding="utf-8").read())
    st = run(local, "status", "--porcelain").stdout
    check("modified: shows as unstaged ' M'", " M shared.txt" in st, st)

# 3. No race: clean path is unchanged and reports nothing foreign.
with tempfile.TemporaryDirectory() as td:
    local, origin = make_pair(td)
    commit(origin, "incoming.txt", "from origin\n")
    r = cmf.sync(local, "main")
    check("clean: MERGED", r["status"] == "MERGED", repr(r))
    check("clean: no foreign fields", not r.get("unstaged_foreign") and not r.get("foreign_in_commit"), repr(r))

# 4. Reset fails: NEVER abort (that would discard foreign staged work); ERROR, merge left, foreign still staged.
with tempfile.TemporaryDirectory() as td:
    local, origin = make_pair(td)
    commit(origin, "incoming.txt", "from origin\n")
    install_race(stage_new, fail_reset=True)
    try:
        r = cmf.sync(local, "main")
    finally:
        restore_git()
    check("reset-fail: ERROR", r["status"] == "ERROR", repr(r))
    check("reset-fail: merge NOT aborted", cmf.ref_state(local, "MERGE_HEAD")[0] == "present", repr(r))
    check("reset-fail: foreign work still staged",
          "foreign.txt" in run(local, "diff", "--cached", "--name-only").stdout)
    check("reset-fail: detail names the situation", "foreign" in r.get("detail", "").lower(), repr(r))

passed = sum(_results)
print("\nmerge-forward staged-race tests: %d/%d passed" % (passed, len(_results)))
sys.exit(0 if passed == len(_results) else 1)
