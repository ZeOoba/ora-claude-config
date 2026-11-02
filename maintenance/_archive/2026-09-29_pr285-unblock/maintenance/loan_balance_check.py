#!/usr/bin/env python3
"""loan_balance_check.py -- recompute expected loan balances from documented terms.

Reads ~/.claude/data/loan-terms.json (lender schedules and executed-note terms) and
prints the balance each loan SHOULD show on a given date, assuming every scheduled
payment was received on its due date. Optionally compares against the Notion Loans DB
(a JSON export of {name, balance, maturity}) and reports differences, an LTV watch list
and near maturities. Report-only: it never writes to Notion or any business folder.

Usage:
  python loan_balance_check.py [--terms PATH] [--as-of YYYY-MM-DD] [--notion-json PATH]
                               [--tolerance 5] [--md-out PATH] [--html-out PATH] [--json]
Exit code 0 always (the report carries the findings); 2 on unreadable input.
"""
import argparse
import html
import json
import os
import sys
from datetime import date, datetime, timedelta

DEFAULT_TERMS = os.path.join(os.path.expanduser("~"), ".claude", "data", "loan-terms.json")
LTV_CEILING = 0.65          # ORA per-property refi ceiling (informational here, never modified)
MATURITY_HORIZON_DAYS = 548  # about 18 months
TERMS_STALE_DAYS = 120


def _d(s):
    return datetime.strptime(s, "%Y-%m-%d").date()


def _add_month(d, day):
    y, m = (d.year, d.month + 1) if d.month < 12 else (d.year + 1, 1)
    last = (date(y + (m == 12), (m % 12) + 1, 1) - timedelta(days=1)).day
    return date(y, m, min(day, last))


def expected_balance(loan, as_of):
    """Full-loan principal after the last scheduled payment on or before as_of."""
    kind = loan["kind"]
    if kind == "schedule":
        bal = loan["original_principal"]
        for d, b in loan["schedule"]:
            if _d(d) <= as_of:
                bal = b
            else:
                break
        return round(bal, 2)
    if kind == "interest_only":
        return round(loan["original_principal"], 2)
    if kind == "anchor_amortizing":
        a = loan["anchor"]
        pay_date, bal = _d(a["date"]), a["principal"]
        maturity = _d(loan["maturity"])
        r = loan["rate"] / 12.0
        while True:
            nxt = _add_month(pay_date, loan["day"])
            if nxt > as_of or nxt >= maturity:
                break
            pay_date = nxt
            bal = bal - (loan["payment"] - bal * r)
        return round(bal, 2)
    raise ValueError(f"unknown loan kind: {kind}")


def load_terms(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def compute(terms, as_of, notion_rows=None, tolerance=5.0):
    findings = {"as_of": as_of.isoformat(), "loans": [], "differences": [], "watch": [], "notes": []}
    meta = terms.get("_meta", {})
    verified = meta.get("verified_on")
    if verified and (as_of - _d(verified)).days > TERMS_STALE_DAYS:
        findings["notes"].append(f"Terms file last verified {verified} ({(as_of - _d(verified)).days} days ago; re-verify against lender documents).")
    matched_notion = set()
    for loan in terms["loans"]:
        full = expected_balance(loan, as_of)
        share = loan.get("share", 1.0)
        exp = round(full * share, 2)
        row = {"id": loan["id"], "role": loan.get("role", "payable"), "share": share, "expected_full": full, "expected_share": exp,
               "maturity": loan.get("maturity"), "notion": None, "diff": None}
        mat = _d(loan["maturity"]) if loan.get("maturity") else None
        if mat and (mat - as_of).days <= MATURITY_HORIZON_DAYS:
            findings["watch"].append(f"{loan['id']}: matures {loan['maturity']} ({(mat - as_of).days} days)"
                                     + (f" - {loan['maturity_note']}" if loan.get("maturity_note") else ""))
        elif loan.get("maturity_note"):
            findings["watch"].append(f"{loan['id']}: {loan['maturity_note']}")
        ap = loan.get("appraisal")
        if ap and loan.get("role", "payable") == "payable":
            ltv = full / ap["value"]
            row["ltv_on_appraisal"] = round(ltv, 4)
            tag = "" if ap.get("confirmed", True) else " (appraisal value unconfirmed)"
            if ltv > LTV_CEILING:
                findings["watch"].append(f"{loan['id']}: LTV {ltv:.1%} on the {ap['date']} appraisal (${ap['value']:,}) is above the {LTV_CEILING:.0%} per-property ceiling{tag}. Informational: the ceiling governs refis, not this loan.")
        if notion_rows is not None:
            hit = next((n for n in notion_rows if loan["notion_name"].lower() in (n.get("name") or "").lower()), None)
            if hit is None:
                findings["differences"].append(f"{loan['id']}: no Notion Loans DB record matches '{loan['notion_name']}'.")
            else:
                matched_notion.add(hit.get("name"))
                row["notion"] = hit.get("balance")
                if hit.get("balance") is not None:
                    row["diff"] = round(hit["balance"] - exp, 2)
                    if abs(row["diff"]) > tolerance:
                        findings["differences"].append(
                            f"{loan['id']}: Notion balance ${hit['balance']:,.2f} vs expected ${exp:,.2f} ({'ORA share' if share != 1 else 'full loan'}) as of {as_of}: difference ${row['diff']:+,.2f}"
                            + ("; verify the latest installment was received" if loan["kind"] == "anchor_amortizing" else ""))
                if loan.get("maturity") and hit.get("maturity") and str(hit["maturity"])[:10] != loan["maturity"]:
                    findings["differences"].append(f"{loan['id']}: Notion maturity {str(hit['maturity'])[:10]} vs documented {loan['maturity']}.")
        findings["loans"].append(row)
    if notion_rows is not None:
        extra = [n.get("name") for n in notion_rows if n.get("name") not in matched_notion]
        if extra:
            findings["notes"].append(f"{len(extra)} Notion loan record(s) are not modeled (internal or no lender schedule): " + "; ".join(extra))
    return findings


def render_markdown(f):
    out = [f"# Loan balance check, as of {f['as_of']}", "",
           "Report-only. Expected balances assume every scheduled payment was received on its due date.", ""]
    out.append(f"## Differences ({len(f['differences'])})")
    out += [f"- {x}" for x in f["differences"]] or ["- None: every modeled Notion balance is within tolerance."]
    out += ["", "## Watch list"] + ([f"- {x}" for x in f["watch"]] or ["- Nothing on the watch list."])
    if f["notes"]:
        out += ["", "## Notes"] + [f"- {x}" for x in f["notes"]]
    out += ["", "## Expected balances", "", "| Loan | Role | Share | Expected (ORA share) | Full loan | Notion | Diff |", "|---|---|---|---|---|---|---|"]
    for r in f["loans"]:
        n = "" if r["notion"] is None else f"{r['notion']:,.2f}"
        d = "" if r["diff"] is None else f"{r['diff']:+,.2f}"
        out.append(f"| {r['id']} | {r['role']} | {r['share']:.0%} | {r['expected_share']:,.2f} | {r['expected_full']:,.2f} | {n} | {d} |")
    return "\n".join(out) + "\n"


def render_html(f):
    esc = html.escape
    parts = [f"<html><body style='font-family:Calibri,Arial,sans-serif;font-size:11pt'><h3>Loan balance check, as of {esc(f['as_of'])}</h3>",
             "<p>Report-only. Expected balances assume every scheduled payment was received on its due date.</p>"]
    parts.append(f"<b>Differences ({len(f['differences'])})</b><ul>" + "".join(f"<li>{esc(x)}</li>" for x in (f["differences"] or ["None: every modeled Notion balance is within tolerance."])) + "</ul>")
    parts.append("<b>Watch list</b><ul>" + "".join(f"<li>{esc(x)}</li>" for x in (f["watch"] or ["Nothing on the watch list."])) + "</ul>")
    if f["notes"]:
        parts.append("<b>Notes</b><ul>" + "".join(f"<li>{esc(x)}</li>" for x in f["notes"]) + "</ul>")
    parts.append("<table border='1' cellpadding='4' style='border-collapse:collapse;font-size:10pt'><tr><th>Loan</th><th>Role</th><th>Share</th><th>Expected (ORA share)</th><th>Notion</th><th>Diff</th></tr>")
    for r in f["loans"]:
        n = "" if r["notion"] is None else f"{r['notion']:,.2f}"
        d = "" if r["diff"] is None else f"{r['diff']:+,.2f}"
        parts.append(f"<tr><td>{esc(r['id'])}</td><td>{esc(r['role'])}</td><td>{r['share']:.0%}</td><td align='right'>{r['expected_share']:,.2f}</td><td align='right'>{n}</td><td align='right'>{d}</td></tr>")
    parts.append("</table></body></html>")
    return "".join(parts)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--terms", default=DEFAULT_TERMS)
    ap.add_argument("--as-of", default=date.today().isoformat())
    ap.add_argument("--notion-json", help="JSON list of {name, balance, maturity} exported from the Notion Loans DB")
    ap.add_argument("--tolerance", type=float, default=5.0)
    ap.add_argument("--md-out")
    ap.add_argument("--html-out")
    ap.add_argument("--json", action="store_true", help="print findings as JSON instead of markdown")
    a = ap.parse_args(argv)
    try:
        terms = load_terms(a.terms)
        notion = None
        if a.notion_json:
            with open(a.notion_json, encoding="utf-8") as fh:
                notion = json.load(fh)
        f = compute(terms, _d(a.as_of), notion, a.tolerance)
    except (OSError, ValueError, KeyError) as e:
        print(f"loan_balance_check: unreadable input: {e}", file=sys.stderr)
        return 2
    if a.md_out:
        with open(a.md_out, "w", encoding="utf-8") as fh:
            fh.write(render_markdown(f))
    if a.html_out:
        with open(a.html_out, "w", encoding="utf-8") as fh:
            fh.write(render_html(f))
    print(json.dumps(f, indent=1) if a.json else render_markdown(f))
    return 0


if __name__ == "__main__":
    sys.exit(main())
