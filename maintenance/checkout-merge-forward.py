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

  0a. Refuse if a merge, cherry-pick, revert, rebase, paused cherry-pick/revert
      sequence or bisect is ALREADY in progress (MERGE_HEAD / CHERRY_PICK_HEAD /
      REVERT_HEAD / rebase-merge / rebase-apply / sequencer / BISECT_START). A
      marker that cannot be checked (rev-parse exit other than 0 or 1) counts
      as in progress. Re-checked immediately before step 4's merge, because the
      fetch opens a window for another session to start one.
      BLOCKED_OP_IN_PROGRESS -- and never abort it: it may be another session's
      half-resolved conflict, or this script's own stranded merge from a run
      that died between merge and commit. Before this check (PR #193 review,
      2026-09-12) such a state has staged content, so it fell through to step 1
      and was misreported as a routine, silent BLOCKED_STAGED indefinitely.
  0b. Refuse if a live work claim (hooks/lib/claim_work.py) other than this
      task's own `sched-repo-housekeeping` overlaps this repo, or declares no
      paths and so cannot
      be proven disjoint. BLOCKED_CLAIMED. A merge forward rewrites arbitrary
      tracked paths, so any declared work inside the repo is contended. The
      task's own STEP 0 claim cannot enforce this: cross-slug claims only WARN,
      and claim_work's cross-slug check is one-directional. An unloadable
      claim_work is ERROR -- a safety check that cannot run is not a pass.
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
  3b. Compute the overlap READ-ONLY (added 2026-09-21): `git status --porcelain=v2
      -z --untracked-files=all` (tracked + untracked dirty paths) plus
      assume-unchanged / on-disk skip-worktree entries (`ls-files -v`; invisible to
      status, but git still refuses over them), intersected with the paths the
      merge would change (`git merge-tree --write-tree --name-only -z HEAD <sha>`:
      its result tree diffed against HEAD PLUS its conflicted-path list -- a
      modify/delete or binary conflict keeps HEAD's version in the result tree, so
      the diff alone misses it and the merge's --abort then REVERTED the dirty
      edit; fallback `HEAD...<sha>`), matching across directory
      boundaries and case-insensitively. Any overlap -> BLOCKED_DIRTY_OVERLAP with
      those paths, and `git merge` is NEVER invoked. Why: on a branch with its own
      commits, a refused `git merge` (ort, "would be overwritten") rewrites EVERY
      dirty tracked file -- content kept, but new mtime and LF->CRLF under
      core.autocrlf=true -- including files that do not overlap. The live 16:47
      run on 2026-09-21 did this to all 50 modified files in ~/.claude, resetting
      dirty-tree-triage's mtime settlement and breaking live sessions' Read->Edit.
      If the overlap cannot be computed: ERROR, never a blind merge.
  4. Attempt `git merge --no-commit --no-ff origin/<canonical>`.
       - Exit 0 (no conflicts): the index now holds the merge result and
         NOTHING else (git itself refuses a merge while anything is staged)
         -- `git commit --no-edit`. MERGED, report the new sha and how many
         commits it closed. If the COMMIT fails (routinely: a concurrent
         session's git command holding .git/index.lock at that instant), the
         merge is ABORTED and verified gone before returning ERROR. Before
         this fix it returned ERROR with MERGE_HEAD still present, leaving the
         shared checkout mid-merge -- every other session's pathspec commit
         then failed with "cannot do a partial commit during a merge".
       - Exit != 0 and git REFUSED to start ("have not concluded", "unmerged
         files", "unresolved conflict"), or MERGE_HEAD is unverifiable or names
         anything but the origin/<canonical> sha this run merged: the merge is
         not provably this run's. BLOCKED_OP_IN_PROGRESS, never aborted. The
         adversarial review of the first fix reproduced a session's merge that
         started during the fetch being aborted, destroying its staged resolution.
       - Exit != 0 with THIS run's MERGE_HEAD present: a REAL textual conflict.
         `git merge --abort` immediately, fully restoring the pre-merge
         state (working tree, index, HEAD all untouched) -- this is the one
         shape that genuinely needs a human. BLOCKED_CONFLICT, never left
         mid-merge for someone else to trip over.
       Every abort is retried (a lock holder is usually a short-lived git
       command) and then VERIFIED: `merge_aborted` reports whether MERGE_HEAD
       is actually gone, and a failed abort says "LEFT MID-MERGE" in `detail`
       rather than claiming the tree was restored.
       - Exit != 0 with no MERGE_HEAD: git refused (uncommitted local changes
         overlap the incoming diff in a way 3b did not see, e.g. a file dirtied
         between 3b and the merge). FALLBACK only -- the ordinary overlap case
         is caught by 3b. Nothing to abort, but dirty files may have been
         re-written (see 3b). BLOCKED_DIRTY_OVERLAP. If git named NO overlapping path (e.g. a
         stale .git/index.lock, which blocks every session's commits) it is
         ERROR instead, so it alarms rather than passing as routine.

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
`streak_alarm`, true on the STREAK_ALARM_RUNS-th consecutive unsynced run and
then every STREAK_ALARM_REPEAT_RUNS runs after that. The scheduled task emails
on it, so a two-week pin reaches the inbox. The thresholds express ELAPSED TIME:
14 / 7 runs while the task was daily, and 2 / 1 since it went weekly (Fri) on
2026-09-22. That still means "alarm at two weeks pinned, then weekly". Re-derive
both numbers if the cadence changes again.
Without --state-file the streak is unmeasured and `streak_alarm` is false.

Exit 0 = MERGED or NOOP_CLEAN (nothing needed doing). Exit 1 = BLOCKED_*
(needs a human, or was already blocked before this script touched anything).
Exit 2 = usage/tooling error (bad --repo, git missing, etc).
"""
import argparse
import datetime
import importlib.util
import json
import os
import subprocess
import sys
import time

DEFAULT_REPO = r"C:\Users\Owner\.claude"
DEFAULT_CANONICAL = "main"
SYNCED_STATUSES = ("MERGED", "NOOP_CLEAN")
# Second header: origin turns a tracked directory into a file while local
# untracked files sit inside it.
_OVERLAP_HEADERS = ("would be overwritten by merge:",
                    "would lose untracked files in them:")
STREAK_ALARM_RUNS = 2          # weekly cadence since 2026-09-22: 2 unsynced runs = 14 days since the last successful sync
STREAK_ALARM_REPEAT_RUNS = 1   # then every weekly run (was 7 daily runs = 7 days)

# In-progress operation markers (step 0a): refs, then git-path files/directories.
IN_PROGRESS_REFS = (("MERGE_HEAD", "merge"), ("CHERRY_PICK_HEAD", "cherry-pick"),
                    ("REVERT_HEAD", "revert"))
# Marker files/dirs under the git dir. `sequencer` covers a paused multi-commit
# cherry-pick/revert whose CHERRY_PICK_HEAD is already gone; BISECT_START a bisect.
IN_PROGRESS_PATHS = (("rebase-merge", "rebase"), ("rebase-apply", "rebase-apply"),
                     ("sequencer", "cherry-pick/revert sequence"), ("BISECT_START", "bisect"))

# `git merge` stderr when it REFUSES to start because an operation already exists.
# The merge then created nothing of its own, so there is nothing for this run to abort.
MERGE_REFUSAL_MARKERS = ("have not concluded", "unmerged files", "unresolved conflict")

# Abort retry (step 4): the usual lock holder is a short-lived git command.
ABORT_ATTEMPTS = 5
ABORT_RETRY_SECONDS = 1.0

# Work-claim gate (step 0b). The claims module lives in this same tree; the
# claims DIRECTORY is claim_work.CLAIMS_DIR (the live, machine-wide one) unless
# the test seam overrides it.
CLAIM_WORK_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                               "hooks", "lib", "claim_work.py")
CLAIMS_DIR_OVERRIDE = None
# Only THIS task's own STEP 0 claim is ignored. Other unattended tasks also claim
# under `sched-<slug>` and may be writing into this repo, so a prefix match would
# wave their work through.
OWN_CLAIM_SLUG = "sched-repo-housekeeping"


def streak_alarm(consecutive_unsynced):
    """True at the STREAK_ALARM_RUNS-th consecutive unsynced run, then every
    STREAK_ALARM_REPEAT_RUNS-th after (two weeks pinned, then weekly)."""
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
        if any(h in line for h in _OVERLAP_HEADERS):
            in_block = True
            continue
        if in_block and line[:1] in ("\t", " ") and line.strip():
            p = line.strip()
            if p not in paths:
                paths.append(p)
            continue
        in_block = False
    return paths


# `git status --porcelain=v2 -z` field count before the path, per entry type. v2, not
# v1: v1's first entry starts with a space (" M path") that _git's strip() would eat.
_V2_PATH_FIELD = {"1": 8, "2": 9, "u": 10, "?": 1}


def parse_porcelain_v2_z(text):
    """Paths from `git status --porcelain=v2 -z`. A rename/copy ("2") entry is followed
    by a second NUL field (its source path); both are returned."""
    fields, paths, i = (text or "").split("\0"), [], 0
    while i < len(fields):
        f = fields[i]
        i += 1
        n = _V2_PATH_FIELD.get(f[:1])
        if n is None:
            continue
        parts = f.split(" ", n)
        if len(parts) > n:
            paths.append(parts[n])
        if f[:1] == "2":
            if i < len(fields) and fields[i]:
                paths.append(fields[i])
            i += 1
    return paths


def overlapping_paths(dirty, changed):
    """Dirty paths that equal a changed path or sit on either side of a directory
    boundary with one (origin turns dir->file, or adds under an untracked dir).
    Case-insensitive: a false block is safe, a missed one rewrites the tree."""
    ch = [c.casefold() for c in changed]
    hits = []
    for d in dirty:
        dc = d.casefold()
        if any(dc == c or dc.startswith(c + "/") or c.startswith(dc + "/") for c in ch):
            if d not in hits:
                hits.append(d)
    return hits


def incoming_paths(repo, target_sha):
    """Paths the merge of target_sha into HEAD would change, computed without touching
    the index or working tree, or None if it cannot be computed. `merge-tree
    --write-tree` (git >= 2.38) gives the real result tree -- exit 1 only means
    conflicts, and the tree is still written. Fallback: merge-base..target, a
    superset (it also lists changes HEAD already has)."""
    rc, out, _ = _git(["merge-tree", "--write-tree", "--name-only", "-z", "HEAD", target_sha], repo)
    fields = out.split("\0") if rc in (0, 1) and out else [""]
    tree, conflicted = fields[0].strip(), []
    # Conflicted paths follow the tree id up to an empty field. They MUST be added: for
    # modify/delete or binary conflicts the result tree keeps HEAD's version, so the diff
    # below omits them -- and the merge's `--abort` then reverts a dirty edit there.
    for f in fields[1:]:
        if not f:
            break
        conflicted.append(f)
    if tree:
        rc, names, _ = _git(["diff", "--name-only", "--no-renames", "-z", "HEAD", tree], repo)
    else:
        rc, names, _ = _git(["diff", "--name-only", "--no-renames", "-z",
                             "HEAD...%s" % target_sha], repo)
    if rc != 0:
        return None
    return [n for n in names.split("\0") if n] + conflicted


def hidden_dirty_paths(repo):
    """Index entries `git status` cannot see as dirty but `git merge` still refuses over:
    assume-unchanged (lowercase `ls-files -v` tag) always, skip-worktree (`S`) only when
    the file is present on disk (absent = ordinary sparse checkout). None on failure."""
    rc, out, _ = _git(["ls-files", "-v", "-z"], repo)
    if rc != 0:
        return None
    hits = []
    for f in out.split("\0"):
        if len(f) < 3 or f[1] != " ":
            continue
        tag, path = f[0], f[2:]
        if tag.islower() or (tag == "S" and os.path.lexists(os.path.join(repo, path))):
            hits.append(path)
    return hits


def _strip_warnings(text):
    return "\n".join(l for l in (text or "").splitlines()
                     if not l.startswith("warning:"))


def _git(args, repo):
    """(rc, stdout, stderr) -- never raises on a non-zero/missing git. Output is
    pinned to English (LC_ALL=C): the overlap headers and MERGE_REFUSAL_MARKERS
    are matched as text, and a translated refusal would read as this run's merge."""
    try:
        p = subprocess.run(
            ["git"] + args, cwd=repo, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=60,
            env=dict(os.environ, LC_ALL="C", LANGUAGE="C"),
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        return 127, "", str(e)
    return p.returncode, (p.stdout or "").strip(), (p.stderr or "").strip()


def ref_state(repo, ref):
    """(state, sha) with state "present" / "absent" / "unknown". `rev-parse -q --verify`
    exits 1 ONLY for a missing ref; 127 (timeout/OSError) or 128 (fatal) prove nothing,
    and reading them as "absent" would report a mid-merge checkout as restored."""
    rc, sha, _ = _git(["rev-parse", "-q", "--verify", ref], repo)
    if rc == 0 and sha:
        return "present", sha
    if rc == 1:
        return "absent", None
    return "unknown", None


def in_progress_ops(repo):
    """Names of git operations already in progress in `repo` (step 0a). Fails closed:
    a marker that cannot be checked is reported as in progress ("... (unverifiable)")."""
    ops = []
    for ref, name in IN_PROGRESS_REFS:
        state, _ = ref_state(repo, ref)
        if state == "present":
            ops.append(name)
        elif state == "unknown":
            ops.append("%s (unverifiable)" % name)
    for sub, name in IN_PROGRESS_PATHS:
        rc, path, _ = _git(["rev-parse", "--git-path", sub], repo)
        if rc != 0 or not path:
            ops.append("%s (unverifiable)" % name)
            continue
        full = path if os.path.isabs(path) else os.path.join(repo, path)
        if os.path.exists(full):
            ops.append(name)
    return ops


def abort_merge(repo):
    """`git merge --abort`, retried, then VERIFIED. True only if MERGE_HEAD is
    provably gone afterwards -- never infer success from the abort's exit code,
    and never from a rev-parse that failed for some other reason."""
    for attempt in range(ABORT_ATTEMPTS):
        _git(["merge", "--abort"], repo)
        if ref_state(repo, "MERGE_HEAD")[0] == "absent":
            return True
        if attempt + 1 < ABORT_ATTEMPTS and ABORT_RETRY_SECONDS:
            time.sleep(ABORT_RETRY_SECONDS)
    return False


def _mid_merge_note(repo):
    return ("ABORT FAILED -- checkout LEFT MID-MERGE (MERGE_HEAD present); every "
            "session's pathspec commit will fail until someone runs `git merge --abort` "
            "in %s" % repo)


def blocking_claims(repo):
    """Live work claims (other than this task's own) that overlap `repo` or cannot be proven
    disjoint from it (step 0b). Raises if claim_work cannot be loaded -- the
    caller turns that into ERROR, because a safety gate that cannot run is not
    a pass. Uses claim_work.paths_conflict(), which checks BOTH directions and
    returns None (treated as blocking) for a claim that declares no paths."""
    spec = importlib.util.spec_from_file_location("claim_work_cmf", CLAIM_WORK_PATH)
    if spec is None or spec.loader is None:
        raise ImportError("cannot locate claim_work at %s" % CLAIM_WORK_PATH)
    cw = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cw)
    claims_dir = CLAIMS_DIR_OVERRIDE or cw.CLAIMS_DIR
    hits = []
    for c in cw.read_active_claims(base_dir=claims_dir):
        slug = str(c.get("slug") or "")
        if slug == OWN_CLAIM_SLUG:
            continue  # this task's own STEP 0 claim, or a prior run's
        verdict = cw.paths_conflict([os.path.abspath(repo)], c.get("paths") or [])
        if verdict is False:
            continue
        hits.append({"slug": slug, "session_id": c.get("session_id"),
                     "reason": "overlaps repo" if verdict else "declares no paths"})
    return hits


def _op_in_progress(out, ops):
    out["status"] = "BLOCKED_OP_IN_PROGRESS"
    out["in_progress_ops"] = ops
    out["detail"] = ("a %s is already in progress -- left untouched (it may be another "
                     "session's, or a stranded run of this corrector); resolve or abort "
                     "it by hand" % " + ".join(ops))
    return out


def sync(repo=None, canonical=None):
    repo = repo or DEFAULT_REPO
    canonical = canonical or DEFAULT_CANONICAL
    out = {"repo": repo, "canonical": canonical, "status": None, "detail": None,
           "commits_merged": None, "sha": None, "blocked_paths": None,
           "merge_aborted": None, "in_progress_ops": None, "blocking_claims": None}

    rc, _, err = _git(["rev-parse", "--git-dir"], repo)
    if rc != 0:
        out["status"] = "ERROR"
        out["detail"] = "not a git repo: %s" % err
        return out

    ops = in_progress_ops(repo)
    if ops:
        return _op_in_progress(out, ops)

    try:
        claims = blocking_claims(repo)
    except Exception as e:  # noqa: BLE001 -- any load/read failure fails closed
        out["status"] = "ERROR"
        out["detail"] = "work-claim gate could not run (%s: %s) -- not merging" % (
            type(e).__name__, e)
        return out
    if claims:
        out["status"] = "BLOCKED_CLAIMED"
        out["blocking_claims"] = claims
        out["detail"] = "live work claim(s) cover this repo: %s" % ", ".join(
            "%s (%s)" % (c["slug"], c["reason"]) for c in claims[:10])
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

    # Step 0a again, immediately before merging: another session may have started an
    # operation during the fetch. This run may only ever abort a merge it CREATED.
    ops = in_progress_ops(repo)
    if ops:
        return _op_in_progress(out, ops)
    rc, target_sha, _ = _git(["rev-parse", "--verify", target], repo)
    if rc != 0 or not target_sha:
        out["status"] = "ERROR"
        out["detail"] = "cannot resolve %s" % target
        return out

    # Overlap BEFORE merging, read-only. A refused `git merge` on a non-ff branch
    # rewrites every dirty tracked file (new mtime, LF->CRLF under autocrlf) even
    # though it keeps their content -- so when overlap is knowable, never invoke it.
    rc, status_out, _ = _git(["status", "--porcelain=v2", "-z", "--untracked-files=all"], repo)
    hidden = hidden_dirty_paths(repo) if rc == 0 else None
    incoming = incoming_paths(repo, target_sha) if hidden is not None else None
    if incoming is None:
        out["status"] = "ERROR"
        out["detail"] = ("cannot compute the dirty/incoming overlap read-only (%s failed) "
                         "-- not merging" % ("git status" if rc != 0 else
                                             "ls-files" if hidden is None else "merge-tree/diff"))
        return out
    overlap = overlapping_paths(parse_porcelain_v2_z(status_out) + hidden, incoming)
    if overlap:
        out["status"] = "BLOCKED_DIRTY_OVERLAP"
        out["blocked_paths"] = overlap
        out["detail"] = ("%d local path(s) overlap %s; git merge not attempted, tree "
                         "untouched: %s" % (len(overlap), target, ", ".join(overlap[:20])))[:500]
        return out

    # Merge the resolved SHA, not the ref name: a concurrent fetch moving origin/<canonical>
    # in between would otherwise make this run's own MERGE_HEAD fail the check below,
    # stranding its own conflict as "someone else's".
    rc, merge_out, merge_err = _git(
        ["merge", "--no-commit", "--no-ff", "-m",
         "Merge remote-tracking branch '%s'" % target, target_sha], repo)
    if rc == 0:
        rc2, _, commit_err = _git(["commit", "--no-edit"], repo)
        if rc2 != 0:
            # Never return with the merge still staged: a mid-merge shared
            # checkout blocks every other session's pathspec commits.
            aborted = abort_merge(repo)
            out["status"] = "ERROR"
            out["merge_aborted"] = aborted
            out["detail"] = "merge staged cleanly but commit failed (%s): %s" % (
                "merge aborted, tree restored" if aborted else _mid_merge_note(repo),
                commit_err[:400])
            return out
        rc3, sha, _ = _git(["rev-parse", "HEAD"], repo)
        out["status"] = "MERGED"
        out["commits_merged"] = behind
        out["sha"] = sha if rc3 == 0 else None
        out["detail"] = "merged %d commit(s) from %s" % (behind, target)
        return out

    raw = "\n".join(s for s in (merge_err, merge_out) if s)
    head_state, merge_head = ref_state(repo, "MERGE_HEAD")
    # Only git's own fatal:/error: lines -- a conflicted file's PATH can contain a marker.
    diag = [l.lower() for l in raw.splitlines() if l.startswith(("fatal:", "error:"))]
    refused = any(m in l for l in diag for m in MERGE_REFUSAL_MARKERS)
    if head_state != "absent" and (refused or head_state == "unknown" or merge_head != target_sha):
        # Not provably this run's merge: git refused because one already existed, or
        # MERGE_HEAD names something other than what we merged. Never abort it.
        return _op_in_progress(out, in_progress_ops(repo) or ["merge"])
    if head_state == "present":
        aborted = abort_merge(repo)
        out["status"] = "BLOCKED_CONFLICT"
        out["merge_aborted"] = aborted
        out["detail"] = "textual conflict merging %s -- %s: %s" % (
            target, "aborted, tree restored" if aborted else _mid_merge_note(repo),
            (merge_out or merge_err)[:500])
        return out

    paths = parse_overlap_paths(raw)
    if not paths:
        # git refused, but not over overlapping WIP (e.g. a stale index.lock that blocks
        # every session's commits). Routine-silent BLOCKED_DIRTY_OVERLAP would hide it.
        out["status"] = "ERROR"
        out["detail"] = "git refused the merge with no overlapping paths named: %s" % (
            _strip_warnings(raw)[:500])
        return out
    out["status"] = "BLOCKED_DIRTY_OVERLAP"
    out["blocked_paths"] = paths
    out["detail"] = "git refused the merge (%d local path(s) overlap %s): %s" % (
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
