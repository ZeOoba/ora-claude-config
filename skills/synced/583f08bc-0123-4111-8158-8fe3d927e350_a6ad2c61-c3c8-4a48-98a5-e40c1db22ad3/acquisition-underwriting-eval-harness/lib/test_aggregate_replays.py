"""Tests for lib/aggregate_replays.py — N-replay aggregation (added 2026-08-14).

Written FIRST (TDD), unittest style to match test_diff_verdict.py /
test_record_run.py. Run from the harness root:

    python -m unittest discover -s lib -p 'test_*.py' -v
"""

import unittest

from aggregate_replays import (
    CATEGORY_KEY_MAP,
    aggregate_replays,
    normalize_category_keys,
)
from diff_verdict import diff_verdict


def _replay(combined, breakdown=None, **kw):
    r = {"combined": combined}
    if breakdown is not None:
        r["category_breakdown"] = breakdown
    r.update(kw)
    return r


class TestCoreAggregation(unittest.TestCase):
    def test_combined_is_the_mean_not_the_first_run(self):
        out = aggregate_replays([_replay(25.0), _replay(28.5), _replay(27.0)])
        self.assertEqual(out["combined"], 26.83)
        self.assertEqual(out["aggregate"]["n"], 3)

    def test_reports_dispersion_stats(self):
        out = aggregate_replays([_replay(25.0), _replay(32.0), _replay(28.5)])
        agg = out["aggregate"]
        self.assertEqual(agg["combined_min"], 25.0)
        self.assertEqual(agg["combined_max"], 32.0)
        self.assertEqual(agg["combined_range"], 7.0)
        self.assertEqual(agg["combined_stdev"], 3.5)
        self.assertEqual(agg["combined_samples"], [25.0, 32.0, 28.5])

    def test_sem_shrinks_with_n_which_is_the_whole_point(self):
        """SEM must be stdev/sqrt(n) — the justification for gating on a mean."""
        out = aggregate_replays([_replay(25.0), _replay(30.0), _replay(27.5)])
        self.assertEqual(out["aggregate"]["combined_stdev"], 2.5)
        self.assertEqual(out["aggregate"]["combined_sem"], 1.44)  # 2.5 / sqrt(3)

    def test_port_sheldon_n6_2026_08_14_contaminated_snapshot(self):
        """HISTORICAL regression pin, not the current golden. These are the 6 real
        2026-08-14 samples (including the SKILL.md-citation-leaked run 1, 32.0) --
        golden_set/2196-port-sheldon-st-jenison-mi.json no longer uses 28.08 as its
        baseline (rebaselined 2026-08-15 to 26.81 on 8 leakage-excluded samples, see
        the companion test below). Kept to pin aggregate_replays()'s arithmetic
        against a known historical input set, independent of what golden_set stores
        today."""
        samples = [32.0, 27.5, 28.5, 25.0, 28.5, 27.0]
        out = aggregate_replays([_replay(s) for s in samples])
        self.assertEqual(out["combined"], 28.08)
        self.assertEqual(out["aggregate"]["combined_range"], 7.0)
        self.assertEqual(out["aggregate"]["combined_stdev"], 2.31)

    def test_port_sheldon_n8_2026_08_15_leakage_excluded_reproduces_current_golden(self):
        """The 8 samples golden_set/2196-port-sheldon-st-jenison-mi.json's golden.combined
        is actually computed from (run 1, the 32.0 SKILL.md-citation leak, excluded) must
        yield 26.81 -- pins the CURRENT golden, unlike the historical test above."""
        samples = [27.5, 28.5, 25.0, 28.5, 27.0, 25.0, 26.0, 27.0]
        out = aggregate_replays([_replay(s) for s in samples])
        self.assertEqual(out["combined"], 26.81)
        self.assertEqual(out["aggregate"]["combined_range"], 3.5)
        self.assertEqual(out["aggregate"]["combined_stdev"], 1.39)


class TestSingleSample(unittest.TestCase):
    def test_single_replay_is_flagged_not_silently_treated_as_a_mean(self):
        out = aggregate_replays([_replay(29.0)])
        agg = out["aggregate"]
        self.assertEqual(out["combined"], 29.0)
        self.assertIs(agg["single_sample"], True)
        self.assertEqual(agg["n"], 1)
        self.assertIsNone(agg["combined_stdev"])
        self.assertIsNone(agg["combined_sem"])
        self.assertEqual(agg["combined_range"], 0)

    def test_multi_replay_is_not_flagged_single_sample(self):
        out = aggregate_replays([_replay(29.0), _replay(28.0)])
        self.assertIs(out["aggregate"]["single_sample"], False)


class TestErrorHandling(unittest.TestCase):
    def test_empty_list_raises(self):
        with self.assertRaisesRegex(ValueError, "non-empty"):
            aggregate_replays([])

    def test_non_numeric_combined_raises_rather_than_being_dropped(self):
        """A failed replay must surface as an error, never vanish into the mean."""
        for bad in (None, "29.0", {}, [], True, False):
            with self.subTest(bad=bad):
                with self.assertRaisesRegex(ValueError, "must be a number"):
                    aggregate_replays([_replay(28.0), {"combined": bad}])

    def test_error_names_the_offending_index(self):
        with self.assertRaisesRegex(ValueError, r"replays\[1\]"):
            aggregate_replays([_replay(28.0), {"combined": None}])


class TestCategoryKeyNormalization(unittest.TestCase):
    def test_display_names_fold_to_snake_case(self):
        got = normalize_category_keys({
            "Product & Physical": 13.0,
            "Market & Location": 6.0,
            "Value-Add Optionality": 8.0,
        })
        self.assertEqual(
            got,
            {"product_physical": 13.0, "market_location": 6.0, "value_add": 8.0},
        )

    def test_snake_case_keys_pass_through_unchanged(self):
        got = normalize_category_keys({"product_physical": 13.0, "basis": 0.0})
        self.assertEqual(got, {"product_physical": 13.0, "basis": 0.0})

    def test_unmapped_key_is_preserved_not_dropped(self):
        self.assertEqual(
            normalize_category_keys({"Some New Category": 4.0}),
            {"Some New Category": 4.0},
        )

    def test_every_mapped_value_is_a_snake_case_target(self):
        for target in CATEGORY_KEY_MAP.values():
            with self.subTest(target=target):
                self.assertEqual(target, target.lower())
                self.assertNotIn(" ", target)
                self.assertNotIn("&", target)

    def test_every_golden_category_key_is_a_normalization_target(self):
        """Guard against a golden-set key the map can never produce."""
        from pathlib import Path
        import json

        golden_dir = Path(__file__).resolve().parent.parent / "golden_set"
        targets = set(CATEGORY_KEY_MAP.values())
        for path in golden_dir.glob("*.json"):
            bd = json.loads(path.read_text(encoding="utf-8"))["golden"].get(
                "category_breakdown"
            ) or {}
            for key in bd:
                if key.endswith("_flag") or key.endswith("_note"):
                    continue  # annotation entries, not scored categories
                with self.subTest(file=path.name, key=key):
                    self.assertIn(key, targets)

    def test_colliding_keys_with_different_values_raise(self):
        """Silently keeping the last value is the exact failure this module prevents."""
        with self.assertRaisesRegex(ValueError, "collision"):
            normalize_category_keys(
                {"Product & Physical": 13.0, "product_physical": 11.0}
            )

    def test_colliding_keys_with_identical_values_are_harmless(self):
        got = normalize_category_keys(
            {"Product & Physical": 13.0, "product_physical": 13.0}
        )
        self.assertEqual(got, {"product_physical": 13.0})

    def test_aggregate_normalizes_before_averaging(self):
        """Display-keyed and snake-keyed replays of the same deal must combine."""
        out = aggregate_replays([
            _replay(13.0, {"Product & Physical": 13.0}),
            _replay(11.0, {"product_physical": 11.0}),
        ])
        self.assertEqual(out["category_breakdown"], {"product_physical": 12.0})


class TestCategoryNullHandling(unittest.TestCase):
    def test_null_category_counts_as_zero_so_means_sum_to_mean_combined(self):
        """Null = points not supported = 0 contribution, matching the replay's total."""
        out = aggregate_replays([
            _replay(12.0, {"product_physical": 7.0, "seller_motivation": 5.0}),
            _replay(7.0, {"product_physical": 7.0, "seller_motivation": None}),
        ])
        bd = out["category_breakdown"]
        self.assertEqual(bd["seller_motivation"], 2.5)  # (5 + 0) / 2, not 5.0
        self.assertEqual(round(sum(bd.values()), 2), out["combined"])
        self.assertEqual(out["combined"], 9.5)

    def test_null_counts_are_reported_so_gaps_stay_visible(self):
        out = aggregate_replays([
            _replay(7.0, {"product_physical": 7.0, "seller_motivation": None}),
            _replay(7.0, {"product_physical": 7.0, "seller_motivation": None}),
            _replay(12.0, {"product_physical": 7.0, "seller_motivation": 5.0}),
        ])
        counts = out["aggregate"]["category_null_counts"]
        self.assertEqual(counts["seller_motivation"], 2)
        self.assertEqual(counts["product_physical"], 0)

    def test_category_present_in_only_some_replays_is_still_aggregated(self):
        out = aggregate_replays([
            _replay(5.0, {"basis": 5.0}),
            _replay(5.0, {"basis": 5.0, "value_add": 0.0}),
        ])
        self.assertEqual(set(out["category_breakdown"]), {"basis", "value_add"})

    def test_no_breakdowns_anywhere_yields_none(self):
        out = aggregate_replays([_replay(25.0), _replay(27.0)])
        self.assertIsNone(out["category_breakdown"])

    def test_replay_with_no_breakdown_is_skipped_not_zero_filled(self):
        """Zero-filling an absent breakdown manufactures a phantom category delta.

        Regression guard: [combined 28 w/ {basis: 28}] + [combined 28, no
        breakdown] must NOT yield basis 14.0 against a Combined mean of 28.0.
        """
        out = aggregate_replays([_replay(28.0, {"basis": 28.0}), _replay(28.0)])
        self.assertEqual(out["combined"], 28.0)
        self.assertEqual(out["category_breakdown"], {"basis": 28.0})
        self.assertEqual(out["aggregate"]["replays_without_breakdown"], 1)

    def test_replays_without_breakdown_counted_as_zero_when_all_present(self):
        out = aggregate_replays([
            _replay(5.0, {"basis": 5.0}),
            _replay(7.0, {"basis": 7.0}),
        ])
        self.assertEqual(out["aggregate"]["replays_without_breakdown"], 0)

    def test_empty_dict_breakdown_is_treated_as_absent(self):
        out = aggregate_replays([_replay(28.0, {"basis": 28.0}), _replay(28.0, {})])
        self.assertEqual(out["category_breakdown"], {"basis": 28.0})
        self.assertEqual(out["aggregate"]["replays_without_breakdown"], 1)


class TestScalarFields(unittest.TestCase):
    def test_scalar_nulls_are_excluded_from_their_mean_not_zeroed(self):
        """Unlike category points, a null scalar is 'unknown', not 'zero'."""
        out = aggregate_replays([
            _replay(25.0, economics=10.0),
            _replay(27.0, economics=None),
        ])
        self.assertEqual(out["economics"], 10.0)

    def test_all_null_scalar_stays_none(self):
        out = aggregate_replays([_replay(25.0, economics=None), _replay(27.0)])
        self.assertIsNone(out["economics"])

    def test_p_exec_and_quality_are_averaged(self):
        out = aggregate_replays([
            _replay(25.0, quality=25.0, p_exec_pct=30.0),
            _replay(27.0, quality=27.0, p_exec_pct=20.0),
        ])
        self.assertEqual(out["quality"], 26.0)
        self.assertEqual(out["p_exec_pct"], 25.0)


class TestStringLabels(unittest.TestCase):
    def test_tier_label_carried_from_first_replay(self):
        out = aggregate_replays([
            _replay(25.0, verdict_tier="PASS-band"),
            _replay(27.0, verdict_tier="PASS-band"),
        ])
        self.assertEqual(out["verdict_tier"], "PASS-band")
        self.assertNotIn("verdict_tier_variants", out["aggregate"])

    def test_disagreeing_tier_labels_are_all_surfaced(self):
        """A run where replays disagreed on tier must not hide behind run 1's label."""
        out = aggregate_replays([
            _replay(25.0, verdict_tier="PASS-band"),
            _replay(62.0, verdict_tier="T2 WATCH"),
        ])
        self.assertEqual(
            out["aggregate"]["verdict_tier_variants"], ["PASS-band", "T2 WATCH"]
        )

    def test_missing_tier_everywhere_is_none(self):
        out = aggregate_replays([_replay(25.0), _replay(27.0)])
        self.assertIsNone(out["verdict_tier"])


class TestIntegrationWithDiffVerdict(unittest.TestCase):
    def test_aggregate_output_feeds_diff_verdict(self):
        golden = {
            "deal_id": "test-deal",
            "confidence": "HIGH",
            "golden": {
                "combined": 28.08,
                "verdict_tier": "PASS-band",
                "category_breakdown": {"product_physical": 12.75},
            },
            "diff_policy": {"tolerance_combined_pts": 5.0},
        }
        observed = aggregate_replays([
            _replay(32.0, {"Product & Physical": 12.0}, verdict_tier="PASS-band"),
            _replay(27.5, {"Product & Physical": 13.5}, verdict_tier="PASS-band"),
            _replay(28.5, {"Product & Physical": 13.5}, verdict_tier="PASS-band"),
            _replay(25.0, {"Product & Physical": 11.0}, verdict_tier="PASS-band"),
            _replay(28.5, {"Product & Physical": 14.5}, verdict_tier="PASS-band"),
            _replay(27.0, {"Product & Physical": 12.0}, verdict_tier="PASS-band"),
        ])
        result = diff_verdict(golden, observed)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["combined_observed"], 28.08)
        self.assertEqual(result["combined_delta"], 0.0)
        # The normalization fix: per-category deltas resolve instead of silently None.
        self.assertEqual(result["category_deltas"], {"product_physical": 0.0})

    def test_aggregate_block_survives_into_the_diff_result(self):
        """The audit trail must reach record_run's snapshot, not die in-session."""
        golden = {
            "deal_id": "test-deal",
            "confidence": "HIGH",
            "golden": {"combined": 28.0},
            "diff_policy": {"tolerance_combined_pts": 5.0},
        }
        observed = aggregate_replays([_replay(27.0), _replay(28.0), _replay(29.0)])
        result = diff_verdict(golden, observed)
        self.assertIsNotNone(result["aggregate"])
        self.assertEqual(result["aggregate"]["n"], 3)
        self.assertEqual(result["aggregate"]["combined_samples"], [27.0, 28.0, 29.0])

    def test_unaggregated_observed_still_works_and_reports_no_aggregate(self):
        """Backward compatibility: a plain single-replay observed dict must not break."""
        golden = {
            "deal_id": "test-deal",
            "confidence": "HIGH",
            "golden": {"combined": 28.0},
            "diff_policy": {"tolerance_combined_pts": 5.0},
        }
        result = diff_verdict(golden, {"combined": 28.0, "verdict_tier": "PASS-band"})
        self.assertIsNone(result["aggregate"])
        self.assertEqual(result["status"], "PASS")

    def test_degraded_n_is_called_out_in_notes(self):
        golden = {
            "deal_id": "test-deal",
            "confidence": "HIGH",
            "golden": {"combined": 28.0},
            "diff_policy": {"tolerance_combined_pts": 5.0},
        }
        result = diff_verdict(golden, aggregate_replays([_replay(28.0)]))
        self.assertTrue(any("degraded measurement" in n for n in result["notes"]))

    def test_spread_exceeding_tolerance_is_called_out_in_notes(self):
        """Port Sheldon's real condition: replays disagree by more than the gate width."""
        golden = {
            "deal_id": "test-deal",
            "confidence": "HIGH",
            "golden": {"combined": 28.08},
            "diff_policy": {"tolerance_combined_pts": 5.0},
        }
        observed = aggregate_replays([_replay(25.0), _replay(32.0), _replay(27.0)])
        result = diff_verdict(golden, observed)
        self.assertEqual(result["status"], "PASS")  # mean is fine...
        # ...but the disagreement is flagged rather than hidden behind the PASS.
        self.assertTrue(any("exceeds this deal's own" in n for n in result["notes"]))

    def test_tight_spread_produces_no_spread_warning(self):
        golden = {
            "deal_id": "test-deal",
            "confidence": "HIGH",
            "golden": {"combined": 28.0},
            "diff_policy": {"tolerance_combined_pts": 5.0},
        }
        observed = aggregate_replays([_replay(27.0), _replay(28.0), _replay(29.0)])
        result = diff_verdict(golden, observed)
        self.assertFalse(any("exceeds this deal's own" in n for n in result["notes"]))

    def test_single_worst_case_draw_would_flag_but_the_mean_does_not(self):
        """The regression this change exists to prevent: n=1 noise reading as drift."""
        golden = {
            "deal_id": "test-deal",
            "confidence": "HIGH",
            "golden": {"combined": 32.0, "verdict_tier": "PASS-band"},
            "diff_policy": {"tolerance_combined_pts": 5.0},
        }
        lone_low_draw = aggregate_replays([_replay(25.0)])
        self.assertEqual(diff_verdict(golden, lone_low_draw)["status"], "FLAG")

        mean_of_three = aggregate_replays([
            _replay(25.0), _replay(28.5), _replay(32.0)
        ])
        self.assertEqual(diff_verdict(golden, mean_of_three)["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
