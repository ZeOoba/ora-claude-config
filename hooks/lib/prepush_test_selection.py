"""Pure test-selection logic for the LIGHT pre-push tier of
hooks/git-prepush-hook-tests-gate.py.

WHY (2026-11-06, Gabriel-approved follow-up): the pre-push hook-tests gate ran the FULL
tracked suite (~166 files) on every push. Under normal multi-session load several files
blow their 240s/480s budgets or internal timing budgets, so a one-file push that touches
none of them was blocked and needed an allow-hook-test-failure override (twice on
2026-11-06 alone). An override normalised is a gate disabled, so the fix is a tier
split, not another override:

  * LIGHT tier (pre-push, feature-branch pushes): the files chosen HERE from what the
    pushed diff touches, plus ALWAYS_RUN.
  * FULL tier: every discovered file. Runs (a) in GitHub Actions
    (.github/workflows/full-test-suite.yml) on every non-draft PR -- the PR run is the
    authoritative gate a merge must be green on -- plus on each PR merge commit on main
    and weekly, and (b) locally whenever this module
    cannot PROVE a light selection is sound (see `select_tests`), whenever the push
    updates main, and whenever the gate is run outside a real pre-push (the weekly
    ora-prepush-gate-sweep, a human running it by hand).

This module does no I/O of its own: callers pass the changed paths, the discovered test
files and a text reader, so every rule is unit-testable
(hooks/tests/test-prepush-test-selection.py).

SELECTION RULES, in order (over-selection is always the safe direction; every rule only
ever ADDS files or escalates to FULL, never removes):
  1. Changed paths unknown (None)            -> FULL ("cannot determine the diff").
  2. Any changed path is a FULL trigger       -> FULL. Triggers: the gate and this
     module themselves, the other pre-push gates, the shared-library trees
     (hooks/lib/, hooks/tests/lib/) whose fan-in is too wide to map by name, the CI
     workflows (.github/workflows/), and any path containing "confidential" (those
     tests ENV-SKIP in CI, so CI is no backstop for them).
  3. An ALWAYS_RUN file is not among the discovered tests -> FULL (the cheap guard set
     silently shrinking must not shrink the gate with it).
  4. ALWAYS_RUN files are selected.
  4b. Path classes (PATH_CLASS_ADDS): a changed path matching a class pattern selects
     that class's tests. This is for tests that scan a whole tree by glob and never
     name the individual file, which rules 6-8 cannot see. If a mapped test is not
     among the discovered tests -> FULL (same reasoning as rule 3; checked only when
     the class is hit, and the selector's own ALWAYS_RUN test asserts every mapped
     file exists, so a rename fails on the very next push of any kind).
  5. A changed path that IS a discovered test file is selected.
  6. Naming convention: a changed file `<dir>/<name>.<ext>` selects every test whose
     normalised stem is `test-<name>` or starts with `test-<name>-` (`_` and `-` are
     treated as the same character, matching the repo's two test naming styles).
  7. Content reference: every test whose text contains one of the changed file's KEYS
     is selected. A key is the file's basename, plus its extension-less stem when that
     stem is at least MIN_STEM_KEY_LEN chars (catches `import session_kind` and
     `"governor-drift-probe"` path joins). A GENERIC basename (SKILL.md, README.md,
     __init__.py, ...) is replaced by its parent directory name, so a one-file
     task-spec push selects the tests that name THAT task, not every test that
     mentions SKILL.md.
  8. ONE-hop importer closure (not a fixpoint -- see select_tests): a non-test code
     file under hooks/ or maintenance/ whose text contains a changed file's key is
     treated as changed too (rules 6-7 re-applied to it), so editing a guard that
     pretooluse-dispatcher.py loads also selects the dispatcher's tests.
  A test file that cannot be READ is selected (cannot prove it is unrelated).

KNOWN, ACCEPTED LIMITS of the light tier (why CI's full run stays authoritative): a
dependency that is not named in text anywhere (dynamic discovery, globbing a whole
directory, reading a live state file by a computed path) is invisible to rules 6-8
unless a PATH_CLASS_ADDS entry maps it, and
tests run against the pushing checkout's WORKING TREE, not the pushed commit (unchanged
from the full tier). Both are covered by the full suite in CI before merge, EXCEPT tests
that ENV-SKIP in CI (they need gitignored live files); those are covered only by FULL
runs in the main checkout, which is why rule 2 escalates on "confidential" paths.
"""
import fnmatch
import os
import re
from collections import namedtuple

FULL = "full"
LIGHT = "light"

# Repo-relative posix paths. Kept SMALL and CHEAP: these run on every light push, so a
# slow file here re-creates the exact false block the light tier exists to remove.
# Measured 2026-11-06 under real multi-session load (full suite: 44 min wall, 15 files
# timed out): selector test 7s, governor-drift-probe test 80s (hermetic since #410).
# Deliberately NOT here, with the measurement that excluded them:
#   * test-confidentiality-guard.py -- timed out at 480s twice under that load. The
#     confidential-terms HARD guard is gate #3 (git-prepush-confidential-scan.py), which
#     scans the pushed history fail-closed on EVERY push regardless of tier; this test
#     only guards the PreToolUse hook's code and is selected whenever that code (or
#     anything it names) changes.
#   * test-git-prepush-scan.py (221s) and this gate's own test (72-143s) -- the files
#     they cover are FULL triggers, so a change to them already runs everything.
ALWAYS_RUN = (
    "hooks/tests/test-prepush-test-selection.py",
    "maintenance/test-governor-drift-probe.py",
)

FULL_TRIGGER_FILES = frozenset((
    "hooks/git-prepush-hook-tests-gate.py",
    "hooks/git-prepush-doctrine-gate.py",
    "hooks/git-prepush-confidential-scan.py",
    "hooks/lib/prepush_test_selection.py",
))
FULL_TRIGGER_PREFIXES = (
    "hooks/lib/",
    "hooks/tests/lib/",
    # The authoritative CI gate itself: `pull_request` runs the PR head's copy of the
    # workflow, so a PR could otherwise weaken its own gate under a LIGHT push
    # (independent review, 2026-11-06).
    ".github/workflows/",
)
# Any pushed path containing this (case-insensitive) forces FULL. WHY: the confidential
# guard's tests ENV-SKIP in CI and in every worktree (hooks/confidential-terms.json is
# gitignored), so CI is NOT a backstop for them; the only place they truly run is a FULL
# run in the main checkout. Confidential-deal handling is hard invariant 3, so anything
# that names it gets the whole suite locally rather than a mapped subset.
FULL_TRIGGER_SUBSTRINGS = ("confidential",)

# Basenames that say nothing about WHICH thing changed; the parent directory name is
# the meaningful key instead (scheduled-tasks/<id>/SKILL.md -> "<id>").
GENERIC_BASENAMES = frozenset((
    "skill.md", "readme.md", "__init__.py", "index.md", "index.html", "index.js",
    "config.json", "manifest.json", "state.json", "notes.md",
))
# Rule 4b. Pattern -> tests, matched SEGMENT BY SEGMENT (fnmatch per "/" segment, same
# segment count, case-insensitive), so "*" never crosses a directory. Add a class here
# whenever a test globs a tree instead of naming its files.
#
# scheduled-tasks/<id>/*.md -- the cross-spec lints. Each iterates the live
# scheduled-tasks/*/ spec tree, so a SKILL.md push (keyed only by <id>, rule 7) reached
# them only when the test happened to name that id: verified 2026-11-08 on origin/main,
# a push of scheduled-tasks/ora-am-brief/SKILL.md went LIGHT (33/173 tests) without the
# send-contract lint; for ora-pm-ledger (10/173) two of the three were absent.
# Measured runtimes 2026-11-08: 4s / 18s / 3s.
#   * test_send_contract_spec_lint.py -- no spec retries send-via-outlook.ps1 exit 5/6
#     (R-05; a retry routes around Hard Invariant 1 or double-sends).
#   * test_scheduled_task_run_guard.py -- fleet conformance of the double-fire run guard
#     (block-sentinel) wiring in every live spec. It falls back to the first *.md when a
#     task folder has no SKILL.md, hence "*.md" rather than "SKILL.md".
#   * test_task_spec_command_paths.py -- spec command lines use forward-slash paths
#     (an unquoted backslash is an escape in the Bash tool).
# Deliberately NOT here:
#   * test-doctrine-integrity-probe.py -- excluded for COST (58s), not because it is
#     unrelated: test_guard_liveness_real_no_orphans concatenates every live SKILL.md,
#     and commit-provenance-guard's only invocation point is
#     scheduled-tasks/ora-weekly-hygiene/SKILL.md, so dropping that line orphans a guard.
#     Rule 7 currently selects it for that spec only because the test happens to mention
#     "ora-weekly-hygiene" for an unrelated check (incidental, not a mapping). The CI
#     full run is the backstop for that spec and for every other spec's guard wiring.
#   * test_send_contract_suite.py -- it runs scheduled-tasks/_shared/test-*.ps1, not the
#     specs, and names those files itself.
PATH_CLASS_ADDS = {
    "scheduled-tasks/*/*.md": (
        "maintenance/_tests/test_send_contract_spec_lint.py",
        "maintenance/_tests/test_scheduled_task_run_guard.py",
        "maintenance/_tests/test_task_spec_command_paths.py",
    ),
}
MIN_STEM_KEY_LEN = 6
# Where importer closure (rule 8) looks: non-test code under these trees.
CLOSURE_ROOTS = ("hooks/", "maintenance/")
CLOSURE_EXTS = (".py", ".ps1", ".sh", ".psm1")

Selection = namedtuple("Selection", "mode selected reasons why_full")


def _norm(path):
    """Repo-relative posix form. Strips only a literal leading "./" (never lstrip,
    which would also eat the dot of ".github/...")."""
    path = path.replace("\\", "/")
    while path.startswith("./"):
        path = path[2:]
    return path


def _norm_stem(name):
    return os.path.splitext(name)[0].lower().replace("_", "-")


def keys_for(path):
    """The text keys that identify a changed file in other files' content (rule 7)."""
    path = _norm(path)
    base = path.rsplit("/", 1)[-1]
    if base.lower() in GENERIC_BASENAMES:
        parent = path.rsplit("/", 2)[-2] if path.count("/") >= 1 else ""
        return {parent} if parent else set()
    keys = {base}
    stem = os.path.splitext(base)[0]
    if len(stem) >= MIN_STEM_KEY_LEN:
        keys.add(stem)
    return keys


def _name_matches(test_rel, changed_rel):
    """Rule 6: test-<name>.py / test-<name>-<suffix>.py, `_` == `-`."""
    base = changed_rel.rsplit("/", 1)[-1]
    if base.lower() in GENERIC_BASENAMES:
        return False
    want = "test-" + _norm_stem(base)
    got = _norm_stem(test_rel.rsplit("/", 1)[-1])
    return got == want or got.startswith(want + "-")


def matches_class(path, pattern):
    """Rule 4b: segment-exact, case-insensitive glob match ("*" stays inside one segment)."""
    got = _norm(path).lower().split("/")
    want = pattern.lower().split("/")
    return len(got) == len(want) and all(fnmatch.fnmatchcase(g, w) for g, w in zip(got, want))


def class_adds(changed):
    """{test: [why, ...]} for every PATH_CLASS_ADDS class hit by a changed path."""
    out = {}
    for pattern, adds in PATH_CLASS_ADDS.items():
        hits = [p for p in changed if matches_class(p, pattern)]
        if hits:
            for a in adds:
                out.setdefault(a, []).append("path class %s: %s" % (pattern, hits[0]))
    return out


def is_full_trigger(path):
    path = _norm(path)
    return (path in FULL_TRIGGER_FILES
            or any(path.startswith(p) for p in FULL_TRIGGER_PREFIXES)
            or any(s in path.lower() for s in FULL_TRIGGER_SUBSTRINGS))


def _contains_any(text, keys):
    return [k for k in keys if k and k in text]


def select_tests(changed_paths, test_files, read_text, closure_files=()):
    """Decide the tier and, for LIGHT, which test files run.

    changed_paths : iterable of repo-relative paths, or None when the diff is unknown.
    test_files    : repo-relative posix paths of every DISCOVERED test file, in the
                    order they should run.
    read_text     : callable(rel_path) -> str; may raise (unreadable == select it).
    closure_files : repo-relative paths of non-test code files eligible for rule 8.

    Returns Selection(mode, selected, reasons, why_full). For FULL, `selected` is every
    test file and `reasons` is empty; for LIGHT, `reasons[test]` lists why it was chosen.
    """
    test_files = [_norm(t) for t in test_files]

    def full(why):
        return Selection(FULL, list(test_files), {}, why)

    if changed_paths is None:
        return full("could not determine which files the push changes")
    changed = sorted({_norm(p) for p in changed_paths if p})
    triggers = [p for p in changed if is_full_trigger(p)]
    if triggers:
        return full("push touches gate/shared-library path(s): " + ", ".join(triggers))
    missing = [a for a in ALWAYS_RUN if a not in test_files]
    if missing:
        return full("always-run test(s) not discovered: " + ", ".join(missing))
    by_class = class_adds(changed)
    missing = sorted(a for a in by_class if a not in test_files)
    if missing:
        return full("path-class test(s) not discovered: " + ", ".join(missing))

    reasons = {}

    def add(test, why):
        reasons.setdefault(test, [])
        if why not in reasons[test]:
            reasons[test].append(why)

    for a in ALWAYS_RUN:
        add(a, "always-run")
    for a, whys in by_class.items():
        for why in whys:
            add(a, why)

    texts = {}
    unreadable = set()
    for t in test_files:
        try:
            texts[t] = read_text(t)
        except Exception:
            unreadable.add(t)
    for t in unreadable:
        add(t, "unreadable test file (cannot prove unrelated)")

    # Rule 8 closure: grow the changed set with importers until it stops growing.
    test_set = set(test_files)
    closure_pool = [_norm(c) for c in closure_files if _norm(c) not in test_set]
    closure_texts = {}
    for c in closure_pool:
        try:
            closure_texts[c] = read_text(c)
        except Exception:
            closure_texts[c] = None
    # ONE hop, deliberately not a fixpoint: measured 2026-11-06 against the last 25
    # commits on main, a transitive closure chains through hub modules
    # (pretooluse-dispatcher.py, doctrine-integrity-probe.py) and selected ~134 of 169
    # files for a one-line fleet-heartbeat.json change -- i.e. the full suite with
    # extra steps. Deeper transitive dependencies are what CI's full run is for.
    effective = {p: "changed" for p in changed}
    for p in changed:
        ks = keys_for(p)
        for c, text in closure_texts.items():
            if c in effective:
                continue
            if text is None or _contains_any(text, ks):
                effective[c] = "references %s" % p

    for p, origin in effective.items():
        tag = p if origin == "changed" else "%s (%s)" % (p, origin)
        if p in test_set:
            add(p, "changed test file")
        ks = keys_for(p)
        for t in test_files:
            if _name_matches(t, p):
                add(t, "name match: " + tag)
            text = texts.get(t)
            if text is not None:
                hit = _contains_any(text, ks)
                if hit:
                    add(t, "mentions %s: %s" % (sorted(hit)[0], tag))

    selected = [t for t in test_files if t in reasons]
    return Selection(LIGHT, selected, reasons, None)
