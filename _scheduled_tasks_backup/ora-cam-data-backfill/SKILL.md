---
name: ora-cam-data-backfill
description: One-time CAM data-readiness backfill (2026-08-15) — lease-abstraction-pipeline batch run against SharePoint lease documents to populate CAM Recovery Type / OpEx Budget PSF / Lease Type / pro-rata share for the Notion Tenant DB + HubSpot ahead of the 2027-01-15 CAM reconciliation cycle. [MODEL: claude-sonnet-5 | set 2026-07-13]
---

This is an automated one-time run. The user (Gabriel Goldberg, VP Acquisitions, ORA) is not present to answer questions — execute autonomously, make reasonable choices, and note them in your output. Only take "write" actions this prompt specifically asks for. End your response with <run-summary>one or two sentences on what you found and whether anything changed</run-summary>.

CONTEXT: ora-cam-reconciliation-annual ran off-cadence on 2026-07-12 and hit a data-readiness wall: of 139 active tenants (HubSpot) / 139 active records (Notion Tenant DB, collection b12f4cfd-a995-4755-8341-6435ae8173b4), 0/139 had CAM Recovery Type on file, 0/139 had OpEx Budget PSF, only 16/139 had Lease Type, and only 45/138 had a stored pro-rata share (building_percentage/property_percentage). The Notion CAM Reconciliation DB had zero FY2024/2025 rows — this was the annual task's first real run. This task exists to close that gap well before the next scheduled fire (2027-01-15, cron "0 7 15 1 *").

TASK: Run a lease-abstraction-pipeline batch pass (per that skill's SKILL.md — batch mode, scheduled/autonomous operation, do not pause mid-run) against the commercial lease documents in SharePoint / OneDrive "Investment Candidates -- 2026" and any property-specific lease folders reachable via the sharepoint_search / sharepoint_folder_search MCP tools, scoped to the ~139 active tenants in the Notion Tenant DB (b12f4cfd-a995-4755-8341-6435ae8173b4). For each tenant with a locatable, abstractable lease document, extract and upsert into the Notion Tenant DB (and HubSpot Contacts where the corresponding field exists):
- CAM Recovery Type (NNN / gross / modified gross / cumulative vs. non-cumulative cap, controllable vs. non-controllable)
- OpEx Budget PSF (if stated or derivable from the lease's expense-stop / base-year language)
- Lease Type
- Pro-rata share (building_percentage / property_percentage) — cross-check against any existing HubSpot value rather than overwriting silently if they conflict; flag conflicts instead of guessing.

Do NOT fabricate any of these fields for a tenant whose lease document cannot be located or is not abstractable — leave that tenant flagged as a genuine gap rather than inferring a plausible-sounding value, per the no-fabrication invariant. This mirrors the same data-readiness gap already logged in reference_tenant_db_completeness_gap.md and the 2026-07-12 CAM Reconciliation FY2025 BLOCKED Notion page — cross-reference both for context, and update reference_tenant_db_completeness_gap.md's Claude-system memory copy is out of scope for this Cowork-surface task (leave that to a Code-surface session); instead note remaining gaps in this run's own output.

OUTPUT:
A. A coverage-gap-closure XLSX (before/after CAM-field coverage % by field, per ORA Institutional Style Guide v1.0+, 16-point QC Gate) saved to this run's outputs folder.
B. A Notion Operations Hub status page summarizing: tenants processed, fields newly populated by field, tenants still gapped and why (no lease found / lease found but field not stated / conflict flagged).
C. Email via the SOLE send path C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1 (retry once on non-zero exit, then flag loudly in the Notion page rather than halting) TO ggoldberg@oxfordra.net ONLY (no cc — routing canon) with the coverage-gap-closure summary and a link to the XLSX and Notion page. Subject: "ORA CAM Data-Readiness Backfill — [coverage %] before Jan 2027 cycle".

Do not touch any tenant financial/lease field beyond the four CAM-readiness fields listed above. No tenant-facing communications of any kind — this task only touches internal Notion/HubSpot records and the ggoldberg-only internal email above.