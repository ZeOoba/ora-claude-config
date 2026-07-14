---
name: ora-deal-sourcing-scan
description: Weekly on-market deal-sourcing scan (Tuesdays) — searches new industrial/flex listings across ORA's nine target markets, applies the basis/physical hard floors as a GATE, scores survivors, dedupes against the Notion Deal Sourcing Log, mechanically detects price cuts off the stored first-sighting ask, and emails a ranked digest. Restored 2026-07-07 — no replacement task applies the scoring rubric or writes to the Deal Sourcing Log. [MODEL: UNVERIFIABLE | checked 2026-07-08]
---

ORA ON-MARKET DEAL-SOURCING SCAN — weekly run (v2.3, 2026-07-14).

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
re-listed / price-cut) properties in ORA's nine target markets, screens them against
the buy-box, scores survivors, writes them to the Notion Deal Sourcing Log, and emails
a ranked digest. This task covers the ON-MARKET channel; the
off-market distress channel is owned by ora-distress-signal-monitor — do not
duplicate its WARN/tax-sale/bankruptcy work.

CANONICAL INPUTS
- Target markets: the single source of truth is the canonical target-markets.json.
  Read it each run from EITHER of these (first that loads wins):
    1) C:\Users\Owner\ora-skills\target-markets.json  (authoritative — the canonical ora-skills git repo; repointed 2026-07-09 when the third clone at Claude_Workspace\01_Workspace\.claude\skills\ was archived per THIRD_CLONE=RECONCILE-COMMITS)
    2) skills/target-markets.json  (local mirror in this task folder — materialized 2026-07-09; refresh it whenever the canonical file changes)
  The file carries the nine clusters with submarkets, demand drivers, and market
  metrics (incl. sale $/SF benchmarks usable for the basis-vs-replacement score).
  ONLY IF BOTH are unreachable, fall back to the embedded list below and flag
  staleness in the email. Nine clusters: Columbus OH, Cincinnati OH, Kansas City
  MO/KS, Indianapolis IN, Madison WI, Maryland Baltimore/DC (established) +
  entry-phase Grand Rapids MI, Richmond VA, Des Moines IA.
- Scoring methodology: restated in full below so this prompt is self-contained.
  CITATION CORRECTED 2026-07-14 — this task previously cited
  "20260517_ORA_Investment-Candidates-Ranking_v01.xlsx (Methodology sheet)". THAT FILE
  AND THAT SHEET DO NOT EXIST. The live workbook is
  `OneDrive/Investment Candidates -- 2026/20260609_ORA_Investment-Candidates-Ranking_v05a-VintageVerified.xlsx`
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
  ground lease <30 yr; environmental remediation >20% of price; outside the nine
  clusters; institutional Class A pricing (>$130/SF without exceptional justification).
- CAPACITY NOTE (re-verify current deal status EVERY run before applying): IF a
  Columbus acquisition is under contract, bandwidth favors the $1.5-6M sleeve over
  $7M+ checks — score large deals normally but mark them "CAPACITY-GATED" in the
  digest. STATUS AS OF 2026-07-14: NOT ACTIVE. The E. Fulton acquisition was
  TERMINATED (now a lender-note/foreclosure track), so no Columbus deal is under
  contract and NO candidate should be marked CAPACITY-GATED. Do not apply this gate
  on the strength of this note alone — check the Acquisition Pipeline Tracker
  (bcfe4a03) each run and say in the digest which way you found it.

STEP 1 — PULL NEW LISTINGS (preceding ~8 days; widen to ~30 if prior run missed)
For each of the nine clusters, web-search for newly listed industrial/flex product:
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
     Cushman Thalhimer; Des Moines — CBRE Hubbell, R&R Realty, NAI Iowa.
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
- SUBMARKET COVERAGE (do NOT skip): the KS side of Kansas City (Lenexa, Olathe, Shawnee, Overland
  Park) and Maryland's Howard County (Columbia, Jessup, Elkridge) + Anne Arundel/Hanover.
  Run these explicitly through the step-1 aggregators / Claude-in-Chrome, not just
  Crexi/LoopNet. If a submarket genuinely yields no verifiable for-sale listing, state
  that in the email's coverage-gaps note rather than omitting it silently.
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
  hybrid — see the Construction & envelope score in Step 3B; if the listing does not
  state it, LOOK: listing photos and street view usually settle it in seconds, and
  it is worth 3 points), broker + firm, listing URL, date first seen.

STEP 2 — ELIGIBILITY GATE
Keep a candidate only if: (a) industrial/flex/office-warehouse product; (b) in a
target cluster; (c) within or plausibly within 10-80K SF and $1-10M; (d) no instant
disqualifier. Log filtered items with one-line reasons in the run notes; do not
write them to Notion. Unpriced listings in-cluster and on-product PASS the gate
(price discovery is a next action, not a disqualifier).

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
  `Ask at First Sighting` untouched. The formula surfaces the delta. These LEAD the
  digest — a cut is the strongest motivation signal in the whole scan.
- Existing + RE-LIST (was Dead/Passed, now live again): flip Status, flag "RE-LIST".
- ONE EXCEPTION to the never-overwrite rule: if the stored first ask was OUR OWN
  recording error (e.g. a wrong figure scraped from an index page), correct BOTH
  `Asking Price` and `Ask at First Sighting`, and say so in Notes. Otherwise the
  formula fires a phantom "RAISED x%" signal on what was actually our data error —
  this happened on 3255 N 7th St Trafficway, corrected 2026-07-14.
- New: create a record. Never create duplicates. Also check the Acquisition
  Pipeline Tracker (bcfe4a03) so active deals are not re-surfaced as leads.

STEP 5 — WRITE TO NOTION (canonical record — write BEFORE email)
Create/update Deal Sourcing Log records: Deal Name / Address; Metro / Submarket;
Source; Status = "New Lead" (or existing status on update); Asking Price;
**Ask at First Sighting + First Sighted (on creation only)**; Total SF; Price / SF
(FUNCTIONAL — per Step 2.5); Year Built; Buy Box Score (100); **Verdict** (T1 PURSUE /
T2 WATCH / PASS / KILLED); **Floor Result** (PASS / FAIL-BASIS / FAIL-YIELD /
FAIL-BOTH / N/A — this is the gate outcome from Step 3A); Asset Type; Broker /
Contact; Date Seen; Notes / Flags (gate outcome FIRST, then score breakdown, the
pre-mortem, the benchmark used and whether the deal sits near the floor line, plus
PRICE CUT / RE-LIST / REQUEST PRICE / PROVISIONAL / SUB-SCALE flags); Next Action
(what to do, and the decision rule — e.g. "decline if the ask implies over $105/SF").

STEP 6 — EMAIL DIGEST
Send TO ggoldberg@oxfordra.net ONLY — per the 2026-05-15 routing directive, re-ratified 2026-06-10: only the Daily Brief cc's egoldberg.
Email send path (per ORA standing rule — COM is PRIMARY):
  PRIMARY — Outlook COM via the shared helper. Write the HTML body to a temp file, then:
    powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1" -To "ggoldberg@oxfordra.net" -Subject "<subject>" -BodyFile "<temp>.html" -BodyFormat html
    Exit 0 = sent (appended to _shared\send-log.txt). The helper uses the signed-in
    desktop Outlook profile — no OAuth/token. (When run inside the Bash tool, read the
    send-log "[OK] Sent" line to confirm; a trailing $LASTEXITCODE echo may report a
    shell error that is NOT the helper's exit code.)
  NO send fallback (Composio removed 2026-06-11). On a non-zero COM exit: retry once; if it
    still fails, prefix the Notion Deal Sourcing Log digest title with ⚠️ [EMAIL FAILED] and
    log the failure — do NOT halt. The automation-health-monitor producer-beacon check surfaces
    the silent send to Gabriel.
  Outlook only — never Gmail; never route to Composio (gone) or Rube (shut down).
Subject: "ORA Deal-Sourcing Scan — [date] — [N] pursue / [P] pending price / [M] flagged".
Count T1 PURSUE and T1-PENDING-PRICE SEPARATELY in the subject and everywhere else.
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
  (7) Coverage gaps, named explicitly — a submarket that returned nothing gets said
      out loud, never silently omitted.
  (8) Link to the Deal Sourcing Log.
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