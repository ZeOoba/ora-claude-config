#!/usr/bin/env python3
"""Tests for doctrine-integrity-probe.py (TDD).

Run: python test-doctrine-integrity-probe.py
Pure stdlib. ASCII-only output (Windows cp1252 console).
"""
import os
import sys
import subprocess
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PROBE = os.path.join(HERE, "doctrine-integrity-probe.py")
REAL_CLAUDE_MD = os.path.join(os.path.expanduser("~"), ".claude", "CLAUDE.md")


def run_probe(argv=None):
    cmd = [sys.executable, PROBE]
    if argv:
        cmd += argv
    return subprocess.run(cmd, capture_output=True, text=True)


def test_real_doctrine_valid():
    """The live CLAUDE.md doctrine resolves cleanly -> exit 0."""
    r = run_probe()  # defaults to the real CLAUDE.md
    assert r.returncode == 0, (
        "expected exit 0 against real CLAUDE.md, got %d\nSTDOUT:\n%s\nSTDERR:\n%s"
        % (r.returncode, r.stdout, r.stderr)
    )
    assert "[MISSING]" not in r.stdout, "real doctrine reported a MISSING item:\n%s" % r.stdout
    print("  PASS test_real_doctrine_valid (exit 0, no MISSING)")


def test_missing_command_fails():
    """A fixture referencing /nonexistent-cmd -> exit 1 and reports it MISSING."""
    fd, path = tempfile.mkstemp(suffix="_CLAUDE.md", text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            # Genuine commands in the doctrine are written backtick-opened (`/name`),
            # which is the convention the probe keys on.
            fh.write("## Engineering Operating System\n run `/nonexistent-cmd`\n")
        r = run_probe([path])
        assert r.returncode == 1, (
            "expected exit 1 for missing command, got %d\nSTDOUT:\n%s\nSTDERR:\n%s"
            % (r.returncode, r.stdout, r.stderr)
        )
        assert "[MISSING] /nonexistent-cmd" in r.stdout, (
            "expected the specific MISSING line for the command (exit 1 and a "
            "generic [MISSING] can both be supplied by other checks):\n%s" % r.stdout
        )
        print("  PASS test_missing_command_fails (exit 1, reports /nonexistent-cmd)")
    finally:
        os.remove(path)


def test_missing_section_fails():
    """A CLAUDE.md without the EOS section -> exit 1 with a clear message."""
    fd, path = tempfile.mkstemp(suffix="_CLAUDE.md", text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write("# Some other doc\n## Ranked goals\n nothing here\n")
        r = run_probe([path])
        assert r.returncode == 1, (
            "expected exit 1 when section absent, got %d\nSTDOUT:\n%s\nSTDERR:\n%s"
            % (r.returncode, r.stdout, r.stderr)
        )
        print("  PASS test_missing_section_fails (exit 1, section absent)")
    finally:
        os.remove(path)


def test_real_doctrine_skills_resolve():
    """Every skill in the live 'Skill precedence' block resolves on SOME surface.

    Directly guards against the surface-blind false positive from the 2026-06-06
    review (judging Cowork skills absent because only the Code surface was scanned).
    """
    r = run_probe()
    assert r.returncode == 0, (
        "expected exit 0 against real CLAUDE.md, got %d\nSTDOUT:\n%s\nSTDERR:\n%s"
        % (r.returncode, r.stdout, r.stderr)
    )
    assert "Skills referenced:" in r.stdout, "probe did not run the skill check:\n%s" % r.stdout
    for line in r.stdout.splitlines():
        assert not ("[MISSING]" in line and "skill" in line.lower()), (
            "real doctrine reported a skill MISSING (surface-blind regression?):\n%s" % r.stdout
        )
    # Regression guard (review of c9dcdb9): these have REAL SKILL.md homes under
    # 01_Workspace/outputs/ and MUST resolve as real skill dirs, NOT be masked by
    # the plugin allowlist (an over-broad 'outputs' prune once hid them).
    # v2.1 (2026-06-11) slimmed the tie-breaks section: legal-intelligence,
    # tenant-intelligence and re-operations are no longer referenced there, so
    # only the still-referenced pair is asserted.
    for s in ("communication-intelligence", "deal-comparison"):
        line = next((l for l in r.stdout.splitlines()
                     if l.lstrip().startswith("[OK]") and (" " + s + " ") in l), "")
        assert "(Code/Cowork surface)" in line, (
            "%s should resolve via a real skill dir, not the allowlist:\n%s" % (s, r.stdout))
    print("  PASS test_real_doctrine_skills_resolve (real dirs resolve, not allowlist-masked)")


def test_agent_and_workflow_references_resolve():
    """Tokens the doctrine references as AGENTS / WORKFLOWS resolve, not MISSING.

    The 'Skill precedence' block names orchestration primitives that are not SKILL.md
    skills: agents (CLAUDE.md literally says "the bare `deal-recon` agent", "the
    `lease-sweep` agent", "the `portfolio-anomaly-scout` agent") resolve at
    ~/.claude/agents/<name>.md; verified-deal-recon is workflow-backed at
    ~/.claude/workflows/<name>.js. Before this fix they were false MISSING.
    """
    r = run_probe()
    assert r.returncode == 0, (
        "expected exit 0 against real CLAUDE.md, got %d\nSTDOUT:\n%s\nSTDERR:\n%s"
        % (r.returncode, r.stdout, r.stderr))
    # v2.1 (2026-06-11): lease-sweep left the tie-breaks section -> not asserted.
    for agent in ("deal-recon", "portfolio-anomaly-scout"):
        line = next((l for l in r.stdout.splitlines()
                     if l.lstrip().startswith("[OK]") and (" " + agent + " ") in l), "")
        assert "agent definition" in line, (
            "%s should resolve as an agent definition:\n%s" % (agent, r.stdout))
    vdr = next((l for l in r.stdout.splitlines()
                if l.lstrip().startswith("[OK]") and " verified-deal-recon " in l), "")
    assert "workflow" in vdr, (
        "verified-deal-recon should resolve as a workflow:\n%s" % r.stdout)
    print("  PASS test_agent_and_workflow_references_resolve (agents + workflow resolve)")


def test_legacy_deprecated_references_resolve():
    """The 3 archived legacy duplicates resolve as deprecated, not MISSING.

    CLAUDE.md names deal-screen / cap-rate-snapshot / market-comp-analyzer ONLY to
    say they are "legacy duplicates subsumed by acquisition-underwriting". They
    intentionally resolve to nothing on disk; the reference is the deprecation
    notice, so absence is expected-by-design.
    """
    r = run_probe()
    assert r.returncode == 0, (
        "expected exit 0 against real CLAUDE.md, got %d\nSTDOUT:\n%s\nSTDERR:\n%s"
        % (r.returncode, r.stdout, r.stderr))
    for legacy in ("deal-screen", "cap-rate-snapshot", "market-comp-analyzer"):
        line = next((l for l in r.stdout.splitlines()
                     if l.lstrip().startswith("[OK]") and (" " + legacy + " ") in l), "")
        assert "legacy" in line.lower() or "deprecated" in line.lower(), (
            "%s should resolve as a legacy/deprecated reference:\n%s" % (legacy, r.stdout))
    print("  PASS test_legacy_deprecated_references_resolve (3 archived duplicates OK)")


def test_missing_skill_fails():
    """A 'Skill precedence' section naming an unknown skill -> exit 1, reported."""
    fd, path = tempfile.mkstemp(suffix="_CLAUDE.md", text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write("## Engineering Operating System\n no commands here\n"
                     "## Skill precedence\n- Deal: `zzz-nonexistent-skill`\n")
        r = run_probe([path])
        assert r.returncode == 1, (
            "expected exit 1 for missing skill, got %d\nSTDOUT:\n%s\nSTDERR:\n%s"
            % (r.returncode, r.stdout, r.stderr)
        )
        assert "zzz-nonexistent-skill" in r.stdout, (
            "expected the missing skill to be reported:\n%s" % r.stdout
        )
        print("  PASS test_missing_skill_fails (exit 1, reports unknown skill)")
    finally:
        os.remove(path)


def test_missing_skill_section_fails():
    """EOS present but the 'Skill precedence' section absent -> exit 1 (mirrors EOS).

    A drift probe must treat disappearance of the very section it audits as drift,
    not as a benign no-op (review of c9dcdb9, finding #2).
    """
    fd, path = tempfile.mkstemp(suffix="_CLAUDE.md", text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write("## Engineering Operating System\n no commands here\n"
                     "## Some other section\n nothing\n")
        r = run_probe([path])
        assert r.returncode == 1, (
            "expected exit 1 when Skill precedence section absent, got %d\n%s"
            % (r.returncode, r.stdout))
        assert "Skill precedence" in r.stdout and "MISSING" in r.stdout, (
            "expected a MISSING report for the absent Skill precedence section:\n%s" % r.stdout)
        print("  PASS test_missing_skill_section_fails (exit 1, absent section flagged)")
    finally:
        os.remove(path)


def test_skill_section_case_insensitive():
    """A recased '## Skill Precedence' header is still parsed (case-insensitive)."""
    fd, path = tempfile.mkstemp(suffix="_CLAUDE.md", text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write("## Engineering Operating System\n no commands here\n"
                     "## Skill Precedence (Recased)\n- Deal: `zzz-nonexistent-skill`\n")
        r = run_probe([path])
        assert r.returncode == 1, (
            "expected exit 1 (recased section parsed, bogus skill found), got %d\n%s"
            % (r.returncode, r.stdout))
        assert "zzz-nonexistent-skill" in r.stdout, (
            "recased 'Skill Precedence' header not parsed (case-sensitivity bug):\n%s" % r.stdout)
        print("  PASS test_skill_section_case_insensitive (recased header parsed)")
    finally:
        os.remove(path)


def _v21_base():
    """Minimal fixture valid under the v2.1 layout (renamed section headers)."""
    return ("## Engineering OS (Claude Code surface ONLY -- omit from ported copies)\n"
            " no commands here\n"
            "## Skill tie-breaks (descriptions route; prefer the narrowest match)\n"
            "- nothing referenced\n")


def _write_fixture(content):
    fd, path = tempfile.mkstemp(suffix="_CLAUDE.md", text=True)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(content)
    return path


def test_v21_headers_parse():
    """The renamed v2.1 headers ('Engineering OS', 'Skill tie-breaks') are parsed.

    Guards against the 2026-06-11 regression: the v2.1 CLAUDE.md rewrite renamed
    both sections and the probe hard-failed on 'section not found' instead of
    auditing their contents."""
    path = _write_fixture(_v21_base().replace(
        "- nothing referenced", "- Deal: `zzz-nonexistent-skill`"))
    try:
        r = run_probe([path])
        assert r.returncode == 1, (
            "expected exit 1 (bogus skill in a parsed tie-breaks section), got %d\n%s"
            % (r.returncode, r.stdout))
        assert "zzz-nonexistent-skill" in r.stdout, (
            "v2.1 'Skill tie-breaks' header not parsed -- bogus skill not reported:\n%s"
            % r.stdout)
        assert "section not found" not in r.stdout, (
            "v2.1 'Engineering OS' header not parsed:\n%s" % r.stdout)
    finally:
        os.remove(path)
    path = _write_fixture(_v21_base())
    try:
        r = run_probe([path])
        assert r.returncode == 0, (
            "expected exit 0 for a clean v2.1 fixture, got %d\n%s" % (r.returncode, r.stdout))
    finally:
        os.remove(path)
    print("  PASS test_v21_headers_parse (both renamed headers parsed)")


def test_size_budget_fail():
    """CLAUDE.md over the word budget -> exit 1 with a size-budget report.
    The pre-trim v1 file was 1,597 words; regression to that size must FAIL."""
    path = _write_fixture(_v21_base() + ("word " * 1600) + "\n")
    try:
        r = run_probe([path])
        assert r.returncode == 1, (
            "expected exit 1 for an over-budget file, got %d\n%s" % (r.returncode, r.stdout))
        assert "size budget exceeded" in r.stdout, (
            "expected the specific size-budget failure line:\n%s" % r.stdout)
    finally:
        os.remove(path)
    print("  PASS test_size_budget_fail (1,600-word fixture fails the budget)")


def test_dated_annotation_fails():
    """A bare ISO date in CLAUDE.md violates 'keep this file dateless' -> exit 1.
    Dates embedded in hyphenated slugs (spec filenames) are exempt."""
    path = _write_fixture(_v21_base() + "- ratified 2026-06-10, do not unify\n")
    try:
        r = run_probe([path])
        assert r.returncode == 1, (
            "expected exit 1 for a dated annotation, got %d\n%s" % (r.returncode, r.stdout))
        assert "date" in r.stdout.lower(), "expected a dated-annotation report:\n%s" % r.stdout
    finally:
        os.remove(path)
    path = _write_fixture(_v21_base().replace(
        "omit from ported copies",
        "spec: docs/2026-06-05-engineering-operating-system-design.md"))
    try:
        r = run_probe([path])
        assert r.returncode == 0, (
            "slug-embedded date (spec filename) must be exempt, got exit %d\n%s"
            % (r.returncode, r.stdout))
    finally:
        os.remove(path)
    print("  PASS test_dated_annotation_fails (bare date fails; slug date exempt)")


def test_tombstone_aging_warns():
    """A date older than 30 days in session-context.md -> WARN (never exit 1):
    the volatile layer may reference recent history, but tombstones must age out."""
    import datetime
    old = (datetime.date.today() - datetime.timedelta(days=90)).isoformat()
    doc = _write_fixture(_v21_base())
    fd, sc = tempfile.mkstemp(suffix="_session-context.md", text=True)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write("- connector REMOVED %s -- never reference it\n" % old)
    try:
        r = run_probe([doc, "--session-context=%s" % sc])
        assert r.returncode == 0, (
            "aging tombstones are WARN-only, got exit %d\n%s" % (r.returncode, r.stdout))
        assert "aging tombstone:" in r.stdout, (
            "expected an aging-tombstone WARN:\n%s" % r.stdout)
    finally:
        os.remove(doc)
        os.remove(sc)
    print("  PASS test_tombstone_aging_warns (90-day-old tombstone -> WARN, exit 0)")


def test_cross_file_duplication_warns():
    """A >=12-word verbatim run shared between CLAUDE.md and session-context.md
    -> WARN (one fact, one home), never exit 1 (known-deliberate residuals exist
    until the rules.md consolidation pass; flip to fail after it lands)."""
    shared = ("alpha bravo charlie delta echo foxtrot golf hotel india "
              "juliet kilo lima mike november oscar")
    doc = _write_fixture(_v21_base() + "- " + shared + "\n")
    fd, sc = tempfile.mkstemp(suffix="_session-context.md", text=True)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write("unrelated line\n- " + shared + "\n")
    try:
        r = run_probe([doc, "--session-context=%s" % sc])
        assert r.returncode == 0, (
            "duplication is WARN-only, got exit %d\n%s" % (r.returncode, r.stdout))
        assert "duplicated run (" in r.stdout, (
            "expected a cross-file duplication WARN:\n%s" % r.stdout)
    finally:
        os.remove(doc)
        os.remove(sc)
    print("  PASS test_cross_file_duplication_warns (shared 15-word run -> WARN, exit 0)")


def test_confidential_leak_fails():
    """An ACTIVE confidential term in CLAUDE.md (invariant 3) -> exit 1, and the
    probe report must NOT echo the term itself (the report is emailed weekly)."""
    import json
    terms = {"_meta": {"purpose": "test"},
             "zz_test": {"label": "t", "active": True, "note": "",
                         "always": ["zzz-secret-deal"], "context": [],
                         "context_requires_any": []}}
    fd, tpath = tempfile.mkstemp(suffix="_terms.json", text=True)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(terms, fh)
    doc = _write_fixture(_v21_base() + "- we discussed zzz-secret-deal here\n")
    try:
        r = run_probe([doc, "--terms=%s" % tpath])
        assert r.returncode == 1, (
            "expected exit 1 for a confidential-term leak, got %d\n%s"
            % (r.returncode, r.stdout))
        assert "confidential" in r.stdout.lower(), (
            "expected a confidential-leak report:\n%s" % r.stdout)
        assert "zzz-secret-deal" not in r.stdout, (
            "the probe report must never echo the confidential term itself:\n%s" % r.stdout)
    finally:
        os.remove(doc)
        os.remove(tpath)
    # An INACTIVE deal's terms are not a leak (deal closed -> name may appear).
    terms["zz_test"]["active"] = False
    fd, tpath = tempfile.mkstemp(suffix="_terms.json", text=True)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(terms, fh)
    doc = _write_fixture(_v21_base() + "- we discussed zzz-secret-deal here\n")
    try:
        r = run_probe([doc, "--terms=%s" % tpath])
        assert r.returncode == 0, (
            "inactive deal terms must not fail, got exit %d\n%s" % (r.returncode, r.stdout))
    finally:
        os.remove(doc)
        os.remove(tpath)
    print("  PASS test_confidential_leak_fails (active term -> exit 1, term not echoed; inactive -> OK)")


def test_terms_shape_failopen():
    """Malformed terms-file SHAPES degrade to WARN (fail-open), never crash:
    (a) valid JSON that is not an object; (b) 'always' null; (c) 'always' a
    string (which would otherwise iterate per character and flood MISSING)."""
    import json
    cases = [
        ("[1, 2, 3]", "not a JSON object"),
        (json.dumps({"zz": {"active": True, "always": None}}), "not a list"),
        (json.dumps({"zz": {"active": True, "always": "zzz-secret-deal"}}), "not a list"),
    ]
    for raw, expect in cases:
        fd, tpath = tempfile.mkstemp(suffix="_terms.json", text=True)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(raw)
        doc = _write_fixture(_v21_base() + "- we discussed zzz-secret-deal here\n")
        try:
            r = run_probe([doc, "--terms=%s" % tpath])
            assert r.returncode == 0, (
                "shape '%s' must fail open (exit 0), got %d\nSTDOUT:\n%s\nSTDERR:\n%s"
                % (expect, r.returncode, r.stdout, r.stderr))
            assert r.stderr.strip() == "", (
                "probe must never crash (stderr non-empty):\n%s" % r.stderr)
            assert expect in r.stdout, (
                "expected a '%s' fail-open WARN:\n%s" % (expect, r.stdout))
            assert "inert this run" in r.stdout, (
                "an inert leak check must announce itself:\n%s" % r.stdout)
        finally:
            os.remove(doc)
            os.remove(tpath)
    print("  PASS test_terms_shape_failopen (3 malformed shapes -> WARN + inert notice, no crash)")


def test_leak_formatting_and_excerpt_withholding():
    """(a) Word-run matching defeats formatting evasion: a term split by
    markdown emphasis still leaks-fails. (b) A duplicated-run excerpt that
    contains an active term is WITHHELD from the printed report -- the
    index-only discipline of the leak check must not be defeated by the
    duplication check sharing the same (emailed) stdout."""
    import json
    terms = {"zz_test": {"label": "t", "active": True,
                         "always": ["delta-echo-foxtrot"], "context": [],
                         "context_requires_any": []}}
    fd, tpath = tempfile.mkstemp(suffix="_terms.json", text=True)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(terms, fh)
    # (a) markdown-split term in the doc body
    doc = _write_fixture(_v21_base() + "- we met re delta **echo** foxtrot today\n")
    try:
        r = run_probe([doc, "--terms=%s" % tpath])
        assert r.returncode == 1, (
            "markdown-split term must still leak-fail, got %d\n%s" % (r.returncode, r.stdout))
        assert "delta" not in r.stdout, (
            "report echoed part of the confidential term:\n%s" % r.stdout)
    finally:
        os.remove(doc)
    # (b) duplicated run containing the term -> excerpt withheld
    shared = ("alpha bravo charlie delta echo foxtrot golf hotel india "
              "juliet kilo lima mike november oscar")
    doc = _write_fixture(_v21_base() + "- " + shared + "\n")
    fd, sc = tempfile.mkstemp(suffix="_session-context.md", text=True)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write("unrelated\n- " + shared + "\n")
    try:
        r = run_probe([doc, "--terms=%s" % tpath, "--session-context=%s" % sc])
        assert "excerpt withheld" in r.stdout, (
            "expected the duplication excerpt to be withheld:\n%s" % r.stdout)
        assert "alpha bravo charlie" not in r.stdout, (
            "the term-bearing excerpt text was printed:\n%s" % r.stdout)
    finally:
        os.remove(doc)
        os.remove(sc)
    print("  PASS test_leak_formatting_and_excerpt_withholding (split term caught; excerpt withheld)")


def main():
    assert os.path.isfile(REAL_CLAUDE_MD), "real CLAUDE.md not found: %s" % REAL_CLAUDE_MD
    test_real_doctrine_valid()
    test_missing_command_fails()
    test_missing_section_fails()
    test_real_doctrine_skills_resolve()
    test_agent_and_workflow_references_resolve()
    test_legacy_deprecated_references_resolve()
    test_missing_skill_fails()
    test_missing_skill_section_fails()
    test_skill_section_case_insensitive()
    test_v21_headers_parse()
    test_size_budget_fail()
    test_dated_annotation_fails()
    test_tombstone_aging_warns()
    test_cross_file_duplication_warns()
    test_confidential_leak_fails()
    test_terms_shape_failopen()
    test_leak_formatting_and_excerpt_withholding()
    print("ALL DOCTRINE-PROBE TESTS PASS")


if __name__ == "__main__":
    main()
