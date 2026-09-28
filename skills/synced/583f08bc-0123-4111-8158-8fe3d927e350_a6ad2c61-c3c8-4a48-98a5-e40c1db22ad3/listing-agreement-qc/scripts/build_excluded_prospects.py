#!/usr/bin/env python3
"""
build_excluded_prospects.py — ORA Excluded Prospects exhibit builder (SP-2).

Turns a tenant list pulled from the Notion Tenant Database into the exhibit that
attaches to a broker listing agreement, in ORA Style Guide v1.0 trade dress.

Input JSON: a list of objects, each with any of
    name        (required)  legal entity or trade name as it should appear
    entity      (optional)  registered legal entity name if different
    suite       (optional)  suite / unit
    sf          (optional)  square feet
    status      (optional)  Lease Status from Notion
    expires     (optional)  ISO lease expiration
    source      (optional)  "Subject property" / "Adjacent - 2018 Zettler Rd" / free text
    basis       (optional)  why excluded; defaults by source

Usage:
    python3 build_excluded_prospects.py \
        --property "2000-2002 Zettler Rd, Columbus, OH 43232" \
        --parcel "010-015487-00" \
        --owner "FAIRGROUND VILLAGE CENTER LLC" \
        --broker "Cushman & Wakefield U.S., Inc." \
        --tenants tenants.json \
        --free-days 90 \
        --out "Exhibit A - Excluded Prospects.docx"

Notion source (filter out rows whose Tenant Name starts with the archived marker):
    SELECT "Tenant Name","Tenant Legal Entity Name","Suite / Unit","SF",
           "Lease Status","date:Lease Expiration:start"
    FROM "collection://b12f4cfd-a995-4755-8341-6435ae8173b4"
    WHERE "Property Address" LIKE '%<street>%'
"""

import argparse
import json
import sys

try:
    from docx import Document
    from docx.shared import Pt, Inches, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
except ImportError:                                               # pragma: no cover
    print("python-docx required:  pip install python-docx --break-system-packages",
          file=sys.stderr)
    raise

NAVY = RGBColor(0x1B, 0x2A, 0x4A)
GOLD = RGBColor(0xC9, 0xA9, 0x6E)
GREY = RGBColor(0x6B, 0x6B, 0x6B)
SERIF, SANS = "EB Garamond", "DM Sans"

DEFAULT_BASIS = {
    "subject": "Occupant of the Property. Introduced to the Property by Owner.",
    "adjacent": "Tenant of an Owner-affiliated property. Relationship predates the Term.",
    "affiliate": "Affiliate of Owner or entity under common control.",
    "engaged": "Counterparty engaged by Owner prior to the Commencement Date.",
}


def _shade(cell, hexfill):
    el = OxmlElement("w:shd")
    el.set(qn("w:val"), "clear")
    el.set(qn("w:color"), "auto")
    el.set(qn("w:fill"), hexfill)
    cell._tc.get_or_add_tcPr().append(el)


def _fixed_layout(table, widths):
    """python-docx honours cell widths only with a fixed layout + a real grid."""
    tblPr = table._tbl.tblPr
    layout = OxmlElement("w:tblLayout")
    layout.set(qn("w:type"), "fixed")
    tblPr.append(layout)
    w = OxmlElement("w:tblW")
    w.set(qn("w:w"), str(int(sum(x.inches for x in widths) * 1440)))
    w.set(qn("w:type"), "dxa")
    tblPr.append(w)
    for i, col in enumerate(table.columns):
        col.width = widths[i]
        for cell in col.cells:
            cell.width = widths[i]


def _run(p, text, font=SERIF, size=10, bold=False, color=None, italic=False):
    r = p.add_run(text)
    r.font.name = font
    r.font.size = Pt(size)
    r.bold = bold
    r.italic = italic
    if color is not None:
        r.font.color.rgb = color
    return r


def build(args, tenants):
    doc = Document()
    for s in doc.sections:
        s.top_margin = s.bottom_margin = Inches(0.9)
        s.left_margin = s.right_margin = Inches(1.0)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _run(p, "EXHIBIT A", SANS, 9, True, GOLD)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _run(p, "EXCLUDED PROSPECTS", SERIF, 18, False, NAVY)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _run(p, args.property, SANS, 9.5, False, GREY)
    if args.parcel:
        _run(p, f"   ·   Parcel {args.parcel}", SANS, 9.5, False, GREY)

    doc.add_paragraph()

    lead = (
        f"This Exhibit A is attached to and forms part of the Listing Agreement between "
        f"{args.owner} (“Owner”) and {args.broker} (“Broker”) covering the "
        f"Property described above.\n\n"
        f"Notwithstanding anything in the Listing Agreement or the Schedule of Commissions "
        f"to the contrary, no commission or other compensation shall be payable to Broker "
        f"in connection with any sale, exchange, conveyance, or other transfer of all or any "
        f"part of the Property to, or to any affiliate or principal of, any party listed "
        f"below (each an “Excluded Prospect”) where the binding agreement to transfer "
        f"is entered into within {args.free_days} days after the Commencement Date. "
        f"Thereafter, a commission shall be payable at the rate set forth in the Schedule of "
        f"Commissions only if Broker has provided substantive services to that Excluded "
        f"Prospect with respect to the Property and has documented those services to Owner "
        f"in writing prior to the binding agreement."
    )
    for para in lead.split("\n\n"):
        q = doc.add_paragraph()
        q.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        q.paragraph_format.space_after = Pt(8)
        _run(q, para, SERIF, 10)

    doc.add_paragraph()

    cols = ["#", "Excluded Prospect", "Suite / SF", "Basis for exclusion"]
    widths = [Inches(0.32), Inches(1.95), Inches(1.35), Inches(2.88)]
    t = doc.add_table(rows=1, cols=len(cols))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    _fixed_layout(t, widths)
    for i, c in enumerate(cols):
        cell = t.rows[0].cells[i]
        cell.width = widths[i]
        cell.text = ""
        _run(cell.paragraphs[0], c, SANS, 8.5, True, RGBColor(0xFF, 0xFF, 0xFF))
        _shade(cell, "1B2A4A")

    for n, x in enumerate(tenants, 1):
        row = t.add_row()
        cant = OxmlElement("w:cantSplit")          # keep a prospect on one page
        row._tr.get_or_add_trPr().append(cant)
        src = (x.get("source") or "").lower()
        key = ("subject" if "subject" in src else
               "adjacent" if "adjacent" in src else
               "affiliate" if "affiliat" in src else
               "engaged" if "engag" in src else "subject")
        basis = x.get("basis") or DEFAULT_BASIS[key]
        if x.get("status"):
            basis += f"  Lease status: {x['status']}"
            if x.get("expires"):
                basis += f" (exp. {x['expires']})"
            basis += "."

        name = x["name"]
        if x.get("entity") and x["entity"] != x["name"]:
            name += f"\n{x['entity']}"

        sf = ""
        if x.get("suite"):
            sf = str(x["suite"])
        if x.get("sf"):
            sf += ("\n" if sf else "") + f"{int(x['sf']):,} SF"

        for i, val in enumerate([str(n), name, sf, basis]):
            cell = row.cells[i]
            cell.width = widths[i]
            cell.text = ""
            cell.paragraphs[0].paragraph_format.space_after = Pt(1)
            lines = val.split("\n")
            _run(cell.paragraphs[0], lines[0], SERIF, 9, bold=(i == 1))
            for extra in lines[1:]:
                pp = cell.add_paragraph()
                _run(pp, extra, SANS, 8, False, GREY)
            if n % 2 == 0:
                _shade(cell, "F5F3EF")

    doc.add_paragraph()
    note = doc.add_paragraph()
    note.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    _run(note,
         "Owner may supplement this Exhibit A upon written notice to Broker to add any "
         "party with whom Owner was in contact regarding the Property prior to the "
         "Commencement Date. This Exhibit does not limit Section 5 of the Listing "
         "Agreement with respect to any prospect not listed here.",
         SERIF, 9, italic=True, color=GREY)

    doc.add_paragraph()
    sig = doc.add_table(rows=4, cols=2)
    sig.autofit = False
    _fixed_layout(sig, [Inches(3.25), Inches(3.25)])
    labels = [("OWNER", "BROKER"),
              (f"{args.owner}", f"{args.broker}"),
              ("By: ______________________________", "By: ______________________________"),
              ("Date: ____________________________", "Date: ____________________________")]
    for r, (a, b) in enumerate(labels):
        for c, val in enumerate([a, b]):
            cell = sig.rows[r].cells[c]
            cell.width = Inches(3.25)
            cell.text = ""
            _run(cell.paragraphs[0], val, SANS if r == 0 else SERIF,
                 8.5 if r == 0 else 9.5, bold=(r <= 1),
                 color=GOLD if r == 0 else None)

    doc.save(args.out)
    return args.out


def main():
    ap = argparse.ArgumentParser(description="Build the ORA Excluded Prospects exhibit")
    ap.add_argument("--property", required=True)
    ap.add_argument("--parcel", default="")
    ap.add_argument("--owner", required=True)
    ap.add_argument("--broker", required=True)
    ap.add_argument("--tenants", required=True, help="JSON file, list of prospect objects")
    ap.add_argument("--free-days", type=int, default=90)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    tenants = json.load(open(a.tenants, encoding="utf8"))
    tenants = [x for x in tenants if not str(x.get("name", "")).lstrip().startswith("⛔")]
    if not tenants:
        print("ERROR: no live prospects after filtering archived rows", file=sys.stderr)
        sys.exit(2)
    out = build(a, tenants)
    print(f"wrote {out} with {len(tenants)} excluded prospects")


if __name__ == "__main__":
    main()
