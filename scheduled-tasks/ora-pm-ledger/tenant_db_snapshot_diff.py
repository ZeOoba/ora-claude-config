#!/usr/bin/env python3
"""
tenant_db_snapshot_diff.py  --  ora-pm-ledger Block A helper.

WHY THIS EXISTS
  The Notion Tenant Database's `last_edited_time` column is FROZEN at the source
  (every row reports its March-2026 bulk-import stamp, even rows provably edited
  in July). Every read path -- SQL bridge, notion-search, notion-fetch, and REST
  -- agrees, so no timestamp query can detect a Tenant DB edit. See SKILL.md
  Block A DEFECT 1. The ONLY mechanism that can detect edits is a full snapshot
  hashed and diffed against the prior run. Unlimited REST reads (ORA Command
  Center integration token, granted 2026-07-16) make a nightly full pull cheap.

WHAT IT DOES
  --run [--date YYYY-MM-DD]
     1. Pulls every Tenant DB row via REST (paginated).
     2. Normalizes each row's properties to plain values (skipping volatile
        metadata: created/last_edited time+by), fingerprints each row (sha256).
     3. Loads the previous snapshot (state/tenant-db-latest.json) if present.
     4. Emits a diff: added / removed / changed(field-level old->new).
     5. Writes the new snapshot to latest + a dated archive.
     6. Prints a JSON block on the last line prefixed `RESULT_JSON=` for the
        caller (the digest) to parse. First run = baseline, no diff.
  --selftest
     Runs the diff engine against synthetic snapshots, no network. Exit 0 = pass.

STORAGE
  state/tenant-db-latest.json         <- previous/current pointer
  state/tenant-db-<YYYY-MM-DD>.json   <- dated archive (audit trail)

TOKEN
  NOTION_TOKEN from C:\\Users\\Owner\\oxford-command-center\\.env (read-only).
"""
import argparse, datetime, hashlib, json, os, sys, time, urllib.request, urllib.error

# Harness-spawned/scheduled runs get a cp1252 stdout on Windows; tenant titles
# carry emoji (e.g. the U+26D4 archive tombstone). Force UTF-8 so prints never crash.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

TENANT_DB_ID = "8dbbaec0-611a-4617-be07-6a77d0d0307a"   # single-source; REST /databases/{id}/query @ 2022-06-28 = 200
ENV_PATH = r"C:\Users\Owner\oxford-command-center\.env"
STATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state")
LATEST = os.path.join(STATE_DIR, "tenant-db-latest.json")
SKIP_TYPES = {"created_time", "last_edited_time", "created_by", "last_edited_by"}

# Notion formula fields whose value is derived from the CURRENT DATE. They recompute on
# every read, so they differ across any two pulls taken on different days regardless of
# whether a human or agent touched the row. Including them in the fingerprint made the
# detector report ~98% false positives on the first genuine cross-day run (2026-07-24:
# 267 rows "changed", 5 real). The 2026-07-20 "verified end-to-end" sign-off missed this
# because that verification was a SAME-DAY second pull, where these had not yet moved.
#
# Excluded by NAME, not by type: a formula over static inputs is a legitimate change
# signal and must stay in the fingerprint. Only calendar-derived ones are dropped.
# If a new date-derived formula is added to the Tenant DB, the bulk-field guard in
# diff_snapshots() will surface it rather than let it silently flood the diff again.
TIME_DERIVED_FIELDS = {
    "Days to Expiration",
    "Months Remaining",
    "WALT Contribution (Years)",
    "Tenant Tenure (Months)",
    # Added 2026-07-24 after the bulk-field guard below flagged it on its first run:
    # 'Months to Expiry' moved on 298/298 rows in the 07-21 -> 07-22 diff. Integer months,
    # so unlike the others it only moves at a month boundary — i.e. it would have produced
    # a full 298-row false burst roughly once a month rather than daily.
    "Months to Expiry",
}

# A field changing on more than this share of all rows is almost certainly bulk/derived
# rather than edited, and is reported as a warning instead of silently inflating the diff.
BULK_FIELD_RATIO = 0.5


# ---------- property normalization ----------
def _people(v):
    return "|".join(sorted(p.get("id", "") for p in v or []))

def norm_prop(p):
    """Return a stable plain-text value for one Notion property object, or None to skip."""
    t = p.get("type")
    if t in SKIP_TYPES:
        return None
    if t in ("title", "rich_text"):
        return "".join(x.get("plain_text", "") for x in p.get(t, []))
    if t == "number":
        n = p.get("number")
        return "" if n is None else repr(n)
    if t in ("select", "status"):
        o = p.get(t)
        return o.get("name", "") if o else ""
    if t == "multi_select":
        return "|".join(sorted(o.get("name", "") for o in p.get("multi_select", [])))
    if t == "date":
        d = p.get("date")
        return "" if not d else "%s/%s" % (d.get("start", ""), d.get("end", "") or "")
    if t == "checkbox":
        return "true" if p.get("checkbox") else "false"
    if t in ("url", "email", "phone_number"):
        return p.get(t) or ""
    if t == "people":
        return _people(p.get("people"))
    if t == "relation":
        return "|".join(sorted(r.get("id", "") for r in p.get("relation", [])))
    if t == "files":
        return "|".join(sorted(f.get("name", "") for f in p.get("files", [])))
    if t == "unique_id":
        u = p.get("unique_id") or {}
        return "%s%s" % (u.get("prefix") or "", u.get("number"))
    if t == "formula":
        f = p.get("formula") or {}
        ft = f.get("type")
        val = f.get(ft) if ft else None
        if isinstance(val, dict):   # date formula
            return "%s/%s" % (val.get("start", ""), val.get("end", "") or "")
        return "" if val is None else str(val)
    if t == "rollup":
        r = p.get("rollup") or {}
        rt = r.get("type")
        if rt == "number":
            n = r.get("number")
            return "" if n is None else repr(n)
        if rt == "date":
            d = r.get("date") or {}
            return "%s/%s" % (d.get("start", ""), d.get("end", "") or "")
        if rt == "array":
            return "[array:%d]" % len(r.get("array", []))
        return str(r.get(rt, ""))
    # unknown/unhandled type: best-effort stable repr
    return json.dumps(p.get(t), sort_keys=True, default=str)


def title_of(props):
    for name, p in props.items():
        if p.get("type") == "title":
            return "".join(x.get("plain_text", "") for x in p.get("title", [])) or "(untitled)"
    return "(no title)"


def row_fields(props):
    """{prop_name: normalized_value} excluding skipped metadata/None and date-derived formulas."""
    out = {}
    for name, p in props.items():
        if name in TIME_DERIVED_FIELDS:
            continue
        v = norm_prop(p)
        if v is not None:
            out[name] = v
    return out


def comparable_fields(row):
    """Fields of a stored snapshot row, minus any date-derived ones.

    Applied on BOTH sides of the diff so snapshots written before TIME_DERIVED_FIELDS
    existed compare cleanly against ones written after — without this, the first run
    after the fix would report every row as changed (the stored pre-fix hash covers
    fields the new fingerprint no longer includes).
    """
    return {k: v for k, v in (row.get("fields") or {}).items() if k not in TIME_DERIVED_FIELDS}


def fingerprint(fields):
    blob = json.dumps(fields, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def build_snapshot(pages, as_of, db_id):
    rows = {}
    for pg in pages:
        props = pg.get("properties", {})
        fields = row_fields(props)
        rows[pg["id"]] = {"title": title_of(props), "hash": fingerprint(fields), "fields": fields}
    return {"as_of": as_of, "db_id": db_id, "count": len(rows), "rows": rows}


# ---------- diff engine (pure, unit-tested by --selftest) ----------
def diff_snapshots(prev, curr):
    p = (prev or {}).get("rows", {})
    c = curr.get("rows", {})
    added, removed, changed = [], [], []
    for pid, row in c.items():
        if pid not in p:
            added.append({"id": pid, "title": row["title"]})
            continue
        # Compare filtered fields directly rather than the stored hash: the hash may have
        # been computed under an older field set (see comparable_fields).
        pf, cf = comparable_fields(p[pid]), comparable_fields(row)
        if pf != cf:
            changes = []
            for k in sorted(set(pf) | set(cf)):
                if pf.get(k) != cf.get(k):
                    changes.append({"field": k, "old": pf.get(k, "<absent>"), "new": cf.get(k, "<absent>")})
            changed.append({"id": pid, "title": row["title"], "changes": changes})
    for pid, row in p.items():
        if pid not in c:
            removed.append({"id": pid, "title": row["title"]})
    # Bulk-field guard: a field that moved on most rows is derived or bulk-written, not
    # edited. Surface it loudly instead of letting it inflate the diff unnoticed, which is
    # exactly how the date-derived-formula defect went undetected until 2026-07-24.
    warnings = []
    total = len(c)
    if total:
        freq = {}
        for row in changed:
            for ch in row["changes"]:
                freq[ch["field"]] = freq.get(ch["field"], 0) + 1
        for field, n in sorted(freq.items(), key=lambda kv: -kv[1]):
            # >= not >: a derived field moving on EXACTLY half the rows is the same signal,
            # and on a small DB that boundary is easy to land on.
            if n / total >= BULK_FIELD_RATIO:
                warnings.append(
                    "field %r changed on %d/%d rows (%.0f%%) — likely derived or bulk-written, "
                    "not edited; consider adding it to TIME_DERIVED_FIELDS"
                    % (field, n, total, 100.0 * n / total)
                )

    return {
        "prev_as_of": (prev or {}).get("as_of"),
        "curr_as_of": curr.get("as_of"),
        "prev_count": (prev or {}).get("count", 0),
        "curr_count": curr.get("count", 0),
        "added": added,
        "removed": removed,
        "changed": changed,
        "unchanged": curr.get("count", 0) - len(added) - len(changed),
        "warnings": warnings,
    }


# ---------- REST pull ----------
def load_token():
    # Exact key match: a prefix match would happily return NOTION_TOKEN_OLD / _BACKUP and
    # authenticate as the wrong (possibly revoked) integration.
    with open(ENV_PATH, encoding="utf-8") as f:
        for line in f:
            k, sep, v = line.partition("=")
            if sep and k.strip() == "NOTION_TOKEN":
                return v.strip().strip('"').strip("'")
    raise RuntimeError("NOTION_TOKEN not found in %s" % ENV_PATH)


def pull_all(db_id, token):
    pages, cursor = [], None
    while True:
        body = {"page_size": 100}
        if cursor:
            body["start_cursor"] = cursor
        req = urllib.request.Request(
            "https://api.notion.com/v1/databases/%s/query" % db_id,
            data=json.dumps(body).encode(),
            headers={"Authorization": "Bearer " + token,
                     "Notion-Version": "2022-06-28",
                     "Content-Type": "application/json"},
            method="POST")
        # Bounded retry on rate-limit/transient server errors. Unattended at 18:00, one
        # Notion hiccup would otherwise be an unhandled HTTPError and a lost run.
        d = None
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    d = json.load(r)
                break
            except urllib.error.HTTPError as e:
                if e.code in (429, 500, 502, 503, 504) and attempt < 2:
                    time.sleep(2 * (attempt + 1))
                    continue
                raise
            except urllib.error.URLError:
                if attempt < 2:
                    time.sleep(2 * (attempt + 1))
                    continue
                raise
        pages.extend(d.get("results", []))
        if d.get("has_more"):
            cursor = d.get("next_cursor")
        else:
            break
    return pages


# ---------- self-test ----------
def selftest():
    prev = {"as_of": "2026-07-19", "count": 3, "rows": {
        "A": {"title": "Acme", "hash": fingerprint({"Rent": "1000", "Status": "Active"}),
              "fields": {"Rent": "1000", "Status": "Active"}},
        "B": {"title": "Beta", "hash": fingerprint({"Rent": "2000"}),
              "fields": {"Rent": "2000"}},
        "C": {"title": "Gone", "hash": fingerprint({"Rent": "50"}),
              "fields": {"Rent": "50"}},
    }}
    curr = {"as_of": "2026-07-20", "count": 3, "rows": {
        "A": {"title": "Acme", "hash": fingerprint({"Rent": "1200", "Status": "Active"}),
              "fields": {"Rent": "1200", "Status": "Active"}},   # changed Rent 1000->1200
        "B": {"title": "Beta", "hash": fingerprint({"Rent": "2000"}),
              "fields": {"Rent": "2000"}},                        # unchanged
        "D": {"title": "New Tenant", "hash": fingerprint({"Rent": "9"}),
              "fields": {"Rent": "9"}},                            # added
        # C removed
    }}
    d = diff_snapshots(prev, curr)
    ok = True
    def check(cond, msg):
        nonlocal ok
        print(("  PASS " if cond else "  FAIL ") + msg)
        ok = ok and cond
    check([x["id"] for x in d["added"]] == ["D"], "added == [D]")
    check([x["id"] for x in d["removed"]] == ["C"], "removed == [C]")
    check(len(d["changed"]) == 1 and d["changed"][0]["id"] == "A", "changed == [A]")
    ch = d["changed"][0]["changes"] if d["changed"] else []
    check(len(ch) == 1 and ch[0]["field"] == "Rent" and ch[0]["old"] == "1000" and ch[0]["new"] == "1200",
          "A.Rent 1000 -> 1200")
    check(d["unchanged"] == 1, "unchanged == 1 (B)")
    # first-run baseline: prev None -> everything is 'added', no crash
    d0 = diff_snapshots(None, curr)
    check(len(d0["added"]) == 3 and not d0["removed"] and not d0["changed"], "baseline: all added, no diff")

    # --- CROSS-DAY REGRESSION (the case the 2026-07-20 same-day sign-off never exercised) ---
    # Two pulls on different days where ONLY date-derived formulas moved. Real answer: nothing
    # changed. Pre-fix this reported every row as changed.
    def mkrow(title, rent, days, months, walt, tenure):
        f = {"Rent": rent, "Days to Expiration": days, "Months Remaining": months,
             "WALT Contribution (Years)": walt, "Tenant Tenure (Months)": tenure}
        return {"title": title, "hash": fingerprint(f), "fields": f}

    day1 = {"as_of": "2026-07-22", "count": 2, "rows": {
        "X": mkrow("Tenant X", "1000", "1834", "60.32", "32800.96", "78"),
        "Y": mkrow("Tenant Y", "2000", "39", "1.28", "160.27", "12"),
    }}
    day3 = {"as_of": "2026-07-24", "count": 2, "rows": {
        "X": mkrow("Tenant X", "1000", "1832", "60.26", "32765.19", "79"),
        "Y": mkrow("Tenant Y", "2000", "37", "1.21", "152.05", "12"),
    }}
    dcd = diff_snapshots(day1, day3)
    check(not dcd["changed"], "cross-day: date-derived-only movement reports 0 changed")
    check(dcd["unchanged"] == 2, "cross-day: unchanged == 2")
    check(not dcd["warnings"], "cross-day: no spurious bulk-field warning")

    # Same cross-day pull, but one row also has a REAL edit -> exactly that row, that field.
    day3b = json.loads(json.dumps(day3))
    day3b["rows"]["Y"]["fields"]["Rent"] = "2500"
    dreal = diff_snapshots(day1, day3b)
    check(len(dreal["changed"]) == 1 and dreal["changed"][0]["id"] == "Y",
          "cross-day: real edit still detected (Y only)")
    check([c["field"] for c in dreal["changed"][0]["changes"]] == ["Rent"],
          "cross-day: only the real field reported, not the derived ones")

    # Migration: a PRE-FIX snapshot (hash + fields include date-derived) vs a POST-FIX one
    # (fields omit them) must NOT report every row as changed.
    prefix_rows = json.loads(json.dumps(day1["rows"]))          # carries derived fields + old hash
    postfix_rows = {}
    for k, v in day3["rows"].items():
        f = {kk: vv for kk, vv in v["fields"].items() if kk not in TIME_DERIVED_FIELDS}
        postfix_rows[k] = {"title": v["title"], "hash": fingerprint(f), "fields": f}
    dmig = diff_snapshots({"as_of": "2026-07-22", "count": 2, "rows": prefix_rows},
                          {"as_of": "2026-07-24", "count": 2, "rows": postfix_rows})
    check(not dmig["changed"], "migration: pre-fix vs post-fix snapshot reports 0 changed")

    # Bulk-field guard fires for a NON-excluded field moving on >50% of rows.
    day3c = json.loads(json.dumps(day3))
    for r in day3c["rows"].values():
        r["fields"]["Rent"] = str(int(r["fields"]["Rent"]) + 1)
    dbulk = diff_snapshots(day1, day3c)
    check(any("'Rent'" in w or '"Rent"' in w for w in dbulk["warnings"]),
          "bulk guard: warns when a non-excluded field moves on >50% of rows")

    # Bulk guard fires at EXACTLY the threshold (>= not >). On a small DB a derived field
    # moving on precisely half the rows is the same signal and must not sail through.
    half_prev = {"as_of": "2026-07-22", "count": 4, "rows": {
        k: {"title": k, "hash": fingerprint({"Rent": "1"}), "fields": {"Rent": "1"}}
        for k in "PQRS"}}
    half_curr = json.loads(json.dumps(half_prev))
    half_curr["as_of"] = "2026-07-24"
    for k in ("P", "Q"):                       # exactly 2 of 4 = 50%
        half_curr["rows"][k]["fields"]["Rent"] = "2"
    dhalf = diff_snapshots(half_prev, half_curr)
    check(len(dhalf["changed"]) == 2, "50pct boundary: 2 of 4 rows changed")
    check(any("'Rent'" in w for w in dhalf["warnings"]),
          "bulk guard fires at exactly 50pct (>= threshold)")

    print("SELFTEST:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


# ---------- run ----------
# A pull that collapses to a fraction of the prior row count is far more likely to be a
# revoked/narrowed integration scope or an unshared DB (Notion still answers 200 with 0
# results) than 250 tenants genuinely vanishing. Persisting that would destroy the baseline
# and make the NEXT run report ~300 spurious "added".
COLLAPSE_FLOOR_RATIO = 0.5


def atomic_write_json(path, obj):
    """Write via tmp + os.replace so a crash mid-write cannot leave truncated JSON.

    A half-written state file is worse than a missing one: it wedges every subsequent
    unattended run until a human repairs it.
    """
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def load_prev():
    """Previous snapshot, or None. A corrupt/unreadable file degrades to a fresh baseline
    with a loud warning rather than raising and killing every future 18:00 run."""
    if not os.path.exists(LATEST):
        return None, None
    try:
        with open(LATEST, encoding="utf-8") as f:
            prev = json.load(f)
        if not isinstance(prev, dict) or not isinstance(prev.get("rows"), dict):
            return None, "previous snapshot has unexpected shape - treated as no baseline"
        return prev, None
    except Exception as e:
        return None, "previous snapshot unreadable (%s: %s) - treated as no baseline" % (
            type(e).__name__, e)


def run(as_of):
    os.makedirs(STATE_DIR, exist_ok=True)
    token = load_token()
    pages = pull_all(TENANT_DB_ID, token)
    curr = build_snapshot(pages, as_of, TENANT_DB_ID)
    prev, load_warning = load_prev()
    d = diff_snapshots(prev, curr)
    baseline = prev is None
    warnings = list(d.get("warnings", []))
    if load_warning:
        warnings.append(load_warning)

    # Persist — unless the pull looks like a collapse, in which case KEEP the old baseline.
    persisted = True
    prev_count = (prev or {}).get("count", 0)
    if prev and (curr["count"] == 0 or curr["count"] < prev_count * COLLAPSE_FLOOR_RATIO):
        persisted = False
        warnings.append(
            "REFUSED to persist snapshot: row count collapsed %d -> %d (below %.0f%% of prior). "
            "Prior baseline kept. Check the Notion integration's database access before trusting "
            "this run's diff." % (prev_count, curr["count"], COLLAPSE_FLOOR_RATIO * 100))
    if persisted:
        atomic_write_json(LATEST, curr)
        atomic_write_json(os.path.join(STATE_DIR, "tenant-db-%s.json" % as_of), curr)

    # human summary
    if baseline:
        print("Baseline established: %d rows snapshotted for %s (no prior snapshot to diff)." % (curr["count"], as_of))
    else:
        print("Tenant DB diff %s -> %s: %d added, %d removed, %d changed, %d unchanged (of %d)." % (
            d["prev_as_of"], as_of, len(d["added"]), len(d["removed"]), len(d["changed"]),
            d["unchanged"], curr["count"]))
        for c in d["changed"][:50]:
            flds = ", ".join("%s: %s -> %s" % (x["field"], x["old"], x["new"]) for x in c["changes"][:6])
            print("   CHANGED  %s  [%s]" % (c["title"], flds))
        for a in d["added"][:50]:
            print("   ADDED    %s" % a["title"])
        for r in d["removed"][:50]:
            print("   REMOVED  %s" % r["title"])
    # Warnings MUST reach the caller. They were previously computed and dropped here, which
    # made the bulk-field guard dead in production (it only ever fired via --selftest).
    for w in warnings:
        print("   WARNING  %s" % w)
    result = {"baseline": baseline, "prev_as_of": d["prev_as_of"], "curr_as_of": as_of,
              "count": curr["count"], "added": d["added"], "removed": d["removed"],
              "changed": d["changed"], "unchanged": d["unchanged"],
              "warnings": warnings, "persisted": persisted}
    print("RESULT_JSON=" + json.dumps(result, ensure_ascii=True))  # ASCII-safe for any downstream pipe encoding
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--date", default=datetime.date.today().isoformat())
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.run:
        return run(a.date)
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
