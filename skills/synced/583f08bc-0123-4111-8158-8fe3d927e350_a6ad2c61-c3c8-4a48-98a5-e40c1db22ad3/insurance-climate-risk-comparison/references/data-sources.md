# Data sources — insurance-climate-risk-comparison

Verified live 2026-09-11. Re-verify if a call fails — these are third-party services and can move.

## FEMA National Risk Index (climate/disaster risk)

**Service:** National Risk Index Counties, ArcGIS Feature Service (this is FEMA's actual live-query mechanism for NRI — it is *not* part of the OpenFEMA `v1`/`v2` DisasterDeclarations-style REST API family, despite both being FEMA data; don't look for it there).

```
https://services.arcgis.com/XG15cJAlne2vxtgt/arcgis/rest/services/National_Risk_Index_Counties/FeatureServer/0/query
```

Standard ArcGIS REST query params: `where=STCOFIPS='{5-digit state+county FIPS}'&outFields=*&f=json`. Query by `STCOFIPS` (preferred, unambiguous) or `STATE`+`COUNTY` name if FIPS isn't yet resolved.

Landing page (for the human-readable version, downloadable full dataset, and FEMA's own documentation PDF): https://www.fema.gov/about/openfema/data-sets/national-risk-index-data — data vintage as of 2026-09-11 is v1.20 (December 2025).

### Key fields

| Field | Meaning |
|---|---|
| `STATE`, `STATEABBRV`, `STATEFIPS` | State identifiers |
| `COUNTY`, `COUNTYFIPS`, `STCOFIPS` | County identifiers — `STCOFIPS` is the 5-digit code to query on |
| `RISK_VALUE` | Composite risk, dollar-denominated value |
| `RISK_SCORE` | Composite risk, 0–100 nationally-normalized score |
| `RISK_RATNG` | Composite risk, categorical tier: Very Low / Relatively Low / Relatively Moderate / Relatively High / Very High |
| `RISK_SPCTL` | Composite risk, **state** percentile (NOT national — don't use this for cross-state comparison, it only ranks counties within their own state) |
| `EAL_SCORE`, `EAL_RATNG`, `EAL_SPCTL` | Expected Annual Loss — composite, same score/rating/percentile pattern |
| `ALR_NPCTL` | Expected Annual Loss Rate, **national** percentile (composite only — there is no `RISK_NPCTL` national-percentile equivalent for the composite risk score itself, confirmed against the live field list 2026-09-11) |

### Per-hazard fields

Each hazard follows the same `[CODE]_RISKS` / `[CODE]_RISKR` (score/rating) and `[CODE]_EALS` / `[CODE]_EALR` (expected-annual-loss score/rating) pattern. Hazard codes relevant to ORA's shallow-bay industrial product:

| Code | Hazard |
|---|---|
| `IFLD` | Riverine flooding |
| `CFLD` | Coastal flooding |
| `HRCN` | Hurricane |
| `TRND` | Tornado |
| `CWAV` | Cold wave / severe winter weather |
| `HWAV` | Heat wave |
| `HAIL` | Hail |
| `ERQK` | Earthquake |
| `DRGT` | Drought |
| `WFIR` | Wildfire |

Pull `RISK_SCORE`/`RISK_RATNG` for the composite, and `[CODE]_RISKS`/`[CODE]_RISKR` for the ten hazards above, per county. Rank by score to report "top 3 hazards" per Step 4 of SKILL.md.

**No API key required.** Free, public ArcGIS Feature Service.

## Insurance cost proxy ladder

There is no clean, free, state-level **commercial** property insurance rate dataset from a primary government source — checked 2026-09-11. NAIC (the natural first stop) publishes state-level P&C data, but the only clean state-average-premium table is the *Dwelling Fire, Homeowners Owner-Occupied, and Homeowners Tenant/Condo* report — residential, several years stale at any given time (the edition current as of 2026-09-11 covers 2018 data, published 2021), and NAIC's own release notes caution against reading it as a clean state-by-state ranking. Use it anyway as the best available government-adjacent signal, clearly flagged — commercial and residential property insurance cost move together directionally (same regional hazard/reinsurance cost environment), just not 1:1.

**Rung 1 — PROXY-GOV.** NAIC Dwelling Fire/Homeowners report: https://naic.soutronglobal.net/Portal/Public/en-GB/RecordView/Index/2006 (or search "NAIC homeowners insurance report" for the current edition — check for a newer vintage than 2018 data before using). Report the state average premium, the data year, and note explicitly that it is a **residential proxy, not a commercial figure** — directional only.

**Rung 2 — PROXY-AGGREGATOR.** Only when Rung 1 has no usable state coverage. A commercial-property-insurance-cost aggregator report (e.g. MoneyGeek's annual commercial property insurance cost report, or an equivalent named aggregator current at run time) — cite by name, publisher, and date, exactly as ORA's Voice Register requires for aggregator sources ("aggregators last-resort"). Flag AGGREGATOR-PROXY, the lowest confidence tier, and say so in the narrative, not just the table footnote.

**Never blend tiers silently.** If a market's insurance figure is ACTUAL (from `insurance-renewal-review`) for one comparison and PROXY for the rest, say so in the row — don't average an actual and a proxy into one number.

## Multi-county cluster reference (Kansas City)

Confirmed already in `target-markets.json`'s standing flood note: the Kaw River bottoms districts (Fairfax Industrial Park, Armourdale — Wyandotte County KS / Unified Government of Wyandotte County-KCK) and West Bottoms (Jackson County MO) sit behind the UG/USACE levee system. When running Kansas City MO/KS, pull NRI for both Wyandotte County KS (`STCOFIPS` 20209) and Jackson County MO (`STCOFIPS` 29095) and report the range — verify both FIPS codes against the geocoder output at run time rather than trusting this note blindly, per SKILL.md Step 1's "resolve at runtime" rule.
