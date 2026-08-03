---
name: reference-lane-telemetry-records-are-not-sessions
description: lane-telemetry.jsonl holds ~2.4 records per session — the emitter re-appends on every resume; never read a raw line count as a session count
metadata: 
  node_type: memory
  type: reference
  originSessionId: 83715320-ea98-4ae2-8ebd-e3ec6f2163dd
  modified: 2026-08-03T20:39:04.724Z
---

`~/.claude/telemetry/lane-telemetry.jsonl` is a **record** log, not a session log. `hooks/eos-telemetry.py` is a SessionEnd hook that re-parses the **entire** transcript and appends a **fresh** record every time it fires — and SessionEnd fires on every resume/clear/compaction, not once per session.

Measured 2026-08-03: **962 records = 394 distinct `session_id`s**. Worst single session appeared **18 times**. Every multi-record session had non-decreasing edit counts (26 monotonic, 0 non-monotonic), confirming the re-parse-of-a-growing-transcript mechanism.

Consequences when reading this file ad hoc:
- A raw line count overstates sessions ~2.4x.
- Any rate computed per record **weights long/resumed sessions N times**. They skew "good": resumed sessions declare lanes and dispatch subagents more often than short ones, so per-record rates read *higher* than reality (dispatch 43.0% per record vs 40.2% per session).
- Early fires snapshot the transcript **before** later activity, so a session can hold records that contradict each other. 5 sessions held conflicting `task_dispatched` values. Merge existential signals by UNION, never last-write-wins.
- `task_dispatched` must only be unioned from a record that was itself dispatch-**capable** — a blind-era or detector-regressed record's value is not evidence of anything, and letting its `True` win manufactures the signal.

`maintenance/eos-telemetry-rollup.py` handles all of this correctly as of commit `454cf3e` (branch `claude/eos-rollup-dedupe`) — read sessions from `merge_sessions()`, don't re-derive. **The emitter is deliberately UNFIXED**: it still appends a duplicate record per resume, so the file keeps growing faster than sessions and any *other* consumer must dedupe by `session_id` itself.

Interpreting the dispatch rate: the denominator is every session that touched a file, so markdown/memory-only sessions (~a third, ~8% dispatch) dilute it. Code sessions run ~59%, climbing monotonically with size (0% at ≤2 edits → ~59% at 20+) — that is the CLAUDE.md "inline for trivial/small/coupled" rule working, not drift.

Related: [[reference-config-write-guard-blocks-eos-review-gate]] · [[feedback_verified_null_vs_inferred_null]]
