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
import subprocess
import sys
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

# --- classify_disposition -------------------------------------------------------------
stage_map = {"Passed": "PASS", "Killed": "TERMINATE", "Under Review": "NOT_A_TOKEN"}
expect("classify_disposition: mapped stage returns its token",
       dsr.classify_disposition("Passed", stage_map) == "PASS")
expect("classify_disposition: unmapped stage returns None",
       dsr.classify_disposition("Candidate", stage_map) is None)
expect("classify_disposition: mapped-but-invalid-token returns None (never guesses)",
       dsr.classify_disposition("Under Review", stage_map) is None)

# --- format_event_log_entry / format_ledger_row ----------------------------------------
t = {"page_id": "pg2", "deal": "470 McCormick Blvd", "old_stage": "In Negotiation",
     "new_stage": "Passed"}
entry = dsr.format_event_log_entry(t, "2026-07-08")
expect("format_event_log_entry: starts with dated header",
       entry.startswith("## 2026-07-08 — Deal-stage sync: 470 McCormick Blvd"),
       entry)
expect("format_event_log_entry: mentions both stages",
       "In Negotiation" in entry and "Passed" in entry)

t_new = {"page_id": "pg2", "deal": "470 McCormick Blvd", "old_stage": None,
         "new_stage": "Passed"}
entry_new = dsr.format_event_log_entry(t_new, "2026-07-08")
expect("format_event_log_entry: None old_stage renders as (none), not the word None",
       "(none)" in entry_new and "None" not in entry_new)

row = dsr.format_ledger_row(t, "PASS", "2026-07-08")
expect("format_ledger_row: correct column count", row.count("|") == 6, row)
expect("format_ledger_row: uses the standing fallback reason when none given",
       "reason not logged elsewhere" in row)

row_with_reason = dsr.format_ledger_row(t, "PASS", "2026-07-08",
                                         reason="LOI lapsed, Gabriel killed in-session")
expect("format_ledger_row: uses supplied reason when given",
       "LOI lapsed" in row_with_reason
       and "reason not logged elsewhere" not in row_with_reason)

# --- CLI (E2E via subprocess, mirroring test-governor-drift-probe.py's pattern) --------
def run_cli(args):
    return subprocess.run([sys.executable, MOD_PATH] + args,
                           capture_output=True, text=True, encoding="utf-8")

cli_current_path = os.path.join(tmpdir, "cli-current.json")
with open(cli_current_path, "w", encoding="utf-8") as f:
    json.dump(current, f)
cli_map_path = os.path.join(tmpdir, "cli-map.json")
with open(cli_map_path, "w", encoding="utf-8") as f:
    json.dump({"Passed": "PASS"}, f)
cli_snapshot_path = os.path.join(tmpdir, "cli-snapshot.json")
dsr.save_snapshot(cli_snapshot_path, snapshot)

proc = run_cli(["--current-file", cli_current_path, "--stage-map-file", cli_map_path,
                "--snapshot-file", cli_snapshot_path, "--date", "2026-07-10"])
expect("CLI: exit 0 on normal run", proc.returncode == 0, proc.stderr)
payload = json.loads(proc.stdout) if proc.returncode == 0 else {}
expect("CLI: reports 2 transitions", payload.get("count") == 2, payload)
expect("CLI: 470 transition carries a PASS disposition + non-null ledger_row",
       any(x["deal"] == "470 McCormick Blvd" and x["disposition"] == "PASS"
           and x["ledger_row"] for x in payload.get("transitions", [])),
       payload)
expect("CLI: 511 transition has no disposition (not in stage_map) and null ledger_row",
       any(x["deal"] == "511 Industrial Mile Rd" and x["disposition"] is None
           and x["ledger_row"] is None for x in payload.get("transitions", [])),
       payload)
expect("CLI: ledger_row preserves UTF-8 em-dash end-to-end",
       any(x["ledger_row"] and "—" in x["ledger_row"]
           for x in payload.get("transitions", [])),
       payload)
expect("CLI: snapshot file updated to current state",
       dsr.load_snapshot(cli_snapshot_path) == current)

bootstrap_snapshot_path = os.path.join(tmpdir, "bootstrap-snapshot.json")
proc2 = run_cli(["--current-file", cli_current_path, "--stage-map-file", cli_map_path,
                 "--snapshot-file", bootstrap_snapshot_path, "--bootstrap"])
expect("CLI --bootstrap: exit 0", proc2.returncode == 0, proc2.stderr)
bootstrap_payload = json.loads(proc2.stdout) if proc2.returncode == 0 else {}
expect("CLI --bootstrap: reports bootstrap true, no transitions key",
       bootstrap_payload.get("bootstrap") is True
       and "transitions" not in bootstrap_payload)
expect("CLI --bootstrap: snapshot seeded to current state",
       dsr.load_snapshot(bootstrap_snapshot_path) == current)

proc3 = run_cli(["--current-file", os.path.join(tmpdir, "nope.json"),
                 "--stage-map-file", cli_map_path])
expect("CLI: missing --current-file exits 2 (fail loud)", proc3.returncode == 2)
expect("CLI: missing --current-file names the failing input on stderr",
       "cannot read --current-file" in proc3.stderr, proc3.stderr)

proc4 = run_cli(["--current-file", cli_current_path,
                 "--stage-map-file", os.path.join(tmpdir, "nope-map.json"),
                 "--snapshot-file", os.path.join(tmpdir, "exit2-snap-a.json")])
expect("CLI: missing --stage-map-file exits 2 (fail loud)", proc4.returncode == 2,
       proc4.stderr)

nondict_current_path = os.path.join(tmpdir, "cli-nondict-current.json")
with open(nondict_current_path, "w", encoding="utf-8") as f:
    json.dump([1, 2], f)
proc5 = run_cli(["--current-file", nondict_current_path,
                 "--stage-map-file", cli_map_path,
                 "--snapshot-file", os.path.join(tmpdir, "exit2-snap-b.json")])
expect("CLI: non-dict JSON in --current-file exits 2", proc5.returncode == 2,
       proc5.stderr)

nondict_map_path = os.path.join(tmpdir, "cli-nondict-map.json")
with open(nondict_map_path, "w", encoding="utf-8") as f:
    json.dump([1, 2], f)
proc6 = run_cli(["--current-file", cli_current_path,
                 "--stage-map-file", nondict_map_path,
                 "--snapshot-file", os.path.join(tmpdir, "exit2-snap-c.json")])
expect("CLI: non-dict JSON in --stage-map-file exits 2", proc6.returncode == 2,
       proc6.stderr)

# --- summary ----------------------------------------------------------------------------
passed = sum(1 for ok, _ in results if ok)
print("\ndeal-stage-reconciler tests: %d/%d passed" % (passed, len(results)))
raise SystemExit(0 if passed == len(results) else 1)
