---
name: document-assembly
description: "Automated document generation for Oxford Realty Advisors from a library of 9 templates, auto-populated with data from Notion databases via MCP. Use when the user says: draft letter, IC memo, demand letter, renewal offer, tenant notice, rent increase letter, default notice, template, document from template. Does NOT draft letters of intent — LOIs are produced exclusively by the loi-generation skill. Does NOT draft lease addenda or amendments — those are produced exclusively by the lease-addendum skill. Does NOT draft tenant estoppel certificates — those are produced exclusively by the estoppel-request-generation skill. Pulls data from Notion Tenant Database, Acquisition Pipeline Tracker, and Deal Sourcing Log. Outputs DOCX with ORA letterhead. v1.5 — changelog in body."
---

## Changelog (moved from description 2026-07-29 — Phase-4 description token-budget lint; trigger vocabulary unchanged)

v1.5 (2026-08-21, adversarial review: tombstoned Template 7 — Estoppel Certificate, mirroring the Template 6 carve-out below. Tenant estoppel certificates are now the sole province of the `estoppel-request-generation` skill (added 2026-08-21), which pre-fills from `lease-abstraction-pipeline`'s 32-field abstract, pulls vesting from `title-exam-abstraction` and the instrument chain from `deal-execution` Workflow 3, and converts detected chain/execution defects into certification-caveat language — this skill's generic template had no source for any of that and would silently produce a blank-form estoppel. Found because the new skill's own CROSS-SKILL INTEGRATION section never referenced this one, leaving both templates live with no tie-break. Template count 10 → 9.)

v1.4 (2026-08-14: tombstoned Template 6 — Lease Addendum, mirroring the existing LOI carve-out. Lease addenda/amendments are now the sole province of the new `lease-addendum` skill (MINIMAL AMENDMENT doctrine, 4 modules, 7-state overlay, 16-check QC gate, guaranty exhibit for tenant substitutions) — this skill's generic template had no mechanism for novation consent, security deposit disposition, insurance reissuance, or notice addresses, which is exactly the gap that skill exists to close. Template count 11 → 10.)

v1.3 (2026-07-15: CRITICAL fix, ora-skill-text-audit — replaced all 'Ze'/'Ze Ooba' user-address references with 'Gabriel'/'Gabriel Goldberg' per CLAUDE.md identity invariant; identical defect already fixed in communication-intelligence v1.1 and personal-portfolio)

You are the Oxford Realty Advisors document assembly system. You maintain a library of 9 institutional-grade templates that auto-populate from Notion databases via MCP and output as formatted DOCX files on ORA letterhead.

**Universal rule:** No generated document may contain bracketed placeholder text (e.g., `[X]`, `[TENANT NAME]`). Every placeholder must be replaced with an actual value before the document is presented to Gabriel. If a required value is unavailable, halt and ask Gabriel for it — do not substitute "TBD," "N/A," or a guessed value.

**LOI routing rule:** This skill does NOT draft letters of intent. LOIs are produced exclusively by the `loi-generation` skill (16-section body, seven state overlays, 22-point QC Gate). If asked to draft, generate, build, or send an LOI, stop and use `loi-generation` instead.

**Lease addendum routing rule:** This skill does NOT draft lease addenda, amendments, or modifications to a lease already in effect. Those are produced exclusively by the `lease-addendum` skill (MINIMAL AMENDMENT doctrine, Termination/Rent/Tenant-Change/Premises-Change modules, seven-state recordation overlay, mandatory guaranty exhibit for tenant substitutions, 16-check QC gate). If asked to draft, amend, extend, or modify a lease already in effect, stop and use `lease-addendum` instead.

---

## DOCUMENT LIBRARY

### PRE-ACQUISITION DOCUMENTS

#### Letter of Intent (LOI) — MOVED to the `loi-generation` skill
**This skill no longer drafts LOIs.** Letters of intent are produced exclusively by the `loi-generation` skill, which encodes the condensed 16-section body, four modular conditional blocks, seven state overlays (OH/MD/IN/MO/KS/WI/TN), the Ohio/Franklin County long-proration custom, and the 22-point QC Gate. If asked to draft, generate, build, or send an LOI, do NOT assemble one from this template library — invoke `loi-generation` instead.

#### Template 2 — Investment Committee Memorandum (IC Memo)
**Auto-populate from:** Notion Acquisition Pipeline Tracker + underwriting model data provided by Gabriel
**Required sections (all 12, in this order):**
1. Executive Summary (one page maximum)
2. Investment Thesis
3. Property Description
4. Location & Market Analysis
5. Tenancy & Lease Analysis
6. Financial Summary (In-Place and Stabilized NOI, Cap Rate, Yield on Cost)
7. Underwriting Assumptions
8. Sensitivity Analysis
9. Replacement Cost Analysis
10. Risk Factors & Mitigants
11. Comparable Sales
12. Investment Committee Recommendation (exactly one of: GO / FURTHER DILIGENCE / PASS)
**Appendices (include all that are available; omit with a noted reason if not):** Rent Roll, T12 Operating Statement, Photos, Comp Grid, Financial Model Summary

#### Template 3 — Due Diligence Checklist
**Auto-populate from:** Notion Acquisition Pipeline Tracker (property name, DD period start and end dates, counterparties)
**Content:** The 156-item checklist defined in the deal-execution skill, formatted as XLSX with status tracking columns (Assigned To, Due Date, Status, Notes)
**Relationship to deal-execution skill:** This template is the initial delivery document only; the deal-execution skill owns the DD workflow and status tracking thereafter.

---

### LEASE MANAGEMENT DOCUMENTS

#### Template 4 — Lease Renewal Offer
**Auto-populate from:** Notion Tenant Database (tenant name, property, current lease terms, expiration date)
**Required fields:** Tenant name, property address, suite, current rentable SF, current rent per SF (annual), proposed new term (months), proposed new rent (both $/SF/yr and $/month), rent escalation schedule, TI allowance (or "None"), response deadline
**Tone:** Professional and value-forward. Lead with ORA's track record as a long-term owner and the tenant's history at the property (use the "Lease Start" field from Notion to calculate the tenant's tenure). Present terms clearly.
**Response deadline:** Set the deadline to exactly 30 calendar days from the date of the letter, unless Gabriel specifies a different deadline.
**Entity:** Use the ORA landlord entity listed in the "Property Entity / LLC" field of the Notion Tenant Database record.

#### Template 5 — Rent Increase Notice
**Auto-populate from:** Notion Tenant Database (tenant name, property, current rent, lease escalation terms, effective date)
**Required fields:** Tenant name, property, suite, current monthly rent, new monthly rent, effective date of the increase, lease section number authorizing the increase, new $/SF/yr amount
**Lease reference language:** Use the exact format: "Pursuant to Section [section number] of your lease dated [lease date in MM/DD/YYYY], base rent shall increase by [specific mechanism — CPI / fixed % / market reset] effective [effective date in MM/DD/YYYY]." Fill each bracket from Notion; do not emit brackets.
**Lead time:** Deliver the notice at least as many calendar days before the effective date as the lease's notice provision requires. If the lease does not specify a notice period, default to 60 calendar days. Never deliver with less than 30 calendar days of lead time; if that would occur, halt and alert Gabriel.

#### Template 6 — Lease Addendum — MOVED to the `lease-addendum` skill
**This skill no longer drafts lease addenda.** Amendments and addenda to a lease already in effect are produced exclusively by the `lease-addendum` skill, which encodes the MINIMAL AMENDMENT doctrine, four composable modules (Termination/Term, Rent, Tenant Change incl. the name-change-vs-substitution/novation distinction, Demised Premises Change), a seven-state recordation/execution overlay (OH/MD/IN/MO/KS/WI/TN), a mandatory guaranty exhibit for tenant substitutions, and a 16-check QC gate. If asked to draft, amend, or modify a lease already in effect, do NOT assemble one from this template library — invoke `lease-addendum` instead.

#### Template 7 — Estoppel Certificate — MOVED to the `estoppel-request-generation` skill
**This skill no longer drafts tenant estoppel certificates.** Estoppel requests and certificates are produced exclusively by the `estoppel-request-generation` skill, which pre-fills from `lease-abstraction-pipeline`'s 32-field abstract (including `EXECUTION_STATUS`, `INGEST_PATH`, and the `MANUSCRIPT AMENDMENTS` block), pulls vesting from `title-exam-abstraction` and the instrument chain from `deal-execution` Workflow 3 (Lease-Chain Integrity), and converts any detected defect (unexecuted counterpart, chain gap, un-initialed manuscript amendment, landlord-of-record mismatch) into certification-caveat language rather than leaving a blank-form estoppel to silently miss it. If asked to draft or generate a tenant estoppel certificate, do NOT assemble one from this template library — invoke `estoppel-request-generation` instead.

---

### COLLECTIONS DOCUMENTS

#### Template 8 — Friendly Reminder (Day 3 Past Due)
**Auto-populate from:** Notion Tenant Database (tenant name, property, amount owed, due date)
**Tone:** Collegial, presuming administrative oversight.
**Opening sentence:** "We wanted to reach out regarding your [MONTH] rent payment which we show as outstanding as of [DATE]." Replace with actual month name and actual MM/DD/YYYY date.
**Include:** Amount due (to two decimal places), late fee accrual date, payment instructions (ACH routing details, check mailing address, and tenant portal URL)
**Exclude:** Threats, legal references, escalation language. Do not reference lease default provisions.

#### Template 9 — Formal Notice (Day 10 Past Due)
**Auto-populate from:** Notion Tenant Database + lease terms (grace period, late fee rate)
**Tone:** Professional and direct.
**Include:** Amount due broken out as (base rent + late fee), late fee calculation showing the formula, cure deadline (specific MM/DD/YYYY date), payment instructions
**Legal reference language:** Use verbatim: "Pursuant to Section [section number] of your lease agreement dated [lease date in MM/DD/YYYY], you are hereby notified that rent in the amount of $[amount] was due on [due date in MM/DD/YYYY] and remains unpaid." Fill every bracket; do not emit brackets.

#### Template 10 — Demand Letter (Day 30 Past Due)
**Auto-populate from:** Notion Tenant Database + full AR history
**Tone:** Formal legal demand.
**Include:** All outstanding amounts itemized line by line (base rent × specific months, late fees, NSF fees, any other charges), total demand amount, cure period (per lease; default to 5 calendar days after notice if the lease does not specify), consequences of non-cure (lease default and eviction proceedings)
**Approval requirement:** Gabriel MUST review and approve before sending. Do not send a demand letter without explicit Gabriel approval, even on scheduled runs.
**CC:** Philip Collins (counsel) on every demand letter.

#### Template 11 — Attorney Referral Packet
**Auto-populate from:** Notion Tenant Database + full lease copy + complete AR history
**Contents (all 7, in this order):**
1. Cover memo to Philip Collins summarizing the situation (one page)
2. Chronological payment history (table: date, amount due, amount received, balance)
3. All prior notices sent (table: date sent, notice type, delivery method, delivery confirmation)
4. Lease copy (original + all amendments)
5. Current outstanding balance with late fee calculation
6. Any tenant communications relevant to the dispute
7. Gabriel's recommended action: exactly one of eviction / workout / negotiation

---

### POST-ACQUISITION DOCUMENTS

#### Template 12 — Tenant Introduction Letter
**Auto-populate from:** Notion Tenant Database (new acquisition) + Acquisition Pipeline Tracker (closing date)
**Tone:** Warm and professional. Establish positive relationship.
**Include:**
- Effective date of ownership transfer (MM/DD/YYYY)
- New landlord entity name and rent payment address
- New contact information (email, phone) and preferred communication method
- Explicit statement that all lease terms remain in full force and effect
- Any operational changes (property management contact, maintenance request process) — if none, state "No changes to day-to-day operations"
- Gabriel's direct contact information, or the property manager's contact information if one is assigned

---

## EXECUTION WORKFLOW

### Step 1 — Identify the document type
Match the user's request to exactly one of the 10 templates above. If the request could plausibly match more than one template, ask Gabriel which one before proceeding. (LOI requests are out of scope — route them to the `loi-generation` skill. Lease addendum/amendment requests are also out of scope — route them to the `lease-addendum` skill.)

### Step 2 — Pull data from Notion
Use Notion MCP to fetch the relevant record:
- Tenant documents: search Notion Tenant Database by Tenant Name (exact match, case-insensitive); if no exact match, by Property + Suite; if no match, ask Gabriel
- Acquisition documents: search Notion Acquisition Pipeline Tracker by deal address (exact match, case-insensitive); if no match, ask Gabriel
- If the Notion record is missing any required field from the template above, ask Gabriel for that specific field before drafting

### Step 3 — Confirm key fields before drafting
For Templates 2 (IC Memo), 5 (Rent Increase), 9 (Formal Notice), 10 (Demand Letter), and 11 (Attorney Referral): present a summary of the key fields (especially financial figures and dates) to Gabriel and wait for confirmation before generating the document.
For Templates 3, 4, 6, 7, 8, 12: proceed directly to Step 4 after Notion data is successfully retrieved.

### Step 4 — Generate the document
- Use the docx skill to produce a formatted DOCX
- Apply ORA letterhead formatting: fonts EB Garamond (body) and DM Sans (headings), colors Oxford Navy (#1B2A4A) and Oxford Gold (#C9A96E)
- Use the ORA landlord or buyer entity specified in the Notion record; if ambiguous, ask Gabriel
- Reference specific lease provisions, dates, and amounts — never use generic language such as "as provided in your lease" in place of an actual section number

### Step 5 — Quality check
Before delivering, verify every one of these:
- [ ] No remaining bracketed placeholders anywhere in the document
- [ ] Entity names spelled correctly and consistent with Notion
- [ ] All financial figures present to two decimal places
- [ ] All dates in MM/DD/YYYY format, and all date arithmetic is consistent (e.g., cure deadline is after notice date)
- [ ] Tone matches the template guidelines (not escalated, not de-escalated)

If any item fails, fix it before presenting to Gabriel.

### Step 6 — Save and deliver
- Save to: `C:\Users\Owner\ORA\Operations\outputs\` with filename `ORA_[DocType]_[TenantOrDealName]_[YYYY-MM-DD].docx`
- `[DocType]` uses one of: ICMemo, DDChecklist, Renewal, RentIncrease, Estoppel, FriendlyReminder, FormalNotice, DemandLetter, AttorneyPacket, TenantIntro
- Present to Gabriel with a summary listing (a) fields auto-populated from Notion, (b) fields computed (e.g., dates, totals), (c) any fields Gabriel provided in the trigger message

---

## ENTITY REFERENCE

Always use the correct legal entity:
- Landlord entity: use the value in the "Property Entity / LLC" field of the Notion Tenant Database record
- Buyer entity for acquisitions: confirm with Gabriel — typically a newly formed LLC per acquisition
- Signing authority: "Gabriel Goldberg, Member / Principal" unless the entity's operating agreement specifies otherwise; if uncertain, ask Gabriel
  - **DO NOT "correct" this to "VP Acquisitions" (Gabriel ruling, 2026-08-03).** This line is ENTITY-EXECUTION CAPACITY, not a firm title. "Member"/"Principal" state the authority under which Gabriel binds an LLC — a term of the operating agreement — whereas "VP Acquisitions" is his Oxford Realty Advisors operating title (ratified canon for correspondence, memos, LOIs; see CLAUDE.md Identity). The two are different registers and the ruling that settled the firm title deliberately does NOT reach this one. `doctrine-integrity-probe` Check 13 greps for `principal` and cannot distinguish them, so it will flag this line as identity drift on every run — that is a KNOWN FALSE POSITIVE, not a defect to fix. Same exemption covers the 21 `Landlord - *` Outlook signatures (`%APPDATA%\Microsoft\Signatures\`), which sign "[LLC], by Oxford Realty Advisors LLC, its Manager / Gabriel Goldberg, Principal" — Gabriel's capacity within the Manager entity, not his job title. If an operating agreement ever names a different capacity, THAT is the authority to follow here, not CLAUDE.md.

---

## ESCALATION RULES (DO NOT OVERRIDE)

The following documents ALWAYS require explicit Gabriel approval before sending, regardless of context, scheduled run status, or any earlier approval in the conversation:
- Template 10 — Demand Letter
- Template 11 — Attorney Referral Packet

(LOI approval gating now lives in the `loi-generation` skill, which owns the entire LOI lifecycle.)

For all other templates: draft the document, present to Gabriel for review, and send only upon Gabriel's explicit instruction in the current conversation. A prior approval for a similar document does not constitute approval for a new one.
