#!/usr/bin/env python3
"""Tests for spec-liveness-probe.py -- spec-claim vs live-runtime-value drift.

Why this exists (OI-171, 2026-08-16): `ora-cc-snapshot-refresh`'s severity gate
emailed on "at least one flag of severity warn or higher". The single permanent
data-quality flag IS `warn`, so every clean run still sent [ALERT]. The gate was
written believing that flag was `info` -- it had been bumped info -> warn in
490d89f ~21 HOURS EARLIER. Two individually-correct changes; the interaction
defeated the gate, and no probe caught it because doctrine-integrity-probe.py
reads no live data and governor-drift-probe.py deliberately excludes snapshot
values (its :1224 comment).

The acceptance test that matters is REPLAY: this probe must FAIL against the
pre-fix spec text and PASS against the post-fix text.

Run: python test-spec-liveness-probe.py   (exit 0 = all pass)
"""
import importlib.util
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "spec_liveness_probe", os.path.join(HERE, "spec-liveness-probe.py"))
slp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(slp)

FAILURES = []


def check(label, cond, detail=""):
    if cond:
        print("  [OK] %s" % label)
    else:
        print("  [FAIL] %s %s" % (label, detail))
        FAILURES.append(label)


# The live flag as it actually is, verified 2026-08-16 against portfolio.json.
LIVE_WARN = [{
    "entity": "loans",
    "field": "name",
    "issue": ("Loan Index row 24 is tombstoned in the workbook and was skipped, "
              "so it cannot claim a snapshot id or warehouse key"),
    "rawValue": "⚠ DUPLICATE OF ROW 22 — DO NOT USE",
    "severity": "warn",
}]

# The exact sentence from SKILL.md as of 1706bc2 -- the defect, verbatim in shape.
PREFIX_SPEC = (
    "v1.1 2026-08-11: STEP 5 clause (b) now gates the alert email on SEVERITY.\n"
    "one flag is permanent and intentional -- the tombstoned Loan Index row 24\n"
    "duplicate marker, `loans · name`, severity info -- so an exit-0 run emailed.\n"
)

# Single line on purpose: the real SKILL.md keeps the severity word and the flag
# identity on ONE long unwrapped line (verified against the live file, line 59).
# An earlier version of this fixture split them across two lines, which was not
# how any real spec is written and which forced a >=1-line matching window --
# and that window then swallowed adjacent THRESHOLD RULES as flag claims. Caught
# by running the probe against the live checkout, not by these unit tests.
POSTFIX_SPEC = (
    "   - Known permanent **`warn`** flag, correct behavior, never an exception: "
    "`loans · name` -- \"Loan Index row 24 is tombstoned in the workbook\".\n"
)

# Regression fixture, from the live post-fix SKILL.md. A threshold RULE bullet
# sitting immediately above the allowlist bullet that mentions the flag by name.
# The rule legitimately says "info" and "warn" regardless of the live severity;
# reporting it is a permanent false positive on a file that is already CORRECT.
ADJACENT_RULE_SPEC = (
    "   - **`info`-only, or `warn`-flags-all-allowlisted => no email.** Record it.\n"
    "   - **RATIFIED-TOMBSTONE ALLOWLIST.** Requires issue containing "
    "\"Loan Index row 24 is tombstoned\".\n"
)

# A pure RULE, not a claim about a specific flag. Must never be reported.
RULE_ONLY_SPEC = (
    "   - **Email only if at least one entry is `severity: \"warn\"`** (or any\n"
    "future severity above `warn`). Quote that entry's fields verbatim.\n"
    "   - **`info`-only => no email.** Record the flag in the Notion note.\n"
)


print("test 1: REPLAY -- pre-fix spec asserting `info` against live `warn` is reported")
f = slp.check_severity_drift([("ora-cc-snapshot-refresh/SKILL.md", PREFIX_SPEC)],
                             LIVE_WARN)
check("reports exactly one drift", len(f) == 1, "got %r" % (f,))
check("names the source", any("ora-cc-snapshot-refresh" in x for x in f), "got %r" % (f,))
check("states spec-vs-live", any("info" in x and "warn" in x for x in f), "got %r" % (f,))

print("test 2: post-fix spec asserting `warn` against live `warn` is silent")
f = slp.check_severity_drift([("ora-cc-snapshot-refresh/SKILL.md", POSTFIX_SPEC)],
                             LIVE_WARN)
check("no findings", f == [], "got %r" % (f,))

print("test 3: rule-only text (threshold, not a flag claim) is NOT a false positive")
f = slp.check_severity_drift([("ora-cc-snapshot-refresh/SKILL.md", RULE_ONLY_SPEC)],
                             LIVE_WARN)
check("no findings", f == [], "got %r" % (f,))

print("test 4: reverse direction -- spec `warn`, live `info` -- is also reported")
live_info = [dict(LIVE_WARN[0], severity="info")]
f = slp.check_severity_drift([("x/SKILL.md", POSTFIX_SPEC)], live_info)
check("reports drift", len(f) == 1, "got %r" % (f,))

print("test 5: EVERY conflicting source reported, not just the first")
f = slp.check_severity_drift(
    [("a/SKILL.md", PREFIX_SPEC), ("b/SKILL.md", PREFIX_SPEC),
     ("c/SKILL.md", POSTFIX_SPEC)], LIVE_WARN)
check("two findings", len(f) == 2, "got %r" % (f,))
check("both sources named",
      any("a/SKILL.md" in x for x in f) and any("b/SKILL.md" in x for x in f),
      "got %r" % (f,))

print("test 6: allowlist rot -- spec pins a rawValue no longer present live")
f = slp.check_allowlist_rot([("ora-cc-snapshot-refresh/SKILL.md", POSTFIX_SPEC)], [])
check("reports rot", len(f) == 1, "got %r" % (f,))
f = slp.check_allowlist_rot([("ora-cc-snapshot-refresh/SKILL.md", POSTFIX_SPEC)],
                            LIVE_WARN)
check("silent when flag still live", f == [], "got %r" % (f,))

print("test 7: fail-open -- unreadable/missing snapshot yields None, never raises")
with tempfile.TemporaryDirectory() as d:
    missing = os.path.join(d, "nope.json")
    check("missing file -> None", slp.load_live_flags(missing) is None)
    bad = os.path.join(d, "bad.json")
    open(bad, "w", encoding="utf-8").write("{not json")
    check("malformed json -> None", slp.load_live_flags(bad) is None)
    noflags = os.path.join(d, "noflags.json")
    json.dump({"meta": {}}, open(noflags, "w", encoding="utf-8"))
    check("absent dataQuality key -> empty list, not None",
          slp.load_live_flags(noflags) == [])

print("test 8: load_live_flags parses the real shape")
with tempfile.TemporaryDirectory() as d:
    p = os.path.join(d, "portfolio.json")
    json.dump({"dataQuality": LIVE_WARN}, open(p, "w", encoding="utf-8"))
    got = slp.load_live_flags(p)
    check("one flag", got is not None and len(got) == 1, "got %r" % (got,))
    check("severity warn", got and got[0]["severity"] == "warn")

print("test 9: main() is report-only -- exit 0 even with drift present")
rc = slp.run([("ora-cc-snapshot-refresh/SKILL.md", PREFIX_SPEC)], LIVE_WARN)
check("exit code 0 despite findings", rc == 0, "got %r" % (rc,))
rc = slp.run([("x/SKILL.md", POSTFIX_SPEC)], None)
check("exit code 0 when snapshot unreadable", rc == 0, "got %r" % (rc,))


print("test 10: REGRESSION -- a threshold rule ADJACENT to a flag mention is not a claim")
f = slp.check_severity_drift([("ora-cc-snapshot-refresh/SKILL.md", ADJACENT_RULE_SPEC)],
                             LIVE_WARN)
check("no false positive on the already-correct post-fix file", f == [], "got %r" % (f,))

print("test 11: non-cp1252 characters in a finding surface do not crash the printer")
weird = ("   - Known permanent `info` flag `loans · name` \"Loan Index row 24 is "
         "tombstoned\" ⇒ ⚠ — ✓\n")
try:
    rc = slp.run([("weird/SKILL.md", weird)], LIVE_WARN)
    check("run() survives and returns 0", rc == 0, "got %r" % (rc,))
except UnicodeEncodeError as e:
    check("run() survives", False, "UnicodeEncodeError: %s" % e)

print("test 12: REVIEW FIX -- claim satisfied if ANY severity token on the line matches")
# Order-independence. A correct spec citing history ("was info, now warn") must not
# drift; the pre-fix spec, which names ONLY the stale value, still must.
correct_hist = "- `loans · name` was `info` historically but now reads `warn`.\n"
check("stale-value-first but correct => silent",
      slp.check_severity_drift([("a", correct_hist)], LIVE_WARN) == [], "regression")
only_stale = "- `loans · name` severity info -- permanent, never an exception.\n"
check("only the stale value => still reported",
      len(slp.check_severity_drift([("a", only_stale)], LIVE_WARN)) == 1)

print("test 13: REVIEW FIX -- rawValue drift trips allowlist rot")
# The SKILL.md allowlist keys on an EXACT rawValue. If the marker is reworded while
# entity/field/issue stay put, the allowlist silently stops covering the flag.
reworded = [dict(LIVE_WARN[0], rawValue="⚠ DUP OF ROW 22")]
f = slp.check_allowlist_rot([("ora-cc-snapshot-refresh/SKILL.md", POSTFIX_SPEC)],
                            reworded)
check("reworded rawValue => rot reported", len(f) == 1, "got %r" % (f,))
check("exact rawValue => silent",
      slp.check_allowlist_rot([("x/SKILL.md", POSTFIX_SPEC)], LIVE_WARN) == [])

print("test 14: REVIEW FIX -- both fleets are scanned, and coverage is reported")
check("SPEC_ROOTS covers CC and LAMS", len(slp.SPEC_ROOTS) == 2,
      "got %r" % (slp.SPEC_ROOTS,))
labels = {lbl for lbl, _ in slp.SPEC_ROOTS}
check("both fleets labelled", labels == {"CC", "LAMS"}, "got %r" % (labels,))

print()
if FAILURES:
    print("FAILED (%d): %s" % (len(FAILURES), ", ".join(FAILURES)))
    sys.exit(1)
print("ALL SPEC-LIVENESS-PROBE TESTS PASS")
sys.exit(0)
