---
name: title-exam-abstraction
description: 'Abstract a title exam, title commitment, preliminary report, or recorded-instrument set for Oxford Realty Advisors and turn every encumbrance into a tracked deal-terms-register item. Use when the user mentions: title exam, title commitment, title report, prelim, Schedule B, Schedule B-II exceptions, title exceptions, encumbrance review, cross-collateral, cross-default, assignment of rents, mortgage payoff, easement of record, deed restriction, chain of title, vesting, legal description, mortgage location survey, ALTA survey, or uploads a title exam / commitment / recorded instrument. Also trigger when a deal folder contains title work older than 90 days. Distinguishes what a document ESTABLISHES from what it merely reports, separates boundary surveys from mortgage location surveys, and routes every finding to a closing deliverable, a survey order, or a register item. Never substitutes for counsel. v1.1'
---

# Title Exam Abstraction — Oxford Realty Advisors

Turns title work into a decision. Three outputs, every time: **what is established**, **what must be
cleared before closing**, and **what remains unknown and who is ordering it**.

This skill abstracts and routes. It does not opine on marketability or insurability — that is counsel's
call, and every output says so.

---

## OPERATING PRINCIPLES

1. **A title exam reports; a commitment insures.** An examiner's abstract is one professional's read of
   the record. Only a commitment binds an underwriter. Never let an exam stand in for a commitment in a
   closing decision, and always say which one is in hand.
2. **Age is a defect.** Title work older than 90 days is stale; older than a year it is a lead, not a
   finding. State the age in the first line of every output.
3. **OCR-derived recording references are directional.** Title exams are frequently handwritten on a form.
   Book/page numbers, dollar figures and dates read by OCR must be re-pulled from the current commitment
   before they enter any deal document. Say so explicitly rather than presenting them as verified.
4. **Every exception routes somewhere.** No exception is ever abstracted and left. Each one exits this
   skill as a closing deliverable, a survey order, a register item, an accepted title exception, or a
   question for counsel — named, with an owner.
5. **Read the instrument, not the summary line.** A one-line "cross-easement agreement" entry can be a
   multi-party instrument that the seller cannot terminate alone. Pull and read anything that constrains
   use, access, parking or transfer.

---

## STEP 1 — CLASSIFY THE DOCUMENT SET

Before abstracting, name what is actually in hand. These are not interchangeable:

| Document | What it establishes | What it does NOT |
|---|---|---|
| Title exam / abstract | One examiner's read of the record chain | Does not insure; no underwriter is bound |
| Title commitment (Sch. A + B) | The underwriter's terms to insure, and its required cures | Not a survey; Schedule B-II survives closing unless cured |
| Owner's policy (prior) | What a prior owner was insured for, as of its date | Says nothing about the intervening period |
| Recorded instrument | The actual bargain — controls over any summary of it | May be superseded by a later instrument |
| **ALTA/NSPS survey** | Boundary, improvements, encroachments, plotted easements | — |
| **Mortgage location survey** | **Almost nothing for a buyer** — see below | Not a boundary survey; no title research |

**The mortgage-location-survey trap (Ohio: OAC 4733-38 vs 4733-37).** A mortgage location survey is
prepared for a lender's closing, states on its face that no title or abstract research was performed, and
that boundary and easement information came from client-furnished deed material and "may or may not be
complete." It cannot support a PSA legal description, a square-footage reconciliation, an easement
exhibit, or any site-plan decision. When one is the only survey in a deal folder, the correct output is
an **ALTA/NSPS survey order**, and the memo should say plainly that the file currently has no survey for
buyer purposes. Check the certification block and the governing administrative-code citation — the
distinction is stated there, not in the title.

Also record, for each document: preparer, date, client (a survey prepared for a lender names that lender —
useful evidence of the encumbrance history), and the parcel/auditor number.

---

## STEP 2 — SCANNED-DOCUMENT DISCIPLINE

Title exams are commonly handwritten on a printed form and scanned. Where the document has no text layer:

1. Render page images (`pdftoppm -r 300 -png`) and build a contact sheet before reading OCR output.
2. Read the exam form's ruled sections visually — Vesting, Mortgages, Easements, Restrictions, Taxes,
   Assessments, Liens/Judgments. Handwriting in these sections is the finding.
3. Recorded instruments attached behind the form usually OCR well; the form itself usually does not.
4. Mark every figure and recording reference taken from OCR as `[OCR — verify]`.

This mirrors `lease-abstraction-pipeline` STEP 2A. Same failure mode, same discipline.

---

## STEP 3 — ABSTRACT (field set)

**A. Vesting and chain**
Record owner exactly as titled, including entity type and state of formation · vesting deed (instrument,
date) · whether the vested name matches the PSA seller **exactly** — a DBA, a predecessor partnership, or
a similar-but-different entity is a finding, not a formality · any gap or unrecorded conveyance in the chain.

**B. Monetary encumbrances**
For each: instrument type (mortgage, deed of trust, assignment of rents, UCC, judgment, mechanic's lien) ·
lender/holder · recording reference · original face amount · date · whether an assignment of rents or
leases accompanies it.

**C. Cross-collateral and cross-default — treat as its own category**
Where the parcel secures obligations beyond its own note, this is the single finding most able to move a
closing date, and it is routinely buried in a "liens" line. Capture: every cross-collateral, cross-default
and blanket-lien instrument · which other properties or obligations are implicated · and, critically, that
**payoff of the note is not the same as release of the parcel from the package.** Both are separate
closing deliverables and both need written confirmation from the lender.

**D. Easements and use restrictions**
Grantee, purpose, width, recording reference, and whether it is plottable · separate *utility* easements
(usually accepted) from *access, parking, cross-easement and reciprocal* instruments (usually operative
constraints on the business plan) · for any multi-party instrument, identify **every party and every
successor**, because the seller alone cannot terminate or amend it · covenants, PD/PUD conditions, and
whether any recorded instrument is a zoning requirement (ask the municipality in writing; do not infer).

**E. Taxes and assessments**
Current installments, paid/unpaid status, special assessments, CAUV or abatement status, and any pending
reassessment. Cross-reference the pro-forma reassessed figure from `acquisition-underwriting`.

**F. Legal description**
Reproduce it. Flag any conflict with the PSA exhibit, the auditor record, or the survey — and note that
only an ALTA survey resolves an acreage or SF conflict.

---

## STEP 4 — ROUTE EVERY FINDING

Each abstracted item exits as exactly one of:

| Route | When | Lands in |
|---|---|---|
| **Seller closing deliverable** | Payoff, release, satisfaction, termination or amendment is required | PSA deliverable list + condition precedent |
| **Survey order** | The item cannot be located, plotted or measured from the record | ALTA/NSPS scope letter |
| **Register item** | A term must be tracked across PSA drafts to closing | `DEAL-TERMS-REGISTER.md` — assign the next number |
| **Accepted exception** | ORA will take title subject to it | Title objection letter: expressly listed as accepted |
| **Counsel question** | Insurability, marketability, or multi-party consent mechanics | Named counsel, with the question written out |

Write the register rows in the register's own format so they can be pasted in directly, and never
renumber existing rows.

**REGISTER WRITE-BACK VERIFICATION — mandatory before any register item is reported as added (v1.1,
2026-08-24).** Drafting a register row and landing it on disk are two different events, and only the
second one counts. Before this run's output, a memo, or a status summary says register items were
added:

1. **Re-read `DEAL-TERMS-REGISTER.md` from disk** after writing — not from what you composed, not from
   the tool result that reported success.
2. **Confirm each new number is present**, and quote the highest number now in the file.
3. **Reconcile against the numbers you intended.** If the file's highest number is lower than the rows
   you drafted, the write did not land: say so plainly and either write it now or hand off the exact
   rows, in the register's format, to whoever can.
4. **Never assign a number that a prior run may already have claimed but not written.** If any earlier
   record (a memo, a prior session's summary, project memory) says rows `N…M` were added and they are
   not in the file, treat `N…M` as **RESERVED**, start at `M+1`, and state the reservation in the
   register's own update log so the next writer inherits it. Reserving numbers is always cheaper than
   a collision, because existing rows are never renumbered.

Origin (754 Old State Route 74): a 2026-08-21 review recorded in project memory that it "added Items
16–22." The register on disk ran 1–15 and had last been written a month earlier. The claim survived
four weeks and two downstream sessions because nothing ever re-read the file, and the next writer
would have silently reused those numbers. A one-line read-back would have caught it the same day.

---

## STEP 5 — OUTPUT

A DOCX memo on ORA letterhead (ORA Institutional Style Guide v1.0+; 16-point QC gate before presenting),
naming `[DocType]_[Property]_[MMDDYYYY]` per the deal-file schema, containing:

1. **What is in hand and how old it is** — one line, first.
2. **Established** — vesting, parcel, legal description, restrictions of record.
3. **Must be cleared** — ranked by ability to move the closing date, cross-collateral first.
4. **Unknown** — with the order that would resolve each, and who is placing it.
5. **Register items** — ready to paste.
6. **Counsel questions** — written out.

Then state the two standing caveats: OCR-derived references are directional pending the commitment, and
nothing here is a legal opinion on marketability or insurability.

---

## CROSS-SKILL INTEGRATION

- `deal-execution` — Workflow 3 DD (Title & Survey category) consumes this output; findings become closing deliverables there.
- `loi-generation` / `deal-execution` — the `DEAL-TERMS-REGISTER.md` is the destination for tracked items.
- `lease-abstraction-pipeline` — landlord-of-record on each lease must match vesting here; a mismatch is a finding in both.
- `estoppel-request-generation` — SNDA and subordination requirements discovered here drive estoppel and SNDA scope.
- `ora-flood-zoning-dd` — zoning verification and flood determination; PD/PUD conditions found here route there.
- `acquisition-underwriting` — tax and assessment findings feed the carrying-cost build.

## Changelog

- v1.1 (2026-08-24): Added **REGISTER WRITE-BACK VERIFICATION** to STEP 4. STEP 4 told the reader to assign the next register number and never renumber, and stopped there — it never required confirming that the rows actually reached the file. Origin (754 Old State Route 74): a 2026-08-21 review recorded in project memory that it "added Items 16–22"; the register on disk ran 1–15 and had last been written on 2026-07-21. The claim survived four weeks and two downstream sessions unchallenged, and the next writer would have silently reused those numbers against rows that may yet be pasted in. The step now requires a post-write re-read from disk, quoting the highest number now present, an explicit reconciliation against the rows drafted, and — the part that makes the failure recoverable rather than merely visible — a **RESERVED** range recorded in the register's own update log whenever an earlier record claims rows the file does not contain, so the next writer starts above them instead of colliding. Also bumps the frontmatter version token, which sat at v1.0 with no changelog entry to move.
- v1.0 (2026-08-21): initial. Built after the 754 Old State Route 74 file review surfaced an open mortgage, a recorded assignment of rents, and a cross-collateral / cross-default package against the parcel — none of which appeared in the deal-terms register or the DD tracker after four months — and after the folder's only survey turned out to be a 2016 mortgage location survey that expressly disclaims boundary and title research while being relied on as if it were a boundary survey.
