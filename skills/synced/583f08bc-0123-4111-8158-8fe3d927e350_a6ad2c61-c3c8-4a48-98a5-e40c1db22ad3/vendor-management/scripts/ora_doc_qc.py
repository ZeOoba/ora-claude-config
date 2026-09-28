#!/usr/bin/env python3
"""
ora_doc_qc.py — shared extraction, check-registry, and report harness for
Oxford Realty Advisors document QC scanners.

Factored out of pma_qc.py (2026-08-17) after discovering that listing_qc.py
(listing-agreement-qc v1.0) scores a scanned, no-text-layer PDF as CLEAN — the
KRG Management Agreement extracts to an empty string via pdftotext, an empty
string trips zero checks, and a QC tool reporting "clean" on a document it
never read is the worst possible failure mode for a pre-signature gate.
pma_qc.py closed that gap with an OCR fallback + hard UNREADABLE floor. This
module makes that fix, plus the extraction/severity/report machinery all three
scanners already duplicate, a single maintained implementation instead of
three copies that drift.

THREE CONSUMERS, THREE DIFFERENT SHAPES — read this before assuming a drop-in:

  scripts/listing_qc.py   (listing-agreement-qc)  25 checks, detail-string style,
                           has PDF via pdftotext, NO OCR fallback, NO unreadable
                           gate — same false-clean risk pma_qc.py fixed for PMAs.
                           Already committed to the ora-skills repo (PR #44,
                           2026-08-17) — only its retrofit onto this module is
                           pending, not the file's existence.
  scripts/lease_qc.py      (lease-form-qc)         51 checks, BOOLEAN style
                           (id, severity, label, fn(text)->bool), DOCX-ONLY —
                           any non-.docx path (including a PDF) falls through to
                           a raw text() open() with no format detection at all,
                           which garbles a PDF into near-total-failure rather
                           than false-clean, but is still an extraction bug of
                           the same family. Also carries a bespoke footer-text
                           concatenation ([[FOOTER]] marker) for its F18 check
                           that this module supports via extract()'s `footer`
                           meta field so lease_qc.py does not lose it.
  scripts/pma_qc.py        (pma-qc)                32 checks, detail-string
                           style, PDF + OCR fallback + UNREADABLE gate (the
                           reference implementation this module was extracted
                           from).

This module standardizes on the **detail-string style**: a check function
takes a ctx dict and returns None (pass), a string (fail, with that string as
the printed detail), or True (fail, using the check's own title as the
detail — sugar for porting a boolean-style check like lease_qc.py's without
inventing new detail text). It does NOT change what any check tests for; it
only changes the calling convention. Converting lease_qc.py's 51
`lambda t: <bool>` checks to `lambda ctx: <bool test on ctx["t"]> or None` (or
wrapping with `bool_check()` below) is mechanical and covered in the migration
notes at the bottom of this file.

Each tool keeps its OWN CHECKS registry (via new_registry()) — there is
deliberately no shared global list. Cross-tool check ID collisions (pma-qc's
P1 vs listing-agreement-qc's L1 vs lease-form-qc's A1) are fine; they live in
separate registries and are never merged.
"""

import argparse
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

DEFAULT_MIN_WORDS = 150
SEV_ORDER = {"BLOCK": 0, "HIGH": 1, "MED": 2, "LOW": 3}

# ---------------------------------------------------------------- extraction


def _strip_xml(x):
    x = re.sub(r"</w:p>", "\n", x)
    x = re.sub(r"<w:tab/>", "\t", x)
    x = re.sub(r"<[^>]+>", "", x)
    for a, b in (("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"),
                 ("&quot;", '"'), ("&apos;", "'")):
        x = x.replace(a, b)
    return x


def ocr_available():
    return bool(shutil.which("pdftoppm") and shutil.which("tesseract"))


def _ocr_pdf(path, dpi=300, page_timeout=300, raster_timeout=600):
    """Rasterize + OCR a PDF. Returns text or None if the toolchain is
    unavailable or the run fails. This is the fallback path — never assume
    it succeeded; check the returned meta["extraction"] == "ocr"."""
    if not ocr_available():
        return None
    out = []
    with tempfile.TemporaryDirectory() as td:
        stem = os.path.join(td, "pg")
        try:
            subprocess.run(["pdftoppm", "-r", str(dpi), "-png", path, stem],
                           check=True, capture_output=True, timeout=raster_timeout)
            for img in sorted(glob.glob(stem + "*.png")):
                r = subprocess.run(["tesseract", img, "-"],
                                   capture_output=True, timeout=page_timeout)
                out.append(r.stdout.decode("utf8", "replace"))
        except Exception:                                          # noqa: BLE001
            return None
    return "\n".join(out) if out else None


def extract(path, allow_ocr=True, min_words=DEFAULT_MIN_WORDS, want_footer=False):
    """Return (body_text, meta). body_text is None when the document could not
    be read to at least `min_words` words — callers MUST treat that as
    UNREADABLE, never as "zero defects found". This is the single fix this
    module exists to centralize: an empty or near-empty extraction is not a
    clean bill of health, it is a scanner that never read the document.

    meta always carries: format, extraction ("native"|"ocr"), words,
    tracked_changes, comments, strike, headers, footer (if want_footer),
    creator, company, auto_numbered_paras, manual_numbered_paras. DOCX-only
    fields default sanely for PDF/text input (0 / False / "" / None as fits).

    `strike` (bool) flags raw w:strike markup — a compare-tool's visual
    strikethrough, distinct from real OOXML w:ins/w:del tracked changes
    (`tracked_changes`). A caller distinguishing "real tracked changes" from
    "just a diff tool's formatting" needs both signals.
    """
    meta = {"format": None, "extraction": "native", "tracked_changes": 0,
            "comments": False, "strike": False, "headers": "", "footer": "",
            "creator": None, "company": None, "words": 0,
            "auto_numbered_paras": 0, "manual_numbered_paras": 0}
    ext = os.path.splitext(path)[1].lower()

    if ext in (".docx", ".dotx"):
        meta["format"] = "docx"
        with zipfile.ZipFile(path) as z:
            names = z.namelist()
            doc = z.read("word/document.xml").decode("utf8", "replace")
            meta["tracked_changes"] = len(re.findall(r"<w:(ins|del) ", doc))
            meta["comments"] = "word/comments.xml" in names
            meta["strike"] = "w:strike" in doc
            meta["auto_numbered_paras"] = len(re.findall(r"<w:numPr>", doc))
            meta["manual_numbered_paras"] = len(
                re.findall(r"<w:t[^>]*>\s*\d{1,2}\.\s*</w:t>", doc))
            hdr = [_strip_xml(z.read(n).decode("utf8", "replace"))
                   for n in names if re.match(r"word/header\d*\.xml", n)]
            meta["headers"] = " ".join(hdr)
            if want_footer:
                ftr = [_strip_xml(z.read(n).decode("utf8", "replace"))
                       for n in names if re.match(r"word/footer\d*\.xml", n)]
                meta["footer"] = " ".join(ftr)
            if "docProps/core.xml" in names:
                c = z.read("docProps/core.xml").decode("utf8", "replace")
                m = re.search(r"<dc:creator>([^<]*)</dc:creator>", c)
                meta["creator"] = m.group(1) if m else None
            if "docProps/app.xml" in names:
                a = z.read("docProps/app.xml").decode("utf8", "replace")
                m = re.search(r"<Company>([^<]*)</Company>", a)
                meta["company"] = m.group(1) if m else None
            body = _strip_xml(doc)

    elif ext == ".pdf":
        meta["format"] = "pdf"
        body = ""
        if shutil.which("pdftotext"):
            try:
                body = subprocess.run(["pdftotext", "-layout", path, "-"],
                                      capture_output=True,
                                      check=True).stdout.decode("utf8", "replace")
            except Exception:                                      # noqa: BLE001
                body = ""
        if len(body.split()) < min_words and allow_ocr:
            ocr = _ocr_pdf(path)
            if ocr and len(ocr.split()) > len(body.split()):
                body, meta["extraction"] = ocr, "ocr"
    else:
        meta["format"] = "text"
        body = open(path, encoding="utf8", errors="replace").read()

    meta["words"] = len(body.split())
    if meta["words"] < min_words:
        return None, meta
    return body, meta


def norm(t):
    t = (t.replace("’", "'").replace("‘", "'")
          .replace("“", '"').replace("”", '"')
          .replace("–", "-").replace("—", "-").replace("\xa0", " "))
    return re.sub(r"\s+", " ", t)


def has(ctx, pattern):
    return re.search(pattern, ctx["t"], re.I) is not None


def quote(ctx, pattern, width=90):
    m = re.search(pattern, ctx["t"], re.I)
    if not m:
        return ""
    s = max(0, m.start() - 10)
    return '"' + ctx["t"][s:s + width].strip() + '..."'


# ------------------------------------------------------------ check registry

def new_registry():
    """Return (check_decorator, CHECKS_list) private to one tool. Each of the
    three scanners calls this once at module scope so their check IDs never
    collide across tools (pma-qc's P1 and listing-agreement-qc's L1 are
    unrelated and must stay unrelated)."""
    checks = []

    def check(cid, sev, title, pos=None):
        def deco(fn):
            checks.append((cid, sev, title, pos, fn))
            return fn
        return deco

    return check, checks


def bool_check(cid, sev, title, test, pos=None):
    """Port a lease_qc.py-style boolean check: `test` takes the normalized
    text and returns True when the DEFECT IS PRESENT. Returns a
    (id, sev, title, pos, fn) tuple in the standard 5-tuple shape, using the
    title itself as the detail (matches lease_qc.py's existing report output,
    which prints only the label — no per-check computed detail today)."""
    def fn(ctx):
        return True if test(ctx["t"]) else None
    return (cid, sev, title, pos, fn)


def unfilled_token_check(cid="TOK", sev="BLOCK", title="Unfilled template tokens remain",
                          pos=None, pattern=r"\[[A-Z][A-Z0-9 _/,.'&-]{2,40}\]",
                          template_marker="_TEMPLATE"):
    """Shared token-gate check. pma-qc's P5, listing-agreement-qc's L9, and
    lease-form-qc's T1 are all this same rule — but as of 2026-08-17 none of
    the three actually call this helper; each is still a locally hand-written
    check (pma_qc.py's _p5, listing_qc.py's _l9, lease_qc.py's _t1) that
    duplicates the pattern rather than sharing this implementation of it. T1
    in particular could not simply be swapped for a call to this helper: it
    also scans footer text (ctx["meta"]["footer"]) in addition to body text,
    which this helper does not read (it only reads ctx["raw"], the body) —
    see lease_qc.py's _t1 and its own comment. P5/L9 have no such constraint
    and are the more plausible future callers of this helper as-is; T1 would
    need the helper extended to cover the footer first.
    Register it into a tool's own registry with:
        CHECKS.append(unfilled_token_check())
    or, to keep the tool's existing check ID/title, pass those explicitly."""
    def fn(ctx):
        if ctx.get("is_template") or ctx.get("allow_tokens"):
            return None
        toks = sorted(set(re.findall(pattern, ctx["raw"])))
        if not toks:
            return None
        shown = ", ".join(toks[:6]) + ("..." if len(toks) > 6 else "")
        return f"{len(toks)} unfilled token(s): {shown}"
    return (cid, sev, title, pos, fn)


# ------------------------------------------------------------------- runner

def run_checks(ctx, checks):
    """Execute one tool's CHECKS list against ctx. Returns a sorted list of
    failure dicts. A check whose fn returns True is sugar for 'failed, detail
    == title' (see bool_check). A check that raises is downgraded to a MED
    finding naming the error, never allowed to crash the whole scan — one
    broken check must not blind the report to every other check's result."""
    results = []
    for cid, sev, title, pos, fn in checks:
        try:
            detail = fn(ctx)
        except Exception as e:                                     # noqa: BLE001
            detail, sev = f"check error: {e}", "MED"
        if detail is None or detail is False:
            continue
        if detail is True:
            detail = title
        results.append({"id": cid, "severity": sev, "title": title,
                        "position": pos, "detail": str(detail).strip()})
    results.sort(key=lambda r: (SEV_ORDER[r["severity"]], r["id"]))
    return results


def scan(path, checks, allow_tokens=False, allow_ocr=True,
         min_words=DEFAULT_MIN_WORDS, want_footer=False):
    """Full pipeline: extract -> build ctx -> run_checks. Returns a report
    dict, or None on a hard I/O error (caller should treat that as exit 2,
    same as an UNREADABLE result but for a different reason — file missing or
    unopenable vs. file opened but unextractable)."""
    if not os.path.exists(path):
        print(f"ERROR: no such file: {path}", file=sys.stderr)
        return None
    try:
        body, meta = extract(path, allow_ocr=allow_ocr, min_words=min_words,
                             want_footer=want_footer)
    except Exception as e:                                         # noqa: BLE001
        print(f"ERROR: extraction failed on {path}: {e}", file=sys.stderr)
        return None

    name = os.path.basename(path)
    if body is None:
        return {"file": name, "format": meta["format"],
                "extraction": meta["extraction"], "words": meta["words"],
                "unreadable": True, "checks_run": 0, "failures": []}

    ctx = {"t": norm(body), "raw": body, "meta": meta, "name": name,
           "allow_tokens": allow_tokens, "is_template": "_TEMPLATE" in name.upper()}
    failures = run_checks(ctx, checks)

    return {"file": name, "format": meta["format"], "extraction": meta["extraction"],
            "words": meta["words"], "unreadable": False,
            "tracked_changes": meta["tracked_changes"], "comments": meta["comments"],
            "strike": meta["strike"],
            "creator": meta.get("creator"), "company": meta.get("company"),
            "checks_run": len(checks), "failures": failures}


# ------------------------------------------------------------------- report

def _wrap(t, n):
    out, cur = [], ""
    for word in t.split():
        if len(cur) + len(word) + 1 > n:
            out.append(cur)
            cur = word
        else:
            cur = (cur + " " + word).strip()
    if cur:
        out.append(cur)
    return out


def print_report(r, ocr_absence_note=None):
    """Human-readable report for one scan() result. `ocr_absence_note`, if
    given, is printed when extraction == 'ocr' — pass a tool-specific list of
    check IDs whose findings are absence-based (fire because language is
    MISSING) and therefore provisional under lossy OCR text, e.g.
    'P16, P19, P24, P27-P30 are PROVISIONAL under OCR'."""
    print("=" * 78)
    print(f"FILE       {r['file']}  [{r['format']}]")
    print(f"EXTRACTION {r['extraction']}  ({r['words']} words)")
    if r["unreadable"]:
        print("RESULT     UNREADABLE - no text layer and OCR unavailable or "
              "insufficient.")
        print("           This document has NO QC result. An empty or "
              "near-empty extraction")
        print("           trips no checks and would otherwise score as clean.")
        print("           Install poppler-utils + tesseract, or supply a "
              "text-layer copy.")
        print()
        return
    enc = (f"tracked changes: {r['tracked_changes']}" if r.get("tracked_changes")
           else "compare-tool formatting (strikethrough), no tracked changes"
           if r.get("strike")
           else "no tracked changes (clean)")
    print(f"ENC        {enc}; comments.xml: {'yes' if r.get('comments') else 'no'}")
    if r.get("company"):
        print(f"ORIGIN     creator={r.get('creator')!r} company={r.get('company')!r}")
    counts = {}
    for x in r["failures"]:
        counts[x["severity"]] = counts.get(x["severity"], 0) + 1
    tally = " · ".join(f"{counts[s]} {s}" for s in
                             ("BLOCK", "HIGH", "MED", "LOW") if s in counts)
    print(f"RESULT     {len(r['failures'])} of {r['checks_run']} checks FAILED"
          + (f"  ({tally})" if tally else ""))
    if r["extraction"] == "ocr" and ocr_absence_note:
        print("NOTE       OCR text is lossy.", ocr_absence_note)
    print("-" * 78)
    for x in r["failures"]:
        pos = f"  ({x['position']})" if x.get("position") else ""
        print(f"[{x['severity']:<5}] {x['id']:<5} {x['title']}{pos}")
        if x["detail"] and x["detail"] != x["title"]:
            for line in _wrap(x["detail"], 70):
                print(f"           {line}")
    if not r["failures"]:
        print("  clean - no defects detected")
    print()


def build_cli(description):
    """Shared argparse skeleton. Each tool adds its own extras if needed and
    must still honor --allow-tokens / --no-ocr / --json so the three scanners
    behave identically at the command line."""
    ap = argparse.ArgumentParser(description=description)
    ap.add_argument("files", nargs="+")
    ap.add_argument("--allow-tokens", action="store_true",
                    help="suppress the unfilled-token BLOCK (working drafts)")
    ap.add_argument("--no-ocr", action="store_true",
                    help="disable the OCR fallback for image-only PDFs")
    ap.add_argument("--json", action="store_true")
    return ap


def run_cli(checks, description, ocr_absence_note=None, want_footer=False):
    """Full main()-equivalent. A tool's own script becomes:

        from ora_doc_qc import new_registry, run_cli
        check, CHECKS = new_registry()
        @check("P1", "BLOCK", "...", "PM-9")
        def _p1(ctx): ...
        if __name__ == "__main__":
            run_cli(CHECKS, "ORA property management agreement QC gate",
                    ocr_absence_note="P16, P19, P24, P27-P30 are PROVISIONAL")

    Exit codes preserved from every existing tool: 0 clean, 1 failures found,
    2 usage/extraction/unreadable error.
    """
    a = build_cli(description).parse_args()
    reports, bad = [], 0
    for f in a.files:
        r = scan(f, checks, a.allow_tokens, allow_ocr=not a.no_ocr,
                 want_footer=want_footer)
        if r is None:
            bad = 2
            continue
        reports.append(r)
        if r["unreadable"]:
            bad = 2

    if a.json:
        print(json.dumps(reports, indent=2))
    else:
        for r in reports:
            print_report(r, ocr_absence_note=ocr_absence_note)

    if any(r["failures"] for r in reports):
        sys.exit(1)
    sys.exit(bad)


# DONE: pma-qc, listing-agreement-qc, and lease-form-qc are all retrofitted
# onto this module (see commit history and each skill's SKILL.md changelog
# for the specifics of its own port). new_registry(), bool_check(), and
# unfilled_token_check() above carry the reusable porting guidance for any
# future consumer; there is nothing migration-specific left to say here.
