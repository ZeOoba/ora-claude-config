---
name: ora-millage-lookup
description: "Resolve a parcel's property-tax rate and taxable base from verified government endpoints for Oxford Realty Advisors acquisitions. Use whenever the user mentions: millage, mill rate, certified tax rate, effective tax rate, property tax lookup, tax rate by district, assessed value lookup, assessment lookup, taxable value, tax history, county assessor pull, auditor tax record, parcel tax record, reassessed tax, or when an acquisition SCREEN/UNDERWRITE has an unresolved property-tax figure. Companion to acquisition-underwriting STAGE 2.5 item 5 (millage lookup ladder), which caps any deal with an unknown reassessed tax at T2 WATCH. Distinct from tax-appeal, which owns the assessment-challenge workflow; this skill only resolves the rate and base. Produces a sourced rate + taxable-base block per parcel. v1.1 — changelog in body."
---

# ORA Millage & Assessment Lookup

Purpose: turn `[EST]` property-tax figures into sourced, reproducible ones. Under Buy Box v1.1 an unknown reassessed tax caps a deal at **T2 WATCH**, and `acquisition-underwriting` STAGE 2.5 item 5 makes a rate-pull attempt a **pre-FULL requirement** — this skill is that attempt, executed the same way every time.

Sibling to `ora-flood-zoning-dd`: same shape (a ladder over verified government endpoints, a registry in `references/endpoints.md`, an explicit UNVERIFIED verdict when every tier fails). Built 2026-08-03 once a second state/district static endpoint was confirmed, the threshold `acquisition-underwriting` v4.6 set for systematizing this.

## Decision rules

- A resolved figure carries **four** things or it is not resolved: the **rate**, its **unit**, the **taxable base** it applies to, and a **source + retrieval date**. A bare percentage is not an answer.
- **Never assert a rate without a named source and date.** If every tier fails, report **UNVERIFIED** explicitly and fall back to the State Reassessment Matrix range midpoint as `[EST]` — logging the specific attempts (tier, endpoint, date, what came back) per the pre-FULL requirement. A bare `[EST] — verify pre-LOI` with no attempt logged is INCOMPLETE for FULL mode.
- **The taxable base is not the headline assessment.** Phase-ins (DC, MD), caps (IN 3% GAV, IA 90% rollback), and abatements/PILOTs all drive a wedge between the assessment a portal displays and the value tax is actually computed on. Compute the pro-forma on the **post-sale reassessed** basis per the State Reassessment Matrix — never on the seller's in-place bill, and never on a displayed assessment you haven't reconciled to the bill.
- **A pulled rate describes the seller's year, not yours.** Rates move annually; a sale resets the base in most footprint states. The pull establishes the rate and the current base — the reassessment calculation still runs.
- **On tiers 2–3, get the MECHANISM, not the answer (added v1.1, 2026-08-24).** Tier 2 and tier 3 put you in front of a human at an assessor's or auditor's office, and the answers that come back are reassuringly conclusive — "your taxes won't change," "you'll be reassessed at sale," "there's no reassessment on a transfer here." **None of those is a filing path.** Push one level down every time and record it: **what instrument resets the base** (a transfer/conveyance form, a sales-disclosure filing, a new-owner declaration), **who files it and when**, **what triggers the recompute** (the sale itself, the next lien date, the next reappraisal cycle), and **when the new figure is certified**. A verbal "it won't change" that is really "it won't change until the January 1 lien date" is a different pro-forma from the same words meaning "this state doesn't reset on sale" — and the two are indistinguishable in a note that records only the answer. Where the mechanism can't be pinned down, that is an UNVERIFIED tier, not a resolved one. Same discipline as `ora-flood-zoning-dd` Step 6A applies to entitlements; see `acquisition-underwriting` STAGE 2.5 item 5.
- This skill **reads**. It never writes a determination into a master workbook in place — same rule as `ora-flood-zoning-dd` (copy to a new `YYYYMMDD_[Name]_v##.xlsx` first).

## The ladder (run in order; record which tier resolved it)

1. **State/county published static certified-rate document.** A state DOR/DLGF-style annual "Certified Tax Rates by District/County" PDF at a stable government URL. **PREFERRED whenever it exists** — fetchable, citable, search-indexable, no session required.
2. **Direct county assessor/auditor parcel record** — a REST/JSON service where one exists (see registry), otherwise the county's parcel-search page or a phone/portal query. A government REST service that answers a scripted query with no interactive session is **tier-1-equivalent**; treat it as tier 1 for citation purposes and say so.
3. **Interactive state/county GIS or tax portal** (e.g. Indiana's DLGF Gateway) — **LAST resort**. Not indexable by search, needs a live session; if reached only this way, log the query date and the screen values used.
4. **State Reassessment Matrix range midpoint**, `[EST]`, only after 1–3 are genuinely unattainable, with the attempts logged.

**Why the order:** tier 3 is exactly what a bare WebSearch reliably fails to reach, and tier 1 frequently succeeds where tier 3 doesn't — a static government PDF is a document, an interactive query tool is an application.

## Pitfalls — every one of these has produced a wrong or missing answer

1. **HTTP 200 with zero results is not "no data."** ArcGIS `/query` returns a full 200 response — field definitions, aliases, the lot — with an **empty `features` array** when the `where` clause matches nothing. A malformed key looks exactly like a parcel that doesn't exist. **Always check `len(features)`, never the status code or the response size.** (Confirmed 2026-08-03: a 26 KB, HTTP-200 DC response containing zero features.) This is the verified-null-vs-inferred-null rule in its most common concrete form.
2. **Parcel keys are often fixed-width composites.** DC's SSL is 4-char square + padding + 4-char lot — `SSL='0199    0821'` with **four** spaces resolves; one or two spaces returns the 200/zero-features above. When padding is uncertain, use a `LIKE` query (`SSL LIKE '0199%0821'`) and confirm you got exactly one feature.
3. **Do not "correct" a government URL.** Indiana's published filename is `2026_Certifed_Tax_Rates_By_District.pdf` — the typo (`Certifed`) is **in the state's own filename**. Verified 2026-08-03: the typo'd URL returns 200 (649,963 bytes); the correctly-spelled variant returns 404. Fetch the literal string in the registry.
4. **Units differ by state and are silently interchangeable-looking.** DC's `TAXRATE` field returns `1.65` meaning **$1.65 per $100** (= 1.65%); Indiana publishes a certified rate as a **percent of AV** (2.6830%); Michigan quotes **mills** (44.75 mills = 4.475%). Record the unit alongside the number, and sanity-check by reproducing the actual bill.
5. **Reconcile the rate against a real bill before trusting it.** `ANNUALTAX ÷ TAXRATE` recovers the taxable base; if that base is nowhere near any assessment field on the record, one of the three is wrong or a phase-in/abatement is in play. Do this check every time — it is one division and it catches unit errors, wrong-parcel pulls, and phase-in surprises at once.
6. **One parcel ≠ one deal.** Multi-parcel assemblages (and condo/underlying-lot structures) carry separate rates and bases. Pull each; never extrapolate one parcel's rate across a portfolio.

## Output block (paste into the facts file / IC memo §6 source note)

```
PARCEL      <address> — <county/district>, <state>  ·  key: <APN/SSL/parcel id>
RATE        <value> <unit>  (e.g. 1.65 per $100 = 1.65%)
TAXABLE     <base> — <how derived: field name, or ANNUALTAX ÷ RATE>
ASSESSMENT  current <x> / proposed <y>   [if the record carries both]
IN-PLACE    <seller's annual tax>  ·  history: <years available>
PRO-FORMA   <post-sale reassessed tax>  ·  <$/SF>   [per State Reassessment Matrix]
TIER        <1|2|3|4> — <endpoint or document>
SOURCE      <URL or office/method> · retrieved <YYYY-MM-DD>
```

Anything unresolved: state it as **UNVERIFIED** with the attempts logged, never as a silent `[EST]`.

## Registry

`references/endpoints.md` — per-state/district verified endpoints, status flags (V = live-verified with a date, U = unverified pattern / not yet discovered), and per-jurisdiction caveats. **Two entries are V today (Indiana DLGF, DC OTR/DCGIS); everything else is U.** That is a coverage statement, not a gap to paper over — an absent entry means run tier 2/3 by hand for that county and add what you find.

Cross-links: `county-parcel-screen`'s `references/county-endpoints.v1.json` (parcel/CAMA geometry layers, 22 counties) often carries the same service root as the assessor's tax record — check it before discovering an endpoint from scratch. `ora-flood-zoning-dd` Step 1 uses that same registry.

## Changelog

- v1.1 (2026-08-24): Added the **get-the-mechanism-not-the-answer** decision rule for tiers 2–3, where the source is a person at an assessor's or auditor's office rather than a document. The ladder was built to guarantee a *sourced* figure and says nothing about the difference between a favorable verbal answer and a reset mechanism — "your taxes won't change" is a sentence, not a filing path, and it can mean "not until the January 1 lien date" or "this state doesn't reset on sale," which are different pro-formas. The rule now requires the instrument that resets the base, who files it and when, what triggers the recompute, and when the figure is certified; a mechanism that can't be pinned down makes the tier UNVERIFIED, not resolved. Origin is the entitlement analogue at 754 Old State Route 74, where a written "no special approval needed" from a township turned out to sit on top of a minor-amendment application — encoded as `ora-flood-zoning-dd` Step 6A the same day. No ladder order, endpoint, or output field changed.
- v1.0 (2026-08-03): initial. Built out of `acquisition-underwriting` v4.7, which recorded the DC OTR/DCGIS endpoint as the second confirmed state/district static endpoint and thereby met the two-endpoint systematization threshold v4.6 had set. Ladder text is the canonical copy of Stage 2.5 item 5's; pitfalls 1–3 and 5 come from the 1518 K St NW underwrite and its 2026-08-03 merge-time re-verification.
