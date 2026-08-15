#!/usr/bin/env python3
"""
property_register_snapshot_diff.py  --  ora-pm-ledger Block A helper.

WHY THIS EXISTS
  The Notion Property Register's `last_edited_time` column is UNIFORM at the
  source: live-checked 2026-08-11, all 14 rows share one identical stamp
  (2026-07-12T17:16:00) -- a batch-write signature, not per-row editing. This
  is the same failure mode already documented for CapEx & Maintenance Log and,
  differently, for the Tenant DB (SKILL.md A.1's Reality table and DEFECT 1).
  A timestamp query cannot detect a Property Register edit; `WHERE
  last_edited_time >= today` returns 0 rows whether or not anything changed,
  and reporting that as "no edits" is a confident false negative.

  Property Register was the LAST A.1 source without a detector -- the gap named
  as still-open in the 2026-07-27 amendment note and carried in every EOD
  ledger since. This closes it.

  This script does NOT share code with its two siblings on purpose: all three
  are short, fully self-contained, heavily selftested engines living alone in
  this folder (see `outbox_qc_window.py` for the same convention). A shared
  library would touch two working, reviewed production scripts for a refactor
  nobody asked for.

WHAT IT DOES
  --run [--date YYYY-MM-DD]
     1. Pulls every Property Register row via REST (paginated).
     2. Normalizes each row's properties to plain values (skipping volatile
        metadata: created/last_edited time+by), fingerprints each row (sha256).
     3. Loads the previous snapshot (state/property-register-latest.json).
     4. Emits a diff: added / removed / changed (field-level old->new).
     5. Writes the new snapshot to latest + a dated archive.
     6. Prints a JSON block on the last line prefixed `RESULT_JSON=` for the
        caller (the digest) to parse. First run = baseline, no diff.
  --selftest
     Runs the diff engine against synthetic snapshots, no network. Exit 0 = pass.

DATE-DERIVED FIELDS -- TWO EXIST, confirmed live 2026-08-11
  Unlike CapEx & Maintenance Log (whose set is legitimately empty), this
  database carries two formula fields that recompute from the calendar on
  every read and MUST be excluded or the detector drowns in false positives on
  its first cross-day run -- precisely the defect that made
  `tenant_db_snapshot_diff.py` report 267 of 298 rows changed when only 5 had
  really been edited (SKILL.md's account of 2026-07-24):

    * 'Days to Loan Maturity'
        dateBetween(<Loan Maturity Date>, now(), "days")
        Moves every single day, on every row carrying a maturity date.
    * 'Loan Maturity Flag'
        if(dateBetween(<Loan Maturity Date>, now(), "days") < 365,
           "🔴 < 1 Year", if(dateBetween(...
        Banded version of the same driver. Moves rarely -- but when it does it
        is pure calendar passage with no human edit behind it, which is the
        WORST case: an unexcluded band flip looks exactly like a real edit.

  Excluded BY NAME, never by type. Three other formula fields on this database
  are ratios of STATIC inputs and are legitimate change signals that must keep
  firing:
    * 'Estimated NOI'   = <Total Monthly Rent> * 12
    * 'LTV'             = <Total Outstanding Debt> / <Estimated Current Value>
    * 'Occupancy %'     = <Occupied SF> / <Total SF>
  'LTV' in particular is governor-adjacent (CLAUDE.md invariant 4: LTV <= 40%
  aggregate / 65% per-property). Excluding formulas by TYPE would have silently
  blinded this detector to LTV movement. --selftest asserts LTV still diffs.

ROLLUP FIELDS
  This database carries 14 rollup fields (Total Monthly Rent, Total Outstanding
  Debt, Occupied SF, Tenant Count, ...). They are KEPT: a rollup moving means
  something real changed in a related database, which is genuine signal. Each
  rollup's source property was checked individually at build time (2026-08-11)
  to confirm none pulls from a calendar-derived formula in its source database
  -- notably none reach the Tenant DB's five date-derived fields. If one is ever
  repointed at such a field, the bulk-field guard below will surface it on its
  first cross-day run before it can silently flood the diff.

STORAGE
  state/property-register-latest.json         <- previous/current pointer
  state/property-register-<YYYY-MM-DD>.json   <- dated archive (audit trail)

TOKEN
  NOTION_TOKEN from C:\\Users\\Owner\\oxford-command-center\\.env (read-only).
"""
import argparse, datetime, hashlib, json, os, sys, time, urllib.request, urllib.error

# Harness-spawned/scheduled runs get a cp1252 stdout on Windows; property names and
# the maturity-flag emoji carry non-ASCII characters. Force UTF-8 so prints never crash.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# Single-source database; REST /databases/{id}/query @ 2022-06-28 = 200, verified live 2026-08-11.
PROPERTY_REGISTER_DB_ID = "19a61fc9-21ed-42d7-a0db-aa730d9a9683"
ENV_PATH = r"C:\Users\Owner\oxford-command-center\.env"
STATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state")
LATEST = os.path.join(STATE_DIR, "property-register-latest.json")
ARCHIVE_PREFIX = "property-register-2"
SKIP_TYPES = {"created_time", "last_edited_time", "created_by", "last_edited_by"}

# See the DATE-DERIVED FIELDS note in the module docstring. Both confirmed live
# 2026-08-11 by reading each formula's expression, not inferred from its name.
TIME_DERIVED_FIELDS = {
    "Days to Loan Maturity",   # dateBetween(<Loan Maturity Date>, now(), "days")
    "Loan Maturity Flag",      # if(dateBetween(<Loan Maturity Date>, now(), "days") < 365, ...)
}

# A field changing on more than this share of all rows is almost certainly bulk/derived
# rather than edited, and is reported as a warning instead of silently inflating the diff.
BULK_FIELD_RATIO = 0.5


# ---------- property normalization ----------
def _people(v):
    return "|".join(sorted(p.get("id", "") for p in v or []))

def _array_digest(arr, _depth=0):
    """Order-sensitive content digest of a rollup array's elements (OI-151).

    Elements of a rollup array are themselves Notion property-value objects, so
    each is normalized through norm_prop -- the same stripping that protects a
    top-level property from volatile metadata (SKIP_TYPES) applies here too, which
    is what keeps this from churning every run. Anything not property-shaped (the
    selftest uses bare ints) falls back to a sorted-key JSON dump.

    Depth-guarded because a rollup array can in principle carry another rollup;
    unbounded recursion here would be a crash in an unattended 18:00 run, which is
    strictly worse than the blind spot this closes. Beyond the limit we degrade to
    the JSON dump rather than giving up.

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
            # A skipped (None) element still has to occupy a slot, or dropping a
            # metadata element would read as identical to it never existing.
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
            # OI-151: this used to fingerprint by LENGTH ALONE, so swapping one
            # element for another kept the token identical and the change was a
            # SILENT false negative -- precisely the failure class this script
            # exists to prevent (see the module docstring). Latent while every
            # row's relations are empty; live the moment they are populated.
            # The empty case deliberately keeps the exact legacy token so this
            # change causes ZERO diff churn against snapshots written before it
            # -- today all 14 rows are empty, so the first run after this lands
            # reports no spurious edits.
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

    Applied on BOTH sides of the diff so a snapshot written before a field was
    added to TIME_DERIVED_FIELDS still compares cleanly against one written
    after -- without this, the first run after such a change would report every
    row as changed (the stored pre-change hash covers fields the new
    fingerprint no longer includes). See tenant_db_snapshot_diff.py's own
    2026-07-24 fix for the incident this pattern exists to prevent.
    """
    return {k: v for k, v in (row.get("fields") or {}).items() if k not in TIME_DERIVED_FIELDS}


def fingerprint(fields):
    blob = json.dumps(fields, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def detect_truncation(pages):
    """Warnings for any property value Notion truncated in the query response.

    Notion caps multi-reference property values (relation, people, and rollup arrays) at 25
    items in database-query results and sets `has_more` ON THE PROPERTY OBJECT. Nothing else
    in this file reads that flag, and the consequences are silent in both directions:
      * a property with >25 relations always fingerprints the same first-25 id set, so
        adding a 26th tenant is UNDETECTABLE; and
      * if Notion's ordering of that relation is not stable between reads, the first-25
        SUBSET changes on its own and produces a daily false "changed" -- sorting the ids
        (which norm_prop does) makes the value stable but cannot recover the missing ones.

    Latent on this database today: every relation and rollup is empty on all 14 rows, checked
    live 2026-08-11. It arms as soon as the Tenants/Loans relations are populated -- ORA runs
    ~140 tenants across ~14 properties, so at least one >25-relation property is plausible.
    Raised by the 2026-08-11 independent review. Detection only: fixing it properly needs a
    per-page property-item fetch, which is not worth the request budget until it actually bites.
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
    # Denominate by rows present in BOTH snapshots, not by all current rows. `changed` can
    # only ever be drawn from the intersection, so using len(c) systematically dilutes the
    # ratio and lets a partially-populated derived field slip under the threshold forever.
    # Concretely (independent review, 2026-08-11): if only 5 of 14 properties carry a loan,
    # a rollup repointed at a calendar-derived source drifts on just those 5 -> 5/14 = 36%
    # -> no warning, and 5 rows report a false "changed" every day indefinitely. The guard
    # is documented as the backstop for keeping this database's 14 rollups, so it has to be
    # sensitive exactly where a rollup would actually drift.
    total = len(set(p) & set(c))
    if total:
        freq = {}
        for row in changed:
            for ch in row["changes"]:
                freq[ch["field"]] = freq.get(ch["field"], 0) + 1
        for field, n in sorted(freq.items(), key=lambda kv: -kv[1]):
            # >= not >: a derived field moving on EXACTLY half the rows is the same signal,
            # and on a 14-row table that boundary (7 of 14) is easy to land on.
            if n / total >= BULK_FIELD_RATIO:
                warnings.append(
                    "field %r changed on %d/%d compared rows (%.0f%%) — derived, bulk-written, "
                    "or a SCHEMA CHANGE (a rename/add makes every row report <absent> -> value). "
                    "Diagnose which before excluding anything, and NEVER exclude 'LTV', "
                    "'Occupancy %%' or 'Estimated NOI' — they are static-input formulas and "
                    "'LTV' is governor-critical."
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
    """One POST to Notion's query endpoint, with bounded retry. Split out from pull_all so
    the pagination loop can be exercised offline by --selftest via the `fetch` seam."""
    req = urllib.request.Request(
            "https://api.notion.com/v1/databases/%s/query" % db_id,
            data=json.dumps(body).encode(),
            headers={"Authorization": "Bearer " + token,
                     "Notion-Version": "2022-06-28",
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
            # OI-152: this was `except urllib.error.URLError`, which covers a
            # failure to CONNECT but not a timeout reading the RESPONSE BODY --
            # `json.load(r)` runs inside this try, and a socket read timeout
            # there raises TimeoutError, which is neither HTTPError nor
            # URLError. So the exact "one Notion hiccup = a lost run" case the
            # comment above promises to absorb still died on first occurrence
            # if the hiccup landed mid-body. OSError is the common base of
            # URLError, TimeoutError and the socket errors (ConnectionReset,
            # etc.), so this widens to the whole transient-network family
            # without reaching non-network failures: a malformed body raises
            # JSONDecodeError (a ValueError) and is still not retried, because
            # it is not transient. HTTPError is matched by the clause above
            # first, so its status-code logic is unchanged.
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
    prev = {"as_of": "2026-08-09", "count": 3, "rows": {
        "A": {"title": "1100 Rarig Ave",
              "hash": fingerprint({"Market": "Columbus", "Zoning": "M-2"}),
              "fields": {"Market": "Columbus", "Zoning": "M-2"}},
        "B": {"title": "9050 Red Branch Rd",
              "hash": fingerprint({"Market": "Baltimore"}),
              "fields": {"Market": "Baltimore"}},
        "C": {"title": "Disposed test parcel",
              "hash": fingerprint({"Market": "Columbus"}),
              "fields": {"Market": "Columbus"}},
    }}
    curr = {"as_of": "2026-08-11", "count": 3, "rows": {
        "A": {"title": "1100 Rarig Ave",
              "hash": fingerprint({"Market": "Columbus", "Zoning": "M-1"}),
              "fields": {"Market": "Columbus", "Zoning": "M-1"}},   # changed Zoning
        "B": {"title": "9050 Red Branch Rd",
              "hash": fingerprint({"Market": "Baltimore"}),
              "fields": {"Market": "Baltimore"}},                   # unchanged
        "D": {"title": "New acquisition — 754 Old State Rte 74",
              "hash": fingerprint({"Market": "Cincinnati"}),
              "fields": {"Market": "Cincinnati"}},                  # added
        # C removed
    }}
    d = diff_snapshots(prev, curr)
    check([x["id"] for x in d["added"]] == ["D"], "added == [D]")
    check([x["id"] for x in d["removed"]] == ["C"], "removed == [C]")
    check(len(d["changed"]) == 1 and d["changed"][0]["id"] == "A", "changed == [A]")
    ch = d["changed"][0]["changes"] if d["changed"] else []
    check(len(ch) == 1 and ch[0]["field"] == "Zoning" and ch[0]["old"] == "M-2" and ch[0]["new"] == "M-1",
          "A.Zoning 'M-2' -> 'M-1'")
    check(d["unchanged"] == 1, "unchanged == 1 (B)")
    d0 = diff_snapshots(None, curr)
    check(len(d0["added"]) == 3 and not d0["removed"] and not d0["changed"], "baseline: all added, no diff")

    # ---- TIME_DERIVED_FIELDS: the REAL production set ----
    # Unlike the CapEx sibling (which has no calendar-derived formula and can only prove the
    # mechanism against a synthetic field name), this database has two real ones. These
    # assertions exercise the actual production constant, so they fail loudly if a future
    # edit empties or renames it.
    check("Days to Loan Maturity" in TIME_DERIVED_FIELDS,
          "production set excludes 'Days to Loan Maturity'")
    check("Loan Maturity Flag" in TIME_DERIVED_FIELDS,
          "production set excludes 'Loan Maturity Flag'")
    check("LTV" not in TIME_DERIVED_FIELDS,
          "production set does NOT exclude 'LTV' (static-input formula, governor-adjacent)")
    check("Occupancy %" not in TIME_DERIVED_FIELDS and "Estimated NOI" not in TIME_DERIVED_FIELDS,
          "production set does NOT exclude the other static-input formulas")

    def mkprop(title, days, flag, ltv, market="Columbus"):
        f = {"Market": market, "Days to Loan Maturity": days,
             "Loan Maturity Flag": flag, "LTV": ltv}
        f = {k: v for k, v in f.items() if k not in TIME_DERIVED_FIELDS}
        return {"title": title, "hash": fingerprint(f), "fields": f}

    # Cross-day: ONLY the calendar-derived fields moved. Must report zero changes.
    day1 = {"as_of": "2026-08-09", "count": 2, "rows": {
        "X": mkprop("3540 E. Fifth Ave", "400", "🟡 1-2 Years", "0.31"),
        "Y": mkprop("29000 Information Lane", "370", "🟡 1-2 Years", "0.28"),
    }}
    day2 = {"as_of": "2026-08-11", "count": 2, "rows": {
        "X": mkprop("3540 E. Fifth Ave", "398", "🟡 1-2 Years", "0.31"),   # counter ticked
        "Y": mkprop("29000 Information Lane", "364", "🔴 < 1 Year", "0.28"),  # BAND FLIPPED
    }}
    dcd = diff_snapshots(day1, day2)
    check(not dcd["changed"],
          "cross-day: date-derived movement (incl. a maturity-flag BAND FLIP) reports 0 changed")
    check(dcd["unchanged"] == 2, "cross-day: unchanged == 2")
    check(not dcd["warnings"], "cross-day: no spurious bulk-field warning")

    # Same cross-day pull, but LTV genuinely moved on one row. LTV is a static-input formula
    # and governor-adjacent -- it MUST still be detected. This is the assertion that proves
    # the exclusion is by NAME and not by TYPE.
    day2b = json.loads(json.dumps(day2))
    day2b["rows"]["Y"]["fields"]["LTV"] = "0.42"
    dreal = diff_snapshots(day1, day2b)
    check(len(dreal["changed"]) == 1 and dreal["changed"][0]["id"] == "Y",
          "cross-day: a real LTV move is still detected (Y only)")
    check([c["field"] for c in dreal["changed"][0]["changes"]] == ["LTV"],
          "cross-day: only LTV reported, not the two calendar fields alongside it")

    # Migration: a snapshot written BEFORE these fields were excluded (it still carries them
    # in `fields`) vs one written after must NOT report every row as changed.
    prefield_rows = {}
    for k, t in (("X", "3540 E. Fifth Ave"), ("Y", "29000 Information Lane")):
        f = dict(day1["rows"][k]["fields"])
        f["Days to Loan Maturity"] = "400"      # as an OLD snapshot would have stored it
        f["Loan Maturity Flag"] = "🟡 1-2 Years"
        prefield_rows[k] = {"title": t, "hash": fingerprint(f), "fields": f}
    dmig = diff_snapshots({"as_of": "2026-08-09", "count": 2, "rows": prefield_rows}, day2)
    check(not dmig["changed"], "migration: pre-exclusion vs post-exclusion snapshot reports 0 changed")

    # ---- bulk-field guard ----
    bulk_prev = {"as_of": "2026-08-09", "count": 4, "rows": {
        k: {"title": k, "hash": fingerprint({"PM Platform": "Rent Manager"}),
            "fields": {"PM Platform": "Rent Manager"}} for k in "PQRS"}}
    bulk_curr = json.loads(json.dumps(bulk_prev))
    bulk_curr["as_of"] = "2026-08-11"
    for k in ("P", "Q", "R"):                  # 3 of 4 = 75%
        bulk_curr["rows"][k]["fields"]["PM Platform"] = "AppFolio"
    dbulk = diff_snapshots(bulk_prev, bulk_curr)
    check(any("'PM Platform'" in w for w in dbulk["warnings"]),
          "bulk guard: warns when a non-excluded field moves on >50% of rows")

    half_curr = json.loads(json.dumps(bulk_prev))
    half_curr["as_of"] = "2026-08-11"
    for k in ("P", "Q"):                       # exactly 2 of 4 = 50%
        half_curr["rows"][k]["fields"]["PM Platform"] = "AppFolio"
    dhalf = diff_snapshots(bulk_prev, half_curr)
    check(len(dhalf["changed"]) == 2, "50pct boundary: 2 of 4 rows changed")
    check(any("'PM Platform'" in w for w in dhalf["warnings"]),
          "bulk guard fires at exactly 50pct (>= threshold)")

    # ---- rollup + unique_id normalization (this DB is rollup-heavy: 14 of them) ----
    check(norm_prop({"type": "rollup", "rollup": {"type": "number", "number": 12345.0}}) == repr(12345.0),
          "norm_prop: numeric rollup normalizes stably")
    # OI-151 regression battery. The old behaviour was a bare length token, which
    # made an equal-length element swap invisible -- a silent false negative.
    _arr = lambda a: norm_prop({"type": "rollup", "rollup": {"type": "array", "array": a}})
    check(_arr([]) == "[array:0]",
          "norm_prop: EMPTY array rollup keeps the exact legacy token (no diff churn on landing)")
    check(_arr([1, 2, 3]).startswith("[array:3:"),
          "norm_prop: non-empty array rollup still carries its length, plus a content digest")
    check(_arr([1, 2, 3]) == _arr([1, 2, 3]),
          "norm_prop: identical array content digests identically (no spurious daily churn)")
    check(_arr([1, 2, 3]) != _arr([1, 2, 4]),
          "norm_prop: OI-151 -- an EQUAL-LENGTH element swap now changes the token")
    check(_arr([1, 2, 3]) != _arr([3, 2, 1]),
          "norm_prop: array digest is order-sensitive (a reorder is a real change)")
    check(_arr([{"type": "rich_text", "rich_text": [{"plain_text": "Ada"}]}])
          != _arr([{"type": "rich_text", "rich_text": [{"plain_text": "Grace"}]}]),
          "norm_prop: property-shaped elements normalize through norm_prop and differ by content")
    check(_arr([{"type": "rich_text", "rich_text": [{"plain_text": "Ada"}]}])
          == _arr([{"type": "rich_text", "rich_text": [{"plain_text": "Ada"}]}]),
          "norm_prop: property-shaped elements with identical content digest identically")
    # A rollup nested inside a rollup array must not recurse without bound: the
    # depth guard has to degrade to a JSON dump rather than raise in an unattended run.
    _nested = {"type": "rollup", "rollup": {"type": "array", "array": [
        {"type": "rollup", "rollup": {"type": "array", "array": [
            {"type": "rollup", "rollup": {"type": "array", "array": [
                {"type": "rollup", "rollup": {"type": "array", "array": [1]}}]}}]}}]}}
    check(isinstance(norm_prop(_nested), str) and norm_prop(_nested).startswith("[array:1:"),
          "norm_prop: deeply nested rollup arrays are depth-guarded, not a RecursionError")
    check(norm_prop({"type": "unique_id", "unique_id": {"prefix": "PROP", "number": 7}}) == "PROP7",
          "norm_prop: unique_id (Property ID) normalizes")
    check(norm_prop({"type": "last_edited_time", "last_edited_time": "2026-07-12T17:16:00Z"}) is None,
          "norm_prop: the frozen 'Last Updated' column is skipped as metadata")

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

    # ---- load_prev() corruption fallback ----
    global STATE_DIR, LATEST
    real_dir, real_latest = STATE_DIR, LATEST
    tmpdir = os.path.join(real_dir, "_selftest_tmp_propreg")
    try:
        os.makedirs(tmpdir, exist_ok=True)
        STATE_DIR, LATEST = tmpdir, os.path.join(tmpdir, "property-register-latest.json")
        good = {"as_of": "2026-08-09", "db_id": "x", "count": 1,
                "rows": {"A": {"title": "1100 Rarig Ave", "hash": "h", "fields": {"Market": "Columbus"}}}}
        with open(os.path.join(tmpdir, "property-register-2026-08-09.json"), "w", encoding="utf-8") as f:
            json.dump(good, f)
        with open(LATEST, "w", encoding="utf-8") as f:
            f.write("{ truncated")
        prevx, warn = load_prev()
        check(prevx is not None and prevx.get("count") == 1,
              "corrupt LATEST falls back to newest dated archive")
        check(warn and "archive" in warn, "archive fallback is reported, not silent")

        os.remove(os.path.join(tmpdir, "property-register-2026-08-09.json"))
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
    with_prior = {"count": 14}

    # These assert the DISTINGUISHING message, not merely `not persisted`. The 2026-08-11
    # review showed the earlier versions were vacuous: because the branch below now refuses
    # every 0-row pull unconditionally, deleting the load_warning branch entirely left all
    # three still passing. Keying on the branch's own wording makes them load-bearing again.
    p, w = decide_persist(None, 0, "previous snapshot unreadable (fake)")
    check(not p, "decide_persist: refuses when curr=0 and load_warning is set (prev=None)")
    check(w and "Two independent failure signals" in w,
          "decide_persist: 0-row+degraded-load takes its OWN branch (not the generic refusal)")
    check(w and "REFUSED" in w, "decide_persist: refusal is a loud warning, not silent")
    p2, w2 = decide_persist(with_prior, 0, "previous snapshot unreadable (fake)")
    check(not p2, "decide_persist: refuses when curr=0 and load_warning is set (prev_count>0)")
    check(w2 and "Two independent failure signals" in w2,
          "decide_persist: same distinguishing branch when a prior baseline exists")

    # DIVERGENCE FROM THE CapEx SIBLING, deliberate: CapEx was legitimately empty before
    # 2026-07-26, so a clean first-run 0-row persist is allowed there. A Property Register
    # holding zero rows would mean the firm owns no properties -- that is never a true state,
    # so a 0-row pull here is ALWAYS an access failure and must never establish a baseline.
    p3, w3 = decide_persist(None, 0, None)
    check(not p3, "decide_persist: refuses a 0-row FIRST run (an empty property register is never real)")
    check(w3 and "REFUSED" in w3 and "never" in w3.lower(),
          "decide_persist: the 0-row first-run refusal explains why")

    p4, w4 = decide_persist(with_prior, 0, None)
    check(not p4, "decide_persist: refuses 0 rows against a prior non-empty baseline")
    check(w4 and "REFUSED" in w4 and "0 rows" in w4, "decide_persist: refusal names the cause")

    # Exact 50% collapse (7 of 14) must refuse -- matching the bulk-field guard's >= boundary.
    p5, w5 = decide_persist(with_prior, 7, None)
    check(not p5, "decide_persist: refuses at the exact 50pct collapse boundary (7 of 14)")
    p6, w6 = decide_persist(with_prior, 8, None)
    check(p6 and w6 is None, "decide_persist: 8 of 14 (just above the boundary) persists cleanly")
    p7, w7 = decide_persist(with_prior, 14, None)
    check(p7 and w7 is None, "decide_persist: a normal same-count pull persists silently (no warning)")

    # ---- 2026-08-11 independent-review regressions ----

    # (a) Bulk-field guard denominates by COMPARED rows, not all current rows. A derived
    # field drifting on a populated subset must still trip it. 5 of 14 rows share the field;
    # under the old len(c) denominator this was 5/14 = 36% and warned silently forever.
    sub_prev = {"as_of": "2026-08-11", "count": 5, "rows": {
        "L%d" % i: {"title": "L%d" % i, "hash": "h", "fields": {"Days to Loan Maturity X": "400"}}
        for i in range(5)}}
    sub_curr = {"as_of": "2026-08-12", "count": 14, "rows": {}}
    for i in range(5):                       # the 5 loan-carrying rows drift
        sub_curr["rows"]["L%d" % i] = {"title": "L%d" % i, "hash": "h",
                                       "fields": {"Days to Loan Maturity X": "399"}}
    for i in range(9):                       # 9 rows that were never in prev
        sub_curr["rows"]["N%d" % i] = {"title": "N%d" % i, "hash": "h", "fields": {}}
    dsub = diff_snapshots(sub_prev, sub_curr)
    check(len(dsub["changed"]) == 5, "subset drift: 5 rows changed")
    check(any("Days to Loan Maturity X" in w for w in dsub["warnings"]),
          "bulk guard denominates by COMPARED rows (5/5), not all current rows (5/14)")
    check(any("compared rows" in w for w in dsub["warnings"]),
          "bulk-guard warning says 'compared rows' so the denominator is unambiguous")
    check(all("NEVER exclude 'LTV'" in w for w in dsub["warnings"]),
          "bulk-guard remedy warns against excluding the governor-critical fields")

    # (b) Notion's 25-item truncation on relation/people/rollup arrays is DETECTED.
    trunc_pages = [{"id": "p1", "properties": {
        "Property Name": {"type": "title", "title": [{"plain_text": "1100 Rarig Ave"}]},
        "Tenants": {"type": "relation", "relation": [{"id": "t%d" % i} for i in range(25)],
                    "has_more": True},
        "Zoning": {"type": "rich_text", "rich_text": [{"plain_text": "M-2"}]},
    }}]
    tw = detect_truncation(trunc_pages)
    check(len(tw) == 1 and "Tenants" in tw[0] and "1100 Rarig Ave" in tw[0],
          "detect_truncation: flags a has_more relation, naming row and field")
    check(not detect_truncation([{"id": "p1", "properties": {
        "Tenants": {"type": "relation", "relation": [{"id": "t1"}]}}}]),
          "detect_truncation: silent when nothing is truncated")
    check(detect_truncation([{"id": "p2", "properties": {
        "Occupied SF": {"type": "rollup", "rollup": {"type": "array", "array": [],
                                                     "has_more": True}}}}]),
          "detect_truncation: also reads has_more nested on a rollup")

    # (c) --date validation rejects an unsubstituted template placeholder.
    def date_ok(s):
        try:
            datetime.date.fromisoformat(s); return True
        except ValueError:
            return False
    check(not date_ok("{TODAY}") and date_ok("2026-08-11"),
          "--date validation rejects '{TODAY}' and accepts a real ISO date")

    # (d) END-TO-END run(): a REFUSED run must not claim a baseline. This is the review's
    # most severe finding -- the defect lived in run()'s reporting, which no pure-helper test
    # could reach, so it is driven through the _pages seam against a scratch state dir.
    real_dir2, real_latest2 = STATE_DIR, LATEST
    tmp2 = os.path.join(real_dir2, "_selftest_tmp_run")
    import io, contextlib
    try:
        os.makedirs(tmp2, exist_ok=True)
        STATE_DIR, LATEST = tmp2, os.path.join(tmp2, "property-register-latest.json")

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            run("2026-08-12", _pages=[])          # 0-row pull, no prior baseline
        out = buf.getvalue()
        res = json.loads(out.rsplit("RESULT_JSON=", 1)[1].strip())
        check(res["persisted"] is False, "e2e refusal: persisted is False")
        check(res["baseline"] is False,
              "e2e refusal: baseline is False (a refused run establishes NOTHING)")
        check("Baseline established" not in out,
              "e2e refusal: does NOT print 'Baseline established'")
        check("REFUSED" in out, "e2e refusal: says REFUSED in the human summary")
        check(not os.path.exists(LATEST), "e2e refusal: no state file written")

        # A genuine first run DOES baseline, through the same path.
        good_pages = [{"id": "pA", "properties": {
            "Property Name": {"type": "title", "title": [{"plain_text": "1100 Rarig Ave"}]},
            "Zoning": {"type": "rich_text", "rich_text": [{"plain_text": "M-2"}]}}}]
        buf2 = io.StringIO()
        with contextlib.redirect_stdout(buf2):
            run("2026-08-12", _pages=good_pages)
        res2 = json.loads(buf2.getvalue().rsplit("RESULT_JSON=", 1)[1].strip())
        check(res2["persisted"] and res2["baseline"] and res2["count"] == 1,
              "e2e baseline: a real first run persists and reports baseline true")

        # (e) A MISSING latest falls back to the archive instead of silently re-baselining.
        os.remove(LATEST)
        check(os.path.exists(os.path.join(tmp2, "property-register-2026-08-12.json")),
              "e2e: dated archive survives independently of latest")
        prev3, warn3 = load_prev()
        check(prev3 is not None and prev3["count"] == 1,
              "missing LATEST falls back to the newest dated archive")
        check(warn3 and "MISSING" in warn3,
              "missing LATEST is reported loudly, not treated as 'no baseline'")
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
# results) than several properties genuinely vanishing between two runs. Persisting that
# would destroy the baseline and make the NEXT run report every remaining row as spuriously
# "added". ORA holds ~14 properties and disposes of them one at a time over years, so a
# halving between two daily runs is not a plausible real-world event.
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

    A corrupt/unreadable LATEST degrades gracefully rather than raising and killing every
    future 18:00 run. It falls back to the newest dated archive BEFORE giving up: without
    that, corruption masquerades as 'no baseline', which disables the collapse guard below
    and lets a simultaneously-collapsed pull overwrite the baseline with an empty snapshot.
    """
    if not os.path.exists(LATEST):
        # A MISSING latest is handled exactly like a corrupt one. Before the 2026-08-11
        # independent review this branch returned (None, None) immediately, so deletion --
        # from a state-dir cleanup, a hand repair, or a move -- was strictly more dangerous
        # than truncation: no archive fallback AND no load_warning, which disabled both the
        # degraded-signal refusal and the collapse guard (prev_count == 0). A 6-of-14
        # partial-access pull then persisted silently with zero warnings, and the NEXT run
        # reported 8 spurious properties as newly ADDED.
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
    production risk -- is directly exercised by --selftest instead of only being reachable
    through a live or mocked run(). Carried forward from capex_snapshot_diff.py, whose own
    version of this function was rewritten after an independent review found two defects in
    the inline logic it replaced.

    ONE DELIBERATE DIVERGENCE from that sibling: the 0-row-with-no-prior-baseline case
    REFUSES here instead of persisting with a warning. CapEx & Maintenance Log was genuinely
    empty before 2026-07-26, so a clean 0-row first run was a real state there. A Property
    Register holding zero rows would mean Oxford owns no properties -- never true, and never
    going to be. A 0-row pull against this database is always an access failure (revoked or
    narrowed integration scope, unshared database; Notion answers 200 with an empty result
    set in all of those cases), so it must never be allowed to establish a baseline.

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
            "baseline. An empty Property Register is never a real state — Oxford always "
            "owns properties — so this is an access failure (revoked/narrowed integration "
            "scope, or the database is no longer shared with it), not an empty table. "
            "Fix access, then re-run to establish the baseline.")

    if prev_count > 0 and curr_count <= prev_count * COLLAPSE_FLOOR_RATIO:
        return False, (
            "REFUSED to persist snapshot: row count collapsed %d -> %d (at or below %.0f%% "
            "of prior). Prior baseline kept. Check the Notion integration's database access "
            "before trusting this run's diff."
            % (prev_count, curr_count, COLLAPSE_FLOOR_RATIO * 100))

    return True, None


def run(as_of, _pages=None):
    """`_pages` injects an already-fetched page list, bypassing token load + HTTP.

    Exists so --selftest can drive this function end-to-end offline. The persist/refusal
    reporting path is the one part of this file that an independent review found broken
    (a refused run still printed "Baseline established" and set baseline:true), and that
    defect lived HERE, in run()'s reporting -- not in any of the pure helpers the selftest
    already covered. A seam is the only way to regression-test it without a network call.
    """
    os.makedirs(STATE_DIR, exist_ok=True)
    if _pages is None:
        token = load_token()
        pages = pull_all(PROPERTY_REGISTER_DB_ID, token)
    else:
        pages = _pages
    curr = build_snapshot(pages, as_of, PROPERTY_REGISTER_DB_ID)
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
        atomic_write_json(os.path.join(STATE_DIR, "property-register-%s.json" % as_of), curr)

    # A refused run establishes NOTHING. `baseline` must therefore depend on `persisted`, not
    # on `prev is None` alone: before the 2026-08-11 independent review it did not, so an
    # access failure (0 rows, correctly refused) still printed "Baseline established" and set
    # `baseline: true` in RESULT_JSON. The digest parsing that JSON would read an outage as a
    # clean no-edits day -- precisely the inferred-null-presented-as-verified-null failure the
    # whole snapshot-diff approach exists to prevent.
    baseline = prev is None and persisted

    # human summary
    if not persisted:
        print("REFUSED: no snapshot persisted for %s (%d rows pulled). Prior state kept, "
              "NO baseline established. See WARNING below." % (as_of, curr["count"]))
    elif baseline:
        print("Baseline established: %d rows snapshotted for %s (no prior snapshot to diff)." % (curr["count"], as_of))
    else:
        print("Property Register diff %s -> %s: %d added, %d removed, %d changed, %d unchanged (of %d)." % (
            d["prev_as_of"], as_of, len(d["added"]), len(d["removed"]), len(d["changed"]),
            d["unchanged"], curr["count"]))
        for c in d["changed"][:50]:
            flds = ", ".join("%s: %s -> %s" % (x["field"], x["old"], x["new"]) for x in c["changes"][:6])
            print("   CHANGED  %s  [%s]" % (c["title"], flds))
        for a in d["added"][:50]:
            print("   ADDED    %s" % a["title"])
        for r in d["removed"][:50]:
            print("   REMOVED  %s" % r["title"])
    # Warnings MUST reach the caller. They were previously computed and dropped here in the
    # Tenant DB script's early history, which made the bulk-field guard dead in production
    # (it only ever fired via --selftest) -- carried the fix forward from the start here.
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
        # substitute. If that substitution ever fails, an unvalidated --date sails through:
        # the run succeeds, as_of becomes the literal "{TODAY}", and the archive is written
        # under a name ARCHIVE_PREFIX can never match -- so load_prev()'s corruption fallback
        # silently loses that day's audit trail. Fail loudly instead. (2026-08-11 review.)
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
