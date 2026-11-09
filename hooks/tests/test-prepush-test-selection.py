#!/usr/bin/env python3
"""Tests for hooks/lib/prepush_test_selection.py -- the LIGHT pre-push tier's test
selector. Pure: an in-memory fake repo (dict of path -> text), no subprocesses, no git,
plus a membership check of ALWAYS_RUN against the REAL discovered suite.

Run: python hooks/tests/test-prepush-test-selection.py (exit 0 = pass)
"""
import glob
import os
import sys

HOOKS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLAUDE_DIR = os.path.dirname(HOOKS)
sys.path.insert(0, os.path.join(HOOKS, "lib"))
import prepush_test_selection as sel  # noqa: E402

results = []


def expect(label, cond, detail=""):
    results.append((bool(cond), label))
    if not cond:
        print("  FAIL: %s %s" % (label, detail))


ALWAYS = list(sel.ALWAYS_RUN)
FAKE = {a: "always\n" for a in ALWAYS}
FAKE.update({
    "hooks/tests/test-foo-guard.py": "load('foo-guard.py')\n",
    "hooks/tests/test-foo-guard-worktree.py": "suffix variant, no textual reference\n",
    "hooks/tests/test-bar.py": "checks scheduled-tasks/ora-am-brief spec\n",
    "hooks/tests/test-dispatch.py": "runs pretooluse-dispatcher.py end to end\n",
    "maintenance/_tests/test_some_probe.py": "import some_probe\n",
    "maintenance/test-unrelated.py": "nothing to see; mentions SKILL.md generically\n",
    "hooks/tests/test-slow-autonomy.py": "unrelated slow thing\n",
})
TESTS = sorted(FAKE)
CODE = {
    "hooks/pretooluse-dispatcher.py": "GUARDS = ['foo-guard.py']\n",
    "hooks/foo-guard.py": "def main(): pass\n",
    "maintenance/some-probe.py": "pass\n",
}
ALL = dict(FAKE, **CODE)


def read(p):
    if p not in ALL:
        raise OSError(p)
    return ALL[p]


def pick(changed, tests=TESTS, closure=tuple(CODE), reader=read):
    return sel.select_tests(changed, tests, reader, closure)


# --- FULL escalations ------------------------------------------------------------
s = pick(None)
expect("unknown diff -> FULL", s.mode == sel.FULL and s.why_full)
expect("FULL selects every test", s.selected == TESTS)

for trig in ("hooks/lib/session_kind.py", "hooks/tests/lib/gitfixture.py",
             "hooks/git-prepush-hook-tests-gate.py", "hooks/lib/prepush_test_selection.py",
             "hooks/git-prepush-confidential-scan.py", "hooks/git-prepush-doctrine-gate.py"):
    s = pick([trig])
    expect("trigger %s -> FULL" % trig, s.mode == sel.FULL, repr(s.why_full))
for trig in (".github/workflows/full-test-suite.yml", "hooks/confidentiality-guard.py",
             "hooks/tests/test-confidentiality-guard.py", "docs/Confidential-notes.md"):
    s = pick([trig])
    expect("trigger %s -> FULL" % trig, s.mode == sel.FULL, repr(s.why_full))
s = pick(["hooks\\lib\\x.py"])
expect("windows-separator trigger path still escalates", s.mode == sel.FULL)

s = pick(["docs/x.md"], tests=[t for t in TESTS if t != ALWAYS[0]])
expect("an ALWAYS_RUN file missing from discovery -> FULL",
       s.mode == sel.FULL and ALWAYS[0] in (s.why_full or ""), repr(s.why_full))

# --- LIGHT selection ---------------------------------------------------------------
s = pick([])
expect("empty diff -> LIGHT with exactly ALWAYS_RUN",
       s.mode == sel.LIGHT and sorted(s.selected) == sorted(ALWAYS), repr(s.selected))

s = pick(["docs/unrelated-note.md"])
expect("unreferenced doc change -> ALWAYS_RUN only", sorted(s.selected) == sorted(ALWAYS))
expect("slow unrelated test is NOT selected for an unrelated change",
       "hooks/tests/test-slow-autonomy.py" not in s.selected)

s = pick(["hooks/foo-guard.py"])
expect("name match selects test-foo-guard.py", "hooks/tests/test-foo-guard.py" in s.selected)
expect("name match selects suffix variant test-foo-guard-worktree.py",
       "hooks/tests/test-foo-guard-worktree.py" in s.selected)
expect("closure: dispatcher references foo-guard.py -> dispatcher test selected",
       "hooks/tests/test-dispatch.py" in s.selected, repr(s.reasons))
expect("unrelated test still excluded", "maintenance/test-unrelated.py" not in s.selected)

# Closure is ONE hop: hub.py references the dispatcher, which references foo-guard.py.
# A fixpoint would pull hub's tests in for a foo-guard change; measured 2026-11-06 that
# turned a one-file push into ~80% of the suite.
CODE2 = dict(CODE, **{"hooks/hub.py": "run('pretooluse-dispatcher.py')\n"})
ALL2 = dict(FAKE, **CODE2)
ALL2["hooks/tests/test-hub.py"] = "exercise hub.py\n"
TESTS2 = sorted(TESTS + ["hooks/tests/test-hub.py"])
s = sel.select_tests(["hooks/foo-guard.py"], TESTS2, lambda p: ALL2[p], tuple(CODE2))
expect("closure is one hop: dispatcher's test selected",
       "hooks/tests/test-dispatch.py" in s.selected)
expect("closure is one hop: two-hop hub test NOT selected",
       "hooks/tests/test-hub.py" not in s.selected, repr(s.reasons.get("hooks/tests/test-hub.py")))

s = pick(["maintenance/some-probe.py"])
expect("underscore/hyphen equivalence in name match",
       "maintenance/_tests/test_some_probe.py" in s.selected, repr(s.selected))

# --- Path-class adds (rule 4b): cross-spec lints glob scheduled-tasks/*/SKILL.md and
# never name a task id, so key matching (rule 7) cannot reach them. Verified 2026-11-08:
# a SKILL.md-only push for ora-am-brief selected 35/180 tests with the send-contract
# lint absent -- the lint that guards the sole external send path.
SPEC_LINTS = list(getattr(sel, "PATH_CLASS_ADDS", {}).get("scheduled-tasks/*/*.md", ()))
expect("scheduled-task spec class maps to a non-empty lint set", SPEC_LINTS, repr(SPEC_LINTS))
FAKE_SPEC = dict(ALL, **{t: "globs every spec; names no task id\n" for t in SPEC_LINTS})
TESTS_SPEC = sorted(TESTS + SPEC_LINTS)


def pick_spec(changed, tests=TESTS_SPEC):
    return sel.select_tests(changed, tests, lambda p: FAKE_SPEC[p], tuple(CODE))


s = pick_spec(["scheduled-tasks/ora-am-brief/SKILL.md"])
expect("SKILL.md-only push stays LIGHT", s.mode == sel.LIGHT, repr(s.why_full))
for t in SPEC_LINTS:
    expect("SKILL.md-only push selects spec lint %s" % t, t in s.selected, repr(s.selected))
    expect("spec lint %s carries a path-class reason" % t,
           any("path class" in r for r in s.reasons.get(t, [])), repr(s.reasons.get(t)))
expect("scheduled-task class set is EXACTLY the three cross-spec lints (no silent drop)",
       set(SPEC_LINTS) == {"maintenance/_tests/test_send_contract_spec_lint.py",
                           "maintenance/_tests/test_scheduled_task_run_guard.py",
                           "maintenance/_tests/test_task_spec_command_paths.py"},
       repr(SPEC_LINTS))
s = pick_spec(["scheduled-tasks\\ora-am-brief\\skill.md"])
expect("class match tolerates windows separators and lowercase basename",
       SPEC_LINTS and all(t in s.selected for t in SPEC_LINTS), repr(s.selected))
s = pick_spec(["SCHEDULED-TASKS/X/SKILL.MD"])
expect("class match is case-insensitive on every segment (SCHEDULED-TASKS/X/SKILL.MD)",
       SPEC_LINTS and all(t in s.selected for t in SPEC_LINTS), repr(s.selected))
s = pick_spec(["scheduled-tasks/ora-am-brief/notes.md"])
expect("other .md in a task folder also selects the spec lints (run-guard falls back to *.md)",
       SPEC_LINTS and all(t in s.selected for t in SPEC_LINTS), repr(s.selected))
s = pick_spec(["docs/unrelated-note.md"])
expect("non-spec push does NOT pull the spec lints",
       not any(t in s.selected for t in SPEC_LINTS), repr(s.selected))
s = pick_spec(["scheduled-tasks/ora-pm-ledger/state_retention.py"])
expect("a non-.md file in a task folder is not a spec (no class add)",
       not any(t in s.selected for t in SPEC_LINTS), repr(s.selected))
s = pick_spec(["scheduled-tasks/_archive_2026-07-16_retired/old-task/SKILL.md"])
expect("segment-exact match: a 3-deep archived spec is not the live-spec class",
       not any(t in s.selected for t in SPEC_LINTS), repr(s.selected))
s = pick_spec(["scheduled-tasks/ora-am-brief/SKILL.md"])
expect("generic SKILL.md keyed by parent dir -> test-bar selected",
       "hooks/tests/test-bar.py" in s.selected)
expect("generic SKILL.md does NOT select every test that mentions SKILL.md",
       s.mode == sel.LIGHT and "maintenance/test-unrelated.py" not in s.selected,
       repr((s.mode, s.why_full)))
if SPEC_LINTS:
    s = pick_spec(["scheduled-tasks/ora-am-brief/SKILL.md"],
                  tests=[t for t in TESTS_SPEC if t != SPEC_LINTS[0]])
    expect("a mapped class test missing from discovery -> FULL (never silently skipped)",
           s.mode == sel.FULL and SPEC_LINTS[0] in (s.why_full or ""), repr(s.why_full))
    s = pick_spec(["docs/unrelated-note.md"], tests=[t for t in TESTS_SPEC if t != SPEC_LINTS[0]])
    expect("a missing class test does not escalate a push outside that class",
           s.mode == sel.LIGHT, repr(s.why_full))

s = pick(["maintenance/test-unrelated.py"])
expect("a changed test file selects itself", "maintenance/test-unrelated.py" in s.selected)

s = pick(["./hooks/foo-guard.py"])
expect("leading ./ is normalised", "hooks/tests/test-foo-guard.py" in s.selected)
expect("'.github' prefix is not mangled by normalisation",
       sel._norm("./.github/workflows/x.yml") == ".github/workflows/x.yml")

s = pick(["hooks/foo-guard.py"], reader=lambda p: (_ for _ in ()).throw(OSError(p))
         if p == "hooks/tests/test-slow-autonomy.py" else read(p))
expect("unreadable test file is selected (fail toward running)",
       "hooks/tests/test-slow-autonomy.py" in s.selected)

s = pick(["hooks/foo-guard.py"])
expect("selection preserves discovery order", s.selected == [t for t in TESTS if t in s.selected])
expect("every selected test carries a reason", all(s.reasons.get(t) for t in s.selected))

expect("keys_for: short stems are not keys (avoid substring noise)",
       sel.keys_for("hooks/x.py") == {"x.py"}, repr(sel.keys_for("hooks/x.py")))
expect("keys_for: long stem is a key", "session_kind" in sel.keys_for("hooks/lib/session_kind.py"))

# --- ALWAYS_RUN against the REAL suite ------------------------------------------------
real = set()
for parts in (("hooks", "tests"), ("maintenance",), ("maintenance", "_tests")):
    for pat in ("test-*.py", "test_*.py"):
        for p in glob.glob(os.path.join(CLAUDE_DIR, *parts, pat)):
            real.add(os.path.relpath(p, CLAUDE_DIR).replace(os.sep, "/"))
for a in ALWAYS:
    expect("ALWAYS_RUN entry exists in the real suite: %s" % a, a in real)
expect("ALWAYS_RUN stays small (<= 4 files; it runs on every light push)", len(ALWAYS) <= 4)
# A renamed/removed class-mapped test must fail HERE (this file is ALWAYS_RUN, so on
# every push), not wait for the next spec push to hit the FULL fallback.
for pattern, adds in getattr(sel, "PATH_CLASS_ADDS", {}).items():
    for a in adds:
        expect("PATH_CLASS_ADDS[%s] entry exists in the real suite: %s" % (pattern, a), a in real)

passed = sum(1 for ok, _ in results if ok)
print("\nprepush-test-selection tests: %d/%d passed" % (passed, len(results)))
sys.exit(0 if passed == len(results) else 1)
