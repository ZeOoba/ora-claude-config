#!/usr/bin/env python3
"""Push HEAD to a remote branch, surviving a lost race with a bounded fetch + rebase + retry.

WHY (OI-353, 2026-09-23): every push to ~/.claude runs the ~11-min pre-push gate, and on a
busy day other sessions land on main inside that window, so the push is rejected
(`cannot lock ref 'refs/heads/main': is at X but expected Y`, or git's own fetch-first /
non-fast-forward refusal). That hit the heartbeat backup push on two consecutive runs and
two manual session pushes on the same day. Each time the fix was the same by hand: fetch,
rebase the unpushed commits onto the new tip, push again. This tool does exactly that, and
nothing more clever.

Rules (each is a refusal, never a workaround):
  * Never forces, never skips hooks, never autostashes. The pre-push gate runs on every
    attempt, like any manual push.
  * Touches nothing while another operation is mid-flight in this worktree (rebase, merge,
    cherry-pick, revert, bisect) -- it may be another session's, and aborting it would
    destroy their work. The only rebase this tool ever aborts is one it started itself.
  * Rebases ONLY a clean tree: any tracked-file change, or any skip-worktree /
    assume-unchanged entry (invisible to `git status`) -> refuse before touching anything.
    Untracked files are fine.
  * Rebases ONLY linear, never-pushed work: a merge commit among the unpushed commits, or a
    commit already present on ANY remote ref (e.g. a feature branch already pushed to its
    own upstream), -> refuse. Rebasing those would flatten a merge or fork published
    history. Merge-based reconcile belongs to the caller -- e.g. push-fleet-heartbeat.ps1.
  * A rebase conflict is aborted immediately; HEAD and the tree are left as found.
  * Only a lost race is retried, judged from git's own porcelain status line for the
    target ref -- never from the gate's log, which can contain race-looking test output.
    Any other failure (gate, auth, network) is reported once. Retries: default 1, max 3.
  * Sparse checkouts are always refused (out-of-cone entries read as skip-worktree). A commit
    once on a since-deleted remote branch reads as ALREADY_PUBLISHED until `git fetch --prune`
    drops the stale remote-tracking ref -- fails safe.
  * The target branch must already exist on the remote (first push of a new branch: use a
    plain `git push`).

Exit codes (RESULT_JSON line printed on every outcome, so a piped caller still sees it):
  0 PUSHED / NOTHING_TO_PUSH   1 PUSH_FAILED (not a race)
  2 LOST_RACE (retries used up)   3 DIRTY_TREE
  4 REBASE_CONFLICT / REBASE_FAILED / REBASE_ABORT_FAILED   5 MERGES_IN_RANGE / ALREADY_PUBLISHED
  6 USAGE / FETCH_FAILED / GIT_ERROR   7 OPERATION_IN_PROGRESS   8 PUSHED_UNVERIFIED (push exited 0, remote not re-readable)
After a push reports success, the remote tip is re-read with ls-remote (verify-push.py's
rule: a push's own exit status is not evidence). If another session landed on top in the
meantime, the push still counts when HEAD is an ancestor of the new tip.

Usage:
    python maintenance/safe-push.py --to main [--repo PATH] [--remote origin] [--retries 1]
"""
import argparse
import json
import os
import re
import subprocess
import sys

MAX_RETRIES = 3
IN_PROGRESS = ("rebase-merge", "rebase-apply", "MERGE_HEAD", "CHERRY_PICK_HEAD", "REVERT_HEAD", "BISECT_LOG")
# git push --porcelain status line: <flag>\t<from>:<to>\t<summary> (<reason>)
# Reasons git reports for "the ref moved under us": client-side (fetch first, non-fast-forward),
# GitHub receive-pack (cannot lock ref ... but expected), stock receive-pack (incorrect old value).
RACE_REASON = re.compile(r"\((fetch first|non-fast-forward|incorrect old value provided|cannot lock ref '[^']*': is at \S+ but expected \S+)\)")

try:
    sys.stdout.reconfigure(errors="replace")
except (AttributeError, ValueError):
    pass


def git(repo, *args):
    r = subprocess.run(["git", "-C", repo, *args], capture_output=True,
                       encoding="utf-8", errors="replace")
    return r.returncode, (r.stdout or "").strip(), (r.stderr or "").strip()


def git_path(repo, name):
    """Per-worktree path of a .git state file (rebase-merge, MERGE_HEAD, ...)."""
    return os.path.join(repo, git(repo, "rev-parse", "--git-path", name)[1])


def own_rebase(repo, head0, err):
    """True only for a rebase THIS run started: its state dir exists, git did not refuse because
    one already existed, and its saved orig-head is the HEAD we had just before. A concurrent
    run's rebase in the same checkout (both past the up-front check) fails the orig-head test."""
    if "already a rebase-merge directory" in err or "rebase-apply directory" in err:
        return False
    for n in ("rebase-merge", "rebase-apply"):
        d = git_path(repo, n)
        if os.path.isdir(d):
            try:
                with open(os.path.join(d, "orig-head"), encoding="utf-8") as f:
                    return f.read().strip() == head0
            except OSError:
                return False
    return False


def ref_status_lines(output, target):
    """git's own porcelain status line(s) for refs/heads/<target>; hook output never matches."""
    pat = re.compile(r"^([ +\-*!=])\t[^\t]*:refs/heads/%s\t(.*)$" % re.escape(target))
    lines = output.splitlines()
    # git prints its status block after "To <url>"; anything before it (the pre-push gate's
    # log, which can echo these very tests' output) is never read.
    starts = [i for i, l in enumerate(lines) if l.startswith("To ")]
    block = lines[starts[-1] + 1:] if starts else []
    return [(m.group(1), m.group(2)) for m in (pat.match(l) for l in block) if m]


def is_race(output, target):
    return any(flag == "!" and RACE_REASON.search(summary) for flag, summary in ref_status_lines(output, target))


def push_streaming(repo, remote, target):
    """Run the push, echoing output live (the gate is long) and returning (rc, text)."""
    p = subprocess.Popen(["git", "-C", repo, "push", "--porcelain", remote, "HEAD:refs/heads/" + target],
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         encoding="utf-8", errors="replace", bufsize=1)
    lines = []
    for line in p.stdout:
        sys.stdout.write(line)
        sys.stdout.flush()
        lines.append(line)
    return p.wait(), "".join(lines)


def finish(code, verdict, **info):
    info.update(verdict=verdict, exit=code)
    print("safe-push: " + verdict + ("" if not info.get("detail") else " -- " + info["detail"]))
    print("RESULT_JSON=" + json.dumps(info, sort_keys=True))
    sys.exit(code)


def must(base, rc, out, err, what, attempts):
    if rc != 0:
        finish(6, "GIT_ERROR", detail="%s failed: %s" % (what, err[-300:]), attempts=attempts, **base)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--to", required=True, help="existing remote branch to push HEAD to (e.g. main)")
    ap.add_argument("--repo", default=".")
    ap.add_argument("--remote", default="origin")
    ap.add_argument("--retries", type=int, default=1, help="lost-race retries (default 1, max %d)" % MAX_RETRIES)
    a = ap.parse_args()
    base = {"repo": a.repo, "remote": a.remote, "target": a.to}
    if not 0 <= a.retries <= MAX_RETRIES:
        finish(6, "USAGE", detail="--retries must be 0..%d" % MAX_RETRIES, **base)
    if git(a.repo, "rev-parse", "--git-dir")[0] != 0:
        finish(6, "USAGE", detail="not a git repo: " + a.repo, **base)
    if git(a.repo, "check-ref-format", "--branch", a.to)[0] != 0 or any(c in a.to for c in ":*?[\\ "):
        finish(6, "USAGE", detail="--to is not a plain branch name: %r" % a.to, **base)
    if not re.fullmatch(r"[A-Za-z0-9._-]+", a.remote) or git(a.repo, "remote", "get-url", a.remote)[0] != 0:
        finish(6, "USAGE", detail="--remote must be a configured remote name: %r" % a.remote, **base)

    busy = [n for n in IN_PROGRESS if os.path.exists(git_path(a.repo, n))]
    if busy:
        finish(7, "OPERATION_IN_PROGRESS", detail="in progress here (possibly another session's): " + ", ".join(busy)
               + " -- nothing touched", **base)

    dirty = must(base, *git(a.repo, "status", "--porcelain", "--untracked-files=no"), "git status", 0)
    hidden = [l for l in must(base, *git(a.repo, "ls-files", "-v"), "git ls-files", 0).splitlines()
              if l[:1].islower() or l[:1] == "S"]
    if dirty or hidden:
        finish(3, "DIRTY_TREE", detail="uncommitted tracked changes or hidden (skip-worktree/assume-unchanged) "
               "entries -- commit them or push from a clean worktree",
               paths=(dirty.splitlines() + hidden)[:20], **base)

    rc, remote_line, err = git(a.repo, "ls-remote", "--heads", a.remote, "refs/heads/" + a.to)
    if rc != 0:
        finish(6, "FETCH_FAILED", detail=err[-300:], attempts=0, **base)
    if not remote_line:
        finish(6, "USAGE", detail="%s/%s does not exist -- first push of a new branch: use plain git push"
               % (a.remote, a.to), **base)

    ref = "refs/remotes/%s/%s" % (a.remote, a.to)
    attempts = 0
    while True:
        rc, _, err = git(a.repo, "fetch", "-q", a.remote, "+refs/heads/%s:%s" % (a.to, ref))
        if rc != 0:
            finish(6, "FETCH_FAILED", detail=err[-300:], attempts=attempts, **base)
        ahead = must(base, *git(a.repo, "rev-list", "--count", ref + "..HEAD"), "rev-list ahead", attempts)
        if ahead == "0":
            finish(0, "NOTHING_TO_PUSH", attempts=attempts, **base)
        behind = must(base, *git(a.repo, "rev-list", "--count", "HEAD.." + ref), "rev-list behind", attempts)
        if behind != "0":
            merges = must(base, *git(a.repo, "rev-list", "--merges", ref + "..HEAD"), "rev-list merges", attempts)
            if merges:
                finish(5, "MERGES_IN_RANGE", detail="unpushed commits include a merge; reconcile by merge instead",
                       merges=merges.splitlines(), attempts=attempts, **base)
            unpublished = must(base, *git(a.repo, "rev-list", "--count", ref + "..HEAD", "--not", "--remotes"),
                               "rev-list unpublished", attempts)
            if unpublished != ahead:
                finish(5, "ALREADY_PUBLISHED", detail="%s of %s commit(s) to rebase already exist on a remote ref "
                       "(e.g. this branch's own upstream); rebasing would fork published history"
                       % (int(ahead) - int(unpublished), ahead), attempts=attempts, **base)
            print("safe-push: %s moved (%s new commit(s)) -- rebasing %s local commit(s) onto it" % (ref, behind, ahead))
            head0 = must(base, *git(a.repo, "rev-parse", "HEAD"), "rev-parse HEAD", attempts)
            rc, _, err = git(a.repo, "rebase", "-q", ref)
            if rc != 0:
                conflict = bool(git(a.repo, "diff", "--name-only", "--diff-filter=U")[1])
                verdict = "REBASE_CONFLICT" if conflict else "REBASE_FAILED"
                if not own_rebase(a.repo, head0, err):
                    finish(4, verdict, detail="rebase did not start as ours (another operation owns the rebase "
                           "state -- possibly a concurrent run); nothing aborted. " + err[-300:],
                           attempts=attempts, **base)
                arc, _, aerr = git(a.repo, "rebase", "--abort")
                if arc != 0:
                    finish(4, "REBASE_ABORT_FAILED", detail="our rebase failed AND its abort failed -- inspect by "
                           "hand: " + (aerr or err)[-300:], attempts=attempts, **base)
                finish(4, verdict, detail="rebase aborted; HEAD and tree left as found. " + err[-300:],
                       attempts=attempts, **base)

        attempts += 1
        rc, out = push_streaming(a.repo, a.remote, a.to)
        if rc == 0:
            head = must(base, *git(a.repo, "rev-parse", "HEAD"), "rev-parse HEAD", attempts)
            rc2, line, err = git(a.repo, "ls-remote", a.remote, "refs/heads/" + a.to)
            tip = line.split()[0] if (rc2 == 0 and line) else ""
            if tip == head:
                finish(0, "PUSHED", head=head, attempts=attempts, **base)
            # someone may have landed on top already: still ours if HEAD is in the new tip's history
            frc, _, ferr = git(a.repo, "fetch", "-q", a.remote, "+refs/heads/%s:%s" % (a.to, ref))
            if frc != 0 or rc2 != 0:
                finish(8, "PUSHED_UNVERIFIED", head=head, detail="push exited 0 but the remote could not be re-read "
                       "to confirm (%s) -- rerun: NOTHING_TO_PUSH confirms it landed"
                       % (ferr or "ls-remote failed")[-200:], attempts=attempts, **base)
            if git(a.repo, "merge-base", "--is-ancestor", head, ref)[0] == 0:
                finish(0, "PUSHED", head=head, tip=tip, detail="HEAD confirmed in remote history (tip %s)" % tip[:12],
                       attempts=attempts, **base)
            finish(1, "PUSH_FAILED", detail="push exited 0 but HEAD %s is not in remote tip %s"
                   % (head[:12], tip[:12] or "?"), attempts=attempts, **base)
        if not is_race(out, a.to):
            finish(1, "PUSH_FAILED", detail="not a lost race -- not retried", attempts=attempts, **base)
        if attempts > a.retries:
            finish(2, "LOST_RACE", detail="remote kept moving; gave up after %d attempt(s)" % attempts,
                   attempts=attempts, **base)
        print("safe-push: lost the race (remote moved during the push) -- retry %d/%d" % (attempts, a.retries))


if __name__ == "__main__":
    main()
