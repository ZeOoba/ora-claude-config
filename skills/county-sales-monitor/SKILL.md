---
name: county-sales-monitor
description: >
  ORA recurring industrial sales/transfer digest. Pulls recently RECORDED
  industrial sales (bldg SF <150,000) from county-parcel-screen's endpoint
  registry on a trailing 30-day window, flags non-arms-length/nominal
  transfers, and writes each transaction into a queryable Notion comps
  database with $/SF where derivable. Trigger on: recent industrial sales,
  county sales tracker, sales digest, transaction monitor, comp tracking,
  recent county transfers, industrial sales this month, what traded, who's
  buying or selling industrial in a market, new comps since [date], set up a
  sales feed — Franklin OH / Baltimore Co MD / Polk IA at launch, other ORA
  markets are a documented next phase. MARKET INTELLIGENCE, not sourcing: does
  NOT replace county-parcel-screen (off-market owner call lists, motivated
  sellers, delinquent-tax/estate leads). Single-property comp grids route to
  acquisition-underwriting COMPS mode. v0.5 (2026-08-15) — piloted (304
  transactions live in Notion) and scheduled monthly (ora-county-sales-monitor).
---

# county-sales-monitor

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
gives enough volume for a real median $/SF). Geography at launch: the three
Tier A counties only (below) — the other eight ORA clusters are Tier B/C,
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
MD, and Polk IA are the entire pilot. Tier B and Tier C are documented below
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
  current, refreshed continuously: `sale_date`, `price`, `instrument`
  (Deed | Contract), `seller`, `buyer`, book/pg, plus the CAMA snapshot
  (`gross_area` = building SF, occupancy). The best assessor source found to
  date and the only one with clean grantor/grantee back three decades.

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
`LAST_SALE_PRICE`; Marion IN as a disclosure state; Dane WI only via the
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
Polk's sales CSV is continuous; Ottawa's is annual). A strict `sale_date IN
window` query will permanently miss every deed that posted late. So: query the
window, **and also** diff the full recent-sales key set against the prior run's
persisted key set, and surface late arrivals in a separate `LATE-POSTED` block
with their true sale date. Key = county + parcel ID + sale date + price.

### 2. Pull the universe, per county
Launch scope is Tier A only (Franklin OH, Baltimore Co MD, Polk IA) — the
mappings below for other counties are carried forward for the documented
expansion phase, not exercised in v0.2. Industrial use codes only, taken from
county-parcel-screen's already-resolved mapping — Ohio DTE 300-series (`CLASSCD`/`CLASS` 3xx); Jackson MO Ascend
`landuse_cd` 3200-3299; Dane WI SLUCM `2xxx-3xxx` + `6371/6373/6376/6379/6381`;
Polk IA occupancy 46/25C/20A/48/44/20B; Henrico VA 406/675/453/495/670/470/472/
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

### 6. Roll up multi-parcel transactions
One deed can span several parcels (Polk publishes `dps`/`gps`; Butler publishes
`No Of Parcels`). Price is transaction-level; SF is parcel-level. Left unrolled,
$/SF on a multi-parcel sale is garbage — usually a wild overstatement. Group by
deed/instrument number where published, sum SF across the parcels in the group,
compute $/SF once at the transaction level, and flag `MULTI-PARCEL` with the
parcel count. Where no instrument number is published, group on
(county, sale date, price, grantee) and flag the grouping as INFERRED.

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
| `buyer` / `seller` | where public; `not published` where the county scrubs names (Anne Arundel, Howard) or publishes grantee only |
| `use_code` + `use_description` | native code and its meaning |
| `flags` | NONARMS / CONTRACT-SALE / MULTI-PARCEL(n) / LATE-POSTED / ORA-AFFILIATED / SF-UNPUBLISHED |
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

### 9. Recurring execution — NOT part of this skill
This skill defines pull + filter + format only. Making it recur goes through
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
- bash sandbox: 45s per call. Use county-parcel-screen's `scripts/dl_resume.py`
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
conveyances post-mid-2023) — parties look missing when only the recent ones are.

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
