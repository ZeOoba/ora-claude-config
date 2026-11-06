#!/usr/bin/env python3
"""Tests for memory-integrity-probe.py check 4a in append-only files (2026-11-05).

Gabriel's ruling (2026-11-05, the OI-288 case): event_log.md is append-only, so an
open-items link in it that has gone dead can never be corrected in place. That covers an
item that closed and moved to open-items-tracker-history.md after the entry was written,
and an id that resolves nowhere. Check 4a reports such a link as a WARNING in an
append-only file and keeps failing on it everywhere else. Before this change one such
link (cited since 2026-09-30, flagged by R33 on 2026-10-28) failed the probe on every
run, which also masks any new hard issue.

The pure-function cases cover oi_pointer_findings(). The end-to-end cases run the probe as a
subprocess over a temp ORA_MEMORY_DIR fixture and assert the exit code, which is what the
daily health guard actually reads. Nothing here touches the live memory tree.

Run: python test-memory-integrity-deadpointers.py   (exit 0 = all pass)
"""
import importlib.util
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PROBE = os.path.join(HERE, "memory-integrity-probe.py")
spec = importlib.util.spec_from_file_location("mip", PROBE)
mip = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mip)

results = []


def expect(label, cond, detail=""):
    results.append((bool(cond), label))
    if not cond:
        print("  FAIL: %s %s" % (label, detail))


WHERE = {"OI-288": "open-items-tracker-history.md", "OI-500": "open-items-tracker.md"}
STALE = "see [OI-288](open-items-tracker.md#OI-288)"   # wrong file: the item moved to history
MISSING = "see open-items-tracker.md#OI-999"             # resolves in neither file
GOOD = ("see [a](open-items-tracker.md#OI-500) and "
        "[b](open-items-tracker-history.md#OI-288)")
SUFFIX = " -- append-only file, left as written"


# The exact issue text the inline check 4a produced before this change (06ef73d8), so any
# rewording of the ordinary-file messages fails here rather than slipping through a substring.
def stale_msg(name):
    return ("%s references open-items-tracker.md#OI-288, but that id's anchor is actually in "
            "open-items-tracker-history.md (dead pointer -- wrong file named, likely stale from "
            "before the item closed/split)" % name)


def missing_msg(name):
    return ("%s references open-items-tracker.md#OI-999, which has no matching row in either "
            "open-items-tracker.md or open-items-tracker-history.md (dead pointer)" % name)


# Names that sit next to the exemption and must still FAIL: other logs, a dated or archived
# copy, and other casings of the one exempt name.
NEAR_MISSES = ("ops_decision_log.md", "event_log_2026-11.md", "archive_event_log.md",
               "Event_Log.md", "EVENT_LOG.md", "event_log.MD", "event_log.md.bak")

# --- scope is pinned: widening the exemption must be a deliberate, reviewed change ---
expect("APPEND_ONLY_FILES is exactly event_log.md",
       getattr(mip, "APPEND_ONLY_FILES", None) == frozenset({"event_log.md"}),
       repr(getattr(mip, "APPEND_ONLY_FILES", None)))

f = getattr(mip, "oi_pointer_findings", None)
expect("oi_pointer_findings exists", callable(f))
if callable(f):
    # Ordinary memory files: behaviour unchanged, still hard failures, text byte-identical.
    i, w = f("notes.md", STALE, WHERE)
    expect("ordinary file: wrong-file link -> exactly the old issue text",
           i == [stale_msg("notes.md")] and w == [], (i, w))
    i, w = f("notes.md", MISSING, WHERE)
    expect("ordinary file: missing-row link -> exactly the old issue text",
           i == [missing_msg("notes.md")] and w == [], (i, w))
    # Order is the old sorted (stem, id) order, whatever order the text cites them in.
    i, w = f("notes.md", MISSING + " then " + STALE, WHERE)
    expect("ordinary file: findings keep sorted (stem, id) order",
           i == [stale_msg("notes.md"), missing_msg("notes.md")] and w == [], (i, w))

    # The append-only log: the same links become warnings, same text plus the reason.
    i, w = f("event_log.md", STALE, WHERE)
    expect("event_log: wrong-file link -> one warning, exact text + reason",
           i == [] and w == [stale_msg("event_log.md") + SUFFIX], (i, w))
    i, w = f("event_log.md", MISSING, WHERE)
    expect("event_log: missing-row link -> one warning, exact text + reason",
           i == [] and w == [missing_msg("event_log.md") + SUFFIX], (i, w))

    # Near misses are NOT exempt: widening the rule (suffix, prefix, case-folding) fails here.
    for name in NEAR_MISSES:
        i, w = f(name, STALE, WHERE)
        expect("near miss %s: still an issue, not a warning" % name,
               i == [stale_msg(name)] and w == [], (i, w))

    # Links that resolve produce nothing, in either kind of file.
    for name in ("notes.md", "event_log.md"):
        i, w = f(name, GOOD, WHERE)
        expect("%s: resolving links produce nothing" % name, not i and not w, (i, w))

    # Repeated references collapse to one finding (the sorted-set behaviour is kept).
    i, w = f("notes.md", STALE + " again " + STALE, WHERE)
    expect("repeats collapse to one finding", len(i) == 1 and not w, (i, w))


# --- end to end: the exit code the daily health guard reads ---
def run_probe(files):
    with tempfile.TemporaryDirectory() as d:
        files = dict(files)
        files["MEMORY.md"] = "".join("- [%s](%s)\n" % (n, n) for n in sorted(files))
        for name, text in files.items():
            with open(os.path.join(d, name), "w", encoding="utf-8") as fh:
                fh.write(text)
        env = dict(os.environ, ORA_MEMORY_DIR=d)
        r = subprocess.run([sys.executable, PROBE], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", env=env, timeout=120)
        return r.returncode, r.stdout + r.stderr


BASE = {
    "open-items-tracker.md": "### OI-500\n**Status:** OPEN\n",
    "open-items-tracker-history.md": "### OI-288\n**Status:** CLOSED\n",
}
rc, out = run_probe(dict(BASE, **{"event_log.md": "## 2026-09-30 -- entry\n" + STALE + "\n"}))
expect("e2e: stale link only in event_log.md -> exit 0", rc == 0, "rc=%s\n%s" % (rc, out))
expect("e2e: the stale link is still reported, as a warning",
       "WARNINGS" in out and "append-only" in out, out)
rc, out = run_probe(dict(BASE, **{"notes.md": STALE + "\n"}))
expect("e2e: the same link in an ordinary file -> exit 1 with the exact issue line",
       rc == 1 and ("  - " + stale_msg("notes.md")) in out and "append-only" not in out,
       "rc=%s\n%s" % (rc, out))
# Near misses on disk, through main(): a widening done in main() rather than in the pure
# function (e.g. a name.startswith("event_log") routing) must fail here too.
E2E_NEAR = ("ops_decision_log.md", "event_log_2026-11.md", "archive_event_log.md")
rc, out = run_probe(dict(BASE, **dict({"event_log.md": "## 2026-09-30 -- entry\n" + STALE + "\n"},
                                      **{n: STALE + "\n" for n in E2E_NEAR})))
expect("e2e: near-miss logs beside event_log.md still fail the run",
       rc == 1 and all(("  - " + stale_msg(n)) in out for n in E2E_NEAR)
       and ("  ~ " + stale_msg("event_log.md") + SUFFIX) in out, "rc=%s\n%s" % (rc, out))
rc, out = run_probe(dict(BASE, **{"event_log.md": "## 2026-11-05 -- entry\n" + GOOD + "\n"}))
expect("e2e: clean fixture -> exit 0 with no warning about links",
       rc == 0 and "append-only" not in out, "rc=%s\n%s" % (rc, out))

failed = [label for ok, label in results if not ok]
print("%d/%d passed" % (len(results) - len(failed), len(results)))
sys.exit(1 if failed else 0)
