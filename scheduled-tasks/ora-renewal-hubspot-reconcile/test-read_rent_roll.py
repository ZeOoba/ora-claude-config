"""Tests for read_rent_roll.py -- the pure parse/gate logic only (no workbook I/O).

Run: python test-read_rent_roll.py
"""
import datetime as dt
import importlib.util
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("rrr", os.path.join(_HERE, "read_rent_roll.py"))
rrr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rrr)

HDR = ("Property", "Tenant Name", "Unit", "Company", "Sq Ft", "Monthly Rent", "Rent / SF",
       "Lease Start", "Lease End", "Escalation Date", "Escalation %", "Status",
       "Notice to Vacate", "Annual Rent", "Esc. Exception", "Occupancy Class", "Lease Type")


def _row(prop, tenant, unit, company, end, status="Active", notice=None):
    return (prop, tenant, unit, company, 1200, 1000, 10.0, dt.datetime(2024, 1, 1), end,
            None, None, status, notice, 12000, None, None, "Term")


def _sheet(as_of="As of September 19, 2026   |   3 tenants   |   ...", data=()):
    return [(None,), (as_of,), (None,), (None,), HDR] + list(data)


class ParseTests(unittest.TestCase):
    def test_stops_at_portfolio_totals_block(self):
        rows = _sheet(data=[
            _row("A", "T1", "1", "Co1", dt.datetime(2027, 1, 31)),
            _row("A", "T2", "2", "Co2", dt.datetime(2027, 2, 28)),
            ("PORTFOLIO TOTALS", "138 tenants", None, None, 1, 1, 1, None, None, None,
             None, "129A", 0.07, None, None, None, None),
            ("Gross SF (all roster rows)", 513158, "Sum of col E", None),
        ])
        out = rrr.parse(rows)
        self.assertEqual([r["Tenant Name"] for r in out["rows"]], ["T1", "T2"])

    def test_skips_blank_tenant_rows(self):
        rows = _sheet(data=[_row("A", None, "1", "VACANT", None),
                            _row("A", "T1", "2", "Co1", dt.datetime(2027, 1, 31))])
        self.assertEqual(len(rrr.parse(rows)["rows"]), 1)

    def test_dates_iso_and_excel_serials_converted(self):
        rows = _sheet(data=[_row("A", "T1", "1", "Co1", 46387.0)])  # COM serial
        self.assertEqual(rrr.parse(rows)["rows"][0]["Lease End"], "2026-12-31")
        rows = _sheet(data=[_row("A", "T1", "1", "Co1", dt.datetime(2026, 12, 31))])
        self.assertEqual(rrr.parse(rows)["rows"][0]["Lease End"], "2026-12-31")

    def test_rows_without_lease_end_are_surfaced(self):
        rows = _sheet(data=[_row("2207 Northwood", "Melissa Drew", "Sign", "InSite Build",
                                 None, status=None)])
        out = rrr.parse(rows)
        self.assertEqual(len(out["no_lease_end"]), 1)
        self.assertEqual(out["no_lease_end"][0]["Company"], "InSite Build")

    def test_unusable_lease_end_text_is_surfaced(self):
        rows = _sheet(data=[_row("A", "T1", "1", "Co1", "MTM"),
                            _row("A", "T2", "2", "Co2", 5.0)])  # not a plausible serial
        self.assertEqual(len(rrr.parse(rows)["no_lease_end"]), 2)

    def test_end_marker_recorded(self):
        with_marker = _sheet(data=[_row("A", "T1", "1", "Co1", None),
                                   ("PORTFOLIO TOTALS", "1 tenants")])
        self.assertTrue(rrr.parse(with_marker)["hit_end_marker"])
        self.assertFalse(rrr.parse(_sheet(data=[_row("A", "T1", "1", "Co1", None)]))["hit_end_marker"])

    def test_as_of_and_header_count_parsed(self):
        out = rrr.parse(_sheet(data=[_row("A", "T1", "1", "Co1", None)]))
        self.assertEqual(out["as_of"], "2026-09-19")
        self.assertEqual(out["header_tenant_count"], 3)

    def test_missing_header_row_raises(self):
        bad = [(None,), ("As of September 19, 2026",), (None,), (None,), ("Nope",)]
        with self.assertRaises(ValueError):
            rrr.parse(bad)


class GateTests(unittest.TestCase):
    TODAY = dt.date(2026, 9, 21)

    def _parsed(self, as_of="2026-09-19", n=138, header=None, marker=True):
        return {"as_of": as_of, "header_tenant_count": n if header is None else header,
                "hit_end_marker": marker,
                "rows": [{"Tenant Name": "t%d" % i} for i in range(n)]}

    def test_fresh_in_range_passes(self):
        self.assertEqual(rrr.gate(self._parsed(), self.TODAY), [])

    def test_stale_fails(self):
        self.assertTrue(rrr.gate(self._parsed(as_of="2026-09-13"), self.TODAY))

    def test_exactly_seven_days_passes(self):
        self.assertEqual(rrr.gate(self._parsed(as_of="2026-09-14"), self.TODAY), [])

    def test_unparseable_as_of_fails(self):
        self.assertTrue(rrr.gate(self._parsed(as_of=None), self.TODAY))

    def test_future_as_of_fails(self):
        self.assertTrue(rrr.gate(self._parsed(as_of="2026-09-22"), self.TODAY))

    def test_missing_end_marker_fails(self):
        self.assertTrue(rrr.gate(self._parsed(marker=False), self.TODAY))

    def test_header_count_mismatch_fails(self):
        self.assertTrue(rrr.gate(self._parsed(n=138, header=150), self.TODAY))
        self.assertEqual(rrr.gate(self._parsed(n=138, header=140), self.TODAY), [])

    def test_count_out_of_range_fails(self):
        self.assertTrue(rrr.gate(self._parsed(n=99), self.TODAY))
        self.assertTrue(rrr.gate(self._parsed(n=201), self.TODAY))


if __name__ == "__main__":
    sys.exit(0 if unittest.main(exit=False).result.wasSuccessful() else 1)
