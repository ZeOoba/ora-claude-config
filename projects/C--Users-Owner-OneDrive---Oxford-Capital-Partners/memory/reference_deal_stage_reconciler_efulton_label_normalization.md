---
name: reference-deal-stage-reconciler-efulton-label-normalization
description: "First deal-stage-reconciler run (2026-07-27) flagged E Fulton as a stage \"transition\" that was really just a label-normalization artifact, not a new decision"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 9e120169-efb4-4cea-b841-46f7f0ef8f05
  modified: 2026-07-27T22:11:30.018Z
---

On 2026-07-27's ora-open-sessions-board run — the first execution of Step 4.5 (deal-stage reconciliation) — the reconciler compared live Notion Acquisition Pipeline Tracker stages against `deal-stage-map.json`'s seeded snapshot and flagged one transition: **E Fulton Street Portfolio — Columbus, OH**: `Killed — Note/Short-Sale in Discussion` → `Killed`.

This was not a real stage change. Notion's `Stage` select field only supports a fixed option set (Closing, Under Contract, Due Diligence, LOI Executed, LOI Pending, Candidate, Closed Won, Passed, Killed) — it has no room for a compound label like "Killed — Note/Short-Sale in Discussion". The seeded snapshot had captured a richer descriptive label (likely hand-authored, combining Stage + Kill Reason context) that Notion's actual field can't hold. The reconciler correctly diffed the two and logged it per its own doctrine (disposition null → event_log.md entry only, no ledger row — see the 2026-07-27 event_log.md entry).

**Why:** the deal-stage-reconciler script (`~/.claude/maintenance/deal-stage-reconciler.py`) treats the seeded `deal-stage-map.json` as ground truth for "last known stage" and diffs against Notion's actual select value on each run. If any other seeded snapshot entries similarly hold richer/compound labels than Notion's select options allow, the same spurious-looking transition will fire once, on first comparison, then settle since the map now stores the normalized value.

**How to apply:** if a future ora-open-sessions-board run reports a deal-stage transition where the "old" value looks like a richer/annotated version of the "new" Notion select value (rather than a genuinely different stage), don't treat it as a live deal-status change — it's very likely the same map-vs-schema normalization artifact. Verify against the actual Notion page's Stage + Kill Reason/Notes fields before treating it as news. Full incident: `event_log.md` 2026-07-27 entry "Deal-stage sync: E Fulton Street Portfolio...".
