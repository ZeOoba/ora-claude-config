#!/usr/bin/env python3
"""Tests for health-guard-beacon.py -- the LOCAL durable beacon.

WHY THIS EXISTS. ora-health-guard's freshness beacon lived only on a Notion page. That
made the detector depend on the connector whose outage is one of the main things that
degrades a run, so a healthy run and a dead one looked identical.

Observed live 2026-08-04: the run woke 51min late, executed end to end, and sent all
three emails -- but all four notion-fetch calls returned net::ERR_FAILED, so per spec
B.3.5 it correctly skipped the Notion beacon write. The next run (2026-08-05) saw a
42h Notion gap and reported a FAIL that never happened, and the off-machine watchdog
opened ZeOoba/ora-cowork-watchdog#10 on the same non-event.

The local beacon is written unconditionally, so "did this task run?" is answerable
without the network. Notion stays as the cross-fleet surface.

Run: python _tests/test_health_guard_beacon.py   (exit 0 = pass)
"""
import importlib.util
import json
import os
import sys
import tempfile

MAINT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location(
    "hgb", os.path.join(MAINT, "health-guard-beacon.py"))
hgb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hgb)

results = []


def expect(label, cond, detail=""):
    results.append((bool(cond), label))
    if not cond:
        print("  FAIL: %s %s" % (label, detail))


def fresh_store():
    return os.path.join(tempfile.mkdtemp(prefix="hgb_"), "health-guard-beacon.json")


# --- write is unconditional and durable --------------------------------------------

p = fresh_store()
hgb.write_beacon(p, status="DEGRADED", subject_sent="[ACTION] Health Guard - x",
                 failed_connectors="notion", notion_written=False,
                 notion_error="net::ERR_FAILED", now_iso="2026-08-04T06:24:05-04:00")
expect("write creates the store even when Notion failed", os.path.isfile(p))
data = json.load(open(p, encoding="utf-8"))
expect("store holds one entry", len(data["entries"]) == 1, "got %r" % data)
e = data["entries"][-1]
expect("notion_written recorded False", e["notion_written"] is False, "got %r" % e)
expect("notion_error preserved", e["notion_error"] == "net::ERR_FAILED", "got %r" % e)

# a missing parent directory must not lose the beacon -- that would reintroduce the
# exact blind spot this file exists to close.
deep = os.path.join(tempfile.mkdtemp(prefix="hgb_"), "nested", "dir", "beacon.json")
hgb.write_beacon(deep, status="OK", subject_sent="s", failed_connectors="none",
                 notion_written=True, now_iso="2026-08-05T05:35:00-04:00")
expect("write creates missing parent directories", os.path.isfile(deep))

# --- read: gap is computed from the LOCAL entry, not from Notion --------------------

p = fresh_store()
hgb.write_beacon(p, status="OK", subject_sent="s", failed_connectors="none",
                 notion_written=False, notion_error="net::ERR_FAILED",
                 now_iso="2026-08-04T06:24:05-04:00")
r = hgb.read_beacon(p, now_iso="2026-08-05T05:35:00-04:00")
expect("gap_hours computed from the local entry (~23.2h)",
       23.0 < r["gap_hours"] < 23.3, "got %r" % r["gap_hours"])
expect("gap under 26h -> verdict OK even though Notion was never written",
       r["verdict"] == "OK", "got %r" % r)
expect("Notion-side staleness surfaced separately, not as the verdict",
       r["notion_gap_explained"] is True, "got %r" % r)

# The real 08-04 -> 08-05 case: 42h of Notion silence, but the task DID run in between.
# Must NOT read as a missed cycle.
p = fresh_store()
hgb.write_beacon(p, status="DEGRADED", subject_sent="s", failed_connectors="notion",
                 notion_written=False, now_iso="2026-08-04T06:24:05-04:00")
r = hgb.read_beacon(p, now_iso="2026-08-05T05:35:00-04:00")
expect("08-04 outage case does not report a missed cycle", r["verdict"] == "OK",
       "got %r" % r)

# --- a genuinely missed cycle still fails -------------------------------------------
# The fix must not blind the detector; that would be worse than the false positive.

p = fresh_store()
hgb.write_beacon(p, status="OK", subject_sent="s", failed_connectors="none",
                 notion_written=True, now_iso="2026-08-01T05:20:00-04:00")
r = hgb.read_beacon(p, now_iso="2026-08-05T05:35:00-04:00")
expect("a real 4-day silence still reports STALE", r["verdict"] == "STALE",
       "got %r" % r)
expect("real silence is not excused as a Notion outage",
       r["notion_gap_explained"] is False, "got %r" % r)

# --- absent store is UNKNOWN, never a silent pass -----------------------------------
# feedback_verified_null_vs_inferred_null: a zero that could mean "couldn't look" is a
# failure, not a pass.

r = hgb.read_beacon(os.path.join(tempfile.mkdtemp(prefix="hgb_"), "nope.json"),
                    now_iso="2026-08-05T05:35:00-04:00")
expect("missing store -> UNKNOWN verdict", r["verdict"] == "UNKNOWN", "got %r" % r)
expect("missing store -> gap_hours is None, not 0", r["gap_hours"] is None, "got %r" % r)

# a corrupt store must also be UNKNOWN rather than crashing the daily health guard
p = fresh_store()
os.makedirs(os.path.dirname(p), exist_ok=True)
open(p, "w", encoding="utf-8").write("{not json")
r = hgb.read_beacon(p, now_iso="2026-08-05T05:35:00-04:00")
expect("corrupt store -> UNKNOWN, no exception", r["verdict"] == "UNKNOWN", "got %r" % r)

# --- ledger retention ---------------------------------------------------------------

p = fresh_store()
for d in range(1, 40):
    hgb.write_beacon(p, status="OK", subject_sent="s", failed_connectors="none",
                     notion_written=True,
                     now_iso="2026-07-%02dT05:20:00-04:00" % ((d % 28) + 1))
data = json.load(open(p, encoding="utf-8"))
expect("ledger is capped (retains history without growing without bound)",
       len(data["entries"]) <= hgb.MAX_ENTRIES, "got %d" % len(data["entries"]))
expect("newest entry is retained after capping",
       data["entries"][-1]["last_run_et"].startswith("2026-07-"),
       "got %r" % data["entries"][-1])

passed = sum(1 for ok, _ in results if ok)
print("health-guard-beacon tests: %d/%d passed" % (passed, len(results)))
sys.exit(0 if passed == len(results) else 1)
