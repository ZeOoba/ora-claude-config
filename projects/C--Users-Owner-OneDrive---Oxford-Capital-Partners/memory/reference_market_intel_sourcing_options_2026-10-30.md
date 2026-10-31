---
name: reference_market_intel_sourcing_options_2026-10-30
description: 2026-10-30 /research verdict on improving news/transaction/market-intel sourcing — inbox-as-feed + state bulk sales feeds; verified free endpoints (Cook IL, Indiana SDF)
metadata:
  type: reference
---

Research verdict (2026-10-30, not yet built or ratified):

- Root problem: daily-brief/market-monitor fetch the open web, and the best CRE sources (bizjournals, GlobeSt, CoStar, Crexi, LoopNet) return 403. Only 3 of 11 clusters have a recorded-sales price feed (Franklin OH, Baltimore Co MD, Polk IA).
- Fix 1 — inbox-as-feed: those publishers deliver by email (newsletters, saved-search alerts). Route them to one Outlook folder and parse via the M365 `outlook_email_search` MCP. CoStar alert emails are already the TOS-compliant path ([[reference_costar_loopnet_subscriptions]]); the export-retention caveat still applies.
- Fix 2 — state bulk sales feeds into the county-sales Worker ([[reference_county_sales_monitor_worker]]):
  - Cook County IL: Socrata `datacatalog.cookcountyil.gov/resource/wvhk-k5uv.json`, anonymous. Fields include sale price, class, buyer and seller names. Max sale_date was 2026-08-12 when probed 2026-10-30. Data is unfiltered (non-arm's-length included).
  - Indiana: STATS Indiana SDF (`stats.indiana.edu/sdfdata/SDF_2026.zip`, 22MB, weekly Fri). **A partial-price comp source (final finding, P0 2026-10-30).** 142 of 545 industrial (3xx) SDFs statewide carry a price; unpriced rows carry `G_Confidential_Finance=Y`. Price is in cents, in E1 or G1 (Part G). Marion and Boone ARE present but named "MARION COUNTY" / "BOONE COUNTY" — normalize names before filtering. The earlier "47 of 545" and "Marion absent" claims were wrong (name mismatch, and the G1 field was missed). Cluster 2026 YTD: Marion 25/113 priced, Boone 17/17, Hamilton 8/9, Hendricks/Johnson/Hancock 0. Encodings: SALEDISC and SALECONTAC are UTF-16; SALEPARCEL is latin-1. Marion has no public building SF: IndyGIS `ESTSQFT` is land area, so building footprints are the only proxy.
  - Cook industrial building classes (Assessor classcode.pdf): 593, 663(A/B), 893, 583, 673. Last-12-month sales ~440, ~97% with price over $25k. SF and year built come from the Commercial Valuation dataset `csik-bsws` (bldgsf, yearbuilt, address).
  - Wisconsin RETR: DOR moved access into My Tax Account (notice 2026-02-24). Unverified.
  - Maryland SDAT statewide Real Property Assessments dataset: has last-sale fields. Unverified for commercial.
- Indianapolis plan (draft): `ora-county-sales-monitor/docs/plans/2026-10-30-indianapolis-comps-plan.md`. It splits public transfer events (SDF and county GIS) from price channels (inbox, manual), then joins them. Inbox check on 2026-10-30: **no CoStar alert emails since 2026-08-01**. Crexi mail is listings only. Connect CRE Midwest and M&M/CBRE blasts do arrive. Indiana deeds carry no price because the state has no transfer tax. DLGF posts only ratio-study narratives, not the county workbooks.
- KS/MO are non-disclosure states, so no vendor has true prices there; CoStar alerts plus broker contacts are the only path.

Fit with existing plans: once built, these sources belong in the Intelligence Platform facts layer ([[project_intelligence_platform_roadmap_ratified_2026-07-29]]).
