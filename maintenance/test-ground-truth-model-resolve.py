#!/usr/bin/env python3
"""Tests for ground-truth-model-resolve.py -- verifier model floor ladder."""
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "ground_truth_model_resolve", os.path.join(HERE, "ground-truth-model-resolve.py"))
gmr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gmr)

FAILURES = []


def check(label, cond, detail=""):
    if cond:
        print("  [OK] %s" % label)
    else:
        print("  [FAIL] %s %s" % (label, detail))
        FAILURES.append(label)


def test_rung1_registry_model_wins():
    model, source = gmr.resolve_audited_model(
        {"model": "claude-opus-5"}, skill_md_text="[MODEL: claude-sonnet-5 | set 2026-01-01]")
    check("registry model field takes priority over the SKILL.md tag",
          (model, source) == ("claude-opus-5", "registry"), (model, source))


def test_rung2_skill_md_tag_used_when_registry_absent():
    model, source = gmr.resolve_audited_model(
        {}, skill_md_text="[MODEL: claude-opus-5 | checked 2026-08-12]")
    check("SKILL.md tag used when registry has no model field",
          (model, source) == ("claude-opus-5", "skill_md_tag"), (model, source))


def test_rung3_session_record_used_when_registry_and_tag_absent():
    model, source = gmr.resolve_audited_model(
        {}, skill_md_text=None, session_record={"model": "claude-sonnet-5"})
    check("session record model used as the last resort before fail-safe",
          (model, source) == ("claude-sonnet-5", "session_record"), (model, source))


def test_rung4_all_absent_fails_safe_to_none():
    model, source = gmr.resolve_audited_model({}, skill_md_text=None, session_record=None)
    check("all three rungs absent resolves to None, not a guess",
          (model, source) == (None, "unresolved"), (model, source))


def test_verifier_model_matches_or_exceeds_audited_tier():
    verifier, reasoning = gmr.resolve_verifier_model({"model": "claude-sonnet-5"})
    check("verifier model is at least the audited model's tier",
          gmr._tier(verifier) >= gmr._tier("claude-sonnet-5"), (verifier, reasoning))


def test_verifier_model_unresolved_audited_model_forces_fable():
    verifier, reasoning = gmr.resolve_verifier_model({})
    check("an unresolved audited model forces the verifier to Fable "
          "(reviewer >= implementer must never be silently violated)",
          verifier == gmr.FABLE_MODEL, (verifier, reasoning))


def test_verifier_model_unknown_audited_model_also_forces_fable():
    verifier, reasoning = gmr.resolve_verifier_model({"model": "some-future-model-not-in-the-table"})
    check("an audited model outside the known tier table also fails safe to Fable "
          "(never silently license a cheaper verifier)",
          verifier == gmr.FABLE_MODEL, (verifier, reasoning))


def test_extract_model_tag_parses_the_real_frontmatter_format():
    # Real production format includes a bare word (e.g. "observed") between
    # the model id and the pipe.
    text = ("description: ...supersedes the retired task... "
            "[MODEL: claude-opus-5 observed | checked 2026-08-12 via live-run transcript canary]")
    tag = gmr.extract_model_tag(text)
    check("parses the real [MODEL: ...] tag format used in production SKILL.md files "
          "(including the trailing 'observed' annotation)", tag == "claude-opus-5", tag)


def test_extract_model_tag_parses_the_simple_format():
    tag = gmr.extract_model_tag("[MODEL: claude-sonnet-5 | set 2026-01-01]")
    check("parses the simple [MODEL: <id> | ...] tag format", tag == "claude-sonnet-5", tag)


def test_to_agent_tool_model_name_maps_all_four_known_ids():
    check("claude-haiku-4-5-20251001 maps to 'haiku'",
          gmr.to_agent_tool_model_name("claude-haiku-4-5-20251001") == "haiku")
    check("claude-sonnet-5 maps to 'sonnet'",
          gmr.to_agent_tool_model_name("claude-sonnet-5") == "sonnet")
    check("claude-opus-5 maps to 'opus'",
          gmr.to_agent_tool_model_name("claude-opus-5") == "opus")
    check("claude-fable-5-1 maps to 'fable'",
          gmr.to_agent_tool_model_name("claude-fable-5-1") == "fable")


def test_to_agent_tool_model_name_raises_on_unknown_id():
    try:
        gmr.to_agent_tool_model_name("some-future-model-not-in-the-table")
        check("unknown full model id raises ValueError instead of "
              "silently returning an invalid Agent-tool name", False)
    except ValueError:
        check("unknown full model id raises ValueError instead of "
              "silently returning an invalid Agent-tool name", True)


if __name__ == "__main__":
    test_rung1_registry_model_wins()
    test_rung2_skill_md_tag_used_when_registry_absent()
    test_rung3_session_record_used_when_registry_and_tag_absent()
    test_rung4_all_absent_fails_safe_to_none()
    test_verifier_model_matches_or_exceeds_audited_tier()
    test_verifier_model_unresolved_audited_model_forces_fable()
    test_verifier_model_unknown_audited_model_also_forces_fable()
    test_extract_model_tag_parses_the_real_frontmatter_format()
    test_extract_model_tag_parses_the_simple_format()
    test_to_agent_tool_model_name_maps_all_four_known_ids()
    test_to_agent_tool_model_name_raises_on_unknown_id()
    print("-" * 72)
    if FAILURES:
        print("FAIL: %d failure(s): %s" % (len(FAILURES), ", ".join(FAILURES)))
        sys.exit(1)
    print("ALL PASS")
    sys.exit(0)
