#!/usr/bin/env python3
"""Agent usage report: real Agent/Task dispatches per custom agent, plus zero-use flags.

Counts unique tool_use ids whose input.subagent_type names a definition in
~/.claude/agents/, across ~/.claude/projects/**/*.jsonl (parent + subagent transcripts).
Read-only. Stdlib only. ASCII-only output (Windows cp1252 console).

Usage:
    python agent-usage-report.py [--days 30] [--min-age-days 30] [--out FILE] [--json]

Zero-use rule: an agent with 0 dispatches in the window AND a definition older than
--min-age-days is flagged REVIEW (retire, rewire, or fix). Younger agents are YOUNG.
Caveats printed in the report: Workflow-internal dispatches may not appear as tool_use
lines, and transcript retention bounds the window.
"""
import argparse
import datetime
import glob
import json
import os
import subprocess
import sys

HOME = os.path.expanduser("~")
CLAUDE_DIR = os.path.join(HOME, ".claude")


def _first_commit_epoch(path):
    """Epoch of the commit that first added `path`, or None (not in git / git unavailable).

    File mtime is a poor age signal here: a checkout or an in-place edit resets it, which
    made long-lived agents read as brand new.
    """
    try:
        r = subprocess.run(
            ["git", "-C", os.path.dirname(path), "log", "--diff-filter=A", "--follow",
             "--format=%at", "--", os.path.basename(path)],
            capture_output=True, text=True, timeout=20)
        times = [int(x) for x in r.stdout.split() if x.isdigit()]
        return float(min(times)) if times else None
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


def list_agents(agents_dir):
    """Return {name: created_epoch} for every agents/*.md (stem = name).

    created = first git commit that added the file; falls back to mtime when untracked.
    """
    out = {}
    if not os.path.isdir(agents_dir):
        return out
    for fn in os.listdir(agents_dir):
        if fn.lower().endswith(".md"):
            path = os.path.join(agents_dir, fn)
            out[fn[:-3]] = _first_commit_epoch(path) or os.path.getmtime(path)
    return out


def count_dispatches(projects_dir, names, since_epoch):
    """Return ({name: set(tool_use_id)}, transcripts_scanned, oldest_ts_seen)."""
    found = {n: set() for n in names}
    scanned = 0
    oldest = None
    if not os.path.isdir(projects_dir):
        return found, scanned, oldest
    for path in glob.glob(os.path.join(projects_dir, "**", "*.jsonl"), recursive=True):
        try:
            if os.path.getmtime(path) < since_epoch:
                continue
            scanned += 1
            with open(path, encoding="utf-8", errors="ignore") as fh:
                for line in fh:
                    if "subagent_type" not in line:
                        continue
                    try:
                        obj = json.loads(line)
                    except ValueError:
                        continue
                    content = (obj.get("message") or {}).get("content")
                    if not isinstance(content, list):
                        continue
                    ts = (obj.get("timestamp") or "")[:10]
                    for block in content:
                        if (isinstance(block, dict) and block.get("type") == "tool_use"
                                and block.get("name") in ("Agent", "Task")):
                            st = (block.get("input") or {}).get("subagent_type")
                            if st in found:
                                found[st].add(block.get("id") or (path, line[:40]))
                                if ts and (oldest is None or ts < oldest):
                                    oldest = ts
        except OSError:
            continue
    return found, scanned, oldest


def build_report(agents, found, days, min_age_days, now):
    rows = []
    for name in sorted(agents):
        n = len(found.get(name, ()))
        age_days = int((now - agents[name]) / 86400)
        if n > 0:
            flag = "ok"
        elif age_days >= min_age_days:
            flag = "REVIEW"
        else:
            flag = "YOUNG"
        rows.append({"agent": name, "dispatches": n, "def_age_days": age_days, "flag": flag})
    rows.sort(key=lambda r: (-r["dispatches"], r["agent"]))
    return rows


def render(rows, days, scanned, oldest, today):
    lines = ["# Agent usage report - %s (window: last %d days)" % (today, days), ""]
    review = [r["agent"] for r in rows if r["flag"] == "REVIEW"]
    young = [r["agent"] for r in rows if r["flag"] == "YOUNG"]
    lines.append("%d agents - %d used - %d REVIEW (zero use, definition older than the age floor) - %d YOUNG"
                 % (len(rows), sum(1 for r in rows if r["dispatches"]), len(review), len(young)))
    lines.append("")
    lines.append("| Agent | Dispatches | Definition age (d) | Flag |")
    lines.append("|---|---:|---:|---|")
    for r in rows:
        lines.append("| %s | %d | %d | %s |" % (r["agent"], r["dispatches"], r["def_age_days"], r["flag"]))
    lines.append("")
    if review:
        lines.append("REVIEW: " + ", ".join(review) + " - retire, rewire to a caller, or fix (check tools vs body).")
    lines.append("Scanned %d transcripts; oldest matching dispatch seen: %s." % (scanned, oldest or "none"))
    lines.append("Caveats: dispatches made inside Workflow runs may not appear as tool_use lines; "
                 "transcript retention bounds the window; definition age = first git commit of the file (mtime if untracked).")
    return "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--min-age-days", type=int, default=30)
    ap.add_argument("--agents-dir", default=os.path.join(CLAUDE_DIR, "agents"))
    ap.add_argument("--projects-dir", default=os.path.join(CLAUDE_DIR, "projects"))
    ap.add_argument("--out")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    now = datetime.datetime.now().timestamp()
    agents = list_agents(args.agents_dir)
    found, scanned, oldest = count_dispatches(
        args.projects_dir, list(agents), now - args.days * 86400)
    rows = build_report(agents, found, args.days, args.min_age_days, now)
    today = datetime.date.today().isoformat()
    text = json.dumps(rows, indent=2) if args.json else render(rows, args.days, scanned, oldest, today)
    if args.out:
        with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
