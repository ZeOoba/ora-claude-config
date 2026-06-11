#!/usr/bin/env python3
"""Tests for git-prepush-confidential-scan.py (pure functions only, synthetic terms).

The scanner is the 2026-06-11 incident lesson made executable: a pre-push gate must
scan the FULL HISTORY being pushed (git log -p over each pushed range), not the tree.
Run: python test-git-prepush-scan.py   (exit 0 = all pass)
"""
import importlib.util
import os
import sys

HOOKS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location(
    "pps", os.path.join(HOOKS, "git-prepush-confidential-scan.py"))
pps = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pps)

results = []


def expect(label, cond, detail=""):
    results.append((bool(cond), label))
    if not cond:
        print("  FAIL: %s %s" % (label, detail))


ZERO = "0" * 40
SHA_A = "a" * 40
SHA_B = "b" * 40
TERMS = ["zephyr corp", "9999 example ave"]  # synthetic — never real deal terms here

# --- parse_pushrefs ---------------------------------------------------------------
refs = pps.parse_pushrefs(
    "refs/heads/main %s refs/heads/main %s\nnot a ref line\n" % (SHA_A, SHA_B))
expect("parse: one valid line", len(refs) == 1 and refs[0][1] == SHA_A and refs[0][3] == SHA_B)
expect("parse: empty input", pps.parse_pushrefs("") == [])

# --- rev_range --------------------------------------------------------------------
expect("range: new remote ref -> full local history", pps.rev_range(SHA_A, ZERO) == SHA_A)
expect("range: existing remote -> delta range", pps.rev_range(SHA_A, SHA_B) == "%s..%s" % (SHA_B, SHA_A))

# --- scan_text --------------------------------------------------------------------
expect("scan: clean text", pps.scan_text("quarterly portfolio summary", TERMS) == [])
expect("scan: hit, case-insensitive", pps.scan_text("re: ZePHyR CoRp teaser", TERMS) == [0])
expect("scan: multiple hits, indices not strings",
       pps.scan_text("zephyr corp at 9999 example ave", TERMS) == [0, 1])
expect("scan: term never echoed", all(
    t not in repr(pps.scan_text("zephyr corp", TERMS)) for t in TERMS))

# --- load_terms shape -------------------------------------------------------------
expect("load_terms: returns list or None (fail-closed contract)",
       pps.load_terms() is None or isinstance(pps.load_terms(), list))

passed = sum(1 for ok, _ in results if ok)
print("\ngit-prepush-scan tests: %d/%d passed" % (passed, len(results)))
sys.exit(0 if passed == len(results) else 1)
