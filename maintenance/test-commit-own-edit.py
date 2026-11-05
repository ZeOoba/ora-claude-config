#!/usr/bin/env python3
"""Tests for commit-own-edit.py -- the end-of-run landing step for unattended memory writers.

Run: python test-commit-own-edit.py   (exit 0 = all pass)

Every test builds a throwaway repo that mirrors the live layout (a `projects/<project>/memory/`
tree, `* text=auto`, core.autocrlf=true, CRLF files on disk), plus fixture provenance
(touched-files.txt per session), claims and transcripts dirs. It then drives the REAL
preflight-shared-checkout.py through land(). Tests that need a race inject it by wrapping the
real preflight or the module's own git runner; nothing else is mocked.
"""
import importlib.util
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import threading
import time
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "commit-own-edit.py")
_spec = importlib.util.spec_from_file_location("commit_own_edit", SCRIPT)
coe = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(coe)

MINE = "aaaaaaaa-1111-4111-8111-111111111111"
OTHER = "bbbbbbbb-2222-4222-8222-222222222222"
MEM = "projects/C--Users-Owner-OneDrive---Oxford-Capital-Partners/memory/"
TRACKER = MEM + "open-items-tracker.md"
NOTES = MEM + "notes.md"
OUTSIDE = "maintenance/script.py"
# Fixture commits are dated here, so a touch recorded at "now" is newer than the path's last
# commit (a LIVE owner); a touch dated before it is STALE (see preflight _split_stale).
PAST = "2026-01-01T12:00:00"
BEFORE_PAST = time.mktime(time.strptime("2025-12-01T12:00:00", "%Y-%m-%dT%H:%M:%S"))

_GIT_ENV = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR",
            "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_PREFIX")


def _env(dated=False):
    env = {k: v for k, v in os.environ.items() if k not in _GIT_ENV}
    if dated:
        env["GIT_AUTHOR_DATE"] = env["GIT_COMMITTER_DATE"] = PAST
    return env


def git(repo, *args, dated=False):
    p = subprocess.run(["git"] + list(args), cwd=repo, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=_env(dated))
    if p.returncode != 0:
        raise RuntimeError("git %s failed: %s" % (" ".join(args), p.stderr))
    return p.stdout


def changed(repo, staged=False):
    args = ["diff", "--name-only"] + (["--cached"] if staged else [])
    return git(repo, *args).split()


def _rmtree(path):
    def _retry(func, p, _exc):
        os.chmod(p, stat.S_IWRITE)  # git objects are read-only on Windows
        func(p)
    if sys.version_info >= (3, 12):
        shutil.rmtree(path, onexc=_retry)
    else:
        shutil.rmtree(path, onerror=_retry)


class Fixture:
    def __init__(self):
        self.root = os.path.realpath(tempfile.mkdtemp(prefix="coe-test-"))
        self.repo = os.path.join(self.root, "repo")
        self.sessions = os.path.join(self.root, "sessions")
        self.claims = os.path.join(self.root, "claims")
        self.transcripts = os.path.join(self.root, "projects")
        for d in (self.repo, self.sessions, self.claims, self.transcripts):
            os.makedirs(d)
        git(self.repo, "init", "-q", "-b", "main")
        git(self.repo, "config", "user.name", "Fixture")
        git(self.repo, "config", "user.email", "fixture@example.invalid")
        git(self.repo, "config", "core.autocrlf", "true")
        git(self.repo, "config", "commit.gpgsign", "false")
        self.write(".gitattributes", "* text=auto\n")
        self.write(TRACKER, "# Open items\n\n| id | item |\n|----|------|\n| OI-001 | first |\n")
        self.write(NOTES, "notes\n")
        self.write(OUTSIDE, "print('x')\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "seed", dated=True)

    def p(self, rel):
        return os.path.join(self.repo, *rel.split("/"))

    def write(self, rel, text):
        full = self.p(rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8", newline="\r\n") as fh:  # live files are CRLF
            fh.write(text)

    def append(self, rel, text):
        with open(self.p(rel), "a", encoding="utf-8", newline="\r\n") as fh:
            fh.write(text)

    def touch(self, session, rel, when=None):
        """Record a touch the way commit-provenance-recorder.py does."""
        d = os.path.join(self.sessions, session)
        os.makedirs(d, exist_ok=True)
        key = os.path.normcase(os.path.realpath(self.p(rel)))
        with open(os.path.join(d, "touched-files.txt"), "a", encoding="utf-8") as fh:
            fh.write("%s\t%.6f\n" % (key, time.time() if when is None else when))

    def claim(self, session, rel, slug="open-items-tracker"):
        """A live claim in claim_work.py's on-disk shape."""
        rec = {"title": slug, "session_id": session, "description": "fixture claim",
               "claimed_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
               "paths": [os.path.realpath(self.p(rel))]}
        with open(os.path.join(self.claims, slug + ".json"), "w", encoding="utf-8") as fh:
            json.dump(rec, fh)

    def head(self):
        return git(self.repo, "rev-parse", "HEAD").strip()

    def snap(self, rel=TRACKER):
        """Everything a refusal must leave exactly as it was."""
        with open(self.p(rel), "rb") as fh:
            body = fh.read()
        return {"head": self.head(), "index": git(self.repo, "ls-files", "-s"), "body": body,
                "rel": rel}

    def begin(self, rel=TRACKER, session=MINE):
        return coe.begin(self.p(rel), session=session, sessions_dir=self.sessions)

    def land(self, rel=TRACKER, session=MINE, message="memory(open-items): fixture run", **kw):
        kw.setdefault("sessions_dir", self.sessions)
        kw.setdefault("claims_dir", self.claims)
        kw.setdefault("transcripts_dir", self.transcripts)
        kw.setdefault("quiet_seconds", 0)
        return coe.land(self.p(rel), message, session=session, **kw)

    def cli(self, *args):
        cmd = [sys.executable, SCRIPT] + list(args)
        return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                              errors="replace", env=_env())

    def close(self):
        _rmtree(self.root)


def _fixture_test(fn):
    """Give each test a fresh fixture and always clean it up."""
    def run():
        f = Fixture()
        try:
            fn(f)
        finally:
            f.close()
        print("PASS %s" % fn.__name__)
    run.__name__ = fn.__name__
    return run


def _status(r, status, code):
    assert r["status"] == status, "expected %s, got %r" % (status, r)
    assert r["exit_code"] == code, "expected exit %d, got %r" % (code, r)


def _assert_left(f, r, snap, reason, body_unchanged=True):
    """LEFT_FOR_SWEEP for the stated reason (so a test cannot pass through a different guard),
    with HEAD and the whole index exactly as they were and the edit still in the working tree."""
    _status(r, "LEFT_FOR_SWEEP", 1)
    assert reason in r["reason"], "expected reason containing %r, got %r" % (reason, r["reason"])
    assert f.head() == snap["head"], "a commit was made"
    assert git(f.repo, "ls-files", "-s") == snap["index"], "the index changed"
    assert snap["rel"] in changed(f.repo), "the edit was lost"
    if body_unchanged:
        with open(f.p(snap["rel"]), "rb") as fh:
            assert fh.read() == snap["body"], "the working-tree file changed"


def _own_edit(f, rel=TRACKER, text="| OI-002 | own |\n"):
    f.append(rel, text)
    f.touch(MINE, rel)


# --- the case it exists for ------------------------------------------------------------

@_fixture_test
def test_commits_sole_owner_edit_and_only_that_path(f):
    before = f.head()
    _own_edit(f, text="| OI-002 | second |\n")
    f.append(NOTES, "another session's line\n")  # unrelated dirt must stay dirty
    r = f.land(message="memory(open-items): fixture files OI-002")
    _status(r, "COMMITTED", 0)
    head = f.head()
    assert head != before and r["commit"] == head, r
    assert git(f.repo, "rev-parse", "HEAD^").strip() == before
    assert git(f.repo, "diff-tree", "--no-commit-id", "--name-only", "-r", head).split() == [TRACKER]
    msg = git(f.repo, "log", "-1", "--format=%B")
    assert msg.startswith("memory(open-items): fixture files OI-002"), msg
    assert MINE in msg, msg
    assert changed(f.repo) == [NOTES], changed(f.repo)
    assert changed(f.repo, staged=True) == []
    assert r["branch"] == "main", r
    assert r["path"] == TRACKER, r


@_fixture_test
def test_lands_despite_stale_foreign_touches_after_a_clean_begin(f):
    # The production shape: the live tracker always carries stale owners (sessions that touched
    # it before its last commit), and the preflight contests a stale-only file. A clean
    # baseline taken before this run's first edit proves none of their content is uncommitted.
    f.touch(OTHER, TRACKER, when=BEFORE_PAST)
    _status(f.begin(), "BEGUN", 0)
    _own_edit(f)
    r = f.land()
    _status(r, "COMMITTED", 0)
    assert r["baseline"]["used"] is True, r
    assert git(f.repo, "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD").split() == [TRACKER]


@_fixture_test
def test_nothing_to_commit_when_file_matches_head(f):
    before = f.head()
    r = f.land()
    _status(r, "NOTHING_TO_COMMIT", 0)
    assert f.head() == before


@_fixture_test
def test_other_staged_paths_stay_staged_and_uncommitted(f):
    f.append(NOTES, "staged by another session\n")
    git(f.repo, "add", "--", NOTES)
    _own_edit(f)
    r = f.land()
    _status(r, "COMMITTED", 0)
    assert git(f.repo, "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD").split() == [TRACKER]
    assert changed(f.repo, staged=True) == [NOTES]


@_fixture_test
def test_own_claim_does_not_block(f):
    _own_edit(f)
    f.claim(MINE, TRACKER, slug="sched-open-items-tracker")
    _status(f.land(), "COMMITTED", 0)


@_fixture_test
def test_crlf_stored_blob_lands_without_a_false_alarm(f):
    # Three live memory files are stored as CRLF blobs. `git add` keeps CRLF for a path whose
    # indexed blob already has it, where hash-object would normalise to LF, so the expected
    # blob must come from git add itself, or every such landing reads as unverified.
    rel = MEM + "rules.md"
    with open(f.p(rel), "wb") as fh:
        fh.write(b"# Rules\r\n\r\n- one\r\n")
    blob = git(f.repo, "hash-object", "-w", "--no-filters", "--", rel).strip()
    git(f.repo, "update-index", "--add", "--cacheinfo", "100644,%s,%s" % (blob, rel))
    git(f.repo, "commit", "-q", "-m", "a CRLF blob", dated=True)
    assert changed(f.repo) == [], "fixture: a CRLF blob over a CRLF file should read clean"
    _own_edit(f, rel=rel, text="- two\n")
    r = f.land(rel=rel)
    _status(r, "COMMITTED", 0)
    stored = subprocess.run(["git", "cat-file", "-p", "HEAD:" + rel], cwd=f.repo,
                            capture_output=True, env=_env()).stdout
    assert stored.count(b"\r\n") == stored.count(b"\n") == 4, stored
    assert git(f.repo, "diff", "--numstat", "HEAD~1", "HEAD").split()[:2] == ["1", "0"]


# --- every shape where the content is not provably this session's alone ----------------

@_fixture_test
def test_leaves_file_when_another_session_also_touched_it(f):
    _own_edit(f)
    f.touch(OTHER, TRACKER)
    s = f.snap()
    r = f.land()
    _assert_left(f, r, s, "preflight CONTESTED")
    assert sorted(r["preflight"]["foreign"][0]["owners"]) == sorted([OTHER, MINE]), r


@_fixture_test
def test_leaves_file_with_no_recorded_owner(f):
    f.append(TRACKER, "| OI-002 | written by a script, not the Edit tool |\n")
    s = f.snap()
    r = f.land()
    _assert_left(f, r, s, "preflight CONTESTED")
    assert r["preflight"]["foreign"][0]["owners"] == [], r


@_fixture_test
def test_leaves_file_when_another_sessions_claim_covers_it(f):
    _own_edit(f)
    f.claim(OTHER, TRACKER)
    s = f.snap()
    r = f.land()
    _assert_left(f, r, s, "preflight CONTESTED")
    assert [c["session_id"] for c in r["preflight"]["competing_claims"]] == [OTHER], r


@_fixture_test
def test_leaves_file_when_a_foreign_touch_is_only_stale_and_there_is_no_begin(f):
    # Without a baseline nothing proves the stale owner's content was committed (a partial
    # commit can leave its hunk dirty), so the preflight's stale-only rule stands.
    f.touch(OTHER, TRACKER, when=BEFORE_PAST)
    _own_edit(f)
    s = f.snap()
    r = f.land()
    _assert_left(f, r, s, "preflight CONTESTED")
    assert r["preflight"]["foreign"][0]["stale_owners"] == [OTHER], r
    assert r["baseline"]["used"] is False, r


@_fixture_test
def test_begin_on_a_dirty_file_makes_land_refuse(f):
    # Foreign content written with Bash (no provenance) before this run started: the preflight
    # alone would read the file as this session's. The dirty baseline is the proof otherwise.
    f.append(TRACKER, "| OI-666 | someone's uncommitted script write |\n")
    _status(f.begin(), "DIRTY_AT_BEGIN", 1)
    _own_edit(f)
    s = f.snap()
    _assert_left(f, f.land(), s, "before this run")


@_fixture_test
def test_baseline_is_void_once_the_path_is_committed_after_begin(f):
    f.touch(OTHER, TRACKER, when=BEFORE_PAST)
    _status(f.begin(), "BEGUN", 0)
    _own_edit(f, text="| OI-002 | own, then committed by someone else |\n")
    git(f.repo, "add", "--", TRACKER)
    # Dated in the past, so only the blob comparison (not the commit-time one) can void it.
    git(f.repo, "commit", "-q", "-m", "someone lands the tracker", dated=True)
    _own_edit(f, text="| OI-003 | own |\n")
    s = f.snap()
    r = f.land()
    _assert_left(f, r, s, "preflight CONTESTED")
    assert r["baseline"]["used"] is False, r


@_fixture_test
def test_baseline_does_not_excuse_a_live_foreign_owner(f):
    _status(f.begin(), "BEGUN", 0)
    _own_edit(f)
    f.touch(OTHER, TRACKER)
    s = f.snap()
    _assert_left(f, f.land(), s, "preflight CONTESTED")


@_fixture_test
def test_baseline_does_not_excuse_a_foreign_claim(f):
    _status(f.begin(), "BEGUN", 0)
    _own_edit(f)
    f.claim(OTHER, TRACKER)
    s = f.snap()
    _assert_left(f, f.land(), s, "preflight CONTESTED")


@_fixture_test
def test_late_foreign_touch_is_seen_after_the_quiet_window(f):
    # A foreign Edit-tool write whose touch record lands a moment after the write (recorder lag
    # measured live: p99 4.7 s). The quiet window holds the preflight until the record exists.
    _own_edit(f)
    f.append(TRACKER, "| OI-888 | foreign Edit-tool row |\n")
    s = f.snap()
    timer = threading.Timer(1.5, f.touch, args=(OTHER, TRACKER))
    timer.start()
    try:
        r = f.land(quiet_seconds=4)
    finally:
        timer.join()
    _assert_left(f, r, s, "preflight CONTESTED")


@_fixture_test
def test_gives_up_when_the_file_never_goes_quiet(f):
    _own_edit(f)
    s = f.snap()
    stop = threading.Event()

    def keep_touching():
        while not stop.is_set():
            os.utime(f.p(TRACKER), None)
            time.sleep(0.2)

    th = threading.Thread(target=keep_touching)
    th.start()
    try:
        r = f.land(quiet_seconds=1, quiet_max_wait=2)
    finally:
        stop.set()
        th.join()
    _assert_left(f, r, s, "still being written")


@_fixture_test
def test_leaves_file_when_provenance_is_partial(f):
    # A session's touched-files.txt that exists but cannot be read leaves ownership unknown.
    os.makedirs(os.path.join(f.sessions, OTHER, "touched-files.txt"))
    _own_edit(f)
    s = f.snap()
    _assert_left(f, f.land(), s, "provenance")


@_fixture_test
def test_leaves_file_when_a_version_of_it_is_staged(f):
    f.append(TRACKER, "| OI-002 | staged by someone |\n")
    git(f.repo, "add", "--", TRACKER)
    _own_edit(f, text="| OI-003 | working tree only |\n")
    s = f.snap()
    _assert_left(f, f.land(), s, "staged in the shared index")


@_fixture_test
def test_leaves_file_when_it_changes_during_the_check(f):
    _own_edit(f)
    s = f.snap()

    def racing_preflight(*args, **kwargs):
        out = coe.run_preflight(*args, **kwargs)
        f.append(TRACKER, "| OI-999 | concurrent unrecorded write |\n")
        return out

    _assert_left(f, f.land(preflight=racing_preflight), s, "changed while", body_unchanged=False)


@_fixture_test
def test_leaves_file_when_the_branch_changes_during_the_check(f):
    before = f.head()
    _own_edit(f)

    def switching_preflight(*args, **kwargs):
        out = coe.run_preflight(*args, **kwargs)
        git(f.repo, "checkout", "-q", "-b", "elsewhere")
        return out

    r = f.land(preflight=switching_preflight)
    _status(r, "LEFT_FOR_SWEEP", 1)
    assert "branch" in r["reason"], r
    assert git(f.repo, "rev-parse", "main").strip() == before
    assert git(f.repo, "rev-parse", "elsewhere").strip() == before


@_fixture_test
def test_leaves_file_when_the_path_is_committed_during_the_check(f):
    # Another session commits its own version of the file straight from the index while this
    # run is checking. Committing our working tree on top would silently revert their commit.
    _own_edit(f)

    def landing_preflight(*args, **kwargs):
        out = coe.run_preflight(*args, **kwargs)
        theirs = git(f.repo, "show", "HEAD:" + TRACKER) + "| OI-555 | theirs, index only |\n"
        blob = subprocess.run(["git", "hash-object", "-w", "--stdin"], input=theirs.encode(),
                              cwd=f.repo, capture_output=True, env=_env()).stdout.decode().strip()
        git(f.repo, "update-index", "--cacheinfo", "100644,%s,%s" % (blob, TRACKER))
        git(f.repo, "commit", "-q", "-m", "someone else commits the tracker meanwhile")
        return out

    r = f.land(preflight=landing_preflight)
    _status(r, "LEFT_FOR_SWEEP", 1)
    assert "committed" in r["reason"], r
    assert "OI-555" in git(f.repo, "show", "HEAD:" + TRACKER), "their commit was reverted"


@_fixture_test
def test_leaves_file_while_the_index_is_locked(f):
    _own_edit(f)
    s = f.snap()
    lock = os.path.join(f.repo, ".git", "index.lock")
    open(lock, "w").close()
    try:
        _assert_left(f, f.land(lock_attempts=2, lock_wait=0), s, "locked")
        assert os.path.exists(lock), "another process's lock was removed"
    finally:
        os.remove(lock)


@_fixture_test
def test_branch_ref_lock_is_contention_not_an_error(f):
    _own_edit(f)
    s = f.snap()
    lock = os.path.join(f.repo, ".git", "refs", "heads", "main.lock")
    open(lock, "w").close()
    try:
        _assert_left(f, f.land(lock_attempts=2, lock_wait=0), s, "locked")
        assert os.path.exists(lock), "another process's lock was removed"
    finally:
        os.remove(lock)


@_fixture_test
def test_leaves_file_on_detached_head(f):
    git(f.repo, "checkout", "-q", "--detach")
    _own_edit(f)
    s = f.snap()
    _assert_left(f, f.land(), s, "detached")


@_fixture_test
def test_leaves_file_mid_merge_cherry_pick_revert_or_rebase(f):
    _own_edit(f)
    s = f.snap()
    gd = os.path.join(f.repo, ".git")
    for marker, is_dir in (("MERGE_HEAD", False), ("CHERRY_PICK_HEAD", False),
                           ("REVERT_HEAD", False), ("rebase-merge", True), ("rebase-apply", True)):
        p = os.path.join(gd, marker)
        if is_dir:
            os.makedirs(p)
        else:
            with open(p, "w") as fh:
                fh.write(s["head"] + "\n")
        try:
            r = f.land()
            _assert_left(f, r, s, "mid-operation")
            assert r["preflight"] is None, "checks ran in a repository that is mid-operation"
        finally:
            shutil.rmtree(p) if is_dir else os.remove(p)


@_fixture_test
def test_leaves_file_when_a_merge_starts_during_the_check(f):
    _own_edit(f)
    s = f.snap()

    def merging_preflight(*args, **kwargs):
        out = coe.run_preflight(*args, **kwargs)
        with open(os.path.join(f.repo, ".git", "MERGE_HEAD"), "w") as fh:
            fh.write(s["head"] + "\n")
        return out

    try:
        _assert_left(f, f.land(preflight=merging_preflight), s, "mid-operation")
    finally:
        os.remove(os.path.join(f.repo, ".git", "MERGE_HEAD"))


@_fixture_test
def test_baseline_is_void_when_the_path_was_committed_and_reverted_after_begin(f):
    # HEAD's blob is back to the baseline's, but a commit after --begin means a foreign touch
    # made after the baseline can read as stale while its content is still uncommitted.
    _status(f.begin(), "BEGUN", 0)
    time.sleep(2)  # integer commit seconds must land after the foreign touch below
    f.append(TRACKER, "| OI-444 | foreign, still uncommitted |\n")
    f.touch(OTHER, TRACKER, when=time.time() - 1.0)
    base = git(f.repo, "rev-parse", "HEAD:" + TRACKER).strip()
    other = subprocess.run(["git", "hash-object", "-w", "--stdin"],
                           input=(git(f.repo, "show", "HEAD:" + TRACKER) + "x\n").encode(),
                           cwd=f.repo, capture_output=True, env=_env()).stdout.decode().strip()
    for blob, msg in ((other, "someone commits a change"), (base, "and reverts it")):
        git(f.repo, "update-index", "--cacheinfo", "100644,%s,%s" % (blob, TRACKER))
        git(f.repo, "commit", "-q", "-m", msg)
    _own_edit(f)
    s = f.snap()
    r = f.land()
    _assert_left(f, r, s, "preflight CONTESTED")
    assert r["baseline"]["used"] is False, r


@_fixture_test
def test_requires_positive_proof_not_just_an_exit_0(f):
    # CLEAR with the path absent from dirty_overlap_mine (a spelling mismatch, say) proves
    # nothing; STALE_UNTRACKED_KNOWN_BLOB also exits 0; a non-zero exit never counts.
    _own_edit(f)
    s = f.snap()
    base = {"dirty_overlap_foreign": [], "competing_claims": [], "provenance_available": True,
            "provenance_partial": 0}
    for code, verdict, mine in ((0, "CLEAR", []),
                                (0, "STALE_UNTRACKED_KNOWN_BLOB", [{"path": TRACKER}]),
                                (1, "CLEAR", [{"path": TRACKER}])):
        fake = dict(base, verdict=verdict, dirty_overlap_mine=mine)
        r = f.land(preflight=lambda *a, **k: (code, fake, ""))
        _assert_left(f, r, s, "preflight %s" % verdict)


@_fixture_test
def test_errors_when_the_preflight_returns_no_verdict(f):
    before = f.head()
    _own_edit(f)
    r = f.land(preflight=lambda *a, **k: (1, None, "Traceback: boom"))
    _status(r, "ERROR", 2)
    assert "boom" in r["reason"], r
    assert f.head() == before


# --- the commit window ----------------------------------------------------------------------

@_fixture_test
def test_undoes_a_commit_that_fails_verification(f):
    # A write that lands between the last check and git's own read of the file. The commit
    # cannot be prevented, so it must be taken back: branch, index entry, nothing lost.
    before = f.head()
    old_entry = git(f.repo, "ls-files", "-s", "--", TRACKER)
    _own_edit(f)
    real_git = coe._git

    def racing_git(repo, *args, **kwargs):
        if "commit" in args:
            f.append(TRACKER, "| OI-777 | foreign write in the commit window |\n")
        return real_git(repo, *args, **kwargs)

    coe._git = racing_git
    try:
        r = f.land()
    finally:
        coe._git = real_git
    _status(r, "UNDONE", 3)
    assert f.head() == before, "the unverified commit is still on the branch"
    assert git(f.repo, "ls-files", "-s", "--", TRACKER) == old_entry, "index entry not restored"
    with open(f.p(TRACKER), encoding="utf-8") as fh:
        body = fh.read()
    assert "OI-002" in body and "OI-777" in body, "working-tree content was lost"


@_fixture_test
def test_undoes_a_commit_made_on_top_of_someone_elses_commit_of_the_path(f):
    # Someone commits their own version of the file in the instant before git commit runs.
    # Our commit would silently revert theirs; verification must catch the parent and undo.
    _own_edit(f)
    real_git = coe._git
    theirs = {}

    def racing_git(repo, *args, **kwargs):
        if "commit" in args and not theirs:
            body = git(f.repo, "show", "HEAD:" + TRACKER) + "| OI-555 | theirs, index only |\n"
            blob = subprocess.run(["git", "hash-object", "-w", "--stdin"], input=body.encode(),
                                  cwd=f.repo, capture_output=True, env=_env()).stdout.decode().strip()
            git(f.repo, "update-index", "--cacheinfo", "100644,%s,%s" % (blob, TRACKER))
            git(f.repo, "commit", "-q", "-m", "theirs")
            theirs["sha"] = f.head()
        return real_git(repo, *args, **kwargs)

    coe._git = racing_git
    try:
        r = f.land()
    finally:
        coe._git = real_git
    _status(r, "UNDONE", 3)
    assert f.head() == theirs["sha"], "their commit is no longer the branch tip"
    assert "OI-555" in git(f.repo, "show", "HEAD:" + TRACKER)
    assert changed(f.repo, staged=True) == [], "index entry not restored to the branch tip"


@_fixture_test
def test_begin_twice_keeps_the_clean_baseline(f):
    # A second --begin after the run's own edits must not turn the clean baseline dirty.
    f.touch(OTHER, TRACKER, when=BEFORE_PAST)
    _status(f.begin(), "BEGUN", 0)
    _own_edit(f)
    _status(f.begin(), "BEGUN", 0)
    _status(f.land(), "COMMITTED", 0)


@_fixture_test
def test_reverted_file_in_the_commit_window_is_not_an_error(f):
    before = f.head()
    _own_edit(f)
    real_git = coe._git

    def reverting_git(repo, *args, **kwargs):
        if "commit" in args:
            real_git(repo, "checkout", "--", TRACKER)
        return real_git(repo, *args, **kwargs)

    coe._git = reverting_git
    try:
        r = f.land()
    finally:
        coe._git = real_git
    _status(r, "NOTHING_TO_COMMIT", 0)
    assert f.head() == before


@_fixture_test
def test_failing_commit_hook_is_an_error_not_a_lock(f):
    hook = os.path.join(f.repo, ".git", "hooks", "pre-commit")
    with open(hook, "w", newline="\n") as fh:
        fh.write("#!/bin/sh\necho blocked-by-test-hook >&2\nexit 1\n")
    os.chmod(hook, 0o755)
    before = f.head()
    _own_edit(f)
    r = f.land(lock_attempts=3, lock_wait=0)
    _status(r, "ERROR", 2)
    assert "blocked-by-test-hook" in r["reason"], r
    assert f.head() == before


@_fixture_test
def test_ignores_an_inherited_git_environment(f):
    # A parent git process (a hook) can export GIT_DIR / GIT_INDEX_FILE.
    _own_edit(f)
    bogus = os.path.join(f.root, "bogus-index")
    saved = {k: os.environ.get(k) for k in ("GIT_INDEX_FILE", "GIT_DIR")}
    os.environ["GIT_INDEX_FILE"] = bogus
    os.environ["GIT_DIR"] = os.path.join(f.root, "no-such-git-dir")
    try:
        r = f.land()
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    _status(r, "COMMITTED", 0)
    assert not os.path.exists(bogus)


@_fixture_test
def test_bracketed_file_name_is_matched_literally(f):
    odd, twin = MEM + "x[1].md", MEM + "x1.md"
    f.write(odd, "odd\n")
    f.write(twin, "twin\n")
    git(f.repo, "add", "--", odd, twin)
    git(f.repo, "commit", "-q", "-m", "two look-alike names", dated=True)
    f.append(twin, "twin's own change\n")
    _own_edit(f, rel=odd, text="odd's own change\n")
    r = f.land(rel=odd)
    _status(r, "COMMITTED", 0)
    assert git(f.repo, "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD").split() == [odd]
    assert twin in changed(f.repo)


# --- REFUTE pass 2 reproductions -------------------------------------------------------------

@_fixture_test
def test_write_right_after_the_quiet_window_is_caught(f):
    # Repro A: a foreign Edit-tool write lands just after the quiet window was judged, and its
    # touch record arrives after the preflight scan. The file must still read as unquiet.
    _own_edit(f)
    time.sleep(1.1)
    s = f.snap()
    real_wait = coe._wait_quiet
    # The touch record "arrives" only after the landing is over (the timer is cancelled), so the
    # preflight cannot catch this write: only the quiet-state check can.
    timer = threading.Timer(600, f.touch, args=(OTHER, TRACKER))

    def gap(*args, **kwargs):
        out = real_wait(*args, **kwargs)
        f.append(TRACKER, "| OI-321 | foreign write in the gap |\n")
        timer.start()
        return out

    coe._wait_quiet = gap
    try:
        r = f.land(quiet_seconds=1)
    finally:
        coe._wait_quiet = real_wait
        timer.cancel()
    _assert_left(f, r, s, "changed while", body_unchanged=False)


@_fixture_test
def test_index_write_failure_after_the_commit_is_repaired(f):
    # Repro B: git creates the commit but fails to write the new index (exit 128), leaving the
    # path's index entry at the old blob -- a staged revert of the run's rows.
    _own_edit(f)
    old = git(f.repo, "ls-files", "-s", "--", TRACKER).split("\t", 1)[0].split()
    real_git = coe._git

    def failing_index_git(repo, *args, **kwargs):
        if "commit" in args:
            real_git(repo, *args, **kwargs)
            real_git(repo, "update-index", "--cacheinfo", "%s,%s,%s" % (old[0], old[1], TRACKER))
            return 128, "", "fatal: unable to write new index file"
        return real_git(repo, *args, **kwargs)

    coe._git = failing_index_git
    try:
        r = f.land()
    finally:
        coe._git = real_git
    _status(r, "COMMITTED", 0)
    assert changed(f.repo, staged=True) == [], "the index still stages a revert of the commit"
    assert "OI-002" in git(f.repo, "show", "HEAD:" + TRACKER)


@_fixture_test
def test_commit_without_the_run_trailer_is_unverified_not_nothing(f):
    # Repro C: a commit-msg hook strips the trailer, so the commit cannot be found by it.
    hook = os.path.join(f.repo, ".git", "hooks", "commit-msg")
    with open(hook, "w", newline="\n") as fh:
        fh.write("#!/bin/sh\nsed -i '/^Commit-Own-Edit-/d' \"$1\"\n")
    os.chmod(hook, 0o755)
    before = f.head()
    _own_edit(f)
    r = f.land()
    assert f.head() != before, "fixture: the hook should not block the commit"
    _status(r, "COMMITTED_UNVERIFIED", 3)


@_fixture_test
def test_version_staged_after_the_check_is_not_overwritten(f):
    # Repro D: another session stages its own version of the path after the preflight.
    _own_edit(f)
    staged = {}

    def staging_preflight(*args, **kwargs):
        out = coe.run_preflight(*args, **kwargs)
        body = git(f.repo, "show", "HEAD:" + TRACKER) + "| OI-654 | staged by someone |\n"
        blob = subprocess.run(["git", "hash-object", "-w", "--stdin"], input=body.encode(),
                              cwd=f.repo, capture_output=True, env=_env()).stdout.decode().strip()
        git(f.repo, "update-index", "--cacheinfo", "100644,%s,%s" % (blob, TRACKER))
        staged["blob"] = blob
        return out

    before = f.head()
    r = f.land(preflight=staging_preflight)
    _status(r, "LEFT_FOR_SWEEP", 1)
    assert "staged" in r["reason"], r
    assert f.head() == before
    assert git(f.repo, "rev-parse", ":" + TRACKER).strip() == staged["blob"], "their staged blob was replaced"


@_fixture_test
def test_undo_never_discards_a_commit_someone_made_on_top(f):
    # Repro E: verification fails AND another session commits on top before the take-back.
    # The take-back must refuse (compare-and-swap) rather than move the branch over theirs.
    _own_edit(f)
    real_git = coe._git
    theirs = {}

    def racing_git(repo, *args, **kwargs):
        if "commit" in args and not theirs:
            f.append(TRACKER, "| OI-777 | foreign write in the commit window |\n")
            out = real_git(repo, *args, **kwargs)
            git(f.repo, "commit", "-q", "--allow-empty", "-m", "theirs, on top")
            theirs["sha"] = f.head()
            return out
        return real_git(repo, *args, **kwargs)

    coe._git = racing_git
    try:
        r = f.land()
    finally:
        coe._git = real_git
    _status(r, "COMMITTED_UNVERIFIED", 3)
    assert f.head() == theirs["sha"], "their commit was discarded"


@_fixture_test
def test_commit_found_even_when_someone_commits_on_top_at_once(f):
    # Another session commits right after ours: HEAD's message lacks our trailer, so the commit
    # must be found by searching for it, and it is still a verified landing.
    _own_edit(f)
    real_git = coe._git
    done = {}

    def racing_git(repo, *args, **kwargs):
        if "commit" in args and not done:
            out = real_git(repo, *args, **kwargs)
            git(f.repo, "commit", "-q", "--allow-empty", "-m", "theirs, on top")
            done["x"] = True
            return out
        return real_git(repo, *args, **kwargs)

    coe._git = racing_git
    try:
        r = f.land()
    finally:
        coe._git = real_git
    _status(r, "COMMITTED", 0)
    assert r["commit"] == git(f.repo, "rev-parse", "HEAD^").strip(), r


@_fixture_test
def test_a_tag_named_like_the_branch_does_not_break_verification(f):
    git(f.repo, "tag", "main")
    _own_edit(f)
    r = f.land()
    _status(r, "COMMITTED", 0)
    assert r["branch"] == "main", r


@_fixture_test
def test_unparseable_preflight_output_is_an_error(f):
    _own_edit(f)
    bogus = os.path.join(f.root, "bogus-preflight.py")
    with open(bogus, "w", encoding="utf-8") as fh:
        fh.write("print('this is not json')\n")
    real = coe.PREFLIGHT
    coe.PREFLIGHT = bogus
    try:
        r = f.land()
    finally:
        coe.PREFLIGHT = real
    _status(r, "ERROR", 2)
    assert "no verdict" in r["reason"], r


@_fixture_test
def test_main_turns_an_unexpected_exception_into_result_json(f):
    import contextlib, io
    real = coe.land

    def boom(*a, **k):
        raise RuntimeError("unexpected boom")

    coe.land = boom
    out = io.StringIO()
    try:
        with contextlib.redirect_stdout(out):
            code = coe.main(["--path", f.p(TRACKER), "--message", "m", "--session", MINE])
    finally:
        coe.land = real
    last = out.getvalue().strip().splitlines()[-1]
    assert code == 2 and last.startswith("RESULT_JSON="), (code, out.getvalue())
    assert json.loads(last[len("RESULT_JSON="):])["status"] == "ERROR"


@_fixture_test
def test_content_change_that_keeps_mtime_and_size_is_caught(f):
    # The (mtime, size) signature misses a same-length rewrite whose mtime is put back; the
    # blob comparison right before the commit must not.
    _own_edit(f, text="| OI-002 | own |\n")
    s = f.snap()

    def sneaky_preflight(*args, **kwargs):
        out = coe.run_preflight(*args, **kwargs)
        p = f.p(TRACKER)
        st = os.stat(p)
        with open(p, "rb") as fh:
            body = fh.read()
        with open(p, "wb") as fh:
            fh.write(body.replace(b"OI-002", b"OI-009"))
        os.utime(p, ns=(st.st_atime_ns, st.st_mtime_ns))
        return out

    _assert_left(f, f.land(preflight=sneaky_preflight), s, "changed while", body_unchanged=False)


@_fixture_test
def test_land_rejects_a_negative_or_nan_quiet_period(f):
    _own_edit(f)
    for bad in (-1, float("nan")):
        _status(f.land(quiet_seconds=bad), "ERROR", 2)


def test_worst_case_runtime_fits_the_spec_timeout():
    # A landing that outlives its Bash timeout prints no RESULT_JSON while possibly committing
    # later. The spec must grant at least the helper's true worst case (every hang guard hit).
    worst = (coe.QUIET_MAX_WAIT + coe.PREFLIGHT_TIMEOUT + 3 * coe.COMMIT_TIMEOUT
             + 2 * 3.0 + 60)  # + lock waits + a minute of ordinary git calls
    spec = os.path.join(HERE, os.pardir, "scheduled-tasks", "ora-appsec-sweep", "SKILL.md")
    with open(spec, encoding="utf-8") as fh:
        m = re.search(r"(\d+) ms timeout", fh.read())
    assert m, "spec step 7c no longer states a timeout"
    assert worst * 1000 <= int(m.group(1)), (worst, m.group(1))
    print("PASS test_worst_case_runtime_fits_the_spec_timeout")


@_fixture_test
def test_trailerless_commit_under_someone_elses_commit_is_unverified(f):
    # Repro A2 (pass 3): a hook strips the trailer AND another session commits on top at once.
    hook = os.path.join(f.repo, ".git", "hooks", "commit-msg")
    with open(hook, "w", newline="\n") as fh:
        fh.write("#!/bin/sh\nsed -i '/^Commit-Own-Edit-/d' \"$1\"\n")
    os.chmod(hook, 0o755)
    _own_edit(f)
    real_git = coe._git

    def racing_git(repo, *args, **kwargs):
        if "commit" in args:
            out = real_git(repo, *args, **kwargs)
            git(f.repo, "commit", "-q", "--allow-empty", "--no-verify", "-m", "theirs, on top")
            return out
        return real_git(repo, *args, **kwargs)

    coe._git = racing_git
    try:
        r = f.land()
    finally:
        coe._git = real_git
    _status(r, "COMMITTED_UNVERIFIED", 3)


@_fixture_test
def test_someone_elses_identical_hand_landing_is_nothing_to_commit(f):
    # Repro D4 (pass 3): another session commits exactly our content just before our commit.
    _own_edit(f)
    real_git = coe._git

    def landing_git(repo, *args, **kwargs):
        if "commit" in args:
            git(f.repo, "commit", "-q", "-m", "hand-landed by someone", "--", TRACKER)
        return real_git(repo, *args, **kwargs)

    coe._git = landing_git
    try:
        r = f.land()
    finally:
        coe._git = real_git
    _status(r, "NOTHING_TO_COMMIT", 0)


@_fixture_test
def test_undo_keeps_a_version_someone_staged_meanwhile(f):
    # Repro C (pass 3): verification fails, and another session stages the path before the undo.
    _own_edit(f)
    real_git = coe._git
    staged = {}

    def racing_git(repo, *args, **kwargs):
        if "commit" in args:
            f.append(TRACKER, "| OI-777 | foreign write in the commit window |\n")
            out = real_git(repo, *args, **kwargs)
            body = git(f.repo, "show", "HEAD:" + TRACKER) + "| OI-888 | staged by someone |\n"
            blob = subprocess.run(["git", "hash-object", "-w", "--stdin"], input=body.encode(),
                                  cwd=f.repo, capture_output=True, env=_env()).stdout.decode().strip()
            git(f.repo, "update-index", "--cacheinfo", "100644,%s,%s" % (blob, TRACKER))
            staged["blob"] = blob
            return out
        return real_git(repo, *args, **kwargs)

    before = f.head()
    coe._git = racing_git
    try:
        r = f.land()
    finally:
        coe._git = real_git
    _status(r, "UNDONE", 3)
    assert f.head() == before
    assert git(f.repo, "rev-parse", ":" + TRACKER).strip() == staged["blob"], "their staged version was reset"


@_fixture_test
def test_undo_with_a_tag_named_like_the_branch_moves_the_branch(f):
    # The take-back must name the full ref: `update-ref main` would write .git/main.
    git(f.repo, "tag", "main")
    before = f.head()
    _own_edit(f)
    real_git = coe._git

    def racing_git(repo, *args, **kwargs):
        if "commit" in args:
            f.append(TRACKER, "| OI-777 | foreign write in the commit window |\n")
        return real_git(repo, *args, **kwargs)

    coe._git = racing_git
    try:
        r = f.land()
    finally:
        coe._git = real_git
    _status(r, "UNDONE", 3)
    assert git(f.repo, "rev-parse", "refs/heads/main").strip() == before
    assert not os.path.exists(os.path.join(f.repo, ".git", "main"))


@_fixture_test
def test_index_write_failure_with_a_third_version_staged_is_reported(f):
    # git exits 128 after committing and the index holds neither the old nor the new blob:
    # someone else's version, to be reported, never overwritten.
    _own_edit(f)
    real_git = coe._git
    third = {}

    def failing_index_git(repo, *args, **kwargs):
        if "commit" in args:
            real_git(repo, *args, **kwargs)
            body = git(f.repo, "show", "HEAD:" + TRACKER) + "| OI-999 | third version |\n"
            blob = subprocess.run(["git", "hash-object", "-w", "--stdin"], input=body.encode(),
                                  cwd=f.repo, capture_output=True, env=_env()).stdout.decode().strip()
            real_git(repo, "update-index", "--cacheinfo", "100644,%s,%s" % (blob, TRACKER))
            third["blob"] = blob
            return 128, "", "fatal: unable to write new index file"
        return real_git(repo, *args, **kwargs)

    coe._git = failing_index_git
    try:
        r = f.land()
    finally:
        coe._git = real_git
    _status(r, "COMMITTED_UNVERIFIED", 3)
    assert git(f.repo, "rev-parse", ":" + TRACKER).strip() == third["blob"]


@_fixture_test
def test_cli_rejects_a_negative_or_nan_quiet_period(f):
    for bad in ("-1", "nan"):
        p = f.cli("--path", f.p(TRACKER), "--message", "m", "--session", MINE,
                  "--quiet-seconds", bad)
        assert p.returncode == 2, (bad, p.returncode, p.stdout, p.stderr)
        assert _result_json(p)["status"] == "ERROR"


# --- refusals: nothing it should ever commit ---------------------------------------------

@_fixture_test
def test_refuses_path_outside_memory(f):
    before = f.head()
    f.append(OUTSIDE, "print('y')\n")
    f.touch(MINE, OUTSIDE)
    _status(f.land(rel=OUTSIDE), "ERROR", 2)
    _status(f.begin(rel=OUTSIDE), "ERROR", 2)
    assert f.head() == before


@_fixture_test
def test_refuses_untracked_file(f):
    before = f.head()
    f.write(MEM + "new-file.md", "new\n")
    f.touch(MINE, MEM + "new-file.md")
    _status(f.land(rel=MEM + "new-file.md"), "ERROR", 2)
    assert f.head() == before


@_fixture_test
def test_refuses_a_directory_or_a_deleted_file(f):
    # A directory holding exactly one tracked file must not land that file instead, and a
    # tracked file missing from disk must never be committed as a deletion.
    only = MEM + "sub/only.md"
    f.write(only, "only\n")
    git(f.repo, "add", "--", only)
    git(f.repo, "commit", "-q", "-m", "one file in a subdirectory", dated=True)
    before = f.head()
    _own_edit(f, rel=only, text="own\n")
    kw = dict(session=MINE, sessions_dir=f.sessions, claims_dir=f.claims,
              transcripts_dir=f.transcripts, quiet_seconds=0)
    _status(coe.land(os.path.dirname(f.p(only)), "m", **kw), "ERROR", 2)
    os.remove(f.p(TRACKER))
    f.touch(MINE, TRACKER)
    _status(coe.land(f.p(TRACKER), "m", **kw), "ERROR", 2)
    assert f.head() == before


@_fixture_test
def test_refuses_without_a_session_id(f):
    before = f.head()
    _own_edit(f)
    _status(f.land(session=""), "ERROR", 2)
    _status(f.begin(session=""), "ERROR", 2)
    assert f.head() == before


@_fixture_test
def test_refuses_an_empty_message(f):
    before = f.head()
    _own_edit(f)
    _status(f.land(message="   "), "ERROR", 2)
    assert f.head() == before


@_fixture_test
def test_refuses_a_missing_path(f):
    _status(f.land(rel=MEM + "does-not-exist.md"), "ERROR", 2)


@_fixture_test
def test_extended_length_path_is_refused_not_raised(f):
    if os.name != "nt":
        return
    r = coe.land("\\\\?\\" + f.p(TRACKER), "m", session=MINE, sessions_dir=f.sessions,
                 claims_dir=f.claims, transcripts_dir=f.transcripts, quiet_seconds=0)
    assert r["status"] in ("ERROR", "NOTHING_TO_COMMIT"), r


@_fixture_test
def test_resolves_a_lowercased_path_spelling(f):
    # touched-files.txt and some callers spell paths lowercased; git's index keeps the real case.
    if os.name != "nt":
        return
    _own_edit(f)
    r = coe.land(f.p(TRACKER).lower(), "memory(open-items): lowercased", session=MINE,
                 sessions_dir=f.sessions, claims_dir=f.claims, transcripts_dir=f.transcripts,
                 quiet_seconds=0)
    _status(r, "COMMITTED", 0)
    assert r["path"] == TRACKER, r


# --- post-commit verification -------------------------------------------------------------

@_fixture_test
def test_verify_commit_flags_extra_paths_wrong_content_and_wrong_branch(f):
    f.append(TRACKER, "| OI-002 | second |\n")
    f.append(NOTES, "swept in\n")
    git(f.repo, "add", "--", TRACKER, NOTES)
    git(f.repo, "commit", "-q", "-m", "two paths")
    sha = f.head()
    blob = git(f.repo, "rev-parse", sha + ":" + TRACKER).strip()
    problems = coe.verify_commit(f.repo, sha, TRACKER, blob)
    assert any(NOTES in p for p in problems), problems

    f.append(TRACKER, "| OI-003 | third |\n")
    git(f.repo, "add", "--", TRACKER)
    git(f.repo, "commit", "-q", "-m", "one path")
    sha = f.head()
    blob = git(f.repo, "rev-parse", sha + ":" + TRACKER).strip()
    assert coe.verify_commit(f.repo, sha, TRACKER, blob) == []
    assert coe.verify_commit(f.repo, sha, TRACKER, blob, branch="main") == []
    assert coe.verify_commit(f.repo, sha, TRACKER, "0" * 40) != []
    assert any("not on branch" in p
               for p in coe.verify_commit(f.repo, sha, TRACKER, blob, branch="elsewhere")), \
        "a commit off the checked branch passed verification"


@_fixture_test
def test_verify_commit_flags_a_merge_commit(f):
    git(f.repo, "checkout", "-q", "-b", "side")
    f.append(NOTES, "side\n")
    git(f.repo, "commit", "-q", "-am", "side")
    git(f.repo, "checkout", "-q", "main")
    f.append(TRACKER, "| OI-002 | main |\n")
    git(f.repo, "commit", "-q", "-am", "main")
    git(f.repo, "merge", "-q", "--no-ff", "-m", "merge side", "side")
    sha = f.head()
    blob = git(f.repo, "rev-parse", sha + ":" + TRACKER).strip()
    assert any("parents" in p for p in coe.verify_commit(f.repo, sha, TRACKER, blob))


def test_memory_prefix_matches_land_live_commits():
    # A commit outside land-live-commits.py's allowlist blocks the standing landing PR
    # (BLOCKED_NON_MEMORY), so the two must name the same tree.
    with open(os.path.join(HERE, "land-live-commits.py"), encoding="utf-8") as fh:
        m = re.search(r'^MEMORY = "([^"]+)"', fh.read(), re.M)
    assert m, "land-live-commits.py no longer defines MEMORY"
    assert coe.MEMORY_PREFIX == m.group(1), (coe.MEMORY_PREFIX, m.group(1))
    print("PASS test_memory_prefix_matches_land_live_commits")


# --- CLI contract -------------------------------------------------------------------------

def _result_json(proc):
    lines = proc.stdout.strip().splitlines()
    assert lines and lines[-1].startswith("RESULT_JSON="), (proc.stdout, proc.stderr)
    return json.loads(lines[-1][len("RESULT_JSON="):])


@_fixture_test
def test_cli_begin_then_land_with_matching_exit_codes(f):
    f.touch(OTHER, TRACKER, when=BEFORE_PAST)
    common = ["--session", MINE, "--sessions-dir", f.sessions]
    land_args = common + ["--claims-dir", f.claims, "--transcripts-dir", f.transcripts,
                          "--quiet-seconds", "0"]
    p = f.cli("--begin", "--path", f.p(TRACKER), *common)
    assert p.returncode == 0, (p.returncode, p.stdout, p.stderr)
    assert _result_json(p)["status"] == "BEGUN"

    _own_edit(f)
    p = f.cli("--path", f.p(TRACKER), "--message", "memory(open-items): cli", *land_args)
    assert p.returncode == 0, (p.returncode, p.stdout, p.stderr)
    assert _result_json(p)["status"] == "COMMITTED"

    p = f.cli("--path", f.p(TRACKER), "--message", "memory(open-items): cli", *land_args)
    assert p.returncode == 0, (p.returncode, p.stdout, p.stderr)
    assert _result_json(p)["status"] == "NOTHING_TO_COMMIT"

    _own_edit(f, text="| OI-003 | third |\n")
    f.touch(OTHER, TRACKER)
    p = f.cli("--path", f.p(TRACKER), "--message", "memory(open-items): cli", *land_args)
    assert p.returncode == 1, (p.returncode, p.stdout, p.stderr)
    assert _result_json(p)["status"] == "LEFT_FOR_SWEEP"


@_fixture_test
def test_cli_usage_errors_still_end_with_result_json(f):
    p = f.cli("--path", f.p(TRACKER))  # --message missing
    assert p.returncode == 2, (p.returncode, p.stdout, p.stderr)
    assert _result_json(p)["status"] == "ERROR"
    p = f.cli("--path", f.p(TRACKER), "--message", "m", "--sesion", MINE)  # typo'd flag
    assert p.returncode == 2, (p.returncode, p.stdout, p.stderr)
    assert _result_json(p)["status"] == "ERROR"


@_fixture_test
def test_cli_help_touches_nothing(f):
    # memory-commit-sweep.py once ran its real sweep on `--help` (2026-08-16).
    before = f.head()
    _own_edit(f)
    p = f.cli("--help")
    assert p.returncode == 0, (p.returncode, p.stderr)
    assert "usage" in p.stdout.lower(), p.stdout
    assert f.head() == before
    assert TRACKER in changed(f.repo)


TESTS = [
    test_commits_sole_owner_edit_and_only_that_path,
    test_lands_despite_stale_foreign_touches_after_a_clean_begin,
    test_nothing_to_commit_when_file_matches_head,
    test_other_staged_paths_stay_staged_and_uncommitted,
    test_own_claim_does_not_block,
    test_crlf_stored_blob_lands_without_a_false_alarm,
    test_leaves_file_when_another_session_also_touched_it,
    test_leaves_file_with_no_recorded_owner,
    test_leaves_file_when_another_sessions_claim_covers_it,
    test_leaves_file_when_a_foreign_touch_is_only_stale_and_there_is_no_begin,
    test_begin_on_a_dirty_file_makes_land_refuse,
    test_baseline_is_void_once_the_path_is_committed_after_begin,
    test_baseline_does_not_excuse_a_live_foreign_owner,
    test_baseline_does_not_excuse_a_foreign_claim,
    test_late_foreign_touch_is_seen_after_the_quiet_window,
    test_gives_up_when_the_file_never_goes_quiet,
    test_leaves_file_when_provenance_is_partial,
    test_leaves_file_when_a_version_of_it_is_staged,
    test_leaves_file_when_it_changes_during_the_check,
    test_leaves_file_when_the_branch_changes_during_the_check,
    test_leaves_file_when_the_path_is_committed_during_the_check,
    test_leaves_file_while_the_index_is_locked,
    test_branch_ref_lock_is_contention_not_an_error,
    test_leaves_file_on_detached_head,
    test_leaves_file_mid_merge_cherry_pick_revert_or_rebase,
    test_leaves_file_when_a_merge_starts_during_the_check,
    test_baseline_is_void_when_the_path_was_committed_and_reverted_after_begin,
    test_requires_positive_proof_not_just_an_exit_0,
    test_errors_when_the_preflight_returns_no_verdict,
    test_undoes_a_commit_that_fails_verification,
    test_undoes_a_commit_made_on_top_of_someone_elses_commit_of_the_path,
    test_begin_twice_keeps_the_clean_baseline,
    test_reverted_file_in_the_commit_window_is_not_an_error,
    test_failing_commit_hook_is_an_error_not_a_lock,
    test_ignores_an_inherited_git_environment,
    test_bracketed_file_name_is_matched_literally,
    test_write_right_after_the_quiet_window_is_caught,
    test_index_write_failure_after_the_commit_is_repaired,
    test_commit_without_the_run_trailer_is_unverified_not_nothing,
    test_version_staged_after_the_check_is_not_overwritten,
    test_undo_never_discards_a_commit_someone_made_on_top,
    test_commit_found_even_when_someone_commits_on_top_at_once,
    test_a_tag_named_like_the_branch_does_not_break_verification,
    test_unparseable_preflight_output_is_an_error,
    test_main_turns_an_unexpected_exception_into_result_json,
    test_content_change_that_keeps_mtime_and_size_is_caught,
    test_land_rejects_a_negative_or_nan_quiet_period,
    test_worst_case_runtime_fits_the_spec_timeout,
    test_trailerless_commit_under_someone_elses_commit_is_unverified,
    test_someone_elses_identical_hand_landing_is_nothing_to_commit,
    test_undo_keeps_a_version_someone_staged_meanwhile,
    test_undo_with_a_tag_named_like_the_branch_moves_the_branch,
    test_index_write_failure_with_a_third_version_staged_is_reported,
    test_cli_rejects_a_negative_or_nan_quiet_period,
    test_refuses_path_outside_memory,
    test_refuses_untracked_file,
    test_refuses_a_directory_or_a_deleted_file,
    test_refuses_without_a_session_id,
    test_refuses_an_empty_message,
    test_refuses_a_missing_path,
    test_extended_length_path_is_refused_not_raised,
    test_resolves_a_lowercased_path_spelling,
    test_verify_commit_flags_extra_paths_wrong_content_and_wrong_branch,
    test_verify_commit_flags_a_merge_commit,
    test_memory_prefix_matches_land_live_commits,
    test_cli_begin_then_land_with_matching_exit_codes,
    test_cli_usage_errors_still_end_with_result_json,
    test_cli_help_touches_nothing,
]


if __name__ == "__main__":
    only = set(sys.argv[1:])
    failed = []
    selected = [t for t in TESTS if not only or t.__name__ in only]
    for t in selected:
        try:
            t()
        except Exception:
            failed.append(t.__name__)
            print("FAIL %s" % t.__name__)
            traceback.print_exc(limit=3)
    print("\ncommit-own-edit tests: %d/%d passed" % (len(selected) - len(failed), len(selected)))
    sys.exit(1 if failed else 0)
