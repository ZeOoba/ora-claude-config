---
name: index-markets
description: "Sub-index of MEMORY.md — market, deal, portfolio-data and workbook pointers (buy box, ledgers, decided deals, rent-roll/lease-data gotchas). Split out 2026-08-24; MEMORY.md links this file, and memory-integrity-probe check 1 follows it one level."
metadata: 
  node_type: memory
  type: reference
  originSessionId: 0fc18634-d92f-4211-8be2-5903fcf2975f
  modified: 2026-09-12T21:57:53.286Z
---

# ORA Memory Index — Markets & Deals

> **Sub-index of [MEMORY.md](MEMORY.md).** Split out 2026-08-24: the root index had reached 24,367 bytes — 33 bytes below the 24,400-byte Read-tool hard limit — and this section was 6,100 of them. Per the size-gate calibration, the lever is ARCHIVAL or SPLITTING, never prose trimming.
>
> These pointers are **NOT auto-loaded** the way the root index is. Read this file before any deal, buy-box, rent-roll, lease-data, insurance or workbook question, rather than assuming no prior finding exists.
>
> The three ⛔ entries from this section stayed in the root index on purpose — they prevent active harm (a wrong walk-price number, a silently broken snapshot/mirror deploy) and must survive without anyone opening a sub-index. Same rule going forward: ⛔ stays in root, everything else lands here.
>
> Same rules as the root index: one line per entry, pointers only, never content. Rationale for the split pattern: [size gate is a runway marker](reference_memory_index_size_gate_is_a_runway_marker.md).

## Markets & Deals
- [Market Intelligence](markets.md) — cross-market snapshots, macro (FRED), replacement cost, comps
- [Basis Denominator — RCT v03 (RATIFIED)](project_replacement_cost_benchmark_unratified.md) — the ONE denominator; ORA buys at ~35-40% of replacement
- **[Acquisition Buy Box & Scorecard v1.1 (RATIFIED)](acquisition-buy-box-v1.md)** — Rulings 1-5 + Amendments A-G, ratified 2026-06-09; created 08-17 closing a gap where drift-check step 2c cited this key since 06-20 and it never existed
- [Notion Pipeline Tracker stale governor fields](reference_notion_pipeline_tracker_stale_governor_fields.md) — RCR formula stale at $95/SF; DSCR text asserted a non-canonical floor; fixed 08-11
- [Deal Decision Ledger](deal-decision-ledger.md) — one row per decided PASS/SKIP/DROP/PARK/CLOSE + buy-box rule validated
- [Disposition & Exit Ledger](disposition-ledger.md) — POST-acquisition lifecycle: ACQUIRED/HOLD/REFI/1031/SALE; 13 deals + 1100 Rarig HOLD backfilled 07-29
- [DG Portfolio OH — PASS](deal_dg_portfolio_oh_2026-06.md) — Matthews 3-store DG net-lease + cap stratification
- [1100 Rarig Ave — Disposition (HOLD)](deal_1100_rarig_disposition_2026-07.md) — basis/NOI/cost-seg; open gaps in file
- [Historical Evaluations acquisition review 07-29](project_historical_evaluations_acquisition_review_2026-07-29.md) — 13-deal table; 2 LTV exceptions, 2 open date discrepancies
- [entry-market-scan defects 08-04](reference_entry_market_scan_defects_2026-08-04.md) — `Gate Review` field: blank = awaiting Gabriel, never placeholder it
- [5515 Catfish Court broker-correspondence claim is FALSE](reference_catfish_court_broker_correspondence_claim_false.md) — 08-14 re-check is a warm follow-up, not a cold call
- [808 Rhoads real broker is Elford, not Koon/Menninger](reference_808_rhoads_real_broker_is_elford_not_koon.md) — Deal went OUT of contract 06-26; seller wants ~$3.5M vs the $2.86M LOI plan
- [Delinquency collection-status blind spot](reference_delinquency_report_collection_status_blindspot.md) — "no action taken" is inferred; wrong 4 of 6 tenants
- [Columbus Suburban default/vacate 07-28](tenant_columbus_suburban_default_2026-07-28.md) — ORA-T-105 gone; $20,457 owed, PM misspells name "Suburan"; vacate ≠ contract expiry
- [Rent-roll vacancy convention changed 08-01](reference_rent_roll_vacancy_convention_change_2026-08-01.md) — occupancy 98.6%→94.9% is definitional, not deterioration
- [NOI opportunity sweep 09-19](reference_noi_opportunity_sweep_2026-09-19.md) — ~$18.8K/yr from 2 solar roof leases (King Energy, HARD 2027-12-31 §48E wall); cost-seg CapEx row wrong (5 studies exist); billboard = $3,600/yr; Salisbury vacant parcel NOT ORA's
- [Tax-appeal sweep 09-19](reference_tax_appeal_sweep_2026-09-19_no_candidates_underassessed.md) — ZERO appeal candidates, everything under-assessed; exposure is Wicomico Group 3 notice ~late Dec 2026, Jackson MO 2027, HB 126 on recent Ohio buys; Rarig 'appeal cut tax' claim UNVERIFIED/possibly inverted
- [Broker coverage-gap map 09-19](reference_broker_coverage_gap_map_findings_2026-09-19.md) — v01 'missed warm leads' REFUTED on thread bodies; real finding = unsent drafts incl. 2 chases to Koon on 808 Rhoads; gap pool has almost no emails
- [Mortgage-maturity signal not bulk-accessible 09-18](reference_mortgage_maturity_signal_not_bulk_accessible_2026-09-18.md) — no ORA market's recorder exposes bulk mortgage data; do not re-propose as a free build
- [Renewal cohort rulings + lease basis by property 09-18](reference_renewal_cohort_rulings_and_lease_basis_2026-09-18.md) — who already has an offer out (first-stage HubSpot deal ≠ un-worked), 9050 Red Branch = NNN, GT bay layout, Fresenius rent schedule
- [2207 Northwood MTM tenants ≠ holdover 09-18](reference_2207_northwood_mtm_tenants_not_holdover_2026-09-18.md) — Adkins Towing + Anibal Morales are month-to-month per Gabriel; workbook "Holdover" label is wrong for them
- [parseLeases vacancy-block phantom leases](reference_parseleases_vacancy_block_phantom_leases_2026-08-03.md) — CLOSED 08-03
- [Both snapshot tasks write ONE file](reference_snapshot_tasks_share_one_file_diff_absorption.md) — the sibling's "no commit" is correct, not broken
- [CC snapshot is TRACKED, not ignored](reference_command_center_snapshot_is_tracked_not_ignored.md) — auto-committed unattended; the task file's "git-ignored" claim is wrong
- **[Worktree isolation dropped gitignored overlay.json — CLOSED 09-06](reference_worktree_isolation_drops_gitignored_overlay_2026-09-05.md)** — PRs #312 then #311 merged (order mattered: #311 unmasked #312's silent loss). Refute found BOTH incomplete after green CI: #311's guard judged RAW JSON while the loader coerces, so junk passed and still zeroed; #312's writers gated on a flag that is null for `not-configured`. **Lessons: a guard must judge what the consumer PRODUCES, not its input; a partial vi.mock silently yields `undefined` for omitted exports (broke 21 tests).** STILL OPEN: partial-shrink of `tasks` (not a shrink-guard key), bake-mirror warns-only
- [Notion Tenant DB Completeness Gap](reference_tenant_db_completeness_gap.md) — split on `Row Retired`, not the ⛔ARCHIVED prefix
- **[Step 8 CHURN population = 07-12 Category-B dedup residue, not the phantom batch 09-05](reference_step8_churn_population_is_dedup_residue_not_phantom_batch_2026-09-05.md)** — OI-221's 09-05 update cites the wrong ruling and a title+expiration signature that fails on 3/13; scope Step 8 to `Row Retired == false` instead. Handy is not "the one exception"
- [ora-pm critical-dates feed unreliable 08-04](reference_ora_pm_critical_dates_feed_unreliable_2026-08-04.md) — wrong on 5 of 10 rows; match on property+unit, never tenant name
- [Lease-date detector defects 07-24](reference_lease_date_detector_defects_2026-07-24.md) — PR #232 merged; diff by business key not id
- [HubSpot missed the 07-16 lease-date correction](reference_hubspot_missed_lease_date_correction.md) — HubSpot never fixed; J&R live conflict
- **[HubSpot Lease Renewal `closedate` unreliable 08-16](reference_hubspot_lease_renewal_closedate_unreliable_2026-08-16.md)** — wrong on 2 of 3 Aug expirations (1yr/3yr early); never alert off it
- [Insurance lapse confirmed REAL 07-25](project_insurance_lapse_confirmed_real_2026-07-25.md) — 5 properties expired/cancelled, 3 with no plan
- **[9620 State 350 Hartford switch + deductible-ladder fix 08-17](reference_insurance_9620_state350_and_deductible_ladder_2026-08-17.md)** — 3 items OPEN (broker of record/GL transition/short-rate); "47% short" finding was wrong, corrected in skill v2.0
- [Master Lease landlord entity states 08-03](project_masterlease_landlord_entity_states_2026-08-03.md) — MD/MO entities sourced; Baqir/Baquir + 13B/B13 open
- [Master Lease next-rev upstream notes](reference_masterlease_next_rev_upstream_notes.md) — typo RESOLVED in v2.4.1; heading fragmentation still open
- [Master workbook no single-writer 07-24](project_master_workbook_no_single_writer_2026-07-24.md) — OPEN: uncoordinated concurrent edits
- [Master workbook single-writer proposal 07-25](project_master_workbook_single_writer_proposal_2026-07-25.md) — RATIFIED; text now [tech.md](tech.md) §3d
- [Cash Data excludes PM-held accounts](reference_cash_data_excludes_pm_held_accounts.md) — negative balance is usually tax-timing, not distress
- [Annual debt service 366-day over-capture](reference_workbook_annual_debt_service_366day_overcapture.md) — RESOLVED 08-05
- [ELS EOMONTH pair-fix landed HALF](reference_els_eomonth_pair_fix_half_applied_2026-08-05.md) — OI-094: `H6:I9` moved to EOMONTH but `Assumptions!B30` was never constrained to month-end; strictly WORSE than pre-fix under manual override
- **[754 Old State §31 has NO "Parking Contingency Period" 08-26](reference_754_section31_has_no_parking_contingency_period_2026-08-26.md)** — §31 is "Parking Modifications"; governing dates are **Sept 9** (PD filing) and **Oct 9, 2026** (FP outer limit) off the **Aug 10** certified Effective Date. The 08-12 psa-reconciliation banner wrongly listed this term as corroborated — a prior banner's corroboration list is not itself verified. Also: sig page is raster, text-layer read falsely reports an unexecuted instrument
