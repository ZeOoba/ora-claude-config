"""Tests for check_website_deploy.py -- the OUTBOUND-ACTION check invoked by
website-canonical's netlify CLI wrapper, closing the value-indirection gap (OI-007)
that ora-autonomy-gate.py's Gate 2a shell-text detection is structurally blind to.

Run: python test-check-website-deploy.py
Stdlib only. ASCII-only. Self-contained. Every call isolates
ORA_OVERRIDE_SESSIONS_DIR so the suite never depends on a real live token.
"""
import os
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(HERE, "lib", "check_website_deploy.py")

SESSION_A = "aaaaaaaa-1111-2222-3333-444444444444"
SESSION_B = "bbbbbbbb-5555-6666-7777-888888888888"


def fresh_sessions_dir():
    return tempfile.mkdtemp(prefix="cwd-sess-")


def mint(sessions_dir, session_id=SESSION_A, reason="Gabriel approved in-turn",
         age_seconds=0, raw=None):
    d = os.path.join(sessions_dir, session_id, "overrides")
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, "allow-website-deploy")
    if raw is not None:
        body = raw
    else:
        body = "scope: website-deploy\nsession: %s\nreason: %s\n" % (session_id, reason)
    with open(path, "w", encoding="ascii") as fh:
        fh.write(body)
    if age_seconds:
        old = time.time() - age_seconds
        os.utime(path, (old, old))
    return path


def run(session, sessions_dir=None, extra_args=None):
    env = dict(os.environ)
    env["ORA_OVERRIDE_SESSIONS_DIR"] = sessions_dir if sessions_dir is not None else fresh_sessions_dir()
    args = [sys.executable, SCRIPT]
    if extra_args is not None:
        args += extra_args
    else:
        args += ["--session", session]
    proc = subprocess.run(args, capture_output=True, text=True, env=env)
    return proc.returncode, proc.stdout, proc.stderr


def test_deny_no_token():
    rc, out, err = run(SESSION_A, sessions_dir=fresh_sessions_dir())
    assert rc == 1, "no token must deny (exit 1), got %s (%s)" % (rc, err)
    print("PASS test_deny_no_token")


def test_allow_valid_token():
    d = fresh_sessions_dir()
    path = mint(d)
    rc, out, err = run(SESSION_A, sessions_dir=d)
    assert rc == 0, "a valid token must allow, got %s (%s)" % (rc, err)
    assert not os.path.exists(path), "single-use token must be consumed on ALLOW"
    print("PASS test_allow_valid_token")


def test_deny_wrong_session():
    d = fresh_sessions_dir()
    mint(d, session_id=SESSION_B)
    rc, out, err = run(SESSION_A, sessions_dir=d)
    assert rc == 1, "a token minted for a different session must deny, got %s (%s)" % (rc, err)
    print("PASS test_deny_wrong_session")


def test_deny_expired_token():
    d = fresh_sessions_dir()
    mint(d, age_seconds=400)  # TTL is 300s
    rc, out, err = run(SESSION_A, sessions_dir=d)
    assert rc == 1, "an expired token must deny, got %s (%s)" % (rc, err)
    print("PASS test_deny_expired_token")


def test_deny_wrong_scope():
    d = fresh_sessions_dir()
    mint(d, raw="scope: website-write\nsession: %s\nreason: x\n" % SESSION_A)
    rc, out, err = run(SESSION_A, sessions_dir=d)
    assert rc == 1, "a token with the wrong scope must deny, got %s (%s)" % (rc, err)
    print("PASS test_deny_wrong_scope")


def test_single_use_consumption():
    d = fresh_sessions_dir()
    mint(d)
    rc1, _, err1 = run(SESSION_A, sessions_dir=d)
    assert rc1 == 0, "first check must allow, got %s (%s)" % (rc1, err1)
    rc2, _, err2 = run(SESSION_A, sessions_dir=d)
    assert rc2 == 1, "second check on a consumed token must deny, got %s (%s)" % (rc2, err2)
    print("PASS test_single_use_consumption")


def test_usage_error_missing_session_arg():
    rc, out, err = run(None, extra_args=[])
    assert rc == 3, "missing --session must be a usage error (exit 3), got %s (%s)" % (rc, err)
    print("PASS test_usage_error_missing_session_arg")


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
    print("ALL CHECK-WEBSITE-DEPLOY TESTS PASS (%d)" % len(tests))
