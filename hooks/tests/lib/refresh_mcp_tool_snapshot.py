#!/usr/bin/env python3
"""Regenerate hooks/tests/lib/mcp_tool_snapshot.json (R-06 MCP delete gate).

The snapshot is the evidence test-mcp-delete-tiers.py checks the tier table against:
every delete-shaped tool name in it must have an explicit tier row, and a row's
`verified` flag must equal "this suffix is in the snapshot".

SOURCES
  connector_tools : union of the `enabledMcpTools` keys ("<server>:<tool>") across the
                    Claude Desktop session records (local_*.json) modified in the last
                    --days days, in the CC store that maintenance/_shared/
                    store_discovery.py finds (or --store-dir).
  internal_tools  : app-internal and session-attached tool names, which are NOT in
                    enabledMcpTools. One full mcp__ name per line in --internal-file,
                    pasted from a live session's tool list. '#' lines are comments.

USAGE
  python hooks/tests/lib/refresh_mcp_tool_snapshot.py --internal-file <txt>
         [--store-dir DIR] [--days 30] [--out PATH]

Writes ASCII JSON, sorted lists, captured_at = today's local date. Read-only toward the
store. Exit 0 written, 2 no source found.

Stdlib only. ASCII-only. Windows (`python`).
"""
import argparse
import datetime
import glob
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
HOOKS_DIR = os.path.dirname(os.path.dirname(HERE))
SHARED = os.path.join(os.path.dirname(HOOKS_DIR), "maintenance", "_shared")
DEFAULT_OUT = os.path.join(HERE, "mcp_tool_snapshot.json")


def cc_store_dir():
    sys.path.insert(0, SHARED)
    try:
        import store_discovery  # noqa: E402
        reg = store_discovery.discover_store("claude-code-sessions")
    except Exception:
        return None
    return os.path.dirname(reg) if reg else None


def connector_tools(store_dir, days):
    cutoff = time.time() - days * 86400
    names, records = set(), 0
    for path in glob.glob(os.path.join(store_dir, "local_*.json")):
        try:
            if os.path.getmtime(path) < cutoff:
                continue
            with open(path, "r", encoding="utf-8") as fh:
                rec = json.load(fh)
        except Exception:
            continue
        tools = rec.get("enabledMcpTools") if isinstance(rec, dict) else None
        if isinstance(tools, dict):
            records += 1
            names.update(k for k in tools if isinstance(k, str) and ":" in k)
    return sorted(names), records


def internal_tools(path):
    with open(path, "r", encoding="ascii") as fh:
        names = [ln.strip() for ln in fh if ln.strip() and not ln.lstrip().startswith("#")]
    bad = [n for n in names if not n.startswith("mcp__") or n.count("__") < 2]
    if bad:
        raise SystemExit("ERROR: not full mcp__<server>__<tool> names: %r" % bad[:5])
    return sorted(set(names))


def main(argv=None):
    ap = argparse.ArgumentParser(description="Regenerate the MCP tool-name snapshot.")
    ap.add_argument("--internal-file", required=True)
    ap.add_argument("--store-dir", default=None)
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--out", default=DEFAULT_OUT)
    a = ap.parse_args(argv)
    store = a.store_dir or cc_store_dir()
    if not store or not os.path.isdir(store):
        print("ERROR: no Claude Desktop CC session store found")
        return 2
    conn, records = connector_tools(store, a.days)
    if not conn:
        print("ERROR: no enabledMcpTools keys in %s within %d days" % (store, a.days))
        return 2
    snap = {
        "_doc": ("R-06 MCP tool-name snapshot. Regenerate with "
                 "hooks/tests/lib/refresh_mcp_tool_snapshot.py; test-mcp-delete-tiers.py "
                 "fails when captured_at is older than 90 days."),
        "captured_at": datetime.date.today().isoformat(),
        "window_days": a.days,
        "source_records": records,
        "internal_source": os.path.basename(a.internal_file),
        "connector_tools": conn,
        "internal_tools": internal_tools(a.internal_file),
    }
    with open(a.out, "w", encoding="ascii", newline="\n") as fh:
        json.dump(snap, fh, indent=1, sort_keys=True, ensure_ascii=True)
        fh.write("\n")
    print("wrote %s: %d connector tools from %d records, %d internal tools"
          % (a.out, len(conn), records, len(snap["internal_tools"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
