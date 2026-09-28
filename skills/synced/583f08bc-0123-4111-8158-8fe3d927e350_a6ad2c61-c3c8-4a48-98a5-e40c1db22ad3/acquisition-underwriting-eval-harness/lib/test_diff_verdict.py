"""Tests for lib/diff_verdict.py — golden-set comparison/tolerance engine.

Written FIRST (TDD). Fixtures mirror the real golden_set/*.json shape:
top-level `confidence` and `diff_policy`; scores under `golden`;
`quality`/`economics`/`category_breakdown` sometimes null; Hamilton-style
breakdowns carry non-numeric `*_flag` entries that must be skipped.

Also loads the 6 real golden files as a smoke check that the engine
handles every real row without error.
"""

import copy
import json
import unittest
from pathlib import Path

from diff_verdict import diff_verdict, _parse_floor_pair
from diff_verdict import (
    _YOC_LABEL_RE,
    _DSCR_LABEL_RE,
    _EXPLICIT_FLOOR_PCT_RE,
    _EXPLICIT_FLOOR_X_RE,
    _POSITIONAL_PCT_RE,
    _POSITIONAL_X_RE,
)

GOLDEN_DIR = Path(__file__).resolve().parent.parent / "golden_set"


def make_golden(
    deal_id="test-deal",
    confidence="HIGH",
    combined=65.0,
    golden_tier="T2 WATCH",
    category_breakdown=None,
    known_gaps=None,
    tolerance=3.0,
    floor_result="N/A",
):
    return {
        "deal_id": deal_id,
        "deal_name": "Test Deal",
        "mode": "SCREEN",
        "confidence": confidence,
        "known_gaps": known_gaps if known_gaps is not None else [],
        "inputs": {},
        "golden": {
            "quality": None,
            "economics": None,
            "combined": combined,
            "category_breakdown": category_breakdown,
            "expected_score": None,
            "p_exec_pct": None,
            "verdict_tier": golden_tier,
            "bands_predicted_tier": "T2 WATCH",
            "floor_result": floor_result,
        },
        "diff_policy": {
            "primary_signal": "combined_score",
            "tolerance_combined_pts": tolerance,
            "tier_check": "informational_only",
        },
    }


def make_observed(
    combined=65.0,
    verdict_tier="T2 WATCH",
    category_breakdown=None,
    floor_result="N/A",
):
    return {
        "combined": combined,
        "quality": None,
        "economics": None,
        "expected_score": None,
        "p_exec_pct": None,
        "verdict_tier": verdict_tier,
        "floor_result": floor_result,
        "category_breakdown": category_breakdown,
        "notes": "",
    }


class TestPassFlag(unittest.TestCase):
    def test_pass_within_tolerance(self):
        """(a) Observed within tolerance -> PASS."""
        result = diff_verdict(make_golden(combined=65.0), make_observed(combined=66.5))
        self.assertEqual(result["status"], "PASS")
        self.assertTrue(result["scored"])
        self.assertFalse(result["informational_only"])
        self.assertAlmostEqual(result["combined_delta"], 1.5)
        self.assertEqual(result["combined_golden"], 65.0)
        self.assertEqual(result["combined_observed"], 66.5)
        self.assertEqual(result["tolerance_pts"], 3.0)
        self.assertEqual(result["deal_id"], "test-deal")

    def test_flag_beyond_tolerance(self):
        """(b) Observed beyond tolerance -> FLAG (both directions)."""
        result = diff_verdict(make_golden(combined=65.0), make_observed(combined=70.0))
        self.assertEqual(result["status"], "FLAG")
        self.assertAlmostEqual(result["combined_delta"], 5.0)

        result_neg = diff_verdict(make_golden(combined=65.0), make_observed(combined=60.5))
        self.assertEqual(result_neg["status"], "FLAG")
        self.assertAlmostEqual(result_neg["combined_delta"], -4.5)

    def test_boundary_exactly_at_tolerance_is_pass(self):
        """(d) |delta| == tolerance is PASS — only strictly-beyond flags."""
        result = diff_verdict(make_golden(combined=65.0), make_observed(combined=68.0))
        self.assertAlmostEqual(result["combined_delta"], 3.0)
        self.assertEqual(result["status"], "PASS")

        result_neg = diff_verdict(make_golden(combined=65.0), make_observed(combined=62.0))
        self.assertAlmostEqual(result_neg["combined_delta"], -3.0)
        self.assertEqual(result_neg["status"], "PASS")


class TestConfidenceScoring(unittest.TestCase):
    def test_low_confidence_not_scored_but_delta_reported(self):
        """(c) LOW confidence -> scored False even with a large delta; delta still computed."""
        golden = make_golden(confidence="LOW", combined=48.0)
        result = diff_verdict(golden, make_observed(combined=60.0))
        self.assertFalse(result["scored"])
        self.assertTrue(result["informational_only"])
        self.assertAlmostEqual(result["combined_delta"], 12.0)
        # Status still computed/reported (delta > tolerance -> FLAG label),
        # but scored=False tells the caller to exclude it from strict tallies.
        self.assertEqual(result["status"], "FLAG")
        self.assertTrue(
            any("LOW confidence" in n for n in result["notes"]),
            f"expected a LOW-confidence exclusion note in {result['notes']}",
        )

    def test_high_and_medium_confidence_scored(self):
        for conf in ("HIGH", "MEDIUM"):
            result = diff_verdict(
                make_golden(confidence=conf), make_observed()
            )
            self.assertTrue(result["scored"], f"confidence={conf} should be scored")
            self.assertFalse(result["informational_only"])

    def test_unrecognized_confidence_raises_not_silently_excludes(self):
        """REFUTE-pass finding: `scored = confidence in ("HIGH","MEDIUM")` used to
        silently treat any typo'd or missing confidence value (e.g. "High", "") as
        equivalent to LOW -- excluding a row from the strict pass/fail tally without
        anyone deciding to. Must raise instead."""
        for bad_confidence in ("High", "", None, "MED"):
            golden = make_golden(confidence=bad_confidence)
            with self.assertRaises(ValueError):
                diff_verdict(golden, make_observed())


class TestTierInformational(unittest.TestCase):
    def test_reads_golden_verdict_tier_key_not_archived_verdict_tier(self):
        """Regression test: a 2026-08-14 rebaseline renamed golden['golden']'s tier
        key from archived_verdict_tier to verdict_tier. diff_verdict.py briefly read
        the old name after the rename, silently returning archived_tier=None for
        every real golden file -- caught by the mutated-input self-test (see
        SKILL.md 'Self-test'), not by this suite, because make_golden() had drifted
        to match the same stale key name as the bug. Assert directly against a
        golden dict shaped like the REAL schema (verdict_tier only, no
        archived_verdict_tier key at all) so this class of key-rename desync
        cannot silently reintroduce itself.
        """
        golden = make_golden(combined=65.0, golden_tier="T2 WATCH")
        self.assertNotIn(
            "archived_verdict_tier",
            golden["golden"],
            "make_golden() fixture must match the real golden_set/*.json schema "
            "(verdict_tier), not the retired archived_verdict_tier key name",
        )
        result = diff_verdict(golden, make_observed(combined=65.0, verdict_tier="T2 WATCH"))
        self.assertEqual(result["golden_tier"], "T2 WATCH")
        self.assertTrue(result["tier_match"])

    def test_tier_mismatch_alone_does_not_flag(self):
        """(e) Combined matches, tier differs -> still PASS; tier reported."""
        golden = make_golden(combined=65.0, golden_tier="T2 WATCH")
        observed = make_observed(combined=65.0, verdict_tier="T1 PURSUE")
        result = diff_verdict(golden, observed)
        self.assertEqual(result["status"], "PASS")
        self.assertFalse(result["tier_match"])
        self.assertEqual(result["golden_tier"], "T2 WATCH")
        self.assertEqual(result["observed_tier"], "T1 PURSUE")

    def test_tier_match_reported(self):
        result = diff_verdict(
            make_golden(golden_tier="T2 WATCH"),
            make_observed(verdict_tier="T2 WATCH"),
        )
        self.assertTrue(result["tier_match"])

    def test_tier_match_ignores_parenthetical_annotation(self):
        """McCormick's golden tier is 'KILLED (post-hoc status overwrite, ...)' —
        normalization compares the label before the parenthetical."""
        golden = make_golden(
            golden_tier="KILLED (post-hoc status overwrite, not a skill verdict band -- see known_gaps)"
        )
        result = diff_verdict(golden, make_observed(verdict_tier="KILLED"))
        self.assertTrue(result["tier_match"])


class TestCategoryBreakdown(unittest.TestCase):
    def test_category_deltas_when_both_present(self):
        """(f) Per-category deltas computed; non-numeric *_flag entries skipped."""
        golden_bd = {
            "basis": 20,
            "basis_flag": "[est]",
            "yield": 0,
            "yield_flag": "[est]",
            "product_physical": 10,
        }
        observed_bd = {"basis": 22, "yield": 1.0, "product_physical": 10}
        result = diff_verdict(
            make_golden(combined=30.0, category_breakdown=golden_bd),
            make_observed(combined=33.0, category_breakdown=observed_bd),
        )
        deltas = result["category_deltas"]
        self.assertIsNotNone(deltas)
        self.assertAlmostEqual(deltas["basis"], 2.0)
        self.assertAlmostEqual(deltas["yield"], 1.0)
        self.assertAlmostEqual(deltas["product_physical"], 0.0)
        self.assertNotIn("basis_flag", deltas)
        self.assertNotIn("yield_flag", deltas)
        # Category deltas never gate: |combined delta| == 3.0 -> still PASS.
        self.assertEqual(result["status"], "PASS")

    def test_category_none_safe_golden_null(self):
        result = diff_verdict(
            make_golden(category_breakdown=None),
            make_observed(category_breakdown={"basis": 20}),
        )
        self.assertIsNone(result["category_deltas"])

    def test_category_none_safe_observed_null(self):
        result = diff_verdict(
            make_golden(category_breakdown={"basis": 20}),
            make_observed(category_breakdown=None),
        )
        self.assertIsNone(result["category_deltas"])

    def test_category_key_missing_in_observed_reported_as_none(self):
        golden_bd = {"basis": 20, "yield": 4.2}
        observed_bd = {"basis": 20}
        result = diff_verdict(
            make_golden(category_breakdown=golden_bd),
            make_observed(category_breakdown=observed_bd),
        )
        self.assertAlmostEqual(result["category_deltas"]["basis"], 0.0)
        self.assertIsNone(result["category_deltas"]["yield"])


class TestNotes(unittest.TestCase):
    def test_known_gaps_carried_forward(self):
        gaps = ["NOI is not recorded anywhere.", "Scoring used a $700K walk price."]
        result = diff_verdict(make_golden(known_gaps=gaps), make_observed())
        for gap in gaps:
            self.assertTrue(
                any(gap in n for n in result["notes"]),
                f"known_gap not carried into notes: {gap}",
            )


class TestInputValidation(unittest.TestCase):
    def test_missing_observed_combined_raises(self):
        observed = make_observed()
        observed["combined"] = None
        with self.assertRaises(ValueError):
            diff_verdict(make_golden(), observed)

    def test_missing_tolerance_raises(self):
        golden = make_golden()
        del golden["diff_policy"]["tolerance_combined_pts"]
        with self.assertRaises(ValueError):
            diff_verdict(golden, make_observed())

    def test_inputs_not_mutated(self):
        golden = make_golden(category_breakdown={"basis": 20})
        observed = make_observed(category_breakdown={"basis": 21})
        golden_copy = copy.deepcopy(golden)
        observed_copy = copy.deepcopy(observed)
        diff_verdict(golden, observed)
        self.assertEqual(golden, golden_copy)
        self.assertEqual(observed, observed_copy)


class TestFloorConstantDrift(unittest.TestCase):
    """cc-audit-army finding M18-eval-harness-cannot-detect-governor-drift (2026-08-21),
    Gabriel-approved NARROW fix: DSCR/IRR are excluded from Combined by design, so a governor
    change there previously produced a Combined delta of exactly zero and could never flip
    status off PASS. These tests pin the narrow floor-constant parse/gate — DSCR and YoC only
    (both true fixed constants across every deal), and ONLY when the floor_result prose states
    an explicit '<observed> vs <floor>' comparison on both sides. Basis is deliberately NOT
    covered (its floor is vintage-dependent per deal, not a fixed constant)."""

    def test_matching_floor_constants_do_not_flag(self):
        golden = make_golden(
            combined=65.0,
            floor_result="CLEARS (Basis 75.0% vs 65% floor; YoC 10.96% vs 8%; DSCR 1.45x vs 1.25x)",
        )
        observed = make_observed(
            combined=65.0,
            floor_result="CLEARS (Basis 74.0% vs 65% floor; YoC 11.20% vs 8%; DSCR 1.50x vs 1.25x)",
        )
        result = diff_verdict(golden, observed)
        self.assertEqual(result["status"], "PASS")
        self.assertFalse(result["floor_drift"])

    def test_yoc_parses_own_clause_not_the_adjacent_basis_clause(self):
        """Bug caught by independent review (2026-08-22): on this exact combined
        'CLEARS (Basis ...%; YoC ...%; DSCR ...x)' string -- the module's OWN canonical
        healthy fixture, reused above -- `_parse_floor_pair` used to return the BASIS
        clause's numbers (75.0, 65.0) for a YoC search, because the old ±100-char window
        around the 'YoC' label reached past the ';' back into the Basis clause and
        _POSITIONAL_PCT_RE's optional label group let it match the leftmost '<num>% vs
        <num>%' pair in that whole window rather than the YoC-specific one. Assert the
        actually-parsed pair directly (not just status/floor_drift), on the healthy
        string where the prior test passed for the WRONG reason."""
        s = "CLEARS (Basis 75.0% vs 65% floor; YoC 10.96% vs 8%; DSCR 1.45x vs 1.25x)"
        self.assertEqual(
            _parse_floor_pair(s, _YOC_LABEL_RE, _EXPLICIT_FLOOR_PCT_RE, _POSITIONAL_PCT_RE),
            (10.96, 8.0),
        )
        self.assertEqual(
            _parse_floor_pair(s, _DSCR_LABEL_RE, _EXPLICIT_FLOOR_X_RE, _POSITIONAL_X_RE),
            (1.45, 1.25),
        )

    def test_yoc_drift_inside_full_combined_clears_phrasing_flags(self):
        """The exact defect class this fix closes: a REAL YoC governor drift (8% -> 7.5%)
        stated inside the realistic combined 'CLEARS (Basis ...; YoC ...; DSCR ...)'
        phrasing -- not the isolated 'YoC <n>% vs <floor>% floor' shape -- must still be
        caught, not silently swallowed by a false match on the adjacent Basis clause."""
        golden = make_golden(
            combined=65.0,
            floor_result="CLEARS (Basis 75.0% vs 65% floor; YoC 10.96% vs 8%; DSCR 1.45x vs 1.25x)",
        )
        observed = make_observed(
            combined=65.0,  # identical Combined -- would PASS under the old gate alone
            floor_result="CLEARS (Basis 75.0% vs 65% floor; YoC 10.96% vs 7.5%; DSCR 1.45x vs 1.25x)",
        )
        result = diff_verdict(golden, observed)
        self.assertEqual(result["status"], "FLAG")
        self.assertTrue(result["floor_drift"])
        self.assertTrue(
            any("GOVERNOR DRIFT on YoC floor" in n and "8.0" in n and "7.5" in n for n in result["notes"]),
            result["notes"],
        )

    def test_trailing_floor_label_reversal_inside_combined_phrasing_flags_drift(self):
        """A 'floor <N>x vs <N>x' reversal case (floor labeled AFTER the number, stated
        FIRST) embedded inside the full multi-clause combined phrasing, not in isolation
        -- pins that clause-scoping doesn't reintroduce the reversal bug the trailing-label
        tests above already cover standalone."""
        golden = make_golden(
            floor_result="CLEARS (Basis 75.0% vs 65% floor; YoC 10.96% vs 8%; DSCR 1.25x floor vs 1.45x actual)",
        )
        observed = make_observed(
            floor_result="CLEARS (Basis 75.0% vs 65% floor; YoC 10.96% vs 8%; DSCR 1.10x floor vs 1.45x actual)",
        )
        result = diff_verdict(golden, observed)
        self.assertEqual(result["status"], "FLAG")
        self.assertTrue(result["floor_drift"])
        self.assertTrue(
            any("GOVERNOR DRIFT on DSCR floor" in n and "1.25" in n and "1.1" in n for n in result["notes"]),
            result["notes"],
        )

    def test_dscr_floor_drift_flags_even_though_combined_matches(self):
        """The exact gap this fix closes: DSCR is excluded from Combined, so a real governor
        change here must flag through floor_drift, not through combined_delta."""
        golden = make_golden(
            combined=65.0,
            floor_result="CLEARS (Basis 75.0% vs 65% floor; YoC 10.96% vs 8%; DSCR 1.45x vs 1.25x)",
        )
        observed = make_observed(
            combined=65.0,  # identical Combined -- would PASS under the old gate alone
            floor_result="CLEARS (Basis 75.0% vs 65% floor; YoC 10.96% vs 8%; DSCR 1.45x vs 1.10x)",
        )
        result = diff_verdict(golden, observed)
        self.assertEqual(result["status"], "FLAG")
        self.assertTrue(result["floor_drift"])
        self.assertTrue(
            any("GOVERNOR DRIFT on DSCR floor" in n and "1.25" in n and "1.1" in n for n in result["notes"]),
            result["notes"],
        )

    def test_yoc_floor_drift_flags(self):
        golden = make_golden(floor_result="YoC 10.96% vs 8% floor")
        observed = make_observed(floor_result="YoC 10.96% vs 7.5% floor")
        result = diff_verdict(golden, observed)
        self.assertEqual(result["status"], "FLAG")
        self.assertTrue(result["floor_drift"])

    def test_unparseable_prose_on_either_side_is_a_reported_gap_not_a_flag(self):
        """The real golden_set shape: most rows never restate 'DSCR <x> vs <floor>' explicitly
        (ranges, different orderings, or the number omitted entirely). Must never be assumed
        clean OR guessed as drift -- reported as an explicit gap only."""
        golden = make_golden(
            floor_result="DSCR clears (~1.42-1.45x, LTV-bound refi) wherever computed",
        )
        observed = make_observed(floor_result="N/A")
        result = diff_verdict(golden, observed)
        self.assertFalse(result["floor_drift"])
        self.assertEqual(result["status"], "PASS")
        self.assertTrue(
            any("DSCR floor constant not verified" in n for n in result["notes"]), result["notes"]
        )

    def test_both_sides_agree_but_disagree_with_canonical_is_reported_not_gated(self):
        """Both sides parse and match EACH OTHER, but not the canonical 1.25x -- flagged as a
        stale-fixture note, not gated (this module never 'corrects' golden values -- see
        module docstring)."""
        golden = make_golden(floor_result="DSCR 1.30x vs 1.10x floor")
        observed = make_observed(floor_result="DSCR 1.30x vs 1.10x floor")
        result = diff_verdict(golden, observed)
        self.assertFalse(result["floor_drift"])
        self.assertEqual(result["status"], "PASS")
        self.assertTrue(
            any("differs from the canonical value" in n for n in result["notes"]), result["notes"]
        )

    def test_non_string_floor_result_does_not_crash(self):
        golden = make_golden(floor_result=None)
        observed = make_observed(floor_result=None)
        result = diff_verdict(golden, observed)  # must not raise
        self.assertFalse(result["floor_drift"])

    # cc-audit-army code-review finding (2026-08-22): the original regex assumed capture
    # group 1 is always "observed" and group 2 is always "floor" -- i.e. text always reads
    # "<observed> vs <floor>". A real golden file phrases YoC with the observed number
    # BEFORE the floor is even labeled, and a floor-stated-first phrasing ("DSCR floor of
    # 1.25x vs 1.45x actual") would reverse the assignment entirely, producing a
    # confidently WRONG drift/stale-fixture verdict rather than the intended "not verified"
    # gap.
    def test_real_golden_file_phrasing_yoc_before_label_parses_correctly(self):
        # Verbatim shape from golden_set/2196-port-sheldon-st-jenison-mi.json's floor_result.
        golden = make_golden(floor_result="Yield breached (~6.0-6.9% YoC vs 8.0% floor)")
        result = diff_verdict(
            golden,
            make_observed(floor_result="Yield breached (~6.2% YoC vs 8.0% floor)"),
        )
        self.assertFalse(result["floor_drift"])
        self.assertFalse(
            any("YoC floor constant not verified" in n for n in result["notes"]), result["notes"]
        )

    def test_explicit_floor_of_phrasing_is_not_reversed(self):
        """The floor is explicitly labeled ('floor of 1.25x') even though it's stated
        FIRST -- must not be mistaken for the observed figure just because it's in the
        first capture-group position."""
        golden = make_golden(floor_result="DSCR floor of 1.25x vs 1.45x actual")
        observed = make_observed(floor_result="DSCR floor of 1.25x vs 1.50x actual")
        result = diff_verdict(golden, observed)
        self.assertFalse(result["floor_drift"], "both state the same 1.25x floor -- must not read as drift")

    def test_explicit_floor_of_phrasing_still_detects_real_drift(self):
        golden = make_golden(floor_result="DSCR floor of 1.25x vs 1.45x actual")
        observed = make_observed(floor_result="DSCR floor of 1.10x vs 1.45x actual")
        result = diff_verdict(golden, observed)
        self.assertTrue(result["floor_drift"])
        self.assertTrue(
            any("GOVERNOR DRIFT on DSCR floor" in n and "1.25" in n and "1.1" in n for n in result["notes"]),
            result["notes"],
        )

    def test_trailing_floor_label_phrasing_is_not_reversed(self):
        """'1.25x floor' (floor labeled AFTER the number, still stated first) must also
        resolve correctly rather than defaulting to positional assignment."""
        golden = make_golden(floor_result="DSCR 1.25x floor vs 1.45x actual")
        observed = make_observed(floor_result="DSCR 1.10x floor vs 1.45x actual")
        result = diff_verdict(golden, observed)
        self.assertTrue(result["floor_drift"])


class TestRealGoldenFiles(unittest.TestCase):
    """Smoke test: every real golden file runs through the engine cleanly."""

    def test_all_six_real_files(self):
        files = sorted(GOLDEN_DIR.glob("*.json"))
        self.assertEqual(len(files), 6, f"expected 6 golden files, found {len(files)}")
        # Re-baselined 2026-08-14: golden values are now the fresh replay under
        # current doctrine (see each file's known_gaps re: the RCT v03 date-boundary
        # finding), not the pre-v03 archived Notion scores. Confidence reflects how
        # many scorecard categories that fresh replay left null.
        expected_scored = {
            "470-mccormick-blvd-columbus-oh": False,      # LOW
            "11850-hamilton-ave-cincinnati-oh": False,    # LOW
            "1333-research-rd-gahanna-oh": False,         # LOW
            "2196-port-sheldon-st-jenison-mi": True,      # HIGH
            # Enriched 2026-08-14 (real sourced physical specs, 3-run repeatability
            # check) -- promoted LOW -> MEDIUM. Tenancy & Lease stays null by design
            # (occupancy was a genuine unknown at the 6/9 screen date, not a research
            # gap), so it never reaches HIGH, but MEDIUM is scored=True same as HIGH.
            "e-fulton-st-portfolio-columbus-oh": True,    # MEDIUM
            "liberty-office-park-west-chester-oh": True,  # HIGH
        }
        for f in files:
            golden = json.loads(f.read_text(encoding="utf-8"))
            # Perfect replay: observed == golden values.
            g = golden["golden"]
            observed = make_observed(
                combined=g["combined"],
                verdict_tier=g["verdict_tier"],
                category_breakdown=g.get("category_breakdown"),
            )
            result = diff_verdict(golden, observed)
            self.assertEqual(result["status"], "PASS", f.name)
            self.assertAlmostEqual(result["combined_delta"], 0.0, msg=f.name)
            self.assertEqual(
                result["scored"], expected_scored[golden["deal_id"]], f.name
            )
            # Widened 3.0 -> 5.0 harness-wide after the repeatability check (see
            # SKILL.md 'Limitations') showed a 3-run range as large as 4.5 pts.
            self.assertEqual(result["tolerance_pts"], 5.0, f.name)
            # Golden files with a breakdown produce deltas; null stays None.
            if g.get("category_breakdown"):
                self.assertIsNotNone(result["category_deltas"], f.name)
                for v in result["category_deltas"].values():
                    self.assertAlmostEqual(v, 0.0, msg=f.name)
            else:
                self.assertIsNone(result["category_deltas"], f.name)


if __name__ == "__main__":
    unittest.main(verbosity=2)
