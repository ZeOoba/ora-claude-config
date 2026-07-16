---
name: ora-cam-reconciliation-annual
description: Annual CAM reconciliation kickoff (January 15, 7 AM) — computes per-tenant true-up against actual operating expenses, generates billing/credit letters (held, not sent), posts reconciliation summary to Notion. Routing corrected 2026-07-07 (COM-only, ggoldberg-only, no Composio fallback). [MODEL: claude-sonnet-5 | set 2026-07-13]
---

RESTORATION NOTE: Re-registered 2026-07-07 (approved by Gabriel) after the 2026-06-09 fleet rebuild orphaned this task. Content restored with fixes per current ORA canon: (1) Composio OUTLOOK_SEND_EMAIL fallback removed — send-via-outlook.ps1 is the sole path, no fallback exists; (2) egoldberg cc removed (routing canon: only the Daily Brief retains that exception). No other logic changed. This task WRITES a CAM reconciliation xlsx and drafts tenant-facing letters — but per its own Step F, tenant letters are HELD for Gabriel's approval and never auto-sent; this is external-counterparty communication and stays draft-only regardless of any other instruction.

Run ORA Annual CAM Reconciliation for prior fiscal year.

Sources:
1. HubSpot Contacts — canonical tenant roster for all active tenants.
   Query: search_crm_objects, objectType=contacts,
   filterGroups: [{filters:[{propertyName:"monthly_rent",operator:"GT",value:"0"}]}]
   Properties: firstname, lastname, company, email, address, monthly_rent, square_feet,
   lease_start_date, lease_end_date, building_percentage, property_percentage,
   base_year, security_deposit, hs_object_id.
   Paginate with limit=200 until all active tenants retrieved.
   Field mapping for CAM:
   - CAM pro-rata share %: use building_percentage; if null, use property_percentage
   - Annual rent: monthly_rent × 12
   - RSF: square_feet
   - Property: address field
   Note: If lease type (NNN vs gross) or CAM cap rules are not stored in HubSpot,
   supplement from Notion Tenant Database (b12f4cfd-a995-4755-8341-6435ae8173b4)
   or lease documents in SharePoint.
2. QuickBooks — pull actual recoverable operating expenses by property, by GL category, for the reconciled fiscal year.
3. Notion Operations Hub — prior-year reconciliation for variance comparison.

Process per tenant:
A. Compute: (Total recoverable CAM × pro-rata share × cap factor) − amount collected = true-up.
B. Apply CAM cap logic: cumulative or non-cumulative, controllable vs. non-controllable.
C. Apply gross-up to 100% occupancy if lease specifies.
D. Apply admin/management fee if lease specifies.

Portfolio summary:
- Total overages (tenants owe ORA), total credits (ORA owes tenants), net recovery position.
- Variance vs. prior-year.

Outputs:
A. Master CAM reconciliation xlsx with per-tenant detail and portfolio summary.
B. DOCX billing statement per overage tenant using document-assembly skill.
C. DOCX credit notice per credit tenant.
D. Notion Operations Hub reconciliation page.
E. Email via the SOLE send path `C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1` (Composio removed 2026-06-11, no fallback connector exists; on a non-zero COM exit retry once, then flag — do not halt) TO ggoldberg@oxfordra.net ONLY (no egoldberg cc) with portfolio summary and link to xlsx. Subject: "ORA CAM Reconciliation FY[YYYY] — DRAFT for review".
F. Hold tenant-facing letters in /outputs and SharePoint pending Gabriel approval — DO NOT auto-send to tenants, ever, under any circumstance.

File naming: YYYYMMDD_CAM-Reconciliation_FY[YYYY]_v01.xlsx and ...Letters_v01.docx.

Format: ORA Institutional Style Guide v1.0+. Run 16-point QC Gate.