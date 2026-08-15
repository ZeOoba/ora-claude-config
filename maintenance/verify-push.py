#!/usr/bin/env python3
"""Verify that a push actually landed: local HEAD == the remote branch tip.

WHY (this check existed NOWHERE before 2026-08-14): nothing in this setup ever
confirmed, after pushing, that the remote branch had actually moved. Success was
asserted from the push command's own exit status -- and that status is not
trustworthy. Piping the push into `tail` reported exit 0 while the push had in
fact FAILED; only an unpiped re-run surfaced the real exit 1 (memory:
feedback_piped_gate_exit_masking). That produced at least one false
"push succeeded" claim.

So this tool is deliberately built to be immune to that class of failure:

  * It NEVER consults the push's exit code, and never runs a push itself. It
    re-derives the truth from the remote via `ls-remote` and compares it to
    local HEAD. Whatever the push claimed is irrelevant here.
  * It uses `ls-remote` rather than the local `origin/<branch>` tracking ref,
    because a tracking ref is a cache -- it can be stale, and a stale cache that
    happens to match HEAD is exactly a false green. `ls-remote` asks the remote.
  * Its exit code is the primary signal, but it ALSO prints a machine-readable
    RESULT_JSON line, so that a caller who pipes it (and thereby masks the exit
    code -- the original defect) can still see the verdict in the output.
  * Every distinguishable failure mode gets its OWN exit code. "I could not
    reach the remote" is not "they differ", and neither is "no upstream". A
    verified null and an inferred null are different findings; collapsing them
    into one generic failure is how ambiguous results get read as green.

Both shas are printed on EVERY outcome where they are known -- success included
-- so the output is directly pasteable as evidence.

Read-only. Runs `rev-parse`, `symbolic-ref`, `config --get`, `ls-remote`,
`fetch` (of a single ref, for the ahead/behind counts only) and `rev-list`.
Never touches the working tree, the index, HEAD, or any branch.

Usage:
    python maintenance/verify-push.py [--repo PATH] [--branch NAME]
                                      [--remote NAME] [--timeout SECS]

    --repo    repo to check (default: cwd)
    --branch  branch to verify (default: the current branch; required when HEAD
              is detached, which is the normal state inside a worktree)
    --remote  remote to ask (default: the branch's configured upstream remote)

Exit codes:
    0  MATCH                  local HEAD == remote branch tip -- push verified
    1  DIVERGED               they differ (ahead/behind counts reported)
    2  NOT_A_REPO             --repo is not a git repository (or is unreadable)
    3  DETACHED_HEAD          HEAD is detached and no --branch was given
    4  NO_UPSTREAM            branch has no configured upstream remote
    5  REMOTE_UNREACHABLE     could not reach the remote -- verified NOTHING
    6  REMOTE_BRANCH_MISSING  remote is reachable; the branch is not on it
    7  NO_COMMITS             repo has no commits, so HEAD resolves to nothing
"""
import argparse
import json
import os
import subprocess
import sys

EXIT_MATCH = 0
EXIT_DIVERGED = 1
EXIT_NOT_A_REPO = 2
EXIT_DETACHED_HEAD = 3
EXIT_NO_UPSTREAM = 4
EXIT_REMOTE_UNREACHABLE = 5
EXIT_REMOTE_BRANCH_MISSING = 6
EXIT_NO_COMMITS = 7

STATUS = {
    EXIT_MATCH: "MATCH",
    EXIT_DIVERGED: "DIVERGED",
    EXIT_NOT_A_REPO: "NOT_A_REPO",
    EXIT_DETACHED_HEAD: "DETACHED_HEAD",
    EXIT_NO_UPSTREAM: "NO_UPSTREAM",
    EXIT_REMOTE_UNREACHABLE: "REMOTE_UNREACHABLE",
    EXIT_REMOTE_BRANCH_MISSING: "REMOTE_BRANCH_MISSING",
    EXIT_NO_COMMITS: "NO_COMMITS",
}

DEFAULT_TIMEOUT = 60
UNKNOWN = "(unknown)"


def _say(msg):
    print("[verify-push] " + msg)


def _finish(code, repo, branch, remote, local_sha, remote_sha,
            ahead, behind, detail, remote_ref=None):
    """Print the human block, then the pipe-proof machine line, then exit.

    The verdict word and both shas go to stdout on EVERY path, so neither a
    swallowed exit code nor a truncating pipe can turn a failure into a green.

    Every label names the ref ACTUALLY compared (remote_ref), never a
    reconstructed `<remote>/<branch>`: a local branch can track a
    differently-named remote ref, and a label that misnames what it compared is
    the same species of misleading evidence this tool exists to kill.
    """
    status = STATUS.get(code, "UNKNOWN")
    target = ("%s %s" % (remote, remote_ref)) if (remote and remote_ref) else None
    _say("repo      : %s" % repo)
    _say("branch    : %s%s" % (branch or UNKNOWN,
                               ("  ->  %s" % target) if target else ""))
    _say("local  HEAD      : %s" % (local_sha or UNKNOWN))
    _say("remote branch tip: %s" % (remote_sha or UNKNOWN))
    if ahead is not None and behind is not None:
        _say("ahead %d / behind %d  (local-only / remote-only commits)" % (ahead, behind))
    else:
        _say("ahead ? / behind ?  (not computed -- see detail)")
    if detail:
        _say(detail)
    _say("VERDICT: %s" % status)
    print("RESULT_JSON=" + json.dumps({
        "status": status,
        "match": code == EXIT_MATCH,
        "exit_code": code,
        "repo": repo,
        "branch": branch,
        "remote": remote,
        "remote_ref": remote_ref,
        "local_sha": local_sha,
        "remote_sha": remote_sha,
        "ahead": ahead,
        "behind": behind,
        "detail": detail,
    }, sort_keys=True))
    sys.exit(code)


def main():
    ap = argparse.ArgumentParser(
        description="Verify local HEAD matches the remote branch tip.")
    ap.add_argument("--repo", default=None, help="repo path (default: cwd)")
    ap.add_argument("--branch", default=None,
                    help="branch to verify (default: current branch)")
    ap.add_argument("--remote", default=None,
                    help="remote name (default: the branch's upstream remote)")
    ap.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT,
                    help="seconds allowed for each remote call (default %d)" % DEFAULT_TIMEOUT)
    args = ap.parse_args()

    repo = os.path.abspath(args.repo or os.getcwd())

    def git(argv, timeout=15):
        """Run read-only git. Returns (rc, stdout, stderr); rc 124 on timeout.

        Never raises -- a crash here would be indistinguishable from a clean
        verification, which is the failure mode this whole tool exists to kill.
        """
        try:
            p = subprocess.run(["git", "-C", repo] + argv,
                               capture_output=True, text=True, timeout=timeout)
            return p.returncode, (p.stdout or "").strip(), (p.stderr or "").strip()
        except subprocess.TimeoutExpired:
            return 124, "", "timed out after %ss" % timeout
        except Exception as exc:  # git missing, path gone, permissions
            return 125, "", str(exc)

    fail = lambda code, detail, **kw: _finish(  # noqa: E731
        code, repo, kw.get("branch"), kw.get("remote"),
        kw.get("local_sha"), kw.get("remote_sha"), None, None, detail,
        kw.get("remote_ref"))

    # --- 1. is this a git repo at all -------------------------------------
    if not os.path.isdir(repo):
        fail(EXIT_NOT_A_REPO, "path does not exist or is not a directory")
    rc, _out, err = git(["rev-parse", "--git-dir"])
    if rc != 0:
        fail(EXIT_NOT_A_REPO, "not a git repository: %s" % (err or "rev-parse failed"))

    # --- 2. local HEAD ----------------------------------------------------
    rc, local_sha, err = git(["rev-parse", "HEAD"])
    if rc != 0 or not local_sha:
        fail(EXIT_NO_COMMITS,
             "HEAD does not resolve to a commit (empty repo?): %s" % (err or "no output"))

    # --- 3. which branch --------------------------------------------------
    branch = args.branch
    if not branch:
        rc, cur, _err = git(["symbolic-ref", "--quiet", "--short", "HEAD"])
        if rc != 0 or not cur:
            fail(EXIT_DETACHED_HEAD,
                 "HEAD is detached -- pass --branch NAME to name the branch the "
                 "push was supposed to land on",
                 local_sha=local_sha)
        branch = cur

    # --- 4. which remote, and under what name does the branch live there --
    # `branch.<b>.merge` is the authority for the remote-side ref name: a local
    # branch may be pushed under a different name, and comparing against the
    # wrong remote ref would be a false verdict either way.
    remote = args.remote
    if not remote:
        rc, configured, _err = git(["config", "--get", "branch.%s.remote" % branch])
        if rc != 0 or not configured:
            fail(EXIT_NO_UPSTREAM,
                 "branch '%s' has no configured upstream remote -- nothing to "
                 "verify against (push with -u, or pass --remote)" % branch,
                 branch=branch, local_sha=local_sha)
        remote = configured

    rc, merge_ref, _err = git(["config", "--get", "branch.%s.merge" % branch])
    remote_ref = merge_ref if (rc == 0 and merge_ref.startswith("refs/")) \
        else "refs/heads/%s" % branch

    # --- 5. ask the REMOTE, not the local tracking ref --------------------
    # --exit-code makes "no such ref" (rc 2) distinguishable from "could not
    # reach you at all" (rc 128) -- the distinction the exit-code table rests on.
    rc, out, err = git(["ls-remote", "--exit-code", remote, remote_ref],
                       timeout=args.timeout)
    if rc == 2:
        fail(EXIT_REMOTE_BRANCH_MISSING,
             "remote '%s' is reachable but %s does not exist on it -- the push "
             "did NOT land" % (remote, remote_ref),
             branch=branch, remote=remote, remote_ref=remote_ref, local_sha=local_sha)
    if rc != 0:
        fail(EXIT_REMOTE_UNREACHABLE,
             "remote '%s' unreachable -- verified NOTHING (this is not a "
             "divergence finding): %s" % (remote, err or "ls-remote failed"),
             branch=branch, remote=remote, remote_ref=remote_ref, local_sha=local_sha)
    remote_sha = out.split()[0] if out.split() else ""
    if not remote_sha:
        fail(EXIT_REMOTE_UNREACHABLE,
             "remote '%s' returned no sha for %s -- verified NOTHING"
             % (remote, remote_ref),
             branch=branch, remote=remote, remote_ref=remote_ref, local_sha=local_sha)

    # --- 6. ahead/behind counts (best effort) -----------------------------
    # The verdict is already decided by the two shas above; this fetch exists
    # only so the counts can be reported. If it fails, the counts go unknown --
    # the verdict does NOT degrade.
    ahead = behind = None
    git(["fetch", "--quiet", remote, remote_ref], timeout=args.timeout)
    rc, _o, _e = git(["cat-file", "-e", remote_sha + "^{commit}"])
    if rc == 0:
        rc, counts, _err = git(["rev-list", "--left-right", "--count",
                                "HEAD...%s" % remote_sha])
        parts = counts.split() if rc == 0 else []
        if len(parts) == 2:
            try:
                ahead, behind = int(parts[0]), int(parts[1])
            except ValueError:
                ahead = behind = None

    # --- 7. verdict -------------------------------------------------------
    if local_sha == remote_sha:
        _finish(EXIT_MATCH, repo, branch, remote, local_sha, remote_sha,
                ahead if ahead is not None else 0,
                behind if behind is not None else 0,
                "push VERIFIED: %s %s tip equals local HEAD" % (remote, remote_ref),
                remote_ref)
    _finish(EXIT_DIVERGED, repo, branch, remote, local_sha, remote_sha,
            ahead, behind,
            "local HEAD and %s %s DIFFER -- do not claim the push succeeded"
            % (remote, remote_ref),
            remote_ref)


if __name__ == "__main__":
    main()
