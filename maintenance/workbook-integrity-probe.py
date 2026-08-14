"""ORA Master Workbook integrity probe -- detects the openpyxl absolute-rel defect.

THE DETECTION HALF of the openpyxl-write ban. `hooks/workbook-write-guard.py` is
prevention, but text matching cannot follow a path through a variable or a script
file (`python do_the_thing.py`), so prevention has a structural ceiling. This probe
covers what prevention cannot: it answers "is the workbook parseable RIGHT NOW"
cheaply, before an expensive consumer discovers it the hard way.

WHY IT EXISTS (2026-08-13/14). An openpyxl re-save wrote ABSOLUTE worksheet comment
relationship targets (`/xl/comments/comment1.xml`) where Excel writes them RELATIVE
(`../comments/comment1.xml`). exceljs keys on the relative form, so the lookup is
`undefined` and `.comments` throws, aborting the whole parse. Three consumers broke
for ~15h and the loudest symptom any of them produced was `build:mirror failed (1)`.

WHAT MAKES THIS HARD TO DIAGNOSE BY HAND -- every obvious check says "fine":
  * zip integrity (testzip) is CLEAN
  * all xl/comments/comment*.xml parts are PRESENT -- nothing is missing
  * no ~$ Excel lock file exists
  * a naive `../` -> `xl/` rel-target normalization reports the parts "MISSING",
    which is an artifact of the check, not the defect
The parts exist. The TARGET STYLE is the defect. That is what this probe measures.

DO NOT USE dc:creator AS A SIGNAL (verified 2026-08-14 on the repaired file). It is
sticky: once openpyxl has authored the file, `dc:creator` reads `openpyxl` forever,
including on a perfectly healthy workbook that Excel has since rewritten. The
reliable discriminators are `<Application>` in docProps/app.xml and, definitively,
the absolute-vs-relative rel-target count this probe returns.

EXIT CODES:
  0 = clean (no absolute worksheet rel targets)
  1 = CORRUPT (absolute rel targets present -- exceljs WILL fail to parse)
  2 = could not evaluate (missing/unreadable/not a zip). Deliberately distinct from
      1: "cannot verify" is not "confirmed broken", and a caller must be able to tell
      a real defect from a sync gap. Mirrors the verified-null-vs-inferred-null rule.

USAGE:
  python maintenance/workbook-integrity-probe.py [path] [--json]
Falls back to $WORKBOOK_PATH, then the canonical OneDrive location.

REMEDY when it reports CORRUPT: open the workbook in Excel and re-save. Excel rewrites
the rels to relative form. Do NOT hand-patch the XML and do NOT auto-normalize the
targets -- openpyxl's save also strips conditional formatting and can flatten formulas
to static values, so a rel-only repair produces a file that PARSES while being
silently gutted. Re-run this probe to confirm.

Stdlib only. ASCII-only. Windows (`python`).
"""
import json
import os
import re
import sys
import zipfile

DEFAULT_PATH = ("C:\\Users\\Owner\\OneDrive - Oxford Capital Partners\\"
                "eric spreadsheets\\Master Excel Template Company Wide -- Oxford.xlsx")

TARGET_RE = re.compile(r'Target="([^"]+)"')
APPLICATION_RE = re.compile(r"<Application>(.*?)</Application>", re.DOTALL)
LASTMOD_RE = re.compile(r"<cp:lastModifiedBy>(.*?)</cp:lastModifiedBy>", re.DOTALL)
MODIFIED_RE = re.compile(r"<dcterms:modified[^>]*>(.*?)</dcterms:modified>", re.DOTALL)

EXIT_CLEAN = 0
EXIT_CORRUPT = 1
EXIT_UNEVALUATED = 2


def _text(zf, name):
    try:
        return zf.read(name).decode("utf-8", "replace")
    except Exception:
        return ""


def probe(path):
    """Return a result dict. Never raises for an ordinary bad-input case."""
    result = {
        "path": path,
        "status": "unevaluated",
        "absoluteTargets": 0,
        "totalTargets": 0,
        "offendingSheets": [],
        "application": None,
        "lastModifiedBy": None,
        "modified": None,
        "detail": "",
    }
    if not os.path.isfile(path):
        result["detail"] = ("workbook not found at this path (OneDrive sync gap, or "
                            "the path is wrong) -- cannot evaluate")
        return result
    try:
        zf = zipfile.ZipFile(path)
    except Exception as exc:
        result["detail"] = "not a readable zip/xlsx container: %s" % exc
        return result

    with zf:
        app = _text(zf, "docProps/app.xml")
        core = _text(zf, "docProps/core.xml")
        m = APPLICATION_RE.search(app)
        if m:
            result["application"] = m.group(1).strip()
        m = LASTMOD_RE.search(core)
        if m:
            result["lastModifiedBy"] = m.group(1).strip()
        m = MODIFIED_RE.search(core)
        if m:
            result["modified"] = m.group(1).strip()

        rels = [n for n in zf.namelist()
                if n.endswith(".rels") and "/worksheets/" in n]
        for name in rels:
            body = _text(zf, name)
            for target in TARGET_RE.findall(body):
                result["totalTargets"] += 1
                if target.startswith("/"):
                    result["absoluteTargets"] += 1
                    sheet = name.replace("/_rels", "").replace(".rels", "")
                    if sheet not in result["offendingSheets"]:
                        result["offendingSheets"].append(sheet)

    if result["totalTargets"] == 0:
        # No worksheet rels at all is unusual but not itself the defect; say so
        # rather than reporting a false clean.
        result["status"] = "clean"
        result["detail"] = ("no worksheet relationship targets found -- nothing to "
                            "check (unusual, but not the openpyxl defect)")
        return result

    if result["absoluteTargets"]:
        result["status"] = "corrupt"
        result["detail"] = (
            "%d of %d worksheet rel targets are ABSOLUTE across %d sheet(s). exceljs "
            "reconcile() keys on the relative form, so this workbook WILL fail to "
            "parse with \"Cannot read properties of undefined (reading 'comments')\". "
            "Remedy: open in Excel and re-save."
            % (result["absoluteTargets"], result["totalTargets"],
               len(result["offendingSheets"])))
    else:
        result["status"] = "clean"
        result["detail"] = ("all %d worksheet rel targets are relative -- exceljs "
                            "will parse this workbook" % result["totalTargets"])
    return result


def main(argv):
    as_json = "--json" in argv
    args = [a for a in argv if not a.startswith("--")]
    path = (args[0] if args else None) or os.environ.get("WORKBOOK_PATH") \
        or DEFAULT_PATH

    result = probe(path)

    if as_json:
        print(json.dumps(result, indent=2))
    else:
        label = {"clean": "CLEAN", "corrupt": "CORRUPT",
                 "unevaluated": "UNEVALUATED"}[result["status"]]
        print("[%s] %s" % (label, result["path"]))
        print("  %s" % result["detail"])
        if result["application"] or result["lastModifiedBy"]:
            print("  writer: Application=%r lastModifiedBy=%r modified=%r"
                  % (result["application"], result["lastModifiedBy"],
                     result["modified"]))
            print("  (dc:creator is deliberately NOT reported -- it is sticky and "
                  "reads 'openpyxl' even on a repaired file)")
        for sheet in result["offendingSheets"]:
            print("  offending: %s" % sheet)

    return {"clean": EXIT_CLEAN, "corrupt": EXIT_CORRUPT,
            "unevaluated": EXIT_UNEVALUATED}[result["status"]]


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
