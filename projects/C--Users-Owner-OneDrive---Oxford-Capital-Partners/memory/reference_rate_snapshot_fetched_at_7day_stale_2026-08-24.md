---
name: reference-rate-snapshot-fetched-at-7day-stale-2026-08-24
description: "ora-sofr-direct-prefetch found Rate Snapshot fetched_at stamp 7 days stale (08-17) on 08-24, not the few-minute ordering race it's designed for"
metadata: 
  node_type: memory
  type: reference
  originSessionId: ad0183a8-416e-4ff7-8e04-cda104b67125
  modified: 2026-08-24T14:22:25.081Z
---

`ora-sofr-direct-prefetch`'s 2026-08-24 10:10 ET run read the "Rate Snapshot — Current" Notion page (`35e6ecd8-9e59-814f-ae22-fe99464084d1`) and found the machine-readable header's `fetched_at` stamped `2026-08-17 09:52 ET` — 7 calendar days behind, with `prior_trading_day: 2026-08-14`. All of §1 (UST yields), §3 (BBB OAS/PMMS), §4 (FedWatch) still carried 08-14/08-13/08-17 data as of the 08-24 read.

**Why this matters.** The task's STEP 2 ordering-hazard logic (see `ora-sofr-direct-prefetch` SKILL.md CONTEXT section) was designed around a same-burst race with `ora-am-brief` Block A — the two fleets firing seconds apart, resolving within ~6 minutes (observed 2026-07-24). A 7-day-stale `fetched_at` is a different failure class: Block A (`0 6 * * *`, CC/MCP-only) appears to not have written this page's non-SOFR sections in a week, not merely lost a same-day race. This task only owns §2 (SOFR Strip) and patched it correctly (`supersede_status=EXPECTED_NOT_YET_OBSERVED`, logged to `sofr-supersede-status.log`); per its STEP 5 silence rule this outcome does not trigger an Ops Hub post or email, so nothing else records the anomaly.

**How to apply:** if `ora-am-brief` / Block A health comes up (automation-health-monitor findings, a stale Daily Brief, or a future audit), check whether this Rate Snapshot page's §1/§3/§4 data and header `fetched_at` are still behind — a persistent multi-day gap (vs. a single burst) points at Block A not running to completion, not just producer-ordering noise. Cross-check `automation-health-monitor`'s beacon sweep and `ora-health-guard`'s late-wake findings ([[reference_am_cluster_late_wake_root_cause_2026-08-13]]) for the same window.
