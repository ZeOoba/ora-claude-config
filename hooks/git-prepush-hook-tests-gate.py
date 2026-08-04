#!/usr/bin/env python3
"""Native git pre-push gate #2 for ~/.claude — HOOK-TEST-SUITE gate (runs between the
doctrine-drift gate and the confidentiality scan).

WHY (found 2026-07-24): commit 7d01eff rewrote shared-checkout-guard.py's WIP
attribution logic (evidence-based naming, replacing an arbitrary others[0] guess) but
left hooks/tests/test-shared-checkout-guard.py asserting the PRE-fix contract — the
test file's last touch predated the guard rewrite by one commit. Nothing but a human
manually running `python hooks/tests/test-*.py` would ever have caught the mismatch;
it sat broken at HEAD until the next session happened to run the suite by hand. A
behavior-changing hook fix landing without its own test updated in the SAME commit is
exactly the failure class this gate exists to catch at push time, not by luck later.

WHAT IT RUNS: every python test file in the three tracked test trees, each as its own
subprocess (matching how a human runs them: `python <file>`, exit 0 = pass). Aggregates
PASS/FAIL/ENV-SKIP and BLOCKS the push if any test genuinely fails.

DISCOVERY ROOTS (TEST_ROOTS below) and the two-pattern glob: the gate originally swept
hooks/tests/test-*.py ONLY, which silently left both maintenance test trees — 17 files —
outside every gate in the repo, free to rot exactly as described above. The repo carries
two long-standing naming conventions that are NOT worth unifying (renaming files just to
satisfy a glob churns history for no behavioral gain): hooks/tests/ uses "test-*.py"
(hyphen), maintenance/_tests/ uses "test_*.py" (underscore), and maintenance/ itself has
BOTH. So discovery globs both patterns in every root. glob is non-recursive, hence
maintenance/ and maintenance/_tests/ are listed separately rather than walked — a walk
would also drag in unrelated fixture subtrees. All 17 newly-covered files were verified
green (max 14.3s each, well inside PER_TEST_TIMEOUT_SECONDS) before being made blocking.

NOT a discovery root: hooks/ itself. It contains hooks/test-ora-autonomy-gate.py, a
STALE duplicate of the hooks/tests/ copy (different content, last touched an earlier
commit) — a gate must not certify an orphan as live. Nor is test-stuck-session-watchdog.ps1
covered: this runner is `python <file>`, and a PowerShell test needs a different runner.
Both are tracked as separate cleanups, not silently absorbed here.

ENV-SKIP, not FAIL: a test can print a line containing the literal sentinel
`CANNOT RUN:` and exit non-zero to declare "I cannot execute in this environment" --
e.g. test-confidentiality-guard.py does exactly this when the live, gitignored
hooks/confidential-terms.json is absent (true in ANY linked worktree by design, since
`git worktree add` never checks out a gitignored file). That is not a regression, so
it does not block. This sentinel already existed in test-confidentiality-guard.py
before this gate was written; this gate treats it as a general, adoptable contract --
any test file may declare itself ENV-SKIP the same way. A genuinely broken
confidential-terms.json in the MAIN checkout is caught independently by
git-prepush-confidential-scan.py's own fail-closed check, so this gate does not need
to special-case that overlap.

A subprocess TIMEOUT (PER_TEST_TIMEOUT_SECONDS) is never ENV-SKIP, but it earns exactly
ONE rerun of that file at a doubled budget (TIMEOUT_RETRY_MULTIPLIER) before it can
block. WHY (found 2026-07-26): during a push with three other live sessions,
test-eos-review-gate.py — the suite's runtime outlier — blew the flat
90s budget (exit 124) and blocked the push, then passed all 48 of its tests quickly
when rerun in isolation moments later: an environmental load flake (same class as the
known intermittent npm-test access-violation flake), not a regression. The rerun's
result is authoritative — a second timeout, or any non-timeout failure surfaced by the
rerun, is a real blocking FAIL, since a test that cannot finish inside DOUBLE the
budget even once signals a genuine hang, not load. A non-timeout failure is NEVER
retried: a deterministic assertion failure must not get two bites at the gate. A file
that recovered on the rerun is disclosed in the summary ("timeout-retry ... not
blocking") so flakes stay visible instead of being silently eaten.

SPAWN COUNT CORRECTED 2026-08-03 (open-items-tracker.md#OI-059). This paragraph used
to call test-eos-review-gate.py "the suite's outlier at 48 subprocess spawns." 48 is
that file's TEST count, not its spawn count — see "all 48 of its tests" above, which is
where the number came from (48 then, 55 now). Real figure, measured by wrapping
subprocess.Popen with a counter around a full run (NOT by counting call sites — a grep
of `make_repo(`/`run_hook(` undercounts badly, because two loops call the fixture once
per iteration and the `def` line matches too):
  559 spawns per run = 451 git + 108 Python.
Of the git spawns, 365 come from the make_repo() fixture (73 runtime calls x 5: init +
2x config + add + commit) and the rest from direct git() helper calls. So 48 was an
~11.6x undercount, and THE FIXTURE IS THE MAJORITY OF THE COST (365 of 559) — anyone
optimising against the old number would have gone after the hook invocations, i.e. the
wrong half, and would also have been tempted to break the subprocess boundary that is
itself part of what a security-gate test must verify.
Wall-clock for that file alone on an otherwise-idle machine: 46-67s observed across
runs, against the 90s PER_TEST_TIMEOUT_SECONDS below. That thin and variable a margin
is the whole reason the retry above exists; under real multi-session load it exceeds
90s (absorbed by the retry) and can exceed 180s (a hard block). Fix: OI-059.

OVERRIDE (shared contract, hooks/lib/override_tokens.py — same shape as the doctrine
gate's allow-doctrine-drift). A token lives at
  ~/.claude/hooks/sessions/<session_id>/overrides/allow-hook-test-failure
valid 60 minutes from its mtime, content must declare `scope: hook-test-failure` and a
`session:` matching the pushing session. Create it ONLY after Gabriel's explicit
in-turn confirmation; scheduled/headless sessions must NEVER self-create one. Every use
is LOGGED (newest-first) to memory/event_log.md via maintenance/append-event-log.py.
Mirrors the doctrine gate's posture exactly: a bare-terminal push (no
CLAUDE_CODE_SESSION_ID in the environment) cannot be overridden at all.

SESSION IDENTITY / FAIL-CLOSED / clean-run short-circuit: identical reasoning to
git-prepush-doctrine-gate.py — see that file's docstring; not repeated here.

Install (done 2026-07-24; re-do after any fresh clone — the .git/hooks/pre-push shim
is NOT version-controlled, this script and its siblings ARE). The shim runs THREE
tracked checks in order — doctrine-drift gate, then this hook-test gate, then the
fail-closed confidentiality scan (the first two take </dev/null so neither consumes
git's ref stdin; the final exec hands that stdin to the confidentiality scan
unchanged):
  .git/hooks/pre-push  ->  #!/bin/sh
                           ROOT="$(git rev-parse --show-toplevel)"
                           python "$ROOT/hooks/git-prepush-doctrine-gate.py" "$@" </dev/null || exit $?
                           python "$ROOT/hooks/git-prepush-hook-tests-gate.py" "$@" </dev/null || exit $?
                           exec python "$ROOT/hooks/git-prepush-confidential-scan.py" "$@"

Exit 0 = allow push (all tests pass, or failures with a valid logged override).
Exit 1 = block (a real test failure, no valid override) — git pre-push convention.
"""
import concurrent.futures
import glob
import importlib.util
import os
import subprocess
import sys
from datetime import datetime

HOOK_DIR = os.path.dirname(os.path.abspath(__file__))
CLAUDE_DIR = os.path.dirname(HOOK_DIR)
LIB_DIR = os.path.join(HOOK_DIR, "lib")
sys.path.insert(0, LIB_DIR)
# NO fallback on this import, same reasoning as the doctrine gate: a missing
# override_tokens module must not degrade to a looser local check — it blocks instead.
from override_tokens import Tier, token_grants, describe_token  # noqa: E402

HOOK_TEST_FAILURE = Tier("allow-hook-test-failure", "hook-test-failure", 3600, single_use=False)
APPEND_LOG_SCRIPT = os.path.join(CLAUDE_DIR, "maintenance", "append-event-log.py")
PER_TEST_TIMEOUT_SECONDS = 90
# One rerun at PER_TEST_TIMEOUT_SECONDS * this, for first-run timeouts ONLY (load-flake
# policy — see the module docstring). A doubled budget covers the 559-spawn outlier
# generically; deliberately NOT a per-file known-slow roster, which would rot.
TIMEOUT_RETRY_MULTIPLIER = 2
ENV_SKIP_SENTINEL = "CANNOT RUN:"
# Bounded worker pool for run_suite() (added 2026-07-26, OI-028 root cause — see
# run_suite()'s docstring). Fixed, not os.cpu_count()-scaled: this gate runs on
# Gabriel's interactive daily-driver machine during a live push, and several
# discovered files (e.g. test-eos-review-gate.py, 559 subprocess spawns) are
# themselves subprocess-heavy, so scaling to all logical cores would let one push
# oversubscribe the host. 8 is comfortably below the 16-core machine this was
# measured on and still collapses the observed 137s sequential runtime to roughly
# the single slowest file's own duration (a few seconds), not floor-to-zero.
MAX_PARALLEL_TESTS = 8

# git sets these in a hook process's own environment so IT can operate on the outer
# repo. Every test file is spawned as a subprocess of THIS gate, so without stripping
# them here, each test would inherit them too -- silently redirecting any `git -C
# <tempdir>` call a test makes (against its own throwaway fixture repo) back onto the
# outer repo instead. Same bug class as commit 337a7af, which patched each affected
# test file's own os.environ individually; fixing it here at the spawn point covers
# every test file, including ones not touched by that commit.
GIT_ENV_LEAK_VARS = (
    "GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR",
    "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_PREFIX",
)

# Every tracked python test tree, as ~/.claude-relative path parts. See the module
# docstring for why hooks/ itself is excluded and why these are listed rather than walked.
TEST_ROOTS = (
    ("hooks", "tests"),
    ("maintenance",),
    ("maintenance", "_tests"),
)
# Both repo naming conventions, applied to every root (see docstring).
TEST_FILE_PATTERNS = ("test-*.py", "test_*.py")

# Test seam only (mirrors the doctrine gate's EVENT_LOG_OVERRIDE/STATUS_PATH_OVERRIDE):
# when set, discovery reads from THIS directory alone instead of the real TEST_ROOTS.
# None -> canonical.
TESTS_DIR_OVERRIDE = None
EVENT_LOG_OVERRIDE = None


def default_tests_dir():
    """The primary tree. Kept as the single-root accessor for callers that want one
    directory; discovery itself goes through default_test_dirs()."""
    return TESTS_DIR_OVERRIDE or os.path.join(CLAUDE_DIR, "hooks", "tests")


def default_test_dirs():
    """Every directory discovery sweeps. The override seam collapses this to one dir so
    a test can point the gate at a throwaway fixture tree."""
    if TESTS_DIR_OVERRIDE:
        return [TESTS_DIR_OVERRIDE]
    return [os.path.join(CLAUDE_DIR, *parts) for parts in TEST_ROOTS]


def discover_test_files(root=None):
    """Every test file across the discovery roots (or `root` alone, when given), both
    naming styles, de-duplicated and sorted for stable, deterministic run order."""
    found = set()
    for directory in ([root] if root else default_test_dirs()):
        for pattern in TEST_FILE_PATTERNS:
            found.update(glob.glob(os.path.join(directory, pattern)))
    return sorted(found)


def display_name(path):
    """Label for reports. Repo-relative (posix) when the file lives under ~/.claude, so
    same-named files in different trees stay distinguishable — maintenance/_tests/ and
    hooks/tests/ both carry a doctrine-gate test. Bare basename for anything outside the
    repo (fixture files in a tempdir have no meaningful repo-relative form)."""
    try:
        rel = os.path.relpath(os.path.abspath(path), CLAUDE_DIR)
    except ValueError:  # different drive on Windows -- not under CLAUDE_DIR
        return os.path.basename(path)
    if rel.startswith(os.pardir):
        return os.path.basename(path)
    return rel.replace(os.sep, "/")


def run_test_file(path, timeout=None):
    """Run one test file exactly as a human would (`python <file>`). Returns (rc,
    combined_output, timed_out). A timeout is reported as rc 124 (shell convention)
    with a synthetic message, PLUS timed_out=True — the retry policy in run_suite()
    keys on that flag, never on the rc, so a child that merely EXITS 124 by itself is
    a deterministic failure and earns no retry (review finding, 2026-07-26). See the
    module docstring for how a first genuine timeout is retried before it can block."""
    timeout = timeout if timeout is not None else PER_TEST_TIMEOUT_SECONDS
    env = {k: v for k, v in os.environ.items() if k not in GIT_ENV_LEAK_VARS}
    try:
        proc = subprocess.run(
            [sys.executable, path],
            capture_output=True, text=True, timeout=timeout, env=env,
        )
        return proc.returncode, (proc.stdout or "") + (proc.stderr or ""), False
    except subprocess.TimeoutExpired as e:
        partial = (e.stdout or "") if isinstance(e.stdout, str) else ""
        return 124, partial + "\nTIMEOUT after %ss\n" % timeout, True
    except Exception as e:  # pragma: no cover - defensive
        return 1, "COULD NOT LAUNCH: %s\n" % e, False


def classify(rc, output):
    """pass | env-skip | fail. See module docstring for the ENV-SKIP contract."""
    if rc == 0:
        return "pass"
    if ENV_SKIP_SENTINEL in (output or ""):
        return "env-skip"
    return "fail"


def _run_one(path):
    """Run a single test file end-to-end, including the timeout-retry policy. Split
    out of run_suite() (2026-07-26) so it can be dispatched to a worker pool — same
    logic as before, just callable per-file instead of inline in a sequential loop.
    References run_test_file by module-global name (not a captured local), so a test
    that monkeypatches gt.run_test_file still intercepts calls made from a worker
    thread — normal Python global lookup-at-call-time, unaffected by which thread
    calls it."""
    rc, output, timed_out = run_test_file(path)
    timeout_retried = False
    if timed_out:
        timeout_retried = True
        rc, output, _ = run_test_file(
            path, timeout=PER_TEST_TIMEOUT_SECONDS * TIMEOUT_RETRY_MULTIPLIER)
    return {
        "file": display_name(path),
        "rc": rc,
        "status": classify(rc, output),
        "output": output,
        "timeout_retried": timeout_retried,
    }


def run_suite(root=None):
    """[{"file", "rc", "status", "output", "timeout_retried"}] for every discovered
    test file, in DISCOVERY (sorted) order. A first-run timeout (the timed_out flag
    from run_test_file, NOT the rc — so a child that merely exits 124 is a
    deterministic failure, no retry) gets one rerun at the doubled budget; the
    rerun's rc/output replace the first run's and are what classify() judges.
    timeout_retried records that the rerun happened, whatever its outcome, so the
    summary can disclose it.

    Runs discovered files CONCURRENTLY, bounded by MAX_PARALLEL_TESTS (2026-07-26,
    OI-028 root cause). WHY: a live push trace showed this gate running all ~54
    tracked test files SEQUENTIALLY, one subprocess at a time, for 137s wall-clock —
    while the actual network push (git send-pack) that ran immediately after
    completed in 0.54s. That 137s is what open-items-tracker.md's OI-028 had logged
    as the push itself "hanging"; it was never the network call, it was this loop.
    Each file is an independent subprocess with no shared state (env-var stripping
    and the timeout/retry policy are both already scoped per-file in _run_one/
    run_test_file), so there is no correctness reason to serialize them. Output order
    is restored to the original discovery order after collection, regardless of which
    worker finishes first, so reports stay deterministic/diffable run to run."""
    paths = discover_test_files(root)
    if not paths:
        return []
    results_by_path = {}
    workers = min(MAX_PARALLEL_TESTS, len(paths))
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        future_to_path = {pool.submit(_run_one, path): path for path in paths}
        for future in concurrent.futures.as_completed(future_to_path):
            results_by_path[future_to_path[future]] = future.result()
    return [results_by_path[path] for path in paths]


def any_real_failure(results):
    return any(r.get("status") == "fail" for r in results)


def format_summary(results):
    """A human-readable report: counts, then the tail of every FAIL's output (enough
    to diagnose without re-running by hand), then a one-line list of ENV-SKIPs."""
    passed = [r for r in results if r["status"] == "pass"]
    failed = [r for r in results if r["status"] == "fail"]
    skipped = [r for r in results if r["status"] == "env-skip"]
    lines = ["hook-tests-gate: %d pass, %d fail, %d env-skip (of %d)"
             % (len(passed), len(failed), len(skipped), len(results))]
    for r in failed:
        tail = "\n".join((r["output"] or "").splitlines()[-8:])
        # .get(): stubbed/legacy result dicts may predate the timeout_retried key.
        note = ", after a timeout retry" if r.get("timeout_retried") else ""
        lines.append("--- FAIL: %s (exit %s%s) ---\n%s" % (r["file"], r["rc"], note, tail))
    if skipped:
        lines.append("env-skip (not blocking): " + ", ".join(r["file"] for r in skipped))
    recovered = [r for r in passed if r.get("timeout_retried")]
    if recovered:
        lines.append("timeout-retry (timed out under load, passed on the doubled-budget "
                     "rerun; not blocking): " + ", ".join(r["file"] for r in recovered))
    return "\n".join(lines)


def current_session_id():
    return os.environ.get("CLAUDE_CODE_SESSION_ID") or None


def override_token(session_id):
    return token_grants(session_id, HOOK_TEST_FAILURE)


def override_active(session_id):
    return override_token(session_id) is not None


def decide(any_fail, override_is_active):
    """Pure decision, same shape as the doctrine gate's decide().
      no real failure                 -> (0, False)  allow, nothing to log.
      real failure, overridden        -> (0, True)   allow + LOG.
      real failure, no override       -> (1, False)  BLOCK."""
    if not any_fail:
        return 0, False
    if override_is_active:
        return 0, True
    return 1, False


def build_override_entry(now=None, session_id=None, reason=None):
    now = now or datetime.now()
    reason = (reason or "").strip() or "<none given in the token>"
    return (
        "## %s — Pre-push proceeded DESPITE a hook test failure (allow-hook-test-failure override used)\n\n"
        "- The `~/.claude` git pre-push hook-tests gate (`hooks/git-prepush-hook-tests-gate.py`) ran the "
        "full test suite (`hooks/tests/`, `maintenance/`, `maintenance/_tests/`) and found a real "
        "failure, but session `%s` held a valid "
        "`allow-hook-test-failure` token (session-scoped, `scope: hook-test-failure`, < 60 min from "
        "mtime), so the push was ALLOWED rather than blocked.\n"
        "- Reason recorded in the token: %s\n"
        "- Mechanical record only, per the rules.md override protocol (token created only after "
        "Gabriel's explicit in-turn confirmation; headless sessions never self-create one). Override "
        "used at %s local.\n"
        % (now.strftime("%Y-%m-%d"), session_id or "<unknown>", reason,
           now.strftime("%Y-%m-%d %H:%M:%S"))
    )


def log_override_use(session_id=None, reason=None):
    entry = build_override_entry(session_id=session_id, reason=reason)
    cmd = [sys.executable, APPEND_LOG_SCRIPT]
    if EVENT_LOG_OVERRIDE:
        cmd += ["--log", EVENT_LOG_OVERRIDE]
    try:
        subprocess.run(cmd, input=entry.encode("utf-8"), capture_output=True)
    except Exception as e:  # pragma: no cover - defensive
        sys.stderr.write(
            "pre-push hook-tests gate: override used but event_log append FAILED (%s) - "
            "record it manually.\n" % e)


def main():
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except Exception:
            pass
    results = run_suite()
    # Fail-closed floor (code review finding, 2026-07-25): discovery now sweeps three
    # independently-vanishable roots instead of one. glob.glob() on a missing directory
    # returns [] rather than raising, so a miscomputed CLAUDE_DIR or an accidentally
    # emptied/renamed root would otherwise silently produce "0 pass, 0 fail, 0 env-skip"
    # and exit 0 -- a fully neutered, silently-passing gate. That is a DIFFERENT failure
    # class than "a discovered test failed" (this is "we found no tests to run at all"),
    # so it is deliberately NOT eligible for the allow-hook-test-failure override token
    # (wrong scope) and blocks unconditionally, even with no session id.
    if not results:
        sys.stdout.write(
            "hook-tests-gate: 0 tests discovered across %d root(s) -- treating as a "
            "gate failure, not a clean run.\n" % len(default_test_dirs()))
        sys.stderr.write(
            "pre-push BLOCKED: git-prepush-hook-tests-gate.py discovered ZERO test files "
            "(expected roots: %s). This means the gate itself is broken (missing "
            "directory, bad CLAUDE_DIR, or discovery regression) -- fix discovery, do not "
            "override; no allow-hook-test-failure token can bypass this, it is the wrong "
            "scope for an empty suite.\n" % ", ".join(default_test_dirs()))
        return 1
    # Same floor, per-root (independent review finding, 2026-07-25): the check above only
    # catches TOTAL emptiness across all three roots. If exactly one root silently vanished
    # (e.g. hooks/tests/ itself -- which also carries this gate's OWN sentinel test, so its
    # loss would otherwise be invisible: the other two roots still yield files, any_fail
    # stays False, and the gate would exit 0 having quietly dropped a third of its coverage)
    # that must block too, for the same "broken gate, not a failing test" reason, and for
    # the same reason it is NOT eligible for the hook-test-failure override token.
    empty_roots = [d for d in default_test_dirs() if not discover_test_files(d)]
    if empty_roots:
        sys.stdout.write(
            "hook-tests-gate: %d/%d root(s) discovered 0 tests -- treating as a gate "
            "failure, not a clean run.\n" % (len(empty_roots), len(default_test_dirs())))
        sys.stderr.write(
            "pre-push BLOCKED: git-prepush-hook-tests-gate.py found test files overall, "
            "but these discovery root(s) yielded ZERO: %s. That silently drops a slice of "
            "coverage rather than exercising it -- fix discovery, do not override; no "
            "allow-hook-test-failure token can bypass this, it is the wrong scope for a "
            "vanished root.\n" % ", ".join(empty_roots))
        return 1
    sys.stdout.write(format_summary(results) + "\n")
    any_fail = any_real_failure(results)
    session_id = current_session_id()
    # Look for a token ONLY when there is a real failure to override — same
    # speculative-consume avoidance as the doctrine gate (HOOK_TEST_FAILURE is
    # multi-use today, making this latent rather than live, same posture as there).
    fields = override_token(session_id) if any_fail else None
    exit_code, log_override = decide(any_fail, fields is not None)
    if log_override:
        log_override_use(session_id, (fields or {}).get("reason"))
        sys.stderr.write(
            "pre-push: hook test failure present but OVERRIDDEN - session %s holds a valid "
            "allow-hook-test-failure token. Push ALLOWED; the override was logged to "
            "event_log.md.\n" % session_id)
    elif exit_code != 0:
        sys.stderr.write(
            "pre-push BLOCKED: the tracked test suite has a real failure (see report above). "
            "Fix it first. If Gabriel has just explicitly authorized pushing anyway, write "
            "this override token and retry:\n%s"
            % describe_token(session_id, HOOK_TEST_FAILURE))
        if not session_id:
            sys.stderr.write(
                "  NOTE: this push carries no CLAUDE_CODE_SESSION_ID, so no override can be "
                "honored here at all. Fix the failure — do not try to mint a token.\n")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
