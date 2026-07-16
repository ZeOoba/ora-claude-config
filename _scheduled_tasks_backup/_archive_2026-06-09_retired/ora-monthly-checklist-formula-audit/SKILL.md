---
name: ora-monthly-checklist-formula-audit
description: Monthly checklist formula audit — runs day 5 of month, 07:30. Scans all xlsx checklists in active deal folders for range/data-extent mismatches and emails defect report to Gabriel + Eric. Audit output now includes (a) audit-window timestamp and (b) Pre-Flight Migration-Eligibility Inventory (TABLED / MIGRATION-ELIGIBLE / NOT-ELIGIBLE counts) so the post-closing structured-table migration window opens with a fresh discovery rather than re-running by hand. Updated 2026-05-06.
---

**[MCP ROUTING — normalized 2026-06-03]** Outlook email: `C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1` (PRIMARY) → `mcp__composio-ora__OUTLOOK_SEND_EMAIL` (fallback). HubSpot: native `mcp__a3e380ce-…__*`. Notion: native `mcp__c5f4869f-…__notion-*`. QuickBooks: Desktop only (no live MCP). The prior `8a611864` Composio wrapper is no longer connected; Rube `d6315173` is retired — never reference either. ORA does not use Google Workspace.

ORA Monthly Checklist Formula Audit — automated scan for dashboard formula range gaps.

## Purpose
Detect the "frozen-range vs. live-data-extent" defect across all ORA xlsx checklists and trackers. This defect was first surfaced 2026-04-27 in the E. Fulton DD Checklist (D14:D39 missed row 40; D42:D67 missed rows 68-69) and again in the Property Purchase Checklist (MASTER CHECKLIST!Q5:S17 dashboard covered only 11 of 17 sections, leaving ~37 line items invisible including the Stearns Bank foreclosure tracking).

## Scope
Scan all .xlsx files in:
- Active deal folders under `C:\Users\Owner\OneDrive - Oxford Capital Partners (1)\` (E Fulton DD folder, plus any newer active acquisitions)
- ORA canonical checklists wherever they live (Property Purchase Checklist, DD Checklist Best, monthly close, ops trackers)

Skip: financial models (IRRModel*.xlsx — those have intentional fixed ranges) and lease abstracts (Lease Summaries*.xlsx).

## Audit Procedure
For each xlsx file in scope:
1. Load all sheets via openpyxl
2. Extract all formulas containing range references like `A1:A10`, `B5:C20`, etc.
3. For each range, check:
   - Does the formula's range cover all populated cells in that column / region?
   - Are there populated cells immediately AFTER the range end?
   - Are there populated cells immediately BEFORE the range start (excluding header)?
4. Flag any "range tail short of data" or "range head past header" mismatches.

## Defect Report Format
For each defect:
- File path
- Sheet name
- Cell containing the formula
- Current range
- Suggested range (extending to actual data extent)
- Risk level: HIGH if dashboard counter / total formula; MEDIUM if section-specific; LOW if cosmetic

## Pre-Flight Migration-Eligibility Inventory (added 2026-05-06)
Every audit run must include a one-section pre-flight inventory ahead of the post-closing structured-table migration window (per `outputs/20260506_ORA_StructuredTableMigrationPlan_v01.md` §5; trigger window 2026-06-21 through 2026-07-15 for E. Fulton, and applicable to every future deal).

For each xlsx file in scope, classify each sheet as:
- **TABLED** — sheet already uses Excel structured tables (List Objects); count `wb[sheetname].tables` via openpyxl
- **MIGRATION-ELIGIBLE** — sheet has a contiguous data block of ≥10 rows with a header row and at least one aggregation formula referencing a hard-coded range over that block; would benefit from migration
- **NOT MIGRATION-ELIGIBLE** — sheet is a financial model, lease abstract, dashboard-only sheet without a data block, or otherwise structurally unsuited

Output:
- Audit window date — print as "This audit covers workbook state as of YYYY-MM-DD HH:MM:SS local time" at the top of every report
- Per-deal-folder counts — TABLED / MIGRATION-ELIGIBLE / NOT-ELIGIBLE
- Portfolio-level totals
- Trend line if prior audit reports exist in `outputs/` — does the migration-eligible count change month over month?
- Names of new MIGRATION-ELIGIBLE files (i.e., new workbooks added since last audit) so the post-closing migration window opens with a fresh pre-flight inventory rather than re-running discovery by hand

## Delivery
1. Save defect report as `outputs/[YYYYMMDD]_ORA_ChecklistFormulaAudit_[YYYY-MM].md` in the most-active deal folder
2. Post a Notion page in Operations Hub (database 32b6ecd8-9e59-81f2-b329-df3fd0e25062) with the audit summary and defect count
3. Email ggoldberg@oxfordra.net via Composio OUTLOOK_SEND_EMAIL (Eric removed per Gabriel directive 2026-05-15) with:
   - Subject: "ORA Checklist Formula Audit — [Month YYYY] — [N] defects detected" (or "No defects detected")
   - Body: defect summary table, link to full report, recommended actions
4. If zero defects detected, send a brief "all clean" confirmation email (do not skip — confirms the audit ran)

## Hard Constraints
- Read-only on source files. NEVER modify a checklist as part of the audit; produce a report only.
- Honor the 2x/day scheduled-task cap (this task runs monthly, well under cap).
- If a file fails to load (corrupted xlsx, locked by another process), log the failure in the report and continue with remaining files.
- Email routing: To ggoldberg@oxfordra.net only per Gabriel directive 2026-05-15 (overrides prior cc-both rule and any older ze@oxfordra.net default). Eric receives only the Daily Brief.

## Output File Naming
`[YYYYMMDD]_ORA_ChecklistFormulaAudit_v01.md` saved to outputs/ in the most active deal folder (currently `E Fulton Street Due Dilligence Items/outputs/`).

---

## Publication Guard (v1.1) — REQUIRED for all Notion writes in this skill

This skill follows the v1.1 publication-guard pattern documented at `C:\Users\Owner\OneDrive - Oxford Capital Partners (1)\Documents\Claude\Scheduled\_shared\PUBLICATION_GUARD.md`. Apply these five steps every time this skill calls `notion-create-pages`. This guard SUPERSEDES any prior in-body instructions to "log failure inline" or "do not retry more than once" — those were v1.0 conventions and are now obsolete.

1. **Capture** — invoke `notion-create-pages(parent=…, pages=[…])`. Capture `response.pages[0].id` as `publishedId` and `.url` as `publishedUrl`.
2. **Retry once** — if `publishedId` is null, undefined, an error code, or the response itself errored, retry the same `notion-create-pages` call exactly ONCE. Do not loop.
3. **Search-verify** — call `notion-search(query=<literal title used in Step 1>, filters={created_date_range: {start: today, end: today+1}})`. Confirm the returned page ID matches `publishedId`. If no match or different ID, treat as publication failure → Step 4.
4. **Outlook fallback (auto-send)** — IFF Steps 1+2+3 all failed, AUTO-SEND via Composio `OUTLOOK_SEND_EMAIL` with `account_id="me"`, `to="ggoldberg@oxfordra.net"`, `subject="❌ ora-monthly-checklist-formula-audit PUBLICATION FAILED — <YYYY-MM-DD>"`, body containing what the page WOULD have contained verbatim, plus the Notion API error verbatim, body_tag `"AUTO-SENT — meta-failure path, no human-in-loop available"`. This auto-send overrides the default "draft, don't send" rule because the skill's audit/monitoring function is meaningless if its publication fails silently.
5. **Failure-mode logging** — append a single line to the skill's chat-summary output: `Publish: [✅ direct | ✅ retry | ❌ fallback-sent | ❌❌ total-blackout]`.

---

*Guard added 2026-05-10 per P0-2 tier-2/3 rollout (2026-05-08 health review). Reference: `_shared\PUBLICATION_GUARD.md` v1.1.*