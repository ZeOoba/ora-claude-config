---
name: reference-rate-snapshot-fetched-at-utc-mislabel
description: "Notion Rate Snapshot page can stamp fetched_at with a UTC value labeled 'ET' (+4h), making the page look fresher than it is and suppressing ora-health-guard's B.2 STALE escalation. Observed 2026-07-28; 07-27 stamp was correct, so it is intermittent."
metadata: 
  node_type: memory
  type: reference
  originSessionId: 066d3f8a-ef1d-43d1-accf-2b48d147e096
  modified: 2026-07-28T14:12:41.230Z
---

# Rate Snapshot `fetched_at` can be UTC wearing an "ET" label

**Observed 2026-07-28** on Notion page `35e6ecd8-9e59-814f-ae22-fe99464084d1` ("📈 Rate Snapshot — Current"), written by `ora-am-brief` Block A.

The page header read `fetched_at: 2026-07-28 12:58 ET` and its §6 run-timing note said the run "fired at ~12:54 ET". **Both were UTC values carrying an ET label — off by +4 hours (EDT).**

## Evidence (the first point alone is conclusive)

1. **12:58 ET had not happened yet.** Wall clock at read time was **09:02 ET / 13:02 UTC**. A page cannot be stamped four hours into the future.
2. Notion's own server-side "as of" for that read was `2026-07-28T12:58:42Z` — matching "12:58" exactly *as UTC*.
3. Registry ground truth: `ora-am-brief` `lastRunAt = 2026-07-28T12:54:24Z` = **08:54 ET**. The page's "~12:54 ET" is that same instant, mislabeled.

## Why it matters — it can silence the detector that watches it

`ora-health-guard` Block B.2 computes `rate_age_hours` and `missed_sessions` **directly off `fetched_at`**. A UTC value read as ET makes the page look **four hours fresher than it is**, biasing the staleness check toward silence — the wrong direction. Near a 06:00 ET slot boundary it can suppress a genuine STALE flag.

That matters more than a normal freshness bug because `fetched_at` is the *only* cheap signal that the rate producer dropped a day: a dropped slot leaves **no `recordedSkips` entry**, and `lastRunAt` is single-valued. See [[reference_fleet_throttle_skip_catchup_burst]].

## Scope — intermittent, not constant

The 2026-07-27 stamp (`2026-07-27 09:25 ET`) looks correctly ET. So this is **not** a constant offset — possibly tied to which code path a catch-up run takes. Do not assume every stamp is wrong; **check it against a known-UTC anchor** (the task's registry `lastRunAt`, or Notion's own "as of") before trusting or before alarming.

The 2026-07-28 STALE flag itself was **unaffected** — the gap was ~23.5h, nowhere near a boundary.

## What to do

- **Reading the page:** sanity-check `fetched_at` against `lastRunAt` from the scheduler registry before computing any age.
- **Consumer hardening (proposed, not built):** have B.2 reject a `fetched_at` that is *in the future* relative to session time rather than computing a negative age and silently passing.
- **Producer fix (proposed, not built):** `ora-am-brief` Block A should stamp from local ET explicitly, or label the field `UTC` / append the offset. Consistency is what the detector needs, not a particular zone.

Related: [[reference_scheduled_task_staleness_guard_trips]] · [[feedback_verified_null_vs_inferred_null]] · [[reference_fleet_status_dual_read]]
