#!/usr/bin/env python3
"""Tests for fleet-status.py's verdict recalibration (added 2026-07-14).

Black-box, subprocess-driven against a synthetic registry (`--registry PATH --json`,
both flags the script's own docstring already documents as "used by tests"). No
mocking of datetime.now() -- every fixture timestamp is computed relative to the
real wall clock at test-run time via now_ms(), so the script's own now_ms() and the
test's expectations always agree regardless of when the suite runs.

Contract under test (the recalibration, not the pre-existing table/collision code):
  * never-ran is only VERDICT-worthy if the task is a RECURRING task (no fireAt) whose
    createdAt is older than a cadence-aware buffer inferred from its cron fields --
    a quarterly/annual task that simply hasn't reached its next fire yet must not flag.
  * FIRST-SLOT RULE (2026-09-02, R21-2b): a never-ran recurring task whose first
    post-registration slot elapsed more than MISSED_CYCLE_GRACE_HOURS ago IS overdue
    regardless of that buffer; a slot that predates createdAt never counts.
  * A one-time task (has fireAt) is never counted under never-ran-overdue; it's
    handled by the expired-needs-attention check below instead.
  * expired one-time is only VERDICT-worthy if it never fired (missed) or is still
    enabled past its fireAt (didn't auto-disable) -- a normal successful one-time
    completion (lastRunAt set, enabled false) must NOT flag.
  * throttle skips only count within the last 24h (each event carries its own "at"
    timestamp) -- an old burst must decay out, not remain a permanent scar.
  * same-time collisions are unchanged: any co-occurrence still flags.
  * an all-healthy synthetic fleet (no collisions, nothing overdue, nothing missed,
    no recent skips) must show VERDICT: OK.

Stdlib only. ASCII-only. Windows (`python`).
"""
import json
import os
import subprocess
import sys
import tempfile
import time

HOOK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fleet-status.py")

DAY = 86400 * 1000
_failures = []


def now_ms():
    return int(time.time() * 1000)


def recent_iso(hours_ago=1):
    """An ISO8601 'Z' timestamp a couple hours old -- well inside the
    missed-single-cycle detector's grace window (added 2026-07-27, OI-031),
    for fixtures where task health/missed-cycle status isn't what's under
    test. A fixed old date like 2026-01-01 would now trip that detector and
    force an unrelated ATTENTION verdict."""
    import datetime
    dt = datetime.datetime.fromtimestamp((now_ms() - hours_ago * 3600 * 1000) / 1000.0,
                                          datetime.timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def check(name, cond, detail=""):
    if cond:
        print("PASS " + name)
    else:
        print("FAIL " + name + "  " + detail)
        _failures.append(name)


def run(tasks, skips=None):
    """Write a synthetic registry, run fleet-status.py --json against it, return the
    parsed JSON (or None + stderr on a hard failure)."""
    reg = {"scheduledTasks": tasks, "recordedSkips": skips or {}}
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "scheduled-tasks.json")
        with open(p, "w", encoding="utf-8") as fh:
            json.dump(reg, fh)
        proc = subprocess.run(
            [sys.executable, HOOK, "--registry", p, "--json"],
            capture_output=True, text=True,
        )
        if proc.returncode != 0:
            return None, proc.stderr
        return json.loads(proc.stdout), proc.stderr


def task(id_, cron=None, fire_at=None, enabled=True, last_run=None, created_days_ago=None):
    t = {"id": id_, "enabled": enabled}
    if cron is not None:
        t["cronExpression"] = cron
    if fire_at is not None:
        t["fireAt"] = fire_at
    if last_run is not None:
        t["lastRunAt"] = last_run
    if created_days_ago is not None:
        t["createdAt"] = now_ms() - int(created_days_ago * DAY)
    return t


# 1. All-healthy synthetic fleet -> VERDICT: OK.

def test_registration_age_annotates_never():
    """A bare NEVER reads as "dead". On 2026-08-16 that inference nearly retired
    the WORKING half of a dual-fleet pair: ora-passed-deal-tracker's CC copy had
    never fired because it was registered THAT MORNING on a monthly cron."""
    import importlib.util, tempfile, datetime
    spec = importlib.util.spec_from_file_location("fs_mod", HOOK)
    fs = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fs)

    log = "\n".join([
        "2026-07-08T10:00:00 cc=1 lams=1 drops=- regressions=- "
        "adds={'lams': ['ora-passed-deal-tracker']} missing_stores=-",
        "2026-08-16T11:47:46 cc=3 lams=1 drops=- regressions=- "
        "adds={'cc': ['ora-county-sales-monitor', 'ora-passed-deal-tracker']} "
        "missing_stores=-",
        "",
    ])
    fd, path = tempfile.mkstemp(suffix=".log"); os.close(fd)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(log)
    try:
        reg = fs.registration_dates(path)
        # The line ends with `missing_stores=-`, so an end-of-line anchor after
        # `adds={...}` matched nothing and silently returned {} -- which looks
        # exactly like "no registrations recorded".
        check("adds parsed despite trailing missing_stores=", len(reg) == 3, repr(reg))
        # Keyed by (fleet, id): the same taskId legitimately lives on BOTH fleets,
        # and collapsing them reported the LAMS birthday for the CC copy -- i.e.
        # "6 weeks old and never fired", the false 'dead' reading itself.
        check("CC copy carries its own registration date",
              reg.get("cc:ora-passed-deal-tracker") == "2026-08-16", repr(reg))
        check("LAMS original keeps its earlier date",
              reg.get("lams:ora-passed-deal-tracker") == "2026-07-08", repr(reg))
        now = datetime.datetime(2026, 8, 16, 12, 0)
        check("same-day registration reads 'registered today'",
              fs.never_label("ora-passed-deal-tracker", "cc", reg, now)
              == "NEVER (registered today)",
              fs.never_label("ora-passed-deal-tracker", "cc", reg, now))
        check("older registration reports its age",
              "39d ago" in fs.never_label("ora-passed-deal-tracker", "lams", reg, now),
              fs.never_label("ora-passed-deal-tracker", "lams", reg, now))
        check("unknown registration yields a BARE NEVER, never a guessed age",
              fs.never_label("ora-nope", "cc", reg, now) == "NEVER")
        check("missing log yields {} rather than raising",
              fs.registration_dates(path + ".nope") == {})
    finally:
        os.unlink(path)


def test_all_healthy_is_ok():
    tasks = [
        task("daily-a", cron="0 6 * * *", created_days_ago=1, last_run=recent_iso()),
        task("weekly-b", cron="0 7 * * 1", created_days_ago=2, last_run=recent_iso()),
        task("quarterly-c", cron="0 8 1 1,4,7,10 *", created_days_ago=5),  # never-ran, not due -- fine
        task("onetime-d", fire_at=now_ms() - 5 * DAY, enabled=False, last_run="2026-01-01T00:00:00Z"),
    ]
    data, err = run(tasks)
    check("test_all_healthy_is_ok", data is not None and data.get("verdict") == "OK",
          "expected OK, got %r (stderr=%s)" % (data, err))


# 2. A quarterly task that has simply never reached its next fire is NOT overdue.
def test_quarterly_not_yet_due_is_not_overdue():
    tasks = [task("quarterly-new", cron="0 8 1 1,4,7,10 *", created_days_ago=10)]
    data, _ = run(tasks)
    check("test_quarterly_not_yet_due_is_not_overdue",
          data is not None and data.get("never_ran_overdue") == [],
          "expected no overdue never-ran, got %r" % (data,))


# 3. A daily task created weeks ago that has NEVER run once IS overdue.
def test_daily_never_run_for_weeks_is_overdue():
    tasks = [task("daily-stale", cron="0 6 * * *", created_days_ago=20)]
    data, _ = run(tasks)
    check("test_daily_never_run_for_weeks_is_overdue",
          data is not None and data.get("never_ran_overdue") == ["daily-stale"],
          "expected daily-stale flagged overdue, got %r" % (data,))
    check("test_daily_never_run_for_weeks_is_overdue_verdict",
          data is not None and data.get("verdict", "").startswith("ATTENTION"),
          "expected ATTENTION verdict, got %r" % (data,))


# 4. A monthly task created 10 days ago whose next slot is still AHEAD has NOT
#    exceeded its cadence buffer and has no elapsed post-registration slot.
#    (Pinned to a day-of-month 3 days in the future: a fixed `1 * *` here was
#    date-dependent -- run on the 2nd or 3rd of a month, the 1st has just
#    elapsed and the first-slot rule correctly flags it, which is test 4b.)
def _dom_days_from_today(delta_days):
    import datetime
    return (datetime.date.today() + datetime.timedelta(days=delta_days)).day


def test_monthly_recent_creation_not_overdue():
    cron = "0 5 %d * *" % _dom_days_from_today(+3)
    tasks = [task("monthly-new", cron=cron, created_days_ago=10)]
    data, _ = run(tasks)
    check("test_monthly_recent_creation_not_overdue",
          data is not None and data.get("never_ran_overdue") == [],
          "expected not overdue, got %r" % (data,))


# 4b. FIRST-SLOT RULE (2026-09-02, Automation Audit R21-2b): a never-ran
#     recurring task whose first post-registration slot elapsed more than the
#     grace window ago IS overdue, regardless of the cadence buffer. This is the
#     ora-pm-monthly-billing shape: registered 08-21, slot 09-01 11:10 missed
#     in an outage, previously read "0 overdue" until ~09-30.
def test_monthly_never_ran_first_slot_elapsed_is_overdue():
    cron = "0 0 %d * *" % _dom_days_from_today(-2)   # slot ~2 days ago, 00:00 local
    tasks = [task("monthly-missed", cron=cron, created_days_ago=5)]
    data, _ = run(tasks)
    check("test_monthly_never_ran_first_slot_elapsed_is_overdue",
          data is not None and data.get("never_ran_overdue") == ["monthly-missed"],
          "expected monthly-missed flagged, got %r" % (data,))
    check("test_monthly_never_ran_first_slot_elapsed_reason",
          data is not None and "first slot" in data.get("never_ran_overdue_reason", {}).get("monthly-missed", ""),
          "expected first-slot reason, got %r" % (data,))
    check("test_monthly_never_ran_first_slot_elapsed_verdict",
          data is not None and data.get("verdict", "").startswith("ATTENTION"),
          "expected ATTENTION verdict, got %r" % (data,))


# 4c. A slot that predates registration never counts: the same cron registered
#     AFTER the slot passed is simply waiting for next month (the
#     ora-passed-deal-tracker shape -- registered 08-16 on a `15 * *` cron).
def test_monthly_never_ran_slot_before_registration_not_overdue():
    cron = "0 0 %d * *" % _dom_days_from_today(-2)
    tasks = [task("monthly-fresh", cron=cron, created_days_ago=1)]
    data, _ = run(tasks)
    check("test_monthly_never_ran_slot_before_registration_not_overdue",
          data is not None and data.get("never_ran_overdue") == [],
          "expected not overdue (slot predates createdAt), got %r" % (data,))


# 5. A one-time task with a FUTURE fireAt is never-ran but not due -- no flag anywhere.
def test_onetime_future_fire_not_flagged():
    tasks = [task("future-onetime", fire_at=now_ms() + 5 * DAY)]
    data, _ = run(tasks)
    check("test_onetime_future_fire_not_flagged",
          data is not None and data.get("never_ran_overdue") == []
          and data.get("expired_needs_attention") == [],
          "future one-time task must not flag anywhere, got %r" % (data,))


# 6. Normal successful one-time completion (fired, then auto-disabled) -> not flagged.
def test_onetime_normal_completion_not_flagged():
    tasks = [task("onetime-done", fire_at=now_ms() - 3 * DAY, enabled=False,
                  last_run="2026-01-01T00:00:00Z")]
    data, _ = run(tasks)
    check("test_onetime_normal_completion_not_flagged",
          data is not None and data.get("expired_needs_attention") == [],
          "successful one-time completion must not flag, got %r" % (data,))


# 7. One-time task past fireAt that NEVER fired (missed) -> flagged.
def test_onetime_missed_fire_flagged():
    tasks = [task("onetime-missed", fire_at=now_ms() - 3 * DAY, enabled=False)]
    data, _ = run(tasks)
    check("test_onetime_missed_fire_flagged",
          data is not None and data.get("expired_needs_attention") == ["onetime-missed"],
          "missed one-time fire must flag, got %r" % (data,))


# 8. One-time task past fireAt that fired but never auto-disabled -> flagged.
def test_onetime_stuck_enabled_flagged():
    tasks = [task("onetime-stuck", fire_at=now_ms() - 3 * DAY, enabled=True,
                  last_run="2026-01-01T00:00:00Z")]
    data, _ = run(tasks)
    check("test_onetime_stuck_enabled_flagged",
          data is not None and data.get("expired_needs_attention") == ["onetime-stuck"],
          "still-enabled-past-fireAt must flag, got %r" % (data,))


# 9. Throttle skip events within the last 24h count; older ones decay out.
def test_recent_skips_counted_old_skips_decay():
    tasks = [task("noisy", cron="0 6 * * *", created_days_ago=1, last_run="2026-01-01T00:00:00Z")]
    skips = {
        "noisy": [
            {"at": now_ms() - 2 * 3600 * 1000, "reason": "global_limit"},   # 2h ago -- recent
            {"at": now_ms() - 10 * DAY, "reason": "global_limit"},          # 10d ago -- decayed
        ]
    }
    data, _ = run(tasks, skips)
    check("test_recent_skips_counted_old_skips_decay",
          data is not None and data.get("recent_skip_events_24h") == 1,
          "expected exactly 1 recent skip counted, got %r" % (data,))
    check("test_recent_skips_verdict_attention",
          data is not None and data.get("verdict", "").startswith("ATTENTION"),
          "a real recent skip must still drive ATTENTION, got %r" % (data,))


# 10. An old, fully-decayed skip burst alone must NOT keep the verdict at ATTENTION.
def test_old_skip_burst_alone_is_ok():
    tasks = [task("quiet", cron="0 6 * * *", created_days_ago=1, last_run=recent_iso())]
    skips = {"quiet": [{"at": now_ms() - 30 * DAY, "reason": "global_limit"}]}
    data, _ = run(tasks, skips)
    check("test_old_skip_burst_alone_is_ok",
          data is not None and data.get("verdict") == "OK",
          "old decayed skip burst alone must not block OK, got %r" % (data,))


# 11. Same-time collisions are UNCHANGED -- still always a real flag.
def test_collision_still_flags():
    tasks = [
        task("a", cron="0 6 * * *", created_days_ago=1, last_run="2026-01-01T00:00:00Z"),
        task("b", cron="0 6 * * *", created_days_ago=1, last_run="2026-01-01T00:00:00Z"),
    ]
    data, _ = run(tasks)
    check("test_collision_still_flags",
          data is not None and data.get("verdict", "").startswith("ATTENTION")
          and data.get("collisions"),
          "same-time collision must still flag, got %r" % (data,))


# 12. Same clock time, disjoint days-of-week -> NOT a real collision (added 2026-07-20
# after cron_hm()-only grouping flagged ora-financial-code-integrity-sweep (Mon 13:30)
# x ora-appsec-sweep (Wed 13:30) as a false-positive collision).
def test_same_time_different_weekday_not_a_collision():
    tasks = [
        task("mon-task", cron="30 13 * * 1", created_days_ago=1, last_run=recent_iso()),
        task("wed-task", cron="30 13 * * 3", created_days_ago=1, last_run=recent_iso()),
    ]
    data, _ = run(tasks)
    check("test_same_time_different_weekday_not_a_collision",
          data is not None and data.get("collisions") == {},
          "Mon-only vs Wed-only at the same clock time must not collide, got %r" % (data,))
    check("test_same_time_different_weekday_verdict_ok",
          data is not None and data.get("verdict") == "OK",
          "expected OK verdict with no genuine collision, got %r" % (data,))


# 13. Same clock time, overlapping weekday RANGES -> still a real collision.
def test_same_time_overlapping_weekday_range_still_collides():
    tasks = [
        task("weekday-task", cron="0 9 * * 1-5", created_days_ago=1, last_run="2026-01-01T00:00:00Z"),
        task("wed-task2", cron="0 9 * * 3", created_days_ago=1, last_run="2026-01-01T00:00:00Z"),
    ]
    data, _ = run(tasks)
    check("test_same_time_overlapping_weekday_range_still_collides",
          data is not None and data.get("collisions"),
          "Wed is inside Mon-Fri -- must still collide, got %r" % (data,))


# 14. A multi-fire cron (comma-list hour field) whose one AM-window fire time
# falls in 05:00-09:30 must be counted in am_pileup_count -- prior cron_hm()
# raised ValueError on "7,13,19" and silently dropped the task from the count
# entirely (flagged 07-27c, closed 2026-08-09).
def test_multifire_cron_counted_in_am_pileup():
    tasks = [task("ora-lease-snapshot-refresh", cron="40 7,13,19 * * 1-5",
                  created_days_ago=1, last_run=recent_iso())]
    data, _ = run(tasks)
    check("test_multifire_cron_counted_in_am_pileup",
          data is not None and data.get("am_pileup_count") == 1,
          "expected the 07:40 fire time counted once, got %r" % (data,))


# 15. A multi-fire task sharing ONE of its fire times with a single-fire task
# must show up as a real same-time collision (previously invisible to
# collision detection for the same cron_hm() reason as #14).
def test_multifire_cron_collides_on_shared_fire_time():
    tasks = [
        task("ora-lease-snapshot-refresh", cron="40 7,13,19 * * 1-5",
             created_days_ago=1, last_run=recent_iso()),
        task("other-1340-task", cron="40 13 * * 1-5",
             created_days_ago=1, last_run=recent_iso()),
    ]
    data, _ = run(tasks)
    check("test_multifire_cron_collides_on_shared_fire_time",
          data is not None and "13:40" in (data.get("collisions") or {})
          and set(data["collisions"]["13:40"]) ==
              {"ora-lease-snapshot-refresh", "other-1340-task"},
          "expected a 13:40 collision between the two tasks, got %r" % (data,))


# 16. --json's per-task tasks[] entries expose last_run_at directly (added
# 2026-08-12, closes the gap flagged in reference_ora_session_sweep_lams_
# registry_gap.md: a caller cross-referencing lastRunAt for date-sourcing
# had to fall back to re-parsing the registry file paths fleet-status.py
# prints, duplicating discover_registries() logic, because the JSON output
# had id/fleet/enabled/cron but not lastRunAt even though the human-readable
# table already prints it and the registry itself always carries the field).
def test_json_tasks_expose_last_run_at():
    tasks = [
        task("ran-before", cron="0 6 * * *", created_days_ago=5,
             last_run="2026-08-01T12:00:00.000Z"),
        task("never-ran", cron="0 8 1 1,4,7,10 *", created_days_ago=1),
    ]
    data, _ = run(tasks)
    by_id = {t["id"]: t for t in (data or {}).get("tasks", [])}
    check("test_json_tasks_expose_last_run_at_present",
          data is not None
          and by_id.get("ran-before", {}).get("last_run_at") == "2026-08-01T12:00:00.000Z",
          "expected ran-before's last_run_at echoed verbatim, got %r" % (data,))
    check("test_json_tasks_expose_last_run_at_null_when_never_ran",
          data is not None and by_id.get("never-ran", {}).get("last_run_at") is None,
          "expected never-ran's last_run_at to be null, got %r" % (data,))


if __name__ == "__main__":
    test_all_healthy_is_ok()
    test_quarterly_not_yet_due_is_not_overdue()
    test_daily_never_run_for_weeks_is_overdue()
    test_monthly_recent_creation_not_overdue()
    test_monthly_never_ran_first_slot_elapsed_is_overdue()
    test_monthly_never_ran_slot_before_registration_not_overdue()
    test_onetime_future_fire_not_flagged()
    test_onetime_normal_completion_not_flagged()
    test_onetime_missed_fire_flagged()
    test_registration_age_annotates_never()
    test_onetime_stuck_enabled_flagged()
    test_recent_skips_counted_old_skips_decay()
    test_old_skip_burst_alone_is_ok()
    test_collision_still_flags()
    test_same_time_different_weekday_not_a_collision()
    test_same_time_overlapping_weekday_range_still_collides()
    test_multifire_cron_counted_in_am_pileup()
    test_multifire_cron_collides_on_shared_fire_time()
    test_json_tasks_expose_last_run_at()
    if _failures:
        print("\n%d FAILURE(S): %s" % (len(_failures), ", ".join(_failures)))
        sys.exit(1)
    print("\nALL fleet-status verdict-recalibration tests passed.")
    sys.exit(0)
