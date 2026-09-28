---
name: insurance-climate-risk-comparison
description: "Compares insurance costs and natural-disaster/climate-change risk for a target market against the national average and Oxford Realty Advisors' other target markets, for underwriting and market-entry decisions. Use when the user mentions: insurance cost comparison, climate risk, natural disaster risk, climate change risk, disaster exposure, hazard risk, how a market compares on insurance or climate, or is evaluating a new/entry-phase target market and needs its risk profile benchmarked against the portfolio. Pulls FEMA National Risk Index composite + per-hazard scores by county, and insurance $/SF (ORA's own realized premiums where owned, a public proxy elsewhere). Distinct from insurance-renewal-review (single-property premium history/renewal decisions) and ora-flood-zoning-dd (single-parcel FEMA flood-zone/zoning DD-Critical gate) — this skill is MARKET-level and comparative, and never gates a deal. v1.0"
---

# Insurance & Climate Risk Market Comparison (ORA) — v1.0

Purpose: given a target market, answer "how exposed is this market to insurance cost and natural-disaster/climate risk, relative to the national picture and to ORA's other target markets" — for underwriting judgment and market-entry decisions. This is reference context, not a gate: it does not touch acquisition-underwriting's Buy Box scorecard, Stage 1 floors, or any governor constant (DSCR/LTV). Gabriel applies the judgment; this skill supplies the sourced comparison.

## Relationship to other skills — read this before starting

- **insurance-renewal-review** owns premium HISTORY and the renewal decision for ORA's own already-owned properties, built from carrier declarations. This skill READS its output (the latest Premium-History workbook) for realized $/SF — it never re-derives or second-guesses that data, and it never opens or OCRs a declarations PDF itself.
- **ora-flood-zoning-dd** resolves FEMA flood-zone (NFHL) and zoning at the SINGLE-PARCEL level as a DD-Critical acquisition gate (SFHA on the pad = kill). This skill is MARKET-level, uses FEMA's National Risk Index (a county-level composite hazard score across 18 hazard types, not a parcel flood-zone determination), and never gates anything. If a specific parcel is already in DD, ora-flood-zoning-dd is still the authority on its flood/zoning status — this skill's output is broader market context, not a substitute.
- **market-monitor / target-markets.json** is the canonical list of ORA's 10 target-market clusters (Columbus OH, Cincinnati OH, Kansas City MO/KS, Indianapolis IN, Maryland/Baltimore-DC, Madison WI, Grand Rapids MI, Richmond VA, Des Moines IA, Louisville KY) and owns market fundamentals (vacancy, rent, cap rates, replacement cost). This skill treats that cluster list as the fixed comparison universe. **If target-markets.json and this skill's market list ever diverge, target-markets.json wins** — same convention every other consumer of that file follows.

## Design decision: no static county map

It would be tempting to hardcode a cluster→county table once and reuse it. **Don't.** This repo has been burned repeatedly by exactly that pattern — see `target-markets.json`'s own changelog entries on stale `consumers` arrays and cross-file parity drift. A static table here would be a second, unowned copy of information that changes as ORA's exposure within a cluster shifts (new submarket, new county). Instead, **resolve the representative county for each cluster at runtime**, every run, the same way `ora-flood-zoning-dd` resolves a parcel (Step 1 below) — using whatever address/submarket is currently recorded in `target-markets.json` or `market-monitor`. This costs a few extra geocoder calls per run; it does not cost a maintenance liability.

## Workflow

### Step 1 — Resolve each market to a representative county

For the target market and for each of the other 9 clusters:

1. Pull the cluster's current submarket/property list from `target-markets.json` (preferred) or `market-monitor`.
2. Take one representative address already on record — an ORA-owned property if the cluster has exposure (`has_existing_exposure: true`), otherwise a named submarket center.
3. Geocode via the Census geocoder (same endpoint `ora-flood-zoning-dd` uses):
   `https://geocoding.geo.census.gov/geocoder/locations/onelineaddress?address={URL-ENCODED ADDRESS}&benchmark=Public_AR_Current&format=json`
4. Read `STATEFIPS` + `COUNTYFIPS` (or county name) from the geocoder's `addressComponents`. **Do not** carry over `ora-flood-zoning-dd`'s parcel-boundary validation step here — that guards against a point landing outside a specific parcel, which doesn't apply at county granularity — but DO sanity-check the returned county/state against the cluster's known state (a geocode returning the wrong state is a hard stop, not a data point).
5. **Multi-county clusters:** some clusters genuinely span more than one county or state (Kansas City MO/KS is the clearest case — ORA's own `target-markets.json` flood_note already documents Kaw River bottoms exposure split across Wyandotte County KS (Fairfax/Armourdale) and Jackson County MO (West Bottoms)). When a cluster's recorded submarkets span multiple counties, pull NRI for each and report the range, not just one county — collapsing a bi-state cluster to a single county would silently drop real risk variance.

### Step 2 — Pull FEMA National Risk Index data per county

Source and field reference: `references/data-sources.md`. In short — query the NRI Counties ArcGIS FeatureServer by `STCOFIPS`, read the composite `RISK_SCORE` / `RISK_RATNG` and the per-hazard `[HAZARD]_RISKS` / `[HAZARD]_RISKR` fields for the hazards that matter to shallow-bay industrial (flood — riverine `IFLD` and coastal `CFLD`, wind — hurricane `HRCN` and tornado `TRND`, severe winter weather `CWAV`, hail `HAIL`, earthquake `ERQK`, drought `DRGT` for the water-stress angle on climate change).

**"National average" methodology — state this explicitly in the output, don't imply a number that doesn't exist.** NRI's `RISK_SCORE` and `RISK_RATNG` are already nationally-normalized (the rating tiers — Very Low / Relatively Low / Relatively Moderate / Relatively High / Very High — are defined against the national distribution of all ~3,200 counties). There is no separate "national average county" to query. Report the score, the rating tier, and frame the tier itself as the national-average reference point (e.g. "Relatively Moderate ≈ national middle band") rather than fabricating a synthetic national mean.

### Step 3 — Pull insurance cost per market, two-tier

1. **ACTUAL:** for any cluster with `has_existing_exposure: true`, ask Gabriel for (or locate) the latest Premium-History workbook from `insurance-renewal-review`'s most recent run and pull realized $/SF from its Summary tab, aggregated to the market. If no recent workbook exists or the property isn't in it yet, don't guess — fall through to PROXY and say why.
2. **PROXY:** for every other cluster (and any ACTUAL cluster missing current data), pull a public benchmark per the ladder in `references/data-sources.md` — there is no clean, free, state-level *commercial* property insurance rate dataset (verified 2026-09-11: NAIC's own homeowners report is the closest free government-adjacent source and even it is residential, several years stale, and NAIC itself cautions against direct state comparisons). Use the ladder's rung 1 source when available; fall to rung 2 (a named aggregator) only when rung 1 has no coverage for that state, and label it AGGREGATOR explicitly per ORA's sourcing hierarchy (primary sources first, aggregators last-resort).
3. **Every insurance figure in the output must carry its tier tag inline — ACTUAL / PROXY-GOV / PROXY-AGGREGATOR.** Never present a proxy figure with the same visual weight as a realized premium. This mirrors the `hard_cost_flag: SOURCED/PROXY` convention already used in `target-markets.json`'s replacement-cost blocks — reuse that convention, don't invent a new one.

### Step 4 — Build the comparison table

One row per: target market, national reference, and each of the other 9 clusters (fewer if the user asked for a narrower comparison set). Columns:

| Market | NRI Composite Score | NRI Rating | Top 3 Hazards (score) | Insurance $/SF | Tier |
|---|---|---|---|---|---|

### Step 5 — Narrative flags

Below the table, call out in plain language:
- Any market scoring materially above the portfolio average on composite risk or $/SF (say how much, and which hazard is driving it).
- Any single-hazard outlier even if the composite looks fine — a market can be "Relatively Moderate" overall while carrying a "Very High" flood or hurricane sub-score that a composite number hides.
- **Cross-reference, don't re-derive, existing DD flags.** `target-markets.json` already carries a standing flood note for Kansas City (Kaw River bottoms / Fairfax Industrial Park / Armourdale / West Bottoms, behind the UG/USACE levee system). If NRI corroborates a flag that's already on record, cite it and move on — don't re-run analysis that's already been done and ratified.

### Step 6 — Output

Default: markdown comparison table + narrative memo, inline in chat. Only write a file to `/outputs/` if Gabriel asks for a persisted copy, using ORA's session-output naming (`YYYY-MM-DD_Topic_DocType_v##.ext`).

## What this skill deliberately does not do

- Does not modify acquisition-underwriting's scorecard, Stage 1 floors, or any governor constant.
- Does not run on a schedule — on-demand only. (Nothing here precludes adding a scheduled refresh later via `register-scheduled-task` if the comparison set proves useful often enough to warrant it — FEMA NRI updates roughly annually, so a quarterly or semi-annual cadence would be more than sufficient if ever added.)
- Does not substitute for `ora-flood-zoning-dd`'s parcel-level DD-Critical flood/zoning gate, or for `insurance-renewal-review`'s renewal decision.

## Changelog

v1.0 (2026-09-11): Initial skill, built from a brainstormed and Gabriel-approved design. FEMA NRI Counties ArcGIS FeatureServer endpoint and field names verified live the same day (`references/data-sources.md`). No clean free primary source exists for state-level commercial property insurance rates — documented the two-rung PROXY ladder and the ACTUAL/PROXY-GOV/PROXY-AGGREGATOR tagging convention rather than presenting proxy figures as equivalent-confidence to ORA's own realized premiums.
