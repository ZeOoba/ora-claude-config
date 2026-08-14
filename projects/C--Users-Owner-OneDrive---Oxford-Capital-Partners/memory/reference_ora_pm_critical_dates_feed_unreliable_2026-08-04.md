---
name: reference-ora-pm-critical-dates-feed-unreliable-2026-08-04
description: ora-pm critical-dates alert disagreed with the Master Workbook on 5 of 10 lease dates and omitted the nearest expiry — do not act on it unverified
metadata: 
  node_type: memory
  type: reference
  originSessionId: 7c750896-9388-4e71-8a83-fd55979171a3
  modified: 2026-08-04T22:29:20.576Z
---

The `[ORA PM] 10 Critical Dates` alert (ora-pm.pages.dev/critical-dates) sent 2026-08-04 18:06 ET was cross-checked row-by-row against `oxford-command-center/data/snapshots/portfolio.json` (Master Excel Template lineage, `asOf 2026-08-04`), which CLAUDE.md designates the source of record for firm figures.

**5 of 10 rows were wrong**, each by 2–5 years, and each assigned a *bucket* date (2026-09-30 or 2026-10-31) rather than the lease's real date:

| ora-pm row | ora-pm date | Master Workbook |
|---|---|---|
| P.U.P.S Dog Obedience — 9050 Red Branch K | 2026-09-30 | Karen Decker — **2031-09-30** |
| The Companies LLC — 2800 Banwick 2808 | 2026-09-30 | Jade (Cieli) Tucker — **2028-09-30** |
| Heritage Pool Supply — 7658 Fishel Dr N | 2026-09-30 | Kristen Morgan — **2031-09-30** |
| Sky Shield — 2203-2207 Northwood A3 | 2026-09-30 | Brett Lagana — **2029-08-31** |
| DELVAL Equipment — 29000 Info Lane 204-205 | 2026-10-31 | Jim McDonough — **2028-04-30** |

The other 5 (Hoodz of Delmarva, Midwest Closets, Bakers Specialty, Soldier Trucking, BRITMAN) matched exactly.

**Separately the feed omits the nearest expiration in the portfolio:** CJ's Tint Shop / Courteney Jones, 29000 Information Lane 105, expiring 2026-08-31, $22,200/yr.

**Why it matters:** a false 57-day warning on a lease with five years left wastes attention, and the omission hides the one expiry actually inside 30 days. Both failure directions in one feed.

**How to apply:** treat ora-pm critical-dates as unverified until the discrepancy is closed; reconcile against `portfolio.json` before acting. **Cross-reference by property + unit, never by tenant name** — the two systems differ by convention: ora-pm carries entity names ("Hoodz of Delmarva"), the Workbook carries the contact of record ("Jim Hogan"). Matching on name alone produces spurious mismatches on rows that actually agree.

Awaiting Gabriel's ruling on whether the feed stays in service (raised as TIER 3 item 2 in the 2026-08-04 EOD Action Ledger).

Related: [[reference-hubspot-missed-lease-date-correction]], [[reference-lease-date-detector-defects-2026-07-24]], [[reference-parseleases-vacancy-block-phantom-leases-2026-08-03]]
