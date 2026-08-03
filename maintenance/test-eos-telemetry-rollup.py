"""Tests for eos-telemetry-rollup.load_records status discrimination.

Regression guard for the 2026-07-26 defect class: an empty result set that
cannot be distinguished from a failed read. load_records previously returned a
bare [] for a genuine first run, a corrupt file, and an I/O error alike, and
the caller printed "(no telemetry recorded yet)" for all three.

Run: python test-eos-telemetry-rollup.py
"""

import importlib.util
import json
import os
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SPEC = importlib.util.spec_from_file_location(
    "rollup", os.path.join(HERE, "eos-telemetry-rollup.py")
)
rollup = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(rollup)

failures = []


def check(name, cond, got=""):
    if cond:
        print("  PASS  %s" % name)
    else:
        print("  FAIL  %s  %s" % (name, got))
        failures.append(name)


def write(tmp, text, encoding="utf-8"):
    p = os.path.join(tmp, "lane-telemetry.jsonl")
    with open(p, "w", encoding=encoding) as fh:
        fh.write(text)
    return p


print("load_records status discrimination")

with tempfile.TemporaryDirectory() as tmp:
    # 1. absent — the ONLY legitimate empty
    recs, status, _ = rollup.load_records(os.path.join(tmp, "nope.jsonl"))
    check("absent file -> 'absent'", status == "absent", status)
    check("absent file -> no records", recs == [], recs)

    # 2. ok — clean read
    p = write(tmp, '{"lane":"L2"}\n{"lane":"L3"}\n')
    recs, status, _ = rollup.load_records(p)
    check("clean file -> 'ok'", status == "ok", status)
    check("clean file -> 2 records", len(recs) == 2, len(recs))

    # 3. corrupt — content present, nothing usable. Must NOT look like a first run.
    p = write(tmp, "not json at all\n{{{ broken\n")
    recs, status, detail = rollup.load_records(p)
    check("garbage file -> 'corrupt'", status == "corrupt", status)
    check("corrupt is distinguishable from absent", status != "absent", status)
    check("corrupt reports skipped count", "2" in detail, detail)

    # 4. genuinely empty file -> ok, not corrupt (no lines to skip)
    p = write(tmp, "")
    recs, status, _ = rollup.load_records(p)
    check("empty file -> 'ok'", status == "ok", status)

    # 5. partial corruption must not discard the good records
    p = write(tmp, '{"lane":"L2"}\ngarbage\n{"lane":"L5"}\n')
    recs, status, detail = rollup.load_records(p)
    check("mixed file keeps good records", len(recs) == 2, len(recs))
    check("mixed file status 'ok'", status == "ok", status)
    check("mixed file reports the skip", "1" in detail, detail)

    # 6. non-ASCII must survive (old encoding='ascii' mangled then dropped these)
    p = write(tmp, json.dumps({"lane": "L3", "note": "café — naïve"}) + "\n")
    recs, status, _ = rollup.load_records(p)
    check("non-ASCII line is retained", len(recs) == 1, len(recs))
    check("non-ASCII file -> 'ok'", status == "ok", status)

    # 7. non-dict JSON lines count as skipped, not as records
    p = write(tmp, '[1,2,3]\n"a string"\n')
    recs, status, detail = rollup.load_records(p)
    check("non-dict lines are not records", recs == [], recs)
    check("all-non-dict -> 'corrupt'", status == "corrupt", status)

print()
print("merge_sessions field merging (white-box)")

# The rollup's REPORT does not print merged `edits` or `files`, so the
# subprocess suite in hooks/tests/ structurally cannot cover them -- any
# mutation there survives. These fields are still part of a merged session's
# data and are read by ad-hoc analysis, so they are asserted directly here.


def rec(sid, **kw):
    d = {
        "schema": 2,
        "detectors": {"dispatch": ["Agent", "Task"]},
        "ts": "2026-07-25T12:00:00+00:00",
        "session_id": sid,
        "edits": 1,
        "files": [],
        "bash_test_ran": False,
        "task_dispatched": False,
        "lane_declared": False,
        "verification_seen": False,
    }
    d.update(kw)
    return d


# edits: MAX across re-emissions, never first- or last-write. A re-parse of a
# growing transcript reports >= the previous count, but a truncated re-parse
# must never be able to shrink the session.
sess, collapsed = rollup.merge_sessions([
    rec("s", edits=59), rec("s", edits=107), rec("s", edits=70),
])
check("edits merges to the max", sess[0]["edits"] == 107, sess[0]["edits"])
check("collapsed counts absorbed records", collapsed == 2, collapsed)

# files: union, sorted, de-duplicated.
sess, _ = rollup.merge_sessions([
    rec("s", files=["b.py", "a.py"]), rec("s", files=["a.py", "c.py"]),
])
check("files merge to a sorted union",
      sess[0]["files"] == ["a.py", "b.py", "c.py"], sess[0]["files"])

# The aliasing fix: a merged session must never share a list object with the
# input records, or appending to the output corrupts the source.
src = [rec("solo", files=["x.py"])]
sess, _ = rollup.merge_sessions(src)
sess[0]["files"].append("MUTATED")
check("single-record session does not alias the input list",
      src[0]["files"] == ["x.py"], src[0]["files"])

# merge_file_lists is TOTAL -- it may never raise, whatever is in the file.
for bad in ([1], [["nested"]], {"not": "a list"}, None, "string", [None, "ok.py"]):
    try:
        out = rollup.merge_file_lists(["a.py"], bad)
        ok = isinstance(out, list)
    except Exception as exc:
        ok = False
        out = "raised %s" % type(exc).__name__
    check("merge_file_lists survives %r" % (bad,), ok, out)

check("merge_file_lists keeps only strings",
      rollup.merge_file_lists(["a.py", 1], [None, "b.py"]) == ["a.py", "b.py"],
      rollup.merge_file_lists(["a.py", 1], [None, "b.py"]))

print()
print("merge-failure fallback (white-box)")

# merge_sessions is TOTAL for the dict records load_records yields, so no
# input file can reach the fallback branch -- the black-box suite structurally
# cannot cover it, and every mutation of it survives there. It is also the
# branch that exists to stop a silent blank report, so leaving it uncertified
# defeats its own purpose. Force the failure directly.

import contextlib
import io as _io
import sys as _sys


def run_main_with_broken_merge(records_json):
    """Run main() with merge_sessions forced to raise; return its stdout."""
    tmp = tempfile.mkdtemp(prefix="eos-rollup-fallback-")
    path = os.path.join(tmp, "lane-telemetry.jsonl")
    with _io.open(path, "w", encoding="ascii") as fh:
        fh.write(records_json)

    def boom(_records):
        raise RuntimeError("forced merge failure")

    original_merge = rollup.merge_sessions
    original_argv = _sys.argv
    rollup.merge_sessions = boom
    _sys.argv = ["eos-telemetry-rollup.py", path]
    buf = _io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            rollup.main()
    finally:
        rollup.merge_sessions = original_merge
        _sys.argv = original_argv
    return buf.getvalue()


TWO = (
    json.dumps({"schema": 2, "detectors": {"dispatch": ["Agent"]},
                "session_id": "s", "edits": 1, "files": [],
                "bash_test_ran": True, "task_dispatched": True,
                "lane_declared": True, "verification_seen": True}) + "\n"
) * 2

out = run_main_with_broken_merge(TWO)

# 1. It must say so. A silent degradation to raw records is the failure mode.
check("merge failure prints the loud banner", "SESSION MERGE FAILED" in out, out)
check("banner names the exception", "RuntimeError" in out, out)
check("banner warns the counts are unreliable", "unreliable" in out.lower(), out)

# 2. It must still produce the WHOLE report. Reverting the follow-on fix
#    (rec.get(CAPABILITY) -> rec[CAPABILITY]) KeyErrors mid-report and the
#    top-level handler truncates everything below the banner, exit 0 -- a
#    partial rebirth of the blank-report defect on the very path built to
#    prevent it. Assert the tail of the report survives.
for required in ("dispatch-capable cohort:", "blind-era backlog:",
                 "lane_declared:", "bash_test_ran:", "task_dispatched:",
                 "verification_seen:", "most-frequently-missing signal:"):
    check("fallback still prints %r" % required, required in out, out[-400:])

# 3. The fallback reports RAW records, so both re-emissions count as sessions.
#    That is the documented degradation -- pin it so a silent change is caught.
check("fallback counts raw records as sessions",
      "total coding sessions: 2" in out, out)
check("fallback reports 0 collapsed",
      "0 duplicate re-emission(s) collapsed" in out, out)

print()
if failures:
    print("FAILED: %d" % len(failures))
    raise SystemExit(1)
print("all passed")
