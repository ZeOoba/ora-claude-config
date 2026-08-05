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
real_text = open(mip.TRACKER, encoding="utf-8").read()
real_items = mip.parse_open_items(real_text)
real_open_autochecks = {oid for oid, it in real_items.items()
                        if it["status"] == "OPEN" and it["autocheck"] and "kind=" in it["autocheck"]}
previously_affected = {"OI-009", "OI-016", "OI-021", "OI-022", "OI-024", "OI-025"}
expect("none of the previously-affected OI rows are in the live tracker's open_autochecks now",
       real_open_autochecks.isdisjoint(previously_affected),
       "got overlap %r" % (real_open_autochecks & previously_affected))
expect("OI-016 now parses as CLOSED in the live tracker (post-restructure)",
       real_items.get("OI-016", {}).get("status") == "CLOSED",
       "got %r" % real_items.get("OI-016"))

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

passed = sum(1 for ok, _ in results if ok)
print("memory-integrity-probe tests: %d/%d passed" % (passed, len(results)))
sys.exit(0 if passed == len(results) else 1)
