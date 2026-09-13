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
        msg = "%s %s" % (label, detail)
        print("  [FAIL] %s" % msg)
        FAILURES.append(label)
        # OI-296 review round 2, req 4: under pytest, a failed check() must
        # actually fail the test -- previously it only appended to FAILURES,
        # which pytest never inspects, so every test_* function "passed"
        # regardless of what check() found (pytest run: 54/54, 71/71 "green"
        # even with real assertion failures inside). The direct-run harness
        # (`python test-ground-truth-run-index.py`, __main__ below) is
        # unaffected -- it already reads FAILURES itself and is what the
        # repo's pre-push tests gate actually runs.
        if os.environ.get("PYTEST_CURRENT_TEST"):
            raise AssertionError(msg)


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
    hours, reason, widen_kind = gti.decide_window_hours(now, last_run, [], [])
    check("default window when auditor is current and no resume in range",
          hours == 24.0, "hours=%s reason=%s" % (hours, reason))
    check("widen_kind is 'none' when nothing widens", widen_kind == "none", widen_kind)


def test_window_widens_when_auditor_gap_exceeds_default():
    # Fixture: catch-up burst -- the auditor itself was paused/host-closed for
    # 3 days, so its own last run is 72h old.
    now = datetime(2026, 9, 11, 4, 0, tzinfo=timezone.utc)
    last_run = now - timedelta(hours=72)
    hours, reason, widen_kind = gti.decide_window_hours(now, last_run, [], [])
    check("window widens to cover the auditor's own gap",
          hours >= 72.0, "hours=%s reason=%s" % (hours, reason))
    check("reason names the gap", "prior auditor run" in reason, reason)
    check("widen_kind is 'auditor_gap' for a pure auditor-gap widen",
          widen_kind == "auditor_gap", widen_kind)


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
    hours, reason, widen_kind = gti.decide_window_hours(now, now - timedelta(hours=1),
                                                         [resume_task], [])
    check("window widens on a fleet-resume event even when the auditor itself "
          "is current", hours > 24.0, "hours=%s reason=%s" % (hours, reason))
    check("reason names the resume task", "fleet-resume event" in reason, reason)
    check("widen_kind is 'resume_event' for a pure resume widen (no auditor gap)",
          widen_kind == "resume_event", widen_kind)


def test_window_widens_on_both_auditor_gap_and_resume_event():
    # I6: when BOTH conditions hold, widen_kind must be "both" -- the
    # auditor-gap justification still applies, so the loose floor tier
    # should still be used (see assert_join_rate_floor).
    now = datetime(2026, 9, 11, 16, 5, tzinfo=timezone.utc)
    last_run = now - timedelta(hours=72)
    resume_task = {
        "id": "ora-routine-pause-resume-2026-09-11",
        "enabled": True,
        "lastRunAt": "2026-09-11T16:01:00.000Z",
    }
    hours, reason, widen_kind = gti.decide_window_hours(now, last_run, [resume_task], [])
    check("widen_kind is 'both' when both an auditor gap and a resume event hold",
          widen_kind == "both", widen_kind)


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
    hours, reason, widen_kind = gti.decide_window_hours(now, now - timedelta(hours=1), [recurring], [])
    check("a RECURRING task named *resume* does not trigger the resume widen",
          hours == 24.0, "hours=%s reason=%s" % (hours, reason))
    check("widen_kind is 'none' (recurring resume-named task doesn't count)",
          widen_kind == "none", widen_kind)


def test_never_ran_does_not_widen_without_a_resume_event():
    # Confirmed with Gabriel 2026-09-11: a literal never-ran (no prior
    # auditor run at all) does NOT by itself widen the window -- there is
    # no measurable gap, and the realistic backfill case (mid-pause
    # registration) is covered separately by the resume-event widen path.
    now = datetime(2026, 9, 10, 4, 0, tzinfo=timezone.utc)
    hours, reason, widen_kind = gti.decide_window_hours(now, None, [], [])
    check("never-ran with no resume event stays at the default window",
          hours == 24.0, "hours=%s reason=%s" % (hours, reason))
    check("the reason still names the never-ran condition for visibility",
          "no prior auditor run" in reason, reason)
    check("widen_kind is 'none' -- a never-ran with no resume didn't actually widen",
          widen_kind == "none", widen_kind)


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
# find_executing_session -- FALLBACK path (records with no scheduledTaskId)
#
# The four tests below deliberately use records with NO `scheduledTaskId` key.
# That omission is INTENTIONAL and load-bearing, not another accidental gap:
# it is what makes these records represent records that never carry
# scheduledTaskId at all (interactive sessions) -- the createdAt/title
# fallback exists to serve these, not a temporal era. Any record here that
# grew a scheduledTaskId would silently stop testing the fallback.
# ---------------------------------------------------------------------------

def test_fallback_find_executing_session_matches_by_createdat_and_title():
    # FALLBACK path: no record carries scheduledTaskId, so the createdAt/title
    # heuristic is the only key available -- correct for records that never
    # carry scheduledTaskId (interactive sessions).
    task = {"id": "automation-health-monitor", "lastRunAt": "2026-09-10T17:13:10.632Z"}
    records = [
        # decoy: a notifySessionId-style stale record, months earlier
        {"createdAt": 1783537999843, "title": "Some old chat", "titleSource": "auto"},
        {"createdAt": 1789060390632, "title": "Automation health monitor", "titleSource": "auto",
         "sessionId": "local_e59d1b67-bf90-4e6b-9883-3e8a52dec80c",
         "cliSessionId": "696009a7-1727-470b-917d-51df0ec81803"},
    ]
    check("these never carry scheduledTaskId by design (interactive-session "
          "shape), so the fallback is what gets exercised",
          all("scheduledTaskId" not in r for r in records))
    found = gti.find_executing_session(task, records)
    check("fallback finds the session created at the same ms as lastRunAt",
          found is not None and found["cliSessionId"] == "696009a7-1727-470b-917d-51df0ec81803")


def test_fallback_find_executing_session_ambiguous_window_is_unjoined():
    # Catch-up burst: two sessions with no scheduledTaskId, created inside
    # the same 2s tolerance window, neither titled for this task.
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
    # Records with no scheduledTaskId only. On CURRENT data this branch is
    # unreachable, because titleSource=="auto" and scheduledTaskId are
    # mutually exclusive on the real stores -- any record a modern scheduled
    # run produces takes the primary path long before this code is reached.
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
    # A record carrying scheduledTaskId as an EMPTY STRING or None still declared
    # an owner (even if that value happens to be falsy) -- it must be excluded
    # from the fallback pool by PRESENCE, not by truthiness. A single record is
    # used deliberately: with the old truthiness check this record would be the
    # SOLE fallback candidate and would be wrongly returned; with the correct
    # presence check it is excluded and the result is None.
    task = {"id": "ora-weekly-hygiene", "lastRunAt": "2026-09-11T16:01:02.000Z"}
    t_ms = 1789142462000

    empty_string_case = [
        {"createdAt": t_ms, "title": "Ora weekly hygiene", "titleSource": "auto",
         "scheduledTaskId": "", "cliSessionId": "should-not-be-returned"},
    ]
    found = gti.find_executing_session(task, empty_string_case)
    check("a record with scheduledTaskId='' (falsy but present) is excluded from "
          "the fallback pool -- returns None, not the sole 'candidate'",
          found is None, found)

    none_value_case = [
        {"createdAt": t_ms, "title": "Ora weekly hygiene", "titleSource": "auto",
         "scheduledTaskId": None, "cliSessionId": "should-not-be-returned"},
    ]
    found2 = gti.find_executing_session(task, none_value_case)
    check("a record with scheduledTaskId=None (falsy but present) is excluded from "
          "the fallback pool -- returns None, not the sole 'candidate'",
          found2 is None, found2)


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


def test_join_rate_floor_resume_only_widen_uses_strict_floor():
    # I6, the whole point of the fix: task selection in build_run_index keys
    # on lastRunAt, so a resume catch-up burst's own runs are ALREADY fully
    # captured by the plain default-hours window -- the 3x widen adds no
    # coverage benefit for that burst. The floor must therefore stay STRICT
    # (90%) when the widen reason is purely resume_event (no auditor gap),
    # even though window_hours itself is wide.
    ok, msg = gti.assert_join_rate_floor(50, 100, window_hours=100.0, widen_kind="resume_event")
    check("a resume-only widen with a mediocre (50/100) join rate FAILS the "
          "strict 90% floor, despite a wide window", not ok, msg)


def test_join_rate_floor_auditor_gap_widen_still_uses_loose_floor():
    # Same mediocre rate as above, but this time the widen reason IS a
    # genuine auditor-gap catch-up -- the loose floor still applies,
    # unchanged from pre-I6 behavior (this is assert_join_rate_floor's
    # default widen_kind too).
    ok, msg = gti.assert_join_rate_floor(50, 100, window_hours=100.0, widen_kind="auditor_gap")
    check("the SAME 50/100 rate under an auditor-gap widen still passes the "
          "loose 30% floor (unchanged behavior)", ok, msg)


def test_join_rate_floor_default_widen_kind_matches_auditor_gap_behavior():
    # Backward compatibility: callers that don't pass widen_kind at all (the
    # pre-I6 call shape) must see identical behavior to explicit
    # widen_kind="auditor_gap".
    ok_default, _ = gti.assert_join_rate_floor(50, 100, window_hours=100.0)
    ok_explicit, _ = gti.assert_join_rate_floor(50, 100, window_hours=100.0, widen_kind="auditor_gap")
    check("omitting widen_kind behaves identically to widen_kind='auditor_gap'",
          ok_default == ok_explicit == True)


def _write_registry(path, tasks, recorded_skips=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    json.dump({"scheduledTasks": tasks, "recordedSkips": recorded_skips or {}},
              open(path, "w", encoding="utf-8"))


def _write_session_record(registry_dir, session_id, created_at_ms, title,
                           cli_session_id=None, scheduled_task_id=None):
    """Writes a session record shaped like the REAL thing: a scheduled run
    carries `scheduledTaskId` (the task id verbatim) and `titleSource` None.
    Passing scheduled_task_id=None deliberately produces a record with no
    scheduledTaskId (interactive-session shape), for exercising the fallback
    path."""
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
        # dedup disabled -- isolates this baseline test from real machine
        # state (an un-injected ground_truth_state_dir/send_log_path would
        # otherwise resolve to the REAL production paths).
        index = gti.build_run_index(cc_reg, lams_reg, [], now=now,
                                     dedup_previously_audited=False)
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

        index = gti.build_run_index(cc_reg, lams_reg, [proj_dir], now=now,
                                     dedup_previously_audited=False)
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

        index = gti.build_run_index(cc_reg, lams_reg, [proj_dir], now=now,
                                     dedup_previously_audited=False)
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

        index = gti.build_run_index(cc_reg, lams_reg, [proj_dir], now=now,
                                     dedup_previously_audited=False)
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
                                     last_auditor_run_at=injected_last_run,
                                     dedup_previously_audited=False)
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
        index = gti.build_run_index(cc_reg, lams_reg, [], now=now,
                                     dedup_previously_audited=False)  # no injection
        check("omitting last_auditor_run_at does not raise and yields a sane window",
              index["window_hours"] >= 24.0, index["window_hours"])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# OI-296 -- skip runs already audited and ACTUALLY PUBLISHED (sent) by a
# prior night's digest. Round 1 measured 2026-09-13: Stage 0 re-selected 5 of
# 12 in-window runs a 2026-09-12 20:34Z audit had already verified. Round-1's
# fix used "a sibling digest-<date>.html exists" as the published signal and
# excluded any run-index filename-dated today or later. Independent review
# (round 2) found both wrong: an HTML file can be rendered and never actually
# emailed (retry/SMTP failure/killed process), and filename-date exclusion
# both silently drops a legitimately-published same-day rerun and can pair a
# send with the wrong document. The real signal is send-via-outlook.ps1's own
# append-only send log (a line lands ONLY on a confirmed send), and ordering
# uses each document's own `generated_at`, never its filename -- see
# load_ground_truth_digest_sends/load_previously_audited's docstrings.
# ---------------------------------------------------------------------------

def _write_prior_run_index(state_dir, filename_date_str, runs, generated_at):
    """Writes a prior run-index-<filename_date_str>.json. `generated_at` is
    set INDEPENDENTLY of the filename on purpose -- OI-296 review round 2:
    published-ness and ordering are decided by the document's own
    generated_at field, never by its filename, and several tests below rely
    on being able to prove that by deliberately mismatching the two."""
    os.makedirs(state_dir, exist_ok=True)
    path = os.path.join(state_dir, "run-index-{}.json".format(filename_date_str))
    json.dump({"generated_at": generated_at, "runs": runs}, open(path, "w", encoding="utf-8"))
    return path


def _write_send_log(send_log_path, lines):
    """Writes a synthetic send-log.txt from pre-formatted lines (use
    _gt_send_line to build realistic ones)."""
    os.makedirs(os.path.dirname(send_log_path), exist_ok=True)
    open(send_log_path, "w", encoding="utf-8").write("\n".join(lines) + ("\n" if lines else ""))
    return send_log_path


def _gt_send_line(iso_ts, date_label, subject_sep="--", ok=True):
    """One realistic send-log line for a Ground-Truth Audit digest send --
    real shape verified against the live log 2026-09-13:
    '2026-09-13T09:21:33-04:00 [OK] Sent to=ggoldberg@oxfordra.net cc=none
    subject="[ORA] Ground-Truth Audit -- 2026-09-13" bytes=14030 format=html'
    """
    subject = "[ORA] Ground-Truth Audit {} {}".format(subject_sep, date_label)
    status = "[OK] Sent" if ok else "[FAIL] Send"
    return '{} {} to=ggoldberg@oxfordra.net cc=none subject="{}" bytes=14030 format=html'.format(
        iso_ts, status, subject)


def _prior_run_record(run_id, task_id, fleet, candidate_session_count=1,
                       transcript_size=0, transcript_mtime=0.0, include_transcript_size=True):
    """One run entry as it would appear inside a prior published run-index
    document. `include_transcript_size=False` simulates an OLDER index file
    that predates the transcript_size/transcript_mtime fields (req 7
    back-compat)."""
    rec = {"run_id": run_id, "task_id": task_id, "fleet": fleet,
           "candidate_session_count": candidate_session_count}
    if include_transcript_size:
        rec["transcript_size"] = transcript_size
        rec["transcript_mtime"] = transcript_mtime
    return rec


# --- load_ground_truth_digest_sends -----------------------------------------

def test_load_ground_truth_digest_sends_parses_ok_matching_lines_and_ignores_others():
    tmp = tempfile.mkdtemp()
    try:
        send_log = os.path.join(tmp, "send-log.txt")
        _write_send_log(send_log, [
            _gt_send_line("2026-09-13T09:21:33-04:00", "2026-09-13"),
            # wrong subject -- must be ignored
            '2026-09-13T09:00:00-04:00 [OK] Sent to=ggoldberg@oxfordra.net cc=none '
            'subject="[ORA] Daily Brief -- 2026-09-13" bytes=500 format=html',
            # right subject, but a FAILED send -- must be ignored
            _gt_send_line("2026-09-13T08:00:00-04:00", "2026-09-13", ok=False),
        ])
        sends, warning = gti.load_ground_truth_digest_sends(send_log)
        check("no warning on a readable send log", warning is None, warning)
        check("exactly one real ground-truth OK send is parsed", len(sends) == 1, sends)
        check("the parsed send is converted to aware UTC",
              sends and sends[0].tzinfo is not None and sends[0].utcoffset().total_seconds() == 0,
              sends)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_load_ground_truth_digest_sends_tolerates_dash_variants():
    tmp = tempfile.mkdtemp()
    try:
        send_log = os.path.join(tmp, "send-log.txt")
        _write_send_log(send_log, [
            _gt_send_line("2026-09-12T20:34:00-04:00", "2026-09-12", subject_sep="—"),
        ])
        sends, _ = gti.load_ground_truth_digest_sends(send_log)
        check("an em-dash subject separator still matches (prefix-only check)",
              len(sends) == 1, sends)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_load_ground_truth_digest_sends_converts_et_offset_correctly():
    tmp = tempfile.mkdtemp()
    try:
        send_log = os.path.join(tmp, "send-log.txt")
        _write_send_log(send_log, [_gt_send_line("2026-09-12T20:00:00-04:00", "2026-09-12")])
        sends, _ = gti.load_ground_truth_digest_sends(send_log)
        check("a -04:00 ET send converts to the correct UTC instant (crosses "
              "into the next calendar day)",
              sends and sends[0] == datetime(2026, 9, 13, 0, 0, tzinfo=timezone.utc), sends)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_load_ground_truth_digest_sends_missing_file_is_fail_open_with_warning():
    sends, warning = gti.load_ground_truth_digest_sends(
        os.path.join(tempfile.gettempdir(), "definitely-missing-oi296-sendlog.txt"))
    check("a missing send log yields no sends", sends == [], sends)
    check("a missing send log produces a warning naming dedup being disabled",
          warning is not None and "dedup disabled" in warning, warning)


def test_load_ground_truth_digest_sends_unreadable_path_is_fail_open_with_warning():
    tmp = tempfile.mkdtemp()
    try:
        # a directory where a file is expected -- open() raises OSError
        sends, warning = gti.load_ground_truth_digest_sends(tmp)
        check("an unreadable (directory) send log path yields no sends", sends == [], sends)
        check("an unreadable send log produces a warning", warning is not None, warning)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# --- load_previously_audited (published-via-send-log semantics) ------------

def test_load_previously_audited_requires_an_actual_send_to_count_as_published():
    tmp = tempfile.mkdtemp()
    try:
        state_dir = os.path.join(tmp, "state")
        send_log = os.path.join(tmp, "send-log.txt")
        run_id = "cc:ora-pm-ledger:2026-09-12T19:00:00.000Z"
        _write_prior_run_index(state_dir, "2026-09-12",
                                [{"run_id": run_id, "task_id": "ora-pm-ledger", "fleet": "cc"}],
                                generated_at="2026-09-12T20:00:00.000Z")
        _write_send_log(send_log, [])  # index exists, nothing was ever sent
        now = datetime(2026, 9, 13, 12, 0, tzinfo=timezone.utc)
        prior, warnings = gti.load_previously_audited(state_dir, now, send_log_path=send_log)
        check("an index with no matching send is never treated as published",
              prior == {}, prior)
        check("no warnings for a legitimately-empty send log", warnings == [], warnings)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_load_previously_audited_orders_candidates_by_generated_at_not_filename():
    # req 8: order candidate indexes by generated_at, never by filename --
    # the OLDER-generated document is filed under a LATER-looking filename
    # date to prove filename order is never consulted.
    tmp = tempfile.mkdtemp()
    try:
        state_dir = os.path.join(tmp, "state")
        send_log = os.path.join(tmp, "send-log.txt")
        run_id_early = "cc:ora-early-task:2026-09-12T19:00:00.000Z"
        run_id_late = "cc:ora-late-task:2026-09-12T23:00:00.000Z"
        # filename says "09-11" but is actually generated LATER than "09-12"
        _write_prior_run_index(state_dir, "2026-09-11",
                                [{"run_id": run_id_late, "task_id": "ora-late-task", "fleet": "cc"}],
                                generated_at="2026-09-13T00:00:00.000Z")
        _write_prior_run_index(state_dir, "2026-09-12",
                                [{"run_id": run_id_early, "task_id": "ora-early-task", "fleet": "cc"}],
                                generated_at="2026-09-12T20:00:00.000Z")
        _write_send_log(send_log, [
            _gt_send_line("2026-09-12T16:05:00-04:00", "2026-09-12"),  # -> 20:05Z, pairs with EARLY
            _gt_send_line("2026-09-12T20:10:00-04:00", "2026-09-13"),  # -> 00:10Z next day, pairs with LATE
        ])
        now = datetime(2026, 9, 13, 12, 0, tzinfo=timezone.utc)
        prior, _ = gti.load_previously_audited(state_dir, now, send_log_path=send_log)
        check("the early-generated doc's run is published (paired by "
              "generated_at, not its '09-12' filename)", run_id_early in prior, prior)
        check("the late-generated doc's run is ALSO published (its '09-11' "
              "filename is a red herring -- ordering used generated_at)",
              run_id_late in prior, prior)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_load_previously_audited_same_utc_day_rerun_dedups_against_earlier_published_run():
    tmp = tempfile.mkdtemp()
    try:
        state_dir = os.path.join(tmp, "state")
        send_log = os.path.join(tmp, "send-log.txt")
        run_id = "cc:ora-pm-ledger:2026-09-13T05:00:00.000Z"
        _write_prior_run_index(state_dir, "2026-09-13",
                                [{"run_id": run_id, "task_id": "ora-pm-ledger", "fleet": "cc"}],
                                generated_at="2026-09-13T09:00:00.000Z")
        _write_send_log(send_log, [_gt_send_line("2026-09-13T05:21:00-04:00", "2026-09-13")])  # -> 09:21Z
        now = datetime(2026, 9, 13, 11, 0, tzinfo=timezone.utc)  # SAME calendar day as the prior index
        prior, _ = gti.load_previously_audited(state_dir, now, send_log_path=send_log)
        check("a same-UTC-day published prior run IS deduped -- the old "
              "filename/calendar-day exclusion is gone (OI-296 review round 2)",
              run_id in prior, prior)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_load_previously_audited_overwritten_index_does_not_pair_with_earlier_send():
    # the on-disk index for today was overwritten by a SECOND same-day run
    # AFTER an earlier send already went out (for now-lost prior content) --
    # its generated_at (10:00Z) postdates that send (09:21Z), so it must NOT
    # be credited with a publish it never itself received.
    tmp = tempfile.mkdtemp()
    try:
        state_dir = os.path.join(tmp, "state")
        send_log = os.path.join(tmp, "send-log.txt")
        run_id_b = "cc:ora-task-b:2026-09-13T09:30:00.000Z"
        _write_prior_run_index(state_dir, "2026-09-13",
                                [{"run_id": run_id_b, "task_id": "ora-task-b", "fleet": "cc"}],
                                generated_at="2026-09-13T10:00:00.000Z")
        _write_send_log(send_log, [_gt_send_line("2026-09-13T09:21:00+00:00", "2026-09-13")])
        now = datetime(2026, 9, 13, 12, 0, tzinfo=timezone.utc)
        prior, _ = gti.load_previously_audited(state_dir, now, send_log_path=send_log)
        check("the overwritten index's run is NOT paired with a send that "
              "predates its own generated_at -- it was never itself actually "
              "sent", run_id_b not in prior, prior)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_load_previously_audited_et_evening_send_crossing_utc_midnight():
    tmp = tempfile.mkdtemp()
    try:
        state_dir = os.path.join(tmp, "state")
        send_log = os.path.join(tmp, "send-log.txt")
        run_id = "cc:ora-pm-ledger:2026-09-12T19:00:00.000Z"
        # generated late UTC-evening on 09-12 (23:50Z)
        _write_prior_run_index(state_dir, "2026-09-12",
                                [{"run_id": run_id, "task_id": "ora-pm-ledger", "fleet": "cc"}],
                                generated_at="2026-09-12T23:50:00.000Z")
        # sent at 20:00 ET on 09-12 (local date string still "09-12") but
        # that instant is 00:00Z on 09-13 -- a DIFFERENT UTC calendar date
        # than either the generated_at's date or the send's own local date
        _write_send_log(send_log, [_gt_send_line("2026-09-12T20:00:00-04:00", "2026-09-12")])
        now = datetime(2026, 9, 13, 6, 0, tzinfo=timezone.utc)
        prior, _ = gti.load_previously_audited(state_dir, now, send_log_path=send_log)
        check("an ET-evening send whose UTC instant lands on the NEXT "
              "calendar day still correctly pairs with the prior "
              "UTC-evening index (true instant comparison, not date-string "
              "matching)", run_id in prior, prior)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_load_previously_audited_send_log_unreadable_disables_dedup_with_warning():
    tmp = tempfile.mkdtemp()
    try:
        state_dir = os.path.join(tmp, "state")
        run_id = "cc:ora-pm-ledger:2026-09-12T19:00:00.000Z"
        _write_prior_run_index(state_dir, "2026-09-12",
                                [{"run_id": run_id, "task_id": "ora-pm-ledger", "fleet": "cc"}],
                                generated_at="2026-09-12T20:00:00.000Z")
        missing_send_log = os.path.join(tmp, "does-not-exist-send-log.txt")
        now = datetime(2026, 9, 13, 12, 0, tzinfo=timezone.utc)
        prior, warnings = gti.load_previously_audited(state_dir, now, send_log_path=missing_send_log)
        check("an unreadable/missing send log yields NOTHING previously "
              "audited (fail open)", prior == {}, prior)
        check("a warning explains dedup was disabled because the send log "
              "was unreadable", warnings and "dedup disabled" in warnings[0], warnings)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_load_previously_audited_prefilter_skips_far_out_of_range_files_without_opening():
    # req 9: a cheap filename-date prefilter bounds the lookback before ANY
    # file is opened -- proven here by making the far-out-of-range file
    # corrupt: if it were opened, a "could not read" warning would appear.
    tmp = tempfile.mkdtemp()
    try:
        state_dir = os.path.join(tmp, "state")
        os.makedirs(state_dir, exist_ok=True)
        send_log = os.path.join(tmp, "send-log.txt")
        _write_send_log(send_log, [])
        far_path = os.path.join(state_dir, "run-index-2020-01-01.json")
        open(far_path, "w", encoding="utf-8").write("{not valid json at all")
        now = datetime(2026, 9, 13, 12, 0, tzinfo=timezone.utc)
        prior, warnings = gti.load_previously_audited(
            state_dir, now, window_hours=24.0, send_log_path=send_log)
        check("a far-out-of-range corrupt file produces no warning -- the "
              "cheap prefilter skipped it before ever opening it",
              warnings == [], warnings)
        check("nothing previously audited (the only file was prefiltered "
              "out)", prior == {}, prior)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_load_previously_audited_corrupt_prior_index_in_range_still_warns():
    tmp = tempfile.mkdtemp()
    try:
        state_dir = os.path.join(tmp, "state")
        os.makedirs(state_dir, exist_ok=True)
        send_log = os.path.join(tmp, "send-log.txt")
        _write_send_log(send_log, [])
        near_path = os.path.join(state_dir, "run-index-2026-09-12.json")
        open(near_path, "w", encoding="utf-8").write("{not valid json")
        now = datetime(2026, 9, 13, 12, 0, tzinfo=timezone.utc)
        prior, warnings = gti.load_previously_audited(
            state_dir, now, window_hours=24.0, send_log_path=send_log)
        check("a corrupt prior index inside the horizon still produces a "
              "warning", len(warnings) == 1 and "run-index-2026-09-12.json" in warnings[0],
              warnings)
        check("a corrupt prior index never crashes / yields nothing", prior == {}, prior)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_load_previously_audited_missing_generated_at_warns():
    tmp = tempfile.mkdtemp()
    try:
        state_dir = os.path.join(tmp, "state")
        os.makedirs(state_dir, exist_ok=True)
        send_log = os.path.join(tmp, "send-log.txt")
        _write_send_log(send_log, [])
        path = os.path.join(state_dir, "run-index-2026-09-12.json")
        json.dump({"runs": []}, open(path, "w", encoding="utf-8"))  # no generated_at at all
        now = datetime(2026, 9, 13, 12, 0, tzinfo=timezone.utc)
        prior, warnings = gti.load_previously_audited(state_dir, now, send_log_path=send_log)
        check("a prior index with no generated_at warns and contributes "
              "nothing", prior == {} and len(warnings) == 1 and "generated_at" in warnings[0],
              (prior, warnings))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_load_previously_audited_missing_state_dir_is_safe():
    prior, warnings = gti.load_previously_audited(
        os.path.join(tempfile.gettempdir(), "definitely-does-not-exist-oi296"),
        datetime(2026, 9, 13, 12, 0, tzinfo=timezone.utc))
    check("a missing state dir yields empty results, never raises",
          prior == {} and warnings == [], (prior, warnings))


# --- build_run_index integration --------------------------------------------

def test_build_run_index_no_skip_when_prior_index_was_never_sent():
    tmp = tempfile.mkdtemp()
    try:
        cc_dir = os.path.join(tmp, "cc")
        cc_reg = os.path.join(cc_dir, "scheduled-tasks.json")
        state_dir = os.path.join(tmp, "state")
        send_log = os.path.join(tmp, "send-log.txt")
        last_run = "2026-09-12T19:00:00.000Z"
        _write_registry(cc_reg, [
            {"id": "ora-pm-ledger", "cronExpression": "0 19 * * *",
             "enabled": True, "lastRunAt": last_run, "lastScheduledFor": last_run},
        ])
        lams_reg = os.path.join(tmp, "lams", "scheduled-tasks.json")
        _write_registry(lams_reg, [])
        run_id = gti.build_run_id("cc", "ora-pm-ledger", last_run)
        _write_prior_run_index(state_dir, "2026-09-12",
                                [_prior_run_record(run_id, "ora-pm-ledger", "cc")],
                                generated_at="2026-09-12T20:00:00.000Z")
        _write_send_log(send_log, [])  # index exists, nothing was ever sent

        now = datetime(2026, 9, 13, 12, 0, tzinfo=timezone.utc)
        index = gti.build_run_index(cc_reg, lams_reg, [], now=now,
                                     ground_truth_state_dir=state_dir, send_log_path=send_log)
        check("a run whose prior index was never actually SENT is not "
              "skipped", any(r["run_id"] == run_id for r in index["runs"]), index["runs"])
        check("previously_audited is empty", index["previously_audited"] == [],
              index["previously_audited"])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_build_run_index_skips_previously_published_unjoined_run():
    tmp = tempfile.mkdtemp()
    try:
        cc_dir = os.path.join(tmp, "cc")
        cc_reg = os.path.join(cc_dir, "scheduled-tasks.json")
        state_dir = os.path.join(tmp, "state")
        send_log = os.path.join(tmp, "send-log.txt")
        last_run = "2026-09-12T19:00:00.000Z"
        _write_registry(cc_reg, [
            {"id": "ora-pm-ledger", "cronExpression": "0 19 * * *",
             "enabled": True, "lastRunAt": last_run, "lastScheduledFor": last_run},
        ])
        lams_reg = os.path.join(tmp, "lams", "scheduled-tasks.json")
        _write_registry(lams_reg, [])
        run_id = gti.build_run_id("cc", "ora-pm-ledger", last_run)
        _write_prior_run_index(state_dir, "2026-09-12",
                                [_prior_run_record(run_id, "ora-pm-ledger", "cc", candidate_session_count=1)],
                                generated_at="2026-09-12T20:00:00.000Z")
        _write_send_log(send_log, [_gt_send_line("2026-09-12T16:34:00-04:00", "2026-09-12")])  # -> 20:34Z

        now = datetime(2026, 9, 13, 12, 0, tzinfo=timezone.utc)
        index = gti.build_run_index(cc_reg, lams_reg, [], now=now,
                                     ground_truth_state_dir=state_dir, send_log_path=send_log)
        check("the previously-published, unjoined run does not appear in "
              "runs", all(r["run_id"] != run_id for r in index["runs"]), index["runs"])
        hits = [p for p in index["previously_audited"] if p["run_id"] == run_id]
        check("it is recorded in previously_audited", hits != [], index["previously_audited"])
        check("audited_in_digest names the actual send time (UTC)",
              hits and hits[0]["audited_in_digest"].startswith("2026-09-12T20:34:00"), hits)
        check("no reaudited_after_prior_digest entries for a plain skip",
              index["reaudited_after_prior_digest"] == [], index)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_build_run_index_reincludes_on_session_count_growth():
    tmp = tempfile.mkdtemp()
    try:
        cc_dir = os.path.join(tmp, "cc")
        cc_reg = os.path.join(cc_dir, "scheduled-tasks.json")
        state_dir = os.path.join(tmp, "state")
        send_log = os.path.join(tmp, "send-log.txt")
        last_run = "2026-09-12T19:00:00.000Z"
        _write_registry(cc_reg, [
            {"id": "ora-pm-ledger", "cronExpression": "0 19 * * *",
             "enabled": True, "lastRunAt": last_run, "lastScheduledFor": last_run},
        ])
        t_ms = int(datetime.fromisoformat(last_run.replace("Z", "+00:00")).timestamp() * 1000)
        # TWO session records claiming this firing NOW -- a new session for
        # the same cycle appeared AFTER the prior audit only recorded ONE
        _write_session_record(cc_dir, "local_fire_a", t_ms, "Ora pm ledger",
                               cli_session_id="fire-a", scheduled_task_id="ora-pm-ledger")
        _write_session_record(cc_dir, "local_fire_b", t_ms + 4000, "Ora pm ledger",
                               cli_session_id="fire-b", scheduled_task_id="ora-pm-ledger")
        proj_dir = os.path.join(tmp, "proj")
        os.makedirs(proj_dir)
        open(os.path.join(proj_dir, "fire-a.jsonl"), "w").close()
        open(os.path.join(proj_dir, "fire-b.jsonl"), "w").close()

        lams_reg = os.path.join(tmp, "lams", "scheduled-tasks.json")
        _write_registry(lams_reg, [])

        run_id = gti.build_run_id("cc", "ora-pm-ledger", last_run)
        # prior published index recorded only 1 session for this cycle, and
        # a deliberately huge transcript_size so size-growth never fires --
        # isolating this test to the session-count-growth path
        _write_prior_run_index(state_dir, "2026-09-12",
                                [_prior_run_record(run_id, "ora-pm-ledger", "cc",
                                                    candidate_session_count=1,
                                                    transcript_size=1_000_000, transcript_mtime=0.0)],
                                generated_at="2026-09-12T20:00:00.000Z")
        _write_send_log(send_log, [_gt_send_line("2026-09-12T16:34:00-04:00", "2026-09-12")])

        now = datetime(2026, 9, 13, 12, 0, tzinfo=timezone.utc)
        index = gti.build_run_index(cc_reg, lams_reg, [proj_dir], now=now,
                                     ground_truth_state_dir=state_dir, send_log_path=send_log)
        check("a run whose candidate_session_count GREW past the prior "
              "published count is re-included",
              any(r["run_id"] == run_id for r in index["runs"]), index["runs"])
        reaud = [r for r in index["reaudited_after_prior_digest"] if r["run_id"] == run_id]
        check("it is recorded with the session-growth reason", reaud and
              reaud[0]["reason"] == "new session for same cycle after prior digest", reaud)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_build_run_index_reincludes_on_transcript_size_growth():
    tmp = tempfile.mkdtemp()
    try:
        cc_dir = os.path.join(tmp, "cc")
        cc_reg = os.path.join(cc_dir, "scheduled-tasks.json")
        state_dir = os.path.join(tmp, "state")
        send_log = os.path.join(tmp, "send-log.txt")
        last_run = "2026-09-12T19:00:00.000Z"
        _write_registry(cc_reg, [
            {"id": "ora-pm-ledger", "cronExpression": "0 19 * * *",
             "enabled": True, "lastRunAt": last_run, "lastScheduledFor": last_run},
        ])
        t_ms = int(datetime.fromisoformat(last_run.replace("Z", "+00:00")).timestamp() * 1000)
        _write_session_record(cc_dir, "local_pmledger", t_ms, "Ora pm ledger",
                               cli_session_id="pmledger-cli", scheduled_task_id="ora-pm-ledger")
        proj_dir = os.path.join(tmp, "proj")
        os.makedirs(proj_dir)
        transcript_path = os.path.join(proj_dir, "pmledger-cli.jsonl")
        open(transcript_path, "w", encoding="utf-8").write("x" * 500)  # 500 bytes NOW

        lams_reg = os.path.join(tmp, "lams", "scheduled-tasks.json")
        _write_registry(lams_reg, [])

        run_id = gti.build_run_id("cc", "ora-pm-ledger", last_run)
        _write_prior_run_index(state_dir, "2026-09-12",
                                [_prior_run_record(run_id, "ora-pm-ledger", "cc",
                                                    candidate_session_count=1,
                                                    transcript_size=100,  # smaller than the 500 bytes above
                                                    transcript_mtime=0.0)],
                                generated_at="2026-09-12T20:00:00.000Z")
        _write_send_log(send_log, [_gt_send_line("2026-09-12T16:34:00-04:00", "2026-09-12")])

        now = datetime(2026, 9, 13, 12, 0, tzinfo=timezone.utc)
        index = gti.build_run_index(cc_reg, lams_reg, [proj_dir], now=now,
                                     ground_truth_state_dir=state_dir, send_log_path=send_log)
        check("a run whose transcript GREW past the prior published size "
              "is re-included", any(r["run_id"] == run_id for r in index["runs"]), index["runs"])
        reaud = [r for r in index["reaudited_after_prior_digest"] if r["run_id"] == run_id]
        check("it carries the transcript-growth reason", reaud and
              reaud[0]["reason"] == "transcript grew after prior audit", reaud)
        run = [r for r in index["runs"] if r["run_id"] == run_id][0]
        check("the run record itself carries transcript_size/transcript_mtime",
              run["transcript_size"] == 500 and run["transcript_mtime"] is not None, run)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_build_run_index_falls_back_to_mtime_rule_when_prior_lacks_transcript_size():
    tmp = tempfile.mkdtemp()
    try:
        cc_dir = os.path.join(tmp, "cc")
        cc_reg = os.path.join(cc_dir, "scheduled-tasks.json")
        state_dir = os.path.join(tmp, "state")
        send_log = os.path.join(tmp, "send-log.txt")
        last_run = "2026-09-12T19:00:00.000Z"
        _write_registry(cc_reg, [
            {"id": "ora-pm-ledger", "cronExpression": "0 19 * * *",
             "enabled": True, "lastRunAt": last_run, "lastScheduledFor": last_run},
        ])
        t_ms = int(datetime.fromisoformat(last_run.replace("Z", "+00:00")).timestamp() * 1000)
        _write_session_record(cc_dir, "local_pmledger", t_ms, "Ora pm ledger",
                               cli_session_id="pmledger-cli", scheduled_task_id="ora-pm-ledger")
        proj_dir = os.path.join(tmp, "proj")
        os.makedirs(proj_dir)
        transcript_path = os.path.join(proj_dir, "pmledger-cli.jsonl")
        open(transcript_path, "w").close()

        lams_reg = os.path.join(tmp, "lams", "scheduled-tasks.json")
        _write_registry(lams_reg, [])

        run_id = gti.build_run_id("cc", "ora-pm-ledger", last_run)
        # OLD-shaped prior record -- no transcript_size/transcript_mtime keys
        # at all (predates this round of changes)
        _write_prior_run_index(state_dir, "2026-09-12",
                                [_prior_run_record(run_id, "ora-pm-ledger", "cc",
                                                    candidate_session_count=1,
                                                    include_transcript_size=False)],
                                generated_at="2026-09-12T20:00:00.000Z")
        send_dt = "2026-09-12T16:34:00-04:00"  # -> 20:34:00Z
        _write_send_log(send_log, [_gt_send_line(send_dt, "2026-09-12")])
        publish_epoch = datetime.fromisoformat(send_dt).astimezone(timezone.utc).timestamp()
        os.utime(transcript_path, (publish_epoch + 100, publish_epoch + 100))  # modified AFTER the send

        now = datetime(2026, 9, 13, 12, 0, tzinfo=timezone.utc)
        index = gti.build_run_index(cc_reg, lams_reg, [proj_dir], now=now,
                                     ground_truth_state_dir=state_dir, send_log_path=send_log)
        check("with no prior transcript_size, the OLD mtime-vs-send-time "
              "rule re-includes a transcript modified after the send",
              any(r["run_id"] == run_id for r in index["runs"]), index["runs"])
        reaud = [r for r in index["reaudited_after_prior_digest"] if r["run_id"] == run_id]
        check("it carries the back-compat mtime reason", reaud and
              reaud[0]["reason"] == "transcript modified after prior digest", reaud)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_build_run_index_does_not_reinclude_when_transcript_size_not_greater():
    tmp = tempfile.mkdtemp()
    try:
        cc_dir = os.path.join(tmp, "cc")
        cc_reg = os.path.join(cc_dir, "scheduled-tasks.json")
        state_dir = os.path.join(tmp, "state")
        send_log = os.path.join(tmp, "send-log.txt")
        last_run = "2026-09-12T19:00:00.000Z"
        _write_registry(cc_reg, [
            {"id": "ora-pm-ledger", "cronExpression": "0 19 * * *",
             "enabled": True, "lastRunAt": last_run, "lastScheduledFor": last_run},
        ])
        t_ms = int(datetime.fromisoformat(last_run.replace("Z", "+00:00")).timestamp() * 1000)
        _write_session_record(cc_dir, "local_pmledger", t_ms, "Ora pm ledger",
                               cli_session_id="pmledger-cli", scheduled_task_id="ora-pm-ledger")
        proj_dir = os.path.join(tmp, "proj")
        os.makedirs(proj_dir)
        transcript_path = os.path.join(proj_dir, "pmledger-cli.jsonl")
        open(transcript_path, "w", encoding="utf-8").write("x" * 200)  # 200 bytes now

        lams_reg = os.path.join(tmp, "lams", "scheduled-tasks.json")
        _write_registry(lams_reg, [])

        run_id = gti.build_run_id("cc", "ora-pm-ledger", last_run)
        _write_prior_run_index(state_dir, "2026-09-12",
                                [_prior_run_record(run_id, "ora-pm-ledger", "cc",
                                                    candidate_session_count=1,
                                                    transcript_size=200,  # SAME size -- no growth
                                                    transcript_mtime=0.0)],
                                generated_at="2026-09-12T20:00:00.000Z")
        _write_send_log(send_log, [_gt_send_line("2026-09-12T16:34:00-04:00", "2026-09-12")])

        now = datetime(2026, 9, 13, 12, 0, tzinfo=timezone.utc)
        index = gti.build_run_index(cc_reg, lams_reg, [proj_dir], now=now,
                                     ground_truth_state_dir=state_dir, send_log_path=send_log)
        check("an unchanged transcript size does NOT re-include -- still "
              "skipped", all(r["run_id"] != run_id for r in index["runs"]), index["runs"])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_build_run_index_join_stats_total_includes_skipped_runs_but_audited_excludes_them():
    # req 3 (MAJOR): join_stats total/joined measure transcript-join health
    # across EVERY in-window candidate, before dedup; "audited" is the
    # post-dedup count.
    tmp = tempfile.mkdtemp()
    try:
        cc_dir = os.path.join(tmp, "cc")
        cc_reg = os.path.join(cc_dir, "scheduled-tasks.json")
        state_dir = os.path.join(tmp, "state")
        send_log = os.path.join(tmp, "send-log.txt")
        skipped_last_run = "2026-09-12T19:00:00.000Z"
        new_last_run = "2026-09-13T05:00:00.000Z"
        _write_registry(cc_reg, [
            {"id": "ora-pm-ledger", "cronExpression": "0 19 * * *",
             "enabled": True, "lastRunAt": skipped_last_run, "lastScheduledFor": skipped_last_run},
            {"id": "ora-am-brief", "cronExpression": "0 5 * * *",
             "enabled": True, "lastRunAt": new_last_run, "lastScheduledFor": new_last_run},
        ])
        lams_reg = os.path.join(tmp, "lams", "scheduled-tasks.json")
        _write_registry(lams_reg, [])

        skipped_run_id = gti.build_run_id("cc", "ora-pm-ledger", skipped_last_run)
        _write_prior_run_index(state_dir, "2026-09-12",
                                [_prior_run_record(skipped_run_id, "ora-pm-ledger", "cc")],
                                generated_at="2026-09-12T20:00:00.000Z")
        _write_send_log(send_log, [_gt_send_line("2026-09-12T16:34:00-04:00", "2026-09-12")])

        now = datetime(2026, 9, 13, 12, 0, tzinfo=timezone.utc)
        index = gti.build_run_index(cc_reg, lams_reg, [], now=now,
                                     ground_truth_state_dir=state_dir, send_log_path=send_log)
        check("exactly one run survives into `runs` (the new one)",
              len(index["runs"]) == 1, index["runs"])
        check("join_stats TOTAL counts BOTH in-window candidates regardless "
              "of the skip", index["join_stats"]["cc"]["total"] == 2, index["join_stats"])
        check("join_stats AUDITED counts only the one that survived dedup",
              index["join_stats"]["cc"]["audited"] == 1, index["join_stats"])
        check("exactly one previously_audited entry recorded",
              len(index["previously_audited"]) == 1, index["previously_audited"])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_build_run_index_duplicate_detection_excludes_skipped_run_even_with_multiple_sessions():
    # req 5 (strengthened): give the SKIPPED run >= 2 matching sessions --
    # it WOULD raise same_cycle_refire if it weren't excluded from `runs`
    # before detect_duplicates ever saw it.
    tmp = tempfile.mkdtemp()
    try:
        cc_dir = os.path.join(tmp, "cc")
        cc_reg = os.path.join(cc_dir, "scheduled-tasks.json")
        state_dir = os.path.join(tmp, "state")
        send_log = os.path.join(tmp, "send-log.txt")
        last_run = "2026-09-12T19:00:00.000Z"
        _write_registry(cc_reg, [
            {"id": "ora-pm-ledger", "cronExpression": "0 19 * * *",
             "enabled": True, "lastRunAt": last_run, "lastScheduledFor": last_run},
        ])
        t_ms = int(datetime.fromisoformat(last_run.replace("Z", "+00:00")).timestamp() * 1000)
        _write_session_record(cc_dir, "local_fire_a", t_ms, "Ora pm ledger",
                               cli_session_id="fire-a", scheduled_task_id="ora-pm-ledger")
        _write_session_record(cc_dir, "local_fire_b", t_ms + 4000, "Ora pm ledger",
                               cli_session_id="fire-b", scheduled_task_id="ora-pm-ledger")
        proj_dir = os.path.join(tmp, "proj")
        os.makedirs(proj_dir)
        open(os.path.join(proj_dir, "fire-a.jsonl"), "w").close()
        open(os.path.join(proj_dir, "fire-b.jsonl"), "w").close()

        lams_reg = os.path.join(tmp, "lams", "scheduled-tasks.json")
        _write_registry(lams_reg, [])

        run_id = gti.build_run_id("cc", "ora-pm-ledger", last_run)
        # prior published index already recorded 2 sessions for this cycle
        # (no session-growth) and a huge transcript_size (no size-growth) --
        # stays skipped despite carrying 2 matching sessions NOW.
        _write_prior_run_index(state_dir, "2026-09-12",
                                [_prior_run_record(run_id, "ora-pm-ledger", "cc",
                                                    candidate_session_count=2,
                                                    transcript_size=10_000_000, transcript_mtime=0.0)],
                                generated_at="2026-09-12T20:00:00.000Z")
        _write_send_log(send_log, [_gt_send_line("2026-09-12T16:34:00-04:00", "2026-09-12")])

        now = datetime(2026, 9, 13, 12, 0, tzinfo=timezone.utc)
        index = gti.build_run_index(cc_reg, lams_reg, [proj_dir], now=now,
                                     ground_truth_state_dir=state_dir, send_log_path=send_log)
        check("the run (with 2 matching sessions) is still skipped -- no "
              "growth in either signal",
              all(r["run_id"] != run_id for r in index["runs"]), index["runs"])
        check("same_cycle_refire never fires for a run excluded before "
              "detect_duplicates ever saw it",
              all(f["type"] != "same_cycle_refire" for f in index["duplicate_flags"]),
              index["duplicate_flags"])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_build_run_index_no_dedup_disables_everything():
    tmp = tempfile.mkdtemp()
    try:
        cc_dir = os.path.join(tmp, "cc")
        cc_reg = os.path.join(cc_dir, "scheduled-tasks.json")
        state_dir = os.path.join(tmp, "state")
        send_log = os.path.join(tmp, "send-log.txt")
        last_run = "2026-09-12T19:00:00.000Z"
        _write_registry(cc_reg, [
            {"id": "ora-pm-ledger", "cronExpression": "0 19 * * *",
             "enabled": True, "lastRunAt": last_run, "lastScheduledFor": last_run},
        ])
        lams_reg = os.path.join(tmp, "lams", "scheduled-tasks.json")
        _write_registry(lams_reg, [])
        run_id = gti.build_run_id("cc", "ora-pm-ledger", last_run)
        _write_prior_run_index(state_dir, "2026-09-12",
                                [_prior_run_record(run_id, "ora-pm-ledger", "cc")],
                                generated_at="2026-09-12T20:00:00.000Z")
        _write_send_log(send_log, [_gt_send_line("2026-09-12T16:34:00-04:00", "2026-09-12")])

        now = datetime(2026, 9, 13, 12, 0, tzinfo=timezone.utc)
        index = gti.build_run_index(cc_reg, lams_reg, [], now=now,
                                     ground_truth_state_dir=state_dir, send_log_path=send_log,
                                     dedup_previously_audited=False)
        check("dedup_previously_audited=False disables the skip entirely",
              any(r["run_id"] == run_id for r in index["runs"]), index["runs"])
        check("previously_audited is empty when dedup is disabled",
              index["previously_audited"] == [], index["previously_audited"])
        check("join_stats audited count equals total when dedup is disabled",
              index["join_stats"]["cc"]["audited"] == index["join_stats"]["cc"]["total"],
              index["join_stats"])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_build_run_index_corrupt_prior_index_adds_warning_not_crash():
    tmp = tempfile.mkdtemp()
    try:
        cc_dir = os.path.join(tmp, "cc")
        cc_reg = os.path.join(cc_dir, "scheduled-tasks.json")
        state_dir = os.path.join(tmp, "state")
        os.makedirs(state_dir)
        send_log = os.path.join(tmp, "send-log.txt")
        _write_send_log(send_log, [])
        last_run = "2026-09-13T05:00:00.000Z"
        _write_registry(cc_reg, [
            {"id": "ora-am-brief", "cronExpression": "0 5 * * *",
             "enabled": True, "lastRunAt": last_run, "lastScheduledFor": last_run},
        ])
        lams_reg = os.path.join(tmp, "lams", "scheduled-tasks.json")
        _write_registry(lams_reg, [])

        open(os.path.join(state_dir, "run-index-2026-09-12.json"), "w",
             encoding="utf-8").write("{not valid json")

        now = datetime(2026, 9, 13, 12, 0, tzinfo=timezone.utc)
        index = gti.build_run_index(cc_reg, lams_reg, [], now=now,
                                     ground_truth_state_dir=state_dir, send_log_path=send_log)
        check("a corrupt prior index never crashes build_run_index",
              len(index["runs"]) == 1, index["runs"])
        check("the corrupt index produces a warning in the output document",
              len(index.get("warnings", [])) == 1
              and "run-index-2026-09-12.json" in index["warnings"][0], index.get("warnings"))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_build_run_index_default_ground_truth_state_dir_is_last_run_marker_dirname():
    # Injectability contract: omitting ground_truth_state_dir must fall back
    # to os.path.dirname(LAST_RUN_MARKER), not silently disable dedup.
    tmp = tempfile.mkdtemp()
    try:
        cc_dir = os.path.join(tmp, "cc")
        cc_reg = os.path.join(cc_dir, "scheduled-tasks.json")
        last_run = "2026-09-12T19:00:00.000Z"
        _write_registry(cc_reg, [
            {"id": "ora-pm-ledger", "cronExpression": "0 19 * * *",
             "enabled": True, "lastRunAt": last_run, "lastScheduledFor": last_run},
        ])
        lams_reg = os.path.join(tmp, "lams", "scheduled-tasks.json")
        _write_registry(lams_reg, [])
        run_id = gti.build_run_id("cc", "ora-pm-ledger", last_run)

        fake_marker_dir = os.path.join(tmp, "fake-state")
        send_log = os.path.join(tmp, "send-log.txt")
        _write_prior_run_index(fake_marker_dir, "2026-09-12",
                                [_prior_run_record(run_id, "ora-pm-ledger", "cc")],
                                generated_at="2026-09-12T20:00:00.000Z")
        _write_send_log(send_log, [_gt_send_line("2026-09-12T16:34:00-04:00", "2026-09-12")])

        orig_marker = gti.LAST_RUN_MARKER
        gti.LAST_RUN_MARKER = os.path.join(fake_marker_dir, "last-auditor-run.json")
        try:
            now = datetime(2026, 9, 13, 12, 0, tzinfo=timezone.utc)
            index = gti.build_run_index(cc_reg, lams_reg, [], now=now, send_log_path=send_log)
            check("omitting ground_truth_state_dir falls back to "
                  "dirname(LAST_RUN_MARKER), so the dedup still fires",
                  all(r["run_id"] != run_id for r in index["runs"]), index["runs"])
        finally:
            gti.LAST_RUN_MARKER = orig_marker
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_build_run_index_default_send_log_path_is_shared_send_log():
    check("the default send log path resolves under scheduled-tasks/_shared",
          gti._default_send_log_path().replace("\\", "/").endswith(
              "scheduled-tasks/_shared/send-log.txt"),
          gti._default_send_log_path())


def test_main_reports_previously_audited_skip_count_via_send_log():
    # main() uses REAL current time internally, so this fixture is built
    # relative to actual now rather than a fixed 2026-09-1x date.
    #
    # req 3 (round 2): join_stats now measures the floor over ALL in-window
    # candidates BEFORE dedup, so a skipped-but-UNJOINED run would legitimately
    # fail the floor and make main() exit 1 -- that is not what this test is
    # about, so the run is given a real joinable transcript (kept smaller
    # than the prior recorded size, so it still gets skipped by dedup).
    tmp = tempfile.mkdtemp()
    try:
        cc_dir = os.path.join(tmp, "cc")
        os.makedirs(cc_dir, exist_ok=True)
        real_now = datetime.now(timezone.utc)
        run_last_run = real_now - timedelta(hours=3)
        run_last_run_iso = run_last_run.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        prior_date = (real_now - timedelta(days=1)).strftime("%Y-%m-%d")
        prior_generated_at = (real_now - timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        send_time_iso = (real_now - timedelta(hours=1, minutes=50)).strftime("%Y-%m-%dT%H:%M:%S+00:00")

        cc_tasks = [
            {"id": "ora-pm-ledger", "cronExpression": "0 19 * * *",
             "enabled": True, "lastRunAt": run_last_run_iso,
             "lastScheduledFor": run_last_run_iso},
        ]
        t_ms = int(run_last_run.timestamp() * 1000)
        _write_session_record(cc_dir, "local_pmledger", t_ms, "Ora pm ledger",
                               cli_session_id="pmledger-cli", scheduled_task_id="ora-pm-ledger")
        proj_dir = os.path.join(tmp, "proj")
        os.makedirs(proj_dir)
        open(os.path.join(proj_dir, "pmledger-cli.jsonl"), "w").close()  # 0 bytes -- joined but tiny

        run_id = gti.build_run_id("cc", "ora-pm-ledger", run_last_run_iso)
        _write_prior_run_index(tmp, prior_date,
                                [_prior_run_record(run_id, "ora-pm-ledger", "cc",
                                                    transcript_size=1_000_000)],  # no size growth possible
                                generated_at=prior_generated_at)
        send_log = os.path.join(tmp, "send-log.txt")
        _write_send_log(send_log, [_gt_send_line(send_time_iso, prior_date)])

        rc, out, _ = _run_main_with_state(
            ["--out", os.path.join(tmp, "out.json")], tmp, cc_tasks=cc_tasks,
            project_dirs=[proj_dir], send_log_path=send_log)
        check("main() still exits 0 -- the run is joined (floor passes) even "
              "though dedup skips it", rc == 0, rc)
        check("stdout reports the previously-audited skip count",
              "1 previously audited skipped" in out, out)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_main_no_dedup_flag_includes_previously_audited_run():
    tmp = tempfile.mkdtemp()
    try:
        cc_dir = os.path.join(tmp, "cc")
        os.makedirs(cc_dir, exist_ok=True)
        real_now = datetime.now(timezone.utc)
        run_last_run = real_now - timedelta(hours=3)
        run_last_run_iso = run_last_run.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        prior_date = (real_now - timedelta(days=1)).strftime("%Y-%m-%d")
        prior_generated_at = (real_now - timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        send_time_iso = (real_now - timedelta(hours=1, minutes=50)).strftime("%Y-%m-%dT%H:%M:%S+00:00")

        cc_tasks = [
            {"id": "ora-pm-ledger", "cronExpression": "0 19 * * *",
             "enabled": True, "lastRunAt": run_last_run_iso,
             "lastScheduledFor": run_last_run_iso},
        ]
        # give the run a real joinable transcript so the pre-existing
        # join-rate floor (unrelated to OI-296) doesn't itself fail main()
        t_ms = int(run_last_run.timestamp() * 1000)
        _write_session_record(cc_dir, "local_pmledger", t_ms, "Ora pm ledger",
                               cli_session_id="pmledger-cli", scheduled_task_id="ora-pm-ledger")
        proj_dir = os.path.join(tmp, "proj")
        os.makedirs(proj_dir)
        open(os.path.join(proj_dir, "pmledger-cli.jsonl"), "w").close()

        run_id = gti.build_run_id("cc", "ora-pm-ledger", run_last_run_iso)
        _write_prior_run_index(tmp, prior_date,
                                [_prior_run_record(run_id, "ora-pm-ledger", "cc")],
                                generated_at=prior_generated_at)
        send_log = os.path.join(tmp, "send-log.txt")
        _write_send_log(send_log, [_gt_send_line(send_time_iso, prior_date)])

        out_path = os.path.join(tmp, "out.json")
        rc, out, _ = _run_main_with_state(
            ["--out", out_path, "--no-dedup"], tmp, cc_tasks=cc_tasks,
            project_dirs=[proj_dir], send_log_path=send_log)
        check("main() exits 0", rc == 0, rc)
        check("stdout reports 0 previously audited skipped under --no-dedup",
              "0 previously audited skipped" in out, out)
        written = json.load(open(out_path, encoding="utf-8"))
        check("the run survives in the written index under --no-dedup",
              any(r["run_id"] == run_id for r in written["runs"]), written["runs"])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# I3 -- resolve_registry_paths() / main() exit-2 on total registry-discovery
# failure. Before this fix, `_sd is None` or `discover_store` returning None
# for either fleet fell through to `_registry_tasks(None)`, whose try/except
# swallows the resulting TypeError and returns [] -- 0 runs, both floors
# trivially "ok", exit 0. A broken auditor looked identical to a quiet night.
# ---------------------------------------------------------------------------

def test_resolve_registry_paths_errors_when_sd_unavailable():
    orig_sd = gti._sd
    gti._sd = None
    try:
        cc, lams, err = gti.resolve_registry_paths()
        check("cc path is None when store_discovery failed to import",
              cc is None, cc)
        check("lams path is None when store_discovery failed to import",
              lams is None, lams)
        check("error names _sd unavailability, not a generic failure",
              err is not None and "_sd" in err, err)
    finally:
        gti._sd = orig_sd


def test_resolve_registry_paths_errors_when_discover_store_returns_none():
    class FakeSD:
        @staticmethod
        def discover_store(name):
            return None  # simulate discovery running but finding nothing

    orig_sd = gti._sd
    gti._sd = FakeSD()
    try:
        cc, lams, err = gti.resolve_registry_paths()
        check("cc path is None", cc is None, cc)
        check("lams path is None", lams is None, lams)
        check("error names BOTH failed fleets, distinguishing this from the "
              "_sd-unavailable case", err is not None and "cc:" in err and "lams:" in err, err)
    finally:
        gti._sd = orig_sd


def test_resolve_registry_paths_errors_when_only_one_fleet_fails():
    class FakeSD:
        @staticmethod
        def discover_store(name):
            return None if name == "local-agent-mode-sessions" else "/fake/cc-path"

    orig_sd = gti._sd
    gti._sd = FakeSD()
    try:
        cc, lams, err = gti.resolve_registry_paths()
        check("the healthy fleet's path still resolves", cc == "/fake/cc-path", cc)
        check("the broken fleet's path is None", lams is None, lams)
        check("EITHER fleet failing is still a hard error -- not a silent partial index",
              err is not None and "lams:" in err, err)
    finally:
        gti._sd = orig_sd


def test_resolve_registry_paths_ok_when_both_fleets_resolve():
    class FakeSD:
        @staticmethod
        def discover_store(name):
            return "/fake/" + name

    orig_sd = gti._sd
    gti._sd = FakeSD()
    try:
        cc, lams, err = gti.resolve_registry_paths()
        check("cc path resolves", cc == "/fake/claude-code-sessions", cc)
        check("lams path resolves", lams == "/fake/local-agent-mode-sessions", lams)
        check("no error when both fleets resolve cleanly", err is None, err)
    finally:
        gti._sd = orig_sd


def test_main_exits_2_on_total_registry_discovery_failure():
    orig_sd = gti._sd
    gti._sd = None
    try:
        import io
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            rc = gti.main(["--json"])
        check("main() returns the NEW exit code 2 (distinct from 0=clean and "
              "1=join-rate floor breach) when registry discovery totally fails",
              rc == 2, rc)
    finally:
        gti._sd = orig_sd


# ---------------------------------------------------------------------------
# I4 -- the "last auditor run" marker must NOT be written for a --json
# (read-only) invocation, or for an explicit --window-hours (ad-hoc manual)
# override -- only the normal automatic path should reset the gap-tracking
# clock a real scheduled run depends on.
# ---------------------------------------------------------------------------

def _run_main_with_fake_registries(argv, tmp):
    """Runs gti.main(argv) against empty, valid fake registries with _sd and
    LAST_RUN_MARKER monkeypatched, capturing stdout/stderr so test output
    stays clean. Returns (rc, marker_path)."""
    import io
    import contextlib

    cc_reg = os.path.join(tmp, "cc", "scheduled-tasks.json")
    lams_reg = os.path.join(tmp, "lams", "scheduled-tasks.json")
    _write_registry(cc_reg, [])
    _write_registry(lams_reg, [])

    class FakeSD:
        @staticmethod
        def discover_store(name):
            return cc_reg if name == "claude-code-sessions" else lams_reg

    marker_path = os.path.join(tmp, "last-auditor-run.json")
    orig_sd = gti._sd
    orig_marker = gti.LAST_RUN_MARKER
    gti._sd = FakeSD()
    gti.LAST_RUN_MARKER = marker_path
    try:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            rc = gti.main(argv)
        return rc, marker_path
    finally:
        gti._sd = orig_sd
        gti.LAST_RUN_MARKER = orig_marker


def _run_main_with_state(argv, tmp, cc_tasks=None, lams_tasks=None, project_dirs=None,
                          send_log_path=None):
    """Like _run_main_with_fake_registries, but seeds the CC/LAMS registries
    with real tasks and points LAST_RUN_MARKER's directory at `tmp` -- so
    `tmp` doubles as the ground-truth state dir the OI-296 dedup reads from
    by default (dirname(LAST_RUN_MARKER)), exercising the real main()/argparse
    path end to end. `project_dirs`, if given, monkeypatches
    find_project_dirs() so a fixture-created transcript can actually join
    (main() otherwise always reads the real ~/.claude/projects tree).
    `send_log_path`, if given, monkeypatches `_default_send_log_path()` so
    main() (which has no --send-log-path CLI flag) reads a fixture send log
    instead of the real scheduled-tasks/_shared/send-log.txt.
    Returns (rc, stdout_text, marker_path)."""
    import io
    import contextlib

    cc_reg = os.path.join(tmp, "cc", "scheduled-tasks.json")
    lams_reg = os.path.join(tmp, "lams", "scheduled-tasks.json")
    _write_registry(cc_reg, cc_tasks or [])
    _write_registry(lams_reg, lams_tasks or [])

    class FakeSD:
        @staticmethod
        def discover_store(name):
            return cc_reg if name == "claude-code-sessions" else lams_reg

    marker_path = os.path.join(tmp, "last-auditor-run.json")
    orig_sd = gti._sd
    orig_marker = gti.LAST_RUN_MARKER
    orig_find_project_dirs = gti.find_project_dirs
    orig_default_send_log_path = gti._default_send_log_path
    gti._sd = FakeSD()
    gti.LAST_RUN_MARKER = marker_path
    if project_dirs is not None:
        gti.find_project_dirs = lambda *a, **k: project_dirs
    if send_log_path is not None:
        gti._default_send_log_path = lambda: send_log_path
    try:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            rc = gti.main(argv)
        return rc, buf.getvalue(), marker_path
    finally:
        gti._sd = orig_sd
        gti.LAST_RUN_MARKER = orig_marker
        gti.find_project_dirs = orig_find_project_dirs
        gti._default_send_log_path = orig_default_send_log_path


def test_main_json_flag_does_not_write_last_auditor_run_marker():
    tmp = tempfile.mkdtemp()
    try:
        rc, marker_path = _run_main_with_fake_registries(["--json"], tmp)
        check("main() with --json still exits 0 on a clean (empty) index", rc == 0, rc)
        check("the last-auditor-run marker is NOT written for a --json "
              "(read-only investigative) invocation", not os.path.exists(marker_path))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_main_window_hours_override_does_not_write_last_auditor_run_marker():
    tmp = tempfile.mkdtemp()
    try:
        rc, marker_path = _run_main_with_fake_registries(
            ["--window-hours", "48", "--out", os.path.join(tmp, "out.json")], tmp)
        check("main() with --window-hours still exits 0 on a clean (empty) index",
              rc == 0, rc)
        check("the last-auditor-run marker is NOT written for an explicit "
              "--window-hours (ad-hoc manual) override", not os.path.exists(marker_path))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_main_normal_invocation_still_writes_last_auditor_run_marker():
    # Regression guard: the real automatic nightly path (neither --json nor
    # --window-hours) must still reset the clock exactly as before.
    tmp = tempfile.mkdtemp()
    try:
        rc, marker_path = _run_main_with_fake_registries(
            ["--out", os.path.join(tmp, "out.json")], tmp)
        check("main() on the normal automatic path still exits 0", rc == 0, rc)
        check("the last-auditor-run marker IS written on a normal automatic run "
              "(unchanged behavior)", os.path.exists(marker_path))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    test_build_run_id_keys_on_last_scheduled_for()
    test_window_default_when_nothing_widens()
    test_window_widens_when_auditor_gap_exceeds_default()
    test_window_widens_on_fleet_resume_event()
    test_window_widens_on_both_auditor_gap_and_resume_event()
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
    test_join_rate_floor_resume_only_widen_uses_strict_floor()
    test_join_rate_floor_auditor_gap_widen_still_uses_loose_floor()
    test_join_rate_floor_default_widen_kind_matches_auditor_gap_behavior()
    test_build_run_index_excludes_its_own_run()
    test_build_run_index_end_to_end_joins_a_real_shaped_run()
    test_build_run_index_end_to_end_flags_a_genuine_duplicate_fire()
    test_build_run_index_persists_file_path_and_session_model_for_verifier_dispatch()
    test_build_run_index_last_auditor_run_at_is_injectable()
    test_build_run_index_default_last_auditor_run_at_falls_back_to_real_file_reader()
    test_load_ground_truth_digest_sends_parses_ok_matching_lines_and_ignores_others()
    test_load_ground_truth_digest_sends_tolerates_dash_variants()
    test_load_ground_truth_digest_sends_converts_et_offset_correctly()
    test_load_ground_truth_digest_sends_missing_file_is_fail_open_with_warning()
    test_load_ground_truth_digest_sends_unreadable_path_is_fail_open_with_warning()
    test_load_previously_audited_requires_an_actual_send_to_count_as_published()
    test_load_previously_audited_orders_candidates_by_generated_at_not_filename()
    test_load_previously_audited_same_utc_day_rerun_dedups_against_earlier_published_run()
    test_load_previously_audited_overwritten_index_does_not_pair_with_earlier_send()
    test_load_previously_audited_et_evening_send_crossing_utc_midnight()
    test_load_previously_audited_send_log_unreadable_disables_dedup_with_warning()
    test_load_previously_audited_prefilter_skips_far_out_of_range_files_without_opening()
    test_load_previously_audited_corrupt_prior_index_in_range_still_warns()
    test_load_previously_audited_missing_generated_at_warns()
    test_load_previously_audited_missing_state_dir_is_safe()
    test_build_run_index_no_skip_when_prior_index_was_never_sent()
    test_build_run_index_skips_previously_published_unjoined_run()
    test_build_run_index_reincludes_on_session_count_growth()
    test_build_run_index_reincludes_on_transcript_size_growth()
    test_build_run_index_falls_back_to_mtime_rule_when_prior_lacks_transcript_size()
    test_build_run_index_does_not_reinclude_when_transcript_size_not_greater()
    test_build_run_index_join_stats_total_includes_skipped_runs_but_audited_excludes_them()
    test_build_run_index_duplicate_detection_excludes_skipped_run_even_with_multiple_sessions()
    test_build_run_index_no_dedup_disables_everything()
    test_build_run_index_corrupt_prior_index_adds_warning_not_crash()
    test_build_run_index_default_ground_truth_state_dir_is_last_run_marker_dirname()
    test_build_run_index_default_send_log_path_is_shared_send_log()
    test_main_reports_previously_audited_skip_count_via_send_log()
    test_main_no_dedup_flag_includes_previously_audited_run()
    test_resolve_registry_paths_errors_when_sd_unavailable()
    test_resolve_registry_paths_errors_when_discover_store_returns_none()
    test_resolve_registry_paths_errors_when_only_one_fleet_fails()
    test_resolve_registry_paths_ok_when_both_fleets_resolve()
    test_main_exits_2_on_total_registry_discovery_failure()
    test_main_json_flag_does_not_write_last_auditor_run_marker()
    test_main_window_hours_override_does_not_write_last_auditor_run_marker()
    test_main_normal_invocation_still_writes_last_auditor_run_marker()
    print("-" * 72)
    if FAILURES:
        print("FAIL: %d failure(s): %s" % (len(FAILURES), ", ".join(FAILURES)))
        sys.exit(1)
    print("ALL PASS")
    sys.exit(0)
