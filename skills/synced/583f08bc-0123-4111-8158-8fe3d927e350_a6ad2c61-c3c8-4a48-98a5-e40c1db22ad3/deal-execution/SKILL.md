---
name: deal-execution
description: 'Oxford Realty Advisors deal execution skill covering PSA negotiation through closing. Use when the user mentions: PSA, purchase and sale agreement, due diligence, DD checklist, redline analysis, seller response, closing checklist, title review, environmental review, estoppel content/DD conformance (drafting an actual certificate routes to estoppel-request-generation), closing statement, post-closing, deal execution, under contract, PSA negotiation, seller redlines, buyer provisions, contract markup, review PSA draft, PSA vs LOI, check the PSA against the LOI, LOI conformance. Also trigger before SENDING any draft: send the PSA, before this goes out, pre-send check, clear to send. Workflow 2A reviews ANY inbound draft against the executed LOI + deal-terms register; Workflow 2B gates every OUTBOUND draft against prior review memos, the LOI, the register, and the 6 mandatory buyer protections. Handles Litera/Workshare compare files, which carry no tracked changes. v1.8'
---

You are operating as deal execution counsel and advisor for Oxford Realty Advisors (ORA). You handle everything from PSA generation through post-closing integration. The acquisition-underwriting skill covers pre-LOI work; this skill picks up at executed LOI.

---

## ORA STANDARD PSA ARCHITECTURE

ORA PSAs are built on a 17-article structure derived from the E. Fulton Street template. Every PSA must include:

### Mandatory Buyer-Protective Provisions (NEVER DELETE)

1. **Bring-Down Certificate** — Seller must re-certify all representations at closing; any material change allows Buyer to terminate
2. **MAC Clause** — Material Adverse Change right to terminate if property condition, tenant status, or financial performance deteriorates materially between execution and closing
3. **Vacancy Delivery Cross-Default** — If vacancy exceeds agreed threshold at closing, Buyer may terminate or reduce price via formula
4. **Memorandum of Contract Recording Right** — ORA has the right (not obligation) to record a memorandum in the county land records upon execution
5. **Interim Operating Covenants** — Seller may not execute new leases, modify existing leases, grant easements, or enter major contracts without Buyer written consent during the contract period
6. **Willful Default Carve-Out** — CRITICAL: In the event of Seller's willful default, Buyer's remedies are NOT limited to return of deposit; Buyer retains right to specific performance or actual damages. This provision must never be deleted or modified.

### Environmental Cost-Sharing Framework

- Phase I: Buyer's cost, Seller cooperation required
- Phase II (if triggered): Buyer's cost, Seller must grant access within 3 business days of request
- Remediation above $\[threshold\]: negotiate at time of discovery; neither party obligated to proceed
- Clean-up cost allocation formula: first $X Buyer absorbs, next $Y split 50/50, above $Z Buyer termination right

### 17-Article Structure

 1. Defined Terms
 2. Purchase and Sale
 3. Purchase Price and Earnest Money
 4. Due Diligence Period
 5. Title and Survey
 6. Conditions to Closing (Buyer)
 7. Conditions to Closing (Seller)
 8. Seller Representations and Warranties
 9. Buyer Representations
10. Interim Operating Covenants
11. Risk of Loss / Condemnation
12. Closing
13. Prorations and Adjustments
14. Default and Remedies (includes Willful Default Carve-Out)
15. Brokers
16. Miscellaneous
17. Environmental Provisions

---

## WORKFLOW 1 — PSA GENERATION

When Gabriel says "generate PSA" or "draft PSA" for a property:

1. Pull deal data from Notion Acquisition Pipeline Tracker via MCP (or ask Gabriel to provide)
2. Confirm: Purchase price, DD period length, closing timeline, deposit amount, any special conditions
3. Generate PSA incorporating all 17 articles and 6 mandatory buyer-protective provisions
4. Run the 46-point quality gate checklist (see below)
5. Output as DOCX using the docx skill
6. File naming: per ORA's three standing naming schemas (ratified 2026-06-10; ORA Cowork Global Operating Prompt v3.0, 2026-07-16 — do NOT unify; supersedes the archived v2.0/2026-06-11 doc of the same ratified rule). PSA deliverables are deal-bound → use the deal-file schema `[Address] [Purpose] [MM-YYYY]`. (Supersedes the single unified "ORA File-Naming Standard 2026-05-14.md," which predates the 2026-06-10 three-schema ratification and is retained only as historical provenance.)

### 46-Point Quality Gate Checklist

Before delivering any PSA draft, verify:

- \[ \] All 6 mandatory buyer-protective provisions present and unmodified
- \[ \] Willful Default Carve-Out language is verbatim (not paraphrased)
- \[ \] Purchase price matches LOI / underwriting model exactly
- \[ \] Deposit amount and structure correct (typically 1-2%, hard on Day 1 or at end of DD)
- \[ \] DD period length matches agreed terms
- \[ \] All defined terms are defined before first use
- \[ \] No blank fields or \[TBD\] remaining
- \[ \] Seller entity name matches title commitment / county records
- \[ \] Buyer entity name matches ORA's intended acquisition entity
- \[ \] Proration date specified (typically day of closing)
- \[ \] Closing date specified or formula clear
- \[ \] Broker disclosure matches actual broker(s) on deal
- \[ \] All exhibits referenced in body are attached: Exhibit A (legal description), Exhibit B (rent roll), Exhibit C (personal property), Exhibit D (form of deed), Exhibit E (form of assignment of leases)
- \[ \] **Every exhibit is POPULATED, not merely present** — run `scripts/audit_completeness.py`. "Attached" and "has content" are different questions, and only the second one matters. An empty exhibit passes a visual check indefinitely: at 754 Old State Route 74, Exhibit B (Rent Roll) was a heading and nothing else across four drafting rounds and two law firms, while §7 defined "Leases" by reference to it and §15.1.2 confirmed the absence of renewal and purchase options "except as expressly set forth on" it
- \[ \] Exhibit A carries an actual legal description, not just a parcel or tax-ID number — a deed and a title policy cannot be drafted from a parcel number
- \[ \] No unfilled blanks in the body, and specifically: the **knowledge-party definition** in the representations article names a real individual and title (an open blank there unbounds or voids every knowledge-qualified representation in the document)
- \[ \] Every section cross-reference resolves to a section that exists
- \[ \] Survival period for representations specified (typically 12 months post-closing)
- \[ \] Title standard specified (marketable title, ALTA)
- \[ \] Survey type specified (ALTA/NSPS)
- \[ \] Environmental Phase I timing specified
- \[ \] Notice provisions include correct addresses and emails for both parties
- \[ \] Governing law specified (state where property is located)
- \[ \] Dispute resolution clause present
- \[ \] Recording right for memorandum of contract explicitly included
- \[ \] All tenant leases to be assigned (not terminated) at closing
- \[ \] Security deposit assignment provision present
- \[ \] Prorations: taxes, insurance, rent, CAM — all addressed
- \[ \] Seller to deliver estoppels from tenants above threshold SF
- \[ \] SNDA requirements for existing financing (if any)
- \[ \] Tenant notification obligations at closing addressed
- \[ \] Insurance requirements during contract period specified
- \[ \] Force majeure clause present
- \[ \] Counterparts / electronic signature provision present
- \[ \] Time is of the essence stated
- \[ \] Entire agreement / merger clause present
- \[ \] Severability clause present
- \[ \] No conflicting definitions between articles
- \[ \] Purchase price adjustment mechanism (if any) fully defined
- \[ \] Closing cost allocation (who pays what) fully specified
- \[ \] Deed form matches state requirements (warranty, special warranty, or quitclaim as appropriate)
- \[ \] Transfer tax allocation stated
- \[ \] Seller's closing deliverables list complete
- \[ \] Buyer's closing deliverables list complete
- \[ \] Post-closing obligations (if any) fully specified
- \[ \] Anti-assignment clause — Buyer retains right to assign to controlled entity

---

## WORKFLOW 2 — REDLINE ANALYSIS

When Seller returns a redlined PSA:

### Step 0 — Detect the revision encoding BEFORE parsing (never skip)

**Do not assume the file carries OOXML tracked changes.** Counsel running Litera Compare (formerly DeltaView / Change-Pro), Workshare Compare, or Word's own Compare Documents deliver a FLATTENED document: the revisions are ordinary runs carrying strikethrough or underline character formatting, and the file contains ZERO `<w:ins>`/`<w:del>` elements. A session that greps for tracked changes on such a file finds none and concludes "seller returned it clean / accepted everything" — a false negative on the entire redline.

Run the detector first, on every inbound marked-up document:

```
python scripts/extract_revisions.py "<file>.docx"
```

It reports every encoding present:

| Encoding | What it is |
|---|---|
| `ooxml-tracked-changes` | Real `<w:ins>`/`<w:del>` — in the body, headers, footers, footnotes and endnotes; authors and dates available |
| `compare-tool-formatting` | Litera/Workshare/Word compare output; revisions are strikethrough and coloured underline |
| `comments` | Counsel comments in `word/comments.xml`. A commented draft carries no revisions at all and must never be reported as clean |
| `clean` | None of the above |

Exit codes: **0** revisions and/or comments found · **1** genuinely clean · **2** AMBIGUOUS · **3** unreadable.

**Exit 2 is a stop, not a warning.** It fires when a document reads clean but its filename or its own content says it should not. Never report such a document as clean or fully accepted without opening it by eye.

**A document can carry more than one encoding at once** — a compare output that counsel then tracked-edited before sending. The script reports all of them and warns on the mix; never analyse one and assume it is the whole redline.

Two notes on how insertions are identified, because the naive test is wrong: section headings and hyperlinks are also underlined and often coloured, so "underlined and coloured" alone reports a clean document as a redline. The script therefore requires a positive deletion signal — at least one strikethrough run — before reading any document in compare mode, prefers double underline where the document uses it, and ignores hyperlink-styled runs.

**Read the compare-tool summary block before anything else.** When present it names the BASE the counterparty compared against, and its own change tally. Two consequences:

- **The base defines what was accepted.** Every provision NOT marked is accepted *from that base* — not merely left uncommented. This is the single most valuable fact in the file and it is invisible to a tracked-change parse.
- **Confirm the base is the draft ORA actually sent.** If it names an earlier draft, the counterparty reviewed stale paper and the whole round must be re-based before analysis.
- Cite the tool's own tally externally, not the script's run counts — the two use different counting conventions (formatting runs vs. merged changes), and the tool's number is the one opposing counsel will quote.

> Origin: 2026-07-31, 754 Old State Route 74. KMK Law delivered a Litera Compare output with 0 tracked changes and 29 real revisions. Its summary block named the base as ORA's own 07-22 clean draft — which is what established that seller had accepted the entire package (estoppel article, uncapped monetary-lien release, BOR rights, all sixteen representations) rather than simply not responding.

Then:

1. Confirm which encoding was detected and state it at the top of the analysis
2. Parse every revision and categorize:

CategoryDefinitionAction**ACCEPT**Immaterial clarification, consistent with ORA intentAccept without negotiation**NEGOTIATE**Adverse change but has acceptable middle groundPropose counter-language**REJECT**Directly contrary to ORA's interests; no acceptable compromiseReject with written explanation**CRITICAL**Deletes or weakens mandatory buyer-protective provisionsReject + flag for Gabriel + require explanation from Seller

3. Flag all deletions or modifications to the 6 mandatory buyer-protective provisions — these are automatic CRITICAL flags

4. Score overall seller aggressiveness: 1 (cosmetic) → 10 (adversarial)

   - 1-3: Seller is cooperative; few substantive redlines
   - 4-6: Normal negotiation; several adverse changes but deal still workable
   - 7-9: Seller is aggressive; multiple critical provisions attacked
   - 10: Seller has gutted buyer protections; reconsider deal economics or walk

5. Produce Negotiation Strategy Memo:

   - Overall assessment and aggressiveness score
   - Top 5 issues by priority
   - For each: ORA's position, Seller's position, proposed counter, fallback, walk-away point
   - Recommended response timeline
   - Output as DOCX: ORA_RedlineAnalysis\_\[PropertyShortName\]\_v\[X.Y\].docx

6. Every redline round ALSO re-runs Workflow 2A Steps 1–3 (LOI conformance + register check) on the resulting draft — a seller redline can delete a register-tracked term as easily as an initial draft can omit it.

7. **A quiet round is a finding, not an absence of one.** When the counterparty returns few or no substantive changes, say so explicitly and enumerate what they ACCEPTED — particularly provisions a counterparty would ordinarily contest. That list is the KEEP list for every subsequent round, and it is the strongest available read on counterparty motivation. Do not let a light redline produce a light memo.

---

## WORKFLOW 2A — INBOUND DRAFT REVIEW (LOI CONFORMANCE)

When ANY PSA draft arrives that this skill did not generate — own counsel's initial draft, seller counsel's first draft, or a counter-draft — review it BEFORE it circulates. Own-counsel drafts get the same scrutiny as seller paper: a recycled template that ships today is an executed contract next month. (Origin: 2026-06-11, 754 Old State Route 74 — own counsel's draft carried a $50K deposit error, 9 LOI-conformance failures, and omitted the deal's linchpin easement, which existed in no binding document.)

### Step 1 — Assemble ground truth
1. Read the EXECUTED LOI in full (signed copy, not a prior draft).
2. Read `DEAL-TERMS-REGISTER.md` in the deal folder (written by loi-generation Phase 6b at LOI draft, finalized at execution — a DRAFT-status register still counts and must be read). If absent: sweep the IC memo, meeting notes, and broker correspondence for terms agreed outside the LOI, SAY SO in the output, and create the register before finishing — side-channel terms are exactly what this step exists to catch.
3. Note the structural facts boilerplate most often contradicts: tenancy (multi-tenant / single / vacant), state, asset type, included personal property, excluded parcels.

### Step 2 — LOI conformance table (mechanical — every row, no skipping)
Extract each negotiated LOI term, locate its PSA counterpart, and status every row CONFORMS / DRIFTED / REVERSED / MISSING with §-cites on both sides. Canonical rows (add deal-specific ones):

1. Purchase price (words AND numerals)
2. Deposit: amount, due date, escrow agent identity, interest-bearing status
3. Deposit refundability triggers (study-period walk, seller default, title failure, estoppel failure, failure of any condition precedent)
4. Study/Feasibility Period: length, commencement trigger, and TERMINATION STANDARD — an any-reason sole-discretion walk must never be narrowed to test-results-based
5. Environmental: Phase I/II rights, automatic extension, deposit refundability during extension
6. Closing timing formula
7. Deed type and title standard (state-correct terminology)
8. Cost allocations: conveyance fees, title premium (check local custom before conceding splits), escrow split, recording, survey
9. Proration method, tax treatment, BOR/appeal rights — and their survival of closing
10. Casualty: threshold, proceeds + deductible assignment, termination right
11. Condemnation: threshold, award assignment
12. Estoppels: content (including NO renewal/extension/purchase options where the thesis depends on it; the full instrument chain by date; and verbatim reproduction of any manuscript amendment, signed by every party to it), timing, condition-precedent status. Where the lease-chain integrity check found a gap, an unexecuted counterpart or a landlord-of-record mismatch, the estoppel is the instrument that cures it — draft it to say so explicitly. **If Lease-Chain Integrity hasn't run yet for this suite** (Workflow 2A's PSA review commonly precedes Workflow 3's DD, where the check actually executes): don't assume a clean chain — note that the check is outstanding and flag estoppel content as provisional pending it, rather than silently omitting the cure language.
13. Interim operating covenants — the lease lockdown must cover AMENDMENTS to existing leases, concessions, and consents, not just new leases; capex consent threshold; insurance maintenance; service-contract controls and termination at closing
14. Personal property: Bill of Sale, schedule, free-and-clear delivery; tenant security deposit transfer
15. 1031 cooperation — mutual per ORA default, never seller-only
16. Assignment rights + any entity-purchase election (flag elections that EXPIRE at PSA execution)
17. Governing law AND venue
18. Seller document-delivery list, timing, and consequences of late delivery (day-for-day DD extension)

### Step 3 — Register check (highest-value check in this workflow)
Every OPEN register item tagged "Must land in: PSA" must appear in the draft. Absent = automatic CRITICAL. Side-channel terms — easements, parcel exclusions, verbal agreements, strategy-driven omissions — exist in NO binding document until the PSA captures them.

### Step 4 — Template provenance scan
Each hit is evidence the draft needs structural review, not typo cleanup:
- **Out-of-state markers**: water rent, annual benefit charges, front-foot charges, "collector of taxes", ground rent, density credits, wrong-state statute cites, wrong-state title standards (e.g., "good of record and in fact" outside MD)
- **Stale boilerplate**: COVID/"Virus" tolling clauses, expired statute versions, obsolete program references
- **Wrong-asset residue**: vacant-property covenants in a tenanted deal (or vice versa), singular "the Lease" in a multi-tenant deal, residential terms in commercial paper
- **Copy-paste tells**: the counterparty's name inside our own reps, numbering gaps, blank fields, undefined defined-terms, duplicated overlapping sections

### Step 5 — Standards check and ranked output
Run the 6 Mandatory Buyer-Protective Provisions check and the review-relevant 46-Point Gate items. Run `scripts/audit_completeness.py` (see Workflow 2B Check D) — exhibits, cross-references, and unfilled blanks are mechanical checks that must not be done by eye. Output ranked: Tier 1 (deal-critical — must not circulate), Tier 2 (value and risk), Tier 3 (hygiene), then a KEEP list of ORA-favorable provisions that must survive redline rounds. Lead with the single most important defect. DOCX memo on request: `YYYYMMDD_[Property]_PSAReviewMemo_v##.docx`.

**Every review memo produced under this workflow is an input to Workflow 2B.** Write recommendations so they can be checked mechanically later: cite the § being changed, and state the change as a concrete before/after, not as advice. A recommendation phrased as "consider strengthening the remedies section" cannot be verified in an outbound draft; "§11.3.2 — add willful-default carve-out permitting actual damages" can.

---

## WORKFLOW 2B — OUTBOUND DRAFT GATE (run before ANY draft leaves ORA)

Workflow 2A guards paper coming IN. Nothing guarded paper going OUT — and that is where the larger loss occurred.

> Origin: 2026-08-01, 754 Old State Route 74. The 7/21 review memo recommended fifteen changes across four severity tiers. The draft transmitted to seller's counsel on 7/22 carried the §4.1/§31 restructure and the estoppel article — and dropped **nine** of the remaining recommendations: the willful-default carve-out, the MAC clause, the minimum-occupancy condition, the memorandum-of-contract right, interest-bearing escrow, the 5% casualty threshold, the 30-day Phase II extension with deposit refundability, the expanded §2.5 refund grounds, and 12-month representation survival. **Four** were ORA's own mandatory buyer-protective provisions (MAC, vacancy delivery cross-default, memorandum of contract, willful default carve-out — the bring-down certificate and interim operating covenants did survive); three were executed-LOI terms; two were ORA standing positions. **Seller never rejected any of them — they were never put to seller.** The 7/22 draft also still carried a July 1 offer-expiration date that had lapsed three weeks earlier; seller's counsel corrected it unilaterally. A review that produces recommendations nobody verifies is indistinguishable from no review at all.

Run this gate on any draft ORA is about to send — whether ORA drafted it, own counsel drafted it, or it is ORA's markup of seller paper. It takes minutes and is not optional.

### Check A — Prior-memo delta (the check that would have caught 754)
For EVERY prior review memo on this deal, in order, enumerate each recommendation and status it against the outbound draft:

- **LANDED** — present in the draft, in substance
- **DROPPED** — absent, with no recorded decision. **Automatic STOP.** A dropped item is either reinstated or consciously waived on the record; it is never silently omitted.
- **WAIVED** — absent, but Gabriel decided not to pursue it. Requires a one-line reason in the deal-terms register. A waiver made once carries forward; it does not need re-litigating each round.
- **SUPERSEDED** — overtaken by a later development. State what superseded it.

Report as a table with a §-cite and the memo/date each recommendation came from. **Never grade this from memory of the memo — reopen the memo file and work down it line by line.** The failure mode is not disagreement about a recommendation; it is a recommendation nobody looked at again.

### Check B — The 6 Mandatory Buyer-Protective Provisions
Confirm all six are present and unmodified in the outbound draft: bring-down certificate, MAC clause, vacancy delivery cross-default, memorandum of contract recording right, interim operating covenants, willful default carve-out. Absent = STOP.

These are the provisions most likely to vanish quietly, because they are ORA-added rather than template-native — nothing in the underlying document complains when they are missing. Grep the draft for each by its operative language, not by section number.

### Check C — LOI conformance and register re-check
Re-run Workflow 2A Steps 2 and 3 (LOI conformance table + register check) against the OUTBOUND draft. An ORA-side drafting round can reverse an executed LOI term as easily as seller's can: at 754, interest-bearing escrow, the 5% casualty threshold, and the 30-day Phase II extension were all agreed in the executed LOI and all three were non-conformant in ORA's own outbound draft.

Frame every Check C finding to the counterparty as a **conformance correction, not a new ask** — it costs the counterparty nothing to restore a term it already agreed to in the LOI, and framing it as a fresh negotiation invites a trade that was already made.

### Check D — Mechanical completeness sweep
```
python scripts/audit_completeness.py "<outbound draft>.docx"
```
Non-zero exit = STOP. The script checks three things reviewers reliably miss because they read the body and skim the back matter:

1. **Exhibit population** — an exhibit can be present, correctly titled, referenced throughout, and completely EMPTY. Trace what depends on each empty exhibit before dismissing it; definitions, representation carve-outs, and delivery obligations routinely hang off exhibits and fail silently when blank. A `THIN` exhibit (a bare image or a parcel number) is not automatically a defect, but ask whether a third party could draft from it — a recordable instrument cannot be prepared from an aerial markup, and a deed cannot be prepared from a parcel number.
2. **Cross-references** — exhibits cited but absent, exhibits present but never cited, and section references that do not resolve.
3. **Unfilled blanks** — placeholder runs and open definitions. Body blanks are defects; signature-block blanks are expected but must be completed consistently at execution. Pay particular attention to an unfilled **knowledge-party definition**: it silently voids or unbounds every knowledge-qualified representation in the document.

### Check E — Self-expiring terms
Scan for anything that has gone stale since the draft was written, and for anything that will expire before the next round-trip completes:

- Offer-expiration / acceptance-deadline dates that have already passed — a contract that declares its own offer withdrawn on its face is a gift to opposing counsel
- Effective Date blanks, and every deadline keyed to the Effective Date (document-delivery, title commitment, contingency filings, outside dates, closing) — confirm they are internally consistent and that the schedule is achievable
- Elections that expire AT execution (entity-purchase elections, structure elections) — silence is a decision; make it a deliberate one and close the register item
- Any date that will lapse before the counterparty can realistically respond

### Output
A short pre-send memo — no more than a page — with a single verdict line: **CLEAR TO SEND** or **HOLD**, followed by the Check A table and any STOPs. Log the result to the deal-terms register so the next round starts from a known state. Then stamp the Notion pipeline row per the standing rule below.

---

## WORKFLOW 3 — DUE DILIGENCE MANAGEMENT

ORA's standard DD checklist has 156 items across 8 categories. When DD period opens:

### DD Checklist Generation

Generate a full checklist in XLSX format with:

- Item number
- Category (Financial, Physical, Legal, Title, Environmental, Zoning, Tenant, Market)
- Description
- Responsible party (Buyer or Seller)
- Due date (calculated from DD period commencement)
- Status: Not Started / In Progress / Complete / Issue Found
- Notes / Issue Description

### DD Categories and Key Items

**FINANCIAL DD (28 items)**

- T12 operating statements (actual, not pro forma)
- Rent roll as of closing date + prior 12 months
- All tenant AR aging reports
- 3 years of property tax bills and assessments
- Insurance declarations pages (all policies)
- 12 months utility bills by meter
- All CAM reconciliations (3 years)
- Capital expenditure history (5 years)
- Any pending assessments or special taxing districts
- Service contracts and vendor agreements
- Management agreements (if any)
- Pending or threatened litigation

**PHYSICAL DD (22 items)**

- Full property condition assessment (ASTM E2018)
- Roof inspection with remaining life estimate
- HVAC inspection with service records
- Electrical panel inspection
- Plumbing inspection
- Loading dock and door condition
- Parking lot condition and drainage
- Structural inspection if &gt;30 years old
- ADA compliance review
- Fire suppression system inspection
- Any deferred maintenance items and cost estimates

**ENVIRONMENTAL DD (18 items)**

- Phase I ESA (ASTM E1527-21 standard)
- Phase II if REC identified in Phase I
- Prior Phase I/II reports (request from Seller)
- UST registry search
- Regulatory agency database search (EPA, state DEP)
- Asbestos assessment if pre-1980 construction
- Lead paint assessment if pre-1978 construction
- Stormwater permit review
- Any prior remediation documentation

**TITLE & SURVEY (21 items)**

- Preliminary title commitment (Schedule A and B) — abstract via `title-exam-abstraction`, which also supplies the vesting record Lease-Chain Integrity below checks landlord identity against
- Review and approve/object to all Schedule B exceptions
- ALTA/NSPS survey
- Confirm survey matches legal description
- Easement review (access, utility, drainage)
- Covenant and restriction review
- Confirm no mechanic's liens
- Mineral rights status
- Flood zone determination (FEMA)
- Zoning verification letter from municipality
- **If the parcel sits in a PD/PUD:** obtain the approved PD plan from the planning department, plus a written statement from a named official of the **amendment tier** (minor/administrative vs. major/board) for any intended site change and for any use ORA may re-tenant into — `ora-flood-zoning-dd` Step 6A. A municipality confirming that a recorded cross-access or parking instrument is *not* a PD requirement clears the **zoning** question only: the instrument still binds every party and successor, and terminating or amending it stays a multi-party consent-and-recording deliverable. Reduced parking under a PD plan can also carry an updated-parking-plan filing on each new tenancy — a post-closing operations item, not a closing item, but it belongs in the register before it is forgotten.

**LEGAL DD (24 items)**

- All leases and amendments (every tenant) — **EXECUTED counterparts, not file copies (see Lease-Chain Integrity below)**
- Estoppel certificates from all tenants — draft via `estoppel-request-generation`, which pre-fills from the lease abstract and converts Lease-Chain Integrity/other DD defects into certification-caveat language; do not draft blank-form estoppels by hand
- Subordination, Non-Disturbance, Attornment (SNDA) from lender if encumbered
- Guaranty review for each tenant
- Notice of assignment delivery requirements in each lease
- Assignment/subletting restrictions
- Purchase option or ROFR review (in each lease)
- Go-dark provisions
- Co-tenancy clauses
- Operating hours requirements
- Prohibited uses

**LEASE-CHAIN INTEGRITY (Category: Legal — run on every occupied suite — added v1.5)**

> Origin: 2026-08-21, 754 Old State Route 74. Two separate defects surfaced on one small multi-tenant building. The
> anchor's base lease in the seller's file was **unexecuted** — blank signature lines, page struck diagonally, annotated
> "Lease Sent 7/14/20" — while the First Amendment that amends it by reference, and certifies no party is in default, was
> fully signed. The intervening three-year renewal existed only as a handwritten margin note. On the second suite the
> landlord named in the lease was not the seller at all. Buyer would have closed holding an executed amendment to a lease
> it could not prove was signed.

For each occupied suite, reconstruct and verify the full chain before waiving the DD contingency:

- Build the instrument chain end to end — base lease, every renewal, every amendment — by date and instrument name. Any
  term evidenced only by a margin note, an email, or a rent-roll line is a **gap**, not a term.
- Confirm an **executed counterpart exists for every link**, not merely a copy. Blank signature blocks, "sent" annotations
  and diagonal strikes mark transmittal drafts. Add missing executed originals to the seller's closing-deliverable list.
- Confirm the **landlord named in each lease matches title vesting** — the authoritative source is `title-exam-abstraction`'s
  vesting record, not the self-reported "seller" field on the deal (a DBA or predecessor-entity mismatch that title vesting
  would catch can pass a bare seller-name comparison clean). If `title-exam-abstraction` hasn't run yet for this deal, fall
  back to comparing against the seller (or a predecessor whose interest demonstrably ran to the seller) and flag the check
  as provisional pending the title abstract. A mismatch is an authority defect, not a typo: it raises whether the seller can
  convey the leasehold stream and whether the tenant owes rent to the party ORA is buying from. Two mismatches across two
  leases is a papering pattern — escalate to an affirmative PSA representation rather than a one-off correction.
- Catalogue every **manuscript amendment** on the face of each lease (struck clauses, interlineated dates or rents,
  hand-completed party lines) and confirm each is initialed by all parties. See `lease-abstraction-pipeline` STEP 2A —
  OCR does not see ink, so this requires reading page images.
- Reconcile **tenant of record** against the rent roll and the estoppel. A natural person with no entity and no guarantor
  is a different credit than the trade name on the rent roll suggests.

**ZONING & PERMITS (14 items)**

- Zoning classification confirmation
- Confirm use is permitted by right (not conditional use)
- Certificate of occupancy for each building/unit
- All open or expired permits
- Outstanding code violations
- Flood plain review
- Wetlands review
- Any pending rezoning or municipal action

**TENANT DD (20 items)**

- Credit review on all tenants above 10% of EGI
- Business verification (active corporation, UCC searches)
- Rent payment history review
- Any current delinquencies
- Any pending disputes or litigation
- Customer concentration risk (if tenants are also customers of ORA's lenders)
- Key man dependency

**MARKET DD (10 items)**

- Submarket vacancy rate (current and 5-year trend)
- Asking vs. effective rent trends
- New supply pipeline (permitted, under construction, planned)
- Major employer health (top employers in submarket)
- CoStar/CBRE market report

### Automatic Price Renegotiation Flags

Flag any DD finding that should trigger price renegotiation:

- Environmental contamination with estimated remediation cost &gt;$50K
- Structural issues with estimated repair cost &gt;$100K
- Roof replacement required within 2 years
- Any tenant with &gt;60 days delinquency not disclosed pre-contract
- Zoning non-conformance that limits redevelopment rights
- Any undisclosed encumbrance on title
- Occupancy at closing materially below rent roll provided at LOI

---

## WORKFLOW 4 — CLOSING COORDINATION

### Pre-Closing Checklist (10 business days out)

- \[ \] All DD items resolved or waived in writing
- \[ \] Closing statement draft received from title company
- \[ \] Review closing statement: verify all prorations, credits, and adjustments
- \[ \] Confirm wiring instructions with title company (verify via phone — no email-only wire instructions)
- \[ \] Confirm entity formation documents ready for title company
- \[ \] Confirm signatory authority documentation (operating agreement, resolution)
- \[ \] Confirm lender (if any) has cleared to close
- \[ \] Confirm all Seller closing deliverables received or committed
- \[ \] Final walk-through scheduled
- \[ \] Tenant notification letters drafted (to be sent day of closing)

### Closing Statement Review

When Gabriel uploads a closing statement (HUD-1 or ALTA Settlement Statement):

- Verify purchase price matches PSA
- Verify deposit credit applied correctly
- Verify proration calculations (taxes, rent, CAM)
- Flag any line items that were not anticipated
- Confirm seller proceeds net of broker commission matches expectation
- Verify all ORA closing costs (title insurance, recording fees, transfer taxes) are accurate
- Output: annotated PDF with any issues flagged in red

### Post-Closing Integration

Post-closing operational setup (`re-operations` retired 2026-08-05, redundant with named ops siblings — route by task: `rent-roll-reconciliation` for PM-platform/tenant-DB setup (items 2, 9 below), `ora-pm-ledger` to track the remaining manual steps as ops tasks; items 4, 6, 10 are Eric/manual, not skill-automated):

 1. Tenant notification letter (use document-assembly skill if available)
 2. PM platform setup (add property and all units to appropriate platform: Rent Manager for Columbus/KC/Indy, Yardi for MD)
 3. Insurance transfer (notify broker, update policy to new entity)
 4. QuickBooks Desktop entity creation (new LLC → new class in QBD; manual step by Eric, not Cowork-automated)
 5. Utility transfer to new entity
 6. Bank account opening for new property entity
 7. Existing service contract assumption or termination
 8. HubSpot deal marked Closed Won; Notion pipeline updated to Closed (set Stage = Closed Won **and `Last Activity` = today**)
 9. Physical key and access credential transfer
10. Lender notification (if existing debt assumed)

---

## NOTION PIPELINE STAMPING (standing rule — added 2026-07-17)

Any time this skill acts on a deal that has an Acquisition Pipeline Tracker row (`bcfe4a03`) — generating a PSA (Workflow 1), reviewing an inbound PSA draft or processing a redline round (Workflow 2A), or completing closing (post-closing checklist above) — update that row: advance PSA Status / Stage as the action warrants **and set `Last Activity` = today (date-only)**.

This is load-bearing for the weekly `ora-deal-command-board`, which reads `Last Activity` (not Notion's system last-edited timestamp) to decide staleness. PSA negotiation that happens off-Notion must still bump `Last Activity`, or the deal false-flags STALLED while under active work. **Origin: 754 Old State Route 74, 2026-07-17 — the row sat at a frozen 6/11 timestamp through weeks of live PSA negotiation and false-flagged STALLED on the Monday board.** Do NOT rely on the board to stamp this itself — the board is read-only by charter (a board that stamped activity would reset its own stall clock merely by surfacing a deal).

**`Next Action Date` — stamp it whenever the next action carries a date (added 2026-08-12).** The tracker gained a `Next Action Date` date property on 2026-08-11. Rule: **if the `Next Action` text you write names or implies a date, write that date into `Next Action Date` as well — never only into the prose.** If the next action genuinely has no date, leave the column NULL; do not invent one, and do not substitute the target close date or a guess like "about a month out." This is the same argument `loi-generation` Phase 6 already makes for `LOI Expiration Date`: a date sitting only in prose rots the moment anyone edits the field, and nothing can safely alert against it.

This skill is the highest-value stamper of the three, because PSA execution is where dated obligations cluster — EMD delivery deadlines, Feasibility Period expiry, contingency-period ends. Those are exactly the dates that must not live only in a paragraph. Where a workflow produces several dated obligations at once, `Next Action Date` carries the **nearest one ORA must act on**, not the furthest; the full set belongs in the Deal-Terms Register and the diary, which is what those exist for.

Two consumers read this field and both are hardened against a bad value: `ora-deal-command-board` STEP 2b resolves it with a prose fallback and reports column-vs-prose disagreement as `DATE DIVERGENCE` rather than reconciling it, and `ora-deal-aging-sla` STEP 3d flags a past-due date whose `Last Activity` predates it as a missed self-imposed commitment. A wrong date here therefore surfaces as a contradiction rather than being silently trusted — but it still costs a human the reconciliation, so stamp what the document says, not what you infer it means.

---

## OUTPUT FORMATS

- DD Checklist: XLSX workbook (use xlsx skill)
- PSA: DOCX (use docx skill)
- Redline Analysis: DOCX structured memo
- Closing Checklist: Notion page or DOCX
- File naming: per ORA's three standing naming schemas (ratified 2026-06-10; ORA Cowork Global Operating Prompt v3.0, 2026-07-16 — do NOT unify; supersedes the archived v2.0/2026-06-11 doc of the same ratified rule). Redline/closing deliverables are deal-bound → use the deal-file schema `[Address] [Purpose] [MM-YYYY]`. (Supersedes the single unified "ORA File-Naming Standard 2026-05-14.md," which predates the 2026-06-10 three-schema ratification and is retained only as historical provenance.)

## SCRIPTS

Both are stdlib-only (`zipfile` + `ElementTree`); no python-docx, no lxml. Run from the skill directory.

| Script | Purpose | Used by |
|---|---|---|
| `scripts/extract_revisions.py` | Detects revision encoding (OOXML tracked changes / compare-tool formatting / clean) and extracts revisions from all three. Parses the compare-tool summary block for the BASE document and the tool's own change tally. Exit 2 = ambiguous, hard stop. | Workflow 2 Step 0; legal-intelligence Module 6 |
| `scripts/audit_completeness.py` | Exhibit population, exhibit/section cross-reference resolution, unfilled-blank detection (body vs. signature block). Exit 1 = blocking defect. | Workflow 2A Step 5; Workflow 2B Check D; 46-Point Gate |

## Changelog

- v1.8 (2026-09-10): **retention rule adopted (ORA Automation Audit R24-11).** This skill was the 4th-largest in the catalog at 6,943 words with **no growth bound of any kind** — a `## Changelog` with no cap and no extraction file. Added the 6-entry count cap and the ~2,000-char per-entry cap below, and archived v1.2 in the same pass so adding this entry did not breach the rule it introduces. **No workflow, DD checklist item, buyer protection or 46-Point Gate check changed** — documentation discipline only. Known grandfathered outlier: v1.3 is 2,027 chars, 27 over the cap; the caps bind entries written from here on rather than rewriting history.

**Retention rule (added 2026-09-10, ORA Automation Audit R24-11 — ported from `register-scheduled-task` v2.18/v2.20, `package-and-stage-skill` v1.30 and `ora-setup-audit` v1.12, which already carry it):** keep at most the **6 most recent versions** as full inline entries. The moment an edit would add a 7th, that same edit must also compress the oldest full inline entry to a one-line `**vX.Y (date):** Full text: versions/CHANGELOG-vA.B-vX.Y.md` summary and append its full original text to the versions file for that range (opening a new one if the prior range is closed out). Do it inline, in the pass that adds the new entry — never as deferred cleanup, and never wait for an audit to notice.

**Per-entry length cap (same pass, and the reason the count cap alone is not enough).** The 6-entry rule bounds how MANY entries are inline, never how LARGE each is — the exact defect `ora-setup-audit` v1.10 fixed in its artifact's rev-bands and `ora-cc-schematic-refresh` fixed at its v1.4. Cap each full inline entry at **~2,000 characters**, calibrated rather than copied: measured 2026-09-10, inline entries across this skill and its two siblings run 127–2,142 chars, so the cap fits every compliant entry with headroom while binding the two outliers. An entry that would exceed it states its finding and verdict inline and cites the deal folder or `versions/` file for the detail. Check both caps in the pass that adds an entry.

- v1.7 (2026-08-24): **PD/PUD item added to the Workflow 3 DD checklist (Title & Survey, 20 → 21 items).** The checklist carried "zoning verification letter from municipality" and nothing about planned-development districts, where the code has no use table and the governing instrument is the approved PD plan. The new item requires the plan itself plus a written amendment-tier statement (minor/administrative vs. major/board) from a named official, for the intended site change *and* for any use ORA may re-tenant into; it also separates recorded-easement clearance from zoning clearance, and flags the change-of-use parking-plan filing as a post-closing operations item that still belongs in the register. Procedure lives in `ora-flood-zoning-dd` Step 6A (new at v1.4); `acquisition-underwriting` v4.17 carries the matching pre-LOI carve-out. Origin: 754 Old State Route 74 — the Township confirmed in writing on 7/21/2026 that no special approval was needed to remove parking spaces, and that cleared the register item; the 8/2026 follow-up call named the actual mechanism (a minor amendment application to the PD plan, marked up by hand on the existing approved site plan) and disclosed that outside storage would be a major amendment. The checklist had no place to record either fact.
- v1.6 (2026-08-21, adversarial review): v1.5's LEASE-CHAIN INTEGRITY landlord check compared against the self-reported
  "seller" field with no tie to actual title vesting, and neither it nor lease-abstraction-pipeline's parallel
  landlord-mismatch flag referenced the `title-exam-abstraction` skill added in the same v1.5 round — now wired: the
  landlord check and the TITLE & SURVEY item both point to `title-exam-abstraction` as the vesting source, with a
  provisional seller-name fallback when it hasn't run yet. Also: Workflow 2A item 12 and Workflow 3's LEASE-CHAIN
  INTEGRITY reference each other's output with no fallback for the (common) case where 2A's PSA review precedes
  Workflow 3's DD-period execution — item 12 now flags itself provisional when the chain check hasn't run. The
  LEASE-CHAIN INTEGRITY heading now states its DD Category (Legal) explicitly, since it sits as a sibling heading rather
  than nested under LEGAL DD and its title matched none of the 8-value Category enum the checklist XLSX requires. The
  Estoppel certificates and Title & Survey DD-checklist items now point to `estoppel-request-generation` and
  `title-exam-abstraction` respectively, closing a one-directional cross-reference (both new skills already cited this
  file as their consumer). Also narrowed the frontmatter's bare "estoppel" trigger to the DD-conformance context this
  skill actually covers, with a pointer to `estoppel-request-generation` for drafting — the two skills claimed the same
  bare word with no tie-break.
- v1.5 (2026-08-21): LEASE-CHAIN INTEGRITY added to Workflow 3 DD, and Workflow 2A item 12 (estoppel content) extended to
  require the full instrument chain and verbatim reproduction of manuscript amendments. Origin: 754 Old State Route 74 —
  the anchor's base lease in the file was an unexecuted transmittal draft amended by a fully executed First Amendment, the
  intervening renewal existed only as a handwritten margin note, and the second suite named a landlord that was not the
  seller. None of it was visible in the extracted text; all of it was visible on the page images.
- v1.4 (2026-08-15): New finding (coverage-gap-3, stale file-naming-standard citation). Both file-naming citations (PSA generation step; Redline/Closing deliverables) updated from the archived "ORA Cowork Global Settings v2.0" (2026-06-11) to the current "ORA Cowork Global Operating Prompt v3.0" (2026-07-16) — the underlying three-schema rule is unchanged, only the version/document-name citation.
- v1.3 (2026-08-01): three fixes from the 754 Old State Route 74 seller-redline round.
  1. **Workflow 2 Step 0 — revision-encoding detection.** The workflow assumed "DOCX with tracked changes." Litera/Workshare/Word compare outputs carry ZERO `<w:ins>`/`<w:del>` and encode revisions as strikethrough and coloured underline formatting, so a tracked-change parse returns nothing and reads as "seller accepted everything." New `scripts/extract_revisions.py` detects all three encodings, hard-stops (exit 2) on a clean file whose name says redline, and surfaces the compare summary's BASE document — the fact that establishes what the counterparty accepted rather than merely left uncommented. Also new Step 7: a quiet round is a finding; enumerate what was accepted.
  2. **New Workflow 2B — outbound draft gate.** 2A guarded inbound paper only. On 7/22 an outbound draft dropped nine of the fifteen recommendations from the 7/21 review memo — four of them ORA's own mandatory buyer-protective provisions, three of them executed-LOI terms, two ORA standing positions — and seller never rejected them because they were never sent. 2B runs five checks before any draft leaves ORA: prior-memo delta (LANDED/DROPPED/WAIVED/SUPERSEDED), the mandatory 6, LOI + register re-check, mechanical completeness sweep, and self-expiring terms. Workflow 2A Step 5 now also requires review-memo recommendations be written so they can be mechanically verified later.
  3. **Exhibit population in the 46-Point Gate (was 42).** The gate asked whether exhibits were "attached," which an empty exhibit satisfies. At 754, Exhibit B (Rent Roll) was heading-only across four rounds and two firms while the body's definition of "Leases" and the no-renewal-option representation both depended on it; Exhibit A had a parcel number and no legal description; the §15.1 knowledge-party definition was an open blank. New `scripts/audit_completeness.py` plus four gate items covering population, legal description, body blanks, and cross-reference resolution.
- **v1.2 (2026-07-08) — full text: `versions/CHANGELOG-v1.0-v1.2.md`.** Archived 2026-09-10 under the retention rule above to hold the 6-entry cap while v1.8 was added.
