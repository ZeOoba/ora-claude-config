---
name: tenant-db-renewal-watch-view
description: "Added Months to Expiry formula + Renewal Watch (<=90 days, excl. retired/vacant/expired) saved view to the Notion Tenant DB for the daily 4b cross-check against portfolio.json — CLOSED 2026-07-22, refresh wired + diagnostic views trashed"
metadata: 
  node_type: memory
  type: project
  originSessionId: 86ec9edd-63ac-49e3-a01a-f5729bf946ca
  modified: 2026-07-22T14:03:32.713Z
---

Built 2026-07-22 per Gabriel's ask: give the daily 4b cross-check one canonical Notion surface to reconcile against `portfolio.json`, collapsing the row-misalignment error class behind the 2026-07-16 incident (J&R Enterprises had a null Lease Expiration silently filled from the portfolio.json snapshot).

**Delivered** (Tenant DB, data source `b12f4cfd-a995-4755-8341-6435ae8173b4`):
- New FORMULA property **"Months to Expiry"** = `dateBetween(prop("Lease Expiration"), now(), "months")`. The schema already had "Months Remaining" and "Days to Expiration" (also formulas keyed off Lease Expiration) — Gabriel chose to keep those and reuse them for display, but see the pivot below for why the new field's *filter* couldn't actually run through them.
- Saved view **"Renewal Watch — ≤90 Days (as of 2026-07-22)"** (`view://3a56ecd8-9e59-819c-8333-000c3d9a8627`), filtered on the native `Lease Expiration` date field (2026-07-22 to 2026-10-20 inclusive) AND `Lease Status` not in (Vacant, Expired) AND `Row Retired` = false.

**Why the filter ended up on the raw date field, not a formula column:** confirmed via direct testing that this Notion MCP's view DSL cannot filter formula-type properties correctly — see [reference_notion_view_dsl_formula_filter_bug.md](reference_notion_view_dsl_formula_filter_bug.md). Every attempt (numeric `<=`, checkbox `=true`) silently built a broken rollup-style filter that matched all rows. Pivoted to filtering the underlying `Lease Expiration` date directly, which works correctly but only with an absolute date value (relative offsets like `+90d` are silently accepted and non-functional, also documented in that reference file).

**Why `Row Retired = false` matters more than the Lease Status exclusion:** the naive date-only filter surfaced 31 rows, several tagged "⛔ ARCHIVED 2026-07-12" with `Row Retired = __YES__` — including the exact J&R Enterprises row from the 2026-07-16 incident. Excluding those (Gabriel confirmed via decision question: exclude Vacant + Expired from Lease Status, and Row Retired is the real "not Terminated" proxy since the schema has no literal Terminated value) brought the view down to 5 clean rows: J&R Enterprises, CJ's Tint Shop, Columbus Suburban Construction, Hoodz of Delmarva, Sky Shield.

**Known limitation, now CLOSED 2026-07-22:** the view's date bounds were a frozen absolute range that would go stale. Fixed by adding a new step 1 to `ora-lease-expiration-brief`'s SKILL.md (`OneDrive…\Documents\Claude\Scheduled\ora-lease-expiration-brief\SKILL.md` — path is NOT git-tracked, so the ora-skills single-writer check was N/A here): each Monday 10:45am run now recomputes today/today+90 as absolute ISO literals and calls Notion `update_view` on `view://3a56ecd8-9e59-819c-8333-000c3d9a8627` (CLEAR FILTER; FILTER Lease Expiration >= today AND <= today+90 AND Lease Status != Vacant AND != Expired AND Row Retired = false), with an explicit callout not to filter formula properties or use relative-date syntax (both silently no-op per [reference_notion_view_dsl_formula_filter_bug.md](reference_notion_view_dsl_formula_filter_bug.md)).

**Cleanup note — DONE 2026-07-22:** the 3 "🗑️ DELETE ME — Claude diagnostic view (safe to remove)" throwaway views were manually trashed via Claude in Chrome (Notion has no programmatic view-delete tool) — confirmed via the view-search box returning "No results" for "DELETE ME" afterward, view count dropped 43→40.
