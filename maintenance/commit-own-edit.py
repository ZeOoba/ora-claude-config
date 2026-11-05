#!/usr/bin/env python3
"""commit-own-edit.py -- land the ONE memory file an unattended run edited, at the end of the
run, but only when this session provably owns every uncommitted byte of it. Anything less
leaves the file for ora-memory-commit-sweep, exactly as before.

WHY (2026-11-05): ora-appsec-sweep appends its findings to open-items-tracker.md and, being
report-only, never committed them. The only backstop, ora-memory-commit-sweep, runs weekly
(Fridays 19:00), so each Wednesday run's rows sat uncommitted for about two days. For that whole
time preflight-shared-checkout.py reported the tracker CONTESTED to every other writer (owner:
the ended run, labelled ORPHANED). The 2026-11-04 rows (OI-389..395) blocked another session
until it landed them by hand as e8b708c6; dirty-tree triage had landed earlier backlogs the same
way (09482331, 4e8aa134).

TWO CALLS, around the run's own edits:
  --begin --path P       BEFORE the first edit. Records a baseline for (this session, P) beside
                         this session's provenance: whether P matched HEAD at that moment, and
                         HEAD's blob of it. BEGUN = clean. DIRTY_AT_BEGIN = someone's
                         uncommitted content was already in P, so the landing will refuse.
  --path P --message M   AFTER the last edit. Commits P, or leaves it.

THE LANDING COMMITS ONLY WHEN ALL OF THESE HOLD:
  - P is a tracked file under MEMORY_PREFIX (the tree land-live-commits.py ships; a commit
    outside it would block that pipeline with BLOCKED_NON_MEMORY); a session id and a message
    were given;
  - HEAD is on a branch, no merge/rebase/cherry-pick/revert is in progress, nothing of P is
    staged, and the baseline (if any) was clean;
  - P has been untouched for QUIET_SECONDS, so every Edit-tool write before the check has its
    touch record on disk (recorder lag measured live 2026-11-05: p50 0.3 s, p99 4.7 s), and P's
    (mtime, size) stays exactly as it was when judged quiet until the commit -- a write after
    the judgement would otherwise slip in with its touch record still pending;
  - preflight-shared-checkout.py says CLEAR with P in dirty_overlap_mine and provenance fully
    readable: this session is P's only LIVE recorded owner and no other session's claim covers
    it. STALE owners (sessions that touched P before its last commit -- the live tracker always
    has some) contest P, because a partial commit can leave their hunk dirty. They are excused
    (--accept-stale) only by a clean baseline with P not committed since: P then held no
    uncommitted content when this run began, so whatever they wrote was already committed;
  - right before the commit: the bytes `git add` would store for P are still the checked ones,
    HEAD's blob of P has not moved, nothing of P has been staged, and HEAD is still on the
    checked branch (compared as a full refs/heads/ name: a tag can share a branch's short name).
Then: `git commit --only -- P` (P's working-tree content, ignoring everything else in the shared
index -- other staged paths stay staged), and verification of the commit found by its per-run
trailer: one parent, parent's P unchanged, only P, the checked blob, on the checked branch. A
commit that fails verification is taken back (branch moved back only if it still points at it,
P's index entry restored): UNDONE. If taking it back fails too: COMMITTED_UNVERIFIED. If git
exits non-zero after creating the commit (it can fail to write the new index), P's index entry
is repaired when it still holds the old blob, which would otherwise stage a revert of the
commit. A commit that landed without this run's trailer (a commit-msg hook) cannot be verified
as this run's: COMMITTED_UNVERIFIED.

WHY A SCRIPT, NOT GIT COMMANDS IN THE TASK SPEC: the sequence has documented traps in this
checkout (a pathspec commit re-reads the working tree, a bare commit takes the whole shared
index, `git add` keeps CRLF for a path whose indexed blob has CRLF while hash-object normalises,
index.lock contention), and an unattended run should not improvise around them -- the same
reasoning as memory-commit-sweep.py and append-event-log.py.

RESIDUAL EXPOSURE. Provenance comes only from the Edit/Write tool hook. So a foreign write made
with Bash or a script DURING the run's window (after --begin, before the landing) is invisible,
and would be committed with the run's rows; without --begin, that window reaches back to P's
last commit. The same holds for a foreign Edit-tool touch recorded under a spelling the
preflight's owner lookup cannot match (a since-removed junction, an NTFS stream suffix, a
an extended-length or UNC-share spelling), and for touches in a session directory the preflight cannot list
(it reads such a directory as empty, not as unreadable). This helper refuses anything with a
recorded foreign owner; the weekly sweep it replaces for this case commits any settled content
without looking at owners.

Never pushes; never stages any path but P; never stashes or checks out; never touches a lock it
did not take; moves a ref only to take back its own just-made commit. Landing on main stays
land-live-commits.py's job (memory-commit-sweep STEP 2).

Exit: 0 COMMITTED, NOTHING_TO_COMMIT, BEGUN | 1 LEFT_FOR_SWEEP, DIRTY_AT_BEGIN | 2 ERROR
(refused input or a git/preflight failure; nothing committed) | 3 UNDONE, COMMITTED_UNVERIFIED (a
commit failed verification; a human should look). The last stdout line is always
RESULT_JSON={...}.

Usage:
  python commit-own-edit.py --begin --path <memory file>
  python commit-own-edit.py --path <memory file> --message "<commit subject>"
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
PREFLIGHT = os.path.join(HERE, "preflight-shared-checkout.py")

# Must equal land-live-commits.py's MEMORY (pinned by test_memory_prefix_matches_land_live_commits).
MEMORY_PREFIX = "projects/C--Users-Owner-OneDrive---Oxford-Capital-Partners/memory/"

EXIT = {"COMMITTED": 0, "NOTHING_TO_COMMIT": 0, "BEGUN": 0,
        "LEFT_FOR_SWEEP": 1, "DIRTY_AT_BEGIN": 1, "ERROR": 2,
        "UNDONE": 3, "COMMITTED_UNVERIFIED": 3}

GIT_TIMEOUT = 60
COMMIT_TIMEOUT = 120  # generous: a killed `git commit` can strand .git/index.lock
PREFLIGHT_TIMEOUT = 300  # ~1 s on the live checkout (2026-11-05)
QUIET_SECONDS = 15
# Capped so the worst case (quiet wait + lock retries + git and preflight time) stays inside the
# Bash tool's default 120 s timeout; a call that outlives it prints no RESULT_JSON to the run.
QUIET_MAX_WAIT = 60
IN_PROGRESS = ("MERGE_HEAD", "CHERRY_PICK_HEAD", "REVERT_HEAD", "rebase-merge", "rebase-apply")
_LOCK_RE = re.compile(r"\.lock\b|cannot lock ref", re.I)  # index.lock, <ref>.lock contention
BASELINE_DIR = "commit-own-edit"

# Repository-selecting variables a parent git process (a hook) may export; inheriting one would
# point every call below at another repository or index.
_GIT_ENV_VARS = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR",
                 "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_PREFIX")

COMMIT_BODY = ("Landed by maintenance/commit-own-edit.py at the end of an unattended run: "
               "preflight-shared-checkout.py found this session to be the path's only live "
               "recorded owner (stale owners excused only by a clean --begin baseline), so the "
               "run committed its own edit instead of leaving it for the weekly "
               "memory-commit-sweep.")


def _env(extra=None):
    env = dict(os.environ)
    for name in _GIT_ENV_VARS:
        env.pop(name, None)
    if extra:
        env.update(extra)
    return env


def _git(repo, *args, timeout=GIT_TIMEOUT, extra_env=None):
    """(returncode, stdout, stderr). returncode is None when git could not run or timed out.
    --literal-pathspecs: every path argument is a file name, never a glob."""
    try:
        p = subprocess.run(["git", "--literal-pathspecs"] + list(args), cwd=repo,
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=timeout, env=_env(extra_env))
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        return None, "", str(exc)
    return p.returncode, p.stdout, p.stderr


def _session(session):
    if session is None:
        session = os.environ.get("CLAUDE_CODE_SESSION_ID", "")
    return (session or "").strip()


def _default_sessions_dir():
    # Same default as hooks/lib/commit_provenance.py sessions_dir().
    return (os.environ.get("COMMIT_PROVENANCE_SESSIONS_DIR")
            or os.path.join(os.path.expanduser("~"), ".claude", "hooks", "sessions"))


def _locate(path):
    """({full, repo, rel}, None) for a tracked file under MEMORY_PREFIX, else (None, reason)."""
    try:
        full = os.path.realpath(os.path.abspath(path))
    except (OSError, ValueError) as exc:
        return None, "cannot resolve %s: %s" % (path, exc)
    if not os.path.isfile(full):
        return None, "not an existing file: %s" % path
    rc, out, err = _git(os.path.dirname(full), "rev-parse", "--show-toplevel")
    if rc != 0 or not out.strip():
        return None, "not inside a git work tree: %s" % (err.strip() or path)
    repo = os.path.realpath(out.strip())
    try:
        rel = os.path.relpath(full, repo).replace(os.sep, "/")
    except ValueError as exc:
        return None, "cannot place %s inside %s: %s" % (path, repo, exc)
    if rel == ".." or rel.startswith("../"):
        return None, "%s is outside %s" % (path, repo)
    rc, out, _ = _git(repo, "ls-files", "-z", "--full-name", "--", rel)
    entries = [e for e in out.split("\0") if e] if rc == 0 else []
    if len(entries) != 1:
        return None, "not a tracked file: %s" % rel
    rel = entries[0]  # the index's own spelling
    if not rel.startswith(MEMORY_PREFIX):
        return None, ("%s is outside %s; land-live-commits.py would refuse to ship a commit of "
                      "it (BLOCKED_NON_MEMORY)" % (rel, MEMORY_PREFIX))
    return {"full": full, "repo": repo, "rel": rel}, None


def _branch_ref(repo):
    """HEAD's full branch ref (refs/heads/<name>), or None when detached. Never --short: that
    turns into heads/<name> when a tag shares the branch's name."""
    rc, out, _ = _git(repo, "symbolic-ref", "-q", "HEAD")
    ref = out.strip() if rc == 0 else ""
    return ref if ref.startswith("refs/heads/") else None


def _short(ref):
    return ref[len("refs/heads/"):] if ref and ref.startswith("refs/heads/") else ref


def _head(repo):
    rc, out, _ = _git(repo, "rev-parse", "--verify", "-q", "HEAD")
    return out.strip() if rc == 0 and out.strip() else None


def _blob_at(repo, rev, rel):
    rc, out, _ = _git(repo, "rev-parse", "--verify", "-q", "%s:%s" % (rev, rel))
    return out.strip() if rc == 0 and out.strip() else None


def _busy(git_dir):
    return [n for n in IN_PROGRESS if os.path.exists(os.path.join(git_dir, n))]


def _last_commit_time(repo, rel):
    """Committer time of the newest commit touching rel -- the same instant the preflight's
    stale-owner rule compares touches against."""
    rc, out, _ = _git(repo, "log", "-1", "--format=%ct", "--", rel)
    try:
        return float(out.split()[0]) if rc == 0 else None
    except (IndexError, ValueError):
        return None


def _staged_blob(repo, rel, head):
    """The blob `git commit --only -- rel` would store right now: `git add` into a throwaway
    index seeded from `head`, which is the path commit --only takes. A CRLF-stored blob keeps
    its CRLF here exactly as git add keeps it, where hash-object would normalise it to LF and
    every check below would false-alarm."""
    tmp = tempfile.mkdtemp(prefix="coe-index-")
    try:
        env = {"GIT_INDEX_FILE": os.path.join(tmp, "index")}
        if _git(repo, "read-tree", head, extra_env=env)[0] != 0:
            return None
        if _git(repo, "add", "--", rel, extra_env=env)[0] != 0:
            return None
        rc, out, _ = _git(repo, "ls-files", "-s", "--", rel, extra_env=env)
        meta = out.split("\t", 1)[0].split() if rc == 0 else []
        return meta[1] if len(meta) == 3 else None
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _sig(full):
    """(mtime_ns, size) of the file, or None."""
    try:
        st = os.stat(full)
    except OSError:
        return None
    return (st.st_mtime_ns, st.st_size)


def _wait_quiet(full, quiet, max_wait):
    """The file's (mtime_ns, size) at the moment it was judged `quiet` seconds untouched, or
    None if that did not happen within `max_wait` seconds (or the file vanished). Every later
    check must still see exactly this state: a write after the judgement would otherwise slip
    in with its touch record still pending."""
    deadline = time.time() + max_wait
    while True:
        try:
            st = os.stat(full)
        except OSError:
            return None
        age = time.time() - st.st_mtime
        if age >= quiet:
            return (st.st_mtime_ns, st.st_size)
        pause = quiet - age
        if time.time() + pause > deadline:
            return None
        time.sleep(pause)


def _baseline_path(sessions_dir, session, repo, rel):
    key = hashlib.sha1(("%s|%s" % (os.path.normcase(repo), rel)).encode("utf-8")).hexdigest()
    return os.path.join(sessions_dir, session, BASELINE_DIR, key[:16] + ".json")


def _load_baseline(path):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            rec = json.load(fh)
    except (OSError, ValueError):
        return None
    return rec if isinstance(rec, dict) else None


def _baseline_excuses_stale(rec, repo, rel, head_blob):
    """(True, why) when a CLEAN baseline proves every touch older than P's last commit carries
    no uncommitted content: P matched HEAD when this run began, and has not been committed
    since (same HEAD blob, last commit not newer than the baseline)."""
    if rec is None:
        return False, "no --begin baseline for this session and path"
    if os.path.normcase(rec.get("repo") or "") != os.path.normcase(repo) or rec.get("rel") != rel:
        return False, "the baseline is for another file"
    if rec.get("base_blob") != head_blob:
        return False, "the file was committed after --begin"
    begun, last = rec.get("begun_at"), _last_commit_time(repo, rel)
    if not isinstance(begun, (int, float)) or last is None or last > begun:
        return False, "the file's last commit is not older than the baseline"
    return True, "clean baseline from %s, file not committed since" % time.strftime(
        "%Y-%m-%dT%H:%M:%S", time.localtime(begun))


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
    return {
        "verdict": report.get("verdict"),
        "exit_code": code,
        "path_is_mine": any(_same_path(d.get("path"), rel)
                            for d in report.get("dirty_overlap_mine") or []),
        "provenance_available": report.get("provenance_available"),
        "provenance_partial": report.get("provenance_partial"),
        "foreign": [{"path": d.get("path"), "owners": d.get("owners"),
                     "stale_owners": d.get("stale_owners")}
                    for d in report.get("dirty_overlap_foreign") or []],
        "competing_claims": [{"slug": c.get("slug"), "session_id": c.get("session_id")}
                             for c in report.get("competing_claims") or []],
    }


def _find_commit(repo, nonce):
    """The commit whose message carries this run's nonce, or None."""
    rc, out, _ = _git(repo, "log", "-1", "--format=%H%x00%B", "HEAD")
    if rc == 0 and nonce in out:
        return out.split("\0", 1)[0].strip()
    rc, out, _ = _git(repo, "log", "--all", "--fixed-strings", "--grep=" + nonce, "--format=%H")
    shas = out.split() if rc == 0 else []
    return shas[0] if len(shas) == 1 else None


def _tree_entry(repo, rev, rel):
    """(mode, blob) of rel in rev's tree, or None."""
    rc, out, _ = _git(repo, "ls-tree", "-z", rev, "--", rel)
    meta = out.split("\0")[0].split("\t", 1)[0].split() if rc == 0 else []
    return (meta[0], meta[2]) if len(meta) == 3 else None


def _index_blob(repo, rel):
    rc, out, _ = _git(repo, "ls-files", "-s", "--", rel)
    meta = out.split("\t", 1)[0].split() if rc == 0 else []
    return meta[1] if len(meta) == 3 else None


def _set_index_entry(repo, rel, entry):
    """Point rel's index entry at entry=(mode, blob), touching no other entry. None on
    success, else git's complaint (retried briefly: the shared index is often locked)."""
    err = ""
    for attempt in range(3):
        if attempt:
            time.sleep(1)
        rc, _, err = _git(repo, "update-index", "--cacheinfo", "%s,%s,%s" % (entry[0], entry[1], rel))
        if rc == 0:
            return None
    return err.strip() or "update-index failed"


def _looks_like_ours(repo, sha, parent, rel, blob):
    """True when `sha` is a single-parent commit on `parent` that changed only rel, to blob --
    this run's commit with its trailer stripped (a commit-msg hook), as far as git can tell."""
    rc, out, _ = _git(repo, "rev-list", "--parents", "-n", "1", sha)
    if rc != 0 or out.split()[1:] != [parent]:
        return False
    rc, out, _ = _git(repo, "diff-tree", "-z", "--no-commit-id", "--name-only", "-r", sha)
    return rc == 0 and [p for p in out.split("\0") if p] == [rel] and _blob_at(repo, sha, rel) == blob


def verify_commit(repo, sha, rel, expected_blob, branch=None, parent_blob=None):
    """Problems with `sha` as the landing of `rel` at `expected_blob` ([] == verified).
    `branch` is a full ref (refs/heads/x) or a bare branch name."""
    problems = []
    rc, out, err = _git(repo, "rev-list", "--parents", "-n", "1", sha)
    if rc != 0:
        return ["cannot read commit %s: %s" % (sha, err.strip())]
    parents = out.split()[1:]
    if len(parents) != 1:
        problems.append("commit %s has %d parents, expected 1" % (sha, len(parents)))
    elif parent_blob is not None and _blob_at(repo, parents[0], rel) != parent_blob:
        problems.append("commit %s's parent is not the HEAD that was checked (its %s differs)"
                        % (sha, rel))
    rc, out, _ = _git(repo, "diff-tree", "-z", "--no-commit-id", "--name-only", "-r", sha)
    paths = sorted(p for p in out.split("\0") if p) if rc == 0 else None
    if paths != [rel]:
        problems.append("commit %s touched %s, expected only %s"
                        % (sha, paths if paths is not None else "(unreadable)", rel))
    blob = _blob_at(repo, sha, rel)
    if blob != expected_blob:
        problems.append("commit %s stored blob %s for %s, expected %s"
                        % (sha, blob, rel, expected_blob))
    if branch:
        ref = branch if branch.startswith("refs/") else "refs/heads/" + branch
        rc, _, _ = _git(repo, "merge-base", "--is-ancestor", sha, ref)
        if rc != 0:
            problems.append("commit %s is not on branch %s" % (sha, _short(ref)))
    return problems


def _undo(repo, ref, sha, rel):
    """Take back this run's own just-made commit: move `ref` back to the commit's parent only
    if it still points at the commit (compare-and-swap, so a commit someone made on top is never
    discarded), then restore rel's index entry. None on success."""
    parent = (_git(repo, "rev-parse", "--verify", "-q", sha + "^1")[1] or "").strip()
    if not parent:
        return "cannot read the parent of %s" % sha
    rc, _, err = _git(repo, "update-ref", "-m", "commit-own-edit: take back an unverified commit",
                      ref, parent, sha)
    if rc != 0:
        return "could not move %s back to %s: %s" % (_short(ref), parent[:10], err.strip())
    entry = _tree_entry(repo, parent, rel)
    err = _set_index_entry(repo, rel, entry) if entry else "its entry could not be read"
    if err:
        return ("%s is back at %s, but restoring %s's index entry failed (%s); run: "
                "git reset -q -- %s" % (_short(ref), parent[:10], rel, err, rel))
    return None


def _result(mode, session):
    return {"status": None, "exit_code": None, "mode": mode, "path": None, "repo": None,
            "session": session or None, "branch": None, "commit": None, "reason": ""}


def begin(path, session=None, sessions_dir=None):
    """Record the baseline the landing needs: did `path` match HEAD before this run touched it?
    Idempotent: a second call keeps the first record while HEAD's blob of the path is unchanged,
    so the run's own edits can never turn a clean baseline dirty."""
    session = _session(session)
    res = _result("begin", session)

    def done(status, reason):
        res.update(status=status, exit_code=EXIT[status], reason=reason)
        return res

    if not session:
        return done("ERROR", "no session id (pass --session or set CLAUDE_CODE_SESSION_ID)")
    loc, err = _locate(path)
    if err:
        return done("ERROR", err)
    repo, rel = loc["repo"], loc["rel"]
    res.update(repo=repo, path=rel)
    ref = _branch_ref(repo)
    if not ref:
        return done("ERROR", "HEAD is detached; the landing would refuse anyway")
    branch = res["branch"] = _short(ref)
    head_blob = _blob_at(repo, "HEAD", rel)
    target = _baseline_path(sessions_dir or _default_sessions_dir(), session, repo, rel)
    res["baseline_file"] = target
    prior = _load_baseline(target)
    if prior and prior.get("base_blob") == head_blob:
        if prior.get("clean"):
            return done("BEGUN", "baseline already recorded for this run: the file matched HEAD")
        return done("DIRTY_AT_BEGIN", "baseline already recorded for this run: the file had "
                                      "uncommitted content before this run touched it")
    wt_rc = _git(repo, "diff", "--quiet", "HEAD", "--", rel)[0]
    ix_rc = _git(repo, "diff", "--cached", "--quiet", "--", rel)[0]
    if wt_rc not in (0, 1) or ix_rc not in (0, 1) or not head_blob:
        return done("ERROR", "could not compare the file with HEAD")
    clean = wt_rc == 0 and ix_rc == 0
    rec = {"version": 1, "repo": repo, "rel": rel, "branch": branch, "base_blob": head_blob,
           "clean": clean, "begun_at": time.time()}
    try:
        os.makedirs(os.path.dirname(target), exist_ok=True)
        tmp = target + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(rec, fh)
        os.replace(tmp, target)
    except OSError as exc:
        return done("ERROR", "could not record the baseline: %s" % exc)
    if clean:
        return done("BEGUN", "baseline recorded: the file matches HEAD")
    return done("DIRTY_AT_BEGIN", "the file already has uncommitted content this run did not "
                                  "write; the landing will leave it for the weekly sweep")


def land(path, message, session=None, sessions_dir=None, claims_dir=None,
         transcripts_dir=None, lock_attempts=3, lock_wait=3.0, quiet_seconds=QUIET_SECONDS,
         quiet_max_wait=QUIET_MAX_WAIT, preflight=None):
    """Commit `path` if this session provably owns all of its uncommitted content. Returns the
    result dict printed as RESULT_JSON."""
    session = _session(session)
    message = (message or "").strip()
    res = _result("land", session)
    res["preflight"] = None
    res["baseline"] = {"used": False, "reason": ""}

    def done(status, reason):
        res.update(status=status, exit_code=EXIT[status], reason=reason)
        return res

    if not session:
        return done("ERROR", "no session id (pass --session or set CLAUDE_CODE_SESSION_ID); "
                             "ownership cannot be proven without one")
    if not message:
        return done("ERROR", "empty commit message")
    if not (isinstance(quiet_seconds, (int, float)) and 0 <= quiet_seconds < float("inf")):
        return done("ERROR", "quiet_seconds must be a finite number >= 0")
    loc, err = _locate(path)
    if err:
        return done("ERROR", err)
    full, repo, rel = loc["full"], loc["repo"], loc["rel"]
    res.update(repo=repo, path=rel)

    ref = _branch_ref(repo)
    if not ref:
        return done("LEFT_FOR_SWEEP", "HEAD is detached; a commit here would sit on no branch")
    branch = res["branch"] = _short(ref)
    rc, out, err = _git(repo, "rev-parse", "--absolute-git-dir")
    if rc != 0 or not out.strip():
        return done("ERROR", "cannot locate the git dir: %s" % err.strip())
    git_dir = out.strip()
    busy = _busy(git_dir)
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

    sessions_dir = sessions_dir or _default_sessions_dir()
    rec = _load_baseline(_baseline_path(sessions_dir, session, repo, rel))
    if rec is not None and not rec.get("clean") and rec.get("rel") == rel:
        return done("LEFT_FOR_SWEEP", "the file already had uncommitted content before this run "
                                      "touched it (--begin found it dirty)")
    quiet_sig = _wait_quiet(full, quiet_seconds, quiet_max_wait)
    if quiet_sig is None:
        return done("LEFT_FOR_SWEEP", "the file is still being written (no %gs quiet period "
                                      "within %gs)" % (quiet_seconds, quiet_max_wait))

    head0 = _head(repo)
    head_blob0 = _blob_at(repo, head0, rel) if head0 else None
    checked = _staged_blob(repo, rel, head0) if head_blob0 else None
    if not checked:
        return done("ERROR", "could not compute the blob git would store for %s" % rel)
    excused, why = _baseline_excuses_stale(rec, repo, rel, head_blob0)
    res["baseline"] = {"used": excused, "reason": why}
    extra = []
    for flag, value in (("--sessions-dir", sessions_dir), ("--claims-dir", claims_dir),
                        ("--session-transcripts-dir", transcripts_dir)):
        if value:
            extra += [flag, value]
    if excused:
        extra += ["--accept-stale", full]
    code, report, detail = (preflight or run_preflight)(repo, full, session, extra)
    if report is None:
        return done("ERROR", "preflight returned no verdict (exit %s): %s" % (code, detail))
    summary = _preflight_summary(code, report, rel)
    res["preflight"] = summary
    if summary["provenance_available"] is not True or summary["provenance_partial"]:
        return done("LEFT_FOR_SWEEP", "provenance is not fully readable (%s session file(s) "
                                      "unreadable), so ownership is unknown"
                    % summary["provenance_partial"])
    if code != 0 or summary["verdict"] != "CLEAR" or not summary["path_is_mine"]:
        return done("LEFT_FOR_SWEEP", "preflight %s: this session is not provably the file's "
                                      "only live recorded owner" % summary["verdict"])

    nonce = uuid.uuid4().hex
    trailers = "Commit-Own-Edit-Session: %s\nCommit-Own-Edit-Run: %s" % (session, nonce)
    attempts = max(1, lock_attempts)
    sha, last, commit_rc = None, "", None
    for attempt in range(attempts):
        if attempt:
            time.sleep(lock_wait)
        now_ref = _branch_ref(repo)
        if now_ref != ref:
            return done("LEFT_FOR_SWEEP", "the branch changed during the landing (now %s)"
                        % (_short(now_ref) or "detached HEAD"))
        busy = _busy(git_dir)
        if busy:
            return done("LEFT_FOR_SWEEP", "repository is mid-operation (%s)" % ", ".join(busy))
        head_now = _head(repo)
        if not head_now or _blob_at(repo, head_now, rel) != head_blob0:
            return done("LEFT_FOR_SWEEP", "the file was committed by someone else during the "
                                          "landing")
        rc, _, err = _git(repo, "diff", "--cached", "--quiet", "--", rel)
        if rc == 1:
            return done("LEFT_FOR_SWEEP", "a version of the file was staged in the shared index "
                                          "during the landing; it is not this run's to replace")
        if rc != 0:
            return done("ERROR", "git diff --cached failed: %s" % err.strip())
        if _sig(full) != quiet_sig or _staged_blob(repo, rel, head_now) != checked:
            return done("LEFT_FOR_SWEEP", "the file changed while it was being checked")
        rc, out, err = _git(repo, "commit", "--only", "--quiet", "-m", message,
                            "-m", COMMIT_BODY, "-m", trailers, "--", rel,
                            timeout=COMMIT_TIMEOUT)
        sha = _find_commit(repo, nonce)  # also settles a timed-out commit either way
        if sha:
            commit_rc = rc
            break
        now = _head(repo)
        if now and now != head_now and _looks_like_ours(repo, now, head_now, rel, checked):
            res["commit"] = now
            return done("COMMITTED_UNVERIFIED", "HEAD moved to %s, a commit of exactly this file "
                                                "and content, but it lacks this run's trailer (a "
                                                "commit-msg hook?), so it is not provably this "
                                                "run's; check it by hand" % now[:10])
        last = (err or out).strip()
        if _LOCK_RE.search(last):
            continue
        if _git(repo, "diff", "--quiet", "HEAD", "--", rel)[0] == 0:
            return done("NOTHING_TO_COMMIT", "the file matched HEAD by the time git read it "
                                             "(it changed during the landing)")
        return done("ERROR", "git commit failed (exit %s): %s" % (rc, last[:500]))
    if not sha:
        return done("LEFT_FOR_SWEEP", "the repository stayed locked by another git process "
                                      "(%d attempts): %s" % (attempts, last[:300]))

    res["commit"] = sha
    problems = verify_commit(repo, sha, rel, checked, branch=ref, parent_blob=head_blob0)
    if problems:
        undo_error = _undo(repo, ref, sha, rel)
        if undo_error is None:
            return done("UNDONE", "commit %s failed verification and was taken back: %s"
                        % (sha[:10], "; ".join(problems)))
        return done("COMMITTED_UNVERIFIED", "%s; taking it back failed: %s"
                    % ("; ".join(problems), undo_error))
    note = ""
    if commit_rc != 0:
        # git can create the commit and still fail to write the new index (exit 128), leaving
        # the path staged as a revert of the commit -- which the next bare commit would land.
        # Repair only that exact shape; a third version there is someone else's to keep.
        ix = _index_blob(repo, rel)
        if ix == head_blob0:
            repair_error = _set_index_entry(repo, rel, _tree_entry(repo, sha, rel))
            if repair_error:
                return done("COMMITTED_UNVERIFIED", "commit %s landed, but the index still "
                                                    "stages %s's old version (%s); run: git reset "
                                                    "-q -- %s" % (sha[:10], rel, repair_error, rel))
            res["index_repaired"] = True
            note = "; git exited %s after creating it, index entry repaired" % commit_rc
        elif ix != checked:
            return done("COMMITTED_UNVERIFIED", "commit %s landed, but git exited %s and the index "
                                                "now holds another version of %s; check it by hand"
                        % (sha[:10], commit_rc, rel))
        else:
            note = "; git exited %s after creating it" % commit_rc
    res["worktree_matches_commit"] = _git(repo, "diff", "--quiet", sha, "--", rel)[0] == 0
    return done("COMMITTED", "committed %s as %s on %s%s" % (rel, sha[:10], branch, note))


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        """A usage error still ends with RESULT_JSON (exit 2), like every other outcome."""
        self.print_usage(sys.stderr)
        r = {"status": "ERROR", "exit_code": EXIT["ERROR"], "mode": None, "path": None,
             "reason": "usage: %s" % message}
        print("COMMIT-OWN-EDIT ERROR -- usage: %s" % message)
        print("RESULT_JSON=" + json.dumps(r))
        sys.exit(EXIT["ERROR"])


def _parse_args(argv):
    ap = _Parser(
        description="Commit ONE memory file this session edited, only when "
                    "preflight-shared-checkout.py proves this session is its only live recorded "
                    "owner; otherwise leave it for ora-memory-commit-sweep. Run once with "
                    "--begin before the first edit, then without it after the last. See the "
                    "module docstring.")
    ap.add_argument("--begin", action="store_true",
                    help="record the baseline (before the run's first edit of --path)")
    ap.add_argument("--path", required=True, help="the memory file this run edits")
    ap.add_argument("--message", default=None,
                    help="commit subject (required without --begin), e.g. 'memory(open-items): "
                         "ora-appsec-sweep 2026-11-11 files OI-397..OI-399'")
    ap.add_argument("--session", default=None,
                    help="this run's session id (default: $CLAUDE_CODE_SESSION_ID)")
    ap.add_argument("--sessions-dir", default=None,
                    help="provenance sessions dir (default: ~/.claude/hooks/sessions)")
    ap.add_argument("--claims-dir", default=None, help="preflight pass-through (tests)")
    ap.add_argument("--transcripts-dir", default=None, help="preflight pass-through (tests)")
    ap.add_argument("--quiet-seconds", type=float, default=QUIET_SECONDS,
                    help="quiet period before the check, >= 0 (default %(default)s; tests use 0)")
    args = ap.parse_args(argv)
    if not args.begin and not (args.message or "").strip():
        ap.error("--message is required unless --begin is given")
    return args


def main(argv=None):
    args = _parse_args(sys.argv[1:] if argv is None else argv)  # -h exits here, before any git
    try:
        if args.begin:
            r = begin(args.path, session=args.session, sessions_dir=args.sessions_dir)
        else:
            r = land(args.path, args.message, session=args.session,
                     sessions_dir=args.sessions_dir, claims_dir=args.claims_dir,
                     transcripts_dir=args.transcripts_dir, quiet_seconds=args.quiet_seconds)
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
