#!/usr/bin/env python3
r"""Tests for check-dispatch-model-floor.py — the OI-052 post-hoc model-floor probe.

WHY THIS EXISTS. The probe is the enforcement mechanism for CLAUDE.md's
never-below-Fable floor on the appsec sweep's security judgment (Option C). It is
security-gate code, so its two riskiest failure modes get explicit coverage:
  (a) a false PASS when the floor was actually breached mid-run (fallback / below-
      floor model), which would let a real breach ride silently, and
  (b) a false PASS on ABSENCE — no transcripts, or a transcript with no model
      lines — which must be a verified-null tooling error, never "clean".

Run: python _tests/test_check_dispatch_model_floor.py   (exit 0 = pass)
"""
import importlib.util
import json
import os
import sys
import tempfile

MAINT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location(
    "cdmf", os.path.join(MAINT, "check-dispatch-model-floor.py"))
cdmf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cdmf)

results = []


def expect(label, cond, detail=""):
    results.append((bool(cond), label))
    if not cond:
        print("  FAIL: %s %s" % (label, detail))


def _msg(model=None, blocks=None):
    """One JSONL record. model=None => a non-model-bearing line (e.g. user turn)."""
    msg = {"content": blocks if blocks is not None else [{"type": "text"}]}
    if model is not None:
        msg["model"] = model
    return json.dumps({"message": msg})


def write_agent(dirpath, name, lines):
    with open(os.path.join(dirpath, name), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


FABLE = "claude-fable-5"
FR = cdmf.floor_rank("fable")


def test_all_fable_passes():
    with tempfile.TemporaryDirectory() as d:
        write_agent(d, "agent-a.jsonl", [_msg(), _msg(FABLE), _msg(FABLE)])
        write_agent(d, "agent-b.jsonl", [_msg(FABLE), _msg(FABLE)])
        status, rows = cdmf.scan_subagents_dir(d, FR)
        expect("all-fable => status 0", status == 0, "got %d" % status)
        expect("all-fable => 2 rows", len(rows) == 2)


def test_fallback_block_fails():
    with tempfile.TemporaryDirectory() as d:
        write_agent(d, "agent-a.jsonl", [
            _msg(FABLE),
            _msg(FABLE, blocks=[{"type": "fallback"}]),
            _msg("claude-opus-4-8"),
        ])
        status, rows = cdmf.scan_subagents_dir(d, FR)
        expect("fallback => status 1", status == 1, "got %d" % status)
        expect("fallback flagged", rows[0]["saw_fallback"] is True)


def test_below_floor_model_fails():
    with tempfile.TemporaryDirectory() as d:
        # No explicit fallback block, but the model itself dropped below the floor.
        write_agent(d, "agent-a.jsonl", [_msg(FABLE), _msg("claude-opus-5")])
        status, rows = cdmf.scan_subagents_dir(d, FR)
        expect("below-floor model => status 1", status == 1, "got %d" % status)
        expect("below-floor recorded a violation", rows[0]["first_violation"] is not None)


def test_opus5_is_below_fable_floor():
    # Regression guard for the tier ordering: Mythos-class (fable) sits ABOVE Opus,
    # so opus-5 must rank strictly below the fable floor.
    expect("opus-5 < fable floor", cdmf.model_rank("claude-opus-5") < FR)
    expect("opus-4-8 < fable floor", cdmf.model_rank("claude-opus-4-8") < FR)
    expect("fable == floor", cdmf.model_rank("claude-fable-5") == FR)
    expect("mythos == floor", cdmf.model_rank("claude-mythos-5") == FR)


def test_unknown_model_fails_closed():
    with tempfile.TemporaryDirectory() as d:
        write_agent(d, "agent-a.jsonl", [_msg(FABLE), _msg("claude-future-9")])
        status, _ = cdmf.scan_subagents_dir(d, FR)
        expect("unknown model treated as below floor => status 1", status == 1,
               "got %d" % status)


def test_missing_dir_is_tooling_error():
    status, rows = cdmf.scan_subagents_dir(
        os.path.join(tempfile.gettempdir(), "definitely-not-a-real-dir-oi052"), FR)
    expect("missing dir => status 2", status == 2, "got %d" % status)
    expect("missing dir => no rows", rows == [])


def test_empty_dir_is_tooling_error():
    with tempfile.TemporaryDirectory() as d:
        status, rows = cdmf.scan_subagents_dir(d, FR)
        expect("empty dir => status 2 (verified-null, not PASS)", status == 2,
               "got %d" % status)


def test_transcript_with_no_model_lines_is_verified_null():
    with tempfile.TemporaryDirectory() as d:
        # A transcript that parses cleanly but carries zero model-bearing lines
        # (all user turns, no assistant model) must NOT read as a held floor.
        write_agent(d, "agent-a.jsonl", [_msg(), _msg()])
        status, rows = cdmf.scan_subagents_dir(d, FR)
        expect("no-model-lines => status 2", status == 2, "got %d" % status)
        expect("no-model-lines flagged", rows[0]["model_bearing_lines"] == 0)


def test_corrupted_breach_line_is_not_clean():
    # REFUTE F1 (CRITICAL): a below-floor tail hidden in an unparseable line (torn
    # write / two records concatenated) must NOT silently vanish into a PASS. The
    # surviving fable lines must not certify the run clean.
    with tempfile.TemporaryDirectory() as d:
        good = _msg(FABLE)
        breach = _msg("claude-opus-4-8")
        torn = breach + good  # two JSON docs concatenated on one physical line
        write_agent(d, "agent-a.jsonl", [good, torn, good])
        status, rows = cdmf.scan_subagents_dir(d, FR)
        expect("corrupted breach line => status 2 (not 0)", status == 2, "got %d" % status)
        expect("parse failure counted", rows[0]["parse_failures"] >= 1)


def test_bom_first_line_breach_is_caught():
    # REFUTE F2: a UTF-8 BOM on line 1 must not turn a first-line breach into a
    # silently-skipped parse failure. With utf-8-sig the line parses and the
    # below-floor model is caught (status 1).
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "agent-a.jsonl")
        with open(p, "w", encoding="utf-8-sig") as f:
            f.write(_msg("claude-opus-4-8") + "\n" + _msg(FABLE) + "\n")
        status, _ = cdmf.scan_subagents_dir(d, FR)
        expect("BOM + first-line breach => status 1", status == 1, "got %d" % status)


def test_dict_content_fallback_is_caught():
    # REFUTE F3: a fallback block delivered as a dict (not a list) or with drifted
    # casing must still be caught.
    with tempfile.TemporaryDirectory() as d:
        rec = json.dumps({"message": {"model": FABLE, "content": {"type": "Fallback"}}})
        write_agent(d, "agent-a.jsonl", [_msg(FABLE), rec])
        status, rows = cdmf.scan_subagents_dir(d, FR)
        expect("dict/cased fallback => status 1", status == 1, "got %d" % status)
        expect("dict fallback flagged", rows[0]["saw_fallback"] is True)


def test_top_level_model_breach_is_caught():
    # REFUTE F4: a model id at the top level of the record (not message.model)
    # must still be ranked.
    with tempfile.TemporaryDirectory() as d:
        rec = json.dumps({"model": "claude-opus-4-8", "message": {"content": []}})
        write_agent(d, "agent-a.jsonl", [_msg(FABLE), rec])
        status, _ = cdmf.scan_subagents_dir(d, FR)
        expect("top-level model breach => status 1", status == 1, "got %d" % status)


def test_unreadable_or_misencoded_is_tooling_error_not_crash():
    # REFUTE axis 2: a mis-encoded (UTF-16) transcript must be classified as a
    # tooling error (status 2), not crash the process and not read as clean.
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "agent-a.jsonl")
        with open(p, "w", encoding="utf-16") as f:
            f.write(_msg(FABLE) + "\n" + _msg("claude-opus-4-8") + "\n")
        status, rows = cdmf.scan_subagents_dir(d, FR)
        expect("mis-encoded file => status 2 (no crash)", status == 2, "got %d" % status)
        expect("read_error recorded", rows[0].get("read_error") is not None)


def test_non_string_model_does_not_crash():
    # A present-but-non-string model must rank unknown (below floor), not raise.
    with tempfile.TemporaryDirectory() as d:
        rec = json.dumps({"message": {"model": {"weird": "obj"}, "content": []}})
        write_agent(d, "agent-a.jsonl", [rec])
        status, _ = cdmf.scan_subagents_dir(d, FR)
        expect("non-string model => status 1 (below floor, no crash)", status == 1,
               "got %d" % status)


def test_main_exit_codes():
    # End-to-end through main() with --subagents-dir: clean=0, breach=1, absent=2.
    with tempfile.TemporaryDirectory() as d:
        write_agent(d, "agent-a.jsonl", [_msg(FABLE), _msg(FABLE)])
        expect("main clean => 0", cdmf.main(["--subagents-dir", d]) == 0)
    with tempfile.TemporaryDirectory() as d:
        write_agent(d, "agent-a.jsonl", [_msg(FABLE), _msg("claude-opus-4-8")])
        expect("main breach => 1", cdmf.main(["--subagents-dir", d]) == 1)
    expect("main absent dir => 2",
           cdmf.main(["--subagents-dir",
                      os.path.join(tempfile.gettempdir(), "nope-oi052-xyz")]) == 2)


def test_full_model_id_floor_arg():
    # A floor given as a full model id resolves and ranks correctly.
    with tempfile.TemporaryDirectory() as d:
        write_agent(d, "agent-a.jsonl", [_msg("claude-opus-5")])
        # opus-5 (90) passes an opus-4-8 (80) floor...
        expect("opus-5 passes opus-4-8 floor",
               cdmf.main(["--subagents-dir", d, "--floor", "claude-opus-4-8"]) == 0)
        # ...but fails the fable floor.
        expect("opus-5 fails fable floor",
               cdmf.main(["--subagents-dir", d, "--floor", "fable"]) == 1)


def test_violation_outranks_verified_null():
    with tempfile.TemporaryDirectory() as d:
        write_agent(d, "agent-good.jsonl", [_msg(FABLE), _msg("claude-opus-4-8")])  # violation
        write_agent(d, "agent-empty.jsonl", [_msg(), _msg()])                        # verified-null
        status, _ = cdmf.scan_subagents_dir(d, FR)
        expect("violation outranks verified-null => status 1", status == 1,
               "got %d" % status)


def test_meta_json_not_scanned_as_transcript():
    with tempfile.TemporaryDirectory() as d:
        write_agent(d, "agent-a.jsonl", [_msg(FABLE)])
        # a .meta.json sidecar must be ignored (does not match agent-*.jsonl)
        with open(os.path.join(d, "agent-a.meta.json"), "w", encoding="utf-8") as f:
            f.write('{"model":"fable"}')
        status, rows = cdmf.scan_subagents_dir(d, FR)
        expect("meta.json ignored => 1 row", len(rows) == 1, "got %d rows" % len(rows))
        expect("meta.json ignored => status 0", status == 0)


def test_unknown_floor_name():
    expect("unknown floor name => None", cdmf.floor_rank("nonesuch") is None)
    expect("fable floor resolves", cdmf.floor_rank("fable") == 100)


def test_real_session_transcripts_catch_the_2026_08_12_fallback():
    """Integration check against THIS session's real subagent transcripts, which
    are known to contain the mid-run opus-4-8 fallback that motivated OI-052. If
    the dir isn't present (running elsewhere), skip rather than fail — but when it
    IS present the probe MUST report a violation, or the probe is useless."""
    sid = os.environ.get("CLAUDE_CODE_SESSION_ID")
    if not sid:
        print("  (skip) real-session check — no CLAUDE_CODE_SESSION_ID")
        return
    d = os.path.join(cdmf.CLAUDE, "projects", cdmf.PROJECT, sid, "subagents")
    if not os.path.isdir(d):
        print("  (skip) real-session check — %s absent" % d)
        return
    status, rows = cdmf.scan_subagents_dir(d, FR)
    if not rows:
        print("  (skip) real-session check — no transcripts yet")
        return
    expect("real 2026-08-12 transcripts => status 1 (caught the fallback)",
           status == 1, "got %d over %d rows" % (status, len(rows)))


if __name__ == "__main__":
    for fn in sorted(k for k in dict(globals()) if k.startswith("test_")):
        globals()[fn]()
    passed = sum(1 for ok, _ in results if ok)
    total = len(results)
    print("\n%d/%d assertions passed" % (passed, total))
    sys.exit(0 if passed == total else 1)
