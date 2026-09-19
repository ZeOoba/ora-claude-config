"""Tests for commit-provenance-guard.py PreToolUse hook (matcher: Bash).

Run: python test-commit-provenance-guard.py
Stdlib only. ASCII-only. Self-contained (creates its own temp git repos).
Fail-open BY CONSTRUCTION: blocking needs TWO affirmative signals (a foreign
touched-set hit AND affirmative liveness). Anything else -> allow.
"""

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

# This test spins up its own throwaway git repos in temp dirs. When invoked as part of
# the real pre-push hook chain, git sets GIT_DIR/GIT_WORK_TREE/GIT_INDEX_FILE (etc.) in
# this process's environment so IT can operate on the outer repo -- but those same vars
# leak into every subprocess git call below and silently redirect them at the outer repo
# instead of the temp one, breaking git operations against the temp fixtures.
for _v in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR",
           "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_PREFIX"):
    os.environ.pop(_v, None)

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"))
import gitfixture  # noqa: E402  (shared repo fixture -- open-items-tracker.md#OI-061)

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # hooks/
HOOK = os.path.join(HERE, "commit-provenance-guard.py")

# Load the guard module directly by file path so tests can call its
# functions (is_git_commit, candidate_paths, repo_root) in-process.
_spec = importlib.util.spec_from_file_location("commit_provenance_guard", HOOK)
_cpg = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_cpg)
is_git_commit = _cpg.is_git_commit
candidate_paths = _cpg.candidate_paths
find_commit_segment = _cpg.find_commit_segment
repo_root = _cpg.repo_root
last_commit_time = _cpg.last_commit_time


def run_hook(cmd, cwd, sessions_dir, session_id="me", fleet_state=None, ttl_h=None):
    env = dict(os.environ)
    env["COMMIT_PROVENANCE_SESSIONS_DIR"] = sessions_dir
    if ttl_h is not None:
        env["COMMIT_PROVENANCE_TTL_H"] = str(ttl_h)
    env["ORA_FLEET_STATE"] = fleet_state or "C:/does/not/exist_cpg.json"
    # This test suite's fixtures speak the LEGACY single-file liveness format.
    # other_active_sessions()'s no-override production path (which this guard
    # always uses) prefers the NEW per-session directory over ORA_FLEET_STATE
    # whenever that directory exists -- and fleet-session-hook.py's 2026-07-25
    # per-session-file redesign means it now genuinely exists on any machine
    # that has actually run the live hook. Without this override these fixtures
    # would silently stop exercising the legacy branch (and these tests would
    # pass or fail depending on unrelated real machine state) the moment that
    # directory first appears on disk.
    env["ORA_FLEET_SESSIONS_DIR"] = "C:/does/not/exist_cpg_sessions_dir"
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
    # Shared template-and-copy fixture (open-items-tracker.md#OI-061). Identical shape to
    # the hand-rolled version this replaces -- init + user config, NO commit -- but the 3
    # git spawns are paid ONCE per process instead of on each of the 38 call sites here.
    # This file was the largest remaining fixture cost: test-side git spawns 179 -> 68
    # (process-tree-wide, including the guard's own internal git calls, 230 -> 119).
    # Timing is load-dominated and NOT a reliable ranking signal -- idle medians measured
    # between 10.5s and 34.4s for the same file; prefer the spawn delta, which is
    # deterministic. An earlier "72.2s = 80% of the 90s budget" note was measured under
    # self-inflicted load and was wrong; do not reintroduce it.
    return gitfixture.blank_repo(prefix="cpg-repo-")


def write_and_stage(repo, name, text="x"):
    p = os.path.join(repo, name)
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(text)
    _git(["add", name], repo)
    return os.path.normcase(os.path.abspath(p))


def sessions_tmp():
    return tempfile.mkdtemp(prefix="cpg-sess-")


def seed_touched(sessions_dir, sid, paths, age_h=0, touch_ts=None, no_timestamp=False):
    """Write a touched-files.txt for `sid`. `touch_ts` (default: now) is the
    per-path touch time written into the new tab-separated format; pass
    `no_timestamp=True` to write the pre-2026-07-17 bare-path format instead
    (exercises the "unknown touch time -> conservative" fallback).
    `age_h` ages the FILE's own mtime, independent of the per-path timestamp
    -- it drives the existing whole-set TTL check, not the new per-path one.
    """
    d = os.path.join(sessions_dir, sid)
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, "touched-files.txt")
    ts = touch_ts if touch_ts is not None else time.time()
    with open(p, "w", encoding="utf-8") as fh:
        for x in paths:
            fh.write(x + "\n" if no_timestamp else "%s\t%.6f\n" % (x, ts))
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


def test_broken_sibling_import_allows_and_does_not_traceback_on_non_commits():
    """Regression, adversarial review 2026-07-17: commit_provenance.py / session_liveness.py
    are imported at MODULE LOAD, before main()'s first line -- so an import failure used to
    crash the hook on EVERY Bash call, not just git commits (the traceback fires before
    is_git_commit()'s fast-path check is even reached). Reproduced pre-fix: a plain `ls -la`
    tracebacked and exited 1. This guard's own SAFETY INVARIANT is "no information -> ALLOW"
    for missing/stale data; an import failure must degrade the same way, on ANY command."""
    sandbox = tempfile.mkdtemp(prefix="cpg-broken-")
    shutil.copytree(HERE, os.path.join(sandbox, "hooks"))
    broken_hook = os.path.join(sandbox, "hooks", "commit-provenance-guard.py")
    os.remove(os.path.join(sandbox, "hooks", "lib", "commit_provenance.py"))

    for label, command in (
        ("a plain non-git command", "ls -la"),
        ("an actual git commit", 'git commit -m "x"'),
    ):
        env = dict(os.environ)
        env["COMMIT_PROVENANCE_SESSIONS_DIR"] = sessions_tmp()
        proc = subprocess.run(
            [sys.executable, broken_hook],
            input=json.dumps({"session_id": "me", "cwd": tempfile.mkdtemp(),
                              "tool_input": {"command": command}}),
            capture_output=True, text=True, env=env)
        assert proc.returncode == 0, (
            "%s with the sibling module missing must ALLOW (exit 0), got %s\nstderr: %s"
            % (label, proc.returncode, proc.stderr))
        assert "Traceback" not in proc.stderr, (
            "%s tracebacked with the sibling module missing -- the import guard did not "
            "catch it\nstderr: %s" % (label, proc.stderr))

    shutil.rmtree(sandbox, ignore_errors=True)
    print("PASS test_broken_sibling_import_allows_and_does_not_traceback_on_non_commits")


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


def test_heredoc_message_with_trailing_pathspec_narrows_candidate_set():
    """2026-07-26 real-incident reproduction. `tokenize_cmd_segments()` split the
    command LINE BY LINE with no cross-line quote tracking, so a heredoc-style
    `-m "$(cat <<'EOF' ... EOF)"` -- the pattern this fleet's own commit
    instructions REQUIRE for every commit message -- opens a `"` on its first
    line that isn't closed until several lines later. Each line was shlex-split
    independently; line 1 hit an unterminated-quote ValueError and fell back to
    a bare whitespace split, capping the recognized commit args at that one
    line. A trailing `-- <pathspec>` on the line AFTER the heredoc closes
    landed in its own disconnected, non-"git ..." segment and was silently
    dropped -- candidate_paths() then fell through to "no pathspec -> the
    WHOLE staged index", exactly the false positive that blocked a real,
    correctly-pathspec-scoped commit on both commit-provenance-guard.py and
    eos-review-gate.py (which share this module). A single-line `-m` with the
    same trailing pathspec already worked fine (test_pathspec_narrows_
    candidate_set above) -- this is specifically the heredoc/multi-line case."""
    repo = make_repo()
    mine = write_and_stage(repo, "mine.txt")
    theirs = write_and_stage(repo, "theirs.txt")

    cmd = (
        'git commit -m "$(cat <<\'EOF\'\n'
        'fix: a real multi-line commit message\n\n'
        'Body paragraph explaining the change in more than one line,\n'
        'the way this fleet'"'"'s own commit convention requires.\n\n'
        'Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>\n'
        'EOF\n'
        ')" -- mine.txt'
    )
    result = candidate_paths(repo, cmd)
    assert result == {mine}, (
        "a heredoc commit message with a trailing pathspec must narrow to "
        "just the pathspec'd file, same as the single-line case -- got %r "
        "(theirs.txt leaking in means the pathspec was silently dropped and "
        "the whole staged index was used instead)" % result)
    assert theirs not in result
    print("PASS test_heredoc_message_with_trailing_pathspec_narrows_candidate_set")


def test_chained_command_dashdash_does_not_hijack_pathspec():
    """2026-07-24 independent-review finding (M2, shared with eos-review-gate.py,
    which reuses candidate_paths via git_commit_parse.py). A `--` belonging to a
    DIFFERENT chained command must not be read as THIS commit's pathspec -- the
    old whole-string `"--" in tokens` scan found the `--` in a trailing
    `git log ... -- hooks/` and discarded the real staged set entirely."""
    repo = make_repo()
    mine = write_and_stage(repo, "mine.txt")
    theirs = write_and_stage(repo, "theirs.txt")

    result = candidate_paths(
        repo, 'git commit -m "x" && git log -1 --format=%s -- hooks/')
    assert result == {mine, theirs}, (
        "a foreign segment's -- must not narrow this commit's candidates, got %r"
        % result)
    print("PASS test_chained_command_dashdash_does_not_hijack_pathspec")


def test_dry_run_in_commit_message_does_not_blind_a_real_commit():
    """2026-07-24 independent-review finding (m5). The old check was
    `"--dry-run" in cmd` over the WHOLE raw string -- a commit message that
    merely mentions the text "--dry-run" (plausible in this very hooks/ repo)
    silently zeroed out is_git_commit for a real, non-dry-run commit."""
    assert is_git_commit('git commit -m "docs: explain the --dry-run flag"') is True
    assert is_git_commit('git commit --dry-run -m "x"') is False, (
        "a REAL --dry-run flag on the commit segment must still be recognized")
    print("PASS test_dry_run_in_commit_message_does_not_blind_a_real_commit")


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
    """TTL is keyed off the ENTRY's own touch_ts (2026-07-20 fix) -- age the
    per-path timestamp itself, not just the touched-files.txt file's mtime,
    which no longer gates this check at all (see the compounding-bug test
    below for why the old file-mtime gate was wrong)."""
    repo = make_repo()
    foreign = write_and_stage(repo, "theirs.txt")
    sess = sessions_tmp()
    stale_ts = time.time() - 99 * 3600
    seed_touched(sess, "other", [foreign], touch_ts=stale_ts)
    fs = fleet_state_with(["other"])
    rc, out, err = run_hook('git commit -m "x"', repo, sess, fleet_state=fs, ttl_h=6)
    assert rc == 0, "stale touched-set must not block, got %s (%s)" % (rc, err)
    print("PASS test_foreign_touched_set_older_than_ttl_allows")


def test_stale_entry_ages_out_even_when_other_entries_in_same_file_are_fresh():
    """Root cause 2 regression (2026-07-20): the OLD code gated TTL on
    touched-files.txt's whole-file mtime, so a live session that keeps
    touching OTHER paths keeps rewriting (and re-mtime-ing) the file, which
    kept a days-stale entry for THIS path looking fresh forever. TTL must be
    evaluated per-entry off that entry's own touch_ts, independent of
    whatever else the session touched more recently in the same file."""
    repo = make_repo()
    foreign = write_and_stage(repo, "theirs.txt")
    other_file = os.path.normcase(os.path.abspath(os.path.join(repo, "unrelated.txt")))
    sess = sessions_tmp()
    stale_ts = time.time() - 99 * 3600
    d = os.path.join(sess, "other")
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, "touched-files.txt")
    with open(p, "w", encoding="utf-8") as fh:
        fh.write("%s\t%.6f\n" % (foreign, stale_ts))        # 99h-stale candidate
        fh.write("%s\t%.6f\n" % (other_file, time.time()))  # fresh, unrelated --
        # keeps the FILE's own mtime fresh even though `foreign`'s own touch is old.
    fs = fleet_state_with(["other"])
    rc, out, err = run_hook('git commit -m "x"', repo, sess, fleet_state=fs, ttl_h=6)
    assert rc == 0, (
        "a per-entry-stale touch must age out even while the session's "
        "touched-files.txt mtime stays fresh from other activity, got %s (%s)"
        % (rc, err))
    print("PASS test_stale_entry_ages_out_even_when_other_entries_in_same_file_are_fresh")


def test_unknown_touch_time_never_ages_out_via_ttl():
    """Unknown touch time (pre-2026-07-17 bare-path format) has no per-path
    timestamp to age -- per commit_provenance.py's documented contract it
    stays 'just touched' and must never time out, even if the file's own
    mtime is ancient (proving the file mtime is no longer consulted at all)."""
    repo = make_repo()
    foreign = write_and_stage(repo, "theirs.txt")
    sess = sessions_tmp()
    seed_touched(sess, "other", [foreign], no_timestamp=True)
    old = time.time() - 99 * 3600
    p = os.path.join(sess, "other", "touched-files.txt")
    os.utime(p, (old, old))
    fs = fleet_state_with(["other"])
    rc, out, err = run_hook('git commit -m "x"', repo, sess, fleet_state=fs, ttl_h=6)
    assert rc == 2, (
        "unknown touch time must never age out via TTL, got %s (%s)" % (rc, err))
    print("PASS test_unknown_touch_time_never_ages_out_via_ttl")


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


def test_heredoc_pathspec_excluding_foreign_allows_end_to_end():
    """2026-07-26 real-incident reproduction, full hook subprocess this time (not
    just candidate_paths() in-process). The block message's OWN recommended
    remediation is `git commit -m "..." -- <your/file>` -- but this fleet's
    commit convention REQUIRES a heredoc for that `-m`, and combining the two
    is exactly the shape that silently lost the pathspec and blocked a
    legitimate, correctly-scoped commit. Companion to
    test_heredoc_message_with_trailing_pathspec_narrows_candidate_set, which
    checks candidate_paths() directly -- this checks the actual hook exit
    code, the thing that matters operationally."""
    repo = make_repo()
    foreign = write_and_stage(repo, "theirs.txt")
    write_and_stage(repo, "mine.txt")
    sess = sessions_tmp()
    seed_touched(sess, "other", [foreign])
    fs = fleet_state_with(["other"])
    cmd = (
        'git commit -m "$(cat <<\'EOF\'\n'
        'fix: a real multi-line commit message\n\n'
        'Body paragraph explaining the change.\n'
        'EOF\n'
        ')" -- mine.txt'
    )
    rc, out, err = run_hook(cmd, repo, sess, fleet_state=fs)
    assert rc == 0, (
        "a heredoc-message commit with a pathspec excluding the foreign file "
        "must allow, got %s (%s) -- if this blocks, the pathspec was silently "
        "dropped and the guard saw (and flagged) the foreign file instead" %
        (rc, err))
    print("PASS test_heredoc_pathspec_excluding_foreign_allows_end_to_end")


def test_apostrophe_in_comment_does_not_hide_a_real_commit():
    """Adversarial-review finding (2026-07-26, same-day as the heredoc fix
    above): the FIRST fix attempt for the heredoc bug accumulated lines on an
    unterminated-quote ValueError and, on end-of-input, naive-split the WHOLE
    merged buffer as one token stream. An apostrophe inside a `#` shell
    comment (`# don't add theirs`) reads to plain shlex (without
    comments=True) as an unterminated single-quote -- the merged-buffer
    fallback then swallowed a REAL, later `git commit` line into that one
    meaningless token stream instead of recognizing it as its own segment,
    making is_git_commit() return False for a command that unambiguously
    does commit. That is a false ALLOW on both commit-provenance-guard.py
    and eos-review-gate.py -- worse than the bug being fixed, since it
    silently disables enforcement rather than merely over-blocking. Caught
    by independent review before landing; this locks the fix in."""
    assert is_git_commit(
        "git add mine.txt  # don't add theirs\n"
        'git commit -am "sweep"'
    ) is True, "a real trailing commit must still be detected past a comment apostrophe"
    print("PASS test_apostrophe_in_comment_does_not_hide_a_real_commit")


def test_cascading_comment_apostrophes_do_not_hide_a_real_commit():
    """Second half of the same adversarial-review finding: a comment
    apostrophe on one line can be spuriously "closed" by an UNRELATED
    comment apostrophe on a LATER line, making the merged buffer look
    quote-balanced to plain shlex while actually burying a real, intervening
    `git commit` inside what shlex then reads as literal quoted content."""
    assert is_git_commit(
        "git add a.txt # don't\n"
        "git commit -am x\n"
        "echo ok # can't"
    ) is True, "a real commit sandwiched between two comment-apostrophe lines must still be detected"
    print("PASS test_cascading_comment_apostrophes_do_not_hide_a_real_commit")


def test_large_heredoc_body_tokenizes_in_linear_not_quadratic_time():
    """Adversarial-review finding (2026-07-26): the FIRST fix attempt called
    shlex.split() on the ENTIRE growing buffer on every accumulated line --
    O(n^2) in input size. Independently measured at 13s for a 500-line
    heredoc body and 55s for 1000 lines, against the ~5s budget other gates
    in this codebase assume for a hook call; both commit-provenance-guard.py
    and eos-review-gate.py call tokenize_cmd_segments() on every Bash
    PreToolUse with no size pre-filter, so this was a real per-commit stall
    risk, not just a benchmark curiosity. The actual fix tracks quote state
    incrementally per line (_scan_quote_state, O(line length)) instead of
    re-tokenizing the whole buffer each time, so total cost is O(total input
    length). A 2000-line body -- 4x the size that took the old approach 55s
    -- must complete in low single-digit seconds with wide margin."""
    body = "\n".join("line %d of a very long commit message body" % i for i in range(2000))
    cmd = "git commit -m \"$(cat <<'EOF'\n" + body + "\nEOF\n)\" -- mine.txt"
    start = time.time()
    args = find_commit_segment(cmd)
    elapsed = time.time() - start
    assert args is not None and "--" in args, (
        "a 2000-line heredoc must still tokenize correctly, not just quickly")
    assert elapsed < 5.0, (
        "2000-line heredoc took %.2fs -- expected sub-second, this smells like "
        "the old O(n^2) re-tokenization behavior again" % elapsed)
    print("PASS test_large_heredoc_body_tokenizes_in_linear_not_quadratic_time "
          "(%.3fs)" % elapsed)


def test_heredoc_body_with_decoy_dashdash_does_not_leak_as_pathspec():
    """Round-3 adversarial-review finding (2026-07-26, on the round-2 fix
    attempt): with no `$(...)` awareness, an ODD count of `"` inside the
    heredoc BODY flipped the round-2 scanner's outer quote-state parity,
    ending the segment early and exposing later body prose as commit args --
    reproduced there to leak a decoy `-- decoy.txt` as if it were the REAL
    pathspec, silently dropping the actual `-- mine.txt` into a discarded
    tail segment. The current fix excises the heredoc body as opaque content
    (matched by its literal terminator line, never quote-scanned at all), so
    nothing inside it -- including a stray, unbalanced `"` -- can affect
    anything outside it."""
    cmd = (
        'git commit -m "$(cat <<\'EOF\'\n'
        'use "safe -- decoy.txt as the fix\n'
        'EOF\n'
        ')" -- mine.txt'
    )
    args = find_commit_segment(cmd)
    assert args is not None, "the real commit must still be detected"
    assert "--" in args, args
    idx = args.index("--")
    assert args[idx + 1:] == ["mine.txt"], (
        "the pathspec must be mine.txt, not decoy content leaked from the "
        "heredoc body: %r" % args)
    print("PASS test_heredoc_body_with_decoy_dashdash_does_not_leak_as_pathspec")


def test_heredoc_body_with_decoy_dry_run_does_not_blind_the_commit():
    """Same round-3 finding, second shape: a decoy `--dry-run` leaked from an
    odd-quote-count heredoc body into the real commit's args, making
    is_git_commit() return False for a command that unambiguously commits."""
    cmd = (
        'git commit -m "$(cat <<\'EOF\'\n'
        'try "safe mode with --dry-run first\n'
        'EOF\n'
        ')" -- mine.txt'
    )
    assert is_git_commit(cmd) is True, "a real commit must not be hidden by heredoc body prose"
    args = find_commit_segment(cmd)
    assert "--dry-run" not in args, (
        "a decoy --dry-run from the heredoc body must not leak into real args: %r" % args)
    print("PASS test_heredoc_body_with_decoy_dry_run_does_not_blind_the_commit")


def test_mid_word_hash_does_not_hide_a_same_line_commit():
    """Round-3 adversarial-review finding: bash only starts a `#` comment at
    the START of a word; the round-2 fix (and shlex's own comments=True)
    treated ANY unquoted `#` as a comment-start, so `${#arr[@]}` -- a bash
    parameter-expansion length operator, `#` mid-word -- hid a real,
    same-line-following `git commit` entirely. The current fix removes
    comment-handling from the quote scanner altogether (comments are no
    longer relevant once the heredoc body is excised via its own literal
    terminator-line rule instead of quote/comment scanning), so a bare `#`
    anywhere is just an ordinary character for quote-parity purposes."""
    assert is_git_commit("echo ${#arr[@]} && git commit -am x") is True
    assert is_git_commit("sed s/#/x/ f && git commit -am x") is True
    print("PASS test_mid_word_hash_does_not_hide_a_same_line_commit")


def test_pathspec_containing_hash_is_not_truncated():
    """Same finding, third shape: a real pathspec containing `#` (a real,
    if unusual, filename character) must not be truncated at the `#` by an
    overly aggressive comment rule."""
    args = find_commit_segment('git commit -m x -- readme#old.md')
    assert args is not None
    assert args[-1] == "readme#old.md", args
    print("PASS test_pathspec_containing_hash_is_not_truncated")


def test_heredoc_unrelated_to_commit_message_is_not_misread():
    """A heredoc used for something OTHER than a commit message (e.g.
    writing a file) must still be recognized and excised correctly, and must
    not itself be mistaken for a commit segment; the real `git commit` after
    it must still be detected as its own segment."""
    cmd = "cat <<'EOF' > file.txt\nsome content\nEOF\ngit commit -m x"
    args = find_commit_segment(cmd)
    assert args == ["-m", "x"], args
    print("PASS test_heredoc_unrelated_to_commit_message_is_not_misread")


def test_indented_decoy_terminator_does_not_end_the_heredoc_early():
    """Round-4 adversarial-review finding (2026-07-26, on the round-3 fix):
    bash requires the terminator line to be an EXACT match for the
    delimiter -- no surrounding whitespace tolerated (unless `<<-` is used,
    which strips only LEADING TABS before comparing). The round-3 version
    matched via `line.strip() == delim`, so a body line that is merely an
    INDENTED variant of the delimiter (`  EOF`) ended the heredoc early to
    this parser while bash keeps reading it as body -- re-exposing the rest
    of the body, including a decoy `-- decoy.txt`, as shell-level text.
    Bash-verified: a body line `  EOF` is body, not a terminator."""
    cmd = (
        "git commit -m \"$(cat <<'EOF'\n"
        "  EOF\n"
        'use "safe -- decoy.txt as the fix\n'
        "EOF\n"
        ')" -- mine.txt'
    )
    args = find_commit_segment(cmd)
    assert args is not None, "the real commit must still be detected"
    assert "--" in args, args
    idx = args.index("--")
    assert args[idx + 1:] == ["mine.txt"], (
        "an indented decoy 'EOF' in the body must not end the heredoc early "
        "and leak decoy content as the pathspec: %r" % args)
    print("PASS test_indented_decoy_terminator_does_not_end_the_heredoc_early")


def test_quoted_fake_marker_does_not_excise_a_real_intervening_commit():
    """Round-4 adversarial-review finding: the marker regex had no quote
    awareness, so `<<WORD` appearing INSIDE a quote (`echo "see <<EOF
    docs"`) was read as a real heredoc marker. If some later, unrelated line
    coincidentally equals that fake delimiter, a real intervening `git
    commit` between them got excised as if it were heredoc "body". Bash-
    verified: the quoted `<<EOF` is plain text to bash, not a marker, so the
    commit runs for real."""
    cmd = 'echo "see <<EOF docs"\ngit commit -am sweep\nEOF'
    assert is_git_commit(cmd) is True, (
        "a real commit between a quoted fake marker and a coincidental "
        "matching line must still be detected, not excised as fake body")
    print("PASS test_quoted_fake_marker_does_not_excise_a_real_intervening_commit")


def test_fallback_never_re_exposes_the_excised_heredoc_body():
    """Round-4 adversarial-review finding: when the shell-level quote never
    balances by end-of-input (e.g. a trailing comment-apostrophe after the
    pathspec keeps the scanner open forever, since it has no comment
    handling by design), the fallback used to re-tokenize the ENTIRE
    consumed range -- including the excised heredoc BODY -- as ordinary
    shell lines. A body line containing real-looking commit flags
    (`git commit --dry-run -m example`) then surfaced as a fabricated final
    segment, making is_git_commit() return False for a command that
    unambiguously does commit. The body and its terminator must never be
    re-tokenized on ANY path, including this one."""
    cmd = (
        "git commit -m \"$(cat <<'EOF'\n"
        "git commit --dry-run -m example\n"
        "EOF\n"
        ")\" -- mine.txt  # don't forget"
    )
    assert is_git_commit(cmd) is True, (
        "the real commit must be detected even when the fallback path fires; "
        "if this returns False, heredoc body prose leaked back into args")
    print("PASS test_fallback_never_re_exposes_the_excised_heredoc_body")


def test_non_word_delimiter_still_narrows_pathspec():
    """Round-5 adversarial-review finding: the delimiter regex only matched
    a plain word-character class, but bash's heredoc delimiter is a full
    shell WORD (`END-OF-MSG`, `EOF.txt` are both legal). A delimiter outside
    the narrow class never matched its own real terminator line, silently
    reproducing round 1's original false-block (whole staged index) for any
    such delimiter."""
    repo = make_repo()
    mine = write_and_stage(repo, "mine.txt")
    theirs = write_and_stage(repo, "theirs.txt")
    cmd = (
        "git commit -m \"$(cat <<'END-OF-MSG'\n"
        "body text\n"
        "END-OF-MSG\n"
        ')" -- mine.txt'
    )
    result = candidate_paths(repo, cmd)
    assert result == {mine}, (
        "a non-word delimiter (END-OF-MSG) must still correctly narrow to "
        "the pathspec, got %r" % result)
    assert theirs not in result
    print("PASS test_non_word_delimiter_still_narrows_pathspec")


def test_truncated_delimiter_prefix_as_body_line_does_not_end_heredoc_early():
    """Round-5 companion to the above: with the delimiter widened, a body
    line matching the OLD truncated word-only prefix (`END` for a real
    `END-OF-MSG` delimiter) must not be mistaken for the real terminator --
    that was the false-allow direction of the same narrow-charset bug."""
    cmd = (
        "git commit -m \"$(cat <<'END-OF-MSG'\n"
        'use "safe -- decoy.txt as the fix\n'
        "END-OF-MSG\n"
        ')" -- mine.txt'
    )
    args = find_commit_segment(cmd)
    assert args is not None and "--" in args, args
    idx = args.index("--")
    assert args[idx + 1:] == ["mine.txt"], (
        "decoy content must not leak as the pathspec: %r" % args)
    print("PASS test_truncated_delimiter_prefix_as_body_line_does_not_end_heredoc_early")


def test_already_closed_subshell_does_not_grant_the_marker_escape_hatch():
    """Round-5 adversarial-review finding: the `$(` escape hatch for the
    marker-quote-rejection check used to be a bare substring test, foolable
    by a `$(...)` that closes its OWN `)` before the `<<` appears --
    `echo "$(date +%Y) note <<EOF here"` has a `$(` earlier on the line, but
    it's already closed, so the `<<EOF` is genuinely still just quoted text
    to bash, not a real marker. If a later, unrelated line coincidentally
    equals that fake delimiter, a real intervening `git commit` must still
    be detected, not excised as fake heredoc body."""
    cmd = (
        'echo "$(date +%Y) note <<EOF here"\n'
        'git commit -am sweep\n'
        'EOF'
    )
    assert is_git_commit(cmd) is True, (
        "a real commit after an already-closed-subshell decoy marker must "
        "still be detected")
    print("PASS test_already_closed_subshell_does_not_grant_the_marker_escape_hatch")


def test_quote_opened_on_an_earlier_line_is_not_forgotten():
    """Round-5 adversarial-review finding: the marker-rejection check always
    started scanning from state=None, so it was structurally blind to a
    quote opened on an EARLIER, non-heredoc line. A quote spanning two plain
    lines (no heredoc involved at all) whose second line happens to contain
    `<<DELIM` must still correctly reject that as a real marker -- and the
    real, later `git commit` must still be found. `carry_state` threads the
    quote parity across non-heredoc lines (gating marker acceptance only,
    never merging lines for tokenization) to close this."""
    cmd = (
        'echo "line one\n'
        'see <<EOF docs"\n'
        'git commit -am sweep\n'
        'EOF'
    )
    assert is_git_commit(cmd) is True, (
        "a real commit after a marker inside a quote opened on an earlier "
        "line must still be detected, not excised as fake heredoc body")
    print("PASS test_quote_opened_on_an_earlier_line_is_not_forgotten")


def test_carry_state_does_not_reintroduce_the_round_2_regression():
    """Guard against carry_state (round 5) reintroducing round 2's
    cross-line-accumulation false-allow: a comment apostrophe on one
    (non-heredoc) line must still never hide a real commit on a later
    line -- carry_state only gates heredoc-marker acceptance, it must never
    cause non-heredoc lines to be merged for tokenization."""
    cmd = "git add mine.txt  # don't add theirs\ngit commit -am \"sweep\""
    assert is_git_commit(cmd) is True
    print("PASS test_carry_state_does_not_reintroduce_the_round_2_regression")


def test_herestring_operator_is_not_mistaken_for_a_heredoc_marker():
    """Round-5 adversarial-review finding: `<<<WORD` is bash's here-STRING
    operator -- an entirely different, single-line construct with no body
    or terminator at all. The marker regex matched it anyway via its middle
    `<<`, and if a later, unrelated line coincidentally equalled the
    here-string's own word, everything in between (including a real `git
    commit`) was excised as fake heredoc body. A genuine `cat<<EOF` (no
    space before the operator) must remain unaffected by the fix."""
    cmd = "grep -q x <<<hello\ngit commit -am sweep\nhello"
    assert is_git_commit(cmd) is True, (
        "a real commit after a here-string operator must still be "
        "detected, not excised as fake heredoc body")
    cmd2 = "cat<<EOF\nbody\nEOF\ngit commit -m x"
    args2 = find_commit_segment(cmd2)
    assert args2 == ["-m", "x"], (
        "a genuine no-space heredoc marker must still be recognized: %r" % args2)
    print("PASS test_herestring_operator_is_not_mistaken_for_a_heredoc_marker")


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


# ---------- Recency-heuristic fix (2026-07-17): re-diff against HEAD, don't
# just trust the touched-set + TTL. 3 false positives in one session the same
# day were all this exact shape: another session's edit had already landed in
# HEAD by commit time, but the touched-set entry (and liveness) persisted. ----

def test_foreign_edit_already_committed_since_touch_allows():
    """THE false-positive case from 2026-07-17: `other` touched shared.txt an
    hour ago; that content is already safely committed; `me` now has its OWN
    separate, later edit staged on the same path. Must ALLOW -- `other`'s
    contribution is provably already safe, and blocking here would attribute
    only MY OWN new work to a foreign hit."""
    repo = make_repo()
    p = os.path.join(repo, "shared.txt")
    with open(p, "w", encoding="utf-8") as fh:
        fh.write("v1 base")
    _git(["add", "shared.txt"], repo)
    _git(["commit", "-m", "base"], repo)
    shared = os.path.normcase(os.path.abspath(p))

    sess = sessions_tmp()
    an_hour_ago = time.time() - 3600
    seed_touched(sess, "other", [shared], touch_ts=an_hour_ago)

    # `other`'s edit lands (committed just now, i.e. AFTER their recorded touch).
    with open(p, "w", encoding="utf-8") as fh:
        fh.write("v2 -- other's edit, now committed")
    _git(["add", "shared.txt"], repo)
    _git(["commit", "-m", "other's edit lands"], repo)

    # `me` now makes a separate, later edit of my own on the SAME path.
    with open(p, "w", encoding="utf-8") as fh:
        fh.write("v3 -- my own separate edit")
    _git(["add", "shared.txt"], repo)

    fs = fleet_state_with(["other"])
    rc, out, err = run_hook('git commit -m "my change"', repo, sess, fleet_state=fs)
    assert rc == 0, (
        "other's already-committed touch must not block my own later edit, "
        "got %s (%s)" % (rc, err))
    print("PASS test_foreign_edit_already_committed_since_touch_allows")


def test_foreign_touch_after_last_commit_still_blocks():
    """The genuinely risky case: `other` touched shared.txt AFTER the last
    commit that includes it -- their edit could still be sitting uncommitted
    on their side. Must still BLOCK."""
    repo = make_repo()
    p = os.path.join(repo, "shared.txt")
    with open(p, "w", encoding="utf-8") as fh:
        fh.write("v1 base")
    _git(["add", "shared.txt"], repo)
    _git(["commit", "-m", "base"], repo)
    shared = os.path.normcase(os.path.abspath(p))

    sess = sessions_tmp()
    an_hour_from_now = time.time() + 3600  # safely after the base commit above
    seed_touched(sess, "other", [shared], touch_ts=an_hour_from_now)

    # `me` stages a change to the same path -- `other`'s (newer) touch is
    # unaccounted for by any commit.
    with open(p, "w", encoding="utf-8") as fh:
        fh.write("v2 -- my edit, but other touched it more recently, unlanded")
    _git(["add", "shared.txt"], repo)

    fs = fleet_state_with(["other"])
    rc, out, err = run_hook('git commit -m "x"', repo, sess, fleet_state=fs)
    assert rc == 2, (
        "a touch newer than the last commit must still block, got %s (%s)" % (rc, err))
    print("PASS test_foreign_touch_after_last_commit_still_blocks")


def test_unknown_touch_time_still_blocks_even_if_committed():
    """Backward-compat / conservative-default check: an old-format bare-path
    touched-files.txt line (no timestamp) must keep the ORIGINAL behaviour --
    always a hit -- even when the path has since been committed. Unknown
    touch time must never be treated as 'safe'."""
    repo = make_repo()
    p = os.path.join(repo, "shared.txt")
    with open(p, "w", encoding="utf-8") as fh:
        fh.write("v1 base")
    _git(["add", "shared.txt"], repo)
    _git(["commit", "-m", "base"], repo)
    shared = os.path.normcase(os.path.abspath(p))

    sess = sessions_tmp()
    seed_touched(sess, "other", [shared], no_timestamp=True)  # old format

    with open(p, "w", encoding="utf-8") as fh:
        fh.write("v2 -- my edit")
    _git(["add", "shared.txt"], repo)

    fs = fleet_state_with(["other"])
    rc, out, err = run_hook('git commit -m "x"', repo, sess, fleet_state=fs)
    assert rc == 2, (
        "unknown touch time must stay conservative (always a hit), got %s (%s)"
        % (rc, err))
    print("PASS test_unknown_touch_time_still_blocks_even_if_committed")


# ---------- Case-sensitivity fix (2026-07-20): norm() lowercases the whole
# absolute path (os.path.normcase on Windows); `git log -- <pathspec>` matches
# literally regardless of core.ignorecase, so a lowercased pathspec silently
# failed to match any real path with an uppercase character anywhere in it.
# Every fixture filename elsewhere in this file happens to already be
# lowercase, so normcase was a no-op there and never exercised the bug --
# these tests deliberately use MixedCase names to force the mismatch. ----

def test_last_commit_time_finds_commit_despite_normcased_path():
    """Direct unit-level regression: last_commit_time() must resolve a
    normcase'd (lowercased) pathspec against a commit whose real on-disk
    path has uppercase characters in the directory AND the filename."""
    repo = make_repo()
    mixed_dir = os.path.join(repo, "MixedCase")
    os.makedirs(mixed_dir, exist_ok=True)
    p = os.path.join(mixed_dir, "SharedFile.TXT")
    with open(p, "w", encoding="utf-8") as fh:
        fh.write("v1")
    _git(["add", "MixedCase/SharedFile.TXT"], repo)
    _git(["commit", "-m", "base"], repo)
    norm_path = os.path.normcase(os.path.abspath(p))
    if os.name == "nt":
        assert norm_path != os.path.abspath(p), (
            "fixture assumption failed: normcase should lowercase this path "
            "on Windows -- test would be vacuous otherwise")
    ct = last_commit_time(repo, norm_path)
    assert ct is not None, (
        "last_commit_time must find the commit via a normcased (lowercased) "
        "pathspec -- got None, the 2026-07-20 case-sensitivity regression is back")
    print("PASS test_last_commit_time_finds_commit_despite_normcased_path")


def test_mixed_case_foreign_edit_already_committed_since_touch_allows():
    """Full-flow regression: a MixedCase path touched by another live session
    an hour ago, but safely committed since -- must ALLOW. Same shape as
    test_foreign_edit_already_committed_since_touch_allows above, but with a
    path that actually stresses the normcase/pathspec-matching fix (that
    earlier test's all-lowercase fixture name accidentally could not)."""
    repo = make_repo()
    mixed_dir = os.path.join(repo, "MixedCase")
    os.makedirs(mixed_dir, exist_ok=True)
    p = os.path.join(mixed_dir, "SharedFile.TXT")
    with open(p, "w", encoding="utf-8") as fh:
        fh.write("v1 base")
    _git(["add", "MixedCase/SharedFile.TXT"], repo)
    _git(["commit", "-m", "base"], repo)
    shared = os.path.normcase(os.path.abspath(p))

    sess = sessions_tmp()
    an_hour_ago = time.time() - 3600
    seed_touched(sess, "other", [shared], touch_ts=an_hour_ago)

    with open(p, "w", encoding="utf-8") as fh:
        fh.write("v2 -- other's edit, now committed")
    _git(["add", "MixedCase/SharedFile.TXT"], repo)
    _git(["commit", "-m", "other's edit lands"], repo)

    with open(p, "w", encoding="utf-8") as fh:
        fh.write("v3 -- my own separate edit")
    _git(["add", "MixedCase/SharedFile.TXT"], repo)

    fs = fleet_state_with(["other"])
    rc, out, err = run_hook('git commit -m "my change"', repo, sess, fleet_state=fs, ttl_h=6)
    assert rc == 0, (
        "a mixed-case path safely committed since its touch must not "
        "block (2026-07-20 case-sensitivity regression), got %s (%s)"
        % (rc, err))
    print("PASS test_mixed_case_foreign_edit_already_committed_since_touch_allows")


# ---------- Compound `git add ... && git commit` blind spot (2026-07-24) ----------
# PreToolUse fires BEFORE the command executes, so at hook-fire time the `git add`
# in a compound command has NOT run yet -- `git diff --cached --name-only` sees an
# EMPTY index, candidate_paths() returns an empty set, and main()'s
# `if not cands: return` allows the commit before foreign_hits() is ever consulted.
# Confirmed as the mechanism behind a real incident: 4 janitor commits of this exact
# shape (`git add <paths> && git commit -q -F -`) swept 41 files including two other
# live sessions' uncommitted edits, and commit-provenance-guard did not fire despite
# every OTHER precondition for a block being met (recorder healthy, liveness healthy,
# no override sentinel, touch well within TTL). See event_log.md 2026-07-24.

def test_compound_explicit_add_then_commit_includes_unstaged_file():
    """Direct unit check: an explicit `git add foo.txt` naming a file that is on
    disk but NOT YET staged must appear in candidate_paths() -- simulating the
    hook firing before the add actually runs."""
    repo = make_repo()
    p = os.path.join(repo, "foreign.txt")
    with open(p, "w", encoding="utf-8") as fh:
        fh.write("unstaged content")
    # deliberately NOT `git add`-ed -- the whole point is the add hasn't run yet
    expect = os.path.normcase(os.path.abspath(p))
    result = candidate_paths(repo, 'git add foreign.txt && git commit -m "x"')
    assert result is not None and expect in result, (
        "an about-to-be-staged explicit path must be a candidate, got %r" % result)
    print("PASS test_compound_explicit_add_then_commit_includes_unstaged_file")


def test_compound_add_dash_capital_a_includes_modified_and_untracked():
    """`git add -A` stages both modified-tracked and untracked files; the
    pre-execution candidate set must include both kinds."""
    repo = make_repo()
    tracked = os.path.join(repo, "tracked.txt")
    with open(tracked, "w", encoding="utf-8") as fh:
        fh.write("v1")
    _git(["add", "tracked.txt"], repo)
    _git(["commit", "-m", "base"], repo)
    with open(tracked, "w", encoding="utf-8") as fh:
        fh.write("v2 -- unstaged modification")
    untracked = os.path.join(repo, "new.txt")
    with open(untracked, "w", encoding="utf-8") as fh:
        fh.write("brand new")

    result = candidate_paths(repo, 'git add -A && git commit -m "x"')
    assert result is not None
    assert os.path.normcase(os.path.abspath(tracked)) in result, (
        "modified tracked file must be a candidate under -A, got %r" % result)
    assert os.path.normcase(os.path.abspath(untracked)) in result, (
        "untracked file must be a candidate under -A, got %r" % result)
    print("PASS test_compound_add_dash_capital_a_includes_modified_and_untracked")


def test_compound_add_dot_includes_untracked():
    """`git add .` (bare dot) must behave like -A for candidate purposes."""
    repo = make_repo()
    untracked = os.path.join(repo, "new.txt")
    with open(untracked, "w", encoding="utf-8") as fh:
        fh.write("brand new")
    result = candidate_paths(repo, 'git add . && git commit -m "x"')
    assert result is not None
    assert os.path.normcase(os.path.abspath(untracked)) in result, (
        "untracked file must be a candidate under `add .`, got %r" % result)
    print("PASS test_compound_add_dot_includes_untracked")


def test_add_segment_after_commit_segment_is_not_collected():
    """Precision check: a `git add` that comes AFTER the commit in the same
    compound command could not possibly have been staged for THIS commit --
    must not be treated as a candidate (guards against over-broad matching)."""
    repo = make_repo()
    later = os.path.join(repo, "later.txt")
    with open(later, "w", encoding="utf-8") as fh:
        fh.write("added after the commit fires")
    result = candidate_paths(repo, 'git commit -m "x" && git add later.txt')
    assert result == set() or os.path.normcase(os.path.abspath(later)) not in (result or set()), (
        "an add AFTER the commit segment must not be collected, got %r" % result)
    print("PASS test_add_segment_after_commit_segment_is_not_collected")


def test_plain_commit_with_no_add_segment_unaffected():
    """A bare `git commit` with no preceding `git add` anywhere must behave
    exactly as before -- pure regression guard for the existing majority of
    calls, which don't have this compound shape at all."""
    repo = make_repo()
    mine = write_and_stage(repo, "mine.txt")
    result = candidate_paths(repo, 'git commit -m "x"')
    assert result == {mine}, "unaffected by the new logic, got %r" % result
    print("PASS test_plain_commit_with_no_add_segment_unaffected")


def test_compound_add_and_commit_blocks_foreign_file_end_to_end():
    """THE incident reproduction, full stack via run_hook(): another live
    session's untracked file sits on disk; THIS session runs the exact
    `git add <paths> && git commit ...` shape the janitor commits used.
    Before the fix: candidate_paths() saw an empty staged set (add hadn't run
    yet) -> `if not cands: return` -> silently ALLOWED (rc 0) -- reproducing
    the real incident. After the fix: must BLOCK (rc 2)."""
    repo = make_repo()
    foreign_path = os.path.join(repo, "theirs.txt")
    with open(foreign_path, "w", encoding="utf-8") as fh:
        fh.write("another live session's uncommitted edit")
    foreign = os.path.normcase(os.path.abspath(foreign_path))
    mine_path = os.path.join(repo, "mine.txt")
    with open(mine_path, "w", encoding="utf-8") as fh:
        fh.write("my own file")

    sess = sessions_tmp()
    seed_touched(sess, "other", [foreign])
    fs = fleet_state_with(["other"])

    rc, out, err = run_hook(
        'git add theirs.txt mine.txt && git commit -m "x"', repo, sess, fleet_state=fs)
    assert rc == 2, (
        "compound add+commit sweeping a foreign untracked file must BLOCK, "
        "got %s (%s) -- this is the 2026-07-24 incident shape" % (rc, err))
    assert "theirs.txt" in err, "stderr must name the foreign file, got %r" % err
    print("PASS test_compound_add_and_commit_blocks_foreign_file_end_to_end")


def test_compound_add_dash_capital_a_blocks_foreign_untracked_file_end_to_end():
    """Same incident shape but via `git add -A` instead of explicit paths."""
    repo = make_repo()
    foreign_path = os.path.join(repo, "theirs.txt")
    with open(foreign_path, "w", encoding="utf-8") as fh:
        fh.write("another live session's uncommitted edit")
    foreign = os.path.normcase(os.path.abspath(foreign_path))

    sess = sessions_tmp()
    seed_touched(sess, "other", [foreign])
    fs = fleet_state_with(["other"])

    rc, out, err = run_hook('git add -A && git commit -m "x"', repo, sess, fleet_state=fs)
    assert rc == 2, (
        "compound `git add -A` sweeping a foreign untracked file must BLOCK, "
        "got %s (%s)" % (rc, err))
    print("PASS test_compound_add_dash_capital_a_blocks_foreign_untracked_file_end_to_end")


def test_compound_add_of_only_own_files_still_allows():
    """No false positive: a compound add+commit that stages ONLY the caller's
    own files (nothing in any other live session's touched-set) must ALLOW."""
    repo = make_repo()
    mine_path = os.path.join(repo, "mine.txt")
    with open(mine_path, "w", encoding="utf-8") as fh:
        fh.write("just mine")
    sess = sessions_tmp()
    # no touched-set entries at all -- nothing foreign in play
    rc, out, err = run_hook('git add mine.txt && git commit -m "x"', repo, sess)
    assert rc == 0, "compound add+commit of only own files must allow, got %s (%s)" % (rc, err)
    print("PASS test_compound_add_of_only_own_files_still_allows")


def test_compound_add_explicit_dir_expands_to_modified_files_inside():
    """Directory expansion: `git add somedir` should be treated the same as
    staging every modified/untracked file currently under that directory."""
    repo = make_repo()
    sub = os.path.join(repo, "subdir")
    os.makedirs(sub, exist_ok=True)
    inner = os.path.join(sub, "inner.txt")
    with open(inner, "w", encoding="utf-8") as fh:
        fh.write("untracked, inside subdir")
    result = candidate_paths(repo, 'git add subdir && git commit -m "x"')
    assert result is not None
    assert os.path.normcase(os.path.abspath(inner)) in result, (
        "a file inside an added directory must be a candidate, got %r" % result)
    print("PASS test_compound_add_explicit_dir_expands_to_modified_files_inside")


# ---------- REFUTE-pass follow-up (2026-07-24): the compound-add fix above
# only caught the &&/;/||/|-joined, `git`-token-first shape. An adversarial
# security-auditor pass found two ordinary, non-adversarial shapes that
# reproduced the SAME incident: newline-separated statements (no operator
# between the add and the commit) and env-var-prefixed invocations. Both
# empirically verified against the pre-fix code before being closed. ----------

def test_env_var_prefixed_add_still_detected():
    """`FOO=bar git add x` -- a leading env-assignment token must not hide
    the `git add` from the segment detector."""
    repo = make_repo()
    p = os.path.join(repo, "foreign.txt")
    with open(p, "w", encoding="utf-8") as fh:
        fh.write("unstaged")
    expect = os.path.normcase(os.path.abspath(p))
    result = candidate_paths(
        repo, 'GIT_AUTHOR_NAME=x git add foreign.txt && git commit -m "x"')
    assert result is not None and expect in result, (
        "env-var-prefixed add must still be detected, got %r" % result)
    print("PASS test_env_var_prefixed_add_still_detected")


def test_newline_separated_add_then_commit_still_detected():
    """`git add` and `git commit` on separate physical lines with NO shell
    operator between them -- a bare newline is still a statement boundary."""
    repo = make_repo()
    p = os.path.join(repo, "foreign.txt")
    with open(p, "w", encoding="utf-8") as fh:
        fh.write("unstaged")
    expect = os.path.normcase(os.path.abspath(p))
    cmd = 'git add foreign.txt\ngit commit -m "x"'
    result = candidate_paths(repo, cmd)
    assert result is not None and expect in result, (
        "newline-separated add+commit must still be detected, got %r" % result)
    print("PASS test_newline_separated_add_then_commit_still_detected")


def test_env_var_prefixed_add_blocks_foreign_file_end_to_end():
    """Full stack reproduction of REFUTE PoC (1)."""
    repo = make_repo()
    foreign_path = os.path.join(repo, "theirs.txt")
    with open(foreign_path, "w", encoding="utf-8") as fh:
        fh.write("another live session's uncommitted edit")
    foreign = os.path.normcase(os.path.abspath(foreign_path))
    sess = sessions_tmp()
    seed_touched(sess, "other", [foreign])
    fs = fleet_state_with(["other"])
    rc, out, err = run_hook(
        'GIT_AUTHOR_NAME=x git add theirs.txt && git commit -m "sweep"',
        repo, sess, fleet_state=fs)
    assert rc == 2, (
        "env-var-prefixed add sweeping a foreign file must BLOCK, got %s (%s)"
        % (rc, err))
    print("PASS test_env_var_prefixed_add_blocks_foreign_file_end_to_end")


def test_newline_separated_add_blocks_foreign_file_end_to_end():
    """Full stack reproduction of REFUTE PoC (2)."""
    repo = make_repo()
    foreign_path = os.path.join(repo, "theirs2.txt")
    with open(foreign_path, "w", encoding="utf-8") as fh:
        fh.write("another live session's uncommitted edit")
    foreign = os.path.normcase(os.path.abspath(foreign_path))
    sess = sessions_tmp()
    seed_touched(sess, "other", [foreign])
    fs = fleet_state_with(["other"])
    cmd = 'cd .\ngit add theirs2.txt\ngit commit -m "sweep"'
    rc, out, err = run_hook(cmd, repo, sess, fleet_state=fs)
    assert rc == 2, (
        "newline-separated add sweeping a foreign file must BLOCK, got %s (%s)"
        % (rc, err))
    print("PASS test_newline_separated_add_blocks_foreign_file_end_to_end")


def test_heredoc_body_mentioning_git_add_in_single_commit_does_not_false_block():
    """Accepted-gap safe-direction guarantee (2nd-round REFUTE, 2026-07-24): a
    single `git commit -m "..."` whose heredoc-style body happens to contain
    the literal words "git add" as prose must NOT be misread as a real add
    segment -- there is no OTHER commit segment strictly AFTER that phantom
    line (only the one real, opening `git commit` invocation exists in this
    command), so _git_add_segments()'s own "needs a commit after it" rule
    excludes it. Deliberately does NOT also mention "git commit" inside the
    body text -- doing so would create a SECOND commit-shaped line, which is
    the accepted-gap's own documented trigger condition (any add with some
    commit segment after it, anywhere), not the safe case being locked in
    here. This guards the "fails safe, never hides a real hit" property so a
    future change can't quietly flip it to unsafe."""
    repo = make_repo()
    cmd = (
        'git commit -m "$(cat <<\'EOF\'\n'
        'fix: describe a workaround\n\n'
        'For a partial splice, first run:\n'
        'git add PHANTOM.md\n'
        'then finish it by hand.\n'
        'EOF\n'
        ')"'
    )
    result = candidate_paths(repo, cmd)
    phantom = os.path.normcase(os.path.abspath(os.path.join(repo, "PHANTOM.md")))
    assert result is None or phantom not in result, (
        "a heredoc body mentioning 'git add' as prose inside a SINGLE commit "
        "must not be treated as a real candidate, got %r" % result)
    print("PASS test_heredoc_body_mentioning_git_add_in_single_commit_does_not_false_block")


def test_add_sandwiched_between_two_commits_is_collected_for_the_second():
    """REFUTE PoC (3): `commit; add; commit` -- a naive 'stop at the FIRST
    commit segment' rule drops the sandwiched add entirely, even though it
    plainly gets staged for the SECOND commit. Must be collected."""
    repo = make_repo()
    p = os.path.join(repo, "sandwiched.txt")
    with open(p, "w", encoding="utf-8") as fh:
        fh.write("unstaged")
    expect = os.path.normcase(os.path.abspath(p))
    cmd = 'git commit -m "first"\ngit add sandwiched.txt\ngit commit -m "second"'
    result = candidate_paths(repo, cmd)
    assert result is not None and expect in result, (
        "an add sandwiched between two commits must be collected for the "
        "later one, got %r" % result)
    print("PASS test_add_sandwiched_between_two_commits_is_collected_for_the_second")


# --------------------------------------------------------------------------
# degraded contract: guarded import failed -> ANNOUNCE, still allow
# --------------------------------------------------------------------------
# Same incident as the review gate's equivalent tests (2026-09-17): a partial
# branch sync left a hooks/lib module missing, the guarded import caught it,
# PROVENANCE_CONTRACT_LOADED went False, and main() returned immediately -- so
# the guard silently allowed commits that could sweep up another session's
# uncommitted work, looking exactly like "nothing to flag".
#
# The fix here is VISIBILITY, not blocking. eos-review-gate.py fails closed on
# the same signal; this guard does not, because the 2026-07-17 adversarial
# review ratified allow-on-import-failure for ANY command (the test above,
# test_broken_sibling_import_allows_..., pins it) and because blocking here
# would freeze commits fleet-wide on one broken lib file. Gabriel chose that
# split 2026-09-17.


def _run_degraded(command):
    """Run a COPY of the guard whose hooks/lib is EMPTY, so the guarded import
    fails for real rather than by monkeypatching."""
    td = tempfile.mkdtemp(prefix="cpg-degraded-")
    try:
        hooks_dir = os.path.join(td, "hooks")
        os.makedirs(os.path.join(hooks_dir, "lib"))
        hook = os.path.join(hooks_dir, "commit-provenance-guard.py")
        shutil.copy2(HOOK, hook)
        env = dict(os.environ)
        env["PYTHONPATH"] = ""  # the real hooks/lib must not satisfy the import
        stdin_text = json.dumps({
            "session_id": "me", "cwd": td, "tool_name": "Bash",
            "tool_input": {"command": command},
        })
        proc = subprocess.run([sys.executable, hook], input=stdin_text,
                              capture_output=True, text=True, env=env)
        return proc.returncode, proc.stderr
    finally:
        shutil.rmtree(td, ignore_errors=True)


def test_degraded_contract_allows_a_commit_but_says_it_is_ungated():
    """This guard does NOT fail closed -- see _degraded()'s docstring. The
    2026-07-17 ruling (allow on import failure, commits included) stands; what
    changed 2026-09-17 is that the allow is no longer SILENT."""
    rc, err = _run_degraded('git commit -m "x" -- hooks/lib/git_commit_parse.py')
    assert rc == 0, (
        "the 2026-07-17 invariant is allow-on-no-information, commits included; "
        "got rc=%s err=%r" % (rc, err))
    assert "could not be imported" in err, (
        "the allow must name the real cause: %r" % err)
    assert "UNGATED" in err, (
        "an allowed commit must say plainly that nothing checked it: %r" % err)


def test_degraded_wording_does_not_assert_a_git_add_is_a_commit():
    """The detector over-matches (`\\bcommit\\b` fires on the hyphen in
    commit-provenance-guard.py), so the warning says a command MENTIONS a commit
    rather than asserting it IS one. Nothing gates on this side -- the claim is
    purely textual, which is exactly why it needs a test."""
    rc, err = _run_degraded("git add hooks/commit-provenance-guard.py")
    assert rc == 0, "this guard never blocks while degraded, got rc=%s" % rc
    assert "mentions a git commit" in err, (
        "an over-match must not be worded as a certainty: %r" % err)


def test_degraded_contract_allows_non_commit_but_announces():
    rc, err = _run_degraded("ls -la")
    assert rc == 0, (
        "blocking every Bash call would brick the fleet, got rc=%s err=%r" % (rc, err))
    assert "commit-provenance-guard" in err and "could not be imported" in err, (
        "a degraded guard must announce itself even when it allows: %r" % err)


if __name__ == "__main__":
    test_non_git_command_silent()
    test_git_commit_with_no_foreign_files_allows()
    test_malformed_stdin_fails_open()
    test_broken_sibling_import_allows_and_does_not_traceback_on_non_commits()
    test_cwd_not_a_repo_allows()
    test_dry_run_allows()
    test_git_add_of_commit_named_file_is_not_a_commit()
    test_commit_message_with_dashdash_does_not_corrupt_pathspec()
    test_pathspec_narrows_candidate_set()
    test_heredoc_message_with_trailing_pathspec_narrows_candidate_set()
    test_chained_command_dashdash_does_not_hijack_pathspec()
    test_dry_run_in_commit_message_does_not_blind_a_real_commit()
    test_foreign_file_from_live_session_blocks()
    test_foreign_file_but_session_not_live_allows()
    test_foreign_touched_set_older_than_ttl_allows()
    test_stale_entry_ages_out_even_when_other_entries_in_same_file_are_fresh()
    test_unknown_touch_time_never_ages_out_via_ttl()
    test_last_commit_time_finds_commit_despite_normcased_path()
    test_mixed_case_foreign_edit_already_committed_since_touch_allows()
    test_explicit_pathspec_excluding_foreign_allows()
    test_heredoc_pathspec_excluding_foreign_allows_end_to_end()
    test_apostrophe_in_comment_does_not_hide_a_real_commit()
    test_cascading_comment_apostrophes_do_not_hide_a_real_commit()
    test_large_heredoc_body_tokenizes_in_linear_not_quadratic_time()
    test_heredoc_body_with_decoy_dashdash_does_not_leak_as_pathspec()
    test_heredoc_body_with_decoy_dry_run_does_not_blind_the_commit()
    test_mid_word_hash_does_not_hide_a_same_line_commit()
    test_pathspec_containing_hash_is_not_truncated()
    test_heredoc_unrelated_to_commit_message_is_not_misread()
    test_indented_decoy_terminator_does_not_end_the_heredoc_early()
    test_quoted_fake_marker_does_not_excise_a_real_intervening_commit()
    test_fallback_never_re_exposes_the_excised_heredoc_body()
    test_non_word_delimiter_still_narrows_pathspec()
    test_truncated_delimiter_prefix_as_body_line_does_not_end_heredoc_early()
    test_already_closed_subshell_does_not_grant_the_marker_escape_hatch()
    test_quote_opened_on_an_earlier_line_is_not_forgotten()
    test_carry_state_does_not_reintroduce_the_round_2_regression()
    test_herestring_operator_is_not_mistaken_for_a_heredoc_marker()
    test_override_sentinel_allows()
    test_own_touched_set_never_blocks_self()
    test_commit_dash_a_picks_up_foreign_tracked_modification()
    test_foreign_edit_already_committed_since_touch_allows()
    test_foreign_touch_after_last_commit_still_blocks()
    test_unknown_touch_time_still_blocks_even_if_committed()
    test_compound_explicit_add_then_commit_includes_unstaged_file()
    test_compound_add_dash_capital_a_includes_modified_and_untracked()
    test_compound_add_dot_includes_untracked()
    test_add_segment_after_commit_segment_is_not_collected()
    test_plain_commit_with_no_add_segment_unaffected()
    test_compound_add_and_commit_blocks_foreign_file_end_to_end()
    test_compound_add_dash_capital_a_blocks_foreign_untracked_file_end_to_end()
    test_compound_add_of_only_own_files_still_allows()
    test_compound_add_explicit_dir_expands_to_modified_files_inside()
    test_env_var_prefixed_add_still_detected()
    test_newline_separated_add_then_commit_still_detected()
    test_env_var_prefixed_add_blocks_foreign_file_end_to_end()
    test_newline_separated_add_blocks_foreign_file_end_to_end()
    test_add_sandwiched_between_two_commits_is_collected_for_the_second()
    test_heredoc_body_mentioning_git_add_in_single_commit_does_not_false_block()
    test_degraded_contract_allows_a_commit_but_says_it_is_ungated()
    test_degraded_wording_does_not_assert_a_git_add_is_a_commit()
    test_degraded_contract_allows_non_commit_but_announces()
    print("ALL COMMIT-PROVENANCE-GUARD TESTS PASS")
