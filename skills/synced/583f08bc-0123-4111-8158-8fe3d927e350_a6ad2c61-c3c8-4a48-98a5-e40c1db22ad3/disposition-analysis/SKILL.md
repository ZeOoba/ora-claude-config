---

name: disposition-analysis
description: Oxford Realty Advisors hold / refinance / 1031 / sell decision engine. Use when the user mentions: should we sell, hold or sell, disposition, dispose of, exit an asset, recycle or prune the portfolio, 1031, like-kind exchange, replace an asset, refinance vs sell, harvest gains, cash out, when to sell, or keeping vs selling a property. Defaults to HOLD + cash-out refinance for liquidity (ORA generational-hold doctrine); when capital is recycled the default exit is a 1031 exchange; a taxable sale is the rare exception that must clear a high bar. Charges the forfeited estate step-up and deferred depreciation recapture (Sec 1245 ordinary + unrecaptured Sec 1250 + LTCG + NIIT + state) against any taxable sale; models the 1031 deferral (carryover basis, 45/180-day, QI, boot) and the estate step-up overlay. Produces a hold/refi/1031/sell recommendation with tax-charged net proceeds. Conforms to the ORA Tax-Inclusive Underwriting Standard. Refi execution (term sheets, lender selection) routes to debt-management. v1.3
---

# Disposition Analysis — Oxford Realty Advisors (v1.3)

You are evaluating whether ORA should HOLD, REFINANCE, 1031-EXCHANGE, or make a TAXABLE SALE of an asset. ORA is a generational-hold family office; the burden of proof is on selling, and recycling is almost always done via 1031. Every analysis carries the tax overlay — a sale's "true" cost is the headline price minus the tax a hold would have avoided.

## Default posture (the thumb on the scale)
1. **HOLD + cash-out refinance is the default.** Debt is not income — a refi pulls tax-free liquidity without triggering gain, recapture, or forfeiting the step-up. Exhaust this before considering any sale.
2. **If capital must be recycled into a better asset, default to a 1031 exchange.** ORA almost always 1031s. This defers both capital gain and ALL recapture (§1245 + §1250) indefinitely via carryover basis.
3. **A taxable sale is the exception** — only when no like-kind replacement fits, the asset is structurally impaired, or a non-deferrable need exists. It must clear a high bar because it forfeits the step-up and crystallizes recapture.

## Workflow

### Step 1 — Why is a sale on the table?
Classify the trigger: liquidity need (→ refi first), underperformance / structural impairment (→ 1031 into better basis), market-peak harvesting (→ 1031, rarely taxable), portfolio rebalance / concentration, or forced (partnership, estate, lender). The trigger sets which paths are live.

### Step 2 — Build the HOLD case
Forward 5–10-yr NOI, refi capacity at 65% LTV (tax-free proceeds available now), continued after-tax IRR on the held basis (REPS-qualified, no recapture — per Taxpayer Profile). This is the benchmark every disposition path must beat.

### Step 3 — Quantify the disposition tax (the charge)
Compute, per the Tax-Inclusive Standard recapture block:
- Amount realized (net of selling costs) → adjusted basis (cost − accumulated depreciation incl. cost-seg) → total gain.
- Decompose: **§1245 recapture** (cost-seg personal property, ordinary up to 37% + 3.8% NIIT) → **unrecaptured §1250** (building SL, 25% + NIIT) → **LTCG** (appreciation above cost, 20% + NIIT) → **+ state** (OH + apportionment).
- Total tax on sale, and the **forfeited step-up** (the income tax heirs would never have paid). The cost of a taxable sale = sale tax + the present value of the step-up given up.

### Step 4 — Compare the four paths
Side by side, after-tax to ORA:
- **HOLD + refi:** tax-free liquidity now; keeps step-up; continued NOI growth.
- **1031 exchange (default recycle):** defers gain + recapture; carryover basis (depreciation does NOT reset — continue old schedule on the replacement); net equity rolls 100%. Model the replacement's basis and go-forward depreciation. Watch **boot** (cash or debt relief = taxable to that extent) — structure to avoid.
- **Taxable sale:** net proceeds AFTER the Step-3 tax charge; only wins if the redeployment return on the smaller after-tax pile beats hold + 1031.
- **Estate/transfer (generational):** for next-gen assets, the step-up at death eliminates all recapture — usually dominates a lifetime sale; layer valuation-discount gifting of LLC interests (balance vs forgone step-up).

### Step 5 — 1031 execution guardrails (when recycling)
- Like-kind = any US real property held for investment/business → broad (industrial ↔ flex ↔ land ↔ retail all qualify).
- **45-day** replacement identification, **180-day** close (or tax-return due date). Use a **Qualified Intermediary** — seller cannot touch proceeds.
- **Equal-or-up rule:** replace equal/greater value AND equity AND debt to fully defer; any shortfall (cash or debt relief) = taxable boot.
- Reverse and improvement exchanges available if timing/identification is tight.
- Basis carries over (minus boot, plus new cash) → the replacement inherits a low basis and continues the old depreciation; factor this into the replacement's after-tax model.

### Step 6 — Recommendation
State HOLD / REFI / 1031 / SELL with the tax-charged numbers and the one-line reason. Default to the most tax-deferring path that meets the trigger; only recommend a taxable sale when it clears the hold-and-1031 benchmark after the full tax charge. Flag any boot, §461(l)/timing interaction, and the estate consequence.

### Step 7 — Log the ruling (2026-07-29)
Append one row to `memory/disposition-ledger.md` — the post-acquisition lifecycle ledger (Date | Property | Event | Terms/Amount | Rationale | Source). Event = the ruling (HOLD / REFI / 1031 / SELL); for a HOLD, Terms/Amount is "No transaction" plus the live refi lever if quantified. This is a DIFFERENT file from `memory/deal-decision-ledger.md`, which is scoped to PRE-acquisition pipeline decisions (PASS/SKIP/DROP/PARK/CLOSE) only — never write a disposition ruling there. If this is the property's first-ever row in disposition-ledger.md, also add the ACQUIRED baseline row (purchase price, date, source) before the new ruling row, so the ledger is self-contained per property.

## Conventions
- Pull defaults from the ORA Taxpayer Profile (REPS qualified, 1031 default, rates) and the Tax-Inclusive Underwriting Standard.
- Rates: §1245 ordinary 37% + 3.8% NIIT · unrecaptured §1250 25% + NIIT · LTCG 20% + NIIT · + OH state. Confirm current law / state with CPA.
- Never present a disposition without the forfeited-step-up + recapture charge. Refi-before-sale is the default. 1031-before-taxable-sale is the default for recycling.
- Output: concise decision memo (paths table + recommendation); for a live decision, build the four-path after-tax comparison in the IRR model.

## Cross-skill
acquisition-underwriting (replacement-asset underwrite for 1031 targets) · deal-comparison (replacement vs hold) · the IRR model's Tax Analysis tab (recapture block) · portfolio-reporting (concentration/rebalance triggers) · disposition-ledger.md (Step 7 log, new 2026-07-29).

## Changelog

- v1.3 (2026-09-07): ORA Automation Audit R23-9-adjacent — reciprocal to debt-management v1.4. Added a one-clause deferral: once refi is chosen, EXECUTION (term sheets, lender selection) routes to debt-management. This skill keeps ownership of the strategic hold/refi/1031/sell call itself. No model, tax treatment, or trigger vocabulary otherwise changed.
- v1.2 (2026-08-24): Description trimmed to restore headroom (was 1001/1024,
  headroom 23 -- close-out work-order item 4). Dropped the implementation-detail
  clause naming the ledger file path (the ledger itself, and every tax/exchange
  rule clause, is unchanged); no trigger vocabulary removed.
  `description_budget.py` now reports headroom 73.

