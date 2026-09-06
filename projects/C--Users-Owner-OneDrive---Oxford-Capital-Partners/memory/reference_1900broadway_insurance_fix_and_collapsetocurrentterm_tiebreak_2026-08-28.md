---
name: 1900broadway-insurance-fix-and-collapsetocurrentterm-tiebreak-2026-08-28
description: "1900 N Broadway insurance fixed in BOTH the warehouse (source_date tie-break bug found) AND the live ORA Master Workbook itself (Gabriel confirmed the write, executed via Excel COM); workspace-wide BCL relabel done in both places too. CLOSED 2026-09-02: portfolio.json re-extracted on schedule, both fixes now in the snapshot the Daily Brief reads."
metadata: 
  node_type: memory
  type: reference
  originSessionId: 82435ac0-53e4-4251-9e29-282fd4fdafef
  modified: 2026-08-28T21:13:50.349Z
---

Gabriel supplied the actual 2026-2027 Erie renewal certificates for 1900 North Broadway LLC
(package/ULTRAFLEX + umbrella) on 2026-08-28, same day the Daily Brief fired a CRITICAL
"policy expired" alert for both policies as lapsed 2026-08-27. Investigation found two distinct,
compounding data-quality bugs in `oxford-command-center`'s warehouse; a third thing (the actual
alert source) turned out to be the live ORA Master Workbook itself — Gabriel reviewed a drafted
cell-level edit and confirmed it ("Go ahead"), and it was executed the same session. **All three
are now fixed as of 2026-08-28**, except the Daily Brief's own cache (see UPDATE below).

**UPDATE (same session, after Gabriel's confirmation): the live workbook write is DONE, not
just drafted.** Executed via Excel COM (`ora-master-workbook-ingest` doctrine — never openpyxl),
17 cells across 11 rows, backed up first (`Documents\Claude\_backups\..._pre-1900BroadwayInsFix_
2026-08-28.xlsx`, SHA256 `1C4CE894F5728D54C82BAE5C9DE2AA134C1B428625ED4BBC8A08482EDA61D27F`),
each cell asserted against its pre-write value before writing. **Row numbers in the drafted
proposal (26/27) turned out to be stale** — 3 rows had been inserted into the Insurance Renewals
tab since the last structural reference (a Hartford GL/Umbrella/EPLI bundle at 9620 State 350),
shifting 1900 Broadway to rows 30/31 and every later BCL row down by 2-4. Caught by re-scanning
column A for exact slug matches live via COM immediately before writing, not by reusing the
drafted row numbers — **this is the reusable lesson: never trust a cached row number for this
tab, always re-resolve by slug at write time.** Post-write read-back confirmed the `K` status
formula recalculated 1900 Broadway from `EXPIRED` to `Current`. Full cell-by-cell diff:
[[event_log.md]] under 2026-08-28, "ORA Master Workbook write: 1900 Broadway insurance term flip
+ workspace-wide BCL relabel (Gabriel confirmed)".

**✅ CLOSED 2026-09-02 — the snapshot cache has regenerated; nothing here is still open.**
`ora-cc-snapshot-refresh`'s scheduled Monday run re-extracted `data/snapshots/portfolio.json` on
2026-09-02 (exit 0, clean, 0 data-quality flags) and both fixes landed in the snapshot the Daily
Brief actually reads: 1900 N Broadway's two Erie policies now carry `effective 2026-08-27` /
`expires 2027-08-27`, `status "Renew Now" -> "Current"` (package premium 11166 -> 11554, BCL
2271 -> 1992), and all 10 BCL rows read `"Business Catastrophe Liability (BCL)"`. No manual
re-extract was ever needed — the scheduled task cleared it, so the question below never had to be
put to Gabriel. Verified by reading the regenerated `insurance[]` directly, not inferred from the
diff. Commit `ad904b9` (stranded locally — the push was blocked by [[open-items-tracker.md#OI-205]]
branch protection, which does not affect the local artifact the Brief reads).

Original open item, superseded, kept for the reasoning:

**Still open: the Daily Brief will not reflect this until its cache regenerates.**
`server/brief/run.ts` reads `data/snapshots/portfolio.json`, a periodic cached extraction
(`scripts/extract-workbook.ts`) of the workbook — not the live file. The workbook fix does not
retroactively refresh that cache. Deliberately did NOT run `npm run extract` manually: portfolio.json
is git-tracked in a shared repo and its normal scheduled task auto-commits/pushes it, which was
outside what Gabriel confirmed for this task. **Ask him if he wants a manual re-extract to clear
tomorrow's brief before the next scheduled regen (`ora-cc-snapshot-refresh`, Mondays 06:15 ET, or
a more frequent drift-check task).**

Below is the original investigation (pre-confirmation), kept for the reusable lessons.

**Full detail and the exact SQL performed is in [[event_log.md]] under 2026-08-28** ("1900 N
Broadway insurance warehouse fix + workspace-wide BCL relabel") — this memory is the pointer +
the reusable lesson, not a restatement.

**Lesson 1 — `collapseToCurrentTerm`'s source_date-primary tie-break (`server/warehouse/
insurance-analysis.ts`'s `isMoreCurrent`) can be exploited by re-ingestion timing.** A row
carrying the CORRECT, later term can lose to a row carrying a STALE, earlier term simply because
the stale row was re-captured more recently. This happened here because the live workbook briefly
showed the new term early (before it incepted), self-corrected back to the old term with a
"RENEWAL ISSUED, NOT YET INCEPTED" note, and nobody flipped it forward again once the incept
date passed — so every re-ingest after that kept re-capturing the now-stale "corrected" state
with a newer `source_date`, permanently burying the correct row. **Not fixed** — flagged as a
general vulnerability, not just a 1900-Broadway-specific data error. Any property with a
similar near-incept-date correction pattern in the workbook is at risk of the same failure mode.

**Lesson 2 — the CRITICAL alert email is NOT sourced from the warehouse at all.**
`src/analytics/conditions.ts`'s `ins-lapsed-live-*` condition (the one that actually fires
CRITICAL emails) reads `snapshot.insurance[]` — Spine A, a live/cached read of the ORA Master
Workbook's Insurance Renewals tab (`data/snapshots/portfolio.json`, regenerated weekly by
`ora-cc-snapshot-refresh`, Mondays 06:15 ET) — never the `property_insurance_policies` warehouse
table. Fixing warehouse dates alone does NOT silence this alert; the workbook itself needed the
write. **Superseded by the UPDATE above: Gabriel confirmed, the workbook write is done** — the
gap remaining is only the Daily Brief's own snapshot cache, not the workbook.

**Lesson 3 — "Business Crime Liability (BCL)" is wrong everywhere it appears, confirmed against
the primary source.** Erie's own Schedule of Forms (umbrella policy PDF, page 3, form BCL,
edition 04/03) defines it as "BUSINESS CATASTROPHE LIABILITY POLICY"; the declarations page
itself is titled "ERIE INSURANCE EXCHANGE BUSINESS CATASTROPHE POLICY". All 19 warehouse rows
across all 10 properties carrying this label were Erie policies with the identical mislabel —
relabeled workspace-wide in the warehouse. The label is workbook-authored raw text
(`server/workbook/parse.ts:1133`, `coverage: str(row(ws, r, 4))` — no code-side dictionary), so a
warehouse-only fix would have been cosmetic and silently overwritten by the next re-ingest —
**superseded by the UPDATE above: all 10 BCL rows' D column were also relabeled in the live
workbook itself**, so this one is fixed at the actual source, not just cosmetically.

**Not touched, already tracked:** [[reference_alert_engine_duplicate_emails_diagnosis_2026-08-11]]'s
`property_id` slug-vs-property-id mismatch (0 of 14 match) — reconfirmed still true, still open as
[OI-125](open-items-tracker.md#OI-125), LOW severity, deliberately deferred with an auditable path
already documented in-file. Out of scope here.

**How to apply:** before trusting ANY "current" read of `property_insurance_policies` for a
property with a recent renewal near its incept date, don't assume the highest-`source_date` row
is the correct one — check whether an older-`source_date` row actually carries a later
`effective_date`/`expiration_date` (a sign of exactly this tie-break trap). And before treating a
Command Center insurance CRITICAL alert as warehouse-fixable, check whether the firing condition
is `src/analytics/conditions.ts` (Spine A / live workbook) vs `server/warehouse/
insurance-conditions.ts` (Spine B / warehouse) — only the latter is fixable without a DSOR write.
