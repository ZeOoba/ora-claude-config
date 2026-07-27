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
if failures:
    print("FAILED: %d" % len(failures))
    raise SystemExit(1)
print("all passed")
