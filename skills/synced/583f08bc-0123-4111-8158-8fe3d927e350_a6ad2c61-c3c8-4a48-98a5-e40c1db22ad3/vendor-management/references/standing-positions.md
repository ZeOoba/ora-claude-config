# ORA standing positions — repeat-trade vendor contracts

**STATUS: PROPOSED. NOT RATIFIED.**

Drafted from the Standard Paving & Concrete proposal 26-9465-1 (dated 8/28/2026,
Technology Commons, 29000 Information Ln, Easton MD — mill patching, sealcoat and
striping, $75,223). These are the review standard this skill applies and the
recommendations it presents. They are **not** settled ORA policy — unlike the
SP-1 … SP-16 listing positions ratified 2026-08-17. Do not describe any VC
position as ratified until Gabriel records ratification here and in
`event_log.md`.

Each position carries the scanner check(s) in `scripts/vendor_qc.py` that enforce
it and the replacement language to insert.

Applies to the repeat trades: paving, roofing, snow and ice, HVAC, electrical,
plumbing, landscaping, fire and life-safety, janitorial, and any other trade
engaged more than once across the portfolio. It does **not** apply to a
negotiated construction contract on AIA-family paper — that is a different
instrument and goes to `legal-intelligence`.

---

## VC-1 — The contracting Owner is the property entity; the manager signs as disclosed agent
*Checks: V01, V02*

The seed proposal names **Thomas Park Management** as Client, with an acceptance
block that collects a signature and a title on blank lines and identifies no
entity. The terms then provide that no provision confers any remedy upon any
person or entity that is not a party. Read together, the one-year warranty, the
indemnity, and every payment remedy run to the property manager — not to the ORA
entity that owns Technology Commons, pays the $75,223, and will still own the
asphalt after the management agreement turns over.

This is the highest-frequency defect in vendor paper because the manager, not
Owner, solicits the bid. It is also the cheapest to fix, and it must be fixed
before signature: a warranty held by the wrong party is not a warranty.

**Position.** Either name the ORA property entity as Purchaser with the manager
signing as disclosed agent, or name the entity as an express beneficiary. Prefer
the first.

> "Purchaser is [Property Owner], LLC, a [State] limited liability company
> ('Owner'). [Manager] executes this instrument solely as managing agent for and
> on behalf of Owner, as a disclosed agent, and assumes no personal liability
> hereunder. All warranties, indemnities and remedies granted to Purchaser run to
> Owner directly."

And, in the beneficiary bar:

> "…except that Owner and any successor owner of the Property are express
> third-party beneficiaries of the warranty and indemnity articles, and Owner may
> assign its rights hereunder to any successor owner or successor managing agent
> without Contractor's consent."

---

## VC-2 — Defect notice is not less than 30 days and is never time of the essence
*Checks: V03, V04*

The seed warranty requires written notice of any defect **within five days after
discovery, time being of the essence**. Market is 30 days, or "promptly upon
discovery." Five days is unachievable on a multi-tenant flex park where the
property manager and the tenants, not Owner, are on site — and because time is of
the essence, a day-six notice is a complete defense to an otherwise valid claim.
The notice period, not the warranty term, is where trade warranties are actually
lost.

**Position.**

> "Owner shall give Contractor written notice of any defect within thirty (30)
> days after discovery. Electronic mail notice is sufficient."

Delete "time being of the essence" wherever it modifies the notice covenant.

---

## VC-3 — Warranty is suspended during a payment dispute, never forfeited
*Check: V05*

The seed form voids **all** warranty rights automatically if full payment
including late charges is not received within 45 days of substantial completion,
and simultaneously runs 2%/month interest and accelerates retainage. Because
invoices are net-30 with interest already running, an ordinary punch-list
holdback or a disputed change order extinguishes the warranty permanently.

**Position.**

> "Contractor's warranty obligations are suspended, and not forfeited, during any
> uncured payment default by Owner, and reinstate in full upon cure."

If the counterparty will not move, the operational consequence must be stated in
the review: no holdback, pay on time, resolve the punch list before payment.

---

## VC-4 — Warranty causation carve-outs reach Owner, its agents and employees — never "third parties"
*Check: V09*

The seed warranty is defeated where the failure was caused by the act of the
customer, its agents or employees, **or any third parties**, or sub-base failure.
The standard formulation stops at agents and employees. On a truck court or
tenant parking field, "any third parties" means a tenant trailer, the snow
contractor, or a delivery vehicle answers virtually any pavement claim.

**Position.** Strike "or any third parties." Retain the Owner/agent/employee
carve-out.

---

## VC-5 — The warranty grant and any warranty summary are consistent
*Check: V10*

The seed package includes a marketing-styled warranty matrix stating that
cracking and pavement failures **are** covered, while the terms disclaim
responsibility for soft or unstable subgrade causing "future sinking, breaking,
or cracking of asphalt surface" and impose no duty to check the sub-base. On a lot
already showing alligatoring, ponding and failed prior patches, nearly every
plausible failure mode is subgrade-driven. The covered scope is therefore much
narrower than the matrix implies.

Do not rely on the matrix to resolve the conflict. These forms carry both a
merger clause and an express anti-construction clause ("provisions shall not be
construed for or against either party"), which together defeat the usual
contra-proferentem argument.

**Position.** One warranty statement, in the terms, with the exclusions stated in
the same place as the grant. Delete the matrix or make it expressly subordinate.

---

## VC-6 — Price is firm through the actual work window; escalators are capped and two-way
*Checks: V11, V12, V14*

The seed proposal holds pricing for 30 days from 8/28/2026 and provides that
work after that date may be renegotiated at the contractor's option — while also
carrying an uncapped liquid-asphalt index escalator and an uncapped diesel
surcharge. Mill patching of 2,590 SY plus 10,100 SY of sealcoat will not be
scheduled and completed by 9/27. The quoted $75,223 is a floor.

**Position.**

> "Prices are firm through the scheduled work window and are not subject to
> renegotiation on account of elapsed time. Any adjustment for [commodity]
> adjusts in both directions and in the aggregate shall not exceed three percent
> (3%) of the contract sum."

---

## VC-7 — Escalator clauses state a numeric baseline and its publication date
*Check: V13*

The seed escalator reads "[a]ny upward adjustment in the price of liquid asphalt
cement **over per liquid ton**" — a dollar threshold is missing from the trigger.
The clause elsewhere recites a Maryland index of $807.50 as of 08/09/2026, but the
operative sentence does not tie to it. As drafted the number is whatever the
contractor later asserts.

**Position.** Name the index, the exact baseline value, and the publication date
in the operative sentence, and attach the index print as an exhibit.

---

## VC-8 — Cancellation, remobilization and change-order machinery is mutual and capped
*Checks: V18, V19, V25*

The seed form charges 20% of contract price on cancellation before commencement,
$2,500 for cancellation inside 48 hours, $2,500 per additional move-in, and
$1,200 per additional striping mobilization — with no reciprocal credit when the
contractor reschedules, and no obligation on the contractor to phase around
occupied-site access. It further provides that adjusted rates bind Owner "as
though a written change order were approved and signed by both parties," which is
a unilateral price amendment.

**Position.** Reciprocal reschedule credit; a phased access plan as an exhibit
with mobilizations priced into it; and Owner's signature as a condition precedent
to any rate adjustment or extra work.

---

## VC-9 — Acceptance requires written notice and a stated inspection window
*Check: V15*

The seed form deems the work accepted, and the bill payable in 15 days, if Owner
fails to walk the site with a contractor representative before demobilization.

**Position.**

> "Substantial completion occurs upon Contractor's written notice thereof, after
> which Owner has ten (10) business days to inspect and deliver a punch list.
> Owner's rights as to latent defects survive acceptance and final payment."

---

## VC-10 — Indemnity is mutual; damages waivers are mutual
*Checks: V06, V17*

The seed form has Owner indemnify, defend, protect and hold the contractor
harmless, with no reciprocal obligation and no carve-out for the contractor's own
negligence, while disclaiming all implied warranties and excluding indirect,
incidental, special, punitive and consequential damages in the contractor's
favor only.

**Position.** Mutual indemnity, each carved out for the other's own negligence
and willful misconduct; mutual consequential-damages waiver; and an express
statement that the implied-warranty disclaimer does not limit the express
workmanship warranty.

---

## VC-11 — Insurance, additional-insured status and a COI are conditions precedent to mobilization
*Check: V07*

**The seed proposal contains no insurance article at all.** No CGL limits, no
additional-insured status, no waiver of subrogation, no workers' compensation
confirmation, no certificate requirement. For milling machines, rollers and
tack-coat operations on an occupied multi-tenant site this is the largest single
uninsured exposure in the document, and it is an absence — it will never surface
in a fee-focused read.

**Position.** CGL not less than $2,000,000 per occurrence, auto, umbrella and
statutory workers' compensation; Owner and the managing agent as additional
insured on a primary and non-contributory basis; waiver of subrogation in Owner's
favor; certificate delivered before mobilization as a condition precedent.

---

## VC-12 — Lien waivers are exchanged for payment
*Check: V08*

The seed form has no lien waiver mechanic while expressly contemplating
subcontractors and reciting lien fees as a collection cost. Maryland mechanics'
lien exposure on a multi-tenant commercial property is real and reaches Owner
regardless of who signed the contract.

**Position.** Conditional waiver with each progress application; unconditional
waiver from the contractor and from each subcontractor and supplier at final
payment; final payment conditioned on receipt.

---

## VC-13 — Confidentiality does not impede competitive bidding
*Check: V20*

The seed proposal carries a legend barring dissemination of the information,
maps or pricing to any other person or entity, with an express threat of legal
action. There is no carve-out for counsel, lender, the property manager,
affiliates, or comparison against competing bids — which is the entire purpose
for which Owner solicited the document.

**Position.** Mutual confidentiality with a carve-out for counsel, lender,
insurance advisors, property manager, affiliates, and other contractors for
competitive bid comparison. Or strike the legend.

---

## VC-14 — Default interest and fee-shifting are mutual; no pre-waiver of exemptions
*Checks: V21, V22*

The seed form charges 2% per month (24% per annum) on past-due balances, shifts
all collection costs and attorneys' fees one way "whether suit is filed thereon
or not," has Owner waive all claims or rights to claim exemptions under
applicable state laws, and pre-consents to assignment of the receivable to a
collection agent — all before any dispute exists.

**Position.** Prevailing-party fee shifting. Strike the exemption waiver and the
pre-consent to assignment. Confirm the monthly rate against the governing state's
commercial interest limits.

---

## VC-15 — Site-condition disclaimers do not swallow the priced scope
*Check: V16*

The seed form assumes a workable sub-base of at least four inches, disclaims any
responsibility to check it, and disclaims all consequences of its deficiency —
while the scope being priced is repair of pavement that is visibly failing. The
disclaimer and the deliverable are in direct tension.

**Position.** Either buy the investigation (proof roll or cores) as a priced line
item and let the contractor own disclosed conditions, or record in writing that
this is a maintenance treatment carrying no structural warranty, and budget the
reconstruction separately. Do not sign a repair contract that disclaims repair.

---

## VC-16 — Occupied-site obligations are qualified to reasonable efforts
*Check: V24*

The seed form makes Owner absolutely responsible for removing all vehicles
(towing if required) by 7:00 a.m., and makes Owner responsible for damage to any
vehicle left on the work site. Owner does not control tenants, their employees,
or their customers.

**Position.** Commercially reasonable efforts with a stated tenant-notice period;
towing priced as a contractor line item; no Owner guarantee of a vehicle-free
site after reasonable notice.

---

## VC-17 — A completion schedule is committed in writing before mobilization
*Check: V23*

The seed form provides that the contractor is not bound to schedules unless
agreed in writing, will work in its normal operating schedule if none is
established, and reserves the right to delay start until the entire area is
ready — while Owner carries cancellation and remobilization charges keyed to that
same schedule. The schedule risk is entirely one-directional.

**Position.** Named mobilization and substantial-completion dates before
mobilization, with the reciprocal reschedule credit at VC-8.

---

## VC-18 — Governing law, venue and the acceptance block are conformed before countersignature
*Checks: V26, V27*

Governing law and venue must match the state where the property sits. The seed
form specifies Maryland law and Maryland courts for a Talbot County asset, which
**conforms** — this is the one check the seed passes, and it is worth confirming
rather than assuming on a multi-state portfolio where the trade's home form may
name its own state.

The acceptance block must be pre-filled with the ORA property LLC, its state of
formation, and the signatory's capacity, so that VC-1 is not undone at the
moment of signature.

**Position.**

> "TECHNOLOGY COMMONS OWNER, LLC, a Maryland limited liability company
> By: ____________  Name: ____________  Its: Authorized Signatory"
