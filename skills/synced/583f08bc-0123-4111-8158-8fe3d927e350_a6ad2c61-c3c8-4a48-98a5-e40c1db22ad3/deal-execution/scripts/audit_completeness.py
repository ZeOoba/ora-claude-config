#!/usr/bin/env python3
"""Audit a contract .docx for the defects that survive human proofreading.

Why this exists
---------------
The quality gate asked whether exhibits were "attached." That is the wrong question.
An exhibit can be present, referenced, correctly titled, and completely EMPTY — and
because reviewers read the body and skim the back matter, an empty exhibit survives
round after round while the body increasingly depends on it.

    Origin: 2026-08-01, 754 Old State Route 74. Exhibit B (Rent Roll) was a heading
    and nothing else — no table, no image, no text — across four drafting rounds and
    two law firms. Meanwhile §7 defined "Leases" by reference to it, and §15.1.2
    confirmed the absence of renewal/purchase options "except as expressly set forth
    on the rent roll attached as Exhibit B." The single provision protecting the
    deal's value thesis pointed at a blank page. Exhibit A carried a parcel number
    but no legal description; §15.1's knowledge-party definition was an open blank.

Four checks, all mechanical:
  1. EXHIBIT POPULATION  — does each exhibit contain anything at all?
  2. CROSS-REFERENCES    — every exhibit cited in the body exists, and vice versa;
                           every section cross-reference resolves.
  3. UNFILLED BLANKS     — placeholder runs, [TBD], and open definitions, split into
                           body blanks (defects) and signature-block blanks (expected).
  4. KNOWLEDGE PARTY     — the definition that silently voids or unbounds every
                           knowledge-qualified representation when left blank.

Usage
-----
    python audit_completeness.py CONTRACT.docx
    python audit_completeness.py CONTRACT.docx --json

Exit codes
----------
    0  no blocking defects
    1  blocking defects found
    3  usage / read error

Stdlib only. Python 3.8+.
"""
from __future__ import annotations

import json
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
A_BLIP = "{http://schemas.openxmlformats.org/drawingml/2006/main}blip"
V_IMAGE = "{urn:schemas-microsoft-com:vml}imagedata"

SUMMARY_MARKERS = (
    "summary report", "litera compare", "workshare compare", "deltaview",
    "change-pro", "document comparison done on",
)
# "signature page" alone also matches the Counterparts boilerplate ("…signature pages
# may be delivered by email") in mid-document, which would silently downgrade every
# later body blank — including an open Purchase Price — to an expected signature blank.
SIGNATURE_START_RE = re.compile(
    r"in\s+witness\s+whereof|^\s*\[?signature\s+(page|and\s+exhibit\s+pages)\s+"
    r"(follows?|to\s+follow)", re.IGNORECASE)

EXHIBIT_HEAD_RE = re.compile(r"^\s*EXHIBIT\s+([A-Z](?:-\d+)?)\b\s*$", re.IGNORECASE)
# "Exhibit A" and also "Exhibits A, B and C"
EXHIBIT_REF_RE = re.compile(r"\bExhibits?\s+((?:[A-Z](?:-\d+)?)(?:\s*,\s*(?:and\s+)?"
                            r"[A-Z](?:-\d+)?|\s+and\s+[A-Z](?:-\d+)?)*)\b")
EXHIBIT_LETTER_RE = re.compile(r"[A-Z](?:-\d+)?")
SECTION_REF_RE = re.compile(r"(?:Section|Paragraph|Article|§)\s*(\d+(?:\.\d+)*)")
SECTION_HEAD_RE = re.compile(r"^\s*(\d+(?:\.\d+)*)\s*[.—-]?\s*[A-Z(]")

# Law-firm DMS stamps ("15744530.v2", or two concatenated by a compare tool) are the
# only content in many otherwise-empty exhibit ranges. Counting them as content
# downgrades a BLOCKING empty exhibit to advisory THIN — and every iManage document
# carries one.
DMS_STAMP_RE = re.compile(r"^(?:\d{6,}\.v\d+\s*)+$")

# Statutory citations look exactly like internal cross-references ("Section 1445",
# "§§ 6901", "R.C. § 5302.07", "Section 1031 of the Code"). Suppress ONLY on a
# positive statute signal — never on "the number looks too big," which silently
# swallows the real dangling references this check exists to find.
STATUTE_BEFORE_RE = re.compile(
    r"(?:U\.?\s?S\.?\s?C|C\.?\s?F\.?\s?R|\bR\.?C\.?|O\.?R\.?C|I\.?R\.?C|Revenue Code"
    r"|Internal Revenue|Ohio Revised|Public Law|Stat\.|U\.S\.C\.A|§§).{0,45}$",
    re.IGNORECASE)
STATUTE_AFTER_RE = re.compile(
    r"^\s*(?:\([a-z0-9)(]+\)\s*)?(?:et\s+seq|of\s+the\s+(?:Internal\s+Revenue\s+)?Code"
    r"|of\s+the\s+Ohio\s+Revised|U\.?\s?S\.?\s?C|of\s+Title\s+\d)", re.IGNORECASE)
# Above this, a reference is reported as a LIKELY CITATION (advisory) rather than a
# dangling internal reference — reported either way, never silently dropped.
MAX_PLAUSIBLE_SECTION = 100

BLANK_PATTERNS = [
    (re.compile(r"_{3,}"), "underscore placeholder"),
    (re.compile(r"\[\s*(?:TBD|TBA|XXX+|insert|to come|•)\s*\]", re.I), "bracket placeholder"),
    (re.compile(r"\bTBD\b"), "TBD"),
    (re.compile(r"\$\s*_{2,}"), "open dollar amount"),
    (re.compile(r"\[\s*\]"), "empty bracket"),
]
KNOWLEDGE_DEF_RE = re.compile(
    r"(?:to\s+(?:the\s+)?(?:Seller|Purchaser|Buyer)(?:'s|’s)?\s+(?:actual\s+)?knowledge"
    r"|knowledge\s+of\s+(?:the\s+)?(?:Seller|Purchaser|Buyer))", re.IGNORECASE)


def _load(path: Path) -> ET.Element:
    with zipfile.ZipFile(path) as z:
        if "word/document.xml" not in z.namelist():
            raise KeyError("word/document.xml")
        return ET.fromstring(z.read("word/document.xml"))


def _text_of(el: ET.Element, include_deleted: bool = False) -> str:
    """Visible text. Deleted text is EXCLUDED by default — text the counterparty
    struck must not count toward exhibit population or trip blank detection (a
    struck '____' replaced by a real value is not an unfilled blank)."""
    out = []
    for n in el.iter():
        if n.tag == W + "t":
            out.append(n.text or "")
        elif n.tag == W + "delText" and include_deleted:
            out.append(n.text or "")
        elif n.tag == W + "tab":
            out.append(" ")
    return "".join(out)


def _count_media(el: ET.Element) -> int:
    return sum(1 for n in el.iter() if n.tag in (A_BLIP, V_IMAGE))


def _blocks(root: ET.Element) -> list:
    body = root.find(W + "body")
    if body is None:
        return []
    out = []
    for el in body:
        tag = el.tag.split("}")[-1]
        out.append((tag if tag in ("p", "tbl") else "other", el))
    return out


def _exhibit_heading(kind: str, el: ET.Element, text: str):
    """Exhibit letter if this block is an exhibit heading, else None. A heading placed
    inside a table is still a heading."""
    m = EXHIBIT_HEAD_RE.match(text.strip())
    if m:
        return m.group(1).upper()
    if kind == "tbl":
        for p in el.iter(W + "p"):
            m = EXHIBIT_HEAD_RE.match(_text_of(p).strip())
            if m:
                return m.group(1).upper()
    return None


def audit(path: Path) -> dict:
    root = _load(path)
    blocks = _blocks(root)
    texts = [_text_of(el) for _, el in blocks]

    chrome_at = len(blocks)
    for i, t in enumerate(texts):
        if any(m in t.strip().lower() for m in SUMMARY_MARKERS):
            chrome_at = i
            break
    limit = chrome_at

    sig_at = limit
    for i in range(limit):
        if SIGNATURE_START_RE.search(texts[i].strip()):
            sig_at = i
            break

    # ---- 1. exhibit population -------------------------------------------
    heads = []
    for i in range(limit):
        letter = _exhibit_heading(blocks[i][0], blocks[i][1], texts[i])
        if letter:
            heads.append((i, letter))

    exhibits = []
    for n, (start, letter) in enumerate(heads):
        end = heads[n + 1][0] if n + 1 < len(heads) else limit
        chars = media = tables = 0
        caption = ""
        for j in range(start + 1, end):
            kind, el = blocks[j]
            t = texts[j].strip()
            media += _count_media(el)
            if kind == "tbl":
                tables += 1
                chars += len(t)
                continue
            if DMS_STAMP_RE.match(t):
                continue  # law-firm document stamp, not exhibit content
            if not caption and t and (t.startswith("(") or len(t) < 40) \
                    and j <= start + 2:
                caption = t
                continue
            chars += len(t)
        populated = bool(chars or media or tables)
        exhibits.append({
            "letter": letter, "caption": caption, "block": start,
            "text_chars": chars, "images": media, "tables": tables,
            "populated": populated,
            "thin": populated and chars < 60 and not tables,
        })

    # ---- 2. cross-references ---------------------------------------------
    body_limit = heads[0][0] if heads else limit
    referenced = {}
    for i in range(body_limit):
        for m in EXHIBIT_REF_RE.finditer(texts[i]):
            for letter in EXHIBIT_LETTER_RE.findall(m.group(1)):
                referenced[letter] = referenced.get(letter, 0) + 1
    present = {e["letter"] for e in exhibits}
    dangling_exhibit = sorted(set(referenced) - present)
    orphan_exhibit = sorted(present - set(referenced))

    section_heads = set()
    for i in range(body_limit):
        m = SECTION_HEAD_RE.match(texts[i].strip())
        if m:
            section_heads.add(m.group(1))
            # A heading "9.2" also establishes that article 9 exists.
            parts = m.group(1).split(".")
            for k in range(1, len(parts)):
                section_heads.add(".".join(parts[:k]))

    dangling_section, likely_citations = [], []
    seen = set()
    for i in range(body_limit):
        t = texts[i]
        for m in SECTION_REF_RE.finditer(t):
            ref = m.group(1)
            if ref in seen or ref in section_heads:
                continue
            if STATUTE_BEFORE_RE.search(t[max(0, m.start() - 60):m.start()]):
                continue
            if STATUTE_AFTER_RE.match(t[m.end():m.end() + 45]):
                continue
            seen.add(ref)
            head = int(ref.split(".")[0])
            (likely_citations if head > MAX_PLAUSIBLE_SECTION
             else dangling_section).append(ref)
    dangling_section.sort(key=lambda x: [int(p) for p in x.split(".")])
    likely_citations.sort(key=lambda x: [int(p) for p in x.split(".")])

    # ---- 3. unfilled blanks ----------------------------------------------
    body_blanks, sig_blanks = [], []
    for i in range(limit):
        t = texts[i]
        if not t.strip() or DMS_STAMP_RE.match(t.strip()):
            continue
        for rx, label in BLANK_PATTERNS:
            m = rx.search(t)
            if not m:
                continue
            lo, hi = max(0, m.start() - 70), min(len(t), m.end() + 70)
            entry = {"block": i, "kind": label,
                     "context": t[lo:hi].strip().replace("\n", " ")}
            (sig_blanks if i >= sig_at else body_blanks).append(entry)
            break

    # ---- 4. knowledge party ----------------------------------------------
    knowledge = {"found": False, "unfilled": False, "context": ""}
    for i in range(min(sig_at, limit)):
        t = texts[i]
        if not KNOWLEDGE_DEF_RE.search(t):
            continue
        if re.search(r"shall\s+mean|means|refers\s+to", t, re.I):
            knowledge["found"] = True
            if re.search(r"_{3,}", t):
                knowledge["unfilled"] = True
                knowledge["context"] = t.strip()[:260]
            break

    empty = [e for e in exhibits if not e["populated"]]
    blocking = bool(empty or dangling_exhibit or dangling_section
                    or body_blanks or knowledge["unfilled"])

    return {
        "file": path.name,
        "blocks": len(blocks),
        "exhibits": exhibits,
        "empty_exhibits": [e["letter"] for e in empty],
        "thin_exhibits": [e["letter"] for e in exhibits if e["thin"]],
        "exhibit_refs": referenced,
        "dangling_exhibit_refs": dangling_exhibit,
        "unreferenced_exhibits": orphan_exhibit,
        "dangling_section_refs": dangling_section,
        "likely_statutory_citations": likely_citations,
        "body_blanks": body_blanks,
        "signature_blanks": sig_blanks,
        "knowledge_party": knowledge,
        "blocking": blocking,
    }


def render(r: dict) -> str:
    L = []
    add = L.append
    add("=" * 78)
    add("COMPLETENESS AUDIT — {}".format(r["file"]))
    add("=" * 78)

    add("")
    add("-- 1. EXHIBIT POPULATION " + "-" * 52)
    if not r["exhibits"]:
        add("   no exhibit headings found")
    for e in r["exhibits"]:
        flag = ("EMPTY   <-- BLOCKING" if not e["populated"]
                else "THIN    <-- verify sufficiency" if e["thin"] else "ok")
        cap = " {}".format(e["caption"]) if e["caption"] else ""
        add("   Exhibit {}{:<30} chars={:<6} img={} tbl={}  {}".format(
            e["letter"], cap, e["text_chars"], e["images"], e["tables"], flag))
    if r["empty_exhibits"]:
        add("")
        add("   !! EMPTY: {} — an exhibit the body relies on is a blank page.".format(
            ", ".join(r["empty_exhibits"])))
        add("   !! Trace what depends on it before signing: definitions,")
        add("   !! representation carve-outs and delivery obligations commonly")
        add("   !! hang off exhibits and fail silently when they are blank.")
    if r["thin_exhibits"]:
        add("   ?  THIN: {} — ask whether a third party could draft from it. A "
            "recordable".format(", ".join(r["thin_exhibits"])))
        add("      instrument cannot be prepared from an aerial markup, nor a deed "
            "from a parcel number.")

    add("")
    add("-- 2. CROSS-REFERENCES " + "-" * 54)
    add("   exhibits referenced in body : {}".format(
        ", ".join("{}({})".format(k, v)
                  for k, v in sorted(r["exhibit_refs"].items())) or "—"))
    if r["dangling_exhibit_refs"]:
        add("   !! REFERENCED BUT ABSENT   : {}".format(
            ", ".join(r["dangling_exhibit_refs"])))
    if r["unreferenced_exhibits"]:
        add("   ?  present but never cited : {}".format(
            ", ".join(r["unreferenced_exhibits"])))
    if r["dangling_section_refs"]:
        add("   !! SECTION REFS THAT DO NOT RESOLVE: {}".format(
            ", ".join(r["dangling_section_refs"])))
    if r["likely_statutory_citations"]:
        add("   ?  probable statute cites (advisory): {}".format(
            ", ".join(r["likely_statutory_citations"])))
    if not (r["dangling_exhibit_refs"] or r["dangling_section_refs"]):
        add("   all exhibit and section cross-references resolve")

    add("")
    add("-- 3. UNFILLED BLANKS " + "-" * 55)
    if not r["body_blanks"]:
        add("   none in the body")
    for b in r["body_blanks"]:
        add("   !! [block {}] {}".format(b["block"], b["kind"]))
        add("      …{}…".format(b["context"]))
    if r["signature_blanks"]:
        add("   ({} blank(s) in the signature block — expected, but must be "
            "completed".format(len(r["signature_blanks"])))
        add("    consistently at execution)")

    add("")
    add("-- 4. KNOWLEDGE PARTY " + "-" * 55)
    k = r["knowledge_party"]
    if not k["found"]:
        add("   no knowledge-party definition located (confirm by eye if the")
        add("   representations are knowledge-qualified)")
    elif k["unfilled"]:
        add("   !! UNFILLED — every knowledge-qualified representation in this")
        add("   !! document is unbounded or void until a named individual and")
        add("   !! title are inserted. Signing blocker.")
        add("      …{}…".format(k["context"]))
    else:
        add("   defined")

    add("")
    add("=" * 78)
    add("BLOCKING DEFECTS PRESENT" if r["blocking"] else "NO BLOCKING DEFECTS")
    add("=" * 78)
    return "\n".join(L)


KNOWN_FLAGS = {"--json"}


def main(argv: list) -> int:
    args = [a for a in argv[1:] if not a.startswith("--")]
    flags = {a for a in argv[1:] if a.startswith("--")}
    unknown = flags - KNOWN_FLAGS
    if unknown:
        print("error: unknown flag(s): {}".format(", ".join(sorted(unknown))),
              file=sys.stderr)
        return 3
    if not args:
        print(__doc__)
        return 3
    path = Path(args[0])
    if not path.exists():
        print("error: no such file: {}".format(path), file=sys.stderr)
        return 3
    try:
        r = audit(path)
    except (zipfile.BadZipFile, KeyError, ET.ParseError, OSError) as exc:
        print("error: could not read {} as a .docx: {}".format(path.name, exc),
              file=sys.stderr)
        return 3
    print(json.dumps(r, indent=2) if "--json" in flags else render(r))
    return 1 if r["blocking"] else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
