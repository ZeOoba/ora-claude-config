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
from collections import defaultdict
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


def find_project_dirs(claude_home=None):
    """All ~/.claude/projects/* directories (CC transcripts are spread across
    all of them, one per cwd -- spec Sec 3.4; NOT confined to the OneDrive
    one). Returns a list of absolute directory paths; [] if the projects dir
    doesn't exist."""
    home = claude_home or os.path.expanduser("~/.claude")
    proj_root = os.path.join(home, "projects")
    if not os.path.isdir(proj_root):
        return []
    return [os.path.join(proj_root, d) for d in os.listdir(proj_root)
            if os.path.isdir(os.path.join(proj_root, d))]


def find_executing_session(task, session_records, tolerance_ms=JOIN_TOLERANCE_MS):
    """Identify which session record executed a task's most recent firing.

    NOT notifySessionId -- that field is a static "notify here" target fixed
    at registration/last-edit time (verified against 4 real tasks across both
    fleets: every notifySessionId record's createdAt predates the audited
    lastRunAt by weeks to months). Spec Sec 3.5a.

    The real key: the executing session's createdAt matches the task's
    lastRunAt to within `tolerance_ms`, disambiguated by title when more than
    one candidate falls in that window (a catch-up burst can create several
    sessions inside one tolerance window).

    `session_records` is an iterable of dicts as loaded from local_*.json
    (must include at least createdAt; title/titleSource optional).

    Returns the single matching session dict, or None if zero or more than
    one candidate survives -- ambiguity is never resolved by guessing.
    """
    last_run = _parse_iso(task.get("lastRunAt"))
    if last_run is None:
        return None
    target_ms = int(last_run.timestamp() * 1000)
    expected_title = (task.get("id") or "").replace("-", " ").capitalize()

    candidates = []
    for rec in session_records:
        ca = rec.get("createdAt")
        if ca is None:
            continue
        try:
            ca_ms = int(ca)
        except (TypeError, ValueError):
            continue
        if abs(ca_ms - target_ms) <= tolerance_ms:
            candidates.append(rec)

    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]

    # Ambiguous window -- disambiguate by title. Only trust auto-generated
    # titles (a user-renamed title, titleSource != "auto", cannot be expected
    # to match the task-id-derived form).
    titled = [r for r in candidates
              if r.get("titleSource") == "auto" and r.get("title") == expected_title]
    if len(titled) == 1:
        return titled[0]
    return None  # still ambiguous -- unjoined, never guessed


def join_cc_transcript(session_record, project_dirs):
    """CC transcript path for a session record, or None.

    session record -> cliSessionId -> <cliSessionId>.jsonl, searched across
    EVERY project dir (spec Sec 3.4: scoping to one dir drops the join rate
    100/100 -> 80/100 on the most recent 100 sessions). Top-level transcripts
    only -- a subagent transcript is evidence WITHIN a run, not a run in its
    own right.
    """
    cli_session_id = (session_record or {}).get("cliSessionId")
    if not cli_session_id:
        return None
    for d in project_dirs:
        candidate = os.path.join(d, cli_session_id + ".jsonl")
        if os.path.isfile(candidate):
            return candidate
    return None


def join_lams_transcript(session_record, lams_registry_dir):
    """LAMS transcript path for a session record, or None.

    session record -> <sessionId>/audit.jsonl, in the SAME directory as the
    LAMS scheduled-tasks.json registry (confirmed: all 501/501 real
    audit.jsonl files sit at exactly this depth). Keyed on sessionId, NOT
    cliSessionId -- sessionId already carries the 'local_' prefix (spec
    Sec 3.4/3.5); do not re-add it.
    """
    session_id = (session_record or {}).get("sessionId")
    if not session_id or not lams_registry_dir:
        return None
    candidate = os.path.join(lams_registry_dir, session_id, "audit.jsonl")
    return candidate if os.path.isfile(candidate) else None


def load_session_records(registry_dir):
    """All local_*.json session records in a registry's directory, as a list
    of dicts. Unreadable files are skipped, never raise."""
    records = []
    for p in glob.glob(os.path.join(registry_dir or "", "local_*.json")):
        try:
            records.append(json.load(open(p, encoding="utf-8-sig")))
        except Exception:
            continue
    return records


def _min_cron_period(cron_expression):
    """Coarse minimum-period estimate for a 5-field cron expression, used
    only to flag an implausibly tight re-schedule -- not a full cron parser.
    Returns a timedelta, or None if the expression can't be classified."""
    if not cron_expression:
        return None
    fields = cron_expression.split()
    if len(fields) != 5:
        return None
    minute, hour = fields[0], fields[1]
    if minute.startswith("*/"):
        try:
            return timedelta(minutes=int(minute[2:]))
        except ValueError:
            return None
    if minute == "*":
        return timedelta(minutes=1)
    if hour == "*":
        return timedelta(hours=1)
    return timedelta(days=1)  # daily/weekly/monthly all lower-bound at 1 day


def detect_duplicates(runs, cc_task_ids_enabled, lams_task_ids_enabled):
    """Deterministic duplicate/collision flags across a set of run records
    (spec Sec 5 Stage 0). `runs` is a list of dicts each carrying at least
    fleet, task_id, run_id, last_scheduled_for (and cron_expression where
    recurring). Returns a list of flag dicts: {"type", "detail", "run_ids"}.

    Three flag types -- duplicate detection is a key comparison, never an
    agent's judgment call:
      - same_cycle_refire: two fires share one lastScheduledFor
      - cron_period_collision: two distinct lastScheduledFor values fall
        inside the same cron period for the same task
      - cross_fleet_twin: the same task id is enabled on BOTH registries
    """
    flags = []

    by_cycle = defaultdict(list)
    for r in runs:
        key = (r["fleet"], r["task_id"], r.get("last_scheduled_for"))
        by_cycle[key].append(r["run_id"])
    for (fleet, task_id, cycle), run_ids in by_cycle.items():
        if cycle and len(run_ids) > 1:
            flags.append({
                "type": "same_cycle_refire",
                "detail": "{} fired {} times for the same logical cycle {}".format(
                    task_id, len(run_ids), cycle),
                "run_ids": run_ids,
            })

    twins = set(cc_task_ids_enabled) & set(lams_task_ids_enabled)
    for task_id in sorted(twins):
        flags.append({
            "type": "cross_fleet_twin",
            "detail": "'{}' is enabled on BOTH the CC and LAMS registries -- "
                      "known dual-fleet double-fire hazard".format(task_id),
            "run_ids": [r["run_id"] for r in runs if r["task_id"] == task_id],
        })

    by_task = defaultdict(list)
    for r in runs:
        if r.get("cron_expression") and r.get("last_scheduled_for"):
            by_task[(r["fleet"], r["task_id"])].append(r)
    for (fleet, task_id), task_runs in by_task.items():
        times = sorted((_parse_iso(r["last_scheduled_for"]) for r in task_runs
                        if _parse_iso(r["last_scheduled_for"]) is not None))
        min_period = _min_cron_period(task_runs[0].get("cron_expression"))
        for a, b in zip(times, times[1:]):
            if a == b:
                continue  # identical lastScheduledFor is same_cycle_refire's flag, not this one
            if min_period is not None and (b - a) < min_period:
                flags.append({
                    "type": "cron_period_collision",
                    "detail": "{} scheduled twice ({} and {}) inside one cron "
                              "period ({})".format(task_id, a.isoformat(), b.isoformat(),
                                                    task_runs[0].get("cron_expression")),
                    "run_ids": [r["run_id"] for r in task_runs],
                })

    return flags
