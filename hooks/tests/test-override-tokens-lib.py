#!/usr/bin/env python3
"""Contract tests for hooks/lib/override_tokens.py itself.

Run: python test-override-tokens-lib.py   (exit 0 = pass)
Stdlib only. Fully isolated via the ORA_OVERRIDE_SESSIONS_DIR seam -- never touches a real
session's tokens.

WHY A THIRD SUITE: this module is now the SHARED token contract behind two security gates
(ora-autonomy-gate.py, git-prepush-doctrine-gate.py). Each gate's suite exercises the module
through its own gate, which leaves two things untested:

  1. The extra_check protocol, added 2026-07-17 when the autonomy gate adopted this module.
     Its fail-closed guard (a tier declaring requires_extra_check must REFUSE to grant when a
     caller supplies no extra_check) is UNREACHABLE through either gate, because both gates
     always pass one. It only protects a FUTURE caller who forgets -- so only a direct test
     can prove it works rather than merely reading like it does.
  2. Ordering: extra_check must run BEFORE consumption, so a token failing it is refused
     WITHOUT being burned. Through a gate this is invisible; here it is observable.
"""
import importlib.util
import os
import sys
import tempfile

HOOKS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location(
    "override_tokens", os.path.join(HOOKS, "lib", "override_tokens.py"))
ot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ot)

SESSION = "lib-test-session"
results = []


def expect(label, cond, detail=""):
    results.append((bool(cond), label))
    if not cond:
        print("  FAIL: %s %s" % (label, detail))


def mint(root, tier, content, session_id=SESSION):
    d = os.path.join(root, session_id, "overrides")
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, tier.name)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)
    return path


with tempfile.TemporaryDirectory() as td:
    os.environ["ORA_OVERRIDE_SESSIONS_DIR"] = td

    PLAIN = ot.Tier("t-plain", "plain-scope", 3600)
    BOUND = ot.Tier("t-bound", "bound-scope", 3600, requires_extra_check=True)
    ONESHOT = ot.Tier("t-oneshot", "oneshot-scope", 3600, single_use=True,
                      requires_extra_check=True)

    # --- token_grants returns FIELDS, not a bool (so `reason:` can reach an audit trail) --
    mint(td, PLAIN, "scope: plain-scope\nsession: %s\nreason: because Gabriel said so\n" % SESSION)
    got = ot.token_grants(SESSION, PLAIN)
    expect("grant returns the parsed fields", isinstance(got, dict), "got %r" % (got,))
    expect("grant carries the reason through", (got or {}).get("reason") == "because Gabriel said so")
    expect("no token -> None (not False)", ot.token_grants("nobody-session", PLAIN) is None)

    # --- THE NEW GUARD: a requires_extra_check tier REFUSES when no extra_check is given ---
    # Unreachable through either gate; this is the only place it is proven.
    p = mint(td, BOUND, "scope: bound-scope\nsession: %s\n" % SESSION)
    expect("requires_extra_check tier + NO extra_check -> refused (fail closed)",
           ot.token_grants(SESSION, BOUND) is None,
           "a forgotten extra_check silently granted -- the binding would be skipped")
    expect("the refused token was NOT burned", os.path.isfile(p))
    expect("requires_extra_check tier + passing extra_check -> granted",
           ot.token_grants(SESSION, BOUND, extra_check=lambda f: True) is not None)
    expect("requires_extra_check tier + failing extra_check -> refused",
           ot.token_grants(SESSION, BOUND, extra_check=lambda f: False) is None)

    # --- extra_check receives the parsed fields --------------------------------------
    seen = {}
    ot.token_grants(SESSION, BOUND, extra_check=lambda f: seen.update(f) or True)
    expect("extra_check is handed the parsed fields", seen.get("scope") == "bound-scope")

    # --- ORDERING: extra_check runs BEFORE consumption --------------------------------
    # A single-use token that fails the caller's binding must be refused WITHOUT being
    # burned: it may be a legitimate token tested against the wrong action, and burning it
    # would force a re-mint of an approval Gabriel already gave.
    p = mint(td, ONESHOT, "scope: oneshot-scope\nsession: %s\n" % SESSION)
    expect("single-use + failing extra_check -> refused",
           ot.token_grants(SESSION, ONESHOT, extra_check=lambda f: False) is None)
    expect("single-use token survives a FAILED extra_check (not burned)", os.path.isfile(p),
           "the token was consumed despite failing its binding -- ordering regression")
    # ...and a passing one IS consumed.
    expect("single-use + passing extra_check -> granted",
           ot.token_grants(SESSION, ONESHOT, extra_check=lambda f: True) is not None)
    expect("single-use token IS burned after a successful grant", not os.path.isfile(p))
    expect("burned token cannot grant twice",
           ot.token_grants(SESSION, ONESHOT, extra_check=lambda f: True) is None)

    # --- a non-single-use token survives repeated grants ------------------------------
    p = mint(td, PLAIN, "scope: plain-scope\nsession: %s\n" % SESSION)
    ot.token_grants(SESSION, PLAIN)
    expect("multi-use token survives a grant", os.path.isfile(p))
    expect("multi-use token grants again", ot.token_grants(SESSION, PLAIN) is not None)

    os.environ.pop("ORA_OVERRIDE_SESSIONS_DIR", None)

passed = sum(1 for ok, _ in results if ok)
print("\noverride_tokens contract tests: %d/%d passed" % (passed, len(results)))
sys.exit(0 if passed == len(results) else 1)
