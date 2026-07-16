---
name: project-replacement-cost-benchmark-unratified
description: "RCT v03 is ORA's SINGLE basis denominator (ratified 2026-07-14) — all-in shallow-bay, rebuilt from the C&W guide; floor = vintage ramp 65%→60%; ORA buys at ~35-40% of true replacement"
metadata: 
  node_type: memory
  type: project
  originSessionId: 909eeb4c-d321-40d2-a4e2-c592aa9f393d
---

**RATIFIED 2026-07-14 (Gabriel, governor-level). THERE IS ONE BASIS DENOMINATOR: `RCT v03`.** It lives in the **`acquisition-underwriting`** skill ("Replacement Cost Table (RCT v03)" under UNDERWRITING CONVENTIONS) and is authoritative. **If you find a second denominator, it is a bug.**

**RCT v03 LOW $/SF** (basis divides by LOW): Columbus 229.65 · Cincinnati 251.46 · Kansas City 227.90 · Indianapolis 253.83 · Madison 229.08 `[PROXY]` · Maryland 232.97 · Grand Rapids 253.11 `[PROXY, weakest]` · Richmond 232.97 `[PROXY]` · Des Moines 231.66 `[PROXY]`.

**Basis test:** `basis $/SF = (price × 1.02 closing + CapEx + lease-up carry) ÷ FUNCTIONAL SF`, clears if ≤ `RCT LOW × (1 − vintage floor)`. **Vintage floor = linear ramp: 65% at ≤1995 → 60% at ≥2005** (−0.5%/yr). Unknown year built → default 1995 (conservative).

## The two things worth remembering

**1. ORA buys at ~35–40% of TRUE all-in replacement cost — a ~64% discount.** The long-standing "25–30% discount" language was **an artifact of an understated denominator, never the strategy.** Say the real number in IC memos and lender packages; it is far stronger and wholly defensible.

**2. The floor % and the denominator are a MATCHED PAIR.** Never change one without re-solving the other. Leaving the old 30% floor against RCT v03 would have set the Columbus floor at $160.76/SF — a price at which *every* buy-box candidate clears. **A floor that passes everything is not a floor.**

## Why (the history, so it isn't re-litigated)

Three denominators were tried and two discarded **in one day**:
- **The old scan constants** ($140 Midwest / $170 MD / $150 Richmond / $130 DSM) — never sourced at all.
- **C&W hard cost** — ratified in the morning on my recommendation, **retired the same afternoon.** It's *hard-cost, big-box (109,200 SF), March-2025* standing in for an *all-in, shallow-bay, 2026* figure. **My recommendation was wrong.** C&W's correct role is (a) the primary source RCT v03 is **built from**, and (b) the **coherence check** that caught RCT v02's error. It is not a benchmark.
- **RCT v02** — the doctrine ORA already had. Better instrument, but **broken**: for **5 of 9 markets its "all-in" POINT sat BELOW C&W's pure HARD cost** (Cincinnati, Indianapolis, Grand Rapids, Richmond, Des Moines). *All-in cannot be less than hard cost — it contains hard cost.* It had been scaled off a big-box baseline with the **shallow-bay premium never applied**.

**Direction of the error:** replacement understated → discounts computed too small → **ORA was too STRICT and passing on deals that clear doctrine.** Maryland ran the other way (RCT v02 priced it as the most expensive market at $165 when C&W shows Baltimore is mid-priced at $133.70) → **the MD floor was too generous.**

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
