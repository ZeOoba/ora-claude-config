# Millage & Assessment Endpoint Registry

**V** = live-verified, with the date · **U** = unverified pattern or not yet discovered
Every V entry below was fetched on its stated date. Re-verify before citing a figure into an IC memo; government URLs move.

**Coverage is 2 of 12 jurisdictions.** That is a statement of fact, not a gap to paper over. An absent entry means run the ladder's tier 2/3 by hand for that county — and add what you find here.

---

## VERIFIED

### Indiana — DLGF certified tax rates (tier 1, static document)

| Field | Value |
|---|---|
| URL | `https://www.in.gov/dlgf/files/2026-reports/2026_Certifed_Tax_Rates_By_District.pdf` |
| Status | **V** — HTTP 200, 649,963 bytes, `Last-Modified: 2026-03-04`; verified 2026-07-27 (Pike Plaza underwrite), re-verified 2026-08-03 |
| Unit | percent of assessed value |
| Covers | every IN taxing district, by county |
| Reference figure | Marion County, Pike Township, tax district **601 INDIANAPOLIS PIKE**: 2026 certified gross rate **2.6830%**. Supersedes any earlier `[EST]` range-midpoint for Marion County / Indianapolis screens. |

> ⚠ **The filename typo is the state's, not ours.** `Certifed` (missing the `i`) is what DLGF published. Verified 2026-08-03: the typo'd URL returns 200; `2026_Certified_Tax_Rates_By_District.pdf` (correct spelling) returns **404**. Fetch the literal string above. Expect the `2026-reports` / `2026_` segments to increment annually — and expect the typo to be silently fixed some year, so on a 404 try the corrected spelling before concluding the document moved.

Tier-3 fallback for IN: the DLGF **Gateway** portal (interactive; log query date + screen values).

### Washington DC — OTR / DCGIS parcel service (tier-1-equivalent, static REST)

| Field | Value |
|---|---|
| Service | `https://maps2.dcgis.dc.gov/dcgis/rest/services/DCGIS_DATA/Property_and_Land_WebMercator/MapServer` |
| Layer | **40** — *Owner Polygons (Common Ownership Layer)*, 222 fields |
| Query | `/40/query?where=SSL%3D'<ssl>'&outFields=*&returnGeometry=false&f=json` |
| Status | **V** — verified 2026-08-02 (1518 K St NW underwrite), re-verified live 2026-08-03 |
| Unit | `TAXRATE` is **per $100** of taxable value (`1.65` = 1.65%) |

**Key format — the trap.** `SSL` is fixed-width: 4-char square + padding + 4-char lot. `SSL='0199    0821'` (**four** spaces) returns 1 feature; one or two spaces returns **HTTP 200 with zero features**, indistinguishable from a nonexistent parcel. Use `SSL LIKE '0199%0821'` when padding is uncertain and confirm exactly one feature came back.

**Fields that carry the underwriting inputs:**

| Purpose | Fields |
|---|---|
| Identity | `SSL` · `PREMISEADD` · `OWNERNAME` · `USECODE` · `CLASSTYPE` · `LANDAREA` |
| Assessment | `OLDTOTAL` (current) · `NEWTOTAL` (proposed) · `NEWLAND`/`NEWIMPR` · `PHASELAND`/`PHASEBUILD` |
| Tax | `TAXRATE` · `ANNUALTAX` · `CY1TAX`–`CY2TAX` · `PY1TAX`–`PY10TAX` (10-year history) |
| Sale | `SALEPRICE` · `SALEDATE` (epoch ms) · `SALETYPE` |

**Read the taxable base, not the headline assessment.** DC phases in assessment increases, so `ANNUALTAX ÷ TAXRATE` recovers the base actually taxed and will not equal `OLDTOTAL`.

Worked validation — **1518 K St NW** (SSL `0199    0821`), retrieved 2026-08-02, re-verified 2026-08-03:

| | |
|---|---|
| `OWNERNAME` | 1518 K STREET LLC |
| `SALEPRICE` / `SALEDATE` | $5,800,000 · 2012-12-20 |
| `OLDTOTAL` / `NEWTOTAL` | $5,049,400 / $3,488,890 |
| `ANNUALTAX` ÷ `TAXRATE` | $48,954.02 ÷ 1.65% = **$2,966,910 taxable base** (~41% below the current headline assessment, purely on phase-in) |

**DC Class 2 commercial rates, FY2026 (graduated):** $1.65/$100 ≤$5M · $1.77/$100 $5–10M · $1.89/$100 >$10M.
**DC transfer + recordation, commercial:** 2.9% combined, effective 10/1/2023.

---

## NOT YET DISCOVERED (tier 2/3 by hand — add findings here)

| Jurisdiction | ORA status | Route to use |
|---|---|---|
| **Ohio** (Franklin/Columbus · Hamilton/Cincinnati) | established cluster — largest footprint | County auditor per-parcel record is the working tier 2. **Negative result, 2026-08-03:** two guessed `tax.ohio.gov/researcher/tax-analysis/tax-data-series/...` paths for the statewide real-property rate tables both returned **404** — do not re-guess those two; find the current path from the department's own index before adding a tier-1 entry. |
| **Maryland** (BWI corridor) | established cluster | SDAT real-property search is the tier-2 record; note the 3-yr phase-in when reading any assessment. |
| **Wisconsin** (Dane/Madison) | established cluster | Annual full-value + mill rate is published at state level; endpoint not yet located. |
| **Missouri** (Clay/Platte/Jackson) | established cluster | County collector/assessor records; no statewide static document located. |
| **Kansas** (Johnson) | established cluster | County clerk publishes annual levy sheets; endpoint not yet located. |
| **Tennessee** | owned footprint | Comptroller publishes certified rates; endpoint not yet located. |
| **Michigan** (Kent/Grand Rapids) | entry cluster | City/township + county treasurer millage; **units are mills** — see the worked MI example in `acquisition-underwriting` (44.75 mills derived from a disclosed bill ÷ taxable value). |
| **Virginia** (Richmond) | entry cluster | City/county rate ordinances; endpoint not yet located. |
| **Iowa** (Polk/Des Moines) | entry cluster | County treasurer; note the 90% rollback when reading assessments. |
| **Kentucky** (Louisville/Jefferson) | entry cluster | PVA + Metro rate schedule; endpoint not yet located. |

Before discovering an endpoint from scratch, check `county-parcel-screen`'s `references/county-endpoints.v1.json` — its parcel/CAMA service roots (22 counties, live-verified 2026-07-19) frequently host the assessor's tax record on a sibling layer of the same ArcGIS service.
