#!/usr/bin/env python3
"""Safe, unattended merge-forward sync for a repo with a declared canonical
branch (open-items-tracker.md#OI-249, candidate (a)).

WHY: the primary `~/.claude` checkout sat on `feat/model-canary-probe-step25`
for weeks, was merged into `main` once (2026-08-23) without its own HEAD ever
moving back, and re-diverged to 40+ commits behind -- found three times by
accident. `cross-repo-wip-scan.py` (candidate (c), landed same day) now
DETECTS that drift on a weekly cadence. This script is the paired CORRECTOR:
it keeps the checkout's current branch merged forward with `origin/main` so
drift never has the chance to compound, WITHOUT ever requiring the checkout
to be clean first (unlike actually switching HEAD to `main`, which is what
"resolved" this twice before without fixing anything).

SAFETY MODEL -- this repo is shared across a dozen+ concurrent sessions, so
every step is designed to either land a clean merge commit or leave the
checkout in EXACTLY the state it was found in. Never a partial/stuck state.

  1. Refuse to run at all if the index already has ANYTHING staged
     (`git diff --cached` non-empty). A bare `git commit` after the merge
     would sweep that stranger's staged content into the merge commit --
     the exact hazard documented in feedback_git_index_is_shared_state.md,
     and one this session hit for real (another session's staged
     hooks/eos-review-gate.py) while triaging this very repo. BLOCKED_STAGED,
     never attempted.
  2. `git fetch origin <canonical>` -- read-only against the working tree,
     only updates the remote-tracking ref.
  3. If HEAD is already 0 commits behind `origin/<canonical>`: NOOP_CLEAN,
     nothing to do.
  4. Attempt `git merge --no-commit --no-ff origin/<canonical>`.
       - Exit 0 (no conflicts): the index now holds the merge result and
         NOTHING else (guaranteed by step 1) -- `git commit --no-edit` is
         safe. MERGED, report the new sha and how many commits it closed.
       - Exit != 0 with a MERGE_HEAD present: a REAL textual conflict.
         `git merge --abort` immediately, fully restoring the pre-merge
         state (working tree, index, HEAD all untouched) -- this is the one
         shape that genuinely needs a human. BLOCKED_CONFLICT, never left
         mid-merge for someone else to trip over.
       - Exit != 0 with no MERGE_HEAD: git refused before writing anything
         (uncommitted local changes overlap the incoming diff -- the
         ordinary case on this checkout, since it usually carries a large
         WIP backlog). Nothing to abort; the tree was never touched.
         BLOCKED_DIRTY_OVERLAP.

Never runs `git add -A`, never touches any path outside the merge/commit it
performs, never resets/rebases/force-anything. Detection-only companion:
cross-repo-wip-scan.py (weekly, alarms on drift regardless of whether this
script could act on it).

  python maintenance/checkout-merge-forward.py                # ~/.claude, main
  python maintenance/checkout-merge-forward.py --repo <path> --canonical main
  python maintenance/checkout-merge-forward.py --json

Exit 0 = MERGED or NOOP_CLEAN (nothing needed doing). Exit 1 = BLOCKED_*
(needs a human, or was already blocked before this script touched anything).
Exit 2 = usage/tooling error (bad --repo, git missing, etc).
"""
import argparse
import json
import subprocess
import sys

DEFAULT_REPO = r"C:\Users\Owner\.claude"
DEFAULT_CANONICAL = "main"


def _git(args, repo):
    """(rc, stdout, stderr) -- never raises on a non-zero/missing git."""
    try:
        p = subprocess.run(
            ["git"] + args, cwd=repo, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        return 127, "", str(e)
    return p.returncode, (p.stdout or "").strip(), (p.stderr or "").strip()


def sync(repo=None, canonical=None):
    repo = repo or DEFAULT_REPO
    canonical = canonical or DEFAULT_CANONICAL
    out = {"repo": repo, "canonical": canonical, "status": None, "detail": None,
           "commits_merged": None, "sha": None}

    rc, _, err = _git(["rev-parse", "--git-dir"], repo)
    if rc != 0:
        out["status"] = "ERROR"
        out["detail"] = "not a git repo: %s" % err
        return out

    rc, staged, _ = _git(["diff", "--cached", "--name-only"], repo)
    if rc != 0:
        out["status"] = "ERROR"
        out["detail"] = "cannot read the index"
        return out
    if staged:
        out["status"] = "BLOCKED_STAGED"
        out["detail"] = "another session's content is already staged: %s" % (
            ", ".join(staged.splitlines()[:10]))
        return out  # never attempted anything -- tree untouched.

    rc, _, err = _git(["fetch", "origin", canonical], repo)
    if rc != 0:
        out["status"] = "ERROR"
        out["detail"] = "fetch failed: %s" % err
        return out

    target = "origin/%s" % canonical
    rc, count_out, _ = _git(["rev-list", "--count", "HEAD..%s" % target], repo)
    if rc != 0 or not count_out.isdigit():
        out["status"] = "ERROR"
        out["detail"] = "cannot count commits behind %s" % target
        return out
    behind = int(count_out)
    if behind == 0:
        out["status"] = "NOOP_CLEAN"
        out["detail"] = "already up to date with %s" % target
        out["commits_merged"] = 0
        return out

    rc, merge_out, merge_err = _git(
        ["merge", "--no-commit", "--no-ff", target], repo)
    if rc == 0:
        rc2, _, commit_err = _git(["commit", "--no-edit"], repo)
        if rc2 != 0:
            # Should not happen given the staged-index guard above, but
            # never claim success on an unverified commit.
            out["status"] = "ERROR"
            out["detail"] = "merge staged cleanly but commit failed: %s" % commit_err
            return out
        rc3, sha, _ = _git(["rev-parse", "HEAD"], repo)
        out["status"] = "MERGED"
        out["commits_merged"] = behind
        out["sha"] = sha if rc3 == 0 else None
        out["detail"] = "merged %d commit(s) from %s" % (behind, target)
        return out

    rc_head, merge_head, _ = _git(["rev-parse", "-q", "--verify", "MERGE_HEAD"], repo)
    if rc_head == 0 and merge_head:
        _git(["merge", "--abort"], repo)
        out["status"] = "BLOCKED_CONFLICT"
        out["detail"] = "textual conflict merging %s -- aborted, tree restored: %s" % (
            target, (merge_out or merge_err)[:500])
        return out

    out["status"] = "BLOCKED_DIRTY_OVERLAP"
    out["detail"] = "git refused before writing anything (local changes overlap %s): %s" % (
        target, (merge_err or merge_out)[:500])
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--repo", default=None)
    ap.add_argument("--canonical", default=None)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    r = sync(args.repo, args.canonical)
    if args.json:
        print(json.dumps(r, indent=2))
    else:
        print("%s %s (%s): %s" % (r["status"], r["repo"], r["canonical"], r["detail"]))
    return 0 if r["status"] in ("MERGED", "NOOP_CLEAN") else (2 if r["status"] == "ERROR" else 1)


if __name__ == "__main__":
    sys.exit(main())
