#!/usr/bin/env python3
"""Agent usage report: real Agent/Task dispatches per custom agent, plus zero-use flags.

Counts unique tool_use ids whose input.subagent_type names a definition in
~/.claude/agents/, across ~/.claude/projects/**/*.jsonl (parent + subagent transcripts).
Read-only. Stdlib only. ASCII-only output (Windows cp1252 console).

Usage:
    python agent-usage-report.py [--days 30] [--min-age-days 30] [--out FILE] [--json]

Zero-use rule: an agent with 0 dispatches in the window AND a definition older than
--min-age-days is flagged REVIEW (retire, rewire, or fix). Younger agents are YOUNG.
Workflow scripts dispatch with agent(prompt, {agentType: '<name>'}) and never emit the Agent
tool's subagent_type, so they are counted separately: each persisted
<session>/workflows/wf_*.json run whose script names the agent counts as one Workflow run
(runs, not calls). Either kind of evidence clears the zero-use flag. Caveat printed in the
report: transcript and workflow-run retention bound the window.
"""
import argparse
import datetime
import glob
import json
import os
import re
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
            try:
                out[fn[:-3]] = _first_commit_epoch(path) or os.path.getmtime(path)
            except OSError:
                continue  # moved/archived by another session mid-run: skip, don't abort
    return out


def _ts_epoch(raw):
    """Epoch for an ISO-8601 transcript timestamp, or None if absent/unparseable."""
    if not isinstance(raw, str) or not raw:
        return None
    try:
        dt = datetime.datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt.timestamp()


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
                    if not isinstance(obj, dict):
                        continue
                    msg = obj.get("message")
                    content = msg.get("content") if isinstance(msg, dict) else None
                    if not isinstance(content, list):
                        continue
                    raw_ts = obj.get("timestamp")
                    raw_ts = raw_ts if isinstance(raw_ts, str) else ""
                    # The mtime check above is only a fast pre-filter: a recently touched
                    # transcript can still hold old dispatches, so bound by each dispatch's
                    # own timestamp too (unparseable/absent -> keep, fail open).
                    line_epoch = _ts_epoch(raw_ts)
                    if since_epoch and line_epoch is not None and line_epoch < since_epoch:
                        continue
                    ts = raw_ts[:10]
                    for block in content:
                        if (isinstance(block, dict) and block.get("type") == "tool_use"
                                and block.get("name") in ("Agent", "Task")):
                            inp = block.get("input")
                            st = inp.get("subagent_type") if isinstance(inp, dict) else None
                            if isinstance(st, str) and st in found:
                                tid = block.get("id")
                                found[st].add(tid if isinstance(tid, str) and tid
                                              else (path, line[:40]))
                                if ts and (oldest is None or ts < oldest):
                                    oldest = ts
        except OSError:
            continue
    return found, scanned, oldest


_WF_AGENT_TYPE_RE = re.compile(r"""agentType\s*:\s*['"]([A-Za-z0-9:_-]+)['"]""")


def count_workflow_runs(projects_dir, names, since_epoch):
    """Return {name: set(runId)} of Workflow runs whose script names the agent.

    Workflow scripts dispatch with agent(prompt, {agentType: '<name>'}) and never emit the
    Agent tool's subagent_type, so count_dispatches cannot see them. Each run is persisted
    as <session>/workflows/wf_*.json with its script, runId and timestamp; a run whose
    script references the agent is evidence the agent is in use. This counts RUNS, not
    calls: per-agent call counts inside a run are not recorded. Fails open on bad files.
    """
    runs = {n: set() for n in names}
    wanted = set(names)
    if not os.path.isdir(projects_dir):
        return runs
    pattern = os.path.join(projects_dir, "**", "workflows", "wf_*.json")
    for path in glob.glob(pattern, recursive=True):
        try:
            with open(path, encoding="utf-8", errors="ignore") as fh:
                obj = json.load(fh)
        except (OSError, ValueError):
            continue
        if not isinstance(obj, dict) or not isinstance(obj.get("script"), str):
            continue
        epoch = _ts_epoch(obj.get("timestamp"))
        if epoch is None:
            try:
                epoch = os.path.getmtime(path)
            except OSError:
                continue
        if since_epoch and epoch < since_epoch:
            continue
        run_id = obj.get("runId")
        run_id = run_id if isinstance(run_id, str) and run_id else os.path.basename(path)
        for agent_type in set(_WF_AGENT_TYPE_RE.findall(obj["script"])):
            if agent_type in wanted:
                runs[agent_type].add(run_id)
    return runs


def build_report(agents, found, days, min_age_days, now, wf=None):
    rows = []
    for name in sorted(agents):
        n = len(found.get(name, ()))
        w = len((wf or {}).get(name, ()))
        age_days = int((now - agents[name]) / 86400)
        if n > 0 or w > 0:
            flag = "ok"
        elif age_days >= min_age_days:
            flag = "REVIEW"
        else:
            flag = "YOUNG"
        rows.append({"agent": name, "dispatches": n, "workflow_runs": w,
                     "def_age_days": age_days, "flag": flag})
    rows.sort(key=lambda r: (-r["dispatches"], -r["workflow_runs"], r["agent"]))
    return rows


def render(rows, days, scanned, oldest, today):
    lines = ["# Agent usage report - %s (window: last %d days)" % (today, days), ""]
    review = [r["agent"] for r in rows if r["flag"] == "REVIEW"]
    young = [r["agent"] for r in rows if r["flag"] == "YOUNG"]
    lines.append("%d agents - %d used - %d REVIEW (zero use, definition older than the age floor) - %d YOUNG"
                 % (len(rows), sum(1 for r in rows if r["dispatches"] or r.get("workflow_runs")),
                    len(review), len(young)))
    lines.append("")
    lines.append("| Agent | Dispatches | Workflow runs | Definition age (d) | Flag |")
    lines.append("|---|---:|---:|---:|---|")
    for r in rows:
        lines.append("| %s | %d | %d | %d | %s |" % (
            r["agent"], r["dispatches"], r.get("workflow_runs", 0), r["def_age_days"], r["flag"]))
    lines.append("")
    if review:
        lines.append("REVIEW: " + ", ".join(review) + " - retire, rewire to a caller, or fix (check tools vs body).")
    lines.append("Scanned %d transcripts; oldest matching dispatch seen: %s." % (scanned, oldest or "none"))
    lines.append("Dispatches = Agent/Task tool calls. Workflow runs = persisted Workflow runs whose script "
                 "names the agent (runs, not dispatches: call counts inside a run are not recorded); "
                 "either counts as use.")
    lines.append("Caveats: transcript and workflow-run retention bound the window; "
                 "definition age = first git commit of the file (mtime if untracked).")
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
    wf = count_workflow_runs(args.projects_dir, list(agents), now - args.days * 86400)
    rows = build_report(agents, found, args.days, args.min_age_days, now, wf)
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
