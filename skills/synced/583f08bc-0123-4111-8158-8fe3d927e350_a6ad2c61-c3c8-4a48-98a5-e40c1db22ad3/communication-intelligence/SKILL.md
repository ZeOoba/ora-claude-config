---
name: communication-intelligence
description: "Context-enriched communication drafting for Oxford Realty Advisors. Use this skill whenever the user mentions: write an email, draft a response, compose a message, reply to, reach out to, follow up with, send a letter to, communicate with, notify, or any request to produce a written communication to a tenant, broker, vendor, lender, attorney, or counterparty. Also trigger when the user receives an email and needs help crafting a response. This skill automatically enriches drafts with relationship context from Notion, HubSpot, and conversation history. v1.2 (2026-07-11)"
---

# Communication Intelligence — Oxford Realty Advisors

## MODULE 1: CONTEXT ENRICHMENT WORKFLOW

Before drafting any communication, execute this enrichment sequence:

### Step 1 — Identify the Recipient
Determine recipient type:
- **Tenant** → known occupant of an Oxford property
- **Broker** → industrial or commercial real estate broker
- **Vendor / Service Provider** → maintenance, legal, environmental, accounting, insurance
- **Lender** → bank, life insurance company, or private lender
- **Attorney** → transaction counsel, tenant counsel, opposing counsel
- **Government / Regulatory** → tax assessor, zoning authority, environmental agency
- **Partner / Internal** → Eric, Gabriel, co-investors

### Step 2 — Pull Relationship Context by Recipient Type

**TENANT:**
Search Notion Tenant Database for:
- Property address and unit/suite
- Current base rent and rent PSF
- Lease commencement and expiration dates
- Escalation schedule and next escalation date
- Current AR balance and collections status
- Payment history (on-time, chronic late, delinquent)
- Renewal status and any renewal offer outstanding
- Security deposit amount on file
- Personal guaranty status
- Insurance expiration and compliance status
- Tenant Grade (A/B/C/D)
- Any open maintenance requests or disputes

**BROKER:**
Search HubSpot contacts for:
- Deals this broker has submitted (property, size, price, outcome)
- Current deal stage for any active submission
- Last interaction date
- Markets the broker covers
- Relationship quality (preferred vs. occasional vs. new)

**VENDOR:**
Search Notion Vendor & Advisor Directory for:
- Service type and scope
- Current contract status and expiration
- Performance history
- Billing relationship (hourly, retainer, per-project)

**LENDER:**
Search memory and conversation history for:
- Loan details (property, balance, rate, maturity)
- Relationship status (active borrower, applicant, prospective)
- Past interactions and covenant compliance status

**ATTORNEY:**
Search Notion Key Contacts for:
- Role and specialty (transaction, litigation, environmental, tax)
- Active matters
- Billing relationship and hourly rate
- Firm conflicts to be aware of

### Step 3 — Check for Active Issues
Before drafting, verify:
- Any open AR balance or active collections stage (flag collections letters to use escalating tone)
- Any pending lease expiration within 180 days (flag renewal context)
- Any active deal involving this contact (flag deal-specific sensitivity)
- Any recent correspondence in Email Response Queue (avoid duplicating prior communication)
- Any legal hold or dispute in progress (flag for precise, protective language)

### Step 4 — Determine Communication Posture
Select the appropriate posture based on context:
- **Routine / informational** → professional, neutral, efficient
- **Collections (Stage 1 — Reminder)** → courteous but direct; reference lease obligation
- **Collections (Stage 2 — Formal Notice)** → firm; cite lease section; state cure deadline
- **Collections (Stage 3 — Demand)** → no pleasantries; formal demand; state escalation consequence
- **Collections (Stage 4 — Legal Referral)** → notify referral to legal counsel; cease direct negotiations
- **Renewal negotiation** → firm but constructive; emphasize mutual benefit and continuity value
- **New relationship / outreach** → warm, highlight Oxford's track record and capabilities
- **Legal / adversarial** → precise, formal, protective of Oxford's rights; no admissions

---

## MODULE 2: TONE AND STYLE GUIDELINES

Oxford communications must be:
- **Direct and professional** — no unnecessary preamble, pleasantries, or filler phrases
- **Specific** — always reference property address, unit/suite number, lease dates, dollar amounts, and section citations
- **Actionable** — every communication ends with a clear ask, deadline, or next step
- **Entity-aware** — always use the correct Oxford LLC entity as the signatory (not "Oxford Realty Advisors" generically when a specific LLC is landlord)
- **Measured** — never emotional, never threatening language that could be used against Oxford in litigation

### Signature Block (standard)
```
Gabriel Goldberg
Oxford Realty Advisors
[Direct Phone]
ggoldberg@oxfordra.net
oxfordra.net
```

### Entity Awareness
When drafting landlord communications, use the correct entity:
- Verify which LLC holds the subject property from memory context or Notion Entity Structure DB
- Sign as: "[Property LLC Name], by Oxford Realty Advisors, its Manager"
- Do not sign as "Oxford Realty Advisors" if the actual landlord is a separate property LLC

---

## MODULE 3: COMMUNICATION TYPE TEMPLATES

### Rent Delinquency — Stage 1 (Reminder, 1–5 days late)
Subject: Rent Reminder — [Property Address], Suite [X]
- Reference lease section for rent due date
- State exact amount owed and due date
- Request payment within 5 business days
- Include payment instructions

### Rent Delinquency — Stage 2 (Formal Notice, 6–14 days late)
Subject: Notice of Unpaid Rent — [Property Address], Suite [X]
- Cite lease section number explicitly
- State exact amount owed including late fee (5% after 5-day grace)
- Issue formal cure notice with specific cure deadline
- State that failure to cure may result in further action under the lease

### Rent Delinquency — Stage 3 (Demand, 15–30 days late)
Subject: Formal Demand for Payment — [Property Address]
- No pleasantries
- State total amount owed (rent + late fees + interest)
- Issue final demand with hard deadline
- State consequences: termination of lease, legal action, credit reporting

### Lease Renewal Offer
Subject: Lease Renewal Proposal — [Property Address], Suite [X]
- Reference current lease term expiration date
- Present renewal term, rate, and escalation structure
- Highlight Oxford's investment in the property
- Request response by specific date (30 days from letter date)
- Include acceptance mechanism (countersign and return or call to negotiate)

### COI / Insurance Request
Subject: Certificate of Insurance Required — [Property Address], Suite [X]
- Reference lease section requiring COI
- State expiration date of prior COI (or note that no COI on file)
- Provide Oxford's certificate holder information
- Request updated COI within 10 business days

### Deal Outreach to Broker
Subject: Seeking Industrial Assets — [Market]
- State Oxford's acquisition criteria concisely: market, size ($1M–$10M), building type (shallow-bay industrial/flex), deal type (value-add Class B/C)
- Express preference for off-market or lightly marketed deals
- Offer quick timeline and clean execution
- Do not disclose current pipeline or acquisition targets

### OM / Broker Package Request (added 2026-07-11)
When requesting an OM, broker package, or financial summary from a broker, include a line asking for the **native file or a text-layer PDF export** — not a "Print to PDF" rasterized scan. Rationale (proven this session): rasterized scans have no extractable text, forcing vision-based page-by-page reading and measurably slowing underwriting turnaround. Do not wait until a scanned package arrives to raise this — ask upfront on every OM request.

---

## MODULE 4: MULTI-CHANNEL FORMATTING

Adapt format based on channel:

### Formal Email (tenant notice, legal correspondence)
- Full professional format
- Subject line references property, tenant name, and topic
- Proper salutation: "Dear [First Name]:" or "Dear Mr./Ms. [Last Name]:" for formal
- Body: 2–4 paragraphs maximum
- Closing: "Sincerely," or "Regards,"
- Full signature block with entity, phone, email

### Informal / Follow-Up Email (broker, vendor check-in)
- Concise: 3–5 sentences
- Conversational but professional
- No formal salutation required
- Signature: first name only or abbreviated block

### HubSpot Note (internal CRM entry)
- Third-person narrative: "Gabriel spoke with [Broker Name] re: [Deal]..."
- No salutation or closing
- Log outcome and next step
- Tag deal record and contact record

### Text Message
- Maximum 3 sentences
- No attachments referenced
- Ends with clear single ask or action
- Do not send sensitive financial or legal information via SMS

---

## MODULE 5: TEMPLATE INTEGRATION

When communication type matches a document-assembly template, use that template as the base and layer relationship context on top. Reference the `document-assembly` skill for:
- Renewal offer letters (tenant-specific rent schedule populated)
- Collections notices (lease section citations auto-populated)
- LOI and PSA cover letters (deal-specific terms populated)
- Lender correspondence (loan terms populated from Loan Portfolio Tracker)

---

## TRIGGER PHRASES
Activate this skill when Gabriel says:
"write an email", "draft a response", "compose a letter", "reply to", "reach out to", "follow up with", "send a letter", "communicate with", "notify", "collections letter", "renewal offer", "broker outreach", "COI request", "demand letter", "tenant notice", "lender update", "vendor communication", "how should I respond to", "what should I say to"

## Changelog

- v1.1 (2026-07-08): CRITICAL fix (Skill Text Audit finding 1) — Standard Signature Block (§ Module 2) signed outbound comms as "Ze Ooba" / `ze@oxfordra.net`, an incorrect/retired identity never valid for this principal. Corrected to Gabriel Goldberg / `ggoldberg@oxfordra.net` per current routing canon. Entity Awareness logic immediately below (landlord mail signs as the property LLC, not the generic firm name) was reviewed and left intact — not regressed by this fix. Note: this repo copy already carried the correct block; the installed Cowork runtime copy did not (silent re-sync drift) — repackage and reinstall via `package-and-stage-skill` to close the gap.
- v1.2 (2026-07-11): added a new "OM / Broker Package Request" template under Module 3 — proactively ask brokers for native/text-layer PDF exports rather than Print-to-PDF rasterized scans, which force vision-based extraction and slow underwriting. Motivating incident this session: an entire OM/brochure set arrived rasterized with no text layer. No other content changed. Repackage and reinstall via `package-and-stage-skill` to reach the installed Cowork runtime copy.
