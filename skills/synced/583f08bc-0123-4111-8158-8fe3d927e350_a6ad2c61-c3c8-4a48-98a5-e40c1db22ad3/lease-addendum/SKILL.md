---
name: lease-addendum
description: "ORA lease amendment/addendum drafting skill -- SOLE path for amending, extending, or modifying a lease already in effect. Use when the user says: draft addendum, lease addendum, amend/amendment, extend the lease, rent change, tenant substitution, name change, novation, add/remove tenant, premises change, add a unit, guaranty exhibit, or uploads a draft addendum to an ORA lease. NOT new leases (masterlease-jurisdiction-rebase + lease-form-qc), NOT counterparty paper (legal-intelligence), NOT LOIs (loi-generation), NOT renewal letters (document-assembly). Encodes MINIMAL AMENDMENT doctrine, 4 modules (Term/Rent/Tenant Change/Premises Change), 7-state recordation overlay, guaranty exhibit for substitutions, 16-check QC gate. DRAFT ONLY -- outbound send needs Gabriel's confirmation. v1.0"
---

# Lease Addendum — Oxford Realty Advisors

Drafts amendments and addenda to leases **already in effect**. This is the sole path for that
document type — see Scope below for the four adjacent skills it is not.

## Scope and boundary

**Owns:** amendments, addenda, and modifications to an in-force ORA lease.

**Does NOT own — route and say so if triggered wrongly:**

| If the request is... | Route to |
|---|---|
| A new lease on ORA paper | `masterlease-jurisdiction-rebase` (template) then `lease-form-qc` (gate) |
| Analysis of counterparty-drafted paper, or a redline/compare of a returned addendum | `legal-intelligence` |
| A letter of intent | `loi-generation` |
| A renewal offer letter or other generic template | `document-assembly` |

This is the SOLE path for lease addenda as of v1.0. `document-assembly`'s Template 6 (Lease
Addendum) is tombstoned in the same commit that ships this skill, mirroring its existing LOI
carve-out — see that skill's Changelog.

## Doctrine — MINIMAL AMENDMENT

The Prime Lease governs. The addendum changes an enumerated short list of terms and nothing
else. This is the design center; every module below operates inside it.

1. **Recital** identifies the Prime Lease by date, every prior amendment by date, the parties as
   currently constituted, and the Premises by street address, city, state, ZIP — defining
   "Premises" if the Prime Lease did not. ORA's own house form (see `references/house-style.md`)
   currently uses a blanket "and any subsequent addendums" catch-all instead of enumerating
   prior amendment dates — that catch-all does not satisfy this rule; QC check 9 (ordinal) and
   the recital check require the actual dates.
2. **Only amended terms appear**, each as a labeled hanging-indent paragraph. Never restate an
   unchanged provision — restatement creates ambiguity about whether it was amended. (Confirmed
   as ORA's actual practice across the existing addendum corpus — no restatement anywhere in it.)
3. **Ratification clause is mandatory.** ORA's own canonical sentence, used verbatim in every
   addendum reviewed: *"All other terms of the Prime Lease will remain in effect."* Where a
   conflict-control clause is genuinely needed (M3b, or any amendment touching multiple prior
   addenda), add it as its own sentence, not a semicolon-appended rider — this is ORA's own
   verified practice, not an invented convention: *"All other terms of the Prime Lease will
   remain in full force and effect. In the event of any conflict between this Addendum and the
   Prime Lease, this Addendum controls."*
4. **Never renumber the Prime Lease.** Cross-reference by section title, not number — the house
   style already does this by using generic labels (Termination, Rent, Tenant, Brokers) rather
   than section numbers; preserve that.
5. **Defined terms must match the Prime Lease exactly.** If it says "Demised Premises," the
   addendum says "Demised Premises."
6. **Ordinal verified, never assumed.** First / Second / Third Addendum is confirmed against the
   lease file before drafting. Guessing produces two documents with the same name — and the
   corpus already contains a live example of the failure mode: one file's own metadata Title
   field disagrees with its body title on the ordinal (see QC check 9).
7. **Counterparts + electronic signature clause. Notices only if addresses change.** Neither
   clause exists anywhere in ORA's current addendum template — add both as a new standing
   paragraph pair whenever they're triggered (counterparts: always; notices: only when a party's
   notice address is new or changing, which is every M3b substitution and every M4 unit swap).

Target length: 2–3 pages plus exhibits. If a draft exceeds that, the QC report names which
module inflated it.

## Modules

Composable — a deal invokes only the modules it needs.

### M1 — Termination / Term
New expiration date; whether this is an extension or a holdover conversion; confirm no option is
being exercised (that's a different instrument — an option exercise is not an addendum). Compute
cumulative term from the **original commencement date**, across all amendments, and test it
against the state recordation/acknowledgment threshold in `references/state-overlay.json`. Flag
if crossed — this is QC check 7.

### M2 — Rent
New base rent, commencement of the new rate, escalation basis and rate. Generate the rent
schedule as a table (ORA's own corpus already does this for every escalating addendum — 1×2 or
3-column, Lease Year / Monthly / Annual). Hard requirements:

- **Arithmetic verified programmatically** — `scripts/addendum_qc.py` check 3 recomputes every
  row and flags any mismatch.
- **Compounding, not simple**, unless the addendum expressly states otherwise. ORA's own
  practice is 3% compounding on the Lease-Year anniversary in every escalating deal reviewed —
  confirm the actual negotiated rate and basis before drafting, don't default silently.
- **Every row must trace to an operative clause.** A stub or interim period shown in the table
  with no clause granting it is a QC check 2 **BLOCK** defect. This is not hypothetical — it is
  the exact defect present in the 9050 Red Branch Rd Second Addendum (the acceptance-test file):
  the table's July–September 2026 stub row has no operative sentence obligating payment.
- **The table caption names who owes rent in each period** when a party change straddles it.
- **Escalation on the Lease-Year anniversary**, not the calendar year, unless the Prime Lease or
  this addendum states otherwise.

### M3 — Tenant change
Two legally distinct paths. Conflating them is the primary failure mode of this document type —
confirmed by the acceptance-test file, which drafted a full entity substitution using the
two-sentence mechanism ORA otherwise reserves for cosmetic name changes.

**3a — Name change** (d/b/a, corporate rename, same legal entity): ministerial. Recite old and
new name, confirm same entity, no release, no new guaranty, updated COI.

**3b — Substitution / novation** (different legal entity): a credit event, not a relabel.
Mandatory package — every item below is a QC gate check (13–16):

- Incoming tenant's **assumption** of all Tenant obligations.
- **Scoped release** of the outgoing parties — prospective only; outgoing parties remain liable
  for everything accruing before the effective date, including unascertained obligations and any
  opex/tax reconciliation for prior periods.
- **Consent signature block for every released party.** You cannot release a party, or reassign
  its security deposit, on a document it never signed. (The acceptance-test file has zero
  signature or even textual reference to the outgoing entity beyond the opening recital — this
  is the single most severe defect in that document.)
- **Security deposit disposition** stated explicitly: assigned, returned, or topped up — with the
  outgoing party's waiver if assigned.
- **Guaranty** where individual liability is being removed (see Guaranty Exhibit below).
- **Conditions precedent:** guaranty delivered, COI reissued in the new entity's name naming
  Landlord as additional insured, good-standing and signatory-authority evidence, foreign
  qualification in the property state if the entity is out-of-state.
- **Effective date** defined as the later of full execution and satisfaction of all conditions,
  plus an outside date with a Landlord termination right.

**Notice addresses are mandatory for M3b** (see Doctrine rule 7) — the incoming tenant's notice
address does not exist anywhere in ORA's boilerplate today and must be added explicitly.

### M4 — Demised Premises change
Adding or reducing units. Never a square-footage edit alone. Recompute and state: RSF, pro-rata
share for operating costs and taxes, rent PSF, parking allocation, insurance limits, revised
Exhibit A depiction with stipulated non-remeasurable SF. On a reduction, this is a partial
surrender — require surrender-condition and restoration standards, a release of the surrendered
space, and confirmation the reduction does not breach a lender covenant or a co-tenancy
provision.

## State and county overlay

`references/state-overlay.json` — keyed by state (OH/MD/IN/MO/KS/WI/TN), each entry carrying
`statute_cite`, `plain_language_rule`, `primary_source_url`, `verified_date`, and a
`confidence` field of `VERIFIED` or `UNVERIFIED — counsel confirmation required`. Every cite in
that file was independently confirmed against the state's official legislature/code site before
entry — none was carried forward from this skill's own build notes or any other skill without
re-verification (two skills already in this repo carry state citations for overlapping states;
neither was trusted as a source — see the file's own `sources_consulted` field per entry).

Covers per state: recordation/acknowledgment threshold for leases by term length (measured from
**original commencement**, cumulative across all amendments); whether a memorandum of lease is
the customary alternative; execution formalities (seal, witness, notarial acknowledgment);
limitations period for sealed vs. simple contracts; any recordation/transfer tax reached by a
lease amendment; statutory notice requirements a term change could trigger.

County layer: the venue clause in any new counterparts/guaranty language names the actual
county. Property-tax and reassessment consequences of a term or premises change route to
`ora-millage-lookup`, not computed here.

## Guaranty exhibit

Two forms — `references/guaranty-short-form.md` (ratified default, six lettered paragraphs A–F)
and `references/guaranty-long-form.md` (adds financial-statement covenant, notices,
representations, notarial acknowledgment — use when the guarantor's credit is thin or a
confessed-judgment provision is contemplated). D and E are load-bearing; QC check 16 flags any
redline touching B–E as material.

**Doctrine note:** this departs from ratified standing position 2 (`lease-form-qc` — co-tenancy,
not guaranty, for new leases). It is a deal-specific concession on an **existing** tenancy where
a novation is removing an individual's joint-and-several liability, not a change to the master
lease form. Log each use to `memory/rules.md`.

## QC gate

`scripts/addendum_qc.py` — reads `word/document.xml` directly (zip + regex, no `python-docx`
dependency for scanning), following the same pattern as `lease-form-qc/scripts/lease_qc.py`.
Severity BLOCK / HIGH / MED / LOW; non-zero exit on any BLOCK. Never present a draft as ready
with an open BLOCK.

| # | Check | Severity |
|---|---|---|
| 1 | Circular effective date — condition precedent due "on or before" a date defined as the moment of execution | HIGH |
| 2 | Rent-table row with no operative clause | HIGH |
| 3 | Rent arithmetic / compounding recomputed and verified | HIGH |
| 4 | Party-consent completeness — every released party, and every party whose collateral is reallocated, has a signature block | BLOCK |
| 5 | Security deposit disposition stated | BLOCK |
| 6 | Entity silently dropped from or added to the party list without a release or joinder | BLOCK |
| 7 | Cumulative term vs. state recordation threshold (`state-overlay.json`) | HIGH |
| 8 | Ratification / conflict-control clause present | BLOCK |
| 9 | Ordinal verified against the lease file (incl. metadata Title field — must match body title) | MED |
| 10 | Defined terms match the Prime Lease | MED |
| 11 | Insurance condition on any tenant change | BLOCK |
| 12 | Notice addresses present where a party changed | BLOCK |
| 13 | Counterparts / e-signature clause | MED |
| 14 | Unfilled `[TOKEN]` on a non-template file | BLOCK |
| 15 | Premises change without recomputed pro-rata share | HIGH |
| 16 | Guaranty attached where M3b applies | BLOCK |

Report table: `ID · Provision · Status · Severity · Recommended fix`, then a plain list of
remaining blanks.

## DOCX build mechanics

`templates/Lease_Addendum_TEMPLATE.docx` is the starting point — clean metadata, standing
counterparts clause, real page break before signatures, enumerated-prior-addenda recital
scaffolding. `scripts/build_addendum_docx.py` generates it (`--template`) and generates
populated drafts from deal data (`--config <json>`) using the same mechanics below; regenerate
the template from this script rather than hand-editing the `.docx` if the scaffolding needs to
change. For an addendum already in progress (not starting fresh), edit the source addendum in
place with `python-docx`, preserving the existing style set. No sibling skill in this repo
already implements table-integrity XML tricks, PDF-pagination
verification, or signature-page formatting — `lease-form-qc` is read-only and
`masterlease-jurisdiction-rebase` never touches tables, margins, or fonts. Two patterns are
reused from `masterlease-jurisdiction-rebase` (attribution in `scripts/addendum_qc.py` header):
the **asserted-count substitution** discipline (every text substitution declares its expected
match count; a mismatch aborts rather than silently applying 0 or N+1 replacements — this
skill's anti-contamination floor, ported from that skill's 2026-08-03 rule) and the **paragraph
clone** technique (`copy.deepcopy` a model paragraph's `w:pPr`/`w:rPr` to give an inserted
paragraph the correct numbering/style rather than defaulting to Normal).

- **Table integrity** — `w:cantSplit` on every row plus `w:keepNext` on every row but the last,
  and on the paragraph preceding the table. Never a manual page break.
- **Notice blocks** — `keepNext` binds each label to its address lines so a heading cannot orphan.
- **Term paragraphs** — 1.5" hanging indent, single tab after the label. Strip legacy mid-sentence
  tabs and non-breaking-space artifacts (mirrors `lease-form-qc` F9).
- **Signature page** — hard page break preceded by a centered, indented italic
  "[SIGNATURE PAGE TO FOLLOW]". ORA's current addendum corpus uses this phrase as plain text with
  no real page break behind it (confirmed across all five reviewed addenda) — this skill fixes
  that: a genuine `w:br type="page"`, not the `lastRenderedPageBreak` Word leaves behind
  incidentally. All signature blocks on one page. Spacing via `space_before`/`space_after`, never
  empty spacer paragraphs.
- **Exhibits** — own section, 1.0" margins, `WD_SECTION.NEW_PAGE`.
- **Verify page composition by rendering to PDF and reading it back.** Do not trust the paragraph
  model for pagination.

## Deliverables and conventions

- `YYYY-MM-DD_[Property]_[Addendum-Type]_v##.docx` in the deal folder `/outputs/`.
- Extractable-text PDF (Microsoft Print to PDF prohibited).
- QC report DOCX per ORA Institutional Style Guide (EB Garamond / DM Sans / IBM Plex Mono; Navy
  #1B2A4A, Gold #C9A96E, Parchment #F5F3EF).
- Never delete — move superseded drafts to `/archive/`.
- **DRAFT ONLY.** Outbound delivery to a tenant or counterparty requires Gabriel's explicit
  in-turn confirmation (Hard Invariant 1).

## Workflow

1. **Ingest** — lease file, prior addenda (enumerate every date — do not accept a blanket
   catch-all), and the deal terms being changed.
2. **Classify modules** — which of M1–M4 apply; for M3, classify 3a vs. 3b explicitly and state
   the classification in the draft header before writing a single clause.
3. **Verify ordinal** against the lease file (rule 6) before naming the document.
4. **Draft** — Doctrine rules 1–7, modules selected, guaranty exhibit if M3b.
5. **QC gate** — `scripts/addendum_qc.py`; fix and re-run until zero BLOCKs.
6. **Build DOCX + PDF** — mechanics above; verify pagination by rendering and reading back.
7. **Present** — never as ready with an open BLOCK; DRAFT ONLY, no outbound send.

## Failure modes — when NOT to use this skill

- The document is a brand-new lease, not an amendment to an in-force one → route to
  `masterlease-jurisdiction-rebase` + `lease-form-qc`.
- The counterparty sent back a redlined/compared version of a draft addendum →
  `legal-intelligence` Module 6 (reuse its Step 0 tracked-changes-vs-compare-tool detection,
  which itself routes to `deal-execution`'s `extract_revisions.py` — don't reimplement it here).
- An option is being exercised, not a new term negotiated → that's an option-exercise notice, a
  different instrument; do not draft it as an addendum.
- The state is not one of OH/MD/IN/MO/KS/WI/TN → the overlay has no entry; state so explicitly
  and require counsel confirmation before drafting anything with recordation/execution
  consequences.

## Changelog

- **v1.0** (2026-08-14) — initial build. Structural model: `loi-generation` (sole-path skill,
  state overlays, mandatory QC gate, versioned DOCX + extractable-text PDF). Doctrine, modules,
  and QC checks specified directly by Gabriel; house-style baseline and the M3b gap it doesn't
  cover confirmed against five real ORA addenda (1100 Rarig, 2203-2207 Northwood, 29000
  Information Lane, 9050 Red Branch Rd, 2808 Banwick Rd). State overlay independently verified
  per-state against primary sources (see `references/state-overlay.json`) -- 6 of 7 states fully
  verified (OH/MD/IN/MO/KS/WI); TN partially verified (2 of 6 items live-confirmed against
  advance.lexis.com before a CAPTCHA gate; the remaining 4 are explicitly marked
  UNVERIFIED -- counsel confirmation required rather than asserted). DOCX table/margin/PDF
  mechanics have no reusable prior art in this repo — written net-new, with the asserted-count
  substitution and paragraph-clone patterns ported from `masterlease-jurisdiction-rebase`.
  **Acceptance test PASSED:** `scripts/addendum_qc.py --m3b --state MD` against the original
  9050 Red Branch Rd Second Addendum draft correctly flags all 8 defects named in the build spec
  (checks 4/5/6/11/12/16 at BLOCK, checks 2/7 at HIGH -- 10 of 16 checks fail overall, exit 1) and
  clears cleanly against `2026-08-14_..._REVISED_v03.docx`, Gabriel's independently-drafted
  correction (0 BLOCKs, exit 0; the 2 residual findings -- the MD § 3-101(a) recordation advisory
  and a metadata Title/body ordinal mismatch the manual correction didn't touch -- are both real,
  not false positives, confirming the gate isn't just pattern-matching the original defect). The
  REVISED_v03 file's own drafting (assumption/release language, Substitution Date with an outside
  date and Landlord termination right, conditions precedent incl. foreign qualification, deposit
  assignment with waiver, and a six-paragraph A-F guaranty) independently converges on this
  skill's M3b package and guaranty-short-form structure point-for-point, despite being drafted
  before this skill existed -- strong evidence the doctrine in this file is right, not just
  internally consistent.
