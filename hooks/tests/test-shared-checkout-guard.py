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


def run_hook(stdin_text, repos, sessions_dir, extra_env=None):
    env = dict(os.environ)
    env["SHARED_CHECKOUT_REPOS"] = os.pathsep.join(repos)
    env["SHARED_CHECKOUT_SESSIONS_DIR"] = sessions_dir
    if extra_env:
        env.update(extra_env)
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


def test_rearm_on_dirty_set_change():
    """A NEW dirty-state fingerprint after the first warning re-arms it --
    the fix for 'warns only once per session even if new external changes land'."""
    repo = make_main_repo(dirty=True)
    sess = sessions_tmp()
    fp = os.path.join(repo, "server", "x.ts")
    _, out1, _ = run_hook(payload("s6", fp), [repo], sess)
    assert "systemMessage" in out1, "first call must warn, got %r" % out1
    with open(os.path.join(repo, "second-foreign-file.txt"), "w") as fh:
        fh.write("more WIP")
    _, out2, _ = run_hook(payload("s6", fp), [repo], sess)
    assert "systemMessage" in out2, (
        "changed dirty set must re-arm the warning, got %r" % out2)
    print("PASS test_rearm_on_dirty_set_change")


def test_same_dirty_set_stays_silent_after_warning():
    """Re-confirms the ORIGINAL dedupe intent survives the re-arm fix: an
    UNCHANGED dirty set must not re-warn on every single edit."""
    repo = make_main_repo(dirty=True)
    sess = sessions_tmp()
    fp = os.path.join(repo, "server", "x.ts")
    _, out1, _ = run_hook(payload("s7", fp), [repo], sess)
    _, out2, _ = run_hook(payload("s7", fp), [repo], sess)
    assert "systemMessage" in out1, "first call must warn, got %r" % out1
    assert "systemMessage" not in out2, (
        "unchanged dirty set must stay silent on the second call, got %r" % out2)
    print("PASS test_same_dirty_set_stays_silent_after_warning")


def test_other_active_session_named_in_message():
    """When session_liveness reports another open session, the warning names it."""
    repo = make_main_repo(dirty=True)
    sess = sessions_tmp()
    fp = os.path.join(repo, "server", "x.ts")
    fd, state_path = tempfile.mkstemp(suffix="_session-state.json")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump({"sessions": {"other-session-99": {"status": "working", "cwd": repo, "lastAt": "t"}}}, fh)
    try:
        rc, out, err = run_hook(payload("s8", fp), [repo], sess, extra_env={"ORA_FLEET_STATE": state_path})
        assert "other-se" in out, (
            "expected the other session's (truncated) id in the warning, got %r" % out)
    finally:
        os.remove(state_path)
    print("PASS test_other_active_session_named_in_message")


def test_no_other_session_generic_message():
    """When session_liveness finds nothing (empty/missing state), the message
    stays the original generic form -- proves the enrichment degrades safely."""
    repo = make_main_repo(dirty=True)
    sess = sessions_tmp()
    fp = os.path.join(repo, "server", "x.ts")
    rc, out, err = run_hook(payload("s9", fp), [repo], sess,
                            extra_env={"ORA_FLEET_STATE": "C:/does/not/exist_xyz.json"})
    assert "systemMessage" in out, "must still warn, got %r" % out
    assert "is open right now" not in out, (
        "no other session known -> must not fabricate a collision note, got %r" % out)
    print("PASS test_no_other_session_generic_message")


def test_warning_reaches_the_model_via_additional_context():
    """REGRESSION (2026-07-16): the warning must reach CLAUDE, not just the user.

    `systemMessage` is documented as "Warning message shown to the USER" and is
    never injected into the model's context. This guard shipped 2026-07-09 emitting
    ONLY systemMessage (+ stderr, which PreToolUse feeds to Claude only on exit 2 --
    and this hook exits 0 by design). Net effect: it fired correctly for 7 days
    (168 session markers) while the agent it exists to steer never received a single
    warning -- proven live 2026-07-16, when a session edited a file another live
    session was concurrently writing and got no hook warning at all.

    Per the PreToolUse contract, `hookSpecificOutput.additionalContext` is the ONLY
    field that is both model-visible and decoupled from blocking."""
    repo = make_main_repo(dirty=True)
    fp = os.path.join(repo, "server", "x.ts")
    rc, out, err = run_hook(payload("s10", fp), [repo], sessions_tmp())
    assert rc == 0, "must stay non-blocking, got %s" % rc
    data = json.loads(out)
    hso = data.get("hookSpecificOutput") or {}
    assert hso.get("hookEventName") == "PreToolUse", (
        "must declare hookEventName PreToolUse, got %r" % out)
    assert hso.get("permissionDecision") == "allow", (
        "warn-only invariant: must explicitly ALLOW, never deny/ask, got %r" % out)
    assert hso.get("additionalContext"), (
        "the warning must reach the MODEL via additionalContext, got %r" % out)
    assert "is open right now" in hso["additionalContext"] or "uncommitted" in hso["additionalContext"], (
        "additionalContext must carry the actual collision warning, got %r" % hso)
    assert data.get("systemMessage"), "must STILL warn the user via systemMessage too"
    print("PASS test_warning_reaches_the_model_via_additional_context")


def test_silent_cases_emit_no_additional_context():
    """The delivery fix must not make silent cases chatty: a clean tree still
    emits nothing at all (no systemMessage AND no additionalContext)."""
    repo = make_main_repo(dirty=False)
    fp = os.path.join(repo, "server", "x.ts")
    rc, out, err = run_hook(payload("s11", fp), [repo], sessions_tmp())
    assert rc == 0
    assert "additionalContext" not in out, "clean tree must stay fully silent, got %r" % out
    assert "systemMessage" not in out, "clean tree must stay fully silent, got %r" % out
    print("PASS test_silent_cases_emit_no_additional_context")


def test_never_denies_even_when_warning():
    """Explicit guard on the stated SAFETY INVARIANT: warn-only. Adding
    permissionDecision must never introduce deny/ask."""
    repo = make_main_repo(dirty=True)
    fp = os.path.join(repo, "server", "x.ts")
    rc, out, err = run_hook(payload("s12", fp), [repo], sessions_tmp())
    data = json.loads(out)
    decision = (data.get("hookSpecificOutput") or {}).get("permissionDecision")
    assert decision == "allow", "must be allow, got %r" % decision
    assert decision not in ("deny", "ask"), "must never block or prompt"
    assert rc == 0, "must exit 0"
    print("PASS test_never_denies_even_when_warning")


if __name__ == "__main__":
    test_outside_repo_silent()
    test_worktree_silent()
    test_main_clean_silent()
    test_main_dirty_warns()
    test_dedupe_once_per_session()
    test_malformed_stdin_fails_open()
    test_rearm_on_dirty_set_change()
    test_same_dirty_set_stays_silent_after_warning()
    test_other_active_session_named_in_message()
    test_no_other_session_generic_message()
    test_warning_reaches_the_model_via_additional_context()
    test_silent_cases_emit_no_additional_context()
    test_never_denies_even_when_warning()
    print("ALL SHARED-CHECKOUT-GUARD TESTS PASS")
