---
name: reference-els-eomonth-pair-fix-half-applied-2026-08-05
description: "2026-08-05 16:46 ET — the OI-094 February pair-fix landed only half: ELS H6:I9 moved to EOMONTH(B30,12) but Assumptions!B30 was NOT constrained to month-end, which is strictly worse than the pre-fix state under manual override"
metadata: 
  node_type: memory
  type: reference
  originSessionId: a9ce8b4c-71ff-45fd-8f0c-f7ae22c39008
  modified: 2026-08-05T20:51:12.131Z
---

**Caught 2026-08-05 ~16:50 ET, live, while building the OI-092 cross-check.** The workbook was
edited at 16:46 mid-session. Two changes landed in `External Loans Summary`; a third, required
one, did not.

**What landed.** Banwick range `B11:B70` → `B11:B71` (OI-094 truncation — genuinely FIXED, the
$3.35M r71 balloon is now inside the summed range), and the right edge on `H6:I9` moved
`EDATE(Assumptions!$B$30,12)` → `EOMONTH(Assumptions!$B$30,12)`.

**What did NOT land, and must.** `Assumptions!B30` still reads

```
=IF(B31="Auto (current month-end)",EOMONTH(TODAY(),0),IF(ISNUMBER(B32),B32,EOMONTH(TODAY(),0)))
```

The manual-override branch returns **`B32` raw**. OI-094's ruling requires `EOMONTH(B32,0)`.
`EOMONTH` on the right edge is only safe *paired* with a month-end-constrained B30 — that was the
explicit finding, and only half of the pair was applied.

**The half-applied state is WORSE than the defect it replaced.** Simulation over 3,024
manual-override cases (9 pay-days × 28 days-of-month × 12 months, 2027):

| state | cases ≠ 12 payments |
|---|---|
| pre-fix `EDATE`, B30 unconstrained | **3** — all under-capture 11 |
| **current `EOMONTH`, B30 unconstrained** | **2,073** — all over-capture 13 |
| OI-094 pair `EOMONTH` + `EOMONTH(B32,0)` | **0** |

Worked case: `B32 = 2027-03-15`, pay-day 20 → window `(2027-03-15, 2028-03-31]` captures **13**
payments. This is the OI-092 over-capture defect re-opened, at ~69% of override dates instead of
~6 days/loan/year. Corroborates OI-094's own 1,428-deviation simulation (different case set, same
direction and magnitude class).

**Latent only** because `B31 = "Auto (current month-end)"` today, which forces B30 to a month-end
and makes `EOMONTH(B30,12) ≡ EDATE(B30,12)`. It goes live the first time the Close Control manual
override is used — which is the entire reason that block exists.

**Second, separate defect from the same edit: the block is now internally inconsistent.**
Only the four borrower rows moved. `H15`/`I15` (Restoration Church Trust) and `H16`
(485 S Walnut) are **still on `EDATE`**. Two different right-edge functions now govern one
summary block, so the six loans no longer share a window definition under manual override.

**Not fixed by this edit, still open:** RCT's $1,945,102.73 balloon (Oxford 50% = $972,551.37)
sits in the PAYMENT AMOUNT column, invisible to the `D`/`E`-only sum — live now, since RCT matures
2027-02-20 inside the current window. Also `E16` still anchors on bare `TODAY()` while every other
cell anchors on `B30`, so 485 S Walnut's principal and interest use different as-of dates.

**The `server/workbook/debt-service-crosscheck.ts` detector catches this class.** It computes its
window as `EDATE(B30,12)` independently, so once the workbook's `EOMONTH` window diverges under an
override, the recomputed-vs-cached comparison fires a one-payment `annualDebtService` divergence.
It is the reason the Banwick truncation was observed being fixed in real time.

Related: [[reference_workbook_annual_debt_service_366day_overcapture]] ·
[[feedback_findings_decay_recheck_before_writing]] · [[feedback_verified_null_vs_inferred_null]]
