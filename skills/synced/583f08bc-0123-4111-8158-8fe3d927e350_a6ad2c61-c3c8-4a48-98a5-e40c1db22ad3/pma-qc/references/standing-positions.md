# ORA standing positions — property management agreements

**STATUS: PROPOSED. NOT RATIFIED.**

Drafted 2026-08-17 from the Kohr Royer Griffith Management Agreement review
(executed 23 December 2020, five Columbus properties). These are the review
standard this skill applies and the recommendations it presents. They are **not**
settled ORA policy — unlike the SP-1 … SP-16 listing positions ratified
2026-08-17. Do not describe any PM position as ratified until Gabriel records
ratification here and in `event_log.md`.

Each position carries the scanner check(s) in `scripts/pma_qc.py` that enforce it
and the replacement language to insert.

---

## PM-1 — Exclusivity is per-property and severable by service line
*Checks: P3, P3b*

KRG §1: *"The owner hereby appoints the Agent **exclusively** to rent, lease,
operate and manage the above referenced Property."* Four service lines granted in
one clause, across a five-property Exhibit A, with no severability. The only exit
is a 60-day termination of the entire agreement. There is no mechanism to move
leasing at one building to a specialist broker, or to remove one property on a
sale, without unwinding management at four others.

**Position.** Three structural changes:

> "Owner appoints Agent to manage the properties listed on Exhibit A. Agent's
> appointment as leasing agent is a separate grant, made property by property on
> Exhibit A, and may be modified by Owner as to any property on thirty (30) days'
> written notice without affecting Agent's management appointment as to that or
> any other property. Owner may remove any property from Exhibit A upon thirty
> (30) days' written notice, whereupon this agreement shall terminate as to that
> property only."

Retain an exclusivity grant for **management**; a property cannot have two
managers. Leasing is the line that must stay severable.

---

## PM-2 — Renewal is affirmative, or the notice deadline is calendared
*Check: P7*

KRG §1: *"This agreement shall automatically renew for annual periods."* No
notice requirement, no anniversary review, no rate reset. Six renewals have run
unexamined since 2020.

**Position.** Preferred: *"This agreement may be extended for successive annual
periods by written agreement of the parties."* If the manager will not move off
auto-renewal, accept it only alongside a hard obligation:

> "Not later than ninety (90) days before each anniversary, Agent shall deliver
> to Owner a written summary of fees charged during the preceding twelve months
> by category, together with any proposed change in rates."

Either way, register the notice deadline as a scheduled task the day the
agreement is signed.

---

## PM-3 — "Gross monies collected" is defined and excludes non-revenue receipts
*Check: P10*

KRG §2(c)(1): *"Four (4%) percent of gross monies collected or $850 monthly,
whichever is greater."* Undefined. Read literally it reaches security deposits,
insurance and condemnation proceeds, sale and refinancing proceeds, tenant
improvement allowances funded by Owner, capital contributions, and tax-appeal
refunds — none of which are operating revenue, several of which are Owner's own
capital returning to Owner.

**Position.**

> "'Gross Monies Collected' means base rent, percentage rent, and recurring
> operating-expense, tax, and insurance reimbursements actually collected from
> tenants at the Property during the month. It excludes security and other
> deposits, insurance and condemnation proceeds, proceeds of any sale or
> financing, capital contributions by Owner, tenant improvement allowances,
> tax-appeal refunds, late fees and default interest, and any amount collected
> and remitted to a third party."

Late fees are deliberately excluded from the base: a percentage of late fees pays
the manager more when collections go worse.

---

## PM-4 — Owner deficit funding is noticed, cured, and capped; approval thresholds escalate
*Checks: P8, P21*

Two defects in the spending machinery.

**Deficit funding.** KRG §2(b): expenses exceeding receipts are payable by the
15th of the following month, *"Failure of Owner to remit will result in Agent
charging 1% of total outstanding balance each month that balance remains."* One
percent monthly, compounding, is **12.68% effective annual** — with no notice
requirement, no cure period, no cap, and no reciprocal obligation on the Agent to
remit Owner's net proceeds by any date at all.

**Position.**

> "Agent shall deliver written notice of any deficit with the monthly statement.
> Owner shall fund within fifteen (15) days after receipt of such notice. Amounts
> not funded within ten (10) days after a second written notice shall bear
> interest at the lesser of one percent (1%) per month, simple and
> non-compounding, or the maximum rate permitted by law. Agent shall remit net
> proceeds to Owner by the fifteenth (15th) day of each month."

**Approval thresholds.** KRG §3(b) sets $2,000 per item, unchanged since 2020,
with no aggregate annual cap and no definition of the emergency exception.

> "Agent shall obtain Owner's prior written approval for any expenditure
> exceeding $5,000 for any one item or $25,000 in the aggregate in any calendar
> year, excepting only emergency expenditures reasonably necessary to prevent
> imminent injury to persons or material damage to the Property, of which Agent
> shall notify Owner within twenty-four (24) hours."

Escalate the per-item figure at every renewal or index it.

---

## PM-5 — Interest on Owner's funds belongs to Owner; accounts are segregated
*Checks: P9, P23*

KRG §3(d): *"If the property management trust account is set up to earn interest,
Owner agrees that any such interest earned shall be kept by the Agent."* Owner's
money, manager's yield. At meaningful float this is an unpriced fee. §2(c) also
pre-exculpates the Agent for bank failure while imposing no requirement that
funds sit in a segregated account or within FDIC limits.

**Position.**

> "All funds collected for Owner's account shall be held in a segregated trust
> account in Owner's name at a federally insured institution, shall not be
> commingled with Agent's funds or with funds of any other owner, and any
> interest earned thereon shall accrue to Owner or be credited against fees next
> due."

Check the manager's handling against Ohio R.C. 4735.18 and the trust-account
rules for licensed brokers before conceding the point.

---

## PM-6 — The indemnity does not reach the manager's own negligence
*Check: P2*

KRG §4(a): Owner *"save[s] the Agent harmless from all damage suits in connection
with the management of the premises and from liability from injury suffered by
any person whomsoever,"* names Agent as co-insured on Owner's liability policy,
and provides that *"The Agent shall not be liable for any error of judgment or
for any mistake of fact of law, or for anything which it may do or refrain from
doing hereinafter, except in cases of willful misconduct or gross negligence."*

Read together: Owner indemnifies the manager for the manager's own ordinary
negligence, and the manager is exculpated for it besides. The manager's actual
negligence — a missed insurance renewal, a botched eviction, an unrepaired
hazard — lands entirely on Owner.

**Position.** Carve it out on both sides:

> "Owner's indemnity shall not extend to any claim arising from Agent's
> negligence, willful misconduct, breach of this agreement, or violation of law.
> Agent shall indemnify and hold Owner harmless from any claim arising from
> Agent's negligent or wrongful acts or omissions, or those of its employees and
> subcontractors."

The exculpation clause and the indemnity clause must be amended together;
amending one leaves the other doing the same work.

---

## PM-7 — Owner has audit rights, a budget, and variance reporting
*Checks: P16, P24*

KRG §2(b) requires monthly statements and nothing else. No right to inspect books
and records, no records-retention period, no stated basis of accounting, no
annual operating budget, no variance reporting, no year-end package, no leasing
activity report.

**Position.**

> "Agent shall maintain complete books and records for the Property, retained for
> not less than four (4) years. Owner and its representatives may inspect and
> audit such records upon five (5) business days' notice. If an audit discloses
> an overcharge exceeding three percent (3%) of fees charged in the audited
> period, Agent shall reimburse the cost of the audit. Agent shall deliver a
> proposed annual operating budget not later than November 1 for Owner's
> approval, monthly variance reporting against the approved budget, and a
> year-end package including all Forms 1099 within thirty (30) days after year
> end."

---

## PM-8 — Manager carries E&O; bond and insurance certificates are delivered annually
*Checks: P17, P22*

KRG §2(d) requires a $250,000 fidelity bond on employees handling Owner's monies
— fixed since 2020, with no obligation to deliver evidence of it, ever. There is
no professional liability (E&O) requirement at all, and Owner is required to name
Agent as co-insured on Owner's own liability policy with no reciprocal naming.

**Position.**

> "Agent shall maintain (a) a fidelity bond of not less than $500,000 covering
> employees handling Owner's funds, (b) commercial general liability insurance of
> not less than $1,000,000 per occurrence / $2,000,000 aggregate, and (c)
> professional liability (errors and omissions) insurance of not less than
> $1,000,000, in each case naming Owner as additional insured where applicable,
> and shall deliver certificates evidencing the same upon execution and annually
> thereafter."

Scale the bond to the largest monthly collection the manager holds, not to a
round number carried forward from an old form.

---

## PM-9 — The manager never executes a lease or any instrument in Owner's name
*Check: P1*

KRG §3(a) authorizes the Agent *"to sign, renew and/or cancel leases"* and to
*"sign and serve in the name of the Owner such notices as are appropriate."* On
brokerage paper ORA has already won the opposite position — SP-9, ratified, is a
flat prohibition on the broker executing anything. The management agreement gives
away on page one what the listing agreement protects.

**Position.** Import SP-9 verbatim:

> "Agent shall not have the authority to execute any lease, lease amendment,
> renewal, extension, purchase and sale agreement, or other instrument on behalf
> of Owner. All documentation shall be executed solely by Owner or its duly
> authorized representative."

Notice-serving authority for statutory tenant notices may be retained; lease
execution may not.

---

## PM-10 — Litigation is Owner-approved, Owner-counseled, and cost-capped
*Check: P6*

KRG §3(a) lets the Agent *"institute and prosecute actions; evict tenants and
recover possession of premises; sue for in the name of the Owner and recover
rents and other sums due; and when expedient, to settle, compromise, and release
such actions or suits or reinstate such tenancies."* Unilateral authority to sue,
settle, and release claims in Owner's name — including the authority to release a
claim Owner would have pursued — with no approval threshold and no counsel
selection right.

**Position.**

> "Agent shall not commence, settle, compromise, or release any action in Owner's
> name without Owner's prior written approval. Owner shall select counsel. Agent
> may serve statutory notices for non-payment and may commence a forcible entry
> and detainer action after written notice to Owner, provided that any settlement
> or release remains subject to Owner's approval."

Routine evictions can be delegated. Releases cannot.

---

## PM-11 — The leasing fee base is defined, capped, timed, and clawed back; no tail survives
*Checks: P4, P20, P29*

KRG §2(c)(2): *"Six (6%) percent of gross lease value for original leases.
Renewals to be handled by Owner."* "Gross lease value" is undefined — no
exclusion of option, renewal, or expansion terms, no present-value convention, no
treatment of free rent or tenant improvement allowances, no cooperating-broker
split, no payment timing, no clawback if the tenant defaults early. Separately,
§3(a) permits the Agent to *"utilize a leasing agent to market the premises"*
under a section whose preamble has **Owner** assume the expense — an outside
broker at Owner's cost with no offset against the Agent's own 6%.

The one favorable term is negative: the agreement contains **no post-termination
commission tail**. That silence should be converted to an express covenant so it
cannot later be argued in.

**Position.**

1. **Base.** "'Gross Lease Value' means aggregate base rent payable over the
   initial stated term, excluding option, renewal, and expansion periods,
   operating expense reimbursements, percentage rent, and any period of abated
   rent, and net of any tenant improvement allowance funded by Owner."
2. **Timing.** Half on full execution, half on the earlier of rent commencement
   or tenant occupancy.
3. **Clawback.** "If the tenant defaults and the lease is terminated within
   twelve (12) months after rent commencement, Agent shall refund a pro rata
   portion of the commission."
4. **Offset.** "Any cooperating or outside broker engaged by Agent shall be
   compensated from Agent's fee, and shall not increase the aggregate leasing
   commission payable by Owner."
5. **No tail.** "No commission shall be payable with respect to any lease
   executed after the termination of this agreement."
6. **Renewals.** Preserve the Owner reservation, and state it broadly: "Renewals,
   extensions, and expansions shall be handled by Owner or by such party as Owner
   may designate, at no cost to Owner hereunder." The KRG text says only
   "handled by Owner," which does not clearly permit Owner to use a third party.

---

## PM-12 — Capital-project fees are capped and affiliate work is disclosed
*Checks: P11, P25*

KRG §2(c)(3) charges a construction supervision fee on capital projects *"match[ing]
the Management fee percentage"* — a second percentage on money that is not
operating revenue, triggered by the undefined standard of Agent being *"required
to spend extra time."* Nothing in the agreement requires disclosure when the
manager routes work to an affiliated contractor, and nothing prohibits a markup
on subcontracted work.

**Position.**

> "Agent's construction supervision fee shall not exceed four percent (4%) of
> hard costs actually incurred, shall apply only to capital projects exceeding
> $25,000 approved in advance by Owner, and shall not apply to repair or
> replacement work funded from operating accounts. Agent shall disclose in
> writing any interest it or any affiliate holds in a contractor, vendor, or
> supplier engaged at the Property, and shall pass through all third-party costs
> at actual cost without markup, rebate, or administrative charge."

---

## PM-13 — Casualty fees are offset, not stacked; hourly rates escalate
*Checks: P12, P26*

KRG §2(c)(5) charges *"Ten (10%) percent of gross billings to be collected from
insurer"* on fire/flood rehabilitation. That sits on top of the management fee
(insurance proceeds arguably fall inside the undefined "gross monies collected"),
and on top of the construction supervision fee for the same physical work. A
single $300,000 casualty can carry three separate fees for one project.

§2(c)(4) and §2(c)(6) set $45/hour for court appearances and for sale-support
duties when KRG is not the listing agent — 2020 rates, uncapped, and in the
latter case a charge that exists only because Owner used a different broker.

**Position.**

> "The casualty fee shall be the sole compensation payable to Agent in connection
> with a casualty restoration, and shall be credited against any construction
> supervision fee otherwise payable for the same work. Insurance and condemnation
> proceeds are excluded from Gross Monies Collected."

For hourly work: cap the annual aggregate, index the rate, and strike the
sale-support charge or cap it — a fee that penalizes Owner for engaging a
different listing broker is a soft exclusivity provision sitting in the fee
schedule.

---

## PM-14 — Notice provisions exist
*Check: P19*

KRG §1's only exit is *"60 day written notice"* — to an address the agreement
never specifies, by a method it never specifies, effective on a date it never
defines. The agreement also has no governing law, no venue, no attorney-fee
provision, and no jury waiver (see P27).

**Position.** A standard notice block: addresses for both parties, delivery by
hand, nationally recognized overnight courier, or certified mail, effective on
receipt or refusal, with a copy to counsel and an address-change mechanism. Ohio
law, Franklin County venue, prevailing-party fees.

---

## PM-15 — Termination triggers real turnover obligations; assumed contracts are scheduled
*Checks: P13, P14*

KRG §3(c) authorizes the Agent to contract for utilities and services *"as the
Agent shall deem advisable; the Owner to assume the obligation of any contract so
entered into at the termination of this agreement."* Owner assumes contracts
Owner has never seen, on termination, with no schedule and no notice. The
agreement imposes no turnover obligations at all: no delivery of leases, tenant
files, security deposits, keys, plans, warranties, or accounting.

**Position.**

> "Agent shall deliver to Owner, within fifteen (15) days after termination: all
> leases, tenant correspondence and files, security deposits and all other funds
> held for Owner's account, a final accounting, keys and access credentials,
> plans, warranties, and a complete schedule of all service contracts entered
> into on Owner's behalf, together with copies. Owner shall assume only those
> service contracts identified on a schedule delivered to and approved by Owner
> in advance, and in no event any contract not terminable on sixty (60) days'
> notice."

Add a for-cause immediate termination right: fraud, misapplication of funds, loss
of license, failure to maintain the required bond or insurance.

---

## PM-16 — The manager may not assign; change of control is a termination event
*Check: P15*

KRG's closing sentence binds *"the successors and assigns of the Agent."*
Brokerage and management firms consolidate; Owner engaged a specific local
operator and can be delivered a national platform without consent.

**Position.**

> "Agent may not assign this agreement or delegate its duties without Owner's
> prior written consent. A transfer of a majority of the ownership interests in
> Agent, or a merger or sale of substantially all of Agent's assets, shall
> constitute an assignment. Owner may terminate upon thirty (30) days' notice
> following any such event."

Owner's side may remain freely assignable to an ORA affiliate or a purchaser.

---

## PM-17 — Owner entity and property schedule are verified against county records
*Checks: P18, P30*

KRG names the Owner as **"Eric Goldberg"** individually. If title is held in
property LLCs, the named Owner is not the owner of record. Exhibit A lists five
address ranges with no parcel IDs, no building SF, and no per-property entity.

**Position.** Conform the Owner name, per property, to the Secretary of State
registered name verified against the county owner-of-record string — the same
discipline as the ratified SP-12 on listing paper. Exhibit A carries address
range, parcel ID(s), building SF, owning entity, and the service lines engaged.

Note on the mismatch: it is a conforming amendment to make, not a defense to
rely on. Years of accepted services and paid fees support ratification, and
raising it as an escape hatch invites a fight ORA would likely lose while
forfeiting the relationship. [SPECULATIVE — no Ohio authority pulled on these
facts; confirm with counsel before it is ever asserted.]

---

## PM-18 — No unfilled tokens; document hygiene is part of the gate
*Checks: P5, P27, P28, P31*

Any `[TOKEN]` surviving into a document whose filename lacks `_TEMPLATE` is a
BLOCK. Also corrected in the same markup: missing governing law and venue, missing
confidentiality covenant covering the rent roll and tenant financials, and
signature blocks that do not identify the signing entity, the signatory's title,
and the capacity in which they sign. The KRG signature page identifies neither
the entity nor the capacity and its dates are partially illegible.

---

## Fee benchmark (context, not a position)

KRG's schedule: **4.00%** of gross monies collected or **$850/month** minimum,
whichever is greater; **6.00%** of gross lease value on original leases;
construction supervision at the management rate; **10.00%** of casualty billings;
$45/hour for court and sale-support time.

Two observations, neither ratified:

- Third-party shallow-bay industrial management in secondary Midwest markets more
  commonly runs **3.00%–4.00%** with a per-property monthly minimum, and **4.00%**
  new-lease commissions where the manager is also the leasing agent. The 6.00%
  leasing rate sits at the top of the range for a manager who is not bearing
  outside-broker cooperation cost.
- The $850 monthly floor across a five-property schedule is the term worth
  confirming: whether it applies **per property** or **per agreement** changes
  annual minimum compensation by roughly **$40,800**. The KRG text does not say,
  and the answer sits in the billing history, not the document.

---

## PM-19 — The manager contracts trade work in Owner's name, as disclosed agent
*Checks: P32, P33*

The management agreement is the instrument that authorizes the manager to go out
and buy paving, roofing, HVAC and snow services on ORA's assets. The KRG form
grants that authority — repairs, alterations, hiring contractors, purchasing
supplies — and says nothing about **whose name** the resulting contract is signed
in.

The consequence is not theoretical. A Q3 2026 paving proposal for an ORA-owned
Maryland asset, solicited by the property manager, named **the manager** as
Purchaser on a form providing that no provision confers any remedy upon a
non-party. On that paper the one-year workmanship warranty, the indemnity and
every payment remedy ran to the manager — a counterparty terminable on sixty
days' notice — and not to the entity that owns the asphalt and paid the invoice.
A management agreement that is silent on contracting capacity produces that
result by default, at every property, on every trade.

The second half of the position is the threshold. The KRG form requires Owner's
prior written approval above **$2,000** — a figure set in 2020, never indexed, on
an agreement that has auto-renewed six times. Approval is also not the same as
signature: an approved job still gets contracted on the manager's signature
unless the agreement says otherwise.

**Position.** Three changes.

> "Agent shall contract for all repairs, capital improvements and vendor services
> in the name of Owner, as Owner's disclosed agent, and shall name Owner as the
> contracting party on every such agreement. Agent shall not contract for work at
> the Property as principal."

> "Agent shall obtain Owner's prior written approval for any single expenditure in
> excess of $[X], which threshold shall be adjusted annually by CPI. Owner shall
> countersign any trade contract for an expenditure exceeding that threshold."

> "In an emergency threatening imminent harm to persons or property, Agent may act
> without prior approval and shall notify Owner within twenty-four (24) hours,
> provided that emergency expenditures shall not exceed $[Y] per occurrence
> without Owner's approval."

**Companion.** PM-19 governs the *authority*. `vendor-management` VC-1 governs
the *instrument that authority produces* — and catches the same defect from the
other end, at the moment a specific trade contract is about to be signed. Run
both: fixing the management agreement does not cure trade paper already executed
in the manager's name, and fixing one contract does not stop the next one.
