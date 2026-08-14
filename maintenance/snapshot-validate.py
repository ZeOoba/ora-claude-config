#!/usr/bin/env python3
"""snapshot-validate.py — structural validator for _state-history registry snapshots.

WHY THIS EXISTS (2026-08-13). automation-health-monitor Step 0 v1.20 validated its
snapshots by COUNTING tasks. A count check is blind to the two defects that actually
occurred:

  * 2026-08-11.lams.json — 16 rows, and every row missing cronExpression/fireAt.
    Count check saw "16 vs 30" only because the truncation happened to be severe.
  * 2026-08-12.lams.json — 30 taskIds present, DOES NOT PARSE. A complete JSON
    document (closing "]" + "}") followed by more task rows appended after the
    close: a chunked write whose FIRST chunk was already a complete document.
    A count of taskId occurrences returns 30 and passes. It passed twice — on
    write, and on the next run's pre-diff read — and was caught only by
    membership-guard.ps1's PowerShell parser, a sibling task.

RULE: a snapshot is trusted only if it PARSES and conforms. Never if it merely counts.

v1.1 (2026-08-14) — SEVERITY SPLIT. COUNT IS NOT STRUCTURE, IN EITHER DIRECTION.
v1.0 folded --expect-count into structural validity, so a snapshot that parsed
cleanly and conformed in every respect was still reported "SNAPSHOT INVALID ... do
NOT use as a diff baseline" purely because the fleet had legitimately changed size.
That fired for real on 2026-08-14: two tasks were deliberately removed from the LAMS
registry (a two-month-old dangling orphan plus an expired one-time entry), the
2026-08-13 baseline was perfect, and the run burned two passes disambiguating
"corrupt file" from "the fleet got smaller." A count delta IS the diff signal Step 0
exists to report — it is the finding, not an obstacle to finding it.

Two consequences, both fixed here:

  1. A count delta is now an [ADVISORY] ROSTER-DELTA, not an [ACTION]. Structural
     validity is decided by parse + schema alone. Exit stays 0 and the file remains
     usable as a diff baseline.

  2. LATENT BUG, closed: newest_valid() passed expect_count down into validate(),
     so --newest-valid inherited the same conflation. On the very day the fleet
     changes size — precisely when a fallback baseline is most likely to be needed —
     it would have walked the entire history and returned NO-VALID-BASELINE, because
     every historical snapshot carries the OLD count. The fallback search now judges
     structure only, and reports each candidate's count for the caller to read.

Truncation is still caught, and does not depend on the count check to catch it. The
2026-08-11 file's 16 rows ALL also failed ROW-NO-SCHEDULE, which is an independent
[ACTION]. As a belt-and-suspenders backstop for a hypothetical CLEAN truncation
(well-formed rows, just fewer of them), a LARGE delta is still fatal: the split is
--count-tolerance (default max(3, 10% of expected)). Routine churn of a task or two
advises; losing half the fleet still fails. --strict-count restores v1.0 behaviour
for any caller that wants an exact match to be fatal.

Exit codes:  0 = structurally valid   1 = INVALID (>=1 [ACTION])   2 = could not look
             (a ROSTER-DELTA advisory alone does NOT change the exit code)

Usage:
  snapshot-validate.py --path <file.json> [--expect-count N] [--strict-count]
                       [--count-tolerance N]
  snapshot-validate.py --dir <_state-history> --fleet lams --newest-valid [--expect-count N]
      -> prints the newest STRUCTURALLY-valid snapshot path (fallback-baseline search)
"""
import argparse, glob, json, os, sys

REQUIRED_TOP = ("snapshotDate", "capturedAtUtc", "source", "tasks")
REQUIRED_ROW = ("taskId", "enabled")
SCHEDULE_KEYS = ("cronExpression", "fireAt")


def default_tolerance(expect_count):
    """Routine churn advises; a truncation-scale drop still fails."""
    return max(3, int(round(expect_count * 0.10)))


def validate(path, expect_count=None, strict_count=False, count_tolerance=None):
    """Return (ok: bool, findings: list[str], n_tasks: int|None).

    `ok` reflects STRUCTURAL validity only. A count delta within tolerance is
    reported as [ADVISORY] and leaves `ok` True — see the v1.1 note above.
    """
    f = []
    try:
        raw = open(path, encoding="utf-8-sig", errors="strict").read()
    except Exception as e:
        return False, ["[ACTION] UNREADABLE %s :: %s" % (path, e)], None
    if not raw.strip():
        return False, ["[ACTION] EMPTY %s" % path], None
    try:
        doc = json.loads(raw)
    except Exception as e:
        f.append("[ACTION] PARSE-FAIL %s :: %s" % (path, e))
        occ = raw.count('"taskId"')
        f.append("        note: file contains %d taskId occurrences — a COUNT check "
                 "would have passed this file. This is the 2026-08-12 defect class "
                 "(complete document followed by appended rows)." % occ)
        return False, f, None
    if not isinstance(doc, dict):
        return False, ["[ACTION] NOT-AN-OBJECT %s :: top level is %s"
                       % (path, type(doc).__name__)], None
    for k in REQUIRED_TOP:
        if k not in doc:
            f.append("[ACTION] MISSING-KEY %s :: %s" % (path, k))
    tasks = doc.get("tasks")
    if not isinstance(tasks, list):
        f.append("[ACTION] TASKS-NOT-LIST %s" % path)
        return False, f, None
    n = len(tasks)
    if n == 0:
        f.append("[ACTION] ZERO-TASKS %s" % path)
    seen = set()
    for i, row in enumerate(tasks):
        if not isinstance(row, dict):
            f.append("[ACTION] ROW-NOT-OBJECT %s :: index %d" % (path, i))
            continue
        for k in REQUIRED_ROW:
            if k not in row:
                f.append("[ACTION] ROW-MISSING-KEY %s :: index %d missing %s"
                         % (path, i, k))
        if not any(k in row for k in SCHEDULE_KEYS):
            f.append("[ACTION] ROW-NO-SCHEDULE %s :: index %d (%s) has neither "
                     "cronExpression nor fireAt — the 2026-08-11 defect class"
                     % (path, i, row.get("taskId", "?")))
        tid = row.get("taskId")
        if tid in seen:
            f.append("[ACTION] DUPLICATE-TASKID %s :: %s" % (path, tid))
        seen.add(tid)

    # --- count comparison: advisory by default, fatal only when truncation-scale ---
    if expect_count is not None and n != expect_count:
        delta = n - expect_count
        tol = count_tolerance if count_tolerance is not None else default_tolerance(expect_count)
        if strict_count:
            f.append("[ACTION] COUNT-MISMATCH %s :: %d rows, expected %d (--strict-count)"
                     % (path, n, expect_count))
        elif abs(delta) > tol:
            f.append("[ACTION] COUNT-MISMATCH-LARGE %s :: %d rows, expected %d "
                     "(delta %+d exceeds tolerance %d) — a drop this large is the "
                     "truncation signature, not routine roster churn."
                     % (path, n, expect_count, delta, tol))
        else:
            f.append("[ADVISORY] ROSTER-DELTA %s :: %d rows, live registry has %d "
                     "(delta %+d, within tolerance %d). The file is STRUCTURALLY "
                     "VALID and IS usable as a diff baseline — this delta is the "
                     "registry diff itself and belongs in the report, not a defect."
                     % (path, n, expect_count, delta, tol))

    return (len([x for x in f if x.startswith("[ACTION]")]) == 0), f, n


def newest_valid(directory, fleet, expect_count=None, exclude=()):
    """Newest STRUCTURALLY-valid snapshot. Deliberately does not judge on count —
    see v1.1 note 2: a fallback baseline is most needed on the day the count moves."""
    pat = os.path.join(directory, "*.%s.json" % fleet)
    for p in sorted(glob.glob(pat), reverse=True):
        if os.path.basename(p) in exclude or ".dryrun." in p:
            continue
        ok, _, n = validate(p)  # structure only — expect_count intentionally omitted
        if ok:
            return p, n
    return None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--path")
    ap.add_argument("--dir")
    ap.add_argument("--fleet", choices=("lams", "cc"), default="lams")
    ap.add_argument("--newest-valid", action="store_true")
    ap.add_argument("--expect-count", type=int)
    ap.add_argument("--strict-count", action="store_true",
                    help="restore v1.0 behaviour: ANY count mismatch is fatal")
    ap.add_argument("--count-tolerance", type=int,
                    help="override the default max(3, 10%% of expected) tolerance")
    ap.add_argument("--exclude", default="")
    a = ap.parse_args()

    exclude = tuple(x for x in a.exclude.split(",") if x)

    if a.newest_valid:
        if not a.dir or not os.path.isdir(a.dir):
            print("[ACTION] COULD-NOT-LOOK :: --dir missing or not a directory")
            return 2
        p, n = newest_valid(a.dir, a.fleet, a.expect_count, exclude)
        if not p:
            print("[ACTION] NO-VALID-BASELINE :: no structurally-valid .%s.json in %s"
                  % (a.fleet, a.dir))
            return 1
        print("VALID-BASELINE %s tasks=%d" % (p, n))
        if a.expect_count is not None and n != a.expect_count:
            print("[ADVISORY] ROSTER-DELTA :: baseline carries %d rows, live registry "
                  "has %d (delta %+d). Baseline accepted on structure; the delta is "
                  "the diff signal." % (n, a.expect_count, n - a.expect_count))
        return 0

    if not a.path:
        print("[ACTION] COULD-NOT-LOOK :: --path or --newest-valid required")
        return 2
    if not os.path.exists(a.path):
        print("[ACTION] MISSING %s" % a.path)
        return 1
    ok, findings, n = validate(a.path, a.expect_count, a.strict_count, a.count_tolerance)
    for line in findings:
        print(line)
    if ok:
        print("SNAPSHOT OK %s tasks=%d" % (a.path, n))
        return 0
    print("SNAPSHOT INVALID %s (%d finding(s)) — do NOT use as a diff baseline and "
          "do NOT leave a failed write in place silently."
          % (a.path, len([x for x in findings if x.startswith("[ACTION]")])))
    return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # never let the validator itself masquerade as "clean"
        print("[ACTION] COULD-NOT-LOOK :: validator raised %s: %s"
              % (type(e).__name__, e))
        sys.exit(2)
