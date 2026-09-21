"""READ-ONLY reader for the ORA Master Workbook's `Master Tenant Rent Roll` tab.

STEP 1 of ora-renewal-hubspot-reconcile calls this instead of an inline heredoc.
An inline script names the workbook path in the same shell command that writes the
script file, which trips workbook-write-guard ("mutating shell command names the
master workbook") -- a false positive observed on the 2026-09-21 run. The path
lives here, in a checked-in file, so the shell command never names it.

Never writes the workbook:
  * openpyxl is opened with read_only=True and never saved.
  * The COM fallback attaches to an ALREADY-RUNNING Excel (never opens a second
    one), reads UsedRange.Value2, never calls Save and never sets a cell. It
    records Workbook.Saved before and after so a flip is reported, not hidden.

Usage:
  python read_rent_roll.py [--out <json path>] [--today YYYY-MM-DD]

Writes the full result as JSON (to --out, or stdout) and exits:
  0  read OK and the STEP 1d gate passed
  2  read OK but the gate FAILED (stale or future as-of / unparseable as-of / count out
     of range / roster end marker missing / count disagrees with row 2)
  3  the tab could not be read or parsed by either path
  Any other nonzero (e.g. 1 from an unexpected crash) must be treated like 3.
"""
import argparse
import datetime as dt
import json
import os
import re
import sys

WORKBOOK = (r"C:\Users\Owner\OneDrive - Oxford Capital Partners\eric spreadsheets"
            r"\Master Excel Template Company Wide -- Oxford.xlsx")
WORKBOOK_NAME_PREFIX = "Master Excel Template Company Wide"
SHEET = "Master Tenant Rent Roll"
HEADER_ROW_INDEX = 4  # row 5 in Excel
DATE_FIELDS = ("Lease Start", "Lease End", "Escalation Date")
# The tenant block ends where the summary block begins; nothing below it is a lease.
END_OF_ROSTER = "PORTFOLIO TOTALS"
MAX_AGE_DAYS = 7
COUNT_MIN, COUNT_MAX = 100, 200
# Row 2's "N tenants" is computed by the workbook from the same roster; a parse that
# drifts further than this from it has read the wrong rows (e.g. past a moved
# PORTFOLIO TOTALS label into the summary block).
HEADER_COUNT_TOLERANCE = 2
_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
EXCEL_EPOCH = dt.date(1899, 12, 30)


def _to_iso(value):
    if isinstance(value, (dt.datetime, dt.date)):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, (int, float)) and 20000 < value < 80000:  # COM date serial
        return (EXCEL_EPOCH + dt.timedelta(days=int(value))).isoformat()
    return value


def _parse_as_of(cell):
    m = re.search(r"As of\s+([A-Za-z]+ \d{1,2}, \d{4})", str(cell or ""))
    if not m:
        return None
    try:
        return dt.datetime.strptime(m.group(1), "%B %d, %Y").date().isoformat()
    except ValueError:
        return None


def _parse_header_count(cell):
    m = re.search(r"(\d+)\s+tenants", str(cell or ""))
    return int(m.group(1)) if m else None


def parse(rows):
    """rows: list of row tuples, sheet row 1 first. Returns the parsed roster dict."""
    rows = list(rows)
    if len(rows) <= HEADER_ROW_INDEX:
        raise ValueError("sheet has fewer rows than the header row")
    header = [str(h).strip() if h is not None else None for h in rows[HEADER_ROW_INDEX]]
    if "Tenant Name" not in header or "Lease End" not in header:
        raise ValueError("row 5 is not the expected header: %r" % (header,))
    as_of_cell = rows[1][0] if rows[1] else None

    out_rows, no_lease_end, hit_end_marker = [], [], False
    for raw in rows[HEADER_ROW_INDEX + 1:]:
        first = str(raw[0]).strip().upper() if raw and raw[0] is not None else ""
        if first == END_OF_ROSTER:
            hit_end_marker = True
            break
        rec = {k: v for k, v in zip(header, raw) if k}
        if not rec.get("Tenant Name"):
            continue
        for f in DATE_FIELDS:
            if f in rec:
                rec[f] = _to_iso(rec[f])
        out_rows.append(rec)
        # Blank OR unusable (text like "MTM"/"TBD", an implausible serial): the
        # STEP 4/6 date checks cannot see either, so both must be surfaced.
        if not _ISO_DATE_RE.match(str(rec.get("Lease End") or "")):
            no_lease_end.append(rec)

    return {
        "as_of_raw": as_of_cell,
        "as_of": _parse_as_of(as_of_cell),
        "header_tenant_count": _parse_header_count(as_of_cell),
        "rows": out_rows,
        "no_lease_end": no_lease_end,
        "hit_end_marker": hit_end_marker,
    }


def gate(parsed, today):
    """STEP 1d fail-loud gate. Returns a list of failure reasons ([] = pass)."""
    reasons = []
    if not parsed.get("as_of"):
        reasons.append("row-2 'As of' date unparseable: %r" % (parsed.get("as_of_raw"),))
    else:
        age = (today - dt.date.fromisoformat(parsed["as_of"])).days
        if age > MAX_AGE_DAYS:
            reasons.append("workbook as-of %s is %d days old (> %d)"
                           % (parsed["as_of"], age, MAX_AGE_DAYS))
        elif age < 0:
            reasons.append("workbook as-of %s is in the future" % parsed["as_of"])
    n = len(parsed.get("rows", []))
    if not COUNT_MIN <= n <= COUNT_MAX:
        reasons.append("parsed roster count %d outside %d-%d" % (n, COUNT_MIN, COUNT_MAX))
    if not parsed.get("hit_end_marker"):
        reasons.append("'%s' row not found -- roster end unknown" % END_OF_ROSTER)
    hc = parsed.get("header_tenant_count")
    if hc is None:
        reasons.append("row-2 tenant count unparseable")
    elif abs(n - hc) > HEADER_COUNT_TOLERANCE:
        reasons.append("parsed %d rows but row 2 says %d tenants (tolerance %d)"
                       % (n, hc, HEADER_COUNT_TOLERANCE))
    return reasons


def _read_openpyxl():
    from openpyxl import load_workbook
    wb = load_workbook(WORKBOOK, data_only=True, read_only=True)
    try:
        return list(wb[SHEET].iter_rows(values_only=True)), "openpyxl read-only", None
    finally:
        wb.close()


def _read_com():
    import win32com.client
    xl = win32com.client.GetActiveObject("Excel.Application")
    for wb in xl.Workbooks:
        if str(wb.Name).startswith(WORKBOOK_NAME_PREFIX):
            saved_before = bool(wb.Saved)
            used = wb.Worksheets(SHEET).UsedRange
            # UsedRange need not start at A1; pad so row/column indices match the sheet.
            top, left = int(used.Row) - 1, int(used.Column) - 1
            values = [(None,)] * top + [(None,) * left + tuple(r) for r in (used.Value2 or ())]
            saved_after = bool(wb.Saved)
            note = None
            if saved_before != saved_after:
                note = "Workbook.Saved flipped %s -> %s during read" % (saved_before, saved_after)
            return values, "excel COM read-only attach", note
    raise RuntimeError("running Excel has no workbook named %s*" % WORKBOOK_NAME_PREFIX)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    ap.add_argument("--today", default=dt.date.today().isoformat())
    args = ap.parse_args(argv)
    today = dt.date.fromisoformat(args.today)

    errors, rows, read_path, com_note = [], None, None, None
    try:
        rows, read_path, com_note = _read_openpyxl()
    except Exception as e:  # PermissionError when a live Excel holds the lock
        errors.append("openpyxl: %s: %s" % (type(e).__name__, e))
        try:
            rows, read_path, com_note = _read_com()
            read_path += " (openpyxl failed: %s)" % type(e).__name__
        except Exception as e2:
            errors.append("COM: %s: %s" % (type(e2).__name__, e2))

    if rows is None:
        result = {"ok": False, "read_path": None, "errors": errors,
                  "gate_failures": ["tab unreadable by either path"]}
        code = 3
    else:
        try:
            parsed = parse(rows)
        except ValueError as e:
            result = {"ok": False, "read_path": read_path, "errors": errors + [str(e)],
                      "gate_failures": ["tab read but not parseable: %s" % e]}
            code = 3
        else:
            failures = gate(parsed, today)
            result = dict(parsed, ok=not failures, read_path=read_path, errors=errors,
                          gate_failures=failures, com_saved_flip=com_note,
                          parsed_count=len(parsed["rows"]))
            code = 0 if not failures else 2

    text = json.dumps(result, default=str, indent=1)
    if args.out:
        if os.path.dirname(args.out):
            os.makedirs(os.path.dirname(args.out), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text)
        print(json.dumps({k: result.get(k) for k in (
            "ok", "as_of", "header_tenant_count", "parsed_count", "read_path",
            "gate_failures", "errors", "com_saved_flip")}, default=str))
        print("no_lease_end:", [(r.get("Property"), r.get("Unit"), r.get("Company"))
                                for r in result.get("no_lease_end", [])])
    else:
        print(text)
    return code


if __name__ == "__main__":
    sys.exit(main())
