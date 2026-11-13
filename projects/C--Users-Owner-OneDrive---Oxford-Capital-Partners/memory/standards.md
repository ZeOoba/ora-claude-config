---
name: standards
description: ORA institutional standards — financial modeling conventions + communication patterns/tone by audience. Merged from reference_financial + reference_communication.
metadata: 
  node_type: memory
  type: reference
  originSessionId: 8ffab475-017d-4acd-9f70-f4496936d089
  modified: 2026-07-27T13:17:19.935Z
---

# ORA Standards — Financial Conventions & Communication

Merged 2026-06-03 from reference_financial.md + reference_communication.md.

---

## PART A — Financial Modeling Conventions

### Hard rules (canonical per CLAUDE.md / investment criteria)
- **DSCR ≥ 1.25× — hard acquisition governor** (corrected from 1.75 → 1.25 on 2026-06-03, G5).
- **LTV ceiling: 40% portfolio-aggregate** self-imposed max (Hard Invariant 4). **Per-property refi-sizing ceiling: LESSER of 65% LTV and 1.25× DSCR** — a distinct, non-conflicting second-level governor (Gabriel-ratified 2026-07-11, reaffirmed in-turn 2026-07-16): a single property may refi to 65% LTV post-close while the portfolio in aggregate stays under the 40% ceiling. Primary text: `acquisition-underwriting/SKILL.md` (v3.8+, restated v4.0 :55/:117/:221/:343). Do not conflate the two — a per-property figure is not a portfolio-aggregate drift and vice versa.
- Every deal model: NOI, Cap Rate, Yield on Cost, Levered/Unlevered IRR, Equity Multiple, DSCR.
- Every acquisition: replacement-cost analysis against the ratified RCT v03 per-market band (basis floor computes at band LOW; vintage ramp per the private RCT file).
- Rent comps denominated **$/SF NNN** unless otherwise specified.
- All models include **sensitivity tables**.
- **10-year** projection horizon, fully dynamic assumptions.

### Default assumptions (starting points; Gabriel may override per deal — update when validated)
| Assumption | Default | Last Validated |
|-----------|---------|---------------|
| Vacancy/Credit Loss | **5.0%** stabilized (unanimous: 754, 511, 470, 275; "ORA structural convention") | 2026-07-09 |
| Annual Rent Escalation | **3.0%/yr** (unanimous: 754, 511, 470, 275; "ORA contractual minimum 3%"; DG single-store uses contractual 10%/5-yr option steps instead) | 2026-07-09 |
| Expense Growth | **3.0%/yr** (754, 511, 275, DG insurance/reserves; DG CAM specifically 2.0%) | 2026-07-09 |
| TI Allowance (new) | **~$5/SF** blended, single figure — range $3–$6/SF (470 $3 · 754 $5 · 511 $6); models do NOT split new/renewal; MTM→NNN capture deals (275) model $0 TI | 2026-07-09 |
| TI Allowance (renewal) | not modeled separately — same single blended TI/SF applies (no new/renewal split in any model) | 2026-07-09 |
| Leasing Commissions (new) | **Legitimately deal-structure-dependent — reach for $2/SF flat first.** $2/SF flat is the ORA default for stabilized multi-tenant lease-up (754, 511); a 6%-of-term-rent basis is acceptable where a broker-driven leasing assumption is more realistic (470 — at ~$9/SF NNN this is ≈$2.70/SF over 5 yrs, modestly richer, not a wild divergence); MTM→NNN capture deals (275) model $0 LC. **Gabriel-ratified 2026-07-17** (explicit decision, not staff default): keep as documented divergence — not reconciled to one number, both conventions are real and retained. Not split new/renewal in any model. | 2026-07-17 |
| Leasing Commissions (renewal) | not modeled separately — same LC basis applies | 2026-07-09 |
| CapEx Reserve $/SF | **$0.15/SF/yr ORA convention** (470, 275) — **CHANGED FINDING 2026-07-17:** DG's reserve cell (`Inputs!B44`) now reads **$0.20/SF**, not the $0.15 this row cited as of 2026-07-09 — re-verified live via `openpyxl(data_only=True)`, drift confirmed, not a fabrication. DG moves from the "$0.15 unanimous" group to join 511 as a $0.20 outlier; 754 remains uniquely at $0.30. **Flagged for Gabriel's acknowledgment — not silently absorbed.** One-time initial/deferred-maintenance reserves are deal-specific, excluded. | 2026-07-17 |
| Exit Cap Rate Spread (vs entry) | **Confirmed closed as market-absolute, ratified 2026-07-17.** Not modeled as a spread in any of the 5 workbooks — exit cap set as market **absolute** from acq-underwriting Exit Cap table: **7.75% Columbus-default** (511, 470, 275) · **7.5% Cincinnati** (DG) · **8.0%** for older multi-tenant flex (754). Going-in cap cells remain uncached live formulas in every workbook (re-confirmed 2026-07-17, not re-derived via recalc this pass — the structural "not a spread anywhere" finding is sufficient to close without fabricating a derived number; optional recalc-based derivation remains available as a follow-up if the color evidence is ever wanted). See source-basis note | 2026-07-17 |
| Replacement Cost Range | **Ratified RCT v03 (2026-07-14)**: Columbus POINT [RCT-private] (band [RCT-private]–[RCT-private]) · Cincinnati [RCT-private] ([RCT-private]–[RCT-private]) · KC [RCT-private] · Indianapolis [RCT-private] · Mid-Atlantic [RCT-private] — full 9-market table: acquisition-underwriting SKILL.md RCT v03 = platform `config/replacement-cost.v3.json` (PR #210; drift-pinned by tests, PR #214). See note re the June-10 workbook naming collision | 2026-07-16 |

#### Source basis — default assumptions (re-verified 2026-07-17 against live source cells; validated 2026-07-09)
Pulled from actual ORA underwriting models (hardcoded input cells; computed cells in these workbooks are stored as live formulas, not cached values — going-in cap rates therefore could not be read, so no numeric exit-minus-entry spread is asserted). Six source deals reviewed.
- **754 Old State Route 74 (Cincinnati OH)** — `C:\Users\Owner\OneDrive - Oxford Capital Partners\754 Old State\IRR Model -- 754 Old St.xlsx`, tab `754-Inputs`: vacancy 5.0% (C23) · rent escalation 3.0% (C22) · expense inflation 3.0% (C45) · TI $5/SF (C26) · LC $2/SF (C27) · replacement reserves $0.30/SF (C33) · initial CapEx reserve $50K one-time (C37) · exit cap 8.0% (C42).
- **511 Industrial Mile Rd (Columbus OH)** — `C:\Users\Owner\OneDrive - Oxford Capital Partners\Investment Candidates -- 2026\20260516_511IndustrialMile_IRRModel_v01.xlsx`, tab `511-Inputs` (carries v03 post-tour findings): vacancy 5.0% (C23) · rent escalation 3.0% (C22) · expense inflation 3.0% (C45) · TI $6/SF (C26) · LC $2/SF (C27) · replacement reserves $0.20/SF (C33) · initial CapEx reserve $500K one-time deal-specific physical-plant (C37) · exit cap 7.75% (C42).
- **470 McCormick Blvd (Columbus OH)** — `C:\Users\Owner\OneDrive - Oxford Capital Partners\Investment Candidates -- 2026\20260610_470-McCormick_Model_v03.xlsx`, tab `Inputs`: structural vacancy yr2+ 5.0% (B19) · escalation 3.0% (B17) · TI $3/SF (B20) · LC 6% of yrs 1–5 rent (B21) · reserves $0.15/SF (B39) · exit cap 7.75% "Buy Box v1.0 default" (B52) · refi value cap 7.25% (B51) · immediate repairs $60K one-time (B22). No standalone expense-inflation input (vacant/IOS reposition model).
- **DG single-store — 11850 Hamilton Ave, Cincinnati OH** — `C:\Users\Owner\OneDrive - Oxford Capital Partners\Investment Candidates -- 2026\DollarGeneral-Cincinnati_UnderwritingModel_v03.xlsx`, tab `Inputs`: insurance escalation 3.0% "ORA convention – 3% minimum" (B40) · CAM escalation 2.0% (B42) · reserve/cost escalation 3.0% (B45) · reserves **$0.20/SF (B44 — re-verified 2026-07-17, was cited $0.15 as of 2026-07-09; genuine drift, not a transcription error)** · mgmt 4% EGI (B43) · exit cap 7.5% "Cincinnati market, acq-underwriting Exit Cap table" (B57). Single-tenant NNN/modified-gross retail → no general-vacancy or TI/LC inputs; rent steps via 10%/5-yr options. NOTE: separate parked deal, **NOT** the DG 3-pack.
- **275 Old County Line Rd (Columbus OH)** — `C:\Users\Owner\OneDrive - Oxford Capital Partners\Investment Candidates -- 2026\outputs\20260612_275-OldCountyLine_IRR-Model_v04.xlsx`, tab `Inputs` (full 10-yr IRR model; projects.md's "v1.1" is the parallel `outputs\archive\ORA_ScreenModel_275-OldCountyLine_v1.1.xlsx`): economic vacancy & credit loss 5.0% "ORA structural convention" (B14) · annual rent escalation 3.0% "ORA contractual minimum 3%" (B19) · expense growth 3.0% (B20) · structural reserves $0.15/SF "ORA non-recoverable reserve" (B16) · mgmt 4% EGI (B15) · exit cap 7.75% "ORA default" (B27) · refi valuation cap 7.75% (B26) · Day-1 deferred-maintenance CapEx $400K one-time (B7) · replacement cost carried $138.73/SF, RCT v03 Columbus POINT (B36). NO TI/LC inputs — value-add is MTM→NNN mark-to-market capture (Lease-Up tab: each unit converts to $9.00/SF NNN with a 1-mo downtime that year, then 3%/yr; no TI or LC modeled on capture). NOTE: the root-folder `275 Old County Line Rd 2.0.xlsx` is a superseded back-of-envelope snapshot (single `Sheet1`, LTV 70% / rate 6.5% only) — do not cite it as the model.

**Replacement Cost Range note (SUPERSEDED 2026-07-16 — naming-collision warning):** the June-10 workbook cited below self-labels "v03" but is NOT the ratified RCT v03. The ratified table (2026-07-14, rebuilt from the C&W 2025 guide; Columbus POINT [RCT-private]) lives in acquisition-underwriting SKILL.md's RCT v03 section and the platform's `config/replacement-cost.v3.json`, and governs every screen; the workbook figures below ($138.73 Columbus) are retained only as historical context for pre-2026-07-14 models. *(Original note, refreshed 2026-07-09, superseding the stale $85–$120/SF figure validated 2026-04-09:)* source is `Investment Candidates -- 2026\20260610_ORA_Replacement-Cost-Table_v03.xlsx`, tab `Replacement Cost Table v03` — Columbus row 6 (POINT $138.73, LOW $124.86, HIGH $152.60) and Cincinnati row 7 (POINT $137.20, LOW $123.48, HIGH $150.92); both recomputed by hand from the live input cells (hard cost, soft %, dev profit %, financing %, land $/ac, FAR, ±10% band) since the sheet's own POINT/LOW/HIGH cells are live formulas, not cached values. Table is marked **PROVISIONAL** in its own header pending insurance SOVs/appraisals; next scheduled refresh 2026-09-10 (no v04 exists yet — confirmed only v02/v03 exist, and v02→v03 held 0.0% change on every input). **Outlier flagged, not folded into the range:** 754 Old State Route 74's model (`754-Inputs` C18) carries a hardcoded $160/SF — about 17% above the RCT Cincinnati POINT and 6% above its HIGH band — with no per-cell source note and unchanged since v01 (2026-05-16, predates both RCT versions). Gabriel should confirm whether this is a legitimate asset-specific quote or a stale input that should be reconciled to the RCT methodology.

**Gaps / flags (no value fabricated for any of these):**
- **2040 S Hamilton Rd (Columbus OH)** — NO underwriting model exists (LOI .docx only; projects.md: "UNSCOREABLE — no underwriting package exists"). Zero assumptions pulled. **Gabriel-ratified 2026-07-17** (explicit decision, not staff default): stays permanent N/A in this table — this table distills conventions from completed models, and a model-less deal contributes nothing to fabricate. Whether 2040 *should* be underwritten is a separate pipeline decision, not a table residual.
- **DG 3-pack OH (New Lebanon / Columbus-Lockbourne / Fayetteville)** — NO Excel model; it was a `verified-deal-recon` PASS at pre-screen (deal_dg_portfolio_oh_2026-06.md). The only DG model on disk is the separate 11850 Hamilton Ave single-store deal above.
- **TI & LC new-vs-renewal split** — none of the six models split TI or LC into new vs renewal; each carries one blended figure. The "renewal" rows are "not modeled separately," not a found value.
- **Leasing-commission convention diverges — CLOSED 2026-07-17, documented not reconciled.** $/SF flat (754, 511) vs % of term rent (470); retained as legitimate deal-structure-dependent conventions rather than averaged into one number — see the table row above.
- **Exit-cap "spread vs entry" — CLOSED 2026-07-17, confirmed market-absolute.** Not parameterized as a spread anywhere; exit cap is set as a market absolute from the acquisition-underwriting Exit Cap table. Going-in caps remain formula cells not cached in the workbooks, so no numeric spread is asserted — this convention itself (absolute, not relative) is the closure, not a residual.

### Model structure preferences
- **Excel (.xlsx) is the single source of truth** — never build financial models in markdown or other formats.
- Assumptions on a dedicated tab; inputs color-coded (blue = input, black = calculated).
- Summary tab with key-metrics dashboard.
- Sensitivity tables on NOI, exit cap, and interest rate.
- Cash flow waterfall: gross potential rent → vacancy → EGI → expenses → NOI → debt service → BTCF.

### QC verification method (added 2026-07-11)
- Running `recalc.py` (or any formula-recalc script) confirms formulas evaluate — it does NOT confirm they evaluate over the correct ranges. Recalc passing is not sufficient QC on its own.
- **Standing habit:** before presenting any headline number (Scorecard Quality/Economics/Combined, NOI, cap rate, IRR, DSCR, equity multiple), open the workbook with `openpyxl.load_workbook(path, data_only=True)` and eyeball every headline cell against its component inputs — confirm subtotal/summary formulas sum the intended row ranges, not just that they return a number.
- **Incident (2026-07-11):** QC caught the acquisition-underwriting Scorecard's subtotal formulas summing the wrong row ranges, inflating Combined from 57 to 73 — `recalc.py` alone had passed it. Deal not identified in the carried-over session note — confirm no deliverable showing Combined=73 was already presented before treating this as closed. Detail: event_log.md.

### Entity / debt conventions
- QuickBooks Desktop manages ~20 LLC company files; each property has its own LLC entity; debt service calculated per-entity.
- **Debt service / DSCR excludes internal (intercompany) loans — Gabriel-confirmed 2026-07-27.** Only external third-party borrower debt counts toward debt-service-coverage calculations. Internal/intercompany positions (e.g. Master Workbook's "Internal Loan Journals" — 2203 FROM EGFLLC, Muirkirk-to-EG(Oxford), 3883 from Oxford, 1100 From Fenton) are intercompany accrual, not a real external obligation requiring coverage, and should never be added into a DSCR or debt-service figure alongside external debt. They do still count toward **Total Debt** balance/leverage figures (external + internal), which is a distinct metric from DSCR. Applies wherever DSCR or "debt service" is computed — Master Workbook ingest, acquisition-underwriting, disposition-analysis, debt-management.

---

## PART B — Communication Patterns & Tone

### Brand voice (all external)
Professional, understated, institutional. No superlatives — let the numbers speak. Precise, authoritative, unhurried.

### By audience
**Tenants** — professional, direct, respectful. Reference specific lease provisions (section numbers); include relevant dates/amounts/deadlines. Delinquency escalation: reminder → formal notice → demand → legal referral (progressive tone). Renewals: lead with value proposition, present terms clearly, include response deadline. Always specify the correct landlord entity. Formats: email body text AND .docx letter on ORA letterhead.

**Brokers** — collegial but efficient. Lead with criteria match/mismatch. Numbers-forward: SF, price, cap rate, $/SF before qualitative. **Document intake (added 2026-07-11):** when requesting OMs/broker packages, ask for native/text-layer PDF exports. "Print to PDF" rasterized scans force vision-based page-by-page reading and measurably slow underwriting turnaround — flag this to brokers proactively, not just after receiving a scanned package.

**Transaction counsel (Philip Collins)** — formal, clause-specific. Reference PSA/lease section numbers. Flag severity: CRITICAL / MAJOR / MINOR. Categorize: purchaser-favorable / neutral / seller-favorable.

**Lenders** — (pending; populate when loan communications occur).

**Internal (Eric, Gabriel)** — (pending; populate as patterns emerge).
