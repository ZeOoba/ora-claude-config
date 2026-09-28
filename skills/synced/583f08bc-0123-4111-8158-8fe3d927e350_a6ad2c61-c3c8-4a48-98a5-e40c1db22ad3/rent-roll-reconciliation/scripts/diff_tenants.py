"""
Diff a parsed rent roll (see parse_rent_roll.py) against a pulled snapshot
of the Notion Tenant Database, and report:
  - matched records with field mismatches (SF, rent, dates, escalation)
  - Notion records with no rent-roll match
  - rent-roll rows with no Notion match

Usage:
    python diff_tenants.py notion_all.json rentroll.json

notion_all.json: list of dicts with at least:
    id, Tenant Name, Property Address, Suite / Unit, SF, Monthly Rent,
    Lease Start, Lease Expiration, Next Escalation Date, Escalation Percent

rentroll.json: output of parse_rent_roll.py

This is a starting point, not a black box -- read the output and use
judgment per SKILL.md step 5/6 before writing anything. In particular,
a "no match" from this script is NOT sufficient justification to retire
a record; a "match" on name alone without SF/rent corroboration can be a
false positive (see the Bay Area Corporation / Bay Area Exteriors case
in SKILL.md history) -- always check the matched SF/rent line up too.
"""
import sys
import json
import re


def norm(s):
    if not s:
        return ""
    s = str(s).lower()
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    s = re.sub(r"\b(llc|inc|ltd|corp|corporation|company|co|the|dba|jr|sr)\b", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def build_rr_index(rentroll):
    idx = []
    for r in rentroll:
        if not r.get("property") or str(r["property"]).strip().upper() in ("NONE", "PORTFOLIO TOTALS"):
            continue
        toks = set()
        for f in ("contact", "company"):
            v = norm(r.get(f))
            if v:
                toks.add(v)
        idx.append({"rec": r, "toks": toks})
    return idx


# Match-acceptance tolerances (distinct from the mismatch-REPORTING tolerances used later
# in diff() on an already-matched row -- these decide whether a name-token hit may be
# ACCEPTED as a match at all). SF must agree exactly: it's an integer field with no
# expected rounding/unit ambiguity between Notion and a rent roll on the same property.
# Rent is allowed a cent-level tolerance for float/rounding noise, not a real disagreement.
SF_MATCH_TOLERANCE = 0
RENT_MATCH_TOLERANCE_USD = 0.02


def _token_matches(name, e):
    """True if rr_idx entry `e`'s token set intersects `name` in either direction, both
    sides clearing the >2-char floor (a short fragment on EITHER side is not distinctive
    enough to trust). Callable against an entry regardless of its consumed state --
    _candidates() below applies this only to unconsumed entries; match_rr additionally
    uses it against CONSUMED entries to detect the "lost to an earlier match" case."""
    n = norm(name)
    if not n or len(n) <= 2:
        return False
    return any(t and len(t) > 2 and (n in t or t in n) for t in e["toks"])


def _candidates(name, rr_idx):
    """Every UNCONSUMED rr_idx entry whose token set intersects `name` (see _token_matches)."""
    return [e for e in rr_idx if not e.get("consumed") and _token_matches(name, e)]


def _corroboration_possible(sf, rent, rec):
    """True if EITHER field has data on BOTH sides to compare at all -- i.e. corroboration
    could be ATTEMPTED. False means there is nothing to check against (not that a check
    was attempted and failed), which match_rr treats differently: see "matched_unverified"."""
    return (
        (sf is not None and rec.get("sf") is not None)
        or (rent is not None and rec.get("monthly_rent") is not None)
    )


def match_rr(name, sf, rent, rr_idx):
    """Score every candidate rather than returning the first token hit (first-substring
    match with no corroboration produced a real false positive -- see the Bay Area
    Corporation / Bay Area Exteriors case in SKILL.md history). A name-token hit alone
    is never sufficient to ACCEPT a match when corroboration is actually possible: SF or
    monthly-rent must also agree within tolerance. Consumes the winning entry so a single
    rent-roll row cannot be matched to more than one Notion record (many-to-one).

    Returns (rec_or_None, status) where status is one of:
      "matched"            -- exactly one corroborated candidate; rr entry consumed.
      "matched_unverified" -- exactly one candidate, and corroboration was never POSSIBLE
                               for it (neither side has SF/rent data at all) -- accepted as
                               the only option rather than discarded, because the sparsest
                               records (missing SF/rent) are precisely what this skill
                               exists to fill in; routing them to "ambiguous" -- whose own
                               resolution method requires SF/rent evidence that doesn't
                               exist for these rows -- would silently drop exactly the
                               records most in need of reconciliation. Multiple such
                               candidates, or a real corroboration ATTEMPT that failed
                               (data present but disagreed), both stay "ambiguous" --
                               this exception applies ONLY to a single candidate with no
                               data on either side to check.
      "ambiguous"           -- 2+ corroborated candidates, 1+ candidates where corroboration
                               was attempted and failed, or 2+ candidates with no
                               corroboration possible (name-only hits are reported, never
                               auto-applied).
      "consumed_by_other"   -- the only token-matching candidate(s) were already consumed
                               by an earlier Notion record in this run. Matching is a
                               single greedy pass in `notion` order, so a later record that
                               would have corroborated equally well (or better) against an
                               already-claimed row must not read identically to "genuinely
                               no candidate" -- the caller folds this into the ambiguous
                               bucket rather than silently reporting no_match.
      None                  -- no candidate at all, consumed or not.
    """
    candidates = _candidates(name, rr_idx)
    if not candidates:
        if any(_token_matches(name, e) for e in rr_idx if e.get("consumed")):
            return None, "consumed_by_other"
        return None, None

    def corroborates(e):
        rec = e["rec"]
        sf_ok = sf is not None and rec.get("sf") is not None and sf == rec["sf"]
        rent_ok = (rent is not None and rec.get("monthly_rent") is not None
                   and abs(rent - rec["monthly_rent"]) <= RENT_MATCH_TOLERANCE_USD)
        return sf_ok or rent_ok

    corroborated = [e for e in candidates if corroborates(e)]
    if len(corroborated) == 1:
        corroborated[0]["consumed"] = True
        return corroborated[0]["rec"], "matched"
    if len(corroborated) > 1:
        return None, "ambiguous"

    if len(candidates) == 1 and not _corroboration_possible(sf, rent, candidates[0]["rec"]):
        candidates[0]["consumed"] = True
        return candidates[0]["rec"], "matched_unverified"

    # Either 2+ uncorroborated candidates, or a single candidate whose corroboration was
    # attempted and failed -- both are reported for a human to resolve (see module
    # docstring); neither is auto-applied.
    return None, "ambiguous"


def diff(notion, rentroll):
    rr_idx = build_rr_index(rentroll)
    mismatches = []
    no_match = []
    ambiguous = []

    for rec in notion:
        # rec.get("Tenant Name", "") only supplies the default when the KEY is absent --
        # a Notion title field that is present but null (a real, documented shape) still
        # yields None here, and None.startswith(...) two lines below raised AttributeError.
        name = rec.get("Tenant Name") or ""
        if name.startswith("[Unknown") or name.startswith("⛔"):
            continue
        m, status = match_rr(name, rec.get("SF"), rec.get("Monthly Rent"), rr_idx)
        # "consumed_by_other" is a real ambiguity discovered across two different
        # match_rr() calls rather than within one (see match_rr's docstring) -- it
        # belongs in the same human-review bucket as "ambiguous", not in no_match.
        if status in ("ambiguous", "consumed_by_other"):
            ambiguous.append(rec)
            continue
        if not m:
            no_match.append(rec)
            continue

        diffs = {}
        if m.get("sf") is not None and rec.get("SF") != m["sf"]:
            diffs["SF"] = (rec.get("SF"), m["sf"])
        if m.get("monthly_rent") is not None:
            a, b = rec.get("Monthly Rent") or 0, m["monthly_rent"] or 0
            if abs(a - b) > 0.02:
                diffs["Monthly Rent"] = (rec.get("Monthly Rent"), m["monthly_rent"])
        if m.get("lease_start") and rec.get("Lease Start") != m["lease_start"]:
            diffs["Lease Start"] = (rec.get("Lease Start"), m["lease_start"])
        if m.get("lease_end") and rec.get("Lease Expiration") != m["lease_end"]:
            diffs["Lease Expiration"] = (rec.get("Lease Expiration"), m["lease_end"])
        if m.get("escalation_date") and rec.get("Next Escalation Date") != m["escalation_date"]:
            diffs["Next Escalation Date"] = (rec.get("Next Escalation Date"), m["escalation_date"])
        if m.get("escalation_pct") is not None:
            a, b = rec.get("Escalation Percent") or 0, m["escalation_pct"] or 0
            if abs(a - b) > 0.0005:
                diffs["Escalation Percent"] = (rec.get("Escalation Percent"), m["escalation_pct"])

        # A "matched_unverified" row must surface even with zero field diffs -- otherwise
        # "matched, nothing to report" and "matched but never actually corroborated" would
        # look identical, silently hiding the one thing a human needs to know before
        # trusting it (see match_rr's docstring).
        if diffs or status == "matched_unverified":
            entry = {
                "id": rec.get("id"),
                "name": name,
                "property": rec.get("Property Address"),
                "diffs": diffs,
            }
            if status == "matched_unverified":
                entry["note"] = (
                    "matched by name only -- no SF/rent on either side to corroborate; "
                    "verify manually"
                )
            mismatches.append(entry)

    # "consumed" (set on the winning entry inside match_rr) replaces the old id-set
    # membership check -- a row consumed by one Notion record can no longer win a
    # DIFFERENT Notion record's match (one-to-one), so it must not appear here either.
    unmatched_rr = [e["rec"] for e in rr_idx if not e.get("consumed")]
    return mismatches, no_match, unmatched_rr, ambiguous


if __name__ == "__main__":
    notion = json.load(open(sys.argv[1]))
    rentroll = json.load(open(sys.argv[2]))

    mismatches, no_match, unmatched_rr, ambiguous = diff(notion, rentroll)

    print(f"=== FIELD MISMATCHES ON MATCHED RECORDS ({len(mismatches)}) ===")
    for m in mismatches:
        note = f"  [{m['note']}]" if m.get("note") else ""
        print(m["id"], "|", m["name"], "|", m["property"], "|", m["diffs"], note)

    print(f"\n=== AMBIGUOUS -- 2+ candidates or no SF/rent corroboration ({len(ambiguous)}) ===")
    print("Reported only -- do NOT auto-apply any of these; resolve by hand per SKILL.md step 5/6.")
    for r in ambiguous:
        print(r.get("id"), "|", r.get("Tenant Name"), "|", r.get("Property Address"),
              "|SF", r.get("SF"), "|rent", r.get("Monthly Rent"))

    print(f"\n=== NOTION RECORDS WITH NO RENT-ROLL MATCH ({len(no_match)}) ===")
    for r in no_match:
        print(r.get("id"), "|", r.get("Tenant Name"), "|", r.get("Property Address"),
              "|SF", r.get("SF"), "|rent", r.get("Monthly Rent"))

    print(f"\n=== RENT-ROLL ROWS WITH NO NOTION MATCH ({len(unmatched_rr)}) ===")
    for r in unmatched_rr:
        print(r.get("property"), "|", r.get("unit"), "|", r.get("contact"), "|", r.get("company"),
              "|SF", r.get("sf"), "|rent", r.get("monthly_rent"))
