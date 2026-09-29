#!/usr/bin/env python3
"""Tests for block-sentinel.py -- the per-block, per-ET-date scheduled-task entry guard.

Built 2026-08-09 after ora-am-brief double-fired during the overnight-offline
catch-up burst (machine woke 219 min late; ora-health-guard reported the lag).
Block B published Notion page 3b76ecd8-9e59-8160-bb0f-c6b5c925a278 and sent
"ORA Daily Brief - Sunday, August 9 2026" at 09:06 ET, then a second fire landed
at 09:11 ET (registry lastRunAt 2026-08-09T13:11:04Z). Only a manual stand-down
stopped the second fire from re-sending the email and clobbering the page --
Block B has no entry guard, and the daily-brief skill's Patch 3 pre-create check
dedups the NOTION PAGE ONLY (the COM send is unconditional) and on "exactly 1
match" does replace_content, i.e. it OVERWRITES a completed prior run's page
because it assumes any match is its own retry artifact.

Contract under test:
  * claim on a virgin date PROCEEDs and writes IN_PROGRESS.
  * claim when today's block is COMPLETE returns SKIP_ALREADY_COMPLETE (exit 10)
    and emits the BLOCK_<X>_ALREADY_COMPLETE_TODAY log token -- this is the
    same-day second-invocation path the 08-09 incident needed.
  * claim when IN_PROGRESS is YOUNGER than the TTL returns STAND_DOWN (exit 11)
    -- two overlapping fires. A COMPLETE-only sentinel would not catch this,
    because fire #2 arrives while fire #1 is still generating.
  * claim when IN_PROGRESS is OLDER than the TTL re-claims and PROCEEDs -- a
    crashed run must not wedge the task forever. Both halves of the TTL are
    load-bearing; test them separately.
  * blocks are independent within a date, and dates are independent of each other.
  * complete records notionPageId / emailSentAt and flips status to COMPLETE.
  * the ET date -- not UTC, not naive-local -- keys the record. A 22:00 ET run
    on Aug 9 is UTC Aug 10; it must still key to 2026-08-09.
  * --force overrides a COMPLETE record (the documented manual-rerun escape
    hatch; a real all-blocks manual verification run happened on 2026-08-09
    at 10:51 ET and must remain possible).
  * a corrupt/unreadable state file FAILS OPEN (PROCEED) -- never let the guard
    itself become the reason the brief stops going out.

Stdlib only. ASCII-only. Windows (`python`). Run: python test-block-sentinel.py
"""
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "block-sentinel.py")

_failures = []


def run(args, state):
    """Invoke block-sentinel.py; return (exit_code, parsed_json_stdout)."""
    cmd = [sys.executable, SCRIPT] + args + ["--state", state]
    p = subprocess.run(cmd, capture_output=True, text=True)
    try:
        payload = json.loads(p.stdout)
    except Exception:
        payload = {"_raw_stdout": p.stdout, "_stderr": p.stderr}
    return p.returncode, payload


def check(name, cond, detail=""):
    if cond:
        print("  PASS  %s" % name)
    else:
        print("  FAIL  %s  %s" % (name, detail))
        _failures.append(name)


def tmp_state():
    fd, path = tempfile.mkstemp(suffix=".json", prefix="sentinel-test-")
    os.close(fd)
    os.remove(path)  # want the path, not the file -- virgin state
    return path


def write_state(path, obj):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh)


def read_state(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def et_today():
    """Today's ET date, computed independently of the script under test."""
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(timezone.utc).astimezone(ZoneInfo("America/New_York")).strftime("%Y-%m-%d")
    except Exception:
        # Mirrors the script's fallback rule (2nd Sun Mar 02:00 -> 1st Sun Nov 02:00),
        # NOT a flat -4. A flat -4 made every date-keyed test fail spuriously between
        # November and March on a host without tzdata.
        u = datetime.now(timezone.utc)

        def nth_sunday(month, nth):
            d = datetime(u.year, month, 1, tzinfo=timezone.utc)
            return d + timedelta(days=(6 - d.weekday()) % 7 + 7 * (nth - 1))

        off = -4 if (nth_sunday(3, 2) + timedelta(hours=7)) <= u < (nth_sunday(11, 1) + timedelta(hours=6)) else -5
        return (u + timedelta(hours=off)).strftime("%Y-%m-%d")


def iso_ago(minutes):
    return (datetime.now(timezone.utc) - timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------- tests

def test_virgin_claim_proceeds():
    print("\ntest_virgin_claim_proceeds")
    st = tmp_state()
    rc, out = run(["claim", "--task", "ora-am-brief", "--block", "blockB", "--run-id", "r1"], st)
    check("exit 0", rc == 0, "got %s (%s)" % (rc, out))
    check("decision PROCEED", out.get("decision") == "PROCEED", str(out))
    data = read_state(st)
    rec = data[et_today()]["blockB"]
    check("status IN_PROGRESS", rec["status"] == "IN_PROGRESS", str(rec))
    check("runId recorded", rec["runId"] == "r1", str(rec))
    check("claimedAt present", bool(rec.get("claimedAt")), str(rec))
    os.remove(st)


def test_already_complete_skips():
    """THE 2026-08-09 INCIDENT PATH: fire #2 arrives after fire #1 finished."""
    print("\ntest_already_complete_skips")
    st = tmp_state()
    write_state(st, {et_today(): {"blockB": {
        "status": "COMPLETE", "runId": "fire1", "claimedAt": iso_ago(20),
        "notionPageId": "3b76ecd8-9e59-8160-bb0f-c6b5c925a278",
        "emailSentAt": iso_ago(5)}}})
    rc, out = run(["claim", "--task", "ora-am-brief", "--block", "blockB", "--run-id", "fire2"], st)
    check("exit 10", rc == 10, "got %s (%s)" % (rc, out))
    check("decision SKIP_ALREADY_COMPLETE", out.get("decision") == "SKIP_ALREADY_COMPLETE", str(out))
    check("log token", out.get("logToken") == "BLOCK_B_ALREADY_COMPLETE_TODAY", str(out))
    check("skip classified NORMAL", out.get("skipClass") == "NORMAL", str(out))
    check("prior notionPageId surfaced", out.get("record", {}).get("notionPageId", "").startswith("3b76ecd8"), str(out))
    rec = read_state(st)[et_today()]["blockB"]
    check("prior record untouched", rec["runId"] == "fire1", str(rec))
    os.remove(st)


def test_in_progress_within_ttl_stands_down():
    """Two OVERLAPPING fires -- the case a COMPLETE-only sentinel cannot catch."""
    print("\ntest_in_progress_within_ttl_stands_down")
    st = tmp_state()
    write_state(st, {et_today(): {"blockB": {
        "status": "IN_PROGRESS", "runId": "fire1", "claimedAt": iso_ago(4),
        "notionPageId": None, "emailSentAt": None}}})
    rc, out = run(["claim", "--task", "ora-am-brief", "--block", "blockB",
                   "--run-id", "fire2", "--ttl-min", "30"], st)
    check("exit 11", rc == 11, "got %s (%s)" % (rc, out))
    check("decision STAND_DOWN", out.get("decision") == "STAND_DOWN_IN_PROGRESS", str(out))
    check("log token", out.get("logToken") == "BLOCK_B_IN_PROGRESS_ELSEWHERE", str(out))
    rec = read_state(st)[et_today()]["blockB"]
    check("claim NOT stolen", rec["runId"] == "fire1", str(rec))
    os.remove(st)


def test_in_progress_past_ttl_reclaims():
    """Crashed run must not wedge the task -- a legitimate retry has to get through."""
    print("\ntest_in_progress_past_ttl_reclaims")
    st = tmp_state()
    write_state(st, {et_today(): {"blockB": {
        "status": "IN_PROGRESS", "runId": "crashed", "claimedAt": iso_ago(95),
        "notionPageId": None, "emailSentAt": None}}})
    rc, out = run(["claim", "--task", "ora-am-brief", "--block", "blockB",
                   "--run-id", "retry", "--ttl-min", "30"], st)
    check("exit 0", rc == 0, "got %s (%s)" % (rc, out))
    check("decision PROCEED", out.get("decision") == "PROCEED", str(out))
    check("reclaim flagged", out.get("logToken") == "BLOCK_B_RECLAIMED_STALE_IN_PROGRESS", str(out))
    rec = read_state(st)[et_today()]["blockB"]
    check("claim taken over", rec["runId"] == "retry", str(rec))
    check("still IN_PROGRESS", rec["status"] == "IN_PROGRESS", str(rec))
    os.remove(st)


def test_ttl_boundary_is_exclusive_both_ways():
    """TTL is load-bearing in BOTH directions; pin the boundary, not just the middle."""
    print("\ntest_ttl_boundary_is_exclusive_both_ways")
    st = tmp_state()
    write_state(st, {et_today(): {"blockB": {
        "status": "IN_PROGRESS", "runId": "f1", "claimedAt": iso_ago(29),
        "notionPageId": None, "emailSentAt": None}}})
    rc, _ = run(["claim", "--task", "t", "--block", "blockB", "--run-id", "f2", "--ttl-min", "30"], st)
    check("29min < 30min TTL -> stand down", rc == 11, "got %s" % rc)
    write_state(st, {et_today(): {"blockB": {
        "status": "IN_PROGRESS", "runId": "f1", "claimedAt": iso_ago(31),
        "notionPageId": None, "emailSentAt": None}}})
    rc, _ = run(["claim", "--task", "t", "--block", "blockB", "--run-id", "f2", "--ttl-min", "30"], st)
    check("31min > 30min TTL -> reclaim", rc == 0, "got %s" % rc)
    os.remove(st)


def test_blocks_and_dates_are_independent():
    print("\ntest_blocks_and_dates_are_independent")
    st = tmp_state()
    write_state(st, {
        et_today(): {"blockB": {"status": "COMPLETE", "runId": "x", "claimedAt": iso_ago(10),
                                "notionPageId": None, "emailSentAt": None}},
        "2000-01-01": {"blockD": {"status": "COMPLETE", "runId": "ancient", "claimedAt": "2000-01-01T10:00:00Z",
                                  "notionPageId": None, "emailSentAt": None}},
    })
    rc, out = run(["claim", "--task", "t", "--block", "blockD", "--run-id", "r"], st)
    check("blockD unaffected by blockB COMPLETE", rc == 0, "got %s (%s)" % (rc, out))
    check("blockD unaffected by old-date COMPLETE", out.get("decision") == "PROCEED", str(out))
    rc, _ = run(["claim", "--task", "t", "--block", "blockB", "--run-id", "r"], st)
    check("blockB still blocked", rc == 10, "got %s" % rc)
    os.remove(st)


def test_complete_records_artifacts():
    print("\ntest_complete_records_artifacts")
    st = tmp_state()
    run(["claim", "--task", "t", "--block", "blockB", "--run-id", "r1"], st)
    rc, out = run(["complete", "--task", "t", "--block", "blockB", "--run-id", "r1",
                   "--notion-page-id", "3b76ecd8", "--email-sent-at", "2026-08-09T13:06:58Z"], st)
    check("exit 0", rc == 0, "got %s (%s)" % (rc, out))
    rec = read_state(st)[et_today()]["blockB"]
    check("status COMPLETE", rec["status"] == "COMPLETE", str(rec))
    check("notionPageId stored", rec["notionPageId"] == "3b76ecd8", str(rec))
    check("emailSentAt stored", rec["emailSentAt"] == "2026-08-09T13:06:58Z", str(rec))
    rc, _ = run(["claim", "--task", "t", "--block", "blockB", "--run-id", "r2"], st)
    check("subsequent claim now skips", rc == 10, "got %s" % rc)
    os.remove(st)


def test_et_date_not_utc_date():
    """A 22:00 ET run is already tomorrow in UTC; the record must key to the ET date."""
    print("\ntest_et_date_not_utc_date")
    st = tmp_state()
    rc, out = run(["claim", "--task", "t", "--block", "blockB", "--run-id", "r"], st)
    check("exit 0", rc == 0, "got %s" % rc)
    key = list(read_state(st).keys())[0]
    check("keyed to ET date", key == et_today(), "key=%s et_today=%s" % (key, et_today()))
    check("etDate echoed in output", out.get("etDate") == et_today(), str(out))
    utc_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if utc_date != et_today():
        check("ET date differs from UTC date and ET won", key != utc_date, "key=%s utc=%s" % (key, utc_date))
    else:
        print("  SKIP  ET/UTC dates coincide right now -- boundary not exercisable")
    os.remove(st)


def test_force_overrides_complete():
    """The 2026-08-09 10:51 ET manual all-blocks verification run must stay possible."""
    print("\ntest_force_overrides_complete")
    st = tmp_state()
    write_state(st, {et_today(): {"blockB": {"status": "COMPLETE", "runId": "sched",
                                             "claimedAt": iso_ago(60), "notionPageId": "p",
                                             "emailSentAt": iso_ago(55)}}})
    rc, out = run(["claim", "--task", "t", "--block", "blockB", "--run-id", "manual", "--force"], st)
    check("exit 0", rc == 0, "got %s (%s)" % (rc, out))
    check("forced flagged", out.get("logToken") == "BLOCK_B_FORCED_OVERRIDE", str(out))
    rec = read_state(st)[et_today()]["blockB"]
    check("claim taken over", rec["runId"] == "manual", str(rec))
    os.remove(st)


def test_corrupt_state_fails_open():
    print("\ntest_corrupt_state_fails_open")
    st = tmp_state()
    with open(st, "w", encoding="utf-8") as fh:
        fh.write("{ this is not json ][")
    rc, out = run(["claim", "--task", "t", "--block", "blockB", "--run-id", "r"], st)
    check("exit 0 (fail open)", rc == 0, "got %s (%s)" % (rc, out))
    check("degradation surfaced", out.get("stateFileError") is not None, str(out))
    os.remove(st)


def test_status_is_read_only():
    print("\ntest_status_is_read_only")
    st = tmp_state()
    rc, out = run(["status", "--task", "t", "--block", "blockB"], st)
    check("exit 0 on missing state", rc == 0, "got %s (%s)" % (rc, out))
    check("no file created by status", not os.path.exists(st), "status wrote a file")
    check("reports absent", out.get("record") is None, str(out))


def test_old_dates_pruned():
    print("\ntest_old_dates_pruned")
    st = tmp_state()
    write_state(st, {"2000-01-01": {"blockA": {"status": "COMPLETE", "runId": "x",
                                               "claimedAt": "2000-01-01T10:00:00Z",
                                               "notionPageId": None, "emailSentAt": None}}})
    run(["claim", "--task", "t", "--block", "blockB", "--run-id", "r"], st)
    data = read_state(st)
    check("ancient date pruned", "2000-01-01" not in data, str(list(data.keys())))
    check("today retained", et_today() in data, str(list(data.keys())))
    os.remove(st)


# ---------------------------------------------- added after code review 2026-08-09

def run_env(args, state, env):
    """Invoke with extra environment (clock / zoneinfo injection)."""
    e = dict(os.environ)
    e.update(env)
    cmd = [sys.executable, SCRIPT] + args + ["--state", state]
    p = subprocess.run(cmd, capture_output=True, text=True, env=e)
    try:
        return p.returncode, json.loads(p.stdout)
    except Exception:
        return p.returncode, {"_raw": p.stdout, "_err": p.stderr}


def test_et_date_at_utc_boundary_is_deterministic():
    """Was tautological: the only assertion that could catch a UTC regression sat
    behind "if the two dates happen to differ right now", so it slept ~16h/day.
    Pin it with an injected clock instead."""
    print("\ntest_et_date_at_utc_boundary_is_deterministic")
    st = tmp_state()
    # 2026-08-10T02:30Z == 2026-08-09 22:30 EDT. The ET date must be the 9th.
    rc, out = run_env(["claim", "--task", "t", "--block", "blockB", "--run-id", "r"], st,
                      {"ORA_SENTINEL_NOW": "2026-08-10T02:30:00Z"})
    check("exit 0", rc == 0, "got %s (%s)" % (rc, out))
    check("ET date is 08-09, not UTC 08-10", out.get("etDate") == "2026-08-09", str(out.get("etDate")))
    check("state keyed to ET date", "2026-08-09" in read_state(st), str(list(read_state(st).keys())))
    os.remove(st)
    # And in winter, where the offset is -5.
    rc, out = run_env(["claim", "--task", "t", "--block", "blockB", "--run-id", "r"], st,
                      {"ORA_SENTINEL_NOW": "2026-01-15T04:30:00Z"})
    check("EST boundary: 2026-01-14, not 01-15", out.get("etDate") == "2026-01-14", str(out.get("etDate")))
    os.remove(st)


def test_dst_fallback_matches_zoneinfo():
    """The manual DST rule is the most intricate arithmetic in the file and is dead
    code on a host where zoneinfo works -- so force the fallback and diff it against
    zoneinfo across both transitions."""
    print("\ntest_dst_fallback_matches_zoneinfo")
    try:
        from zoneinfo import ZoneInfo
    except Exception:
        print("  SKIP  zoneinfo unavailable -- nothing to diff against")
        return
    probes = [
        "2026-03-08T06:59:00Z",  # 01:59 EST, just before spring forward
        "2026-03-08T07:01:00Z",  # 03:01 EDT, just after
        "2026-11-01T05:59:00Z",  # 01:59 EDT, just before fall back
        "2026-11-01T06:01:00Z",  # 01:01 EST, just after
        "2026-06-15T12:00:00Z",
        "2026-12-31T04:30:00Z",  # UTC year boundary, ET still the 30th
        "2027-01-01T02:00:00Z",
    ]
    st = tmp_state()
    for iso in probes:
        want = datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(
            ZoneInfo("America/New_York")).strftime("%Y-%m-%d")
        if os.path.exists(st):
            os.remove(st)
        _, out = run_env(["claim", "--task", "t", "--block", "blockB", "--run-id", "r"], st,
                         {"ORA_SENTINEL_NOW": iso, "ORA_SENTINEL_NO_ZONEINFO": "1"})
        check("fallback == zoneinfo @ %s" % iso, out.get("etDate") == want,
              "fallback=%s zoneinfo=%s" % (out.get("etDate"), want))
    if os.path.exists(st):
        os.remove(st)


def test_concurrent_claims_grant_exactly_one():
    """The lock is the single most load-bearing property of the guard and was
    entirely untested. Fire N claims at once; exactly one may win."""
    print("\ntest_concurrent_claims_grant_exactly_one")
    st = tmp_state()
    procs = [subprocess.Popen(
        [sys.executable, SCRIPT, "claim", "--task", "t", "--block", "blockB",
         "--run-id", "racer%d" % i, "--ttl-min", "30", "--state", st],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for i in range(6)]
    codes = [p.wait() for p in procs]
    check("exactly one PROCEED", codes.count(0) == 1, "codes=%s" % codes)
    check("the other five stood down", codes.count(11) == 5, "codes=%s" % codes)
    rec = read_state(st)[et_today()]["blockB"]
    check("winner owns the record", str(rec["runId"]).startswith("racer"), str(rec))
    os.remove(st)


def test_complete_without_claim_is_refused():
    """The design's only real false-suppression path: fabricating COMPLETE for a
    block nobody claimed would silently suppress every later fire that ET date."""
    print("\ntest_complete_without_claim_is_refused")
    st = tmp_state()
    rc, out = run(["complete", "--task", "t", "--block", "blockB", "--run-id", "ghost"], st)
    check("exit 12 REFUSED", rc == 12, "got %s (%s)" % (rc, out))
    check("nothing persisted", out.get("persisted") is False, str(out))
    check("no state file written", not os.path.exists(st), "a file was created")
    rc, _ = run(["claim", "--task", "t", "--block", "blockB", "--run-id", "real"], st)
    check("a real run still PROCEEDs", rc == 0, "got %s" % rc)
    os.remove(st)


def test_adopt_allows_state_loss_reconvergence():
    """--adopt is the one legitimate no-prior-claim path: the Sent-Items probe
    reported ALREADY_SENT after the OneDrive state file was lost."""
    print("\ntest_adopt_allows_state_loss_reconvergence")
    st = tmp_state()
    rc, out = run(["complete", "--task", "t", "--block", "blockB", "--run-id", "reconverge",
                   "--adopt", "--email-sent-at", "2026-08-09T13:06:58Z"], st)
    check("exit 0", rc == 0, "got %s (%s)" % (rc, out))
    rec = read_state(st)[et_today()]["blockB"]
    check("COMPLETE recorded", rec["status"] == "COMPLETE", str(rec))
    check("marked adopted", rec.get("adopted") is True, str(rec))
    os.remove(st)


def test_fail_from_non_owner_is_refused():
    """A stood-down fire calling fail must NOT release the live fire's claim."""
    print("\ntest_fail_from_non_owner_is_refused")
    st = tmp_state()
    run(["claim", "--task", "t", "--block", "blockB", "--run-id", "live"], st)
    rc, _ = run(["claim", "--task", "t", "--block", "blockB", "--run-id", "stoodDown"], st)
    check("second claim stands down", rc == 11, "got %s" % rc)
    rc, out = run(["fail", "--task", "t", "--block", "blockB", "--run-id", "stoodDown",
                   "--error", "wrongly reported"], st)
    check("exit 12 REFUSED", rc == 12, "got %s (%s)" % (rc, out))
    rec = read_state(st)[et_today()]["blockB"]
    check("live claim intact", rec["runId"] == "live" and rec["status"] == "IN_PROGRESS", str(rec))
    rc, _ = run(["claim", "--task", "t", "--block", "blockB", "--run-id", "third"], st)
    check("third fire still blocked", rc == 11, "got %s" % rc)
    os.remove(st)


def test_owner_may_fail_and_that_releases_the_claim():
    print("\ntest_owner_may_fail_and_that_releases_the_claim")
    st = tmp_state()
    run(["claim", "--task", "t", "--block", "main", "--run-id", "r1"], st)
    rc, out = run(["fail", "--task", "t", "--block", "main", "--run-id", "r1",
                   "--error", "notion unreachable"], st)
    check("exit 0", rc == 0, "got %s (%s)" % (rc, out))
    rec = read_state(st)[et_today()]["main"]
    check("status FAILED", rec["status"] == "FAILED", str(rec))
    check("error recorded", rec.get("error") == "notion unreachable", str(rec))
    rc, out = run(["claim", "--task", "t", "--block", "main", "--run-id", "r2"], st)
    check("retry proceeds immediately, no TTL wait", rc == 0, "got %s (%s)" % (rc, out))
    os.remove(st)


def test_block_id_aliases_address_one_record():
    """Block ids are typed into an LLM-executed spec at four call sites per block,
    so blockB / blockb / Block-B must all address the SAME record."""
    print("\ntest_block_id_aliases_address_one_record")
    st = tmp_state()
    run(["claim", "--task", "t", "--block", "blockB", "--run-id", "r1"], st)
    rc, _ = run(["complete", "--task", "t", "--block", "blockb", "--run-id", "r1"], st)
    check("alias complete accepted", rc == 0, "got %s" % rc)
    keys = list(read_state(st)[et_today()].keys())
    check("exactly one record, not two", len(keys) == 1, "keys=%s" % keys)
    rc, _ = run(["claim", "--task", "t", "--block", "Block-B", "--run-id", "r2"], st)
    check("alias claim sees it COMPLETE", rc == 10, "got %s" % rc)
    os.remove(st)


def test_main_block_id_supported():
    """ora-deal-aging-sla uses --block main; the non-block* token path was unexercised."""
    print("\ntest_main_block_id_supported")
    st = tmp_state()
    rc, out = run(["claim", "--task", "ora-deal-aging-sla", "--block", "main", "--run-id", "r1"], st)
    check("exit 0", rc == 0, "got %s (%s)" % (rc, out))
    check("token is BLOCK_MAIN_*", str(out.get("logToken", "")).startswith("BLOCK_MAIN_"), str(out))
    run(["complete", "--task", "ora-deal-aging-sla", "--block", "main", "--run-id", "r1"], st)
    rc, out = run(["claim", "--task", "ora-deal-aging-sla", "--block", "main", "--run-id", "r2"], st)
    check("second fire skips", rc == 10, "got %s" % rc)
    check("token BLOCK_MAIN_ALREADY_COMPLETE_TODAY",
          out.get("logToken") == "BLOCK_MAIN_ALREADY_COMPLETE_TODAY", str(out))
    os.remove(st)


def test_period_month_reclaims_across_days_within_same_month():
    """A monthly task claimed and completed on the 1st must SKIP on a re-fire
    later the same month (2026-09-06 does NOT restage a monthly task) -- the
    gap --period exists to close (added 2026-09-06)."""
    print("\ntest_period_month_reclaims_across_days_within_same_month")
    st = tmp_state()
    rc, out = run(["claim", "--task", "t", "--block", "main", "--run-id", "r1",
                   "--period", "month"], st)
    check("exit 0", rc == 0, "got %s (%s)" % (rc, out))
    check("periodKey is YYYY-MM", out.get("periodKey") == et_today()[:7], str(out))
    run(["complete", "--task", "t", "--block", "main", "--run-id", "r1", "--period", "month"], st)
    rc, out = run(["claim", "--task", "t", "--block", "main", "--run-id", "r2",
                   "--period", "month"], st)
    check("same-month re-fire skips", rc == 10, "got %s (%s)" % (rc, out))
    os.remove(st)


def test_period_week_keys_to_iso_week():
    print("\ntest_period_week_keys_to_iso_week")
    st = tmp_state()
    rc, out = run(["claim", "--task", "t", "--block", "main", "--run-id", "r1",
                   "--period", "week"], st)
    check("exit 0", rc == 0, "got %s (%s)" % (rc, out))
    check("periodKey looks like an ISO week", bool(out.get("periodKey", "").count("-W") == 1),
          str(out))
    data = read_state(st)
    check("state keyed to the ISO week, not the day", et_today() not in data, str(list(data.keys())))
    os.remove(st)


def test_period_day_is_unaffected_default():
    """--period defaults to "day" -- omitting the flag entirely must reproduce
    the exact pre-existing behavior (etDate, day-keyed state)."""
    print("\ntest_period_day_is_unaffected_default")
    st = tmp_state()
    rc, out = run(["claim", "--task", "t", "--block", "main", "--run-id", "r1"], st)
    check("exit 0", rc == 0, "got %s (%s)" % (rc, out))
    check("period defaults to day", out.get("period") == "day", str(out))
    check("periodKey equals etDate for day period", out.get("periodKey") == out.get("etDate"), str(out))
    check("etDate is today's ET date", out.get("etDate") == et_today(), str(out))
    os.remove(st)


def test_period_month_and_day_buckets_are_independent():
    """The same task/block claimed under two different --period values must not
    collide -- they address different dict keys in the same state file."""
    print("\ntest_period_month_and_day_buckets_are_independent")
    st = tmp_state()
    run(["claim", "--task", "t", "--block", "main", "--run-id", "d1"], st)
    run(["complete", "--task", "t", "--block", "main", "--run-id", "d1"], st)
    rc, out = run(["claim", "--task", "t", "--block", "main", "--run-id", "m1",
                   "--period", "month"], st)
    check("month claim unaffected by day-period COMPLETE", rc == 0, "got %s (%s)" % (rc, out))
    os.remove(st)


def test_ttl_exact_boundary():
    """The sibling test samples 29 and 31 minutes; pin the boundary itself."""
    print("\ntest_ttl_exact_boundary")
    st = tmp_state()
    write_state(st, {"2026-08-09": {"blockB": {
        "status": "IN_PROGRESS", "runId": "f1", "claimedAt": "2026-08-09T13:30:00Z",
        "notionPageId": None, "emailSentAt": None}}})
    rc, out = run_env(["claim", "--task", "t", "--block", "blockB", "--run-id", "f2",
                       "--ttl-min", "30"], st, {"ORA_SENTINEL_NOW": "2026-08-09T14:00:00Z"})
    check("age == TTL exactly -> reclaim (comparison is <, not <=)", rc == 0,
          "got %s (%s)" % (rc, out))
    os.remove(st)


# ------------------------------------ slot subcommand (added 2026-09-24)
# Incident: an ora-pr-land-watch run computed its SLOT with Git Bash
# `TZ=America/New_York date`, which this machine silently evaluates as UTC.
# At 16:51Z (12:51 EDT) it read "16:51 ET", claimed slot-15 instead of slot-12,
# and would have blocked the real 15:35 run had the claim not been released by
# hand. The fix moves slot arithmetic into the sentinel, which already owns the
# ET clock (zoneinfo + statutory-DST fallback).

PR_LAND_TIMES = "09:35,12:35,15:35,18:35,21:35"


def run_slot(times, now, extra_env=None):
    e = dict(os.environ)
    e["ORA_SENTINEL_NOW"] = now
    e.update(extra_env or {})
    p = subprocess.run([sys.executable, SCRIPT, "slot", "--times", times],
                       capture_output=True, text=True, env=e)
    try:
        return p.returncode, json.loads(p.stdout)
    except Exception:
        return p.returncode, {"_raw": p.stdout, "_err": p.stderr}


def test_slot_incident_utc_afternoon_is_et_noon_slot():
    print("\ntest_slot_incident_utc_afternoon_is_et_noon_slot")
    rc, out = run_slot(PR_LAND_TIMES, "2026-09-24T16:51:00Z")
    check("exit 0", rc == 0, "got %s (%s)" % (rc, out))
    check("16:51Z == 12:51 EDT -> slot-12 (not slot-15)", out.get("block") == "slot-12", str(out))
    check("reports ET date", out.get("etDate") == "2026-09-24", str(out.get("etDate")))
    check("reports ET wall time", out.get("etTime") == "12:51", str(out.get("etTime")))


def test_slot_boundary_is_inclusive():
    print("\ntest_slot_boundary_is_inclusive")
    rc, out = run_slot(PR_LAND_TIMES, "2026-09-24T19:35:00Z")   # 15:35 EDT exactly
    check("at HH:35 exactly the slot has started", out.get("block") == "slot-15", str(out))
    rc, out = run_slot(PR_LAND_TIMES, "2026-09-24T19:34:59Z")   # 15:34:59 EDT
    check("one second before -> previous slot", out.get("block") == "slot-12", str(out))


def test_slot_before_first_time_is_pre_label():
    print("\ntest_slot_before_first_time_is_pre_label")
    rc, out = run_slot(PR_LAND_TIMES, "2026-09-24T13:00:00Z")   # 09:00 EDT
    check("before 09:35 ET -> slot-pre09", out.get("block") == "slot-pre09", str(out))


def test_slot_late_evening_keys_to_et_date():
    print("\ntest_slot_late_evening_keys_to_et_date")
    rc, out = run_slot(PR_LAND_TIMES, "2026-08-10T02:30:00Z")   # 22:30 EDT Aug 9
    check("22:30 EDT -> slot-21", out.get("block") == "slot-21", str(out))
    check("ET date is 08-09, not UTC 08-10", out.get("etDate") == "2026-08-09", str(out))


def test_slot_winter_offset_and_fallback_agree():
    print("\ntest_slot_winter_offset_and_fallback_agree")
    now = "2026-01-15T17:40:00Z"                                 # 12:40 EST
    rc, a = run_slot(PR_LAND_TIMES, now)
    rc2, b = run_slot(PR_LAND_TIMES, now, {"ORA_SENTINEL_NO_ZONEINFO": "1"})
    check("EST: 17:40Z -> slot-12", a.get("block") == "slot-12", str(a))
    check("no-zoneinfo fallback agrees", b.get("block") == a.get("block"), "%s vs %s" % (a, b))


def test_slot_times_order_insensitive_and_validated():
    print("\ntest_slot_times_order_insensitive_and_validated")
    rc, out = run_slot("21:35,09:35,15:35,12:35,18:35", "2026-09-24T16:51:00Z")
    check("unsorted --times still -> slot-12", out.get("block") == "slot-12", str(out))
    rc, out = run_slot("9:35,25:00", "2026-09-24T16:51:00Z")
    check("invalid --times -> nonzero exit", rc != 0, "got %s (%s)" % (rc, out))
    check("invalid --times -> no block emitted", not out.get("block"), str(out))


def test_slot_rejects_out_of_range_and_duplicate_hours():
    print("\ntest_slot_rejects_out_of_range_and_duplicate_hours")
    for bad in ("09:35,25:00", "09:35,12:60", "09:35,", "09:05,09:35"):
        rc, out = run_slot(bad, "2026-09-24T16:51:00Z")
        check("%r -> exit 2" % bad, rc == 2, "got %s (%s)" % (rc, out))
        check("%r -> no block" % bad, not out.get("block"), str(out))


def test_slot_dst_days_fallback_parity():
    print("\ntest_slot_dst_days_fallback_parity")
    # 2026-03-08 spring-forward, 2026-11-01 fall-back: 09:40 local on both.
    for now, want in (("2026-03-08T13:40:00Z", "slot-09"), ("2026-11-01T14:40:00Z", "slot-09"),
                      ("2026-03-08T13:30:00Z", "slot-pre09")):
        rc, a = run_slot(PR_LAND_TIMES, now)
        rc2, b = run_slot(PR_LAND_TIMES, now, {"ORA_SENTINEL_NO_ZONEINFO": "1"})
        check("%s -> %s" % (now, want), a.get("block") == want, str(a))
        check("%s fallback agrees" % now, b.get("block") == want, str(b))


def test_claim_slot_times_resolves_and_stores_block():
    print("\ntest_claim_slot_times_resolves_and_stores_block")
    st = tmp_state()
    rc, out = run_env(["claim", "--task", "t", "--slot-times", PR_LAND_TIMES, "--run-id", "r1"],
                      st, {"ORA_SENTINEL_NOW": "2026-09-24T16:51:00Z"})
    check("exit 0 PROCEED", rc == 0 and out.get("decision") == "PROCEED", "got %s (%s)" % (rc, out))
    check("emits resolved block slot-12", out.get("block") == "slot-12", str(out.get("block")))
    check("stored under 2026-09-24/slot12 (canon key)", "slot12" in read_state(st).get("2026-09-24", {}),
          str(read_state(st)))
    rc, out = run_env(["claim", "--task", "t", "--slot-times", PR_LAND_TIMES, "--block", "slot-15",
                       "--run-id", "r2"], st, {"ORA_SENTINEL_NOW": "2026-09-24T16:52:00Z"})
    check("--slot-times overrides a wrong --block -> stands down on slot-12",
          rc == 11 and out.get("block") == "slot-12", "got %s (%s)" % (rc, out))
    os.remove(st)


def test_claim_slot_times_single_instant_near_midnight():
    """Reviewer finding: `slot` then `claim` as two calls can straddle midnight
    (slot-21 at 23:59:40, claim keyed to the next day). In-claim resolution uses
    one clock reading for both, so block and date always agree."""
    print("\ntest_claim_slot_times_single_instant_near_midnight")
    st = tmp_state()
    rc, out = run_env(["claim", "--task", "t", "--slot-times", PR_LAND_TIMES, "--run-id", "r"],
                      st, {"ORA_SENTINEL_NOW": "2026-09-25T03:59:40Z"})   # 23:59:40 EDT 09-24
    check("slot-21 keyed to 09-24", out.get("block") == "slot-21" and out.get("etDate") == "2026-09-24",
          str(out))
    os.remove(st)
    rc, out = run_env(["claim", "--task", "t", "--slot-times", PR_LAND_TIMES, "--run-id", "r"],
                      st, {"ORA_SENTINEL_NOW": "2026-09-25T04:00:05Z"})   # 00:00:05 EDT 09-25
    check("slot-pre09 keyed to 09-25", out.get("block") == "slot-pre09" and out.get("etDate") == "2026-09-25",
          str(out))
    os.remove(st)


def test_claim_without_block_or_slot_times_writes_nothing():
    print("\ntest_claim_without_block_or_slot_times_writes_nothing")
    st = tmp_state()
    rc, out = run_env(["claim", "--task", "t", "--run-id", "r"], st,
                      {"ORA_SENTINEL_NOW": "2026-09-24T16:51:00Z"})
    check("exit 2", rc == 2, "got %s (%s)" % (rc, out))
    check("no state file created", not os.path.exists(st), "state exists")
    rc, out = run_env(["claim", "--task", "t", "--slot-times", "9:35", "--run-id", "r"], st,
                      {"ORA_SENTINEL_NOW": "2026-09-24T16:51:00Z"})
    check("bad --slot-times -> exit 2", rc == 2, "got %s (%s)" % (rc, out))
    check("bad --slot-times -> no state file", not os.path.exists(st), "state exists")


def test_claim_slot_times_then_finalize_with_emitted_block():
    print("\ntest_claim_slot_times_then_finalize_with_emitted_block")
    st = tmp_state()
    env = {"ORA_SENTINEL_NOW": "2026-09-24T16:51:00Z"}
    rc, out = run_env(["claim", "--task", "t", "--slot-times", PR_LAND_TIMES, "--run-id", "r1"], st, env)
    block = out.get("block")
    rc, out = run_env(["complete", "--task", "t", "--block", block, "--run-id", "r1"], st,
                      {"ORA_SENTINEL_NOW": "2026-09-24T17:10:00Z"})
    check("complete with emitted block -> exit 0", rc == 0, "got %s (%s)" % (rc, out))
    check("record COMPLETE", read_state(st)["2026-09-24"]["slot12"]["status"] == "COMPLETE",
          str(read_state(st)))
    os.remove(st)


if __name__ == "__main__":
    print("block-sentinel.py -- entry-guard contract tests")
    test_virgin_claim_proceeds()
    test_already_complete_skips()
    test_in_progress_within_ttl_stands_down()
    test_in_progress_past_ttl_reclaims()
    test_ttl_boundary_is_exclusive_both_ways()
    test_blocks_and_dates_are_independent()
    test_complete_records_artifacts()
    test_et_date_not_utc_date()
    test_force_overrides_complete()
    test_corrupt_state_fails_open()
    test_status_is_read_only()
    test_old_dates_pruned()
    test_et_date_at_utc_boundary_is_deterministic()
    test_dst_fallback_matches_zoneinfo()
    test_concurrent_claims_grant_exactly_one()
    test_complete_without_claim_is_refused()
    test_adopt_allows_state_loss_reconvergence()
    test_fail_from_non_owner_is_refused()
    test_owner_may_fail_and_that_releases_the_claim()
    test_block_id_aliases_address_one_record()
    test_main_block_id_supported()
    test_period_month_reclaims_across_days_within_same_month()
    test_period_week_keys_to_iso_week()
    test_period_day_is_unaffected_default()
    test_period_month_and_day_buckets_are_independent()
    test_ttl_exact_boundary()
    test_slot_incident_utc_afternoon_is_et_noon_slot()
    test_slot_boundary_is_inclusive()
    test_slot_before_first_time_is_pre_label()
    test_slot_late_evening_keys_to_et_date()
    test_slot_winter_offset_and_fallback_agree()
    test_slot_times_order_insensitive_and_validated()
    test_slot_rejects_out_of_range_and_duplicate_hours()
    test_slot_dst_days_fallback_parity()
    test_claim_slot_times_resolves_and_stores_block()
    test_claim_slot_times_single_instant_near_midnight()
    test_claim_without_block_or_slot_times_writes_nothing()
    test_claim_slot_times_then_finalize_with_emitted_block()
    if _failures:
        print("\n%d FAILURE(S): %s" % (len(_failures), ", ".join(_failures)))
        sys.exit(1)
    print("\nALL block-sentinel tests passed.")
    sys.exit(0)
