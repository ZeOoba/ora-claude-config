# Downstream Cascade Targets

Per-target field maps for propagating canonical PSA facts into Oxford Realty Advisors deliverables. Read this reference during Step 5 (Generate the Cascade Pack) of the skill.

Each target section specifies (a) what fields to push, (b) where they go in the target document, (c) the output format for the cascade instruction file, and (d) any target-specific QC checks.

---

## Target 1 — DD Checklist Workbook

**Output file.** `YYYYMMDD_[Property]_DD-Cascade-Instructions_v01.md`
**Format.** Markdown prompt intended for Claude-in-Excel (the native Excel Copilot integration). The user pastes the prompt into the Excel Claude pane; Excel Claude executes the edits against the open workbook.

**Target workbook structure (assumed).** The ORA DD Checklist template has the tabs: COVER SHEET, OPS DASHBOARD, 2-WEEK LOOKAHEAD, DEAL ASSUMPTIONS, MASTER CHECKLIST, TIMELINE, DOCUMENT INDEX, CONTACT DIRECTORY, WIRE TRACKER, VENDOR STATUS, PSA CLAUSE MAP, COST TRACKER, PARCEL ZONING MAP (v02+), DATA ROOM MAP, DECISION LOG, RED FLAGS LOG.

**Field map.**

| Fact # | Target — Tab | Target — Cell / Row | Value |
|---|---|---|---|
| P-001 | DEAL ASSUMPTIONS | Parties / Purchaser (Contracting Entity) | Oxford Capital Partners, LLC |
| P-002 | DEAL ASSUMPTIONS | Parties / Purchaser (d/b/a / Notice Name) | Oxford Realty Advisors, LLC |
| P-007–P-009 | DEAL ASSUMPTIONS + CONTACT DIRECTORY | Buyer's Counsel row | Firm + Attorney + Email |
| P-010, P-012, P-013 | DEAL ASSUMPTIONS + CONTACT DIRECTORY | Seller rows | Entity + Signatory + Title |
| P-014 | DEAL ASSUMPTIONS + CONTACT DIRECTORY | Seller's Counsel row | Firm + attorneys + emails |
| P-015 | CONTACT DIRECTORY | Listing Broker row | Broker + firm + party represented |
| P-016–P-030 | DEAL ASSUMPTIONS + PARCEL ZONING MAP | Property block + parcel grid | All address / SF / acres / parcels / jurisdiction / zoning |
| P-031–P-045 | DEAL ASSUMPTIONS | Economics block | All price + deposit + env caps + cost allocations |
| P-046 | DEAL ASSUMPTIONS | Key Dates — Root Inputs / PSA Effective Date | Effective Date |
| P-047–P-060 | DEAL ASSUMPTIONS + TIMELINE + 2-WEEK LOOKAHEAD | Derived Dates block | Every date |
| P-063–P-078 | DEAL ASSUMPTIONS Controls + PSA CLAUSE MAP | Mechanics map | Each mechanic row |
| P-079–P-081 | PSA CLAUSE MAP | Survival row | §22 survival matrix |
| P-087–P-099 (each) | DOCUMENT INDEX + RED FLAGS LOG + MASTER CHECKLIST §8 | Per-case / per-notice | One checklist row per disclosed item |
| P-100+ tenant rows | MASTER CHECKLIST §5 (Lease Audit) + DOCUMENT INDEX | Per-tenant | Cross-reference lease abstract and estoppel items |
| P-136–P-142 | MASTER CHECKLIST §12 (Closing) | Excluded equipment | Item referencing pre-closing walkthrough |
| P-151–P-156 | DOCUMENT INDEX + DATA ROOM MAP | Exhibits | One row per exhibit |

**Required post-edit QC checks in the generated prompt.** Include a 12-point verification gate in every DD cascade prompt (see `20260423_E-Fulton_DD-Checklist_Excel-Claude-Prompt_v01.md` as reference template).

---

## Target 2 — IC Memo

**Output file.** `YYYYMMDD_[Property]_IC-Cascade-Instructions_v01.md`
**Format.** Markdown find-and-replace map suitable for Claude-in-Word or manual DOCX editing.

**Typical IC Memo sections requiring reconciliation.**

| IC Memo Section | Source Facts |
|---|---|
| §1.1 Deal Overview (property line) | P-016, P-022, P-023, P-024, P-026 |
| §1.1 Parties | P-001, P-010, P-015 |
| §1.1 Seller Counsel | P-014 |
| §1.1 PSA Status + Effective Date | P-046 |
| §1.1 Hard Close Deadline | P-058 or "None — Stearns/lender flex codified" if P-058 = N/A |
| §1.1 Earnest Money + Escrow Agent | P-034, P-036 |
| §1.2 Investment Thesis — Price/SF | P-037 (derived) |
| §1.3 Key Return Metrics | Depends on model — not directly sourced from PSA |
| §1.4 Sources & Uses | P-031, financing from underwriting model |
| §1.5 Kill Conditions | Include P-039/P-040/P-041 thresholds + any Exhibit F item classed as kill-relevant |
| Property Description | P-016, P-017–P-021, P-027–P-030 |
| Rent Roll Summary | P-100+ tenant rows |
| DD Requirements | §8 and §13 cases from P-087+ |
| Transaction Structure | P-031, P-032, P-034, P-063, P-064, P-073 |
| LOI Terms & Transaction Timeline | P-046, P-047, P-055, P-056, P-060 |

**QC check specific to IC memo.** Every dollar amount, date, SF figure, and parcel ID in the IC memo must match the Fact Table exactly. Run a word-count-style diff before finalizing — any cell referenced but not populated from the Fact Table is a defect.

---

## Target 3 — Rent Roll

**Output file.** `YYYYMMDD_[Property]_RentRoll-Cascade-Instructions_v01.md`
**Format.** Markdown prompt referencing Exhibit D facts.

**Field map.**

The rent roll is substantially Exhibit D. Use Section 8 tenant rows (P-100+) to populate:

| Rent Roll Column | Source Fact |
|---|---|
| Tenant Name | Tenant Name field |
| Premises / Suite | Premises Address field |
| SF | Premises SF field |
| Lease Start | From lease abstract, cross-check with Exhibit D |
| Lease Expiration | Expiration Date field (governing) |
| Base Rent — Monthly | Monthly Base Rent Y1 field (plus ladder if captured) |
| Base Rent — Annual | Annual Base Rent Y1 field |
| Escalation | Escalation Structure field |
| Options | Options to Renew field |
| Security Deposit | Security Deposit field |
| Guarantor | Guarantor field |
| Notes | Any "Body-vs-Exhibit Discrepancy" flag content |

**Recipient sensitivity.** If the rent roll is going to a lender, investor, buyer, or broker, route the output through the `rent-roll-qc` skill before delivery. Do not skip this step.

---

## Target 4 — Title Instructions Letter

**Output file.** `YYYYMMDD_[Property]_TitleInstructions-v01.docx`
**Format.** Formal DOCX letter to the escrow / title agent, on ORA letterhead.

**Recipient.** Escrow Agent per P-036.

**Required content.**

1. **Subject line** — "Title Commitment and Closing Instructions — [Property Short Name]"
2. **Property identification** — All parcel IDs (P-017 through P-021 in full), all street addresses (P-016), recorded deed reference (P-030).
3. **Dual-jurisdiction notice** — If P-027 ≠ P-028, instruct title to run **separate municipal lien searches for both jurisdictions**. State each jurisdiction by name.
4. **Coverage request** — ALTA 2021 Extended Coverage policy with endorsements: ALTA 9.0, ALTA 25 (Survey/Same as Survey), Access, Contiguity (if multi-parcel), Tax Parcel. (Per §7 of standard ORA PSA.)
5. **Seller-lender payoff coordination** — For every foreclosure or lender-held-lien disclosure from P-087+ marked title-impacting: include explicit instruction to coordinate payoff letter, recordable release, UCC-3 terminations, and (if applicable) stipulation of non-pursuit filed in the pending action.
6. **Lis Pendens extinguishment** — For every Lis Pendens in P-087+: quote the Instrument Number (P-089) and instruct title to extinguish or endorse around prior to Closing.
7. **Existing litigation inventory** — Full list of Exhibit F disclosures requiring title treatment.
8. **Survey coordination** — Reference the surveyor and the 2022 survey update obligation per §4.3 / §7.
9. **Closing-cost allocation** — Quote P-042 and P-043 (typically split 50/50 per §8.2 and §7 respectively).
10. **Deed form** — Special warranty deed per §9.3(a).
11. **Authority package receipt** — Instruction to not schedule closing until Seller's §15.1.16 authority package (P-050) is on file.
12. **Wire verification protocol** — All wires verified by phone before transmission; restate fraud-prevention protocol.

**QC check.** The title instructions letter must not contain any dollar figure, date, or parcel ID that isn't in the Fact Table. Every instruction must tie back to a §ref.

---

## Target 5 — Underwriting Model

**Output file.** `YYYYMMDD_[Property]_UW-Cascade-Instructions_v01.md`
**Format.** Markdown input-override list.

**Typical UW model inputs to reconcile.**

| UW Model Input | Source Fact |
|---|---|
| Purchase Price | P-031 |
| Acquisition Date | P-060 (Target Close) |
| Total SF (governing) | P-024 |
| Price per SF | P-037 |
| Env. Buyer Cap | P-039 |
| Env. Seller Credit | P-040 |
| Env. Termination Threshold | P-041 |
| Closing Cost Allocation | P-042 (50/50 deviates from standard Franklin County 40/60 assumption — flag in model if applicable) |
| Title Insurance Cost Allocation | P-043 |
| In-Place Rent (Y1) | Sum of annual base rents from tenant rows |
| Tenant SF (in-place) | Sum of SF from tenant rows marked In-Place at Close = Yes |
| Vacancy SF at Close | P-024 minus in-place tenant SF minus P-066 vacancy-delivery scope |
| Earnest Money (escrow) | P-034 |
| Lease Expirations | Per-tenant expiration dates |

**QC check.** Before delivering UW cascade, confirm the model's Total SF input matches P-024 exactly — a 539-SF delta at $6–$9/SF rent can shift stabilized NOI by $3K–$5K annually.

---

## Target 6 — Notion Deal Record

**Output file.** `YYYYMMDD_[Property]_Notion-Cascade-Instructions_v01.md`
**Format.** Markdown prompt with explicit MCP tool calls.

**Notion databases affected.**

| Database | Database ID | Data Source ID (collection://) | Purpose |
|---|---|---|---|
| **PSA Deals — Precedent Library** | `b2b626ed-2490-40dd-8dbd-d378e1356568` | `d5cd671d-ba2b-4635-a011-cf5303574408` | **PRIMARY** — create or update the deal-level precedent row |
| **PSA Facts — Master** | `b28d0555-8f0c-465e-86e3-cd5625c68539` | `af3dc100-38e5-46ab-8d40-22c0e880e79a` | **PRIMARY** — create one row per fact (P-### ID); relates to PSA Deals |
| **Acquisition Pipeline Tracker** | `46c8a5c6-8b37-4c53-a10d-0f55c97613e5` | `bcfe4a03-7e61-4ac1-a0bb-c44174fa138b` | Update the pipeline record (two-way relation from PSA Deals via `Pipeline Link` property) |
| **Deal Sourcing Log** | — | `9a6ae219-85a3-4621-899c-c757fd062f8b` | Mark the source lead as converted |
| **Broker Relationships** | — | `48e43778-...` | Log listing broker contribution |
| **Tenant Database** | — | `8dbbaec0-...` | Create / update tenant records for in-place tenants |

Hub page for the precedent library: [📑 PSA Precedent Library](https://www.notion.so/34b6ecd89e598105a102c2f1595ecced).

**PSA Deals — Precedent Library field map (primary cascade).**

| PSA Deals Property | Source Fact | Type |
|---|---|---|
| Deal Name | `"[Property Short Name] ([Effective Date YYYY-MM-DD])"` | Title |
| Property Short Name | User-supplied | Text |
| Effective Date | P-046 | Date |
| Purchase Price | P-031 | Number (dollar) |
| Total SF | P-024 | Number |
| Market | Derived from P-016 city | Select |
| Property Type | User-classified from the asset description | Select |
| Jurisdiction(s) | P-027 (+ P-028 if dual) | Text |
| Buyer Entity | P-001 (+ P-002 noted if inconsistent) | Text |
| Seller Entity | P-010 | Text |
| Buyer's Counsel | P-007 + P-008 | Text |
| Seller's Counsel | P-014 | Text |
| Escrow Agent | P-036 | Text |
| Deal Stage | Derived from deal state (Under LOI / PSA Signed / Under DD / Clear to Close / Closed / Terminated) | Select |
| Env Buyer Cap | P-039 | Number (dollar) |
| Env Seller Credit | P-040 | Number (dollar) |
| Env Termination Threshold | P-041 | Number (dollar) |
| General Reps Survival | P-079 | Text |
| Environmental Reps Survival | P-080 | Text |
| Fundamental Reps Survival | P-081 | Text |
| Closing Cost Allocation | P-042 | Select |
| Title Cost Allocation | P-043 | Select |
| Seller 1031 Reserved | P-075 | Checkbox |
| Buyer 1031 | P-076 | Checkbox |
| Memorandum Recording Right | P-147 | Select |
| Foreclosure-Adjacent | True if any P-087+ row is a foreclosure-type | Checkbox |
| Lis Pendens Present | True if any P-087+ row is a Lis Pendens type | Checkbox |
| Open Code Violations (Count) | Count of P-087+ rows with category = municipal code enforcement | Number |
| Fact Table URL | Link to `YYYYMMDD_[Short]_PSA-Facts_v##.xlsx` | URL |
| PSA PDF URL | Link to executed PSA PDF | URL |
| Pipeline Link | Relation to Acquisition Pipeline Tracker record for same deal | Relation |
| Notes | Deviations from ORA standard, negotiation context, flagged ambiguities | Text |

**PSA Facts — Master row shape (one row per fact).**

Use the Fact # from `psa-fact-schema.md` as the stable identifier. Title format: `"[Property Short Name] — P-###"`. Required properties: Deal (relation), Fact #, Section, Field, Value, PSA Source, Confidence, Flag, Notes. Use `Value (Number)` for numeric facts and `Value (Date)` for date facts to enable sort/filter. Leave rollup columns (`Market (rollup)`, `Effective Date (rollup)`, etc.) untouched — they auto-populate from the Deal relation.

**Acquisition Pipeline Tracker update (secondary — lightweight).**

After PSA Deals is populated, update the Pipeline record with only the fields the pipeline already tracks:

| Pipeline Tracker Field | Source |
|---|---|
| Stage | "Under Contract" or "Due Diligence" per deal state |
| PSA Status | "Executed" |
| Purchase Price | P-031 |
| Total SF | P-024 |
| Key Attorney | P-008 (Buyer's counsel) |
| Target Close Date | P-060 |
| Environmental | Derived — "Phase 2 In Progress" / "Phase 2 Complete" per DD state |
| Notes | Deviations + critical flags summary |

The Pipeline Link two-way relation means the Pipeline record now displays a `PSA Deals Record` back-reference — no separate update needed on that property.

**MCP calls (templates).** Execute in this order.

### A. Upsert the PSA Deals row (primary cascade target)

```
notion-search query="[Property Short Name]" data_source_url="collection://d5cd671d-ba2b-4635-a011-cf5303574408"
  → if exists: notion-update-page page_id=<found> command="update_properties" properties={...per Field Map above...}
  → if not exists: notion-create-pages parent={type:"data_source_id", data_source_id:"d5cd671d-ba2b-4635-a011-cf5303574408"} pages=[{properties:{...}}]
  → capture the returned page URL — this is the "Deal" relation target for every Fact row below
```

### B. Batch-create PSA Facts rows (up to 100 per call)

```
notion-create-pages
  parent={type:"data_source_id", data_source_id:"af3dc100-38e5-46ab-8d40-22c0e880e79a"}
  pages=[
    {properties: {"Fact ID": "[Short Name] — P-001", "Deal": "<deal page URL>", "Fact #": "P-001",
                  "Section": "Parties", "Field": "...", "Value": "...",
                  "PSA Source": "...", "Confidence": "High", "Flag": "None"}},
    ... up to 100 rows per call — batch remaining facts in subsequent calls ...
  ]
```

Rollups (Market, Effective Date, Purchase Price, Property Type) auto-populate from the Deal relation — do not set them on the Facts row.

### C. Link PSA Deals → Acquisition Pipeline Tracker (two-way)

```
notion-search query="[Property Short Name]" data_source_url="collection://bcfe4a03-7e61-4ac1-a0bb-c44174fa138b"
  → notion-update-page page_id=<PSA Deals row> command="update_properties"
       properties={"Pipeline Link": "<Pipeline record URL>"}
  → the two-way relation auto-populates the reverse "PSA Deals Record" on the Pipeline record
```

### D. Tenant Database updates (one record per in-place tenant)

```
notion-search query="[Tenant Name]" data_source_url="collection://8dbbaec0-..."
  → per tenant: notion-update-page OR notion-create-pages
```

**Batch size discipline.** Notion MCP `notion-create-pages` supports up to 100 pages per call. A typical PSA produces 125–155 fact rows — split into 2 calls. Do not retry a failed batch without deduplicating; use `notion-search` + `Fact #` filter to detect partial writes.

**QC check.** After the cascade runs, fetch the updated Notion records via `notion-fetch` and diff against the Fact Table. Any field that failed to update is a defect.

---

## Cascade execution order

When the user says "cascade everything," execute in this order. Each step may depend on the prior.

1. **PSA Deals (upsert)** — canonical deal-level row, created first because every downstream reference points to its URL.
2. **PSA Facts (batch create)** — up to 100 rows per call; typical PSA = 2 calls. Rollups populate automatically once the Deal relation is set.
3. **Acquisition Pipeline Tracker (update)** — lightweight Stage / PSA Status / Close Date update; `Pipeline Link` relation auto-reverses onto the pipeline record.
4. **DD Checklist Workbook (cascade instruction pack)** — re-keys all deal assumptions and derived dates.
5. **Title Instructions Letter** — sent to escrow agent.
6. **Rent Roll** — refreshed from Exhibit D via the `rent-roll-qc` skill.
7. **IC Memo** — updated last because it summarizes everything above.
8. **Underwriting Model** — run in parallel with (4) if model is already built.

Do not cascade to a target that does not yet exist. If the user asks for a DD workbook cascade but has no DD workbook, generate the workbook first via the `deal-execution` skill, then cascade.

**Idempotency.** If the PSA Deals row for this deal already exists (detected via `Deal Name` match in step 1), update it rather than create a duplicate. If PSA Facts already exist for the deal, do not append duplicates — instead update existing rows by matching on `Fact #` + `Deal` relation.

---

## Email summary (final step)

After the full cascade, draft an email to the user (`ggoldberg@oxfordra.net` ONLY, per ORA routing canon — the sole egoldberg cc exception is the ora-am-brief Daily Brief, which does not apply here) summarizing:

1. Which targets were cascaded (numbered list).
2. Any facts flagged Ambiguous / Conflicting / Missing that the user must resolve.
3. The location of the Fact Table and every cascade output file (use computer:// links when in Cowork).
4. The next recommended action (e.g., execute the DD Excel prompt; send the title letter to Newmark).

Use the `communication-intelligence` skill for the email draft so the tone matches ORA's institutional register.
