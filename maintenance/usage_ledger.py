#!/usr/bin/env python3
"""ORA MCP/Skill usage ledger (read-only over session logs; append-only ledger).

Why: LAMS keeps audit.jsonl for ~2 weeks only (85/525 sessions at 2026-09-30) and
~/.claude.json#skillUsage is Code-surface Skill-tool only. This persists per-server,
per-tool and per-skill counts before the source rotates.

Subcommands:
  scan     [--root DIR ...] [--ledger F]   append new/grown sessions to ledger
  dc       [--dc-config F] [--dc-history F] [--ledger F]   snapshot Desktop Commander's own counters
  summary  [--ledger F] [--days N ...] [--json]            aggregate latest record per session
Stdlib only. Never writes outside --ledger. Exit 0 on success, 2 on unreadable root.
"""
import argparse, json, os, re, sys, time, glob
from collections import defaultdict
from datetime import datetime, timezone, timedelta

TOOL_RE = re.compile(r'"name"\s*:\s*"(mcp__[A-Za-z0-9_\-]+__[^"]+)"')
SKILL_RE = re.compile(r'"name"\s*:\s*"Skill"\s*,\s*"input"\s*:\s*\{\s*"skill"\s*:\s*"([^"]+)"')
DEFAULT_LEDGER = os.path.expanduser(r"~/.claude/maintenance/_state/mcp-usage-ledger.jsonl")

# Cowork logs some cloud connectors under their connector UUID. Verified 2026-09-30 by tool-name signature.
ALIASES = {
    "c5f4869f-7d3a-4472-a66a-8e61315feb51": "Notion",
    "c5f4869f-7d3a-4472-a66a-8e59a4b760": "Notion(variant-id)",
    "c0ea3c01-b8f1-4371-aa06-08a1449f59fc": "ms365",
    "a3e380ce-2ea9-4b42-92d9-37c588a4b760": "HubSpot",
    "plugin_desktop-commander_desktop-commander": "Desktop_Commander(plugin)",
}

def now_iso(): return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def load_ledger(path):
    recs = []
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for ln in f:
                ln = ln.strip()
                if ln:
                    try: recs.append(json.loads(ln))
                    except json.JSONDecodeError: pass  # tolerate torn tail line
    return recs

def latest_by_session(recs):
    best = {}
    for r in recs:
        if r.get("kind") != "session": continue
        k = r["session"]
        if k not in best or r.get("bytes", 0) >= best[k].get("bytes", 0):
            best[k] = r
    return best

def parse_audit(path):
    counts = defaultdict(lambda: defaultdict(int)); skills = defaultdict(int)
    with open(path, encoding="utf-8", errors="replace") as f:
        for ln in f:
            for m in TOOL_RE.finditer(ln):
                parts = m.group(1).split("__", 2)
                if len(parts) == 3: counts[ALIASES.get(parts[1], parts[1])][parts[2]] += 1
            for m in SKILL_RE.finditer(ln):
                skills[m.group(1)] += 1
    return {s: dict(t) for s, t in counts.items()}, dict(skills)

def cmd_scan(a):
    roots = a.root or [os.path.expanduser(r"~\AppData\Roaming\Claude\local-agent-mode-sessions")]
    files = []
    for r in roots:
        if not os.path.isdir(r):
            print(f"UNREADABLE root: {r}", file=sys.stderr); return 2
        files += glob.glob(os.path.join(r, "**", "audit.jsonl"), recursive=True)
    known = latest_by_session(load_ledger(a.ledger))
    os.makedirs(os.path.dirname(os.path.abspath(a.ledger)), exist_ok=True)
    added = 0
    with open(a.ledger, "a", encoding="utf-8") as out:
        for p in sorted(files):
            sid = os.path.basename(os.path.dirname(p))
            st = os.stat(p)
            if sid in known and known[sid].get("bytes", 0) >= st.st_size: continue
            counts, skills = parse_audit(p)
            rec = {"kind": "session", "ts": now_iso(), "session": sid,
                   "mtime": datetime.fromtimestamp(st.st_mtime, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                   "bytes": st.st_size, "counts": counts, "skills": skills}
            out.write(json.dumps(rec, separators=(",", ":")) + "\n"); added += 1
    print(f"scan: {len(files)} audit files, {added} records appended -> {a.ledger}")
    return 0

def cmd_dc(a):
    snap = {"kind": "dc", "ts": now_iso()}
    try:
        with open(a.dc_config, encoding="utf-8") as f:
            cfg = json.load(f)
        us = cfg.get("usageStats", {})
        snap["toolCounts"] = us.get("toolCounts", {})
        snap["totalToolCalls"] = us.get("totalToolCalls", sum(snap["toolCounts"].values()))
    except Exception as e:
        snap["config_error"] = str(e)
    # durable per-call history: count lines + last-7d by timestamp (no payloads kept)
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        n = n7 = 0; first = last = None; tools7 = defaultdict(int)
        ts_re = re.compile(r'^\{"timestamp":"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})')
        tn_re = re.compile(r'"toolName":"([^"]+)"')
        with open(a.dc_history, encoding="utf-8", errors="replace") as f:
            for ln in f:
                n += 1
                m = ts_re.match(ln)
                if m:
                    t = datetime.strptime(m.group(1), "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
                    first = first or m.group(1); last = m.group(1)
                    if t >= cutoff:
                        n7 += 1
                        tn = tn_re.search(ln[:400])
                        if tn: tools7[tn.group(1)] += 1
        snap.update({"history_lines": n, "history_last7d": n7, "history_first_ts": first,
                     "history_last_ts": last, "history_tools_7d": dict(tools7)})
    except Exception as e:
        snap["history_error"] = str(e)
    prev = [r for r in load_ledger(a.ledger) if r.get("kind") == "dc" and "toolCounts" in r]
    if prev and "toolCounts" in snap:
        p = prev[-1]["toolCounts"]
        snap["delta_since_prev"] = {k: v - p.get(k, 0) for k, v in snap["toolCounts"].items() if v - p.get(k, 0)}
        snap["prev_ts"] = prev[-1]["ts"]
    os.makedirs(os.path.dirname(os.path.abspath(a.ledger)), exist_ok=True)
    with open(a.ledger, "a", encoding="utf-8") as out:
        out.write(json.dumps(snap, separators=(",", ":")) + "\n")
    print("dc:", {k: snap[k] for k in snap if k not in ("toolCounts",)})
    return 0

def cmd_summary(a):
    recs = load_ledger(a.ledger)
    best = latest_by_session(recs)
    out = {"generated": now_iso(), "sessions_in_ledger": len(best), "windows": {}}
    for d in (a.days or [7, 30, 0]):
        cut = None if d == 0 else (datetime.now(timezone.utc) - timedelta(days=d)).strftime("%Y-%m-%dT%H:%M:%SZ")
        srv = defaultdict(lambda: defaultdict(int)); sk = defaultdict(int); n = 0
        for r in best.values():
            if cut and r["mtime"] < cut: continue
            n += 1
            for s, t in r["counts"].items():
                for tool, c in t.items(): srv[ALIASES.get(s, s)][tool] += c
            for s, c in r["skills"].items(): sk[s] += c
        out["windows"]["all" if d == 0 else f"{d}d"] = {
            "sessions": n,
            "servers": {s: sum(t.values()) for s, t in sorted(srv.items(), key=lambda x: -sum(x[1].values()))},
            "skills": dict(sorted(sk.items(), key=lambda x: -x[1])[:25])}
    dcs = [r for r in recs if r.get("kind") == "dc"]
    if dcs: out["dc_latest"] = {k: dcs[-1].get(k) for k in ("ts", "totalToolCalls", "history_last7d", "delta_since_prev", "prev_ts")}
    out["span"] = {"earliest_session_mtime": min((r["mtime"] for r in best.values()), default=None)}
    if a.json: print(json.dumps(out, indent=1))
    else:
        for w, v in out["windows"].items():
            print(f"[{w}] sessions={v['sessions']}  " + "  ".join(f"{s}={c}" for s, c in v["servers"].items()))
    return 0

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    s = sp.add_parser("scan"); s.add_argument("--root", action="append"); s.add_argument("--ledger", default=DEFAULT_LEDGER); s.set_defaults(f=cmd_scan)
    d = sp.add_parser("dc"); d.add_argument("--dc-config", default=os.path.expanduser(r"~/.claude-server-commander/config.json"))
    d.add_argument("--dc-history", default=os.path.expanduser(r"~/.claude-server-commander/tool-history.jsonl")); d.add_argument("--ledger", default=DEFAULT_LEDGER); d.set_defaults(f=cmd_dc)
    m = sp.add_parser("summary"); m.add_argument("--ledger", default=DEFAULT_LEDGER); m.add_argument("--days", type=int, action="append"); m.add_argument("--json", action="store_true"); m.set_defaults(f=cmd_summary)
    a = ap.parse_args(); sys.exit(a.f(a))

if __name__ == "__main__": main()
