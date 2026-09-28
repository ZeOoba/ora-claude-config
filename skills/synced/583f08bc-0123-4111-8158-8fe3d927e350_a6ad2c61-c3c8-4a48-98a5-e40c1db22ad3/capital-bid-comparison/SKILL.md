---
name: capital-bid-comparison
description: "Level two or more contractor proposals for the same building-system scope into a comparable basis, code-check each, allocate risk, and produce an award recommendation plus per-contractor RFI lists. Trigger on: compare these proposals, bid comparison, bid leveling, normalize these bids, apples to apples, which contractor should we use, award recommendation, scope gap, RFI list, or two or more uploaded proposals for the same work. Hands the winning bid to vendor-management QC before signature."
---

# Capital Bid Comparison

Multi-bid leveling for repeat-trade and capital work on ORA-owned assets. This skill
runs **before** award and **before** `vendor-management` QC mode. The sequence is fixed:

> **level → code-check → allocate risk → RFI → recommend award → `vendor-management` QC → signature**

One proposal is not a comparison. On a single bid, say so, run the code and risk passes
anyway, and state what a second bid would test.

## Why this exists

Seed pair: the **9050 Red Branch Rd Unit K rooftop replacement**, 2026-09-17. Two HVAC
proposals, $1,100 apart on a ~$28K job — a 4.0% spread that read as a price decision and
was not one.

| | Hayden Mechanical | JEM Heating & A/C |
|---|---|---|
| As bid | $27,600 | $28,700 |
| Economizer, duct smoke detector, permit | included | **absent** |
| Two-zone control, bypass damper, duct mods | **absent** | included |
| Normalized | ~$30.6–32.6K | ~$30.8–32.5K |

Three findings drove the design:

1. **The spread was not the price, it was the scope.** Normalized, the two bids converge
   inside $500. Every minute spent on the $1,100 was a minute not spent on the fact that
   one bid omitted an economizer that IECC 2021 very likely requires and the other omitted
   the zone controls that are the tenant's actual complaint.
2. **Absences do not appear in a price table.** The lower bid carried the code items; the
   higher bid carried no permit, no economizer, no smoke detector, and **no exclusions at
   all**. An absent exclusion list is ambiguity, not protection.
3. **The party and payment blocks decided more money than the equipment did.** One quote
   was billed to the *tenant*, not the owning LLC, so the labor warranty ran to someone
   else. One demanded 80% before the unit was set; the other took nothing until
   completion. Neither fact is in the scope narrative.

## Step 1 — Establish the basis before reading either price

Record, for the record and in this order:

1. **The asset.** Pull it from the Building Asset Register (`capital-asset-register`). If
   the asset is not registered, or its nameplate is unverified, register it now — the
   existing equipment's age, model and capacity are inputs to this comparison, not
   trivia. On the seed pair nobody knew the unit's age until a *bidder* read the plate.
2. **The contracting entity.** The ORA property entity that owns the asset, from the **ORA
   Master Workbook** (SharePoint, per Notion pointer page
   `3706ecd8-9e59-813a-b4c7-ecbc2c213fa8`). Never from a proposal's recitals, never from
   the property manager's email, never from memory. Note that the Notion 🏢 Property
   Register carries a `Property Entity / LLC` field that is **empty for some properties** —
   an empty field is not an answer.
3. **Who owes the work.** Read the governing lease before pricing anything. Landlord
   capital, tenant obligation, and landlord-capital-amortizable-into-CAM are three
   different answers with three different economics. Record it on the asset row.
4. **Whether each bidder can be awarded at all.** See Step 5.

## Step 2 — Level the scope (before price)

Normalize to the trade's unit, then compare. Trades quote different quantities, depths,
thicknesses and inclusions for the same physical job.

| Trade | Normalize to | Equalize these before comparing price |
|---|---|---|
| HVAC — packaged / RTU | **$/ton installed** | tonnage; gas input MBH; IEER/EER; refrigerant; curb adapter vs direct fit; economizer; DCV; duct smoke detector; permit; crane; disposal; zone controls; startup and commissioning scope |
| HVAC — split / VRF | **$/ton installed** | line-set reuse vs new; diffuser work; condensate pump; electrical reuse |
| Roofing | **$/SF by system and mil** | membrane type; mil thickness; insulation R and layer count; tear-off vs recover; fastened vs adhered; edge metal; **warranty term AND type (NDL vs material-only)** |
| Paving | **$/SY at a stated depth** | square yards; mill depth; coat count; base-repair SY; striping stalls; whether subgrade investigation was purchased |
| Electrical service | **$/amp, or per item** | service size; panel vs feeder vs both; utility coordination; load calculation; permit |
| Overhead doors | **$/door at size and spec** | clear opening; spring cycle rating; panel R-value; opener HP; track type |
| Fire / life safety | **per device + per riser** | device count; panel replace vs retrofit; monitoring term; AHJ acceptance testing |
| Plumbing / water heater | **per unit at capacity and recovery** | gallons; recovery rate; venting; expansion tank; code-triggered upgrades |
| Snow | **$/push + $/ton salt** | trigger depth; per-event vs seasonal cap; salt included; sidewalk and entry scope |
| Janitorial | **$/SF/month** | visit frequency; scope per visit; supplies included; day porter |
| Landscaping | **$/visit + $/season** | cuts per season; mulch CY; pruning cycles; irrigation start/stop |

Then publish a **normalized cost reconciliation** — as-bid, plus each side's priced gaps,
equals normalized. Show the arithmetic. Tag every gap estimate `[SPECULATIVE]` with a
range; a made-up point estimate in this table is worse than a range.

## Step 3 — Code-check each bid independently

A bid is not cheaper for omitting what the code requires. Check the **adopted edition in
that jurisdiction** — ORA spans OH, MD, IN, WI, MO, KS and TN and the editions differ.
Never carry a threshold from one state to another.

| Trade | Check |
|---|---|
| HVAC | Economizer (IECC 2021 C403.5 — 54,000 Btu/h threshold; Columbia MD is CZ4A). Return-air duct smoke detection (IMC 606, air-moving systems over 2,000 cfm — a 7.5-ton unit is ~3,000 cfm). DCV (C403.7.4, occupant-density triggered — verify the density, do not assume it). A2L refrigerant compliance (AIM Act, post-2025 manufacture). Mechanical permit. Roof-load certification where operating weight rises materially. Condensate and gas venting. |
| Roofing | Uplift and fastening per ASCE 7 plus local wind speed. Insulation R per IECC C402. Secondary drainage. Fire classification. Permit. |
| Paving | **ADA accessible route, stall count and van-accessible ratio.** Restriping changes stall geometry and is the most commonly missed compliance trap in the trade. |
| Electrical | Adopted NEC edition. Load calculation. Service and disconnect labeling. Permit. |
| Fire / life safety | NFPA 13 / 25 / 72 adopted editions. AHJ acceptance testing. Monitoring continuity during cutover. |

Also check **who is pulling the permit**. Silence is not an exemption. A jurisdiction that
has recently stood up a dedicated commercial mechanical permitting program — Howard
County MD did in April 2025 — is actively enforcing. Unpermitted work surfaces at
refinance, sale, insurance renewal and tenant estoppel, which is to say at the worst
possible moments.

## Step 4 — Allocate risk, in three tiers

Same discipline as `vendor-management` Step 4. A review that flags everything trains
Gabriel to ignore the review.

- **Non-negotiable** — correct contracting entity; insurance as a condition precedent to
  mobilization; permit responsibility; an enforceable warranty.
- **Priced** — payment structure, schedule commitment, price-hold, escalator caps,
  concealed-condition caps. Say what each costs.
- **Accept and note** — genuinely trade-standard allocations, recorded so the next
  comparison does not relitigate them.

Run the **payment-leverage test** on every bid: compute the dollars paid before
substantial completion and the dollars still retained at punch list. Report both in
dollars, not percentages — "80% paid before the unit is set" reads differently as
"$22,080 out the door with $5,520 of leverage left." Recommend retainage to passed
inspection.

An **absent exclusion list is a finding, not a convenience.** Report it as ambiguity that
resolves against ORA, and ask for one.

## Step 5 — The three gates that cost money when skipped

Run all three on every comparison. Each exists because it was missed once.

1. **Prequalification gate.** No award issues against a vendor whose Notion `Prequal
   Status` is *Bid-Only — Not Prequalified*. COI naming the ORA property entity as
   additional insured, license number, W-9 and Workers Comp are collected **before** the
   award, not after. Route to `vendor-management` MANAGE mode to run it.
2. **Utility incentive gate — mandatory on any equipment replacement over $10,000.**
   Identify the serving utility and check the commercial prescriptive program before
   award, because the eligible specification has to be in the awarded scope. In BGE
   territory that is Smart Energy Savers. Record the outcome on the asset row's `Rebate
   Status`; *Not Checked* after an award is a process failure. Where ORA funds the capital
   and the tenant pays the utility, say so plainly — the efficiency savings accrue to the
   tenant, so an incentive is often the only thing that makes an efficiency upgrade
   rational for ORA.
3. **Roof-coordination gate — mandatory whenever any trade mobilizes onto a roof.** Not
   only roofing work: a crane set, a curb adapter, a new penetration, or an HVAC change-out
   all qualify. HVAC and roofing proposals both routinely exclude roofing. Before award,
   assign in writing (a) who patches and warrants the membrane at every penetration and
   (b) whether the building's roof warranty survives the work. Price the roofer's
   attendance as a line item. A $28K mechanical job can void a roof warranty worth many
   multiples of itself.

## Step 6 — Check the physical evidence against the scope

Read embedded photographs, aerials and site notes against the priced scope. Where they
disagree, say so. Note also what **each bidder observed that the other did not** — on the
seed pair one bidder captured the existing unit's nameplate and age while the other caught
an unsealed exhaust opening to the exterior. Neither did both, and the union of their
observations is a better picture of the asset than either bid alone. Every such item is
either in someone's scope or it is nobody's; assign it.

## Step 7 — Report and recommend

Deliver in this order:

1. **Verdict** — one paragraph, naming the awardee and the conditions of award.
2. **What is actually being compared** — the scope divergence, stated before any price.
3. **Side-by-side table** and the **normalized cost reconciliation**.
4. **Pros and cons per bidder** — specific, quantified, no filler on either side.
5. **Risks neither bid covers** — ORA's own exposures.
6. **Award recommendation with numbered conditions** — entity, payment structure,
   specification changes, insurance, add-alternates.
7. **Per-contractor RFI lists** — separate lists, each ordered scope-and-code first,
   commercial second. These are drafts; see Hard rules.
8. **What would change the recommendation** — the specific finding that would flip it.

Deliver as DOCX per the ORA Institutional Style Guide with the 16-point QC Gate applied,
naming files `YYYY-MM-DD_[Property]_[Trade]-BidEval_v##.docx`.

## Scope boundaries

| Situation | Skill |
|---|---|
| Two or more proposals, same building-system scope | **this skill** |
| One proposal, pre-signature defect scan (27 checks, VC-1…VC-18) | `vendor-management` QC mode |
| Vendor onboarding, prequal roster, COI sweep, performance review | `vendor-management` MANAGE mode |
| The asset's identity, age, remaining life, replacement pipeline | `capital-asset-register` |
| Whether the capital item belongs in the annual budget | `annual-cycle` |
| Comparing acquisition targets (not contractor bids) | `deal-comparison` |
| Lender term sheets and debt pricing | `debt-management` |
| Insurance renewal and carrier comparison | `insurance-renewal-review` |
| Property management agreement | `pma-qc` |
| Broker listing agreement | `listing-agreement-qc` |
| Negotiated AIA-family construction contract | `legal-intelligence` |
| Drafting the award, negotiation or declination email | `communication-intelligence` |

## Hard rules

- This skill **recommends**. It never awards and never sends. An RFI, an award, a
  negotiation or a declination going to a contractor is an outbound communication to an
  external counterparty and requires Gabriel's explicit in-turn confirmation (standing
  invariant 1).
- **Never confirm the contracting entity from a proposal, from a manager's email, or from
  memory.** Read the ORA Master Workbook. An empty `Property Entity / LLC` field in Notion
  is a gap to escalate, not a blank to fill by inference.
- **Never present a scope-gap cost estimate as a firm number.** Tag `[SPECULATIVE]`, give a
  range, and say what would tighten it.
- **Never call a bid cheaper until it is leveled.** Price comparison before scope
  normalization is the error this skill exists to prevent.
- **Never recommend award to a Bid-Only vendor.** The prequal gate is not advisory.
- Do not decode an equipment model number from memory. Verify the model, capacity,
  efficiency and refrigerant against the manufacturer's published data, and state what
  could not be verified.
- A two-bid field on a capital item is thin. Say so, and recommend a third bid unless the
  asset is down or a stated deadline makes the delay more expensive than the risk.
- The awarded bid still goes through `vendor-management` QC before signature. This skill
  does not substitute for that gate, and neither is legal advice.

## Changelog

- **v1.0 (2026-09-17) — initial.** Built from the 9050 Red Branch Rd Unit K rooftop pair
  (Hayden $27,600 / JEM $28,700, 2026-09-17). Carries the standing normalization table
  (11 trades), the code-check matrix (5 trades), the three gates — prequalification,
  utility incentive over $10K, roof coordination — and the payment-leverage test.
  Instituted as the sibling of `vendor-management` QC mode: multi-bid leveling routes
  here, single-document pre-signature defect scanning stays there, and the awarded bid
  passes through QC before signature. No QC check or standing position was altered.