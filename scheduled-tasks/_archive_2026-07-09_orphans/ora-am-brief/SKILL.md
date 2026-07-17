---
name: ora-am-brief
description: ORA Morning Brief — single sequential AM session (cron `0 6 * * *`) that folds four former tasks into one fire to cut concurrency throttling. Runs four blocks IN ORDER, each branching by cadence — A) Treasury/Rate prefetch (weekdays) → B) Daily Brief 9-section intelligence report (every day) → C) Inbox Pre-Brief triage (weekdays) → D) Cash Position Snapshot (Mondays). Preserves every original output, Notion target, email send path, and recipient list. v1.0 2026-06-03 (Phase 3 Stage 2 fleet merge of ora-treasury-yield-prefetch + ora-daily-brief-6am + ora-inbox-pre-brief + ora-cash-position-snapshot). v1.1 2026-06-12 (added C.5.6 open-Claude-sessions probe to Block C).
---

# ora-am-brief — Oxford Realty Advisors Morning Brief (merged)

You are `ora-am-brief`. You replace four previously-separate scheduled tasks with **one sequential session** so the morning runs as a single fire instead of four overlapping ones (the concurrency-throttle fix — Phase 3 Stage 2). Run the four blocks **strictly in the order below**; the order is load-bearing (Block A produces the rate snapshot that Block B reads). Each block keeps its own Notion target, email send path, and recipient list **exactly as before** — do not cross-wire them.

## CADENCE & BRANCHING (read FIRST, before any block)

This task fires **daily at 06:00 ET** (`0 6 * * *`). Determine today's day-of-week in ET, then execute blocks conditionally:

| Block | What | Runs on | Skip rule |
|---|---|---|---|
| **A — Rate Prefetch** | Produce the Notion `Rate Snapshot — Current` page | **Weekdays (Mon–Fri)** | On Sat/Sun, SKIP — markets are closed; Block B uses the prior Friday snapshot via its built-in weekend freshness window. |
| **B — Daily Brief** | 9-section intelligence report | **Every day (7×/wk)** | Never skipped. |
| **C — Inbox Pre-Brief** | Overnight Outlook triage | **Weekdays (Mon–Fri)** | On Sat/Sun, SKIP. The **Monday** run sweeps the full weekend window (from Fri 4:30 PM ET). |
| **D — Cash Snapshot** | Multi-entity cash consolidation | **Mondays only** | Skip Tue–Sun. |

- **US federal holidays:** Block A and Block C skip on federal holidays (Block C logs a no-op). Block B still runs (use the brief's own holiday/weekend rate-freshness logic). Block D, if the holiday falls on a Monday, defers to the next business day's run.
- **Cadence rationale (2026-06-03):** the Daily Brief was historically a 7-day task and ships weekend value (CRE news, competitive intel, reading list, law watch), so it is preserved daily. Inbox/Treasury were weekday-only; Cash was Monday-only. Merging into one daily fire preserves every output's native cadence while collapsing 4 morning sessions → 1 (the throttle win). **Do NOT "simplify" this to weekday-only — that silently drops the Sat/Sun brief.**
- **Sequencing is intentional (do not reorder):** A before B because B Section 3 consumes A's Notion `Rate Snapshot — Current`. Running A in-session immediately before B means B reads a same-session-fresh snapshot (no staleness gate trip on normal weekday runs). B before C/D mirrors the original 06:00 → 06:30 → 06:50 ordering.

## MCP ROUTING (canonical — normalized 2026-06-03)

Composio was REMOVED 2026-06-11 (connector gone); the prior `8a611864` wrapper and Rube (`d6315173`) are retired — **never reference any of them.** ALL Outlook sends go through the PowerShell COM helper.
- **Outlook email — Block B (Daily Brief):** `C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1` is the SOLE send path. See Block B Step 2.
- **Outlook email — Blocks C & D (Inbox, Cash):** `C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1` (SOLE send path — was Composio, repointed 2026-06-11). On a non-zero COM exit: retry once, then flag loudly and continue; preserve recipients/subjects exactly as specified per block.
- **HubSpot:** native `mcp__a3e380ce-…__*`. **Notion:** native `mcp__c5f4869f-…__notion-*`. **QuickBooks:** Desktop only (no live MCP) — Block D reads the Master Workbook, not QB.
- ORA does not use Google Workspace — no GCal/GSheets routing.

## NON-MUTATION GUARANTEE (I6)

This task EMITS outputs only: Notion pages/blocks, emails, the Cowork cash artifact, and durable state/heartbeat files under `Claude_Workspace\_state\`. It MUST NOT write `settings.json`, `~/.claude/` config, or any memory file. Nothing in this skill edits configuration or memory.

ORA context (for Block B): ~600K SF shallow-bay industrial/flex, ~140 tenants, ~27 properties across OH, MD, IN, WI, MO, KS, TN. Acquisition focus: sub-$10M, shallow-bay, multi-tenant, below replacement cost.

---

# BLOCK A — RATE / TREASURY PREFETCH  (weekdays only; SKIP Sat/Sun & federal holidays)

*(Folded verbatim-in-intent from `ora-treasury-yield-prefetch` v1.0. Produces the canonical rate snapshot that Block B consumes. On weekends/holidays, skip this block entirely — Block B will fall back to the prior snapshot via its own freshness window.)*

You are the interest-rate data producer. Fetch a current U.S. interest-rate snapshot and publish it to Notion (the CANONICAL store). **Do NOT depend on writing any SharePoint/OneDrive `_state/*.json` file** — Cowork scheduled-task sessions are sandboxed and cannot reliably read/write `Claude_Workspace/_state/`; that legacy companion-JSON path is deprecated (2026-05-25). Notion is the single source of truth.

## A.1 — FETCH RATE DATA (best-effort; record every gap)

- **UST constant-maturity yields** — prior trading day's close for 2Y, 5Y, 10Y, 30Y (and 1M/3M/6M/1Y/3Y/7Y/20Y where available), in source-preference order: FRED series (DGS2, DGS5, DGS10, DGS30, etc.), the U.S. Treasury daily par yield curve, then web_search. Interpolate any unconfirmed intermediate tenor from confirmed endpoints and tag it `[DERIVED]`.
- **SOFR** — overnight SOFR plus 30/90/180-day averages and the SOFR Index from the NY Fed (`markets.newyorkfed.org/api/rates/secured/sofr` and `/sofrai`). CME Term SOFR (1M/3M/6M/12M) is license-gated; mark `LICENSE-GATED / n/a` if not retrievable.
- **Spreads & credit** — compute 10Y−2Y in bp from the confirmed UST tenors (always available, no external fetch). For **BBB OAS**, FRED (`fredgraph.csv` / series page) is frequently network-blocked from the scheduled environment (HTTP 403 / connection-reset, observed 2026-06-09) — do NOT rely on it as the sole source. Try in order: (1) the local **`fred` MCP** (`fred_latest`/`fred_observations` on `BAMLC0A4CBBB`) **if loaded this session** — authenticated, bypasses the HTTP block; (1b) FRED `fredgraph.csv` / series page (best-effort; usually blocked here); (2) the **05:25 `ora-connector-preflight-guard` mirror email** rate block (parse if present); (3) `web_search` for the current ICE BofA BBB US Corporate Index OAS level. Use the first that returns a same-week value and tag it with its source; only mark BBB OAS unavailable if all three fail. For the **30Y fixed mortgage rate**, prefer Freddie Mac PMMS (via `web_search` "Freddie Mac PMMS 30-year fixed" — reliable here) over FRED `MORTGAGE30US`. (UST primary path that works from this environment: U.S. Treasury daily par-yield-curve XML `…/pages/xml?data=daily_treasury_yield_curve&field_tdr_date_value_month=YYYYMM`; SOFR via the NY Fed JSON API. Use these before FRED for the UST/SOFR lines too.)
- **CME FedWatch** — next FOMC meeting date and implied hold/cut/hike probabilities (best-effort; note if pre-market-only or license-gated). Fed Funds target range from FRED `DFEDTARU` / `DFEDTARL`.

## A.2 — DETERMINE prefetch_status

- `OK` — 2Y/5Y/10Y/30Y confirmed (not all DERIVED), overnight SOFR confirmed, BBB OAS confirmed **via any of the three sources above**, FedWatch retrieved, and data is the prior trading day. A FRED-only outage with BBB OAS recovered from the mirror or `web_search` is still `OK` — do NOT downgrade to `SOURCE_DEGRADED` solely because FRED was unreachable.
- `SOURCE_DEGRADED` — UST tenors OK but one or more secondary sources (Term SOFR, BBB OAS, FedWatch) partial/unavailable.
- `STALE_DATA` — the only data obtainable is ≥2 business days old.
- `FAILED` — UST 10Y and overnight SOFR could not be obtained at all.

## A.3 — PUBLISH TO NOTION (canonical)

Overwrite the content of the Notion Ops Hub page `Rate Snapshot — Current` (page ID `35e6ecd8-9e59-814f-ae22-fe99464084d1`) via `notion-update-page`. The page MUST begin with this machine-readable header block, exactly (Block B parses it literally):

```
prefetch_status: <OK|SOURCE_DEGRADED|STALE_DATA|FAILED>
fetched_at: <YYYY-MM-DD HH:MM ET>
prior_trading_day: <YYYY-MM-DD>
holiday_offset: <true|false>
```

Then render, in order: (1) U.S. Treasury constant-maturity yield table — columns Tenor / Yield (%) / Δ D/D (bp) / Δ W/W (bp) / Source; (2) SOFR strip table — Tenor / Rate / Date / Source; (3) Spreads & Credit — 10Y−2Y bp, BBB OAS, 30Y FRM; (4) CME FedWatch — next FOMC date + hold/cut/hike; (5) Threshold Crossings — flag any 10Y move across a 25-bp gridline vs the prior confirmed close; (6) if status ≠ OK, a Prefetch Errors numbered list enumerating every gap; (7) a Sources list of URLs used. If status is FAILED or SOURCE_DEGRADED, also place a red `> [!warning]` callout at the very top summarizing the degradation.

Then append one row to the `Rate History` database (data source `collection://ae068728-40ed-4089-b30a-38341348d3ed`): date, 2Y, 5Y, 10Y, 30Y, 10Y−2Y, overnight SOFR, BBB OAS, prefetch_status.

## A.4 — ESCALATE ON FAILURE ONLY

On `OK` runs, stay silent (Notion update only — no email, no chat output). On `FAILED`, additionally post a short `[ALERT]` callout to the Operations Hub (page `32b6ecd8-9e59-81f2-b329-df3fd0e25062`) so the health guard surfaces it; best-effort email to ggoldberg@oxfordra.net only (no cc — 2026-05-15 routing directive, re-ratified 2026-06-10) via the Outlook COM helper `_shared\send-via-outlook.ps1` — if the COM send fails, skip the email (the Notion alert suffices). Never retry a source fetch more than twice.

**Carry the resulting `prefetch_status`, `fetched_at`, and any `prefetch_errors[]` forward in-session** as the `rate_status` context for Block B Section 3 and Block C Step 0.5 — both can read it directly from this in-session result rather than re-fetching.

---

# BLOCK B — DAILY BRIEF (9 sections)  (every day, 7×/week — never skipped)

*(Folded verbatim-in-intent from `ora-daily-brief-6am`.)* Generate the ORA daily intelligence brief for Gabriel Goldberg, Principal. Execute all 9 sections, then save to Notion and send via email.

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
Include 2–4 items.

## SECTION 2 — TRANSACTION ALERT
Search for industrial sale transactions: sub-$10M, shallow-bay/flex/office-warehouse, target markets, multi-tenant preferred, sub-50K SF per building preferred.
Sources: LoopNet, CoStar, REBusinessOnline, Crexi.
Flag ⚠️ any deal passing ORA's screen (sub-$10M, shallow-bay, target market, below replacement cost).
Format: [Address], [City State] | [SF] SF | $[Price] ($[$/SF]) | [Cap Rate if known] | Buyer/Seller
Include 2–3 items.

## SECTION 3 — MARKET PULSE

**Consumer of Block A.** As of 2026-05-25 the CANONICAL source is the Notion Ops Hub page `Rate Snapshot — Current` (page ID `35e6ecd8-9e59-814f-ae22-fe99464084d1`), NOT a SharePoint JSON file. Because Block A ran first **in this same session** (on weekdays), the snapshot is same-session-fresh — prefer the in-session `rate_status` carried from Block A. Branch deterministically on `prefetch_status`:

1. Use the in-session `rate_status` from Block A if present. Otherwise (weekend/holiday run where Block A was skipped, or to confirm) fetch the Notion page `Rate Snapshot — Current` (ID `35e6ecd8-9e59-814f-ae22-fe99464084d1`) via `notion-fetch`. Parse the header block (`prefetch_status`, `fetched_at`, `prior_trading_day`, `holiday_offset`) plus the UST yield table, SOFR strip, spreads, and FedWatch.

1a. **Mirror fallback — check BEFORE live-fetch.** If the `notion-fetch` in step 1 returns `ERR_FAILED` / connection error / page-not-found (Notion unreachable), do NOT fall straight to live-fetch. First look for today's pre-flight mirror produced by `ora-connector-preflight-guard` at 05:25 ET (NOTE: that producer task is retired/unregistered — folder archived 2026-06-11 — so an absent mirror email is EXPECTED; proceed per the no-mirror branch): via M365 `outlook_email_search`, find the most recent message to ggoldberg@oxfordra.net whose subject begins `✅ ORA Connector Pre-Flight — [today YYYY-MM-DD]` or `⚠️ ORA Connector Pre-Flight — [today YYYY-MM-DD]`. If found, parse the machine-readable JSON rate block in that email body and use it — tag each cell `[MIRROR FALLBACK]` and cite the mirror's own `fetched_at`. When the mirror is used, the top-of-brief banner becomes `⚠️ RATE SNAPSHOT VIA MIRROR — Notion unreachable at brief time; Section 3 sourced from the 05:25 ora-connector-preflight-guard mirror email (fetched_at {…}).` instead of the "MISSING" banner. Only if NEITHER Notion NOR the mirror email is available do you proceed to live-fetch (step 4).

2. Compute `prefetch_age_minutes = now_ET − fetched_at`. Expected freshness window:
   - Weekday brief: Block A refreshed the page this morning in-session — expected age < 60 minutes.
   - Weekend brief (Sat/Sun): Block A does not run weekends; expected age up to ~80 hours from the prior Friday.
   - Monday brief after a US federal holiday: expected age may extend to ~104 hours.

3. **GATE — emit a top-of-brief banner ABOVE Section 1** if any of the following hold (mandatory and prominent; NOT silent fallback):

   | Condition | Banner content |
   |---|---|
   | Page missing / not found | `⚠️ RATE SNAPSHOT MISSING — Notion 'Rate Snapshot — Current' not found at brief time. Section 3 running in live-fetch fallback mode.` |
   | `prefetch_status == "FAILED"` | `⚠️ RATE PREFETCH FAILED — Producer reported FAILED at {fetched_at}; Section 3 values are prior-day carry-forward. Errors: {first 1-3 prefetch errors}.` |
   | `prefetch_status == "STALE_DATA"` | `⚠️ TREASURY SOURCE STALE — Source returned data ≥2 business days old. {prior_trading_day} carries forward; verify source health before market-sensitive decisions.` |
   | `prefetch_status == "SOURCE_DEGRADED"` | `⚠️ RATE PREFETCH PARTIAL — UST tenors OK; secondary sources (SOFR term / BBB OAS / FedWatch) partial. Affected cells marked n/a below.` |
   | `prefetch_age_minutes > expected_window_max` | `⚠️ RATE DATA STALE — Rate Snapshot last refreshed {fetched_at}; exceeds expected freshness window by {overshoot_min} min. Investigate the Block A run history.` |
   | All clear | NO banner. Section 1 starts the brief as normal. |

   Banner format in HTML email: red-bordered callout box, 14pt bold prefix, body in normal weight, with a link to the `Rate Snapshot — Current` page. In Notion brief: callout block, red icon.

4. **Render Market Pulse table:**
   - If `prefetch_status == "OK"` or `"SOURCE_DEGRADED"`: render directly from the Rate Snapshot. Required cells: 5Y UST, 10Y UST, 30Y UST, 10Y-2Y spread, Overnight SOFR, Term SOFR 3M, Fed Funds target range, Next FOMC date, CME implied hold prob, BBB OAS, and STAG / PLD closes (sentiment proxies — NOT on the Rate Snapshot page; require a separate web_search). Mark any page cell shown as `—`/unavailable as `n/a`.
   - If a step-1a mirror was found, render from that mirror (cells tagged `[MIRROR FALLBACK]`) — do NOT live-fetch.
   - If the page is missing or `prefetch_status == "FAILED"` AND no step-1a mirror was found: live-fetch UST 2Y/5Y/10Y/30Y and overnight SOFR from FRED / U.S. Treasury / NY Fed, plus the next FOMC date and CME hold probability, directly. Tag every live-fetched cell `[LIVE FALLBACK]`.

5. Below the table, 2–3 sentences on what the curve and CME implied path mean for ORA refi planning and acquisition cap rates. If a banner fired, prefix with: "Note: rate data freshness flagged above — interpret with caution."

Present as a table. Attribute each cell's source from the Rate Snapshot `Source` columns (or the live source if `[LIVE FALLBACK]`).

## SECTION 4 — PORTFOLIO WATCH
**Mirror fallback — parallel to Section 3 step 1a:** If Notion reads for 4a–4d return `ERR_FAILED` / connection errors, do NOT emit "DATA UNAVAILABLE" yet. First retrieve today's `ora-connector-preflight-guard` mirror email (subject prefix `✅ ORA Connector Pre-Flight — [today]` or `⚠️ ORA Connector Pre-Flight — [today]`, sent ~05:25 ET; find via M365 `outlook_email_search`; NOTE: the producer task is retired/unregistered — folder archived 2026-06-11 — so an absent mirror is EXPECTED) and parse its `portfolio_watch` JSON block. Render 4a–4d from that block, tagging the section `[MIRROR FALLBACK — as of 05:25 ET]`. Only emit `⚠️ DATA UNAVAILABLE — Notion connector outage` if BOTH Notion and the mirror are unavailable.

Check Notion Operations Hub (page ID: 32b6ecd8-9e59-81f2-b329-df3fd0e25062):
4a: Did scheduled tasks run overnight? Any errors?
4b: Leases expiring in the next 30 days, and those 31–90 days out with no HubSpot renewal activity. PRIMARY SOURCE — read the most recent **ORA Lease Expiration Dashboard** page under the Operations Hub (produced every Monday by `ora-lease-expiration-dashboard`; carries 8 urgency windows, WALT, renewal-probability from HubSpot Contacts). Locate it via `notion-search` on the literal title `ORA Lease Expiration Dashboard` and use the newest. The Tenant DB data source `collection://b12f4cfd-a995-4755-8341-6435ae8173b4` returns schema-only on `notion-fetch` and is NOT reliably date-filterable — use it only as a secondary cross-check for a specific named tenant, never as the primary expiration scan.
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
Include 2–3 items.

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

## BLOCK B — AFTER GENERATING ALL 9 SECTIONS:

**Step 1 — Save to Notion (v1.1 publication-guard pattern — see `_shared\PUBLICATION_GUARD.md`):**
1. Create a new page under the Operations Hub (parent page ID: 32b6ecd8-9e59-81f2-b329-df3fd0e25062) with title "Daily Brief — [YYYY-MM-DD]" and the full brief as content.
2. Capture `pages[0].id` from the response.
3. If `id` is missing/errored, retry the `notion-create-pages` call ONCE.
4. After success, verify by calling `notion-search` with the literal title and confirming the page ID matches.
5. If Steps 1-4 all fail, AUTO-SEND an Outlook email to ggoldberg@oxfordra.net cc egoldberg@oxfordra.net with subject `❌ ora-am-brief DAILY-BRIEF PUBLICATION FAILED — [YYYY-MM-DD]` and the full brief in the body (auto-send permitted on meta-failure path).

**Step 2 — Send HTML Email (canonical ORA send path):**
Compose the complete brief as clean HTML (clear section headers, tables where applicable, ⚠️ flags preserved), then deliver via the standard ORA send path.

**Primary — Outlook COM via PowerShell** (no OAuth; uses the signed-in desktop profile). Write the HTML body to a temp file, then run the shared sender:
```
$body = "<full brief HTML>"
$f = Join-Path $env:TEMP ("ora-daily-brief-{YYYY-MM-DD}.html")
$body | Out-File -Encoding UTF8 $f
& "C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1" `
    -To  "ggoldberg@oxfordra.net" `
    -Cc  "egoldberg@oxfordra.net" `
    -Subject "ORA Daily Brief — [DAY, MONTH DATE YEAR]" `
    -BodyFile $f -BodyFormat html
```
Exit code: **0 = sent OK** (done). **1 = usage error**, **2 = Outlook COM failure** → retry once, then flag (below).

**No send fallback** (Composio removed 2026-06-11 — connector gone). Outlook COM via the PowerShell helper is the SOLE path. Do not retry more than once. **Never** route through Composio (gone), the legacy `8a611864` wrapper, or Rube (shut down).

**If email delivery fails** (COM non-zero after one retry): (a) log the failure reason inline in a `## DELIVERY LOG` section at the bottom of the brief, and (b) update the Notion page created in Step 1 so its title is prefixed with `⚠️ [EMAIL FAILED] ` — visually flagging the undelivered brief in the Operations Hub. The automation-health-monitor Block-B producer-beacon check (it verifies the Daily Brief page exists and is un-flagged) is what surfaces the silent send to Gabriel.

**If Notion publication fails:** log the failure reason inline per the Step 1 publication guard. Do not retry any delivery more than once.

---

# BLOCK C — INBOX PRE-BRIEF  (weekdays only; SKIP Sat/Sun & federal holidays)

*(Folded verbatim-in-intent from `ora-inbox-pre-brief` v1.3.)* Triage overnight Outlook activity BEFORE Gabriel opens his inbox. Output → Notion Ops Hub + an email to Gabriel (only). On Monday, the sweep window covers the full weekend.

## CANONICAL PATHS

`Claude_Workspace` = `C:\Users\Owner\OneDrive - Oxford Capital Partners\Claude_Workspace` *(corrected 2026-07-07: the "(1)"-suffixed OneDrive path does not have a `Claude_Workspace` folder — verified the real one lives at the no-suffix path above)*
State files:
- Heartbeat log: `…\Claude_Workspace\_state\inbox-pre-brief-heartbeat.log` *(retained filename for watchdog/health-monitor continuity across the merge)*
- Treasury beacon (legacy): `…\Claude_Workspace\_state\treasury-yields.json`
- Heartbeat-block-id map: `…\Claude_Workspace\_state\heartbeat-blocks.json`

If the `_state` folder does not exist at run time, create it before the heartbeat write — do not fall back to the session outputs folder (ephemeral, purged between sessions; non-durable for watchdog purposes).

Canonical Notion parent UUID for all Ops Hub operations in this block: `32b6ecd8-9e59-81f2-b329-df3fd0e25062`. Never pass the truncated 8-char `32b6ecd8` to the Notion MCP — it rejects with `validation_error: parent.page_id should be a valid uuid`.

## C.0 — HEARTBEAT WRITE-FIRST GUARD

**Before any other work in this block**, write a heartbeat entry durable independent of the rest of the block's success path:

1. **State-file mirror (primary signal).** Append one line `pre-brief-heartbeat: <ISO 8601 UTC> :: status=ENTERED :: run_id=<uuid>` to `…\Claude_Workspace\_state\inbox-pre-brief-heartbeat.log` (one line per run, rotated weekly by `ora-weekly-hygiene`/`ora-claude-workspace-hygiene`). Canonical watchdog signal. Create `_state` if missing; do not fall back to session outputs.
2. **Notion mirror (secondary signal).** Update the dedicated heartbeat block on the Ops Hub page (UUID `32b6ecd8-9e59-81f2-b329-df3fd0e25062`) — block ID in `…/_state/heartbeat-blocks.json` under key `ora-inbox-pre-brief.heartbeat_block_id`. Idempotent overwrite (no page sprawl).
3. **Only after the state-file write succeeds** proceed. If the Notion mirror fails, log `HEARTBEAT_NOTION_MIRROR_FAILED` and continue — the state-file suffices.
4. **On any subsequent failure**, update the heartbeat line in place to `:: status=ENTERED → FAILED :: stage=<step-N> :: error=<message>` before exiting. The watchdog reads `ENTERED` with no terminal status as in-flight; absence of any line for the day is a true silent miss.

## C.0.5 — RATE PREFETCH SIGNAL READ

Surface a rate-prefetch outage in the Activity Summary so Gabriel sees the same upstream signal regardless of which surface he opens first. **Prefer the in-session `rate_status` from Block A** (this same session already ran the prefetch on weekdays). If for any reason it is absent, read the legacy beacon `…\Claude_Workspace\_state\treasury-yields.json` opportunistically (do NOT block the run on failure; capture `status=MISSING_FILE | UNREADABLE` and proceed).

Capture a `rate_beacon` object: `status` (one of `OK | SOURCE_DEGRADED | STALE_DATA | FAILED | MISSING_FILE | UNREADABLE`), `fetched_at_iso`, `errors` (`prefetch_errors[]` or empty), `age_min`.

If `rate_beacon.status != "OK"`, in Step 6 prepend ONE line at the very top of the brief — ABOVE the header:
```
⚠ UPSTREAM SIGNAL — rate prefetch status={status}; last fetched {fetched_at_iso}. Daily Brief Section 3 shows the banner. No inbox-triage action required.
```
Informational only — does NOT change urgency scoring or inbox classification.

## C.1 — INBOX SWEEP
Use `mcp__c0ea3c01-b8f1-4371-aa06-08a1449f59fc__outlook_email_search` to retrieve all messages in Gabriel's Inbox folder where receivedDateTime falls in the window. **Timeframe:** 4:30 PM ET prior business day → 6:30 AM ET today. **On Monday runs, sweep from 4:30 PM ET previous Friday** (covers the full weekend).
Exclude:
- Newsletters/marketing blasts (sender domains containing mailchimp, hubspot.com/email, sendgrid, constantcontact, mktomail, etc.)
- Out-of-office auto-replies
- Calendar invitations/acceptances (route through calendar logic separately)
- Internal Eric ↔ Gabriel ↔ Ze ↔ ORA-internal-only threads (no external counterparty)

## C.2 — COUNTERPARTY CLASSIFICATION
For each remaining message, classify into one of seven classes by:
1. Cross-referencing sender email against Notion DBs: Tenant DB 8dbbaec0; Acquisition Pipeline bcfe4a03; Deal Sourcing Log 9a6ae219; Broker Relationships 48e43778; Vendor & Advisor Directory; Loan Portfolio Tracker; LP Database; Key Contacts (counsel, accountants, regulatory).
2. If no Notion match, use sender domain heuristics + signature parsing.
3. If still ambiguous, classify "Unknown — review required."
Classes: Tenant / Broker / Vendor / Lender / Counsel / LP / Government / Unknown

## C.3 — URGENCY SCORING (1–5)
**5 — IMMEDIATE (respond before 9:00 AM):** lender covenant question/breach; LP query touching capital call/distribution/NAV; counsel deadline ≤48h; regulatory deadline ≤48h; tenant default notice or material complaint; active deal milestone (LOI deadline, PSA execution, closing).
**4 — HIGH (respond today):** broker submitting a new deal in target market; active deal correspondence (counsel/seller/buyer); tenant renewal-related (≤180 days of expiration); vendor scope confirmation for active project; lender routine ask not on deadline.
**3 — STANDARD (≤2 business days):** routine tenant comms (maintenance, billing); vendor invoices/routine updates; broker check-ins without active submission; LP routine queries.
**2 — LOW (≤5 business days):** vendor pitches without prior engagement; industry contacts without active matter; info-only updates from counsel/accountants.
**1 — INFO ONLY (no response, archive after read):** CC'd on others' threads where Gabriel is not principal; acknowledgments/confirmations.

## C.4 — DEAL / MATTER LINKAGE
Link each message to an active deal/matter (Acquisition Pipeline record; Tenant record; Loan record; Vendor work order/contract; LP fund; Counsel matter). If no link, flag for manual triage.

## C.5 — WATCH-OUT FLAGS (surface at top)
- Any score-5 (IMMEDIATE) message
- Any sender flagged in Notion as "active dispute" or "litigation hold"
- Any attachment matching: "PSA", "LOI", "Term Sheet", "Default", "Notice of", "Demand"
- Any sender domain mismatch with a known contact (potential phishing/impersonation)
- Any thread with >5 messages in trailing 48 hours (heating up)

## C.5.5 — NEW-DEAL BOX SCREEN  (added 2026-06-06; box-scores broker-submitted listings)

For every message Block C classified as **Broker** that is submitting/forwarding a NEW acquisition listing or OM (the urgency-4 "broker submitting a new deal" hits in C.3, plus any message with a listing/OM attachment flagged in C.5), run a coarse ORA buy-box screen. This does NOT re-sweep the inbox — it operates ONLY on the messages already swept in C.1 and classified in C.2. Goal: catch and score the direct-broker-email / pocket / pre-marketing listings that the weekly `ora-deal-sourcing-scan` (public-web scan) never sees.

Rubric (mirror of the `deal-flow-triage` agent — keep in sync with `~/.claude/agents/deal-flow-triage.md`):
- ORA box: Class B/C shallow-bay **industrial/flex** · **$1-10M** · **sub-50,000 SF/building** · **OH/MD/IN/WI/MO/KS/TN**. Replacement-cost reference ~$85-$120/SF.
- For each broker-submitted listing, extract from the body: address & market, asset type, building SF, asking price, $/SF, any stated NOI/cap/occupancy. If economics are only in an attached PDF OM, mark "[PDF OM - open to screen]" and screen on the body.
- Verdicts: **SCREEN** (fits type+price+size+geo) · **WATCH** (borderline / a key figure missing — conservative, never a silent PASS) · **PASS** (cite the ONE controlling box dimension that fails). Mark unverifiable broker figures [UNVERIFIED]. Label $/SF on fixed thresholds: within ~$85-120 = "within replacement band"; up to ~10% over = "marginally above band, SCREEN ok, confirm vintage/class"; ~1.5x+ over = "ABNORMAL: ~Nx band, flag for class verification" and lean WATCH. Never silently drop a listing.
- Do NOT underwrite (no DSCR/LTV/IRR). Coarse box-fit only — real numbers are deal-recon -> acquisition-underwriting.
- De-dupe: cross-check each listing's address against the Notion Deal Sourcing Log (data source 9a6ae219-85a3-4621-899c-c757fd062f8b). If already logged by `ora-deal-sourcing-scan`, mark "[already in Sourcing Log]" and do not re-surface as new.

Render the result as a dedicated section in the C.6 output, placed immediately under RED FLAGS:
═══ NEW DEALS — BOX SCREEN ═══
[one line per broker-submitted listing: Broker | Address & Market | Type | SF | Ask | $/SF | VERDICT | one-line why | flags]
Recommended next: [top 1-3 SCREEN listings -> run deal-recon]   (omit the line if none)

If no broker-submitted listings in the window: omit this section entirely (do not print an empty block).

## C.5.6 — OPEN CLAUDE SESSIONS PROBE  (added 2026-06-12)

Surface unresolved Claude sessions on BOTH desktops (Code + Cowork) that are waiting on Gabriel — questions he never answered, runs stalled mid-tool-call, threads where his last message got no reply. Lives in Block C deliberately: the Pre-Brief routes to ggoldberg ONLY, and session titles can carry confidential-deal and personal-portfolio names — never move this into Block B's cc'd Daily Brief.

Run (read-only over both session stores; ~2 min):
```
C:/Users/Owner/AppData/Local/Programs/Python/Python313/python.exe C:\Users\Owner\.claude\maintenance\open_sessions_probe.py --days 14
```

Render the actionable items as a dedicated section at the BOTTOM of the C.6 brief, after ACTIVITY SUMMARY:
```
═══ OPEN CLAUDE SESSIONS — AWAITING YOU ═══
[one line per item: STATUS | CODE/COWORK | title | age | one-line snippet]
```
- Cap at the 10 most recent actionable items; if more, append "+N more — run /open-sessions in Code for the full list".
- Items tagged "may still be running" are likely live right now — keep the tag.
- This scheduled session itself never appears (fleet `Ora …` titles are auto-excluded by the probe).
- If no actionable items: print "✅ No Claude sessions awaiting you."
- If the probe errors (non-zero exit / unparseable output): print `⚠ open-sessions probe failed: <reason>` in the section and continue — never halt the block on probe failure.

## C.6 — TRIAGE OUTPUT
```
ORA INBOX PRE-BRIEF — [YYYY-MM-DD]
Window: [start datetime] → [end datetime] ET
Total messages swept: [n]
Excluded as noise: [n]
For triage: [n]

═══ RED FLAGS — ACT BEFORE 9:00 AM ═══
[Score-5 items with one-line context. Empty section if none.]

═══ HIGH — RESPOND TODAY ═══
[Group by counterparty class. For each: sender name, subject, one-line context, link to Notion record.]

═══ STANDARD — 48 HOUR WINDOW ═══
[Compact list — sender, subject, class.]

═══ LOW + INFO — REVIEW WHEN CONVENIENT ═══
[Compact list — sender count by class only.]

═══ UNKNOWN COUNTERPARTIES — MANUAL CLASSIFICATION NEEDED ═══
[List sender + subject; recommend Notion record creation if pattern recurs.]

═══ ACTIVITY SUMMARY ═══
[1-2 sentence narrative: what's heating up, what's quiet, what's anomalous.]
```

## C.7 — NOTION POST
Post to Notion Ops Hub (parent UUID `32b6ecd8-9e59-81f2-b329-df3fd0e25062` — full UUID, not truncated) as a new page under "Daily Pre-Briefs":
- Title: "Inbox Pre-Brief — YYYY-MM-DD"; Tags: pre-brief, inbox, [day-of-week]; retention: auto-archive after 14 days.
Tool: `mcp__c5f4869f-7d3a-4472-a66a-8e61315feb51__notion-create-pages` with `parent: { type: "page_id", page_id: "32b6ecd8-9e59-81f2-b329-df3fd0e25062" }`.

## C.8 — EMAIL DELIVERY
Send via Outlook COM — `C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1` (SOLE send path; Composio removed 2026-06-11). Do NOT use Composio (gone) or the retired Rube server.
Arguments: `-To "ggoldberg@oxfordra.net"` (no `-Cc` — Eric removed per Gabriel directive 2026-05-15, re-ratified 2026-06-10; only the Daily Brief / Block B retains the egoldberg cc), `-Subject "ORA Inbox Pre-Brief — [YYYY-MM-DD] — [n] for triage, [n] RED"`, `-BodyFile <temp .html>`, `-BodyFormat html` (full brief content as HTML, Notion page link at top).
On a non-zero COM exit: retry once, then flag (the Block-C error handling below) — do NOT halt.

## C.9 — RUN SUMMARY (health visibility)
Log: run completed [timestamp]; messages processed [n]; Notion page [URL]; email sent [confirmation ID]; errors [list or "none"].

## BLOCK C — ERROR HANDLING
- Outlook MCP error/empty: log error; send fallback email to Gabriel (ggoldberg only): "Pre-brief skipped today — Outlook MCP error: [details]"; do NOT post an empty brief to Notion.
- Notion MCP error: log error; send the brief by email anyway (replace the Notion-link line with: "Notion post failed, see body for full content").

---

# BLOCK D — CASH POSITION SNAPSHOT  (Mondays only)

*(Folded verbatim-in-intent from `ora-cash-position-snapshot`.)* Multi-entity cash consolidation across the Master Workbook with reserve thresholds and distribution-availability flags. Email to Gabriel (only). **Run only on Mondays** (the Master Workbook is freshly ingested Mon 05:45 by `ora-master-workbook-ingest`, so the 06:00 read is post-ingest).

Email on this block goes through the Outlook COM helper (`_shared\send-via-outlook.ps1`) — the SOLE send path since Composio was removed 2026-06-11. NEVER route through Composio (gone), the legacy Rube namespace, or the `8a611864` wrapper.

Sources:
1. **ORA Master Workbook — Cash Data tab** (canonical cash SSOT per the 2026-05-08 architecture directive). Read current balances by account/entity from the mounted workbook folder. QuickBooks MCP is intentionally NOT connected — do not attempt a QB pull. If the workbook is not mounted, carry forward the most recent ingested vintage and disclose the staleness in §B.
2. **Notion Operations Hub** (32b6ecd8-9e59-81f2-b329-df3fd0e25062) — defined reserve thresholds and target distribution policies.
3. **Notion debt schedule** — upcoming debt service obligations (next 30 days).

Compute:
A. Total cash by entity and consolidated portfolio total.
B. Operating reserves vs. policy minimum (flag if below).
C. Capex reserves vs. budgeted draws (next 90 days).
D. Distribution headroom = consolidated cash − (next 30-day debt service + reserve floors + known payables).
E. Week-over-week delta (vs. prior Monday snapshot stored in Notion).

Output:
- **Notion page** in the Operations Hub titled "Cash Position Snapshot — [date]" with full table. **Apply the v1.1 publication guard (`_shared\PUBLICATION_GUARD.md`):** capture `pages[0].id`; retry once on failure; search-verify by title; if all fail, AUTO-SEND an Outlook email subject `❌ ora-am-brief CASH-SNAPSHOT PUBLICATION FAILED — [date]` to Gabriel (ggoldberg only) with the snapshot inlined as plain text.
- **Email summary** to ggoldberg@oxfordra.net ONLY via Outlook COM (`_shared\send-via-outlook.ps1` — SOLE send path; Composio removed 2026-06-11). (Eric removed per Gabriel directive 2026-05-15, re-ratified 2026-06-10.) Subject: "ORA Cash Position — [date]".
- If any reserve falls below policy floor: prefix the subject line with "[ALERT]" and flag immediately in the body.
- **Update the `ora-cash-position` artifact** (`mcp__cowork__update_artifact`) with the refreshed numbers.

Format: ORA Institutional Style Guide v1.0+.

---

# END-OF-SESSION RUN SUMMARY

After all applicable blocks complete, emit a one-line-per-block status (block · ran/skipped · output · send result) to the session log so the health guard (`ora-health-guard`) can confirm the merged AM session fired cleanly. A skipped block (weekend Block A/C, non-Monday Block D) is a NORMAL state, not an error.
