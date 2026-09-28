---
name: solar-lease-underwriting
description: "Oxford Realty Advisors rooftop solar / community-solar lease underwriting skill. Use when evaluating, negotiating, or reviewing a rooftop solar, community solar, or PPA-style lease proposal (King Energy or any developer) before signature, or auditing an already-executed one. Trigger on: solar lease, rooftop lease, community solar, King Energy, roof rent, solar PPA, Site Access Fee, ITC, SREC, solar rent benchmark, should we lease our roof, solar developer proposal, solar lease economics, King Energy pitch. Companion to legal-intelligence (clause-level contract review) and acquisition-underwriting (whole-property acquisition) — this skill owns the counterparty-economics and rent-benchmarking layer specific to third-party rooftop energy leases. v1.1 (2026-08-15: see Changelog)."
---

# Solar / Rooftop Lease Underwriting (ORA) — v1.0

## Scope and skill tie-break

- **This skill** owns: rent benchmarking against market, the developer's-side pro forma (their expected IRR), the red-flag checklist, and the negotiation punch list for rooftop solar / community-solar leases.
- **legal-intelligence** owns clause-level contract analysis (indemnification, SNDA, insurance, default mechanics) — run it in parallel on the actual lease document; don't duplicate its job here.
- **acquisition-underwriting** owns whole-property acquisitions. A solar rooftop lease on a property ORA ALREADY OWNS is this skill's job, not acquisition-underwriting's, even though the buy-box/scorecard mental model (benchmark against comps, flag deviations, produce a recommendation) is deliberately similar.
- Deal pattern covered: a developer (King Energy or similar) leases roof space from ORA ("Host") to build and operate a rooftop PV system, typically enrolled in a state community solar program, paying Host a rent schedule while the developer retains 100% of ITC, depreciation, RECs, and subscription/SREC revenue. If a proposal instead has ORA self-developing or co-investing, route to portfolio-growth / debt-management for the capital-stack side and use this skill only for the comparative "what would leasing to a developer get us instead" baseline.

## Step 1 — Extract deal terms into a term sheet

Pull from the Lease + Order Form (King Energy's format: Lease + Attachment B Order Form + Exhibits is standard; other developers vary):

- System size (kW-DC), estimated annual production (kWh), roof SF occupied
- Full rent schedule by year band, including whether extension years (typically Year 26+ after a 25-yr initial term to a 34-yr cap) are priced — **flag immediately if extension-year rent is undefined; this is a recurring drafting gap** (found on the Red Branch deal, Order Form silent on Yr 26-34, while the Northwood deal for the same counterparty did define it at $75k/yr + CPI — inconsistent handling across deals from the same developer is a signal, not a coincidence).
- Any zero-rent introductory period and its length
- Revenue-share / production-linked / SREC-price-linked kicker, if any (expect none — flag if absent)
- Site Access Fee / roof capex reimbursement: amount, recoupment/clawback terms tied to early termination or rent abatement, and whether it is really a capex offset (funding work ORA would do anyway) vs. incremental value
- Termination provisions: Host redevelopment right, Host buyout right (basis: FMV of system), Default Event mechanics, and specifically the **Recapture Amount** clause — Host-caused early termination within the first several years typically requires reimbursing the developer's lost ITC. Extract the exact year cutoff and flag it as a contingent liability that constrains disposition/redevelopment optionality through that date.
- ITC/NTP financing contingencies: "3 years to finance+NTP or either party may terminate," "5 years or automatic termination," and any accelerated deadline tied to federal tax-credit phase-out rules in effect at signing (e.g., the OBBBA July 2026 begin-construction deadline referenced in 2026-vintage King Energy paper) — log ALL of these as dated entries in the ORA Critical Deadlines Tracker (Notion collection `c89df6f2-1d18-4341-9e57-6a15a696b14a`) at signature, not after the fact.
- Tenant/host subscription rights to the community solar output (expect none — flag if absent; this is a live negotiating ask)
- Liability cap and claims window (King Energy standard: $1M aggregate, 1-yr claims period) — sanity-check against the asset's fire/structural exposure, not against the deal size

## Step 2 — Benchmark the rent

Compute, on the actual (not headline) rent schedule:

- **$/kW-DC/yr** and **$/SF/yr**, both as a 25-year average (including any zero-rent years) and as the peak-tier rate
- Compare against recent ORA precedent for the same counterparty/program type before treating any single number as "market" — ORA's own two King Energy MD community solar deals priced within $41-60/kW/yr average and $0.41-0.73/SF/yr average but arrived there via very different zero-rent windows (5 vs. 10 years), so a same-counterparty comp can still hide a materially different NPV
- Never accept a comparison against a single anchor deal as sufficient — pull 2-3 external comps if available via acquisition-underwriting's COMP GRID DISCIPLINE (industrial comps only — see the gap noted in "Known gaps to close" below for why no solar-specific comp source exists yet) or market-monitor before calling a rate fair
- A **flat, non-escalating, non-revenue-linked** rent structure is the market default for this product — the negotiating lever is the floor rent and the length of any zero-rent period, not the escalated out-year rate, which developers will concede more easily since it's discounted furthest

## Step 3 — Model the developer's expected returns (SPECULATIVE unless developer discloses actuals)

Build an unlevered project pro forma from ORA's side of the table — this is inherently an outside view and must be labeled [SPECULATIVE]/[FORECAST]:

1. **Capex:** system kW-DC × current $/W-DC benchmark (source a current SEIA/NREL or Wood Mackenzie C&I benchmark, don't reuse a stale figure) + Site Access Fee (roof capex, paid by developer, NOT part of ITC-eligible basis)
2. **ITC:** current statutory rate × system capex only (not roof capex) — check current law/phase-down status, don't assume a rate from a prior year's memory
3. **Depreciation:** system capex less 50% of ITC value = depreciable basis; apply bonus depreciation rate in effect at signing (100% bonus depreciation restored under OBBBA for property placed in service after 1/19/2025, subject to change — verify current status) × corporate rate (21% federal) for the tax shield; note this figure is realized by the developer's tax equity structure, not received in cash 1:1 — apply a monetization haircut (~85-95%) for transferability/tax-equity execution costs
4. **Revenue:** production (with ~0.5%/yr degradation) × (a) subscription/bill-credit rate — **this is the single largest and least-sourced input; sweep a range ($0.07-$0.17/kWh has been used as an illustrative band, not a citation) rather than presenting one number as fact** — plus (b) production/1000 × current state SREC or equivalent REC price (source from a live SREC exchange/SACP figure, not memory)
5. **Costs:** O&M (~$10-18/kW-DC/yr, escalated), subscriber administration (~5-8% of subscription revenue), inverter replacement reserve mid-life, the actual negotiated rent schedule
6. Compute unlevered IRR and NPV; **always present as a sensitivity table across the subscription-rate and installed-cost assumptions**, never a single point estimate, and say plainly that the developer's actual levered/tax-equity sponsor IRR runs materially higher than the unlevered figure — that gap is normal for this asset class, not evidence of a bad model
7. Quantify the rent's contribution: rerun the same model with the rent schedule zeroed out and report the IRR delta in points. This turns "is the rent fair" into a number instead of a vibe, and is the single most persuasive exhibit in a renegotiation conversation.

## Step 4 — Red-flag checklist (apply to every proposal before recommending signature)

- [ ] Zero-rent period longer than ~3-5 years with no floor rent
- [ ] No revenue share, SREC-price kicker, or any upside participation for Host
- [ ] Extension-year (post-Year-25) rent undefined or missing CPI escalation
- [ ] No ORA/tenant subscription-rights carve-out
- [ ] Recapture Amount / early-termination exposure not quantified in dollars before signing
- [ ] Liability cap materially below plausible fire/structural exposure given system size and roof placement
- [ ] Site Access Fee recoupment terms not modeled against ORA's own early-exit scenarios (redevelopment, sale)
- [ ] ITC/NTP financing deadlines not yet logged in the Critical Deadlines Tracker
- [ ] Deal terms not benchmarked against at least one other comp (internal precedent or external)

## Step 5 — Should ORA self-develop instead?

Default answer is **no** unless ALL of the following hold: (a) ORA's entity structure has confirmed tax appetite to absorb the Year-1 ITC + bonus depreciation directly (verify with tax counsel — a family-office pass-through often does not, without a tax-equity partner, which erodes the theoretical edge), (b) ORA is prepared to take on EPC contracting, state program application risk (e.g., MD CSEGS), and utility interconnection risk, and (c) ORA has or will build subscriber acquisition/servicing capability for the community-solar revenue line, which is the largest and most execution-dependent part of the returns. Absent all three, the better lever is renegotiating lease terms (Step 4 punch list), not taking on development risk. Revisit only if ORA scales into a market where it already holds tax capacity and in-house asset management that can absorb O&M near-zero marginal cost.

## Step 6 — Output

Produce: (1) a term sheet extraction, (2) the rent benchmark table, (3) the sensitized developer pro forma with IRR-impact-of-rent, (4) the red-flag checklist with pass/fail, (5) a negotiation punch list for anything still executory, (6) Critical Deadlines Tracker rows for every date-driven contingency. Run the 16-point QC Gate before presenting if this is going into an institutional deliverable (IC-style memo); a working analysis for Gabriel's own review does not require the full gate but should still cite sources and label every modeled (non-contractual) number.

## Known gaps to close on the next cycle

- No external solar-rooftop-lease comp set exists yet in ORA's systems (acquisition-underwriting's COMP GRID DISCIPLINE and market-monitor are built for industrial rent/sale comps, not solar; the retired `rent-comp` skill, gone since 2026-08-05, never had one either). Building one is the single highest-value follow-on to this skill.

## Changelog

- v1.1 (2026-08-15): HIGH fix (Skill Text Audit finding F2). Step 2 and the "Known gaps" comp-sourcing mentions repointed from the retired `rent-comp` skill (gone 2026-08-05) to acquisition-underwriting's COMP GRID DISCIPLINE section (absorbed there 2026-08-12). Also deduplicated an accidentally doubled YAML frontmatter block (lines 1-9 previously repeated the `---`/`name`/`description` block twice) — no content or trigger-vocabulary change from the dedup itself. Description trimmed to a single trailing version tag with this history moved here, after the trim itself pushed the field to 1,035 chars (over the platform's 1,024-char limit that has broken `package_skills.py` before — see `parcel-data-recovery` v1.3). No benchmarking method, red-flag checklist, or pro-forma math changed.
- Subscription/bill-credit pricing for MD (and any future state) community solar programs is not sourced anywhere in ORA's knowledge base — worth a one-time research pass to replace the [SPECULATIVE] band in Step 3 with an actual cited range.

