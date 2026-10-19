---
name: ora-deal-sourcing-scan
description: Weekly on-market deal-sourcing scan (Tuesdays) — searches new industrial/flex listings across ORA's ten target markets, applies the basis/physical hard floors as a GATE, scores survivors, dedupes against the Notion Deal Sourcing Log, mechanically detects price cuts off the stored first-sighting ask, and emails a ranked digest. Restored 2026-07-07 — no replacement task applies the scoring rubric or writes to the Deal Sourcing Log. [MODEL: claude-opus-5 observed | checked 2026-08-12 via live-run transcript canary]
---

ORA ON-MARKET DEAL-SOURCING SCAN — weekly run (v2.8, 2026-09-23).

v2.8 — COVERAGE-GAP CLOSURE (2026-09-23, Gabriel-directed). NO SCORE, WEIGHT, GATE,
THRESHOLD, FLOOR OR GOVERNOR CHANGED — this version changes run ORDER, SOURCE COVERAGE and
REPORTING only. The 2026-09-23 run named six coverage gaps; root cause for four of them was
the same: mandatory steps sat at the END of a long run (tracker fetch, roster refresh,
construction photos, provisional verification) and were dropped when budget ran out, while
the source ladder was executed text-only by scouts that had no browser. Fixes:
  1. NEW STEP 0 PRE-FLIGHT runs BEFORE any scouting: Pipeline Tracker fetch + capacity
     gate, Property Register roster-drift refresh, provisional carry-forward load,
     Montgomery-cadence decision. These can no longer be starved by a long Step 1.
  2. NEW STEP 1B BROWSER PASS, run by the ORCHESTRATOR (not scouts — the browser pane is
     one shared surface), sequential and paced: Crexi public marketplace, LoopNet public
     search, the JS-rendered broker-direct pages, provisional-listing detail resolution —
     under HARD page-load caps and compact-JSON extraction. A per-market SOURCE COVERAGE
     CONTRACT (Step 1) says which source families each market must touch; KC now REQUIRES
     Block & Co and Newmark Zimmer direct. Crexi's public search was MEASURED loadable in
     the logged-out pane on 2026-09-23 (the working URL form is recorded in 1B-A).
  3. CONSTRUCTION: new STEP 3C (after tiers) photo-checks every T1 PURSUE /
     T1-PENDING-PRICE row in-run; T2 UNKNOWN rows are HANDED OFF to
     `ora-sourcing-construction-verify` (created 2026-09-23 for exactly this; it waits for
     this scan's DONE-MARKER so the two never drive the browser pane at once). A handoff is
     a RECEIPT, not a coverage gap. A skipped or unattributable T1 check is still a gap.
     Existing T1/T2 rows with a blank Construction Type are set to 'Unknown — CONFIRM'
     when touched, so they enter the backstop queue.
  4. PROVISIONAL LISTINGS: must get a detail-page resolution attempt in Step 1B. Addressed
     + still unresolved → LOGGED as PROVISIONAL (T2 max), never silently dropped.
     Unaddressed → carried forward in a state file and retried for 3 runs.
  5. LISTING-DATE BASIS captured per listing (listed / days-on-market / updated-only /
     ORA-first-sighted). An "updated" date alone is never evidence of a new listing or a
     re-list. Step 4 carries the re-list-vs-refresh decision rule.
  6. DIGEST §7 SPLIT into 7a RUN RECEIPTS (every mandatory step: DONE / HANDED-OFF /
     FAILED + reason), 7b SOURCE COVERAGE MATRIX, 7c TRUE COVERAGE GAPS, 7d FILTERED BY
     DESIGN (Madison nil, Montgomery cadence, sub-scale). Scope-by-design items no longer
     masquerade as gaps, and real gaps can no longer hide among them.

v2.7 — LISTING-AGENT CAPTURE + BROKER RELATION LINKING (2026-09-19, Gabriel-directed).
NO SCORE, WEIGHT, GATE, THRESHOLD OR GOVERNOR CHANGED — this version only adds data
capture. Driven by the 2026-09-19 broker-coverage analysis: of 545 Deal Sourcing Log
rows, only 310 (56.9%) carry a usable broker NAME; the rest name an aggregator (Crexi,
CommercialSearch, Revere) or a placeholder, and the `Broker (Linked)` relation is
essentially empty (the Broker Relationships DB holds 9 rows). ORA therefore cannot see
which brokers are actually active in its markets. Fixed at the source: STEP 1 now
requires the listing AGENT off the listing DETAIL page, STEP 5 writes `Broker / Contact`
as "Name, Firm" AND links `Broker (Linked)` to a Broker Relationships row (creating a
minimal row when none exists, capped at 25/run), and STEP 6 reports a "Broker capture"
section. Match key is NAME + FIRM, not email — see the executability findings in STEP 1.
*** PROVENANCE NOTE FOR WHOEVER COMMITS THIS FILE: v2.7 was layered on TOP of the
UNCOMMITTED v2.6 own-portfolio-guard change in the shared ~/.claude checkout, on branch
`feat/model-canary-probe-step25`. The working tree therefore carries TWO separate
uncommitted changes (v2.6 and v2.7) by two different sessions. Commit accordingly. ***

v2.6 — OWN-PORTFOLIO GUARD (2026-09-18, Gabriel-directed). STEP 2 gains criterion (e),
run first: every candidate goes through _shared\own_portfolio_guard.py (range-aware
match against _shared\ora-own-portfolio-exclusions.json). Closes the 2026-09-05 defect
where ORA's own Cushman-listed 2000-2026 Zettler complex was logged T1 PURSUE. Own assets
seen on market now go to a digest section, never to Notion as leads. STEP 4 reports
legacy own-asset rows for retirement. No scoring weight changed.

v2.5 — LOUISVILLE KY LEG ADDED; THE SCAN IS NOW TEN MARKETS, NOT NINE (2026-08-11,
coverage fix + mirror sync, no scoring weight changed). Louisville was ratified as the
10th canonical cluster by Gabriel on 2026-08-05 (target-markets.json v1.7, now v1.8) and
was added to the Notion Acquisition Pipeline Tracker's Market select the same day — but
NOTHING EVER ADDED IT TO THIS SCAN. It was a live, ratified target market with no
scanning leg for six days, and the 2026-08-11 run covered nine markets while the firm's
own canon said ten. That is the defect this version closes. Louisville is ENTRY-PHASE,
so it scores Market 14/20, not 20 — and per Ruling 3 entry clusters earn NO satellite
eligibility until ORA's first closed deal validates the cluster. Also added: the
Louisville RCT row to the Step 3A mirrored table, and Louisville brokerages to Step 1
(incl. KCREA / kcrea.com, a Kentucky-specific listing platform none of the other nine
markets has — worth trying alongside the Yardi network).

v2.5 LOUISVILLE DENOMINATOR — RESOLVED, AND NOT BY A PROXY. An earlier draft of this
version carried an OPEN CONFLICT note here, because `acquisition-underwriting` had just
been given a [PROXY: Columbus] figure while `target-markets.json` v1.8 carried a
[PROXY: Indianapolis] one. BOTH WERE WRONG. Louisville is in the C&W 2025 guide, and the
extract has been in THIS TASK'S OWN FOLDER all along:
  skills/cw-2025-construction-costs.json  (45 markets, small25/med25/large25 per market)
Louisville small25 = $135.28 -> LOW $237.07 -> clears at $82.97/SF (<=1995), $94.83 (>=2005).
That sourced row is now in acquisition-underwriting and is mirrored above; the [PROXY] tag
is GONE and Louisville does NOT carry DENOMINATOR-SENSITIVE.
CHECK THAT FILE FIRST for any per-market hard cost — it is faster and better-sourced than
any proxy, and the C&W flipbook itself is canvas-rendered with no text layer, so scraping
it fails. CLOSED 2026-08-12 (Gabriel): `target-markets.json`'s Louisville `replacement_cost` block —
which carried hard $143.46 (Indianapolis proxy) and the false claim "Louisville is NOT in the
C&W guide" — was DELETED. Louisville is the only cluster with no replacement_cost block, by
decision. The other nine clusters KEEP theirs (Gabriel, 2026-08-12): their numbers are correct
and match the C&W hard costs behind RCT v03, and the blocks carry provenance that exists
nowhere else (2024 comparatives, YoY %, land $/acre, small-bay extrapolations). They are
RETAINED AS PROVENANCE, NOT AS A DENOMINATOR. Never read a denominator from
target-markets.json — its operative benchmark was RETIRED 2026-07-14; RCT v03 in
`acquisition-underwriting` is the only one.

v2.4 — CONSTRUCTION TYPE IS NOW DETERMINABLE (2026-08-04, procedural fix, no scoring
weight or governor changed): the Step 1 instruction to settle construction type by
looking at listing photos was UNEXECUTABLE as written — WebFetch returns text only, so
on the 2026-08-04 run all nine market agents returned UNKNOWN for every candidate.
Because UNKNOWN scores identically to PEMB (2/5), that silently suppressed ~3 points
across essentially the entire scan. Step 1 now carries a working browser-pane procedure
(resize viewport FIRST — a fresh pane is 0x0 and renders nothing, which is what past
runs misread as "screenshot failed"; then extract `.property-details-gallery` image
URLs, download at ?width=1400, and Read them). It also documents the two traps that
produce a CONFIDENTLY WRONG answer: the `.similarproperty` carousel serves OTHER
buildings' photos (on 4111 Founders Blvd, every image on the page was another
property's), and the image CDN keys on the GUID so reconstructed URLs silently return
a duplicate image. Validated same-day: 7267 Park Cir Dr confirmed precast, 3717 Jonlen
Dr confirmed block; both Notion rows corrected 2/5 -> 5/5. Coverage is partial by
nature — some listings genuinely have an empty gallery, and a verified "no photos
exist" is a legitimate UNKNOWN. NOTE the by-product that outweighed the 3 points: the
Jonlen interior photos exposed a taproom/arcade build-out that Step 2.5 zero-credits.

v2.3 — BASIS DENOMINATOR RECONCILED TO RCT v03 (Gabriel, 2026-07-14, governor-level):
This scan had been running its own basis benchmark. It no longer does. THE FIRM HAS
ONE DENOMINATOR: **RCT v03**, in `acquisition-underwriting`. Rebuilt from the C&W 2025
guide (all-in, shallow-bay); the vintage ramp was recalibrated 30/25 -> 65/60 because
the floor % and the denominator are a matched pair. Basis now includes the 2% closing
cost doctrine requires. RETIRED, do not reintroduce: the C&W-hard "operative benchmark"
(ratified and retired the same day), the old $140/$170/$150/$130 constants, and RCT v02.
See Step 3A. NOTE: `acquisition-underwriting` states its Buy Box & Scorecard v1.1
"supersedes ... the scan Fit Score" — the Fit Score below is a LIGHT TRIAGE screen for
on-market volume, NOT a competing scorecard. Anything it advances gets re-scored under
v1.1. Keep the two distinct and never present a Fit Score as an underwriting verdict.

v2.2 — CONSTRUCTION & ENVELOPE FACTOR (Gabriel, 2026-07-14):
ORA prefers masonry / brick / block / tilt-up over metal. This was ALREADY ratified
doctrine in the acquisition-underwriting skill ("block/tilt-up/brick full credit;
PEMB ~= half, never kills") — the sourcing scan had simply never inherited it. Now a
5-point score component (Step 3B), funded by reweighting Basis 20 -> 15 (basis is a
GATE now, so 20 score points double-counted it). Construction type is captured in
Step 1. NEVER a disqualifier. See also the METAL-BUILDING BASIS DISTORTION warning in
Step 3A — this is not merely a taste preference; the ratified replacement-cost
benchmark is tilt-up product, so it systematically FLATTERS metal buildings' basis.

v2.1 — BASIS BENCHMARK RATIFIED (Gabriel, 2026-07-14, governor-level):
The basis hard floor now tests against Cushman & Wakefield 2025 SMALL-TIER HARD COST,
per metro, read live from target-markets.json v1.4. The old $140/$170/$150/$130
figures were never sourced; the Maryland one was 27% too high. Per-metro floors are
tabulated in Step 3A. An "all-in" (hard+soft+land) denominator was considered and
REJECTED — it would pass essentially every Class B/C deal, and a floor that passes
everything is not a floor.

v2.0 CHANGES (all driven by defects found in the 2026-07-14 run):
1. GATE BEFORE SCORE (Step 3A). The basis hard floor now DECIDES the tier; the score
   only ranks within a gate outcome. The old score-first design produced 29 Tier-1s
   out of 43 candidates because FAIL-BASIS deals were still scoring 62-78 into the
   pursue band. The score is not the gate. The floor is the gate.
2. UNPRICED DEALS ARE THEIR OWN BUCKET (T1-PENDING-PRICE), counted separately — 13 of
   the old 29 "Tier 1" deals had no published ask, so the basis test had never run.
3. FUNCTIONAL SF NORMALIZATION (Step 2.5) before any $/SF is computed — a 4-story
   1895 warehouse was showing a $17.76/SF headline basis against a true ~$71/SF.
4. MECHANICAL PRICE-CUT DETECTION (Step 4) off three new Notion fields; 144 rows
   backfilled 2026-07-14. Previously the log stored no prior ask, so cuts were
   structurally undetectable and "no cuts" was being reported as a finding.
5. BENCHMARK HONESTY — replacement-cost figures are PROVISIONAL/UNRATIFIED and
   likely TOO LOW; every digest must say which was used and flag deals near the line.
6. PROVISIONAL (index-only) listings cannot reach T1 until a detail page confirms them.
7. Montgomery County MD downgraded to monthly; capacity gate corrected (E. Fulton
   terminated — no Columbus deal under contract).

(v1.0 was restored 2026-07-07 after the CC/MCP registry was destroyed by a 2026-07-05
app reinstall; recovered from the 2026-06-22 fleet snapshot.)

ROLE & PURPOSE
Run the weekly on-market sourcing scan for Oxford Realty Advisors (ORA), a private
buyer of Class B/C shallow-bay industrial/flex. Each run finds newly listed (or
re-listed / price-cut) properties in ORA's ten target markets, screens them against
the buy-box, scores survivors, writes them to the Notion Deal Sourcing Log, and emails
a ranked digest. This task covers the ON-MARKET channel; the
off-market distress channel is owned by ora-distress-signal-monitor — do not
duplicate its WARN/tax-sale/bankruptcy work.

CANONICAL INPUTS
- Target markets: the single source of truth is the canonical target-markets.json.
  Read it each run from EITHER of these (first that loads wins):
    1) C:\Users\Owner\ora-skills\target-markets.json  (authoritative — the canonical ora-skills git repo; repointed 2026-07-09 when the third clone at Claude_Workspace\01_Workspace\.claude\skills\ was archived per THIRD_CLONE=RECONCILE-COMMITS)
    2) skills/target-markets.json  (local mirror in this task folder — materialized 2026-07-09; refresh it whenever the canonical file changes)
  The file carries the ten clusters with submarkets, demand drivers, and market
  metrics (incl. sale $/SF benchmarks usable for the basis-vs-replacement score).
  ONLY IF BOTH are unreachable, fall back to the embedded list below and flag
  staleness in the email. TEN clusters: Columbus OH, Cincinnati OH, Kansas City
  MO/KS, Indianapolis IN, Madison WI, Maryland Baltimore/DC (established) +
  entry-phase Grand Rapids MI, Richmond VA, Des Moines IA, LOUISVILLE KY.
  (Louisville ratified as the 10th canonical cluster by Gabriel 2026-08-05 in
  target-markets.json v1.7/v1.8; the scan only began covering it 2026-08-11 —
  it was a live cluster with no scanning leg for six days. Entry-phase, so
  Market scores 14/20, not 20.)
- Scoring methodology: restated in full below so this prompt is self-contained.
  CITATION CORRECTED 2026-07-14 — this task previously cited
  "20260517_ORA_Investment-Candidates-Ranking_v01.xlsx (Methodology sheet)". THAT FILE
  AND THAT SHEET DO NOT EXIST. The live workbook is
  `OneDrive/Business/Investment Candidates -- 2026/20260609_ORA_Investment-Candidates-Ranking_v05a-VintageVerified.xlsx` (path updated 2026-07-17 — `Investment Candidates -- 2026\` moved under `Business\` per the OneDrive Business/Personal split)
  and its doctrine lives on the "Assumptions & Sources" sheet.
  ⚠️ AND IT IS A DIFFERENT RUBRIC. The workbook (and the acquisition-underwriting
  skill) run "Buy Box & Scorecard v1.1": Basis 25 + Yield 20 + Product & Physical 20 +
  Market 12 + Seller 10 + Tenancy 7 + Value-Add 6-13. The Fit Score below is a
  SEPARATE, LIGHTER screening rubric for on-market triage — it is NOT the same
  100-pt system and should not be described as mirroring it. Deal advancing past this
  scan gets re-scored under v1.1 by acquisition-underwriting. Keep them distinct.

ORA BUY-BOX (screening filter — apply unchanged)
- Product: Class B/C industrial, shallow-bay, flex, office-warehouse ONLY.
- Size: ~10,000-80,000 SF building; deal size $1M-$10M (sweet spot $1.5-6M).
- Capital sleeve: $0.75-5.0M equity at 65% LTV; all-cash close + post-close refi.
- Hard floors (independent): >=25% discount to replacement cost (basis-buyer
  doctrine — basis beats cap rate) AND >8% stabilized yield-on-cost.
- Value-add preferred over stabilized "almost always" (below-market rents, vacancy,
  short WALT, mismanagement are POSITIVES, not negatives).
- Physical floors: >=200A power, >=2 stalls/1,000 SF parking, functional clear height.
- Mezzanine/2nd-floor SF on slab = 0% credit unless independently functional.
- Instant disqualifiers: retail-only; office-only; multifamily; auto-use tenancy;
  ground lease <30 yr; environmental remediation >20% of price; outside the ten
  clusters; institutional Class A pricing (>$130/SF without exceptional justification).
- CAPACITY NOTE (re-verify current deal status EVERY run before applying): IF a
  Columbus acquisition is under contract, bandwidth favors the $1.5-6M sleeve over
  $7M+ checks — score large deals normally but mark them "CAPACITY-GATED" in the
  digest. STATUS AS OF 2026-07-14: NOT ACTIVE. The E. Fulton acquisition was
  TERMINATED (now a lender-note/foreclosure track), so no Columbus deal is under
  contract and NO candidate should be marked CAPACITY-GATED. Do not apply this gate
  on the strength of this note alone — check the Acquisition Pipeline Tracker
  (bcfe4a03) each run and say in the digest which way you found it. (v2.8: that check
  now happens in STEP 0, before scouting — never at the end of the run.)

RUN ORDER & BUDGET (v2.8 — the order IS the fix; do not re-sequence)
  STEP 0 pre-flight → STEP 1 text scouts (parallel) → STEP 1B browser pass (orchestrator,
  sequential) → STEP 2 / 2.5 / 3A / 3B gate + score → STEP 3C construction photos for
  T1-bound rows → STEP 4 dedupe → STEP 5 / 5A / 5B Notion writes → handoff list for
  ora-sourcing-construction-verify → STEP 6 digest → DONE-MARKER (last action).
  BUDGET — HARD CAPS, NOT JUDGMENT (the 2026-09-23 run died on "if running long"):
    STEP 1B-A discovery: ≤ 30 page loads TOTAL across all ten markets (≈1 Crexi + ≤2
      broker-direct per market; LoopNet only for markets where Crexi was blocked or
      returned 0). STEP 1B-B provisional resolution: ≤ 12 loads. STEP 3C: ≤ 4 loads per
      T1 row. Count loads; stop the sub-step at its cap and name what was not loaded.
    EXTRACTION DISCIPLINE: read pages with `javascript_tool` returning COMPACT JSON (address,
      price, SF, DOM/listed date, href — nothing else), or `get_page_text` with
      max_chars ≤ 6000. Never pull a full accessibility tree or full page text into
      context — raw page dumps are what exhaust the run.
    CHECKPOINT: STEP 0 must be complete before 1B-A starts, and the Step 1 text-scout
      candidate list must already be recorded in the run notes, so a 1B overrun can cost
      only 1B's own breadth — never the gate, dedupe or Notion writes.
  If a mandatory step nevertheless fails, it is a FAILED receipt with its reason — the
  digest never omits it and never re-labels it a "scope choice".
  MANDATORY STEP ROSTER (each gets a receipt line in digest §7a, every run):
    R1 Pipeline Tracker fetch + capacity gate · R2 Property Register roster refresh ·
    R3 provisional carry-forward load · R4 text scouts, all ten clusters ·
    R5 browser pass (Crexi · LoopNet · JS broker-direct) · R6 provisional detail
    resolution · R7 construction — T1 in-run · R8 construction — handoff list ·
    R9 full-set dedupe · R10 Notion writes · R11 Step 5B tracker cross-writes ·
    R12 own-portfolio guard · R13 carry-forward file written · R14 done-marker written.
  DONE-MARKER (R14, the run's LAST action, after the digest send attempt): write
    C:\Users\Owner\OneDrive - Oxford Capital Partners\Claude_Workspace\_state\deal-sourcing-scan-done.json
    = {"run_date":"YYYY-MM-DD","completed_at":"<ISO>","handoff_rows":N}. The follow-on
    ora-sourcing-construction-verify reads it and does NOT start until it shows today's
    date — that is what stops it driving the browser pane while this scan still is.

STEP 0 — PRE-FLIGHT (v2.8 — runs FIRST, before any scout is dispatched)
Compute the run date once (`date '+%A %Y-%m-%d'`) and the day-of-month.
  0a. ACQUISITION PIPELINE TRACKER — query collection://bcfe4a03-7e61-4ac1-a0bb-c44174fa138b
      for ALL rows (paginate on has_more; no LIMIT window — same rule as the Step 4
      dedupe guard). Keep the result in context: STEP 4 (don't re-surface active deals)
      and STEP 5B (verified-ask cross-writes) BOTH reuse this one fetch — do not re-pull.
      CAPACITY GATE: from the same result, determine whether any Columbus OH row sits in
      an under-contract stage (PSA executed / under contract / DD / closing). State the
      finding and the rows it rests on in receipt R1. If the fetch fails (quota → the
      `notion-quota-fallback` skill; still failing → R1 FAILED): apply NO capacity gate,
      SKIP 5B (write nothing to the tracker), and say both in the digest header line —
      never fall back silently on the "last known" note above.
  0b. PROPERTY REGISTER ROSTER REFRESH — read collection://24d6a531-f4b7-4c38-87fb-3b1be4a4f1f3
      (Address column) and the Tenant DB 'Property Address' options; diff against
      _shared\ora-own-portfolio-exclusions.json. Every owned address missing from the
      roster is added to an IN-MEMORY supplement for this run's STEP 2(e) check (treat as
      owned) and reported "ROSTER DRIFT: <address>" in R2. Do not edit the roster file.
      If the read fails, R2 FAILED and the guard runs on roster v-current only — say so.
  0c. PROVISIONAL CARRY-FORWARD — read
      C:\Users\Owner\OneDrive - Oxford Capital Partners\Claude_Workspace\_state\deal-sourcing-provisional-carryforward.json
      (outside every git checkout on purpose — a state file in ~/.claude would show up as
      unowned WIP in dirty-tree triage)
      (absent on first run = empty list; that is not a failure). Each entry
      {id, market, descriptor, source_url, first_seen, attempts, last_attempt, reason} is
      queued for STEP 1B-B detail resolution this run.
  0d. MONTGOMERY COUNTY MD — run it only when day-of-month <= 7 (the first Tuesday). Decide
      here, record the decision in §7d; this is cadence by design, not a gap.

STEP 1 — PULL NEW LISTINGS (preceding ~8 days; widen to ~30 if prior run missed)
For each of the ten clusters, web-search for newly listed industrial/flex product:
- Query patterns: "[metro] industrial property for sale [current month/year]",
  "[metro] flex warehouse listing", "[metro] industrial investment offering
  memorandum new".
- SOURCE STRATEGY — Crexi & LoopNet listing-DETAIL pages block automated fetch
  (HTTP 403); do NOT rely on plain WebFetch against them. Work the sources in this
  priority order, and capture a working public URL for every listing:
  1) Fetch-accessible aggregators that return clean detail pages — commercialsearch.com
     and commercialcafe.com (Yardi network), plus the Crexi PUBLIC MARKETPLACE index
     read via Claude-in-Chrome (logged out). These carry the same inventory and are the
     PRIMARY machine-readable source. (Confirm each slug actually loads a detail page —
     a dead CommercialSearch slug silently serves the city "for lease" index instead.)
  2) Broker-direct listing pages — many are JS-rendered; if WebFetch returns empty,
     read them via Claude-in-Chrome. Dominant local brokerages per cluster:
     Columbus — NAI Ohio Equities, Colliers Columbus, Equity Inc; Cincinnati — JLL,
     Colliers (Jeff Kroger team), Square Foot Commercial, Cushman Cincinnati;
     KC — Block & Co, Newmark Zimmer, AREA RE; Indianapolis — Bradley Co, Colliers
     Indy, Lee & Associates; Madison — Oakbrook, Founders 3, Colliers WI;
     Maryland — MacKenzie, St. John Properties resales, NAI KLNB; Grand Rapids —
     Colliers West MI, NAI Wisinski; Richmond — Porter Realty, Colliers Richmond,
     Cushman Thalhimer; Des Moines — CBRE Hubbell, R&R Realty, NAI Iowa;
     Louisville — Cushman & Wakefield | Commercial Kentucky
     (commercialkentucky.com, VERIFIED), CBRE Louisville. LOUISVILLE HAS A
     SOURCE THE OTHER NINE DO NOT: **KCREA (kcrea.com)**, the Kentucky
     Commercial Real Estate Alliance — a regional MLS-style listing platform
     with dedicated Louisville industrial for-sale pages. Try it alongside the
     Yardi network; it may carry inventory the national aggregators miss.
     Additional local Louisville brokerages are NOT yet verified — surface
     whichever firms appear as listing brokers on the first run and record
     them here rather than guessing at names.
  3) Crexi / LoopNet gated detail pages — open ONLY the logged-out public version via
     Claude-in-Chrome when no aggregator/broker page is available. NEVER log in, NEVER
     bypass a paywall or CAPTCHA. If still inaccessible, note it and move on.
- SUBAGENT DISPATCH GUARDRAIL (validated 2026-07-07 — see memory
  feedback_subagent_anti_delegation.md): if this step is executed by fanning work
  out to per-cluster subagents (e.g. via the Agent tool, one dispatch per market),
  every dispatch prompt MUST explicitly forbid the subagent from calling
  Agent/Task/Workflow itself, and MUST state that its final message has to be the
  actual findings, never a status/progress update. Without this line, roughly
  half of Tools:* subagents given this "scout multiple sources across many
  submarkets" framing will reflexively recurse into a child call and return a
  placeholder narration instead of data — confirmed on the 2026-07-07 restore run
  (4/9 first-pass agents recursed, each burning ~65K tokens for zero usable
  output; 0/7 recursed once the guardrail clause was added, all returning real
  verified data). Sanity check: a per-market agent that returns in under ~5 tool
  calls almost certainly delegated rather than worked — re-dispatch with the
  guardrail before trusting a thin or empty result.
- [v2.8: the Claude-in-Chrome references in the SOURCE STRATEGY ladder above and the
  "grant the dispatch browser-pane access" option below are SUPERSEDED by the v2.8
  RESOLUTION that follows and by STEP 1B — every browser read is done by the orchestrator
  in the browser pane (mcp__Claude_Browser__*), never by a scout.]
- BROWSER-TOOL REQUIREMENT (added 2026-09-05; remedy superseded by v2.8): a per-market dispatch given ONLY
  WebSearch/WebFetch cannot read JS-rendered broker-direct inventory pages — WebFetch
  returns an empty page or a nav shell for these, which reads as "no crawlable
  inventory" when the page may in fact carry live listings. Confirmed unreachable this
  way on 2026-09-05: NAI Wisinski, Colliers West MI, Cushman & Wakefield | Thalhimer,
  NAI Iowa, Hubbell Realty, R&R Realty, and Commercial Kentucky's own listing pages.
  Before reporting a brokerage as having "no crawlable for-sale inventory," either grant
  the dispatch browser-pane / Claude-in-Chrome tool access and have it actually load the
  page, or say explicitly in the run notes that only a text-only pass was attempted —
  do not let a text-only null read as a confirmed empty inventory.
  v2.8 RESOLUTION: scouts stay text-only (WebSearch/WebFetch) and run in parallel; every
  browser-dependent source is read by the ORCHESTRATOR in STEP 1B, sequentially. Do NOT
  give per-market subagents the browser pane — it is one shared pane, and parallel agents
  driving it clobber each other's navigation. Each scout's final message MUST include a
  SOURCE LEDGER: one line per source it tried → {loaded + N listings | loaded, 0 listings
  | empty/JS shell | 403 | not tried}. Every "empty/JS shell" and "403" line becomes a
  STEP 1B work item. A scout that returns no ledger is re-dispatched (like the <5-tool-call
  delegation check above).

- SOURCE COVERAGE CONTRACT (v2.8). A market is COVERED only when all three families
  below have a receipt (loaded with listings, verified-loaded-empty, or a named block):
    F1 Yardi network (commercialsearch / commercialcafe) — text scout.
    F2 Crexi public marketplace + LoopNet public search — STEP 1B browser pass.
    F3 Broker-direct: AT LEAST the REQUIRED brokerages below — text scout first, STEP 1B
       browser if the text pass returned empty/JS shell.
  REQUIRED broker-direct per market (the rest of the list above is best-effort):
    Columbus — NAI Ohio Equities, Colliers Columbus · Cincinnati — Colliers (Kroger team),
    Cushman Cincinnati · KANSAS CITY — BLOCK & CO AND NEWMARK ZIMMER, BOTH REQUIRED
    (2026-09-23 run covered KC from CommercialSearch/CommercialCafe only) · Indianapolis —
    Bradley Co, Colliers Indy · Madison — Oakbrook, Colliers WI · Maryland — MacKenzie,
    NAI KLNB · Grand Rapids — NAI Wisinski, Colliers West MI · Richmond — Cushman
    Thalhimer, Porter Realty · Des Moines — CBRE Hubbell, NAI Iowa · Louisville —
    Commercial Kentucky, KCREA.
  Record the per-market × per-family result in the digest's §7b SOURCE COVERAGE MATRIX.
  A family with no receipt for a market is a TRUE GAP (§7c) naming the market and family.
  CELL SEMANTICS (one rule, used by the contract AND §7c): `N listings` and `0 (verified
  loaded)` are COVERED. `blocked` (403 / Access Denied / bot-check) is a GAP-EXTERNAL —
  listed in §7c under its own sub-heading, because nothing the run can legitimately do
  fixes it. `JS shell — not read`, `pane throttled` and `not tried` are GAP-RUN — the run
  fell short, and they lead §7c. Note: the 2026-09-19 "Crexi 403s" finding was for PLAIN
  FETCH; the logged-out browser pane loaded Crexi search on 2026-09-23 (STEP 1B-A).
- SUBMARKET COVERAGE (do NOT skip): the KS side of Kansas City (Lenexa, Olathe, Shawnee, Overland
  Park) and Maryland's Howard County (Columbia, Jessup, Elkridge) + Anne Arundel/Hanover.
  Run these explicitly through the step-1 aggregators / Claude-in-Chrome, not just
  Crexi/LoopNet. If a submarket genuinely yields no verifiable for-sale listing, state
  that in the email's coverage-gaps note rather than omitting it silently.
- ADDED 2026-09-05 (coverage-gap fix, no scoring weight changed): Baltimore's Curtis Bay,
  Dundalk, and Rosedale, plus Glen Burnie MD, need the SAME explicit per-submarket query
  treatment as Howard County above. On the 2026-09-05 run a generic "Baltimore" sweep
  returned only aggregate counts for these four, no addressable street listings — a bare
  metro-level query does not reliably surface individual addresses for them. Query each
  by name; if a filtered Crexi/LoopNet browser-pane pull (not just WebSearch/WebFetch) is
  still needed to get addressable results, do it rather than reporting an aggregate-only
  null as a coverage gap.
- ADDED 2026-09-05: Indianapolis's Whiteland and Beech Grove submarkets need their OWN
  query, not folded into a combined Noblesville search. On the 2026-09-05 run they were
  bundled into one Noblesville-area query and came back under-covered — neither returned
  a distinct result. Search each by name.
- MONTGOMERY COUNTY MD — MONTHLY, NOT WEEKLY (downgraded 2026-07-14). A full
  fetch-verified pass found ZERO in-box industrial for-sale inventory county-wide:
  both Yardi platforms return no industrial-for-sale listings for Rockville,
  Gaithersburg, or Germantown, and the only priced comps nearby (Frederick, Beltsville)
  landed 57-74% ABOVE the basis floor. The county is expensive, thin, and office/lab
  skewed — the inventory structurally is not there at ORA's price point. Run it on the
  first scan of each month only. The better route into this geography is
  `county-parcel-screen` against Montgomery County assessor data (off-market), not
  repeated on-market scanning. One open human thread: a CBRE "Rockville Flex
  Properties" offering (5706-5712 Frederick Ave + 12300 Washington Ave, 53,365 SF,
  short WALT, seller financing) is the most buy-box-shaped signal there, but it is
  behind a CBRE deal-room login and CANNOT be reached by any automated pass — it needs
  a broker call, not another scan.
- MADISON WI — a nil result is NORMAL. Only ~4 industrial for-sale listings exist
  citywide (confirmed 2026-07-14). An honest empty return is the correct output, not a
  scan failure — do not stretch office or retail product into "flex" to fill the table.
- Also capture RE-LISTS and PRICE CUTS on properties already in the Deal Sourcing
  Log or previously ranked — both are motivation signals; note prior price and delta.
- Respect site terms: public pages and web-search results only. Never log in, never
  bypass paywalls or CAPTCHAs.
- Record for each candidate: address, metro/submarket, SF, asking price, $/SF,
  year built, occupancy/tenancy, clear height, parking, power (if stated),
  CONSTRUCTION TYPE (masonry / brick / block / tilt-up / precast / PEMB-metal /
  hybrid — see the Construction & envelope score in Step 3B), broker + firm,
  listing URL, date first seen, and LISTING-DATE BASIS (v2.8, below).

  *** LISTING-DATE BASIS — MANDATORY (v2.8, 2026-09-23) ***
  The 2026-09-23 run's dates were mostly platform "updated" stamps, so re-list vs refresh
  could not be told apart. For every candidate record exactly one basis, strongest first:
    LISTED <date>   — the page shows a listed / "on market since" / "date listed" date.
    DOM <n>         — the page shows days-on-market (Crexi and LoopNet usually do; derive
                      listed = run date − n and record both). This is why STEP 1B reads the
                      Crexi/LoopNet copy of a listing even when the Yardi copy was found.
    UPDATED-ONLY <date> — only a "last updated"/"refreshed" stamp (typical on
                      CommercialSearch/CommercialCafe). NEVER treat this as a listing date.
    NONE            — nothing shown. ORA's own `First Sighted` is then the only anchor.
  Write it into Notes / Flags as `DATE-BASIS: <basis>` (no new Notion property — the scan
  must not mutate the DB schema unattended). When two sources disagree, keep the EARLIEST
  listed date and name both. The re-list decision rule that uses this is in STEP 4.

  *** LISTING-AGENT CAPTURE — MANDATORY (v2.7, 2026-09-19, Gabriel-directed) ***
  Capture the LISTING AGENT(S) for every candidate: full name, firm, and email/phone
  ONLY where actually shown. This is the fix for the 545/310 (56.9%) broker-name gap.
  A PLATFORM IS NOT A BROKER. Never write "Crexi", "LoopNet", "CommercialSearch",
  "CommercialCafe", "Revere", "CoStar", "PropertyShark" or any other platform name into
  a broker field — those belong in the Deal Sourcing Log's own `Source` select, not in
  `Broker / Contact`. Never guess a name, never construct or infer an email address from
  a firm's domain pattern, and never carry an agent name over from a different listing.
  SOURCE ORDER (measured 2026-09-19 against real current Columbus OH and Indianapolis IN
  industrial listings — write around what actually works, per the v2.4 lesson):
  1) commercialsearch.com / commercialcafe.com listing DETAIL pages — WORKS. 5 of 5
     detail pages returned a clean agent name + firm via plain WebFetch (Dan Sheeran Jr.
     / NAI Ohio Equities · Michael J. Semon / NAI Ohio Equities · Matthew Ferguson /
     Premier Commercial | TCN Worldwide · Annie Scott / Annie Scott Realty Group). This
     is the PRIMARY source and it is the same Yardi-network ladder Step 1 already uses.
     THE DETAIL PAGE IS REQUIRED: the city SEARCH-RESULT pages show address/price/SF and
     NO agent at all, so a search-card scrape yields nothing. Get the detail-page slug
     from the index, then fetch it.
  2) Brokerage's OWN site — BEST-EFFORT FALLBACK ONLY, not the preferred source. Measured
     worse than the aggregators: drk-realty.com's listings page returned no listings at
     all to WebFetch, and ohioequities.com is query-param/JS-driven and yielded only the
     firm switchboard number, no agent. Try it (browser pane if WebFetch is empty, per
     the BROWSER-TOOL REQUIREMENT above) but do not spend a run's budget here.
  3) Crexi / LoopNet — DO NOT COUNT ON THESE. Both 403 on BOTH the search index and the
     listing detail page to automated fetch (re-confirmed 2026-09-19). A blocked
     aggregator is `AGENT NOT CAPTURED`, reason `aggregator blocked` — it is NEVER a
     reason to guess, and NEVER a reason to attempt a login, a paywall bypass or a
     CAPTCHA (see the standing rule above).
  EMAIL AND PHONE ARE USUALLY UNOBTAINABLE — THIS IS EXPECTED, NOT A FAILURE. Every
  aggregator detail page tested gates contact behind a "Contact Broker" form; 0 of 5
  published an agent email or direct phone. Capture them when a page genuinely shows
  them (brokerage sites sometimes do) and leave them blank otherwise. Do NOT hold up a
  listing waiting for contact details.
  FALLBACK ORDER when the agent cannot be resolved: (i) named individual agent + firm —
  best; (ii) firm only, with the agent as `AGENT NOT CAPTURED` — acceptable, record the
  firm; (iii) neither — write the literal string `AGENT NOT CAPTURED` and record the
  REASON in Notes / Flags (`aggregator blocked` · `detail page not loaded` · `no agent
  shown on page` · `listing came from an OM/broker email with no agent named`).
  BROKER CAPTURE NEVER BLOCKS A LISTING WRITE. A candidate whose agent cannot be
  captured is still logged, still gated, still scored and still written to Notion
  exactly as it would otherwise be — `AGENT NOT CAPTURED` is a data state, not an error
  and not a filter. Never drop, defer or fail a listing over a missing broker.

  *** HOW TO ACTUALLY DETERMINE CONSTRUCTION TYPE (added 2026-08-04 — the previous
  instruction was just "LOOK: listing photos usually settle it in seconds", and on the
  2026-08-04 run ALL NINE market agents reported it as impossible and returned UNKNOWN
  for every candidate. UNKNOWN scores the same as PEMB (2/5), so that silently
  suppressed ~3 points on essentially the whole scan. The instruction was wrong, not
  the agents — WebFetch returns text only and cannot see images. Use this instead: ***
  *** MANDATORY, NOT DISCRETIONARY (ratified by Gabriel 2026-09-05, after the 2026-09-05
  run skipped this whole procedure "for scope reasons" with no compensating check). The
  score impact is genuinely small — ~1 in 5 candidates resolvable, up to 3 points each
  (masonry/tilt-up/precast resolving from UNKNOWN; less for hybrid, none for confirmed
  PEMB — the one measured sample, 2026-08-04, averaged 2 points across 3/3/0) — but
  the real yield is the by-products below, which listing text never discloses. Skipping
  this step is a COVERAGE GAP to name explicitly in that run's digest, exactly like a
  submarket that returned nothing — never a silent scope trade-off a run makes on its
  own. Restore it every run. ***
  *** v2.8 SPLIT (2026-09-23 — skipped again on the 2026-09-23 run, budget exhausted): ***
  - IN-RUN (receipt R7): after STEP 3A/3B assigns tiers, run steps 1-2 below for EVERY
    T1 PURSUE and T1-PENDING-PRICE row, in STEP 3C. These are the rows that trigger an
    OM request or a broker call this week; they cannot wait. Skipping one = R7 FAILED and
    a §7c gap naming the address. T1 rows are NEVER handed off.
  - HANDOFF (receipt R8): every T2 WATCH row left UNKNOWN is written with
    `Construction Type` = 'Unknown — CONFIRM' AND a populated `Listing URL` (except a
    Crexi/LoopNet-only-URL row, which stays BLANK per STEP 5), which is
    exactly the target set of `ora-sourcing-construction-verify` (runs after this scan's
    done-marker, own budget, corrects the construction score only). Name the handoff count
    in §7a. A handed-off row is NOT a coverage gap — EXCEPT a T2 whose only working URL is
    crexi/loopnet: that task skips those domains, so name it in §7c as "construction
    unverifiable — Crexi/LoopNet-only URL" rather than counting it as handed off.
  - BACKFILL ON TOUCH: when STEP 4 updates an EXISTING active T1/T2 row whose
    `Construction Type` is BLANK (116 such rows on 2026-09-23 — they predate the field),
    set it to 'Unknown — CONFIRM' in the same update so the row enters the backstop queue —
    EXCEPT rows carrying `PROVISIONAL-UNRESOLVED` or whose only URL is crexi/loopnet, which
    stay blank (see STEP 5).
    Do not mass-backfill untouched rows from this task.
  - MARK WHAT YOU CHECKED: every row photo-checked in-run (resolved OR verified-attempt
    UNKNOWN) gets the verify task's own token appended to Notes / Flags —
    `CONSTRUCTION-CHECKED <run date>: <type or 'UNKNOWN — <reason>'>; findings: <...>` —
    so the verify task does not redo it.
  - Step 1 of the procedure (read the listing text) still runs for EVERY candidate.
  1. Read the listing text first. A minority state it outright ("masonry", "precast
     concrete", "pre-engineered steel", "block"). Cheapest win; take it and stop.
  2. Otherwise open the listing in the BROWSER PANE (preview_start / navigate), then:
     a. FIRST resize the viewport — `resize_window` with explicit width/height
        (e.g. 1280x900). A fresh pane reports 0x0 and NOTHING renders or decodes;
        this is almost certainly what past runs experienced as "screenshot failed to
        composite". Confirm with `window.innerWidth` before trusting an empty result.
     b. Extract gallery image URLs via javascript_tool:
        document.querySelectorAll('.property-details-gallery img')
        Dedupe on the src with the ?query stripped.
     c. Download at full size with curl, appending `?width=1400`, then Read the file
        (Read renders images). Classify from wall texture: regular 8x16 coursing +
        mortar joints = BLOCK/CMU · large panels with vertical joints, often fluted =
        TILT-UP/PRECAST · ribbed/corrugated metal skin with standing-seam roof = PEMB ·
        brick = MASONRY. Interior shots are just as diagnostic as exteriors (exposed
        block walls + steel bar-joist roof reads masonry immediately).
  *** TWO TRAPS THAT WILL PRODUCE A WRONG ANSWER — BOTH HIT ON 2026-08-04: ***
  - ATTRIBUTION. CommercialSearch/CommercialCafe pages carry a "similar properties"
    carousel (`.similarproperty`, `.carousel.listings`). Its photos are OTHER
    BUILDINGS. On 4111 Founders Blvd every single image on the page belonged to the
    carousel, and the most prominent one was actually 3717 Jonlen Dr — scoring it
    would have assigned that building's construction to the wrong deal. ALWAYS scope
    the query to `.property-details-gallery` and CHECK THE `alt` ATTRIBUTE, which
    carries either the subject address or the subject listing title. If alt does not
    match the subject, DISCARD the image.
  - THE CDN KEYS ON THE GUID, NOT THE FILENAME. URLs look like
    `cdn.commercialsearch.com/images/<GUID>/<name>.jpeg`. Reusing one GUID with
    different filenames returns THE SAME IMAGE every time (verified: four "different"
    downloads came back byte-identical, same md5). Never construct these URLs — always
    take the full href per image from the DOM.
  - NOT EVERY IMAGE IS DIAGNOSTIC. Filter out aerials, site plans, location maps and
    marketing overlays — they cannot resolve wall material. The filename is the tell
    (`Zoomed In Aerial.jpg`, `Site Plan .jpg`, `Location Map.jpg`, `Cover Photo`).
    A gallery of nothing but aerials is a VERIFIED-ATTEMPT UNKNOWN, not a hit.
  EXPECTED COVERAGE — DO NOT TREAT A LOW HIT-RATE AS A BUG. Measured across 15 listings
  on 2026-08-04: **3 resolved** (7267 Park Cir Dr precast · 3717 Jonlen Dr block ·
  5740 W Minnesota St PEMB) · **4 had images but only non-diagnostic aerials/site plans**
  (1310 S West St · 4197 Reardon Rd · 8840 N Greenview Dr · 2800 Annapolis Rd) ·
  **8 had a `.property-details-gallery` containing ZERO images** (4111 Founders Blvd ·
  1621 Dana Ave · 1330 Kemper Meadow · 12033 Best Place · 1900 Benhill Ave ·
  6380 Beulah Rd · 1255 N Main St · 1255 N Winchester St · 1437 Gentry St). So roughly
  **1 in 5 candidates is resolvable from photos** — still infinitely better than the
  previous 0 in 9, but budget accordingly. For the other ~80%, the broker call remains
  the ONLY route and the Next Action must continue to say "CONFIRM CONSTRUCTION".
  A verified "no photos exist" is a real result: record UNKNOWN and note the gallery was
  empty, so the next run does not repeat the attempt. Do NOT report UNKNOWN without
  having actually run steps 1-2.
  *** THE BY-PRODUCTS OUTWEIGH THE 3 POINTS — the real reason to do this. *** Every
  resolvable listing on 2026-08-04 yielded something the listing TEXT never disclosed:
  3717 Jonlen's interiors exposed a taproom/arcade build-out that Step 2.5 zero-credits ·
  5740 W Minnesota revealed United Rentals as the in-place credit tenant AND triggered
  the PEMB basis-distortion warning · 8840 N Greenview's aerial showed a SEPARATE
  0.90-acre parcel marketed at $250,000 beside the building ask · 2800 Annapolis's aerial
  showed a narrow TRIANGULAR site pinched against an active rail line (no expansion, poor
  truck circulation) · 7267 Park Cir Dr showed a cell tower on the parcel. None of that
  appears in any listing description. Inspect the photos even when construction type is
  already settled from text — and note that the "non-diagnostic" aerials still produced
  three of those five findings.

STEP 1B — BROWSER PASS (v2.8 — ORCHESTRATOR ONLY, sequential, browser pane)
Why: the 2026-09-23 scouts were text-only, so Crexi/LoopNet were never fetched, JS-rendered
broker inventory was never read, and two provisional finds were dropped for want of a
detail page. The browser pane (mcp__Claude_Browser__*) reads all three. Run it yourself,
after the text scouts return and before gating.
SETUP: resize_window 1280x900 FIRST and confirm `window.innerWidth` > 0 (a fresh pane is
0x0 and renders nothing). If the browser tools are absent or a permission prompt blocks
them with nobody attending: R5/R6/R7 = FAILED ("no browser pane this session"), every
affected market-family goes to §7c, and the run CONTINUES text-only — never substitute
curl/WebFetch against a 403 and never look for another route around a block.
HARD LIMITS (all sub-steps): public, logged-out pages ONLY. Never log in, never create an
account, never solve or bypass a CAPTCHA / "Access Denied" / bot-check. On any block page:
stop that SITE for the rest of the run (no retry, no alternate route), record `403/blocked`
in the source ledger, move on. PACING: ≥20 s between page loads on the same domain (LoopNet
tripped "Access Denied" at ~25 loads in a few minutes on 2026-09-18 — see
ora-loopnet-listings-sync). A block on LoopNet here can also block Monday's
ora-loopnet-listings-sync, so stay well inside the pace.
  1B-A  DISCOVERY (receipt R5) — per market, in this order, within the HARD CAPS:
        · Crexi public marketplace — MEASURED 2026-09-23 (logged-out, browser pane): the
          public search DOES load and filters work. WORKING URL FORM:
            https://www.crexi.com/properties?types%5B%5D=Industrial&placeIds%5B%5D=<Google place id>
          (Columbus OH = ChIJcd6QucGJOIgRM7Wxz_hmMuQ, verified — the tab title resolved to
          "Columbus, OH Industrial For Sale | Crexi"). For other metros get the place id by
          typing the metro into Crexi's own location box once; record the id in run notes.
          The city-path form (/properties/OH/Columbus?...) HUNG on a spinner — do not use it.
          Results hydrate SLOWLY: wait ≥10 s and confirm the tab title names the metro
          before reading — an early read returns a 51-character shell that looks like
          "no listings". Extract cards with javascript_tool: unique hrefs matching
          /properties/<id>/ plus the enclosing tile's innerText (walk up the parent chain
          until the text is >60 chars; cap 300 chars per card). If the pane is HIDDEN and a
          script times out, retry once with a shorter script, then record `pane throttled`.
        · LoopNet public search — only where Crexi was blocked or returned 0 for the metro
          (protects Monday's ora-loopnet-listings-sync from an Access-Denied block).
        · Every REQUIRED broker-direct page from the SOURCE COVERAGE CONTRACT whose scout
          ledger line says empty/JS shell (plus any other empty/JS-shell ledger line, budget
          permitting). Record listings found; "loaded, 0 for-sale listings" is a legitimate
          verified-empty result — "never loaded" is not.
        New finds here join the candidate list exactly like scout finds (same Step 1 record,
        same agent capture, same DATE-BASIS). For a candidate already found via Yardi, read
        its Crexi/LoopNet card only to get DOM / listed date — do not duplicate it.
  1B-B  PROVISIONAL RESOLUTION (receipt R6) — for every PROVISIONAL candidate (index-only,
        snippet-only, or unaddressed) from this run's scouts AND every carry-forward entry
        loaded in STEP 0c: try to load a DETAIL page (search the platform/broker site by
        the descriptor — e.g. "50,000 SF industrial West Chester OH" — in the pane).
          · Resolved (detail page loaded) → normal candidate; drop PROVISIONAL.
          · ADDRESSED but unresolved → it IS LOGGED to Notion (STEP 5) flagged with the exact
            token `PROVISIONAL-UNRESOLVED` in Notes / Flags (ora-sourcing-construction-verify
            excludes rows on that exact token — keep the spelling),
            Verdict capped at T2 WATCH (the standing "PROVISIONAL cannot be T1" rule), Next
            Action "VERIFY LISTING — detail page not loadable <run date>". It is NEVER
            silently left out (2026-09-23: 1211 Cox Ave, Erlanger KY was dropped this way).
            It still runs STEP 2(e) own-portfolio guard first. TWO FIELDS STAY BLANK on a
            PROVISIONAL row, deliberately:
              - `Ask at First Sighting` — an index-page figure must never become the
                write-once baseline (index rows understated one KC price by $125K in July;
                baking that in fires a phantom CUT/RAISED later). Put the index ask in
                `Asking Price` with "PROVISIONAL ASK" in Notes; write `Ask at First
                Sighting` on the run that first VERIFIES the ask (this is not the
                "overwrite" case — the field was empty).
              - `Construction Type` — leave BLANK, not 'Unknown — CONFIRM'. The verify task
                would otherwise load the index URL, find no gallery, stamp
                CONSTRUCTION-CHECKED and drop the row from its queue for good. Set it to
                'Unknown — CONFIRM' on the run that resolves the detail page.
          · UNADDRESSED and unresolved → cannot become a Notion row (no dedupe key). Keep it
            in the carry-forward file (STEP 0c path) with attempts+1; after 3 failed
            attempts drop it and name it once in §7c as "abandoned after 3 runs".
        Write the carry-forward file at the end of the run (receipt R13): the surviving
        unaddressed entries only. This is a local JSON state file — no Notion write. On a
        later run, a resolved PROVISIONAL row is updated in place (STEP 4 match): replace the
        `PROVISIONAL-UNRESOLVED` token with `PROVISIONAL-RESOLVED <run date>` (the verify task
        then picks the row up), write the verified ask to `Asking Price` AND the (still-empty)
        `Ask at First Sighting`, set `Construction Type` = 'Unknown — CONFIRM' unless resolved
        (or leave it BLANK if the only working URL is Crexi/LoopNet, per STEP 5).
  (Construction photos for T1-bound rows are NOT part of this pass — they need tiers, so
  they run later as STEP 3C, after TIER ASSIGNMENT. Do not attempt them here.)

STEP 2 — ELIGIBILITY GATE
Keep a candidate only if: (a) industrial/flex/office-warehouse product; (b) in a
target cluster; (c) within or plausibly within 10-80K SF and $1-10M; (d) no instant
disqualifier; (e) NOT ORA's OWN PORTFOLIO (v2.6 — see below; runs FIRST, before a-d).
Log filtered items with one-line reasons in the run notes; do not
write them to Notion.

*** (e) OWN-PORTFOLIO GUARD (v2.6, 2026-09-18, Gabriel-directed after a real incident) ***
On 2026-09-05 this scan logged ORA's OWN Cushman & Wakefield listing — "2000-2026 Zettler
Road Complex, Columbus OH" — as a new lead: T1 PURSUE, score 71, Next Action "REQUEST
PRICE" from our own listing broker. The address range never string-matched any owned
address (2000-2002 / 2018 / 2022 Zettler) and NO step checked ownership. A scan that
tells us to call our own broker for our own price is not a sourcing tool.
For EVERY candidate, before any scoring or Notion read/write:
  python "C:\Users\Owner\.claude\scheduled-tasks\_shared\own_portfolio_guard.py" "<full listing address as titled>" --broker "<listing broker firm + names>"
  - exit 2 / OWN-PORTFOLIO → DROP. Never score it, never write it to the Deal Sourcing Log
    or Pipeline Tracker. Put one line in the digest under "OWN ASSETS SEEN ON MARKET"
    (address, platform, ask if shown, days on market) — that is disposition intel for
    Gabriel, not a lead.
  - exit 3 / BROKER-FLAG → the listing broker is one ORA has engaged on its own assets.
    Not a drop by itself; verify the address against the roster by hand and state the
    check in Notes / Flags before logging.
  - exit 0 / CLEAR → continue to (a)-(d).
  The matcher is RANGE-AWARE (a "2000-2026" listing hits owned 2018) and normalizes
  suffixes/directionals. Roster: _shared\ora-own-portfolio-exclusions.json (v1.0).
  ROSTER REFRESH each run (v2.8: EXECUTED IN STEP 0b, before scouting — use its in-memory
  supplement here; do not re-read): read the Notion Property Register
  (collection://24d6a531-f4b7-4c38-87fb-3b1be4a4f1f3) Address column and the Tenant DB
  'Property Address' options; any owned address missing from the roster → treat as owned
  for this run and report "ROSTER DRIFT: <address>" in the run notes (do not edit the
  roster file unattended). Known gap: the Sepich Portfolio is one aggregate Register row
  with no addresses — the roster covers only the Sepich buildings named elsewhere.
  If the guard script cannot run (python missing, file absent), FAIL CLOSED for Columbus
  OH candidates on streets that appear in the roster, and say so in the digest.
Unpriced listings in-cluster and on-product PASS the gate (a)-(d) (price discovery is a
next action, not a disqualifier) — but never (e): an unpriced own asset is still ours.

STEP 2.5 — FUNCTIONAL SF NORMALIZATION (do this BEFORE any $/SF is computed)
Compute $/SF on FUNCTIONAL SF, not marketed SF. Marketed SF routinely includes
space that earns 0% credit under ORA doctrine, and a $/SF built on inflated SF
produces a basis figure that is simply false.
- Multi-story / upper floors / mezzanine on slab: 0% credit unless INDEPENDENTLY
  functional (own loading, own access, usable clear height). Default to 0% credit.
- Heavy office component: count it, but flag the office ratio — a 50%-office
  "10,000 SF industrial" building has 5,000 SF of industrial basis.
- Special-purpose improvements (cold storage, clean room, distillery/brewery
  process build-out, lab): assume a generic shallow-bay tenant pays nothing for
  them. Underwrite at zero or salvage and re-test basis on the remainder.
WORKED EXAMPLE (2026-07-14, why this step exists): 1275 Budd St, Cincinnati listed
at $1.1M / 61,932 SF = a headline $17.76/SF, which scored as the deepest basis
discount in the entire scan. It is a FOUR-STORY 1895 warehouse. Functional
ground-floor SF is ~15,500, so the true basis is ~$71/SF — four times the headline.
The nominal figure would have pushed a freight-elevator conversion play into Tier 1.
ALWAYS state both figures: "marketed $X/SF; functional $Y/SF (basis test uses $Y)."

STEP 3A — HARD-FLOOR GATE (runs BEFORE scoring; DECIDES THE TIER)
THE SCORE IS NOT THE GATE. THE FLOOR IS THE GATE. This is the single most important
rule in this task. On 2026-07-14 the old score-first design produced 29 Tier-1s out of
43 candidates — a ranking signal so diluted it was useless — because deals that FAILED
the basis hard floor were still scoring 62-78 and landing in the pursue band. Tier is
now assigned by the gate; the score only RANKS candidates within a gate outcome.

*** THE DENOMINATOR IS RCT v03. THERE IS ONLY ONE. IF YOU FIND A SECOND, IT IS A BUG. ***
RCT v03 lives in the `acquisition-underwriting` skill ("Replacement Cost Table (RCT
v03)" under UNDERWRITING CONVENTIONS) and is AUTHORITATIVE. Do NOT screen off
target-markets.json — its operative benchmark was RETIRED 2026-07-14. Do NOT use the
old $140/$170/$150/$130 constants, the retired C&W-hard figures, or RCT v02.

BASIS TEST (ratified by Gabriel 2026-07-14):
  basis $/SF = (price x 1.02 closing) / FUNCTIONAL SF     <- Step 2.5 SF, not marketed SF
  CLEARS if  basis $/SF  <=  RCT v03 LOW x (1 - vintage floor)
  Vintage floor = linear ramp: 65% at <=1995 -> 60% at >=2005 (-0.5%/yr).
  Year built UNKNOWN -> default 1995 (the 65% floor; conservative). Flag it.

  Note the 2% closing cost: doctrine defines basis as ALL-IN (price + closing + CapEx
  + lease-up carry). At scan time we cannot know CapEx or carry, so price x 1.02 is a
  DELIBERATELY GENEROUS PROXY — the true basis is always worse. Say so on any deal
  that clears by a thin margin. (The scan previously used bare price/SF, which
  flattered every candidate.)

    METRO         RCT v03 LOW   clears at <=1995   clears at >=2005
    Columbus         $229.65         $ 80.38            $ 91.86
    Cincinnati       $251.46         $ 88.01            $100.58
    Kansas City      $227.90         $ 79.77            $ 91.16
    Indianapolis     $253.83         $ 88.84            $101.53
    Maryland         $232.97         $ 81.54            $ 93.19
    Madison          $229.08         $ 80.18            $ 91.63   [PROXY]
    Grand Rapids     $253.11         $ 88.59            $101.24   [PROXY — WEAKEST]
    Richmond         $232.97         $ 81.54            $ 93.19   [PROXY]
    Des Moines       $231.66         $ 81.08            $ 92.66   [PROXY]
    Louisville       $237.07         $ 82.97            $ 94.83
  (Table mirrored for convenience. acquisition-underwriting WINS on any disagreement.)

WHY THE FLOOR IS 65%, NOT 25% — READ THIS BEFORE YOU "CORRECT" IT:
  The floor % and the denominator are a MATCHED PAIR. RCT v03 is TRUE all-in
  shallow-bay replacement cost (~$230-254/SF LOW), roughly DOUBLE the understated
  figure the old 25-30% floor was calibrated against. A 25% floor against RCT v03
  would let a Columbus deal pay $172/SF and "clear" — every candidate in the buy-box
  passes. A FLOOR THAT PASSES EVERYTHING IS NOT A FLOOR.
  ORA's real, revealed strategy is to buy at ~35-40% OF TRUE REPLACEMENT COST — a
  ~64% discount. The "25% discount" language was always an artifact of a wrong
  denominator. Use the real number in the digest; it is a far stronger fact.
  *** METAL-BUILDING BASIS DISTORTION — READ THIS BEFORE CLEARING A PEMB ***
  The C&W benchmark measures ground-up build-to-suit DISTRIBUTION CENTERS, i.e.
  CONCRETE / TILT-UP product. A pre-engineered metal building costs materially LESS
  to build than tilt-up. So applying a tilt-up-derived replacement cost to a METAL
  building OVERSTATES its discount to replacement — the metal building looks like a
  basis bargain partly because it was cheap to build, not because it is mispriced.
  Metal is therefore flattered TWICE: cheap to build, and then credited with a
  discount measured against a more expensive form of construction.
  RULE: any PEMB/metal candidate that clears the basis floor by less than ~15% is
  SUSPECT — say so explicitly in the digest and in the Notion record, and do not
  present its basis discount as clean. A masonry/tilt-up building clearing by the
  same margin is a genuinely better deal at the same $/SF.
  We do NOT yet have a sourced PEMB $/SF, so no numeric adjustment is applied —
  flag it, do not fabricate a multiplier. Sourcing a PEMB shell cost is on the
  same GC/lender email that would settle soft costs and the small-bay premium.
- PHYSICAL FLOORS: >=200A power, >=2 stalls/1,000 SF parking, functional clear
  height. UNKNOWN is not FAILED — treat unknowns as open questions, not failures.
- INSTANT DISQUALIFIERS: per the buy-box list above.

Gate outcomes (write the outcome to Notion `Floor Result`):
- PASS — clears basis, no failed physical floor, no disqualifier. ELIGIBLE FOR T1.
- FAIL-BASIS — priced above 75% of replacement. CANNOT BE T1 AT ANY SCORE.
  Maximum tier is T2 WATCH. Log it, state the price at which it WOULD clear, and
  monitor for a cut. Pursuing one requires an explicit Gabriel exception plus a
  named compensating factor written into `Exception Compensating Factor`.
- FAIL-YIELD / FAIL-BOTH — as above for the >8% stabilized YoC floor once NOI is known.
- N/A (UNPRICED) — on-doctrine but no ask published. The basis test CANNOT BE RUN.
  These are NOT Tier 1. They are their own bucket: **T1-PENDING-PRICE**. The only
  action is REQUEST PRICE. Never report them in the same count as gate-cleared T1s —
  on 2026-07-14, 13 of the 29 "Tier 1" deals were unpriced, which flattered the
  headline badly. For each, state the ask ABOVE WHICH IT DIES on basis, so the broker
  call has a decision rule attached before it is made.

STEP 3B — SCORE (Fit Score 0-100 — RANKS WITHIN A GATE OUTCOME, never overrides it)
- Market — primary cluster (20): established cluster 20; entry-phase 14; edge of
  cluster 8; outside 0 (should have been filtered).
- Product — B/C industrial/flex (15): on-doctrine 15; mixed w/ heavy office 8;
  marginal 4.
- Basis vs replacement (15): >=25% below replacement 15; 10-25% below 9; near
  replacement 4; above 0. Unpriced = 7 provisional. RETAINED as a ranking signal
  (depth of discount legitimately separates two deals that both clear the floor) —
  but it NO LONGER decides the tier. Step 3A does. REWEIGHTED 20 -> 15 in v2.2:
  basis is now a GATE, so carrying 20 score points for it double-counted. The freed
  5 points fund the construction factor below.
- Construction & envelope (5) — ADDED v2.2, Gabriel 2026-07-14. ORA prefers
  masonry / brick / block / tilt-up over metal. Mirrors the convention already
  ratified in the acquisition-underwriting skill ("block/tilt-up/brick full credit;
  PEMB ~= half, never kills"):
    masonry, brick, CMU/block, tilt-up concrete, precast .......... 5
    hybrid (masonry/block walls + metal roof, or metal rear addition)  3
    pre-engineered metal building (PEMB) / metal skin on steel frame   2
    UNKNOWN ....................................................... 2
  UNKNOWN scores the SAME as PEMB, deliberately: do not award credit you have not
  verified, and never let "we didn't check" outscore "we checked and it's metal."
  Confirming construction is 3 free points on a broker call — so ask. Flag every
  unknown "CONFIRM CONSTRUCTION".
  NEVER A DISQUALIFIER — a metal building is a preference penalty, not a floor.
- Stabilized YoC (10): >8% achievable on stated/estimated NOI 10; 7-8% 6; <7% 2;
  unknown 5 provisional.
- Capital sleeve (10): $1.5-6M 10; $1-1.5M or $6-10M 6; outside 0.
- Value-add bias (5): vacancy/below-market rents/short WALT present 5; stabilized 2.
- Physical floors (10): meets power+parking+clear 10; one unknown 6; one failed 3;
  two+ failed 0.
- Mezz SF credit (5): no mezz dependency 5; mezz-inflated SF 0.
- Lease quality (5): PG or 3%+ escalations evident 5; unknown 3; weak 0.

TIER ASSIGNMENT (gate first, score second):
- T1 PURSUE      = Floor Result PASS **AND** score >=60. Request OM immediately.
- T1-PENDING-PRICE = Floor Result N/A (unpriced) AND score >=60. REQUEST PRICE only.
                     Report and count SEPARATELY from T1 PURSUE.
- T2 WATCH       = FAIL-BASIS (any score), OR PASS with score 50-59. Log, monitor
                   for price cuts, no outreach.
- PASS / DECLINE = priced at or above replacement, OR 2+ failed physical floors, OR
                   an instant disqualifier, OR score <50. Log with the reason.
A score >=60 NEVER promotes a FAIL-BASIS deal into T1. If you find yourself writing
"scores 78 but fails basis — worth a look," STOP: that is the exact failure this
redesign exists to prevent. It is a T2.

STEP 3C — CONSTRUCTION PHOTOS, T1-BOUND (v2.8, receipt R7 — runs NOW, after tiers exist)
For every T1 PURSUE and T1-PENDING-PRICE row whose construction is still UNKNOWN after the
listing-text read: run the STEP 1 construction procedure (browser pane, both traps), ≤ 4
page loads per row. Order of URLs to try: the commercialsearch/commercialcafe detail page
(the `.property-details-gallery` selector and the alt-text attribution check are VALIDATED
only there) → broker-direct listing page → Crexi public detail page.
NON-YARDI PAGES: there is no validated gallery selector. Take only images inside the
listing's own media/gallery container (never a "similar"/"nearby"/"recommended" block),
and only when the alt text or the adjacent caption names the SUBJECT address or title —
the same attribution rule as the Yardi trap. If attribution cannot be established, the
result is NOT a verified-attempt UNKNOWN: it is R7 FAILED for that row, named in §7c
("T1 construction unverified — no attributable gallery on <platform>"), with Next Action
"CONFIRM CONSTRUCTION" on the broker call. Never mark an unattributable page as checked.
Write the result, the CONSTRUCTION-CHECKED token and any by-products into the row in
STEP 5. If a confirmed construction type moves the score across the 60 line, re-apply
TIER ASSIGNMENT (the gate is unchanged; only the 5-pt component moved).

BENCHMARK HONESTY (mandatory in every digest): the denominator is RCT v03 — SOURCED
from the C&W 2025 guide and ratified by Gabriel 2026-07-14. State in the digest which
metro floor was applied, and state the discount as a share of TRUE replacement ("this
deal buys at 34% of all-in replacement cost"), not as a vague "below replacement."
Live caveats that must still be surfaced:
- THE x1.30 SOFT/PROFIT/FINANCING MULTIPLIER IS AN [EST] — the only unsourced input in
  RCT v03. It is deliberately set at the LOW end of the industry range, so the floor
  is HARDER than truth, not softer. One GC quote per market retires it.
- BASIS IS A GENEROUS PROXY AT SCAN TIME — price x 1.02 omits CapEx and lease-up carry,
  which doctrine includes. True basis is always worse than the scan's figure.
- FOUR METROS USE PROXIES — Madison (Milwaukee), Grand Rapids (Detroit), Richmond
  (Baltimore), Des Moines (Minneapolis) are NOT in the C&W guide. Mark any basis
  verdict in those four [PROXY]. GRAND RAPIDS IS THE WEAKEST: Detroit is a high-cost
  union market while RSMeans shows Grand Rapids well below the national average, so
  its floor ($107.73) is probably TOO GENEROUS — flag Grand Rapids passes accordingly.
- NAME ANY DEAL WITHIN ~3% OF ITS FLOOR. The benchmark is March-2025 vintage and
  construction cost is reaccelerating (Turner +4.87% YoY, Mortenson +6.77%, AGC input
  PPI +8.4%), so a near-line deal could move on the next guide.
DO NOT use an "all-in" (hard + soft + land) denominator. It was considered and
REJECTED on ratification: at ~$230/SF Midwest it sets the floor near $172/SF, which
essentially every Class B/C deal clears — a floor that passes everything is not a
floor. The true all-in figure (~$200-240/SF) is an IC-MEMO NARRATIVE point — "we buy
at 30-50% of true replacement" — and belongs in memos and lender packages, NOT in
the screen.

PROVISIONAL / UNVERIFIED LISTINGS: a listing captured from a search-results INDEX
page, with no listing DETAIL page ever loaded, is PROVISIONAL. Mark it, and it
CANNOT be T1 until a detail page (or broker) confirms it. Index rows carry stale
prices, wrong year-built, and dead listings: on 2026-07-14, four KCK index-only
finds were verified a week later and produced one confirmed, two corrected (one
wrong year-built, one price understated by $125K), and one dead listing. Verify
before pursuing, never after.

PRE-MORTEM RULE (project standing instruction): for every T1 / T1-PENDING-PRICE / T2
candidate, write one sentence stating the most likely reason the deal FAILS ORA
underwriting (basis, YoC, physical floor, tenancy, zoning, environmental, capacity).
This ships in both the Notion record and the digest. No candidate is presented
without its failure mode.

STEP 4 — DEDUPE / DIFF (price-cut detection is now MECHANICAL — use it)
Fetch existing rows from the Deal Sourcing Log (Notion data source
9a6ae219-85a3-4621-899c-c757fd062f8b). Match on address (normalized) + metro.

*** DEDUPE GUARD — FETCH THE FULL ACTIVE SET, NOT A WINDOW (added 2026-07-21 after a real
incident). *** The log holds 100+ active rows. On 2026-07-21 the dedupe baseline was pulled
with `ORDER BY "Last Updated" DESC LIMIT 100`, which silently missed the OLDER half of the
log — so 9 of that run's 21 "new" rows were in fact DUPLICATES of existing rows (5545 Fair
Ln, 5027 Madison, 4612 Paddock, 84-100 Fornof, 620 Lindenwood, 6800 E Truman, 1020 W Pratt,
2141 Kennedy, 2201 Advance). A LIMIT on the dedupe query is a duplicate-manufacturing bug.
RULE: before writing ANY new row, fetch EVERY active row (Status NOT IN ('Dead','Passed'))
with NO row limit — paginate if the result is truncated (the SQL result carries has_more;
re-query with a `"Deal Name / Address" > '<last-seen-name>'` cursor and ORDER BY that column
until has_more is false). Build the normalized-address set from the COMPLETE result, then
match each candidate against it. Normalize by stripping the em-dash/comma city/ZIP suffix and
lower-casing the street (e.g. "5545 Fair Ln" == "5545 Fair Lane — Fairfax (Cincinnati), OH
45227"); match on street-number + street-name + (SF within 2%) as the dup key, since the
same property is logged with varying submarket labels and dash/comma punctuation. If a
candidate matches an existing row, UPDATE that row (per the rules below) — never create a
second. A per-run sanity check: if >1 row shares a normalized street address, they are dups.

The log now carries three fields (added 2026-07-14) that make price-cut detection a
diff instead of a guess. Before they existed, this task could read a listing's CURRENT
price but had no stored PRIOR price, so a quiet cut was structurally invisible — and
"no price cuts this week" was being reported as a finding when it was really a blind
spot. All 144 priced rows were backfilled on 2026-07-14, so the baseline exists:
- `Ask at First Sighting` (number) — the ask the FIRST time ORA ever saw the listing.
  WRITE IT ONCE. NEVER overwrite it on a re-sighting; overwriting destroys the signal.
- `First Sighted` (date) — when that first ask was recorded.
- `Price Delta vs First Ask` (formula, auto) — renders e.g. "CUT -12% ($2,650,000 to
  $2,332,000)". No manual arithmetic; read it.

On each run:
- Existing + unchanged: skip silently.
- Existing + PRICE CUT: update `Asking Price` and `Price / SF` ONLY. Leave
  `Ask at First Sighting` untouched (except a PROVISIONAL row being resolved, whose empty
  `Ask at First Sighting` is filled once per STEP 1B-B). The formula surfaces the delta. These LEAD the
  digest — a cut is the strongest motivation signal in the whole scan.
- Existing + RE-LIST (was Dead/Passed, now live again): flip Status, flag "RE-LIST".
- ONE EXCEPTION to the never-overwrite rule: if the stored first ask was OUR OWN
  recording error (e.g. a wrong figure scraped from an index page), correct BOTH
  `Asking Price` and `Ask at First Sighting`, and say so in Notes. Otherwise the
  formula fires a phantom "RAISED x%" signal on what was actually our data error —
  this happened on 3255 N 7th St Trafficway, corrected 2026-07-14.
- New: create a record. Never create duplicates. Also check the Acquisition
  Pipeline Tracker (bcfe4a03) so active deals are not re-surfaced as leads — against the
  STEP 0a fetch already in context (v2.8); do not re-pull it here.

RE-LIST vs REFRESH — DECISION RULE (v2.8; uses the STEP 1 DATE-BASIS). Flag "RE-LIST" ONLY
when one of these is true:
  (a) the matching row is Dead/Passed and the listing is live again (the rule above); or
  (b) the EARLIEST LISTED/DOM-derived date across ALL platforms carrying the listing is
      LATER than the row's `First Sighted` (re-entered on market after ORA first saw it).
      Use the earliest across sources — a Crexi copy posted after the Yardi copy ORA saw
      first is syndication lag, not a re-list.
  A changed platform ID / URL by itself (no dated evidence under (b)) is flagged
  "POSSIBLE RE-LIST — URL changed" in Notes, never "RE-LIST", and is not a motivation
  signal in the digest. (No field records every re-sighting — unchanged rows are skipped
  silently — so an "absent N days" test is not executable; do not attempt one.)
  An UPDATED-ONLY date newer than `First Sighted` is a REFRESH — never a re-list, never a
  new listing, never a motivation signal. ONLY when a re-list question actually arises on
  an existing row (price changed, URL/ID changed, or a newer UPDATED stamp) AND neither (a)
  nor (b) can be tested (DATE-BASIS UPDATED-ONLY/NONE on every source), write "RE-LIST
  UNDETERMINABLE" in Notes and count it in §7c — do not guess either way. Unchanged rows
  stay silent; they never generate this flag. For a NEW row, `First Sighted` = run date regardless of
  basis; the DATE-BASIS token records what the platform actually claimed.
- EXISTING ROW THAT IS AN OWN ASSET (v2.6): if the full active-set fetch contains a row
  the own-portfolio guard flags (e.g. legacy LoopNet-inbound rows for 2800-2826 Banwick,
  384-398 Morrison, 1100 Rarig; the 2026-09-05 Zettler row), do NOT update it as a lead.
  Report it once per run under "OWN-ASSET ROWS IN SOURCING LOG" for Gabriel to retire —
  never flip Status unattended.

STEP 5 — WRITE TO NOTION (canonical record — write BEFORE email)
CREATE-VERIFY (Deal Sourcing Log rows AND new Broker Relationships rows): if a create returns a grace/quota notice or no page ID, look for it — query the data source for the row's natural key (address / `Listing URL`; `Broker Name` + `Company / Brokerage`), then search by that key (search lags: a miss alone is not proof) — a match created at/after the create call is this run's row, use it; never blind-retry a create (it produced a duplicate). After a grace/quota notice with no match, do not retry: the create is UNVERIFIED — name it under the digest's coverage gaps. Quota errors → `notion-quota-fallback` skill.
Create/update Deal Sourcing Log records: Deal Name / Address; Metro / Submarket;
Source; **`Listing URL`** (the working public URL captured in Step 1 — field added
2026-08-12; before that STEP 1 was told to capture a URL for every listing and STEP 5 had
NOWHERE TO WRITE IT, so every run captured one and silently discarded it. That is why no
historical row can have its ask provenance reconstructed, and why STEP 5B's cross-write had
to fall back to document provenance. Write it on creation AND whenever a re-sighting loads a
different working URL; leave blank only when the ask came from an OM or a broker directly,
i.e. when there genuinely is no listing page); Status = "New Lead" (or existing status on
update); Asking Price;
**Ask at First Sighting + First Sighted (on creation only — EXCEPT a PROVISIONAL row:
`First Sighted` = creation date as usual, but `Ask at First Sighting` stays BLANK until the
run that verifies the ask; see STEP 1B-B)**; Total SF; Price / SF
(FUNCTIONAL — per Step 2.5); Year Built; Buy Box Score (100); **Verdict** (T1 PURSUE /
T2 WATCH / PASS / KILLED); **Floor Result** (PASS / FAIL-BASIS / FAIL-YIELD /
FAIL-BOTH / N/A — this is the gate outcome from Step 3A); Asset Type;
**`Construction Type`** (v2.8 — select; EXACT options: 'Masonry / Brick' · 'Block / CMU' ·
'Tilt-Up / Precast Concrete' · 'Hybrid (masonry + metal)' · 'Pre-Engineered Metal (PEMB)' ·
'Unknown — CONFIRM'. Write it on EVERY create and whenever this run resolved it; an
unresolved row MUST carry 'Unknown — CONFIRM' — that value plus `Listing URL` is the
handoff key ora-sourcing-construction-verify selects on, so a blank here silently drops
the row from the backstop. TWO EXCEPTIONS stay BLANK on purpose: a PROVISIONAL-UNRESOLVED
row (STEP 1B-B), and a T2 whose only working URL is crexi/loopnet (the verify task cannot
load those domains; name it in §7c instead)); Broker / Contact; Date Seen; Notes / Flags (gate outcome FIRST, then score breakdown, the
pre-mortem, the benchmark used and whether the deal sits near the floor line, plus
PRICE CUT / RE-LIST / REQUEST PRICE / PROVISIONAL / SUB-SCALE flags); Next Action
(what to do, and the decision rule — e.g. "decline if the ask implies over $105/SF").

*** STEP 5A — BROKER FIELD + BROKER RELATION (v2.7, 2026-09-19, Gabriel-directed) ***
Two writes per listing, both in the Deal Sourcing Log row you just created/updated:
  - `Broker / Contact` (text — this is the ACTUAL property name in the log's schema;
    verified 2026-09-19 against collection://9a6ae219-85a3-4621-899c-c757fd062f8b.
    It is NOT called "Broker / Source"): write `Name, Firm` — e.g.
    `Dan Sheeran Jr., NAI Ohio Equities`. Firm only when the agent is unknown:
    `AGENT NOT CAPTURED, NAI Ohio Equities`. Neither known: `AGENT NOT CAPTURED`.
    Multiple agents: `Name1, Name2, Firm`. NEVER a platform name (see Step 1).
  - `Broker (Linked)` (relation → collection://48e43778-b1f2-4b16-8f3c-0bf18f8642e9):
    link to the matching Broker Relationships row. The broker-side mirror of this
    relation is `Sourced Listings` — link ONE side and Notion populates the other; do
    not write both. Leave the relation EMPTY when the agent is `AGENT NOT CAPTURED` —
    never link a row to a firm-only placeholder, and never create a placeholder row.

MATCHING — NAME + FIRM IS THE KEY, NOT EMAIL. The 2026-09-19 executability test found
agent emails are essentially never published (0 of 5 detail pages), so an email-first
match would almost always miss and manufacture duplicates. Read the Broker
Relationships DB first, then match in this order, stopping at the first hit:
  1. exact `Broker Name` + exact `Company / Brokerage`;
  2. case-insensitive / whitespace-normalized `Broker Name` within the same firm;
  3. if `Email` is known AND a row carries that exact `Email`, that row wins outright.
NEVER CREATE A DUPLICATE WHEN A MATCH EXISTS. If two existing rows both match, link the
one with the higher `Tier` and report the duplicate pair in the digest — do not merge
them unattended.

CREATING A NEW BROKER ROW (only when no match exists). Write ONLY these properties —
they are the ones that actually exist in this DB (schema read 2026-09-19); inventing a
property or a select option will fail the write:
  - `Broker Name`          (title)        — the agent's full name. Required.
  - `Company / Brokerage`  (text)         — the firm.
  - `Email`                (email)        — ONLY if the page actually published it; else blank.
  - `Phone`                (phone_number) — ONLY if actually published; else blank.
  - `Markets`              (multi_select) — ONLY an option that ALREADY EXISTS:
        Columbus OH · Kansas City MO · Indianapolis IN · Maryland · Cleveland OH ·
        Nashville TN · Multi-Market · Des Moines IA · Cincinnati OH · Louisville KY ·
        Madison WI · Grand Rapids MI · Richmond VA
      (The last five were ADDED to the database by Gabriel's direction on 2026-09-19 — the
      original 8 kept their option ids and all 9 existing rows read identically before
      and after.) For a market with NO matching option — e.g. a new entry market — LEAVE
      `Markets` BLANK and name the market in `Notes`. NEVER invent a select option — the
      scan runs unattended and must not mutate the DB's schema. Report any such gap once
      per run in the digest ("Markets option missing for: <market>") so Gabriel can add it
      by hand.
  - `Tier`                 (select)       — `Tier 3 — Cold` for every new row (verify that
      exact option string, EM DASH included, exists before writing; the live options are
      `Tier 1 — Active` / `Tier 2 — Warm` / `Tier 3 — Cold` / `Inactive`). A broker the
      scan has merely observed is cold by definition — never open a row at a warmer tier.
  - `Notes`                (text)         — `Source: ora-deal-sourcing-scan; First seen: <listing date>`.
      *** There is NO `Source` property and NO `First Seen` property on this DB. That is
      why both go in `Notes`. `Date Added` is a created_time and is READ-ONLY. ***
  Do NOT write `Relationship Owner`, `Specialty`, `Contact Frequency`, `Last Contacted`,
  `Deals Referred`/`Deals Closed`, `Volume Closed ($)`, `HubSpot Contact Link` or
  `LinkedIn` — those are relationship-management fields a human owns, and the rollup /
  formula properties (`Listings Sent (Auto)`, `T1/T2 Listings (Auto)`, `LOIs (Auto)`,
  `Closed (Auto)`) are computed and must never be written.

CAP: at most 25 NEW broker rows per run. Linking to EXISTING rows is uncapped. On
hitting the cap, stop creating rows, still write `Broker / Contact` text for every
remaining listing, leave those relations empty, and report the overflow count and the
names not created in the digest's "Broker capture" section so the next run picks them up.

STEP 5B — CROSS-WRITE THE VERIFIED ASK TO THE ACQUISITION PIPELINE TRACKER
(added 2026-08-12, Gabriel-directed in-turn. Closes a real 36-minute-fuse defect: on
2026-08-11 this scan verified 4484 Robertson Road's published ask at $2,950,000
($116.14/SF marketed vs a Madison floor of $80.18 — FAIL-BASIS) and emailed it, but
nothing wrote it to the pipeline tracker. The tracker row was re-stamped 36 minutes
LATER, still recording the ask as "NOT YET KNOWN — verified null" and still instructing
the deal owner to ask the broker for a price on a call the next morning. Two ORA systems
held contradictory states because this task had a read of the tracker but no write.)

WHEN THIS RUNS: for every scanned candidate that matches an EXISTING row in the
Acquisition Pipeline Tracker (bcfe4a03-7e61-4ac1-a0bb-c44174fa138b). STEP 0a already
fetched that tracker (v2.8 — moved up front so 5B cannot be starved: on 2026-09-23 the
fetch was never executed and 5B silently did not run) — reuse that same fetch and the same
normalized-address match key (street-number + street-name, SF within 2%). Do NOT issue a
second pull. If STEP 0a FAILED, write nothing here and say so (receipt R11 FAILED).

*** "VERIFIED" IS A HARD PRECONDITION, NOT A LABEL. *** Write ONLY if this run actually
loaded a listing DETAIL page and read the ask off it. If the candidate is PROVISIONAL
(index-only or snippet-only, no detail page ever loaded — see Step 1's source ladder),
you have NOT verified anything: do NOT write, and say so in the digest. Writing an
index-page figure into the tracker would launder an unconfirmed number into the deal
record, which is strictly worse than leaving the field null. Precedent: in July, four
index-only Kansas City finds produced one confirmed, two corrected (including a price
understated by $125K) and one dead listing.

WRITE EXACTLY THESE THREE FIELDS, AND NOTHING ELSE:
  - `Listing Ask (Verified)`     (number/dollar) — the ask as published on the detail page,
                                                   OR read out of an OM (see provenance below).
  - `Listing Ask Verified On`    (date)          — the date THIS run read it. Always stamp.
  - `Listing Ask Source`         (url/text)      — WHERE THE FIGURE ACTUALLY CAME FROM. Never
                                                   leave this blank on a fresh write; never
                                                   invent or reconstruct it.

*** PROVENANCE MUST MATCH THE REAL SOURCE — A URL IS NOT ALWAYS AVAILABLE (amended 2026-08-12).
*** The original wording required "the working public URL captured in Step 1", which assumed every
verified ask comes from a web listing. It does not, and that assumption pressures a run into pasting
in a URL that does not actually publish the figure — fabricated provenance, the exact thing this field
exists to prevent. Worked case: 4484 Robertson Road's $2,950,000 was resolved by OCR of
`OM 4484 Robertson Road Madison, WI 53714_OCR.pdf`, while the only public listing (LoopNet) shows
*price upon request* and 403s to automated fetch — so a LoopNet URL there would have CONTRADICTED the
figure it claimed to source. Write whichever of these is true:
  - listing page verified this run  → the working public URL.
  - OM / broker document            → the document filename plus how it was read, e.g.
                                      `OM <file>.pdf (OCR-resolved YYYY-MM-DD)`. Say so plainly if
                                      no public listing publishes the ask.
  - broker stated it directly       → `Broker <name> <firm>, <channel> YYYY-MM-DD`.
Never cite a source that does not itself carry the number. If the only available URL shows
price-upon-request, that URL is NOT the provenance — the document or conversation is.

*** NEVER WRITE `Purchase Price`. *** This is the whole point of the three dedicated
fields, ratified by Gabriel 2026-08-12 over the simpler option of reusing `Purchase Price`:
  (a) `Purchase Price` feeds TWO formulas — `Price Per SF` (= Purchase Price / Total SF)
      and `Replacement Cost Ratio`. The latter is ALREADY KNOWN-BROKEN (still computing
      against $95/SF, an RCT v01-era denominator, vs RCT v03's $228-254; flagged to
      Gabriel 2026-08-11, unfixed pending his sign-off because it is governor-adjacent).
      A broker marketing figure written to `Purchase Price` would silently propagate into
      both, one of them wrong by ~2.5x, and would surface on six views as a deal price.
  (b) `Purchase Price` blank is MEANINGFUL — it is a verified null meaning "no underwritten
      or agreed price yet." Overwriting it destroys that signal.
  (c) `Purchase Price` already carries three different meanings across existing rows (ask /
      IC-memo recommended advance / blank-pending). Do not add a fourth.
An ask is broker marketing. `Purchase Price` is what ORA would or did pay. They are
different quantities and they now live in different fields — keep it that way.

ALSO NEVER WRITE, from this task, on a pipeline-tracker row: `Next Action`, `Stage`,
`LOI Status`, `PSA Status`, `Last Activity`, `Last Updated`, `Notes`, `Kill Reason`.
Those are posture and clock fields owned by the deal owner and by `ora-deal-aging-sla`,
which measures staleness against them — a scan touching them would reset the very clock
another task exists to watch. This mirrors that task's own standing guardrail.

OVERWRITE RULE (deliberately the OPPOSITE of `Ask at First Sighting`):
  - `Ask at First Sighting` in the Deal Sourcing Log is WRITE-ONCE — it is a historical
    baseline and overwriting it destroys the price-cut signal.
  - `Listing Ask (Verified)` is a CURRENT-STATE field — overwrite it freely whenever a
    newer run verifies a different published ask, and re-stamp `Listing Ask Verified On`.
    The stamp is what makes the figure trustworthy; a value without a fresh date is a
    figure of unknown age. Never write the value without the date.
  - If the ask is UNCHANGED, still re-stamp `Listing Ask Verified On` — "re-confirmed
    today" is a different and more useful fact than "last seen three weeks ago."

DO NOT CREATE PIPELINE-TRACKER ROWS. This step only UPDATES rows that already exist.
A scanned listing with no tracker row stays in the Deal Sourcing Log where it belongs;
promoting a lead into the acquisition pipeline is Gabriel's decision, not a scan's.

REPORT IT. In the Step 6 digest, add a short "Pipeline tracker cross-writes" line naming
each row written (deal, ask, verified-on) and each match that was SKIPPED as PROVISIONAL.
A silent write to the deal record is not acceptable — the digest is the audit trail.

FLAG THE CONTRADICTION, DO NOT RESOLVE IT. If the matched row's `Next Action` prose makes
a claim the verified ask contradicts — "price not yet known", "ask the broker for a
number", a stale price expectation — say so explicitly in the digest as a named finding,
LEADING the item. Do NOT edit the prose to fix it. That is the deal owner's call, and
rewriting it would erase the evidence that the two systems had diverged. (`ora-deal-aging-sla`
reports posture divergence the same way and for the same reason.)

STEP 6 — EMAIL DIGEST
Send TO ggoldberg@oxfordra.net ONLY — per the 2026-05-15 routing directive, re-ratified 2026-06-10: only the Daily Brief cc's egoldberg.
Email send path (per ORA standing rule — COM is PRIMARY):
  PRIMARY — Outlook COM via the shared helper. Write the HTML body to a temp file, then:
    powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1" -To "ggoldberg@oxfordra.net" -Subject "<subject>" -BodyFile "<temp>.html" -BodyFormat html -DedupTaskId "ora-deal-sourcing-scan" -DedupPeriodKey "<run date yyyy-MM-dd>"
    Exit 0 = sent (appended to _shared\send-log.txt). The helper uses the signed-in
    desktop Outlook profile — no OAuth/token. (When run inside the Bash tool, read the
    send-log "[OK] Sent" (or "[OK] DEDUP-SKIP") line to confirm; a trailing $LASTEXITCODE echo may report a
    shell error that is NOT the helper's exit code.)
  NO send fallback (Composio removed 2026-06-11). Contract mode (R-05): the helper dedups on task id + period + subject before Send() and itself retries exit 2/4 once, so the caller NEVER retries any exit code. <run date yyyy-MM-dd> = the date part of the run date computed once at run start (the same value used in the subject). On exit 1, 3 or 5: do NOT retry; flag it loudly in the run summary. On exit 6 (send state unknown — the message MAY have gone out; includes DEDUP-BLOCK/QUARANTINE and the fail-closed DEDUP-* refusals): do NOT retry and never resend; flag it loudly in the run summary for a human to check Sent Items, per rules.md §2. On any failed send, prefix the Notion Deal Sourcing Log digest title with ⚠️ [EMAIL FAILED] and
    log the failure — do NOT halt. The automation-health-monitor producer-beacon check surfaces
    the silent send to Gabriel.
  Outlook only — never Gmail; never route to Composio (gone) or Rube (shut down).
Subject (FIXED per run day so the R-05 dedup key matches a same-day rerun; no counts or other run-dependent text): "ORA Deal-Sourcing Scan — [date]". [date] = the run date computed once at run start with `date '+%A %Y-%m-%d'` (date part only), reused verbatim in every title, subject and body.
Count T1 PURSUE and T1-PENDING-PRICE SEPARATELY in the body and everywhere else; the body opens with the counts line "[N] pursue / [P] pending price / [M] flagged" (counts never go in the subject).
Body order:
  (1) PRICE CUT / RE-LIST flags first — the strongest motivation signals. Read them
      off the `Price Delta vs First Ask` formula; give prior ask, new ask, and %.
      If there are genuinely none, say so — but do NOT claim "no cuts" as a finding
      unless the first-ask baseline actually exists for the rows in question.
  (2) T1 PURSUE — gate-cleared AND priced. These are the only deals that earn an OM
      request. Address, metro, functional SF, ask, functional $/SF, the basis
      discount vs the [EST] benchmark, score, pre-mortem, URL.
  (3) T1-PENDING-PRICE — on-doctrine but unpriced; the basis test could not be run.
      Action is REQUEST PRICE, nothing more. For each, give the ask ABOVE WHICH IT
      DIES, so the broker call carries its own decision rule. Group the calls by
      brokerage — one call often covers several listings.
  (4) T2 WATCH — including every FAIL-BASIS deal, with the price at which it WOULD
      clear. State plainly that a high score does not override a failed floor.
  (5) One-line count of PASS/DECLINE logged.
  (6) Benchmark honesty note: which replacement-cost figure was used, that it is
      [EST] and PROVISIONAL, and any deal within ~3 ppt of the floor line.
  (7) COVERAGE — four sub-sections (v2.8; replaces the single "coverage gaps" list, which
      mixed real gaps with scope-by-design items):
      7a RUN RECEIPTS — one line per mandatory step R1-R14 (roster under RUN ORDER; R14 is
         written after the send, so the digest lists it as "pending — written last"):
         DONE (with the key count/finding) · HANDED-OFF (to what, how many) · FAILED
         (reason). R1 must state the capacity-gate finding and the rows it rests on. R8
         must state the handoff count to ora-sourcing-construction-verify. A step with no
         receipt line is a defect in the run, not a quiet week.
      7b SOURCE COVERAGE MATRIX — ten markets × F1 Yardi / F2 Crexi+LoopNet / F3 required
         broker-direct: each cell `N listings` · `0 (verified loaded)` · `blocked` ·
         `JS shell — not read` · `not tried`. Compact table.
      7c TRUE COVERAGE GAPS — anything that should have been read and was not: every
         non-green matrix cell, any FAILED receipt, T1 rows without a photo check,
         PROVISIONAL rows logged unresolved, carry-forward entries abandoned after 3 runs,
         RE-LIST UNDETERMINABLE count, a submarket that returned nothing. Named, never
         omitted.
      7d FILTERED BY DESIGN — not gaps, listed so they are visibly deliberate: Madison nil
         (normal — ~4 citywide — but ONLY when Madison's F1, F2 and F3 matrix cells are all
         loaded; a Madison nil with any unread family is a §7c gap, not by-design), Montgomery County MD skipped (not first Tuesday — STEP 0d),
         sub-scale exclusions (<10K SF or <$1M: address + SF + ask, one line each — the
         buy-box floor is unchanged; this list lets Gabriel override by hand), and the
         own-assets-seen-on-market list.
  (8) BROKER CAPTURE (added v2.7, 2026-09-19) — four counts, one short section:
        - listings scanned this run;
        - listings with a NAMED listing agent;
        - count of `AGENT NOT CAPTURED`, broken out by reason (aggregator blocked /
          detail page not loaded / no agent shown / OM-or-email with no agent named);
        - NEW Broker Relationships rows created this run.
      Also name here, when they occur: the 25-row cap being hit and the names not
      created; any missing `Markets` select option (e.g. a market outside the 13 current options);
      and any duplicate broker rows found while matching. This section is the audit
      trail for the 56.9% broker-name gap this version exists to close — report the
      counts even when they are bad, and never round them up.
  (9) Link to the Deal Sourcing Log.
If nothing new: send a brief "no new on-doctrine listings this week" note — a short,
honest digest is the correct output of a quiet week.

INTEGRITY RULES
- Report only verifiable listings with a working source URL. Never fabricate or
  infer a listing, price, or NOI. Mark every estimated figure "[EST]" and every
  provisional score component in Notes.
- Broker asking prices are unverified marketing figures — never present them as
  underwritten values.
- Do not contact any broker or counterparty. The scan identifies and ranks;
  outreach is a manual, principal-directed decision.
- Do not duplicate ora-distress-signal-monitor coverage (WARN/tax/bankruptcy).