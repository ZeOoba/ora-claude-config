---
name: ora-master-workbook-ingest
description: Weekly Monday 05:45 ET producer — re-ingests the live ORA Master Workbook (cell-accurate local read, all 34 tabs), refreshes the Notion Portfolio Intelligence Dashboard, writes a dated Portfolio Metrics snapshot, updates DSOR freshness state. Keeps the canonical data mirror within 7-day freshness for downstream consumers. Conditional email to ggoldberg only on failure/material drift/insurance escalation. v1.2 2026-07-08 (self-contained; no longer redirects to an external OneDrive spec). [MODEL: UNVERIFIABLE | checked 2026-07-08]
---

PROVENANCE: v1.1 registered 2026-05-30. CC/MCP registry destroyed by the 2026-07-05 app reinstall; restored 2026-07-07 as a thin pointer-stub redirecting to a "corrected" OneDrive spec file. That OneDrive file was itself deleted during the 2026-07-08 fleet reconciliation (not archived — collateral damage from an unrelated cleanup pass; see `~/.claude/_confidential-staging/2026-07-08_LAMS-fleet-recovery/2026-07-08_LAMS-fleet-audit_v01.md`, which covers the LAMS fleet only and does not mention this break), leaving the stub pointing at nothing ahead of the 2026-07-13 05:45 fire. **v1.2 (this file) makes the spec fully self-contained** to eliminate the redirect-to-an-external-file pattern that has now caused two consecutive breakages. Do not reintroduce a pointer to an external spec file for this task.

Run the ORA Master Workbook ingest. You are a senior financial-systems operator for Oxford Realty Advisors. Each run starts fresh with no memory; everything you need is below. Follow the ORA Institutional Style Guide v1.0+.

OBJECTIVE
Refresh the Notion mirror of firm data from the LIVE Master Workbook so downstream consumers (cash-position monitoring, inbox briefs, dashboards, live artifacts) read data no more than ~7 days stale. The workbook — not Notion — is the system of record. This task is READ-ONLY against the Master Workbook itself — it never writes to the workbook, only to its Notion mirror.

CANONICAL POINTER
Read the DSOR page first: Notion page 3706ecd8-9e59-813a-b4c7-ecbc2c213fa8 ("ORA Data Source of Record (DSOR) — Master Workbook"). It defines read order, IDs, and the freshness rule. If anything below conflicts with that page, the page wins.

STEP 1 — READ THE LIVE WORKBOOK (system of record)
PRIMARY — Desktop Commander local read (cell-accurate, no truncation). The workbook is OneDrive-synced on Gabriel-Laptop at:
  C:\Users\Owner\OneDrive - Oxford Capital Partners\eric spreadsheets\Master Excel Template Company Wide -- Oxford.xlsx
  (Verified 2026-07-07/08 — do NOT use a "(1)"-suffix variant; that path is stale/ENOENT. If a future OneDrive re-sync reintroduces a "(1)" or "(2)" suffix folder — a known OneDrive collision artifact — re-verify with get_file_info before relying on either path.)
  1. Freshness: mcp__Desktop_Commander__get_file_info on that path → capture `modified` (= workbook lastModifiedDateTime) and the `sheets` array (should be 34 tabs). If the path is missing (sync gap), fall back to SECONDARY and flag it.
  2. Read each SoR tab cell-accurately with mcp__Desktop_Commander__read_file (sheet=<tab name>, optional range="Sheet!A1:Z99"). Returns exact JSON 2D arrays. Read the FULL tab. Do NOT rely on the SharePoint text render — it hard-truncates at ~100K chars and silently drops External Loans Summary / Portfolio Summary — Internal / Loan Index / Cash Data.
  KEY CELLS to lock: External Loans Summary — borrower total, lender block (negative = capital deployed), and the "Portfolio LTV" cell (net external debt ÷ Oxford value, distinct from 00_Home gross LTV). Portfolio Summary — Internal — per-loan Current Balance + PORTFOLIO TOTALS + top-concentration. Cash Data — the as-of date is MAX(header date row), NOT the Cash Balances summary A2 label. Cash Balances' embedded historical table also lags the current column by ~2 periods (diagnosed 2026-07-08 — newest balances get pasted into an existing older-dated row instead of a newly appended one; a `..._pre-A2fix_2026-06-09.xlsx` backup in `Documents\Claude\_backups` shows a prior fix attempt that didn't stick). Property NOI — portfolio totals row. Assumptions — all rates.
SECONDARY (fallback only) — Microsoft 365 connector read_resource with URI:
  file:///b!fogSrIGhzUeBSf98j4jg7JBJQDYJDw5Og7B2gKTH8HDkm61VkL_ZQYZmGfTNXL9f/01ABKEESVJPJNG6AC7F5DKUNFUHRCN5AUM
  Saved to a file with offset/limit paging — read fully in chunks; capture lastModifiedDateTime via sharepoint_search "Master Excel Template Company Wide Oxford". WARNING: this render truncates at ~100K chars; treat any tab past the cutoff as MISSING — flag it, do NOT silently reconstruct or carry forward.
Source-of-truth tabs: 00_Home, Property NOI, Master Tenant Rent Roll, Cash Balances, Cash Data, Loan Index, External Loans Summary, Portfolio Summary — Internal, Insurance Renewals, Assumptions.

STEP 2 — NO-OP GUARD
Fetch DSOR page §5. If the workbook lastModifiedDateTime is unchanged since the last recorded ingest, log a one-line no-op to the Operations Hub (32b6ecd8-9e59-81f2-b329-df3fd0e25062) and STOP — do not rewrite the dashboard or send email.

STEP 3 — EXTRACT CANONICAL METRICS
From the SoR tabs compute, at minimum: portfolio SF / value / NOI / DSCR / LTV / cap rate / equity / CoC (Oxford share and 100%); rent roll totals (tenant count, annualized & monthly rent, weighted $/SF, top tenant, top-5 concentration, WALT); external borrower & lender debt (balances, rates, maturities), internal loan book and concentration; cash by entity and total; insurance policy status counts and expirations (track per-policy status across runs — see STEP 6 escalation rule); lease-expiration windows. Reconcile to 00_Home headline figures (QC gate — note any variance > tolerance).

STEP 4 — REFRESH THE MIRROR (do NOT create duplicate databases)
a. Update the Portfolio Intelligence Dashboard (Notion page 3396ecd8-9e59-819c-a598-e55dc5581504): replace the metric tables and set the "Last refreshed" line to today with the workbook lastModifiedDateTime cited.
b. Write a dated archive page "Portfolio Metrics Snapshot — [date] (Master Workbook ingest)" under the Knowledge Base (3386ecd8-9e59-8166-af49-da066dc7ca14), same structure as prior snapshots.
c. If the ora-master-dashboard / ora-cash-position artifacts exist, refresh their numbers. Reliable channel: mcp__Desktop_Commander__edit_block in place on the artifact index.html (e.g. C:\Users\Owner\OneDrive - Oxford Capital Partners\Documents\Claude\Artifacts\<id>\index.html — no "(1)" suffix; verified 2026-07-08, that directory currently has no artifacts, so this step is a no-op) — the cowork Edit tool is blocked there (outside connected folders) and mcp__cowork__update_artifact requires a full faithful HTML reproduction. Patch the `const D = {…}` data object + header "As of" stamp.
d. Update DSOR page 3706ecd8-9e59-813a-b4c7-ecbc2c213fa8 §5 "Current state" with the new workbook lastModifiedDateTime and today's ingest date; append a §6 change-log line.

STEP 5 — PUBLICATION GUARD
For each Notion write, capture pages[0].id; retry once on failure; verify by title search. Apply the shared _shared\PUBLICATION_GUARD.md pattern if present.

STEP 6 — CONDITIONAL NOTIFICATION
Email if any of:
  (a) any Notion publication failed after retry, or
  (b) a QC reconciliation variance > tolerance, or
  (c) the workbook lastModifiedDateTime is itself > 14 days old (upstream not being updated), or
  (d) [added 2026-07-08] any Insurance Renewals policy has appeared in EXPIRED status for 3+ consecutive ingest runs (compare this run's expired policy list against the last 2 DSOR/Ops-Hub change-log entries by Policy #/RowID). As of 2026-07-07's run this condition is ALREADY MET for INS-FVC-PCKG, INS-FVC-BCL, INS-ETCPOA-PCKG, INS-ETCPOA-BCL, INS-1100RARIG-PCKG, INS-1100RARIG-BCL (expired since ≤2026-06-09, 4+ consecutive runs) and INS-3883LIVINGSTON-PCKG, INS-3883LIVINGSTON-BCL (expired since 2026-06-11, 3 consecutive runs as of 2026-06-22/07-07) — the next run that reaches this step should include these in the alert even if (a)-(c) are otherwise clean. Do not re-alert on the same policy every subsequent run once it has fired once under this rule — track "already escalated" via a note in the Ops Hub log line and only re-fire if newly crossing the 3-run threshold or after a gap.
Route via the SOLE send path `C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1` (write the body to a temp file via Desktop Commander `write_file`, then `-BodyFile`; Composio removed 2026-06-11, no fallback connector exists — on a non-zero COM exit retry once, then flag, do not halt). `-To "ggoldberg@oxfordra.net"` ONLY (no egoldberg cc — routing canon: only the Daily Brief cc's Eric). Subject on failure/escalation: "[ALERT] ora-master-workbook-ingest — [reason] — [date]". Do NOT use the legacy Rube namespace. On a clean run with no escalation, post a one-line success log to the Operations Hub only — no email.

Output format and tone per ORA Institutional Style Guide v1.0+.