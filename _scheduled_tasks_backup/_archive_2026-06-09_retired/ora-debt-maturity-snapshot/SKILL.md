---
name: ora-debt-maturity-snapshot
description: Weekly debt maturity and rate snapshot (Fridays 4 PM) — pulls SOFR/10Y/spread benchmarks, maps to ORA debt schedule in Notion, flags loans inside 18-month refi window.
---

**[MCP ROUTING — normalized 2026-06-03]** Outlook email: `C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1` (PRIMARY) → `mcp__composio-ora__OUTLOOK_SEND_EMAIL` (fallback). HubSpot: native `mcp__a3e380ce-…__*`. Notion: native `mcp__c5f4869f-…__notion-*`. QuickBooks: Desktop only (no live MCP). The prior `8a611864` Composio wrapper is no longer connected; Rube `d6315173` is retired — never reference either. ORA does not use Google Workspace.

You are running the ORA Weekly Debt Maturity & Rate Snapshot.

OBJECTIVE
Surface refi exposure by mapping current rate environment to ORA's debt schedule.

EXECUTION
1. **Rate environment — fetch in this priority order. DO NOT scrape the FRED series HTML page (e.g. `fred.stlouisfed.org/series/SOFR30DAYAVG`); it renders a cached "latest observation" block that lags the live series by weeks.**
   a. **PRIMARY — FRED API (JSON, latest record).** The absolute URLs are listed here verbatim so they are provenance-valid for `web_fetch` in-run:
      - 1M SOFR (30-day avg): `https://api.stlouisfed.org/fred/series/observations?series_id=SOFR30DAYAVG&api_key={{FRED_API_KEY}}&file_type=json&sort_order=desc&limit=1`
      - 3M SOFR (90-day avg): `https://api.stlouisfed.org/fred/series/observations?series_id=SOFR90DAYAVG&api_key={{FRED_API_KEY}}&file_type=json&sort_order=desc&limit=1`
      - 10Y Treasury (DGS10): `https://api.stlouisfed.org/fred/series/observations?series_id=DGS10&api_key={{FRED_API_KEY}}&file_type=json&sort_order=desc&limit=1`
      - Overnight SOFR (optional): same pattern with `series_id=SOFR`.
      Parse `observations[0].date` (use as the cited timestamp) and `observations[0].value`. DGS10 returns `"."` on non-trading days — if `value=="."`, refetch with `limit=5` and take the most recent numeric observation. Cite "FRED <SERIES_ID>, <date>".
   b. **SECONDARY — Notion "Rate Snapshot — Current"** (maintained by the ora-daily-brief prefetch, ~05:40 ET). Use only if a FRED call errors or `{{FRED_API_KEY}}` is unset. Record the prefetch timestamp and flag staleness (>24h) in §A.
   c. **TERTIARY — WebSearch** (FRED / WSJ / CNBC US10Y / sofrrate.com). Cite source + timestamp.
   **CMBS AAA & BBB- conduit spreads:** WebSearch CRE Finance Council MarketMetrics / Trepp / Commercial Observer; carry last-known if no fresh print (informational only — book holds no CMBS debt). Cite source + timestamp for every benchmark.
   *Setup note: `{{FRED_API_KEY}}` is a free, read-only, low-sensitivity key (public economic data; re-issuable at fredaccount.stlouisfed.org). Provisioned inline 2026-05-29. If a FRED call ever returns an auth error, the key was rotated — re-issue and replace the three URLs above; the skill falls through to (b)/(c) meanwhile with no regression.*
2. Query Notion Operations Hub for the Debt Schedule (or page-level loan list under Properties database). Pull: Property, Lender, Original Principal, Current Balance, Rate (fixed/floating), Index + Spread (if floating), Maturity Date, IO/Amort, Prepay Penalty.
3. Compute for each loan: Days-to-Maturity, Current All-In Rate (for floating), Implied Refi Rate (10Y + 200bps default; can be tuned). Flag if (Days ≤ 540) OR (Floating AND All-In ≥ 7.5%).
4. Compute portfolio-level: weighted-avg rate, weighted-avg maturity, % fixed vs floating, total principal in 18-month refi window.
5. Build snapshot in ORA Institutional Style: header with current rates, table per loan, portfolio summary footer.
6. Save to Notion as "Debt Snapshot — YYYY-MM-DD".
7. Email Gabriel + Eric from ggoldberg@oxfordra.net. Subject: "ORA Debt Snapshot — YYYY-MM-DD ($Xm in refi window)". Body: 3-bullet summary + link.

QC GATES
- All loans accounted for vs. baseline count.
- Rate sources cited with timestamps.
- Rate sources fetched per the §1 hierarchy (FRED API → Notion prefetch → WebSearch). If ALL tiers fail for a benchmark, note the tier path that was attempted in the body and use last-known value. SOFR averages are immaterial while the book is 100% fixed — do not block the run on them.

---

## Publication Guard (v1.1) — REQUIRED for all Notion writes in this skill

This skill follows the v1.1 publication-guard pattern documented at `C:\Users\Owner\OneDrive - Oxford Capital Partners (1)\Documents\Claude\Scheduled\_shared\PUBLICATION_GUARD.md`. Apply these five steps every time this skill calls `notion-create-pages`. This guard SUPERSEDES any prior in-body instructions to "log failure inline" or "do not retry more than once" — those were v1.0 conventions and are now obsolete.

1. **Capture** — invoke `notion-create-pages(parent=…, pages=[…])`. Capture `response.pages[0].id` as `publishedId` and `.url` as `publishedUrl`.
2. **Retry once** — if `publishedId` is null, undefined, an error code, or the response itself errored, retry the same `notion-create-pages` call exactly ONCE. Do not loop.
3. **Search-verify** — call `notion-search(query=<literal title used in Step 1>, filters={created_date_range: {start: today, end: today+1}})`. Confirm the returned page ID matches `publishedId`. If no match or different ID, treat as publication failure → Step 4.
4. **Outlook fallback (auto-send)** — IFF Steps 1+2+3 all failed, AUTO-SEND via Composio `OUTLOOK_SEND_EMAIL` with `account_id="me"`, `to="ggoldberg@oxfordra.net"`, `subject="❌ ora-debt-maturity-snapshot PUBLICATION FAILED — <YYYY-MM-DD>"`, body containing what the page WOULD have contained verbatim, plus the Notion API error verbatim, body_tag `"AUTO-SENT — meta-failure path, no human-in-loop available"`. This auto-send overrides the default "draft, don't send" rule because the skill's audit/monitoring function is meaningless if its publication fails silently.
5. **Failure-mode logging** — append a single line to the skill's chat-summary output: `Publish: [✅ direct | ✅ retry | ❌ fallback-sent | ❌❌ total-blackout]`.

---

*Guard added 2026-05-10 per P0-2 tier-2/3 rollout (2026-05-08 health review). Reference: `_shared\PUBLICATION_GUARD.md` v1.1.*

*2026-05-29 — §1 rewritten to a 3-tier rate-retrieval hierarchy (FRED API primary → Notion "Rate Snapshot — Current" prefetch → WebSearch). Root cause of recurring 30D/90D SOFR carryforward flags: FRED series HTML page serves a stale cached observation, and the `.txt`/data endpoints failed `web_fetch` provenance because the absolute URLs were never surfaced in-run. Fix: canonical FRED API URLs are now embedded verbatim in §1a (provenance-valid) and return a single latest JSON record. FRED API key provisioned 2026-05-29 — hierarchy live.*