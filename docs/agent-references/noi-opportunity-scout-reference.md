# noi-opportunity-scout: reference detail

Read on demand by the `noi-opportunity-scout` agent (`agents/noi-opportunity-scout.md`). Moved out of the agent body on 2026-09-29 to cut the per-dispatch prompt; text below is the original wording, unchanged. Load the section you need; do not read the whole file by default.

## A. Live firm data: fallback order when the data tabs cannot be reached

The M365 workbook render is capped at the first 9 (hidden infrastructure) sheets, so `startPage` will not reach `Property NOI` or the rent roll. The live workbook is also routinely held open (Errno 13), which defeats the Excel MCP and SharePoint paths. Try, in order: (a) `C:\Users\Owner\oxford-command-center\data\snapshots\portfolio.json`, a read-only extract of the live workbook regenerated each weekday by ora-lease-snapshot-refresh and weekly by ora-cc-snapshot-refresh (keys include `properties`, `leases`, `loans`, `cash`, `insurance`, `governors`, `workbookTotals`, `dataQuality`); cite `meta.generatedAt` and mark it STALE if it is more than 7 days old; its rows carry workbook values as entered (e.g. hard-coded $0 expenses), so flag them, never correct them; (b) a locally synced copy read with the `mcp__excel__*` tools, found with a targeted Glob under the ORA OneDrive folder (never a broad recursive search, which times out); (c) the workbook's `Claude Log` sheet, which narrates every cell write with before and after values; (d) the Notion Tenant Database (`collection://b12f4cfd-a995-4755-8341-6435ae8173b4`), which reconciles to total SF and is the best source for the unit-level rent roll, then the Notion Property Register and Debt Snapshot pages (the Register is often stale and has carried wrong purchase dates and entities). State which rung you used and mark anything from rung (c) or (d) "one remove from source".

## B. Lease and operating-agreement text

Available as text extractions in `C:\Users\Owner\.claude\data\property-fact-base\<slug>_src\EXTRACT__*.txt` (produced by `_tools\sidecar_extract.py`); Glob and `Read` them before reporting any lease, amendment, OA or settlement statement PDF/DOCX as unreadable. OCR pages are marked `[ocr]` in their page header (`===== PAGE N [ocr] =====`): quote them, but verify any figure that drives a ranking against a second source.

## C. Per-property fact bases

`C:\Users\Owner\.claude\data\property-fact-base\<property>.json`. Check for one first; it carries parcel IDs, land area, coverage, building facts, zoning, association covenants and the appraisal, each with a source and a CONFIRMED / INFERRED / CONFLICT / NOT FOUND status. Use it in place of re-deriving those fields, honor every status, and resolve or flag each CONFLICT rather than picking a side. Its `still_needed` list is the remaining gap list for that property. A field marked NOT FOUND, INFERRED or illegible is unverified unless `_meta.corporate_folder_read_*` records a `recheck_*` against the Corporate and Settlement folder (the original builds never searched it, so price, lender, operating-agreement and chain-of-title NOT FOUNDs were wrong); say so and mark any verdict resting on such a field "one remove". If no fact base exists, the fields are DATA NEEDED. Each fact base may have a `_src` sidecar folder holding text-layer extractions and page images of key source documents; `Read` those. You have no shell and `Read` cannot render PDFs, so if a source PDF is unreadable, say so, mark every verdict that depends on it "one remove", and list the PDF and pages the caller should pre-extract into the sidecar. Never state that you re-verified something you could not open.

## D. Incentive registry handling

`C:\Users\Owner\.claude\data\incentive-registry.json`. Read it first for any tax, energy or environmental idea. Every row carries a verification level and a retrieved date. Treat rows as leads to re-verify, never as final authority. Read each row's `scope_note` and `open_questions`; a same-day row still needs a SCOPE check against the property (jurisdiction, utility type, acquisition year, lease structure) before it drives an idea. Skip rows with status CLOSED or WINDOW_CLOSED except to cite them as history. Anything the registry lacks for the property's serving utility is a gap to research, not a reason to assume.

## E. Lenses (run all five on every property in scope)

1. **Tax structure.** Cost segregation and Form 3115 catch-up on assets not yet studied; abatements (Ohio CRA, enterprise zone) on planned renovation capex; opportunity-zone and 1031 angles on any disposition or recap; parcel or land splits that change assessment. Section 179D is closed for construction beginning after 2026-06-30; do not propose it except for work already begun. Appeals belong to `tax-appeal-scout`.
2. **Land and space.** Outside storage, trailer and truck parking, container storage, laydown yards, EV or fleet charging, outparcel sale or ground lease, mezzanines, demising, small-bay conversion, dead-space reuse. All income here is `[SPECULATIVE]` until a local operator or broker quote exists.
3. **Energy.** Rooftop or community solar (hand to `solar-lease-underwriting`), storage, demand response on meters ORA controls, house-meter supply aggregation across the ~20 LLCs, LED and efficiency work. Ohio utility efficiency rebates ended in 2020; do not assume they exist. Third-party submetering carries regulatory risk in Ohio; a landlord's own incidental resale is exempt.
4. **Environmental.** Stormwater fee credits, C-PACE for tenant-recovered capital, brownfield and voluntary-action programs only where a Phase I or known condition supports it, cool-roof programs.
5. **Ancillary income.** Cell tower and small-cell rooftop leases, billboard or signage on road frontage, easements, telecom access, parking or storage fees. ORA has a realized precedent: FVC closed a $500K one-time cell-tower easement sale in 2025. Look for the same play elsewhere.

Not your lenses, hand off instead: appeals (`tax-appeal-scout`), CAM under-recovery and missed escalations (`portfolio-anomaly-scout`), insurance rebid (`insurance-renewal-review`), service-contract rebid (`vendor-management`), mark-to-market rents (the renewal-comps runs, `market-monitor`). If you notice one in passing, name it in one line and route it; do not size it.

## F. Near-term program dates to check first

The federal solar credit placed-in-service cutoff of 2027-12-31, the Maryland net-metering closing date of 2027-07-01, the Howard County stormwater credit filing deadline of April 1, and Ohio opportunity-zone transition relief on 2026-12-31.

## G. Tax-lens ideas: detail

Cost segregation, depreciation timing and abatements on capex change after-tax cash, not NOI, and create no value at a cap rate. For these:
- State NOI delta as $0 and value as $0. Never launder a tax benefit into the NOI field.
- Report a second metric, **one-time after-tax cash** (or annual after-tax cash), with the arithmetic and every unverified input labeled. The taxpayer profile (passive-activity status, member marginal rates) is not documented anywhere, so treat usability of any deduction as UNVERIFIED and hand the sizing to the CPA.
- Rank tax ideas in a separate short section after the NOI-ranked list, ordered by after-tax cash times probability.
- In the ledger row, never file a tax idea as `Revenue Enhancement`; use `Combined` or the closest non-revenue type and put $0 in the NOI field.
- Bonus depreciation likely does not apply to cost-seg pools on existing buildings acquired before 2017-09-28. Check the acquisition date before assuming it; the gain on those assets is the straight-line acceleration only. CPA confirms.
