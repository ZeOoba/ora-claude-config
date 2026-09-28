---
name: debt-management
description: "Oxford Realty Advisors debt management, capital-markets, and payoff-statement skill. Use when the user mentions: refinance, refi, term sheet, lender selection, loan negotiation, DSCR, debt yield, LTV, debt covenant, lender call, prepayment, defeasance, swap, rate cap, hedge, balloon, maturity, loan reserves, lender package, lender comparison, capital stack, recap, mezzanine, preferred equity. ALSO the SOLE path for PAYOFF STATEMENTS in either direction — trigger on: payoff statement, payoff letter, payoff figure, payoff good through, per diem, payoff demand, title company payoff request, authorization to obtain/release payoff, our borrower is refinancing, seller-financed note payoff, satisfaction or release of a note we hold, or auditing a payoff quoted TO us. Also trigger when the user uploads a term sheet, commitment letter, lender proposal, amortization schedule, or a title-company payoff authorization form. Strategic hold/refi/1031/sell decisions route to disposition-analysis first. v1.4"
---

# Debt Management

Manage and optimize ORA's debt across the loan lifecycle: origination, monitoring, covenant compliance, refinance evaluation, lender relationships — and payoff statements on notes ORA **holds** as well as notes ORA **owes**.

## Scope

All debt instruments held or owed by ORA entities: agency, life-co, bank, CMBS, bridge, mezzanine, preferred equity, and seller-financed purchase-money notes where an ORA SPV is the Lender. Excludes personal debt (Gabriel/Eric — see personal-portfolio).

## Triggers

Refinance evaluation, term-sheet redline, lender call prep, covenant test, DSCR/LTV/debt-yield calculation, hedge evaluation, balloon planning, lender RFP, capital-stack restructuring, **payoff statement issuance or audit**.

## Inputs

- Notion debt schedule (linked from Operations Hub `32b6ecd8`)
- Loan documents in SharePoint `/Loans External/[entity]/` and cross-referenced property folders
- The `loans-external-register` Cowork artifact (register of record for tracked terms — read-only input, never edit from a summary)
- Term sheets, amortization schedules, payoff authorizations uploaded by user
- Capital-markets benchmarks (10Y Treasury, SOFR, BBB CMBS spreads, life-co spreads)

---

# PAYOFF STATEMENTS

## Step 0 — Establish direction before anything else

Two different jobs share the word "payoff." Get this wrong and every downstream number is backwards.

- **ORA as LENDER (issuing).** An ORA entity holds the note; the borrower is refinancing or selling and their title company wants a payoff. ORA produces the instrument. This is the less common case but it does occur — ORA takes back seller financing on dispositions.
- **ORA as BORROWER (receiving).** ORA is refinancing; the lender issues a payoff and ORA audits it.

Do not infer direction from the property being "ours." On a disposition with seller financing, the property is gone and the note is the asset. Verify against the executed Note's own Lender/Borrower recitals and the Notion PSA/deal record — not from memory.

## Workflow A — Issuing a payoff statement (ORA as Lender)

### A1. Establish the paid-through date from evidence, never from the schedule's due dates

Read the **Date Paid** column of the amortization schedule, not the due-date column. A missing Date Paid means *unverified*, not *unpaid* — and a populated one may sit well after the due date.

Confirm you have the controlling copy of the schedule. Hash/mtime it against the copy in the deal folder; a workbook that has been updated since your last read will change the answer. If two copies disagree, stop and ask which governs.

### A2. Principal

Unpaid principal = the balance **after the last installment actually received and applied**. Nothing else.

### A3. Accrued interest

- Read the accrual convention out of the Note itself. A 30/360 note accrues 30 days per month regardless of the calendar; do not substitute actual/365.
- Per diem = principal × annual rate ÷ 360 (on a 30/360 note).
- Day count from paid-through date to payoff date on the same convention: `(m2−m1)×30 + (d2−d1)`.
- Cross-check the per diem against the schedule's own next-month interest ÷ 30. They must agree.

### A4. Principal does NOT accrue between installment dates

A payoff is a lump-sum discharge, not another scheduled installment. Do **not** prorate the next month's principal reduction into the payoff. Between due dates the balance is static and only interest accrues. Amortization is an event that happens when a payment is applied, and the payoff itself is what extinguishes the remaining principal.

### A5. The double-count trap — the single most dangerous error in this workflow

**Never add an unpaid installment on top of un-reduced principal plus full accrued interest.**

An installment is *composed of* interest plus principal reduction. If you carry the undiminished principal AND charge interest for the whole period, the installment is already fully captured. Adding it again overstates the payoff by exactly one installment.

Wrong: `principal (un-reduced) + missed installment + full-period interest`
Right: `principal (un-reduced) + full-period interest`

### A6. Mandatory consistency cross-check

Compute total cash to Lender both ways:

- Path A — borrower pays the next installment separately: `reduced payoff + that installment`
- Path B — it rolls into the payoff: `larger payoff`

These must agree to within day-count rounding (single-digit dollars). A spread of one installment means a double-count in A5. Run this every time; it is cheap and it catches the error.

### A7. Quote conservatively

Where an installment comes due between the statement date and closing, quote on the basis that it is **NOT** separately remitted. A lender must never quote below what it is owed, and a borrower closing shortly after a due date may reasonably skip the payment expecting the payoff to absorb it.

State the **reduced alternate figure on the face of the letter**, and direct the settlement agent to confirm with Lender which applies not fewer than two business days before disbursement.

### A8. Late charges are an election, not an automatic

Compute assessable charges from the Note's **actual** grace period — read the section, do not trust a register or summary. Present the history to Gabriel (which installments cleared grace, the per-charge amount, the aggregate) and let him decide.

If waived: frame it in the letter as a one-time accommodation **limited to installments already received**, with rights under the late-charge section expressly reserved as to any installment falling due on or after the letter date. Silence reads as a blanket waiver.

### A9. Foot the displayed column

The stated total must equal the sum of the **rounded line items as displayed**, not a rounded sum of unrounded inputs. Settlement agents add the column; a one-cent disagreement is a credibility problem on an instrument whose whole job is arithmetic.

### A10. Date it with today's actual date

Derive the date from the current date, never from file timestamps or an assumed schedule. A misdated payoff can assert as future an installment that has already come due.

### A11. Required contents

- Superseding clause voiding all prior statements, where one was previously issued
- Borrower, Lender, property, Note date and original principal, security instrument
- Itemized table: principal, accrued interest (with day count, rate, convention, per diem), late charges, recording/release fee, total
- "Good through" date and per diem thereafter
- Void-and-recalculate trigger if a further installment comes due before funding
- Wiring instructions under separate cover, with an explicit warning against relying on emailed wires without verbal callback verification
- Satisfaction/release mechanics and the statement that the lien **remains of record until the satisfaction is recorded**
- Signature block for the Lender entity's authorized signatory, matching how the Note was executed

## Workflow B — Auditing a payoff issued TO ORA (ORA as Borrower)

Run the same math in reverse against the lender's figure. Check:

- Paid-through date against ORA's own payment records
- Day-count convention and per diem against the Note
- Whether a prepayment penalty / yield maintenance / defeasance charge actually applies at this date, and whether the open window has been reached
- Fees for legitimacy: recording and release are real; "processing," "demand," and "statement" fees frequently are not and are often waivable
- Whether any late charges asserted are within the Note's grace terms
- That principal has not been carried at a stale balance

Report variances with the arithmetic shown; do not accept a lender's total on its face.

## Payoff QC gate — all must pass before presenting

1. Direction (lender vs borrower) verified against the executed Note's recitals
2. Paid-through date sourced from actual payment evidence
3. Controlling copy of the amortization schedule confirmed
4. Accrual convention read from the Note, not assumed
5. Per diem cross-checks against the schedule's own interest line
6. No principal prorated between installment dates (A4)
7. No installment double-counted (A5)
8. Path A / Path B consistency cross-check run and agreeing (A6)
9. Alternate figure stated on the letter's face where an installment falls before closing
10. Late-charge election explicitly decided by Gabriel and correctly framed
11. Displayed column foots to the stated total
12. Letter dated to the actual current date
13. Standard ORA 16-point QC gate on the DOCX

## Payoff outputs

- DOCX on the **Lender entity's** letterhead (not the generic firm name) per ORA Institutional Style Guide v1.0+
- File naming: `YYYY-MM-DD_[Property]_PayoffStatement_v##.docx`
- PDF must carry an extractable text layer (Microsoft Print to PDF prohibited)
- Render and visually verify before presenting — payoff tables split across page breaks orphan the total from its components
- After issuance, update the `loans-external-register` artifact's receivable card (payoff figure, good-through date, per diem, sources)

---

## Standard Workflows (non-payoff)

### Refinance Evaluation
1. Pull current loan terms from Notion debt schedule.
2. Calculate breakeven refi rate including prepay penalty, defeasance, points, legal.
3. Build NPV comparison: hold-current vs. refi-now vs. refi-at-maturity.
4. Survey market: 3+ lender quotes. Use HubSpot lender-relationship database for outreach.
5. Output: refi-decision memo (DOCX, ORA Style) with NPV table, sensitivity to rate moves, and recommended action.

### Term-Sheet Redline
1. Compare against ORA Standard Lender Provisions library (Notion Knowledge Base).
2. Flag any deviation in: prepayment rights, debt-yield/DSCR triggers, recourse scope, reserves, transfer/assumption, springing recourse, environmental indemnity.
3. Produce redline DOCX with comments using legal-intelligence skill conventions.

### Lender Call Prep
1. Pull last 4 quarters of operating data for the property/portfolio.
2. Build covenant compliance summary (DSCR, debt yield, LTV).
3. Surface any operational anomalies (occupancy drops, major capex, tenant departures).
4. Produce 2-page lender brief (DOCX, ORA Style).

### Covenant Test
1. Pull tested covenants from loan documents.
2. Compute current value vs. covenant threshold.
3. Flag any covenant within 10% of breach.
4. Output: compliance memo (DOCX) and Notion update.

## Outputs

- DOCX deliverables follow ORA Institutional Style Guide v1.0+
- File naming: `YYYYMMDD_[Property-or-Topic]_[DocType]_[v##].docx`
- Mirror to SharePoint `/Loans/Analysis/`
- Notion update to debt schedule and Operations Hub

## Boundaries

- This skill DRAFTS lender and title-company communications. It does not SEND. Outbound to a lender, borrower, or settlement agent requires Gabriel's explicit in-turn approval per Hard Invariant 1.
- Payoff statements are counterparty-facing instruments — draft only, never transmitted from this skill.
- Hedge execution (swaps, caps) is never automated — drafts only.
- All redlines are produced as comments/tracked changes; final acceptance is human.
- Loan terms carried in the `loans-external-register` artifact are governor-adjacent (DSCR/LTV inputs). Corrections flow from the executed instrument, never from a lender email or summary (Hard Invariant 4).

## Dependencies

- legal-intelligence skill (for redline mechanics)
- portfolio-reporting skill (for NOI inputs)
- communication-intelligence skill (for lender/title-company email drafts)
- xlsx skill (for sensitivity models)
- docx skill (for memo and payoff-letter deliverables)
- `ora-loan-terms-reconciliation` scheduled task (monthly register-vs-instrument drift check)

## Changelog

- v1.4 (2026-09-07): ORA Automation Audit R23-9-adjacent — a full pairwise trigger sweep found "refinance" shared with disposition-analysis (strategic hold/refi/1031/sell decision vs. this skill's execution). Added a one-clause deferral: strategic refi-vs-other-exit calls route to disposition-analysis first. Reciprocal clause added there. No procedure, QC gate, or trigger vocabulary otherwise changed.
- v1.3 (2026-08-17): Added the PAYOFF STATEMENTS section — Step 0 direction check, Workflow A (issuing, ORA as Lender), Workflow B (auditing a payoff received), and a 13-point payoff QC gate. Encodes four errors made while hand-building the 5600 Sunnyside / Restoration Church payoff three times: (1) an installment double-counted on top of un-reduced principal plus full accrued interest, overstating by $16,713.65; (2) a total rounded from unrounded inputs instead of footing the displayed column, off by $0.01; (3) a letter dated from file timestamps rather than the current date, which falsely asserted a past-due installment as not yet due; (4) a register-sourced late-charge grace period (15 days) used instead of the executed Note's actual term (5 days). Adds the A6 Path A/Path B consistency cross-check that catches the double-count class arithmetically. Scope widened to seller-financed notes where an ORA SPV is Lender.
- v1.2 (2026-07-08): Migrated into `ora-skills` (git-pinned, `package-and-stage-skill`-covered) from the `ora-operations-extensions` plugin. That plugin has no `installed_plugins.json` entry and no local commit pinning — it is Cowork/Connector-platform-managed, not Code-managed — so its runtime-cache copy had zero protection against a silent re-sync revert. This repo copy is now the source of truth. Once installed via Save-skill, remove the old `ora-operations-extensions:debt-management` plugin skill (Settings → Capabilities) to avoid duplicate-skill triggering.
- v1.1 (2026-07-08): Removed stale `ora-debt-maturity-snapshot` / `ora-lender-covenant-tracker` scheduled-task references (root cause of the 2026-07-08 fleet resurrection loop) — fixed directly on the plugin's runtime-cache and Claude_Workspace source-pack copies, prior to this migration.
