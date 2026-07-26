"""Tests for eos-review-gate.py PreToolUse hook (matcher: Bash).

Run: python test-eos-review-gate.py
Stdlib only. ASCII-only. Self-contained -- builds REAL git repos in temp dirs
(not string fixtures), because every load-bearing decision this gate makes is a
question only git can answer: what a compound `git add X && git commit` would
capture, and what the working-tree content of a risk path actually hashes to.

Shape follows hooks/tests/test-eos-plan-gate.py.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

# This test spins up its own throwaway git repos in temp dirs. When invoked as part of
# the real pre-push hook chain, git sets GIT_DIR/GIT_WORK_TREE/GIT_INDEX_FILE (etc.) in
# this process's environment so IT can operate on the outer repo -- but those same vars
# leak into every subprocess git call below and silently redirect them at the outer repo
# instead of the temp one, breaking `git commit -q -m "init"` and similar with 128 errors.
for _v in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR",
           "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_PREFIX"):
    os.environ.pop(_v, None)

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # hooks/
HOOK = os.path.join(HERE, "eos-review-gate.py")

LADDER_TOP = "claude-fable-5"  # must match eos-review-gate.REVIEWER_MODEL_LADDER[0]


# --------------------------------------------------------------------------
# harness
# --------------------------------------------------------------------------

def git(repo, *args):
    proc = subprocess.run(["git", "-C", repo] + list(args),
                          capture_output=True, text=True)
    assert proc.returncode == 0, "git %s failed: %s" % (args, proc.stderr)
    return proc.stdout


def make_repo():
    """A real git repo with one committed non-risk file."""
    repo = tempfile.mkdtemp(prefix="eos-rg-repo-")
    subprocess.run(["git", "init", "-q", repo], capture_output=True)
    git(repo, "config", "user.email", "t@t.t")
    git(repo, "config", "user.name", "t")
    write(repo, "README.md", "hello\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "init")
    return repo


def write(repo, rel, text):
    path = os.path.join(repo, rel)
    parent = os.path.dirname(path)
    if parent and not os.path.isdir(parent):
        os.makedirs(parent)
    with open(path, "w", encoding="ascii", newline="\n") as fh:
        fh.write(text)
    return path


def run_hook(command, repo, sessions_dir, session_id="sess1", extra_env=None):
    env = dict(os.environ)
    env["EOS_SESSIONS_DIR"] = sessions_dir
    env["ORA_OVERRIDE_SESSIONS_DIR"] = sessions_dir
    if extra_env:
        env.update(extra_env)
    stdin_text = json.dumps({
        "session_id": session_id,
        "cwd": repo,
        "tool_name": "Bash",
        "tool_input": {"command": command},
    })
    proc = subprocess.run([sys.executable, HOOK], input=stdin_text,
                          capture_output=True, text=True, env=env)
    return proc.returncode, proc.stdout, proc.stderr


def run_cli(args, repo, sessions_dir, session_id="sess1"):
    env = dict(os.environ)
    env["EOS_SESSIONS_DIR"] = sessions_dir
    env["ORA_OVERRIDE_SESSIONS_DIR"] = sessions_dir
    env["CLAUDE_CODE_SESSION_ID"] = session_id
    proc = subprocess.run([sys.executable, HOOK, "--repo", repo] + args,
                          capture_output=True, text=True, env=env)
    return proc.returncode, proc.stdout, proc.stderr


def record_review(repo, sessions_dir, session_id="sess1", model=LADDER_TOP,
                  verdict="approved"):
    rc, out, err = run_cli(
        ["--record", "--verdict", verdict, "--model", model,
         "--notes", "test-recorded review"],
        repo, sessions_dir, session_id)
    assert rc == 0, "--record failed rc=%s err=%s" % (rc, err)
    return json.loads(out)


def assert_blocked(rc, err, label):
    assert rc == 2, "%s: expected BLOCK (exit 2), got rc=%s err=%r" % (label, rc, err)
    # Must be the gate's OWN block banner, not merely a stderr mentioning the
    # filename -- a missing or crashing hook also exits non-zero with the path in
    # its message, which would certify these tests green against no gate at all.
    assert "BLOCKED (eos-review-gate)" in err, (
        "%s: must be a real gate block, got %r" % (label, err))


def assert_allowed(rc, err, label):
    assert rc == 0, "%s: expected ALLOW (exit 0), got rc=%s err=%r" % (label, rc, err)


# --------------------------------------------------------------------------
# fast paths / fail-open
# --------------------------------------------------------------------------

def test_non_commit_command_allows():
    repo, tmp = make_repo(), tempfile.mkdtemp(prefix="eos-rg-s-")
    write(repo, "hooks/thing.py", "x = 1\n")
    for cmd in ["ls -la", "git status", "git add hooks/thing.py",
                "npm test", "git log --oneline -5"]:
        rc, out, err = run_hook(cmd, repo, tmp)
        assert_allowed(rc, err, "non-commit %r" % cmd)
    print("PASS test_non_commit_command_allows")


def test_dry_run_commit_allows():
    repo, tmp = make_repo(), tempfile.mkdtemp(prefix="eos-rg-s-")
    write(repo, "hooks/thing.py", "x = 1\n")
    git(repo, "add", "-A")
    rc, out, err = run_hook('git commit --dry-run -m "x"', repo, tmp)
    assert_allowed(rc, err, "--dry-run")
    print("PASS test_dry_run_commit_allows")


def test_malformed_stdin_fails_open():
    tmp = tempfile.mkdtemp(prefix="eos-rg-s-")
    env = dict(os.environ)
    env["EOS_SESSIONS_DIR"] = tmp
    proc = subprocess.run([sys.executable, HOOK], input="not json",
                          capture_output=True, text=True, env=env)
    assert proc.returncode == 0, "malformed stdin must exit 0, got %s" % proc.returncode
    print("PASS test_malformed_stdin_fails_open")


def test_non_repo_cwd_fails_open():
    tmp = tempfile.mkdtemp(prefix="eos-rg-s-")
    notrepo = tempfile.mkdtemp(prefix="eos-rg-notrepo-")
    rc, out, err = run_hook('git commit -m "x"', notrepo, tmp)
    assert_allowed(rc, err, "non-repo cwd")
    print("PASS test_non_repo_cwd_fails_open")


# --------------------------------------------------------------------------
# scope: what does / does not trigger the gate
# --------------------------------------------------------------------------

def test_non_risk_files_allow():
    repo, tmp = make_repo(), tempfile.mkdtemp(prefix="eos-rg-s-")
    for rel in ["src/ui/button.tsx", "README.md", "docs/notes.md",
                "memory/firm.md", "src/components/Card.css"]:
        write(repo, rel, "content for %s\n" % rel)
    git(repo, "add", "-A")
    rc, out, err = run_hook('git commit -m "ui work"', repo, tmp)
    assert_allowed(rc, err, "non-risk staged files")
    print("PASS test_non_risk_files_allow")


def test_each_risk_class_blocks():
    """Every class on the CLAUDE.md risk list must trip the gate on its own."""
    cases = [
        ("hooks/new-guard.py", "x = 1\n"),
        (".env.local", "A=1\n"),
        ("config/credentials.json", "{}\n"),
        ("hooks/confidential-terms.json", "{}\n"),
        ("settings.json", "{}\n"),
        ("CLAUDE.md", "# doctrine\n"),
        ("scheduled-tasks.json", "{}\n"),
        ("public/_headers", "/*\n  X: 1\n"),
        ("netlify.toml", "[build]\n"),
        ("src/finance/governor.ts", "export const DSCR = 1.25\n"),
        ("src/engine/noi_engine.py", "def noi(): return 0\n"),
        ("src/scoring/deal_score.ts", "export const score = 1\n"),
        ("src/capital_allocation.py", "x = 1\n"),
        ("src/benchmarking/replacement_cost.py", "x = 1\n"),
    ]
    for rel, body in cases:
        repo, tmp = make_repo(), tempfile.mkdtemp(prefix="eos-rg-s-")
        write(repo, rel, body)
        git(repo, "add", "-A")
        rc, out, err = run_hook('git commit -m "change"', repo, tmp)
        assert_blocked(rc, err, "risk class %s" % rel)
        assert rel.split("/")[-1] in err, (
            "block message must name the risk file %s, got %r" % (rel, err))
        shutil.rmtree(repo, ignore_errors=True)
    print("PASS test_each_risk_class_blocks (%d classes)" % len(cases))


def test_docs_under_hooks_do_not_trigger():
    """hooks/**/*.md is documentation, not enforcement code. CLAUDE.md itself
    stays in scope (covered by test_each_risk_class_blocks)."""
    repo, tmp = make_repo(), tempfile.mkdtemp(prefix="eos-rg-s-")
    write(repo, "hooks/README.md", "notes\n")
    write(repo, "hooks/docs/design.md", "notes\n")
    git(repo, "add", "-A")
    rc, out, err = run_hook('git commit -m "docs"', repo, tmp)
    assert_allowed(rc, err, "hooks docs")
    print("PASS test_docs_under_hooks_do_not_trigger")


def test_session_scratch_never_triggers():
    """hooks/sessions/** is gitignored scratch (tokens, counters, artifacts).
    It must never itself be treated as blast-radius code."""
    repo, tmp = make_repo(), tempfile.mkdtemp(prefix="eos-rg-s-")
    write(repo, "hooks/sessions/abc/code-edits.count", "3\n")
    git(repo, "add", "-Af")
    rc, out, err = run_hook('git commit -m "scratch"', repo, tmp)
    assert_allowed(rc, err, "session scratch")
    print("PASS test_session_scratch_never_triggers")


# --------------------------------------------------------------------------
# the core enforcement: artifact must be tied to THIS diff
# --------------------------------------------------------------------------

def test_risk_file_without_review_blocks():
    repo, tmp = make_repo(), tempfile.mkdtemp(prefix="eos-rg-s-")
    write(repo, "hooks/new-guard.py", "x = 1\n")
    git(repo, "add", "-A")
    rc, out, err = run_hook('git commit -m "add guard"', repo, tmp)
    assert_blocked(rc, err, "no review artifact")
    assert "--record" in err, "block must tell the operator how to record a review"
    print("PASS test_risk_file_without_review_blocks")


def test_valid_review_allows():
    repo, tmp = make_repo(), tempfile.mkdtemp(prefix="eos-rg-s-")
    write(repo, "hooks/new-guard.py", "x = 1\n")
    git(repo, "add", "-A")
    record_review(repo, tmp)
    rc, out, err = run_hook('git commit -m "add guard"', repo, tmp)
    assert_allowed(rc, err, "valid review artifact")
    print("PASS test_valid_review_allows")


def test_stale_review_blocks():
    """THE anti-theater test. A review recorded against one version of the diff
    must NOT satisfy the gate after the content changes. Without this the gate
    is decoration: review once, commit anything forever."""
    repo, tmp = make_repo(), tempfile.mkdtemp(prefix="eos-rg-s-")
    write(repo, "hooks/new-guard.py", "x = 1\n")
    git(repo, "add", "-A")
    record_review(repo, tmp)
    rc, out, err = run_hook('git commit -m "v1"', repo, tmp)
    assert_allowed(rc, err, "review matches v1")

    # Implementer keeps editing after the review.
    write(repo, "hooks/new-guard.py", "x = 1\nimport os  # sneaked in\n")
    git(repo, "add", "-A")
    rc, out, err = run_hook('git commit -m "v2"', repo, tmp)
    assert_blocked(rc, err, "stale review must not satisfy v2")
    print("PASS test_stale_review_blocks")


def test_review_of_one_file_does_not_cover_a_second():
    """Adding a SECOND risk file after the review invalidates it -- the key
    covers the whole reviewed set, not one path."""
    repo, tmp = make_repo(), tempfile.mkdtemp(prefix="eos-rg-s-")
    write(repo, "hooks/a.py", "a = 1\n")
    git(repo, "add", "-A")
    record_review(repo, tmp)
    write(repo, "hooks/b.py", "b = 1\n")
    git(repo, "add", "-A")
    rc, out, err = run_hook('git commit -m "a+b"', repo, tmp)
    assert_blocked(rc, err, "review of {a} must not cover {a,b}")
    print("PASS test_review_of_one_file_does_not_cover_a_second")


def test_rejected_verdict_blocks():
    repo, tmp = make_repo(), tempfile.mkdtemp(prefix="eos-rg-s-")
    write(repo, "hooks/new-guard.py", "x = 1\n")
    git(repo, "add", "-A")
    record_review(repo, tmp, verdict="rejected")
    rc, out, err = run_hook('git commit -m "x"', repo, tmp)
    assert_blocked(rc, err, "rejected verdict")
    print("PASS test_rejected_verdict_blocks")


def test_under_tier_reviewer_model_blocks():
    """Reviewer >= implementer. A review claimed by a cheap model is not a
    review this gate accepts.

    The artifact is hand-written rather than produced via --record, because
    --record ALSO refuses an under-tier model (test_record_cli_rejects_under_tier_model
    covers that). Two independent checks: the CLI refuses to write one, and the
    hook refuses to honour one that got written anyway. If only the CLI checked,
    the enforcement would live entirely in the cooperative path."""
    repo, tmp = make_repo(), tempfile.mkdtemp(prefix="eos-rg-s-")
    write(repo, "hooks/new-guard.py", "x = 1\n")
    git(repo, "add", "-A")
    rc, out, _ = run_cli(["--key"], repo, tmp)
    key = json.loads(out)["key"]
    art = os.path.join(tmp, "sess1", "reviews", key + ".json")
    os.makedirs(os.path.dirname(art), exist_ok=True)
    with open(art, "w", encoding="ascii") as fh:
        json.dump({"key": key, "session": "sess1", "verdict": "approved",
                   "reviewer_model": "claude-haiku-4-5-20251001",
                   "paths": ["hooks/new-guard.py"]}, fh)
    rc, out, err = run_hook('git commit -m "x"', repo, tmp)
    assert_blocked(rc, err, "under-tier reviewer model")
    assert "model" in err.lower(), "block must explain the tier failure, got %r" % err
    print("PASS test_under_tier_reviewer_model_blocks")


def test_corrupt_artifact_blocks():
    """Fail CLOSED on an unreadable artifact -- the gate's own internal errors
    fail open, but a malformed *grant* must never count as approval."""
    repo, tmp = make_repo(), tempfile.mkdtemp(prefix="eos-rg-s-")
    write(repo, "hooks/new-guard.py", "x = 1\n")
    git(repo, "add", "-A")
    art = record_review(repo, tmp)
    with open(art["artifact_path"], "w", encoding="ascii") as fh:
        fh.write("{ not json")
    rc, out, err = run_hook('git commit -m "x"', repo, tmp)
    assert_blocked(rc, err, "corrupt artifact")
    print("PASS test_corrupt_artifact_blocks")


def test_artifact_from_another_session_does_not_grant():
    repo, tmp = make_repo(), tempfile.mkdtemp(prefix="eos-rg-s-")
    write(repo, "hooks/new-guard.py", "x = 1\n")
    git(repo, "add", "-A")
    record_review(repo, tmp, session_id="othersess")
    rc, out, err = run_hook('git commit -m "x"', repo, tmp, session_id="sess1")
    assert_blocked(rc, err, "cross-session artifact")
    print("PASS test_artifact_from_another_session_does_not_grant")


# --------------------------------------------------------------------------
# the compound-command blind spot (the shape this fleet actually commits in)
# --------------------------------------------------------------------------

def test_pending_add_compound_command_blocks():
    """`git add hooks/x.py && git commit -m "..."` stages NOTHING at hook-fire
    time. A gate that only reads `git diff --cached` sees an empty set and
    allows -- exactly the blind spot that let 4 janitor commits through
    commit-provenance-guard on 2026-07-24."""
    repo, tmp = make_repo(), tempfile.mkdtemp(prefix="eos-rg-s-")
    write(repo, "hooks/new-guard.py", "x = 1\n")
    rc, out, err = run_hook(
        'git add hooks/new-guard.py && git commit -m "add guard"', repo, tmp)
    assert_blocked(rc, err, "compound add+commit")
    print("PASS test_pending_add_compound_command_blocks")


def test_pending_add_all_compound_blocks():
    repo, tmp = make_repo(), tempfile.mkdtemp(prefix="eos-rg-s-")
    write(repo, "hooks/new-guard.py", "x = 1\n")
    rc, out, err = run_hook('git add -A && git commit -m "sweep"', repo, tmp)
    assert_blocked(rc, err, "compound add -A + commit")
    print("PASS test_pending_add_all_compound_blocks")


def test_newline_separated_compound_blocks():
    """A bare newline is a statement separator too -- no && required."""
    repo, tmp = make_repo(), tempfile.mkdtemp(prefix="eos-rg-s-")
    write(repo, "hooks/new-guard.py", "x = 1\n")
    rc, out, err = run_hook(
        'git add hooks/new-guard.py\ngit commit -m "add guard"', repo, tmp)
    assert_blocked(rc, err, "newline-separated add+commit")
    print("PASS test_newline_separated_compound_blocks")


def test_commit_a_flag_sees_unstaged_risk_edit():
    repo, tmp = make_repo(), tempfile.mkdtemp(prefix="eos-rg-s-")
    write(repo, "hooks/new-guard.py", "x = 1\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "baseline guard")
    write(repo, "hooks/new-guard.py", "x = 2  # unstaged edit\n")
    rc, out, err = run_hook('git commit -am "tweak"', repo, tmp)
    assert_blocked(rc, err, "commit -a with unstaged risk edit")
    print("PASS test_commit_a_flag_sees_unstaged_risk_edit")


def test_explicit_pathspec_narrows_scope():
    """`git commit -- <path>` commits only that path; a dirty risk file NOT in
    the pathspec must not trip the gate."""
    repo, tmp = make_repo(), tempfile.mkdtemp(prefix="eos-rg-s-")
    write(repo, "src/ui/button.tsx", "export const B = 1\n")
    write(repo, "hooks/unrelated.py", "y = 1\n")
    git(repo, "add", "-A")
    rc, out, err = run_hook('git commit -m "ui only" -- src/ui/button.tsx', repo, tmp)
    assert_allowed(rc, err, "pathspec excludes the risk file")
    print("PASS test_explicit_pathspec_narrows_scope")


def test_git_c_repo_resolution():
    """`git -C <repo> commit` must be resolved against <repo>, not the cwd."""
    repo, tmp = make_repo(), tempfile.mkdtemp(prefix="eos-rg-s-")
    elsewhere = tempfile.mkdtemp(prefix="eos-rg-elsewhere-")
    write(repo, "hooks/new-guard.py", "x = 1\n")
    git(repo, "add", "-A")
    rc, out, err = run_hook('git -C "%s" commit -m "x"' % repo, elsewhere, tmp)
    assert_blocked(rc, err, "git -C repo resolution")
    print("PASS test_git_c_repo_resolution")


# --------------------------------------------------------------------------
# override token escape hatch (shared contract, session-scoped, single-use)
# --------------------------------------------------------------------------

def override_path(sessions_dir, session_id):
    return os.path.join(sessions_dir, session_id, "overrides", "allow-unreviewed-commit")


def write_override(sessions_dir, session_id, scope="unreviewed-blast-radius-commit",
                   session_field=None):
    path = override_path(sessions_dir, session_id)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="ascii", newline="\n") as fh:
        fh.write("scope: %s\nsession: %s\nreason: Gabriel approved in-turn\n"
                 % (scope, session_field or session_id))
    return path


def test_valid_override_token_allows_and_is_consumed():
    repo, tmp = make_repo(), tempfile.mkdtemp(prefix="eos-rg-s-")
    write(repo, "hooks/new-guard.py", "x = 1\n")
    git(repo, "add", "-A")
    path = write_override(tmp, "sess1")
    rc, out, err = run_hook('git commit -m "x"', repo, tmp)
    assert_allowed(rc, err, "valid override token")
    assert not os.path.exists(path), "single-use token must be consumed"
    rc, out, err = run_hook('git commit -m "x again"', repo, tmp)
    assert_blocked(rc, err, "consumed token must not grant twice")
    print("PASS test_valid_override_token_allows_and_is_consumed")


def test_wrong_scope_override_blocks():
    repo, tmp = make_repo(), tempfile.mkdtemp(prefix="eos-rg-s-")
    write(repo, "hooks/new-guard.py", "x = 1\n")
    git(repo, "add", "-A")
    write_override(tmp, "sess1", scope="website-deploy")
    rc, out, err = run_hook('git commit -m "x"', repo, tmp)
    assert_blocked(rc, err, "wrong-scope override")
    print("PASS test_wrong_scope_override_blocks")


def test_foreign_session_override_blocks():
    repo, tmp = make_repo(), tempfile.mkdtemp(prefix="eos-rg-s-")
    write(repo, "hooks/new-guard.py", "x = 1\n")
    git(repo, "add", "-A")
    write_override(tmp, "sess1", session_field="someoneelse")
    rc, out, err = run_hook('git commit -m "x"', repo, tmp)
    assert_blocked(rc, err, "session-mismatched override")
    print("PASS test_foreign_session_override_blocks")


def test_override_not_consumed_when_gate_would_not_block():
    """token_grants() CONSUMES. Evaluating it speculatively would burn a
    single-use approval on a commit that never needed one."""
    repo, tmp = make_repo(), tempfile.mkdtemp(prefix="eos-rg-s-")
    write(repo, "src/ui/button.tsx", "export const B = 1\n")
    git(repo, "add", "-A")
    path = write_override(tmp, "sess1")
    rc, out, err = run_hook('git commit -m "ui"', repo, tmp)
    assert_allowed(rc, err, "non-risk commit")
    assert os.path.exists(path), "token must NOT be burned by a commit that never needed it"
    print("PASS test_override_not_consumed_when_gate_would_not_block")


# --------------------------------------------------------------------------
# mode switch
# --------------------------------------------------------------------------

def test_warn_mode_never_blocks():
    repo, tmp = make_repo(), tempfile.mkdtemp(prefix="eos-rg-s-")
    write(repo, "hooks/new-guard.py", "x = 1\n")
    git(repo, "add", "-A")
    rc, out, err = run_hook('git commit -m "x"', repo, tmp,
                            extra_env={"EOS_REVIEW_GATE_MODE": "warn"})
    assert rc == 0, "warn mode must exit 0, got %s" % rc
    assert "eos-review-gate" in err, "warn mode must still say something, got %r" % err
    print("PASS test_warn_mode_never_blocks")


def test_off_mode_is_silent():
    repo, tmp = make_repo(), tempfile.mkdtemp(prefix="eos-rg-s-")
    write(repo, "hooks/new-guard.py", "x = 1\n")
    git(repo, "add", "-A")
    rc, out, err = run_hook('git commit -m "x"', repo, tmp,
                            extra_env={"EOS_REVIEW_GATE_MODE": "off"})
    assert rc == 0 and err.strip() == "", "off mode must be silent, got rc=%s %r" % (rc, err)
    print("PASS test_off_mode_is_silent")


def test_unknown_mode_defaults_to_block():
    """A typo in the mode env must not silently disable a security gate."""
    repo, tmp = make_repo(), tempfile.mkdtemp(prefix="eos-rg-s-")
    write(repo, "hooks/new-guard.py", "x = 1\n")
    git(repo, "add", "-A")
    rc, out, err = run_hook('git commit -m "x"', repo, tmp,
                            extra_env={"EOS_REVIEW_GATE_MODE": "blcok"})
    assert_blocked(rc, err, "unknown mode must default to block")
    print("PASS test_unknown_mode_defaults_to_block")


# --------------------------------------------------------------------------
# CLI surface (this is how a review is actually satisfiable)
# --------------------------------------------------------------------------

def test_key_cli_is_deterministic_and_content_sensitive():
    repo, tmp = make_repo(), tempfile.mkdtemp(prefix="eos-rg-s-")
    write(repo, "hooks/new-guard.py", "x = 1\n")
    git(repo, "add", "-A")
    rc, out, _ = run_cli(["--key"], repo, tmp)
    assert rc == 0, "--key must exit 0"
    first = json.loads(out)
    assert first["key"], "--key must emit a key"
    assert any(p.endswith("hooks/new-guard.py") for p in first["paths"]), first["paths"]

    rc, out, _ = run_cli(["--key"], repo, tmp)
    assert json.loads(out)["key"] == first["key"], "key must be stable for stable content"

    write(repo, "hooks/new-guard.py", "x = 2\n")
    git(repo, "add", "-A")
    rc, out, _ = run_cli(["--key"], repo, tmp)
    assert json.loads(out)["key"] != first["key"], "key must change when content changes"
    print("PASS test_key_cli_is_deterministic_and_content_sensitive")


def test_record_cli_rejects_under_tier_model():
    repo, tmp = make_repo(), tempfile.mkdtemp(prefix="eos-rg-s-")
    write(repo, "hooks/new-guard.py", "x = 1\n")
    git(repo, "add", "-A")
    rc, out, err = run_cli(
        ["--record", "--verdict", "approved", "--model", "claude-haiku-4-5-20251001"],
        repo, tmp)
    assert rc != 0, "--record must refuse an under-tier reviewer model"
    print("PASS test_record_cli_rejects_under_tier_model")


def test_record_cli_cmd_scopes_pathspec_commit_and_validates_against_main():
    """2026-07-26 fix: without --cmd, --record scores every at-risk path in the
    WHOLE working tree -- so in a busy shared checkout with an unrelated risk
    file staged elsewhere (another session's work), a review recorded for a
    pathspec-scoped commit could never validate against what main() actually
    gates on for that commit (main() correctly narrows via risk_files/
    candidate_paths). Passing --cmd makes the CLI compute the EXACT same
    scope+digest as main(), so the recorded review validates."""
    repo, tmp = make_repo(), tempfile.mkdtemp(prefix="eos-rg-s-")
    write(repo, "hooks/mine.py", "x = 1\n")
    git(repo, "add", "hooks/mine.py")
    write(repo, "hooks/theirs.py", "y = 1\n")  # another session's file, also staged
    git(repo, "add", "hooks/theirs.py")

    cmd = 'git commit -m "my scoped change" -- hooks/mine.py'

    # Whole-tree --record (no --cmd) sees BOTH files...
    rc, out, err = run_cli(
        ["--record", "--verdict", "approved", "--model", LADDER_TOP,
         "--notes", "n"], repo, tmp)
    assert rc == 0, "whole-tree --record failed: %s" % err
    assert set(json.loads(out)["paths"]) == {"hooks/mine.py", "hooks/theirs.py"}

    # ...and does NOT satisfy the narrower pathspec-scoped commit's gate.
    rc, out, err = run_hook(cmd, repo, tmp)
    assert_blocked(rc, err, "whole-tree review must not satisfy a narrower pathspec commit")

    # --cmd-scoped --record sees ONLY what that commit will land...
    rc, out, err = run_cli(
        ["--record", "--cmd", cmd, "--verdict", "approved", "--model", LADDER_TOP,
         "--notes", "n"], repo, tmp)
    assert rc == 0, "--cmd-scoped --record failed: %s" % err
    assert json.loads(out)["paths"] == ["hooks/mine.py"]

    # ...and NOW the pathspec-scoped commit is allowed.
    rc, out, err = run_hook(cmd, repo, tmp)
    assert_allowed(rc, err, "cmd-scoped review must satisfy the matching commit")
    print("PASS test_record_cli_cmd_scopes_pathspec_commit_and_validates_against_main")


def test_key_cli_cmd_matches_hook_key_for_all_flag_commit():
    """--cmd scoping must also match main() for a NON-pathspec commit shape
    (`-a`), not just the pathspec case -- scope_for_cmd is the single source
    of truth for both, so this is really pinning that main() and the CLI never
    diverge for any cmd shape, not just the one that motivated the fix. The
    unrelated file stays UNTRACKED (never staged): -a only re-stages already-
    TRACKED modified files, so an untracked file is correctly excluded from
    this commit regardless of --cmd scoping -- this is not the same "staged
    but unrelated" scenario the pathspec test above covers."""
    repo, tmp = make_repo(), tempfile.mkdtemp(prefix="eos-rg-s-")
    write(repo, "hooks/tracked.py", "x = 1\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "baseline")
    write(repo, "hooks/tracked.py", "x = 2  # unstaged edit\n")
    write(repo, "hooks/other-live-session.py", "z = 1\n")  # untracked, unrelated

    cmd = 'git commit -am "tweak"'
    rc, out, err = run_cli(["--key", "--cmd", cmd], repo, tmp)
    assert rc == 0, err
    cmd_scoped = json.loads(out)
    assert cmd_scoped["paths"] == ["hooks/tracked.py"], (
        "-a must see the unstaged tracked edit but not the untracked, "
        "never-staged unrelated file: %r" % cmd_scoped["paths"])

    rc, out, err = run_cli(
        ["--record", "--cmd", cmd, "--verdict", "approved", "--model", LADDER_TOP,
         "--notes", "n"], repo, tmp)
    assert rc == 0, err
    rc, out, err = run_hook(cmd, repo, tmp)
    assert_allowed(rc, err, "cmd-scoped review of an -a commit must satisfy main()")
    print("PASS test_key_cli_cmd_matches_hook_key_for_all_flag_commit")


def test_directory_pathspec_does_not_collapse_to_constant_key():
    """2026-07-26 adversarial-review finding F1 (CRITICAL). `_content_digest`
    on a DIRECTORY path hits OSError and returns the constant "DELETED" --
    treating a directory pathspec argument as one literal candidate path made
    review_key() content-independent: a review recorded once for
    `git commit -- hooks/` validated FOREVER regardless of what any file
    under hooks/ actually contained. Confirmed reproducible pre-fix; this
    pins the fix -- the key MUST change when the directory's contents change,
    and a NEW file added under the directory MUST also change it."""
    repo, tmp = make_repo(), tempfile.mkdtemp(prefix="eos-rg-s-")
    write(repo, "hooks/a.py", "SAFE = 1\n")
    git(repo, "add", "hooks/a.py")
    cmd = 'git commit -m "scoped" -- hooks/'

    rc, out, err = run_cli(["--key", "--cmd", cmd], repo, tmp)
    assert rc == 0, err
    first = json.loads(out)
    assert first["paths"] == ["hooks/a.py"], (
        "directory pathspec must expand to real files, not stay a literal "
        "'hooks' candidate: %r" % first["paths"])
    key1 = first["key"]

    write(repo, "hooks/a.py", "BACKDOOR = True\n")
    git(repo, "add", "hooks/a.py")
    rc, out, err = run_cli(["--key", "--cmd", cmd], repo, tmp)
    key2 = json.loads(out)["key"]
    assert key2 != key1, "key must change when the directory's content changes"

    write(repo, "hooks/b.py", "NEW_RISK = True\n")
    git(repo, "add", "hooks/b.py")
    rc, out, err = run_cli(["--key", "--cmd", cmd], repo, tmp)
    third = json.loads(out)
    assert set(third["paths"]) == {"hooks/a.py", "hooks/b.py"}
    assert third["key"] != key2, "key must change when a new file is added under the directory"

    # A review recorded for the directory pathspec at the earlier (2-file) state
    # must not satisfy the live hook for the current (2-file, different content) commit.
    rc, out, err = run_cli(
        ["--record", "--cmd", cmd, "--verdict", "approved", "--model", LADDER_TOP,
         "--notes", "n"], repo, tmp)
    assert rc == 0, err
    rc, out, err = run_hook(cmd, repo, tmp)
    assert_allowed(rc, err, "review matching the CURRENT directory content must satisfy the commit")

    # Now mutate a file WITHOUT re-recording -- the stale review must not satisfy it.
    write(repo, "hooks/a.py", "BACKDOOR 2 = True\n")
    git(repo, "add", "hooks/a.py")
    rc, out, err = run_hook(cmd, repo, tmp)
    assert_blocked(rc, err, "mutating a file under the reviewed directory must invalidate the review")
    print("PASS test_directory_pathspec_does_not_collapse_to_constant_key")


def test_bare_dot_pathspec_still_gates():
    """2026-07-26 adversarial-review finding F2 (HIGH, same root cause as F1).
    `git commit -- .` resolved to the repo-root literal path "." via _rel(),
    whose risk_reason() is None (it is not itself a named risk file) --
    risk_files() came back EMPTY and the gate allowed a real hooks/**
    landing with NO review at all, not even an unsatisfiable one. Confirmed
    reproducible pre-fix (git show --name-only HEAD showed the risk file
    actually landed). Also exercises './' and ':/' (git's other repo-root
    pathspec forms) and, per the ROUND-2 follow-up REFUTE pass, the forms
    the FIRST fix attempt (an isdir-or-hardcoded-string predicate) still
    missed: a shell glob ('*'), and git's own pathspec-magic long/short
    forms (':(top)' == ':/' spelled out, ':(glob)hooks/**', ':(icase)HOOKS')
    -- each confirmed pre-round-2-fix to allow (rc=0) with risk_files() empty."""
    for root_form in (".", "./", ":/", ":", "*",
                      ":(top)", ":(glob)hooks/**", ":(icase)HOOKS"):
        repo, tmp = make_repo(), tempfile.mkdtemp(prefix="eos-rg-s-")
        write(repo, "hooks/new-guard.py", "x = 1\n")
        git(repo, "add", "-A")
        rc, out, err = run_hook('git commit -m "x" -- \'%s\'' % root_form, repo, tmp)
        assert_blocked(rc, err, "pathspec %r must still gate" % root_form)
    print("PASS test_bare_dot_pathspec_still_gates")


def test_glob_pathspec_key_is_not_a_constant():
    """ROUND-2 REFUTE finding R2: `git commit -- 'hooks/*.py'` (a glob, not a
    bare directory) still hit the SAME literal-path fast path as the
    unfixed-round-1 code, because round 1's predicate only special-cased
    os.path.isdir() and five hardcoded strings -- a glob is neither. Content
    digest on the non-existent literal path "hooks/*.py" returned the
    constant DELETED, exactly reproducing F1 for any glob pathspec."""
    repo, tmp = make_repo(), tempfile.mkdtemp(prefix="eos-rg-s-")
    write(repo, "hooks/a.py", "SAFE = 1\n")
    git(repo, "add", "hooks/a.py")
    cmd = "git commit -m x -- 'hooks/*.py'"
    rc, out, err = run_cli(["--key", "--cmd", cmd], repo, tmp)
    assert rc == 0, err
    first = json.loads(out)
    assert first["paths"] == ["hooks/a.py"], first["paths"]
    key1 = first["key"]
    write(repo, "hooks/a.py", "BACKDOOR = True\n")
    git(repo, "add", "hooks/a.py")
    rc, out, err = run_cli(["--key", "--cmd", cmd], repo, tmp)
    key2 = json.loads(out)["key"]
    assert key2 != key1, "glob pathspec key must not be a content-independent constant"
    print("PASS test_glob_pathspec_key_is_not_a_constant")


def test_deleted_directory_pathspec_still_resolves_via_git():
    """ROUND-2 REFUTE finding R2 (deleted-dir variant): round 1's predicate
    used os.path.isdir(), which is False for a directory whose last tracked
    file was just `git rm`'d -- even though `git diff --cached -- <it>`
    still correctly reports the deletion. Round 1 fell through to the
    literal-path fast path, producing the same constant DELETED digest."""
    repo, tmp = make_repo(), tempfile.mkdtemp(prefix="eos-rg-s-")
    write(repo, "hooks/old/critical-guard.py", "GUARD = 1\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "baseline")
    git(repo, "rm", "-q", "-r", "hooks/old")
    cmd = "git commit -m x -- hooks/old"
    rc, out, err = run_cli(["--key", "--cmd", cmd], repo, tmp)
    assert rc == 0, err
    rels = json.loads(out)["paths"]
    assert rels == ["hooks/old/critical-guard.py"], (
        "deleted-directory pathspec must resolve to the real deleted path, not "
        "a literal 'hooks/old' candidate: %r" % rels)
    print("PASS test_deleted_directory_pathspec_still_resolves_via_git")


def test_untracked_file_under_directory_pathspec_is_covered():
    """ROUND-2 REFUTE finding R3: pathspec_arg_paths' directory expansion
    unioned staged + unstaged-tracked-modified + tracked, but NOT untracked
    (ls-files --others --exclude-standard) -- so a review recorded for
    `-- hooks/` before a brand-new untracked file existed under it did not
    account for that file, yet `git add hooks/ && git commit -- hooks/`
    (this fleet's own documented committing shape) lands it anyway."""
    repo, tmp = make_repo(), tempfile.mkdtemp(prefix="eos-rg-s-")
    write(repo, "hooks/a.py", "SAFE = 1\n")
    git(repo, "add", "hooks/a.py")
    record_cmd = "git commit -m x -- hooks/"
    rc, out, err = run_cli(
        ["--record", "--cmd", record_cmd, "--verdict", "approved",
         "--model", LADDER_TOP, "--notes", "n"], repo, tmp)
    assert rc == 0, err

    write(repo, "hooks/evil.py", "EVIL = True\n")  # brand-new, untracked at record time
    rc, out, err = run_hook(
        'git add hooks/ && git commit -m x -- hooks/', repo, tmp)
    assert_blocked(rc, err,
        "a new untracked file under the reviewed directory must invalidate the review")
    print("PASS test_untracked_file_under_directory_pathspec_is_covered")


def test_record_cli_refuses_when_nothing_is_at_risk():
    repo, tmp = make_repo(), tempfile.mkdtemp(prefix="eos-rg-s-")
    write(repo, "src/ui/button.tsx", "export const B = 1\n")
    git(repo, "add", "-A")
    rc, out, err = run_cli(
        ["--record", "--verdict", "approved", "--model", LADDER_TOP], repo, tmp)
    assert rc != 0, "--record must refuse when there is no risk diff to review"
    print("PASS test_record_cli_refuses_when_nothing_is_at_risk")


# --------------------------------------------------------------------------
# 2026-07-24 independent-review findings (M1-M4, m5-m7, n8) -- each test here
# is the closure proof for one confirmed PoC from the mandatory review this
# gate itself required before it could be merged. See
# hooks/eos-review-gate.py's module docstring (PROVENANCE FIX) for the M1
# narrative.
# --------------------------------------------------------------------------

def test_index_vs_worktree_divergence_is_not_satisfied_by_worktree_review():
    """M1. Stage v1, get it reviewed (CLI reads the working tree, which at
    record time still equals v1), THEN edit the working tree to v2 WITHOUT
    re-staging. A bare `git commit` lands v1 (the index), not v2 -- so the
    hook must key on v1 and find the v1 review a MATCH (this is now the
    CORRECT outcome: v1 really is what's reviewed and what lands).
    Confirms the fix doesn't just move WHERE it breaks -- it must actually
    make the gate track committed reality, not just working-tree state."""
    repo, tmp = make_repo(), tempfile.mkdtemp(prefix="eos-rg-s-")
    write(repo, "hooks/g.py", "v1\n")
    git(repo, "add", "-A")
    record_review(repo, tmp)  # reviews v1 (working tree == index right now)
    write(repo, "hooks/g.py", "v2 unstaged edit\n")  # index still v1
    rc, out, err = run_hook('git commit -m "x"', repo, tmp)
    assert_allowed(rc, err, "plain commit lands v1, which was genuinely reviewed")
    print("PASS test_index_vs_worktree_divergence_is_not_satisfied_by_worktree_review")


def test_index_vs_worktree_divergence_blocks_when_review_covers_the_edit():
    """M1, the actual PoC 1 shape. Stage v1, THEN edit to v2 and record a
    review AFTER the edit (so the CLI captures v2, not v1). A bare `git
    commit` still lands v1 (the index) -- the review covered bytes that will
    NEVER be committed, so the gate must block."""
    repo, tmp = make_repo(), tempfile.mkdtemp(prefix="eos-rg-s-")
    write(repo, "hooks/g.py", "v1 staged, will be committed\n")
    git(repo, "add", "-A")
    write(repo, "hooks/g.py", "v2 working tree, what the reviewer sees\n")
    record_review(repo, tmp)  # keys on v2 (CLI reads working tree)
    rc, out, err = run_hook('git commit -m "x"', repo, tmp)  # lands v1
    assert_blocked(rc, err, "review of v2 must not authorize landing v1")
    print("PASS test_index_vs_worktree_divergence_blocks_when_review_covers_the_edit")


def test_index_and_worktree_digests_match_under_autocrlf_normalization():
    """B2 (discovered against the LIVE checkout during the actual merge --
    neither review round's fresh temp repos ever round-tripped a file through
    a real git CHECKOUT, so core.autocrlf never got a chance to convert
    LF->CRLF on disk; this suite's own write() helper always writes explicit
    LF). This machine runs core.autocrlf=true. Hashing raw `open(path,'rb')`
    disk bytes for the working-tree digest while hashing git's own
    LF-normalized index blob for the staged digest meant the two digests
    differed for EVERY text file under autocrlf, even for byte-for-byte
    logically identical content -- making the gate permanently unsatisfiable
    via --record for a plain (separately-staged, then bare `git commit`)
    commit shape. Fixed by routing BOTH digests through git's own blob
    object-id computation (`git hash-object` for the working tree,
    `git rev-parse :path` for the index), which normalize identically."""
    repo, tmp = make_repo(), tempfile.mkdtemp(prefix="eos-rg-s-")
    git(repo, "config", "core.autocrlf", "true")
    g = os.path.join(repo, "hooks", "g.py")
    write(repo, "hooks/g.py", "line one\nline two\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "baseline")
    # autocrlf only rewrites the working tree on an actual CHECKOUT -- a plain
    # `git add` merely WARNS that it will convert "the next time Git touches
    # it". Force it: delete and re-materialize from the object database.
    os.remove(g)
    git(repo, "checkout", "HEAD", "--", "hooks/g.py")
    with open(g, "rb") as fh:
        disk_bytes = fh.read()
    assert b"\r\n" in disk_bytes, (
        "test setup must actually trigger autocrlf CRLF conversion on disk")
    write(repo, "hooks/g.py", "line one\nline two\nline three\n")
    git(repo, "add", "-A")
    os.remove(g)
    git(repo, "checkout", "--", "hooks/g.py")  # re-materialize the STAGED version, CRLF
    with open(g, "rb") as fh:
        crlf_bytes = fh.read()
    assert b"\r\n" in crlf_bytes
    record_review(repo, tmp)  # CLI keys via the CRLF-on-disk working-tree bytes
    rc, out, err = run_hook('git commit -m "x"', repo, tmp)  # hook keys via INDEX
    assert_allowed(rc, err,
        "CRLF-normalized content must key identically between CLI (worktree) "
        "and hook (index) -- autocrlf must not defeat the gate")
    print("PASS test_index_and_worktree_digests_match_under_autocrlf_normalization")


def test_index_vs_worktree_divergence_blocks_for_mixed_case_path():
    """B1 (second review round). `_index_digest` queried git with the
    LOWERCASED rel path; `git show :path` matches path text LITERALLY even
    under Windows' core.ignorecase=true, so a mixed-case index entry (the
    real-world case: CLAUDE.md) silently missed and fell back to the
    working-tree digest -- reintroducing M1's exact bug for the flagship
    risk file. Same shape as
    test_index_vs_worktree_divergence_blocks_when_review_covers_the_edit but
    with a mixed-case filename, which is precisely what the all-lowercase
    "hooks/g.py" fixtures elsewhere in this suite cannot catch."""
    repo, tmp = make_repo(), tempfile.mkdtemp(prefix="eos-rg-s-")
    write(repo, "CLAUDE.md", "v1 staged, will be committed\n")
    git(repo, "add", "-A")
    write(repo, "CLAUDE.md", "v2 working tree, what the reviewer sees\n")
    record_review(repo, tmp)  # keys on v2 (CLI reads working tree)
    rc, out, err = run_hook('git commit -m "x"', repo, tmp)  # lands v1
    assert_blocked(rc, err, "mixed-case CLAUDE.md: review of v2 must not authorize landing v1")
    print("PASS test_index_vs_worktree_divergence_blocks_for_mixed_case_path")


def test_all_flag_reviews_worktree_content_correctly():
    """M1 counterpart: `-a` re-stages from the working tree, so a review of
    the CURRENT working tree DOES cover what `commit -a` will land, even with
    a divergent (older) index."""
    repo, tmp = make_repo(), tempfile.mkdtemp(prefix="eos-rg-s-")
    write(repo, "hooks/g.py", "v1\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "baseline")
    write(repo, "hooks/g.py", "v2\n")  # unstaged; index still has v1
    record_review(repo, tmp)  # CLI reviews v2 (working tree)
    rc, out, err = run_hook('git commit -am "x"', repo, tmp)  # -a lands v2
    assert_allowed(rc, err, "commit -a lands the reviewed working-tree content")
    print("PASS test_all_flag_reviews_worktree_content_correctly")


def test_chained_trailing_dashdash_does_not_hijack_pathspec():
    """M2. A `--` belonging to a DIFFERENT chained command must not be read as
    this commit's pathspec and used to discard the real staged risk file."""
    repo, tmp = make_repo(), tempfile.mkdtemp(prefix="eos-rg-s-")
    write(repo, "hooks/g.py", "x = 1\n")
    git(repo, "add", "-A")
    rc, out, err = run_hook(
        'git commit -m "x" && git log -1 --format=%s -- hooks/', repo, tmp)
    assert_blocked(rc, err, "chained `-- pathspec` in a later command")
    print("PASS test_chained_trailing_dashdash_does_not_hijack_pathspec")


def test_own_pathspec_still_narrows_correctly():
    """M2 regression guard: the commit's OWN `-- pathspec` must still work
    exactly as before -- only a FOREIGN segment's `--` should stop counting."""
    repo, tmp = make_repo(), tempfile.mkdtemp(prefix="eos-rg-s-")
    write(repo, "src/ui/button.tsx", "export const B = 1\n")
    write(repo, "hooks/unrelated.py", "y = 1\n")
    git(repo, "add", "-A")
    rc, out, err = run_hook('git commit -m "ui only" -- src/ui/button.tsx', repo, tmp)
    assert_allowed(rc, err, "own pathspec excludes the risk file")
    print("PASS test_own_pathspec_still_narrows_correctly")


def test_commit_message_mentioning_dry_run_still_gates():
    """m5. `--dry-run` must be recognized as a real FLAG of the commit
    segment, not a substring anywhere in the command -- a commit message that
    merely mentions the text "--dry-run" must not blind the gate."""
    repo, tmp = make_repo(), tempfile.mkdtemp(prefix="eos-rg-s-")
    write(repo, "hooks/g.py", "x = 1\n")
    git(repo, "add", "-A")
    rc, out, err = run_hook(
        'git commit -m "docs: explain the --dry-run flag"', repo, tmp)
    assert_blocked(rc, err, "commit message mentioning --dry-run")
    print("PASS test_commit_message_mentioning_dry_run_still_gates")


def test_react_hooks_directory_not_falsely_flagged():
    """M4. `src/hooks/useAuth.ts` is idiomatic React, not this repo's
    hooks/** enforcement code -- only a REPO-ROOT hooks/ path is in scope."""
    repo, tmp = make_repo(), tempfile.mkdtemp(prefix="eos-rg-s-")
    write(repo, "src/hooks/useAuth.ts", "export const useAuth = () => null\n")
    git(repo, "add", "-A")
    rc, out, err = run_hook('git commit -m "feat: auth hook"', repo, tmp)
    assert_allowed(rc, err, "src/hooks/ (React convention) must not trigger the gate")
    print("PASS test_react_hooks_directory_not_falsely_flagged")


def test_root_hooks_directory_still_flagged():
    """M4 regression guard: the repo's OWN top-level hooks/ must still gate."""
    repo, tmp = make_repo(), tempfile.mkdtemp(prefix="eos-rg-s-")
    write(repo, "hooks/new-guard.py", "x = 1\n")
    git(repo, "add", "-A")
    rc, out, err = run_hook('git commit -m "x"', repo, tmp)
    assert_blocked(rc, err, "root hooks/ must still gate")
    print("PASS test_root_hooks_directory_still_flagged")


def test_noise_filter_not_falsely_flagged_as_financial():
    """m6. "noi" as a bare substring matched "noise" -- a financial token must
    require a word boundary, not just containment."""
    repo, tmp = make_repo(), tempfile.mkdtemp(prefix="eos-rg-s-")
    write(repo, "src/audio/noise_filter.py", "def denoise(): pass\n")
    git(repo, "add", "-A")
    rc, out, err = run_hook('git commit -m "x"', repo, tmp)
    assert_allowed(rc, err, "noise_filter.py must not be flagged as financial")
    print("PASS test_noise_filter_not_falsely_flagged_as_financial")


def test_noi_engine_still_flagged_as_financial():
    """m6 regression guard: a genuine NOI engine path must still gate --
    the boundary fix must not blind real financial-decision code."""
    repo, tmp = make_repo(), tempfile.mkdtemp(prefix="eos-rg-s-")
    write(repo, "src/engine/noi_engine.py", "def noi(): return 0\n")
    git(repo, "add", "-A")
    rc, out, err = run_hook('git commit -m "x"', repo, tmp)
    assert_blocked(rc, err, "noi_engine.py must still be flagged as financial")
    print("PASS test_noi_engine_still_flagged_as_financial")


def test_capital_allocation_prefix_still_flagged():
    """m6 regression guard: intentional PREFIX tokens like "capital_alloc"
    (matching capital_allocation.py, capital_allocator.py, ...) must not be
    broken by the new word-boundary handling -- only the short, genuinely
    collision-prone fragments (noi/irr/ltv/engine) got boundary-restricted."""
    repo, tmp = make_repo(), tempfile.mkdtemp(prefix="eos-rg-s-")
    write(repo, "src/capital_allocation.py", "x = 1\n")
    git(repo, "add", "-A")
    rc, out, err = run_hook('git commit -m "x"', repo, tmp)
    assert_blocked(rc, err, "capital_allocation.py must still be flagged")
    print("PASS test_capital_allocation_prefix_still_flagged")


def test_search_engine_ui_not_falsely_flagged():
    """m6 regression guard: "engine" as an ordinary English word (search
    engine, template engine) must not trigger the gate -- this is the false
    positive the ORIGINAL delimited-substring design already avoided; the
    boundary-token consolidation must preserve that, not regress it."""
    repo, tmp = make_repo(), tempfile.mkdtemp(prefix="eos-rg-s-")
    write(repo, "src/hooks/useSearchEngine.ts", "export const x = 1\n")
    git(repo, "add", "-A")
    rc, out, err = run_hook('git commit -m "x"', repo, tmp)
    assert_allowed(rc, err, "useSearchEngine.ts must not be flagged as financial")
    print("PASS test_search_engine_ui_not_falsely_flagged")


def test_compound_add_commit_is_satisfiable_via_record():
    """M3. The fleet's own default committing shape -- `git add <untracked> &&
    git commit` -- must be satisfiable through --record, not just blockable
    by the hook. An untracked (never staged) risk file is the exact case that
    made --record refuse with "nothing at risk" while the hook still blocked:
    an unsatisfiable loop with no exit but the override token."""
    repo, tmp = make_repo(), tempfile.mkdtemp(prefix="eos-rg-s-")
    write(repo, "hooks/g.py", "x = 1\n")  # untracked, never staged
    record_review(repo, tmp)  # must NOT refuse "nothing at risk"
    rc, out, err = run_hook(
        'git add hooks/g.py && git commit -m "x"', repo, tmp)
    assert_allowed(rc, err, "compound add+commit of an untracked risk file, reviewed")
    print("PASS test_compound_add_commit_is_satisfiable_via_record")


def test_warn_mode_does_not_consume_override_token():
    """m7. token_grants() CONSUMES a single-use token. Under warn mode the
    gate never blocks, so it must never even LOOK at the token -- doing so
    silently burns Gabriel's approval on a commit that didn't need one, with
    no warning that it happened."""
    repo, tmp = make_repo(), tempfile.mkdtemp(prefix="eos-rg-s-")
    write(repo, "hooks/g.py", "x = 1\n")
    git(repo, "add", "-A")
    path = write_override(tmp, "sess1")
    rc, out, err = run_hook('git commit -m "x"', repo, tmp,
                            extra_env={"EOS_REVIEW_GATE_MODE": "warn"})
    assert rc == 0, "warn mode must exit 0, got %s" % rc
    assert os.path.exists(path), (
        "warn mode must NOT consume the override token -- it never needed one")
    print("PASS test_warn_mode_does_not_consume_override_token")


TESTS = [v for k, v in sorted(globals().items()) if k.startswith("test_")]

if __name__ == "__main__":
    failures = 0
    for t in TESTS:
        try:
            t()
        except AssertionError as exc:
            failures += 1
            print("FAIL %s: %s" % (t.__name__, exc))
    if failures:
        print("%d REVIEW-GATE TEST(S) FAILED" % failures)
        sys.exit(1)
    print("ALL REVIEW-GATE TESTS PASS (%d)" % len(TESTS))
