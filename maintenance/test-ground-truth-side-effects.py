#!/usr/bin/env python3
"""Tests for ground-truth-side-effects.py -- Stage 1 of the ground-truth auditor."""
import importlib.util
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "ground_truth_side_effects", os.path.join(HERE, "ground-truth-side-effects.py"))
gse = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gse)

FAILURES = []


def check(label, cond, detail=""):
    if cond:
        print("  [OK] %s" % label)
    else:
        print("  [FAIL] %s %s" % (label, detail))
        FAILURES.append(label)


def _write_transcript(lines):
    fd, path = tempfile.mkstemp(suffix=".jsonl")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        for line in lines:
            f.write(json.dumps(line) + "\n")
    return path


def test_extract_side_effects_detects_email_send():
    path = _write_transcript([
        {"type": "tool_use", "name": "Bash",
         "input": {"command": "powershell scheduled-tasks/_shared/send-via-outlook.ps1 -To x"}},
    ])
    effects = gse.extract_side_effects(path)
    check("email send detected", effects.get("email_sent") == 1, effects)
    os.remove(path)


def test_extract_side_effects_detects_notion_write():
    path = _write_transcript([
        {"type": "tool_use", "name": "mcp__notion__notion-create-pages", "input": {}},
    ])
    effects = gse.extract_side_effects(path)
    check("notion write detected", effects.get("notion_write") == 1, effects)
    os.remove(path)


def test_extract_side_effects_empty_for_read_only_run():
    path = _write_transcript([
        {"type": "tool_use", "name": "Read", "input": {"file_path": "x.md"}},
        {"type": "tool_use", "name": "Grep", "input": {"pattern": "x"}},
    ])
    effects = gse.extract_side_effects(path)
    check("a read-only run has no side effects", effects == {}, effects)
    os.remove(path)


def test_extract_side_effects_missing_transcript_is_empty_not_an_exception():
    effects = gse.extract_side_effects("/does/not/exist.jsonl")
    check("missing transcript degrades to {} without raising", effects == {})


def test_has_side_effects_unjoined_run_is_never_gated_out():
    run = {"joined": False, "side_effects": {}}
    check("an unjoined run always goes to a verifier -- it cannot be proven "
          "clean (spec Sec 9 R1a)", gse.has_side_effects(run) is True)


def test_has_side_effects_joined_clean_run_is_gated():
    run = {"joined": True, "side_effects": {}}
    check("a joined run with zero side effects is gated out (cost gate)",
          gse.has_side_effects(run) is False)


def test_annotate_run_index_produces_correct_counts():
    path_email = _write_transcript([
        {"type": "tool_use", "name": "Bash", "input": {"command": "send-via-outlook.ps1"}}])
    run_index = {
        "runs": [
            {"run_id": "a", "joined": True, "transcript": path_email},
            {"run_id": "b", "joined": True, "transcript": None},
            {"run_id": "c", "joined": False, "transcript": None},
        ]
    }
    gse.annotate_run_index(run_index)
    stats = run_index["side_effect_stats"]
    check("1 verifier dispatched (email) + 1 unjoined = 2, 1 stamped clean",
          stats == {"verifiers_dispatched": 2, "stamped_clean": 1, "total": 3}, stats)
    os.remove(path_email)


if __name__ == "__main__":
    test_extract_side_effects_detects_email_send()
    test_extract_side_effects_detects_notion_write()
    test_extract_side_effects_empty_for_read_only_run()
    test_extract_side_effects_missing_transcript_is_empty_not_an_exception()
    test_has_side_effects_unjoined_run_is_never_gated_out()
    test_has_side_effects_joined_clean_run_is_gated()
    test_annotate_run_index_produces_correct_counts()
    print("-" * 72)
    if FAILURES:
        print("FAIL: %d failure(s): %s" % (len(FAILURES), ", ".join(FAILURES)))
        sys.exit(1)
    print("ALL PASS")
    sys.exit(0)
