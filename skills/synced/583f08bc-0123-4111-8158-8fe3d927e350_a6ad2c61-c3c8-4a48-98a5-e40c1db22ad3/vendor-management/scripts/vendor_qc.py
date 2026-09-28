#!/usr/bin/env python3
"""ORA repeat-trade vendor contract QC gate.

Scans counterparty vendor/trade paper (paving, roofing, snow, HVAC,
landscaping, fire/life-safety, janitorial) where an ORA property entity is or
should be the contracting Owner.

Severity: BLOCK (do not execute) / HIGH / MED / LOW.

Shared extraction, OCR fallback, UNREADABLE gate, and report/CLI harness live
in ora_doc_qc.py, exactly as in pma-qc, listing-agreement-qc and lease-form-qc.
tools/package_skills.py SHARED_ROOT_DEPS injects a copy at packaging time so
the packaged .skill runs standalone; the sys.path append below is the
raw-checkout dev fallback.
"""

import re as _re
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent.parent / 'tools'))

from ora_doc_qc import new_registry, has, quote, run_cli

check, CHECKS = new_registry()


# ---- BLOCK -----------------------------------------------------------------

@check("V01", "BLOCK", "Contracting Purchaser is the manager, not the ORA property entity",
       "VC-1")
def _v01(ctx):
    mgr = has(ctx, r"(client|purchaser|customer)\b[^\n]{0,80}manage"
                   r"|manage(ment|rs)?,?\s*(inc|llc|lp|l\.l\.c)")
    agency = has(ctx, r"as agent for|on behalf of (the )?owner|as authorized agent"
                      r"|disclosed agent|for and on behalf of|as managing agent for")
    if mgr and not agency:
        return ("The named Purchaser appears to be a management company signing as "
                "principal, with no disclosed-agency language. The warranty, the "
                "indemnity, and every remedy in this instrument then run to the "
                "manager, not to the ORA entity that owns the asset and pays the "
                "invoice. Name the property LLC as Purchaser, or name it as an "
                "express third-party beneficiary with assignment on manager "
                "turnover. " + quote(ctx, r"(client|purchaser)\b"))
    return None


@check("V02", "BLOCK", "No-third-party-beneficiary clause with no Owner carve-out", "VC-1")
def _v02(ctx):
    bar = has(ctx, r"no provision of this [^.]{0,60}confer upon any other person or entity"
                   r"|shall not confer[^.]{0,60}(any|no) (third|other) part")
    carve = has(ctx, r"third[- ]party beneficiar|except that owner|other than owner")
    if bar and not carve:
        return ("The instrument expressly bars any non-party from claiming a remedy "
                "under it. Combined with V01 this is dispositive: the asset owner has "
                "no contractual standing on the warranty it is paying for. Carve the "
                "Owner entity out by name.")
    return None


@check("V03", "BLOCK", "Defect-notice period under 30 days", "VC-2")
def _v03(ctx):
    short = has(ctx, r"within \(?(one|two|three|four|five|six|seven|1|2|3|4|5|6|7)\)? "
                     r"?(\(\d\))? ?days after discovery"
                     r"|notice of any defect[^.]{0,60}\b(5|five|7|seven|10|ten) ?\(?\d?\)? ?days")
    if short:
        return ("Defect notice is due in days, not weeks. On a multi-tenant asset the "
                "manager, not Owner, is on site; a sub-30-day clock is unachievable "
                "and converts the warranty into a formality. Market is 30 days or "
                "'promptly upon discovery.' " + quote(ctx, r"days after discovery"))
    return None


@check("V04", "BLOCK", "Defect notice made time of the essence", "VC-2")
def _v04(ctx):
    if has(ctx, r"time being of the essence[^.]{0,80}warrant"
                r"|time is of the essence[^.]{0,80}(notice|warrant)"):
        return ("'Time of the essence' on the defect-notice covenant makes a one-day "
                "late notice a complete defense to an otherwise valid warranty claim. "
                "Strike it, or the notice period is the whole warranty.")
    return None


@check("V05", "BLOCK", "Warranty forfeited (not suspended) on payment timing", "VC-3")
def _v05(ctx):
    if has(ctx, r"warranty rights[^.]{0,120}(forfeited|void)"
                r"|(forfeited|become void)[^.]{0,80}warranty"):
        return ("Warranty rights are automatically and permanently forfeited on a "
                "payment timing failure — which a good-faith punch-list holdback or a "
                "disputed change order will trigger. Market is suspension of the "
                "contractor's warranty obligations during an uncured default, "
                "reinstated on payment. " + quote(ctx, r"warranty rights"))
    return None


@check("V06", "BLOCK", "Indemnity is one-way or reaches the contractor's own negligence",
       "VC-10")
def _v06(ctx):
    ind = has(ctx, r"(purchaser|customer|owner) (agrees to )?indemnif|hold contractor harmless"
                   r"|indemnify, defend, protect")
    mutual = has(ctx, r"contractor (shall|agrees to) indemnif|mutual(ly)? indemnif")
    carve = has(ctx, r"except to the extent (caused|arising)[^.]{0,60}"
                     r"(contractor|its own) negligen")
    if ind and not (mutual and carve):
        return ("Indemnity runs one way, with no carve-out for the contractor's own "
                "negligence. Owner is insuring the trade's ordinary negligence on "
                "Owner's own property. Make it mutual and carve out each party's own "
                "negligence and willful misconduct.")
    return None


@check("V07", "BLOCK", "No insurance, additional-insured, or COI requirement", "VC-11")
def _v07(ctx):
    if not has(ctx, r"certificate of insurance|additional insured|commercial general "
                    r"liability|waiver of subrogation|workers'? compensation insurance"):
        return ("The instrument contains no insurance article at all — no CGL limits, "
                "no additional-insured status for Owner and the manager, no waiver of "
                "subrogation, no workers' comp confirmation, no COI before "
                "mobilization. For work involving milling machines and rollers on an "
                "occupied site this is the single largest uninsured exposure in the "
                "document.")
    return None


@check("V08", "BLOCK", "No lien waiver or lien-release mechanic", "VC-12")
def _v08(ctx):
    if not has(ctx, r"lien waiver|waiver of lien|release of lien|partial (and|&) final "
                    r"waiver|conditional waiver"):
        lien_risk = has(ctx, r"lien fees|mechanic'?s lien|subcontractor")
        d = ("No lien waiver mechanic. Owner has no contractual right to conditional "
             "waivers on progress payments or unconditional waivers from the "
             "contractor, its subs and its suppliers at final payment. ")
        if lien_risk:
            d += ("The instrument references subcontractors and/or lien costs, so the "
                  "exposure is live, not theoretical. ")
        d += "Add a waiver-for-payment exchange as a condition precedent to each draw."
        return d
    return None


# ---- HIGH ------------------------------------------------------------------

@check("V09", "HIGH", "Warranty causation carve-out reaches 'any third parties'", "VC-4")
def _v09(ctx):
    if has(ctx, r"(caused by|act of)[^.]{0,90}third part"):
        return ("The warranty is defeated by any contribution from 'third parties,' "
                "not merely from Owner, its agents and employees. On a truck-court or "
                "tenant-parking asset, a tenant trailer, a snow contractor, or a "
                "delivery vehicle then answers virtually any pavement failure claim. "
                "Strike 'or any third parties.' " + quote(ctx, r"third part"))
    return None


@check("V10", "HIGH", "Warranty summary contradicted by the terms and conditions", "VC-5")
def _v10(ctx):
    matrix = has(ctx, r"covered by\s*warranty|not\s*covered|warranty information")
    guts = has(ctx, r"not responsible for any soft or unstable sub[- ]?grade"
                    r"|not be contractor'?s responsibility to check sub[- ]?base"
                    r"|not responsible for consequences of sub[- ]?base")
    if matrix and guts:
        return ("A warranty summary states cracking and pavement failure are covered "
                "while the terms disclaim responsibility for subgrade-driven sinking, "
                "breaking and cracking and impose no duty to inspect the sub-base. On "
                "a distressed lot most plausible failure modes are subgrade-driven, so "
                "the covered scope is far narrower than the summary implies. Reconcile "
                "them in one place; do not rely on the summary — an anti-construction "
                "clause and a merger clause will usually defeat contra proferentem.")
    return None


@check("V11", "HIGH", "No price hold through the actual work window", "VC-6")
def _v11(ctx):
    short = has(ctx, r"valid for thirty \(30\) days|pricing[^.]{0,80}within 30 days"
                     r"|valid for \(?\d{1,2}\)? days")
    hold = has(ctx, r"price(s)? (shall be|are) firm|firm through|price hold|not subject to "
                    r"escalation (through|until)")
    if short and not hold:
        return ("Pricing is held only for a short validity window and may be "
                "renegotiated at the contractor's option thereafter. Trade work of "
                "this scope is rarely scheduled and completed inside that window, so "
                "the quoted total is a floor, not a price. Obtain a written price hold "
                "through the actual scheduled work window.")
    return None


@check("V12", "HIGH", "Material escalator uncapped", "VC-6")
def _v12(ctx):
    esc = has(ctx, r"asphalt (price )?index|liquid asphalt|material rates increase"
                   r"|price escalat|index(ed)? price")
    cap = has(ctx, r"cap(ped)? at|shall not exceed[^.]{0,40}(percent|%)|maximum increase")
    if esc and not cap:
        return ("A commodity-index escalator passes unlimited upward price movement to "
                "Owner with no ceiling and no reciprocal downward adjustment. Cap the "
                "aggregate escalation as a percentage of contract price and make the "
                "adjustment two-way.")
    return None


@check("V13", "HIGH", "Escalator baseline missing, garbled, or unanchored", "VC-7")
def _v13(ctx):
    esc = has(ctx, r"index|escalat")
    garbled = has(ctx, r"over per (liquid )?ton|over the posted[^.]{0,40}price as posted"
                       r"|increase (in|of)[^.]{0,30}over per")
    anchored = has(ctx, r"baseline\s+(index\s+)?(price\s+)?of\s*\$"
                        r"|from a baseline of \$|baseline of \$[\d,.]+")
    if esc and (garbled or not anchored):
        d = ("The escalator lacks a clean numeric baseline. ")
        if garbled:
            d += ("The threshold phrase is grammatically incomplete — a dollar figure "
                  "is missing from the trigger, leaving the operative number to the "
                  "contractor's later assertion. ")
        d += ("Restate the clause to name the exact index, the exact baseline value, "
              "and the publication date it is drawn from, and attach the index print.")
        return d
    return None


@check("V14", "HIGH", "Fuel or similar surcharge uncapped and unilateral", "VC-6")
def _v14(ctx):
    if has(ctx, r"fuel surcharge|surcharge when published"):
        if not has(ctx, r"surcharge[^.]{0,80}(cap|shall not exceed|maximum)"):
            return ("A fuel surcharge is applied unilaterally off a published index "
                    "with no ceiling and no floor rebate. Cap it, or fold it into the "
                    "unit price and delete the article.")
    return None


@check("V15", "HIGH", "Deemed acceptance on failure to inspect", "VC-9")
def _v15(ctx):
    if has(ctx, r"failure to inspect[^.]{0,80}(signify|constitute) acceptance"
                r"|deemed accepted|signify acceptance of work"):
        return ("Work is deemed accepted, and payment obligations triggered, if Owner "
                "does not walk the site before demobilization. Condition acceptance on "
                "written notice of substantial completion plus a stated inspection "
                "window, and preserve latent-defect rights notwithstanding acceptance.")
    return None


@check("V16", "HIGH", "Site-condition disclaimer swallows the contracted scope", "VC-15")
def _v16(ctx):
    disc = has(ctx, r"not be contractor'?s responsibility to check sub[- ]?base"
                    r"|not responsible for consequences of sub[- ]?base"
                    r"|assumes[^.]{0,60}workable sub[- ]?base")
    invest = has(ctx, r"contractor shall (inspect|test|verify)[^.]{0,60}sub[- ]?base"
                      r"|core sample|proof roll")
    if disc and not invest:
        return ("The contractor assumes a conforming sub-base, disclaims any duty to "
                "verify it, and disclaims the consequences if it is deficient — while "
                "the priced scope is repair of pavement that is failing. Either buy a "
                "proof-roll or core investigation as a line item, or accept in writing "
                "that this is a maintenance treatment with no structural warranty.")
    return None


@check("V17", "HIGH", "Implied warranties disclaimed and damages waived one-way", "VC-10")
def _v17(ctx):
    disc = has(ctx, r"disclaims any and all representations and warranties"
                    r"|implied warranties of merchantability")
    mutual = has(ctx, r"each party (waives|disclaims)|neither party shall be liable for "
                      r"(any )?(indirect|consequential)")
    if disc and not mutual:
        return ("Implied warranties are disclaimed and indirect, incidental, special, "
                "punitive and consequential damages are excluded in the contractor's "
                "favor only. Make the damages waiver mutual, and preserve the express "
                "workmanship warranty notwithstanding the implied-warranty disclaimer.")
    return None


# ---- MED -------------------------------------------------------------------

@check("V18", "MED", "Cancellation and mobilization charges one-way and uncapped", "VC-8")
def _v18(ctx):
    fee = has(ctx, r"mobilization fee|cancels scheduled work|percent \(\d+%\) of the total "
                   r"contract price|twenty percent \(20%\)")
    recip = has(ctx, r"contractor (shall|agrees to) (pay|credit)[^.]{0,60}(delay|reschedul)")
    if fee and not recip:
        return ("Cancellation and remobilization charges run only against Owner, with "
                "no reciprocal credit when the contractor reschedules. Make the "
                "remedies mutual, or cap Owner's exposure at documented "
                "out-of-pocket cost.")
    return None


@check("V19", "MED", "Additional move-in charged with no coordination duty", "VC-8")
def _v19(ctx):
    if has(ctx, r"additional move[- ]?in|each additional mobilization"):
        if not has(ctx, r"contractor shall (sequence|phase|coordinate)"
                        r"|phased (work|access) plan"):
            return ("Per-mobilization charges apply while the contractor takes no "
                    "obligation to phase work around occupied-site access. On a "
                    "tenanted asset full simultaneous access is not deliverable. "
                    "Agree a phasing plan and price the mobilizations into it.")
    return None


@check("V20", "MED", "Confidentiality legend restricts competitive bidding", "VC-13")
def _v20(ctx):
    conf = has(ctx, r"not to disseminate it to any other person|contains confidential "
                    r"information|legally privileged")
    carve = has(ctx, r"except to (owner|its )?(counsel|lender|advisors|affiliates)"
                     r"|professional advisors")
    if conf and not carve:
        return ("A confidentiality legend bars disclosure of the pricing, with a "
                "litigation threat attached, and no carve-out for Owner's counsel, "
                "lender, property manager, affiliates, or competitive bid comparison. "
                "As written it impedes the bid process the document exists to serve. "
                "Add the advisor and affiliate carve-out or strike the legend.")
    return None


@check("V21", "MED", "Past-due interest or attorneys' fees one-way", "VC-14")
def _v21(ctx):
    fee = has(ctx, r"attorney'?s fees and court costs incurred by contractor"
                   r"|pay all collection costs|service charge of \d+% per month")
    mutual = has(ctx, r"prevailing party")
    if fee and not mutual:
        return ("Default interest, collection costs and attorneys' fees run only "
                "against Owner. Convert to a prevailing-party standard and confirm the "
                "monthly rate against the governing state's usury and commercial "
                "interest limits.")
    return None


@check("V22", "MED", "Waiver of exemptions or pre-consent to assignment of collection",
       "VC-14")
def _v22(ctx):
    if has(ctx, r"waives all claims or rights to claim exemptions"
                r"|consents to the assignment of collection rights"):
        return ("Owner pre-waives statutory exemptions and pre-consents to assignment "
                "of the receivable to a collection agent, before any dispute exists. "
                "Strike both; neither is necessary to secure payment on a net-30 "
                "trade invoice.")
    return None


@check("V23", "MED", "No binding completion schedule", "VC-17")
def _v23(ctx):
    unbound = has(ctx, r"not be bound to schedules|normal operating schedule"
                       r"|reserves the right to delay the start")
    bound = has(ctx, r"substantial completion (shall|will) occur|completion date of"
                     r"|liquidated damages")
    if unbound and not bound:
        return ("The contractor is expressly not bound to any schedule and may delay "
                "start at its discretion, while Owner carries cancellation and "
                "remobilization exposure on the same schedule. Commit start and "
                "substantial-completion dates in writing before mobilization.")
    return None


@check("V24", "MED", "Occupied-site obligations unqualified and risk-shifted to Owner",
       "VC-16")
def _v24(ctx):
    burden = has(ctx, r"removal of vehicles from the work site is the sole responsibility"
                      r"|damage to vehicles left on the work site is the responsibility "
                      r"of the purchaser|towing if required")
    qualified = has(ctx, r"commercially reasonable efforts|reasonable efforts to notify")
    if burden and not qualified:
        return ("Owner absolutely guarantees a cleared site by a fixed morning hour and "
                "absorbs damage to any vehicle left behind — at an asset whose parking "
                "is occupied by tenants and their customers, whom Owner does not "
                "control. Qualify to commercially reasonable efforts with stated tenant "
                "notice, and place towing on the contractor as a priced line item.")
    return None


@check("V25", "MED", "Change orders deemed approved without signature", "VC-8")
def _v25(ctx):
    if has(ctx, r"as though a written change order were approved and signed"
                r"|deemed (approved|deemed a change order)"):
        return ("Adjusted rates bind Owner 'as though' a signed change order existed. "
                "That is a unilateral price amendment. Require Owner's written "
                "authorization as a condition precedent to any rate adjustment or "
                "extra work.")
    return None


# ---- LOW -------------------------------------------------------------------

@check("V26", "LOW", "Governing law or venue not confirmed against the property state",
       "VC-18")
def _v26(ctx):
    if not has(ctx, r"governed by[^.]{0,80}laws of the State"
                    r"|construed and enforced in accordance"
                    r"|governing law|exclusive venue"):
        return ("No governing-law or venue provision. Specify the state where the "
                "property sits, for both law and exclusive venue.")
    return None


@check("V27", "LOW", "Acceptance block omits contracting entity and capacity", "VC-18")
def _v27(ctx):
    # Scoped to the acceptance block itself. "duly authorized" appears in the
    # modification clause of most trade forms; reading it as capacity language
    # for the signature is a false negative on the one check that catches the
    # wrong-entity execution this skill exists to prevent. Verified against the
    # Standard Paving seed form, where the unscoped version passed a document
    # whose acceptance block names no entity at all.
    m = _re.search(r"accepted:", ctx["t"], _re.I)
    if not m:
        return None
    block = ctx["t"][m.start():m.start() + 700]
    if _re.search(r"an authorized (officer|signatory)|\bIts:|limited liability company"
                  r"|a \w+ corporation", block, _re.I):
        return None
    if _re.search(r"purchaser:\s*_|printed name:\s*_|title:\s*_", block, _re.I):
        return ("The acceptance block collects a name and a title on blank lines with "
                "no contracting entity and no statement of capacity. Pre-fill the ORA "
                "property LLC, its state of formation, and the signatory's capacity "
                "before this is countersigned.")
    return None


if __name__ == "__main__":
    run_cli(CHECKS, "ORA repeat-trade vendor contract QC gate",
            ocr_absence_note=("Absence findings (V07, V08, V11, V13, V17, V19, V23, "
                              "V26, V27) are PROVISIONAL - confirm against the page "
                              "images before reporting a missing clause to a "
                              "counterparty."))
