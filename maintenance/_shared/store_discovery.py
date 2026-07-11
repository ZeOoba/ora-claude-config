#!/usr/bin/env python3
"""Shared scheduler-store discovery for the ORA maintenance probes.

SINGLE implementation of the dual-store discovery that cc-verifier-probe,
registry-membership-probe, fleet-status, and setup-self-audit each used to
reimplement (2026-07-09 consolidation). Store roots and the ratified fleet
floors live in scheduler-stores.json NEXT TO THIS FILE — a store-path move or
a floor recalibration is a one-file edit there, nowhere else.

Fail-open: if the config is missing or unreadable, the DEFAULTS below (the
2026-07-09 live layout / ratified floors) apply — a broken config must never
blind a probe.

fleet-deadman.ps1 deliberately does NOT read this module or the config — it
is the independent external backstop and stays self-contained by design.
"""
import glob
import json
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(_HERE, "scheduler-stores.json")

_DEFAULT_ROOTS = [r"%APPDATA%\Claude",
                  r"%LOCALAPPDATA%\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Roaming\Claude"]
_DEFAULT_FLOORS = {"cc": 13, "lams": 4}


def _load_config():
    try:
        return json.load(open(CONFIG_PATH, encoding="utf-8"))
    except Exception:
        return {}


def _expand(path):
    # %VAR% expansion with fallbacks for the two vars the roots actually use,
    # so discovery still works in a stripped environment (scheduled context).
    home = os.path.expanduser("~")
    path = path.replace("%APPDATA%", os.environ.get("APPDATA")
                        or os.path.join(home, "AppData", "Roaming"))
    path = path.replace("%LOCALAPPDATA%", os.environ.get("LOCALAPPDATA")
                        or os.path.join(home, "AppData", "Local"))
    return os.path.expandvars(path)


def store_bases(store, config=None):
    """Base directories to scan for a store ('claude-code-sessions' /
    'local-agent-mode-sessions'), configured roots first, defaults on fail."""
    cfg = _load_config() if config is None else config
    roots = cfg.get("storeRoots") or _DEFAULT_ROOTS
    return [os.path.join(_expand(r), store) for r in roots]


def discover_store(store, config=None):
    """Path of the live scheduled-tasks.json for a store, or None.

    Biggest-then-newest across all configured roots (I4: GUIDs rotate, never
    hardcode; the MSIX LocalCache path mirrors Roaming — one registry per
    store). Empty and unparseable registries are skipped."""
    best = None
    for base in store_bases(store, config):
        for p in glob.glob(os.path.join(base, "**", "scheduled-tasks.json"),
                           recursive=True):
            try:
                d = json.load(open(p, encoding="utf-8"))
            except Exception:
                continue
            n = len(d.get("scheduledTasks", []) or [])
            if n and (best is None or (n, os.path.getmtime(p)) > best[0]):
                best = ((n, os.path.getmtime(p)), p)
    return best[1] if best else None


def fleet_floor(label, default, config=None):
    """Ratified fleet floor for 'cc'/'lams' from the config; built-in default
    for the label if unset/malformed; caller default for unknown labels."""
    cfg = _load_config() if config is None else config
    v = (cfg.get("fleetFloors") or {}).get(label)
    if isinstance(v, int) and not isinstance(v, bool):
        return v
    return _DEFAULT_FLOORS.get(label, default)
