---
name: ora-lease-expiration-dashboard
description: Weekly rolling lease expiration dashboard — ENHANCED 2026-04-28 with auto-escalation and HubSpot task creation; PART 2 made idempotent 2026-05-25. Source: HubSpot Contacts (monthly_rent > 0 OR vacant_ = Yes). 8 urgency windows, WALT, renewal probability, concentration risk.
---

**[MCP ROUTING — normalized 2026-06-03]** Outlook email: `C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1` (PRIMARY) → `mcp__composio-ora__OUTLOOK_SEND_EMAIL` (fallback). HubSpot: native `mcp__a3e380ce-…__*`. Notion: native `mcp__c5f4869f-…__notion-*`. QuickBooks: Desktop only (no live MCP). The prior `8a611864` Composio wrapper is no longer connected; Rube `d6315173` is retired — never reference either. ORA does not use Google Workspace.

Run ORA Lease Expiration Dashboard — ENHANCED with auto-escalation and HubSpot task creation.

Source: HubSpot Contacts — canonical tenant roster.
Query: search_crm_objects, objectType=contacts
filterGroups: [{filters:[{propertyName:"monthly_rent",operator:"GT",value:"0"}]}, {filters:[{propertyName:"vacant_",operator:"EQ",value:"Yes"}]}]
Properties to fetch: firstname, lastname, company, email, address, monthly_rent, vacant_,
  lease_start_date, lease_end_date, square_feet, escalation_percent, next_escalation_date,
  security_deposit, base_year, option_date, hs_object_id
Paginate with limit=200 and offset until all contacts retrieved (total ~140).

Field mapping:
- Tenant name: company (fall back to firstname + lastname if company is blank)
- Property: address field
- SF: square_feet (parse as number)
- Monthly rent: monthly_rent (parse as number); Annual rent: monthly_rent × 12
- Lease expiration: lease_end_date
- Days to expiration: (lease_end_date − today in days)
- Vacant: vacant_ = "Yes"
- Active tenants: monthly_rent > 0 AND vacant_ ≠ "Yes"

PART 1 — Dashboard:
1. Fetch all tenant contacts from HubSpot as described above.
2. Filter to active tenants for expiration analysis.
3. Compute days-to-expiration for each lease using lease_end_date.
4. Bucket into 8 urgency windows: MTM (lease_end_date < today), 0-30d, 31-90d, 91-180d, 181-365d, 1-2yr, 2-3yr, 3yr+.
5. Compute portfolio WALT (with and without MTM) using square_feet as weight.
6. Quantify rollover risk in SF and annual revenue per window.
7. Apply renewal probability scoring per tenant via tenant-intelligence skill.
8. Surface concentration risk: largest expirations within 18 months.
9. Update ora-lease-expiration-rolling artifact.
10. Post structured brief to Notion Operations Hub.

PART 2 — Auto-Escalation (IDEMPOTENT as of 2026-05-25; migrated from Rube rcp_pYWxBJyxGLyB):

PRE-FLIGHT (run ONCE, before creating any task) — inventory existing renewal tasks:
- Query search_crm_objects, objectType=tasks, paginated (limit=200):
  filterGroups: [{filters:[{propertyName:"hs_task_subject",operator:"CONTAINS_TOKEN",value:"Renewal Outreach"}]}]
  properties: hs_task_subject, hs_task_status, hs_timestamp, hs_object_id
- A task is OPEN when hs_task_status ≠ "COMPLETED".
- Build OPEN_RENEWAL_TASKS: a map keyed by NORMALIZED tenant name, value = list of open task IDs.
  NORMALIZE(name): take the hs_task_subject text preceding "Renewal Outreach", lowercase it,
  then strip leading/trailing whitespace AND separator punctuation (em dash —, en dash –,
  hyphen -, commas, periods). This collapses the inconsistent legacy subject formats
  ("[Tenant] Renewal Outreach …" and "[Tenant] — Renewal Outreach …") onto one key so the
  pre-cleanup backlog is still recognized. Apply the SAME NORMALIZE() to each tenant's company
  name when performing the idempotency lookup in Step B.

For each active HubSpot tenant where days-to-expiration ≤ 180:
A. Read the contact's hs_lead_status and record it in the run summary (context only — it does
   NOT gate task creation).
B. IDEMPOTENCY GATE — look the tenant up in OPEN_RENEWAL_TASKS (normalized-name match):
   - If ≥1 open task already exists → DO NOT create a task. Record "skipped — already
     escalated (N open task[s])".
   - If none exists → create exactly ONE HubSpot task (objectType=tasks):
       • hs_task_subject = "[company] Renewal Outreach — 180-day window"  ← use this exact
         string; the literal " Renewal Outreach — 180-day window" suffix is the dedup key,
         so never vary its spacing or punctuation.
       • hs_task_body = tenant / property / SF / annual rent / lease end / days-to-expiration /
         urgency bucket / renewal probability / hs_lead_status / "Source:
         ora-lease-expiration-dashboard <YYYY-MM-DD>".
       • hs_task_status = "NOT_STARTED", hs_task_priority = "HIGH".
       • hs_timestamp = 5 business days after the run date (17:00 ET).
       • hubspot_owner_id = the owner ID for ggoldberg@oxfordra.net (resolve via search_owners).
       • associations: targetObjectType=contacts, targetObjectId = the tenant's hs_object_id.
       • confirmationStatus = "CONFIRMATION_WAIVED_FOR_SESSION" — this scheduled task is the
         standing authorization for the write.
     Record "task created (id …)".
C. Capture the per-tenant action (created / skipped) in the run summary.

NEVER create a second open task for a tenant that already has one. The skill is expected to
create 0 tasks in any week where every ≤180-day tenant is already covered.

STALE-TASK RECONCILIATION (report only — do NOT auto-close or delete):
- List every OPEN_RENEWAL_TASKS entry whose tenant is NOT in the current ≤180-day set under
  "Stale renewal tasks" in the run summary (tenant renewed, departed, or rolled past 180 days).
  Recommend manual close in HubSpot.
- If any tenant maps to >1 open task, report the duplicate count as a CRM-hygiene flag.

Output:
- Email Gabriel + Eric via Outlook from ggoldberg@ with three sections: dashboard summary, auto-escalation actions taken (tasks created, tenants skipped as already-escalated, stale tasks flagged), priority renewal queue.
- Subject: "ORA Lease Expiration Dashboard — Week of [Mon date]".
- Notion Operations Hub page archiving the brief.

Format: ORA Institutional Style Guide v1.0+.

---

## Publication Guard (v1.1) — REQUIRED for all Notion writes in this skill

This skill follows the v1.1 publication-guard pattern documented at `C:\Users\Owner\OneDrive - Oxford Capital Partners (1)\Documents\Claude\Scheduled\_shared\PUBLICATION_GUARD.md`. Apply these five steps every time this skill calls `notion-create-pages`. This guard SUPERSEDES any prior in-body instructions to "log failure inline" or "do not retry more than once" — those were v1.0 conventions and are now obsolete.

1. **Capture** — invoke `notion-create-pages(parent=…, pages=[…])`. Capture `response.pages[0].id` as `publishedId` and `.url` as `publishedUrl`.
2. **Retry once** — if `publishedId` is null, undefined, an error code, or the response itself errored, retry the same `notion-create-pages` call exactly ONCE. Do not loop.
3. **Search-verify** — call `notion-search(query=<literal title used in Step 1>, filters={created_date_range: {start: today, end: today+1}})`. Confirm the returned page ID matches `publishedId`. If no match or different ID, treat as publication failure → Step 4.
4. **Outlook fallback (auto-send)** — IFF Steps 1+2+3 all failed, AUTO-SEND via Composio `OUTLOOK_SEND_EMAIL` with `account_id="me"`, `to="ggoldberg@oxfordra.net"`, `subject="❌ ora-lease-expiration-dashboard PUBLICATION FAILED — <YYYY-MM-DD>"`, body containing what the page WOULD have contained verbatim, plus the Notion API error verbatim, body_tag `"AUTO-SENT — meta-failure path, no human-in-loop available"`. This auto-send overrides the default "draft, don't send" rule because the skill's audit/monitoring function is meaningless if its publication fails silently.
5. **Failure-mode logging** — append a single line to the skill's chat-summary output: `Publish: [✅ direct | ✅ retry | ❌ fallback-sent | ❌❌ total-blackout]`.

---

*Guard added 2026-05-10 per P0-2 tier-2/3 rollout (2026-05-08 health review). Reference: `_shared\PUBLICATION_GUARD.md` v1.1.*

*PART 2 made idempotent 2026-05-25: the escalation step now inventories existing open "Renewal Outreach" tasks and skips any tenant already covered, instead of creating one task per ≤180-day tenant every run. Fix prompted by the 2026-05-25 run, which found 63 open renewal tasks accumulated across the 2026-05-04 / 05-11 / 05-18 runs (26 distinct tenants; up to 3 duplicates each) because the prior PART 2 had no deduplication. The skill now also flags stale tasks (tenants since renewed/departed) for manual close. One-time cleanup of the existing 63-task backlog remains a manual action.*