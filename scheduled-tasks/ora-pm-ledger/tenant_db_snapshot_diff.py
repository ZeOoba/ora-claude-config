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
import argparse, datetime, hashlib, json, os, sys, urllib.request, urllib.error

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
    """{prop_name: normalized_value} excluding skipped metadata/None."""
    out = {}
    for name, p in props.items():
        v = norm_prop(p)
        if v is not None:
            out[name] = v
    return out


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
        elif p[pid]["hash"] != row["hash"]:
            changes = []
            pf, cf = p[pid].get("fields", {}), row.get("fields", {})
            for k in sorted(set(pf) | set(cf)):
                if pf.get(k) != cf.get(k):
                    changes.append({"field": k, "old": pf.get(k, "<absent>"), "new": cf.get(k, "<absent>")})
            changed.append({"id": pid, "title": row["title"], "changes": changes})
    for pid, row in p.items():
        if pid not in c:
            removed.append({"id": pid, "title": row["title"]})
    return {
        "prev_as_of": (prev or {}).get("as_of"),
        "curr_as_of": curr.get("as_of"),
        "prev_count": (prev or {}).get("count", 0),
        "curr_count": curr.get("count", 0),
        "added": added,
        "removed": removed,
        "changed": changed,
        "unchanged": curr.get("count", 0) - len(added) - len(changed),
    }


# ---------- REST pull ----------
def load_token():
    with open(ENV_PATH, encoding="utf-8") as f:
        for line in f:
            if line.startswith("NOTION_TOKEN"):
                return line.split("=", 1)[1].strip().strip('"')
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
        with urllib.request.urlopen(req, timeout=60) as r:
            d = json.load(r)
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
    print("SELFTEST:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


# ---------- run ----------
def run(as_of):
    os.makedirs(STATE_DIR, exist_ok=True)
    token = load_token()
    pages = pull_all(TENANT_DB_ID, token)
    curr = build_snapshot(pages, as_of, TENANT_DB_ID)
    prev = None
    if os.path.exists(LATEST):
        with open(LATEST, encoding="utf-8") as f:
            prev = json.load(f)
    d = diff_snapshots(prev, curr)
    baseline = prev is None
    # persist
    with open(LATEST, "w", encoding="utf-8") as f:
        json.dump(curr, f, ensure_ascii=False)
    with open(os.path.join(STATE_DIR, "tenant-db-%s.json" % as_of), "w", encoding="utf-8") as f:
        json.dump(curr, f, ensure_ascii=False)
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
    result = {"baseline": baseline, "prev_as_of": d["prev_as_of"], "curr_as_of": as_of,
              "count": curr["count"], "added": d["added"], "removed": d["removed"],
              "changed": d["changed"], "unchanged": d["unchanged"]}
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
