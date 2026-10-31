---
name: county-parcel-screen
description: >
  ORA county-parcel direct-to-owner acquisition screen. Pulls a county's industrial
  parcel universe from public auditor/assessor data, calibrates auditor values to
  market empirically, scores every parcel 0-100 against the ORA buy-box, mines
  delinquency / estate / seller-in-motion motivation signals, and delivers ranked
  call-list workbooks. Use this skill whenever the user mentions: parcel screen,
  county screen, off-market sourcing, direct-to-owner, owner outreach list, cold
  call list, delinquent tax leads, motivated sellers, estate owners, sellers in
  motion, county auditor data, assessor data, parcel data, or asks to find
  off-market industrial acquisition candidates in ANY target market (Columbus,
  Cincinnati, Kansas City, Indianapolis, Maryland, Madison, Grand Rapids,
  Richmond, Des Moines, or a new county). Also trigger for "next market",
  "run the screen on X", or any request to build owner-level lead lists from
  public property records. v1.3 — changelog in body.
---

# county-parcel-screen

Generate off-market industrial acquisition leads for Oxford Realty Advisors from
public county property data. The screen finds owners with the CAPACITY to sell at
ORA's basis-buyer price (low basis, long hold) and the MOTIVATION to do so
(delinquency, estate, liquidation-in-progress). Validated end-to-end on Columbus
and Cincinnati; per-county endpoints and quirks live in references/.

## Buy-box (apply unchanged unless user overrides)

Class B/C industrial / shallow-bay / flex / office-warehouse only. 10,000-80,000
SF building (sweet spot 15-50K). Deal $1-10M; equity sleeve $0.75-5M at 65% LTV.
Hard floors: >=25% discount to replacement (~$150/SF benchmark) AND >8% stabilized
YoC. Instant disqualifiers: retail/office/multifamily, auto-use tenancy,
institutional Class A pricing, outside ORA's nine clusters.

## Workflow

**Counterparty floor — FAIL-LOUD, no degraded fallback (hardened 2026-09-18):**

CANONICAL PATH — load the guard from this absolute path, always:

    C:\Users\Owner\.claude\skills\county-parcel-screen\data\pipeline-guard.local.json

(override only via the `ORA_PIPELINE_GUARD` env var). The file is UNTRACKED and
gitignored on purpose — counterparty names never live in tracked files — so it exists
in exactly ONE place on this machine. It is NOT in the `ora-skills` repo checkout and
NOT in the AppData plugin bundle. Every consumer's old `<skill>/../data/` RELATIVE path
therefore resolves to nothing whenever the skill executes from any copy other than
`~/.claude/skills/` — which is precisely how the 2026-09-18 Jackson MO run came to
screen against ORA-self patterns only. It did warn; the warning was not acted on and
the list shipped anyway (`…JacksonMO_Summary_v01.md`, honest-limits item on the
degraded floor). The same-day Howard MD run loaded the file explicitly and recorded
in its QC paragraph that "the module's own
relative path resolves into the plugin cache, where the file does not exist, and would
have degraded the floor silently."

Rules, in force for every run regardless of which copy of this skill is executing:
1. Load the guard from the CANONICAL ABSOLUTE PATH above — never from a path relative
   to the executing skill copy, and never from a bundled or cached duplicate.
2. Pass its `never_call_names` as `args.neverCallNames` to
   `workflows/parcel-screen-fanout.js` (optionally a full `args.pipelineGuard` to skip
   the Phase-0 Notion fetch).
3. **If the guard cannot be loaded, or loads with zero `never_call_names`, STOP.** Do
   not score, do not rank, do not produce a call list, a workbook or a summary. A
   degraded ORA-self-only floor is NO LONGER an allowed run mode — "no match" from a
   degraded screen is not the same as screened. Report the failure to Gabriel and stop.
4. **Record the guard as evidence in every deliverable.** The workbook README sheet and
   the run summary must each carry the guard file's absolute PATH, its filesystem
   MODIFIED TIME (UTC), and BOTH entry counts — `never_call_names` (what the workflow
   screens on) and `never_call_patterns` (what `institutional_owners.py` screens on).
   They are different lists; citing only one can look screened while the other is
   empty. `institutional_owners.guard_evidence()` returns exactly this dict.

### 1. Discover sources (skip for counties already in references/)
Find (a) an ArcGIS REST parcel layer with owner, site address, tax-mailing
address, land-use code, sale date/price, appraised values - verify field names
via <layer>?f=json and a count query; (b) bulk extracts (tax duplicate w/
delinquency, transfer history w/ owner names, building/appraisal cards, rental
contacts). Spawn a recon subagent per 2 counties when discovering new markets -
it saves main-context budget. Ohio counties all use DTE codes (industrial =
300-series); other states need the use-code scheme mapped first.

### 2. Pull the universe
Industrial use codes, paged queries via sandbox python urllib (web_fetch is
URL-length-capped - never rely on it for paged REST pulls). Building SF
10-80K where the layer has SF; otherwise improvement-value band $150K-$7M as
the size proxy and note the gap. Save raw JSON before processing.

### 3. Exclude
Government/exempt; institutional owners via scripts/institutional_owners.py -
the CANONICAL exclusion module (import screen_owner / screen_mail /
ora_never_call; run on BOTH owner fields AND mail fields). Doctrine:
'EXCLUDE' = drop; 'VERIFY' = keep + flag VERIFY-INSTITUTIONAL and adjudicate
before outreach - never silently drop on a weak token (the DUKE COMBINED
lesson), and never let fund-style names through (the G&I XI lesson; module
catches fund morphology generically). Append newly caught aliases to the
module's TIER1/TIER2 tables with a dated note. Also exclude: value band
outside ~$250K-$8.5M; never-call counterparties (ora_never_call 'NEVER-CALL'
tier = live/former deal counterparties — drop); parcels already in the ORA
pipeline (Notion Acquisition Pipeline bcfe4a03). ORA/affiliate matches
(ora_never_call 'ORA-SELF': Oxford*, Goldberg, FJ&S incl. FJS) are KEPT and
flagged ORA-AFFILIATED — NEVER dropped, per Gabriel 2026-06-10 (the Oxford
Campus I mail-name false positive proved silent drops unsafe). No outreach
to flagged rows without principal adjudication.

### 4. Calibrate empirically - never guess
Auditor-to-market factor = median SALEPRICE / appraised-value of in-universe
arm's-length sales (>=$100K, <=3yr, ratio 0.5-4). Ohio post-2023-reappraisal
runs ~1.6x (Franklin 1.65 n=57; Hamilton 1.61 n=182). Derive basis-score
thresholds FROM the factor: 20 pts = >=40% modeled discount to replacement;
14 = >=25% (the ORA floor); 6 = 10-25%; 0 below. Use ZIP-level ratios where
n>=3 per ZIP - they range 1.0-2.0 within one county.

### 5. Fix the hold score
40%+ of recent sale dates are $0/nominal transfers (re-titling, estate,
intra-family) - NOT purchases. A sub-$25K transfer never scores as a recent
purchase: fall back to the PRIOR arms-length transfer and flag
`HOLD-PRE-NOMINAL`; only if no prior arms-length transfer is published does the
row become UNKNOWN-HOLD (§ "Hold / tenure scoring"). Owner name containing
TRUSTEE/ESTATE/EXECUTOR/SUCCESSOR, or TR + recent nominal transfer ->
ESTATE-SIGNAL: the single highest-priority call flag, because succession is
the one motivation that reliably overrides low-basis capital-gains lock-in.

### 6. Score 0-100
product 25 / size 15 / hold 20 / basis 20 / entity-owner 10 / absentee-mail 5 /
multi-parcel-owner 5. Tiers: A >=90 (call), B 85-89 (mail), C 70-84 (watch),
D (archive). When SF or values are unavailable, rescale honestly (e.g. 0-75
"pre-SF") and say so in the README sheet - never fake a component. The sub-bands
WITHIN each component are pinned below — use them, do not re-infer them.

## Scoring sub-bands (pinned 2026-09-18)

Until 2026-09-18 this skill published only the component WEIGHTS (plus the basis
bands and the 16-point UNKNOWN-HOLD value). On that day the Franklin OH pilot had to
infer the rest, and its choices became the de-facto spec that the same-day Howard MD
and Jackson MO runs then reproduced rather than re-derived. They are pinned here,
verbatim from that pilot's workbook README
(`2026-09-18_RingScreen-FranklinOH_CallList_v01.xlsx`, SCORING block) and its summary.

**These sub-bands were pinned FROM A RUN, not derived from first principles. They are
Gabriel's to amend.** Any run that diverges from them MUST say so on the face of its
summary and workbook README, with the reason — otherwise successive runs stop being
comparable, which is the failure these three runs hit.

**SF gate:** building SF 10,000-80,000. **Value band:** calibrated value ~$250K-$8.5M
(applied AFTER the SF gate). **Tier cutoffs:** A >=90 call | B 85-89 mail | C 70-84
watch | D archive.

- **product 25** — core shallow-bay/flex (DTE 330, 340-343, 350-354, 358, 370-372,
  391, 392) | **18** secondary (302, 310, 355-357, 360, 399) | **10** heavy (320
  foundries). A flagged EXTENSION universe outside the county's ratified industrial
  series (e.g. Franklin DTE 480, Jackson `landuse_cd` 2240/2241) scores **18**, on
  its own sheet.
- **size 15** for 15,000-50,000 SF (the stated buy-box sweet spot) | **10** for
  10,000-14,999 | **9** for 50,001-80,000.
- **hold 20** — graduated curve, NOT a bucket. See § "Hold / tenure scoring"
  below, which supersedes v1.2's 20/18/14/10/5/0 buckets and retires the
  16-point UNKNOWN-HOLD default.
- **basis 20** >=40% modeled discount to the $150/SF benchmark | **14** >=25% (the
  ORA floor) | **6** 10-25% | **0** below. (Already skill-stated; restated here so
  the whole scale sits in one place.)
- **entity 10** where the owner of record is an entity rather than a natural person.
- **absentee 5** where the tax-mailing ZIP differs from the site ZIP.
- **multi 5** — graduated on RELATIONSHIP membership, not raw county parcel
  count: **0** single parcel and no other holding in the county universe |
  **2** single parcel in this cluster but the owner holds 2+ elsewhere in the
  county universe (dispersed portfolio owner) | **3** 2 relationship members |
  **4** 3-4 members | **5** 5+ members, OR 2+ members whose COMBINED SF is
  >=40,000. See § "Sibling-parcel consolidation". (v1.2 gave a flat 5 to any
  owner of >1 county parcel; that conflated a callable adjacent cluster with a
  scattered portfolio.)

## Hold / tenure scoring (v1.3 — supersedes the v1.2 hold bucket)

Long hold is ORA's best FREE motivation proxy — mortgage-maturity mining was
ruled out as paid-data-only on 2026-09-18 (memory:
`reference_mortgage_maturity_signal_not_bulk_accessible_2026-09-18.md`), which
makes this component the one worth getting right.

**Why a curve, not buckets.** Tenure is not linear evidence. Three mechanisms
drive it, and all three saturate:

1. **Basis decay / lock-in.** Every year of straight-line depreciation lowers
   adjusted basis, so the embedded gain — and the capital-gains + §1250
   recapture bill — rises fastest early and asymptotes once the building is
   substantially depreciated. Lock-in is a *capacity* signal (the owner can
   clear ORA's price) and a *willingness* brake at the same time.
2. **Depreciation exhaustion.** Commercial real property runs a **39-year**
   straight-line recovery period. At full depreciation the tax shelter is gone
   while the recapture liability is at maximum: holding produces no further
   sheltering benefit. This is the sharpest single inflection in the whole
   curve and it is why a ~38-year hold is the practical ceiling of the signal.
3. **Owner life-cycle.** A 30-year hold on a small-bay building is strongly
   correlated with an ageing individual principal or a first-generation family
   LLC. Past ~35 years succession pressure is already near-certain — more years
   add almost no new information, and where it is confirmed the ESTATE-SIGNAL
   flag carries it, not this component.

Below ~2 years the owner is a buyer, not a seller. Between 5 and 15 years the
owner crosses from "still executing a business plan" to "holding a seasoned,
depreciated, refinanced asset" — that transition is where nearly all of the
discriminating power lives.

**The curve.** Let `y` = years held (see basis rules below):

    hold_points = 0                                            for y < 2
    hold_points = 20 x (1 - e^(-(y-2)/8)) / (1 - e^(-4.5))      for 2 <= y <= 38
    hold_points = 20                                            for y > 38

Time constant **tau = 8 years** (the shallow-bay hold/refi cycle); normalised so
the curve reaches exactly 20.0 at **y = 38**, one year inside the 39-year
depreciation life. Round to 1 decimal; carry the unrounded value for ordering
and tier on the 1-dp component total.

| y | 2 | 3 | 5 | 7 | 10 | 12 | 15 | 20 | 25 | 30 | 35 | 38+ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| pts | 0.0 | 2.4 | 6.3 | 9.4 | 12.8 | 14.4 | 16.2 | 18.1 | 19.1 | 19.6 | 19.9 | 20.0 |

Diminishing marginal signal, as intended: **5->15 yrs = +9.9 pts; 25->35 yrs =
+0.8 pts** — a ~12x difference in marginal information. This is the
quantitative answer to "why does D&A Berwick's 38-year hold score near-maximal":
it is not that 38 is a big number, it is that 38 is one year short of full
depreciation of a commercial building, so every tax and life-cycle mechanism
that makes tenure informative has already run to completion. A 45-year hold
carries no more signal — hence the cap, not an extrapolation.

**Versus the v1.2 buckets.** The curve is deliberately close to them in the
middle of the range and differs at the edges: it removes the 2-point cliff at
the 24/25-year bucket boundary, stops paying a 25-year and a 45-year hold
identically, and scores the 5-15 year band more finely. **This DOES move scores
— unlike v1.2, which changed no scored constant.** Any run using the v1.2
buckets instead must say so on the face of its summary.

**What `y` is measured from, in order:**
1. The most recent **arms-length** transfer (price >= $25K, or the county's own
   validity code where one exists and is trustworthy — Polk IA `quality`,
   Richmond/Chesterfield VA `val_code_1`, Hamilton OH `SALETYPE`; NOT Franklin
   OH `IsValid`, which reads 'F' on real deeds).
2. If the latest transfer is nominal/non-arms-length, the **prior** arms-length
   transfer — flag `HOLD-PRE-NOMINAL`. A re-titling must never reset tenure to
   zero; that is failure mode F1 and it is the single most common way a
   long-hold owner disappears from the list. Where the source publishes a
   multi-segment sale history (MD Socrata `ed4q-f8tm` carries three), walk back
   through the segments rather than giving up after one.
3. Only if no arms-length transfer is published at all: **UNKNOWN-HOLD**.

**UNKNOWN-HOLD — the 16-point default is RETIRED.** Awarding 16 silently
asserted a ~14.6-year hold on a row with no evidence of any hold, and on the
2026-09-18 Howard MD and Jackson MO runs that guess was carried by 80% and 100%
of rows respectively. Replace it with a coverage test, applied per run:

- **UNKNOWN-HOLD on <=20% of scored rows** (the Ohio pattern — a rare
  correction): score those rows' hold at **0**, flag them `HOLD-UNKNOWN`, and
  carry a **`Hold ceiling` = score + 20** column so the reader can see the
  row's range rather than a false point estimate. State plainly that these rows
  are UNDER-ranked and must not be read as short holds. Do not rescale — a
  per-row rescale would put two different scales in one list.
- **UNKNOWN-HOLD on >20% of scored rows**: the component cannot discriminate.
  Drop it list-wide, score **0-80**, and set tier cutoffs as percentages of the
  achievable maximum (the Jackson MO treatment below). Say so on the face of the
  deliverable.

Either way the rule is the same one: **flag it, never guess it.**

## Sibling-parcel consolidation (v1.3 — closes failure mode F6)

One owner holding several adjacent parcels on one old deed is ONE relationship
and ONE phone call, but v1.2 scored it as N independent rows. All three
2026-09-18 runs hit this and all three flagged it unresolved: Franklin (D&A
Berwick 2 parcels / 46,000 SF, DINOVO 3, AIRPORT PLAZA 4), Howard (RUMSEY ROAD
3 parcels / 120,060 SF on one deed liber), Jackson (DEEVIC 4 contiguous parcels
/ ~60,400 SF — "seven names collapse to roughly four conversations").

**Consolidate AFTER scoring every parcel individually. Never drop a parcel row**
— the parcel list is what someone dials from and what DD runs on. Deliver both:
a `Relationships` sheet ranked by relationship score, and the existing ranked
parcel sheet with `Relationship ID` and `Relationship Rank` columns added.

### Matching rule (apply in order; deterministic, so two runs agree)

**Normalise first.** Owner name: uppercase, strip punctuation, `&` -> `AND`,
collapse whitespace, drop leading/trailing `THE`, and strip trailing entity
suffixes (LLC, L L C, INC, LTD, LP, LLP, CORP, CO, TRUST, TR, TTEE) **for
comparison only — never for display**. Mailing address: uppercase, USPS suffix
abbreviations, unit/suite split into its own field, ZIP5.

1. **MERGE — name + address.** Same normalised owner name AND same normalised
   mail street + ZIP5. Both must match. Name alone merges unrelated common
   names; address alone merges everything behind one registered agent (F9).
2. **MERGE — deed link.** Same deed/instrument reference (liber+folio, deed
   transfer number, book/page) across parcels AND agreeing mail addresses. One
   deed is one acquisition event, so this merges even when the names differ.
   This is what recovers Howard's three Rumsey Road parcels.
3. **FLAG, never merge — `RELATIONSHIP-CANDIDATE`.** Same mail address with
   different owner names, where the parcels are also adjacent or same-street
   (Franklin's CCC COLUMBUS / BSC COLUMBUS sibling SPEs at one out-of-state
   address, same-day re-titling). Also: same deed reference but DISAGREEING mail
   addresses (Howard's nine OAKLAND RIDGE parcels on one liber /10583/00069 with
   nine different C/O parties — either one owner or a stale blanket-deed entry,
   and the run may not assert which). Human adjudication before outreach.
4. **Geographic qualifier.** Members must be in the same county screen and
   within **0.5 mi** of each other, or contiguous. A same-owner parcel across
   the county is a portfolio fact that feeds the `multi` component, not a
   relationship.

### Roll-up

- **Combined SF** = sum of members. **Do NOT re-apply the 10,000-80,000 SF gate
  to it** — the gate is per BUILDING, because ORA buys shallow-bay boxes, not
  one 120K box. Rumsey Road's 120,060 SF is a three-building portfolio purchase,
  not an out-of-box asset.
- **Relationship years-held** = the MAXIMUM member years-held (the earliest
  acquisition dates the relationship; later add-ons evidence a committed local
  owner). Report the member count at that tenure.
- **Relationship score** = max(member scores), with the `multi` component
  recomputed on member count per the graduated sub-band above. **Do not re-score
  size on combined SF** — that would penalise an assemblage for exceeding the
  single-building sweet spot, which is backwards.
- Members inherit the relationship's rank for call ordering; each keeps its own
  parcel-level score for DD.

Note the consequence, and state it in the README: **consolidation changes the
UNIT of the list, not the scores.** It is a row-count and call-planning fix, not
a score inflator. A run reporting materially higher scores after consolidating
has a bug.

### Error profile (state this in every QC sheet)

**False positives** — merging parties who are not one counterparty:
- Common LLC names (`MAIN STREET PROPERTIES LLC`). Mitigated by rule 1's
  conjunctive name+address test.
- Registered-agent, attorney or property-manager mailing addresses standing
  behind dozens of unrelated owners (F9). Mitigated: address alone never merges.
- Stale blanket-deed owner lines (the Howard OAKLAND RIDGE pattern). Mitigated
  by rule 3's disagreeing-address carve-out.
- Land-condominium units under one declarant, which may be separately sellable.
  Merge for calling, flag `LAND-CONDO`, and verify structure before pricing.
- **Name-stripped counties** (Anne Arundel and Howard MD on the state extract):
  the key degrades to address + deed only, so FP risk is materially higher.
  In those counties emit rule-1 merges as FLAGS unless the deed also matches.

**False negatives** — missing a relationship that exists:
- **Generational transfer resets the deed.** Father's LLC -> children's LLC:
  new name, new deed, sometimes new mail address, and the whole cluster reads as
  a 3-year hold. This is the most damaging miss because it destroys the long-hold
  signal precisely where succession motivation is highest. Partially mitigated by
  the `HOLD-PRE-NOMINAL` fallback (these transfers are usually nominal) — but
  only where the county publishes consideration AND a prior segment.
- Alias drift a normaliser cannot reach: `BERWICK, D & A LLC` vs
  `D & A BERWICK LLC`. Accepted miss; do not add fuzzy matching without a
  measured FP rate.
- Distinct SPEs per parcel with genuinely different addresses — invisible here,
  recoverable only from SOS principal lookups (step 8).
- Counties publishing no deed reference and no mail address (Wyandotte KS has no
  published tax-mail at all): rule 1 and 2 both fail; consolidation is
  UNAVAILABLE, say so rather than reporting zero relationships as a finding.

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
| Louisville KY | Jefferson | **UNKNOWN — never screened** | no section in `county-endpoints.md`; not among the nine ratified clusters | UNKNOWN |

Three practical consequences: **(a)** Missouri and Kansas will never have a
hold signal from public records — the >20% branch (drop the component) is their
permanent state, not a run defect. **(b)** Michigan and suburban Wisconsin need
market-specific proxies, and Michigan's is a gap magnitude rather than a date.
**(c)** Indianapolis is the highest-value gap to close — a disclosure state
whose endpoints were never written down.

### Missing-component treatments (also pinned from the 2026-09-18 runs)

Never fake a component. Drop it, rescale honestly, and state the rescale on every
row's score-breakdown cell and in the README sheet.

- **Entity-owner uncomputable (Howard MD pattern — the state layer strips owner
  names, so `estate_v2` cannot fire on a name either):** drop the 10-point component
  and rescale **raw out of 90, x 100/90**. Per `…HowardMD_Summary_v01.md`, §5 "Data
  gaps, limits, and where this run is weaker than the pilot" item 1, which
  also post-hoc recovered all 20 names and found all 20 were entities — the rescale
  was arithmetically equivalent there and did not distort the ranking.
- **Non-disclosure state (Jackson MO pattern — no published sale price or date, so
  there is no empirical calibration factor, the basis component is zero on every
  row by construction, AND no transfer date exists to derive tenure from):** drop
  BOTH the 20-point basis component and the 20-point hold component. **REVISED in
  v1.3:** the Jackson run scored 0-80 with a flat 16 UNKNOWN-HOLD on every row,
  giving an achievable maximum of 76. That flat 16 was a constant offset — it added
  no discrimination whatsoever but inflated every score by 16 points and made the
  list look better-evidenced than it was. Under the retired-default rule, 100%
  UNKNOWN-HOLD takes the >20% branch and the component is dropped list-wide:
  **score 0-60** (prod 25 + size 15 + entity 10 + absentee 5 + multi 5), achievable
  maximum **60**. Tier cutoffs stay percentages of the achievable maximum, not
  absolute points — the pilot's A>=90 / B 85 / C 70 are 90% / 85% / 70%, giving
  **A >=54.0 · B 51.0-53.9 · C 42.0-50.9 · D <42.0**. A mechanical rescale would
  make A-tier reachable only by a literally perfect score — a degenerate tier.
  Carry a *Score %* column so any other rule can be applied. Per
  `…JacksonMO_Summary_v01.md`, §6 "Divergences from the pilot" rows 2-4. Such a
  list is NOT comparable to a calibrated one — say so on the face of the
  deliverable.

### 7. Mine motivation signals (bulk extracts)
- Delinquency: tax-duplicate TotPrior/TotPenalty > 0 (or in-layer fields -
  Hamilton has DELQ_TAXES directly). Flag amount and vintage.
- Owner-level clustering: owners delinquent on ANY parcel who also own
  industrial - distress before it reaches the subject property.
- Sellers-in-motion: owners who sold industrial >=$100K within ~2 years AND
  still own - liquidation in progress; call before the next listing. Use
  grantor fields where published (Butler); otherwise infer prior owner from
  consecutive transfer records (Franklin pattern).
- Special-assessment arrears; rental-registry phone numbers; TIF flags
  (TIF distorts the value/basis math - flag, price in DD).

### 8. Verify before anyone calls
Occupant web check per finalist - Columbus found auto-use (policy-blocked
tenants) at 2 of the top 10, including the #1 scorer. Check for archived/
delisted listings (motivated seller). State SOS entity lookup for principals
(Ohio API is bot-gated - browser or manual). The score ranks capacity;
verification ranks quality. Attach a one-line pre-mortem (most likely reason
the deal fails ORA underwriting) to every presented candidate - ORA project
doctrine requires it.

### 9. Deliver
ORA-style workbooks (Oxford Navy 1B2A4A headers, Arial, zero formula errors,
run the xlsx skill's recalc.py): YYYYMMDD_[Market]-Parcel-Screen_v0N.xlsx
(ranked screen + README + QC failure-modes sheet) and, when distress data
exists, YYYYMMDD_[Market]-Motivated-Leads_v0N.xlsx. Save to the Investment
Candidates folder. Call-order doctrine: estate first, then delinquent entity
owners, then sellers-in-motion, then absentee portfolios, then long-holds.

## Engineering notes (hard-won - read before running)
- bash sandbox: 45s per call. Use scripts/dl_resume.py (resumable ranged
  downloader) for files >40MB. Unzip into a NEW subdirectory - the sandbox
  cannot overwrite or delete files written by previous calls. Stream-parse
  100MB+ files with csv.reader straight from zipfile.open().
- Parcel-ID formats differ between a county's GIS layer and its tax files
  (Franklin: '010-104049' vs '"010-104049-00"') - normalize before joining,
  verify the join produced matches (a silent 0-match join cost an hour once).
- Excel bulk files: pip install python-calamine, pandas engine="calamine"
  (10x faster than openpyxl; openpyxl times out on 250K-row files).
- Some county report servers WAF-gate downloads: send full browser headers
  (User-Agent + Accept(html) + Referer + Sec-Fetch-*) - Butler 403s without.
- Census ACS by ZCTA: the API now requires a key; key-free path is the
  table-based Summary File FTP (acsdt5y2023-bXXXXX.dat, estimate = column 1).
- GIS layers are often thin mirrors: physical fields (year built, height,
  condition) may be 0% populated - the bulk appraisal/building extract is the
  real source (Franklin Build.txt: YRBLT/WALLHGT/PHYCOND = 100% coverage).
  Conversely some counties (all 4 Cincinnati counties) publish NO commercial
  SF anywhere public - use footprint spatial joins or per-parcel scrapes.
- Owner-scrubbed GIS != owner-inaccessible: counties on Oracle APEX/ORDS CAMA
  front-ends (Henrico VA pattern - <host>/ords/<schema>/f?p=...) yield owners
  to a scripted wwv_flow.accept POST. Use scripts/apex_owner_pull.py (county
  config registry + resumable bulk + --smoke test; Henrico validated 279/279
  at ~0.85s/parcel). Probe for /ords/ before declaring a county data-hostile;
  add each validated county to the module's COUNTIES dict.
- Canonical classifiers live in scripts/: estate_v2.py (estate signals; '&'
  trailing-TRUST patch 2026-06-09), institutional_owners.py (institutional/
  ORA/never-call). Import these - never re-implement inline regex per run.

## Failure modes (carry into every QC sheet)
F1 nominal-transfer hold distortion | F2 stale auditor values (calibrate!) |
F3 physical fields empty in GIS layer | F4 class-code lag -> verify occupant |
F5 low basis != willingness (lock-in; estate/delinquency override) | F6 one
building spanning sibling parcels | F7 TIF value distortion | F8 unbranded
institutional affiliates slip the regex | F9 tax-mail = agent, not principal |
F10 the screen measures capacity, not willingness - expect 2-5% response;
volume + quarterly re-runs + signal-led call order is the strategy.

## References
- references/market-status.md - per-market progress tracker + queue. Update
  it after every market run.
- references/county-endpoints.md - verified URLs, field names, ID formats,
  quirks for every county already discovered. Append new counties here.
- references/county-endpoints.v1.json - machine-readable derived index (parcel/
  CAMA layer URL + layer id/name + MD JURSCODE only) of county-endpoints.md, for
  other skills to consume programmatically without parsing prose. county-endpoints.md
  remains the source of truth on any conflict; regenerate the JSON from it.

## Changelog
- **v1.3 (2026-09-18):** Deepened the long-hold ownership-tenure signal — chosen as
  ORA's best FREE motivation proxy after mortgage-maturity mining was ruled out as
  paid-data-only the same day (memory:
  `reference_mortgage_maturity_signal_not_bulk_accessible_2026-09-18.md`).
  **UNLIKE v1.2, THIS MOVES SCORES.** Four changes. **(1) Hold is now a graduated
  curve**, `20 x (1-e^(-(y-2)/8)) / (1-e^(-4.5))`, 0 below 2 yrs, capped at 20 from
  38 yrs — tau = 8 yrs (the shallow-bay hold/refi cycle), normalised to reach 20.0
  at 38 yrs, one year inside the **39-year commercial straight-line depreciation
  life**. That anchor is the non-hand-waving answer to why D&A Berwick's 38-year
  hold is near-maximal: basis decay, depreciation exhaustion and owner life-cycle
  have all run to completion, so a 45-year hold carries no more information.
  Marginal signal 5->15 yrs = +9.9 pts vs 25->35 yrs = +0.8 pts (~12x), and the
  2-point cliff at the old 24/25-yr bucket boundary is gone. **(2) The 16-point
  UNKNOWN-HOLD default is RETIRED** — it silently asserted a ~14.6-yr hold on rows
  with no hold evidence, and carried 80% of the Howard MD and 100% of the Jackson
  MO lists. Replaced by a coverage test: <=20% unknown -> score those rows 0, flag
  `HOLD-UNKNOWN`, carry a `Hold ceiling` (= score + 20) column, never rescale;
  >20% -> drop the component list-wide and tier on percentages of the achievable
  maximum. Jackson's treatment is revised accordingly from 0-80/achievable-76 to
  **0-60/achievable-60** (A >=54.0 · B 51.0-53.9 · C 42.0-50.9 · D <42.0) — the old
  flat 16 was a constant offset that added no discrimination but inflated every
  score. Also added: a nominal latest transfer now falls back to the PRIOR
  arms-length transfer (`HOLD-PRE-NOMINAL`) instead of going straight to unknown.
  **(3) Sibling-parcel consolidation (closes F6)**, flagged unresolved by all three
  2026-09-18 runs. Parcels are scored individually and never dropped, then grouped
  into RELATIONSHIPS by normalised owner name + normalised mail street/ZIP5, or by
  shared deed reference with agreeing addresses; same-address/different-name and
  same-deed/different-address cases are FLAGGED `RELATIONSHIP-CANDIDATE`, never
  auto-merged; members must be within 0.5 mi or contiguous. Roll-up carries combined
  SF (NOT re-gated against the 10-80K per-building gate), max member tenure, and
  member count. The `multi` component is regraded 0/2/3/4/5 on relationship
  membership rather than a flat 5 for any multi-parcel county owner. Documented FP
  risks (common LLC names, agent mailing addresses, stale blanket deeds, land
  condos, name-stripped MD counties) and FN risks (generational deed resets — the
  most damaging — alias drift, per-parcel SPEs, counties publishing neither deed nor
  mail address). **Consolidation changes the UNIT of the list, not the scores; a run
  reporting higher scores after consolidating has a bug.** **(4) New
  hold-data-availability table by ORA market** — Ohio's rich transfer history does
  not generalise and neither does Missouri's total absence. Verified absent: Warren
  OH, Jackson/Clay MO, Wyandotte KS, Hanover VA, suburban Dane WI. Date-free proxy
  only: Kent MI (Proposal-A `TaxableValue`/`SEVValue` uncapping gap — a magnitude,
  not a date). Year-granularity only: Dallas IA. Unknown/never established: Platte
  MO, Johnson KS, Jefferson KY (Louisville was never screened). Best in class: Polk
  IA. **Indianapolis is the highest-value open gap** — a disclosure state whose v01
  run clearly reached transfer dates, but `county-endpoints.md` carries no
  Indianapolis section at all; re-derive before relying on it.
  **MARYLAND HOLD GAP CLOSED — it was a run defect, not a data gap.** The Howard run
  reported 16 of 20 rows UNKNOWN-HOLD and concluded the statewide layer "publishes no
  transfer date at all", routing the fix to deed-by-deed mdlandrec work. Re-queried
  live: `TRADATE` is populated on **708 of 786** Howard `LU='I'` parcels (90.1%) and
  **255 of 279** in the 10-80K SF band (91.4%), with `CONSIDR1`, `CONVEY1` and
  `DR1LIBER`/`DR1FOLIO` alongside; a 40-row sample returned 38. The trap is that
  `SDATDATE`/`MDPVDATE` are extract VINTAGE stamps and `LASTASSD` is the assessment
  cycle — none is the transfer date — and that MD `LU` is alphabetic, so an
  Ohio-reflex `LU LIKE '4%'` filter returns zero rows silently. The field was already
  documented in the Anne Arundel entry ("same field set"). `county-endpoints.md` now
  carries the MD hold recipe (arms-length gate on `CONVEY1`, walk back through the
  Socrata `ed4q-f8tm` three sale segments + grantor names when segment 1 is nominal),
  the better Harford (`TRANS_DATE`, 100%) and Anne Arundel (`ASST_TRANSFER_DATE`,
  95.4%) county layers, statewide population by jurisdiction, and a
  do-not-re-investigate note that mdlandrec (registration-gated, manual, no API) and
  free bulk transfer/recordation-tax rolls (nonexistent) are both moot.
  **Franklin re-score (175 rows, on-disk v02 data, no county re-query):** mean delta
  **-4.1** (106 down / 46 up / 23 unchanged); tiers A 38->28, B 32->23, C 79->71,
  D 26->53, 59 rows change tier. **The movement is almost entirely the retired
  UNKNOWN-HOLD default, not the curve** — 34 rows (19.4%) lose 16 points; the curve
  alone moves rows by <=3. **D&A Berwick behaves exactly as designed: both parcels
  hold 100.0 and rise to ranks 1-2 (from 1 and 3), consolidating into ONE
  relationship — 2 parcels, 46,000 SF, 38 yrs.** 13 clusters cover 33 rows, so the
  list collapses from 175 parcel rows to **155 conversations**. The largest
  relationship found is AIRPORT PLAZA LTD at **4 parcels / 119,640 SF**, previously
  scattered across two sheets. `BERWICK CENTRE DEVELOPMENT CO` was correctly NOT
  merged with D&A Berwick (different mail address) — the conjunctive rule working.
  Top-5 reshuffle: Modern Builders 4->3, BSC Columbus 10->5, Airport Plaza 2->4 and
  FRG-X-DMD-OH 5->7 (both lose `multi` points as single-parcel members of their
  clusters). **Watch item: Franklin sits at 19.4% UNKNOWN-HOLD, one row short of
  flipping to the >20% drop-the-component branch** — a genuinely fragile boundary on
  this data set; re-check it every run rather than assuming the branch. Expected
  qualitatively if the other two are re-run, NOT re-run live here: **Howard MD**
  changes most — 16 UNKNOWN-HOLD rows become real tenures off `TRADATE`, the run
  leaves the >20% branch entirely and returns to a full 0-100 scale, Rumsey Road's
  three parcels (120,060 SF, one liber) merge into one relationship, and the
  long-hold rows the summary could only infer from deed vintage (Standard Court
  /05290, Rumsey /06228) should score their way up rather than needing a manual
  call-order override. **Jackson MO** changes least in ranking and most in
  presentation: no transfer date exists at any price, so it stays on the dropped-hold
  branch, but the scale becomes 0-60 with tiers on the achievable maximum, and
  Deevic's four contiguous parcels plus Monopoly's adjacent holding collapse the
  seven-name list to roughly four conversations as its own summary predicted.
- **v1.2 (2026-09-18):** Findings from three same-day adjacent-parcel ring screens
  (Franklin OH pilot, Howard MD, Jackson MO). **No scored constant changed** — the
  component weights, basis bands, UNKNOWN-HOLD 16, SF gate, value band and tier
  cutoffs are all as previously ratified; this pins the previously-unpublished
  SUB-BANDS within each component so runs are reproducible, and documents the two
  missing-component rescales those runs had to invent (Howard: entity-owner
  uncomputable → 0-90 ×100/90; Jackson: non-disclosure state → basis dropped, 0-80
  scale, tiers as percentages of the achievable 76). Sub-bands were pinned FROM the
  Franklin pilot run and are Gabriel's to amend; divergent runs must say so.
  **Counterparty floor is now FAIL-LOUD.** The guard file
  `data/pipeline-guard.local.json` is untracked/gitignored and exists in exactly one
  place (`~/.claude/skills/county-parcel-screen/data/`), so every consumer's old
  `__file__`-relative path resolved to nothing when the skill ran from the repo
  checkout or the AppData plugin bundle — and degraded to an ORA-self-only floor with
  a warning nobody acted on. The Jackson MO run shipped a call list screened that way;
  the Howard run loaded the file explicitly and recorded the near-miss.
  `institutional_owners.py` and `test-pipeline-match.mjs` now load the CANONICAL
  ABSOLUTE PATH (`ORA_PIPELINE_GUARD` overrides) and raise / exit-1 rather than
  degrade; `parcel-screen-fanout.js` receives the floor from its caller and now THROWS
  when it is absent — or when it is the old ORA-self pair — instead of warning. The
  guard is validated on BOTH `never_call_names` and `never_call_patterns` in
  `institutional_owners.py` (the two are different lists screened on different paths;
  the `.mjs` and the workflow screen on names only, and validate that). Every
  deliverable must record the guard's path, UTC mtime and both counts
  (`guard_evidence()`).
  `test-pipeline-match.mjs` gains a regression that fails if the removed ORA-self
  fallback returns, and no longer passes by skipping its deal cases when the guard is
  missing — the state in which the floor is actually broken. Two endpoint corrections in
  `county-endpoints.md`: Franklin `IsValid` is NOT usable as an arms-length gate (reads
  'F' on real deeds — use the $25K nominal rule), and Jackson's geometry layer
  (`ParcelsAscendRelate/FeatureServer/1`) can return 999 rows on a 1,000-row page while
  still setting `exceededTransferLimit=true`, so page on the flag, not the row count
  (a short-page loop silently truncated 2,999 of 4,666). The Jackson paging quirk is
  mirrored into `county-endpoints.v1.json`; the Franklin `IsValid` correction is not,
  because that derived index carries no deed/transfer fields. Still open, unchanged:
  the replacement-cost benchmark conflict (SKILL.md ~$150/SF vs ora-am-brief
  ~$85-120/SF vs RCT v03 KC LOW $227.90) and the F8 institutional aliases.
- **v1.1 (2026-07-19):** Added references/county-endpoints.v1.json (schema_version
  1.0) - live-verified (real `?f=json` requests, not re-cited from memory) against
  all 22 counties already documented in county-endpoints.md. 19 VERIFIED, 2
  VERIFIED-PARTIAL (Clay MO, Platte MO - geometry live but attribute-thin, matches
  existing doc), 2 NOT-FOUND (Johnson KS paid-gate, Polk IA has no ArcGIS REST
  parcel layer - CSV export only). Caught and corrected two live drifts since the
  2026-06-09/11 source-doc runs: Dane County WI's statewide parcel service was
  renamed (`Wisconsin_Statewide_Parcels` -> `Wisconsin_Statewide_Parcels_DB`, layer
  rolled to the 2026 vintage) - fixed in county-endpoints.md same pass; Kent County
  MI's primary Hosted/ParcelsWithCondos layer now requires a token (was public
  2026-06-09) - registry points to the still-public OpenData mirror instead, flagged
  for periodic re-check. Also resolved two URLs county-endpoints.md had left
  truncated: Baltimore County MD's own polygon+owner-name GIS layer, and Richmond
  City VA's parcel layer (`services1.arcgis.com`, not bare `services.arcgis.com`,
  which 400s). Built to satisfy ora-flood-zoning-dd v1.2's Step 1 cross-link
  (parcel-geometry lookup for the pad/yard flood split).
- **v1.0:** initial - validated Franklin (Columbus) + Hamilton/Butler/Clermont/
  Warren (Cincinnati), June 2026.
