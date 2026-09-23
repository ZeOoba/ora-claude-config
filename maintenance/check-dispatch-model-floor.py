#!/usr/bin/env python3
r"""ORA dispatch model-floor probe (OI-052) — deterministic, post-hoc.

WHY THIS EXISTS. CLAUDE.md's "never below Fable" floor for confidential/
financial/governor and security-gate code is carried, per Gabriel's ratified
Option C (2026-07-24), by the `model:'fable'` pin on the security-auditor Agent
dispatch — NOT by the scheduled task's own (server-pinned, inert) frontmatter.
The DISPATCH INTEGRITY GATE asserts the pin was PASSED to the Agent call, but a
pin is honored at SPAWN, not for the DURATION: on the 2026-07-31 and 2026-08-12
sweeps both subagents began on claude-fable-5 and then fell back mid-run to a
below-floor model (opus-5, then opus-4-8), and the below-floor tier produced the
actual findings report. The three spawn-time assertions all PASS in that case —
they are structurally blind to a mid-run fallback. This probe is the fourth,
post-hoc assertion: it reads the subagent transcripts AFTER the run and fails if
any subagent ran below the floor or shows a fallback block.

WHAT IT CHECKS, per agent-*.jsonl transcript in a session's subagents dir:
  every assistant message's model is AT OR ABOVE the floor. A below-floor model
  value is the VIOLATION.

A content block of type "fallback" is RECORDED as informational context, NOT a
standalone violation — what matters is the tier it fell TO. Two independent signals
establish that tier, and either one below the floor is a violation:
  - the per-line `message.model` (this harness writes the actual served tier onto
    post-fallback lines: a run shows `claude-fable-5` then `claude-opus-4-8`), and
  - the fallback event's own `to` field
    (`{"type":"fallback","from":"claude-fable-5","to":"claude-opus-5"}`), ranked
    directly so a below-floor fallback is caught even if message.model never updated.
A fallback whose destination is AT OR ABOVE the floor is compliant and must not
alarm. Gabriel RULED 2026-08-14 that a mid-run fallback to an OPUS tier is
compliant with never-below-Fable (OI-052 closed); the sweep therefore invokes this
with `--floor claude-opus-4-8`, and only a drop BELOW Opus trips it.

FAIL-CLOSED ON ABSENCE. A missing subagents dir, or a dir with zero agent-*.jsonl
files, is a TOOLING ERROR (exit 2), never a silent PASS — an unverifiable floor
is not a held floor (memory: feedback_verified_null_vs_inferred_null). An
agent-*.jsonl with zero assistant/model-bearing lines is likewise a violation,
not a pass, for the same reason.

EXIT CODES:
  0 = every subagent held the floor for its full duration (no below-floor model,
      no fallback block)
  1 = at least one subagent violated the floor (below-floor model or fallback)
  2 = tooling error / verified-null (no dir, no agent files, or a transcript
      with no model-bearing lines)

USAGE:
  check-dispatch-model-floor.py --session <SESSION_ID> [--floor fable]
  check-dispatch-model-floor.py --subagents-dir <PATH>  [--floor fable]

Report-only: reads transcripts, prints a per-agent table, changes nothing.
"""
import argparse
import glob
import json
import os
import sys

# Canonical project dir for the --session convenience form.
PROJECT = "C--Users-Owner-OneDrive---Oxford-Capital-Partners"
CLAUDE = os.environ.get("CLAUDE_HOME", r"C:\Users\Owner\.claude")

# Model tier ranks. Higher = more capable. The Mythos-class tier (fable/mythos,
# same underlying model) sits ABOVE Opus, so opus-5 and every opus-4.x, sonnet,
# and haiku are all BELOW the Fable floor. An UNKNOWN model ranks below the floor
# by construction (fail-closed): a model we can't place must not read as "held".
MODEL_RANK = {
    "claude-mythos-5": 100,
    "claude-mythos-5-1": 100,
    "claude-fable-5-1": 100,
    # claude-fable-5 is superseded (2026-09-02) but stays LOAD-BEARING, not just
    # a courtesy for old transcripts: floor_rank() below builds "claude-%s-5" %
    # floor, so the default `--floor fable` shorthand resolves through THIS key.
    # There is no short-name form for fable-5-1 yet -- only the full id
    # (--floor claude-fable-5-1) resolves it. Deleting this entry breaks the
    # default floor invocation (exit 2, TOOLING ERROR -- fails closed, but loud).
    "claude-fable-5": 100,
    "claude-opus-5-5": 95,  # 2026-09-22 -- above opus-5, still below the Fable floor
    "claude-opus-5": 90,
    "claude-opus-4-8": 80,
    "claude-opus-4.8": 80,
    "claude-opus-4-1": 75,
    "claude-sonnet-5": 70,
    "claude-sonnet-4-5": 65,
    "claude-haiku-4-5": 50,
}
UNKNOWN_RANK = -1  # anything not in MODEL_RANK — fail-closed, always below any floor


def model_rank(model):
    """Rank a model id. Unknown or non-string ids rank below every real floor
    (fail-closed): a value we can't place must never read as 'held'."""
    if not model or not isinstance(model, str):
        return UNKNOWN_RANK
    return MODEL_RANK.get(model, UNKNOWN_RANK)


def floor_rank(floor):
    """Resolve a floor NAME (e.g. 'fable') to its rank. Unknown floor is a usage
    error, surfaced by the caller — here we return None so main() can exit 2."""
    key = "claude-%s-5" % floor if not floor.startswith("claude-") else floor
    return MODEL_RANK.get(key)


def scan_transcript(path, floor):
    """Scan one agent-*.jsonl. Returns a dict:
        {file, models, saw_fallback, first_violation, model_bearing_lines,
         parse_failures: int, read_error: str|None}
    Two kinds of "can't certify" show up here, both handled fail-closed by the
    caller: parse_failures>0 (a JSONL line that didn't parse — a torn/concatenated/
    truncated write is evidence destruction, never "clean"), and read_error (the
    file couldn't be opened/decoded at all). Neither is silently skipped: an
    unreadable transcript is a verified-null, not a pass.
    Uses utf-8-sig so a BOM (e.g. left by a PowerShell rewrite of a transcript)
    does not poison line 1 into a parse failure that hides a first-line breach."""
    models = {}
    saw_fallback = False
    first_fallback_line = None
    first_violation = None
    model_bearing = 0
    parse_failures = 0
    try:
        with open(path, encoding="utf-8-sig") as f:
            for lineno, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except (ValueError, TypeError):
                    # A machine-written JSONL line that won't parse is an anomaly
                    # (torn write / two records concatenated / truncation), not
                    # noise to skip — count it so the caller fails closed.
                    parse_failures += 1
                    continue
                msg = rec.get("message") if isinstance(rec, dict) else None
                if not isinstance(msg, dict):
                    continue
                # Fallback block: content may be a list OR a single dict, and the
                # type string casing may drift — normalize both. Recorded for the
                # report as informational context only; it is NOT a violation on
                # its own (the post-fallback tier is judged by message.model rank
                # below — see the module docstring / OI-052 ruling).
                content = msg.get("content")
                blocks = content if isinstance(content, list) else (
                    [content] if isinstance(content, dict) else [])
                for block in blocks:
                    if isinstance(block, dict) and \
                            str(block.get("type", "")).lower() == "fallback":
                        saw_fallback = True
                        if first_fallback_line is None:
                            first_fallback_line = lineno
                        # The harness fallback event carries its destination tier
                        # (`{"type":"fallback","from":...,"to":...}`). Rank `to`
                        # directly, so a fallback to a BELOW-floor tier is caught
                        # even if message.model never updated to reflect it — this
                        # closes the "trust message.model" residual. A fallback to
                        # an at/above-floor tier (e.g. opus under the opus floor)
                        # is compliant and sets no violation.
                        to_model = block.get("to")
                        if isinstance(to_model, str) and model_rank(to_model) < floor \
                                and first_violation is None:
                            first_violation = \
                                "fallback to below-floor model %r at line %d" % (to_model, lineno)
                # Model id normally lives at message.model; tolerate a top-level
                # model key too (schema drift). A present-but-non-string model is
                # coerced to a sentinel so it ranks unknown instead of crashing.
                model = msg.get("model")
                if model is None and isinstance(rec, dict):
                    model = rec.get("model")
                if model is None:
                    continue
                if not isinstance(model, str):
                    model = "<non-string:%s>" % type(model).__name__
                model_bearing += 1
                models[model] = models.get(model, 0) + 1
                if model_rank(model) < floor and first_violation is None:
                    first_violation = "below-floor model %r at line %d" % (model, lineno)
    except (OSError, UnicodeDecodeError) as e:
        return {
            "file": os.path.basename(path),
            "models": {}, "saw_fallback": False, "first_fallback_line": None,
            "first_violation": None,
            "model_bearing_lines": 0, "parse_failures": 0,
            "read_error": "%s: %s" % (type(e).__name__, e),
        }
    return {
        "file": os.path.basename(path),
        "models": models,
        "saw_fallback": saw_fallback,
        "first_fallback_line": first_fallback_line,
        "first_violation": first_violation,
        "model_bearing_lines": model_bearing,
        "parse_failures": parse_failures,
        "read_error": None,
    }


def scan_subagents_dir(subagents_dir, floor):
    """Scan every agent-*.jsonl in a subagents dir. Returns (status, rows) where
    status is 0 (all held), 1 (a floor violation), or 2 (tooling / verified-null),
    and rows is the list of per-transcript scan dicts.

    Precedence: a genuine floor violation (status 1) outranks a verified-null
    (status 2) — if we found a real below-floor run we report THAT, not 'couldn't
    look'. But a wholly-absent dir or empty file set is status 2 on its own."""
    if not subagents_dir or not os.path.isdir(subagents_dir):
        return 2, []
    # glob.escape the dir so a literal '[' / ']' in the path (glob char-class
    # metacharacters) can't silently match zero files and read as "no transcripts".
    files = sorted(
        p for p in glob.glob(os.path.join(glob.escape(subagents_dir), "agent-*.jsonl"))
        if not p.endswith(".meta.json")
    )
    if not files:
        return 2, []
    rows = [scan_transcript(p, floor) for p in files]
    # A fallback block is NOT a violation on its own (OI-052 ruling) — only a
    # below-floor message.model is. saw_fallback is carried for the report only.
    violated = any(r["first_violation"] for r in rows)
    # "Can't certify clean" — any of: a transcript with no model-bearing lines, a
    # line that failed to parse (evidence destruction), or a file we couldn't read.
    verified_null = any(
        r["model_bearing_lines"] == 0 or r.get("parse_failures", 0) > 0
        or r.get("read_error") for r in rows)
    if violated:
        return 1, rows
    if verified_null:
        return 2, rows
    return 0, rows


def resolve_subagents_dir(args):
    if args.subagents_dir:
        return args.subagents_dir
    if args.session:
        return os.path.join(
            CLAUDE, "projects", PROJECT, args.session, "subagents")
    return None


def main(argv=None):
    ap = argparse.ArgumentParser(description="ORA dispatch model-floor probe (OI-052)")
    ap.add_argument("--session", help="session id; resolves the canonical subagents dir")
    ap.add_argument("--subagents-dir", help="explicit path to a session's subagents dir")
    ap.add_argument("--floor", default="fable",
                    help="model floor name (default: fable) or full model id")
    args = ap.parse_args(argv)

    fr = floor_rank(args.floor)
    if fr is None:
        print("TOOLING ERROR: unknown floor %r" % args.floor)
        return 2

    subagents_dir = resolve_subagents_dir(args)
    if not subagents_dir:
        print("TOOLING ERROR: pass --session or --subagents-dir")
        return 2

    status, rows = scan_subagents_dir(subagents_dir, fr)

    print("dispatch model-floor probe - floor=%s dir=%s" % (args.floor, subagents_dir))
    if status == 2 and not rows:
        print("TOOLING ERROR / VERIFIED-NULL: no agent-*.jsonl transcripts found - "
              "the floor could NOT be verified. This is NOT a pass.")
        return 2
    for r in rows:
        models = ", ".join("%s=%d" % (m, c) for m, c in sorted(r["models"].items())) \
            or "(no model-bearing lines)"
        flags = []
        if r["first_violation"]:
            flags.append(r["first_violation"])
        if r.get("read_error"):
            flags.append("READ ERROR: %s" % r["read_error"])
        if r.get("parse_failures", 0) > 0:
            flags.append("%d UNPARSEABLE LINE(S) - cannot certify" % r["parse_failures"])
        if r["model_bearing_lines"] == 0 and not r.get("read_error"):
            flags.append("VERIFIED-NULL (no model-bearing lines)")
        # A fallback is NOT a failure — only a below-floor model.model is.
        bad = (r["first_violation"] or r.get("read_error")
               or r.get("parse_failures", 0) > 0 or r["model_bearing_lines"] == 0)
        mark = "FAIL" if bad else "OK"
        # Fallback shown as informational context on the row (even on an OK row).
        info = ""
        if r["saw_fallback"]:
            info = "  (info: fell back mid-run @line %s; destination tier judged by model rank above)" \
                % r.get("first_fallback_line")
        print("  [%s] %s - %s%s%s" % (
            mark, r["file"], models,
            ("  <<< " + "; ".join(flags)) if flags else "", info))

    if status == 0:
        print("RESULT: PASS - every subagent held the %s floor end-to-end "
              "(mid-run fallbacks to a compliant tier are allowed)." % args.floor)
    elif status == 1:
        print("RESULT: FAIL - a subagent ran BELOW the %s floor (its message.model "
              "dropped under the floor)." % args.floor)
    else:
        print("RESULT: TOOLING ERROR - the floor could not be verified "
              "(unreadable / unparseable / no model-bearing lines). Treated as NOT held.")
    return status


if __name__ == "__main__":
    sys.exit(main())
