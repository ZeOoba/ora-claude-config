---
name: reference-hubspot-lease-renewal-closedate-unreliable-2026-08-16
description: "HubSpot Lease Renewal `closedate` is wrong on 2 of 3 August 2026 expirations — never drive an expiration alert off it without a workbook cross-check"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 681975eb-43c2-4411-8b0c-14015927e5b8
  modified: 2026-08-17T01:11:19.741Z
---

HubSpot's **Lease Renewal pipeline `closedate` is not a trustworthy lease-expiration signal.** Found 2026-08-16 by cross-checking all three HubSpot deals dated `2026-08-31` against `oxford-command-center/data/snapshots/portfolio.json`. Matched on monthly rent (exact to the dollar in both error cases, so same lease, not a name collision):

| Tenant | HubSpot closedate | Workbook leaseEnd | Error |
|---|---|---|---|
| CJ's Tint Shop (unit 105) | 2026-08-31 | 2026-08-31 | none |
| Robert & Kesha Best (C1+C2) | 2026-08-31 | 2027-08-31 | **1 yr early** |
| Medspeed, LLC (unit 305) | 2026-08-31 | 2029-08-31 | **3 yr early** |

**The errors are phantom expirations, not missed ones** — nothing lapses silently. The real cost is alerting: the 2026-08-16 Command Center Daily Brief §5 recommended a HubSpot workflow triggered on `closedate < 90 days AND hs_lastmodifieddate > 30 days ago`. Built on this field as-is it fires on leases years from expiring, and Gabriel learns to ignore it. **Drive expiration alerts off `portfolio.json` (workbook-sourced); treat HubSpot as activity-tracking only** — its `hs_lastmodifieddate` staleness signal is sound even where `closedate` is not.

Third occurrence of the same defect class across three different systems: Notion Tenant DB dates (2026-07-16, J&R / Chesapeake / Stone Crest), the [[reference_hubspot_missed_lease_date_correction]] gap, and now HubSpot `closedate`. A recurring workbook↔HubSpot↔Notion lease-date reconciler is the standing fix — see [[reference_ora_pm_critical_dates_feed_unreliable_2026-08-04]] for the same "match on property+unit, never tenant name" discipline.

Most of the 25 open Lease Renewal deals are still frozen at `appointmentscheduled` with `hs_lastmodifieddate` on 2026-03-27, the bulk-creation date — so a stale-date filter alone will not separate real from phantom.

**RULED CLOSED 2026-08-16 (Gabriel):** the "build a HubSpot workflow off `closedate`+`hs_lastmodifieddate`" idea surfaced a second time (spawn_task suggestion, same day as the Daily Brief §5 mention above) and was ruled unnecessary both times. Live re-check found 37 open deals (not 25), 20 of 37 still frozen at 03-27 (not "great majority"). Re-verified 8 of the ~12 deals the rule would actually fire on today against `portfolio.json`: only CJ's Tint Shop and Midwest Closets were real; Best/Medspeed/Heritage Pool/P.U.P.S/DELVAL/Soldier Trucking were phantom (workbook leaseEnd 1-5yr later) — these are leases already renewed in the workbook whose HubSpot deal was never advanced past `appointmentscheduled`, so a HubSpot-sourced alert fires hardest on the leases already handled, the worst kind of false positive. **The capability already exists, correctly sourced:** oxford-command-center's `src/analytics/conditions.ts` L-1 ("Expiring, no renewal signal", ≤90d + no renewal-stage advance) and L-2 ("Renewal lapsed/holdover") read `leaseEnd` from the workbook-fed snapshot, fire a same-day critical alert email to ggoldberg@oxfordra.net (`server/brief/run.ts`), AND populate the Daily Brief's ≤90d forward calendar — daily via `ora-am-brief` (`0 6 * * *`), tighter cadence than the proposed monthly HubSpot workflow. No new build. If this idea surfaces a third time, point straight here instead of re-deriving.
