---
name: ora-tenant-at-risk-monthly
description: Monthly tenant-at-risk scan (8th of month, 8:30 AM) — runs tenant-intelligence on full HubSpot tenant roster (monthly_rent > 0), surfaces top 5 risks with renewal probability, payment history, and concentration impact.
---

**[MCP ROUTING — normalized 2026-06-03]** Outlook email: `C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1` (PRIMARY) → `mcp__composio-ora__OUTLOOK_SEND_EMAIL` (fallback). HubSpot: native `mcp__a3e380ce-…__*`. Notion: native `mcp__c5f4869f-…__notion-*`. QuickBooks: Desktop only (no live MCP). The prior `8a611864` Composio wrapper is no longer connected; Rube `d6315173` is retired — never reference either. ORA does not use Google Workspace.

You are running the ORA Monthly Tenant-at-Risk Scan.

OBJECTIVE
Surface the top 5 tenants most likely to cause portfolio impact (default, non-renewal, or downsize) in the next 6 months, with recommended outreach.

EXECUTION
1. Invoke tenant-intelligence skill in PORTFOLIO_RISK mode. Inputs:
   - HubSpot Contacts — canonical tenant roster.
     Query: search_crm_objects, objectType=contacts,
     filterGroups: [{filters:[{propertyName:"monthly_rent",operator:"GT",value:"0"}]}, {filters:[{propertyName:"vacant_",operator:"EQ",value:"Yes"}]}]
     Properties: firstname, lastname, company, email, address, monthly_rent, vacant_,
     lease_start_date, lease_end_date, square_feet, escalation_percent,
     next_escalation_date, security_deposit, hs_object_id.
     Paginate with limit=200 until all ~140 contacts retrieved.
     Active tenants for risk scoring = monthly_rent > 0 AND vacant_ ≠ "Yes".
   - HubSpot tenant interactions (last 12 months) — notes and engagements per contact id
   - QuickBooks delinquency report (last 6 months)
2. Score each tenant on: payment history (40%), renewal probability (25%), industry/sector risk (15%), space-fit risk (10%), interaction sentiment (10%). Normalize 0-100, lower = higher risk.
3. Compute concentration impact for each: % of portfolio NOI lost if tenant exits.
4. Rank. Take top 5 (lowest scores OR highest concentration impact). For each, draft a recommended outreach action: (a) call from Gabriel/Eric, (b) renewal incentive, (c) credit check refresh, (d) replacement-tenant pre-marketing.
5. Build report in ORA Institutional Style. Save to Notion as "Tenant Risk Scan — YYYY-MM". Update ora-tenant-risk-scoreboard live artifact.
6. Email Gabriel + Eric from ggoldberg@oxfordra.net. Subject: "ORA Tenant Risk Scan — YYYY-MM (Top 5)". Body: tenant name, risk score, recommended action, deadline.

QC GATES
- Score model assumptions cited.
- Top 5 selections justified with both score AND concentration.
- NEVER auto-contact tenants. Drafts only.

---

## Publication Guard (v1.1) — REQUIRED for all Notion writes in this skill

This skill follows the v1.1 publication-guard pattern documented at `C:\Users\Owner\OneDrive - Oxford Capital Partners (1)\Documents\Claude\Scheduled\_shared\PUBLICATION_GUARD.md`. Apply these five steps every time this skill calls `notion-create-pages`. This guard SUPERSEDES any prior in-body instructions to "log failure inline" or "do not retry more than once" — those were v1.0 conventions and are now obsolete.

1. **Capture** — invoke `notion-create-pages(parent=…, pages=[…])`. Capture `response.pages[0].id` as `publishedId` and `.url` as `publishedUrl`.
2. **Retry once** — if `publishedId` is null, undefined, an error code, or the response itself errored, retry the same `notion-create-pages` call exactly ONCE. Do not loop.
3. **Search-verify** — call `notion-search(query=<literal title used in Step 1>, filters={created_date_range: {start: today, end: today+1}})`. Confirm the returned page ID matches `publishedId`. If no match or different ID, treat as publication failure → Step 4.
4. **Outlook fallback (auto-send)** — IFF Steps 1+2+3 all failed, AUTO-SEND via Composio `OUTLOOK_SEND_EMAIL` with `account_id="me"`, `to="ggoldberg@oxfordra.net"`, `subject="❌ ora-tenant-at-risk-monthly PUBLICATION FAILED — <YYYY-MM-DD>"`, body containing what the page WOULD have contained verbatim, plus the Notion API error verbatim, body_tag `"AUTO-SENT — meta-failure path, no human-in-loop available"`. This auto-send overrides the default "draft, don't send" rule because the skill's audit/monitoring function is meaningless if its publication fails silently.
5. **Failure-mode logging** — append a single line to the skill's chat-summary output: `Publish: [✅ direct | ✅ retry | ❌ fallback-sent | ❌❌ total-blackout]`.

---

*Guard added 2026-05-10 per P0-2 tier-2/3 rollout (2026-05-08 health review). Reference: `_shared\PUBLICATION_GUARD.md` v1.1.*