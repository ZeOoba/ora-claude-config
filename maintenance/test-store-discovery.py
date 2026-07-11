#!/usr/bin/env python3
"""Tests for _shared/store_discovery.py — the single scheduler-store discovery
implementation (2026-07-09; kills the 6-copy dual-store discovery drift).

Pure/temp-dir tests only — never touches the live registries or the real
scheduler-stores.json (a config dict is injected instead).

Run: python test-store-discovery.py   (exit 0 = all pass)
"""
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "sd", os.path.join(HERE, "_shared", "store_discovery.py"))
sd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sd)

results = []


def expect(label, cond, detail=""):
    results.append((bool(cond), label))
    if not cond:
        print("  FAIL: %s %s" % (label, detail))


def _mk_registry(base, *guids, n_tasks=1, mtime=None):
    d = os.path.join(base, *guids)
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, "scheduled-tasks.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump({"scheduledTasks": [{"id": f"t{i}", "enabled": True}
                                      for i in range(n_tasks)]}, f)
    if mtime is not None:
        os.utime(p, (mtime, mtime))
    return p


tmp = tempfile.mkdtemp(prefix="sd-test-")
try:
    # --- store_bases: config roots win; store name is appended ---
    cfg = {"storeRoots": [os.path.join(tmp, "rootA"), os.path.join(tmp, "rootB")]}
    bases = sd.store_bases("claude-code-sessions", config=cfg)
    expect("store_bases appends store to every configured root",
           bases == [os.path.join(tmp, "rootA", "claude-code-sessions"),
                     os.path.join(tmp, "rootB", "claude-code-sessions")], bases)

    # --- store_bases: empty/absent config falls back to built-in defaults ---
    fallback = sd.store_bases("claude-code-sessions", config={})
    expect("store_bases falls back to defaults on empty config",
           len(fallback) == 2 and all(b.endswith("claude-code-sessions") for b in fallback),
           fallback)
    expect("default roots cover Roaming + MSIX LocalCache",
           any("Roaming" in b for b in fallback) and
           any("Claude_pzs8sxrjxfjjc" in b for b in fallback), fallback)

    # --- discover_store: biggest wins over newest ---
    now = time.time()
    big = _mk_registry(os.path.join(tmp, "rootA"), "claude-code-sessions",
                       "guid1", "guid2", n_tasks=5, mtime=now - 1000)
    _mk_registry(os.path.join(tmp, "rootB"), "claude-code-sessions",
                 "guid3", "guid4", n_tasks=2, mtime=now)
    got = sd.discover_store("claude-code-sessions", config=cfg)
    expect("discover_store prefers biggest registry", got == big, got)

    # --- discover_store: newest wins on size tie ---
    newer = _mk_registry(os.path.join(tmp, "rootB"), "claude-code-sessions",
                         "guid5", "guid6", n_tasks=5, mtime=now)
    got = sd.discover_store("claude-code-sessions", config=cfg)
    expect("discover_store tie-breaks by newest mtime", got == newer, got)

    # --- discover_store: empty registries are skipped; none found -> None ---
    _mk_registry(os.path.join(tmp, "rootA"), "local-agent-mode-sessions",
                 "g", "g2", n_tasks=0)
    expect("discover_store ignores empty registries -> None",
           sd.discover_store("local-agent-mode-sessions", config=cfg) is None)

    # --- discover_store: malformed JSON is skipped, not fatal ---
    badd = os.path.join(tmp, "rootA", "claude-code-sessions", "bad", "g")
    os.makedirs(badd, exist_ok=True)
    with open(os.path.join(badd, "scheduled-tasks.json"), "w", encoding="utf-8") as f:
        f.write("{not json")
    expect("malformed registry skipped without raising",
           sd.discover_store("claude-code-sessions", config=cfg) == newer)

    # --- fleet_floor: config value wins; falls back to default on absence ---
    expect("fleet_floor reads config", sd.fleet_floor("cc", 99, config={"fleetFloors": {"cc": 7}}) == 7)
    expect("fleet_floor falls back to built-in default for known label",
           sd.fleet_floor("cc", 99, config={}) == 13)
    expect("fleet_floor falls back to caller default for unknown label",
           sd.fleet_floor("nope", 42, config={}) == 42)
    expect("fleet_floor ignores non-int config values",
           sd.fleet_floor("lams", 99, config={"fleetFloors": {"lams": "four"}}) == 4)

    # --- the REAL config file must be present, parseable, and complete ---
    real = os.path.join(HERE, "_shared", "scheduler-stores.json")
    expect("scheduler-stores.json exists next to the helper", os.path.isfile(real))
    if os.path.isfile(real):
        rc = json.load(open(real, encoding="utf-8"))
        expect("real config has storeRoots", bool(rc.get("storeRoots")))
        expect("real config has both fleet floors",
               isinstance((rc.get("fleetFloors") or {}).get("cc"), int) and
               isinstance((rc.get("fleetFloors") or {}).get("lams"), int))
finally:
    shutil.rmtree(tmp, ignore_errors=True)

npass = sum(1 for ok, _ in results if ok)
print(f"store-discovery tests: {npass}/{len(results)} pass")
sys.exit(0 if npass == len(results) else 1)
