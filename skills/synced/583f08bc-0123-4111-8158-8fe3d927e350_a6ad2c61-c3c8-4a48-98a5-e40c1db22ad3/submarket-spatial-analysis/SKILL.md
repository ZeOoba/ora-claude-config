---
name: submarket-spatial-analysis
description: Submarket and spatial analysis for ORA properties and acquisition candidates. Use when the user mentions: submarket, spatial analysis, drive time, isochrone, intermodal proximity, highway access, last-mile, demographics, employment density, population growth, MSA, micropolitan, traffic count, locational benchmark, location quality score, GIS, mapping, or any task requiring geographic analysis of properties relative to demand drivers. v1.6 (2026-08-24: see Changelog)
license: ORA Internal
---

# Submarket Spatial Analysis

Analyze ORA properties and acquisition candidates against spatial demand drivers: highway access, intermodal proximity, last-mile geography, employment, and demographics.

## Scope

Covers all ORA target markets (OH, MD, IN, WI, MO, KS, TN) and submarkets within them. Used for acquisition screening, tenant-mix optimization, and disposition evaluation.

## Triggers

Acquisition candidate location scoring, submarket comparison, intermodal proximity check, drive-time analysis, demographic profile, employment growth check, last-mile suitability scoring.

## Inputs

- Notion property database (lat/long for each ORA property)
- Census ACS data (demographics, employment) — public APIs
- BTS NTAD (highway, rail, intermodal) — public data
- Web search / Firecrawl for nearby anchor tenants and points of interest (no dedicated places/POI API is connected — this is a manual lookup, not a live query)
- Web search for submarket reports (CBRE, Cushman, JLL)
- **Drive-time routing** (see Drive-Time Method below): OpenRouteService (ORS) public API — `[GG: ORS API key needed — free signup at openrouteservice.org; set ORS_API_KEY in the environment]` — with a keyless OpenStreetMap-based OSRM public server (`router.project-osrm.org`) as fallback.

## Standard Workflows

### Drive-Time Method (resolution ladder — try in order, label the result honestly)

Any step that needs a drive-time (isochrone population, labor pool, distance-to-anchor by road) resolves the travel time through this ladder and **states which tier produced the number** in the output:

1. **OpenRouteService (ORS) — preferred, needs a free key.** If `ORS_API_KEY` is present, call the ORS public API:
   - Matrix (many origins→destinations, durations): `POST https://api.openrouteservice.org/v2/matrix/driving-car` with header `Authorization: {ORS_API_KEY}`, body `{"locations": [[lon,lat],...], "metrics": ["duration"]}`.
   - Isochrones (true drive-time polygon for ring population): `POST https://api.openrouteservice.org/v2/isochrones/driving-car`, body `{"locations": [[lon,lat]], "range": [1800], "range_type": "time"}` (1800 s = 30 min). Intersect the polygon with Census block-group centroids for the 30-min population/labor pool.
   - Free tier ≈ 2,000 matrix calls/day, 500 isochrone calls/day — ample for ORA volume. Label: **"drive-time: ORS road network"**.
   - `[GG: ORS API key needed — free signup at openrouteservice.org]`
2. **OSRM public server — keyless fallback (verified live 2026-07-18, independently re-confirmed 2026-07-19 via a real `route` + `table` request between Columbus OH and Rickenbacker Inland Port — both returned valid duration/distance).** If no ORS key, use the public OSM demo server (no key, best-effort, rate-limited — never for bulk production):
   - Route (point-to-point duration/distance): `GET https://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=false` → `routes[0].duration` (seconds), `.distance` (m).
   - Table (durations matrix): `GET https://router.project-osrm.org/table/v1/driving/{lon1,lat1;lon2,lat2;...}?annotations=duration` → `durations` matrix (seconds).
   - OSRM has **no isochrone endpoint** — for ring population, sample candidate block-group centroids within a straight-line radius and keep those whose table-driving-time ≤ threshold. Label: **"drive-time: OSRM public OSM server (best-effort)"**.
3. **Straight-line approximation — LAST resort, always labeled as such.** If both ORS and OSRM are unavailable/erroring, estimate: road distance ≈ great-circle × 1.3 detour factor; time ≈ distance ÷ assumed speed (55 mph highway / 30 mph arterial / 20 mph urban). Label: **"drive-time: straight-line estimate (no routing service) — REPLACE with ORS/OSRM before any IC-grade figure"**.

Never present a tier-3 estimate as a routed figure; the tier label is mandatory in every memo/scorecard cell that carries a drive-time.

### Acquisition Location Score (1–100)
1. Distance to nearest interstate (weight 25%).
2. Distance to nearest intermodal (BNSF, NS, CSX) — for industrial (weight 20%).
3. 30-min drive-time population (weight 15%) — resolve travel time via the Drive-Time Method ladder above (ORS → OSRM → straight-line), labeling the tier.
4. 30-min drive-time labor pool of relevant occupations (weight 15%) — same Drive-Time Method ladder for the ring, PLUS a mandatory sub-step: metro-level bachelor's+ educational attainment, confirming labor QUALITY (not the ring itself — see Boundaries). **Primary method (2026-08-24): Esri ArcGIS Living Atlas hosted keyless FeatureServices** — `ACS_Highlights_Population_Housing_Basics_Centroids` (org `P3ePLMYs2RVChkJx`, county/tract layers, population/age bands, ACS 5yr current vintage) for the population/age cut, and `ACS_Educational_Attainment_Boundaries` (same org, same vintage, table B15002) for attainment — both keyless, paginated via `resultOffset` (maxRecordCount=50/request). Query every county in the subject property's metro CBSA and sum; cite as "CONFIRMED (Esri ArcGIS Living Atlas, ACS 5yr B15002/B01001, keyless FeatureService)". **Known gap:** Living Atlas layers auto-update in place annually and do NOT preserve versioned historical snapshots (confirmed 2026-08-24 — two candidate historical `arcgis.com/sharing/rest/content/items/{id}` lookups either 404'd or resolved back to the current live service), so the 5-year-prior anchor (e.g. 2019 vs. current) this step used to pull from `census-acs-extract` is NOT obtainable this way — report the current-year attainment level/share only and flag the 5-year delta as an explicit UNVERIFIED gap rather than fabricating or omitting it silently. **Fallback, if `CENSUS_API_KEY` is ever provisioned:** `api.census.gov`'s ACS 5-year table API restores both the current AND historical vintage in one call (table B15003), closing the delta gap — prefer it over Living Atlas the moment a key exists, and update this line + Boundaries together when that happens.
5. Submarket vacancy and rent growth trend (weight 15%).
6. Major employer / anchor tenant proximity (weight 10%).
7. Output: location score memo (DOCX) with composite score and component breakdown.

### Submarket Comparison
1. Compare 2+ submarkets across the same dimensions.
2. Normalize scores; produce ranking.
3. Output: submarket comparison memo (DOCX) with side-by-side table.

### Last-Mile Suitability
1. Distance to population centers (5/10/15 mile rings).
2. Truck-court and dock-door inventory.
3. Highway access / signal density.
4. Output: last-mile scorecard (xlsx).

### Tenant Mix Optimization
1. For an existing property, plot current tenants by industry.
2. Identify gaps relative to submarket employment composition.
3. Output: tenant mix recommendation memo (DOCX).

## Outputs

- DOCX memos with embedded maps where possible
- xlsx scorecards
- Mirror to SharePoint /Acquisitions/[deal]/Spatial/
- File naming: YYYYMMDD_[Property-or-Submarket]_Spatial_v##.docx

## Boundaries

- Forecasts of demographic change marked [FORECAST].
- Census data lag is acknowledged (typically 12–24 months).
- Drive-time figures follow the Drive-Time Method ladder (ORS road network → keyless OSRM public server → straight-line estimate) and **must state which tier produced them**. ORS needs a free API key (`ORS_API_KEY`; see the placeholder in Inputs) — until it is set, live routing runs on the keyless OSRM public server (best-effort, not for bulk production), and only falls to a straight-line estimate if both are unavailable. If a dedicated routing MCP connector is ever added, prefer it and update this line and tech.md together.
- **Metro attainment (step 4) permanently repointed 2026-08-24** to the keyless Esri ArcGIS Living Atlas FeatureServices (`ACS_Highlights_Population_Housing_Basics_Centroids` + `ACS_Educational_Attainment_Boundaries`, org `P3ePLMYs2RVChkJx`) — `census-acs-extract` retired 2026-08-05 with no successor, and its archived script (`_archive/census-acs-extract_retired-2026-08-05/census_acs_extract.py`) is not present in every session's synced-skills cache (confirmed absent 2026-08-24; only lives in the full `ora-skills` repo checkout), so it is no longer a dependable manual fallback either. Living Atlas closes the CURRENT-year attainment confirmation but not the 5-year-anchor delta (layers overwrite in place, no versioned history — see step 4). `api.census.gov` now hard-requires `CENSUS_API_KEY` (returns an HTML "Missing Key" page with none set, confirmed 2026-08-24) — provisioning that key is the one fix that restores both current AND historical vintage in a single call; until then, report the delta as UNVERIFIED. Don't conflate attainment with the drive-time ring: a CONFIRMED attainment figure does not mean the drive-time ring is routed at ORS/OSRM quality — check the tier label on that figure separately.

## Dependencies

- acquisition-underwriting skill (consumes location score for IC memo)
- acquisition-underwriting skill's COMP GRID DISCIPLINE section (rental rate inputs — flows the opposite direction from the location-score dependency above; the retired `rent-comp` skill, gone 2026-08-05, previously supplied this)
- market-monitor skill (submarket trends)
- docx skill (memo deliverables)
- Esri ArcGIS Living Atlas keyless FeatureServices (`ACS_Highlights_Population_Housing_Basics_Centroids`, `ACS_Educational_Attainment_Boundaries`) — permanent replacement for the retired `census-acs-extract` (Location Score component 4, metro labor-quality/attainment); see Boundaries for the historical-vintage gap this substitution does not close.

## Changelog

- v1.6 (2026-08-24): Permanently repointed Location Score step 4's metro attainment sub-step from the retired `census-acs-extract` (and its archived script, confirmed absent from this session's synced-skills cache — it only lives in the full `ora-skills` repo) to the keyless Esri ArcGIS Living Atlas FeatureServices already used as a same-day workaround during the Knopp Ave / Cane Run Rd (Louisville) DD pass. Documented a real limitation surfaced during that pass: Living Atlas layers auto-update in place with no versioned historical snapshots, so the step's 5-year-anchor delta is no longer obtainable this way and must be reported as an explicit UNVERIFIED gap rather than the archived script's CONFIRMED band — recommended `CENSUS_API_KEY` provisioning as the fix that restores it. No Location Score weight or Drive-Time Method rung changed.
- v1.5 (2026-08-15): HIGH fix (Skill Text Audit finding F3) + LOW fix (finding F9). The Dependencies list's `rent-comp skill (rental rate inputs)` line was orphaned by that skill's 2026-08-05 retirement; repointed to acquisition-underwriting's COMP GRID DISCIPLINE section (absorbed there 2026-08-12) and reworded to avoid reading as a duplicate of the existing acquisition-underwriting (location-score) dependency above it — the two flow in opposite directions. Also moved the v1.4/v1.3 changelog prose that had accumulated in the description field down here (both already existed in this section, so the description copies were pure duplication); description now carries a single trailing version tag. No Location Score weight, Drive-Time Method rung, or scoring math changed.
- v1.4 (2026-08-12): Tombstoned the three `census-acs-extract` references left dangling by that skill's 2026-08-05 retirement (zero-use, no successor named). Location Score component 4's attainment sub-step is now an explicit MANUAL pull, with a pointer to the still-runnable archived script (`_archive/census-acs-extract_retired-2026-08-05/census_acs_extract.py`, whose `extract_metro_attainment(year)` and `ANCHORS` dict both still work). The step was previously an unexecutable instruction naming a skill that no longer exists. No Location Score weight or Drive-Time Method rung changed.

- **v1.3 (2026-07-20):** Reconciled two independent, previously-unmerged lines of work that had drifted into a version collision:
  - Recovered the Drive-Time Method resolution ladder (ORS keyed API → keyless OSRM public server → straight-line estimate last, each tier honestly labeled) from a stale unmerged commit (`b5ad834`, 2026-07-19) sitting in the `next5-sourcing-data` worktree — OSRM public server (`router.project-osrm.org` route + table endpoints) verified live 2026-07-18, re-confirmed 2026-07-19. That commit's companion `ora-flood-zoning-dd` edit was NOT carried forward — it cross-linked a `county-parcel-screen` skill and `county-endpoints.v1.json` registry that do not exist anywhere in this repo's history (confirmed via full-history search); that half of the branch rests on a phantom dependency and was left out.
  - Retained the `census-acs-extract` metro labor-quality/attainment confirmation added earlier the same day (was tagged v1.2, 2026-07-20). Location Score steps 3/4 and the Boundaries section now clearly separate the two: the Drive-Time Method ladder resolves the population/labor-pool ring; census-acs-extract confirms labor quality (attainment) at the metro level.
- **v1.2 (2026-07-18, unmerged until this reconciliation):** Drive-Time Method ladder added (ORS → OSRM → straight-line).
- **v1.1 (2026-07-16):** Removed references to mcp__places/ESRI/Mapbox/OSRM as connected tools (none were connected); drive-time/nearby-anchor steps stated the actual method used.
