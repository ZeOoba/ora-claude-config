# Pause-aware health checks + durable pause record — plan (2026-09-12)

**Objective:** a deliberate bounded pause stops producing health FAILs, without muting real failures — via a self-writing durable record of past pause windows that the beacon and missed-cycle checks subtract from a gap before judging it.

**Trigger:** 2026-09-12 ora-health-guard run, 5 FAILs, 3 caused by the 09-07→09-11 pause. Root cause: `_shared/fleet_pause.py` only answers "paused NOW"; after the resume fires the window vanishes, and the only past-pause file (`*_FleetPause_RestoreLedger*.json`) is hand-written and was never written for 09-07.

## Constraints
- Do not touch untracked `_shared/fleet_pause.py` / `_tests/test_fleet_pause.py` (session fd011007, preflight CONTESTED).
- Commit by explicit path (3 other sessions have live dirty files in the checkout).
- Fail-safe: unreadable pause store → checks alarm exactly as before.
- ora-health-guard stays report-only.
- Item 3 (laptop keep-awake) is Gabriel's decision; no system power change applied.

## Steps
| # | Size | Step | Verify |
|---|---|---|---|
| T1 | S | ✅ `_shared/pause_windows.py` — redesigned to observed-state after 3 refute passes | 24 tests; live 09-07 hand records |
| T2 | XS | `health-guard-beacon.py` PAUSE_EXPLAINED verdict | 6 new + existing tests; live read |
| T3 | S | `fleet-status.py` find_missed_cycles pause split + summary line | new + existing missed-cycle tests |
| T4 | XS | `pause-resume-guard.py` auto-capture each run, fail-open | run guard, exit 0 |
| T5 | XS | `ora-health-guard/SKILL.md` B.3.5a / C.0b / C.1.1 | terms match code keys |
| T6 | XS | `ora-skills/register-scheduled-task/SKILL.md` capture step | repo clean pre-check; flag re-import |
| T7 | XS | explicit-path commits, event_log, memory | `git show --stat` |

## Risk
All reversible (git revert; new `_state` file). Worst case = false negative, mitigated: per-task windows, ≥5 referenced ids + enable verb, only downgrades STALE.

## Must not touch
`_shared/fleet_pause.py`, `_tests/test_fleet_pause.py`, `state-freshness-probe.py`, `fleet-deadman.ps1`, registries, settings.json, CLAUDE.md, hooks/.

## Follow-up scope (same day, Gabriel-directed)
| # | Size | Step | Verify |
|---|---|---|---|
| F1 | XS | ✅ Close stale OI-273 marker (38/38, after verifying all 38 ids enabled) | find_stalled() == [] |
| F2 | S | `pause-resume-guard.py` `find_incomplete_resumes()`: a fired resume-shaped one-time task whose named recurring ids are still disabled after grace → alarm (OI-273 detection gap: 6/38 = 16% escaped the ≤10% ratio check) | new tests in test-pause-resume-guard.py; live run shows 0 |
| F3 | XS | register-scheduled-task v2.23: unattended `update_scheduled_task` blocks on a permission prompt (root cause OI-273); resume needs Desktop-UI permission mode or attended run; marker command needs `--fleet` | doc diff |
| F4 | XS | ✅ ora-health-guard v1.13 lid-close watch | commit 1e6dc71 |
| F5 | XS | ✅ Land Rev 24 files + 14-day resume-horizon fix | 7199c53, cc1fd72 |
| F6 | S | Land all commits on main via worktree cherry-pick branches + PRs (OI-249 friction) | check-branch-point --expect N; push gate |
