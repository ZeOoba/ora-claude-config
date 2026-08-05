#!/usr/bin/env python3
"""Tests for OI-100: git-prepush-doctrine-gate.py must validate the COMMIT about to be
pushed, not the working tree. Prior to this fix, run_doctrine_probe() ran the probe with
no arguments, which validates the working tree -- a false-negative hole (commit drift,
revert it uncommitted, push: the gate saw a clean working tree and let a drifted commit
through). See open-items-tracker.md OI-100 and doctrine-integrity-probe.py's
LIVE_CLAUDE_DIR comment for the two traps this fix has to avoid.

CANONICAL REGRESSION TEST (test_gate_blocks_committed_drift_reverted_only_in_working_tree):
commit doctrine drift, then revert it in the WORKING TREE only, leaving the commit
itself drifted -- the gate must BLOCK. This is the exact auto-check named in OI-100.

Fully isolated: every test builds its own throwaway git repo in a temp dir (never the
real ~/.claude repo) via REPO_ROOT_OVERRIDE/PROBE_SCRIPT_OVERRIDE, so `git worktree add`
never registers anything against the real repo's worktree list.

Run: python test-git-prepush-doctrine-gate-worktree.py  (exit 0 = pass)
"""
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile

# Same hazard/fix as maintenance/test-doctrine-integrity-probe.py's module-level scrub:
# an inherited GIT_DIR/GIT_WORK_TREE would silently redirect every git call below at the
# outer repo instead of each test's own throwaway one.
for _v in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR",
           "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_PREFIX"):
    os.environ.pop(_v, None)

HOOKS = os.path.dirname(os.path.abspath(__file__))
HOOKS = os.path.dirname(HOOKS)
CLAUDE_ROOT = os.path.dirname(HOOKS)
REAL_PROBE_SCRIPT = os.path.join(CLAUDE_ROOT, "maintenance", "doctrine-integrity-probe.py")

spec = importlib.util.spec_from_file_location(
    "dg", os.path.join(HOOKS, "git-prepush-doctrine-gate.py"))
dg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dg)

results = []


def expect(label, cond, detail=""):
    results.append((bool(cond), label))
    if not cond:
        print("  FAIL: %s %s" % (label, detail))


def _run(args, cwd):
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True)


def make_throwaway_repo():
    """A minimal, real git repo with its own copy of doctrine-integrity-probe.py (so
    PROBE_SCRIPT_OVERRIDE can point straight at it -- the probe file itself need not be
    TRACKED, it just has to exist on disk for `git worktree add` -> subprocess to find).
    Returns (repo_dir, probe_script_path)."""
    repo_dir = tempfile.mkdtemp(prefix="ora-oi100-repo-")
    _run(["git", "init", "-q"], cwd=repo_dir)
    _run(["git", "config", "user.email", "test@example.com"], cwd=repo_dir)
    _run(["git", "config", "user.name", "test"], cwd=repo_dir)
    probe_script = os.path.join(repo_dir, "doctrine-integrity-probe.py")
    shutil.copyfile(REAL_PROBE_SCRIPT, probe_script)
    return repo_dir, probe_script


def write_claude_md(repo_dir, text):
    with open(os.path.join(repo_dir, "CLAUDE.md"), "w", encoding="utf-8") as f:
        f.write(text)


def commit_all(repo_dir, message):
    _run(["git", "add", "-A"], cwd=repo_dir)
    r = _run(["git", "commit", "-q", "-m", message], cwd=repo_dir)
    assert r.returncode == 0, "commit failed: %s%s" % (r.stdout, r.stderr)


# Minimal fixture valid under the FULL live-mode probe -- mirrors
# maintenance/test-doctrine-integrity-probe.py's proven-clean _v21_base() (required
# headers, nothing referenced inside them, so checks 1-4 have nothing to flag). Every
# other check the full live-mode probe runs (8, 9, 10, 11, 12, 13) is WARN-only/
# fail-open on an absent file (verified against doctrine-integrity-probe.py directly),
# so a throwaway repo with no memory/, settings.json, scheduled-tasks/, etc. still
# resolves clean overall.
CLEAN_CLAUDE_MD = ("## Engineering OS (test fixture)\n"
                    " no commands here\n"
                    "## Skill tie-breaks (test fixture)\n"
                    "- nothing referenced\n"
                    "\nEverything here is clean, no bare dates, short.\n")
DRIFTED_CLAUDE_MD = CLEAN_CLAUDE_MD.replace(
    "Everything here is clean, no bare dates, short.\n",
    "Everything here is clean, except this incident happened on 2020-01-01 and was "
    "never fixed.\n")


# --- materialize_pushed_commit() / remove_worktree(): unit-level ---------------------
with tempfile.TemporaryDirectory() as _outer:
    repo, probe = make_throwaway_repo()
    try:
        write_claude_md(repo, CLEAN_CLAUDE_MD)
        commit_all(repo, "initial clean commit")
        # Dirty the working tree WITHOUT committing -- materialize must not see this.
        write_claude_md(repo, DRIFTED_CLAUDE_MD)

        wt_path, err = dg.materialize_pushed_commit(repo_root=repo)
        expect("materialize: succeeds against a real repo", wt_path is not None, err or "")
        if wt_path:
            with open(os.path.join(wt_path, "CLAUDE.md"), encoding="utf-8") as f:
                seen = f.read()
            expect("materialize: worktree reflects COMMITTED content, not the dirty "
                   "working tree", seen == CLEAN_CLAUDE_MD,
                   "got %r" % seen[:80])
            dg.remove_worktree(wt_path, repo_root=repo)
            expect("remove_worktree: scratch dir is gone", not os.path.isdir(wt_path))

        # Restore working tree to a known state for the next block.
        write_claude_md(repo, CLEAN_CLAUDE_MD)
    finally:
        shutil.rmtree(repo, ignore_errors=True)

# --- materialize_pushed_commit(): fail-closed on a non-repo ---------------------------
_not_a_repo = tempfile.mkdtemp(prefix="ora-oi100-notrepo-")
try:
    wt_path2, err2 = dg.materialize_pushed_commit(repo_root=_not_a_repo)
    expect("materialize: fails closed (None) against a non-repo dir", wt_path2 is None)
    expect("materialize: fail-closed path reports an error string",
           bool(err2), "err2=%r" % err2)
finally:
    shutil.rmtree(_not_a_repo, ignore_errors=True)


# --- run_doctrine_probe(): fail-closed when materialization itself fails --------------
_not_a_repo2 = tempfile.mkdtemp(prefix="ora-oi100-notrepo2-")
try:
    dg.REPO_ROOT_OVERRIDE = _not_a_repo2
    rc, out = dg.run_doctrine_probe()
    expect("run_doctrine_probe: rc=1 when the commit cannot be materialized "
           "(fail-closed, matches the pre-existing 'probe cannot be launched' "
           "contract)", rc == 1, "got rc=%r" % rc)
finally:
    dg.REPO_ROOT_OVERRIDE = None
    shutil.rmtree(_not_a_repo2, ignore_errors=True)


# --- THE CANONICAL OI-100 REGRESSION TEST ---------------------------------------------
# "commit doctrine drift, then revert it in the working tree only (leaving the commit
# itself drifted) -- the gate must BLOCK. Today it allows (that's the bug)."
repo3, probe3 = make_throwaway_repo()
try:
    write_claude_md(repo3, CLEAN_CLAUDE_MD)
    commit_all(repo3, "clean baseline")

    write_claude_md(repo3, DRIFTED_CLAUDE_MD)
    commit_all(repo3, "introduces a bare-date drift")  # HEAD is now drifted

    # Revert in the WORKING TREE ONLY -- do NOT commit. HEAD still carries the drift;
    # `git status` shows CLAUDE.md modified back to clean.
    write_claude_md(repo3, CLEAN_CLAUDE_MD)
    status = _run(["git", "status", "--porcelain"], cwd=repo3).stdout
    expect("scenario setup: working tree shows CLAUDE.md as modified (dirty)",
           "CLAUDE.md" in status, "git status: %r" % status)

    # OLD-STYLE differential (reference_refute_differential_harness.md: judge the delta,
    # not an absolute) -- a bare/positional read of "whatever's on disk right now" is
    # exactly what the pre-fix gate's argument-less probe invocation amounted to
    # (PROBE_SCRIPT/REAL_CLAUDE_MD were hardcoded to the live checkout with no override
    # seam, so it could only ever see the working tree, never a specific commit).
    old_style = subprocess.run(
        [sys.executable, probe3, "--quick", os.path.join(repo3, "CLAUDE.md")],
        capture_output=True, text=True)
    expect("OLD-STYLE (working-tree read): reports CLEAN -- reproduces the bug "
           "(drift is in the commit, not the working tree, so a working-tree-only "
           "read misses it)", old_style.returncode == 0,
           "rc=%d out=%s" % (old_style.returncode, old_style.stdout[-300:]))

    # NEW behavior: the real, current run_doctrine_probe(), wired at the throwaway repo.
    dg.REPO_ROOT_OVERRIDE = repo3
    dg.PROBE_SCRIPT_OVERRIDE = probe3
    try:
        rc3, out3 = dg.run_doctrine_probe()
    finally:
        dg.REPO_ROOT_OVERRIDE = None
        dg.PROBE_SCRIPT_OVERRIDE = None

    expect("NEW (run_doctrine_probe, materializes HEAD): BLOCKS -- the commit's drift "
           "is caught even though the working tree looks clean (THE FIX)",
           rc3 != 0, "rc3=%r out3=%s" % (rc3, out3[-300:]))
    expect("NEW: reports the actual drift (bare date), not a generic failure",
           "2020-01-01" in out3 or "bare" in out3.lower() or "date" in out3.lower(),
           "out3=%s" % out3[-500:])

    # Full end-to-end: main() itself (not just run_doctrine_probe()) must BLOCK too,
    # with no session id / no override token available in this test environment.
    os.environ.pop("CLAUDE_CODE_SESSION_ID", None)
    dg.REPO_ROOT_OVERRIDE = repo3
    dg.PROBE_SCRIPT_OVERRIDE = probe3
    dg.EVENT_LOG_OVERRIDE = os.path.join(repo3, "_unused_event_log.md")
    with open(dg.EVENT_LOG_OVERRIDE, "w", encoding="utf-8") as f:
        f.write("# test log\n")
    try:
        main_rc = dg.main()
    finally:
        dg.REPO_ROOT_OVERRIDE = None
        dg.PROBE_SCRIPT_OVERRIDE = None
        dg.EVENT_LOG_OVERRIDE = None
    expect("NEW: main() exits non-zero (git pre-push BLOCK convention) for the same "
           "committed-but-reverted drift", main_rc != 0, "main_rc=%r" % main_rc)
finally:
    shutil.rmtree(repo3, ignore_errors=True)


# --- Env-scrub regression (independent review + REFUTE pass, 2026-08-05): an inherited
# GIT_DIR/GIT_WORK_TREE (git exports these to hook subprocesses) must not redirect
# `git worktree add`/`remove` at some OTHER repo than the one `cwd=`/`repo_root` name. ---
repo5, probe5 = make_throwaway_repo()
try:
    write_claude_md(repo5, CLEAN_CLAUDE_MD)
    commit_all(repo5, "repo5 baseline")
    # Poison with a DIFFERENT real repo's .git dir. If the scrub in _clean_git_env()
    # were missing (or dropped), git would resolve against THIS repo instead of repo5,
    # and materialize_pushed_commit would either fail outright or silently checkout the
    # wrong tree -- either way it would not reflect repo5's actual HEAD.
    os.environ["GIT_DIR"] = os.path.join(CLAUDE_ROOT, ".git")
    try:
        wt5, err5 = dg.materialize_pushed_commit(repo_root=repo5)
        expect("env-scrub: materialize succeeds against repo5 despite a poisoned "
               "GIT_DIR pointing at a DIFFERENT real repo", wt5 is not None, err5 or "")
        if wt5:
            with open(os.path.join(wt5, "CLAUDE.md"), encoding="utf-8") as f:
                seen5 = f.read()
            expect("env-scrub: materialized worktree reflects repo5's OWN HEAD "
                   "content, not the poisoned repo's", seen5 == CLEAN_CLAUDE_MD,
                   "got %r" % seen5[:120])
            dg.remove_worktree(wt5, repo_root=repo5)
    finally:
        os.environ.pop("GIT_DIR", None)
finally:
    shutil.rmtree(repo5, ignore_errors=True)


# --- Sanity: a genuinely clean commit (no working-tree tricks) still passes -----------
repo4, probe4 = make_throwaway_repo()
try:
    write_claude_md(repo4, CLEAN_CLAUDE_MD)
    commit_all(repo4, "clean")
    dg.REPO_ROOT_OVERRIDE = repo4
    dg.PROBE_SCRIPT_OVERRIDE = probe4
    try:
        rc4, out4 = dg.run_doctrine_probe()
    finally:
        dg.REPO_ROOT_OVERRIDE = None
        dg.PROBE_SCRIPT_OVERRIDE = None
    expect("sanity: a genuinely clean commit still passes (rc=0), no false positive "
           "from the worktree-materialization machinery itself", rc4 == 0,
           "rc4=%r out4=%s" % (rc4, out4[-300:]))
finally:
    shutil.rmtree(repo4, ignore_errors=True)


passed = sum(1 for ok, _ in results if ok)
print("\ngit-prepush-doctrine-gate-worktree tests: %d/%d passed" % (passed, len(results)))
sys.exit(0 if passed == len(results) else 1)
