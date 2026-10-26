---
name: ora-loan-balance-check
description: Monthly (21st, 11:35 AM ET) report-only loan balance check: recomputes expected balances for six Loans External notes from documented lender terms, compares them with the Notion Loans DB, and emails differences, the 3540 LTV watch and near maturities to ggoldberg only. Never writes to Notion, the workbook or the terms file. [MODEL: UNVERIFIABLE | checked 2026-09-21]
---

ORA Loan Balance Check (v1.0, created 2026-09-21 at Gabriel's direction: monthly, report-only).

PURPOSE: catch stale loan balances before anyone relies on them. On 2026-09-21 the Notion Loans DB held balances up to five payments stale (Information Lane, 3540, Red Branch, Restoration). This task recomputes what each balance SHOULD be from documented terms and reports differences. It is REPORT-ONLY: never edit a Notion loan record, the Master Workbook, or the terms file. If a difference is found, state it; Gabriel or a supervised session decides.

STEP 0 - DOUBLE-FIRE ENTRY GUARD (first action, before any Notion or file call).
python C:/Users/Owner/.claude/scheduled-tasks/_shared/block-sentinel.py claim --task ora-loan-balance-check --block main --run-id <run_id> --period month --ttl-min 30
- Exit 10 (this month's run already completed) or exit 11 (another fire is live): stand down as a NORMAL skip. Send nothing, touch neither Notion nor Outlook, and call neither complete nor fail.
- Exit 0: proceed. ALWAYS pass --period month on every sentinel call.
When the run's email has been sent: python C:/Users/Owner/.claude/scheduled-tasks/_shared/block-sentinel.py complete --task ora-loan-balance-check --block main --run-id <run_id> --period month --email-sent-at <ISO8601>
If the run aborts: python C:/Users/Owner/.claude/scheduled-tasks/_shared/block-sentinel.py fail --task ora-loan-balance-check --block main --run-id <run_id> --period month --error "<what broke>"

STEP 1 - PULL THE NOTION LOANS DB (read-only).
Use the Notion MCP notion-query-data-sources tool (SQL mode) on data source collection://05b0012c-453c-45f5-a7c6-16efd2e3013e:
SELECT "Loan Name" AS name, "Outstanding Balance" AS balance, "date:Maturity Date:start" AS maturity FROM "collection://05b0012c-453c-45f5-a7c6-16efd2e3013e" ORDER BY "Loan Name"
Write the rows as a JSON list [{"name":..., "balance":..., "maturity":...}] to %TEMP%\ora-loan-balance-notion-<YYYY-MM-DD>.json (every <YYYY-MM-DD> / <today YYYY-MM-DD> slot in this task, including the Step 3 subject and the Step 4 row date, = the run date computed once at run start with `date '+%A %Y-%m-%d'`, date part in every date slot, reused verbatim) with a DIRECT file write (never a shell here-string). If Notion is unreachable, skip --notion-json in Step 2 and put "Notion unreachable, expected balances only" in the subject.

STEP 2 - RUN THE CALCULATOR.
C:/Users/Owner/AppData/Local/Programs/Python/Python313/python.exe C:/Users/Owner/.claude/maintenance/loan_balance_check.py --as-of <today YYYY-MM-DD> --notion-json <the json from Step 1> --html-out %TEMP%\ora-loan-balance-<YYYY-MM-DD>.html --md-out "C:\Users\Owner\OneDrive - Oxford Capital Partners\Claude_Workspace\02_Outputs\<YYYY-MM-DD>_LoanBalanceCheck_Report_v01.md"
It reads C:\Users\Owner\.claude\data\loan-terms.json (lender schedules and executed-note terms, last verified 2026-09-21). Exit 2 = unreadable input: go to the failure path in Step 5. Do NOT hand-compute or "fix" balances.

HOW TO READ THE REPORT (do not editorialize beyond this):
- "Differences": Notion balance vs expected, tolerance $5. A difference on the Restoration Church note usually means the latest installment (due the 20th) was assumed received but not yet recorded; say so and ask Gabriel to confirm receipt. The Restoration note is a receivable held by Eric Goldberg and the Lynn S. Abrams Trust (assigned 10/2025); a payoff was pending at creation (AWO Title).
- "Watch list": (1) 3540 E. Fifth LTV on the lender's 1/2025 appraisal is above ORA's 65% per-property ceiling; Gabriel decided on 2026-09-21 to ACCEPT AND MONITOR, so report the current figure every month as informational, never as an alarm. (2) Information Lane maturity is unresolved (form Note reads "__10, 2031" vs Symetra's schedule 12/10/2030); repeat the line until the signed Note is read. (3) Any note maturing within 18 months.
- "Notes": unmodeled Notion records (internal loans: Rarig, Northwood/EGFLLC, Livingston, EGFLLC-from-Oxford, Muirkirk-from-EG) are intentionally not checked; a terms file older than 120 days is flagged for re-verification.

STEP 3 - EMAIL (ggoldberg@oxfordra.net ONLY, no cc, routing canon).
Send the HTML report via C:/Users/Owner/.claude/scheduled-tasks/_shared/send-via-outlook.ps1 -To ggoldberg@oxfordra.net -Subject "ORA Loan Balance Check -- <YYYY-MM-DD> -- <N> difference(s)" -BodyFile <the html from Step 2>. The email is sent every month (the LTV watch is a standing report). On exit 2 or 4: retry once, then flag loudly in the Ops Hub row (Step 4) and do NOT halt. On exit 5 or 6 (or any code other than 2 or 4) do NOT retry: flag it loudly in the run summary and in the failure record named above, and never resend (exit 6 = send state unknown — the message MAY have gone out), per rules.md §2.

STEP 4 - OPS HUB ROW.
Post one row to the Notion Operations Hub (parent page 32b6ecd8-9e59-81f2-b329-df3fd0e25062): the date, the number of differences, the watch-list count, and the email send status. This is the only Notion write this task makes. If the create errors or returns a grace/quota notice, look for it — `notion-fetch` the parent for a child carrying this run's date, then search by that date + task name (search lags: a miss alone is not proof) — a match created at/after the create call is this run's row, use it; never blind-retry a create (it produced a duplicate). After a grace/quota notice with no match, do not retry: the row is UNVERIFIED — say so in the run report and continue to Step 5. Quota errors → `notion-quota-fallback` skill.

STEP 5 - CLOSE.
Run the Step 0 complete command with --email-sent-at. On any abort run the fail command. Report only what happened; never fabricate a balance or a payment.

MAINTENANCE (not part of a scheduled run): the terms file is refreshed ONLY from lender documents in a supervised session, when a loan is paid, refinanced, assigned or re-documented. Tests: python C:/Users/Owner/.claude/maintenance/_tests/test_loan_balance_check.py