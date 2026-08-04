#!/usr/bin/env python3
"""Safety check before removing a git worktree as "stale cleanup".

WHY (2026-08-04, this session's own near-miss): mid-cleanup of what looked like a
batch of merged, disposable worktrees, one of them -- oi072-append-event-log --
actually held a real, independently-reviewed, unmerged commit. `git worktree list`
alone shows a branch name and a HEAD sha; it does not say whether that HEAD is an
ancestor of main, and eyeballing "does this branch name look like leftover chore
work" is exactly the judgment call that almost deleted reviewed work. This is the
mechanical version of the check that should have run first: clean working tree AND
HEAD is an ancestor of the base branch, together, or it is NOT safe cleanup fodder.

Stdlib only. Windows (`python`).
"""
import os
import subprocess
import sys

# Scrubbed here for the same reason isolated_commit.py scrubs it (2026-08-04
# independent review, minor note 3): git exports these to hook subprocesses,
# and this module lives under hooks/lib, so an inherited GIT_DIR would
# silently redirect every check here at whatever repo that variable names
# instead of the `worktree_path` the caller asked about.
_GIT_ENV_VARS = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR",
                 "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES",
                 "GIT_PREFIX")


def _clean_env():
    env = dict(os.environ)
    for v in _GIT_ENV_VARS:
        env.pop(v, None)
    return env


def _run(repo, *args):
    # encoding="utf-8" explicit, not implied by text=True: see isolated_commit.py's
    # identical fix for the live failure this avoids -- text=True alone falls back
    # to the OS locale codepage (cp1252 on this machine), which cannot decode
    # UTF-8 branch names, commit messages, or file paths that reach git's output.
    return subprocess.run(["git", "-C", repo] + list(args),
                          capture_output=True, text=True, encoding="utf-8",
                          env=_clean_env())


def is_clean(worktree_path):
    """True if `git status --porcelain` reports nothing -- no uncommitted
    changes, staged or not, tracked or not."""
    p = _run(worktree_path, "status", "--porcelain")
    return p.returncode == 0 and p.stdout.strip() == ""


def head_ref(worktree_path):
    """The worktree's current branch name, or its bare commit sha if HEAD is
    detached. A detached HEAD's `--abbrev-ref` is the literal string "HEAD",
    which is not a usable ref for merge-base comparison -- detect that case and
    fall back to the resolved sha explicitly rather than silently comparing
    the wrong thing (which would make every detached worktree look unmerged
    even when its exact commit is main's own tip)."""
    p = _run(worktree_path, "rev-parse", "--abbrev-ref", "HEAD")
    if p.returncode != 0:
        return None
    name = p.stdout.strip()
    if name and name != "HEAD":
        return name
    p2 = _run(worktree_path, "rev-parse", "HEAD")
    if p2.returncode != 0:
        return None
    return p2.stdout.strip() or None


def is_merged(worktree_path, ref, base="main"):
    """True if `ref` (a branch name or commit sha) is an ancestor of `base` --
    i.e. every commit reachable from `ref` is already reachable from `base`,
    so nothing would be lost by deleting `ref`. False if it genuinely is not
    an ancestor. Run FROM `worktree_path` so a linked worktree's shared
    object store is used without the caller having to separately locate the
    main checkout.

    `git merge-base --is-ancestor` exits 0 (ancestor) or 1 (not an ancestor)
    for a normal comparison, but ALSO exits with other codes (128, typically)
    when `base` (or `ref`) does not resolve at all -- e.g. a `--base main`
    default check run against a repo whose default branch is `master`.
    Collapsing that into "not merged" (independent review, minor note 2)
    would misreport a bad `--base` argument as "unmerged commits would be
    lost", which reads as a real merge-safety finding when it is actually a
    caller error. Raises RuntimeError for that case instead so
    `check_worktree` can report it distinctly."""
    p = _run(worktree_path, "merge-base", "--is-ancestor", ref, base)
    if p.returncode == 0:
        return True
    if p.returncode == 1:
        return False
    raise RuntimeError(
        "worktree_cleanup_check: could not compare %s against base %r -- "
        "does the base ref exist? git says: %s" % (
            ref, base, (p.stderr or "").strip()[:300]))


def check_worktree(worktree_path, base="main"):
    """Full verdict for one worktree. Never raises -- an inspection tool that
    can crash mid-sweep is worse than one that reports UNSAFE with a reason,
    since a caller checking N worktrees should not have one bad path abort the
    whole pass. `result["ref"] is None` means the path could not be inspected
    at all (not a directory, or not a git worktree) -- treat that as UNSAFE
    too, never as "nothing to check"."""
    result = {"worktree": worktree_path, "ref": None, "clean": False,
              "merged": False, "safe": False, "reason": ""}
    if not os.path.isdir(worktree_path):
        result["reason"] = "not a directory"
        return result
    ref = head_ref(worktree_path)
    if ref is None:
        result["reason"] = "could not resolve HEAD -- not a git worktree?"
        return result
    result["ref"] = ref
    result["clean"] = is_clean(worktree_path)
    try:
        result["merged"] = is_merged(worktree_path, ref, base)
    except RuntimeError as e:
        # merged stays False (the dataclass-ish default), safe stays False --
        # a caller reading only `result["safe"]` still gets the conservative
        # answer, but `reason` now says WHY distinctly from a real "unmerged
        # commits would be lost" finding (independent review, minor note 2).
        result["reason"] = "could not determine merge status: %s" % e
        return result
    if not result["clean"]:
        result["reason"] = "working tree has uncommitted changes"
    elif not result["merged"]:
        result["reason"] = ("HEAD (%s) is not an ancestor of %s -- unmerged "
                            "commits would be lost" % (ref, base))
    else:
        result["safe"] = True
        result["reason"] = "clean, and %s is merged into %s" % (ref, base)
    return result


def main():
    import argparse  # lazy: CLI-only, matches claim_work.py's convention
    p = argparse.ArgumentParser(
        description="Check whether a git worktree is safe to remove as stale "
                     "cleanup: clean working tree AND HEAD merged into --base. "
                     "Exits 0 if safe, 1 if unsafe, 2 on error.")
    p.add_argument("worktree", help="Path to the worktree to check")
    p.add_argument("--base", default="main",
                   help="Ref to check merge-ancestry against (default: main)")
    args = p.parse_args()

    result = check_worktree(args.worktree, base=args.base)
    if result["ref"] is None:
        print("ERROR: %s -- %s" % (result["worktree"], result["reason"]))
        return 2
    verdict = "SAFE" if result["safe"] else "UNSAFE"
    print("%s: %s (ref=%s, clean=%s, merged=%s) -- %s" % (
        verdict, result["worktree"], result["ref"], result["clean"],
        result["merged"], result["reason"]))
    return 0 if result["safe"] else 1


if __name__ == "__main__":
    sys.exit(main())
