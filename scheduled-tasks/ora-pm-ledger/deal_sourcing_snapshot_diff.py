#!/usr/bin/env python3
"""
deal_sourcing_snapshot_diff.py  --  ora-pm-ledger Block A helper.

WHY THIS EXISTS
  Unlike the three Section B sources this script's siblings were built for
  (Tenant DB, Property Register, CapEx & Maintenance Log), the Deal Sourcing
  Log's native `Last Updated` column is NOT broken -- SKILL.md's A.1 Reality
  table marks it "LIVE -- varies" (dates spread 2026-03-22 to 2026-07-15,
  confirmed live). The REST last-edited-time query therefore remains a real,
  working signal for THIS run and should keep being used for the coarse
  "did this row change today" question.

  What the timestamp query cannot do is say WHAT changed. For a deal-sourcing
  log, the field-level detail is the whole point -- a broker cutting an asking
  price, a status flip to "Dead", a Go/No-Go verdict changing -- and knowing
  only that a row's timestamp moved gives Gabriel none of that. This script
  adds the same snapshot+diff mechanism as its three siblings (full paginated
  pull -> per-row fingerprint -> diff against yesterday's persisted snapshot)
  as a field-level ADDITION alongside the existing timestamp check, not a
  replacement for it -- see SKILL.md Block A / A.2 for how the two are folded
  together.

WHAT IT DOES
  --run [--date YYYY-MM-DD]
     1. Pulls every Deal Sourcing Log row via REST (paginated).
     2. Normalizes each row's properties to plain values (skipping volatile
        metadata: created/last_edited time+by), fingerprints each row (sha256).
     3. Loads the previous snapshot (state/deal-sourcing-latest.json).
     4. Emits a diff: added / removed / changed (field-level old->new), keyed
        on the Notion PAGE ID -- never on "Deal Name / Address", which is a
        free-text title field an agent or Gabriel can rename at will and is
        therefore not a stable row identity (a rename would otherwise read as
        one row removed + a different one added).
     5. Writes the new snapshot to latest + a dated archive.
     6. Prints a JSON block on the last line prefixed `RESULT_JSON=` for the
        caller (the digest) to parse. First run = baseline, no diff.
  --selftest
     Runs the diff engine against synthetic snapshots, no network. Exit 0 = pass.

DATE-DERIVED FIELDS -- NONE FOUND, checked live 2026-08-15
  The schema carries exactly one formula field: 'Price Delta vs First Ask'.
  Read the live data rather than inferred from its name (per the hard-won
  lesson in tenant_db_snapshot_diff.py's TIME_DERIVED_FIELDS comment and
  memory/reference_lease_date_detector_defects_2026-07-24.md): pulled sample
  rows via REST and confirmed the formula resolves to a STRING derived purely
  from two other STATIC stored number fields on the same row -- 'Asking Price'
  and 'Ask at First Sighting' -- e.g. 'CUT -7% (2320000 to 2150000)' or
  'unchanged' when the two are equal. No date/now()/calendar input is
  involved: two rows checked on the same pull with identical Asking Price and
  Ask at First Sighting both string "unchanged", and eight rows with a real
  price gap each showed a value matching Asking Price - Ask at First Sighting
  exactly. This is exactly the kind of static-input formula
  property_register_snapshot_diff.py's 'LTV' is -- a real, governor-adjacent-
  style change signal (a price cut is precisely what Gabriel wants surfaced,
  not filtered) -- so TIME_DERIVED_FIELDS stays EMPTY here, same as CapEx. The
  bulk-field guard below is the backstop if that ever turns out wrong, or if a
  calendar-derived formula is added to this database later.

STORAGE
  state/deal-sourcing-latest.json         <- previous/current pointer
  state/deal-sourcing-<YYYY-MM-DD>.json   <- dated archive (audit trail)

TOKEN
  NOTION_TOKEN from C:\\Users\\Owner\\oxford-command-center\\.env (read-only).

ENDPOINT
  This id (9a6ae219...) is a DATA SOURCE id, not a database page id (the
  canonical pair per SKILL.md A.1 is database `8d2ddc5177e84cd7b1c0c0f6ef943479`
  / data source `9a6ae219-85a3-4621-899c-c757fd062f8b`). Query it at
  `POST /v1/data_sources/{id}/query` with `Notion-Version: 2025-09-03` --
  verified 200 live 2026-08-15, 479 rows. The older `/v1/databases/{id}/query`
  @ 2022-06-28 pair the other three siblings use is for single-source
  databases; this id is a data-source id and uses the newer endpoint/version,
  matching how SKILL.md documents the Acquisition Pipeline Tracker sibling.
"""
import argparse, datetime, hashlib, json, os, sys, time, urllib.request, urllib.error

# Harness-spawned/scheduled runs get a cp1252 stdout on Windows; deal titles and
# Go/No-Go values carry emoji (e.g. 🟢/🟡/🔴/⏳). Force UTF-8 so prints never crash.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# Data-source id (NOT the database page id -- see ENDPOINT note in the module
# docstring). REST /data_sources/{id}/query @ 2025-09-03 = 200, verified live
# 2026-08-15, 479 rows.
DEAL_SOURCING_DB_ID = "9a6ae219-85a3-4621-899c-c757fd062f8b"
ENV_PATH = r"C:\Users\Owner\oxford-command-center\.env"
STATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state")
LATEST = os.path.join(STATE_DIR, "deal-sourcing-latest.json")
ARCHIVE_PREFIX = "deal-sourcing-2"
SKIP_TYPES = {"created_time", "last_edited_time", "created_by", "last_edited_by"}

# See the DATE-DERIVED FIELDS note in the module docstring. 'Price Delta vs
# First Ask' was checked live and confirmed to derive only from two static
# stored numbers (Asking Price, Ask at First Sighting) -- it is deliberately
# NOT in this set, matching 'LTV' on the Property Register sibling: excluding
# by NAME, never by TYPE, keeps a real price-movement signal alive. Empty
# today; the bulk-field guard is the backstop if that verdict is ever wrong.
TIME_DERIVED_FIELDS = set()

# A field changing on more than this share of all rows is almost certainly bulk/derived
# rather than edited, and is reported as a warning instead of silently inflating the diff.
BULK_FIELD_RATIO = 0.5


# ---------- property normalization ----------
def _people(v):
    return "|".join(sorted(p.get("id", "") for p in v or []))

def _array_digest(arr, _depth=0):
    """Order-sensitive content digest of a rollup array's elements (OI-151, carried
    forward from property_register_snapshot_diff.py). No rollup field exists on this
    database today (checked live 2026-08-15 -- schema carries none), but this keeps
    norm_prop forward-safe if one is ever added, at zero cost while it stays unused.

    sha1 is a fingerprint here, not a security primitive: the only property needed
    is that different content produces a different token.
    """
    parts = []
    for el in arr:
        if isinstance(el, dict) and el.get("type") and _depth < 3:
            try:
                v = norm_prop(el, _depth=_depth + 1)
            except Exception:
                v = None
            parts.append("\x00" if v is None else str(v))
        else:
            parts.append(json.dumps(el, sort_keys=True, default=str))
    return hashlib.sha1("\x1f".join(parts).encode("utf-8")).hexdigest()[:12]


def norm_prop(p, _depth=0):
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
        # This database carries two relation fields (Owner Outreach Lead, Pipeline
        # Deal). Sorted id join keeps the value stable across re-reads regardless of
        # Notion's return order.
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
            arr = r.get("array", [])
            if not arr:
                return "[array:0]"
            return "[array:%d:%s]" % (len(arr), _array_digest(arr, _depth))
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

    Applied on BOTH sides of the diff so a snapshot written before a field was added
    to TIME_DERIVED_FIELDS still compares cleanly against one written after -- see
    tenant_db_snapshot_diff.py's 2026-07-24 fix for the incident this pattern exists
    to prevent (267 of 298 rows false-positived on the first cross-day run there).
    """
    return {k: v for k, v in (row.get("fields") or {}).items() if k not in TIME_DERIVED_FIELDS}


def fingerprint(fields):
    blob = json.dumps(fields, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def detect_truncation(pages):
    """Warnings for any property value Notion truncated in the query response.

    Notion caps multi-reference property values (relation, people, and rollup arrays) at 25
    items in database-query results and sets `has_more` ON THE PROPERTY OBJECT. This database
    carries two relation fields (Owner Outreach Lead, Pipeline Deal); if either ever exceeds
    25 linked pages on one row, this row's fingerprint would silently cover only the first 25
    and miss further additions -- carried forward from property_register_snapshot_diff.py,
    where the same defect class was raised by independent review 2026-08-11.
    """
    warns = []
    for pg in pages:
        title = title_of(pg.get("properties", {}))
        for name, p in (pg.get("properties") or {}).items():
            if name in TIME_DERIVED_FIELDS:
                continue
            truncated = p.get("has_more")
            if not truncated and p.get("type") == "rollup":
                truncated = (p.get("rollup") or {}).get("has_more")
            if truncated:
                warns.append(
                    "row %r property %r was TRUNCATED by Notion at 25 items (has_more=true). "
                    "Its fingerprint covers only the first 25, so changes beyond that are "
                    "invisible and this field may also churn spuriously. Do not trust an "
                    "unchanged/changed verdict for this field." % (title, name))
    return warns


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
    # edited. Surface it loudly instead of letting it inflate the diff unnoticed -- exactly
    # how the Tenant DB's date-derived-formula defect went undetected until 2026-07-24.
    warnings = []
    # Denominate by rows present in BOTH snapshots, not by all current rows (property
    # register's 2026-08-11 independent-review fix) -- using len(c) systematically dilutes
    # the ratio and lets a partially-populated derived field slip under the threshold forever.
    total = len(set(p) & set(c))
    if total:
        freq = {}
        for row in changed:
            for ch in row["changes"]:
                freq[ch["field"]] = freq.get(ch["field"], 0) + 1
        for field, n in sorted(freq.items(), key=lambda kv: -kv[1]):
            # >= not >: a derived field moving on EXACTLY half the rows is the same signal,
            # and that boundary is easy to land on.
            if n / total >= BULK_FIELD_RATIO:
                warnings.append(
                    "field %r changed on %d/%d compared rows (%.0f%%) — likely derived, "
                    "bulk-written, or a SCHEMA CHANGE (a rename/add makes every row report "
                    "<absent> -> value). Diagnose which before excluding anything, and never "
                    "exclude 'Price Delta vs First Ask' without re-verifying it against live "
                    "data first — it is a static-input formula and a real price-movement signal."
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


def _http_page(db_id, token, body):
    """One POST to Notion's data-source query endpoint, with bounded retry. Split out
    from pull_all so the pagination loop can be exercised offline by --selftest via the
    `fetch` seam. Uses /v1/data_sources/{id}/query @ 2025-09-03 -- see the module
    docstring's ENDPOINT note for why this differs from the three siblings' /v1/databases
    @ 2022-06-28 (this id is a data-source id, not a database page id)."""
    req = urllib.request.Request(
            "https://api.notion.com/v1/data_sources/%s/query" % db_id,
            data=json.dumps(body).encode(),
            headers={"Authorization": "Bearer " + token,
                     "Notion-Version": "2025-09-03",
                     "Content-Type": "application/json"},
            method="POST")
    # Bounded retry on rate-limit/transient server errors. Unattended at 18:00, one
    # Notion hiccup would otherwise be an unhandled HTTPError and a lost run.
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and attempt < 2:
                time.sleep(2 * (attempt + 1))
                continue
            raise
        except OSError:
            # Covers a failure to connect AND a timeout reading the response body (a
            # socket-read timeout raises TimeoutError, which is neither HTTPError nor
            # URLError -- OSError is the common base of both plus ConnectionReset etc.).
            # Carried forward from property_register_snapshot_diff.py's OI-152 fix. A
            # malformed body still raises JSONDecodeError (a ValueError) and is correctly
            # NOT retried, since it isn't transient.
            if attempt < 2:
                time.sleep(2 * (attempt + 1))
                continue
            raise


def pull_all(db_id, token, fetch=None):
    """All rows, following pagination. `fetch(db_id, token, body) -> dict` is injectable
    for offline testing; it defaults to the real HTTP call."""
    fetch = fetch or _http_page
    pages, cursor, guard = [], None, 0
    while True:
        guard += 1
        if guard > 200:   # a hard backstop against any unforeseen loop shape
            raise RuntimeError("pull_all exceeded %d pages - aborting suspected loop" % guard)
        body = {"page_size": 100}
        if cursor:
            body["start_cursor"] = cursor
        d = fetch(db_id, token, body)
        pages.extend(d.get("results", []))
        if not d.get("has_more"):
            break
        cursor = d.get("next_cursor")
        # Notion's contract says next_cursor is non-null whenever has_more is true. If it
        # ever isn't, re-sending the same body would refetch page 1 forever — an infinite
        # loop in an unattended 18:00 job. Stop and let the collapse guard judge a short pull.
        if not cursor:
            break
    return pages


# ---------- self-test ----------
def selftest():
    ok = True
    def check(cond, msg):
        nonlocal ok
        print(("  PASS " if cond else "  FAIL ") + msg)
        ok = ok and cond

    # ---- core diff engine ----
    prev = {"as_of": "2026-08-13", "count": 3, "rows": {
        "A": {"title": "321 W 7th St — Richmond, VA",
              "hash": fingerprint({"Status": "Reviewing", "Asking Price": "2320000"}),
              "fields": {"Status": "Reviewing", "Asking Price": "2320000"}},
        "B": {"title": "10 Hill St — Kansas City, KS",
              "hash": fingerprint({"Status": "New Lead"}),
              "fields": {"Status": "New Lead"}},
        "C": {"title": "Dead deal — never closes",
              "hash": fingerprint({"Status": "Dead"}),
              "fields": {"Status": "Dead"}},
    }}
    curr = {"as_of": "2026-08-15", "count": 3, "rows": {
        "A": {"title": "321 W 7th St — Richmond, VA",
              "hash": fingerprint({"Status": "Reviewing", "Asking Price": "2150000"}),
              "fields": {"Status": "Reviewing", "Asking Price": "2150000"}},   # price cut
        "B": {"title": "10 Hill St — Kansas City, KS",
              "hash": fingerprint({"Status": "New Lead"}),
              "fields": {"Status": "New Lead"}},                              # unchanged
        "D": {"title": "New sighting — 7520 W Washington St",
              "hash": fingerprint({"Status": "New Lead"}),
              "fields": {"Status": "New Lead"}},                              # added
        # C removed
    }}
    d = diff_snapshots(prev, curr)
    check([x["id"] for x in d["added"]] == ["D"], "added == [D]")
    check([x["id"] for x in d["removed"]] == ["C"], "removed == [C]")
    check(len(d["changed"]) == 1 and d["changed"][0]["id"] == "A", "changed == [A]")
    ch = d["changed"][0]["changes"] if d["changed"] else []
    check(len(ch) == 1 and ch[0]["field"] == "Asking Price"
          and ch[0]["old"] == "2320000" and ch[0]["new"] == "2150000",
          "A.Asking Price 2320000 -> 2150000")
    check(d["unchanged"] == 1, "unchanged == 1 (B)")
    d0 = diff_snapshots(None, curr)
    check(len(d0["added"]) == 3 and not d0["removed"] and not d0["changed"], "baseline: all added, no diff")

    # ---- diff key is the Notion PAGE ID, never the title ----
    # A row whose title (Deal Name / Address) is edited but whose page id is unchanged
    # must be reported as a CHANGED row (title moved), never as one removed + one added.
    prev_rename = {"as_of": "2026-08-13", "count": 1, "rows": {
        "X": {"title": "5207 Holland Dr", "hash": fingerprint({"Status": "Reviewing"}),
              "fields": {"Status": "Reviewing"}}}}
    curr_rename = {"as_of": "2026-08-15", "count": 1, "rows": {
        "X": {"title": "5207 & 5209 Holland Dr — corrected address",
              "hash": fingerprint({"Status": "Reviewing"}), "fields": {"Status": "Reviewing"}}}}
    drn = diff_snapshots(prev_rename, curr_rename)
    check(not drn["added"] and not drn["removed"],
          "title-only edit under a stable page id is NOT added+removed")

    # ---- TIME_DERIVED_FIELDS: the REAL production set is EMPTY ----
    # Unlike the Property Register sibling (two real calendar-derived formulas),
    # 'Price Delta vs First Ask' was checked live and found to derive only from two
    # static stored numbers -- so it must NOT be excluded. This assertion exercises the
    # actual production constant so it fails loudly if a future edit adds something to it
    # without re-verifying against live data first.
    check(TIME_DERIVED_FIELDS == set(),
          "production set is EMPTY (Price Delta vs First Ask verified static-input, not calendar-derived)")

    def mkprop(title, status, price_delta, asking, first_ask):
        f = {"Status": status, "Price Delta vs First Ask": price_delta,
             "Asking Price": asking, "Ask at First Sighting": first_ask}
        f = {k: v for k, v in f.items() if k not in TIME_DERIVED_FIELDS}
        return {"title": title, "hash": fingerprint(f), "fields": f}

    # A real price cut changes 'Price Delta vs First Ask' alongside 'Asking Price' -- both
    # MUST be reported, proving the formula field is a live signal, not silently dropped.
    day1 = {"as_of": "2026-08-13", "count": 1, "rows": {
        "Y": mkprop("321 W 7th St", "Reviewing", "unchanged", "2320000", "2320000"),
    }}
    day2 = {"as_of": "2026-08-15", "count": 1, "rows": {
        "Y": mkprop("321 W 7th St", "Reviewing", "CUT -7% (2320000 to 2150000)", "2150000", "2320000"),
    }}
    dreal = diff_snapshots(day1, day2)
    check(len(dreal["changed"]) == 1 and dreal["changed"][0]["id"] == "Y",
          "a real price cut is detected")
    changed_fields = {c["field"] for c in dreal["changed"][0]["changes"]}
    check("Price Delta vs First Ask" in changed_fields and "Asking Price" in changed_fields,
          "both the formula AND its static input are reported — the formula is NOT filtered out")

    # Same-day rerun with nothing touched: zero changes, no spurious warnings. Since
    # TIME_DERIVED_FIELDS is empty there is no calendar-drift case to construct here (that
    # regression class does not apply to this database) -- unlike the Tenant DB / Property
    # Register siblings. A stable no-op pull is still asserted so a future accidental
    # addition to TIME_DERIVED_FIELDS would show up as a behavior change here.
    dstable = diff_snapshots(day1, day1)
    check(not dstable["changed"] and not dstable["warnings"], "identical re-pull: 0 changed, 0 warnings")

    # Migration: a snapshot written before TIME_DERIVED_FIELDS existed (irrelevant here since
    # it's empty, but the comparable_fields() helper must still be a no-op) compares cleanly.
    dmig = diff_snapshots(day1, day2)
    check(comparable_fields(day1["rows"]["Y"]) == day1["rows"]["Y"]["fields"],
          "comparable_fields() is a no-op when TIME_DERIVED_FIELDS is empty")

    # ---- bulk-field guard ----
    bulk_prev = {"as_of": "2026-08-13", "count": 4, "rows": {
        k: {"title": k, "hash": fingerprint({"Source": "Crexi"}), "fields": {"Source": "Crexi"}}
        for k in "PQRS"}}
    bulk_curr = json.loads(json.dumps(bulk_prev))
    bulk_curr["as_of"] = "2026-08-15"
    for k in ("P", "Q", "R"):                  # 3 of 4 = 75%
        bulk_curr["rows"][k]["fields"]["Source"] = "Broker — Direct"
    dbulk = diff_snapshots(bulk_prev, bulk_curr)
    check(any("'Source'" in w for w in dbulk["warnings"]),
          "bulk guard: warns when a field moves on >50% of rows")

    half_curr = json.loads(json.dumps(bulk_prev))
    half_curr["as_of"] = "2026-08-15"
    for k in ("P", "Q"):                       # exactly 2 of 4 = 50%
        half_curr["rows"][k]["fields"]["Source"] = "Broker — Direct"
    dhalf = diff_snapshots(bulk_prev, half_curr)
    check(len(dhalf["changed"]) == 2, "50pct boundary: 2 of 4 rows changed")
    check(any("'Source'" in w for w in dhalf["warnings"]),
          "bulk guard fires at exactly 50pct (>= threshold)")

    # Bulk guard denominates by COMPARED rows, not all current rows (property register's
    # 2026-08-11 review fix). 5 of 5 rows sharing a field must trip it even against a
    # much larger current pull.
    sub_prev = {"as_of": "2026-08-13", "count": 5, "rows": {
        "L%d" % i: {"title": "L%d" % i, "hash": "h", "fields": {"Notes / Flags": "old"}}
        for i in range(5)}}
    sub_curr = {"as_of": "2026-08-15", "count": 200, "rows": {}}
    for i in range(5):
        sub_curr["rows"]["L%d" % i] = {"title": "L%d" % i, "hash": "h", "fields": {"Notes / Flags": "new"}}
    for i in range(195):
        sub_curr["rows"]["N%d" % i] = {"title": "N%d" % i, "hash": "h", "fields": {}}
    dsub = diff_snapshots(sub_prev, sub_curr)
    check(any("Notes / Flags" in w and "compared rows" in w for w in dsub["warnings"]),
          "bulk guard denominates by COMPARED rows (5/5), not all current rows (5/200)")

    # ---- normalization spot-checks ----
    check(norm_prop({"type": "title", "title": [{"plain_text": "1315 W 12th St"}]}) == "1315 W 12th St",
          "norm_prop: title normalizes")
    check(norm_prop({"type": "number", "number": 4875000.0}) == repr(4875000.0),
          "norm_prop: number normalizes stably")
    check(norm_prop({"type": "select", "select": {"name": "🟢 Go — Submit LOI"}}) == "🟢 Go — Submit LOI",
          "norm_prop: select with emoji normalizes")
    check(norm_prop({"type": "relation", "relation": [{"id": "b"}, {"id": "a"}]}) == "a|b",
          "norm_prop: relation ids sort deterministically")
    check(norm_prop({"type": "created_time", "created_time": "2026-03-22T00:00:00Z"}) is None,
          "norm_prop: 'Date Added' (created_time) is skipped as metadata")
    check(norm_prop({"type": "last_edited_time", "last_edited_time": "2026-08-15T00:00:00Z"}) is None,
          "norm_prop: 'Last Updated' (last_edited_time) is skipped as metadata")
    check(norm_prop({"type": "formula", "formula": {"type": "string", "string": "unchanged"}}) == "unchanged",
          "norm_prop: string-formula (Price Delta vs First Ask) normalizes")

    # ---- pagination ----
    calls = {"n": 0}
    def bad_fetch(db_id, token, body):
        calls["n"] += 1
        return {"results": [{"id": "p%d" % calls["n"], "properties": {}}],
                "has_more": True, "next_cursor": None}
    got = pull_all("db", "tok", fetch=bad_fetch)
    check(calls["n"] == 1 and len(got) == 1, "null next_cursor with has_more stops after 1 page")

    seq = [{"results": [{"id": "a"}], "has_more": True, "next_cursor": "c1"},
           {"results": [{"id": "b"}], "has_more": True, "next_cursor": "c2"},
           {"results": [{"id": "c"}], "has_more": False, "next_cursor": None}]
    seen_cursors = []
    def good_fetch(db_id, token, body):
        seen_cursors.append(body.get("start_cursor"))
        return seq[len(seen_cursors) - 1]
    allrows = pull_all("db", "tok", fetch=good_fetch)
    check([r["id"] for r in allrows] == ["a", "b", "c"], "pagination concatenates all pages")
    check(seen_cursors == [None, "c1", "c2"], "pagination forwards each next_cursor exactly once")

    # ---- load_prev() corruption / missing fallback ----
    global STATE_DIR, LATEST
    real_dir, real_latest = STATE_DIR, LATEST
    tmpdir = os.path.join(real_dir, "_selftest_tmp_dealsourcing")
    try:
        os.makedirs(tmpdir, exist_ok=True)
        STATE_DIR, LATEST = tmpdir, os.path.join(tmpdir, "deal-sourcing-latest.json")
        good = {"as_of": "2026-08-13", "db_id": "x", "count": 1,
                "rows": {"A": {"title": "321 W 7th St", "hash": "h", "fields": {"Status": "Reviewing"}}}}
        with open(os.path.join(tmpdir, "deal-sourcing-2026-08-13.json"), "w", encoding="utf-8") as f:
            json.dump(good, f)
        with open(LATEST, "w", encoding="utf-8") as f:
            f.write("{ truncated")
        prevx, warn = load_prev()
        check(prevx is not None and prevx.get("count") == 1,
              "corrupt LATEST falls back to newest dated archive")
        check(warn and "archive" in warn, "archive fallback is reported, not silent")

        os.remove(os.path.join(tmpdir, "deal-sourcing-2026-08-13.json"))
        prev2, warn2 = load_prev()
        check(prev2 is None and warn2 and "no readable archive" in warn2,
              "no archive -> honest no-baseline with a warning")
    finally:
        for n in os.listdir(tmpdir) if os.path.isdir(tmpdir) else []:
            os.remove(os.path.join(tmpdir, n))
        if os.path.isdir(tmpdir):
            os.rmdir(tmpdir)
        STATE_DIR, LATEST = real_dir, real_latest

    # ---- decide_persist() ----
    with_prior = {"count": 479}

    p, w = decide_persist(None, 0, "previous snapshot unreadable (fake)")
    check(not p, "decide_persist: refuses when curr=0 and load_warning is set (prev=None)")
    check(w and "Two independent failure signals" in w,
          "decide_persist: 0-row+degraded-load takes its OWN branch")
    check(w and "REFUSED" in w, "decide_persist: refusal is a loud warning, not silent")
    p2, w2 = decide_persist(with_prior, 0, "previous snapshot unreadable (fake)")
    check(not p2, "decide_persist: refuses when curr=0 and load_warning is set (prev_count>0)")

    # This database is an accreting log (479 rows today; rows are marked Dead/Passed, never
    # purged -- see the module docstring). A 0-row pull is therefore ALWAYS an access failure,
    # same divergence from CapEx as property_register_snapshot_diff.py: never allowed to
    # establish a baseline, even on a genuine first-ever run.
    p3, w3 = decide_persist(None, 0, None)
    check(not p3, "decide_persist: refuses a 0-row FIRST run (an empty deal-sourcing log is never real)")
    check(w3 and "REFUSED" in w3 and "never" in w3.lower(),
          "decide_persist: the 0-row first-run refusal explains why")

    p4, w4 = decide_persist(with_prior, 0, None)
    check(not p4, "decide_persist: refuses 0 rows against a prior non-empty baseline")
    check(w4 and "REFUSED" in w4 and "0 rows" in w4, "decide_persist: refusal names the cause")

    # Exact 50% collapse must refuse -- matching the bulk-field guard's >= boundary.
    p5, w5 = decide_persist(with_prior, 240, None)   # 240/479 = 50.1%, just above
    check(p5 and w5 is None, "decide_persist: just above 50pct persists cleanly")
    p5b, w5b = decide_persist({"count": 480}, 240, None)   # exactly 50.0% of 480
    check(not p5b, "decide_persist: refuses at the exact 50pct collapse boundary")
    p6, w6 = decide_persist(with_prior, 479, None)
    check(p6 and w6 is None, "decide_persist: a normal same-count pull persists silently (no warning)")

    # ---- truncation detection ----
    trunc_pages = [{"id": "p1", "properties": {
        "Deal Name / Address": {"type": "title", "title": [{"plain_text": "9050 Red Branch Rd"}]},
        "Pipeline Deal": {"type": "relation", "relation": [{"id": "t%d" % i} for i in range(25)],
                          "has_more": True},
        "Status": {"type": "select", "select": {"name": "Reviewing"}},
    }}]
    tw = detect_truncation(trunc_pages)
    check(len(tw) == 1 and "Pipeline Deal" in tw[0] and "9050 Red Branch Rd" in tw[0],
          "detect_truncation: flags a has_more relation, naming row and field")
    check(not detect_truncation([{"id": "p1", "properties": {
        "Pipeline Deal": {"type": "relation", "relation": [{"id": "t1"}]}}}]),
          "detect_truncation: silent when nothing is truncated")

    # ---- --date validation ----
    def date_ok(s):
        try:
            datetime.date.fromisoformat(s); return True
        except ValueError:
            return False
    check(not date_ok("{TODAY}") and date_ok("2026-08-15"),
          "--date validation rejects '{TODAY}' and accepts a real ISO date")

    # ---- end-to-end run() ----
    real_dir2, real_latest2 = STATE_DIR, LATEST
    tmp2 = os.path.join(real_dir2, "_selftest_tmp_run")
    import io, contextlib
    try:
        os.makedirs(tmp2, exist_ok=True)
        STATE_DIR, LATEST = tmp2, os.path.join(tmp2, "deal-sourcing-latest.json")

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            run("2026-08-15", _pages=[])          # 0-row pull, no prior baseline
        out = buf.getvalue()
        res = json.loads(out.rsplit("RESULT_JSON=", 1)[1].strip())
        check(res["persisted"] is False, "e2e refusal: persisted is False")
        check(res["baseline"] is False, "e2e refusal: baseline is False")
        check("Baseline established" not in out, "e2e refusal: does NOT print 'Baseline established'")
        check("REFUSED" in out, "e2e refusal: says REFUSED in the human summary")
        check(not os.path.exists(LATEST), "e2e refusal: no state file written")

        good_pages = [{"id": "pA", "properties": {
            "Deal Name / Address": {"type": "title", "title": [{"plain_text": "321 W 7th St"}]},
            "Status": {"type": "select", "select": {"name": "Reviewing"}}}}]
        buf2 = io.StringIO()
        with contextlib.redirect_stdout(buf2):
            run("2026-08-15", _pages=good_pages)
        res2 = json.loads(buf2.getvalue().rsplit("RESULT_JSON=", 1)[1].strip())
        check(res2["persisted"] and res2["baseline"] and res2["count"] == 1,
              "e2e baseline: a real first run persists and reports baseline true")

        os.remove(LATEST)
        prev3, warn3 = load_prev()
        check(prev3 is not None and prev3["count"] == 1,
              "missing LATEST falls back to the newest dated archive")
        check(warn3 and "MISSING" in warn3, "missing LATEST is reported loudly, not treated as 'no baseline'")
    finally:
        for n in os.listdir(tmp2) if os.path.isdir(tmp2) else []:
            os.remove(os.path.join(tmp2, n))
        if os.path.isdir(tmp2):
            os.rmdir(tmp2)
        STATE_DIR, LATEST = real_dir2, real_latest2

    print("SELFTEST:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


# ---------- run ----------
# A pull that collapses to a fraction of the prior row count is far more likely to be a
# revoked/narrowed integration scope or an unshared DB (Notion still answers 200 with 0
# results) than several hundred deal-sourcing log rows genuinely vanishing between two runs.
# Persisting that would destroy the baseline and make the NEXT run report every remaining
# row as spuriously "added".
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


def _read_snapshot(path):
    with open(path, encoding="utf-8") as f:
        snap = json.load(f)
    if not isinstance(snap, dict) or not isinstance(snap.get("rows"), dict):
        raise ValueError("unexpected shape")
    return snap


def newest_archive():
    """Newest dated archive, or (None, None). Archives are the audit trail and are written
    alongside LATEST, so they are the natural fallback when LATEST is damaged."""
    try:
        names = sorted(n for n in os.listdir(STATE_DIR)
                       if n.startswith(ARCHIVE_PREFIX) and n.endswith(".json"))
    except OSError:
        return None, None
    for name in reversed(names):
        try:
            return _read_snapshot(os.path.join(STATE_DIR, name)), name
        except Exception:
            continue
    return None, None


def load_prev():
    """Previous snapshot, or None.

    A corrupt/unreadable/missing LATEST degrades gracefully rather than raising and killing
    every future 18:00 run. It falls back to the newest dated archive BEFORE giving up:
    without that, corruption or deletion masquerades as 'no baseline', which disables the
    collapse guard below and lets a simultaneously-collapsed pull overwrite the baseline with
    an empty snapshot. Pattern carried forward from property_register_snapshot_diff.py's
    2026-08-11 independent-review fix.
    """
    if not os.path.exists(LATEST):
        arch, name = newest_archive()
        if arch is not None:
            return arch, ("LATEST snapshot file is MISSING - fell back to archive %s for the "
                          "diff baseline. If this was a deliberate reset, delete the archives "
                          "too; otherwise investigate what removed it." % name)
        return None, None
    try:
        return _read_snapshot(LATEST), None
    except Exception as e:
        why = "previous snapshot unreadable (%s: %s)" % (type(e).__name__, e)
        arch, name = newest_archive()
        if arch is not None:
            return arch, why + " - fell back to archive %s for the diff baseline" % name
        return None, why + " - and no readable archive; treated as no baseline"


def decide_persist(prev, curr_count, load_warning):
    """Whether to persist a pull of `curr_count` rows, and any extra warning to surface.

    A pure function so the persist/refusal decision -- the one part of this file with real
    production risk -- is directly exercised by --selftest. Pattern carried forward from
    property_register_snapshot_diff.py.

    ONE DELIBERATE CHOICE, matching Property Register rather than CapEx: the
    0-row-with-no-prior-baseline case REFUSES here instead of persisting with a warning. This
    database is an accreting sourcing log -- 479 rows live 2026-08-15, deals that die stay as
    'Dead'/'Passed'/'KILLED' rows rather than being removed -- so a 0-row pull is always an
    access failure (revoked/narrowed integration scope, or the database unshared; Notion
    answers 200 with an empty result set in all of those cases), never a real empty state.

    Returns (persisted: bool, warning: str or None). `warning` is set on every refusal.
    """
    prev_count = (prev or {}).get("count", 0)

    if curr_count == 0 and load_warning:
        return False, (
            "REFUSED to persist snapshot: pull returned 0 rows AND the previous snapshot "
            "load was already degraded (%s). Two independent failure signals at once is "
            "never trustworthy. Prior state kept." % load_warning)

    if curr_count == 0:
        if prev_count > 0:
            return False, (
                "REFUSED to persist snapshot: pull returned 0 rows against a prior non-empty "
                "baseline (%d rows). Check the Notion integration's database access before "
                "trusting this as a real deletion. Prior snapshot kept." % prev_count)
        return False, (
            "REFUSED to persist snapshot: pull returned 0 rows and there is no prior "
            "baseline. An empty Deal Sourcing Log is never a real state — sourced deals "
            "accrete and are marked Dead/Passed/KILLED rather than removed — so this is an "
            "access failure (revoked/narrowed integration scope, or the database is no "
            "longer shared with it), not an empty table. Fix access, then re-run to "
            "establish the baseline.")

    if prev_count > 0 and curr_count <= prev_count * COLLAPSE_FLOOR_RATIO:
        return False, (
            "REFUSED to persist snapshot: row count collapsed %d -> %d (at or below %.0f%% "
            "of prior). Prior baseline kept. Check the Notion integration's database access "
            "before trusting this run's diff."
            % (prev_count, curr_count, COLLAPSE_FLOOR_RATIO * 100))

    return True, None


def run(as_of, _pages=None):
    """`_pages` injects an already-fetched page list, bypassing token load + HTTP.

    Exists so --selftest can drive this function end-to-end offline, matching the seam
    property_register_snapshot_diff.py added after an independent review found the
    persist/refusal REPORTING path (not any pure helper) was where a real defect lived.
    """
    os.makedirs(STATE_DIR, exist_ok=True)
    if _pages is None:
        token = load_token()
        pages = pull_all(DEAL_SOURCING_DB_ID, token)
    else:
        pages = _pages
    curr = build_snapshot(pages, as_of, DEAL_SOURCING_DB_ID)
    prev, load_warning = load_prev()
    d = diff_snapshots(prev, curr)
    warnings = list(d.get("warnings", []))
    warnings.extend(detect_truncation(pages))
    if load_warning:
        warnings.append(load_warning)

    persisted, persist_note = decide_persist(prev, curr["count"], load_warning)
    if persist_note:
        warnings.append(persist_note)
    if persisted:
        atomic_write_json(LATEST, curr)
        atomic_write_json(os.path.join(STATE_DIR, "deal-sourcing-%s.json" % as_of), curr)

    # A refused run establishes NOTHING. `baseline` depends on `persisted`, not merely on
    # `prev is None` -- see property_register_snapshot_diff.py's run() docstring for the
    # exact defect class (a refused run printing "Baseline established" and reporting
    # baseline:true) this guards against.
    baseline = prev is None and persisted

    # human summary
    if not persisted:
        print("REFUSED: no snapshot persisted for %s (%d rows pulled). Prior state kept, "
              "NO baseline established. See WARNING below." % (as_of, curr["count"]))
    elif baseline:
        print("Baseline established: %d rows snapshotted for %s (no prior snapshot to diff)." % (curr["count"], as_of))
    else:
        print("Deal Sourcing Log diff %s -> %s: %d added, %d removed, %d changed, %d unchanged (of %d)." % (
            d["prev_as_of"], as_of, len(d["added"]), len(d["removed"]), len(d["changed"]),
            d["unchanged"], curr["count"]))
        for c in d["changed"][:50]:
            flds = ", ".join("%s: %s -> %s" % (x["field"], x["old"], x["new"]) for x in c["changes"][:6])
            print("   CHANGED  %s  [%s]" % (c["title"], flds))
        for a in d["added"][:50]:
            print("   ADDED    %s" % a["title"])
        for r in d["removed"][:50]:
            print("   REMOVED  %s" % r["title"])
    # Warnings MUST reach the caller -- dropping them here made the bulk-field guard dead
    # in production in the Tenant DB script's early history (it only ever fired via
    # --selftest); every sibling since has carried the fix forward from the start.
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
        # SKILL.md invokes this with a literal `{TODAY}` placeholder for the harness to
        # substitute. If that substitution ever fails, an unvalidated --date sails through
        # and the archive is written under a name ARCHIVE_PREFIX can never match, silently
        # losing that day's audit trail. Fail loudly instead (property_register's 2026-08-11
        # review fix, carried forward).
        try:
            datetime.date.fromisoformat(a.date)
        except ValueError:
            print("ERROR: --date %r is not an ISO YYYY-MM-DD date. If this is an unsubstituted "
                  "template placeholder, the caller's date substitution failed." % a.date,
                  file=sys.stderr)
            return 2
        return run(a.date)
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
