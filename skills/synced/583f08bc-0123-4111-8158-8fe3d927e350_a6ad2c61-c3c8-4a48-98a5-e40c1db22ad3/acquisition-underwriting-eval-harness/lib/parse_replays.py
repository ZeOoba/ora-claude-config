"""Read frozen-replay subagent transcripts straight into the harness pipeline (added 2026-09-13).

Replaces the manual step where the orchestrating session copied each replay's
scores into a scratch driver script. Reads the Agent tool's on-disk transcripts
(`<project>/<session-id>/subagents/agent-<id>.jsonl` + `.meta.json`), extracts
the SINGLE fenced json block each replay is required to end with -- zero or two
or more is a FAILED replay, never a guess at which was meant (SKILL.md Step 2,
and the prompt contract at SKILL.md's "EXACTLY ONE fenced json block") -- and
attributes every replay to its golden deal by the FROZEN FACTS block in its own
prompt -- never by description or arrival order.

What a transcript CANNOT show (REFUTE I1, 2026-09-13): a differing earlier
completion notification can leave no trace on disk (09-12 Hamilton r3). The
orchestrator must still watch notifications per SKILL.md Step 1.5 and pass any
such task-id via --failed-agent-ids.

Library:
    parse_transcript(path)
    collect_replays(subagents_dir, golden_dir, agent_ids=None, failed_agent_ids=None)

CLI (from the harness root):
    python lib/parse_replays.py --subagents-dir <dir> --agent-ids ID ... \
        [--failed-agent-ids ID ...] [--record --skill-sha SHA --run-label LABEL]

Exit codes:
    0 = every golden deal has >=1 parsed replay, no replay failed.
    4 = every golden deal has >=1 parsed replay, but >=1 replay failed (degraded n;
        reported per deal). Snapshot is still recorded with --record.
    3 = a golden deal has no result or could not be aggregated, a requested
        agent-id has no transcript, a requested agent could not be attributed, or a
        --failed-agent-ids value matched no parsed transcript (the flag did not land).
        Nothing is recorded; scheduled-task state must not advance.

Repeated --agent-ids values are de-duplicated (by normcased path, so a case-differing
repeat counts once on Windows) and reported as `duplicate_agent_ids`: parsing one
transcript twice would count it as two independent samples and inflate n. A repeat also
makes the run DEGRADED (exit 4) -- an 18-id list with a duplicate is one real replay
short, so the deals' n is lower than intended even when every deal parsed.

A golden-set defect (duplicate deal_id, identical inputs, unreadable dir) exits 3 with a
JSON `error`, never a traceback: a caller reads the exit code and the JSON, not stderr.
"""

import argparse
import json
import os
import re
import sys
from numbers import Real
from pathlib import Path

_FENCED_JSON = re.compile(r"```json[ \t]*\r?\n(.*?)\r?\n?```", re.DOTALL | re.IGNORECASE)
_FROZEN_MARKER = "FROZEN FACTS:"
_BAD_STOPS = {"max_tokens", "refusal", "pause_turn", "model_context_window_exceeded"}

EXIT_CLEAN, EXIT_UNUSABLE, EXIT_DEGRADED = 0, 3, 4


class ReplayParseError(ValueError):
    """A replay response that cannot be used as a sample (Step 2 failure)."""


def extract_json_block(text):
    """Return the single fenced json object in `text`; raise on zero, several, or invalid."""
    blocks = _FENCED_JSON.findall(text or "")
    if len(blocks) != 1:
        raise ReplayParseError(
            f"expected exactly one fenced json block, found {len(blocks)} -- never "
            "guess which block was intended"
        )
    try:
        value = json.loads(blocks[0])
    except json.JSONDecodeError as exc:
        raise ReplayParseError(f"fenced json block is not valid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ReplayParseError("fenced json block is not a JSON object")
    return value


def _frozen_inputs(prompt):
    if not isinstance(prompt, str) or _FROZEN_MARKER not in prompt:
        return None
    tail = prompt.split(_FROZEN_MARKER, 1)[1]
    start = tail.find("{")
    if start < 0:
        return None
    try:
        value, _ = json.JSONDecoder().raw_decode(tail[start:])
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def _content(entry):
    return (entry.get("message") or {}).get("content")


def _blocks_of(entry):
    """Content blocks of `entry` that are dicts. A non-dict item (a bare string in a
    content list -- seen in older/variant transcript shapes) is skipped rather than
    dereferenced: `c.get` on a str raised AttributeError out of parse_transcript and
    killed the whole run instead of failing one replay (PR #65 review, F4)."""
    content = _content(entry)
    if not isinstance(content, list):
        return []
    return [c for c in content if isinstance(c, dict)]


def _text_of(entry):
    content = _content(entry)
    if isinstance(content, str):
        return content
    return "".join(c.get("text") or "" for c in _blocks_of(entry) if c.get("type") == "text")


def _is_tool_result(entry):
    return any(c.get("type") == "tool_result" for c in _blocks_of(entry))


def _requests(entries):
    """Group assistant entries by API request, in order, noting what follows each.

    Thinking/text/tool_use from one request arrive as separate entries sharing a
    requestId, and end_turn is NOT reliably stamped (REFUTE C1: a completed 09-12
    replay ends in a text entry with stop_reason null), so completion is inferred
    from structure rather than the stop_reason field.
    """
    reqs, by_id, run = [], {}, 0
    for i, e in enumerate(entries):
        if e.get("type") != "assistant":
            # A non-assistant entry ends the current un-keyed run of assistant entries.
            run += 1
        if e.get("type") == "assistant":
            # No requestId: group CONSECUTIVE assistant entries as one response. Keying each
            # entry separately split one response's text, so a final answer whose json block
            # sat in an earlier entry parsed as 0 blocks and the replay was scored failed
            # (PR #65 review, F5).
            rid = e.get("requestId") or f"_run{run}"
            if rid not in by_id:
                by_id[rid] = {"text": "", "tool_use": False, "stops": set(), "last": i}
                reqs.append(by_id[rid])
            r = by_id[rid]
            r["text"] += _text_of(e)
            r["last"] = i
            if any(c.get("type") == "tool_use" for c in _blocks_of(e)):
                r["tool_use"] = True
            stop = (e.get("message") or {}).get("stop_reason")
            if stop:
                r["stops"].add(stop)
    for r in reqs:
        nxt = next((e for e in entries[r["last"] + 1:] if e.get("type") in ("user", "assistant")), None)
        if nxt is None:
            r["followed_by"] = "eof"
        elif nxt.get("type") == "user":
            r["followed_by"] = "tool_result" if _is_tool_result(nxt) else "user"
        else:
            r["followed_by"] = "assistant"
    return reqs


def parse_transcript(path):
    """Parse one agent transcript into {agent_id, description, inputs, status, result, error, completion_count}."""
    path = Path(path)
    agent_id = path.stem[len("agent-"):] if path.stem.startswith("agent-") else path.stem
    out = {"agent_id": agent_id, "description": None, "inputs": None,
           "status": "failed", "result": None, "error": None, "completion_count": 0}

    meta_path = path.with_name(path.stem + ".meta.json")
    try:
        if meta_path.exists():
            out["description"] = json.loads(meta_path.read_text(encoding="utf-8")).get("description")
        entries = []
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if line.strip():
                entries.append(json.loads(line))
    except (OSError, json.JSONDecodeError) as exc:
        out["error"] = f"unreadable transcript: {exc}"
        return out

    try:
        return _parse_entries(entries, out)
    except Exception as exc:  # noqa: BLE001 -- one odd transcript fails ONE replay
        # Before this, any unexpected entry shape raised out of collect_replays and
        # aborted an 18-replay run with a traceback -- neither of the documented exit
        # codes, and the 17 good replays were lost too (PR #65 review, F4).
        out["error"] = f"malformed transcript ({type(exc).__name__}: {exc})"
        return out


def _parse_entries(entries, out):
    out["inputs"] = _frozen_inputs(next((_text_of(e) for e in entries if e.get("type") == "user"), None))

    reqs = _requests(entries)
    # A completion: a request that produced text, called no tool, and was followed by
    # end of transcript or by a non-tool_result user message (a resume).
    completions = [r for r in reqs
                   if r["text"].strip() and not r["tool_use"] and "tool_use" not in r["stops"]
                   and r["followed_by"] in ("eof", "user")]
    out["completion_count"] = len(completions)
    if not completions:
        last = reqs[-1] if reqs else None
        bad = sorted(last["stops"] & _BAD_STOPS) if last else []
        if bad:
            out["error"] = f"response stopped with stop_reason {bad[0]}"
        elif last and (last["tool_use"] or "tool_use" in last["stops"]):
            out["error"] = "transcript ends mid-tool-call (agent incomplete)"
        else:
            out["error"] = "no completed response"
        return out

    bad = sorted(set().union(*(r["stops"] for r in completions)) & _BAD_STOPS)
    if bad:
        out["error"] = f"response stopped with stop_reason {bad[0]}"
        return out
    try:
        parsed = [extract_json_block(r["text"]) for r in completions]
    except ReplayParseError as exc:
        out["error"] = str(exc)
        return out
    if any(p != parsed[0] for p in parsed[1:]):
        out["error"] = (f"{len(parsed)} completions from one agent with json blocks that differ "
                        "-- failed replay (SKILL.md Step 1.5)")
        return out
    combined = parsed[0].get("combined")
    if not isinstance(combined, Real) or isinstance(combined, bool):
        out["error"] = f"'combined' is not a number ({combined!r})"
        return out
    out["status"], out["result"] = "ok", parsed[0]
    return out


def collect_replays(subagents_dir, golden_dir, agent_ids=None, failed_agent_ids=None):
    """Group parsed replays by golden deal.

    Returns {"deals": {deal_id: {"golden_path", "replays", "failures", "agent_ids"}},
             "unattributed": [...], "missing_agent_ids": [...]}.
    Every golden deal appears, even with zero replays.

    Raises:
        ValueError: if two golden files carry identical inputs (attribution would be ambiguous).
    """
    subagents_dir, golden_dir = Path(subagents_dir), Path(golden_dir)
    flagged_order = list(dict.fromkeys(failed_agent_ids or ()))
    failed_agent_ids = set(flagged_order)
    goldens = {}
    for g in sorted(golden_dir.glob("*.json")):
        data = json.loads(g.read_text(encoding="utf-8"))
        deal_id = data.get("deal_id") or g.stem
        # deals is keyed by deal_id, so a second file carrying the same id silently
        # overwrote the first and dropped a whole deal out of the gate (PR #65 review, F3).
        if deal_id in goldens:
            raise ValueError(
                f"golden deal_id {deal_id!r} appears in two files "
                f"({goldens[deal_id][1].name} and {g.name}) -- one would silently "
                "replace the other and its deal would vanish from the run")
        for other, (inputs, _) in goldens.items():
            if inputs == data.get("inputs"):
                raise ValueError(f"golden deals {other!r} and {deal_id!r} have identical inputs")
        goldens[deal_id] = (data.get("inputs"), g)

    duplicate_agent_ids = []
    if agent_ids is None:
        paths, missing = sorted(subagents_dir.glob("agent-*.jsonl")), []
    else:
        # De-duplicate: a hand-pasted id list that repeats an id parsed the same transcript
        # twice and counted it as two independent samples, inflating n (PR #65 review, F2).
        # Key on the NORMCASED PATH, not the id string: Path.exists() is case-insensitive
        # on Windows, so "A1B2C3" resolves to agent-a1b2c3.jsonl and a case-differing repeat
        # slipped through an id-keyed check and was counted twice (REFUTE pass, R1).
        seen_keys, paths, missing = set(), [], []
        for aid in agent_ids:
            p = subagents_dir / f"agent-{aid}.jsonl"
            key = os.path.normcase(str(p))
            if key in seen_keys:
                if aid not in duplicate_agent_ids:
                    duplicate_agent_ids.append(aid)
                continue
            seen_keys.add(key)
            if p.exists():
                paths.append(p)
            else:
                missing.append(aid)

    deals = {d: {"golden_path": str(g), "replays": [], "failures": [], "agent_ids": []}
             for d, (_, g) in goldens.items()}
    unattributed, seen_agent_ids = [], set()
    for p in paths:
        t = parse_transcript(p)
        seen_agent_ids.add(t["agent_id"])
        deal = next((d for d, (inputs, _) in goldens.items()
                     if t["inputs"] is not None and inputs == t["inputs"]), None)
        if deal is None:
            unattributed.append({"agent_id": t["agent_id"], "description": t["description"],
                                 "error": t["error"]})
            continue
        bucket = deals[deal]
        bucket["agent_ids"].append(t["agent_id"])
        if t["agent_id"] in failed_agent_ids:
            prior = t["error"]
            t["status"] = "failed"
            t["error"] = ("orchestrator-flagged: completion notifications differed "
                          "(SKILL.md Step 1.5)")
            # Keep the transcript's own diagnosis: overwriting it hid a DIFFERENT defect
            # (e.g. an agent that never finished its tool call) behind the flag, and the
            # transcript may be gone before anyone notices (PR #65 review, F6).
            if prior:
                t["error"] += f"; transcript also failed: {prior}"
        if t["status"] == "ok":
            bucket["replays"].append(t["result"])
        else:
            bucket["failures"].append({"agent_id": t["agent_id"], "description": t["description"],
                                       "completion_count": t["completion_count"], "error": t["error"]})
    # A flagged id that matched no parsed transcript is a SILENT no-op otherwise: the
    # replay the orchestrator rejected stays in the sample and the run still exits CLEAN
    # (PR #65 review, F1). Report it so main can refuse the run.
    # Compare case-insensitively for the same reason the de-dup key is normcased (R1):
    # a flagged id differing only in case names the same transcript on this filesystem.
    seen_folded = {os.path.normcase(a) for a in seen_agent_ids}
    unknown_failed = [a for a in flagged_order if os.path.normcase(a) not in seen_folded]
    return {"deals": deals, "unattributed": unattributed, "missing_agent_ids": missing,
            "duplicate_agent_ids": duplicate_agent_ids,
            "unknown_failed_agent_ids": unknown_failed}


def main(argv=None):
    here = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--subagents-dir", required=True)
    ap.add_argument("--golden-dir", default=str(here.parent / "golden_set"))
    ap.add_argument("--agent-ids", nargs="+")
    ap.add_argument("--failed-agent-ids", nargs="+", default=[])
    ap.add_argument("--record", action="store_true", help="write the runs/ snapshot via record_run")
    ap.add_argument("--run-dir", default=str(here.parent / "runs"))
    ap.add_argument("--skill-sha")
    ap.add_argument("--run-label", default="scheduled-poll")
    args = ap.parse_args(argv)

    sys.path.insert(0, str(here))
    from aggregate_replays import aggregate_replays
    from diff_verdict import diff_verdict
    from record_run import record_run

    try:
        collected = collect_replays(args.subagents_dir, args.golden_dir, args.agent_ids,
                                    args.failed_agent_ids)
    except (ValueError, OSError) as exc:
        # A golden-set defect (duplicate deal_id / identical inputs) or an unreadable
        # golden dir used to escape as a traceback: rc=1 with no JSON, outside the
        # documented 0/3/4 contract a caller reads (REFUTE pass, R5).
        report = {"error": f"golden set unusable: {exc}", "exit_code": EXIT_UNUSABLE}
        print(json.dumps(report, indent=2, default=str))
        return EXIT_UNUSABLE
    report = {"deals": {}, "unattributed": collected["unattributed"],
              "missing_agent_ids": collected["missing_agent_ids"],
              "duplicate_agent_ids": collected["duplicate_agent_ids"],
              "unknown_failed_agent_ids": collected["unknown_failed_agent_ids"]}
    unusable = bool(collected["missing_agent_ids"]) or not collected["deals"]
    # A --failed-agent-ids value nothing matched means the orchestrator's Step 1.5 flag
    # did not land. Refuse rather than record a mean that may include the rejected replay.
    unusable = unusable or bool(collected["unknown_failed_agent_ids"])
    if args.agent_ids is not None and collected["unattributed"]:
        unusable = True
    # A repeated id means the requested list is one real replay short, so the run is
    # degraded even when every deal parsed: n is lower than the operator intended
    # (REFUTE pass, R2). Reported, snapshot still recorded -- that is what exit 4 means.
    degraded = bool(collected["duplicate_agent_ids"])
    results = []
    for deal_id, bucket in collected["deals"].items():
        entry = {"n": len(bucket["replays"]), "failures": bucket["failures"], "agent_ids": bucket["agent_ids"]}
        degraded = degraded or bool(bucket["failures"])
        if not bucket["replays"]:
            entry["status"] = "NO_RESULT"
            unusable = True
        else:
            try:
                golden = json.loads(Path(bucket["golden_path"]).read_text(encoding="utf-8"))
                diff = diff_verdict(golden, aggregate_replays(bucket["replays"]))
            except (ValueError, TypeError, KeyError) as exc:
                entry["status"], entry["error"] = "ERROR", f"aggregate/diff failed: {exc}"
                unusable = True
            else:
                results.append(diff)
                entry.update({k: diff.get(k) for k in (
                    "status", "scored", "combined_golden", "combined_observed", "combined_delta", "floor_drift")})
                entry["combined_range"] = (diff.get("aggregate") or {}).get("combined_range")
        report["deals"][deal_id] = entry

    code = EXIT_UNUSABLE if unusable else (EXIT_DEGRADED if degraded else EXIT_CLEAN)
    if args.record and code != EXIT_UNUSABLE:
        report["recorded"] = record_run(results, run_dir=args.run_dir,
                                        skill_sha=args.skill_sha, run_label=args.run_label)
    report["exit_code"] = code
    print(json.dumps(report, indent=2, default=str))
    return code


if __name__ == "__main__":
    sys.exit(main())
