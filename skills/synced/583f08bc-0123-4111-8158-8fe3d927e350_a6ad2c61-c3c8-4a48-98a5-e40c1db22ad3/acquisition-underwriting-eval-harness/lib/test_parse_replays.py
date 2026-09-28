"""Tests for lib/parse_replays.py — transcript -> parsed replay extraction (added 2026-09-13).

Written FIRST (TDD), unittest style. Run from the harness root:

    python -m unittest discover -s lib -p 'test_*.py' -v
"""

import json
import tempfile
import unittest
from pathlib import Path

from parse_replays import (
    ReplayParseError,
    collect_replays,
    extract_json_block,
    parse_transcript,
)

FENCE = "`" * 3
NL = chr(10)

GOLDEN_INPUTS = {"address": "1 Test Rd, Columbus, OH", "asking_price": 1000000}
OTHER_INPUTS = {"address": "2 Other St, Cincinnati, OH", "asking_price": 2000000}


def _block(payload):
    return f"{FENCE}json\n{json.dumps(payload)}\n{FENCE}"


def _result(combined, **kw):
    r = {"combined": combined, "quality": combined, "economics": 0.0,
         "category_breakdown": {"Basis": 0.0, "Product & Physical": combined}}
    r.update(kw)
    return r


def _prompt(inputs):
    return (
        "You are running a FROZEN REPLAY of the acquisition-underwriting skill's SCREEN mode\n\n"
        "FROZEN FACTS:\n" + json.dumps(inputs, indent=1) + "\n\n"
        "Compute Quality, Economics, Combined ...\n" + FENCE + "json\n{\"combined\": <float>}\n" + FENCE
    )


def _assistant(text, request_id, stop_reason=None, kind="text"):
    content = [{"type": "text", "text": text}] if kind == "text" else [{"type": kind}]
    return {"type": "assistant", "requestId": request_id,
            "message": {"role": "assistant", "content": content, "stop_reason": stop_reason}}


def _write_agent(dirpath, agent_id, prompt, entries, description="Replay X r1"):
    lines = [{"type": "user", "message": {"role": "user", "content": prompt}}] + entries
    p = Path(dirpath) / f"agent-{agent_id}.jsonl"
    p.write_text("\n".join(json.dumps(x) for x in lines) + "\n", encoding="utf-8")
    (Path(dirpath) / f"agent-{agent_id}.meta.json").write_text(
        json.dumps({"description": description, "model": "fable"}), encoding="utf-8")
    return p


def _write_golden(dirpath, deal_id, inputs):
    (Path(dirpath) / f"{deal_id}.json").write_text(
        json.dumps({"deal_id": deal_id, "inputs": inputs, "confidence": "HIGH",
                    "diff_policy": {"tolerance_combined_pts": 5.0}, "golden": {"combined": 10.0}}),
        encoding="utf-8")


class TestExtractJsonBlock(unittest.TestCase):
    def test_single_block_parses(self):
        self.assertEqual(extract_json_block("prose\n" + _block({"combined": 12.0}))["combined"], 12.0)

    def test_zero_blocks_fails(self):
        with self.assertRaises(ReplayParseError):
            extract_json_block("no json here")

    def test_multiple_blocks_fail_never_guess(self):
        with self.assertRaises(ReplayParseError):
            extract_json_block(_block({"combined": 1.0}) + "\n" + _block({"combined": 2.0}))

    def test_invalid_json_fails(self):
        with self.assertRaises(ReplayParseError):
            extract_json_block(f"{FENCE}json\n{{\"combined\": 1.0,}}\n{FENCE}")

    def test_non_object_fails(self):
        with self.assertRaises(ReplayParseError):
            extract_json_block(f"{FENCE}json\n[1, 2]\n{FENCE}")


class TestParseTranscript(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def test_final_text_is_joined_across_entries_of_the_end_turn_request(self):
        p = _write_agent(self.d, "a1", _prompt(GOLDEN_INPUTS), [
            _assistant("interim narration, no block", "req1"),
            _assistant("", "req1", "tool_use", kind="tool_use"),
            _assistant("", "req2", kind="thinking"),
            _assistant("Verdict prose part 1\n", "req2"),
            _assistant(_block(_result(14.0)), "req2", "end_turn"),
        ])
        t = parse_transcript(p)
        self.assertEqual(t["status"], "ok")
        self.assertEqual(t["result"]["combined"], 14.0)
        self.assertEqual(t["inputs"], GOLDEN_INPUTS)
        self.assertEqual(t["description"], "Replay X r1")
        self.assertEqual(t["completion_count"], 1)

    def test_json_in_interim_non_final_text_is_ignored(self):
        p = _write_agent(self.d, "a2", _prompt(GOLDEN_INPUTS), [
            _assistant("draft " + _block(_result(99.0)), "req1", "tool_use"),
            _assistant(_block(_result(14.0)), "req2", "end_turn"),
        ])
        self.assertEqual(parse_transcript(p)["result"]["combined"], 14.0)

    def test_no_completion_is_a_failure(self):
        p = _write_agent(self.d, "a3", _prompt(GOLDEN_INPUTS), [
            _assistant("", "req1", "tool_use", kind="tool_use"),
        ])
        t = parse_transcript(p)
        self.assertEqual(t["status"], "failed")
        self.assertIsNone(t["result"])

    def test_two_blocks_in_final_response_is_a_failure(self):
        p = _write_agent(self.d, "a4", _prompt(GOLDEN_INPUTS), [
            _assistant(_block(_result(1.0)) + _block(_result(2.0)), "req1", "end_turn"),
        ])
        self.assertEqual(parse_transcript(p)["status"], "failed")

    def test_two_completions_identical_blocks_accepted_once(self):
        p = _write_agent(self.d, "a5", _prompt(GOLDEN_INPUTS), [
            _assistant("first " + _block(_result(15.0)), "req1", "end_turn"),
            {"type": "user", "message": {"role": "user", "content": "resume"}},
            _assistant("again " + _block(_result(15.0)), "req2", "end_turn"),
        ])
        t = parse_transcript(p)
        self.assertEqual(t["status"], "ok")
        self.assertEqual(t["completion_count"], 2)
        self.assertEqual(t["result"]["combined"], 15.0)

    def test_two_completions_differing_blocks_is_a_failure(self):
        # Data-quality finding 5: Hamilton r3, 2026-09-12 (15.0 then 11.0).
        p = _write_agent(self.d, "a6", _prompt(GOLDEN_INPUTS), [
            _assistant(_block(_result(15.0)), "req1", "end_turn"),
            {"type": "user", "message": {"role": "user", "content": "resume"}},
            _assistant(_block(_result(11.0)), "req2", "end_turn"),
        ])
        t = parse_transcript(p)
        self.assertEqual(t["status"], "failed")
        self.assertIn("differ", t["error"])

    def test_final_text_without_end_turn_stamp_is_a_completion(self):
        # REFUTE C1 (2026-09-13): real 09-12 transcript agent-ad3b51b8... ends in a text
        # entry with stop_reason null and no end_turn anywhere, yet it completed.
        p = _write_agent(self.d, "c1", _prompt(GOLDEN_INPUTS), [
            _assistant("", "req1", "tool_use", kind="tool_use"),
            {"type": "user", "message": {"role": "user", "content": [{"type": "tool_result"}]}},
            _assistant("", "req2", kind="thinking"),
            _assistant(_block(_result(55.0)), "req2"),
        ])
        t = parse_transcript(p)
        self.assertEqual(t["status"], "ok")
        self.assertEqual(t["result"]["combined"], 55.0)
        self.assertEqual(t["completion_count"], 1)

    def test_thinking_and_text_both_stamped_end_turn_count_as_one(self):
        # REFUTE I2: one request, two entries both carrying end_turn.
        p = _write_agent(self.d, "c2", _prompt(GOLDEN_INPUTS), [
            _assistant("", "req1", "end_turn", kind="thinking"),
            _assistant(_block(_result(12.0)), "req1", "end_turn"),
        ])
        self.assertEqual(parse_transcript(p)["completion_count"], 1)

    def test_last_request_pending_tool_use_is_incomplete(self):
        p = _write_agent(self.d, "c3", _prompt(GOLDEN_INPUTS), [
            _assistant("checking " + _block(_result(3.0)), "req1"),
            _assistant("", "req1", "tool_use", kind="tool_use"),
        ])
        self.assertEqual(parse_transcript(p)["status"], "failed")

    def test_max_tokens_stop_is_a_named_failure(self):
        p = _write_agent(self.d, "c4", _prompt(GOLDEN_INPUTS), [
            _assistant("truncated " + FENCE + "json\n{\"combined\": 1", "req1", "max_tokens"),
        ])
        t = parse_transcript(p)
        self.assertEqual(t["status"], "failed")
        self.assertIn("max_tokens", t["error"])

    def test_resumed_agent_with_differing_answer_is_a_failure(self):
        # A resume appears as a plain (non tool_result) user message after a completed response.
        p = _write_agent(self.d, "c5", _prompt(GOLDEN_INPUTS), [
            _assistant(_block(_result(15.0)), "req1"),
            {"type": "user", "message": {"role": "user", "content": "please double-check"}},
            _assistant(_block(_result(11.0)), "req2", "end_turn"),
        ])
        t = parse_transcript(p)
        self.assertEqual(t["completion_count"], 2)
        self.assertEqual(t["status"], "failed")

    def test_non_numeric_combined_is_a_failure_not_a_crash(self):
        p = _write_agent(self.d, "c6", _prompt(GOLDEN_INPUTS), [
            _assistant(_block(_result(None)), "req1", "end_turn"),
        ])
        t = parse_transcript(p)
        self.assertEqual(t["status"], "failed")
        self.assertIn("combined", t["error"])

    def test_truncated_transcript_line_is_a_failure_not_a_crash(self):
        p = _write_agent(self.d, "c7", _prompt(GOLDEN_INPUTS), [
            _assistant(_block(_result(12.0)), "req1", "end_turn"),
        ])
        p.write_text(p.read_text(encoding="utf-8") + '{"type": "assist', encoding="utf-8")
        self.assertEqual(parse_transcript(p)["status"], "failed")

    def test_uppercase_json_fence_is_accepted(self):
        text = f"{FENCE}JSON\n{json.dumps(_result(9.0))}\n{FENCE}"
        self.assertEqual(extract_json_block(text)["combined"], 9.0)

    def test_prompt_without_frozen_facts_has_no_inputs(self):
        p = _write_agent(self.d, "a7", "some unrelated agent task", [
            _assistant("done", "req1", "end_turn"),
        ])
        self.assertIsNone(parse_transcript(p)["inputs"])


class TestCollectReplays(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.sub = Path(self.tmp.name) / "subagents"
        self.gold = Path(self.tmp.name) / "golden_set"
        self.sub.mkdir()
        self.gold.mkdir()
        _write_golden(self.gold, "deal-a", GOLDEN_INPUTS)
        _write_golden(self.gold, "deal-b", OTHER_INPUTS)

    def tearDown(self):
        self.tmp.cleanup()

    def test_attributes_by_frozen_inputs_not_description(self):
        _write_agent(self.sub, "x1", _prompt(GOLDEN_INPUTS),
                     [_assistant(_block(_result(10.0)), "r", "end_turn")], description="Replay deal-b r1")
        _write_agent(self.sub, "x2", _prompt(OTHER_INPUTS),
                     [_assistant(_block(_result(20.0)), "r", "end_turn")])
        out = collect_replays(self.sub, self.gold)
        self.assertEqual([r["combined"] for r in out["deals"]["deal-a"]["replays"]], [10.0])
        self.assertEqual([r["combined"] for r in out["deals"]["deal-b"]["replays"]], [20.0])

    def test_failures_are_reported_per_deal_never_dropped(self):
        _write_agent(self.sub, "ok1", _prompt(GOLDEN_INPUTS),
                     [_assistant(_block(_result(10.0)), "r", "end_turn")])
        _write_agent(self.sub, "bad1", _prompt(GOLDEN_INPUTS),
                     [_assistant("no block", "r", "end_turn")])
        deal = collect_replays(self.sub, self.gold)["deals"]["deal-a"]
        self.assertEqual(len(deal["replays"]), 1)
        self.assertEqual([f["agent_id"] for f in deal["failures"]], ["bad1"])

    def test_non_replay_agents_are_listed_as_unattributed(self):
        _write_agent(self.sub, "other", "unrelated task", [_assistant("done", "r", "end_turn")])
        _write_agent(self.sub, "stray", _prompt({"address": "9 Unknown"}),
                     [_assistant(_block(_result(5.0)), "r", "end_turn")])
        out = collect_replays(self.sub, self.gold)
        self.assertEqual(sorted(u["agent_id"] for u in out["unattributed"]), ["other", "stray"])
        self.assertEqual(out["deals"]["deal-a"]["replays"], [])

    def test_agent_ids_filter_limits_to_this_run(self):
        _write_agent(self.sub, "old", _prompt(GOLDEN_INPUTS),
                     [_assistant(_block(_result(1.0)), "r", "end_turn")])
        _write_agent(self.sub, "new", _prompt(GOLDEN_INPUTS),
                     [_assistant(_block(_result(2.0)), "r", "end_turn")])
        out = collect_replays(self.sub, self.gold, agent_ids=["new"])
        self.assertEqual([r["combined"] for r in out["deals"]["deal-a"]["replays"]], [2.0])

    def test_requested_agent_id_with_no_transcript_is_reported(self):
        out = collect_replays(self.sub, self.gold, agent_ids=["missing"])
        self.assertEqual([m for m in out["missing_agent_ids"]], ["missing"])

    def test_every_golden_deal_appears_even_with_zero_replays(self):
        out = collect_replays(self.sub, self.gold)
        self.assertEqual(sorted(out["deals"]), ["deal-a", "deal-b"])
        self.assertEqual(out["deals"]["deal-b"]["replays"], [])

    def test_orchestrator_flagged_agent_is_a_failure(self):
        # REFUTE I1: a differing first notification can leave no transcript trace, so the
        # orchestrator's own notification log must be able to fail a replay.
        _write_agent(self.sub, "dup", _prompt(GOLDEN_INPUTS),
                     [_assistant(_block(_result(11.0)), "r", "end_turn")])
        deal = collect_replays(self.sub, self.gold, failed_agent_ids=["dup"])["deals"]["deal-a"]
        self.assertEqual(deal["replays"], [])
        self.assertEqual(deal["failures"][0]["agent_id"], "dup")

    def test_duplicate_golden_inputs_raise(self):
        _write_golden(self.gold, "deal-c", GOLDEN_INPUTS)
        with self.assertRaises(ValueError):
            collect_replays(self.sub, self.gold)



class TestReviewFindings(unittest.TestCase):
    """Regression tests for the 7 findings of the 2026-09-17 PR #65 review.

    Every one of the first three corrupts `n` or the deal set with NO signal, which is
    the one thing this gate exists to get right (see aggregate_replays' own docstring:
    the whole point is a mean over independent samples).
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.sub, self.gold = root / "subagents", root / "golden_set"
        self.sub.mkdir()
        self.gold.mkdir()
        _write_golden(self.gold, "deal-a", GOLDEN_INPUTS)
        _write_golden(self.gold, "deal-b", OTHER_INPUTS)

    def tearDown(self):
        self.tmp.cleanup()

    # F1 -- a Step 1.5 flag that matches nothing must not silently no-op.
    def test_unknown_failed_agent_id_is_reported(self):
        _write_agent(self.sub, "a1", _prompt(GOLDEN_INPUTS),
                     [_assistant(_block(_result(10.0)), "r", "end_turn")])
        out = collect_replays(self.sub, self.gold, agent_ids=["a1"],
                              failed_agent_ids=["a1", "typo-id"])
        self.assertEqual(out["unknown_failed_agent_ids"], ["typo-id"])

    def test_unknown_failed_agent_id_makes_the_run_unusable(self):
        _write_agent(self.sub, "a1", _prompt(GOLDEN_INPUTS),
                     [_assistant(_block(_result(10.0)), "r", "end_turn")])
        _write_agent(self.sub, "b1", _prompt(OTHER_INPUTS),
                     [_assistant(_block(_result(10.0)), "r", "end_turn")])
        import contextlib
        import io as _io
        from parse_replays import main
        buf = _io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = main(["--subagents-dir", str(self.sub), "--golden-dir", str(self.gold),
                         "--agent-ids", "a1", "b1", "--failed-agent-ids", "typo-id"])
        self.assertEqual(code, 3)
        self.assertEqual(json.loads(buf.getvalue())["unknown_failed_agent_ids"], ["typo-id"])

    # F2 -- a repeated id must not become a second independent sample.
    def test_duplicate_agent_ids_are_counted_once(self):
        _write_agent(self.sub, "dup1", _prompt(GOLDEN_INPUTS),
                     [_assistant(_block(_result(10.0)), "r", "end_turn")])
        out = collect_replays(self.sub, self.gold, agent_ids=["dup1", "dup1"])
        self.assertEqual(len(out["deals"]["deal-a"]["replays"]), 1)
        self.assertEqual(out["deals"]["deal-a"]["agent_ids"], ["dup1"])
        self.assertEqual(out["duplicate_agent_ids"], ["dup1"])

    # F3 -- two goldens sharing a deal_id silently dropped one deal from the gate.
    def test_duplicate_golden_deal_id_raises(self):
        (self.gold / "deal-a-copy.json").write_text(
            json.dumps({"deal_id": "deal-a", "inputs": {"address": "3 Third Ave"},
                        "confidence": "HIGH", "diff_policy": {"tolerance_combined_pts": 5.0},
                        "golden": {"combined": 10.0}}), encoding="utf-8")
        with self.assertRaises(ValueError) as ctx:
            collect_replays(self.sub, self.gold)
        self.assertIn("deal-a", str(ctx.exception))

    # F4 -- one malformed transcript must degrade ONE replay, not kill the run.
    def test_malformed_entry_shape_fails_only_that_replay(self):
        good = _prompt(GOLDEN_INPUTS)
        _write_agent(self.sub, "good1", good,
                     [_assistant(_block(_result(10.0)), "r", "end_turn")])
        # content list holding a bare string instead of a block dict
        bad = {"type": "assistant", "requestId": "r",
               "message": {"role": "assistant", "content": ["oops"], "stop_reason": "end_turn"}}
        _write_agent(self.sub, "bad1", good, [bad])
        out = collect_replays(self.sub, self.gold)
        deal = out["deals"]["deal-a"]
        self.assertEqual([r["combined"] for r in deal["replays"]], [10.0])
        self.assertEqual([f["agent_id"] for f in deal["failures"]], ["bad1"])

    # F5 -- entries without requestId belong to ONE response, not one each.
    def test_response_split_across_entries_without_request_id_still_parses(self):
        split = [
            {"type": "assistant", "message": {"role": "assistant", "stop_reason": None,
             "content": [{"type": "text", "text": "Scores:" + NL + _block(_result(12.0))}]}},
            {"type": "assistant", "message": {"role": "assistant", "stop_reason": None,
             "content": [{"type": "text", "text": NL + "Done."}]}},
        ]
        path = _write_agent(self.sub, "nosplit", _prompt(GOLDEN_INPUTS), split)
        t = parse_transcript(path)
        self.assertEqual(t["status"], "ok", t["error"])
        self.assertEqual(t["completion_count"], 1)
        self.assertEqual(t["result"]["combined"], 12.0)

    # R1 -- id de-duplication must survive a case-differing repeat: Path.exists() is
    # case-insensitive on Windows, so "A1B2C3" resolves to agent-a1b2c3.jsonl and the
    # same transcript was counted twice with duplicate_agent_ids empty.
    def test_case_differing_duplicate_agent_id_is_still_one_sample(self):
        _write_agent(self.sub, "a1b2c3", _prompt(GOLDEN_INPUTS),
                     [_assistant(_block(_result(14.0)), "r", "end_turn")])
        out = collect_replays(self.sub, self.gold, agent_ids=["a1b2c3", "A1B2C3"])
        self.assertEqual([r["combined"] for r in out["deals"]["deal-a"]["replays"]], [14.0])
        self.assertEqual(out["duplicate_agent_ids"], ["A1B2C3"])

    # R2 -- a duplicated id means one real replay is missing from the requested list, so
    # the run is degraded, not clean.
    def test_duplicate_agent_id_degrades_the_run(self):
        _write_agent(self.sub, "a1", _prompt(GOLDEN_INPUTS),
                     [_assistant(_block(_result(10.0)), "r", "end_turn")])
        _write_agent(self.sub, "b1", _prompt(OTHER_INPUTS),
                     [_assistant(_block(_result(10.0)), "r", "end_turn")])
        import contextlib
        import io as _io
        from parse_replays import main
        buf = _io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = main(["--subagents-dir", str(self.sub), "--golden-dir", str(self.gold),
                         "--agent-ids", "a1", "a1", "b1"])
        self.assertEqual(code, 4)
        self.assertEqual(json.loads(buf.getvalue())["duplicate_agent_ids"], ["a1"])

    # R3 -- a stray non-dict content block must be SKIPPED (the F4 claim), not merely
    # caught: the tool_use scan still dereferenced raw list items.
    def test_stray_string_content_block_is_skipped_and_the_replay_parses(self):
        entry = {"type": "assistant", "requestId": "r",
                 "message": {"role": "assistant", "stop_reason": "end_turn",
                             "content": ["oops", {"type": "text", "text": _block(_result(13.0))}]}}
        path = _write_agent(self.sub, "stray", _prompt(GOLDEN_INPUTS), [entry])
        t = parse_transcript(path)
        self.assertEqual(t["status"], "ok", t["error"])
        self.assertEqual(t["result"]["combined"], 13.0)

    # R4 -- a golden-set error must exit on the documented contract, not a traceback.
    def test_golden_set_error_exits_unusable_with_json(self):
        (self.gold / "deal-a-copy.json").write_text(
            json.dumps({"deal_id": "deal-a", "inputs": {"address": "3 Third Ave"},
                        "confidence": "HIGH", "diff_policy": {"tolerance_combined_pts": 5.0},
                        "golden": {"combined": 10.0}}), encoding="utf-8")
        import contextlib
        import io as _io
        from parse_replays import main
        buf = _io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = main(["--subagents-dir", str(self.sub), "--golden-dir", str(self.gold)])
        self.assertEqual(code, 3)
        self.assertIn("deal-a", json.loads(buf.getvalue())["error"])

    # F6 -- flagging must not erase the transcript's own diagnosis.
    def test_orchestrator_flag_preserves_the_original_error(self):
        _write_agent(self.sub, "halfdone", _prompt(GOLDEN_INPUTS),
                     [_assistant("thinking", "r", "tool_use", kind="tool_use")])
        deal = collect_replays(self.sub, self.gold, failed_agent_ids=["halfdone"])["deals"]["deal-a"]
        err = deal["failures"][0]["error"]
        self.assertIn("orchestrator-flagged", err)
        self.assertIn("mid-tool-call", err)


class TestMainExitCodes(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.sub, self.gold, self.runs = root / "subagents", root / "golden_set", root / "runs"
        self.sub.mkdir()
        self.gold.mkdir()
        _write_golden(self.gold, "deal-a", GOLDEN_INPUTS)
        _write_golden(self.gold, "deal-b", OTHER_INPUTS)

    def tearDown(self):
        self.tmp.cleanup()

    def _main(self, *extra):
        import contextlib
        import io
        from parse_replays import main
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = main(["--subagents-dir", str(self.sub), "--golden-dir", str(self.gold),
                         "--run-dir", str(self.runs), *extra])
        return code, json.loads(buf.getvalue())

    def _ok(self, aid, inputs, combined):
        _write_agent(self.sub, aid, _prompt(inputs), [_assistant(_block(_result(combined)), "r", "end_turn")])

    def test_clean_run_exits_0(self):
        self._ok("a1", GOLDEN_INPUTS, 10.0)
        self._ok("b1", OTHER_INPUTS, 10.0)
        code, report = self._main()
        self.assertEqual(code, 0)
        self.assertEqual(report["deals"]["deal-a"]["status"], "PASS")

    def test_every_deal_resolved_but_a_replay_failed_exits_4(self):
        self._ok("a1", GOLDEN_INPUTS, 10.0)
        self._ok("b1", OTHER_INPUTS, 10.0)
        _write_agent(self.sub, "b2", _prompt(OTHER_INPUTS), [_assistant("no block", "r", "end_turn")])
        self.assertEqual(self._main()[0], 4)

    def test_deal_with_no_result_exits_3_and_does_not_record(self):
        self._ok("a1", GOLDEN_INPUTS, 10.0)
        code, report = self._main("--record", "--skill-sha", "abc")
        self.assertEqual(code, 3)
        self.assertNotIn("recorded", report)
        self.assertFalse(self.runs.exists())

    def test_unattributed_requested_agent_exits_3(self):
        # REFUTE I4
        self._ok("a1", GOLDEN_INPUTS, 10.0)
        self._ok("b1", OTHER_INPUTS, 10.0)
        self._ok("stray", {"address": "9 Unknown"}, 10.0)
        self.assertEqual(self._main("--agent-ids", "a1", "b1", "stray")[0], 3)

    def test_aggregate_error_is_reported_not_raised(self):
        # REFUTE I3: breakdown carrying both display and snake_case keys makes aggregate raise.
        _write_agent(self.sub, "a1", _prompt(GOLDEN_INPUTS), [_assistant(_block(
            _result(10.0, category_breakdown={"Basis": 1.0, "basis": 2.0})), "r", "end_turn")])
        self._ok("b1", OTHER_INPUTS, 10.0)
        code, report = self._main()
        self.assertEqual(code, 3)
        self.assertEqual(report["deals"]["deal-a"]["status"], "ERROR")

    def test_clean_run_records_snapshot(self):
        self._ok("a1", GOLDEN_INPUTS, 10.0)
        self._ok("b1", OTHER_INPUTS, 10.0)
        code, report = self._main("--record", "--skill-sha", "abc")
        self.assertEqual(code, 0)
        self.assertTrue(Path(report["recorded"]["snapshot_path"]).exists())


if __name__ == "__main__":
    unittest.main()
