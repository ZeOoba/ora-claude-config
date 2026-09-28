# Verified County Endpoints — ORA Parcel Data Recovery (v3)

> **Companion registry — read this before assuming either file is the whole picture (added 2026-09-06, ORA Automation Audit R23-8).**
> `county-parcel-screen/references/county-endpoints.v1.json` is the machine-readable registry of **parcel-geometry / CAMA layer**
> endpoints across 22 ORA target counties. **THIS file is different in kind:** it holds the **building-footprint, CAMA-detail and
> bulk-export** endpoints (FEMA USA Structures, county building outlines, Beacon/Schneider, auditor data exports) plus per-county
> match rates, statutory assessment ratios and value-basis calibration — the things a *recovery* pass needs and a *screen* does not.
>
> **They are complementary, not duplicates, and neither supersedes the other.** Measured 2026-09-06 against the FULL human-readable
> source of truth (`county-parcel-screen/references/county-endpoints.md`, 46 URLs): of the 17 URLs in this file, exactly **3 are
> shared** and **14 are unique to recovery work**. An audit pass read the overlapping county names as a dual-write pair and came
> within one step of merging them, which would have deleted those 14. If you are tempted to consolidate these, diff the URLs first —
> the counties overlap, the endpoints do not.

Replaces `references/endpoints.md` (v2). v3 additions (2026-07-12): Cincinnati/Hamilton OH CAGIS
outage re-confirmed live + OGRIP/FEMA bypass added; Chesterfield VA `ASSESSED` field-deprecation
root-caused (renamed, not removed) + endpoint added; Des Moines/Dallas IA metro researched for the
first time (Polk endpoint candidates + Dallas no-bulk-API confirmation).

## ⚠️ v2 critical corrections (carried forward)
- **Jackson MO `total_sqft` is LAND area, NOT building SF** (v1 was wrong — it equals the screen "Land
  SF"; a 195,971 parcel survived the >50K-SF kill gate). Use FEMA USA Structures (below) for Jackson
  building SF.
- **Marion IN `ESTSQFT` is LOT square footage, not building** — never use as building SF.
- Always run the **land-vs-building unit-assertion gate** (SKILL.md QC, Edit 2) before shipping any
  recovered SF.

## ⚠️ v3 new findings
- **CAGIS (Hamilton County OH) confirmed down again as of 2026-07-12** — not a stale note. Tested
  `cagis.hamilton-co.org`, `cagisportal.hamilton-co.org`, `cagisonline.hamilton-co.org` including a
  search-confirmed *existing* live sub-service (`HCSWD_Stormwater`) — all unreachable. Control test
  against Franklin OH / Butler OH on-prem ArcGIS Servers succeeded on the identical call pattern,
  ruling out a general network issue. See new Hamilton section below for the OGRIP+FEMA bypass.
- **Chesterfield VA `ASSESSED` was never removed — it was split** into `TotalAssessment`,
  `FairMarketValue`, `LandUseValue`, `ImprovementValue` on a live, non-deprecated-in-practice service
  (the AGOL *item* is flagged deprecated in metadata; the *service* still runs current schema). See
  new Chesterfield section.
- **Des Moines/Dallas IA researched for the first time this pass** — Polk County has a real ArcGIS
  Server but it was unreachable from the research sandbox on 2026-07-12 (needs off-sandbox retest,
  not yet ruled dead); Dallas County confirmed to have **no bulk API** — Beacon/Schneider only.

## FEMA USA Structures — universal building-SF fallback
For any county with no usable footprint/CAMA building source:
- **Service:** `https://services2.arcgis.com/FiaPA4ga0iQKduv3/arcgis/rest/services/USA_Structures_View/FeatureServer/0`
  — field `SQFEET` (true building sq ft; vintage ~2016–2020, post-2020 construction missing).
- **Method:** spatial-intersect FEMA structures with the county parcel polygon; FEMA-vs-county geometry
  is misregistered, so use **Intersects + majority-in (>50%)**, not Contains; for straddlers,
  area-proportional clip. Take area from `SQFEET`, never recompute from Web Mercator.
- Footprint = ground-floor floor ⇒ multi-story understated; tag `method=fema_structures_majority_in`.
- Confirmed live 2026-07-12.

## Franklin County, OH (Columbus) — land area + building SF — 1,130/1,132 (99.8%)
- **Endpoint:** `https://gis.franklincountyohio.gov/hosting/rest/services/ParcelFeatures/Parcel_Features/MapServer/0` (layer "Tax Parcel"). Confirmed live 2026-07-12.
- **Join:** `PARCELID`, dashed exactly as screens ship (`010-113471`).
- **Fields:** `STATEDAREA` = land **square feet** (aliased "Legal Acres" but is sq ft — 24,107 = 0.55
  ac); `BLDGAREA` (matches auditor bldg SF); `ACRES` (GIS) is null service-wide — use `STATEDAREA`.
- **FAR:** Bldg SF ÷ `STATEDAREA` directly (STATEDAREA already sq ft — do NOT ×43,560).

## Jackson County, MO (KC) — building SF via FEMA — 1,762/1,839 (95.8%)
- **Building SF:** FEMA USA Structures (above) intersected (majority-in) with parcel polygons
  `https://jcgis.jacksongov.org/arcgis/rest/services/ParcelViewer/ParcelsAscendRelate/MapServer/1`
  (join `Name`, dashed). Jackson County GIS has NO native footprint/structure layer.
- **Land area:** screen "Land SF" (= the Ascend `total_sqft`, which is LAND). **Do NOT use `total_sqft`
  as building SF.**
- **Caveats:** `gis.jacksongov.org` (no `jc`) is a different, unreachable host. Underground complexes
  carry multi-million SF — flag >1M. Ascend "Assessed/Auditor $" is fractional (÷0.32 for market).

## Clay County, MO (KC) — 447/514 (87.0%)
- **Building SF:** footprint layer 0 (st_area) at `https://gisweb.claycountymo.gov/s/rest/services/InternetmapParcel2/MapServer`
  via county proxy `…/proxy/proxy.ashx?<url>` (injects token); layer 3 "Taxable Parcels" for CAMA.
  Renumbered parcels: assessor `/pub/rest/parcels?situs=` (needs Referer).
- **Caveats:** `actual_year_built`/`total_area` residential-only ⇒ commercial SF = footprint. Values
  market-basis (~$30/SF) — no ratio.

## Wyandotte County, KS / UG KCK — 733/797 (92.0%)
- **Building SF:** AGOL `services1.arcgis.com/Qo2HHQp8vgPs2wg3` `Building_Footprint/FeatureServer/1`
  (`Shape__Area`, sq ft) intersected with `Parcel_py_Values/FeatureServer/0` (join `PARCEL_NBR`).
  Footprints ≤2020-12.
- **CRITICAL:** UG's published `SqFootage`/`SQFT` are LAND (≈acre×43,560) — never building.
- **Values:** `Commercial_18_19/FeatureServer/1` (join `PARCEL` string) `AppraisedTotal2019` — STALE
  2019; KS commercial market = assessed/0.25. Live CAMA `landsweb.wycokck.org`/`maps.wycokck.org` was
  down 2026-06-11 — recheck before any Wyandotte reprice.

## Hamilton County, OH (Cincinnati) — ~185 (Top-150 + leads)

**CAGIS native endpoint — CONFIRMED DOWN as of 2026-07-12 (re-tested, not assumed).**
- **Parcels+values (blocked):** CAGIS `…/COUNTYWIDE/AuditorParcelInformation/MapServer/15` (join
  `PARCELID` 12-digit; `MKT_TOTAL_VAL`, `DELQ_TAXES`, `ACREDEED`, `LUCLASS`). Tested three CAGIS
  domain variants 2026-07-12 (`cagis.hamilton-co.org`, `cagisportal.hamilton-co.org`,
  `cagisonline.hamilton-co.org`) — all unreachable, including a confirmed-live sibling service
  (`HCSWD_Stormwater`) on the same host, isolating the failure to CAGIS specifically (control test
  against Franklin OH / Butler OH on-prem servers succeeded on the identical pattern).
- **SF (blocked):** `COUNTYWIDE/PlanimetricLayers/MapServer/6` "Building Polygons" (`SQFT`,
  `EST_STORY`) spatial-intersect with L15 geometry. L17 SQFT is residential-only. Unreachable while
  CAGIS is down.

**Bypass (NEW, live 2026-07-12) — geometry/SF only, values still unresolved:**
- **Geometry + land area:** OGRIP Ohio Statewide Parcels Public View —
  `https://services2.arcgis.com/MlJ0G8iWUyC7jAmu/arcgis/rest/services/OhioStatewidePacels_full_view/FeatureServer/0`
  (AGOL-hosted, bypasses the CAGIS host entirely). Confirmed 354,521 Hamilton County records live.
  Fields: `LocalParcelID`, `StateParcelID`, `LandArea`, `SitusAddressAll`, geometry.
  **Caveat:** this is a redacted "public view" — `MarketValueTotal`/`AssessedValueTotal`/
  `StructureAreaGross` exist in the underlying schema (visible in the field-template prototype) but
  are stripped from the exposed `fields[]` on both `Parcels` (layer 0) and the related `Cama` table
  (layer 1, joined by `StateLinkId`). Geometry + land area only.
- **Building SF:** FEMA USA Structures (above), majority-in intersect against the OGRIP geometry.
- **Values (still open):** not resolved this pass. Candidate path: Hamilton County Auditor's separate
  "wedge" property-search site (`wedge3.hcauditor.org`, confirmed indexed) via per-parcel scrape —
  same shape as the Warren County OH `iasWorld` scrape below. Not yet built.

## Butler County, OH — 206/206 (100%)
- **PIN/LUC/YrBlt + ACRES:** `https://maps.butlercountyauditor.org/arcgis/rest/services/PARCELSEARCH/MapServer/0`
  (value fields null). Confirmed live 2026-07-12.
- **Building GBA (true, multi-story captured):** Tyler iasWorld datalet
  `https://propertysearch.bcohio.gov/Datalets/Datalet.aspx?mode=commercial&UseSearch=no&pin=<PIN>` —
  sum `AREA` of "COMMERCIAL INTERIOR/EXTERIOR (ALL CARDS)". No Butler footprint layer exists.
- **Values:** same host `mode=profileall` (100% values, TY2025).

## Clermont County, OH — 250/365 (68%)
- **Building SF (fast):** footprint ArcGIS
  `https://maps.clermontcountyohio.gov/server/rest/services/WMAS/BuildingOutlines/MapServer/0`
  (`PIN`; `area` already sq ft), summed per PIN. PINs carry trailing dots — preserve.
- **Bulk CAMA (alt):** `https://www.clermontauditor.org/wp-content/uploads/PublicAccess/CLERMONT_AA407.ZIP`
  (iasWorld DAT: SF = Σ COMINTEXT.AREA; values APRVAL.DAT; delq CHARGE.DAT). Footprint-less
  vacant/300-LUC = NO-SF.

## Warren County, OH — 311/452 (68%)
- **Account map + land + values:** nightly export
  `https://auditor.warrencountyohio.gov/propertysearch/PublicDataExport/DownloadData` (SummaryData.csv
  ParcelNumber→AccountNumber; **strips leading zeros** — normalize). ValuesData.csv — sum component
  rows per account-year.
- **Building SF:** scrape `…/PropertySearch/Summary/Building?account_nbr=<acct>` per building.
- **v2 caveat (corrects v1):** the CommercialBuilding/FloorData export files carry rows but `AREA` is
  **zero-filled** (still unusable); the per-building AJAX **zero-fills non-primary buildings** (server
  defect) — scrape captures the PRIMARY building only ⇒ multi-building GBA UNDERSTATED. Tag
  `scrape-primary-bldg(of N; total UNDERSTATED)`; SF-verify any multi-bldg row that screens IN before
  LOI. ~54 Area=0 sound-value parcels = NO-SF.

## Indianapolis metro
- **Marion:** parcels `https://gis.indy.gov/.../sde_Parcel/sde_Parcel/MapServer/5` (`ACREAGE`, join
  `STATEPARCELNUMBER` dashed); buildings `…/sde_Buildings/sde_Buildings/MapServer/0` (join
  `PARCEL_TAG`; `SHAPE.STArea()` sq ft, SR 2965). **Do NOT use parcel `ESTSQFT` — it is LOT SF.**
  1,786/1,908 (93.3%).
- **Hamilton-IN:** parcels `https://gis1.hamiltoncounty.in.gov/.../HamCoParcelsPublic/FeatureServer/0`
  (`DEEDACRES`, `STPRCLNO`) + `HamCoBuildingFootprints/FeatureServer/6` (`Shape__Area`, SR 6459,
  majority-in). 255/282 (90.4%). NB: distinct from Hamilton County OH above — do not conflate.
- **Boone / Hendricks / Johnson:** land from state parcels
  `https://gisdata.in.gov/server/rest/services/Hosted/Parcel_Boundaries_of_Indiana_Current/FeatureServer/0`
  (reproject to EPSG:2965; join `state_parcel_id`); building SF from **FEMA USA Structures**
  (majority-in). 77–87%. Post-2020 construction beyond FEMA vintage = NO-SF; upgrade via
  Schneider/Beacon scrape for true GBA + stories.

## Chesterfield County, VA (Richmond metro) — NEW, root cause found + endpoint live 2026-07-12
- **`ASSESSED` field was never removed — it was restructured.** The AGOL item backing this layer is
  flagged `"contentStatus":"deprecated"` in its own metadata (confirms the deprecation note was real),
  but the underlying **service still runs** on the county's current schema.
- **Live endpoint:** `https://services3.arcgis.com/TsynfzBSE6sXfoLq/ArcGIS/rest/services/Cadastral/FeatureServer/3`
  (layer name `ParcelsEnriched`).
- **Field mapping (old → new):** `ASSESSED` → split into `TotalAssessment` (int, direct replacement),
  `FairMarketValue` (double), `LandUseValue` (double), `ImprovementValue` (double); `AssessmentYear`
  (int) for vintage.
- **Join key:** `Tax_ID` (string, 15 char) — verify exact dash/zero-padding against a known screen row
  before batch query. `GPIN`/`MPN` available as alternates.
- **Building SF caveat:** schema is residential-shaped (`FinishedArea`, `UnfinishedArea`, `Bedrooms`,
  etc.) — no clean commercial building-SF field. For shallow-bay/flex parcels, use the FEMA USA
  Structures fallback (majority-in intersect) rather than trusting `FinishedArea` for commercial
  improvements.

## Des Moines / Dallas, IA metro — NEW, first research pass 2026-07-12
- **Polk County (Des Moines):** candidate ArcGIS Server, search-indexed but **untested live this
  pass — unreachable from the research sandbox, not yet ruled dead.** Isolated the failure to the
  `gis4.polkcountyiowa.gov` subdomain specifically: the county's main site (`www.polkcountyiowa.gov`)
  and unrelated AGOL services resolved fine on the same session, so this is a host-specific failure
  (same signature as the Hamilton CAGIS outage), not a general block. Candidate endpoints to retest
  off-sandbox:
  - `https://gis4.polkcountyiowa.gov/server/rest/services/Public/Polk_County_Parcels/FeatureServer/1` (Cadastral Parcels)
  - `https://gis4.polkcountyiowa.gov/server/rest/services/Auditor/Auditor_Export/FeatureServer/113` (`Tax_Parcels_Dimensions` — part of a larger Auditor_Export service group worth enumerating layer-by-layer once reachable)
- **Dallas County (IA):** **confirmed no bulk API** — runs on Beacon (Schneider Corporation),
  `https://beacon.schneidercorp.com/Application.aspx?AppID=909&LayerID=17429&PageTypeID=2&PageID=7823`.
  Session/JS-driven HTML search app, not a queryable REST layer; also unreachable via plain fetch this
  session (likely requires session-cookie bootstrapping). Recovery requires a per-parcel scrape build
  comparable in scope to the Warren County OH script — not yet attempted.

## Statutory assessment ratios (value-basis)
- MO commercial market = assessed / 0.32 · KS commercial appraised = assessed / 0.25 · OH auditor
  values = 100% market. VA (Chesterfield) `FairMarketValue`/`TotalAssessment` — confirm basis (likely
  100% fair market, VA generally assesses at FMV) before use — not yet verified against a known sale.

## Still not researched / not yet closed out
- Baltimore-MD SDAT name-recovery; Henrico mail addresses; Madison/Dane WI NO-SF rows; Indianapolis
  collar true-GBA upgrade (Schneider/Beacon).
- **Hamilton County OH values** (post-CAGIS-outage) — wedge.hcauditor.org scrape not yet built.
- **Polk County IA** — needs off-sandbox live retest of `gis4.polkcountyiowa.gov` before building the
  recovery script.
- **Dallas County IA** — needs a Beacon/Schneider scrape build (no REST path exists).
- **Phase 9's 166 unverified parcels** — not addressed by this endpoint pass; requires direct
  workbook access (Code surface / OneDrive-synced copy) to identify which rows/counties they land in.
