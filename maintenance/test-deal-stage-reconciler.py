#!/usr/bin/env python3
"""Tests for deal-stage-reconciler.py (TDD).

Pure-function unit tests, mirroring test-registry-membership-probe.py's pattern.
No Notion/network access anywhere in this file or the module under test -- the module
only ever receives already-fetched JSON (see the 2026-07-09 cross-fleet
deal-stage-reconciliation design spec).

Run: python test-deal-stage-reconciler.py   (exit 0 = all pass)
"""
import importlib.util
import json
import os
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
MOD_PATH = os.path.join(HERE, "deal-stage-reconciler.py")

spec = importlib.util.spec_from_file_location("dsr", MOD_PATH)
dsr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dsr)

results = []


def expect(label, cond, detail=""):
    results.append((bool(cond), label))
    if not cond:
        print("  FAIL: %s %s" % (label, detail))


tmpdir = tempfile.mkdtemp(prefix="dsr-test-")

# --- load_snapshot / save_snapshot --------------------------------------------------
missing_path = os.path.join(tmpdir, "does-not-exist.json")
expect("load_snapshot: missing file -> {}", dsr.load_snapshot(missing_path) == {})

corrupt_path = os.path.join(tmpdir, "corrupt.json")
with open(corrupt_path, "w", encoding="utf-8") as f:
    f.write("{not valid json")
expect("load_snapshot: corrupt file -> {}", dsr.load_snapshot(corrupt_path) == {})

not_dict_path = os.path.join(tmpdir, "not-dict.json")
with open(not_dict_path, "w", encoding="utf-8") as f:
    json.dump([1, 2, 3], f)
expect("load_snapshot: non-dict JSON -> {}", dsr.load_snapshot(not_dict_path) == {})

roundtrip_path = os.path.join(tmpdir, "snap.json")
sample = {"pg1": {"deal": "511 Industrial Mile Rd", "stage": "Candidate"}}
dsr.save_snapshot(roundtrip_path, sample)
expect("save_snapshot: round-trips via load_snapshot",
       dsr.load_snapshot(roundtrip_path) == sample)
expect("save_snapshot: no leftover tmp-write file",
       not os.path.exists(roundtrip_path + ".tmp-write"))

# --- diff_stages ----------------------------------------------------------------------
current = {
    "pg1": {"deal": "511 Industrial Mile Rd", "stage": "Under Review"},
    "pg2": {"deal": "470 McCormick Blvd", "stage": "Passed"},
    "pg3": {"deal": "754 Old State Route 74", "stage": "In Negotiation"},
}
snapshot = {
    "pg1": {"deal": "511 Industrial Mile Rd", "stage": "Candidate"},
    "pg3": {"deal": "754 Old State Route 74", "stage": "In Negotiation"},
    "pg4": {"deal": "Old Removed Deal", "stage": "Passed"},
}
transitions = dsr.diff_stages(current, snapshot)
by_id = {t["page_id"]: t for t in transitions}
expect("diff_stages: unchanged stage produces no transition", "pg3" not in by_id)
expect("diff_stages: changed stage produces a transition", "pg1" in by_id)
expect("diff_stages: changed transition has correct old/new",
       by_id.get("pg1", {}).get("old_stage") == "Candidate"
       and by_id["pg1"]["new_stage"] == "Under Review")
expect("diff_stages: brand-new page_id has old_stage None",
       by_id.get("pg2", {}).get("old_stage") is None)
expect("diff_stages: page removed from current is not reported", "pg4" not in by_id)
expect("diff_stages: exactly 2 transitions", len(transitions) == 2, transitions)

# --- summary ----------------------------------------------------------------------------
passed = sum(1 for ok, _ in results if ok)
print("\ndeal-stage-reconciler tests: %d/%d passed" % (passed, len(results)))
raise SystemExit(0 if passed == len(results) else 1)
