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

    # --- BOM regression (adversarial review, 2026-07-17): PowerShell's default Out-File/
    # Set-Content/`>` redirection on Windows writes a UTF-8 BOM. Plain "utf-8" decoding
    # leaves the BOM attached to the first line, corrupting "scope" into a different dict
    # key -- a genuinely Gabriel-approved token minted via ordinary Windows tooling would
    # silently fail closed with no diagnostic. utf-8-sig fixes this.
    BOM_TIER = ot.Tier("t-bom", "bom-scope", 3600)
    bom_path = os.path.join(td, SESSION, "overrides", BOM_TIER.name)
    os.makedirs(os.path.dirname(bom_path), exist_ok=True)
    with open(bom_path, "w", encoding="utf-8-sig") as fh:
        fh.write("scope: bom-scope\nsession: %s\nreason: minted via PowerShell Out-File\n" % SESSION)
    expect("a BOM-prefixed token still grants",
           ot.token_grants(SESSION, BOM_TIER) is not None,
           "utf-8 (not utf-8-sig) would corrupt the leading 'scope' key and silently deny")

    # --- CONCURRENT DOUBLE-SPEND (merge-gate review of PR #480, 2026-11-21) -------------
    # One session firing N identical gated calls in parallel spent ONE single-use token
    # TWICE (8 parallel hook runs -> [0, 0, 2, 2, 2, 2, 2, 2]). Cause: check-then-consume,
    # with os.remove() as the "consume". On Windows os.remove is NOT an exclusive claim:
    # overlapping DeleteFile calls on one file BOTH return success (measured: 8 processes
    # racing os.remove on one file -> >1 success in 40/40 trials; os.rename likewise 40/40;
    # O_CREAT|O_EXCL 0/40). So "the delete succeeded" proves nothing about who won.
    #
    # Deterministic reproduction: a barrier inside parse_token holds every caller at the
    # point where all have passed the pre-checks, and consume_token is replaced with the
    # Windows overlap semantics measured above (an overlapping delete of a file that existed
    # when the race began reports success). Correct code admits exactly ONE caller into the
    # validate+consume section, so only one ever reaches the barrier; the barrier then times
    # out for it alone (BrokenBarrierError is swallowed) and it proceeds.
    import threading

    RACERS = 8
    RACE = ot.Tier("t-race", "race-scope", 3600, single_use=True, requires_extra_check=True)
    race_path = mint(td, RACE, "scope: race-scope\nsession: %s\n" % SESSION)

    barrier = threading.Barrier(RACERS, timeout=2.0)
    real_parse, real_consume = ot.parse_token, ot.consume_token

    def parse_at_barrier(path):
        fields = real_parse(path)
        try:
            barrier.wait()
        except threading.BrokenBarrierError:
            pass
        return fields

    def windows_overlapping_delete(path):
        try:
            os.remove(path)
        except FileNotFoundError:
            pass  # an overlapping DeleteFile on Windows reports success here
        return True

    ot.parse_token, ot.consume_token = parse_at_barrier, windows_overlapping_delete
    grants = []
    try:
        threads = [threading.Thread(target=lambda: grants.append(
            ot.token_grants(SESSION, RACE, extra_check=lambda f: True)))
            for _ in range(RACERS)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(30)
    finally:
        ot.parse_token, ot.consume_token = real_parse, real_consume
    n_granted = sum(1 for g in grants if g is not None)
    expect("%d parallel consumers of ONE single-use token -> exactly ONE grant" % RACERS,
           n_granted == 1, "granted %d times -- single-use double-spend" % n_granted)
    expect("the raced token is burned", not os.path.isfile(race_path))

    # A claim left behind by a caller that died mid-consume must fail CLOSED for that exact
    # token instance -- and must NOT block a token Gabriel re-mints afterwards.
    race_path = mint(td, RACE, "scope: race-scope\nsession: %s\n" % SESSION)
    st = os.stat(race_path)
    claims = os.path.join(td, SESSION, ot.CLAIM_SUBDIR)
    os.makedirs(claims, exist_ok=True)
    stale = os.path.join(claims, "%s.%s.lock" % (RACE.name, ot._token_identity(st)))
    open(stale, "w").close()
    expect("token whose claim is held elsewhere -> refused (fail closed)",
           ot.token_grants(SESSION, RACE, extra_check=lambda f: True) is None)
    expect("...and is NOT burned by the refused caller", os.path.isfile(race_path))
    os.remove(race_path)
    import time as _time
    _time.sleep(0.05)
    race_path = mint(td, RACE, "scope: race-scope\nsession: %s\nreason: re-minted\n" % SESSION)
    expect("a re-minted token is not blocked by a dead caller's leftover claim",
           ot.token_grants(SESSION, RACE, extra_check=lambda f: True) is not None)

    # A failed binding releases the claim, so the SAME token still grants for the right action.
    race_path = mint(td, RACE, "scope: race-scope\nsession: %s\n" % SESSION)
    expect("single-use + failing extra_check under the claim -> refused",
           ot.token_grants(SESSION, RACE, extra_check=lambda f: False) is None)
    expect("...then the same token grants for a matching action (claim was released)",
           ot.token_grants(SESSION, RACE, extra_check=lambda f: True) is not None)
    expect("no claim files are left behind after normal grants/refusals",
           [n for n in os.listdir(claims) if n != os.path.basename(stale)] == [],
           "left: %r" % os.listdir(claims))

    # A peek (consume=False) and a multi-use tier never take the claim.
    p = mint(td, RACE, "scope: race-scope\nsession: %s\n" % SESSION)
    expect("peek of a single-use token grants without burning",
           ot.token_grants(SESSION, RACE, extra_check=lambda f: True, consume=False) is not None
           and os.path.isfile(p))

    # --- Real multi-process race (non-deterministic complement to the barrier test) -------
    # Uses the real os.remove; on Windows this double-spent before the fix.
    import subprocess
    racer = (
        "import importlib.util,os,sys,time\n"
        "spec=importlib.util.spec_from_file_location('ot',sys.argv[1]);ot=importlib.util.module_from_spec(spec);spec.loader.exec_module(ot)\n"
        "t0=float(sys.argv[2])\n"
        "while time.time()<t0: pass\n"
        "T=ot.Tier('t-proc','proc-scope',3600,single_use=True,requires_extra_check=True)\n"
        "print('GRANT' if ot.token_grants(sys.argv[3],T,extra_check=lambda f: True) is not None else 'DENY')\n"
    )
    lib_path = os.path.join(HOOKS, "lib", "override_tokens.py")
    PROC = ot.Tier("t-proc", "proc-scope", 3600, single_use=True)
    worst = 0
    for _trial in range(6):
        mint(td, PROC, "scope: proc-scope\nsession: %s\n" % SESSION)
        t0 = _time.time() + 0.8
        procs = [subprocess.Popen([sys.executable, "-c", racer, lib_path, str(t0), SESSION],
                                  stdout=subprocess.PIPE, text=True, env=os.environ.copy())
                 for _ in range(RACERS)]
        outs = [pr.communicate(timeout=60)[0].strip() for pr in procs]
        worst = max(worst, outs.count("GRANT"))
        if outs.count("GRANT") != 1:
            break
    expect("real %d-process race on one single-use token never grants more than once"
           % RACERS, worst == 1, "max grants in a trial: %d" % worst)

    # --- STUCK-CLAIM HINT (PR #481 follow-up) -------------------------------------------
    # A caller killed while holding a claim leaves the claim file behind; that token instance
    # is then refused forever, and the operator sees a valid-looking token keep failing.
    # stuck_claim_note() names the cause in the block message. It must only fire for a claim
    # on the CURRENT token instance that is older than a live spend could be, and never raise.
    STUCK = ot.Tier("t-stuck", "stuck-scope", 3600, single_use=True)
    stuck_tok = mint(td, STUCK, "scope: stuck-scope\nsession: %s\n" % SESSION)
    expect("no claim -> no stuck-claim note", ot.stuck_claim_note(SESSION, STUCK) == "")
    stuck_claim = os.path.join(td, SESSION, ot.CLAIM_SUBDIR, "%s.%s.lock" % (
        STUCK.name, ot._token_identity(os.stat(stuck_tok))))
    os.makedirs(os.path.dirname(stuck_claim), exist_ok=True)
    open(stuck_claim, "w").close()
    expect("a FRESH claim (a live spend in progress) -> no note",
           ot.stuck_claim_note(SESSION, STUCK) == "")
    old = _time.time() - 60
    os.utime(stuck_claim, (old, old))
    note = ot.stuck_claim_note(SESSION, STUCK)
    expect("an aged claim on the current token instance -> note names it",
           "STUCK CLAIM" in note and "rewrite" in note.lower(), "note=%r" % note)
    expect("describe_token carries the stuck-claim note",
           "STUCK CLAIM" in ot.describe_token(SESSION, STUCK))
    expect("the stuck token is refused (fail closed) while the note is shown",
           ot.token_grants(SESSION, STUCK) is None and os.path.isfile(stuck_tok))
    _time.sleep(0.05)
    stuck_tok = mint(td, STUCK, "scope: stuck-scope\nsession: %s\nreason: rewritten\n" % SESSION)
    expect("after a rewrite the old claim no longer matches -> no note",
           ot.stuck_claim_note(SESSION, STUCK) == "")
    expect("...and the rewritten token grants", ot.token_grants(SESSION, STUCK) is not None)
    expect("multi-use tier -> never a note", ot.stuck_claim_note(SESSION, PLAIN) == "")
    expect("bad session id -> no note, no exception",
           ot.stuck_claim_note("../evil", STUCK) == "" and ot.stuck_claim_note(None, STUCK) == "")

    os.environ.pop("ORA_OVERRIDE_SESSIONS_DIR", None)

passed = sum(1 for ok, _ in results if ok)
print("\noverride_tokens contract tests: %d/%d passed" % (passed, len(results)))
sys.exit(0 if passed == len(results) else 1)
