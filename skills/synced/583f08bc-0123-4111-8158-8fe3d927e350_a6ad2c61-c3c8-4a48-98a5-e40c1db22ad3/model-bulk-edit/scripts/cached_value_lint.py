#!/usr/bin/env python3
"""cached_value_lint.py -- find ORA workbooks whose formulas carry no cached values.

Why this exists: the QC Gate reads headline figures with
openpyxl.load_workbook(path, data_only=True), which returns the value Excel last
*cached* into the file. A workbook written programmatically (openpyxl, xlsxwriter)
and never opened in Excel has formulas but no cached values, so every one of those
reads comes back None. None reads as "field not populated", not as "this file has
never been calculated" -- so a broken model looks like an incomplete one and the QC
Gate passes over it silently.

Found live 2026-08-22: ORA_UnderwritingModel_125DouglasPike_v2.0.xlsx carried null
DSCR at Returns!B37 and Sensitivity!B17. Any QC run against it would have read nulls.

Exit codes: 0 = no dead workbooks, 1 = at least one DEAD/PARTIAL, 2 = usage error.

Usage:
  python cached_value_lint.py <root> [--json] [--quiet]
"""
import os, sys, json, gc, warnings
warnings.filterwarnings("ignore")

try:
    import openpyxl
except ImportError:
    print("openpyxl not installed", file=sys.stderr); sys.exit(2)

SKIP_DIRS = {"_archive", "archive", ".git", "__pycache__"}

def audit(path):
    """Return (formulas, cached, unreadable_reason).

    read_only=True is LOAD-BEARING, not a nicety. Without it openpyxl builds a full
    in-memory object tree per workbook, and this function holds TWO of them at once
    (formulas + cached values). A sweep over ORA's Business tree reached 9.1 GB RSS
    and exhausted the machine's paging file (2026-08-22) -- an unrelated PowerShell
    call then died with 0x800705AF. read_only streams row-by-row and keeps the
    footprint flat regardless of workbook size or count.
    """
    wf = wv = None
    try:
        wf = openpyxl.load_workbook(path, data_only=False, read_only=True)
        wv = openpyxl.load_workbook(path, data_only=True, read_only=True)
        formulas = cached = 0
        for name in wf.sheetnames:
            fs, vs = wf[name], wv[name]
            # zip the two streams so neither sheet is materialised in full
            for frow, vrow in zip(fs.iter_rows(), vs.iter_rows()):
                for fc, vc in zip(frow, vrow):
                    if isinstance(fc.value, str) and fc.value.startswith("="):
                        formulas += 1
                        if vc.value is not None:
                            cached += 1
        return formulas, cached, None
    except Exception as e:
        return 0, 0, f"{type(e).__name__}: {e}"[:120]
    finally:
        for wb in (wf, wv):
            try:
                if wb is not None:
                    wb.close()
            except Exception:
                pass
        gc.collect()

def classify(f, c):
    if f == 0:            return "NO-FORMULAS"
    if c == 0:            return "DEAD"       # every formula uncached
    if c < f * 0.98:      return "PARTIAL"    # some stale/uncalculated region
    return "OK"

def main(argv):
    if len(argv) < 2:
        print(__doc__); return 2
    root = argv[1]
    as_json = "--json" in argv
    quiet = "--quiet" in argv
    rows = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            if not fn.lower().endswith((".xlsx", ".xlsm")) or fn.startswith("~$"):
                continue
            p = os.path.join(dirpath, fn)
            f, c, err = audit(p)
            verdict = "UNREADABLE" if err else classify(f, c)
            rows.append({"path": os.path.relpath(p, root), "verdict": verdict,
                         "formulas": f, "cached": c, "error": err})
    bad = [r for r in rows if r["verdict"] in ("DEAD", "PARTIAL")]
    if as_json:
        print(json.dumps({"root": root, "rows": rows}, indent=1))
    else:
        for r in sorted(rows, key=lambda r: (r["verdict"] != "DEAD", r["path"])):
            if quiet and r["verdict"] in ("OK", "NO-FORMULAS"):
                continue
            extra = r["error"] or f'{r["cached"]}/{r["formulas"]} formulas cached'
            print(f'{r["verdict"]:11} {r["path"]}  ({extra})')
        n_un = sum(1 for r in rows if r["verdict"] == "UNREADABLE")
        print(f'\n{len(rows)} workbook(s) | {len(bad)} dead-or-partial | {n_un} unreadable')
        if bad:
            print("Remedy: open in Excel and save, or re-run the write through Excel COM with "
                  "CalculateFullRebuild(). Do NOT re-save with openpyxl -- that is what caused it.")
    return 1 if bad else 0

if __name__ == "__main__":
    sys.exit(main(sys.argv))
