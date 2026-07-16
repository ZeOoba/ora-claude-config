---
name: standards
description: ORA institutional standards — financial modeling conventions + communication patterns/tone by audience. Merged from reference_financial + reference_communication.
metadata: 
  node_type: memory
  type: reference
  originSessionId: 8ffab475-017d-4acd-9f70-f4496936d089
---

# ORA Standards — Financial Conventions & Communication

Merged 2026-06-03 from reference_financial.md + reference_communication.md.

---

## PART A — Financial Modeling Conventions

### Hard rules (canonical per CLAUDE.md / investment criteria)
- **DSCR ≥ 1.25× — hard acquisition governor** (corrected from 1.75 → 1.25 on 2026-06-03, G5).
- **LTV ceiling: 40%** self-imposed max.
- Every deal model: NOI, Cap Rate, Yield on Cost, Levered/Unlevered IRR, Equity Multiple, DSCR.
- Every acquisition: replacement-cost analysis ($85–$120/SF range).
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
| Leasing Commissions (new) | **DIVERGENT convention**: $2/SF flat (754, 511) vs 6% of yrs 1–5 rent (470); not split new/renewal; MTM→NNN capture deals (275) model $0 LC | 2026-07-09 |
| Leasing Commissions (renewal) | not modeled separately — same LC basis applies | 2026-07-09 |
| CapEx Reserve $/SF | **$0.15/SF/yr** — clear ORA convention (470, DG, 275 all $0.15, all labeled "ORA convention/reserve"); higher outliers 511 $0.20 · 754 $0.30. One-time initial/deferred-maintenance reserves are deal-specific, excluded | 2026-07-09 |
| Exit Cap Rate Spread (vs entry) | Not modeled as a spread — exit cap set as market **absolute** from acq-underwriting Exit Cap table: **7.75% Columbus-default** (511, 470, 275) · **7.5% Cincinnati** (DG) · **8.0%** for older multi-tenant flex (754). See source-basis note | 2026-07-09 |
| Replacement Cost Range | **$123–$153/SF** (RCT v03: Columbus POINT $138.73, band $124.86–$152.60; Cincinnati POINT $137.20, band $123.48–$150.92) — see note | 2026-07-09 |

#### Source basis — default assumptions (validated 2026-07-09)
Pulled from actual ORA underwriting models (hardcoded input cells; computed cells in these workbooks are stored as live formulas, not cached values — going-in cap rates therefore could not be read, so no numeric exit-minus-entry spread is asserted). Six source deals reviewed.
- **754 Old State Route 74 (Cincinnati OH)** — `C:\Users\Owner\OneDrive - Oxford Capital Partners\754 Old State\IRR Model -- 754 Old St.xlsx`, tab `754-Inputs`: vacancy 5.0% (C23) · rent escalation 3.0% (C22) · expense inflation 3.0% (C45) · TI $5/SF (C26) · LC $2/SF (C27) · replacement reserves $0.30/SF (C33) · initial CapEx reserve $50K one-time (C37) · exit cap 8.0% (C42).
- **511 Industrial Mile Rd (Columbus OH)** — `C:\Users\Owner\OneDrive - Oxford Capital Partners\Investment Candidates -- 2026\20260516_511IndustrialMile_IRRModel_v01.xlsx`, tab `511-Inputs` (carries v03 post-tour findings): vacancy 5.0% (C23) · rent escalation 3.0% (C22) · expense inflation 3.0% (C45) · TI $6/SF (C26) · LC $2/SF (C27) · replacement reserves $0.20/SF (C33) · initial CapEx reserve $500K one-time deal-specific physical-plant (C37) · exit cap 7.75% (C42).
- **470 McCormick Blvd (Columbus OH)** — `C:\Users\Owner\OneDrive - Oxford Capital Partners\Investment Candidates -- 2026\20260610_470-McCormick_Model_v03.xlsx`, tab `Inputs`: structural vacancy yr2+ 5.0% (B19) · escalation 3.0% (B17) · TI $3/SF (B20) · LC 6% of yrs 1–5 rent (B21) · reserves $0.15/SF (B39) · exit cap 7.75% "Buy Box v1.0 default" (B52) · refi value cap 7.25% (B51) · immediate repairs $60K one-time (B22). No standalone expense-inflation input (vacant/IOS reposition model).
- **DG single-store — 11850 Hamilton Ave, Cincinnati OH** — `C:\Users\Owner\OneDrive - Oxford Capital Partners\Investment Candidates -- 2026\DollarGeneral-Cincinnati_UnderwritingModel_v03.xlsx`, tab `Inputs`: insurance escalation 3.0% "ORA convention – 3% minimum" (B40) · CAM escalation 2.0% (B42) · reserve/cost escalation 3.0% (B45) · reserves $0.15/SF "ORA convention" (B44) · mgmt 4% EGI (B43) · exit cap 7.5% "Cincinnati market, acq-underwriting Exit Cap table" (B57). Single-tenant NNN/modified-gross retail → no general-vacancy or TI/LC inputs; rent steps via 10%/5-yr options. NOTE: separate parked deal, **NOT** the DG 3-pack.
- **275 Old County Line Rd (Columbus OH)** — `C:\Users\Owner\OneDrive - Oxford Capital Partners\Investment Candidates -- 2026\outputs\20260612_275-OldCountyLine_IRR-Model_v04.xlsx`, tab `Inputs` (full 10-yr IRR model; projects.md's "v1.1" is the parallel `outputs\archive\ORA_ScreenModel_275-OldCountyLine_v1.1.xlsx`): economic vacancy & credit loss 5.0% "ORA structural convention" (B14) · annual rent escalation 3.0% "ORA contractual minimum 3%" (B19) · expense growth 3.0% (B20) · structural reserves $0.15/SF "ORA non-recoverable reserve" (B16) · mgmt 4% EGI (B15) · exit cap 7.75% "ORA default" (B27) · refi valuation cap 7.75% (B26) · Day-1 deferred-maintenance CapEx $400K one-time (B7) · replacement cost carried $138.73/SF, RCT v03 Columbus POINT (B36). NO TI/LC inputs — value-add is MTM→NNN mark-to-market capture (Lease-Up tab: each unit converts to $9.00/SF NNN with a 1-mo downtime that year, then 3%/yr; no TI or LC modeled on capture). NOTE: the root-folder `275 Old County Line Rd 2.0.xlsx` is a superseded back-of-envelope snapshot (single `Sheet1`, LTV 70% / rate 6.5% only) — do not cite it as the model.

**Replacement Cost Range note (refreshed 2026-07-09, superseding the stale $85–$120/SF figure validated 2026-04-09):** source is `Investment Candidates -- 2026\20260610_ORA_Replacement-Cost-Table_v03.xlsx`, tab `Replacement Cost Table v03` — Columbus row 6 (POINT $138.73, LOW $124.86, HIGH $152.60) and Cincinnati row 7 (POINT $137.20, LOW $123.48, HIGH $150.92); both recomputed by hand from the live input cells (hard cost, soft %, dev profit %, financing %, land $/ac, FAR, ±10% band) since the sheet's own POINT/LOW/HIGH cells are live formulas, not cached values. Table is marked **PROVISIONAL** in its own header pending insurance SOVs/appraisals; next scheduled refresh 2026-09-10 (no v04 exists yet — confirmed only v02/v03 exist, and v02→v03 held 0.0% change on every input). **Outlier flagged, not folded into the range:** 754 Old State Route 74's model (`754-Inputs` C18) carries a hardcoded $160/SF — about 17% above the RCT Cincinnati POINT and 6% above its HIGH band — with no per-cell source note and unchanged since v01 (2026-05-16, predates both RCT versions). Gabriel should confirm whether this is a legitimate asset-specific quote or a stale input that should be reconciled to the RCT methodology.

**Gaps / flags (no value fabricated for any of these):**
- **2040 S Hamilton Rd (Columbus OH)** — NO underwriting model exists (LOI .docx only; projects.md: "UNSCOREABLE — no underwriting package exists"). Zero assumptions pulled.
- **DG 3-pack OH (New Lebanon / Columbus-Lockbourne / Fayetteville)** — NO Excel model; it was a `verified-deal-recon` PASS at pre-screen (deal_dg_portfolio_oh_2026-06.md). The only DG model on disk is the separate 11850 Hamilton Ave single-store deal above.
- **TI & LC new-vs-renewal split** — none of the six models split TI or LC into new vs renewal; each carries one blended figure. The "renewal" rows are "not modeled separately," not a found value.
- **Leasing-commission convention diverges** — $/SF flat (754, 511) vs % of term rent (470); left unreconciled rather than averaged.
- **Exit-cap "spread vs entry"** — not parameterized as a spread anywhere; exit cap is set as a market absolute from the acquisition-underwriting Exit Cap table. Going-in caps are formula cells not cached in the workbooks, so a numeric spread was not derivable without fabrication.

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
