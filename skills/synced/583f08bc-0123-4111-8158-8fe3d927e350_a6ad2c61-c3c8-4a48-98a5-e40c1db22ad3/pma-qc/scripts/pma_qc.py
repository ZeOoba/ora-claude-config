#!/usr/bin/env python3
"""
pma_qc.py — Oxford Realty Advisors property management agreement QC gate.

Scans a third-party property management agreement (ORA or an ORA entity as
Owner) for the 34 systemic defects catalogued in the KRG form register.

Usage:
    python3 pma_qc.py <agreement.docx|pdf|txt> [more ...] [--allow-tokens]
                      [--no-ocr] [--json]

Exit codes: 0 = clean, 1 = one or more failures, 2 = usage/extraction/
UNREADABLE error.

Severity: BLOCK (do not execute) / HIGH / MED / LOW.

Checks FAIL on the DEFECT. A check that does not fire means the protective
language was found. Every check reports the ORA standing position it enforces
(see references/standing-positions.md — PM-1 .. PM-19, PROPOSED not ratified).

Extraction, the OCR fallback, the UNREADABLE gate, and the report/CLI harness
now live in ora_doc_qc.py, shared with listing-agreement-qc and lease-form-qc
(both retrofitted onto it on this same branch). This file was the reference
port: everything below the imports is pma-qc's own 34 checks.

ora_doc_qc.py itself is NOT vendored inside this skill's scripts/ directory —
it fans out from the repo-root tools/ora_doc_qc.py via package_skills.py's
SHARED_ROOT_DEPS (the same pattern target-markets.json already uses for four
other skills), landing at scripts/ora_doc_qc.py inside the packaged .skill so
this skill installs and runs standalone. In a raw repo/worktree checkout
(where nothing has been packaged yet), the sys.path shim below falls back to
the repo-root tools/ directory so `python pma-qc/scripts/pma_qc.py ...` still
works for local development.
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
# ora_doc_qc there (`.../ora-skills/pma-qc/scripts/` -> parent.parent.parent
# -> `.../ora-skills/tools/`). Verified 2026-08-17 against both a raw
# worktree checkout and a real extracted .skill (see task-4-fix-report.md).
sys.path.append(str(Path(__file__).resolve().parent.parent.parent / 'tools'))

from ora_doc_qc import new_registry, has, quote, run_cli

check, CHECKS = new_registry()

# ---- BLOCK -----------------------------------------------------------------


@check("P1", "BLOCK", "Manager may execute leases in Owner's name", "PM-9")
def _p1(ctx):
    grant = has(ctx, r"sign,?\s*renew\s*and/?or\s*cancel|execute\s+(any\s+)?leases?"
                     r"|to\s+sign[^.]{0,60}leases?")
    guard = has(ctx, r"shall not have the authority to execute"
                     r"|no authority to (sign|execute)[^.]{0,60}lease")
    if grant and not guard:
        return ("Agent holds authority to execute leases for Owner and the SP-9 "
                "negative covenant is absent. " + quote(ctx, r"sign,?\s*renew"))
    return None


@check("P2", "BLOCK", "Owner indemnity reaches the manager's own negligence", "PM-6")
def _p2(ctx):
    indem = has(ctx, r"sav\w*\s+the\s+Agent\s+harm\w+"
                     r"|hold\w*\s+(the\s+)?Agent\s+harm\w+"
                     r"|indemnif\w+\s+(the\s+)?Agent")
    carve = has(ctx, r"shall not extend to any claim arising from Agent'?s negligence"
                     r"|except (to the extent )?(of|caused by) Agent'?s negligen")
    reciprocal = has(ctx, r"Agent shall indemnif\w+ (and hold )?Owner")
    if indem and not carve:
        d = "Owner indemnifies Agent with no carve-out for Agent's negligence."
        if has(ctx, r"willful misconduct or \w+ negligence"):
            d += (" Compounded by an exculpation limiting Agent liability to "
                  "willful misconduct or gross negligence - amend both together.")
        if not reciprocal:
            d += " No reciprocal Agent indemnity."
        return d
    return None


@check("P3", "BLOCK", "Exclusive grant with no per-property or service-line carve-out",
       "PM-1")
def _p3(ctx):
    excl = has(ctx, r"appoints? the Agent exclusively|exclusive(ly)? to (rent|lease|manage)"
                    r"|exclusive right to (manage|lease and manage)")
    sever = has(ctx, r"terminate as to (that|such) property only"
                     r"|remove any property from Exhibit|separate grant"
                     r"|property by property")
    if excl and not sever:
        return ("Exclusivity attaches to every service line across the whole "
                "property schedule with no severability. Removing leasing at one "
                "building, or one property on a sale, requires terminating the "
                "entire agreement. " + quote(ctx, r"exclusiv\w+"))
    return None


@check("P3b", "HIGH", "Leasing and management granted as a single indivisible appointment",
       "PM-1")
def _p3b(ctx):
    combined = has(ctx, r"to (rent|lease)[^.]{0,40}(operate and manage|and manage)")
    sever = has(ctx, r"separate grant|appointment as leasing agent is")
    if combined and not sever:
        return ("Leasing and management are one grant. State them as separate "
                "appointments so leasing can move without disturbing management.")
    return None


@check("P4", "BLOCK", "Leasing commission base undefined or uncapped", "PM-11")
def _p4(ctx):
    fee = has(ctx, r"for leasing[:,]|leasing commission|percent of gross lease value")
    defined = has(ctx, r"'?Gross Lease Value'? means|aggregate base rent payable over")
    if fee and not defined:
        d = "Leasing fee charged on an undefined base. "
        if has(ctx, r"gross lease value"):
            d += ("'Gross lease value' is used without definition - no exclusion "
                  "of option/renewal/expansion terms, no present-value convention, "
                  "no treatment of abated rent or TI allowance. ")
        if not has(ctx, r"refund a pro rata portion|clawback"):
            d += "No clawback on early tenant default. "
        if not has(ctx, r"half (up)?on (full )?execution|upon rent commencement"):
            d += "No payment timing stated."
        return d
    return None


@check("P5", "BLOCK", "Unfilled tokens in a non-template document", "PM-18")
def _p5(ctx):
    if ctx["is_template"] or ctx["allow_tokens"]:
        return None
    toks = re.findall(r"\[[A-Z][A-Z0-9 _/-]{2,40}\]", ctx["raw"])
    if toks:
        u = sorted(set(toks))[:8]
        return f"{len(toks)} unfilled token(s): {', '.join(u)}"
    return None


@check("P6", "BLOCK", "Manager may sue, settle, and release claims in Owner's name",
       "PM-10")
def _p6(ctx):
    grant = has(ctx, r"institute and prosecute|sue for in the name of the Owner"
                     r"|settle,? compromise,? and release")
    guard = has(ctx, r"without Owner'?s prior written approval"
                     r"|Owner shall select counsel")
    if grant and not guard:
        return ("Unilateral authority to commence, settle, compromise, and "
                "release actions in Owner's name - including releasing a claim "
                "Owner would have pursued. No approval threshold, no counsel "
                "selection right, no cost cap.")
    return None


# ---- HIGH ------------------------------------------------------------------

@check("P7", "HIGH", "Automatic renewal with no notice or review trigger", "PM-2")
def _p7(ctx):
    auto = has(ctx, r"automatical\w*\s+rene\w+|shall (automatically )?continue"
                    r"|rene\w+ for (successive )?annual")
    affirm = has(ctx, r"may be extended[^.]{0,60}by written agreement")
    review = has(ctx, r"ninety \(90\) days before each anniversary"
                      r"|written summary of fees charged")
    if auto and not (affirm or review):
        return ("Renews annually with no notice requirement and no anniversary "
                "review. Rates and thresholds never get re-examined.")
    return None


@check("P8", "HIGH", "Owner deficit funding: default interest, no notice, cure, or cap",
       "PM-4")
def _p8(ctx):
    m = re.search(r"(\d+(?:\.\d+)?)\s*%\s*of (the )?total outstanding balance each month"
                  r"|charging\s*(\d+(?:\.\d+)?)\s*%", ctx["t"], re.I)
    deficit = has(ctx, r"expenses are greater than receipts|Owner agrees to pay such excess")
    if deficit and m:
        rate = m.group(1) or m.group(3)
        try:
            eff = ((1 + float(rate) / 100) ** 12 - 1) * 100
            eff_s = f" ({eff:.2f}% effective annual if compounding)"
        except Exception:                                          # noqa: BLE001
            eff_s = ""
        d = f"Default interest of {rate}% per month{eff_s}."
        if not has(ctx, r"non-?compounding|simple interest"):
            d += " Not stated as simple/non-compounding."
        if not has(ctx, r"cure|second written notice"):
            d += " No notice or cure period."
        if not has(ctx, r"maximum rate permitted by law"):
            d += " No usury savings clause."
        if not has(ctx, r"Agent shall remit net proceeds"):
            d += " No reciprocal deadline for Agent to remit Owner's net proceeds."
        return d
    if deficit and not has(ctx, r"within fifteen \(15\) days after receipt"):
        return "Owner deficit funding obligation with no notice-and-cure mechanic."
    return None


@check("P9", "HIGH", "Manager retains interest earned on Owner's funds", "PM-5")
def _p9(ctx):
    if has(ctx, r"interest earned shall be kept by the Agent"
                r"|any such interest[^.]{0,40}Agent"):
        return ("Interest on Owner's money accrues to the manager. Unpriced fee "
                "on Owner's float. " + quote(ctx, r"interest earned"))
    if has(ctx, r"trust account|funds collected") and not has(
            ctx, r"interest[^.]{0,60}(accrue to Owner|credited against fees)"):
        return "Trust account provisions silent on who receives interest."
    return None


@check("P10", "HIGH", "Management fee base undefined", "PM-3")
def _p10(ctx):
    fee = has(ctx, r"percent of gross monies collected|of gross (monies|receipts|collections)"
                   r"|for management[:,]")
    defined = has(ctx, r"'?Gross Monies Collected'? means|means base rent, percentage rent")
    if fee and not defined:
        return ("Management fee charged on an undefined base. As written it "
                "reaches security deposits, insurance and condemnation proceeds, "
                "sale and financing proceeds, TI allowances, capital "
                "contributions, and tax-appeal refunds.")
    return None


@check("P11", "HIGH", "Capital-project fee uncapped and loosely triggered", "PM-12")
def _p11(ctx):
    if has(ctx, r"modernization|capital improvement|construction supervision"):
        d = ""
        if has(ctx, r"match the Management fee percentage|matches the management fee"):
            d += ("Construction supervision fee set at the management rate - a "
                  "second percentage on money that is not operating revenue. ")
        if has(ctx, r"required to spend extra time"):
            d += "Triggered by the undefined standard of 'extra time'. "
        if not has(ctx, r"shall not exceed[^.]{0,40}of hard costs"):
            d += "No cap on hard costs and no de minimis project floor."
        return d or None
    return None


@check("P12", "HIGH", "Casualty fee stacks on the management and supervision fees",
       "PM-13")
def _p12(ctx):
    m = re.search(r"\((\d+)\s*%?\s*[\)\}\]]?\s*percent of gross billings",
                  ctx["t"], re.I)
    if has(ctx, r"fire/?\s*flood|casualty|gross billings to be collected from insurer"):
        if not has(ctx, r"sole compensation payable to Agent in connection with a casualty"
                        r"|credited against any construction supervision fee"):
            pct = (m.group(1) + "%") if m else "the stated"
            return (f"Casualty fee of {pct} of insurer billings with no offset. "
                    "Sits on top of the construction supervision fee for the same "
                    "physical work, and - because the management fee base is "
                    "undefined - arguably on top of the management fee as well. "
                    "One casualty, three fees.")
    return None


@check("P13", "HIGH", "Owner assumes manager-signed service contracts, unscheduled",
       "PM-15")
def _p13(ctx):
    if has(ctx, r"Owner to assume the obligation of any contract"
                r"|Owner shall assume[^.]{0,40}contract"):
        if not has(ctx, r"schedule delivered to and approved by Owner"
                        r"|terminable on sixty \(60\) days"):
            return ("Owner assumes every service contract the manager signed, at "
                    "termination, with no schedule, no advance approval, and no "
                    "requirement that they be terminable. Demand the schedule "
                    "before terminating, not after.")
    return None


@check("P14", "HIGH", "No post-termination turnover obligations", "PM-15")
def _p14(ctx):
    if not has(ctx, r"deliver to Owner[^.]{0,120}(tenant files|security deposits|final accounting)"
                    r"|within fifteen \(15\) days after termination"):
        return ("Manager owes nothing on the way out: no delivery of leases, "
                "tenant files, security deposits, funds, final accounting, keys, "
                "plans, or warranties. Also no for-cause immediate termination "
                "right for fraud, misapplication of funds, or lapsed bond.")
    return None


@check("P15", "HIGH", "Manager may assign; no change-of-control termination", "PM-16")
def _p15(ctx):
    binds = has(ctx, r"successors and assigns of the Agent")
    guard = has(ctx, r"Agent may not assign|without Owner'?s prior written consent"
                     r"|shall constitute an assignment")
    if binds and not guard:
        return ("Agreement runs to the Agent's assigns with no consent "
                "requirement. Owner engaged a specific operator and can be "
                "delivered its acquirer.")
    return None


@check("P16", "HIGH", "No Owner audit or books-and-records inspection right", "PM-7")
def _p16(ctx):
    if not has(ctx, r"inspect and audit|books and records[^.]{0,60}(inspect|audit)"
                    r"|right to audit"):
        return ("Monthly statements with no right to inspect the underlying "
                "books, no retention period, no stated basis of accounting, and "
                "no audit-cost shifting on a material overcharge.")
    return None


@check("P17", "HIGH", "No manager professional liability (E&O) requirement", "PM-8")
def _p17(ctx):
    if not has(ctx, r"errors and omissions|professional liability"):
        d = "Manager carries no E&O requirement. "
        if has(ctx, r"naming Agent as co-?insured|Agent as co-?insured"):
            d += ("Owner is required to name the manager as co-insured on Owner's "
                  "own liability policy with nothing reciprocal.")
        return d
    return None


@check("P18", "HIGH", "Owner named as an individual, not the title-holding entity",
       "PM-17")
def _p18(ctx):
    m = re.search(r"hereinafter called\s*[\"']?\s*Owner", ctx["t"], re.I)
    if not m:
        return ("Could not locate the Owner designation - verify the preamble "
                "by hand.")
    window = ctx["t"][max(0, m.start() - 60):m.start()]
    words = [w for w in window.split() if w.strip("-–—.,")]
    if not words:
        return "Owner designation is blank in the preamble."
    # An entity name ENDS with its designator. Test the final token only -
    # testing a window catches an unrelated 'Inc' earlier in the caption.
    last = words[-1].strip(".,;:\"'").upper()
    if last in ("LLC", "L.L.C.", "LLP", "LP", "L.P.", "INC", "CORP",
                "CORPORATION", "COMPANY", "CO", "TRUST", "LTD", "PARTNERSHIP",
                "ASSOCIATION", "LLC.", "INCORPORATED"):
        return None
    shown = " ".join(words[-3:])
    return (f"Owner designated as '{shown}' - the name does not end in an "
            "entity designator, so it reads as an individual. Verify against "
            "the county owner-of-record string per property and conform by "
            "amendment. Do not rely on the mismatch as a defense: accepted "
            "services and paid fees support ratification.")


@check("P19", "HIGH", "Termination turns on a written notice with no notice provision",
       "PM-14")
def _p19(ctx):
    term = has(ctx, r"terminate this agreement with[^.]{0,30}written notice"
                    r"|written notice[^.]{0,40}terminate")
    addr = has(ctx, r"[Nn]otices? (shall be|to be) (given|delivered|sent)"
                    r"|addressed as follows|Notices:")
    if term and not addr:
        return ("The only exit is a written notice, to an address the agreement "
                "never specifies, by a method it never specifies, effective on a "
                "date it never defines.")
    return None


@check("P20", "HIGH", "Manager may engage an outside leasing broker at Owner's expense",
       "PM-11")
def _p20(ctx):
    if has(ctx, r"utilize a leasing agent|engage (an|a) (outside|cooperating) broker"):
        if not has(ctx, r"compensated from Agent'?s fee"
                        r"|shall not increase the aggregate leasing commission"):
            return ("Manager may bring in an outside leasing broker with the cost "
                    "falling on Owner and no offset against the manager's own "
                    "leasing fee.")
    return None


# ---- MED -------------------------------------------------------------------

@check("P21", "MED", "Expenditure approval threshold stale, uncapped, no emergency test",
       "PM-4")
def _p21(ctx):
    m = re.search(r"expenditures? in excess of \$([\d,]+)", ctx["t"], re.I)
    if m:
        d = f"Per-item approval threshold ${m.group(1)}."
        if not has(ctx, r"in the aggregate in any calendar year|aggregate annual"):
            d += " No aggregate annual cap."
        if not has(ctx, r"imminent injury to persons|emergency expenditure"):
            d += " Emergency exception undefined."
        d += " Escalate or index at each renewal."
        return d
    if has(ctx, r"repairs and alterations") and not has(ctx, r"prior (written )?approval"):
        return "Repair and alteration authority with no stated approval threshold."
    return None


@check("P22", "MED", "Fidelity bond fixed, with no delivery obligation", "PM-8")
def _p22(ctx):
    m = re.search(r"fidelity bond in the amount of \$([\d,]+)", ctx["t"], re.I)
    if m:
        if not has(ctx, r"deliver certificates|certificate of[^.]{0,30}bond"):
            return (f"${m.group(1)} fidelity bond with no obligation to evidence "
                    "it, ever. Scale the amount to the largest monthly collection "
                    "the manager holds and require an annual certificate.")
    elif not has(ctx, r"fidelity bond|employee dishonesty"):
        return "No fidelity bond required on employees handling Owner's funds."
    return None


@check("P23", "MED", "Funds not segregated; bank-failure risk pre-allocated to Owner",
       "PM-5")
def _p23(ctx):
    d = ""
    if not has(ctx, r"segregated (trust )?account|shall not be commingled"):
        d += "No segregated, non-commingled trust account per Owner. "
    if has(ctx, r"not be held liable in the event of bankruptcy|failure of such institution"):
        d += ("Agent pre-exculpated for bank failure while choosing the "
              "institution and with no FDIC-limit obligation.")
    return d or None


@check("P24", "MED", "No operating budget, variance reporting, or performance standard",
       "PM-7")
def _p24(ctx):
    if not has(ctx, r"annual operating budget|variance report"):
        d = "No annual operating budget or variance reporting. "
        if has(ctx, r"use diligence in the [Mm]anagement"):
            d += ("Standard of performance is 'diligence' with no metric, no "
                  "reporting SLA, and no leasing activity report.")
        return d
    return None


@check("P25", "MED", "No affiliate-vendor disclosure or anti-markup covenant", "PM-12")
def _p25(ctx):
    if not has(ctx, r"disclose in writing any interest[^.]{0,60}(contractor|vendor)"
                    r"|without markup|at actual cost"):
        return ("Nothing requires the manager to disclose an interest in a "
                "contractor or vendor, and nothing prohibits a markup or rebate "
                "on subcontracted work.")
    return None


@check("P26", "MED", "Hourly rates never escalated and uncapped", "PM-13")
def _p26(ctx):
    rates = re.findall(r"\$(\d{2,3})\s*per hour", ctx["t"], re.I)
    if rates:
        d = f"Hourly rate(s): {', '.join('$' + r for r in sorted(set(rates)))}. "
        d += "No annual aggregate cap and no index. "
        if has(ctx, r"if [A-Z]{2,4} is not the listing agent|not the listing agent"):
            d += ("The sale-support charge applies only when Owner uses a "
                  "different listing broker - a soft exclusivity provision "
                  "sitting in the fee schedule.")
        return d
    return None


@check("P27", "MED", "No governing law, venue, attorney fees, or jury waiver", "PM-14")
def _p27(ctx):
    missing = []
    if not has(ctx, r"governed by the laws|governing law"):
        missing.append("governing law")
    if not has(ctx, r"\bvenue\b|exclusive jurisdiction"):
        missing.append("venue")
    if not has(ctx, r"prevailing party|attorneys?'? fees"):
        missing.append("attorney fees")
    if not has(ctx, r"waive[sd]? (any )?(right to )?(a )?trial by jury|jury waiver"):
        missing.append("jury waiver")
    if missing:
        return "Absent: " + ", ".join(missing) + "."
    return None


@check("P28", "MED", "No confidentiality covenant", "PM-18")
def _p28(ctx):
    if not has(ctx, r"confidential"):
        return ("Manager holds the rent roll, tenant financials, and lease terms "
                "with no confidentiality obligation.")
    return None


@check("P29", "MED", "No express covenant that no commission tail survives termination",
       "PM-11")
def _p29(ctx):
    if not has(ctx, r"[Nn]o commission shall be payable with respect to any lease "
                    r"executed after|no (post-?termination )?tail"):
        if has(ctx, r"leasing|commission"):
            return ("The agreement is silent on post-termination commissions. "
                    "Silence currently favors Owner - convert it to an express "
                    "covenant so it cannot later be argued in.")
    return None


@check("P30", "MED", "Property schedule lacks parcel IDs, SF, and per-property entity",
       "PM-17")
def _p30(ctx):
    if has(ctx, r"Exhibit A|List of properties|see Exhibit"):
        if not has(ctx, r"parcel (id|number)|APN|auditor'?s parcel"):
            return ("Exhibit A is an address list. It must carry parcel ID(s), "
                    "building SF, the owning entity as the county renders it, and "
                    "the service lines engaged per property.")
    return None


@check("P32", "BLOCK", "Manager may contract capital or vendor work in its own name",
       "PM-19")
def _p32(ctx):
    auth = has(ctx, r"(make|cause to be made|contract for|order)[^.]{0,80}"
                    r"(repairs|alterations|improvements|capital)"
                    r"|hire[^.]{0,40}(contractors?|vendors?)"
                    r"|enter into (service|vendor|maintenance) (contracts?|agreements?)"
                    r"|purchase (supplies|materials)")
    agency = has(ctx, r"in (the name of|owner'?s name)[^.]{0,60}(owner|as agent)"
                      r"|as (a )?disclosed agent|for and on behalf of owner"
                      r"|shall name owner as the contracting part"
                      r"|owner shall be the contracting party")
    if auth and not agency:
        return ("The manager may procure repairs, capital work and vendor services "
                "with no requirement that it contract as Owner's disclosed agent or "
                "name the Owner entity as the contracting party. It will therefore "
                "sign trade paper in its own name, and every warranty, indemnity and "
                "payment remedy in that paper will run to the manager rather than to "
                "the ORA entity that owns the asset and funds the work - a defect that "
                "survives the manager's own turnover. Observed live: a Q3 2026 paving "
                "proposal for an ORA-owned asset named the manager as Purchaser under "
                "a form barring any non-party from claiming a remedy. Require that "
                "every trade contract name the Owner entity as the contracting party, "
                "with the manager signing as disclosed agent. Route the trade paper "
                "itself to `vendor-contract-qc` (VC-1). " + quote(ctx, r"repairs"))
    return None


@check("P33", "HIGH", "No dollar threshold requiring Owner countersignature on capital work",
       "PM-19")
def _p33(ctx):
    auth = has(ctx, r"(make|cause to be made|contract for)[^.]{0,80}"
                    r"(repairs|alterations|improvements|capital)"
                    r"|expenditure|purchase (supplies|materials)")
    if not auth:
        return None
    thresholds = re.findall(r"\$\s?([\d,]{3,9})(?:\.00)?", ctx["t"])
    approval = has(ctx, r"(prior )?(written )?(approval|consent) of owner"
                        r"|owner'?s (prior )?(written )?(approval|consent)")
    countersign = has(ctx, r"countersign|signed by owner|executed by owner"
                           r"|owner shall execute")
    indexed = has(ctx, r"adjusted annually|CPI|consumer price index|escalat")
    emergency = has(ctx, r"emergenc")
    emergency_bounded = has(ctx, r"emergenc[^.]{0,120}(notify|notice to owner within|"
                                 r"promptly (notify|advise))")
    if not approval:
        return ("Capital and repair authority is granted with no approval threshold at "
                "all. State a dollar figure above which Owner's prior written approval "
                "is required, and above which Owner - not the manager - countersigns "
                "the trade contract.")
    problems = []
    if not countersign:
        problems.append("Approval is required but Owner's countersignature on the "
                        "trade contract is not, so an approved job is still contracted "
                        "on the manager's signature (see P32)")
    if thresholds and not indexed:
        problems.append("The threshold is a fixed figure with no index or periodic "
                        "reset; on an auto-renewing agreement it erodes every year "
                        "against construction cost inflation and silently widens the "
                        "manager's discretionary authority")
    if emergency and not emergency_bounded:
        problems.append("The emergency exception is unbounded - no notice obligation "
                        "to Owner and no dollar ceiling, which swallows the threshold "
                        "whenever the manager characterizes work as urgent")
    if problems:
        return ". ".join(problems) + "."
    return None


# ---- LOW -------------------------------------------------------------------

@check("P31", "LOW", "Signature block omits entity, title, and capacity", "PM-18")
def _p31(ctx):
    if has(ctx, r"Owner Signature|Agent Signature|Owner Name"):
        if not has(ctx, r"\bTitle:|\bIts:|duly authorized"):
            return ("Signature block identifies no entity, no signatory title, "
                    "and no capacity.")
    return None


if __name__ == "__main__":
    run_cli(CHECKS, "ORA property management agreement QC gate",
            ocr_absence_note=("Absence findings (P16, P19, P24, P27-P30, P33) are "
                              "PROVISIONAL - confirm against the page images "
                              "before reporting a missing clause to a "
                              "counterparty."))
