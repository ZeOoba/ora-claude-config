#!/usr/bin/env python3
"""Tests for registry-membership-probe.py — the generated-fleet-block extension.

Covers the two pure functions added 2026-06-11 so session-context.md's roster is
registry-generated instead of hand-edited (the audit's root-cause fix for doctrine
drift): render_fleet_block() and splice_generated_block(). Pure-function tests only —
no registry or session-context I/O.

Run: python test-registry-membership-probe.py   (exit 0 = all pass)
"""
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "rmp", os.path.join(HERE, "registry-membership-probe.py"))
rmp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rmp)

results = []


def expect(label, cond, detail=""):
    results.append((bool(cond), label))
    if not cond:
        print("  FAIL: %s %s" % (label, detail))


DETAIL = {
    "cc": [("ora-alpha", "30 6 * * *"), ("ora-beta", "0 18 * * *")],
    "lams": [("ora-gamma", "50 5,17 * * *")],
}

# --- render_fleet_block ---------------------------------------------------------------
block = rmp.render_fleet_block(DETAIL, ts="2026-06-11T00:00:00")
expect("render: begin marker", rmp.BEGIN_MARKER in block)
expect("render: end marker", rmp.END_MARKER in block)
expect("render: cc count", "CC/MCP — 2 live" in block, repr(block))
expect("render: lams count", "LAMS/Cowork — 1 live" in block, repr(block))
expect("render: task id present", "ora-alpha (30 6 * * *)" in block, repr(block))
expect("render: do-not-hand-edit notice", "do NOT hand-edit" in block)
expect("render: empty fleet renders 0", "CC/MCP — 0 live" in rmp.render_fleet_block({"cc": [], "lams": []}, ts="x"))

# --- splice_generated_block -----------------------------------------------------------
doc = ("# context\n- prose above\n"
       + rmp.BEGIN_MARKER + "\nOLD STALE ROSTER\n" + rmp.END_MARKER
       + "\n- prose below\n")
new_doc, replaced = rmp.splice_generated_block(doc, block)
expect("splice: replaced flag", replaced is True)
expect("splice: old content gone", "OLD STALE ROSTER" not in new_doc)
expect("splice: new content in", "ora-alpha (30 6 * * *)" in new_doc)
expect("splice: prose above kept", "- prose above" in new_doc)
expect("splice: prose below kept", "- prose below" in new_doc)
expect("splice: single begin marker", new_doc.count(rmp.BEGIN_MARKER) == 1)

# idempotent: splicing the same block twice changes nothing the second time
again, replaced2 = rmp.splice_generated_block(new_doc, block)
expect("splice: idempotent", replaced2 is True and again == new_doc)

# markers absent -> unchanged, replaced=False (never guess an anchor)
plain = "# context\n- no markers here\n"
same, replaced3 = rmp.splice_generated_block(plain, block)
expect("splice: no markers -> unchanged", replaced3 is False and same == plain)

# duplicated BEGIN markers -> refuse (which block is real is ambiguous)
dup = doc + "\n" + rmp.BEGIN_MARKER + "\nsecond\n" + rmp.END_MARKER + "\n"
same2, replaced4 = rmp.splice_generated_block(dup, block)
expect("splice: duplicate BEGIN -> refuse", replaced4 is False and same2 == dup)

# stray END before the real pair is ignored; the real pair still replaced
stray = rmp.END_MARKER + "\n" + doc
fixed, replaced5 = rmp.splice_generated_block(stray, block)
expect("splice: stray early END ignored",
       replaced5 is True and "OLD STALE ROSTER" not in fixed
       and fixed.startswith(rmp.END_MARKER))

# END-before-BEGIN with no closing END after -> refuse, unchanged
broken = rmp.END_MARKER + "\nmid\n" + rmp.BEGIN_MARKER + "\ntail\n"
same3, replaced6 = rmp.splice_generated_block(broken, block)
expect("splice: END-before-BEGIN only -> refuse", replaced6 is False and same3 == broken)

# STATE-shape guarantee: enabled_recurring == ids of enabled_recurring_detail
import json as _json
import tempfile as _tempfile
_reg = {"scheduledTasks": [
    {"id": "b", "cronExpression": "0 1 * * *", "enabled": True},
    {"id": "a", "cronExpression": "0 2 * * *", "enabled": True},
    {"id": "c", "cronExpression": None, "enabled": True},          # one-time -> excluded
    {"id": "d", "cronExpression": "0 3 * * *", "enabled": False},  # disabled -> excluded
]}
with _tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as _tf:
    _json.dump(_reg, _tf)
    _p = _tf.name
try:
    ids = rmp.enabled_recurring(_p)
    det = rmp.enabled_recurring_detail(_p)
    expect("STATE shape: ids == ids-of-detail == sorted enabled recurring",
           ids == [i for i, _ in det] == ["a", "b"])
finally:
    os.unlink(_p)

# --- summary ---------------------------------------------------------------------------
passed = sum(1 for ok, _ in results if ok)
print("\nregistry-membership-probe tests: %d/%d passed" % (passed, len(results)))
sys.exit(0 if passed == len(results) else 1)
