# Exhibit Extraction Patterns

Guidance for parsing each standard PSA exhibit and resolving the recurring ambiguities that show up in Oxford Realty Advisors transactions. Read this reference during Step 1 (Extract the PSA) of the skill.

---

## Exhibit A — Legal Description

**Purpose.** Legally sufficient metes-and-bounds description of every parcel being conveyed, with recorded deed references and — often — the aggregate SF and acreage as independent numerical statements.

**What to extract.**
1. **Parcel IDs** — locate every parcel number in the exhibit. Compare character-for-character against the preamble. Watch for leading-zero and hyphen typos (e.g., "010-99201" in the preamble vs. "010-099201" in Exhibit A).
2. **Tracts** — capture every tract, sub-parcel, and any split-acreage statement (e.g., "of which 1.342 acre lies within the Village of Whitehall and 1.664 acres lies within the City of Columbus").
3. **Recorded instrument** — capture the recording reference (Instrument # and date) for the master deed.
4. **Aggregate SF and acreage** — capture the exhibit's stated aggregate. If the exhibit sums component tracts, compute the sum independently and compare against the preamble-stated aggregate. Flag any variance > 0.1%.

**Recurring ambiguities to flag.**
- **Parcel ID typo in preamble body** that is corrected in Exhibit A. Record the corrected Exhibit A value and flag the preamble as Typo.
- **Mid-sentence chain-of-title blanks** like "Deed Book ____, page ____" — note as a title search follow-up, not a PSA defect.
- **Cross-jurisdictional tracts** where a single tract straddles two municipalities. Populate both P-027 and P-028, and attach a Note citing the split language.
- **Stated SF in preamble ≠ computed SF from exhibit component sum.** The preamble value is typically the governing figure for prorations; exhibit component sums are surveyor approximations. Record both (P-024 governing, P-025 component sum) and flag as Ambiguous if variance > 0.1%.

---

## Exhibit B — Existing Leases Schedule

**Purpose.** List of every lease, license, or occupancy agreement affecting the property as of the Effective Date. Typically populates the "Leases Complete" representation (e.g., §15.1.15).

**What to extract.**
1. Each tenant by name, premises address, approximate SF, lease start/expiration, term length, amendments.
2. Any "licenses" or "occupancy agreements" that are not leases — capture separately (licenses are revocable and do not create tenancy interests).
3. Any tenant listed with a parenthetical note like "lease says X which is inaccurate." Record both the stated value and the PSA's acknowledgment of inaccuracy.

**Recurring ambiguities to flag.**
- **License vs. lease characterization.** A document labeled "License Agreement" (e.g., Nutis Press) is not a tenancy. Estoppel, SNDA, and vacate mechanics differ. Record as a tenant row with Field "Occupancy Type" = "License" and add a Note.
- **Expiration typo between lease body and rent roll** (e.g., OotBox lease states 12/31/2030 but exhibit rent roll shows 12/31/2031, with PSA exhibit itself stating "lease says 12/31/2030 which is inaccurate"). Record the rent-roll value as the governing fact, note the PSA's own acknowledgment, and flag the body of the lease.
- **Renewal option count mismatches** between Exhibit B and Exhibit D. Use Exhibit D (rent roll) as governing unless the user overrides.

---

## Exhibit C — Assignment and Assumption of Leases (form)

**Purpose.** Closing-deliverable template. This is a form document that gets filled in at Closing; its presence is verified, but its contents do not populate the Fact Table except to confirm the §9.3(j) obligation.

**What to extract.**
- Confirmation that the form is attached.
- Any blanks or bracketed placeholders that need to be populated at Closing (entity names, dates, property address).
- Indemnity split — pre-Effective-Date obligations remain with Assignor; post-Effective-Date obligations transfer.
- Security deposit treatment — confirm the form provides for transfer at Closing via the settlement statement.

**Recurring ambiguities to flag.**
- Form references a PSA dated "_______" — note but do not treat as a defect; gets populated at Closing.
- Form names "Assignor" and "Assignee" but leaves entity type blank ("an __________") — note for closing coordinator.

---

## Exhibit D — Rent Roll

**Purpose.** Authoritative tenant financial schedule. Governs prorations, security-deposit transfers, and post-closing tenant notifications.

**What to extract.**
1. Per tenant: SF, monthly rent by year, annual rent by year, escalation structure, expiration, renewal options, option rates.
2. Per tenant: comments column (this is where PSA-acknowledged typos and inaccuracies live).
3. Totals — if the exhibit states portfolio totals, compute independently and compare.

**Recurring ambiguities to flag.**
- **Y1/Y2/Y3… rent laddering** where rent increases by non-standard increments. Capture every year's rent separately; do not assume linearity.
- **Renewal option structure.** "Two (2) Five (5) Year Options" means 2 options, 5-yr term each — 10 years of extension runway. Record term count and length separately.
- **Renewal rates** — some leases fix renewal pricing (e.g., "3% increase from Year 5 rental rate and thereafter raise 3% every 2 years"). Others leave renewals at market. Capture the formula verbatim.
- **Mid-term renewals** — a tenant in its 3rd 2-year renewal option with 7 remaining is different from a tenant with 2 × 5-yr options. Do not collapse.

---

## Exhibit E — Tenant Notification Letter (form)

**Purpose.** Form letter to tenants notifying of ownership change and new payment instructions.

**What to extract.**
- Confirmation that the form is attached.
- New landlord contact info to populate at closing (owner principal + secondary contact + payment instructions).
- Security deposit representation — the form typically confirms deposits transfer to new landlord.

**Recurring ambiguities to flag.**
- New Landlord payment info block is blank pre-Closing — this gets populated after the SPV's bank account is opened. Flag as a closing-coordination item (Fact Table row in Section 9 referencing §9.3(l)).

---

## Exhibit F — Litigation and Government Notices

**Purpose.** Full disclosure of every case, notice, agency action, or enforcement matter known to Seller as of the Effective Date. This is the single most important exhibit for reconciling risk into the DD checklist and red-flag log.

**What to extract.**

Populate one Fact Table row per disclosed item. For each:

1. **Case caption or notice title** — verbatim.
2. **Case number or instrument number** — verbatim, including court and division.
3. **Court / agency** — full name and branch.
4. **Filed date** — explicit date if stated.
5. **Current status** — any post-filing events disclosed (agreed judgments, motions to reopen, pending orders, approvals).
6. **Co-defendants / co-respondents** — especially important when a current tenant is a co-defendant (creates cross-default and estoppel coordination issues).
7. **Property-specific?** — Yes if tied to subject property or Seller-as-owner-of-subject-property; No if tied to Seller's other holdings.

**Recurring subtypes and how to extract each.**

### Municipal / city code enforcement

- Capture the **issuing entity** (City Attorney, Code Enforcement, Zoning Board), the **notice date**, and the **affected parcel(s) or addresses**. Parcels are often listed as street-number ranges (e.g., "3483, 3551-3561, 3555 and 3585").
- Classify by violation type: **graphics / signage**, **zoning**, **city code** (general), **housing**, **environmental**, **nuisance**.
- Cross-reference against §13 of the PSA — if §13 places cure obligation on Seller at Closing, note Seller as the cure party and Buyer as verification party. This is a material ownership allocation.

### Lis Pendens

- Capture the **instrument number** and **recording date**.
- Capture the **underlying case** the lis pendens references.
- Lis pendens is **title-impacting** by definition — mark P-095 = Yes.
- Title commitment must either extinguish the lis pendens (Seller obligation) or endorse around it.

### Foreclosure actions

- Capture the **caption** (typically Lender v. Seller), **case number**, **court**, **filed date**, and **current status**.
- Mark as **property-specific**, **title-impacting**, and **Seller-cure-at-closing-required**.
- Every foreclosure disclosure triggers a Seller Lender workstream in the DD checklist (payoff letter, lien release, UCC-3 terminations, stipulation of non-pursuit).
- Note the plaintiff bank's name verbatim — this becomes the payoff counterparty.

### Agreed judgments / consent orders

- Capture the **filing date** of the original judgment and any **subsequent motions** (motion to reopen, motion for contempt, motion to enforce).
- If a motion to reopen is pending alleging non-compliance, the judgment is **actively disputed** — mark as Open, not Resolved, even if the judgment itself is "entered."
- Agreed judgments often run with the land — attorney review required. Do not assume the new owner inherits no obligation.

### Agency approvals and permits

- Capture the **approving agency**, **approval date**, **permit or letter type**, and **renewal cadence** (annual, triennial, etc.).
- An approval is not a violation, but it is still a disclosable fact and may require **annual certification** post-closing.
- Examples: Ohio EPA NPDES No-Exposure exclusion letter (annual certification), stormwater discharge permits, air emissions permits, hazardous waste generator notifications.

### Pending or threatened litigation (general)

- Capture any **tort, contract, landlord-tenant, or environmental** suit not otherwise covered.
- Note who the plaintiff is — if it's a tenant, coordinate with the estoppel for that tenant.

---

## Signature block

**Purpose.** Establishes Effective Date, signatories, and time of execution.

**What to extract.**
1. Every signatory's printed name and title.
2. The execution date adjacent to each signature — the **latest** date is the Effective Date unless the PSA specifies an alternate "Effective Date" convention.
3. Time zone — if the signature platform (DocuSign, Adobe Sign) records a timestamp, capture it; it occasionally matters for "same business day" calculations.

**Recurring ambiguities to flag.**
- Signature timestamps that straddle midnight — use the date at the signing party's jurisdiction.
- Handwritten dates vs. digital signature dates — use the digital timestamp if both are present (more reliable).

---

## Addendums, side letters, and post-execution amendments

If the user provides any document dated **after** the PSA Effective Date that modifies PSA terms, treat as an amendment.

**Incorporation rules.**
1. Preserve the original Fact Table as v01.
2. Produce a v02 Fact Table with an **Amendment Delta** column populated for every changed row, recording before/after values and the amending document reference.
3. Flag any downstream cascade instructions that need to be re-run against v02.

**What qualifies as an amendment.**
- Formal "First Amendment to Real Estate Contract" instruments.
- Letter agreements signed by both parties changing any substantive PSA term.
- Email exchanges that explicitly amend a PSA term and are countersigned or clearly accepted by both sides.
- Seller's approval documents under §15.1.16 that include substantive modifications (rare but happens).

**What does NOT qualify.**
- Unilateral email statements.
- Broker emails.
- Non-counterparty communications.

If uncertainty exists, flag as Ambiguous and ask the user to confirm amendment status before cascading.

---

## Edge cases worth remembering

### PSA with "or assigns"
When the Seller or Purchaser signs as "Entity X, LLC or assigns," capture the signing entity as the contracting party but flag that assignment may occur pre-closing. The Fact Table Purchaser or Seller row should remain as signed; assignment is tracked separately.

### PSA with §9.1 closing-date blank
The language "but in no case beyond _______ without approval from Seller's lender" with a blank is intentional flexibility. Record as:
- P-058 (Closing Outer Cap — Explicit Date) = N/A
- P-059 (Source of Hard Stop) = "None — §9.1 blank; any calendar constraint derives from Seller lender agreement, not from PSA"

### PSA §29 Seller §1031 language without Buyer §1031 language
Confirm with the user whether Buyer intends its own §1031 — do not assume. Most Oxford transactions are not §1031 exchanges from the Buyer side.

### PSA references exhibits that are blank or "TBD"
A PSA signed with a TBD exhibit is defective. Flag as Missing and request the completed exhibit before cascading.

### PSA with a "Memorandum of Contract shall not be recorded" covenant
Note as a deviation from the ORA standard (which preserves the right to record). Capture as P-147 = No with a Note citing the specific PSA section. Do not attempt to record a memorandum against the PSA's express prohibition.
