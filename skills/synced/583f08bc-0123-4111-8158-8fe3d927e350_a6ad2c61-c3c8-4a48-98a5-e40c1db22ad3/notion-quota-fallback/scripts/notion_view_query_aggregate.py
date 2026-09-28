#!/usr/bin/env python3
"""
notion_view_query_aggregate.py

Reusable helper for the "SQL quota exhausted -> view-mode pagination" fallback
pattern discovered during the 2026-08-16 Tenant Database Market Rent PSF
backfill (Cowork session).

WHY THIS EXISTS
----------------
mcp__Notion__notion-query-data-sources in SQL mode is gated by a shared
workspace-wide "Query Data Source" usage quota. When that quota is exhausted,
SQL-mode calls fail outright with:
    "Your workspace has reached the usage limit for Query Data Source."

view mode on the SAME tool is NOT subject to that tool-specific quota (per the
tool's own description: "View mode is available without a tool-specific quota
on every plan"). view mode executes a *view's* existing filters/sorts and
supports pagination via start_cursor / next_cursor, but:
  1. It only accepts a view_url, not an arbitrary SQL WHERE clause -- so you
     get back whatever rows the *view* returns (often the whole data source,
     not just what you'd visually filtered client-side but never saved).
  2. Individual pages of results routinely exceed the tool's inline-display
     token limit (100 rows x ~40 properties easily runs 300k+ characters) and
     get written to a tool-results/*.txt file instead of returned inline.
  3. Each row of the JSON is one line, too long for Read's offset/limit
     chunking -- you need a real JSON parser (this script), not line-based
     tools.

HOW TO USE THIS PATTERN
------------------------
1. Call the tool once per page:

     mcp__Notion__notion-query-data-sources({
       "data": {
         "mode": "view",
         "view_url": "<the database view URL, with ?v=<view-id>>",
         "page_size": 100,
         "start_cursor": "<next_cursor from the previous page, omit on page 1>"
       }
     })

   Each call either returns inline (rare, if small) or reports:
     "Output has been saved to /root/.claude/projects/.../tool-results/<file>.txt"

2. Repeat, feeding each response's "next_cursor" back in as "start_cursor",
   until a response comes back with "has_more": false. There is no reliable
   way to know the total row count in advance -- just loop until has_more
   is false. (In the 2026-08-16 run: 298 total rows -> 3 pages of 100/100/98.)

3. Once you have the list of tool-results file paths for that query, feed them
   to this script's aggregate() function (or run this file directly) to merge,
   dedupe by `url`, and filter/query them like a small in-memory table --
   without ever re-touching the SQL-mode quota.

CLI USAGE
---------
    python3 notion_view_query_aggregate.py \\
        --files tool-results/query-page1.txt tool-results/query-page2.txt \\
        --contains "Property Address" "Salisbury" \\
        --equals "Row Retired" "__NO__" \\
        --missing "Market Rent PSF"

    # Or just point it at a directory and it will glob every
    # mcp-Notion-notion-query-data-sources-*.txt file in it:
    python3 notion_view_query_aggregate.py --dir tool-results/

Prints one line per matching row: "<Tenant Name> | <Property Address> | <url>"
and a final count. Exits non-zero if any input file fails to parse, so it's
safe to use in a verification step (e.g. "count should be 0").

AS A LIBRARY
-------------
    from notion_view_query_aggregate import load_pages, aggregate

    rows = aggregate(load_pages(["page1.txt", "page2.txt"]))
    salisbury_blank = [
        r for r in rows.values()
        if "Salisbury" in str(r.get("Property Address", ""))
        and r.get("Row Retired") == "__NO__"
        and "Market Rent PSF" not in r
    ]
"""

import argparse
import glob
import json
import os
import sys


def load_pages(paths):
    """Load one or more raw tool-result JSON files (each the full response
    body of a single notion-query-data-sources view-mode call)."""
    pages = []
    for p in paths:
        with open(p, "r") as f:
            data = json.load(f)
        if "results" not in data:
            raise ValueError(f"{p}: no 'results' key -- is this a view-mode query result?")
        pages.append((p, data))
    return pages


def aggregate(pages):
    """Merge every row across pages into a single dict keyed by row `url`
    (Notion page URLs are stable and unique, so this also de-dupes rows that
    show up in more than one page due to overlapping cursors)."""
    merged = {}
    for path, data in pages:
        for row in data["results"]:
            url = row.get("url", path + "#" + str(len(merged)))
            merged[url] = row
    return merged


def summarize_pagination(pages):
    """Sanity-check: warn if the LAST page (by call order given) doesn't have
    has_more == False, since that means the caller stopped paginating early
    and this aggregate is INCOMPLETE."""
    if not pages:
        return
    _, last = pages[-1]
    if last.get("has_more"):
        print(
            f"WARNING: last page provided still has has_more=true "
            f"(next_cursor={last.get('next_cursor')!r}). "
            f"This aggregate may be missing rows -- fetch more pages.",
            file=sys.stderr,
        )


def apply_filters(rows, contains=None, equals=None, missing=None, present=None):
    """rows: dict of url -> row. Returns filtered dict.
    contains: list of (field, substring) -- field must contain substring (str match)
    equals:   list of (field, value)     -- field must equal value exactly (string compare)
    missing:  list of field names        -- field must be ABSENT from the row (Notion
                                             omits blank properties entirely rather than
                                             sending null/empty-string)
    present:  list of field names        -- field must be present in the row
    """
    contains = contains or []
    equals = equals or []
    missing = missing or []
    present = present or []

    def keep(row):
        for field, sub in contains:
            if sub not in str(row.get(field, "")):
                return False
        for field, val in equals:
            if row.get(field) != val:
                return False
        for field in missing:
            if field in row:
                return False
        for field in present:
            if field not in row:
                return False
        return True

    return {url: row for url, row in rows.items() if keep(row)}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--files", nargs="+", help="Explicit list of tool-result JSON files, in page order")
    src.add_argument("--dir", help="Directory to glob for mcp-Notion-notion-query-data-sources-*.txt files")
    ap.add_argument("--contains", nargs=2, action="append", default=[], metavar=("FIELD", "SUBSTRING"))
    ap.add_argument("--equals", nargs=2, action="append", default=[], metavar=("FIELD", "VALUE"))
    ap.add_argument("--missing", nargs="+", default=[], metavar="FIELD")
    ap.add_argument("--present", nargs="+", default=[], metavar="FIELD")
    ap.add_argument("--field", default="Tenant Name", help="Field to print per matching row (default: Tenant Name)")
    args = ap.parse_args()

    if args.dir:
        paths = sorted(glob.glob(os.path.join(args.dir, "mcp-Notion-notion-query-data-sources-*.txt")))
        if not paths:
            print(f"No mcp-Notion-notion-query-data-sources-*.txt files found in {args.dir}", file=sys.stderr)
            sys.exit(1)
    else:
        paths = args.files

    pages = load_pages(paths)
    summarize_pagination(pages)
    rows = aggregate(pages)
    filtered = apply_filters(rows, contains=args.contains, equals=args.equals, missing=args.missing, present=args.present)

    for row in filtered.values():
        print(f"{row.get(args.field, '<no ' + args.field + '>')} | {row.get('Property Address', '')} | {row.get('url', '')}")

    print(f"\n{len(filtered)} matching row(s) out of {len(rows)} total unique row(s) across {len(pages)} page(s).")


if __name__ == "__main__":
    main()
