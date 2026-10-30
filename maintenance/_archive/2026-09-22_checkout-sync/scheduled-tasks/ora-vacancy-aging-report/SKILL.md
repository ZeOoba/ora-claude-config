---
name: ora-vacancy-aging-report
description: Weekly Tuesday 08:20 ET accountability report — every vacant or notice-to-vacate unit in the live Master Workbook rent roll, ranked by days vacant and $ at stake (last rent x days vacant / 30), addressed to the responsible PM/leasing contact where known. Read-only against the workbook; writes nothing anywhere. ggoldberg-only email via Outlook COM, sent every run (accountability tool, not an exception report). Companion to ora-lease-expiration-brief (LAMS, upcoming expirations) — this covers units already vacant or under notice. v1.1 2026-09-18: PM mapping extended to all properties via Outlook/SharePoint search, corroborated against oxford-command-center's property_master registry (7 of 10 properties now resolved: 3 mapped 08-06, 4 mapped 09-18, 2 confirmed self-managed, 1 still unmapped). v1.2 2026-09-22: 1900 N Broadway now maps to BOTH Steve Seh (CRC Property Manager) and George Renehan (CRC Controller, ops/finance/operating statements) per Gabriel ruling — no longer "PM contact unconfirmed". [MODEL: claude-sonnet-5 | set 2026-09-18]
---

ORA VACANCY AGING REPORT — weekly run (v1.0, 2026-09-18). Unattended scheduled run for Oxford Realty Advisors (ORA). Purpose: hold third-party property managers and listing brokers accountable for vacant suites. Gabriel does not lease space himself — leasing is done by PMs/brokers — so this is a report to escalate to them, never a lead-generation tool, and never drafts tenant-facing content.

HARD LIMITS: read-only against the workbook. No writes to HubSpot, Notion, the workbook, or any tenant/broker-facing surface. No drafts, no Outlook drafts to PMs — this is an internal report to Gabriel only. Never fabricate a PM contact — if none is on file for a property, say so plainly.

STEP 0 — DOUBLE-FIRE ENTRY GUARD (added 2026-09-18; run before STEP 1). Same overnight-offline catch-up-burst exposure documented fleet-wide (README-DOUBLE-FIRE-GUARD.md) — this task emails on EVERY run (STEP 6), including the STEP 1c fail-loud gate path, so a second fire in the same window would send a duplicate report or a duplicate gate-failure alert. Run this first:

```
python C:\Users\Owner\.claude\scheduled-tasks\_shared\block-sentinel.py claim --task ora-vacancy-aging-report --block main --run-id <run_id> --ttl-min 30
```

- **Exit 10** → today's report already sent. Log `BLOCK_MAIN_ALREADY_COMPLETE_TODAY`, do not re-read the workbook or send again, and report it as a NORMAL skip citing the earlier run's email.
- **Exit 11** → another fire is live. Stand down identically.
- **Exit 0** → proceed to STEP 1.

**Only the run that holds the claim may call `complete` or `fail`.** A run that stood down (exit 10 or 11) calls neither. Full contract: `_shared/README-DOUBLE-FIRE-GUARD.md`. Do not "fix" a double-fire by retiming this task's cron — the burst is documented fleet-wide behavior; the guard belongs here.

STEP 1 — READ THE SOURCE OF RECORD (live workbook, read-only). File: `C:\Users\Owner\OneDrive - Oxford Capital Partners\eric spreadsheets\Master Excel Template Company Wide -- Oxford.xlsx`, tab `Master Tenant Rent Roll`. Row 2 holds "As of <Month D, YYYY> │ N tenants │ …"; row 5 is the header (Property, Tenant Name, Unit, Company, Sq Ft, Monthly Rent, Rent / SF, Lease Start, Lease End, Escalation Date, Escalation %, Status, Notice to Vacate, Annual Rent, Esc. Exception, Occupancy Class).
 a. PRIMARY: Python openpyxl `load_workbook(path, data_only=True, read_only=True)` — never save. Full interpreter `C:/Users/Owner/AppData/Local/Programs/Python/Python313/python.exe`, `PYTHONIOENCODING=utf-8`.
 b. FALLBACK on PermissionError (file locked by a live Excel session, common): attach READ-ONLY to the running instance via PowerShell `[Runtime.InteropServices.Marshal]::GetActiveObject('Excel.Application')`, find the workbook whose Name starts "Master Excel Template Company Wide", read `Worksheets('Master Tenant Rent Roll').UsedRange.Value2` (dates are Excel serials, epoch 1899-12-30). Never call Save, never set a cell, never open a second Excel. Record `Workbook.Saved` before and after; report if it flips.
 c. FAIL-LOUD GATE: if neither path reads the tab, OR the row-2 "As of" date is more than 7 days before today, OR the parsed row count is outside 100–200 → run the pre-send probe below, then send the email anyway with subject `[ACTION] Vacancy report could not trust the workbook — <today's date>` stating exactly what failed, close the STEP 0 claim with `complete --email-sent-at <ISO8601>`, and stop — do not guess at vacancy from a stale or partial read.

    **PRE-SEND SENT-ITEMS PROBE (mandatory, immediately before this send).** Layer 2 of the STEP 0 guard, dated stem:
```
powershell -ExecutionPolicy Bypass -File C:\Users\Owner\.claude\scheduled-tasks\_shared\outlook-sent-probe.ps1 -SubjectFile "<temp .txt containing exactly: Vacancy report could not trust the workbook - <today's date>>"
```
    Exit 10 → do NOT send, log `MAIN_EMAIL_ALREADY_IN_SENT_ITEMS`, and still call `block-sentinel.py complete` (no `--email-sent-at`) so Layer 1 re-converges. Exit 1 → fail open: send anyway, and note the probe gap in the email body.
 Temp files only under `C:\Users\Owner\AppData\Local\Temp\ora-vacancy-report\`. GATE-SAFETY: never put the strings `website-canonical` or `oxford-site` in a shell command or path — a site-write guard blocks them.

STEP 2 — IDENTIFY VACANCY ROWS. A row is IN SCOPE if EITHER: (a) `Occupancy Class` contains "Vacant" (any of: available for lease, notice given, lease expired) or "Holdover" — these ARE currently vacant/unstable, OR (b) `Notice to Vacate` = "Yes" regardless of Occupancy Class — these are COMING vacancies. Exclude common-area rows (no tenant name, e.g. signage/easement rows with SF = 0) from the main table; list them separately under "Non-suite items" only if they carry Notice to Vacate = Yes. **Standing exclusion (Gabriel, 2026-09-18): Adkins Towing (2207 Northwood A8) is intentionally month-to-month at a below-market rate — do not list as vacant/at-risk even though Status may read "Expired."** Anibal Morales (2207 Northwood C4) IS in scope — he is month-to-month AND under notice from ORA, so he is a genuine coming vacancy.

STEP 3 — COMPUTE, per row:
 - Days vacant: for `Occupancy Class` containing "Vacant" — today minus `Lease End` (or, if `Lease End` is blank, flag "vacancy start date unknown — do not compute"). Negative values (Lease End in the future) mean not yet vacant; report those separately under "Vacating soon" using days-until instead of days-vacant.
 - Last rent / SF and last monthly rent, from the row's own Monthly Rent and Rent/SF (this is the PRIOR tenant's rate — the row is not currently paying it; label clearly as "last collected rate", never as current income).
 - Annualized exposure: last monthly rent × 12. Sum this across all rows in scope for a portfolio total.
 - SF.

STEP 4 — PROPERTY → PM/LEASING CONTACT MAPPING. Use exactly this mapping (from `memory/people.md`; the first three confirmed 2026-08-06, the remainder confirmed 2026-09-18 by Outlook/SharePoint search, evidenced by recurring correspondence rather than an executed management agreement — none was found for any property in this list); do not invent a contact for any property not listed:
 - Morrison Rd, 1100 Rarig Ave, 2800/2802/2822 Banwick Rd, 3034 Westerville Rd, 3540/4595/4601 E 5th Ave (Columbus OH — all Kohr Royer Griffith per `oxford-command-center` finance.sqlite `property_master.property_manager`, which also lists "Sepich" as a KRG property not yet identified in ORA's own naming) → Paul Trautman, Kohr Royer Griffith, Pault@KRGRE.com, P 614-228-5547 / D 614-255-9218
 - 2203-2207 Northwood Dr (Salisbury MD) → Brady Smith, SVN, brady.smith@svn.com
 - 3875-3883 E Livingston Ave, 2002/2018/2022 Zettler Rd (Columbus OH) → Matthew Osowski SIOR, NAI Ohio Equities, mosowski@ohioequities.com, 614-629-5229
 - 29000 Information Lane (Easton MD, aka "Easton Technology Center") → Civita M. Peters, Director of Portfolio Management, Thomas Park Management, civita.peters@thomas-park.com, (c) 410-299-6235 / (o) 410-280-0220 (cc colleague Tiffanie Dessau, tiffanie.dessau@thomas-park.com). Leasing agent: Trent Spicer-Davis, SVN, trent.spicerdavis@svn.com — transactional, not the PM.
 - 9050 Red Branch Rd (Columbia MD) → Steve Seh, CRC Commercial / Community Realty Company, sseh@crc-commercial.com — operational PM. Leasing/accounting contact at the same firm: Heather Applegarth, happlegarth@crc-commercial.com (Gabriel-supplied 2026-09-18, Outlook-verified same day — active two-way thread through 2026-09-09; her own signature reads "Director of Lease Administration / Commercial Property Manager," a fuller title than "leasing/accounting" — flag, don't silently relabel her as a second PM). (Separately, George Renehan, Controller, GRenehan@crc-commercial.com, 301-345-3334, is CRC's cross-portfolio accounting contact — do not present him as the PM.)
 - 9620 State 350 / 350 Hwy (Raytown MO) → Garrett Alejos, Property Manager, Peak Real Estate, galejos@peakrep.com, (913) 202-2155 (superseded number; do not use the earlier 913-788-0277). Leasing agent: Wyatt Palmer, wpalmer@peakrep.com, (913) 230-3100 (Gabriel-supplied 2026-09-18, Outlook-verified same day — active two-way thread through 2026-09-17, signature confirms title/firm/phone).
 - 1900 North Broadway (Baltimore MD) → CRC Commercial (same firm as Red Branch) — TWO contacts, both correct (Gabriel ruling 2026-09-22): Steve Seh, Property Manager, CRC Commercial, sseh@crc-commercial.com — the property-level PM and the escalation line for vacancy; and George Renehan, Controller, CRC Commercial, GRenehan@crc-commercial.com, 301-345-3334 — ops/finance/operating statements. List both on this row, each with his role; do not collapse Renehan into "the PM" or drop either.
 - 401 Sunburst Hwy (Cambridge MD), 7658 Fishel Dr N → SELF-MANAGED, confirmed by `oxford-command-center` finance.sqlite `property_master.property_manager = null` for both (corroborated for 401 Sunburst by the Rent Manager/FVC/River Rd platform grouping). Contact = "Self-managed by Gabriel — no PM to notify"; still list the vacancy, just without a PM escalation line.
 - Any OTHER property not listed above → contact = "PM NOT ON FILE — confirm with Gabriel"; do not guess, do not reuse a nearby property's contact.
 If a vacant row's property does not exactly match one of the mapped name patterns above (allow for minor punctuation/suite differences, e.g. "2207 Northwood" matches "2203-2207 Northwood Dr"; "Easton Technology Center" matches "29000 Information Lane"), treat it as unmapped rather than force a match.

STEP 5 — REPORT. Sections, in this order:
 1. Summary line: total units in scope, total SF, total annualized exposure (sum of last-collected rent), count with no known PM contact.
 2. "Currently vacant" table, sorted by days vacant descending (unknown-start rows last): property | unit | SF | days vacant | last rent/SF | last monthly rent | occupancy class | PM/leasing contact.
 3. "Vacating soon" table (Notice to Vacate = Yes, not yet vacant OR future Lease End), sorted by days-until ascending: property | unit | SF | vacate/lease-end date | days until | current monthly rent | PM/leasing contact.
 4. "No PM contact on file" — the distinct list of properties with an unmapped vacancy this run, so the gap itself is visible and someone can fix the mapping.
 5. One line noting Adkins Towing was excluded by standing ruling, so the exclusion is auditable, not silent.
 Plain facts, no recommendations on re-leasing strategy or rent — that is Gabriel's and the PM's call, not this task's. Every figure traces to the workbook row that produced it.

STEP 6 — SEND. Email every run (this is a standing accountability report, not an exception report — silence would look identical to "no vacancies," which is never true for a real portfolio, so absence of email is not a valid healthy-state signal here).

**PRE-SEND SENT-ITEMS PROBE (mandatory, immediately before this send).** Layer 2 of the STEP 0 guard, dated stem `Vacancy Report <date>` (the subject's dynamic tail — unit/dollar counts — varies run to run, so the stem excludes it):
```
powershell -ExecutionPolicy Bypass -File C:\Users\Owner\.claude\scheduled-tasks\_shared\outlook-sent-probe.ps1 -SubjectFile "<temp .txt containing exactly: Vacancy Report <date>>"
```
Exit 10 → do NOT send, log `MAIN_EMAIL_ALREADY_IN_SENT_ITEMS`, and still call `block-sentinel.py complete` below (with `--email-sent-at` from the earlier send) so Layer 1 re-converges. Exit 1 → fail open: send anyway, and note the probe gap in the email body.

TO `ggoldberg@oxfordra.net` ONLY, never cc — via the sole send path `C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1`. On non-zero exit: retry once; if it still fails, there is no Notion fallback for this task — instead append one line to `C:\Users\Owner\.claude\scheduled-tasks\ora-vacancy-aging-report\state\run-log.jsonl`: `{date, workbook_as_of, in_scope_count, total_annualized_exposure, email_sent:false, error:"<what failed>"}` so `automation-health-monitor`/`ora-task-integrity-guard` can still find evidence this run executed even without an email. Subject: `Vacancy Report <date> — N units, $X annualized, M with no PM on file`. On a normal send, also append the same JSON line with `email_sent:true` and no `error` field.

Close the STEP 0 claim on whichever branch fired:
```
python C:\Users\Owner\.claude\scheduled-tasks\_shared\block-sentinel.py complete --task ora-vacancy-aging-report --block main --run-id <run_id> --email-sent-at <ISO8601>
```
On the send-failed-after-retry branch (run-log appended, no email), omit `--email-sent-at` — the run-log entry is this run's durable evidence in place of an email, same convention as a legitimate no-send completion. If the run aborts before reaching either branch, call `fail --task ora-vacancy-aging-report --block main --run-id <run_id> --error "<what broke>"` instead so the claim does not strand at IN_PROGRESS for the full TTL.

QUESTIONS FOR GABRIEL: if a workbook row's Occupancy Class or Notice-to-Vacate combination does not fit STEP 2's rule cleanly, list it under a "Needs a rule" note in the email rather than guessing.