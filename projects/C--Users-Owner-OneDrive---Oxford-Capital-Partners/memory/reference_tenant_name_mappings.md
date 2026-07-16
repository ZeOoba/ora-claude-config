---
name: Tenant Name Mappings — PM Platform → Notion Tenant DB
description: Reconciliation aliases between tenant names as they appear in A/R reports vs. Notion Tenant DB titles. Use when running Module C or any workflow that matches PM platform records to Tenant DB pages.
type: reference
originSessionId: 4af85f8f-ed95-41e9-a944-bf3a7f2e5278
---
# Tenant Name Mappings

PM platform exports (Rent Manager / Yardi / AppFolio) sometimes use different tenant names than the Tenant Database titles in Notion. Notion search alone won't always find them. Always check this list when a tenant lookup returns empty.

> **Spot-checked 2026-06-11** vs the freshest PM exports on disk: `Master Lease Database\_pipeline\drops\` 4.14.2026 batch (`CRC Delinquency 4.14.2026.xlsx`, `29000 Delinquency 4.14.2026.xlsx`, `1100 Rarig / 3034 / 3540 E 5th / Sepich Delinquency 4.14.2026.csv`). 12 of 12 PM-platform aliases verified character-exact. CAVEAT: that batch is the SAME vintage the table was built from — no PM export newer than 2026-04-14 exists on disk (consolidated `Rent Roll 04.20.2026.xlsx` is a pipeline output, not a raw export). Mappings are internally consistent but unverified against post-April platform data — re-verify against the next A/R export before reconciliation use.

## Confirmed Mappings (updated 2026-04-14; spot-checked 2026-06-11)

| PM Platform Name | Notion Tenant DB Title | Property |
|---|---|---|
| SoccerPlant, Inc. | Soccer Plant Inc *(search keyword: "Utku" — operator name, not tenant name)* | 9050 Red Branch Rd |
| XPO Foods, LLC | Masala Bazaar (XPO Foods, LLC) | 9050 Red Branch Rd |
| David Franklin Perry and Atomic Auto Salon LLC | Atomic Auto Salon LLC | 9050 Red Branch Rd |
| IMH LLC | I.M.H LLC | 3540 E 5th |
| TYM Wholesale | TYM Wholesale LLC | 2000 Zettler Rd |
| Buckeyes Best Transport (no apostrophe) | Buckeye's Best Transport (with apostrophe) | 3034 Westerville |
| P.U.P.S. | P.U.P.S Dog Obedience Training, LLC | 9050 Red Branch Rd |
| Buckner & Sons Masonry | Buckner and Sons Masonry | 1100 Rarig |
| BURGUNDYGINGER LLC (all caps) | BurgundyGinger LLC | 2810 Banwick |
| Gator Roofing Inc. | Gator Roofing LLC | 2024 Zettler Rd *(AppFolio groups it under property "2012 Zettler Rd", unit "2024")* |
| Columbus Suburan Construction (seller typo) | Columbus Suburban Construction | 384 Old Morrison Rd |
| PRO REPAIR (all caps) | PRO REPAIR LLC | 1100 Rarig Ave #M |

## Not found in Tenant DB as of 2026-04-14

These tenants appear in A/R reports but have no matching record:

- Building Bridges Therapy Svcs (29000 Info Lane) — $3,884.84 delinquent
- Eastpoint Church (29000 Info Lane) — $2,084.84 delinquent
- Chateau 1590, LLC (29000 Info Lane) — $1,742.31 delinquent
- Butter Pat Industries / Butter Pat Industries, LLC (29000 — two tenant accts) — $1,887.58 combined
- Magothy Electric Company, Inc. (29000) — $290.87
- Lamar Advantage GP Co. (3034 Westerville, billboard tenant) — $500 (likely ghost charge)

**Action:** These need to be added as new records if they're real active leases, or flagged for write-off if legacy/ghost.

## Lookup tips

- Notion search is semantic and often fails on exact match — search on **distinctive words**, not full name
- For known duplicates (⛔ DUPLICATE prefix), always take the non-duplicate record (most recent non-duplicate timestamp)
- Some tenants have multiple legitimate records (different units/leases) — in those cases the A/R balance should ideally be split, but pragmatically update the most-recent record with the total

## Update history

- **2026-06-11** — Spot-check (setup-remediation C4): all 12 confirmed aliases re-verified character-exact against the 4.14.2026 drops batch (Yardi XLSX + AppFolio/Rent Manager CSVs). All 6 "not found in Tenant DB" tenants still present in the 29000 Yardi export with matching balances (Building Bridges 3,884.84 / Eastpoint 2,084.84 / Chateau 1,742.31 / Butter Pat 534.00 + 1,353.58 / Magothy 290.87). No newer PM export exists on disk — currency vs the live platforms remains UNVERIFIED; check at next A/R export. Added AppFolio property-grouping note for Gator Roofing.
- **2026-04-14** — Initial mapping from first full Module C run across 7 A/R reports. 27 tenants updated with AR Balance / AR Aging Bucket / AR Data Date. 6 tenants flagged as missing from DB.
