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

Exit codes:  0 = valid   1 = INVALID (at least one [ACTION] line)   2 = could not look

Usage:
  snapshot-validate.py --path <file.json> [--expect-count N]
  snapshot-validate.py --dir <_state-history> --fleet lams --newest-valid [--expect-count N]
      -> prints the newest structurally-valid snapshot path (fallback-baseline search)
"""
import argparse, glob, json, os, sys

REQUIRED_TOP = ("snapshotDate", "capturedAtUtc", "source", "tasks")
REQUIRED_ROW = ("taskId", "enabled")
SCHEDULE_KEYS = ("cronExpression", "fireAt")


def validate(path, expect_count=None):
    """Return (ok: bool, findings: list[str], n_tasks: int|None)."""
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
    if expect_count is not None and n != expect_count:
        f.append("[ACTION] COUNT-MISMATCH %s :: %d rows, live registry has %d"
                 % (path, n, expect_count))
    return (len([x for x in f if x.startswith("[ACTION]")]) == 0), f, n


def newest_valid(directory, fleet, expect_count=None, exclude=()):
    pat = os.path.join(directory, "*.%s.json" % fleet)
    for p in sorted(glob.glob(pat), reverse=True):
        if os.path.basename(p) in exclude or ".dryrun." in p:
            continue
        ok, _, n = validate(p, expect_count)
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
        return 0

    if not a.path:
        print("[ACTION] COULD-NOT-LOOK :: --path or --newest-valid required")
        return 2
    if not os.path.exists(a.path):
        print("[ACTION] MISSING %s" % a.path)
        return 1
    ok, findings, n = validate(a.path, a.expect_count)
    for line in findings:
        print(line)
    if ok:
        print("SNAPSHOT OK %s tasks=%d" % (a.path, n))
        return 0
    print("SNAPSHOT INVALID %s (%d finding(s)) — do NOT use as a diff baseline and "
          "do NOT leave a failed write in place silently." % (a.path, len(findings)))
    return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # never let the validator itself masquerade as "clean"
        print("[ACTION] COULD-NOT-LOOK :: validator raised %s: %s"
              % (type(e).__name__, e))
        sys.exit(2)
