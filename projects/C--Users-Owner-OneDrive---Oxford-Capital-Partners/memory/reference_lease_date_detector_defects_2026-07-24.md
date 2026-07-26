---
name: reference-lease-date-detector-defects-2026-07-24
description: "Two detector defects found 2026-07-24 — wrong lease dates in Command Center CRITICAL alerts (root cause = row-position-derived lease IDs, NOT conditions.ts), and tenant_db_snapshot_diff.py false positives across a day boundary (FIXED)."
metadata: 
  node_type: memory
  type: reference
  originSessionId: e3f980f6-f186-4928-ba79-212963641f99
  modified: 2026-07-24T23:51:05.462Z
---

Both surfaced during the 2026-07-24 `ora-pm-ledger` run.

## 1. Wrong lease dates in Command Center CRITICAL alerts — root cause is UNSTABLE LEASE IDs

**Do not blame `conditions.ts` / `critical-dates.ts`. That was my first diagnosis and it was WRONG.**
Running the real `evaluateConditions` against the on-disk snapshot at `referenceDate 2026-07-24`
produces entirely correct output — verified by direct execution, not inspection:

- Granite Tops & More → `Renewal lapsed / holdover — lease end passed May 31, 2026` (warning, L-2)
- J&R Enterprises → `expires Jul 31, 2026 (7d)` (critical)
- Carlton L. Handy → **no alert at all** (correctly silent; 2027-02-28)

The alert *rules* are right, including an L-2 holdover branch. What the emails showed instead:
Granite Tops paired with J&R's date/day-count, Carlton Handy paired with CJ's Tint Shop's, J&R
dropped entirely.

**Actual root cause: lease IDs embed a worksheet ROW INDEX and are therefore unstable.**
Proof — `data/alert-state.json` vs the current snapshot:
`zettler-2000-2002-`**135**→**131** · `29000-information-lane-105-`**56**→**53** ·
`29000-information-lane-101-`**53**→**50** · `2207-northwood-a4-`**22**→**21**.
When workbook row order shifts, (a) a tenant's identity can pair with another row's dates, and
(b) the alert-dedupe state silently invalidates — previously-alerted leases re-fire, and a lease
whose new id collides with an old one is suppressed (that is how J&R vanished).

**Already being fixed — do NOT write a competing fix.** Branch `fix/lease-id-integrity`
(worktree `.claude/worktrees/lease-id-integrity-fix`), 10 commits + 3 REFUTE rounds, ~+1,359
lines with tests; commit `a9f0bf0` = *"fix(parse): stable lease ids independent of worksheet row
position"* in `server/workbook/parse.ts`, plus a portfolio.json staleness guard and a
lease-snapshot drift check. Duplicating it is the hazard in
[[reference_concurrent_session_duplicate_hardening_work]].

**Open follow-up when that branch lands:** `data/alert-state.json` still holds the OLD row-index
ids. Stale ids there will keep mis-deduping until the state is reconciled or reset.

Until fixed, treat CRITICAL lease emails as pointers, not facts. Cross-check any lease date
against `portfolio.json` + Notion Tenant DB + the HubSpot renewal deal before acting. Related:
the separate documented `direction` defect in the same module (balloon alerts firing on notes
receivable — Restoration Church Trust is an ASSET).

## 2. `tenant_db_snapshot_diff.py` false positives across a day boundary — FIXED 2026-07-24

It fingerprinted five **date-derived formula fields** that recompute from the calendar on every
read: `Days to Expiration`, `Months Remaining`, `WALT Contribution (Years)`,
`Tenant Tenure (Months)`, `Months to Expiry`. First real cross-day run: **267 of 298 rows
"changed", 5 real** (a Property Address correction, `9620 State 350 — Columbus OH` → `Kansas City MO`).

**Why it survived sign-off:** the "verified end-to-end 2026-07-20" claim — written into
`ora-pm-ledger`'s own SKILL.md — came from a **same-day second pull**, where those fields had not
yet moved. It was never tested across a date change.

**Fix applied:** excluded by NAME via `TIME_DERIVED_FIELDS` (not by type — a formula over static
inputs is still a real signal); `diff_snapshots` now compares *filtered* fields on both sides
rather than the stored hash, so pre-fix snapshots still compare cleanly (without this the first
post-fix run would have reported all 298 rows changed); added a **bulk-field guard** emitting
`warnings[]` when any non-excluded field moves on >50% of rows. That guard immediately caught
`Months to Expiry`, a fifth derived field that would have burst monthly rather than daily.

Re-verified on real archived snapshots: 07-22→07-24 **5** (was 267) · 07-21→07-22 **20** (was
298) · 07-20→07-21 **164** — all substantive, no spurious warnings. `--selftest` now 13
assertions including cross-day, migration, and bulk-guard cases.

**Generalizable lesson — the reusable one:** a same-day rerun is not a valid test for any
date-sensitive diff, fixture, or detector. "Advance the clock" must be a required case.
Related: [[feedback_fixture_shaped_tests_certify_dead_branches]].

## 3. RESOLVED 2026-07-24 evening — `fix/lease-id-integrity` merged (PR #232), re-baseline complete

`227bfd8` merged 19:05 ET. First `ora-lease-snapshot-refresh` firing afterward correctly refused
to write `portfolio.json` (137/138 ids churned — new stable-id scheme vs. the old row-position
scheme, tripped the >25% anomaly floor) and separately flagged one `overlay.json` `renewalStages`
key (`9620-state-350-110-102` → Triple Threat Kansas City LLC, unit 110) as a prefix-match needing
manual suite-turnover confirmation. Gabriel confirmed Triple Threat is still the occupant (lease
2026-04-15 through 2029-04-30, verified against the live workbook) — the scheduled-task session
hand-applied that one re-key (value `Negotiating` preserved), then `--force` re-baselined
`portfolio.json`. Both files gitignored, nothing to commit. Verified independently by a second,
concurrently-running session (this one) via a clean rerun of both scripts: `lease-snapshot-drift-check.ts`
exit 0 ("No lease drift... 138 leases"), `migrate-lease-overlay-ids.ts` dry run exit 0 (no warnings).

**The churn was masking 5 real `leaseEnd` corrections the row-position bug had attached to the
wrong lease — 2 adverse:** Fully Equipped Cleaning (Banwick 2802) and Columbus Suburban
Construction (Morrison 386+388) were both shown with 8-10 months of term left but actually expired
2026-06-30 — **in holdover since**, unflagged by any expiration/renewal report because the only
watcher keyed off forecasted (not elapsed) expirations. Also newly correct: Carlton L. Handy
(2207 Northwood A4, now 2026-08-31/38 days out) and Granite Tops & More (Zettler 2000-2002, now
2026-07-31/7 days out) moved sooner; J&R Enterprises (9620 State 350 105B) moved out to
2026-12-31 (favorable). Resolution + these findings emailed to Gabriel and filed to Notion by the
resolving session.

**Systematization candidates the resolving session flagged (not yet built):** (1) the drift check
only diffs id-set membership — a business-key (company+unit) value diff would have surfaced these
5 date changes directly instead of burying them in a 275-line id dump; (2) nothing currently alarms
on a lease past `leaseEnd` still carrying a non-`Expired` status — both holdovers sat silent because
detection is forecast-only, not elapsed-aware.

This closes this file's "Open follow-up" note above about `data/alert-state.json` holding stale
row-index ids — the re-baseline carries the new stable ids forward; alert-state itself was not
separately checked by either session and may still warrant a one-time reconciliation pass if old
ids are found lingering there.
