---
name: reference-tenant-db-cache-and-notion-quota-myth
description: "Notion query quota is a mistaken diagnosis (real cause: gated MCP tool, not a Notion plan limit); a daily Tenant DB cache already exists via ora-pm-ledger but no other skill reads it yet"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 156b1fa9-1de0-442e-aacf-4c9ef378327f
  modified: 2026-07-21T16:40:27.918Z
---

# The "Notion query quota" isn't real — and a daily Tenant DB cache already exists

**The finding, corrected 2026-07-21:** a tenant-DB brief this session reported "Property, Suite/Unit,
SF, Monthly Rent, Rent PSF, Renewal Option Terms, Required Notice Period — unavailable this cycle
(Notion source blocked)" and recommended upgrading the Notion plan or building a cache. Both premises
were wrong.

## 1. The quota is an MCP-tool gate, not a Notion plan limit

Established across `ora-pm-ledger` runs 2026-07-16 through 2026-07-20 (see those sessions via
`search_session_transcripts` for "DEFECT 2" / "mcp_tool_upsell"): the `entitlement_required` error
only fires from the **`notion-query-data-sources` MCP tool in SQL mode**
(`tool_error_code: entitlement_required`, `source: mcp_tool_upsell`, `product: business`). Notion's
own REST API (what `notion-search`, `notion-fetch`, and direct `/databases/{id}/query` REST calls use)
has no such limit. **Do not recommend a Notion plan upgrade for this** — it fixes nothing, since the
gate is on the MCP connector's tool tier, not the workspace's data allowance.

**How to apply:** if a query hits `entitlement_required` from `query_data_sources`, don't retry it and
don't treat it as "Notion is out of quota." Use `notion-search`/`notion-fetch` instead, or read the
cache below. [[open-items-tracker]] OI-009's Northwood incident (2026-07-17) describes a wait-and-retry
that "worked" — that was likely the quota actually resetting on a *different*, session-level gate, not
proof the workspace-level story is correct. Don't generalize that incident's framing.

## 2. A daily Tenant DB cache already exists

`ora-pm-ledger` (CC/MCP, `0 18 * * *`) built and verified `tenant_db_snapshot_diff.py`
(`~\.claude\scheduled-tasks\ora-pm-ledger\tenant_db_snapshot_diff.py`) on 2026-07-20. It does a full
REST pull of the Notion Tenant DB (`/databases/8dbbaec0…/query` @ API version `2022-06-28`, paginated),
fingerprints each row (excluding volatile `created_time`/`last_edited_time` metadata), and diffs
against the prior snapshot. Output lands at
`~\.claude\scheduled-tasks\ora-pm-ledger\state\tenant-db-latest.json` — verified against real data:
296 rows, 0 false positives on a same-day re-run.

**This snapshot already contains every field reported "blocked" above** — confirmed by direct read
2026-07-21: `Property Address`, `Suite / Unit`, `SF`, `Monthly Rent`, `Rent PSF (Annual)`,
`Renewal Option Terms`, `Required Notice Period (Days)`, plus ~60 more columns per row, keyed by
Notion page ID. As-of date is whatever `ora-pm-ledger` last ran (check `data["as_of"]` — typically
yesterday relative to any given day, refreshed nightly at 18:00).

**The gap:** this cache was built for `ora-pm-ledger`'s own edit-detection purposes. No other skill
(`lease-renewal-pipeline`, `tenant-intelligence`, `rent-roll-qc`, `daily-brief`, `exception-detection`,
or any ad hoc "tenant DB brief") is wired to read it — they all still live-query Notion per-run and can
still hit the MCP-tool gate above. **Before recommending a new cache-building project, check this file
first** — reading it directly (Python `json.load`, watch for the cp1252 stdout gotcha on `⛔` titles —
use `PYTHONIOENCODING=utf-8`) is usually all that's needed.

## 3. Related, still-open gaps (as of 2026-07-21)

- `exception-detection` Category 4 ("HubSpot-Notion deal stage mismatch") is scoped to acquisition
  pipeline deals only — it does not cover tenant-status conflicts (Notion tenant archived/duplicate vs.
  an open HubSpot "Lease Renewal" deal, or a HubSpot Lease Renewal deal past its closedate and never
  advanced past `appointmentscheduled`). Extending this category is a scoped SKILL.md edit, not a
  rebuild — check `ora-skills` single-writer state first.
- All 50 HubSpot "Lease Renewal" deals were bulk-created 2026-03-27 and remain in stage
  `appointmentscheduled` regardless of whether the closedate has passed — nothing in the current
  workflow ever advances deal stage on actual renewal/vacate outcomes. 14 have closedates already past
  as of 2026-07-21; 12 of those untouched since creation. This is a stage-hygiene gap, not a missing-data
  gap — do not conflate the two when triaging future "stale HubSpot deal" flags.
- No monthly HubSpot→Notion reconciliation task exists yet. Given #2 above, one is now cheap to build:
  cross-reference the existing `ora-pm-ledger` cache against a HubSpot `Lease Renewal` deal pull
  (`search_crm_objects` on `deals`, query `"Lease Renewal"`) rather than building fresh infrastructure.

Related: [[project_tenant_db_no_sync_rootcause]] (root cause: Notion demoted from write-source
2026-04-29, no sync ever replaced it) · [[reference_tenant_db_completeness_gap]] (⛔ ARCHIVED prefix is
a deliberate soft-archive convention, not a bug) · [[open-items-tracker]]
