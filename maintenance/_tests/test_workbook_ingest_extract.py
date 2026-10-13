"""Tests for maintenance/workbook-ingest-extract.py against a SYNTHETIC workbook
(built in a temp dir; the real master is never touched). stdlib unittest + __main__.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

import openpyxl

SCRIPT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "workbook-ingest-extract.py")

NOI_HDR = ["#", "Property", "Oxford Own%", "Oxford Value", "Gross Income (Oxford)",
           "Oxford NOI (scenario-adj)", "Debt Svc (Oxford)"]
RR_HDR = ["Property", "Tenant Name", "Sq Ft", "Annual Rent", "Lease End", "Status",
          "Notice to Vacate"]


def build(path, sepich_rent_delta=0.0, drop_from_export=False):
    wb = openpyxl.Workbook()
    home = wb.active
    home.title = "00_Home"
    home.append(["PORTFOLIO VALUE (Oxford share)", "TOTAL DEBT (Oxford share)", "PORTFOLIO LTV"])
    home.append([3000000.0, 1500000.0, 1000000.0 / 3000000.0])
    noi = wb.create_sheet("EXPORT_PropertyNOI")
    noi.append(NOI_HDR)
    noi.append([1, "A", 1, 1000000.0, 100000.0, 100000.0, 0])
    noi.append([3, "B (50%)", 0.5, 500000.0, 60000.0, 60000.0, 0])
    noi.append([7, "Sepich", 1, 1500000.0, 150000.0, 150000.0, 50000.0])
    src = wb.create_sheet("Master Tenant Rent Roll")
    rr = wb.create_sheet("EXPORT_RentRoll")
    rr.append(RR_HDR)
    src.append(["Title row"])
    src.append(RR_HDR)
    rows = [["55 New Plant Court", "T1", 1000, 100000.0, None, "Active", None],
            ["1900 North Broadway", "T2", 1000, 120000.0, None, "Active", None],
            ["Banwick", "T3", 1000, 90000.0, None, "Active", None],
            ["Zettler", "T4", 1000, 60000.0 + sepich_rent_delta, None, "Active", None],
            ["Zettler", "", 1000, None, None, "Vacant", None]]
    for r in rows:
        src.append(r)
    src.append(["PORTFOLIO TOTAL", "", 5000, 999999.0, None, "", None])
    for r in (rows[:-2] + rows[-1:] if drop_from_export else rows):
        rr.append(r)
    loans = wb.create_sheet("EXPORT_Loans")
    loans.append(["Loan Name", "Role", "Outstanding Balance (Deployed)"])
    loans.append(["X", "Borrower", 900000.0])
    loans.append(["3883 from Oxford", "Borrower", 100000.0])
    loans.append(["L", "Lender", -200000.0])
    internal = wb.create_sheet("EXPORT_Loans_Internal")
    internal.append(["Loan Name", "Current Balance"])
    internal.append(["I1", 600000.0])
    cash = wb.create_sheet("EXPORT_CashBalanceSummary")
    cash.append(["Entity / LLC", "Current Cash Balance"])
    cash.append(["E1", 10.0])
    cash.append(["E2", 5.5])
    ins = wb.create_sheet("EXPORT_InsuranceRenewals")
    ins.append(["RowID", "Status"])
    ins.append(["P1", "EXPIRED"])
    ins.append(["P2", "Current"])
    chk = wb.create_sheet("EXPORT_MonthlyChecklist")
    chk.append(["Loan / Property", "OCT"])
    chk.append(["a", "\u2705"])
    chk.append(["b", "\u2610"])
    chk.append(["c", "\u2014"])
    wb.save(path)


def run(path):
    env = dict(os.environ, ORA_WORKBOOK_PATH=path)
    p = subprocess.run([sys.executable, SCRIPT], env=env, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT)
    out = p.stdout.decode("utf-8", "replace")
    res = None
    for line in out.splitlines():
        if line.startswith("RESULT_JSON="):
            res = json.loads(line[len("RESULT_JSON="):])
    return p.returncode, out, res


class ExtractTests(unittest.TestCase):
    def test_clean_workbook_passes_every_tie_out(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "m.xlsx")
            build(path)
            rc, out, res = run(path)
            self.assertEqual(rc, 0, out)
            self.assertEqual(res["failed_tie_outs"], [])
            self.assertEqual(res["tie_outs"]["T5_rentroll_to_noi"]["total_noi_gross"], 310000.0)
            self.assertEqual(res["tie_outs"]["T6_cash"]["total"], 15.5)
            self.assertEqual(res["insurance"]["expired"], ["P1"])
            self.assertEqual(res["checklist_oct"], {"done": 1, "total": 2})

    def test_sepich_rollup_variance_is_named_to_the_cent(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "m.xlsx")
            build(path, sepich_rent_delta=-19096.20)
            rc, out, res = run(path)
            self.assertEqual(rc, 1, out)
            self.assertIn("T5_rentroll_to_noi", res["failed_tie_outs"])
            self.assertIn("T5 VARIANCE line 7", out)
            self.assertIn("-19096.20", out)

    def test_export_missing_a_source_tenant_is_flagged_but_t5_ties_to_source(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "m.xlsx")
            build(path, drop_from_export=True)
            rc, out, res = run(path)
            self.assertEqual(rc, 1, out)
            self.assertEqual(res["failed_tie_outs"], ["T5b_export_rentroll_complete"])
            gap = res["tie_outs"]["T5b_export_rentroll_complete"]["gaps"][0]
            self.assertEqual((gap["property"], gap["missing"]), ("zettler", 60000.0))
            self.assertTrue(res["tie_outs"]["T5_rentroll_to_noi"]["pass"])
            self.assertIn("T5b EXPORT_RentRoll GAP zettler", out)

    def test_unmapped_rent_roll_property_fails_not_silently_dropped(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "m.xlsx")
            build(path)
            wb = openpyxl.load_workbook(path)
            wb["Master Tenant Rent Roll"].append(["999 New Place", "T9", 1, 5.0, None, "Active", None])
            wb.save(path)
            rc, out, res = run(path)
            self.assertEqual(rc, 1, out)
            self.assertEqual(res["tie_outs"]["T5_rentroll_to_noi"]["unmapped_rent_roll_properties"],
                             ["999 new place"])

    def test_missing_file_exits_2_never_zeros(self):
        rc, out, res = run(os.path.join(tempfile.gettempdir(), "does-not-exist-ora.xlsx"))
        self.assertEqual(rc, 2)
        self.assertIsNone(res)
        self.assertIn("COULD NOT READ", out)

    def test_script_never_writes_the_workbook(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "m.xlsx")
            build(path)
            before = (os.path.getmtime(path), os.path.getsize(path))
            run(path)
            self.assertEqual((os.path.getmtime(path), os.path.getsize(path)), before)
        src = open(SCRIPT, encoding="utf-8").read()
        self.assertNotIn(".save(", src)


if __name__ == "__main__":
    unittest.main(verbosity=2)
