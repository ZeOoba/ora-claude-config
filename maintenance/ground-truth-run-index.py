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
import re
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
PRIMARY_JOIN_BOUND_SECONDS = 300  # scheduledTaskId-path distance bound (spec Sec 3.5a
                                   # correction) -- shared by find_executing_session's
                                   # primary-path rejection and find_all_sessions_for_task's
                                   # default window, so the two bounds can't drift apart.


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

    Returns (window_hours: float, reason: str, widen_kind: str). `now` and
    `last_auditor_run_at` are aware UTC datetimes (or None for the latter).

    `widen_kind` is a machine-readable record of WHY the window was widened --
    one of "none", "auditor_gap", "resume_event", "both" -- consumed by
    assert_join_rate_floor to decide which floor tier applies (final-review
    I6, 2026-09-11). This matters because task selection in build_run_index
    keys on lastRunAt, not lastScheduledFor: a resume catch-up burst's own
    session records already carry a recent lastRunAt and are therefore fully
    captured by the plain default-hours window on their own -- the 3x widen
    below adds negligible coverage benefit for that burst itself (it does admit
    older, unrelated tasks whose lastRunAt falls in the wider window, where join
    quality is known to degrade with age -- spec Sec 3.5 -- but that population
    is small relative to a just-resumed fleet). A resume-only widen must
    NOT relax the join-rate floor the way a genuine auditor-gap widen
    legitimately does; see assert_join_rate_floor's docstring for the floor
    logic this feeds.
    """
    reasons = []
    window_hours = float(default_hours)
    gap_hours = None
    auditor_gap_widened = False

    if last_auditor_run_at is None:
        reasons.append("no prior auditor run recorded")
    else:
        gap_hours = (now - last_auditor_run_at).total_seconds() / 3600.0
        if gap_hours > default_hours:
            reasons.append(
                "prior auditor run was {:.1f}h ago (> {}h)".format(gap_hours, default_hours))
            window_hours = max(window_hours, gap_hours)
            auditor_gap_widened = True

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
        # re-enabled -- a bounded pause can span days. (Widening the window
        # is still correct here -- it's the FLOOR relaxation this widen used
        # to carry as a side effect that I6 decouples, not the widen itself.)
        window_hours = max(window_hours, default_hours * 3)

    if auditor_gap_widened and resume_hit:
        widen_kind = "both"
    elif auditor_gap_widened:
        widen_kind = "auditor_gap"
    elif resume_hit:
        widen_kind = "resume_event"
    else:
        widen_kind = "none"

    if not reasons:
        return (float(default_hours),
                "default {}h window (no widen condition met)".format(default_hours),
                widen_kind)
    return window_hours, "; ".join(reasons), widen_kind


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

      - Exactly one record claims this task id -> candidate for the executing
        session, BUT still gated by the same `PRIMARY_JOIN_BOUND_SECONDS`
        (300s) distance check as the tiebreak below: if its `createdAt` is
        more than that far from the task's `lastRunAt`, it is rejected and
        this function returns None overall (NOT a fall-through to the
        fallback pool below -- the fallback is for records with NO
        scheduledTaskId at all, not for a scheduledTaskId record that failed
        this check). Measured on live data, the true firing's session record
        is always within 2ms of lastRunAt; the closest ever-observed
        unrelated record is ~23h away, so 300s costs zero real joins while
        closing a real risk: if a task's true firing record is ever deleted
        or archived and an older, unrelated record with the same id happens
        to survive, an unbounded return would silently join to it rather
        than correctly reporting unjoined.
      - More than one claims it (the normal case -- a daily task accumulates
        one record per firing; measured up to n=105 for ora-aaos-expire-
        leases) -> tiebreak among these CONFIRMED candidates by whichever
        `createdAt` is closest to the task's `lastRunAt`, THEN the same
        300s bound is applied to the winner -- a nearest-of-N pick is still
        just a guess if even the nearest candidate is a day away. This is a
        choice among records already proven to belong to this task, not a
        heuristic guess across the whole session population. Measured across
        all 55 in-window tasks on both fleets 2026-09-11, the winning
        candidate sat 0-2 ms from lastRunAt while the runner-up was never
        closer than ~82,000,000 ms (~23 h) -- the tiebreak is unambiguous by
        seven orders of magnitude, and 300s (150,000x the observed true-match
        distance) sits comfortably below that runner-up floor. (Residual risk,
        documented rather than hidden: if the true firing's record has been
        deleted or archived away AND a different stale record for the same
        task id happens to sit within 300s of lastRunAt, the tiebreak could
        still silently return that stale record. The 0-vs-23h gap above is
        what makes this scenario implausible on measured data, not something
        this function can rule out in principle.)
      - Zero claim it -> fall back to the createdAt/title heuristic below.
        (A sole or winning claimant that FAILS the 300s bound does NOT fall
        through here -- it returns None directly, above. The fallback pool
        below is scoped to records with no scheduledTaskId at all; a record
        that named this task id and simply sat too far from lastRunAt is not
        that, and re-admitting it to the fallback pool would just reintroduce
        the silent-stale-join risk the bound exists to close.)

    FALLBACK -- createdAt within `tolerance_ms` of lastRunAt, disambiguated by
    an auto-generated title. Exists for session records that never carry
    `scheduledTaskId` at all -- ordinary interactive/non-scheduled sessions,
    for which it is the correct and only available key. This is NOT a
    "pre-scheduledTaskId-era" path: a reviewer measured the actual createdAt
    date ranges in both stores and found no temporal boundary between
    scheduledTaskId-carrying and non-carrying records -- they are interleaved
    across the same date range in both fleets, because field presence tracks
    session TYPE (scheduled vs. interactive), not time. Measured 2026-09-11,
    every current task with a lastRunAt has at least one scheduledTaskId-
    carrying claimant, so this fallback is never actually reached on live
    data today -- it is dead-but-correct defensive code for a data shape
    (a task whose only session records lack scheduledTaskId) that doesn't
    currently occur, not a live legacy path. Note its title branch cannot
    fire for any record that HAS a scheduledTaskId: measured 2026-09-11,
    `titleSource == "auto"` and `scheduledTaskId` are perfectly mutually
    exclusive on the CC store (397 auto / 0 of them with scheduledTaskId;
    753 with scheduledTaskId / 0 of them auto) and `titleSource` is absent
    from all 501 LAMS records. That is exactly why this can no longer be the
    primary path.

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
    def _distance(rec):
        ca_ms = _created_at_ms(rec)
        return abs(ca_ms - target_ms) if ca_ms is not None else float("inf")

    claimants = _sessions_claiming_task(task, session_records)
    primary_bound_ms = PRIMARY_JOIN_BOUND_SECONDS * 1000
    if len(claimants) == 1:
        if _distance(claimants[0]) <= primary_bound_ms:
            return claimants[0]
        return None  # stale/unrelated claimant -- do NOT fall through to the fallback pool
    if len(claimants) > 1:
        winner = min(claimants, key=_distance)
        if _distance(winner) <= primary_bound_ms:
            return winner
        return None  # nearest candidate is still too far -- do NOT fall through

    # --- fallback: records that never carry scheduledTaskId -----------------
    # A record that CARRIES a scheduledTaskId has already declared which task
    # it belongs to, and (given we reached here) it is not this one -- so it
    # is excluded from the fallback pool outright. Without this the timing
    # heuristic will happily join another task's session whose createdAt
    # happens to land inside the tolerance window, which is a silent
    # cross-task mis-join, not a near miss. Presence, not truthiness: a
    # record with scheduledTaskId "" or None has still declared an owner
    # (even if that value is falsy) and must still be excluded.
    expected_title = (task.get("id") or "").replace("-", " ").capitalize()
    candidates = []
    for rec in session_records:
        if "scheduledTaskId" in rec:
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


def find_all_sessions_for_task(task, session_records, window_seconds=PRIMARY_JOIN_BOUND_SECONDS):
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
                            default_hours=DEFAULT_WINDOW_HOURS,
                            widen_kind="auditor_gap"):
    """Width-dependent join-rate floor (spec Sec 9 R1a) -- NOT a non-zero
    check. Measured on the live CC store (spec Sec 3.5, all 17 project dirs):
    100% at n=100-200 recent sessions, ~43% fleet-wide. A widened window is
    expected to read lower; the SAME low rate on a normal 24h window means the
    join is broken.

    `widen_kind` -- one of "none", "auditor_gap", "resume_event", "both", the
    third element decide_window_hours returns -- decides WHICH floor tier
    applies, not just how wide the window got (final-review I6, 2026-09-11).
    Defaults to "auditor_gap" so existing direct callers of this function
    alone (tests keyed purely on window_hours) keep today's width-only
    behavior unchanged.

    Why WHY matters, not just HOW WIDE: task selection in build_run_index is
    keyed on lastRunAt, not lastScheduledFor -- a resume catch-up burst's own
    session records are created minutes after the resume event, so they
    already carry a recent lastRunAt and are FULLY captured by the plain
    default-hours window on their own. The 3x resume widen therefore adds no
    real coverage benefit for that burst. If a pure resume_event widen were
    still allowed to relax the floor to 60%/30%, it would make the floor MORE
    PERMISSIVE on exactly the run the design calls "the single richest
    idempotency target available" (spec) -- backwards from the intent. A
    genuine "auditor_gap" widen (or "both", where the gap justification still
    applies) is a real multi-day catch-up where lower join rates are
    structurally expected (spec Sec 3.5/R1a), so it keeps the looser tiers.

    Floor schedule:
      - widen_kind == "resume_event" (no auditor gap): >= 90% ALWAYS,
        regardless of window_hours -- see above.
      - otherwise, width-dependent as before:
          - window_hours <= default_hours (normal night): >= 90%
          - window_hours <= default_hours * 3 (a moderate widen): >= 60%
          - wider than that (a multi-day catch-up burst): >= 30%

    Returns (ok: bool, message: str). total_count == 0 is trivially ok (an
    empty window has nothing to fail to join).
    """
    if total_count == 0:
        return True, "no runs in window -- floor not applicable"
    rate = joined_count / total_count
    if widen_kind == "resume_event":
        floor = 0.90
    elif window_hours <= default_hours:
        floor = 0.90
    elif window_hours <= default_hours * 3:
        floor = 0.60
    else:
        floor = 0.30
    ok = rate >= floor
    msg = "{}/{} joined ({:.0%}) against a {:.0%} floor for a {:.1f}h window (widen_kind={})".format(
        joined_count, total_count, rate, floor, window_hours, widen_kind)
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


_RUN_INDEX_FILENAME_RE = re.compile(r"^run-index-(\d{4}-\d{2}-\d{2})\.json$")

# OI-296 review round 2 (I1/I2/I8): "published" is no longer a sibling
# digest-<date>.html file's mere existence on disk -- an HTML file can be
# written and never actually emailed (send-via-outlook.ps1 retries, a
# transient SMTP failure, a killed process before the send step). The real
# published signal is send-via-outlook.ps1's own append-only send log, which
# gets a line ONLY on a confirmed successful send. Real line shape (verified
# against the live log 2026-09-13):
#   2026-09-13T09:21:33-04:00 [OK] Sent to=ggoldberg@oxfordra.net cc=none \
#       subject="[ORA] Ground-Truth Audit -- 2026-09-13" bytes=14030 format=html
_GT_DIGEST_SUBJECT_PREFIX = "[ORA] Ground-Truth Audit"
_SEND_LOG_LINE_RE = re.compile(r'^(?P<ts>\S+)\s+\[OK\]\s+Sent\b.*?subject="(?P<subject>[^"]*)"')


def _default_send_log_path():
    """The real send-via-outlook.ps1 send log, resolved relative to this
    file (maintenance/) rather than hardcoded, so the worktree/checkout the
    code actually lives in is what gets read."""
    return os.path.normpath(os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..",
        "scheduled-tasks", "_shared", "send-log.txt"))


def load_ground_truth_digest_sends(send_log_path):
    """Every confirmed-successful Ground-Truth Audit digest send, as a
    sorted list of aware UTC datetimes.

    Matches a line iff it starts with an ISO8601-with-offset timestamp,
    carries the literal `[OK] Sent` status (send-via-outlook.ps1 appends this
    ONLY after a confirmed send -- never for a queued/attempted/failed one),
    and has a `subject="..."` whose text starts with
    `"[ORA] Ground-Truth Audit"`. The digest's date separator has varied
    ("--" vs an em dash "-- "/"—") across send-via-outlook.ps1 revisions; a
    plain prefix check tolerates both without caring which one is in use.

    Returns (sends, warning):
      - sends: [] on a genuinely empty/no-matching-lines log (not an error --
        a real "nothing sent yet" state).
      - warning: None on success (file present and readable, regardless of
        how many lines matched), or a human-readable string when the log
        itself could not be read at all (missing path or an OS-level read
        failure). Never raises.
    """
    if not send_log_path or not os.path.isfile(send_log_path):
        return [], ("previously_audited: send log not found at {} -- dedup disabled "
                     "(nothing treated as previously audited)".format(send_log_path))
    try:
        raw_lines = open(send_log_path, encoding="utf-8", errors="replace").readlines()
    except OSError as e:
        return [], ("previously_audited: send log at {} could not be read ({}) -- "
                     "dedup disabled".format(send_log_path, e))

    sends = []
    for line in raw_lines:
        m = _SEND_LOG_LINE_RE.match(line)
        if not m:
            continue
        if not m.group("subject").startswith(_GT_DIGEST_SUBJECT_PREFIX):
            continue
        try:
            ts = datetime.fromisoformat(m.group("ts"))
        except ValueError:
            continue
        if ts.tzinfo is None:
            continue  # can't safely convert an offset-less timestamp -- skip rather than guess
        sends.append(ts.astimezone(timezone.utc))
    sends.sort()
    return sends, None


def load_previously_audited(state_dir, now, window_hours=DEFAULT_WINDOW_HOURS, send_log_path=None):
    """Collects run_ids already audited AND actually PUBLISHED (sent) by a
    prior night's digest (OI-296; review round 2 replaced the original
    "sibling digest-<date>.html exists" signal -- a written-but-never-sent
    HTML file must not suppress a re-audit, and filename dates must never
    decide "prior" -- see the module comment above _GT_DIGEST_SUBJECT_PREFIX
    and this function's ordering logic below).

    A prior `run-index-<date>.json` document (its content, not its filename)
    counts as published iff:
      1. its `generated_at` is strictly earlier than `now`, AND
      2. there is a confirmed Ground-Truth Audit send (from
         load_ground_truth_digest_sends) whose UTC instant is
         >= that document's `generated_at`,
         <  the `generated_at` of the next-NEWER candidate document (if any),
         <= `now`.

    Candidate documents are ordered by their own `generated_at` field,
    NEVER by filename -- a same-day rerun can overwrite run-index-<date>.json
    with a newer generated_at, and an auditor can legitimately run more than
    once in one UTC calendar day; filename-date exclusion would either drop
    a legitimately-published same-day run or misattribute a send to the
    wrong document. `window_hours` only feeds a CHEAP prefilter (see below);
    it is never part of the correctness check itself.

    Returns (previously_audited, warnings):
      - previously_audited: dict run_id -> {
            "task_id", "fleet",
            "audited_in_digest": <UTC ISO string of the send that published it>,
            "digest_time": <aware UTC datetime of that same send>,
            "candidate_session_count": <int or None, as recorded THEN>,
            "has_transcript_size": <bool -- was transcript_size even a field
                in the prior record? False for index files predating this
                round of changes>,
            "transcript_size": <int, None, or absent-equivalent -- see
                has_transcript_size>,
            "transcript_mtime": <float or None, as recorded THEN>,
        }
        If a run_id is published by more than one candidate document, the
        one with the LATEST generated_at wins (most temporally relevant).
      - warnings: list[str] -- one entry per prior run-index file that could
        not be read/parsed, one if a document has no parseable
        `generated_at`, and one (with dedup entirely disabled -- see below)
        if the send log itself could not be read.

    Fails open, never raises: a missing state_dir, a missing/unreadable send
    log, or an unreadable/malformed prior run-index file is treated as
    "contributes nothing" -- a send-log read failure disables dedup for this
    call ENTIRELY (returns {} immediately) since without it nothing can be
    confirmed published; a corrupt individual run-index file only drops that
    one file. Both classes still append a warning so the anomaly is visible.
    """
    result = {}
    warnings = []
    if not state_dir or not os.path.isdir(state_dir):
        return result, warnings

    resolved_send_log_path = send_log_path if send_log_path is not None else _default_send_log_path()
    sends, send_log_warning = load_ground_truth_digest_sends(resolved_send_log_path)
    if send_log_warning is not None:
        warnings.append(send_log_warning)
        return result, warnings  # fail open -- nothing can be confirmed published without the log

    # Cheap prefilter (OI-296 review round 2, req 9): bound the number of
    # files even opened to a generous window around `now`, using the
    # FILENAME date only as an estimate -- correctness itself comes from
    # each document's own generated_at, checked below, never from this.
    horizon_days = (window_hours / 24.0) + 3.0
    today = now.date()

    candidates = []  # [(generated_at, doc), ...]
    for path in sorted(glob.glob(os.path.join(state_dir, "run-index-*.json"))):
        base = os.path.basename(path)
        m = _RUN_INDEX_FILENAME_RE.match(base)
        if not m:
            continue
        try:
            file_date = datetime.strptime(m.group(1), "%Y-%m-%d").date()
        except ValueError:
            continue
        if abs((file_date - today).days) > horizon_days:
            continue  # cheap prefilter only -- never the correctness check

        try:
            doc = json.load(open(path, encoding="utf-8"))
        except Exception as e:
            warnings.append(
                "previously_audited: could not read prior run-index {} -- "
                "treating its runs as NOT previously audited ({})".format(base, e))
            continue

        gen_at = _parse_iso(doc.get("generated_at"))
        if gen_at is None:
            warnings.append(
                "previously_audited: prior run-index {} has no parseable "
                "generated_at -- treating its runs as NOT previously "
                "audited".format(base))
            continue
        if gen_at >= now:
            continue  # not strictly prior to THIS run

        candidates.append((gen_at, doc))

    candidates.sort(key=lambda c: c[0])  # order by generated_at -- never by filename (req 8)

    for i, (gen_at, doc) in enumerate(candidates):
        next_gen_at = candidates[i + 1][0] if i + 1 < len(candidates) else None
        publish_time = None
        for s in sends:
            if s < gen_at:
                continue
            if next_gen_at is not None and s >= next_gen_at:
                continue
            if s > now:
                continue
            publish_time = s  # earliest qualifying send -- when this doc was first actually published
            break
        if publish_time is None:
            continue  # generated, maybe even rendered to HTML, but never actually sent

        for r in (doc.get("runs", []) or []):
            run_id = r.get("run_id")
            if not run_id:
                continue
            existing = result.get(run_id)
            if existing is None or gen_at >= existing["_generated_at"]:
                result[run_id] = {
                    "task_id": r.get("task_id"),
                    "fleet": r.get("fleet"),
                    "audited_in_digest": publish_time.isoformat(),
                    "digest_time": publish_time,
                    "candidate_session_count": r.get("candidate_session_count"),
                    "has_transcript_size": "transcript_size" in r,
                    "transcript_size": r.get("transcript_size"),
                    "transcript_mtime": r.get("transcript_mtime"),
                    "_generated_at": gen_at,
                }

    for entry in result.values():
        entry.pop("_generated_at", None)

    return result, warnings


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
                     now=None, window_hours_override=None, last_auditor_run_at=None,
                     ground_truth_state_dir=None, dedup_previously_audited=True,
                     send_log_path=None):
    """Stage 0 orchestrator -- produces the complete run-index document.

    `last_auditor_run_at` -- override for `_read_last_auditor_run()` (tests
    inject a controlled value here instead of depending on the real marker
    file; `None` means "use whatever the real file says", i.e. current
    default behavior is unchanged).

    `ground_truth_state_dir` -- override for where OI-296's
    load_previously_audited() looks for prior `run-index-*.json` files.
    `None` (the default) resolves to `os.path.dirname(LAST_RUN_MARKER)`, i.e.
    the real state dir -- tests inject a temp dir instead.

    `send_log_path` -- override for the send-via-outlook.ps1 send log OI-296
    review round 2 reads to confirm a prior index was actually PUBLISHED
    (sent), not merely generated. `None` resolves to the real
    scheduled-tasks/_shared/send-log.txt (see `_default_send_log_path`).

    `dedup_previously_audited` -- OI-296: when True (the default), a
    candidate run whose run_id was already audited AND actually published
    by a prior night's digest is skipped rather than re-selected (see
    load_previously_audited's docstring for the exact published-ness rule,
    and the re-include exceptions below). `False` is the `--no-dedup` escape
    hatch for ad-hoc re-audits -- it disables the skip entirely, restoring
    pre-OI-296 behavior.

    Returns a dict:
      {
        "generated_at": iso str,
        "window_hours": float,
        "window_reason": str,
        "window_widen_kind": str,
        "runs": [ { run_id, fleet, task_id, last_scheduled_for, last_run_at,
                    cron_expression, model, transcript, joined: bool,
                    transcript_size, transcript_mtime, recorded_skips: [...],
                    file_path, session_model,
                    candidate_session_count: int }, ... ],
        "duplicate_flags": [ ... ],
        "join_stats": { "cc": {joined, total, audited, rate_ok, message},
                         "lams": {...} },
        "previously_audited": [ {run_id, task_id, fleet, audited_in_digest}, ... ],
        "reaudited_after_prior_digest": [ {run_id, task_id, fleet,
                    audited_in_digest, reason}, ... ],
        "warnings": [ str, ... ],
      }

    `window_widen_kind` -- one of "none", "auditor_gap", "resume_event",
    "both" (see decide_window_hours/assert_join_rate_floor docstrings, I6
    final review 2026-09-11) -- an explicit --window-hours override counts as
    "none" here: it is a manual choice, not a measured auditor-gap or
    resume-event widen, so it gets the same width-only floor tiers "none"
    gets from decide_window_hours (no special relaxation or extra strictness
    beyond window_hours itself).

    `join_stats["cc"/"lams"]["joined"/"total"]` (OI-296 review round 2, req 3):
    computed over EVERY in-window candidate BEFORE dedup -- the floor
    measures transcript-join health, a property of the fleet's own
    session/transcript plumbing, not of which runs this call happened to
    select for audit. `["audited"]` is the count AFTER dedup (== len of this
    fleet's entries in `runs`) -- how many actually got audited this call,
    distinct from how many were even candidates.

    `previously_audited`/`reaudited_after_prior_digest`/`warnings` (OI-296):
    a run skipped under the dedup rule is excluded from `runs` entirely --
    it never reaches detect_duplicates (which operates only on `runs`), and
    per req 3 above it also does not count toward `join_stats[...]["audited"]`
    (though it DOES still count toward `["joined"]`/`["total"]`). `warnings`
    carries one entry per prior file/send-log condition
    load_previously_audited() could not resolve (fail-open, never a crash --
    see its docstring).
    """
    now = now or datetime.now(timezone.utc)
    cc_tasks_all = _registry_tasks(cc_registry_path)
    lams_tasks_all = _registry_tasks(lams_registry_path)

    if window_hours_override is not None:
        window_hours, window_reason = float(window_hours_override), "explicit --window-hours override"
        widen_kind = "none"
    else:
        effective_last_run = last_auditor_run_at if last_auditor_run_at is not None else _read_last_auditor_run()
        window_hours, window_reason, widen_kind = decide_window_hours(
            now, effective_last_run, cc_tasks_all, lams_tasks_all)

    if dedup_previously_audited:
        state_dir = ground_truth_state_dir if ground_truth_state_dir is not None \
            else os.path.dirname(LAST_RUN_MARKER)
        previously_audited_index, warnings = load_previously_audited(
            state_dir, now, window_hours=window_hours, send_log_path=send_log_path)
    else:
        previously_audited_index, warnings = {}, []

    window_start = now - timedelta(hours=window_hours)

    cc_session_records = load_session_records(
        os.path.dirname(cc_registry_path) if cc_registry_path else None)
    lams_registry_dir = os.path.dirname(lams_registry_path) if lams_registry_path else None
    lams_session_records = load_session_records(lams_registry_dir)
    cc_recorded_skips = _registry_recorded_skips(cc_registry_path)
    lams_recorded_skips = _registry_recorded_skips(lams_registry_path)

    runs = []
    previously_audited_out = []
    reaudited_out = []
    cc_joined = cc_total = cc_audited = 0
    lams_joined = lams_total = lams_audited = 0

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
            else:
                transcript = join_lams_transcript(session, lams_registry_dir) if session else None

            # transcript_size/transcript_mtime (OI-296 review round 2, req 7):
            # recorded on EVERY run regardless of dedup, both for the current
            # index's own record and as the growth baseline a future night's
            # dedup will compare against.
            if transcript:
                try:
                    transcript_size = os.path.getsize(transcript)
                except OSError:
                    transcript_size = None
                try:
                    transcript_mtime = os.path.getmtime(transcript)
                except OSError:
                    transcript_mtime = None
            else:
                transcript_size = None
                transcript_mtime = None

            # join-rate floor measures transcript-join health across EVERY
            # in-window candidate, computed BEFORE dedup selection (OI-296
            # review round 2, req 3) -- a run skipped below still counts here.
            if fleet == "cc":
                cc_total += 1
                if transcript:
                    cc_joined += 1
            else:
                lams_total += 1
                if transcript:
                    lams_joined += 1

            run_id = build_run_id(fleet, task_id, t.get("lastScheduledFor"))

            # --- OI-296: skip a run a PRIOR PUBLISHED digest already audited
            # -- unless new evidence arrived after that publish: either a new
            # session claimed the same cycle (req 6) or the transcript grew
            # (req 7; falls back to the old mtime-vs-send-time comparison
            # only when the prior record predates the transcript_size field
            # -- back-compat with older index files). An unjoined run
            # (transcript is None) can never clear the size-growth check, so
            # it is always skipped when previously published.
            prior = previously_audited_index.get(run_id)
            if prior is not None:
                skip = True
                reason = None

                prior_session_count = prior.get("candidate_session_count")
                if prior_session_count is not None and len(matching_sessions) > prior_session_count:
                    skip = False
                    reason = "new session for same cycle after prior digest"

                if skip:
                    if prior.get("has_transcript_size"):
                        prior_size = prior.get("transcript_size")
                        if transcript_size is not None and (prior_size is None or transcript_size > prior_size):
                            skip = False
                            reason = "transcript grew after prior audit"
                    else:
                        prior_digest_time = prior.get("digest_time")
                        if (transcript_mtime is not None and prior_digest_time is not None
                                and transcript_mtime > prior_digest_time.timestamp()):
                            skip = False
                            reason = "transcript modified after prior digest"

                if skip:
                    previously_audited_out.append({
                        "run_id": run_id,
                        "task_id": task_id,
                        "fleet": fleet,
                        "audited_in_digest": prior["audited_in_digest"],
                    })
                    continue  # excluded from runs/"audited" -- NOT from total/joined counted above
                reaudited_out.append({
                    "run_id": run_id,
                    "task_id": task_id,
                    "fleet": fleet,
                    "audited_in_digest": prior["audited_in_digest"],
                    "reason": reason,
                })

            if fleet == "cc":
                cc_audited += 1
            else:
                lams_audited += 1
            runs.append({
                "run_id": run_id,
                "fleet": fleet,
                "task_id": task_id,
                "last_scheduled_for": t.get("lastScheduledFor"),
                "last_run_at": t.get("lastRunAt"),
                "cron_expression": t.get("cronExpression"),
                "model": t.get("model"),
                "transcript": transcript,
                "joined": transcript is not None,
                "transcript_size": transcript_size,
                "transcript_mtime": transcript_mtime,
                "recorded_skips": skips.get(task_id, []),
                "file_path": t.get("filePath"),
                "session_model": (session.get("model") if session else None),
                "candidate_session_count": len(matching_sessions),
            })

    cc_enabled = {t.get("id") for t in cc_tasks_all if t.get("enabled")}
    lams_enabled = {t.get("id") for t in lams_tasks_all if t.get("enabled")}
    duplicate_flags = detect_duplicates(runs, cc_enabled, lams_enabled)

    cc_ok, cc_msg = assert_join_rate_floor(cc_joined, cc_total, window_hours, widen_kind=widen_kind)
    lams_ok, lams_msg = assert_join_rate_floor(lams_joined, lams_total, window_hours, widen_kind=widen_kind)

    return {
        "generated_at": now.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "window_hours": window_hours,
        "window_reason": window_reason,
        "window_widen_kind": widen_kind,
        "runs": runs,
        "duplicate_flags": duplicate_flags,
        "previously_audited": previously_audited_out,
        "reaudited_after_prior_digest": reaudited_out,
        "warnings": warnings,
        "join_stats": {
            "cc": {"joined": cc_joined, "total": cc_total, "audited": cc_audited,
                   "rate_ok": cc_ok, "message": cc_msg},
            "lams": {"joined": lams_joined, "total": lams_total, "audited": lams_audited,
                     "rate_ok": lams_ok, "message": lams_msg},
        },
    }


def resolve_registry_paths():
    """Resolves the CC and LAMS registry paths via store_discovery, returning
    (cc_path, lams_path, error) -- `error` is None on success, or a clear
    human-readable string naming which fleet failed and why (`_sd` unavailable
    -- the store_discovery import failed -- vs. `discover_store` ran but
    returned None for that fleet) when EITHER path could not be resolved.

    Extracted from main() so the exit-2 "could not even start" path (I3) is
    unit-testable via dependency injection / monkeypatching `_sd` without
    needing real registry files on disk."""
    if _sd is None:
        return None, None, (
            "registry discovery unavailable: store_discovery failed to import "
            "(_sd is None) -- cannot resolve either fleet's registry path")

    cc_path = _sd.discover_store("claude-code-sessions")
    lams_path = _sd.discover_store("local-agent-mode-sessions")

    failures = []
    if cc_path is None:
        failures.append("cc: discover_store('claude-code-sessions') returned None")
    if lams_path is None:
        failures.append("lams: discover_store('local-agent-mode-sessions') returned None")
    if failures:
        return cc_path, lams_path, "registry discovery failed -- " + "; ".join(failures)
    return cc_path, lams_path, None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--window-hours", type=float, default=None,
                         help="Override automatic window sizing (ad-hoc investigation only).")
    parser.add_argument("--out", default=None,
                         help="Output path. Default: _state/ground-truth/run-index-<date>.json")
    parser.add_argument("--json", action="store_true",
                         help="Print the run index to stdout instead of writing a file.")
    parser.add_argument("--no-dedup", action="store_true",
                         help="Disable the OI-296 previously-audited-run skip (ad-hoc "
                              "re-audits only) -- applies to --window-hours and --json too.")
    args = parser.parse_args(argv)

    cc_path, lams_path, discovery_error = resolve_registry_paths()
    if discovery_error is not None:
        # Fail LOUD, not empty: without this check, a total registry-read
        # failure (_sd is None, or discover_store returns None for either
        # fleet) fell through to _registry_tasks(None), whose try/except
        # swallows the resulting TypeError and returns [] -- producing 0
        # runs, both floors trivially "ok" (assert_join_rate_floor treats an
        # empty window as vacuously passing), and exit 0. That makes a
        # completely broken auditor indistinguishable from a genuinely quiet
        # night. Exit 2 is a NEW code, distinct from 0 (clean) and 1 (join-
        # rate floor breached), so a caller can tell "could not even start"
        # apart from both.
        print("GROUND-TRUTH AUDITOR COULD NOT START: " + discovery_error, file=sys.stderr)
        return 2
    project_dirs = find_project_dirs()

    now = datetime.now(timezone.utc)
    # --window-hours and --json are investigative overrides, not exemptions
    # from OI-296 dedup -- re-selecting an already-published run is still
    # wrong under either. Only --no-dedup disables it.
    index = build_run_index(cc_path, lams_path, project_dirs, now=now,
                             window_hours_override=args.window_hours,
                             dedup_previously_audited=not args.no_dedup)

    if args.json:
        print(json.dumps(index, indent=2))
    else:
        out = args.out or os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "_state", "ground-truth",
            "run-index-{}.json".format(now.strftime("%Y-%m-%d")))
        os.makedirs(os.path.dirname(out), exist_ok=True)
        json.dump(index, open(out, "w", encoding="utf-8"), indent=2)
        print("wrote {} ({} runs, {} duplicate flags, {} previously audited skipped)".format(
            out, len(index["runs"]), len(index["duplicate_flags"]),
            len(index["previously_audited"])))

    # Only a normal automatic run resets the "when did the auditor last run"
    # clock. --json is a read-only investigative dump (no run-index file is
    # even written), and --window-hours is an ad-hoc manual override (not the
    # real nightly cadence) -- either one writing the marker would silently
    # reset the gap-tracking clock that a REAL scheduled run depends on for
    # decide_window_hours' auditor-gap widen, potentially suppressing a
    # legitimate future widen because this ad-hoc invocation looked like the
    # last real run.
    if not args.json and args.window_hours is None:
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
