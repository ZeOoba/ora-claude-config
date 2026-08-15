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

# ---- _frontmatter_ok: STRUCTURAL check, deliberately NOT a strict YAML parse (2026-07-24) ----
import tempfile


def _fm(text):
    fp = os.path.join(tempfile.mkdtemp(), "SKILL.md")
    with open(fp, "w", encoding="utf-8") as f:
        f.write(text)
    return ssa._frontmatter_ok(fp)


GOOD = "---\nname: x\ndescription: does a thing\n---\n\n# Body\n"
expect("well-formed frontmatter -> ok", _fm(GOOD) is True, _fm(GOOD))

# REGRESSION this check shipped with: a bare `"## name:" in text` substring test scored a
# file malformed when its BODY merely quoted the pattern. Real case, found 2026-07-24:
# scheduled-tasks (lams)/ora-skill-text-audit documents `## name:` in backticks at line 41.
QUOTED = GOOD + "\nThe frontmatter (or its inline `## name:` line) ends with a version.\n"
expect("body prose quoting '## name:' is NOT malformed", _fm(QUOTED) is True, _fm(QUOTED))

# ...while still catching the class it exists for: frontmatter collapsed onto a heading.
COLLAPSED = "---\n## name: x description: y\n---\n\nbody\n"
expect("collapsed '## name:' INSIDE the fence -> malformed", _fm(COLLAPSED) is False, _fm(COLLAPSED))
expect("no opening fence -> malformed", _fm("## name: x description: y\n") is False)
# A single '#' is a legal YAML comment, not the collapsed-heading regression.
expect("YAML comment '# name:' in the fence is NOT malformed",
       _fm("---\n# name: see below\nname: x\ndescription: y\n---\n\nbody\n") is True)
expect("no closing fence -> malformed",
       _fm("---\nname: x\ndescription: y\n\nbody, fence never closes\n") is False)
expect("description only in body, not in the fence -> malformed",
       _fm("---\nname: x\n---\n\ndescription: not frontmatter\n") is False)

# Descriptions carrying ': ' MUST pass: the harness's own reader is line-wise/lenient, and
# 44 fleet SKILL.md files use the trailing '[MODEL: <id> | checked <date>]' convention.
# Tightening this to strict YAML would flag ~82/110 files the harness reads correctly.
MODEL_TAG = ("---\nname: ora-sofr-direct-prefetch\n"
             "description: Prefetch SOFR. Use when the user mentions: SOFR, rates. "
             "[MODEL: UNVERIFIABLE | checked 2026-07-09]\n---\n\nbody\n")
expect("unquoted ': ' / [MODEL: ...] description -> ok", _fm(MODEL_TAG) is True, _fm(MODEL_TAG))
try:
    import yaml
except ImportError:
    pass
else:
    try:
        yaml.safe_load(MODEL_TAG.split("---", 2)[1])
        strict_rejects = False
    except Exception:
        strict_rejects = True
    expect("strict YAML rejects it -- so the leniency here is load-bearing, not an oversight",
           strict_rejects)


# --- check_prepush_shim (2026-07-29, Phase-5): shim-content logic via a temp CLAUDE root ---
import tempfile
_orig_claude = ssa.CLAUDE
try:
    tmp = tempfile.mkdtemp()
    hooks_dir = os.path.join(tmp, ".git", "hooks")
    os.makedirs(hooks_dir)
    ssa.CLAUDE = tmp
    ssa.results.clear()
    ssa.check_prepush_shim()
    expect("shim: missing -> CRIT", ssa.results[-1]["status"] == "CRIT", str(ssa.results[-1]))
    with open(os.path.join(hooks_dir, "pre-push"), "w") as f:
        f.write("python git-prepush-doctrine-gate.py\npython git-prepush-hook-tests-gate.py\n")
    ssa.results.clear()
    ssa.check_prepush_shim()
    expect("shim: partial chain -> CRIT names the gap",
           ssa.results[-1]["status"] == "CRIT" and "confidential" in ssa.results[-1]["detail"],
           str(ssa.results[-1]))
    with open(os.path.join(hooks_dir, "pre-push"), "a") as f:
        f.write("exec python git-prepush-confidential-scan.py\n")
    ssa.results.clear()
    ssa.check_prepush_shim()
    expect("shim: full chain -> OK", ssa.results[-1]["status"] == "OK", str(ssa.results[-1]))
finally:
    ssa.CLAUDE = _orig_claude
    ssa.results.clear()

# --- check_skill_mirror_drift / find_skill_mirror_drift (2026-08-15) ---
# Automation Audit Rev 10 finding R10-1: a scheduled ora-setup-audit run loaded a
# STALE local ~/.claude/skills/ora-setup-audit/SKILL.md mirror instead of the
# canonical ~/ora-skills copy, because nothing detected the two had diverged.
# check_skills() (above) validates frontmatter STRUCTURE across all mirrors; it
# never compares CONTENT between the repo and the local ~/.claude/skills copy of
# the same skill -- this check closes that specific gap.
_orig_ora_skills = ssa.ORA_SKILLS_DIR
_orig_claude2 = ssa.CLAUDE
try:
    repo_root = tempfile.mkdtemp()
    local_root = tempfile.mkdtemp()
    ssa.ORA_SKILLS_DIR = repo_root
    ssa.CLAUDE = local_root  # check_skill_mirror_drift reads os.path.join(CLAUDE, "skills")
    local_skills_dir = os.path.join(local_root, "skills")
    os.makedirs(local_skills_dir)

    # 1. A skill that exists ONLY in the repo (the common case -- most skills are
    #    never locally mirrored at all) is not drift.
    os.makedirs(os.path.join(repo_root, "only-in-repo"))
    with open(os.path.join(repo_root, "only-in-repo", "SKILL.md"), "w") as f:
        f.write("repo only")
    ssa.results.clear()
    ssa.check_skill_mirror_drift()
    expect("mirror-drift: no shared skills -> OK",
           ssa.results[-1]["status"] == "OK", str(ssa.results[-1]))

    # 2. A skill mirrored in both places with IDENTICAL content -> OK, not flagged.
    os.makedirs(os.path.join(repo_root, "same-skill"))
    os.makedirs(os.path.join(local_skills_dir, "same-skill"))
    with open(os.path.join(repo_root, "same-skill", "SKILL.md"), "w") as f:
        f.write("v1 content")
    with open(os.path.join(local_skills_dir, "same-skill", "SKILL.md"), "w") as f:
        f.write("v1 content")
    ssa.results.clear()
    ssa.check_skill_mirror_drift()
    expect("mirror-drift: identical mirrored copy -> OK",
           ssa.results[-1]["status"] == "OK", str(ssa.results[-1]))

    # 3. A skill mirrored in both places with DIVERGED content -> WARN, names it.
    #    This is the exact R10-1 shape: the local copy is stale relative to repo.
    with open(os.path.join(local_skills_dir, "same-skill", "SKILL.md"), "w") as f:
        f.write("STALE v0 content")
    ssa.results.clear()
    ssa.check_skill_mirror_drift()
    expect("mirror-drift: diverged mirrored copy -> WARN, names the skill",
           ssa.results[-1]["status"] == "WARN" and "same-skill" in ssa.results[-1]["detail"],
           str(ssa.results[-1]))

    # 4. Missing repo dir entirely -> SKIP, never a false OK/WARN.
    ssa.ORA_SKILLS_DIR = os.path.join(repo_root, "does-not-exist")
    ssa.results.clear()
    ssa.check_skill_mirror_drift()
    expect("mirror-drift: missing repo dir -> SKIP",
           ssa.results[-1]["status"] == "SKIP", str(ssa.results[-1]))
finally:
    ssa.ORA_SKILLS_DIR = _orig_ora_skills
    ssa.CLAUDE = _orig_claude2
    ssa.results.clear()

# find_skill_mirror_drift as a pure function, independent of the check_*/add() glue.
_d1, _d2 = tempfile.mkdtemp(), tempfile.mkdtemp()
os.makedirs(os.path.join(_d1, "x"))
os.makedirs(os.path.join(_d2, "x"))
with open(os.path.join(_d1, "x", "SKILL.md"), "w") as f:
    f.write("a")
with open(os.path.join(_d2, "x", "SKILL.md"), "w") as f:
    f.write("b")
expect("find_skill_mirror_drift: pure fn detects content divergence",
       ssa.find_skill_mirror_drift(_d1, _d2) == ["x"],
       ssa.find_skill_mirror_drift(_d1, _d2))
expect("find_skill_mirror_drift: pure fn returns [] with no divergence",
       ssa.find_skill_mirror_drift(_d1, _d1) == [])

npass = sum(1 for ok, _ in results if ok)
print(f"setup-self-audit tests: {npass}/{len(results)} pass")
sys.exit(0 if npass == len(results) else 1)
