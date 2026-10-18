#!/usr/bin/env python3
"""config-capability-baseline.py -- REPORT-ONLY probe (W0-00b + W0-01).

1. Binary baseline: which Claude Code binaries load ~/.claude/settings.json, the lowest
   one, and which capabilities that lowest binary can use (MIN_VERSION map below;
   VERIFIED/UNVERIFIED mirrors capability-research.md 2026-10-17).
2. Connector-identity drift: every mcp__<server>__ id referenced in settings.json,
   agents/*.md and hooks/*.py, diffed against a live-server snapshot (--live-servers FILE,
   one server id per line, written by a session from its own tool list).

Writes nothing. Never reads hooks/confidential-terms.json or _confidential-staging/.
Exit 0 always, except --strict with a dead reference -> 3.

  python config-capability-baseline.py [--root DIR] [--live-servers FILE] [--version-override V1,V2] [--json] [--strict]
"""
import argparse
import glob
import json
import os
import re
import subprocess
import sys

MIN_VERSION = {
    "onFailure:block": ((2, 1, 295), "VERIFIED"),
    "mcp allow-rule exact-server match (mcp__<server>__*)": ((2, 1, 299), "VERIFIED"),
    "agent frontmatter model overrides CLAUDE_CODE_SUBAGENT_MODEL": ((2, 1, 251), "VERIFIED"),
    "hook `if` filter": ((2, 1, 278), "UNVERIFIED"),
    "cache TTL keys (promptCacheTtl/subagentPromptCacheTtl)": ((2, 1, 242), "UNVERIFIED"),
}
_VER = re.compile(r"(\d+)\.(\d+)\.(\d+)")
_REF = re.compile(r"mcp__([A-Za-z0-9][A-Za-z0-9_\-]*?)__")
SKIP_NAMES = {"confidential-terms.json", "_confidential-staging"}


def parse_version(s):
    m = _VER.search(s or "")
    return tuple(int(x) for x in m.groups()) if m else None


def lowest_binary(versions):
    parsed = [(parse_version(v), v) for v in versions if parse_version(v)]
    return min(parsed)[1] if parsed else None


def extract_refs(text):
    return set(_REF.findall(text or ""))


def _read(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return ""


def collect_refs(root):
    refs = {"settings": set(), "agents": set(), "hooks": set()}
    refs["settings"] = extract_refs(_read(os.path.join(root, "settings.json")))
    for p in glob.glob(os.path.join(root, "agents", "*.md")):
        for line in _read(p).splitlines():
            if line.lower().startswith(("tools:", "disallowedtools:")):
                refs["agents"] |= extract_refs(line)
    for p in glob.glob(os.path.join(root, "hooks", "*.py")):
        if os.path.basename(p) in SKIP_NAMES:
            continue
        refs["hooks"] |= extract_refs(_read(p))
    return refs


def dead_refs(refs, live):
    out = []
    for where, ids in refs.items():
        for r in sorted(ids):
            if r not in live:
                out.append({"ref": r, "where": where})
    return out


def discover_binaries(version_override):
    if version_override:
        return [v.strip() for v in version_override.split(",") if v.strip()]
    found = []
    try:
        p = subprocess.run(["claude", "--version"], capture_output=True, text=True, timeout=15)
        if parse_version(p.stdout):
            found.append(p.stdout.strip())
    except (OSError, subprocess.TimeoutExpired):
        pass
    appdata = os.environ.get("APPDATA") or os.path.join(os.path.expanduser("~"), "AppData", "Roaming")
    for d in glob.glob(os.path.join(appdata, "Claude", "claude-code", "*")):
        if parse_version(os.path.basename(d)):
            found.append(os.path.basename(d))
    return found


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=os.path.expanduser("~/.claude"))
    ap.add_argument("--live-servers")
    ap.add_argument("--version-override")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict", action="store_true")
    a = ap.parse_args(argv)

    versions = discover_binaries(a.version_override)
    low = lowest_binary(versions)
    low_t = parse_version(low) if low else None
    caps = [{"name": n, "min_version": ".".join(map(str, mv)), "confidence": conf,
             "usable_on_lowest": bool(low_t and low_t >= mv)} for n, (mv, conf) in MIN_VERSION.items()]

    refs = collect_refs(a.root)
    live = None
    if a.live_servers:
        live = {l.strip() for l in _read(a.live_servers).splitlines() if l.strip()}
    dead = dead_refs(refs, live) if live is not None else []
    report = {"binaries": versions, "lowest_binary": low, "capabilities": caps,
              "connector_refs": {k: sorted(v) for k, v in refs.items()},
              "live_snapshot_provided": live is not None, "dead_refs": dead}

    if a.json:
        print(json.dumps(report, indent=2))
    else:
        print("lowest binary loading settings.json: %s  (all: %s)" % (low, ", ".join(versions) or "none found"))
        for c in caps:
            print("  %-62s >=%s  %-10s usable-on-lowest=%s" % (c["name"], c["min_version"], c["confidence"], c["usable_on_lowest"]))
        for where, ids in report["connector_refs"].items():
            print("refs in %-8s: %s" % (where, ", ".join(ids) or "-"))
        print("DEAD references: %s" % (", ".join("%s (%s)" % (d["ref"], d["where"]) for d in dead) or
                                       ("none" if live is not None else "n/a (no --live-servers snapshot)")))
    return 3 if (a.strict and dead) else 0


if __name__ == "__main__":
    sys.exit(main())
