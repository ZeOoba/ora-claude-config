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

passed = sum(1 for ok, _ in _results if ok)
print("\ncheckout-merge-forward tests: %d/%d passed" % (passed, len(_results)))
sys.exit(0 if passed == len(_results) else 1)
