---
name: lease-form-qc
description: "Pre-execution QC gate for leases drafted on Oxford Realty Advisors own landlord form (Fairground Village Center / 1100 Rarig Ave / Sepich portfolio paper). Use when the user says: QC this lease, check this lease before signing, lease form check, run the lease QC, review our lease draft, new tenant lease, lease from the template, or uploads a DOCX that is an ORA-form lease. Also run before ANY outbound lease goes to a tenant or broker. Scans 51 systemic defects in the ORA base form (dead cross-references, undefined terms, OpEx billing, statutory cites, Ohio mitigation exposure) plus a token gate and footer tenant-mismatch check (53 checks) with PASS/FAIL severity. Also runs --loi-conformance: register vs. drafted lease, CONFORMS/CONFORMS+/PARTIAL/MISSING/CONFLICT matrix, for lease-generation's LOI gate. Carries ORA's six ratified standing lease positions (2026-08-03). Distinct from legal-intelligence: audits ORA's OWN paper. v2.6 (T2 tenant-mismatch check + --loi-conformance mode; 53 checks)"
---

# Lease Form QC — Oxford Realty Advisors own paper

Pre-execution gate for leases drafted on the ORA landlord form. Run BEFORE a draft
goes to a tenant, broker, or counsel. This is a defect scan of **our** paper — for
counterparty leases and PSAs use `legal-intelligence`.

## Ratified standing positions (Gabriel Goldberg, 2026-08-03)

These six were open decision gates. They are now **settled ORA policy** and are baked
into `ORA_MasterLease_ShallowBayIndustrial_v2.3_TEMPLATE.docx`. Apply them by default;
do not re-ask unless the deal presents a specific reason to depart.

| # | Position | Drafting consequence |
|---|---|---|
| 1 | **Modified gross**, tenant pays its proportionate share of increases over a base year. Base year = **the calendar year in which the Commencement Date occurs.** | Never label rent "net base rent" — that label is the A7 defect. Keep calendar-year accounting (matches Franklin County tax billing and ORA's books). No annualization of the base is needed: the Building incurs a full calendar year of cost regardless of when the tenant takes possession. |
| 2 | **Co-tenancy, not a guaranty.** Individuals are joined as joint-and-several co-tenants. | No guaranty exhibit. Conform insolvency language to "**if Tenant, any person or entity comprising Tenant, or any guarantor of this Lease**…" so it reaches co-tenants. Accept that co-tenants hold full tenant rights (notice, cure, possession). External AI reviewers will recommend a separate personal guaranty — that recommendation is **rejected as settled policy**, not an open question. |
| 3 | **Security deposit = 1.0× monthly rent.** | Do not propose 2 months absent a specific credit concern. |
| 4 | **Late fee 10% + 18% default interest**, retained. | Known penalty-characterization risk, consciously accepted. Do not silently reduce to 5%. The 18% now carries a lesser-of-maximum-lawful-rate savings clause (added 2026-08-03) — that clause preserves the rate, it does not soften it. |
| 5 | **Flat Hazardous Materials ban — no retail-product carve-out.** | Keep the environmental section absolute. Maximum landlord leverage is the deliberate choice. When the tenant's use plausibly involves packaged chemicals, note the day-one-breach/waiver risk in the report, but do not insert a carve-out. |
| 6 | **No extension option** by default. | Preserves mark-to-market flexibility. If an option is ever added, total possible term may exceed three years, triggering the R.C. 5301.01 acknowledgment (notarization) requirement. |

## External AI review intake (formalized v2.2)

When Gabriel supplies one or more external LLM reviews of ORA paper, run this protocol
(proven on the v2.2 reviews 2026-08-03 and the v2.4.1 ChatGPT/Grok/Gemini reviews
2026-08-04):

0. **Review-packet rule (added v2.3):** external AI reviews of ORA paper must be run on
   the master **and Exhibit B (Rules & Regulations) together** — never the bare master.
   Reviewers who see only the master report the operational package (roof, floor loading,
   exterior storage, plumbing, docks, utility capacity) as "missing"; this false finding
   recurred in both the 2026-08-04 v2.4.1 and v2.5 cycles. If a supplied review shows no
   awareness of Exhibit B, note it in the report and rule those points ALREADY DONE.
1. **Verify every factual claim against the document XML before ruling** — extracted
   text hides Word's numbering layer, footers and exhibit attachments; expect
   hallucinated defects (fake typos, "no numbering", "missing" provisions that exist).
2. **Screen every suggestion against the six ratified positions** — tenant-side edits
   (late-fee/default-rate reductions, entry notice, tiered holdover, audit rights,
   expense caps, SNDA-by-default, tenant self-help/offset, guaranty restructure) are
   rejected wholesale on landlord paper.
3. **Check whether the reviewer saw Exhibit B** — operational-package recommendations
   are usually already implemented there; rule them ALREADY DONE, not accepted.
4. **Rule each point** with the taxonomy AGREE / PARTIAL / REJECT / ALREADY DONE /
   FACTUALLY FALSE / DECISION GATE / COUNSEL PASS / DEFER-v3.0, one-to-two-sentence
   reasoning each, and verify quantitative claims (occurrence counts) directly.
5. **Route accepted edits** as asserted-count substitutions on the controlled master
   (never hand-edits to property templates), then rerun this QC and the
   masterlease-jurisdiction-rebase engine.

Reference adjudications (Claude Lease Project Outputs): 2026-08-04_MasterLease-v2.4.1_External-Review-Adjudication_Memo_v01.docx
(18 edits + 4 gate adoptions -> master v2.5) and 2026-08-04_MasterLease-v2.5_External-Review-Adjudication_Memo_v01.docx
(11 edits + Exhibit B v1.2 -> master v2.6; zero gates re-opened).

## Adjudicating external AI reviews of ORA paper (added v2.1)

Three external models reviewed template v2.2 on 2026-08-03. Lessons that generalize:

- **Verify every factual claim against the XML before acting.** Two models
  independently reported a "Demised Premisess" typo that does not exist anywhere in
  the document, and one claimed "no sections are numbered" when 35 Heading-1 sections
  carry style-based auto-numbering. External reviewers cannot see Word's numbering
  layer from extracted text and will hallucinate agreement with each other.
- **One real catch survived verification:** a numeric self-reference ("this Section 24
  shall be self-operative") broke when a section insertion shifted Subordination from
  24 to 25. Fix pattern: replace numeric self-references with "this Section" — now
  check F7.
- **Screen every suggestion against the ratified positions first.** Tenant-side edits
  (indemnity carve-outs for landlord negligence, entry-notice requirements, late-fee
  reductions, tenant self-help/offset, holdover reduction to 125–150%, landlord
  condition representations against as-is delivery) are drafted for the wrong client
  and are rejected wholesale on landlord paper.
- **Genuinely valuable additive material goes to the Rules & Regulations exhibit, not
  the lease body:** roof-penetration controls, exterior storage/trailer/container
  bans, truck parking, loading-dock rules, plumbing/floor-drain abuse, utility-capacity
  disclaimer, security and business-interruption disclaimers, CO/permits warranty,
  pest and mold responsibility. The lease already binds Tenant to promulgated rules;
  an exhibit keeps the form stable and lets rules evolve without re-papering.

## Why this exists

An audit on 2026-08-03 scanned six ORA-form leases spanning 2021–2026 (386 Morrison
08-2021, 410 Morrison 11-2022, 2822 Banwick 04-2025, 420 Morrison 10-2025, 2018
Zettler 02-2026, 388 Morrison/Shefler 08-2026). Result: **each failed 34–36 of the
original 39 checks** (39 of 42 current checks for the Shefler lease). Defects are
inherited from the base form, not introduced deal by deal. The SharePoint lease
library holds ~106 documents on this form.

Root cause: **cross-property contamination.** The Zettler building block (ZIP 43232)
was pasted into Morrison Road paper (correct ZIP 43213 — verified against Franklin
County Auditor parcel 010-208204, ZIPCD 43213, BLDGAREA 31,200) sometime between 2022
and 2025, and propagated forward. New leases were being spun from the last executed
lease rather than a controlled master, so every correction died with the deal it was
made on. The template now cites the county parcel number in the building description
— keep that pattern for every property.

## How to run

### Step 1 — Automated scan

```bash
python3 scripts/lease_qc.py <lease.docx|pdf|txt> [more ...] [--allow-tokens]
                            [--no-ocr] [--json]
```

Extraction, the OCR fallback, the UNREADABLE gate, and the report/CLI harness come
from the shared `ora_doc_qc.py` (also used by `pma-qc` and `listing-agreement-qc`). The
module is not vendored inside this skill's `scripts/` directory — `tools/package_skills.py`'s
`SHARED_ROOT_DEPS` injects a copy from the repo root at packaging time, landing at
`scripts/ora_doc_qc.py` inside the packaged `.skill` so lease-form-qc installs and runs
standalone. In a raw repo/worktree checkout, `lease_qc.py`'s sys.path fallback resolves
the repo-root `tools/` copy instead. DOCX is read from `word/document.xml`, PDF via
`pdftotext` with an OCR fallback, and plain text directly — useful for bulk-scanning
historical leases pulled from SharePoint. The report opens with a FILE / EXTRACTION /
ENC / RESULT block, then one line per FAIL with severity (BLOCK / HIGH / MED / LOW).

**Exit codes: 0 = clean, 1 = one or more failures, 2 = usage / extraction /
UNREADABLE.** Exit 2 is the important one: a document that will not yield enough text
to scan (a scanned PDF with no text layer, OCR unavailable) now gets **no QC verdict
at all** rather than a fabricated one. Before v2.5 a PDF was read as if it were UTF-8
prose and reported ~16 mojibake "failures" including BLOCKs. Never report a QC result
for a file that exited 2 — supply a text-layer copy, or install poppler-utils +
tesseract.

Benchmarks (scanner v2.6, 53 checks = 51 defect checks + T1 + T2): untouched ORA-form lease
≈ **39–48 failures**; a v2.4.1-derived lease fails exactly F10–F13 (+F14–F18); a
v2.5-derived lease fails exactly **F14–F18**; a v2.6-derived lease = **0 of 53** (the OH
master fixture in this repo re-verified directly: T2 does not fire — its footer complex
fields are PAGE/NUMPAGES page numbering, not FILENAME/DOCPROPERTY. The five rebased
state-conformed property templates this repo does not carry a local copy of were not
independently re-run for this change; confirm the same 0-of-53 on them before relying
on this benchmark for those files).
The scanner also enforces a **T1 token gate**: any
unfilled `[TOKEN]` **in the body or the footer** of a file whose name lacks
`_TEMPLATE` is a BLOCK failure (drafted leases must be fully filled; pass
`--allow-tokens` to scan a working draft). The footer half matters — the master's
footer carries `[PREMISES ADDRESS]` and `[TENANT ENTITY]`, and a token fill that
edits only the body leaves them printing on every page. Anything
above 0 on a template-derived lease means a token fill introduced a defect. **Scan clean or accepted documents only** — a tracked-change
redline contains both old and new text and will spuriously fail (~15 checks); run
`accept_changes.py` first.

### Step 2 — Check revision encoding before reporting "no changes"

A Litera / Workshare / Word-compare output carries **zero** `<w:ins>`/`<w:del>`
elements and encodes revisions as strikethrough plus coloured underline. Counsel
comments live in `word/comments.xml` and are invisible to a tracked-change parse.
State the detected encoding at the top of every report.

The scanner does this for you. The ENC line distinguishes all three states:
`tracked changes: <n>` (real OOXML `w:ins`/`w:del`), `compare-tool formatting
(strikethrough), no tracked changes` (Litera/Workshare/Word-compare output — run
`accept_changes.py` before believing the ~15 spurious failures), and `no tracked
changes (clean)`. It also reports `comments.xml: yes|no`.

### Step 3 — Report

Table: Class · Section · Status · Severity · Recommended fix. Then any item where the
deal departs from a ratified standing position above.

---

## Defect classes

### Class 1 — DEAL-BLOCKING

| ID | Defect |
|---|---|
| A1 | **ZIP / address conflict.** Section 1 premises ZIP contradicts the Section 4 building-block ZIP. Morrison Road = 43213 (county-verified); Zettler Road = 43232. Verify against the Franklin County Auditor parcel record, never against another lease. |
| A6 | **Operating-cost pass-through has no billing machinery** — no estimates, no annual reconciliation, no payment window, no survival. Unenforceable in practice. |
| A7 | **"Net base rent" label on a base-year structure.** Contradicts ratified position 1. Delete "net." |
| A11 | **Audited financial statements** demanded of small tenants who will never produce them — perpetual technical default, worthless covenant. |
| B7 | **Notices fail where they matter.** Tenant's only notice address is the Demised Premises; individual co-tenants get no separate address. Under ratified position 2 co-tenants must be independently noticed. |

### Class 2 — DEAD & FRAGILE CROSS-REFERENCES

- **A2** — "RIGHTS RESERVED BY LANDLORD" cited but the section does not exist in the
  legacy form. Fix by *adding* the section (landlord-protective), not striking the reference.
- **A2b** — "INSPECTIONS, REPAIRS AND INSTALLATIONS" cited; actual heading is "ENTRY
  FOR INSPECTIONS, REPAIRS AND INSTALLATIONS." A second occurrence drops the plural.
- **A3** — "ALL RISK PROPERTY INSURANCE" cited; actual heading is "INSURANCE."
- **A9** — Prevailing-party carve-out cites DEFAULT OF TENANT; the landlord-only fee
  rule lives in REMEDIES.
- **F7 (new)** — **Fragile numeric self-references** ("this Section 24 shall be
  self-operative"): any inserted section shifts auto-numbering and silently breaks
  them. Confirmed live: adding Rights Reserved moved Subordination 24→25. Use "this
  Section" for self-references; verify all remaining numeric refs (2(a), 11) against
  live numbering after ANY section insertion or reorder.

### Class 3 — UNDEFINED OPERATIVE TERMS

`Project`, `Building`, `Premises` (vs. `Demised Premises`), `Business Day`,
`Governmental Agency`, `Lease Term`. Standard definitions block goes under DEMISED
PREMISES (Building = county parcel-cited address + RSF; Project = Building + land +
common areas; Business Day = weekdays excl. Ohio bank holidays; Lease Term = term +
extensions + holdover). Match **any quote style** when testing for a definition —
the form mixes straight and curly quotes.

### Class 4 — OBSOLETE / WRONG STATUTORY CITATIONS

CERCLA: 42 U.S.C. § 9061 → **§ 9601**. HMTA: 49 U.S.C. § 1802 → **§ 5101** (recodified 1994).

### Class 5 — OHIO LAW EXPOSURE

- **B2** — Unqualified no-mitigation disclaimer vs. *Frenchtown Square Partnership v.
  Lemstone, Inc.*, 99 Ohio St.3d 254, 2003-Ohio-3648. Add "except to the extent
  required by applicable law."
- **B3** — Acceleration without reletting-proceeds credit invites a penalty attack.
- **F8 (new)** — 18% default interest should carry a **usury savings clause** (lesser
  of 18% or maximum lawful rate). Preserves the rate under ratified position 4.
- **R.C. 5301.01** — total possible term (including options) over three years requires
  acknowledgment. Position 6 keeps terms short; still check every option.
- Jury waiver and subrogation waiver enforceable; no Ohio commercial deposit statute.

### Class 5a — v2.5 STANDARD PROVISIONS (added v2.2)

- **F10** — venue clause (courts of the county where the Project is located; tokenless, rebase-safe).
- **F11** — indemnity carve-out for losses waived under the INSURANCE waiver of subrogation.
- **F12** — "Governmental Agency" and "Building Standard" defined.
- **F13** — Operating Costs exclude amounts separately billed to / paid directly by tenants.

### Class 5b — v2.6 STANDARD PROVISIONS (added v2.4)

- **F14** — "All Risk (Special Form) Property insurance" — modernized policy-form terminology.
- **F15** — Landlord exculpation enumerates managers, members, officers, employees, agents.
- **F16** — assignment/sublease excess-rent (profit) capture, net of documented brokerage.
- **F17** — continuous prepaid annual HVAC preventative-maintenance contract, copy delivered annually.
- **F18** — footer carries the ORA Master Lease form-version tag (vintage forensics).
- **T1** — unfilled-token gate on non-template files (BLOCK; `--allow-tokens` to override).

### Class 5c — CROSS-DOCUMENT PROVENANCE (added for the lease-generation handoff)

- **T2** — footer FILENAME/DOCPROPERTY field resolves to a tenant name other than this
  lease's own defined Tenant (BLOCK). Catches a lease cloned from a **different**
  tenant's executed lease as a drafting shortcut (instead of the property template),
  where a stale Word field in the footer still displays the old tenant's name even
  after every `[TOKEN]` has been filled — T1 cannot see this, because a field's cached
  result is not a token, it is ordinary-looking text that happens to be wrong. Handles
  a co-tenant list (ratified position 2) by checking a footer field against every
  listed name, not just the first. No FILENAME/DOCPROPERTY field in the footer at all —
  lease-generation's own output, which replaces the field with static text — passes
  cleanly by design. Can only see a Word **complex** field (`<w:fldChar>` +
  `<w:instrText>`); a **simple** field (`<w:fldSimple w:instr="...">`) stores its
  instruction in a tag attribute the shared extraction module discards along with every
  other tag, and is invisible to this check — a documented limit, not a gap to route
  around inside this file (see `_footer_field_candidates()`'s comment).

### Class 6 — MISSING PROVISIONS

No-recording · Landlord default standard · Force majeure · OFAC · Counterparts/
e-signature · Time of the essence · Personal property taxes · Exhibit A premises
depiction with stipulated non-remeasurable SF · Rent schedule table · County parcel
number in the building description.

### Class 7 — OTHER SUBSTANTIVE GAPS

A8 corporation-only authority clause · A10 circular Delay-in-Commencement · B4
ambiguous holdover formula (keep the 200% rate, fix the arithmetic) · B5 unallocated
HVAC replacement (Landlord replaces at end of useful life, amortized into Operating
Costs, unless Tenant's maintenance default) · B6 insurance gaps (CGL aggregate,
Employer's Liability, contractor minimums, annual COI delivery) · B8 water billing
mechanism · B11 guarantor/co-tenant conform per position 2 · Rent proration by actual
days in month, not 1/30th.

### Class 8 — TYPOGRAPHY AND MECHANICS

"his agents" → "its" · "succeeding Lease or succeeding tenant" · "a comparable
publications" · "Interior lighting" stray capital · "tenant shall provide" lowercase ·
"under seal" · missing comma in building address · empty Heading-1 spacer paragraphs
before the signature block · **F9 (new)** non-breaking-space artifacts in operative
text (legacy Word residue; also masks regex-based QC checks) · F6 Business-Day late
fee vs calendar-day cure (passes once Business Day is defined) · blank execution date.

### Class 9 — CLAUSE ORDER

Sequencing defects in the legacy form (Security Deposit after Assignment; Landlord
Cure stranded; Financial Statements after Miscellaneous). Reordering is optional —
if done, re-verify every numeric cross-reference (see F7).

---

## `--loi-conformance` mode (added for the lease-generation handoff)

```bash
python3 scripts/lease_qc.py --loi-conformance <deal-terms-register.json> <lease.docx> [--json]
```

Replays lease-generation's own "LOI conformance matrix" gate (that skill's SKILL.md
"3. Gates", item 4) as a scanner-owned, testable output instead of a manual judgment
call: loads a `deal-terms-register.json` (schema at
`lease-generation/references/deal-terms-register.schema.json`), reads the drafted
lease's text, and emits one row per field category — landlord, tenant, co_tenants,
premises, use, term, options, rent, expense_structure, utilities, security_deposit,
parking, landlord_work, maintenance, insurance, broker, signage (17 total) — each a
**CONFORMS / CONFORMS+ / PARTIAL / MISSING / CONFLICT** verdict. Not every schema leaf
has its own row: `special_provisions` (a heterogeneous array of ad-hoc clauses with no
fixed shape to match against) and a handful of already-covered categories' own
sub-fields (`utilities.gas`/`.trash`, `parking.allocation`/`.vehicle_class_cap`) are not
independently verified — treat a CONFORMS row as "the fields this mode checks conform,"
not "every negotiated term in this category was verified," and cross-check those
specific sub-fields by hand. Text and `--json` report shapes both follow the standard
scan mode's conventions. Exit codes: **0** = every row CONFORMS/CONFORMS+, **1** = at
least one PARTIAL/MISSING/CONFLICT row (matches the matrix gate: "nothing ships with
PARTIAL/MISSING/CONFLICT unless Gabriel resolved it"), **2** = usage / register-load /
lease-UNREADABLE error, including a malformed register (not a JSON object) or a missing
lease file — a single malformed FIELD inside an otherwise-valid register degrades just
that row to MISSING (with a `could not evaluate` detail) rather than crashing the whole
matrix. This is a separate code path from the standard 53-check scan (different question, different
source of truth, different output shape) and does not add to `checks_run`.

## Decision gates — never fix unilaterally

Only genuine departures from the six ratified positions get comments now. Gate rulings
2026-08-04 (Gabriel): ADOPTED into master v2.5 — Basic Lease Information page (body
controls on conflict), relocation right (Rights Reserved clause (h)), assignment
recapture, CC&R compliance. REJECTED as defaults (deal-by-deal concessions only) —
SNDA/non-disturbance (pure subordination remains the landlord default),
affiliate-assignment carve-out. Remaining counsel-pass items: attorney-in-fact
estoppel, R.C. Ch. 1923 self-help/notice-to-quit waiver, acceleration formula,
gross-up methodology.

## Output

- Redline deterministic fixes as **real tracked changes** (`<w:ins>`/`<w:del>` with
  author and date), never clean overwrites.
- **Normalize runs before editing** — split multi-`<w:t>` runs into one-`<w:t>` runs
  first; a splitter that keeps only the first `<w:t>` silently truncates paragraphs.
- Validate with the `docx` skill's `scripts/office/validate.py <out> --original <in>
  --author "<author>"`; must report **All validations PASSED**.
- Deliver the QC report as a DOCX per the ORA Institutional Style Guide (EB Garamond /
  DM Sans / IBM Plex Mono; Navy #1B2A4A, Gold #C9A96E, Parchment #F5F3EF), named
  `YYYY-MM-DD_[Property]_Lease-QC_v##.docx`.

## Preventing recurrence

Draft new leases from **`ORA_MasterLease_ShallowBayIndustrial_v2.6_TEMPLATE.docx`** (accept the
tracked v2.5→v2.6 changes when drafting) with
**`ORA_MasterLease_ExhibitB_RulesAndRegulations_v1.2_TEMPLATE.docx`** attached as Exhibit B
(0 of 46; all six positions encoded; BLI page, venue, subrogation carve-out, OpEx separate-billing exclusion included; deal terms tokenized; parcel-number pattern
included). Never copy the last executed lease. After filling tokens, run this QC
anyway — token fills introduce their own errors. **After inserting or removing any
section, re-verify every numeric cross-reference** — that is exactly how the v2.2
Section 24 defect was born.

## Changelog

### v2.6 — T2 + `--loi-conformance` mode (lease-generation handoff)

Two additions handed off from `lease-generation`'s SKILL.md, both additive (no
existing check ID, severity, or logic changed):

| Change | Why |
|---|---|
| **T2** registered (BLOCK) | Footer FILENAME/DOCPROPERTY field naming a different tenant than this lease's own defined Tenant — the cross-contamination failure mode this skill exists to catch generally, specific to a stale field surviving a token fill. Ctx-aware (like A2/F9/F18), not `bool_check()`-wrapped: reads `ctx["meta"]["footer"]` and `ctx["raw"]`. Detects Word **complex** fields (`fldChar`+`instrText`) only — a **simple** field's `w:instr` attribute is discarded by the shared extraction module's tag-stripping and is invisible here; widening that is an `ora_doc_qc.py` change, out of this file's reach (see Class 5c). A candidate is only ever treated as a tenant claim when it occupies the documented tenant slot — a FILENAME token after a literal `Lease` marker, or a DOCPROPERTY whose property NAME itself reads tenant/lessee-labeled — after independent review reproduced false BLOCKs on address-only filenames and on ordinary metadata properties (`Company`, `DocID`, `Title`, `Manager`). Checks_run is now **53**. |
| `--loi-conformance <register.json>` mode added | A second CLI mode (dispatched before CHECKS/`run_cli()`) replaying lease-generation's "LOI conformance matrix" gate as a scanner-owned, testable CONFORMS/CONFORMS+/PARTIAL/MISSING/CONFLICT matrix across 17 field categories. Separate code path, separate source of truth (the deal's own register, not the fixed defect registry) — does not touch `checks_run` or the standard scan's severity model. Two independent review passes found and fixed: dollar-amount matching was truncating cents (a register rent stated to the cent could silently CONFORMS against a lease stating different cents); the `gross` expense-structure phrase matched "gross negligence" in any lease's exculpation clause regardless of actual structure; `term`'s CONFORMS+ was inferred from bare "early access" text rather than the register's own `term.early_access` field; a `suite` value with no word-boundary anchoring could never fail; `utilities`' key-name fallback made that row unfailable; the mode had no error containment (a missing lease file or a malformed register field raised an uncaught exception at **exit 1**, indistinguishable from a real "the matrix has blocking rows" verdict, now **exit 2**, or a contained MISSING row for one malformed field); a CPI/fixed-dollar-step escalation (not text-matchable) silently CONFORMS'd instead of reporting PARTIAL; and `landlord_work`/`signage`'s exact-phrase matching against free-text register descriptions made those two rows essentially unfailable to CONFORM even against ORA's own canonical example register (`_phrase_present()` gained a `threshold` mode: a majority of a description's significant (5+ char) words, matched anywhere in the lease text, rather than every word verbatim in one window). |

Regression evidence: 89 unit tests in `tests/` (41 new — 16 on T2 including 4 dedicated
false-positive-surface cases, 25 on `--loi-conformance` including its own dedicated
regression-fix test class — the pre-existing 48 unchanged in substance; two hardcoded
`checks_run`/"N of 52" literals bumped to 53 to reflect T2's registration). Two
independent code review passes (pr-review-toolkit code-reviewer, re-run after the first
pass's fixes since a review verdict is keyed to exact content) found 3 critical + 6
important defects on the first pass and 2 further important defects on the second,
all fixed and covered above and in `tests/`. The
OH master v2.6 fixture in this repo re-verified directly: **0 of 53**, T2 silent (its
footer complex fields are PAGE/NUMPAGES, not FILENAME/DOCPROPERTY) — the five rebased
state-conformed property templates live outside this repo and were not independently
re-run for this change.

### v2.5.1 (2026-08-17) — review fixes, before v2.5 ever shipped

Both items below were caught by independent review of the v2.5 retrofit and fixed on
the same branch, so no operator ever saw the defective behavior.

| Change | Why |
|---|---|
| **T1 scans the FOOTER again** | v2.5 registered T1 via the shared `unfilled_token_check()`, which reads the document BODY only. Footer text lives in `meta["footer"]`, a channel that helper never looks at — so removing the old `[[FOOTER]]` splice silently dropped the footer from the token gate. ORA's own v2.6 master carries `[PREMISES ADDRESS]` and `[TENANT ENTITY]` in `word/footer2.xml`/`footer3.xml`: a lease with a filled body and an untouched footer cleared T1 and would have gone out for signature with both tokens on every page. T1 is now a local ctx-aware check scanning body **and** footer with the same regex, the same two gates (`_TEMPLATE` filename, `--allow-tokens`), and the same BLOCK severity. |
| **ENC precision restored** (supersedes the v2.5 "ENC precision lost" row, now removed) | `ora_doc_qc.scan()` now carries `extract()`'s `meta["strike"]` into its report dict and `print_report()` branches on it, so the ENC line again distinguishes compare-tool strikethrough from a genuinely clean document. The Step 2 workaround heuristic this briefly required is deleted. |

Regression evidence: 47 unit tests in `tests/` (5 new, all on the footer-token path,
including one that asserts the shared body-only helper *would* have missed it and
that the v2.5 `[[FOOTER]]` false BLOCK does not return); `pma-qc` and
`listing-agreement-qc` fixtures re-run unchanged.

### v2.5 (2026-08-17) — retrofit onto the shared `ora_doc_qc.py`

Extraction, OCR fallback, UNREADABLE gate, report, and CLI now come from the shared
module. Check logic is unchanged except where noted. Intentional behavior changes:

| Change | Why |
|---|---|
| **Exit 2 added** for usage / extraction / UNREADABLE | A PDF used to be read as UTF-8 prose. Measured on a 8-word no-text-layer PDF: **16 of 51 "FAILED", 2 BLOCK, exit 1** — a verdict on a document never read. Such input now returns no QC result. |
| **T1 stopped firing on `[FOOTER]`** | `text_of()` spliced a `[[FOOTER]]` marker onto every DOCX and `TOKEN_RE` matched the inner `[FOOTER]`. On all 10 real executed ORA leases regression-tested, that was the **only** token T1 ever found — a spurious **BLOCK** on every non-`_TEMPLATE` lease. Marker gone, false BLOCK gone. |
| **F6 now fires on ORA's own paper** | ORA paper writes "five `\xa0` (5) Business Days…"; the old pipeline never folded the non-breaking space, so F6's plain-space pattern silently never matched. It fired on 8 of 10 real leases once folded — a real defect that had been invisible. |
| **A3 / A9 now catch smart-quoted cross-references** | They match an ASCII `"` class; Word emits curly quotes, so they used to miss every real instance. Neither fires on the v2.6 master. |
| **T1 is a registered check** | Was synthesized ad hoc inside `scan()`. Now in the registry, so it appears in `--json` and the denominator (**52**, not 51). |
| **F18 reads `meta["footer"]`** | Replaces the `[[FOOTER]]` parsing trick. Same four-row truth table; footer boilerplate no longer leaks into every other check's body text. |
| **Report format** | Shared `print_report()` block. Nothing parses this script's stdout; `masterlease-revision-cycle` / `-jurisdiction-rebase` gate on the exit code, unchanged. |

Regression evidence: 42 unit tests in `tests/`; 23 real ORA files (10 executed leases,
7 addenda/intake copies, 6 v2.6 templates) diffed pre- vs post-retrofit with **zero
unexplained verdict changes** — every delta traced to a row above. All six v2.6
templates: **0 of 52**, identical before and after.
