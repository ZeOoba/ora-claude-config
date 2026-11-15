---
name: ora-rep-hours-monthly
description: Monthly real estate professional (REP) hour-log check — tallies the Notion REP Hour Log year-to-date per person against the 750-hour, more-than-half and 500-hour tests, and nudges for missing entries. Emails ggoldberg@oxfordra.net only. [MODEL: claude-opus-5-5 | set 2026-10-15]
---

# ORA monthly REP hour-log check

Why it exists: REP status keeps roughly $1.2M a year of rental income out of NIIT (about $45K a year) and made the 2024 Northwood loss deductible. The IRS sustains REP claims on contemporaneous logs, not reconstructions.

## Run date and guard
Compute once: `date '+%A %Y-%m-%d'`. Exit silently unless today is the first weekday (Mon–Fri) of the month.

## — DOUBLE-FIRE ENTRY GUARD (runs after the first-weekday guard above: a skipped fire must not claim)
python C:/Users/Owner/.claude/scheduled-tasks/_shared/block-sentinel.py claim --task ora-rep-hours-monthly --block main --run-id <run_id> --period month --ttl-min 30
- Exit 10 = this month already completed; Exit 11 = another fire is live. Stand down: no Notion query or file write, no email; report a NORMAL skip.
- Exit 0 = proceed.
After the run finishes (after the email sends): `... block-sentinel.py complete --task ora-rep-hours-monthly --block main --run-id <run_id> --period month --email-sent-at <ISO8601>`. On abort, and on a send that ends in failure (exit 5, or exit 2 or 4 once its single repeat is spent; exit 6 is the exception, see the send step): `... fail ... --error "<what broke>"` (never `complete` without a real `--email-sent-at`, except exit 6: see the send step when an email was owed). Only the claim holder calls complete/fail. ALWAYS pass `--period month`.

## Data source
Notion database "REP Hour Log — Real Estate Professional Substantiation" under the Operations Hub.
Data source: `collection://30b8f133-2286-41bf-82d2-bb76109527c1`. Columns: Entry, Date, Person (Eric / Rebecca / Gabriel), Hours, Property / activity, Category, Counts toward REP (checkbox), Evidence, Month.
Exclude every row whose Entry matches `^ZZ[\s._-]*TEST` (case-insensitive, leading whitespace stripped): the fleet test-artifact sentinel.

## Steps
1. Query all rows dated 1/1 of the current year through the last day of the prior month.
2. Per person, compute year-to-date:
   - REP hours = sum of Hours where Counts toward REP is checked;
   - non-REP hours = all other Hours (non-real-estate work, investor-type work);
   - share = REP hours / (REP + non-REP hours);
   - pace = REP hours ÷ months elapsed × 12 (projected year-end).
   - hours by Property / activity (the grouped-rental 500-hour material-participation test).
3. Flag per person: projected REP hours under 750; share at or under 50%; prior month with zero entries; any entry with an empty Evidence field.
4. Email via Outlook COM `C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1`, TO `ggoldberg@oxfordra.net` ONLY.
   Subject: `REP hours YTD <run date> — Eric <x> h · Gabriel <y> h · Rebecca <z> h (750 needed)`.
   Body: one table per person (YTD hours, pace, share, flags), then "Months with no entries", then QUESTIONS FOR GABRIEL. On exit 2 or 4: retry once, then flag in the Notion completion row; do not halt. On exit 5 or 6 (or any code other than 2 or 4) do NOT retry: flag it loudly in the run summary and in the Notion completion row and the guard close-out, and never resend (exit 6 = send state unknown — the message MAY have gone out), per rules.md §2. Close the guard `fail` on exit 5, but on exit 6 close it `complete` with no `--email-sent-at` (never `fail`: a same-day re-fire would send the message again).
5. In the January run, also produce the prior full-year summary as `Taxes Estimated + Returns\outputs\<run date>_REPHours_TY<prior year>_Summary_v01.md` for the preparer.

## Never
- Never add, edit or back-fill hour entries. Logging is the taxpayer's own act; this task only reads and reports.
- Never state that a person qualifies or fails. Report the numbers against the tests and leave the determination to the preparer.
