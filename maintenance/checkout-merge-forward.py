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
  python maintenance/checkout-merge-forward.py --json --state-file <path>

BLOCKED DIAGNOSTICS (added 2026-09-12): on BLOCKED_DIRTY_OVERLAP the result
carries `blocked_paths` -- every path git named under its "would be
overwritten by merge" headers (tracked-modified and untracked alike) -- and
`detail` has git's LF->CRLF `warning:` lines stripped. Before this, the
500-char detail cap was consumed entirely by those warnings on the live
checkout, so the run never said WHICH files blocked it.

STATE FILE (added 2026-09-12): `--state-file` makes this script the sole
writer of the corrector's last-run record (previously hand-written by the
scheduled task). Beyond the legacy lastRun/status/commitsMerged/sha keys it
keeps `consecutiveUnsynced` (runs in a row that did not end MERGED or
NOOP_CLEAN -- reset to 0 by either), `unsyncedSince` (first run of the
current streak) and `blockedPaths`. A blocked result is routine for any ONE
day; a long streak means drift is compounding with nothing correcting it.
cross-repo-wip-scan.py reads this file weekly and escalates past its
threshold -- the threshold lives there, not here (one fact, one home).

STREAK ALARM (added 2026-09-12): the weekly check can sit a full week behind
the streak it reports. With --state-file, the JSON also carries
`streak_alarm`, true on the STREAK_ALARM_RUNS-th (14th) consecutive unsynced
run and then every STREAK_ALARM_REPEAT_RUNS (7) runs after that. The daily
scheduled task emails on it, so a two-week pin reaches the inbox without
waiting for Sunday, and the repeat interval keeps it from mailing every day.
Without --state-file the streak is unmeasured and `streak_alarm` is false.

Exit 0 = MERGED or NOOP_CLEAN (nothing needed doing). Exit 1 = BLOCKED_*
(needs a human, or was already blocked before this script touched anything).
Exit 2 = usage/tooling error (bad --repo, git missing, etc).
"""
import argparse
import datetime
import json
import os
import subprocess
import sys

DEFAULT_REPO = r"C:\Users\Owner\.claude"
DEFAULT_CANONICAL = "main"
SYNCED_STATUSES = ("MERGED", "NOOP_CLEAN")
_OVERLAP_HEADER = "would be overwritten by merge:"
STREAK_ALARM_RUNS = 14
STREAK_ALARM_REPEAT_RUNS = 7


def streak_alarm(consecutive_unsynced):
    """True at the 14th consecutive unsynced run, then every 7th after."""
    if not isinstance(consecutive_unsynced, int) or consecutive_unsynced < STREAK_ALARM_RUNS:
        return False
    return (consecutive_unsynced - STREAK_ALARM_RUNS) % STREAK_ALARM_REPEAT_RUNS == 0


def parse_overlap_paths(git_output):
    """Paths git lists under each 'would be overwritten by merge:' header
    (tracked-modified and untracked variants), in order, de-duplicated.
    Listed paths are tab/space-indented; the first unindented line ends a
    block."""
    paths, in_block = [], False
    for line in (git_output or "").splitlines():
        if _OVERLAP_HEADER in line:
            in_block = True
            continue
        if in_block and line[:1] in ("\t", " ") and line.strip():
            p = line.strip()
            if p not in paths:
                paths.append(p)
            continue
        in_block = False
    return paths


def _strip_warnings(text):
    return "\n".join(l for l in (text or "").splitlines()
                     if not l.startswith("warning:"))


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
           "commits_merged": None, "sha": None, "blocked_paths": None}

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

    raw = "\n".join(s for s in (merge_err, merge_out) if s)
    out["status"] = "BLOCKED_DIRTY_OVERLAP"
    out["blocked_paths"] = parse_overlap_paths(raw)
    out["detail"] = "git refused before writing anything (%d local path(s) overlap %s): %s" % (
        len(out["blocked_paths"]), target, _strip_warnings(raw)[:500])
    return out


def update_state(result, state_path, now_iso=None):
    """Write the corrector's last-run record, carrying the consecutive-
    unsynced streak forward from the prior file. A missing, corrupt, or
    legacy (pre-counter) prior file restarts the streak from this run.
    Atomic replace; raises OSError on an unwritable path (caller decides)."""
    now_iso = now_iso or datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    prior = {}
    try:
        with open(state_path, encoding="utf-8") as fh:
            loaded = json.load(fh)
        if isinstance(loaded, dict):
            prior = loaded
    except (OSError, ValueError):
        pass

    if result["status"] in SYNCED_STATUSES:
        streak, since = 0, None
    else:
        prev = prior.get("consecutiveUnsynced")
        prev = prev if isinstance(prev, int) and prev >= 0 else 0
        streak = prev + 1
        since = (prior.get("unsyncedSince") if prev > 0 else None) or now_iso

    state = {
        "lastRun": now_iso,
        "status": result["status"],
        "commitsMerged": result.get("commits_merged"),
        "sha": result.get("sha"),
        "consecutiveUnsynced": streak,
        "unsyncedSince": since,
        "blockedPaths": result.get("blocked_paths"),
    }
    parent = os.path.dirname(os.path.abspath(state_path))
    os.makedirs(parent, exist_ok=True)
    tmp = state_path + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(state, fh, indent=2)
        os.replace(tmp, state_path)
    except OSError:
        # An orphaned .tmp would itself age into cross-repo-wip-scan's WIP count.
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise
    return state


def main(argv=None):
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--repo", default=None)
    ap.add_argument("--canonical", default=None)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--state-file", default=None,
                    help="write/advance the last-run record (consecutiveUnsynced streak)")
    args = ap.parse_args(argv)

    r = sync(args.repo, args.canonical)
    r["streak_alarm"] = False
    if args.state_file:
        try:
            st = update_state(r, args.state_file)
            r["consecutive_unsynced"] = st["consecutiveUnsynced"]
            r["unsynced_since"] = st["unsyncedSince"]
            r["streak_alarm"] = streak_alarm(st["consecutiveUnsynced"])
        except OSError as e:
            # Best-effort: a state-write failure never changes the sync verdict.
            r["state_error"] = str(e)
    if args.json:
        print(json.dumps(r, indent=2))
    else:
        print("%s %s (%s): %s" % (r["status"], r["repo"], r["canonical"], r["detail"]))
    return 0 if r["status"] in ("MERGED", "NOOP_CLEAN") else (2 if r["status"] == "ERROR" else 1)


if __name__ == "__main__":
    sys.exit(main())
