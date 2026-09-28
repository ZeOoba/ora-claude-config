#!/usr/bin/env python3
"""
addendum_qc.py -- QC gate for ORA lease addenda (lease-addendum skill v1.0)

Usage: python3 addendum_qc.py <addendum.docx|pdf> [more ...] [--allow-tokens] [--m3b] [--m4]
                              [--state ST]

Exit 0 = no BLOCK-severity failures across all readable files.
Exit 1 = at least one BLOCK found on a readable file (takes priority over exit 2 even if
         another file in the same run was unreadable -- there is a real, actionable defect).
Exit 2 = a file could not be read to at least 150 words and got no QC result at all.
Severity is BLOCK / HIGH / MED / LOW, same convention as lease-form-qc/scripts/lease_qc.py.

Pattern (zip + regex over word/document.xml, no python-docx dependency for scanning) and the
(id, severity, label, test) check-tuple convention are ported directly from
lease-form-qc/scripts/lease_qc.py -- see that script for the source of the text_of() shape.

--m3b flags this run as a tenant-substitution/novation addendum, which turns on checks 4, 5, 6,
11, 12, 16 (the M3b package) as BLOCK-severity even when the document doesn't self-declare a
substitution (the acceptance-test failure mode this gate exists to catch is exactly a
substitution that was drafted -- and therefore reads -- as if it were a ministerial name change).

WHAT THE ora_doc_qc RETROFIT CHANGED
-------------------------------------
This file's former text_of() was unconditional `zipfile.ZipFile(path)` -- no format branch at
all. A PDF (or any non-.docx path) raised an uncaught zipfile.BadZipFile, crashing the whole run
at exit code 1 -- indistinguishable, at the exit code, from "found a real BLOCK-severity defect".
There was also no word-count floor, so a near-empty .docx ran all 16 checks against a handful of
words instead of being flagged as unreadable. Same root cause as the false-clean/false-BLOCK bugs
ora_doc_qc.py was extracted to fix in pma-qc/listing-agreement-qc/lease-form-qc (no real format
detection before applying a format-specific parser to file bytes), a third failure shape: a hard
crash rather than a false result. extract() now does real format detection, tries pdftotext then
OCR for a PDF, and returns UNREADABLE (exit 2) for anything that will not yield 150 words.
Verified in tests/test_addendum_qc.py against a synthetic no-text-layer PDF fixture and a
near-empty DOCX fixture.

Checks 2 and 3 (the rent-schedule row parser, _rent_rows) read ctx["raw"] -- the shared module's
un-normalized body text -- not ctx["t"]. ora_doc_qc.norm() collapses all whitespace, newlines
included, and _rent_rows() depends on each table cell landing on its own line. ctx["t"] would
silently zero out every parsed row, a silent false-negative in exactly the checks that verify
rent-schedule arithmetic -- the same class of pitfall lease-form-qc's A2 hit with its re.M anchor.
Pinned by tests/test_addendum_qc.py::TestRentTableParity against a frozen copy of the pre-retrofit
line-based parser.

Check 9 (ordinal consistency) previously depended on a `[[CORE_TITLE]] <title>` marker that
text_of() spliced onto the body, then re-parsed back out with a regex -- the same pattern that
caused lease-form-qc's F18 to trip on its own `[[FOOTER]]` marker (this one happened not to
collide with TOKEN_RE, since TOKEN_RE's character class lacks '_', but that was luck, not design).
It now reads a cleanly-extracted `ctx["core_title"]` (via the local _docx_title() helper, mirroring
how ora_doc_qc.extract() already reads dc:creator/Company from the same docProps/core.xml part)
instead of re-parsing a marker out of scanned text. The title text is still appended to ctx["t"]
(unmarked) so check 14's token scan keeps the same coverage of metadata-embedded tokens it had
before.
"""

import json
import os
import re
import sys
import zipfile
from pathlib import Path

# Dev-checkout fallback: Python already puts this script's own directory at sys.path[0] on
# startup, so append (not insert) the repo-root tools/ directory as a lower-priority fallback --
# a packaged .skill ships ora_doc_qc.py alongside this script (via SHARED_ROOT_DEPS), so that
# co-located copy is always tried first; a raw repo/worktree checkout has no such co-located
# copy, so the appended repo-root tools/ path is what resolves ora_doc_qc there. Mirrors
# lease-form-qc/scripts/lease_qc.py's identical shim -- the ora_doc_qc retrofit added the import
# below to this file but omitted the shim its sibling already carries, leaving every invocation
# of this script (and its whole test suite) unable to import ora_doc_qc at all outside a
# packaged .skill.
sys.path.append(str(Path(__file__).resolve().parent.parent.parent / 'tools'))

from ora_doc_qc import DEFAULT_MIN_WORDS, SEV_ORDER, extract, norm, run_checks

TOKEN_RE = re.compile(r"\[[A-Z][A-Z0-9 /,.'&-]{2,}\]")
Q = '["“”‘’«»]'

MONEY_RE = re.compile(r"\$[\d,]+\.\d{2}")
DATE_RE = re.compile(
    r"(January|February|March|April|May|June|July|August|September|October|November|December)"
    r"\s+\d{1,2},\s*(\d{4})"
)
BINDING_PHRASES = (
    "in accordance with the following schedule",
    "in accordance with the schedule below",
    "in accordance with the schedule set forth",
    "as set forth in the rent schedule",
)


def load_state_overlay():
    ref = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "references", "state-overlay.json")
    if not os.path.exists(ref):
        return {}
    with open(ref, encoding="utf-8") as f:
        return json.load(f)


def _docx_title(path):
    """dc:title from docProps/core.xml, "" if the part or the tag is absent.
    Mirrors how ora_doc_qc.extract() already reads dc:creator/Company from the
    same part -- see the module docstring for why this replaced the old
    [[CORE_TITLE]] marker-splice-and-re-parse."""
    try:
        with zipfile.ZipFile(path) as z:
            if "docProps/core.xml" not in z.namelist():
                return ""
            core_xml = z.read("docProps/core.xml").decode("utf-8", "replace")
    except (zipfile.BadZipFile, KeyError, OSError):
        return ""
    m = re.search(r"<dc:title>(.*?)</dc:title>", core_xml, re.S)
    return re.sub(r"<[^>]+>", "", m.group(1)).strip() if m else ""


def _defined(t, term):
    return bool(re.search(Q + r"\s*" + re.escape(term) + r"\s*" + Q + r"\s*(shall\s+)?means?\b", t))


def _has_signature_block_for(t, name_fragment):
    """Crude but conservative: a signature block exists for a party if its name appears
    within 200 chars of a 'By:' / 'Its:' / signature-line marker."""
    idx = t.find(name_fragment)
    if idx < 0:
        return False
    window = t[max(0, idx - 200): idx + 200]
    return bool(re.search(r"\bBy:|\bIts:|_{5,}|Signature", window))


PERIOD_LINE_RE = re.compile(r"^\s*\d{1,2}[/-]\d{4}\s*[-–]\s*\d{1,2}[/-]\d{4}\s*$")


def _rent_rows(t):
    """Extract rent-schedule table rows using <w:tc> cell boundaries (each cell lands on its own
    line after text_of()'s tc-split). A row is a period-range cell followed within 4 cells by
    exactly two money cells -- column order (monthly-first vs annual-first) varies across ORA's
    own template family, so this does NOT assume an order; returns (smaller, larger) pairs and
    lets the caller decide which should be 1/12 of the other. Prose sentences (which don't sit on
    a table-cell line by themselves) are excluded by construction."""
    lines = [ln.strip() for ln in t.splitlines()]
    rows = []
    i = 0
    while i < len(lines):
        if PERIOD_LINE_RE.match(lines[i]):
            amounts = []
            for j in range(i + 1, min(i + 5, len(lines))):
                if MONEY_RE.fullmatch(lines[j]):
                    amounts.append(float(lines[j].replace("$", "").replace(",", "")))
                elif amounts or PERIOD_LINE_RE.match(lines[j]):
                    break
            if len(amounts) >= 2:
                rows.append((min(amounts[:2]), max(amounts[:2])))
        i += 1
    return rows


def check_circular_effective_date(t):
    return bool(re.search(r"on or before\s+the\s+(date|Effective Date)\s+of\s+(execution|this Addendum)", t, re.I))


def check_rent_row_no_clause(t):
    """A rent-schedule table exists (>=2 money-pair rows, or a 'RENT SCHEDULE' header) but the
    operative Base Rent paragraph never binds to it with a phrase like 'in accordance with the
    following schedule' -- meaning any stub/interim row in the table has no operative clause
    obligating payment of it."""
    has_table = len(_rent_rows(t)) >= 2 or "rent schedule" in t.lower()
    if not has_table:
        return False
    return not any(p in t.lower() for p in BINDING_PHRASES)


ESCALATION_RATE_RE = re.compile(
    r"(?:escalat\w*|increas\w*)[^.]{0,60}?(\d{1,2}(?:\.\d+)?)\s*%", re.I)


def _rent_schedule_window(t):
    """Character span anchored on the same binding-phrase/'rent schedule' text that
    check_rent_row_no_clause's has_table heuristic uses, extended generously to cover the
    operative clause and the table itself. None if no such anchor exists.

    Scoping the escalation-rate search to this window -- rather than the whole document,
    ctx["raw"] -- keeps an unrelated clause elsewhere (e.g. "Tenant's share of Operating
    Expenses shall increase 5% annually") from being picked up as the RENT escalation rate.
    """
    lower = t.lower()
    positions = [lower.find(p) for p in BINDING_PHRASES if p in lower]
    pos = min(positions) if positions else lower.find("rent schedule")
    if pos < 0:
        return None
    # Backward margin stays SHORT (a short same-sentence lead-in like "escalating at 3%
    # annually, Base Rent shall be payable in accordance..." -- a few dozen chars) rather
    # than wide enough to reach into an entirely separate, unrelated preceding clause/
    # paragraph.
    return max(0, pos - 50), min(len(t), pos + 2000)


def check_rent_arithmetic(t):
    """Table rows only (see _rent_rows) -- order-agnostic: the larger of each row's two amounts
    should be ~12x the smaller (annual = monthly * 12), regardless of which column is which).
    Also checks year-over-year escalation when the operative clause states a rate: each row's
    annual amount should compound onto the prior row's by (1 + rate). Returns a distinguishing
    string (not a generic True) rather than PASS (False) when a rent schedule is clearly present
    (check_rent_row_no_clause's has_table heuristic) but no rows parsed cleanly -- "nothing wrong
    found" and "could not check" must never read identically (verified-null-vs-inferred-null)."""
    rows = _rent_rows(t)
    has_table = len(rows) >= 2 or "rent schedule" in t.lower()
    if not rows:
        if has_table:
            return ("rent schedule detected but no rows parsed cleanly -- compounding could NOT "
                    "be verified (not a clean pass); confirm the table format manually")
        return False

    for smaller, larger in rows:
        if smaller > 0 and abs(smaller * 12 - larger) > 1.00:
            return True

    window = _rent_schedule_window(t)
    rate_match = ESCALATION_RATE_RE.search(t[window[0]:window[1]]) if window else None
    if rate_match and len(rows) >= 2:
        rate = float(rate_match.group(1)) / 100
        # larger of each pair is the annual figure (order-agnostic, same as the pair above).
        annuals = [larger for _smaller, larger in rows]
        for i in range(1, len(annuals)):
            expected = annuals[i - 1] * (1 + rate)
            if abs(annuals[i] - expected) > max(1.00, expected * 0.005):
                return (f"row {i + 1} annual rent {annuals[i]:.2f} does not compound onto row {i} "
                        f"({annuals[i - 1]:.2f}) at the stated {rate * 100:.2f}% escalation "
                        f"(expected {expected:.2f})")
    return False


def check_party_consent(t, m3b):
    if not m3b:
        return False
    outgoing = re.findall(r"Tenant\s+shall\s+be\s+([^,\.]+),?\s+d/?b/?a", t, re.I)
    if not outgoing:
        return False
    # Use the PARSED outgoing-party name(s), not a hardcoded literal -- an earlier version
    # tested the fixture name "MLC" specifically, which meant every real substitution (any
    # party name other than "MLC") always found no signature block and was always flagged
    # BLOCK regardless of whether a genuine consent/signature block was present.
    #
    # all(), not any(): a multi-tenant/co-tenant substitution can release MORE THAN ONE
    # outgoing party in the same instrument. any() would clear (no BLOCK) the moment ONE
    # of them has a discoverable signature block, silently missing that a second released
    # party's consent is unconfirmed -- consent completeness means EVERY named outgoing
    # party must have one, not just one of them.
    return (not all(_has_signature_block_for(t, n.strip()) for n in outgoing)
            and not re.search(r"consent(s)?\s+to\s+(this\s+)?release", t, re.I))


def check_security_deposit(t, m3b):
    if not m3b:
        return False
    return "security deposit" not in t.lower()


def check_entity_dropped(t, m3b):
    if not m3b:
        return False
    return not re.search(r"\brelease(d|s)?\b.{0,80}\bTenant\b|\bassum(e|ption|es)\b.{0,80}\bobligations\b", t, re.I | re.S)


def check_term_vs_recordation(t, overlay, state):
    """Extract the earliest 'dated <date>' (Prime Lease commencement proxy) and the latest year
    referenced anywhere in the document (new expiration proxy), and flag if the cumulative span
    exceeds the state's recordation/acknowledgment threshold. Coarse (year-granularity) by
    design -- this is a QC flag to trigger human/counsel review, not a legal conclusion."""
    if not state or state not in overlay:
        return False
    threshold = overlay[state].get("threshold_years")
    if threshold is None:
        return False
    dates = DATE_RE.findall(t)
    if not dates:
        return False
    years = [int(y) for _, y in dates]
    commencement_match = re.search(r"dated\s+\w+\s+\d{1,2},\s*(\d{4})", t, re.I)
    start_year = int(commencement_match.group(1)) if commencement_match else min(years)
    end_year = max(years)
    return (end_year - start_year) > threshold


def check_ratification(t):
    return "all other terms of the prime lease will remain in effect" not in t.lower() and \
           "remain in full force and effect" not in t.lower()


def check_ordinal(t, core_title):
    body_ord = re.search(r"\b(First|Second|Third|Fourth|Fifth|Sixth|Seventh|Eighth|Ninth|Tenth)\b\s+Addendum", t, re.I)
    title_ord = re.search(r"\b(First|Second|Third|Fourth|Fifth|Sixth|Seventh|Eighth|Ninth|Tenth)\b\s+Addendum", core_title, re.I) if core_title else None
    if core_title and body_ord and title_ord:
        return body_ord.group(1).lower() != title_ord.group(1).lower()
    return False


def check_defined_terms(t):
    if "Demised Premises" in t and not _defined(t, "Demised Premises") and '"Premises"' in t:
        return True
    return False


def check_insurance(t, m3b):
    if not m3b:
        return False
    return "insurance" not in t.lower()


def check_notice_address(t, party_changed):
    if not party_changed:
        return False
    return "notice" not in t.lower() and "address" not in t.lower()


def check_counterparts(t):
    return "counterpart" not in t.lower()


FORMATTING_MARKERS = ("[SIGNATURE PAGE TO FOLLOW]",)


def check_unfilled_token(t, allow_tokens):
    """Flags an unfilled [TOKEN] placeholder. Intentional formatting cues (the signature-page
    marker) are not drafting tokens and must not trip this check -- exempted explicitly rather
    than by loosening TOKEN_RE, so a real [TENANT NAME]-style placeholder still fires."""
    if allow_tokens:
        return False
    for m in TOKEN_RE.finditer(t):
        if m.group(0) not in FORMATTING_MARKERS:
            return True
    return False


def check_premises_pro_rata(t, m4):
    if not m4:
        return False
    return "pro rata" not in t.lower() and "pro-rata" not in t.lower() and "proportionate share" not in t.lower()


def check_guaranty_attached(t, m3b):
    if not m3b:
        return False
    return "guaranty" not in t.lower()


# (id, severity, title, position, fn(ctx)) -- fn returns None to PASS, True to
# FAIL with the title as the detail (run_checks() sugar, see ora_doc_qc.py).
# Most checks are parameterized by CLI flags (m3b/m4/state/overlay) in addition
# to text, so unlike lease_qc.py's mostly-uniform bool_check() port, these stay
# direct ctx-aware closures over the original check_*() bodies (unchanged).
# Checks 2/3 read ctx["raw"] (not ctx["t"]) -- see the module docstring.
CHECKS = [
    ("1", "HIGH", "Circular effective date", None,
     lambda ctx: True if check_circular_effective_date(ctx["t"]) else None),
    ("2", "HIGH", "Rent-table row with no operative clause", None,
     lambda ctx: True if check_rent_row_no_clause(ctx["raw"]) else None),
    ("3", "HIGH", "Rent arithmetic / compounding verified", None,
     lambda ctx: check_rent_arithmetic(ctx["raw"]) or None),
    ("4", "BLOCK", "Party-consent completeness (M3b)", None,
     lambda ctx: True if check_party_consent(ctx["t"], ctx["m3b"]) else None),
    ("5", "BLOCK", "Security deposit disposition stated (M3b)", None,
     lambda ctx: True if check_security_deposit(ctx["t"], ctx["m3b"]) else None),
    ("6", "BLOCK", "Entity dropped/added without release or joinder (M3b)", None,
     lambda ctx: True if check_entity_dropped(ctx["t"], ctx["m3b"]) else None),
    ("7", "HIGH", "Cumulative term vs. state recordation threshold", None,
     lambda ctx: True if check_term_vs_recordation(ctx["t"], ctx["overlay"], ctx["state"]) else None),
    ("8", "BLOCK", "Ratification / conflict-control clause present", None,
     lambda ctx: True if check_ratification(ctx["t"]) else None),
    ("9", "MED", "Ordinal consistent: body title vs. document metadata Title", None,
     lambda ctx: True if check_ordinal(ctx["t"], ctx["core_title"]) else None),
    ("10", "MED", "Defined terms match the Prime Lease", None,
     lambda ctx: True if check_defined_terms(ctx["t"]) else None),
    ("11", "BLOCK", "Insurance condition on tenant change (M3b)", None,
     lambda ctx: True if check_insurance(ctx["t"], ctx["m3b"]) else None),
    ("12", "BLOCK", "Notice addresses present where a party changed", None,
     lambda ctx: True if check_notice_address(ctx["t"], ctx["m3b"] or ctx["m4"]) else None),
    ("13", "MED", "Counterparts / e-signature clause", None,
     lambda ctx: True if check_counterparts(ctx["t"]) else None),
    ("14", "BLOCK", "Unfilled [TOKEN] on non-template file", None,
     lambda ctx: True if check_unfilled_token(ctx["t"], ctx["allow_tokens"]) else None),
    ("15", "HIGH", "Premises change without recomputed pro-rata share (M4)", None,
     lambda ctx: True if check_premises_pro_rata(ctx["t"], ctx["m4"]) else None),
    ("16", "BLOCK", "Guaranty attached where M3b applies", None,
     lambda ctx: True if check_guaranty_attached(ctx["t"], ctx["m3b"]) else None),
]


def scan(path, m3b=False, m4=False, allow_tokens=False, state=None, overlay=None):
    """Returns "unreadable", True (a BLOCK fired), or False (readable, no BLOCK).
    Always prints a report line to stdout for the file, same as before."""
    print(f"\n{path}")
    if not os.path.exists(path):
        print("  ERROR: no such file")
        return "unreadable"
    try:
        body, meta = extract(path, min_words=DEFAULT_MIN_WORDS)
    except Exception as e:                                         # noqa: BLE001
        print(f"  ERROR: extraction failed: {e}")
        return "unreadable"

    if body is None:
        print(f"  UNREADABLE - {meta['words']} words extracted ({meta['format']}, "
              f"extraction={meta['extraction']}); no QC result. Install "
              "poppler-utils + tesseract, or supply a text-layer copy.")
        return "unreadable"

    core_title = _docx_title(path) if meta["format"] == "docx" else ""
    is_template = "TEMPLATE" in os.path.basename(path).upper()
    combined = body + (f"\n{core_title}" if core_title else "")
    ctx = {"t": norm(combined), "raw": body, "meta": meta, "core_title": core_title,
           "m3b": m3b, "m4": m4, "state": state, "overlay": overlay or {},
           "allow_tokens": allow_tokens or is_template}

    results = run_checks(ctx, CHECKS)
    results.sort(key=lambda r: (SEV_ORDER[r["severity"]], int(r["id"])))

    if not results:
        print(f"  ---- 0 of {len(CHECKS)} checks failed")
        return False
    for r in results:
        print(f"  [{r['severity']:<5}] {r['id']:<3} FAIL  {r['title']}")
    counts = {s: sum(1 for r in results if r["severity"] == s) for s in SEV_ORDER}
    print(f"  ---- {len(results)} of {len(CHECKS)} checks failed "
          f"(BLOCK {counts.get('BLOCK', 0)} / HIGH {counts.get('HIGH', 0)} / "
          f"MED {counts.get('MED', 0)} / LOW {counts.get('LOW', 0)})")
    return any(r["severity"] == "BLOCK" for r in results)


if __name__ == "__main__":
    args = sys.argv[1:]
    m3b = "--m3b" in args
    m4 = "--m4" in args
    allow = "--allow-tokens" in args
    state = None
    for i, a in enumerate(args):
        if a == "--state" and i + 1 < len(args):
            state = args[i + 1]
    args = [a for a in args if not a.startswith("--") and a != state]
    if not args:
        sys.exit(__doc__)
    overlay = load_state_overlay()
    any_block = False
    any_unreadable = False
    for p in args:
        r = scan(p, m3b=m3b, m4=m4, allow_tokens=allow, state=state, overlay=overlay)
        if r == "unreadable":
            any_unreadable = True
        elif r:
            any_block = True
    if any_block:
        sys.exit(1)
    sys.exit(2 if any_unreadable else 0)
