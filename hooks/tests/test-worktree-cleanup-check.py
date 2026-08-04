#!/usr/bin/env python3
"""Tests for worktree_cleanup_check.py -- the merge-ancestry + clean-tree safety
check that would have caught this session's own near-miss (see the module's own
docstring: a reviewed, unmerged branch almost got deleted as "stale worktree
cleanup" because `git worktree list` alone doesn't say whether HEAD is an
ancestor of main).

Builds real linked worktrees via `git worktree add` against a gitfixture-built
base repo -- gitfixture's own templates are plain repos, not worktrees, so this
suite still pays real subprocess spawns for `worktree add`/`branch`/`commit`,
but that is inherent to actually exercising worktree semantics, not something
gitfixture is meant to amortize away.

Run: python test-worktree-cleanup-check.py   (exit 0 = all pass)
"""
import os
import subprocess
import sys
import tempfile

for _v in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR",
           "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_PREFIX"):
    os.environ.pop(_v, None)

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "lib"))
import gitfixture  # noqa: E402

sys.path.insert(0, os.path.join(HERE, "..", "lib"))
import worktree_cleanup_check as wcc  # noqa: E402

results = []


def check(label, cond, detail=""):
    results.append((bool(cond), label))
    if not cond:
        print("  FAIL: %s %s" % (label, detail))


def git(repo, *args):
    return subprocess.run(["git", "-C", repo] + list(args),
                          capture_output=True, text=True)


main_repo = gitfixture.repo_with_commit()
base_branch = git(main_repo, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
check("setup: resolved base branch name", bool(base_branch))

# --- scenario 1: clean worktree, branch fully merged into base -> SAFE ---
wt_safe = tempfile.mkdtemp(prefix="wcc-wt-safe-")
os.rmdir(wt_safe)  # `worktree add` refuses a pre-existing directory
r = git(main_repo, "branch", "merged-branch")
check("setup: branch created (safe scenario)", r.returncode == 0, r.stderr)
r = git(main_repo, "worktree", "add", wt_safe, "merged-branch")
check("setup: worktree add succeeded (safe scenario)", r.returncode == 0, r.stderr)

result = wcc.check_worktree(wt_safe, base=base_branch)
check("safe scenario: ref resolved", result["ref"] == "merged-branch", result)
check("safe scenario: clean=True", result["clean"] is True, result)
check("safe scenario: merged=True", result["merged"] is True, result)
check("safe scenario: safe=True", result["safe"] is True, result)

# --- scenario 2: worktree has an UNMERGED commit -> UNSAFE ---
wt_unmerged = tempfile.mkdtemp(prefix="wcc-wt-unmerged-")
os.rmdir(wt_unmerged)
r = git(main_repo, "branch", "unmerged-branch")
check("setup: branch created (unmerged scenario)", r.returncode == 0, r.stderr)
r = git(main_repo, "worktree", "add", wt_unmerged, "unmerged-branch")
check("setup: worktree add succeeded (unmerged scenario)", r.returncode == 0, r.stderr)
with open(os.path.join(wt_unmerged, "new-file.txt"), "w", encoding="utf-8") as f:
    f.write("real, reviewed, unmerged work\n")
git(wt_unmerged, "add", "-A")
r = git(wt_unmerged, "-c", "user.email=t@t.t", "-c", "user.name=t",
       "commit", "-qm", "unmerged commit -- must NOT be reported safe")
check("setup: unmerged commit created", r.returncode == 0, r.stderr)

result = wcc.check_worktree(wt_unmerged, base=base_branch)
check("unmerged scenario: clean=True (commit landed, nothing uncommitted)",
      result["clean"] is True, result)
check("unmerged scenario: merged=False", result["merged"] is False, result)
check("THE CORE REGRESSION GUARD: unmerged scenario: safe=False",
      result["safe"] is False, result)

# --- scenario 3: worktree is merged but DIRTY (uncommitted change) -> UNSAFE ---
wt_dirty = tempfile.mkdtemp(prefix="wcc-wt-dirty-")
os.rmdir(wt_dirty)
r = git(main_repo, "branch", "dirty-branch")
check("setup: branch created (dirty scenario)", r.returncode == 0, r.stderr)
r = git(main_repo, "worktree", "add", wt_dirty, "dirty-branch")
check("setup: worktree add succeeded (dirty scenario)", r.returncode == 0, r.stderr)
with open(os.path.join(wt_dirty, "README.md"), "a", encoding="utf-8") as f:
    f.write("uncommitted edit\n")

result = wcc.check_worktree(wt_dirty, base=base_branch)
check("dirty scenario: clean=False", result["clean"] is False, result)
check("dirty scenario: merged=True (the branch itself has no new commits)",
      result["merged"] is True, result)
check("dirty scenario: safe=False despite merged=True", result["safe"] is False, result)

# --- regression for independent-review minor note 2: a BAD --base ref (e.g.
# the "main" default against a repo whose default branch is actually
# something else) must be reported as a DISTINCT error, not silently folded
# into "unmerged commits would be lost" -- those read as very different
# findings to whoever is deciding whether to delete a worktree ---
result_bad_base = wcc.check_worktree(wt_safe, base="this-ref-does-not-exist-anywhere")
check("bad --base: safe=False", result_bad_base["safe"] is False, result_bad_base)
check("bad --base: reason is distinct from the real 'unmerged' finding "
      "(does not claim commits would be lost)",
      "could not determine merge status" in result_bad_base["reason"]
      and "would be lost" not in result_bad_base["reason"],
      result_bad_base)

# --- scenario 4: detached HEAD at the base tip -> SAFE ---
wt_detached = tempfile.mkdtemp(prefix="wcc-wt-detached-")
os.rmdir(wt_detached)
r = git(main_repo, "worktree", "add", "--detach", wt_detached, base_branch)
check("setup: detached worktree add succeeded", r.returncode == 0, r.stderr)

result = wcc.check_worktree(wt_detached, base=base_branch)
check("detached scenario: ref is a sha, not 'HEAD'",
      bool(result["ref"]) and result["ref"] != "HEAD", result)
check("detached scenario: safe=True", result["safe"] is True, result)

# --- scenario 5: nonexistent path -> error, never SAFE ---
result = wcc.check_worktree(os.path.join(tempfile.gettempdir(), "wcc-does-not-exist-xyz"))
check("nonexistent path: ref is None", result["ref"] is None, result)
check("nonexistent path: safe=False", result["safe"] is False, result)

# --- scenario 6: existing directory that is NOT a git worktree -> error, never SAFE
# (this is exactly the shape blissful-nash-783df1/goofy-hopper-44e430 turned out to
# be during this session's real cleanup -- empty stray directories, no .git at all) ---
wt_not_git = tempfile.mkdtemp(prefix="wcc-wt-not-git-")
result = wcc.check_worktree(wt_not_git, base=base_branch)
check("plain (non-git) directory: ref is None", result["ref"] is None, result)
check("plain (non-git) directory: safe=False", result["safe"] is False, result)

# --- CLI exit codes, exercised end-to-end (not just the library function) ---
CLI = os.path.join(HERE, "..", "lib", "worktree_cleanup_check.py")


def run_cli(*args):
    return subprocess.run([sys.executable, CLI] + list(args),
                          capture_output=True, text=True)


r = run_cli(wt_safe, "--base", base_branch)
check("CLI: safe scenario exits 0", r.returncode == 0, r.stdout + r.stderr)
check("CLI: safe scenario prints SAFE", r.stdout.startswith("SAFE:"), r.stdout)

r = run_cli(wt_unmerged, "--base", base_branch)
check("CLI: unmerged scenario exits 1", r.returncode == 1, r.stdout + r.stderr)
check("CLI: unmerged scenario prints UNSAFE", r.stdout.startswith("UNSAFE:"), r.stdout)

r = run_cli(os.path.join(tempfile.gettempdir(), "wcc-does-not-exist-xyz"))
check("CLI: nonexistent path exits 2", r.returncode == 2, r.stdout + r.stderr)


passed = sum(1 for ok, _ in results if ok)
print("\nworktree-cleanup-check tests: %d/%d passed" % (passed, len(results)))
sys.exit(0 if passed == len(results) else 1)
