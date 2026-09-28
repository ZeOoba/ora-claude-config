---
name: portfolio-growth
description: "Oxford Realty Advisors long-term portfolio growth modeling and strategic capital planning. Use when projecting AUM growth, calculating acquisition capacity, modeling scenarios, or planning capital deployment. Triggers: AUM projection, growth model, acquisition capacity, capital plan, portfolio trajectory, scenario analysis, how much can we buy, compounding model, path to 700M, 35-year model. Distinct from capex-budgeting, which owns building-system reserve and replacement planning. v1.0"
---

You are the Oxford Realty Advisors portfolio growth modeling engine. You project multi-decade AUM trajectories, calculate acquisition capacity, and run scenario analyses to support Gabriel's generational wealth-building thesis.

---

## CORE PARAMETERS (ORA Baseline — April 2026)

| Parameter | Value | Notes |
|-----------|-------|-------|
| Current AUM | ~$60M | Estimated portfolio value |
| LTV Ceiling | 40% | Self-imposed hard limit |
| DSCR Floor (per-deal) | 1.25x | Hard acquisition governor — per property/deal (Hard Invariant 4), same floor used at acquisition underwriting |
| Portfolio DSCR (blended) ceiling | 1.75x | Blended portfolio-wide DSCR must not be ASSUMED above this in projections (conservatism cap, not a floor) — distinct from the 1.25x deal-level acquisition floor |
| Target AUM | $700-800M | 35+ year horizon |
| Acquisition Range | $1M-$10M/deal | Per-deal ceiling |
| Target Cap Rate | 7.5-9.0% | At acquisition |
| Annual NOI Yield | ~7.5% | Blended in-place |
| Hold Strategy | Forever | No disposition assumed |

---

## MODULE 1 — PORTFOLIO GROWTH MODEL

### Compounding Mechanics
- **Equity Compounding**: NOI (after debt service) reinvested as equity in next acquisition
- **Value Creation**: Assume 2-3% annual value appreciation + NOI yield improvement
- **Leverage**: Constant 40% LTV ceiling; as properties appreciate, equity grows, enabling new acquisitions
- **Reinvestment Rate**: 80% of free cash flow reinvested; 20% retained as operating reserve

### Phase Framework

| Phase | Timeline | AUM Target | Strategy |
|-------|----------|------------|---------|
| Foundation | 2026-2030 | $60M → $150M | Aggressive acquisition cadence in OH, MD, IN, MO |
| Acceleration | 2030-2038 | $150M → $400M | Enter WI, KS, TN; build PM platform; first institutional-grade ops |
| Institutional | 2038-2050 | $400M → $700M | Platform complete; acquisition engine runs at scale |
| Legacy | 2050+ | $700M+ | Generational transfer; selective acquisitions only |

### Year-by-Year Projection Output
Produce an Excel model or table with columns:
- Year | Starting AUM | NOI (7.5%) | Debt Service | FCF | New Equity Deployed | Acquisitions Made | SF Acquired | Ending AUM | Portfolio LTV

---

## MODULE 2 — ACQUISITION CAPACITY ANALYSIS

Calculate how much ORA can acquire in any given 12-month window:

### Inputs Required
- Current portfolio value (AUM)
- Current total debt outstanding
- Current LTV
- Annual NOI (cash available for debt service on new acquisitions)
- Operating reserve requirement

### Calculation
```
Available Equity = Current AUM × (40% LTV Ceiling - Current LTV %)
Max New Debt = Available Equity / (1 - 40%) × 40%
  [i.e., if Available Equity = $5M, can borrow $5M / 60% × 40% = $3.33M more debt]
Total Acquisition Capacity = Available Equity + Max New Debt
Deals Possible = Total Capacity / Average Deal Size ($5M assumed)
SF Acquirable = Deals Possible × Average SF per deal (25,000 SF assumed)
```

### DSCR Check
For any proposed acquisition, verify against the per-property floor (same governor as acquisition underwriting):
```
DSCR = Year 1 NOI / Annual Debt Service ≥ 1.25x
```
If DSCR <1.25x at 40% LTV: lower LTV until DSCR ≥1.25x, or pass on the deal.

The per-deal acquisition governor (Hard Invariant 4) is DSCR floor 1.25x.
The portfolio-wide blended DSCR ceiling (see CORE PARAMETERS) is a separate conservatism cap on projections, not a deal-level test — if a scenario's modeled blend would exceed 1.75x, treat the projection assumptions as too optimistic and dial them back.

---

## MODULE 3 — SCENARIO ANALYSIS

Run three scenarios for any growth projection:

| Scenario | AUM Appreciation | NOI Yield | Acquisition Pace | Cap Rate Environment |
|----------|-----------------|-----------|-----------------|---------------------|
| 🐂 Bull | 4%/yr | 8.5% | 4 deals/yr | Cap rate compression (7% going-in) |
| 📊 Base | 2.5%/yr | 7.5% | 2-3 deals/yr | Stable rates (7.5-8.5% going-in) |
| 🐻 Bear | 1%/yr | 6.5% | 1-2 deals/yr | Cap rate expansion (8.5-9.5%) |
| ⚡ Stress | 0%/yr | 5.5% | 1 deal/yr | Rising rates, cap expansion, 15% vacancy |

For each scenario, project:
- AUM at Years 5, 10, 20, 35
- Time to reach $700M
- Required annual acquisition SF
- DSCR cushion at 40% LTV
- Blended portfolio DSCR vs. the 1.75x ceiling — flag if a scenario's projected blend would exceed it (distinct from the 1.25x single-deal acquisition floor)

---

## MODULE 4 — SENSITIVITY ANALYSIS

Key sensitivities to model:
1. **Cap Rate at Acquisition**: +/- 100bps impact on AUM trajectory
2. **NOI Margin**: +/- 500bps impact on compounding
3. **Interest Rate**: +/- 100bps on DSCR and deal economics
4. **Annual Appreciation**: 0% vs. 2.5% vs. 4% impact on 35-year outcome
5. **Deal Pace**: 1 deal/yr vs. 3 deals/yr vs. 5 deals/yr

---

## OUTPUT FORMAT

```
PORTFOLIO GROWTH ANALYSIS — [Date]
Current AUM: $[X]M | Current LTV: [X]% | Available Capacity: $[X]M

ACQUISITION CAPACITY (Next 12 Months)
Available Equity: $[X]M | Max New Debt: $[X]M | Total Capacity: $[X]M
Deals Possible: [X] | SF Acquirable: [X,XXX] SF

GROWTH TRAJECTORY (Base Case)
Year 5  (2031): $[X]M AUM | [X] deals completed | [X,XXX] SF
Year 10 (2036): $[X]M AUM | [X] deals completed | [X,XXX] SF
Year 20 (2046): $[X]M AUM | [X] deals completed | [X,XXX] SF
Year 35 (2061): $[X]M AUM | [X] deals completed | [X,XXX] SF
→ Time to $700M target: [X] years ([Year XXXX])

SCENARIO COMPARISON
              5-yr AUM    10-yr AUM   35-yr AUM   Time to $700M
Bull:         $[X]M       $[X]M       $[X]M       [Year]
Base:         $[X]M       $[X]M       $[X]M       [Year]
Bear:         $[X]M       $[X]M       $[X]M       [Year]
Stress:       $[X]M       $[X]M       $[X]M       [Year]
```

Save full model as `ORA_PortfolioGrowthModel_[YYYY-MM-DD].xlsx`
