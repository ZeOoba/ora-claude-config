#!/usr/bin/env python3
"""Tests for pause-resume-guard.py -- qodo-code-review findings on PR #143:

  - "Failed alerts never retry" (High, x2): alarm-sent state was persisted BEFORE
    send_alert() was even called, and its return value was discarded -- a failed Outlook
    delivery permanently suppressed every later retry of a still-active alarm.
  - "send_alert() missing notion logging" (Medium/rule violation): a failed retry wasn't
    logged anywhere for follow-up/auditability.
  - "Pending resume triggers alarm" (Medium): a resume task registered but not yet due
    was indistinguishable from no resume task at all, causing a false alarm.

Run: python test-pause-resume-guard.py
"""
import importlib.util
import json
import os
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "pause_resume_guard", os.path.join(HERE, "pause-resume-guard.py"))
prg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prg)


def _epoch_ms(dt):
    return int(dt.timestamp() * 1000)


def _recurring_tasks(n, enabled):
    return [{"id": f"task-{i}", "cronExpression": "0 6 * * *", "enabled": enabled} for i in range(n)]


class _FakeProc:
    def __init__(self, returncode, stderr=""):
        self.returncode = returncode
        self.stderr = stderr
        self.stdout = ""


# --- analyze_fleet: pending-vs-overdue resume ------------------------------------------

def test_pending_future_resume_does_not_report_overdue_unit():
    tasks = _recurring_tasks(10, enabled=False)  # near-zero ratio
    future = _epoch_ms(datetime.now(timezone.utc) + timedelta(hours=6))
    tasks.append({"id": "ora-routine-pause-resume-08-22", "fireAt": future, "cronExpression": None})
    r = prg.analyze_fleet("cc", tasks)
    assert r["overdueResume"] is None, f"a future resume must not read as overdue: {r}"
    assert r["hasResumeTask"] is True, "a pending (not-yet-due) resume task must still be reported as existing"
    print("  PASS test_pending_future_resume_does_not_report_overdue_unit")


def test_no_resume_task_at_all_unit():
    tasks = _recurring_tasks(10, enabled=False)
    r = prg.analyze_fleet("cc", tasks)
    assert r["overdueResume"] is None
    assert r["hasResumeTask"] is False
    print("  PASS test_no_resume_task_at_all_unit")


def test_overdue_resume_still_reported_unit():
    tasks = _recurring_tasks(10, enabled=False)
    past = _epoch_ms(datetime.now(timezone.utc) - timedelta(hours=1))
    tasks.append({"id": "ora-routine-pause-resume-08-22", "fireAt": past, "cronExpression": None})
    r = prg.analyze_fleet("cc", tasks)
    assert r["overdueResume"] is not None
    assert r["overdueResume"]["minutesOverdue"] >= 59
    assert r["hasResumeTask"] is True
    print("  PASS test_overdue_resume_still_reported_unit")


def test_pending_resume_does_not_trip_the_no_resume_alarm_branch_e2e_state_unit():
    """The actual caller-level bug: with a PENDING (future) resume, near_zero AND
    prev_near_zero=True used to still trip the 'no pending/overdue resume exists' alarm,
    because the caller only checked `not overdueResume`, not whether a resume existed."""
    tasks = _recurring_tasks(10, enabled=False)
    future = _epoch_ms(datetime.now(timezone.utc) + timedelta(hours=6))
    tasks.append({"id": "ora-routine-pause-resume-08-22", "fireAt": future, "cronExpression": None})
    r = prg.analyze_fleet("cc", tasks)
    near_zero = r["ratio"] <= 0.10
    prev_near_zero = True  # simulate: this is the fleet's second consecutive near-zero check
    trip = (near_zero and not r["overdueResume"] and not r["hasResumeTask"] and prev_near_zero)
    assert trip is False, "a pending future resume must suppress the 'no resume exists' alarm"
    print("  PASS test_pending_resume_does_not_trip_the_no_resume_alarm_branch_e2e_state_unit")


# --- retire-pending resurrection (2026-08-22, register-scheduled-task v2.14) -----------

def _write_rp(tmpdir, payload):
    p = os.path.join(tmpdir, "retire-pending.json")
    with open(p, "w", encoding="utf-8") as f:
        f.write(payload if isinstance(payload, str) else json.dumps(payload))
    return p


def test_retire_pending_enabled_is_a_finding_unit():
    """THE case this check exists for: a bulk resume flips a ratified-but-unexecuted
    retirement back on, which is indistinguishable from a healthy task to every other
    detector here."""
    tmp = tempfile.mkdtemp(prefix="prg-rp-")
    p = _write_rp(tmp, {"pending": [{"fleet": "lams", "id": "ora-passed-deal-tracker",
                                     "ratified": "2026-08-22", "reason": "duplicate of the CC copy",
                                     "executeFrom": "native on-device Cowork session"}]})
    tasks = {"lams": [{"id": "ora-passed-deal-tracker", "cronExpression": "30 6 15 * *", "enabled": True}]}
    found = prg.find_resurrected(tasks, path=p)
    assert len(found) == 1, f"an enabled retire-pending id must be a finding: {found}"
    assert found[0]["id"] == "ora-passed-deal-tracker"
    assert found[0]["executeFrom"] == "native on-device Cowork session"
    print("  PASS test_retire_pending_enabled_is_a_finding_unit")


def test_retire_pending_disabled_is_not_a_finding_unit():
    """Still awaiting execution, exactly as filed -- the normal state, never an alarm."""
    tmp = tempfile.mkdtemp(prefix="prg-rp-")
    p = _write_rp(tmp, {"pending": [{"fleet": "lams", "id": "ora-passed-deal-tracker"}]})
    tasks = {"lams": [{"id": "ora-passed-deal-tracker", "cronExpression": "30 6 15 * *", "enabled": False}]}
    assert prg.find_resurrected(tasks, path=p) == []
    print("  PASS test_retire_pending_disabled_is_not_a_finding_unit")


def test_retire_pending_executed_retirement_is_not_a_finding_unit():
    """Id absent from the registry = the retirement executed. The register entry is now
    stale and should be removed by the executing session, but a stale entry must not
    alarm -- alarming here would punish a completed retirement."""
    tmp = tempfile.mkdtemp(prefix="prg-rp-")
    p = _write_rp(tmp, {"pending": [{"fleet": "lams", "id": "ora-passed-deal-tracker"}]})
    assert prg.find_resurrected({"lams": [{"id": "something-else", "enabled": True}]}, path=p) == []
    print("  PASS test_retire_pending_executed_retirement_is_not_a_finding_unit")


def test_retire_pending_only_matches_its_named_fleet_unit():
    """A same-id cross-fleet pair is the whole reason these retirements exist. The CC copy
    of ora-passed-deal-tracker is CANONICAL and enabled on purpose -- matching on id alone
    would alarm on it forever."""
    tmp = tempfile.mkdtemp(prefix="prg-rp-")
    p = _write_rp(tmp, {"pending": [{"fleet": "lams", "id": "ora-passed-deal-tracker"}]})
    tasks = {"cc": [{"id": "ora-passed-deal-tracker", "cronExpression": "30 6 15 * *", "enabled": True}],
             "lams": [{"id": "ora-passed-deal-tracker", "cronExpression": "30 6 15 * *", "enabled": False}]}
    assert prg.find_resurrected(tasks, path=p) == [], "the canonical CC copy must never be flagged"
    print("  PASS test_retire_pending_only_matches_its_named_fleet_unit")


def test_retire_pending_missing_or_malformed_register_fails_open_unit():
    """Fail-open by construction: this check shares a process with the fleet-ratio and
    stalled-marker checks and must never be able to crash or false-alarm them."""
    tmp = tempfile.mkdtemp(prefix="prg-rp-")
    tasks = {"lams": [{"id": "ora-passed-deal-tracker", "enabled": True}]}
    assert prg.load_retire_pending(os.path.join(tmp, "does-not-exist.json")) == []
    assert prg.find_resurrected(tasks, path=os.path.join(tmp, "does-not-exist.json")) == []
    assert prg.find_resurrected(tasks, path=_write_rp(tmp, "{not json at all")) == []
    assert prg.find_resurrected(tasks, path=_write_rp(tmp, {"pending": "a string, not a list"})) == []
    # entries missing fleet or id are skipped, not guessed at
    assert prg.load_retire_pending(_write_rp(tmp, {"pending": [{"id": "no-fleet"}, {"fleet": "lams"}]})) == []
    print("  PASS test_retire_pending_missing_or_malformed_register_fails_open_unit")


def test_retire_pending_alarm_state_is_namespaced_not_a_top_level_fleet_key_unit():
    """Regression guard for the alarm-key routing: a 'retire-pending:<fleet>:<id>' alarm
    must persist under _retirePending, NOT as a top-level fleet key (which is what the
    marker check's bare else-branch would have done, and would have collided with the
    real fleet ratio state)."""
    tmp = tempfile.mkdtemp(prefix="prg-rp-e2e-")
    p = _write_rp(tmp, {"pending": [{"fleet": "cc", "id": "ora-doomed-task", "ratified": "2026-08-22"}]})
    tasks = {"cc": _recurring_tasks(10, enabled=True) + [
        {"id": "ora-doomed-task", "cronExpression": "0 6 * * *", "enabled": True}]}

    state1, calls1 = _run_main_with_fixtures(tasks, tmp, send_alert_result=True, retire_pending_path=p)
    assert calls1 == 1, "a newly-resurrected retire-pending id must alarm"
    assert state1["_retirePending"]["cc:ora-doomed-task"]["alarmed"] is True
    assert "retire-pending:cc:ora-doomed-task" not in state1, "must not leak a top-level key"

    # Run 2: unchanged and already delivered -- must not re-email.
    _, calls2 = _run_main_with_fixtures(tasks, tmp, send_alert_result=True, retire_pending_path=p)
    assert calls2 == 0, "an already-delivered retire-pending alarm must not re-send"

    # Run 3: the id is disabled again -- the alarm state clears so a future flip re-alarms.
    tasks["cc"][-1]["enabled"] = False
    state3, calls3 = _run_main_with_fixtures(tasks, tmp, send_alert_result=True, retire_pending_path=p)
    assert calls3 == 0
    assert state3["_retirePending"]["cc:ora-doomed-task"]["alarmed"] is False
    print("  PASS test_retire_pending_alarm_state_is_namespaced_not_a_top_level_fleet_key_unit")


# --- send_alert: retry, return value, Notion logging on failure ------------------------

def test_send_alert_retries_once_on_com_failure_then_succeeds_unit():
    calls = []

    def fake_run(args, **kw):
        calls.append(args)
        return _FakeProc(2) if len(calls) == 1 else _FakeProc(0)

    prg.subprocess.run = fake_run
    ok = prg.send_alert("subject", "body", identifier="test")
    assert ok is True
    assert len(calls) == 2, f"expected exactly one retry (2 calls total), got {len(calls)}"
    print("  PASS test_send_alert_retries_once_on_com_failure_then_succeeds_unit")


def test_send_alert_returns_false_on_persistent_failure_and_does_not_raise_unit():
    prg.subprocess.run = lambda args, **kw: _FakeProc(1, stderr="boom")
    notion_calls = []
    prg._log_send_failure_to_notion = lambda subject, identifier, proc: notion_calls.append(
        (subject, identifier, proc.returncode)) or True
    ok = prg.send_alert("subject", "body", identifier="cc; marker:foo")
    assert ok is False
    assert len(notion_calls) == 1, "a failed send must attempt to log to Notion exactly once"
    assert notion_calls[0][1] == "cc; marker:foo"
    print("  PASS test_send_alert_returns_false_on_persistent_failure_and_does_not_raise_unit")


def test_notion_logging_failure_itself_never_raises_unit():
    """Best-effort by construction: if Notion is ALSO unreachable, send_alert must still
    return cleanly rather than propagate a second failure on top of the first."""
    prg.subprocess.run = lambda args, **kw: _FakeProc(1, stderr="boom")

    def _broken_token():
        raise RuntimeError("NOTION_TOKEN not found")
    prg._load_notion_token = _broken_token
    ok = prg.send_alert("subject", "body", identifier="test")
    assert ok is False  # the ORIGINAL failure still reports correctly
    print("  PASS test_notion_logging_failure_itself_never_raises_unit")


# --- main(): the actual end-to-end regression for the "never retry" bug ----------------

def _run_main_with_fixtures(tasks_by_fleet, state_dir, send_alert_result, stalled=None,
                            retire_pending_path=None):
    """Monkeypatch fleet_status/task_progress_marker/send_alert/save path, then call
    main() once via a real argv, and return the resulting persisted state dict.

    retire_pending_path defaults to a path that does not exist, so a test that isn't
    about the retire-pending check never reads the LIVE register (which would make these
    tests depend on real fleet state)."""
    prg.fleet_status.discover_registries = lambda: [(f, f"{f}.json") for f in tasks_by_fleet]
    prg.fleet_status.load = lambda path: (tasks_by_fleet[path[:-5]], None)
    prg.task_progress_marker.find_stalled = lambda grace_minutes: (stalled or [])
    prg.STATE_PATH = os.path.join(state_dir, "state.json")
    prg.RETIRE_PENDING_PATH = retire_pending_path or os.path.join(state_dir, "no-retire-pending.json")
    # main() observes the LIVE registries into _state/fleet-pause-windows.json (2026-09-12);
    # a unit test must never write live state.
    prg.capture_pause_windows = lambda: {"held": {}, "errors": []}

    sent = {"calls": 0}

    def fake_send_alert(subject, body, identifier=None):
        sent["calls"] += 1
        return send_alert_result

    prg.send_alert = fake_send_alert
    old_argv = sys.argv
    sys.argv = ["pause-resume-guard.py", "--json"]
    try:
        prg.main()
    finally:
        sys.argv = old_argv
    return prg.load_state(), sent["calls"]


def test_failed_delivery_does_not_persist_alarmed_and_retries_next_run_unit():
    """THE core regression test. Two runs: first run trips a new alarm and delivery FAILS
    -- 'alarmed' must stay unset so the second run retries the SAME alarm rather than
    silently suppressing it as 'already alarmed'."""
    tmp = tempfile.mkdtemp(prefix="prg-e2e-")
    tasks = {"cc": _recurring_tasks(10, enabled=False)}  # near-zero, no resume task

    # Run 1: near_zero flips True this run -- prev_near_zero is False (fresh state), so
    # the "two consecutive checks" branch does NOT trip yet. Seed prevNearZero=True by
    # writing state by hand first (simulating "this is the second check").
    prg.STATE_PATH = os.path.join(tmp, "state.json")
    prg.save_state({"cc": {"nearZero": True, "lastChecked": "x", "alarmed": False}})

    state1, calls1 = _run_main_with_fixtures(tasks, tmp, send_alert_result=False)
    assert calls1 == 1, "a new trip must attempt exactly one send"
    assert state1.get("cc", {}).get("alarmed") is not True, \
        "a FAILED delivery must not be persisted as alarmed=True (this is the bug)"

    # Run 2: same conditions, delivery now succeeds -- must attempt to send AGAIN (proving
    # run 1 did not silently suppress it), and NOW persist alarmed=True.
    state2, calls2 = _run_main_with_fixtures(tasks, tmp, send_alert_result=True)
    assert calls2 == 1, "the still-unresolved alarm from run 1 must be retried, not suppressed"
    assert state2["cc"]["alarmed"] is True, "a SUCCESSFUL delivery must be persisted as alarmed=True"

    # Run 3: alarm now marked delivered -- must NOT re-send.
    state3, calls3 = _run_main_with_fixtures(tasks, tmp, send_alert_result=True)
    assert calls3 == 0, "an already-delivered alarm must not re-send on the next run"
    print("  PASS test_failed_delivery_does_not_persist_alarmed_and_retries_next_run_unit")


def main():
    test_pending_future_resume_does_not_report_overdue_unit()
    test_no_resume_task_at_all_unit()
    test_overdue_resume_still_reported_unit()
    test_pending_resume_does_not_trip_the_no_resume_alarm_branch_e2e_state_unit()
    test_send_alert_retries_once_on_com_failure_then_succeeds_unit()
    test_send_alert_returns_false_on_persistent_failure_and_does_not_raise_unit()
    test_notion_logging_failure_itself_never_raises_unit()
    test_failed_delivery_does_not_persist_alarmed_and_retries_next_run_unit()
    test_retire_pending_enabled_is_a_finding_unit()
    test_retire_pending_disabled_is_not_a_finding_unit()
    test_retire_pending_executed_retirement_is_not_a_finding_unit()
    test_retire_pending_only_matches_its_named_fleet_unit()
    test_retire_pending_missing_or_malformed_register_fails_open_unit()
    test_retire_pending_alarm_state_is_namespaced_not_a_top_level_fleet_key_unit()
    test_incomplete_resume_oi273_shape_is_a_finding_unit()
    test_complete_resume_is_not_a_finding_unit()
    test_resume_within_grace_is_not_yet_judged_unit()
    test_old_resume_outside_lookback_is_ignored_unit()
    test_non_resume_one_time_task_is_ignored_unit()
    test_retire_pending_ids_are_excluded_from_incomplete_resume_unit()
    test_incomplete_resume_alarms_once_and_clears_unit()
    print("ALL PAUSE-RESUME-GUARD TESTS PASS")


# --- incomplete resume (OI-273, 2026-09-12) ------------------------------------------
# The 2026-09-11 resume fired, re-enabled 6 of 38 ids, and blocked on an unanswered
# permission prompt; list_task_runs said `succeeded`. The fleet-ratio check (<=10% enabled)
# could not see it -- 6/38 is 16% -- and the stalled-marker check only fires after the
# marker goes stale. This check reads what the resume ASKED for against live `enabled`.

def _resume_skill(tmp, ids, name="resume.md", verb="Re-enable exactly these ids:"):
    p = os.path.join(tmp, name)
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(verb + "\n" + "\n".join("%d. %s" % (n + 1, i) for n, i in enumerate(ids)))
    return p


def _fired(minutes_ago):
    return (datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def _fleet_with_resume(tmp, enabled_ids, all_ids, fired_minutes_ago, verb="Re-enable exactly these ids:"):
    rec = [{"id": i, "cronExpression": "0 6 * * *", "enabled": i in enabled_ids} for i in all_ids]
    rec.append({"id": "ora-routine-pause-resume-x", "fireAt": 1, "enabled": False,
                "lastRunAt": _fired(fired_minutes_ago),
                "filePath": _resume_skill(tmp, all_ids, verb=verb)})
    return rec


def test_incomplete_resume_oi273_shape_is_a_finding_unit():
    tmp = tempfile.mkdtemp(prefix="prg-ir-")
    ids = [f"task-{i}" for i in range(38)]
    tasks = {"cc": _fleet_with_resume(tmp, set(ids[:6]), ids, fired_minutes_ago=90)}
    out = prg.find_incomplete_resumes(tasks, retire_pending_path=os.path.join(tmp, "none.json"))
    assert len(out) == 1, out
    assert out[0]["taskId"] == "ora-routine-pause-resume-x"
    assert out[0]["disabled"] == ids[6:], out[0]
    assert out[0]["listed"] == 38
    print("  PASS test_incomplete_resume_oi273_shape_is_a_finding_unit")


def test_complete_resume_is_not_a_finding_unit():
    tmp = tempfile.mkdtemp(prefix="prg-ir-")
    ids = [f"task-{i}" for i in range(10)]
    tasks = {"cc": _fleet_with_resume(tmp, set(ids), ids, fired_minutes_ago=90)}
    assert prg.find_incomplete_resumes(tasks, retire_pending_path=os.path.join(tmp, "none.json")) == []
    print("  PASS test_complete_resume_is_not_a_finding_unit")


def test_resume_within_grace_is_not_yet_judged_unit():
    tmp = tempfile.mkdtemp(prefix="prg-ir-")
    ids = [f"task-{i}" for i in range(10)]
    tasks = {"cc": _fleet_with_resume(tmp, set(), ids, fired_minutes_ago=5)}
    assert prg.find_incomplete_resumes(tasks, retire_pending_path=os.path.join(tmp, "none.json")) == []
    print("  PASS test_resume_within_grace_is_not_yet_judged_unit")


def test_old_resume_outside_lookback_is_ignored_unit():
    tmp = tempfile.mkdtemp(prefix="prg-ir-")
    ids = [f"task-{i}" for i in range(10)]
    tasks = {"cc": _fleet_with_resume(tmp, set(), ids, fired_minutes_ago=60 * 24 * 10)}
    assert prg.find_incomplete_resumes(tasks, retire_pending_path=os.path.join(tmp, "none.json")) == []
    print("  PASS test_old_resume_outside_lookback_is_ignored_unit")


def test_non_resume_one_time_task_is_ignored_unit():
    # an audit that lists disabled ids but never re-enables anything is not a resume
    tmp = tempfile.mkdtemp(prefix="prg-ir-")
    ids = [f"task-{i}" for i in range(10)]
    tasks = {"cc": _fleet_with_resume(tmp, set(), ids, fired_minutes_ago=90,
                                      verb="Audit report covering these ids:")}
    assert prg.find_incomplete_resumes(tasks, retire_pending_path=os.path.join(tmp, "none.json")) == []
    print("  PASS test_non_resume_one_time_task_is_ignored_unit")


def test_retire_pending_ids_are_excluded_from_incomplete_resume_unit():
    tmp = tempfile.mkdtemp(prefix="prg-ir-")
    ids = [f"task-{i}" for i in range(10)]
    tasks = {"cc": _fleet_with_resume(tmp, set(ids[:9]), ids, fired_minutes_ago=90)}
    rp = _write_rp(tmp, {"pending": [{"fleet": "cc", "id": "task-9"}]})
    assert prg.find_incomplete_resumes(tasks, retire_pending_path=rp) == []
    print("  PASS test_retire_pending_ids_are_excluded_from_incomplete_resume_unit")


def test_incomplete_resume_alarms_once_and_clears_unit():
    tmp = tempfile.mkdtemp(prefix="prg-ir-e2e-")
    ids = [f"task-{i}" for i in range(38)]
    tasks = {"cc": _fleet_with_resume(tmp, set(ids[:6]), ids, fired_minutes_ago=90)}
    state1, calls1 = _run_main_with_fixtures(tasks, tmp, send_alert_result=True)
    assert calls1 == 1, "a partially-completed resume must alarm"
    assert state1["_incompleteResume"]["cc:ora-routine-pause-resume-x"]["alarmed"] is True
    _, calls2 = _run_main_with_fixtures(tasks, tmp, send_alert_result=True)
    assert calls2 == 0, "an already-delivered incomplete-resume alarm must not re-send"
    for t in tasks["cc"]:
        if t.get("cronExpression"):
            t["enabled"] = True
    state3, calls3 = _run_main_with_fixtures(tasks, tmp, send_alert_result=True)
    assert calls3 == 0
    assert state3["_incompleteResume"]["cc:ora-routine-pause-resume-x"]["alarmed"] is False
    print("  PASS test_incomplete_resume_alarms_once_and_clears_unit")


if __name__ == "__main__":
    main()
