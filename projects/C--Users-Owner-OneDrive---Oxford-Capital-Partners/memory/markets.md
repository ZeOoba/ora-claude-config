---
name: markets
description: "ORA market intelligence — cross-market snapshots, macro indicators, replacement-cost benchmarks, transaction comps, and Columbus submarket detail. Validated data only."
metadata: 
  node_type: memory
  type: reference
  originSessionId: 8ffab475-017d-4acd-9f70-f4496936d089
---

# ORA Market Intelligence

Merged 2026-06-03 from market_general.md + market_columbus.md. **Add entries only as Gabriel validates data during deal analysis / daily briefs; each entry cites source + date.** Live macro now comes from the FRED MCP (see [tech.md](tech.md)) rather than manual tracking.

## Cross-market snapshots (validated data only)
| Market | Avg Cap Rate | Avg Rent $/SF NNN | Vacancy | Last Updated |
|--------|-------------|-------------------|---------|--------------|
| Columbus OH | [GAP — no sub-$10M/small-deal series found; Midwest regional avg 7.43% per Matthews 2025 Cap Rate Recap is directional only, not metro-specific] | $6.57/SF NNN | 5.19% | Colliers Columbus Industrial Q1 2026, pub. ~Apr 2026 |
| Kansas City MO | [GAP — no sub-$10M-specific series found] | $5.49/SF (NNN status not stated by source) | 4.9% | CBRE Kansas City Industrial Figures Q4 2025, pub. Jan 2026 |
| Indianapolis IN | ~8.6% headline metro-wide implied [SPECULATIVE — source attribution unclear; no sub-$10M series] | $6.41/SF NNN overall; flex-specific $10.27/SF NNN | 6.8% | Colliers Indianapolis Industrial Q4 2025, pub. Jan 2026 |
| DC Metro / MD (Howard Co./I-270 corridor — not downtown DC) | Institutional-only: one large infill portfolio traded ~5.75% cap (Camber-PGIM, Jan 2026) — not representative of sub-$10M deals [GAP] | $11.04/SF (NNN status not confirmed) | 8.3% (trending ~9.7–9.9% per Q1 2026 commentary) | CBRE Baltimore Industrial Figures Q4 2025 + MacKenzie Commercial Q4 2025 Ind./Flex Report, pub. Jan 2026 |
| Baltimore | Same dataset as DC Metro/MD row — CBRE does not publish a distinct Baltimore-proper breakout separate from the Baltimore-Washington Corridor series [no independent figure found] | — | 8.3% | CBRE Baltimore Industrial Figures Q4 2025, pub. Jan 2026 |
| Cincinnati OH (primary cluster, added 2026-07-11 — row parity w/ market-monitor v1.1) | [GAP — no Cincinnati-specific sub-$10M series; generic 6.5–8.0% flex commentary found is unattributed, SPECULATIVE, not used] | $5.93/SF (NNN status not explicitly stated) | 5.3% | Colliers Cincinnati Industrial Report Q4 2025, pub. Jan 2026 |
| Madison WI (primary; relabeled 2026-07-11 from stale "Wisconsin (expansion)") | Not found — no cap rate series located at any deal size [GAP] | Not found from a primary brokerage source [omitted rather than fabricated] | 4.2% (reported vacancy has swung 1.8%→4.2%→6% across recent quarters/sources — thin inventory base amplifies volatility; treat as noisy) | Lee & Associates Madison WI Industrial Q1 2026, pub. ~Apr 2026 |
| Grand Rapids MI (entry cluster, added 2026-07-11) | — | — | — | — |
| Richmond VA (entry cluster, added 2026-07-11) | — | — | — | — |
| Des Moines IA (entry cluster, added 2026-07-11) | 7.0–7.6% [SPECULATIVE — Matthews/aggregator 2025, no metro broker print] | $6.90/SF blended NNN (mfg $6.40 · whse $7.00 · flex $9.40) | 7.5% | Colliers Q4 2025 (via market-monitor skill v1.1) — carried from skill's brokerage research, NOT independently Gabriel-validated; refresh quarterly and confirm at deal level before relying on it |
| Chicago–Greater Cook County IL (entry cluster, ratified 2026-09-29 as the 11th canonical cluster — all of Cook County; collar counties not satellites, Ruling 3) | 7.8% market cap (CoStar Near South Cook, all-industrial, BLENDED — not a sub-$10M series); ORA exit cap 8.00% | $10.40/SF (NNN status not stated by source; +4.2% YoY) | 6.2% (−70 bps YoY) | CoStar Near South Cook submarket summary, 2026-09-29 (other Cook submarkets not yet pulled); see target-markets.json v1.11 |
| Nashville TN (watch/adjacent; relabeled 2026-07-11 from stale "Tennessee (expansion)") | — | — | — | —

**Cap rate methodology flag (2026-07-11, from live research pass):** none of the 7 established markets above has a published, source-attributable cap rate series specific to sub-$10M/smaller multi-tenant or flex industrial — every cap-rate cell is either a headline institutional print, an unattributed generic range, or absent. A "7.5%→7.9%" figure surfaced identically across the Columbus/KC/Baltimore searches but traces to a generic **national** cap-rate trend chart, not a metro print — do not cite it as market-specific. Midwest regional average 7.43% (Matthews 2025 Cap Rate Recap) and national multi-tenant industrial ~6% are directional only. **Implication: continue underwriting sub-$10M deals off deal-level comps (see [standards.md](standards.md) Exit Cap table sourced from actual ORA models), not off these headline metro series — they were never fit for that purpose and this pass confirms no better series exists.** Grand Rapids/Richmond entry-cluster rows remain unpopulated this pass (out of scope — see market-monitor skill for their entry-cluster figures instead).

## Macro indicators
Pull live from FRED MCP: 10yr/5yr/2yr Treasury (DGS10/5/2), SOFR, MORTGAGE30US, CPI YoY, FEDFUNDS. (Verified 2026-05-31: DGS10 4.45%, SOFR 3.62%, MORTGAGE30US 6.53%, CPI YoY 3.78%.)

## Macro snapshot — 2026-06-11 (quarterly cadence; next due 2026-09)
Source: Notion "Rate Snapshot — Current" (page `35e6ecd8-9e59-814f-ae22-fe99464084d1`, maintained daily by ora-am-brief Block A; this pull = 2026-06-10 06:18 ET run, prefetch SOURCE_DEGRADED — UST/PMMS/SOFR confirmed, BBB OAS approximate).
- **10Y UST 4.56%** (6/8 close, Fed H.15 confirmed; ~4.57% 6/9 per market reporting) · 2Y 4.15% · 5Y 4.29% · 30Y 5.03% · **10Y−2Y +41 bp**
- **Overnight SOFR 3.63%** (6/8, NY Fed) · Fed funds target 3.50–3.75% (effective 3.62%); June 16–17 FOMC priced ~96.5% hold, street shifting to no 2026 cuts
- **30Y fixed mortgage 6.48%** (Freddie PMMS wk of 6/4; prior 6.53%, yr-ago 6.85%)
- BBB OAS ≈100 bp [APPROX — web-sourced; FRED blocked that run]
**Buy-box read:** at current debt costs (~10Y+200–250 bp → ~6.5–7.0% coupon, 25-yr am, debt constant ≈8.5%), the LTV ≤40% governor means DSCR 1.25× binds only below a ~4.2% going-in cap — ORA's 8%+ cap targets clear it ~2.4×. The binding hurdles at these rates remain the yield/basis floors, not debt service. (Governor values unchanged: DSCR ≥1.25× / LTV ≤40%.)

## Replacement-cost benchmarks
ORA general range **$85–$120/SF** (by market + building class). Market-specific validated figures: pending.

## Transaction comps (validated pricing only)
| Date | Property | Market | SF | Price | $/SF | Cap Rate | Source |
|------|----------|--------|----|-------|------|----------|--------|
| — | — | — | — | — | — | — | — |

## Columbus OH — submarket notes
- **East Side (E. Fulton St area):** E. Fulton Street Portfolio — 202,164 SF, 5 buildings, $4M ask ($19.79/SF) — active acquisition. **[CONFIDENTIAL — internal only; materially impaired, confirmed TCE/chlorinated-solvent release, Phase II 2026-06-01. Never on any external surface.]**
- First validated Columbus data points will come from E. Fulton underwriting + rent-comp research.
