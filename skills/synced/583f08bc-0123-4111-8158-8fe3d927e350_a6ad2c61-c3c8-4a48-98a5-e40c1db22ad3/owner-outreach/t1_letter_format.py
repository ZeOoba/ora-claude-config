"""
ORA T1 owner-outreach letter — format constants and fit rules.
Format Spec v1.1 (ratified 2026-08-24).

Drop this file beside build_t1_letterpack.py and import from it. It exists so the
letter's geometry lives in ONE named place instead of being scattered through the
generator as literals.

    from t1_letter_format import (
        PAGE, SPACING, SIG_GAP_TWIPS, LETTERHEAD_MODE,
        fit_re_line, split_address_block, tighten_for_overflow, verify_pack,
    )

Nothing here writes files or talks to the network.
"""

# --------------------------------------------------------------------------
# Page geometry (twips; 1440 twips = 1 inch)
# --------------------------------------------------------------------------

PAGE = {
    "width":  12240,   # 8.5"
    "height": 15840,   # 11"
    "top":     2160,   # 1.50" — clears the pre-printed letterhead band
    "bottom":  1440,   # 1.00"
    "left":    1584,   # 1.10"
    "right":   1584,   # 1.10"
    "header":   720,
    "footer":   720,
}

PRINTABLE_WIDTH_IN = (PAGE["width"] - PAGE["left"] - PAGE["right"]) / 1440.0  # 6.30"

# "letterhead" = pre-printed stock, no typeset firm block (the production default).
# "plain"      = plain paper, firm name + tagline typeset at the top of each letter.
LETTERHEAD_MODE = "letterhead"

# Plain-paper top margin (Format Spec v1.1): no pre-printed letterhead band to
# clear, so plain mode uses 1.00" instead of PAGE's letterhead-mode 1.50".
# Every other margin (bottom/left/right/header/footer) is identical in both
# modes -- only top changes.
PLAIN_TOP = 1440


def page_for_mode(mode=LETTERHEAD_MODE):
    """Return the page-margins dict for `mode` -- PAGE, with 'top' swapped to
    PLAIN_TOP when mode == "plain". PAGE itself always describes letterhead
    mode; this is the one place a caller should read plain mode's margins
    from, rather than re-deriving the swap inline."""
    if mode == "plain":
        return {**PAGE, "top": PLAIN_TOP}
    return PAGE

FONT = "EB Garamond"
SZ_BODY = 22        # half-points -> 11 pt
SZ_FIRM = 30        # 15 pt  (plain mode only)
SZ_TAGLINE = 19     # 9.5 pt (plain mode only)
COLOR_NAVY = "1B2A4A"

# --------------------------------------------------------------------------
# Paragraph spacing — space-after in twips. space-before is 0 everywhere.
# --------------------------------------------------------------------------

SPACING = {
    "date":            200,
    "owner_name":        0,
    "owner_addr":        0,
    "owner_csz":         0,
    "spacer":          120,
    "re_line":         200,
    "salutation":      160,
    "body":            200,
    "closing_thanks":  200,
    "sincerely":       920,   # the signature gap — 46 pt
    "sig_line":          0,
    "sig_web":         200,
    "postscript":        0,
}

SIG_GAP_TWIPS = SPACING["sincerely"]

# Per-letter fallback applied ONLY to a letter that will not otherwise fit one
# page. Never apply pack-wide; never shrink the font instead.
TIGHTEN = {200: 100, 160: 100, 120: 80, 920: 680}

# --------------------------------------------------------------------------
# Line budgets
# --------------------------------------------------------------------------
# Empirically calibrated against the 2026-08-26 pack (156 letters) at the
# geometry above. Every letter whose Re: line rendered at <= 61 characters fit
# one page; every letter at >= 80 characters wrapped to a second line and pushed
# the P.S. onto page two. 76 sits in the middle of that gap with margin on both
# sides. Address-block lines share the same printable width, so they share the
# budget.

MAX_LINE_CHARS = 76
RE_PREFIX = "Re:  "

# Re:-line property list is truncated past this many properties with "(+N more)".
# NOTE: this cap alone does NOT prevent a wrap — three long addresses can still
# render at 87 characters. MAX_LINE_CHARS is the binding constraint; this is the
# knob fit_re_line() turns to satisfy it.
RE_LIST_SOFT_CAP = 3


def fit_re_line(properties, market, max_chars=MAX_LINE_CHARS):
    """Build a Re: line that renders on ONE line.

    properties : list[str] site addresses, queue order (highest score first)
    market     : str market name

    Drops properties from the visible list until the whole line fits, rolling
    every dropped property into the "(+N more)" tail. Always shows at least one
    property; if a single address plus the market still exceeds the budget, the
    line is returned long and verify_pack() will catch the resulting overflow
    rather than silently truncating an address.
    """
    props = list(properties)
    if not props:
        raise ValueError("fit_re_line: no properties")

    for shown in range(min(len(props), RE_LIST_SOFT_CAP), 0, -1):
        hidden = len(props) - shown
        body = " · ".join(props[:shown])
        if hidden:
            body += f" (+{hidden} more)"
        line = f"{RE_PREFIX}{body} — {market}" if len(props) > 1 else f"{RE_PREFIX}{body}, {market}"
        if len(line) <= max_chars:
            return line

    hidden = len(props) - 1
    body = props[0] + (f" (+{hidden} more)" if hidden else "")
    return f"{RE_PREFIX}{body} — {market}" if len(props) > 1 else f"{RE_PREFIX}{body}, {market}"


def prose_property_list(properties, max_named=RE_LIST_SOFT_CAP):
    """Body-prose property list. Mirrors the Re: line's truncation so the two
    never disagree about how many properties the letter is about.

    Returns (text, property_word) — property_word is "property" or "properties"
    and must be used for BOTH body mentions.
    """
    props = list(properties)
    word = "property" if len(props) == 1 else "properties"
    if len(props) == 1:
        return props[0], word
    if len(props) == 2:
        return f"{props[0]} and {props[1]}", word
    if len(props) <= max_named:
        return ", ".join(props[:-1]) + f", and {props[-1]}", word
    shown = props[:max_named]
    n = len(props) - max_named
    tail = "one other nearby" if n == 1 else f"{n} others nearby"
    return ", ".join(shown) + f", and {tail}", word


def split_address_block(mail_name, street, city_state_zip, max_chars=MAX_LINE_CHARS):
    """Return address-block lines, none of which wrap.

    Guards the second observed overflow mode: the Tier-0 mailing parse appends
    trustee/attention text ("CO Trustees Et Al") to the street line, producing an
    82-character line that wraps and costs the letter a line it does not have.
    Trailing capacity/attention text is split onto its own line instead.
    """
    ATTN_MARKERS = (" CO Trustees", " Co Trustees", " Trustees Et Al", " Et Al",
                    " C/O ", " Attn ", " ATTN ")

    mail_name = " ".join(mail_name.split())
    street = " ".join(street.split())
    attn = None

    # The Tier-0 parse often prefixes the street field with the mailing name
    # repeated, then a capacity phrase, then the actual street. Peel both off.
    if street.lower().startswith(mail_name.lower()):
        street = street[len(mail_name):].strip()

    for marker in ATTN_MARKERS:
        m = marker.strip()
        if street.lower().startswith(m.lower()):
            rest = street[len(m):].strip()
            # capacity phrase runs until the first token that starts a street
            # number (a digit) or a PO Box
            i = 0
            for i, tok in enumerate(rest.split()):
                if tok[0].isdigit() or tok.lower().startswith(("po", "p.o")):
                    break
            else:
                i = len(rest.split())
            toks = rest.split()
            attn = " ".join([m] + toks[:i]).strip()
            street = " ".join(toks[i:]).strip()
            break

    lines = [mail_name]
    if attn:
        lines.append(attn)
    if street:
        lines.append(street)
    lines.append(city_state_zip.strip())

    over = [l for l in lines if len(l) > max_chars]
    if over:
        raise ValueError(f"address block still wraps after split: {over!r}")
    return lines


def tighten_for_overflow(spacing):
    """Per-letter fallback: return a tightened copy of a spacing dict."""
    return {k: TIGHTEN.get(v, v) for k, v in spacing.items()}


# --------------------------------------------------------------------------
# Post-generation integrity gate
# --------------------------------------------------------------------------

def verify_pack(pdf_path, expected_letters, has_cover=True):
    """Assert the rendered pack is one letter per page.

    Page count alone is NOT sufficient — it passes when one letter spills to two
    pages while another is short. This checks that every page after the cover
    carries exactly one salutation.

    Returns (ok, problems). Callers should hard-fail on ok=False, the same
    severity as the existing letter-count integrity check.
    """
    import pypdf

    reader = pypdf.PdfReader(pdf_path)
    pages = reader.pages
    expected_pages = expected_letters + (1 if has_cover else 0)
    problems = []

    if len(pages) != expected_pages:
        problems.append(
            f"page count {len(pages)} != expected {expected_pages} "
            f"({expected_letters} letters + {'1 cover' if has_cover else 'no cover'})"
        )

    start = 1 if has_cover else 0
    for i in range(start, len(pages)):
        text = pages[i].extract_text() or ""
        n = text.count("Dear ")
        if n == 0:
            problems.append(f"page {i+1}: no salutation — previous letter overflowed onto it")
        elif n > 1:
            problems.append(f"page {i+1}: {n} salutations — two letters share a page")
        if "Dear Property Owner" in text:
            problems.append(f"page {i+1}: retired generic salutation present")

    return (not problems), problems
