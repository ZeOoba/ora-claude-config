#!/usr/bin/env python3
"""Tests for governor-drift-probe.py (TDD).

Two layers:
  * UNIT  -- import scan_line() and assert the DETECTION logic is intact: canonical
             governor lines are clean; real DSCR/LTV drift still flags. This is the
             guardrail that the false-positive fix did NOT weaken enforcement.
  * E2E   -- run the probe against the real tree and assert (a) exit 0 and (b) no
             finding cites event_log.md (the append-only narrative log we exclude).

Run: python test-governor-drift-probe.py
Pure stdlib. ASCII-only output (Windows cp1252 console).
"""
import os
import sys
import subprocess
import importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
PROBE = os.path.join(HERE, "governor-drift-probe.py")


def _load_probe_module():
    spec = importlib.util.spec_from_file_location("governor_drift_probe", PROBE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_probe(argv=None):
    cmd = [sys.executable, PROBE]
    if argv:
        cmd += argv
    return subprocess.run(cmd, capture_output=True, text=True)


def test_canonical_clean_unit():
    """A line declaring the canonical governor (DSCR 1.25 / LTV 40) is clean."""
    m = _load_probe_module()
    assert m.scan_line("Acquisition governor (non-negotiable): DSCR >= 1.25x, LTV <= 40%.") == [], \
        "canonical governor line should produce no findings"
    print("  PASS test_canonical_clean_unit")


def test_real_ltv_drift_still_flags_unit():
    """A governor declaration with a WRONG LTV ceiling still flags (enforcement intact)."""
    m = _load_probe_module()
    out = m.scan_line("Hard filter / LTV ceiling <= 65% on every deal.")
    assert any("LTV" in o for o in out), (
        "real LTV drift (65%%) must still flag; got %r" % out)
    print("  PASS test_real_ltv_drift_still_flags_unit")


def test_real_dscr_drift_still_flags_unit():
    """A governor declaration with a WRONG DSCR floor still flags (enforcement intact)."""
    m = _load_probe_module()
    out = m.scan_line("Self-imposed minimum DSCR floor is 1.10x (governor).")
    assert any("DSCR" in o for o in out), (
        "real DSCR drift (1.10x) must still flag; got %r" % out)
    # 1.75 regression sentinel still on.
    assert m.scan_line("legacy governor DSCR 1.75x"), "1.75 DSCR sentinel must stay armed"
    print("  PASS test_real_dscr_drift_still_flags_unit")


def test_dscr_drift_without_trailing_x_flags_unit():
    """A governor DSCR floor written WITHOUT a trailing x/× still flags.

    Real governors in this shop are written "DSCR >= 1.25x", but a drift could be
    introduced as a bare "DSCR floor 1.10" with no multiplier sign. The equality
    check must not depend on the 'x' being present.
    """
    m = _load_probe_module()
    out = m.scan_line("Hard acquisition screen (non-negotiable): DSCR floor 1.10.")
    assert any("DSCR" in o for o in out), (
        "x-less DSCR drift (1.10) must flag; got %r" % out)
    # And with an ascii ">=" comparator (which used to false-trip the scoring sentinel
    # via the "= 1" fragment), both with and without a trailing x:
    out2 = m.scan_line("Minimum DSCR >= 1.15 on every deal (governor).")
    assert any("DSCR" in o for o in out2), (
        "x-less DSCR drift (>=1.15) must flag; got %r" % out2)
    out3 = m.scan_line("Hard filter: DSCR >= 1.10x (governor).")
    assert any("DSCR" in o for o in out3), (
        "ascii-comparator DSCR drift (>=1.10x) must flag; got %r" % out3)
    print("  PASS test_dscr_drift_without_trailing_x_flags_unit")


def test_real_scoring_rubric_still_excluded_unit():
    """A genuine DSCR scoring rubric must NOT be read as governor drift (no FP).

    Guards the RE_SCORING tightening: '=10'/'=8' point assignments and 'N.N-N' bands
    still mark the line as a rubric and exclude it from the equality check.
    """
    m = _load_probe_module()
    rubric = "DSCR scoring (governor-adjacent): >=2.5x=10; 2.0-2.49x=8; 1.5-1.99x=5; <1.25x=0."
    assert m.scan_line(rubric) == [], (
        "scoring rubric should be excluded, not flagged as drift; got %r" % m.scan_line(rubric))
    print("  PASS test_real_scoring_rubric_still_excluded_unit")


def test_canonical_dscr_without_x_clean_unit():
    """The canonical 1.25 (no x) on a governor line is still CLEAN (no over-match)."""
    m = _load_probe_module()
    assert m.scan_line("Governor (non-negotiable): DSCR floor 1.25, LTV ceiling 40%.") == [], \
        "canonical DSCR 1.25 (no x) should not flag"
    print("  PASS test_canonical_dscr_without_x_clean_unit")


def test_non_governor_dscr_prose_not_flagged_unit():
    """A non-declaration prose mention of a deal's DSCR must NOT flag (is_gov gate)."""
    m = _load_probe_module()
    assert m.scan_line("The deal's actual DSCR came in at 1.42 last quarter.") == [], \
        "prose DSCR mention (no governor keyword) should not flag"
    print("  PASS test_non_governor_dscr_prose_not_flagged_unit")


def test_narrative_suppression_is_file_level_not_logic_level():
    """The event_log narrative lines DO trip scan_line() -- proving the suppression is
    a file-scoped exclusion, not a gutting of the detection logic."""
    m = _load_probe_module()
    # The exact shape that false-flagged on 2026-06-09 (event_log:57 financing sleeve).
    out = m.scan_line("did NOT find a governor line (only a 65% LTV financing-scenario "
                      "assumption); governors live in CLAUDE.md.")
    assert out, "scan_line should still detect at the line level; file-level skip does the suppression"
    print("  PASS test_narrative_suppression_is_file_level_not_logic_level")


def test_ltv_correction_note_suppressed_unit():
    """I-4: a legit LTV correction note ("LTV ceiling corrected from 65% to 40%") documents a PAST
    fix landing on canonical 40% -- the old 65% it quotes must NOT flag as live drift. Symmetric
    to the DSCR "corrected from 1.75 → 1.25" note that was already suppressed."""
    m = _load_probe_module()
    notes = [
        "Governor: LTV ceiling corrected from 65% to 40% on 2026-06-03.",
        "LTV ceiling corrected down from 65% to 40% (was wrong in v1).",
        "Hard filter: LTV ceiling corrected from 70% → 40%.",
    ]
    for line in notes:
        assert m.scan_line(line) == [], (
            "LTV correction-to-canonical note must be suppressed; line=%r got=%r"
            % (line, m.scan_line(line)))
    # And the DSCR correction note stays suppressed (regression on the pre-existing behavior).
    assert m.scan_line("DSCR >= 1.25x — governor (corrected from 1.75 → 1.25, G5).") == [], \
        "DSCR correction note must remain suppressed"
    print("  PASS test_ltv_correction_note_suppressed_unit")


def test_ltv_correction_note_does_not_oversuppress_unit():
    """I-4 guard: the note suppressor must be TIGHT (40% as the explicit correction destination),
    so it does NOT silence a REAL drift that merely shares a line with the word 'corrected', and
    an LTV note must NOT suppress a co-located DSCR drift (metric-specific suppression)."""
    m = _load_probe_module()
    # 'corrected ... to 40%' with NO 'from <N>%' is not a ceiling correction -> real 65% still flags.
    out1 = m.scan_line("Hard filter: LTV ceiling 65% (typo corrected to 40% in section 4).")
    assert any("65" in o for o in out1), (
        "real 65%% ceiling must still flag when 40%% is not a from->to correction; got %r" % out1)
    # an LTV correction note must NOT suppress a co-located DSCR drift.
    out2 = m.scan_line("Governor DSCR floor 1.40x; LTV corrected from 70% to 40% last cycle.")
    assert any("1.40" in o for o in out2), (
        "DSCR drift must still flag despite a co-located LTV correction note; got %r" % out2)
    assert not any("70" in o for o in out2), (
        "the corrected-away 70%% must be suppressed; got %r" % out2)
    # span-scoped suppression (not whole-branch): a LIVE 65% ceiling co-located with an UNRELATED
    # correction-to-40 in a later clause must STILL flag -- only the corrected-away value is skipped.
    out3 = m.scan_line("Hard filter: LTV ceiling 65%; basis discount corrected from 30% to 40%.")
    assert any("65" in o for o in out3), (
        "live 65%% ceiling must flag despite an unrelated correction-to-40 clause; got %r" % out3)
    print("  PASS test_ltv_correction_note_does_not_oversuppress_unit")


def test_dscr_correction_note_span_scoped_unit():
    """M-2 symmetry: the DSCR correction-note suppressor is now span-scoped too -- only the
    corrected-away old value (inside a 'corrected from <X> to/→ 1.25' span) is skipped, NOT the
    whole DSCR branch. A genuine note stays clean; a live drift sharing the line still flags."""
    m = _load_probe_module()
    # genuine DSCR correction notes stay suppressed (the real-tree shape + an x-less variant).
    for line in ["DSCR >= 1.25x — governor (corrected from 1.75 → 1.25 on 2026-06-03, G5).",
                 "Hard filter: DSCR floor corrected from 1.40 -> 1.25.",
                 "Governor: DSCR floor corrected from 1.75x → 1.25x."]:  # canonical WITH trailing x
        assert m.scan_line(line) == [], (
            "genuine DSCR correction note must be suppressed; line=%r got=%r"
            % (line, m.scan_line(line)))
    # 'corrected to 1.25' WITHOUT a 'from <X>' is not a from->to note -> a live 1.40 still flags.
    out1 = m.scan_line("Governor DSCR floor 1.40x (cap rate corrected to 1.25 elsewhere).")
    assert any("1.40" in o for o in out1), (
        "live 1.40 drift must flag when 1.25 is not a from->to correction dest; got %r" % out1)
    # a live 1.75 NOT inside a correction span must still trip the sentinel.
    out2 = m.scan_line("DSCR governor 1.75x is the new floor; note 1.25 was corrected earlier.")
    assert any("1.75" in o for o in out2), (
        "live 1.75 must still trip the sentinel when not corrected-away; got %r" % out2)
    # two-clause: genuine correction in clause 1, LIVE drift in clause 2 -> the live one flags.
    out3 = m.scan_line("DSCR floor corrected from 1.75 → 1.25; mezz sleeve DSCR floor 1.10x.")
    assert any("1.10" in o for o in out3), (
        "live mezz 1.10 drift must flag despite a co-located correction note; got %r" % out3)
    assert not any("1.75" in o for o in out3), (
        "the corrected-away 1.75 must stay suppressed; got %r" % out3)
    print("  PASS test_dscr_correction_note_span_scoped_unit")


def test_governor_with_incidental_rubric_fragment_flags_unit():
    """I-1: a GOVERNOR DECLARATION that merely SHARES a line with a single rubric-shaped
    fragment (=N point assignment, "was X-Y" band note, "=0 if below" consequence clause)
    must STILL have its declared DSCR floor checked. The old whole-line RE_SCORING skip
    swallowed all four of these (any single =N/band killed the equality check)."""
    m = _load_probe_module()
    cases = [
        "Governor: DSCR floor 1.10 (was 1.0-1.5 band legacy)",  # bare band fragment
        "Governor DSCR >= 1.10x = 5 points",                    # single =5 assignment
        "Governor DSCR floor 1.10, =0 if below",                # =0 consequence clause
        "Governor DSCR floor 1.10x; <1.25x=0",                  # single rubric tail
    ]
    for line in cases:
        out = m.scan_line(line)
        assert any("DSCR" in o for o in out), (
            "drifted governor (1.10) co-located with a rubric fragment must flag; "
            "line=%r got=%r" % (line, out))
    print("  PASS test_governor_with_incidental_rubric_fragment_flags_unit")


def test_count_gate_not_bypassable_by_appending_rubric_pairs_unit():
    """I-1 hardening: a wrong DSCR floor must NOT escape merely because >=2 rubric pairs
    were appended to the same line to trip the rubric count gate. The declared floor sits
    OUTSIDE every value=points pair, so it must still be checked even on a rubric-looking line."""
    m = _load_probe_module()
    line = ("Acquisition governor: minimum DSCR 1.40x. "
            "(Scoring band ref: >=2.5x=10; 2.0-2.49x=8.)")
    out = m.scan_line(line)
    assert any("1.40" in o for o in out), (
        "wrong floor 1.40 declared outside the rubric pairs must still flag; got %r" % out)
    print("  PASS test_count_gate_not_bypassable_by_appending_rubric_pairs_unit")


def test_multi_pair_rubric_false_positive_guard_unit():
    """The companion guard to the above: a GENUINE multi-entry scoring rubric (>=2 value=points
    pairs) must STILL be excluded -- the fix must not reintroduce the rubric false positive a
    naive span-strip would. Covers the canonical 4-pair rubric and a minimal 2-pair rubric."""
    m = _load_probe_module()
    four = "DSCR scoring (governor-adjacent): >=2.5x=10; 2.0-2.49x=8; 1.5-1.99x=5; <1.25x=0."
    assert m.scan_line(four) == [], (
        "4-pair rubric must stay clean; got %r" % m.scan_line(four))
    two = "Governor DSCR rubric: >=2.5x=10; 2.0-2.49x=8."
    assert m.scan_line(two) == [], (
        "2-pair rubric must stay clean; got %r" % m.scan_line(two))
    print("  PASS test_multi_pair_rubric_false_positive_guard_unit")


def test_canonical_decoy_does_not_hide_dscr_drift_unit():
    """I-2: a drifted DSCR floor must flag even when a CANONICAL value is restated earlier on
    the same line (the decoy). The primary extractor binds to the FIRST decimal after 'dscr'
    (canonical 1.25), so the real value must be picked up via its change/declaration construct."""
    m = _load_probe_module()
    cases = [
        "Acquisition governor: DSCR floor raised from 1.25 to 1.40x.",  # verb from-to pivot
        "Hard filter: minimum DSCR increased to 1.40x (governor).",     # verb-to (no canon)
        "Governor DSCR floor 1.25 -> 1.40x.",                           # arrow pivot
        "Acquisition governor: DSCR floor 1.25 now 1.40x.",             # 'now' pivot (canon-first)
        "Governor: DSCR floor 1.25 then 1.40x.",                        # 'then' pivot
        "Governor: DSCR floor is now 1.40x (was 1.25).",                # 'is now' pivot
    ]
    for line in cases:
        out = m.scan_line(line)
        assert any("1.40" in o for o in out), (
            "drifted DSCR floor 1.40 behind a canonical decoy must flag; line=%r got=%r"
            % (line, out))
    print("  PASS test_canonical_decoy_does_not_hide_dscr_drift_unit")


def test_no_x_pivot_decoy_flags_via_canonical_left_operand_unit():
    """I-3: a no-x DSCR decoy where the canonical 1.25 sits immediately LEFT of an arrow/then/now
    pivot ("DSCR floor 1.25 -> 1.40") must flag. The canonical left-operand is the metric guard
    that replaces the trailing-x requirement for THIS shape: it is what distinguishes a DSCR drift
    edit from an incidental "throughput 2.0 -> 3.5" (left operand 2.0, not canonical)."""
    m = _load_probe_module()
    flag = [
        "Governor DSCR floor 1.25 -> 1.40",       # ascii arrow, no x
        "Governor: DSCR floor 1.25 then 1.40",     # 'then' pivot, no x
        "Acquisition governor DSCR floor 1.25 now 1.40",   # 'now' pivot, no x
    ]
    for line in flag:
        out = m.scan_line(line)
        assert any("1.40" in o for o in out), (
            "no-x canonical-left pivot decoy must flag; line=%r got=%r" % (line, out))
    # The disambiguator must NOT fire when the pivot's left operand is NOT canonical (incidental
    # metric): these stay clean (also re-covered in the incidental-figures guard).
    clean = [
        "Governor: DSCR floor 1.25x; throughput 2.0 -> 3.5 units.",
        "Governor: DSCR 1.25x; occupancy ratio 1.10 -> 1.42 over the year.",
        # M-1 guard: a literal 1.25 + pivot that is NOT a DSCR figure (no 'dscr' on the line).
        "Hard filter governor: schema migrated v1.25 -> 2.00 this quarter.",
        "Acquisition governor: equity multiple 1.25 then 1.60 in the model.",
    ]
    for line in clean:
        assert m.scan_line(line) == [], (
            "non-canonical left operand must not flag; line=%r got=%r" % (line, m.scan_line(line)))
    print("  PASS test_no_x_pivot_decoy_flags_via_canonical_left_operand_unit")


def test_canonical_decoy_does_not_hide_ltv_drift_unit():
    """I-2 (LTV): a drifted LTV ceiling must flag even when 40% is restated earlier on the line.
    LTV detection requires an LTV-adjacent ceiling/max anchor (the metric guard), so the decoy
    must phrase the drift as an LTV ceiling/max -- which is how a real LTV drift edit reads."""
    m = _load_probe_module()
    cases = [
        "Governor: LTV ceiling raised from 40% to 65%.",      # verb from-to pivot
        "Governor: LTV ceiling now 65% (was 40%).",           # 'now' pivot after anchor
        "Hard filter: max LTV 65% (was 40%).",                # max-LTV anchor
        "Governor: LTV ceiling raised from 45% to 65%.",      # non-canonical 'from' (45) must flag
        "Governor: LTV ceiling, revised, 65%.",               # first % after anchor IS the drift
        "Governor: LTV ceiling henceforth set to 65%.",       # I-3: drift >22 chars past anchor
    ]
    for line in cases:
        out = m.scan_line(line)
        assert any(("65" in o) or ("45" in o) for o in out), (
            "drifted LTV ceiling behind a canonical/anchored decoy must flag; line=%r got=%r"
            % (line, out))
    print("  PASS test_canonical_decoy_does_not_hide_ltv_drift_unit")


def test_incidental_figures_not_flagged_unit():
    """I-2 FP guard: an incidental OBSERVED/cap-rate/phase figure on a governor line -- NOT bound
    to a threshold construct -- must NOT flag. This is the false-positive class a naive
    multi-extract reintroduces; the real tree is dense with such figures (cap rates, phase tags,
    deal LTV ranges), so the live probe must stay clean."""
    m = _load_probe_module()
    clean = [
        "Acquisition governor: DSCR floor 1.25x (portfolio came in at 1.42 avg).",
        "Governor: LTV ceiling 40% (deals currently underwritten to 28%).",
        "Hard governor: DSCR >= 1.25x, LTV <= 40% (cap rates 7.0-8.0%, Phase 1.1 done).",
        "Hard filter (non-negotiable): DSCR >= 1.25x at 40% LTV; comps 60-70% of replacement.",
        # real-tree shape: a basis-discount threshold bound to a bare comparator is NOT an LTV.
        "ORA basis buyer: prefer >=25% below replacement, >8% yield; DSCR/LTV governor separate.",
        # change-verb + "from N% to N%" RANGE where N is NOT canonical -> not a decoy, must not flag.
        "Governor note: comps moved within a band from 30% to 38% of cost; DSCR/LTV unchanged.",
        # metric-agnostic keyword/arrow FPs (non-DSCR decimals lack the x; non-LTV %s lack the
        # LTV-adjacent ceiling/max anchor). A realistic combined buy-box line must stay clean:
        "Hard filter: DSCR >= 1.25x, LTV <= 40%, max 7% exit cap, min 8% YoC.",
        "Governor: DSCR 1.25x, LTV 40%; occupancy 80% -> 95%, vacancy 15% -> 8% target.",
        "Governor: DSCR floor 1.25x; rent floor 5.50 psf, clear-height ceiling 32.0 ft.",
        "Governor: DSCR floor 1.25x; throughput 2.0 -> 3.5 units/hr.",
        "Hard filter: DSCR >= 1.25x, LTV <= 40%; LTV ceiling 40%; cap rate 7%.",
        # LTV anchor present but a comma separates an unrelated exit-cap max -> window stops.
        "Governor: max LTV 40%, max 8% exit cap.",
        # connective (not a delimiter) joins the canonical ceiling to another metric: the FIRST
        # percent after the anchor is canonical 40%, so the later figure is left alone.
        "Hard filter: max LTV 40% and 25% minimum basis discount per acquisition.",
        "Governor: LTV ceiling 40% with 8% minimum yield on cost.",
        # I-3 window widened to 40 chars but stops at a clause break, so a following clause's
        # percent is not swept in even without a canonical LTV % right after the anchor.
        "Governor: LTV ceiling per policy; exit cap max 8%, basis discount 25%.",
        "Hard filter: max LTV (see appendix B for the 25% basis-discount schedule).",
    ]
    for line in clean:
        out = m.scan_line(line)
        assert out == [], (
            "incidental figure not bound to a threshold construct must not flag; line=%r got=%r"
            % (line, out))
    print("  PASS test_incidental_figures_not_flagged_unit")


def test_event_log_excluded_e2e():
    """End-to-end: real tree is clean AND no finding cites event_log.md."""
    r = run_probe()
    assert r.returncode == 0, (
        "expected exit 0 (event_log.md excluded), got %d\nSTDOUT:\n%s\nSTDERR:\n%s"
        % (r.returncode, r.stdout, r.stderr))
    assert "event_log.md" not in r.stdout, (
        "event_log.md narrative should not be scanned for governor drift:\n%s" % r.stdout)
    print("  PASS test_event_log_excluded_e2e (exit 0, event_log.md not scanned)")


def main():
    assert os.path.isfile(PROBE), "probe not found: %s" % PROBE
    test_canonical_clean_unit()
    test_real_ltv_drift_still_flags_unit()
    test_real_dscr_drift_still_flags_unit()
    test_dscr_drift_without_trailing_x_flags_unit()
    test_real_scoring_rubric_still_excluded_unit()
    test_canonical_dscr_without_x_clean_unit()
    test_non_governor_dscr_prose_not_flagged_unit()
    test_narrative_suppression_is_file_level_not_logic_level()
    test_ltv_correction_note_suppressed_unit()
    test_ltv_correction_note_does_not_oversuppress_unit()
    test_dscr_correction_note_span_scoped_unit()
    test_governor_with_incidental_rubric_fragment_flags_unit()
    test_count_gate_not_bypassable_by_appending_rubric_pairs_unit()
    test_multi_pair_rubric_false_positive_guard_unit()
    test_canonical_decoy_does_not_hide_dscr_drift_unit()
    test_no_x_pivot_decoy_flags_via_canonical_left_operand_unit()
    test_canonical_decoy_does_not_hide_ltv_drift_unit()
    test_incidental_figures_not_flagged_unit()
    test_event_log_excluded_e2e()
    print("ALL GOVERNOR-PROBE TESTS PASS")


if __name__ == "__main__":
    main()
