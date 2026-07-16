---
name: ora-sharepoint-aging-freshness-check
description: Weekly Sunday 8:00 PM ET audit of ORA SharePoint workspace for stale, orphaned, or non-conforming files; reports to Notion Ops Hub and emails Goldbergs.
---

ORA SHAREPOINT AGING & FRESHNESS CHECK — Weekly Sunday 20:00 ET

OBJECTIVE
Audit `oxfordra.sharepoint.com/sites/ClaudeWorkspace` and the broader ORA SharePoint tenant for (a) stale documents, (b) naming-convention violations, (c) orphaned drafts, (d) misplaced files, and (e) artifacts associated with retired deals. Output a remediation queue.

SCOPE & THRESHOLDS
1. Inventory all files modified date, owner, path, and size across these root folders (extend if more exist):
   - /Claude_Workspace/Deals/
   - /Claude_Workspace/Properties/
   - /Claude_Workspace/Tenants/
   - /Claude_Workspace/References/
   - /Claude_Workspace/Reports/
   - /Claude_Workspace/Outputs/
   - /Claude_Workspace/Inbox/
2. Aging buckets:
   - GREEN: modified ≤30 days
   - AMBER: 31–90 days (review)
   - RED: 91–180 days (action required)
   - BLACK: >180 days (archive or delete decision)
3. Apply context overrides — closed-deal DD packages stay PERMANENT in /Closed-Deals/; reference materials (Voice Register, Standard Positions, Style Guide) are evergreen unless version bumped.

CHECKS
A. NAMING CONFORMANCE — flag any file in /Outputs/, /Reports/, or /Deals/ that does not match `YYYYMMDD_[Property-or-Topic]_[DocType]_[v##].ext`. Provide the file path and a proposed corrected name.
B. ORPHANED DRAFTS — files with "_DRAFT", "_WIP", "v01"–"v09" that have not advanced in >30 days and are not paired with a finalized version.
C. RETIRED DEAL ARTIFACTS — cross-check against Notion Acquisition Pipeline Tracker (bcfe4a03); any deal in Status = Killed or Closed for >60 days with files outside /Closed-Deals/ or /Dead-Deals/ should be flagged for `deal-retirement` skill.
D. DUPLICATE DETECTION — same filename or same size+modified-date pairs across two folders; surface top 20.
E. PDF TEXT LAYER — sample 5 random PDFs from the past 30 days; confirm extractable text. Flag any failures (Microsoft Print to PDF prohibition).
F. EMPTY OR PLACEHOLDER FILES — files <2KB that are not legitimate metadata stubs.
G. PERMISSION ANOMALIES — files shared externally or with broad org-wide read; list with sharer and date.

OUTPUTS
1. SharePoint XLSX: `Claude_Workspace/Reports/{YYYYMMDD}_SharePoint_Freshness-Audit_v01.xlsx` with sheets: Summary, Aging-Inventory, Naming-Violations, Orphaned-Drafts, Retired-Deal-Artifacts, Duplicates, PDF-Failures, Permission-Anomalies.
2. Notion Ops Hub (32b6ecd8-9e59-81f2-b329-df3fd0e25062) entry titled `SharePoint Freshness Audit — {YYYY-MM-DD}` summarizing counts per category and linking the XLSX. Tag: Workflow-Hygiene.
3. Email digest via Composio OUTLOOK_SEND_EMAIL from ggoldberg@oxfordra.net to ggoldberg@oxfordra.net (Eric removed per Gabriel directive 2026-05-15 — only Daily Brief retains egoldberg cc). Subject: `ORA Workspace Hygiene — {YYYY-MM-DD} — {N_red+N_black} items require action`. Body: top-line counts, 5 highest-priority remediation items with paths, link to full XLSX in SharePoint.

CONSTRAINTS
- Do NOT delete or move any files. Audit-only. Remediation is human-approved next pass.
- Do NOT modify permissions.
- If SharePoint MCP returns auth or throttling errors, retry once with exponential backoff; on second failure, log to Notion Ops Hub and email ggoldberg@oxfordra.net with the error.
- Run the 16-point QC Gate on the XLSX before publishing.
- File naming follows the ORA convention literally.

CLOSE
Append ≤3 bullets of workflow optimization observations (recurring violation patterns, candidate skills, naming-rule edge cases) to the Notion entry.