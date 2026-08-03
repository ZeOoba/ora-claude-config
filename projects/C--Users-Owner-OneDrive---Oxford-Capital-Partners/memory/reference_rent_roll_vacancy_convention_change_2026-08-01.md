---
name: reference_rent_roll_vacancy_convention_change_2026-08-01
description: Master Workbook rent roll changed its vacancy definition on 2026-08-01 per Gabriel — occupancy % before and after that date are not comparable
metadata: 
  node_type: memory
  type: reference
  originSessionId: 3a21fa0c-1eb5-4c06-b0c0-b5dce4253d70
  modified: 2026-08-03T15:44:49.876Z
---

The Master Tenant Rent Roll tab gained a **PORTFOLIO SF & OCCUPANCY** analytics block, and the vacancy definition changed effective **2026-08-01 per Gabriel** (stated in-cell: "Convention changed 8/1/26 per GG"). Vacant SF is now the **union of `Status = "Vacant"` and `Notice to Vacate = "Yes"`** (no double-count), where previously noticed-but-still-paying units counted as occupied.

Effect on the 2026-08-02 workbook: gross roster 513,158 SF → less 900 SF common area → **Total Leasable 512,258 SF**; vacant incl. notice **26,045 SF**; **Leased 486,213 SF**; **occupancy 94.92%**. The tab also publishes a memo "physical basis" occupancy of **97.88%** that adds back the 15,200 SF noticed-but-still-in-occupancy.

**Why this matters:** the `ora-master-workbook-ingest` snapshot for 2026-07-26 reported occupancy as **98.6%** on the old basis. The ~3.7-point drop between the 07-26 and 08-03 snapshots is almost entirely a definitional change, not a leasing event. Reading it as portfolio deterioration would be wrong.

**How to apply:** when comparing occupancy across Portfolio Metrics Snapshots that straddle 2026-08-01, use the physical-basis memo figure for continuity with pre-08-01 snapshots, or state plainly that the series breaks. The headline going forward is the stricter Leased ÷ Total Leasable number. Three portfolio SF figures now coexist by definition and none is marked headline — Property NOI **513,761**, rent-roll gross roster **513,158**, Total Leasable **512,258** (0.29% spread); pick the one matching the denominator you need. Related: [[00_system_of_record]], [[project_northwood_egflc_loan_miscategorized_2026-07-27]].
