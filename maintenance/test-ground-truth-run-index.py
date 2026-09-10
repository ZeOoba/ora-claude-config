#!/usr/bin/env python3
"""Tests for ground-truth-run-index.py -- Stage 0 of the ground-truth auditor.

House style matches the other maintenance test rigs: plain python, no pytest.
Run: python test-ground-truth-run-index.py   (exit 0 = all pass)
"""
import importlib.util
import json
import os
import shutil
import sys
import tempfile
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "ground_truth_run_index", os.path.join(HERE, "ground-truth-run-index.py"))
gti = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gti)

FAILURES = []


def check(label, cond, detail=""):
    if cond:
        print("  [OK] %s" % label)
    else:
        print("  [FAIL] %s %s" % (label, detail))
        FAILURES.append(label)


def test_build_run_id_keys_on_last_scheduled_for():
    # The real AHM case (spec Sec 3.6): lastScheduledFor 15:05Z, lastRunAt
    # 17:13Z -- a catch-up fire 2h08m late. run_id must be built from
    # lastScheduledFor so this reads as the SAME logical cycle as any other
    # fire scheduled for the same slot, regardless of when it actually ran.
    rid = gti.build_run_id("lams", "automation-health-monitor", "2026-09-10T15:05:00.000Z")
    check("run_id uses lastScheduledFor verbatim",
          rid == "lams:automation-health-monitor:2026-09-10T15:05:00.000Z", rid)
    rid_again = gti.build_run_id("lams", "automation-health-monitor", "2026-09-10T15:05:00.000Z")
    check("two fires of the same lastScheduledFor produce the SAME run_id "
          "(this is what makes duplicate detection possible)", rid == rid_again)


def test_window_default_when_nothing_widens():
    now = datetime(2026, 9, 10, 12, 0, tzinfo=timezone.utc)
    last_run = now - timedelta(hours=6)  # auditor ran 6h ago, well inside 24h
    hours, reason = gti.decide_window_hours(now, last_run, [], [])
    check("default window when auditor is current and no resume in range",
          hours == 24.0, "hours=%s reason=%s" % (hours, reason))


def test_window_widens_when_auditor_gap_exceeds_default():
    # Fixture: catch-up burst -- the auditor itself was paused/host-closed for
    # 3 days, so its own last run is 72h old.
    now = datetime(2026, 9, 11, 4, 0, tzinfo=timezone.utc)
    last_run = now - timedelta(hours=72)
    hours, reason = gti.decide_window_hours(now, last_run, [], [])
    check("window widens to cover the auditor's own gap",
          hours >= 72.0, "hours=%s reason=%s" % (hours, reason))
    check("reason names the gap", "prior auditor run" in reason, reason)


def test_window_widens_on_fleet_resume_event():
    # Fixture: the 2026-09-11 16:01 ET fleet resume -- a one-time task with no
    # cronExpression, id containing 'resume', that just fired.
    now = datetime(2026, 9, 11, 16, 5, tzinfo=timezone.utc)
    resume_task = {
        "id": "ora-routine-pause-resume-2026-09-11",
        "enabled": True,
        "lastRunAt": "2026-09-11T16:01:00.000Z",
        # no cronExpression -- one-time
    }
    hours, reason = gti.decide_window_hours(now, now - timedelta(hours=1),
                                             [resume_task], [])
    check("window widens on a fleet-resume event even when the auditor itself "
          "is current", hours > 24.0, "hours=%s reason=%s" % (hours, reason))
    check("reason names the resume task", "fleet-resume event" in reason, reason)


def test_recurring_task_named_resume_does_not_widen():
    # A recurring task that happens to have 'resume' in its id must NOT be
    # mistaken for a one-time fleet-resume marker.
    now = datetime(2026, 9, 10, 12, 0, tzinfo=timezone.utc)
    recurring = {
        "id": "ora-resume-watch",
        "enabled": True,
        "cronExpression": "0 * * * *",
        "lastRunAt": "2026-09-10T11:59:00.000Z",
    }
    hours, reason = gti.decide_window_hours(now, now - timedelta(hours=1), [recurring], [])
    check("a RECURRING task named *resume* does not trigger the resume widen",
          hours == 24.0, "hours=%s reason=%s" % (hours, reason))


def test_never_ran_does_not_widen_without_a_resume_event():
    # Confirmed with Gabriel 2026-09-11: a literal never-ran (no prior
    # auditor run at all) does NOT by itself widen the window -- there is
    # no measurable gap, and the realistic backfill case (mid-pause
    # registration) is covered separately by the resume-event widen path.
    now = datetime(2026, 9, 10, 4, 0, tzinfo=timezone.utc)
    hours, reason = gti.decide_window_hours(now, None, [], [])
    check("never-ran with no resume event stays at the default window",
          hours == 24.0, "hours=%s reason=%s" % (hours, reason))
    check("the reason still names the never-ran condition for visibility",
          "no prior auditor run" in reason, reason)


# ---------------------------------------------------------------------------
# find_executing_session -- PRIMARY path (scheduledTaskId)
#
# Fixtures below are shaped on records actually dumped from the live stores on
# 2026-09-11, not hand-typed guesses. Two properties of the real data drive
# their shape and must not be "tidied" away:
#   * `scheduledTaskId` holds the executing task's id VERBATIM. Present on
#     753/1,288 CC records and 301/501 LAMS records (1,054/1,789 overall);
#     the balance are ordinary interactive sessions with no task to name.
#   * a record carrying `scheduledTaskId` has `titleSource` ABSENT/None --
#     always. On the CC store the two are perfectly mutually exclusive
#     (397 titleSource=="auto", none of them with scheduledTaskId), and
#     `titleSource` does not appear on any of the 501 LAMS records at all.
#     Fabricating `titleSource: "auto"` onto a scheduled-run fixture is the
#     exact defect that let a dead heuristic pass two review rounds.
# ---------------------------------------------------------------------------

def _real_shaped_session(scheduled_task_id, created_at_ms, title,
                          session_id="local_e59d1b67-bf90-4e6b-9883-3e8a52dec80c",
                          cli_session_id="696009a7-1727-470b-917d-51df0ec81803",
                          model="claude-sonnet-5"):
    """A session record shaped like a REAL scheduled-run record. Note
    titleSource is None, matching every real record that carries a
    scheduledTaskId -- never "auto"."""
    return {"sessionId": session_id, "cliSessionId": cli_session_id,
            "scheduledTaskId": scheduled_task_id, "createdAt": created_at_ms,
            "lastActivityAt": created_at_ms + 2556930, "title": title,
            "titleSource": None, "model": model, "isArchived": False}


def test_find_executing_session_primary_key_is_scheduled_task_id():
    # Real values (live LAMS store, 2026-09-10): automation-health-monitor's
    # lastRunAt is 2026-09-10T17:13:10.632Z and its session record carries
    # scheduledTaskId "automation-health-monitor" with createdAt 1789060390632.
    task = {"id": "automation-health-monitor", "lastRunAt": "2026-09-10T17:13:10.632Z"}
    records = [
        # decoy: same firing instant, but it names a DIFFERENT task
        _real_shaped_session("ora-cowork-heartbeat", 1789060390632,
                             "Ora cowork heartbeat", cli_session_id="wrong-task"),
        _real_shaped_session("automation-health-monitor", 1789060390632,
                             "Automation health monitor"),
    ]
    found = gti.find_executing_session(task, records)
    check("exact scheduledTaskId match selects the executing session",
          found is not None and found["cliSessionId"] == "696009a7-1727-470b-917d-51df0ec81803",
          found)


def test_find_executing_session_single_claimant_needs_no_title_check():
    # The id match IS the disambiguation (no title check needed) as long as
    # the lone claimant clears the 300s PRIMARY_JOIN_BOUND_SECONDS distance
    # check -- here it's ~90s off, comfortably inside the bound but far
    # outside the old 2s createdAt tolerance the pre-scheduledTaskId primary
    # path required.
    task = {"id": "ora-capex-idea-stage-nudge", "lastRunAt": "2026-09-10T17:13:10.632Z"}
    records = [_real_shaped_session("ora-capex-idea-stage-nudge",
                                     1789060390632 - 90_000,  # ~90s off
                                     "Ora capex idea stage nudge", cli_session_id="lone")]
    found = gti.find_executing_session(task, records)
    check("a single scheduledTaskId claimant within the 300s bound is "
          "returned without any title check",
          found is not None and found["cliSessionId"] == "lone", found)


def test_find_executing_session_single_claimant_beyond_bound_is_unjoined():
    # Fix 1 (2026-09-11 hardening): the primary path is no longer unbounded.
    # A lone claimant whose createdAt sits ~1 year from lastRunAt (far beyond
    # the measured ~23h worst-case unrelated distance) must be REJECTED, not
    # silently returned as if it were the true firing's record -- exactly the
    # silent-stale-join risk PRIMARY_JOIN_BOUND_SECONDS exists to close.
    task = {"id": "ora-capex-idea-stage-nudge", "lastRunAt": "2026-09-10T17:13:10.632Z"}
    t_ms = 1789060390632
    year_ms = 365 * 24 * 60 * 60 * 1000
    records = [
        _real_shaped_session("ora-capex-idea-stage-nudge", t_ms - year_ms,
                             "Ora capex idea stage nudge", cli_session_id="stale-lone"),
        # fallback-eligible decoy: no scheduledTaskId, createdAt exactly on
        # lastRunAt -- if the rejected primary claimant fell through to the
        # fallback pool, this decoy would be wrongly picked up instead.
        {"createdAt": t_ms, "title": "Ora capex idea stage nudge", "titleSource": "auto",
         "cliSessionId": "fallback-decoy"},
    ]
    found = gti.find_executing_session(task, records)
    check("a single claimant ~1 year from lastRunAt is rejected, not returned",
          found is None, found)
    check("rejection does NOT fall through to the fallback pool (the decoy "
          "is never picked)", found is None and (found is None or
          found.get("cliSessionId") != "fallback-decoy"), found)


def test_find_executing_session_tiebreak_winner_beyond_bound_is_unjoined():
    # Same hardening, multi-claimant path: even the NEAREST of several
    # confirmed claimants must clear the 300s bound. If the true firing's
    # record were deleted/archived and only a stale claimant survived, an
    # unbounded tiebreak would silently return it.
    task = {"id": "ora-doctrine-integrity-guard", "lastRunAt": "2026-09-10T17:13:10.632Z"}
    t_ms = 1789060390632
    year_ms = 365 * 24 * 60 * 60 * 1000
    records = [
        _real_shaped_session("ora-doctrine-integrity-guard", t_ms - year_ms,
                             "Ora doctrine integrity guard", cli_session_id="stale-a"),
        _real_shaped_session("ora-doctrine-integrity-guard", t_ms - year_ms - 5_000,
                             "Ora doctrine integrity guard", cli_session_id="stale-b"),
        # fallback-eligible decoy, present to confirm no fall-through happens
        {"createdAt": t_ms, "title": "Ora doctrine integrity guard", "titleSource": "auto",
         "cliSessionId": "fallback-decoy"},
    ]
    found = gti.find_executing_session(task, records)
    check("the nearest of several stale claimants is still rejected past the "
          "300s bound", found is None, found)


def test_find_executing_session_tiebreaks_claimants_by_nearest_created_at():
    # The NORMAL case on real data: a daily task accumulates one record per
    # firing (measured up to n=105). Tiebreak is among records already proven
    # to belong to THIS task -- not a guess across the whole population.
    # Measured 2026-09-11: winner sits 0-2ms out, runner-up never closer than
    # ~82,000,000ms (~23h).
    t_ms = 1789060390632
    task = {"id": "ora-doctrine-integrity-guard", "lastRunAt": "2026-09-10T17:13:10.632Z"}
    records = [
        _real_shaped_session("ora-doctrine-integrity-guard", t_ms - 85_897_807,
                             "Ora doctrine integrity guard", cli_session_id="yesterday"),
        _real_shaped_session("ora-doctrine-integrity-guard", t_ms + 1,
                             "Ora doctrine integrity guard", cli_session_id="this-firing"),
        _real_shaped_session("ora-doctrine-integrity-guard", t_ms - 171_795_614,
                             "Ora doctrine integrity guard", cli_session_id="two-days-ago"),
    ]
    found = gti.find_executing_session(task, records)
    check("among multiple confirmed claimants, the nearest createdAt to "
          "lastRunAt wins", found is not None and found["cliSessionId"] == "this-firing",
          found)


def test_find_executing_session_never_claims_another_tasks_session():
    # A record claiming a DIFFERENT task must not be joined, even when its
    # createdAt lands exactly on this task's lastRunAt -- the old heuristic
    # would have taken it.
    task = {"id": "ora-am-brief", "lastRunAt": "2026-09-10T17:13:10.632Z"}
    records = [_real_shaped_session("ora-pm-ledger", 1789060390632,
                                     "Ora pm ledger", cli_session_id="other-task")]
    found = gti.find_executing_session(task, records)
    check("a session claiming a different scheduledTaskId is never selected, "
          "even at an exact createdAt hit", found is None, found)


# ---------------------------------------------------------------------------
# find_executing_session -- FALLBACK path (pre-scheduledTaskId-era records)
#
# The four tests below deliberately use records with NO `scheduledTaskId` key.
# That omission is INTENTIONAL and load-bearing, not another accidental gap:
# it is what makes these records represent the pre-field era the createdAt/
# title heuristic still exists to serve. Any record here that grew a
# scheduledTaskId would silently stop testing the fallback.
# ---------------------------------------------------------------------------

def test_fallback_find_executing_session_matches_by_createdat_and_title():
    # FALLBACK path: no record carries scheduledTaskId, so the createdAt/title
    # heuristic is the only key available -- correct for pre-field records.
    task = {"id": "automation-health-monitor", "lastRunAt": "2026-09-10T17:13:10.632Z"}
    records = [
        # decoy: a notifySessionId-style stale record, months earlier
        {"createdAt": 1783537999843, "title": "Some old chat", "titleSource": "auto"},
        {"createdAt": 1789060390632, "title": "Automation health monitor", "titleSource": "auto",
         "sessionId": "local_e59d1b67-bf90-4e6b-9883-3e8a52dec80c",
         "cliSessionId": "696009a7-1727-470b-917d-51df0ec81803"},
    ]
    check("no fixture here carries scheduledTaskId -- these are pre-field-era "
          "records by design, so the fallback is what gets exercised",
          all("scheduledTaskId" not in r for r in records))
    found = gti.find_executing_session(task, records)
    check("fallback finds the session created at the same ms as lastRunAt",
          found is not None and found["cliSessionId"] == "696009a7-1727-470b-917d-51df0ec81803")


def test_fallback_find_executing_session_ambiguous_window_is_unjoined():
    # Catch-up burst: two pre-field-era sessions created inside the same 2s
    # tolerance window, neither titled for this task.
    task = {"id": "ora-weekly-hygiene", "lastRunAt": "2026-09-11T16:01:02.000Z"}
    t_ms = 1789142462000
    records = [
        {"createdAt": t_ms + 100, "title": "Ora deal sourcing scan", "titleSource": "auto"},
        {"createdAt": t_ms - 100, "title": "Ora pm ledger", "titleSource": "auto"},
    ]
    found = gti.find_executing_session(task, records)
    check("fallback: two candidates, neither titled for this task -> unjoined "
          "(never guessed)", found is None)


def test_fallback_find_executing_session_disambiguates_by_title_in_a_burst():
    # Pre-field-era only. On CURRENT data this branch is unreachable, because
    # titleSource=="auto" and scheduledTaskId are mutually exclusive on the
    # real stores -- any record a modern scheduled run produces takes the
    # primary path long before this code is reached.
    task = {"id": "ora-weekly-hygiene", "lastRunAt": "2026-09-11T16:01:02.000Z"}
    t_ms = 1789142462000
    records = [
        {"createdAt": t_ms + 50, "title": "Ora deal sourcing scan", "titleSource": "auto"},
        {"createdAt": t_ms - 50, "title": "Ora weekly hygiene", "titleSource": "auto",
         "cliSessionId": "aaaa"},
    ]
    found = gti.find_executing_session(task, records)
    check("fallback: title match resolves an otherwise-ambiguous burst window",
          found is not None and found["cliSessionId"] == "aaaa")


def test_fallback_find_executing_session_ignores_notify_session_id():
    # A task's notifySessionId points at a record with a matching cliSessionId
    # but a createdAt from months earlier -- must NOT be selected.
    task = {"id": "ora-am-brief", "lastRunAt": "2026-09-10T06:00:00.000Z",
            "notifySessionId": "local_STALE"}
    records = [
        {"createdAt": 1783537999843, "title": "ORA EOD action ledger coverage gaps",
         "titleSource": "auto", "sessionId": "local_STALE", "cliSessionId": "stale-cli-id"},
    ]
    found = gti.find_executing_session(task, records)
    check("fallback: a notifySessionId record with the wrong createdAt is "
          "never selected", found is None)


def test_fallback_excludes_falsy_but_present_scheduled_task_id():
    # Fix 2 (2026-09-11): exclusion from the fallback pool is by KEY PRESENCE,
    # not truthiness. A record with scheduledTaskId "" or None has still
    # declared an owner and must be excluded even though the value is falsy --
    # the old `if rec.get("scheduledTaskId")` check would have wrongly
    # admitted these into the fallback pool.
    task = {"id": "ora-weekly-hygiene", "lastRunAt": "2026-09-11T16:01:02.000Z"}
    t_ms = 1789142462000
    records = [
        {"createdAt": t_ms, "title": "Ora weekly hygiene", "titleSource": "auto",
         "scheduledTaskId": "", "cliSessionId": "empty-string-owner"},
        {"createdAt": t_ms, "title": "Ora weekly hygiene", "titleSource": "auto",
         "scheduledTaskId": None, "cliSessionId": "none-owner"},
    ]
    found = gti.find_executing_session(task, records)
    check("records carrying scheduledTaskId (even falsy '' or None) are "
          "excluded from the fallback pool, leaving nothing to join",
          found is None, found)


def test_find_all_sessions_for_task_returns_the_single_normal_case():
    t_ms = 1789060390632
    task = {"id": "ora-cowork-heartbeat", "lastRunAt": "2026-09-10T17:13:10.632Z"}
    records = [
        _real_shaped_session("ora-cowork-heartbeat", t_ms, "Ora cowork heartbeat"),
        # same task, YESTERDAY's firing -- outside the 300s window
        _real_shaped_session("ora-cowork-heartbeat", t_ms - 88_330_262,
                             "Ora cowork heartbeat", cli_session_id="yesterday"),
    ]
    found = gti.find_all_sessions_for_task(task, records)
    check("a clean single firing yields a list of exactly 1", len(found) == 1, found)


def test_find_all_sessions_for_task_surfaces_a_genuine_duplicate_fire():
    # THE duplicate-detection evidence case: two session records both stamped
    # with the same scheduledTaskId, created seconds apart, both attempting
    # the same firing. The registry cannot express this -- it keeps one row
    # per task and overwrites lastRunAt -- so this is the only real signal.
    t_ms = 1789060390632
    task = {"id": "ora-cowork-heartbeat", "lastRunAt": "2026-09-10T17:13:10.632Z"}
    records = [
        _real_shaped_session("ora-cowork-heartbeat", t_ms, "Ora cowork heartbeat",
                             cli_session_id="fire-a"),
        _real_shaped_session("ora-cowork-heartbeat", t_ms + 4_000, "Ora cowork heartbeat",
                             cli_session_id="fire-b"),
    ]
    found = gti.find_all_sessions_for_task(task, records)
    check("two sessions claiming the same task near the same firing BOTH "
          "return -- direct duplicate-execution evidence", len(found) == 2, found)


def test_find_all_sessions_for_task_excludes_other_tasks():
    t_ms = 1789060390632
    task = {"id": "ora-cowork-heartbeat", "lastRunAt": "2026-09-10T17:13:10.632Z"}
    records = [
        _real_shaped_session("ora-cowork-heartbeat", t_ms, "Ora cowork heartbeat"),
        # a DIFFERENT task firing at the very same instant
        _real_shaped_session("automation-health-monitor", t_ms,
                             "Automation health monitor", cli_session_id="other"),
    ]
    found = gti.find_all_sessions_for_task(task, records)
    check("a session with a different scheduledTaskId is excluded even at the "
          "same instant", len(found) == 1 and found[0]["scheduledTaskId"] == "ora-cowork-heartbeat",
          found)


def test_find_all_sessions_for_task_excludes_matches_outside_the_window():
    # scheduledTaskId matches, but createdAt is 301s out -- that is a
    # DIFFERENT firing of the same task, not a duplicate of this one.
    t_ms = 1789060390632
    task = {"id": "ora-cowork-heartbeat", "lastRunAt": "2026-09-10T17:13:10.632Z"}
    records = [
        _real_shaped_session("ora-cowork-heartbeat", t_ms, "Ora cowork heartbeat"),
        _real_shaped_session("ora-cowork-heartbeat", t_ms + 301_000,
                             "Ora cowork heartbeat", cli_session_id="next-cycle"),
    ]
    found = gti.find_all_sessions_for_task(task, records, window_seconds=300)
    check("a scheduledTaskId match outside window_seconds is excluded",
          len(found) == 1 and found[0]["cliSessionId"] != "next-cycle", found)


def test_join_cc_transcript_across_multiple_project_dirs():
    tmp = tempfile.mkdtemp()
    try:
        dir_a = os.path.join(tmp, "projA")
        dir_b = os.path.join(tmp, "projB")
        os.makedirs(dir_a)
        os.makedirs(dir_b)
        cli_id = "c2673895-9f28-47c4-9bb1-61b07a1cc87f"
        open(os.path.join(dir_b, cli_id + ".jsonl"), "w").close()
        result = gti.join_cc_transcript({"cliSessionId": cli_id}, [dir_a, dir_b])
        check("finds the transcript even when it's in the SECOND dir searched, "
              "not the first (spec Sec 3.4: scoping to one dir loses the join)",
              result == os.path.join(dir_b, cli_id + ".jsonl"))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_join_cc_transcript_absent_degrades_to_none():
    result = gti.join_cc_transcript({"cliSessionId": "does-not-exist"}, ["/nonexistent"])
    check("missing CC transcript degrades to None, not an exception", result is None)


def test_join_lams_transcript_uses_session_id_with_prefix_intact():
    tmp = tempfile.mkdtemp()
    try:
        session_id = "local_00a0caa8-2a71-4ec2-94f4-b00e2c542b1b"  # already prefixed
        os.makedirs(os.path.join(tmp, session_id))
        open(os.path.join(tmp, session_id, "audit.jsonl"), "w").close()
        result = gti.join_lams_transcript({"sessionId": session_id}, tmp)
        check("LAMS join uses sessionId as-is (no re-added local_ prefix)",
              result == os.path.join(tmp, session_id, "audit.jsonl"))
        doubled = os.path.join(tmp, "local_" + session_id)
        check("doubling the prefix would NOT be the real path (regression guard)",
              not os.path.isdir(doubled))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_join_lams_transcript_absent_degrades_to_none():
    result = gti.join_lams_transcript({"sessionId": "local_missing"}, tempfile.gettempdir())
    check("missing LAMS transcript degrades to None, not an exception", result is None)


def test_detect_duplicates_same_cycle_refire():
    # Post-C2: the flag fires on REAL evidence -- more than one session record
    # claiming this task's firing (candidate_session_count from
    # find_all_sessions_for_task) -- not on multiple registry rows in one
    # build call, which the registry structurally cannot produce.
    runs = [
        {"fleet": "cc", "task_id": "ora-weekly-hygiene", "run_id": "cc:ora-weekly-hygiene:X",
         "last_scheduled_for": "X", "last_run_at": "2026-09-11T16:01:02.000Z",
         "candidate_session_count": 2},
    ]
    flags = gti.detect_duplicates(runs, [], [])
    hits = [f for f in flags if f["type"] == "same_cycle_refire"]
    check("two session records claiming one firing is flagged", len(hits) == 1, flags)
    check("the detail reports the real count found, not a row count",
          hits and "2 session records" in hits[0]["detail"]
          and "1 of these are likely duplicate" in hits[0]["detail"], flags)
    check("the flag keeps its shape (single run_id, from this run)",
          hits and hits[0]["run_ids"] == ["cc:ora-weekly-hygiene:X"], flags)


def test_detect_duplicates_no_same_cycle_refire_on_a_clean_single_firing():
    runs = [
        {"fleet": "cc", "task_id": "ora-weekly-hygiene", "run_id": "cc:ora-weekly-hygiene:X",
         "last_scheduled_for": "X", "last_run_at": "2026-09-11T16:01:02.000Z",
         "candidate_session_count": 1},
    ]
    flags = gti.detect_duplicates(runs, [], [])
    check("exactly one claiming session is NOT flagged",
          [f for f in flags if f["type"] == "same_cycle_refire"] == [], flags)


def test_detect_duplicates_same_cycle_refire_absent_count_is_safe():
    # An unjoined run (or a run-index document predating this field) carries
    # no candidate_session_count -- must not raise and must not flag.
    runs = [
        {"fleet": "cc", "task_id": "ora-weekly-hygiene", "run_id": "cc:ora-weekly-hygiene:X",
         "last_scheduled_for": "X", "last_run_at": "2026-09-11T16:01:02.000Z"},
    ]
    flags = gti.detect_duplicates(runs, [], [])
    check("a missing candidate_session_count is absent-safe and never flags",
          [f for f in flags if f["type"] == "same_cycle_refire"] == [], flags)


def test_detect_duplicates_cross_fleet_twin():
    runs = [
        {"fleet": "cc", "task_id": "ora-passed-deal-tracker",
         "run_id": "cc:ora-passed-deal-tracker:X", "last_scheduled_for": "X"},
        {"fleet": "lams", "task_id": "ora-passed-deal-tracker",
         "run_id": "lams:ora-passed-deal-tracker:Y", "last_scheduled_for": "Y"},
    ]
    flags = gti.detect_duplicates(runs, ["ora-passed-deal-tracker"], ["ora-passed-deal-tracker"])
    hits = [f for f in flags if f["type"] == "cross_fleet_twin"]
    check("same task id enabled on both fleets is flagged", len(hits) == 1, flags)


def test_detect_duplicates_cron_period_collision():
    runs = [
        {"fleet": "lams", "task_id": "automation-health-monitor",
         "run_id": "lams:automation-health-monitor:A", "last_scheduled_for": "2026-09-10T15:05:00.000Z",
         "cron_expression": "5 11 * * 1-5"},
        {"fleet": "lams", "task_id": "automation-health-monitor",
         "run_id": "lams:automation-health-monitor:B", "last_scheduled_for": "2026-09-10T15:06:00.000Z",
         "cron_expression": "5 11 * * 1-5"},
    ]
    flags = gti.detect_duplicates(runs, [], [])
    hits = [f for f in flags if f["type"] == "cron_period_collision"]
    # NOTE (final-review C2 fix, 2026-09-11): this is a SYNTHETIC multi-row
    # scenario the real single-invocation pipeline cannot produce today -- the
    # registry supplies exactly one last_scheduled_for per task per
    # build_run_index() call, so this flag is DORMANT in production and fires
    # only if Stage 0 is later extended to ingest multiple nights' run-index
    # documents. Kept deliberately, with the limitation documented in
    # detect_duplicates rather than left as a silent no-op.
    check("two schedules 1 minute apart on a daily cron are flagged", len(hits) == 1, flags)


def test_detect_duplicates_no_false_positive_on_normal_daily_runs():
    runs = [
        {"fleet": "lams", "task_id": "automation-health-monitor",
         "run_id": "lams:automation-health-monitor:day1", "last_scheduled_for": "2026-09-09T15:05:00.000Z",
         "cron_expression": "5 11 * * 1-5"},
        {"fleet": "lams", "task_id": "automation-health-monitor",
         "run_id": "lams:automation-health-monitor:day2", "last_scheduled_for": "2026-09-10T15:05:00.000Z",
         "cron_expression": "5 11 * * 1-5"},
    ]
    flags = gti.detect_duplicates(runs, [], [])
    check("two normal consecutive daily fires are NOT flagged", flags == [], flags)


def test_detect_duplicates_refire_is_not_also_a_cron_collision():
    # A duplicate firing (now evidenced by candidate_session_count > 1 on the
    # single registry row the fleet actually produces) must not ALSO be
    # double-reported as a cron_period_collision -- that flag requires two
    # DISTINCT lastScheduledFor values per its own docstring, which one
    # build_run_index() call can never supply.
    runs = [
        {"fleet": "lams", "task_id": "automation-health-monitor",
         "run_id": "lams:automation-health-monitor:same",
         "last_scheduled_for": "2026-09-10T15:05:00.000Z",
         "last_run_at": "2026-09-10T17:13:10.632Z",
         "cron_expression": "5 11 * * 1-5", "candidate_session_count": 2},
    ]
    flags = gti.detect_duplicates(runs, [], [])
    types = [f["type"] for f in flags]
    check("a duplicate firing IS flagged as same_cycle_refire",
          types.count("same_cycle_refire") == 1, flags)
    check("a duplicate firing is NOT also flagged as cron_period_collision",
          types.count("cron_period_collision") == 0, flags)


def test_join_rate_floor_normal_window_high_rate_passes():
    ok, msg = gti.assert_join_rate_floor(95, 100, window_hours=24.0)
    check("95/100 on a normal 24h window passes the 90% floor", ok, msg)


def test_join_rate_floor_normal_window_low_rate_fails():
    ok, msg = gti.assert_join_rate_floor(50, 100, window_hours=24.0)
    check("50/100 on a normal 24h window FAILS the 90% floor "
          "(this is what R1a exists to catch)", not ok, msg)


def test_join_rate_floor_widened_window_same_low_rate_passes():
    # The exact scenario R1a exists to distinguish: the SAME ~50% rate is
    # expected, not alarming, on a widened window.
    ok, msg = gti.assert_join_rate_floor(50, 100, window_hours=100.0)
    check("50/100 on a widened (>72h) window passes the 30% floor -- "
          "the widener must not false-alarm nightly", ok, msg)


def test_join_rate_floor_empty_window_is_trivially_ok():
    ok, msg = gti.assert_join_rate_floor(0, 0, window_hours=24.0)
    check("an empty window never fails the floor", ok, msg)


def _write_registry(path, tasks, recorded_skips=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    json.dump({"scheduledTasks": tasks, "recordedSkips": recorded_skips or {}},
              open(path, "w", encoding="utf-8"))


def _write_session_record(registry_dir, session_id, created_at_ms, title,
                           cli_session_id=None, scheduled_task_id=None):
    """Writes a session record shaped like the REAL thing: a scheduled run
    carries `scheduledTaskId` (the task id verbatim) and `titleSource` None.
    Passing scheduled_task_id=None deliberately produces a pre-field-era
    record for exercising the fallback join."""
    rec = {"sessionId": session_id, "createdAt": created_at_ms,
           "title": title, "titleSource": None}
    if scheduled_task_id:
        rec["scheduledTaskId"] = scheduled_task_id
    if cli_session_id:
        rec["cliSessionId"] = cli_session_id
    json.dump(rec, open(os.path.join(registry_dir, session_id + ".json"), "w", encoding="utf-8"))


def test_build_run_index_excludes_its_own_run():
    tmp = tempfile.mkdtemp()
    try:
        cc_reg = os.path.join(tmp, "cc", "scheduled-tasks.json")
        lams_reg = os.path.join(tmp, "lams", "scheduled-tasks.json")
        now = datetime(2026, 9, 11, 20, 5, tzinfo=timezone.utc)
        _write_registry(cc_reg, [
            {"id": "ora-ground-truth-auditor", "cronExpression": "0 4 * * *",
             "enabled": True, "lastRunAt": now.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
             "lastScheduledFor": now.strftime("%Y-%m-%dT%H:%M:%S.000Z")},
        ])
        _write_registry(lams_reg, [])
        index = gti.build_run_index(cc_reg, lams_reg, [], now=now)
        check("the auditor's own run never appears in its own index",
              all(r["task_id"] != "ora-ground-truth-auditor" for r in index["runs"]),
              index["runs"])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_build_run_index_end_to_end_joins_a_real_shaped_run():
    tmp = tempfile.mkdtemp()
    try:
        cc_dir = os.path.join(tmp, "cc")
        cc_reg = os.path.join(cc_dir, "scheduled-tasks.json")
        now = datetime(2026, 9, 10, 20, 0, tzinfo=timezone.utc)
        last_run = "2026-09-10T16:56:58.667Z"
        _write_registry(cc_reg, [
            {"id": "ora-doctrine-integrity-guard", "cronExpression": "5 7 * * *",
             "enabled": True, "lastRunAt": last_run, "lastScheduledFor": last_run,
             "model": "claude-opus-5", "filePath": "/some/path/SKILL.md"},
        ])
        t_ms = int(datetime.fromisoformat(last_run.replace("Z", "+00:00")).timestamp() * 1000)
        _write_session_record(cc_dir, "local_aa8cdc0f", t_ms,
                               "Ora doctrine integrity guard", cli_session_id="abc123",
                               scheduled_task_id="ora-doctrine-integrity-guard")
        # inject a model onto the session record after the fact (helper doesn't take one)
        session_path = os.path.join(cc_dir, "local_aa8cdc0f.json")
        rec = json.load(open(session_path, encoding="utf-8"))
        rec["model"] = "claude-sonnet-5"
        json.dump(rec, open(session_path, "w", encoding="utf-8"))
        proj_dir = os.path.join(tmp, "proj")
        os.makedirs(proj_dir)
        open(os.path.join(proj_dir, "abc123.jsonl"), "w").close()

        lams_reg = os.path.join(tmp, "lams", "scheduled-tasks.json")
        _write_registry(lams_reg, [])

        index = gti.build_run_index(cc_reg, lams_reg, [proj_dir], now=now)
        check("exactly one run indexed", len(index["runs"]) == 1, index["runs"])
        run = index["runs"][0]
        check("run is joined to its transcript", run["joined"] is True, run)
        check("run_id keys on lastScheduledFor", run["run_id"].endswith(last_run), run)
        check("CC join-rate floor passes at 1/1", index["join_stats"]["cc"]["rate_ok"] is True,
              index["join_stats"])
        check("a clean single firing carries candidate_session_count == 1",
              run.get("candidate_session_count") == 1, run)
        check("a clean single firing raises no duplicate flag",
              index["duplicate_flags"] == [], index["duplicate_flags"])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_build_run_index_end_to_end_flags_a_genuine_duplicate_fire():
    # The whole C2 fix, end to end: ONE registry row (all the fleet can ever
    # produce for a task) plus TWO session records both stamped with that
    # task's scheduledTaskId near the same firing -> same_cycle_refire.
    tmp = tempfile.mkdtemp()
    try:
        cc_dir = os.path.join(tmp, "cc")
        cc_reg = os.path.join(cc_dir, "scheduled-tasks.json")
        now = datetime(2026, 9, 10, 20, 0, tzinfo=timezone.utc)
        last_run = "2026-09-10T16:56:58.667Z"
        _write_registry(cc_reg, [
            {"id": "ora-doctrine-integrity-guard", "cronExpression": "5 7 * * *",
             "enabled": True, "lastRunAt": last_run, "lastScheduledFor": last_run,
             "model": "claude-opus-5", "filePath": "/some/path/SKILL.md"},
        ])
        t_ms = int(datetime.fromisoformat(last_run.replace("Z", "+00:00")).timestamp() * 1000)
        _write_session_record(cc_dir, "local_fire_a", t_ms,
                               "Ora doctrine integrity guard", cli_session_id="cli-a",
                               scheduled_task_id="ora-doctrine-integrity-guard")
        _write_session_record(cc_dir, "local_fire_b", t_ms + 4000,
                               "Ora doctrine integrity guard", cli_session_id="cli-b",
                               scheduled_task_id="ora-doctrine-integrity-guard")
        proj_dir = os.path.join(tmp, "proj")
        os.makedirs(proj_dir)
        open(os.path.join(proj_dir, "cli-a.jsonl"), "w").close()
        open(os.path.join(proj_dir, "cli-b.jsonl"), "w").close()

        lams_reg = os.path.join(tmp, "lams", "scheduled-tasks.json")
        _write_registry(lams_reg, [])

        index = gti.build_run_index(cc_reg, lams_reg, [proj_dir], now=now)
        check("the registry still yields exactly ONE row/run for the task -- "
              "which is why row counting could never have detected this",
              len(index["runs"]) == 1, index["runs"])
        run = index["runs"][0]
        check("candidate_session_count carries the real evidence count (2)",
              run.get("candidate_session_count") == 2, run)
        hits = [f for f in index["duplicate_flags"] if f["type"] == "same_cycle_refire"]
        check("a genuine duplicate fire IS flagged end to end", len(hits) == 1,
              index["duplicate_flags"])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_build_run_index_persists_file_path_and_session_model_for_verifier_dispatch():
    # Task 8's SKILL.md STEP 3 dispatches gmr.resolve_verifier_model(task_record,
    # skill_md_text, session_record) for every side-effecting run -- the live
    # agent needs the task's own SKILL.md path (rung 2) and the joined
    # session's own model field (rung 3) to build those inputs itself. Prove
    # both survive onto the run record for a joined run, and are None/absent
    # -safe (never raise) for an unjoined one.
    tmp = tempfile.mkdtemp()
    try:
        cc_dir = os.path.join(tmp, "cc")
        cc_reg = os.path.join(cc_dir, "scheduled-tasks.json")
        now = datetime(2026, 9, 10, 20, 0, tzinfo=timezone.utc)
        last_run = "2026-09-10T16:56:58.667Z"
        _write_registry(cc_reg, [
            {"id": "ora-doctrine-integrity-guard", "cronExpression": "5 7 * * *",
             "enabled": True, "lastRunAt": last_run, "lastScheduledFor": last_run,
             "model": "claude-opus-5", "filePath": "/some/path/SKILL.md"},
            {"id": "ora-unjoined-task", "cronExpression": "0 5 * * *",
             "enabled": True, "lastRunAt": "2026-09-10T05:00:00.000Z",
             "lastScheduledFor": "2026-09-10T05:00:00.000Z",
             "model": "claude-opus-5", "filePath": "/some/other/SKILL.md"},
        ])
        t_ms = int(datetime.fromisoformat(last_run.replace("Z", "+00:00")).timestamp() * 1000)
        _write_session_record(cc_dir, "local_aa8cdc0f", t_ms,
                               "Ora doctrine integrity guard", cli_session_id="abc123",
                               scheduled_task_id="ora-doctrine-integrity-guard")
        session_path = os.path.join(cc_dir, "local_aa8cdc0f.json")
        rec = json.load(open(session_path, encoding="utf-8"))
        rec["model"] = "claude-sonnet-5"
        json.dump(rec, open(session_path, "w", encoding="utf-8"))
        proj_dir = os.path.join(tmp, "proj")
        os.makedirs(proj_dir)
        open(os.path.join(proj_dir, "abc123.jsonl"), "w").close()

        lams_reg = os.path.join(tmp, "lams", "scheduled-tasks.json")
        _write_registry(lams_reg, [])

        index = gti.build_run_index(cc_reg, lams_reg, [proj_dir], now=now)
        by_task = {r["task_id"]: r for r in index["runs"]}

        joined_run = by_task["ora-doctrine-integrity-guard"]
        check("joined run persists its own registry file_path",
              joined_run["file_path"] == "/some/path/SKILL.md", joined_run)
        check("joined run persists the joined session's own model as session_model",
              joined_run["session_model"] == "claude-sonnet-5", joined_run)

        unjoined_run = by_task["ora-unjoined-task"]
        check("unjoined run still carries its own registry file_path",
              unjoined_run["file_path"] == "/some/other/SKILL.md", unjoined_run)
        check("unjoined run's session_model is None (absent-safe, never raises)",
              unjoined_run["session_model"] is None, unjoined_run)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_build_run_index_last_auditor_run_at_is_injectable():
    # Testability fix: a test must be able to control the "previous auditor
    # run" timestamp without depending on (or polluting) the real
    # maintenance/_state/ground-truth/last-auditor-run.json file. Injecting a
    # very old timestamp should widen the window past the 24h default,
    # exactly as decide_window_hours would if that value came from the real
    # file -- proving the parameter actually reaches decide_window_hours.
    tmp = tempfile.mkdtemp()
    try:
        cc_reg = os.path.join(tmp, "cc", "scheduled-tasks.json")
        lams_reg = os.path.join(tmp, "lams", "scheduled-tasks.json")
        _write_registry(cc_reg, [])
        _write_registry(lams_reg, [])
        now = datetime(2026, 9, 11, 4, 0, tzinfo=timezone.utc)
        injected_last_run = now - timedelta(hours=72)  # far older than 24h
        index = gti.build_run_index(cc_reg, lams_reg, [], now=now,
                                     last_auditor_run_at=injected_last_run)
        check("an injected old last_auditor_run_at widens the window past the default "
              "-- proves the parameter is actually used, not ignored",
              index["window_hours"] >= 72.0, index["window_hours"])
        check("the window_reason names the gap, sourced from the injected value",
              "prior auditor run" in index["window_reason"], index["window_reason"])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_build_run_index_default_last_auditor_run_at_falls_back_to_real_file_reader():
    # When NOT injected (the real main() call pattern), behavior must be
    # unchanged: None triggers the existing _read_last_auditor_run() path.
    # This test does not assert on the real file's actual content (that
    # would reintroduce the hazard) -- it only asserts that omitting the
    # parameter does not raise and produces a valid window_hours >= 24.0
    # (the floor for any outcome of decide_window_hours).
    tmp = tempfile.mkdtemp()
    try:
        cc_reg = os.path.join(tmp, "cc", "scheduled-tasks.json")
        lams_reg = os.path.join(tmp, "lams", "scheduled-tasks.json")
        _write_registry(cc_reg, [])
        _write_registry(lams_reg, [])
        now = datetime(2026, 9, 11, 4, 0, tzinfo=timezone.utc)
        index = gti.build_run_index(cc_reg, lams_reg, [], now=now)  # no injection
        check("omitting last_auditor_run_at does not raise and yields a sane window",
              index["window_hours"] >= 24.0, index["window_hours"])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    test_build_run_id_keys_on_last_scheduled_for()
    test_window_default_when_nothing_widens()
    test_window_widens_when_auditor_gap_exceeds_default()
    test_window_widens_on_fleet_resume_event()
    test_recurring_task_named_resume_does_not_widen()
    test_never_ran_does_not_widen_without_a_resume_event()
    test_find_executing_session_primary_key_is_scheduled_task_id()
    test_find_executing_session_single_claimant_needs_no_title_check()
    test_find_executing_session_single_claimant_beyond_bound_is_unjoined()
    test_find_executing_session_tiebreak_winner_beyond_bound_is_unjoined()
    test_find_executing_session_tiebreaks_claimants_by_nearest_created_at()
    test_find_executing_session_never_claims_another_tasks_session()
    test_fallback_find_executing_session_matches_by_createdat_and_title()
    test_fallback_find_executing_session_ambiguous_window_is_unjoined()
    test_fallback_find_executing_session_disambiguates_by_title_in_a_burst()
    test_fallback_find_executing_session_ignores_notify_session_id()
    test_fallback_excludes_falsy_but_present_scheduled_task_id()
    test_find_all_sessions_for_task_returns_the_single_normal_case()
    test_find_all_sessions_for_task_surfaces_a_genuine_duplicate_fire()
    test_find_all_sessions_for_task_excludes_other_tasks()
    test_find_all_sessions_for_task_excludes_matches_outside_the_window()
    test_join_cc_transcript_across_multiple_project_dirs()
    test_join_cc_transcript_absent_degrades_to_none()
    test_join_lams_transcript_uses_session_id_with_prefix_intact()
    test_join_lams_transcript_absent_degrades_to_none()
    test_detect_duplicates_same_cycle_refire()
    test_detect_duplicates_no_same_cycle_refire_on_a_clean_single_firing()
    test_detect_duplicates_same_cycle_refire_absent_count_is_safe()
    test_detect_duplicates_cross_fleet_twin()
    test_detect_duplicates_cron_period_collision()
    test_detect_duplicates_no_false_positive_on_normal_daily_runs()
    test_detect_duplicates_refire_is_not_also_a_cron_collision()
    test_join_rate_floor_normal_window_high_rate_passes()
    test_join_rate_floor_normal_window_low_rate_fails()
    test_join_rate_floor_widened_window_same_low_rate_passes()
    test_join_rate_floor_empty_window_is_trivially_ok()
    test_build_run_index_excludes_its_own_run()
    test_build_run_index_end_to_end_joins_a_real_shaped_run()
    test_build_run_index_end_to_end_flags_a_genuine_duplicate_fire()
    test_build_run_index_persists_file_path_and_session_model_for_verifier_dispatch()
    test_build_run_index_last_auditor_run_at_is_injectable()
    test_build_run_index_default_last_auditor_run_at_falls_back_to_real_file_reader()
    print("-" * 72)
    if FAILURES:
        print("FAIL: %d failure(s): %s" % (len(FAILURES), ", ".join(FAILURES)))
        sys.exit(1)
    print("ALL PASS")
    sys.exit(0)
