---
name: listing-agreement-qc
description: "Pre-execution QC gate for BROKER LISTING AGREEMENTS on counterparty paper where Oxford Realty Advisors is the Owner. Use when the user says: QC this listing agreement, check this listing before I sign, review the brokerage agreement, listing agreement review, compare listing agreements, exclusive right to sell, exclusive right to lease, commission schedule, broker engagement, or uploads a DOCX/PDF that is a listing agreement. Run before ANY listing is signed or countersigned. Scans 25 systemic defects (dual gross-price definitions, missing excluded-prospect and affiliate carve-outs, automatic holdover, unconditioned tail, lease language in a sale-only instrument, blanket dual agency, missing lender-consent and Ohio agency-disclosure hooks) with BLOCK/HIGH/MED/LOW severity. Carries ORA's sixteen ratified standing listing positions. Distinct from lease-form-qc (ORA's own lease paper) and legal-intelligence. v1.3"
---

# Listing Agreement QC — counterparty brokerage paper

Pre-execution gate for broker listing agreements where ORA is the Owner. Run
**before** signature or countersignature. This audits the *brokerage engagement*
— for ORA's own lease paper use `lease-form-qc`; for PSAs and leases from a
counterparty use `legal-intelligence`; for the deal itself use
`acquisition-underwriting` or `disposition-analysis`.

## Why this exists

An audit on 2026-08-17 compared the unexecuted **2000-2002 Zettler Rd** sale
listing (C&W, 8.13.26) against the executed **3875-3883 E Livingston Ave**
sale-and-lease listing (C&W, 4.21.26). Sentence-level diff result: **every
sale-side clause was verbatim identical.** No ORA-negotiated protection had been
dropped and no commission economics had moved.

The finding was that the *identity* was the problem. Six defects present in the
Livingston form had been carried forward into a second engagement without
re-examination, and a further six clauses of lease machinery had been left inside
an instrument whose operative grant is sale-only and whose Schedule of
Commissions contains no lease rate table.

Root cause: **no gate existed between "the broker sent the same form" and
"Gabriel signed it."** Diffing a new listing against the last executed one
returns "no changes" and reads as clearance. It is not — it only proves the
defects are stable. This skill converts a diff into an absolute standard.

Scanner benchmarks (v1.0, 25 checks):

| Document | Failures | Notes |
|---|---|---|
| Zettler 8.13.26 (sale only, unexecuted) | **18 of 25** | + L10/L11 lease-residue, L20 entity name, L22 numbering, L24 (header only — L24 also scans the footer as of v1.2, but this file's footer is clean C&W boilerplate) |
| Livingston 4.20.26 (sale + lease, executed) | **15 of 25** | No lease-residue (has a lease schedule); no L23 on this file. Corrected in v1.2 — see Changelog for the file-identification and re-verification history |
| A fully remediated ORA listing | **0 of 25** | target state |

Anything above 0 on a form ORA has already marked up means a defect survived the markup.

## The sixteen ratified standing positions

`references/standing-positions.md` is the canon. Ratified by Gabriel Goldberg
2026-08-17 out of the Zettler/Livingston comparison. Apply by default; do not
re-ask unless the deal presents a specific reason to depart. Each scanner check
cites the position it enforces (SP-1 … SP-16).

The four that cost real money if omitted, in priority order when a markup must
be shortened:

1. **SP-2 — Excluded Prospects exhibit is mandatory.** No exclusive listing is
   signed without one. Build it with `scripts/build_excluded_prospects.py`.
2. **SP-3 — Affiliate and involuntary transfers are carved out.** Entity
   contributions, estate planning, foreclosure/deed in lieu, and condemnation
   never trigger a fee.
3. **SP-5 — Mutual 30-day termination after day 90** of the primary term.
4. **SP-1 — One definition of gross sale price**, and it is the computation
   paragraph.

## How to run

### Step 1 — Automated scan

```bash
python3 scripts/listing_qc.py <agreement.docx|pdf|txt> [more ...] [--allow-tokens] [--no-ocr] [--json]
```

Reads `word/document.xml` directly for DOCX (so it sees headers, footers,
tracked changes, comments, and the numbering layer), `pdftotext -layout` for
PDF with an OCR fallback (poppler + tesseract) when the text layer is too
thin, raw for text. A document that still can't be read to at least 150 words
reports `RESULT UNREADABLE` and exits 2 — it is never scored as "clean," which
is the failure mode this scanner used to have on a scanned, no-text-layer PDF.
Prints one line per FAIL with severity and the standing position it enforces.
Exit codes: 0 clean, 1 one or more failures, 2 usage/extraction/UNREADABLE
error.

The scanner auto-detects **scope** (`SALE ONLY` / `SALE + LEASE`) and suppresses
the lease-residue checks (L10, L11) when a lease commission schedule is actually
present. It also enforces a **token gate**: any unfilled `[TOKEN]` in a file
whose name lacks `_TEMPLATE` is a BLOCK failure. Pass `--allow-tokens` for a
working draft.

### Step 2 — Check revision encoding before reporting "no changes"

Same trap as `lease-form-qc`. A Litera / Workshare / Word-compare output carries
**zero** `<w:ins>`/`<w:del>` elements and encodes revisions as strikethrough plus
coloured underline. The scanner reports the detected encoding — state it at the
top of every report. A clean DOCX with no tracked changes means the markups are
baked in and the file carries **no redline record**; the only way to know what
moved off the broker's base form is a compare against the archived base template
(see Step 5).

### Step 3 — Diff against the last executed listing on the same broker's form

```bash
python3 scripts/listing_qc.py new.docx last_executed.pdf --json > /tmp/qc.json
```

Read both reports side by side. Three outcomes, and the middle one is the trap:

- **New failures** the prior agreement did not have → a protection was dropped.
  Report as a regression.
- **Identical failure sets** → the form is stable. This is **not** clearance.
  It means the same defects are about to be signed a second time. Report every
  BLOCK regardless of how many times it has previously been accepted.
- **Fewer failures** → the broker improved the form, or the scope changed.
  Confirm which.

### Step 4 — Verify the property and the party against source-of-record

Never take the recitals on faith. For an Ohio parcel:

```bash
curl -s -G "https://gis.franklincountyohio.gov/hosting/rest/services/ParcelFeatures/Parcel_Features/MapServer/0/query" \
  --data-urlencode "where=PARCELID='010-015487'" \
  --data-urlencode "outFields=PARCELID,OWNERNME1,SITEADDRESS,BLDGAREA,ACRES,CLASSDSCRP,SALEDATE,SALEPRICE" \
  --data-urlencode "returnGeometry=false" --data-urlencode "f=json"
```

Other counties: see `ora-millage-lookup` and `ora-flood-zoning-dd` for the
endpoint registry. Confirm three things:

1. **Owner of record** matches the Owner named in the preamble, character for
   character. The county string settles which of two internal spellings is
   correct (Zettler 2026-08-17: county reads `FAIRGROUND VILLAGE CENTER LLC`,
   no comma — the signature block's comma was the error, not the preamble).
2. **Site address and building area** match the described Property. A hyphenated
   address range against a single parcel ID is L21 and must be resolved before
   signature, not after.
3. **Encumbrances.** Query Notion for the property's loan register. A listing on
   a financed asset needs the SP-11 lender-consent language (Zettler sits in the
   Fairground Village Center LLC borrower group — Symetra loan, two Columbus
   properties as collateral).

### Step 5 — Build the Excluded Prospects exhibit (SP-2)

```bash
python3 scripts/build_excluded_prospects.py --property "2000-2002 Zettler Rd" \
    --tenants tenants.json --out "Exhibit A - Excluded Prospects.docx"
```

Source the tenant list from the Notion Tenant Database
(`collection://b12f4cfd-a995-4755-8341-6435ae8173b4`). Query on `Property
Address` **and on the adjacent-portfolio addresses**, not just the subject —
ORA's own tenants next door are the highest-probability unsourced buyers and are
exactly who the exclusion is for.

```sql
SELECT "Tenant Name", "Tenant Legal Entity Name", "Suite / Unit", "SF",
       "Lease Status", "date:Lease Expiration:start"
FROM "collection://b12f4cfd-a995-4755-8341-6435ae8173b4"
WHERE "Property Address" LIKE '%<street>%'
```

Filter out rows whose `Tenant Name` begins with `⛔ ARCHIVED` — those are
superseded records, not live tenants. Include tenants whose status is `Notice
Given` or recently `Expired`: an outgoing tenant at the subject building is a
purchase candidate, not a former one.

### Step 6 — Deal-folder close-out

Run `references/deal-folder-checklist.md`. Nine artifacts, three of which are
routinely missing (agency disclosure form, broker's base template, countersigned
PDF). Do not mark the listing complete until the countersigned copy is in the
folder — an Adobe Sign audit report evidences only the party who signed *through
Adobe*, and a broker who applies a signature image outside the transaction leaves
no audit trail (confirmed on Livingston 2026-05-04).

### Step 7 — Report

Order findings BLOCK → HIGH → MED → LOW. For each: the defect, the failure
scenario in dollars where it can be quantified, and the exact replacement
language from `references/standing-positions.md`. Close with an explicit
**execute / do not execute** recommendation. Deliver as DOCX per the ORA Style
Guide with the 16-point QC Gate applied.

## Scope boundaries

| Situation | Skill |
|---|---|
| Broker listing agreement, ORA as Owner | **this skill** |
| ORA's own lease form going to a tenant | `lease-form-qc` |
| Counterparty lease, PSA, loan doc | `legal-intelligence` |
| PSA against an executed LOI | `deal-execution` / `psa-reconciliation` |
| Whether to sell at all, and at what price | `disposition-analysis` |
| Drafting the broker engagement email | `communication-intelligence` |

## Hard rule

This skill **reviews**. It never sends. A markup going back to the broker is an
outbound communication to an external counterparty and requires Gabriel's
explicit in-turn confirmation (standing invariant 1).

## Changelog

- **v1.3 (2026-08-24)** — Description trimmed to restore headroom (was
  988/1024, headroom 36 -- close-out work-order item 4). Dropped the named
  broker-firm examples parenthetical and the ratification-date parenthetical;
  no trigger vocabulary or named-defect clause removed.
  `description_budget.py` now reports headroom 101.

- **v1.2 (2026-08-17)** — Two fixes to the v1.1 retrofit, plus the regression
  test coverage neither shipped with.
  1. **L24 was silently blind to footer content** (commit `7e88341`). The v1.1
     retrofit narrowed `meta["headers"]` to headers only and routed footer
     text to a separate `meta["footer"]` field gated behind
     `extract(..., want_footer=True)` — `pma_qc.py` and `lease_qc.py` both
     opt in via their own `run_cli(...)` call, but `listing_qc.py`'s never
     did, so `meta["footer"]` had been permanently empty since v1.1 and L24
     scanned headers only. Same false-negative shape as lease-form-qc's T1
     footer-blindness fix earlier in this branch (`900ad05`). Fixed by
     passing `want_footer=True` and scanning `headers + footer` in L24.
  2. **Missing `ocr_absence_note`** (commit `81c15d8`). `pma_qc.py` and
     `lease_qc.py` both pass a tool-specific `ocr_absence_note` to
     `run_cli(...)` flagging which findings are absence-based and therefore
     provisional under lossy OCR text; `listing_qc.py` never did. Added,
     covering the 13 absence-based checks (BLOCK: L2, L3, L5, L7, L8, L11;
     HIGH: L12, L13, L14, L15, L16, L17, L19).
  3. **Regression test coverage.** Neither fix above shipped with a committed
     test — against this branch's own precedent, `900ad05`'s equivalent
     lease-form-qc T1 fix shipped a purpose-built fixture in the same commit.
     Worse: no existing suite (across all three `ora_doc_qc.py` consumers)
     exercised `listing_qc.py`'s real `run_cli(..., want_footer=True)` call
     site through a subprocess — deleting `want_footer=True` from that call
     today would have left every prior test green. Added
     `tests/test_listing_qc.py` (5 tests, real-subprocess CLI invocations,
     matching `lease-form-qc/tests/test_lease_qc.py`'s house style): footer-only
     residue fires L24 (the regression this file exists to catch — red-checked
     by temporarily reverting `want_footer=True`: 2 of 5 tests fail and the
     other 3 stay green, confirming those 3 don't accidentally depend on the
     footer wiring), header-only residue still fires L24 (regression coverage
     for the pre-existing behavior, not just the new half), and a realistic
     non-empty clean header/footer does not false-positive (guards the "quote
     window" false-positive concern separately raised in review).
  4. **Benchmark re-verification.** Re-ran both real benchmark DOCX
     (read-only, from Gabriel's OneDrive `Business\` deal folders). Zettler
     8.13.26: unchanged at **18/25** — L24 fires from header text only
     ("A PROPOSAL FOR ... listing agreement for sale"); the footer is C&W
     page-numbering boilerplate with no residue, so the footer-scan addition
     doesn't move this file's count. Livingston: the correct C&W-authored
     benchmark file is `Listing Agreement for Sale and Lease Clean 4.20.2026
     - 3875 E Livingston-.docx` (the file-identification correction v1.1
     already flagged) — re-verified at **15/25**, also unchanged by the
     footer fix (same reason: clean C&W boilerplate footer). This reconciles
     the "14/25 vs 15/25" discrepancy v1.1 left open; the benchmark table
     above is corrected to 15/25 accordingly. **Caution for anyone citing
     commit `7e88341`'s own message:** it reports "still 18/25 and 7/25" for
     Zettler/Livingston, but the 7/25 figure was measured against `3883
     Livingston, LLC\Brokerage Agreement -- 3875-3883 E Livingston.docx` — a
     Colliers-form brokerage agreement unrelated to the C&W listing this
     skill's benchmark table documents, not the Livingston listing agreement
     the table cites. That commit's own conclusion (no regression) still
     holds for the file it actually checked, but 7/25 is not the number to
     cite for the Livingston benchmark row — 15/25 is.
- **v1.1 (2026-08-17)** — Retrofit onto the shared `tools/ora_doc_qc.py`
  extraction/report module (also used by `pma-qc`). Closes a real false-clean
  bug: the old bespoke `extract()` had no OCR fallback and no minimum-words
  floor, so a scanned counterparty PDF with no text layer extracted to an
  empty (or near-empty) string; several of this scanner's checks fire on
  *absence* of protective language, so a near-empty extraction didn't even
  read as a flat "0 of 25 clean" — it silently produced a plausible-looking
  partial report (verified: 4 of 25 FAILED on a synthetic 6-word fixture,
  exit code 1, no signal the document was never really read). Now: any
  document extracting to under 150 words reports `RESULT UNREADABLE` and
  exits 2. Regression fixture at `tests/build_no_text_layer_fixture.py` /
  `tests/no_text_layer_fixture.pdf`. No check-body changes at this revision —
  all 25 checks' logic unchanged here (L24's body was corrected later, in
  v1.2 below; this claim was accurate for v1.1 itself but is superseded and
  should not be read as still true of the file as it stands today). One
  behavior change: the printed/JSON `SCOPE` line is dropped
  (nothing downstream parsed it — grep-verified) — scope detection still
  drives L10/L11 internally. Re-benchmarked against both v1.0 documents,
  unchanged: 18/25 (Zettler 8.13.26). Livingston re-check found 15/25 against
  the actual C&W-authored `... Clean 4.20.2026 ...` file (this table's "14/25"
  and "4.21.26" predate a file-identification correction and are carried here
  unedited pending reconciliation — not introduced by this retrofit).
- **v1.0 (2026-08-17)** — Initial. 25 checks, 16 ratified standing positions,
  excluded-prospects builder, deal-folder checklist, C&W form defect register.
  Benchmarked at 18/25 (Zettler 8.13.26) and 14/25 (Livingston 4.20.26).
