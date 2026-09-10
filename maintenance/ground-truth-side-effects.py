#!/usr/bin/env python3
"""ground-truth-side-effects.py -- Stage 1 of the ORA Ground-Truth Auditor.

Per run, derives CANDIDATE side effects from its transcript (or, if unjoined,
treats it as requiring a verifier -- see has_side_effects()). Runs with zero
side effects get a cheap deterministic stamp and never reach a verifier
agent -- this is the approved cost gate (design spec Sec 5 Stage 1): ~8-15
verifiers/night instead of 64.

Usage:
    python ground-truth-side-effects.py --run-index PATH [--out PATH]
"""
import argparse
import json
import os
import re
import sys

# Patterns matched against a transcript's tool_use records (Bash commands and
# MCP tool names) to detect a candidate side effect. Matching the TOOL CALL,
# not its outcome -- Stage 3's CLAIM ACCURACY axis re-verifies the actual
# published artifact; Stage 1 only decides whether a verifier is worth
# dispatching at all.
SIDE_EFFECT_PATTERNS = {
    "email_sent": re.compile(r"send-via-outlook\.ps1", re.IGNORECASE),
    "notion_write": re.compile(r"notion-(create-pages|update-page)"),
    "git_push": re.compile(r"\bgit\s+push\b"),
    "oi_filed": re.compile(r"allocate-oi-id\.py"),
    "file_write": re.compile(r'"name"\s*:\s*"(Write|Edit)"'),
}


def extract_side_effects(transcript_path):
    """Scan one transcript .jsonl for candidate side effects. Returns a dict
    {effect_name: count}; empty dict if the transcript has none or cannot be
    read. Never raises -- an unreadable transcript degrades to {} exactly
    like a run with no side effects (has_side_effects()'s `joined` check,
    not this function, is where "could not read" is distinguished from
    "read and clean")."""
    if not transcript_path or not os.path.isfile(transcript_path):
        return {}
    found = {}
    try:
        with open(transcript_path, encoding="utf-8", errors="replace") as f:
            for line in f:
                for name, pattern in SIDE_EFFECT_PATTERNS.items():
                    if pattern.search(line):
                        found[name] = found.get(name, 0) + 1
    except Exception:
        return {}
    return found


def has_side_effects(run_record):
    """True if a run record (from the Stage 0 index, annotated with
    side_effects) registered at least one candidate side effect, OR if it
    could not be joined to a transcript at all -- an unjoined run cannot be
    proven clean, so it is never silently gated out (spec Sec 9 R1a: an
    unjoined run is UNVERIFIABLE, never treated as clean)."""
    if not run_record.get("joined"):
        return True  # external enumeration required -- never assume clean
    return bool(run_record.get("side_effects"))


def annotate_run_index(run_index):
    """Adds `side_effects` (dict) to every run in a loaded run-index document,
    and a top-level `side_effect_stats` summary (gated vs ungated counts --
    spec Sec 9 R3, so cost drift is visible in the digest rather than
    discovered on a bill). Mutates and returns run_index."""
    gated = ungated = 0
    for run in run_index.get("runs", []):
        run["side_effects"] = extract_side_effects(run.get("transcript"))
        if has_side_effects(run):
            ungated += 1  # dispatched to a verifier
        else:
            gated += 1  # stamped clean, no agent
    run_index["side_effect_stats"] = {
        "verifiers_dispatched": ungated,
        "stamped_clean": gated,
        "total": ungated + gated,
    }
    return run_index


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-index", required=True, help="Stage 0 run-index JSON path")
    parser.add_argument("--out", default=None, help="Output path (default: overwrite --run-index)")
    args = parser.parse_args(argv)

    run_index = json.load(open(args.run_index, encoding="utf-8"))
    annotate_run_index(run_index)

    out = args.out or args.run_index
    json.dump(run_index, open(out, "w", encoding="utf-8"), indent=2)
    stats = run_index["side_effect_stats"]
    print("{} runs: {} to verifier, {} stamped clean".format(
        stats["total"], stats["verifiers_dispatched"], stats["stamped_clean"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
