#!/usr/bin/env python3
"""Extract revisions from a .docx REGARDLESS of how they are encoded.

Why this exists
---------------
Workflow 2 and legal-intelligence Module 6 both used to assume "DOCX with tracked
changes" — i.e. OOXML <w:ins>/<w:del> elements. That assumption is wrong for a large
share of the paper ORA actually receives. Law firms running Litera Compare (formerly
DeltaView / Change-Pro), Workshare Compare, or Word's own "Compare Documents" ship a
FLATTENED document in which revisions are ordinary runs carrying strikethrough or
underline CHARACTER FORMATTING. Such a file contains ZERO <w:ins>/<w:del> elements.

A session that greps for <w:ins> on one of those files finds nothing and concludes
"seller returned it clean / accepted everything." That is a false negative on the
entire redline.

    Origin: 2026-07-31, 754 Old State Route 74. Seller's counsel (KMK Law) delivered
    "PSA -- 754 Old State Rd Seller Redline 07-31-2026.docx" — a Litera Compare
    output with 0 tracked changes and 29 real revisions encoded as red strikethrough
    and blue double-underline. A naive tracked-change parse returned nothing.

Second, subtler payoff: a compare-tool summary block names the BASELINE the other
side compared against. At 754 that block read "Original DMS: … Purchaser Clean
07-22-2026.docx" — which is what proved seller had ACCEPTED the whole 07-22 package
rather than merely declining to comment on it. Always read the base.

What counts as a revision here
------------------------------
  * <w:ins>/<w:del>/<w:moveTo>/<w:moveFrom> anywhere in the document, headers,
    footers, footnotes or endnotes
  * compare-tool character formatting (strikethrough / coloured underline)
  * counsel COMMENTS in word/comments.xml — a "PSA with comments" file carries no
    revisions at all and must not be reported as clean

A document may carry MORE THAN ONE encoding at once (a compare output that counsel
then tracked-edited before sending). All present encodings are reported; none is
allowed to mask another.

Usage
-----
    python extract_revisions.py FILE.docx                 # detect + report
    python extract_revisions.py FILE.docx --json          # machine-readable
    python extract_revisions.py FILE.docx --quiet         # summary only, no bodies

Exit codes
----------
    0  revisions and/or comments found
    1  file genuinely clean
    2  AMBIGUOUS — clean by every detector, but filename/content says it should not
       be. Treat as a hard stop and inspect by eye before reporting "no changes."
    3  usage / read error

Stdlib only (zipfile + ElementTree). No python-docx, no lxml. Python 3.8+.
"""
from __future__ import annotations

import json
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

SUMMARY_MARKERS = (
    "summary report", "litera compare", "workshare compare", "deltaview",
    "change-pro", "document comparison done on",
)
EXPECT_REVISIONS_RE = re.compile(
    r"redline|black\s*line|blackline|compare|markup|marked[\s_-]*up|tracked|revis|comment",
    re.IGNORECASE,
)
NEUTRAL_COLORS = {None, "", "auto", "000000", "FFFFFF"}
REVISION_TAGS = (W + "ins", W + "del", W + "moveTo", W + "moveFrom")
KIND_OF = {W + "ins": "INSERT", W + "del": "DELETE",
           W + "moveTo": "MOVE-TO", W + "moveFrom": "MOVE-FROM"}
# Every part that can carry tracked changes, not just the body.
REVISION_PARTS = ("word/document.xml", "word/footnotes.xml", "word/endnotes.xml")
HEADER_FOOTER_RE = re.compile(r"^word/(header|footer)\d*\.xml$")


def _parts(z: zipfile.ZipFile) -> list:
    names = [n for n in REVISION_PARTS if n in z.namelist()]
    names += sorted(n for n in z.namelist() if HEADER_FOOTER_RE.match(n))
    return names


def _run_text(run: ET.Element) -> str:
    out = []
    for node in run.iter():
        if node.tag in (W + "t", W + "delText"):
            out.append(node.text or "")
        elif node.tag == W + "tab":
            out.append("\t")
        elif node.tag in (W + "br", W + "cr"):
            out.append(" ")
    return "".join(out)


def _run_format(run: ET.Element) -> dict:
    rPr = run.find(W + "rPr")
    if rPr is None:
        return {"strike": False, "underline": None, "color": None, "style": None}
    u = rPr.find(W + "u")
    color = rPr.find(W + "color")
    style = rPr.find(W + "rStyle")
    return {
        "strike": (rPr.find(W + "strike") is not None)
        or (rPr.find(W + "dstrike") is not None),
        "underline": u.get(W + "val") if u is not None else None,
        "color": color.get(W + "val") if color is not None else None,
        "style": style.get(W + "val") if style is not None else None,
    }


def _walk_runs(el: ET.Element, state=None):
    """Yield (run, kind_or_None) in document order, tracking <w:ins>/<w:del> ancestry."""
    for child in el:
        tag = child.tag
        if tag == W + "r":
            yield child, state
        elif tag in REVISION_TAGS:
            yield from _walk_runs(child, KIND_OF[tag])
        elif tag == W + "rPr":
            continue
        else:
            yield from _walk_runs(child, state)


def parse_summary(paragraphs: list) -> tuple:
    """Locate a compare-tool summary block -> (start_index, fields)."""
    start = None
    for i, text in enumerate(paragraphs):
        low = text.strip().lower()
        if any(m in low for m in SUMMARY_MARKERS):
            start = i
            break
    if start is None:
        return None, {}

    tail = paragraphs[start:]
    fields = {}
    for i, text in enumerate(tail):
        t = text.strip()
        low = t.lower()
        # Tool name first: Litera emits name and "comparison done on" in ONE paragraph,
        # so an elif chain that tests the timestamp first never records the tool.
        if low.startswith(("litera", "workshare", "deltaview", "change-pro")):
            fields.setdefault("compare_tool", t)
        if "comparison done on" in low:
            fields.setdefault("compare_run_at", t)
        if low.startswith("original") and ":" in t:
            fields["compare_base"] = t.split(":", 1)[1].strip()
        elif low.startswith("modified") and ":" in t:
            fields["compare_modified"] = t.split(":", 1)[1].strip()
        for label in ("Add", "Delete", "Move From", "Move To", "Total Changes"):
            if t.rstrip(":").strip().lower() == label.lower() and i + 1 < len(tail):
                nxt = tail[i + 1].strip()
                if nxt.isdigit():
                    fields.setdefault("tool_counts", {})[label] = int(nxt)
    return start, fields


def _comments(z: zipfile.ZipFile) -> list:
    if "word/comments.xml" not in z.namelist():
        return []
    root = ET.fromstring(z.read("word/comments.xml"))
    out = []
    for c in root.iter(W + "comment"):
        txt = "".join(n.text or "" for n in c.iter(W + "t")).strip()
        out.append({
            "author": c.get(W + "author") or "?",
            "date": c.get(W + "date") or "",
            "text": txt,
        })
    return out


def extract(path: Path) -> dict:
    with zipfile.ZipFile(path) as z:
        if "word/document.xml" not in z.namelist():
            raise KeyError("word/document.xml")
        doc = ET.fromstring(z.read("word/document.xml"))
        part_roots = [(n, ET.fromstring(z.read(n))) for n in _parts(z)]
        comments = _comments(z)

    paras = list(doc.iter(W + "p"))
    para_text = ["".join(_run_text(r) for r, _ in _walk_runs(p)) for p in paras]
    summary_start, summary = parse_summary(para_text)
    limit = summary_start if summary_start is not None else len(paras)

    # ---- encoding 1: OOXML tracked changes (all parts) ---------------------
    tracked = []
    authors = {}
    para_mark_revisions = 0
    for part_name, root in part_roots:
        for idx, p in enumerate(root.iter(W + "p")):
            pPr = p.find(W + "pPr")
            if pPr is not None:
                rPr = pPr.find(W + "rPr")
                if rPr is not None and (
                    rPr.find(W + "ins") is not None or rPr.find(W + "del") is not None
                ):
                    para_mark_revisions += 1
            for run, kind in _walk_runs(p):
                if not kind:
                    continue
                txt = _run_text(run)
                if txt:
                    tracked.append({"part": part_name, "para": idx,
                                    "kind": kind, "text": txt})
        for el in root.iter():
            if el.tag in REVISION_TAGS:
                a = el.get(W + "author")
                if a:
                    authors[a] = authors.get(a, 0) + 1

    # ---- encoding 2: compare-tool character formatting ---------------------
    # Deletions are unambiguous (strikethrough). Insertions are the trap: ordinary
    # section HEADINGS and HYPERLINKS are underlined and often coloured, so
    # "underlined and coloured" alone reports a clean document as a redline.
    # Gate on a positive deletion signal instead — a compare output that contains
    # insertions essentially always contains at least one deletion — and prefer
    # double underline when the document uses it.
    strike_runs, dbl_colored, cand_ins = [], [], []
    for idx, p in enumerate(paras[:limit]):
        for run, kind in _walk_runs(p):
            if kind:
                continue  # already captured as a real tracked change
            f = _run_format(run)
            txt = _run_text(run)
            if not txt.strip():
                continue
            if f["style"] == "Hyperlink":
                continue
            if f["strike"]:
                strike_runs.append((idx, txt, f["color"]))
            elif f["underline"] and f["color"] not in NEUTRAL_COLORS:
                cand_ins.append((idx, txt, f["color"], f["underline"]))
                if f["underline"] == "double":
                    dbl_colored.append((idx, txt, f["color"]))

    compare_mode = bool(strike_runs) or len(dbl_colored) >= 3
    formatted = []
    if compare_mode:
        prefer_double = bool(dbl_colored)
        for idx, txt, color in strike_runs:
            formatted.append({"part": "word/document.xml", "para": idx,
                              "kind": "DELETE", "text": txt, "color": color})
        for idx, txt, color, uval in cand_ins:
            if prefer_double and uval != "double":
                continue
            formatted.append({"part": "word/document.xml", "para": idx,
                              "kind": "INSERT", "text": txt, "color": color})
        formatted.sort(key=lambda r: r["para"])

    # ---- classify ----------------------------------------------------------
    encodings = []
    if tracked:
        encodings.append("ooxml-tracked-changes")
    if formatted:
        encodings.append("compare-tool-formatting")
    if comments:
        encodings.append("comments")
    revisions = tracked + formatted
    if not encodings:
        encodings = ["clean"]

    name_expects = bool(EXPECT_REVISIONS_RE.search(path.name))
    is_clean = not revisions and not comments
    ambiguous = is_clean and (name_expects or summary_start is not None)

    def _count(kind):
        return sum(1 for r in revisions if r["kind"] == kind)

    return {
        "file": path.name,
        "encodings": encodings,
        "mixed": len([e for e in encodings if e != "clean"]) > 1,
        "ambiguous": ambiguous,
        "filename_expects_revisions": name_expects,
        "paragraph_count": len(paras),
        "content_paragraphs": limit,
        "revision_count": len(revisions),
        "insert_runs": _count("INSERT"),
        "delete_runs": _count("DELETE"),
        "move_runs": _count("MOVE-TO") + _count("MOVE-FROM"),
        "paragraph_mark_revisions": para_mark_revisions,
        "comment_count": len(comments),
        "authors": authors,
        "revision_colors": {
            "deletion": sorted({c for _, _, c in strike_runs if c}),
            "insertion": sorted({r["color"] for r in formatted
                                 if r["kind"] == "INSERT" and r.get("color")}),
        },
        "summary_block": summary,
        "comments": comments,
        "revisions": revisions,
        "paragraphs": para_text,
    }


def render(res: dict, quiet: bool = False) -> str:
    L = []
    add = L.append
    add("=" * 78)
    add("REVISION EXTRACTION — {}".format(res["file"]))
    add("=" * 78)
    add("Encoding(s)       : {}".format(", ".join(res["encodings"])))
    add("Paragraphs        : {} ({} before tool chrome)".format(
        res["paragraph_count"], res["content_paragraphs"]))
    add("Revision runs     : {} ({} insert / {} delete{})".format(
        res["revision_count"], res["insert_runs"], res["delete_runs"],
        " / {} move".format(res["move_runs"]) if res["move_runs"] else ""))
    if res["paragraph_mark_revisions"]:
        add("Para-mark revs    : {} (paragraph splits/merges — counted separately "
            "from text runs)".format(res["paragraph_mark_revisions"]))
    if res["comment_count"]:
        add("Comments          : {}".format(res["comment_count"]))
    if res["authors"]:
        add("Authors           : " + ", ".join(
            "{} ({})".format(k, v) for k, v in sorted(res["authors"].items())))
    if "compare-tool-formatting" in res["encodings"]:
        rc = res["revision_colors"]
        add("Revision palette  : deletion={} insertion={}".format(
            rc["deletion"] or "—", rc["insertion"] or "—"))

    if res["mixed"]:
        add("")
        add("!! MIXED ENCODING — this document carries more than one revision")
        add("!! mechanism at once ({}). Both are reported".format(
            ", ".join(e for e in res["encodings"] if e != "clean")))
        add("!! above; do not analyse one and assume it is the whole redline.")

    s = res.get("summary_block") or {}
    if s:
        add("")
        add("-- COMPARE-TOOL SUMMARY (read this before anything else) " + "-" * 20)
        for key, label in (("compare_tool", "tool    "), ("compare_run_at", "run     "),
                           ("compare_base", "BASE    "),
                           ("compare_modified", "MODIFIED")):
            if s.get(key):
                add("  {} : {}".format(label, s[key]))
        if s.get("tool_counts"):
            add("  tally    : " + ", ".join(
                "{}={}".format(k, v) for k, v in s["tool_counts"].items()))
        add("")
        add("  The BASE is the counterparty's own statement of what it compared")
        add("  against. Every provision NOT marked below was accepted from that")
        add("  base — not merely left uncommented. Confirm BASE is the draft ORA")
        add("  actually sent; if it is not, the counterparty reviewed stale paper.")
        if s.get("tool_counts"):
            add("  Cite the tool's tally externally, not the run counts above —")
            add("  they count differently (formatting runs vs. merged changes).")

    if res["ambiguous"]:
        add("")
        add("!! AMBIGUOUS — no revisions or comments found in ANY supported")
        add("!! encoding, but the filename or content indicates there should be.")
        add("!! Do NOT report this document as 'clean' or 'fully accepted'")
        add("!! without opening it by eye.")

    if not quiet and res["comments"]:
        add("")
        add("-- COMMENTS " + "-" * 65)
        for c in res["comments"]:
            add("   [{}] {}".format(c["author"], c["text"][:220]))

    if not quiet and res["revisions"]:
        add("")
        add("-- REVISIONS BY PARAGRAPH " + "-" * 51)
        by_para = {}
        for r in res["revisions"]:
            by_para.setdefault((r["part"], r["para"]), []).append(r)
        for key in sorted(by_para):
            part, pid = key
            add("")
            add("[{}para {}]".format(
                "" if part == "word/document.xml" else part + " ", pid))
            for r in by_para[key]:
                tag = {"INSERT": "+", "DELETE": "-"}.get(r["kind"], "~")
                add("   {} {!r}".format(tag, r["text"]))
            if part == "word/document.xml" and pid < len(res["paragraphs"]):
                ctx = res["paragraphs"][pid].strip()
                if ctx:
                    add("   ctx: {}{}".format(
                        ctx[:300], "…" if len(ctx) > 300 else ""))
    return "\n".join(L)


KNOWN_FLAGS = {"--json", "--quiet"}


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
        res = extract(path)
    except (zipfile.BadZipFile, KeyError, ET.ParseError, OSError) as exc:
        print("error: could not read {} as a .docx: {}".format(path.name, exc),
              file=sys.stderr)
        return 3

    if "--json" in flags:
        res.pop("paragraphs", None)
        print(json.dumps(res, indent=2))
    else:
        print(render(res, quiet="--quiet" in flags))

    if res["ambiguous"]:
        return 2
    return 0 if (res["revision_count"] or res["comment_count"]) else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
