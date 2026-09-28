---
name: vendor-management
description: "Two modes for ORA's vendor relationships. MANAGE (default): prequalification, scoring, RFP issuance, contract intake, performance review — trigger on vendor, contractor, RFP, prequalify, vendor score/performance, 1099, W-9, COI, MSA, concentration, rebid, onboarding/offboarding, vendor audit. QC: pre-execution defect scan of a SINGLE repeat-trade proposal or service agreement where an ORA property entity is/should be Owner — trigger on QC this vendor contract, review this proposal before I sign, contractor proposal, service agreement, should we sign this bid, or an uploaded proposal/bid. Scans 27 defects at BLOCK/HIGH/MED/LOW. Multi-bid leveling routes to capital-bid-comparison. Distinct from pma-qc, listing-agreement-qc, legal-intelligence. 18 PROPOSED QC positions, unratified. v2.1"
---

# Vendor Management

Two modes for the vendor relationship. **MANAGE** (default) owns the lifecycle —
prequalification, onboarding, RFP/rebid, performance review, concentration, COI/W-9
renewal. **QC** is the pre-execution defect gate for a **single** repeat-trade contractor
proposal or service agreement before signature. Route on intent: a lifecycle or
administrative ask is MANAGE; a request to review, QC or score one specific proposal before
signing is QC.

**Two or more proposals for the same scope is neither mode — that is
`capital-bid-comparison`.** It levels scope, code-checks each bid, and recommends an
award; the awarded bid then comes back here for QC before signature. The sequence is
fixed: **level → code-check → RFI → award recommendation → QC → signature.**

## MANAGE mode

### Scope

All vendors transacted with ORA entities: maintenance, capex contractors, professional
services (legal, accounting, brokerage, insurance), property management adjuncts, IT,
banking. Excludes LP/lender relationships.

### Triggers

Vendor prequalification, onboarding, RFP/bid solicitation, vendor performance review,
contract renewal, COI/W-9 collection, vendor scoring, rebid decision, 1099 prep, vendor
concentration audit.

### Inputs

- **Notion Vendor & Advisor Directory** — canonical vendor record.
  Wrapper `faf35e01-c3b7-4137-9407-04478180d31a` · data source
  `07dd54fd-1bc9-4555-8787-3fbd9b518abe`. Prequalification columns were added 2026-09-17;
  see the Prequalification workflow below.
- QuickBooks vendor records (Desktop, ~20 LLC files via SharePoint export) — spend,
  payment history, 1099-eligible flag
- ora-vendor-scoreboard artifact (TTM scoring)
- COI/W-9 documents in SharePoint /Vendors/[vendor]/
- Contracts and MSAs in SharePoint /Vendors/Contracts/
- Property service requests in the PM platform (per 🏢 Property Register `PM Platform`)

> **Notion ID convention.** `notion-fetch` and schema tools need the **data source** id;
> REST/CRUD paths need the **wrapper** id. The canon in User Preferences mixes the two
> without labelling them. Resolve both from the Database ID Map KB page
> (`34f6ecd8-9e59-811a-a961-f21fd2680744`) rather than assuming.

### Standard Workflows

#### Prequalification (gate — run before any award, not after)

The defect this exists to prevent: on the 2026-09-17 rooftop pair at 9050 Red Branch Rd
Unit K, **both** HVAC bidders were asked for COI, license number and W-9 *after* bidding.
Neither could have been awarded compliantly on the day the bids arrived.

1. Collect and record in the Directory: `Trade`, `License No.`, `License State`, `License
   Verified On`, `COI Carrier`, `COI Expiry`, `Addl Insured Confirmed`, `GL Per
   Occurrence`, `GL Aggregate`, `Umbrella Limit`, `Workers Comp`, `W-9 on File`, `MSA on
   File`, `Home Base`, `Service Radius (mi)`, `Counties Served`, `Emergency Response`,
   `Last Prequal Review`.
2. Verify the COI names **the ORA property entity** as additional insured — entity-specific,
   not firm-generic. A COI naming the wrong Oxford entity is a VC-1 defect wearing an
   insurance costume.
3. Check limits against ORA standards (GL $1M/$2M, umbrella where applicable) plus Workers
   Comp.
4. Set `Prequal Status`. **Bid-Only — Not Prequalified** means pricing was solicited or
   received but the file is incomplete. **No award issues against Bid-Only.** This is a
   gate, not advice.
5. **Bench coverage.** Maintain at least two prequalified vendors per critical trade per
   market. Report any county where ORA owns assets and has no prequalified bench — as of
   2026-09-17 Howard County MD has **no** HVAC bench; both bidders dispatch from Carroll
   County, ~38–40 mi out, which is a live warranty-response and service-cost issue, not a
   cosmetic one.

#### Vendor Onboarding
1. Collect W-9, COI, and references.
2. Verify COI naming ORA entities as additional insured.
3. Check insurance limits against ORA standards (GL $1M/$2M, umbrella where applicable).
4. Issue MSA from template library.
5. Create the Directory record and QuickBooks vendor entry; set `Prequal Status`.
6. Output: vendor onboarding packet (DOCX) and SharePoint folder.

#### RFP / Rebid
1. Pull current vendor cost, response time, and quality history.
2. Identify 3+ qualified alternatives from the Directory or referrals, filtered to
   `Prequal Status` = Prequalified where possible.
3. Generate RFP package (DOCX) with scope, specifications, timeline. State the required
   inclusions explicitly — permit responsibility, code-required accessories, disposal,
   commissioning — so bids arrive comparable rather than needing leveling afterwards.
4. Distribute via `communication-intelligence`.
5. Score responses on price, qualifications, references, schedule. **Two or more responses
   route to `capital-bid-comparison` for scope leveling and code-checking before scoring.**
6. Output: vendor selection memo (DOCX) with recommendation.

#### Performance Review (semi-annual)
1. Pull TTM transaction data.
2. Score on: cost vs. benchmark, response time, repeat-call rate, tenant feedback.
3. Compare to benchmarks for category.
4. Flag rebid candidates (price drift > 8% YoY OR response time > 1.5× benchmark).
5. Output: vendor scorecard (xlsx) and review memo (DOCX).

#### Concentration Audit
1. Compute: top-vendor share by category and overall.
2. Flag single-source dependencies and trades with no prequalified backup.
3. Recommend: backup vendors for critical categories.
4. Output: concentration risk memo (DOCX).

#### COI / W-9 Renewal
1. Quarterly scan of the Directory on `COI Expiry`.
2. Flag vendors with COI expiring < 60 days, and any vendor with work scheduled whose
   `Prequal Status` is not Prequalified.
3. Generate renewal request emails.

> Before 2026-09-17 this workflow could not execute: the Directory had no `COI Expiry`
> field to scan. If a scan returns nothing, confirm the column exists before reporting
> "no expiring COIs."

### Outputs (MANAGE)

- DOCX deliverables follow ORA Institutional Style Guide v1.0+
- xlsx scorecards with per-vendor and per-category views
- File naming: YYYYMMDD_[Vendor-or-Category]_[DocType]_v##.docx
- Directory updates after every interaction
- ora-vendor-scoreboard artifact refresh

### Boundaries (MANAGE)

- This skill DRAFTS vendor communications and contracts. POs and signed contracts require
  Gabriel approval.
- Termination of vendor relationships requires explicit Gabriel decision.
- 1099 issuance handled by accounting; this skill PREPARES the data only.

### Dependencies (MANAGE)

- `capital-bid-comparison` (multi-bid leveling and award recommendation)
- `capital-asset-register` (what the vendor is servicing, and its age)
- `communication-intelligence` (vendor email drafts)
- `legal-intelligence` (MSA review)
- `xlsx` (scorecard models) · `docx` (RFPs and memos)

## QC mode

Pre-execution gate for a single trade contract, contractor proposal or service agreement
where ORA (or an ORA property entity) is or should be the Owner. Run **before** signature
and **before** countersigning anything the property manager solicited — the second case is
what surfaces the wrong-party defect.

For the property management agreement itself use `pma-qc`; for brokerage listing
agreements use `listing-agreement-qc`; for ORA's own lease paper use `lease-form-qc`; for
leases, PSAs, loan documents and negotiated AIA-family construction contracts use
`legal-intelligence`.

### Why this exists

Trade paper is where ORA signs the most instruments and reads them the least. A $75,223
paving proposal is small enough to feel routine and large enough to carry a full one-sided
risk allocation, and it arrives as a marketing PDF — logo, drone photograph, warranty
matrix — which is not the shape the eye reads as a contract.

Seed document: the **Standard Paving & Concrete proposal 26-9465-1**, dated 8/28/2026, for
Technology Commons, 29000 Information Ln, Easton MD — mill patching (2,590 SY), sealcoat
(10,100 SY) and striping, $75,223. Fourteen pages, of which four are photographs. It scans
**26 of 27**.

Three findings drove the design:

1. **The binding defect was upstream of the warranty.** The question that produced this
   mode was "is the warranty standard." The one-year workmanship term is market. What was
   not market: the Purchaser named on the instrument was **Thomas Park Management**, not
   the ORA entity that owns Technology Commons — and the terms bar any non-party from
   claiming a remedy. A warranty review that never checks the party block reviews a
   warranty that runs to someone else.
2. **The largest exposures are absences.** No insurance article. No additional-insured
   status. No waiver of subrogation. No lien waiver mechanic. Nine of the 27 checks fire
   on absence, and none of them are visible to a read that starts at the price table.
3. **The marketing layer contradicts the terms layer.** A warranty matrix says cracking
   and pavement failure are covered; the terms disclaim subgrade-driven cracking and
   impose no duty to check the sub-base. On a distressed lot that is most of the failure
   modes. A merger clause plus an express anti-construction clause means the matrix will
   not save Owner.

Scanner benchmarks (v1.0, 27 checks):

| Document | Failures | Notes |
|---|---|---|
| Standard Paving 26-9465-1 (8/28/2026, as received) | **26 of 27** | 8 BLOCK · 9 HIGH · 8 MED · 1 LOW |
| A fully remediated ORA trade contract | **0 of 27** | target state · `tests/remediated_fixture.txt` |

The single pass is VC-18 governing law: Maryland law and Maryland venue for a Talbot County
asset. On a seven-state portfolio that is worth confirming, not assuming — the trade's home
form will often name its own state.

### The eighteen standing positions — PROPOSED, NOT RATIFIED

`references/standing-positions.md` carries VC-1 … VC-18. **These are drafted from the
Standard Paving review and have not been ratified by Gabriel.** Like `pma-qc`'s PM-1 …
PM-19 and unlike `listing-agreement-qc`'s ratified SP-1 … SP-16, they are a proposed canon:
apply them as the review standard, present them as recommendations, and do not describe any
of them as settled ORA policy until ratification is recorded here and in `event_log.md`.

The four that cost real money, in priority order when a markup must be shortened:

1. **VC-1 — The contracting Owner is the property entity.** Fix this before anything else.
   Every other position is worthless if the remedies run to the manager. It is also the
   cheapest ask in the document and the one a contractor will never refuse.
2. **VC-11 — Insurance is a condition precedent to mobilization.** An absence, not a
   clause. Milling machines and rollers on an occupied site with no CGL limits, no
   additional-insured status and no COI.
3. **VC-2 / VC-3 — The warranty survives contact with reality.** A five-day defect notice
   made time of the essence, plus automatic warranty forfeiture on payment timing, means
   the one-year warranty is unlikely to ever be enforceable.
4. **VC-6 / VC-7 — Price is a price.** A 30-day validity window on work that cannot be
   scheduled in 30 days, an uncapped commodity escalator, and an escalator sentence with
   the threshold figure missing.

### How to run

#### Step 1 — Automated scan

```bash
python3 scripts/vendor_qc.py <proposal.pdf|docx|txt> [more ...] [--allow-tokens] [--json]
```

Extraction, OCR fallback, and the report/CLI harness live in `ora_doc_qc.py`, shared with
`pma-qc`, `listing-agreement-qc` and `lease-form-qc`. The module is not vendored in this
skill's `scripts/` directory — `tools/package_skills.py`'s `SHARED_ROOT_DEPS` injects a copy
at packaging time so the packaged `.skill` installs and runs standalone; in a raw repo
checkout `vendor_qc.py`'s sys.path fallback resolves the repo-root `tools/` copy. Prints one
line per FAIL with severity and the standing position it enforces. Exits non-zero on any
failure or on UNREADABLE.

#### Step 2 — Trust the OCR gate

Trade proposals are frequently scanned or exported flat. Under 150 extracted words triggers
OCR fallback; still under 150 exits 2 with `UNREADABLE` and no score. **A low word count is
never a clean result.**

When the header reads `EXTRACTION ocr`, treat every *absence* finding (V07, V08, V11, V13,
V17, V19, V23, V26, V27) as **provisional** and confirm against the page images before
telling a contractor a clause is missing. Presence findings are reliable; absence findings
on OCR are not.

#### Step 3 — Answer the party question before anything else

Report, at the top of every review, before any commercial term:

1. **Who is named as Purchaser**, verbatim.
2. **Whether the ORA property entity appears anywhere** in the instrument.
3. **Whether a no-third-party-beneficiary clause bars Owner** from the remedies.
4. **What the acceptance block will actually bind** if signed as printed.

If the answer to (2) is no, the review's first recommendation is a corrected party block and
nothing else changes until it is agreed. Cross-check the entity against the ORA Master
Workbook (SharePoint, per the Notion pointer page) — never against the proposal's own
recitals or the manager's email. Note that the 🏢 Property Register's `Property Entity /
LLC` field is **empty for some properties**; an empty field is a gap to escalate, not a
blank to fill by inference.

#### Step 4 — Separate the trade-standard from the one-sided

Every trade form carries terms that are genuinely market and will not move: warranty term
length on a maintenance treatment, exclusion of acts of nature and heavy-equipment damage,
disclaimer of drainage on sub-2% grade, subgrade exclusions where no investigation was
purchased. Say so plainly. A review that flags everything trains Gabriel to ignore the
review.

The report must distinguish three tiers, in this order:

- **Non-negotiable asks** — VC-1, VC-11, VC-12, and the VC-2/VC-3 warranty mechanics. A
  contractor that refuses all four is not a counterparty for a repeat trade.
- **Priced asks** — escalator caps, price hold, phasing plan, schedule commitment. These may
  cost real money; say how much.
- **Accept and note** — genuinely standard allocations, recorded so the next review does not
  relitigate them.

#### Step 5 — Check the scope against the physical evidence

Trade proposals usually embed site photographs and a marked-up aerial. Read them against the
scope. In the seed document the photographs show alligator cracking, ponding, and multiple
failed prior patches — evidence that the priced treatment is a maintenance measure on a
failing section, which is what makes VC-15 a live issue rather than boilerplate. Where the
photographs and the scope disagree, state it.

Quantify unit pricing before commenting on total price:

```
mill patch $/SY = line total / square yards
sealcoat  $/SY = line total / square yards
striping  $/stall = line total / stall count
```

#### Step 6 — Three gates before any award

Run all three. Each exists because it was missed once. `capital-bid-comparison` runs the
same three on multi-bid work; they apply identically to a single-bid award.

1. **Prequalification.** No award against `Prequal Status` = Bid-Only. See the MANAGE-mode
   Prequalification workflow.
2. **Utility incentive — mandatory on any equipment replacement over $10,000.** Identify the
   serving utility and check the commercial prescriptive program **before** award, because
   the eligible specification must be inside the awarded scope. In BGE territory that is
   Smart Energy Savers. Record the result on the asset's `Rebate Status`. Where ORA funds the
   capital and the tenant pays the utility, say so — an incentive is often the only thing
   that makes an efficiency upgrade rational for ORA.
3. **Roof coordination — mandatory whenever any trade mobilizes onto a roof.** Not only
   roofing work: a crane set, a curb adapter, a new penetration or an HVAC change-out all
   qualify, and HVAC and roofing proposals both routinely exclude roofing. Assign in writing,
   before award, who patches and warrants the membrane at every penetration and whether the
   building's roof warranty survives. Price the roofer's attendance as a line item. A $28K
   mechanical job can void a roof warranty worth several multiples of itself. Driven by
   `Roof-Mounted` on the asset row.

#### Step 7 — Trade-file close-out

Run `references/trade-file-checklist.md`. The certificate of insurance, the W-9, and the
warranty certificate are the three routinely absent. Write the asset's nameplate, warranty
expiry and servicing vendor back to the Building Asset Register
(`capital-asset-register`) — post-completion is the last cheap moment to capture them.

#### Step 8 — Report

Order findings BLOCK → HIGH → MED → LOW, after the Step 3 party block and the Step 4
tiering. For each: the defect, the failure scenario in dollars where quantifiable, and the
exact replacement language from `references/standing-positions.md`. Close with an explicit
**execute / execute as amended / do not execute** recommendation. Deliver as DOCX per the ORA
Style Guide with the 16-point QC Gate applied.

### Scope boundaries (QC)

| Situation | Skill/mode |
|---|---|
| One repeat-trade vendor proposal or service agreement, ORA as Owner | **QC mode, this skill** |
| Two or more proposals for the same scope — leveling, code-check, award | `capital-bid-comparison` |
| The asset's age, model, remaining life, replacement pipeline | `capital-asset-register` |
| Whether the capital item belongs in the annual budget | `annual-cycle` |
| Third-party property management agreement | `pma-qc` |
| Broker listing agreement (sale or lease) | `listing-agreement-qc` |
| ORA's own lease form going to a tenant | `lease-form-qc` |
| Counterparty lease, PSA, loan doc, AIA construction contract | `legal-intelligence` |
| Rooftop solar / community solar lease | `solar-lease-underwriting` |
| Drafting the award, negotiation, or declination email | `communication-intelligence` |

### Hard rules (QC)

- This mode **reviews**. It never sends. A markup, an award, or a declination going to a
  contractor is an outbound communication to an external counterparty and requires Gabriel's
  explicit in-turn confirmation (standing invariant 1).
- **Never confirm the contracting entity from memory or from the proposal's own recitals.**
  Read the ORA Master Workbook. The whole point of VC-1 is that the document is wrong about
  who the owner is.
- Never state that a term is "standard" without saying which tier it falls in per Step 4.
  Trade-standard and one-sided both appear in every one of these forms.
- **Never compare two proposals' prices inside QC mode.** Scope leveling is a separate
  discipline with its own failure modes; route to `capital-bid-comparison`.
- This mode is not legal advice and does not substitute for counsel. Route any instrument
  with a payment bond, a lien already filed, or a live claim to `legal-intelligence` and to
  Philip Collins.
- VC-1 … VC-18 are **proposed**, not ratified. Say so in every report that cites them.

## Changelog

- **v2.1 (2026-09-17) — prequalification gate, two new gates, and multi-bid routing split out.** Added the MANAGE-mode **Prequalification** workflow against the 19 columns added to the Notion Vendor & Advisor Directory the same day (`Trade`, `Prequal Status`, license no./state/verified, COI carrier/expiry/additional-insured, GL per-occurrence and aggregate, umbrella, Workers Comp, W-9, MSA, home base, service radius, counties served, emergency response, last review). Before this the COI/W-9 Renewal workflow **could not execute** — the Directory had no `COI Expiry` field to scan, so a quarterly sweep would have returned nothing and read as clean. Added QC Step 6: the **utility-incentive gate** (>$10K equipment replacement) and the **roof-coordination gate** (any trade mobilizing onto a roof), both driven off the Building Asset Register; former Steps 6–8 renumbered to 5, 7, 8 with the bid-comparison stub removed. Step 7 now writes nameplate and warranty data back to that register. Multi-bid work routes to the new `capital-bid-comparison`; the trigger phrases "compare these bids" and bare "bid" were removed from this skill's description to end the collision, and "prequalify" added. Replaced the boundary-table row pointing at `capex-budgeting`, which **does not exist on any surface**, with `annual-cycle` (which owns the annual budget and the Nov 1 kickoff task). Recorded the Notion wrapper-vs-data-source id hazard in Inputs. Seed defect: both bidders on the 9050 Red Branch Rd Unit K rooftop pair were asked for COI, license and W-9 after bidding, and Howard County MD has no prequalified HVAC bench. No QC check, standing position, script or reference file was altered; `scripts/vendor_qc.py`, `scripts/ora_doc_qc.py`, `references/standing-positions.md` and `references/trade-file-checklist.md` are referenced unchanged.
- **v2.0 (2026-09-11) — merged the standalone `vendor-contract-qc` skill in as QC mode (ORA Automation Audit R25-8, Gabriel in-turn).** The two skills' trigger phrases collided ("vendor contract" matched both, neither named the other as a sibling) with no CLAUDE.md tie-break arbitrating the pair — the first genuine collision since Revision 24's clean sweep. Merging removes the ambiguity by construction: routing is now MANAGE-vs-QC intent, decided inside one skill, not a cross-skill guess. `scripts/`, `references/` and `tests/` moved from `vendor-contract-qc/` into this skill's directory unchanged; `tools/package_skills.py`'s `SHARED_ROOT_DEPS` key repointed from `vendor-contract-qc` to `vendor-management`. Five references in `pma-qc` (`SKILL.md` ×4, `references/standing-positions.md` ×1) repointed from `vendor-contract-qc` to `vendor-management` so nothing dangles. `vendor-contract-qc/` archived to `_archive/2026-09-11_vendor-contract-qc-merged-into-vendor-management/`. No QC logic, check, or standing position changed — routing and packaging only.
- **v1.0 (vendor-management, lifecycle-only) — initial.** MANAGE-mode workflows as built: onboarding, RFP/rebid, performance review, concentration audit, COI/W-9 renewal.
- **v1.0 (vendor-contract-qc, standalone, 2026-09-09) — initial.** 27 checks, 18 proposed standing positions, trade-file checklist, Standard Paving seed defect register. Benchmarked at 26/27 (Standard Paving 26-9465-1) and 0/27 (remediated fixture). Two checks were corrected during benchmarking after false-positiving on the remediated fixture (V13 baseline-anchor phrasing, V26 governing-law phrasing) and one after false-negativing on the seed (V27 now scopes its capacity test to the acceptance block, so "duly authorized" in the modification clause can no longer mask an unidentified contracting entity).