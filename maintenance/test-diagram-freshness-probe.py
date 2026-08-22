#!/usr/bin/env python3
"""Tests for diagram-freshness-probe.py -- qodo-code-review finding on PR #143:

  "Invalid stamp aborts audit" (Medium): a syntactically-matching but calendar-invalid
  stamp (e.g. 2026-02-31) crashed date.fromisoformat() inside a single list comprehension
  in main(), aborting the whole cross-repo audit instead of reporting a per-repo problem.

Run: python test-diagram-freshness-probe.py
"""
import importlib.util
import os
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "diagram_freshness_probe", os.path.join(HERE, "diagram-freshness-probe.py"))
dfp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dfp)

MERMAID_CONTENT = "# Repo\n```mermaid\ngraph TD; a-->b;\n```\n"


def _fake_read(monkeypatched_content):
    return lambda path: (monkeypatched_content, None)


def test_calendar_invalid_stamp_reports_problem_not_crash_unit():
    content = MERMAID_CONTENT + "<!-- diagram-verified: 2026-02-31 -->\n"
    dfp.read_local = _fake_read(content)
    result = dfp.check_one("fake-repo", "irrelevant-path", None, max_age_days=90)
    assert result["status"] == "INVALID_STAMP", f"expected INVALID_STAMP, got: {result}"
    assert "2026-02-31" in result["detail"]
    print("  PASS test_calendar_invalid_stamp_reports_problem_not_crash_unit")


def test_invalid_stamp_does_not_abort_the_whole_audit_unit():
    """The real bug: one bad target inside main()'s list comprehension used to kill every
    other target's result too. Simulate the comprehension directly against a mixed list."""
    good_content = MERMAID_CONTENT + f"<!-- diagram-verified: {date.today().isoformat()} -->\n"
    bad_content = MERMAID_CONTENT + "<!-- diagram-verified: 2026-02-31 -->\n"

    def fake_read_local(path):
        return (bad_content if path == "bad" else good_content), None

    dfp.read_local = fake_read_local
    targets = [("good-repo", "good", None), ("bad-repo", "bad", None), ("good-repo-2", "good", None)]
    results = [dfp.check_one(label, local, remote, 90) for label, local, remote in targets]
    assert len(results) == 3, f"expected all 3 targets to produce a result, got: {results}"
    statuses = {r["repo"]: r["status"] for r in results}
    assert statuses["bad-repo"] == "INVALID_STAMP"
    assert statuses["good-repo"] == "FRESH" and statuses["good-repo-2"] == "FRESH"
    print("  PASS test_invalid_stamp_does_not_abort_the_whole_audit_unit")


def test_valid_stamp_still_flags_as_a_problem_unit():
    dfp.read_local = _fake_read(MERMAID_CONTENT + "<!-- diagram-verified: 2026-02-31 -->\n")
    result = dfp.check_one("fake-repo", "irrelevant-path", None, max_age_days=90)
    assert result["status"] in ("STALE", "MISSING_STAMP", "UNREADABLE", "FUTURE_STAMP", "INVALID_STAMP")
    print("  PASS test_valid_stamp_still_flags_as_a_problem_unit")


def test_genuinely_fresh_valid_stamp_unaffected_unit():
    dfp.read_local = _fake_read(MERMAID_CONTENT + f"<!-- diagram-verified: {date.today().isoformat()} -->\n")
    result = dfp.check_one("fake-repo", "irrelevant-path", None, max_age_days=9999)
    assert result["status"] == "FRESH", f"regression: valid stamp mis-flagged: {result}"
    print("  PASS test_genuinely_fresh_valid_stamp_unaffected_unit")


def main():
    test_calendar_invalid_stamp_reports_problem_not_crash_unit()
    test_invalid_stamp_does_not_abort_the_whole_audit_unit()
    test_valid_stamp_still_flags_as_a_problem_unit()
    test_genuinely_fresh_valid_stamp_unaffected_unit()
    print("ALL DIAGRAM-FRESHNESS-PROBE TESTS PASS")


if __name__ == "__main__":
    main()
