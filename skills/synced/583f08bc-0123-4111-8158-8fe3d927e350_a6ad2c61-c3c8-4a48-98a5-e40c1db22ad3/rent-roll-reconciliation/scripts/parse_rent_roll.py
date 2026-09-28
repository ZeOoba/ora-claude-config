"""
Parse a rent-roll .xlsx export into a normalized JSON list of tenant records.

Usage:
    python parse_rent_roll.py <path-to-rent-roll.xlsx> <output.json> [--sheet Sheet1] [--header-row 5]

Adjust HEADER_ROW / column order below to match the actual export --
rent rolls from different PM platforms (Yardi, AppFolio, Rent Manager)
vary in header row position and column order. Inspect the first ~10
rows of the sheet before assuming this template fits.

Expected column order (adjust as needed):
Property, Tenant/Contact Name, Unit, Company, Sq Ft, Monthly Rent,
Rent / SF, Lease Start, Lease End, Escalation Date, Escalation %,
Status, Vacant, Annual Rent
"""
import sys
import json
import argparse
import openpyxl


def parse(path, sheet_name=None, header_row=5):
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb[sheet_name] if sheet_name else wb.active

    rows = []
    for r in range(header_row + 1, ws.max_row + 1):
        vals = [ws.cell(row=r, column=c).value for c in range(1, 16)]
        if all(v is None for v in vals):
            continue
        rows.append(vals)

    records = []
    for v in rows:
        # Adjust unpacking to match the real column order for this export.
        _, prop, contact, unit, company, sf, rent, rentpsf, lstart, lend, esc_date, esc_pct, status, vacant, annual = v

        # Skip obvious non-tenant rows (totals, blank separators).
        if prop and str(prop).strip().upper() in ("PORTFOLIO TOTALS", "TOTALS", "TOTAL"):
            continue

        records.append({
            "property": prop,
            "unit": unit,
            "contact": contact,
            "company": company,
            "sf": sf,
            "monthly_rent": rent,
            "rent_psf": rentpsf,
            "lease_start": str(lstart)[:10] if lstart else None,
            "lease_end": str(lend)[:10] if lend else None,
            "escalation_date": str(esc_date)[:10] if esc_date else None,
            "escalation_pct": esc_pct,
            "status": status,
            "vacant": vacant,
            "annual_rent": annual,
        })
    return records


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("input_xlsx")
    ap.add_argument("output_json")
    ap.add_argument("--sheet", default=None)
    ap.add_argument("--header-row", type=int, default=5)
    args = ap.parse_args()

    records = parse(args.input_xlsx, args.sheet, args.header_row)
    with open(args.output_json, "w") as f:
        json.dump(records, f, indent=1)

    print(f"Parsed {len(records)} records -> {args.output_json}")
