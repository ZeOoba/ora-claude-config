"""Tests for maintenance/eos-telemetry-rollup.py.

WHY THIS FILE EXISTS: the 2026-07-24 dispatch-detection fix shipped only its
EMITTER half. eos-telemetry.py started matching the real `Agent` tool name and
started stamping a `ts` field whose documented purpose is "to segment records
written after the 2026-07-24 dispatch-detection fix from the blind-era backlog,
which is uniformly task_dispatched=false and would otherwise depress the blended
rate indefinitely" -- but the CONSUMER (the rollup) was never taught to read
`ts`. It blended 766 structurally-blind records with 50 valid ones and reported
task_dispatched at 2.2% when the real post-fix rate was 38.0%. The rollup had no
tests at all, which is why a half-shipped fix passed unnoticed.

Lives in hooks/tests/ (not maintenance/_tests/) deliberately:
git-prepush-hook-tests-gate.py auto-discovers ONLY hooks/tests/test-*.py, so a
test placed under maintenance/_tests/ would never gate anything.

Run: python test-eos-telemetry-rollup.py
Stdlib only. ASCII-only. Self-contained (creates its own temp dirs/files).
"""

import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # repo root
ROLLUP = os.path.join(HERE, "maintenance", "eos-telemetry-rollup.py")

POST_FIX_TS = "2026-07-24T17:00:00+00:00"


def run_rollup(path):
    """Run the rollup as a subprocess against an explicit jsonl path."""
    proc = subprocess.run(
        [sys.executable, ROLLUP, path],
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stdout, proc.stderr


def rec(ts=None, lane=False, test=False, dispatch=False, verify=False):
    """One telemetry record. ts=None simulates a blind-era (pre-fix) record."""
    r = {
        "session_id": "s",
        "edits": 1,
        "files": ["x.py"],
        "bash_test_ran": test,
        "task_dispatched": dispatch,
        "lane_declared": lane,
        "verification_seen": verify,
        "override_used": False,
        "override_reason": None,
        "override_at": None,
    }
    if ts is not None:
        r["ts"] = ts
    return r


def write_fixture(records):
    tmp = tempfile.mkdtemp(prefix="eos-rollup-test-")
    path = os.path.join(tmp, "lane-telemetry.jsonl")
    with open(path, "w", encoding="ascii") as fh:
        for r in records:
            fh.write(json.dumps(r) + "\n")
    return path


def line_for(out, prefix):
    """The single output line starting with prefix (asserts exactly one)."""
    hits = [ln for ln in out.splitlines() if ln.strip().startswith(prefix)]
    assert len(hits) == 1, "expected exactly 1 line starting %r, got %r" % (prefix, hits)
    return hits[0]


def test_dispatch_rate_excludes_blind_era():
    """THE BUG: task_dispatched must be measured over post-fix records only.

    10 blind-era (dispatch structurally false) + 4 post-fix (2 dispatched).
    Blended = 2/14 = 14.3% (wrong). Post-fix cohort = 2/4 = 50.0% (right).
    """
    records = [rec() for _ in range(10)]
    records += [
        rec(ts=POST_FIX_TS, dispatch=True),
        rec(ts=POST_FIX_TS, dispatch=True),
        rec(ts=POST_FIX_TS, dispatch=False),
        rec(ts=POST_FIX_TS, dispatch=False),
    ]
    path = write_fixture(records)
    rc, out, err = run_rollup(path)
    assert rc == 0, "expected exit 0, got %s (stderr=%s)" % (rc, err)

    line = line_for(out, "task_dispatched")
    assert "50.0%" in line, "expected post-fix rate 50.0%%, got: %r" % line
    assert "14.3%" not in line, "blended blind-era rate leaked into report: %r" % line
    assert "2/4" in line, "expected the post-fix cohort denominator 2/4, got: %r" % line
    print("PASS test_dispatch_rate_excludes_blind_era")


def test_full_corpus_signals_use_all_records():
    """Signals that were ALWAYS validly instrumented keep the full corpus.

    Discarding 766 valid observations would needlessly lose precision, so only
    task_dispatched is cohort-restricted. lane_declared True in 7 of 10
    blind-era and 0 of 4 post-fix: full corpus = 7/14 = 50.0%; a post-fix-only
    reading would be 0.0%.
    """
    records = [rec(lane=True) for _ in range(7)]
    records += [rec(lane=False) for _ in range(3)]
    records += [rec(ts=POST_FIX_TS, lane=False) for _ in range(4)]
    path = write_fixture(records)
    rc, out, err = run_rollup(path)
    assert rc == 0, "expected exit 0, got %s (stderr=%s)" % (rc, err)

    line = line_for(out, "lane_declared")
    assert "50.0%" in line, "expected full-corpus 50.0%%, got: %r" % line
    assert "7/14" in line, "expected full-corpus denominator 7/14, got: %r" % line
    print("PASS test_full_corpus_signals_use_all_records")


def test_no_post_fix_records_reports_unavailable():
    """All-blind-era corpus must NOT print a misleading 0.0% for dispatch."""
    path = write_fixture([rec() for _ in range(5)])
    rc, out, err = run_rollup(path)
    assert rc == 0, "expected exit 0, got %s (stderr=%s)" % (rc, err)

    line = line_for(out, "task_dispatched")
    assert "0.0%" not in line, (
        "all-blind-era corpus must not report a 0.0%% dispatch rate as if real: %r" % line)
    assert "n/a" in line.lower(), "expected an explicit no-data marker, got: %r" % line
    print("PASS test_no_post_fix_records_reports_unavailable")


def test_cohort_sizes_are_disclosed():
    """The report must state how many records fall in each cohort -- silent
    truncation of 766 records would read as 'we measured everything'."""
    records = [rec() for _ in range(10)] + [rec(ts=POST_FIX_TS) for _ in range(4)]
    path = write_fixture(records)
    rc, out, err = run_rollup(path)
    assert rc == 0, "expected exit 0, got %s (stderr=%s)" % (rc, err)
    low = out.lower()
    assert "10" in out and "4" in out, "cohort sizes not disclosed: %r" % out
    assert "blind" in low or "pre-fix" in low or "legacy" in low, (
        "blind-era cohort not labeled in report: %r" % out)
    print("PASS test_cohort_sizes_are_disclosed")


def test_has_ts_edge_shapes_classified_as_blind_era():
    """has_ts() is the load-bearing discriminator, so pin its edge contract.

    A null / empty / whitespace / non-string `ts` is NOT a valid post-fix
    stamp and must fall to the blind-era cohort even when the record claims
    task_dispatched=true. This direction is deliberate: it under-states rather
    than over-states the dispatch rate, so a malformed or tampered record can
    never inflate the metric. The real emitter always writes a non-empty ISO
    string, so these shapes should not occur -- that is exactly why they need
    a test rather than trust.
    """
    records = [
        rec(dispatch=True),                    # no ts key at all
        {"task_dispatched": True, "ts": None},
        {"task_dispatched": True, "ts": ""},
        {"task_dispatched": True, "ts": "   "},
        {"task_dispatched": True, "ts": 1753380000},
        rec(ts=POST_FIX_TS, dispatch=True),    # the only valid post-fix record
    ]
    path = write_fixture(records)
    rc, out, err = run_rollup(path)
    assert rc == 0, "expected exit 0, got %s (stderr=%s)" % (rc, err)

    line = line_for(out, "task_dispatched")
    assert "1/1" in line, (
        "only the validly-stamped record belongs to the post-fix cohort: %r" % line)
    assert "100.0%" in line, line
    print("PASS test_has_ts_edge_shapes_classified_as_blind_era")


def test_most_missing_not_skewed_by_blind_era():
    """most-frequently-missing must not name task_dispatched purely because of
    blind-era absences. Here post-fix dispatch is 100% while bash_test_ran is
    the genuinely weakest signal."""
    records = [rec(lane=True, test=True, verify=True) for _ in range(10)]
    records += [rec(ts=POST_FIX_TS, lane=True, test=False, dispatch=True, verify=True)
                for _ in range(4)]
    path = write_fixture(records)
    rc, out, err = run_rollup(path)
    assert rc == 0, "expected exit 0, got %s (stderr=%s)" % (rc, err)

    line = line_for(out, "most-frequently-missing")
    assert "task_dispatched" not in line, (
        "most-missing skewed by blind-era dispatch absences: %r" % line)
    assert "bash_test_ran" in line, "expected bash_test_ran as weakest signal: %r" % line
    print("PASS test_most_missing_not_skewed_by_blind_era")


def test_empty_file_graceful():
    path = write_fixture([])
    rc, out, err = run_rollup(path)
    assert rc == 0, "expected exit 0, got %s (stderr=%s)" % (rc, err)
    assert "no telemetry" in out.lower(), out
    print("PASS test_empty_file_graceful")


def test_missing_file_graceful():
    tmp = tempfile.mkdtemp(prefix="eos-rollup-test-")
    rc, out, err = run_rollup(os.path.join(tmp, "does-not-exist.jsonl"))
    assert rc == 0, "expected exit 0, got %s (stderr=%s)" % (rc, err)
    assert "no telemetry" in out.lower(), out
    print("PASS test_missing_file_graceful")


def test_malformed_lines_skipped():
    tmp = tempfile.mkdtemp(prefix="eos-rollup-test-")
    path = os.path.join(tmp, "lane-telemetry.jsonl")
    with open(path, "w", encoding="ascii") as fh:
        fh.write("not json\n")
        fh.write(json.dumps(rec(ts=POST_FIX_TS, dispatch=True)) + "\n")
        fh.write("{broken\n")
    rc, out, err = run_rollup(path)
    assert rc == 0, "expected exit 0, got %s (stderr=%s)" % (rc, err)
    line = line_for(out, "task_dispatched")
    assert "100.0%" in line, "expected 1/1 post-fix dispatch, got: %r" % line
    print("PASS test_malformed_lines_skipped")


if __name__ == "__main__":
    test_dispatch_rate_excludes_blind_era()
    test_full_corpus_signals_use_all_records()
    test_no_post_fix_records_reports_unavailable()
    test_has_ts_edge_shapes_classified_as_blind_era()
    test_cohort_sizes_are_disclosed()
    test_most_missing_not_skewed_by_blind_era()
    test_empty_file_graceful()
    test_missing_file_graceful()
    test_malformed_lines_skipped()
    print("ALL TELEMETRY ROLLUP TESTS PASS")
