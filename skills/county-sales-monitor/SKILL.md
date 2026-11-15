---
name: county-sales-monitor
description: >
  Use when Gabriel wants a recurring digest of recently RECORDED industrial
  sales and transfers (bldg SF under 150,000) across ORA target-market counties,
  or new comps for the Notion comps database. Trigger on: recent industrial
  sales, county sales tracker, sales digest, recent county transfers, what
  traded, who's buying or selling industrial in a market, new comps since
  [date], set up a sales feed. MARKET INTELLIGENCE, not sourcing: does NOT
  replace county-parcel-screen (off-market owner call lists, motivated sellers,
  delinquent-tax/estate leads). Single-property comp grids route to
  acquisition-underwriting COMPS mode.
---

# county-sales-monitor (v0.12)

Produce a recurring digest of recently recorded industrial sales and transfers
across ORA's target-market counties, so Gabriel sees what actually traded — at
what $/SF, to whom — without a manual county-by-county pull. This is market
awareness and comp accumulation. It never scores a deal, never ranks an owner,
and never initiates outreach. Endpoints, field names, and use-code mappings are
IMPORTED from `county-parcel-screen`, never re-derived here.

## Digest scope (apply unchanged unless the user overrides)

Industrial / shallow-bay / flex / office-warehouse / warehouse-distribution use
codes only. **Building SF < 150,000**; where the county publishes no commercial
SF, keep the row and mark SF `unpublished` — never drop it. Trailing window:
**30 days, ratified by Gabriel 2026-08-15** (weekly was considered and
rejected — recording lag makes a 7-day window too thin to trust, and 30 days
gives enough volume for a real median $/SF). Geography: the
Tier A counties only (below) — the other ORA clusters are Tier B/C,
documented as the next expansion phase, not yet in scope. No minimum price,
no maximum price, no value band.

**This cap is deliberately wider than the acquisition buy-box.** 10-80K SF is
county-parcel-screen's deal-qualification filter; 150K SF here is a market-
awareness aperture — a 120K SF trade three exits away is a comp and a signal
even though ORA would never buy it. Do NOT import county-parcel-screen's buy-box
gates, replacement-cost floors, YoC floors, value bands, 0-100 scorecard,
institutional/estate/never-call exclusion tiers, or the pipeline-guard
counterparty floor. None of them apply to a comp feed.

## Coverage (state it per county — never silently omit)

Sale-price/date availability is the binding constraint, not parcel geometry.
Three tiers; the digest prints a per-county line for every county in every run,
including the ones that produced nothing and the ones that structurally cannot.

**Launch scope, ratified 2026-08-15: Tier A only.** Franklin OH, Baltimore Co
MD, and Polk IA were the entire pilot; Cook IL joined Tier A in v0.10. Tier B and Tier C are documented below
so the expansion path is clear, but nothing outside Tier A is built, verified,
or scheduled in v0.2 — expanding to Tier B is a distinct future pass, each
county verified individually before it's trusted in a real digest.

**Tier A — CONFIRMED live sale date + price (validated by county-parcel-screen):**
- **Franklin OH** (Columbus) — parcel layer `SALEDATE`/`SALEPRICE` plus the
  Tax Accounting `Transfer*.txt` / `Transfer010.xlsx` transfer history with
  grantee owner names. Already proven as a "new comps since [date]" pull
  (Columbus v04 workbook carries a New Comps sheet). Best-documented county.
- **Baltimore Co MD** — `TRADATE` / `CONSIDR1` (sale price) in the statewide
  MdProperty CAMA layer (`JURSCODE='BACO'`), with owner names recovered by the
  join to the county `bcgis Property/MapServer/1` layer (`ACCTID[4:]` = TAXPIN).
  `SQFTSTRC` building SF ~89% populated. Nominal transfers are rare here (1 in
  the whole industrial universe) — unlike Ohio. **Known recording lag, found
  2026-08-15 via the pilot's own Notion data: TRADATE runs ~4+ months behind**
  (the 45-row pilot pull showed a clean taper 8→3→3 across Feb-Apr 2026, then
  zero from May through the mid-August pull date). Worse than Franklin's
  ~1-month bulk-file lag. A monthly run will structurally read this county as
  "quiet" for its most recent 3-4 months — that is expected source behavior,
  not a coverage regression, and Step 8's regression check must not conflate
  the two (see Step 8 below).
- **Polk IA** (Des Moines) — `POLKCOUNTY.csv` commercial sales export, 1987 to
  current, but lagging (newest `initial_entry_date` 2026-07-30 as of
  2026-10-01): `sale_date`, `price`, `instrument`
  (Deed | Contract), `seller`, `buyer`, book/pg, plus the CAMA snapshot
  (`gross_area` = building SF, occupancy). The best assessor source found to
  date and the only one with clean grantor/grantee back three decades.

- **Cook IL** (Chicago–Greater Cook County; added v0.10, 2026-10-30, Gabriel
  in-turn instruction) — Cook County Assessor open data on Socrata, no auth.
  Parcel sales `datacatalog.cookcountyil.gov/resource/wvhk-k5uv.json`
  (`sale_date`, `sale_price`, `doc_no` deed number, `num_parcels_sale`,
  published `buyer_name` / `seller_name`, `deed_type` / `mydec_deed_type`, the
  Assessor's `sale_filter_*` non-market flags; unfiltered since 2023-10-31).
  Building SF, year built, address and market value from Commercial Valuation
  `csik-bsws` (valuation groups: `keypin` + `pins`). Industrial building classes
  only: **5-93, 5-83, 6-63, 6-73, 8-93** (Assessor `classcode.pdf`); land,
  minor/ancillary improvements, special improvements and condo units excluded.
  Live probe 2026-10-30: 440 in-scope sale rows in 12 months → 303 deeds → 276
  under the SF cap → 206 clean $/SF comps (median $95.31), 27 RATIO-REVIEW.
  SF is published only when every building PIN on the deed is valued and each
  valuation group lies wholly inside the deed (a house or store on a mixed deed
  blocks it). The reassessment year carries SF but no market value yet, so the
  ratio denominator borrows the newest earlier year's value for an unchanged
  PIN set. Sale dates lag
  recording ~3 months (newest 2026-08-06 on 2026-10-30). The ratio test uses the
  Assessor's market value (assessed level is 25%, so the raw assessed value is
  never the denominator).
- **Indianapolis cluster IN** (Marion, Hamilton, Boone, Hendricks, Johnson,
  Hancock; added v0.11, 2026-10-30) — **partial price**. Statewide
  sales-disclosure file `stats.indiana.edu/sdfdata/SDF_<yr>.zip` (weekly,
  Fridays; current year cumulative, prior year needed for the 365-day window).
  A filer can mark Part G confidential (`G_Confidential_Finance`), which
  withholds the price; **only priced disclosures become comps**, and the rest
  are counted on the coverage row. Industrial building classes (DLGF Code List
  1): **330, 340, 345, 346, 350, 370**. Excluded: 300/309 land, 310 food & drink
  and 320 heavy manufacturing (special-purpose), 360 truck terminals, 380/385/390
  extraction, landfill and grain, 398 building on leased land, 399 other
  structures. Price is format 12.2 (cents) in `E1_Sales_Price` or `G1_Sales_Price`
  (Part G). Buyer/seller come from `SALECONTAC`. The ratio test uses land +
  improvement AV (Indiana assesses market value-in-use; live price/AV medians
  were 1.0–1.9x). **No building SF** in the file, so rows carry SF-UNPUBLISHED
  until a county GIS join exists (Hamilton `sq_ft_comm`; Marion has footprints
  only). A sale filed on several forms (shared `Unique_Sales_ID`,
  `C6_Form_Total` = form N of M) is one transaction over the union of its
  parcels; the file repeats some parcel and disclosure rows, so each parcel
  counts once. Live probe 2026-10-30, 12-month window: 34 priced comps (Marion
  11, Boone 13, Hamilton 9, Hancock 1); withheld: Marion 92/103, Hendricks 4/4,
  Johnson 14/14, Hancock 12/13. Filing lag is about 1 week, but some counties
  submit monthly: coverage WARNs only when a county's newest filing is more than
  45 days old. Form answers that
  mark a non-market price raise NONARMS: trade, partial interest, court order,
  partition, charity, sheriff, short sale, quitclaim, auction, existing business
  in price, portfolio sale, and special relationship/foreclosure/auction/trade/
  partial. A land contract is CONTRACT-SALE.

**Tier C — CONFIRMED no usable public sale price (say so, every run):**
- **Warren OH** (Cincinnati) — no public values, SF, or sales anywhere.
- **Johnson Co KS + Platte Co MO** (Kansas City) — Missouri and Kansas are
  **non-disclosure states**; no public sale price will ever exist. This is
  permanent, not a gap to close. The whole KC cluster is affected for price;
  transfer *dates* may still be inferable per county — verify before claiming.
- **Kent MI** (Grand Rapids) — no public sales; the county applies a statutory
  2.0x assessment ratio. Ottawa MI publishes an annual ECF sales study PDF
  (parcel-level improved sales with Bldg SF and $/SF) but it is **annual, not
  continuous** — usable as a yearly comp backfill, not a weekly feed.

**Tier B — PROVISIONAL, needs a Step 0 verification pass before first use:**
Every other county. `county-endpoints.md` documents sale-bearing fields for
several of them (Butler OH's `Property Sale.CSV` with direct Grantor1/2 +
NEW OWN1/2; Hamilton OH's `HistoricSalesExport.xlsx`; Clermont OH's
`Sales/ParSales/MapServer/12`; Anne Arundel + Howard MD `CONSIDR1`/`TRADATE`
with SDAT-scrubbed owner names; Henrico VA's
`AssessorProValGPINRecTransPublish` with `val_code_1` arm's-length codes;
Chesterfield VA `SaleDate`/`SalePrice`; Richmond City `LAST_SALE_DATE`/
`LAST_SALE_PRICE`; other Indiana counties through the same statewide SDF file
as the Indianapolis cluster (Tier A above; filter by the `County_ID` / SDF_ID
prefix, because county names come in two formats, "Marion" vs "MARION
COUNTY"); Dane WI only via the
Madison **city** assessor conveyance pages, where grantor/grantee go blank from
mid-2023 forward; Dallas IA sales layers that carry price but **no sale date
and no parties**). None of that has been exercised as a *windowed recent-sales*
pull. Verify field-by-field on first run and record the result — a field that
exists is not the same as a field that updates weekly.

**Louisville / Jefferson Co KY** was added to ORA market coverage in 2026-08
(`market-monitor`, `acquisition-underwriting`, `daily-brief`) and is the likely
**10th cluster**. Its county endpoints have NOT been discovered. Do not invent a
URL or field name for it; adding it means running county-parcel-screen's Step 1
discovery for Jefferson Co KY first and appending the result to that skill's
registry. Flagged for Gabriel below.

## Workflow

### 0. Load the registry (never fork it)
Read `../county-parcel-screen/references/county-endpoints.v1.json` for the
per-county service URL / layer id / MD `JURSCODE`, and
`../county-parcel-screen/references/county-endpoints.md` for the sale, value,
and SF field names, ID formats, and quirks. **`county-endpoints.md` wins on any
conflict.** If an endpoint has drifted or a field name is wrong, that is a fix
to county-parcel-screen's registry — patch it there, note it in that skill's
changelog, and re-read. Never maintain a second, silently-diverging copy of
endpoint state inside this skill. Two endpoints already drifted between the
June 2026 discovery runs and the 2026-07-19 verification pass (Dane WI service
rename, Kent MI token-gating); assume more will.

### 1. Resolve the window
Default `[today - 30d, today]` (ratified cadence — monthly). Accept an
explicit date range for backfills or ad hoc pulls. Record the exact window in
the digest header — a digest without its window is uninterpretable later.

**Recording lag is real and it is the main correctness trap.** County data drops
lag the actual deed recording by days to weeks, and different counties refresh
on different cadences (Franklin's tax-accounting files are periodic bulk drops;
Polk's sales CSV lags: newest `initial_entry_date` was 2026-07-30 as of 2026-10-01, so judge freshness by it, not by assumption; Ottawa's is annual). A strict `sale_date IN
window` query will permanently miss every deed that posted late. So: query the
window, **and also** diff the full recent-sales key set against the prior run's
persisted key set, and surface late arrivals in a separate `LATE-POSTED` block
with their true sale date. Key = county + parcel ID + sale date + price.

### 2. Pull the universe, per county
Scope is Tier A only (Franklin OH, Baltimore Co MD, Polk IA, Cook IL, Indianapolis cluster IN) — the
mappings below for other counties are carried forward for the documented
expansion phase, not exercised in v0.2. Industrial use codes only, taken from
county-parcel-screen's already-resolved mapping — Ohio DTE 300-series (`CLASSCD`/`CLASS` 3xx); Jackson MO Ascend
`landuse_cd` 3200-3299; Dane WI SLUCM `2xxx-3xxx` + `6371/6373/6376/6379/6381`;
Polk IA occupancy 46/25C/20A/48/44/20B; Cook IL class 593/583/663/673/893 (letter suffixes included); Indiana DLGF class 330/340/345/346/350/370; Henrico VA 406/675/453/495/670/470/472/
326/328; Chesterfield VA 510/511/512/660/270/380/390/370/275/700; Hanover VA by
`ZONING_LIST IN ('M-1','M-2','M-3')` inference. Self-storage / mini-warehouse
codes are **excluded** everywhere they exist as a distinct code (Dane 6375,
Henrico 386, Chesterfield 450, Polk 47) — different asset class, distorts $/SF.
Auto-use codes (Chesterfield 600, Polk 37) are excluded from the comp set for
the same reason, not for ORA's tenancy-policy reason.

Paged queries via sandbox python `urllib` — `web_fetch` is URL-length-capped and
must not be used for paged REST pulls. Save raw JSON/CSV per county before
processing, so a bad parse never costs a re-pull.

### 3. Filter noise (not owners)
Drop government/exempt parties (`TAX_TYPE_CODE` '7'/'8' in Richmond City,
`Exempt='E'` in Chesterfield, per-county equivalents elsewhere) — same rule as
county-parcel-screen Step 3. That is the ONLY exclusion tier this skill runs.
Institutional buyers are the *point* of a comp feed, not something to strip;
a Prologis or STAG acquisition in an ORA submarket is high-value intelligence.
ORA-affiliated entities (Oxford*, Goldberg, FJ&S) are kept and flagged
ORA-AFFILIATED, matching county-parcel-screen doctrine.

### 4. Apply the size gate
Building SF < 150,000 where SF is published. Where it is not (all four
Cincinnati counties, the KC cluster, Marion IN, Kent MI, Dane WI outside the
city), mark `bldg_sf = unpublished`, `sf_source = none`, and **keep the row** —
an unknown-SF trade is still a trade. Never infer SF from improvement value and
present it as SF. If a footprint spatial join or an ECF study supplies SF, name
the source in `sf_source`; footprint ≠ gross building area, so say which.

### 5. Flag non-arms-length — flag, never drop
Nominal-transfer share of recent sale dates runs **40%+ in some counties**
(Ohio especially: re-titlings, intra-family, entity reorganizations). Dropping
them silently is wrong twice — it hides re-titling activity that is itself a
signal, and it makes the digest look thinner than the recording activity was.
Flag `NONARMS` when any of:
- price = $0 or < $25,000 (the county-parcel-screen threshold), or
- price / assessed total value is wildly off-band (outside ~0.5-4.0x), or
- the county publishes a validity/conveyance code saying so — Hamilton
  `VSALEVAL`, Henrico `val_code_1` ('1 - VALID SALE'), Clermont `SALETYPE`,
  Baltimore `CONVEY1`, Butler's deed transfer type, or
- grantor and grantee share a surname or entity stem, or
- `instrument = Contract` (Polk IA land-contract sales — economically real but
  not a cash comp; flag distinctly as `CONTRACT-SALE`).

`NONARMS` rows appear in the digest with the flag visible and are excluded from
any aggregate median $/SF the digest computes. Say the excluded count.

**Worker split (v0.7):** the ratio band is weak evidence on its own (G8 stale
assessed values trip it on genuine high-value sales). A real-priced row whose
ONLY non-arm's-length signal is the ratio band carries `RATIO-REVIEW` instead of
`NONARMS`: it keeps its Price PSF on the row but is excluded from the coverage
median and the Clean $/SF count until a human validates it, and the digest lists
those rows separately. $0 / under $25K, shared grantor/grantee stem and county
validity codes stay hard `NONARMS`. Known gap: the worker's 0.5-4.0x band is
global, while this skill requires per-county ratio tests (Baltimore Co assessments
run ~64% below sales).

### 6. Roll up multi-parcel transactions
One deed can span several parcels (Polk publishes `dps`/`gps`; Butler publishes
`No Of Parcels`). Price is transaction-level; SF is parcel-level. Left unrolled,
$/SF on a multi-parcel sale is garbage — usually a wild overstatement. Group by
deed/instrument number where published, sum SF across the parcels in the group,
compute $/SF once at the transaction level, and flag `MULTI-PARCEL` with the
parcel count. Where no instrument number is published, group on
(county, sale date, price, grantee) and flag the grouping as INFERRED.

**Franklin deed grouping (v0.7):** the Tax Accounting Transfer file publishes
`ConveyNumber` and the deed's full `ParcelCount`, so the worker groups on the deed
number (`MULTI-PARCEL`, not INFERRED) and keys the row on its lead parcel plus
`+N` for the N additional member parcels (unchanged from the inferred key shape). A deed that covers more parcels than the feed holds is
`MULTI-PARCEL` + `SF-INCOMPLETE` with no $/SF, and its assessed value is dropped
so the ratio test cannot fire on a partial sum (G3). Because a deed number can
fail to attach to one member (ambiguous same-day deeds, amount mismatch), any
same-date, same-price row beside a deed group that is short of its published
count is treated as a possible unnumbered member: `MULTI-PARCEL-INFERRED` +
`SF-INCOMPLETE`, no $/SF. The 150K SF cap uses the known member SF even when the
total is incomplete.

### 7. Compute and assemble
`$/SF = price / building SF`, only where both are real and the transaction is
single-parcel-or-rolled-up and not flagged NONARMS. Where SF is unpublished,
leave $/SF blank — **blank, never zero, never imputed.** Assemble one row per
transaction with:

| Field | Notes |
|---|---|
| `property_address` | site address, not mailing address |
| `county`, `state`, `market` | ORA cluster name |
| `parcel_id` | native county format; note that GIS-layer and tax-file formats differ (Franklin `010-104049` vs `"010-104049-00"`) |
| `sale_date` | as recorded; note epoch-ms fields (Richmond City, Henrico) need conversion |
| `sale_price` | as published |
| `bldg_sf` | integer or `unpublished` |
| `sf_source` | in-layer / CAMA extract / footprint join / ECF study / none |
| `price_psf` | blank if not derivable |
| `buyer` / `seller` | where public; `not published` where the county scrubs names (Anne Arundel, Howard) or publishes grantee only. Franklin (worker, v0.7): Seller is the INFERRED prior owner of the parcel, always labelled "(prior owner, inferred)", never a published grantor; blank when a different grantee recorded the same day (chain) or the deed is not matched. An inferred seller never feeds the shared-stem NONARMS test or ORA-AFFILIATED. |
| `convey_number` / `instrument_type` | Worker rows: deed number (Franklin ConveyNumber) and raw instrument code (Franklin InstrumentType: LW, GW, WD, QC, AF ...; Polk Deed / Contract). Codes are shown raw and are NOT an arm's-length gate: LW appears on both priced sales and $0 re-titlings. |
| `use_code` + `use_description` | native code and its meaning |
| `flags` | NONARMS / RATIO-REVIEW / CONTRACT-SALE / MULTI-PARCEL(n) / LATE-POSTED / ORA-AFFILIATED / SF-UNPUBLISHED (Worker rows also carry SF-INCOMPLETE and MULTI-PARCEL-INFERRED) |
| `source` | county + layer/file the row came from, so any row is re-verifiable |

Then a **per-county coverage block**: rows found, window queried, data source,
and for Tier C counties an explicit "no public sale-price data (reason)" line.
A county that returned zero rows and a county that structurally cannot return
rows are different facts and must read differently — an inferred null presented
as a verified null is a failure (ORA doctrine).

### 8. Deliver
**Ratified 2026-08-15: the Notion database is the system of record, not a
workbook.** Each transaction is one page/row in a dedicated Notion database
(propose `County Sales Comps` under the Knowledge Base parent `3386ecd8` —
confirm exact placement with Gabriel before first creation via
`notion-create-database`, then upsert rows with `notion-create-pages` /
`notion-update-page` on later runs). Properties mirror the row spec table in
Step 7 (`property_address`, `county`, `state`, `market`, `parcel_id`,
`sale_date`, `sale_price`, `bldg_sf`, `sf_source`, `price_psf`, `buyer`,
`seller`, `use_code`, `flags`, `source`), plus a `run_date` property so
repeated runs are traceable. Upsert key = `county + parcel_id + sale_date +
price` (same key as the Step 1 late-posted diff) — a re-seen transaction
updates in place, it never duplicates a row.

This makes the database itself the growing comp base: it accumulates
row-over-row across every monthly run rather than resetting each time, so
"what traded in Franklin OH over the last year" becomes a live query against
accumulated rows, not a pile of separate files to reconcile by hand.

Email body (not the full digest) carries the top-line: N transactions, 3
markets, median $/SF where derivable, plus any coverage regression (a Tier A
county that returned nothing when it previously returned something is a
**finding**, not an empty result) — with a link to the Notion database view.

**Exception, Baltimore Co MD only:** its TRADATE lag runs ~4+ months (see the
Tier A coverage note above), so a run reporting few or zero new Baltimore Co
transactions is EXPECTED, not a regression — do not flag it as one on its own.
Only escalate Baltimore Co as a real finding if the pattern itself changes:
e.g. a prior run had current data and a later run's most-recent date is now
OLDER (the lag window widening further), or the query errors outright. Judge
by the shape of the date distribution, not the raw new-row count.

Internal only. Routing per ORA canon: `ggoldberg@oxfordra.net` ONLY, no cc.
Recorded sales are public record, but the digest is ORA work product — it is not
an external surface and must not be forwarded outside the firm without review
(Invariant 3 applies to any row that touches an active confidential deal).

### 9. Recurring execution — digest scheduling is NOT part of this skill
**As of v0.6 (2026-10-02) pull + filter + format run as a hosted Notion Worker**
(`county-sales-monitor`, worker id `01a0fa61-6ca4-78f2-895d-5aafe648dbbf`, repo
`C:\Users\Owner\ora-county-sales-monitor`), refreshing weekly a trailing
365-day window (the 30-day digest window stays the digest's scope), Tier A
comps only, writing to the two "(Worker)" databases under References. Worker
semantics differ from §1/§5 where noted: LATE-POSTED means first seen more
than 30 days after the sale date on any post-baseline cycle, and `Price PSF`
is also blank on SF-INCOMPLETE rows. That makes the *store* current
without the Desktop app or either scheduler fleet. It does not email: the
monthly digest remains a separate reader of those databases.

**Franklin Transfer-file ingest (v0.7, deployed 2026-10-02).** Each cycle the
worker lists the auditor's newest "YYYY-MM-DD Tax Accounting" folder, reads the
zip directory of `Tab-Delimited.zip` (121 MB) with HTTP Range, range-fetches only
the three `Transfer*.txt` entries (~41 MB compressed), stream-inflates them and
keeps only rows for the parcels the GIS pull returned (~5 s, +55 MB RSS locally;
hosted executes 2-10 s; Notion publishes no worker memory or timeout limits).
Rows join on parcel + sale date + price; when several same-day deeds fit, the GIS
buyer must single one out or nothing is published for the row. The drop lags the
GIS layer ~1 month: unmatched sales dated on or after the folder date are expected
lag, not an error. Operating rules that follow from this:
- **A failed or degraded transfer load emits NO Franklin comps that cycle** (the
  coverage row shows WARN with the reason). Grouping would otherwise revert to the
  inference and re-create rows the deed numbers retired (G11). Existing rows stay.
- **Regroups retire stale rows only on proof.** When deed numbers show a sale was
  grouped differently than the row the worker wrote earlier, the stale key is
  deleted in the same execute that writes its replacement (or immediately when the
  sale is now out of scope), and the earliest First Seen is carried to the new
  key so the regroup is never mistaken for a late-posted deed. A row that merely
  left the feed (parcel re-sold, last-sale overwrite) is history and is never
  deleted.
- **Upserts are stamped with the UTC day, so a re-upsert on the same UTC day is
  skipped by Notion.** New fields and flags reach EXISTING rows on the first cycle
  of a new UTC day; a same-day trigger only writes new keys and deletes.

This skill defines pull + filter + format only. Making the digest recur goes through
`register-scheduled-task` (supervised `create_scheduled_task` MCP tool only —
JSON-splicing a registry is prohibited and has been proven to register-but-
never-schedule), on the correct fleet, routed to `ggoldberg@oxfordra.net`.
Do not register anything from inside this skill, and do not assume a schedule
exists because this section describes one.

## Boundary with county-parcel-screen (read before routing)

| | county-parcel-screen | county-sales-monitor |
|---|---|---|
| Question | who might sell to us | what actually traded |
| Unit | owner / parcel | transaction |
| Universe | current ownership snapshot | recorded transfers in a window |
| SF gate | 10-80K (buy-box) | <150K (awareness) |
| Scoring | 0-100 buy-box scorecard | none |
| Motivation mining | delinquency / estate / sellers-in-motion | none |
| Exclusions | gov + institutional + never-call + value band | gov/exempt only |
| Output | ranked owner call list | Notion comp database (accumulating) |
| Leads to | direct-to-owner outreach | market intelligence, comp sets |
| Cadence | per-market campaign runs | monthly recurring feed |

Overlap is real in one place only: county-parcel-screen's *sellers-in-motion*
signal reads the same transfer files this skill reads. That is fine — different
question, same source. If this skill's pull materially improves the transfer
parse, push the improvement into county-parcel-screen's scripts rather than
keeping a better private copy.

Downstream consumers (hand off, don't duplicate): `acquisition-underwriting`
COMPS mode for a single-property comp grid; `market-monitor` for vacancy /
rent-growth / market-condition narrative; `memory/markets.md` for durable
validated comps; the replacement-cost benchmark (RCT v03) is the ratified
denominator — this skill reports observed $/SF, it does not re-derive a
replacement-cost benchmark.

## Engineering notes (inherited — verify, don't re-learn the hard way)
- bash sandbox: 45s per call. Use county-parcel-screen's `scripts/dl_resume.py` (`county-parcel-screen/scripts/dl_resume.py` in this repo; other skill, not bundled here)
  for files >40MB (Franklin `Transfer010.xlsx` is 43MB; Hamilton
  `HistoricSalesExport.xlsx` is 59MB; the Polk sales CSV ~13MB is fine direct).
  Unzip into a NEW subdirectory — the sandbox cannot overwrite files written by
  a previous call.
- Excel bulk files: `pip install python-calamine`, pandas `engine="calamine"`.
  openpyxl times out on 250K-row files.
- Parcel-ID formats differ between a county's GIS layer and its tax/sales files.
  Normalize before joining and **assert the join matched** — a silent 0-match
  join looks exactly like a quiet week.
- Some county report servers WAF-gate downloads (Butler 403s): send full browser
  headers (UA + Accept + Referer + Sec-Fetch-*). Polk's Akamai WAF tolerates
  plain urllib with a normal UA.
- Date encodings vary: epoch ms (Richmond City `LAST_SALE_DATE`, Henrico
  `sale_date`), `'DD-MON-YY'` (Butler `SALEDT`), `YYYYMMDD` (Baltimore
  `TRADATE`), ISO-ish strings (Chesterfield). Normalize to ISO date on ingest.
- Text fields are space-padded in some counties (Kent MI everything, Polk
  occupancy codes) — strip before comparing.
- `LAST_SALE_*`-style fields hold only the most recent sale. They are a *state*,
  not a log: a parcel that sold twice in the window shows once, and a parcel
  whose sale predates the window still carries a populated field. Always filter
  on the date, never treat presence of the field as recency.

## Failure modes (carry into every QC sheet)
G1 recording lag — window-only queries permanently drop late-posted deeds (fix:
the prior-run key diff, Step 1) | G2 nominal/re-titling transfers read as sales
(40%+ in some OH counties) | G3 multi-parcel deed inflates $/SF | G4 SF absent →
$/SF silently imputed or row silently dropped | G5 Tier C county's structural
absence read as "nothing traded" | G6 endpoint drift since the last registry
verification | G7 `LAST_SALE_*` snapshot mistaken for a transaction log |
G8 stale assessed values distort the arm's-length ratio test (the same F2 that
bites county-parcel-screen — Baltimore Co's 1.639 @3yr vs 1.211 @5yr) |
G9 use-code lag: a code says industrial after conversion, or vice versa |
G10 grantor/grantee blank in the recent window specifically (Madison city
conveyances post-mid-2023) — parties look missing when only the recent ones are |
G11 deed-grouping flap — a degraded deed-file load reverts grouping to the
inference and re-creates rows the deed numbers retired (fix: emit nothing for that
county that cycle; regroup deletes ride with their replacement) | G12 inferred
seller read as a published grantor — the Franklin Seller is the prior owner on the
parcel, labelled as inferred, and is never a classification input.

## References
- **Notion database (LIVE, created 2026-08-15):** `County Sales Comps` —
  https://app.notion.com/p/311cf71222d14a56aa33da354cb3a1ea, data source
  `collection://63a5e6b3-2655-4e0c-9843-3102d78adc0d`, nested under Knowledge
  Base → Knowledge & Archive → Oxford Real Assets Operations Hub. Schema:
  Property Address (title), County/State/Market (select, currently only the 3
  Tier A values — add options when Tier B expands), Parcel ID, Sale Date,
  Sale Price, Building SF, SF Source, Price PSF, Buyer, Seller, Use Code, Use
  Description, Flags (multi-select), Source, Run Date. Upsert key = County +
  Parcel ID + Sale Date + Sale Price (match before insert, never blind-append).
- **Worker-managed databases (LIVE, deployed 2026-10-02; nested under Knowledge
  Base `3386ecd8`):**
  - `County Sales Comps (Worker)` — database `3ed6ecd8-9e59-8168-a367-df08b6ff6d3b`,
    data source `collection://28bae38c-f495-4c9e-9edc-b86c0ae2c413`. One row per
    transaction; upsert key `County|Parcel|SaleDate|Price`; County options are
    `Franklin` / `Baltimore County` / `Polk` / `Cook` (the legacy DB uses `Franklin OH` /
    `Baltimore Co MD` / `Polk IA`). Adds `Comp Key`, `Parcel Count`,
    `First Seen`, `Days to First Seen`, `Last Synced`, `Convey Number`,
    `Instrument Type`, and the `SF-INCOMPLETE`, `MULTI-PARCEL-INFERRED` and
    `RATIO-REVIEW` flags.
  - `County Sales Coverage (Worker)` — database `3ed6ecd8-9e59-81b1-947b-dff540312cfc`,
    data source `collection://f26e704a-9191-436b-85cf-fd64258928be`. One row per
    county per cycle (10 Tier A + 4 Tier C = 14, after the v0.11 deploy).
  - Managed databases are read-only to everything but the worker; schema changes
    go through a worker redeploy and can drop data. Ops: pause with
    `ntn workers capabilities disable <sync>`; never delete the worker or the
    databases.
  - The legacy `County Sales Comps` database (above) is retained, unmodified,
    pending Gabriel's decision on archiving.
- `../county-parcel-screen/references/county-endpoints.v1.json` — machine-readable
  service URL / layer id / JURSCODE registry. Consume programmatically. Do not
  copy into this skill.
- `../county-parcel-screen/references/county-endpoints.md` — source of truth for
  sale/value/SF field names, ID formats, per-county quirks. Wins on conflict.
- `../county-parcel-screen/references/market-status.md` — per-market run history;
  the source of the Tier A / Tier C coverage facts above.
- ORA memory `markets.md` (validated comps), `project_replacement_cost_benchmark_unratified.md`
  (RCT v03 — the ratified denominator, read-only from here).

## Constants so far (carried from county-parcel-screen, not re-derived)
Nominal-transfer share of recent sale dates ~40%+ in Ohio counties; commercial
building SF publication is the exception (Franklin, Baltimore Co, Polk, Henrico,
Chesterfield), not the rule; MO and KS are non-disclosure states — no public
sale price, permanently; Ohio auditor-to-market ~1.6x post-2023 reappraisal
(relevant here only as the ratio band for the arm's-length test, not as a
valuation input); Baltimore Co assessments run ~64% below recent industrial
sales, so ratio-based arm's-length tests must be per-county, never global.

## Changelog
- **v0.12 (2026-11-05):** The Geography line said "the other eight ORA clusters
  are Tier B/C". That was true while Tier A held three clusters; with Cook IL
  (v0.10) and the Indianapolis cluster (v0.11) promoted it is six, so the line
  now names no count. Wording only; no county, tier or price rule changed.
- **v0.11 (2026-10-30):** Indianapolis cluster IN (Marion, Hamilton, Boone,
  Hendricks, Johnson, Hancock) promoted to Tier A as a partial-price source. The
  Worker adapter is `src/counties/indiana.ts` + `src/sdf.ts`. Only priced
  disclosures are emitted; confidential ones are counted on coverage. Industrial
  class list 330/340/345/346/350/370 **ratified by Gabriel 2026-10-30**.
  Worker county labels carry the state suffix (`Marion IN` ...) to stay distinct
  from same-named counties elsewhere. No change to scored or governor constants.
- **v0.10 (2026-10-30):** Cook IL promoted to Tier A (Worker adapter
  `src/counties/cook.ts`, `ZeOoba/ora-county-sales-monitor` PR #7). Indiana's
  statewide SDF file verified as a partial-price source (Tier B entry above;
  adapter planned). Cook multi-PIN deeds group on the published `doc_no`; SF is summed per
  valuation group only when every group lies wholly inside the deed, otherwise
  unknown with the cap still applied. Takes effect on the Worker's next
  supervised deploy. No change to scored or governor constants.
- v0.9.1 (2026-10-29): Spelled out the cross-skill path of `dl_resume.py`. This was a reference-path clarification only (wording; no change to procedures, scored or governor constants): NO change to scored or governor constants.
- **v0.9 (2026-10-15):**
  Closes the open Worker defect recorded in v0.8. Step 3's government/exempt
  exclusion was implemented for Baltimore (`EXCLASS`) and Polk (DOR quality) but
  not for Franklin, whose parcel layer carries no exempt field (`EXPLUC` empty on
  all 219 industrial-class parcels sold since 2025-10-02; `TOTVALUEEXP` reflects partial exemptions; `PCLASS` is
  "I" throughout). The fix is a current-owner (buyer) name test in the Worker's
  Franklin adapter (`ZeOoba/ora-county-sales-monitor` PR #5, commit `fe32c9f`,
  merged to `main` as `32abe0b`; `src/counties/exempt.ts`). Decisions (Gabriel,
  2026-10-15): (A) scope is government plus PUBLIC institutions (state, city, county, authorities, public
  colleges and schools); churches, other nonprofits and private institutions are
  KEPT, so this is narrower than Polk's "Government or Exempt" class, which also
  removed a church and a nonprofit; (B) rows already written are left in place,
  not deleted; (C) a numbered deed with any government parcel is dropped whole.
  Seller is never tested (Franklin Seller is inferred, and an inferred seller
  never drives a flag). The filter runs after deed enrichment so exclusions cannot
  trip the degraded-pull WARN, and an excluded sale is never reported as a
  dropped group, so `planRegroup` cannot retire its existing rows. Coverage Notes
  gain the line `N government/public-institution sale(s) excluded.` No change to
  `rules.ts`, the schema, county labels or the key format. Pre-deploy evidence:
  typecheck, lint and 57 of 57 tests clean; a read-only live pull of the Franklin
  layer (window start 2025-10-15) went from 208 raw to 204 kept with 4 sales
  excluded; the name test run on 91 distinct live Franklin owner names flagged 21,
  all public bodies, and kept private owners such as OHIOHEALTH CORPORATION and
  OHIO POWER COMPANY. The `simulate` comps cycle moved Franklin from 164 to 160
  rows and the harness's own median from $117.77 to $113.14 (Columbus State
  Community College, $236.05/SF, was the only excluded sale with a $/SF; see the
  post-deploy note below for the Coverage-basis figures). **Orphaned rows:** the four existing
  Franklin comps below were written before the filter and are now excluded, so
  they stay in the Comps DB with a frozen `Last Synced` and no longer update.
  Treat them as excluded when reading the database; do not count them toward
  Franklin medians or volumes:
  `Franklin|130-011588|2026-02-09|0` (State of Ohio),
  `Franklin|520-165723|2026-05-19|0` (City of Columbus),
  `Franklin|010-282683|2026-01-29|0` (Columbus Regional Airport Authority),
  `Franklin|010-005337|2025-12-23|1950000` (Columbus State Community College,
  the only one with a $/SF). Known limits (best effort, also in the Worker
  README): a public body whose name contains a church-type word is kept; a
  public body ending in the abbreviation "CO" is missed; a private college is
  not recognised as public; a suffix-less private name that reads like a public
  body (for example "STATE OF THE ART STORAGE") would be dropped. Known
  unrelated issues: the Worker's `npm run simulate` fails a date-dependent
  assertion in its own harness (`test/simulate.ts:73`), identically on unmodified
  `main`; and GitHub Actions jobs die in about 3 seconds with no logs on every
  run in both the Worker repo and ora-skills, so CI status is not evidence about
  these changes. **Deployed 2026-10-15** from `main` at `32abe0b` with no schema
  change; the existing Worker was updated, not duplicated (the same two managed
  databases received the new cycle; no new databases appeared). **First
  post-deploy cycle, run date 2026-10-15 (window start 2025-10-15), read from
  Notion:** the Franklin Coverage row is OK and its Notes read "4
  government/public-institution sale(s) excluded", as predicted. Franklin
  Transactions 160 (167 on 2026-10-10), clean $/SF rows 40, NONARMS rows 90,
  median $100.68. That median reproduces exactly from the Comps DB: the 40 clean
  rows have a median of (100.64 + 100.71) / 2. The filter's own effect on it is
  about $0.04 (removing the $236.05/SF college row moves the median from 100.71
  to 100.68), so the filter is not what moved it from $117.77 on 2026-10-10. That
  fall coincides with the window rolling forward five days and new sales posting
  (the Comps DB now holds a $35.73/SF sale dated 2026-10-09), on a distribution
  with a gap around the middle (100.71, 113.14, 117.77), where a few rows
  crossing the window edge move the median this far; the exact rows that left the
  window were not diffed. The `simulate` figures above (a $113.14
  median) are on the harness basis, which includes RATIO-REVIEW rows and takes
  the upper middle value, so they do not compare to the Coverage median. Comps DB
  after the cycle: Franklin 172 rows / 172 distinct Comp Keys (160 upserted this
  cycle, equal to the Coverage Transactions), Polk 64 / 64, Baltimore Co 38 / 38;
  0 duplicate Comp Keys; 0 LATE-POSTED; `Price PSF` never 0 and blank on every
  NONARMS, CONTRACT-SALE and SF-INCOMPLETE row. The four orphaned keys above are
  present and unchanged (Last Synced 2026-10-10, same flags, the college row
  still carrying its $236.05/SF).
- **v0.8 (2026-10-15):** Post-deploy verification of the Worker databases and a
  fresh parity run against the legacy pilot (read-only; no Worker or database
  change). Worker DB state 2026-10-15: 273 comps (Franklin 171 / Baltimore Co 38
  / Polk 64), 273 distinct Comp Keys, 0 duplicates, `Price PSF` never 0 and blank
  on all 147 NONARMS / CONTRACT-SALE / SF-INCOMPLETE rows, 0 LATE-POSTED; Coverage
  holds 7 rows per cycle (cycles 2026-10-02, 10-03, 10-10). Parity, window
  2025-10-01 to 2026-08-15, strict County+Parcel+Date+Price: 189 matched of 258
  legacy rows; 227 equivalent at transaction level. Strict misses are 17 Baltimore
  Co rows with a NULL price in both databases (SQL NULL never equals NULL; 38 of
  38 match once NULL-safe), 14 Polk rows where the legacy ID is the 14-digit `dp`
  and the Worker lists the member `gp` PINs, and 7 Franklin legacy rows vs 14
  Worker rows from multi-parcel deed granularity (priced deeds roll up in the
  Worker; $0 NONARMS deeds emit one row per parcel and now carry SF). The 31
  remaining legacy-only rows resolve to: 20 with SF >= 150K (Worker SF gate), 2
  Franklin deeds legacy marked SF-UNPUBLISHED that are over the cap ($15.4M
  Action Group parcel 010-000782 at 153,412 SF; $137.8M NLF Columbus parcel
  495-286103 at 1,600,052 SF), 3 Franklin sales dated 2025-10-01 before the
  Worker's first window start, 4 Franklin parcels (Westerville Rd, $0 on
  2026-07-29) whose GIS `SALEDATE` was overwritten by a 2026-08-18 $13,005,000
  resale (G7, verified against the live layer), and 2 Polk sales whose DOR
  `quality` is "Government or Exempt" (a church and a nonprofit; verified in the
  live CSV), which the Worker excludes by design. This closes the "1 Polk
  unexplained" row in v0.6. The Coverage `Transactions` count runs below the
  Comps row count by design: the Comps DB never deletes, so rows whose sale date
  has aged past the rolling 365-day window stay (10-10: 167 / 37 / 62 vs 171 /
  38 / 64; 4 / 1 / 2 rows dated before 2025-10-10). **Open defect (Worker, not
  fixed here):** Step 3's government/exempt exclusion is implemented for Baltimore
  (`EXCLASS`) and Polk (DOR quality) but NOT for Franklin; two $0 NONARMS rows
  with government buyers (State of Ohio, City of Columbus) are in the Franklin
  set. Ruled a Worker defect by Gabriel 2026-10-15; fix is a Worker change
  (src/counties/franklin.ts) and needs a separate approved redeploy.
- **v0.7 (2026-10-02):** Worker follow-ups ratified by Gabriel the same day.
  (1) `RATIO-REVIEW` splits ratio-only trips out of `NONARMS` (Franklin 20 rows,
  Baltimore Co 1, Polk 0 on the first run; coverage medians unchanged by design).
  (2) Franklin Transfer ingest adds Convey Number, Instrument Type, deed-published
  parcel counts and an inferred, labelled prior-owner Seller; deed-numbered groups
  replace the buyer-name inference. First deployed cycle: Franklin 173 -> 169 rows
  (5 superseded rows deleted, 1 regrouped row added; 3 of the 5 are large groups
  now correctly over the 150K SF cap: a $117M Parsons Ave foundry, a $137.7M Shook
  Rd group, a $15.4M Reynoldsburg-New Albany group, each with a single parcel above
  the cap on its own), Baltimore 38 and Polk 64 unchanged, 194 of 215 sales
  matched (199 before the same-day-deed ambiguity rule withheld 5; the other 16
  unmatched are all dated after the 09-15 drop). Adversarial review took three
  rounds; defects found and fixed before deploy: orphaned group keys, false
  LATE-POSTED on regroup, doubled $/SF on a deed member left without a number,
  deletes sent ahead of their replacement rows, SF cap bypass through the
  multi-parcel guard. New failure modes G11, G12. Seller inferred rule left OFF
  for the shared-stem test (Gabriel, 2026-10-02). IsValid remains unusable. Open:
  per-county ratio bands; two priced in-window Franklin sales hidden by the GIS
  last-sale field (G7) are findable via the transfer history if recovery is wanted.
- **v0.6 (2026-10-02):** Pull, filter and format now run as a hosted Notion
  Worker (`@notionhq/workers` locked at 0.9.2; two weekly incremental syncs; Tier A comps only;
  no secrets). First cycle 2026-10-02: 275 comps (Franklin 173 / Baltimore Co 38
  / Polk 64), 275 distinct keys, 0 LATE-POSTED (baseline cycle), `Price PSF`
  blank on every NONARMS / CONTRACT-SALE / SF-INCOMPLETE row and never 0;
  coverage database 7 rows. Clean $/SF medians (coverage rows): Franklin
  $115.46, Baltimore Co $155.68, Polk $120.08. Parity vs the legacy pilot
  (strict County+Parcel+Date+Price, 2025-10-01 to 2026-08-15; the worker's own
  window starts 2025-10-02): 207 matched (Franklin 119 / Baltimore 38 / Polk
  50); 51 legacy-only, 32 new-only. Legacy-only causes: multi-parcel
  representation 23 (incl. 3 Franklin parcels the worker rolls into one
  MULTI-PARCEL-INFERRED row), Franklin rows with SF >= 150K that the legacy
  kept and the worker's SF gate drops 20, window edge 3, other 5 (4 Franklin
  last-sale-only `SALEDATE` overwrites, G7; 1 Polk unexplained). Use-code lists and the 25D / 46A Polk
  exclusions are unchanged from v0.5; the flag set (adds SF-INCOMPLETE and
  MULTI-PARCEL-INFERRED), PSF blanking on SF-INCOMPLETE, the 365-day re-pull
  and the First-Seen-based LATE-POSTED rule differ from the v0.5 manual
  workflow. Polk sales export observation: see `county-endpoints.md`.
- **v0.5 (2026-08-15):** Post-pilot QC pass on the live Notion data (304 rows
  queried directly, not just re-read from agent reports) confirmed row counts
  and key-uniqueness clean, but surfaced one real finding the original pilot
  reports missed: Baltimore Co MD's TRADATE field runs ~4+ months behind
  (clean taper Feb-Apr 2026, zero May-Aug despite the window running current)
  — worse than Franklin's known ~1-month lag. Documented in the Tier A
  coverage note and carved out of Step 8's coverage-regression check so the
  monthly scheduled task doesn't misread expected Baltimore Co quiet months
  as a finding. Same fact added to county-parcel-screen's `county-endpoints.md`.
- **v0.4 (2026-08-15):** First live pilot run executed — all three Tier A
  counties, 12-month window (2025-08-15 to 2026-08-15), 304 transactions
  written to the Notion database (Franklin OH 179, Polk IA 80, Baltimore Co
  MD 45). No endpoint drift on any documented field, but all three counties
  surfaced real gaps in county-parcel-screen's `county-endpoints.md` that this
  skill's agents correctly did NOT patch themselves (per instruction): Franklin's
  GIS `VALID` field is null-populated and useless (its transfer file's `IsValid`
  works instead); Polk's `quality` DOR validity column was undocumented;
  Baltimore's `CONVEY1=4` conveyance code (driving ~half its "transfers") is
  undocumented anywhere public. Franklin's NONARMS rate (81.6%) ran well above
  the ~40% Ohio baseline — partly real, partly the documented G8 stale-assessment
  failure mode tripping the ratio test on genuine high-value 2025-26 sales.
  Per-county medians: Franklin $120.27/SF (n=25), Baltimore Co $152.51/SF
  (n=18), Polk $105.04/SF (n=43) — not blended into a portfolio figure, the
  three markets aren't comparable on one number. Franklin also found its bulk
  transfer file lags the live GIS layer by ~1 month (25 of 179 rows had no
  transfer-file match yet, Seller reported "not published" rather than guessed).
  No scheduled task registered — still a separate future step.
- **v0.3 (2026-08-15):** Gabriel ratified the remaining four open questions:
  Notion database nests under Knowledge Base `3386ecd8` (not standalone);
  first-run lookback is 12 months for all three Tier A counties; comps stay
  Notion-only for now (no auto-flow into `markets.md`); next step is building
  the Tier A pilot directly, not a skill-creator eval loop. KC cluster
  handling remains deferred (genuinely not urgent — out of scope until Tier B
  expansion). Nothing left blocking the pilot build.
- **v0.2 (2026-08-15):** Gabriel ratified four scope decisions: monthly
  cadence (not weekly), Notion database as the delivery surface (not a
  workbook), Tier A pilot only at launch (Franklin OH / Baltimore Co MD /
  Polk IA — Tier B expansion is a distinct later pass), and Louisville /
  Jefferson Co KY deferred until after the nine existing clusters ship.
  Sections updated throughout to match.
- **v0.1 (2026-08-15):** Initial DRAFT for Gabriel's review. Specification only —
  no pilot run, no scheduled task, no scripts, no evals. Coverage tiers derived
  from county-parcel-screen `market-status.md` + `county-endpoints.md` as of the
  2026-07-24 revision; Tier B counties are documented-but-unexercised for a
  windowed sales pull.

## Ratified decisions (all seven original open questions — 2026-08-15)

1. **Cadence:** monthly, 30-day trailing window.
2. **Delivery:** Notion database (`County Sales Comps`, under Knowledge Base
   `3386ecd8`), not a workbook — accumulates row-over-row, upsert-keyed on
   `county + parcel_id + sale_date + price`.
3. **Launch scope:** Tier A only — Franklin OH, Baltimore Co MD, Polk IA.
   Tier B/C and Louisville/Jefferson Co KY are a documented later expansion.
4. **First-run lookback:** 12 months, all three Tier A counties.
5. **Comp persistence:** Notion-only for now; promoting a comp into
   `memory/markets.md` stays a manual, deliberate act.
6. **KC cluster handling:** deferred — out of scope for Tier A, revisit only
   when Tier B expansion reaches Jackson/Clay/Platte MO or Johnson/Wyandotte KS.
7. **Next step:** build the Tier A pilot directly against live endpoints
   rather than running skill-creator's synthetic eval loop first — the real
   open risk is whether the documented county fields actually work for a
   windowed pull, which only a live run proves.

Nothing remains open before the pilot build. No scripts, evals, or scheduled
task exist yet as of v0.3 — those are the pilot build's own output, not this
spec's.
