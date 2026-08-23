---
name: reference-debt-scoring-oxfordnoi-basis-confirmed-correct
description: "debt-scoring.ts's DSCR/debt-yield oxfordNoi fix (9cb6169) premise CONFIRMED correct against the live Master Workbook -- debt_positions is already Oxford-share-only for the JV properties"
metadata:
  type: reference
  originSessionId: 6fc6add8-c93f-4640-9f1d-8a6aa6be1ba7
  modified: 2026-08-22T22:16:07.689Z
---

**CORRECTED same day (2026-08-22), same session.** This memory originally concluded the fix's premise was probably wrong, based only on an external loan-diligence register (`loan_terms.xlsx`) that reflects the raw legal note, not the workbook's own downstream modeling. Gabriel then supplied the actual local path to the live Master Workbook (`OneDrive - Oxford Capital Partners\eric spreadsheets\Master Excel Template Company Wide -- Oxford.xlsx`), which the M365 connector's full-workbook read had been truncating before reaching (`Loan Index`/`External Loans Summary` sit past sheet ~15 of 54; the connector's dump caps out mid-`Claude Log`). Reading it directly via the Excel MCP tool settles the question. **The original conclusion below is retracted; the corrected finding follows.**

## Confirmed finding

`oxford-command-center/server/warehouse/debt-scoring.ts` computes DSCR/debt yield as `oxfordNoi / annualDebtService` (commit `9cb6169`). The code comment's premise — "`debt_positions` carries only Oxford's own debt share on a jointly-owned property" — **is correct**, verified directly against the live workbook's `External Loans Summary` row 7 (9050 Red Branch Rd, the one real 50%-JV property with external debt) and its underlying amortization sheet:

- The amortization sheet (`9050 Red Branch Road` tab) carries **two parallel balance columns**: `F` = "Remaining Balance (**Full**)" and `G` = "**Oxford Balance (50%)**" (`=F11*Oxford_Share_9050`, a named range).
- `External Loans Summary!E7` (current balance) reads from column **G** (the halved column), not F.
- `External Loans Summary!D7` (original principal) = `='9050 Red Branch Road'!B4*0.5` — explicitly halved.
- `External Loans Summary!H7`/`I7` (interest/principal feeding `J7`, "Annual Debt Service") = `SUMPRODUCT(...)*0.5` against the amortization sheet's **full-basis** interest/principal columns — explicitly halved at the point of use.
- Row label: `B7` = `"Muirkirk Properties (NorthMarq/Symetra) — Oxford 50% share"`.
- By contrast, row 6 (3540 E Fifth Ave, 100%-owned) has **no** `*0.5` anywhere — confirming the halving is deliberate and specific to the JV property, not a blanket convention.
- The same `*0.5`-and-"Oxford 50% share"-label pattern appears on `1100 From Fenton` (row 14) and `3883 from Oxford` (row 10) too — a consistent, workbook-wide design, not a one-off.

Since `debt_positions` (which feeds `debt-scoring.ts`) is populated from this exact `External Loans Summary`/`Loan Index` layer (per `parse.ts`'s `parseLoans()`), its balance/payment figures for 9050 Red Branch **are already Oxford's 50% share** — matching `oxfordNoi` exactly. The fix is basis-consistent as originally written, not merely conservative.

## Why the earlier doubt happened

The `loan_terms.xlsx` diligence register (a title/loan-verification exercise against actual promissory notes) correctly reports the loan's **legal** original principal ($4.5M, the full facility per the Woodmen note) — that figure is accurate for its own purpose (verifying the note terms), it's just answering a different question than "what basis does the ORA financial engine use." The workbook deliberately re-bases to Oxford's economic share downstream of the legal instrument; the diligence file was never going to show that, since it wasn't reading the workbook.

## Standing proof, still true regardless

Independent of this confirmation, the fix is also provably conservative (never a false governor-clearance) purely from `ownershipPct` being bounded to `(0,1]` — see the reasoning kept below for reference, since it's still the right way to reason about any FUTURE fractionally-owned property before its workbook basis is separately confirmed:

```
postfix_DSCR = oxfordNoi / debtService = ownershipPct * correct_DSCR <= correct_DSCR
```

For 9050 Red Branch specifically this is now moot — `correct_DSCR` under the confirmed basis literally *is* `postfix_DSCR` (no gap between them) — but the proof is worth keeping for the next new JV property, where the workbook basis should be re-checked the same way rather than assumed.

Related: [[project_governor_ltv_remediation_2026-07-24]].
