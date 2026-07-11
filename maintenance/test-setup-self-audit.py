#!/usr/bin/env python3
"""Tests for setup-self-audit.py — the 2026-07-09 registry-derived rewrite.

Covers the pure functions that replaced the stale hand-curated EXPECTED_TASKS
baseline (retired 2026-07-09): classify_fleet() (registry->disk breaks +
disk->registry orphans — the one check no other probe covers) and
fleet_count_claims() (SoR section-7-scoped drift parsing). Pure-function
tests only — no registry, disk-store, or SoR I/O.

Run: python test-setup-self-audit.py   (exit 0 = all pass)
"""
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "ssa", os.path.join(HERE, "setup-self-audit.py"))
ssa = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ssa)

results = []


def expect(label, cond, detail=""):
    results.append((bool(cond), label))
    if not cond:
        print("  FAIL: %s %s" % (label, detail))


def t(i, enabled=True, exists=True):
    return {"id": i, "enabled": enabled, "exists": exists}


# ---- classify_fleet ----
# clean: every enabled filePath resolves, every disk folder is registered
broken, orphans = ssa.classify_fleet(
    [t("a"), t("b")], ["a", "b"])
expect("clean fleet -> no broken, no orphans", broken == [] and orphans == [])

# enabled task whose SKILL.md filePath does not resolve -> broken
broken, orphans = ssa.classify_fleet(
    [t("a"), t("b", exists=False)], ["a", "b"])
expect("enabled+missing filePath -> broken", broken == ["b"], broken)

# DISABLED task with a missing filePath is NOT broken (canary-model-check class)
broken, _ = ssa.classify_fleet(
    [t("a"), t("c", enabled=False, exists=False)], ["a", "c"])
expect("disabled+missing filePath -> not broken", broken == [], broken)

# disk folder registered in NEITHER fleet -> orphan (the 16-vs-13 drift class)
broken, orphans = ssa.classify_fleet(
    [t("a")], ["a", "ora-entry-market-scan", "ora-calibration-snapshot"])
expect("unregistered folders -> orphans, sorted",
       orphans == ["ora-calibration-snapshot", "ora-entry-market-scan"], orphans)

# a DISABLED but registered task's folder is NOT an orphan
_, orphans = ssa.classify_fleet(
    [t("a"), t("canary", enabled=False, exists=True)], ["a", "canary"])
expect("disabled-but-registered folder -> not an orphan", orphans == [], orphans)

# registered in the OTHER fleet only -> still not an orphan (union semantics)
_, orphans = ssa.classify_fleet(
    [t("a"), {"id": "lams-task", "enabled": True, "exists": True}], ["a", "lams-task"])
expect("registered anywhere in the union -> not an orphan", orphans == [], orphans)

# ---- fleet_count_claims (SoR section-7-headline-scoped) ----
SOR = """# System of Record
## 6. Something else
There are 45 tasks in this historical section that must NOT be parsed.
## 7. Scheduled fleet
The fleet has 19 live tasks and also 15 tasks on one side.
Nothing here says fourteen.
### Historical pre-Stage-2 snapshot
45 tasks (42 enabled) -- dated history, legitimately stated, must NOT be parsed.
## 8. Next section
99 tasks mentioned here are out of scope too.
"""
claims = ssa.fleet_count_claims(SOR)
expect("counts scoped to section 7 headline (### history excluded)",
       claims == [15, 19], claims)

# hyphenated and singular forms -- the ORIGINAL drift was the "14-task baseline"
HYPH = "## 7. Fleet\nthe 14-task baseline and a 29-task detail and 1 task extra.\n## 8. y\n"
expect("N-task / singular forms caught (the 14-task-baseline class)",
       ssa.fleet_count_claims(HYPH) == [1, 14, 29], ssa.fleet_count_claims(HYPH))

expect("no false match on task-prefixed words (taskbar)",
       ssa.fleet_count_claims("## 7. x\n3 taskbars\n") == [])

expect("no section 7 -> no claims", ssa.fleet_count_claims("## 3. x\n5 tasks\n") == [])

expect("count-free section 7 -> no claims",
       ssa.fleet_count_claims("## 7. Fleet\nroster is GENERATED daily\n## 8. y\n") == [])

npass = sum(1 for ok, _ in results if ok)
print(f"setup-self-audit tests: {npass}/{len(results)} pass")
sys.exit(0 if npass == len(results) else 1)
