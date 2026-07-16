---
name: ora-insurance-renewal-tracker
description: Quarterly insurance renewal tracker — ENHANCED 2026-04-28 to also cover tenant COI expirations. Property side: 27 ORA policies against 120/90/60-day windows. Tenant side: scans all active (non-vacant) tenants from HubSpot Contacts for COI expiration status.
---

**[COMPOSIO MIGRATION 2026-05-08 — Rube EOL bridge]** All MCP routing on this task is pinned to the native Composio Platform connector (`mcp__8a611864-5cda-497f-baf9-6d3c02ab3404__COMPOSIO_*`), NOT the legacy Rube namespace (`mcp__d6315173-234c-4e6c-bea7-7f5e15d2bde5__RUBE_*`). Tool slugs (`OUTLOOK_SEND_EMAIL`, `OUTLOOK_CREATE_DRAFT`, `OUTLOOK_CREATE_ME_EVENT`, `HUBSPOT_*`, etc.) are byte-identical between stacks; only the MCP server prefix changes. Use the Composio path for Outlook (mail + calendar) and HubSpot. ORA does not use Google Workspace — no GCal/GSheets routing applies. (Notion writes can continue to use the native `mcp__c5f4869f-...__notion-*` MCP; QuickBooks reads can continue to use the native `mcp__52fa80c0-...` MCP.)

Run ORA Insurance Renewal Tracker — covers BOTH property policies AND tenant COI compliance.

PART 1 — Property Insurance (existing logic):
1. Pull all 27 ORA property policies from Notion Operations Hub or insurance database.
2. For each policy, compute days until expiration.
3. Bucket: 120d / 90d / 60d / 30d / expired.
4. Surface premium creep year-over-year.
5. Carrier exposure analysis.
6. Update ora-insurance-renewal-calendar artifact.

PART 2 — Tenant COI Compliance (migrated from Rube rcp_IG3xjM7bt6rG):
1. Pull all active (non-vacant) tenants from HubSpot Contacts — canonical tenant roster.
   Query: search_crm_objects, objectType=contacts,
   filterGroups: [{filters:[{propertyName:"monthly_rent",operator:"GT",value:"0"}]}]
   Properties: firstname, lastname, company, email, address, monthly_rent,
   lease_end_date, square_feet, hs_object_id.
   Paginate with limit=200 until all active tenants retrieved.
2. For each tenant contact, check HubSpot notes/engagements for any COI or certificate of insurance data. If a COI expiration date is recorded, compute days until expiration.
3. Bucket and note COI status per tenant: Current / Expiring 60 Days / Expiring 30 Days / Expired / Not on File.
4. Verify COI naming ORA entities as additional insured (where data captured in HubSpot notes).
5. Compute portfolio metrics: count by status, % expired or expiring 30 days.

Output:
- Email Gabriel + Eric via Outlook from ggoldberg@ with two sections:
  Section A: Property policy renewal queue (carrier, premium delta, action queue).
  Section B: Tenant COI compliance status (count by bucket, list of expired/expiring-30d tenants).
- Subject: "ORA Insurance Tracker Q[N] [YYYY] — Property + Tenant COI" (prefix [ALERT] if any tenant Expired or any property < 30 days to expiration).
- Notion Operations Hub page archiving both sections.
- Update ora-insurance-renewal-calendar artifact.

Format: ORA Institutional Style Guide v1.0+.

---

## Publication Guard (v1.1) — REQUIRED for all Notion writes in this skill

This skill follows the v1.1 publication-guard pattern documented at `C:\Users\Owner\OneDrive - Oxford Capital Partners (1)\Documents\Claude\Scheduled\_shared\PUBLICATION_GUARD.md`. Apply these five steps every time this skill calls `notion-create-pages`. This guard SUPERSEDES any prior in-body instructions to "log failure inline" or "do not retry more than once" — those were v1.0 conventions and are now obsolete.

1. **Capture** — invoke `notion-create-pages(parent=…, pages=[…])`. Capture `response.pages[0].id` as `publishedId` and `.url` as `publishedUrl`.
2. **Retry once** — if `publishedId` is null, undefined, an error code, or the response itself errored, retry the same `notion-create-pages` call exactly ONCE. Do not loop.
3. **Search-verify** — call `notion-search(query=<literal title used in Step 1>, filters={created_date_range: {start: today, end: today+1}})`. Confirm the returned page ID matches `publishedId`. If no match or different ID, treat as publication failure → Step 4.
4. **Outlook fallback (auto-send)** — IFF Steps 1+2+3 all failed, AUTO-SEND via Composio `OUTLOOK_SEND_EMAIL` with `account_id="outlook_icaco-sequel"`, `to="ggoldberg@oxfordra.net"`, `subject="❌ ora-insurance-renewal-tracker PUBLICATION FAILED — <YYYY-MM-DD>"`, body containing what the page WOULD have contained verbatim, plus the Notion API error verbatim, body_tag `"AUTO-SENT — meta-failure path, no human-in-loop available"`. This auto-send overrides the default "draft, don't send" rule because the skill's audit/monitoring function is meaningless if its publication fails silently.
5. **Failure-mode logging** — append a single line to the skill's chat-summary output: `Publish: [✅ direct | ✅ retry | ❌ fallback-sent | ❌❌ total-blackout]`.

---

*Guard added 2026-05-10 per P0-2 tier-2/3 rollout (2026-05-08 health review). Reference: `_shared\PUBLICATION_GUARD.md` v1.1.*