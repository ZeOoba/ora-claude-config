"""ORA Claude Code reliability telemetry -- rollup report.

Reads lane-telemetry.jsonl and prints a short summary: total coding sessions
and the share that declared a lane, ran a test, and dispatched a subagent,
plus the single most-frequently-missing reliability signal. Handles an empty
or missing file gracefully. Always exits 0.

RECORDS ARE NOT SESSIONS. The emitter is a SessionEnd hook that re-parses the
ENTIRE transcript and appends a fresh record every time it fires -- and
SessionEnd fires on every resume/clear/compaction, not once per session. One
session can therefore hold many records (18, at the observed worst). Reporting
records as sessions overstates the population and weights a long-running
session's verdict by however many times it was resumed. Records sharing a
session_id are merged into one session before any rate is computed; see
merge_sessions for why the merge is a union rather than last-write-wins.

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

# Key a record is merged on, and the internal key holding a merged session's
# capability. The latter is prefixed so it can never collide with a real
# telemetry field name.
SESSION_KEY = "session_id"
CAPABILITY = "_capability"
CAPABILITY_RANK = {BLIND: 0, DEGRADED: 1, CAPABLE: 2}

# Signals unioned across ALL of a session's records. These three were never
# blind, so any record's True is the session's answer.
#
# COHORT_SIGNAL is deliberately NOT here. task_dispatched may only be unioned
# from a record that was itself CAPABLE of seeing dispatch: a blind-era or
# detector-regressed record's value "is not evidence of anything" (see the
# module docstring), and letting its True win would report a dispatch the
# trustworthy record never observed -- manufacturing the very signal this
# rollup exists to measure.
UNION_SIGNALS = tuple(ALL_RECORD_SIGNALS)


def resolve_path():
    if len(sys.argv) > 1 and sys.argv[1].strip():
        return sys.argv[1]
    base = os.environ.get("EOS_TELEMETRY_DIR") or DEFAULT_DIR
    return os.path.join(base, OUT_NAME)


def load_records(path):
    """Return (records, status, detail).

    An empty `records` list is NOT self-explanatory, so the status says which
    empty it is. Previously every one of these collapsed to a bare [] and the
    caller printed "(no telemetry recorded yet)" -- meaning a corrupt, moved, or
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
        # Do NOT discard what was already read -- a partial I/O failure used to
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


def merge_file_lists(prev_files, new_files):
    """Union two records' `files` lists, TOTALLY -- never raising.

    The emitter writes a list of path strings, but lane-telemetry.jsonl is
    append-only and hand-editable, so a malformed entry must not be able to
    take the whole report down. It very nearly could: merge_sessions runs
    BEFORE the first print, so a TypeError here reached the top-level
    `except Exception: pass` and the rollup exited 0 having printed ZERO
    bytes -- no numbers and no read-failure banner, indistinguishable from
    "nothing to report". Two bad lines in a 900-record file were enough.

    Non-string entries are dropped rather than risking an unhashable or
    unorderable set operation (`{["nested"]}` raises; `sorted({1, "a"})`
    raises). A set of str is always hashable and always orderable.
    """
    merged = set()
    for source in (prev_files, new_files):
        if isinstance(source, list):
            merged.update(f for f in source if isinstance(f, str))
    return sorted(merged)


def merge_sessions(records):
    """Collapse SessionEnd re-emissions into one entry per session.

    Returns (sessions, collapsed) where `collapsed` counts the records absorbed
    into an earlier entry. Each returned session carries CAPABILITY holding the
    BEST capability among its records: a session spanning the 2026-07-24
    dispatch fix has one blind record and one capable one, and it is a single
    capable session, not one of each.

    The merge is a UNION, never last-write-wins. Two reasons:

      1. Every merged signal is existential -- "did this session ever declare a
         lane / run a test / dispatch a subagent / show verification evidence".
         A False means "not seen yet", which is not evidence of absence when a
         later record saw it.
      2. It repairs the stale-partial class. An early SessionEnd fire snapshots
         the transcript BEFORE a dispatch happens and writes
         task_dispatched=false; the next fire, after the dispatch, writes true.
         Taking either the first or the last record makes the verdict depend on
         which re-emission happened to land last. Union does not.

    Ordering is preserved by first appearance so the output stays stable and
    diffable across runs.

    KNOWN, BOUNDED: a session straddling the moment a detector regressed holds
    one capable record and one degraded record, and best-of classifies it
    capable -- so it does not raise the regression WARNING. This is deliberate
    (it DOES hold a trustworthy observation) and self-limiting: every session
    started after the regression has only degraded records and still flags, so
    the canary fires within one session rather than being lost.
    """
    order = []
    by_sid = {}
    collapsed = 0

    for rec in records:
        state = dispatch_capability(rec)
        sid = rec.get(SESSION_KEY)
        prev = by_sid.get(sid) if isinstance(sid, str) and sid else None

        if prev is None:
            merged = dict(rec)
            # dict() is SHALLOW. Without this copy a single-record session's
            # `files` IS the caller's list object, so anything that later
            # appends to a merged session reaches back and corrupts the input
            # records. Verified aliasing before this line was added.
            if isinstance(merged.get("files"), list):
                merged["files"] = list(merged["files"])
            merged[CAPABILITY] = state
            # Seed the dispatch verdict ONLY from a record that could see
            # dispatch. A degraded record's True must not become the session's
            # answer just because it happened to arrive first.
            merged[COHORT_SIGNAL] = (
                state == CAPABLE and rec.get(COHORT_SIGNAL) is True
            )
            order.append(merged)
            # A record with no session_id has no merge key. Keep it as its own
            # session rather than collapsing every keyless record together --
            # that would fabricate one giant session out of unrelated work.
            if isinstance(sid, str) and sid:
                by_sid[sid] = merged
            continue

        collapsed += 1
        if CAPABILITY_RANK[state] > CAPABILITY_RANK[prev[CAPABILITY]]:
            prev[CAPABILITY] = state
        for key in UNION_SIGNALS:
            if rec.get(key) is True:
                prev[key] = True
        if state == CAPABLE and rec.get(COHORT_SIGNAL) is True:
            prev[COHORT_SIGNAL] = True
        # A re-parse of a growing transcript reports counts >= the previous
        # one, but never rely on that: take the max so a truncated re-parse
        # (post-compaction, say) can never shrink a session.
        if isinstance(rec.get("edits"), int) and isinstance(prev.get("edits"), int):
            prev["edits"] = max(prev["edits"], rec["edits"])
        prev["files"] = merge_file_lists(prev.get("files"), rec.get("files"))

    return order, collapsed


def pct(part, total):
    if total == 0:
        return "0.0%"
    return "%.1f%%" % (100.0 * part / total)


def main():
    path = resolve_path()
    records, status, detail = load_records(path)

    # Defence in depth. merge_sessions runs before the first print, so ANY
    # exception it raises is caught by the top-level handler and the rollup
    # exits 0 having printed nothing at all -- a silent blank that reads as
    # "no findings". Fall back to the un-merged records (over-counted, but
    # reported) and say so loudly rather than emitting nothing.
    merge_failed = ""
    try:
        sessions, collapsed = merge_sessions(records)
    except Exception as exc:
        sessions, collapsed = records, 0
        merge_failed = "%s: %s" % (type(exc).__name__, exc)
    total = len(sessions)

    print("EOS Lane Telemetry Rollup")
    print("source: %s" % path)
    print("total coding sessions: %d" % total)
    print("total records: %d (%d duplicate re-emission(s) collapsed)"
          % (len(records), collapsed))
    if merge_failed:
        print("!! SESSION MERGE FAILED (%s) -- falling back to RAW RECORDS. "
              "Every count below over-reports sessions and weights resumed "
              "sessions multiple times. Treat as unreliable." % merge_failed)
    if detail:
        print("read note: %s" % detail)

    if status in ("unreadable", "corrupt"):
        # Loud and unmistakable: this is NOT the benign first-run empty. Exit
        # stays 0 so the calling block does not halt, but the caller must never
        # report this as "no telemetry yet".
        print("!! TELEMETRY READ FAILED (%s) -- %s" % (status, detail))
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
    for rec in sessions:
        # .get + recompute, never rec[CAPABILITY]: on the merge-failure path
        # above `sessions` holds RAW records, which carry no CAPABILITY key.
        state = rec.get(CAPABILITY) or dispatch_capability(rec)
        if state == CAPABLE:
            capable.append(rec)
        elif state == DEGRADED:
            degraded += 1
        else:
            blind += 1

    print("dispatch-capable cohort: %d" % len(capable))
    print("blind-era backlog: %d" % blind)
    print("detector-regressed sessions: %d" % degraded)

    # Signal rates. Each is (label, present, denominator, scope, measurable).
    rows = []
    for key in ALL_RECORD_SIGNALS:
        present = sum(1 for r in sessions if r.get(key) is True)
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
            print("%-18s n/a (0 dispatch-capable sessions; "
                  "%d blind-era session(s) cannot report dispatch)"
                  % (label + ":", blind))
            continue
        print("%-18s %s (%d/%d %s)" % (
            label + ":", pct(present, denom), present, denom, scope))

    if degraded:
        print("WARNING: %d session(s) declare schema >= %d but a dispatch "
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
              "session(s))" % (label, pct(present, denom), denom, scope))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
