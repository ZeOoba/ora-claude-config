---
name: reference-pause-windows-observed-state
description: "Pause-aware health checks exist (2026-09-12) — _shared/pause_windows.py records OBSERVED per-task pause intervals; don't rebuild, don't parse resume SKILL.md text"
metadata: 
  node_type: memory
  type: reference
  originSessionId: de840aed-126d-4193-8c05-57d0ee2052d1
  modified: 2026-09-12T22:59:32.935Z
---

`~/.claude/maintenance/_shared/pause_windows.py` (commit `4a7d758`) is the durable record of past bounded pauses. `_shared/fleet_pause.py` only knows about a pause while it is live. Store: `_state/fleet-pause-windows.json` (runtime, untracked).

- **Recording:** `pause-resume-guard.py` (native, every 6h) calls `capture()`. A task is HELD only if it is **disabled AND named by a pending one-time task that names ≥3 disabled tasks**. Holds over 21 days are voided. Intervals close on a non-held observation, a run since the last observation, a >48h blind span, or task deletion.
- **Hand records:** `pause_windows.py record --note "<evidence>"`, capped at 21d. Used for the 09-07 pause (`cc:`/`lams:pause-2026-09-07`) and for 1–2 task pauses.
- **Consumers:** `health-guard-beacon.py` (`PAUSE_EXPLAINED`), `fleet-status.py` (`pause-explained (NOT missed)` line), `ora-health-guard` C.0b (queries the record first, ledger glob as fallback), register-scheduled-task v2.22 (capture at pause time).

**Why:** the 09-12 health-guard run reported 3 of its 5 FAILs purely because of the planned pause.

**How to apply:**
- Don't infer pause membership from resume SKILL.md text. Two same-day designs doing that were refuted with 10 false-negative paths (carve-outs, efficacy checks, cancel/re-pause, early re-enables). Text is not state; observe the registry.
- A subtraction may only ever downgrade STALE. An unreadable store must mean no subtraction.
- Before adding pause-awareness to another detector, reuse `overlap_hours()`.
- **Detectors keyed by FILE, not task, must DECLARE producers** (see `state-freshness-probe.py` `PAUSABLE_PRODUCERS`, branch `feat/freshness-probe-pause-record`). Inferring the producer from file names in scripts, SKILL.md files or Task Scheduler actions was refuted 3 ways the same day (native writers outside maintenance/, case, two-hop chains). Take the MIN overlap across declared producers. A declared producer missing from a registry gets no excuse at all, never a fallback to undeclared rules.
- **Scheduled resumes must be attended (OI-273):** the Desktop runner blocks `update_scheduled_task` even in `bypassPermissions`.

Related: [[reference_bounded_pause_voided_overlapping_efficacy_checks_2026-08-21]] · [[feedback_verified_null_vs_inferred_null]] · [[project_regression_root_cause_audit_2026-08-28]] (heuristic-not-structure mechanism).
