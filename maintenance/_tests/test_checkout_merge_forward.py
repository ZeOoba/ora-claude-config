#!/usr/bin/env python3
"""Tests for checkout-merge-forward.py -- the paired corrector to
cross-repo-wip-scan.py's branch-drift detection (open-items-tracker.md#OI-249,
candidate (a), 2026-09-09). Real throwaway git repos with a real local
"origin" remote (file-path clone) -- no mocked git, same convention as
test_check_branch_point.py and test_cross_repo_wip_scan.py.

Run: python _tests/test_checkout_merge_forward.py   (exit 0 = pass)
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

# ISOLATION (2026-09-12): sync() now consults live work claims before merging, and
# claim_work.CLAIMS_DIR is the LIVE ~/.claude/hooks/active-work. Every test gets an
# empty claims dir by default so a real session's claim can never block (or pass)
# a test; the claim tests below point it at their own fixture dir explicitly.
_EMPTY_CLAIMS = tempfile.mkdtemp(prefix="cmf-empty-claims-")
cmf.CLAIMS_DIR_OVERRIDE = _EMPTY_CLAIMS
cmf.ABORT_RETRY_SECONDS = 0  # never sleep between abort attempts under test

_CW_PATH = os.path.join(os.path.dirname(os.path.dirname(HERE)), "hooks", "lib", "claim_work.py")
_cw_spec = importlib.util.spec_from_file_location("claim_work_fixture", _CW_PATH)
claim_work = importlib.util.module_from_spec(_cw_spec)
_cw_spec.loader.exec_module(claim_work)

_results = []


def check(name, cond, detail=""):
    _results.append((bool(cond), name))
    if not cond:
        print("FAIL %s  %s" % (name, detail))
    else:
        print("PASS %s" % name)


def run(repo, *args, check_rc=True):
    p = subprocess.run(["git"] + list(args), cwd=repo, capture_output=True, text=True)
    if check_rc and p.returncode != 0:
        raise RuntimeError("git %s failed: %s" % (" ".join(args), p.stderr))
    return p


def write(repo, fname, text):
    with open(os.path.join(repo, fname), "w", encoding="utf-8") as fh:
        fh.write(text)


def commit(repo, msg, fname=None):
    fname = fname or (msg.replace(" ", "_") + ".txt")
    write(repo, fname, msg)
    run(repo, "add", fname)
    run(repo, "commit", "-q", "-m", msg, "--no-verify")


def make_pair(td, canonical="main"):
    """(local, origin) -- local is a real clone of origin, both on `canonical`
    with one shared commit, local's `origin/<canonical>` genuinely resolves."""
    origin = os.path.join(td, "origin")
    os.makedirs(origin)
    run(origin, "init", "-q", "-b", canonical)
    run(origin, "config", "user.email", "t@example.com")
    run(origin, "config", "user.name", "T")
    commit(origin, "base commit")

    local = os.path.join(td, "local")
    run(td, "clone", "-q", origin, local)
    run(local, "config", "user.email", "t@example.com")
    run(local, "config", "user.name", "T")
    return local, origin


# --- already up to date -> NOOP_CLEAN, no commit made -------------------------------
with tempfile.TemporaryDirectory() as td:
    local, origin = make_pair(td)
    before = run(local, "rev-parse", "HEAD").stdout.strip()
    r = cmf.sync(local, "main")
    check("noop: status NOOP_CLEAN", r["status"] == "NOOP_CLEAN", repr(r))
    check("noop: commits_merged 0", r["commits_merged"] == 0, repr(r))
    after = run(local, "rev-parse", "HEAD").stdout.strip()
    check("noop: HEAD unchanged", before == after, "before=%s after=%s" % (before, after))

# --- clean fast-forwardable drift -> MERGED, exactly N commits landed ---------------
with tempfile.TemporaryDirectory() as td:
    local, origin = make_pair(td)
    for i in range(3):
        commit(origin, "origin commit %d" % i, fname="o%d.txt" % i)
    r = cmf.sync(local, "main")
    check("merge: status MERGED", r["status"] == "MERGED", repr(r))
    check("merge: commits_merged == 3", r["commits_merged"] == 3, repr(r))
    check("merge: sha reported", bool(r["sha"]), repr(r))
    head = run(local, "rev-parse", "HEAD").stdout.strip()
    check("merge: HEAD actually moved to the reported sha", head == r["sha"], repr(r))
    check("merge: origin's new files are present",
          os.path.isfile(os.path.join(local, "o0.txt"))
          and os.path.isfile(os.path.join(local, "o2.txt")))
    check("merge: index is clean after (nothing left staged)",
          run(local, "diff", "--cached", "--name-only").stdout.strip() == "")
    check("merge: no unrelated file touched",
          not os.path.isfile(os.path.join(local, "should-not-exist.txt")))

    # A second run is a clean no-op -- proves the merge actually committed.
    r2 = cmf.sync(local, "main")
    check("merge: second run is NOOP_CLEAN", r2["status"] == "NOOP_CLEAN", repr(r2))

# --- dirty overlap: local uncommitted change to a path origin also touches ---------
with tempfile.TemporaryDirectory() as td:
    local, origin = make_pair(td)
    commit(origin, "origin changes shared.txt", fname="shared.txt")
    # Local has an UNCOMMITTED edit to the same path origin's new commit touches.
    write(local, "shared.txt", "local uncommitted edit, conflicts with the fetch\n")
    r = cmf.sync(local, "main")
    check("dirty-overlap: status BLOCKED_DIRTY_OVERLAP",
          r["status"] == "BLOCKED_DIRTY_OVERLAP", repr(r))
    check("dirty-overlap: local uncommitted edit preserved verbatim",
          open(os.path.join(local, "shared.txt")).read()
          == "local uncommitted edit, conflicts with the fetch\n")
    check("dirty-overlap: no MERGE_HEAD left behind",
          run(local, "rev-parse", "-q", "--verify", "MERGE_HEAD", check_rc=False).returncode != 0)
    check("dirty-overlap: local HEAD did not move past what it cloned",
          run(local, "rev-parse", "HEAD").stdout.strip()
          != run(origin, "rev-parse", "HEAD").stdout.strip())

# --- real textual conflict: both sides edit the SAME line, committed on both sides -
with tempfile.TemporaryDirectory() as td:
    local, origin = make_pair(td)
    write(origin, "conflict.txt", "origin version\n")
    run(origin, "add", "conflict.txt")
    run(origin, "commit", "-q", "-m", "origin edits conflict.txt")
    write(local, "conflict.txt", "local version\n")
    run(local, "add", "conflict.txt")
    run(local, "commit", "-q", "-m", "local edits conflict.txt", "--no-verify")
    head_before = run(local, "rev-parse", "HEAD").stdout.strip()

    r = cmf.sync(local, "main")
    check("conflict: status BLOCKED_CONFLICT", r["status"] == "BLOCKED_CONFLICT", repr(r))
    check("conflict: MERGE_HEAD cleaned up (abort ran)",
          run(local, "rev-parse", "-q", "--verify", "MERGE_HEAD", check_rc=False).returncode != 0)
    check("conflict: HEAD unchanged after abort",
          run(local, "rev-parse", "HEAD").stdout.strip() == head_before)
    check("conflict: working tree has no conflict markers left",
          "<<<<<<<" not in open(os.path.join(local, "conflict.txt")).read())
    check("conflict: index clean after abort",
          run(local, "diff", "--cached", "--name-only").stdout.strip() == "")

# --- another session's content already staged -> refuse before touching anything ---
with tempfile.TemporaryDirectory() as td:
    local, origin = make_pair(td)
    for i in range(2):
        commit(origin, "origin commit %d" % i, fname="p%d.txt" % i)
    write(local, "someone-elses-work.txt", "staged by another session\n")
    run(local, "add", "someone-elses-work.txt")
    head_before = run(local, "rev-parse", "HEAD").stdout.strip()

    r = cmf.sync(local, "main")
    check("staged-guard: status BLOCKED_STAGED", r["status"] == "BLOCKED_STAGED", repr(r))
    check("staged-guard: names the staged path", "someone-elses-work.txt" in r["detail"], repr(r))
    check("staged-guard: HEAD unchanged (never even fetched/merged)",
          run(local, "rev-parse", "HEAD").stdout.strip() == head_before)
    check("staged-guard: the stranger's staged content is still staged, untouched",
          "someone-elses-work.txt" in run(local, "diff", "--cached", "--name-only").stdout)

# --- not a git repo at all -----------------------------------------------------------
with tempfile.TemporaryDirectory() as td:
    not_repo = os.path.join(td, "not-a-repo")
    os.makedirs(not_repo)
    r = cmf.sync(not_repo, "main")
    check("not-a-repo: status ERROR", r["status"] == "ERROR", repr(r))

# --- main() exit codes ---------------------------------------------------------------
with tempfile.TemporaryDirectory() as td:
    local, origin = make_pair(td)
    rc = cmf.main(["--repo", local, "--canonical", "main"])
    check("main: exit 0 on NOOP_CLEAN", rc == 0, "got %r" % rc)

with tempfile.TemporaryDirectory() as td:
    local, origin = make_pair(td)
    commit(origin, "one more", fname="q.txt")
    rc = cmf.main(["--repo", local, "--canonical", "main"])
    check("main: exit 0 on MERGED", rc == 0, "got %r" % rc)

with tempfile.TemporaryDirectory() as td:
    local, origin = make_pair(td)
    write(local, "x.txt", "uncommitted\n")
    run(local, "add", "x.txt")
    rc = cmf.main(["--repo", local, "--canonical", "main"])
    check("main: exit 1 on BLOCKED_STAGED", rc == 1, "got %r" % rc)

# --- dirty overlap names EVERY overlapping path, git's CRLF warnings stripped ------
# (2026-09-12: the live run's detail was truncated at 500 chars of LF->CRLF
# warnings before git ever named a single overlapping file.)
with tempfile.TemporaryDirectory() as td:
    local, origin = make_pair(td)
    for i in range(3):
        write(origin, "ov%d.txt" % i, "origin %d\n" % i)
        run(origin, "add", "ov%d.txt" % i)
    run(origin, "commit", "-q", "-m", "origin adds ov0..ov2")
    for i in range(3):
        write(local, "ov%d.txt" % i, "local untracked %d\n" % i)  # untracked overlap
    r = cmf.sync(local, "main")
    check("blocked-paths: status BLOCKED_DIRTY_OVERLAP",
          r["status"] == "BLOCKED_DIRTY_OVERLAP", repr(r))
    check("blocked-paths: all three overlapping paths listed",
          sorted(r.get("blocked_paths") or []) == ["ov0.txt", "ov1.txt", "ov2.txt"], repr(r))
    check("blocked-paths: detail carries no 'warning:' noise",
          "warning:" not in (r["detail"] or ""), repr(r))

with tempfile.TemporaryDirectory() as td:
    local, origin = make_pair(td)
    commit(origin, "origin changes shared.txt", fname="shared.txt")
    write(local, "shared.txt", "local committed\n")
    run(local, "add", "shared.txt")
    run(local, "commit", "-q", "-m", "local base for shared", "--no-verify")
    write(local, "shared.txt", "local uncommitted on top\n")  # tracked, modified overlap
    r = cmf.sync(local, "main")
    check("blocked-paths: tracked modified overlap surfaced",
          r["status"] == "BLOCKED_DIRTY_OVERLAP" and r.get("blocked_paths") == ["shared.txt"],
          repr(r))

check("parse: tracked + untracked headers, CRLF warnings ignored",
      cmf.parse_overlap_paths(
          "warning: in the working copy of 'a.md', LF will be replaced by CRLF\n"
          "error: Your local changes to the following files would be overwritten by merge:\n"
          "\tx/one.py\n\tx/two.py\n"
          "Please commit your changes or stash them before you merge.\n"
          "error: The following untracked working tree files would be overwritten by merge:\n"
          "\tnew.txt\n"
          "Please move or remove them before you merge.\nAborting")
      == ["x/one.py", "x/two.py", "new.txt"])
check("parse: nothing recognisable -> empty list", cmf.parse_overlap_paths("fatal: boom") == [])

# --- state file: consecutive-unsynced counter ---------------------------------------
import json as _json
with tempfile.TemporaryDirectory() as td:
    sp = os.path.join(td, "sub", "state.json")
    blocked = {"status": "BLOCKED_DIRTY_OVERLAP", "commits_merged": None, "sha": None,
               "blocked_paths": ["a.txt"]}
    s1 = cmf.update_state(blocked, sp, now_iso="2026-09-10T16:45:00-04:00")
    check("state: first blocked run -> consecutiveUnsynced 1", s1["consecutiveUnsynced"] == 1, repr(s1))
    check("state: unsyncedSince set to first blocked run",
          s1["unsyncedSince"] == "2026-09-10T16:45:00-04:00", repr(s1))
    s2 = cmf.update_state(dict(blocked, status="BLOCKED_STAGED"), sp,
                          now_iso="2026-09-11T16:45:00-04:00")
    check("state: second non-landing run increments", s2["consecutiveUnsynced"] == 2, repr(s2))
    check("state: unsyncedSince preserved across the streak",
          s2["unsyncedSince"] == "2026-09-10T16:45:00-04:00", repr(s2))
    on_disk = _json.load(open(sp, encoding="utf-8"))
    check("state: written to disk with legacy keys intact",
          on_disk["status"] == "BLOCKED_STAGED" and "lastRun" in on_disk
          and "commitsMerged" in on_disk and on_disk["blockedPaths"] == ["a.txt"], repr(on_disk))
    s3 = cmf.update_state({"status": "MERGED", "commits_merged": 4, "sha": "abc"}, sp,
                          now_iso="2026-09-12T16:45:00-04:00")
    check("state: MERGED resets the streak",
          s3["consecutiveUnsynced"] == 0 and s3["unsyncedSince"] is None
          and s3["commitsMerged"] == 4 and s3["sha"] == "abc", repr(s3))

with tempfile.TemporaryDirectory() as td:
    sp = os.path.join(td, "state.json")
    write(td, "state.json", '{"lastRun": "x", "status": "BLOCKED_DIRTY_OVERLAP"}')  # legacy shape
    s = cmf.update_state({"status": "ERROR", "commits_merged": None, "sha": None}, sp,
                         now_iso="2026-09-12T16:45:00-04:00")
    check("state: legacy file without counter counts itself as run 1 of streak",
          s["consecutiveUnsynced"] == 1, repr(s))
    write(td, "state.json", "not json{")
    s = cmf.update_state({"status": "BLOCKED_DIRTY_OVERLAP", "commits_merged": None, "sha": None},
                         sp, now_iso="2026-09-12T16:45:00-04:00")
    check("state: corrupt prior file does not crash, restarts at 1",
          s["consecutiveUnsynced"] == 1, repr(s))

with tempfile.TemporaryDirectory() as td:
    local, origin = make_pair(td)
    sp = os.path.join(td, "st.json")
    write(local, "x.txt", "uncommitted\n")
    run(local, "add", "x.txt")
    rc = cmf.main(["--repo", local, "--canonical", "main", "--json", "--state-file", sp])
    check("main: --state-file written and exit code unchanged",
          rc == 1 and _json.load(open(sp))["consecutiveUnsynced"] == 1, "rc=%r" % rc)

# --- streak_alarm: daily self-alarm at 14 unsynced runs, then every 7 ---------------
A, R = cmf.STREAK_ALARM_RUNS, cmf.STREAK_ALARM_REPEAT_RUNS
check("streak_alarm: constants are 14 / 7", (A, R) == (14, 7), repr((A, R)))
check("streak_alarm: below threshold silent", cmf.streak_alarm(A - 1) is False)
check("streak_alarm: fires at threshold", cmf.streak_alarm(A) is True)
check("streak_alarm: silent between repeats", cmf.streak_alarm(A + 1) is False
      and cmf.streak_alarm(A + R - 1) is False)
check("streak_alarm: repeats every R runs", cmf.streak_alarm(A + R) is True
      and cmf.streak_alarm(A + 2 * R) is True)
check("streak_alarm: None/0 silent", cmf.streak_alarm(None) is False and cmf.streak_alarm(0) is False)

with tempfile.TemporaryDirectory() as td:
    local, origin = make_pair(td)
    sp = os.path.join(td, "st.json")
    write(td, "st.json", _json.dumps({"consecutiveUnsynced": A - 1, "unsyncedSince": "2026-08-30"}))
    write(local, "x.txt", "uncommitted\n")
    run(local, "add", "x.txt")
    import io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = cmf.main(["--repo", local, "--canonical", "main", "--json", "--state-file", sp])
    out = _json.loads(buf.getvalue())
    check("main: streak_alarm true in JSON on the 14th unsynced run",
          out.get("streak_alarm") is True and out.get("consecutive_unsynced") == A, repr(out))
    check("main: unsynced_since surfaced for the alarm body",
          out.get("unsynced_since") == "2026-08-30", repr(out))
    check("main: exit code unchanged by the alarm flag", rc == 1, "rc=%r" % rc)

with tempfile.TemporaryDirectory() as td:
    local, origin = make_pair(td)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        cmf.main(["--repo", local, "--canonical", "main", "--json"])
    out = _json.loads(buf.getvalue())
    check("main: no --state-file -> streak_alarm false (unmeasured, never fires)",
          out.get("streak_alarm") is False, repr(out))

# --- update_state leaves no orphan .tmp when the replace fails ----------------------
with tempfile.TemporaryDirectory() as td:
    sp = os.path.join(td, "state.json")
    real_replace = cmf.os.replace
    def boom(src, dst):
        raise PermissionError("locked by AV")
    cmf.os.replace = boom
    try:
        raised = False
        try:
            cmf.update_state({"status": "BLOCKED_STAGED", "commits_merged": None, "sha": None},
                             sp, now_iso="2026-09-12T16:45:00-04:00")
        except OSError:
            raised = True
    finally:
        cmf.os.replace = real_replace
    check("state: replace failure still raises OSError (caller records state_error)", raised)
    check("state: replace failure leaves no .tmp behind", not os.path.exists(sp + ".tmp"),
          repr(os.listdir(td)))

# =====================================================================================
# PR #193 code-review findings (2026-09-12). Each scenario below failed, or could not
# be expressed, against the pre-fix script.
# =====================================================================================


def _with_lock_on(predicate):
    """A _git wrapper that holds .git/index.lock while `predicate(args)` commands run --
    the shape of a concurrent session's git command owning the lock at that instant."""
    real = cmf._git

    def wrapped(args, repo):
        if predicate(args):
            lock = os.path.join(repo, ".git", "index.lock")
            open(lock, "w").close()
            try:
                return real(args, repo)
            finally:
                os.remove(lock)
        return real(args, repo)
    return real, wrapped


def _has(repo, ref):
    return run(repo, "rev-parse", "-q", "--verify", ref, check_rc=False).returncode == 0


# --- F1: commit fails after a clean merge -> merge ABORTED, tree restored -------------
with tempfile.TemporaryDirectory() as td:
    local, origin = make_pair(td)
    commit(origin, "origin moves ahead", fname="o.txt")
    before = run(local, "rev-parse", "HEAD").stdout.strip()
    real, wrapped = _with_lock_on(lambda a: a[:1] == ["commit"])
    cmf._git = wrapped
    try:
        r = cmf.sync(local, "main")
    finally:
        cmf._git = real
    check("F1 commit-fail: status ERROR", r["status"] == "ERROR", repr(r))
    check("F1 commit-fail: merge_aborted True", r.get("merge_aborted") is True, repr(r))
    check("F1 commit-fail: no MERGE_HEAD left behind", not _has(local, "MERGE_HEAD"))
    check("F1 commit-fail: index clean", run(local, "diff", "--cached", "--name-only").stdout.strip() == "")
    check("F1 commit-fail: HEAD unchanged", run(local, "rev-parse", "HEAD").stdout.strip() == before)
    check("F1 commit-fail: incoming file not left in the tree",
          not os.path.isfile(os.path.join(local, "o.txt")))
    # The failure mode this closes: another session's pathspec commit must still work.
    write(local, "mine.txt", "a session's own edit\n")
    run(local, "add", "mine.txt")
    p = run(local, "commit", "-q", "-m", "other session", "--no-verify", "--", "mine.txt", check_rc=False)
    check("F1 commit-fail: an innocent pathspec commit still succeeds afterwards",
          p.returncode == 0, p.stderr)

# --- F1: commit fails AND the abort keeps failing -> say so loudly, never "restored" --
with tempfile.TemporaryDirectory() as td:
    local, origin = make_pair(td)
    commit(origin, "origin moves ahead", fname="o.txt")
    real, wrapped = _with_lock_on(lambda a: a[:1] == ["commit"] or a[:2] == ["merge", "--abort"])
    cmf._git = wrapped
    try:
        r = cmf.sync(local, "main")
    finally:
        cmf._git = real
    check("F1 abort-fail: status ERROR", r["status"] == "ERROR", repr(r))
    check("F1 abort-fail: merge_aborted False", r.get("merge_aborted") is False, repr(r))
    check("F1 abort-fail: detail says LEFT MID-MERGE", "LEFT MID-MERGE" in (r["detail"] or ""), repr(r))
    check("F1 abort-fail: report is truthful (MERGE_HEAD really present)", _has(local, "MERGE_HEAD"))
    run(local, "merge", "--abort", check_rc=False)

# --- F1: real conflict whose abort fails -> BLOCKED_CONFLICT, not "tree restored" -----
with tempfile.TemporaryDirectory() as td:
    local, origin = make_pair(td)
    write(origin, "shared.txt", "origin line\n"); run(origin, "add", "shared.txt")
    run(origin, "commit", "-q", "-m", "origin edit", "--no-verify")
    write(local, "shared.txt", "local line\n"); run(local, "add", "shared.txt")
    run(local, "commit", "-q", "-m", "local edit", "--no-verify")
    real, wrapped = _with_lock_on(lambda a: a[:2] == ["merge", "--abort"])
    cmf._git = wrapped
    try:
        r = cmf.sync(local, "main")
    finally:
        cmf._git = real
    check("F1 conflict-abort-fail: status BLOCKED_CONFLICT", r["status"] == "BLOCKED_CONFLICT", repr(r))
    check("F1 conflict-abort-fail: merge_aborted False", r.get("merge_aborted") is False, repr(r))
    check("F1 conflict-abort-fail: detail does not claim restoration",
          "tree restored" not in (r["detail"] or "") and "LEFT MID-MERGE" in (r["detail"] or ""), repr(r))
    run(local, "merge", "--abort", check_rc=False)

# --- F1: real conflict, abort succeeds -> merge_aborted True ----------------------------
with tempfile.TemporaryDirectory() as td:
    local, origin = make_pair(td)
    write(origin, "shared.txt", "origin line\n"); run(origin, "add", "shared.txt")
    run(origin, "commit", "-q", "-m", "origin edit", "--no-verify")
    write(local, "shared.txt", "local line\n"); run(local, "add", "shared.txt")
    run(local, "commit", "-q", "-m", "local edit", "--no-verify")
    r = cmf.sync(local, "main")
    check("F1 conflict: merge_aborted True", r.get("merge_aborted") is True, repr(r))
    check("F1 conflict: no MERGE_HEAD", not _has(local, "MERGE_HEAD"))

# --- F2: another session's in-progress MERGE -> refuse, and NEVER abort it -----------
with tempfile.TemporaryDirectory() as td:
    local, origin = make_pair(td)
    write(origin, "shared.txt", "origin line\n"); run(origin, "add", "shared.txt")
    run(origin, "commit", "-q", "-m", "origin edit", "--no-verify")
    write(local, "shared.txt", "local line\n"); run(local, "add", "shared.txt")
    run(local, "commit", "-q", "-m", "local edit", "--no-verify")
    run(local, "fetch", "-q", "origin")
    run(local, "merge", "origin/main", check_rc=False)  # conflicted, as a human left it
    mh_before = run(local, "rev-parse", "MERGE_HEAD").stdout.strip()
    conflicted = open(os.path.join(local, "shared.txt"), encoding="utf-8").read()
    commit(origin, "origin moves further", fname="later.txt")  # corrector would act
    r = cmf.sync(local, "main")
    check("F2 merge: status BLOCKED_OP_IN_PROGRESS", r["status"] == "BLOCKED_OP_IN_PROGRESS", repr(r))
    check("F2 merge: names the merge", "merge" in (r.get("in_progress_ops") or []), repr(r))
    check("F2 merge: NOT misreported as BLOCKED_STAGED", r["status"] != "BLOCKED_STAGED", repr(r))
    check("F2 merge: the other session's MERGE_HEAD is untouched",
          _has(local, "MERGE_HEAD") and run(local, "rev-parse", "MERGE_HEAD").stdout.strip() == mh_before)
    check("F2 merge: their conflicted file is untouched",
          open(os.path.join(local, "shared.txt"), encoding="utf-8").read() == conflicted)

# --- F2: the corrector's OWN stranded merge (F1 abort-fail) is caught next run too ----
with tempfile.TemporaryDirectory() as td:
    local, origin = make_pair(td)
    commit(origin, "origin moves ahead", fname="o.txt")
    real, wrapped = _with_lock_on(lambda a: a[:1] == ["commit"] or a[:2] == ["merge", "--abort"])
    cmf._git = wrapped
    try:
        cmf.sync(local, "main")
    finally:
        cmf._git = real
    r = cmf.sync(local, "main")
    check("F2 stranded: next run is BLOCKED_OP_IN_PROGRESS, not a silent BLOCKED_STAGED",
          r["status"] == "BLOCKED_OP_IN_PROGRESS", repr(r))
    run(local, "merge", "--abort", check_rc=False)

# --- F2: in-progress CHERRY-PICK and REBASE are refused too ---------------------------
with tempfile.TemporaryDirectory() as td:
    local, origin = make_pair(td)
    write(local, "c.txt", "base\n"); run(local, "add", "c.txt")
    run(local, "commit", "-q", "-m", "c base", "--no-verify")
    run(local, "checkout", "-q", "-b", "side")
    write(local, "c.txt", "side\n"); run(local, "commit", "-q", "-am", "side edit", "--no-verify")
    side = run(local, "rev-parse", "HEAD").stdout.strip()
    run(local, "checkout", "-q", "main")
    write(local, "c.txt", "main\n"); run(local, "commit", "-q", "-am", "main edit", "--no-verify")
    run(local, "cherry-pick", side, check_rc=False)
    commit(origin, "origin moves", fname="o2.txt")
    r = cmf.sync(local, "main")
    check("F2 cherry-pick: status BLOCKED_OP_IN_PROGRESS", r["status"] == "BLOCKED_OP_IN_PROGRESS", repr(r))
    check("F2 cherry-pick: names it", "cherry-pick" in (r.get("in_progress_ops") or []), repr(r))
    check("F2 cherry-pick: CHERRY_PICK_HEAD untouched", _has(local, "CHERRY_PICK_HEAD"))

with tempfile.TemporaryDirectory() as td:
    local, origin = make_pair(td)
    write(origin, "r.txt", "origin\n"); run(origin, "add", "r.txt")
    run(origin, "commit", "-q", "-m", "origin r", "--no-verify")
    write(local, "r.txt", "local\n"); run(local, "add", "r.txt")
    run(local, "commit", "-q", "-m", "local r", "--no-verify")
    run(local, "fetch", "-q", "origin")
    run(local, "rebase", "origin/main", check_rc=False)  # conflicts -> rebase in progress
    r = cmf.sync(local, "main")
    check("F2 rebase: status BLOCKED_OP_IN_PROGRESS", r["status"] == "BLOCKED_OP_IN_PROGRESS", repr(r))
    check("F2 rebase: names it", any("rebase" in o for o in (r.get("in_progress_ops") or [])), repr(r))
    run(local, "rebase", "--abort", check_rc=False)

# --- F5: live work claims covering this repo block the merge (both directions) -------
import datetime as _dt


def _claims_case(label, make_claim, expect_blocked):
    with tempfile.TemporaryDirectory() as td:
        local, origin = make_pair(td)
        commit(origin, "origin moves ahead", fname="o.txt")
        cdir = os.path.join(td, "claims")
        os.makedirs(cdir)
        make_claim(cdir, local, td)
        before = run(local, "rev-parse", "HEAD").stdout.strip()
        cmf.CLAIMS_DIR_OVERRIDE = cdir
        try:
            r = cmf.sync(local, "main")
        finally:
            cmf.CLAIMS_DIR_OVERRIDE = _EMPTY_CLAIMS
        if expect_blocked:
            check("F5 %s: status BLOCKED_CLAIMED" % label, r["status"] == "BLOCKED_CLAIMED", repr(r))
            check("F5 %s: HEAD did not move" % label,
                  run(local, "rev-parse", "HEAD").stdout.strip() == before)
            check("F5 %s: names the blocking claim" % label, bool(r.get("blocking_claims")), repr(r))
        else:
            check("F5 %s: not blocked, merged" % label, r["status"] == "MERGED", repr(r))


_claims_case("file inside repo",
             lambda d, local, td: claim_work.write_claim(
                 "repo-housekeeping", "sess-a", "triage", base_dir=d,
                 paths=[os.path.join(local, "base_commit.txt")]),
             True)
_claims_case("repo-root directory claim",
             lambda d, local, td: claim_work.write_claim(
                 "repo-housekeeping", "sess-a", "triage", base_dir=d, paths=[local]),
             True)
_claims_case("pathless claim (cannot prove disjoint)",
             lambda d, local, td: claim_work.write_claim(
                 "hooks-override-auth", "sess-a", "banner claim", base_dir=d, paths=None),
             True)
_claims_case("corrector's own sched- claim is ignored",
             lambda d, local, td: claim_work.write_claim(
                 "sched-repo-housekeeping", "sess-sched", "this task", base_dir=d, paths=[local]),
             False)
_claims_case("another scheduled task's sched- claim still blocks",
             lambda d, local, td: claim_work.write_claim(
                 "sched-memory-commit-sweep", "sess-other-task", "committing memory", base_dir=d,
                 paths=[local]),
             True)
_claims_case("claim on a different repo is disjoint",
             lambda d, local, td: claim_work.write_claim(
                 "repo-housekeeping", "sess-a", "elsewhere", base_dir=d,
                 paths=[os.path.join(td, "some-other-repo", "x.md")]),
             False)
_claims_case("expired claim is ignored",
             lambda d, local, td: claim_work.write_claim(
                 "repo-housekeeping", "sess-a", "old", base_dir=d, paths=[local],
                 now=_dt.datetime.now() - _dt.timedelta(hours=5)),
             False)

# --- F5: claim_work unloadable -> ERROR (fail closed), never a silent merge ----------
with tempfile.TemporaryDirectory() as td:
    local, origin = make_pair(td)
    commit(origin, "origin moves ahead", fname="o.txt")
    before = run(local, "rev-parse", "HEAD").stdout.strip()
    real_path = cmf.CLAIM_WORK_PATH
    cmf.CLAIM_WORK_PATH = os.path.join(td, "no-such-claim_work.py")
    try:
        r = cmf.sync(local, "main")
    finally:
        cmf.CLAIM_WORK_PATH = real_path
    check("F5 unloadable: status ERROR", r["status"] == "ERROR", repr(r))
    check("F5 unloadable: HEAD did not move", run(local, "rev-parse", "HEAD").stdout.strip() == before)

# --- new statuses advance the unsynced streak, and exit 1 ------------------------------
with tempfile.TemporaryDirectory() as td:
    sp = os.path.join(td, "state.json")
    for i, st in enumerate(("BLOCKED_CLAIMED", "BLOCKED_OP_IN_PROGRESS"), 1):
        s = cmf.update_state({"status": st, "commits_merged": None, "sha": None}, sp,
                             now_iso="2026-09-12T16:45:0%d-04:00" % i)
        check("streak: %s advances consecutiveUnsynced" % st, s["consecutiveUnsynced"] == i, repr(s))

with tempfile.TemporaryDirectory() as td:
    local, origin = make_pair(td)
    commit(origin, "origin moves ahead", fname="o.txt")
    cdir = os.path.join(td, "claims"); os.makedirs(cdir)
    claim_work.write_claim("repo-housekeeping", "sess-a", "triage", base_dir=cdir, paths=[local])
    cmf.CLAIMS_DIR_OVERRIDE = cdir
    try:
        rc = cmf.main(["--repo", local, "--canonical", "main", "--json"])
    finally:
        cmf.CLAIMS_DIR_OVERRIDE = _EMPTY_CLAIMS
    check("main(): BLOCKED_CLAIMED exits 1", rc == 1, "rc=%r" % rc)

# =====================================================================================
# Adversarial review of the fix above (2026-09-12). Each scenario was reproduced as a
# failure against the first fix.
# =====================================================================================


def _conflicting_feature(local):
    """A local `feature` branch that conflicts with local main on h.txt. Returns its sha."""
    write(local, "h.txt", "base\n"); run(local, "add", "h.txt")
    run(local, "commit", "-q", "-m", "h base", "--no-verify")
    run(local, "checkout", "-q", "-b", "feature")
    write(local, "h.txt", "feature\n"); run(local, "commit", "-q", "-am", "feature h", "--no-verify")
    sha = run(local, "rev-parse", "HEAD").stdout.strip()
    run(local, "checkout", "-q", "main")
    write(local, "h.txt", "main\n"); run(local, "commit", "-q", "-am", "main h", "--no-verify")
    return sha


def _race_case(label, trigger):
    """Another session starts a conflicted merge mid-run (at `trigger`), then resolves
    and stages it. The corrector must never abort it or wipe the resolution."""
    with tempfile.TemporaryDirectory() as td:
        local, origin = make_pair(td)
        feature = _conflicting_feature(local)
        commit(origin, "origin moves ahead", fname="o.txt")
        real = cmf._git
        fired = []

        def other_session():
            run(local, "merge", "feature", check_rc=False)
            write(local, "h.txt", "HUMAN RESOLUTION WORK\n")
            run(local, "add", "h.txt")
            fired.append(True)

        def wrapped(args, repo):
            if not fired and trigger == "before-merge" and args[:2] == ["merge", "--no-commit"]:
                other_session()
            res = real(args, repo)
            if not fired and trigger == "after-fetch" and args[:1] == ["fetch"]:
                other_session()
            return res
        cmf._git = wrapped
        try:
            r = cmf.sync(local, "main")
        finally:
            cmf._git = real
        check("race %s: the other session's merge really started" % label, bool(fired))
        check("race %s: status BLOCKED_OP_IN_PROGRESS" % label,
              r["status"] == "BLOCKED_OP_IN_PROGRESS", repr(r))
        check("race %s: never claims it aborted anything" % label, r.get("merge_aborted") is not True, repr(r))
        check("race %s: their MERGE_HEAD survives" % label,
              _has(local, "MERGE_HEAD") and run(local, "rev-parse", "MERGE_HEAD").stdout.strip() == feature)
        check("race %s: their resolution survives" % label,
              open(os.path.join(local, "h.txt"), encoding="utf-8").read() == "HUMAN RESOLUTION WORK\n")


_race_case("after fetch", "after-fetch")
_race_case("just before the merge command", "before-merge")

# --- rev-parse failing for a reason other than "ref absent" is NOT "absent" -------------
with tempfile.TemporaryDirectory() as td:
    local, origin = make_pair(td)
    _conflicting_feature(local)
    run(local, "merge", "feature", check_rc=False)
    real = cmf._git

    def flaky(args, repo):
        if args[:1] == ["rev-parse"] and "--verify" in args:
            return 127, "", "timed out"
        if args[:2] == ["merge", "--abort"]:
            return 128, "", "fatal: simulated"
        return real(args, repo)
    cmf._git = flaky
    try:
        aborted = cmf.abort_merge(local)
        ops = cmf.in_progress_ops(local)
    finally:
        cmf._git = real
    check("rc127: abort_merge does not report success while MERGE_HEAD exists",
          aborted is False and _has(local, "MERGE_HEAD"), "aborted=%r" % aborted)
    check("rc127: in_progress_ops fails closed on an unverifiable ref", bool(ops), repr(ops))
    run(local, "merge", "--abort", check_rc=False)

# --- a stale index.lock present BEFORE the run -> ERROR, never a silent routine block ----
with tempfile.TemporaryDirectory() as td:
    local, origin = make_pair(td)
    commit(origin, "origin moves ahead", fname="o.txt")
    lock = os.path.join(local, ".git", "index.lock")
    open(lock, "w").close()
    try:
        r = cmf.sync(local, "main")
    finally:
        os.remove(lock)
    check("stale lock: status ERROR (not BLOCKED_DIRTY_OVERLAP with no paths)",
          r["status"] == "ERROR", repr(r))
    check("stale lock: detail names index.lock", "index.lock" in (r["detail"] or ""), repr(r))

# --- paused multi-commit cherry-pick sequence (sequencer, no CHERRY_PICK_HEAD) + bisect ---
with tempfile.TemporaryDirectory() as td:
    local, origin = make_pair(td)
    write(local, "c.txt", "base\n"); run(local, "add", "c.txt")
    run(local, "commit", "-q", "-m", "c base", "--no-verify")
    run(local, "checkout", "-q", "-b", "side")
    write(local, "c.txt", "side\n"); run(local, "commit", "-q", "-am", "side c", "--no-verify")
    s1 = run(local, "rev-parse", "HEAD").stdout.strip()
    commit(local, "side two", fname="s2.txt")
    s2 = run(local, "rev-parse", "HEAD").stdout.strip()
    run(local, "checkout", "-q", "main")
    write(local, "c.txt", "main\n"); run(local, "commit", "-q", "-am", "main c", "--no-verify")
    run(local, "cherry-pick", s1, s2, check_rc=False)  # stops on s1
    write(local, "c.txt", "resolved\n"); run(local, "add", "c.txt")
    run(local, "commit", "-q", "--no-edit", "--no-verify", check_rc=False)  # clears CHERRY_PICK_HEAD only
    commit(origin, "origin moves", fname="o3.txt")
    has_seq = os.path.isdir(os.path.join(local, ".git", "sequencer"))
    r = cmf.sync(local, "main")
    check("sequencer: fixture really left a paused sequence", has_seq and not _has(local, "CHERRY_PICK_HEAD"))
    check("sequencer: status BLOCKED_OP_IN_PROGRESS", r["status"] == "BLOCKED_OP_IN_PROGRESS", repr(r))
    run(local, "cherry-pick", "--quit", check_rc=False)

with tempfile.TemporaryDirectory() as td:
    local, origin = make_pair(td)
    commit(local, "second", fname="b2.txt")
    run(local, "bisect", "start")
    commit(origin, "origin moves", fname="o4.txt")
    r = cmf.sync(local, "main")
    check("bisect: status BLOCKED_OP_IN_PROGRESS", r["status"] == "BLOCKED_OP_IN_PROGRESS", repr(r))
    run(local, "bisect", "reset", check_rc=False)

# =====================================================================================
# Adversarial review round 2 (2026-09-12).
# =====================================================================================

# --- origin/main moves between resolving the target and merging -> own conflict still aborted --
with tempfile.TemporaryDirectory() as td:
    local, origin = make_pair(td)
    write(origin, "shared.txt", "origin line\n"); run(origin, "add", "shared.txt")
    run(origin, "commit", "-q", "-m", "origin edit", "--no-verify")
    write(local, "shared.txt", "local line\n"); run(local, "add", "shared.txt")
    run(local, "commit", "-q", "-m", "local edit", "--no-verify")
    real = cmf._git
    moved = []

    def racing_fetch(args, repo):
        if not moved and args[:2] == ["merge", "--no-commit"]:
            commit(origin, "origin moves again", fname="later.txt")
            run(local, "fetch", "-q", "origin")  # another session's fetch
            moved.append(True)
        return real(args, repo)
    cmf._git = racing_fetch
    try:
        r = cmf.sync(local, "main")
    finally:
        cmf._git = real
    check("moving target: status BLOCKED_CONFLICT", r["status"] == "BLOCKED_CONFLICT", repr(r))
    check("moving target: own merge aborted, not stranded",
          r.get("merge_aborted") is True and not _has(local, "MERGE_HEAD"), repr(r))
    run(local, "merge", "--abort", check_rc=False)

# --- a conflicted PATH containing a refusal phrase is not mistaken for a refusal ---------
with tempfile.TemporaryDirectory() as td:
    local, origin = make_pair(td)
    os.makedirs(os.path.join(origin, "notes")); os.makedirs(os.path.join(local, "notes"))
    name = os.path.join("notes", "unmerged files audit.md")
    write(origin, name, "origin line\n"); run(origin, "add", name)
    run(origin, "commit", "-q", "-m", "origin edit", "--no-verify")
    write(local, name, "local line\n"); run(local, "add", name)
    run(local, "commit", "-q", "-m", "local edit", "--no-verify")
    r = cmf.sync(local, "main")
    check("marker in path: status BLOCKED_CONFLICT", r["status"] == "BLOCKED_CONFLICT", repr(r))
    check("marker in path: own merge aborted", not _has(local, "MERGE_HEAD"), repr(r))
    run(local, "merge", "--abort", check_rc=False)

# --- git output is pinned to English so the refusal markers can match -------------------
_seen_env = []
_real_run = cmf.subprocess.run


def _spy(*a, **k):
    _seen_env.append(k.get("env"))
    return _real_run(*a, **k)
cmf.subprocess.run = _spy
try:
    cmf._git(["--version"], HERE)
finally:
    cmf.subprocess.run = _real_run
check("locale: _git runs git with LC_ALL=C",
      bool(_seen_env) and (_seen_env[0] or {}).get("LC_ALL") == "C", repr(_seen_env[:1]))

# --- untracked files inside a directory origin turns into a file -> routine, not ERROR --
check("parse: 'would lose untracked files in them' header lists the directory",
      cmf.parse_overlap_paths(
          "error: Updating the following directories would lose untracked files in them:\n"
          "\tx\n\nAborting\n") == ["x"])
with tempfile.TemporaryDirectory() as td:
    local, origin = make_pair(td)
    os.makedirs(os.path.join(origin, "x"))
    write(origin, os.path.join("x", "a.txt"), "a\n"); run(origin, "add", "x")
    run(origin, "commit", "-q", "-m", "x dir", "--no-verify")
    run(local, "pull", "-q", "origin", "main")
    run(origin, "rm", "-q", "-r", "x"); write(origin, "x", "now a file\n"); run(origin, "add", "x")
    run(origin, "commit", "-q", "-m", "x becomes a file", "--no-verify")
    write(local, os.path.join("x", "untracked.txt"), "local wip\n")
    r = cmf.sync(local, "main")
    check("dir->file: routine BLOCKED_DIRTY_OVERLAP, not ERROR",
          r["status"] == "BLOCKED_DIRTY_OVERLAP" and bool(r.get("blocked_paths")), repr(r))
    check("dir->file: untracked WIP preserved",
          os.path.isfile(os.path.join(local, "x", "untracked.txt")))

# =====================================================================================
# Refused merge rewrote the whole dirty tree (2026-09-21). On a branch with its own
# commits (non-ff), `git merge --no-commit --no-ff` refusing over overlapping WIP still
# rewrote EVERY dirty tracked file -- new mtime, LF->CRLF under core.autocrlf=true --
# including files that do not overlap. The overlap is now computed read-only first and
# `git merge` is never invoked when it is non-empty.
# =====================================================================================


def _non_ff_with_dirty(td):
    """local has its own commit (non-ff), autocrlf=true, a dirty OVERLAPPING tracked
    file and a dirty NON-overlapping tracked file, both LF on disk with an old mtime."""
    local, origin = make_pair(td)
    run(local, "config", "core.autocrlf", "true")
    for f in ("shared.txt", "bystander.txt"):
        with open(os.path.join(local, f), "wb") as fh:
            fh.write(b"committed\n")
        run(local, "add", f)
    run(local, "commit", "-q", "-m", "local own commit", "--no-verify")
    run(origin, "pull", "-q", local, "main")  # origin shares the base, then diverges
    with open(os.path.join(origin, "shared.txt"), "wb") as fh:
        fh.write(b"origin edit\n")
    run(origin, "commit", "-q", "-am", "origin edits shared", "--no-verify")
    commit(local, "local diverges", fname="mine.txt")  # local now non-ff
    snap = {}
    for f in ("shared.txt", "bystander.txt"):
        p = os.path.join(local, f)
        with open(p, "wb") as fh:
            fh.write(("dirty %s\nsecond line\n" % f).encode())
        os.utime(p, (1_600_000_000, 1_600_000_000))
        snap[f] = (os.stat(p).st_mtime_ns, open(p, "rb").read())
    return local, origin, snap


with tempfile.TemporaryDirectory() as td:
    local, origin, snap = _non_ff_with_dirty(td)
    merges = []
    real = cmf._git

    def spy(args, repo):
        if args[:1] == ["merge"]:
            merges.append(args)
        return real(args, repo)
    cmf._git = spy
    try:
        r = cmf.sync(local, "main")
    finally:
        cmf._git = real
    check("non-ff dirty: status BLOCKED_DIRTY_OVERLAP", r["status"] == "BLOCKED_DIRTY_OVERLAP", repr(r))
    check("non-ff dirty: blocked_paths names only the overlapping file",
          r.get("blocked_paths") == ["shared.txt"], repr(r))
    for f in ("bystander.txt", "shared.txt"):
        p = os.path.join(local, f)
        check("non-ff dirty: %s mtime unchanged" % f, os.stat(p).st_mtime_ns == snap[f][0],
              "%r -> %r" % (snap[f][0], os.stat(p).st_mtime_ns))
        check("non-ff dirty: %s bytes unchanged (no LF->CRLF)" % f,
              open(p, "rb").read() == snap[f][1], repr(open(p, "rb").read()))
    check("non-ff dirty: git merge never invoked", merges == [], repr(merges))
    check("non-ff dirty: HEAD untouched, no MERGE_HEAD", not _has(local, "MERGE_HEAD"))

# --- the read-only overlap check itself cannot run -> ERROR, merge never attempted ------
with tempfile.TemporaryDirectory() as td:
    local, origin, snap = _non_ff_with_dirty(td)
    merges = []
    real = cmf._git

    def broken_status(args, repo):
        if args[:1] == ["merge"]:
            merges.append(args)
        if args[:1] == ["status"]:
            return 128, "", "fatal: simulated"
        return real(args, repo)
    cmf._git = broken_status
    try:
        r = cmf.sync(local, "main")
    finally:
        cmf._git = real
    check("precheck fails: status ERROR", r["status"] == "ERROR", repr(r))
    check("precheck fails: git merge never invoked", merges == [], repr(merges))
    check("precheck fails: bystander untouched",
          open(os.path.join(local, "bystander.txt"), "rb").read() == snap["bystander.txt"][1])

# --- dirty but DISJOINT from the incoming change -> still merges ------------------------
with tempfile.TemporaryDirectory() as td:
    local, origin = make_pair(td)
    commit(origin, "origin adds new", fname="new.txt")
    write(local, "base_commit.txt", "dirty, not touched by origin\n")
    write(local, "scratch.txt", "untracked, not touched by origin\n")
    r = cmf.sync(local, "main")
    check("disjoint dirty: status MERGED", r["status"] == "MERGED", repr(r))
    check("disjoint dirty: WIP preserved",
          open(os.path.join(local, "base_commit.txt")).read() == "dirty, not touched by origin\n"
          and os.path.isfile(os.path.join(local, "scratch.txt")))

check("overlap: exact, dir-prefix both ways, case-insensitive, disjoint",
      cmf.overlapping_paths(["a/b.txt", "x/wip.txt", "D/e.md", "keep.txt", "sub/new.txt"],
                            ["a/b.txt", "x", "d/E.md", "sub", "other.txt"])
      == ["a/b.txt", "x/wip.txt", "D/e.md", "sub/new.txt"])
check("overlap: 'ab' is not under 'a'", cmf.overlapping_paths(["ab/c.txt"], ["a"]) == [])
check("porcelain v2 -z: modified, rename pair, unmerged, untracked, spaces in names",
      cmf.parse_porcelain_v2_z(
          "1 .M N... 100644 100644 100644 aaa aaa one two.txt\0"
          "2 R. N... 100644 100644 100644 aaa aaa R100 new name.txt\0old name.txt\0"
          "u UU N... 100644 100644 100644 100644 a b c conf.txt\0"
          "? dir/u v.txt\0")
      == ["one two.txt", "new name.txt", "old name.txt", "conf.txt", "dir/u v.txt"])
with tempfile.TemporaryDirectory() as td:
    local, origin = make_pair(td)
    write(local, "base_commit.txt", "modified\n")
    write(local, "a b.txt", "untracked\n")
    os.makedirs(os.path.join(local, "nd"))
    write(local, os.path.join("nd", "deep.txt"), "untracked in new dir\n")
    rc, out, _ = cmf._git(["status", "--porcelain=v2", "-z", "--untracked-files=all"], local)
    check("porcelain v2 -z: live git output parses (first entry intact after strip)",
          sorted(cmf.parse_porcelain_v2_z(out)) == ["a b.txt", "base_commit.txt", "nd/deep.txt"],
          repr(out))

passed = sum(1 for ok, _ in _results if ok)
print("\ncheckout-merge-forward tests: %d/%d passed" % (passed, len(_results)))
sys.exit(0 if passed == len(_results) else 1)
