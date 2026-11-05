#!/usr/bin/env python3
"""commit-own-edit.py -- at the end of an unattended run, commit the ONE memory file the run
edited, but only when preflight-shared-checkout.py proves this session is its sole recorded
owner. Anything less leaves the file for ora-memory-commit-sweep, exactly as before.

WHY (2026-11-05): ora-appsec-sweep appends its findings to open-items-tracker.md and, being
report-only, never committed them. The only backstop, ora-memory-commit-sweep, runs weekly
(Fridays 19:00), so each Wednesday run's rows sat uncommitted for about two days. For that whole
time preflight-shared-checkout.py reported the tracker CONTESTED to every other writer (owner:
the ended run, labelled ORPHANED). The 2026-11-04 rows (OI-389..395) blocked another session
until it landed them by hand as e8b708c6; dirty-tree triage had landed earlier backlogs the same
way (09482331, 4e8aa134).

WHAT IT DOES -- one path, one commit, or nothing:
  1. Refuses (ERROR) anything that is not a tracked file under MEMORY_PREFIX, the tree
     land-live-commits.py ships to main (a commit outside it would block that pipeline with
     BLOCKED_NON_MEMORY), and refuses to run without a session id or a message.
  2. Leaves the file (LEFT_FOR_SWEEP) unless ALL of these hold:
       - HEAD is on a branch and no merge, rebase, cherry-pick or revert is in progress;
       - the index holds HEAD's version of the path (nobody has staged a version of it);
       - the preflight (no --since, no --accept-stale) says CLEAR with the path in
         dirty_overlap_mine: this session is its only live recorded owner, no other session's
         live claim covers it, and no owner is stale-only or unknown;
       - the file's bytes did not change while that was checked (hashed before and after).
  3. Commits with `git commit --only -- <path>`: the working-tree content of that one path,
     ignoring whatever else sits in the shared index (other staged paths stay staged).
  4. Verifies the commit it made, found by a per-run trailer: one parent, exactly that path,
     exactly the blob that was checked, on the branch that was checked.

WHY A SCRIPT, NOT TWO COMMANDS IN THE TASK SPEC: the git sequence has documented traps in this
checkout (a pathspec commit re-reads the working tree, a bare commit takes the whole shared
index, index.lock contention), and an unattended run should not improvise around them -- the
same reasoning as memory-commit-sweep.py and append-event-log.py.

ACCEPTED LIMITATION, inherited from the preflight (see its docstring): "sole owner" means sole
RECORDED owner. Provenance comes from the Edit/Write tool hook, so a foreign edit made through
Bash or a script and left uncommitted BEFORE this run's edit is invisible and would be committed
with it. The weekly sweep commits such content blind already, so this exposure is strictly
smaller. A foreign write DURING the check changes the hash and is caught. Callers must write the
file with the Edit tool; otherwise their own edit reads as unowned and is left for the sweep
(safe, but nothing lands).

Never pushes, never stages any other path, never resets, stashes or checks out, never touches a
lock it did not take. Landing on main stays land-live-commits.py's job (memory-commit-sweep
STEP 2).

Exit: 0 COMMITTED or NOTHING_TO_COMMIT | 1 LEFT_FOR_SWEEP (not provably this run's alone, or the
index stayed locked; the weekly sweep lands it) | 2 ERROR (refused input or a git/preflight
failure; nothing committed) | 3 COMMITTED_UNVERIFIED (a commit landed but failed verification; a
human must look at it). The last stdout line is always RESULT_JSON={...}.

Usage:
  python commit-own-edit.py --path <memory file> --message "<commit subject>" [--session ID]
"""
import argparse
import json
import os
import subprocess
import sys
import time
import traceback
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
PREFLIGHT = os.path.join(HERE, "preflight-shared-checkout.py")

# Must equal land-live-commits.py's MEMORY (pinned by test_memory_prefix_matches_land_live_commits).
MEMORY_PREFIX = "projects/C--Users-Owner-OneDrive---Oxford-Capital-Partners/memory/"

EXIT = {"COMMITTED": 0, "NOTHING_TO_COMMIT": 0, "LEFT_FOR_SWEEP": 1, "ERROR": 2,
        "COMMITTED_UNVERIFIED": 3}

GIT_TIMEOUT = 60
COMMIT_TIMEOUT = 120  # generous: a killed `git commit` can strand .git/index.lock
PREFLIGHT_TIMEOUT = 300  # ~1 s on the live checkout (2026-11-05)
IN_PROGRESS = ("MERGE_HEAD", "CHERRY_PICK_HEAD", "REVERT_HEAD", "rebase-merge", "rebase-apply")

# Repository-selecting variables a parent git process (a hook) may export; inheriting one would
# point every call below at another repository or index.
_GIT_ENV_VARS = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR",
                 "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_PREFIX")

COMMIT_BODY = ("Landed by maintenance/commit-own-edit.py at the end of an unattended run: "
               "preflight-shared-checkout.py found this session to be the path's sole recorded "
               "owner, so the run committed its own edit instead of leaving it uncommitted for "
               "the weekly memory-commit-sweep.")


def _env():
    env = dict(os.environ)
    for name in _GIT_ENV_VARS:
        env.pop(name, None)
    return env


def _git(repo, *args, timeout=GIT_TIMEOUT):
    """(returncode, stdout, stderr). returncode is None when git could not run or timed out.
    --literal-pathspecs: every path argument is a file name, never a glob."""
    try:
        p = subprocess.run(["git", "--literal-pathspecs"] + list(args), cwd=repo,
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=timeout, env=_env())
    except (OSError, subprocess.SubprocessError) as exc:
        return None, "", str(exc)
    return p.returncode, p.stdout, p.stderr


def run_preflight(repo, path, session, extra_args=()):
    """preflight-shared-checkout.py --json for one path -> (exit_code, report, detail).
    report is None when the preflight could not run or did not print JSON."""
    cmd = [sys.executable, PREFLIGHT, "--repo", repo, "--paths", path,
           "--session", session, "--json"] + list(extra_args)
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=PREFLIGHT_TIMEOUT, env=_env())
    except (OSError, subprocess.SubprocessError) as exc:
        return None, None, str(exc)
    try:
        report = json.loads(p.stdout)
    except ValueError:
        return p.returncode, None, (p.stderr or p.stdout).strip()[-500:]
    if not isinstance(report, dict):
        return p.returncode, None, "preflight printed JSON that is not an object"
    return p.returncode, report, ""


def _same_path(a, b):
    return os.path.normcase(a or "") == os.path.normcase(b or "")


def _preflight_summary(code, report, rel):
    mine = any(_same_path(d.get("path"), rel) for d in report.get("dirty_overlap_mine") or [])
    return {
        "verdict": report.get("verdict"),
        "exit_code": code,
        "path_is_mine": mine,
        "foreign": [{"path": d.get("path"), "owners": d.get("owners"),
                     "stale_owners": d.get("stale_owners")}
                    for d in report.get("dirty_overlap_foreign") or []],
        "competing_claims": [{"slug": c.get("slug"), "session_id": c.get("session_id")}
                             for c in report.get("competing_claims") or []],
    }


def _hash(repo, rel):
    """Blob id `git add` would store for the working-tree file (filters applied)."""
    rc, out, _ = _git(repo, "hash-object", "--", rel)
    return out.strip() if rc == 0 and out.strip() else None


def _find_commit(repo, nonce):
    """The commit whose message carries this run's nonce, or None."""
    rc, out, _ = _git(repo, "log", "-1", "--format=%H%x00%B", "HEAD")
    if rc == 0 and nonce in out:
        return out.split("\0", 1)[0].strip()
    rc, out, _ = _git(repo, "log", "--all", "--fixed-strings", "--grep=" + nonce, "--format=%H")
    shas = out.split() if rc == 0 else []
    return shas[0] if len(shas) == 1 else None


def verify_commit(repo, sha, rel, expected_blob, branch=None):
    """Problems with `sha` as the landing of `rel` at `expected_blob` ([] == verified)."""
    problems = []
    rc, out, err = _git(repo, "rev-list", "--parents", "-n", "1", sha)
    if rc != 0:
        return ["cannot read commit %s: %s" % (sha, err.strip())]
    parents = len(out.split()) - 1
    if parents != 1:
        problems.append("commit %s has %d parents, expected 1" % (sha, parents))
    rc, out, err = _git(repo, "diff-tree", "-z", "--no-commit-id", "--name-only", "-r", sha)
    paths = sorted(p for p in out.split("\0") if p) if rc == 0 else None
    if paths != [rel]:
        problems.append("commit %s touched %s, expected only %s"
                        % (sha, paths if paths is not None else "(unreadable)", rel))
    rc, out, _ = _git(repo, "rev-parse", "--verify", "-q", "%s:%s" % (sha, rel))
    blob = out.strip() if rc == 0 else None
    if blob != expected_blob:
        problems.append("commit %s stored blob %s for %s, expected %s"
                        % (sha, blob, rel, expected_blob))
    if branch:
        rc, _, _ = _git(repo, "merge-base", "--is-ancestor", sha, "refs/heads/" + branch)
        if rc != 0:
            problems.append("commit %s is not on branch %s" % (sha, branch))
    return problems


def land(path, message, session=None, sessions_dir=None, claims_dir=None,
         transcripts_dir=None, lock_attempts=3, lock_wait=3.0, preflight=None):
    """Commit `path` if this session provably owns all of its uncommitted content. Never raises
    for an expected condition; returns the result dict printed as RESULT_JSON."""
    if session is None:
        session = os.environ.get("CLAUDE_CODE_SESSION_ID", "")
    session = (session or "").strip()
    message = (message or "").strip()
    res = {"status": None, "exit_code": None, "path": None, "repo": None,
           "session": session or None, "branch": None, "commit": None, "reason": "",
           "preflight": None}

    def done(status, reason):
        res.update(status=status, exit_code=EXIT[status], reason=reason)
        return res

    if not session:
        return done("ERROR", "no session id (pass --session or set CLAUDE_CODE_SESSION_ID); "
                             "ownership cannot be proven without one")
    if not message:
        return done("ERROR", "empty commit message")
    full = os.path.realpath(os.path.abspath(path))
    if not os.path.isfile(full):
        return done("ERROR", "not an existing file: %s" % path)
    rc, out, err = _git(os.path.dirname(full), "rev-parse", "--show-toplevel")
    if rc != 0 or not out.strip():
        return done("ERROR", "not inside a git work tree: %s" % (err.strip() or path))
    repo = os.path.realpath(out.strip())
    res["repo"] = repo
    rel = os.path.relpath(full, repo).replace(os.sep, "/")
    rc, out, err = _git(repo, "ls-files", "-z", "--full-name", "--", rel)
    entries = [e for e in out.split("\0") if e] if rc == 0 else []
    if len(entries) != 1:
        return done("ERROR", "not a tracked file: %s" % rel)
    rel = entries[0]  # the index's own spelling
    res["path"] = rel
    if not rel.startswith(MEMORY_PREFIX):
        return done("ERROR", "%s is outside %s; land-live-commits.py would refuse to ship a "
                             "commit of it (BLOCKED_NON_MEMORY)" % (rel, MEMORY_PREFIX))

    rc, out, _ = _git(repo, "symbolic-ref", "-q", "--short", "HEAD")
    if rc != 0 or not out.strip():
        return done("LEFT_FOR_SWEEP", "HEAD is detached; a commit here would sit on no branch")
    res["branch"] = out.strip()
    rc, out, err = _git(repo, "rev-parse", "--absolute-git-dir")
    if rc != 0 or not out.strip():
        return done("ERROR", "cannot locate the git dir: %s" % err.strip())
    git_dir = out.strip()
    busy = [n for n in IN_PROGRESS if os.path.exists(os.path.join(git_dir, n))]
    if busy:
        return done("LEFT_FOR_SWEEP", "repository is mid-operation (%s)" % ", ".join(busy))

    rc, _, err = _git(repo, "diff", "--quiet", "HEAD", "--", rel)
    if rc == 0:
        return done("NOTHING_TO_COMMIT", "the file matches HEAD")
    if rc != 1:
        return done("ERROR", "git diff HEAD failed: %s" % err.strip())
    rc, _, err = _git(repo, "diff", "--cached", "--quiet", "--", rel)
    if rc == 1:
        return done("LEFT_FOR_SWEEP", "a version of the file is staged in the shared index; it "
                                      "is not this run's to commit or discard")
    if rc != 0:
        return done("ERROR", "git diff --cached failed: %s" % err.strip())

    checked_blob = _hash(repo, rel)
    if not checked_blob:
        return done("ERROR", "could not hash %s" % rel)
    extra = []
    for flag, value in (("--sessions-dir", sessions_dir), ("--claims-dir", claims_dir),
                        ("--session-transcripts-dir", transcripts_dir)):
        if value:
            extra += [flag, value]
    code, report, detail = (preflight or run_preflight)(repo, full, session, extra)
    if report is None:
        return done("ERROR", "preflight returned no verdict (exit %s): %s" % (code, detail))
    summary = _preflight_summary(code, report, rel)
    res["preflight"] = summary
    if code != 0 or summary["verdict"] != "CLEAR" or not summary["path_is_mine"]:
        return done("LEFT_FOR_SWEEP", "preflight %s: this session is not provably the file's "
                                      "sole recorded owner" % summary["verdict"])

    nonce = uuid.uuid4().hex
    trailers = "Commit-Own-Edit-Session: %s\nCommit-Own-Edit-Run: %s" % (session, nonce)
    lock = os.path.join(git_dir, "index.lock")
    sha, last = None, ""
    for attempt in range(max(1, lock_attempts)):
        if attempt:
            time.sleep(lock_wait)
        if os.path.exists(lock):
            last = "index.lock present"
            continue
        if _hash(repo, rel) != checked_blob:
            return done("LEFT_FOR_SWEEP", "the file changed while it was being checked")
        rc, out, err = _git(repo, "commit", "--only", "--quiet", "-m", message,
                            "-m", COMMIT_BODY, "-m", trailers, "--", rel,
                            timeout=COMMIT_TIMEOUT)
        sha = _find_commit(repo, nonce)  # also settles a timed-out commit either way
        if sha:
            break
        last = (err or out).strip()
        if "index.lock" not in last:
            return done("ERROR", "git commit failed (exit %s): %s" % (rc, last[:500]))
    if not sha:
        return done("LEFT_FOR_SWEEP", "the index stayed locked by another git process (%d "
                                      "attempts): %s" % (max(1, lock_attempts), last[:300]))

    res["commit"] = sha
    problems = verify_commit(repo, sha, rel, checked_blob, branch=res["branch"])
    if problems:
        return done("COMMITTED_UNVERIFIED", "; ".join(problems))
    rc, _, _ = _git(repo, "diff", "--quiet", sha, "--", rel)
    res["worktree_matches_commit"] = rc == 0
    return done("COMMITTED", "committed %s as %s on %s" % (rel, sha[:10], res["branch"]))


def _parse_args(argv):
    ap = argparse.ArgumentParser(
        description="Commit ONE memory file this session edited, only when "
                    "preflight-shared-checkout.py proves this session is its sole recorded "
                    "owner; otherwise leave it for ora-memory-commit-sweep. Exit 0 "
                    "COMMITTED/NOTHING_TO_COMMIT, 1 LEFT_FOR_SWEEP, 2 ERROR, 3 "
                    "COMMITTED_UNVERIFIED. See the module docstring.")
    ap.add_argument("--path", required=True, help="the memory file this run edited")
    ap.add_argument("--message", required=True,
                    help="commit subject, e.g. 'memory(open-items): ora-appsec-sweep "
                         "2026-11-11 files OI-397..OI-399'")
    ap.add_argument("--session", default=None,
                    help="this run's session id (default: $CLAUDE_CODE_SESSION_ID)")
    ap.add_argument("--sessions-dir", default=None, help="preflight pass-through (tests)")
    ap.add_argument("--claims-dir", default=None, help="preflight pass-through (tests)")
    ap.add_argument("--transcripts-dir", default=None, help="preflight pass-through (tests)")
    return ap.parse_args(argv)


def main(argv=None):
    args = _parse_args(sys.argv[1:] if argv is None else argv)  # -h exits here, before any git
    try:
        r = land(args.path, args.message, session=args.session, sessions_dir=args.sessions_dir,
                 claims_dir=args.claims_dir, transcripts_dir=args.transcripts_dir)
    except Exception as exc:  # the verdict must survive anything, like the preflight's
        r = {"status": "ERROR", "exit_code": EXIT["ERROR"], "path": args.path,
             "reason": "unexpected %s: %s" % (type(exc).__name__, exc),
             "traceback": traceback.format_exc(limit=5)}
    print("COMMIT-OWN-EDIT %s -- %s: %s" % (r["status"], r.get("path") or args.path,
                                           r["reason"]))
    print("RESULT_JSON=" + json.dumps(r))
    return r["exit_code"]


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    sys.exit(main())
