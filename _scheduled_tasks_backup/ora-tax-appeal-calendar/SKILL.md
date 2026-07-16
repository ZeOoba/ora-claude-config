---
name: ora-tax-appeal-calendar
description: Quarterly property tax appeal calendar (1st of Jan/Apr/Jul/Oct, 9:30 AM) — county appeal windows are seasonal; retimed from monthly per 2026-04-28 audit recommendation IV.F. For each of 27 ORA properties, compares assessed value × cap rate to NOI-implied valuation, surfaces appeal candidates and county-specific deadlines, emails Gabriel + Eric. Composio Outlook pin added 2026-05-08.
---

**[COMPOSIO MIGRATION 2026-05-08 — Rube EOL bridge]** All MCP routing on this task is pinned to the native Composio Platform connector (`mcp__8a611864-5cda-497f-baf9-6d3c02ab3404__COMPOSIO_*`), NOT the legacy Rube namespace (`mcp__d6315173-234c-4e6c-bea7-7f5e15d2bde5__RUBE_*`). Tool slugs (`OUTLOOK_SEND_EMAIL`, `OUTLOOK_CREATE_DRAFT`, `OUTLOOK_CREATE_ME_EVENT`, `HUBSPOT_*`, etc.) are byte-identical between stacks; only the MCP server prefix changes. Use the Composio path for Outlook (mail + calendar) and HubSpot. ORA does not use Google Workspace — no GCal/GSheets routing applies. (Notion writes can continue to use the native `mcp__c5f4869f-...__notion-*` MCP; QuickBooks reads can continue to use the native `mcp__52fa80c0-...` MCP.)

You are running the ORA Monthly Property Tax Appeal Calendar.

OBJECTIVE
Identify properties where assessed value materially exceeds income-approach valuation AND where the county appeal deadline is within 90 days.

EXECUTION
1. Invoke tax-appeal skill in BATCH mode. For each of 27 ORA properties:
   a. Pull current assessed value from Notion Property database (or from prior tax bill in SharePoint).
   b. Pull TTM NOI from QuickBooks (Profit & Loss by class, last 12 months).
   c. Apply market cap rate floor by submarket per acquisition-underwriting skill guidance.
   d. Compute Implied Value = NOI / cap rate. Compute Overassessment Ratio = Assessed / Implied.
2. Pull county-by-county appeal deadlines (cached in Notion Knowledge Base; refresh annually). For OH/MD/IN/WI/MO/KS/TN counties, note next deadline.
3. APPEAL CANDIDATE = (Overassessment Ratio ≥ 1.10) AND (deadline within 90 days).
4. Build report in ORA Institutional Style: Property | County | Assessed | TTM NOI | Implied | Ratio | Deadline | Recommendation (FILE / WATCH / SKIP).
5. Save to Notion Operations Hub as "Tax Appeal Calendar — YYYY-MM".
6. Email Gabriel + Eric from ggoldberg@oxfordra.net via Composio Outlook (`mcp__8a611864-5cda-497f-baf9-6d3c02ab3404__COMPOSIO_MULTI_EXECUTE_TOOL` with `tool_slug: OUTLOOK_SEND_EMAIL`, account `outlook_dagger-sowl`). Subject: "ORA Tax Appeal Calendar — YYYY-MM (N candidates)". Body: top candidates with deadline urgency + link.
7. If any candidate has deadline within 30 days, prefix subject with "[ACTION REQUIRED]".

QC GATES
- All 27 properties evaluated.
- Cap rate floor sources cited.
- No appeal filed without Gabriel approval — this skill produces analysis only.

---

## Publication Guard (v1.1) — REQUIRED for all Notion writes in this skill

This skill follows the v1.1 publication-guard pattern documented at `C:\Users\Owner\OneDrive - Oxford Capital Partners (1)\Documents\Claude\Scheduled\_shared\PUBLICATION_GUARD.md`. Apply these five steps every time this skill calls `notion-create-pages`. This guard SUPERSEDES any prior in-body instructions to "log failure inline" or "do not retry more than once" — those were v1.0 conventions and are now obsolete.

1. **Capture** — invoke `notion-create-pages(parent=…, pages=[…])`. Capture `response.pages[0].id` as `publishedId` and `.url` as `publishedUrl`.
2. **Retry once** — if `publishedId` is null, undefined, an error code, or the response itself errored, retry the same `notion-create-pages` call exactly ONCE. Do not loop.
3. **Search-verify** — call `notion-search(query=<literal title used in Step 1>, filters={created_date_range: {start: today, end: today+1}})`. Confirm the returned page ID matches `publishedId`. If no match or different ID, treat as publication failure → Step 4.
4. **Outlook fallback (auto-send)** — IFF Steps 1+2+3 all failed, AUTO-SEND via Composio `OUTLOOK_SEND_EMAIL` with `account_id="outlook_icaco-sequel"`, `to="ggoldberg@oxfordra.net"`, `subject="❌ ora-tax-appeal-calendar PUBLICATION FAILED — <YYYY-MM-DD>"`, body containing what the page WOULD have contained verbatim, plus the Notion API error verbatim, body_tag `"AUTO-SENT — meta-failure path, no human-in-loop available"`. This auto-send overrides the default "draft, don't send" rule because the skill's audit/monitoring function is meaningless if its publication fails silently.
5. **Failure-mode logging** — append a single line to the skill's chat-summary output: `Publish: [✅ direct | ✅ retry | ❌ fallback-sent | ❌❌ total-blackout]`.

---

*Guard added 2026-05-10 per P0-2 tier-2/3 rollout (2026-05-08 health review). Reference: `_shared\PUBLICATION_GUARD.md` v1.1.*