---
name: estoppel-request-generation
description: 'Build tenant estoppel certificate requests for Oxford Realty Advisors directly from abstracted lease data, so every certified fact is pre-filled from the lease and every known defect is put to the tenant to cure. Use when the user mentions: estoppel, estoppel certificate, tenant estoppel, estoppel request, send estoppels, estoppel form, SNDA, subordination non-disturbance attornment, tenant acknowledgment, or asks what the estoppels should say. Also trigger during DD on any acquisition with occupied suites, and whenever lease-abstraction-pipeline or deal-execution surfaces a chain gap, an unexecuted counterpart, a manuscript amendment or a landlord-of-record mismatch. Pre-fills from the 32-field abstract, converts each quality flag into a certification, and produces one tailored form per tenant plus a cover letter. DRAFT ONLY — outbound counterparty send requires Gabriel confirmation. v1.1'
---

# Estoppel Request Generation — Oxford Realty Advisors

An estoppel is the one instrument in due diligence that makes the tenant — not the seller — certify what
the lease is. That makes it the cheapest available cure for every document defect found during abstraction,
and the last chance to get one. Blank-form estoppels waste it.

**Two rules govern everything below.** First, **pre-fill every certifiable fact from the lease abstract and
ask the tenant to confirm or correct it.** A tenant handed a blank form fills it from memory and returns
something that certifies nothing. Second, **every defect found during abstraction becomes an affirmative
certification.** If the file has a gap, the estoppel is where it closes.

**DRAFT ONLY.** These go to counterparties. Nothing is sent without Gabriel's explicit in-turn confirmation
(Hard Invariant 1). Estoppel forms are ordinarily transmitted by the seller under the PSA — confirm the
transmittal path before drafting the cover letter.

---

## STEP 1 — ASSEMBLE INPUTS

Required before drafting:

- The **32-field abstract** per tenant from `lease-abstraction-pipeline`, including `EXECUTION_STATUS`,
  `INGEST_PATH`, the `MANUSCRIPT AMENDMENTS` block, and all STEP 5 quality flags.
- The **instrument chain** per suite from `deal-execution` Workflow 3 (Lease-Chain Integrity). **If this skill is
  invoked earlier in DD than Workflow 3 has run for a given suite** (this skill's own trigger fires broadly "during DD
  on any acquisition with occupied suites," which can precede Workflow 3's completion) — don't block drafting or assume
  a clean chain. Draft with the chain check noted as outstanding and flag it for a follow-up pass once Workflow 3 runs.
- **Vesting** from `title-exam-abstraction` — the landlord name that should appear on every form.
- The **PSA estoppel article** — threshold SF, delivery deadline, condition-precedent status, and the
  agreed form if one is attached as an exhibit.
- The **deal thesis**, from the IC memo: what must be true for the underwriting to hold.

If the abstract has not been run, run it first. Drafting estoppels off a rent roll reproduces the rent
roll's errors under a tenant's signature, which is worse than not having them.

---

## STEP 2 — THE STANDING CERTIFICATIONS

Every ORA estoppel certifies, pre-filled from the abstract:

1. **The instrument chain**, by name and date — base lease, each renewal, each amendment — and that it is
   the complete agreement with no other written or oral modifications.
2. **Premises and square footage** as recited in the lease. Where the lease-recited SF differs from the rent
   roll, recite **both** and ask the tenant to confirm which governs its rent.
3. **Commencement and expiration dates.**
4. **Current base rent**, the escalation schedule, and the date through which rent has been paid.
5. **Additional rent / CAM / tax / insurance** obligations and the reimbursement structure, stated as the
   lease states it — gross, modified gross, or NNN.
6. **Security deposit** amount, or an affirmative statement that **none** is held. A silent form lets a
   deposit surface after closing.
7. **Options — affirmatively negative where the thesis requires it.** Not "the tenant has no options" as
   boilerplate, but: no renewal option, no extension option, no expansion option, no termination right, no
   purchase option, no right of first refusal, no right of first offer. Where a mark-to-market thesis
   depends on rollover, this is the single most important line on the form.
8. **No default** by either party and no outstanding landlord obligations, allowances, free rent, or
   unfunded tenant improvements.
9. **No prepaid rent** beyond the current month.
10. **Tenant of record** — the exact legal name of each party to the lease, including natural persons, and
    each signatory's authority.
11. **Acknowledgment of assignment** to the buyer entity, and attornment.

---

## STEP 3 — CONVERT EACH DEFECT INTO A CERTIFICATION

This is the step that distinguishes this skill from a template. Map every abstraction flag to language:

| Finding | Certification to add |
|---|---|
| `EXECUTION_STATUS` = UNEXECUTED / PARTIALLY_EXECUTED | Tenant certifies the named instrument is in full force and effect, was duly executed and delivered, and that tenant has performed under it since commencement — **and attaches its executed counterpart** |
| Chain gap (renewal evidenced only by a margin note, email, or rent-roll line) | Tenant certifies the term was extended by [instrument/means], on [date], to [expiry], and that no other extension exists |
| Manuscript amendment on the face of the lease | **Reproduce the amended clause verbatim in the form**, both struck and inserted text, and have the tenant certify it was mutually agreed and initialed by all parties on [date] |
| Landlord-of-record mismatch | Tenant certifies it recognizes [vested owner] as landlord, that it has paid rent to [payee], and consents to the assignment |
| Tenant of record is a natural person / trade name differs | Tenant certifies each individual's full legal name, any trade name used, and that no entity is a party |
| No security deposit found | Affirmative statement that no deposit, letter of credit or other security is held |
| Free parking or parking-count rights in the lease | Tenant certifies the number of spaces, whether reserved or non-exclusive, and any charge — this constrains site-plan changes |
| Landlord-borne operating obligations (utilities, HVAC, cleaning) | Tenant certifies which costs the landlord bears and that none is in arrears |
| Indemnity cap, low insurance limits, missing additional-insured | Certify the insurance and indemnity provisions as written — do not attempt to amend them through an estoppel |
| Weak holdover / consent-based holdover | Certify the holdover rate and that tenant has received no notice or agreement extending occupancy beyond expiry |
| SNDA required by the lease | Route to a separate SNDA — do not fold non-disturbance into the estoppel |

**Never use an estoppel to amend a lease.** It certifies facts. A term ORA wants changed is a lease
amendment (`lease-addendum`) or a re-leasing objective, and mixing the two invites a tenant to refuse the
whole form.

---

## STEP 4 — SIGNATURE BLOCK

Match the tenant of record exactly, and build one signature line per party. Where the tenant is two
individuals, both sign. Where entities and individuals are co-tenants, all sign. Where a manuscript
amendment is being ratified, every party to that amendment must sign — a hand change a successor landlord
cannot prove was mutual is a live dispute at rollover, which is precisely what the form exists to prevent.

Include: date, guarantor reaffirmation where a guaranty exists, and a statement that the certificate may be
relied upon by buyer, its lender, and their successors and assigns.

---

## STEP 5 — OUTPUT

- One **tailored DOCX form per tenant**, pre-filled, on ORA letterhead (Style Guide v1.0+; 16-point QC gate).
  Naming: `[DocType]_[Property]_[MMDDYYYY]` per the deal-file schema.
- A **cover letter** per the transmittal path — routed through the seller where the PSA so provides,
  following `communication-intelligence` voice register for counterparty mail.
- A **tracking table**: tenant, SF, threshold status, sent date, due date, PSA condition-precedent status,
  and the specific defect each form is curing.
- A **returned-form review checklist**: what a non-conforming response looks like for each pre-filled field,
  and which corrections are material enough to reopen underwriting or trigger a price adjustment.

Then hold for Gabriel's confirmation before anything leaves ORA.

---

## CROSS-SKILL INTEGRATION

- `lease-abstraction-pipeline` — supplies the abstract, flags and manuscript-amendment block. Run first.
- `deal-execution` — Workflow 2A item 12 sets estoppel content requirements; Workflow 3 supplies the chain check.
- `title-exam-abstraction` — supplies vesting and any SNDA/subordination requirement.
- `communication-intelligence` — drafts the counterparty cover letter.
- `lease-addendum` — the correct path for anything that amends rather than certifies.
- `legal-intelligence` — counsel review of any non-standard certification.
- `document-assembly` — its former Template 7 (Estoppel Certificate) is tombstoned in favor of this skill (2026-08-21);
  do not draft estoppels from that generic template library.

## Changelog

- v1.1 (2026-08-21, adversarial review): added the `document-assembly` cross-reference (its Template 7 is now
  tombstoned in favor of this skill — the two templates were left live with no tie-break, risking a "create estoppel"
  request routing to the wrong one). Added a fallback to STEP 1 for when `deal-execution` Workflow 3's Lease-Chain
  Integrity hasn't run yet for a suite this skill is asked to cover, since this skill's own trigger can fire before
  Workflow 3 completes.
- v1.0 (2026-08-21): initial. Built after the 754 Old State Route 74 lease review, where the estoppels were the natural cure for four separate defects — an unexecuted base lease amended by an executed First Amendment, a three-year renewal evidenced only by a handwritten margin note, an initialed manuscript change to a lease expiry, and a landlord named in the lease who was not the seller — none of which a blank-form estoppel would have reached.
