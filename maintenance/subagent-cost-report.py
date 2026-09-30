#!/usr/bin/env python
"""Subagent cost report: per agent-type run count, weighted input, and model mix.

Reads subagent transcripts under ~/.claude/projects/*/*/subagents/agent-*.jsonl
(plus the sibling .meta.json for agentType). Read-only; always exits 0.

Weighted input = fresh input + cache-creation + cache-read/10. An approximation
for ranking agent types, NOT billed spend.

Usage: python subagent-cost-report.py [--days 30] [--top 15]
"""
import argparse
import collections
import glob
import json
import os
import time

FABLE = "fable"


def scan(days):
    root = os.path.expanduser("~/.claude/projects/*/*/subagents/agent-*.jsonl")
    cutoff = time.time() - days * 86400
    agg = collections.defaultdict(
        lambda: {"n": 0, "w_in": 0, "out": 0, "models": collections.Counter(), "prompt": 0}
    )
    files = []
    for f in glob.glob(root):
        try:
            if os.path.getmtime(f) >= cutoff:
                files.append(f)
        except OSError:
            continue
    for f in files:
        agent_type = "?"
        mp = f[: -len(".jsonl")] + ".meta.json"
        if os.path.exists(mp):
            try:
                with open(mp, encoding="utf-8") as fh:
                    agent_type = json.load(fh).get("agentType") or "?"
            except (OSError, ValueError):
                pass
        first_prompt = None
        model = None
        # One JSONL line is written per content block, each repeating the same
        # message.id and usage; keep the max per field per message id so a
        # multi-block message is counted once.
        usage_by_id = {}
        try:
            with open(f, encoding="utf-8", errors="ignore") as fh:
                for line in fh:
                    try:
                        msg = (json.loads(line).get("message")) or {}
                    except ValueError:
                        continue
                    role = msg.get("role")
                    if role == "user" and first_prompt is None:
                        c = msg.get("content")
                        first_prompt = len(c if isinstance(c, str) else json.dumps(c))
                    elif role == "assistant":
                        m = msg.get("model")
                        if m and not m.startswith("<"):  # skip "<synthetic>" error stubs
                            model = m
                        u = msg.get("usage") or {}
                        slot = usage_by_id.setdefault(
                            msg.get("id") or f"anon{len(usage_by_id)}", {}
                        )
                        for k in (
                            "input_tokens",
                            "cache_creation_input_tokens",
                            "cache_read_input_tokens",
                            "output_tokens",
                        ):
                            slot[k] = max(slot.get(k, 0), u.get(k) or 0)
        except OSError:
            continue
        w_in = sum(
            s.get("input_tokens", 0)
            + s.get("cache_creation_input_tokens", 0)
            + s.get("cache_read_input_tokens", 0) // 10
            for s in usage_by_id.values()
        )
        out = sum(s.get("output_tokens", 0) for s in usage_by_id.values())
        a = agg[agent_type]
        a["n"] += 1
        a["w_in"] += w_in
        a["out"] += out
        a["prompt"] += first_prompt or 0
        a["models"][model or "?"] += 1
    return len(files), agg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--top", type=int, default=15)
    args = ap.parse_args()
    total, agg = scan(args.days)
    print(f"subagent transcripts, last {args.days}d: {total}")
    tot_w = sum(a["w_in"] for a in agg.values()) or 1
    fable_all = sum(c for a in agg.values() for m, c in a["models"].items() if FABLE in m)
    print(f"overall Fable share of runs: {fable_all}/{total} = {100 * fable_all / max(total, 1):.0f}%")
    print(f"{'agent type':34} {'runs':>5} {'wIn(M)':>8} {'%wIn':>5} {'avgPrompt':>9} {'fable%':>6}  models")
    rows = sorted(agg.items(), key=lambda kv: -kv[1]["w_in"])[: args.top]
    for t, a in rows:
        fab = sum(c for m, c in a["models"].items() if FABLE in m)
        print(
            f"{t:34} {a['n']:5} {a['w_in'] / 1e6:8.1f} {100 * a['w_in'] / tot_w:4.0f}% "
            f"{a['prompt'] // max(a['n'], 1):9} {100 * fab / max(a['n'], 1):5.0f}%  "
            f"{dict(a['models'])}"
        )


if __name__ == "__main__":
    main()
