---
name: Lease Intelligence Pipeline
description: ORA lease & A/R dashboard pipeline — architecture, platform mapping, and known data conventions
type: project
originSessionId: f3857322-25d4-417f-9a2e-a1b703d736bf
---
# Lease Intelligence Pipeline (2026-04-20)

Location: `OneDrive\Master Lease Database\_pipeline\`
Dashboard: `OneDrive\Master Lease Database\2026-04-20_ORA_LeaseDashboard_v2.html`

## Architecture
Manual CSV/XLSX drops → Python parsers → `output/TENANTS.json` → static HTML dashboard fetches JSON.
Zero external deps beyond stdlib + openpyxl. Run via `python build.py`; view via `python serve.py` then http://127.0.0.1:8765/.

## Platform mapping (A/R)
- **AppFolio** (transaction-detail CSV): Rarig, 3034 Westerville, 3540 E 5th, "Sepich" portfolio (= 2000 Zettler + 2012 Zettler + Banwick + Morrison)
- **Rent Manager** (summary CSV, section headers): 2203-2207 Northwood (Salisbury MD)
- **Yardi/MRI** (xlsx, pre-bucketed aging): 29000 Information Lane, 1900 N Broadway ("eastgate")
- **QuickBooks**: NOT part of tenant A/R — accounting system only. Do not wire QB to this pipeline.

## Known data conventions
- AppFolio "<Multi>" unit = tenant leases multiple units — no unit-level allocation available
- Rent Manager units use format `{num}{letter}` (e.g. `4A`) while lease rows use `{letter}{zero-num}` (e.g. `A04`); parser normalizes via `unit_variants()`
- Yardi property codes: `29000inf` → Info Lane, `eastgate` → Broadway
- "Sepich" = AppFolio portfolio grouping for Columbus OH, not a property

## A/R reconciliation rules
- **Active A/R**: matched to a current lease row via normalized-key fuzzy match (strips punctuation, trailing LLC/Inc, case-insensitive). ~$191K across 35 tenants as of 2026-04-14 files.
- **Legacy A/R**: unmatched = former tenants who vacated and were replaced. Tracked in `sync_log.legacy_ar` as collection follow-up; NOT surfaced as unmapped. ~$13.8K across 8 tenants.
- Explicit aliases in `config/tenant_aliases.json` for material name differences (e.g. "SoccerPlant, Inc." → "Soccer Plant Inc", "XPO Foods, LLC" → "Masala Bazaar (XPO Foods)")

## Outstanding (Session 3+)
- Rent-roll CSV parsers for AppFolio/Yardi/RM still stubbed — need sample exports to lock `FIELD_MAP`
- Salisbury (Northwood) SF=0 in lease data — enter actuals to enable $/SF calcs
- Properties with A/R files but no lease file yet: none (all 7 files covered)
- Properties in dashboard with no A/R file yet: Red Branch, E Livingston, Fishel Dr, Hwy 350, Info Lane (other than 29000), Broadway (other than CRC-covered tenants)
