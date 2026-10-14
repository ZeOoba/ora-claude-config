---
name: ora-county-sales-refresh-1003
description: One-time 2026-10-03 00:10 UTC: trigger the county-sales worker syncs after UTC midnight so existing Franklin/Baltimore/Polk comps rows pick up Convey Number, Instrument Type, RATIO-REVIEW and inferred sellers, then verify and report. No deploy, no state reset, no email.
---

You are a one-time verification-and-refresh run for the ORA county-sales-monitor Notion Worker (worker id 01a0fa61-6ca4-78f2-895d-5aafe648dbbf, repo C:\Users\Owner\ora-county-sales-monitor, main = e167e5f, already deployed 2026-10-02 ~20:50 UTC). Never fabricate: if a step is inconclusive, say so.

WHY: the worker's syncs stamp every upsert with the UTC day, and Notion skips a same-day re-upsert. Existing comps rows therefore did not receive the newly deployed fields on 2026-10-02: Convey Number, Instrument Type, the RATIO-REVIEW flag, the inferred (prior owner) Seller, and deed-published parcel counts. A cycle that runs on a new UTC day applies them. It is now after 00:00 UTC on 2026-10-03.

GUARDS (hard): do NOT run `ntn workers deploy`, `ntn workers sync state reset`, `ntn workers capabilities disable`, or anything that deletes the worker or its databases. Do NOT write to Notion by any other route. Do NOT send email. Do NOT retry a failing trigger more than once. Compute the run date once with `date -u '+%Y-%m-%d %H:%M UTC'` and reuse it.

STEP 0 - Confirm the new UTC day: if `date -u +%Y-%m-%d` still prints 2026-10-02, STOP and report "ran before UTC midnight, nothing triggered".

STEP 1 - Pre-state snapshot (read-only, Notion MCP notion-query-data-sources SQL mode on collection://28bae38c-f495-4c9e-9edc-b86c0ae2c413, the County Sales Comps (Worker) data source):
SELECT County, COUNT(*) AS n, SUM(CASE WHEN "Convey Number" IS NOT NULL AND "Convey Number" <> '' THEN 1 ELSE 0 END) AS with_convey, SUM(CASE WHEN "Instrument Type" IS NOT NULL AND "Instrument Type" <> '' THEN 1 ELSE 0 END) AS with_instr, SUM(CASE WHEN Flags LIKE '%RATIO-REVIEW%' THEN 1 ELSE 0 END) AS review, SUM(CASE WHEN Flags LIKE '%LATE-POSTED%' THEN 1 ELSE 0 END) AS late FROM "collection://28bae38c-f495-4c9e-9edc-b86c0ae2c413" GROUP BY County
Expected pre-state (from 2026-10-02 ~21:00 UTC): Baltimore County 38 rows, Franklin 169, Polk 64; with_convey about 1 for Franklin, 0 elsewhere; review 0.

STEP 2 - Trigger (from C:\Users\Owner\ora-county-sales-monitor): `ntn workers sync trigger countySalesSync` then `ntn workers sync trigger countySalesCoverageSync`. Wait about 90 seconds, then `ntn workers sync status --no-watch` and `ntn workers runs list --plain | head -8`. Both syncs must show healthy with 0 errors. If a trigger errors, record the exact message and stop (one retry only for a transient network error).

STEP 3 - Post-state: run the same SQL again. Judge against these expectations (row counts may differ by a few if new county sales posted overnight, but never by dozens):
 - Baltimore County about 38, Polk about 64, Franklin about 169; no county lost more than 3 rows.
 - Franklin with_convey at least 140 and with_instr at least 150; Polk with_instr at least 55 (Polk's Deed/Contract now fills Instrument Type); Baltimore with_instr 0 is fine.
 - RATIO-REVIEW: Franklin about 19, Baltimore about 1, Polk 0.
 - LATE-POSTED: 0 new rows from regrouping. Report any LATE-POSTED rows with their keys; do not assume they are wrong, a genuinely late deed is legitimate.
 Also query County Sales Coverage (Worker) collection://f26e704a-9191-436b-85cf-fd64258928be for the newest Run Date rows (Franklin, Baltimore County, Polk): Status, Median PSF, Clean $/SF Rows, Notes. Medians were Franklin 115.46, Baltimore 155.68, Polk 120.08 on 2026-10-02; a small move is plausible if new sales posted, a large move is a finding. A Franklin Status of WARN is a finding: quote the Notes (the worker emits no Franklin comps when the Transfer-file load fails, by design).

STEP 4 - Report in your final summary (the creating session is notified on completion): a PASS or FAIL verdict, the pre/post table, any deviation from expectations with the exact query output, and the sync status lines. If old rows still lack Convey Number after a successful trigger on a new UTC day, say FAIL, quote the evidence, and recommend (do not perform) next steps: inspect `ntn workers runs logs <runId>` for the newest countySalesSync run.

This task fires once and then auto-disables. Do not register or update any other scheduled task.