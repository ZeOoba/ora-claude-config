---
name: ora-deal-sourcing-scan
description: Weekly on-market deal-sourcing scan (Tuesdays) — searches new industrial/flex listings across ORA's ten target markets, applies the basis/physical hard floors as a GATE, scores survivors, dedupes against the Notion Deal Sourcing Log, mechanically detects price cuts off the stored first-sighting ask, and emails a ranked digest. Restored 2026-07-07 — no replacement task applies the scoring rubric or writes to the Deal Sourcing Log. [MODEL: claude-opus-5 observed | checked 2026-08-12 via live-run transcript canary]
---

ORA ON-MARKET DEAL-SOURCING SCAN — weekly run (v2.5, 2026-08-11).

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
  (bcfe4a03) each run and say in the digest which way you found it.

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
  hybrid — see the Construction & envelope score in Step 3B), broker + firm,
  listing URL, date first seen.

  *** HOW TO ACTUALLY DETERMINE CONSTRUCTION TYPE (added 2026-08-04 — the previous
  instruction was just "LOOK: listing photos usually settle it in seconds", and on the
  2026-08-04 run ALL NINE market agents reported it as impossible and returned UNKNOWN
  for every candidate. UNKNOWN scores the same as PEMB (2/5), so that silently
  suppressed ~3 points on essentially the whole scan. The instruction was wrong, not
  the agents — WebFetch returns text only and cannot see images. Use this instead: ***
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
Source; **`Listing URL`** (the working public URL captured in Step 1 — field added
2026-08-12; before that STEP 1 was told to capture a URL for every listing and STEP 5 had
NOWHERE TO WRITE IT, so every run captured one and silently discarded it. That is why no
historical row can have its ask provenance reconstructed, and why STEP 5B's cross-write had
to fall back to document provenance. Write it on creation AND whenever a re-sighting loads a
different working URL; leave blank only when the ask came from an OM or a broker directly,
i.e. when there genuinely is no listing page); Status = "New Lead" (or existing status on
update); Asking Price;
**Ask at First Sighting + First Sighted (on creation only)**; Total SF; Price / SF
(FUNCTIONAL — per Step 2.5); Year Built; Buy Box Score (100); **Verdict** (T1 PURSUE /
T2 WATCH / PASS / KILLED); **Floor Result** (PASS / FAIL-BASIS / FAIL-YIELD /
FAIL-BOTH / N/A — this is the gate outcome from Step 3A); Asset Type; Broker /
Contact; Date Seen; Notes / Flags (gate outcome FIRST, then score breakdown, the
pre-mortem, the benchmark used and whether the deal sits near the floor line, plus
PRICE CUT / RE-LIST / REQUEST PRICE / PROVISIONAL / SUB-SCALE flags); Next Action
(what to do, and the decision rule — e.g. "decline if the ask implies over $105/SF").

STEP 5B — CROSS-WRITE THE VERIFIED ASK TO THE ACQUISITION PIPELINE TRACKER
(added 2026-08-12, Gabriel-directed in-turn. Closes a real 36-minute-fuse defect: on
2026-08-11 this scan verified 4484 Robertson Road's published ask at $2,950,000
($116.14/SF marketed vs a Madison floor of $80.18 — FAIL-BASIS) and emailed it, but
nothing wrote it to the pipeline tracker. The tracker row was re-stamped 36 minutes
LATER, still recording the ask as "NOT YET KNOWN — verified null" and still instructing
the deal owner to ask the broker for a price on a call the next morning. Two ORA systems
held contradictory states because this task had a read of the tracker but no write.)

WHEN THIS RUNS: for every scanned candidate that matches an EXISTING row in the
Acquisition Pipeline Tracker (bcfe4a03-7e61-4ac1-a0bb-c44174fa138b). STEP 4 already
fetches that tracker to avoid re-surfacing active deals as leads — reuse that same fetch
and the same normalized-address match key (street-number + street-name, SF within 2%).
Do NOT issue a second pull.

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