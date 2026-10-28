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


def test_mmd_file_with_percent_stamp_is_in_scope_unit():
    """A standalone .mmd has no ```mermaid fence and uses a `%%` stamp; it must be checked, not NO_DIAGRAM."""
    today = date.today().isoformat()
    dfp.read_local = _fake_read(f"%% diagram-verified: {today}\nflowchart TB\n  a --> b\n")
    result = dfp.check_one("fake.mmd", "docs/diagrams/x.mmd", None, max_age_days=90)
    assert result["status"] == "FRESH", f"expected FRESH for a stamped .mmd, got: {result}"
    dfp.read_local = _fake_read("flowchart TB\n  a --> b\n")
    result = dfp.check_one("fake.mmd", "docs/diagrams/x.mmd", None, max_age_days=90)
    assert result["status"] == "MISSING_STAMP", f"expected MISSING_STAMP for an unstamped .mmd, got: {result}"
    print("  PASS test_mmd_file_with_percent_stamp_is_in_scope_unit")


def test_oldest_of_several_stamps_decides_unit():
    """A README with 3 diagrams must not read FRESH because only the FIRST diagram was re-stamped."""
    today = date.today().isoformat()
    content = (MERMAID_CONTENT + f"<!-- diagram-verified: {today} -->\n"
               + MERMAID_CONTENT + "<!-- diagram-verified: 2020-01-01 -->\n")
    dfp.read_local = _fake_read(content)
    result = dfp.check_one("fake-repo", "README.md", None, max_age_days=90)
    assert result["status"] == "STALE", f"stale later stamp was hidden by a fresh first stamp: {result}"
    assert "2020-01-01" in result["detail"]
    print("  PASS test_oldest_of_several_stamps_decides_unit")


def test_invalid_stamp_anywhere_in_file_is_reported_unit():
    today = date.today().isoformat()
    content = (MERMAID_CONTENT + f"<!-- diagram-verified: {today} -->\n"
               + MERMAID_CONTENT + "<!-- diagram-verified: 2026-02-31 -->\n")
    dfp.read_local = _fake_read(content)
    result = dfp.check_one("fake-repo", "README.md", None, max_age_days=90)
    assert result["status"] == "INVALID_STAMP", f"expected INVALID_STAMP, got: {result}"
    print("  PASS test_invalid_stamp_anywhere_in_file_is_reported_unit")


def test_repo_own_mmd_files_are_targets_unit():
    labels = [t[0] for t in dfp.TARGETS]
    assert any("docs/diagrams/01_hook_lifecycle.mmd" in l for l in labels), f"missing .mmd targets: {labels}"
    print("  PASS test_repo_own_mmd_files_are_targets_unit")


def main():
    test_calendar_invalid_stamp_reports_problem_not_crash_unit()
    test_invalid_stamp_does_not_abort_the_whole_audit_unit()
    test_valid_stamp_still_flags_as_a_problem_unit()
    test_genuinely_fresh_valid_stamp_unaffected_unit()
    test_mmd_file_with_percent_stamp_is_in_scope_unit()
    test_oldest_of_several_stamps_decides_unit()
    test_invalid_stamp_anywhere_in_file_is_reported_unit()
    test_repo_own_mmd_files_are_targets_unit()
    print("ALL DIAGRAM-FRESHNESS-PROBE TESTS PASS")


if __name__ == "__main__":
    main()
