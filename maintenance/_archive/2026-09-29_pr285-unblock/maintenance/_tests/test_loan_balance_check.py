#!/usr/bin/env python3
"""Tests for loan_balance_check.py. Run: python test_loan_balance_check.py"""
import os
import sys
import unittest
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import loan_balance_check as lbc  # noqa: E402

TERMS = lbc.load_terms(lbc.DEFAULT_TERMS)
BY_ID = {l["id"]: l for l in TERMS["loans"]}


class ExpectedBalance(unittest.TestCase):
    def test_schedule_lookup_matches_lender_documents(self):
        # Exact lender figures read from the schedules on 2026-09-21.
        self.assertEqual(lbc.expected_balance(BY_ID["park_3540"], date(2026, 9, 16)), 2437576.94)
        self.assertEqual(lbc.expected_balance(BY_ID["info_lane"], date(2026, 9, 10)), 2760611.91)
        self.assertEqual(lbc.expected_balance(BY_ID["bm"], date(2026, 9, 5)), 3707567.24)

    def test_schedule_before_first_payment_is_original_principal(self):
        self.assertEqual(lbc.expected_balance(BY_ID["bm"], date(2026, 5, 20)), 3725000.0)
        self.assertEqual(lbc.expected_balance(BY_ID["park_3540"], date(2025, 4, 20)), 2500000.0)

    def test_schedule_day_before_a_payment_keeps_prior_balance(self):
        self.assertEqual(lbc.expected_balance(BY_ID["info_lane"], date(2026, 9, 9)), 2765070.31)

    def test_schedule_after_balloon_is_zero(self):
        self.assertEqual(lbc.expected_balance(BY_ID["park_3540"], date(2032, 5, 1)), 0.0)

    def test_anchor_forward_reproduces_ledger_to_the_cent(self):
        # ORA ledger 9/6/2026: principal after the 8/20/2026 installment is 1,957,526.84.
        self.assertEqual(lbc.expected_balance(BY_ID["restoration"], date(2026, 8, 20)), 1957526.84)
        self.assertEqual(lbc.expected_balance(BY_ID["restoration"], date(2026, 8, 19)), 1959543.91)

    def test_anchor_matches_register_for_red_branch(self):
        # Register 7/29/2026: ORA 50% principal 1,328,736 after 162 payments.
        full = lbc.expected_balance(BY_ID["red_branch"], date(2026, 7, 29))
        self.assertLess(abs(full * 0.5 - 1328736), 1.0)

    def test_anchor_stops_amortizing_at_maturity(self):
        # The payment due on the maturity date is the balloon, so the balance stays at the
        # level after the last regular installment (1/20/2027) and is never amortized to zero.
        last_regular = lbc.expected_balance(BY_ID["restoration"], date(2027, 1, 20))
        self.assertEqual(lbc.expected_balance(BY_ID["restoration"], date(2027, 2, 20)), last_regular)
        self.assertEqual(lbc.expected_balance(BY_ID["restoration"], date(2027, 6, 1)), last_regular)
        self.assertGreater(last_regular, 1_800_000)

    def test_interest_only_is_constant(self):
        self.assertEqual(lbc.expected_balance(BY_ID["walnut"], date(2027, 1, 1)), 252000.0)


class Compare(unittest.TestCase):
    def rows(self, **over):
        base = [{"name": "Banwick/Morrison - Symetra #11153", "balance": 3707567.24, "maturity": "2031-06-05"},
                {"name": "29000 Information Lane - Symetra #10258", "balance": 2760611.91, "maturity": "2030-12-10"},
                {"name": "3540 E. Fifth Ave - Park National Bank", "balance": 2437576.94, "maturity": "2032-04-16"},
                {"name": "9050 Red Branch Rd - WoodmenLife", "balance": None, "maturity": "2028-01-01"},
                {"name": "Restoration Church Trust Balloon", "balance": None, "maturity": "2027-02-20"},
                {"name": "485 S. Walnut St. - Oxford Capital IO Balloon", "balance": 252000.0, "maturity": "2028-09-26"}]
        for r in base:
            if r["name"] in over:
                r["balance"] = over[r["name"]]
        return base

    def test_within_tolerance_is_not_a_difference(self):
        f = lbc.compute(TERMS, date(2026, 9, 21), self.rows(), tolerance=5.0)
        self.assertEqual([x for x in f["differences"] if x.startswith(("bm", "info_lane", "park_3540", "walnut"))], [])

    def test_stale_balance_is_flagged(self):
        f = lbc.compute(TERMS, date(2026, 9, 21), self.rows(**{"29000 Information Lane - Symetra #10258": 2782697.78}))
        self.assertTrue(any(x.startswith("info_lane") and "difference" in x for x in f["differences"]))

    def test_missing_notion_record_is_flagged(self):
        rows = [r for r in self.rows() if "Walnut" not in r["name"]]
        f = lbc.compute(TERMS, date(2026, 9, 21), rows)
        self.assertTrue(any(x.startswith("walnut") and "no Notion" in x for x in f["differences"]))

    def test_share_basis_applied_to_red_branch(self):
        f = lbc.compute(TERMS, date(2026, 9, 21), self.rows())
        rb = next(r for r in f["loans"] if r["id"] == "red_branch")
        self.assertAlmostEqual(rb["expected_share"], rb["expected_full"] * 0.5, places=2)


class Watch(unittest.TestCase):
    def test_3540_ltv_above_ceiling_is_on_watch_list(self):
        f = lbc.compute(TERMS, date(2026, 9, 21))
        self.assertTrue(any("park_3540" in w and "66.8%" in w for w in f["watch"]))

    def test_receivables_have_no_ltv_watch(self):
        f = lbc.compute(TERMS, date(2026, 9, 21))
        self.assertFalse(any(w.startswith(("walnut", "restoration")) and "LTV" in w for w in f["watch"]))

    def test_maturity_conflict_note_is_surfaced(self):
        import copy
        terms = copy.deepcopy(TERMS)
        next(l for l in terms["loans"] if l["id"] == "info_lane")["maturity_note"] = "UNRESOLVED: test conflict"
        f = lbc.compute(terms, date(2026, 9, 21))
        self.assertTrue(any("info_lane" in w and "UNRESOLVED" in w for w in f["watch"]))

    def test_info_lane_maturity_is_settled_by_the_executed_note(self):
        f = lbc.compute(TERMS, date(2026, 9, 21))
        self.assertFalse(any("info_lane" in w and "UNRESOLVED" in w for w in f["watch"]))
        loan = next(l for l in TERMS["loans"] if l["id"] == "info_lane")
        self.assertEqual(loan["maturity"], "2030-12-10")

    def test_stale_terms_file_is_noted(self):
        f = lbc.compute(TERMS, date(2027, 3, 1))
        self.assertTrue(any("re-verify" in n for n in f["notes"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
