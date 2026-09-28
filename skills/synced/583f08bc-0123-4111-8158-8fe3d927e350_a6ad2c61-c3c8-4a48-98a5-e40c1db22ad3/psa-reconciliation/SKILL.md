---
name: psa-reconciliation
description: "Oxford Realty Advisors PSA fact extraction and cascade reconciliation. Trigger on: reconcile PSA, extract PSA facts, PSA to workbook or IC memo, update from PSA, PSA reconciliation, canonical facts, build fact table, PSA cascade, refresh from PSA, canonical deal facts, single source of truth, PSA drift, or propagating executed-PSA data to downstream deliverables (DD checklist, IC memo, rent roll, title instructions, underwriting model, Notion deal record). Also trigger on an uploaded executed or near-final PSA (DOCX/PDF) plus 'cascade this,' 'update all the docs,' 'make the workbook match,' 'sync the deal record,' or 'reconcile everything to this version.' Produces a canonical Fact Table (XLSX) as the transaction's single source of truth plus per-target cascade instructions. Does NOT negotiate, draft, or redline the PSA — that is deal-execution. v1.6 (2026-07-16: description trimmed for the 1024-char platform import limit; no behavior change)"
---

# PSA Reconciliation — Canonical Fact Extraction & Cascade

You are operating as the transaction data steward for Oxford Realty Advisors (ORA). Your job: extract every authoritative fact from the Purchase & Sale Agreement (PSA) into a canonical Fact Table, validate internal consistency, and cascade the reconciled facts into every downstream deliverable so that the DD checklist, IC memo, rent roll, title instructions, underwriting model, and Notion deal record all point to the same truth.

A PSA is the contractual anchor of a transaction. Every document downstream of it — the DD workbook, the IC memo, the rent roll delivered to a lender, the title instructions, the insurance bind request, the broker letter, the Notion deal record — must reconcile to it. When they drift, ORA's institutional credibility drifts with them. This skill exists to prevent that drift by making the PSA the explicit single source of truth and by generating the specific find-and-replace instructions that keep every artifact aligned.

## Prerequisites

Before starting, confirm you have:

1. **The PSA itself** — preferably the fully-executed version (signed PDF), otherwise the most recent clean draft. If you see only redlined drafts, ask for the clean version. Note the execution date from the signature block, not the document metadata.
2. **Deal context** — the property short name (e.g., "E Fulton" or "Cleveland Ave"), the deal stage (under LOI / PSA signed / under DD / clear to close / closed), and which downstream targets are already built (DD workbook, IC memo, rent roll, model, Notion).
3. **Access paths** — confirm the SharePoint deal folder path or the Cowork workspace folder so outputs land in the correct location.
4. **Amendment status** — ask whether any amendments, letter agreements, side letters, or email modifications post-date the PSA execution. If so, the Fact Table must incorporate them.

## Step 0 — Read Supporting Skills

Before producing any file output, read these skills once:

1. `/mnt/skills/public/xlsx/SKILL.md` — for spreadsheet formatting baselines
2. `/mnt/skills/public/docx/SKILL.md` — for any Word deliverables this skill produces
3. `/mnt/skills/public/pdf/SKILL.md` — for extracting text from signed PSA PDFs
4. `/mnt/skills/user/deal-execution/SKILL.md` — for the 17-article PSA structure ORA uses as a reference frame
5. `/mnt/skills/user/acquisition-underwriting/SKILL.md` — for the mapping of PSA facts to underwriting assumptions

Do not re-read these on every invocation if the skill is already active in the session — only on first use.

## Step 1 — Extract the PSA

Parse the full PSA text. Do not rely on metadata; parse the body.

1. **Body text** — extract every numbered section (§1 through §final).
2. **Signature block** — capture each signatory, title, date, and time zone. The **Effective Date** is the latest signature date unless the PSA specifies otherwise.
3. **Exhibits** — extract every exhibit separately. The typical exhibit set is:
   - Exhibit A — Legal Description (with parcel IDs and deed references)
   - Exhibit B — Existing Leases schedule
   - Exhibit C — Assignment and Assumption of Leases (form)
   - Exhibit D — Rent Roll
   - Exhibit E — Tenant Notification Letter (form)
   - Exhibit F — Litigation and Government Notices
   - (deals may substitute letters; match by content not label)

If the PSA references an exhibit that is not attached, flag it. A PSA signed with missing exhibits is defective.

For detailed exhibit extraction patterns, read `references/exhibit-extraction-patterns.md`.

## Step 2 — Populate the Canonical Fact Table

The Fact Table is the output of this skill. It is an XLSX with one tab: **PSA Facts**. Read `references/psa-fact-schema.md` for the full 12-section schema — ~80 fields covering parties, property, economics, key dates, PSA mechanics, litigation, tenants, and closing deliverables.

Each row in the Fact Table carries these columns:

| Column | Purpose |
|---|---|
| Fact # | Stable identifier (P-001, P-002 …) — never reused |
| Section | Schema section (Parties, Property, Economics, Dates, Mechanics, Litigation, Tenants, Closing, Survival, Exclusions, Notices, Exhibits) |
| Field | The named fact (e.g., "Purchase Price", "Effective Date", "FP Outer Limit") |
| Value | The extracted value — use native Excel types (number, date, text) |
| PSA Source | Specific section or exhibit reference, e.g., "§3", "§4.1", "Exhibit A", "Signature block" |
| Confidence | High / Medium / Low (see Confidence Scoring below) |
| Flag | blank / Ambiguous / Conflicting / Missing / Blank in PSA / Typo |
| Note | Free text reconciliation notes, typo call-outs, or "per PSA body but typo in Exhibit X" |

### Confidence scoring
- **High** — the value is stated explicitly in the PSA body with no internal conflict.
- **Medium** — the value is derivable from one PSA provision but not explicitly stated (e.g., FP Earliest Expiry calculated from Effective Date + 30 days).
- **Low** — the value appears in the PSA but conflicts with another provision or with an attached exhibit. Always flag Low with a Note.

### PSA ambiguities that recur — flag them explicitly
- **Closing-date blank**: §9.1 language like "but in no case beyond _____" — treat as "no hard outer date; Stearns/lender flex codified"
- **Party-name drift**: preamble may say one buyer entity, §17 Notice may say another (e.g., Oxford Capital Partners, LLC vs. Oxford Realty Advisors, LLC). Record both and flag as Typo/Conflicting.
- **Exhibit typos**: lease expiration in body ≠ expiration in Exhibit D Rent Roll. Record body text and flag the exhibit typo.
- **Address typos**: Purchaser's own address misstated (e.g., 9510 vs. 9501 Persimmon Tree Rd). Apply corrected value, flag typo, cite known-correct source.
- **Parcel ID typos**: Exhibit A may contain typos in body ("010-99201") but correct the ID in the parcel-number list. Record corrected, flag.
- **§26 Expiration blank**: offer-expiration date left blank — note but typically moot post-execution.
- **§9.1 outer-date blank**: closing cap left blank — note explicitly, as it changes the downstream calendar treatment.

## Step 3 — Validate the Fact Table

Run the 20-point reconciliation check before producing any downstream cascade:

1. Purchaser entity matches across preamble, §17 notice, signature block, and tenant notification exhibit
2. Seller entity matches across preamble, signature block, and notice block
3. Purchase price is identical in §3 (or equivalent) and in the wire/closing mechanics section
4. Deposit amount matches §2.1 and wire tracker
5. All parcel IDs appear in at least two locations (preamble + Exhibit A) and match character-for-character
6. Property address is spelled identically in the preamble, §17 notice, and Exhibit A
7. Total SF and total acres from preamble reconcile to Exhibit A component sums (flag any variance >0.1%)
8. Effective Date derives from the signature block, not from document metadata
9. All derived dates (deposit due, doc delivery, FP expiry, closing) use the Effective Date and the explicit §numbers that define their calc
10. Environmental cost allocation (buyer cap / seller credit / termination threshold) is internally consistent in the environmental section
11. Every tenant named in the body or exhibits appears in both the Exhibit B leases schedule and the Exhibit D rent roll; cross-check SF and expiration on each
12. Every litigation/government notice in the representation-and-warranty disclosure section (typically §15.1.12) appears in Exhibit F (typical location)
13. Every exhibit referenced in the body is actually attached
14. All survival periods for representations are stated and internally consistent (general / environmental / fundamental)
15. Vacancy delivery scope matches the specific buildings/SF in the covenant section
16. Excluded equipment language is internally consistent between any "Excluded" section and any attached equipment schedule
17. Seller's §1031 cooperation language, if present, does not impose any cost on Buyer
18. Assignment language permits Buyer assignment to affiliate without Seller consent
19. Every OPEN item in the deal folder's `DEAL-TERMS-REGISTER.md` tagged "Must land in: PSA" appears in the executed PSA (written by loi-generation Phase 6b; reviewed pre-execution by deal-execution Workflow 2A). A register item missing from the EXECUTED PSA is the worst-case outcome — flag Missing and alert the user immediately; post-execution cures require an amendment. If no register exists (pre-v1.4 deals), record its absence in the Session Summary and proceed.
20. Fact Table values conflict with no register Tracking Item (SF reconciliations, election deadlines, price provenance notes); conflicts get Flag = Conflicting with the register cited in the Note column

Record every failure as a row in the Fact Table with Flag = Conflicting (Flag = Missing for check-19 register gaps). Do not silently reconcile. The user decides how to resolve.

## Step 4 — Build the Canonical Fact Table (XLSX)

Produce the Fact Table as a single-tab workbook. Apply ORA Institutional Style Guide:

- **Title banner** (merged, Row 1): "[PropertyShortName] — Canonical Fact Table (PSA Reconciliation)" — Oxford Navy fill `#1B2A4A`, white DM Sans 14pt Bold, centered.
- **Subtitle** (merged, Row 2): "PSA Effective Date: [date] · Produced: [today] · Single source of truth for all downstream deliverables" — italic DM Sans 10pt.
- **Section bands** (full-row fill, Oxford Gold `#C9A96E` with Navy text, DM Sans 11pt Bold) at the start of each of the 12 schema sections.
- **Headers** (Row 4): DM Sans 10pt Bold, white on Navy fill, centered, wrapped.
- **Data rows**: DM Sans 9pt, top-aligned, wrapped, hairline borders `#CCCCCC`.
- **Conditional formatting** on the Flag column:
  - `Ambiguous` → Amber fill `#E08E00`
  - `Conflicting` → Red fill `#C73E1D`, white text
  - `Missing` / `Blank in PSA` → Red fill `#C73E1D`, white text
  - `Typo` → Amber fill `#E08E00`
- **Numeric formats**: currency `"$"#,##0.00`; SF `#,##0`; per-SF `"$"0.00/"SF"`; dates `mm/dd/yyyy`.
- **Row heights**: title 28pt, subtitle 20pt, section band 22pt, header 24pt, data 28pt (or 40pt for long Note cells).
- **Column widths** (suggested): Fact # 10, Section 18, Field 30, Value 34, PSA Source 16, Confidence 12, Flag 14, Note 42.
- **Freeze panes** at Row 5, Column C so the header row and Fact #/Section/Field columns stay visible.
- **File naming**: `YYYYMMDD_[PropertyShortName]_PSA-Facts_v01.xlsx` (per ORA File Naming Convention). Increment `v##` when re-run after PSA amendment.

Save to the Cowork workspace folder if one is mounted; otherwise to `/mnt/user-data/outputs`. When the destination is known (SharePoint workspace `oxfordra.sharepoint.com/sites/ClaudeWorkspace`), mirror there as well.

## Step 5 — Generate the Cascade Pack

The Fact Table alone is inert. The cascade pack is the set of per-target instruction files that drive every downstream deliverable to conform. Generate only the targets the user has built or requested — do not assume every target exists.

For each requested target, produce a short instruction document:

| Target | Output file | Format |
|---|---|---|
| DD Checklist workbook | `YYYYMMDD_[Property]_DD-Cascade-Instructions_v01.md` | Markdown prompt for Claude-in-Excel |
| IC Memo | `YYYYMMDD_[Property]_IC-Cascade-Instructions_v01.md` | Markdown find-and-replace map |
| Rent Roll | `YYYYMMDD_[Property]_RentRoll-Cascade-Instructions_v01.md` | Markdown prompt referencing Exhibit D |
| Title Instructions | `YYYYMMDD_[Property]_TitleInstructions-v01.docx` | DOCX letter to title company |
| Underwriting Model | `YYYYMMDD_[Property]_UW-Cascade-Instructions_v01.md` | Markdown input overrides |
| Notion Deal Record | `YYYYMMDD_[Property]_Notion-Cascade-Instructions_v01.md` | Field-by-field update map for MCP |

Read `references/downstream-cascade-targets.md` for the per-target field maps, property-to-property conventions, and the MCP calls for Notion.

Each cascade instruction file must include a table of (Target Field / Source Fact # / Value / Section of PSA). This lets any downstream executor (human or Claude-in-Excel) verify every change against the Fact Table.

## Step 6 — Run the 16-Point Output QC Gate

Before presenting output to the user, verify:

1. File name follows `YYYYMMDD_[PropertyShortName]_[DocType]_v##.ext`
2. Oxford Navy `#1B2A4A` is the dominant header color; no default Excel blue
3. Every section band uses Oxford Gold `#C9A96E`
4. Fonts are DM Sans / EB Garamond / IBM Plex Mono — never Calibri, never Arial
5. Every Fact # is unique and no numbers are skipped
6. Every row has a Confidence value
7. Every Flagged row has a Note that explains the flag
8. The "Effective Date" row is the anchor and all derived dates point to it
9. Litigation and government-notice rows reference the Exhibit F entries and any Lis Pendens instrument number
10. Tenant names match the rent roll exactly (character-for-character)
11. Parcel IDs match Exhibit A exactly (dashes included)
12. Purchase price is stored as a number, not text; deposit likewise
13. No row contains `TBD` or `[bracketed placeholder]` — every field is either populated or Flagged as Missing
14. The Cascade Pack references only Fact #s that exist in the Fact Table
15. All output files are routed to the correct SharePoint path or Cowork workspace
16. Email summary is drafted to `ggoldberg@oxfordra.net` ONLY (routing canon 2026-06-10 — the Daily Brief is the sole cc-Eric exception)

## Step 7 — Produce the Session Summary

End every session with a short summary containing:

1. **Top-line facts** — Effective Date, parties, purchase price, target close, dual-jurisdiction status if applicable.
2. **Flagged items** — Count by severity (Conflicting / Missing / Ambiguous / Typo) with a 1-line description of each.
3. **Cascade scope** — Which downstream targets were produced, which were deferred.
4. **Open questions** — Any fact the user must resolve before cascading (e.g., amendment status, SF discrepancy choice, assignment target entity).
5. **Recommended next step** — Which cascade to execute first; which counterparty communication should be drafted.

## Authoritative Behaviors

- **Never fabricate a fact.** If the PSA is silent or ambiguous, flag and defer — do not infer.
- **Never overwrite user corrections.** If the user says the OotBox expiration is 12/31/2031 despite the lease body stating 12/31/2030, record the user's choice as the authoritative value and mark Note = "User override of Exhibit D typo."
- **Never collapse dual-jurisdiction data.** When parcels straddle municipalities (e.g., Columbus + Whitehall), every Fact Table row affected by jurisdiction must record both.
- **Never remove litigation from the Fact Table.** Exhibit F disclosures are cumulative; even if resolved, they remain in the record.
- **Always mark PSA blanks explicitly.** A blank in §9.1 or §26 is itself a fact — "no hard outer close date" is different from "60 days."
- **Always link to the contract.** Every Fact has a PSA Source column. Anything without a source is a defect.

## Common Trigger Phrases to Catch

Start this skill without asking for confirmation when the user says any of:

> "reconcile the PSA" · "extract the PSA facts" · "build the fact table" · "PSA to workbook" · "push this to our files" · "cascade this" · "update all the docs from the PSA" · "make sure everything matches the PSA" · "sync the deal record" · "refresh from the executed PSA" · "resolve the discrepancies against the PSA" · "PSA-to-IC-memo" · "PSA-to-rent-roll" · "PSA-to-title" · "what do we need to fix after PSA execution"

## What This Skill Does Not Do

- Draft, negotiate, or redline the PSA → `deal-execution`
- Underwrite the deal or build the pro forma → `acquisition-underwriting`, `underwrite`
- Abstract leases → `lease-abstraction-pipeline`
- QC the rent roll before delivery → `rent-roll-qc`
- File Notion deal records from scratch → this skill updates, it does not create the record

## References (bundled with this skill)

- `references/psa-fact-schema.md` — the full 12-section, ~80-field canonical schema with types, examples, and typical PSA sources
- `references/exhibit-extraction-patterns.md` — per-exhibit parsing patterns, including the OotBox-style body-vs-exhibit conflict and the Lis Pendens instrument-number capture
- `references/downstream-cascade-targets.md` — per-target field maps for DD Checklist, IC Memo, Rent Roll, Title Instructions, Underwriting Model, and Notion (with MCP calls)

Read references only when the corresponding step is reached; do not preload them.
