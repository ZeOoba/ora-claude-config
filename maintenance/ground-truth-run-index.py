#!/usr/bin/env python3
"""ground-truth-run-index.py -- Stage 0 of the ORA Ground-Truth Auditor.

Deterministic run index: reads both scheduled-task registries, resolves each
run's actual transcript (task -> session record -> transcript, one join per
fleet -- see docs/superpowers/specs/2026-09-10-ground-truth-auditor-design.md
Sec 3.4/3.5/3.5a), flags duplicate side effects, and asserts a join-rate floor
before any verifier agent is dispatched. No LLM judgment happens in this file
-- duplicate detection is a key comparison, not something an agent can be
argued out of (design spec Sec 5 Stage 0).

Usage:
    python ground-truth-run-index.py [--window-hours N] [--out PATH] [--json]

Emits one run-index JSON document (see build_run_index()'s docstring for the
schema) to --out, or stdout with --json.
"""
import argparse
import glob
import json
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "_shared"))
try:
    import store_discovery as _sd
except Exception:
    _sd = None

DEFAULT_WINDOW_HOURS = 24
JOIN_TOLERANCE_MS = 2000  # createdAt vs lastRunAt match window (spec Sec 3.5a)


def build_run_id(fleet, task_id, last_scheduled_for):
    """run_id keys on lastScheduledFor (the logical cycle), never lastRunAt --
    a catch-up fire's lastRunAt can lag lastScheduledFor by hours (measured:
    automation-health-monitor 2026-09-10, 2h08m10s -- spec Sec 3.6). Keying on
    lastRunAt would make every catch-up fire read as a distinct logical cycle
    and collapse idempotency detection."""
    return "{}:{}:{}".format(fleet, task_id, last_scheduled_for)


def _parse_iso(ts):
    """Parse a registry ISO8601 timestamp ('...Z' or '...+00:00') to an
    aware UTC datetime, or None if ts is falsy/unparseable."""
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def decide_window_hours(now, last_auditor_run_at, cc_tasks, lams_tasks,
                         default_hours=DEFAULT_WINDOW_HOURS):
    """Automatic window sizing (design spec Sec 5 Stage 0). Widens past
    default_hours when either holds:

      1. a MEASURED gap since the previous auditor run exceeds default_hours
         (last_auditor_run_at is not None and the gap is too large), or
      2. the window contains a fleet-resume event -- a one-time task (no
         cronExpression) whose id contains 'resume', fired within
         default_hours of `now`.

    A literal "never ran" (last_auditor_run_at is None, e.g. the auditor's
    very first invocation) is recorded in the returned reason for visibility
    but does NOT by itself widen the window -- there is no measurable gap to
    widen by, and the realistic backfill scenario (registering the auditor
    mid-pause) is already covered by condition 2's resume-event detection.
    A bare never-ran with no resume event in range has nothing further back
    to meaningfully look at; a nightly auditor audits nightly deltas going
    forward, not fleet history since inception. Confirmed with Gabriel
    2026-09-11 -- do not "fix" this into an unbounded or arbitrary widen
    without checking with him again.

    A fixed 24h window keyed on lastScheduledFor would silently drop the
    catch-up runs most likely to have duplicated side effects (spec Sec 5).

    Returns (window_hours: float, reason: str). `now` and `last_auditor_run_at`
    are aware UTC datetimes (or None for the latter).
    """
    reasons = []
    window_hours = float(default_hours)
    gap_hours = None

    if last_auditor_run_at is None:
        reasons.append("no prior auditor run recorded")
    else:
        gap_hours = (now - last_auditor_run_at).total_seconds() / 3600.0
        if gap_hours > default_hours:
            reasons.append(
                "prior auditor run was {:.1f}h ago (> {}h)".format(gap_hours, default_hours))
            window_hours = max(window_hours, gap_hours)

    resume_cutoff = now - timedelta(hours=default_hours)
    resume_hit = False
    for t in list(cc_tasks) + list(lams_tasks):
        if t.get("cronExpression"):
            continue  # recurring, not a one-time resume marker
        tid = (t.get("id") or "").lower()
        if "resume" not in tid:
            continue
        ts = _parse_iso(t.get("lastRunAt"))
        if ts is not None and ts >= resume_cutoff:
            resume_hit = True
            reasons.append("fleet-resume event '{}' fired in window".format(t.get("id")))

    if resume_hit:
        # A resume alone (auditor otherwise on schedule) still needs the
        # window widened enough to reach the paused period it just
        # re-enabled -- a bounded pause can span days.
        window_hours = max(window_hours, default_hours * 3)

    if not reasons:
        return float(default_hours), "default {}h window (no widen condition met)".format(default_hours)
    return window_hours, "; ".join(reasons)
