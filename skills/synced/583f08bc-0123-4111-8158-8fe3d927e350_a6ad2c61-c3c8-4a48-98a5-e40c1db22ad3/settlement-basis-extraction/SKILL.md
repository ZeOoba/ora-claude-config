---
name: settlement-basis-extraction
description: Extract acquisition/disposition data from HUD-1/ALTA settlement statements and build a capitalizable-basis register for Oxford Realty Advisors property entities. Use when the user says: import settlement statements, build the basis register, extract closing costs, OCR the settlement PDFs, capitalize closing charges, reconcile a settlement to Schedule L, or points at a folder of HUD-1/ALTA settlement statements, deeds, or closing packages. Also trigger when a new acquisition or disposition closes and the settlement package needs to be worked into the entity's basis and the portfolio's EXCHANGE_1031 tracking. Produces a workbook (README, ENTITY_MASTER, PROPERTY_PL, BALANCE_SHEET, DEPR_COSTSEG, BASIS_REGISTER, CHARGE_DETAIL, EXCHANGE_1031, PAYMENTS, EXCEPTIONS, SOURCE_INDEX) with every figure transcribed verbatim and blank cells where a digit can't be read with confidence. v1.1
---

# Settlement-Basis Extraction (ORA) — v1.1

## When to use this

Any time a settlement statement (HUD-1 or ALTA Combined) needs to become a
line item in an entity's basis, and every time an acquisition or disposition
closes. This is the same procedure that built the 2026-08-17 Tax & Basis
Register from 32 settlement PDFs across 27 transactions -- it is written so
that work is repeatable rather than re-invented per closing.

Do not use this for lease abstraction, insurance declarations, or tax
returns themselves -- those have their own skills
(`lease-abstraction-pipeline`, `insurance-renewal-review`). This skill's
scope is strictly: settlement statement in, capitalizable basis + charge
detail + 1031 chain entry out.

## Method

### 1. Triage every document for a text layer before doing anything else

A HUD-1/ALTA PDF is either a native digital document (title company software
output -- has a real text layer) or a scan (has none). Do not assume; check
each file. If extracting text returns empty or near-empty content, the
document is image-only and needs OCR before anything downstream can read it
programmatically.

- Digitally-generated ALTA statements (recent closings, e.g. a 2023+ Stewart
  Title combined statement) usually have a text layer.
- Older HUD-1s, faxed pages, and anything with visible fold marks / skew in
  a preview are almost always scans.
- Historically, roughly 70% of a settlement corpus comes back scan-only
  (23 of 32 in the 2026-08-17 corpus). Budget for OCR being the majority
  case, not the exception.

### 2. OCR every image-only document at 300 dpi, and keep the twin next to the original

Run OCR (300 dpi minimum -- lower resolutions lose small print like transfer
tax splits and per-diem prorations) and save the searchable output ALONGSIDE
the original in the same folder, not in a separate output tree. Suggested
naming: `<original filename> (OCR).pdf`. This is a one-time cost per
document -- once a settlement has a searchable twin, every future skill run
(this one, tax-appeal, disposition-analysis) benefits without re-OCRing.

Where a digit cannot be read with confidence after OCR, leave the cell
**blank** in the register. Never guess a number to fill a cell. Log the
illegible field in the EXCEPTIONS tab with the file name and the specific
line item.

Two known illegible-field patterns worth watching for specifically:
- Contract sales price (HUD-1 line 101) sometimes fails OCR when the rest of
  the page is legible. If line 101 is unreadable, the contract price can
  often be corroborated from the transfer-tax and commission lines (both are
  usually a fixed percentage of price) -- derive it that way and flag the
  cell as **derived, not transcribed** rather than leaving it blank.
- An entire settlement table (all of Section L, or the whole HUD-1 second
  page) can fail as a block, typically from a bad fax generation or a
  photocopy-of-a-photocopy. When that happens, don't partially transcribe
  around it -- flag the whole document as "OCR failed, request clean copy"
  in EXCEPTIONS and move on. Partial transcription of a garbled table is
  worse than no transcription.

### 3. Transcribe verbatim, then cross-foot before touching anything else

Transcribe every settlement charge line as it appears -- do not net, round,
or reclassify during transcription. Cross-foot each settlement against its
own printed control totals (Borrower's total due = Seller's total due =
Section L total, or the ALTA combined-statement subtotals/totals block).
A settlement that doesn't foot to zero against its own printed totals has a
transcription error somewhere in that document -- find and fix it before
moving to the next document, not at the end of the batch.

### 4. Tag every closing charge capitalizable / not

Every line in Section L (HUD-1) or the charges block (ALTA) gets a
capitalizable/not-capitalizable tag. Use `references/charge-capitalization-taxonomy.md`
for the standard tagging rules (Reg. 1.263(a)-2, transfer taxes, prorations,
loan costs vs. acquisition costs). This produces the CHARGE_DETAIL tab --
one row per closing-charge line, tagged, for every settlement in the batch.
The 2026-08-17 register carried 442 such lines across 27 transactions; do
not summarize charges into a single "closing costs" number, the per-line
detail is what lets a future preparer or IC memo pull exactly which costs
were capitalized and why.

### 5. Flag land/improvement allocation gaps as you go, don't wait for the tax return

If a settlement's entire debit total lands in one basis bucket with no
land/improvement split (common when the settlement statement itself doesn't
allocate), flag it immediately in EXCEPTIONS -- "zero land basis, needs
assessor ratio or appraisal split" -- rather than letting it silently
capitalize 100% to depreciable improvements. This has been a recurring
finding (1100 Rarig, and 401 Sunburst's Dorchester County SDAT record showing
Land Value $0) -- treat a missing split as a standing exception category, not
a one-off.

### 6. Update the EXCHANGE_1031 tab and the 1031 chain register together, at every closing

If the settlement is a leg of a like-kind exchange (QI named on the HUD-1 /
ALTA, or the closing falls within 45/180 days of a known relinquishment),
add a row to EXCHANGE_1031 AND to the standing 1031 Exchange Chain Register
(see the companion register -- ask the user if they don't have a current
copy) in the same session. Record: identification-notice parcels, this
leg's settlement date and parcel(s), and whether this leg is on the Form
8824 (leave blank/PENDING if the 8824 hasn't been filed yet -- don't wait
for the return to create the row). The point of updating both at closing
time, rather than retroactively, is that a parcel-count mismatch between the
identification notice and the settlement is visible immediately, not two tax
seasons later -- this is exactly how the McGregor/Northwood gap in the
2026-08-17 register went undetected for two years.

### 7. Build/refresh the workbook

Standard tab structure (create tabs that don't yet exist; append to ones
that do -- do not create a parallel workbook per batch):

- `README` -- what was imported this pass, source paths, coverage, OCR
  method note, gaps to close.
- `ENTITY_MASTER` -- one row per LLC/entity.
- `TAX_SUMMARY` -- federal + state filing summary by entity-year.
- `PROPERTY_PL` -- Form 8825 line-by-line by property.
- `BALANCE_SHEET` -- Schedule L + M-2.
- `DEPR_COSTSEG` -- depreciation and cost segregation position by property.
- `BASIS_REGISTER` -- one row per property, rolling basis.
- `CHARGE_DETAIL` -- one row per settlement closing-charge line, tagged
  capitalizable/not (see step 4).
- `EXCHANGE_1031` -- one row per exchange leg (see step 6).
- `PAYMENTS` -- coupons/estimated payments if in scope for this batch.
- `EXCEPTIONS` -- every illegible field, cross-foot failure, and land/basis
  gap, with file name and specific line item.
- `SOURCE_INDEX` -- file name -> tab/row(s) it feeds, so a reviewer can trace
  any number back to its settlement statement.

Every check column in the workbook should be a live formula, not a
hardcoded value -- the point is that the workbook re-verifies itself when a
row is edited later. Build per the `xlsx` skill's conventions (recalc
before shipping; no hardcoded results where a formula is possible).

### 8. Close with a "six items that change a number" style summary, not a raw diff dump

After the workbook is built, write a short list (the 2026-08-17 register
used six) of the specific findings that would change a number a preparer or
IC memo currently relies on -- zero land basis, a parcel missing from an
8824, a related-party exposure, a Section 481(a) catch-up with no Form 3115,
a title-chain gap, an error in a previously-issued memo. This is the
highest-value output of the whole procedure; the workbook is the evidence,
this list is the action item.

## Output

- The refreshed workbook (xlsx), named per the session-output convention:
  `YYYY-MM-DD_TaxAndBasisRegister_Workbook_vXX.xlsx` in the deal's
  `/outputs/` subfolder.
- Searchable OCR twins left alongside every original that needed them.
- An updated 1031 Exchange Chain Register (see companion register skill/
  workbook) if any leg closed this batch.
- A short "items that change a number" list in the response, not just in
  the workbook.

## Do not

- Do not guess a digit to fill a blank cell. Blank + EXCEPTIONS row beats a
  plausible-looking wrong number.
- Do not summarize CHARGE_DETAIL into a single closing-costs figure -- keep
  the per-line detail.
- Do not wait until the tax return is being prepared to reconcile an
  exchange leg against its identification notice -- do it at closing.
- Do not treat a land-value-zero settlement as resolved by capitalizing
  100% to improvements -- that is the exception, not the default.

## Changelog

- v1.1 (2026-08-24): Description trimmed to restore headroom (was 1019/1024,
  headroom 5 -- close-out work-order item 4, the tightest of the six flagged
  skills). Dropped the "LLC" gloss and the dated version-history parenthetical
  ("first cut, generalized from..."); the full workbook-tab list and every
  trigger phrase kept intact. `description_budget.py` now reports headroom 123.
