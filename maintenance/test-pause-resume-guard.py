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
import contextlib
import importlib.util
import io
import json
import os
import sys
import tempfile
import time
from datetime import date, datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "pause_resume_guard", os.path.join(HERE, "pause-resume-guard.py"))
prg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prg)
_REAL_SEND_ALERT = prg.send_alert


def _refuse_real_send(*a, **k):
    raise RuntimeError("a test reached the REAL subprocess.run (PowerShell / Outlook send) -- stub it")


def _refuse_network(*a, **k):
    raise RuntimeError("a test reached the network (urlopen -> Notion API) -- stub it")


# Safety net (2026-11-05): no test may ever reach PowerShell/Outlook or the Notion API. A test
# that exercises send_alert installs its own subprocess.run fake; anything else hits these.
prg.subprocess.run = _refuse_real_send
prg.urllib.request.urlopen = _refuse_network


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
                            retire_pending_path=None, held_off_path=None, held_by_pause=None,
                            sent_log=None, json_output=True, send_runner=None):
    """Monkeypatch fleet_status/task_progress_marker/send_alert/save path, then call
    main() once via a real argv, and return the resulting persisted state dict.

    retire_pending_path defaults to a path that does not exist, so a test that isn't
    about the retire-pending check never reads the LIVE register (which would make these
    tests depend on real fleet state). held_off_path likewise defaults to a non-existent
    file in state_dir (= no holds), so no test reads the LIVE _state/held-off.json.
    held_by_pause is what the stubbed capture_pause_windows() reports as held by a pending
    resume. sent_log, if given, receives one {"subject", "body", "identifier"} dict per send
    attempt. json_output=False exercises the text summary -- the path the native task runs.
    send_runner, if given, runs the REAL send_alert with subprocess.run replaced by send_runner
    (and Notion failure logging stubbed): the only way a test reaches send_alert's _sendLog
    bookkeeping through main(). The safety net is reinstalled afterwards."""
    prg.fleet_status.discover_registries = lambda: [(f, f"{f}.json") for f in tasks_by_fleet]
    prg.fleet_status.load = lambda path: (tasks_by_fleet[path[:-5]], None)
    prg.task_progress_marker.find_stalled = lambda grace_minutes: (stalled or [])
    prg.STATE_PATH = os.path.join(state_dir, "state.json")
    prg.RETIRE_PENDING_PATH = retire_pending_path or os.path.join(state_dir, "no-retire-pending.json")
    prg.HELD_OFF_PATH = held_off_path or os.path.join(state_dir, "no-held-off.json")
    # main() observes the LIVE registries into _state/fleet-pause-windows.json (2026-09-12);
    # a unit test must never write live state.
    prg.capture_pause_windows = lambda: {"held": {f: list(ids) for f, ids in (held_by_pause or {}).items()},
                                         "errors": []}

    sent = {"calls": 0}

    def fake_send_alert(subject, body, identifier=None, **kwargs):
        sent["calls"] += 1
        if sent_log is not None:
            sent_log.append({"subject": subject, "body": body, "identifier": identifier})
        return send_alert_result

    if send_runner is None:
        prg.send_alert = fake_send_alert
    else:
        prg.send_alert = _REAL_SEND_ALERT
        prg.subprocess.run = send_runner
        prg._log_send_failure_to_notion = lambda subject, identifier, proc: True
    old_argv = sys.argv
    sys.argv = ["pause-resume-guard.py"] + (["--json"] if json_output else [])
    try:
        prg.main()
    finally:
        sys.argv = old_argv
        # restore the real send_alert so a later direct send_alert test never gets this fake
        # (safe: the module-level net still refuses the real subprocess.run)
        prg.send_alert = _REAL_SEND_ALERT
        if send_runner is not None:
            prg.subprocess.run = _refuse_real_send
    return prg.load_state(), sent["calls"]


def test_failed_delivery_does_not_persist_alarmed_and_retries_next_run_unit():
    """THE core regression test. Two runs: first run trips a new alarm and delivery FAILS
    -- 'alarmed' must stay unset so the second run retries the SAME alarm rather than
    silently suppressing it as 'already alarmed'."""
    tmp = tempfile.mkdtemp(prefix="prg-e2e-")
    tasks = {"cc": _recurring_tasks(10, enabled=False)}  # near-zero, no resume task
    # 2026-11-05: these 10 disabled recurring tasks would also be STRANDED, and that digest
    # would ride in the same email -- making every `calls == 1` below satisfiable by the
    # digest alone. Exact-id holds keep this test about the fleet-ratio alarm only (a "*"
    # hold would not do: an active "*" now also holds the fleet-ratio alarm under test).
    held = _hold_exact(tmp, "cc", [t["id"] for t in tasks["cc"]])

    # Run 1: near_zero flips True this run -- prev_near_zero is False (fresh state), so
    # the "two consecutive checks" branch does NOT trip yet. Seed prevNearZero=True by
    # writing state by hand first (simulating "this is the second check").
    prg.STATE_PATH = os.path.join(tmp, "state.json")
    prg.save_state({"cc": {"nearZero": True, "lastChecked": "x", "alarmed": False}})

    state1, calls1 = _run_main_with_fixtures(tasks, tmp, send_alert_result=False, held_off_path=held)
    assert calls1 == 1, "a new trip must attempt exactly one send"
    assert state1.get("cc", {}).get("alarmed") is not True, \
        "a FAILED delivery must not be persisted as alarmed=True (this is the bug)"

    # Run 2: same conditions, delivery now succeeds -- must attempt to send AGAIN (proving
    # run 1 did not silently suppress it), and NOW persist alarmed=True.
    state2, calls2 = _run_main_with_fixtures(tasks, tmp, send_alert_result=True, held_off_path=held)
    assert calls2 == 1, "the still-unresolved alarm from run 1 must be retried, not suppressed"
    assert state2["cc"]["alarmed"] is True, "a SUCCESSFUL delivery must be persisted as alarmed=True"

    # Run 3: alarm now marked delivered -- must NOT re-send.
    state3, calls3 = _run_main_with_fixtures(tasks, tmp, send_alert_result=True, held_off_path=held)
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
    test_incomplete_resume_naive_and_epoch_lastrunat_unit()
    test_incomplete_resume_crash_never_kills_main_unit()
    test_load_holds_splits_active_and_expired_by_review_date_unit()
    test_stranded_disabled_recurring_without_intent_is_stranded_unit()
    test_stranded_enabled_recurring_is_not_stranded_unit()
    test_stranded_one_time_task_is_never_stranded_unit()
    test_stranded_retire_pending_is_not_stranded_unit()
    test_stranded_active_exact_hold_is_not_stranded_unit()
    test_stranded_expired_hold_is_stranded_as_hold_expired_unit()
    test_stranded_wildcard_hold_covers_only_its_fleet_unit()
    test_stranded_held_by_pending_resume_is_not_stranded_unit()
    test_stranded_malformed_registers_surface_errors_and_still_strand_unit()
    test_stranded_main_honours_pending_resume_hold_unit()
    test_stranded_digest_first_run_sends_once_and_records_delivery_unit()
    test_stranded_digest_same_set_does_not_resend_unit()
    test_stranded_digest_newly_stranded_id_resends_unit()
    test_stranded_digest_realerts_when_last_alert_over_7_days_old_unit()
    test_stranded_digest_failed_delivery_keeps_state_and_retries_unit()
    test_stranded_state_clears_when_all_tasks_enabled_unit()
    test_stranded_subject_only_changes_when_digest_is_new_unit()
    test_stranded_digest_reason_content_unit()
    test_stranded_digest_and_incomplete_resume_share_one_email_unit()
    test_stranded_check_crash_never_kills_main_unit()
    test_stranded_text_summary_line_unit()
    test_stranded_0928_replay_unit()
    # 2026-11-05 adversarial REFUTE findings
    test_stranded_digest_build_crash_becomes_check_error_unit()
    test_stranded_reviewer_inputs_never_crash_the_real_path_unit()
    test_stranded_pause_exclusion_requires_a_bounded_resume_unit()
    test_stranded_digest_names_every_new_id_past_the_cap_unit()
    test_stranded_missing_fleet_keeps_its_record_unit()
    test_stranded_flapping_exclusion_sends_once_within_7_days_unit()
    test_stranded_old_format_alerted_ids_are_migrated_unit()
    test_stranded_future_or_unreadable_last_alerted_re_alerts_unit()
    test_stranded_exact_hold_decides_before_the_wildcard_unit()
    test_load_holds_rejects_non_string_fields_unit()
    test_retire_pending_bom_is_read_unit()
    test_save_state_is_atomic_unit()
    test_send_alert_records_every_attempt_in_send_log_unit()
    test_send_log_is_saved_printed_and_in_json_unit()
    test_fleet_wildcard_hold_suppresses_only_the_fleet_ratio_alarm_unit()
    print("ALL PAUSE-RESUME-GUARD TESTS PASS")


def test_incomplete_resume_naive_and_epoch_lastrunat_unit():
    """Review finding: a naive ISO lastRunAt raised TypeError (would kill main()), and an
    epoch-ms lastRunAt was silently skipped. Both must be judged."""
    ids = [f"task-{i}" for i in range(10)]
    ninety_ago = datetime.now(timezone.utc) - timedelta(minutes=90)
    for variant in (ninety_ago.strftime("%Y-%m-%dT%H:%M:%S"), int(ninety_ago.timestamp() * 1000)):
        tmp = tempfile.mkdtemp(prefix="prg-ir-v-")
        tasks = {"cc": _fleet_with_resume(tmp, set(), ids, fired_minutes_ago=90)}
        tasks["cc"][-1]["lastRunAt"] = variant
        out = prg.find_incomplete_resumes(tasks, retire_pending_path=os.path.join(tmp, "none.json"))
        assert len(out) == 1 and len(out[0]["disabled"]) == 10, (variant, out)
    print("  PASS test_incomplete_resume_naive_and_epoch_lastrunat_unit")


def test_incomplete_resume_crash_never_kills_main_unit():
    tmp = tempfile.mkdtemp(prefix="prg-ir-crash-")
    original = prg.find_incomplete_resumes

    def boom(*a, **k):
        raise RuntimeError("synthetic")
    prg.find_incomplete_resumes = boom
    try:
        state, calls = _run_main_with_fixtures({"cc": _recurring_tasks(10, enabled=True)}, tmp,
                                               send_alert_result=True)
        _, calls_again = _run_main_with_fixtures({"cc": _recurring_tasks(10, enabled=True)}, tmp,
                                                 send_alert_result=True)
    finally:
        prg.find_incomplete_resumes = original
    assert calls == 1, "a crashed check must surface as an alarm, not kill main() or vanish"
    assert calls_again == 0, "a persisting check error must not re-email every run"
    state_ok, calls_ok = _run_main_with_fixtures({"cc": _recurring_tasks(10, enabled=True)}, tmp,
                                                 send_alert_result=True)
    assert calls_ok == 0
    assert state_ok["_incompleteResume"]["check-error"]["alarmed"] is False, \
        "a recovered check must clear its error alarm so a future failure re-alarms"
    print("  PASS test_incomplete_resume_crash_never_kills_main_unit")


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
    # 2026-11-05: the 32 still-disabled ids are also STRANDED; exact-id holds keep calls1 == 1
    # measuring the incomplete-resume alarm alone. The shared-email case is covered by
    # test_stranded_digest_and_incomplete_resume_share_one_email_unit.
    held = _hold_exact(tmp, "cc", ids)
    state1, calls1 = _run_main_with_fixtures(tasks, tmp, send_alert_result=True, held_off_path=held)
    assert calls1 == 1, "a partially-completed resume must alarm"
    assert state1["_incompleteResume"]["cc:ora-routine-pause-resume-x"]["alarmed"] is True
    _, calls2 = _run_main_with_fixtures(tasks, tmp, send_alert_result=True, held_off_path=held)
    assert calls2 == 0, "an already-delivered incomplete-resume alarm must not re-send"
    for t in tasks["cc"]:
        if t.get("cronExpression"):
            t["enabled"] = True
    state3, calls3 = _run_main_with_fixtures(tasks, tmp, send_alert_result=True, held_off_path=held)
    assert calls3 == 0
    assert state3["_incompleteResume"]["cc:ora-routine-pause-resume-x"]["alarmed"] is False
    print("  PASS test_incomplete_resume_alarms_once_and_clears_unit")


# --- stranded tasks (2026-11-05) -------------------------------------------------------
# 2026-09-28: ora-routine-pause-resume-09-28 stalled with 35 recurring tasks disabled. The
# incomplete-resume check saw it but its alarm was never delivered; the same day a cleanup
# pass archived the resume's folder, its filePath stopped resolving, find_incomplete_resumes
# `continue`d past it, and 24 of those tasks stayed dark 32 days. Every check above judges
# an EVENT; this one judges STATE -- a recurring task that is disabled with no recorded intent.

TODAY = date(2026, 11, 5)
STRANDED_SUBJECT = "[ORA] Fleet pause/resume guard - ALARM (stranded tasks: %d, week %d)"
PLAIN_SUBJECT = "[ORA] Fleet pause/resume guard - ALARM"


def _rec(task_id, enabled=False):
    return {"id": task_id, "cronExpression": "0 6 * * *", "enabled": enabled}


def _hold(fleet, task_id, review_by, reason="kept off on purpose"):
    return {"fleet": fleet, "id": task_id, "reason": reason, "ruledBy": "Gabriel",
            "ruledOn": "2026-11-01", "reviewBy": review_by}


def _write_holds(tmpdir, payload, name="held-off.json"):
    p = os.path.join(tmpdir, name)
    with open(p, "w", encoding="utf-8") as f:
        f.write(payload if isinstance(payload, str) else json.dumps(payload))
    return p


def _hold_exact(tmpdir, fleet, task_ids):
    """Far-future EXACT-id holds: keep a test about some OTHER check from also raising the
    stranded digest its disabled fixtures would produce. Not "*": an active "*" hold also
    holds the fleet's fleet-ratio alarm (2026-11-05)."""
    return _write_holds(tmpdir, {"holds": [_hold(fleet, i, "2999-12-31", reason="test isolation")
                                           for i in task_ids]}, name="held-off-isolation.json")


def _resume_task(fire_in, enabled=True, task_id="ora-routine-pause-resume-11-07"):
    """A one-time task firing `fire_in` from now -- the pause holder D2 bounds."""
    return {"id": task_id, "cronExpression": None, "enabled": enabled,
            "fireAt": _epoch_ms(datetime.now(timezone.utc) + fire_in)}


def _proc(rc, stderr="", stdout=""):
    p = _FakeProc(rc, stderr=stderr)
    p.stdout = stdout
    return p


def _stranded(tasks, tmp, held_by_pause=None, holds=None, rp=None, today=TODAY):
    """find_stranded against temp registers only -- never the live _state/ files."""
    holds_path = (_write_holds(tmp, holds) if holds is not None
                  else os.path.join(tmp, "no-held-off.json"))
    rp_path = _write_rp(tmp, rp) if rp is not None else os.path.join(tmp, "no-retire-pending.json")
    return prg.find_stranded(tasks, held_by_pause=held_by_pause, retire_pending_path=rp_path,
                             holds_path=holds_path, today=today)


def _with_live(*dark_ids):
    """A healthy-ratio CC fleet (so no fleet-ratio alarm) plus the given disabled recurring ids."""
    return {"cc": _recurring_tasks(10, enabled=True) + [_rec(i) for i in dark_ids]}


def _digest_reason(body):
    return body.split("Source: stranded:digest\nReason: ", 1)[1].split("\n\n", 1)[0]


def test_load_holds_splits_active_and_expired_by_review_date_unit():
    tmp = tempfile.mkdtemp(prefix="prg-st-")
    p = _write_holds(tmp, {"holds": [_hold("cc", "ora-a", "2026-11-05"), _hold("cc", "ora-b", "2026-11-04"),
                                     _hold("lams", "*", "2026-12-31")]})
    active, expired, errors = prg.load_holds(p, today=TODAY)
    assert errors == [], errors
    # active THROUGH its reviewBy date (UTC): reviewBy == today still holds
    assert sorted((h["fleet"], h["id"]) for h in active) == [("cc", "ora-a"), ("lams", "*")], active
    assert [(h["fleet"], h["id"], h["reviewBy"]) for h in expired] == [("cc", "ora-b", "2026-11-04")], expired
    assert prg.load_holds(os.path.join(tmp, "absent.json"), today=TODAY) == ([], [], []), \
        "an absent register means no holds, and is not an error"
    # PowerShell 5.1 writes UTF-8 WITH a BOM; that is not a malformed register
    bom = os.path.join(tmp, "bom.json")
    with open(bom, "w", encoding="utf-8-sig") as f:
        json.dump({"holds": [_hold("cc", "ora-a", "2026-12-31")]}, f)
    active, _, errors = prg.load_holds(bom, today=TODAY)
    assert errors == [] and [h["id"] for h in active] == ["ora-a"], (active, errors)
    print("  PASS test_load_holds_splits_active_and_expired_by_review_date_unit")


def test_stranded_disabled_recurring_without_intent_is_stranded_unit():
    tmp = tempfile.mkdtemp(prefix="prg-st-")
    out, errors = _stranded({"cc": [_rec("ora-weekly-report")]}, tmp)
    assert errors == [], errors
    assert out == [{"fleet": "cc", "id": "ora-weekly-report", "reason": "no-recorded-intent",
                    "holdReason": None, "reviewBy": None}], out
    print("  PASS test_stranded_disabled_recurring_without_intent_is_stranded_unit")


def test_stranded_enabled_recurring_is_not_stranded_unit():
    tmp = tempfile.mkdtemp(prefix="prg-st-")
    out, _ = _stranded({"cc": [_rec("ora-weekly-report", enabled=True)]}, tmp)
    assert out == [], out
    print("  PASS test_stranded_enabled_recurring_is_not_stranded_unit")


def test_stranded_one_time_task_is_never_stranded_unit():
    """A fired or expired one-time task is disabled by design -- in both registry shapes."""
    tmp = tempfile.mkdtemp(prefix="prg-st-")
    fired = _epoch_ms(datetime.now(timezone.utc) - timedelta(days=5))
    tasks = {"cc": [{"id": "ora-routine-pause-resume-09-28", "cronExpression": None, "fireAt": fired,
                     "enabled": False},
                    {"id": "ora-legacy-one-shot", "cronExpression": str(fired), "enabled": False}]}
    out, _ = _stranded(tasks, tmp)
    assert out == [], out
    print("  PASS test_stranded_one_time_task_is_never_stranded_unit")


def test_stranded_retire_pending_is_not_stranded_unit():
    tmp = tempfile.mkdtemp(prefix="prg-st-")
    rp = {"pending": [{"fleet": "lams", "id": "ora-passed-deal-tracker", "ratified": "2026-08-22"}]}
    tasks = {"lams": [_rec("ora-passed-deal-tracker"), _rec("ora-other")],
             "cc": [_rec("ora-passed-deal-tracker")]}  # same id on the OTHER fleet: still judged
    out, errors = _stranded(tasks, tmp, rp=rp)
    assert errors == [], errors
    assert [(s["fleet"], s["id"]) for s in out] == [("cc", "ora-passed-deal-tracker"), ("lams", "ora-other")], out
    print("  PASS test_stranded_retire_pending_is_not_stranded_unit")


def test_stranded_active_exact_hold_is_not_stranded_unit():
    tmp = tempfile.mkdtemp(prefix="prg-st-")
    out, errors = _stranded({"cc": [_rec("ora-held"), _rec("ora-neighbour")]}, tmp,
                            holds={"holds": [_hold("cc", "ora-held", "2026-11-05")]})
    assert errors == [], errors
    assert [s["id"] for s in out] == ["ora-neighbour"], "an exact hold covers its own id only: %r" % out
    print("  PASS test_stranded_active_exact_hold_is_not_stranded_unit")


def test_stranded_expired_hold_is_stranded_as_hold_expired_unit():
    tmp = tempfile.mkdtemp(prefix="prg-st-")
    out, errors = _stranded({"cc": [_rec("ora-held")]}, tmp, holds={"holds": [
        _hold("cc", "ora-held", "2026-11-04", reason="vendor contract paused")]})
    assert errors == [], errors
    assert out == [{"fleet": "cc", "id": "ora-held", "reason": "hold-expired",
                    "holdReason": "vendor contract paused", "reviewBy": "2026-11-04"}], out
    print("  PASS test_stranded_expired_hold_is_stranded_as_hold_expired_unit")


def test_stranded_wildcard_hold_covers_only_its_fleet_unit():
    tmp = tempfile.mkdtemp(prefix="prg-st-")
    tasks = {"lams": [_rec("ora-a"), _rec("ora-b")], "cc": [_rec("ora-a")]}
    out, errors = _stranded(tasks, tmp, holds={"holds": [
        _hold("lams", "*", "2099-12-31", reason="LAMS fleet kept dark")]})
    assert errors == [], errors
    assert [(s["fleet"], s["id"]) for s in out] == [("cc", "ora-a")], out
    print("  PASS test_stranded_wildcard_hold_covers_only_its_fleet_unit")


def test_stranded_held_by_pending_resume_is_not_stranded_unit():
    """capture_pause_windows()'s "held" = disabled AND named by a pending, not-yet-fired
    resume: a legitimate pause in progress, honoured while the fleet has a BOUNDED resume (D2).
    Fleet-scoped, like every other exclusion."""
    tmp = tempfile.mkdtemp(prefix="prg-st-")
    tasks = {"cc": [_rec("ora-paused"), _rec("ora-dark"), _resume_task(timedelta(days=2))],
             "lams": [_rec("ora-paused")]}
    out, notes = _stranded(tasks, tmp, held_by_pause={"cc": ["ora-paused"]})
    assert notes == [], notes
    assert [(s["fleet"], s["id"]) for s in out] == [("cc", "ora-dark"), ("lams", "ora-paused")], out
    print("  PASS test_stranded_held_by_pending_resume_is_not_stranded_unit")


def test_stranded_malformed_registers_surface_errors_and_still_strand_unit():
    """The held-off register exists to SUPPRESS alarms, so a broken one must never hide a
    stranded task: it applies no hold, the task stays stranded, the error comes back, and
    nothing raises."""
    tmp = tempfile.mkdtemp(prefix="prg-st-")
    tasks = {"cc": [_rec("ora-a")]}
    for bad in ("{not json", json.dumps([_hold("cc", "ora-a", "2099-12-31")]),
                json.dumps({"holds": "not a list"})):
        out, errors = _stranded(tasks, tmp, holds=bad)
        assert [(s["id"], s["reason"]) for s in out] == [("ora-a", "no-recorded-intent")], (bad, out)
        assert len(errors) == 1 and "held-off" in errors[0], (bad, errors)
    # bad ENTRIES are skipped one at a time, each named; a valid sibling still applies
    out, errors = _stranded({"cc": [_rec("ora-a"), _rec("ora-b")]}, tmp, holds={"holds": [
        {"fleet": "cc", "id": "ora-a", "reason": "no reviewBy at all"},
        _hold("cc", "ora-a", "next tuesday"),
        _hold("cc", "ora-a", "2026-02-30"),
        {"id": "ora-a", "reviewBy": "2099-12-31"},
        _hold("cowork", "ora-a", "2099-12-31"),
        "not an object",
        _hold("cc", "ora-b", "2099-12-31")]})
    assert [s["id"] for s in out] == ["ora-a"], out
    assert len(errors) == 6, errors
    # an unreadable register (here: a directory) is an error string, never an exception
    active, expired, errors = prg.load_holds(tmp, today=TODAY)
    assert (active, expired) == ([], []) and len(errors) == 1, errors
    # a broken retire-pending register surfaces the same way -- its ids would read as stranded
    out, errors = _stranded(tasks, tmp, rp="{not json")
    assert [s["id"] for s in out] == ["ora-a"], out
    assert len(errors) == 1 and "retire-pending" in errors[0], errors
    print("  PASS test_stranded_malformed_registers_surface_errors_and_still_strand_unit")


def test_stranded_main_honours_pending_resume_hold_unit():
    """main() must hand capture_pause_windows()'s "held" to the check: a bounded pause in
    progress is not stranded (exclusions (a) and (b) are exercised through main() by the
    retire-pending and fleet-hold tests)."""
    tmp = tempfile.mkdtemp(prefix="prg-st-e2e-")
    tasks = _with_live("ora-paused")
    tasks["cc"].append(_resume_task(timedelta(days=2)))  # the bounded resume holding it
    state, calls = _run_main_with_fixtures(tasks, tmp, send_alert_result=True,
                                           held_by_pause={"cc": ["ora-paused"]})
    assert calls == 0, "a task held by a pending resume must not raise the digest"
    assert state["_stranded"]["ids"] == [], state["_stranded"]
    print("  PASS test_stranded_main_honours_pending_resume_hold_unit")


def test_stranded_digest_first_run_sends_once_and_records_delivery_unit():
    tmp = tempfile.mkdtemp(prefix="prg-st-e2e-")
    sent = []
    state, calls = _run_main_with_fixtures(_with_live("ora-dark-b", "ora-dark-a"), tmp,
                                           send_alert_result=True, sent_log=sent)
    assert calls == 1, "a newly stranded set must alarm"
    assert sent[0]["identifier"] == "stranded:digest", sent[0]["identifier"]
    assert sent[0]["subject"] == STRANDED_SUBJECT % (2, 1), sent[0]["subject"]
    st = state["_stranded"]
    assert st["ids"] == ["cc:ora-dark-a", "cc:ora-dark-b"], st
    assert st["alertedAt"] == {k: st["lastAlerted"] for k in st["ids"]}, \
        "delivery stamps exactly the ids the digest named: %r" % st
    assert "alertedIds" not in st, st
    assert prg._parse_run_ts(st["lastAlerted"]) is not None, st
    assert sorted(st["firstSeen"]) == st["ids"], st
    assert all(prg._parse_run_ts(v) is not None for v in st["firstSeen"].values()), st
    print("  PASS test_stranded_digest_first_run_sends_once_and_records_delivery_unit")


def test_stranded_digest_same_set_does_not_resend_unit():
    tmp = tempfile.mkdtemp(prefix="prg-st-e2e-")
    tasks = _with_live("ora-dark")
    state1, calls1 = _run_main_with_fixtures(tasks, tmp, send_alert_result=True)
    state2, calls2 = _run_main_with_fixtures(tasks, tmp, send_alert_result=True)
    assert (calls1, calls2) == (1, 0), (calls1, calls2)
    assert state2["_stranded"]["lastAlerted"] == state1["_stranded"]["lastAlerted"]
    assert state2["_stranded"]["firstSeen"] == state1["_stranded"]["firstSeen"], "first-seen survives a quiet run"
    print("  PASS test_stranded_digest_same_set_does_not_resend_unit")


def test_stranded_digest_newly_stranded_id_resends_unit():
    tmp = tempfile.mkdtemp(prefix="prg-st-e2e-")
    tasks = _with_live("ora-dark-a")
    state1, _ = _run_main_with_fixtures(tasks, tmp, send_alert_result=True)
    tasks["cc"].append(_rec("ora-dark-b"))
    sent = []
    state2, calls = _run_main_with_fixtures(tasks, tmp, send_alert_result=True, sent_log=sent)
    assert calls == 1 and sent[0]["identifier"] == "stranded:digest", sent
    assert sent[0]["subject"] == STRANDED_SUBJECT % (2, 1), sent[0]["subject"]
    st = state2["_stranded"]
    assert st["alertedAt"] == {"cc:ora-dark-a": st["lastAlerted"], "cc:ora-dark-b": st["lastAlerted"]}, st
    assert st["firstSeen"]["cc:ora-dark-a"] == state1["_stranded"]["firstSeen"]["cc:ora-dark-a"]
    print("  PASS test_stranded_digest_newly_stranded_id_resends_unit")


def test_stranded_digest_realerts_when_last_alert_over_7_days_old_unit():
    tmp = tempfile.mkdtemp(prefix="prg-st-e2e-")
    tasks = _with_live("ora-dark")
    _run_main_with_fixtures(tasks, tmp, send_alert_result=True)

    def age_record(days):
        state = prg.load_state()
        then = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        state["_stranded"]["lastAlerted"] = then
        state["_stranded"]["firstSeen"] = {k: then for k in state["_stranded"]["ids"]}
        state["_stranded"]["alertedAt"] = {k: then for k in state["_stranded"]["ids"]}
        prg.save_state(state)
        return then

    age_record(6)
    _, calls = _run_main_with_fixtures(tasks, tmp, send_alert_result=True)
    assert calls == 0, "a digest delivered 6 days ago is not due again yet"
    then = age_record(8)
    sent = []
    state, calls = _run_main_with_fixtures(tasks, tmp, send_alert_result=True, sent_log=sent)
    assert calls == 1, "a persisting stranded set must re-alert weekly, not go quiet after one email"
    assert sent[0]["subject"] == STRANDED_SUBJECT % (1, 2), sent[0]["subject"]
    assert state["_stranded"]["lastAlerted"] != then, "delivery advances lastAlerted"
    assert state["_stranded"]["firstSeen"]["cc:ora-dark"] == then, "first-seen survives the re-alert"
    print("  PASS test_stranded_digest_realerts_when_last_alert_over_7_days_old_unit")


def test_stranded_digest_failed_delivery_keeps_state_and_retries_unit():
    tmp = tempfile.mkdtemp(prefix="prg-st-e2e-")
    tasks = _with_live("ora-dark-a")
    state1, calls1 = _run_main_with_fixtures(tasks, tmp, send_alert_result=False)
    assert calls1 == 1
    assert state1["_stranded"]["lastAlerted"] is None and state1["_stranded"]["alertedAt"] == {}, \
        "an UNDELIVERED digest must not be recorded as alerted: %r" % state1["_stranded"]
    assert state1["_stranded"]["ids"] == ["cc:ora-dark-a"], "the set itself is still tracked"
    state2, calls2 = _run_main_with_fixtures(tasks, tmp, send_alert_result=True)
    assert calls2 == 1, "the undelivered digest must be retried on the next run"
    delivered_at = state2["_stranded"]["lastAlerted"]
    assert delivered_at is not None and state2["_stranded"]["alertedAt"] == {"cc:ora-dark-a": delivered_at}
    # a later failed delivery leaves the last DELIVERED record exactly as it was...
    tasks["cc"].append(_rec("ora-dark-b"))
    state3, calls3 = _run_main_with_fixtures(tasks, tmp, send_alert_result=False)
    assert calls3 == 1
    assert state3["_stranded"]["lastAlerted"] == delivered_at, state3["_stranded"]
    assert state3["_stranded"]["alertedAt"] == {"cc:ora-dark-a": delivered_at}, state3["_stranded"]
    # ...and the next run re-sends
    state4, calls4 = _run_main_with_fixtures(tasks, tmp, send_alert_result=True)
    assert calls4 == 1
    assert sorted(state4["_stranded"]["alertedAt"]) == ["cc:ora-dark-a", "cc:ora-dark-b"], state4["_stranded"]
    print("  PASS test_stranded_digest_failed_delivery_keeps_state_and_retries_unit")


def test_stranded_state_clears_when_all_tasks_enabled_unit():
    """Enabling everything clears ids/firstSeen at once; the per-id delivery record survives 7
    days (D6 flap protection), then the record clears completely."""
    tmp = tempfile.mkdtemp(prefix="prg-st-e2e-")
    tasks = _with_live("ora-dark")
    state1, _ = _run_main_with_fixtures(tasks, tmp, send_alert_result=True)
    delivered_at = state1["_stranded"]["lastAlerted"]
    tasks["cc"][-1]["enabled"] = True
    state2, calls2 = _run_main_with_fixtures(tasks, tmp, send_alert_result=True)
    assert calls2 == 0
    assert state2["_stranded"] == {"ids": [], "firstSeen": {}, "alertedAt": {"cc:ora-dark": delivered_at},
                                   "lastAlerted": delivered_at}, state2["_stranded"]
    aged = prg.load_state()
    old = (datetime.now(timezone.utc) - timedelta(days=8)).isoformat()
    aged["_stranded"]["alertedAt"] = {"cc:ora-dark": old}
    aged["_stranded"]["lastAlerted"] = old
    prg.save_state(aged)
    state3, _ = _run_main_with_fixtures(tasks, tmp, send_alert_result=True)
    assert state3["_stranded"] == {"ids": [], "firstSeen": {}, "alertedAt": {}, "lastAlerted": None}, \
        state3["_stranded"]
    tasks["cc"][-1]["enabled"] = False
    _, calls4 = _run_main_with_fixtures(tasks, tmp, send_alert_result=True)
    assert calls4 == 1, "after a full clear, the next stranding is new again"
    print("  PASS test_stranded_state_clears_when_all_tasks_enabled_unit")


def test_stranded_subject_only_changes_when_digest_is_new_unit():
    tmp = tempfile.mkdtemp(prefix="prg-st-e2e-")
    tasks = _with_live("ora-dark")
    first = []
    _run_main_with_fixtures(tasks, tmp, send_alert_result=True, sent_log=first)  # digest delivered
    assert [s["subject"] for s in first] == [STRANDED_SUBJECT % (1, 1)], first
    stall = [{"taskId": "ora-one-shot", "fleet": "cc", "step": 2, "totalSteps": 5,
              "staleMinutes": 99, "note": "blocked"}]
    sent = []
    _, calls = _run_main_with_fixtures(tasks, tmp, send_alert_result=True, stalled=stall, sent_log=sent)
    assert calls == 1 and sent[0]["identifier"] == "marker:ora-one-shot", sent
    assert sent[0]["subject"] == PLAIN_SUBJECT, "a run whose digest is not new keeps the existing subject"
    print("  PASS test_stranded_subject_only_changes_when_digest_is_new_unit")


def test_stranded_digest_reason_content_unit():
    tmp = tempfile.mkdtemp(prefix="prg-st-e2e-")
    tasks = _with_live(*[f"ora-dark-{i:02d}" for i in range(30)])
    tasks["lams"] = [_rec("ora-lams-a"), _rec("ora-lams-b"), _rec("ora-lams-live", enabled=True)]
    held = _write_holds(tmp, {"holds": [_hold("lams", "*", "2026-01-31", reason="LAMS fleet kept dark"),
                                        {"fleet": "cc", "id": "ora-dark-00", "reason": "forgot the date"}]})
    sent = []
    _, calls = _run_main_with_fixtures(tasks, tmp, send_alert_result=True, held_off_path=held, sent_log=sent)
    assert calls == 1 and sent[0]["identifier"] == "stranded:digest", sent
    assert sent[0]["subject"] == STRANDED_SUBJECT % (32, 1), sent[0]["subject"]
    today = datetime.now(timezone.utc).date().isoformat()
    reason = _digest_reason(sent[0]["body"])
    head, rest = reason.split("\n")[0], reason.split("\n")[1:]
    assert head.startswith("32 ") and ("first stranded by this check %s" % today) in head \
        and "week 1" in head, head
    newly = [n for n, line in enumerate(rest) if line.strip().startswith("Newly stranded (32): ")]
    capped = [n for n, line in enumerate(rest) if line.strip().startswith("No recorded intent (30): ")]
    assert len(newly) == 1 and len(capped) == 1 and newly[0] < capped[0], rest
    assert reason.count("(off since ") == 25, "the no-intent list stops at 25 entries: %r" % reason
    assert ("cc:ora-dark-24 (off since %s)" % today) in reason and "cc:ora-dark-25 (off since" not in reason
    assert "..." in reason
    expired = [line for line in rest if "Expired hold" in line]
    assert len(expired) == 1, rest
    for needle in ("lams:ora-lams-a", "lams:ora-lams-b", "2026-01-31", "LAMS fleet kept dark"):
        assert needle in expired[0], (needle, expired[0])
    assert "lams:ora-lams-a (off since" not in reason, "expired holds are listed separately"
    assert any("missing reviewBy" in line for line in rest), "a register error is named in the digest"
    assert "held-off.json (fleet, id, reason, ruledBy, ruledOn, reviewBy)" in rest[-1], rest[-1]
    assert "register-scheduled-task" in rest[-1], "the digest ends with the remedy: %r" % rest[-1]
    print("  PASS test_stranded_digest_reason_content_unit")


def test_stranded_digest_and_incomplete_resume_share_one_email_unit():
    """OI-273 shape with no hold: the incomplete-resume alarm and the digest of the same
    still-disabled ids go out together, in ONE email."""
    tmp = tempfile.mkdtemp(prefix="prg-st-e2e-")
    ids = [f"task-{i}" for i in range(38)]
    tasks = {"cc": _fleet_with_resume(tmp, set(ids[:6]), ids, fired_minutes_ago=90)}
    sent = []
    _, calls = _run_main_with_fixtures(tasks, tmp, send_alert_result=True, sent_log=sent)
    assert calls == 1, "one run, one email"
    assert sent[0]["identifier"].split("; ") == ["incomplete-resume:cc:ora-routine-pause-resume-x",
                                                 "stranded:digest"], sent[0]["identifier"]
    assert sent[0]["subject"] == STRANDED_SUBJECT % (32, 1), sent[0]["subject"]
    print("  PASS test_stranded_digest_and_incomplete_resume_share_one_email_unit")


def test_stranded_check_crash_never_kills_main_unit():
    tmp = tempfile.mkdtemp(prefix="prg-st-crash-")
    tasks = _with_live("ora-dark")
    state0, _ = _run_main_with_fixtures(tasks, tmp, send_alert_result=True)  # digest delivered
    original = prg.find_stranded

    def boom(*a, **k):
        raise RuntimeError("synthetic")
    prg.find_stranded = boom
    try:
        sent = []
        state1, calls1 = _run_main_with_fixtures(tasks, tmp, send_alert_result=True, sent_log=sent)
        _, calls2 = _run_main_with_fixtures(tasks, tmp, send_alert_result=True)
    finally:
        prg.find_stranded = original
    assert calls1 == 1 and sent[0]["identifier"] == "stranded:check-error", sent
    assert sent[0]["subject"] == PLAIN_SUBJECT and "synthetic" in sent[0]["body"], sent[0]
    assert calls2 == 0, "a persisting check error must not re-email every run"
    record = ("ids", "firstSeen", "alertedAt", "lastAlerted")
    assert {k: state1["_stranded"][k] for k in record} == {k: state0["_stranded"][k] for k in record}, \
        "a check that could not run must not rewrite the stranded record"
    state3, calls3 = _run_main_with_fixtures(tasks, tmp, send_alert_result=True)
    assert calls3 == 0, "recovered: the same, already-delivered set is not re-sent"
    assert state3["_stranded"].get("checkError", {}).get("alarmed", False) is False, \
        "a recovered check must clear its error alarm so a future failure re-alarms"
    print("  PASS test_stranded_check_crash_never_kills_main_unit")


def test_stranded_text_summary_line_unit():
    """The native task runs WITHOUT --json, so the text summary is the production path."""
    tmp = tempfile.mkdtemp(prefix="prg-st-text-")
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        _run_main_with_fixtures(_with_live("ora-dark"), tmp, send_alert_result=True, json_output=False)
    lines = buf.getvalue().splitlines()
    assert [line for line in lines if line.startswith("stranded:")] == ["stranded: 1"], lines
    print("  PASS test_stranded_text_summary_line_unit")


def test_stranded_0928_replay_unit():
    """REPLAY 2026-09-28: the resume fired 5 days ago, its folder was archived (SKILL.md gone)
    and 35 recurring tasks are still disabled. The incomplete-resume check finds nothing,
    exactly as it did then -- inside its 72h window because open() fails on the archived
    path, after it because the window has closed -- and the fleet ratio (40/75 enabled)
    looks healthy. The stranded digest is the one check that still sees it."""
    tmp = tempfile.mkdtemp(prefix="prg-st-0928-")
    dark = [f"ora-report-{i:02d}" for i in range(35)]
    live = [f"ora-live-{i:02d}" for i in range(40)]
    archived = os.path.join(tmp, "scheduled-tasks", "ora-routine-pause-resume-09-28", "SKILL.md")

    def fleet(fired_ago):
        fired = datetime.now(timezone.utc) - fired_ago
        return {"cc": [_rec(i) for i in dark] + [_rec(i, enabled=True) for i in live] + [
            {"id": "ora-routine-pause-resume-09-28", "cronExpression": None, "fireAt": _epoch_ms(fired),
             "enabled": False, "lastRunAt": fired.strftime("%Y-%m-%dT%H:%M:%S.000Z"), "filePath": archived}]}

    assert not os.path.exists(archived)
    none = os.path.join(tmp, "none.json")
    assert prg.find_incomplete_resumes(fleet(timedelta(hours=30)), retire_pending_path=none) == [], \
        "inside the window: open() on the archived path fails and the case is skipped"
    tasks = fleet(timedelta(days=5))
    assert prg.find_incomplete_resumes(tasks, retire_pending_path=none) == []
    sent = []
    state, calls = _run_main_with_fixtures(tasks, tmp, send_alert_result=True, sent_log=sent)
    assert calls == 1, "the stranded digest must fire where every event-based check is blind"
    assert sent[0]["identifier"] == "stranded:digest", sent[0]["identifier"]
    assert sent[0]["subject"] == STRANDED_SUBJECT % (35, 1), sent[0]["subject"]
    assert state["_stranded"]["ids"] == sorted("cc:" + i for i in dark), state["_stranded"]["ids"]
    assert sorted(state["_stranded"]["alertedAt"]) == state["_stranded"]["ids"], state["_stranded"]
    assert state.get("_incompleteResume") == {}, state.get("_incompleteResume")
    _, calls2 = _run_main_with_fixtures(tasks, tmp, send_alert_result=True)
    assert calls2 == 0, "6h later, same dark set: quiet until the set changes or a week passes"
    print("  PASS test_stranded_0928_replay_unit")


# --- 2026-11-05 adversarial REFUTE findings (D1-D11, C8, atomic save, "*" fleet-ratio ruling) ---

_STALL = [{"taskId": "ora-one-shot", "fleet": "cc", "step": 2, "totalSteps": 5,
           "staleMinutes": 99, "note": "blocked"}]


def test_stranded_digest_build_crash_becomes_check_error_unit():
    """D1: a failure AFTER find_stranded returns -- the reviewer's two digest-build inputs,
    injected past the D9 validators -- becomes the stranded:check-error alarm. The run's other
    alarm still goes out in the same email, and the state is still saved."""
    lapsed = {"fleet": "cc", "reason": "hold-expired", "reviewBy": "2026-01-01"}
    cases = {"unhashable holdReason": [dict(lapsed, id="ora-x", holdReason=["a", "list"])],
             "mixed int/str holdReason": [dict(lapsed, id="ora-x", holdReason=5),
                                          dict(lapsed, id="ora-y", holdReason="five")]}
    original = prg.find_stranded
    for label, bad in cases.items():
        tmp = tempfile.mkdtemp(prefix="prg-st-d1-")
        prg.find_stranded = lambda *a, _bad=bad, **k: ([dict(s) for s in _bad], [])
        try:
            sent = []
            state, calls = _run_main_with_fixtures(_with_live("ora-x", "ora-y"), tmp, send_alert_result=True,
                                                   stalled=_STALL, sent_log=sent)
        finally:
            prg.find_stranded = original
        assert calls == 1, (label, calls)
        assert sent[0]["identifier"].split("; ") == ["marker:ora-one-shot", "stranded:check-error"], \
            (label, sent[0]["identifier"])
        assert os.path.exists(prg.STATE_PATH), label
        assert state["_markers"]["ora-one-shot"]["alarmed"] is True, (label, "other alarm delivered and saved")
        assert state["_stranded"]["checkError"]["alarmed"] is True, (label, state["_stranded"])
    print("  PASS test_stranded_digest_build_crash_becomes_check_error_unit")


def test_stranded_reviewer_inputs_never_crash_the_real_path_unit():
    """D1 + D9 end to end: the same inputs arriving the real way -- expired holds whose reason is a
    list, a dict or an int beside a str, and non-string elements in a stored ids/alertedIds -- are
    stopped at the door (a named register error / dropped from the stored record). Nothing
    crashes, the state is saved, and the run's other alarm still goes out beside the digest."""
    tmp = tempfile.mkdtemp(prefix="prg-st-d1-real-")
    held = _write_holds(tmp, {"holds": [_hold("cc", "ora-x", "2026-01-01", reason=["kept", "dark"]),
                                        _hold("cc", "ora-y", "2026-01-01", reason={"why": "dark"}),
                                        _hold("cc", "ora-z", "2026-01-01", reason=5),
                                        _hold("cc", "ora-w", "2026-01-01", reason="a real ruling")]})
    then = (datetime.now(timezone.utc) - timedelta(days=4)).isoformat()
    prg.STATE_PATH = os.path.join(tmp, "state.json")
    prg.save_state({"_stranded": {"ids": ["cc:ora-x", ["not", "hashable"], 7],
                                  "firstSeen": {"cc:ora-x": then},
                                  "alertedIds": [["not", "hashable"], {"a": 1}, "cc:ora-x"],
                                  "lastAlerted": then}})
    sent = []
    state, calls = _run_main_with_fixtures(_with_live("ora-x", "ora-y", "ora-z", "ora-w"), tmp,
                                           send_alert_result=True, held_off_path=held, stalled=_STALL,
                                           sent_log=sent)
    assert calls == 1, calls
    assert sent[0]["identifier"].split("; ") == ["marker:ora-one-shot", "stranded:digest"], sent[0]["identifier"]
    reason = _digest_reason(sent[0]["body"])
    assert reason.count("reason must be a string") == 3, reason
    st = state["_stranded"]
    assert st["ids"] == ["cc:ora-w", "cc:ora-x", "cc:ora-y", "cc:ora-z"], st
    assert all(isinstance(k, str) for k in st["alertedAt"]) and "alertedIds" not in st, st
    assert state["_markers"]["ora-one-shot"]["alarmed"] is True
    print("  PASS test_stranded_reviewer_inputs_never_crash_the_real_path_unit")


def test_stranded_pause_exclusion_requires_a_bounded_resume_unit():
    """D2: capture_pause_windows()'s held list has no time bound of its own and is not
    resume-specific, so a fleet's held ids are honoured only while that fleet has an ENABLED
    one-time *-resume-* task firing between 24h ago and 21 days ahead. Otherwise the list is
    ignored, the ids are judged like any other, and ONE note says why."""
    held = {"cc": ["ora-paused"]}
    cases = [("bounded: fires in 3 days", [_resume_task(timedelta(days=3))], True),
             ("bounded: 20h overdue", [_resume_task(-timedelta(hours=20))], True),
             ("unbounded: fires in 30 days", [_resume_task(timedelta(days=30))], False),
             ("stale: 30h overdue", [_resume_task(-timedelta(hours=30))], False),
             ("non-resume holder", [_resume_task(timedelta(days=3), task_id="ora-quarterly-catch-up")], False),
             ("disabled resume", [_resume_task(timedelta(days=3), enabled=False)], False),
             ("no holder at all", [], False)]
    for label, extra, honoured in cases:
        tmp = tempfile.mkdtemp(prefix="prg-st-d2-")
        out, notes = _stranded({"cc": [_rec("ora-paused")] + extra}, tmp, held_by_pause=held)
        if honoured:
            assert out == [] and notes == [], (label, out, notes)
        else:
            assert [s["id"] for s in out] == ["ora-paused"], (label, out)
            assert len(notes) == 1 and notes[0].startswith("pause exclusion ignored for cc"), (label, notes)
    # end to end, the note rides in the digest
    tmp = tempfile.mkdtemp(prefix="prg-st-d2-e2e-")
    tasks = _with_live("ora-paused")
    tasks["cc"].append(_resume_task(timedelta(days=30)))
    sent = []
    _, calls = _run_main_with_fixtures(tasks, tmp, send_alert_result=True, held_by_pause=held, sent_log=sent)
    assert calls == 1 and "pause exclusion ignored for cc" in _digest_reason(sent[0]["body"]), sent
    print("  PASS test_stranded_pause_exclusion_requires_a_bounded_resume_unit")


def test_stranded_digest_names_every_new_id_past_the_cap_unit():
    """D3: 30 ids already delivered, a 31st newly stranded. It sorts last in the 25-entry
    oldest-first list, so the uncapped "Newly stranded" line is what names it."""
    tmp = tempfile.mkdtemp(prefix="prg-st-d3-")
    tasks = _with_live(*[f"ora-old-{i:02d}" for i in range(30)])
    _run_main_with_fixtures(tasks, tmp, send_alert_result=True)
    st = prg.load_state()
    earlier = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
    st["_stranded"]["firstSeen"] = {k: earlier for k in st["_stranded"]["ids"]}
    prg.save_state(st)
    tasks["cc"].append(_rec("ora-zz-new"))
    sent = []
    _, calls = _run_main_with_fixtures(tasks, tmp, send_alert_result=True, sent_log=sent)
    assert calls == 1, calls
    reason = _digest_reason(sent[0]["body"])
    assert "Newly stranded (1): cc:ora-zz-new" in reason, reason
    assert "cc:ora-zz-new (off since" not in reason, "the 25-entry list alone would have hidden it"
    assert sent[0]["subject"] == STRANDED_SUBJECT % (31, 1), sent[0]["subject"]
    print("  PASS test_stranded_digest_names_every_new_id_past_the_cap_unit")


def test_stranded_missing_fleet_keeps_its_record_unit():
    """D5: a run that finds no LAMS registry must neither judge nor wipe LAMS's record."""
    tmp = tempfile.mkdtemp(prefix="prg-st-d5-")
    cc = _recurring_tasks(10, enabled=True) + [_rec("ora-dark-cc")]
    lams = [_rec("ora-dark-lams"), _rec("ora-lams-live", enabled=True)]
    state1, calls1 = _run_main_with_fixtures({"cc": cc, "lams": lams}, tmp, send_alert_result=True)
    assert calls1 == 1
    rec1 = state1["_stranded"]
    state2, calls2 = _run_main_with_fixtures({"cc": cc}, tmp, send_alert_result=True)  # no LAMS registry
    rec2 = state2["_stranded"]
    assert calls2 == 0, calls2
    assert rec2["ids"] == rec1["ids"], rec2
    for field in ("firstSeen", "alertedAt"):
        assert rec2[field]["lams:ora-dark-lams"] == rec1[field]["lams:ora-dark-lams"], (field, rec2)
    cc[-1]["enabled"] = True  # CC is still judged while LAMS is unseen
    state3, _ = _run_main_with_fixtures({"cc": cc}, tmp, send_alert_result=True)
    assert state3["_stranded"]["ids"] == ["lams:ora-dark-lams"], state3["_stranded"]
    state4, calls4 = _run_main_with_fixtures({"cc": cc, "lams": lams}, tmp, send_alert_result=True)
    assert calls4 == 0, "LAMS back with the same dark task: already delivered, not news"
    assert state4["_stranded"]["firstSeen"]["lams:ora-dark-lams"] == rec1["firstSeen"]["lams:ora-dark-lams"]
    print("  PASS test_stranded_missing_fleet_keeps_its_record_unit")


def test_stranded_flapping_exclusion_sends_once_within_7_days_unit():
    """D6: an exclusion that comes and goes (here a bounded pause hold) must not re-send the
    digest on every re-entry. alertedAt keeps each id's last delivered digest for 7 days, even
    while the id is out of the set; after that a re-entry is news again."""
    tmp = tempfile.mkdtemp(prefix="prg-st-d6-")
    tasks = _with_live("ora-flappy")
    tasks["cc"].append(_resume_task(timedelta(days=2)))  # bounded holder, so the held list counts
    held = {"cc": ["ora-flappy"]}
    calls = [_run_main_with_fixtures(tasks, tmp, send_alert_result=True, held_by_pause=h)[1]
             for h in (None, held, None, held, None)]
    assert calls == [1, 0, 0, 0, 0], calls
    st = prg.load_state()
    old = (datetime.now(timezone.utc) - timedelta(days=8)).isoformat()
    st["_stranded"]["alertedAt"] = {"cc:ora-flappy": old}
    st["_stranded"]["lastAlerted"] = old
    prg.save_state(st)
    _, excused = _run_main_with_fixtures(tasks, tmp, send_alert_result=True, held_by_pause=held)
    _, back = _run_main_with_fixtures(tasks, tmp, send_alert_result=True)
    assert (excused, back) == (0, 1), (excused, back)
    print("  PASS test_stranded_flapping_exclusion_sends_once_within_7_days_unit")


def test_stranded_old_format_alerted_ids_are_migrated_unit():
    """D6: a pre-alertedAt state ({"alertedIds": [...]}) reads as "each of those ids alerted at
    lastAlerted" and is rewritten in the new shape."""
    tmp = tempfile.mkdtemp(prefix="prg-st-d6m-")
    then = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
    prg.STATE_PATH = os.path.join(tmp, "state.json")
    prg.save_state({"_stranded": {"ids": ["cc:ora-dark"], "firstSeen": {"cc:ora-dark": then},
                                  "alertedIds": ["cc:ora-dark"], "lastAlerted": then}})
    state, calls = _run_main_with_fixtures(_with_live("ora-dark"), tmp, send_alert_result=True)
    assert calls == 0, "an id in a pre-D6 alertedIds was alerted at lastAlerted (2 days ago)"
    assert state["_stranded"] == {"ids": ["cc:ora-dark"], "firstSeen": {"cc:ora-dark": then},
                                  "alertedAt": {"cc:ora-dark": then}, "lastAlerted": then}, state["_stranded"]
    print("  PASS test_stranded_old_format_alerted_ids_are_migrated_unit")


def test_stranded_future_or_unreadable_last_alerted_re_alerts_unit():
    """D7: a delivery stamp in the future (clock jump, hand edit) or unreadable must not suppress
    re-alerts indefinitely -- it is stale. Same for a per-id alertedAt."""
    future = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
    for field, bad in (("lastAlerted", future), ("lastAlerted", "not a timestamp"), ("alertedAt", future)):
        tmp = tempfile.mkdtemp(prefix="prg-st-d7-")
        tasks = _with_live("ora-dark")
        _run_main_with_fixtures(tasks, tmp, send_alert_result=True)  # delivered
        st = prg.load_state()
        if field == "alertedAt":
            st["_stranded"]["alertedAt"] = {"cc:ora-dark": bad}
        else:
            st["_stranded"]["lastAlerted"] = bad
        prg.save_state(st)
        state, calls = _run_main_with_fixtures(tasks, tmp, send_alert_result=True)
        assert calls == 1, (field, bad, calls)
        assert state["_stranded"]["lastAlerted"] != bad, (field, "delivery replaces the bad stamp")
    print("  PASS test_stranded_future_or_unreadable_last_alerted_re_alerts_unit")


def test_stranded_exact_hold_decides_before_the_wildcard_unit():
    """D8: an exact-id hold, active or expired, decides its task alone -- an active "*" must not
    hide an EXPIRED per-task ruling, and an expired "*" must not override an active one."""
    tmp = tempfile.mkdtemp(prefix="prg-st-d8-")
    tasks = {"lams": [_rec("ora-a"), _rec("ora-b")]}
    out, errors = _stranded(tasks, tmp, holds={"holds": [
        _hold("lams", "*", "2099-12-31", reason="LAMS fleet kept dark"),
        _hold("lams", "ora-a", "2026-10-01", reason="per-task review was due 10-01")]})
    assert errors == [], errors
    assert out == [{"fleet": "lams", "id": "ora-a", "reason": "hold-expired",
                    "holdReason": "per-task review was due 10-01", "reviewBy": "2026-10-01"}], out
    out, _ = _stranded(tasks, tmp, holds={"holds": [
        _hold("lams", "*", "2026-01-31", reason="old fleet ruling"),
        _hold("lams", "ora-a", "2099-12-31", reason="still deliberate")]})
    assert [(s["id"], s["reason"]) for s in out] == [("ora-b", "hold-expired")], out
    print("  PASS test_stranded_exact_hold_decides_before_the_wildcard_unit")


def test_load_holds_rejects_non_string_fields_unit():
    """D9: a non-string fleet, id, reason or reviewBy makes the entry malformed -- named, no hold
    -- and nothing is coerced: no str(), no case-folding, no trimming."""
    tmp = tempfile.mkdtemp(prefix="prg-st-d9-")
    bad = [{"fleet": "cc", "id": ["ora-a"], "reviewBy": "2099-12-31"},
           _hold("cc", "ora-a", "2026-01-01", reason=["kept", "dark"]),
           _hold("cc", "ora-a", "2026-01-01", reason={"why": "dark"}),
           {"fleet": 1, "id": "ora-a", "reviewBy": "2099-12-31"},
           {"fleet": "cc", "id": "ora-a", "reviewBy": 20991231},
           {"fleet": "cc", "id": 42, "reviewBy": "2099-12-31"},
           _hold("CC", "ora-a", "2099-12-31"),
           _hold("cc", " ora-a", "2099-12-31")]
    p = _write_holds(tmp, {"holds": bad}, name="bad-holds.json")
    active, expired, errors = prg.load_holds(p, today=TODAY)
    assert (active, expired) == ([], []), (active, expired)
    assert len(errors) == len(bad), errors
    out, errs = _stranded({"cc": [_rec("ora-a")]}, tmp, holds={"holds": bad})
    assert [(s["id"], s["reason"]) for s in out] == [("ora-a", "no-recorded-intent")], out
    assert len(errs) == len(bad), errs
    print("  PASS test_load_holds_rejects_non_string_fields_unit")


def test_retire_pending_bom_is_read_unit():
    """D10: PowerShell 5.1 writes UTF-8 WITH a BOM. Read as strict utf-8 that looked malformed,
    stranding every retire-pending id (and blinding the resurrection check)."""
    tmp = tempfile.mkdtemp(prefix="prg-rp-bom-")
    p = os.path.join(tmp, "retire-pending.json")
    with open(p, "w", encoding="utf-8-sig") as f:
        json.dump({"pending": [{"fleet": "lams", "id": "ora-passed-deal-tracker"}]}, f)
    assert [e["id"] for e in prg.load_retire_pending(p)] == ["ora-passed-deal-tracker"]
    out, errors = prg.find_stranded({"lams": [_rec("ora-passed-deal-tracker")]}, retire_pending_path=p,
                                    holds_path=os.path.join(tmp, "none.json"), today=TODAY)
    assert (out, errors) == ([], []), (out, errors)
    print("  PASS test_retire_pending_bom_is_read_unit")


def test_save_state_is_atomic_unit():
    """A run killed or failing mid-write (one died at 12 s on 2026-11-05, exit 0xC000013A) must
    leave the previous state intact -- not a truncated file that load_state() reads as {}."""
    tmp = tempfile.mkdtemp(prefix="prg-save-")
    prg.STATE_PATH = os.path.join(tmp, "state.json")
    prg.save_state({"cc": {"alarmed": True}})
    real_dump = prg.json.dump

    def torn_dump(obj, f, **kw):
        f.write('{"cc": {"ala')
        raise OSError("simulated: disk full mid-write")
    prg.json.dump = torn_dump
    raised = False
    try:
        prg.save_state({"cc": {"alarmed": False}})
    except OSError:
        raised = True
    finally:
        prg.json.dump = real_dump
    assert raised, "a failed write must not pass silently"
    assert prg.load_state() == {"cc": {"alarmed": True}}, "the previous state must survive a torn write"
    assert os.listdir(tmp) == ["state.json"], os.listdir(tmp)
    print("  PASS test_save_state_is_atomic_unit")


def test_send_alert_records_every_attempt_in_send_log_unit():
    """C8: every subprocess attempt lands in send_log -- rc==0, rc!=0 (stderr kept, first 500
    chars), the rc 2 retry pair, and an exception inside subprocess.run (recorded, never
    raised) -- capped at the 10 most recent."""
    saved = (prg.subprocess.run, prg._log_send_failure_to_notion)
    prg._log_send_failure_to_notion = lambda subject, identifier, proc: True
    try:
        log = []
        prg.subprocess.run = lambda args, **kw: _proc(0, stdout="queued " * 50)
        assert prg.send_alert("s-ok", "body", send_log=log) is True
        e = log[-1]
        assert (e["ok"], e["rc"], e["subject"], e["stderr"], len(e["stdout"])) == (True, 0, "s-ok", "", 200), e
        assert prg._parse_run_ts(e["at"]) is not None, e
        prg.subprocess.run = lambda args, **kw: _proc(1, stderr="E" * 600)
        assert prg.send_alert("s-fail", "body", send_log=log) is False
        assert (log[-1]["ok"], log[-1]["rc"], len(log[-1]["stderr"])) == (False, 1, 500), log[-1]
        rcs = iter([2, 0])
        prg.subprocess.run = lambda args, **kw: _proc(next(rcs))
        assert prg.send_alert("s-retry", "body", send_log=log) is True
        assert [(x["rc"], x["ok"]) for x in log[-2:]] == [(2, False), (0, True)], log[-2:]

        def boom(args, **kw):
            raise FileNotFoundError("powershell is not on PATH")
        prg.subprocess.run = boom
        assert prg.send_alert("s-exc", "body", send_log=log) is False, "an exception is a failed delivery"
        e = log[-1]
        assert (e["ok"], e["rc"], e["exception"]) == (False, None, "FileNotFoundError: powershell is not on PATH"), e
        prg.subprocess.run = lambda args, **kw: _proc(0)
        for n in range(12):
            prg.send_alert("s-%02d" % n, "body", send_log=log)
        assert [x["subject"] for x in log] == ["s-%02d" % n for n in range(2, 12)], [x["subject"] for x in log]
    finally:
        prg.subprocess.run, prg._log_send_failure_to_notion = saved
    print("  PASS test_send_alert_records_every_attempt_in_send_log_unit")


def test_send_log_is_saved_printed_and_in_json_unit():
    """C8 end to end: main() keeps the attempts in state["_sendLog"], prints the latest in the
    text summary and includes _sendLog in --json. The send command line itself is unchanged."""
    tmp = tempfile.mkdtemp(prefix="prg-sendlog-")
    tasks = _with_live("ora-dark")
    runs = []

    def runner(args, **kw):
        runs.append(list(args))
        return _proc(1, stderr="Outlook COM: class not registered")
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        state, _ = _run_main_with_fixtures(tasks, tmp, send_alert_result=None, send_runner=runner,
                                           json_output=False)
    assert len(runs) == 1, runs
    a = runs[0]
    assert a[:7] == ["powershell", "-NoProfile", "-File", prg.SEND_SCRIPT, "-To", "ggoldberg@oxfordra.net",
                     "-Subject"], a
    assert a[7] == STRANDED_SUBJECT % (1, 1) and a[8] == "-BodyFile" and a[10:] == ["-BodyFormat", "text"], a
    log = state["_sendLog"]
    assert len(log) == 1 and (log[0]["ok"], log[0]["rc"]) == (False, 1), log
    assert "class not registered" in log[0]["stderr"], log
    last = [line for line in buf.getvalue().splitlines() if line.startswith("last send: ")]
    assert len(last) == 1 and "rc=1" in last[0] and "class not registered" in last[0], last
    assert state["_stranded"]["lastAlerted"] is None, "a failed send is not a delivery"
    buf2 = io.StringIO()
    with contextlib.redirect_stdout(buf2):
        state2, _ = _run_main_with_fixtures(tasks, tmp, send_alert_result=None, send_runner=runner,
                                            json_output=True)
    out = json.loads(buf2.getvalue())
    assert [e["rc"] for e in out["_sendLog"]] == [1, 1], out["_sendLog"]
    assert out["_sendLog"] == state2["_sendLog"]
    print("  PASS test_send_log_is_saved_printed_and_in_json_unit")


def test_fleet_wildcard_hold_suppresses_only_the_fleet_ratio_alarm_unit():
    """2026-11-05 deliberate change: an ACTIVE "*" hold (Gabriel ruled LAMS dark 2026-10-30) also
    holds that fleet's fleet-ratio near-zero alarm -- with one printed line -- while the marker,
    retire-pending, incomplete-resume and stranded checks run untouched. A lapsed "*" holds
    nothing."""
    lams = [_rec(f"ora-lams-{i:02d}") for i in range(11)] + [_rec("ora-lams-retiring", enabled=True)]

    def run(review_by):
        tmp = tempfile.mkdtemp(prefix="prg-ratio-hold-")
        tasks = {"cc": _recurring_tasks(10, enabled=True), "lams": [dict(t) for t in lams]}
        rp = _write_rp(tmp, {"pending": [{"fleet": "lams", "id": "ora-lams-retiring", "ratified": "2026-10-30"}]})
        held = _write_holds(tmp, {"holds": [_hold("lams", "*", review_by, reason="LAMS fleet kept dark")]})
        prg.STATE_PATH = os.path.join(tmp, "state.json")
        prg.save_state({"lams": {"nearZero": True, "lastChecked": "x", "alarmed": False}})  # 2nd near-zero run
        buf, sent = io.StringIO(), []
        with contextlib.redirect_stdout(buf):
            state, calls = _run_main_with_fixtures(tasks, tmp, send_alert_result=True, retire_pending_path=rp,
                                                   held_off_path=held, sent_log=sent, json_output=False)
        return state, calls, sent, [line for line in buf.getvalue().splitlines() if "held by ruling" in line]

    state, calls, sent, held_lines = run("2099-12-31")  # ruling active
    assert calls == 1 and sent[0]["identifier"] == "retire-pending:lams:ora-lams-retiring", sent
    assert len(held_lines) == 1 and held_lines[0].startswith("fleet-ratio: lams near-zero alarm held by ruling"), \
        held_lines
    assert state["lams"]["nearZero"] is True and state["lams"]["alarmed"] is False, state["lams"]
    state, calls, sent, held_lines = run("2026-01-31")  # ruling lapsed
    idents = sent[0]["identifier"].split("; ")
    assert calls == 1 and idents[0] == "lams" and "stranded:digest" in idents, idents
    assert held_lines == [], held_lines
    print("  PASS test_fleet_wildcard_hold_suppresses_only_the_fleet_ratio_alarm_unit")


if __name__ == "__main__":
    main()
