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
    test_ttl_exact_boundary()
    if _failures:
        print("\n%d FAILURE(S): %s" % (len(_failures), ", ".join(_failures)))
        sys.exit(1)
    print("\nALL block-sentinel tests passed.")
    sys.exit(0)
