"""Tests for eos-telemetry-rollup.py cohort segmentation.

The rollup must not blend two incompatible populations. Records written
before the 2026-07-24 dispatch-detection fix carry task_dispatched=false
unconditionally -- the emitter could not see the real `Agent` tool name --
so counting them in the dispatch denominator reports a wrongly-low rate.

Cohort key, in priority order:
  1. `schema` >= 2 plus a `detectors.dispatch` list that still contains the
     required tool name -> capable.
  2. `schema` >= 2 with a dispatch detector that LOST the required name ->
     degraded. Excluded from the rate and reported loudly. This is the
     regression class the schema field exists to catch.
  3. No `schema` (already-written records) -> fall back to `ts` presence,
     the legacy proxy, so the ~766-record backlog stays classified blind.

Run: python test-eos-telemetry-rollup.py
Stdlib only. ASCII-only. Self-contained (creates its own temp dirs/files).
"""

import json
import os
import subprocess
import sys
import tempfile

# test lives in hooks/tests/ -> repo root is two levels up
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROLLUP = os.path.join(ROOT, "maintenance", "eos-telemetry-rollup.py")


def run_rollup(path):
    """Run the rollup as a subprocess. Returns (returncode, stdout, stderr)."""
    proc = subprocess.run(
        [sys.executable, ROLLUP, path],
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stdout, proc.stderr


def write_jsonl(records, extra_raw_lines=None):
    """Write records to a temp .jsonl and return its path."""
    tmp = tempfile.mkdtemp(prefix="eos-rollup-test-")
    path = os.path.join(tmp, "lane-telemetry.jsonl")
    with open(path, "w", encoding="ascii") as fh:
        for rec in records:
            fh.write(json.dumps(rec) + "\n")
        for raw in extra_raw_lines or []:
            fh.write(raw + "\n")
    return path


def capable_record(session_id, dispatched, **kw):
    """A post-fix record: schema 2 with an intact dispatch detector."""
    rec = {
        "schema": 2,
        "detectors": {"dispatch": ["Agent", "Task"]},
        "ts": "2026-07-25T12:00:00+00:00",
        "session_id": session_id,
        "edits": 1,
        "files": ["C:/proj/a.py"],
        "bash_test_ran": True,
        "task_dispatched": dispatched,
        "lane_declared": True,
        "verification_seen": True,
    }
    rec.update(kw)
    return rec


def legacy_ts_record(session_id, dispatched, **kw):
    """An already-written post-fix record: `ts` stamped, but no schema field.
    Must classify capable via the backward-compatible fallback."""
    rec = {
        "ts": "2026-07-24T18:00:00+00:00",
        "session_id": session_id,
        "edits": 1,
        "files": [],
        "bash_test_ran": True,
        "task_dispatched": dispatched,
        "lane_declared": True,
        "verification_seen": False,
    }
    rec.update(kw)
    return rec


def blind_record(session_id, **kw):
    """A blind-era record: no schema, no ts. task_dispatched is meaningless."""
    rec = {
        "session_id": session_id,
        "edits": 3,
        "files": [],
        "bash_test_ran": False,
        "task_dispatched": False,
        "lane_declared": True,
        "verification_seen": True,
    }
    rec.update(kw)
    return rec


def field(out, label):
    """Return the text after 'label:' on the matching stdout line."""
    for line in out.splitlines():
        if line.startswith(label + ":"):
            return line.split(":", 1)[1].strip()
    raise AssertionError("no %r line in output:\n%s" % (label, out))


def test_schema2_records_form_capable_cohort():
    path = write_jsonl([
        capable_record("s1", True),
        capable_record("s2", False),
    ])
    rc, out, err = run_rollup(path)
    assert rc == 0, "expected exit 0, got %s (stderr=%s)" % (rc, err)
    assert field(out, "dispatch-capable cohort") == "2", out
    assert field(out, "blind-era backlog") == "0", out
    assert "1/2 capable" in field(out, "task_dispatched"), out
    print("PASS test_schema2_records_form_capable_cohort")


def test_ts_fallback_classifies_legacy_postfix_records():
    """Records already on disk carry `ts` but no `schema`. They predate the
    version field and must still land in the capable cohort."""
    path = write_jsonl([
        legacy_ts_record("old1", True),
        legacy_ts_record("old2", False),
    ])
    rc, out, err = run_rollup(path)
    assert rc == 0, "expected exit 0, got %s (stderr=%s)" % (rc, err)
    assert field(out, "dispatch-capable cohort") == "2", (
        "ts-only records must fall back to capable: %s" % out
    )
    assert field(out, "blind-era backlog") == "0", out
    assert "1/2 capable" in field(out, "task_dispatched"), out
    print("PASS test_ts_fallback_classifies_legacy_postfix_records")


def test_blind_era_records_excluded_from_dispatch_rate():
    """The whole point: blind-era false negatives must not enter the
    denominator and depress the reported dispatch rate."""
    path = write_jsonl(
        [capable_record("new1", True)] + [blind_record("b%d" % i) for i in range(9)]
    )
    rc, out, err = run_rollup(path)
    assert rc == 0, "expected exit 0, got %s (stderr=%s)" % (rc, err)
    assert field(out, "total coding sessions") == "10", out
    assert field(out, "dispatch-capable cohort") == "1", out
    assert field(out, "blind-era backlog") == "9", out
    dispatched = field(out, "task_dispatched")
    assert "1/1 capable" in dispatched, dispatched
    assert "100.0%" in dispatched, (
        "blind records must not dilute the rate to 10%%: %s" % dispatched
    )
    print("PASS test_blind_era_records_excluded_from_dispatch_rate")


def test_regressed_detector_is_not_counted_capable():
    """THE latent-weakness test. A record that stamps schema>=2 AND `ts` but
    whose dispatch detector lost the required tool name is NOT capable --
    it must not slip through on the `ts` proxy. Silently trusting it is the
    exact failure the schema field was added to stop."""
    path = write_jsonl([
        capable_record("good", True),
        # DISPATCH_TOOLS regressed: "Agent" dropped. `ts` is still stamped.
        capable_record("bad1", False, detectors={"dispatch": ["Task"]}),
        capable_record("bad2", False, detectors={"dispatch": ["Task"]}),
    ])
    rc, out, err = run_rollup(path)
    assert rc == 0, "expected exit 0, got %s (stderr=%s)" % (rc, err)
    assert field(out, "dispatch-capable cohort") == "1", (
        "regressed-detector records must be excluded from capable: %s" % out
    )
    assert field(out, "detector-regressed sessions") == "2", out
    assert "1/1 capable" in field(out, "task_dispatched"), out
    assert "WARNING" in out, "a detector regression must be reported loudly:\n%s" % out
    print("PASS test_regressed_detector_is_not_counted_capable")


def test_schema2_without_detectors_block_is_capable():
    """Forward-compat: the schema version is the primary key. A future record
    that bumps schema but omits the detectors block is trusted."""
    rec = capable_record("s1", True)
    del rec["detectors"]
    path = write_jsonl([rec])
    rc, out, err = run_rollup(path)
    assert rc == 0, "expected exit 0, got %s (stderr=%s)" % (rc, err)
    assert field(out, "dispatch-capable cohort") == "1", out
    assert field(out, "detector-regressed sessions") == "0", out
    print("PASS test_schema2_without_detectors_block_is_capable")


def test_non_dispatch_signals_span_all_records():
    """lane_declared / bash_test_ran / verification_seen were never blind, so
    they report over the full population, not the capable cohort."""
    path = write_jsonl([
        capable_record("n1", True),
        blind_record("b1", lane_declared=True),
        blind_record("b2", lane_declared=False),
        blind_record("b3", lane_declared=False),
    ])
    rc, out, err = run_rollup(path)
    assert rc == 0, "expected exit 0, got %s (stderr=%s)" % (rc, err)
    assert "2/4 all" in field(out, "lane_declared"), field(out, "lane_declared")
    print("PASS test_non_dispatch_signals_span_all_records")


def test_all_blind_reports_dispatch_unmeasurable():
    """With a zero-size capable cohort the dispatch rate is undefined -- the
    rollup must say so rather than print a fabricated 0.0%."""
    path = write_jsonl([blind_record("b%d" % i) for i in range(5)])
    rc, out, err = run_rollup(path)
    assert rc == 0, "expected exit 0, got %s (stderr=%s)" % (rc, err)
    assert field(out, "dispatch-capable cohort") == "0", out
    dispatched = field(out, "task_dispatched")
    assert "n/a" in dispatched, (
        "a 0-record cohort must report n/a, not 0.0%%: %s" % dispatched
    )
    assert "most-frequently-missing signal" in out, out
    assert "task_dispatched" not in field(out, "most-frequently-missing signal"), (
        "an unmeasurable signal must not win most-missing: %s" % out
    )
    print("PASS test_all_blind_reports_dispatch_unmeasurable")


def test_most_missing_compares_rates_not_raw_absences():
    """Denominators differ between cohorts, so most-missing must rank by rate.
    Here dispatch is 0/1 (0%) while lane_declared is 3/4 (75%) -- ranking by
    raw absence count would wrongly crown lane_declared (1 absent vs 1)."""
    path = write_jsonl([
        capable_record("n1", False, lane_declared=True, bash_test_ran=True,
                       verification_seen=True),
        blind_record("b1", lane_declared=False, bash_test_ran=True,
                     verification_seen=True),
        blind_record("b2", lane_declared=True, bash_test_ran=True,
                     verification_seen=True),
        blind_record("b3", lane_declared=True, bash_test_ran=True,
                     verification_seen=True),
    ])
    rc, out, err = run_rollup(path)
    assert rc == 0, "expected exit 0, got %s (stderr=%s)" % (rc, err)
    assert "task_dispatched" in field(out, "most-frequently-missing signal"), (
        "0%% dispatch must outrank 75%% lane_declared: %s" % out
    )
    print("PASS test_most_missing_compares_rates_not_raw_absences")


def test_duplicate_session_records_collapse_to_one_session():
    """SessionEnd fires on every resume/clear/compaction and re-parses the
    WHOLE transcript, appending a fresh record each time. Three records for
    one session are one session, not three."""
    path = write_jsonl([
        capable_record("s1", False, edits=5),
        capable_record("s1", False, edits=9),
        capable_record("s1", False, edits=12),
    ])
    rc, out, err = run_rollup(path)
    assert rc == 0, "expected exit 0, got %s (stderr=%s)" % (rc, err)
    assert field(out, "total coding sessions") == "1", (
        "3 re-emissions of one session must count as 1 session: %s" % out
    )
    assert field(out, "total records").startswith("3"), (
        "the raw record count must still be reported: %s" % out
    )
    assert field(out, "dispatch-capable cohort") == "1", out
    print("PASS test_duplicate_session_records_collapse_to_one_session")


def test_duplicates_do_not_inflate_dispatch_denominator():
    """A long session that re-emits 3x must not weigh 3x in the rate. Without
    dedupe this reads 3/4 = 75%; the true figure is 1/2 = 50%."""
    path = write_jsonl([
        capable_record("long", True),
        capable_record("long", True),
        capable_record("long", True),
        capable_record("short", False),
    ])
    rc, out, err = run_rollup(path)
    assert rc == 0, "expected exit 0, got %s (stderr=%s)" % (rc, err)
    dispatched = field(out, "task_dispatched")
    assert "1/2 capable" in dispatched, (
        "re-emissions must not be weighted: %s" % dispatched
    )
    assert "50.0%" in dispatched, dispatched
    print("PASS test_duplicates_do_not_inflate_dispatch_denominator")


def test_stale_partial_superseded_by_later_signal():
    """An early SessionEnd fire snapshots the transcript BEFORE a dispatch
    happens, writing task_dispatched=false. That stale partial must not
    outvote the later record that saw the dispatch. These signals are
    existential ('did this session ever X'), so the merge is a union."""
    path = write_jsonl([
        capable_record("s1", False, edits=2, lane_declared=False,
                       bash_test_ran=False, verification_seen=False),
        capable_record("s1", True, edits=30, lane_declared=True,
                       bash_test_ran=True, verification_seen=True),
    ])
    rc, out, err = run_rollup(path)
    assert rc == 0, "expected exit 0, got %s (stderr=%s)" % (rc, err)
    assert "1/1 capable" in field(out, "task_dispatched"), (
        "a later record observing dispatch must win over the stale false: %s" % out
    )
    assert "1/1 all" in field(out, "lane_declared"), out
    assert "1/1 all" in field(out, "bash_test_ran"), out
    assert "1/1 all" in field(out, "verification_seen"), out
    print("PASS test_stale_partial_superseded_by_later_signal")


def test_merge_is_order_independent():
    """The union must not depend on which re-emission landed last. A True
    observed in an EARLIER record survives a later False.

    Every unioned signal is asserted here, not just task_dispatched. Pinning
    dispatch alone leaves last-write-wins undetected on the other three: they
    are the only signals that flow through the UNION_SIGNALS loop, since
    task_dispatched is merged separately under a capability guard. Ordered
    True-then-False deliberately -- last-write-wins agrees with union when
    the True lands last, so that ordering proves nothing."""
    recs = [
        capable_record("s1", True, edits=30, lane_declared=True,
                       bash_test_ran=True, verification_seen=True),
        capable_record("s1", False, edits=2, lane_declared=False,
                       bash_test_ran=False, verification_seen=False),
    ]
    rc, out, err = run_rollup(write_jsonl(recs))
    assert rc == 0, "expected exit 0, got %s (stderr=%s)" % (rc, err)
    assert "1/1 capable" in field(out, "task_dispatched"), (
        "a true observed in an EARLIER record must survive a later false: %s" % out
    )
    for signal in ("lane_declared", "bash_test_ran", "verification_seen"):
        value = field(out, signal)
        assert "1/1 all" in value, (
            "%s must union, not take the last record's value: %s" % (signal, value)
        )
    print("PASS test_merge_is_order_independent")


def test_session_capability_is_the_best_of_its_records():
    """A session spanning the 2026-07-24 fix has a blind record and a capable
    one. It is one capable session -- not one of each."""
    path = write_jsonl([
        blind_record("spanning"),
        capable_record("spanning", True),
    ])
    rc, out, err = run_rollup(path)
    assert rc == 0, "expected exit 0, got %s (stderr=%s)" % (rc, err)
    assert field(out, "total coding sessions") == "1", out
    assert field(out, "dispatch-capable cohort") == "1", out
    assert field(out, "blind-era backlog") == "0", (
        "a session with any capable record is not blind-era: %s" % out
    )
    print("PASS test_session_capability_is_the_best_of_its_records")


def test_distinct_sessions_are_not_merged():
    """Regression guard: dedupe must key on session_id only, never collapse
    genuinely separate sessions that happen to share field values."""
    path = write_jsonl([
        capable_record("a", True),
        capable_record("b", True),
        capable_record("c", False),
    ])
    rc, out, err = run_rollup(path)
    assert rc == 0, "expected exit 0, got %s (stderr=%s)" % (rc, err)
    assert field(out, "total coding sessions") == "3", out
    assert "2/3 capable" in field(out, "task_dispatched"), out
    print("PASS test_distinct_sessions_are_not_merged")


def test_records_without_session_id_stay_separate():
    """A record with no session_id has no merge key. It must be kept as its
    own session, never collapsed with every other keyless record."""
    r1 = capable_record("x", True)
    del r1["session_id"]
    r2 = capable_record("y", False)
    del r2["session_id"]
    path = write_jsonl([r1, r2])
    rc, out, err = run_rollup(path)
    assert rc == 0, "expected exit 0, got %s (stderr=%s)" % (rc, err)
    assert field(out, "total coding sessions") == "2", (
        "keyless records must not collapse into one: %s" % out
    )
    print("PASS test_records_without_session_id_stay_separate")


def test_duplication_does_not_inflate_non_dispatch_numerators():
    """The numerator must be counted over SESSIONS, exactly like the
    denominator. Counting a unioned signal over raw records while dividing by
    sessions prints impossible rates -- 3 duplicate records of one
    lane-declaring session reported 'lane_declared: 300.0% (3/1 all)'."""
    path = write_jsonl([
        capable_record("s1", False, lane_declared=True, bash_test_ran=True,
                       verification_seen=True),
        capable_record("s1", False, lane_declared=True, bash_test_ran=True,
                       verification_seen=True),
        capable_record("s1", False, lane_declared=True, bash_test_ran=True,
                       verification_seen=True),
    ])
    rc, out, err = run_rollup(path)
    assert rc == 0, "expected exit 0, got %s (stderr=%s)" % (rc, err)
    for signal in ("lane_declared", "bash_test_ran", "verification_seen"):
        value = field(out, signal)
        assert "1/1 all" in value, (
            "%s numerator must be counted over sessions: %s" % (signal, value)
        )
        assert "100.0%" in value, value
    print("PASS test_duplication_does_not_inflate_non_dispatch_numerators")


def test_collapsed_count_is_reported_accurately():
    """The one number unique to this feature. 5 records over 2 sessions is
    exactly 3 collapsed; an unasserted counter can drift silently."""
    path = write_jsonl([
        capable_record("a", True),
        capable_record("a", True),
        capable_record("a", True),
        capable_record("b", False),
        capable_record("b", False),
    ])
    rc, out, err = run_rollup(path)
    assert rc == 0, "expected exit 0, got %s (stderr=%s)" % (rc, err)
    assert field(out, "total coding sessions") == "2", out
    assert field(out, "total records") == "5 (3 duplicate re-emission(s) collapsed)", (
        "collapsed count must be exact: %s" % field(out, "total records")
    )
    print("PASS test_collapsed_count_is_reported_accurately")


def test_untrusted_record_cannot_supply_the_dispatch_verdict():
    """A degraded record's task_dispatched 'is not evidence of anything'. If
    the CAPABLE record for a session saw no dispatch, a regressed-detector
    sibling claiming true must NOT make the session count as dispatched --
    that manufactures the exact signal this rollup exists to measure."""
    path = write_jsonl([
        capable_record("p", False),
        capable_record("p", True, detectors={"dispatch": ["Task"]}),
    ])
    rc, out, err = run_rollup(path)
    assert rc == 0, "expected exit 0, got %s (stderr=%s)" % (rc, err)
    dispatched = field(out, "task_dispatched")
    assert "0/1 capable" in dispatched, (
        "an untrusted record must not supply the verdict: %s" % dispatched
    )
    assert "0.0%" in dispatched, dispatched
    print("PASS test_untrusted_record_cannot_supply_the_dispatch_verdict")


def test_untrusted_record_cannot_SEED_the_dispatch_verdict():
    """The capability guard exists TWICE -- once where a session is first
    seeded from a record, once where a later record merges in. Placing the
    untrusted record second exercises only the merge half. Here it lands
    FIRST, so the seed half is what must reject it: without that guard the
    untrusted True becomes the session's opening verdict and the later
    capable False cannot pull it back down, reinstating the exact defect
    this guard was added to close."""
    path = write_jsonl([
        capable_record("p", True, detectors={"dispatch": ["Task"]}),
        capable_record("p", False),
    ])
    rc, out, err = run_rollup(path)
    assert rc == 0, "expected exit 0, got %s (stderr=%s)" % (rc, err)
    dispatched = field(out, "task_dispatched")
    assert "0/1 capable" in dispatched, (
        "an untrusted record must not SEED the verdict: %s" % dispatched
    )
    assert "0.0%" in dispatched, dispatched
    print("PASS test_untrusted_record_cannot_SEED_the_dispatch_verdict")


def test_capable_true_survives_a_later_untrusted_record():
    """Mirror image of the guard: gating the union on capability must not
    throw away a REAL dispatch. A capable record saw it; a degraded sibling
    arriving later must leave that verdict standing."""
    path = write_jsonl([
        capable_record("p", True),
        capable_record("p", False, detectors={"dispatch": ["Task"]}),
    ])
    rc, out, err = run_rollup(path)
    assert rc == 0, "expected exit 0, got %s (stderr=%s)" % (rc, err)
    assert "1/1 capable" in field(out, "task_dispatched"), (
        "the capability guard must not discard a trustworthy True: %s" % out
    )
    print("PASS test_capable_true_survives_a_later_untrusted_record")


def test_blind_record_cannot_supply_the_dispatch_verdict():
    """Same rule for the blind era, where task_dispatched is uniformly
    meaningless rather than merely suspect."""
    path = write_jsonl([
        capable_record("p", False),
        blind_record("p", task_dispatched=True),
    ])
    rc, out, err = run_rollup(path)
    assert rc == 0, "expected exit 0, got %s (stderr=%s)" % (rc, err)
    assert "0/1 capable" in field(out, "task_dispatched"), out
    print("PASS test_blind_record_cannot_supply_the_dispatch_verdict")


def test_malformed_files_cannot_blank_the_report():
    """FAIL-LOUD invariant. merge_sessions runs before the first print, so an
    exception there exited 0 having printed ZERO bytes -- no numbers, no
    banner, indistinguishable from 'nothing to report'. Two records whose
    `files` lists cannot be unioned (unorderable / unhashable entries) must
    still produce a full report."""
    path = write_jsonl([
        capable_record("s", True, files=["a.py"]),
        capable_record("s", True, files=[1]),
        capable_record("t", False, files=[["nested"]]),
        capable_record("t", False, files={"not": "a list"}),
    ])
    rc, out, err = run_rollup(path)
    assert rc == 0, "expected exit 0, got %s (stderr=%s)" % (rc, err)
    assert out.strip(), "a malformed `files` entry must not blank the report"
    assert field(out, "total coding sessions") == "2", out
    assert "1/2 capable" in field(out, "task_dispatched"), out
    print("PASS test_malformed_files_cannot_blank_the_report")


def test_malformed_scalar_fields_cannot_blank_the_report():
    """Same invariant across the other merged fields. lane-telemetry.jsonl is
    append-only and hand-editable; no field type may take the report down."""
    path = write_jsonl([
        capable_record("s", True, edits="lots"),
        capable_record("s", True, edits=None),
        # session_id is positional in the helper, so override it after build.
        dict(capable_record("u", False), session_id=17),
        dict(capable_record("u2", False), session_id=None),
        capable_record("v", False, detectors="not-a-dict"),
    ])
    rc, out, err = run_rollup(path)
    assert rc == 0, "expected exit 0, got %s (stderr=%s)" % (rc, err)
    assert out.strip(), "a malformed scalar must not blank the report"
    assert field(out, "total coding sessions"), out
    print("PASS test_malformed_scalar_fields_cannot_blank_the_report")


def test_malformed_lines_skipped():
    path = write_jsonl(
        [capable_record("s1", True)],
        extra_raw_lines=["not json at all", "", "   ", "[1,2,3]", "null"],
    )
    rc, out, err = run_rollup(path)
    assert rc == 0, "expected exit 0, got %s (stderr=%s)" % (rc, err)
    assert field(out, "total coding sessions") == "1", (
        "malformed and non-dict lines must be skipped: %s" % out
    )
    print("PASS test_malformed_lines_skipped")


def test_missing_file_exits_zero():
    tmp = tempfile.mkdtemp(prefix="eos-rollup-test-")
    rc, out, err = run_rollup(os.path.join(tmp, "nope.jsonl"))
    assert rc == 0, "missing file must exit 0, got %s" % rc
    assert "no telemetry recorded yet" in out, out
    print("PASS test_missing_file_exits_zero")


def test_garbage_file_exits_zero():
    """Fail-open invariant: nothing in this file may make the rollup non-zero."""
    tmp = tempfile.mkdtemp(prefix="eos-rollup-test-")
    path = os.path.join(tmp, "garbage.jsonl")
    with open(path, "w", encoding="ascii") as fh:
        fh.write("\x00\x01 not remotely json \x02\n" * 20)
    rc, out, err = run_rollup(path)
    assert rc == 0, "garbage input must still exit 0, got %s (stderr=%s)" % (rc, err)
    print("PASS test_garbage_file_exits_zero")


if __name__ == "__main__":
    test_schema2_records_form_capable_cohort()
    test_ts_fallback_classifies_legacy_postfix_records()
    test_blind_era_records_excluded_from_dispatch_rate()
    test_regressed_detector_is_not_counted_capable()
    test_schema2_without_detectors_block_is_capable()
    test_non_dispatch_signals_span_all_records()
    test_all_blind_reports_dispatch_unmeasurable()
    test_most_missing_compares_rates_not_raw_absences()
    test_duplicate_session_records_collapse_to_one_session()
    test_duplicates_do_not_inflate_dispatch_denominator()
    test_stale_partial_superseded_by_later_signal()
    test_merge_is_order_independent()
    test_session_capability_is_the_best_of_its_records()
    test_distinct_sessions_are_not_merged()
    test_records_without_session_id_stay_separate()
    test_duplication_does_not_inflate_non_dispatch_numerators()
    test_collapsed_count_is_reported_accurately()
    test_untrusted_record_cannot_supply_the_dispatch_verdict()
    test_untrusted_record_cannot_SEED_the_dispatch_verdict()
    test_capable_true_survives_a_later_untrusted_record()
    test_blind_record_cannot_supply_the_dispatch_verdict()
    test_malformed_files_cannot_blank_the_report()
    test_malformed_scalar_fields_cannot_blank_the_report()
    test_malformed_lines_skipped()
    test_missing_file_exits_zero()
    test_garbage_file_exits_zero()
    print("ALL TELEMETRY ROLLUP TESTS PASS")
