---
name: daily-brief
description: 'Oxford Realty Advisors daily morning intelligence brief. Covers CRE news, industrial transactions, market rates, portfolio watch, ops tip, reading list, CRE law/regulatory watch, shallow bay case study, and competitive intelligence. Use when the user says: daily brief, news, morning brief, CRE news, what''s happening today, what should I know. v2.14 (2026-09-19: Sections 1/2/7/9 now fetch a tested fixed source list directly and keep only items whose date is read from the source, with mandatory [DATE UNVERIFIED] tagging; Section 2 declared thin by design because LoopNet/CoStar/Crexi are blocked). v2.13 (2026-09-12: Section 3 FRED prologue table mapped "30-Day SOFR" to SOFR30DAYAVG instead of overnight SOFR, added a separate SOFR (overnight) row, fixed the T+1 lag caveat, and added Rate Snapshot prefetch_status/fetched_at staleness disclosure — OI-283)'
---

You are generating the Oxford Realty Advisors daily intelligence brief. Execute all 9 sections in sequence and present as a structured report. Target length: concise but complete.

---

## OUTPUT FORMAT

# ORA Daily Brief — \[DAY\], \[MONTH DATE, YEAR\] — \[TIME\]

## 1. CRE NEWS

\[0-4 dated items\]

## 2. TRANSACTION ALERT

\[0-3 dated items\]

## 3. MARKET PULSE

\[Rate snapshot\]

## 4. PORTFOLIO WATCH

\[Operational flags\]

## 5. OPS TIP

\[One actionable suggestion\]

## 6. READING LIST

\[5 articles with 1-line summaries\]

## 7. LAW & REGULATORY WATCH

\[New or revised laws/regulations affecting CRE\]

## 8. SHALLOW BAY CASE STUDY

\[1 operator case study from a real company website\]

## 9. COMPETITIVE INTELLIGENCE

\[Edge information for shallow bay / Mid-Atlantic / Midwest\]

---

## SECTION 0 — PRE-FLIGHT SCHEMA INTEGRITY CHECK (Patch 7, v2.2 — added 2026-04-27)

Before generating any brief content, run this 60-second integrity probe. The check exists because Section 4b/4c depend on the Tenant Database schema, and a deletion of any required property in Notion would otherwise fail the daily brief silently.

**Procedure:**

1. Call `notion-fetch` with `id="collection://b12f4cfd-a995-4755-8341-6435ae8173b4"` (Tenant Database data source ID — NOT the wrapper ID `8dbbaec0...`).

2. **Happy path (fetch succeeds):**
   - Verify the schema contains at minimum these required properties: `Tenant Name` (title), `Lease Status` (select), `AR Balance` (number), `Lease Expiration` (date), `Property Address` (select).
   - Verify the rollups `Interaction Count` (count) and `Last Interaction Date` (latest_date) are present and target `collection://3417d600-eace-497b-b30a-16df4ef00d2e`.
   - If all checks pass: continue silently to Section 1. Do NOT mention the probe in brief output. Do NOT email. Daily success is silent.

3. **Failure path (fetch returns HTTP 400 / validation_error / any error, OR a required property is missing):**
   - This is a real corruption signal — not the wrapper-ID routing quirk (resolved 2026-04-27, see Database ID Map). The data source ID does not error on routing alone.
   - **Step A:** Post a Notion comment on the Operations Hub page `32b6ecd8-9e59-81f2-b329-df3fd0e25062` with the exact error payload, timestamp, and a link to the Database ID Map (https://www.notion.so/34f6ecd89e59811aa961f21fd2680744).
   - **Step B:** Send an alert email via Outlook COM — the SOLE send path (Composio retired 2026-06-11; there is NO fallback). Run via Desktop Commander `start_process`:
     - `powershell -ExecutionPolicy Bypass -File "C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1" -To "ggoldberg@oxfordra.net" -Subject "[ALERT] Tenant DB schema integrity failure — [today's date]" -BodyFile "<path to HTML body file>" -BodyFormat html`
     - No cc. Alerts are automated outputs → ggoldberg@oxfordra.net ONLY (routing canon 2026-06-10; the cc-Eric exception applies solely to the Daily Brief email itself).
     - Body: HTML with error code/message, request ID, timestamp, missing-property names if applicable, and recommendation to inspect Notion UI.
     - On non-zero exit: retry once, then record the send failure in the Step A Notion comment — do NOT halt the brief.
   - **Step C:** Continue with the brief. Section 4b/4c will use the graceful-degradation pattern (Patch 4) automatically. Sections 1, 2, 3, 5, 6, 7, 8, 9 are unaffected.

4. **Idempotency:** This probe runs every brief cycle. If the same failure recurs across multiple days, the daily emails will repeat — that is intentional. Suppress duplicate-day comments on the Operations Hub by checking for an existing same-day integrity-failure comment before posting (skip if already present).

**Why this lives here:** A separate 5 AM scheduled task was the original design but cannot be created from inside a scheduled-task session. Folding the probe into the 6 AM brief gives the same single-day alert window with one fewer moving part.

---

## FIXED SOURCE LIST (v2.14 — added 2026-09-19; live test evidence and drop reasons: `references/source-test-2026-09-19.md`)

**Why.** WebSearch has no last-24-hours filter and returns undated aggregator pages, so a search-only run cannot tell a fresh item from a stale one. Sections 1, 2, 7 and 9 therefore FETCH the sources below directly and keep only items whose date is READ from the fetched page or feed.

**Window.** Timestamped items: the 24 hours ending at run start (ET; convert `+0000` to ET). Day-only dates: the run date and the prior calendar day (ET). Section 7: 7 days. Filter every item on its OWN date, never by list position (Bisnow D.C. is not date-sorted).

**Method.** WebFetch each URL in A with the prompt: `List every item with its publication date/time and headline verbatim. State the newest and oldest date.` Use curl, never WebFetch, for the two APIs in B (WebFetch cannot take an 8 MB JSON). Never `curl -k`.

**A. News (Sections 1, 2, 9) — WebFetch:**
1. REBusinessOnline — `https://rebusinessonline.com/feed/` (timestamps; NATIONAL, keep target-market items); day-dated backup `https://rebusinessonline.com/category/industrial/`
2. ConnectCRE — `https://www.connectcre.com/feed/` (thin, about 2 hours deep)
3. Commercial Observer — `https://commercialobserver.com/feed/`
4. Bisnow — `https://www.bisnow.com/rss` (Market and Category tags) and `https://www.bisnow.com/washington-dc` (DC/NoVA/MD)
5. Indianapolis Business Journal — `https://www.ibj.com/real-estate`
6. Richmond BizSense — `https://richmondbizsense.com/feed/`
7. Business Record, Des Moines — `https://www.businessrecord.com/feed/` (general business; keep RE/industrial)
8. BizTimes — `https://www.biztimes.com/feed/` (MILWAUKEE: a Wisconsin proxy, not Madison — label it as such)
9. Section 9 competitor news — `https://basisindustrial.com/` (home page news list, dates as `M.D.YY`; sparse)

**B. Law/regulation (Section 7) — curl:**
1. Kansas — `https://www.kslegislature.gov/li/api/v13/rev-1/bill_status/` (about 8 MB JSON; filter locally on `HISTORY[].occurred_datetime` inside the 7-day window). Outside session this is empty (newest action 2026-05-05 as of 2026-09-19): print `no Kansas action since {newest date}`, a verified null, not a gap.
2. Federal Register — `https://www.federalregister.gov/api/v1/documents.json?per_page=20&order=newest&conditions%5Bterm%5D={term}&conditions%5Bpublication_date%5D%5Bgte%5D={run date minus 7 days}` (percent-encode the brackets; spaces as `+`). Run exactly these five terms, one call each: `commercial+real+estate`, `industrial+property`, `opportunity+zone`, `landlord+tenant`, `1031+exchange`. Low precision — keep only items that actually touch CRE, industrial, landlord-tenant, tax or environmental rules. A response with `count` 0 has NO `results` key: treat that as a verified empty result, not an error. Counted once toward B's 2 URLs however many terms ran.

OH, MD, IN, MO, WI and TN legislatures expose no fetchable dated activity surface (tested 2026-09-19). Cover them by WebSearch only, and tag each item `[DATE UNVERIFIED]` unless a fetched bill or statute page shows the action date.

**NOT built on:** GlobeSt and every bizjournals.com / Business First title (403 bot challenge); LoopNet, CoStar, Crexi (blocked). **Section 2 stays thin by design** — closed-sale price, SF, cap rate, buyer and seller sit behind those sources. Do not pad it and do not infer a price or cap rate from a headline. Five target clusters have no working local source (OH, MO/KS, MI, KY, TN) and two are partial (MD: DC/NoVA only, no Baltimore; WI: Milwaukee proxy only, no Madison); the national feeds carry them.

**Date-verification rule.** Every COUNTED item in Sections 1, 2, 7 and 9 carries a date read from the fetched source. An item whose date cannot be verified — WebSearch-only, an aggregator copy, an article page showing no date — may be printed ONLY with the `[DATE UNVERIFIED]` tag, on a separate closing line of its section (`Unverified-date leads:`, at most 2). Such a lead NEVER counts toward the section's item count or minimum, never carries a ⚠️ flag, and never drives an ORA Action. A WebSearch hit becomes a counted item only when WebFetch of the article itself shows its date. If a section has no dated items, print its empty-state sentence, never tagged filler. WebSearch stays a supplement for the market and state gaps above. Section 7 is the one exception: bill and statute pages there often confirm a measure exists without showing its action date, so a Section 7 item may be counted with the tag attached.

**Empty windows are normal.** A feed with zero in-window items is expected on weekends and Mondays and is reported, not padded.

**Source status (mandatory, last line of Section 9).** `Source status: {n}/13 URLs fetched (11 in A + 2 in B) — unavailable this run: {names or none} — zero in-window items: {names or none}.` A listed source that returns non-200, a bot challenge, or nothing in-window is reported by name. A source that could not be checked must never read as "nothing happened".

---

## SECTION 1 — CRE NEWS

> Geographic scope is governed by `target-markets.json` (v1.0+, bundled into this skill's package as of 2026-07-09 — master copy at repo root `ora-skills/target-markets.json`). Keep the list below in parity with that file's clusters + acceptable_states.

Using the FIXED SOURCE LIST (A), find significant industrial/shallow-bay news dated inside the window in:

- OH (Columbus, Cincinnati, Cleveland, Dayton)
- MD (Baltimore Metro, DC Metro/Northern Virginia, I-270 Corridor)
- IN (Indianapolis Metro)
- MO/KS (Kansas City Metro)
- WI (Madison)
- MI (Grand Rapids) — entry/beachhead target, added 2026-05-30
- VA (Richmond) — entry/beachhead target, added 2026-05-30
- IA (Des Moines) — entry/beachhead target, added 2026-05-30
- KY (Louisville) — entry/beachhead target, added 2026-08-05
- TN (pipeline/watch market)

Sources: the FIXED SOURCE LIST (A) only, plus WebSearch to fill the market gaps that list names, each WebSearch item subject to the date-verification rule. GlobeSt, bizjournals.com and CoStar are blocked — an item seen only as a search snippet from them is `[DATE UNVERIFIED]` unless a fetched page shows its date.

Filter for: new development announcements, vacancy changes, major lease signings (&gt;50K SF), investment sales, policy/zoning changes, port/logistics/e-commerce demand trends.

Format: \[Source\] \[Location\]: \[Headline\]. \[1-sentence relevance to ORA.\]

If fewer than 2 dated items exist, print those and `No further dated items in fetched sources for {window}` — never fill to 2 with undated material.

---

## SECTION 2 — TRANSACTION ALERT

Search for industrial sale transactions matching ORA criteria:

- Sub-$10M total consideration
- Shallow-bay, flex, office-warehouse product type
- Target markets: OH, MD, IN, MO, KS, WI (Columbus, Cincinnati, Baltimore/DC, Indianapolis, Kansas City, Madison) + entry-phase MI (Grand Rapids), VA (Richmond), IA (Des Moines), KY (Louisville); TN watch
- Multi-tenant preferred; sub-50,000 SF per building preferred

Include when available: Price, SF, price/SF, cap rate, buyer, seller, broker. Sources: the FIXED SOURCE LIST (A). LoopNet, CoStar and Crexi return 403 to this host — do not cite them. **This section stays thin by design:** press-release sale items usually state SF and buyer but not price or cap rate. Print only what the fetched item states, mark absent fields `n/d`, and if no in-window sale meets ORA's box print `No qualifying sub-$10M sale in fetched sources for {window}` — never pad, never infer price or cap rate. Flag with ⚠️ any deal that would have passed ORA's investment screen.

Format: \[Address\], \[City State\] | \[SF\] SF | $\[Price\] ($\[$/SF\]) | \[Cap Rate\] | Buyer/Seller

---

## SECTION 3 — MARKET PULSE

**FRED Rates Prologue (Patch 8, v2.3 — 2026-04-28):** Before fetching from treasury.gov, pull authoritative series directly from the FRED CSV API (no API key required for public series). These values are the canonical source — do NOT estimate or fall back to training-data priors.

For each series below, call `web_fetch` on `https://fred.stlouisfed.org/graph/fredgraph.csv?id={SERIES_ID}`. Parse the CSV: iterate from the last row upward and take the first row where the value column is not `"."` (blank placeholder). Extract that row's date and value.

| Rate | FRED Series ID | Notes |
|---|---|---|
| 5-Year Treasury | `DGS5` | Daily, constant maturity |
| 10-Year Treasury | `DGS10` | Daily, constant maturity |
| 30-Day SOFR | `SOFR30DAYAVG` | NY Fed 30-day compounded average — posts T+1, see caveat below |
| SOFR (overnight) | `SOFR` | NY Fed overnight rate |
| Fed Funds Upper | `DFEDTARU` | FOMC target range upper |
| Fed Funds Lower | `DFEDTARL` | FOMC target range lower |

Label every FRED-sourced value inline with its release date, e.g. *"4.31% — FRED DGS10, 2026-04-24 close."* If a FRED fetch returns HTTP error or all-blank values, fall through to treasury.gov / NY Fed as fallback and mark the cell `[treasury.gov fallback]`. Both FRED and treasury.gov fail → mark `Unavailable as of [time]`.

**Notion-outage mirror fallback (Patch 9, v2.6 — 2026-07-15):** If the FRED CSV fetch and the treasury.gov/NY Fed fallback both fail, or the "Rate Snapshot — Current" Notion page that feeds this section's `rate_status` context (published by `ora-am-brief` Block A) is unreachable at generation time: search Gabriel's mailbox (`outlook_email_search`) for that morning's `ora-health-guard` connector pre-flight email — subject beginning `✅ ORA Connector Pre-Flight — [today YYYY-MM-DD]` or `⚠️ ORA Connector Pre-Flight — [today YYYY-MM-DD]` — and parse the `rate_snapshot` JSON block from the body. Use it for this section's rate table. Carry its `confidence` field through verbatim — it will be exactly `PRIMARY` or `SECONDARY`, never any other value — and label every cell sourced from the mirror `[MIRROR FALLBACK — confidence: PRIMARY|SECONDARY]`. Keep any `n/a` cell in the mirror as `n/a`; never interpolate or estimate a value to fill it. If no such email exists for today, or it also lacks usable data, fall through to the `Unavailable as of [time]` rule above.

Fetch current rates from [treasury.gov](http://treasury.gov), NY Fed SOFR page, CME FedWatch (as secondary confirmation only after FRED prologue above):

RateCurrentChange (30-day)5-Year Treasury\[X.XX%\]\[+/- X bps\]10-Year Treasury\[X.XX%\]\[+/- X bps\]30-Day SOFR\[X.XX%\]\[+/- X bps\]Fed Funds Target\[X.XX–X.XX%\]

Also note: Fed commentary, upcoming FOMC dates, CMBS spread (10-yr AAA) if findable, and significant moves in STAG, PLD, EGP as industrial REIT sentiment proxies.

**Data-as-of caveat (Patch 6, v2.1):** When the brief generates before the Fed H.15 daily print is posted (~4:15 PM ET), Section 3 must show the most recent business-day close and explicitly label it: *"Latest available (Fed H.15 release, [previous business day] close)."* Never fabricate "today's" close. This H.15 timing governs Treasury, Fed Funds, and `SOFR` (overnight) only.

**30-Day SOFR T+1 lag (v2.13, 2026-09-12 — OI-283):** `SOFR30DAYAVG` is a separate NY Fed publication on its own T+1 schedule, not the H.15 release above — the value available at brief-generation time is the compounded average through the prior business day, not through the current or release day. Label it accordingly, e.g. *"3.6485% — FRED SOFR30DAYAVG, average through 2026-09-11."* Do not apply the H.15 ~4:15 PM ET caveat to this series, and do not treat its T+1 posting as a data problem requiring the `[treasury.gov fallback]` or `Unavailable` markers above.

**Rate Snapshot staleness disclosure (v2.13, 2026-09-12 — OI-283):** Before presenting any rate sourced from or informed by the "Rate Snapshot — Current" Notion page (see the Notion-outage mirror fallback above), check its header `prefetch_status` and `fetched_at`. If `prefetch_status` is not `OK`, or `fetched_at` is older than one business day, Section 3 must state this plainly before the rate table — e.g. "⚠ Rate Snapshot degraded — prefetch_status: SOURCE_DEGRADED, last fetched 2026-09-03 05:08 ET" — rather than presenting the page's rates as current with no caveat.

---

## SECTION 4 — PORTFOLIO WATCH

Execute Notion/HubSpot checks:

4a — Scheduled Tasks: Did overnight tasks run? Any errors or missed executions?

4b — Lease Expirations (Notion Tenant Database):

- Any leases expiring in next 30 days?
- Any expiring 31-90 days with no HubSpot renewal activity? Format: \[Tenant\] | \[Property\] | \[Expiration\] | \[Status\]

4c — Delinquency (last Delinquency Tracker output in Notion):

- Any AR balance &gt; $0? Flag anyone &gt;30 days. Format: \[Tenant\] | \[Property\] | $\[Amount\] | \[Days Outstanding\]

4d — Active Deal Actions (Notion Acquisition Pipeline Tracker):

- Deals with deadline in next 7 days?
- Deals stuck at same stage &gt;14 days with no activity? Format: \[Deal\] | \[Stage\] | \[Next Action\] | \[Deadline\]

If no flags: "✅ No items requiring immediate attention."

**Tenant DB ID routing (Patch 4, v2.1 — corrected 2026-04-27 from initial misdiagnosis):**

The Tenant Database has TWO IDs and **the correct one to use depends on which API you are calling.** This is not a "canonical vs. legacy" distinction — both IDs are correct, just for different surfaces.

| Call type | Use this ID | Why |
|---|---|---|
| `notion-fetch` (this MCP) | **Data source ID:** `b12f4cfd-a995-4755-8341-6435ae8173b4` (or `collection://b12f4cfd-a995-4755-8341-6435ae8173b4`) | Calling fetch on the wrapper returns the misleading `validation_error: "Aggregation property not found in data source"` |
| `notion-update-data-source` | **Data source ID** | Operates at the data-source layer |
| Browser navigation (`notion.so/{id}`) | **Database wrapper ID:** `8dbbaec0-611a-4617-be07-6a77d0d0307a` | The wrapper is what URLs use |
| ~~Composio `NOTION_QUERY_DATABASE_WITH_FILTER` / `NOTION_CREATE_DATABASE_ITEM` / `lease-renewal-pipeline` paginator~~ | **RETIRED 2026-06-11** | Composio connector removed. Route all row queries and CRUD through the Notion MCP (`notion-fetch` / `notion-search` / `notion-create-pages` / `notion-update-page`) using the data source ID. The wrapper ID remains valid only for browser URLs. |

**The misdiagnosis on 2026-04-27 was treating the data source ID as universally "canonical" — it's not. Use the table above.**

**Defensive pattern for Section 4b/4c:**

```
try:
  notion-fetch id=collection://b12f4cfd-a995-4755-8341-6435ae8173b4   # data source ID for fetch
  produce 4b/4c with live schema introspection data
except validation_error("Aggregation property not found"):
  # Should NOT happen with the data source ID. If it does, the failure is real schema corruption.
  insert canonical fallback message:
    "Section 4b/4c degraded — Tenant DB schema corruption detected on data source `b12f4cfd-a995-4755-8341-6435ae8173b4`. Falling back to most recent Lease Expiration Brief."
  notion-search for most recent "Lease Expiration Brief" or "Lease Expiration Dashboard" under Operations Hub.
```

For querying tenant *rows* (not schema), use the Notion MCP (`notion-fetch` on the data source ID, paginating as needed). The former Composio wrapper-ID path is RETIRED (connector removed 2026-06-11) — `lease-renewal-pipeline` requires the same migration.

**Database ID Map** for all ORA databases is maintained in the Knowledge Base sub-page `Database ID Map — v1.0` (created 2026-04-27). Resolve once and cache when adding new databases.

**4b Notion-vs-Workbook cross-check (Patch 10/11, v2.7–v2.8).** Notion Tenant DB's `Lease Expiration` field has a documented history of data-quality defects (see `references/incident-history.md` for the 2026-07-16 Chesapeake Brands/Stone Crest Counters/J&R Enterprises incident and the 2026-07-25 HubSpot follow-on). Before reporting a lease-expiration date sourced from Notion in 4b:
- If `C:\Users\Owner\oxford-command-center\data\snapshots\portfolio.json` is reachable from the current run surface, read its `leases` array (each entry has `company`/`tenantName`, `propertyKey`, `unit`, `leaseEnd`) and match by **property + unit + tenant contact/company, not tenant name alone** — several Tenant DB tenants share near-identical names, and matching on name alone risks pairing the wrong record. `meta.asOf`/`meta.source` in that file document its vintage; it is Master Workbook-derived, which CLAUDE.md designates the firm's source of record for firm figures.
- If the matched Workbook lease date **disagrees** with Notion's, or one source has a date the other lacks: report **both** values in the 4b row with a `⚠ DISCREPANCY` tag, rather than presenting Notion's figure alone as settled. Do not silently prefer one source over the other in the brief text — flag it for Gabriel.
- If `portfolio.json` is unreachable from this run surface (a known Cowork-vs-Code cross-surface gap — do not treat this as an error to retry), report the Notion-sourced figure as-is but append the one-line caveat: "Notion Tenant DB has a documented history of Lease Expiration data errors — not cross-checked against the Workbook this run." Do not fail or skip the section over this.
- This cross-check does not extend to 4c/4d.
- **HubSpot third leg.** A lease-date correction is a three-system change (workbook → Notion → HubSpot), not two — Notion-only fixes have gone stale in HubSpot for over a week undetected. If this run has HubSpot access and a DISCREPANCY fires on a tenant per the bullets above, also pull that tenant's HubSpot Lease Renewal deal (match on company/tenant name) and compare its `closedate` against the workbook `leaseEnd`; report all three values if HubSpot disagrees too. Do not rely on `ora-tenant-hubspot-reconciliation` to catch this same-day — it runs monthly. If HubSpot wasn't checked this run (no access, or run surface lacks the connector), say so plainly rather than implying the three-way check was done.

**Notion-outage mirror fallback (Patch 9, v2.6 — 2026-07-15):** If Notion is unreachable for this section — Section 0's pre-flight probe failed, or any of the live 4a–4d queries above error out — search Gabriel's mailbox for the same `ora-health-guard` connector pre-flight email described in Section 3's fallback and parse its `portfolio_watch` JSON block (keyed `4a`/`4b`/`4c`/`4d`). Use it in place of the live queries and tag the whole section `[MIRROR FALLBACK]`. Apply these producer-documented caveats rather than presenting the mirror as live current data:
- The block reflects state as of 05:15 ET that morning, not live at 06:00 — state this explicitly.
- `4b` and `4c` may carry `null` — their producers are retired/stale (the Lease Expiration Dashboard refresh was retired 2026-06-09) — present as "not currently tracked," not as a fresh zero-flags result.
- `4d` is a directional read only (deadline/stuck-stage snapshot, not confirmed live) — label it as such.
- If `portfolio_watch` itself is `null` in the mirror email (Notion was already down at 05:15 when the mirror was captured), Section 4 has no fallback available today — state plainly "Section 4 unavailable — Notion down at both 05:15 and 06:00 checkpoints" rather than fabricating content or silently dropping the section.

---

## SECTION 5 — OPS TIP

Generate one actionable suggestion for improving ORA's software automation, file organization, or operational workflow. Rotate through these topic domains (do not repeat on consecutive days):

1. Zapier — new automation (specify trigger → filter → action)
2. HubSpot — workflow, property, or view for pipeline visibility
3. Notion — database improvement, formula, or view
4. QuickBooks Desktop — report, memorized transaction, or class structure improvement (manual access via SharePoint export; no live MCP)
5. PM Platforms — Rent Manager, AppFolio, or Yardi feature to leverage
6. Document management — naming convention, folder structure, or template
7. Claude / AI — a script or automation buildable in one session

Format: Topic: \[Domain\] | Suggestion: \[1-2 sentences\] | Effort: \[Low/Medium/High\] | Time saved: \[hrs/month\]

---

## SECTION 6 — READING LIST

Identify 5 articles Gabriel should read today based on ORA's goals:

- Portfolio growth (acquisitions, market entry, deal sourcing)
- Operational excellence (PM technology, tenant management, accounting automation)
- Technology for RE (PropTech, API integrations, platform building)
- Finance/capital markets (interest rates, debt, REIT activity)
- Business strategy (family office structure, generational wealth, compounding)

Prioritize: acquisition opportunities, market data with actionable implications, operational best practices for 140+ tenant portfolios, technology replacing current SaaS stack.

Format per article: \[#\]. \[Article Title\] — \[Publication\] \[URL\] \[One sentence: why relevant to ORA specifically\]

---

## SECTION 7 — LAW & REGULATORY WATCH

Find new or revised federal, state, or local laws/regulations enacted or proposed in the last 7 days that affect commercial real estate, specifically industrial/flex property owners.

**Fetch first:** run FIXED SOURCE LIST (B) — the Kansas bill-status API and the Federal Register API, both via curl. Only Kansas exposes a dated state feed; OH, MD, IN, MO, WI and TN are covered by the WebSearch terms below and every such item carries the date-verification rule (`[DATE UNVERIFIED]` unless a fetched page shows the action date). State legislatures are mostly out of session in the fall, so an empty window is normal — say which sources were checked rather than implying coverage.

Search terms to use (WebSearch supplement):

- "commercial real estate law 2026" + \[state: OH, MD, IN, MO, WI, KS, TN\]
- "industrial zoning regulation" OR "warehouse zoning" + target states
- "landlord tenant law commercial" + target states
- "CMBS regulation" OR "commercial mortgage regulation" 2026
- "1031 exchange" legislation updates
- "opportunity zone" regulation changes
- "environmental regulation industrial" + EPA + 2026
- "property tax assessment commercial" + target states
- "ADA commercial real estate" updates
- Federal: FASB lease accounting, SEC real estate disclosure rules, CFPB commercial lending

For each item found, include:

- \[Jurisdiction\] \[Law/Rule Name or Bill Number\]: \[What changed\]. \[Impact on ORA — 1 sentence.\]
- Status: \[Enacted / Proposed / In Committee / Effective Date\]

If nothing material found in last 7 days, note the last significant regulatory change relevant to ORA and its current status.

Sources: [congress.gov](http://congress.gov), state legislature websites, NAR legislative tracker, BOMA regulatory updates, law firm CRE client alerts (JLL Law, DLA Piper, Ballard Spahr).

---

## SECTION 8 — SHALLOW BAY CASE STUDY

Each day, identify and summarize one real-world case study, project spotlight, or operational lesson from a real shallow-bay or multi-tenant flex industrial operator's website.

Source from actual company websites (not aggregators). Rotate through these operators daily:

- Brennan Investment Group ([brennanllc.com](http://brennanllc.com))
- Basis Industrial ([basisindustrial.com](http://basisindustrial.com))
- STAG Industrial ([stagindustrial.com/investors](http://stagindustrial.com/investors))
- Broadstone Net Lease / Broadstone Industrial
- Seagis Property Group ([seagisproperty.com](http://seagisproperty.com))
- Link Logistics ([linklogistics.com/insights](http://linklogistics.com/insights))
- Ares Industrial ([aresindustrialreit.com](http://aresindustrialreit.com))
- Exeter Property Group
- LBA Realty
- Whitebox Real Estate

What to look for on each site: press releases, project spotlights, investor presentations, blog posts, market reports, deal announcements, leasing strategies, development pipelines.

Format: Operator: \[Company Name\] Source URL: \[Direct link to the page\] Topic: \[Acquisition / Development / Leasing / Operations / Capital Markets\] Summary: \[3-4 sentences on what they did, the market, the asset type, and the outcome or thesis\] ORA Takeaway: \[1 sentence — what Gabriel can apply or learn from this specific to ORA's strategy\]

If a company's site yields nothing useful today, move to the next operator on the list.

---

## SECTION 9 — COMPETITIVE INTELLIGENCE

Generate intelligence that gives ORA a specific edge over other shallow-bay buyers and landlords in the Mid-Atlantic (MD, VA, DC) and Midwest (OH, IN, MO, KS, WI) markets. This section must be actionable — not general market commentary.

Use the FIXED SOURCE LIST (A) first — filter its in-window items for competitor moves, broker intel, tenant demand, supply pipeline and lender news. Items 3–7 below remain WebSearch-led and are subject to the date-verification rule.

Run these specific searches:

1. "shallow bay industrial" OR "flex industrial" for sale \[target markets\] — new listings that ORA has not yet screened. Crexi, LoopNet and CoStar are blocked, so this item can only surface listings reported in the FIXED SOURCE LIST (A); if none, print `Listing: none surfaced (Crexi/LoopNet/CoStar not monitorable from this host)` — do not fabricate one
2. Competitor activity: fetch `https://basisindustrial.com/` and scan FIXED SOURCE LIST (A) items for the named firms; WebSearch "\[Brennan Investment Group OR STAG OR Seagis OR LBA\] acquires" + target markets for the others (undated aggregator hits → `[DATE UNVERIFIED]`) — any deals announced this week
3. Off-market signals: search for "\[property address\] industrial auction" OR "industrial bankruptcy sale" OR "motivated seller industrial" in target markets
4. Broker intelligence: any new industrial broker hires, team moves, or boutique firm launches in target markets that could affect deal flow to ORA
5. Tenant demand signals: any large employer announcements (expansions, relocations, new facilities) in target markets that will drive warehouse/flex demand in next 12-24 months
6. Zoning/entitlement pipeline: any new industrial park approvals or rezoning actions that will add supply to ORA's target submarkets in 12-24 months — affects exit cap assumptions
7. Lender activity: any new bridge or permanent lenders entering shallow-bay industrial space, or existing lenders tightening terms — affects ORA's acquisition financing options

Format per item: Category: \[Listing / Competitor Move / Off-Market / Broker Intel / Tenant Demand / Supply Pipeline / Lender\] Finding: \[Specific, factual, sourced finding — 2-3 sentences\] ORA Action: \[What to do with this information — call a broker, adjust underwriting, etc.\]

Minimum 3 items; maximum 6. Prioritize items requiring action within 72 hours. If fewer than 3 dated, sourced items exist, print the ones that do and say so — never fill to the minimum with undated, `[DATE UNVERIFIED]` or invented material (tagged leads go on the closing `Unverified-date leads:` line and do not count). Close the section with the mandatory `Source status:` line (see FIXED SOURCE LIST).

---

## DELIVERY NOTES

- Total brief should take Gabriel &lt;7 minutes to read
- Sections 1-3 and 7-9 require web access — fetch the FIXED SOURCE LIST first (Sections 1, 2, 7, 9), then search only to fill named gaps; complete all fetches and searches before generating output
- Section 4 uses Notion/HubSpot MCPs — check those before generating output
- If a rate or item cannot be found, note "Unavailable as of \[time\]" — never fabricate
- Save brief to Notion under the Operations Hub (parent page id `32b6ecd8-9e59-81f2-b329-df3fd0e25062`) with title `Daily Brief — [YYYY-MM-DD]`.

  **Pre-create dedup guard (Patch 3, v2.1; 1-match branch corrected 2026-08-11):** Before creating a new page, run `notion-search` for the title `Daily Brief — [YYYY-MM-DD]` filtered to the Operations Hub parent.

  - **0 matches** → create.
  - **Exactly 1 match** → **it depends on who created it, and you must check.** Overwrite with `notion-update-page command=replace_content` **only if this same session created that page earlier in this run** (a genuine retry — track the page id you created and compare). **If the page was NOT created by this session, do NOT overwrite it.** Treat it as a completed prior run: log `PRIOR_BRIEF_PAGE_PRESENT` with the existing page id, skip publication *and* the Outlook send below, and report a NORMAL skip citing that page. Then stop — do not create a second page either.
  - **2+ matches** → create the new canonical page, then retitle older duplicates with prefix `🗑️ ... [DUPLICATE — SUPERSEDED by <new_page_id>]` so the workspace surface is clean.

  > **Read before "simplifying" the 1-match branch back to a bare overwrite.** A same-day match during a catch-up burst is often a completed earlier fire's published brief, not this run's own retry — overwriting it destroys a brief Gabriel may already have read and acted on, and does nothing to stop a duplicate Outlook send (unconditional, not gated by this Notion check). Full incident (2026-08-09 double-fire) and rationale: `references/incident-history.md`.

- When running as a scheduled task: send the HTML brief via Outlook COM — the SOLE send path (v2.5, 2026-06-11):
  1. Write the full HTML brief to a temp file (avoids command-line length limits and quoting issues).
  2. Desktop Commander `start_process`: `powershell -ExecutionPolicy Bypass -File "C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1" -To "ggoldberg@oxfordra.net" -Cc "egoldberg@oxfordra.net" -Subject "ORA Daily Brief — [DAY, MONTH DATE YEAR]" -BodyFile "<temp file path>" -BodyFormat html`
  3. The Daily Brief is the SOLE sanctioned cc to egoldberg@oxfordra.net (routing canon 2026-06-10). Every other automated output goes to ggoldberg@oxfordra.net only.
  4. Exit codes: 0 = sent; non-zero → retry once, then flag the failure loudly in the Notion completion row (the automation-health-monitor producer-beacon check catches silent sends) — do NOT halt.

- **Routing (effective 2026-06-11):** Composio was fully RETIRED on 2026-06-11 (connector removed — there is NO Composio fallback). Rube EOL 2026-05-15; Gmail is disabled on the tenant. Outlook COM via `send-via-outlook.ps1` is the only send mechanism. Any remaining `OUTLOOK_SEND_EMAIL`, `COMPOSIO_*`, or `RUBE_*` invocation will hard-fail and must be migrated to the COM script.

---

## CHANGELOG

**Retention rule (added 2026-09-11, ORA Automation Audit R25-7 — ported from `register-scheduled-task` v2.18/v2.20, `package-and-stage-skill` v1.30, `ora-setup-audit` v1.12, `acquisition-underwriting` v1.8 and `deal-execution` v1.8, which already carry it):** keep at most the **6 most recent versions** as full inline entries. The moment an edit would add a 7th, that same edit must also compress the oldest full inline entry to a one-line `**vX.Y (date):** Full text: versions/CHANGELOG-vA.B-vX.Y.md` summary and append its full original text to the versions file for that range. Do it inline, in the pass that adds the new entry.

**Per-entry length cap (same pass):** cap each full inline entry at **~2,000 characters** — the count cap alone bounds how many entries are inline, never how large each is. Measured 2026-09-11: this skill's three entries run 290–944 chars, so the cap fits with headroom. An entry that would exceed it states its finding and verdict inline and cites `versions/` for the detail. This skill was flagged (R25-7) as the #3 realized-cost skill in the environment (146,039 word-loads) with no growth-bound mechanism at all — documentation discipline only, no news-filter, transaction-screen, or workflow logic changed.

- **v2.14 (2026-09-19):** Sections 1, 2, 7 and 9 now FETCH a fixed, live-tested source list instead of relying on WebSearch, which has no last-24-hours filter and returns undated aggregator pages (the 2026-09-19 run came out thin for that reason). New `FIXED SOURCE LIST` block: 11 news URLs across 9 sources via WebFetch (REBusinessOnline, ConnectCRE, Commercial Observer, Bisnow + Bisnow D.C., IBJ, Richmond BizSense, Business Record, BizTimes, Basis Industrial) and 2 law/regulation APIs via curl (Kansas bill-status; Federal Register, 5 fixed terms), a window rule (24 h timestamped / run date + prior day for day-only / 7 d for Section 7), a mandatory `[DATE UNVERIFIED]` tag that is deterministic (tagged leads sit on a closing line and never count toward an item minimum; output-format minimums are now `0-N dated items`), and a `Source status:` line so an unchecked source never reads as "nothing happened". Tested 2026-09-19 (about 60 sources/endpoints, each listed in the record; curl and WebFetch): GlobeSt and every bizjournals.com title are 403-blocked; LoopNet/CoStar/Crexi are blocked, so Section 2 is declared thin by design; six of seven state legislatures (OH, MD, IN, MO, WI, TN) expose no fetchable dated activity surface and stay WebSearch-only. Full results, drop reasons and the per-market coverage table: `references/source-test-2026-09-19.md`. No screening, scoring, dedup, delivery or Section 3/4/5/6/8 logic changed.
- **v2.13 (2026-09-12):** OI-283 fix. Section 3's FRED prologue table mislabeled the overnight `SOFR` series as "30-Day SOFR" — on 2026-09-12 it surfaced SOFR (overnight, 3.62% on 2026-09-10) under that label while the actual 30-day compounded average (`SOFR30DAYAVG`, 3.6485% on 2026-09-11) was never fetched. "30-Day SOFR" now maps to `SOFR30DAYAVG`; added a separate "SOFR (overnight)" row mapped to `SOFR` so both series stay available to the prologue fetch. Added a dedicated caveat for `SOFR30DAYAVG`'s own T+1 NY Fed publish schedule (the value reflects the compounded average through the prior business day) — the existing Patch 6 H.15 caveat governs Treasury/Fed Funds/overnight-SOFR timing only and must not be applied to the 30-day average. Also added a stale/degraded Rate Snapshot disclosure: when the "Rate Snapshot — Current" Notion page's `prefetch_status` is not `OK` or its `fetched_at` is older than one business day, Section 3 must state it before presenting any rate informed by that page (on 2026-09-12 the page carried `SOURCE_DEGRADED` / `fetched_at: 2026-09-03 05:08 ET` and the brief said nothing); also carries forward the 2026-09-11 R25-7 retention-rule and per-entry-length-cap paragraphs above, which the cache-rescue flow found divergent from this commit and restored. No other section's logic changed.
- **v2.11 (2026-08-16):** Size fix (ORA Automation Audit Revision 9/15 finding — this skill runs unattended 7×/week via `ora-am-brief`, making its size a recurring cost, not a one-time read). Moved the pre-create dedup guard's "why the 1-match branch changed" narrative (2026-08-09 double-fire incident) and Section 4b's Patch 10/11 incident narrative (2026-07-16 Chesapeake Brands/Stone Crest Counters/J&R Enterprises + 2026-07-25 HubSpot follow-on) to new `references/incident-history.md`. The operational rules themselves (1-match branch logic, property+unit+tenant matching, `⚠ DISCREPANCY` tagging, HubSpot three-way check) are unchanged in `SKILL.md` — only the historical justification moved. No logic, gate, or output-format change.
- **v2.10 (2026-08-15):** HIGH fix (Skill Text Audit finding F6). Sections 1-2 geographic scope had zero Louisville/Kentucky mentions despite `target-markets.json` ratifying Louisville KY as the 10th canonical cluster (entry-phase, 2026-08-05) 10 days earlier — added `KY (Louisville) — entry/beachhead target, added 2026-08-05` to both lists, matching the existing MI/VA/IA wording pattern. Section 7's law/regulatory-watch state bracket already omitted MI/VA/IA (a pre-existing gap predating this fix, not introduced by it) and was left as-is rather than expanding scope beyond the Louisville parity gap — flagged for a separate finding, not fixed here. Also corrected a frontmatter/body version mismatch: the `description` tag had drifted to v2.8 while this Changelog was already at v2.9 (same doctrine class this audit itself checks for) — frontmatter now reads v2.10 to match. No news-filter, transaction-screen, or workflow logic changed.
- **v2.9 (2026-08-11):** Corrected the Patch 3 pre-create dedup guard's 1-match branch — overwrite is now permitted only for a page this session created; any other match is a completed prior run (skip publication AND the send). Full history back to v2.0: `versions/CHANGELOG-v2.0-v2.9.md`.
