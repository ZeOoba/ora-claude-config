---
name: project-master-workbook-no-single-writer-2026-07-24
description: "Master Excel Template Company Wide -- Oxford.xlsx has no single-writer discipline -- its own embedded Claude Log sheet shows ~140 turns of concurrent/uncoordinated agent edits, most today, touching NOI/debt-balance/lease-date cells outside the lease-id incident. The lease-date incident itself is CLOSED correctly (see project_lease_snapshot_id_rebaseline_pending_2026-07-24.md) -- this note is only about the surrounding governance gap."
metadata:
  type: project
  originSessionId: e3f980f6-f186-4928-ba79-212963641f99
  modified: 2026-07-24T23:57:21.323Z
---

## Correction to my own earlier draft of this note

My first pass here wrongly concluded Carlton Handy/Granite Tops/J&R's CURRENT (post-PR#232)
lease-end dates were themselves the bug, and that the 4-source cross-check Gabriel cited
(2027-02-28 for Handy) was ground truth. **That was backwards.** A concurrent session closed the
actual incident the same day — see [[project_lease_snapshot_id_rebaseline_pending_2026-07-24]]:
the row-position id bug had been silently attaching the WRONG leaseEnd to these tenants for a long
time; Gabriel authorized a business-key re-baseline; the corrected values are Handy 2026-08-31
(6mo EARLIER than the believed 2027-02-28 — an undetected holdover), J&R +5mo, Granite Tops +2mo.
Notion/HubSpot's agreement on the wrong 2027-02-28 for Handy reflects those systems having
inherited the same pre-fix bad value, not independent verification. Do not re-open this — it is
CLOSED and Gabriel-confirmed (Triple Threat Kansas City LLC occupancy check).

## What's still real and still open: no single-writer protocol on the workbook itself

Independent of the (now-closed) lease-id incident, the master workbook carries its own embedded
audit-trail sheet, "Claude Log" — ~140 rows/turns, the large majority dated 2026-07-24. It shows
multiple agents/sessions writing to this SAME file concurrently with no coordination mechanism,
including cells unrelated to the lease-id incident:
- Turns 108/111/112: repeated `Master Tenant Rent Roll` sorts that wrote formula cells (Rent/SF,
  Status, Annual Rent) back with stale row-relative references — caught and patched in Turn 115.
  Turn 112 separately had an off-by-one that stranded a tenant row outside its sorted block for a
  full turn.
- Turns 132–137: `External Loans Summary!E10` (a live debt balance) was changed FIVE times in
  immediate succession (×0.5 → ×2 → /2 → no scaling) — trial-and-error on production debt data.
- A separate "HubSpot Excel peer agent" independently diffed HubSpot's tenant export against the
  master and overwrote 3 OTHER tenants' lease-end dates (Medspeed, P.U.P.S, Stone Crest) based on
  HubSpot being "5 years ahead" — a different correction mechanism than the business-key
  re-baseline used for the Handy/J&R/Granite Tops incident, running in the same file same day.

Unlike `ora-skills` (single-writer rule enforced) or the scheduled-task registries (membership-log
check required before writes), this workbook has no analogous protocol. The lease-id incident
happened to resolve cleanly, but the pattern (uncoordinated concurrent writes to the one workbook
that's "FIRST for firm figures") is a standing risk to NOI/LTV/DSCR/debt-balance figures too, not
just lease dates.

## Recommendation (awaiting Gabriel — governance only, no financial-figure action needed)

Establish single-writer discipline on the master workbook (same pattern as the ora-skills rule in
`tech.md §2`) so concurrent agent sessions can't collide on it the way Turns 108–137 show they did
today. This is a process/governance question, not a data-correctness one — the lease-date incident
itself needs no further action.

Related: [[project_lease_snapshot_id_rebaseline_pending_2026-07-24]] (the actual incident, CLOSED
correctly) · [[reference_lease_date_detector_defects_2026-07-24]] (first-pass diagnosis) ·
[[reference_concurrent_session_duplicate_hardening_work]] (same failure class).
