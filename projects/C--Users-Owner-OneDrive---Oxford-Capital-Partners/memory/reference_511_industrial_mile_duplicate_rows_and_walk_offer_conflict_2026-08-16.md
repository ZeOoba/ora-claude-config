---
name: reference-511-industrial-mile-duplicate-rows-and-walk-offer-conflict-2026-08-16
description: "511 Industrial Mile has TWO Deal Sourcing Log rows, and its Walk Price ($930K) sits below its actual LOI ($1.45M) — the loss is unclassifiable until that resolves"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 7c978502-193c-48bf-9ad5-22f3ee76848c
  modified: 2026-08-16T20:33:11.970Z
---

**511 Industrial Mile Road, Columbus OH 43228** — ORA's only completed, priced competitive LOI loss (lost 2026-07-17, competing buyer under contract at full ask **$1,575,000** vs ORA's LOI v02 at **$1,450,000**; relayed by broker Noah Kahkonen, Best Corporate RE). Two defects found on it 2026-08-16 while backfilling the lost-deal ledger:

**1. Duplicate Sourcing Log rows.** Same address, same 17,688 SF, different broker names:
- `3446ecd8-9e59-8193-a251-ce86f2e51413` — "511 Industrial Mile Road — Columbus, OH 43228", Status=Reviewing, Walk Price $930,000, broker Noah Kahkonen. **This is the canonical row** — the ledger backfill was written here.
- `37c6ecd8-9e59-8132-a81c-d40eed8d6380` — "511 Industrial Mile Rd, Columbus, OH 43228", Status=Dead, no Walk Price, broker "James Mangas".

Match on normalized address, never on row identity, or this deal double-counts in every aggregate.

**2. Walk Price contradicts the actual offer.** The canonical row carries Walk Price **$930,000** against an LOI ORA actually submitted at **$1,450,000**. Those cannot both be true — a walk price is the ceiling, and ORA does not bid above its own ceiling. Consequences:
- `Loss Class` is deliberately held at **UNCLASSIFIED**, and `ORA Max Defensible Price` deliberately left blank. Do not "fix" this by picking whichever number looks plausible.
- If $930K is right → R1 **BASIS-DISCIPLINE** (winner paid 69% over ORA's walk; losing was the strategy working).
- If the walk price is stale → the terms dimension binds instead: the tax-reassessment protection was ORA's stated deal-break term, pointing at **EXECUTION**.

**Live re-engagement position.** Pipeline Stage is deliberately held at `Candidate`, NOT `Passed`, per Gabriel — to hold the fallout position. `ora-511-industrial-fallout-check` (one-time task) fires **2026-08-21** to ask the broker whether the competing contract survived DD and financing. If it failed, re-engage at or below $1.45M. The Sourcing Log row now carries `Re-Engagement Flag` ticked and `Re-Engagement Tickler Date` 2026-08-21.

**Related, same sweep:** the Acquisition Pipeline Tracker's `LOI Status` field is unreliable and disagrees with the Sourcing Log — `1333 Research Road` reads `Not Submitted` there while its Sourcing Log row reads `LOI Submitted`; 511 reads `Submitted` with no LOI Expiration Date. Same failure shape as [[reference-hubspot-lease-renewal-closedate-unreliable-2026-08-16]]. Never branch automation on it; the Sourcing Log's `LOI Outcome` is the field to use.

See also [[reference-808-rhoads-real-broker-is-elford-not-koon]] (the other live winner-busted re-engagement, cold 50+ days).
