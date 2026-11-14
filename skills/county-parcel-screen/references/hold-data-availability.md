# county-parcel-screen — hold-data availability by ORA market

Moved out of `SKILL.md` on 2026-09-22 (body split). Check this table before promising a hold-scored list in any market, and state the row's verdict on the face of the deliverable.

## Hold-data availability by ORA market (checked 2026-09-18 — do NOT assume)

Ohio's rich transfer history does NOT generalise. Neither does Missouri's total
absence. Check this table before promising a hold-scored list in any market, and
state the row's verdict on the face of the deliverable.

**VERIFIED** = an actual run or a live query confirmed it. **DOCUMENTED** = the
field is recorded in `county-endpoints.md` but no run has scored hold off it.
**UNKNOWN** = never established; do not assume either way.

| Market | County | Hold signal | Source / field | Status |
|---|---|---|---|---|
| Columbus OH | Franklin | **YES** | GIS `SALEDATE`/`SALEPRICE` + bulk `Transfer*.xlsx` per-parcel history | VERIFIED (3 runs) |
| Cincinnati OH | Hamilton | **YES** | `Sales/ParSales/MapServer/12` — `SALEDATE`, `PRICE`, `SALETYPE` (arms-length gate) | DOCUMENTED |
| Cincinnati OH | Butler | **YES** | `Owners Report.CSV` `SALEDATE` + `Property Sale.CSV` (Deed Transfer Number, Sale Date, Price, **No Of Parcels** — directly feeds the sibling rule) | DOCUMENTED |
| Cincinnati OH | Clermont | **PARTIAL** | parcel layer has none; join `Sales/ParSales/MapServer/12` | DOCUMENTED, untested |
| Cincinnati OH | Warren | **NO** | no public values, SF or sales; calibration factor undefined (n=0) | VERIFIED absent |
| Maryland | ALL counties | **YES — gap closed 2026-09-18** | statewide `MD_PropertyData` `TRADATE` + `CONSIDR1` + `CONVEY1` + `DR1LIBER`/`DR1FOLIO`; Socrata `ed4q-f8tm` adds 3 sale segments + grantor | VERIFIED (see below) |
| Kansas City | Jackson MO | **NO** | non-disclosure state — no sale date AND no price published anywhere | VERIFIED absent |
| Kansas City | Clay MO | **NO** | non-disclosure; layer thin, values frozen 2020 | VERIFIED absent |
| Kansas City | Platte MO | **UNKNOWN** | data-hostile, never pulled | UNKNOWN |
| Kansas City | Wyandotte KS | **NO** | non-disclosure; no values and no published tax-mail either (consolidation also unavailable) | VERIFIED absent |
| Kansas City | Johnson KS | **UNKNOWN** | paid gate (AIMS ADS extract) | UNKNOWN |
| Indianapolis | Marion + 4 collar IN | **PROBABLY YES — endpoint UNDOCUMENTED** | IN is a disclosure state; the v01 run derived a 2.32x median from sale prices (n=226) and flagged a "nominal transfer 2026-04", so dates were reachable. But `county-endpoints.md` carries **no Indianapolis section at all** — only `scripts/indy_*.py`. **Re-derive and document the endpoint before relying on it.** | UNVERIFIED |
| Madison WI | Dane | **CITY ONLY** | statewide WI DOA layer has **no sale date/price**; City of Madison assessor conveyance pages carry date+price (HTML scrape, ~660 pages, grantor blank post-2023); WI DOR RETR is GenTax-gated | VERIFIED — **suburban Dane has no free hold signal** |
| Grand Rapids MI | Kent | **NO DATE — proxy only** | MI publishes no public sales. The v01 run used a **Proposal-A `TaxableValue`/`SEVValue` gap proxy**: taxable value uncaps to SEV on transfer, so TV≈SEV implies a recent transfer and a wide TV<SEV gap implies a long hold. Genuine tenure evidence, but a **magnitude, not a date** — it cannot feed the years-held curve directly. Calibrate the gap to years locally before scoring. | VERIFIED |
| Grand Rapids MI | Ottawa | **PARTIAL** | annual ECF Analysis PDF carries parcel-level sales with date+price, but only ~40 industrial sales per 2-yr window — a calibration sample, not parcel coverage | VERIFIED |
| Richmond VA | Henrico | **YES** | parcel layer `SaleDate` ('YYYY-MM-DD') + `SalePrice` | DOCUMENTED |
| Richmond VA | Chesterfield | **YES** | `AssessorProValGPINRecTransPublish` — `sale_date` (epoch ms), `sale_price`, `val_code_1` ('1 - VALID SALE') — the cleanest published arms-length gate in the registry | DOCUMENTED |
| Richmond VA | Richmond City | **YES** | same layer pattern — `sale_date`, `sale_price`, `val_code_1` | DOCUMENTED |
| Richmond VA | Hanover | **NO** | no use code, no SF, no sale date/price — deed book/page only | VERIFIED absent |
| Des Moines IA | Polk | **YES — best in class** | inventory `transfer_th1` (current-owner deed date) + sales file 1987->current with `sale_date`, `instrument` (Deed/Contract), `seller`/`buyer`, and Iowa DOR `quality` arms-length classification | VERIFIED |
| Des Moines IA | Dallas | **YEAR ONLY** | `Assessor/Sales` layers carry `SaleYear` + `Sale1..Sale4` prices — **no sale date, no parties**. Year granularity is enough for the curve (+/-1 yr moves <1 pt past year 10) but not for the nominal-transfer test. | VERIFIED |
| Louisville KY | Jefferson | **UNKNOWN — never screened** | no section in `county-endpoints.md`; Louisville has been a ratified entry-phase cluster since 2026-08-05 (`target-markets.json`), but its county endpoints were never built | UNKNOWN |

Three practical consequences: **(a)** Missouri and Kansas will never have a
hold signal from public records — the >20% branch (drop the component) is their
permanent state, not a run defect. **(b)** Michigan and suburban Wisconsin need
market-specific proxies, and Michigan's is a gap magnitude rather than a date.
**(c)** Indianapolis is the highest-value gap to close — a disclosure state
whose endpoints were never written down.
