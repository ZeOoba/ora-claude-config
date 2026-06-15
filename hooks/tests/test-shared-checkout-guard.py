"""Tests for shared-checkout-guard.py PreToolUse hook (Edit|Write|MultiEdit).

Run: python test-shared-checkout-guard.py
Stdlib only. ASCII-only. Self-contained (creates its own temp dirs + git repos).
Warn-only / fail-open: the hook NEVER denies; it emits a systemMessage warning.
"""

import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # hooks/ (test in hooks/tests/)
HOOK = os.path.join(HERE, "shared-checkout-guard.py")


def run_hook(stdin_text, repos, sessions_dir):
    env = dict(os.environ)
    env["SHARED_CHECKOUT_REPOS"] = os.pathsep.join(repos)
    env["SHARED_CHECKOUT_SESSIONS_DIR"] = sessions_dir
    proc = subprocess.run(
        [sys.executable, HOOK],
        input=stdin_text, capture_output=True, text=True, env=env,
    )
    return proc.returncode, proc.stdout, proc.stderr


def payload(session_id, file_path):
    return json.dumps({"session_id": session_id, "tool_input": {"file_path": file_path}})


def _git(args, cwd):
    subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True)


def make_main_repo(dirty):
    d = tempfile.mkdtemp(prefix="scg-main-")
    _git(["init", "-q"], d)
    _git(["config", "user.email", "t@t.t"], d)
    _git(["config", "user.name", "t"], d)
    if dirty:
        with open(os.path.join(d, "foreign-wip.txt"), "w") as fh:
            fh.write("another session's uncommitted work")
    return d


def make_worktree_repo():
    # A linked worktree: .git is a FILE (gitdir pointer), not a directory.
    d = tempfile.mkdtemp(prefix="scg-wt-")
    with open(os.path.join(d, ".git"), "w") as fh:
        fh.write("gitdir: /somewhere/.git/worktrees/x\n")
    return d


def sessions_tmp():
    return tempfile.mkdtemp(prefix="scg-sess-")


def test_outside_repo_silent():
    repo = make_main_repo(dirty=True)
    rc, out, err = run_hook(payload("s1", "C:/somewhere/else/file.ts"), [repo], sessions_tmp())
    assert rc == 0, "outside expected exit 0, got %s (%s)" % (rc, err)
    assert "systemMessage" not in out, "outside must be silent, got %r" % out
    print("PASS test_outside_repo_silent")


def test_worktree_silent():
    repo = make_worktree_repo()
    fp = os.path.join(repo, "server", "x.ts")
    rc, out, err = run_hook(payload("s2", fp), [repo], sessions_tmp())
    assert rc == 0, "worktree expected exit 0, got %s" % rc
    assert "systemMessage" not in out, "linked worktree must be silent, got %r" % out
    print("PASS test_worktree_silent")


def test_main_clean_silent():
    repo = make_main_repo(dirty=False)
    fp = os.path.join(repo, "server", "x.ts")
    rc, out, err = run_hook(payload("s3", fp), [repo], sessions_tmp())
    assert rc == 0, "clean expected exit 0, got %s" % rc
    assert "systemMessage" not in out, "clean main checkout must be silent, got %r" % out
    print("PASS test_main_clean_silent")


def test_main_dirty_warns():
    repo = make_main_repo(dirty=True)
    fp = os.path.join(repo, "server", "x.ts")
    rc, out, err = run_hook(payload("s4", fp), [repo], sessions_tmp())
    assert rc == 0, "dirty expected exit 0 (non-blocking), got %s" % rc
    assert "deny" not in out, "must NEVER deny, got %r" % out
    assert "systemMessage" in out, "dirty main checkout must warn, got %r" % out
    print("PASS test_main_dirty_warns")


def test_dedupe_once_per_session():
    repo = make_main_repo(dirty=True)
    sess = sessions_tmp()
    fp = os.path.join(repo, "server", "x.ts")
    _, out1, _ = run_hook(payload("s5", fp), [repo], sess)
    _, out2, _ = run_hook(payload("s5", fp), [repo], sess)
    assert "systemMessage" in out1, "first call must warn, got %r" % out1
    assert "systemMessage" not in out2, "second call must be silent (dedupe), got %r" % out2
    print("PASS test_dedupe_once_per_session")


def test_malformed_stdin_fails_open():
    repo = make_main_repo(dirty=True)
    rc, out, err = run_hook("not json", [repo], sessions_tmp())
    assert rc == 0, "malformed stdin must exit 0, got %s" % rc
    assert "systemMessage" not in out, "fail-open must be silent, got %r" % out
    print("PASS test_malformed_stdin_fails_open")


if __name__ == "__main__":
    test_outside_repo_silent()
    test_worktree_silent()
    test_main_clean_silent()
    test_main_dirty_warns()
    test_dedupe_once_per_session()
    test_malformed_stdin_fails_open()
    print("ALL SHARED-CHECKOUT-GUARD TESTS PASS")
