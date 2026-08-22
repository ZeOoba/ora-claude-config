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


def test_scan_code_canonical_clean_unit():
    """Code-aware path (2026-06-14): the real capital-config ENFORCEMENT CONSTANTS are clean, and
    the `dscrFloor > 3` sanity ceiling no longer reads as a 3.0 DSCR threshold (the FP class is gone
    because code is routed to scan_code, not the prose scan_line). Numeric equality: 0.4 == 0.40."""
    m = _load_probe_module()
    code = "\n".join([
        "export const CAPITAL_CONFIG = {",        # the real seed object (CAPITAL_CONFIG)
        "  dscrFloor: 1.25,",
        "  ltvCeiling: 0.40,",
        "} as const;",
        "  dscrFloor: number;",                    # interface type annotation -- must NOT flag
        "  if (next.dscrFloor < 1.25) { throw new Error('capital-config: DSCR floor below 1.25 -- refused'); }",
        "  if (next.ltvCeiling > 0.40) { throw new Error('capital-config: LTV ceiling above 0.40 -- refused'); }",
        "  if (next.dscrFloor > 3) { throw new Error('exceeds sane ceiling 3.0 -- likely a fat-finger'); }",
        "    dscrFloor: update.dscrFloor ?? current.dscrFloor,",  # expression RHS -- must NOT flag
    ])
    assert m.scan_code(code) == [], "canonical seed + guard + sanity ceiling must be clean; got %r" % m.scan_code(code)
    assert m.scan_code("if (next.ltvCeiling > 0.4) {}") == [], "0.4 must equal 0.40 (no drift)"
    assert m.scan_code("if (next.dscrFloor < 1.250) {}") == [], "1.250 must equal 1.25 (no drift)"
    assert m.scan_code("  ltvCeiling: .40,") == [], "leading-dot .40 must equal 0.40 (no drift)"
    print("  PASS test_scan_code_canonical_clean_unit")


def test_scan_code_constant_drift_flags_unit():
    """Closes the latent FALSE NEGATIVE: a drifted enforcement CONSTANT flags even if no prose /
    error-string changes (the old probe only validated the message)."""
    m = _load_probe_module()
    assert any("DSCR" in r for _, r, _ in m.scan_code("if (next.dscrFloor < 1.10) {}")), \
        "drifted DSCR floor 1.10 must flag"
    assert any("LTV" in r for _, r, _ in m.scan_code("if (next.ltvCeiling > 0.50) {}")), \
        "drifted LTV ceiling 0.50 must flag"
    print("  PASS test_scan_code_constant_drift_flags_unit")


def test_scan_code_direction_and_inversion_flags_unit():
    """Operator flips and inverted guards are SEMANTIC drift -- must flag; the legit `> 3` sanity
    ceiling must NOT be mistaken for an inverted floor."""
    m = _load_probe_module()
    assert m.scan_code("if (next.dscrFloor <= 1.25) {}"), "dscr '<=' direction drift must flag"
    assert m.scan_code("if (next.ltvCeiling >= 0.40) {}"), "ltv '>=' direction drift must flag"
    assert m.scan_code("if (next.dscrFloor > 1.25) {}"), "inverted dscr floor (>1.25) must flag"
    assert m.scan_code("if (next.ltvCeiling < 0.40) {}"), "inverted ltv ceiling (<0.40) must flag"
    assert m.scan_code("if (next.dscrFloor > 3) {}") == [], "sanity ceiling > 3 must stay clean"
    print("  PASS test_scan_code_direction_and_inversion_flags_unit")


def test_scan_code_ignores_deal_values_unit():
    """scan_code keys ONLY on the enforcement identifiers (dscrFloor / ltvCeiling), so per-deal
    dscr/ltv VALUES -- the latent JSON-sentinel FP (a deal at exactly 1.75) -- never flag."""
    m = _load_probe_module()
    assert m.scan_code('{ "dscr": 1.75, "ltv": 0.54 }') == [], "json deal values must not flag"
    assert m.scan_code("const dscr = 1.10; const ltv = 0.65;") == [], "local deal vars must not flag"
    print("  PASS test_scan_code_ignores_deal_values_unit")


def test_scan_code_seed_literal_drift_flags_unit():
    """BLOCKER fix (adversarial review 2026-06-14): the ratified SEED literal in CAPITAL_CONFIG --
    `dscrFloor: 1.25,` / `ltvCeiling: 0.40,` -- IS the live governor value (a one-char edit there
    weakens the governor). The comparison-only check missed it; the seed (colon) check must flag it.
    Leading-dot form too. NOTE: scan_code flags conditions.ts's legit `dscrFloor: 1.1,` BY DESIGN --
    the FP is avoided by main() ROUTING scan_code ONLY to the governor file, verified by the E2E."""
    m = _load_probe_module()
    assert any("DSCR" in r for _, r, _ in m.scan_code("  dscrFloor: 1.00,")), "seed DSCR 1.00 must flag"
    assert any("LTV" in r for _, r, _ in m.scan_code("  ltvCeiling: 0.75,")), "seed LTV 0.75 must flag"
    assert any("LTV" in r for _, r, _ in m.scan_code("  ltvCeiling: .65,")), "leading-dot seed .65 must flag"
    # proof the check is LIVE (so the E2E green => routing, not a dead check, protects conditions.ts):
    assert m.scan_code("  dscrFloor: 1.1,"), "scan_code must flag a non-canonical seed (live check)"
    print("  PASS test_scan_code_seed_literal_drift_flags_unit")


def test_scan_code_presence_regexes_unit():
    """Deletion guard (main): the presence regexes match a NUMERIC governor declaration (seed OR
    guard) but NOT the bare interface type annotation -- so deleting the value while keeping the
    type does not mask the deletion."""
    m = _load_probe_module()
    assert m.RE_CODE_DSCR_ANY.search("  dscrFloor: 1.25,"), "seed satisfies presence"
    assert m.RE_CODE_DSCR_ANY.search("if (next.dscrFloor < 1.25) {"), "guard satisfies presence"
    assert not m.RE_CODE_DSCR_ANY.search("  dscrFloor: number;"), "type annotation must NOT satisfy presence"
    assert m.RE_CODE_LTV_ANY.search("  ltvCeiling: 0.40,"), "ltv seed satisfies presence"
    assert not m.RE_CODE_LTV_ANY.search("  ltvCeiling: number;"), "ltv type annotation must NOT satisfy presence"
    print("  PASS test_scan_code_presence_regexes_unit")


def test_reverse_order_dscr_floor_flags_unit():
    """Reverse-order gap (2026-07-08): a governor DSCR floor written NUMBER-then-keyword
    ("This 1.40x floor is the acquisition governor") carries no literal 'dscr' AND puts the keyword
    AFTER the value, so RE_DSCR_THRESH (dscr-anchored) and RE_DSCR_DECL (keyword-before-number) both
    miss it. Pre-fix this returned [] (a real false negative); RE_DSCR_DECL_REV closes it. The
    trailing x/× stays REQUIRED, so a rent/height decimal that merely precedes a keyword never trips."""
    m = _load_probe_module()
    out = m.scan_line("This 1.40x floor is the acquisition governor for every deal.")
    assert any("1.40" in o for o in out), (
        "reverse-order DSCR floor 1.40x must flag; got %r" % out)
    for line in ["Hard acquisition governor: the 1.10x minimum stands.",
                 "Governor: 1.15x floor, non-negotiable.",
                 "Acquisition screen: a 1.40X ceiling applies."]:   # uppercase X too (re.I)
        out2 = m.scan_line(line)
        assert any(("1.10" in o) or ("1.15" in o) or ("1.40" in o) for o in out2), (
            "reverse-order DSCR drift must flag; line=%r got=%r" % (line, out2))
    # canonical reverse form stays CLEAN (no over-match):
    assert m.scan_line("This 1.25x floor is the acquisition governor.") == [], \
        "canonical reverse 1.25x floor must not flag"
    print("  PASS test_reverse_order_dscr_floor_flags_unit")


def test_reverse_order_ltv_ceiling_flags_unit():
    """Reverse-order LTV gap: "65% ceiling"/"65% maximum" NUMBER-then-keyword with NO literal 'ltv'
    on the line (so the ltv-gated LTV branch never ran). RE_LTV_CEIL_REV closes it on
    governor-declaration lines. Word set is {ceiling, maximum} only."""
    m = _load_probe_module()
    for line in ["This 65% ceiling is the acquisition governor.",
                 "Hard filter: a 65% maximum applies to every deal.",
                 "Acquisition screen: 55% ceiling, non-negotiable."]:
        out = m.scan_line(line)
        assert any(("65" in o) or ("55" in o) for o in out), (
            "reverse-order LTV ceiling drift must flag; line=%r got=%r" % (line, out))
    # canonical reverse form stays CLEAN.
    assert m.scan_line("Governor: 40% ceiling on every deal.") == [], \
        "canonical reverse 40% ceiling must not flag"
    print("  PASS test_reverse_order_ltv_ceiling_flags_unit")


def test_reverse_order_no_false_positive_unit():
    """The reverse-order path must NOT flag stray numbers with no governor meaning: a bare count, a
    physical ceiling, a rent/height decimal preceding a keyword (no abutting x), and non-LTV percents
    abutting bare 'max' (deliberately excluded from the LTV reverse set). This is the false-positive
    class the fix must avoid (precision over recall)."""
    m = _load_probe_module()
    clean = [
        "40 tenants across the portfolio pay on time.",       # bare count -- no % / x
        "The ceiling is 12 feet in the warehouse.",           # physical ceiling -- no % / x, not is_gov
        "Governor: DSCR floor 1.25x; rent floor 5.50 psf, clear-height ceiling 32.0 ft.",  # no abutting x
        "Hard filter: DSCR >= 1.25x, LTV <= 40%; vacancy 15% max, exit cap 8% max.",  # bare 'max' excluded
        "Acquisition governor: DSCR >= 1.25x, LTV <= 40% (portfolio 1.42x avg, 28% actual).",
    ]
    for line in clean:
        assert m.scan_line(line) == [], (
            "reverse-order path must not false-positive; line=%r got=%r" % (line, m.scan_line(line)))
    print("  PASS test_reverse_order_no_false_positive_unit")


def test_reverse_order_suppression_still_applies_unit():
    """The reverse-order DSCR path honors the SAME suppressors as the forward passes: a portfolio-
    level "1.75x floor" (the ratified blended target, a distinct metric) stays suppressed, while a
    per-deal / acquisition-governor marker VETOES suppression so a real per-deal drift still flags."""
    m = _load_probe_module()
    assert m.scan_line("Portfolio-wide governor: the 1.75x floor is the blended target.") == [], \
        "portfolio-wide reverse 1.75x floor must be suppressed"
    out = m.scan_line("Per-deal acquisition governor: the 1.75x floor now applies.")
    assert any("1.75" in o for o in out), (
        "per-deal reverse 1.75x floor must still flag (veto); got %r" % out)
    print("  PASS test_reverse_order_suppression_still_applies_unit")


def test_reverse_order_refi_suppression_unit():
    """The reverse-order LTV path honors the post-close-refi suppressor: a refi debt-sizing
    "65% maximum" (no acquisition-governor marker, value not declared AS the governor) is suppressed;
    an acquisition-governor marker on the line vetoes suppression so a real drift still flags."""
    m = _load_probe_module()
    suppressed = "Self-imposed refi debt post-close sizing: a 65% maximum against stabilized exit value."
    assert m.scan_line(suppressed) == [], (
        "post-close-refi reverse 65%% maximum must be suppressed; got %r" % m.scan_line(suppressed))
    vetoed = "Refi post-close note, yet the acquisition governor is now a 65% maximum."
    assert any("65" in o for o in m.scan_line(vetoed)), (
        "acq-governor marker must veto refi suppression on the reverse path; got %r" % m.scan_line(vetoed))
    print("  PASS test_reverse_order_refi_suppression_unit")


def test_version_token_not_a_dscr_threshold_unit():
    """2026-07-11 FP fix (root cause 1): a VERSION token ("v3.8") abutting the digits is NOT a DSCR
    threshold -- a real threshold is never written letter-abutted ("floor 1.10", never "v1.10" /
    "spec3.8"). The letter-lookbehind must kill the version-token read WITHOUT weakening detection:
    a real drifted floor sharing a line with a version token must still flag."""
    m = _load_probe_module()
    # the real SKILL.md:50 shape -- v3.8 read as "DSCR 3.8x" (the false positive):
    clean = [
        "- **DSCR floor (per-property governor — v3.8; reported on every UNDERWRITE, not just "
        "at refi sizing):** post-refi DSCR must be ≥1.25x at the market-rate refi terms.",
        "Governor spec v3.8: DSCR floor unchanged at 1.25x.",
        "Hard filter (v2.7): DSCR >= 1.25x on every deal.",
    ]
    for line in clean:
        assert m.scan_line(line) == [], (
            "version token must not read as a DSCR threshold; line=%r got=%r"
            % (line, m.scan_line(line)))
    # REFUTE guard: real drift NEAR a version token still flags.
    out1 = m.scan_line("Hard filter: DSCR floor 1.10x (spec v3.8).")
    assert any("1.10" in o for o in out1), (
        "real 1.10 drift beside a version token must flag; got %r" % out1)
    assert not any("3.8" in o for o in out1), (
        "the v3.8 version token must never flag; got %r" % out1)
    out2 = m.scan_line("Governor v3.8: DSCR floor 1.10.")
    assert any("1.10" in o for o in out2), (
        "x-less 1.10 drift after a version token must flag; got %r" % out2)
    print("  PASS test_version_token_not_a_dscr_threshold_unit")


def test_approximate_tilde_value_not_a_dscr_threshold_unit():
    """2026-08-21 FP fix (ora-skills deal-comparison/SKILL.md:153): a CHANGELOG entry narrating a
    past bug's symptom ("inflating computed DSCR ~1.6x") read as a live DSCR governor declaration
    and blocked the pre-push hook-tests gate.

    Two REFUTE-caught gaps shaped this into its final, span-scoped, THREE-signal design (all
    required together: tilde-glued value + literal "corrected" + a separate plain-1.25 restatement):
      1) A blanket lookbehind (suppress every tilde-glued value, unconditionally) was rejected --
         it would also hide a REAL drift report written the same way ("dscr floor ~1.10x" with no
         companion canonical restatement).
      2) A looser two-signal gate (tilde value + a bare 1.25 ANYWHERE on the line, no "corrected"
         requirement) was ALSO rejected -- "the acquisition dscr floor reads ~1.10x in three files
         -- needs reverting to 1.25x" is an UNRESOLVED drift report that mentions 1.25 without ever
         saying the fix happened, and would have been wrongly suppressed. Requiring "corrected" (the
         same completed-action anchor RE_DSCR_CORRECTION already uses) closes that gap."""
    m = _load_probe_module()
    # the real deal-comparison/SKILL.md:153 shape (trimmed to the relevant clause) -- must be clean:
    assert m.scan_line(
        "(1) DSCR was tested at 40% LTV — the portfolio-aggregate governor, not per-property refi "
        "sizing — inflating computed DSCR ~1.6x and letting deals that would floor-flag in "
        "acquisition-underwriting score clean here; corrected to the LESSER-of-65%-LTV/1.25x-DSCR "
        "basis."
    ) == [], "the real changelog shape must not read as a DSCR threshold"
    # a shorter changelog shape carrying all three required signals -- also clean:
    assert m.scan_line(
        "Symptom under the old code: DSCR read ~1.10, well above the real floor; corrected to the "
        "canonical 1.25x DSCR floor."
    ) == [], "a corrected changelog note with all three signals must not flag"

    # REFUTE gap 1 (closed): unconditional tilde suppression must NOT hide a bare, unresolved report.
    out_bare = m.scan_line("dscr floor ~1.10x now -- must fix.")
    assert any("1.10" in o for o in out_bare), (
        "a bare tilde value with no companion evidence must still flag; got %r" % out_bare)

    # REFUTE gap 2 (closed): tilde + bare 1.25 with NO "corrected" is still an unresolved report,
    # not a changelog note -- must flag, not be suppressed.
    out_unresolved = m.scan_line(
        "the acquisition dscr floor reads ~1.10x in three files -- needs reverting to 1.25x.")
    assert any("1.10" in o for o in out_unresolved), (
        "an unresolved drift report mentioning 1.25 without 'corrected' must still flag; got %r"
        % out_unresolved)

    # Sanity: a genuinely off-canonical value elsewhere on the line, sharing a line with a
    # "corrected"+tilde note but on its OWN un-hedged "dscr" occurrence, is untouched by the
    # tilde suppressor (which is span-scoped to the tilde-glued value only) and still flags.
    out_guard = m.scan_line(
        "Changelog: old code read DSCR ~1.6x; corrected to 1.25x. Unrelated: DSCR floor 1.10x.")
    assert any("1.10" in o for o in out_guard), (
        "a real drift on its own un-hedged dscr occurrence must still flag; got %r" % out_guard)
    assert not any("1.6" in o for o in out_guard), (
        "the ~1.6x changelog figure, with 'corrected'+1.25 present, must not flag; got %r"
        % out_guard)
    print("  PASS test_approximate_tilde_value_not_a_dscr_threshold_unit")


def test_tilde_hedge_corrected_word_boundary_and_directional_unit():
    """ROUND-1 INDEPENDENT REVIEW (2026-08-22): the first cut of the tilde-hedge suppressor
    gated on `"corrected" in low` -- a bare, whole-line, non-directional substring test. Two
    real false negatives followed, both on a Hard-Invariant-4 guard whose stated bias is
    detection over silence:
      1) "un**corrected**" contains the substring "corrected", so a drift report that
         literally says it is NOT fixed was wrongly suppressed.
      2) The gate had no directionality or per-span binding: an unrelated "corrected" earlier
         on the line (describing a DIFFERENT fix), or "corrected" preceding the tilde value
         itself (the NEW/bad figure being hedged, not the old one), or a second still-broken
         tilde value sharing a line with one genuinely-fixed value, could all ride an
         unrelated "corrected" token into silent suppression.
    Fixed by requiring the WORD-BOUNDARY token "corrected" to appear AFTER each tilde value
    individually, within a bounded reach (_tilde_hedge_suppressed_spans)."""
    m = _load_probe_module()
    # gap 1: "uncorrected" must not satisfy the completed-action anchor.
    out1 = m.scan_line(
        "dscr floor still reads ~1.10x across three skills, uncorrected; canonical is 1.25x.")
    assert any("1.10" in o for o in out1), (
        "an explicitly UNcorrected drift report must still flag; got %r" % out1)
    # gap 2a: "corrected to ~1.40x" -- the hedged value IS the new/bad figure, not a symptom
    # of an already-fixed one. "corrected" precedes it, so directionality must not suppress it.
    out2a = m.scan_line("dscr floor corrected to ~1.40x, was 1.25x previously.")
    assert any("1.40" in o for o in out2a), (
        "a tilde-hedged value that is ITSELF the new drift (corrected TO it) must still flag; "
        "got %r" % out2a)
    # gap 2b: an unrelated, earlier "corrected" (fixing something else entirely) must not arm
    # suppression for a DSCR drift later on the same line.
    out2b = m.scan_line(
        "audit: the ltv typo was corrected to 40%; separately the dscr floor now reads ~1.10x "
        "vs the canonical 1.25x -- still open.")
    assert any("1.10" in o for o in out2b), (
        "an unrelated earlier 'corrected' must not mask a real drift later on the line; got %r"
        % out2b)
    # gap 2c: two tilde values on one line, only the FIRST genuinely followed by "corrected" --
    # the second, still-unfixed value must not inherit the first's suppression.
    out2c = m.scan_line(
        "changelog: symptom dscr ~1.6x corrected to 1.25x; note the live floor also reads "
        "~1.40x dscr minimum, unfixed.")
    assert not any("1.6" in o for o in out2c), (
        "the genuinely-corrected ~1.6x symptom must stay suppressed; got %r" % out2c)
    assert any("1.40" in o for o in out2c), (
        "a second, still-unfixed tilde value sharing the line must still flag; got %r" % out2c)
    print("  PASS test_tilde_hedge_corrected_word_boundary_and_directional_unit")


def test_deal_comparison_skill_file_clean():
    """The live deal-comparison SKILL.md (repo copy) must scan CLEAN line-by-line -- the 2026-08-21
    false positive at line 153 (a v1.2 Changelog entry narrating the DSCR-wrong-LTV bug fix, see
    test_approximate_tilde_value_not_a_dscr_threshold_unit)."""
    m = _load_probe_module()
    path = r"C:\Users\Owner\ora-skills\deal-comparison\SKILL.md"
    assert os.path.isfile(path), "skill file not found: %s" % path
    findings = []
    with open(path, encoding="utf-8", errors="replace") as fh:
        for i, raw in enumerate(fh, 1):
            for reason in m.scan_line(raw):
                findings.append((i, reason))
    assert findings == [], (
        "deal-comparison SKILL.md must be clean; got %r" % findings)
    print("  PASS test_deal_comparison_skill_file_clean (0 findings)")


def test_rate_percent_not_a_dscr_threshold_unit():
    """2026-07-11 FP fix (root cause 1b): "DSCR, 7.00% fixed" was read as "DSCR 7.0x" -- the regex
    backtracked to a PARTIAL capture ("7.0" of "7.00") to defeat the (?!\\s*%) percent guard. The
    full-number capture ((?![0-9]) after the value) must kill that, while an actual absurd DSCR
    threshold ("floor 7.0x") still flags."""
    m = _load_probe_module()
    # the real SKILL.md:281 shape:
    clean = ("7. **Debt & Capital Structure** — all-cash close + per-property refi terms "
             "(per UNDERWRITING CONVENTIONS: LESSER of 65% LTV and 1.25x DSCR, 7.00% fixed, "
             "25-yr amort, 5/10-yr term — state which of LTV/DSCR binds), and the "
             "portfolio-aggregate LTV governor check (40% ceiling, STAGE 2.3) stated explicitly.")
    assert m.scan_line(clean) == [], (
        "a percent rate after DSCR must not partial-capture as a threshold; got %r"
        % m.scan_line(clean))
    assert m.scan_line("Governor note: DSCR-linked refi rate 7.00% fixed.") == [], \
        "DSCR-adjacent 7.00%% rate must not flag"
    out = m.scan_line("Governor: DSCR floor 7.0x on every deal.")
    assert any("7.0" in o for o in out), (
        "a real (absurd) DSCR floor 7.0x must still flag; got %r" % out)
    print("  PASS test_rate_percent_not_a_dscr_threshold_unit")


def test_refi_lesser_of_construct_suppressed_unit():
    """2026-07-11 FP fix (root cause 2): a 65% sitting INSIDE the explicit ratified refi-sizing
    construct "LESSER of 65% LTV and 1.25x DSCR" is a refinance-market input, not the acquisition
    governor -- suppressed even when the line carries per-property / dscr-floor markers (which
    legitimately describe the refi rule post-v3.8). The construct's guard is the LITERAL canonical
    1.25x DSCR member: drift EITHER member and the construct no longer suppresses."""
    m = _load_probe_module()
    clean = [
        # SKILL.md:50 (also carries the v3.8 token + "dscr floor" marker):
        "- **DSCR floor (per-property governor — v3.8; reported on every UNDERWRITE, not just "
        "at refi sizing):** post-refi DSCR must be ≥1.25x at the market-rate refi terms in "
        "UNDERWRITING CONVENTIONS (LESSER of 65% LTV per-property and 1.25x DSCR).",
        # SKILL.md:260:
        "  - **LTV-governor check:** the refi LTV assumption on the Inputs tab must be validated "
        "against the stated governor (LESSER of 65% LTV per-property and 1.25x DSCR; UNDERWRITING "
        "CONVENTIONS) via a formula/flag on the Inputs or Returns tab.",
        # SKILL.md:300 (both a LESSER-of pair and a "refis running to 65% LTV"):
        "100% family capital; ~15% portfolio LTV; **Two governors, two levels:** per-property refi "
        "ceiling = LESSER of 65% LTV and 1.25x DSCR (UNDERWRITING CONVENTIONS); portfolio-aggregate "
        "ceiling = 40% LTV (Hard Invariant 4), checked per-deal at STAGE 2.3. At ~15% actual, ORA "
        "carries headroom even with individual refis running to 65% LTV.",
        # SKILL.md:112 (hyphenated/slash form + "refi to 65% LTV"):
        "**A. Portfolio-aggregate LTV governor (RATIFIED — Hard Invariant 4):** compute LTV = "
        "(aggregate debt, including this deal's post-refi debt at the LESSER-of-65%-LTV/1.25x-DSCR "
        "sizing from UNDERWRITING CONVENTIONS) ÷ (aggregate value). This governor is distinct "
        "from the per-property 65% LTV / 1.25x DSCR refi-sizing convention — a single property "
        "can refi to 65% LTV while the portfolio in aggregate stays well under 40%.",
    ]
    for line in clean:
        out = m.scan_line(line)
        assert out == [], (
            "refi-sizing LESSER-of construct must be suppressed; line=%r got=%r" % (line[:90], out))
    # REFUTE guards -- drift either member of the construct and detection returns:
    out1 = m.scan_line("Acquisition LTV ceiling: LESSER of 65% LTV and 1.10x DSCR.")
    assert any("65" in o for o in out1), (
        "a LESSER-of pair whose DSCR member drifted off 1.25x is NOT the ratified construct; "
        "its 65%% must flag; got %r" % out1)
    out2 = m.scan_line("Governor: refi post-close sized to LESSER of 75% LTV and 1.25x DSCR.")
    # 75% inside a canonical-anchored LESSER-of span is a refi-sizing figure (drift of the refi
    # ceiling, not the acquisition governor) -- out of this probe's scope, stays suppressed.
    assert out2 == [], (
        "the refi-sizing ceiling itself is not the acquisition governor; got %r" % out2)
    print("  PASS test_refi_lesser_of_construct_suppressed_unit")


def test_refi_sizing_phrase_suppressed_unit():
    """SKILL.md:8 shapes: "65% LTV refi-sizing figure" / "65% LTV is the PER-PROPERTY refi-sizing
    ceiling" -- a percent NAMED as the refi-sizing figure is suppressed; a bare singular 'governor'
    token near the value vetoes the suppression (a value declared AS the governor must flag)."""
    m = _load_probe_module()
    line8 = ("**Clarified LTV governor scope** — an earlier draft flagged the skill's 65% LTV "
             "refi-sizing figure as conflicting with ORA's 40% LTV governor. Gabriel confirmed "
             "2026-07-11 these are two distinct, non-conflicting governors: **65% LTV is the "
             "PER-PROPERTY refi-sizing ceiling** (unchanged; correctly LESSER-of with 1.25x DSCR "
             "in UNDERWRITING CONVENTIONS), and **40% LTV is a separate PORTFOLIO-AGGREGATE "
             "ceiling** (Hard Invariant 4).")
    assert m.scan_line(line8) == [], (
        "the ratified refi-sizing scope-clarification must be suppressed; got %r" % m.scan_line(line8))
    # REFUTE guard: the same refi words cannot mask a value declared AS the governor.
    out = m.scan_line("Hard screen: the acquisition LTV governor is 65% LTV refi-sizing parity.")
    assert any("65" in o for o in out), (
        "a 65%% declared AS the governor must flag despite refi-sizing phrasing; got %r" % out)
    print("  PASS test_refi_sizing_phrase_suppressed_unit")


def test_canonical_dscr_governor_at_ltv_suppressed_unit():
    """SKILL.md:249 shape: "the 1.25x DSCR governor at 65% LTV" -- the 65% is the refi level AT
    WHICH the canonical DSCR governor applies (the 'governor' token binds to the canonical 1.25x
    DSCR on its left, not to the 65%). Suppressed. A 'governor' token NOT bound to the canonical
    DSCR phrase still vetoes (a real LTV-governor declaration flags)."""
    m = _load_probe_module()
    line249 = ("- **Madison DSCR caution:** owner-user pricing $148–$176/SF makes DSCR "
               "≥1.25x extremely difficult on most sub-$10M Class B/C assets — verify "
               "deal-level DSCR before LOI on every Madison screen. **[Unaffected by the "
               "LTV-governor scope clarification — this caution was already anchored to the "
               "1.25x DSCR governor at 65% LTV, both unchanged.]**")
    assert m.scan_line(line249) == [], (
        "the '1.25x DSCR governor at 65%% LTV' pairing must be suppressed; got %r"
        % m.scan_line(line249))
    # REFUTE guards:
    out1 = m.scan_line("The LTV governor at 65% LTV must hold on every deal.")
    assert any("65" in o for o in out1), (
        "a bare 'LTV governor at 65%%' declaration must flag; got %r" % out1)
    out2 = m.scan_line("Governor: 1.25x DSCR at 65% LTV applies at acquisition close.")
    assert any("65" in o for o in out2), (
        "'governor:' introducing the pair (not the canonical-DSCR-governor phrase) must flag; "
        "got %r" % out2)
    print("  PASS test_canonical_dscr_governor_at_ltv_suppressed_unit")


def test_bps_rate_pricing_tier_suppressed_unit():
    """SKILL.md:196 shape: "−25 bps for stabilized multi-tenant ≥1.40x DSCR" is a refi
    RATE-PRICING TIER (a bps adjustment keyed to a DSCR band), never a governor floor -- suppressed.
    The same 1.40x declared as a floor/governor elsewhere on the line still flags."""
    m = _load_probe_module()
    line196 = ("- **All-cash bid + refi post-close (per-property governor: LESSER of 65% LTV and "
               "1.25x DSCR).** **Refi debt assumptions (2026 defaults):** fixed rate **7.00%** "
               "(band 6.75–7.25% for DSCR/agency-style industrial; +25 bps for sub-$2M or "
               "single-tenant, −25 bps for stabilized multi-tenant ≥1.40x DSCR) · "
               "**25-yr amortization** · refi sized to the LESSER of **65% LTV** (stabilized "
               "value at exit cap, per-property) **and 1.25x DSCR** (the governor — never "
               "exceed). NOTE: the IRR floor and the DSCR floor (Stage 1) are the two floors "
               "computed with debt layered in.")
    assert m.scan_line(line196) == [], (
        "the bps rate-pricing tier + LESSER-of refi sizing must be suppressed; got %r"
        % m.scan_line(line196))
    # REFUTE guard: a 1.40x declared as a floor OUTSIDE the bps tier still flags on the same line.
    out = m.scan_line("Refi post-close pricing: −25 bps at ≥1.40x DSCR — and this "
                      "1.40x floor is the acquisition governor now.")
    assert any("1.40" in o for o in out), (
        "a 1.40x floor declared as the acquisition governor must flag even beside a bps tier; "
        "got %r" % out)
    # REFUTE guard (closed hole, 2026-07-11): a DECLARED floor whose 'governor' token sits ~30
    # chars before the value must not be masked by the bps-tier span (the -40 before-reach).
    out2 = m.scan_line("Governor floor -25 bps tier >=1.10x DSCR is the new per-deal minimum.")
    assert any("1.10" in o for o in out2), (
        "a governor floor phrased through a bps tier must still flag; got %r" % out2)
    print("  PASS test_bps_rate_pricing_tier_suppressed_unit")


def test_perdeal_perproperty_drift_still_flags_unit():
    """Regression (task-mandated): per-deal / per-property GOVERNOR drift must still flag -- the
    refi-construct suppressors must not extend to bare per-property declarations."""
    m = _load_probe_module()
    for line, val in [
        ("Per-deal governor: DSCR floor 1.10x.", "1.10"),
        ("Per-property DSCR floor 1.40x (governor).", "1.40"),
        ("Per-deal governor DSCR 1.75x on every acquisition.", "1.75"),
        ("Hard filter: per-property LTV ceiling 65%.", "65"),
    ]:
        out = m.scan_line(line)
        assert any(val in o for o in out), (
            "per-deal/per-property governor drift must still flag; line=%r got=%r" % (line, out))
    print("  PASS test_perdeal_perproperty_drift_still_flags_unit")


def test_review_hole1_lesser_of_gap_drift_flags_unit():
    """REVIEW HOLE 1: a drift hidden INSIDE a LESSER-of construct's gap must flag -- the earlier
    whole-span suppressor masked it because the canonical 1.25x member still terminated the match.
    Member-scoped suppression + decimal-free gap: the gap drift breaks the match, so both the
    injected floor AND the ceiling member stay visible."""
    m = _load_probe_module()
    out1 = m.scan_line("Per-property governor: LESSER of 65% LTV and DSCR floor 1.10x / 1.25x DSCR.")
    assert any("1.10" in o for o in out1), ("HOLE1a: gap-hidden 1.10 must flag; got %r" % out1)
    assert any("65" in o for o in out1), ("HOLE1a: 65 must flag (construct broken); got %r" % out1)
    out2 = m.scan_line("LESSER of 65% LTV and the governor DSCR floor 1.10x and 1.25x DSCR.")
    assert any("1.10" in o for o in out2), ("HOLE1b: gap-hidden 1.10 must flag; got %r" % out2)
    print("  PASS test_review_hole1_lesser_of_gap_drift_flags_unit")


def test_review_hole2_bps_gap_no_leapfrog_flags_unit():
    """REVIEW HOLE 2: the bps rate-tier gap must not leapfrog a declared floor to reach the tier's
    band value -- a decimal-free gap breaks the match so the injected floor stays visible."""
    m = _load_probe_module()
    out1 = m.scan_line("Minimum DSCR schedule: -25 bps applies at DSCR floor 1.10x for >=1.40x DSCR deals.")
    assert any("1.10" in o for o in out1), ("HOLE2a: 1.10 must flag; got %r" % out1)
    out2 = m.scan_line("Hard filter note (see refi tier schedule): -25 bps DSCR floor 1.10x stabilized >=1.40x DSCR.")
    assert any("1.10" in o for o in out2), ("HOLE2b: 1.10 must flag; got %r" % out2)
    print("  PASS test_review_hole2_bps_gap_no_leapfrog_flags_unit")


def test_review_hole3_paired_gap_drift_flags_unit():
    """REVIEW HOLE 3: a no-x floor hidden in the PAIRED (1.25x DSCR ... N% LTV) gap must flag, and
    the N% member no longer masks either -- decimal-free gap breaks the match."""
    m = _load_probe_module()
    out = m.scan_line("Minimum DSCR: 1.25x DSCR floor 1.10 at 65% LTV.")
    assert any("1.10" in o for o in out), ("HOLE3: 1.10 must flag; got %r" % out)
    assert any("65" in o for o in out), ("HOLE3: 65 must flag; got %r" % out)
    print("  PASS test_review_hole3_paired_gap_drift_flags_unit")


def test_review_hole4_veto_window_and_refi_gate_flags_unit():
    """REVIEW HOLE 4: the +-40 veto window must be REAL (overlap over the whole line), and the bps
    tier must be gated on a refi token. A value declared AS the governor ~34 chars out flags; a
    bps-shaped governor-change note with NO refi context flags."""
    m = _load_probe_module()
    out1 = m.scan_line("Buy note: 65% LTV refi-sizing figure is the governor now.")
    assert any("65" in o for o in out1), ("HOLE4a: declared-governor 65 must flag; got %r" % out1)
    out2 = m.scan_line("Governor ratified change, all deals, notes: -25 bps at >=1.10x DSCR pricing.")
    assert any("1.10" in o for o in out2), ("HOLE4b: no-refi bps 1.10 must flag; got %r" % out2)
    print("  PASS test_review_hole4_veto_window_and_refi_gate_flags_unit")


def test_review_hole5_dscr_extraction_regressions_flags_unit():
    """REVIEW HOLE 5: the version-lookbehind must not silence a letter-glued drift ('changed to1.10'
    -- 'o' abuts, not a version 'v'), and the percent guard must only exclude an ABUTTING percent so
    a space-separated '1.10 %' DSCR multiple still flags. Genuine version token 'v3.8' stays clean."""
    m = _load_probe_module()
    out1 = m.scan_line("Governor DSCR floor changed to1.10 effective now.")
    assert any("1.10" in o for o in out1), ("HOLE5a: letter-glued to1.10 must flag; got %r" % out1)
    out2 = m.scan_line("Governor: minimum DSCR 1.10 %")
    assert any("1.10" in o for o in out2), ("HOLE5b: space-percent 1.10 %% must flag; got %r" % out2)
    # the genuine version token must still NOT flag (FP fix preserved):
    assert m.scan_line("Governor spec v3.8: DSCR floor unchanged at 1.25x.") == [], \
        "v3.8 version token must stay clean"
    print("  PASS test_review_hole5_dscr_extraction_regressions_flags_unit")


def test_followup1_value_dscr_keyword_order_flags_unit():
    """FOLLOW-UP 1: close the pre-existing reverse-order FN for the value->dscr->floor-word shape
    ('1.10x DSCR floor' / '1.10x DSCR minimum') -- a value, then the literal 'dscr', then a
    floor-word AFTER it. RE_DSCR_DECL_REV misses it (dscr between value and keyword) and
    RE_DSCR_THRESH misses it (dscr precedes the value). New matcher feeds the SAME suppressor
    pipeline, so canonical/portfolio/version/rent guards all still apply."""
    m = _load_probe_module()
    for line, val in [
        ("Hard filter: 1.10x DSCR minimum on every deal.", "1.10"),
        ("Acquisition governor: 1.10x DSCR floor per deal.", "1.10"),
        ("Governor screen: 1.40x DSCR ceiling applies.", "1.40"),   # uppercase-insensitive keyword
    ]:
        out = m.scan_line(line)
        assert any(val in o for o in out), (
            "value->dscr->floor-word drift must flag; line=%r got=%r" % (line, out))
    # canonical must NOT flag (canonical-skip suppressor):
    assert m.scan_line("Governor: 1.25x DSCR floor on every deal.") == [], \
        "canonical 1.25x DSCR floor must not flag"
    # portfolio-wide 1.75 must NOT flag (portfolio suppressor + 1.75 sentinel portfolio-qualified):
    assert m.scan_line("Governor: 1.75x DSCR floor (portfolio-wide) is the blended target.") == [], \
        "portfolio-wide 1.75x DSCR floor must not flag"
    # version-glued and rent/height decimals must NOT over-match:
    assert m.scan_line("Governor spec v1.10x DSCR floor note (typo).") == [], \
        "version-glued v1.10 must not flag via the new matcher"
    assert m.scan_line("Governor: DSCR >= 1.25x; rent floor 5.50 psf, clear-height ceiling 32.0 ft.") == [], \
        "rent/height decimals must not match the value->dscr->keyword shape"
    print("  PASS test_followup1_value_dscr_keyword_order_flags_unit")


def test_followup2_refi_to_ltv_veto_tier_unit():
    """FOLLOW-UP 2: RE_REFI_TO_LTV moves to the VETO tier -- a 'refi to N% LTV' declared AS a
    ceiling/governor nearby FLAGS, while the legitimate skill refi-to lines (no governor-declaration
    nearby) stay suppressed. 'hard ceiling'/'hard cap' added as declaration tokens (the skill uses
    'aggregate ceiling'/'per-property ceiling'/'refi-sizing ceiling', never 'hard ceiling')."""
    m = _load_probe_module()
    # MUST FLAG -- value declared as a hard ceiling / governor / acquisition nearby:
    out1 = m.scan_line("Hard filter: every deal must refi to 65% LTV as the hard ceiling.")
    assert any("65" in o for o in out1), (
        "refi-to-65 declared as the hard ceiling must flag; got %r" % out1)
    out2 = m.scan_line("Governor: refi to 65% LTV is the acquisition ceiling now.")
    assert any("65" in o for o in out2), (
        "refi-to-65 declared as the acquisition ceiling must flag; got %r" % out2)
    # MUST NOT FLAG -- the :300-shaped legit refi-to (portfolio governor far, no hard-ceiling decl):
    clean = "Headroom to the portfolio governor even with individual refis running to 65% LTV."
    assert m.scan_line(clean) == [], (
        "legit refi-to-65 (no governor-declaration nearby) must stay suppressed; got %r"
        % m.scan_line(clean))
    print("  PASS test_followup2_refi_to_ltv_veto_tier_unit")


def test_round2_declaring_governor_before_value_flags_unit():
    """ROUND-2 review W1 (was an OLD-flagged -> NEW-silent regression): a real drift whose declaring
    'governor' sits ~22 chars BEFORE a refi-sizing-named member ("acquisition governor was hereby
    raised to 55% LTV refi-sizing parity") must flag. VETO_BEFORE widened 20->28 to catch it while
    staying below the tightest benign real-skill before-gap (:196 at 32). W3: an "Nx DSCR minimum"
    floor declared inside a bps rate tier is a governor statement and must flag despite the tier."""
    m = _load_probe_module()
    out1 = m.scan_line("The acquisition LTV governor was hereby raised to 55% LTV refi-sizing parity.")
    assert any("55" in o for o in out1), (
        "W1: governor-declared 55%% ~22 chars after the keyword must flag; got %r" % out1)
    out2 = m.scan_line("Refi governor floor for all deals was cut hard to -25 bps 1.10x DSCR minimum.")
    assert any("1.10" in o for o in out2), (
        "W3: an 'Nx DSCR minimum' floor inside a bps tier must flag; got %r" % out2)
    # guard the widened window's upper edge: the benign :196-style contrast mention (governor ~32
    # before a refi-sizing member) must STILL be suppressed -- proven by the full-file test, but
    # pinned here directly against the exact shape.
    benign = ("Scope note: conflicting with ORA's 40% LTV governor. Gabriel confirmed later that "
              "65% LTV is the per-property refi-sizing ceiling.")
    assert m.scan_line(benign) == [], (
        "benign 'governor. <32 chars> 65% refi-sizing' contrast must stay suppressed; got %r"
        % m.scan_line(benign))
    print("  PASS test_round2_declaring_governor_before_value_flags_unit")


def test_n6_hard_cap_ceiling_is_gov_gate_unit():
    """N6 (asymmetry from follow-up 2): 'hard cap'/'hard ceiling' were added to the VETO tokens but
    not to GOV_KEYWORDS, so a line whose ONLY governor signal is 'hard cap'/'hard ceiling' was never
    treated as a governor declaration -> nothing scanned it -> SILENT. Fix adds them to GOV_KEYWORDS.
    A drift declared solely via 'hard cap'/'hard ceiling' must now flag."""
    m = _load_probe_module()
    out1 = m.scan_line("1.25x DSCR at 65% LTV is the hard cap now.")
    assert any("65" in o for o in out1), (
        "N6: '... 65% LTV is the hard cap' must flag 65; got %r" % out1)
    out2 = m.scan_line("65% LTV is the hard ceiling.")
    assert any("65" in o for o in out2), (
        "N6: '65% LTV is the hard ceiling' must flag 65; got %r" % out2)
    out3 = m.scan_line("Every deal: DSCR floor 1.10x is our hard cap.")
    assert any("1.10" in o for o in out3), (
        "N6: a DSCR drift on a 'hard cap'-only line must flag; got %r" % out3)
    # canonical on a 'hard cap' line must stay clean (no over-match from the widened gate):
    assert m.scan_line("DSCR >= 1.25x, LTV <= 40% is our hard cap.") == [], \
        "canonical governor on a hard-cap line must not flag"
    print("  PASS test_n6_hard_cap_ceiling_is_gov_gate_unit")


def test_perprop_portfolio_aggregate_pairing_suppressed_unit():
    """RATIFIED 2026-07-11 dual-governor pairing (setup-review finding C4, 2026-07-16): the real
    acquisition-underwriting SKILL.md v4.0 line 10 closes "...governor constants (DSCR 1.25x /
    per-property LTV 65% / portfolio-aggregate LTV 40%) changed" -- documenting two distinct,
    non-conflicting governors this probe only tracks one of (the portfolio-aggregate 40%). Suppressed
    ONLY when the portfolio-aggregate companion on the same line equals the canonical 40 -- the bare
    per-property case (test_perdeal_perproperty_drift_still_flags_unit, no portfolio-aggregate
    companion at all) and a drifted companion both continue to flag in full."""
    m = _load_probe_module()
    real_line = ("No scorecard weights, Stage 1 floors, or governor constants (DSCR 1.25x / "
                 "per-property LTV 65% / portfolio-aggregate LTV 40%) changed.")
    assert m.scan_line(real_line) == [], (
        "ratified per-property/portfolio-aggregate 40%% pairing must be suppressed; got %r"
        % m.scan_line(real_line))
    # REFUTE guard 1: a drifted portfolio-aggregate companion (not 40) must still flag BOTH members --
    # the pairing is only exempt when the canonical portfolio ceiling is actually present.
    drifted = ("governor constants (DSCR 1.25x / per-property LTV 65% / "
               "portfolio-aggregate LTV 45%) changed.")
    out = m.scan_line(drifted)
    assert any("65" in o for o in out) and any("45" in o for o in out), (
        "a drifted portfolio-aggregate companion must leave both members flagged; got %r" % out)
    # REFUTE guard 2: swapping which member carries which label must not accidentally suppress a
    # real drift -- a per-property value paired with a NON-canonical "portfolio-aggregate" figure
    # elsewhere on the line is not the ratified exemption. (The line MUST carry a governor keyword:
    # without one, is_gov is False and the module's long-standing "plain prose mentions of LTV are
    # ignored" gate makes the line unflaggable for reasons unrelated to this pairing -- which would
    # make the guard vacuous rather than protective.)
    out2 = m.scan_line("Governor constants: per-property LTV 70% / portfolio-aggregate LTV 55% "
                       "-- both revised upward.")
    assert any("70" in o for o in out2) and any("55" in o for o in out2), (
        "a non-canonical portfolio-aggregate companion must not suppress the pairing; got %r" % out2)
    print("  PASS test_perprop_portfolio_aggregate_pairing_suppressed_unit")


def test_perprop_member_value_locked_to_ratified_65_unit():
    """VALUE-LOCK: a per-property member that is NOT the ratified 65 flags even when its
    portfolio-aggregate companion IS canonical 40.

    Closes the hole in companion-anchoring alone: without the value-lock, a real per-property drift
    could ride a correctly-stated canonical companion into silence. The aggregate figure is
    canonical here, so the ONLY thing that can flag this line is the per-property member itself.
    """
    m = _load_probe_module()
    for val in ("80", "55", "45", "70"):
        line = ("governor constants (DSCR 1.25x / per-property LTV %s%% / "
                "portfolio-aggregate LTV 40%%) restated." % val)
        out = m.scan_line(line)
        assert any(val in o for o in out), (
            "per-property LTV %s%% must flag despite a canonical-40 companion; got %r" % (val, out))
    print("  PASS test_perprop_member_value_locked_to_ratified_65_unit")


def test_perproperty_non_ratified_ltv_still_flags_unit():
    """ANTI-BLINDING: an unpaired per-property LTV declaration still flags at ANY value.

    This is why the fix is pairing-anchored + value-locked rather than the blanket "per-property
    veto span" the setup-audit note (C4) sketched. Instrumentation: each of these flags ONLY via the
    bare-proximity pass, so a blanket per-property span would silence a REAL per-property drift --
    the catastrophic false-negative class this module is written to avoid. C4 should not be
    implemented as written.
    """
    m = _load_probe_module()
    for line, val in (("Per-property LTV 80% is the governor now.", "80"),
                      ("Governor: per-property LTV 55% hard cap.", "55"),
                      ("Per-property LTV 70% (governor, non-negotiable).", "70"),
                      ("The per-property 45% LTV governor applies to every deal.", "45")):
        out = m.scan_line(line)
        assert any(val in o for o in out), (
            "unpaired per-property LTV %s%% must still flag; line=%r got=%r" % (val, line, out))
    # ... and the ratified 65 itself, when UNPAIRED, is still not exempt: the pairing is what
    # licenses it, not the number alone.
    out65 = m.scan_line("Hard filter: per-property LTV ceiling 65%.")
    assert any("65" in o for o in out65), (
        "unpaired per-property 65%% declared as an acquisition ceiling must flag; got %r" % out65)
    print("  PASS test_perproperty_non_ratified_ltv_still_flags_unit")


def test_perprop_pairing_vetoed_when_declared_as_acquisition_ceiling_unit():
    """VETO tier (Refute Finding 2, 2026-07-16): a MISLABELED pairing still flags.

    The pairing suppresses "per-property LTV 65% / portfolio-aggregate LTV 40%" because 65 and 40
    are both the ratified numbers -- but if the SAME LINE declares the per-property 65 AS the
    acquisition hard ceiling/governor (a labeling error, not a numeric drift), that must still
    surface: the two-level framing is being misapplied even though neither number is wrong. Mirrors
    the veto policy every other named refi-sizing member already uses (_governor_declared_nearby).
    """
    m = _load_probe_module()
    for line in ("the acquisition hard ceiling: per-property LTV 65% / portfolio-aggregate LTV 40%",
                 "per-property LTV 65% is the governor now / portfolio-aggregate LTV 40%"):
        out = m.scan_line(line)
        assert any("65" in o for o in out), (
            "per-property 65%% declared AS the acquisition ceiling must flag despite a canonical "
            "companion; line=%r got=%r" % (line, out))
    # And the ordinary, correctly-framed pairing (no nearby ceiling/governor declaration on the
    # per-property member) must stay suppressed -- this is a VETO, not a blanket re-flag.
    assert m.scan_line("No scorecard weights or governor constants (DSCR 1.25x / per-property LTV "
                       "65% / portfolio-aggregate LTV 40%) changed.") == [], \
        "the ordinary ratified pairing must remain suppressed"
    print("  PASS test_perprop_pairing_vetoed_when_declared_as_acquisition_ceiling_unit")


def test_dated_audit_memory_file_excluded_unit():
    """Dated audit/project memory files NARRATE findings -- they do not declare a live governor.

    The 2026-07-16 setup-audit file tripped the probe on the very line describing this false
    positive. The exemption already existed in intent but was hardcoded to one filename; it is now a
    pattern (mirroring EVENT_LOG_ARCHIVE_RE). Kept tight so live doctrine files stay in scope.
    """
    m = _load_probe_module()
    skipped = ("project_claude-setup-audit-2026-07-16.md",
               "project_claude-md-formal-audit-2026-07-08.md",
               "project_claude-setup-audit-2026-07-09.md")
    for bn in skipped:
        assert m.DATED_AUDIT_RE.match(bn), "dated audit file must be exempt: %s" % bn
    scanned = ("project_replacement_cost_benchmark_unratified.md",  # live doctrine, no date
               "standards.md", "rules.md", "firm.md", "CLAUDE.md",
               "project_oxfordra_seo_audit_2026-07.md")             # partial date -> still scanned
    for bn in scanned:
        assert not m.DATED_AUDIT_RE.match(bn), "live/doctrine file must NOT be exempt: %s" % bn
    # The exemption is FILE-scoped, not logic-level: the narrative line still trips scan_line().
    audit_line = ('- **C4 -- governor-drift probe FP** on "per-property LTV 65%" '
                  '(ratified distinct governor 2026-07-11) -> memory-integrity RED daily.')
    assert m.scan_line(audit_line), (
        "detection logic must be intact -- the audit line is excluded by FILE, not by gutting scan_line")
    print("  PASS test_dated_audit_memory_file_excluded_unit")


def test_acquisition_underwriting_skill_file_clean():
    """The live acquisition-underwriting SKILL.md (repo copy) must scan CLEAN line-by-line --
    the 10 false positives of 2026-07-11 (lines 8, 50, 112, 196, 249, 260, 281, 300)."""
    m = _load_probe_module()
    path = r"C:\Users\Owner\ora-skills\acquisition-underwriting\SKILL.md"
    assert os.path.isfile(path), "skill file not found: %s" % path
    findings = []
    with open(path, encoding="utf-8", errors="replace") as fh:
        for i, raw in enumerate(fh, 1):
            for reason in m.scan_line(raw):
                findings.append((i, reason))
    assert findings == [], (
        "acquisition-underwriting SKILL.md must be clean; got %r" % findings)
    print("  PASS test_acquisition_underwriting_skill_file_clean (0 findings)")


def test_test_files_excluded_from_scan_unit():
    """Pre-existing false positive (2026-07-08): the probe scanned maintenance/_tests/ fixture files
    that intentionally quote off-canonical governor values ("[GOVERNOR DRIFT] DSCR 1.20") to test
    OTHER gates -- the same class as the probe's own already-skipped test file. _is_test_file() now
    excludes the _tests/ subtree and sibling python test modules so those fixtures never read as
    live drift."""
    m = _load_probe_module()
    assert m._is_test_file(r"C:\Users\Owner\.claude\maintenance\_tests\test_git_prepush_doctrine_gate.py")
    assert m._is_test_file("/home/x/.claude/maintenance/_tests/anything.json")
    assert m._is_test_file(r"C:\Users\Owner\.claude\maintenance\test-doctrine-integrity-probe.py")
    assert m._is_test_file("/x/maintenance/test_open_sessions_probe.py")
    assert m._is_test_file("/x/foo_test.py")
    # real governor homes must NOT be treated as test files:
    assert not m._is_test_file(r"C:\Users\Owner\.claude\projects\...\memory\standards.md")
    assert not m._is_test_file("/x/.claude/CLAUDE.md")
    assert not m._is_test_file("/x/oxford-command-center/src/capital-config.ts")
    print("  PASS test_test_files_excluded_from_scan_unit")


def test_event_log_excluded_e2e():
    """End-to-end: real tree is clean AND no finding cites event_log.md."""
    r = run_probe()
    assert r.returncode == 0, (
        "expected exit 0 (event_log.md excluded), got %d\nSTDOUT:\n%s\nSTDERR:\n%s"
        % (r.returncode, r.stdout, r.stderr))
    assert "event_log.md" not in r.stdout, (
        "event_log.md narrative should not be scanned for governor drift:\n%s" % r.stdout)
    print("  PASS test_event_log_excluded_e2e (exit 0, event_log.md not scanned)")


def test_active_work_claims_pruned_unit():
    """2026-08-22 FP fix, found while landing the tilde-hedge changelog fix above:
    hooks/active-work/*.json (claim_work.py's ephemeral cross-session claim broadcasts) is the
    SAME narrative-artifact class as event_log.md/MEMORY.md -- a claim's free-text `description`
    legitimately quotes whatever bug it's about, and a --force takeover additionally embeds the
    displaced claim's own description verbatim in `prior_claim`. This session's OWN claim file,
    describing this exact fix, ended up quoting 'inflating computed DSCR ~1.6x' and self-triggered
    the probe the moment it was written -- pruned by directory name, same as _archive/_staging."""
    m = _load_probe_module()
    assert m._is_pruned_dir("active-work")
    # Tight: requires the exact directory name, so an unrelated dir is never over-pruned
    # (suppression is a false NEGATIVE on a governor guard).
    assert not m._is_pruned_dir("active-work-archive")
    assert not m._is_pruned_dir("work")
    print("  PASS test_active_work_claims_pruned_unit")


def test_active_work_claims_excluded_e2e():
    """End-to-end companion to test_event_log_excluded_e2e: a live claim_work.py claim file
    quoting an off-canonical DSCR value in its free-text description must not fail the probe.

    REGRESSION GUARD (round-1 independent review, 2026-08-22): the original version of this
    test used a payload that ALSO satisfied the tilde-hedge suppressor's own three signals
    (tilde-glued + "corrected" + plain 1.25 companion) -- so it passed even with the
    `active-work` prune reverted, since scan_line() on that text already returns [] on its
    own. This payload is a BARE, unhedged, unsuppressed governor declaration
    ("DSCR governor floor 1.60x") that WOULD flag if actually scanned (verified directly via
    m.scan_line() before wiring it into the file below), so this test can only pass because of
    the prune."""
    m = _load_probe_module()
    would_flag = m.scan_line("DSCR governor floor 1.60x per the audit note.")
    assert would_flag, (
        "test payload must itself be a flaggable governor declaration, or this e2e proves "
        "nothing about the active-work prune -- got %r" % would_flag)
    claims_dir = os.path.join(m.CLAUDE, "hooks", "active-work")
    os.makedirs(claims_dir, exist_ok=True)
    probe_path = os.path.join(claims_dir, "_governor_probe_selftest_claim.json")
    payload = ('{"session_id": "test", "title": "selftest", '
               '"description": "DSCR governor floor 1.60x per the audit note.", '
               '"claimed_at": "2026-08-22T00:00:00"}')
    assert not os.path.exists(probe_path), (
        "stale selftest claim file from a prior run: %s" % probe_path)
    with open(probe_path, "w", encoding="utf-8") as fh:
        fh.write(payload)
    try:
        r = run_probe()
        assert r.returncode == 0, (
            "a claim file quoting an off-canonical value must not fail the probe (proves the "
            "active-work prune, not merely that the payload text is independently suppressed); "
            "got %d\n%s" % (r.returncode, r.stdout))
        assert "active-work" not in r.stdout, (
            "hooks/active-work claim files should not be scanned for governor drift:\n%s"
            % r.stdout)
    finally:
        os.remove(probe_path)
    print("  PASS test_active_work_claims_excluded_e2e (exit 0, active-work not scanned)")


def test_fleet_roots_are_scanned_unit():
    """COVERAGE GAP closed 2026-07-24: build_targets() scanned neither scheduled-task fleet
    root, yet 17 fleet SKILL.md files declare DSCR/LTV. A governor edit landing in
    ora-am-brief or ora-monthly-portfolio-briefing was invisible to the Hard-Invariant-4
    guard. Both roots must now be targets."""
    m = _load_probe_module()
    roots = [os.path.normcase(os.path.normpath(r)) for r, _ in m.build_targets()]
    cc = os.path.normcase(os.path.normpath(os.path.join(m.CLAUDE, "scheduled-tasks")))
    lams = os.path.normcase(os.path.normpath(os.path.join(
        m.HOME, "OneDrive - Oxford Capital Partners", "Documents", "Claude", "Scheduled")))
    assert cc in roots, "CC/MCP fleet root not scanned: %s" % cc
    assert lams in roots, "LAMS/Cowork fleet root not scanned: %s" % lams
    print("  PASS test_fleet_roots_are_scanned_unit")


def test_dated_archive_dirs_pruned_unit():
    """Pre-existing prune gap: iter_files() pruned a dir named EXACTLY '_archive', but the
    live convention is '_archive_<date>[_suffix]' -- 26 such dirs exist, and the archived
    '_archive_2026-04-28' SKILL.md (a 2026-04 draft carrying 'DSCR ... below 1.75 (ORA hard
    governor)') would read as live drift the moment the fleet roots were added."""
    m = _load_probe_module()
    assert m._is_pruned_dir("_archive")
    assert m._is_pruned_dir("_archive_2026-04-28")
    assert m._is_pruned_dir("_archive_2026-07-16_retired-to-ccmcp")
    assert m._is_pruned_dir("_staging")
    assert m._is_pruned_dir("node_modules") and m._is_pruned_dir(".git")
    # Tight: requires the '_archive_' separator, so a live dir merely starting with the
    # letters must NOT be pruned (suppression is a false NEGATIVE on a governor guard).
    assert not m._is_pruned_dir("_archives_live")
    assert not m._is_pruned_dir("_archivedeals")
    assert not m._is_pruned_dir("archive")
    assert not m._is_pruned_dir("skills")
    print("  PASS test_dated_archive_dirs_pruned_unit")


def test_probe_self_description_prose_suppressed_unit():
    """The probe's OWN exit-code documentation necessarily quotes its sentinel value:
    ora-doctrine-integrity-guard/SKILL.md:35 reads '... or the 1.75 regression sentinel'.
    That is prose ABOUT the detector, not a governor declaration. Suppressed by the term of
    art only -- span-scoped, same pattern as the correction-note suppressors."""
    m = _load_probe_module()
    assert m.scan_line(
        "- governor-drift-probe.py: exit 1 = governor DRIFT found (a DSCR threshold != 1.25x "
        "or LTV ceiling != 40% somewhere, or the 1.75 regression sentinel) with the offending "
        "file:line; exit 2 = PROBE ERROR.") == [], "probe self-description must not self-flag"
    print("  PASS test_probe_self_description_prose_suppressed_unit")


def test_sentinel_suppression_does_not_hide_real_drift_unit():
    """ANTI-SUPPRESSION GUARD (the one that matters). Suppression on a governor guard is a
    false NEGATIVE, so the 1.75-sentinel-prose exclusion must be inert against any real
    declaration -- including a line that also mentions the sentinel."""
    m = _load_probe_module()
    assert m.scan_line("Acquisition governor: DSCR floor 1.75x.") != [], "bare drift must flag"
    assert m.scan_line("DSCR governor is now 1.75 per the new policy.") != []
    # sentinel prose on the SAME line must not launder a separate live declaration
    assert m.scan_line(
        "The 1.75 regression sentinel exists because the DSCR governor floor is 1.75x.") != [], \
        "sentinel prose must not launder a real drift sharing the line"
    # the phrase must be the probe's term of art, not any nearby 'sentinel' token
    assert m.scan_line("DSCR governor 1.75 sentinel value for the portfolio floor.") != []
    # REFUTE-pass finding (2026-07-24): appending the exact suppressed phrase to a real
    # declaration is NOT an evasion -- the suppressor silences only branch 1 (the loose
    # proximity sentinel); every explicit-declaration branch stays armed and catches it via
    # "DSCR governor threshold 1.75x != canonical 1.25x". This asymmetry is the whole reason
    # the suppression is safe; assert it so a future refactor cannot quietly remove it.
    assert m.scan_line("DSCR governor floor 1.75 regression sentinel") != [], \
        "explicit-declaration branches must stay armed through the sentinel suppressor"
    print("  PASS test_sentinel_suppression_does_not_hide_real_drift_unit")


def test_fleet_skill_drift_would_flag_e2e():
    """End-to-end: a real drifted governor written into a fleet SKILL.md is now caught.
    Uses a temp dir shaped like a fleet task folder, scanned through iter_files+scan_line
    exactly as main() does."""
    import tempfile
    m = _load_probe_module()
    root = tempfile.mkdtemp()
    live = os.path.join(root, "ora-fake-task")
    arch = os.path.join(root, "_archive_2026-04-28", "ora-old-task")
    os.makedirs(live)
    os.makedirs(arch)
    drift = "Screen every deal against the DSCR floor of 1.10x and an LTV ceiling of 65%.\n"
    for d in (live, arch):
        with open(os.path.join(d, "SKILL.md"), "w", encoding="utf-8") as fh:
            fh.write("---\nname: t\ndescription: d\n---\n\n" + drift)
    seen = []
    for path in m.iter_files(root, (".md",)):
        with open(path, encoding="utf-8", errors="replace") as fh:
            for raw in fh:
                if m.scan_line(raw):
                    seen.append(path)
    assert any("ora-fake-task" in p for p in seen), "live fleet drift missed: %s" % seen
    assert not any("_archive_2026-04-28" in p for p in seen), "archived copy must be pruned"
    print("  PASS test_fleet_skill_drift_would_flag_e2e")


def test_decimal_fragment_never_binds_unit():
    """2026-07-29 live FP class: a narrated per-property figure "54.3% LTV" on a governor line let
    the free-floating percent capture bind the FRACTIONAL digits alone -> "LTV governor 3% !=
    canonical 40%", a nonsense value (disposition-ledger.md:38 / historical-evaluations:46).
    The fragment must NEVER bind; the FULL decimal must bind instead (and, being non-canonical on a
    governor-keyword line, flags AS ITSELF -- garbage killed, detection preserved; the live ledger
    files are additionally file-exempt, which test_ledger_files_excluded_source_pin covers)."""
    m = _load_probe_module()
    line = ("Park National loan, 54.3% LTV (exceeds 40% governor -- see event_log.md "
            "2026-07-29, ACCEPTED)")
    out = m.scan_line(line)
    assert not any("governor 3%" in r or "governor 6%" in r for r in out), \
        "fractional fragment bound as an LTV value: %s" % out
    assert any("54.3" in r for r in out), \
        "full decimal must bind (detection preserved) on a governor line: %s" % out
    # canonical restated on the same line ("40% governor") must NOT flag
    assert not any("governor 40%" in r for r in out), "canonical 40 misflagged: %s" % out
    print("  PASS test_decimal_fragment_never_binds_unit")


def test_decimal_ltv_drift_still_flags_unit():
    """A genuinely drifted DECIMAL ceiling previously bound a garbage fragment or nothing at all;
    with the decimal-capture fix it must flag with its true value via BOTH word orders."""
    m = _load_probe_module()
    out = m.scan_line("Hard filter: LTV ceiling <= 42.5% on every deal (governor).")
    assert any("42.5" in r for r in out), "comparator-bound decimal drift missed: %s" % out
    out2 = m.scan_line("This 42.5% ceiling is the acquisition governor.")
    assert any("42.5" in r for r in out2), "reverse-order decimal drift missed: %s" % out2
    print("  PASS test_decimal_ltv_drift_still_flags_unit")


def test_canonical_decimal_forty_clean_unit():
    """"40.0%" is numerically canonical -- the numeric compare must not flag it."""
    m = _load_probe_module()
    out = m.scan_line("Acquisition governor (non-negotiable): LTV <= 40.0%.")
    assert out == [], "canonical 40.0%% misread as drift: %s" % out
    print("  PASS test_canonical_decimal_forty_clean_unit")


def test_dated_review_memory_file_excluded_unit():
    """2026-07-29 REFUTE ruling: a 'review' token in DATED_AUDIT_RE was REJECTED (it would sweep in
    project_*_doctrine_review_*.md -- a doctrinal home, FN-biased). The one live review-narrative
    file is exempt by EXACT NAME in skip_names instead; the RE must NOT match review files."""
    m = _load_probe_module()
    assert not m.DATED_AUDIT_RE.match(
        "project_historical_evaluations_acquisition_review_2026-07-29.md"), \
        "'review' pattern token must stay rejected (REFUTE 2026-07-29)"
    assert not m.DATED_AUDIT_RE.match(
        "project_acquisition_underwriting_doctrine_review_2026-07-18.md"), \
        "doctrine-review plan files must stay IN SCOPE"
    for bn in ("standards.md", "rules.md", "firm.md",
               "project_replacement_cost_benchmark_unratified.md"):
        assert not m.DATED_AUDIT_RE.match(bn), "live/doctrine file must NOT be exempt: %s" % bn
    with open(PROBE, "r", encoding="utf-8") as fh:
        src = fh.read()
    assert '"project_historical_evaluations_acquisition_review_2026-07-29.md"' in src, \
        "exact-name exemption for the historical-evaluations review file missing from skip_names"
    print("  PASS test_dated_review_memory_file_excluded_unit")


def test_unit_interval_ltv_flags_unit():
    """REFUTE residual #1 hardening: unit-interval notation on a governor line ("LTV ceiling
    0.65%" -- a human porting ltvCeiling: 0.65 into prose) must flag loudly, not drop silently."""
    m = _load_probe_module()
    out = m.scan_line("Hard filter: LTV ceiling 0.65% on every deal (governor).")
    assert any("0.65" in r for r in out), "unit-interval LTV drift dropped silently: %s" % out
    print("  PASS test_unit_interval_ltv_flags_unit")


def test_ledger_files_excluded_source_pin():
    """disposition-ledger.md / deal-decision-ledger.md are append-only decision ledgers -- the same
    narrative class as event_log.md. skip_names is main()-local, so this pins the exemption at
    SOURCE level (a rename or accidental removal breaks this test loudly)."""
    with open(PROBE, "r", encoding="utf-8") as fh:
        src = fh.read()
    for name in ("disposition-ledger.md", "deal-decision-ledger.md"):
        assert '"%s"' % name in src, "ledger exemption missing from skip_names: %s" % name
    print("  PASS test_ledger_files_excluded_source_pin")


def test_intervening_qualifier_dscr_floor_flags_unit():
    """GAP (2026-08-11): GOV_KEYWORDS held the CONTIGUOUS literal 'dscr floor', so any qualifier
    between the metric and its floor-word defeated the is_gov gate and the whole equality branch
    was skipped. 'DSCR hard floor 1.40x' is the exact phrasing the 2026-08-11 Notion defect used
    ('hard floor 1.75'), so this false negative sat on the most likely real-world drift wording."""
    m = _load_probe_module()
    for line in ("DSCR hard floor 1.40x per property.",
                 "DSCR absolute floor 1.40x per property.",
                 "Per-property DSCR minimum floor 1.40x."):
        out = m.scan_line(line)
        assert any("DSCR" in o for o in out), (
            "drifted DSCR floor with an intervening qualifier must flag: %r -> %r" % (line, out))
    print("  PASS test_intervening_qualifier_dscr_floor_flags_unit")


def test_ratified_perproperty_refi_ceiling_prose_stays_clean_unit():
    """REGRESSION PIN for the reverted LTV half (2026-08-11). Extending the same intervening-
    qualifier pairing to LTV armed prose describing the RATIFIED per-property 65% refi ceiling
    (debt-maturity.DESIGN.md:18) and flagged 65 != 40 -- a false positive on a legitimate figure,
    caught by the E2E test. The LTV half was reverted; this pins the line that exposed it so a
    future LTV attempt fails HERE, at the unit layer, instead of surfacing as a whole-tree E2E
    break. Closing the LTV gap requires widening LTV suppression first (see probe comment)."""
    m = _load_probe_module()
    line = "| Per-property LTV vs the **65% refi ceiling** | **No** (warehouse side) |"
    assert m.scan_line(line) == [], (
        "ratified 65%% per-property refi-ceiling prose must not flag: %r" % (m.scan_line(line),))
    print("  PASS test_ratified_perproperty_refi_ceiling_prose_stays_clean_unit")


def test_perproperty_refi_ceiling_standalone_bullet_stays_clean_unit():
    """REGRESSION PIN (governor-drift-probe.py false positive, live on main): the ratified
    per-property refi-sizing ceiling declared on its OWN bullet -- with no same-line
    portfolio-aggregate 40% companion and no same-line "LESSER of ... DSCR" construct, because
    doctrine legitimately states the two governors on SEPARATE bullets -- escaped every existing
    suppressor and flagged "LTV governor 65%% != canonical 40%%".

    Root cause (acquisition-buy-box-v1.md:31): the literal "LTV ceiling" token arms is_gov (a
    GOV_KEYWORDS hit); the parenthetical "(per-property refi sizing)" immediately after "ceiling"
    truncates RE_LTV_ANCHOR's scan window at the "(" clause-splitter, so the anchor pass never
    reads the 65%% at all; the line falls through to the reverse bare-proximity pass
    (RE_LTV_NEAR, "65%%** LTV"), which had no per-property/refi framing suppressor for a
    STANDALONE mention -- every existing one requires either the portfolio-aggregate companion on
    the same line (the 2026-07-16 pairing suppressor) or a same-line refi construct (LESSER-of /
    refi-to / DSCR-paired). This was KNOWN GAP 2 in the probe's own comments, deliberately
    deferred pending a reviewed change -- this is that change.

    This exact wording (acquisition-buy-box-v1.md:31-32, split across two lines by markdown
    wrapping) is scanned ONE LINE AT A TIME by scan_line(), so the test reproduces line 31 alone,
    exactly as the probe sees it."""
    m = _load_probe_module()
    line = ("- **LTV ceiling (per-property refi sizing):** **≤ 65%** LTV at stabilized "
            "exit-cap value. Refi debt")
    out = m.scan_line(line)
    assert out == [], (
        "ratified per-property refi-sizing ceiling on its own bullet must not flag; got %r" % out)
    # Hyphenated doctrine spelling (SKILL.md house style: "refi-sizing") must be equally clean.
    line_hyphen = "LTV ceiling (per-property refi-sizing): <= 65% LTV at stabilized exit value."
    out_hyphen = m.scan_line(line_hyphen)
    assert out_hyphen == [], (
        "hyphenated 'refi-sizing' spelling must not flag either; got %r" % out_hyphen)
    print("  PASS test_perproperty_refi_ceiling_standalone_bullet_stays_clean_unit")


def test_perproperty_refi_ceiling_standalone_drift_still_flags_unit():
    """VALUE-LOCK guard for the fix above: a per-property refi-sizing ceiling that has actually
    DRIFTED off the ratified 65%% -- still on its own bullet, still no aggregate companion -- must
    still flag. The suppressor is locked to the literal ratified value, not to the "per-property
    refi sizing" phrase alone, so this is the anti-blinding counterpart to
    test_perproperty_non_ratified_ltv_still_flags_unit for the standalone-bullet shape."""
    m = _load_probe_module()
    for val in ("80", "55", "70"):
        line = ("- **LTV ceiling (per-property refi sizing):** **<= %s%%** LTV at stabilized "
                "exit-cap value. Refi debt" % val)
        out = m.scan_line(line)
        assert any(val in o for o in out), (
            "drifted per-property refi-sizing ceiling %s%% must still flag; got %r" % (val, out))
    print("  PASS test_perproperty_refi_ceiling_standalone_drift_still_flags_unit")


def test_perproperty_refi_frame_elsewhere_on_line_does_not_mask_aggregate_drift_unit():
    """ADVERSARIAL FINDING (independent review, round 1, 2026-08-21): the first cut of the
    standalone per-property refi-ceiling fix tested "does RE_PERPROPERTY_REFI_FRAME appear
    ANYWHERE on the line", not whether it actually QUALIFIES the flagged value -- unlike every
    other suppressor in this module, which is span/proximity-scoped. That let a genuinely drifted
    AGGREGATE governor slip through whenever the ratified per-property phrase happened to sit
    elsewhere on the same line (a realistic edit: an author conflating the two governors while
    narrating a change to the aggregate one). Both lines below flag on the pre-fix module and must
    still flag now that the frame is required to sit immediately BEFORE the value it qualifies."""
    m = _load_probe_module()
    for line in (
        "Portfolio LTV ceiling raised to 65% given our per-property refi sizing convention.",
        "Aggregate LTV ceiling 65%; per-property refi sizing unchanged.",
    ):
        out = m.scan_line(line)
        assert any("65" in o for o in out), (
            "aggregate-governor drift to 65%% must still flag even when the ratified per-property "
            "refi-sizing phrase sits elsewhere on the line; line=%r got=%r" % (line, out))
    print("  PASS test_perproperty_refi_frame_elsewhere_on_line_does_not_mask_aggregate_drift_unit")


def test_value_between_metric_and_boundword_flags_unit():
    """GAP NOW CLOSED (2026-08-12). Was pinned as a known gap on 2026-08-11: the
    metric-VALUE-boundword order did not arm, because the value's own decimal is a '.' and the
    qualifier gap class excludes '.' to stop the gate crossing a sentence. "DSCR 1.40x minimum"
    went undetected even though its extractor (RE_DSCR_DECL_REV) existed.

    Closed with a SECOND, value-abutting arming pattern rather than by loosening the first: the
    decimal now lives INSIDE the pattern, so it can never be confused with a sentence boundary.
    The rejected alternative (allow a dot anywhere between digits in the gap) is still rejected --
    it reports "DSCR of 1.42 with a 10 min cure period" as governor drift; see the FP guard test."""
    m = _load_probe_module()
    for line in ("DSCR 1.40x minimum per property.",
                 "DSCR 1.40 floor per property.",
                 "DSCR 1.40x min per property."):
        out = m.scan_line(line)
        assert any("DSCR" in o for o in out), (
            "value-between-metric-and-boundword drift must flag: %r -> %r" % (line, out))
    # Canonical in the same shape must stay clean -- arming is not a finding.
    assert m.scan_line("DSCR 1.25x minimum per property.") == [], \
        "canonical value in the value-first shape must not flag"
    print("  PASS test_value_between_metric_and_boundword_flags_unit")


def test_value_abutting_arming_does_not_flag_durations_unit():
    """FP GUARD for the value-abutting pattern (2026-08-12). The whole reason the simpler
    digit-dot fix was rejected: bare 'min' is a DURATION unit as often as it is 'minimum'. These
    must never report a governor finding -- pinned so a future loosening of the value-abutting
    pattern fails here rather than turning cure periods and uptime prose into Hard-Invariant-4
    findings."""
    m = _load_probe_module()
    for line in ("DSCR of 1.42 with a 10 min cure period",
                 "DSCR poller downtime 1.5 min today.",
                 "Cure period is 30 min; DSCR of 1.42 reported.",
                 "DSCR came in at 1.42; minimum lease term 3 yrs."):
        assert m.scan_line(line) == [], (
            "duration/unrelated prose must NOT flag: %r -> %r" % (line, m.scan_line(line)))
    print("  PASS test_value_abutting_arming_does_not_flag_durations_unit")


def test_ltv_reverse_ceiling_vetoes_non_ltv_subjects_unit():
    """FP CLASS CLOSED (2026-08-12, MAJOR finding from independent review).

    RE_LTV_CEIL_REV fires on any "N% ceiling|maximum" anywhere on an ARMED line and needs no 'ltv'
    token -- that is deliberate, so "This 65% ceiling is the acquisition governor" is caught. But
    once the DSCR side started arming the value-first shape, a line could be armed purely by a DSCR
    statement and this pass would then read an unrelated capped percentage as an LTV ceiling. That
    is realistic buy-box list prose, and one false positive flips the weekly gate red.

    Closed by VETOING on the percentage's subject -- not by requiring positive LTV evidence. The
    requirement form was implemented first and reverted: see
    test_ltv_subject_veto_does_not_silence_real_declarations_unit for the five real declarations it
    silenced and why the direction matters."""
    m = _load_probe_module()
    for line in ("DSCR 1.25x minimum; underwrite vacancy 10% maximum.",
                 "DSCR 1.25 floor, TI cap 12% maximum of TDC.",
                 "DSCR 1.25x minimum with parking ratio 2.0 and site coverage 45% maximum."):
        assert m.scan_line(line) == [], (
            "an unrelated capped percentage on a DSCR-armed line must NOT read as an LTV "
            "ceiling: %r -> %r" % (line, m.scan_line(line)))
    # The reverse-order pass must KEEP its reason for existing. Exact string, not a substring
    # match: a weaker assertion passes even when the WRONG percentage is reported.
    assert m.scan_line("This 65% ceiling is the acquisition governor.") == \
        ["LTV ceiling 65% != canonical 40%"], \
        "reverse-order LTV ceiling on a genuine governor declaration must still flag, and must "\
        "report the ceiling's own value"
    print("  PASS test_ltv_reverse_ceiling_vetoes_non_ltv_subjects_unit")


def test_ltv_subject_veto_does_not_silence_real_declarations_unit():
    """THE REGRESSION GUARD for how this false positive is fixed (2026-08-12).

    The FIRST attempt at this fix REQUIRED a positive LTV-side governor marker near the value. It
    closed the false positives and silently broke five realistic drift declarations that had
    flagged since 2026-07-08 -- verified against baseline ba2b0a8 -- because it reused
    _governor_declared_nearby, a helper whose short before-reach and plural/canonical-phrase
    exemptions are tuned to err toward DETECTION when used to VETO, and therefore err toward
    SILENCE when used as a REQUIREMENT. Independent review caught it.

    These five are the exact lines that broke. They pin the DIRECTION of the fix: suppression must
    stay subject-scoped. If someone reworks this into a positive-evidence gate again, this test
    fails first."""
    m = _load_probe_module()
    for line in ("Under the 1.25x DSCR governor we now allow a 65% maximum.",
                 "Governors: DSCR 1.25x floor and 65% maximum.",
                 "DSCR floor 1.25x and 65% ceiling.",
                 "minimum DSCR 1.25x, 65% maximum leverage.",
                 "Governor note: raised the ceiling to 55% maximum effective today."):
        assert any("LTV" in o for o in m.scan_line(line)), (
            "a real governor declaration must NOT be silenced by the FP fix: %r -> %r"
            % (line, m.scan_line(line)))
    # A distant subject mention must not reach the ceiling's own value (veto is deliberately short).
    assert m.scan_line("vacancy 5% assumed; LTV ceiling 65%.") == \
        ["LTV ceiling 65% != canonical 40%"], \
        "a subject elsewhere on the line must not suppress a genuine ceiling"

    # THE VETO'S OWN REACH, pinned in both dimensions -- these were lost to the first cut of the
    # veto itself and found only by comparing against the 5-week baseline, not against HEAD.
    # (a) 'coverage' must NOT be a vetoing subject: DSCR is the debt-service-COVERAGE ratio, so it
    #     appears in genuine governor prose exactly where a paired LTV ceiling is declared.
    for line in ("Debt service coverage floor; 65% maximum governor.",
                 "Governor: coverage 1.30x; 65% ceiling.",
                 "Governor -- coverage-based sizing, 65% maximum.",
                 "Governor: debt service coverage 1.25x floor and 65% ceiling."):
        assert any("LTV" in o for o in m.scan_line(line)), (
            "'coverage' must not veto -- it is the DSCR's own word: %r -> %r"
            % (line, m.scan_line(line)))
    # (b) the reach must not cross a clause ender into the previous clause's subject.
    for line in ("Governor: assume 5% vacancy; leverage 55% maximum.",
                 "Governor: vacancy 5%; 55% maximum."):
        assert any("LTV" in o for o in m.scan_line(line)), (
            "a previous clause's subject must not suppress this clause's ceiling: %r -> %r"
            % (line, m.scan_line(line)))
    print("  PASS test_ltv_subject_veto_does_not_silence_real_declarations_unit")


def test_ltv_subject_veto_reach_semantics_unit():
    """Pins the two defects the veto helper itself shipped with (2026-08-12, found in review).

    (a) A DECIMAL POINT IS NOT A CLAUSE ENDER. The first cut computed the clause boundary with a
        raw rfind('.'), so "2.5x" truncated the lookback window and cut the subject out of it --
        reopening the exact false-positive class this veto exists to close, on prose that is dense
        with decimal multiples precisely because it is DSCR-adjacent.

    (b) THE SUBJECT MUST END INSIDE THE WINDOW, and must not be separated from the value by a bound
        word. The first cut accepted any subject merely OVERLAPPING the window, which stretched
        suppression past the helper's own stated theory ("the subject sits immediately before the
        value") and silenced a line that flagged at baseline. An intervening ceiling word means the
        value binds to the ceiling, not to the subject."""
    m = _load_probe_module()
    for line in ("DSCR 1.25x minimum, vacancy at 2.5x turnover 10% maximum.",
                 "TI cap 1.5x factor, 12% maximum of TDC on a DSCR floor 1.25x basis."):
        assert m.scan_line(line) == [], (
            "a decimal must not be read as a clause ender: %r -> %r" % (line, m.scan_line(line)))
    for line in ("Governor: at 95% occupancy the ceiling is 65% maximum.",):
        assert any("LTV" in o for o in m.scan_line(line)), (
            "a bound word between subject and value means the value is the ceiling: %r -> %r"
            % (line, m.scan_line(line)))

    # (c) AN INTERVENING PERCENT DISPROVES OWNERSHIP. The subject owns that earlier figure, so the
    # later one is still a ceiling. Without this the veto leapfrogs a real figure -- the same
    # failure the refi machinery's percent-free gaps exist to prevent. These are the "and" form of
    # the clause-crossing lines already pinned above: swap the semicolon for "and" and, before this
    # guard, the line went dark.
    for line in ("Governor: vacancy 5% assumed and 65% maximum.",
                 "Governor: vacancy 8% and 65% maximum leverage.",
                 "Governor: vacancy .5% assumed and 65% maximum."):
        assert any("LTV" in o for o in m.scan_line(line)), (
            "an intervening percent means the subject owns the EARLIER figure, so this one must "
            "still flag: %r -> %r" % (line, m.scan_line(line)))
    print("  PASS test_ltv_subject_veto_reach_semantics_unit")


def test_ltv_house_separator_styles_still_flag_unit():
    """The arming-gate doctrine comment explicitly blesses ',' ':' and the house '--' style as
    plausible governor DECLARATIONS. An earlier cut of this fix tightened the anchor gap to
    exclude them, which silenced exactly the phrasings that comment protects; that tightening was
    reverted in favour of the subject veto. Pinned so it is not reintroduced."""
    m = _load_probe_module()
    for line in ("LTV -- hard ceiling 75%", "LTV: hard ceiling 55%.", "LTV, hard ceiling, 75%",
                 "LTV ceiling, revised, 65%"):
        assert any("LTV" in o for o in m.scan_line(line)), (
            "house separator style must still flag: %r -> %r" % (line, m.scan_line(line)))
    print("  PASS test_ltv_house_separator_styles_still_flag_unit")


def test_ltv_anchor_window_respects_the_subject_veto_unit():
    """FP CLASS CLOSED (2026-08-12, same review), second mechanism. RE_LTV_ANCHOR can bind a
    ceiling word that belongs to a different noun ("LTV steady, maximum TI 12% of TDC"), and the
    anchor's 40-char window then read that subject's percentage as the declared LTV ceiling.

    Fixed with the same subject veto as the reverse pass, NOT by tightening the anchor gap: an
    earlier cut did tighten it (two adjacent words, no comma, no 'governor' token) and thereby
    silenced the ',' ':' and house '--' separator styles that the arming-gate doctrine comment
    explicitly protects -- see test_ltv_house_separator_styles_still_flag_unit."""
    m = _load_probe_module()
    for line in ("Governor note: LTV steady, maximum TI 12% of TDC.",
                 "LTV governor maximum vacancy 10% assumed."):
        assert m.scan_line(line) == [], (
            "a percentage owned by a non-LTV subject must not be read as the anchored LTV "
            "ceiling: %r -> %r"
            % (line, m.scan_line(line)))
    # Genuine qualifier forms must survive -- this is the gap the 08-12 change existed to close.
    for line in ("LTV hard ceiling 75% on an aggregate basis.",
                 "LTV absolute maximum 75% is the acquisition governor.",
                 "Acquisition governor: LTV ceiling 65%."):
        assert any("LTV" in o for o in m.scan_line(line)), (
            "adjectival-qualifier LTV ceiling must still flag: %r -> %r" % (line, m.scan_line(line)))
    print("  PASS test_ltv_anchor_window_respects_the_subject_veto_unit")


def test_ltv_extractor_spans_intervening_qualifier_unit():
    """GAP 2 CLOSED (2026-08-12). "LTV hard ceiling 75%" was ARMED all along -- "hard ceiling" is a
    GOV_KEYWORDS token (N6) -- but yielded nothing, because the EXTRACTOR RE_LTV_ANCHOR required
    contiguous "ltv ceiling" (\\s* only), so the qualifier defeated it. The 2026-08-11 revision
    blamed the arming gate; independent review corrected the attribution to the extractors, and
    this closes it there.

    Widening the extractor is safe with respect to the ratified 65% refi-ceiling false positive
    that caused the earlier revert, because that line is gated out by ARMING, not by extraction --
    pinned by test_ratified_perproperty_refi_ceiling_prose_stays_clean_unit, which must keep
    passing alongside this."""
    m = _load_probe_module()
    out = m.scan_line("LTV hard ceiling 75% on an aggregate basis.")
    assert any("LTV" in o for o in out), (
        "drifted LTV ceiling with an intervening qualifier must flag: %r" % (out,))
    assert m.scan_line("LTV hard ceiling 40% on an aggregate basis.") == [], \
        "canonical LTV ceiling in the same shape must stay clean"

    # BOUNDARY, asserted deliberately: extraction is only half the requirement -- the line must
    # ALSO be armed. "LTV absolute maximum 75%" carries no GOV_KEYWORDS token (unlike "hard
    # ceiling", N6), so it stays clean even though the widened extractor can now read it. This is
    # the arming gate working as designed, NOT a residual extractor bug: closing it would require
    # widening LTV ARMING, which is the change that false-positived on the ratified 65%
    # per-property refi ceiling and was reverted. Documented so the next reader does not "fix"
    # this by reopening that hole.
    assert m.scan_line("LTV absolute maximum 75% on an aggregate basis.") == [], (
        "unarmed LTV prose must stay clean -- widening LTV ARMING is the reverted change")
    print("  PASS test_ltv_extractor_spans_intervening_qualifier_unit")


def test_intervening_qualifier_canonical_stays_clean_unit():
    """Arming the line must not by itself create a finding: canonical values stay clean."""
    m = _load_probe_module()
    assert m.scan_line("DSCR hard floor 1.25x per property.") == [], "canonical must stay clean"
    print("  PASS test_intervening_qualifier_canonical_stays_clean_unit")


def test_qualifier_gate_requires_the_metric_token_unit():
    """PRECISION GUARDRAIL: the fix must pair the METRIC token with its floor/ceiling word, never
    admit a bare 'hard floor' as a governor signal -- 'hard floor' is also a physical building
    term, and a standalone keyword would arm unrelated property prose.

    Also pins ALL FOUR clause enders. Excluding only '.' was not enough: ';' '!' and '?' each let
    the gap cross into an unrelated rent/area figure that RE_DSCR_THRESH then captured as a DSCR
    threshold -- a NEW false positive introduced by the first cut of this fix and caught in
    independent review, not by the suite. One case per boundary character, so a future narrowing of
    the gap class fails here rather than in a whole-tree scan."""
    m = _load_probe_module()
    for line in ("Suite B has a hard floor and a 32.0 ft clear-height ceiling.",
                 "The tenant's hard floor covers 1.40 acres of the yard.",
                 "The deal's actual DSCR came in at 1.42 last quarter.",
                 "DSCR is disclosed quarterly. The rent floor is 1.40 psf.",
                 "DSCR fine; rent floor is 1.40 psf.",
                 "DSCR solid! The rent floor is 1.40 psf.",
                 "DSCR ok? The rent floor is 1.40 psf.",
                 "DSCR steady; unit floor area 1.40 acres."):
        assert m.scan_line(line) == [], (
            "non-governor prose must NOT be armed by the qualifier fix: %r -> %r"
            % (line, m.scan_line(line)))
    print("  PASS test_qualifier_gate_requires_the_metric_token_unit")


def test_stabilization_conditioned_covenant_suppressed_unit():
    """2026-08-15 FP fix: a deal-pipeline row narrating ONE deal's LENDER covenant that only
    clears at stabilization -- "transition-year DSCR breaches (clears the 1.75x floor only at
    Yr3+ stabilization) -> all-cash close mandatory" (the live projects.md shape) -- is the
    property's own projected DSCR against a deal-specific loan covenant, NOT a restatement of
    the canonical acquisition governor. It armed _is_gov via the dscr..value..floor pairing and
    flagged in BOTH the 1.75 sentinel and the equality pass; no existing suppressor (portfolio,
    refi, correction) caught it. Must now scan clean."""
    m = _load_probe_module()
    clean = [
        # paraphrase of the actual projects.md:27 fragment (deal name elided):
        "Substantive: transition-year DSCR breaches (clears the 1.75x floor only at Yr3+ "
        "stabilization) → all-cash close mandatory; anchor tenant ~50% of rents rolls 5/2027.",
        # same covenant shape, non-sentinel value + lease-up wording:
        "Lender covenant: projected DSCR clears the 1.40x floor only after lease-up "
        "stabilization in year 3.",
    ]
    for line in clean:
        out = m.scan_line(line)
        assert out == [], (
            "stabilization-conditioned deal covenant must be suppressed; line=%r got=%r"
            % (line[:90], out))
    print("  PASS test_stabilization_conditioned_covenant_suppressed_unit")


def test_stabilization_language_does_not_mask_governor_drift_unit():
    """REFUTE guard for the fix above -- the test that catches an overly-broad suppression: the
    SAME stabilization language plus an explicit acquisition-governor marker (or the value
    declared AS the governor) is a REAL governor drift dressed up in stabilization words, and
    must STILL flag."""
    m = _load_probe_module()
    # ACQ_GOV_MARKERS veto ("hard acquisition governor" / "dscr floor"):
    out1 = m.scan_line("Hard acquisition governor: DSCR floor 1.75x, even at Yr3+ stabilization.")
    assert any("1.75" in o for o in out1), (
        "acq-governor marker must veto stabilization suppression; got %r" % out1)
    out2 = m.scan_line("Per-deal DSCR floor now 1.40x once the asset reaches stabilization.")
    assert any("1.40" in o for o in out2), (
        "per-deal marker must veto stabilization suppression; got %r" % out2)
    # value declared AS the governor nearby (within the _refi_qualified-precedent +40 reach):
    out3 = m.scan_line("DSCR clears 1.40x at stabilization (the governor).")
    assert any("1.40" in o for o in out3), (
        "a value declared AS the governor must not be masked by stabilization words; got %r" % out3)
    print("  PASS test_stabilization_language_does_not_mask_governor_drift_unit")


def test_stabilization_qualifier_does_not_mask_reversed_word_order_unit():
    """2026-08-15 REFUTE remediation (holes 1/2/5/7): "DSCR minimum" (metric-then-bound-word,
    reversed from the "minimum dscr"/"min dscr" literals in ACQ_GOV_MARKERS) arms is_gov via
    RE_GOV_DSCR_BOUND but escaped every marker veto, so _stabilization_qualified silently
    suppressed REAL governor declarations. Fixed structurally: RE_GOV_DSCR_BOUND matching
    anywhere on the line vetoes stabilization suppression -- the declaration shape pairs metric
    and bound-word directly, while the legitimate covenant narration puts the VALUE between
    them ("clears the 1.75x floor"), whose decimal point RE_GOV_DSCR_BOUND cannot cross."""
    m = _load_probe_module()
    # hole 1 -- reversed word order, non-sentinel drift value:
    out = m.scan_line("DSCR minimum raised to 1.40x at stabilization.")
    assert any("1.40" in o for o in out), (
        "reversed-order 'DSCR minimum' declaration must flag despite stabilization word; got %r" % out)
    # hole 2 -- same gap masking the historical 1.75 drift sentinel itself (worst case):
    out = m.scan_line("DSCR minimum 1.75x during lease-up only.")
    assert any("1.75" in o for o in out), (
        "reversed-order declaration must not mask the 1.75 sentinel; got %r" % out)
    # hole 5 -- 'yr3' used in an unrelated exit-cap-timing sense inside the proximity window:
    out = m.scan_line("Yr3 exit cap 7.0%; DSCR minimum 1.40x.")
    assert any("1.40" in o for o in out), (
        "exit-cap 'Yr3' must not qualify a separate declared minimum for suppression; got %r" % out)
    # hole 7 -- multi-value line: the qualifier modifies the FIRST (legitimate) value but the
    # proximity window also swallowed the SECOND (drifted) value in the next clause:
    out = m.scan_line("Covenant clears 1.75x at Yr3 stabilization; DSCR minimum now 1.40x.")
    assert any("1.40" in o for o in out), (
        "a drifted declaration in the next clause must flag even beside a covenant value; got %r" % out)
    print("  PASS test_stabilization_qualifier_does_not_mask_reversed_word_order_unit")


def test_stabilization_qualifier_veto_covers_arming_vocabulary_unit():
    """2026-08-15 REFUTE remediation (holes 3/4): "hard cap"/"self-imposed"/"disqualif" ARM
    is_gov (GOV_KEYWORDS) but were absent from the suppressor's veto list, so a governor
    declaration whose only signal was one of them was suppressible by a nearby lease-up word.
    Fixed by STAB_GOV_MARKERS -- the stabilization suppressor's veto vocabulary is a superset
    of the arming vocabulary (scoped to this suppressor only; the shared ACQ_GOV_MARKERS is
    unchanged because ratified refi doctrine legitimately writes "self-imposed ... post-close"
    sizing caps, pinned by test_reverse_order_refi_suppression_unit)."""
    m = _load_probe_module()
    # hole 3 -- "hard cap" + "self-imposed" arm but did not veto:
    out = m.scan_line("Self-imposed hard cap: DSCR 1.10x during lease-up.")
    assert any("1.10" in o for o in out), (
        "'hard cap'/'self-imposed' governor declaration must flag despite lease-up word; got %r" % out)
    # hole 4 -- "disqualif" arms but did not veto:
    out = m.scan_line("DSCR below 1.10x disqualified pre-stabilization.")
    assert any("1.10" in o for o in out), (
        "'disqualif' governor declaration must flag despite stabilization word; got %r" % out)
    print("  PASS test_stabilization_qualifier_veto_covers_arming_vocabulary_unit")


def test_stabilization_qualifier_does_not_mask_year_YYYY_dates_unit():
    """2026-08-15 REFUTE remediation (hole 6, worst surface): the bare-substring qualifier
    "year 2" matched INSIDE "year 2026" (any "year 20xx" date), so ordinary dated doctrine
    prose near a DSCR value qualified for suppression across the whole memory/skill tree.
    Fixed: year tokens are now the digit-bounded RE_STAB_YEAR regex (digit 1-3, not followed
    by another digit), so dates can never qualify while genuine "Yr3+"/"year 3" lease-up
    framing still can."""
    m = _load_probe_module()
    out = m.scan_line("Fiscal year 2026 doctrine: DSCR minimum now 1.40x.")
    assert any("1.40" in o for o in out), (
        "'year 2026' date must not qualify a drifted declaration for suppression; got %r" % out)
    # boundary semantics of the replacement regex itself:
    assert m.RE_STAB_YEAR.search("year 2026") is None, "date 'year 2026' must not match RE_STAB_YEAR"
    assert m.RE_STAB_YEAR.search("only at yr3+ stabilization") is not None, (
        "'yr3+' lease-up framing must still match RE_STAB_YEAR")
    assert m.RE_STAB_YEAR.search("stabilization in year 3.") is not None, (
        "'year 3' lease-up framing must still match RE_STAB_YEAR")
    print("  PASS test_stabilization_qualifier_does_not_mask_year_YYYY_dates_unit")


def main():
    assert os.path.isfile(PROBE), "probe not found: %s" % PROBE
    test_fleet_roots_are_scanned_unit()
    test_dated_archive_dirs_pruned_unit()
    test_probe_self_description_prose_suppressed_unit()
    test_sentinel_suppression_does_not_hide_real_drift_unit()
    test_fleet_skill_drift_would_flag_e2e()
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
    test_scan_code_canonical_clean_unit()
    test_scan_code_constant_drift_flags_unit()
    test_scan_code_direction_and_inversion_flags_unit()
    test_scan_code_ignores_deal_values_unit()
    test_scan_code_seed_literal_drift_flags_unit()
    test_scan_code_presence_regexes_unit()
    test_reverse_order_dscr_floor_flags_unit()
    test_reverse_order_ltv_ceiling_flags_unit()
    test_reverse_order_no_false_positive_unit()
    test_reverse_order_suppression_still_applies_unit()
    test_reverse_order_refi_suppression_unit()
    test_version_token_not_a_dscr_threshold_unit()
    test_approximate_tilde_value_not_a_dscr_threshold_unit()
    test_tilde_hedge_corrected_word_boundary_and_directional_unit()
    test_deal_comparison_skill_file_clean()
    test_rate_percent_not_a_dscr_threshold_unit()
    test_refi_lesser_of_construct_suppressed_unit()
    test_refi_sizing_phrase_suppressed_unit()
    test_canonical_dscr_governor_at_ltv_suppressed_unit()
    test_bps_rate_pricing_tier_suppressed_unit()
    test_perdeal_perproperty_drift_still_flags_unit()
    test_review_hole1_lesser_of_gap_drift_flags_unit()
    test_review_hole2_bps_gap_no_leapfrog_flags_unit()
    test_decimal_fragment_never_binds_unit()
    test_decimal_ltv_drift_still_flags_unit()
    test_canonical_decimal_forty_clean_unit()
    test_dated_review_memory_file_excluded_unit()
    test_unit_interval_ltv_flags_unit()
    test_ledger_files_excluded_source_pin()
    test_review_hole3_paired_gap_drift_flags_unit()
    test_review_hole4_veto_window_and_refi_gate_flags_unit()
    test_review_hole5_dscr_extraction_regressions_flags_unit()
    test_followup1_value_dscr_keyword_order_flags_unit()
    test_followup2_refi_to_ltv_veto_tier_unit()
    test_round2_declaring_governor_before_value_flags_unit()
    test_n6_hard_cap_ceiling_is_gov_gate_unit()
    test_perprop_portfolio_aggregate_pairing_suppressed_unit()
    test_perprop_member_value_locked_to_ratified_65_unit()
    test_perproperty_non_ratified_ltv_still_flags_unit()
    test_perprop_pairing_vetoed_when_declared_as_acquisition_ceiling_unit()
    test_dated_audit_memory_file_excluded_unit()
    test_acquisition_underwriting_skill_file_clean()
    test_test_files_excluded_from_scan_unit()
    test_event_log_excluded_e2e()
    test_active_work_claims_pruned_unit()
    test_active_work_claims_excluded_e2e()
    test_intervening_qualifier_dscr_floor_flags_unit()
    test_ratified_perproperty_refi_ceiling_prose_stays_clean_unit()
    test_perproperty_refi_ceiling_standalone_bullet_stays_clean_unit()
    test_perproperty_refi_ceiling_standalone_drift_still_flags_unit()
    test_perproperty_refi_frame_elsewhere_on_line_does_not_mask_aggregate_drift_unit()
    test_ltv_reverse_ceiling_vetoes_non_ltv_subjects_unit()
    test_ltv_subject_veto_does_not_silence_real_declarations_unit()
    test_ltv_subject_veto_reach_semantics_unit()
    test_ltv_house_separator_styles_still_flag_unit()
    test_ltv_anchor_window_respects_the_subject_veto_unit()
    test_ltv_extractor_spans_intervening_qualifier_unit()
    test_value_between_metric_and_boundword_flags_unit()
    test_value_abutting_arming_does_not_flag_durations_unit()
    test_intervening_qualifier_canonical_stays_clean_unit()
    test_qualifier_gate_requires_the_metric_token_unit()
    test_stabilization_conditioned_covenant_suppressed_unit()
    test_stabilization_language_does_not_mask_governor_drift_unit()
    test_stabilization_qualifier_does_not_mask_reversed_word_order_unit()
    test_stabilization_qualifier_veto_covers_arming_vocabulary_unit()
    test_stabilization_qualifier_does_not_mask_year_YYYY_dates_unit()
    print("ALL GOVERNOR-PROBE TESTS PASS")


if __name__ == "__main__":
    main()
