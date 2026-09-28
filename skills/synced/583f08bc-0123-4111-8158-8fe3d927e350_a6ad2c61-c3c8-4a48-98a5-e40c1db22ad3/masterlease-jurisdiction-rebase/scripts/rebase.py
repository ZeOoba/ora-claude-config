#!/usr/bin/env python3
"""ORA Master Lease jurisdiction rebase engine.

Edits the OH-anchored controlled master DOCX in place (native formatting preserved)
into a state-conformed property template. Every substitution carries an expected match
count; a mismatch aborts and names the anchor — anchor drift in a new master revision
must surface loudly, never silently (2026-08-03 propagation-audit discipline).

Usage:
  python3 rebase.py --master <master.docx> --property MD-EAS [--out DIR]
  python3 rebase.py --master <master.docx> --all [--out DIR]

Anchors keyed to master v2.4.1 (2026-08-03). On assertion failure after a master rev:
diff the masters, update the anchor here or in config/, log it in SKILL.md changelog.
"""
import argparse, copy, json, pathlib, re, sys
from docx import Document
from docx.oxml.ns import qn

HERE = pathlib.Path(__file__).resolve().parent
CONFIG = HERE.parent / "config"
ANCHOR_STATE = "Ohio"  # the master's home state; residue check target

SAVINGS_TITLE = "Maximum Lawful Rate."
SAVINGS_BODY = ("  Notwithstanding any other provision of this Lease, the aggregate of all interest, "
    "late fees and other charges in the nature of interest payable by Tenant under this Lease shall "
    "not exceed the maximum rate or amount permitted by applicable law.  If any such charge is held "
    "to exceed the applicable lawful maximum, such charge shall be reduced to the maximum lawful "
    "amount, and any excess actually paid shall be credited against the next installments of rent coming due.")


def replace_in_paragraph(para, old, new):
    """Cross-run splice replace; returns count. Resumes past each replacement so
    appends containing their own anchor cannot loop."""
    count, search_from = 0, 0
    while True:
        runs = para.runs
        full = "".join(r.text for r in runs)
        i = full.find(old, search_from)
        if i < 0:
            return count
        search_from = i + len(new)
        j = i + len(old)
        pos, first = 0, True
        for r in runs:
            s, e = pos, pos + len(r.text)
            if e <= i or s >= j:
                pos = e
                continue
            ls, le = max(s, i) - s, min(e, j) - s
            if first:
                r.text = r.text[:ls] + new + r.text[le:]
                first = False
            else:
                r.text = r.text[:ls] + r.text[le:]
            pos = e
        count += 1


def apply(doc, rules):
    for old, new, expect in rules:
        n = sum(replace_in_paragraph(p, old, new) for p in doc.paragraphs)
        if n != expect:
            sys.exit(f"ANCHOR DRIFT: {old[:90]!r} expected {expect} match(es), found {n}. "
                     "Diff the new master against the prior revision and update this anchor.")


def insert_savings_clause(doc):
    """Clone the Counterparts paragraph (keeps list numbering + underlined-title style)."""
    if any(p.text.startswith(SAVINGS_TITLE) for p in doc.paragraphs):
        return  # idempotent
    target = next((p for p in doc.paragraphs if p.text.startswith("Counterparts; Electronic Signatures.")), None)
    if target is None:
        sys.exit("ANCHOR DRIFT: Counterparts paragraph not found — cannot place Maximum Lawful Rate clause.")
    newp = copy.deepcopy(target._p)
    target._p.addnext(newp)
    from docx.text.paragraph import Paragraph
    np = Paragraph(newp, target._parent)
    body_done = False
    for idx, r in enumerate(np.runs):
        if idx == 0:
            r.text = SAVINGS_TITLE
        elif not body_done and not r.underline:
            r.text = SAVINGS_BODY
            body_done = True
        else:
            r.text = ""
    if not body_done:
        sys.exit("Savings-clause insertion: no non-underlined body run found in cloned paragraph.")


def article(state_name):
    """'an' before vowel-sound state names (Indiana, Ohio, Iowa...); 'a Utah' — the
    only U-state is pronounced with a consonant sound."""
    return "an" if state_name[:1].upper() in "AEIO" else "a"


# --- NNN structure override -------------------------------------------------
# The master's default expense structure is modified gross with a calendar base
# year (ratified standing position #1, 2026-08-03). A property opts out of that
# default only via an explicit "lease_structure": "NNN" field in its
# config/properties.json entry, sourced from Gabriel's direction and the
# property's own established leasing practice — never applied by inference from
# an executed lease alone. 9050 Red Branch Road (MD-COL) is the first such
# override (2026-08-04): Gabriel confirmed the building runs NNN leases
# building-wide, consistent with the LINERX/Eddie Woo Park executed lease and
# ~15 years of suite leases on Muirkirk Properties' own NNN form. This does not
# alter any of the other five ratified positions (co-tenancy, 1.0x deposit, 10%
# late fee / 18% default rate + savings clause, flat Hazardous Materials ban, no
# extension option) — only the expense-recovery mechanism.

NNN_INSURANCE_DEF = (
    "shall mean all premiums and other costs paid or incurred by Landlord for the property, "
    "liability, rent-loss, and other insurance policies Landlord elects to carry on or in connection "
    "with the Project, the Building, or the Premises, as further described in the section of this "
    "Lease entitled “INSURANCE.”"
)


def nnn_text_rules():
    return [
        ("Base Year: [BASE YEAR]", "Base Year: Not applicable — full NNN", 1),  # v2.5 BLI line
        ("\tOPERATING COSTS AND TAXES.",
         "\tOPERATING COSTS, TAXES AND INSURANCE.", 1),
        ("Tenant shall pay to Landlord, Tenant's Proportionate Share (hereinafter defined) of the "
         "increase over base year of all Operating Costs (hereinafter defined) and/or Taxes "
         "(hereinafter defined). Base year shall be defined as the calendar year in which the "
         "Commencement Date occurs, being the [BASE YEAR] calendar year.  ",
         "Tenant shall pay to Landlord, as additional rent, Tenant's Proportionate Share (hereinafter "
         "defined) of all Operating Costs (hereinafter defined), Taxes (hereinafter defined), and "
         "Insurance (hereinafter defined), without regard to any base year -- i.e., on a full, triple "
         "net (NNN) basis from the Commencement Date, consistent with Landlord's established leasing "
         "practice at the Building.  ",
         1),
        ("Landlord may from time to time deliver to Tenant a written estimate of Tenant’s "
         "Proportionate Share of the increase in Operating Costs and Taxes for the then-current "
         "calendar year",
         "Landlord may from time to time deliver to Tenant a written estimate of Tenant’s "
         "Proportionate Share of Operating Costs, Taxes, and Insurance for the then-current calendar "
         "year",
         1),
        ("Landlord shall deliver to Tenant a statement setting forth the actual Operating Costs and "
         "Taxes for that year, Tenant’s Proportionate Share of the increase over the base year, "
         "and the estimated amounts paid by Tenant.",
         "Landlord shall deliver to Tenant a statement setting forth the actual Operating Costs, "
         "Taxes, and Insurance for that year, Tenant’s Proportionate Share thereof, and the "
         "estimated amounts paid by Tenant.",
         1),
    ]


def convert_to_nnn(doc):
    """Rewrite the modified-gross OPERATING COSTS AND TAXES article into a full NNN
    (Operating Costs + Taxes + Insurance, no base year) structure. Fails loudly on
    anchor drift, same discipline as apply()."""
    apply(doc, nnn_text_rules())

    paras = doc.paragraphs
    tax_idx = next((i for i, p in enumerate(paras) if p.text.startswith("“Taxes” ")
                     or p.text.startswith("\"Taxes\" ")), None)
    opcost_idx = next((i for i, p in enumerate(paras) if p.text.startswith("“Operating Costs” ")
                        or p.text.startswith("\"Operating Costs\" ")), None)
    if tax_idx is None or opcost_idx is None:
        sys.exit("ANCHOR DRIFT: could not locate the Operating Costs / Taxes definition paragraphs "
                  "to insert the Insurance definition — diff the master and update convert_to_nnn().")
    ins_idx = tax_idx + 2
    if ins_idx >= len(paras) or paras[ins_idx].text.strip() != "":
        sys.exit(f"ANCHOR DRIFT: expected a blank spacer paragraph at index {ins_idx} (two after the "
                  "Taxes definition) to hold the new Insurance definition; found non-blank or "
                  "out-of-range content. Diff the master and update convert_to_nnn().")

    target = paras[ins_idx]
    for r in list(target.runs):
        r._element.getparent().remove(r._element)
    r0 = target.add_run("“Insurance” ")
    r0.bold = True
    r1 = target.add_run(NNN_INSURANCE_DEF)
    r1.bold = False

    model_pPr = paras[opcost_idx]._p.find(qn("w:pPr"))
    target_pPr = target._p.find(qn("w:pPr"))
    if model_pPr is not None and target_pPr is not None:
        new_pPr = copy.deepcopy(model_pPr)
        target_rPr = target_pPr.find(qn("w:rPr"))
        if target_rPr is not None:
            new_rPr = new_pPr.find(qn("w:rPr"))
            if new_rPr is not None:
                new_pPr.replace(new_rPr, copy.deepcopy(target_rPr))
        target._p.replace(target_pPr, new_pPr)




# --- Single-tenant variant override -----------------------------------------
# Encodes the OH-SingleTenant-NNN template family's deltas vs. the multi-tenant
# master, recovered 2026-08-04 by paragraph diff of the v2.4.1 variant against
# the v2.4.1 base and verified on the v2.6 rebuild (25/25 structural checks,
# lease_qc 0/51). A config entry opts in via "variant": "single-tenant" (always
# paired with "lease_structure": "NNN" for this family). The variant stays
# generic-tokenized: entity/premises/PM fills are SKIPPED and are filled at
# drafting time. Judgment calls ratified 2026-08-04: the master's broader
# capital-amortization clause supersedes the old roof/structure-specific
# sentence; the gross-up sentence and the "Tenant's Allocation" definition are
# removed (meaningless at a 100% share with exclusive parking); relocation
# clause (h) is retained as an inert option.

ST_ALLOC_DEF = (
    "  For purposes hereof, \u201cTenant\u2019s Allocation\u201d shall be equal to a portion of the total "
    "number of available parking spaces in the Project based upon the ratio of (i) the rentable "
    "square footage of the Demised Premises compared to (ii) the rentable square footage for the "
    "entire Project. "
)


def single_tenant_rules():
    return [
        ("approximately [PREMISES RSF] square feet of rentable area in the building situated at "
         "[PREMISES ADDRESS] (such rentable area being hereinafter referred to as the \"Demised Premises\")",
         "the entire building situated at [PREMISES ADDRESS], containing approximately [BUILDING RSF] "
         "square feet of rentable area, together with all adjacent paved, parking and yard areas "
         "serving it (such building and areas being hereinafter referred to as the \"Demised Premises\")", 1),
        ("Demised Premises: [PREMISES ADDRESS] \u2014 approximately [PREMISES RSF] rentable square feet",
         "Demised Premises: [PREMISES ADDRESS] \u2014 the entire building, approximately [BUILDING RSF] "
         "rentable square feet", 1),
        (" If the Building is not fully occupied, for purposes of calculating Tenant's Proportionate "
         "Share, Landlord may \"gross up\" Operating Costs to what they would have been if the Building "
         "or Project had been fully occupied. ",
         " ", 1),
        ("\"Tenant's Proportionate Share\" shall mean the proportion that the rentable square footage of "
         "the Demised Premises bears to the total rentable square footage of the Building, being "
         "[BUILDING RSF] square feet (Franklin County Auditor Parcel No. [PARCEL NO]). Tenant's "
         "Proportionate Share is estimated to be [PROPORTIONATE SHARE]%.",
         "\"Tenant's Proportionate Share\" shall mean one hundred percent (100%), Tenant leasing the "
         "entire Building, containing [BUILDING RSF] square feet (Franklin County Auditor Parcel No. "
         "[PARCEL NO]).", 1),
        ("Tenant\u2019s Proportionate Share: [PROPORTIONATE SHARE]%",
         "Tenant\u2019s Proportionate Share: 100% (entire Building)", 1),
        ("Tenant shall be entitled to a non-exclusive right to use the unreserved parking spaces in "
         "the Project adjacent to the Building in order to satisfy the general operational requirements "
         "of the Demised Premises in an amount not to exceed the Tenant\u2019s Allocation (hereinafter "
         "defined).  Notwithstanding the foregoing, Landlord reserves the right to designate specific "
         "spaces for Tenant\u2019s use or use by any other occupant of the Project and to prohibit "
         "Tenant\u2019s use of other designated spaces.",
         "Tenant shall have the exclusive right to use the parking areas in the Project for Tenant's "
         "employees, agents, customers and invitees, subject to the terms of this Lease.", 1),
        (ST_ALLOC_DEF, "", 1),
        ("prevented by Tenant\u2019s performance of its maintenance obligations.",
         "prevented by Tenant\u2019s performance of its maintenance obligations.  In addition, Tenant, at "
         "Tenant's sole cost and expense, shall provide all janitorial service, snow and ice removal, "
         "lawn mowing, landscaping, exterior sweeping and pest control for the Demised Premises and "
         "the Project, shall keep all parking and yard areas clean and free of debris and free from "
         "accumulation of snow and ice, and shall maintain the Demised Premises in a first-class and "
         "fully operative condition.", 1),
    ]


def convert_to_single_tenant(doc):
    """Rewrite the multi-tenant master into the single-tenant variant (entire-building
    demise, 100% share, exclusive parking, tenant site services). Fails loudly on
    anchor drift, same discipline as apply()."""
    apply(doc, single_tenant_rules())

def build_rules(P, L):
    st = L["state"]
    es = P.get("entity_state")
    if not es:
        sys.exit(f"{P['entity']}: missing 'entity_state' in config/properties.json. The LLC's "
                 "formation state must be SOURCED (Articles of Organization, ratified LLC roster, "
                 "or an executed lease's recital) — never assumed from the property's location. "
                 "Fail-closed by design (2026-08-03 eval finding).")
    rules = [
        ("[LANDLORD ENTITY]", P["entity"], 4),  # v2.5: +1 (BLI page)
        ("a [STATE] limited liability company", f"{article(es)} {es} limited liability company", 3),  # v2.5: +1 (BLI page)
        ("the building situated at [PREMISES ADDRESS] (such rentable area",
         f"the building situated at {P['premises']} (such rentable area", 1),
        ("the building known as [BUILDING ADDRESS], containing [BUILDING RSF] square feet of rentable area",
         P["building_def"], 1),
        (f"national banks in the State of {ANCHOR_STATE} are authorized to close",
         f"national banks in the State of {st} are authorized to close", 1),
        ("bears to the total rentable square footage of the Building, being [BUILDING RSF] square feet ",
         P["share_denominator"], 1),
        ("(Franklin County Auditor Parcel No. [PARCEL NO])", L["parcel_reference"], 1),
        (f"in accordance with the laws of the State of {ANCHOR_STATE}.",
         f"in accordance with the laws of the State of {st}.", 2),  # USE + governing law
        (f"is qualified to do business in the State of {ANCHOR_STATE},",
         f"is qualified to do business in the State of {st},", 1),
        (f"the federal ESIGN Act and the {ANCHOR_STATE} Uniform Electronic Transactions Act.", L["ueta"], 1),
        ("Tenant, as a month-to-month tenant, shall continue to be subject to all of the conditions and covenants of this Lease.",
         "Tenant, as a month-to-month tenant, shall continue to be subject to all of the conditions and covenants of this Lease.  "
         f"The foregoing is in addition to, and not in limitation of, any rights and remedies of Landlord under {L['holdover_statute']}.", 1),
        ("proceed to recover possession under and by virtue of the provisions of the laws or by such other proceedings, including re-entry and possession, as may be applicable.",
         f"proceed to recover possession under and by virtue of the laws of the State of {st}, including {L['possession_statutes']}, "
         "or by such other proceedings, including re-entry and possession, as may be applicable.", 1),
        ("and in the regulations adopted and publications promulgated pursuant to said laws or any future laws or regulations",
         f"and in the regulations adopted and publications promulgated pursuant to said laws, any analogous laws of the State of {st} "
         f"(including {L['env_overlay']}), or any future laws or regulations", 1),
        ("COPY TO:[PROPERTY MANAGER]", P["pm_block"][0], 1),
        ("[MANAGER STREET ADDRESS]", P["pm_block"][1], 1),  # v2.5: master pre-tokenized
        ("[MANAGER CITY, STATE ZIP]", P["pm_block"][2], 1),  # v2.5: master pre-tokenized
        ("ATTN: [MANAGER CONTACT]", P["pm_block"][3], 1),
    ]
    # v2.5 Basic Lease Information page fills
    rules.append((" [PREMISES ADDRESS] — approximately", f" {P['premises']} — approximately", 1))
    m_bd = re.match(r"the building known as (.+), containing (.+) square feet of rentable area", P["building_def"])
    if m_bd:
        rules.append(("[BUILDING ADDRESS] — [BUILDING RSF] rentable square feet (Parcel No. [PARCEL NO])",
                      f"{m_bd.group(1)} — {m_bd.group(2)} rentable square feet {L['parcel_reference'].strip()}", 1))
    if P.get("project_def"):
        rules.append(("the Building together with the land on which it is situated and all parking areas, drives, walkways and other common areas serving it",
                      P["project_def"], 1))
    if P.get("payment_direction"):
        rules.append(("to [PROPERTY MANAGER], at [MANAGER ADDRESS] through the tenant online portal, payable to Landlord,",
                      P["payment_direction"], 1))
    if L.get("extra_no_recording"):
        rules.append(("Any such recording shall be void and shall constitute an Event of Default.",
                      "Any such recording shall be void and shall constitute an Event of Default." + L["extra_no_recording"], 1))
    return rules


def post_check(path, P, L):
    full = "\n".join(p.text for p in Document(str(path)).paragraphs)
    errs = []
    if P.get("variant") == "single-tenant":
        for tok in ("[PREMISES RSF]", "[PROPORTIONATE SHARE]", "[BASE YEAR]"):
            if tok in full:
                errs.append(f"single-tenant variant but {tok} token still present")
        for residue in ("gross up", "Allocation", "non-exclusive"):
            if residue in full:
                errs.append(f"single-tenant variant but multi-tenant residue: {residue}")
        for marker in ("the entire building situated at [PREMISES ADDRESS]",
                       "one hundred percent (100%), Tenant leasing the entire Building",
                       "janitorial service, snow and ice removal"):
            if marker not in full:
                errs.append(f"single-tenant marker missing: {marker[:50]}")
        for tok in ("[LANDLORD ENTITY]", "[PREMISES ADDRESS]"):
            if tok not in full:
                errs.append(f"generic variant should retain token {tok}")
        if SAVINGS_TITLE not in full:
            errs.append("savings clause missing")
        if P.get("lease_structure") == "NNN":
            if "OPERATING COSTS, TAXES AND INSURANCE" not in full:
                errs.append("NNN heading missing")
            if "\u201cInsurance\u201d " not in full and '"Insurance" ' not in full:
                errs.append("Insurance defined term missing")
        if errs:
            sys.exit(f"POST-CHECK FAILED for {path.name}: {errs}")
        return
    if ANCHOR_STATE in full:
        errs.append(f"{ANCHOR_STATE} residue present")
    for tok in ("[STATE]", "[LANDLORD ENTITY]", "[PREMISES ADDRESS]"):
        if tok in full:
            errs.append(f"unfilled token {tok}")
    if SAVINGS_TITLE not in full:
        errs.append("savings clause missing")
    if L["state"] not in full:
        errs.append("state name absent")
    if P.get("lease_structure") == "NNN":
        if "[BASE YEAR]" in full:
            errs.append("NNN property but [BASE YEAR] token still present")
        if "OPERATING COSTS, TAXES AND INSURANCE" not in full:
            errs.append("NNN property but OPERATING COSTS, TAXES AND INSURANCE heading missing")
        if "“Insurance” " not in full and '"Insurance" ' not in full:
            errs.append("NNN property but Insurance defined term missing")
    if errs:
        sys.exit(f"POST-CHECK FAILED for {path.name}: {errs}")


def rebase_one(master_path, P, L):
    """Single source of truth for the per-property pipeline — used by both main()
    and the test suite, so a step added here (like the NNN override) can't drift
    out of sync between the CLI path and its own tests again."""
    doc = Document(str(master_path))
    if P.get("variant") == "single-tenant":
        # Generic-tokenized variant: no entity/premises/PM fills, no state overlay
        # (the family is anchored to the master's own state). Footer token stays.
        convert_to_single_tenant(doc)
        if P.get("lease_structure") == "NNN":
            convert_to_nnn(doc)
        insert_savings_clause(doc)
        return doc
    apply(doc, build_rules(P, L))
    if P.get("lease_structure") == "NNN":
        convert_to_nnn(doc)
    insert_savings_clause(doc)
    for sec in doc.sections:  # v2.5: fill footer lease identifier
        for fp in sec.footer.paragraphs:
            replace_in_paragraph(fp, "[PREMISES ADDRESS]", P["premises"])
    return doc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--master", required=True)
    ap.add_argument("--property", dest="prop")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    props = json.loads((CONFIG / "properties.json").read_text(encoding="utf-8"))
    states = json.loads((CONFIG / "state_overlays.json").read_text(encoding="utf-8"))
    props.pop("_comment", None)
    keys = list(props) if a.all else [a.prop]
    if not keys or keys == [None]:
        sys.exit("Specify --property KEY or --all. Known: " + ", ".join(props))
    unknown = [k for k in keys if k not in props]
    if unknown:
        sys.exit(f"Unknown property key(s) {unknown}. Known: " + ", ".join(props) +
                 ". Add new properties to config/properties.json (facts from source of record only).")

    m = re.search(r"_v(\d+\.\d+(?:\.\d+)?(?:-[A-Za-z0-9]+)?)_", pathlib.Path(a.master).name)
    ver = m.group(1) if m else "UNKNOWN"
    outdir = pathlib.Path(a.out); outdir.mkdir(parents=True, exist_ok=True)

    for k in keys:
        P = props[k]
        L = states.get(P["state_code"])
        if P.get("variant") == "single-tenant":
            L = L or {}
        elif not L or L.get("RESEARCH_REQUIRED"):
            sys.exit(f"{k}: state overlay {P['state_code']} is RESEARCH-REQUIRED — complete "
                     "config/state_overlays.json with fresh statutory research first (fail-closed by design).")
        doc = rebase_one(a.master, P, L)
        out = outdir / f"ORA_MasterLease_ShallowBay_{P['label']}_v{ver}_TEMPLATE.docx"
        doc.save(str(out))
        post_check(out, P, L)
        print(f"OK {k} -> {out.name}")
    print("ALL REBASES PASSED")


if __name__ == "__main__":
    main()
