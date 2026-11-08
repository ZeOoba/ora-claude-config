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
directory, reading a live state file by a computed path) is invisible to rules 6-8, and
tests run against the pushing checkout's WORKING TREE, not the pushed commit (unchanged
from the full tier). Both are covered by the full suite in CI before merge, EXCEPT tests
that ENV-SKIP in CI (they need gitignored live files); those are covered only by FULL
runs in the main checkout, which is why rule 2 escalates on "confidential" paths.
"""
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

    reasons = {}

    def add(test, why):
        reasons.setdefault(test, [])
        if why not in reasons[test]:
            reasons[test].append(why)

    for a in ALWAYS_RUN:
        add(a, "always-run")

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
