---
name: ora-annual-budget-kickoff
description: Annual (first business day of Nov, 10:35 ET) draft of next fiscal year's per-property and consolidated operating budget via the annual-cycle skill; xlsx + memo to /outputs, Ops Hub summary, email to ggoldberg only. Seasonal; re-registered 2026-10-30 on Gabriel's in-turn approval. [MODEL: UNVERIFIABLE | checked 2026-10-30]
---

ORA Annual Budget Kickoff — draft the next fiscal year's operating budget.

## 0. Run date and guards
- Compute the run date ONCE at start: `date '+%A %Y-%m-%d'`. Reuse that exact value in every title, filename, subject and body. FY = run year + 1.
- FIRST-BUSINESS-DAY GUARD: this cron fires on Nov 1, 2 and 3. Proceed only if today is the first Monday–Friday of November (Nov 1 if a weekday; otherwise the following Monday). Otherwise exit silently.
- IDEMPOTENCY GUARD: if a file matching `*_FY{FY}_Operating-Budget_v*.xlsx` already exists in `C:\Users\Owner\OneDrive - Oxford Capital Partners\Claude_Workspace\outputs\` (or the email below is already in Sent Items), stop and report "already ran for FY{FY}".
- If the app was closed and this is a catch-up run later in November, still run once (the idempotency guard prevents duplicates).

## 1. Procedure
Read and follow the `annual-cycle` skill, section "Annual Budget Assembly (November)" — that skill owns the method; do not restate or improvise it. Source paths: repo `C:\Users\Owner\ora-skills\annual-cycle\SKILL.md`. Use `capex-budgeting` for the capex layer and `tenant-intelligence` for renewal probabilities, as that skill directs.

## 2. Data sources (read order — never fabricate)
1. Live ORA Master Workbook on SharePoint FIRST for firm figures; read-order and freshness canon = Notion page `3706ecd8-9e59-813a-b4c7-ecbc2c213fa8`. A mirror more than 7 days behind is STALE — label it, never present as current.
2. QuickBooks is DESKTOP ONLY: use the latest QuickBooks/property P&L exports on SharePoint (TTM and trailing 24 months by property and GL). Never QuickBooks Online, never Zapier, never ask to re-auth a QBO connector.
3. Notion Tenant Database `8dbbaec0` — rent steps, expirations, renewal status for the budget year.
4. Notion Acquisition Pipeline Tracker `bcfe4a037e614ac1a0bbc44174fa138b` — deals expected to close inside FY{FY}; show them as a separate scenario line, never blended into base NOI.
5. Notion CapEx & Maintenance Log `5dfcc3ad532e4e5fbf8d512e2b69e317` plus `capex-budgeting` for next-year capex.
6. Current loan schedules (Master Workbook) for debt service.
If a Notion query hits a quota/usage limit, follow the `notion-quota-fallback` skill.

## 3. Hard limits
- Do NOT modify any existing financial model, the Master Workbook, or any governor constant (DSCR 1.25x, LTV 40% aggregate / 65% per-property). This task only creates a new draft workbook and memo.
- Never fabricate a figure. Any missing input becomes a labeled gap in the workbook AND an entry in a "QUESTIONS FOR GABRIEL" section (question, why it matters, recommended default, options).
- Never name an active confidential deal (roster: `C:\Users\Owner\.claude\hooks\confidential-terms.json`) anywhere outside the internal workbook.

## 4. Outputs
- Workbook: `C:\Users\Owner\OneDrive - Oxford Capital Partners\Claude_Workspace\outputs\{YYYY-MM-DD}_FY{FY}_Operating-Budget_v01.xlsx` (per-property tabs + consolidated; revenue, OpEx, NOI, capex, debt service, cash flow before distributions; a Sources & Gaps tab). Use the xlsx skill; ORA Style Guide v1.0+; run the 16-point QC gate and record the result in the workbook.
- Executive summary memo (DOCX) beside it, same naming with `_Memo_v01.docx`.
- Notion: one summary page under Operations Hub `32b6ecd89e5981f2b329df3fd0e25062` titled `FY{FY} Operating Budget — Draft ({YYYY-MM-DD})`. If create-pages returns no page ID, look for the page (notion-fetch the Ops Hub parent for an exact-title child created at/after the call, then title search) before any retry; never blind-retry. After a grace-period/quota notice with no match, do not retry — mark the Notion step UNVERIFIED in the email.

## 5. Email (internal, pre-authorized)
Send ONLY via `C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1` with `-To "ggoldberg@oxfordra.net"` (no Cc — the egoldberg cc is sanctioned for ora-am-brief alone), `-Subject "FY{FY} Operating Budget — draft ready ({YYYY-MM-DD})"`, body = executive summary + file paths + QUESTIONS FOR GABRIEL, attach the memo DOCX, and pass `-DedupTaskId ora-annual-budget-kickoff -DedupPeriodKey {YYYY-MM-DD}`. On non-zero exit: flag loudly in the Notion page and final report; do not halt.

## 6. Log
Append one entry via `python C:/Users/Owner/.claude/maintenance/append-event-log.py` with header `## {YYYY-MM-DD} — FY{FY} budget kickoff draft` stating outputs, QC result, and gap count. On exit 1 (malformed header), match the newest existing heading format; do not retry blindly.

## 7. Final report
Run date, guard outcome, files written, Notion page URL or UNVERIFIED, email exit code, QC gate result, and the QUESTIONS FOR GABRIEL list.