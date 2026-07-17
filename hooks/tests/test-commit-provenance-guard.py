"""Tests for commit-provenance-guard.py PreToolUse hook (matcher: Bash).

Run: python test-commit-provenance-guard.py
Stdlib only. ASCII-only. Self-contained (creates its own temp git repos).
Fail-open BY CONSTRUCTION: blocking needs TWO affirmative signals (a foreign
touched-set hit AND affirmative liveness). Anything else -> allow.
"""

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # hooks/
HOOK = os.path.join(HERE, "commit-provenance-guard.py")

# Load the guard module directly by file path so tests can call its
# functions (is_git_commit, candidate_paths, repo_root) in-process.
_spec = importlib.util.spec_from_file_location("commit_provenance_guard", HOOK)
_cpg = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_cpg)
is_git_commit = _cpg.is_git_commit
candidate_paths = _cpg.candidate_paths
repo_root = _cpg.repo_root


def run_hook(cmd, cwd, sessions_dir, session_id="me", fleet_state=None, ttl_h=None):
    env = dict(os.environ)
    env["COMMIT_PROVENANCE_SESSIONS_DIR"] = sessions_dir
    if ttl_h is not None:
        env["COMMIT_PROVENANCE_TTL_H"] = str(ttl_h)
    env["ORA_FLEET_STATE"] = fleet_state or "C:/does/not/exist_cpg.json"
    payload = json.dumps({
        "session_id": session_id, "cwd": cwd,
        "tool_input": {"command": cmd},
    })
    proc = subprocess.run([sys.executable, HOOK], input=payload,
                          capture_output=True, text=True, env=env)
    return proc.returncode, proc.stdout, proc.stderr


def _git(args, cwd):
    subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True)


def make_repo():
    d = tempfile.mkdtemp(prefix="cpg-repo-")
    _git(["init", "-q"], d)
    _git(["config", "user.email", "t@t.t"], d)
    _git(["config", "user.name", "t"], d)
    return d


def write_and_stage(repo, name, text="x"):
    p = os.path.join(repo, name)
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(text)
    _git(["add", name], repo)
    return os.path.normcase(os.path.abspath(p))


def sessions_tmp():
    return tempfile.mkdtemp(prefix="cpg-sess-")


def seed_touched(sessions_dir, sid, paths, age_h=0):
    d = os.path.join(sessions_dir, sid)
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, "touched-files.txt")
    with open(p, "w", encoding="utf-8") as fh:
        for x in paths:
            fh.write(x + "\n")
    if age_h:
        old = time.time() - age_h * 3600
        os.utime(p, (old, old))
    return p


def fleet_state_with(sids):
    fd, path = tempfile.mkstemp(suffix="_fleet.json")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump({"sessions": {s: {"status": "working", "cwd": "x", "lastAt": "t"}
                                for s in sids}}, fh)
    return path


# ---------- Task 2 cases: detection + always-allow ----------

def test_non_git_command_silent():
    repo = make_repo()
    rc, out, err = run_hook("ls -la", repo, sessions_tmp())
    assert rc == 0, "non-git must allow, got %s" % rc
    assert out == "" and err == "", "must be silent, got %r / %r" % (out, err)
    print("PASS test_non_git_command_silent")


def test_git_commit_with_no_foreign_files_allows():
    repo = make_repo()
    write_and_stage(repo, "mine.txt")
    rc, out, err = run_hook('git commit -m "x"', repo, sessions_tmp())
    assert rc == 0, "no foreign files -> allow, got %s (%s)" % (rc, err)
    print("PASS test_git_commit_with_no_foreign_files_allows")


def test_malformed_stdin_fails_open():
    env = dict(os.environ)
    env["COMMIT_PROVENANCE_SESSIONS_DIR"] = sessions_tmp()
    proc = subprocess.run([sys.executable, HOOK], input="not json",
                          capture_output=True, text=True, env=env)
    assert proc.returncode == 0, "malformed stdin must exit 0, got %s" % proc.returncode
    print("PASS test_malformed_stdin_fails_open")


def test_cwd_not_a_repo_allows():
    d = tempfile.mkdtemp(prefix="cpg-norepo-")
    rc, out, err = run_hook('git commit -m "x"', d, sessions_tmp())
    assert rc == 0, "not a git repo -> allow, got %s" % rc
    print("PASS test_cwd_not_a_repo_allows")


def test_dry_run_allows():
    """--dry-run fixes no provenance, so it is never blocked."""
    repo = make_repo()
    foreign = write_and_stage(repo, "theirs.txt")
    sess = sessions_tmp()
    seed_touched(sess, "other", [foreign])
    fs = fleet_state_with(["other"])
    rc, out, err = run_hook('git commit --dry-run -m "x"', repo, sess, fleet_state=fs)
    assert rc == 0, "--dry-run must always allow, got %s (%s)" % (rc, err)
    print("PASS test_dry_run_allows")


# ---------- Regression cases: tokenization, not regex substring/split ----------

def test_git_add_of_commit_named_file_is_not_a_commit():
    """`is_git_commit` must key off the git SUBCOMMAND, not a substring match
    -- a filename containing "commit" must never trigger the guard."""
    assert is_git_commit("git add hooks/commit-provenance-guard.py") is False
    assert is_git_commit("git log --oneline -- hooks/commit-provenance-guard.py") is False
    assert is_git_commit('git commit -m "x"') is True
    assert is_git_commit("cd /x && git commit -m y") is True
    print("PASS test_git_add_of_commit_named_file_is_not_a_commit")


def test_commit_message_with_dashdash_does_not_corrupt_pathspec():
    """A ` -- ` sequence inside a quoted -m message must not be mistaken for
    the pathspec separator; a REAL trailing `--` pathspec must still work."""
    repo = make_repo()
    mine = write_and_stage(repo, "mine.txt")
    theirs = write_and_stage(repo, "theirs.txt")

    no_real_pathspec = candidate_paths(repo, 'git commit -m "foo -- bar"')
    assert no_real_pathspec == {mine, theirs}, (
        "no real pathspec -> full staged set, got %r" % no_real_pathspec)

    with_pathspec = candidate_paths(
        repo, 'git commit -m "foo -- bar" -- mine.txt')
    assert with_pathspec == {mine}, (
        "real pathspec after a quoted -- must win, got %r" % with_pathspec)
    print("PASS test_commit_message_with_dashdash_does_not_corrupt_pathspec")


def test_pathspec_narrows_candidate_set():
    repo = make_repo()
    mine = write_and_stage(repo, "mine.txt")
    theirs = write_and_stage(repo, "theirs.txt")

    result = candidate_paths(repo, 'git commit -m "x" -- mine.txt')
    assert result == {mine}, "pathspec must narrow to just mine.txt, got %r" % result
    assert theirs not in result
    print("PASS test_pathspec_narrows_candidate_set")


# ---------- Task 3 cases: the block predicate ----------

def test_foreign_file_from_live_session_blocks():
    """THE case this guard exists for -- 2026-07-16's 4da5d26 sweep."""
    repo = make_repo()
    foreign = write_and_stage(repo, "theirs.txt")
    sess = sessions_tmp()
    seed_touched(sess, "other", [foreign])
    fs = fleet_state_with(["other"])
    rc, out, err = run_hook('git commit -m "x"', repo, sess, fleet_state=fs)
    assert rc == 2, "must BLOCK a foreign-file commit, got %s (%s)" % (rc, err)
    assert "theirs.txt" in err, "stderr must name the file, got %r" % err
    assert "other" in err, "stderr must name the owning session, got %r" % err
    print("PASS test_foreign_file_from_live_session_blocks")


def test_foreign_file_but_session_not_live_allows():
    """Liveness contract: no affirmative 'open' signal -> no information -> allow."""
    repo = make_repo()
    foreign = write_and_stage(repo, "theirs.txt")
    sess = sessions_tmp()
    seed_touched(sess, "other", [foreign])
    rc, out, err = run_hook('git commit -m "x"', repo, sess,
                            fleet_state="C:/does/not/exist_cpg.json")
    assert rc == 0, "dead/unknown session must not block, got %s (%s)" % (rc, err)
    print("PASS test_foreign_file_but_session_not_live_allows")


def test_foreign_touched_set_older_than_ttl_allows():
    repo = make_repo()
    foreign = write_and_stage(repo, "theirs.txt")
    sess = sessions_tmp()
    seed_touched(sess, "other", [foreign], age_h=99)
    fs = fleet_state_with(["other"])
    rc, out, err = run_hook('git commit -m "x"', repo, sess, fleet_state=fs, ttl_h=6)
    assert rc == 0, "stale touched-set must not block, got %s (%s)" % (rc, err)
    print("PASS test_foreign_touched_set_older_than_ttl_allows")


def test_explicit_pathspec_excluding_foreign_allows():
    """The remediation the block message recommends MUST actually work."""
    repo = make_repo()
    foreign = write_and_stage(repo, "theirs.txt")
    write_and_stage(repo, "mine.txt")
    sess = sessions_tmp()
    seed_touched(sess, "other", [foreign])
    fs = fleet_state_with(["other"])
    rc, out, err = run_hook('git commit -m "x" -- mine.txt', repo, sess, fleet_state=fs)
    assert rc == 0, "pathspec excluding the foreign file must allow, got %s (%s)" % (rc, err)
    print("PASS test_explicit_pathspec_excluding_foreign_allows")


def test_override_sentinel_allows():
    """The deliberate 'land the orphaned backlog' janitor workflow (c0272bb)."""
    repo = make_repo()
    foreign = write_and_stage(repo, "theirs.txt")
    sess = sessions_tmp()
    seed_touched(sess, "other", [foreign])
    fs = fleet_state_with(["other"])
    d = os.path.join(sess, "me")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "allow-foreign-commit"), "w", encoding="ascii") as fh:
        fh.write("landing backlog")
    rc, out, err = run_hook('git commit -m "x"', repo, sess, fleet_state=fs)
    assert rc == 0, "override sentinel must allow, got %s (%s)" % (rc, err)
    print("PASS test_override_sentinel_allows")


def test_own_touched_set_never_blocks_self():
    """Self-recognition is structural: only other_sid != my_sid is consulted."""
    repo = make_repo()
    mine = write_and_stage(repo, "mine.txt")
    sess = sessions_tmp()
    seed_touched(sess, "me", [mine])
    fs = fleet_state_with(["me"])
    rc, out, err = run_hook('git commit -m "x"', repo, sess, session_id="me", fleet_state=fs)
    assert rc == 0, "a session must never block itself, got %s (%s)" % (rc, err)
    print("PASS test_own_touched_set_never_blocks_self")


def test_commit_dash_a_picks_up_foreign_tracked_modification():
    repo = make_repo()
    p = os.path.join(repo, "theirs.txt")
    with open(p, "w", encoding="utf-8") as fh:
        fh.write("v1")
    _git(["add", "theirs.txt"], repo)
    _git(["commit", "-m", "base"], repo)
    with open(p, "w", encoding="utf-8") as fh:
        fh.write("v2 -- their uncommitted edit")   # tracked-modified, NOT staged
    foreign = os.path.normcase(os.path.abspath(p))
    sess = sessions_tmp()
    seed_touched(sess, "other", [foreign])
    fs = fleet_state_with(["other"])
    rc, out, err = run_hook('git commit -am "x"', repo, sess, fleet_state=fs)
    assert rc == 2, "-a must capture tracked-modified foreign files, got %s (%s)" % (rc, err)
    print("PASS test_commit_dash_a_picks_up_foreign_tracked_modification")


if __name__ == "__main__":
    test_non_git_command_silent()
    test_git_commit_with_no_foreign_files_allows()
    test_malformed_stdin_fails_open()
    test_cwd_not_a_repo_allows()
    test_dry_run_allows()
    test_git_add_of_commit_named_file_is_not_a_commit()
    test_commit_message_with_dashdash_does_not_corrupt_pathspec()
    test_pathspec_narrows_candidate_set()
    test_foreign_file_from_live_session_blocks()
    test_foreign_file_but_session_not_live_allows()
    test_foreign_touched_set_older_than_ttl_allows()
    test_explicit_pathspec_excluding_foreign_allows()
    test_override_sentinel_allows()
    test_own_touched_set_never_blocks_self()
    test_commit_dash_a_picks_up_foreign_tracked_modification()
    print("ALL COMMIT-PROVENANCE-GUARD TESTS PASS")
