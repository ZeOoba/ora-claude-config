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

# --- ratified_drops (2026-06-11 auto-ratification) -------------------------------------
import datetime as _dt
_TODAY = _dt.date(2026, 6, 11)
# event_log.md entries are '## YYYY-MM-DD' sections (append-event-log.py's
# enforced header level). This fixture previously used '### ' and silently stopped
# matching after the probe's 2026-07-16 split fix ('### '->'## '); realigned here.
_LOG = ("# Event log\nintro prose\n"
        "\n## 2026-06-11 — LAMS registry cleanup (RATIFIED) + lesson\n"
        "Removed scheduled-task-integrity-guard and others.\n"
        "\n## 2026-05-01 — old cleanup (RATIFIED)\n"
        "Removed ora-ancient-task.\n"
        "\n## 2026-06-10 — unrelated note, no keyword\n"
        "Mentions ora-unratified-task but never the magic word.\n")
expect("ratify: named in recent RATIFIED entry",
       rmp.ratified_drops(_LOG, ["scheduled-task-integrity-guard"], _TODAY)
       == {"scheduled-task-integrity-guard"})
expect("ratify: outside 14d window -> not ratified",
       rmp.ratified_drops(_LOG, ["ora-ancient-task"], _TODAY) == set())
expect("ratify: entry lacks RATIFIED token -> not ratified",
       rmp.ratified_drops(_LOG, ["ora-unratified-task"], _TODAY) == set())
expect("ratify: id absent from log -> not ratified",
       rmp.ratified_drops(_LOG, ["ora-never-mentioned"], _TODAY) == set())
expect("ratify: empty/garbage log -> empty set",
       rmp.ratified_drops("", ["x"], _TODAY) == set()
       and rmp.ratified_drops("\n## not-a-date (RATIFIED) x\nx\n", ["x"], _TODAY) == set())
expect("ratify: empty id never matches",
       rmp.ratified_drops(_LOG, [""], _TODAY) == set())

# --- retired_drops (2026-07-17 retirement-prose reconciliation) ------------------------
# The real regression: ora-skills-reimport-watch was retired 2026-07-17 in two
# inline-dated prose lines that live under an OLDER '## 2026-07-16' header and use
# 'retirement'/'Retirement', never the ceremonial 'RATIFIED' token -- so it raised a
# false [ACTION]. Fixture mirrors that exact shape plus the must-NOT-reconcile cases.
_TODAY2 = _dt.date(2026, 7, 17)
_RLOG = (
    "# Event log\n"
    "\n## 2026-07-16 — plugin bundle work (section header predates the retirement)\n"
    "- plugin prose that merely mentions ora-keep-task in passing\n"
    "2026-07-17: ora-skills-reimport-watch retirement (part 1/2) — paused, folder archived.\n"
    "2026-07-17: ora-skills-reimport-watch registry entry deleted. Retirement completed. Closed.\n"
    "\n## 2026-07-17 — bullet-style retirement, no inline date (inherits header date)\n"
    "- **ora-bullet-task** retired this session; registry entry removed.\n"
    "2026-07-17: ora-decomm-task decommissioned and removed from the registry.\n"
    "\n## 2026-07-10 — incident report — must NOT reconcile\n"
    "- ora-silent-victim disappeared from the registry — the 2026-06-09 silent-drop "
    "failure mode; investigating.\n"
    "\n## 2026-06-20 — old retirement, outside the 14d window\n"
    "2026-06-20: ora-old-retiree retirement completed.\n"
)
expect("retire: inline-dated prose line under an older header reconciles (real case)",
       rmp.retired_drops(_RLOG, ["ora-skills-reimport-watch"], _TODAY2)
       == {"ora-skills-reimport-watch"})
expect("retire: bullet line inherits '## ' header date when no inline date",
       rmp.retired_drops(_RLOG, ["ora-bullet-task"], _TODAY2) == {"ora-bullet-task"})
expect("retire: 'decommission' verb also reconciles",
       rmp.retired_drops(_RLOG, ["ora-decomm-task"], _TODAY2) == {"ora-decomm-task"})
expect("retire: incident/silent-drop line (no retire verb) does NOT reconcile",
       rmp.retired_drops(_RLOG, ["ora-silent-victim"], _TODAY2) == set())
expect("retire: id merely mentioned (no retire verb on its line) does NOT reconcile",
       rmp.retired_drops(_RLOG, ["ora-keep-task"], _TODAY2) == set())
expect("retire: retirement outside 14d window does NOT reconcile",
       rmp.retired_drops(_RLOG, ["ora-old-retiree"], _TODAY2) == set())
expect("retire: same-line coupling — retire verb + id must share a line",
       rmp.retired_drops("\n## 2026-07-17 — mix\n- ora-alpha noted here\n- ora-beta retired\n",
                         ["ora-alpha"], _TODAY2) == set())
expect("retire: empty log / empty id -> empty set",
       rmp.retired_drops("", ["x"], _TODAY2) == set()
       and rmp.retired_drops(_RLOG, [""], _TODAY2) == set())
expect("retire: multiple ids resolve independently in one pass",
       rmp.retired_drops(_RLOG, ["ora-bullet-task", "ora-decomm-task", "ora-silent-victim"],
                         _TODAY2) == {"ora-bullet-task", "ora-decomm-task"})

# --- completion-only gate (2026-07-17 residual-risk fix) -------------------------------
# A line that merely PLANS / proposes / negates / is mid-flight must never reconcile a
# genuine drop -- only accomplished-fact wording qualifies. This closes the forward-
# looking 'should retire ora-X next quarter' hole the first cut of retired_drops carried.
_PLAN = (
    "\n## 2026-07-17 — planning + in-progress notes (must NOT reconcile)\n"
    "- we should retire ora-plan-victim next quarter once the consumers migrate\n"
    "- propose to decommission ora-prop-victim; awaiting Gabriel sign-off\n"
    "- do not retire ora-neg-victim -- it is still load-bearing\n"
    "2026-07-17: ora-inprog-victim registry entry still exists, pending deletion next session\n"
    "2026-07-17: ora-done-victim retirement completed; registry entry deleted. Closed.\n"
)
expect("complete-gate: 'should retire ... next quarter' does NOT reconcile",
       rmp.retired_drops(_PLAN, ["ora-plan-victim"], _TODAY2) == set())
expect("complete-gate: 'propose to decommission' does NOT reconcile",
       rmp.retired_drops(_PLAN, ["ora-prop-victim"], _TODAY2) == set())
expect("complete-gate: negated 'do not retire' does NOT reconcile",
       rmp.retired_drops(_PLAN, ["ora-neg-victim"], _TODAY2) == set())
expect("complete-gate: in-progress 'still exists, pending deletion' does NOT reconcile",
       rmp.retired_drops(_PLAN, ["ora-inprog-victim"], _TODAY2) == set())
expect("complete-gate: accomplished completion line reconciles",
       rmp.retired_drops(_PLAN, ["ora-done-victim"], _TODAY2) == {"ora-done-victim"})

# _retirement_completed truth-table (the crux of the fix)
expect("complete-helper: accomplished-fact wording -> True",
       all(rmp._retirement_completed(s) for s in
           ("ora-x retired this session", "ora-x decommissioned", "ora-x deregistered",
            "retirement completed", "registry entry deleted", "removed from the registry")))
expect("complete-helper: planned / hypothetical / negated / in-progress -> False",
       not any(rmp._retirement_completed(s) for s in
               ("we should retire ora-x", "plan to decommission ora-x", "do not retire ora-x",
                "ora-x retirement (part 1/2)", "entry still exists, pending deletion",
                "considering deleting the registry entry", "retirement incomplete")))

# --- summary ---------------------------------------------------------------------------
passed = sum(1 for ok, _ in results if ok)
print("\nregistry-membership-probe tests: %d/%d passed" % (passed, len(results)))
sys.exit(0 if passed == len(results) else 1)
