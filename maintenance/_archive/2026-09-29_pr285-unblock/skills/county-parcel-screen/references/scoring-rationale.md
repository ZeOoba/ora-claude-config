# county-parcel-screen — scoring rationale and error profile

Moved out of `SKILL.md` on 2026-09-22 (body split). Read before amending the hold curve, its constants, or the sibling-consolidation matching rule, and before writing any QC sheet (the error profile below must be stated in every QC sheet).

## Hold / tenure — why a curve, not buckets

Long hold is ORA's best FREE motivation proxy — mortgage-maturity mining was
ruled out as paid-data-only on 2026-09-18 (memory:
`reference_mortgage_maturity_signal_not_bulk_accessible_2026-09-18.md`), which
makes this component the one worth getting right.

**Why a curve, not buckets.** Tenure is not linear evidence. Three mechanisms
drive it, and all three saturate:

1. **Basis decay / lock-in.** Every year of straight-line depreciation lowers
   adjusted basis, so the embedded gain — and the capital-gains + §1250
   recapture bill — rises fastest early and asymptotes once the building is
   substantially depreciated. Lock-in is a *capacity* signal (the owner can
   clear ORA's price) and a *willingness* brake at the same time.
2. **Depreciation exhaustion.** Commercial real property runs a **39-year**
   straight-line recovery period. At full depreciation the tax shelter is gone
   while the recapture liability is at maximum: holding produces no further
   sheltering benefit. This is the sharpest single inflection in the whole
   curve and it is why a ~38-year hold is the practical ceiling of the signal.
3. **Owner life-cycle.** A 30-year hold on a small-bay building is strongly
   correlated with an ageing individual principal or a first-generation family
   LLC. Past ~35 years succession pressure is already near-certain — more years
   add almost no new information, and where it is confirmed the ESTATE-SIGNAL
   flag carries it, not this component.

Below ~2 years the owner is a buyer, not a seller. Between 5 and 15 years the
owner crosses from "still executing a business plan" to "holding a seasoned,
depreciated, refinanced asset" — that transition is where nearly all of the
discriminating power lives.

## Hold / tenure — marginal signal and comparison with the v1.2 buckets

Diminishing marginal signal, as intended: **5->15 yrs = +9.9 pts; 25->35 yrs =
+0.8 pts** — a ~12x difference in marginal information. This is the
quantitative answer to "why does D&A Berwick's 38-year hold score near-maximal":
it is not that 38 is a big number, it is that 38 is one year short of full
depreciation of a commercial building, so every tax and life-cycle mechanism
that makes tenure informative has already run to completion. A 45-year hold
carries no more signal — hence the cap, not an extrapolation.

**Versus the v1.2 buckets.** The curve is deliberately close to them in the
middle of the range and differs at the edges: it removes the 2-point cliff at
the 24/25-year bucket boundary, stops paying a 25-year and a 45-year hold
identically, and scores the 5-15 year band more finely. **This DOES move scores
— unlike v1.2, which changed no scored constant.** Any run using the v1.2
buckets instead must say so on the face of its summary.

## Sibling-consolidation error profile (state this in every QC sheet)

### Error profile (state this in every QC sheet)

**False positives** — merging parties who are not one counterparty:
- Common LLC names (`MAIN STREET PROPERTIES LLC`). Mitigated by rule 1's
  conjunctive name+address test.
- Registered-agent, attorney or property-manager mailing addresses standing
  behind dozens of unrelated owners (F9). Mitigated: address alone never merges.
- Stale blanket-deed owner lines (the Howard OAKLAND RIDGE pattern). Mitigated
  by rule 3's disagreeing-address carve-out.
- Land-condominium units under one declarant, which may be separately sellable.
  Merge for calling, flag `LAND-CONDO`, and verify structure before pricing.
- **Name-stripped counties** (Anne Arundel and Howard MD on the state extract):
  the key degrades to address + deed only, so FP risk is materially higher.
  In those counties emit rule-1 merges as FLAGS unless the deed also matches.

**False negatives** — missing a relationship that exists:
- **Generational transfer resets the deed.** Father's LLC -> children's LLC:
  new name, new deed, sometimes new mail address, and the whole cluster reads as
  a 3-year hold. This is the most damaging miss because it destroys the long-hold
  signal precisely where succession motivation is highest. Partially mitigated by
  the `HOLD-PRE-NOMINAL` fallback (these transfers are usually nominal) — but
  only where the county publishes consideration AND a prior segment.
- Alias drift a normaliser cannot reach: `BERWICK, D & A LLC` vs
  `D & A BERWICK LLC`. Accepted miss; do not add fuzzy matching without a
  measured FP rate.
- Distinct SPEs per parcel with genuinely different addresses — invisible here,
  recoverable only from SOS principal lookups (step 8).
- Counties publishing no deed reference and no mail address (Wyandotte KS has no
  published tax-mail at all): rule 1 and 2 both fail; consolidation is
  UNAVAILABLE, say so rather than reporting zero relationships as a finding.
