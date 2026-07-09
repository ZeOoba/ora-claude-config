#!/usr/bin/env python3
"""Tests for emit-fleet-heartbeat.py — the external dead-man's local heartbeat leg.

Covers the pure builder (build_heartbeat / count_enabled_recurring), the strict
payload rule (timestamp + counts + registry path/existence/sha256 + version marker,
and NOTHING else — no task ids, no cron strings), and the fail-open emit contract
(a write failure returns False, never raises — the probe's primary job must never
break on a heartbeat problem). Mirrors test-registry-membership-probe.py conventions.

Run: python test-emit-fleet-heartbeat.py   (exit 0 = all pass)
"""
import datetime
import hashlib
import importlib.util
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "efh", os.path.join(HERE, "emit-fleet-heartbeat.py"))
efh = importlib.util.module_from_spec(spec)
spec.loader.exec_module(efh)

results = []


def expect(label, cond, detail=""):
    results.append((bool(cond), label))
    if not cond:
        print("  FAIL: %s %s" % (label, detail))


NOW = datetime.datetime(2026, 7, 9, 23, 30, 0, tzinfo=datetime.timezone.utc)

# --- count_enabled_recurring ------------------------------------------------------------
REG = {"scheduledTasks": [
    {"id": "ora-alpha", "cronExpression": "30 6 * * *", "enabled": True},
    {"id": "ora-beta", "cronExpression": "0 18 * * *", "enabled": True},
    {"id": "ora-gamma", "cronExpression": None, "enabled": True},           # one-time -> excluded
    {"id": "ora-delta", "cronExpression": "0 3 * * *", "enabled": False},   # disabled -> excluded
    {"id": "ora-epsilon", "cronExpression": "not a cron", "enabled": True}, # malformed -> excluded
]}
expect("count: enabled 5-field cron only", efh.count_enabled_recurring(REG) == 2,
       repr(efh.count_enabled_recurring(REG)))
expect("count: empty registry -> 0", efh.count_enabled_recurring({}) == 0)
expect("count: None -> 0", efh.count_enabled_recurring(None) == 0)
expect("count: null task list -> 0", efh.count_enabled_recurring({"scheduledTasks": None}) == 0)

# --- build_heartbeat: real files --------------------------------------------------------
tmp = tempfile.mkdtemp()
cc_path = os.path.join(tmp, "cc-scheduled-tasks.json")
with open(cc_path, "w", encoding="utf-8") as f:
    json.dump(REG, f)
cc_bytes = open(cc_path, "rb").read()

lams_reg = {"scheduledTasks": [
    {"id": "ora-zeta", "cronExpression": "50 5,17 * * *", "enabled": True},
]}
lams_path = os.path.join(tmp, "lams-scheduled-tasks.json")
with open(lams_path, "w", encoding="utf-8") as f:
    json.dump(lams_reg, f)
lams_bytes = open(lams_path, "rb").read()

hb = efh.build_heartbeat({"cc": cc_path, "lams": lams_path}, now=NOW)
expect("build: ts is ISO-8601 UTC Z", hb["ts"] == "2026-07-09T23:30:00Z", repr(hb.get("ts")))
expect("build: version marker present",
       isinstance(hb.get("probe_version"), str) and hb["probe_version"], repr(hb))
expect("build: cc count", hb["fleets"]["cc"] == 2, repr(hb["fleets"]))
expect("build: lams count", hb["fleets"]["lams"] == 1, repr(hb["fleets"]))
expect("build: cc exists flag", hb["registries"]["cc"]["exists"] is True)
expect("build: cc sha256 = hash of file bytes",
       hb["registries"]["cc"]["sha256"] == hashlib.sha256(cc_bytes).hexdigest())
expect("build: lams sha256 = hash of file bytes",
       hb["registries"]["lams"]["sha256"] == hashlib.sha256(lams_bytes).hexdigest())
expect("build: path stored as given", hb["registries"]["cc"]["path"] == cc_path)

# STRICT PAYLOAD RULE: counts and hashes only — no task ids, no cron strings anywhere.
blob = json.dumps(hb)
expect("payload: no task ids leak",
       all(i not in blob for i in ("ora-alpha", "ora-beta", "ora-zeta")), blob)
expect("payload: no cron strings leak", "30 6 * * *" not in blob, blob)
expect("payload: top-level keys exactly ts/probe_version/fleets/registries",
       set(hb.keys()) == {"ts", "probe_version", "fleets", "registries"}, repr(set(hb.keys())))
expect("payload: registry keys exactly path/exists/sha256",
       set(hb["registries"]["cc"].keys()) == {"path", "exists", "sha256"},
       repr(set(hb["registries"]["cc"].keys())))

# --- build_heartbeat: missing / undiscovered / unparseable ------------------------------
hb2 = efh.build_heartbeat({"cc": os.path.join(tmp, "nope.json"), "lams": None}, now=NOW)
expect("missing file: exists false", hb2["registries"]["cc"]["exists"] is False)
expect("missing file: hash null", hb2["registries"]["cc"]["sha256"] is None)
expect("missing file: count null", hb2["fleets"]["cc"] is None)
expect("undiscovered store (None path): exists false + hash null + count null",
       hb2["registries"]["lams"] == {"path": None, "exists": False, "sha256": None}
       and hb2["fleets"]["lams"] is None, repr(hb2))

bad_path = os.path.join(tmp, "bad.json")
with open(bad_path, "w", encoding="utf-8") as f:
    f.write("{ not json !!!")
hb3 = efh.build_heartbeat({"cc": bad_path}, now=NOW)
expect("unparseable: exists true", hb3["registries"]["cc"]["exists"] is True)
expect("unparseable: bytes still hashed",
       hb3["registries"]["cc"]["sha256"]
       == hashlib.sha256(open(bad_path, "rb").read()).hexdigest())
expect("unparseable: count null (never guess)", hb3["fleets"]["cc"] is None)

# --- emit_heartbeat: fail-open contract -------------------------------------------------
out = os.path.join(tmp, "_state", "fleet-heartbeat.json")
ok = efh.emit_heartbeat(hb, out)
expect("emit: returns True on success", ok is True)
expect("emit: round-trips via UTF-8 JSON",
       json.load(open(out, encoding="utf-8")) == hb)

# a path UNDER an existing file cannot be created -> must return False, never raise
blocked = os.path.join(cc_path, "cant", "write", "here.json")
try:
    ok2 = efh.emit_heartbeat(hb, blocked)
    expect("emit: write failure returns False (fail-open)", ok2 is False)
except Exception as e:
    expect("emit: write failure returns False (fail-open)", False, repr(e))

# --- summary -----------------------------------------------------------------------------
passed = sum(1 for ok_, _ in results if ok_)
print("\nemit-fleet-heartbeat tests: %d/%d passed" % (passed, len(results)))
sys.exit(0 if passed == len(results) else 1)
