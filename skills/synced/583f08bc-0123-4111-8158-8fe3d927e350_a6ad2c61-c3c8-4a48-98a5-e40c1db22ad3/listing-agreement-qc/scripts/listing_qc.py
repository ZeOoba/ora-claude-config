#!/usr/bin/env python3
"""
listing_qc.py — Oxford Realty Advisors brokerage listing agreement QC gate.

Scans a broker listing agreement (sale, lease, or sale-and-lease) for the 25
systemic defects catalogued in the C&W form register. Reads DOCX (via
word/document.xml), PDF (via pdftotext, with OCR fallback), or plain text.

Usage:
    python3 listing_qc.py <agreement.docx|pdf|txt> [more ...] [--allow-tokens]
                          [--no-ocr] [--json]

Exit codes: 0 = clean, 1 = one or more failures, 2 = usage/extraction/
UNREADABLE error.

Severity: BLOCK (do not execute) / HIGH / MED / LOW.

Checks are written to FAIL on the DEFECT. A check that does not fire means the
protective language was found. Every check reports the ORA standing position it
enforces (see references/standing-positions.md).

Extraction, the OCR fallback, the UNREADABLE gate, and the report/CLI harness
now live in ora_doc_qc.py (shared with pma-qc and lease-form-qc). This
retrofit closes a real bug: this file's own former extract() had no OCR
fallback and no "insufficient words" floor, so a scanned counterparty PDF with
no text layer extracted to an empty string, tripped zero of the 25 checks, and
the tool reported the document clean — the worst failure mode a pre-signature
QC gate can have. See ora_doc_qc.py's docstring for the incident that
prompted it.

ora_doc_qc.py itself is NOT vendored inside this skill's scripts/ directory —
it fans out from the repo-root tools/ora_doc_qc.py via package_skills.py's
SHARED_ROOT_DEPS (the same pattern target-markets.json already uses for four
other skills), landing at scripts/ora_doc_qc.py inside the packaged .skill so
this skill installs and runs standalone. In a raw repo/worktree checkout
(where nothing has been packaged yet), the sys.path shim below falls back to
the repo-root tools/ directory so `python listing-agreement-qc/scripts/
listing_qc.py ...` still works for local development.
"""

import re
import sys
from pathlib import Path

# Dev-checkout fallback: Python already puts this script's own directory at
# sys.path[0] on startup, so append (not insert) the repo-root tools/
# directory as a lower-priority fallback — a packaged .skill ships
# ora_doc_qc.py alongside this script (via SHARED_ROOT_DEPS, see module
# docstring above), so that co-located copy is always tried first,
# structurally, regardless of what does or doesn't exist under an install
# root's own tools/ directory. A raw repo/worktree checkout has no such
# co-located copy, so the appended repo-root tools/ path is what resolves
# ora_doc_qc there. Verified 2026-08-17 against both a raw worktree checkout
# and a real extracted .skill (see task-4-fix-report.md).
sys.path.append(str(Path(__file__).resolve().parent.parent.parent / 'tools'))

from ora_doc_qc import new_registry, has, norm, run_cli

# ------------------------------------------------------------------- checks
# Each check: (id, severity, title, position_ref, fn(ctx) -> None | detail str)
# ctx = {"t": normalized text, "raw": raw text, "meta": meta, "name": filename}


def is_sale_scope(ctx):
    return has(ctx, r"exclusive right to sell(?! and lease)")


def has_lease_schedule(ctx):
    return has(ctx, r"\bLEASES?\b\s*Rate:") or has(ctx, r"Lease\s+Commission\s+Percentage")


check, CHECKS = new_registry()


# ---- BLOCK -----------------------------------------------------------------

@check("L1", "BLOCK", "Conflicting definitions of gross sale price", "SP-1")
def _l1(ctx):
    broad = has(ctx, r"gross sale price shall include any and all consideration")
    narrow = has(ctx, r"Computation of Total Sales Price")
    if broad and narrow:
        return ("Rate paragraph defines gross sale price as 'any and all consideration "
                "received including ... release of existing liabilities' while the "
                "Computation paragraph limits it to cash plus assumed debt. Two "
                "governing definitions; the broad one controls by ambiguity.")
    if broad and not narrow:
        return "Only the broad 'any and all consideration' definition is present; no Computation paragraph."
    return None


@check("L2", "BLOCK", "No excluded-prospect carve-out", "SP-2")
def _l2(ctx):
    if has(ctx, r"exclu(?:ded|sion)\s+(?:prospect|part(?:y|ies)|purchaser)"):
        return None
    if has(ctx, r"Exhibit [A-Z][^.]{0,40}Excluded"):
        return None
    return ("Exclusive right to sell with no named exclusions. A buyer Owner sources "
            "alone - including a sitting or adjacent-portfolio tenant - triggers a full fee.")


@check("L3", "BLOCK", "No affiliate / involuntary-transfer carve-out", "SP-3")
def _l3(ctx):
    reach = has(ctx, r"title is conveyed in any manner") or has(ctx, r"sells? any interest")
    # An "unaffiliated third party" reference is NOT a carve-out; require real
    # exclusionary language tied to a commission.
    carve = (has(ctx, r"no commission[^.]{0,160}(?:affiliat|common control|deed in lieu|condemn|eminent domain)")
             or has(ctx, r"(?<!un)affiliated? (?:entit|transfer|part)")
             or has(ctx, r"under common control")
             or has(ctx, r"deed in lieu of foreclosure")
             or has(ctx, r"condemnation or eminent domain"))
    if reach and not carve:
        return ("Commission reaches any conveyance 'in any manner' / 'any interest' with no "
                "carve-out for affiliate or common-control transfers, estate planning, "
                "foreclosure / deed in lieu, or condemnation.")
    return None


@check("L4", "BLOCK", "Automatic post-expiration holdover", "SP-4")
def _l4(ctx):
    if has(ctx, r"shall continue after the expiration date on a month-to-month basis"):
        return ("Term auto-extends month-to-month after expiration rather than requiring an "
                "affirmative written election. Stacks on top of the post-term tail.")
    return None


@check("L5", "BLOCK", "No Owner termination right during the primary term", "SP-5")
def _l5(ctx):
    holdover_only = has(ctx, r"terminate the holdover month-to-month period")
    general = has(ctx, r"(?:either party|Owner) may terminate this agreement")
    if holdover_only and not general:
        return ("The only termination right runs to the holdover period. Owner is locked for "
                "the entire primary term with no performance or convenience out.")
    if not holdover_only and not general:
        return "No termination right of any kind is granted to Owner."
    return None


@check("L6", "BLOCK", "Tail list not limited to broker-procured prospects", "SP-6")
def _l6(ctx):
    if has(ctx, r"submitted by any party during the term"):
        return ("Post-term protection list captures prospects 'submitted by any party', which "
                "includes prospects Owner itself introduced. Limit to parties introduced by "
                "or through Broker who received substantive services.")
    return None


@check("L7", "BLOCK", "Prospect list delivery is not a condition precedent", "SP-6")
def _l7(ctx):
    if has(ctx, r"will provide to Owner a list of prospective") and not has(
            ctx, r"condition precedent|failure to (?:deliver|provide) (?:such|the) list"):
        return ("Broker must deliver the prospect list within 10 days but no consequence "
                "attaches to failure. Make timely delivery a condition precedent to any tail fee.")
    return None


@check("L8", "BLOCK", "Post-term tail is uncapped", "SP-6")
def _l8(ctx):
    if has(ctx, r"\b180 days after the end of the term\b") and not has(
            ctx, r"in no event shall the aggregate post-term protection period exceed"):
        return "180-day tail is extendable on continuing negotiations with no aggregate cap. ORA cap is 270 days."
    return None


@check("L9", "BLOCK", "Unfilled template token", "SP-16")
def _l9(ctx):
    if ctx["allow_tokens"] or "_TEMPLATE" in ctx["name"]:
        return None
    toks = set(re.findall(r"\[[A-Z][A-Z0-9 _/&-]{2,40}\]", ctx["t"]))
    toks = {t for t in toks if not re.match(r"\[Schedule", t, re.I)}
    if toks:
        return "Unfilled tokens present: " + ", ".join(sorted(toks)[:8])
    return None


# ---- HIGH ------------------------------------------------------------------

@check("L10", "HIGH", "Lease language surviving in a sale-only instrument", "SP-7")
def _l10(ctx):
    if not is_sale_scope(ctx) or has_lease_schedule(ctx):
        return None
    hits = []
    for label, pat in [
        ("Sec.2 Services", r"obtain a satisfactory purchaser and tenant"),
        ("Sec.5 Commission", r"list of prospective purchasers and tenants"),
        ("Sec.6 Outside brokers", r"represent the purchaser or tenant"),
        ("Sec.7 caption", r"Representation of Purchasers and Tenants"),
        ("Sec.9 Authority", r"right to lease and sell"),
        ("Sec.10 Prof. Advice", r"prospective purchaser or tenant, Owner will rely"),
    ]:
        if has(ctx, pat):
            hits.append(label)
    if hits:
        return ("Sale-only grant and no lease commission schedule, but tenant-procurement "
                "language survives at: " + "; ".join(hits) +
                ". Broker is tasked with procuring tenants at no agreed rate - quantum meruit exposure.")
    return None


@check("L11", "HIGH", "No negative covenant barring a lease commission", "SP-7")
def _l11(ctx):
    if not is_sale_scope(ctx) or has_lease_schedule(ctx):
        return None
    if has(ctx, r"[Nn]o commission .{0,80}payable .{0,60}in connection with any lease"):
        return None
    return ("Sale-only agreement lacks an express 'no commission payable on any lease, renewal, "
            "extension, expansion or occupancy agreement' covenant.")


@check("L12", "HIGH", "Blanket dual-agency consent", "SP-8")
def _l12(ctx):
    if not has(ctx, r"consents to such dual representation"):
        return None
    if has(ctx, r"prior to .{0,40}commencing representation") and has(
            ctx, r"does not waive|transaction-specific"):
        return None
    detail = "Advance blanket consent to dual representation"
    if has(ctx, r"provided C&W timely discloses|timely disclos"):
        detail += "; conditioned only on undefined 'timely' disclosure"
    return detail + ". Ohio requires a transaction-specific written consent (R.C. 4735.71)."


@check("L13", "HIGH", "No Ohio agency disclosure form referenced", "SP-8")
def _l13(ctx):
    if not has(ctx, r"\bOhio\b"):
        return None
    if has(ctx, r"[Aa]gency [Dd]isclosure|Consumer Guide to Agency|brokerage policy on agency|4735\.5[357]"):
        return None
    return ("No agency disclosure statement or brokerage agency policy is referenced or attached "
            "(R.C. 4735.53 / 4735.55). Request it for the deal folder.")


@check("L14", "HIGH", "Broker authority to execute documents not negatived", "SP-9")
def _l14(ctx):
    if has(ctx, r"shall not have the authority to execute"):
        return None
    return "Agreement does not expressly deny Broker authority to execute leases, amendments, or contracts on Owner's behalf."


@check("L15", "HIGH", "Seller-carry paper not valued at present value", "SP-1")
def _l15(ctx):
    if not has(ctx, r"Computation of Total Sales Price"):
        return None
    if has(ctx, r"present value, discounted at the then-prevailing market rate"):
        if has(ctx, r"reasonably determined by Owner in good faith"):
            return None
        return "Present-value discount is present but the discount rate is not determined by Owner."
    return "Purchase-money / seller-carry consideration is not discounted to present value."


@check("L16", "HIGH", "Purchase-option double compensation not blocked", "SP-1")
def _l16(ctx):
    if not has(ctx, r"Purchase Option"):
        return None
    if has(ctx, r"credited dollar-for-dollar") and has(ctx, r"compensated twice"):
        return None
    return "Option-consideration commission is not credited against the closing commission; broker may be paid twice."


@check("L17", "HIGH", "Outside-broker dispute may delay Owner", "SP-10")
def _l17(ctx):
    if not has(ctx, r'"?outside broker"?'):
        return None
    if has(ctx, r"shall not be delayed on account of any such unresolved commission dispute") and \
       has(ctx, r"Owner's obligation shall be limited to paying the commission"):
        return None
    return ("Co-broker split dispute is not expressly barred from delaying Owner's negotiations, "
            "or Owner's exposure is not capped at the Schedule amount.")


@check("L18", "HIGH", "Gross price sweeps in 'release of existing liabilities'", "SP-1")
def _l18(ctx):
    if has(ctx, r"including but not limited to release of existing liabilities"):
        return ("'Release of existing liabilities' is undefined and unqualified; it can be read to "
                "reach a discounted payoff or lender forgiveness, which is not consideration Owner receives.")
    return None


@check("L19", "HIGH", "No lender-consent / encumbrance acknowledgment", "SP-11")
def _l19(ctx):
    if has(ctx, r"lender.{0,40}consent|mortgagee.{0,30}consent|subject to .{0,30}(?:existing )?(?:mortgage|deed of trust|loan)"):
        return None
    return ("No acknowledgment that a sale may require lender consent, defeasance, or payoff, and no "
            "provision that no commission is earned if a required lender consent is withheld.")


@check("L20", "HIGH", "Owner entity name inconsistent", "SP-12")
def _l20(ctx):
    names = re.findall(r"\b((?:[A-Z][A-Za-z0-9.&'-]*[,]?\s+){1,6}L\.?L\.?C\.?)(?=\s|$|[(,.])",
                       ctx["t"])
    canon = {}
    for n in names:
        toks = n.strip().split()
        # Compare on the entity tail so a leading caption ("LISTING AGREEMENT FOR
        # SALE ...") does not create a spurious second variant.
        tail = " ".join(toks[-3:])
        key = re.sub(r"[^A-Z0-9]", "", tail.upper())
        if len(key) < 8:
            continue
        canon.setdefault(key, set()).add(tail)
    bad = {k: v for k, v in canon.items() if len(v) > 1}
    if bad:
        first = list(bad.values())[0]
        return "Owner entity rendered inconsistently: " + " vs ".join(sorted(first)) + \
               ". Conform to the exact Secretary of State registered name and the county owner-of-record string."
    return None


@check("L21", "HIGH", "Address range vs parcel count mismatch", "SP-13")
def _l21(ctx):
    m = re.search(r"located at ([^,]{4,60}),", ctx["t"])
    parcels = re.findall(r"Parcel ID:?\s*([0-9-]{6,20})", ctx["t"], re.I)
    if not m:
        return None
    addr = m.group(1)
    ranged = re.search(r"\d+\s*-\s*\d+", addr)
    if ranged and len(set(parcels)) == 1:
        return (f"Property described as a range ('{addr.strip()}') against a single parcel ID "
                f"({parcels[0]}). Verify the parcel covers the full range; if two parcels, list both.")
    return None


# ---- MED / LOW -------------------------------------------------------------

@check("L22", "MED", "Mixed automatic and manual section numbering", "SP-14")
def _l22(ctx):
    m = ctx["meta"]
    if m.get("format") != "docx":
        return None
    if m.get("auto_numbered_paras", 0) and m.get("manual_numbered_paras", 0):
        return (f"{m['auto_numbered_paras']} auto-numbered paragraph(s) coexist with "
                f"{m['manual_numbered_paras']} hard-typed section number(s). Inserting a "
                "paragraph will renumber only part of the document. Convert all to hard-typed text.")
    return None


@check("L23", "MED", "Retroactive commencement", "SP-15")
def _l23(ctx):
    m = re.search(r"commence on ([A-Z][a-z]+ \d{1,2}(?:st|nd|rd|th)?,? \d{4})", ctx["t"])
    d = re.search(r"Date:\s*_?([A-Z][a-z]{2} ?\d{1,2}[,_ ]{1,3}\d{4}|\d{1,2}/\d{1,2}/\d{2,4})", ctx["t"])
    if m and d:
        return (f"Term commences {m.group(1)} while a signature block carries {d.group(1)}. "
                "Confirm the commencement date is not retroactive to execution.")
    return None


@check("L24", "LOW", "Template residue in header / footer", "SP-14")
def _l24(ctx):
    h = ctx["meta"].get("headers", "") + " " + ctx["meta"].get("footer", "")
    if re.search(r"A PROPOSAL FOR|DRAFT|\[Property\]|Insert ", h, re.I):
        return f"Running header/footer carries template residue: '{norm(h)[:90].strip()}'."
    return None


@check("L25", "LOW", "Typographical defects", "SP-14")
def _l25(ctx):
    hits = []
    if re.search(r"\b\d{5}[a-z]", ctx["t"]):
        hits.append("missing space after ZIP code")
    if re.search(r"\s+,", ctx["t"]):
        hits.append("space before comma")
    if has(ctx, r"Each party represent to"):
        hits.append("'Each party represent' subject-verb disagreement")
    if has(ctx, r"\bPurchasee|Premisess|aggreement\b"):
        hits.append("spelling")
    return "; ".join(hits) if hits else None


# --------------------------------------------------------------------- driver

if __name__ == "__main__":
    run_cli(CHECKS, "ORA listing agreement QC gate", want_footer=True,
            ocr_absence_note=("Absence findings (L2, L3, L5, L7, L8, L11, "
                              "L12-L17, L19) are PROVISIONAL - OCR text is "
                              "lossy, so confirm against the page images "
                              "before reporting a missing carve-out or "
                              "clause to a counterparty."))
