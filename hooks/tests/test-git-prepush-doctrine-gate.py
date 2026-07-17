#!/usr/bin/env python3
"""Tests for git-prepush-doctrine-gate.py — the doctrine-drift pre-push gate that runs
AHEAD of the confidentiality scan.

Fully isolated: the sessions root (ORA_OVERRIDE_SESSIONS_DIR) and the event_log target
are redirected to temp dirs, so the test never touches the real hooks/sessions/ or the
canonical event_log.md. The probe is stubbed (we assert the gate's decision/override/
logging wiring, not the probe's own drift detection).
Run: python test-git-prepush-doctrine-gate.py  (exit 0 = pass)

TOKEN HARDENING (2026-07-16) — this suite locks the session-scoped, content-bound token
contract that replaced the flat mtime-only sentinel. It mirrors, deliberately, the
adversarial cases in test-ora-autonomy-gate.py: both gates share one contract via
hooks/lib/override_tokens.py, so both must refuse the same malformed tokens.
"""
import importlib.util
import os
import sys
import tempfile
import time

HOOKS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location(
    "dg", os.path.join(HOOKS, "git-prepush-doctrine-gate.py"))
dg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dg)

SESSION = "test-session-0001"
results = []


def expect(label, cond, detail=""):
    results.append((bool(cond), label))
    if not cond:
        print("  FAIL: %s %s" % (label, detail))


def mint(root, session_id, content, name=None):
    """Write a token into <root>/<session_id>/overrides/<name> and return its path."""
    name = name or dg.DOCTRINE_DRIFT.name
    d = os.path.join(root, session_id, "overrides")
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, name)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)
    return path


def good_token(session_id=SESSION):
    return ("scope: doctrine-drift\n"
            "session: %s\n"
            "reason: Gabriel approved pushing despite a known stale pointer\n"
            % session_id)


# --- decide() pure decision table (pre-existing; must stay UNCHANGED) --------------
expect("decide: clean (rc 0) -> allow, no log", dg.decide(0, False) == (0, False))
expect("decide: clean (rc 0) + override present -> allow, no log", dg.decide(0, True) == (0, False))
expect("decide: drift (rc 1), no override -> BLOCK", dg.decide(1, False) == (1, False))
expect("decide: drift (rc 1) + override -> allow + LOG", dg.decide(1, True) == (0, True))
expect("decide: any non-zero rc treated as drift", dg.decide(2, False) == (1, False))

# --- build_override_entry() -------------------------------------------------------
entry = dg.build_override_entry(session_id=SESSION)
expect("entry: starts with dated '## ' header (append-event-log contract)", entry.startswith("## "))
expect("entry: references the override + drift", "override" in entry.lower() and "drift" in entry.lower())

# --- the retired flat sentinel path must be GONE ----------------------------------
expect("retired flat sentinel constant is gone", not hasattr(dg, "OVERRIDE_DIR"),
       "gate still exposes OVERRIDE_DIR -- the flat hooks/overrides/ path must not be consulted")

# --- override_active(): the hardened, session-scoped, content-bound contract -------
with tempfile.TemporaryDirectory() as td:
    os.environ["ORA_OVERRIDE_SESSIONS_DIR"] = td
    tok = os.path.join(td, SESSION, "overrides", dg.DOCTRINE_DRIFT.name)

    # 1. Nothing minted -> no override.
    expect("no token -> False", dg.override_active(SESSION) is False)

    # 2. A well-formed, fresh, correctly-scoped, session-matched token -> override.
    mint(td, SESSION, good_token())
    expect("valid session-scoped token -> True", dg.override_active(SESSION) is True)

    # 3. Content is load-bearing: an empty / `touch`-minted token is inert.
    mint(td, SESSION, "")
    expect("empty token (touch-minted) -> False", dg.override_active(SESSION) is False)

    # 4. Content-blindness regression: prose that never declares the scope grants nothing.
    mint(td, SESSION, "banana. Not a drift override. DO NOT PUSH ANYTHING.\n")
    expect("prose without scope: -> False", dg.override_active(SESSION) is False)

    # 5. Wrong scope -> inert (a website token must not authorize a doctrine-drift push).
    mint(td, SESSION, "scope: website-deploy\nsession: %s\n" % SESSION)
    expect("wrong scope -> False", dg.override_active(SESSION) is False)

    # 6. Session mismatch INSIDE the token -> inert (defeats copying between sessions).
    mint(td, SESSION, "scope: doctrine-drift\nsession: some-other-session\n")
    expect("session mismatch inside token -> False", dg.override_active(SESSION) is False)

    # 7. Another session's token dir must not grant to me.
    os.remove(tok)
    mint(td, "a-different-session", good_token("a-different-session"))
    expect("another session's token -> False", dg.override_active(SESSION) is False)

    # 8. Duplicate keys are ambiguous -> must never resolve in the grant's favor.
    mint(td, SESSION, "scope: doctrine-drift\nscope: doctrine-drift\nsession: %s\n" % SESSION)
    expect("duplicate keys -> False", dg.override_active(SESSION) is False)

    # 9. Oversized token -> refused (cheap junk/DoS guard).
    mint(td, SESSION, good_token() + ("x" * 9000))
    expect("oversized token -> False", dg.override_active(SESSION) is False)

    # 10. Aged past the TTL -> refused.
    p = mint(td, SESSION, good_token())
    old = time.time() - (dg.DOCTRINE_DRIFT.ttl + 120)
    os.utime(p, (old, old))
    expect("aged token (> TTL) -> False", dg.override_active(SESSION) is False)

    # 11. Future-dated -> refused (a naive `age < ttl` would honor it ~forever).
    p = mint(td, SESSION, good_token())
    future = time.time() + 86400
    os.utime(p, (future, future))
    expect("future-dated token -> False", dg.override_active(SESSION) is False)

    # 12. No session id at all (a human's bare-terminal push) -> override impossible.
    mint(td, SESSION, good_token())
    expect("session_id None -> False (fail closed)", dg.override_active(None) is False)
    expect("session_id empty -> False (fail closed)", dg.override_active("") is False)

    # 13. Path-traversal session ids must not address a token outside the sessions root.
    for evil in ("..", "../overrides", "a/../../overrides", r"..\..\overrides", "a/b"):
        expect("traversal session_id %r -> False" % evil, dg.override_active(evil) is False)

    # --- main() wiring: drift + valid token -> allow + LOG, via the seams -----------
    mint(td, SESSION, good_token())
    tmp_log = os.path.join(td, "event_log_test.md")
    with open(tmp_log, "w", encoding="utf-8") as f:
        f.write("# test log\n\n## 2000-01-01 — seed\n\n- seed entry\n")
    dg.EVENT_LOG_OVERRIDE = tmp_log
    dg.run_doctrine_probe = lambda: 1  # stub: force drift (legacy bare-int contract)
    os.environ["CLAUDE_CODE_SESSION_ID"] = SESSION

    rc = dg.main()
    expect("main: drift + valid token -> exit 0 (push allowed)", rc == 0, "got %r" % rc)
    logged = open(tmp_log, encoding="utf-8").read()
    expect("main: override use appended to event_log (newest-first)",
           "Pre-push proceeded DESPITE doctrine drift" in logged)
    expect("main: new entry inserted ABOVE the seed (newest-first)",
           logged.index("Pre-push proceeded") < logged.index("2000-01-01"))
    expect("main: the override record names the session (real audit trail)",
           SESSION in logged, "session id absent from the logged entry")
    # Content-binding only pays for itself if the content reaches the audit trail: the
    # token's `reason:` must be recorded, not merely parsed and dropped (review, 2026-07-16).
    expect("main: the override record carries the token's reason",
           "known stale pointer" in logged, "reason text absent from the logged entry")

    # A CLEAN push must not even look for a token -- token_grants() consumes at validation
    # time, so a speculative lookup would burn a single-use token on a push that never
    # needed one. Multi-use today makes this latent, so assert the short-circuit directly.
    probed = []
    real_override_token = dg.override_token
    dg.override_token = lambda sid: (probed.append(sid), real_override_token(sid))[1]
    dg.run_doctrine_probe = lambda: 0  # clean
    rc_clean = dg.main()
    dg.override_token = real_override_token
    dg.run_doctrine_probe = lambda: 1  # restore drift for the cases below
    expect("main: clean probe -> exit 0", rc_clean == 0, "got %r" % rc_clean)
    expect("main: clean probe never looks for a token (no speculative consume)",
           probed == [], "override_token consulted on a clean run: %r" % probed)
    expect("main: token survives a clean push", os.path.isfile(tok))

    # main() BLOCKS (exit 1) with drift + no token, writing nothing new to the log.
    os.remove(tok)
    before = open(tmp_log, encoding="utf-8").read()
    rc2 = dg.main()
    after = open(tmp_log, encoding="utf-8").read()
    expect("main: drift + no token -> exit 1 (BLOCK)", rc2 == 1, "got %r" % rc2)
    expect("main: block path writes nothing to the log", before == after)

    # main() BLOCKS when the env carries no session id, even with a token on disk --
    # a push from a bare terminal cannot be overridden.
    mint(td, SESSION, good_token())
    os.environ.pop("CLAUDE_CODE_SESSION_ID", None)
    rc3 = dg.main()
    expect("main: drift + no session id in env -> exit 1 (BLOCK)", rc3 == 1, "got %r" % rc3)

    os.environ.pop("ORA_OVERRIDE_SESSIONS_DIR", None)

passed = sum(1 for ok, _ in results if ok)
print("\ngit-prepush-doctrine-gate tests: %d/%d passed" % (passed, len(results)))
sys.exit(0 if passed == len(results) else 1)
