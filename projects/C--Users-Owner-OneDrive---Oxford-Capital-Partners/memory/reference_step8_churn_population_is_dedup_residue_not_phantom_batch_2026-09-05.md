---
name: reference_step8_churn_population_is_dedup_residue_not_phantom_batch_2026-09-05
description: "The 14-tenant CHURN population ora-tenant-hubspot-reconciliation found on 2026-09-05 (recorded under OI-221) is Category-B same-name dedup residue from the 07-12 Tenant DB cleanup, NOT the Category-D phantom batch, and the 'do not re-triage' ruling it cites applied to the ~18-25 LIVE unconfirmed singletons. Non-filing was the right outcome for the wrong reason; the fix is Row Retired == false scoping, not a title+expiration signature (which fails on 3 of the 13)."
metadata:
  type: reference
  originSessionId: 0a79591a-d472-4d19-98f1-3dc60d594a41
  modified: 2026-09-05T20:24:27.136Z
---

**Verified 2026-09-05** against `ora-pm-ledger/state/tenant-db-latest.json` (as_of 2026-09-05, 298 rows) and [[reference_tenant_db_completeness_gap]] §Execution outcome (2026-07-12).

**What the run got right:** not filing a CHURN item. Every one of the 14 "one tenant, two properties" hits is a LIVE row plus a `⛔ ARCHIVED 2026-07-12 —` retired twin. A retired row's property attribution is not churn; Step 8 was written to catch a *live* row flipping between properties (the 07-21 Columbus OH / Salisbury MD regression).

**What it got wrong (three attribution errors, all in the OI-221 09-05 update):**
1. **The twins are Category B, not Category D.** The `⛔ ARCHIVED 2026-07-12` prefix was applied to ALL 124 rows archived that day (A: 19 pre-labeled duplicates · B: 98 same-name duplicate groups · D: 7 phantoms). Category D was the ~22 fabricated rows squatting on HubSpot contact IDs in the **11751–13051** range with generic invented names (Summit Consulting Group, Velocity Manufacturing…). The 13 twins here are real tenants with same-name live rows — the definition of Category B — and none of their HubSpot contact IDs fall in 11751–13051 (Itron's dup pair is even named in the 07-10 addendum as a Category-B correction).
2. **The ruling quoted does not cover these rows.** "Leave the ~18-25 unconfirmed singletons for individual review" (Gabriel, 07-12, option D) is about phantom-candidate rows left LIVE. The closed ruling that actually covers the twins is Category B's "keep newest/most-complete per group, archive the rest." Either way it is closed — but citing the wrong ruling is how the next run re-opens the right one.
3. **The "same expiration on both rows" signature fails on 3 of the 13:** Airmaster Heating & Cooling and Eastern Shore Karate & Fitness twins carry NO expiration (status Expired, property FVC); Maryland Hospital Association's twin reads 2026-05-31 vs live 2027-05-31. So Carlton L. Handy (different expirations, 3 rows not 2: live Northwood A4 exp 2027-02-28; retired no-property Expired; retired 9050 Red Branch exp 2026-05-31 sharing the live row's HubSpot contact 56366299993) is not "the one exception" — the signature simply is not a reliable discriminator. Handy remains a real open question via [OI-217](open-items-tracker.md#OI-217) (A4 contested, absent from `portfolio.json`), independent of this population.

**How to apply (whoever rewrites Step 8):** scope the Property/Market cross-check to `Row Retired == false` rows only. Do NOT encode a `⛔ ARCHIVED 2026-07-12` + same-expiration exclusion — it is the wrong population boundary and it leaks. The normalised-address point in OI-221 (em-dash vs comma, street-type abbreviations; 0 of 138 exact matches) stands on its own and is still needed.

Related: [[feedback_verified_null_vs_inferred_null]] · [[reference_tenant_db_completeness_gap]] · [[project_tenant_db_no_sync_rootcause]] · OI-009 / OI-221 / OI-231 in [[open-items-tracker]].
