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
# The guidance must name the allocator, not just say "renumber" (2026-08-04).
# Telling someone to renumber without saying HOW sends them back to hand-computing
# max+1 -- the exact procedure that produces these collisions, because the tracker
# shows the old max for the whole gap between reading it and committing the row.
expect("dup-row: report points at allocate-oi-id.py for the replacement id",
       "allocate-oi-id.py" in report, "got %r" % report)
expect("dup-row: report warns off hand-computing max+1",
       "max+1" in report and "do NOT hand-compute" in report, "got %r" % report)

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

# --- collision_finding(): which findings are NEVER a legitimate transient state -----
# The canonical-tracker assertion below runs against a live file that several sessions
# edit concurrently. An OI item is filed as two separate writes (a table row and a
# `### OI-NNN` detail section), so between them the tracker legitimately holds an
# orphaned section or a row with no section. That is a mid-edit state, not a defect,
# and it must not fail this suite for every other session on the machine.
# A DUPLICATE id is different: no filing sequence ever needs two rows carrying the same
# id, so a duplicate is always a real collision no matter when you look.
# any_finding() keeps its broader meaning -- it drives the probe's exit code, which is
# how the weekly hygiene sweep surfaces orphans -- so this is an ADDITIVE predicate.
only_orphan = {"duplicate_rows": [], "duplicate_sections": [],
               "orphaned_sections": ["OI-125"], "missing_sections": ["OI-121"]}
dup_row = {"duplicate_rows": [{"id": "OI-027", "count": 2}], "duplicate_sections": [],
           "orphaned_sections": [], "missing_sections": []}
dup_section = {"duplicate_rows": [], "duplicate_sections": [{"id": "OI-027", "count": 2}],
               "orphaned_sections": [], "missing_sections": []}
spotless = {"duplicate_rows": [], "duplicate_sections": [],
            "orphaned_sections": [], "missing_sections": []}

expect("collision_finding: transient orphan/missing section is NOT a collision",
       codc.collision_finding(only_orphan) is False, "got %r" % (only_orphan,))
expect("collision_finding: duplicate row IS a collision",
       codc.collision_finding(dup_row) is True)
expect("collision_finding: duplicate section IS a collision",
       codc.collision_finding(dup_section) is True)
expect("collision_finding: spotless is not a collision",
       codc.collision_finding(spotless) is False)
# Regression guard: the broader predicate must KEEP flagging orphans, or the weekly
# sweep silently stops reporting them (that sweep is what found OI-111/OI-112).
expect("any_finding still flags an orphaned section (exit-code semantics unchanged)",
       codc.any_finding(only_orphan) is True)
expect("any_finding still flags a duplicate row",
       codc.any_finding(dup_row) is True)

# --- the CANONICAL tracker itself, right now, must be free of ID COLLISIONS ----------
# (regression guard for the actual OI-027 fix). Deliberately NOT asserting full
# cleanliness: see collision_finding() above -- a concurrent session mid-filing an item
# would otherwise fail this test, and with it every push on the machine.
# --- broken-anchor escalation (2026-08-16) -------------------------------
# A sectionless row was reported [INFO] whether or not anything actually linked
# to it, so a genuinely broken cross-reference read as "no action" and persisted
# unnoticed. Escalation is now conditional on a REAL external reference.
_missing = {"missing_sections": ["OI-101", "OI-102"]}
_broken, _benign = codc.split_missing(_missing, {"OI-102"})
expect("split_missing routes a referenced id to broken", _broken == ["OI-102"],
       "got %r" % _broken)
expect("split_missing leaves an unreferenced id benign", _benign == ["OI-101"],
       "got %r" % _benign)
expect("split_missing with no refs escalates nothing",
       codc.split_missing(_missing, set()) == ([], ["OI-101", "OI-102"]))
expect("split_missing tolerates a result with no missing_sections key",
       codc.split_missing({}, {"OI-102"}) == ([], []))

_rep = codc.format_report(dict(_missing, row_count=2, unique_row_count=2,
                               section_count=0, duplicate_rows=[],
                               duplicate_sections=[], orphaned_sections=[]),
                          "fake.md", {"OI-102"})
expect("report marks a linked sectionless row [ACTION] BROKEN_ANCHOR",
       "[ACTION] BROKEN_ANCHOR" in _rep and "OI-102" in _rep, _rep)
expect("report keeps an unlinked sectionless row [INFO]",
       "[INFO]" in _rep and "OI-101" in _rep, _rep)
expect("BROKEN_ANCHOR line does not also list the benign id",
       "OI-101" not in _rep.split("[INFO]")[0], _rep)

# external_anchor_refs on a REAL temp directory. The first version of this test
# asserted only that a known sectionless row was absent from the live refs -- which
# passed for the wrong reason: the regex matched nothing at all, so the set was
# always empty and the assertion could not tell "exclusion works" from "feature is
# dead". It green-lit a feature that could never fire in production.
import tempfile as _tf, shutil as _sh, os as _os
_d = _tf.mkdtemp(prefix="oi-refs-")
try:
    # `with open(...)` -- NOT os.write(os.open(...)), which leaked an unclosed fd
    # per file. On Windows rmtree(ignore_errors=True) then silently fails on the
    # open handles, and this test runs on EVERY push via the prepush gate, so it
    # leaked a temp dir per push indefinitely.
    def _w(name, body):
        with open(_os.path.join(_d, name), "wb") as fh:
            fh.write(body)

    # The form real memory files actually use: a CROSS-FILE link into the tracker.
    _w("event_log.md", b"see [OI-148](open-items-tracker.md#OI-148) for detail\n")
    # A BARE fragment link in another file points at THAT file's own anchors and
    # must NOT be read as a reference to the tracker.
    _w("other.md", b"internal jump [x](#OI-999)\n")
    # The tracker's own self-links must be excluded, or every sectionless row
    # would escalate.
    _w("open-items-tracker.md",
       b"| [OI-777](#OI-777) | ... |\n[OI-778](open-items-tracker.md#OI-778)\n")
    _refs = codc.external_anchor_refs(_d, "open-items-tracker.md")
    expect("external_anchor_refs finds the cross-file link form actually used",
           "OI-148" in _refs, "got %r" % _refs)
    expect("external_anchor_refs ignores a BARE fragment link in another file",
           "OI-999" not in _refs, "got %r" % _refs)
    expect("external_anchor_refs excludes the tracker's own file entirely",
           "OI-777" not in _refs and "OI-778" not in _refs, "got %r" % _refs)
    expect("external_anchor_refs on a missing dir returns empty, never raises",
           codc.external_anchor_refs(_os.path.join(_d, "nope"), "x.md") == set())
finally:
    _sh.rmtree(_d, ignore_errors=True)

# A broken anchor must drive the EXIT CODE too -- an [ACTION] that leaves exit 0
# reproduces the "reads as no action" failure for every machine consumer.
expect("any_finding counts broken_anchors",
       codc.any_finding({"duplicate_rows": [], "duplicate_sections": [],
                         "orphaned_sections": [], "broken_anchors": ["OI-148"]}) is True)
expect("any_finding still ignores merely-sectionless rows",
       codc.any_finding({"duplicate_rows": [], "duplicate_sections": [],
                         "orphaned_sections": [], "broken_anchors": []}) is False)

real = codc.check(open(codc.DEFAULT_TRACKER_PATH, encoding="utf-8").read())
expect("canonical open-items-tracker.md has zero id collisions right now",
       codc.collision_finding(real) is False, "got %r" % real)
if real["orphaned_sections"] or real["missing_sections"]:
    print("  note: canonical tracker currently has orphaned=%r missing=%r -- advisory "
          "only, likely a concurrent mid-filing; `maintenance/check-open-items-"
          "duplicate-ids.py` reports these." % (real["orphaned_sections"],
                                                real["missing_sections"]))

# --- companion history file (split 2026-09-06, Automation Audit R22-4) -------------
# CLOSED items' rows and detail sections moved to open-items-tracker-history.md.
# check() itself is untouched (still a pure function of ONE string) -- these tests
# cover history_path()'s derivation and main()'s combining of the two files, which
# is where the actual dual-file awareness lives.

# history_path() must derive relative to tracker_path()'s OWN directory, never fall
# through to the real production history file, when only TRACKER_PATH_OVERRIDE is
# set. Getting this wrong bleeds unrelated live content (67 real closed rows) into
# every fixture-based test above that only ever meant to exercise the tracker in
# isolation -- exactly the failure this test guards against having reappear.
with tempfile.TemporaryDirectory() as td:
    fixture_tracker = os.path.join(td, "clean-tracker.md")
    with open(fixture_tracker, "w", encoding="utf-8") as f:
        f.write(clean)
    codc.TRACKER_PATH_OVERRIDE = fixture_tracker
    try:
        expect("history_path() derives inside the override's OWN directory, not the real one",
               os.path.dirname(codc.history_path()) == td,
               "got %r" % codc.history_path())
        expect("a companion history file absent from that directory reads as optional/empty",
               codc.read_optional(codc.history_path()) == "")
    finally:
        codc.TRACKER_PATH_OVERRIDE = None

# HISTORY_PATH_OVERRIDE, when explicitly set, wins outright (test seam parity with
# TRACKER_PATH_OVERRIDE).
with tempfile.TemporaryDirectory() as td:
    explicit = os.path.join(td, "wherever.md")
    with open(explicit, "w", encoding="utf-8") as f:
        f.write("### OI-999\n**Status:** CLOSED\n")
    codc.HISTORY_PATH_OVERRIDE = explicit
    try:
        expect("HISTORY_PATH_OVERRIDE wins over the derived path",
               codc.history_path() == explicit, "got %r" % codc.history_path())
    finally:
        codc.HISTORY_PATH_OVERRIDE = None

# main() must COMBINE tracker + history before checking -- a duplicate id split
# across the two files (the exact shape a bad manual edit could produce: the same
# id present as a row in BOTH the live Open table and the history Closed table) is
# every bit as much a real collision as two rows in one file, and must be caught.
with tempfile.TemporaryDirectory() as td:
    t_path = os.path.join(td, "open-items-tracker.md")
    h_path = os.path.join(td, "open-items-tracker-history.md")
    with open(t_path, "w", encoding="utf-8") as f:
        f.write("## Open\n\n" + row("500", "still open per this table") + "\n")
    with open(h_path, "w", encoding="utf-8") as f:
        f.write("## Closed\n\n" + row("500", "also closed per this table") + "\n")
    codc.TRACKER_PATH_OVERRIDE = t_path
    try:
        rc = codc.main()
    finally:
        codc.TRACKER_PATH_OVERRIDE = None
    expect("main() catches a duplicate id split ACROSS tracker + history -> exit 1",
           rc == 1, "got %r" % rc)

    # Sibling case: clean on each file alone, clean combined too (no false positive
    # from the mere fact of being split across two files).
    with open(t_path, "w", encoding="utf-8") as f:
        f.write("## Open\n\n" + row("501") + "\n" + section("501") + "\n")
    with open(h_path, "w", encoding="utf-8") as f:
        f.write("## Closed\n\n" + row("502") + "\n" + section("502", status="CLOSED") + "\n")
    codc.TRACKER_PATH_OVERRIDE = t_path
    try:
        rc = codc.main()
    finally:
        codc.TRACKER_PATH_OVERRIDE = None
    expect("main() reads clean when tracker and history are each clean on their own",
           rc == 0, "got %r" % rc)

# external_anchor_refs() must recognize a cross-file link into EITHER filename, and
# must exclude BOTH filenames as sources (a reference from the tracker INTO the
# history file, or vice versa, is internal to this one logical document).
_d2 = tempfile.mkdtemp(prefix="oi-refs-history-")
try:
    def _w2(name, body):
        with open(os.path.join(_d2, name), "wb") as fh:
            fh.write(body)
    _w2("event_log.md", b"closed via [OI-016](open-items-tracker-history.md#OI-016)\n")
    _w2("open-items-tracker.md",
        b"pointer: [OI-500](open-items-tracker-history.md#OI-500)\n")
    _w2("open-items-tracker-history.md",
        b"pointer back: [OI-501](open-items-tracker.md#OI-501)\n")
    refs2 = codc.external_anchor_refs(_d2, "open-items-tracker.md",
                                      "open-items-tracker-history.md")
    expect("external_anchor_refs matches a cross-file link into the HISTORY filename",
           "OI-016" in refs2, "got %r" % refs2)
    expect("external_anchor_refs excludes a tracker-internal link INTO history (not external)",
           "OI-500" not in refs2, "got %r" % refs2)
    expect("external_anchor_refs excludes a history-internal link INTO tracker (not external)",
           "OI-501" not in refs2, "got %r" % refs2)
finally:
    _sh.rmtree(_d2, ignore_errors=True)

# --- the live combined pair, right now: still zero id collisions -------------------
# Stronger than the tracker-alone regression guard above -- this is what main()
# actually checks in production (tracker text concatenated with history text).
_live_history_text = codc.read_optional(codc.DEFAULT_HISTORY_PATH)
_live_combined = codc.check(
    open(codc.DEFAULT_TRACKER_PATH, encoding="utf-8").read() + "\n" + _live_history_text)
expect("canonical tracker+history combined has zero id collisions right now",
       codc.collision_finding(_live_combined) is False, "got %r" % _live_combined)
# Baseline history: 5 -> 7 (2026-09-13, uncommitted at the time: OI-273 and OI-287, both
# row-less detail sections) -> EMPTY (2026-09-17). Every one of those 7 has since been
# reconciled -- check-open-items-duplicate-ids.py against the live pair now reports
# "orphaned_sections": [] over 273 rows / 273 unique ids / 244 detail sections.
#
# A hardcoded baseline inverts once the backlog it describes is cleaned up: FIXING the
# orphans made this assertion fail, and because it runs in the pre-push hook-tests gate it
# blocked EVERY push, for every session, until the number was refreshed (hit 2026-09-17).
# Empty is the right invariant to hold now -- a new orphan is new damage and should fail
# this test. If a deliberate row-less section is added again, name it here with its reason
# rather than widening the check, and re-verify with check-open-items-duplicate-ids.py first.
expect("no orphaned sections in the live tracker+history pair (a new one is new damage)",
       set(_live_combined["orphaned_sections"]) == set(),
       "got %r" % _live_combined["orphaned_sections"])

passed = sum(1 for ok, _ in results if ok)
print("check-open-items-duplicate-ids tests: %d/%d passed" % (passed, len(results)))
sys.exit(0 if passed == len(results) else 1)
