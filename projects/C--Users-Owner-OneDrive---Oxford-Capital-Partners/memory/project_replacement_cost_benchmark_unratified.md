---
name: project-replacement-cost-benchmark-unratified
description: "RCT v03 is ORA's SINGLE basis denominator (ratified 2026-07-14) — all-in shallow-bay, rebuilt from the C&W guide; floor = vintage ramp (private RCT file); ORA buys at a deep discount to true replacement"
metadata: 
  node_type: memory
  type: project
  originSessionId: 909eeb4c-d321-40d2-a4e2-c592aa9f393d
---

**RATIFIED 2026-07-14 (Gabriel, governor-level). THERE IS ONE BASIS DENOMINATOR: `RCT v03`.** It lives in the **`acquisition-underwriting`** skill ("Replacement Cost Table (RCT v03)" under UNDERWRITING CONVENTIONS) and is authoritative. **If you find a second denominator, it is a bug.**

**RCT v03 LOW $/SF** (basis divides by LOW): Columbus [RCT-private] · Cincinnati [RCT-private] · Kansas City [RCT-private] · Indianapolis [RCT-private] · Madison [RCT-private] `[PROXY]` · Maryland [RCT-private] · Grand Rapids [RCT-private] `[PROXY, weakest]` · Richmond [RCT-private] `[PROXY]` · Des Moines [RCT-private] `[PROXY]`.

**Basis test:** `basis $/SF = (price × 1.02 closing + CapEx + lease-up carry) ÷ FUNCTIONAL SF`, clears if ≤ `RCT LOW × (1 − vintage floor)`. **Vintage floor = linear ramp** (oldYear/oldPct → newYear/newPct: private RCT file `vintageFloor`, ~/.ora-private/rct/). Unknown year built → default to the oldest-vintage floor (conservative).

## The two things worth remembering

**1. ORA buys at ~35–40% of TRUE all-in replacement cost — a ~64% discount.** The long-standing "25–30% discount" language was **an artifact of an understated denominator, never the strategy.** Say the real number in IC memos and lender packages; it is far stronger and wholly defensible.

**2. The floor % and the denominator are a MATCHED PAIR.** Never change one without re-solving the other. Leaving the old 30% floor against RCT v03 would have set the Columbus floor at $160.76/SF — a price at which *every* buy-box candidate clears. **A floor that passes everything is not a floor.**

## Why (the history, so it isn't re-litigated)

Three denominators were tried and two discarded **in one day**:
- **The old scan constants** ($140 Midwest / $170 MD / $150 Richmond / $130 DSM) — never sourced at all.
- **C&W hard cost** — ratified in the morning on my recommendation, **retired the same afternoon.** It's *hard-cost, big-box (109,200 SF), March-2025* standing in for an *all-in, shallow-bay, 2026* figure. **My recommendation was wrong.** C&W's correct role is (a) the primary source RCT v03 is **built from**, and (b) the **coherence check** that caught RCT v02's error. It is not a benchmark.
- **RCT v02** — the doctrine ORA already had. Better instrument, but **broken**: for **5 of 9 markets its "all-in" POINT sat BELOW C&W's pure HARD cost** (Cincinnati, Indianapolis, Grand Rapids, Richmond, Des Moines). *All-in cannot be less than hard cost — it contains hard cost.* It had been scaled off a big-box baseline with the **shallow-bay premium never applied**.

**Direction of the error:** replacement understated → discounts computed too small → **ORA was too STRICT and passing on deals that clear doctrine.** Maryland ran the other way (RCT v02 priced it as the most expensive market at $165 when C&W shows Baltimore is mid-priced at [RCT-private]) → **the MD floor was too generous.**

**Net after correction:** Maryland tightens ~23% · Grand Rapids loosens ~16% · Indianapolis ~7% looser · Columbus/KC/Madison tighten modestly · Richmond/Des Moines ~flat. Re-screen of the 2026-07-14 scan: **11 of 29 priced candidates clear.**

## How RCT v03 is built (each step auditable)

`POINT = C&W hard × shallow-bay size premium × soft/profit/financing × escalation`
1. C&W hard, small tier — **SOURCED**, per metro
2. Shallow-bay premium ~+43% at 40K SF — **SOURCED**, from C&W's *own* size curve (`size^−b`, b = 0.349–0.364 fitted per metro)
3. Soft + developer profit + financing **×1.30 `[EST]`** ← **the one unsourced input.** Low end chosen deliberately so the floor is *harder* than truth, never softer.
4. Escalation ×1.0487 — **SOURCED**, Turner BCI (lowest of three indices)
5. Band ±10% ⇒ LOW = 0.90 × POINT. Coherence passes: every all-in exceeds hard cost at ~1.95×.

## Open

- **The ×1.30 multiplier is the last `[EST]`.** **One email to a GC per core market** — *"all-in $/SF to build a 30–50K SF Class B/C shallow-bay shell"* — retires it, validates the shallow-bay premium, **and** settles the PEMB-vs-tilt-up delta in a single reply. Highest-leverage outstanding action in the whole basis chain.
- **STALE consumers still carrying the old numbers** (wrong on denominator *and* floor): the **Ranking workbook** (all Basis/Combined/Expected scores predate v03), **`parcel-data-recovery`** (25/30 cliff + RCT v02 constants), and the platform engine **`config/replacement-cost.v1.json`** (flat $125/$137.50/$150).
- Four **`[PROXY]`** markets (Madison←Milwaukee, Grand Rapids←Detroit, Richmond←Baltimore, Des Moines←Minneapolis) always trigger **DENOMINATOR-SENSITIVE**. Grand Rapids is weakest — Detroit is a high-cost union market, so its floor is likely too generous.

Related: [[deal-decision-ledger]] · [[markets]] · [[standards]] · [[firm]]


## Addendum 2026-07-27 — a third denominator was caught and reverted (the rule worked)

`county-parcel-screen`'s Columbus v04 output (2026-07-24) carried a flat **$150/SF** benchmark, independent of RCT v03 — its own README already flagged this as unreconciled. An in-session instruction to adopt $150/SF for the off-market master's Columbus tab was caught against this file's "if you find a second denominator, it is a bug" rule before it propagated into memory or to other markets, and reverted. Corrected build: `20260727_AllMarkets-OffMarket-Master_v08.xlsx`, Columbus on RCT v03 LOW ([RCT-private]) at the conservative oldest-vintage threshold ([RCT-private], vintage unknown for all rows). Full narrative: `memory/event_log.md`, 2026-07-27 entry; ratification record: `memory/ops_decision_log.md`, 2026-07-27 entry.

**Added stale-consumer confirmation:** `county-parcel-screen`'s $150/SF is now a **third** confirmed stale consumer alongside the two already named above (ranking workbook, `parcel-data-recovery`). If that tool is re-run for another market, re-derive its basis component against RCT v03 before trusting the 0-100 score's basis sub-component or any "ORA Basis Band" it emits — do not reuse the $150-anchored bands as-is.


## Addendum 2026-07-27 (later same session) — off-market master fully migrated to RCT v03

The off-market master (`AllMarkets-OffMarket-Master`) is CLOSED as a stale consumer as of
`20260727_AllMarkets-OffMarket-Master_v09.xlsx` — all 9 markets now basis-score against RCT v03,
not RCT v02. Full detail: `memory/event_log.md`, 2026-07-27 "full 9-market RCT v02->v03 migration"
entry.

**Remaining stale consumers (unchanged from the original list above):** the standalone
`parcel-data-recovery` skill's own P1 recompute formulas (still documents the old 25/30 cliff +
RCT v02 constants in its own SKILL.md text — only the off-market MASTER WORKBOOK was migrated this
session, not that skill's doctrine text) and the platform engine `config/replacement-cost.v1.json`
(flat $125/$137.50/$150). Route a doctrine patch to those two directly rather than assuming this
session's workbook-level fix covers them.
