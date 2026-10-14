#!/usr/bin/env python3
"""Tests for session-context-xref-probe.py.

The probe's whole value depends on it not crying wolf: it is wired into a DAILY guard,
so a false [XREF-MISSING] costs more attention than a missed one. Most of these tests
are therefore about what must NOT be reported -- elided paths, prose in backticks,
citations whose home is outside the search roots, and a rolled-over event_log.

Run: python test-session-context-xref-probe.py
"""
import importlib.util
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "xref", os.path.join(HERE, "session-context-xref-probe.py"))
xref = importlib.util.module_from_spec(spec)
spec.loader.exec_module(xref)


def _fixture(text, event_log="", archives=None, extra_files=()):
    """Build a throwaway (source, memory_dir) pair."""
    root = tempfile.mkdtemp(prefix="xref-")
    mem = os.path.join(root, "memory")
    os.makedirs(os.path.join(mem, "_archive"))
    src = os.path.join(root, "session-context.md")
    with open(src, "w", encoding="utf-8") as f:
        f.write(text)
    with open(os.path.join(mem, "event_log.md"), "w", encoding="utf-8") as f:
        f.write(event_log)
    for name, body in (archives or {}).items():
        with open(os.path.join(mem, "_archive", name), "w", encoding="utf-8") as f:
            f.write(body)
    for name in extra_files:
        with open(os.path.join(mem, name), "w", encoding="utf-8") as f:
            f.write("x")
    return src, mem


def test_dated_event_log_citation_without_an_entry_is_a_finding_unit():
    """THE root incident, 2026-08-22: session-context.md cited 'History: event_log.md
    2026-08-22' for ora-passed-deal-tracker and no such entry had ever been written."""
    src, mem = _fixture("- Thing. History: `event_log.md` 2026-08-22.\n",
                        event_log="# log\n\n## 2026-08-16 - something else\n")
    findings, skips, _ = xref.probe(src, mem)
    assert skips == []
    assert len(findings) == 1 and findings[0]["kind"] == "event-log-entry"
    assert findings[0]["ref"] == "2026-08-22"
    print("  PASS test_dated_event_log_citation_without_an_entry_is_a_finding_unit")


def test_dated_event_log_citation_with_an_entry_is_clean_unit():
    src, mem = _fixture("- Thing. History: `event_log.md` 2026-08-22.\n",
                        event_log="# log\n\n## 2026-08-22 - the thing happened\n")
    assert xref.probe(src, mem)[0] == []
    print("  PASS test_dated_event_log_citation_with_an_entry_is_clean_unit")


def test_citation_satisfied_by_a_rolled_over_archive_chunk_unit():
    """event_log.md is rolled over periodically; a citation older than the current window
    lives in memory/_archive/. Checking only the live log would turn every rollover into
    a wave of false findings."""
    src, mem = _fixture("- Old thing. History: `event_log.md` 2026-06-11.\n",
                        event_log="# log\n\n## 2026-08-22 - recent only\n",
                        archives={"event_log_2026-08-01.md": "## 2026-06-11 - the old thing\n"})
    assert xref.probe(src, mem)[0] == []
    print("  PASS test_citation_satisfied_by_a_rolled_over_archive_chunk_unit")


def test_undated_event_log_mention_is_not_checked_unit():
    """'History: `event_log.md`' with no date makes no checkable claim."""
    src, mem = _fixture("- Thing. History: `event_log.md`.\n", event_log="# log\n")
    findings, _, stats = xref.probe(src, mem)
    assert findings == [] and stats["datedEventLogCitations"] == 0
    print("  PASS test_undated_event_log_mention_is_not_checked_unit")


def test_unreadable_event_log_skips_the_dated_check_rather_than_alarming_unit():
    """'Could not look' must never be reported as a dated-citation finding -- that would
    be a fabricated verification. The dated check downgrades to a [SKIP] naming how many
    citations went unchecked. (The bare `event_log.md` token is still a FILE citation,
    and a genuinely absent event_log.md is a real finding on that separate check -- the
    two are deliberately independent.)"""
    src, mem = _fixture("- Thing. History: `event_log.md` 2026-08-22.\n")
    os.remove(os.path.join(mem, "event_log.md"))
    findings, skips, _ = xref.probe(src, mem)
    assert not [f for f in findings if f["kind"] == "event-log-entry"], \
        "an unreadable log must not manufacture a dated-entry finding"
    assert len(skips) == 1 and "NOT checked" in skips[0]
    print("  PASS test_unreadable_event_log_skips_the_dated_check_rather_than_alarming_unit")


def test_missing_file_citation_is_a_finding_unit():
    """The second real finding of the probe's first live run: session-context.md pointed
    at `reference_tech.md`, which has never existed -- the file is `tech.md`."""
    src, mem = _fixture("- Full claim protocol: `reference_tech.md`.\n",
                        extra_files=("tech.md",))
    findings, _, _ = xref.probe(src, mem)
    assert len(findings) == 1 and findings[0]["kind"] == "file"
    assert findings[0]["ref"] == "reference_tech.md"
    print("  PASS test_missing_file_citation_is_a_finding_unit")


def test_resolvable_file_citation_is_clean_unit():
    src, mem = _fixture("- Detail: `tech.md` and `memory/tech.md`.\n", extra_files=("tech.md",))
    assert xref.probe(src, mem)[0] == []
    print("  PASS test_resolvable_file_citation_is_clean_unit")


def test_elided_and_prose_backticks_are_skipped_unit():
    """The false-positive classes that actually appear in session-context.md: an elided
    registry path, a call with arguments, a bare identifier, a prose phrase."""
    text = ("- Registry `AppData\\Roaming\\Claude\\claude-code-sessions\\…\\scheduled-tasks.json`; "
            "pause via `update_scheduled_task(enabled:false)`; glob `_archive_*`; "
            "`ora-cowork-heartbeat`; `hooks/lib/claim_work.py claim <slug>`; "
            "`this is prose in backticks.md`\n")
    src, mem = _fixture(text)
    findings, _, stats = xref.probe(src, mem)
    assert stats["fileCitations"] == 0, "none of these are checkable file citations"
    assert findings == [], f"and so none may be reported: {findings}"
    print("  PASS test_elided_and_prose_backticks_are_skipped_unit")


def test_extra_roots_prevent_the_outside_the_search_path_false_positive_unit():
    """A citation whose home is outside the built-in roots is a verified-null, not a
    finding. Live proof: `outreach-ratification.json` lives under the OneDrive business
    folder and read as MISSING until that root was added."""
    src, mem = _fixture("- Bounded by `some-external-manifest.json`.\n")
    assert len(xref.probe(src, mem)[0]) == 1, "sanity: unresolvable without the extra root"

    ext = tempfile.mkdtemp(prefix="xref-ext-")
    with open(os.path.join(ext, "some-external-manifest.json"), "w", encoding="utf-8") as f:
        f.write("{}")
    real_extra = xref.extra_roots
    try:
        xref.extra_roots = lambda: [ext]
        assert xref.probe(src, mem)[0] == []
    finally:
        xref.extra_roots = real_extra
    print("  PASS test_extra_roots_prevent_the_outside_the_search_path_false_positive_unit")


def test_missing_or_empty_source_fails_open_unit():
    """backup-session-context.py already alarms on a missing/empty session-context.md.
    This probe must not double-alarm, and must never crash the guard that runs it."""
    src, mem = _fixture("")
    findings, skips, _ = xref.probe(src, mem)
    assert findings == [] and len(skips) == 1 and "empty" in skips[0]
    findings, skips, _ = xref.probe(os.path.join(mem, "nope.md"), mem)
    assert findings == [] and len(skips) == 1 and "unreadable" in skips[0]
    print("  PASS test_missing_or_empty_source_fails_open_unit")


def test_exit_code_is_1_only_when_something_is_unresolved_unit():
    src, mem = _fixture("- Thing. History: `event_log.md` 2026-08-22.\n",
                        event_log="# log\n\n## 2026-08-22 - present\n")
    old = sys.argv
    try:
        sys.argv = ["p", "--source", src, "--memory-dir", mem, "--json"]
        assert xref.main() == 0
        with open(src, "a", encoding="utf-8") as f:
            f.write("- Missing. History: `event_log.md` 2026-08-19.\n")
        assert xref.main() == 1
    finally:
        sys.argv = old
    print("  PASS test_exit_code_is_1_only_when_something_is_unresolved_unit")


def test_claude_outputs_folder_is_a_builtin_search_root_unit():
    """outreach-ratification.json lives in the OneDrive 'Claude outputs' folder; that
    folder must be a built-in (read-only) root so it stops reading as MISSING, and a
    citation there must resolve."""
    _, mem = _fixture("")
    want = os.path.join(xref.ONEDRIVE, "Business", "Investment Candidates -- 2026", "Claude outputs")
    assert want in xref.search_roots(mem), "Claude outputs root missing from search_roots"
    real_onedrive, real_extra = xref.ONEDRIVE, xref.extra_roots
    fake = tempfile.mkdtemp(prefix="xref-od-")
    outs = os.path.join(fake, "Business", "Investment Candidates -- 2026", "Claude outputs")
    os.makedirs(outs)
    with open(os.path.join(outs, "outreach-ratification.json"), "w", encoding="utf-8") as f:
        f.write("{}")
    src, mem = _fixture("- Bounded by `outreach-ratification.json`.\n")
    try:
        xref.ONEDRIVE = fake
        xref.extra_roots = lambda: []
        assert xref.probe(src, mem)[0] == []
    finally:
        xref.ONEDRIVE, xref.extra_roots = real_onedrive, real_extra
    print("  PASS test_claude_outputs_folder_is_a_builtin_search_root_unit")


def main():
    test_dated_event_log_citation_without_an_entry_is_a_finding_unit()
    test_dated_event_log_citation_with_an_entry_is_clean_unit()
    test_citation_satisfied_by_a_rolled_over_archive_chunk_unit()
    test_undated_event_log_mention_is_not_checked_unit()
    test_unreadable_event_log_skips_the_dated_check_rather_than_alarming_unit()
    test_missing_file_citation_is_a_finding_unit()
    test_resolvable_file_citation_is_clean_unit()
    test_elided_and_prose_backticks_are_skipped_unit()
    test_extra_roots_prevent_the_outside_the_search_path_false_positive_unit()
    test_claude_outputs_folder_is_a_builtin_search_root_unit()
    test_missing_or_empty_source_fails_open_unit()
    test_exit_code_is_1_only_when_something_is_unresolved_unit()
    print("ALL SESSION-CONTEXT-XREF-PROBE TESTS PASS")


if __name__ == "__main__":
    main()
