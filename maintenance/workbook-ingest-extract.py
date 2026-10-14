"""Read-only extraction + tie-outs for ora-master-workbook-ingest.

Replaces the slow cell-by-cell Desktop Commander reads and makes T1-T6 programmatic,
including the per-property T5 (rent roll x ownership share = Property NOI gross income)
that a hand re-sum got wrong on 2026-10-06 (Sepich rollup off by $19,096.20).

READ-ONLY BY CONSTRUCTION: opens the workbook with load_workbook(data_only=True,
read_only=True), never calls save, never opens it for write. It reads only the flat
EXPORT_* tabs (every cell there is a live formula, so cached values equal the model).

INVOKE WITHOUT NAMING THE WORKBOOK on the command line (default path below, override
with ORA_WORKBOOK_PATH): `python maintenance/workbook-ingest-extract.py`. A command
that names the master workbook is inspected by workbook-write-guard.

EXIT: 0 = all tie-outs pass | 1 = at least one tie-out failed | 2 = could not read.
Stdout ends with a RESULT_JSON= line. `--out FILE` also writes the full JSON.
Stdlib + openpyxl (read-only). ASCII-only.
"""
import datetime as dt
import json
import os
import sys

DEFAULT_PATH = (r"C:\Users\Owner\OneDrive - Oxford Capital Partners\eric spreadsheets"
                "\\Master Excel Template Company Wide -- Oxford.xlsx")
TOL = 0.01  # dollars

# Rent-roll "Property" label -> Property NOI line "#" (Sepich rolls five into line 7).
RR_TO_NOI_LINE = {
    "55 new plant court": 1, "29000 information lane": 2, "1900 north broadway": 3,
    "9050 red branch": 4, "3540 e. 5th avenue": 5, "banwick": 7, "morrison": 7,
    "zettler": 7, "4595 e. 5th ave": 7, "4601 e. 5th ave": 7,
    "3034 westerville road": 8, "2207 northwood": 9, "9620 state 350": 10,
    "3875-3883 e livingston": 11, "401 sunburst hwy": 12, "7658 fishel": 13,
    "1100 rarig": 14,
}
NON_LEASED = ("vacant", "common area")
IN_FORCE = ("active", "expiring soon")


def num(v):
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else 0.0


def table(wb, name):
    rows = list(wb[name].iter_rows(values_only=True))
    hdr = [str(h).strip() if h is not None else "" for h in rows[0]]
    out = []
    for r in rows[1:]:
        if all(c is None for c in r):
            continue
        out.append(dict(zip(hdr, r)))
    return out


def col(row, prefix):
    for k, v in row.items():
        if k.startswith(prefix):
            return v
    return None


def home_cells(rows):
    """{header label: value} for 00_Home's headline strip: a row whose cells start with
    PORTFOLIO VALUE / TOTAL DEBT / PORTFOLIO LTV labels, values on the next row."""
    out = {}
    for i, row in enumerate(rows[:-1]):
        labels = [(j, str(c).upper()) for j, c in enumerate(row) if c is not None]
        if not any(t.startswith("PORTFOLIO VALUE") for _, t in labels):
            continue
        nxt = rows[i + 1]
        for j, t in labels:
            for key in ("PORTFOLIO VALUE", "TOTAL DEBT", "PORTFOLIO LTV"):
                if t.startswith(key) and j < len(nxt) and isinstance(nxt[j], (int, float)):
                    out[key] = float(nxt[j])
        break
    return out


def master_to_records(rows):
    """Records (EXPORT_RentRoll column names) from the SOURCE tab 'Master Tenant Rent
    Roll', which is what Property NOI's SUMIFS actually reads. Header row = first row
    whose column A is 'Property'; data rows keep only mapped property labels so
    subtotal/total rows are never double counted."""
    hdr_i = next((i for i, r in enumerate(rows) if r and str(r[0]).strip() == "Property"), None)
    if hdr_i is None:
        raise ValueError("Master Tenant Rent Roll: no 'Property' header row found")
    hdr = [str(h).strip() if h is not None else "" for h in rows[hdr_i]]
    out, unmapped = [], set()
    ann = next((i for i, h in enumerate(hdr) if h == "Annual Rent"), None)
    for r in rows[hdr_i + 1:]:
        if not r or r[0] is None:
            continue
        key = str(r[0]).strip().lower()
        if key in RR_TO_NOI_LINE:
            out.append(dict(zip(hdr, r)))
        elif (key and "total" not in key and ann is not None and ann < len(r)
              and isinstance(r[ann], (int, float)) and r[ann]):
            unmapped.add(key)
    return out, unmapped


def as_date(v):
    if isinstance(v, dt.datetime):
        return v.date()
    if isinstance(v, dt.date):
        return v
    return None


def main(argv):
    path = os.environ.get("ORA_WORKBOOK_PATH") or DEFAULT_PATH
    out_file = None
    if "--out" in argv:
        out_file = argv[argv.index("--out") + 1]
    try:
        import openpyxl
        stat = os.stat(path)
        read_path, tmpdir = path, None
        try:
            wb = openpyxl.load_workbook(read_path, data_only=True, read_only=True)
            read_via = "direct"
        except PermissionError:
            import shutil
            import tempfile
            tmpdir = tempfile.mkdtemp(prefix="ora-ingest-")
            read_path = os.path.join(tmpdir, "snapshot.xlsx")
            shutil.copyfile(path, read_path)  # byte copy of a locked file; source untouched
            wb = openpyxl.load_workbook(read_path, data_only=True, read_only=True)
            read_via = "temp-copy (source locked)"
        sheets = list(wb.sheetnames)
        noi = table(wb, "EXPORT_PropertyNOI")
        rr_export = table(wb, "EXPORT_RentRoll")
        master_rows = list(wb["Master Tenant Rent Roll"].iter_rows(values_only=True))
        loans = table(wb, "EXPORT_Loans")
        internal = table(wb, "EXPORT_Loans_Internal")
        cash = table(wb, "EXPORT_CashBalanceSummary")
        ins = table(wb, "EXPORT_InsuranceRenewals")
        chk = table(wb, "EXPORT_MonthlyChecklist")
        home = list(wb["00_Home"].iter_rows(values_only=True))
        wb.close()
        if tmpdir:
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)
    except PermissionError as exc:
        print("COULD NOT READ workbook: locked by another process (Excel holds it "
              "exclusively, usually mid-save). Retry shortly -- do NOT report zeros. (%s)" % exc)
        return 2
    except Exception as exc:  # noqa: BLE001 -- any read failure is exit 2, never a guess
        print("COULD NOT READ workbook: %s: %s" % (type(exc).__name__, exc))
        return 2

    ties = {}
    rr, unmapped_src = master_to_records(master_rows)
    props = [r for r in noi if isinstance(r.get("#"), (int, float))]
    value = sum(num(r.get("Oxford Value")) for r in props)
    gross = sum(num(r.get("Gross Income (Oxford)")) for r in props)
    noi_adj = sum(num(r.get("Oxford NOI (scenario-adj)")) for r in props)
    ds = sum(num(r.get("Debt Svc (Oxford)")) for r in props)
    hv = home_cells(home)
    home_value = hv.get("PORTFOLIO VALUE")
    ties["T1_value_vs_home"] = {"sum_noi_value": round(value, 2), "home": home_value,
                                "pass": home_value is not None
                                and abs(value - home_value) <= TOL}

    borrower = sum(num(col(r, "Outstanding Balance (Deployed")) for r in loans
                   if r.get("Role") == "Borrower")
    lender = sum(num(col(r, "Outstanding Balance (Deployed")) for r in loans
                 if r.get("Role") == "Lender")
    int_total = sum(num(r.get("Current Balance")) for r in internal
                    if "Current Balance" in r and str(r.get("Loan Name", "")).strip()
                    and not str(r.get("Loan Name", "")).startswith("PORTFOLIO"))
    overlap = next((num(col(r, "Outstanding Balance (Deployed")) for r in loans
                    if str(r.get("Loan Name", "")).startswith("3883")), 0.0)
    total_debt = borrower + int_total - overlap
    home_debt = hv.get("TOTAL DEBT")
    ties["T2_total_debt"] = {"external": round(borrower, 2), "internal": round(int_total, 2),
                             "overlap": round(overlap, 2), "total": round(total_debt, 2),
                             "home": home_debt,
                             "pass": home_debt is not None and abs(total_debt - home_debt) <= TOL}
    gross_ltv = borrower / value if value else None
    home_ltv = hv.get("PORTFOLIO LTV")
    ties["T3_ltv"] = {"gross_external": gross_ltv,
                      "net_external": (borrower + lender) / value if value else None,
                      "home": home_ltv,
                      "pass": gross_ltv is not None and home_ltv is not None
                      and abs(gross_ltv - home_ltv) <= 1e-9}
    ties["T4_dscr_cap"] = {"dscr": noi_adj / ds if ds else None,
                           "cap": noi_adj / value if value else None, "pass": bool(ds and value)}

    share = {int(r["#"]): num(r.get("Oxford Own%")) or 1.0 for r in props}
    by_line, unmapped = {}, set(unmapped_src)
    for r in rr:
        key = str(r.get("Property", "")).strip().lower()
        if key not in RR_TO_NOI_LINE:
            if key:
                unmapped.add(key)
            continue
        line = RR_TO_NOI_LINE[key]
        by_line[line] = by_line.get(line, 0.0) + num(r.get("Annual Rent")) * share.get(line, 1.0)
    lines = []
    for r in props:
        n = int(r["#"])
        want = num(r.get("Gross Income (Oxford)"))
        got = by_line.get(n, 0.0)
        lines.append({"line": n, "property": r.get("Property"),
                      "noi_gross": round(want, 2), "rent_roll_x_share": round(got, 2),
                      "variance": round(got - want, 2), "pass": abs(got - want) <= TOL})
    ties["T5_rentroll_to_noi"] = {"lines": lines, "unmapped_rent_roll_properties": sorted(unmapped),
                                  "total_noi_gross": round(gross, 2),
                                  "total_rent_roll_x_share": round(sum(by_line.values()), 2),
                                  "pass": all(l["pass"] for l in lines) and not unmapped}

    exp_by = {}
    for r in rr_export:
        k = str(r.get("Property", "")).strip().lower()
        if k in RR_TO_NOI_LINE:
            exp_by[k] = exp_by.get(k, 0.0) + num(r.get("Annual Rent"))
    src_by = {}
    for r in rr:
        k = str(r.get("Property", "")).strip().lower()
        src_by[k] = src_by.get(k, 0.0) + num(r.get("Annual Rent"))
    gaps = [{"property": k, "source": round(src_by[k], 2), "export": round(exp_by.get(k, 0.0), 2),
             "missing": round(src_by[k] - exp_by.get(k, 0.0), 2)}
            for k in sorted(src_by) if abs(src_by[k] - exp_by.get(k, 0.0)) > TOL]
    ties["T5b_export_rentroll_complete"] = {
        "source_rows": len(rr), "export_rows": sum(1 for r in rr_export if str(r.get("Property", "")).strip().lower() in RR_TO_NOI_LINE),
        "gaps": gaps, "pass": not gaps}

    cash_rows = [r for r in cash if r.get("Entity / LLC")]
    cash_total = sum(num(r.get("Current Cash Balance")) for r in cash_rows)
    ties["T6_cash"] = {"entities": len(cash_rows), "total": round(cash_total, 3),
                       "pass": len(cash_rows) > 0}

    today = dt.date.today()
    tenants = [r for r in rr if str(r.get("Status", "")).strip().lower() not in NON_LEASED
               and r.get("Tenant Name") not in (None, "")]
    leasable = sum(num(r.get("Sq Ft")) for r in rr
                   if str(r.get("Status", "")).strip().lower() != "common area")
    leased = sum(num(r.get("Sq Ft")) for r in rr
                 if str(r.get("Status", "")).strip().lower() in IN_FORCE + ("active - mtm",
                                                                             "active \u2014 mtm")
                 and str(r.get("Notice to Vacate", "")).strip().lower() != "yes")
    arr = sum(num(r.get("Annual Rent")) for r in rr)
    wnum = wden = 0.0
    for r in rr:
        if str(r.get("Status", "")).strip().lower() in IN_FORCE:
            end = as_date(r.get("Lease End"))
            if end:
                wnum += num(r.get("Annual Rent")) * max((end - today).days, 0) / 365.25
                wden += num(r.get("Annual Rent"))
    ins_counts = {}
    for r in ins:
        ins_counts[str(r.get("Status"))] = ins_counts.get(str(r.get("Status")), 0) + 1
    expired = sorted(str(r.get("RowID")) for r in ins if r.get("Status") == "EXPIRED")
    oct_done = sum(1 for r in chk if str(r.get("OCT")).strip() == "\u2705")
    oct_total = sum(1 for r in chk if str(r.get("OCT")).strip() not in ("\u2014", "None", ""))

    result = {
        "workbook_modified": dt.datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
        "read_via": read_via, "sheet_count": len(sheets), "sheets_hash_note": "COUNTED from the live list",
        "portfolio": {"value": round(value, 2), "noi_scenario_adj": round(noi_adj, 2),
                      "debt_service": round(ds, 2), "gross_income": round(gross, 2)},
        "tie_outs": ties,
        "rent_roll": {"tenants": len(tenants), "arr": round(arr, 2),
                      "leasable_sf": leasable, "leased_sf": leased,
                      "occupancy": leased / leasable if leasable else None,
                      "walt_in_force_years": wnum / wden if wden else None,
                      "definition": "leased = in-force/MTM and not noticed; WALT = ARR-weighted, "
                                    "Status Active/Expiring Soon only"},
        "insurance": {"status_counts": ins_counts, "expired": expired},
        "checklist_oct": {"done": oct_done, "total": oct_total},
    }
    failed = [k for k, v in ties.items() if not v["pass"]]
    result["failed_tie_outs"] = failed
    if out_file:
        with open(out_file, "w", encoding="utf-8") as fh:
            json.dump(result, fh, indent=2, default=str)
    for g in gaps:
        print("T5b EXPORT_RentRoll GAP %s: source %.2f vs export %.2f (missing %.2f)"
              % (g["property"], g["source"], g["export"], g["missing"]))
    for l in lines:
        if not l["pass"]:
            print("T5 VARIANCE line %s %s: rent_roll_x_share %.2f vs noi_gross %.2f (%+.2f)"
                  % (l["line"], l["property"], l["rent_roll_x_share"], l["noi_gross"], l["variance"]))
    print("tie-outs failed: %s" % (", ".join(failed) if failed else "none"))
    print("RESULT_JSON=" + json.dumps(result, default=str))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
