#!/usr/bin/env python3
"""Tests for fleet-spec-git-drift-probe.py (TDD).

Black-box, subprocess-driven against a throwaway git repo (own commits, own
branches standing in for "HEAD" vs "origin/main") for the behavioral tests,
plus a handful of white-box tests that monkeypatch the module's own git()
to force a git-call failure deterministically (real git essentially never
fails for a syntactically valid ref, so failure-path coverage needs this
rather than trying to provoke a genuine git error).

Initial-repo creation goes through hooks/tests/lib/gitfixture.py (house
convention -- see maintenance/test-append-event-log.py) rather than a
hand-rolled `git init` + 2x `git config` + commit: gitfixture caches that
template per-process so repeated calls pay zero extra subprocess spawns.
Everything AFTER the initial commit (branches, further commits, checkout)
is test-specific and stays as plain subprocess git calls -- gitfixture is
deliberately only the initial-fixture layer, not a general git DSL.

Run: python test-fleet-spec-git-drift-probe.py
Stdlib only (plus gitfixture, itself stdlib-only). ASCII-only.
"""
import importlib.util
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "fleet-spec-git-drift-probe.py")
PY = sys.executable

HOOKS_LIB = os.path.join(HERE, "..", "hooks", "tests", "lib")
sys.path.insert(0, os.path.abspath(HOOKS_LIB))
import gitfixture  # noqa: E402  (shared repo fixture -- open-items-tracker.md#OI-061/#OI-072)

# Scrub inherited git worktree/index env vars so subprocess git calls against
# the throwaway fixture repos below operate on THOSE repos, not whatever
# outer checkout/worktree this test itself runs inside (same scrub as
# test-dirty-file-owner-report.py and hooks/tests/test-shared-checkout-guard.py).
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


def write(repo, rel, content):
    path = os.path.join(repo, *rel.split("/"))
    parent = os.path.dirname(path)
    if parent and not os.path.isdir(parent):
        os.makedirs(parent)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)
    return path


def commit(repo, rel, content, msg):
    write(repo, rel, content)
    git(repo, "add", "-A")
    r = git(repo, "commit", "-q", "-m", msg)
    assert r.returncode == 0, r.stderr


def make_repo():
    # gitfixture's default identity/message/newline match what this suite
    # needs exactly (t@t.t/t, "init", one README.md) -- no override needed.
    return gitfixture.repo_with_commit(prefix="fsgd-repo-")


def run_probe(repo, base="main", extra_args=None):
    args = [PY, SCRIPT, "--repo", repo, "--base", base, "--no-fetch", "--json"]
    if extra_args:
        args += extra_args
    proc = subprocess.run(args, capture_output=True, text=True, timeout=30)
    return proc.returncode, proc.stdout + proc.stderr


def _load_probe_module():
    """Import the hyphenated script as a module for white-box tests (forcing
    a specific git() call to fail, which real git essentially never does on
    a syntactically valid ref -- there is no black-box way to provoke this
    deterministically)."""
    spec = importlib.util.spec_from_file_location("fleet_spec_git_drift_probe", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_no_divergence_is_clean():
    repo = make_repo()
    commit(repo, "scheduled-tasks/foo/SKILL.md", "v1\n", "add foo v1")
    rc, out = run_probe(repo, base="main")
    check("test_no_divergence_is_clean", rc == 0, "expected exit 0, got %s\n%s" % (rc, out))


def test_stranded_spec_flagged():
    # HEAD stays on the pre-fix commit ("stale-checkout"); "main" (standing in
    # for origin/main) advances the same file -- the merged-but-not-served shape.
    repo = make_repo()
    commit(repo, "scheduled-tasks/foo/SKILL.md", "v1\n", "add foo v1")
    git(repo, "branch", "-q", "stale-checkout")
    commit(repo, "scheduled-tasks/foo/SKILL.md", "v2 -- guard fixed\n", "fix guard on main")
    r = git(repo, "checkout", "-q", "stale-checkout")
    assert r.returncode == 0, r.stderr
    rc, out = run_probe(repo, base="main")
    check("test_stranded_spec_flagged", rc == 1,
          "expected exit 1, got %s\n%s" % (rc, out))
    check("test_stranded_spec_flagged_names_path",
          "scheduled-tasks/foo/SKILL.md" in out, out)


def test_identical_content_despite_extra_commits_is_clean():
    # main touches the file twice but ends up byte-identical to what HEAD
    # already has -- must NOT flag (a probe that cries wolf on a fixed state
    # is worse than no probe, per this codebase's own precedent).
    repo = make_repo()
    commit(repo, "scheduled-tasks/foo/SKILL.md", "v1\n", "add foo v1")
    git(repo, "branch", "-q", "stale-checkout")
    commit(repo, "scheduled-tasks/foo/SKILL.md", "v_temp\n", "temp edit on main")
    commit(repo, "scheduled-tasks/foo/SKILL.md", "v1\n", "revert to v1 on main")
    r = git(repo, "checkout", "-q", "stale-checkout")
    assert r.returncode == 0, r.stderr
    rc, out = run_probe(repo, base="main")
    check("test_identical_content_despite_extra_commits_is_clean", rc == 0,
          "expected exit 0, got %s\n%s" % (rc, out))


def test_archived_task_dir_excluded():
    repo = make_repo()
    commit(repo, "scheduled-tasks/_archive_foo/SKILL.md", "v1\n", "add archived foo v1")
    git(repo, "branch", "-q", "stale-checkout")
    commit(repo, "scheduled-tasks/_archive_foo/SKILL.md", "v2\n", "edit archived foo on main")
    r = git(repo, "checkout", "-q", "stale-checkout")
    assert r.returncode == 0, r.stderr
    rc, out = run_probe(repo, base="main")
    check("test_archived_task_dir_excluded", rc == 0,
          "expected exit 0 (archived dir out of scope), got %s\n%s" % (rc, out))


def test_new_spec_merged_but_never_pulled_flags():
    # A whole new task spec landed on main; the live checkout never has it at
    # all. Still "merged but not served" -- the live_missing case.
    repo = make_repo()
    git(repo, "branch", "-q", "stale-checkout")
    commit(repo, "scheduled-tasks/newguard/SKILL.md", "v1\n", "add new guard spec on main")
    r = git(repo, "checkout", "-q", "stale-checkout")
    assert r.returncode == 0, r.stderr
    rc, out = run_probe(repo, base="main")
    check("test_new_spec_merged_but_never_pulled_flags", rc == 1,
          "expected exit 1, got %s\n%s" % (rc, out))
    check("test_new_spec_merged_but_never_pulled_names_path",
          "scheduled-tasks/newguard/SKILL.md" in out, out)


def test_unresolvable_base_is_undetermined():
    repo = make_repo()
    commit(repo, "scheduled-tasks/foo/SKILL.md", "v1\n", "add foo v1")
    rc, out = run_probe(repo, base="no-such-ref-xyz")
    check("test_unresolvable_base_is_undetermined", rc == 2,
          "expected exit 2, got %s\n%s" % (rc, out))


def test_not_a_git_repo_is_undetermined():
    d = tempfile.mkdtemp(prefix="fsgd-notrepo-")
    rc, out = run_probe(d, base="main")
    check("test_not_a_git_repo_is_undetermined", rc == 2,
          "expected exit 2, got %s\n%s" % (rc, out))


def test_pathspec_magic_characters_in_task_name_are_literal():
    # A folder named with characters that are pathspec magic under a
    # core.globPathspecs=true config (bracket = glob char class) must still
    # resolve correctly. NOTE: verified empirically (see the review that
    # added the `:(literal)` prefix in commits_ahead()) that this repo's
    # default git config already treats plain pathspecs literally -- so this
    # test does not discriminate pass/fail on the `:(literal)` prefix itself;
    # it documents that a bracket-named folder works correctly either way,
    # and the prefix is retained as free defensive coverage against a
    # non-default config, not as a proven-necessary fix.
    repo = make_repo()
    commit(repo, "scheduled-tasks/[deprecated]-old-task/SKILL.md", "v1\n",
           "add bracket-named task v1")
    git(repo, "branch", "-q", "stale-checkout")
    commit(repo, "scheduled-tasks/[deprecated]-old-task/SKILL.md", "v2\n",
           "advance bracket-named task on main")
    r = git(repo, "checkout", "-q", "stale-checkout")
    assert r.returncode == 0, r.stderr
    rc, out = run_probe(repo, base="main")
    check("test_pathspec_magic_characters_in_task_name_are_literal", rc == 1,
          "expected exit 1 (bracket name matched literally), got %s\n%s" % (rc, out))


def test_base_ls_tree_failure_is_undetermined_not_clean():
    # White-box: force the ls-tree call (base_task_specs) to fail. Pre-fix,
    # this silently returned {} and the whole run reported [OK] -- the false
    # green review caught (this is ONE call covering the entire upstream
    # tree, so its failure must taint the whole run, not just one path).
    repo = make_repo()
    commit(repo, "scheduled-tasks/foo/SKILL.md", "v1\n", "add foo v1")
    mod = _load_probe_module()
    orig_git = mod.git

    def fake_git(r, args, timeout=20, strip=True):
        if args and args[0] == "ls-tree":
            return 128, "", "simulated ls-tree failure"
        return orig_git(r, args, timeout=timeout, strip=strip)

    mod.git = fake_git
    result = mod.analyze(repo, base="main", do_fetch=False)
    check("test_base_ls_tree_failure_is_undetermined_not_clean",
          result["error"] is not None,
          "expected out['error'] to be set, got %r" % (result,))


def test_per_path_log_failure_is_undetermined_not_silently_clean():
    # White-box: force the per-path log call (commits_ahead) to fail for a
    # path that IS genuinely stranded. Pre-fix, this silently returned []
    # ("not ahead") and the path was skipped with no trace in the report.
    repo = make_repo()
    commit(repo, "scheduled-tasks/foo/SKILL.md", "v1\n", "add foo v1")
    git(repo, "branch", "-q", "stale-checkout")
    commit(repo, "scheduled-tasks/foo/SKILL.md", "v2\n", "advance on main")
    r = git(repo, "checkout", "-q", "stale-checkout")
    assert r.returncode == 0, r.stderr
    mod = _load_probe_module()
    orig_git = mod.git

    def fake_git(r, args, timeout=20, strip=True):
        if args and args[0] == "log":
            return 128, "", "simulated log failure"
        return orig_git(r, args, timeout=timeout, strip=strip)

    mod.git = fake_git
    result = mod.analyze(repo, base="main", do_fetch=False)
    check("test_per_path_log_failure_is_undetermined_not_silently_clean",
          "scheduled-tasks/foo/SKILL.md" in result["undetermined_paths"]
          and not result["findings"],
          "expected the path in undetermined_paths with no findings, got %r"
          % (result,))


def test_live_probe_smoke():
    # Against the real checkout this test file itself lives in, --no-fetch so
    # it never touches the network. Must not crash; the real tree's own
    # drift state (clean or found) is not this test's concern.
    repo = os.path.dirname(HERE)
    proc = subprocess.run([PY, SCRIPT, "--repo", repo, "--no-fetch"],
                          capture_output=True, text=True, timeout=30)
    check("test_live_probe_smoke", proc.returncode in (0, 1),
          "live probe should exit 0 or 1, got %s\n%s"
          % (proc.returncode, proc.stdout + proc.stderr))


if __name__ == "__main__":
    test_no_divergence_is_clean()
    test_stranded_spec_flagged()
    test_identical_content_despite_extra_commits_is_clean()
    test_archived_task_dir_excluded()
    test_new_spec_merged_but_never_pulled_flags()
    test_unresolvable_base_is_undetermined()
    test_not_a_git_repo_is_undetermined()
    test_pathspec_magic_characters_in_task_name_are_literal()
    test_base_ls_tree_failure_is_undetermined_not_clean()
    test_per_path_log_failure_is_undetermined_not_silently_clean()
    test_live_probe_smoke()
    if _failures:
        print("\n%d FAILURE(S): %s" % (len(_failures), ", ".join(_failures)))
        sys.exit(1)
    print("\nALL fleet-spec-git-drift-probe tests passed.")
    sys.exit(0)
