#!/usr/bin/env python3
"""Tests for doctrine-integrity-probe.py (TDD).

Run: python test-doctrine-integrity-probe.py
Pure stdlib. ASCII-only output (Windows cp1252 console).
"""
import json
import os
import re
import shutil
import sys
import subprocess
import tempfile

# This test spins up its own throwaway git repos in temp dirs. When invoked as part of
# the real pre-push hook chain, git sets GIT_DIR/GIT_WORK_TREE/GIT_INDEX_FILE (etc.) in
# this process's environment so IT can operate on the outer repo -- but those same vars
# leak into every subprocess git call below and silently redirect them at the outer repo
# instead of the temp one, breaking git operations against the temp fixtures.
for _v in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR",
           "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_PREFIX"):
    os.environ.pop(_v, None)

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


def _guards_fixture(guards_line):
    """A minimal v2.1 fixture with GUARDS_LINE injected into the EOS section (so
    extract_section(EOS) and the check-11 'Guards:' scan both see it)."""
    return _v21_base().replace(
        " no commands here\n", " no commands here\n" + guards_line + "\n", 1)


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
    """CLAUDE.md over the word budget (WORD_BUDGET_FAIL, currently 1850) -> exit 1 with
    a size-budget report. Fixture uses 1,900 words to clear the recalibrated ceiling:
    the 1590->1850 budget recalibration left this fixture's former 1,600-word count
    UNDER the new fail line, so it had stopped exercising the fail path (a stale test,
    not a real regression -- the check itself is correct)."""
    path = _write_fixture(_v21_base() + ("word " * 1900) + "\n")
    try:
        r = run_probe([path])
        assert r.returncode == 1, (
            "expected exit 1 for an over-budget file, got %d\n%s" % (r.returncode, r.stdout))
        assert "size budget exceeded" in r.stdout, (
            "expected the specific size-budget failure line:\n%s" % r.stdout)
    finally:
        os.remove(path)
    print("  PASS test_size_budget_fail (1,900-word fixture fails the budget)")


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


def test_cross_file_duplication_fails():
    """A >=12-word verbatim run shared between CLAUDE.md and session-context.md
    -> hard fail, exit 1 (one fact, one home). FLIPPED 2026-07-14: this was
    WARN-only pending the rules.md consolidation pass (10 dated history-wall
    section headers removed, 3 narrative walls trimmed to event_log.md
    pointers, 2677 -> 2521 words) -- that pass landed, so duplication is now
    enforced, not just advisory."""
    shared = ("alpha bravo charlie delta echo foxtrot golf hotel india "
              "juliet kilo lima mike november oscar")
    doc = _write_fixture(_v21_base() + "- " + shared + "\n")
    fd, sc = tempfile.mkstemp(suffix="_session-context.md", text=True)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write("unrelated line\n- " + shared + "\n")
    try:
        r = run_probe([doc, "--session-context=%s" % sc])
        assert r.returncode == 1, (
            "duplication must now hard-fail, got exit %d\n%s" % (r.returncode, r.stdout))
        assert "duplicated run (" in r.stdout, (
            "expected a cross-file duplication finding:\n%s" % r.stdout)
    finally:
        os.remove(doc)
        os.remove(sc)
    print("  PASS test_cross_file_duplication_fails (shared 15-word run -> FAIL, exit 1)")


def test_no_duplication_still_ok():
    """Sanity check the flip doesn't false-positive: no shared run -> exit 0."""
    doc = _write_fixture(_v21_base() + "- a unique unshared line here\n")
    fd, sc = tempfile.mkstemp(suffix="_session-context.md", text=True)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write("completely different content, nothing in common at all\n")
    try:
        r = run_probe([doc, "--session-context=%s" % sc])
        assert r.returncode == 0, (
            "no duplication should stay exit 0, got %d\n%s" % (r.returncode, r.stdout))
    finally:
        os.remove(doc)
        os.remove(sc)
    print("  PASS test_no_duplication_still_ok (no shared run -> OK, exit 0)")


def test_backup_coverage_flags_untracked_dir():
    """--backup-root: a top-level dir with no git-tracked files that is not on
    the transient allowlist -> WARN opt-in review candidate (advisory, exit 0).
    A dir with a tracked file and an allowlisted dir must both stay silent."""
    doc = _write_fixture(_v21_base())
    root = tempfile.mkdtemp(prefix="probe_backup_root_")
    try:
        subprocess.run(["git", "init", "-q", root], check=True, timeout=15)
        os.makedirs(os.path.join(root, "tracked"))
        with open(os.path.join(root, "tracked", "keep.md"), "w") as fh:
            fh.write("kept\n")
        subprocess.run(["git", "-C", root, "add", "tracked/keep.md"],
                       check=True, timeout=15)
        os.makedirs(os.path.join(root, "cache"))       # allowlisted name
        with open(os.path.join(root, "cache", "x.tmp"), "w") as fh:
            fh.write("x\n")
        os.makedirs(os.path.join(root, "newthing"))    # the review candidate
        with open(os.path.join(root, "newthing", "y.md"), "w") as fh:
            fh.write("y\n")
        r = run_probe([doc, "--backup-root=%s" % root])
        assert r.returncode == 0, (
            "backup-coverage is WARN-only, got exit %d\n%s"
            % (r.returncode, r.stdout))
        assert "Backup-coverage sweep:" in r.stdout, (
            "expected the sweep summary line:\n%s" % r.stdout)
        assert re.search(r"\[WARN\].*'newthing/'", r.stdout), (
            "expected a WARN naming 'newthing/':\n%s" % r.stdout)
        for silent in ("'tracked/'", "'cache/'"):
            assert silent not in r.stdout, (
                "%s must not be flagged:\n%s" % (silent, r.stdout))
    finally:
        os.remove(doc)
        shutil.rmtree(root, ignore_errors=True)
    print("  PASS test_backup_coverage_flags_untracked_dir "
          "(candidate WARNs; tracked + allowlisted silent; exit 0)")


def test_backup_coverage_absent_without_root_in_fixture_mode():
    """Fixture runs without --backup-root must skip the sweep entirely
    (live-only check; fixtures opt in via the override)."""
    doc = _write_fixture(_v21_base())
    try:
        r = run_probe([doc])
        assert "Backup-coverage sweep:" not in r.stdout, (
            "sweep must not run on a fixture without --backup-root:\n%s"
            % r.stdout)
    finally:
        os.remove(doc)
    print("  PASS test_backup_coverage_absent_without_root_in_fixture_mode")


def test_declassification_residue_warns():
    """A deal marked active:false whose 'always' term still appears in the
    probed CLAUDE.md or a --ported-copies= file -> WARN (checklist-completeness
    signal), never a hard fail. Exit 0."""
    doc = _write_fixture(_v21_base())
    fd, terms_file = tempfile.mkstemp(suffix="_terms.json", text=True)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(json.dumps({
            "old_deal": {"active": False, "always": ["zebraquartz"]},
        }))
    fd2, copy_file = tempfile.mkstemp(suffix="_ported_CLAUDE.md", text=True)
    with os.fdopen(fd2, "w", encoding="utf-8") as fh:
        fh.write("# Ported copy\n\nStill mentions zebraquartz here.\n")
    try:
        r = run_probe([doc, "--terms=%s" % terms_file,
                      "--ported-copies=%s" % copy_file])
        assert r.returncode == 0, (
            "declassification residue is WARN-only, got exit %d\n%s"
            % (r.returncode, r.stdout))
        assert "old_deal" in r.stdout and "zebraquartz" in r.stdout, (
            "expected a WARN naming the deal and the residual term:\n%s" % r.stdout)
    finally:
        os.remove(doc)
        os.remove(terms_file)
        os.remove(copy_file)
    print("  PASS test_declassification_residue_warns "
          "(residual term in a ported copy -> WARN, exit 0)")


def test_declassification_residue_clean_when_scrubbed():
    """The same declassified deal, but the ported copy has been scrubbed ->
    no WARN, prints the clean summary line."""
    doc = _write_fixture(_v21_base())
    fd, terms_file = tempfile.mkstemp(suffix="_terms.json", text=True)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(json.dumps({
            "old_deal": {"active": False, "always": ["zebraquartz"]},
        }))
    fd2, copy_file = tempfile.mkstemp(suffix="_ported_CLAUDE.md", text=True)
    with os.fdopen(fd2, "w", encoding="utf-8") as fh:
        fh.write("# Ported copy\n\nNothing relevant here.\n")
    try:
        r = run_probe([doc, "--terms=%s" % terms_file,
                      "--ported-copies=%s" % copy_file])
        assert r.returncode == 0
        assert "Declassification-residue sweep: clean" in r.stdout, (
            "expected the clean summary line:\n%s" % r.stdout)
        assert "zebraquartz" not in r.stdout
    finally:
        os.remove(doc)
        os.remove(terms_file)
        os.remove(copy_file)
    print("  PASS test_declassification_residue_clean_when_scrubbed "
          "(scrubbed copy -> clean, exit 0)")


def test_declassification_residue_ignores_active_deals():
    """A deal that is still ACTIVE (or missing the flag -> default-active) is
    out of scope for this check even if its term appears in a ported copy --
    that is check 8's job (the hard-fail leak scan), not this WARN-only sweep."""
    doc = _write_fixture(_v21_base())
    fd, terms_file = tempfile.mkstemp(suffix="_terms.json", text=True)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(json.dumps({
            "live_deal": {"active": True, "always": ["yttriumfalcon"]},
        }))
    fd2, copy_file = tempfile.mkstemp(suffix="_ported_CLAUDE.md", text=True)
    with os.fdopen(fd2, "w", encoding="utf-8") as fh:
        fh.write("# Ported copy\n\nyttriumfalcon appears here too.\n")
    try:
        r = run_probe([doc, "--terms=%s" % terms_file,
                      "--ported-copies=%s" % copy_file])
        assert "yttriumfalcon" not in r.stdout or "declassified deal" not in r.stdout, (
            "an active deal must never be reported by the declassification-"
            "residue sweep:\n%s" % r.stdout)
    finally:
        os.remove(doc)
        os.remove(terms_file)
        os.remove(copy_file)
    print("  PASS test_declassification_residue_ignores_active_deals "
          "(active deal out of scope for this check)")


def test_declassification_residue_absent_without_root_in_fixture_mode():
    """Fixture runs without --ported-copies= (but WITH a declassified deal in
    the terms file) must still just scan CLAUDE.md alone -- no crash, no
    unconditional skip message required, matching check 12's fixture-mode
    contract (opt in via the override; live default only applies with
    live_mode=True, which a fixture run never is)."""
    doc = _write_fixture(_v21_base())
    fd, terms_file = tempfile.mkstemp(suffix="_terms.json", text=True)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(json.dumps({
            "old_deal": {"active": False, "always": ["zebraquartz"]},
        }))
    try:
        r = run_probe([doc, "--terms=%s" % terms_file])
        assert r.returncode == 0
        assert "Declassification-residue sweep: clean" in r.stdout
    finally:
        os.remove(doc)
        os.remove(terms_file)
    print("  PASS test_declassification_residue_absent_without_root_in_fixture_mode")


def test_declassification_roster_flags_marker_near_term():
    """A declassified deal's term co-occurring with a leftover confidentiality
    marker ([CONFIDENTIAL], (CONFIDENTIAL, 'must never appear externally')
    within a small line window in a --roster-files= file -> WARN, exit 0."""
    doc = _write_fixture(_v21_base())
    fd, terms_file = tempfile.mkstemp(suffix="_terms.json", text=True)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(json.dumps({
            "old_deal": {"active": False, "always": ["zebraquartz"]},
        }))
    fd2, roster_file = tempfile.mkstemp(suffix="_projects.md", text=True)
    with os.fdopen(fd2, "w", encoding="utf-8") as fh:
        fh.write("## Zebraquartz Portfolio\n[CONFIDENTIAL] status: terminated.\n")
    try:
        r = run_probe([doc, "--terms=%s" % terms_file,
                      "--roster-files=%s" % roster_file])
        assert r.returncode == 0, (
            "roster marker residue is WARN-only, got exit %d\n%s"
            % (r.returncode, r.stdout))
        assert "old_deal" in r.stdout and "confidentiality" in r.stdout.lower(), (
            "expected a WARN naming the deal and the marker residue:\n%s" % r.stdout)
    finally:
        os.remove(doc)
        os.remove(terms_file)
        os.remove(roster_file)
    print("  PASS test_declassification_roster_flags_marker_near_term")


def test_declassification_roster_allows_bare_mention_without_marker():
    """A declassified deal's term mentioned in a roster file WITHOUT a
    confidentiality marker nearby must NOT be flagged -- these files are
    SUPPOSED to keep discussing a declassified deal, just without the tags."""
    doc = _write_fixture(_v21_base())
    fd, terms_file = tempfile.mkstemp(suffix="_terms.json", text=True)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(json.dumps({
            "old_deal": {"active": False, "always": ["zebraquartz"]},
        }))
    fd2, roster_file = tempfile.mkstemp(suffix="_projects.md", text=True)
    with os.fdopen(fd2, "w", encoding="utf-8") as fh:
        fh.write("## Zebraquartz Portfolio\nStatus: terminated, declassified, "
                 "now a lender note.\n")
    try:
        r = run_probe([doc, "--terms=%s" % terms_file,
                      "--roster-files=%s" % roster_file])
        assert r.returncode == 0
        assert "old_deal" not in r.stdout, (
            "a bare mention with no marker must not be flagged:\n%s" % r.stdout)
        assert "Declassification-residue sweep: clean" in r.stdout
    finally:
        os.remove(doc)
        os.remove(terms_file)
        os.remove(roster_file)
    print("  PASS test_declassification_roster_allows_bare_mention_without_marker")


def test_declassification_roster_ignores_marker_for_unrelated_active_deal():
    """A confidentiality marker elsewhere in a multi-deal roster file, near a
    DIFFERENT (still-active) deal's term, must not falsely tag the
    declassified deal -- the line-window scope must stay per-deal."""
    doc = _write_fixture(_v21_base())
    fd, terms_file = tempfile.mkstemp(suffix="_terms.json", text=True)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(json.dumps({
            "old_deal": {"active": False, "always": ["zebraquartz"]},
            "live_deal": {"active": True, "always": ["yttriumfalcon"]},
        }))
    fd2, roster_file = tempfile.mkstemp(suffix="_projects.md", text=True)
    with os.fdopen(fd2, "w", encoding="utf-8") as fh:
        fh.write(
            "## Zebraquartz Portfolio\nStatus: declassified, lender note.\n\n\n\n"
            "## Yttriumfalcon Deal\n[CONFIDENTIAL] active acquisition in progress.\n"
        )
    try:
        r = run_probe([doc, "--terms=%s" % terms_file,
                      "--roster-files=%s" % roster_file])
        assert "old_deal" not in r.stdout, (
            "the marker near the UNRELATED active deal must not tag old_deal:\n%s"
            % r.stdout)
    finally:
        os.remove(doc)
        os.remove(terms_file)
        os.remove(roster_file)
    print("  PASS test_declassification_roster_ignores_marker_for_unrelated_active_deal")


def test_declassification_roster_absent_without_override_in_fixture_mode():
    """Fixture runs without --roster-files= must simply scan zero roster files
    (live-only default), matching check 12/13's established contract."""
    doc = _write_fixture(_v21_base())
    fd, terms_file = tempfile.mkstemp(suffix="_terms.json", text=True)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(json.dumps({
            "old_deal": {"active": False, "always": ["zebraquartz"]},
        }))
    try:
        r = run_probe([doc, "--terms=%s" % terms_file])
        assert r.returncode == 0
        assert "roster file(s) checked" in r.stdout
    finally:
        os.remove(doc)
        os.remove(terms_file)
    print("  PASS test_declassification_roster_absent_without_override_in_fixture_mode")


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
            # With 0 usable term sequences the leak check now runs a synthetic matcher
            # self-check instead of going silently inert -- it must announce a PASS.
            assert "self-check: PASS" in r.stdout, (
                "the matcher self-check must run and pass when there is no real "
                "leak target:\n%s" % r.stdout)
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


def test_guard_liveness_real_no_orphans():
    """Check 11 against the LIVE CLAUDE.md / settings.json / scheduled-tasks / pre-push
    shim finds NO orphans: every guard named in the real 'Guards:' line has a live
    invocation point. This is the end-to-end proof the meta-guard closes the exact gap
    that motivated it -- a guard named "active" whose only runner was silently retired.
    A failure here means either an extraction/lookup bug OR a guard genuinely lost its
    runner (e.g. the ora-doctrine-integrity-guard scheduled-task SKILL.md that wires
    governor-drift-probe.py went missing) -- both are real signals, not noise to mute.
    """
    r = run_probe()  # defaults to the real CLAUDE.md (live mode)
    assert r.returncode == 0, (
        "expected exit 0 against real CLAUDE.md, got %d\nSTDOUT:\n%s\nSTDERR:\n%s"
        % (r.returncode, r.stdout, r.stderr))
    assert "Guard liveness:" in r.stdout, (
        "probe did not run the guard-liveness check:\n%s" % r.stdout)
    assert "has no live invocation point found" not in r.stdout, (
        "check 11 found an orphan guard in the live doctrine (a named guard with no "
        "settings.json hook / scheduled-task SKILL.md / pre-push shim runner):\n%s"
        % r.stdout)
    for guard in ("doctrine-integrity-probe.py", "governor-drift-probe.py",
                  "git-prepush-doctrine-gate.py", "eos-telemetry", "eos-plan-gate"):
        line = next((l for l in r.stdout.splitlines()
                     if l.lstrip().startswith("[OK]") and (" " + guard + " ") in l), "")
        assert "live invocation point found" in line, (
            "%s should resolve to a live invocation point:\n%s" % (guard, r.stdout))
    print("  PASS test_guard_liveness_real_no_orphans (5 guards resolve, 0 orphans)")


def test_guard_liveness_fixture_orphan_and_override_excluded():
    """Check 11 on a fixture 'Guards:' line, proving three properties at once:
    (a) a wired guard (eos-telemetry, resolved against the REAL settings.json) is [OK];
    (b) an unwired guard produces the orphan WARN and, being WARN-only this rollout,
        does NOT flip the exit code (mirrors the checks 9/10 WARN-only precedent);
    (c) the eos-plan-gate-style override recipe `touch hooks/sessions/<id>/override`
        -- a second backtick token inside a parenthetical -- is NOT mis-parsed as a
        guard (exactly 2 guards extracted, and 'touch hooks' never printed)."""
    # Real middle-dot (U+00B7) separator between entries, as the live doctrine uses.
    guards = ("Guards: `eos-telemetry` (compliance) · `zzz-orphan-guard.py` "
              "(4+ edits; override `touch hooks/sessions/<id>/override`); all fail open.")
    path = _write_fixture(_guards_fixture(guards))
    try:
        r = run_probe([path])
        assert r.returncode == 0, (
            "guard-liveness is WARN-only; a lone orphan must not flip the exit code, "
            "got %d\nSTDOUT:\n%s\nSTDERR:\n%s" % (r.returncode, r.stdout, r.stderr))
        assert "Guard liveness: 2 guard(s) checked" in r.stdout, (
            "expected exactly 2 guards extracted (override recipe excluded):\n%s" % r.stdout)
        assert ("has no live invocation point found" in r.stdout
                and "zzz-orphan-guard.py" in r.stdout), (
            "expected the unwired guard to be flagged an orphan:\n%s" % r.stdout)
        ok = next((l for l in r.stdout.splitlines()
                   if l.lstrip().startswith("[OK]") and " eos-telemetry " in l), "")
        assert "live invocation point found" in ok, (
            "wired guard eos-telemetry should resolve against the real settings.json:\n%s"
            % r.stdout)
        assert "touch hooks" not in r.stdout, (
            "the override recipe was mis-parsed as a guard (should be shape-filtered):\n%s"
            % r.stdout)
    finally:
        os.remove(path)
    print("  PASS test_guard_liveness_fixture_orphan_and_override_excluded "
          "(2 guards; wired OK, orphan WARN, override excluded, exit 0)")


def test_quick_mode_clean_passes():
    """--quick against the real (clean) CLAUDE.md -> exit 0."""
    r = run_probe(["--quick"])
    assert r.returncode == 0, (
        "expected exit 0 for --quick against real CLAUDE.md, got %d\n%s"
        % (r.returncode, r.stdout))
    assert "QUICK-CHECK OK" in r.stdout, "expected the quick-check OK line:\n%s" % r.stdout
    print("  PASS test_quick_mode_clean_passes")


def test_quick_mode_size_budget_fails():
    """--quick on an over-budget fixture -> exit 1, reports size budget only
    (no skills/leak/guard-liveness output -- proves --quick skips those checks)."""
    path = _write_fixture(_v21_base() + ("word " * 1900) + "\n")
    try:
        r = run_probe(["--quick", path])
        assert r.returncode == 1, (
            "expected exit 1 for over-budget --quick fixture, got %d\n%s"
            % (r.returncode, r.stdout))
        assert "size budget exceeded" in r.stdout, (
            "expected size-budget violation:\n%s" % r.stdout)
        assert "Skills referenced" not in r.stdout, (
            "--quick must skip the skills scan:\n%s" % r.stdout)
        assert "Guard liveness" not in r.stdout, (
            "--quick must skip guard-liveness:\n%s" % r.stdout)
    finally:
        os.remove(path)
    print("  PASS test_quick_mode_size_budget_fails (fails, and skips slow checks)")


def test_quick_mode_bare_date_fails():
    """--quick on a fixture with a bare date -> exit 1, reports it; slug dates exempt."""
    path = _write_fixture(_v21_base() + "- ratified 2026-06-10, do not unify\n")
    try:
        r = run_probe(["--quick", path])
        assert r.returncode == 1, (
            "expected exit 1 for bare-date --quick fixture, got %d\n%s"
            % (r.returncode, r.stdout))
        assert "bare date 2026-06-10" in r.stdout, (
            "expected the specific bare-date violation:\n%s" % r.stdout)
    finally:
        os.remove(path)
    print("  PASS test_quick_mode_bare_date_fails")


def test_quick_mode_clean_fixture_passes():
    """--quick on a clean v2.1 fixture -> exit 0."""
    path = _write_fixture(_v21_base())
    try:
        r = run_probe(["--quick", path])
        assert r.returncode == 0, (
            "expected exit 0 for clean --quick fixture, got %d\n%s"
            % (r.returncode, r.stdout))
    finally:
        os.remove(path)
    print("  PASS test_quick_mode_clean_fixture_passes")


def test_memory_index_long_title_short_hook_no_warn():
    """Regression fix: a long title/filename must NOT trip the check when the
    hook (description after the link) is short -- the bug this fix corrects."""
    fd, path = tempfile.mkstemp(suffix="_MEMORY.md", text=True)
    long_title = "A" * 140
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write("- [%s](some-very-long-filename-that-eats-the-budget.md) -- ok\n" % long_title)
    try:
        r = run_probe(["--memory-index=%s" % path])
        assert r.returncode == 0, (
            "expected exit 0 (WARN-only check), got %d\n%s" % (r.returncode, r.stdout))
        assert "index entry at line 1" not in r.stdout, (
            "a long title with a short hook must NOT warn (regression):\n%s" % r.stdout)
    finally:
        os.remove(path)
    print("  PASS test_memory_index_long_title_short_hook_no_warn")


def test_memory_index_long_hook_warns():
    """A genuinely long HOOK description (past the link) still warns."""
    fd, path = tempfile.mkstemp(suffix="_MEMORY.md", text=True)
    long_hook = "word " * 40  # well over 150 chars
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write("- [Short Title](file.md) -- %s\n" % long_hook)
    try:
        r = run_probe(["--memory-index=%s" % path])
        assert r.returncode == 0, "index check is WARN-only, got %d\n%s" % (r.returncode, r.stdout)
        assert "index entry at line 1" in r.stdout, (
            "a genuinely long hook must still warn:\n%s" % r.stdout)
    finally:
        os.remove(path)
    print("  PASS test_memory_index_long_hook_warns")


def test_memory_index_hookless_entry_no_warn():
    """An entry with no ' -- hook' at all (just a bare link) must not warn or crash."""
    fd, path = tempfile.mkstemp(suffix="_MEMORY.md", text=True)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write("- [Title](file.md)\n")
    try:
        r = run_probe(["--memory-index=%s" % path])
        assert r.returncode == 0, "hookless entry must not fail, got %d\n%s" % (r.returncode, r.stdout)
        assert "index entry at line 1" not in r.stdout, (
            "a hookless entry must not warn:\n%s" % r.stdout)
    finally:
        os.remove(path)
    print("  PASS test_memory_index_hookless_entry_no_warn")


def _load_probe_module():
    import importlib.util
    spec = importlib.util.spec_from_file_location("doctrine_integrity_probe", PROBE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# --- Check 13: doctrine-vs-deliverable identity drift (2026-08-03) ---------
# Regression origin: CLAUDE.md said "Principal" while 38 .docx deliverables, three
# ora-skills sources and build_t1_letterpack.py's outbound signature block all said
# "VP Acquisitions" -- for nearly two months, across two contradictory ratified
# rulings, with no guard noticing. See event_log.md 2026-08-03.

def test_title_normalisation_folds_renderings():
    """The same title written four ways must fold to one key, and a different
    title must NOT fold into it. Without this the probe would flag
    build_t1_letterpack.py's 'Vice President, Acquisitions' as drift against
    CLAUDE.md's 'VP Acquisitions' -- they are the same title."""
    m = _load_probe_module()
    same = ["VP Acquisitions", "VP of Acquisitions", "Vice President, Acquisitions",
            "Vice President of Acquisitions", "  vice  president,  acquisitions  "]
    keys = {m.normalize_title(s) for s in same}
    assert len(keys) == 1, "renderings must fold to one key; got %r" % keys
    assert m.normalize_title("Principal") not in keys, \
        "Principal must not fold into the VP-Acquisitions key"
    print("  PASS test_title_normalisation_folds_renderings")


def test_canonical_title_extracted_from_identity_line():
    m = _load_probe_module()
    doc = ('# doc\n\n## Identity\n'
           '- Gabriel Goldberg, VP Acquisitions, Oxford Realty Advisors (ORA) '
           '-- private family-office industrial real estate. Founder: Eric '
           'Goldberg (father).\n')
    assert m.canonical_identity_title(doc) == m.normalize_title("VP Acquisitions")
    other = doc.replace("VP Acquisitions", "Principal")
    assert m.canonical_identity_title(other) == m.normalize_title("Principal")
    assert m.canonical_identity_title("no identity line here") is None
    print("  PASS test_canonical_title_extracted_from_identity_line")


def test_scan_finds_signature_block_assertion():
    """The real defect shape: name and title on ADJACENT lines in a generator."""
    m = _load_probe_module()
    src = ('def sig(doc):\n'
           '    add(doc, "Gabriel Goldberg", space_after=0)\n'
           '    add(doc, "Vice President, Acquisitions", space_after=0)\n')
    hits = m.scan_title_assertions(src)
    assert len(hits) == 1, "expected one assertion, got %r" % (hits,)
    lineno, raw, norm = hits[0]
    # Report the TITLE's line (3), not the name's (2) -- the title is the token a
    # fix has to edit, so it is the actionable locator.
    assert lineno == 3 and norm == m.normalize_title("VP Acquisitions"), \
        "wrong line/title: %r" % (hits[0],)
    print("  PASS test_scan_finds_signature_block_assertion")


def test_scan_ignores_principal_in_unrelated_prose():
    """'principal' is an ordinary finance word. It must only count when asserted
    as Gabriel's title, or the probe drowns in false positives on loan text."""
    m = _load_probe_module()
    noise = ("The principal amount outstanding is $2.8M. Repayment of principal\n"
             "begins in June. Principal and interest are escrowed separately.\n"
             "Gabriel Goldberg reviewed the note.\n"
             "The principal balance was later written down.\n")
    assert m.scan_title_assertions(noise) == [], \
        "prose 'principal' must not register: %r" % (m.scan_title_assertions(noise),)
    print("  PASS test_scan_ignores_principal_in_unrelated_prose")


def test_drift_detection_is_symmetric_and_quiet_when_aligned():
    m = _load_probe_module()
    canon_vp = m.normalize_title("VP Acquisitions")
    agree = [("letterpack.py",
              'add("Gabriel Goldberg")\nadd("Vice President, Acquisitions")\n')]
    assert m.check_identity_drift(canon_vp, agree) == [], \
        "an equivalent rendering must not be reported as drift"

    conflict = [("settings_template.md", "**Owner:** Gabriel Goldberg, Principal\n")]
    found = m.check_identity_drift(canon_vp, conflict)
    assert len(found) == 1 and "settings_template.md" in found[0], \
        "expected one drift finding, got %r" % (found,)

    # Symmetry: the historical state (canon Principal, emitters VP) must ALSO fire.
    # A one-directional check would have stayed silent for the entire 2-month window.
    canon_pr = m.normalize_title("Principal")
    back = m.check_identity_drift(canon_pr, agree)
    assert len(back) == 1, "reverse drift must fire too; got %r" % (back,)
    print("  PASS test_drift_detection_is_symmetric_and_quiet_when_aligned")


def test_drift_reports_every_conflicting_source_not_just_the_first():
    """38 deliverables drifted at once. Reporting only the first would understate
    the blast radius and let the rest survive a 'fixed it' claim."""
    m = _load_probe_module()
    canon = m.normalize_title("VP Acquisitions")
    srcs = [("a.md", "Gabriel Goldberg, Principal, Oxford Realty Advisors\n"),
            ("b.md", "Gabriel Goldberg, Principal\n"),
            ("c.md", "Gabriel Goldberg, VP Acquisitions\n")]
    found = m.check_identity_drift(canon, srcs)
    assert len(found) == 2, "expected both conflicting sources, got %r" % (found,)
    assert not any("c.md" in f for f in found), "aligned source must not be reported"
    print("  PASS test_drift_reports_every_conflicting_source_not_just_the_first")


def test_compound_role_states_title_in_the_tail():
    """'Gabriel Goldberg, Member / Principal' is a title assertion. Missing it
    let document-assembly's signing-authority line drift unreported."""
    m = _load_probe_module()
    hits = m.scan_title_assertions(
        '- Signing authority: "Gabriel Goldberg, Member / Principal" unless the\n')
    assert [h[2] for h in hits] == [m.normalize_title("Principal")], \
        "compound role must resolve to its tail title; got %r" % (hits,)
    print("  PASS test_compound_role_states_title_in_the_tail")


def test_title_word_before_the_name_is_not_an_assertion():
    """communication-intelligence:213 says '...never valid for this principal.
    Corrected to Gabriel Goldberg / ...'. The word PRECEDES the name and means
    'this person', not a title. Scanning forward-only is what keeps it quiet."""
    m = _load_probe_module()
    prose = ("signed outbound comms as \"Ze Ooba\", an incorrect/retired identity "
             "never valid for this principal. Corrected to Gabriel Goldberg / "
             "`ggoldberg@oxfordra.net` per current routing canon.\n")
    assert m.scan_title_assertions(prose) == [], \
        "a title word before the name must not register: %r" % (
            m.scan_title_assertions(prose),)
    print("  PASS test_title_word_before_the_name_is_not_an_assertion")


def test_title_followed_by_employer_preposition():
    """'Gabriel Goldberg, Principal at Oxford Realty Advisors' IS an assertion --
    found as a false negative by the REFUTE sweep, because 'at' is lowercase and
    the terminator rule rejected it. The preposition alone cannot decide; what
    follows it can. 'principal of the loan' must still stay quiet."""
    m = _load_probe_module()
    pr = m.normalize_title("Principal")
    for txt in ("Gabriel Goldberg, Principal at Oxford Realty Advisors (ORA).\n",
                "User is Gabriel Goldberg, Principal of Oxford Realty Advisors.\n"):
        assert [h[2] for h in m.scan_title_assertions(txt)] == [pr], \
            "employer preposition must register: %r" % (
                m.scan_title_assertions(txt),)
    for txt in ("Gabriel Goldberg reviewed the principal of the loan today.\n",
                "Gabriel Goldberg, principal at the time, signed for it.\n"):
        assert m.scan_title_assertions(txt) == [], \
            "lowercase continuation must stay quiet: %r" % (
                m.scan_title_assertions(txt),)
    print("  PASS test_title_followed_by_employer_preposition")


def test_live_probe_wires_identity_sweep_and_is_non_fatal():
    """End-to-end: the sweep must actually run against the real tree and must be
    WARN-only. Deliberately does NOT assert the tree is clean -- pinning that
    would make this test fixture-shaped, and it would start failing the moment a
    real emitter drifts, which is exactly when the probe is doing its job."""
    r = run_probe()
    assert "Doctrine-vs-deliverable identity" in r.stdout, \
        "sweep did not run in live mode:\n%s" % r.stdout
    assert r.returncode == 0, \
        "identity drift must WARN, never fail the probe:\n%s" % r.stdout
    print("  PASS test_live_probe_wires_identity_sweep_and_is_non_fatal")


def test_selfcheck_positive_and_negative_controls():
    """leak_scan_selfcheck: a clean sample (no synthetic terms) -> ok=True; a sample
    that DOES contain a synthetic term (collision) -> ok=False with a finding."""
    m = _load_probe_module()
    ok, findings = m.leak_scan_selfcheck([("clean", "ordinary CLAUDE doctrine text, no fixtures")])
    assert ok and not findings, "clean sample must pass the self-check; got %r" % findings
    bad = "policy note mentioning Project Halcyon Placeholder in prose"
    ok2, findings2 = m.leak_scan_selfcheck([("bad", bad)])
    assert not ok2 and any("collided" in f or "over-match" in f for f in findings2), (
        "a synthetic-term collision must fail the self-check; got %r" % findings2)
    print("  PASS test_selfcheck_positive_and_negative_controls")


def test_selfcheck_detects_broken_matcher():
    """If contains_run regresses (always False), the POSITIVE control must catch it ->
    ok=False with a NON-FUNCTIONAL finding. This is the assurance the check exists to give."""
    m = _load_probe_module()
    orig = m.contains_run
    try:
        m.contains_run = lambda hay, needle: False  # simulate a broken matcher
        ok, findings = m.leak_scan_selfcheck([("clean", "nothing here")])
        assert not ok and any("NON-FUNCTIONAL" in f for f in findings), (
            "a broken matcher must fail the self-check; got %r" % findings)
    finally:
        m.contains_run = orig
    print("  PASS test_selfcheck_detects_broken_matcher")


def test_no_active_deal_runs_selfcheck_and_passes():
    """Integration: with a 0-active-deal terms file, the probe runs the synthetic
    self-check (instead of going inert) and stays exit 0, announcing a PASS."""
    import json
    terms = {"_meta": {"purpose": "test"},
             "closed_deal": {"label": "t", "active": False, "always": ["zzz-closed"]}}
    fd, tpath = tempfile.mkstemp(suffix="_terms.json", text=True)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(terms, fh)
    doc = _write_fixture(_v21_base())
    try:
        r = run_probe([doc, "--terms=%s" % tpath])
        assert r.returncode == 0, (
            "0-active-deal self-check must keep exit 0, got %d\n%s" % (r.returncode, r.stdout))
        assert "self-check: PASS" in r.stdout, (
            "the probe must announce the matcher self-check PASS:\n%s" % r.stdout)
        assert "[MISSING]" not in r.stdout, "no MISSING expected on a passing self-check:\n%s" % r.stdout
    finally:
        os.remove(doc)
        os.remove(tpath)
    print("  PASS test_no_active_deal_runs_selfcheck_and_passes")


def test_dated_archive_dirs_pruned_from_skill_scan():
    """FALSE-NEGATIVE gap closed 2026-07-24 (same class as governor-drift-probe's).
    SKILL_PRUNE_DIRS matched a dir named EXACTLY '_archive', but the live convention is
    '_archive_<date>[_suffix]'. Claude_Workspace/00_Governance/Scheduled/ holds four such
    dirs with 11 SKILL.md files, so RETIRED skills resolved as PRESENT -- defeating the
    documented intent ("a deleted skill that lingers only in a backup still reports
    MISSING"). Direction matters: on a resolver, an unpruned archive is a false NEGATIVE."""
    m = _load_probe_module()
    assert m._is_pruned_skill_dir("_archive")
    assert m._is_pruned_skill_dir("_ARCHIVE")                      # walk lowercases; be explicit
    assert m._is_pruned_skill_dir("_archive_2026-06-09_retired")
    assert m._is_pruned_skill_dir("_archive_2026-07-12_orphans")
    assert m._is_pruned_skill_dir("_staging_2026-01-01")
    assert m._is_pruned_skill_dir("backups")
    assert m._is_pruned_skill_dir("node_modules")
    # TIGHT: requires the separator, so a live skill dir must NOT be pruned. Over-pruning a
    # resolver is ALSO a false negative (skill reads MISSING when it is present), so both
    # directions are unsafe here -- keep the match anchored to the archive convention.
    assert not m._is_pruned_skill_dir("_archives_live")
    assert not m._is_pruned_skill_dir("archive")
    assert not m._is_pruned_skill_dir("acquisition-underwriting")
    assert not m._is_pruned_skill_dir("loi-generation")
    print("  PASS test_dated_archive_dirs_pruned_from_skill_scan")


def test_archived_skill_no_longer_resolves_e2e():
    """A retired skill living ONLY under _archive_<date>/ must not resolve, while an
    identically-named LIVE skill still does. Built as a temp tree so the assertion does not
    depend on the real workspace's archive contents."""
    m = _load_probe_module()
    import pathlib
    root = pathlib.Path(tempfile.mkdtemp())
    for rel in ("live-skill", "_archive_2026-06-09_retired/retired-skill",
                "_archive_2026-07-12_orphans/nested/deep-retired-skill",
                "_staging_wip/wip-skill", "backups/backed-up-skill"):
        d = root / rel
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text("---\nname: x\ndescription: y\n---\n", encoding="utf-8")
    known, errs, absent = m.collect_skill_dirs([root], m.SKILL_PRUNE_DIRS)
    assert not errs and not absent, (errs, absent)
    assert "live-skill" in known, known
    for gone in ("retired-skill", "deep-retired-skill", "wip-skill", "backed-up-skill"):
        assert gone not in known, "%s resolved out of an archive/backup tree: %s" % (gone, known)
    print("  PASS test_archived_skill_no_longer_resolves_e2e")


def main():
    assert os.path.isfile(REAL_CLAUDE_MD), "real CLAUDE.md not found: %s" % REAL_CLAUDE_MD
    test_dated_archive_dirs_pruned_from_skill_scan()
    test_archived_skill_no_longer_resolves_e2e()
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
    test_cross_file_duplication_fails()
    test_no_duplication_still_ok()
    test_backup_coverage_flags_untracked_dir()
    test_backup_coverage_absent_without_root_in_fixture_mode()
    test_declassification_residue_warns()
    test_declassification_residue_clean_when_scrubbed()
    test_declassification_residue_ignores_active_deals()
    test_declassification_residue_absent_without_root_in_fixture_mode()
    test_declassification_roster_flags_marker_near_term()
    test_declassification_roster_allows_bare_mention_without_marker()
    test_declassification_roster_ignores_marker_for_unrelated_active_deal()
    test_declassification_roster_absent_without_override_in_fixture_mode()
    test_confidential_leak_fails()
    test_terms_shape_failopen()
    test_leak_formatting_and_excerpt_withholding()
    test_guard_liveness_real_no_orphans()
    test_guard_liveness_fixture_orphan_and_override_excluded()
    test_quick_mode_clean_passes()
    test_quick_mode_size_budget_fails()
    test_quick_mode_bare_date_fails()
    test_quick_mode_clean_fixture_passes()
    test_memory_index_long_title_short_hook_no_warn()
    test_memory_index_long_hook_warns()
    test_memory_index_hookless_entry_no_warn()
    test_selfcheck_positive_and_negative_controls()
    test_selfcheck_detects_broken_matcher()
    test_no_active_deal_runs_selfcheck_and_passes()
    test_title_normalisation_folds_renderings()
    test_canonical_title_extracted_from_identity_line()
    test_scan_finds_signature_block_assertion()
    test_scan_ignores_principal_in_unrelated_prose()
    test_drift_detection_is_symmetric_and_quiet_when_aligned()
    test_drift_reports_every_conflicting_source_not_just_the_first()
    test_compound_role_states_title_in_the_tail()
    test_title_followed_by_employer_preposition()
    test_title_word_before_the_name_is_not_an_assertion()
    test_live_probe_wires_identity_sweep_and_is_non_fatal()
    print("ALL DOCTRINE-PROBE TESTS PASS")


if __name__ == "__main__":
    main()
