#!/usr/bin/env python3
"""
acquisition_pipeline_snapshot_diff.py  --  ora-pm-ledger Block A helper.

WHY THIS EXISTS
  On 2026-08-16 the Acquisition Pipeline Tracker was found to have flipped to the
  UNIFORM-STAMP signature: all 20 rows carry one identical `last_edited_time` of
  2026-08-13. SKILL.md A.1's own rule -- "only trust a source whose dates VARY" --
  therefore no longer holds for it, and its A.1 Reality-table entry ("LIVE --
  varies", on 2026-07-15 evidence) is stale.

  This is a DOWNGRADE, not a freeze. Unlike the Tenant DB (stuck in March 2026
  forever, genuinely inert), this column is still ADVANCING -- it moved three days
  before the observation. A zero from the timestamp query is therefore probably
  real; it simply rests on a single unverifiable signal with nothing corroborating
  it. That made this the LAST of the six A.1 database sources with neither varying
  timestamps nor a snapshot-diff detector.

  This script closes that gap, applying the mechanism already proven four times
  (tenant_db, capex, property_register, deal_sourcing): full paginated pull ->
  per-row fingerprint -> diff against the previously persisted snapshot. As with
  the Deal Sourcing sibling, the REST timestamp check is NOT retired -- run both;
  the timestamp answers "did a row move", this answers "what moved in it".

WHAT IT DOES
  --run [--date YYYY-MM-DD]
     1. Pulls every Acquisition Pipeline row via REST (paginated).
     2. Normalizes each row's properties to plain values (skipping volatile
        metadata: created/last_edited time+by, and the date-derived formula
        below), fingerprints each row (sha256).
     3. Loads the previous snapshot (state/acquisition-pipeline-latest.json).
     4. Emits a diff: added / removed / changed (field-level old->new), keyed on
        the Notion PAGE ID -- never on "Deal Name", which is a free-text title an
        agent or Gabriel renames freely (address corrections are routine in this
        tracker), so a rename would otherwise read as one row removed + one added.
     5. Writes the new snapshot to latest + a dated archive.
     6. Prints a JSON block on the last line prefixed `RESULT_JSON=`.
        First run = baseline, no diff.
  --selftest
     Runs the diff engine against synthetic snapshots, no network. Exit 0 = pass.

DATE-DERIVED FIELDS -- ONE FOUND, AND IT IS THE DANGEROUS KIND (checked live 2026-08-16)
  The schema carries THREE formula fields. Each expression was read live from
  `GET /v1/data_sources/{id}` rather than inferred from its name -- the discipline
  that exists because tenant_db_snapshot_diff.py reported 267 of 298 rows changed
  on its first real cross-day run (2026-07-24) after five calendar-derived formulas
  were left in by assumption.

    EXCLUDED -- '\u23f0 Action Overdue'
      if(empty(prop("Next Action Date")), "—",
         if(prop("Next Action Date") < now(),
            "OVERDUE " + format(dateBetween(now(), prop("Next Action Date"), "days")) + "d",
            ""))
      Contains BOTH now() and dateBetween. This is the worst variant of the defect
      class, because it fails two different ways at once:
        (a) it TICKS -- any row with a past Next Action Date reports "OVERDUE 4d"
            then "OVERDUE 5d" the next day, forever; and
        (b) it BAND-FLIPS -- "" -> "OVERDUE 1d" the day a Next Action Date passes,
            which is indistinguishable from a human edit.
      Left unexcluded it would false-positive on every overdue deal every single
      day. That was not hypothetical at build time: two rows (4484 Robertson Road,
      5515 Catfish Court) were already overdue, so the detector would have been
      broken on day one.

      *** THE BULK-FIELD GUARD WOULD NOT HAVE CAUGHT THIS. *** Measured against
      the real 20 rows at build time: exactly 3 would drift per day (2 counter
      ticks + 1 band-flip) = 15%, far below the 50% BULK_FIELD_RATIO threshold.
      The guard stayed silent in the differential control. On a ~20-row table
      where only the subset carrying a Next Action Date can ever drift, the
      backstop is structurally incapable of firing on this field -- so reading
      each formula's expression live was not belt-and-braces here, it was the
      only thing standing between this script and a permanently noisy digest.

    KEPT -- 'Replacement Cost Ratio'
      A market-keyed ratio of two STATIC stored numbers (Purchase Price / Total SF)
      over a per-market replacement-cost constant (one RCT LOW figure per market,
      Columbus OH through Louisville KY; the figures live only in the private RCT
      file since 2026-11-13, never in this public repo). No now()/today()/dateBetween
      anywhere in the expression.
      *** This field is GOVERNOR-ADJACENT. *** It is the RCT basis denominator --
      ORA's buy-at-a-deep-discount-to-replacement-cost discipline is read directly off
      it. Excluding formulas by TYPE rather than by NAME would have silently
      blinded this detector to RCR movement, exactly as it would have blinded the
      Property Register sibling to 'LTV'. Exclusion is therefore BY NAME, and
      --selftest asserts RCR still diffs.

    KEPT -- 'Price Per SF'
      if(and(prop("Total SF") != 0, !empty(prop("Total SF"))),
         prop("Purchase Price") / prop("Total SF"), 0)
      Ratio of two static stored numbers. A real change signal.

  Net: TIME_DERIVED_FIELDS is NON-EMPTY here -- matching property_register, and
  deliberately NOT matching the deal_sourcing sibling whose set is empty. Copying
  the closest-endpoint sibling's empty set would have shipped the defect.

STORAGE
  state/acquisition-pipeline-latest.json        <- previous/current pointer
  state/acquisition-pipeline-<YYYY-MM-DD>.json  <- dated archive (audit trail)

TOKEN
  NOTION_TOKEN from C:\\Users\\Owner\\oxford-command-center\\.env (read-only).

ENDPOINT
  `bcfe4a03...` is a DATA SOURCE id, not a database page id (the parent database
  page is `46c8a5c6-8b37-4c53-a10d-0f55c97613e5`). This database is MULTI-SOURCE,
  so `/v1/databases/{id}/query` 404s on the collection id and 400s on the db id at
  Notion-Version 2022-06-28. Query it at `POST /v1/data_sources/{id}/query` with
  `Notion-Version: 2025-09-03` -- verified 200 live 2026-08-16, 20 rows, 38
  properties. Same endpoint/version pair as the deal_sourcing sibling; the other
  three siblings use /v1/databases @ 2022-06-28 because their ids are
  single-source database page ids.
"""
import argparse, datetime, hashlib, json, os, sys, time, urllib.request, urllib.error

# Harness-spawned/scheduled runs get a cp1252 stdout on Windows. This database carries
# emoji in both property NAMES ('\u23f0 Action Overdue') and VALUES ('\u23f0 Tickler -- call
# broker...'), so an un-reconfigured stdout raises UnicodeEncodeError mid-print and loses
# the run. Observed for real while reading this schema at build time.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# Data-source id (NOT the database page id -- see ENDPOINT note in the module docstring).
ACQ_PIPELINE_DS_ID = "bcfe4a03-7e61-4ac1-a0bb-c44174fa138b"
ENV_PATH = r"C:\Users\Owner\oxford-command-center\.env"
STATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state")
LATEST = os.path.join(STATE_DIR, "acquisition-pipeline-latest.json")
ARCHIVE_PREFIX = "acquisition-pipeline-2"
SKIP_TYPES = {"created_time", "last_edited_time", "created_by", "last_edited_by"}

# See DATE-DERIVED FIELDS in the module docstring. Written as an escape rather than a
# literal so the exclusion cannot be silently broken by a re-save under a non-UTF-8
# encoding -- if this string stops matching the live property name, the field returns to
# the diff and every overdue deal false-positives daily.
# EXCLUDE BY NAME, NEVER BY TYPE: 'Replacement Cost Ratio' (governor-adjacent, the RCT
# basis denominator) and 'Price Per SF' are formulas too and MUST keep diffing.
TIME_DERIVED_FIELDS = {"\u23f0 Action Overdue"}

# A field changing on more than this share of all rows is almost certainly bulk/derived
# rather than edited, and is reported as a warning instead of silently inflating the diff.
BULK_FIELD_RATIO = 0.5


# ---------- property normalization ----------
def _people(v):
    return "|".join(sorted(p.get("id", "") for p in v or []))


def _array_digest(arr, _depth=0):
    """Order-sensitive content digest of a rollup array's elements (OI-151).

    No rollup field exists on this database today (checked live 2026-08-16 -- the schema
    carries none), but this keeps norm_prop forward-safe if one is ever added, at zero
    cost while it stays unused.

    sha1 is a fingerprint here, not a security primitive: the only property needed is that
    different content produces a different token.
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
        # Two relation fields here: 'PSA Deals Record' and 'Sourcing Entry' (the latter
        # points at the Deal Sourcing Log). Sorted id join keeps the value stable across
        # re-reads regardless of Notion's return order.
        return "|".join(sorted(r.get("id", "") for r in p.get("relation", [])))
    if t == "files":
        return "|".join(sorted(f.get("name", "") for f in p.get("files", [])))
    if t == "unique_id":
        # 'Deal ID' is a unique_id property: {"prefix": "ORA", "number": 12} -> "ORA12".
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
    """{prop_name: normalized_value} excluding skipped metadata/None and date-derived formulas.

    Filtering HERE (not only at compare time) keeps the excluded field structurally ABSENT
    from the persisted snapshot, so calendar drift cannot enter the diff at all rather than
    merely being filtered out of it later.
    """
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

    Applied on BOTH sides of the diff so a snapshot written before a field was added to
    TIME_DERIVED_FIELDS still compares cleanly against one written after -- see
    tenant_db_snapshot_diff.py's 2026-07-24 fix for the incident this prevents (267 of 298
    rows false-positived on the first cross-day run there).
    """
    return {k: v for k, v in (row.get("fields") or {}).items() if k not in TIME_DERIVED_FIELDS}


def fingerprint(fields):
    blob = json.dumps(fields, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def detect_truncation(pages):
    """Warnings for any property value Notion truncated in the query response.

    Notion caps multi-reference property values (relation, people, rollup arrays) at 25
    items in database-query results and sets `has_more` ON THE PROPERTY OBJECT. This
    database carries two relation fields ('PSA Deals Record', 'Sourcing Entry'), both at
    max length 1 today -- so this is latent, but a deal accumulating >25 linked sourcing
    entries would otherwise have changes beyond the 25th silently invisible.
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


def detect_missing_exclusions(pages):
    """Warn if a TIME_DERIVED_FIELDS name no longer exists on any pulled row.

    The exclusion matches by EXACT property name, so renaming the field in Notion (dropping
    the emoji, a variation-selector normalization, any text edit) silently stops it matching
    and the calendar-derived value returns to the diff. The bulk-field guard does NOT cover
    this: the rename itself trips it once as a schema change, but from the next day onward
    only the overdue subset drifts -- ~2-3 of 20 rows, 10-15%, structurally below the 50%
    threshold -- so the digest would false-positive every day thereafter with no further
    signal. Raised by independent review 2026-08-16 as the mirror image of the risk the
    TIME_DERIVED_FIELDS comment documents but did not detect.

    Silent on an empty pull: 0 rows means an access failure (decide_persist refuses it), and
    every exclusion would trivially look "missing", which would bury the real refusal notice.
    """
    if not pages:
        return []
    present = set()
    for pg in pages:
        present.update((pg.get("properties") or {}).keys())
    return ["excluded field %r no longer exists on ANY pulled row — it was probably RENAMED "
            "in Notion. The exclusion matches by exact name, so it is no longer suppressing "
            "anything and this field's calendar drift is now inflating the diff. Update "
            "TIME_DERIVED_FIELDS to the new name; do NOT simply delete the entry." % name
            for name in sorted(TIME_DERIVED_FIELDS) if name not in present]


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
    # register's 2026-08-11 review fix) -- len(c) systematically dilutes the ratio and lets
    # a partially-populated derived field slip under the threshold forever. That matters
    # more here than anywhere: this table has only ~20 rows and only the subset carrying a
    # Next Action Date can ever drift.
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
                    "<absent> -> value). Diagnose which before excluding anything. NEVER "
                    "exclude 'Replacement Cost Ratio' or 'Price Per SF' without re-reading "
                    "their expressions live first — both are static-input formulas, and RCR "
                    "is the governor-adjacent replacement-cost basis denominator."
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
    """One POST to Notion's data-source query endpoint, with bounded retry.

    Split out from pull_all so the pagination loop can be exercised offline by --selftest
    via the `fetch` seam. Uses /v1/data_sources/{id}/query @ 2025-09-03 -- see the module
    docstring's ENDPOINT note for why this differs from three of the four siblings.
    """
    req = urllib.request.Request(
            "https://api.notion.com/v1/data_sources/%s/query" % db_id,
            data=json.dumps(body).encode(),
            headers={"Authorization": "Bearer " + token,
                     "Notion-Version": "2025-09-03",
                     "Content-Type": "application/json"},
            method="POST")
    # Bounded retry on rate-limit/transient server errors. Unattended at 18:00, one Notion
    # hiccup would otherwise be an unhandled HTTPError and a lost run.
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
            # Covers a failure to connect AND a socket-read timeout on the response body
            # (TimeoutError is neither HTTPError nor URLError; OSError is the common base
            # of both, plus ConnectionReset). Carried forward from property_register's
            # OI-152 fix. A malformed body still raises JSONDecodeError (a ValueError) and
            # is correctly NOT retried, since it isn't transient.
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
        # ever isn't, re-sending the same body would refetch page 1 forever -- an infinite
        # loop in an unattended 18:00 job. Stop and let the collapse guard judge a short pull.
        if not cursor:
            break
    return pages


# ---------- self-test ----------
def selftest():
    # Declared up front (Python requires `global` before first use in a scope): the
    # differential control below temporarily disables TIME_DERIVED_FIELDS, and the
    # load_prev/run cases redirect STATE_DIR/LATEST at a temp dir. All three are restored
    # in `finally` blocks.
    global TIME_DERIVED_FIELDS, STATE_DIR, LATEST

    ok = True
    def check(cond, msg):
        nonlocal ok
        print(("  PASS " if cond else "  FAIL ") + msg)
        ok = ok and cond

    OVERDUE = "\u23f0 Action Overdue"

    # ---- core diff engine ----
    prev = {"as_of": "2026-08-15", "count": 3, "rows": {
        "A": {"title": "4484 Robertson Road — Madison, WI",
              "hash": fingerprint({"Stage": "Candidate", "Purchase Price": "2750000.0"}),
              "fields": {"Stage": "Candidate", "Purchase Price": "2750000.0"}},
        "B": {"title": "511 Industrial Mile Road — Columbus, OH",
              "hash": fingerprint({"Stage": "Candidate"}),
              "fields": {"Stage": "Candidate"}},
        "C": {"title": "Old passed deal",
              "hash": fingerprint({"Stage": "Dead"}),
              "fields": {"Stage": "Dead"}},
    }}
    curr = {"as_of": "2026-08-16", "count": 3, "rows": {
        "A": {"title": "4484 Robertson Road — Madison, WI",
              "hash": fingerprint({"Stage": "Under Contract", "Purchase Price": "2750000.0"}),
              "fields": {"Stage": "Under Contract", "Purchase Price": "2750000.0"}},   # stage move
        "B": {"title": "511 Industrial Mile Road — Columbus, OH",
              "hash": fingerprint({"Stage": "Candidate"}),
              "fields": {"Stage": "Candidate"}},                                       # unchanged
        "D": {"title": "New candidate — 12021 Sheraton Lane",
              "hash": fingerprint({"Stage": "Candidate"}),
              "fields": {"Stage": "Candidate"}},                                       # added
        # C removed
    }}
    d = diff_snapshots(prev, curr)
    check([x["id"] for x in d["added"]] == ["D"], "added == [D]")
    check([x["id"] for x in d["removed"]] == ["C"], "removed == [C]")
    check(len(d["changed"]) == 1 and d["changed"][0]["id"] == "A", "changed == [A]")
    ch = d["changed"][0]["changes"] if d["changed"] else []
    check(len(ch) == 1 and ch[0]["field"] == "Stage"
          and ch[0]["old"] == "Candidate" and ch[0]["new"] == "Under Contract",
          "A.Stage Candidate -> Under Contract")
    check(d["unchanged"] == 1, "unchanged == 1 (B)")
    d0 = diff_snapshots(None, curr)
    check(len(d0["added"]) == 3 and not d0["removed"] and not d0["changed"], "baseline: all added, no diff")

    # ---- diff key is the Notion PAGE ID, never the title ----
    # Address corrections are routine in this tracker; a retitle under a stable page id
    # must read as CHANGED, never as one removed + one added.
    prev_rename = {"as_of": "2026-08-15", "count": 1, "rows": {
        "X": {"title": "808 Rhoads Ave", "hash": fingerprint({"Stage": "Candidate"}),
              "fields": {"Stage": "Candidate"}}}}
    curr_rename = {"as_of": "2026-08-16", "count": 1, "rows": {
        "X": {"title": "808 Rhoads Avenue — Columbus, OH (corrected)",
              "hash": fingerprint({"Stage": "Candidate"}), "fields": {"Stage": "Candidate"}}}}
    drn = diff_snapshots(prev_rename, curr_rename)
    check(not drn["added"] and not drn["removed"],
          "title-only edit under a stable page id is NOT added+removed")

    # ---- TIME_DERIVED_FIELDS: assert the REAL production set ----
    # Exercises the actual production constant so emptying it, renaming it, or adding a
    # static-input formula to it fails loudly instead of silently.
    check(TIME_DERIVED_FIELDS == {OVERDUE},
          "production set is exactly {'\u23f0 Action Overdue'} — the one calendar-derived formula")
    check("Replacement Cost Ratio" not in TIME_DERIVED_FIELDS,
          "governor-adjacent 'Replacement Cost Ratio' is NOT excluded (exclude by NAME, never by TYPE)")
    check("Price Per SF" not in TIME_DERIVED_FIELDS,
          "static-input 'Price Per SF' is NOT excluded")

    def mkrow(title, stage, overdue, rcr, ppsf, next_action_date):
        f = {"Stage": stage, OVERDUE: overdue, "Replacement Cost Ratio": rcr,
             "Price Per SF": ppsf, "Next Action Date": next_action_date}
        f = {k: v for k, v in f.items() if k not in TIME_DERIVED_FIELDS}
        return {"title": title, "hash": fingerprint(f), "fields": f}

    # ---- THE regression this script exists to prevent ----
    # Cross-day drift with NOTHING really edited: the overdue counter ticks 4d -> 5d on one
    # row and BAND-FLIPS "" -> "OVERDUE 1d" on another. Must produce ZERO changes.
    day1 = {"as_of": "2026-08-15", "count": 2, "rows": {
        "R1": mkrow("4484 Robertson Road", "Candidate", "OVERDUE 4d", "0.38", "82.5", "2026-08-12/"),
        "R2": mkrow("5515 Catfish Court", "Candidate", "", "0.36", "79.0", "2026-08-16/"),
    }}
    day2_driftonly = {"as_of": "2026-08-16", "count": 2, "rows": {
        "R1": mkrow("4484 Robertson Road", "Candidate", "OVERDUE 5d", "0.38", "82.5", "2026-08-12/"),
        "R2": mkrow("5515 Catfish Court", "Candidate", "OVERDUE 1d", "0.36", "79.0", "2026-08-16/"),
    }}
    ddrift = diff_snapshots(day1, day2_driftonly)
    check(not ddrift["changed"] and not ddrift["warnings"],
          "cross-day: overdue counter tick AND band-flip produce 0 changed, 0 warnings")

    # A REAL edit landing alongside that same drift must still be caught.
    day2_realedit = {"as_of": "2026-08-16", "count": 2, "rows": {
        "R1": mkrow("4484 Robertson Road", "Under Contract", "OVERDUE 5d", "0.38", "82.5", "2026-08-12/"),
        "R2": mkrow("5515 Catfish Court", "Candidate", "OVERDUE 1d", "0.36", "79.0", "2026-08-16/"),
    }}
    dreal = diff_snapshots(day1, day2_realedit)
    check(len(dreal["changed"]) == 1 and dreal["changed"][0]["id"] == "R1",
          "a real Stage edit alongside calendar drift is still detected")
    check({c["field"] for c in dreal["changed"][0]["changes"]} == {"Stage"},
          "only the real field is reported — drift does not leak into the change list")

    # A real Next Action Date edit (the DRIVER of the excluded formula) must still diff --
    # excluding the derived field must not blind the detector to its static input.
    day2_datemove = {"as_of": "2026-08-16", "count": 2, "rows": {
        "R1": mkrow("4484 Robertson Road", "Candidate", "", "0.38", "82.5", "2026-08-25/"),
        "R2": mkrow("5515 Catfish Court", "Candidate", "OVERDUE 1d", "0.36", "79.0", "2026-08-16/"),
    }}
    ddate = diff_snapshots(day1, day2_datemove)
    check(len(ddate["changed"]) == 1
          and {c["field"] for c in ddate["changed"][0]["changes"]} == {"Next Action Date"},
          "rescheduling Next Action Date IS detected (the driver is kept, only the derivative dropped)")

    # ---- governor-adjacent RCR must still diff ----
    day2_rcr = {"as_of": "2026-08-16", "count": 2, "rows": {
        "R1": mkrow("4484 Robertson Road", "Candidate", "OVERDUE 5d", "0.47", "102.1", "2026-08-12/"),
        "R2": mkrow("5515 Catfish Court", "Candidate", "OVERDUE 1d", "0.36", "79.0", "2026-08-16/"),
    }}
    drcr = diff_snapshots(day1, day2_rcr)
    fields_moved = {c["field"] for c in drcr["changed"][0]["changes"]} if drcr["changed"] else set()
    check("Replacement Cost Ratio" in fields_moved,
          "a real Replacement Cost Ratio move IS detected (governor-adjacent, never filtered)")
    check("Price Per SF" in fields_moved, "a real Price Per SF move IS detected")

    # ---- DIFFERENTIAL CONTROL: prove the exclusion is what suppresses the drift ----
    # Rebuild BOTH sides with the exclusion disabled. Both snapshots then genuinely carry
    # the field with different values (no <absent> asymmetry), so a non-zero result here is
    # real drift, not a field-set artifact. This is the control that proves the drift test
    # above is capable of failing.
    real_set = TIME_DERIVED_FIELDS
    try:
        TIME_DERIVED_FIELDS = set()
        d1_ctl = {"as_of": "2026-08-15", "count": 2, "rows": {
            "R1": mkrow("4484 Robertson Road", "Candidate", "OVERDUE 4d", "0.38", "82.5", "2026-08-12/"),
            "R2": mkrow("5515 Catfish Court", "Candidate", "", "0.36", "79.0", "2026-08-16/"),
        }}
        d2_ctl = {"as_of": "2026-08-16", "count": 2, "rows": {
            "R1": mkrow("4484 Robertson Road", "Candidate", "OVERDUE 5d", "0.38", "82.5", "2026-08-12/"),
            "R2": mkrow("5515 Catfish Court", "Candidate", "OVERDUE 1d", "0.36", "79.0", "2026-08-16/"),
        }}
        dctl = diff_snapshots(d1_ctl, d2_ctl)
        absent_markers = [c for row in dctl["changed"] for c in row["changes"]
                          if c["old"] == "<absent>" or c["new"] == "<absent>"]
        check(len(dctl["changed"]) == 2,
              "CONTROL: with the exclusion disabled, calendar drift false-positives BOTH rows")
        check(not absent_markers,
              "CONTROL is honest: both sides carry the field, zero <absent> markers (not a field-set artifact)")
        check(any(OVERDUE in w for w in dctl["warnings"]),
              "CONTROL: bulk-field guard would have flagged the drift field (2/2 rows)")
    finally:
        TIME_DERIVED_FIELDS = real_set
    check(TIME_DERIVED_FIELDS == {OVERDUE}, "production set restored after the control")

    # ---- structural absence: excluded field never enters a built snapshot ----
    pg = {"id": "P1", "properties": {
        "Deal Name": {"type": "title", "title": [{"plain_text": "4484 Robertson Road"}]},
        "Stage": {"type": "select", "select": {"name": "Candidate"}},
        OVERDUE: {"type": "formula", "formula": {"type": "string", "string": "OVERDUE 4d"}},
        "Replacement Cost Ratio": {"type": "formula", "formula": {"type": "number", "number": 0.38}},
    }}
    snap = build_snapshot([pg], "2026-08-16", "ds")
    check(OVERDUE not in snap["rows"]["P1"]["fields"],
          "excluded field is structurally ABSENT from the persisted snapshot, not merely filtered at compare time")
    check("Replacement Cost Ratio" in snap["rows"]["P1"]["fields"],
          "kept formula IS persisted")

    # ---- migration: a pre-fix snapshot carrying the field compares cleanly ----
    prefix_row = {"title": "4484 Robertson Road", "hash": "stale-hash-from-old-field-set",
                  "fields": {"Stage": "Candidate", OVERDUE: "OVERDUE 4d",
                             "Replacement Cost Ratio": "0.38"}}
    postfix_row = {"title": "4484 Robertson Road",
                   "hash": fingerprint({"Stage": "Candidate", "Replacement Cost Ratio": "0.38"}),
                   "fields": {"Stage": "Candidate", "Replacement Cost Ratio": "0.38"}}
    dmig = diff_snapshots({"as_of": "2026-08-15", "count": 1, "rows": {"M": prefix_row}},
                          {"as_of": "2026-08-16", "count": 1, "rows": {"M": postfix_row}})
    check(not dmig["changed"],
          "pre-fix snapshot (carrying the excluded field) compares cleanly against a post-fix one")

    # ---- bulk-field guard ----
    bulk_prev = {"as_of": "2026-08-15", "count": 4, "rows": {
        k: {"title": k, "hash": fingerprint({"Market": "Columbus OH"}), "fields": {"Market": "Columbus OH"}}
        for k in "PQRS"}}
    bulk_curr = json.loads(json.dumps(bulk_prev))
    bulk_curr["as_of"] = "2026-08-16"
    for k in ("P", "Q", "R"):                  # 3 of 4 = 75%
        bulk_curr["rows"][k]["fields"]["Market"] = "Madison WI"
    dbulk = diff_snapshots(bulk_prev, bulk_curr)
    check(any("'Market'" in w for w in dbulk["warnings"]),
          "bulk guard: warns when a field moves on >50% of rows")
    check(any("Replacement Cost Ratio" in w for w in dbulk["warnings"]),
          "bulk-guard text names the two formulas that must NOT be blindly excluded")

    half_curr = json.loads(json.dumps(bulk_prev))
    half_curr["as_of"] = "2026-08-16"
    for k in ("P", "Q"):                       # exactly 2 of 4 = 50%
        half_curr["rows"][k]["fields"]["Market"] = "Madison WI"
    dhalf = diff_snapshots(bulk_prev, half_curr)
    check(len(dhalf["changed"]) == 2, "50pct boundary: 2 of 4 rows changed")
    check(any("'Market'" in w for w in dhalf["warnings"]),
          "bulk guard fires at exactly 50pct (>= threshold)")

    # Denominator is COMPARED rows, not all current rows.
    sub_prev = {"as_of": "2026-08-15", "count": 5, "rows": {
        "L%d" % i: {"title": "L%d" % i, "hash": "h", "fields": {"Notes": "old"}} for i in range(5)}}
    sub_curr = {"as_of": "2026-08-16", "count": 40, "rows": {}}
    for i in range(5):
        sub_curr["rows"]["L%d" % i] = {"title": "L%d" % i, "hash": "h", "fields": {"Notes": "new"}}
    for i in range(35):
        sub_curr["rows"]["N%d" % i] = {"title": "N%d" % i, "hash": "h", "fields": {}}
    dsub = diff_snapshots(sub_prev, sub_curr)
    check(any("'Notes'" in w and "compared rows" in w for w in dsub["warnings"]),
          "bulk guard denominates by COMPARED rows (5/5), not all current rows (5/40)")

    # ---- normalization spot-checks ----
    check(norm_prop({"type": "title", "title": [{"plain_text": "511 Industrial Mile Road"}]})
          == "511 Industrial Mile Road", "norm_prop: title normalizes")
    check(norm_prop({"type": "number", "number": 2750000.0}) == repr(2750000.0),
          "norm_prop: number normalizes stably")
    check(norm_prop({"type": "number", "number": None}) == "",
          "norm_prop: empty number is '' (not the string 'None')")
    check(norm_prop({"type": "select", "select": {"name": "Under Contract"}}) == "Under Contract",
          "norm_prop: select normalizes")
    check(norm_prop({"type": "select", "select": None}) == "",
          "norm_prop: cleared select is '' (Stage can be blanked)")
    check(norm_prop({"type": "relation", "relation": [{"id": "b"}, {"id": "a"}]}) == "a|b",
          "norm_prop: relation ids sort deterministically ('Sourcing Entry', 'PSA Deals Record')")
    check(norm_prop({"type": "unique_id", "unique_id": {"prefix": "ORA", "number": 12}}) == "ORA12",
          "norm_prop: 'Deal ID' unique_id normalizes to prefix+number")
    check(norm_prop({"type": "unique_id", "unique_id": {"prefix": None, "number": 7}}) == "7",
          "norm_prop: unique_id with null prefix does not emit 'None'")
    check(norm_prop({"type": "date", "date": {"start": "2026-08-21"}}) == "2026-08-21/",
          "norm_prop: 'Next Action Date' normalizes")
    check(norm_prop({"type": "url", "url": None}) == "",
          "norm_prop: empty 'Listing Ask Source' url is ''")
    check(norm_prop({"type": "formula", "formula": {"type": "number", "number": 0.38}}) == "0.38",
          "norm_prop: numeric formula (Replacement Cost Ratio) normalizes")
    check(norm_prop({"type": "last_edited_time", "last_edited_time": "2026-08-13T16:13:00Z"}) is None,
          "norm_prop: 'Last Updated' (the uniform-stamp column) is skipped as metadata")
    check(norm_prop({"type": "created_time", "created_time": "2026-03-22T00:00:00Z"}) is None,
          "norm_prop: created_time is skipped as metadata")

    # ---- truncation detector ----
    trunc_pages = [{"id": "T1", "properties": {
        "Deal Name": {"type": "title", "title": [{"plain_text": "Big deal"}]},
        "Sourcing Entry": {"type": "relation", "relation": [{"id": "r"}], "has_more": True}}}]
    check(any("Sourcing Entry" in w for w in detect_truncation(trunc_pages)),
          "truncation detector flags a relation Notion capped at 25 items")
    check(detect_truncation([pg]) == [], "truncation detector is silent on untruncated rows")

    # ---- renamed-exclusion detector (independent review, 2026-08-16) ----
    # `pg` carries the excluded field under its real name, so this must be silent.
    check(detect_missing_exclusions([pg]) == [],
          "rename detector is silent while the excluded field still exists")
    # Simulate the rename: same page, the emoji dropped from the property name.
    renamed = {"id": "P1", "properties": {
        k.replace(OVERDUE, "Action Overdue"): v for k, v in pg["properties"].items()}}
    warns_renamed = detect_missing_exclusions([renamed])
    check(len(warns_renamed) == 1 and "RENAMED" in warns_renamed[0],
          "rename detector FIRES when the excluded field is renamed (the drift would be "
          "10-15% — structurally below the bulk guard, so nothing else would catch it)")
    check(detect_missing_exclusions([]) == [],
          "rename detector is silent on a 0-row pull (that is an access failure, not a rename)")

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

    # ---- decide_persist battery ----
    prev20 = {"count": 20}
    check(decide_persist(prev20, 20, None)[0] is True, "persist: steady 20 -> 20")
    check(decide_persist(prev20, 19, None)[0] is True, "persist: 20 -> 19 (a genuine removal) is allowed")
    ok_collapse, w_collapse = decide_persist(prev20, 10, None)
    check(ok_collapse is False and "collapsed" in w_collapse,
          "refuse: 20 -> 10 is at the 50pct collapse floor")
    ok_zero, w_zero = decide_persist(prev20, 0, None)
    check(ok_zero is False and "0 rows" in w_zero, "refuse: 0-row pull against a non-empty baseline")
    ok_first, w_first = decide_persist(None, 0, None)
    check(ok_first is False and "no prior baseline" in w_first,
          "refuse: 0-row FIRST run — an empty pipeline is always an access failure, never a real state")
    ok_deg, w_deg = decide_persist(None, 0, "previous snapshot unreadable")
    check(ok_deg is False and "degraded" in w_deg,
          "refuse: 0 rows AND a degraded prior load names BOTH signals (distinct branch)")
    check(decide_persist(None, 20, None)[0] is True, "persist: clean 20-row first run establishes a baseline")

    # ---- load_prev() corruption / missing fallback ----
    real_dir, real_latest = STATE_DIR, LATEST
    tmpdir = os.path.join(real_dir, "_selftest_tmp_acqpipeline")
    try:
        os.makedirs(tmpdir, exist_ok=True)
        STATE_DIR, LATEST = tmpdir, os.path.join(tmpdir, "acquisition-pipeline-latest.json")
        good = {"as_of": "2026-08-15", "count": 1, "db_id": "ds",
                "rows": {"A": {"title": "t", "hash": "h", "fields": {"Stage": "Candidate"}}}}
        with open(os.path.join(tmpdir, "acquisition-pipeline-2026-08-15.json"), "w", encoding="utf-8") as f:
            json.dump(good, f)
        with open(LATEST, "w", encoding="utf-8") as f:
            f.write("{ this is not valid json")
        prev_c, warn_c = load_prev()
        check(prev_c is not None and prev_c["count"] == 1,
              "corrupt LATEST falls back to the newest dated archive")
        check(warn_c and "unreadable" in warn_c, "corrupt LATEST is reported, not silently swallowed")
        os.remove(LATEST)
        prev_m, warn_m = load_prev()
        check(prev_m is not None and prev_m["count"] == 1,
              "MISSING LATEST also falls back to the archive (not treated as 'no baseline')")
        check(warn_m and "MISSING" in warn_m, "missing LATEST is reported loudly")

        # ---- run() end-to-end through the _pages seam (offline) ----
        for n in os.listdir(tmpdir):
            os.remove(os.path.join(tmpdir, n))
        rc = run("2026-08-16", _pages=[pg])
        check(rc == 0 and os.path.exists(LATEST), "run(): clean first pull persists and exits 0")
        with open(LATEST, encoding="utf-8") as f:
            persisted_snap = json.load(f)
        check(OVERDUE not in persisted_snap["rows"]["P1"]["fields"],
              "run(): excluded field absent from the file actually written to disk")
        check(not os.path.exists(LATEST + ".tmp"), "run(): atomic write leaves no .tmp residue")
        rc0 = run("2026-08-16", _pages=[])
        check(rc0 == 0, "run(): a 0-row pull still exits 0 (reports, does not crash)")
        with open(LATEST, encoding="utf-8") as f:
            still = json.load(f)
        check(still["count"] == 1, "run(): the 0-row pull REFUSED to overwrite the prior baseline")
    finally:
        for n in os.listdir(tmpdir) if os.path.isdir(tmpdir) else []:
            os.remove(os.path.join(tmpdir, n))
        if os.path.isdir(tmpdir):
            os.rmdir(tmpdir)
        STATE_DIR, LATEST = real_dir, real_latest

    print("SELFTEST:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


# ---------- run ----------
# A pull that collapses to a fraction of the prior row count is far more likely to be a
# revoked/narrowed integration scope or an unshared DB (Notion still answers 200 with 0
# results) than most of the acquisition pipeline genuinely vanishing between two runs.
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
    collapse guard below and lets a simultaneously-collapsed pull overwrite the baseline
    with an empty snapshot. Pattern carried forward from property_register_snapshot_diff.py's
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
    production risk -- is directly exercised by --selftest.

    ONE DELIBERATE CHOICE, matching Property Register / Deal Sourcing rather than CapEx: the
    0-row-with-no-prior-baseline case REFUSES here instead of persisting with a warning. The
    Acquisition Pipeline is an accreting tracker -- dead deals keep their row with a Stage
    and Kill Reason rather than being deleted -- so a 0-row pull is always an access failure
    (revoked/narrowed integration scope, or the data source unshared; Notion answers 200 with
    an empty result set in all of those cases), never a real empty state. CapEx was allowed a
    clean 0-row baseline only because that table genuinely was empty before 2026-07-26.

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
                "baseline (%d rows). Check the Notion integration's access to the Acquisition "
                "Pipeline data source before trusting this as a real deletion. Prior snapshot "
                "kept." % prev_count)
        return False, (
            "REFUSED to persist snapshot: pull returned 0 rows and there is no prior "
            "baseline. An empty Acquisition Pipeline Tracker is never a real state — dead "
            "deals keep their row with a Stage and Kill Reason rather than being removed — "
            "so this is an access failure (revoked/narrowed integration scope, or the data "
            "source is no longer shared with it), not an empty table. Fix access, then "
            "re-run to establish the baseline.")

    if prev_count > 0 and curr_count <= prev_count * COLLAPSE_FLOOR_RATIO:
        return False, (
            "REFUSED to persist snapshot: row count collapsed %d -> %d (at or below %.0f%% "
            "of prior). Prior baseline kept. Check the Notion integration's access before "
            "trusting this run's diff."
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
        pages = pull_all(ACQ_PIPELINE_DS_ID, token)
    else:
        pages = _pages
    curr = build_snapshot(pages, as_of, ACQ_PIPELINE_DS_ID)
    prev, load_warning = load_prev()
    d = diff_snapshots(prev, curr)
    warnings = list(d.get("warnings", []))
    warnings.extend(detect_truncation(pages))
    warnings.extend(detect_missing_exclusions(pages))
    if load_warning:
        warnings.append(load_warning)

    persisted, persist_note = decide_persist(prev, curr["count"], load_warning)
    if persist_note:
        warnings.append(persist_note)
    if persisted:
        atomic_write_json(LATEST, curr)
        atomic_write_json(os.path.join(STATE_DIR, "acquisition-pipeline-%s.json" % as_of), curr)

    # A refused run establishes NOTHING. `baseline` depends on `persisted`, not merely on
    # `prev is None` -- see property_register_snapshot_diff.py for the exact defect class
    # (a refused run printing "Baseline established" and reporting baseline:true, letting a
    # digest report an access outage as a clean no-edits day) this guards against.
    baseline = prev is None and persisted

    # human summary
    if not persisted:
        print("REFUSED: no snapshot persisted for %s (%d rows pulled). Prior state kept, "
              "NO baseline established. See WARNING below." % (as_of, curr["count"]))
    elif baseline:
        print("Baseline established: %d rows snapshotted for %s (no prior snapshot to diff)."
              % (curr["count"], as_of))
    else:
        print("Acquisition Pipeline Tracker diff %s -> %s: %d added, %d removed, %d changed, "
              "%d unchanged (of %d)." % (
                  d["prev_as_of"], as_of, len(d["added"]), len(d["removed"]), len(d["changed"]),
                  d["unchanged"], curr["count"]))
        for c in d["changed"][:50]:
            flds = ", ".join("%s: %s -> %s" % (x["field"], x["old"], x["new"]) for x in c["changes"][:6])
            print("   CHANGED  %s  [%s]" % (c["title"], flds))
        for a in d["added"][:50]:
            print("   ADDED    %s" % a["title"])
        for r in d["removed"][:50]:
            print("   REMOVED  %s" % r["title"])
    # Warnings MUST reach the caller -- dropping them here made the bulk-field guard dead in
    # production in the Tenant DB script's early history (it only ever fired via --selftest);
    # every sibling since has carried the fix forward from the start.
    for w in warnings:
        print("   WARNING  %s" % w)
    result = {"baseline": baseline, "prev_as_of": d["prev_as_of"], "curr_as_of": as_of,
              "count": curr["count"], "added": d["added"], "removed": d["removed"],
              "changed": d["changed"], "unchanged": d["unchanged"],
              "warnings": warnings, "persisted": persisted}
    print("RESULT_JSON=" + json.dumps(result, ensure_ascii=True))  # ASCII-safe for any downstream pipe
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
        # losing that day's audit trail. Fail loudly instead.
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
