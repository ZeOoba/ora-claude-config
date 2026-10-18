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




def install_race(stage_fn=None, fail_first=None, mergetree_rc=None):
    """Wrap cmf._git: right after the merge call succeeds, a 'foreign session' stages work.
    fail_first: git subcommand name (e.g. 'commit-tree') whose call is made to fail.
    mergetree_rc: make `merge-tree --write-tree` return this rc with no output."""
    calls = []
    def racing(args, repo):
        calls.append(list(args))
        if fail_first and args[:1] == [fail_first]:
            return 1, "", "boom"
        if mergetree_rc and args[:2] == ["merge-tree", "--write-tree"]:
            return mergetree_rc, "", "usage"
        res = REAL_GIT(args, repo)
        if stage_fn and args[:2] == ["merge", "--no-commit"] and res[0] == 0:
            stage_fn(repo)
        return res
    cmf._git = racing
    return calls


def restore_git():
    cmf._git = REAL_GIT


def commit_files(repo):
    return run(repo, "diff", "--name-only", "HEAD^1", "HEAD").stdout.split()


def sync_with(local, **kw):
    calls = install_race(**kw)
    try:
        return cmf.sync(local, "main"), calls
    finally:
        restore_git()


def porcelain(repo):
    return run(repo, "status", "--porcelain").stdout


def fresh(incoming=("incoming.txt", "from origin\n")):
    td = tempfile.TemporaryDirectory()
    local, origin = make_pair(td.name)
    commit(origin, *incoming)
    return td, local, origin


def stage_new(repo):
    write(repo, "foreign.txt", "session B work\n")
    run(repo, "add", "foreign.txt")


def lf(text):
    return text.replace("\r", "")


def disk(repo, name):
    with open(os.path.join(repo, name), encoding="utf-8", newline="") as fh:
        return lf(fh.read())


# A. foreign NEW file staged in the window
td, local, origin = fresh()
r, _ = sync_with(local, stage_fn=stage_new)
check("A: MERGED", r["status"] == "MERGED", repr(r))
check("A: foreign_staged_preserved", r.get("foreign_staged_preserved") == ["foreign.txt"], repr(r))
check("A: not in merge commit, incoming is", "foreign.txt" not in commit_files(local)
      and "incoming.txt" in commit_files(local), repr(commit_files(local)))
check("A: still staged as added", "A  foreign.txt" in porcelain(local), porcelain(local))
check("A: content intact", disk(local, "foreign.txt") == "session B work\n")
check("A: merge state forgotten", cmf.ref_state(local, "MERGE_HEAD")[0] == "absent")
td.cleanup()

# B. foreign staged edit of an existing tracked non-incoming file
td, local, origin = fresh()
def stage_mod(repo):
    write(repo, "shared.txt", "base\nsession B edit\n")
    run(repo, "add", "shared.txt")
r, _ = sync_with(local, stage_fn=stage_mod)
check("B: MERGED", r["status"] == "MERGED", repr(r))
check("B: not in commit", "shared.txt" not in commit_files(local), repr(commit_files(local)))
check("B: still staged M ", "M  shared.txt" in porcelain(local), porcelain(local))
td.cleanup()

# C. foreign staged edit ON an incoming path
td, local, origin = fresh()
def stage_on_incoming(repo):
    write(repo, "incoming.txt", "foreign edit\n")
    run(repo, "add", "incoming.txt")
r, _ = sync_with(local, stage_fn=stage_on_incoming)
check("C: MERGED", r["status"] == "MERGED", repr(r))
check("C: HEAD has origin's content", lf(run(local, "show", "HEAD:incoming.txt").stdout) == "from origin\n")
check("C: foreign edit still staged", lf(run(local, "show", ":incoming.txt").stdout) == "foreign edit\n")
check("C: foreign edit in worktree", disk(local, "incoming.txt") == "foreign edit\n")
check("C: reported", "incoming.txt" in (r.get("foreign_staged_preserved") or []), repr(r))
td.cleanup()

# D. glob-named foreign file while origin adds ab.txt
td, local, origin = fresh(("ab.txt", "origin ab\n"))
def stage_glob(repo):
    write(repo, "a[b].txt", "glob\n")
    run(repo, "add", "--", "a[b].txt")
r, _ = sync_with(local, stage_fn=stage_glob)
check("D: MERGED", r["status"] == "MERGED", repr(r))
check("D: ab.txt in HEAD tree", "ab.txt" in run(local, "ls-tree", "-r", "--name-only", "HEAD").stdout.split())
check("D: a[b].txt still staged", "a[b].txt" in run(local, "diff", "--cached", "--name-only").stdout, porcelain(local))
td.cleanup()

# E. partial staging: v1 staged, v2 in worktree
td, local, origin = fresh()
def stage_partial(repo):
    write(repo, "foreign.txt", "v1\n")
    run(repo, "add", "foreign.txt")
    write(repo, "foreign.txt", "v2\n")
r, _ = sync_with(local, stage_fn=stage_partial)
check("E: MERGED", r["status"] == "MERGED", repr(r))
check("E: index blob still v1", lf(run(local, "show", ":foreign.txt").stdout) == "v1\n")
check("E: worktree still v2", disk(local, "foreign.txt") == "v2\n")
td.cleanup()

# F. index-only file (staged then deleted from disk)
td, local, origin = fresh()
def stage_indexonly(repo):
    stage_new(repo)
    os.remove(os.path.join(repo, "foreign.txt"))
r, _ = sync_with(local, stage_fn=stage_indexonly)
check("F: MERGED", r["status"] == "MERGED", repr(r))
check("F: still in index", "foreign.txt" in run(local, "ls-files").stdout.split(), porcelain(local))
check("F: not in commit", "foreign.txt" not in commit_files(local))
td.cleanup()

# G. clean path
td, local, origin = fresh()
r, _ = sync_with(local)
check("G: MERGED", r["status"] == "MERGED", repr(r))
check("G: no foreign key", "foreign_staged_preserved" not in r and "recheck" not in r, repr(r))
check("G: two parents", len(run(local, "rev-list", "--parents", "-n", "1", "HEAD").stdout.split()) == 3)
td.cleanup()

# H. commit-tree fails: ERROR, merge left, foreign still staged, no abort
td, local, origin = fresh()
r, calls = sync_with(local, stage_fn=stage_new, fail_first="commit-tree")
check("H: ERROR", r["status"] == "ERROR", repr(r))
check("H: MERGE_HEAD present", cmf.ref_state(local, "MERGE_HEAD")[0] == "present", repr(r))
check("H: foreign still staged", "foreign.txt" in run(local, "diff", "--cached", "--name-only").stdout)
check("H: merge_aborted False", r.get("merge_aborted") is False, repr(r))
check("H: no abort/reset issued",
      not any(c[:2] == ["merge", "--abort"] or c[:1] == ["reset"] for c in calls), repr(calls))
td.cleanup()

# I. merge-tree --write-tree unavailable (rc 129): legacy commit, recheck flagged
td, local, origin = fresh()
r, _ = sync_with(local, mergetree_rc=129)
check("I: MERGED via legacy commit", r["status"] == "MERGED", repr(r))
check("I: recheck unavailable", r.get("recheck") == "unavailable", repr(r))
check("I: incoming merged", "incoming.txt" in commit_files(local))
td.cleanup()

# J. update-ref CAS result: HEAD equals returned sha, second parent is origin
td, local, origin = fresh()
r, _ = sync_with(local, stage_fn=stage_new)
head = run(local, "rev-parse", "HEAD").stdout.strip()
check("J: HEAD == returned sha", r.get("sha") == head, repr(r))
check("J: second parent is origin tip",
      run(local, "rev-parse", "HEAD^2").stdout.strip() == run(origin, "rev-parse", "HEAD").stdout.strip())
check("J: reflog entry", "merge-forward" in run(local, "reflog", "-n", "1", "HEAD").stdout)
td.cleanup()

passed = sum(_results)
print("\nmerge-forward staged-race tests: %d/%d passed" % (passed, len(_results)))
sys.exit(0 if passed == len(_results) else 1)
