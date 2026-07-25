---
name: pipeline-tracker-last-edited-time-stall
description: "Acquisition Pipeline Tracker's Last Updated (last_edited_time) does not advance on some rows despite live edits — row/path-specific, not index lag; use Last Activity instead. Open diagnosis."
metadata: 
  node_type: memory
  type: project
  originSessionId: 52570977-9aa6-4d15-a7f3-3e2b2e789196
  modified: 2026-07-24T20:20:26.430Z
---

# Acquisition Pipeline Tracker — `last_edited_time` stalls on some rows (OPEN)

Confirmed 2026-07-24 while fixing the Stale Deal Watch view (task `ora-daily-brief-followup-0724`). Flagged, deliberately **not fixed** in that pass.

**Observation (Notion Acquisition Pipeline Tracker, `bcfe4a03-7e61-4ac1-a0bb-c44174fa138b`):**
- **1333 Research Road** — `Last Updated = 2026-03-22 20:58:00Z`, *identical to the row's creation timestamp*, despite a Next Action rewritten 2026-07-24. It has never advanced past creation.
- **511 Industrial Mile Road** — `2026-06-09` against a 2026-07-17 broker update.
- **808 Rhoads Avenue** — `2026-06-22` against a 2026-07-24 flood/zoning DD pass.
- **5515 Catfish Court** — `2026-07-15` against a 2026-07-24 Gabriel position note.

**Why this is not simple index lag:** other rows *do* advance — 1150 Newark Rd, 4331 Brockton Dr and 2196 Port Sheldon St all share a clean `2026-07-21 16:09:31Z` bulk-write stamp, and 250 NW 10th / 5515 Catfish share `2026-07-15 13:56:10Z`. So the property updates on some write paths and not others. The stall correlates with rows edited on 2026-07-24, but 1333 Research Road's never-advanced-since-creation value rules out a pure recency/caching explanation. Root cause is **unidentified** — most likely an API write path that mutates property values without touching page-level `last_edited_time`.

**How to apply:** treat `Last Updated` on this database as **unreliable**. Any staleness view, aging SLA, or nudge automation must key off the manually-maintained **`Last Activity`** date property instead, which is being kept current correctly. The Stale Deal Watch view was repointed accordingly on 2026-07-24. Before building anything new on `last_edited_time` in any ORA Notion database, spot-check two or three rows against known recent edits first.

Related: [[reference_notion_view_dsl_formula_filter_bug]] (the same view carried a separate silent-zero-match filter bug, fixed the same day), [[reference_notion_query_requires_dashed_uuid]].
