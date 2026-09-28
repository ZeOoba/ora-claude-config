---
name: notion-quota-fallback
description: Use this skill whenever a Notion query fails with a "Query Data Source" usage-limit / quota error, or whenever you already know the workspace's SQL-mode Notion query quota is exhausted and still need to query, filter, or count rows in a Notion database. Also consult it proactively before running any large or repeated SQL-mode notion-query-data-sources call against a big database (a rent roll, tenant database, deal pipeline, etc.) in a session that has already burned meaningful quota, since hitting the limit mid-task stalls the work. Covers the view-mode + pagination fallback (no tool-specific quota) and a bundled script to aggregate/filter the paginated results without re-querying. Also documents a secondary, unrelated caveat about the Notion UI's "+Filter" control appearing to hang in browser-automation sessions — consult that section if a multi-condition Notion database filter isn't opening in the browser.
---

# Notion Quota Fallback

## Why this exists

`notion-query-data-sources` in **SQL mode** (`mode: "sql"`, or the default when `mode` is omitted) is gated by a **shared, workspace-wide** usage quota. Once it's exhausted, every SQL-mode call fails outright:

> "Your workspace has reached the usage limit for Query Data Source."

This is not a per-tool-call retry-able error and not specific to one database — it blocks *every* SQL-mode query across the whole workspace until the quota resets. Don't retry the same SQL query hoping it clears; switch modes instead.

The same tool's **view mode** (`mode: "view"`) is *not* subject to this quota — per the tool's own description, "View mode is available without a tool-specific quota on every plan." This skill exists because view mode has a different shape (it runs an existing database *view*, not arbitrary SQL) and comes with its own friction — pagination, and result payloads that are too large to read inline — that are easy to fumble the first time. This was worked out and validated end-to-end during a 2026-08-16 Tenant Database backfill (298 rows, 3 pages, correctly identified 32 rows needing an update, then confirmed 0 remaining after the fix).

## Recognizing when to use this

Trigger this skill when either is true:
- A `notion-query-data-sources` SQL-mode call just failed with a usage-limit / quota error.
- You already know (from this session or the user) that the SQL quota is exhausted, and you still need to answer a question that would normally be a SQL query — "which rows have X blank", "how many rows match Y", "get me the full Tenant Database filtered by Z".

If the SQL quota isn't exhausted, just use SQL mode normally — it's simpler and this fallback isn't needed.

## Procedure

### 1. Switch to view mode, paginated

Call the same tool with `mode: "view"` instead of `mode: "sql"`. You need a `view_url` — a database view URL containing a `?v=<view-id>` (get this from `notion-fetch` on the database, or from the URL bar if you navigated there in the browser). SQL's `WHERE` clause has no equivalent here — you get back whatever rows the *view* itself would show (its own filters/sorts already baked in), so pick or create a view with the scope you need, or just query the least-filtered view and filter client-side afterward (Step 3).

```
mcp__Notion__notion-query-data-sources({
  "data": {
    "mode": "view",
    "view_url": "https://app.notion.com/p/<page-id>?v=<view-id>",
    "page_size": 100
  }
})
```

The response includes `has_more` and `next_cursor`. **Loop**, passing each `next_cursor` back in as `start_cursor` on the next call, until a response comes back with `has_more: false`. There's no reliable way to know the total row count up front — just keep going until it says stop. (Reference point: a 298-row database took 3 pages of 100/100/98.)

```
mcp__Notion__notion-query-data-sources({
  "data": {
    "mode": "view",
    "view_url": "<same view_url>",
    "page_size": 100,
    "start_cursor": "<next_cursor from the previous response>"
  }
})
```

### 2. Expect large results to land in a file, not inline

Each page of ~100 rows across a wide database (30-40+ properties per row) routinely exceeds the tool's inline-display token limit. When that happens the response is written to a `tool-results/*.txt` file and the tool result tells you the path. That's expected — don't treat it as an error. The file is valid JSON, but as a **single line**, so line-based reading (`Read` with offset/limit, `head`, `grep -n`) won't chunk it usefully. Don't try to eyeball-slice it by character range either — go straight to Step 3.

### 3. Aggregate and filter with the bundled script

Use `scripts/notion_view_query_aggregate.py` (bundled with this skill) instead of writing ad-hoc Python for every query. Point it at the tool-result files from Step 1-2 (in any order — it merges and de-dupes by row URL) and it answers the SQL-style question you actually had:

```bash
python3 scripts/notion_view_query_aggregate.py \
  --files tool-results/query-page1.txt tool-results/query-page2.txt tool-results/query-page3.txt \
  --equals "Row Retired" "__NO__" \
  --missing "Market Rent PSF"
```

or, if every relevant page landed in the same directory:

```bash
python3 scripts/notion_view_query_aggregate.py --dir tool-results/
```

Filter flags:
- `--equals FIELD VALUE` — field must equal VALUE exactly (checkboxes are the strings `__YES__` / `__NO__`)
- `--contains FIELD SUBSTRING` — field must contain SUBSTRING
- `--missing FIELD` — field must be **absent** from the row (Notion omits blank properties entirely rather than sending null/empty string — this is the correct way to test "is this blank")
- `--present FIELD` — field must be present in the row

It prints one line per matching row (`<Tenant Name> | <Property Address> | <url>` by default — change what's printed with `--field`) and a final count. It exits non-zero on a parse failure, so it's safe to use as a verification gate (e.g., "this should print 0 matching rows when we're done").

It also works as a library if you need something the CLI doesn't cover:

```python
from notion_view_query_aggregate import load_pages, aggregate, apply_filters

pages = load_pages(["page1.txt", "page2.txt", "page3.txt"])
rows = aggregate(pages)  # dict keyed by row url, de-duped
matches = apply_filters(rows, equals=[("Row Retired", "__NO__")], missing=["Market Rent PSF"])
```

Full interface details are in the script's own docstring (`python3 scripts/notion_view_query_aggregate.py --help`).

### 4. If the task needs individual row writes, use `notion-update-page`

Once you've identified the target rows via Step 3, write to them directly with `notion-update-page` (`command: "update_properties"`), one call per page, rather than trying to do a UI bulk-edit while the SQL quota is down. This is more reliable than browser automation for a Notion database view anyway (see the caveat below), and it's what actually resolved the source backfill this skill was built from — 31 individual `notion-update-page` calls driven off a Step 3 filtered list.

## Secondary caveat: Notion's "+Filter" control in browser automation

Unrelated to the quota issue, but discovered in the same session: the Notion database UI's **"+Filter"** control — used to add a *second* AND-condition to an existing filter — can appear completely unresponsive when clicked via browser automation (`mcp__claude-in-chrome__*`), across every interaction strategy (direct coordinates, ref-based clicks, double-click).

This was tested and root-caused: it is **not a genuine Notion product bug**. A fresh full-page `navigate` (reload) to the same view URL, followed by a single click on "+Filter" as the very first interaction on that page load, opened the property picker correctly and the full add-filter flow worked end-to-end. The failure is automation-session state — stale DOM/interaction references accumulated across a long-lived browser session (compounded, in the observed case, by a workspace "free blocks" banner shifting the page layout mid-session).

If you hit this: reload the page fresh before retrying the filter click. If it still fails after a clean reload, stop fighting the UI — fall back to Step 1-4 above (view-mode query + the aggregation script + `notion-update-page`) instead of burning cycles on browser automation for something the API path handles more reliably anyway.
