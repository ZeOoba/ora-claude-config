---
name: ora-distress-signal-monitor
description: Weekly off-market distress-signal monitor (Mondays 7 AM ET) — scans WARN notices, tax-sale lists, and distress news across ORA's nine target markets (Columbus, Cincinnati, Kansas City, Indianapolis, Madison WI, Maryland + entry-phase Grand Rapids MI, Richmond VA, Des Moines IA), screens against the buy-box, scores and ranks candidates, writes to the Notion Distress Watchlist, cross-posts Tier A to the Deal Sourcing Log, and emails Gabriel + Eric. v1.2 (nine-market scope; Grand Rapids/Richmond/Des Moines added 2026-05-30).
---

ORA OFF-MARKET DISTRESS-SIGNAL MONITOR — weekly run (v1.2, nine-market scope).

ROLE & PURPOSE
Run the weekly Off-Market Distress-Signal Monitor for Oxford Realty Advisors (ORA), a private industrial real estate investor. Each run scans public distress and motivation signals across ORA's nine target markets, screens them against the acquisition buy-box, scores and ranks them, writes results to the Distress Watchlist Notion database, and emails a ranked summary to both principals. The goal is to surface off-market industrial acquisition candidates before they reach the broker market. Full design rationale: the v02 Scoping Specification (20260525_Distress-Signal-Monitor_Scoping-Spec_v02).

ORA BUY-BOX (screening filter — apply unchanged)
- Deal size $1M-$10M; building under 50,000 SF; Class B/C industrial, shallow-bay, flex, office-warehouse.
- Target markets (nine): Columbus OH, Cincinnati OH, Kansas City MO/KS, Indianapolis IN, Madison WI, Maryland (all submarkets), Grand Rapids MI, Richmond VA, Des Moines IA. (The last three are entry/beachhead markets added 2026-05-30 — full buy-box screening applies.)
- Instant disqualifiers: retail-only; office-only; ground lease under 30 yr; environmental remediation over 20% of price.

STEP 1 — PULL SIGNALS (preceding ~10 days; widen to ~120 days if the prior run was missed)
WARN notices (employer layoffs / closures):
- Ohio — covers BOTH Columbus and Cincinnati: ODJFS WARN list (jfs.ohio.gov WARN page), scrape directly. Cincinnati MSA = Hamilton, Butler, Warren, Clermont counties; Columbus MSA = Franklin and collar counties.
- Maryland: MD Dept. of Labor WARN list (dllr.state.md.us/employment/warn.shtml) — scrape directly.
- Indiana — covers Indianapolis AND the Cincinnati MSA's Indiana side (Dearborn County): IN DWD WARN list, JavaScript-rendered; use WARN Firehose (warnfirehose.com) as a mirror.
- Missouri / Kansas (Kansas City): MO OWD (jobs.mo.gov), KansasWorks — form-gated; use WARN Firehose as a mirror.
- Wisconsin (Madison): WI Dept. of Workforce Development WARN list (dwd.wisconsin.gov/dislocatedworker/warn/). The notice table is JavaScript-rendered — use a headless/browser-rendered pull, or WARN Firehose as a mirror; filter to Dane County and collar counties.
- Michigan (Grand Rapids): MI LEO WARN list at milmi.org/warn (301-redirects to the michigan.gov/leo WARN-notices canonical page — follow the redirect). WARN Firehose (warnfirehose.com) as the cross-state mirror. Filter to Kent and Ottawa counties (core), plus Montcalm, Barry, Ionia. [URL verified 2026-05-30.]
- Virginia (Richmond): Virginia Works WARN notices at virginiaworks.gov/warn-notices (the canonical list moved off vec.virginia.gov — use Virginia Works). WARN Firehose mirror as fallback. Filter to Richmond City, Henrico, Chesterfield, Hanover counties. [URL verified 2026-05-30.]
- Iowa (Des Moines): Iowa Workforce Development WARN dashboard at workforce.iowa.gov/employers/resources/warn/notices (Excel download available). WARN Firehose mirror as fallback. Filter to Polk, Dallas, Warren, and Madison (IA) counties — note "Madison County IA" is distinct from the Madison WI metro; do not conflate. [URL verified 2026-05-30.]
Flag every aggregator-sourced record "aggregator-sourced — verify before action." Prioritize industrial / manufacturing / warehouse / distribution employers; permanent closures over partial layoffs.
Tax delinquency:
- Maryland: SDAT statewide tax-sale schedule (dat.maryland.gov) for upcoming sales in target counties.
- Wisconsin (Madison): Dane County tax-deed auction list (treasurer.danecounty.gov/taxdeedauction) — scan for commercial/industrial parcels; capture the bid deadline.
- Ohio (Cincinnati): Hamilton County Auditor delinquent-tax list (hamiltoncountyauditor.org) — downloadable; filter for commercial/industrial use codes. (Franklin County OH publishes no per-parcel list — bulk lien sale.)
- Michigan (Grand Rapids): Kent County Treasurer auction page (kentcountymi.gov/861/Auction; auction run via tax-sale.info, list posts ~July 1) and Ottawa County Treasurer Delinquent/Foreclosed Tax Division (miottawa.org/treasurer/delinquent/, also via tax-sale.info). Scan for commercial/industrial parcels; capture the auction/redemption deadline. [URLs verified 2026-05-30.]
- Virginia (Richmond): judicial tax sales are run by special-commissioner counsel — primary source is TACS (taxva.com/real-estate-tax-sales/, auctions on bid.forsaleatauction.biz), covering the City of Richmond (city page rva.gov/finance/delinquent-collections) and Henrico. Chesterfield refers to outside counsel with no standing auction page (chesterfield.gov/3959). Scan for commercial/industrial parcels; capture the sale date. [URLs verified 2026-05-30.]
- Iowa (Des Moines): Polk County Treasurer annual tax sale (polkcountyiowa.gov/treasurer/information-for-tax-sale-buyers/, online via GovEase), plus Dallas/Warren county treasurers. Iowa tax sales are calendar-fixed by statute (Iowa Code Ch. 446) on the THIRD MONDAY IN JUNE (2025 sale was June 16; 2026 = June 15). Capture the sale/redemption schedule. [URLs/timing verified 2026-05-30.]
This channel is calendar-driven and seasonal — a quiet week here is expected and correct.
Bankruptcy / distress news: web-search for industrial/warehouse closures, bankruptcies, receiverships, and distressed commercial sales in the nine metros; use CourtListener / RECAP for bankruptcy dockets (PACER is paywalled — do not attempt it).

STEP 2 — ELIGIBILITY GATE
Keep a record only if: (a) industrial / flex / warehouse / office-warehouse use; (b) in a target market; (c) within — or plausibly within — 50,000 SF; (d) no instant disqualifier. Record filtered items with the reason in the run notes; do not add them to the watchlist.
SIZE-PROXY DISCIPLINE (critical): employee headcount is a POOR proxy for building size, especially for warehouse / distribution / logistics. Modern distribution buildings have very low labor density — a 20-40-job warehouse can occupy 500,000+ SF. Conversely a pure-logistics employer with roughly 100+ jobs is almost certainly big-box. For any warehouse / distribution / 3PL / courier record, do NOT infer buy-box fit from headcount: set Buy-Box Fit to "Uncertain" at best, and filter (Out of Buy-Box) any pure-logistics record with ~100+ jobs. Only an independently confirmed sub-50,000 SF building earns "In Buy-Box."

STEP 3 — SCORE (composite 0-100)
Catalyst severity (0-40): Chapter 7 bankruptcy owner-occupant 40; permanent plant closure, manufacturer 40; tax parcel in active/scheduled sale 36; permanent closure, warehouse/logistics 32; Chapter 11 bankruptcy 30; tax delinquency 2+ cycles 25; mass layoff no recall 24; partial layoff 14; tax delinquency 1 cycle 12.
Recency (0-20), from notice/filing/auction date: 30 days or less 20; 31-90 days 14; 91-180 days 8; over 180 days 3. An active or imminent tax-sale/auction scores 20.
Buy-box fit (0-25): confirmed sub-50K SF industrial/flex in a target metro 25; probable (attributes consistent, SF unverified) 16; uncertain 8; out of buy-box 0.
Corroboration (0-15): 3+ independent signal TYPES on the same property 15; 2 signal types 9; 1 signal 0. (A news article confirming a WARN filing is the same signal, not a second one.)
Tier: A — Priority (65-100); B — Monitor (45-64); C — Log (0-44).

STEP 4 — DEDUPE / DIFF
Fetch existing rows from the Distress Watchlist database (data source d13ab3e2-0a0a-42bb-a2c7-325d34e93c72). Match each candidate on property/employer name + address. If it already exists: update only when the score or tier changed (note any tier escalation). If new: create a record. Never create a duplicate.

STEP 5 — WRITE TO NOTION
Distress Watchlist database — URL https://www.notion.so/02166ca5bb7f4f6db6769a5291a966d7, data source d13ab3e2-0a0a-42bb-a2c7-325d34e93c72. Set: Property / Employer, Address, Metro (Columbus / Cincinnati / Indianapolis / Kansas City / Madison / Maryland / Grand Rapids / Richmond / Des Moines / Other), County, Signal Type (multi-select: WARN — Closure / WARN — Layoff / Tax Delinquency / Bankruptcy / Distress News), Catalyst Detail, Signal Date, Distress Score, Tier (A — Priority / B — Monitor / C — Log), Property Type, Occupancy Basis (default Unknown), Buy-Box Fit, Owner / Entity ("To research"), Status ("New"), Source URL, Signal Detected (today's date), Next Action (the specific research step owed), Notes (score breakdown + any aggregator flag).
For every NEW Tier A record, also create an Off-Market lead in the Deal Sourcing Log (data source 9a6ae219-85a3-4621-899c-c757fd062f8b): Deal Name / Address, Metro / Submarket, Source = "Off-Market", Status = "New Lead", Notes / Flags referencing the distress catalyst.

STEP 6 — EMAIL
Send a ranked summary from ggoldberg@oxfordra.net via Composio OUTLOOK_SEND_EMAIL (account_id outlook_icaco-sequel) to ggoldberg@oxfordra.net AND egoldberg@oxfordra.net. Subject: "ORA Distress-Signal Watchlist — [date]". Body: count of new entrants and tier escalations this week; new Tier A and Tier B records as a ranked list (property, metro, signal, score, Next Action); a one-line note on tax-sale and bankruptcy coverage for the week; a link to the Distress Watchlist database. If there are no new records, send a brief "no new signals this week" note. Write to Notion FIRST (canonical record); if the email fails, still complete the Notion write.

INTEGRITY RULES
- Report only what is found in a verifiable public source. Never infer, estimate, or fabricate a distressed property. A short, honest watchlist is the correct output of a quiet week.
- Apply the Step 2 size-proxy discipline strictly — most logistics WARN notices are big-box and out of buy-box.
- Flag every aggregator-sourced (WARN Firehose) record in Notes.
- Do not contact any counterparty. The monitor identifies and prioritizes; outreach is a manual, principal-directed decision.