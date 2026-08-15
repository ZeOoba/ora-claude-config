---
name: reference-hubspot-missed-lease-date-correction
description: The 2026-07-16 lease-date remediation fixed Notion and the workbook but never propagated to HubSpot renewal deals — HubSpot still carries the disproven dates.
metadata: 
  node_type: memory
  type: reference
  originSessionId: 72e9c1ee-b97a-4644-bd90-b89f2488af01
  modified: 2026-08-05T10:32:07.310Z
---

The 2026-07-16 lease-expiration remediation corrected the Notion Tenant DB (and the workbook was already right), but **the HubSpot Lease Renewal deals built from the same March 2026 import were never touched**. Found 2026-07-25 by the ora-am-brief §4b HubSpot cross-check.

State as of 2026-07-25 (workbook = source of record, `portfolio.json` asOf 2026-07-24):

| Tenant | Workbook | HubSpot deal close date |
|---|---|---|
| STONE CREST COUNTERS LLC (Zettler 2012) | 2028-07-31 | 2026-07-31 — stale |
| Chesapeake Brands, LLC (29000 Info Ln 501) | 2027-03-31 | 2026-07-31 — stale |
| J&R ENTERPRISES (9620 State 350, 105B) | 2026-12-31, `Active` | 2026-07-31, **edited 2026-07-21** — live conflict, unresolved |

**Why:** `2026-07-31` is the exact wrong date from the original defect — the one the 07-16 audit disproved on two rows. Remediating two of three systems leaves the third quietly authoritative for anyone reading HubSpot, and HubSpot is what drives renewal outreach. J&R is worse than stale: someone actively edited it *toward* the wrong date on 07-21, after the correction.

**How to apply:** Treat a lease-date correction as a three-system change — workbook, Notion Tenant DB, HubSpot renewal deal — and verify all three before closing it. When a date dispute surfaces, check HubSpot too; do not assume the Notion fix propagated. J&R still needs one lease-document check to settle. Related: [[reference-lease-date-detector-defects-2026-07-24]], [[project-tenant-hubspot-reconciliation-2026-07-21]], [[reference-tenant-name-mappings]].

Second finding, same run: `ora-tenant-hubspot-reconciliation` (monthly, 1st @ 08:15) is the task that should have caught this and did not surface it — worth checking whether its comparison covers deal *close dates* or only stage/status.
