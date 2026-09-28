#!/usr/bin/env python3
"""
build_addendum_docx.py -- builds an ORA lease addendum DOCX from a config dict.

Two uses:
  1. Base starting template (every field a [TOKEN] placeholder), written to
     templates/Lease_Addendum_TEMPLATE.docx:
       python build_addendum_docx.py --template <output.docx>
  2. A populated draft from a JSON config file:
       python build_addendum_docx.py --config <config.json> <output.docx>

Mechanics encoded here (see SKILL.md "DOCX build mechanics"):
  - Times New Roman 12pt BODY. The letterhead block (firm name, landlord entity,
    title, property address) uses the ORA Institutional Style Guide (EB Garamond /
    DM Sans, Navy #1B2A4A) -- sourced from the DelVal Equipment Corp. addendum
    (29000 Information Lane, 2026-08), the one file in the corpus that carries a
    branded letterhead. Gabriel's instruction (2026-08-14): 95% of real addenda
    match the terser Hogan/Hoodz-of-Delmarva pattern for CONTENT (one-line
    recital, table-per-clause, plain-text signature-page marker) -- that stays
    the default. Only the letterhead typography and DelVal's margins carry over;
    the fuller lettered-Recitals/numbered-Amendments narrative structure and
    DelVal's un-tabled clause layout do NOT -- those were explicitly scoped out.
  - 0.75"/0.75" top/bottom, 1.0"/1.0" left/right margins (DelVal's), including
    the Exhibit section (its own WD_SECTION.NEW_PAGE, still 1.0" all sides per
    the existing Exhibit convention).
  - Hanging-indent labeled paragraphs: bold label + tab, 1.5" hanging indent.
  - w:cantSplit on every table row, w:keepNext on every row but the last (and on
    the paragraph before the table) -- table integrity, never a manual page break.
  - A REAL page break (WD_BREAK.PAGE) before the signature page, preceded by a
    centered italic "[SIGNATURE PAGE TO FOLLOW]" marker -- not the plain-text-only
    convention every real ORA addendum in the corpus currently uses (confirmed via
    lastRenderedPageBreak-only, no w:br, across all five reviewed files).
  - docProps Title set explicitly to the ordinal every build -- the fix for the
    cloned-template metadata-drift defect found in 9050 Red Branch Rd (see
    event_log.md, 2026-08-14).
"""

import copy
import json
import sys

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

ORA_NAVY = RGBColor(0x1B, 0x2A, 0x4A)


def T(val, token):
    """Return val if given, else the bracketed token placeholder."""
    return val if val not in (None, "") else f"[{token}]"


def set_margins(section, inches=1.0, top=None, bottom=None, left=None, right=None):
    section.top_margin = Inches(top if top is not None else inches)
    section.bottom_margin = Inches(bottom if bottom is not None else inches)
    section.left_margin = Inches(left if left is not None else inches)
    section.right_margin = Inches(right if right is not None else inches)


def set_default_font(doc, name="Times New Roman", size=12):
    style = doc.styles["Normal"]
    style.font.name = name
    style.font.size = Pt(size)
    rpr = style.element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = rpr.makeelement(qn("w:rFonts"), {})
        rpr.append(rfonts)
    rfonts.set(qn("w:eastAsia"), name)


def _styled_run(paragraph, text, font="EB Garamond", size=11, bold=False, italic=False, color=None):
    r = paragraph.add_run(text)
    r.font.name = font
    r.font.size = Pt(size)
    r.bold = bold
    r.italic = italic
    if color is not None:
        r.font.color.rgb = color
    return r


def add_letterhead(doc, cfg):
    """Centered letterhead block -- typography sourced verbatim from the DelVal
    Equipment Corp. addendum (29000 Information Lane, 2026-08), the one file in
    the corpus that carries one. Firm name / title in DM Sans bold Navy; landlord
    entity / property address in EB Garamond italic. Scope is letterhead + margins
    only (Gabriel, 2026-08-14) -- this does not change the body font below it."""
    ordinal_upper = T(cfg.get("ordinal"), "ORDINAL").upper()

    p1 = doc.add_paragraph()
    p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p1.paragraph_format.space_after = Pt(3)
    _styled_run(p1, "OXFORD REALTY ADVISORS", font="DM Sans", size=15, bold=True, color=ORA_NAVY)

    p2 = doc.add_paragraph()
    p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p2.paragraph_format.space_after = Pt(15)
    _styled_run(p2, T(cfg.get("landlord_entity"), "LANDLORD ENTITY"), font="EB Garamond", size=11, italic=True, color=ORA_NAVY)

    p3 = doc.add_paragraph()
    p3.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p3.paragraph_format.space_after = Pt(14)
    _styled_run(p3, f"{ordinal_upper} ADDENDUM TO LEASE", font="DM Sans", size=14, bold=True, color=ORA_NAVY)

    p4 = doc.add_paragraph()
    p4.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p4.paragraph_format.space_after = Pt(14)
    _styled_run(p4, T(cfg.get("premises_address"), "PREMISES ADDRESS, CITY, STATE ZIP"), font="EB Garamond", size=11, italic=True)


def set_row_cantsplit(row):
    trPr = row._tr.get_or_add_trPr()
    cant_split = trPr.makeelement(qn("w:cantSplit"), {})
    trPr.append(cant_split)


def set_para_keepnext(paragraph):
    pPr = paragraph._p.get_or_add_pPr()
    keep_next = pPr.makeelement(qn("w:keepNext"), {})
    pPr.append(keep_next)


def apply_table_integrity(table, keep_next_last_row=False):
    """w:cantSplit on every row; w:keepNext on every row's paragraphs but the
    last row (unless keep_next_last_row), and on the paragraph preceding the
    table -- binds the whole table together across a page boundary."""
    for i, row in enumerate(table.rows):
        set_row_cantsplit(row)
        if i < len(table.rows) - 1 or keep_next_last_row:
            for cell in row.cells:
                for p in cell.paragraphs:
                    set_para_keepnext(p)


def add_hanging_paragraph(doc, label, body, hanging_inches=1.5):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Inches(hanging_inches)
    p.paragraph_format.first_line_indent = Inches(-hanging_inches)
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(6)
    r = p.add_run(f"{label}:")
    r.bold = True
    p.add_run("\t" + body)
    return p


def add_signature_page_marker_and_break(doc):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.left_indent = Inches(1.5)
    p.paragraph_format.first_line_indent = Inches(0)
    r = p.add_run("[SIGNATURE PAGE TO FOLLOW]")
    r.italic = True
    br_p = doc.add_paragraph()
    br_run = br_p.add_run()
    br_run.add_break(WD_BREAK.PAGE)


def add_signature_block(doc, role_label, entity_line, signer_lines, seal=False):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(12)
    r = p.add_run(role_label + ":")
    r.bold = True
    if entity_line:
        doc.add_paragraph(entity_line)
    doc.add_paragraph()
    by = doc.add_paragraph()
    by.add_run("By:\t_________________________________" + (" (Seal)" if seal else ""))
    for line in signer_lines:
        doc.add_paragraph(line)


def add_notice_table(doc, blocks):
    """blocks: list of (heading, [address lines]). keepNext binds each heading
    to its address lines so a heading cannot orphan across a page break."""
    heading_p = doc.add_paragraph()
    r = heading_p.add_run("Notices:")
    r.bold = True
    heading_p.add_run(
        "\tAll notices, demands and other communications under the Lease shall be "
        "given in the manner required by the Lease, addressed as follows (or to "
        "such other address as a party designates by notice given in accordance "
        "with the Lease):"
    )
    heading_p.paragraph_format.left_indent = Inches(1.5)
    heading_p.paragraph_format.first_line_indent = Inches(-1.5)
    set_para_keepnext(heading_p)
    for heading, lines in blocks:
        hp = doc.add_paragraph()
        hp.add_run(f"To {heading}:").bold = True
        set_para_keepnext(hp)
        for i, line in enumerate(lines):
            lp = doc.add_paragraph(line)
            if i < len(lines) - 1:
                set_para_keepnext(lp)


def add_rent_schedule_table(doc, caption, rows):
    """rows: list of (period, annual, monthly). Table integrity applied after
    build. Caption states who owes rent in each period when a party change
    straddles it (QC check 2's binding requirement lives in the paragraph
    text that references this table, not in the table itself)."""
    cap = doc.add_paragraph()
    cap.paragraph_format.space_before = Pt(6)
    cr = cap.add_run(caption)
    cr.bold = True
    cr.italic = True
    set_para_keepnext(cap)

    table = doc.add_table(rows=1, cols=3)
    table.style = "Table Grid"
    hdr = table.rows[0].cells
    hdr[0].text, hdr[1].text, hdr[2].text = "Lease Period", "Base Annual Rent", "Base Monthly Rent"
    for h in hdr:
        for p in h.paragraphs:
            for r in p.runs:
                r.bold = True
    for period, annual, monthly in rows:
        row = table.add_row().cells
        row[0].text, row[1].text, row[2].text = period, annual, monthly
    apply_table_integrity(table)
    return table


def add_exhibit_a_guaranty(doc, cfg):
    section = doc.add_section(WD_SECTION.NEW_PAGE)
    set_margins(section, 1.0)

    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    tr = title.add_run('EXHIBIT "A"')
    tr.bold = True
    subtitle = doc.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sr = subtitle.add_run("UNCONDITIONAL AND CONTINUING GUARANTY OF LEASE")
    sr.bold = True

    g = cfg.get("guaranty", {})
    t_incoming = cfg.get("tenant_change", {}).get("incoming_entity_full") or cfg.get("tenant_entity")
    add_hanging_paragraph(doc, "1.  LANDLORD", T(cfg.get("landlord_entity"), "LANDLORD ENTITY"), 1.0)
    add_hanging_paragraph(doc, "2.  GUARANTOR", T(g.get("name"), "GUARANTOR NAME"), 1.0)
    add_hanging_paragraph(doc, "3.  TENANT", T(t_incoming, "TENANT ENTITY (POST-SUBSTITUTION)"), 1.0)
    add_hanging_paragraph(
        doc, "4.  LEASE",
        f"Lease dated {T(cfg.get('prime_lease_date'), 'PRIME LEASE DATE')}, as amended, "
        f"including the {T(cfg.get('ordinal'), 'ORDINAL')} Addendum to which this Guaranty is "
        f"attached, for the premises at {T(cfg.get('premises_address'), 'PREMISES ADDRESS')}",
        1.0,
    )

    paras = [
        ("A.  Consideration and Reliance.",
         "Guarantor holds a direct or indirect ownership interest in Tenant, will derive "
         "substantial economic benefit from the Lease, has received a copy of the Lease, and "
         "acknowledges the sufficiency of that consideration. Landlord has agreed to enter into "
         "the Addendum in reliance on this Guaranty as a material inducement, and would not have "
         "done so without it."),
        ("B.  Guaranty.",
         "Guarantor unconditionally guarantees to Landlord the full and prompt payment of all "
         "rent and other sums payable by Tenant, and the full and faithful performance of all of "
         "Tenant's obligations, under the Lease for the entire term and any extension, renewal, "
         "or holdover, together with all damages, costs, and reasonable attorneys' fees arising "
         "from Tenant's failure to pay or perform. THIS IS A GUARANTY OF PAYMENT AND PERFORMANCE "
         "AND NOT OF COLLECTION."),
        ("C.  Direct, Primary and Continuing.",
         "Guarantor's liability is primary, direct, and independent of Tenant's, and continues "
         "until all obligations under the Lease are fully paid and performed. It is not "
         "conditioned upon any notice or demand, upon Landlord first proceeding against Tenant "
         "or any other guarantor, or upon Landlord pursuing or exhausting any security deposit "
         "or other collateral, each of which Guarantor waives. Landlord may enforce this "
         "Guaranty against Guarantor alone."),
        ("D.  Amendments; Waiver of Defenses.",
         "Landlord may, without notice to or the consent of Guarantor and without releasing, "
         "reducing, or otherwise affecting Guarantor's liability, amend, modify, extend, renew, "
         "or replace the Lease, consent to any assignment, subletting, or further substitution "
         "of Tenant, grant any indulgence or forbearance, waive any default, and release, "
         "impair, or apply any security deposit or any other guarantor; this Guaranty applies to "
         "the Lease as so amended. Guarantor waives presentment, demand, protest, notice of "
         "default or nonpayment, and every defense available to a surety or guarantor, including "
         "any defense based on the amendment of the Lease, the impairment of collateral or of "
         "subrogation rights, the release of any other obligor, or the unenforceability of the "
         "Lease against Tenant for any reason. Guarantor subordinates every claim against Tenant "
         "to prior payment in full of the guaranteed obligations."),
        ("E.  Bankruptcy; Reinstatement.",
         "Guarantor's liability is unaffected by any bankruptcy, insolvency, or similar "
         "proceeding affecting Tenant, or by any rejection, disaffirmance, termination, or "
         "modification of the Lease in such a proceeding, including any limitation on Landlord's "
         "damages under 11 U.S.C. § 502(b)(6); Guarantor remains liable for the full amount "
         "that would have been payable had no such proceeding occurred. If Landlord must return "
         "any payment as a preference or otherwise, this Guaranty is automatically reinstated."),
        ("F.  General.",
         f"This Guaranty is governed by the laws of the State of "
         f"{T(cfg.get('property_state'), 'PROPERTY STATE')}; venue for any action to enforce or "
         f"interpret it lies exclusively in the courts in and for "
         f"{T(cfg.get('county'), 'COUNTY')}, {T(cfg.get('property_state'), 'PROPERTY STATE')}, "
         "and Guarantor consents to personal jurisdiction there. LANDLORD AND GUARANTOR EACH "
         "WAIVE TRIAL BY JURY. The prevailing party is entitled to its court costs and "
         "reasonable attorneys' fees, including on appeal. This Guaranty binds Guarantor's "
         "heirs, personal representatives, successors, and assigns and inures to Landlord's "
         "successors and assigns, including any purchaser or mortgagee; Guarantor may not "
         "assign its obligations. If executed by more than one person, liability is joint and "
         "several."),
    ]
    for label, body in paras:
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(6)
        p.paragraph_format.space_after = Pt(6)
        r = p.add_run(label)
        r.bold = True
        p.add_run(" " + body)

    exec_p = doc.add_paragraph(
        f"Executed and delivered under seal on this ____ day of ______________, "
        f"{T(cfg.get('year'), 'YEAR')}."
    )
    exec_p.paragraph_format.space_before = Pt(18)
    doc.add_paragraph()
    label = doc.add_paragraph()
    label.add_run("GUARANTOR:").bold = True
    doc.add_paragraph("____________________________________________(SEAL)")
    doc.add_paragraph(T(g.get("name"), "GUARANTOR NAME"))
    doc.add_paragraph(f"Address: {T(g.get('address'), 'GUARANTOR ADDRESS')}")


def build_addendum(cfg, output_path):
    doc = Document()
    set_default_font(doc)
    set_margins(doc.sections[0], top=0.75, bottom=0.75, left=1.0, right=1.0)

    ordinal_upper = T(cfg.get("ordinal"), "ORDINAL").upper()
    doc.core_properties.title = f"{ordinal_upper} ADDENDUM TO LEASE"
    doc.core_properties.author = ""

    if cfg.get("sample_banner"):
        banner = doc.add_paragraph()
        banner.alignment = WD_ALIGN_PARAGRAPH.CENTER
        br = banner.add_run(cfg["sample_banner"])
        br.bold = True
        banner.paragraph_format.space_after = Pt(12)

    add_letterhead(doc, cfg)

    # Recital -- enumerated prior addenda, not a blanket catch-all (Doctrine rule 1)
    prior = cfg.get("prior_addenda", [])
    if prior:
        prior_txt = "; ".join(f"{p['ordinal']} Addendum dated {p['date']}" for p in prior)
        prior_clause = f", as amended by the {prior_txt},"
    else:
        prior_clause = f" [and by each prior amendment, enumerated by ordinal and date: {T(None, 'ENUMERATE PRIOR ADDENDA -- NO BLANKET CATCH-ALL')}]"
    recital = doc.add_paragraph(
        f"This is an addendum to a lease dated {T(cfg.get('prime_lease_date'), 'PRIME LEASE DATE')}"
        f"{prior_clause} (collectively the “Lease”) by and between "
        f"{T(cfg.get('tenant_party_recital'), 'TENANT PARTIES')}, as “Tenant”, and "
        f"{T(cfg.get('landlord_entity'), 'LANDLORD ENTITY')} as “Landlord” (the “Prime "
        f"Lease”), covering the premises known as "
        f"{T(cfg.get('premises_address'), 'PREMISES ADDRESS, CITY, STATE ZIP')} (the "
        f"“Premises”)."
    )
    recital.paragraph_format.space_after = Pt(12)

    doc.add_paragraph(
        "The following terms will replace or supplement terms contained in the Lease to which "
        "this document is made a part thereof and attached thereto:"
    )

    m3b = cfg.get("m3b", False)
    m4 = cfg.get("m4", False)

    if m3b:
        t = cfg.get("tenant_change", {})
        add_hanging_paragraph(
            doc, "Tenant",
            f"Effective as of the Substitution Date (defined below), "
            f"{T(t.get('incoming_entity'), 'INCOMING TENANT ENTITY')} is substituted as the sole "
            f"“Tenant” under the Lease, and from and after the Substitution Date each "
            f"reference in the Lease to “Tenant” shall mean "
            f"{T(t.get('incoming_entity'), 'INCOMING TENANT ENTITY')} alone. "
            f"{T(t.get('incoming_entity'), 'INCOMING TENANT ENTITY')} hereby assumes and agrees to "
            f"be bound by, pay and perform all obligations of Tenant under the Lease, whether "
            f"arising before, on or after the Substitution Date. "
            f"{T(t.get('outgoing_entities'), 'OUTGOING PARTIES')} (collectively, “Prior "
            f"Tenant”) are released from the obligations of Tenant first accruing on and "
            f"after the Substitution Date; Prior Tenant shall remain jointly and severally liable "
            f"for all obligations of Tenant accruing under the Lease prior to the Substitution "
            f"Date, including any obligation not then ascertained and any operating-cost, tax or "
            f"other reconciliation attributable to a period prior to the Substitution Date."
        )
        add_hanging_paragraph(
            doc, "Substitution Date",
            f"“Substitution Date” means the later of (a) the date on which this "
            f"Addendum has been fully executed and delivered by Landlord, "
            f"{T(t.get('incoming_entity'), 'INCOMING TENANT ENTITY')} and Prior Tenant, and (b) "
            f"the date on which Landlord has received each of the items listed under "
            f"“Conditions” below. If the Substitution Date has not occurred on or before "
            f"{T(t.get('outside_date'), 'OUTSIDE DATE')}, Landlord may terminate this Addendum by "
            f"written notice, in which event the Lease shall continue unmodified."
        )
        add_hanging_paragraph(
            doc, "Conditions",
            "The following are conditions precedent to the occurrence of the Substitution Date: "
            "(a) the Guaranty of Lease attached as Exhibit A, executed by "
            f"{T(t.get('guarantor_name'), 'GUARANTOR NAME')} and delivered to Landlord; (b) a "
            f"certificate of insurance evidencing all coverages required under the Lease, issued "
            f"in the name of {T(t.get('incoming_entity'), 'INCOMING TENANT ENTITY')} and naming "
            "Landlord as additional insured; and (c) evidence reasonably satisfactory to Landlord "
            f"that {T(t.get('incoming_entity'), 'INCOMING TENANT ENTITY')} is in good standing "
            "and, if a foreign entity, is registered to do business in "
            f"{T(cfg.get('property_state'), 'PROPERTY STATE')}, and that the person executing "
            "this Addendum on its behalf is duly authorized to do so."
        )
        add_hanging_paragraph(
            doc, "Security Deposit",
            "The security deposit currently held by Landlord under the Lease shall remain on "
            f"deposit, shall be held for the account of "
            f"{T(t.get('incoming_entity'), 'INCOMING TENANT ENTITY')} from and after the "
            "Substitution Date, and shall be returned or applied in accordance with the Lease. "
            "No additional deposit is required. Prior Tenant assigns to "
            f"{T(t.get('incoming_entity'), 'INCOMING TENANT ENTITY')} all of its right, title and "
            "interest in the security deposit and waives any claim against Landlord for its "
            "return."
        )
        add_hanging_paragraph(
            doc, "Guaranty",
            "As a material inducement to Landlord to enter into this Addendum, to consent to the "
            "substitution of Tenant, and to release Prior Tenant, "
            f"{T(t.get('guarantor_name'), 'GUARANTOR NAME')} shall execute and deliver to "
            "Landlord the Guaranty of Lease attached to this Addendum as Exhibit A, which is "
            "incorporated herein by reference."
        )

    add_hanging_paragraph(
        doc, "Termination",
        f"Lease Termination will now be {T(cfg.get('new_termination_date'), 'NEW TERMINATION DATE')}."
    )

    rent = cfg.get("rent", {})
    if rent.get("stub_period"):
        stub = rent["stub_period"]
        stub_clause = (
            f"Base rent for the period {stub.get('start', T(None, 'STUB START'))} through "
            f"{stub.get('end', T(None, 'STUB END'))} shall continue at the existing rate of "
            f"{stub.get('amount', T(None, 'STUB MONTHLY AMOUNT'))} per month"
            + (", and Prior Tenant shall be responsible for all such rent accruing prior to the "
               "Substitution Date" if m3b else "")
            + ". "
        )
    else:
        stub_clause = ""
    add_hanging_paragraph(
        doc, "Base Rent",
        f"{stub_clause}Commencing {T(rent.get('new_rate_start'), 'NEW RATE START DATE')}, Tenant "
        f"shall pay base rent in the amount of {T(rent.get('annual'), 'NEW ANNUAL RENT')} per "
        f"year, payable in equal monthly installments of {T(rent.get('monthly'), 'NEW MONTHLY RENT')}. "
        f"Beginning on {T(rent.get('escalation_start'), 'ESCALATION START DATE')}, and on each "
        f"anniversary thereafter, the Annual Base Rent shall automatically increase by "
        f"{T(rent.get('escalation_rate'), 'ESCALATION RATE')} over the Annual Base Rent payable "
        "for the immediately preceding Lease Year, as set forth in the rent schedule below."
    )

    if m4:
        add_hanging_paragraph(
            doc, "Demised Premises",
            f"The Demised Premises is {T(cfg.get('premises_change_direction'), 'EXPANDED/REDUCED')} "
            f"to include {T(cfg.get('premises_change_desc'), 'DESCRIPTION OF SPACE ADDED/SURRENDERED')}, "
            f"resulting in a revised Rentable Square Footage of {T(cfg.get('new_rsf'), 'NEW RSF')} "
            f"and a revised pro rata share of {T(cfg.get('new_pro_rata'), 'NEW PRO RATA %')} for "
            "Operating Costs and Taxes, as depicted on the revised Exhibit A attached hereto."
        )

    broker_disclosure = cfg.get("broker_disclosure") or "any real estate broker"
    add_hanging_paragraph(
        doc, "Brokers",
        "The parties hereto acknowledge and agree that, in connection with this Addendum, they "
        f"have not utilized the services of {broker_disclosure}."
    )
    add_hanging_paragraph(
        doc, "Other Terms",
        "All other terms of the Prime Lease will remain in full force and effect. In the event "
        "of any conflict between this Addendum and the Prime Lease, this Addendum controls. This "
        "Addendum may be executed in counterparts and delivered by electronic transmission, each "
        "of which is an original and all of which together constitute one instrument."
    )

    notice_changed = m3b or m4
    if notice_changed:
        blocks = [("Landlord", cfg.get("landlord_notice_lines", [T(None, "LANDLORD NOTICE ADDRESS")]))]
        if m3b:
            blocks.append(("Tenant", cfg.get("tenant_notice_lines", [T(None, "INCOMING TENANT NOTICE ADDRESS")])))
            blocks.append(("Guarantor", [f"{T(cfg.get('tenant_change', {}).get('guarantor_name'), 'GUARANTOR NAME')}, at the address set forth in Exhibit A"]))
        add_notice_table(doc, blocks)

    if rent.get("schedule"):
        caption = f"RENT SCHEDULE — ADDENDUM TO LEASE — {T(cfg.get('premises_address'), 'PREMISES ADDRESS')}"
        add_rent_schedule_table(doc, caption, rent["schedule"])

    doc.add_paragraph(
        "If you are in agreement with the terms set forth above sign in the space provided below."
    )
    add_signature_page_marker_and_break(doc)

    add_signature_block(
        doc, "LANDLORD", T(cfg.get("landlord_entity"), "LANDLORD ENTITY"),
        [T(cfg.get("landlord_signatory"), "GABRIEL GOLDBERG, ITS MANAGER"), "Date:\t___________________________"],
        seal=True,
    )
    if m3b:
        t = cfg.get("tenant_change", {})
        add_signature_block(
            doc, "TENANT", T(t.get("incoming_entity_full"), "INCOMING TENANT ENTITY, FULL LEGAL NAME"),
            ["Name:\t__________________________", "Title:\t___________________________", "Date:\t___________________________"],
            seal=True,
        )
        consent = doc.add_paragraph(
            "Prior Tenant signs below solely to consent to the substitution of Tenant, to the "
            "assignment of the security deposit to " + T(t.get("incoming_entity"), "INCOMING TENANT ENTITY") +
            ", and to the retained liability described in the “Tenant” paragraph above."
        )
        consent.paragraph_format.space_before = Pt(12)
        add_signature_block(
            doc, "PRIOR TENANT", T(t.get("outgoing_entities"), "OUTGOING PARTIES"),
            ["Name:\t__________________________", "Title:\t___________________________", "Date:\t___________________________"],
            seal=True,
        )
        gp = doc.add_paragraph()
        gp.add_run("GUARANTOR — signs Exhibit A:").bold = True
        doc.add_paragraph(T(t.get("guarantor_name"), "GUARANTOR NAME"))
    else:
        add_signature_block(
            doc, "TENANT", T(cfg.get("tenant_entity"), "TENANT ENTITY"),
            ["Name:\t__________________________", "Title:\t___________________________", "Date:\t___________________________"],
            seal=True,
        )

    if m3b:
        add_exhibit_a_guaranty(doc, cfg)

    doc.save(output_path)
    return output_path


def main():
    args = sys.argv[1:]
    if "--template" in args:
        i = args.index("--template")
        out = args[i + 1]
        build_addendum({}, out)
        print(f"Template written: {out}")
        return
    if "--config" in args:
        i = args.index("--config")
        cfg_path = args[i + 1]
        out = args[i + 2]
        with open(cfg_path, encoding="utf-8") as f:
            cfg = json.load(f)
        build_addendum(cfg, out)
        print(f"Draft written: {out}")
        return
    sys.exit(__doc__)


if __name__ == "__main__":
    main()
