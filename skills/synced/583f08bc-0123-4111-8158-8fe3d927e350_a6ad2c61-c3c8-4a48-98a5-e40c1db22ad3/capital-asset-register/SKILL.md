---
name: capital-asset-register
description: "Maintain ORA's per-property building asset register — nameplate capture, remaining useful life, and the replacement pipeline that feeds the annual capital plan. Trigger on: asset register, equipment register, how old is this unit, what model is it, nameplate, serial number, remaining useful life, EUL, when does this need replacing, replacement pipeline, building systems inventory, walk the roof, capital plan inputs."
---

# Capital Asset Register

One row per physical building-system asset across the portfolio, permanent for that
asset's life. The register answers three questions that ORA could not previously answer
from its own records: **what is installed, how old is it, and when does it need replacing.**

## Why this exists

On 2026-09-17, two contractors bid a rooftop unit replacement at 9050 Red Branch Rd Unit K.
The existing unit's **age and manufacturer were unknown to ORA until a bidding contractor
read the nameplate** — and its model and serial were never captured at all, by either
bidder or by ORA. A 19-year-old asset on a 27-property portfolio reached end of life as a
surprise.

Two consequences, both avoidable:

1. **A surprise replacement is an unbudgeted replacement.** Age is the single input that
   converts a reactive emergency into a line in the annual capital plan.
2. **Without a nameplate you cannot underwrite the bid.** Capacity, gas input, refrigerant
   and efficiency of the *outgoing* unit are what tell you whether the *incoming* unit is
   right-sized. On the seed asset, one bidder proposed 225 MBH of gas input where the
   existing unit had run on an estimated 180 MBH for nineteen years — and nobody could
   confirm the 180.

## Grain — read this before writing anything

| Database | Grain | Data source ID |
|---|---|---|
| 🧰 Building Asset Register | one row per **physical asset**, permanent | see Step 1 |
| 🔧 CapEx & Maintenance Log | one row per **spend event** | `acd5102e-16bc-4171-9cde-19a2496b1429` |
| 🏢 Property Register | one row per **property** | `24d6a531-f4b7-4c38-87fb-3b1be4a4f1f3` |
| Vendor & Advisor Directory | one row per **vendor** | `07dd54fd-1bc9-4555-8787-3fbd9b518abe` |

An asset accumulates **many** CapEx rows over its life. Nameplate identity therefore lives
on the asset and is never repeated on an invoice row. Do not extend the CapEx Log with
model and serial fields; that duplicates the identity on every expenditure and guarantees
drift.

## Step 1 — Confirm the register exists

The register was specified and its DDL frozen on 2026-09-17 but **creation was refused:
the ORA Notion workspace has exhausted its free block allowance.** Schema edits still
succeed; new databases and pages do not.

- Resolve the register by name in Notion under 📂 Databases
  (`3446ecd8-9e59-8150-9803-c0399086cc7e`). If it exists, use it.
- If it does not, the ready-to-run DDL is
  `2026-09-17_BuildingAssetRegister_NotionDDL_v01.sql` — one `notion-create-database` call,
  then a second call for the two formula columns so a formula parse failure cannot take
  the schema down with it.
- Until then the interim register and walk-through intake sheet is
  `2026-09-17_AssetRegister-VendorPrequal_Register_v01.xlsx`. Work there and import later;
  the workbook columns mirror the DDL 1:1 so the import maps without transformation.
- **Never** silently fall back to a private or ad-hoc Notion page. If the write fails, say
  so and write to the workbook. This is a block-quota failure, distinct from the
  query-quota failure `notion-quota-fallback` covers.

## Step 2 — Nameplate capture

The defining rule of this skill: **`Nameplate Verified` is TRUE only when the model and
serial came off the physical plate and the photograph is filed.** A contractor's statement
is `Nameplate Source = Contractor report`. A prior invoice is `Prior invoice`. An educated
guess from vintage is `Estimated`. None of those are verification, and the distinction is
the entire value of the field.

Capture per asset: manufacturer, model, serial, capacity as rated, gas input MBH,
refrigerant, efficiency rating, install date or estimated install year, location, and
whether it is roof-mounted.

Leave unknowns **blank**. A blank is a finding that generates a site visit; an inferred
value is a fabrication that survives forever and gets underwritten against. Do not infer
refrigerant from vintage, capacity from square footage, or install year from a
manufacturer's serial-number scheme without verifying that scheme.

The cheapest capture window is **whenever a technician is already on the asset** — a
service call, a PM visit, a bid walk. Standing ask to every vendor: photograph the
nameplate. It costs them thirty seconds.

## Step 3 — Life scoring

```
Replacement Year     = Install Year + Expected Useful Life
Remaining Life (yrs) = Install Year + Expected Useful Life − current year
```

Both are formula fields. Do not overwrite them with typed values.

Default expected useful lives — ASHRAE service-life data and standard industry practice.
Override per asset where condition warrants, and record why in Notes.

| System | EUL (yrs) | Note |
|---|---|---|
| Packaged RTU, gas/electric | 15–20 | use 20 for shallow-bay light duty |
| Split-system DX | 15 | |
| Furnace | 18–20 | |
| Boiler | 25–35 cast iron · 20–25 steel | |
| Commercial gas water heater | 10–12 | |
| Single-ply roof (TPO/EPDM) | 20–25 | warranty term is not the EUL |
| Modified bitumen / BUR | 20–30 | |
| Asphalt lot, overlay | 15–20 | seal-and-stripe cycle is 3–5, separately |
| Electrical panel / switchgear | 30 | |
| Overhead door | 20–25 | springs 10 |
| Fire sprinkler piping | 40–50 | alarm panel 15–20 |
| LED lighting | 15 | drivers 10 |
| Elevator | 25–30 | to modernization |

**Condition observed overrides age computed.** A unit with 4 years of nominal life left and
a failed compressor is `End of Life`, not `Fair`. Age is the planning input; condition is
the decision input.

## Step 4 — Replacement pipeline and the capital plan

Assets with `Remaining Life` ≤ 3, or `Condition` of Poor / End of Life / Failed, are the
replacement pipeline. For each, carry `Est. Replacement Cost` and `Lease Recovery`.

`Lease Recovery` defaults to **Unreviewed** and may only be set after reading the governing
lease. Landlord capital not recoverable, landlord capital amortizable into CAM, and tenant
obligation are three different answers with materially different economics — on a ~$28K
rooftop unit, CAM amortization over a 15-year life is roughly $2,500–3,300/yr recoverable
`[FORECAST, rate-dependent]`. Guessing this field is worse than leaving it blank.

Hand the pipeline to `annual-cycle`, which owns the annual budget and powers the
`ora-annual-budget-kickoff` scheduled task (Nov 1). This skill supplies the asset-level
inputs; it does not set reserve levels or approve spend.

## Step 5 — The two flags that trigger other gates

- **`Roof-Mounted` = TRUE** triggers the roof-coordination gate on *any* trade mobilizing
  onto that roof, not only roofing work. A crane set, a curb adapter or a new penetration
  all qualify. Membrane patching and roof-warranty survival must be assigned in writing
  before work starts. Enforced in `capital-bid-comparison` Step 5 and `vendor-management`.
- **`Rebate Status`** must move off *Not Checked* before any replacement over $10,000 is
  awarded, because the eligible specification has to be inside the awarded scope. *Not
  Checked* on a completed replacement is a process failure to report.

## Step 6 — Report

For a portfolio sweep: assets by remaining life ascending, the ≤3-year pipeline with
estimated cost and recovery treatment, and — separately and prominently — **the coverage
gap**: how many assets are registered, how many are nameplate-verified, and which
properties have no registered assets at all. Report the gap as a count, never as an
impression. An incomplete register that presents as complete is more dangerous than no
register.

Deliver as XLSX per the ORA Institutional Style Guide, named
`YYYY-MM-DD_AssetRegister_[Scope]_v##.xlsx`.

## Scope boundaries

| Situation | Skill |
|---|---|
| What is installed, how old, when to replace | **this skill** |
| Comparing bids to replace it | `capital-bid-comparison` |
| Pre-signature defect scan of the winning proposal | `vendor-management` QC mode |
| Vendor prequalification, COI, performance | `vendor-management` MANAGE mode |
| Annual budget and reserve levels | `annual-cycle` |
| Recording the spend once incurred | 🔧 CapEx & Maintenance Log |
| Insurance premium history and renewal | `insurance-renewal-review` |
| Tenant-level risk and WALT | `tenant-intelligence` |

## Hard rules

- **Never fabricate an asset attribute.** Blank beats inferred. No model decoded from
  memory, no refrigerant inferred from vintage, no capacity inferred from square footage.
- **`Nameplate Verified` requires a filed photograph.** Nothing else sets it TRUE.
- **`Lease Recovery` requires the lease.** Unreviewed is the honest default.
- This skill **records and plans**. It does not approve capital spend, set reserves, or
  award work.
- Report register coverage as a count on every portfolio-level output. Never let an
  incomplete register read as complete.

## Changelog

- **v1.0 (2026-09-17) — initial.** Created after the 9050 Red Branch Rd Unit K rooftop
  replacement, where the outgoing unit's age and manufacturer were unknown to ORA until a
  bidding contractor read the nameplate, and its model and serial were never captured.
  Schema frozen as `2026-09-17_BuildingAssetRegister_NotionDDL_v01.sql`; Notion creation
  deferred on the workspace free-block cap, interim register shipped as
  `2026-09-17_AssetRegister-VendorPrequal_Register_v01.xlsx`. Grain deliberately separated
  from the pre-existing 🔧 CapEx & Maintenance Log (spend events) rather than extending it.