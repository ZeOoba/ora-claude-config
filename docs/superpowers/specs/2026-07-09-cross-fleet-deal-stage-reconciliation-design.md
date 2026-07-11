# Cross-Fleet Deal-Stage Reconciliation — Design

**Date:** 2026-07-09
**Trigger:** 2026-07-09 setup audit flagged that two deal-pipeline stage changes — 511 Industrial Mile Rd (reset to Candidate) and 470 McCormick Blvd (Passed) — updated `projects.md`'s live pipeline table but never got a corresponding `event_log.md` entry. Framed as "Cowork/LAMS decisions don't automatically write to this machine's Code-side log."

## Problem, precisely

Two `event_log.md` files exist: this machine's (`~/.claude/projects/.../memory/event_log.md`) and Cowork's (`Claude_Workspace/01_Workspace/memory/event_log.md`). Cowork sessions are filesystem-sandboxed to OneDrive paths and cannot reach `~/.claude/` at all — a Cowork-side skill can never write directly to this machine's log, so a true bidirectional "auto-write" bridge is architecturally impossible. The Cowork-side log is also not a complete source for deal decisions on its own (511/470 don't appear there either).

The one surface both fleets reliably write to is **Notion's Acquisition Pipeline Tracker** (`bcfe4a03…`) — every deal-stage decision ends up there regardless of which fleet/session made the call. `ora-open-sessions-board` (daily 17:00 ET, CC/MCP fleet, this machine) already has a `STEP 6` logging convention for decisions made inside its own board, and a `STEP 4` staleness check against `projects.md`'s local pipeline table — but nothing today diffs against *live* Notion, which is why decisions made outside the board's own flow (like 511 and 470) go unlogged regardless of root cause (Cowork sandboxing, a skipped STEP 6, or an ad hoc conversation).

## Decision

Extend `ora-open-sessions-board` with a new step (after STEP 4, before STEP 5's render) that reconciles live Notion Stage values against a local snapshot, and logs any drift. This is root-cause-agnostic — it catches gaps regardless of which fleet or process missed the log, without depending on every skill on both fleets remembering to do it.

Rejected alternatives:
- **Manual relay checklist only** (add a "log this" step to `deal-retirement`/board decision-handling) — same failure mode that created this gap; still discipline-dependent.
- **Don't build anything** — rejected by Gabriel; low frequency (~5-10 deal events/month) doesn't mean zero cost when it silently erodes the one durable decision record the firm has.
- **New dedicated scheduled task** — rejected in favor of folding into `ora-open-sessions-board`, which already runs daily on the right fleet and already touches the same table; avoids a new scheduled-task registration (skips the registry single-writer/blast-radius surface entirely).

## Architecture

```
ora-open-sessions-board (daily 17:00 ET)
  STEP 4  — existing: stale-card cross-check vs local projects.md
  STEP 4.5 (NEW) — deal-stage reconciliation:
    1. Agent calls Notion MCP: live Stage value for every row in the
       Acquisition Pipeline Tracker (bcfe4a03…).
    2. Agent pipes {page_id: {deal, stage}} JSON into
       maintenance/deal-stage-reconciler.py, which diffs against
       maintenance/_state/deal-stage-snapshot.json and returns the list
       of transitions (+ which map to a terminal disposition).
    3. For each transition: append-event-log.py --entry-file (always);
       Edit-tool row-append to deal-decision-ledger.md (only if terminal).
    4. Script writes the updated snapshot.
  STEP 5  — existing: render + notify (unchanged)
```

`projects.md`'s narrative pipeline table (risk/next-action/owner prose) is deliberately **not** auto-written by this step — that's curated judgment, not mechanical state.

## Components

**Snapshot** — `~/.claude/maintenance/_state/deal-stage-snapshot.json`: `{page_id: {deal, stage}}`, keyed by Notion page ID (stable across renames).

**`maintenance/deal-stage-reconciler.py`** (new, pure/offline-testable — matches the existing probe convention, e.g. `governor-drift-probe.py`, `registry-membership-probe.py`): takes the live-fetched Notion JSON + reads the snapshot file; returns transitions and updates the snapshot. No MCP calls inside the script itself — that stays the agent's job, keeping the script deterministically testable.

**`event_log.md` entry** (always, on any Stage change) — short, factual, not narrative:
```
## 2026-07-10 — Deal-stage sync: 511 Industrial Mile Rd — Candidate → Under Review (Notion)

Detected by ora-open-sessions-board's reconciliation step; no corresponding entry
existed. Tripwire only — see Notion for the actual decision context.
```
Written via the existing `append-event-log.py --entry-file` (collision-safe, spool-on-lock, reused as-is).

**`deal-decision-ledger.md` row** (only when the new Stage maps to a terminal disposition — PASS/SKIP/DROP/PARK/CLOSE/TERMINATE): reuses the existing table schema. When the reason isn't knowable from Notion alone: `"Notion Stage → <value>; reason not logged elsewhere — reconcile manually"` rather than a fabricated rationale — flagged in the run summary for later enrichment. Plain Edit-tool append; no lock mechanism (no observed concurrent-writer history on this file, unlike `event_log.md`'s documented 3-way collision — revisit only if that changes).

**Stage-vocabulary mapping** (Notion Stage → PASS/SKIP/DROP/PARK/CLOSE/TERMINATE) is *not* hardcoded from memory here — the build step pulls the real Notion database schema live (`get_properties`/similar) and hand-writes the mapping, erring toward "log to event_log only, skip the ledger row" for anything ambiguous.

## Error handling

- Notion unreachable/times out → skip the step for that run, note it in the existing RUN SUMMARY line, self-heals next day. Never blocks the rest of the board.
- `append-event-log.py` failures already handled by the script (retry + spool-on-lock).
- Snapshot file missing/corrupt → treat as empty (triggers bootstrap, not a crash).

## Rollout

1. **Backfill now, not deferred:** manually log the two known gaps (511 reset, 470 pass) into both `event_log.md` and `deal-decision-ledger.md` as part of this build — closes the originally-flagged gap directly and gives a real seed state.
2. **Bootstrap:** seed the snapshot from current live Notion state on first run with no logging (avoids flooding the log with "changes" that are really just pre-existing state). Only transitions detected from that point forward get logged.
3. **Verification:** live dry run — confirm a real no-op first pass (no false positives against the seeded snapshot), then force one synthetic transition (temporarily stale one entry in the snapshot) to confirm the log+ledger path fires end-to-end.

## Out of scope (YAGNI)

- Any write path Cowork → this machine (architecturally impossible per the sandboxing finding above; Notion-diff sidesteps rather than solves that directly).
- Auto-writing `projects.md`'s narrative table.
- A locking mechanism for `deal-decision-ledger.md` (no observed contention).
- Faster-than-daily cadence (deal decisions are low-frequency, considered actions, not real-time).
