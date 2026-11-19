#!/usr/bin/env python3
"""Tests for loan_balance_check.py. Run: python test_loan_balance_check.py"""
import json
import os
import sys
import unittest
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import loan_balance_check as lbc  # noqa: E402

# Every case below asserts exact lender figures from the LIVE, gitignored
# data/loan-terms.json (real loan terms -- never committed, so never a fixture). A clean
# checkout (CI, 2026-11-06) has no such file: declare ENV-SKIP per the hook-tests gate
# contract. ONLY absence skips -- a present-but-malformed file still fails loudly below.
#
# The EXPECTED figures (balances, Notion row names, the LTV watch text) live next to it in
# the gitignored data/loan-terms.expected.json (moved out of this file 2026-11-19, OI-408:
# this repo is public). Same contract: absent -> ENV-SKIP, present but broken -> fail.
EXPECTED_PATH = os.path.join(os.path.dirname(lbc.DEFAULT_TERMS), "loan-terms.expected.json")
if not os.path.exists(lbc.DEFAULT_TERMS) or not os.path.exists(EXPECTED_PATH):
    print("CANNOT RUN: live loan terms or expected-figures file absent (%s, %s) -- every "
          "case asserts its real lender figures." % (lbc.DEFAULT_TERMS, EXPECTED_PATH))
    sys.exit(1)

TERMS = lbc.load_terms(lbc.DEFAULT_TERMS)
BY_ID = {l["id"]: l for l in TERMS["loans"]}
with open(EXPECTED_PATH, encoding="utf-8") as _f:
    E = json.load(_f)


def bal(loan_id, d):
    """Expected lender balance for loan_id on date d, from the private expected file."""
    return E["balance"]["%s@%s" % (loan_id, d.isoformat())]


class ExpectedBalance(unittest.TestCase):
    def test_schedule_lookup_matches_lender_documents(self):
        # Exact lender figures read from the schedules on 2026-09-21.
        for loan_id, d in (("park_3540", date(2026, 9, 16)), ("info_lane", date(2026, 9, 10)),
                           ("bm", date(2026, 9, 5))):
            self.assertEqual(lbc.expected_balance(BY_ID[loan_id], d), bal(loan_id, d))

    def test_schedule_before_first_payment_is_original_principal(self):
        for loan_id, d in (("bm", date(2026, 5, 20)), ("park_3540", date(2025, 4, 20))):
            self.assertEqual(lbc.expected_balance(BY_ID[loan_id], d), bal(loan_id, d))

    def test_schedule_day_before_a_payment_keeps_prior_balance(self):
        d = date(2026, 9, 9)
        self.assertEqual(lbc.expected_balance(BY_ID["info_lane"], d), bal("info_lane", d))

    def test_schedule_after_balloon_is_zero(self):
        self.assertEqual(lbc.expected_balance(BY_ID["park_3540"], date(2032, 5, 1)), 0.0)

    def test_anchor_forward_reproduces_ledger_to_the_cent(self):
        # ORA ledger 9/6/2026: principal after the 8/20/2026 installment (expected file).
        for d in (date(2026, 8, 20), date(2026, 8, 19)):
            self.assertEqual(lbc.expected_balance(BY_ID["restoration"], d), bal("restoration", d))

    def test_anchor_matches_register_for_red_branch(self):
        # Register 7/29/2026: ORA 50% principal after 162 payments (expected file).
        full = lbc.expected_balance(BY_ID["red_branch"], date(2026, 7, 29))
        self.assertLess(abs(full * 0.5 - E["red_branch_share_principal@2026-07-29"]), 1.0)

    def test_anchor_stops_amortizing_at_maturity(self):
        # The payment due on the maturity date is the balloon, so the balance stays at the
        # level after the last regular installment (1/20/2027) and is never amortized to zero.
        last_regular = lbc.expected_balance(BY_ID["restoration"], date(2027, 1, 20))
        self.assertEqual(lbc.expected_balance(BY_ID["restoration"], date(2027, 2, 20)), last_regular)
        self.assertEqual(lbc.expected_balance(BY_ID["restoration"], date(2027, 6, 1)), last_regular)
        self.assertGreater(last_regular, E["restoration_last_regular_floor"])

    def test_interest_only_is_constant(self):
        d = date(2027, 1, 1)
        self.assertEqual(lbc.expected_balance(BY_ID["walnut"], d), bal("walnut", d))


class Compare(unittest.TestCase):
    def rows(self, **over):
        base = [dict(r) for r in E["notion_rows"]]
        for r in base:
            if r["name"] in over:
                r["balance"] = over[r["name"]]
        return base

    def test_within_tolerance_is_not_a_difference(self):
        f = lbc.compute(TERMS, date(2026, 9, 21), self.rows(), tolerance=5.0)
        self.assertEqual([x for x in f["differences"] if x.startswith(("bm", "info_lane", "park_3540", "walnut"))], [])

    def test_stale_balance_is_flagged(self):
        f = lbc.compute(TERMS, date(2026, 9, 21),
                        self.rows(**{E["info_lane_row_name"]: E["info_lane_stale_balance"]}))
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
        self.assertTrue(any("park_3540" in w and E["park_3540_ltv_watch_text"] in w for w in f["watch"]))

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
        self.assertEqual(loan["maturity"], E["info_lane_maturity"])

    def test_stale_terms_file_is_noted(self):
        f = lbc.compute(TERMS, date(2027, 3, 1))
        self.assertTrue(any("re-verify" in n for n in f["notes"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
