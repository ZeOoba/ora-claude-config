---
name: project-lease-snapshot-id-rebaseline-pending-2026-07-24
description: CLOSED 2026-07-24 — lease-id re-baseline done; it surfaced 2 tenants in undetected holdover since 2026-06-30
metadata: 
  node_type: memory
  type: project
  originSessionId: 70bd543c-295a-42b3-9560-0c3763b7f04e
  modified: 2026-07-24T23:48:33.777Z
---

**CLOSED 2026-07-24**, same day it opened. Gabriel authorized after confirming Triple Threat Kansas City, LLC still occupies 9620 State Rte 350 Unit 110.

**What happened.** PR #232 (`227bfd8`) changed lease ids from row-position (`1100-rarig-a-6`) to tenant-identity (`1100-rarig-a-richwood-equipment-company-llc`). The live `portfolio.json` predated the merge, so 100% of ids differed and `ora-lease-snapshot-refresh` tripped its >25%-removal anomaly floor (exit 1) rather than adopting the new parse.

**Resolution:** backed up to `data/_backup/`, hand-applied the one overlay re-key (`renewalStages` `9620-state-350-110-102` → `...-triple-threat-kansas-city-llc`, value `Negotiating`), then `--force` re-baselined. Verified: drift check exits 0, migration dry run clean, 138/138 unique ids, overlay entry ATTACHED.

**The durable lesson — worth more than the incident.** The id churn was masking five genuine `leaseEnd` corrections, because the row-position bug had been attaching dates to the wrong leases. Two tenants had been in **undetected holdover since 2026-06-30** while the system showed 8–10 months of remaining term:
- Fully Equipped Cleaning Maintenance Services LLC (Banwick 2802): 2027-04-30 → 2026-06-30
- Columbus Suburban Construction (Morrison 386+388): 2026-08-31 → 2026-06-30
- Carlton L. Handy (2207 Northwood A4): 2027-02-28 → 2026-08-31 (pulled 6 months in)
- J&R Enterprises (9620 State 350 105B) +5 mo and Granite Tops & More (Zettler 2000-2002) +2 mo, both favorable

Neither holdover would have appeared on a renewal or expiration report. **Generalizable: when a mass-id-change event trips an integrity floor, diff the payload by business key (company+unit), not by id — the id churn hides the real data deltas underneath it.** A floor that only reports id-set membership will describe a 100% turnover and say nothing about the five records whose values actually changed.

Two gotchas for anyone repeating this: `migrate-lease-overlay-ids.ts --apply` writes NOTHING for prefix-match entries — it defers to a human by design, so "No changes needed" does not mean the overlay is migrated; and both data files are gitignored, so there is nothing to commit afterward.

Notion: refusal `3a76ecd8-9e59-8158-9d3f-cf8853688e87` · resolution `3a76ecd8-9e59-8128-8b4e-ee4440e8d0f6`. Related: [[reference-lease-date-detector-defects-2026-07-24]].
