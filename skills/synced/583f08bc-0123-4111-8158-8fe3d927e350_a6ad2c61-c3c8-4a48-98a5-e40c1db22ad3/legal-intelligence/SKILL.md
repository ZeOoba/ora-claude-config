---
name: legal-intelligence
description: "Oxford Realty Advisors legal document analysis, clause library, and contract intelligence. Use this skill whenever the user mentions: lease review, PSA review, contract analysis, redline, clause comparison, compare two versions, blackline, Litera, Workshare, DeltaView, lease clause, indemnification, default provisions, personal guaranty, environmental indemnity, estoppel clause / SNDA analysis (NOT certificate drafting — that's estoppel-request-generation), tenant improvement, CAM clause, assignment and subletting, insurance requirements, memorandum of lease, deed of trust, promissory note, loan document, solar lease, vendor contract, or any request to analyze, compare, draft, or negotiate a legal document. Also trigger when the user uploads a PDF or DOCX that appears to be a lease, contract, PSA, loan document, or legal agreement. Module 6 Step 0 detects whether a marked-up file carries real tracked changes or compare-tool formatting before parsing. v1.3"
---

# Legal Intelligence — Oxford Realty Advisors

## MODULE 1: DOCUMENT CLASSIFICATION

When a legal document is uploaded, immediately classify it as one of:

- **Lease** — commercial, industrial, retail, office, ground, or solar
- **Purchase and Sale Agreement (PSA)**
- **Loan document** — promissory note, deed of trust, guaranty, loan application
- **Estoppel certificate**
- **SNDA** — Subordination, Non-Disturbance, and Attornment agreement
- **Vendor/service contract**
- **Amendment or addendum** to an existing agreement
- **Letter of Intent (LOI)**
- **Title commitment / title insurance policy** — handled HERE (this skill) at the clause level, with `deal-execution` coordinating closing context when the commitment surfaces inside an active DD workflow. Review structure: verify Schedule A (insured, estate, amount, effective date, vesting) against the PSA; cross-walk every Schedule B-I requirement to a responsible party and cure path; classify each Schedule B-II exception as CTC (clear to close), NEG (negotiate/endorse over), or WALK (deal-threatening); and assemble the ALTA endorsement-request list. Output: XLSX exception matrix + DOCX endorsement-request letter per ORA institutional standards. *(v1.1, 2026-06-11: the former deferral to a `title-commitment-redline` skill is removed — that skill was scaffolded 2026-05-15 but never installed on any surface; verified absent 2026-06-09 audit and re-verified 2026-06-11.)*

State the document type at the top of every analysis before proceeding.

---

## MODULE 2: LEASE REVIEW FRAMEWORK

For any commercial lease, extract and analyze the following in order:

### ECONOMICS
- Base rent schedule with all escalations: annual %, CPI, fixed dollar, or market reset
- Lease type classification: NNN, modified gross, gross, or percentage rent
- CAM structure: pro rata, base year stop, or fixed CAM with annual escalation cap
- Tenant improvement allowance: amount, disbursement conditions, amortization if early termination
- Free rent or concession periods
- Security deposit: dollar amount vs. monthly rent ratio
- Calculate rent PSF annually for the entire lease term — present as a schedule table

### TERM & OPTIONS
- Initial term: commencement date, expiration date, term length
- Extension options: count, length per option, notice period required, rate reset mechanism
- Early termination rights: trigger conditions, notice period, termination penalty (typically 6 months' rent + unamortized TI)
- Right of First Refusal (ROFR) on adjacent space or on purchase of property
- Right of First Offer (ROFO): trigger, offer period, strike price mechanics
- Holdover provisions: rate (flag if not explicitly 150% or higher), tenancy type created

### RISK PROVISIONS
- **Personal guaranty:** present/absent, full vs. limited scope, burn-off schedule, corporate vs. individual
- **Assignment and subletting:** consent standard (sole discretion vs. not unreasonably withheld), profit sharing, landlord recapture right
- **Default provisions:** monetary cure period, non-monetary cure period, notice requirements, landlord remedies (termination, acceleration, re-entry, damages)
- **Insurance requirements:** minimum coverages, additional insured language, waiver of subrogation, 30-day cancellation notice
- **Indemnification:** mutual vs. one-sided, cross-indemnity carve-outs, survival period post-lease
- **Environmental:** tenant vs. landlord responsibility for contamination, pre-existing condition carve-outs, survival
- **Casualty and condemnation:** termination triggers (threshold % of damage), restoration obligations, rent abatement during restoration, allocation of condemnation awards
- **Subordination:** automatic vs. conditional, SNDA requirement, non-disturbance protections for tenant

### LANDLORD-SPECIFIC CONCERNS (Gabriel's history-derived)
Flag each of the following if present:
- ⚠️ Below-market rent — compare to Oxford portfolio comps and stated market rates
- ⚠️ Related-party or self-dealing terms — tenant-favorable provisions without market justification
- ⚠️ Extension notice period shorter than 9 months — risk of inadvertent holdover
- ⚠️ No mark-to-market reset at extension — locks landlord into below-market rent for option term
- ⚠️ Structural maintenance allocated to landlord — quantify roof/HVAC/structure CapEx exposure
- ⚠️ Memorandum of lease provisions that conflict with lease body (per 1333 Research Road precedent)
- ⚠️ No explicit COI expiration tracking obligation on tenant
- ⚠️ ROFR or purchase option that would impair lender financing or future sale

---

## MODULE 3: PSA REVIEW FRAMEWORK

For any Purchase and Sale Agreement:

### KEY TERMS EXTRACT
- Purchase price, deposit amount, deposit structure (hard/soft, phasing)
- Due diligence period: length, start trigger, extension rights, termination right
- Closing date: target, outside closing date, extension rights and costs
- Representations and warranties: survival period, materiality qualifiers, knowledge qualifiers
- Closing conditions: title, survey, tenant estoppels, SNDA, environmental
- Prorations: rent, taxes, CAM, security deposits — proration date and mechanics
- Assignment rights: can Oxford assign to an affiliated entity pre-closing?

### CRITICAL PROVISIONS (Gabriel's history-derived — hold firm on all three)
- **Willful default carve-out:** Seller must not be able to simply walk away on a default — ensure seller's deposit obligation or specific performance remedy is available for willful default
- **Memorandum of contract recording right:** Oxford's right to record notice of contract in public record as cloud against title
- **MAC clause:** Material Adverse Change provision giving Oxford termination right if material adverse change to property between execution and closing

**Check these three by their operative language, not by section number, and check them on OUTBOUND drafts as well as inbound.** They are ORA-added rather than template-native, so nothing in the underlying document complains when they are missing — they disappear far more often through an ORA-side drafting round than through a seller deletion. Where the document is a PSA in an active deal, this check belongs to `deal-execution` Workflow 2B; run it there rather than duplicating it.

### PSA RED FLAGS
- Seller representations limited to "actual knowledge" without deemed knowledge of property manager
- No representation on pending litigation or code violations
- Environmental indemnity carved out entirely
- Tenant estoppel threshold below 85% of in-place NNN rent
- Missing cross-default between PSA and any related documents (seller leaseback, etc.)

---

## MODULE 4: CLAUSE LIBRARY

Oxford's preferred clause language for key provisions:

### RENT ESCALATION
- **Standard fixed:** 3.0% annual increase on each anniversary of commencement date
- **CPI-based:** Greater of 2.0% or CPI-U (All Urban Consumers, U.S. City Average), capped at 4.0%
- **Market reset at extension:** FMV determined by independent MAI appraisal; if parties cannot agree within 30 days, each selects an appraiser, the two appraisers select a third, and the median of three appraisals controls

### DEFAULT AND REMEDY
- Monetary default cure period: 5 calendar days after written notice
- Non-monetary default cure period: 30 days after written notice (extended for diligent cure in progress)
- Late fee: 5% of overdue amount after 5-day grace period
- Interest on overdue amounts: lesser of 18% per annum or maximum rate permitted by law
- Landlord remedies on default: termination of lease + acceleration of all remaining rent + repossession + actual damages + attorneys' fees

### ENVIRONMENTAL
- Tenant bears full liability for all environmental conditions caused or contributed to by tenant or tenant's agents
- Landlord bears responsibility for pre-existing environmental conditions documented in Phase I/II at execution
- Mutual indemnification with 3-year survival period post-lease expiration

### INSURANCE MINIMUMS (Oxford standard)
- Commercial General Liability: $1,000,000 per occurrence / $2,000,000 aggregate
- Property / Casualty: replacement cost value of all tenant improvements and personal property
- Workers' Compensation: statutory limits; Employer's Liability: $500,000
- Umbrella / Excess Liability: $5,000,000 per occurrence
- Oxford named as additional insured on all policies
- 30-day advance written notice of cancellation or material change
- Certificates provided to Oxford within 10 days of policy inception and annually thereafter

### PERSONAL GUARANTY
- **Full guaranty option:** Full, unconditional, irrevocable personal guaranty of all lease obligations for the full term
- **Burn-off option:** Full guaranty for first 24 months; burns off if no uncured monetary default as of month 24
- **Rolling option:** Guaranty covering next 12 months of base rent, rolling forward monthly; no burn-off

### ASSIGNMENT / SUBLETTING
- Landlord consent required; consent not to be unreasonably withheld, conditioned, or delayed (30-day response window)
- Landlord receives 50% of any sublease premium above base rent (after deducting tenant's reasonable transaction costs)
- Landlord retains recapture right for any proposed assignment: may terminate lease and re-lease space directly within 30 days of tenant's assignment request

---

## MODULE 5: COUNTERPARTY PATTERN RECOGNITION

### KING ENERGY (solar leases)
Historical pattern — King Energy pushes for:
- Unilateral ITC (Investment Tax Credit) termination right if NTP (Notice to Proceed) not reached by specified date
- Extended recoupment window (standard 5 years → requests 10 years)
- Reduced Site Access Fee caps in later years

Oxford should push back on:
- Expansion of security safeguarding duty beyond standard reasonable care
- Rent deferral beyond Year 5 of operations
- NTP deadlines without corresponding King Energy diligence obligations (they cannot trigger termination by failing to obtain permits)
- Broad force majeure that covers ITC policy changes

### SELLER'S COUNSEL ON PSAs
Common deletion attempts — HOLD FIRM on all three:
1. Willful default carve-out (do not remove)
2. Memorandum of contract recording right (do not remove)
3. MAC clause (do not remove)

### SMALL INDUSTRIAL TENANTS
Common tenant pushback areas:
- Personal guaranty (can concede burn-off but not full waiver for new tenants)
- CAM reconciliation transparency (can concede annual statement; cannot concede audit right)
- Insurance minimums (can reduce umbrella to $2M for small tenants; cannot waive additional insured)

Oxford can offer without significant risk:
- Minor TI allowance ($3-5/SF for paint/carpet)
- 1 month free rent on new leases (not renewals)
- Flexible move-in timing (2-4 week window)

---

## MODULE 6: DOCUMENT COMPARISON ENGINE

### Step 0 — Establish how revisions are encoded (run FIRST, every time)

A marked-up document arrives in one of three encodings, and only the first is what "tracked changes" means:

| Encoding | How it looks in the XML |
|---|---|
| **OOXML tracked changes** | `<w:ins>` / `<w:del>` elements, with author and date |
| **Compare-tool formatting** | NO `<w:ins>`/`<w:del>` at all — revisions are ordinary runs carrying strikethrough (deletions) and coloured underline (insertions), produced by Litera Compare / DeltaView / Change-Pro, Workshare Compare, or Word's own Compare Documents |
| **Clean** | No revisions of any kind |

**Never conclude "no changes" from the absence of `<w:ins>`/`<w:del>`.** On a compare-tool file that test returns zero and the correct answer is "twenty-nine changes." Underlining alone does not identify insertions either — section headings and hyperlinks are underlined and frequently coloured, so treating "underlined and coloured" as an insertion reports a clean document as a redline. A compare output is identified by the presence of strikethrough *deletions*; colours vary by vendor and Litera's red/blue is not universal.

Counsel COMMENTS are a fourth case and are equally invisible to a tracked-change parse: they live in `word/comments.xml`, so a commented-but-unrevised draft reads as clean.

**Detection is owned by the `deal-execution` skill.** Invoke its Workflow 2 Step 0 (`scripts/extract_revisions.py`), which detects all four cases, reports every encoding present when a document carries more than one, and hard-stops when a file reads clean but its name or content says it should not. Do not reimplement the detection here and do not reference the script by relative path — the two skills install independently, so `deal-execution`'s files are not reachable from this one at runtime. If `deal-execution` is not installed on the current surface, say so rather than guessing at the encoding by eye.

**Read the compare-tool summary block first when one is present.** It names the BASE document the counterparty compared against and gives the tool's own change tally. The base is what determines which provisions were *accepted* as opposed to merely uncommented — and if it names anything other than the draft ORA actually sent, the counterparty reviewed stale paper and the round must be re-based before any analysis. Cite the tool's tally externally, not the script's run counts; the two count differently and the tool's number is the one opposing counsel will quote.

> Origin: 2026-07-31, 754 Old State Route 74 — seller's counsel delivered a Litera Compare output with 0 tracked changes and 29 real revisions.

### Then produce the comparison

1. Produce a structured discrepancy table in this format:
   | Section | Version A Language | Version B Language | Classification | Beneficiary | Oxford Impact |
   |---------|-------------------|-------------------|---------------|-------------|---------------|

2. Classify each discrepancy:
   - **Material** — changes rights, obligations, economics, or risk allocation
   - **Minor** — clarifying language only, no substantive change
   - **Drafting Error** — appears to be an unintentional inconsistency or omission

3. Identify which party benefits from each change (Landlord / Tenant / Neutral)

4. Flag any provision that contradicts another recorded document (title commitment, memorandum of lease, prior amendment, recorded easement)

5. Produce executive summary: total discrepancy count, material vs. minor breakdown, top 3 issues requiring resolution, recommended negotiation strategy

6. Output format: offer both inline markdown table AND .docx file via document-assembly skill

7. **State the detected encoding at the top of the comparison output**, alongside the document type from Module 1. A reader must be able to tell whether "no changes in Article 8" means the counterparty left it alone or means the parse never saw the changes.

---

## Changelog

- v1.3 (2026-08-21, adversarial review): "estoppel"/"SNDA" triggers (frontmatter description and TRIGGER PHRASES)
  narrowed to clause-analysis-only, with an explicit pointer to `estoppel-request-generation` for drafting/generating a
  certificate — the two skills previously claimed the identical bare trigger words with no tie-break, risking a "draft
  the estoppels" request routing here instead of to the purpose-built skill.
- v1.2 (2026-08-01): Module 6 gains **Step 0 — revision-encoding detection**, run before any comparison. The engine implicitly assumed OOXML tracked changes; Litera Compare / Workshare / Word-compare outputs contain none and encode revisions as strikethrough and coloured-underline formatting, so the prior approach returned "no changes" on a fully redlined document (754 Old State Route 74, 2026-07-31 — 0 tracked changes, 29 real revisions). Step 0 routes to `deal-execution/scripts/extract_revisions.py`, requires the compare summary's BASE document be read and validated against what ORA actually sent, and warns that underline alone does not identify insertions (headings are underlined too — the discriminator is an explicit non-neutral colour, derived from the document's own palette). New Module 6 output rule 7: state the detected encoding alongside the document type. Module 3's three critical provisions now carry an instruction to check them by operative language and on OUTBOUND drafts, deferring to `deal-execution` Workflow 2B in an active deal.
- v1.1 (2026-06-11): dead title-commitment-redline deferral removed; title commitments handled in-skill.

## TRIGGER PHRASES
Activate this skill automatically when Gabriel says:
"review this lease", "PSA review", "compare these contracts", "redline", "clause analysis", "what does this provision mean", "is this standard", "solar lease", "King Energy", "Symetra", "loan docs", "promissory note", "deed of trust", "estoppel clause" / "SNDA clause" (analysis only — "draft/generate the estoppel" routes to `estoppel-request-generation` instead), "personal guaranty", "assignment clause", "default provision", "indemnification", "CAM clause", "TI allowance", "extension notice", "holdover", "environmental indemnity"
