"""ORA Claude Code reliability telemetry -- rollup report.

Reads lane-telemetry.jsonl and prints a short summary: total coding sessions
and the share that declared a lane, ran a test, and dispatched a subagent,
plus the single most-frequently-missing reliability signal. Handles an empty
or missing file gracefully. Always exits 0.

COHORT SEGMENTATION. The file holds two incompatible populations. Records
written before the 2026-07-24 dispatch-detection fix carry
task_dispatched=false unconditionally -- the emitter's DISPATCH_TOOLS did not
match the real `Agent` tool name, so it could not see dispatch at all.
Counting those in the dispatch denominator reports a wrongly-low rate
forever. They are excluded from that one signal and reported separately.

A record is dispatch-capable when, in priority order:
  1. `schema` >= MIN_DISPATCH_SCHEMA and its `detectors.dispatch` list still
     contains REQUIRED_DISPATCH_TOOL -> capable.
  2. `schema` >= MIN_DISPATCH_SCHEMA but the dispatch detector LOST that name
     -> degraded. Excluded from the rate and reported loudly. This is the
     regression class the schema field exists to catch: without it, a broken
     emitter that still stamped `ts` would be trusted silently.
  3. No `schema` field (records written before it existed) -> fall back to
     `ts` presence, the legacy proxy. This keeps the ~766-record blind-era
     backlog correctly classified without rewriting history.

Stdlib only. ASCII-only.

Usage: python eos-telemetry-rollup.py [path-to-lane-telemetry.jsonl]
Env: EOS_TELEMETRY_DIR overrides the default telemetry directory.
"""

import json
import os
import sys

DEFAULT_DIR = "C:/Users/Owner/.claude/telemetry"
OUT_NAME = "lane-telemetry.jsonl"

# Minimum record schema that can be trusted to report subagent dispatch.
# See eos-telemetry.py SCHEMA_VERSION for the version history.
MIN_DISPATCH_SCHEMA = 2
# The tool name a capable dispatch detector MUST still match. If a record's
# declared detector list has lost this, the emitter regressed and its
# task_dispatched value is not evidence of anything.
REQUIRED_DISPATCH_TOOL = "Agent"

# Signals that were never blind -- reported over the full population.
ALL_RECORD_SIGNALS = ["lane_declared", "bash_test_ran", "verification_seen"]
# Reported over the dispatch-capable cohort only.
COHORT_SIGNAL = "task_dispatched"

CAPABLE = "capable"
DEGRADED = "degraded"
BLIND = "blind"


def resolve_path():
    if len(sys.argv) > 1 and sys.argv[1].strip():
        return sys.argv[1]
    base = os.environ.get("EOS_TELEMETRY_DIR") or DEFAULT_DIR
    return os.path.join(base, OUT_NAME)


def load_records(path):
    """Return (records, status, detail).

    An empty `records` list is NOT self-explanatory, so the status says which
    empty it is. Previously every one of these collapsed to a bare [] and the
    caller printed "(no telemetry recorded yet)" — meaning a corrupt, moved, or
    unreadable telemetry file was indistinguishable from a genuine first run.

      "absent"     - file does not exist. The ONLY legitimate empty.
      "ok"         - file read cleanly (records may still be [] if truly empty).
      "unreadable" - open/read raised; `records` holds whatever was salvaged
                     before the error rather than being discarded.
      "corrupt"    - file had content but no line parsed into a dict record.

    `detail` carries the skipped-line count / exception text for the report.
    """
    records = []
    skipped = 0
    if not os.path.isfile(path):
        return records, "absent", ""
    try:
        # utf-8, not ascii: the previous encoding mangled any non-ASCII line
        # into replacement chars, json.loads then failed, and the record was
        # dropped silently. Surrogateescape keeps the bytes round-trippable.
        with open(path, "r", encoding="utf-8", errors="surrogateescape") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    skipped += 1
                    continue
                if isinstance(obj, dict):
                    records.append(obj)
                else:
                    skipped += 1
    except Exception as exc:
        # Do NOT discard what was already read — a partial I/O failure used to
        # zero out an otherwise-valid dataset.
        return records, "unreadable", "%s: %s" % (type(exc).__name__, exc)
    if not records and skipped:
        return records, "corrupt", "%d unparseable line(s), 0 usable records" % skipped
    detail = "%d unparseable line(s) skipped" % skipped if skipped else ""
    return records, "ok", detail


def dispatch_capability(rec):
    """Classify a record's ability to have reported subagent dispatch.

    Returns CAPABLE, DEGRADED, or BLIND. Order matters: the schema check runs
    FIRST so a regressed-detector record can never fall through to the weaker
    `ts` proxy and be silently trusted.
    """
    schema = rec.get("schema")
    # bool is a subclass of int -- exclude it explicitly rather than relying
    # on True < 2 happening to be falsy.
    if isinstance(schema, int) and not isinstance(schema, bool):
        if schema < MIN_DISPATCH_SCHEMA:
            return BLIND
        detectors = rec.get("detectors")
        if isinstance(detectors, dict):
            dispatch = detectors.get("dispatch")
            if isinstance(dispatch, list):
                if REQUIRED_DISPATCH_TOOL in dispatch:
                    return CAPABLE
                return DEGRADED
        # Schema is new enough but declares no detectors block. The version
        # is the primary key, so trust it -- forward-compat with a future
        # record shape that drops the block.
        return CAPABLE

    # Backward compatibility for records written before `schema` existed.
    # `ts` presence is the legacy proxy for a post-fix emitter.
    if rec.get("ts"):
        return CAPABLE
    return BLIND


def pct(part, total):
    if total == 0:
        return "0.0%"
    return "%.1f%%" % (100.0 * part / total)


def main():
    path = resolve_path()
    records, status, detail = load_records(path)
    total = len(records)

    print("EOS Lane Telemetry Rollup")
    print("source: %s" % path)
    print("total coding sessions: %d" % total)
    if detail:
        print("read note: %s" % detail)

    if status in ("unreadable", "corrupt"):
        # Loud and unmistakable: this is NOT the benign first-run empty. Exit
        # stays 0 so the calling block does not halt, but the caller must never
        # report this as "no telemetry yet".
        print("!! TELEMETRY READ FAILED (%s) — %s" % (status, detail))
        print("!! This is a FAILURE, not a null result. Do NOT report it as "
              "'(no telemetry recorded yet)'. Verify the file at the source "
              "path above before trusting any Block G ratio this run.")
        return

    if total == 0:
        print("(no telemetry recorded yet)")
        return

    capable = []
    degraded = 0
    blind = 0
    for rec in records:
        state = dispatch_capability(rec)
        if state == CAPABLE:
            capable.append(rec)
        elif state == DEGRADED:
            degraded += 1
        else:
            blind += 1

    print("dispatch-capable cohort: %d" % len(capable))
    print("blind-era backlog: %d" % blind)
    print("detector-regressed records: %d" % degraded)

    # Signal rates. Each is (label, present, denominator, scope, measurable).
    rows = []
    for key in ALL_RECORD_SIGNALS:
        present = sum(1 for r in records if r.get(key) is True)
        rows.append((key, present, total, "all", True))

    dispatched = sum(1 for r in capable if r.get(COHORT_SIGNAL) is True)
    rows.append(
        (COHORT_SIGNAL, dispatched, len(capable), "capable", bool(capable))
    )

    # Stable display order matching the original report.
    order = ["lane_declared", "bash_test_ran", COHORT_SIGNAL, "verification_seen"]
    by_key = {r[0]: r for r in rows}
    for key in order:
        label, present, denom, scope, measurable = by_key[key]
        if not measurable:
            print("%-18s n/a (0 dispatch-capable records; "
                  "%d blind-era record(s) cannot report dispatch)"
                  % (label + ":", blind))
            continue
        print("%-18s %s (%d/%d %s)" % (
            label + ":", pct(present, denom), present, denom, scope))

    if degraded:
        print("WARNING: %d record(s) declare schema >= %d but a dispatch "
              "detector missing %r -- the emitter regressed; these are "
              "excluded from the rate above. Check DISPATCH_TOOLS in "
              "hooks/eos-telemetry.py."
              % (degraded, MIN_DISPATCH_SCHEMA, REQUIRED_DISPATCH_TOOL))

    # Most-frequently-missing signal. Denominators differ across cohorts, so
    # rank by RATE, not by raw absence count -- comparing absences drawn from
    # a 50-record cohort against an 816-record one is meaningless. Signals
    # with no measurable cohort are skipped entirely rather than scoring 0%.
    ranked = [r for r in (by_key[k] for k in order) if r[4] and r[2] > 0]
    if ranked:
        worst = min(ranked, key=lambda r: (1.0 * r[1] / r[2], order.index(r[0])))
        label, present, denom, scope, _ = worst
        print("most-frequently-missing signal: %s (present in %s of %d %s "
              "record(s))" % (label, pct(present, denom), denom, scope))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
