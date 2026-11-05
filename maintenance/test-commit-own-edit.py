#!/usr/bin/env python3
"""Tests for commit-own-edit.py -- the end-of-run landing step for unattended memory writers.

Run: python test-commit-own-edit.py   (exit 0 = all pass)

Every test builds a throwaway repo that mirrors the live layout (a `projects/<project>/memory/`
tree, `* text=auto`, core.autocrlf=true, CRLF files on disk), plus fixture provenance
(touched-files.txt per session), claims and transcripts dirs. It then drives the REAL
preflight-shared-checkout.py through land(). Only the content-changes-mid-check test injects
behaviour, and it does so by wrapping the real preflight.
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

    def land(self, rel=TRACKER, session=MINE, message="memory(open-items): fixture run", **kw):
        kw.setdefault("sessions_dir", self.sessions)
        kw.setdefault("claims_dir", self.claims)
        kw.setdefault("transcripts_dir", self.transcripts)
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


# --- the case it exists for ------------------------------------------------------------

@_fixture_test
def test_commits_sole_owner_edit_and_only_that_path(f):
    before = f.head()
    f.append(TRACKER, "| OI-002 | second |\n")
    f.touch(MINE, TRACKER)
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
def test_nothing_to_commit_when_file_matches_head(f):
    before = f.head()
    r = f.land()
    _status(r, "NOTHING_TO_COMMIT", 0)
    assert f.head() == before


@_fixture_test
def test_other_staged_paths_stay_staged_and_uncommitted(f):
    f.append(NOTES, "staged by another session\n")
    git(f.repo, "add", "--", NOTES)
    f.append(TRACKER, "| OI-002 | second |\n")
    f.touch(MINE, TRACKER)
    r = f.land()
    _status(r, "COMMITTED", 0)
    assert git(f.repo, "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD").split() == [TRACKER]
    assert changed(f.repo, staged=True) == [NOTES]


@_fixture_test
def test_own_claim_does_not_block(f):
    f.append(TRACKER, "| OI-002 | second |\n")
    f.touch(MINE, TRACKER)
    f.claim(MINE, TRACKER, slug="sched-open-items-tracker")
    _status(f.land(), "COMMITTED", 0)


# --- every shape where the content is not provably this session's alone ----------------

def _assert_left(f, r, before, reason):
    """LEFT_FOR_SWEEP for the stated reason (so a test cannot pass via a different guard),
    with no commit made and the edit still in the working tree."""
    _status(r, "LEFT_FOR_SWEEP", 1)
    assert reason in r["reason"], "expected reason containing %r, got %r" % (reason, r["reason"])
    assert f.head() == before, "a commit was made"
    assert TRACKER in changed(f.repo), "the edit was lost"


@_fixture_test
def test_leaves_file_when_another_session_also_touched_it(f):
    before = f.head()
    f.append(TRACKER, "| OI-002 | second |\n")
    f.touch(MINE, TRACKER)
    f.touch(OTHER, TRACKER)
    r = f.land()
    _assert_left(f, r, before, "preflight CONTESTED")
    assert sorted(r["preflight"]["foreign"][0]["owners"]) == sorted([OTHER, MINE]), r


@_fixture_test
def test_leaves_file_with_no_recorded_owner(f):
    before = f.head()
    f.append(TRACKER, "| OI-002 | written by a script, not the Edit tool |\n")
    r = f.land()
    _assert_left(f, r, before, "preflight CONTESTED")
    assert r["preflight"]["foreign"][0]["owners"] == [], r


@_fixture_test
def test_leaves_file_when_another_sessions_claim_covers_it(f):
    before = f.head()
    f.append(TRACKER, "| OI-002 | second |\n")
    f.touch(MINE, TRACKER)
    f.claim(OTHER, TRACKER)
    r = f.land()
    _assert_left(f, r, before, "preflight CONTESTED")
    assert [c["session_id"] for c in r["preflight"]["competing_claims"]] == [OTHER], r


@_fixture_test
def test_leaves_file_when_a_foreign_touch_is_only_stale(f):
    # OTHER touched before the last commit: a partial commit may have left its hunk dirty,
    # so the preflight's stale-only rule must not be overridden (no --accept-stale).
    before = f.head()
    f.touch(OTHER, TRACKER, when=BEFORE_PAST)
    f.append(TRACKER, "| OI-002 | second |\n")
    f.touch(MINE, TRACKER)
    r = f.land()
    _assert_left(f, r, before, "preflight CONTESTED")
    assert r["preflight"]["foreign"][0]["stale_owners"] == [OTHER], r


@_fixture_test
def test_leaves_file_when_a_version_of_it_is_staged(f):
    before = f.head()
    f.append(TRACKER, "| OI-002 | staged by someone |\n")
    git(f.repo, "add", "--", TRACKER)
    staged_blob = git(f.repo, "rev-parse", ":" + TRACKER).strip()
    f.append(TRACKER, "| OI-003 | working tree only |\n")
    f.touch(MINE, TRACKER)
    _assert_left(f, f.land(), before, "staged in the shared index")
    assert git(f.repo, "rev-parse", ":" + TRACKER).strip() == staged_blob, "staged version changed"


@_fixture_test
def test_leaves_file_when_it_changes_during_the_check(f):
    before = f.head()
    f.append(TRACKER, "| OI-002 | second |\n")
    f.touch(MINE, TRACKER)

    def racing_preflight(*args, **kwargs):
        out = coe.run_preflight(*args, **kwargs)
        f.append(TRACKER, "| OI-999 | concurrent unrecorded write |\n")
        return out

    _assert_left(f, f.land(preflight=racing_preflight), before, "changed while")


@_fixture_test
def test_leaves_file_while_the_index_is_locked(f):
    before = f.head()
    f.append(TRACKER, "| OI-002 | second |\n")
    f.touch(MINE, TRACKER)
    lock = os.path.join(f.repo, ".git", "index.lock")
    open(lock, "w").close()
    try:
        _assert_left(f, f.land(lock_attempts=2, lock_wait=0), before, "index stayed locked")
        assert os.path.exists(lock), "another process's lock was removed"
    finally:
        os.remove(lock)


@_fixture_test
def test_leaves_file_on_detached_head(f):
    git(f.repo, "checkout", "-q", "--detach")
    before = f.head()
    f.append(TRACKER, "| OI-002 | second |\n")
    f.touch(MINE, TRACKER)
    _assert_left(f, f.land(), before, "detached")


@_fixture_test
def test_leaves_file_mid_merge(f):
    before = f.head()
    with open(os.path.join(f.repo, ".git", "MERGE_HEAD"), "w") as fh:
        fh.write(before + "\n")
    f.append(TRACKER, "| OI-002 | second |\n")
    f.touch(MINE, TRACKER)
    _assert_left(f, f.land(), before, "mid-operation")


@_fixture_test
def test_requires_positive_proof_not_just_an_exit_0(f):
    # CLEAR with the path absent from dirty_overlap_mine (a spelling mismatch, say) proves
    # nothing; STALE_UNTRACKED_KNOWN_BLOB also exits 0. Neither may commit.
    before = f.head()
    f.append(TRACKER, "| OI-002 | second |\n")
    f.touch(MINE, TRACKER)
    base = {"dirty_overlap_foreign": [], "competing_claims": []}
    for verdict, mine in (("CLEAR", []), ("STALE_UNTRACKED_KNOWN_BLOB", [{"path": TRACKER}])):
        fake = dict(base, verdict=verdict, dirty_overlap_mine=mine)
        r = f.land(preflight=lambda *a, **k: (0, fake, ""))
        _assert_left(f, r, before, "preflight %s" % verdict)


@_fixture_test
def test_errors_when_the_preflight_returns_no_verdict(f):
    before = f.head()
    f.append(TRACKER, "| OI-002 | second |\n")
    f.touch(MINE, TRACKER)
    r = f.land(preflight=lambda *a, **k: (1, None, "Traceback: boom"))
    _status(r, "ERROR", 2)
    assert "boom" in r["reason"], r
    assert f.head() == before


# --- refusals: nothing it should ever commit ---------------------------------------------

@_fixture_test
def test_refuses_path_outside_memory(f):
    before = f.head()
    f.append(OUTSIDE, "print('y')\n")
    f.touch(MINE, OUTSIDE)
    _status(f.land(rel=OUTSIDE), "ERROR", 2)
    assert f.head() == before


@_fixture_test
def test_refuses_untracked_file(f):
    before = f.head()
    f.write(MEM + "new-file.md", "new\n")
    f.touch(MINE, MEM + "new-file.md")
    _status(f.land(rel=MEM + "new-file.md"), "ERROR", 2)
    assert f.head() == before


@_fixture_test
def test_refuses_without_a_session_id(f):
    before = f.head()
    f.append(TRACKER, "| OI-002 | second |\n")
    f.touch(MINE, TRACKER)
    _status(f.land(session=""), "ERROR", 2)
    assert f.head() == before


@_fixture_test
def test_refuses_an_empty_message(f):
    before = f.head()
    f.append(TRACKER, "| OI-002 | second |\n")
    f.touch(MINE, TRACKER)
    _status(f.land(message="   "), "ERROR", 2)
    assert f.head() == before


@_fixture_test
def test_refuses_a_missing_path(f):
    _status(f.land(rel=MEM + "does-not-exist.md"), "ERROR", 2)


@_fixture_test
def test_resolves_a_lowercased_path_spelling(f):
    # touched-files.txt and some callers spell paths lowercased; git's index keeps the real case.
    if os.name != "nt":
        return
    f.append(TRACKER, "| OI-002 | second |\n")
    f.touch(MINE, TRACKER)
    r = coe.land(f.p(TRACKER).lower(), "memory(open-items): lowercased", session=MINE,
                 sessions_dir=f.sessions, claims_dir=f.claims, transcripts_dir=f.transcripts)
    _status(r, "COMMITTED", 0)
    assert r["path"] == TRACKER, r


# --- post-commit verification -------------------------------------------------------------

@_fixture_test
def test_verify_commit_flags_extra_paths_and_wrong_content(f):
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
    last = proc.stdout.strip().splitlines()[-1]
    assert last.startswith("RESULT_JSON="), proc.stdout
    return json.loads(last[len("RESULT_JSON="):])


@_fixture_test
def test_cli_reports_result_json_last_with_matching_exit_code(f):
    f.append(TRACKER, "| OI-002 | second |\n")
    f.touch(MINE, TRACKER)
    common = ["--session", MINE, "--sessions-dir", f.sessions, "--claims-dir", f.claims,
              "--transcripts-dir", f.transcripts]
    p = f.cli("--path", f.p(TRACKER), "--message", "memory(open-items): cli", *common)
    assert p.returncode == 0, (p.returncode, p.stdout, p.stderr)
    assert _result_json(p)["status"] == "COMMITTED"

    p = f.cli("--path", f.p(TRACKER), "--message", "memory(open-items): cli", *common)
    assert p.returncode == 0, (p.returncode, p.stdout, p.stderr)
    assert _result_json(p)["status"] == "NOTHING_TO_COMMIT"

    f.append(TRACKER, "| OI-003 | third |\n")
    f.touch(MINE, TRACKER)
    f.touch(OTHER, TRACKER)
    p = f.cli("--path", f.p(TRACKER), "--message", "memory(open-items): cli", *common)
    assert p.returncode == 1, (p.returncode, p.stdout, p.stderr)
    assert _result_json(p)["status"] == "LEFT_FOR_SWEEP"


@_fixture_test
def test_cli_help_touches_nothing(f):
    # memory-commit-sweep.py once ran its real sweep on `--help` (2026-08-16).
    before = f.head()
    f.append(TRACKER, "| OI-002 | second |\n")
    f.touch(MINE, TRACKER)
    p = f.cli("--help")
    assert p.returncode == 0, (p.returncode, p.stderr)
    assert "usage" in p.stdout.lower(), p.stdout
    assert f.head() == before
    assert TRACKER in changed(f.repo)


TESTS = [
    test_commits_sole_owner_edit_and_only_that_path,
    test_nothing_to_commit_when_file_matches_head,
    test_other_staged_paths_stay_staged_and_uncommitted,
    test_own_claim_does_not_block,
    test_leaves_file_when_another_session_also_touched_it,
    test_leaves_file_with_no_recorded_owner,
    test_leaves_file_when_another_sessions_claim_covers_it,
    test_leaves_file_when_a_foreign_touch_is_only_stale,
    test_leaves_file_when_a_version_of_it_is_staged,
    test_leaves_file_when_it_changes_during_the_check,
    test_leaves_file_while_the_index_is_locked,
    test_leaves_file_on_detached_head,
    test_leaves_file_mid_merge,
    test_requires_positive_proof_not_just_an_exit_0,
    test_errors_when_the_preflight_returns_no_verdict,
    test_refuses_path_outside_memory,
    test_refuses_untracked_file,
    test_refuses_without_a_session_id,
    test_refuses_an_empty_message,
    test_refuses_a_missing_path,
    test_resolves_a_lowercased_path_spelling,
    test_verify_commit_flags_extra_paths_and_wrong_content,
    test_memory_prefix_matches_land_live_commits,
    test_cli_reports_result_json_last_with_matching_exit_code,
    test_cli_help_touches_nothing,
]


if __name__ == "__main__":
    failed = []
    for t in TESTS:
        try:
            t()
        except Exception:
            failed.append(t.__name__)
            print("FAIL %s" % t.__name__)
            traceback.print_exc(limit=3)
    print("\ncommit-own-edit tests: %d/%d passed" % (len(TESTS) - len(failed), len(TESTS)))
    sys.exit(1 if failed else 0)
