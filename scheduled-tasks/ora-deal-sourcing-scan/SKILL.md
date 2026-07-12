---
name: ora-deal-sourcing-scan
description: Weekly on-market deal-sourcing scan (Tuesdays) — searches new industrial/flex listings across ORA's nine target markets, screens against the buy-box, scores with the Ranking-workbook methodology, dedupes against the Notion Deal Sourcing Log, writes new leads, flags repeat-listed/price-cut properties, emails a ranked digest. Restored 2026-07-07 — no replacement task applies the scoring rubric or writes to the Deal Sourcing Log. [MODEL: UNVERIFIABLE | checked 2026-07-08]
---

ORA ON-MARKET DEAL-SOURCING SCAN — weekly run (v1.0, restored 2026-07-07 after the CC/MCP registry was destroyed by a 2026-07-05 app reinstall; recovered from the 2026-06-22 fleet snapshot).

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
- Scoring methodology: mirrors 20260517_ORA_Investment-Candidates-Ranking_v01.xlsx
  (Methodology sheet), restated in full below so this prompt is self-contained.

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
- CAPACITY NOTE (review each run, re-verify current deal status before applying): while a Columbus acquisition is under contract, bandwidth favors the $1.5-6M sleeve over $7M+ checks. Score
  large deals normally but mark them "CAPACITY-GATED" in the digest.

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
- Also capture RE-LISTS and PRICE CUTS on properties already in the Deal Sourcing
  Log or previously ranked — both are motivation signals; note prior price and delta.
- Respect site terms: public pages and web-search results only. Never log in, never
  bypass paywalls or CAPTCHAs.
- Record for each candidate: address, metro/submarket, SF, asking price, $/SF,
  year built, occupancy/tenancy, clear height, parking, power (if stated), broker
  + firm, listing URL, date first seen.

STEP 2 — ELIGIBILITY GATE
Keep a candidate only if: (a) industrial/flex/office-warehouse product; (b) in a
target cluster; (c) within or plausibly within 10-80K SF and $1-10M; (d) no instant
disqualifier. Log filtered items with one-line reasons in the run notes; do not
write them to Notion. Unpriced listings in-cluster and on-product PASS the gate
(price discovery is a next action, not a disqualifier).

STEP 3 — SCORE (Fit Score 0-100, Ranking-workbook weights)
- Market — primary cluster (20): established cluster 20; entry-phase 14; edge of
  cluster 8; outside 0 (should have been filtered).
- Product — B/C industrial/flex (15): on-doctrine 15; mixed w/ heavy office 8;
  marginal 4.
- Basis vs replacement (20): asking $/SF >=25% below replacement (~$130-170/SF
  new-build tilt-up benchmark; use local figure when known) 20; 10-25% below 12;
  near replacement 5; above 0. Unpriced = 10 provisional, flag "REQUEST PRICE".
- Stabilized YoC (10): >8% achievable on stated/estimated NOI 10; 7-8% 6; <7% 2;
  unknown 5 provisional.
- Capital sleeve (10): $1.5-6M 10; $1-1.5M or $6-10M 6; outside 0.
- Value-add bias (5): vacancy/below-market rents/short WALT present 5; stabilized 2.
- Physical floors (10): meets power+parking+clear 10; one unknown 6; one failed 3;
  two+ failed 0.
- Mezz SF credit (5): no mezz dependency 5; mezz-inflated SF 0.
- Lease quality (5): PG or 3%+ escalations evident 5; unknown 3; weak 0.
Tier bands: T1 Pursue (>=60) — request OM immediately; T2 Negotiate (50-59) —
request OM/pricing, likely counter; T3 Watch (30-49) — log only, monitor for cuts;
T4 Decline (<30) — log with reason, no action.

PRE-MORTEM RULE (project standing instruction): for every T1/T2 candidate, write
one sentence stating the most likely reason the deal FAILS ORA underwriting
(basis, YoC, physical floor, tenancy, zoning, capacity). This ships in both the
Notion record and the digest. No candidate is presented without its failure mode.

STEP 4 — DEDUPE / DIFF
Fetch existing rows from the Deal Sourcing Log (Notion data source
9a6ae219-85a3-4621-899c-c757fd062f8b). Match on address (normalized) + metro.
- Existing + unchanged: skip silently.
- Existing + price cut or re-list: update the record, note prior price/date, add
  "PRICE CUT" or "RE-LIST" flag — these lead the digest.
- New: create a record. Never create duplicates. Also check the Acquisition
  Pipeline Tracker (bcfe4a03) so active deals are not re-surfaced as leads.

STEP 5 — WRITE TO NOTION (canonical record — write BEFORE email)
Create/update Deal Sourcing Log records: Deal Name / Address; Metro / Submarket;
Source = "On-Market Scan"; Status = "New Lead" (or existing status on update);
Asking Price; SF; $/SF; Fit Score; Tier; Broker / Firm; Listing URL; Date Seen;
Pre-Mortem (one-line failure mode); Notes / Flags (score breakdown, PRICE CUT /
RE-LIST / REQUEST PRICE / CAPACITY-GATED flags, provisional-score markers).

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
Subject: "ORA Deal-Sourcing Scan — [date] — [N] new / [M] flagged".
Body order: (1) PRICE CUT / RE-LIST flags first (motivation signals); (2) new T1
then T2 candidates — address, metro, SF, ask, $/SF, score, pre-mortem line, listing
URL; (3) one-line count of T3/T4 logged; (4) link to the Deal Sourcing Log. If
nothing new: send a brief "no new on-doctrine listings this week" note — a short,
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