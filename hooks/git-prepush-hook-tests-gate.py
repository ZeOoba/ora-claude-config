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

WHAT IT RUNS: every hooks/tests/test-*.py file, each as its own subprocess (matching
how a human runs them: `python <file>`, exit 0 = pass). Aggregates PASS/FAIL/ENV-SKIP
and BLOCKS the push if any test genuinely fails.

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

A subprocess TIMEOUT (PER_TEST_TIMEOUT_SECONDS) is classified FAIL, never ENV-SKIP — a
hung test signals a real problem (e.g. an infinite loop introduced by a change), not an
environmental absence.

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
ENV_SKIP_SENTINEL = "CANNOT RUN:"

# Test seam only (mirrors the doctrine gate's EVENT_LOG_OVERRIDE/STATUS_PATH_OVERRIDE):
# when set, discovery reads from here instead of the real hooks/tests/. None -> canonical.
TESTS_DIR_OVERRIDE = None
EVENT_LOG_OVERRIDE = None


def default_tests_dir():
    return TESTS_DIR_OVERRIDE or os.path.join(CLAUDE_DIR, "hooks", "tests")


def discover_test_files(root=None):
    """Every hooks/tests/test-*.py, sorted for stable, deterministic run order."""
    return sorted(glob.glob(os.path.join(root or default_tests_dir(), "test-*.py")))


def run_test_file(path, timeout=None):
    """Run one test file exactly as a human would (`python <file>`). Returns (rc,
    combined_output). A timeout is reported as rc 124 (shell convention for timeout)
    with a synthetic message — classify() below always treats this as FAIL, never
    ENV-SKIP, since a hang is not the same claim as a declared environmental absence."""
    timeout = timeout if timeout is not None else PER_TEST_TIMEOUT_SECONDS
    try:
        proc = subprocess.run(
            [sys.executable, path],
            capture_output=True, text=True, timeout=timeout,
        )
        return proc.returncode, (proc.stdout or "") + (proc.stderr or "")
    except subprocess.TimeoutExpired as e:
        partial = (e.stdout or "") if isinstance(e.stdout, str) else ""
        return 124, partial + "\nTIMEOUT after %ss\n" % timeout
    except Exception as e:  # pragma: no cover - defensive
        return 1, "COULD NOT LAUNCH: %s\n" % e


def classify(rc, output):
    """pass | env-skip | fail. See module docstring for the ENV-SKIP contract."""
    if rc == 0:
        return "pass"
    if ENV_SKIP_SENTINEL in (output or ""):
        return "env-skip"
    return "fail"


def run_suite(root=None):
    """[{"file", "rc", "status", "output"}] for every discovered test file, in order."""
    out = []
    for path in discover_test_files(root):
        rc, output = run_test_file(path)
        out.append({
            "file": os.path.basename(path),
            "rc": rc,
            "status": classify(rc, output),
            "output": output,
        })
    return out


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
        lines.append("--- FAIL: %s (exit %s) ---\n%s" % (r["file"], r["rc"], tail))
    if skipped:
        lines.append("env-skip (not blocking): " + ", ".join(r["file"] for r in skipped))
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
        "full `hooks/tests/` suite and found a real failure, but session `%s` held a valid "
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
            "pre-push BLOCKED: the hooks/tests/ suite has a real failure (see report above). "
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
