"""ORA Claude Code reliability telemetry -- rollup report.

Reads lane-telemetry.jsonl and prints a short summary: total coding sessions
and the share that declared a lane, ran a test, and dispatched a subagent,
plus the single most-frequently-missing reliability signal. Handles an empty
or missing file gracefully. Always exits 0.

COHORT SEGMENTATION (added 2026-07-25): eos-telemetry.py could not detect
subagent dispatch before 2026-07-24 -- DISPATCH_TOOLS did not match the real
`Agent` tool name, so every record written before that fix carries
task_dispatched=false regardless of what the session actually did. The fix also
began stamping a `ts` field for exactly this reason ("required to segment
records written after the 2026-07-24 dispatch-detection fix from the blind-era
backlog, which is uniformly task_dispatched=false and would otherwise depress
the blended rate indefinitely"), but this consumer was never taught to read it.
Blending the cohorts reported task_dispatched at 2.2% when the true post-fix
rate was 38.0% -- a number measuring instrumentation history, not behavior.

So each signal now declares its own validity window. Presence of `ts` is the
only available discriminator (blind-era records carry no timestamp at all).
Signals that were always validly instrumented deliberately keep the FULL
corpus: restricting them too would throw away hundreds of valid observations
and make the rates far noisier for no correctness gain.

Stdlib only. ASCII-only.

Usage: python eos-telemetry-rollup.py [path-to-lane-telemetry.jsonl]
Env: EOS_TELEMETRY_DIR overrides the default telemetry directory.
"""

import json
import os
import sys

DEFAULT_DIR = "C:/Users/Owner/.claude/telemetry"
OUT_NAME = "lane-telemetry.jsonl"

# Date the dispatch-detection fix landed in eos-telemetry.py; records written
# from then on carry a `ts`. Referenced in report text only.
DISPATCH_FIX_DATE = "2026-07-24"

# (record key, human label, post_fix_only) for the signals we track.
# post_fix_only=True restricts the signal to records stamped with `ts`, i.e.
# those written by an emitter capable of detecting it. Set this ONLY for a
# signal with a known detection blind spot -- it costs statistical power.
SIGNALS = [
    ("lane_declared", "lane_declared", False),
    ("bash_test_ran", "bash_test_ran", False),
    ("task_dispatched", "task_dispatched", True),
    ("verification_seen", "verification_seen", False),
]


def resolve_path():
    if len(sys.argv) > 1 and sys.argv[1].strip():
        return sys.argv[1]
    base = os.environ.get("EOS_TELEMETRY_DIR") or DEFAULT_DIR
    return os.path.join(base, OUT_NAME)


def load_records(path):
    records = []
    if not os.path.isfile(path):
        return records
    try:
        with open(path, "r", encoding="ascii", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                if isinstance(obj, dict):
                    records.append(obj)
    except Exception:
        return []
    return records


def pct(part, total):
    if total == 0:
        return "0.0%"
    return "%.1f%%" % (100.0 * part / total)


def has_ts(rec):
    """True if this record was written by a post-fix emitter. Blind-era records
    carry no `ts` at all, so presence is the only available discriminator."""
    ts = rec.get("ts")
    return isinstance(ts, str) and ts.strip() != ""


def main():
    path = resolve_path()
    records = load_records(path)
    total = len(records)

    print("EOS Lane Telemetry Rollup")
    print("source: %s" % path)
    print("total coding sessions: %d" % total)

    if total == 0:
        print("(no telemetry recorded yet)")
        return

    post_fix = [r for r in records if has_ts(r)]
    blind_era = [r for r in records if not has_ts(r)]
    print("records: %d total (%d post-fix, %d blind-era pre-%s -- "
          "dispatch undetectable)" % (
              total, len(post_fix), len(blind_era), DISPATCH_FIX_DATE))

    # (label, present, cohort_size, absence_rate or None when no valid cohort)
    rows = []
    for key, label, post_fix_only in SIGNALS:
        cohort = post_fix if post_fix_only else records
        size = len(cohort)
        present = sum(1 for r in cohort if r.get(key) is True)
        absence_rate = None if size == 0 else 1.0 - (float(present) / size)
        rows.append((key, label, present, size, absence_rate, post_fix_only))

    for key, label, present, size, _rate, post_fix_only in rows:
        if size == 0:
            # No valid cohort. Reporting 0.0% here would assert a real rate of
            # zero from zero observations -- the exact misread this fix exists
            # to stop.
            print("%-18s n/a (0 post-fix records; blind-era backlog cannot "
                  "detect this signal)" % (label + ":"))
            continue
        suffix = "  [post-fix cohort]" if post_fix_only else ""
        print("%-18s %s (%d/%d)%s" % (
            label + ":", pct(present, size), present, size, suffix))

    # Most-frequently-missing signal = highest ABSENCE RATE. Rate, not absolute
    # count: cohorts now differ in size, so raw absence counts are no longer
    # comparable across signals. Signals with no valid cohort are excluded
    # rather than ranked. Stable SIGNALS order breaks ties deterministically.
    most_missing = None
    most_missing_rate = -1.0
    most_missing_absent = 0
    most_missing_size = 0
    for _key, label, present, size, rate, _pfo in rows:
        if rate is None:
            continue
        if rate > most_missing_rate:
            most_missing_rate = rate
            most_missing = label
            most_missing_absent = size - present
            most_missing_size = size
    if most_missing is None:
        # Defensive only: unreachable while any signal is full-corpus, since a
        # non-empty corpus always gives those a cohort. Reachable if every
        # signal ever becomes post_fix_only and no post-fix record exists.
        print("most-frequently-missing signal: n/a (no measurable signal)")
    else:
        print("most-frequently-missing signal: %s (missing in %d of %d, %s)" % (
            most_missing, most_missing_absent, most_missing_size,
            pct(most_missing_absent, most_missing_size)))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
