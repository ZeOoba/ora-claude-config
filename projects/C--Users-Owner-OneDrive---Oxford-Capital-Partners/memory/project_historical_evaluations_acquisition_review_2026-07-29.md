---
name: project-historical-evaluations-acquisition-review-2026-07-29
description: "Settlement-price + Master Workbook NOI cross-reference across 13 closed ORA acquisitions (Historical Evaluations Cowork project) — success/failure pattern, 2 confirmed LTV governor exceptions (accepted), 2 open date discrepancies."
metadata:
  node_type: memory
  type: project
  originSessionId: cowork-historical-evaluations-2026-07-29
  modified: 2026-11-10
review_by: 2027-01-29
---

# Historical Evaluations — Acquisition Price/Performance Review (2026-07-29)

Source: Cowork "Historical Evaluations" knowledge project (12 settlement statements, scanned — visually verified against original document images, not OCR text alone; 4 Capstan/CSSI cost segregation studies) cross-referenced against the ORA Master Workbook mirror's `Property NOI` and `Portfolio Summary — Internal` tabs (dated 2026-07-28, the day before this review — treat as fresh but re-verify against the live SharePoint workbook per [tech.md](tech.md) freshness canon before citing externally).

## Price vs. current mark (all 13 identified acquisitions)

| Property | Settled | Purchase Price | Est. Value (100%) | Δ | Cap Rate | CoC | LTV |
|---|---|---|---|---|---|---|---|
| 1900 N Broadway, Baltimore MD | 08/31/2015 | $1,350,000 | $5,460,000 | +304% | 6.68% | 20.3% | 0% |
| 9050 Red Branch Rd, Columbia MD | 08/27/2015 | $7,667,137 | $16,960,000 | +121% | 6.30% | 22.2% | 15.7% |
| 155 New Plant Ct, Owings Mills MD | 10/28/2016 | $1,818,750 | $6,966,690 | +283% | 6.50% | 25.2% | 0% |
| 29000 Information Lane, Easton MD | 12/22/2016 | $2,000,000 | $7,313,662 | +266% | 7.00% | — | 37.9% |
| Sepich Portfolio (8 parcels), Columbus OH | 02/01/2021 | $4,650,000 | $11,814,374 | +154% | 7.00% | 61.3% | 31.5% |
| 3540 E 5th Ave, Columbus OH | 01/20/2022 | $1,300,000 | $4,500,000 | +246% | 6.28% | — | 54.3% |
| 1100 Rarig Ave, Columbus OH | 10/06/2023 | $1,800,000 | $2,374,719 | +32% | 7.00% | 20.8% | 46.6% |
| 3034 Westerville Rd, Columbus OH | 09/19/2024 | $1,652,400 | $1,568,800 | −5% | 7.50% | 7.1% | 0% |
| 2203/2205/2207 Northwood Dr, Salisbury MD | 10/25/2024 | $4,400,000 | $4,809,606 | +9% | 8.00% | 8.7% | 0% |
| 9620 E State Rte 350, Raytown MO | 10/18/2024 | $2,000,000 | $2,000,000 | 0% | 5.42% | 5.4% | 0% |
| 3875-3883 E Livingston Ave, Columbus OH | 06/10/2025 | $925,000 | $1,314,000 | +42% | 7.50% | 9.9% | 0% |
| 401 Sunburst Hwy, Cambridge MD | 01/27/2026 | $950,000 | $961,875 | +1% | 8.00% | 8.1% | 0% |
| 7658 Fishel Dr N, Dublin OH | 01/29/2026 | ~$1,765,000 | $1,863,273 | +6% | 5.50% | 5.8% | 0% |

Portfolio totals (Oxford share, incl. Persimmon Tree residence): $58.7M value, $3.85M NOI, 6.78% blended cap rate, 4.31x DSCR, 17.8% CoC, 6.1-yr avg hold. Reconciles closely to the ~$60M AUM figure in firm.md.

## Success pattern

Strongest driver of outsized returns is long-hold value-add redevelopment, not the acquisition itself. The two 2015-vintage deals (1900 N Broadway, 9050 Red Branch Rd — closed 4 days apart, both 50% JV) show depreciable-basis growth of 3.1x and 1.7x respectively per their May 2024 Capstan cost segregation studies, consistent with the 3-4x value marks above. Sepich Portfolio (61.3% CoC) is the standout single case study by cash-on-cash return.

## Watch list (not yet "failures" — both under 2 years old)

Raytown MO (5.42% cap rate/CoC, lowest in the book; 92% occupied, the only sub-100% asset) and 3034 Westerville Rd (only asset marked below purchase price, −5%; lowest CoC at 7.1%). [FORECAST] if these don't inflect within another 12-18 months given the multi-year lag pattern seen in the 2015-vintage deals, route to disposition-analysis.

## LTV governor — 2 confirmed exceptions, RULED ACCEPTED (Gabriel, 2026-07-29 in-session)

3540 E 5th Ave (54.3% LTV, Park National) and 1100 Rarig Ave (46.6% LTV, internal Fenton→Oxford Capital→1100 Rarig chain) both breach the 40% Hard Invariant 4 ceiling. Gabriel: log with rationale, accept — both are strong performers. **Open follow-up:** check whether these are the same 2 properties [project_governor_ltv_remediation_2026-07-24.md](project_governor_ltv_remediation_2026-07-24.md) (PR #233) newly surfaced after fixing 2 false-clearance defects in the scoring code — not verified this session.

## Date discrepancies — RESOLVED 2026-11-10 (verified against Notion Property Register)

1. **29000 Information Lane** — settlement statement: 12/22/2016 close, $2,000,000, seller Easton Technology Phase I LLC. Property NOI sheet: Acq Date 1/1/2021, equity invested **−$800,000** (implies cash-out refi). Verify against Acquisition Pipeline (bcfe4a03) before citing either date externally.
   - **RESOLVED:** Property Register row ORA-P-2 (Notion `39b6ecd8…feb9d`, CORRECTIONS 2026-09-19) sets Purchase Date 2016-12-22, $2,000,000; SDAT transfer 2016-12-27; acquired as a 1031 replacement (IPX letter 2016-12-02). The 1/1/2021 workbook date is wrong. The −$800,000 equity figure is still unexplained (the "cash-out refi" reading is not confirmed; see [disposition-ledger.md](disposition-ledger.md) row, still INFERRED).
2. **Sepich Portfolio** — settlement statement: 02/01/2021 close, $4,650,000. Property NOI sheet: Acq Date 3/16/2021 (6-week gap, larger than typical disbursement lag — possible second tranche).
   - **RESOLVED:** Property Register row ORA-P-6 (Notion `39b6ecd8…25067`, CORRECTIONS 2026-09-21): settlement 2021-02-01 is correct; 3/16/2021 was a GIS transfer-processing date (deeds recorded 3/17/2021). One closing, two sellers (Sepich Family LP $3,650,000 + Sepich Family II LP $1,000,000). Since split into two Register rows (Banwick + Morrison / Zettler + Sepich Ln + 4595-4601 E 5th). Open there, not here: $61,200 IPX boot check and the unrecorded $1,430,000 Fenton Street LLC loan (OI-337).

## Resolved, not an error: 1100 Rarig rent/SF

Property NOI showed $12.20/SF (= Gross Income ÷ SF); standalone rent roll computed $8.97/SF (base contract rent ÷ SF, 12 tenants). Gabriel confirmed (2026-07-29): these are modified-gross leases — tenant responsible for utilities + opex increases over base year — so $8.97/SF is base rent and $12.20/SF is total collected revenue incl. above-base reimbursements. Both correct; not a data-quality issue.

## Minor correction

Angola Road entity (3034 Westerville Rd, Columbus OH) is **"5242 Angola Road, LLC"** — confirmed by direct visual read of the ALTA settlement statement; an initial OCR pass misread it as "8242." Not cross-checked against `ORA_Property-LLC-Signature-Roster_v01.md` this session — that file lives in the non-Claude OneDrive business folder and needs Gabriel's write-permission per rules.md §1; flagging here instead.

## Sources
12 settlement statements + 4 Capstan/CSSI cost segregation studies (Historical Evaluations Cowork knowledge project, files not individually named — content identified by property address/entity), ORA Master Workbook mirror `Property NOI` + `Portfolio Summary — Internal` tabs (dated 2026-07-28).
