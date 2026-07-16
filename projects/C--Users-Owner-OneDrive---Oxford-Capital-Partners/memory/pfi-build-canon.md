---
name: pfi-build-canon
description: "Property Financial Intelligence build canon — Gabriel-ratified 14-unit roster, PM assignments, and accounting rulings (2026-06-12). Source of truth for all PFI phases; supersedes the spec's Open Items."
metadata: 
  node_type: memory
  type: project
  originSessionId: 560521ac-8a74-4b5f-b526-0cec56a26682
---

# PFI Build Canon (Gabriel-ratified 2026-06-12, verbatim session ruling)

## Roster — 14 units (Persimmon Tree residence EXCLUDED)

| # | Property | Financial mode | Own % | Property manager |
|---|----------|----------------|-------|------------------|
| 1 | 3540 E 5th Ave | P&L + single-tenant NNN lease | 100% | Paul Trautman — Kohr Royer Griffith |
| 2 | 3034 Westerville | P&L + single-tenant NNN lease | 100% | Paul Trautman — Kohr Royer Griffith |
| 3 | 3883 Livingston | P&L + single-tenant NNN lease | 100% | Paul Trautman — Kohr Royer Griffith |
| 4 | FVC (Fairground Village Center / Sepich) | P&L — **ENTITY-LEVEL is the official unit** | 100% | Paul Trautman — Kohr Royer Griffith |
| 5 | 1100 Rarig | P&L | 100% | Paul Trautman — Kohr Royer Griffith |
| 6 | 29000 Info Lane | P&L | 100% | Civita Peters — Thomas Park |
| 7 | 9620 State 350 | P&L | 100% | Peak Real Estate Partners (Hank Simpson + Garrett Alejos) |
| 8 | 9050 Red Branch Rd | P&L | **50%** | Steve She — CRC |
| 9 | 1900 N Broadway | P&L | **50%** | Steve She — CRC |
| 10 | 7658 Fishel | **LEASE-RUN** — master lease + estimated capex; no P&L | 100% | (none — NNN) |
| 11 | 401 Sunburst | **LEASE-RUN** — master lease + estimated capex; no P&L | 100% | (none — NNN) |
| 12 | 55 New Plant (EGFLLC, QuickBooks) | P&L + lease on file | 100% | (none) |
| 13 | 2203-2207 Northwood | P&L (AppFolio) | 100% | Brady Smith — SVN |
| 14 | 1851 S Club Solar | **25% roof/solar project only** — no real estate owned | **25%** | (none) |

## Accounting rulings
- **Owner transfers NEVER in NOI.** General commercial real estate accounting standards govern NOI, cash flow, debt service.
- Northwood 2025 interest expense = seller-financed loan @ 6.99%, **paid off via the 29000 Info Lane refinance** → debt-service classification, historical context only.
- **Coverage starts 2025** for the late-2024 acquisitions (3034 Westerville, 9620 State 350, 2203-2207 Northwood) — no 2024 stub periods.
- Basis: ingest as-is, tag basis per import, compare within-basis only; cross-basis comparisons flagged.
- Asset Management Fees **below NOI** (excluded).
- Ownership presentation: 100% property-level figures with an **Oxford-share overlay** (50% Red Branch + Broadway, 25% 1851 Solar).
- **R&M capex rule: single item > $5,000 = capex; ≤ $5,000 = opex. When line detail is unavailable, assume opex and flag.**
- **Source of record: PM-software exports are AUTHORITATIVE over internal QuickBooks** — QB carries internal-operation accounting not indicative of property performance.
- FVC 2025 contains a **$500,000 one-time perpetual cell-tower easement sale** (American Tower; was on Zettler Rd) — exclude from run-rate NOI.
- Zettler sale: **dead — still owned**; Sepich remains 8 props inside FVC.
- 9510 Persimmon Tree (residence): excluded from the build.
- **1851 S Club Solar income is real and stands as-is (ruled 2026-06-13): SRECs are sold to DC at roughly $400+/SREC — never haircut or discount the SREC income line.** (Entity NOI 2024 ≈ 630.8k / 2025 ≈ 507.5k validated.)
- **9620 State 350 chart (Peak REP QB export) books expenses as NEGATIVE outflows** — the warehouse sign-normalizes on ingest (majority-negative side flips, 'sign-normalized' DQ row). Corrected NOI: 2025 = 27,613.79 (lease-up year; consistent with NI 19,788 thru 09/2025), 2026 YTD = 74,229.81.

Links: [[firm]], [[reference-quickbooks-financials]], [[projects]]
Artifacts: spec `oxford-command-center/docs/superpowers/specs/2026-06-12-property-financial-intelligence-architecture.md` · mapping seed `.../2026-06-12-pfi-account-mapping-seed.json`
