"""ORA Claude Code reliability telemetry -- rollup report.

Reads lane-telemetry.jsonl and prints a short summary: total coding sessions
and the share that declared a lane, ran a test, and dispatched a subagent,
plus the single most-frequently-missing reliability signal. Handles an empty
or missing file gracefully. Always exits 0.

Stdlib only. ASCII-only.

Usage: python eos-telemetry-rollup.py [path-to-lane-telemetry.jsonl]
Env: EOS_TELEMETRY_DIR overrides the default telemetry directory.
"""

import json
import os
import sys

DEFAULT_DIR = "C:/Users/Owner/.claude/telemetry"
OUT_NAME = "lane-telemetry.jsonl"

# (record key, human label) for the signals we track.
SIGNALS = [
    ("lane_declared", "lane_declared"),
    ("bash_test_ran", "bash_test_ran"),
    ("task_dispatched", "task_dispatched"),
    ("verification_seen", "verification_seen"),
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

    counts = {key: 0 for key, _ in SIGNALS}
    for rec in records:
        for key, _ in SIGNALS:
            if rec.get(key) is True:
                counts[key] += 1

    print("lane_declared:     %s (%d/%d)" % (
        pct(counts["lane_declared"], total), counts["lane_declared"], total))
    print("bash_test_ran:     %s (%d/%d)" % (
        pct(counts["bash_test_ran"], total), counts["bash_test_ran"], total))
    print("task_dispatched:   %s (%d/%d)" % (
        pct(counts["task_dispatched"], total),
        counts["task_dispatched"], total))
    print("verification_seen: %s (%d/%d)" % (
        pct(counts["verification_seen"], total),
        counts["verification_seen"], total))

    # Most-frequently-missing signal = lowest present-count (most absences).
    # Stable order via SIGNALS list to break ties deterministically.
    most_missing = None
    most_missing_absent = -1
    for key, label in SIGNALS:
        absent = total - counts[key]
        if absent > most_missing_absent:
            most_missing_absent = absent
            most_missing = label
    print("most-frequently-missing signal: %s (missing in %d of %d)" % (
        most_missing, most_missing_absent, total))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
