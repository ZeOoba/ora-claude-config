#!/usr/bin/env python3
"""Tests for check-open-items-duplicate-ids.py -- the probe that catches two
OI-NNN table rows (or detail sections) sharing the same id, the exact
collision found by hand 2026-07-26 (two rows both stamped OI-027).

Run: python _tests/test_check_open_items_duplicate_ids.py   (exit 0 = pass)
Pure-function tests against check() -- no file I/O needed for the core logic;
main()'s file-read path is covered separately via TRACKER_PATH_OVERRIDE.
"""
import importlib.util
import os
import sys
import tempfile

MAINT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location(
    "codc", os.path.join(MAINT, "check-open-items-duplicate-ids.py"))
codc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(codc)

results = []


def expect(label, cond, detail=""):
    results.append((bool(cond), label))
    if not cond:
        print("  FAIL: %s %s" % (label, detail))


def row(oi_id, body="some finding text"):
    return "| [OI-%s](#OI-%s) | 2026-07-26 | source | %s |\n" % (oi_id, oi_id, body)


def section(oi_id, status="OPEN"):
    return "### OI-%s\n**Status:** %s\n\nsome detail text\n\n" % (oi_id, status)


# --- clean file: no findings --------------------------------------------------------
clean = (
    "## Open\n\n| ID | Opened | Source | One-line |\n|----|----|----|----|\n"
    + row("001") + row("002") + "\n"
    "## Closed\n\n| ID | Opened | Closed | Source | One-line |\n|----|----|----|----|----|\n"
    + row("000") + "\n"
    "### OI-001\n**Status:** OPEN\n\ndetail\n\n"
    "### OI-002\n**Status:** OPEN\n\ndetail\n\n"
)
r = codc.check(clean)
expect("clean: no duplicate rows", r["duplicate_rows"] == [], "got %r" % r["duplicate_rows"])
expect("clean: no duplicate sections", r["duplicate_sections"] == [], "got %r" % r["duplicate_sections"])
expect("clean: no orphaned sections", r["orphaned_sections"] == [], "got %r" % r["orphaned_sections"])
expect("clean: any_finding False", codc.any_finding(r) is False)
expect("clean: row_count counts every row across both tables", r["row_count"] == 3, "got %r" % r["row_count"])
expect("clean: unique_row_count matches row_count when nothing collides",
       r["unique_row_count"] == 3, "got %r" % r["unique_row_count"])

# --- the real 2026-07-26 case: same id in Open + Closed (or twice in Open) ----------
dup_rows = (
    "## Open\n\n| ID | Opened | Source | One-line |\n|----|----|----|----|\n"
    + row("027", "credential exposure finding")
    + row("027", "vitest ESLint gap finding")
    + "\n## Closed\n\n| ID | Opened | Closed | Source | One-line |\n|----|----|----|----|----|\n\n"
)
r = codc.check(dup_rows)
expect("dup-row: detects OI-027 duplicated twice",
       r["duplicate_rows"] == [{"id": "OI-027", "count": 2}], "got %r" % r["duplicate_rows"])
expect("dup-row: any_finding True", codc.any_finding(r) is True)
report = codc.format_report(r, "fixture-path")
expect("dup-row: report names the colliding id",
       "OI-027" in report and "DUPLICATE_ROW" in report, "got %r" % report)
expect("dup-row: report recommends reading both rows, not auto-picking one",
       "renumber" in report.lower(), "got %r" % report)

# --- three-way collision: count must be 3, not just 'duplicated' -------------------
triple = "## Open\n\n" + row("050") + row("050") + row("050")
r = codc.check(triple)
expect("triple: count is exactly 3", r["duplicate_rows"] == [{"id": "OI-050", "count": 3}],
       "got %r" % r["duplicate_rows"])

# --- duplicate detail sections (independent of table-row state) --------------------
dup_sections = (
    "## Open\n\n" + row("012") + "\n"
    + section("012") + section("012")
)
r = codc.check(dup_sections)
expect("dup-section: detects two ### OI-012 sections",
       r["duplicate_sections"] == [{"id": "OI-012", "count": 2}], "got %r" % r["duplicate_sections"])
expect("dup-section: row itself is NOT flagged (only one row exists)",
       r["duplicate_rows"] == [], "got %r" % r["duplicate_rows"])

# --- orphaned section: detail section with no matching row at all ------------------
orphan = "## Open\n\n" + row("099") + "\n" + section("077")
r = codc.check(orphan)
expect("orphan: OI-077 flagged (section with no row)",
       r["orphaned_sections"] == ["OI-077"], "got %r" % r["orphaned_sections"])
expect("orphan: OI-099 (has a row, no section) is NOT flagged as orphaned",
       "OI-099" not in r["orphaned_sections"])
report = codc.format_report(r, "fixture-path")
expect("orphan: report says ORPHANED_SECTION", "ORPHANED_SECTION" in report, "got %r" % report)

# --- missing section: table row with NO matching detail section (mirror of orphaned) -
# Real-world case found 2026-07-27: OI-028 and OI-030 each had a table row but no
# '### OI-NNN' section, so an external '#OI-NNN' link (from event_log.md) resolved to
# nothing. Report-only, like the other three checks -- but NOT part of any_finding(),
# since most closed rows never get a detail section by design (a one-line row is
# often the whole story) and that must not itself start failing every daily run.
missing = "## Open\n\n" + row("028") + row("030") + "\n" + section("028")
r = codc.check(missing)
expect("missing: OI-030 flagged (row with no section)",
       r["missing_sections"] == ["OI-030"], "got %r" % r["missing_sections"])
expect("missing: OI-028 (has both a row and a section) is NOT flagged as missing",
       "OI-028" not in r["missing_sections"])
expect("missing: any_finding() stays False -- a missing section alone is not a collision",
       codc.any_finding(r) is False, "got %r" % r)
report = codc.format_report(r, "fixture-path")
expect("missing: report mentions OI-030 without an [ACTION] tag (informational only)",
       "OI-030" in report and "[ACTION] MISSING_SECTION" not in report, "got %r" % report)

# missing_sections must not mask (or be masked by) a genuine collision in the same run.
missing_plus_dup = "## Open\n\n" + row("040") + row("040") + row("050")
r = codc.check(missing_plus_dup)
expect("missing+dup: OI-040 still reported as a duplicate row",
       r["duplicate_rows"] == [{"id": "OI-040", "count": 2}], "got %r" % r["duplicate_rows"])
expect("missing+dup: OI-050 (row, no section) reported as missing",
       "OI-050" in r["missing_sections"], "got %r" % r["missing_sections"])
expect("missing+dup: any_finding() True because of the real duplicate, not the missing section",
       codc.any_finding(r) is True)

# --- a row referencing an id is not itself confused with a section header ----------
# (regression guard: the row regex must not accidentally match a '### OI-NNN' line,
# and vice versa -- e.g. if someone loosens either regex later.)
mixed = "## Open\n\n" + row("003") + "\n" + section("003", status="CLOSED")
r = codc.check(mixed)
expect("mixed: one row + one matching section -> totally clean",
       codc.any_finding(r) is False, "got %r" % r)

# --- multiple independent findings all surface together, none masks another --------
combo = (
    "## Open\n\n" + row("200") + row("200") + row("201") + "\n"
    + section("200") + section("300")
)
r = codc.check(combo)
expect("combo: duplicate row (OI-200) AND orphaned section (OI-300) both reported",
       r["duplicate_rows"] == [{"id": "OI-200", "count": 2}]
       and r["orphaned_sections"] == ["OI-300"], "got %r" % r)

# --- main(): file-read path via TRACKER_PATH_OVERRIDE -------------------------------
with tempfile.TemporaryDirectory() as td:
    clean_path = os.path.join(td, "clean-tracker.md")
    with open(clean_path, "w", encoding="utf-8") as f:
        f.write(clean)
    codc.TRACKER_PATH_OVERRIDE = clean_path
    try:
        rc = codc.main()
    finally:
        codc.TRACKER_PATH_OVERRIDE = None
    expect("main: clean tracker -> exit 0", rc == 0, "got %r" % rc)

    dirty_path = os.path.join(td, "dirty-tracker.md")
    with open(dirty_path, "w", encoding="utf-8") as f:
        f.write(dup_rows)
    codc.TRACKER_PATH_OVERRIDE = dirty_path
    try:
        rc = codc.main()
    finally:
        codc.TRACKER_PATH_OVERRIDE = None
    expect("main: tracker with a real collision -> exit 1", rc == 1, "got %r" % rc)

    missing_path = os.path.join(td, "does-not-exist.md")
    codc.TRACKER_PATH_OVERRIDE = missing_path
    try:
        rc = codc.main()
    finally:
        codc.TRACKER_PATH_OVERRIDE = None
    expect("main: unreadable tracker path -> exit 1 (failure, not silent clean)",
           rc == 1, "got %r" % rc)

# --- the CANONICAL tracker itself, right now, must be clean (this is also the
# regression guard for the actual OI-027 fix made earlier this session) -------------
real = codc.check(open(codc.DEFAULT_TRACKER_PATH, encoding="utf-8").read())
expect("canonical open-items-tracker.md has zero id collisions right now",
       codc.any_finding(real) is False, "got %r" % real)

passed = sum(1 for ok, _ in results if ok)
print("check-open-items-duplicate-ids tests: %d/%d passed" % (passed, len(results)))
sys.exit(0 if passed == len(results) else 1)
