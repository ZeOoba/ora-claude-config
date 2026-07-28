#!/usr/bin/env python3
"""
capex_snapshot_diff.py  --  ora-pm-ledger Block A helper.

WHY THIS EXISTS
  The Notion CapEx & Maintenance Log's `last_edited_time` column is UNIFORM at
  the source: live-checked 2026-07-27, all 6 rows share one identical stamp
  (2026-07-26T19:20:00Z, == created_time on every row) -- a batch-import
  signature, not per-row editing. This is the same failure mode already
  documented for Property Register and, differently, for the Tenant DB (see
  SKILL.md A.1's Reality table and DEFECT 1). A timestamp query cannot detect
  a CapEx edit any more than it can for those two. The ONLY mechanism that can
  is a full snapshot hashed and diffed against the prior run -- the same
  approach `tenant_db_snapshot_diff.py` uses for the Tenant DB, generalized
  here. This script does NOT share code with that one on purpose: both are
  short, fully self-contained, heavily selftested engines living alone in
  this folder (see `outbox_qc_window.py` for the same convention) -- a shared
  library would touch a working, reviewed production script for a refactor
  nobody asked for.

WHAT IT DOES
  --run [--date YYYY-MM-DD]
     1. Pulls every CapEx & Maintenance Log row via REST (paginated).
     2. Normalizes each row's properties to plain values (skipping volatile
        metadata: created/last_edited time+by), fingerprints each row (sha256).
     3. Loads the previous snapshot (state/capex-latest.json) if present.
     4. Emits a diff: added / removed / changed (field-level old->new).
     5. Writes the new snapshot to latest + a dated archive.
     6. Prints a JSON block on the last line prefixed `RESULT_JSON=` for the
        caller (the digest) to parse. First run = baseline, no diff.
  --selftest
     Runs the diff engine against synthetic snapshots, no network. Exit 0 = pass.

DATE-DERIVED FIELDS -- none exist today, checked live 2026-07-27
  The Tenant DB carries five formula fields that recompute from the calendar
  (Days to Expiration, etc.) and had to be excluded by name or the detector
  drowned in false positives on its first cross-day run (SKILL.md's account of
  2026-07-24). CapEx & Maintenance Log's schema was fetched live for this
  build: its two formula fields, `Annualized Reserve` (Expected Annual NOI
  Impact / Asset Life (Years)) and `Yield on Cost` (Expected Annual NOI Impact
  / Invoice Amount), are both formulas over STATIC numeric inputs -- they only
  move when a human edits one of those inputs, which is a real change signal,
  not calendar drift. CAPEX_TIME_DERIVED_FIELDS is therefore empty. It stays a
  named, mutable set (not a hardcoded absence) so a future date-derived
  formula can be added the same way the Tenant DB's were -- and the bulk-field
  guard below will surface one on its first cross-day run before it can
  silently flood the diff, exactly as it already once did for the Tenant DB.

STORAGE
  state/capex-latest.json         <- previous/current pointer
  state/capex-<YYYY-MM-DD>.json   <- dated archive (audit trail)

TOKEN
  NOTION_TOKEN from C:\\Users\\Owner\\oxford-command-center\\.env (read-only).
"""
import argparse, datetime, hashlib, json, os, sys, time, urllib.request, urllib.error

# Harness-spawned/scheduled runs get a cp1252 stdout on Windows; row titles and
# vendor names can carry non-ASCII characters. Force UTF-8 so prints never crash.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

CAPEX_DB_ID = "5dfcc3ad-532e-4e5f-bf8d-512e2b69e317"   # single-source; REST /databases/{id}/query @ 2022-06-28 = 200, verified live 2026-07-27
ENV_PATH = r"C:\Users\Owner\oxford-command-center\.env"
STATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state")
LATEST = os.path.join(STATE_DIR, "capex-latest.json")
SKIP_TYPES = {"created_time", "last_edited_time", "created_by", "last_edited_by"}

# See the DATE-DERIVED FIELDS note in the module docstring: empty today, checked
# live 2026-07-27. Kept as a named set (not omitted) so the exclusion mechanism
# is a one-line addition, not a rewrite, if Notion ever adds a calendar-derived
# formula to this database.
TIME_DERIVED_FIELDS = set()

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

    Applied on BOTH sides of the diff so a snapshot written before a field was
    added to TIME_DERIVED_FIELDS still compares cleanly against one written
    after -- without this, the first run after such a change would report
    every row as changed (the stored pre-change hash covers fields the new
    fingerprint no longer includes). See tenant_db_snapshot_diff.py's own
    2026-07-24 fix for the incident this pattern exists to prevent.
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
    # edited. Surface it loudly instead of letting it inflate the diff unnoticed -- exactly
    # how the Tenant DB's date-derived-formula defect went undetected until 2026-07-24.
    warnings = []
    total = len(c)
    if total:
        freq = {}
        for row in changed:
            for ch in row["changes"]:
                freq[ch["field"]] = freq.get(ch["field"], 0) + 1
        for field, n in sorted(freq.items(), key=lambda kv: -kv[1]):
            # >= not >: a derived field moving on EXACTLY half the rows is the same signal,
            # and on a 6-row table that boundary (3 of 6) is trivial to land on.
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
        except urllib.error.URLError:
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
    prev = {"as_of": "2026-07-25", "count": 3, "rows": {
        "A": {"title": "HVAC replacement — 55 New Plant Ct",
              "hash": fingerprint({"Vendor": "CoolAir Inc", "Status": "In Progress"}),
              "fields": {"Vendor": "CoolAir Inc", "Status": "In Progress"}},
        "B": {"title": "Roof patch — 1100 Rarig",
              "hash": fingerprint({"Vendor": "TopSeal LLC"}),
              "fields": {"Vendor": "TopSeal LLC"}},
        "C": {"title": "Cancelled parking-lot resurface",
              "hash": fingerprint({"Vendor": "AsphaltCo"}),
              "fields": {"Vendor": "AsphaltCo"}},
    }}
    curr = {"as_of": "2026-07-27", "count": 3, "rows": {
        "A": {"title": "HVAC replacement — 55 New Plant Ct",
              "hash": fingerprint({"Vendor": "CoolAir Inc", "Status": "Complete"}),
              "fields": {"Vendor": "CoolAir Inc", "Status": "Complete"}},   # changed Status
        "B": {"title": "Roof patch — 1100 Rarig",
              "hash": fingerprint({"Vendor": "TopSeal LLC"}),
              "fields": {"Vendor": "TopSeal LLC"}},                        # unchanged
        "D": {"title": "New billboard lease review — 401 Sunburst",
              "hash": fingerprint({"Vendor": "SignCo"}),
              "fields": {"Vendor": "SignCo"}},                             # added
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
    check(len(ch) == 1 and ch[0]["field"] == "Status" and ch[0]["old"] == "In Progress" and ch[0]["new"] == "Complete",
          "A.Status 'In Progress' -> 'Complete'")
    check(d["unchanged"] == 1, "unchanged == 1 (B)")
    # first-run baseline: prev None -> everything is 'added', no crash
    d0 = diff_snapshots(None, curr)
    check(len(d0["added"]) == 3 and not d0["removed"] and not d0["changed"], "baseline: all added, no diff")

    # --- TIME_DERIVED_FIELDS MECHANISM (production set is empty today — see module
    # docstring; this proves the exclusion mechanism itself, not any concrete field name,
    # since CapEx has no calendar-derived formula yet to exercise it against for real) ---
    global TIME_DERIVED_FIELDS
    real_tdf = TIME_DERIVED_FIELDS
    try:
        TIME_DERIVED_FIELDS = {"Days Since Logged"}   # synthetic, proves the mechanism only

        def mkrow(title, vendor, days_since):
            f = {"Vendor": vendor, "Days Since Logged": days_since}
            return {"title": title, "hash": fingerprint(f), "fields": f}

        day1 = {"as_of": "2026-07-22", "count": 2, "rows": {
            "X": mkrow("Item X", "Acme", "3"),
            "Y": mkrow("Item Y", "Beta", "3"),
        }}
        day3 = {"as_of": "2026-07-24", "count": 2, "rows": {
            "X": mkrow("Item X", "Acme", "5"),          # only the derived field moved
            "Y": mkrow("Item Y", "Beta", "5"),
        }}
        dcd = diff_snapshots(day1, day3)
        check(not dcd["changed"], "cross-day: date-derived-only movement reports 0 changed")
        check(dcd["unchanged"] == 2, "cross-day: unchanged == 2")
        check(not dcd["warnings"], "cross-day: no spurious bulk-field warning")

        # Same cross-day pull, but one row also has a REAL edit -> exactly that row, that field.
        day3b = json.loads(json.dumps(day3))
        day3b["rows"]["Y"]["fields"]["Vendor"] = "Gamma"
        dreal = diff_snapshots(day1, day3b)
        check(len(dreal["changed"]) == 1 and dreal["changed"][0]["id"] == "Y",
              "cross-day: real edit still detected (Y only)")
        check([c["field"] for c in dreal["changed"][0]["changes"]] == ["Vendor"],
              "cross-day: only the real field reported, not the derived one")

        # Migration: a snapshot taken BEFORE a field was added to TIME_DERIVED_FIELDS (still
        # carries it in `fields`) vs one taken AFTER (field excluded) must NOT report every
        # row as changed just because the stored field sets differ in shape.
        prefield_rows = json.loads(json.dumps(day1["rows"]))          # carries the field
        postfield_rows = {}
        for k, v in day3["rows"].items():
            f = {kk: vv for kk, vv in v["fields"].items() if kk not in TIME_DERIVED_FIELDS}
            postfield_rows[k] = {"title": v["title"], "hash": fingerprint(f), "fields": f}
        dmig = diff_snapshots({"as_of": "2026-07-22", "count": 2, "rows": prefield_rows},
                              {"as_of": "2026-07-24", "count": 2, "rows": postfield_rows})
        check(not dmig["changed"], "migration: pre-exclusion vs post-exclusion snapshot reports 0 changed")
    finally:
        TIME_DERIVED_FIELDS = real_tdf

    # Bulk-field guard fires for a NON-excluded field moving on >50% of rows.
    bulk_prev = {"as_of": "2026-07-22", "count": 4, "rows": {
        k: {"title": k, "hash": fingerprint({"Status": "Open"}), "fields": {"Status": "Open"}}
        for k in "PQRS"}}
    bulk_curr = json.loads(json.dumps(bulk_prev))
    bulk_curr["as_of"] = "2026-07-24"
    for k in ("P", "Q", "R"):                  # 3 of 4 = 75%
        bulk_curr["rows"][k]["fields"]["Status"] = "Closed"
    dbulk = diff_snapshots(bulk_prev, bulk_curr)
    check(any("'Status'" in w or '"Status"' in w for w in dbulk["warnings"]),
          "bulk guard: warns when a non-excluded field moves on >50% of rows")

    # Bulk guard fires at EXACTLY the threshold (>= not >). On a 6-row table a field moving
    # on precisely half the rows is the same signal and must not sail through.
    half_prev = {"as_of": "2026-07-22", "count": 4, "rows": {
        k: {"title": k, "hash": fingerprint({"Status": "Open"}), "fields": {"Status": "Open"}}
        for k in "PQRS"}}
    half_curr = json.loads(json.dumps(half_prev))
    half_curr["as_of"] = "2026-07-24"
    for k in ("P", "Q"):                       # exactly 2 of 4 = 50%
        half_curr["rows"][k]["fields"]["Status"] = "Closed"
    dhalf = diff_snapshots(half_prev, half_curr)
    check(len(dhalf["changed"]) == 2, "50pct boundary: 2 of 4 rows changed")
    check(any("'Status'" in w for w in dhalf["warnings"]),
          "bulk guard fires at exactly 50pct (>= threshold)")

    # Pagination: has_more=true with a null next_cursor must STOP, not refetch page 1
    # forever. Driven through the injectable fetch seam, no network.
    calls = {"n": 0}

    def bad_fetch(db_id, token, body):
        calls["n"] += 1
        return {"results": [{"id": "p%d" % calls["n"], "properties": {}}],
                "has_more": True, "next_cursor": None}
    got = pull_all("db", "tok", fetch=bad_fetch)
    check(calls["n"] == 1 and len(got) == 1, "null next_cursor with has_more stops after 1 page")

    # Normal pagination still follows the cursor and concatenates every page.
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

    # load_prev(): a corrupt LATEST falls back to the newest readable dated archive rather
    # than reporting "no baseline" (which would disable the collapse guard and let a
    # simultaneously-collapsed pull overwrite the baseline with an empty snapshot).
    global STATE_DIR, LATEST
    real_dir, real_latest = STATE_DIR, LATEST
    tmpdir = os.path.join(real_dir, "_selftest_tmp_capex")
    try:
        os.makedirs(tmpdir, exist_ok=True)
        STATE_DIR, LATEST = tmpdir, os.path.join(tmpdir, "capex-latest.json")
        good = {"as_of": "2026-07-22", "db_id": "x", "count": 1,
                "rows": {"A": {"title": "Acme", "hash": "h", "fields": {"Vendor": "1"}}}}
        with open(os.path.join(tmpdir, "capex-2026-07-22.json"), "w", encoding="utf-8") as f:
            json.dump(good, f)
        with open(LATEST, "w", encoding="utf-8") as f:
            f.write("{ truncated")
        prev, warn = load_prev()
        check(prev is not None and prev.get("count") == 1,
              "corrupt LATEST falls back to newest dated archive")
        check(warn and "archive" in warn, "archive fallback is reported, not silent")

        # With no archive either, it degrades to no-baseline. What protects the file at that
        # point is decide_persist()'s load_warning-based refusal (tested below), not the mere
        # fact of returning None here -- an earlier version of this file claimed protection
        # decide_persist() didn't actually implement yet; see the decide_persist docstring.
        os.remove(os.path.join(tmpdir, "capex-2026-07-22.json"))
        prev2, warn2 = load_prev()
        check(prev2 is None and warn2 and "no readable archive" in warn2,
              "no archive -> honest no-baseline with a warning")
    finally:
        for n in os.listdir(tmpdir) if os.path.isdir(tmpdir) else []:
            os.remove(os.path.join(tmpdir, n))
        if os.path.isdir(tmpdir):
            os.rmdir(tmpdir)
        STATE_DIR, LATEST = real_dir, real_latest

    # --- decide_persist() (independent-review fix, 2026-07-27) ---
    # Two real defects here, both empirically demonstrated against a live run() before this
    # function existed: (1) a corrupt/no-archive load combined with a 0-row pull persisted an
    # empty baseline with NO warning; (2) an exact 50% collapse (3 of 6 rows) persisted
    # silently because the guard used strict `<` instead of `<=`. Both are regression-tested
    # here so they can never silently return.

    with_prior = {"count": 6}

    # Defect 1: corruption + an empty pull together must refuse unconditionally, regardless
    # of what prev_count a fallback archive (or None) reports.
    p, w = decide_persist(None, 0, "previous snapshot unreadable (fake)")
    check(not p, "decide_persist: refuses when curr=0 and load_warning is set (prev=None)")
    check(w and "REFUSED" in w, "decide_persist: refusal is a loud warning, not silent")
    p2, w2 = decide_persist(with_prior, 0, "previous snapshot unreadable (fake)")
    check(not p2, "decide_persist: refuses when curr=0 and load_warning is set (prev_count>0)")

    # A genuine first-ever run with a clean 0-row pull (no load_warning) IS allowed to persist
    # -- but never silently. This is the "table really was empty pre-2026-07-26" case.
    p3, w3 = decide_persist(None, 0, None)
    check(p3, "decide_persist: allows a clean first-run 0-row persist (no load_warning)")
    check(w3 and "EMPTY" in w3, "decide_persist: still warns loudly even when it persists")

    # A 0-row pull against a real prior non-empty baseline refuses, same as before the fix.
    p4, w4 = decide_persist(with_prior, 0, None)
    check(not p4, "decide_persist: refuses 0 rows against a prior non-empty baseline")
    check(w4 and "REFUSED" in w4 and "0 rows" in w4, "decide_persist: refusal names the cause")

    # Defect 2: exact 50% collapse (3 of 6) must now refuse -- the bulk-field guard elsewhere
    # in this file already treats this exact boundary as suspicious via `>=`; the collapse
    # guard was the odd one out with strict `<` and is fixed to `<=` to match.
    p5, w5 = decide_persist(with_prior, 3, None)
    check(not p5, "decide_persist: refuses at the exact 50pct collapse boundary (3 of 6)")

    # One row above the boundary (4 of 6) is NOT a collapse and must persist normally --
    # confirms the fix didn't over-tighten the guard.
    p6, w6 = decide_persist(with_prior, 4, None)
    check(p6 and w6 is None, "decide_persist: 4 of 6 (just above the boundary) persists cleanly")

    # An ordinary unchanged pull persists with no warning at all.
    p7, w7 = decide_persist(with_prior, 6, None)
    check(p7 and w7 is None, "decide_persist: a normal same-count pull persists silently (no warning)")

    print("SELFTEST:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


# ---------- run ----------
# A pull that collapses to a fraction of the prior row count is far more likely to be a
# revoked/narrowed integration scope or an unshared DB (Notion still answers 200 with 0
# results) than several CapEx items genuinely vanishing between two runs. Persisting that
# would destroy the baseline and make the NEXT run report every remaining row as spuriously
# "added". Unlike the Tenant DB, this table WAS legitimately empty before 2026-07-26 — but
# going forward from a real baseline, a collapse is still the safer read than a mass deletion.
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
                       if n.startswith("capex-2") and n.endswith(".json"))
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

    Pulled out of run() as a pure function so the persist/refusal decision -- the one part
    of this file with real production risk -- is directly exercised by --selftest instead of
    only reachable through a live or mocked run(). An independent review (2026-07-27, before
    this file's first commit landed) caught two defects here empirically, neither covered by
    the original selftest because this logic lived inline in run():

      1. The 0-row refusal below only fired when `prev_count > 0`, so a corrupt LATEST with
         no readable archive (load_prev() returns prev=None with `load_warning` set) plus a
         0-row pull fell through BOTH refusal branches and persisted an empty snapshot
         silently -- with NO warning reaching RESULT_JSON. The next day's run would then see
         every real row as spuriously "added", itself warning-free, one day after the actual
         failure. Fixed by refusing unconditionally whenever curr_count == 0 AND load_warning
         is set: two independent failure signals (an empty pull, a degraded prior load) at
         once is never trustworthy regardless of what prev_count a fallback archive reports.
      2. The collapse guard used strict `<` against a 50% floor, so on a 6-row table an EXACT
         50% collapse (3 of 6) sailed through and persisted silently -- while this file's own
         bulk-field guard (see BULK_FIELD_RATIO above) deliberately uses `>=` at the same
         50% boundary with the explicit reasoning that on a small table this exact boundary is
         trivial to land on. Fixed to `<=` so both guards treat the boundary the same way.

    Returns (persisted: bool, warning: str or None). `warning` is set on every 0-row persist
    (even an allowed one) as well as on every refusal -- a silent 0-row persist is exactly
    what caused defect 1 above.
    """
    prev_count = (prev or {}).get("count", 0)

    if curr_count == 0 and load_warning:
        return False, (
            "REFUSED to persist snapshot: pull returned 0 rows AND the previous snapshot "
            "load was already degraded (%s). Two independent failure signals at once is "
            "never trustworthy. Prior state kept." % load_warning)

    if curr_count == 0:
        if prev_count > 0:
            # Unlike the Tenant DB, this table's true empty state (pre-2026-07-26) is a real
            # historical fact, not an access failure -- but once a real non-empty baseline
            # exists, a drop to 0 reads far more like an access/scope regression than every
            # CapEx item being deleted between two runs.
            return False, (
                "REFUSED to persist snapshot: pull returned 0 rows against a prior non-empty "
                "baseline (%d rows). Check the Notion integration's database access before "
                "trusting this as a real deletion. Prior snapshot kept." % prev_count)
        # A genuine first-ever run (or a run following a real prior empty state) with a clean
        # 0-row pull IS allowed to persist -- but never silently. This table has held real
        # rows since 2026-07-26, so going forward a 0-row day is worth a second look even
        # when nothing here technically refuses it.
        return True, (
            "Persisted an EMPTY snapshot (0 rows, no prior non-empty baseline to compare "
            "against). Verify Notion integration access before trusting tomorrow's diff -- "
            "CapEx & Maintenance Log is not expected to stay empty going forward.")

    if prev_count > 0 and curr_count <= prev_count * COLLAPSE_FLOOR_RATIO:
        return False, (
            "REFUSED to persist snapshot: row count collapsed %d -> %d (at or below %.0f%% "
            "of prior). Prior baseline kept. Check the Notion integration's database access "
            "before trusting this run's diff."
            % (prev_count, curr_count, COLLAPSE_FLOOR_RATIO * 100))

    return True, None


def run(as_of):
    os.makedirs(STATE_DIR, exist_ok=True)
    token = load_token()
    pages = pull_all(CAPEX_DB_ID, token)
    curr = build_snapshot(pages, as_of, CAPEX_DB_ID)
    prev, load_warning = load_prev()
    d = diff_snapshots(prev, curr)
    baseline = prev is None
    warnings = list(d.get("warnings", []))
    if load_warning:
        warnings.append(load_warning)

    persisted, persist_note = decide_persist(prev, curr["count"], load_warning)
    if persist_note:
        warnings.append(persist_note)
    if persisted:
        atomic_write_json(LATEST, curr)
        atomic_write_json(os.path.join(STATE_DIR, "capex-%s.json" % as_of), curr)

    # human summary
    if baseline:
        print("Baseline established: %d rows snapshotted for %s (no prior snapshot to diff)." % (curr["count"], as_of))
    else:
        print("CapEx & Maintenance Log diff %s -> %s: %d added, %d removed, %d changed, %d unchanged (of %d)." % (
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
        return run(a.date)
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
