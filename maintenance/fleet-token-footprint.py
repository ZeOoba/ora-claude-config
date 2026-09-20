#!/usr/bin/env python3
"""ORA fleet token-footprint report -- first-turn context per scheduled task.

WHY (2026-09-19). A headless `claude -p --tools ""` measured 210K tokens of context
and was read as "MCP costs ~197K per call". `--tools ""` also removes ToolSearch, which
is consistent with MCP schemas loading eagerly instead of deferring (not isolated in a
controlled test). A default-tools `claude -p` (2.1.278, one sample) measured 71K.
Nothing surfaced per-task footprints, so a claim like that could not be checked; this
report shows what scheduled runs actually carried, from real transcripts.

READ-ONLY. Prints one row per scheduled task:
  RUNS/WK  expected fires/week from the LIVE registry cron (never fleet-roster.md, which
           lags the registry). Standard 5-field crons only; named fields (MON, JAN) are
           accepted; anything unparseable counts as 0. When both day-of-month and
           day-of-week are restricted, cron ORs them; this report does not.
  N        runs found. CC = every run whose first record is inside --days (dated by the
           transcript's own first timestamp, NOT file mtime, which OneDrive/sync rewrites).
           LAMS = at most the 2 newest sessions per task inside --days, so N <= 2 there.
  FIRST    median first-turn context tokens (input + cache_creation + cache_read)
  CALLS    median unique API calls per run (unique message ids, not transcript records)
  TS       ToolSearch called in any run
  MCP      MCP server-id prefixes actually called (not their schema cost)

Sources: CC/MCP = ~/.claude/projects/*/<session>.jsonl whose FIRST user message is a
<scheduled-task name="..."> block; LAMS/Cowork = local-agent-mode-sessions audit.jsonl
for sessionType == "scheduled" sessions.

Scope: registry-driven. Runs of tasks that are no longer in either live registry (retired
or one-off checks) are not shown, so fleet-wide totals from this report undercount.

Usage:  python fleet-token-footprint.py [--days 30] [--json]
Exit 0 always (a report, not a gate): a malformed --days falls back to 30, and any
failure prints a one-line ASCII message. ASCII-only output.
"""
import argparse
import collections
import datetime
import glob
import json
import os
import re
import statistics
import sys
import time

HOME = os.path.expanduser("~")
PROJECTS = os.path.join(HOME, ".claude", "projects")
APPDATA = os.environ.get("APPDATA", os.path.join(HOME, "AppData", "Roaming"))
SESSIONS_ROOT = os.path.join(APPDATA, "Claude")
HEADER_RECORDS = 300           # records to scan for the first user message
TASK_RE = re.compile(r'\A\s*<scheduled-task name="([^"]+)"')
_MONTHS = {n: i + 1 for i, n in enumerate("JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC".split())}
_DAYS = {n: i for i, n in enumerate("SUN MON TUE WED THU FRI SAT".split())}


def _names(field, table):
    return re.sub(r"[A-Za-z]{3}", lambda m: str(table.get(m.group(0).upper(), m.group(0))), field)


def _rng(field, lo, hi):
    out = set()
    for part in field.split(","):
        step = 1
        if "/" in part:
            part, step = part.split("/")
            step = int(step)
        if step < 1:
            raise ValueError("bad step")
        if part == "*":
            a, b = lo, hi
        elif "-" in part:
            a, b = (int(x) for x in part.split("-"))
        else:
            a = b = int(part)
        out |= set(range(a, b + 1, step))
    return out


def runs_per_week(cron):
    """Expected fires/week for a 5-field cron. One-time (@...), expired or unparseable -> 0."""
    try:
        if not isinstance(cron, str) or not cron or cron.startswith("@") or "EXPIRED" in cron:
            return 0.0
        fields = cron.split()
        if len(fields) != 5:
            return 0.0
        m, h, dom, mon, dow = fields
        fires = len(_rng(m, 0, 59)) * len(_rng(h, 0, 23))
        mon = _names(mon, _MONTHS)
        dow = _names(dow, _DAYS)
        if dom == "*" and mon == "*":
            days = len({d % 7 for d in _rng(dow, 0, 7)})     # 0 and 7 are both Sunday
            return float(fires * days)
        nd = len(_rng(dom, 1, 31)) if dom != "*" else 30.4
        nm = len(_rng(mon, 1, 12)) if mon != "*" else 12
        return fires * nd * nm / 52.0
    except (ValueError, TypeError):
        return 0.0


def _total(usage):
    return sum(usage.get(k, 0) or 0 for k in
               ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"))


def scan_lines(lines):
    """-> (first_turn_tokens|None, unique_api_calls, toolsearch_used, mcp_prefixes)."""
    ids, first, ts, mcp = set(), None, False, set()
    for line in lines:
        if '"assistant"' not in line[:400]:
            continue
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        if rec.get("type") != "assistant":
            continue
        msg = rec.get("message") or {}
        ids.add(msg.get("id") or rec.get("uuid"))
        usage = msg.get("usage") or {}
        if first is None and (usage.get("cache_creation_input_tokens", 0) or usage.get("cache_read_input_tokens", 0)):
            first = _total(usage)
        for blk in msg.get("content") or []:
            if isinstance(blk, dict) and blk.get("type") == "tool_use":
                name = blk.get("name", "")
                if name == "ToolSearch":
                    ts = True
                elif name.startswith("mcp__"):
                    mcp.add(name.split("__")[1][:10])
    return first, len(ids), ts, mcp


def _user_text(rec):
    c = (rec.get("message") or {}).get("content")
    if isinstance(c, list):
        c = " ".join(x.get("text", "") for x in c if isinstance(x, dict))
    return c if isinstance(c, str) else ""


def _epoch(ts):
    try:
        return datetime.datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
    except (ValueError, AttributeError):
        return None


def task_header(fh):
    """Stream `fh` to the first real user message. -> (task_name|None, epoch|None, first_record_line).

    Consumes lines from `fh` up to and including that record so the caller can continue
    scanning the same handle without re-reading the file."""
    for _ in range(HEADER_RECORDS):
        line = fh.readline()
        if not line:
            break
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        if rec.get("type") == "user" and not rec.get("isMeta"):
            m = TASK_RE.match(_user_text(rec))
            return (m.group(1) if m else None), _epoch(rec.get("timestamp")), line
    return None, None, None


def _add(per, name, result):
    first, calls, ts, mcp = result
    row = per[name]
    if first:
        row["first"].append(first)
    row["calls"].append(calls)
    row["ts"] = row["ts"] or ts
    row["mcp"] |= mcp


def _new():
    return collections.defaultdict(lambda: {"first": [], "calls": [], "ts": False, "mcp": set()})


def collect_cc(days):
    cut = time.time() - days * 86400
    per = _new()
    for path in glob.glob(os.path.join(PROJECTS, "*", "*.jsonl")):
        try:
            if os.path.getmtime(path) < cut:          # cheap prefilter; mtimes only ever overstate recency
                continue
            with open(path, encoding="utf-8", errors="replace") as fh:
                name, epoch, _ = task_header(fh)
                if not name or (epoch is not None and epoch < cut):
                    continue
                _add(per, name, scan_lines(fh))
        except OSError:
            continue
    return per


def _registry(fleet_dir):
    for p in glob.glob(os.path.join(SESSIONS_ROOT, fleet_dir, "*", "*", "scheduled-tasks.json")):
        try:
            with open(p, encoding="utf-8") as fh:
                return {t["id"]: t for t in json.load(fh)["scheduledTasks"]}, os.path.dirname(p)
        except (OSError, ValueError, KeyError):
            continue
    return {}, None


def collect_lams(lams_dir, days):
    per = _new()
    if not lams_dir:
        return per
    cut = time.time() - days * 86400
    metas = sorted(glob.glob(os.path.join(lams_dir, "local_*.json")), key=os.path.getmtime, reverse=True)
    seen = collections.Counter()
    for meta in metas:
        try:
            with open(meta, encoding="utf-8", errors="replace") as fh:
                d = json.load(fh)
            task = d.get("scheduledTaskId")
            created = d.get("createdAt")
            if d.get("sessionType") != "scheduled" or not task or seen[task] >= 2:
                continue
            if isinstance(created, (int, float)) and created / 1000.0 < cut:
                continue
            audit = os.path.join(meta[:-5], "audit.jsonl")
            if not os.path.exists(audit):
                continue
            seen[task] += 1
            with open(audit, encoding="utf-8", errors="replace") as fh:
                _add(per, task, scan_lines(fh))
        except (OSError, ValueError):
            continue
    return per


def build(days):
    rows = []
    cc_reg, _ = _registry("claude-code-sessions")
    lams_reg, lams_dir = _registry("local-agent-mode-sessions")
    for fleet, reg, per in (("cc", cc_reg, collect_cc(days)), ("lams", lams_reg, collect_lams(lams_dir, days))):
        for tid, t in reg.items():
            s = per.get(tid)
            rows.append({
                "task": tid, "fleet": fleet, "cron": t.get("cronExpression") or ("@" + str(t.get("fireAt", ""))),
                "enabled": bool(t.get("enabled")),
                "runs_per_week": round(runs_per_week(t.get("cronExpression")), 2),
                "n": len(s["calls"]) if s else 0,
                "first": int(statistics.median(s["first"])) if s and s["first"] else None,
                "calls": statistics.median(s["calls"]) if s and s["calls"] else None,
                "toolsearch": bool(s and s["ts"]),
                "mcp": sorted(s["mcp"]) if s else [],
            })
    return rows


def sort_rows(rows):
    """Enabled tasks first, then by first-turn tokens x runs/week (weekly footprint)."""
    return sorted(rows, key=lambda r: (not r["enabled"], -((r["first"] or 0) * r["runs_per_week"])))


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--json", action="store_true")
    try:
        return ap.parse_known_args(argv)[0]
    except SystemExit:                       # malformed value: report anyway with defaults
        return ap.parse_known_args([])[0]


def main(argv=None):
    args = parse_args(argv)
    try:
        rows = build(args.days)
    except Exception as exc:  # noqa: BLE001 -- a report must not raise
        msg = "fleet-token-footprint: could not build report: %s: %s" % (type(exc).__name__, exc)
        print(msg.encode("ascii", "replace").decode("ascii"))
        return 0
    if args.json:
        print(json.dumps(rows, indent=1))
        return 0
    rows = sort_rows(rows)
    print("%-40s %-4s %-3s %7s %3s %8s %6s %-5s %s" % ("TASK", "FLT", "EN", "RUNS/WK", "N", "FIRST", "CALLS", "TS", "MCP"))
    for r in rows:
        line = "%-40s %-4s %-3s %7.2f %3d %8s %6s %-5s %s" % (
            r["task"][:40], r["fleet"], "on" if r["enabled"] else "off", r["runs_per_week"], r["n"],
            r["first"] if r["first"] else "-", "%g" % r["calls"] if r["calls"] else "-",
            r["toolsearch"], ",".join(r["mcp"]))
        print(line.encode("ascii", "replace").decode("ascii"))
    firsts = [r["first"] for r in rows if r["first"]]
    if firsts:
        print("\nfirst-turn tokens: min %d  median %d  max %d  (n=%d tasks)" %
              (min(firsts), statistics.median(firsts), max(firsts), len(firsts)))
    print("Reference points: default-tools `claude -p` ~71K (one sample, CLI 2.1.278); "
          "`claude -p --tools \"\"` ~210K (user-supplied; consistent with, not proof of, eager MCP loading).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
