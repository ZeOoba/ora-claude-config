---
name: ora-daily-brief-6am
description: ORA Daily Brief — runs at 6 AM daily, compiles 9-section intelligence report, saves to Notion, emails ggoldberg@oxfordra.net and egoldberg@oxfordra.net
---

**[COMPOSIO MIGRATION 2026-05-08 — Rube EOL bridge]** All MCP routing on this task is pinned to the native Composio Platform connector (`mcp__8a611864-5cda-497f-baf9-6d3c02ab3404__COMPOSIO_*`), NOT the legacy Rube namespace (`mcp__d6315173-234c-4e6c-bea7-7f5e15d2bde5__RUBE_*`). Tool slugs (`OUTLOOK_SEND_EMAIL`, `OUTLOOK_CREATE_DRAFT`, `OUTLOOK_CREATE_ME_EVENT`, `HUBSPOT_*`, etc.) are byte-identical between stacks; only the MCP server prefix changes. Use the Composio path for Outlook (mail + calendar) and HubSpot. ORA does not use Google Workspace — no GCal/GSheets routing applies. (Notion writes can continue to use the native `mcp__c5f4869f-...__notion-*` MCP; QuickBooks reads can continue to use the native `mcp__52fa80c0-...` MCP.)

You are generating the Oxford Realty Advisors daily intelligence brief for Gabriel Goldberg, Principal at Oxford Realty Advisors. Today's date is available in your environment. Execute all 9 sections below, then save to Notion and send via email.

ORA context: ~600K SF shallow-bay industrial/flex, ~140 tenants, ~27 properties across OH, MD, IN, WI, MO, KS, TN. Acquisition focus: sub-$10M, shallow-bay, multi-tenant, below replacement cost.

---

## SECTION 1 — CRE NEWS
Search the last 24 hours for industrial/shallow-bay news in:
- OH (Columbus, Cincinnati, Cleveland, Dayton)
- MD (Baltimore Metro, DC Metro/Northern Virginia, I-270 Corridor)
- IN (Indianapolis Metro), MO/KS (Kansas City), WI (Madison)
- MI (Grand Rapids), VA (Richmond), IA (Des Moines) — entry/beachhead target markets added 2026-05-30
- TN (watch)

Sources: REBusinessOnline.com, ConnectCRE.com, GlobeSt.com, Commercial Observer, CoStar.
Filter for: new development, vacancy changes, major lease signings >50K SF, investment sales, zoning changes, logistics/e-commerce demand trends.
Format: [Source] [Location]: [Headline]. [1-sentence ORA relevance.]
Include 2-4 items.

## SECTION 2 — TRANSACTION ALERT
Search for industrial sale transactions: sub-$10M, shallow-bay/flex/office-warehouse, target markets, multi-tenant preferred, sub-50K SF per building preferred.
Sources: LoopNet, CoStar, REBusinessOnline, Crexi.
Flag ⚠️ any deal passing ORA's screen (sub-$10M, shallow-bay, target market, below replacement cost).
Format: [Address], [City State] | [SF] SF | $[Price] ($[$/SF]) | [Cap Rate if known] | Buyer/Seller
Include 2-3 items.

## SECTION 3 — MARKET PULSE

**Consumer of `ora-treasury-yield-prefetch` (producer fires 05:40 ET weekdays; this brief fires 06:04 ET). CANONICAL SOURCE as of 2026-05-25 is the Notion Ops Hub page `Rate Snapshot — Current` (page ID `35e6ecd8-9e59-814f-ae22-fe99464084d1`), NOT a SharePoint JSON file — Cowork scheduled-task sessions cannot reliably read or write `Claude_Workspace/_state/*.json`, so that legacy path is deprecated.** Branch deterministically on the `prefetch_status` value parsed from the page's machine-readable header block:

1. Fetch the Notion page `Rate Snapshot — Current` (ID `35e6ecd8-9e59-814f-ae22-fe99464084d1`) via `notion-fetch`. Parse the header block (`prefetch_status`, `fetched_at`, `prior_trading_day`, `holiday_offset`) plus the UST yield table, SOFR strip, spreads, and FedWatch section.

1a. **Mirror fallback (NEW 2026-05-31) — check BEFORE live-fetch.** If the `notion-fetch` in step 1 returns `ERR_FAILED` / connection error / page-not-found (i.e., Notion is unreachable, as on 2026-05-31), do NOT fall straight to live-fetch. First look for today's pre-flight mirror produced by `ora-connector-preflight-guard` at 05:25 ET: via the M365 connector `outlook_email_search` (or a Composio message list), find the most recent message to ggoldberg@oxfordra.net whose subject begins `✅ ORA Connector Pre-Flight — [today YYYY-MM-DD]` or `⚠️ ORA Connector Pre-Flight — [today YYYY-MM-DD]`. If found, parse the machine-readable JSON rate block embedded in that email body and use it as the Section 3 source — tag each cell `[MIRROR FALLBACK]` and cite the mirror's own `fetched_at`. When the mirror is used, the top-of-brief banner becomes `⚠️ RATE SNAPSHOT VIA MIRROR — Notion unreachable at brief time; Section 3 sourced from the 05:25 ora-connector-preflight-guard mirror email (fetched_at {…}).` instead of the "MISSING" banner. Only if NEITHER Notion NOR the mirror email is available do you proceed to live-fetch (step 4).

2. Compute `prefetch_age_minutes = now_ET − fetched_at`. Expected freshness window:
   - Weekday brief: the page should have been refreshed by the producer this morning (producer 05:40, brief 06:04) — expected age < 60 minutes.
   - Weekend brief (Sat/Sun): producer does not run weekends; expected age up to ~80 hours from the prior Friday 05:40.
   - Monday brief after a US federal holiday: expected age may extend to ~104 hours.

3. **GATE — emit a top-of-brief banner ABOVE Section 1** if any of the following hold (banner is mandatory and prominent; it is NOT silent fallback):

   | Condition | Banner content |
   |---|---|
   | Page missing / not found | `⚠️ RATE SNAPSHOT MISSING — Notion 'Rate Snapshot — Current' not found at brief time. Section 3 running in live-fetch fallback mode.` |
   | `prefetch_status == "FAILED"` | `⚠️ RATE PREFETCH FAILED — Producer reported FAILED at {fetched_at}; Section 3 values are prior-day carry-forward. Errors: {first 1-3 prefetch errors}.` |
   | `prefetch_status == "STALE_DATA"` | `⚠️ TREASURY SOURCE STALE — Source returned data ≥2 business days old. {prior_trading_day} carries forward; verify source health before market-sensitive decisions.` |
   | `prefetch_status == "SOURCE_DEGRADED"` | `⚠️ RATE PREFETCH PARTIAL — UST tenors OK; secondary sources (SOFR term / BBB OAS / FedWatch) partial. Affected cells marked n/a below.` |
   | `prefetch_age_minutes > expected_window_max` | `⚠️ RATE DATA STALE — Rate Snapshot last refreshed {fetched_at}; exceeds expected freshness window by {overshoot_min} min. Investigate ora-treasury-yield-prefetch run history.` |
   | All clear | NO banner. Section 1 starts the brief as normal. |

   Banner format in HTML email: red-bordered callout box, 14pt bold prefix, body in normal weight, with a link to the `Rate Snapshot — Current` page. In Notion brief: callout block, red icon.

4. **Render Market Pulse table:**
   - If `prefetch_status == "OK"` or `"SOURCE_DEGRADED"`: render directly from the Rate Snapshot page. Required cells: 5Y UST, 10Y UST, 30Y UST, 10Y-2Y spread, Overnight SOFR, Term SOFR 3M, Fed Funds target range, Next FOMC date, CME implied hold prob, BBB OAS, and STAG / PLD closes (sentiment proxies — NOT on the Rate Snapshot page; require a separate web_search). Mark any page cell shown as `—` or unavailable as `n/a`.
   - If a step-1a mirror was found, render the table from that mirror (cells tagged `[MIRROR FALLBACK]`) — do NOT live-fetch.
   - If the page is missing or `prefetch_status == "FAILED"` AND no step-1a mirror was found: live-fetch UST 2Y/5Y/10Y/30Y and overnight SOFR from FRED / U.S. Treasury / NY Fed, plus the next FOMC date and CME hold probability, directly. Tag every live-fetched cell `[LIVE FALLBACK]`.

5. Below the table, include 2–3 sentences on what the curve and CME implied path mean for ORA refi planning and acquisition cap rates. If a banner fired, prefix the commentary with: "Note: rate data freshness flagged above — interpret with caution."

Present as a table. Attribute each cell's source from the Rate Snapshot page `Source` columns (or the live source if `[LIVE FALLBACK]`).

## SECTION 4 — PORTFOLIO WATCH
Check Notion Operations Hub (page ID: 32b6ecd8-9e59-81f2-b329-df3fd0e25062):
4a: Did scheduled tasks run overnight? Any errors?
4b: Leases expiring in the next 30 days, and those 31–90 days out with no HubSpot renewal activity. PRIMARY SOURCE — read the most recent **ORA Lease Expiration Dashboard** page under the Operations Hub (produced every Monday by the `ora-lease-expiration-dashboard` task; it already carries 8 urgency windows, WALT, and renewal-probability data computed from HubSpot Contacts). Locate it via `notion-search` on the literal title `ORA Lease Expiration Dashboard` and use the newest. The Tenant DB data source `collection://b12f4cfd-a995-4755-8341-6435ae8173b4` returns schema-only on `notion-fetch` and is NOT reliably date-filterable via semantic search — use it only as a secondary cross-check for a specific named tenant, never as the primary expiration scan.
4c: Any delinquency AR >$0? Flag >30 days.
4d: Notion Acquisition Pipeline (search "acquisition pipeline"): deals with deadline in next 7 days? Stuck >14 days?
Format each: [Name] | [Property/Deal] | [Amount/Date] | [Status/Next Action]
If no flags: "✅ No items requiring immediate attention."

## SECTION 5 — OPS TIP
One actionable suggestion for ORA's software automation, file organization, or operational workflow. Rotate daily through: Zapier, HubSpot, Notion, QuickBooks, PM Platforms (Rent Manager/AppFolio/Yardi), Document Management, Claude/AI automation.
Format: Topic: [Domain] | Suggestion: [1-2 sentences] | Effort: [Low/Medium/High] | Time saved: [hrs/month]

## SECTION 6 — READING LIST
5 articles Gabriel should read today covering: portfolio growth, operational excellence, PropTech, capital markets, business strategy. Prioritize acquisition opportunities and market data with actionable implications.
Format: [#]. [Title] — [Publication]\n[URL]\n[Why relevant to ORA]

## SECTION 7 — LAW & REGULATORY WATCH
Search for new or revised laws/regulations (last 7 days) affecting CRE in ORA's markets:
Search: "commercial real estate law 2026" + [OH, MD, IN, MO, KS, WI, MI, VA, IA, TN]; "industrial zoning regulation"; "1031 exchange" legislation; "landlord tenant commercial law"; "property tax assessment commercial"; EPA environmental industrial regulations; FASB/SEC real estate rules.
Sources: congress.gov, state legislature sites, NAR legislative tracker, BOMA, law firm CRE client alerts (DLA Piper, Ballard Spahr, JLL Law).
Format: [Jurisdiction] [Law/Bill]: [What changed]. [ORA impact — 1 sentence.] Status: [Enacted/Proposed/Effective date]
If nothing material in 7 days, report the most recent significant change and current status.
Include 2-3 items.

## SECTION 8 — SHALLOW BAY CASE STUDY
Find 1 real case study, project spotlight, or operational lesson from an actual shallow-bay/flex operator website. Rotate through: brennanllc.com, basisindustrial.com, stagindustrial.com, seagisproperty.com, linklogistics.com/insights, aresindustrialreit.com, lbarealty.com. Look for press releases, project spotlights, investor presentations, blog posts, deal announcements.
Format:
Operator: [Company]
Source URL: [Direct URL]
Topic: [Acquisition/Development/Leasing/Operations/Capital Markets]
Summary: [3-4 sentences: what they did, the market, asset type, outcome/thesis]
ORA Takeaway: [1 sentence — what Gabriel can apply to ORA's strategy]

## SECTION 9 — COMPETITIVE INTELLIGENCE
Run targeted searches for edge information:
1. New shallow-bay listings last 48 hrs on Crexi/LoopNet in target markets not yet in ORA pipeline
2. Competitor acquisitions this week: Brennan, Basis Industrial, STAG, Seagis, LBA, Link Logistics in target markets
3. Off-market signals: industrial auctions, bankruptcy sales, motivated sellers in target markets
4. Broker intel: new industrial broker hires/moves in target markets affecting ORA deal flow
5. Tenant demand signals: employer expansions/relocations driving warehouse demand in 12-24 months
6. Supply pipeline: new industrial park approvals or rezonings adding supply to ORA submarkets
7. Lender activity: new bridge/permanent lenders entering shallow-bay, or tightening terms
Format per item:
Category: [type]
Finding: [Specific, sourced, 2-3 sentences]
ORA Action: [What to do — specific next step]
Include minimum 3, maximum 6 items. Prioritize items needing action within 72 hours.

---

## AFTER GENERATING ALL 9 SECTIONS:

**Step 1 — Save to Notion (v1.1 publication-guard pattern — see `_shared\PUBLICATION_GUARD.md`):**
1. Create a new page under the Operations Hub (parent page ID: 32b6ecd8-9e59-81f2-b329-df3fd0e25062) with title "Daily Brief — [YYYY-MM-DD]" and the full brief as content.
2. Capture `pages[0].id` from the response.
3. If `id` is missing/errored, retry the `notion-create-pages` call ONCE.
4. After success, verify by calling `notion-search` with the literal title and confirming the page ID matches.
5. If Steps 1-4 all fail, AUTO-SEND an Outlook email to ggoldberg@oxfordra.net cc egoldberg@oxfordra.net with subject `❌ ora-daily-brief-6am PUBLICATION FAILED — [YYYY-MM-DD]` and the full brief in the body (auto-send permitted on meta-failure path).

**Step 2 — Send HTML Email:**
Format the complete brief as clean HTML and send via native Composio `OUTLOOK_SEND_EMAIL` through `mcp__8a611864-5cda-497f-baf9-6d3c02ab3404__COMPOSIO_MULTI_EXECUTE_TOOL` using:
- `to`: `ggoldberg@oxfordra.net`
- `cc_emails`: `["egoldberg@oxfordra.net"]`
- `subject`: `ORA Daily Brief — [DAY, MONTH DATE YEAR]`
- `is_html`: `true`
- `save_to_sent_items`: `true`
- `user_id`: `"me"`
- `body`: Full brief formatted as HTML with clear section headers, tables where applicable, and ⚠️ flags preserved

Rube namespace `mcp__d6315173-...__RUBE_*` reached end-of-life 2026-05-15 — do NOT attempt RUBE_MULTI_EXECUTE_TOOL. The native Composio path is the only supported route.

**Composio availability pre-check (do this before Step 2):** confirm the Composio MCP tools (`mcp__8a611864-…__COMPOSIO_*`) are actually loaded this run. If they are not (server disconnected), skip the send attempt entirely and go straight to the email-failure handling below — do not stall retrying an unreachable tool.

**If email delivery fails** — including the case where Composio is disconnected and `OUTLOOK_SEND_EMAIL` is unreachable: (a) log the failure reason inline in a `## DELIVERY LOG` section at the bottom of the brief, and (b) update the Notion page created in Step 1 so its title is prefixed with `⚠️ [EMAIL FAILED] ` — this visually flags the undelivered brief in the Operations Hub so it is not missed.

**If Notion publication fails:** log the failure reason inline per the Step 1 publication guard. Do not retry any delivery more than once.
