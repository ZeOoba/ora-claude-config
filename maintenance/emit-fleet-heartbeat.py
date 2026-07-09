#!/usr/bin/env python3
"""ORA fleet heartbeat emitter -- local leg of the EXTERNAL cross-fleet dead-man.

WHY: the 2026-07-05 Desktop reinstall destroyed the CC/MCP scheduled-task
registry, and the one guard built to catch that was itself a fleet member and
died with it (~14 CC functions dark ~3 weeks). The fix (Task 6, decision
DEADMAN_APPROACH=GITHUB-ACTION, Gabriel-ratified 2026-07-09) monitors the fleet
from OUTSIDE the machine: this script writes maintenance/_state/
fleet-heartbeat.json; push-fleet-heartbeat.ps1 (or any ~/.claude push) ships it
to PRIVATE ZeOoba/ora-claude-config; .github/workflows/fleet-deadman.yml checks
it daily on GitHub and opens an issue when the pulse stops or a fleet shrinks
below its ratified floor.

SIBLING, NOT AN EDIT: registry-membership-probe.py carried another session's
uncommitted work when this was built (single-writer doctrine forbids co-editing),
and the dead-man limb should stay decoupled anyway -- a probe regression must
never be able to kill the heartbeat (same self-containment rationale as
fleet-deadman.ps1). Counting mirrors the probe's definition exactly (enabled
tasks with a 5-field cron; one-time fireAt excluded) and store discovery
delegates to the same maintenance/_shared/store_discovery.py the probe uses,
with a built-in fallback when that helper is unavailable.

STRICT PAYLOAD RULE (the file is pushed off-machine): ISO-8601 UTC timestamp,
per-fleet ENABLED-recurring counts, per-registry path/existence/sha256, version
marker -- NOTHING else. No task ids, no cron strings, no deal terms, no
credentials. test-emit-fleet-heartbeat.py enforces this.

Fail-open: a heartbeat problem is reported on stdout/exit code but never raises
past main(); invoked as its own process it can never break a probe's primary job.
Run it right after registry-membership-probe.py wherever that probe runs
(daily-setup-audit-prompt.md STEP 1 block), and from push-fleet-heartbeat.ps1.

Exit 0 = heartbeat written. Exit 1 = emission failed (heartbeat may be stale --
the GitHub Action will alarm if this persists >24h; that is the design working).
"""
import datetime
import glob
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "_shared"))
try:
    import store_discovery as _sd
except Exception:
    _sd = None  # fail-open: fallback discovery below

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

VERSION = "emit-fleet-heartbeat v1.0 (2026-07-09)"
STATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_state")
HEARTBEAT = os.path.join(STATE_DIR, "fleet-heartbeat.json")

# Same (label, store) pairs registry-membership-probe.py walks.
FLEET_STORES = (("cc", "claude-code-sessions"),
                ("lams", "local-agent-mode-sessions"))

# Fallback discovery roots -- mirror store_discovery._DEFAULT_ROOTS (2026-07-09
# live layout) for when the shared helper is absent/broken.
_FALLBACK_ROOTS = (
    os.path.join(os.environ.get("APPDATA")
                 or os.path.join(os.path.expanduser("~"), "AppData", "Roaming"), "Claude"),
    os.path.join(os.environ.get("LOCALAPPDATA")
                 or os.path.join(os.path.expanduser("~"), "AppData", "Local"),
                 "Packages", "Claude_pzs8sxrjxfjjc", "LocalCache", "Roaming", "Claude"),
)


def count_enabled_recurring(registry):
    """Enabled tasks with a 5-field cron (the probe's enabled-recurring
    definition; one-time fireAt tasks excluded). 0 for empty/None. Pure."""
    n = 0
    for t in (registry or {}).get("scheduledTasks", []) or []:
        expr = t.get("cronExpression")
        if t.get("enabled") and isinstance(expr, str) and len(expr.split()) == 5:
            n += 1
    return n


def _fallback_discover(store):
    """Biggest-then-newest scheduled-tasks.json across the fallback roots --
    a self-contained mirror of store_discovery.discover_store()."""
    best = None
    for base in _FALLBACK_ROOTS:
        for p in glob.glob(os.path.join(base, store, "**", "scheduled-tasks.json"),
                           recursive=True):
            try:
                d = json.load(open(p, encoding="utf-8"))
            except Exception:
                continue
            n = len(d.get("scheduledTasks", []) or [])
            if n and (best is None or (n, os.path.getmtime(p)) > best[0]):
                best = ((n, os.path.getmtime(p)), p)
    return best[1] if best else None


def discover(store):
    """Live registry path for a store, or None. Shared helper first (identical
    to the probe's view), self-contained fallback second."""
    path = None
    if _sd is not None:
        try:
            path = _sd.discover_store(store)
        except Exception:
            path = None
    return path if path is not None else _fallback_discover(store)


def build_heartbeat(store_paths, now=None):
    """Heartbeat payload from {label: registry_path_or_None}. Pure I/O-read.

    Per label: fleets[label] = enabled-recurring count (None when the file is
    missing or unparseable -- never guess); registries[label] = {path, exists,
    sha256 of the raw file bytes (None when missing)}."""
    now = now or datetime.datetime.now(datetime.timezone.utc)
    fleets, registries = {}, {}
    for label, path in store_paths.items():
        exists, digest, count = False, None, None
        if path:
            try:
                with open(path, "rb") as f:
                    raw = f.read()
                exists = True
                digest = hashlib.sha256(raw).hexdigest()
                try:
                    count = count_enabled_recurring(json.loads(raw.decode("utf-8")))
                except Exception:
                    count = None  # unparseable registry: hash it, do not count it
            except OSError:
                exists, digest, count = False, None, None
        fleets[label] = count
        registries[label] = {"path": path, "exists": exists, "sha256": digest}
    return {"ts": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "probe_version": VERSION,
            "fleets": fleets,
            "registries": registries}


def emit_heartbeat(payload, out_path=HEARTBEAT):
    """Atomic UTF-8 JSON write (tmp + os.replace). True on success; False on
    ANY failure -- never raises (fail-open: the caller's primary job continues)."""
    try:
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        tmp = out_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=1)
            f.write("\n")
        os.replace(tmp, out_path)
        return True
    except Exception:
        return False


def main():
    try:
        paths = {label: discover(store) for label, store in FLEET_STORES}
        hb = build_heartbeat(paths)
        ok = emit_heartbeat(hb)
        counts = " ".join("%s=%s" % (k, v) for k, v in hb["fleets"].items())
        print("ORA FLEET HEARTBEAT %s  %s  -> %s"
              % ("written" if ok else "WRITE FAILED", counts, HEARTBEAT))
        return 0 if ok else 1
    except Exception as e:  # belt-and-suspenders fail-open
        print("ORA FLEET HEARTBEAT ERROR (fail-open): %r" % (e,))
        return 1


if __name__ == "__main__":
    sys.exit(main())
