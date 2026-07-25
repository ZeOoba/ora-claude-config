---
name: project-insurance-lapse-confirmed-real-2026-07-25
description: "The 9 expired/cancelled insurance rows flagged in the 2026-07-25 Daily Brief are a REAL live coverage gap, not a workbook-freshness artifact — verified against the live Master Workbook."
metadata: 
  node_type: memory
  type: project
  originSessionId: 72e9c1ee-b97a-4644-bd90-b89f2488af01
  modified: 2026-07-25T15:46:00.162Z
---

The 2026-07-25 Daily Brief hedged its insurance-expiration finding as "most likely a workbook-freshness artifact." That hedge is WRONG and should not be repeated. Verified 2026-07-25 by reading the live Master Workbook directly (not the snapshot):

- `Insurance Renewals` tab's Status column is a formula keyed to a named cell `Ins_AsOfDate` (`Assumptions!B44` = `=IF(B45="Auto (today)",TODAY(),IF(ISNUMBER(B46),B46,TODAY()))`). Mode (`B45`) = `"Auto (today)"`, override cell `B46` blank → **the formula runs off the live system clock, not a frozen date.**
- `EXPORT_InsuranceRenewals` (which feeds `oxford-command-center`'s `portfolio.json` insurance array) is a live cell-reference mirror of `Insurance Renewals` rows 11–35 — not a stale copy-paste.
- Both layers agree exactly with `portfolio.json`'s 9 flagged rows.

**Conclusion: 5 properties carry genuinely expired or cancelled coverage right now**, not a stale-snapshot false alarm:
- Sepich Portfolio / Fairground Village Center LLC — Package + BCL, expired 2026-02-03 (171 days). Workbook note: *"Will need to be rewritten to ESB at renewal"* — known, has a plan.
- Airport Rd, Easton MD (ETC POA) — Package + BCL, expired 2026-04-05 (110 days). **No note — no recorded plan.**
- 1100 Rarig Ave, Columbus OH — Package + BCL, expired 2026-03-19 (127 days). **No note — no recorded plan.**
- 3875-3883 E Livingston Ave, Columbus OH — Package + BCL, expired 2026-06-11 (43 days). **No note — no recorded plan.**
- 1851 South Club Dr (Solar) — cancelled effective 2025-05-30. Workbook note: *"CANCELLED … moved to another agent; confirm replacement coverage"* — known, unresolved.

**Why: Do not default to "probably stale" for a workbook-sourced flag without checking the actual formula chain.** This one had an `Ins_AsOfDate` toggle that could plausibly have been frozen (exactly the kind of thing that caused other dated defects this month) — checking it took one read of `Assumptions!B44:B46`; it does not appear to be checked elsewhere. Related: [[reference_delinquency_report_collection_status_blindspot]] (a different instance of the same "verify before assuming a static/frozen inference" pattern), [[reference_lease_date_detector_defects_2026-07-24]].

**How to apply:** Future daily briefs should report this as a live, real coverage gap requiring action, not hedge it as a possible artifact. Three properties (Airport Rd/ETC POA, 1100 Rarig, 3875-3883 Livingston) have zero recorded remediation — those are the ones needing an actual insurance-renewal push, not just monitoring. This memo is read-only investigation; no edits were made to the workbook (governed file, needs Gabriel's permission to write).
