---
name: disposition-ledger
description: "One row per realized post-acquisition lifecycle event for an OWNED asset — ACQUIRED (closing), HOLD ruling, refinance/cash-out, 1031 exchange, partial-interest transfer, full sale, loan payoff. Companion to disposition-analysis skill; distinct from deal-decision-ledger.md, which covers PRE-acquisition pipeline decisions (PASS/SKIP/DROP/PARK/CLOSE) only. Scaffolded 2026-07-29 per Gabriel's request, after filing acquisition data into deal-decision-ledger.md was correctly flagged as a schema mismatch."
metadata:
  node_type: memory
  type: project
  originSessionId: cowork-historical-evaluations-2026-07-29
  modified: 2026-07-29
---

# Disposition & Exit Ledger

Companion to [deal-decision-ledger.md](deal-decision-ledger.md), which tracks PRE-acquisition pipeline decisions (PASS/SKIP/DROP/PARK/CLOSE) only. This file is the durable record of what happens to an asset AFTER it closes — every HOLD ruling, refinance/cash-out, 1031 exchange, partial-interest transfer, full disposition, or loan payoff — so long-run capital-recycling and leverage decisions compound over time instead of living only in scattered per-property memos.

**Scope boundary:** a deal graduates out of deal-decision-ledger.md (CLOSED) into this file's first row at closing — an ACQUIRED row, cross-referencing the settlement statement. It then accrues one row per subsequent lifecycle event for as long as ORA holds the asset. On an eventual sale/exchange, flag the final row TERMINAL and retire the property's Property NOI row per the deal-retirement skill's checklist.

**Maintenance:** append a row whenever disposition-analysis produces a ruling (HOLD/REFI/1031/SELL), a refinance or cash-out actually closes, or a sale/exchange closes. Never delete a row — an asset that's HELD after a disposition-analysis run gets a new row at the next review, not an edit to the old one (mirrors deal-decision-ledger.md's convention; see [memory-policy.md](memory-policy.md) archive-don't-delete). disposition-analysis v1.1 (2026-07-29) now appends automatically on every ruling — see its Step 7.

## Ledger

| Date | Property | Event | Terms / Amount | Rationale | Source |
|---|---|---|---|---|---|
| 2015-08-27 | 9050 Red Branch Rd, Columbia MD | ACQUIRED | $7,667,137; existing loan assumed $4,223,949.28 + 1031 QI funds $2,989,428.37 | Baseline acquisition | Settlement statement (Muirkirk Properties LLC) |
| 2015-08-31 | 1900 N Broadway, Baltimore MD | ACQUIRED | $1,350,000 | Baseline acquisition | Settlement statement (1900 North Broadway LLC) |
| 2016-10-28 | 155 New Plant Ct, Owings Mills MD | ACQUIRED | $1,818,750; 1031 QI (Eric Goldberg Family LLC) | Baseline acquisition | Settlement statement |
| 2016-12-22 | 29000 Information Lane, Easton MD | ACQUIRED | $2,000,000; 1031 QI | Baseline acquisition | Settlement statement (29000 Information Lane LLC) |
| 2021-02-01 | Sepich Portfolio (8 parcels), Columbus OH | ACQUIRED | $4,650,000 | Baseline acquisition | Settlement statement (Fairground Village Center LLC) |
| 2022-01-20 | 3540 E 5th Ave, Columbus OH | ACQUIRED | $1,300,000; 1031 QI | Baseline acquisition | Settlement statement |
| 2023-10-06 | 1100 Rarig Ave, Columbus OH | ACQUIRED | $1,800,000, unencumbered | Baseline acquisition | Settlement statement (1100 Rarig Ave LLC) |
| 2024-09-19 | 3034 Westerville Rd, Columbus OH | ACQUIRED | $1,652,400 | Baseline acquisition | Settlement statement (5242 Angola Road LLC) |
| 2024-10-18 | 9620 E State Rte 350, Raytown MO | ACQUIRED | $2,000,000; 1031 QI | Baseline acquisition | Settlement statement |
| 2024-10-25 | 2203/2205/2207 Northwood Dr, Salisbury MD | ACQUIRED | $4,400,000; seller-financed (2900 Loch Raven LLC) | Baseline acquisition | Settlement statement (2203 Northwood LLC) |
| 2025-06-10 | 3875-3883 E Livingston Ave, Columbus OH | ACQUIRED | $925,000 | Baseline acquisition | Settlement statement |
| 2026-01-27 | 401 Sunburst Hwy, Cambridge MD | ACQUIRED | $950,000 | Baseline acquisition | Settlement statement (Fairground Village Center LLC) |
| 2026-01-29 | 7658 Fishel Dr N, Dublin OH | ACQUIRED | ~$1,765,000 | Baseline acquisition | Settlement statement / cost segregation study |
| 2026-07-09 | 1100 Rarig Ave, Columbus OH | HOLD (disposition-analysis ruling) | No transaction. Refi lever available: ~$760K tax-free at 40% LTV ceiling if liquidity needed | Unencumbered, 100% occupied, bought at bottom of replacement cost; taxable sale would price near-flat-to-basis — gain is ~40% effective tax via depreciation recapture, estate step-up forfeited | [deal_1100_rarig_disposition_2026-07.md](deal_1100_rarig_disposition_2026-07.md) |
| UNKNOWN (pre-2026-07-28) | 29000 Information Lane, Easton MD | REFI (cash-out, INFERRED — NOT YET VERIFIED) | Equity invested shows as −$800,000 in Property NOI tab (implies net cash pulled exceeds original equity); Symetra loan, balance $2,769,508, 37.9% LTV | Property NOI's Acq Date field also shows 2021-01-01 vs. the 2016-12-22 settlement date — may be dating this refi event, not the acquisition. Backfill exact date/terms from Symetra loan docs or QuickBooks before treating as fact | Property NOI tab inference only — see open discrepancy #1 in [project_historical_evaluations_acquisition_review_2026-07-29.md](project_historical_evaluations_acquisition_review_2026-07-29.md) |
| UNKNOWN (pre-2026-07-28) | 3540 E 5th Ave, Columbus OH | REFI (cash-out, INFERRED — NOT YET VERIFIED) | Equity invested shows as −$200,000 in Property NOI tab; Park National loan, 54.3% LTV (exceeds 40% governor — see event_log.md 2026-07-29, ACCEPTED) | Negative equity implies a cash-out event occurred after the 2022-01-20 acquisition; no date/terms sourced yet | Property NOI tab inference only |
| 2026-07-30 | 9620 E State Rte 350, Raytown MO | SELL via 1031 (disposition-analysis ruling) | Accept Fortierra $3.0M / 70% LTPP seller note in principle; counter coupon 5.5%→6.75–7.0% (or 3-yr balloon) + guaranty/escrows/no-junior-liens; alternative $2.85M all-cash. Note must run payable-to-QI, ORA buys note from QI with outside cash for full deferral | Effective NPV of offer $2.71–2.87M vs. ORA underwritten value $1.75–2.0M ($125k opex, 10% vacancy, 107/108 at $8/SF → NOI ≈$149k) and Gabriel's $2.5M ceiling; asset impaired (HC zoning mismatch, chronic 107/108 vacancy, gross leases, $3.74/SF opex); carryover 1031 basis makes taxable sale punitive. Colliers BOV $2.375–2.675M rejected (assumed Triple Threat in 107/108 at $10/SF — did not occur) | 2026-07-30_9620-E-350-Hwy-Disposition_DecisionMemo_v01.docx (Cowork session outputs) |

*First 13 rows backfilled 2026-07-29 from the settlement-statement price review ([project_historical_evaluations_acquisition_review_2026-07-29.md](project_historical_evaluations_acquisition_review_2026-07-29.md)); the two INFERRED refi rows are flagged, not fabricated — see that file's "Open discrepancies" section. Confirm against QuickBooks/loan docs before relying on the inferred rows for a live decision.*
