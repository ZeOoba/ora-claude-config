---
name: deal-1100-rarig-disposition-2026-07
description: "1100 Rarig Ave disposition-analysis (2026-07-09): HOLD recommended — unencumbered, 100% occupied, sale would be ~40%-effective pure recapture. Data gaps + Tenant DB integrity issue on this property."
metadata:
  type: project
  originSessionId: a744d8cf-2abe-4151-98ea-2bd224723db2
---

# 1100 Rarig Ave — Disposition Analysis (2026-07-09)

Ran as a standing portfolio-health check (no trigger from Gabriel) via the `disposition-analysis` skill. Full memo delivered in-session; key facts worth carrying forward:

**Asset facts (sourced, not modeled):** Purchased $1,800,000 (10/6/2023, ALTA settlement), entity "1100 Rarig Ave, LLC." **Unencumbered** — no acquisition loan, zero interest expense across 2024/2025/2026 P&Ls. Cost-seg study (6/2024): $100,800 5-yr / $115,200 15-yr / $1,224,000 39-yr ($360K land). 14 units, ~21,000 SF, 100% occupied, $246,886/yr scheduled rent. NOI: 2024 $105,648 → 2025 $153,664 (stabilized, after a Board of Revision tax appeal cut RE tax [⚠ 2026-09-19: DIRECTION UNVERIFIED and possibly INVERTED — ORA's filed BOR papers show school-board/third-party complaints seeking to RAISE the value from $1,113,500 to $1,800,000, and the 2024 P&L shows RE tax $43,321; see reference_tax_appeal_sweep_2026-09-19_no_candidates_underassessed.md before citing this] $43,322→$28,771) → 2026-YTD $101,498.

**Recommendation: HOLD.** Bought at bottom of replacement cost, debt-free, 100% occupied. A taxable sale would price near flat-to-basis, meaning the gain is almost entirely **depreciation recapture** (ordinary/25% rates, no LTCG benefit) — roughly 40% effective tax with the estate step-up forfeited. A refi at the 40% LTV ceiling could pull **~$760K tax-free today** if liquidity is ever needed — pro-forma debt service coverage on this asset comes out around 2.4x, comfortably above the floor — and this dominates any sale rationale.

**Why this matters going forward:** don't re-run this from scratch — the facts above (basis, cost-seg pools, unencumbered status, NOI trend) are now known and sourced from the deal folder + P&Ls, not memory-fabricated. Re-verify only if a real trigger (liquidity need, forced sale, market-peak harvest) actually arises.

**How to apply:** if Gabriel raises a 1031 or sale question on this asset, start from the HOLD conclusion above and ask what changed (new trigger) rather than rebuilding the base case. If liquidity is ever needed, lead with the refi lever before any 1031/sale discussion.

## Data gaps still open (needs Gabriel or a QuickBooks export)
1. **Accumulated depreciation claimed** (Form 4562 / QB Desktop fixed-asset register) — only the cost-seg *pools* are known, not depreciation actually taken. QB Desktop requires a human-operated CloudVara RDP session; not agent-accessible.
2. **Current market value** — no validated Columbus cap rate in [markets.md](markets.md); the $1.81–2.05M band used was [SPECULATIVE] (7.5–8.5% cap on 2025 NOI). Needs a BOV/appraisal to firm up any real disposition math.
3. **ORA Taxpayer Profile is undocumented** — REPS-qualified status, member-level marginal rates, and standing tax elections referenced by the `disposition-analysis` skill are **not written down anywhere in memory** (checked firm.md, user.md — both silent). Every disposition-analysis run for any property will hit this same gap until it's captured once, properly, from Gabriel or the CPA.
4. Current OH top individual rate — used ~3.5% as a placeholder; confirm (OH has been compressing brackets).

## Notion Tenant DB integrity issue — confirmed portfolio-wide, see [[reference_tenant_db_completeness_gap]]
A same-day spot-check confirmed this is NOT isolated to Rarig — see [reference_tenant_db_completeness_gap.md](reference_tenant_db_completeness_gap.md) for the full portfolio picture (one property with zero rows, 26% of all rows unlinked to any property, only 19 of ~27 properties represented in the schema at all).

Only **3 of 1100 Rarig's 14 units** exist as rows in the Tenant DB (Richwood/A, GT Industrial/F&I+J, Bakers/K) — the other 11 are invisible to any Notion-driven analytics (daily brief 4b/4c, exception-detection, etc.) for this property. Separately, the **Richwood Equipment Co. (Unit A)** row has Lease Start = Expiration = Next Escalation = **2026-05-01** (impossible zero-day term) with status still "Active" — root cause confirmed as a DB import error (start date copied into the expiration field); the rent roll shows this is actually a normal Velcani→Richwood succession (Velcani thru 4/30/2026, Richwood from 5/1/2026 at $1,300/mo). NOI durability is fine; only the DB row is broken. Recommend a full 14-unit reconciliation pass for this property and a correction to the Richwood row before any automated analytics consume it. Given this was found on one property by accident, worth a quick check whether other multi-tenant properties have the same row-completeness gap.

## Sources used (all real documents, no fabrication)
`1100 Rarig\1100 Rarig Settlement Statement.pdf` · `1100 Rarig\Cost Segregation Study.xlsx` + `Cost Segregation Final Report -- 1100 Rarig Ave 08.27.2024.pdf` · `Property Financials\P&L 2025/2024/2026 YTD -- 1100 Rarig.xlsx` · `1100 Rarig\Rent Roll -- 1100 Rarig Ave 10-10-2025.xlsx` · Notion Tenant DB (`collection://b12f4cfd-a995-4755-8341-6435ae8173b4`). The Notion "Property Record" relation is null on all three 1100 Rarig tenant rows — no asset-level Property Record exists in Notion for this property.
