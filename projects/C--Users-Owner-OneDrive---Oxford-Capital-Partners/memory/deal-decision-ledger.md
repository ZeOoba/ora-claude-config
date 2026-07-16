---
name: deal-decision-ledger
description: "One row per decided acquisition (PASS/SKIP/DROP/PARK/CLOSED/TERMINATED) — date, verdict, one-line reason, and the buy-box rule it validated or refined. Scaffolded 2026-07-09 so revealed acquisition preferences are readable at a glance instead of reconstructed from projects.md prose each session."
metadata:
  node_type: memory
  type: project
  originSessionId: a744d8cf-2abe-4151-98ea-2bd224723db2
---

# Deal Decision Ledger

Companion to the "Active deal pipeline" table in [projects.md](projects.md) (which holds only currently-open deals). This file is the durable record of CLOSED decisions — what got PASSed, SKIPped, DROPped, PARKed, or TERMINATED, and why — so the firm's revealed buy-box preferences compound over time instead of living only in event_log.md prose.

**Maintenance:** append a row on every PASS/SKIP/DROP/PARK/CLOSE/TERMINATE decision (ideally as part of the deal-retirement lifecycle skill, so this accretes automatically rather than depending on manual backfill). Never delete a row — a PARKed deal that later un-parks gets a new row, not an edit to the old one. See [memory-policy.md](memory-policy.md) for the general archive-don't-delete convention.

| Date | Deal | Verdict | One-line reason | Buy-box rule validated / refined |
|---|---|---|---|---|
| 2026-07-08 | 470 McCormick Blvd, Columbus OH | PASS | LOI FINAL v2's 6/17/2026 expiration lapsed 21 days unshipped to broker KRG; Gabriel made an explicit in-session kill decision 7/8 rather than let it drift further | — |
| 2026-07-09 | E. Fulton Street Portfolio, Columbus OH (5 bldgs, 202,164 SF) | ACQUISITION TERMINATED → note/foreclosure track | Confirmed chlorinated-solvent (TCE) release, soil/groundwater/soil-vapor, non-delineated, live indoor-air pathway (Phase II 2026-06-01) | Materially-impaired Phase II environmental findings → walk/re-trade, don't proceed on original terms blind |
| 2026-07-09 | 11850 Hamilton Ave (Dollar General, "quasi-IOS"), Cincinnati OH | PARKED | A Cowork session self-underwrote to v03 and auto-staged the Notion card to Due Diligence; Gabriel parked it | Reinforces: dollar-store/DG net-lease reads as out-of-box standing retail regardless of a favorable self-underwriting result — see the OH 3-pack precedent below |
| 2026-06-14 | Tollway Center (2400 Hassell Rd / 2200 Stonington Ave), Hoffman Estates IL | SKIP | Out-of-box: Cook County (outside target markets), 74,607 SF > 50K SF size cap, concurrent 1980/1990 re-roof + near-total rollover within 18 months | Refines: stack of (size-cap breach + concurrent major capex + concentrated rollover) is a hard pass even before other diligence |
| 2026-06-12 | 927 N Emerson Ave (Goodwill Distribution), Greenwood IN | DROPPED FOR NOW | Open-sessions board decision; revised-offer framing ($7.5M target / $7.85M max) preserved in Cowork session `local_2672b660` if it resurfaces | — |
| 2026-06-11 | Liberty Office Park, West Chester OH | CLOSED (no LOI ever sent) | Stale-thread review kept only 511 Industrial Mile Rd open among the reviewed threads | — |
| 2026-06-11 | 2720 Symmes (Nimer) | CLOSED | Quiet since the 12/2025 counter; closed in the same stale-thread review as Liberty Office Park | — |
| 2026-06-08 | Dollar General 3-pack, OH | PASS | Out-of-box retail net-lease, no value-add path | See [deal_dg_portfolio_oh_2026-06.md](deal_dg_portfolio_oh_2026-06.md) for the full DG cap-rate stratification analysis — the reusable market-data takeaway behind the two DG-adjacent decisions above |

*Sourced from [projects.md](projects.md) "Recently resolved" section and the Active deal pipeline table, 2026-07-09. Older resolved deals (pre-2026-06) were not back-filled from event_log.md in this pass — do so incrementally as they're referenced, or in a dedicated consolidation pass.*
