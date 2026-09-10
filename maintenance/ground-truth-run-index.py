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


def _created_at_ms(rec):
    """A session record's createdAt as int epoch-ms, or None if absent or
    unparseable. Never raises."""
    ca = (rec or {}).get("createdAt")
    if ca is None:
        return None
    try:
        return int(ca)
    except (TypeError, ValueError):
        return None


def _sessions_claiming_task(task, session_records):
    """Every session record whose `scheduledTaskId` is EXACTLY this task's id.

    This is the real, present-in-the-data join key (see
    find_executing_session's docstring). A record whose scheduledTaskId names
    a task id absent from this fleet's registry -- a retired task, measured
    2026-09-11 at 72/753 CC and 38/301 LAMS records -- simply never matches
    any live task here, which is the correct outcome, not a gap.
    """
    task_id = (task or {}).get("id")
    if not task_id:
        return []
    return [r for r in session_records if r.get("scheduledTaskId") == task_id]


def find_executing_session(task, session_records, tolerance_ms=JOIN_TOLERANCE_MS):
    """Identify which session record executed a task's most recent firing.

    PRIMARY KEY -- `scheduledTaskId`. Every session record created by a
    scheduled firing carries `scheduledTaskId` set to the executing task's id
    VERBATIM. This is an exact-match key, not an inference. Measured on the
    live stores 2026-09-11: present on 753/1,288 CC records (58.5%) and
    301/501 LAMS records (60.1%) -- 1,054/1,789 overall; the balance are
    ordinary interactive sessions, which have no task to name.

      - Exactly one record claims this task id -> that IS the executing
        session. Returned immediately; no createdAt or title check is needed,
        because the id match already IS the disambiguation.
      - More than one claims it (the normal case -- a daily task accumulates
        one record per firing; measured up to n=105 for ora-aaos-expire-
        leases) -> tiebreak among these CONFIRMED candidates by whichever
        `createdAt` is closest to the task's `lastRunAt`. This is a choice
        among records already proven to belong to this task, not a heuristic
        guess across the whole session population. Measured across all 55
        in-window tasks on both fleets 2026-09-11, the winning candidate sat
        0-2 ms from lastRunAt while the runner-up was never closer than
        ~82,000,000 ms (~23 h) -- the tiebreak is unambiguous by seven orders
        of magnitude. (Residual risk, documented rather than hidden: if the
        true firing's record has been deleted or archived away, the tiebreak
        will silently return the PREVIOUS firing's record. The 0-vs-23h gap
        above is what makes that detectable downstream, not something this
        function can rule out on its own.)
      - Zero claim it -> fall back to the createdAt/title heuristic below.

    FALLBACK -- createdAt within `tolerance_ms` of lastRunAt, disambiguated by
    an auto-generated title. Retained ONLY for session records predating the
    `scheduledTaskId` field; it is the correct and only available key for
    those. Note its title branch cannot fire for any record that HAS a
    scheduledTaskId: measured 2026-09-11, `titleSource == "auto"` and
    `scheduledTaskId` are perfectly mutually exclusive on the CC store
    (397 auto / 0 of them with scheduledTaskId; 753 with scheduledTaskId /
    0 of them auto) and `titleSource` is absent from all 501 LAMS records.
    That is exactly why this can no longer be the primary path.

    NOT notifySessionId -- that field is a static "notify here" target fixed
    at registration/last-edit time (verified against 4 real tasks across both
    fleets: every notifySessionId record's createdAt predates the audited
    lastRunAt by weeks to months). Spec Sec 3.5a. notifySessionId was the
    trap the spec's first correction caught; `scheduledTaskId` -- the real
    primary key sitting in every record the whole time -- was the one that
    same correction MISSED, because the recon scripts printed a cherry-picked
    field subset and never the full key list. Corrected 2026-09-11 during
    final whole-branch review.

    `session_records` is an iterable of dicts as loaded from local_*.json
    (scheduledTaskId/createdAt/title/titleSource all optional per record).

    Returns the single matching session dict, or None if nothing resolves --
    ambiguity in the FALLBACK path is still never resolved by guessing.
    """
    last_run = _parse_iso(task.get("lastRunAt"))
    if last_run is None:
        return None
    target_ms = int(last_run.timestamp() * 1000)

    # --- primary: exact scheduledTaskId match -------------------------------
    claimants = _sessions_claiming_task(task, session_records)
    if len(claimants) == 1:
        return claimants[0]
    if len(claimants) > 1:
        def _distance(rec):
            ca_ms = _created_at_ms(rec)
            return abs(ca_ms - target_ms) if ca_ms is not None else float("inf")
        return min(claimants, key=_distance)

    # --- fallback: pre-scheduledTaskId-era records --------------------------
    # A record that CARRIES a scheduledTaskId has already declared which task
    # it belongs to, and (given we reached here) it is not this one -- so it
    # is excluded from the fallback pool outright. Without this the timing
    # heuristic will happily join another task's session whose createdAt
    # happens to land inside the tolerance window, which is a silent
    # cross-task mis-join, not a near miss.
    expected_title = (task.get("id") or "").replace("-", " ").capitalize()
    candidates = []
    for rec in session_records:
        if rec.get("scheduledTaskId"):
            continue
        ca_ms = _created_at_ms(rec)
        if ca_ms is None:
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


def find_all_sessions_for_task(task, session_records, window_seconds=300):
    """Every session record plausibly serving ONE firing of `task` -- the
    per-task-firing signal that duplicate detection needs.

    Filters `session_records` to those whose `scheduledTaskId` exactly equals
    the task's id, then keeps only those whose `createdAt` falls within
    `window_seconds` of the task's `lastRunAt` in EITHER direction. The time
    bound is what scopes this to "sessions attempting THIS firing" rather than
    the task's entire session history (a daily task accumulates one record per
    firing -- measured up to n=105 -- so the unbounded set is useless as a
    duplicate signal).

    WHY THIS IS THE ONLY REAL DUPLICATE EVIDENCE AVAILABLE: a genuine
    same-cycle re-fire means the host executed one logical cron slot twice.
    That produces TWO session records both stamped with the same
    `scheduledTaskId` and both created near the same firing time -- direct,
    observable evidence of two executions. The registry cannot express this at
    all: it holds exactly ONE row per task id and OVERWRITES `lastRunAt` and
    `lastScheduledFor` on every fire, so a re-fire leaves no second row behind.
    Counting registry rows within a single build_run_index() call therefore can
    never detect a duplicate -- verified 2026-09-11, 38/38 CC and 29/29 LAMS
    task ids unique, zero registry-level duplicates -- which is precisely why
    the old row-comparison form of `same_cycle_refire` was structurally dead
    code. This function replaces that inference with the session-record
    population the old code loaded and then discarded after picking one winner.

    Returns a list of 0, 1, or more session dicts. Never raises.
    """
    last_run = _parse_iso((task or {}).get("lastRunAt"))
    if last_run is None:
        return []
    target_ms = int(last_run.timestamp() * 1000)
    bound_ms = int(window_seconds * 1000)

    matches = []
    for rec in _sessions_claiming_task(task, session_records):
        ca_ms = _created_at_ms(rec)
        if ca_ms is None:
            continue
        if abs(ca_ms - target_ms) <= bound_ms:
            matches.append(rec)
    return matches


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
    fleet, task_id, run_id, last_scheduled_for, candidate_session_count (and
    cron_expression where recurring). Returns a list of flag dicts:
    {"type", "detail", "run_ids"}.

    Three flag types -- duplicate detection is a key comparison, never an
    agent's judgment call:
      - same_cycle_refire: MORE THAN ONE session record claims this task's
        firing (run["candidate_session_count"] > 1) -- see
        find_all_sessions_for_task. This is direct evidence of two executions.
        It replaces the original form of this check, which compared multiple
        REGISTRY ROWS within one build_run_index() call and was structurally
        dead: the registry holds one row per task id and overwrites it on each
        fire, so one call can never contain two rows for one task (verified
        2026-09-11: 38/38 CC and 29/29 LAMS ids unique).
      - cron_period_collision: two distinct lastScheduledFor values fall
        inside the same cron period for the same task -- DORMANT within a
        single invocation, see its own note below.
      - cross_fleet_twin: the same task id is enabled on BOTH registries.
        Unaffected by the above -- each fleet's registry is a separate
        one-row-per-task source, so comparing enabled-id SETS across the two
        is a real, working per-invocation check.
    """
    flags = []

    for r in runs:
        count = r.get("candidate_session_count") or 0
        if count > 1:
            flags.append({
                "type": "same_cycle_refire",
                "detail": "{} session records both claim to have executed {}'s "
                          "firing at {} -- {} of these are likely duplicate "
                          "executions".format(count, r["task_id"],
                                              r.get("last_run_at"), count - 1),
                "run_ids": [r["run_id"]],
            })

    twins = set(cc_task_ids_enabled) & set(lams_task_ids_enabled)
    for task_id in sorted(twins):
        flags.append({
            "type": "cross_fleet_twin",
            "detail": "'{}' is enabled on BOTH the CC and LAMS registries -- "
                      "known dual-fleet double-fire hazard".format(task_id),
            "run_ids": [r["run_id"] for r in runs if r["task_id"] == task_id],
        })

    # --- cron_period_collision ------------------------------------------
    # SCOPE, stated honestly rather than left as a silent no-op: this check
    # operates on a SEQUENCE of runs spanning MULTIPLE build_run_index()
    # invocations -- e.g. if Stage 0 is ever extended to accept a list of
    # prior nights' run-index documents as additional input, so that several
    # distinct last_scheduled_for values for one task can coexist in `runs`.
    # Within a SINGLE invocation it is DORMANT and never fires, because the
    # registry supplies exactly one last_scheduled_for per task per call
    # (one row per task id, overwritten on each fire) and this check requires
    # two DISTINCT values for the same task. That is a documented limitation
    # of the input, not a bug in the comparison -- the comparison itself is
    # correct and is kept ready for the multi-document input it was written
    # for. Do not "fix" it by re-deriving collisions from registry row counts;
    # that is exactly the dead-code pattern same_cycle_refire was rebuilt to
    # escape (final-review C2, 2026-09-11).
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


def assert_join_rate_floor(joined_count, total_count, window_hours,
                            default_hours=DEFAULT_WINDOW_HOURS):
    """Width-dependent join-rate floor (spec Sec 9 R1a) -- NOT a non-zero
    check. Measured on the live CC store (spec Sec 3.5, all 17 project dirs):
    100% at n=100-200 recent sessions, ~43% fleet-wide. A widened window is
    expected to read lower; the SAME low rate on a normal 24h window means the
    join is broken.

    Floor schedule:
      - window_hours <= default_hours (normal night): >= 90%
      - window_hours <= default_hours * 3 (a moderate widen): >= 60%
      - wider than that (a multi-day catch-up burst): >= 30%

    Returns (ok: bool, message: str). total_count == 0 is trivially ok (an
    empty window has nothing to fail to join).
    """
    if total_count == 0:
        return True, "no runs in window -- floor not applicable"
    rate = joined_count / total_count
    if window_hours <= default_hours:
        floor = 0.90
    elif window_hours <= default_hours * 3:
        floor = 0.60
    else:
        floor = 0.30
    ok = rate >= floor
    msg = "{}/{} joined ({:.0%}) against a {:.0%} floor for a {:.1f}h window".format(
        joined_count, total_count, rate, floor, window_hours)
    return ok, msg


SELF_TASK_ID = "ora-ground-truth-auditor"
LAST_RUN_MARKER = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "_state", "ground-truth",
    "last-auditor-run.json")


def _read_last_auditor_run():
    try:
        d = json.load(open(LAST_RUN_MARKER, encoding="utf-8"))
        return _parse_iso(d.get("completed_at"))
    except Exception:
        return None


def _write_last_auditor_run(now):
    os.makedirs(os.path.dirname(LAST_RUN_MARKER), exist_ok=True)
    json.dump({"completed_at": now.strftime("%Y-%m-%dT%H:%M:%S.000Z")},
              open(LAST_RUN_MARKER, "w", encoding="utf-8"))


def _registry_tasks(registry_path):
    try:
        d = json.load(open(registry_path, encoding="utf-8-sig"))
    except Exception:
        return []
    return d.get("scheduledTasks", []) or []


def _registry_recorded_skips(registry_path):
    try:
        d = json.load(open(registry_path, encoding="utf-8-sig"))
    except Exception:
        return {}
    return d.get("recordedSkips", {}) or {}


def _in_window(task, window_start):
    ts = _parse_iso(task.get("lastRunAt"))
    return ts is not None and ts >= window_start


def build_run_index(cc_registry_path, lams_registry_path, project_dirs,
                     now=None, window_hours_override=None, last_auditor_run_at=None):
    """Stage 0 orchestrator -- produces the complete run-index document.

    `last_auditor_run_at` -- override for `_read_last_auditor_run()` (tests
    inject a controlled value here instead of depending on the real marker
    file; `None` means "use whatever the real file says", i.e. current
    default behavior is unchanged).

    Returns a dict:
      {
        "generated_at": iso str,
        "window_hours": float,
        "window_reason": str,
        "runs": [ { run_id, fleet, task_id, last_scheduled_for, last_run_at,
                    cron_expression, model, transcript, joined: bool,
                    recorded_skips: [...], file_path, session_model,
                    candidate_session_count: int }, ... ],
        "duplicate_flags": [ ... ],
        "join_stats": { "cc": {joined, total, rate_ok, message},
                         "lams": {...} },
      }
    """
    now = now or datetime.now(timezone.utc)
    cc_tasks_all = _registry_tasks(cc_registry_path)
    lams_tasks_all = _registry_tasks(lams_registry_path)

    if window_hours_override is not None:
        window_hours, window_reason = float(window_hours_override), "explicit --window-hours override"
    else:
        effective_last_run = last_auditor_run_at if last_auditor_run_at is not None else _read_last_auditor_run()
        window_hours, window_reason = decide_window_hours(
            now, effective_last_run, cc_tasks_all, lams_tasks_all)

    window_start = now - timedelta(hours=window_hours)

    cc_session_records = load_session_records(
        os.path.dirname(cc_registry_path) if cc_registry_path else None)
    lams_registry_dir = os.path.dirname(lams_registry_path) if lams_registry_path else None
    lams_session_records = load_session_records(lams_registry_dir)
    cc_recorded_skips = _registry_recorded_skips(cc_registry_path)
    lams_recorded_skips = _registry_recorded_skips(lams_registry_path)

    runs = []
    cc_joined = cc_total = 0
    lams_joined = lams_total = 0

    for fleet, tasks, session_records, skips in (
            ("cc", cc_tasks_all, cc_session_records, cc_recorded_skips),
            ("lams", lams_tasks_all, lams_session_records, lams_recorded_skips)):
        for t in tasks:
            task_id = t.get("id")
            if task_id == SELF_TASK_ID:
                continue  # self-exclusion (spec Sec 5 Stage 4)
            if not _in_window(t, window_start):
                continue
            session = find_executing_session(t, session_records)
            # Cheap -- reuses session_records already loaded above. Gives
            # detect_duplicates a REAL per-firing signal instead of counting
            # registry rows, which can never exceed 1 per task per call.
            matching_sessions = find_all_sessions_for_task(t, session_records)
            if fleet == "cc":
                transcript = join_cc_transcript(session, project_dirs) if session else None
                cc_total += 1
                if transcript:
                    cc_joined += 1
            else:
                transcript = join_lams_transcript(session, lams_registry_dir) if session else None
                lams_total += 1
                if transcript:
                    lams_joined += 1
            runs.append({
                "run_id": build_run_id(fleet, task_id, t.get("lastScheduledFor")),
                "fleet": fleet,
                "task_id": task_id,
                "last_scheduled_for": t.get("lastScheduledFor"),
                "last_run_at": t.get("lastRunAt"),
                "cron_expression": t.get("cronExpression"),
                "model": t.get("model"),
                "transcript": transcript,
                "joined": transcript is not None,
                "recorded_skips": skips.get(task_id, []),
                "file_path": t.get("filePath"),
                "session_model": (session.get("model") if session else None),
                "candidate_session_count": len(matching_sessions),
            })

    cc_enabled = {t.get("id") for t in cc_tasks_all if t.get("enabled")}
    lams_enabled = {t.get("id") for t in lams_tasks_all if t.get("enabled")}
    duplicate_flags = detect_duplicates(runs, cc_enabled, lams_enabled)

    cc_ok, cc_msg = assert_join_rate_floor(cc_joined, cc_total, window_hours)
    lams_ok, lams_msg = assert_join_rate_floor(lams_joined, lams_total, window_hours)

    return {
        "generated_at": now.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "window_hours": window_hours,
        "window_reason": window_reason,
        "runs": runs,
        "duplicate_flags": duplicate_flags,
        "join_stats": {
            "cc": {"joined": cc_joined, "total": cc_total, "rate_ok": cc_ok, "message": cc_msg},
            "lams": {"joined": lams_joined, "total": lams_total, "rate_ok": lams_ok, "message": lams_msg},
        },
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--window-hours", type=float, default=None,
                         help="Override automatic window sizing (ad-hoc investigation only).")
    parser.add_argument("--out", default=None,
                         help="Output path. Default: _state/ground-truth/run-index-<date>.json")
    parser.add_argument("--json", action="store_true",
                         help="Print the run index to stdout instead of writing a file.")
    args = parser.parse_args(argv)

    cc_path = _sd.discover_store("claude-code-sessions") if _sd else None
    lams_path = _sd.discover_store("local-agent-mode-sessions") if _sd else None
    project_dirs = find_project_dirs()

    now = datetime.now(timezone.utc)
    index = build_run_index(cc_path, lams_path, project_dirs, now=now,
                             window_hours_override=args.window_hours)

    if args.json:
        print(json.dumps(index, indent=2))
    else:
        out = args.out or os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "_state", "ground-truth",
            "run-index-{}.json".format(now.strftime("%Y-%m-%d")))
        os.makedirs(os.path.dirname(out), exist_ok=True)
        json.dump(index, open(out, "w", encoding="utf-8"), indent=2)
        print("wrote {} ({} runs, {} duplicate flags)".format(
            out, len(index["runs"]), len(index["duplicate_flags"])))

    _write_last_auditor_run(now)

    floor_failures = [f for f in (index["join_stats"]["cc"], index["join_stats"]["lams"])
                      if not f["rate_ok"]]
    if floor_failures:
        print("JOIN-RATE FLOOR BREACHED: " + "; ".join(f["message"] for f in floor_failures),
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
