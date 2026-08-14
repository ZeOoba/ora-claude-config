---
name: project_northwood_egflc_loan_miscategorized_2026-07-27
description: "Northwood $2.8M loan — reclassified internal 08-03, REVERSED unlogged 08-09 as a duplicate; Gabriel ruled C 2026-08-10: internal debt reporting FROZEN until Eric produces the source doc. Quote external debt only."
metadata: 
  node_type: memory
  type: project
  originSessionId: ba3393eb-867c-4773-be60-0095ba1567b2
  modified: 2026-08-11T21:05:02.182Z
---

# ⚠️ CURRENT STATE (2026-08-10): internal debt reporting is FROZEN — Gabriel ruled Option C.

The status of the $2,800,000 loan against **2203-2207 Northwood Dr** (6.99%, IO, matures 2031-10-01) is **unresolved and contested**. Do not publish internal debt or Total Debt as current until **Eric produces the source document** — note, assignment, settlement statement, or the intercompany entry that created it.

**FROZEN — do not quote:**
- **Internal intercompany debt** — booked at **$4,462,463**; true figure lies in a **$2.8M band** up to **$7,262,463** if Northwood belongs in the book.
- **Total Debt** — correspondingly **$14,704,262 ↔ $17,504,262**.

**NOT frozen — fully quotable.** All of these are computed on **external** debt alone and are unaffected under either reading: external debt **$10,627,017.43** · external annual debt service $873,193.82 · gross-external LTV **18.34%** · net-external LTV **15.26%** · **DSCR 4.2644×** · portfolio value $57,951,345 · NOI $3,801,616 · cap 6.56% · cash $8,376,954 · the entire rent roll.

**✅ No governor is impaired.** The ≤40% aggregate LTV test and the ≥1.25× DSCR floor both run on external figures, so both stay live and PASS with wide headroom. This is a **reporting** constraint on one line item, not a gap in covenant or buy-box testing. Internal loans are excluded from DSCR by standing convention ([[standards]], added 2026-07-27) regardless of which bucket this loan lands in.

## How it got here

1. **2026-07-17** — the $2.8M appeared in the workbook's External sheets, entered between 13:07 and 19:43, with **no Claude Log turn recording it**.
2. **2026-07-27** — Gabriel confirmed it is **internal** (Northwood pays EGFLLC), not third-party. Ingest had to publish a same-day correction.
3. **2026-08-03** — Gabriel authorised COM writes; full reclassification applied (new `Rate_Northwood_EGFLLC`, a `Northwood FROM EGFLLC` accrual journal, PSI row 10, Loan Index internal row, external rows deleted). Both LTV cells self-corrected. A hypothesis that it duplicated `2203 FROM EGFLLC` was **tested and refuted** on evidence: that loan is the original acquisition financing, opening 12/9 at $2,757,016 against the 2024-10-03 acquisition, running continuously and never moving by more than $500k, at a **different rate (6.00% vs 6.99%) and principal ($2,757,016 vs $2,800,000)**.
4. **2026-08-05 (Turn 150)** — the journal had already vanished once with no archive record; it was rebuilt.
5. **2026-08-09 — REVERSED AGAIN, unlogged.** The journal was deleted (workbook back to **50 tabs**), PSI row 10 zeroed and status set "Paid Off", and hand-typed labels **"⚠ DUPLICATE OF ROW 6 — DO NOT USE"** added on both PSI row 10 and Loan Index row 24. **No Claude Log / Sync Queue / Archive Log entry records it** — a manual human edit. Total Debt $17,555,291 → $14,704,262; internal $7,313,492 → $4,462,463; **external unchanged**.
6. **2026-08-10** — weekly ingest caught it, filed **WBC-012**, and put options A/B/C to Gabriel. **Gabriel ruled C.**

## Why neither reading is established

**For "duplicate" (reading A):** same property, same EG Florida LLC counterparty; `Monthly Checklist` row 20 describes `2203 FROM EGFLLC` as the 2203/Northwood property loan; and critically **there is no $2,800,000 movement in any of the 16 tracked entities across all 21 months of Cash Data** — no funding event exists anywhere, which a recharacterisation of an existing balance would explain.

**Against it (reading B):** the 08-03 refutation above still holds in the live file — different rate, different principal, and `2203 FROM EGFLLC`'s journal shows no drawdown that could have produced $2.8M.

The unexplained item is the same one that has blocked this since 08-03: **a $2.8M advance with no corresponding cash movement.** That is what the source document must resolve.

## How to apply

- **Quote external debt ($10,627,017), never Total Debt or internal**, until this memory says otherwise. If a figure must be given, state the band and its cause.
- **The workbook was deliberately NOT modified for ruling C** — C is a reporting posture, and editing the model would pre-judge the question it defers (Hard Invariant 4). The workbook still reads $14,704,262 as booked; that is expected, not a defect to re-fix.
- **WBC-001 and WBC-010 are reopened by implication** — both were closed on 08-03 on the strength of the now-contested reclassification. They remain in the register's Resolved section with a pointer rather than being moved back, so the record of what was believed when stays legible.
- **WBC-011 (the 4 `#REF!` cells the deletion left behind) is FIXED** — 2026-08-10, one cell (`PSI!C10` → literal `0`), workbook back to 0 error cells, no figure moved. Do not confuse that closed item with this open one.
- **Next ingest: check whether Eric has produced the source doc or re-entered the loan before reporting any internal figure.** Do not infer the answer from whichever way the workbook currently happens to be booked — it has flipped three times.

Full record: Open Workbook Corrections register (Notion `3b16ecd8-9e59-8153-8c9e-f264e301b3ca`, WBC-012) and the [[00_system_of_record]] DSOR change log.
