#!/usr/bin/env python3
"""Tests for git-prepush-doctrine-gate.py — the doctrine-drift pre-push gate that runs
AHEAD of the confidentiality scan.

Fully isolated: OVERRIDE_DIR and the event_log target are redirected to temp dirs, so
the test never touches the real ~/.claude/hooks/overrides/ or the canonical event_log.md.
The probe is stubbed (we assert the gate's decision/override/logging wiring, not the
probe's own drift detection). Run: python test-git-prepush-doctrine-gate.py  (exit 0 = pass)
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

results = []


def expect(label, cond, detail=""):
    results.append((bool(cond), label))
    if not cond:
        print("  FAIL: %s %s" % (label, detail))


# --- decide() pure decision table -------------------------------------------------
expect("decide: clean (rc 0) -> allow, no log", dg.decide(0, False) == (0, False))
expect("decide: clean (rc 0) + override present -> allow, no log", dg.decide(0, True) == (0, False))
expect("decide: drift (rc 1), no override -> BLOCK", dg.decide(1, False) == (1, False))
expect("decide: drift (rc 1) + override -> allow + LOG", dg.decide(1, True) == (0, True))
expect("decide: any non-zero rc treated as drift", dg.decide(2, False) == (1, False))

# --- build_override_entry() -------------------------------------------------------
entry = dg.build_override_entry()
expect("entry: starts with dated '## ' header (append-event-log contract)", entry.startswith("## "))
expect("entry: references the override + drift", "override" in entry.lower() and "drift" in entry.lower())

# --- override_active(): fresh vs. aged vs. missing, in an ISOLATED temp dir --------
with tempfile.TemporaryDirectory() as td:
    dg.OVERRIDE_DIR = td
    sentinel = os.path.join(td, dg.OVERRIDE_NAME)

    expect("override_active: missing sentinel -> False", dg.override_active() is False)

    with open(sentinel, "w") as f:
        f.write("scratch")
    expect("override_active: fresh sentinel (<60min) -> True", dg.override_active() is True)

    # Age the mtime past the 60-min TTL via os.utime.
    old = time.time() - (dg.OVERRIDE_TTL_SECONDS + 120)
    os.utime(sentinel, (old, old))
    expect("override_active: aged sentinel (>60min) -> False", dg.override_active() is False)

    # Refresh to <60min and prove main() SUPPRESSES the block + LOGS, with a stubbed
    # drifting probe and a temp event_log (never the canonical one).
    os.utime(sentinel, None)  # bump mtime back to now
    tmp_log = os.path.join(td, "event_log_test.md")
    with open(tmp_log, "w", encoding="utf-8") as f:
        f.write("# test log\n\n## 2000-01-01 — seed\n\n- seed entry\n")
    dg.EVENT_LOG_OVERRIDE = tmp_log
    dg.run_doctrine_probe = lambda: 1  # stub: force drift

    rc = dg.main()
    expect("main: drift + fresh override -> exit 0 (push allowed)", rc == 0, "got %r" % rc)
    logged = open(tmp_log, encoding="utf-8").read()
    expect("main: override use appended to event_log (newest-first)",
           "Pre-push proceeded DESPITE doctrine drift" in logged)
    expect("main: new entry inserted ABOVE the seed (newest-first)",
           logged.index("Pre-push proceeded") < logged.index("2000-01-01"))

    # And main() BLOCKS (exit 1) with drift + no override, writing nothing new to the log.
    os.remove(sentinel)
    before = open(tmp_log, encoding="utf-8").read()
    rc2 = dg.main()
    after = open(tmp_log, encoding="utf-8").read()
    expect("main: drift + no override -> exit 1 (BLOCK)", rc2 == 1, "got %r" % rc2)
    expect("main: block path writes nothing to the log", before == after)

passed = sum(1 for ok, _ in results if ok)
print("\ngit-prepush-doctrine-gate tests: %d/%d passed" % (passed, len(results)))
sys.exit(0 if passed == len(results) else 1)
