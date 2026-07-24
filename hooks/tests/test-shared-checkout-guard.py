"""Tests for shared-checkout-guard.py PreToolUse hook (Edit|Write|MultiEdit).

Run: python test-shared-checkout-guard.py
Stdlib only. ASCII-only. Self-contained (creates its own temp dirs + git repos).
Warn-only / fail-open: the hook NEVER denies; it emits a systemMessage warning.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

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


def make_nested_worktree(main_repo, rel="server-side/.claude/worktrees/nested"):
    """A linked worktree living INSIDE `main_repo`'s own directory tree -- the real
    layout `EnterWorktree`/`git worktree add` produces for a session isolating itself
    within a shared repo (e.g. `<repo>/.claude/worktrees/<name>/`). Returns the nested
    worktree's root path."""
    d = os.path.join(main_repo, rel)
    os.makedirs(d)
    with open(os.path.join(d, ".git"), "w") as fh:
        fh.write("gitdir: /somewhere/.git/worktrees/nested\n")
    return d


def sessions_tmp():
    return tempfile.mkdtemp(prefix="scg-sess-")


def write_liveness_state(sid_cwd_pairs):
    """A session-state.json fixture (the shape hooks/lib/session_liveness.py reads).
    Caller owns the returned path and must remove it."""
    fd, path = tempfile.mkstemp(suffix="_session-state.json")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump({"sessions": {sid: {"status": "working", "cwd": cwd, "lastAt": "t"}
                                for sid, cwd in sid_cwd_pairs}}, fh)
    return path


def record_touched(sessions_dir, sid, paths):
    """Write `sid`'s provenance touched-set exactly as commit-provenance-recorder.py
    does -- `normcase(abspath(path))\\t<epoch>` per line, under
    <sessions_dir>/<sid>/touched-files.txt. The recorder and every reader must agree
    byte-for-byte on this format or the intersection silently misses and attribution
    degrades to unattributed forever (see hooks/lib/commit_provenance.py)."""
    d = os.path.join(sessions_dir, sid)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "touched-files.txt"), "w", encoding="utf-8") as fh:
        for p in paths:
            fh.write("%s\t%.6f\n" % (os.path.normcase(os.path.abspath(p)), time.time()))


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


def test_nested_worktree_silent_even_when_outer_repo_dirty():
    """BUG FIX (2026-07-24): a linked worktree NESTED inside a shared repo's own tree
    (e.g. `<repo>/.claude/worktrees/<name>/`, the actual layout EnterWorktree/`git
    worktree add` produces) must stay silent, even while the OUTER shared repo itself
    is dirty with unrelated WIP -- find_repo() matches the file against the outer root
    by prefix, so without checking the file's OWN nearest .git, the guard used to warn
    about the outer checkout's dirty status for a file that was already isolated.
    Observed live: every edit inside .claude/worktrees/scg-attribution-test/ warned
    about .claude's ~30 unrelated uncommitted changes."""
    main = make_main_repo(dirty=True)  # outer repo IS dirty -- must not matter
    nested = make_nested_worktree(main)
    fp = os.path.join(nested, "server", "x.ts")
    rc, out, err = run_hook(payload("s15", fp), [main], sessions_tmp())
    assert rc == 0, "expected exit 0, got %s (%s)" % (rc, err)
    assert "systemMessage" not in out, (
        "file inside a nested linked worktree must stay silent regardless of the "
        "outer repo's dirty status, got %r" % out)
    # Sanity: a file in the OUTER main checkout (NOT inside the nested worktree) must
    # still warn -- proves the fix narrows to the file's own checkout, it doesn't
    # blanket-silence the whole repo just because ONE nested worktree exists somewhere
    # inside it.
    outer_fp = os.path.join(main, "server", "y.ts")
    rc2, out2, err2 = run_hook(payload("s16", outer_fp), [main], sessions_tmp())
    assert "systemMessage" in out2, (
        "a file in the OUTER main checkout must still warn, got %r" % out2)
    print("PASS test_nested_worktree_silent_even_when_outer_repo_dirty")


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


def test_broken_sibling_import_still_warns_and_does_not_traceback():
    """Regression, adversarial review 2026-07-17: session_liveness.py is imported at MODULE
    LOAD, before main()'s try/except (or is_claude_md-style fast paths) even runs. This
    hook never blocks either way (permissionDecision is always "allow"), so an import
    failure here is not a security regression -- but it IS a reliability one: the crash
    would traceback on EVERY Edit/Write/MultiEdit in every session, not just ones this hook
    has something to say about. Proves TWO things: no traceback with the module missing,
    AND the unrelated dirty-file warning still fires -- the stub degrades only the one
    session-collision detail, not the whole hook."""
    sandbox = tempfile.mkdtemp(prefix="scg-broken-")
    shutil.copytree(HERE, os.path.join(sandbox, "hooks"))
    broken_hook = os.path.join(sandbox, "hooks", "shared-checkout-guard.py")
    os.remove(os.path.join(sandbox, "hooks", "lib", "session_liveness.py"))

    repo = make_main_repo(dirty=True)
    env = dict(os.environ)
    env["SHARED_CHECKOUT_REPOS"] = repo
    env["SHARED_CHECKOUT_SESSIONS_DIR"] = sessions_tmp()
    proc = subprocess.run(
        [sys.executable, broken_hook],
        input=payload("s1", os.path.join(repo, "foreign-wip.txt")),
        capture_output=True, text=True, env=env)

    assert proc.returncode == 0, "must still exit 0, got %s\nstderr: %s" % (
        proc.returncode, proc.stderr)
    assert "Traceback" not in proc.stderr, (
        "tracebacked with session_liveness.py missing -- the import guard did not "
        "catch it\nstderr: %s" % proc.stderr)
    assert "systemMessage" in proc.stdout, (
        "the dirty-file warning itself must still fire -- only the session-collision "
        "detail should degrade, not the whole hook. stdout: %r" % proc.stdout)

    shutil.rmtree(sandbox, ignore_errors=True)
    print("PASS test_broken_sibling_import_still_warns_and_does_not_traceback")


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


def test_other_session_without_provenance_is_unattributed():
    """Liveness ALONE must never name a session -- it is not attribution evidence.

    Supersedes test_other_active_session_named_in_message, which asserted the
    opposite ("other-se" in out) and was left stale by 7d01eff. That commit
    deliberately removed the behavior the old test pinned: _attribute_wip used
    to name others[0], an arbitrary index into the liveness dict, with nothing
    tying that session to the dirty files -- observed live naming an idle,
    provenance-less session across ~8 consecutive warnings while the session
    that made the commits went unnamed. A confidently WRONG name is worse than
    no name. See feedback_shared_checkout_guard_session_attribution_unreliable.md.

    This fixture is exactly that case: a session is open, but has recorded no
    touched-set at all, so the honest output is the UNATTRIBUTED fallback."""
    repo = make_main_repo(dirty=True)
    sess = sessions_tmp()
    fp = os.path.join(repo, "server", "x.ts")
    state_path = write_liveness_state([("other-session-99", repo)])
    try:
        rc, out, err = run_hook(payload("s8", fp), [repo], sess,
                                extra_env={"ORA_FLEET_STATE": state_path})
        assert "UNATTRIBUTED" in out, (
            "open session with no recorded touched-set must be reported as "
            "unattributed, got %r" % out)
        assert "other-se" not in out, (
            "must NOT name a session on liveness alone -- that is the 7d01eff "
            "bug, got %r" % out)
        assert "1 other session(s) are open" in out, (
            "the count of open sessions is still useful context, got %r" % out)
    finally:
        os.remove(state_path)
    print("PASS test_other_session_without_provenance_is_unattributed")


def test_other_session_with_provenance_is_named():
    """The naming branch is LIVE: recorded provenance intersecting the dirty set
    does name the session. Without this the 7d01eff rewrite would leave
    _attribute_wip's hits-branch entirely uncovered -- the test suite would
    certify a dead branch (feedback_fixture_shaped_tests_certify_dead_branches.md)."""
    repo = make_main_repo(dirty=True)
    sess = sessions_tmp()
    fp = os.path.join(repo, "server", "x.ts")
    record_touched(sess, "other-session-99", [os.path.join(repo, "foreign-wip.txt")])
    state_path = write_liveness_state([("other-session-99", repo)])
    try:
        rc, out, err = run_hook(payload("s13", fp), [repo], sess,
                                extra_env={"ORA_FLEET_STATE": state_path})
        assert "other-se" in out, (
            "a session whose recorded touched-set intersects the dirty set MUST "
            "be named, got %r" % out)
        assert "recorded edit(s)" in out, (
            "the named-session clause must state the evidence, got %r" % out)
        assert "UNATTRIBUTED" not in out, (
            "evidence exists -- must not fall back to unattributed, got %r" % out)
    finally:
        os.remove(state_path)
    print("PASS test_other_session_with_provenance_is_named")


def test_provenance_for_unrelated_file_stays_unattributed():
    """Proves the naming test above is not fixture-shaped: the guard intersects
    the touched-set against the DIRTY PATHS, it does not merely check that a
    provenance file exists. Same open session, same provenance file, but the
    recorded path is not in the dirty set -> unattributed."""
    repo = make_main_repo(dirty=True)
    sess = sessions_tmp()
    fp = os.path.join(repo, "server", "x.ts")
    record_touched(sess, "other-session-99", [os.path.join(repo, "some-other-file.txt")])
    state_path = write_liveness_state([("other-session-99", repo)])
    try:
        rc, out, err = run_hook(payload("s14", fp), [repo], sess,
                                extra_env={"ORA_FLEET_STATE": state_path})
        assert "UNATTRIBUTED" in out, (
            "provenance that does not intersect the dirty set is not evidence, "
            "got %r" % out)
        assert "other-se" not in out, "must not name on non-intersecting provenance, got %r" % out
    finally:
        os.remove(state_path)
    print("PASS test_provenance_for_unrelated_file_stays_unattributed")


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
    test_nested_worktree_silent_even_when_outer_repo_dirty()
    test_main_clean_silent()
    test_main_dirty_warns()
    test_broken_sibling_import_still_warns_and_does_not_traceback()
    test_dedupe_once_per_session()
    test_malformed_stdin_fails_open()
    test_rearm_on_dirty_set_change()
    test_same_dirty_set_stays_silent_after_warning()
    test_other_session_without_provenance_is_unattributed()
    test_other_session_with_provenance_is_named()
    test_provenance_for_unrelated_file_stays_unattributed()
    test_no_other_session_generic_message()
    test_warning_reaches_the_model_via_additional_context()
    test_silent_cases_emit_no_additional_context()
    test_never_denies_even_when_warning()
    print("ALL SHARED-CHECKOUT-GUARD TESTS PASS")
