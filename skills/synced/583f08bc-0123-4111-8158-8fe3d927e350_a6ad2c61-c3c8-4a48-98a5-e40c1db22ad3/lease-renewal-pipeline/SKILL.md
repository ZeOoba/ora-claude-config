---
name: lease-renewal-pipeline
description: Flag upcoming lease expirations across the portfolio and route renewal-letter drafting through document-assembly. Use when the user mentions upcoming lease expirations, renewal pipeline, which leases are expiring, renewal tracking, expiring leases this quarter, or asks to check/run the lease renewal cycle. Does not itself draft a letter or score tenant risk — see document-assembly and tenant-intelligence. v1.2
user-invocable: true
allowed-tools: Read Glob Grep Write WebSearch WebFetch mcp__c5f4869f-7d3a-4472-a66a-8e61315feb51__notion-search mcp__c5f4869f-7d3a-4472-a66a-8e61315feb51__notion-fetch mcp__a3e380ce-2ea9-4b42-92d9-37c588a4b760__search_crm_objects mcp__c0ea3c01-b8f1-4371-aa06-08a1449f59fc__outlook_email_search
---

## Instructions

Review and manage upcoming lease expirations across the Oxford portfolio.

### Default behavior (no arguments)
Show all leases expiring in the next 6 months.

### With $ARGUMENTS
- A property name → filter to that property
- A timeframe (e.g., "next 90 days", "Q3 2026") → filter to that window
- A tenant name → show that tenant's lease details and renewal status

### Steps

1. **Gather lease data:**
   - **Canonical source:** Notion Tenant Database, queried via the **Notion MCP** (`notion-fetch` / `notion-search`). The former Composio query path (`NOTION_QUERY_DATABASE_WITH_FILTER` against the wrapper ID, with the prefixed-cursor workaround in `references/notion_paginator.py`) is **RETIRED 2026-06-11** — the Composio connector was removed; do not route through it. The paginator is archived under `_archive/lease-renewal-pipeline_pre-notionmcp_2026-06-11/` for history only.
   - **ID routing:** `notion-fetch` and schema introspection → **data source ID** `b12f4cfd-a995-4755-8341-6435ae8173b4` (`collection://b12f4cfd-a995-4755-8341-6435ae8173b4`). Calling `notion-fetch` on the wrapper ID returns `validation_error: "Aggregation property not found in data source"` — a misleading routing quirk, not a data problem (resolved 2026-04-27; see Database ID Map in Knowledge Base). The **database wrapper ID** `8dbbaec0-611a-4617-be07-6a77d0d0307a` remains valid only for browser URLs (`notion.so/{id}`).
   - **Full portfolio scan:** `notion-fetch` on the data source ID, paginating until exhausted; filter client-side on Lease Status. For small targeted lookups (single tenant or property), `notion-search` is sufficient.
   - **Active scope:** Lease Status ∈ {Active, Month-to-Month, Notice Given, Expired}. Exclude Vacant, blank-status stubs, and rows whose Tenant Name contains `⛔` or `DUPLICATE`.
   - **Cross-reference** with rent roll files at `OneDrive\Claude_Workspace\01_Cowork_OS\Cowork_OS_Workspace\` (glob `*rent roll*`, `*lease*`) only when Notion fields are sparse for a given tenant.

2. **Build the expiration pipeline:**
   - Sort by expiration date (soonest first)
   - For each lease show: tenant, property, unit, SF, current rent, rent/SF, lease start, lease end, renewal options (if any), notice period

3. **Flag urgency levels:**
   - **CRITICAL** (red): expires within 60 days, no renewal signed
   - **ACTION NEEDED** (yellow): expires within 120 days, no renewal activity
   - **MONITOR** (green): expires within 180 days, renewal option exists or discussions underway

4. **For CRITICAL and ACTION NEEDED tenants:**
   - Check Outlook/HubSpot for recent communication with the tenant
   - Determine the terms to propose: new term (3-5 years), rent bump (3% annual or market adjustment), key lease terms to update
   - **Renewal letters are standalone formal documents, not email bodies — per CLAUDE.md's Comms drafting tie-break, route drafting to the `document-assembly` skill's templates, never draft letter prose directly in this skill or hand off to `tenant-email`.** Pass `document-assembly` the tenant name, property, the proposed terms above, and the urgency tier.
   - Save the resulting draft to the appropriate property folder

5. **Summary output:**
   - Total leases expiring in window
   - Occupied SF at risk
   - Revenue at risk (annual)
   - Recommended actions prioritized by urgency

### Output Format
Markdown table for the pipeline, followed by draft renewal letters for any critical expirations.

## Changelog

- **v1.2 (2026-09-07):** ORA Automation Audit R23 follow-up — this skill had ZERO trigger phrases in its description, so it could never win a manual, name-based routing decision against tenant-intelligence or document-assembly; only its scheduled-task cron ever ran it. Added trigger vocabulary ("upcoming lease expirations", "renewal pipeline", "expiring leases this quarter", etc.) plus explicit deferrals for drafting (document-assembly) and risk scoring (tenant-intelligence), so it can. No detection logic, cadence, or handoff behavior changed.
- **v1.1 (2026-08-14):** Fixed a live skill-routing collision (ORA Automation Audit Revision 8, `ora-setup-audit`) — Step 4 previously drafted renewal-letter prose directly with no format specified and no reference to CLAUDE.md's ratified comms-drafting tie-break, a silent third path around `document-assembly`/`tenant-email`. Now determines terms only and hands drafting to `document-assembly`, consistent with the tie-break's "tenant-directed formal letters (renewal offers, notices) route to document-assembly" rule. No change to lease-data sourcing or urgency logic.
