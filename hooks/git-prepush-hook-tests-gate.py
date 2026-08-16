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
rerun, is a real blocking FAIL. NOTE (2026-08-12): the original justification for that
rule — "a test that cannot finish inside DOUBLE the budget even once signals a genuine
hang, not load" — is FALSE, and was disproved in the field; see "LOAD, NOT HANG" below.
Exceeding the doubled budget is still treated as blocking, because a gate that retries
forever gates nothing, but do NOT read a second timeout as evidence of a hang: diagnose
it before overriding. A non-timeout failure is NEVER
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
Of the git spawns, 365 came from the make_repo() fixture (73 runtime calls x 5: init +
2x config + add + commit) and the rest from direct git() helper calls. So 48 was an
~11.6x undercount, and THE FIXTURE WAS THE MAJORITY OF THE COST (365 of 559) — anyone
optimising against the old number would have gone after the hook invocations, i.e. the
wrong half, and would also have been tempted to break the subprocess boundary that is
itself part of what a security-gate test must verify.

FIXED 2026-08-04 by `6dc5df3` (OI-061): the shared `hooks/tests/lib/gitfixture.py`
template-and-copytree helper pays the fixture's ~5 spawns ONCE per process instead of
per call, cutting test-eos-review-gate.py 559 -> 199 spawns and
test-memory-orphan-link-guard.py 272 -> 147. OI-059 and OI-057 were both CLOSED on
2026-08-04 on the strength of that measurement. The paragraph above is retained for its
measurement METHOD (wrap subprocess.Popen with a counter; do NOT count call sites), not
as current figures.

LOAD, NOT HANG (2026-08-12) — why PER_TEST_TIMEOUT_SECONDS is now 240, not 90.
The OI-059 closure held only at the load it was validated against (~56 dirty files, a
handful of live sessions). It did not survive real concurrency. On 2026-08-12 a push hit
26 concurrent sessions, 117 dirty files, 16 logical cores pinned at 100%, 5.6 GB free of
32 GB, and 53 simultaneous python processes. Both spawn-heavy files blew the 90s budget
AND the 180s retry, hard-blocking the push. Rerun in isolation minutes later, on the same
still-loaded box, BOTH PASSED: test-eos-review-gate.py 55/55 in 140s,
test-memory-orphan-link-guard.py 79/79 in 105s. Bare `python -c pass` spawn cost measured
348ms and then 1390ms across two samples minutes apart, against ~30-50ms idle — so the
dominant term is process-creation cost under contention, which no amount of in-test
optimisation controls. Post-fix spawn counts are already near the floor: cutting further
means cutting hook invocations, which OI-059 and OI-061 both forbid, since the subprocess
boundary is part of what these tests exist to verify. Hence a budget raise rather than
another optimisation pass. If this false-blocks again, RAISE THE BUDGET or fix the load —
do not "optimise" the tests by collapsing their subprocess boundary, and do not reach for
the allow-hook-test-failure override as the routine remedy: an override normalised is a
gate disabled.

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
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta

HOOK_DIR = os.path.dirname(os.path.abspath(__file__))
CLAUDE_DIR = os.path.dirname(HOOK_DIR)
LIB_DIR = os.path.join(HOOK_DIR, "lib")
sys.path.insert(0, LIB_DIR)
# NO fallback on this import, same reasoning as the doctrine gate: a missing
# override_tokens module must not degrade to a looser local check — it blocks instead.
from override_tokens import Tier, token_grants, describe_token  # noqa: E402

HOOK_TEST_FAILURE = Tier("allow-hook-test-failure", "hook-test-failure", 3600, single_use=False)
APPEND_LOG_SCRIPT = os.path.join(CLAUDE_DIR, "maintenance", "append-event-log.py")
# RAISED 90 -> 240 on 2026-08-12 (Gabriel-directed) after the 90/180 pair produced a
# FALSE BLOCK on a real push: test-eos-review-gate.py and test-memory-orphan-link-guard.py
# both blew the 180s retry budget, then both passed cleanly when rerun in isolation
# minutes later (55/55 in 140s, 79/79 in 105s). See "LOAD, NOT HANG" in the module
# docstring. 240 is set against the 140s worst observed run plus headroom for the
# spawn-cost variance measured that day: 348ms -> 1390ms per bare python spawn across two
# samples minutes apart, ~30-40x the idle cost, on a 16-core box pinned at 100% CPU with
# 53 concurrent python processes. A tighter budget re-earns the false block; the cost of
# this one is that a genuine hang now takes up to 480s to surface.
PER_TEST_TIMEOUT_SECONDS = 240
# One rerun at PER_TEST_TIMEOUT_SECONDS * this, for first-run timeouts ONLY (load-flake
# policy — see the module docstring). A doubled budget covers the spawn-heavy outliers
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

# Test seam only (mirrors EVENT_LOG_OVERRIDE): when set, the override-frequency counter
# reads/writes THIS path instead of the canonical state file. None -> canonical.
OVERRIDE_USAGE_LOG_OVERRIDE = None
OVERRIDE_USAGE_LOG_PATH = os.path.join(CLAUDE_DIR, "hooks", "_state", "override-usage-log.jsonl")
# How far back "how many times has this exact failure been overridden" looks. 24h
# matches OI-136's own framing ("N times today") without hardcoding a calendar day
# boundary that would reset mid-incident.
OVERRIDE_FREQUENCY_WINDOW_HOURS = 24


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
    fail_retried = False
    first_output = None
    status = classify(rc, output)
    if timed_out:
        timeout_retried = True
        rc, output, _ = run_test_file(
            path, timeout=PER_TEST_TIMEOUT_SECONDS * TIMEOUT_RETRY_MULTIPLIER)
        status = classify(rc, output)
    elif status == "fail":
        # ONE rerun for a FAILING file too (2026-08-10). Load-flake protection used to
        # cover only timeouts, but an oversubscribed host does not always produce a
        # timeout: a wall-clock-sensitive concurrency test fails its ASSERTIONS instead
        # and landed in the one category with no retry, blocking the push outright.
        # Live case: maintenance/_tests/test_allocate_oi_id.py races 12 threads against a
        # 30s lock-wait budget; under this gate's own 8-worker pool one thread missed the
        # deadline and all three of its coupled assertions fell together (9/12). It
        # passed cleanly on the very next push.
        #
        # This does NOT weaken the gate: a genuine failure fails both runs and still
        # blocks. What it removes is a single unlucky sample deciding a push. Deliberately
        # `elif`, so one file can never cost three budgets -- a timed-out file already
        # spent the doubled rerun and does not also get this one.
        #
        # The rerun uses the NORMAL budget: the doubled budget exists for timeouts
        # specifically, and keying it on anything but run_test_file()'s timed_out flag is
        # the exact confusion a 2026-07-26 REFUTE review corrected (a child that merely
        # EXITS 124 is a deterministic failure, not a hang).
        fail_retried = True
        first_output = output
        rc, output, _ = run_test_file(path)
        status = classify(rc, output)
        if status == "env-skip":
            # A rerun that declares "CANNOT RUN:" after run 1 genuinely FAILED must not
            # become a non-blocking skip. Run 1 executed far enough to fail its
            # assertions, which is proof the file CAN run in this environment -- so an
            # env-skip on run 2 is a changed precondition (a sibling worker's lock,
            # fixture handle, or resource state), not a real inability to execute.
            # Without this, a real failure both stops blocking AND vanishes from the
            # report, because format_summary()'s flaky list scans passes only. Found by
            # independent review 2026-08-10, reproduced against the first draft.
            status = "fail"
            output = (output or "") + (
                "\n[gate] rerun reported ENV-SKIP, but the FIRST run failed -- a file "
                "that ran far enough to fail has proven it can run here, so this is a "
                "FAIL, not a skip.\n")
    return {
        "file": display_name(path),
        "rc": rc,
        "status": status,
        "output": output,
        "timeout_retried": timeout_retried,
        "fail_retried": fail_retried,
        # Run 1's output, kept on ANY fail-retry (2026-08-16, OI-174).
        #
        # It used to be kept only when the rerun ALSO failed. That threw the
        # sample away in the one case where it is the only evidence that will
        # ever exist: the rerun PASSES, the push proceeds, and the summary
        # reports "FLAKY" while the failing assertion is gone forever. Every
        # such flake was therefore unfalsifiable after the fact -- the only
        # options were to guess or to wait for a recurrence that discards its
        # evidence too. The reasoning already in this comment ("discarding the
        # first sample is exactly the diagnostic this policy makes more
        # valuable") applies with MORE force to the recovered case, because a
        # still-failing file can simply be rerun by hand, and a recovered one
        # cannot be reproduced on demand at all.
        "first_output": first_output if fail_retried else None,
    }


def run_suite(root=None):
    """[{"file", "rc", "status", "output", "timeout_retried", "fail_retried",
    "first_output"}] for every discovered test file, in DISCOVERY (sorted) order.

    Retry policy — at most ONE rerun per file, never two:
      * A first-run TIMEOUT (the timed_out flag from run_test_file, NOT the rc — so a
        child that merely exits 124 is a deterministic failure, not a hang) gets one
        rerun at the DOUBLED budget.
      * Otherwise a first-run FAIL gets one rerun at the NORMAL budget (2026-08-10):
        load-flake protection previously covered only timeouts, but an oversubscribed
        host also makes wall-clock-sensitive tests fail their ASSERTIONS, which had no
        retry and blocked the push outright.
      * An ENV-SKIP is never rerun. And a fail-retry whose rerun reports env-skip is
        forced back to FAIL — run 1 proved the file can execute here, so run 2's
        "CANNOT RUN:" is a changed precondition, not an inability to run. Without that,
        a real failure would stop blocking AND vanish from the report.

    The rerun's rc/output replace the first run's and are what classify() judges;
    first_output preserves run 1's output when a fail-retry still failed, so a file
    that fails two DIFFERENT ways is diagnosable. timeout_retried / fail_retried record
    that a rerun happened, whatever its outcome, so the summary can disclose it — a
    recovered flake is always named, never silently swallowed.

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


def failure_signature(results):
    """A short, stable id for the CURRENT set of genuinely-failing files (status=="fail"
    only; pass/env-skip never contribute). Same failing files -> same signature
    regardless of run order, output content, or exit code -- two runs of the identical
    flake rarely produce byte-identical output, and the frequency counter exists to
    answer "does THIS test file keep needing an override", not "did the exact same
    stack trace happen twice". Sorted, so worker-thread completion order (run_suite()
    already restores discovery order, but this does not depend on that) never changes
    the id."""
    failing = sorted(r["file"] for r in results if r.get("status") == "fail")
    return hashlib.sha256("\n".join(failing).encode("utf-8")).hexdigest()[:12]


def override_usage_log_path():
    return OVERRIDE_USAGE_LOG_OVERRIDE or OVERRIDE_USAGE_LOG_PATH


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
        # .get(): stubbed/legacy result dicts may predate the retry keys.
        if r.get("timeout_retried"):
            note = ", after a timeout retry"
        elif r.get("fail_retried"):
            # Say it failed TWICE, so nobody reads a blocked push as one bad sample.
            note = ", failed twice (reran once)"
        else:
            note = ""
        lines.append("--- FAIL: %s (exit %s%s) ---\n%s" % (r["file"], r["rc"], note, tail))
        # Both runs failed: show run 1 too. They can fail with DIFFERENT signatures, and
        # that divergence is the strongest signal that the file is racy rather than
        # deterministically broken.
        first = r.get("first_output")
        # Compare the FULL outputs, not the tails. `tail` is 8 lines and a first-run
        # excerpt is 5, so comparing those two declared "failed differently" for
        # byte-identical failures whose output ran past 5 lines -- i.e. most real
        # tracebacks -- pointing the reader at "racy" when the evidence says
        # deterministic. Truncation is for DISPLAY only.
        if first and first.strip() != (r["output"] or "").strip():
            first_tail = "\n".join(first.splitlines()[-5:])
            if first_tail.strip():
                lines.append("    (first run failed differently:)\n%s" % first_tail)
    if skipped:
        lines.append("env-skip (not blocking): " + ", ".join(r["file"] for r in skipped))
    recovered = [r for r in passed if r.get("timeout_retried")]
    if recovered:
        lines.append("timeout-retry (timed out under load, passed on the doubled-budget "
                     "rerun; not blocking): " + ", ".join(r["file"] for r in recovered))
    # Disclosed, never swallowed: trading a blocked push for an INVISIBLE flake would be
    # a worse bug than the one the fail-retry policy fixes. A file listed here is a real
    # flake and wants fixing, even though it did not block this push.
    flaky = [r for r in passed if r.get("fail_retried")]
    if flaky:
        lines.append("fail-retry (FAILED once, passed on the rerun; not blocking, but "
                     "this file is FLAKY and should be fixed): "
                     + ", ".join(r["file"] for r in flaky))
        # THE FIRST ATTEMPT'S OUTPUT (2026-08-16, OI-174). Naming the file was
        # never enough to act on: the rerun passed, so the failure cannot be
        # reproduced on demand, and without the original assertion there is
        # nothing to diagnose -- every occurrence reduced to "it flaked again".
        # This is the only moment that evidence exists.
        for r in flaky:
            excerpt = _flake_excerpt(r.get("first_output"))
            if excerpt:
                lines.append("  first-attempt failure in %s (rerun passed; this is the "
                             "only record of it):" % r["file"])
                for ln in excerpt:
                    lines.append("    | " + ln)
    return "\n".join(lines)


FLAKE_EXCERPT_LINES = 12
FLAKE_EXCERPT_WIDTH = 200


def _flake_excerpt(text, max_lines=None, width=None):
    """The most diagnostic tail of a failed run's output, bounded.

    TAIL, not head: assertion errors, tracebacks and test-runner summaries land
    at the END, while the start is usually banner and progress noise. Bounded
    because this prints on an otherwise-successful push -- a flake report that
    buries the gate's own verdict under a wall of text would get scrolled past,
    which is the same invisibility this fix exists to remove."""
    if not text:
        return []
    max_lines = FLAKE_EXCERPT_LINES if max_lines is None else max_lines
    width = FLAKE_EXCERPT_WIDTH if width is None else width
    lines = [ln.rstrip() for ln in str(text).splitlines() if ln.strip()]
    return [ln[:width] for ln in lines[-max_lines:]]


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
    # --entry-file, NOT stdin. append-event-log.py's stdin branch is a bare
    # sys.stdin.read(), which decodes using the Windows locale (cp1252), so piped
    # UTF-8 arrives DOUBLE-ENCODED: the em dash's E2 80 94 becomes "a<TM>". That is
    # how seven override headings landed in event_log.md corrupted (2026-08-03), and
    # a mangled heading also defeats any same-heading check. The --entry-file branch
    # opens with an explicit encoding="utf-8".
    # Prescribed by memory/feedback_append_event_log_stdin_encoding.md.
    path = None
    try:
        fd, path = tempfile.mkstemp(suffix=".md", prefix="ora-override-entry-")
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
            f.write(entry)
        subprocess.run(cmd + ["--entry-file", path], capture_output=True)
    except Exception as e:  # pragma: no cover - defensive
        sys.stderr.write(
            "pre-push hook-tests gate: override used but event_log append FAILED (%s) - "
            "record it manually.\n" % e)
    finally:
        if path:
            try:
                os.unlink(path)
            except OSError:
                pass


def record_override_use(session_id, signature, now=None):
    """Append one line to the override-frequency JSONL (OI-136 candidate fix 2: "a
    visible counter in the gate's block message ... so the approver weighs the pattern,
    not just the instance"). Best-effort, same posture as log_override_use()'s event_log
    append: this is a visibility aid, not a security control -- decide()'s exit code
    never reads this file -- so a write failure must never block or fail the push."""
    now = now or datetime.now()
    path = override_usage_log_path()
    record = {
        "ts": now.strftime("%Y-%m-%dT%H:%M:%S"),
        "session_id": session_id or "<unknown>",
        "signature": signature,
    }
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
    except OSError as e:  # pragma: no cover - defensive
        sys.stderr.write(
            "pre-push hook-tests gate: override used but the frequency-counter append "
            "FAILED (%s) -- not blocking, this is visibility only.\n" % e)


def override_frequency(signature, now=None, window_hours=None):
    """(count, distinct_session_count) of override uses recorded for this exact failure
    signature within the rolling window. Call AFTER record_override_use() for the same
    `now` and the count/session-count returned include the just-recorded use -- that
    keeps the message's arithmetic trivial ("this failure has now been overridden N
    times") instead of requiring the caller to add 1 and re-derive session-set
    membership by hand.

    Missing or unreadable state file reads as (0, 0), never an error or a crash: a fresh
    machine, a wiped state file, or the file simply not existing yet must not be
    mistaken for repeat-override history, and must never be why a push fails. A
    malformed line (bad JSON, a missing field) is skipped rather than aborting the scan
    -- one corrupt line must not blind the counter to every other line in the file."""
    window_hours = (OVERRIDE_FREQUENCY_WINDOW_HOURS if window_hours is None
                     else window_hours)
    now = now or datetime.now()
    cutoff = now - timedelta(hours=window_hours)
    path = override_usage_log_path()
    sessions = set()
    count = 0
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except OSError:
        return (0, 0)
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        # A line can be VALID JSON and still not be a record -- e.g. a bare number or a
        # JSON array from a future writer, a truncated append, or a stray non-JSONL line.
        # rec.get(...) below would raise AttributeError on anything but a dict, which
        # would propagate out of override_frequency() uncaught and crash main() itself
        # (found in this session's own REFUTE pass, not by an external report).
        if not isinstance(rec, dict):
            continue
        if rec.get("signature") != signature:
            continue
        try:
            ts = datetime.strptime(rec["ts"], "%Y-%m-%dT%H:%M:%S")
        except (KeyError, TypeError, ValueError):
            continue
        if ts < cutoff:
            continue
        count += 1
        sessions.add(rec.get("session_id"))
    return (count, len(sessions))


def _pluralize_count(n, singular="time", plural="times"):
    return "%d %s" % (n, singular if n == 1 else plural)


def override_frequency_note(count, distinct_sessions, window_hours, verb):
    """The human-readable line shared by both the BLOCKED and OVERRIDDEN message paths.
    `verb` distinguishes "already has been" (blocked, informational) from "has now been"
    (overridden, this use included) so the tense matches what actually happened."""
    session_word = "session" if distinct_sessions == 1 else "sessions"
    return (
        "  This exact failure %s overridden %s by %d distinct %s in the last %dh -- "
        "weigh that pattern, not just this instance.\n"
        % (verb, _pluralize_count(count), distinct_sessions, session_word, window_hours)
    )


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
        # OI-136 candidate fix 2: surface the pattern, not just this instance. Recorded
        # AFTER the decision is made and the push is already allowed -- this is a
        # visibility aid on a decision already taken, never a gate on it.
        signature = failure_signature(results)
        now = datetime.now()
        record_override_use(session_id, signature, now=now)
        count, distinct_sessions = override_frequency(signature, now=now)
        sys.stderr.write(override_frequency_note(
            count, distinct_sessions, OVERRIDE_FREQUENCY_WINDOW_HOURS, verb="has now been"))
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
        # Same visibility, before any token is minted: an approver deciding whether to
        # authorize a NEW override should see how often this exact failure already has
        # been. Read-only -- blocking a push must never itself write to the counter, or
        # every retry of a still-broken push would inflate its own frequency count.
        signature = failure_signature(results)
        count, distinct_sessions = override_frequency(signature, now=datetime.now())
        if count > 0:
            sys.stderr.write(override_frequency_note(
                count, distinct_sessions, OVERRIDE_FREQUENCY_WINDOW_HOURS,
                verb="already has been"))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
