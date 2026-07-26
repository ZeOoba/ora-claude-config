#!/usr/bin/env python3
"""Tests for git-prepush-hook-tests-gate.py — the pre-push gate that runs the FULL
tracked test suite (`hooks/tests/`, `maintenance/`, `maintenance/_tests/`) and blocks a
push when any test genuinely fails.

Fully isolated: TESTS_DIR_OVERRIDE points discovery at a throwaway fixture directory
(never the real hooks/tests/), and the override-token sessions root is redirected via
ORA_OVERRIDE_SESSIONS_DIR (the same test seam the doctrine gate uses), so this suite
never touches the real hooks/sessions/ or the canonical event_log.md.

WHY THIS GATE EXISTS: commit 7d01eff rewrote shared-checkout-guard.py's attribution
logic but left its own test asserting the PRE-fix contract — a behavior-changing hook
fix landed without its test updated in the same commit, and nothing but a human
manually running the suite would ever have caught it. Run: python
test-git-prepush-hook-tests-gate.py (exit 0 = pass)
"""
import contextlib
import importlib.util
import io
import os
import stat
import sys
import tempfile

HOOKS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location(
    "gt", os.path.join(HOOKS, "git-prepush-hook-tests-gate.py"))
gt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gt)

SESSION = "test-session-0002"
results = []


def expect(label, cond, detail=""):
    results.append((bool(cond), label))
    if not cond:
        print("  FAIL: %s %s" % (label, detail))


def mint(root, session_id, content, name=None):
    name = name or gt.HOOK_TEST_FAILURE.name
    d = os.path.join(root, session_id, "overrides")
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, name)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)
    return path


def good_token(session_id=SESSION):
    return ("scope: hook-test-failure\n"
            "session: %s\n"
            "reason: Gabriel approved pushing despite a known-flaky test\n"
            % session_id)


def write_dummy_test(root, basename, body):
    path = os.path.join(root, basename)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(body)
    return path


# --- fixture: a throwaway tests/ directory with 3 dummy test files -----------------
fixture_root = tempfile.mkdtemp(prefix="gt-fixture-")
write_dummy_test(fixture_root, "test-good.py", "print('ok')\n")
write_dummy_test(fixture_root, "test-bad.py",
                  "print('boom: assertion failed')\nimport sys; sys.exit(1)\n")
write_dummy_test(fixture_root, "test-envskip.py",
                  "print('CANNOT RUN: fixture terms file unreadable')\n"
                  "import sys; sys.exit(1)\n")
# A non-matching file (no test- prefix) must NOT be discovered.
write_dummy_test(fixture_root, "helper.py", "print('not a test')\n")

# --- discover_test_files(), explicit root -------------------------------------------
found = gt.discover_test_files(fixture_root)
found_names = sorted(os.path.basename(p) for p in found)
expect("discover: finds exactly the 3 test-*.py fixtures",
       found_names == ["test-bad.py", "test-envskip.py", "test-good.py"],
       "got %r" % found_names)

# Both naming styles are honored in any root: hooks/tests/ uses "test-*.py" (hyphen)
# but maintenance/ and maintenance/_tests/ use "test_*.py" (underscore), and
# maintenance/ itself carries BOTH. A single-pattern glob is what left the maintenance
# trees unreachable in the first place.
write_dummy_test(fixture_root, "test_underscore.py", "print('ok')\n")
found_both = sorted(os.path.basename(p) for p in gt.discover_test_files(fixture_root))
expect("discover: picks up test_*.py (underscore) alongside test-*.py",
       found_both == ["test-bad.py", "test-envskip.py", "test-good.py",
                      "test_underscore.py"],
       "got %r" % found_both)
expect("discover: still excludes non-test files (helper.py)",
       "helper.py" not in found_both)
os.remove(os.path.join(fixture_root, "test_underscore.py"))

# --- discover_test_files(), CANONICAL roots (no explicit root) -----------------------
# The gate must sweep all three real trees. Asserted by MEMBERSHIP of known-tracked
# files, never by count, so landing or retiring an unrelated test never breaks this.
canonical = gt.discover_test_files()
canonical_rel = {gt.display_name(p) for p in canonical}
for expected in ("hooks/tests/test-secret-patterns.py",          # hyphen style
                 "hooks/tests/test-git-prepush-hook-tests-gate.py",
                 "maintenance/test-append-event-log.py",          # hyphen style
                 "maintenance/test_open_sessions_probe.py",       # underscore style
                 "maintenance/_tests/test_hardening.py",          # nested tree
                 "maintenance/_tests/test_fleet_contract_check.py"):
    expect("discover (canonical): covers %s" % expected,
           expected in canonical_rel,
           "not in discovered set of %d" % len(canonical_rel))

expect("discover (canonical): no duplicate paths across roots/patterns",
       len(canonical) == len(set(canonical)),
       "%d paths, %d unique" % (len(canonical), len(set(canonical))))
# glob is non-recursive, so the maintenance/ sweep must NOT re-collect maintenance/_tests/
# entries under a second path spelling, and must not reach into hooks/tests/ subdirs.
expect("discover (canonical): deterministic ordering (sorted)",
       canonical == sorted(canonical))
# hooks/ ROOT is deliberately NOT a discovery root: hooks/test-ora-autonomy-gate.py is a
# stale duplicate of the hooks/tests/ copy, and the gate must not certify an orphan.
expect("discover (canonical): hooks/ root itself is not swept",
       "hooks/test-ora-autonomy-gate.py" not in canonical_rel)

# --- display_name(): repo-relative inside ~/.claude, bare basename outside ------------
# Two trees can hold same-named files, so FAIL lines must be unambiguous; but fixture
# files in a tempdir have no meaningful repo-relative form, so they fall back to basename.
expect("display_name: repo file -> posix repo-relative path",
       gt.display_name(os.path.join(gt.CLAUDE_DIR, "maintenance", "_tests",
                                    "test_hardening.py"))
       == "maintenance/_tests/test_hardening.py")
expect("display_name: file outside ~/.claude -> bare basename",
       gt.display_name(os.path.join(fixture_root, "test-good.py")) == "test-good.py")

# --- TESTS_DIR_OVERRIDE seam still narrows discovery to exactly one directory ---------
gt.TESTS_DIR_OVERRIDE = fixture_root
try:
    narrowed = {os.path.basename(p) for p in gt.discover_test_files()}
    expect("TESTS_DIR_OVERRIDE: discovery is confined to the override dir",
           narrowed == {"test-bad.py", "test-envskip.py", "test-good.py"},
           "got %r" % sorted(narrowed))
finally:
    gt.TESTS_DIR_OVERRIDE = None

# --- run_test_file() + classify() ---------------------------------------------------
rc_good, out_good, to_good = gt.run_test_file(os.path.join(fixture_root, "test-good.py"))
expect("run: good test exits 0", rc_good == 0, "got %r" % rc_good)
expect("run: good test is not flagged timed_out", to_good is False)
expect("classify: rc 0 -> pass", gt.classify(rc_good, out_good) == "pass")

rc_bad, out_bad, to_bad = gt.run_test_file(os.path.join(fixture_root, "test-bad.py"))
expect("run: bad test exits 1", rc_bad == 1, "got %r" % rc_bad)
expect("run: bad test is not flagged timed_out", to_bad is False)
expect("classify: rc != 0, no CANNOT RUN sentinel -> fail",
       gt.classify(rc_bad, out_bad) == "fail")

rc_skip, out_skip, _ = gt.run_test_file(os.path.join(fixture_root, "test-envskip.py"))
expect("run: env-skip test exits 1", rc_skip == 1, "got %r" % rc_skip)
expect("classify: rc != 0 WITH 'CANNOT RUN:' sentinel -> env-skip",
       gt.classify(rc_skip, out_skip) == "env-skip")

expect("classify: a timeout (no sentinel) is a real failure, not env-skip",
       gt.classify(124, "TIMEOUT after 90s\n") == "fail")

# --- run_test_file(): must not leak git hook env vars into the test subprocess --------
# Simulates git's own pre-push hook environment: git sets GIT_DIR/GIT_WORK_TREE (and
# friends) in the hook process's env so IT can operate on the outer repo. Bug: this
# gate's run_test_file() spawned each test file via subprocess.run() with no env=
# override, so every discovered test inherited these vars too -- silently redirecting
# any `git -C <tempdir>` call a test makes back onto the outer repo instead of its own
# temp fixture (same bug class fixed per-test-file in commit 337a7af; never fixed here).
leak_probe_root = tempfile.mkdtemp(prefix="gt-leak-probe-")
leak_probe = write_dummy_test(
    leak_probe_root, "test-leak-probe.py",
    "import os, sys\n"
    "leaked = [v for v in ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE', 'GIT_COMMON_DIR',\n"
    "                       'GIT_OBJECT_DIRECTORY', 'GIT_ALTERNATE_OBJECT_DIRECTORIES',\n"
    "                       'GIT_PREFIX') if v in os.environ]\n"
    "if leaked:\n"
    "    print('LEAKED: %r' % leaked)\n"
    "    sys.exit(1)\n"
    "print('clean')\n"
    "sys.exit(0)\n")

_leak_env_vars = {
    "GIT_DIR": r"C:\fake\.git", "GIT_WORK_TREE": r"C:\fake",
    "GIT_INDEX_FILE": r"C:\fake\.git\index", "GIT_COMMON_DIR": r"C:\fake\.git",
    "GIT_OBJECT_DIRECTORY": r"C:\fake\.git\objects",
    "GIT_ALTERNATE_OBJECT_DIRECTORIES": r"C:\fake\.git\alt", "GIT_PREFIX": "",
}
_saved_env = {k: os.environ.get(k) for k in _leak_env_vars}
os.environ.update(_leak_env_vars)
try:
    rc_leak, out_leak, _ = gt.run_test_file(leak_probe)
finally:
    for k, v in _saved_env.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v

expect("run_test_file: parent's GIT_DIR/GIT_WORK_TREE/etc. do not leak into the "
       "test subprocess", rc_leak == 0, "got rc=%r out=%r" % (rc_leak, out_leak))

# --- run_suite() ---------------------------------------------------------------------
suite = gt.run_suite(fixture_root)
by_file = {r["file"]: r["status"] for r in suite}
expect("run_suite: 3 results, one per fixture", len(suite) == 3, "got %r" % suite)
expect("run_suite: statuses match", by_file == {
    "test-good.py": "pass", "test-bad.py": "fail", "test-envskip.py": "env-skip",
}, "got %r" % by_file)

# --- timeout-retry policy (load-flake evidence, 2026-07-26) ---------------------------
# During a push with three other live sessions, test-eos-review-gate.py (48 subprocess
# spawns, the suite's outlier) blew the flat 90s budget (exit 124) and blocked the push;
# rerun in isolation moments later it passed all 48 quickly. Policy under test: a FIRST
# timeout earns exactly ONE rerun of that file at a doubled budget; the rerun's result
# is authoritative (a second timeout, or a non-timeout failure on the rerun, is a real
# blocking FAIL). A non-timeout failure is NEVER retried — a deterministic assertion
# failure must not get two bites at the gate.
retry_root = tempfile.mkdtemp(prefix="gt-retry-")
retry_marker = os.path.join(retry_root, "flaky-first-run.marker")
write_dummy_test(retry_root, "test-flaky-timeout.py",
                 "import os, sys, time\n"
                 "marker = %r\n"
                 "if not os.path.exists(marker):\n"
                 "    open(marker, 'w').close()\n"
                 "    time.sleep(30)\n"
                 "print('ok on rerun')\n"
                 "sys.exit(0)\n" % retry_marker)
write_dummy_test(retry_root, "test-hung.py",
                 "import time\ntime.sleep(30)\nprint('never reached')\n")
write_dummy_test(retry_root, "test-plain-fail.py",
                 "print('boom: deterministic failure')\nimport sys; sys.exit(1)\n")
# A child that EXITS 124 by itself (no hang): rc alone must not trigger the retry —
# the policy keys on run_test_file()'s timed_out flag, not on the exit code (REFUTE
# review finding, 2026-07-26).
write_dummy_test(retry_root, "test-fake-124.py",
                 "print('deterministically exiting 124')\nimport sys; sys.exit(124)\n")

# Record every run_test_file() call (file + timeout arg) while still really running the
# subprocess, so retry COUNT and the retry's enlarged BUDGET are asserted directly
# instead of via wall-clock timing (which would itself be load-flaky).
_rtf_calls = []
_real_rtf = gt.run_test_file
def _recording_rtf(path, timeout=None):
    _rtf_calls.append((os.path.basename(path), timeout))
    return _real_rtf(path, timeout)
gt.run_test_file = _recording_rtf
_real_budget = gt.PER_TEST_TIMEOUT_SECONDS
gt.PER_TEST_TIMEOUT_SECONDS = 3
try:
    retry_suite = gt.run_suite(retry_root)
finally:
    gt.PER_TEST_TIMEOUT_SECONDS = _real_budget
    gt.run_test_file = _real_rtf
retry_by_file = {r["file"]: r for r in retry_suite}

flaky = retry_by_file.get("test-flaky-timeout.py", {})
expect("timeout-retry: first-run timeout + passing rerun -> pass (not blocking)",
       flaky.get("status") == "pass", "got %r" % (flaky,))
expect("timeout-retry: the recovered pass is marked timeout_retried",
       flaky.get("timeout_retried") is True, "got %r" % (flaky,))

hung = retry_by_file.get("test-hung.py", {})
expect("timeout-retry: a second timeout is still a real FAIL (rc 124)",
       hung.get("status") == "fail" and hung.get("rc") == 124, "got %r" % (hung,))
expect("timeout-retry: the twice-timed-out file is marked timeout_retried",
       hung.get("timeout_retried") is True, "got %r" % (hung,))

plain = retry_by_file.get("test-plain-fail.py", {})
expect("timeout-retry: non-timeout failure stays FAIL",
       plain.get("status") == "fail", "got %r" % (plain,))
expect("timeout-retry: non-timeout failure is not marked retried",
       plain.get("timeout_retried") is False, "got %r" % (plain,))

fake124 = retry_by_file.get("test-fake-124.py", {})
expect("timeout-retry: a child that itself EXITS 124 stays FAIL",
       fake124.get("status") == "fail" and fake124.get("rc") == 124,
       "got %r" % (fake124,))
expect("timeout-retry: a deterministic exit-124 is NOT marked retried",
       fake124.get("timeout_retried") is False, "got %r" % (fake124,))

flaky_calls = [c for c in _rtf_calls if c[0] == "test-flaky-timeout.py"]
hung_calls = [c for c in _rtf_calls if c[0] == "test-hung.py"]
plain_calls = [c for c in _rtf_calls if c[0] == "test-plain-fail.py"]
fake124_calls = [c for c in _rtf_calls if c[0] == "test-fake-124.py"]
expect("timeout-retry: a timed-out file is run exactly TWICE, never more",
       len(flaky_calls) == 2 and len(hung_calls) == 2,
       "got flaky=%r hung=%r" % (flaky_calls, hung_calls))
expect("timeout-retry: a non-timeout failure is run exactly ONCE",
       len(plain_calls) == 1, "got %r" % (plain_calls,))
expect("timeout-retry: a deterministic exit-124 is run exactly ONCE (flag, not rc, "
       "triggers the retry)", len(fake124_calls) == 1, "got %r" % (fake124_calls,))
expect("timeout-retry: the rerun gets a DOUBLED budget (base 3 -> retry 6)",
       len(flaky_calls) == 2 and flaky_calls[0][1] is None and flaky_calls[1][1] == 6,
       "got %r" % (flaky_calls,))

expect("any_real_failure: a timeout-retried PASS does not block",
       gt.any_real_failure([flaky]) is False)

# Visibility: a flake that recovered must be DISCLOSED in the report, not silently
# eaten, and the twice-timed-out FAIL block must still appear with its exit code.
retry_summary = gt.format_summary(retry_suite)
expect("format_summary: discloses the timeout-retried pass by name",
       "timeout-retry" in retry_summary and "test-flaky-timeout.py" in retry_summary,
       "got %r" % retry_summary)
expect("format_summary: twice-timed-out FAIL block survives with exit 124",
       "test-hung.py" in retry_summary and "124" in retry_summary,
       "got %r" % retry_summary)

# --- any_real_failure() ---------------------------------------------------------------
expect("any_real_failure: pass+env-skip only -> False",
       gt.any_real_failure([{"status": "pass"}, {"status": "env-skip"}]) is False)
expect("any_real_failure: one fail present -> True",
       gt.any_real_failure([{"status": "pass"}, {"status": "fail"}]) is True)
expect("any_real_failure: empty result set -> False",
       gt.any_real_failure([]) is False)

# --- decide() pure decision table (mirrors git-prepush-doctrine-gate.py's shape) ------
expect("decide: no real failure -> allow, no log", gt.decide(False, False) == (0, False))
expect("decide: no real failure + override present -> allow, no log (ignored)",
       gt.decide(False, True) == (0, False))
expect("decide: real failure, no override -> BLOCK", gt.decide(True, False) == (1, False))
expect("decide: real failure + override -> allow + LOG", gt.decide(True, True) == (0, True))

# --- build_override_entry() -----------------------------------------------------------
entry = gt.build_override_entry(session_id=SESSION)
expect("entry: starts with dated '## ' header (append-event-log contract)",
       entry.startswith("## "))
expect("entry: references the override + hook test failure",
       "override" in entry.lower() and "hook test" in entry.lower())

# --- override_active(): smoke-test the shared contract is wired with the RIGHT tier ---
# (token_grants()/parse_token()'s own exhaustive adversarial matrix — duplicate keys,
# oversized, future-dated, path-traversal session ids, etc — is already covered by
# test-git-prepush-doctrine-gate.py and test-ora-autonomy-gate.py against the SAME
# shared hooks/lib/override_tokens.py module. Re-asserting all 13 cases a third time
# here would be redundant padding, not added protection; this section proves only that
# THIS gate's Tier name/scope is wired correctly.)
with tempfile.TemporaryDirectory() as td:
    os.environ["ORA_OVERRIDE_SESSIONS_DIR"] = td

    expect("no token -> False", gt.override_active(SESSION) is False)

    tok = mint(td, SESSION, good_token())
    expect("valid session-scoped token -> True", gt.override_active(SESSION) is True)

    mint(td, SESSION, "scope: doctrine-drift\nsession: %s\n" % SESSION)
    expect("wrong scope (a doctrine-drift token) -> False",
           gt.override_active(SESSION) is False)

    mint(td, SESSION, "scope: hook-test-failure\nsession: some-other-session\n")
    expect("session mismatch inside token -> False", gt.override_active(SESSION) is False)

    import time
    p = mint(td, SESSION, good_token())
    old = time.time() - (gt.HOOK_TEST_FAILURE.ttl + 120)
    os.utime(p, (old, old))
    expect("aged token (> TTL) -> False", gt.override_active(SESSION) is False)

    # --- main() wiring: stub run_suite() at the seam, exercise the full decision path -
    tmp_log = os.path.join(td, "event_log_test.md")
    with open(tmp_log, "w", encoding="utf-8") as f:
        f.write("# test log\n\n## 2000-01-01 — seed\n\n- seed entry\n")
    gt.EVENT_LOG_OVERRIDE = tmp_log

    real_run_suite = gt.run_suite

    # (a) pass + env-skip only -> exit 0, nothing logged.
    gt.run_suite = lambda root=None: [
        {"file": "test-good.py", "status": "pass", "rc": 0, "output": "ok\n"},
        {"file": "test-envskip.py", "status": "env-skip", "rc": 1,
         "output": "CANNOT RUN: no live fixture\n"},
    ]
    os.environ.pop("CLAUDE_CODE_SESSION_ID", None)
    rc_clean = gt.main()
    expect("main: pass+env-skip only -> exit 0", rc_clean == 0, "got %r" % rc_clean)

    # (b) real failure, no session id in env -> BLOCK (bare-terminal push).
    gt.run_suite = lambda root=None: [
        {"file": "test-bad.py", "status": "fail", "rc": 1, "output": "boom\n"},
    ]
    captured = io.StringIO()
    with contextlib.redirect_stdout(captured):
        rc_noSession = gt.main()
    expect("main: real failure + no session id -> exit 1 (BLOCK)",
           rc_noSession == 1, "got %r" % rc_noSession)
    # Regression guard: main() must actually WRITE the format_summary() report before
    # blocking -- a prior draft of this gate silently dropped that write while adding the
    # discovery floor below, so a blocked push showed a stderr "(see report above)" with
    # nothing above it. Assert the real report content lands on stdout, not just the exit
    # code, so that class of regression fails this suite instead of surviving it.
    summary_out = captured.getvalue()
    expect("main: failing run actually PRINTS the summary report to stdout",
           "1 fail" in summary_out and "test-bad.py" in summary_out,
           "captured stdout was %r" % summary_out)

    # (c) real failure, session id present, no token -> BLOCK, nothing logged.
    os.environ["CLAUDE_CODE_SESSION_ID"] = SESSION
    before = open(tmp_log, encoding="utf-8").read()
    rc_noToken = gt.main()
    after = open(tmp_log, encoding="utf-8").read()
    expect("main: real failure + no token -> exit 1 (BLOCK)",
           rc_noToken == 1, "got %r" % rc_noToken)
    expect("main: block path writes nothing to the log", before == after)

    # (d) real failure, valid token -> allow + LOG, reason preserved.
    mint(td, SESSION, good_token())
    rc_override = gt.main()
    logged = open(tmp_log, encoding="utf-8").read()
    expect("main: real failure + valid token -> exit 0 (allowed)",
           rc_override == 0, "got %r" % rc_override)
    expect("main: override use appended to event_log (newest-first)",
           "hook test" in logged.lower() and "override" in logged.lower())
    expect("main: new entry inserted ABOVE the seed (newest-first)",
           logged.index("## 20") < logged.rindex("2000-01-01"))
    expect("main: the override record names the session",
           SESSION in logged, "session id absent from the logged entry")
    expect("main: the override record carries the token's reason",
           "known-flaky test" in logged, "reason text absent from the logged entry")

    # (e) a clean run must not even look for a token (mirrors the doctrine gate's
    # single-use-safety short-circuit; HOOK_TEST_FAILURE is multi-use today, so this is
    # latent-safety rather than a live bug, same posture as the doctrine gate's own test).
    probed = []
    real_override_token = gt.override_token
    gt.override_token = lambda sid: (probed.append(sid), real_override_token(sid))[1]
    gt.run_suite = lambda root=None: [
        {"file": "test-good.py", "status": "pass", "rc": 0, "output": "ok\n"},
    ]
    rc_clean2 = gt.main()
    gt.override_token = real_override_token
    expect("main: clean run -> exit 0", rc_clean2 == 0, "got %r" % rc_clean2)
    expect("main: clean run never looks for a token (no speculative consume)",
           probed == [], "override_token consulted on a clean run: %r" % probed)

    # (f) discovery floor: zero discovered tests is a gate failure in its own right,
    # NOT eligible for the hook-test-failure override (wrong scope -- "no tests found"
    # is a broken gate, not a failing test). Must block even with a valid token present
    # and even with no session id at all.
    gt.run_suite = lambda root=None: []
    mint(td, SESSION, good_token())
    os.environ["CLAUDE_CODE_SESSION_ID"] = SESSION
    rc_empty_with_token = gt.main()
    expect("main: zero discovered tests -> BLOCK even with a valid override token",
           rc_empty_with_token == 1, "got %r" % rc_empty_with_token)

    os.environ.pop("CLAUDE_CODE_SESSION_ID", None)
    rc_empty_no_session = gt.main()
    expect("main: zero discovered tests -> BLOCK with no session id too",
           rc_empty_no_session == 1, "got %r" % rc_empty_no_session)

    # (g) per-root discovery floor: the TOTAL-emptiness check above misses the case where
    # SOME roots still yield files but one silently doesn't (e.g. hooks/tests/ itself
    # vanishing -- which also carries this very gate's own sentinel test, so its loss
    # would otherwise be invisible). Fake a non-empty root + a genuinely empty real
    # directory as the discovery roots, but stub run_suite to return non-empty results
    # (bypassing the total-emptiness branch), and confirm the per-root check still blocks.
    real_default_test_dirs = gt.default_test_dirs
    empty_root = tempfile.mkdtemp(prefix="gt-emptyroot-")
    nonempty_root = tempfile.mkdtemp(prefix="gt-nonemptyroot-")
    write_dummy_test(nonempty_root, "test-x.py", "print('ok')\n")
    gt.default_test_dirs = lambda: [nonempty_root, empty_root]
    gt.run_suite = lambda root=None: [
        {"file": "test-x.py", "status": "pass", "rc": 0, "output": "ok\n"},
    ]
    rc_partial_empty = gt.main()
    gt.default_test_dirs = real_default_test_dirs
    expect("main: one silently-empty root -> BLOCK even though overall results non-empty",
           rc_partial_empty == 1, "got %r" % rc_partial_empty)

    os.environ.pop("ORA_OVERRIDE_SESSIONS_DIR", None)
    os.environ.pop("CLAUDE_CODE_SESSION_ID", None)
    # Restore run_suite so nothing after this point in a future edit silently inherits a
    # gate that discovers zero tests (code review finding, 2026-07-25).
    gt.run_suite = real_run_suite

passed = sum(1 for ok, _ in results if ok)
print("\ngit-prepush-hook-tests-gate tests: %d/%d passed" % (passed, len(results)))
sys.exit(0 if passed == len(results) else 1)
