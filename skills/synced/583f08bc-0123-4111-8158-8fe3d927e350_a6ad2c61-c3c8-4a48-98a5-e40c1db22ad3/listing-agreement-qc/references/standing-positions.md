# ORA ratified standing positions — broker listing agreements

**Ratified: Gabriel Goldberg, 2026-08-17**, out of the 2000-2002 Zettler /
3875-3883 E Livingston comparative review. These are settled ORA policy on any
listing agreement where ORA is the Owner, on any broker's form. Apply by
default. Do not re-open unless the specific deal presents a reason to depart, and
record the departure in the deal-terms register when it does.

Each position carries the scanner check(s) in `scripts/listing_qc.py` that
enforce it and the replacement language to insert.

---

## SP-1 — One definition of gross sale price, and it is the computation paragraph
*Checks: L1, L15, L16, L18*

The C&W form carries two. The Rate paragraph says gross sale price "shall include
any and all consideration received including but not limited to release of
existing liabilities." The Computation paragraph — an ORA markup already present
on both agreements — limits it to (i) cash at closing and (ii) the outstanding
principal of debt assumed or taken subject to, with seller paper at present value
discounted at the prevailing market rate **as reasonably determined by Owner in
good faith**.

The two conflict. "Release of existing liabilities" is undefined and can be read
to reach a discounted payoff or lender forgiveness — neither of which is
consideration Owner receives, and both of which arise precisely in the distressed
scenario where ORA can least afford a phantom fee.

**Position.** The computation paragraph governs. Delete the final sentence of the
Rate paragraph, or subordinate it:

> "…computed as set forth under 'Computation of Total Sales Price' below, which
> shall govern."

Retain the present-value discount and the Owner-determines-the-rate formulation —
both are existing ORA wins and must survive any markup round.

Retain the purchase-option dollar-for-dollar credit ("in no event shall Broker be
compensated twice on the same underlying transaction").

---

## SP-2 — An Excluded Prospects exhibit is mandatory
*Check: L2*

No exclusive listing is signed without one. An exclusive right to sell combined
with the standard referral covenant means a full fee is owed on a buyer Owner
sourced entirely alone.

**Position.** Attach an exhibit naming, at minimum:

- every current tenant at the subject property, including any whose status is
  *Notice Given* or recently *Expired*;
- every tenant at **adjacent ORA properties** — these are the highest-probability
  unsourced buyers for a small freestanding building and the reason the exhibit
  exists;
- any counterparty already engaged as of commencement (prior LOI, broker
  conversation, inbound inquiry);
- ORA affiliates and entities under common control.

Fee treatment: **zero** for the first 90 days, then the Schedule rate if the
broker has actually performed on the prospect. Build with
`scripts/build_excluded_prospects.py`.

---

## SP-3 — Affiliate and involuntary transfers are carved out
*Check: L3*

The form reaches any conveyance where "title is conveyed in any manner" and any
sale of "any interest." As written that captures a contribution to a new ORA
entity, an intra-family or estate-planning transfer, a JV recapitalization, a
deed in lieu, and a condemnation taking — each at 4.00% to 6.00%.

**Position.** Insert:

> "No commission shall be payable on (a) a transfer to an affiliate of Owner or
> to any entity under common control with Owner, (b) a transfer for estate
> planning purposes or to a trust for the benefit of Owner's principals or their
> families, (c) a conveyance by foreclosure or deed in lieu of foreclosure, or
> (d) a taking by condemnation or eminent domain, or a conveyance in lieu
> thereof."

---

## SP-4 — Post-expiration extension is affirmative, never automatic
*Check: L4*

The form auto-continues month-to-month for twelve months after expiration. Stacked
with the post-term tail, a seven-and-a-half-month listing carries roughly **two
years and four months** of total exposure.

**Position.** Replace "shall continue" with "may be extended month-to-month by
written agreement of the parties."

---

## SP-5 — Mutual 30-day termination after day 90
*Check: L5*

The form's only termination right applies to the holdover period. During the
primary term Owner is locked with no performance or convenience out.

**Position.** Insert:

> "At any time after the ninetieth (90th) day of the Term, either party may
> terminate this agreement upon thirty (30) days' prior written notice to the
> other, without penalty. Termination shall not affect Broker's rights with
> respect to prospects properly listed under Section 5."

---

## SP-6 — The post-term tail is capped, procurement-limited, and conditioned
*Checks: L6, L7, L8*

Three separate defects in one clause.

**Position.**

1. **Cap.** The 270-day aggregate cap on the post-term protection period is an
   existing ORA win. It must survive every markup. If a new form omits it, it is a
   BLOCK.
2. **Procurement.** Limit the list to prospects "introduced to the Property by or
   through Broker, and to whom Broker provided substantive services during the
   Term." The form's "submitted by any party" language includes prospects ORA
   itself introduced.
3. **Condition precedent.** Make timely delivery of the list a condition
   precedent: "Broker's delivery of such list within ten (10) days after
   expiration of the primary Term shall be a condition precedent to any
   commission under this paragraph." Define "end of the term" as expiration of
   the **primary** term, since the term otherwise auto-extends into holdover.

---

## SP-7 — Scope conformance: no orphan lease machinery
*Checks: L10, L11*

A sale-only instrument must not retain tenant-procurement language. The Zettler
draft granted only "the exclusive right to sell," attached no lease rate table,
and still obligated the broker to "obtain a satisfactory purchaser **and
tenant(s)**" across six clauses. That is a broker tasked with procuring tenants at
no agreed price — a colorable quantum meruit claim benchmarked to the sister
agreement's 5.00% of years 1–5 base rent.

**Position.** Strike every tenant reference from a sale-only agreement, and add
the negative covenant:

> "No commission or other compensation shall be payable to Broker in connection
> with any lease, renewal, extension, expansion, or occupancy agreement at the
> Property."

Conversely, a lease-inclusive agreement must carry a lease rate table, a
cancellation-clause provision, and the sale-by-owner termination clause.

---

## SP-8 — Dual agency is transaction-specific, and the disclosure form is filed
*Checks: L12, L13*

The form grants blanket advance consent to the broker representing the buyer,
conditioned only on undefined "timely" disclosure. Ohio requires a
transaction-specific written dual-agency consent (R.C. 4735.71) and delivery of
the brokerage policy on agency (R.C. 4735.53, 4735.55). Neither ORA agreement
attaches an agency disclosure form.

**Position.** Replace "timely" with "prior to Broker commencing representation of
such purchaser," and add: "This consent does not waive Owner's right to a
transaction-specific written consent at the time any dual representation
arises." Request the broker's agency disclosure form for the deal folder in the
same markup.

---

## SP-9 — The broker never signs anything on ORA's behalf
*Check: L14*

Existing ORA win, present on both agreements. Must survive every markup.

> "Broker shall not have the authority to execute any lease, lease amendment,
> renewal, extension, purchase and sale agreement, or other instrument on behalf
> of Owner. All documentation shall be executed solely by Owner or its duly
> authorized representative."

---

## SP-10 — A co-broker dispute is never ORA's problem
*Check: L17*

Existing ORA win. Must survive every markup: an unresolved split between the
listing broker and an outside broker may not delay Owner's negotiations, and
Owner's obligation is capped at the amount computed under the Schedule.

---

## SP-11 — Lender consent is acknowledged on any financed asset
*Check: L19*

Neither ORA agreement acknowledges that a sale may require lender consent,
defeasance, or payoff. On an encumbered asset a broker can procure a
ready-willing-and-able buyer, be denied by the lender, and still argue the
commission was earned.

**Position.** Insert:

> "Owner's obligations hereunder are subject to any consent, defeasance, or
> prepayment requirement of any lender holding a lien on the Property. No
> commission shall be deemed earned if a required lender consent is withheld or
> if the transaction fails to close for that reason."

Check the property's loan register before signing. Fairground Village Center LLC
carries a Symetra loan secured by two Columbus properties.

---

## SP-12 — Entity names match the county owner-of-record string
*Check: L20*

The Zettler draft rendered the Owner as `FAIRGROUND VILLAGE CENTER LLC` in the
preamble and `FAIRGROUND VILLAGE CENTER, LLC` in the signature block. The Franklin
County Auditor's owner of record is `FAIRGROUND VILLAGE CENTER LLC`, no comma —
which settles it.

**Position.** Conform every instance to the Secretary of State registered name,
verified against the county owner-of-record string. The ownership representation
is backed by the prevailing-party fee-shifting clause; a misnamed grantor is not
a formatting question.

---

## SP-13 — Property description is verified against the parcel before signature
*Check: L21*

A hyphenated address range against a single parcel ID must be resolved, not
assumed. For Zettler the check cleared favorably: parcel 010-015487 returns
`SITEADDRESS = 2000 - 2002 ZETTLER RD`, `BLDGAREA = 11,160`, `ACRES = 0.916`,
class `COMMERCIAL WAREHOUSES` — a discrete single-building parcel, distinct from
2018 Zettler Rd, correctly described. Where it does not clear, list every parcel
ID.

---

## SP-14 — Document hygiene is part of the gate
*Checks: L22, L24, L25*

Mixed automatic and manual section numbering, template residue in running headers
("A PROPOSAL FOR" on an executed agreement), missing spaces after ZIP codes,
spaces before commas, and subject-verb disagreement all get corrected in the same
markup. They cost nothing to fix and they signal to the counterparty how closely
the document was read.

---

## SP-15 — Commencement is prospective
*Check: L23*

The Livingston agreement commenced 16 April 2026 and was signed 21 April (Owner)
and 4 May (broker) — retroactive on both sides, which silently backdates the term
and the tail. Zettler commences the day after its draft date, which is correct.

**Position.** Commencement is the date of full execution or a stated future date.
Never a date already past.

---

## SP-16 — No unfilled tokens
*Check: L9*

Any `[TOKEN]` surviving into a document whose filename lacks `_TEMPLATE` is a
BLOCK. Drafted listings are fully filled before they are read for substance.

---

## Commission benchmark (context, not a position)

C&W's schedule on both ORA agreements: **6.00%** of gross sale price with a
cooperating broker, split 3.0 / 3.0; **4.00%** with no cooperating broker.

Two observations, neither yet ratified as a position:

- The 200 bp spread pays the listing broker **more** on a direct deal (4.0%) than
  on a co-broked one (3.0%), which sits in mild tension with the cooperation
  covenant elsewhere in the agreement.
- Columbus shallow-bay practice more commonly runs 5.00% co-broked (2.5 / 2.5).
  On a $1.5M sale the delta between the ORA schedule and that benchmark is
  approximately **$15,000**.

Flagged as a negotiation point for the next engagement, not a defect in this one.
