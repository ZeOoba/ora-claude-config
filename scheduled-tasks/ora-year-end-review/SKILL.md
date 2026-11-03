---
name: ora-year-end-review
description: Annual (last business day on or before Feb 28, 12:20 ET) year-in-review of the prior fiscal year via annual-cycle, behind a 6-point preconditions gate; aborts to a status memo if books are not closed. Email ggoldberg only. Feb anchor per the 2026-04-28 correction (Dec 15 predates FY close). Re-registered 2026-10-30 on Gabriel's in-turn approval. [MODEL: UNVERIFIABLE | checked 2026-10-30]
---

ORA Year-End Review — review the prior fiscal year.

## 0. Run date, anchor and guards
- Compute the run date ONCE at start: `date '+%A %Y-%m-%d'`. Reuse that exact value everywhere. Target FY = run year − 1. Never run against an incomplete current year.
- WHY FEBRUARY: corrected 2026-04-28 from the original Dec 15, which fired before fiscal year-end and could never review a complete year. Late February allows prior-FY books to close.
- BUSINESS-DAY GUARD: this cron fires Feb 26, 27 and 28. Proceed only if today is the last Monday–Friday on or before Feb 28. Otherwise exit silently.
- IDEMPOTENCY GUARD: if `*_FY{FY}_Year-In-Review_v*.docx` or `*_FY{FY}_Year-End-Review_Status-Memo_v*.docx` already exists in `C:\Users\Owner\OneDrive - Oxford Capital Partners\Claude_Workspace\outputs\`, stop and report "already ran for FY{FY}". A late catch-up run in March still runs once.

## 1. Preconditions gate — 6 points (run first; abort if any fail)
1. FY anchor: target FY = run year − 1.
2. Books closed: QuickBooks is DESKTOP ONLY — locate per-LLC P&L / GL exports on SharePoint covering the full target FY and dated after Dec 31 of that year. Never QuickBooks Online, never Zapier, never ask to re-auth a QBO connector. Missing or partial-year exports = FAIL.
3. Loan Portfolio Tracker complete: Outstanding Balance, Maturity Date, Monthly Debt Service and Covenant Floor populated for every loan (Master Workbook / Notion).
4. Notion CapEx & Maintenance Log `5dfcc3ad532e4e5fbf8d512e2b69e317` has entries dated in the target FY.
5. Notion Acquisition Pipeline Tracker `bcfe4a037e614ac1a0bbc44174fa138b` filtered by Closed Date within the target FY (never created date).
6. The FY{FY} operating budget (from ora-annual-budget-kickoff, `*_FY{FY}_Operating-Budget_v*.xlsx` in outputs) located for actual-vs-budget; if absent, flag it — this point degrades the review to actuals-only rather than failing it.
If ANY of points 1–5 fails: ABORT. Write `{YYYY-MM-DD}_FY{FY}_Year-End-Review_Status-Memo_v01.docx` naming each failed precondition and what would clear it, email it (section 4), and stop. Never publish a data-empty review.

## 2. On pass — produce the review
Read and follow the `annual-cycle` skill, section "Year-In-Review" (repo `C:\Users\Owner\ora-skills\annual-cycle\SKILL.md`) — it owns the method: actuals vs budget by property and consolidated, AUM trajectory, capital deployed and capex completed, distributions, forward look. Data read order: live ORA Master Workbook on SharePoint FIRST; freshness canon = Notion page `3706ecd8-9e59-813a-b4c7-ecbc2c213fa8` (a mirror more than 7 days behind is STALE — label it). Notion quota errors: follow `notion-quota-fallback`.
Output: `C:\Users\Owner\OneDrive - Oxford Capital Partners\Claude_Workspace\outputs\{YYYY-MM-DD}_FY{FY}_Year-In-Review_v01.docx`, ORA Style Guide v1.0+, 16-point QC gate run and its result stated in the email.

## 3. Hard limits
- Internal draft only: no counterparty or LP sends, no money movement, no deploys.
- Read-only against the Master Workbook and every financial model; never change a governor constant (DSCR 1.25x, LTV 40% aggregate / 65% per-property).
- Never fabricate. Every gap goes in a "QUESTIONS FOR GABRIEL" section (question, why it matters, recommended default, options).
- Never name an active confidential deal (roster: `C:\Users\Owner\.claude\hooks\confidential-terms.json`).

## 4. Notion and email
- Notion: one summary page under Operations Hub `32b6ecd89e5981f2b329df3fd0e25062` titled `FY{FY} Year-End Review ({YYYY-MM-DD})` (or `… — Status Memo` on abort). If create-pages returns no page ID, look for the page (notion-fetch the Ops Hub parent for an exact-title child created at/after the call, then title search) before any retry; never blind-retry; after a grace-period/quota notice with no match, mark the Notion step UNVERIFIED.
- Email ONLY via `C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1` with `-To "ggoldberg@oxfordra.net"` (no Cc; Eric is re-added only on Gabriel's explicit instruction), subject `FY{FY} Year-End Review — draft ready ({YYYY-MM-DD})` or `FY{FY} Year-End Review — ABORTED, preconditions unmet ({YYYY-MM-DD})`, attach the DOCX, and pass `-DedupTaskId ora-year-end-review -DedupPeriodKey {YYYY-MM-DD}`. On non-zero exit: flag loudly in the Notion page and final report; do not halt.

## 5. Log and report
Append one entry via `python C:/Users/Owner/.claude/maintenance/append-event-log.py` with header `## {YYYY-MM-DD} — FY{FY} year-end review` (pass or abort, preconditions result, outputs). On exit 1 (malformed header), match the newest existing heading format; do not retry blindly.
Final report: run date, guard outcome, preconditions table, files written, Notion URL or UNVERIFIED, email exit code, QC result, QUESTIONS FOR GABRIEL.