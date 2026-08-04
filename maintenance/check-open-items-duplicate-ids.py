#!/usr/bin/env python3
"""ORA open-items-tracker.md ID-integrity check -- catches two sessions (or two
same-day entries from one session) independently assigning the SAME OI-NNN id.

WHY (found 2026-07-26): open-items-tracker.md's own convention is "read the
tracker's current highest OI-NNN, assign the next sequential ID" -- a
read-then-write with no lock and no reservation step. Two sessions (or two runs
within one session) that both read the tracker before either commits will mint
the SAME id. Confirmed live: a repo-housekeeping session found the tracker
carrying two distinct rows both stamped OI-027 -- a same-day credential-exposure
finding collided with an already-committed PR-238 vitest-gap finding. Fixed by
hand that day (renumbered to OI-029); this probe is the standing catch for the
next occurrence, so it doesn't again require a human noticing during an
unrelated review pass.

WHAT IT CHECKS, against the tracker's Open + Closed tables and its `### OI-NNN`
detail sections:
  DUPLICATE_ROW      -- an OI-NNN id appears in more than one table row
                        (Open and/or Closed combined -- a real item is closed
                        by MOVING its row, not by leaving a second one behind,
                        so ANY id seen twice across both tables is a collision,
                        never a legitimate state).
  DUPLICATE_SECTION  -- more than one `### OI-NNN` detail section exists for
                        the same id.
  ORPHANED_SECTION   -- a `### OI-NNN` detail section exists with NO matching
                        table row in either Open or Closed. Every item is
                        supposed to have "exactly ONE row" per the tracker's
                        own stated convention; a section with no row is either
                        a row that was dropped by mistake during an edit, or a
                        collision casualty (the correctly-renumbered id's OLD
                        section left behind). Report-only -- do not guess which
                        interpretation applies.
  MISSING_SECTION    -- the mirror image of ORPHANED_SECTION: a table row
                        exists with NO matching `### OI-NNN` section, so the
                        row's own `[OI-NNN](#OI-NNN)` link -- and any external
                        `open-items-tracker.md#OI-NNN` reference from another
                        memory file -- resolves to nothing. Found live
                        2026-07-27: OI-028 and OI-030 each sat as a bare row
                        for a time while `event_log.md` already linked to
                        their `#OI-NNN` anchor, so the link was dead the whole
                        time the section was missing. INFORMATIONAL ONLY --
                        deliberately NOT counted by any_finding()/the exit
                        code, because most closed rows never get a detail
                        section at all (a one-line row is often the complete
                        story) and that must not turn into a daily failure.

Detection only. This probe never edits the tracker or decides which of two
colliding rows is "wrong" -- that requires reading both rows' content and
dates to judge intent (exactly what a human did by hand on 2026-07-26), which
a mechanical id-count cannot safely automate. It surfaces the collision loudly
so a human (or a future session with more context) resolves it, the same
detection/remediation split every other probe in this tree uses.

Exit 0 = clean. Exit 1 = at least one DUPLICATE_ROW / DUPLICATE_SECTION /
ORPHANED_SECTION finding (MISSING_SECTION is informational only and never
affects the exit code -- see above). Prints one line per finding plus a final
RESULT_JSON={...} summary line for programmatic callers.
"""
import json
import os
import re
import sys

CLAUDE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_TRACKER_PATH = os.path.join(
    CLAUDE_DIR, "projects",
    "C--Users-Owner-OneDrive---Oxford-Capital-Partners", "memory",
    "open-items-tracker.md",
)

# Test seam only (mirrors the other probes' *_OVERRIDE pattern): when set, read
# THIS path instead of the canonical tracker. None -> canonical.
TRACKER_PATH_OVERRIDE = None

ROW_ID_RE = re.compile(r"^\|\s*\[OI-(\d+)\]\(#OI-\d+\)\s*\|", re.MULTILINE)
SECTION_ID_RE = re.compile(r"^### OI-(\d+)\s*$", re.MULTILINE)


def tracker_path():
    return TRACKER_PATH_OVERRIDE or DEFAULT_TRACKER_PATH


def _duplicates(ids):
    """[(id, count)] for every id appearing more than once, id order of first
    appearance (stable, not sorted by count) so findings read in document
    order rather than jumping around."""
    seen_order = []
    counts = {}
    for i in ids:
        if i not in counts:
            seen_order.append(i)
        counts[i] = counts.get(i, 0) + 1
    return [(i, counts[i]) for i in seen_order if counts[i] > 1]


def check(text):
    """Pure function of file content -> findings dict. Kept separate from
    file I/O so tests can feed fixture strings directly."""
    row_ids = ROW_ID_RE.findall(text)
    section_ids = SECTION_ID_RE.findall(text)
    row_id_set = set(row_ids)
    section_id_set = set(section_ids)

    duplicate_rows = _duplicates(row_ids)
    duplicate_sections = _duplicates(section_ids)
    # Order of first appearance, de-duped, for orphan reporting.
    orphaned_sections = []
    seen = set()
    for sid in section_ids:
        if sid not in row_id_set and sid not in seen:
            orphaned_sections.append(sid)
            seen.add(sid)
    # Mirror image: a row with no matching section. Order of first appearance, de-duped.
    missing_sections = []
    seen = set()
    for rid in row_ids:
        if rid not in section_id_set and rid not in seen:
            missing_sections.append(rid)
            seen.add(rid)

    return {
        "row_count": len(row_ids),
        "unique_row_count": len(row_id_set),
        "section_count": len(section_ids),
        "duplicate_rows": [{"id": "OI-%s" % i, "count": c} for i, c in duplicate_rows],
        "duplicate_sections": [{"id": "OI-%s" % i, "count": c} for i, c in duplicate_sections],
        "orphaned_sections": ["OI-%s" % i for i in orphaned_sections],
        "missing_sections": ["OI-%s" % i for i in missing_sections],
    }


def any_finding(result):
    return bool(result["duplicate_rows"] or result["duplicate_sections"]
                or result["orphaned_sections"])


def format_report(result, path):
    lines = []
    if not any_finding(result):
        lines.append("open-items-tracker ID check: clean (%d rows, %d unique ids, "
                      "%d detail sections) -- %s" % (
                          result["row_count"], result["unique_row_count"],
                          result["section_count"], path))
    else:
        lines.append("open-items-tracker ID check: %d finding(s) -- %s" % (
            len(result["duplicate_rows"]) + len(result["duplicate_sections"])
            + len(result["orphaned_sections"]), path))
        for d in result["duplicate_rows"]:
            lines.append("[ACTION] DUPLICATE_ROW %s appears in %d table rows -- "
                          "two items were independently assigned the same id; "
                          "read both rows and renumber the newer one (never guess "
                          "which is newer from the id alone). Get the replacement "
                          "id from `python maintenance/allocate-oi-id.py --session "
                          "<id> --note \"<why>\"` -- do NOT hand-compute max+1, "
                          "which is what produced this collision: the tracker still "
                          "shows the OLD max for the whole minutes-long gap between "
                          "reading it and committing the row, so a second session "
                          "reading in good faith gets the same answer."
                          % (d["id"], d["count"]))
        for d in result["duplicate_sections"]:
            lines.append("[ACTION] DUPLICATE_SECTION %s has %d '### %s' detail "
                          "sections -- same collision, in the detail sections "
                          "rather than (or in addition to) the table rows."
                          % (d["id"], d["count"], d["id"]))
        for sid in result["orphaned_sections"]:
            lines.append("[ACTION] ORPHANED_SECTION %s has a '### %s' detail "
                          "section but NO table row in Open or Closed -- likely a "
                          "row lost during an edit, or the stale half of a "
                          "collision that was renumbered elsewhere." % (sid, sid))
    if result["missing_sections"]:
        lines.append("[INFO] %d row(s) have no matching '### OI-NNN' detail section "
                      "(not itself a defect -- a one-line row is often the whole "
                      "story -- but any external '#OI-NNN' link to one of these "
                      "currently resolves to nothing): %s"
                      % (len(result["missing_sections"]), ", ".join(result["missing_sections"])))
    return "\n".join(lines)


def main():
    path = tracker_path()
    try:
        with open(path, "r", encoding="utf-8") as fh:
            text = fh.read()
    except OSError as e:
        sys.stderr.write(
            "open-items-tracker ID check: COULD NOT READ %s (%s) -- treat as "
            "a check failure, not a clean result.\n" % (path, e))
        return 1

    result = check(text)
    print(format_report(result, path))
    print("RESULT_JSON=%s" % json.dumps(result))
    return 1 if any_finding(result) else 0


if __name__ == "__main__":
    sys.exit(main())
