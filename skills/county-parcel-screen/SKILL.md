---
name: county-parcel-screen
description: >
  Use when the user mentions: parcel screen, county screen, ring screen,
  off-market sourcing, owner outreach list, cold call list, delinquent tax
  leads, motivated sellers, estate owners, long-hold owners, assessor or auditor
  parcel data, or off-market industrial candidates in ANY target market or new
  county. Also "next market", "run the screen on X", or owner-level lead lists
  from public property records. Recorded-sales tracking routes to
  county-sales-monitor; a single already-identified target routes to
  verified-deal-recon (deal-recon agent for a first look only); an inbound
  broker batch routes to deal-flow-triage.
---

# county-parcel-screen (v1.4)

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

Override only via the `ORA_PIPELINE_GUARD` env var. The file is UNTRACKED and
gitignored on purpose — counterparty names never live in tracked files — so it exists
in exactly ONE place on this machine: NOT in the `ora-skills` repo checkout and NOT in
the AppData plugin bundle. A path relative to the executing skill copy therefore
resolves to nothing. **Read references/run-history.md (Counterparty floor) before
changing how the guard is loaded.**

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

The sub-bands below were pinned 2026-09-18 FROM the Franklin OH pilot run, not derived
from first principles, and are Gabriel's to amend. **Any run that diverges from them
MUST say so on the face of its summary and workbook README, with the reason** —
otherwise successive runs stop being comparable. **Read references/run-history.md
(Scoring sub-bands provenance) before amending any sub-band.**

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

Long hold is ORA's best FREE motivation proxy (mortgage-maturity mining is
paid-data-only). **Read references/scoring-rationale.md (Why a curve, not buckets)
before amending the hold curve or any of its constants.**

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

**Versus the v1.2 buckets: this DOES move scores** — unlike v1.2, which changed no
scored constant. Any run using the v1.2 buckets instead must say so on the face of
its summary. Marginal-signal figures and the D&A Berwick worked example:
references/scoring-rationale.md.

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
and ONE phone call; v1.2 scored it as N independent rows (all three 2026-09-18
runs hit this — references/run-history.md).

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

**Read references/scoring-rationale.md (Sibling-consolidation error profile) before
writing the QC sheet.** Every QC sheet must state the false-positive classes (common
LLC names, agent/attorney/PM mailing addresses, stale blanket deeds, land condos,
name-stripped MD counties — where rule-1 merges are emitted as FLAGS unless the deed
also matches) and the false-negative classes (generational deed resets — the most
damaging — alias drift, per-parcel SPEs, counties publishing neither deed nor mail
address, where consolidation is UNAVAILABLE and must be reported as such).

## Hold-data availability by ORA market

**Read references/hold-data-availability.md before promising a hold-scored list in any
market**, and state the row's verdict (VERIFIED / DOCUMENTED / UNKNOWN) on the face of
the deliverable. Missouri and Kansas never have a public hold signal — the >20%
drop-the-component branch is their permanent state; Michigan and suburban Wisconsin
need market-specific proxies; Indianapolis is the highest-value undocumented gap.

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
- Foreclosure and tax-lien feeds (Franklin OH, Maryland, Jackson MO; added v1.4): read
  references/distress-feeds.md first. Per-host access verdicts, join keys, calendars and proof-pull results
  live there. Many feeds are MANUAL-ONLY or BLOCKED - honor that; never script around a robots.txt or terms bar.
  Feed rows are lead inputs joined to the screen, not score inputs.

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

## Engineering notes

**Read references/engineering-notes.md before running any pull** — sandbox limits,
resumable downloads, parcel-ID normalisation, bulk-file parsing, WAF headers, Census
key-free path, thin GIS mirrors, APEX/ORDS owner recovery. Canonical classifiers live
in scripts/: `estate_v2.py` and `institutional_owners.py` — import these, never
re-implement inline regex per run.

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
- references/hold-data-availability.md - per-market hold-signal verdicts.
- references/distress-feeds.md - foreclosure and tax-lien sources by market (Franklin OH, Maryland, Jackson MO):
  access verdicts, join keys, calendars, standing manual routines. Step 7.
- references/scoring-rationale.md - hold-curve rationale + sibling-consolidation
  error profile (required in every QC sheet).
- references/run-history.md - incident narratives behind the fail-loud floor,
  the pinned sub-bands and the consolidation rule.
- references/engineering-notes.md - sandbox / parsing / endpoint gotchas.
- versions/CHANGELOG-v1.0-v1.3.md - full changelog text.

## Changelog
- **v1.4 (2026-10-02):** Added references/distress-feeds.md (foreclosure and tax-lien sources for Franklin OH, Maryland, Jackson MO) and a step 7 pointer; county-endpoints.md: Jackson DLT cancellation/petition source, Wyandotte count refresh, Maryland `CONVEY1=4` decoded, recording-lag re-check flagged. Docs only. No scored constant changed.
- **v1.3 (2026-09-18):** Hold/tenure scoring becomes a graduated curve (tau 8 yrs, cap 20 at 38 yrs); 16-point UNKNOWN-HOLD default RETIRED (coverage test, `HOLD-UNKNOWN` / `Hold ceiling`, >20% drops the component); `HOLD-PRE-NOMINAL` fallback; sibling-parcel consolidation closes F6 (`Relationships` sheet, graduated `multi`); hold-data-availability table by market; Maryland hold gap closed (`TRADATE`); Franklin re-scored (mean delta -4.1). **MOVES SCORES.** Full text: versions/CHANGELOG-v1.0-v1.3.md
- **v1.2 (2026-09-18):** Sub-bands pinned from the Franklin OH pilot; Howard MD / Jackson MO missing-component rescales documented; counterparty floor made FAIL-LOUD on the canonical absolute guard path; Franklin `IsValid` and Jackson paging corrections in `county-endpoints.md`. No scored constant changed. Full text: versions/CHANGELOG-v1.0-v1.3.md
- **v1.1 (2026-07-19):** Added references/county-endpoints.v1.json, live-verified against all 22 documented counties; Dane WI rename and Kent MI token-gate drifts fixed. Full text: versions/CHANGELOG-v1.0-v1.3.md
- **v1.0 (2026-06):** initial — validated Franklin (Columbus) + Hamilton/Butler/Clermont/Warren (Cincinnati). Full text: versions/CHANGELOG-v1.0-v1.3.md
