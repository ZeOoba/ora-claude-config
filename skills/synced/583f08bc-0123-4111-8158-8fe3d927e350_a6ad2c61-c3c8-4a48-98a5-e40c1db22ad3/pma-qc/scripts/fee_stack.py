#!/usr/bin/env python3
"""
fee_stack.py — Oxford Realty Advisors property management fee stack model.

Quantifies total manager compensation across the four fee layers a typical
management agreement charges, and the overlap between them. The point is not the
headline management rate. It is that the same dollar can carry two or three fees
when the fee bases are undefined (PM-3, PM-12, PM-13).

Usage:
    python3 fee_stack.py --collections 480000 --mgmt-pct 4 --mgmt-floor 850 \\
        --lease-value 250000 --lease-pct 6 \\
        --capex 120000 --capex-pct 4 \\
        --insurance-billings 300000 --insurance-pct 10 \\
        [--properties 5] [--floor-per-property] [--hours 20 --hourly-rate 45] \\
        [--undefined-base] [--json]

--undefined-base models the exposure when "gross monies collected" is not
defined: insurance proceeds and capital contributions land in the operating
account and carry the management fee a second time. That is the KRG form's
posture and it is the single most expensive undefined term in it.

--floor-per-property applies the monthly minimum per property rather than per
agreement. On the KRG schedule ($850 x 5 properties) that distinction is worth
roughly $40,800 a year and the agreement does not resolve it.
"""

import argparse
import json


def model(a):
    rows = []

    # --- Layer 1: management fee on operating collections -------------------
    pct_fee = a.collections * a.mgmt_pct / 100.0
    months = 12
    floor_total = a.mgmt_floor * months * (a.properties if a.floor_per_property else 1)
    mgmt = max(pct_fee, floor_total)
    rows.append({
        "layer": "Management",
        "basis": f"{a.mgmt_pct:.2f}% of ${a.collections:,.0f} collections",
        "computed": pct_fee,
        "floor": floor_total,
        "fee": mgmt,
        "note": ("floor governs" if floor_total > pct_fee else "percentage governs"),
    })

    # --- Layer 2: leasing commission ---------------------------------------
    lease = a.lease_value * a.lease_pct / 100.0
    rows.append({
        "layer": "Leasing",
        "basis": f"{a.lease_pct:.2f}% of ${a.lease_value:,.0f} gross lease value",
        "computed": lease, "floor": 0.0, "fee": lease, "note": "",
    })

    # --- Layer 3: construction supervision ----------------------------------
    capex = a.capex * a.capex_pct / 100.0
    rows.append({
        "layer": "Construction supervision",
        "basis": f"{a.capex_pct:.2f}% of ${a.capex:,.0f} capital spend",
        "computed": capex, "floor": 0.0, "fee": capex, "note": "",
    })

    # --- Layer 4: casualty ---------------------------------------------------
    cas = a.insurance_billings * a.insurance_pct / 100.0
    rows.append({
        "layer": "Casualty",
        "basis": f"{a.insurance_pct:.2f}% of ${a.insurance_billings:,.0f} insurer billings",
        "computed": cas, "floor": 0.0, "fee": cas, "note": "",
    })

    # --- Layer 5: hourly -----------------------------------------------------
    hourly = a.hours * a.hourly_rate
    if hourly:
        rows.append({
            "layer": "Hourly",
            "basis": f"{a.hours:g} hrs @ ${a.hourly_rate:,.0f}",
            "computed": hourly, "floor": 0.0, "fee": hourly, "note": "",
        })

    stacked = []
    # Overlap A: undefined management-fee base pulls insurance proceeds in.
    if a.undefined_base and a.insurance_billings:
        dup = a.insurance_billings * a.mgmt_pct / 100.0
        stacked.append({
            "overlap": "Insurance proceeds inside 'gross monies collected'",
            "amount": dup,
            "why": ("Casualty proceeds deposited to the operating account are "
                    "collected monies under an undefined base, so the "
                    "management fee applies on top of the casualty fee."),
        })
    # Overlap B: same physical work carrying both supervision and casualty fees.
    if a.capex and a.insurance_billings:
        dup = min(a.capex, a.insurance_billings) * a.capex_pct / 100.0
        stacked.append({
            "overlap": "Casualty restoration also billed as a capital project",
            "amount": dup,
            "why": ("Restoration work charged the construction supervision fee "
                    "and the casualty fee for the same scope. PM-13 credits one "
                    "against the other."),
        })

    base_total = sum(r["fee"] for r in rows)
    stack_total = sum(s["amount"] for s in stacked)
    total = base_total + stack_total
    eff = (total / a.collections * 100.0) if a.collections else 0.0
    eff_base = (base_total / a.collections * 100.0) if a.collections else 0.0

    return {"rows": rows, "overlaps": stacked, "base_total": base_total,
            "overlap_total": stack_total, "total": total,
            "effective_pct_of_collections": eff,
            "effective_pct_excluding_overlap": eff_base,
            "floor_sensitivity": a.mgmt_floor * 12 * (a.properties - 1)}


def main():
    p = argparse.ArgumentParser(description="ORA management fee stack model")
    p.add_argument("--collections", type=float, required=True,
                   help="annual gross monies collected")
    p.add_argument("--mgmt-pct", type=float, default=4.0)
    p.add_argument("--mgmt-floor", type=float, default=0.0,
                   help="monthly minimum management fee")
    p.add_argument("--properties", type=int, default=1)
    p.add_argument("--floor-per-property", action="store_true",
                   help="apply the monthly minimum per property, not per agreement")
    p.add_argument("--lease-value", type=float, default=0.0)
    p.add_argument("--lease-pct", type=float, default=6.0)
    p.add_argument("--capex", type=float, default=0.0)
    p.add_argument("--capex-pct", type=float, default=4.0)
    p.add_argument("--insurance-billings", type=float, default=0.0)
    p.add_argument("--insurance-pct", type=float, default=10.0)
    p.add_argument("--hours", type=float, default=0.0)
    p.add_argument("--hourly-rate", type=float, default=45.0)
    p.add_argument("--undefined-base", action="store_true",
                   help="model the management fee reaching non-revenue receipts")
    p.add_argument("--json", action="store_true")
    a = p.parse_args()

    r = model(a)
    if a.json:
        print(json.dumps(r, indent=2))
        return

    w = 78
    print("=" * w)
    print("MANAGEMENT FEE STACK")
    print("=" * w)
    print(f"{'Layer':<28}{'Basis':<34}{'Fee':>14}")
    print("-" * w)
    for x in r["rows"]:
        note = f"  [{x['note']}]" if x["note"] else ""
        print(f"{x['layer']:<28}{x['basis']:<34}{x['fee']:>14,.0f}")
        if note:
            print(" " * 28 + note.strip())
    print("-" * w)
    print(f"{'Contracted fees':<62}{r['base_total']:>14,.0f}")

    if r["overlaps"]:
        print()
        print("STACKING EXPOSURE (the same dollar carrying two fees)")
        print("-" * w)
        for s in r["overlaps"]:
            print(f"{s['overlap']:<62}{s['amount']:>14,.0f}")
            for line in _wrap(s["why"], w - 4):
                print("    " + line)
        print("-" * w)
        print(f"{'Overlap subtotal':<62}{r['overlap_total']:>14,.0f}")

    print("=" * w)
    print(f"{'TOTAL MANAGER COMPENSATION':<62}{r['total']:>14,.0f}")
    print(f"{'Effective rate on collections':<62}"
          f"{r['effective_pct_of_collections']:>13.2f}%")
    print(f"{'  excluding stacking exposure':<62}"
          f"{r['effective_pct_excluding_overlap']:>13.2f}%")
    if r["floor_sensitivity"]:
        print()
        print(f"Monthly-minimum sensitivity: per-property vs per-agreement "
              f"differs by ${r['floor_sensitivity']:,.0f}/yr.")
        print("Resolve from the billing history - the agreement does not say.")
    print("=" * w)


def _wrap(t, n):
    out, cur = [], ""
    for word in t.split():
        if len(cur) + len(word) + 1 > n:
            out.append(cur)
            cur = word
        else:
            cur = (cur + " " + word).strip()
    if cur:
        out.append(cur)
    return out


if __name__ == "__main__":
    main()
