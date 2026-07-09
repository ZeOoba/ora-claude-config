#!/usr/bin/env python3
"""Regression tests for the 2026-07-08 maintenance-tooling hardening:
  - registry-membership-probe.py: enabled-state regression detection (disabled vs
    dropped) + whole-store-absent grace streak.
  - append-event-log.py: spool-and-drain fallback for OS file-handle locks.

Run: python _tests/test_hardening.py   (exit 0 = all pass)
Pure-function tests + a temp-dir round-trip for the appender spool/drain.
"""
import importlib.util
import os
import sys
import tempfile

MAINT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load(fname, modname):
    spec = importlib.util.spec_from_file_location(modname, os.path.join(MAINT, fname))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


probe = _load("registry-membership-probe.py", "probe")
appender = _load("append-event-log.py", "appender")

_failures = []


def check(name, cond):
    print(("PASS" if cond else "FAIL") + " :: " + name)
    if not cond:
        _failures.append(name)


# ---- Candidate 4: classify_absent (disabled-regression vs true-drop) ----
# prior enabled: a,b,c,d ; now: a still enabled, b disabled, c dropped from registry,
# d still enabled. => regression=[b], drop=[c]
reg, drop = probe.classify_absent(
    ["a", "b", "c", "d"],
    {"a": True, "b": False, "d": True},  # c absent from registry entirely
)
check("classify_absent splits disabled vs dropped", reg == ["b"] and drop == ["c"])
check("classify_absent ignores still-enabled", "a" not in reg and "a" not in drop)

reg2, drop2 = probe.classify_absent([], {"x": True})
check("classify_absent empty prior => nothing absent", reg2 == [] and drop2 == [])

reg3, drop3 = probe.classify_absent(["z"], {})  # store empty/gone
check("classify_absent all-gone => all true-drops", reg3 == [] and drop3 == ["z"])


# ---- Candidate 1: whole-store-absent grace streak ----
s1 = probe.next_missing_streaks({}, {"cc"}, ["cc", "lams"])
check("streak: first miss => 1, present => 0", s1 == {"cc": 1, "lams": 0})
s2 = probe.next_missing_streaks({"cc": 1}, {"cc"}, ["cc", "lams"])
check("streak: consecutive miss increments", s2 == {"cc": 2, "lams": 0})
s3 = probe.next_missing_streaks({"cc": 5}, set(), ["cc", "lams"])
check("streak: reappearance resets to 0", s3 == {"cc": 0, "lams": 0})

check("first absence is NOT actionable (grace)", not probe.missing_is_actionable(1))
check("absence at grace threshold IS actionable", probe.missing_is_actionable(2))
check("absence past threshold stays actionable", probe.missing_is_actionable(3))


# ---- insert_newest ordering sanity (existing behavior, guard against regression) ----
base = "# Log\n\n## 2026-07-01 — older\nbody\n"
out = appender.insert_newest(base, "## 2026-07-08 — newer\nnew")
check("insert_newest puts new entry above existing",
      out.index("newer") < out.index("older"))


# ---- Candidate 3: spool + drain round-trip ----
with tempfile.TemporaryDirectory() as d:
    log = os.path.join(d, "event_log.md")
    with open(log, "w", encoding="utf-8") as f:
        f.write("# Event Log\n\n## 2026-07-01 — seed\nseed body\n")

    # spool two entries (simulate lock), oldest first by ns
    p1 = appender.spool_entry(log, "## 2026-07-08 — first spooled\naaa", 1000)
    p2 = appender.spool_entry(log, "## 2026-07-08 — second spooled\nbbb", 2000)
    check("spool writes files", os.path.isfile(p1) and os.path.isfile(p2))

    drained = appender.drain_spool(log)
    check("drain returns count", drained == 2)
    check("drain removes spooled files", not os.path.isfile(p1) and not os.path.isfile(p2))

    with open(log, encoding="utf-8") as f:
        text = f.read()
    check("both spooled entries now in log",
          "first spooled" in text and "second spooled" in text)
    # oldest-first drain => second (ns2000) inserted last => appears ABOVE first (newest-on-top)
    check("drain preserves newest-on-top order",
          text.index("second spooled") < text.index("first spooled") < text.index("seed"))

    # draining an empty spool is a no-op
    check("drain empty spool => 0", appender.drain_spool(log) == 0)


print()
if _failures:
    print("FAILED (%d): %s" % (len(_failures), ", ".join(_failures)))
    sys.exit(1)
print("ALL PASS")
sys.exit(0)
