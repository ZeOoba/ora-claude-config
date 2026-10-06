"""Tests for eos-review-gate.py PreToolUse hook (matcher: Bash).

Run: python test-eos-review-gate.py
Stdlib only. ASCII-only. Self-contained -- builds REAL git repos in temp dirs
(not string fixtures), because every load-bearing decision this gate makes is a
question only git can answer: what a compound `git add X && git commit` would
capture, and what the working-tree content of a risk path actually hashes to.

Shape follows hooks/tests/test-eos-plan-gate.py.
"""

import concurrent.futures
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time

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

# Shared repo fixture (open-items-tracker.md#OI-061). Import position is NOT load-bearing
# -- gitfixture builds its template LAZILY on first use, which is always after the GIT_*
# scrub above has run at module level. (An earlier version of this comment claimed the
# import had to follow the scrub; that was wrong, and test-memory-orphan-link-guard.py
# imports it before its own scrub, safely.) It WOULD become load-bearing if gitfixture
# ever built a template at import time -- so if you add eager construction there, both
# call sites need re-checking.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"))
import gitfixture  # noqa: E402

LADDER_TOP = "claude-opus-5-5"  # must match eos-review-gate.REVIEWER_MODEL_LADDER[0]


# --------------------------------------------------------------------------
# harness
# --------------------------------------------------------------------------

def git(repo, *args):
    proc = subprocess.run(["git", "-C", repo] + list(args),
                          capture_output=True, text=True)
    assert proc.returncode == 0, "git %s failed: %s" % (args, proc.stderr)
    return proc.stdout


def make_repo():
    """A real git repo with one committed non-risk file.

    Delegates to the shared template-and-copy fixture (OI-061). Byte-for-byte the same
    repo shape as the hand-rolled version this replaces -- init + user config + a
    committed README.md "hello\\n" -- but the ~5 subprocess spawns are paid ONCE per
    process instead of on all 73 runtime calls in this file. That was 365 of this
    file's 559 spawns, and the reason it ran 141.7s under load against a 90s budget.
    """
    return gitfixture.repo_with_commit(files={"README.md": "hello\n"},
                                       message="init",
                                       prefix="eos-rg-repo-",
                                       encoding="ascii")  # matches this file's write()


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
    # EOS_REVIEW_MODELS may be set ambiently (settings.json's top-level "env"
    # block, per the module docstring) -- scrub it so an operator's real
    # override doesn't silently change which model tier THIS suite tests
    # against. A test that wants it set opts in via extra_env below.
    env.pop("EOS_REVIEW_MODELS", None)
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


def run_cli(args, repo, sessions_dir, session_id="sess1", extra_env=None):
    env = dict(os.environ)
    env.pop("EOS_REVIEW_MODELS", None)  # see run_hook's comment above
    env["EOS_SESSIONS_DIR"] = sessions_dir
    env["ORA_OVERRIDE_SESSIONS_DIR"] = sessions_dir
    env["CLAUDE_CODE_SESSION_ID"] = session_id
    if extra_env:
        env.update(extra_env)
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


def _record_line(err):
    """The line of the block message that hands the operator the --record command."""
    return next((l for l in err.splitlines() if "--record" in l and "--verdict" in l),
                "")


def _config_write_guard_verdict(command):
    """Run config-write-guard.py over `command` and return 'BLOCKED' or 'allowed'.

    CROSS-GUARD, deliberately: the defect being pinned is not inside this gate at
    all, it is that this gate's remediation command is refused by the OTHER gate.
    Only a real run of that guard can prove the printed command is usable. Isolated
    via the guard's documented test seams, so it never reads the live tree.

    NOT THE LOAD-BEARING ASSERTION, and it cannot be (independent review, 2026-08-12,
    finding 82). Seaming ORA_CONFIG_GUARD_ROOT to a temp dir is what keeps this test
    off the live tree, but it also means the guard classifies drive-qualified tokens
    against THAT root -- so a regression back to an absolute LIVE hooks/ path would
    still come back "allowed" here. The structural `":/" not in line` check in the
    caller is what actually pins that; this run proves the shape end-to-end against a
    real guard process. Do not delete the structural check as redundant with this.
    The early return below is the same class: a checkout without the guard silently
    skips the cross-check, which is acceptable only because the caller's own
    assertions still run."""
    guard = os.path.join(HERE, "config-write-guard.py")
    if not os.path.isfile(guard):
        return "allowed"  # guard absent from this checkout -- nothing to prove
    env = dict(os.environ)
    env["ORA_CONFIG_GUARD_ROOT"] = tempfile.mkdtemp(prefix="eos-rg-cwg-root-")
    env["ORA_OVERRIDE_SESSIONS_DIR"] = tempfile.mkdtemp(prefix="eos-rg-cwg-sess-")
    env["ORA_CHIP_CLAIMS_LOG"] = os.path.join(
        tempfile.mkdtemp(prefix="eos-rg-cwg-log-"), "chip-claims.log")
    proc = subprocess.run(
        [sys.executable, guard], capture_output=True, text=True, env=env,
        input=json.dumps({"session_id": "s" * 32, "tool_name": "Bash",
                          "tool_input": {"command": command}}))
    return "BLOCKED" if proc.returncode == 2 else "allowed"


def test_record_hint_is_a_command_the_write_guard_permits():
    # WHY (2026-08-12, hit live). This gate printed its --record command spelled with
    # os.path.abspath(__file__) -- i.e. the LIVE C:/Users/Owner/.claude/hooks/ path.
    # config-write-guard's matcher is "write indicator + governance-path marker
    # anywhere in the command", and ">" matches inside an ASCII arrow, which review
    # prose is full of ("199/204 -> 204/204"). So following this gate's own
    # instructions verbatim was blocked by that guard, whose only named exit was
    # minting a 60-min multi-use governance-WIDE token to satisfy one artifact
    # write. Same class as the `--model ` -> "del " deadlock tool_call_paths.py
    # word-anchored on 2026-08-03: a false positive that forces a strictly broader
    # privilege. The repo-relative spelling carries no governance marker at all, so
    # it is not gated -- and the tool resolves its artifact path absolutely, so the
    # review still lands in the live hooks/sessions/ tree either way.
    repo, tmp = make_repo(), tempfile.mkdtemp(prefix="eos-rg-s-")
    write(repo, "hooks/eos-review-gate.py", "# this repo carries its own copy\n")
    write(repo, "hooks/new-guard.py", "x = 1\n")
    git(repo, "add", "-A")
    rc, out, err = run_hook('git commit -m "add guard"', repo, tmp)
    assert_blocked(rc, err, "no review artifact")

    line = _record_line(err)
    assert line, "block message must still hand over a --record command: %r" % err
    assert "hooks/eos-review-gate.py" in line, (
        "record hint must still name the tool: %r" % line)
    # Structural, not a spelling match: ANY drive-qualified path on this line puts a
    # governance marker back into the command the operator is told to run.
    assert ":/" not in line and ":\\" not in line, (
        "record hint must not carry an absolute path when the repo has its own "
        "copy: %r" % line)

    # END-TO-END: the printed command, with the arrow that caused the live block,
    # must actually clear config-write-guard.
    armed = line.strip().replace("<what was reviewed and found>", "199/204 -> 204/204")
    armed = armed.replace("<pinned-id>", LADDER_TOP)
    verdict = _config_write_guard_verdict(armed)
    assert verdict == "allowed", (
        "the record command this gate prints is refused by config-write-guard: "
        "%r -> %s" % (armed, verdict))

    # And the operator is warned about the indicator, since the fallback spelling
    # below (and any hand-typed absolute path) still carries it.
    assert "arrow" in err, (
        "block message must warn that an ASCII arrow in --notes reads as a "
        "redirect: %r" % err)
    print("PASS test_record_hint_is_a_command_the_write_guard_permits")


def test_record_hint_falls_back_to_the_absolute_path_off_repo():
    # A repo that does NOT carry its own copy of the gate (any non-~/.claude repo
    # with financial-decision code) has no relative spelling to offer, so the
    # absolute path is still correct there -- and the arrow warning is what keeps
    # that form usable.
    repo, tmp = make_repo(), tempfile.mkdtemp(prefix="eos-rg-s-")
    write(repo, "hooks/new-guard.py", "x = 1\n")
    git(repo, "add", "-A")
    rc, out, err = run_hook('git commit -m "add guard"', repo, tmp)
    assert_blocked(rc, err, "no review artifact")
    line = _record_line(err)
    assert "eos-review-gate.py" in line and (":/" in line or ":\\" in line), (
        "off-repo fallback must still print a runnable absolute path: %r" % line)
    assert "arrow" in err, "the arrow warning must be present in the fallback too"
    print("PASS test_record_hint_falls_back_to_the_absolute_path_off_repo")


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


def test_record_cli_accepts_opus_5_5():
    """2026-09-22: a genuine Opus 5.5 reviewer (claude-opus-5-5, above claude-opus-5)
    was refused because the ladder predated its release. Opus 5.5, including a
    context-tagged self-report, must record."""
    for mid in ("claude-opus-5-5", "claude-opus-5-5[1m]"):
        repo, tmp = make_repo(), tempfile.mkdtemp(prefix="eos-rg-s-")
        write(repo, "hooks/new-guard.py", "x = 1\n")
        git(repo, "add", "-A")
        rc, out, err = run_cli(
            ["--record", "--verdict", "approved", "--model", mid], repo, tmp)
        assert rc == 0, "--record must accept %s: %s" % (mid, err)
    print("PASS test_record_cli_accepts_opus_5_5")


def test_env_review_models_widens_and_narrows_accepted_tier():
    """EOS_REVIEW_MODELS is the documented escape hatch for a retired/unlisted
    ladder id (settings.json's top-level "env" block is what actually delivers
    it to this subprocess in a live session -- confirmed 2026-09-07, see the
    module docstring). Two things must hold: a model NOT in the hardcoded
    REVIEWER_MODEL_LADDER is accepted once listed in EOS_REVIEW_MODELS, and the
    override REPLACES the ladder rather than adding to it (so a stale
    EOS_REVIEW_MODELS can't accidentally keep an actually-retired id alive
    forever alongside the code-level ladder)."""
    repo, tmp = make_repo(), tempfile.mkdtemp(prefix="eos-rg-s-")
    write(repo, "hooks/new-guard.py", "x = 1\n")
    git(repo, "add", "-A")

    rc, out, err = run_cli(
        ["--record", "--verdict", "approved", "--model", "claude-preview-9"],
        repo, tmp)
    assert rc != 0, "an id absent from both the ladder and EOS_REVIEW_MODELS must be refused"
    assert "not in the accepted tier" in err, (
        "must fail for the accepted-tier reason specifically, not some other "
        "cli_record exit path: %s" % err)

    rc, out, err = run_cli(
        ["--record", "--verdict", "approved", "--model", "claude-preview-9",
         "--notes", "n"],
        repo, tmp, extra_env={"EOS_REVIEW_MODELS": "claude-preview-9"})
    assert rc == 0, "EOS_REVIEW_MODELS must admit an id outside the hardcoded ladder: %s" % err

    rc, out, err = run_cli(
        ["--record", "--verdict", "approved", "--model", LADDER_TOP, "--notes", "n"],
        repo, tmp, extra_env={"EOS_REVIEW_MODELS": "claude-preview-9"})
    assert rc != 0, "EOS_REVIEW_MODELS must REPLACE the ladder, not extend it"

    # A suffixed EOS_REVIEW_MODELS value must not wedge the gate either -- an
    # operator pastes this straight from a self-reported id (the exact
    # scenario the module docstring's settings.json guidance points them at),
    # so both sides of the comparison need the same _bare_model() normalization.
    rc, out, err = run_cli(
        ["--record", "--verdict", "approved", "--model", "claude-preview-9",
         "--notes", "n"],
        repo, tmp, extra_env={"EOS_REVIEW_MODELS": "claude-preview-9[1m]"})
    assert rc == 0, (
        "a bracket-suffixed EOS_REVIEW_MODELS value must still admit its bare "
        "id: %s" % err)
    print("PASS test_env_review_models_widens_and_narrows_accepted_tier")


def test_bracketed_context_window_suffix_is_stripped_before_comparison():
    """A self-reported model id can carry a trailing context-window tag (e.g.
    "claude-opus-5[1m]", this session's own actual id per model-canary-probe.py's
    bare_model()). An exact-match comparison against the ladder would otherwise
    refuse a genuine top-tier reviewer over formatting alone -- the same failure
    class as the 2026-09-07 incident this branch fixes, recurring even with a
    fresh ladder. --record must accept the suffixed form, and the artifact it
    writes must store the BARE id so a later read-back (valid_review) still
    matches a ladder that never itself carries suffixes."""
    repo, tmp = make_repo(), tempfile.mkdtemp(prefix="eos-rg-s-")
    write(repo, "hooks/new-guard.py", "x = 1\n")
    git(repo, "add", "-A")
    suffixed = LADDER_TOP + "[1m]"
    rc, out, err = run_cli(
        ["--record", "--verdict", "approved", "--model", suffixed, "--notes", "n"],
        repo, tmp)
    assert rc == 0, "a bracket-suffixed top-tier id must be accepted: %s" % err
    key = json.loads(out)["key"]
    path = os.path.join(tmp, "sess1", "reviews", key + ".json")
    with open(path, "r", encoding="utf-8") as fh:
        stored = json.load(fh)
    assert stored["reviewer_model"] == LADDER_TOP, (
        "the artifact must store the BARE id, not the suffixed input: %r" % stored["reviewer_model"])
    print("PASS test_bracketed_context_window_suffix_is_stripped_before_comparison")


def test_legacy_suffixed_artifact_still_validates_on_read():
    """valid_review()'s _bare_model() call on the READ path exists specifically
    for an artifact written before this normalization landed (or by any future
    writer that forgets to normalize). Simulate that directly -- write a
    review, then hand-edit its stored reviewer_model back to a suffixed form
    -- rather than only exercising the CLI's own (already-normalizing) write
    path, which test_bracketed_context_window_suffix_is_stripped_before_
    comparison covers."""
    repo, tmp = make_repo(), tempfile.mkdtemp(prefix="eos-rg-s-")
    write(repo, "hooks/new-guard.py", "x = 1\n")
    git(repo, "add", "-A")
    art = record_review(repo, tmp)
    with open(art["artifact_path"], "r", encoding="utf-8") as fh:
        stored = json.load(fh)
    stored["reviewer_model"] = LADDER_TOP + "[1m]"
    with open(art["artifact_path"], "w", encoding="utf-8") as fh:
        json.dump(stored, fh)
    rc, out, err = run_hook('git commit -m "add guard"', repo, tmp)
    assert_allowed(rc, err, "legacy suffixed reviewer_model on the read path")
    print("PASS test_legacy_suffixed_artifact_still_validates_on_read")


def test_bracket_only_env_entry_cannot_produce_an_empty_accepted_model():
    """2026-09-08 independent review, finding 2 (CONFIRMED, fail-OPEN). Before
    the fix, accepted_models() filtered the RAW token's truthiness
    (`v.strip()`) before _bare_model() normalized it, so a bracket-only entry
    like "claude-opus-5,[1m]" passed the filter as non-empty, then normalized
    to "" -- an empty string that stayed IN the accepted tuple. That means a
    --record call (or a legacy artifact) with reviewer_model="" would VALIDATE
    and a real commit would be ALLOWED with no recorded reviewer identity at
    all. This must never validate, regardless of what garbage EOS_REVIEW_MODELS
    carries."""
    repo, tmp = make_repo(), tempfile.mkdtemp(prefix="eos-rg-s-")
    write(repo, "hooks/new-guard.py", "x = 1\n")
    git(repo, "add", "-A")
    rc, out, err = run_cli(
        ["--record", "--verdict", "approved", "--model", "", "--notes", "n"],
        repo, tmp, extra_env={"EOS_REVIEW_MODELS": "claude-opus-5,[1m]"})
    assert rc != 0, (
        "an empty reviewer_model must never be accepted, even with a "
        "bracket-only EOS_REVIEW_MODELS entry present: rc=%s out=%s" % (rc, out))
    print("PASS test_bracket_only_env_entry_cannot_produce_an_empty_accepted_model")


def test_bare_model_strips_trailing_whitespace_before_the_suffix_regex():
    """2026-09-08 independent review, finding 3 (CONFIRMED, fail-closed). The
    suffix regex anchors to end-of-string ($), so a trailing space after the
    closing bracket ("claude-opus-5[1m] ") used to defeat it entirely --
    _bare_model() returned the string unchanged instead of "claude-opus-5",
    which would wrongly refuse a genuine top-tier reviewer over whitespace
    instead of formatting. maintenance/model-canary-probe.py's bare_model()
    (the precedent this file's own comment cites) already strips first;
    this closes the gap between the two."""
    repo, tmp = make_repo(), tempfile.mkdtemp(prefix="eos-rg-s-")
    write(repo, "hooks/new-guard.py", "x = 1\n")
    git(repo, "add", "-A")
    rc, out, err = run_cli(
        ["--record", "--verdict", "approved", "--model", LADDER_TOP + "[1m] ",
         "--notes", "n"],
        repo, tmp)
    assert rc == 0, (
        "a trailing-whitespace-after-suffix id must still normalize to the "
        "bare top-tier id: %s" % err)
    key = json.loads(out)["key"]
    path = os.path.join(tmp, "sess1", "reviews", key + ".json")
    with open(path, "r", encoding="utf-8") as fh:
        stored = json.load(fh)
    assert stored["reviewer_model"] == LADDER_TOP, (
        "must store the bare id even when the input had trailing whitespace "
        "after the suffix: %r" % stored["reviewer_model"])
    print("PASS test_bare_model_strips_trailing_whitespace_before_the_suffix_regex")


def test_comma_inside_bracket_tag_does_not_shred_env_review_models():
    """2026-09-08 independent review, finding 4 (CONFIRMED, fail-closed,
    near-theoretical -- no real context-window tag in this fleet's tracked
    data has ever carried a comma). A naive raw.split(",") on
    EOS_REVIEW_MODELS would split "claude-opus-5[1m,200k]" into
    "claude-opus-5[1m" and "200k]" -- neither matches the anchored suffix
    regex, both survive unstripped, and accepted_models() returns two
    garbage strings that reject every real model id. Same root cause as
    finding 2 (accepted_models() never validated the SHAPE of its entries),
    cheap to close in the same pass."""
    repo, tmp = make_repo(), tempfile.mkdtemp(prefix="eos-rg-s-")
    write(repo, "hooks/new-guard.py", "x = 1\n")
    git(repo, "add", "-A")
    rc, out, err = run_cli(
        ["--record", "--verdict", "approved", "--model", LADDER_TOP,
         "--notes", "n"],
        repo, tmp,
        extra_env={"EOS_REVIEW_MODELS": LADDER_TOP + "[1m,200k]"})
    assert rc == 0, (
        "a comma-bearing context-window tag must not shred the bare id out "
        "of EOS_REVIEW_MODELS: %s" % err)
    print("PASS test_comma_inside_bracket_tag_does_not_shred_env_review_models")


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


def _hint_fixture(prefix):
    """Repo with one non-risk path and one risk path, both staged."""
    repo, tmp = make_repo(), tempfile.mkdtemp(prefix=prefix)
    write(repo, "src/ui/button.tsx", "export const B = 1\n")
    write(repo, "hooks/unrelated.py", "y = 1\n")
    git(repo, "add", "-A")
    return repo, tmp


def test_multiline_quoted_message_emits_shape_hint():
    """OI-122. A directly-quoted MULTI-LINE `-m` detaches the trailing pathspec
    (the tokenizer recognizes heredocs, not this shape), so scope falls back to
    the whole index and an unrelated staged risk file blocks the commit. The
    block message must SAY that, rather than steering to an override -- which
    is what actually happened on 2026-08-11 and spent a ratified exception on a
    commit that carried zero blast-radius files."""
    repo, tmp = _hint_fixture("eos-rg-hint-")
    cmd = 'git commit -m "title line\n\nbody line" -- src/ui/button.tsx'
    rc, out, err = run_hook(cmd, repo, tmp)
    assert_blocked(rc, err, "multi-line quoted message falls back to whole index")
    assert "multi-line" in err, "hint must name the message shape: %s" % err
    assert "heredoc" in err, "hint must offer the heredoc remedy: %s" % err
    print("PASS test_multiline_quoted_message_emits_shape_hint")


def test_heredoc_message_keeps_pathspec_attached():
    """The fleet-sanctioned heredoc form must keep scoping correctly -- this is
    the behaviour the hint points people TO, so it is load-bearing. Guards
    against any future 'fix' that regresses tokenization."""
    repo, tmp = _hint_fixture("eos-rg-heredoc-")
    cmd = ('git commit -m "$(cat <<\'EOF\'\n'
           'title line\n\nbody line\n'
           'EOF\n'
           ')" -- src/ui/button.tsx')
    rc, out, err = run_hook(cmd, repo, tmp)
    assert_allowed(rc, err, "heredoc-fed message keeps the pathspec attached")
    print("PASS test_heredoc_message_keeps_pathspec_attached")


def test_shape_hint_silent_when_pathspec_attached():
    """The hint is a DIAGNOSTIC, not a scope change: when the pathspec attaches
    correctly and the risk file is genuinely in it, the commit still blocks and
    the hint must stay silent."""
    repo, tmp = _hint_fixture("eos-rg-nohint-")
    rc, out, err = run_hook('git commit -m "touch hook" -- hooks/unrelated.py',
                            repo, tmp)
    assert_blocked(rc, err, "risk file genuinely inside the pathspec")
    assert "directly-quoted multi-line" not in err, (
        "hint must not fire when the pathspec attached: %s" % err)
    print("PASS test_shape_hint_silent_when_pathspec_attached")


def test_shape_hint_does_not_change_blocked_path_set():
    """Hard invariant: adding the hint must not alter WHICH paths the gate
    blocks on, nor its exit code. Review finding F3: an earlier version of this
    test discarded both return codes, so it passed under a warn-mode downgrade
    (rc 0 + WARNING -- a genuine fail-open) and on a full revert. Assert the
    block itself, not just a substring of stderr."""
    repo, tmp = _hint_fixture("eos-rg-inv-")
    rc_fb, _, err_fb = run_hook('git commit -m "a\n\nb" -- src/ui/button.tsx',
                                repo, tmp)
    rc_sc, _, err_sc = run_hook('git commit -m "a" -- hooks/unrelated.py',
                                repo, tmp)
    assert_blocked(rc_fb, err_fb, "fall-back scope must still BLOCK")
    assert_blocked(rc_sc, err_sc, "scoped commit must still BLOCK")
    assert "hooks/unrelated.py" in err_fb, (
        "fall-back scope must still report the risk file: %s" % err_fb)
    assert "hooks/unrelated.py" in err_sc, (
        "scoped commit must still report the risk file: %s" % err_sc)
    print("PASS test_shape_hint_does_not_change_blocked_path_set")


def _load_gate_module():
    import importlib.util
    spec = importlib.util.spec_from_file_location("gate_mod_under_test", HOOK)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_hint_remedy_template_actually_parses():
    """Review finding F1 (MAJOR). The heredoc example the hint tells a blocked
    operator to copy must ITSELF tokenize with the pathspec attached. The first
    version indented every rendered line for display, including the terminator
    -- bash requires it at column 0, and this parser's own exact-match
    terminator rule fails on an indented one, so copying the remedy reproduced
    the very false block it was explaining, in a loop."""
    mod = _load_gate_module()
    hint = mod.message_shape_hint('git commit -m "a\n\nb" -- src/x.tsx')
    assert hint, "fixture must trigger the hint"
    start = hint.index('git commit -m "$(cat')
    end = hint.index('" -- <path>', start) + len('" -- <path>')
    tpl = (hint[start:end].replace("<title>", "t")
                          .replace("<body>", "b")
                          .replace("<path>", "src/x.tsx"))
    sys.path.insert(0, os.path.join(HERE, "lib"))
    from git_commit_parse import find_commit_segment
    args = find_commit_segment(tpl)
    assert args is not None and "--" in args, (
        "the hint's own remedy template strands its pathspec: %r -> %r"
        % (tpl, args))
    print("PASS test_hint_remedy_template_actually_parses")


def test_hint_silent_on_heredoc_prose_containing_double_dash():
    """Review finding F2 (MAJOR). `--` is this fleet's house punctuation. A
    heredoc-fed message whose BODY contains ' -- ' parses fine and scopes
    correctly; the hint must not claim its scope fell back."""
    mod = _load_gate_module()
    cmd = ('git commit -m "$(cat <<\'EOF\'\n'
           'reverted the earlier approach -- see notes\n'
           'EOF\n)"')
    assert mod.message_shape_hint(cmd) == "", (
        "hint fired on correctly-parsed heredoc prose containing ' -- '")
    print("PASS test_hint_silent_on_heredoc_prose_containing_double_dash")


def test_hint_silent_on_chained_git_log_pathspec():
    """Review finding F2 (MAJOR), second trigger: a legitimately chained
    `git log ... -- <path>` before the commit is not stranded wreckage."""
    mod = _load_gate_module()
    cmd = 'git log --oneline -1 -- hooks/\ngit commit -m "a\nb"'
    assert mod.message_shape_hint(cmd) == "", (
        "hint fired on a chained `git log -- <path>`")
    print("PASS test_hint_silent_on_chained_git_log_pathspec")


def test_hint_silent_on_env_prefixed_git_command():
    """Review finding N2. A chained git command carrying a legitimate `--` is
    not wreckage even when an env-assignment prefixes it -- `s[0]` is then
    `GIT_PAGER=cat`, not `git`. Classified via git_commit_parse's own
    _segment_git_subcommand_and_args, which skips env-assign tokens."""
    mod = _load_gate_module()
    cmd = 'GIT_PAGER=cat git log --oneline -- hooks/\ngit commit -m "a\nb"'
    assert mod.message_shape_hint(cmd) == "", (
        "hint fired on an env-prefixed `git log -- <path>`")
    print("PASS test_hint_silent_on_env_prefixed_git_command")


def test_hint_silent_on_multiline_message_with_attached_pathspec():
    """Review finding F6: the 'pathspec recovered' branch was never actually
    exercised -- the earlier test used a single-line command, which returns at
    the newline guard before reaching it. A heredoc-fed multi-line message WITH
    a pathspec reaches that branch and must stay silent."""
    mod = _load_gate_module()
    cmd = ('git commit -m "$(cat <<\'EOF\'\ntitle\n\nbody\nEOF\n)" '
           '-- hooks/unrelated.py')
    assert mod.message_shape_hint(cmd) == "", (
        "hint fired despite the pathspec being attached")
    print("PASS test_hint_silent_on_multiline_message_with_attached_pathspec")


def test_index_realcase_path_survives_non_ascii_under_quotepath_false():
    """git-probe-dedup follow-up (2026-09-07, independent-review finding).
    git_commit_parse.git_lines() used to call subprocess.run() with no
    encoding="utf-8", errors="replace" (unlike git_probe_common.git(), which
    every other shared-wrapper caller in this fleet already gets). On Windows,
    a non-UTF-8 byte in git's stdout is decoded inside subprocess's own
    background reader THREAD: the UnicodeDecodeError there does NOT propagate
    out of subprocess.run(), which instead returns NORMALLY with
    returncode=0 and stdout=None -- so the old `try/except Exception` around
    that call caught nothing, and the real crash was an AttributeError from
    `None.splitlines()` on the very next line, OUTSIDE that try. That
    AttributeError unwound past git_lines, past _index_digest /
    _index_realcase_path, all the way to this gate's own top-level `except
    Exception: pass` in __main__ -- the WHOLE hook aborting mid-run and
    exiting 0, not one query degrading. Bash-verified against a real repo
    before landing the fix (see the git-probe-dedup task notes); this test is
    the regression proof requested by that review.

    _index_realcase_path is the one git_lines call site exposed regardless of
    repo/global config: it passes `-c core.quotepath=false` explicitly
    (needed to recover a path's real on-disk casing), where every other
    call site only sees git's DEFAULT core.quotepath=true C-quoting non-ASCII
    bytes to plain ASCII escapes and is not exposed by this particular bug."""
    mod = _load_gate_module()
    repo = gitfixture.blank_repo(prefix="eos-rg-nonascii-")
    # Cyrillic "slovo" (0x0441 0x043b 0x043e 0x0432 0x043e) -- UTF-8-encodes to
    # bytes undefined under cp1252, this fleet's default locale codec
    # (confirmed via locale.getpreferredencoding before this test was
    # written). Built from codepoints, not a literal non-ASCII character in
    # the source, per this file's own "ASCII-only" header contract.
    name = "".join(chr(c) for c in (0x0441, 0x043b, 0x043e, 0x0432, 0x043e)) + ".py"
    rel = "hooks/" + name
    path = os.path.join(repo, "hooks", name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("x = 1\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "init")

    realcase = mod._index_realcase_path(repo, rel)
    assert realcase == rel, (
        "expected the real-cased non-ASCII path back unharmed, got %r -- a "
        "regression here means the encoding gap this test guards is back"
        % (realcase,))

    digest = mod._index_digest(repo, rel)
    assert digest, (
        "digest must resolve for a real, committed non-ASCII path, not "
        "silently degrade to None (the fail-open symptom this bug produced)")
    print("PASS test_index_realcase_path_survives_non_ascii_under_quotepath_false")


# --------------------------------------------------------------------------
# degraded contract: guarded import failed -> fail CLOSED on commits
# --------------------------------------------------------------------------
# Root incident 2026-09-17: a partial branch sync left eos-review-gate.py
# expecting hooks/lib/git_probe_common.py, which that branch did not have. The
# guarded import caught it, PARSE_CONTRACT_LOADED went False, and main()
# returned immediately -- so the gate SILENTLY allowed every blast-radius
# commit, indistinguishable from "nothing to gate". A gate that cannot run its
# own contract must not be the quiet one in the room.


def _degraded_gate_copy():
    """A copy of this gate whose hooks/lib is EMPTY, so the guarded import fails
    exactly the way the missing-module incident did -- no monkeypatching."""
    td = tempfile.mkdtemp(prefix="eos-rg-degraded-")
    hooks_dir = os.path.join(td, "hooks")
    os.makedirs(os.path.join(hooks_dir, "lib"))
    shutil.copy2(HOOK, os.path.join(hooks_dir, "eos-review-gate.py"))
    return td, os.path.join(hooks_dir, "eos-review-gate.py")


def _run_degraded(command, extra_env=None, sessions_dir=None):
    td, hook = _degraded_gate_copy()
    try:
        env = dict(os.environ)
        env.pop("EOS_REVIEW_MODELS", None)
        env.pop("EOS_REVIEW_GATE_MODE", None)
        # The real hooks/lib must not satisfy the import from elsewhere and
        # quietly un-degrade the fixture. (Belt-and-braces: the copied hook puts
        # its OWN empty lib on sys.path[0], which is what actually isolates it.)
        env.pop("PYTHONPATH", None)
        if sessions_dir:
            env["EOS_SESSIONS_DIR"] = sessions_dir
            env["ORA_OVERRIDE_SESSIONS_DIR"] = sessions_dir
        if extra_env:
            env.update(extra_env)
        stdin_text = json.dumps({
            "session_id": "sess1", "cwd": td, "tool_name": "Bash",
            "tool_input": {"command": command},
        })
        proc = subprocess.run([sys.executable, hook], input=stdin_text,
                              capture_output=True, text=True, env=env)
        return proc.returncode, proc.stderr
    finally:
        shutil.rmtree(td, ignore_errors=True)


def test_degraded_contract_blocks_a_commit():
    rc, err = _run_degraded('git commit -m "x" -- hooks/lib/git_commit_parse.py')
    assert rc == 2, (
        "a gate whose contract failed to import must FAIL CLOSED on a commit, "
        "got rc=%s err=%r" % (rc, err))
    assert "BLOCKED (eos-review-gate)" in err, err
    assert "could not be imported" in err, (
        "the block must name the real cause, not read as an ordinary review "
        "block: %r" % err)


def test_degraded_contract_allows_non_commit():
    rc, err = _run_degraded("ls -la")
    assert rc == 0, (
        "a degraded gate must still allow non-commit tool calls -- blocking "
        "every Bash call would brick the fleet, got rc=%s err=%r" % (rc, err))


def test_degraded_contract_announces_on_the_non_commit_path():
    """Fail-closed covers commits; everything else must at least be VISIBLE."""
    rc, err = _run_degraded("ls -la")
    assert "eos-review-gate" in err and "could not be imported" in err, (
        "a degraded gate must announce itself even when it allows: %r" % err)


def test_degraded_over_block_does_not_consume_a_token():
    """The detector is over-broad on purpose, so a loose-only match must block
    WITHOUT spending Gabriel's single-use approval -- otherwise an intervening
    `git log --grep commit` eats the token and the real commit is then blocked
    with none left (the 2026-07-24 m7 failure in a sharper form)."""
    sessions = tempfile.mkdtemp(prefix="eos-rg-degraded-notok-")
    td, hook = _partially_degraded_gate_copy()
    token = os.path.join(sessions, "sess1", "overrides", "allow-unreviewed-commit")
    try:
        os.makedirs(os.path.dirname(token))
        with open(token, "w") as fh:
            fh.write("scope: unreviewed-blast-radius-commit\n"
                     "session: sess1\nreason: must survive an over-match\n")
        env = dict(os.environ)
        for var in ("EOS_REVIEW_MODELS", "EOS_REVIEW_GATE_MODE", "PYTHONPATH"):
            env.pop(var, None)
        env["EOS_SESSIONS_DIR"] = sessions
        env["ORA_OVERRIDE_SESSIONS_DIR"] = sessions
        proc = subprocess.run(
            [sys.executable, hook],
            input=json.dumps({"session_id": "sess1", "cwd": td, "tool_name": "Bash",
                              "tool_input": {"command": "git log --grep commit"}}),
            capture_output=True, text=True, env=env)
        assert proc.returncode == 2, "a loose-only match must still block, got %s" % proc.returncode
        assert os.path.exists(token), (
            "the single-use token was CONSUMED by a non-commit -- it must survive")
        assert "without consuming" in proc.stderr, proc.stderr
    finally:
        shutil.rmtree(sessions, ignore_errors=True)
        shutil.rmtree(td, ignore_errors=True)


def test_degraded_over_blocks_git_add_of_a_commit_named_file():
    """The degraded detector is a substring scan, not is_git_commit()'s
    tokenizer, so this DOES match and block. Pinned deliberately: over-blocking
    is the accepted trade on a path that only runs when hooks/lib is broken, and
    an earlier version of this change claimed the opposite in a comment."""
    rc, err = _run_degraded("git add hooks/commit-provenance-guard.py")
    assert rc == 2, "expected the accepted over-block, got rc=%s err=%r" % (rc, err)
    assert "MENTIONS a git commit but is not shaped like one" in err, (
        "an over-block must say it is one, or it reads as a real verdict: %r" % err)


def test_degraded_never_blocks_the_repair_command():
    """No bootstrap deadlock: restoring the missing module must stay possible."""
    rc, err = _run_degraded("git checkout origin/main -- hooks/lib/git_probe_common.py")
    assert rc == 0, (
        "the repair for the very failure this path reports must not be blocked, "
        "got rc=%s err=%r" % (rc, err))


def test_degraded_honors_mode_off():
    rc, err = _run_degraded('git commit -m "x"',
                            extra_env={"EOS_REVIEW_GATE_MODE": "off"})
    assert rc == 0, "EOS_REVIEW_GATE_MODE=off must win even while degraded, got rc=%s" % rc


def test_degraded_honors_mode_warn():
    rc, err = _run_degraded('git commit -m "x"',
                            extra_env={"EOS_REVIEW_GATE_MODE": "warn"})
    assert rc == 0, "warn mode must not block even while degraded, got rc=%s" % rc
    assert "not blocking" in err, err


def _partially_degraded_gate_copy():
    """The REAL 2026-09-17 shape: hooks/lib is present but ONE module is gone,
    so override_tokens (the first name in the guarded import) is still bound
    while git_commit_parse's own dependency is not. Distinct from the
    empty-lib fixture above, where nothing at all can be imported."""
    # Copy ONLY the gate and lib/*.py -- never the whole hooks/ tree, which
    # contains hooks/sessions/ that other live sessions write concurrently (a
    # copytree of it raced and produced a spurious failure while this test was
    # being written).
    td = tempfile.mkdtemp(prefix="eos-rg-partial-")
    lib_dir = os.path.join(td, "hooks", "lib")
    os.makedirs(lib_dir)
    for name in os.listdir(os.path.join(HERE, "lib")):
        if name.endswith(".py") and name != "git_probe_common.py":
            shutil.copy2(os.path.join(HERE, "lib", name), os.path.join(lib_dir, name))
    shutil.copy2(HOOK, os.path.join(td, "hooks", "eos-review-gate.py"))
    return td, os.path.join(td, "hooks", "eos-review-gate.py")


def test_degraded_honors_an_override_token():
    """The block message points at the token contract -- so the token must
    actually work in the failure this path exists for. Uses the partial fixture:
    with the WHOLE lib gone, override_tokens cannot load either and the gate
    correctly says no token can be honored (covered by the message assertion in
    test_degraded_contract_blocks_a_commit)."""
    sessions = tempfile.mkdtemp(prefix="eos-rg-degraded-tok-")
    td, hook = _partially_degraded_gate_copy()
    try:
        overrides = os.path.join(sessions, "sess1", "overrides")
        os.makedirs(overrides)
        with open(os.path.join(overrides, "allow-unreviewed-commit"), "w") as fh:
            fh.write("scope: unreviewed-blast-radius-commit\n"
                     "session: sess1\n"
                     "reason: degraded-path token test\n")
        env = dict(os.environ)
        env.pop("EOS_REVIEW_MODELS", None)
        env.pop("EOS_REVIEW_GATE_MODE", None)
        env.pop("PYTHONPATH", None)
        env["EOS_SESSIONS_DIR"] = sessions
        env["ORA_OVERRIDE_SESSIONS_DIR"] = sessions
        stdin_text = json.dumps({
            "session_id": "sess1", "cwd": td, "tool_name": "Bash",
            "tool_input": {"command": 'git commit -m "x"'},
        })
        proc = subprocess.run([sys.executable, hook], input=stdin_text,
                              capture_output=True, text=True, env=env)
        assert proc.returncode == 0, (
            "a valid single-use token must be honored on the degraded path, "
            "got rc=%s err=%r" % (proc.returncode, proc.stderr))
        assert "UNREVIEWED" in proc.stderr, proc.stderr
        assert "could not be imported" in proc.stderr, (
            "the token path must still say the gate was degraded: %r" % proc.stderr)
    finally:
        shutil.rmtree(sessions, ignore_errors=True)
        shutil.rmtree(td, ignore_errors=True)


def _run_partial_with_token(tool_input):
    """Run the partially-degraded gate with a valid single-use token present and
    return (rc, stderr, token_survived). `tool_input` is the raw payload value so a
    test can also pass a non-dict."""
    sessions = tempfile.mkdtemp(prefix="eos-rg-degraded-strict-")
    td, hook = _partially_degraded_gate_copy()
    token = os.path.join(sessions, "sess1", "overrides", "allow-unreviewed-commit")
    try:
        os.makedirs(os.path.dirname(token))
        with open(token, "w") as fh:
            fh.write("scope: unreviewed-blast-radius-commit\n"
                     "session: sess1\nreason: strict-regex test\n")
        env = dict(os.environ)
        for var in ("EOS_REVIEW_MODELS", "EOS_REVIEW_GATE_MODE", "PYTHONPATH"):
            env.pop(var, None)
        env["EOS_SESSIONS_DIR"] = sessions
        env["ORA_OVERRIDE_SESSIONS_DIR"] = sessions
        proc = subprocess.run(
            [sys.executable, hook],
            input=json.dumps({"session_id": "sess1", "cwd": td, "tool_name": "Bash",
                              "tool_input": tool_input}),
            capture_output=True, text=True, env=env)
        return proc.returncode, proc.stderr, os.path.exists(token)
    finally:
        shutil.rmtree(sessions, ignore_errors=True)
        shutil.rmtree(td, ignore_errors=True)


def test_degraded_token_not_spent_on_commit_graph_or_commit_tree():
    """REVIEW FINDING (PR #234, adversarial, verified): `commit\\b` has a word
    boundary before `-`, so `git commit-graph write` and `git commit-tree ...`
    matched the STRICT pattern and burned Gabriel's single-use token on a command
    that is not a commit, leaving the real commit blocked with none left -- the
    exact failure the strict pattern exists to prevent. They must still BLOCK
    (loose match) but must not spend the token."""
    for cmd in ("git -c x=y commit-graph write",
                "git commit-tree HEAD^{tree} -m x",
                # SECOND REVIEW (same day): value-less long options that make git
                # print and exit before any subcommand -- a flag lookup, not a commit.
                "git --help commit",
                "git --version commit",
                "git --exec-path commit",
                "git --html-path commit"):
        rc, err, survived = _run_partial_with_token({"command": cmd})
        assert rc == 2, "%r must still block while degraded, got rc=%s" % (cmd, rc)
        assert survived, "%r CONSUMED the single-use token: %r" % (cmd, err)


def test_degraded_token_spendable_on_quoted_and_global_option_commits():
    """REVIEW FINDING (PR #234, verified): the strict pattern rejected real commits
    whose global options contain a quoted space or use a long option, so a valid
    token could not be spent on them. The non-degraded is_git_commit() accepts all
    of these."""
    for cmd in ('git -C "C:/path with space" commit -m x',
                'git -c user.name="a b" commit -m x',
                "git --no-pager commit -m x",
                "git --exec-path=/x commit -m x",   # sets the path AND runs the command
                "git -C 'C:/p q' -c core.x=1 commit -m x"):
        rc, err, survived = _run_partial_with_token({"command": cmd})
        assert rc == 0, "%r is a real commit; a valid token must be honored, rc=%s err=%r" % (
            cmd, rc, err)
        assert not survived, "%r should have spent the single-use token" % cmd


def test_degraded_detector_is_case_insensitive():
    """REVIEW FINDING (PR #234, verified): Git Bash on Windows resolves `GIT`, so an
    upper-case `GIT commit` created a commit while the case-sensitive degraded
    detector allowed it ungated."""
    rc, err = _run_degraded('GIT commit -m "x"')   # empty-lib fixture: no token
    assert rc == 2, "upper-case GIT commit must block while degraded, got rc=%s err=%r" % (rc, err)
    # ...and with a token present the strict pattern must recognise it as a commit
    # too, so the token is honored (spent) rather than the commit being unreachable.
    rc2, err2, survived = _run_partial_with_token({"command": 'GIT commit -m "x"'})
    assert rc2 == 0 and not survived, (
        "upper-case GIT commit must be spendable with a valid token, rc=%s err=%r" % (rc2, err2))


def test_degraded_non_dict_tool_input_still_announces():
    """REVIEW FINDING (PR #234, verified): a non-dict tool_input raised inside
    _degraded, was swallowed by main's catch-all and produced rc=0 with EMPTY
    stderr -- the 'always announce' promise was not kept."""
    rc, err, _ = _run_partial_with_token(["git commit -m x"])
    assert rc == 0, "a malformed payload is not a commit; expected allow, got rc=%s" % rc
    assert "eos-review-gate" in err and "could not be imported" in err, (
        "a degraded gate must announce even on a malformed payload: %r" % err)


# --------------------------------------------------------------------------
# degraded detector: BOUNDED TIME (PR #234 review, measured 2026-09-19)
# --------------------------------------------------------------------------
# `\bgit\b[^;&|]*\bcommit\b` and the strict form are O(n^2): re.search retries
# at every `\bgit\b` and each attempt scans to the end of the `;&|` segment.
# `'git' + ' -c git=git' * n` is the worst shape (every unit re-arms a `git`).
# Measured on the real compiled patterns: n=2000 (22KB) ~2s, n=4000 ~8s, and a
# 99KB command that IS a real commit took ~84s (loose + strict). The dispatcher
# runs guards in-process with no per-guard timeout, so a slow detector on the
# path that exists to fail CLOSED on commits can outlive Claude Code's own hook
# timeout -- and everything after it in the chain never runs.
#
# Time is asserted at the process boundary against a budget far above the fixed
# cost (~1s, mostly interpreter start) and far below the broken cost (30-90s),
# so a loaded machine does not flake it but a regression cannot hide.

_DEGRADED_TIME_BUDGET_S = 15.0


def _quadratic_cmd(n, tail=" x"):
    return "git" + " -c git=git" * n + tail


def test_degraded_quadratic_real_commit_blocks_in_bounded_time():
    cmd = _quadratic_cmd(9000, " log; git commit -m x")   # ~99KB, IS a commit
    assert len(cmd) > 90_000, len(cmd)
    t0 = time.monotonic()
    rc, err = _run_degraded(cmd)
    elapsed = time.monotonic() - t0
    assert rc == 2, "an oversized real commit must FAIL CLOSED, got rc=%s err=%r" % (rc, err[:300])
    assert "BLOCKED (eos-review-gate)" in err, err[:300]
    assert elapsed < _DEGRADED_TIME_BUDGET_S, (
        "degraded detector took %.1fs on a 99KB command (budget %.0fs) -- the "
        "quadratic scan is back" % (elapsed, _DEGRADED_TIME_BUDGET_S))


def test_degraded_quadratic_input_without_commit_word_is_allowed_in_bounded_time():
    """The loose regex is quadratic even when it FAILS, so a huge command that never
    says `commit` used to burn the same ~40s to reach an allow. It must skip the
    scan entirely (and must not be over-blocked just for being large)."""
    cmd = _quadratic_cmd(9000)
    t0 = time.monotonic()
    rc, err = _run_degraded(cmd)
    elapsed = time.monotonic() - t0
    assert rc == 0, "no `commit` anywhere -> not a commit, got rc=%s err=%r" % (rc, err[:300])
    assert elapsed < _DEGRADED_TIME_BUDGET_S, (
        "degraded detector took %.1fs on a 99KB non-commit (budget %.0fs)" % (
            elapsed, _DEGRADED_TIME_BUDGET_S))


def test_degraded_large_command_without_commit_word_is_not_over_blocked():
    rc, err = _run_degraded("echo " + "x" * 200_000)
    assert rc == 0, "size alone must not block a command that never mentions commit: %r" % err[:300]


def test_degraded_oversize_commit_blocks_without_spending_the_token():
    """Past the size cap the detector cannot afford the strict scan, so it must not
    SPEND the single-use token on an input it never classified -- it blocks, like any
    loose match, and the token survives for the real (short) commit."""
    cmd = 'git commit -m "' + "x" * 40_000 + '"'
    rc, err, survived = _run_partial_with_token({"command": cmd})
    assert rc == 2, "an oversize commit must block while degraded, got rc=%s err=%r" % (rc, err[:300])
    assert survived, "the single-use token was CONSUMED by an unclassified oversize command"
    assert "-F" in err and "Write tool" in err, (
        "the block must tell the operator how to get under the cap (`git commit -F "
        "<file>`, message file made with the Write tool since a Bash heredoc naming "
        "git and commit is scanned too), or it is a dead end: %r" % err[:600])


def test_degraded_long_but_ordinary_commit_message_is_still_spendable():
    """The cap must sit well above any legitimate message: an 8KB heredoc-sized
    commit is a real commit and a valid token must still be honored on it."""
    cmd = 'git commit -m "' + "x" * 8_000 + '"'
    rc, err, survived = _run_partial_with_token({"command": cmd})
    assert rc == 0, "a real 8KB commit must remain spendable, rc=%s err=%r" % (rc, err[:300])
    assert not survived, "the real commit should have spent the token"


def test_degraded_commit_kind_boundary_and_shape():
    mod = _load_gate_module()
    cap = mod._DEGRADED_MAX_CMD_CHARS
    # Upper bound is the measured limit, not a comfort range: at 65,536 the worst
    # shape costs ~39s CPU (see the at-cap test). Raise it only with new numbers.
    assert 8_192 <= cap <= 16_384, "cap %r outside the reviewed range" % cap
    kind = mod._degraded_commit_kind
    base = "git commit -m "
    at_cap = base + "x" * (cap - len(base))
    assert len(at_cap) == cap and kind(at_cap) == "strict", kind(at_cap)
    assert kind(at_cap + "x") == "oversize"
    # size alone is not a reason to act: no commit word -> not a commit
    assert kind("git " + "x" * (cap * 4)) is None
    assert kind("ls -la") is None
    assert kind("git log --grep commit") == "loose"
    assert kind("GIT commit -m x") == "strict"
    assert kind(None) is None and kind(["git commit"]) is None


def test_degraded_commit_kind_short_circuits_never_reach_the_regexes():
    """Inputs the prefilter or the cap decide must cost ~nothing however large.
    In-process, on THIS THREAD's CPU time: not wall clock (machine load cannot
    flake it) and not process_time() (this suite runs its tests in a thread pool,
    and process_time() would bill this test for its neighbours' work)."""
    mod = _load_gate_module()
    for cmd in (_quadratic_cmd(9000),                          # no `commit`
                _quadratic_cmd(9000, " log; git commit -m x"),  # over the cap
                "git " + "commit " * 20_000,                    # over the cap
                "commit " * 20_000,                             # no `git`
                "git" + " -C x" * 20_000 + " y"):               # no `commit`
        t0 = time.thread_time()
        mod._degraded_commit_kind(cmd)
        spent = time.thread_time() - t0
        assert spent < 1.0, "%d-char input took %.2fs CPU" % (len(cmd), spent)


def test_degraded_commit_kind_time_is_bounded_at_the_cap():
    """The one that pins the CAP. Every short-circuit test above passes for ANY
    cap; this runs the real regexes on the worst shape found that fits under it
    (`git` + ` --git` * n: every `git` chains, and a `; git commit-x` tail makes the
    strict scan run through the whole first segment). Measured 1.1-2.4s CPU at
    16,384 and ~39s at 65,536, so a cap raised without new numbers fails here.
    Budget 8s: 3x the worst measured, 5x under the mutant."""
    mod = _load_gate_module()
    cap = mod._DEGRADED_MAX_CMD_CHARS
    tail = "; git commit-x"
    cmd = "git" + " --git" * ((cap - 3 - len(tail)) // 6) + tail
    cmd += "x" * (cap - len(cmd))
    assert len(cmd) == cap, (len(cmd), cap)
    t0 = time.thread_time()
    kind = mod._degraded_commit_kind(cmd)
    spent = time.thread_time() - t0
    assert kind in ("loose", "strict"), kind   # it really ran the patterns
    assert spent < 8.0, "worst shape at the cap took %.2fs CPU" % spent


def test_degraded_oversize_without_git_is_not_blocked_for_length_alone():
    """Review finding: a prefilter on `commit` alone blocked
    `echo <20KB> # db.commit()` -- no `git`, so neither pattern can match -- purely
    for its length. It also made the documented `-F` remedy self-blocking when the
    message file was written with a Bash heredoc that mentions `commit`."""
    for cmd in ("echo " + "x" * 20_000 + " # db.commit()",
                "cat > /tmp/msg.txt <<'EOF'\n" + "fix the commit path\n" * 1000 + "EOF"):
        assert len(cmd) > 16_384, len(cmd)
        rc, err = _run_degraded(cmd)
        assert rc == 0, "no `git` -> cannot be a git commit, got rc=%s err=%r" % (rc, err[:300])


def test_degraded_oversize_still_honors_mode_off_and_warn_and_rejects_a_typo():
    """Ordering guard: the size block sits AFTER the mode switch, so the documented
    escape hatches still win over it. A re-ordering would strand a real commit."""
    cmd = 'git commit -m "' + "x" * 40_000 + '"'
    assert _run_degraded(cmd, extra_env={"EOS_REVIEW_GATE_MODE": "off"})[0] == 0
    rc, err = _run_degraded(cmd, extra_env={"EOS_REVIEW_GATE_MODE": "warn"})
    assert rc == 0 and "not blocking" in err, (rc, err[:300])
    assert _run_degraded(cmd, extra_env={"EOS_REVIEW_GATE_MODE": "bogus"})[0] == 2


def test_degraded_commit_kind_matches_the_raw_regexes_under_the_cap():
    """The prefilter and cap are pure short-circuits: for anything under the cap the
    decision must equal what the two compiled patterns alone would have said. Seeded
    fuzz over the token classes that separate loose from strict."""
    import random
    mod = _load_gate_module()
    rng = random.Random(20260919)
    toks = ["git", "GIT", "commit", "Commit", "commit-graph", "-c", "-C", "x=y",
            '"a b"', "'c d'", "--no-pager", "--help", "--exec-path", "--exec-path=/x",
            ";", "&&", "|", "\n", " ", "  ", "gitx", "xgit", "x"]
    for _ in range(4000):
        cmd = "".join(rng.choice(toks) + rng.choice(("", " ", " ")) for _ in range(rng.randint(1, 14)))
        want = None
        if mod._DEGRADED_COMMIT_RE.search(cmd):
            want = "strict" if mod._DEGRADED_STRICT_COMMIT_RE.search(cmd) else "loose"
        assert mod._degraded_commit_kind(cmd) == want, (cmd, mod._degraded_commit_kind(cmd), want)


TESTS = [v for k, v in sorted(globals().items()) if k.startswith("test_")]


class _ThreadRoutedStdout:
    """A stdout stand-in that routes each thread's writes to that thread's own buffer.

    contextlib.redirect_stdout CANNOT be used here: it swaps the process-global
    sys.stdout, so concurrent workers overwrite each other's redirect and restore it in
    the wrong order. Measured, not theorised -- the first cut of this runner used it and
    the suite printed ONE of 55 PASS lines, no summary, and still exited 0. A test
    harness that loses results while reporting success is the worst possible failure on
    a security gate, so the routing is per-thread and the summary is asserted below.
    """

    def __init__(self, real):
        self._real = real
        self._tl = threading.local()

    def set_buffer(self, buf):
        self._tl.buf = buf

    def _target(self):
        return getattr(self._tl, "buf", None) or self._real

    def write(self, s):
        return self._target().write(s)

    def flush(self):
        return self._target().flush()

    def isatty(self):
        return False


def _run_one(t):
    """Run one test with its stdout captured per-thread, so parallel workers neither
    interleave nor lose output. Returns (name, ok, captured_stdout, error_or_None)."""
    buf = io.StringIO()
    routed = isinstance(sys.stdout, _ThreadRoutedStdout)
    try:
        if routed:
            sys.stdout.set_buffer(buf)
        t()
    except Exception as exc:
        # Exception, not AssertionError: a test that raises anything else (KeyError on
        # a missing output field, say) used to escape this handler and abort the RUN,
        # so every test sorted after it was silently never executed and the suite
        # printed no summary at all. A crash is a failure, and the run must continue.
        return t.__name__, False, buf.getvalue(), "%s: %s" % (type(exc).__name__, exc)
    finally:
        if routed:
            sys.stdout.set_buffer(None)  # never leave a dead buffer installed
    return t.__name__, True, buf.getvalue(), None


if __name__ == "__main__":
    # PARALLEL RUNNER (2026-08-12). This file is dominated by process-startup cost, not
    # by its own logic: it makes ~194 run_hook/run_cli calls, each spawning a fresh
    # interpreter, and measurement put the mean spawn at 0.726s of which 0.512s is BARE
    # python startup -- i.e. ~70% of the suite's wall clock was interpreter bootstrap.
    # Sequentially that is ~141s on a quiet machine and 300s+ under real multi-session
    # load, against the pre-push gate's 180s budget. It had already been optimised once
    # (OI-061, the shared git-fixture template: 559 spawns -> ~194, 141.7s -> 76.6s) and
    # regressed anyway, because that fix removed spawns while this one removes the WAIT.
    #
    # Threads, not processes: every spawn is a subprocess.run() that releases the GIL, so
    # the startups overlap. Fidelity is unchanged -- each test still executes the real
    # hook through the real CLI boundary, same asserts, same subprocess semantics. Only
    # the scheduling changed.
    #
    # Isolation holds by construction: each test builds its own repo (mkdtemp) and its
    # own sessions dir, and passes env per-call rather than mutating os.environ.
    # Set EOS_RG_TEST_WORKERS=1 to force the old serial order when debugging a failure
    # (also the honest way to re-measure the serial baseline on this machine).
    try:
        _workers = int(os.environ.get("EOS_RG_TEST_WORKERS", "") or 0)
    except ValueError:
        _workers = 0
    if _workers <= 0:
        _workers = min(8, (os.cpu_count() or 4))

    # Pre-warm the shared fixture template SERIALLY. gitfixture caches templates in a
    # module-level dict with no lock; two workers racing to build the same key would
    # both copytree into a half-built template. One serial call makes every later read
    # a plain dict hit. Without this the parallelism itself would be the bug.
    make_repo()

    failures = 0
    if _workers == 1:
        results = [_run_one(t) for t in TESTS]
    else:
        _real_stdout = sys.stdout
        sys.stdout = _ThreadRoutedStdout(_real_stdout)
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=_workers) as pool:
                # map preserves input order, so output stays deterministic and diffable
                # regardless of completion order.
                results = list(pool.map(_run_one, TESTS))
        finally:
            sys.stdout = _real_stdout

    # RESULT-LOSS GUARD: the first cut of this runner silently dropped 54 of 55 results
    # and still exited 0. Never trust the parallel path to have reported everything --
    # assert the count before printing a pass summary.
    assert len(results) == len(TESTS), (
        "runner lost results: got %d of %d -- refusing to report a verdict"
        % (len(results), len(TESTS)))

    for name, ok, out, err in results:
        if out:
            sys.stdout.write(out)
        if not ok:
            failures += 1
            print("FAIL %s: %s" % (name, err))
    if failures:
        print("%d REVIEW-GATE TEST(S) FAILED" % failures)
        sys.exit(1)
    print("ALL REVIEW-GATE TESTS PASS (%d)" % len(TESTS))
