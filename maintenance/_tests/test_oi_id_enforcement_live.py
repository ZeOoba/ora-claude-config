#!/usr/bin/env python3
"""Gate hook-in: the CANONICAL tracker must pass OI-id enforcement.

This is the file that gives enforcement teeth. The unit tests in
test_oi_id_enforcement.py prove the logic; this one asserts it against the real
tracker, so a push carrying an unreserved id fails the pre-push hook-tests gate.

Mirrors how test_check_open_items_duplicate_ids.py asserts the canonical tracker
has zero collisions -- same pattern, same gate, one layer earlier in the causal
chain: that check catches a collision after it happens, this one refuses the
unallocated id that would have caused it.
"""
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ALLOC = os.path.join(os.path.dirname(HERE), "allocate-oi-id.py")

spec = importlib.util.spec_from_file_location("allocate_oi_id", ALLOC)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

results = []


def expect(label, cond, detail=""):
    results.append((bool(cond), label))
    print("  %s %s%s" % ("PASS" if cond else "FAIL:", label,
                         "" if cond else "  -- " + str(detail)))


baseline = m.read_baseline()
expect("baseline file is readable (else enforcement silently skips forever)",
       baseline is not None,
       "expected a number in %s" % m.DEFAULT_BASELINE)

mode = m.read_mode()
r = m.enforce(baseline=baseline)
text = m.format_enforcement(r)
print("  " + text.splitlines()[0])
print("  mode: %s" % mode)

# Only BLOCK mode fails the gate. In WARN the finding is surfaced loudly and the
# push proceeds -- see _state/oi-id-enforcement-mode.txt for why this shipped as
# WARN (a blocking rule for an unadopted workflow taxes every other session).
if mode == "BLOCK":
    expect("canonical tracker has no unreserved ids above the baseline",
           not r["violations"], text)
elif r["violations"]:
    print("  [WARN] %d unreserved id(s) -- reported, not blocking:" % len(r["violations"]))
    for v in r["violations"]:
        print("         %s  (regularise: allocate-oi-id.py --backfill %s --note \"...\")"
              % (v["id"], v["id"]))
else:
    expect("canonical tracker has no unreserved ids above the baseline (WARN mode)",
           True)

# A skipped run must be loud. Silent skipping is how a gate rots into decoration.
expect("enforcement actually ran (did not skip)", not r.get("skipped"), r)

passed = sum(1 for ok, _ in results if ok)
print("\noi-id enforcement (live) tests: %d/%d passed" % (passed, len(results)))
sys.exit(0 if passed == len(results) else 1)
