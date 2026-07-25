#!/usr/bin/env python3
"""Tests for git-prepush-hook-tests-gate.py — the pre-push gate that runs the FULL
`hooks/tests/` suite and blocks a push when any test genuinely fails.

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
import importlib.util
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

# --- discover_test_files() ----------------------------------------------------------
found = gt.discover_test_files(fixture_root)
found_names = sorted(os.path.basename(p) for p in found)
expect("discover: finds exactly the 3 test-*.py fixtures",
       found_names == ["test-bad.py", "test-envskip.py", "test-good.py"],
       "got %r" % found_names)

# --- run_test_file() + classify() ---------------------------------------------------
rc_good, out_good = gt.run_test_file(os.path.join(fixture_root, "test-good.py"))
expect("run: good test exits 0", rc_good == 0, "got %r" % rc_good)
expect("classify: rc 0 -> pass", gt.classify(rc_good, out_good) == "pass")

rc_bad, out_bad = gt.run_test_file(os.path.join(fixture_root, "test-bad.py"))
expect("run: bad test exits 1", rc_bad == 1, "got %r" % rc_bad)
expect("classify: rc != 0, no CANNOT RUN sentinel -> fail",
       gt.classify(rc_bad, out_bad) == "fail")

rc_skip, out_skip = gt.run_test_file(os.path.join(fixture_root, "test-envskip.py"))
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
    rc_leak, out_leak = gt.run_test_file(leak_probe)
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
    rc_noSession = gt.main()
    expect("main: real failure + no session id -> exit 1 (BLOCK)",
           rc_noSession == 1, "got %r" % rc_noSession)

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

    os.environ.pop("ORA_OVERRIDE_SESSIONS_DIR", None)
    os.environ.pop("CLAUDE_CODE_SESSION_ID", None)

passed = sum(1 for ok, _ in results if ok)
print("\ngit-prepush-hook-tests-gate tests: %d/%d passed" % (passed, len(results)))
sys.exit(0 if passed == len(results) else 1)
