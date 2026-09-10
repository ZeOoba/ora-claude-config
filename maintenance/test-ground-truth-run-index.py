#!/usr/bin/env python3
"""Tests for ground-truth-run-index.py -- Stage 0 of the ground-truth auditor.

House style matches the other maintenance test rigs: plain python, no pytest.
Run: python test-ground-truth-run-index.py   (exit 0 = all pass)
"""
import importlib.util
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


def test_find_executing_session_matches_by_createdat_and_title():
    # Real values from the live registries (2026-09-10): AHM's lastRunAt is
    # 2026-09-10T17:13:10.632Z; its session record's createdAt is the same
    # instant in epoch ms (1789060390632).
    task = {"id": "automation-health-monitor", "lastRunAt": "2026-09-10T17:13:10.632Z"}
    records = [
        # decoy: a notifySessionId-style stale record, months earlier
        {"createdAt": 1783537999843, "title": "Some old chat", "titleSource": "auto"},
        {"createdAt": 1789060390632, "title": "Automation health monitor", "titleSource": "auto",
         "sessionId": "local_e59d1b67-bf90-4e6b-9883-3e8a52dec80c",
         "cliSessionId": "696009a7-1727-470b-917d-51df0ec81803"},
    ]
    found = gti.find_executing_session(task, records)
    check("finds the session created at the same ms as lastRunAt",
          found is not None and found["cliSessionId"] == "696009a7-1727-470b-917d-51df0ec81803")


def test_find_executing_session_ambiguous_window_is_unjoined():
    # Catch-up burst: two sessions created inside the same 2s tolerance
    # window, neither titled for this task.
    task = {"id": "ora-weekly-hygiene", "lastRunAt": "2026-09-11T16:01:02.000Z"}
    t_ms = 1789142462000
    records = [
        {"createdAt": t_ms + 100, "title": "Ora deal sourcing scan", "titleSource": "auto"},
        {"createdAt": t_ms - 100, "title": "Ora pm ledger", "titleSource": "auto"},
    ]
    found = gti.find_executing_session(task, records)
    check("two candidates, neither titled for this task -> unjoined (never guessed)",
          found is None)


def test_find_executing_session_disambiguates_by_title_in_a_burst():
    task = {"id": "ora-weekly-hygiene", "lastRunAt": "2026-09-11T16:01:02.000Z"}
    t_ms = 1789142462000
    records = [
        {"createdAt": t_ms + 50, "title": "Ora deal sourcing scan", "titleSource": "auto"},
        {"createdAt": t_ms - 50, "title": "Ora weekly hygiene", "titleSource": "auto",
         "cliSessionId": "aaaa"},
    ]
    found = gti.find_executing_session(task, records)
    check("title match resolves an otherwise-ambiguous burst window",
          found is not None and found["cliSessionId"] == "aaaa")


def test_find_executing_session_ignores_notify_session_id():
    # A task's notifySessionId points at a record with a matching cliSessionId
    # but a createdAt from months earlier -- must NOT be selected.
    task = {"id": "ora-am-brief", "lastRunAt": "2026-09-10T06:00:00.000Z",
            "notifySessionId": "local_STALE"}
    records = [
        {"createdAt": 1783537999843, "title": "ORA EOD action ledger coverage gaps",
         "titleSource": "auto", "sessionId": "local_STALE", "cliSessionId": "stale-cli-id"},
    ]
    found = gti.find_executing_session(task, records)
    check("a notifySessionId record with the wrong createdAt is never selected",
          found is None)


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


if __name__ == "__main__":
    test_build_run_id_keys_on_last_scheduled_for()
    test_window_default_when_nothing_widens()
    test_window_widens_when_auditor_gap_exceeds_default()
    test_window_widens_on_fleet_resume_event()
    test_recurring_task_named_resume_does_not_widen()
    test_never_ran_does_not_widen_without_a_resume_event()
    test_find_executing_session_matches_by_createdat_and_title()
    test_find_executing_session_ambiguous_window_is_unjoined()
    test_find_executing_session_disambiguates_by_title_in_a_burst()
    test_find_executing_session_ignores_notify_session_id()
    test_join_cc_transcript_across_multiple_project_dirs()
    test_join_cc_transcript_absent_degrades_to_none()
    test_join_lams_transcript_uses_session_id_with_prefix_intact()
    test_join_lams_transcript_absent_degrades_to_none()
    print("-" * 72)
    if FAILURES:
        print("FAIL: %d failure(s): %s" % (len(FAILURES), ", ".join(FAILURES)))
        sys.exit(1)
    print("ALL PASS")
    sys.exit(0)
