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
    test_rate_percent_not_a_dscr_threshold_unit()
    test_refi_lesser_of_construct_suppressed_unit()
    test_refi_sizing_phrase_suppressed_unit()
    test_canonical_dscr_governor_at_ltv_suppressed_unit()
    test_bps_rate_pricing_tier_suppressed_unit()
    test_perdeal_perproperty_drift_still_flags_unit()
    test_review_hole1_lesser_of_gap_drift_flags_unit()
    test_review_hole2_bps_gap_no_leapfrog_flags_unit()
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
    print("ALL GOVERNOR-PROBE TESTS PASS")


if __name__ == "__main__":
    main()
