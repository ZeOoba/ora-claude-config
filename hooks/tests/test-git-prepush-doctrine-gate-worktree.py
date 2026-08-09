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



# --- sweep_stale_push_worktrees(): the janitor -----------------------------------------
# WHY THIS EXISTS. remove_worktree() already runs in a finally, but two leak modes escape
# it, both observed live on 2026-08-09 (9 worktrees registered against the real repo):
#   (A) the process never reaches the finally at all -- a pre-push hook dies with the push
#       (Ctrl-C, terminal close, SIGKILL), leaving a full scratch dir on disk. Observed:
#       ora-doctrine-push-e7uqt8f1, intact and registered, untouched since 2026-08-06.
#   (B) `git worktree remove` fails, remove_worktree() falls back to rmtree and documents
#       the leftover as "harmless but stale; `git worktree prune` clears it later" -- but
#       NOTHING ever runs that prune. Observed: ora-doctrine-push-63_jv1es, directory gone,
#       registration still live. "Later" never arrives on its own.
# A janitor that runs at gate START is the only thing that can cover a run that already
# died. The hard safety property is that it MUST NOT touch a CONCURRENTLY RUNNING gate's
# scratch dir -- pushes from different sessions overlap routinely (27 sessions live when
# this was written), and eating a live worktree mid-probe would turn a hygiene sweep into
# a fail-closed push block. Hence the age threshold, and hence these tests lead with it.
with tempfile.TemporaryDirectory() as _tmproot:
    _repo6, _probe6 = make_throwaway_repo()
    try:
        write_claude_md(_repo6, CLEAN_CLAUDE_MD)
        commit_all(_repo6, "base")

        _old = os.path.join(_tmproot, "ora-doctrine-push-oldone")
        _fresh = os.path.join(_tmproot, "ora-doctrine-push-freshone")
        _alien = os.path.join(_tmproot, "some-other-tool-scratch")
        for _d in (_old, _fresh, _alien):
            os.makedirs(_d)
            with open(os.path.join(_d, "marker.txt"), "w") as _f:
                _f.write("x")
        _long_ago = 1000.0            # epoch: unambiguously older than any threshold
        os.utime(_old, (_long_ago, _long_ago))
        os.utime(_alien, (_long_ago, _long_ago))   # old AND non-matching: age alone must not doom it

        _removed, _pruned = dg.sweep_stale_push_worktrees(
            repo_root=_repo6, temp_root=_tmproot, max_age_seconds=3600)

        expect("janitor: a STALE scratch dir is removed", not os.path.isdir(_old))
        expect("janitor: a FRESH scratch dir SURVIVES (a concurrent push is using it)",
               os.path.isdir(_fresh))
        expect("janitor: a non-matching dir is never touched, however old",
               os.path.isdir(_alien))
        expect("janitor: reports what it removed", _removed == 1, "removed=%r" % (_removed,))

        # skip_path: belt-and-braces for THIS run's own worktree, independent of mtime.
        _mine = os.path.join(_tmproot, "ora-doctrine-push-mine")
        os.makedirs(_mine)
        os.utime(_mine, (_long_ago, _long_ago))   # deliberately ancient
        dg.sweep_stale_push_worktrees(repo_root=_repo6, temp_root=_tmproot,
                                      max_age_seconds=3600, skip_path=_mine)
        expect("janitor: skip_path is never removed even when its mtime is ancient",
               os.path.isdir(_mine))

        # --- leak mode (B): orphaned REGISTRATION, directory already gone ---------------
        _wt = os.path.join(_tmproot, "ora-doctrine-push-orphanreg")
        _r = _run(["git", "worktree", "add", "--detach", "--quiet", _wt, "HEAD"], cwd=_repo6)
        expect("janitor fixture: worktree registered", _r.returncode == 0,
               "%s%s" % (_r.stdout, _r.stderr))
        shutil.rmtree(_wt, ignore_errors=True)     # dir gone, registration remains
        _listed = _run(["git", "worktree", "list"], cwd=_repo6).stdout
        expect("janitor fixture: registration is orphaned before the sweep",
               "orphanreg" in _listed)
        dg.sweep_stale_push_worktrees(repo_root=_repo6, temp_root=_tmproot,
                                      max_age_seconds=0)   # 0 => expire everything eligible
        _listed2 = _run(["git", "worktree", "list"], cwd=_repo6).stdout
        expect("janitor: orphaned registration is pruned (the 'prune it later' that never ran)",
               "orphanreg" not in _listed2, "list=%s" % _listed2)

        # --- a LIVE registration whose dir still exists must survive the prune ----------
        _live = os.path.join(_tmproot, "ora-doctrine-push-liveone")
        _run(["git", "worktree", "add", "--detach", "--quiet", _live, "HEAD"], cwd=_repo6)
        dg.sweep_stale_push_worktrees(repo_root=_repo6, temp_root=_tmproot,
                                      max_age_seconds=3600, skip_path=_live)
        _listed3 = _run(["git", "worktree", "list"], cwd=_repo6).stdout
        expect("janitor: a live registration with an existing dir is NOT pruned",
               "liveone" in _listed3, "list=%s" % _listed3)
        _run(["git", "worktree", "remove", "--force", _live], cwd=_repo6)
    finally:
        shutil.rmtree(_repo6, ignore_errors=True)

# --- the PRUNE leg's own guards (independent review, 2026-08-09) ----------------------
# Two holes the first cut of this change had, both found by review, both writable as tests
# only because real git was measured first:
#   * --expire does NOT protect a missing-directory registration once its admin files are
#     older than the window, so the prune leg needed a SEPARATE guard. It now abstains
#     whenever it sees a missing-dir registration it does not own -- because the victim
#     would be a sibling session's long-lived worktree, permanently dead ("fatal: not a
#     git repository") when its path came back.
#   * the expire bound itself had zero coverage: the orphan test used max_age_seconds=0
#     and the survival test used a registration whose directory still existed, which prune
#     can never touch regardless. Dropping --expire entirely would have stayed green.
_repo8, _probe8 = make_throwaway_repo()
try:
    write_claude_md(_repo8, CLEAN_CLAUDE_MD)
    commit_all(_repo8, "base")
    with tempfile.TemporaryDirectory() as _t8:
        # (a) a FOREIGN missing-dir registration must make the sweep abstain entirely,
        #     leaving even our OWN orphan registered rather than risk the foreign one.
        _foreign = os.path.join(_t8, "someones-real-worktree")
        _ourorphan = os.path.join(_t8, "ora-doctrine-push-ourorphan")
        for _p in (_foreign, _ourorphan):
            _run(["git", "worktree", "add", "--detach", "--quiet", _p, "HEAD"], cwd=_repo8)
        shutil.rmtree(_foreign, ignore_errors=True)
        shutil.rmtree(_ourorphan, ignore_errors=True)
        dg.sweep_stale_push_worktrees(repo_root=_repo8, temp_root=_t8, max_age_seconds=0)
        _l8 = _run(["git", "worktree", "list"], cwd=_repo8).stdout
        expect("prune guard: a FOREIGN missing-dir registration is never pruned",
               "someones-real-worktree" in _l8, "list=%s" % _l8)
        expect("prune guard: the sweep ABSTAINS wholesale rather than prune selectively "
               "(our own orphan survives too -- disk was already reclaimed)",
               "ourorphan" in _l8, "list=%s" % _l8)
        _run(["git", "worktree", "prune"], cwd=_repo8)   # reset for (b)

        # (b) with only OUR debris missing, the guard clears -- and the expire bound then
        #     protects a registration whose admin files are still FRESH.
        _fresh_orphan = os.path.join(_t8, "ora-doctrine-push-freshorphan")
        _run(["git", "worktree", "add", "--detach", "--quiet", _fresh_orphan, "HEAD"], cwd=_repo8)
        shutil.rmtree(_fresh_orphan, ignore_errors=True)
        dg.sweep_stale_push_worktrees(repo_root=_repo8, temp_root=_t8, max_age_seconds=3600)
        _l8b = _run(["git", "worktree", "list"], cwd=_repo8).stdout
        expect("expire bound: a FRESH orphaned registration survives (a concurrent run "
               "whose dir is momentarily unreadable is not dropped)",
               "freshorphan" in _l8b, "list=%s" % _l8b)

        # ...and the same orphan IS pruned once it is treated as expired.
        dg.sweep_stale_push_worktrees(repo_root=_repo8, temp_root=_t8, max_age_seconds=0)
        _l8c = _run(["git", "worktree", "list"], cwd=_repo8).stdout
        expect("expire bound: the same orphan IS pruned when expired",
               "freshorphan" not in _l8c, "list=%s" % _l8c)
finally:
    shutil.rmtree(_repo8, ignore_errors=True)


# --- the janitor must NEVER be able to change the gate's decision ----------------------
# Same posture as remove_worktree(): this is hygiene, not policy. A janitor that can raise
# would convert "your temp dir is odd" into "your push is blocked", which is strictly worse
# than the leak it cleans up.
_nonrepo = tempfile.mkdtemp(prefix="ora-janitor-nonrepo-")
# GIT_CEILING_DIRECTORIES: sweep's prune leg shells out to git with cwd under %TEMP%, and
# git walks UPWARD looking for a repo. There is no ancestor repo above %TEMP% on the
# machine this was written on -- but on a machine with e.g. a dotfiles repo at $HOME this
# test would prune a REAL repo. A test must not depend on the host's directory layout for
# its blast radius (independent review, 2026-08-09).
_prev_ceiling = os.environ.get("GIT_CEILING_DIRECTORIES")
os.environ["GIT_CEILING_DIRECTORIES"] = _nonrepo
try:
    _ok = True
    try:
        dg.sweep_stale_push_worktrees(repo_root=_nonrepo, temp_root=_nonrepo,
                                      max_age_seconds=0)
    except Exception as _e:
        _ok = False
    expect("janitor: never raises on a non-repo root (cannot block a push)", _ok)

    _ok2 = True
    try:
        dg.sweep_stale_push_worktrees(repo_root=os.path.join(_nonrepo, "nope"),
                                      temp_root=os.path.join(_nonrepo, "also-nope"),
                                      max_age_seconds=0)
    except Exception:
        _ok2 = False
    expect("janitor: never raises on nonexistent roots", _ok2)
finally:
    if _prev_ceiling is None:
        os.environ.pop("GIT_CEILING_DIRECTORIES", None)
    else:
        os.environ["GIT_CEILING_DIRECTORIES"] = _prev_ceiling
    shutil.rmtree(_nonrepo, ignore_errors=True)


# --- WIRING: defining the janitor is not the same as CALLING it -----------------------
# A sweep function nothing invokes is exactly the "tested but disconnected" shape that
# leaves the original leak in place while the suite reports green. Monkeypatch the sweep
# (rather than letting it loose on the real %TEMP%, where a concurrent push may have a
# live scratch dir) and assert materialize_pushed_commit actually drives it, BEFORE it
# creates this run's directory.
_repo7, _probe7 = make_throwaway_repo()
try:
    write_claude_md(_repo7, CLEAN_CLAUDE_MD)
    commit_all(_repo7, "base")
    _calls = []
    _real_sweep = dg.sweep_stale_push_worktrees
    dg.sweep_stale_push_worktrees = lambda **kw: (_calls.append(kw), (0, False))[1]
    try:
        _wt7, _err7 = dg.materialize_pushed_commit(repo_root=_repo7)
    finally:
        dg.sweep_stale_push_worktrees = _real_sweep
    try:
        expect("wiring: materialize_pushed_commit invokes the janitor", len(_calls) == 1,
               "calls=%r" % (_calls,))
        expect("wiring: janitor is pointed at the same repo the gate is validating",
               bool(_calls) and _calls[0].get("repo_root") == _repo7,
               "kw=%r" % (_calls[0] if _calls else None,))
        expect("wiring: the scratch worktree is still created normally",
               _wt7 is not None and os.path.isdir(_wt7), "err=%r" % (_err7,))
    finally:
        if _wt7:
            dg.remove_worktree(_wt7, repo_root=_repo7)
finally:
    shutil.rmtree(_repo7, ignore_errors=True)


passed = sum(1 for ok, _ in results if ok)
print("\ngit-prepush-doctrine-gate-worktree tests: %d/%d passed" % (passed, len(results)))
sys.exit(0 if passed == len(results) else 1)
