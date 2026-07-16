---
name: ora-cre-data-mcp-recheck
description: Quarterly CRE-data MCP availability recheck (1st of Jan/Apr/Jul/Oct, 9 AM) — searches the Anthropic MCP registry for Reonomy, Regrid, CompStak, CoStar, Buildout, ATTOM. Emails Gabriel + Eric if any new connector becomes available. Composio Outlook pin added 2026-05-08.
---

**[COMPOSIO MIGRATION 2026-05-08 — Rube EOL bridge]** All MCP routing on this task is pinned to the native Composio Platform connector (`mcp__8a611864-5cda-497f-baf9-6d3c02ab3404__COMPOSIO_*`), NOT the legacy Rube namespace (`mcp__d6315173-234c-4e6c-bea7-7f5e15d2bde5__RUBE_*`). Tool slugs (`OUTLOOK_SEND_EMAIL`, `OUTLOOK_CREATE_DRAFT`, `OUTLOOK_CREATE_ME_EVENT`, `HUBSPOT_*`, etc.) are byte-identical between stacks; only the MCP server prefix changes. Use the Composio path for Outlook (mail + calendar) and HubSpot. ORA does not use Google Workspace — no GCal/GSheets routing applies. (Notion writes can continue to use the native `mcp__c5f4869f-...__notion-*` MCP; QuickBooks reads can continue to use the native `mcp__52fa80c0-...` MCP.)

You are running the ORA Quarterly CRE-Data MCP Availability Recheck.

OBJECTIVE
Detect whether any of the priority CRE-data MCP connectors have shipped to the Anthropic registry since the last check, and notify Gabriel + Eric if so.

EXECUTION
1. For each target connector below, call mcp__mcp-registry__search_mcp_registry with the relevant keywords. Targets:
   - Reonomy (commercial property data)
   - Regrid (parcel data)
   - CoStar (CRE marketplace + analytics)
   - CompStak (lease comps)
   - Buildout (CRE marketing)
   - ATTOM (property + tax data)
2. Compare results against the last-known availability cache stored in Notion Knowledge Base under page "CRE-Data MCP Watch List". If first run, baseline = none available.
3. For any newly-available connector, capture: name, vendor URL, tool list (≥10 most relevant), pricing if visible.
4. Update the Notion cache page with current availability state, dated.
5. If ≥1 new connector is available, email Gabriel + Eric from ggoldberg@oxfordra.net via Composio Outlook (`mcp__8a611864-5cda-497f-baf9-6d3c02ab3404__COMPOSIO_MULTI_EXECUTE_TOOL` with `tool_slug: OUTLOOK_SEND_EMAIL`, account `outlook_dagger-sowl`). Subject: "[NEW] CRE-Data MCP Available: {connector}". Body: summary + recommended action (install vs. wait).
6. If no change, log a one-liner to the Notion page and skip email.

QC GATES
- All 6 targets queried.
- Cache page updated regardless of outcome.
- NEVER auto-install a connector — surface for Gabriel approval only.

---

## Publication Guard (v1.1) — REQUIRED for all Notion writes in this skill

This skill follows the v1.1 publication-guard pattern documented at `C:\Users\Owner\OneDrive - Oxford Capital Partners (1)\Documents\Claude\Scheduled\_shared\PUBLICATION_GUARD.md`. Apply these five steps every time this skill calls `notion-create-pages`. This guard SUPERSEDES any prior in-body instructions to "log failure inline" or "do not retry more than once" — those were v1.0 conventions and are now obsolete.

1. **Capture** — invoke `notion-create-pages(parent=…, pages=[…])`. Capture `response.pages[0].id` as `publishedId` and `.url` as `publishedUrl`.
2. **Retry once** — if `publishedId` is null, undefined, an error code, or the response itself errored, retry the same `notion-create-pages` call exactly ONCE. Do not loop.
3. **Search-verify** — call `notion-search(query=<literal title used in Step 1>, filters={created_date_range: {start: today, end: today+1}})`. Confirm the returned page ID matches `publishedId`. If no match or different ID, treat as publication failure → Step 4.
4. **Outlook fallback (auto-send)** — IFF Steps 1+2+3 all failed, AUTO-SEND via Composio `OUTLOOK_SEND_EMAIL` with `account_id="outlook_icaco-sequel"`, `to="ggoldberg@oxfordra.net"`, `subject="❌ ora-cre-data-mcp-recheck PUBLICATION FAILED — <YYYY-MM-DD>"`, body containing what the page WOULD have contained verbatim, plus the Notion API error verbatim, body_tag `"AUTO-SENT — meta-failure path, no human-in-loop available"`. This auto-send overrides the default "draft, don't send" rule because the skill's audit/monitoring function is meaningless if its publication fails silently.
5. **Failure-mode logging** — append a single line to the skill's chat-summary output: `Publish: [✅ direct | ✅ retry | ❌ fallback-sent | ❌❌ total-blackout]`.

---

*Guard added 2026-05-10 per P0-2 tier-2/3 rollout (2026-05-08 health review). Reference: `_shared\PUBLICATION_GUARD.md` v1.1.*