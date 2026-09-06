#!/usr/bin/env python3
"""Tests for memory-integrity-probe.py's open-items-tracker parsing (check 4).

Covers two real defects found live 2026-07-27 while triaging a memory-integrity FAIL
report: (1) OI_STATUS_RE.search() took the FIRST **Status:** line in a section body,
misreading an item whose narrative updates its own status inline (OPEN -> CLOSED)
rather than moving to a fresh Closed-table section, as still OPEN; (2) the auto-check
evaluator treated ANY non-empty Auto-check text as a kind=... attempt, so the
convention's own documented "no auto-check configured" placeholder (the literal word
"none", used ~16x across the real tracker) was reported as "malformed or unsupported
kind" for every genuinely-OPEN item that used it (OI-009/016/021/022/024/025).

Run: python _tests/test_memory_integrity_probe.py   (exit 0 = pass)
"""
import importlib.util
import os
import sys

MAINT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location(
    "mip", os.path.join(MAINT, "memory-integrity-probe.py"))
mip = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mip)

results = []


def expect(label, cond, detail=""):
    results.append((bool(cond), label))
    if not cond:
        print("  FAIL: %s %s" % (label, detail))


# --- parse_open_items: status ------------------------------------------------------

# single, clean Status line -> read as-is (baseline, must not regress)
single = "### OI-100\n**Status:** OPEN\n**Opened:** 2026-07-01\n\ndetail\n"
items = mip.parse_open_items(single)
expect("single Status line -> OPEN", items["OI-100"]["status"] == "OPEN",
       "got %r" % items["OI-100"])

# the real OI-016 shape: opens OPEN, narrative resolves it, closes CLOSED inline --
# must read the LAST Status line, not the first.
inline_close = (
    "### OI-016\n**Status:** OPEN\n**Opened:** 2026-07-18\n\n"
    "some narrative about the finding\n\n"
    "**Resolved 2026-07-19:** fixed via commit abc123.\n"
    "**Status:** CLOSED.\n"
    "**Auto-check:** none.\n"
)
items = mip.parse_open_items(inline_close)
expect("inline OPEN->CLOSED narrative reads the LAST Status line as CLOSED",
       items["OI-016"]["status"] == "CLOSED.", "got %r" % items["OI-016"])

# --- parse_open_items: autocheck field extraction (unaffected by the fix) ----------

with_kind = "### OI-200\n**Status:** OPEN\n**Auto-check:** kind=registry_disabled_count fleet=lams expect=0\n"
items = mip.parse_open_items(with_kind)
expect("autocheck text captured verbatim",
       items["OI-200"]["autocheck"] == "kind=registry_disabled_count fleet=lams expect=0",
       "got %r" % items["OI-200"])

# --- main()'s open_autochecks filter: "none"-style text must NOT be evaluated ------
# (regression guard for the false "malformed or unsupported kind" warning)

def make_tracker(body):
    return ("## Open\n\n| ID | Opened | Source | One-line |\n|----|----|----|----|\n"
            "| [OI-100](#OI-100) | 2026-07-01 | fixture | one-line |\n\n"
            "## Closed\n\n| ID | Opened | Closed | Source | One-line |\n|----|----|----|----|----|\n\n"
            + body)


none_variants = [
    "### OI-100\n**Status:** OPEN\n**Auto-check:** none.\n",
    "### OI-100\n**Status:** OPEN\n**Auto-check:** none (not a fleet-registry item).\n",
    "### OI-100\n**Status:** OPEN\n**Auto-check:** none (not a fleet-registry item; closure evidence is the landed commit above).\n",
]
for i, body in enumerate(none_variants):
    items = mip.parse_open_items(make_tracker(body))
    open_autochecks = [(oid, it) for oid, it in items.items()
                       if it["status"] == "OPEN" and it["autocheck"] and "kind=" in it["autocheck"]]
    expect("none-variant %d excluded from open_autochecks (no false warning)" % i,
           open_autochecks == [], "got %r" % open_autochecks)

# a genuine kind= attempt (even a bogus one) still enters the evaluation pool --
# the fix must narrow scope to real attempts, not silence malformed-kind detection entirely.
bogus_kind = "### OI-100\n**Status:** OPEN\n**Auto-check:** kind=not_a_real_kind foo=bar\n"
items = mip.parse_open_items(make_tracker(bogus_kind))
open_autochecks = [(oid, it) for oid, it in items.items()
                   if it["status"] == "OPEN" and it["autocheck"] and "kind=" in it["autocheck"]]
expect("a real (even bogus) kind= attempt still enters the evaluation pool",
       len(open_autochecks) == 1, "got %r" % open_autochecks)
result = mip.eval_autocheck(mip.parse_kv(open_autochecks[0][1]["autocheck"]), {})
expect("bogus kind= still evaluates to None (malformed/unsupported) -- detection not silenced",
       result is None, "got %r" % result)

# a real, valid kind= attempt still evaluates normally.
valid_kind = "### OI-100\n**Status:** OPEN\n**Auto-check:** kind=registry_disabled_count fleet=all expect=5\n"
items = mip.parse_open_items(make_tracker(valid_kind))
open_autochecks = [(oid, it) for oid, it in items.items()
                   if it["status"] == "OPEN" and it["autocheck"] and "kind=" in it["autocheck"]]
expect("valid kind= attempt enters the evaluation pool", len(open_autochecks) == 1)
result = mip.eval_autocheck(mip.parse_kv(open_autochecks[0][1]["autocheck"]),
                            {"disabled_by_fleet": {"cc": 3, "lams": 2}})
expect("valid kind=registry_disabled_count evaluates True when it matches", result is True,
       "got %r" % result)

# --- the CANONICAL tracker itself, right now: none of the 6 known-affected items -----
# should enter open_autochecks anymore (regression guard for the real-world fix).
#
# Read BOTH files (split 2026-09-06, Automation Audit R22-4): OI-016 is CLOSED, so
# its `### OI-016` section now lives in the history companion, not the live
# tracker -- parsing the tracker alone would show it as absent (None), not as the
# CLOSED status this test exists to confirm. combined_items mirrors exactly what
# main()'s own check 4 does (parse each file separately, tracker wins on conflict).
real_text = open(mip.TRACKER, encoding="utf-8").read()
real_items = mip.parse_open_items(real_text)
real_history_items = {}
if os.path.isfile(mip.TRACKER_HISTORY):
    real_history_items = mip.parse_open_items(
        open(mip.TRACKER_HISTORY, encoding="utf-8").read())
combined_real_items = dict(real_history_items)
combined_real_items.update(real_items)
real_open_autochecks = {oid for oid, it in combined_real_items.items()
                        if it["status"] == "OPEN" and it["autocheck"] and "kind=" in it["autocheck"]}
previously_affected = {"OI-009", "OI-016", "OI-021", "OI-022", "OI-024", "OI-025"}
expect("none of the previously-affected OI rows are in the live tracker's open_autochecks now",
       real_open_autochecks.isdisjoint(previously_affected),
       "got overlap %r" % (real_open_autochecks & previously_affected))
expect("OI-016 now parses as CLOSED (tracker+history combined, post-split)",
       combined_real_items.get("OI-016", {}).get("status") == "CLOSED",
       "got %r" % combined_real_items.get("OI-016"))
expect("OI-016's section actually lives in the history file now, not the live tracker",
       "OI-016" in real_history_items and "OI-016" not in real_items,
       "history has it: %r, tracker has it: %r" % ("OI-016" in real_history_items, "OI-016" in real_items))

# --- head_orphans: a back-link to MEMORY.md is not an orphan pointer ----------------
# Regression guard for a false FAIL observed live on the 2026-08-05 ora-health-guard run,
# which reported "orphan index link IN GIT ... MEMORY.md" while MEMORY.md was demonstrably
# present in HEAD (git cat-file -e succeeded).
#
# Two individually-correct changes combined to produce it:
#   * head_orphans() removed MEMORY.md from head_FILES -- the set that answers "what does
#     HEAD actually contain?" -- erasing ground truth about a file that IS committed.
#   * the 2026-08-03 sub-index-following change unions each linked INDEX_*.md's links into
#     head_linked, and the real INDEX_reference.md ends with a "Back to [MEMORY.md]" link
#     (added by b91475a, the ## Reference split).
# Result: MEMORY.md appears in head_linked, has been deleted from head_files, and is
# reported as a pointer a clone would find broken -- which it never was.
#
# The self/back-link must be dropped from head_LINKED (there is nothing to verify: the
# index is the thing doing the linking), never from head_FILES.

import subprocess
import tempfile


def _build_repo(tmp, backlink, commit_note_b=True, root_self_link=False):
    """A minimal memory dir under git. Everything is committed unless commit_note_b=False."""
    for cmd in (["git", "init", "-q"],
                ["git", "config", "user.email", "t@example.invalid"],
                ["git", "config", "user.name", "fixture"]):
        subprocess.run(cmd, cwd=tmp, check=True, capture_output=True)
    root = "# Index\n- [Ref sub-index](INDEX_reference.md)\n- [note a](note_a.md)\n"
    if root_self_link:
        root += "- [this index](MEMORY.md)\n"
    sub = "# Reference\n- [note b](note_b.md)\n"
    if backlink:
        sub += "\nBack to [MEMORY.md](MEMORY.md)\n"
    for name, body in (("MEMORY.md", root), ("INDEX_reference.md", sub),
                       ("note_a.md", "x\n"), ("note_b.md", "x\n")):
        with open(os.path.join(tmp, name), "w", encoding="utf-8") as fh:
            fh.write(body)
    staged = ["MEMORY.md", "INDEX_reference.md", "note_a.md"]
    if commit_note_b:
        staged.append("note_b.md")
    subprocess.run(["git", "add"] + staged, cwd=tmp, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-qm", "fixture"], cwd=tmp, check=True, capture_output=True)


def _orphans_in(**kw):
    """head_orphans() against a throwaway repo. Restores mip.MEM so later checks are unaffected."""
    tmp = tempfile.mkdtemp(prefix="mip_head_orphans_")
    _build_repo(tmp, **kw)
    saved = mip.MEM
    try:
        mip.MEM = tmp
        return mip.head_orphans()
    finally:
        mip.MEM = saved


got = _orphans_in(backlink=True)
expect("sub-index back-link to MEMORY.md is NOT reported as an orphan", got == [], "got %r" % got)

got = _orphans_in(backlink=False)
expect("baseline: no back-link, all committed -> no orphans", got == [], "got %r" % got)

got = _orphans_in(backlink=False, root_self_link=True)
expect("MEMORY.md linking itself is NOT reported as an orphan", got == [], "got %r" % got)

# The point of the check must survive the fix: a committed pointer to an uncommitted file
# is still caught, and is not masked by the back-link handling.
got = _orphans_in(backlink=True, commit_note_b=False)
expect("true positive preserved: committed pointer to an UNCOMMITTED file is still reported",
       got == ["note_b.md"], "got %r" % got)

# --- check 0: the size gate covers SUB-INDEXES, not just MEMORY.md -------------------
# Added 2026-08-16 (Gabriel-ratified). The 2026-08-03 split made sub-indexes the lever
# that keeps MEMORY.md under the 24.4KB Read-tool limit, but check 0 stat'd `INDEX`
# (MEMORY.md) ALONE -- so the files absorbing the growth were themselves ungated.
# Measured the day this was written: INDEX_reference.md was 18,361 B, LARGER than the
# 16,936 B root index it had been split out of, and ~6KB from the same ceiling, with
# nothing anywhere that would ever warn. The fix for a bounded artifact had created an
# unbounded child. Sub-indexes are gated on the SAME constants and the SAME severities
# as the root: a sub-index past HARD is exactly as unreadable as the root would be, and
# treating it as a lesser finding rebuilds the blind spot one level down.

W, H = mip.MEMORY_WARN_BYTES, mip.MEMORY_HARD_BYTES

iss, warn = mip.size_gate([("MEMORY.md", W - 1)])
expect("root under WARN -> silent", (iss, warn) == ([], []), "got %r / %r" % (iss, warn))

iss, warn = mip.size_gate([("MEMORY.md", W + 1)])
expect("root past WARN -> 1 warning, 0 issues", len(iss) == 0 and len(warn) == 1,
       "got %r / %r" % (iss, warn))

iss, warn = mip.size_gate([("MEMORY.md", H + 1)])
expect("root past HARD -> 1 issue, 0 warnings", len(iss) == 1 and len(warn) == 0,
       "got %r / %r" % (iss, warn))

# the new coverage: identical thresholds and severities for a sub-index
iss, warn = mip.size_gate([("MEMORY.md", 100), ("INDEX_reference.md", W - 1)])
expect("sub-index under WARN -> silent", (iss, warn) == ([], []), "got %r / %r" % (iss, warn))

iss, warn = mip.size_gate([("MEMORY.md", 100), ("INDEX_reference.md", W + 1)])
expect("sub-index past WARN -> 1 warning naming the sub-index",
       len(iss) == 0 and len(warn) == 1 and "INDEX_reference.md" in warn[0],
       "got %r / %r" % (iss, warn))

iss, warn = mip.size_gate([("MEMORY.md", 100), ("INDEX_reference.md", H + 1)])
expect("sub-index past HARD -> a real ISSUE (same severity as root), naming the sub-index",
       len(iss) == 1 and len(warn) == 0 and "INDEX_reference.md" in iss[0],
       "got %r / %r" % (iss, warn))

# boundary: the constants are exclusive (> not >=), matching the pre-existing root behaviour.
# Note H is itself past W, so exactly-at-HARD is not a HARD breach but IS a WARN breach --
# the two thresholds are separate questions and an earlier version of this test conflated them.
iss, warn = mip.size_gate([("MEMORY.md", W), ("INDEX_reference.md", W)])
expect("exactly-at-WARN is not a breach (> semantics preserved, root and sub-index)",
       (iss, warn) == ([], []), "got %r / %r" % (iss, warn))

iss, warn = mip.size_gate([("INDEX_reference.md", H)])
expect("exactly-at-HARD is not a HARD breach, but does warn (it is past WARN)",
       len(iss) == 0 and len(warn) == 1, "got %r / %r" % (iss, warn))

# every breaching file is reported, not just the first
iss, warn = mip.size_gate([("MEMORY.md", H + 1), ("INDEX_a.md", H + 1), ("INDEX_b.md", W + 1)])
expect("all breaching index files reported (2 issues + 1 warning)",
       len(iss) == 2 and len(warn) == 1, "got %r / %r" % (iss, warn))

# --- check 0 wiring: sized_index_files() actually collects the sub-indexes ------------
# The pure gate above is worthless if main() never hands it a sub-index. This proves the
# collection step, which is where the original defect lived.

def _sized_in(names_bodies, subindexes):
    tmp = tempfile.mkdtemp(prefix="mip_size_gate_")
    for name, body in names_bodies:
        with open(os.path.join(tmp, name), "w", encoding="utf-8") as fh:
            fh.write(body)
    return mip.sized_index_files(tmp, os.path.getsize(os.path.join(tmp, "MEMORY.md")),
                                 subindexes)


def _sized_only(names_bodies, subindexes):
    """Just the sized list, for cases that do not care about the unstattable channel."""
    return _sized_in(names_bodies, subindexes)[0]

sized = _sized_only([("MEMORY.md", "x" * 10), ("INDEX_reference.md", "y" * 20)],
                    ["INDEX_reference.md"])
expect("sized_index_files returns the root FIRST, then each sub-index, with real byte sizes",
       sized == [("MEMORY.md", 10), ("INDEX_reference.md", 20)], "got %r" % (sized,))

sized = _sized_only([("MEMORY.md", "x" * 10)], [])
expect("no sub-indexes -> root only (pre-split behaviour unchanged)",
       sized == [("MEMORY.md", 10)], "got %r" % (sized,))

# --- the two skip reasons are NOT the same, and must not be collapsed ------------------
# GONE: deleted between collect_indexed_links() and the stat. Skipped SILENTLY -- check 1
# already reports it as an orphan pointer, and a probe that cannot look must not invent a
# finding.
sized, unstattable = _sized_in([("MEMORY.md", "x" * 10)], ["INDEX_missing.md"])
expect("a VANISHED sub-index is skipped, not invented as a size finding",
       sized == [("MEMORY.md", 10)], "got %r" % (sized,))
expect("a VANISHED sub-index is not reported as unstattable (it is an orphan, not a lock)",
       unstattable == [], "got %r" % (unstattable,))

# PRESENT BUT UNREADABLE: any other OSError. The file is still adopted and still growing;
# it just was not measured. Skipping that silently means the gate quietly stops covering a
# file while still reporting OK -- the exact blind-spot class this check exists to close.
# Simulated by monkeypatching getsize, since producing a real lock is platform-specific.
_real_getsize = os.path.getsize


def _getsize_locking(path):
    if os.path.basename(path) == "INDEX_locked.md":
        raise PermissionError(13, "The process cannot access the file")
    return _real_getsize(path)


tmp = tempfile.mkdtemp(prefix="mip_locked_")
for _n, _b in (("MEMORY.md", "x" * 10), ("INDEX_locked.md", "y" * 20)):
    with open(os.path.join(tmp, _n), "w", encoding="utf-8") as fh:
        fh.write(_b)
os.path.getsize = _getsize_locking
try:
    sized, unstattable = mip.sized_index_files(
        tmp, _real_getsize(os.path.join(tmp, "MEMORY.md")), ["INDEX_locked.md"])
finally:
    os.path.getsize = _real_getsize
expect("a LOCKED sub-index is left out of the sized set (cannot measure what will not stat)",
       sized == [("MEMORY.md", 10)], "got %r" % (sized,))
expect("a LOCKED sub-index IS reported as unstattable -- coverage loss must not be silent",
       len(unstattable) == 1 and unstattable[0][0] == "INDEX_locked.md",
       "got %r" % (unstattable,))

# --- the LIVE corpus: every sub-index is now actually under the gate ------------------
# NOT an exact-count assertion. sized_index_files() deliberately SKIPS a sub-index it
# cannot stat, so `len(live_sized) == 1 + len(live_subs)` would additionally assert that
# no concurrent write happened between collect_indexed_links() and sized_index_files() --
# something this test cannot control and has no business claiming. The memory dir is
# written by many sessions at once (the 2026-08-16 split rewrote MEMORY.md twice inside a
# single minute), and this file is swept by the pre-push hook-tests gate, so that race
# would surface as a spurious FAIL blocking an unrelated push.
#
# What is actually being verified is the WIRING -- that the root is gated first and that
# nothing outside the adopted sub-index set sneaks in. Both hold regardless of a race.
live_idx = open(mip.INDEX, encoding="utf-8").read()
_, live_subs = mip.collect_indexed_links(live_idx, mip.MEM)
live_sized, live_unstattable = mip.sized_index_files(
    mip.MEM, os.path.getsize(mip.INDEX), live_subs)
expect("live run gates the root FIRST",
       live_sized and live_sized[0][0] == "MEMORY.md", "got %r" % (live_sized,))
expect("live run gates only the root plus sub-indexes MEMORY.md adopts (race-tolerant)",
       len(live_sized) <= 1 + len(live_subs)
       and all(n == "MEMORY.md" or n in live_subs for n, _ in live_sized),
       "subs=%r sized=%r" % (live_subs, live_sized))
expect("every gated entry carries a non-negative byte size",
       all(isinstance(b, int) and b >= 0 for _, b in live_sized), "got %r" % (live_sized,))

# The `<=` above is deliberately weak, so on its own it would still pass if
# sized_index_files() regressed to returning the root alone -- i.e. the exact defect this
# whole change fixes. The deterministic fixture cases above catch that, and so does this:
# every sub-index that can still be MEASURED must have been gated.
#
# The predicate is os.path.getsize in a try/except -- NOT os.path.exists. That distinction
# is the whole point: sized_index_files() skips on a stat FAILURE, and "missing" is only
# one way to fail. A file locked mid-os.replace, or held by an AV or indexer, raises
# PermissionError while remaining perfectly present, so exists() answers True about a file
# that could not be measured and the assertion fails on a healthy tree. Asking the same
# question the code asks is what makes this sound; an earlier version asked a different one
# and claimed, wrongly, that the two could not diverge.
#
# THE CLAIM IS AGAINST BOTH CHANNELS, and a leftover gets ONE re-observation.
#
# Two earlier versions of this assertion raced, in the same way each time: they compared a
# set observed INSIDE sized_index_files (call it T2) against a fresh filesystem sweep taken
# afterwards (T3), so any file whose state differed between T2 and T3 failed the test on a
# healthy tree. Re-sweeping with getsize instead of exists narrowed the window but did not
# close it -- a sub-index locked at T2 lands in `unstattable`, and if the lock clears by T3
# it looks measurable-but-ungated. The unstattable channel was in the failure MESSAGE but
# not in the PREDICATE, which is precisely the gap.
#
# So: a sub-index is satisfied if it appears in EITHER channel -- gated, or reported
# unstattable. Anything still missing gets one re-observation, which distinguishes the two
# things that produce a leftover:
#   * a RACE (lock, or a delete-then-rename save that leaves a GONE window) -- self-clearing,
#     so the second call covers it and the claim passes;
#   * a real REGRESSION to root-only collection -- populates NEITHER channel, on both calls,
#     so the leftover survives and the test fails. The guard keeps its teeth.
live_gated = {n for n, _ in live_sized}
live_unstat = {n for n, _ in live_unstattable}
missing = [n for n in live_subs if n not in live_gated and n not in live_unstat]
if missing:
    _sized2, _unstat2 = mip.sized_index_files(mip.MEM, os.path.getsize(mip.INDEX), live_subs)
    _covered2 = {n for n, _ in _sized2} | {n for n, _ in _unstat2}
    missing = [n for n in missing if n not in _covered2]
expect("every adopted sub-index was gated or reported unstattable (regression guard)",
       not missing,
       "missing=%r gated=%r unstattable=%r" % (
           missing, sorted(live_gated), live_unstattable))
expect("nothing reported unstattable also appears in the sized set (channels are disjoint)",
       not ({n for n, _ in live_unstattable} & live_gated),
       "unstattable=%r gated=%r" % (live_unstattable, sorted(live_gated)))

# --- check 4a: dead pointers across the tracker/history split (2026-09-06, R22-4) ---
# OI_REF_RE now captures WHICH filename a reference names; a reference naming the
# wrong file for where an id's anchor actually lives is a genuinely dead link (a
# markdown reader following it literally lands on a file with no such heading),
# not merely a style nit -- so it must be caught the same as an id that doesn't
# exist anywhere. Full main()-shaped fixtures under ORA_MEMORY_DIR, since this
# logic lives inline in main() rather than in a separately-testable function.

def _run_main_in(mem_dir):
    """main() against a throwaway memory dir, capturing stdout. Exit code + output.

    MEM/INDEX/TRACKER/TRACKER_HISTORY are module-level constants computed ONCE at
    import time from ORA_MEMORY_DIR -- setting that env var here is too late to
    affect them (mip was already imported at the top of this file). Monkey-patch
    the attributes directly instead, matching _orphans_in()'s established pattern
    above for the same reason. governor-drift delegation (check 2a) is skipped by
    main() itself whenever ORA_MEMORY_DIR is set (sandbox isolation, 2026-07-29)
    -- setting it too is harmless belt-and-suspenders, not load-bearing here.
    """
    import io, contextlib
    saved = (mip.MEM, mip.INDEX, mip.TRACKER, mip.TRACKER_HISTORY)
    saved_env = os.environ.get("ORA_MEMORY_DIR")
    mip.MEM = mem_dir
    mip.INDEX = os.path.join(mem_dir, "MEMORY.md")
    mip.TRACKER = os.path.join(mem_dir, "open-items-tracker.md")
    mip.TRACKER_HISTORY = os.path.join(mem_dir, "open-items-tracker-history.md")
    os.environ["ORA_MEMORY_DIR"] = mem_dir
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            try:
                mip.main()
                rc = 0
            except SystemExit as e:
                rc = e.code
    finally:
        mip.MEM, mip.INDEX, mip.TRACKER, mip.TRACKER_HISTORY = saved
        if saved_env is None:
            os.environ.pop("ORA_MEMORY_DIR", None)
        else:
            os.environ["ORA_MEMORY_DIR"] = saved_env
    return rc, buf.getvalue()


def _write(mem_dir, name, body):
    with open(os.path.join(mem_dir, name), "w", encoding="utf-8") as fh:
        fh.write(body)


def _base_memory_fixture(mem_dir, tracker_body="", history_body="", extra_links=()):
    """MEMORY.md linking both tracker files (so check 1 doesn't flag them unlisted),
    plus whatever tracker/history bodies the case needs. extra_links names any
    OTHER file the test will create (e.g. a third-party referrer) so check 1's
    index reconciliation stays clean and doesn't drown the OI-specific assertion
    in an unrelated "unlisted file" finding."""
    extra = "".join("- [%s](%s)\n" % (n, n) for n in extra_links)
    _write(mem_dir, "MEMORY.md",
           "# Index\n- [Open Items Tracker](open-items-tracker.md)\n"
           "- [History](open-items-tracker-history.md)\n" + extra)
    _write(mem_dir, "open-items-tracker.md",
           "## Open\n\n" + tracker_body)
    _write(mem_dir, "open-items-tracker-history.md",
           "## Closed\n\n" + history_body)


_tmp = tempfile.mkdtemp(prefix="mip_oi_split_")
try:
    # OI-700 closed, section lives in history. A reference from a THIRD file naming
    # the OLD (tracker) filename is stale -- the anchor is not there anymore.
    _base_memory_fixture(_tmp, history_body="### OI-700\n**Status:** CLOSED\n",
                         extra_links=["some_note.md"])
    _write(_tmp, "some_note.md",
           "see [OI-700](open-items-tracker.md#OI-700) for detail\n")
    rc, out = _run_main_in(_tmp)
    expect("wrong-file reference (tracker named, id actually in history) -> FAIL",
           rc == 1, "rc=%r out=%r" % (rc, out))
    expect("the wrong-file finding names which file the id is ACTUALLY in",
           "actually in open-items-tracker-history.md" in out, out)
finally:
    _sh_ = __import__("shutil")
    _sh_.rmtree(_tmp, ignore_errors=True)

_tmp = tempfile.mkdtemp(prefix="mip_oi_split_")
try:
    # Same id, but the reference correctly names the history file -- clean.
    _base_memory_fixture(_tmp, history_body="### OI-701\n**Status:** CLOSED\n",
                         extra_links=["some_note.md"])
    _write(_tmp, "some_note.md",
           "see [OI-701](open-items-tracker-history.md#OI-701) for detail\n")
    rc, out = _run_main_in(_tmp)
    expect("correct-file reference (history named, id in history) -> OK",
           rc == 0, "rc=%r out=%r" % (rc, out))
finally:
    __import__("shutil").rmtree(_tmp, ignore_errors=True)

_tmp = tempfile.mkdtemp(prefix="mip_oi_split_")
try:
    # An id that exists in NEITHER file is still the plain old dead pointer, filename aside.
    _base_memory_fixture(_tmp, extra_links=["some_note.md"])
    _write(_tmp, "some_note.md",
           "see [OI-999](open-items-tracker.md#OI-999) for detail\n")
    rc, out = _run_main_in(_tmp)
    expect("reference to an id that exists in neither file -> FAIL (plain dead pointer)",
           rc == 1, "rc=%r out=%r" % (rc, out))
    expect("plain dead-pointer wording used when the id resolves nowhere",
           "has no matching row in either" in out, out)
finally:
    __import__("shutil").rmtree(_tmp, ignore_errors=True)

_tmp = tempfile.mkdtemp(prefix="mip_oi_split_")
try:
    # A tracker-internal self-link and a history-internal self-link are never
    # flagged, matching the pre-existing self-link exclusion (now for BOTH files).
    _base_memory_fixture(
        _tmp,
        tracker_body="### OI-702\n**Status:** OPEN\n\nsee [self](#OI-702)\n",
        history_body="### OI-703\n**Status:** CLOSED\n\nsee [self](#OI-703)\n",
    )
    rc, out = _run_main_in(_tmp)
    expect("bare self-links within either file are never treated as dead pointers -> OK",
           rc == 0, "rc=%r out=%r" % (rc, out))
finally:
    __import__("shutil").rmtree(_tmp, ignore_errors=True)

_tmp = tempfile.mkdtemp(prefix="mip_oi_split_")
try:
    # History file absent entirely (pre-split memory dir, or a dir that just hasn't
    # split yet) must not crash -- optional companion, same posture as the tracker's
    # own optional-file handling.
    _write(_tmp, "MEMORY.md", "# Index\n- [Open Items Tracker](open-items-tracker.md)\n")
    _write(_tmp, "open-items-tracker.md",
           "## Open\n\n### OI-704\n**Status:** OPEN\n")
    rc, out = _run_main_in(_tmp)
    expect("no history file at all -> probe still runs cleanly (optional companion)",
           rc == 0, "rc=%r out=%r" % (rc, out))
finally:
    __import__("shutil").rmtree(_tmp, ignore_errors=True)

passed = sum(1 for ok, _ in results if ok)
print("memory-integrity-probe tests: %d/%d passed" % (passed, len(results)))
sys.exit(0 if passed == len(results) else 1)
