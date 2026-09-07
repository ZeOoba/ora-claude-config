#!/usr/bin/env python3
"""Tests for check-branch-point.py (TDD).

Black-box, subprocess-driven against a throwaway git repo (own commits, own
branches standing in for "HEAD" vs "origin/main") -- mirrors
test-fleet-spec-git-drift-probe.py's own structure, since both scripts now
share hooks/lib/git_probe_common.py and this suite is this file's first-ever
regression proof (added 2026-09-07 alongside that extraction).

Initial-repo creation goes through hooks/tests/lib/gitfixture.py (house
convention -- see maintenance/test-append-event-log.py) rather than a
hand-rolled `git init` + 2x `git config` + commit.

Run: python test-check-branch-point.py
Stdlib only (plus gitfixture, itself stdlib-only). ASCII-only.
"""
import importlib.util
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "check-branch-point.py")
PY = sys.executable

HOOKS_LIB = os.path.join(HERE, "..", "hooks", "tests", "lib")
sys.path.insert(0, os.path.abspath(HOOKS_LIB))
import gitfixture  # noqa: E402  (shared repo fixture -- open-items-tracker.md#OI-061/#OI-072)

# Scrub inherited git worktree/index env vars so subprocess git calls against
# the throwaway fixture repos below operate on THOSE repos, not whatever
# outer checkout/worktree this test itself runs inside (same scrub as
# test-fleet-spec-git-drift-probe.py).
for _v in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR",
           "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_PREFIX"):
    os.environ.pop(_v, None)

_failures = []


def check(name, cond, detail=""):
    if cond:
        print("  PASS " + name)
    else:
        print("  FAIL " + name + "  " + detail)
        _failures.append(name)


def git(repo, *args):
    return subprocess.run(["git", "-C", repo] + list(args),
                           capture_output=True, text=True)


def commit(repo, rel, content, msg):
    path = os.path.join(repo, *rel.split("/"))
    parent = os.path.dirname(path)
    if parent and not os.path.isdir(parent):
        os.makedirs(parent)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)
    git(repo, "add", "-A")
    r = git(repo, "commit", "-q", "-m", msg)
    assert r.returncode == 0, r.stderr


def make_repo():
    return gitfixture.repo_with_commit(prefix="cbp-repo-")


def run_check(repo=None, base="main", expect=None, extra_args=None, json_mode=True):
    args = [PY, SCRIPT, "--base", base]
    if json_mode:
        args += ["--json"]
    if repo is not None:
        args += ["--repo", repo]
    if expect is not None:
        args += ["--expect", str(expect)]
    if extra_args:
        args += extra_args
    proc = subprocess.run(args, capture_output=True, text=True, timeout=30,
                          cwd=repo)
    return proc.returncode, proc.stdout + proc.stderr


def _load_module():
    """Import the hyphenated script as a module for white-box tests (forcing
    a specific git() call to fail -- mirrors
    test-fleet-spec-git-drift-probe.py's own _load_probe_module())."""
    spec = importlib.util.spec_from_file_location("check_branch_point", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_no_extra_commits_is_certified_with_expect_zero():
    repo = make_repo()
    rc, out = run_check(repo, base="main", expect=0)
    check("test_no_extra_commits_is_certified_with_expect_zero", rc == 0,
          "expected exit 0, got %s\n%s" % (rc, out))


def _branch_ahead_of_main(repo, n=1):
    """Create branch 'feature' off main's current tip, commit `n` time(s) on
    it, and leave 'feature' checked out as HEAD -- main stays fixed at its
    original commit, so main is an ancestor of HEAD with exactly `n` extra
    commits. (Committing directly on gitfixture's default checkout, as this
    file's first draft did, advances main and HEAD together -- always zero
    divergence -- which is why that draft's own assertions caught nothing.)"""
    r = git(repo, "checkout", "-q", "-b", "feature")
    assert r.returncode == 0, r.stderr
    for i in range(n):
        commit(repo, "feature-%d.txt" % i, "v1\n", "feature commit %d" % i)


def test_extra_commits_without_expect_is_not_certified():
    # Ancestor of HEAD, but expect not given -- the tool must decline to
    # certify (the exact false-green shape its own docstring incident describes).
    repo = make_repo()
    _branch_ahead_of_main(repo, n=1)
    rc, out = run_check(repo, base="main")
    check("test_extra_commits_without_expect_is_not_certified", rc == 1,
          "expected exit 1, got %s\n%s" % (rc, out))


def test_extra_commits_matching_expect_is_certified():
    repo = make_repo()
    _branch_ahead_of_main(repo, n=1)
    rc, out = run_check(repo, base="main", expect=1)
    check("test_extra_commits_matching_expect_is_certified", rc == 0,
          "expected exit 0, got %s\n%s" % (rc, out))


def test_expect_mismatch_flags_action():
    repo = make_repo()
    _branch_ahead_of_main(repo, n=1)
    rc, out = run_check(repo, base="main", expect=2, json_mode=False)
    check("test_expect_mismatch_flags_action", rc == 1 and "COMMIT_COUNT" in out,
          "expected exit 1 with COMMIT_COUNT action, got %s\n%s" % (rc, out))


def test_base_not_ancestor_is_flagged():
    # Cut a branch, advance main independently, so main is NOT an ancestor of
    # HEAD -- the "branch cut from somewhere else" shape.
    repo = make_repo()
    r = git(repo, "checkout", "-q", "-b", "feature")
    assert r.returncode == 0, r.stderr
    commit(repo, "on-feature.txt", "v1\n", "advance feature")
    r = git(repo, "checkout", "-q", "main")
    assert r.returncode == 0, r.stderr
    commit(repo, "on-main.txt", "v1\n", "advance main independently")
    r = git(repo, "checkout", "-q", "feature")
    assert r.returncode == 0, r.stderr
    rc, out = run_check(repo, base="main", json_mode=False)
    check("test_base_not_ancestor_is_flagged",
          rc == 1 and "BRANCH_POINT" in out and "NOT an ancestor" in out,
          "expected exit 1 with BRANCH_POINT action, got %s\n%s" % (rc, out))


def test_unresolvable_base_is_undetermined():
    repo = make_repo()
    rc, out = run_check(repo, base="no-such-ref-xyz")
    check("test_unresolvable_base_is_undetermined",
          rc == 2 and "does not resolve -- fetch it first" in out,
          "expected exit 2 with the original error text, got %s\n%s" % (rc, out))


def test_not_a_git_repo_is_undetermined():
    d = tempfile.mkdtemp(prefix="cbp-notrepo-")
    rc, out = run_check(d, base="main")
    check("test_not_a_git_repo_is_undetermined", rc == 2,
          "expected exit 2, got %s\n%s" % (rc, out))


def test_repo_none_uses_cwd():
    # Regression: git_probe_common.git()'s repo=None path must omit `-C`
    # entirely (running in the inherited cwd), not pass a literal None/empty
    # value to `-C` -- caught during the hooks/lib extraction, before it ever
    # shipped, by tracing check-branch-point.py's own --repo default.
    repo = make_repo()
    _branch_ahead_of_main(repo, n=1)
    proc = subprocess.run([PY, SCRIPT, "--base", "main", "--expect", "1", "--json"],
                          capture_output=True, text=True, timeout=30, cwd=repo)
    check("test_repo_none_uses_cwd", proc.returncode == 0,
          "expected exit 0 running with no --repo (cwd-relative), got %s\n%s"
          % (proc.returncode, proc.stdout + proc.stderr))


def test_head_resolve_failure_is_undetermined():
    # White-box: force the very first git() call (rev-parse HEAD) to fail --
    # real git essentially never fails this on a valid repo, so failure-path
    # coverage needs a monkeypatch, mirroring
    # test-fleet-spec-git-drift-probe.py's own approach.
    repo = make_repo()
    mod = _load_module()
    orig_git = mod.git

    def fake_git(args, repo=None):
        if args and args[0] == "rev-parse" and args[1:2] == ["HEAD"]:
            return 128, "simulated HEAD resolve failure"
        return orig_git(args, repo)

    mod.git = fake_git
    result = mod.analyze(base="main", repo=repo)
    check("test_head_resolve_failure_is_undetermined",
          result["error"] is not None and "cannot resolve HEAD" in result["error"],
          "expected an unresolved-HEAD error, got %r" % (result,))


def test_json_output_shape():
    repo = make_repo()
    rc, out = run_check(repo, base="main", expect=0)
    check("test_json_output_shape",
          '"certified": true' in out or '"certified":true' in out,
          "expected a certified:true JSON field, got %s\n%s" % (rc, out))


if __name__ == "__main__":
    test_no_extra_commits_is_certified_with_expect_zero()
    test_extra_commits_without_expect_is_not_certified()
    test_extra_commits_matching_expect_is_certified()
    test_expect_mismatch_flags_action()
    test_base_not_ancestor_is_flagged()
    test_unresolvable_base_is_undetermined()
    test_not_a_git_repo_is_undetermined()
    test_repo_none_uses_cwd()
    test_head_resolve_failure_is_undetermined()
    test_json_output_shape()
    if _failures:
        print("\n%d FAILURE(S): %s" % (len(_failures), ", ".join(_failures)))
        sys.exit(1)
    print("\nALL check-branch-point tests passed.")
    sys.exit(0)
