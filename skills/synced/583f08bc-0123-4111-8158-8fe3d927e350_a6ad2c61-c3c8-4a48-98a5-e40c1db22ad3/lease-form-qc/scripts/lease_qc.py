#!/usr/bin/env python3
"""
lease_qc.py - Oxford Realty Advisors lease-form QC scanner.
Companion to the `lease-form-qc` skill. Scans a lease drafted on ORA paper for
the systemic defect classes documented in that skill.

Usage:
    python3 lease_qc.py <lease.docx|pdf|txt> [more ...] [--allow-tokens]
                        [--no-ocr] [--json]

Exit codes: 0 = all PASS, 1 = one or more FAIL,
            2 = usage / extraction / UNREADABLE error.

Severity: BLOCK (do not execute) / HIGH / MED / LOW.
Checks are written to FAIL on the DEFECT; a check that does not fire means the
protective language was found.

Extraction, the OCR fallback, the UNREADABLE gate, and the report/CLI harness
live in ora_doc_qc.py (shared with pma-qc and listing-agreement-qc).
ora_doc_qc.py itself is NOT vendored inside this skill's scripts/ directory —
it fans out from the repo-root tools/ora_doc_qc.py via package_skills.py's
SHARED_ROOT_DEPS (the same pattern target-markets.json already uses for four
other skills), landing at scripts/ora_doc_qc.py inside the packaged .skill so
this skill installs and runs standalone, mirroring pma-qc and
listing-agreement-qc. In a raw repo/worktree checkout (where nothing has been
packaged yet), the sys.path shim below falls back to the repo-root tools/
directory so `python lease-form-qc/scripts/lease_qc.py ...` still works for
local development.

WHAT THE 2026-08-17 RETROFIT CHANGED
------------------------------------
This file's former text_of() branched on `.docx` and sent everything else -
including PDFs - to open(path, encoding='utf-8', errors='replace').read(),
reading a PDF's binary container as prose. Measured on
tests/no_text_layer_fixture.pdf beforehand: 16 of 51 checks "FAILED", 2 of them
BLOCK, exit 1 - a damning verdict on a document the scanner never read, with
nothing in the output admitting it. That is the same root cause as the
false-clean bug ora_doc_qc.py was extracted to fix, in a different disguise.
extract() now does real format detection, tries pdftotext then OCR, and
returns UNREADABLE (exit 2) for anything that will not yield enough words to
be scanned. Intentional behavior changes, all documented in
tests/test_lease_qc.py:

  * exit 2 is new. There was previously no distinct code for "could not read
    this document"; the whole point of the retrofit is that such a document
    now gets no QC verdict at all instead of a fabricated one.
  * the printed report is ora_doc_qc.print_report()'s fuller
    FILE/EXTRACTION/ENC/RESULT block. Nothing in the repo parses this script's
    stdout - masterlease-revision-cycle and masterlease-jurisdiction-rebase
    gate on the "0 failures" exit code, which is unchanged.
  * T1 is a registered check rather than a finding synthesized inside the old
    scan(), so it participates in --json and the checks_run total (52, not 51).
    It reads BODY + meta["footer"] (see _t1) - the footer half is not optional
    coverage, ORA's own master carries real tokens down there.
  * F18 reads meta["footer"] instead of parsing a '[[FOOTER]]' marker that
    text_of() spliced onto the body. That splice also leaked footer
    boilerplate into every other check's body text; it is gone.

WHY THREE CHECKS ARE NOT bool_check()-WRAPPED
---------------------------------------------
bool_check() feeds a check ctx["t"], which is ora_doc_qc.norm()'d: \\s+
collapsed to single spaces, curly quotes and dashes folded to ASCII, \\xa0
rewritten to a plain space. Three checks test signals norm() destroys, so they
take ctx directly. Each is pinned by a parity test against a frozen copy of
the pre-retrofit logic in tests/test_lease_qc.py.

  A2  anchors with '^' under re.M to prove a section HEADING exists. norm()
      erases every newline, so '^' can only match offset 0 and A2 fires on any
      lease that merely mentions the section. Measured on the real v2.6
      master: old = pass, naively-wrapped = FAIL (HIGH). It reads _linewise().
  F9  tests for '\\xa0' literally. norm() rewrites \\xa0 to a space, so a
      wrapped F9 could never fire again - a silent false negative in a gate
      that exists to catch what silently passes. It reads ctx["raw"].
  F18 needs ctx["meta"], not text at all.

ctx["raw"] is not a second extraction path: ora_doc_qc.scan() populates it
from the same extract() call that produces ctx["t"], and the shared
unfilled_token_check() reads it the same way.

A2b / A3 / A9 DELIBERATELY WIDEN. They match an ASCII '"' character class
against document text. Word emits curly quotes, so pre-retrofit they silently
missed every smart-quoted dead cross-reference; norm() folds the quotes and
they now catch those. That is the check working as written. Neither fires on
the current v2.6 master, so ORA's own paper is unaffected.

TWO ADDITIONS FOR lease-generation's HANDOFF (added post-v2.5.1)
------------------------------------------------------------------
lease-generation's SKILL.md documents two handoffs to this scanner:

  * T2 -- a footer FILENAME/DOCPROPERTY field that resolves to a tenant name
    other than this lease's own defined Tenant, the cross-contamination
    failure mode this skill exists to catch generally (see "Why this
    exists" in SKILL.md), specific to a footer field left over from cloning
    a different tenant's executed lease. Registered in CHECKS like any other
    check; see its own comment block for why it is ctx-aware rather than
    bool_check()-wrapped, and for the real, documented limit on which kind
    of Word field it can see.
  * `--loi-conformance <deal-terms-register.json>` -- a second CLI mode
    (dispatched in main() before CHECKS/run_cli() ever runs) that replays
    lease-generation's own "LOI conformance matrix" gate (SKILL.md "3.
    Gates", item 4) as a scanner-owned, testable CONFORMS / CONFORMS+ /
    PARTIAL / MISSING / CONFLICT matrix instead of a manual judgment call.
    See the "--loi-conformance mode" section near the bottom of this file.

Both are additive: CHECKS keeps every existing entry, ID, and severity
unchanged, and the default (no `--loi-conformance`) CLI behavior is
byte-for-byte the same call into ora_doc_qc.run_cli() as before.
"""

import argparse
import json
import os
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

from ora_doc_qc import bool_check, run_cli, extract, norm

Q = '["“”‘’«»]'


def _defined(t, term):
    """True if `term` is given an operative definition, in any quote style."""
    return bool(re.search(Q + r'\s*' + term + r'\s*' + Q + r'\s*(shall\s+)?means?\b', t))


def _linewise(ctx):
    """ctx["raw"] with runs of spaces/tabs collapsed but LINE BREAKS KEPT.

    This is exactly the normalization the pre-retrofit text_of() applied
    (`re.sub(r'[ \\t]+', ' ', tag_stripped_text)`), and it is what a check
    using re.MULTILINE needs. ctx["t"] cannot serve: ora_doc_qc.norm()
    collapses \\s+, newlines included. Only A2 uses this.
    """
    return re.sub(r'[ \t]+', ' ', ctx["raw"])


def _a2(ctx):
    """Dead cross-reference: the lease points at a 'RIGHTS RESERVED BY
    LANDLORD' section that does not exist as a heading. Body identical to the
    pre-retrofit lambda; only the text channel differs (see _linewise)."""
    t = _linewise(ctx)
    if 'RIGHTS RESERVED BY LANDLORD' not in t.upper():
        return None
    if re.search(r'^\s*RIGHTS RESERVED BY LANDLORD\.', t, re.M | re.I):
        return None
    return True


def _f9(ctx):
    """Non-breaking-space artifacts. Must read raw - norm() strips them."""
    return True if '\xa0' in ctx["raw"] else None


def _f18(ctx):
    """Footer lacks the ORA Master Lease form-version tag.

    Pre-retrofit this was:
        '[[FOOTER]]' in t and 'ORA Master Lease v' not in t.split('[[FOOTER]]')[1]
    where text_of() appended '\\n[[FOOTER]] ' + footer_text UNCONDITIONALLY to
    every .docx and never to anything else. Hand-derived truth table:
        docx, footer carries the tag  -> pass  (tail contains it)
        docx, footer lacks the tag    -> FAIL
        docx, no footer part at all   -> FAIL  (tail is empty; empty lacks it)
        non-docx                      -> pass  (no marker was ever appended)
    meta["footer"] defaults to "" when there is no footer part, and "" does not
    contain the tag, so the format guard plus a plain containment test
    reproduces all four rows. All four are asserted in
    tests/test_lease_qc.py::TestF18FooterRewrite, each against a frozen copy of
    the original logic rather than against this comment.
    """
    if ctx["meta"]["format"] != "docx":
        return None
    return None if 'ORA Master Lease v' in ctx["meta"]["footer"] else True


# --------------------------------------------------------------------------
# T2 -- footer FILENAME/DOCPROPERTY field names a different tenant
# --------------------------------------------------------------------------
# lease-generation's SKILL.md hands this scanner a second job: a lease
# cloned from a DIFFERENT tenant's executed lease as a drafting shortcut
# (rather than the property template -- see "Why this exists" above) can
# leave a Word FILENAME or DOCPROPERTY field in the footer that still
# resolves to the OLD tenant's name, even after every [BRACKETED] token in
# the body and footer has been filled. T1 cannot catch this: a field's
# cached result is not a token, it is ordinary-looking text that happens to
# be wrong.
#
# T2 is registered like any other check but, like A2/F9/F18, is NOT
# bool_check()-wrapped: it needs ctx["meta"]["footer"] (T1/F18's channel)
# and ctx["raw"] (the un-normalized body, for a reliable defined-Tenant
# quote match), not the norm()'d ctx["t"].

_ENTITY_SUFFIX_RE = re.compile(
    r'\b(l\.?\s?l\.?\s?c\.?|inc\.?|incorporated|corp\.?|corporation|company|'
    r'co\.?|ltd\.?|limited|l\.?\s?p\.?|limited\s+partnership|'
    r'limited\s+liability\s+compan(?:y|ies))\b', re.I)


def _normalize_entity_name(name):
    """Case/punctuation/whitespace/entity-suffix-insensitive form of an
    entity or individual name, for comparing a footer field's resolved
    value against the lease's own defined Tenant name(s). Squashes ALL
    remaining whitespace (not just runs of it) so 'Acme Holdings LLC' and a
    filename-derived 'AcmeHoldings' compare equal -- a FILENAME field's
    cached value is routinely word-concatenated, and a footer field is
    never going to be spaced exactly like the body's prose."""
    if not name:
        return ""
    n = name.lower().replace("&", " and ")
    n = re.sub(r'[.,]', ' ', n)
    n = _ENTITY_SUFFIX_RE.sub(' ', n)
    return re.sub(r'[^a-z0-9]+', '', n)


_TENANT_QUOTE_RE = re.compile(Q + r'\s*(?:the\s+)?Tenant\s*' + Q, re.I)
_LANDLORD_ANCHOR_RE = re.compile(Q + r'\s*Landlord\s*' + Q + r'\s*\)?', re.I)
_TRAILING_COLLECTIVE_RE = re.compile(
    r'\(?\s*(?:individually\s+and\s+collectively|collectively|'
    r'jointly\s+and\s+severally)\s*,?\s*\)?\s*$', re.I)

_TENANT_NAME_STOPWORDS = {
    "the", "by", "between", "and", "made", "this", "lease", "agreement", "is",
    "collectively", "individually", "jointly", "severally", "referred", "to",
    "as", "hereinafter", "landlord", "tenant", "a", "an", "of", "for", "with",
}


def _extract_tenant_names(text):
    """Best-effort name(s) bound to the lease's own defined "Tenant" term,
    read from its parties clause (e.g. '... 2203 Northwood, LLC
    ("Landlord") and Impact Home Technology LLC and Ryan Adam Spear,
    individually (individually and collectively, "Tenant")' -> ["Impact
    Home Technology LLC", "Ryan Adam Spear"]).

    Anchors on the LANDLORD's own defined-term parenthetical (a reliable
    landmark in ORA's standard preamble: '<Landlord entity> ("Landlord")
    and <Tenant name(s)> ("Tenant")'), not on the first bare "and" in the
    sentence -- a naive '\\band\\s+' anchor matches whichever "and" comes
    first ("made AND entered into by AND between ...") and captures
    everything from there to the Tenant quote, including the Landlord's own
    name. Falls back to a bounded lookback window when no Landlord anchor
    is found (still conservative -- see below).

    Returns every name in a co-tenant list, not just one -- ratified
    position 2 (individuals joined as joint-and-several co-tenants, never a
    guaranty) means "the Tenant" routinely IS a list, and T2 must check a
    footer field against ALL of them before calling it a mismatch (a field
    correctly naming any one listed co-tenant is not stale boilerplate).

    Deliberately conservative: returns [] rather than guess whenever no
    confident "'Tenant'" quote is found at all. T2 must never fire on a
    Tenant name it is not sure of -- a false BLOCK on a signature-ready
    lease is the worst failure mode for a pre-execution gate.
    """
    window_text = text[:4000]
    names = []
    for qm in _TENANT_QUOTE_RE.finditer(window_text):
        anchor_end = None
        for lm in _LANDLORD_ANCHOR_RE.finditer(window_text[:qm.start()]):
            anchor_end = lm.end()          # nearest Landlord anchor before this quote
        start = anchor_end if anchor_end is not None else max(0, qm.start() - 300)
        prefix = window_text[start:qm.start()]
        prefix = _TRAILING_COLLECTIVE_RE.sub('', prefix).rstrip()
        prefix = re.sub(r'^\s*and\s+', '', prefix, flags=re.I)
        for piece in re.split(r'\s*(?:,\s*(?:and\s+)?|\s+and\s+|&)\s*', prefix):
            piece = piece.strip(' ,.\'"()')
            piece = re.sub(r',?\s*individually\s*$', '', piece, flags=re.I).strip()
            if not piece or piece.lower() in _TENANT_NAME_STOPWORDS:
                continue
            if not piece[:1].isalpha() or not piece[:1].isupper():
                continue
            words = piece.split()
            # Reject if ANY word is a sentence stopword, not just when the
            # WHOLE piece is one -- without this, the no-anchor fallback
            # window (used when no ("Landlord") parenthetical precedes the
            # Tenant quote) can capture a verb-phrase fragment like "This
            # Lease is made by" as if it were a party name; caught in
            # independent review. A real entity/person name never contains
            # "is", "made", "by", "the", ... as one of its own words.
            if any(w.lower().strip('.,') in _TENANT_NAME_STOPWORDS for w in words):
                continue
            names.append(piece)
    seen, out = set(), []
    for n in names:
        k = n.lower()
        if k not in seen:
            seen.add(k)
            out.append(n)
    return out


_FIELD_HEAD_RE = re.compile(r'\b(FILENAME|DOCPROPERTY)\b')
_SWITCH_NOISE_RE = re.compile(r'\\\*\s*MERGEFORMAT|\\[a-zA-Z]\b\s*', re.I)


def _footer_field_candidates(footer_text):
    """(kind, prop, result) for every FILENAME/DOCPROPERTY field visible in
    the STRIPPED footer text ora_doc_qc.extract() already produced.

    This is a real, documented limit, not an oversight: Word encodes a
    field two ways. A SIMPLE field (<w:fldSimple w:instr="...">...
    </w:fldSimple>) carries its instruction in a tag ATTRIBUTE, which
    ora_doc_qc._strip_xml() discards along with every other tag --
    invisible here, and there is no way to recover it from ctx (no file
    path, no raw-XML channel). A COMPLEX field (<w:fldChar .../> begin,
    <w:instrText>...</w:instrText>, another fldChar "separate", the cached
    result run(s), a final fldChar "end") keeps its instruction as ELEMENT
    TEXT, which _strip_xml() does NOT remove -- Word's own document order
    puts the instruction immediately before the cached result in the
    stripped stream, which is what this function anchors on. Widening this
    to catch fldSimple too is a change to the shared extraction module (ctx
    would need a raw-XML or file-path channel it does not carry today) --
    out of reach here: lease_qc.py must not regain its own zipfile-based
    extraction path (tests/test_lease_qc.py's
    test_module_imports_nothing_from_a_local_extraction_path pins that),
    and this file must not touch ora_doc_qc.py, shared with pma-qc and
    listing-agreement-qc.
    """
    text = re.sub(r'[ \t]+', ' ', footer_text or "")
    out = []
    for m in _FIELD_HEAD_RE.finditer(text):
        kind = m.group(1).upper()
        tail = text[m.end():]
        nl = tail.find('\n')
        if nl != -1:
            tail = tail[:nl]
        prop = None
        pm = re.match(r'\s*"([^"]*)"', tail)
        if pm:
            prop = pm.group(1)
            tail = tail[pm.end():]
        elif kind == "DOCPROPERTY":
            # Word writes a custom property name TWO ways: quoted
            # (' DOCPROPERTY "TenantName" \* MERGEFORMAT ') and, just as
            # commonly for a single-token name, unquoted
            # (' DOCPROPERTY  TenantName  \* MERGEFORMAT '). The
            # quoted-only parse above silently never matched the unquoted
            # form -- caught in independent review -- which left the
            # _TENANT_PROP_RE gate below unreachable for what is likely
            # the MORE common real-world encoding.
            pm2 = re.match(r'\s*([A-Za-z_][A-Za-z0-9_]*)\b', tail)
            if pm2:
                prop = pm2.group(1)
                tail = tail[pm2.end():]
        tail = _SWITCH_NOISE_RE.sub(' ', tail)
        # _strip_xml() leaves no delimiter where the field's own
        # <w:fldChar fldCharType="end"/> used to be, so an EMPTY field
        # (never refreshed) or a short one runs straight into whatever
        # footer text follows on the same line with nothing marking the
        # boundary between them -- caught in review: an empty field
        # immediately followed by page-numbering text on the same <w:p>
        # was captured as the field's "result" (e.g. "Page 1 of 12"). Cut
        # at ORA's own footer segment separators (bullet/pipe, or a dash
        # introducing "Page N") and at a bare "Page N" run even with no
        # separator, so a segment that was never part of THIS field never
        # gets treated as its cached value.
        tail = re.split(r'\s*[•|]\s*', tail, maxsplit=1)[0]
        tail = re.split(r'\s+-\s+(?=Page\s+\d)', tail, maxsplit=1, flags=re.I)[0]
        tail = re.split(r'\bPage\s+\d', tail, maxsplit=1, flags=re.I)[0]
        tail = tail.strip()
        if tail:
            out.append((kind, prop, tail))
    return out


_FILENAME_NOISE_RE = re.compile(
    r'^(?:lease|suite|redline|draft|vs|final|executed|clean|amendment|'
    r'addendum|v\d+[a-z]?|\d{1,8})$', re.I)

# A DOCPROPERTY field's custom property NAME must itself read as a
# tenant/party field before its value is trusted as a tenant claim -- see
# _entity_name_from_field()'s docstring for why an unfiltered value produced
# false BLOCKs on ordinary metadata fields ("Company", "Manager", "Title",
# a doc-ID) in review.
_TENANT_PROP_RE = re.compile(r'tenant|lessee', re.I)


def _entity_name_from_field(kind, prop, result):
    """The candidate entity/tenant name embedded in one field's cached
    result, or "" if the field does not plausibly carry a tenant claim at
    all -- T2 must never guess.

    DOCPROPERTY: used only when the property NAME itself is tenant/lessee-
    labeled (e.g. 'TenantName'); a custom document property can hold
    anything (a doc ID, ORA's own company name, a manager, a title), and
    treating an arbitrary property's value as a tenant claim produced real
    false BLOCKs in review. An untagged property returns "" -- not a
    guess, not a comparison.

    FILENAME: ORA's naming convention places the tenant token after a
    literal 'Lease' marker ('<Address> Suite <X> Lease <Tenant> <MM-YYYY>
    v0N.docx', or the test-fixture-style 'Lease_TenantName_MMDDYYYY.docx').
    Only tokens AFTER that marker are ever treated as a tenant claim --
    scanning the whole filename (address, suite, dates) reads unrelated
    tokens as "the tenant" whenever a filename happens to carry no real
    tenant name at all (an address-only filename, or a bare version tag
    after 'Lease'), which was the review's other reproduced false BLOCK.
    A filename with no 'Lease' marker returns "".
    """
    result = re.sub(r'\.(docx?|pdf)$', '', (result or "").strip(), flags=re.I)
    if kind == "DOCPROPERTY":
        if not prop or not _TENANT_PROP_RE.search(prop):
            return ""
        return result
    if kind == "FILENAME":
        m = re.search(r'\bLease[_\s]+(.*)$', result, re.I)
        if not m:
            return ""
        tokens = [t for t in re.split(r'[_\-\s]+', m.group(1)) if t]
        keep = [t for t in tokens if not _FILENAME_NOISE_RE.match(t)]
        return " ".join(keep)
    return ""


def _t2(ctx):
    """Footer FILENAME/DOCPROPERTY field resolves to a tenant name other
    than this lease's own defined Tenant. See _footer_field_candidates()
    for why only COMPLEX fields (fldChar+instrText) are detectable this
    way, and _extract_tenant_names() for why a co-tenant list is checked as
    a whole, never just its first name. No field in the footer at all --
    lease-generation's own output, which replaces the field with static
    text -- passes cleanly by design: the very first check below is the
    whole gate for that case."""
    if ctx["meta"]["format"] != "docx":
        return None
    fields = _footer_field_candidates(ctx["meta"].get("footer", ""))
    if not fields:
        return None
    tenant_names = _extract_tenant_names(ctx["raw"])
    if not tenant_names:
        return None
    norm_tenants = {n for n in (_normalize_entity_name(t) for t in tenant_names) if n}
    if not norm_tenants:
        return None
    for kind, prop, result in fields:
        candidate = _entity_name_from_field(kind, prop, result)
        norm_candidate = _normalize_entity_name(candidate)
        if not norm_candidate:
            continue
        if any(norm_candidate == nt or norm_candidate in nt or nt in norm_candidate
               for nt in norm_tenants):
            continue
        label = f'{kind} "{prop}"' if prop else kind
        return (f'footer {label} field resolves to "{candidate}", which does not '
                f'match this lease\'s defined Tenant ({", ".join(tenant_names)}) -- '
                f'verify this was not cloned from a different tenant\'s executed '
                f'lease and left as stale boilerplate.')
    return None


# (id, severity, label, position, fn(ctx)) -- fn returns None to PASS, True to
# FAIL with the label as the detail. Test bodies are verbatim from the
# pre-retrofit file; bool_check() adapts `lambda t: <bool>` to the shared
# ctx-based calling convention with no change to what is tested.
# position is None throughout: lease-form-qc has no standing-positions
# document to cross-reference the way pma-qc (PM-*) and
# listing-agreement-qc (SP-*) do.
CHECKS = [
    bool_check("A1", "BLOCK", "ZIP/address conflict between Sec.1 premises and Sec.4 building block",
               lambda t: len({z for z in re.findall(r'\b4\d{4}\b', t)} - {'43215'}) > 1),
    bool_check("A6", "BLOCK", "Operating-cost pass-through has no billing/reconciliation machinery",
               lambda t: not re.search(r'reconcil', t, re.I)),
    bool_check("A7", "BLOCK", "'net base rent' label on a base-year expense stop (NNN vs gross conflict)",
               lambda t: bool(re.search(r'net base rent', t, re.I)) and bool(re.search(r'increase over base year', t, re.I))),
    bool_check("A11", "BLOCK", "Audited CPA financial statements demanded of a small tenant",
               lambda t: bool(re.search(r'audited by a certified public accountant', t, re.I))),
    bool_check("B7", "BLOCK", "Tenant notice address is the Premises only (fails pre-occupancy/post-abandonment)",
               lambda t: not re.search(r'TENANT NOTICE ADDRESS|Tenant.{0,40}notice address', t, re.I)),
    # A2 is ctx-aware: it needs line breaks for its re.M anchor. See _a2.
    ("A2", "HIGH", "Dead cross-reference: 'RIGHTS RESERVED BY LANDLORD' section does not exist",
     None, _a2),
    bool_check("A2b", "HIGH", "Dead cross-reference: 'INSPECTIONS...' missing the leading 'ENTRY FOR'",
               lambda t: bool(re.search(r'entitled[,]?\s*[""]?\s*INSPECTIONS,\s*REPAIRS', t, re.I))
               or bool(re.search(r'REPAIRS AND INSTALLATION[,""]', t))),
    bool_check("A3", "HIGH", "Dead cross-reference: section 'ALL RISK PROPERTY INSURANCE' does not exist",
               lambda t: bool(re.search(r'entitled[,]?\s*[""]?\s*ALL RISK PROPERTY INSURANCE', t, re.I))),
    bool_check("A9", "HIGH", "Prevailing-party carve-out cites DEFAULT OF TENANT; fee rule lives in REMEDIES",
               lambda t: bool(re.search(r'Except as set forth in the section of this Lease entitled\s*[""]?DEFAULT OF TENANT', t, re.I))),
    bool_check("A5a", "HIGH", "'Project' used but never defined",
               lambda t: 'Project' in t and not _defined(t, 'Project')),
    bool_check("A5b", "HIGH", "'Building' used but never defined",
               lambda t: 'Building' in t and not _defined(t, 'Building')),
    bool_check("A5c", "HIGH", "'Business Day' used but never defined",
               lambda t: 'Business Day' in t and not _defined(t, 'Business Days?')),
    bool_check("A4a", "HIGH", "CERCLA miscited as 42 U.S.C. 9061 (correct: 9601)",
               lambda t: '9061' in t),
    bool_check("A4b", "HIGH", "HMTA cited at obsolete 49 U.S.C. 1802 (recodified 1994 at 5101)",
               lambda t: bool(re.search(r'49 U\.?\s?S\.?\s?C\.?\s*(Section|§)?\s*1802', t))),
    bool_check("A8", "HIGH", "Authority clause limited to corporations (tenants are LLCs/individuals)",
               lambda t: bool(re.search(r'If Tenant is or will be a corporation', t, re.I))),
    bool_check("A10", "HIGH", "'Delay in Commencement' circular against a fixed Commencement Date",
               lambda t: bool(re.search(r'Delay in Commencement', t, re.I))),
    bool_check("B2", "HIGH", "Mitigation disclaimer unqualified (Frenchtown v. Lemstone exposure)",
               lambda t: bool(re.search(r'no obligation to relet', t, re.I))
               and not re.search(r'required by applicable law', t, re.I)),
    bool_check("B3", "MED", "Acceleration without credit for reletting proceeds / fair rental value",
               lambda t: bool(re.search(r'accelerate and recover', t, re.I))
               and not re.search(r'net proceeds of any reletting|fair rental value', t, re.I)),
    bool_check("B4", "MED", "Holdover formula ambiguous (200% applied to accrued arrears)",
               lambda t: bool(re.search(r'two hundred percent \(200%\) of the amount of \(a\)', t, re.I))),
    bool_check("B5", "MED", "HVAC replacement responsibility never affirmatively allocated",
               lambda t: not re.search(r'responsible for replacement of the heating', t, re.I)),
    bool_check("B6a", "MED", "CGL general aggregate limit not stated",
               lambda t: not re.search(r'general aggregate', t, re.I)),
    bool_check("B6b", "MED", "Employer's Liability limit not stated",
               lambda t: not re.search(r"Employer.s Liability", t, re.I)),
    bool_check("B6c", "MED", "No annual COI delivery obligation (certificates only pre-possession)",
               lambda t: not re.search(r'renewal certificates|annually during the Lease Term', t, re.I)),
    bool_check("B8", "MED", "Water supplied 'at Tenant's expense' with no billing mechanism",
               lambda t: bool(re.search(r'water sufficient for drinking', t, re.I))
               and not re.search(r'flat rate of \$', t, re.I)),
    bool_check("B11", "MED", "Guarantor/co-tenant mismatch: 'any guarantor' language with no guaranty and no co-tenant conform",
               lambda t: bool(re.search(r'any guarantor of this Lease', t, re.I))
               and not re.search(r'Guaranty of Lease|GUARANTY', t)
               and not re.search(r'any person or entity comprising Tenant', t, re.I)),
    bool_check("C1", "MED", "No no-recording clause",
               lambda t: not re.search(r'shall not record this Lease', t, re.I)),
    bool_check("C2", "MED", "No Landlord default notice-and-cure standard",
               lambda t: not re.search(r'Landlord shall not be in default', t, re.I)),
    bool_check("C3", "MED", "No force majeure clause",
               lambda t: not re.search(r'force majeure', t, re.I)),
    bool_check("C4", "LOW", "No OFAC / sanctions representation",
               lambda t: not re.search(r'Foreign Assets Control|OFAC', t, re.I)),
    bool_check("C5", "MED", "No counterparts / electronic signature clause",
               lambda t: not re.search(r'counterpart', t, re.I)),
    bool_check("C6", "LOW", "No 'time is of the essence' clause",
               lambda t: not re.search(r'[Tt]ime is of the essence', t)),
    bool_check("C7", "LOW", "No personal property tax allocation to Tenant",
               lambda t: not re.search(r'taxes and assessments levied on Tenant', t, re.I)),
    bool_check("C8", "HIGH", "No Exhibit A premises depiction / stipulated square footage",
               lambda t: not re.search(r'Exhibit A', t)),
    bool_check("F1", "LOW", "'his agents' - Landlord is an LLC",
               lambda t: 'his agents, employees and invitees' in t),
    bool_check("F2", "LOW", "'succeeding Lease or succeeding tenant'",
               lambda t: bool(re.search(r'succeeding Lease or succeeding tenant', t, re.I))),
    bool_check("F3", "LOW", "'a comparable publications'",
               lambda t: 'a comparable publications' in t),
    bool_check("F4", "LOW", "'Interior lighting' stray mid-sentence capital",
               lambda t: 'Interior lighting' in t),
    bool_check("F5", "LOW", "'under seal' - Ohio abolished private seals",
               lambda t: bool(re.search(r'under seal', t, re.I))),
    bool_check("F7", "HIGH", "Fragile numeric self-reference ('this Section N') — breaks when sections shift",
               lambda t: bool(re.search(r'this Section \d+', t))),
    bool_check("F8", "LOW", "Default interest lacks usury savings clause (lesser-of max lawful rate)",
               lambda t: bool(re.search(r'eighteen percent \(18%\) per annum', t))
               and not re.search(r'maximum rate permitted by', t, re.I)),
    # F9 is ctx-aware: norm() would have stripped the very character it looks
    # for. See _f9.
    ("F9", "LOW", "Non-breaking-space artifacts in operative text", None, _f9),
    bool_check("F10", "MED", "No venue clause (courts of the county where the Project is located) — v2.5 standard",
               lambda t: 'Venue for any action' not in t),
    bool_check("F11", "HIGH", "Indemnity lacks waiver-of-subrogation carve-out (insurer can bypass the mutual waiver) — v2.5 standard",
               lambda t: 'waived pursuant to the waiver of subrogation' not in t),
    bool_check("F12", "MED", "'Governmental Agency' or 'Building Standard' used but undefined — v2.5 standard",
               lambda t: (('Governmental Agency' in t and not _defined(t, 'Governmental Agency'))
                          or (re.search(r'[Bb]uilding [Ss]tandard', t) and not _defined(t, 'Building Standard')))),
    bool_check("F13", "MED", "Operating Costs lack separate-billing exclusion (flat-fee water double-recovery risk) — v2.5 standard",
               lambda t: 'increase over base year' in t and 'shall not include amounts separately billed' not in t),
    bool_check("F6", "LOW", "Late fee runs on Business Days, cure on calendar days, and 'Business Day' is undefined",
               lambda t: bool(re.search(r'five \(5\) Business Days following the date when due', t, re.I))
               and not _defined(t, 'Business Days?')),
    bool_check("F14", "MED", "Insurance not modernized: 'All Risk' without '(Special Form)' — v2.6 standard",
               lambda t: 'All Risk' in t and '(Special Form)' not in t),
    bool_check("F15", "MED", "Landlord exculpation lacks manager/member/officer/agent enumeration — v2.6 standard",
               lambda t: 'No other person or entity shall be liable' in t
               and 'manager, member, officer, employee or agent of Landlord' not in t),
    bool_check("F16", "MED", "Assignment/sublease lacks excess-rent (profit) capture — v2.6 standard",
               lambda t: bool(re.search(r'assign or otherwise transfer this Lease', t, re.I))
               and 'of such excess' not in t),
    bool_check("F17", "MED", "HVAC servicing without continuous annual preventative-maintenance contract — v2.6 standard",
               lambda t: bool(re.search(r'serviced on a semiannual basis', t, re.I))
               and 'preventative-maintenance contract' not in t),
    # F18 is ctx-aware: it reads meta["footer"], not body text. See _f18.
    ("F18", "LOW", "Footer lacks the ORA Master Lease form-version tag — v2.6 standard",
     None, _f18),
]

# This skill's own token pattern, deliberately NOT the shared module's default
# (which adds '_' to the class and caps the run at 40 chars). Swapping it would
# be an unrequested, unverified change to what counts as an unfilled token, so
# the local regex stays in force. Pinned by
# tests/test_lease_qc.py::test_local_token_regex_is_preserved_not_the_shared_default.
TOKEN_RE = re.compile(r"\[[A-Z][A-Z0-9 /,.'&-]{2,}\]")


def _t1(ctx):
    """Unfilled template tokens remain — scanned in the BODY *and* the FOOTER.

    T1 was previously synthesized ad hoc inside the old scan() only when tokens
    were found; it is now registered once and evaluated like every other check,
    so it appears in --json and in the checks_run denominator.

    It is NOT registered via ora_doc_qc.unfilled_token_check(), for one reason:
    that helper scans ctx["raw"] alone, and extract(want_footer=True) routes
    footer text to ctx["meta"]["footer"], a channel the helper never reads. The
    pre-retrofit text_of() covered the footer by splicing it onto the body; the
    splice is gone (it caused its own false BLOCK — see the module docstring),
    so the footer must be scanned explicitly or the coverage silently vanishes.
    That is not hypothetical: ORA's own v2.6 master carries
    '[PREMISES ADDRESS]' and '[TENANT ENTITY]' in word/footer2.xml and
    word/footer3.xml, so a lease drafted from it with the body filled and the
    footer left untouched would clear a body-only T1 and go out for signature
    with both tokens printed on every page — the exact failure this BLOCK
    exists to prevent. Pinned by
    tests/test_lease_qc.py::TestTokenGate::test_unfilled_footer_tokens_block_a_filled_body_lease.

    The two gates ('_TEMPLATE' in the filename, --allow-tokens), the BLOCK
    severity, and the detail-string shape are reproduced from the shared helper
    verbatim; only the scanned text differs.
    """
    if ctx.get("is_template") or ctx.get("allow_tokens"):
        return None
    hay = ctx["raw"] + "\n" + ctx["meta"].get("footer", "")
    toks = sorted(set(TOKEN_RE.findall(hay)))
    if not toks:
        return None
    shown = ", ".join(toks[:6]) + ("..." if len(toks) > 6 else "")
    return f"{len(toks)} unfilled token(s): {shown}"


CHECKS.append(("T1", "BLOCK", "Unfilled template tokens remain", None, _t1))
CHECKS.append(("T2", "BLOCK", "Footer FILENAME/DOCPROPERTY field names a different tenant",
               None, _t2))


# ==========================================================================
# --loi-conformance mode -- deal-terms register vs. drafted lease
# ==========================================================================
# lease-generation's SKILL.md ("3. Gates", item 4) hands this skill a second
# job: replicate its "LOI conformance matrix" as a scanner-owned, testable
# output instead of the manual judgment call lease-generation currently
# makes by hand. Field categories and the status vocabulary (CONFORMS /
# CONFORMS+ / PARTIAL / MISSING / CONFLICT) come from that SKILL.md section
# and from references/deal-terms-register.schema.json's top-level deal-fact
# groups (16 of them, excluding pure metadata: deal_id, source_documents,
# template, ratified_position_departures, decision_gates, open_items).
#
# Deliberately a SEPARATE code path from CHECKS/run_checks() above: it
# answers "does the drafted lease match THIS DEAL's negotiated terms", not
# "does ORA's paper carry its known systemic defects" -- a different
# question, against a different source of truth (a per-deal JSON register,
# not the fixed defect registry), with a different output shape (a matrix,
# not BLOCK/HIGH/MED/LOW findings). It reuses ora_doc_qc.extract()/norm()
# for text, unchanged, and touches no shared aggregation code.

_MONEY_RE_CACHE = {}


def _find_dollar_amount(text, amount):
    """A dollar figure equal to `amount`, matched to the EXACT CENT, written
    with comma grouping and either no decimal (a whole-dollar amount) or the
    matching '.NN'. Returns None on any other cents (including a bare
    integer prefix of a different figure, e.g. amount=2000 must NOT match
    "$2,000.50" in the text -- register rents are routinely rsf * rate / 12
    and essentially never land on a whole dollar, so truncating to int()
    before matching silently treated a genuinely CONFLICTing cents figure
    as a match; caught in independent review)."""
    if amount is None:
        return None
    cents = round(float(amount) * 100)
    pat = _MONEY_RE_CACHE.get(cents)
    if pat is None:
        whole, frac = divmod(cents, 100)
        num = f'{whole:,}' + (f'.{frac:02d}' if frac else r'(?:\.00)?')
        # (?!\d)(?!\.\d): a following digit, or a decimal point introducing
        # a DIFFERENT cents figure, both fail the match -- \b alone sits
        # right after the whole-dollar digits regardless of what follows,
        # so it would otherwise also match e.g. "$2,000.50" against a
        # whole-dollar 2000 register figure.
        pat = re.compile(r'\$\s*' + num + r'(?!\d)(?!\.\d)')
        _MONEY_RE_CACHE[cents] = pat
    m = pat.search(text)
    return m.group(0) if m else None


def _num_pattern(n):
    """Word-boundary pattern matching `n` written with or without comma
    grouping (e.g. 2400 or 2,400)."""
    n = int(n)
    variants = sorted({str(n), f'{n:,}'}, key=len, reverse=True)
    return r'\b(?:' + '|'.join(re.escape(v) for v in variants) + r')\b'


def _phrase_present(phrase, text, window=200, threshold=1.0):
    """True if `phrase`'s words are found in `text`, at the given
    `threshold` fraction (default 1.0 = every word).

    threshold=1.0 (the enum-value mode -- utilities): every word of
    `phrase` (underscores treated as spaces) must appear in `text` within
    `window` characters of the phrase's first word. Looser than a literal
    substring match, which real lease prose almost never produces verbatim
    from a register enum value, but still specific enough that unrelated
    text does not satisfy it.

    threshold<1.0 (the free-text-description mode -- landlord_work items,
    signage): register text here is a HUMAN-WRITTEN sentence
    ('one exterior sign over entrance + entry door signage,
    Landlord-approved'), not a fixed enum value a drafting engine copies
    verbatim -- requiring literal presence of every word (including a
    stray '+' or a hyphenated 'Landlord-approved') made these rows
    essentially unfailable to CONFORM against ORA's own canonical example
    register, which independent review flagged as a gate that degrades
    into permanent noise. This mode instead requires `threshold` of the
    phrase's SIGNIFICANT words (>=5 chars, surrounding punctuation
    stripped) to appear anywhere in `text` (no window/proximity
    requirement -- a work-item description and its lease implementation
    are not reliably adjacent). The 5-char floor specifically excludes
    short, generic words ('over', 'door', 'sign') that would otherwise
    make an UNRELATED lease register a false hit almost as often as a
    real one.
    """
    raw_words = [w for w in re.split(r'[\s_]+', phrase or "") if w]
    if threshold >= 1.0:
        if not raw_words:
            return False
        for m in re.finditer(re.escape(raw_words[0]), text, re.I):
            seg = text[m.start():m.start() + window]
            if all(re.search(re.escape(w), seg, re.I) for w in raw_words[1:]):
                return True
        return False
    words = [re.sub(r'^\W+|\W+$', '', w) for w in raw_words]
    sig = [w for w in words if len(w) >= 5]
    if not sig:
        return False
    hits = sum(1 for w in sig if re.search(re.escape(w), text, re.I))
    return (hits / len(sig)) >= threshold


def _find_entity_in_text(entity_name, text):
    if not entity_name:
        return None
    return entity_name if re.search(re.escape(entity_name), text, re.I) else None


_SECTION_HINTS = {
    "landlord": "PARTIES / BASIC LEASE INFORMATION",
    "tenant": "PARTIES / BASIC LEASE INFORMATION",
    "co_tenants": "PARTIES (co-tenant joinder, ratified position 2)",
    "premises": "DEMISED PREMISES",
    "use": "USE OF PREMISES",
    "term": "TERM",
    "options": "OPTIONS TO EXTEND",
    "rent": "RENT",
    "expense_structure": "OPERATING COSTS / RENT",
    "utilities": "UTILITIES",
    "security_deposit": "SECURITY DEPOSIT",
    "parking": "PARKING",
    "landlord_work": "LANDLORD'S WORK / EXHIBIT B",
    "maintenance": "MAINTENANCE AND REPAIRS",
    "insurance": "INSURANCE",
    "broker": "BROKER",
    "signage": "SIGNAGE",
}


def _check_landlord(reg, text):
    entity = (reg.get("landlord") or {}).get("entity")
    if not entity:
        return {"status": "MISSING", "detail": "register has no landlord.entity"}
    if _find_entity_in_text(entity, text):
        return {"status": "CONFORMS", "detail": f"landlord entity '{entity}' found in lease text"}
    return {"status": "MISSING", "detail": f"landlord entity '{entity}' not found in lease text"}


def _check_tenant(reg, text):
    entity = (reg.get("tenant") or {}).get("entity")
    if not entity:
        return {"status": "MISSING", "detail": "register has no tenant.entity"}
    if _find_entity_in_text(entity, text):
        return {"status": "CONFORMS", "detail": f"tenant entity '{entity}' found in lease text"}
    return {"status": "MISSING", "detail": f"tenant entity '{entity}' not found in lease text"}


def _check_co_tenants(reg, text):
    co_tenants = (reg.get("tenant") or {}).get("co_tenants") or []
    if not co_tenants:
        return {"status": "CONFORMS", "detail": "register lists no co-tenants"}
    hits = [n for n in co_tenants if _find_entity_in_text(n, text)]
    if len(hits) == len(co_tenants):
        if re.search(r'joint(?:ly)? and several(?:ly)?', text, re.I):
            return {"status": "CONFORMS",
                    "detail": f"co-tenant(s) {', '.join(co_tenants)} found, with "
                              f"joint-and-several language (ratified position 2)"}
        return {"status": "PARTIAL",
                "detail": "co-tenant(s) named but no joint-and-several language found "
                          "(ratified position 2 -- co-tenancy, never a guaranty)"}
    if not hits:
        return {"status": "MISSING",
                "detail": f"none of the register's co-tenant(s) {', '.join(co_tenants)} found"}
    return {"status": "PARTIAL",
            "detail": f"only {len(hits)} of {len(co_tenants)} co-tenant(s) found"}


def _check_premises(reg, text):
    p = reg.get("premises") or {}
    fields = [
        ("address", p.get("address"), lambda v: re.escape(v)),
        # Word-boundary anchored: an un-anchored suite match (e.g. suite
        # "1") matched somewhere inside virtually every lease regardless of
        # whether the real suite was mentioned at all -- caught in
        # independent review.
        ("suite", p.get("suite"), lambda v: r'\b' + re.escape(str(v)) + r'\b'),
        ("rsf", p.get("rsf"), lambda v: _num_pattern(v)),
    ]
    total = [f for f in fields if f[1] not in (None, "")]
    if not total:
        return {"status": "MISSING", "detail": "register has no premises fields"}
    missing = [label for label, val, patfn in total
               if not re.search(patfn(val), text, re.I)]
    if not missing:
        return {"status": "CONFORMS", "detail": "address/suite/RSF all found in lease text"}
    if len(missing) == len(total):
        return {"status": "MISSING", "detail": "none of address/suite/RSF found in lease text"}
    return {"status": "PARTIAL", "detail": f"missing: {', '.join(missing)}"}


def _check_use(reg, text):
    use = (reg.get("use") or {}).get("permitted_use")
    if not use:
        return {"status": "CONFORMS", "detail": "register specifies no restricted permitted use"}
    if re.search(re.escape(use), text, re.I):
        return {"status": "CONFORMS", "detail": f"permitted use '{use}' found"}
    return {"status": "MISSING", "detail": f"permitted use '{use}' not found in lease text"}


def _check_term(reg, text):
    term = reg.get("term") or {}
    months = term.get("months")
    if months is None:
        return {"status": "MISSING", "detail": "register has no term.months"}
    months_found = bool(re.search(_num_pattern(months) + r'\s*\)?\s*months?', text, re.I))
    # CONFORMS+ is grounded in the register's OWN term.early_access field,
    # not a bare text search for "early access" -- a text-only search
    # cannot tell "the register requires this and the lease has it" (plain
    # CONFORMS) from "the lease grants something the register never asked
    # for" (CONFORMS+), and mislabeled the former as the latter; caught in
    # independent review.
    early_access_required = bool(term.get("early_access"))
    early_access_found = bool(re.search(r'early access|early entry', text, re.I))
    if months_found:
        if early_access_required:
            if early_access_found:
                return {"status": "CONFORMS",
                        "detail": f"{months}-month term and the register's required "
                                  f"early access both found"}
            return {"status": "PARTIAL",
                    "detail": f"{months}-month term found, but the register's required "
                              f"early access ('{term['early_access']}') was not"}
        if early_access_found:
            return {"status": "CONFORMS+",
                    "detail": f"{months}-month term found, plus an early-access grant "
                              f"the register does not require"}
        return {"status": "CONFORMS", "detail": f"{months}-month term found"}
    m = re.search(r'[Tt]erm[^.]{0,60}?(\d{1,3})\s*\)?\s*months?', text)
    if m and int(m.group(1)) != int(months):
        return {"status": "CONFLICT",
                "detail": f"lease states {m.group(1)} months vs register's {months}"}
    return {"status": "MISSING", "detail": f"no {months}-month term language found"}


def _check_options(reg, text):
    opts = reg.get("options") or []
    if not opts:
        return {"status": "CONFORMS",
                "detail": "register specifies no options (ORA ratified position 6 default)"}
    hits = 0
    for o in opts:
        m = o.get("months")
        if m is None:
            continue
        pat = _num_pattern(m) + r'\s*\)?\s*months?'
        if (re.search(pat + r'.{0,80}option', text, re.I | re.S)
                or re.search(r'option.{0,80}' + pat, text, re.I | re.S)):
            hits += 1
    if hits == len(opts):
        return {"status": "CONFORMS", "detail": f"{hits} of {len(opts)} option(s) found"}
    if hits == 0:
        return {"status": "MISSING", "detail": "no option-term language found"}
    return {"status": "PARTIAL", "detail": f"only {hits} of {len(opts)} option(s) found"}


def _check_rent(reg, text):
    schedule = ((reg.get("rent") or {}).get("schedule")) or []
    if not schedule:
        return {"status": "MISSING", "detail": "register has no rent.schedule"}
    monthly = schedule[0].get("monthly")
    found_rent = _find_dollar_amount(text, monthly) if monthly is not None else None
    esc = (reg.get("rent") or {}).get("escalation") or {}
    esc_type = esc.get("type")
    esc_found = False
    esc_label = None
    if esc_type == "fixed_pct" and esc.get("value") is not None:
        esc_label = f"{esc['value']:g}%"
        esc_found = bool(re.search(re.escape(esc_label), text))
    elif esc_type == "none":
        esc_found = True
        esc_label = "flat (no escalation)"
    elif esc_type in ("cpi", "fixed_amount"):
        # NOT verified by this checker: a CPI-indexed or fixed-dollar-step
        # escalation cannot be confirmed from a single text search the way
        # a flat percentage can (there is no one string to look for). Was
        # silently falling through to the "no escalation info" CONFORMS
        # branch below -- a false CONFORMS for coverage never actually
        # performed. Caught in independent re-review.
        if found_rent:
            return {"status": "PARTIAL",
                    "detail": f"Year-1 rent {found_rent} found; the register's "
                              f"'{esc_type}' escalation requires manual verification "
                              f"(not text-matchable)"}
        return {"status": "MISSING",
                "detail": f"Year-1 rent figure not found; register also specifies a "
                          f"'{esc_type}' escalation requiring manual verification"}
    if found_rent and (esc_found or esc_label is None):
        return {"status": "CONFORMS",
                "detail": f"Year-1 rent {found_rent} found"
                          + (f" with {esc_label} escalation" if esc_found and esc_label else "")}
    if found_rent and not esc_found:
        return {"status": "PARTIAL",
                "detail": f"Year-1 rent {found_rent} found, but the register's "
                          f"{esc_label or 'escalation'} was not found in the lease text"}
    if not found_rent and esc_found:
        return {"status": "PARTIAL",
                "detail": "escalation language found but the Year-1 rent figure was not"}
    return {"status": "MISSING", "detail": "neither Year-1 rent nor escalation language found"}


_EXPENSE_PHRASES = {
    # Anchored to RENT/expense-structure phrasing, not the bare word
    # "gross" -- every ORA lease's exculpation/indemnity clause contains
    # "gross negligence", which a bare \bgross\b match fires on regardless
    # of expense structure, producing both a false CONFORMS (any lease,
    # any structure) and a false CONFLICT against a genuine NNN lease with
    # no "gross" rent language at all. Caught in independent review.
    "gross": r'(?:full[\s-]service\s+gross|gross\s+(?:basis|rent|lease)|'
             r'rent\s+(?:is|shall\s+be|are)\s+(?:calculated\s+)?(?:on\s+a\s+)?gross)',
    "modified_gross_base_year": r'base\s+year',
    "nnn": r'\btriple\s+net\b|\bNNN\b',
}


def _check_expense_structure(reg, text):
    t = (reg.get("expense_structure") or {}).get("type")
    if not t:
        return {"status": "MISSING", "detail": "register has no expense_structure.type"}
    pat = _EXPENSE_PHRASES.get(t)
    if pat and re.search(pat, text, re.I):
        return {"status": "CONFORMS", "detail": f"expense structure '{t}' language found"}
    for other_t, other_pat in _EXPENSE_PHRASES.items():
        if other_t != t and re.search(other_pat, text, re.I):
            return {"status": "CONFLICT",
                    "detail": f"lease reads as '{other_t}' but register specifies '{t}'"}
    return {"status": "MISSING", "detail": f"no '{t}' expense-structure language found"}


def _check_utilities(reg, text):
    u = reg.get("utilities") or {}
    total, hits, missing = 0, 0, []
    for key in ("electric", "water_sewer"):
        val = u.get(key)
        if not val:
            continue
        total += 1
        # NOT `or _phrase_present(key, text)` -- falling back to the bare
        # field NAME ("electric") made the row effectively unfailable
        # (almost every lease mentions "electric" somewhere) regardless of
        # what the register's actual enum VALUE says (e.g. who pays, or on
        # what basis); caught in independent review.
        if _phrase_present(val, text):
            hits += 1
        else:
            missing.append(key)
    if total == 0:
        return {"status": "CONFORMS", "detail": "register specifies no utilities detail"}
    if hits == total:
        return {"status": "CONFORMS", "detail": "utilities allocation language found"}
    if hits == 0:
        return {"status": "MISSING", "detail": "no utilities allocation language found"}
    return {"status": "PARTIAL", "detail": f"missing: {', '.join(missing)}"}


def _check_security_deposit(reg, text):
    sd = reg.get("security_deposit") or {}
    amount = sd.get("amount")
    if amount is None:
        return {"status": "MISSING", "detail": "register has no security_deposit.amount"}
    found = _find_dollar_amount(text, amount)
    if found:
        return {"status": "CONFORMS",
                "detail": f"lease states {found}, matching register's ${amount:,.2f}"}
    m = re.search(r'[Ss]ecurity\s+[Dd]eposit[^.$]{0,80}\$\s*[\d,]+(?:\.\d{2})?', text)
    if m:
        stated = re.search(r'\$\s*[\d,]+(?:\.\d{2})?', m.group(0)).group(0)
        return {"status": "CONFLICT",
                "detail": f"lease states {stated} vs register's ${amount:,.2f}"}
    return {"status": "MISSING",
            "detail": f"no Security Deposit dollar figure of ${amount:,.2f} found"}


def _check_parking(reg, text):
    count = (reg.get("parking") or {}).get("overnight_vehicles")
    if count is None:
        return {"status": "CONFORMS", "detail": "register specifies no overnight-vehicle allowance"}
    pat = _num_pattern(count)
    if (re.search(pat + r'.{0,40}(?:overnight|vehicle)', text, re.I)
            or re.search(r'(?:overnight|vehicle).{0,40}' + pat, text, re.I)):
        return {"status": "CONFORMS", "detail": f"{count} overnight vehicle(s) found"}
    return {"status": "MISSING",
            "detail": f"no overnight-parking allowance of {count} vehicle(s) found"}


def _check_landlord_work(reg, text):
    items = ((reg.get("landlord_work") or {}).get("items")) or []
    if not items:
        return {"status": "CONFORMS", "detail": "register specifies no landlord work items"}
    # threshold=0.5 (majority-of-significant-words, see _phrase_present):
    # these are free-text prose descriptions, not fixed enum values, and
    # requiring every word verbatim made this row essentially unfailable
    # to CONFORM against ORA's own canonical example register -- caught
    # in independent review.
    hits = sum(1 for item in items if _phrase_present(item, text, threshold=0.5))
    if hits == len(items):
        return {"status": "CONFORMS", "detail": f"all {len(items)} landlord-work item(s) referenced"}
    if hits == 0:
        return {"status": "MISSING",
                "detail": f"none of the {len(items)} register landlord-work item(s) found"}
    return {"status": "PARTIAL", "detail": f"only {hits} of {len(items)} landlord-work item(s) found"}


def _check_maintenance(reg, text):
    alloc = (reg.get("maintenance") or {}).get("allocation")
    if not alloc:
        return {"status": "MISSING", "detail": "register has no maintenance.allocation"}
    if alloc == "LOI_landlord_hvac_and_major_mechanicals":
        ok = bool(re.search(r'Landlord.{0,60}(?:responsible|maintain)\w*.{0,60}HVAC', text, re.I | re.S))
        return ({"status": "CONFORMS", "detail": "Landlord-HVAC maintenance allocation found"} if ok else
                {"status": "MISSING", "detail": "no Landlord-HVAC maintenance allocation language found"})
    if alloc == "ORA_form_default_tenant_hvac":
        ok = bool(re.search(r'Tenant.{0,60}(?:responsible|maintain)\w*.{0,60}HVAC', text, re.I | re.S))
        return ({"status": "CONFORMS", "detail": "Tenant-HVAC maintenance allocation (ORA default) found"} if ok else
                {"status": "MISSING", "detail": "no Tenant-HVAC maintenance allocation language found"})
    return {"status": "PARTIAL",
            "detail": f"custom maintenance.allocation ('{alloc}') requires manual verification"}


def _check_insurance(reg, text):
    agg = (reg.get("insurance") or {}).get("cgl_aggregate")
    if agg is None:
        return {"status": "CONFORMS", "detail": "register specifies no insurance limits"}
    found = _find_dollar_amount(text, agg)
    if found:
        return {"status": "CONFORMS", "detail": f"CGL aggregate {found} matches register"}
    m = re.search(r'general\s+aggregate[^.$]{0,40}\$\s*[\d,]+', text, re.I)
    if m:
        stated = re.search(r'\$\s*[\d,]+', m.group(0)).group(0)
        return {"status": "CONFLICT",
                "detail": f"lease states {stated} vs register's ${agg:,.0f} CGL aggregate"}
    return {"status": "MISSING", "detail": f"no ${agg:,.0f} CGL aggregate figure found"}


def _check_broker(reg, text):
    dual = (reg.get("broker") or {}).get("dual_agency")
    if not dual:
        return {"status": "CONFORMS", "detail": "register does not require dual-agency disclosure"}
    if re.search(r'dual\s+agen', text, re.I):
        return {"status": "CONFORMS", "detail": "dual-agency disclosure language found"}
    return {"status": "MISSING",
            "detail": "register flags dual agency but no dual-agency language found in lease"}


def _check_signage(reg, text):
    signage = reg.get("signage")
    if not signage:
        return {"status": "CONFORMS", "detail": "register specifies no signage right"}
    # threshold=0.5, same rationale as _check_landlord_work: signage is a
    # free-text grant description, not an enum value.
    if _phrase_present(signage, text, threshold=0.5):
        return {"status": "CONFORMS", "detail": "signage right language found"}
    if re.search(r'\bsignage\b', text, re.I):
        return {"status": "PARTIAL",
                "detail": "lease addresses signage but not matching the register's grant"}
    return {"status": "MISSING",
            "detail": "register grants a signage right not found in the lease text"}


_CONFORMANCE_CHECKERS = [
    ("landlord", _check_landlord),
    ("tenant", _check_tenant),
    ("co_tenants", _check_co_tenants),
    ("premises", _check_premises),
    ("use", _check_use),
    ("term", _check_term),
    ("options", _check_options),
    ("rent", _check_rent),
    ("expense_structure", _check_expense_structure),
    ("utilities", _check_utilities),
    ("security_deposit", _check_security_deposit),
    ("parking", _check_parking),
    ("landlord_work", _check_landlord_work),
    ("maintenance", _check_maintenance),
    ("insurance", _check_insurance),
    ("broker", _check_broker),
    ("signage", _check_signage),
]
# Deliberately NOT covered by a row: `special_provisions` (a heterogeneous
# array of ad-hoc title/text/placement clauses with no fixed shape to match
# against -- generic text-presence matching against arbitrary custom clause
# text is unreliable enough to be worse than no row at all) and the
# sub-fields of already-covered categories not independently checked here
# (e.g. utilities.gas/.trash, parking.allocation/.vehicle_class_cap). Flag
# these for manual review in the memo per lease-generation's SKILL.md
# rather than reporting a false CONFORMS for coverage this mode does not
# actually verify.


def build_conformance_matrix(register, text):
    """One row per deal-terms-register field category (see
    _CONFORMANCE_CHECKERS), each a CONFORMS / CONFORMS+ / PARTIAL / MISSING
    / CONFLICT verdict against the drafted lease's extracted text -- the
    SKILL.md 'LOI conformance matrix' gate, as a scanner-owned, testable
    output instead of a manual judgment call."""
    rows = []
    for category, fn in _CONFORMANCE_CHECKERS:
        try:
            result = fn(register, text)
        except Exception as e:                                      # noqa: BLE001
            # One malformed register field (wrong type, missing nested
            # key) must not crash the whole matrix -- mirrors
            # run_checks()'s "a broken check degrades, it never blinds the
            # report" posture (ora_doc_qc.py). MISSING (a blocking status)
            # rather than silently dropped: an uncheckable field reads as
            # "not verified", the conservative call for a pre-signature
            # gate. Caught in independent review.
            result = {"status": "MISSING", "detail": f"could not evaluate: {e}"}
        rows.append({"category": category,
                     "section": _SECTION_HINTS.get(category, ""),
                     "status": result["status"],
                     "detail": result["detail"]})
    return rows


def _conformance_summary(rows):
    counts = {}
    for r in rows:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    return counts


def _print_conformance_report(report):
    print("=" * 78)
    print(f"REGISTER   {report['register']}")
    print(f"LEASE      {report['lease_file']}")
    print("-" * 78)
    for r in report["rows"]:
        print(f"[{r['status']:<9}] {r['category']:<16} {r['section']}")
        print(f"            {r['detail']}")
    print("-" * 78)
    tally = " · ".join(f"{v} {k}" for k, v in sorted(report["summary"].items()))
    print(f"SUMMARY    {tally}")
    blocking = [r for r in report["rows"] if r["status"] in ("PARTIAL", "MISSING", "CONFLICT")]
    if blocking:
        print(f"GATE       {len(blocking)} row(s) not clear to ship without a resolved "
              f"gate (SKILL.md '3. Gates' item 4): " + ", ".join(r["category"] for r in blocking))
    else:
        print("GATE       clean -- every row CONFORMS or CONFORMS+")
    print()


def _run_loi_conformance(argv):
    ap = argparse.ArgumentParser(
        description="ORA LOI-conformance matrix: deal-terms register vs. a drafted lease")
    ap.add_argument("--loi-conformance", metavar="REGISTER_JSON", required=True,
                    help="deal-terms-register.json (see lease-generation/references/"
                         "deal-terms-register.schema.json)")
    ap.add_argument("lease_file", help="the drafted lease DOCX to check against the register")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    try:
        with open(a.loi_conformance, encoding="utf-8") as f:
            register = json.load(f)
    except Exception as e:                                          # noqa: BLE001
        print(f"ERROR: could not read register {a.loi_conformance}: {e}", file=sys.stderr)
        return 2
    if not isinstance(register, dict):
        print(f"ERROR: {a.loi_conformance} is not a JSON object -- a deal-terms "
              f"register must be a top-level object.", file=sys.stderr)
        return 2

    # Mirrors ora_doc_qc.scan()'s own guards (missing file, extraction
    # exception) so a bad --loi-conformance invocation gets exit 2 (usage/
    # data error), never exit 1 -- exit 1 means "the matrix was computed
    # and at least one row blocks", and collapsing an operational failure
    # into that code let an automated caller read a crash as a real
    # conformance verdict. Caught in independent review.
    if not os.path.exists(a.lease_file):
        print(f"ERROR: no such file: {a.lease_file}", file=sys.stderr)
        return 2
    try:
        body, meta = extract(a.lease_file, want_footer=True)
    except Exception as e:                                          # noqa: BLE001
        print(f"ERROR: extraction failed on {a.lease_file}: {e}", file=sys.stderr)
        return 2
    if body is None:
        print(f"ERROR: {a.lease_file} is UNREADABLE ({meta['words']} words) -- "
              f"no conformance result.", file=sys.stderr)
        return 2

    rows = build_conformance_matrix(register, norm(body))
    report = {"register": os.path.basename(a.loi_conformance),
              "lease_file": os.path.basename(a.lease_file),
              "rows": rows, "summary": _conformance_summary(rows)}

    if a.json:
        print(json.dumps(report, indent=2))
    else:
        _print_conformance_report(report)

    blocking = any(r["status"] in ("PARTIAL", "MISSING", "CONFLICT") for r in rows)
    return 1 if blocking else 0


def main():
    argv = sys.argv[1:]
    # Matches both the space form ("--loi-conformance reg.json") and
    # argparse's own "=" form ("--loi-conformance=reg.json") -- a plain
    # `in argv` membership test missed the latter, silently falling through
    # to the standard scan mode's build_cli(), which does not know the flag
    # and dies with a misleading "unrecognized arguments" usage error.
    if any(a == "--loi-conformance" or a.startswith("--loi-conformance=") for a in argv):
        sys.exit(_run_loi_conformance(argv))
    run_cli(CHECKS, "ORA lease-form QC gate", want_footer=True,
            ocr_absence_note=("Absence findings (A6, B5, B6a-B6c, B7, C1-C8, "
                              "F10, F11) are PROVISIONAL - OCR text is lossy, "
                              "so confirm against the page images before "
                              "reporting a clause missing."))


if __name__ == "__main__":
    main()
