---
name: reference-fleet-status-compound-cron-and-semantics
description: "fleet-status.py's _cron_fires_on() uses AND (intersection) semantics for a compound dom+dow cron, matching the live Claude scheduler's actual nextRunAt behavior — NOT textbook POSIX cron OR-semantics. Fixed 2026-07-28 after it produced a false 137h 'missed single cycle' alarm on ora-entry-market-scan."
metadata: 
  node_type: memory
  type: reference
  originSessionId: a8cdabe8-5d5d-413c-8fad-cb1ccc1b649e
  modified: 2026-07-28T23:31:19.488Z
---

**What the live scheduler actually does.** For a 5-field cron where BOTH day-of-month and day-of-week are restricted (e.g. `0 11 1-7 * 2`, intended as "first Tuesday of the month"), the live Claude scheduled-task engine requires **both** fields to match (AND/intersection) — not standard POSIX cron, which fires if **either** matches (OR/union) once both are restricted.

**Evidence (2026-07-28).** `ora-entry-market-scan`'s registered `nextRunAt` was `2026-08-04` (the first Tuesday that also falls within days 1-7). Under POSIX OR semantics the next match would have been `2026-08-01` (a Saturday, satisfying the dom-only 1-7 branch) — three days earlier. Since the live engine skipped straight past Aug 1-3 to Aug 4, its real behavior is AND, confirmed from this single but decisive data point (no other live task currently has both fields restricted, so this is the only direct evidence available — re-verify if a second compound-cron task is ever registered).

**Why it mattered.** `fleet-status.py`'s `_cron_fires_on()` (used by both `find_missed_cycles()` and `crons_share_a_day()`) implemented the textbook POSIX OR reading. For `ora-entry-market-scan` — registered 2026-07-16, too late for July's real AND-match date (07-07) — the OR-based detector instead expected a fire on *any* Tuesday, including 2026-07-28 (today, but day 28 — outside 1-7). Compared against the task's actual `lastRunAt` (2026-07-22, a one-off manual smoke-test run, not a cron fire — 07-22 is a Wednesday, matching neither field), this manufactured a bogus 137-hour "missed cycle" alarm for a task that has never actually missed anything; its true first-ever scheduled fire (Aug 4) hadn't happened yet.

**Fix.** `_cron_fires_on()` in `C:\Users\Owner\.claude\maintenance\fleet-status.py` changed the both-restricted branch from `or` to `and`. Regression test: `_tests\test_fleet_status_missed_cycle.py::test_compound_dom_dow_cron_uses_first_match_semantics_not_or` (reproduces the bug pre-fix with the exact incident timestamps, passes post-fix). Full suite (8 unit + 16 black-box) green. Live-reverified against the real dual-fleet registry: `missed single cycle` count went 1 → 0.

**If this resurfaces:** check whether a *new* compound dom+dow cron task's `nextRunAt` still matches AND semantics before assuming the fix is stale — this was empirically derived from one live example, not from documented product behavior, and Anthropic's scheduler internals could change without notice.

Related: [[reference_fleet_throttle_skip_catchup_burst]] (a different fleet-status false-positive class — throttle skips from app-closed catch-up bursts, not cron-parsing), [[reference_probe_scan_sets]] (the broader pattern of a probe silently checking the wrong thing).
