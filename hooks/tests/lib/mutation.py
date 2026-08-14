#!/usr/bin/env python3
"""Shared mutation-testing harness for the hook test suites.

WHY. A test that asserts a contract is only worth its runtime if it FAILS when the
contract breaks, and this repo has repeatedly shipped assertions that could not:

  * feedback_fixture_shaped_tests_certify_dead_branches.md -- the general case.
  * test-claim-work-lib.py's "Claimed" prefix check was VACUOUS for months --
    _clean_paths runs normcase(), which lowercases on Windows, so the capital-C
    prefix could never match whether or not the sanitization it guarded existed.
    Proven by deleting the sanitization and watching the suite stay green.
  * test-config-write-guard.py's first ordering-adjacent assertions passed against
    the UNFIXED message, because the block text echoes the offending command back.

The only reliable check is mechanical: break the production line on purpose, re-run,
and confirm the assertion flips. That was hand-rolled three times in one session
(2026-08-11/12) across claim_work's age sort, config-write-guard's block message and
eos-review-gate's record hint -- the same copy-patch-import/spawn dance each time,
with the same hazard each time: a snippet that does not match ANYTHING produces a
byte-identical "mutant", the suite stays green, and the reader concludes the
assertion was vacuous when in truth the mutation never happened. That failure is
silent and points the wrong way, so it is what this module refuses to let happen:
every substitution is COUNT-ASSERTED (the same discipline masterlease-jurisdiction-
rebase adopted for DOCX edits on 2026-08-03).

THREE SHAPES, matching the three real call sites:
  mutate_file(src, edits)   -> path of a mutated copy   (inspect it, diff it)
  mutate_module(src, edits) -> the mutated code IMPORTED (in-process assertions)
  mutate_tree(dir, {rel: edits}) -> a mutated copy of a whole directory, so a hook
                               that imports from its sibling lib/ is still runnable
                               as `python <tree>/the-hook.py` in a subprocess

DELIBERATELY SMALL, for the reason gitfixture.py states: this is verification
infrastructure for security gates, so it must be boring and fully asserted (see
test-mutation-lib.py). It does not run suites, interpret results, or decide what
"caught" means -- callers own their assertions. If you need a new shape, add a named
function; do not add flags to these.

CONTRACT: the source is NEVER modified. Every returned path is a fresh temp file or
directory the caller owns; callers leak into %TEMP% and let the OS reap it, exactly
as the suites using gitfixture already do.
"""
import importlib.util
import os
import shutil
import sys
import tempfile

__all__ = ["MutationError", "mutate_file", "mutate_module", "mutate_tree",
           "load_module", "IGNORED"]

# Never copied into a mutated tree: build artifacts (a stale .pyc for a mutated
# module is an actively wrong input), and the runtime state dirs, which are
# per-session, unbounded, and irrelevant to any mutation.
#
# These are shutil.ignore_patterns globs, so they match BASENAMES AT EVERY DEPTH,
# not just at the tree root -- which is what you want for __pycache__ and harmless
# for the rest under hooks/ today, but it does mean a nested directory named e.g.
# "state" anywhere in the tree is dropped too. A consequence worth knowing: a
# mutant of hooks/ has no sessions/ or state/, so a hook that READS those dirs
# behaves differently from the in-place original for reasons unrelated to your
# edit. Baseline against an unmutated copy -- mutate_tree(dir, {}) is explicitly
# allowed for exactly that -- rather than against the live tree.
IGNORED = ("__pycache__", ".git", "sessions", "state", "active-work")

_COUNTER = [0]


class MutationError(Exception):
    """A mutation could not be applied EXACTLY as specified.

    Always an error, never a warning: an unapplied mutation yields an identical
    mutant, and a green run against an identical mutant is indistinguishable from
    a vacuous assertion -- the precise confusion this module exists to prevent."""


def _normalize(edits):
    out = []
    for edit in edits:
        if len(edit) == 3:
            old, new, count = edit
        elif len(edit) == 2:
            old, new = edit
            count = 1
        else:
            raise MutationError(
                "each edit must be (old, new) or (old, new, count), got %r" % (edit,))
        if count < 1:
            raise MutationError(
                "expected count must be >= 1 (got %d for %r) -- a 0-count edit "
                "produces an identical mutant, which proves nothing" % (count, old))
        if old == new:
            raise MutationError(
                "replacement is identical to the original (%r) -- that produces an "
                "identical mutant, which proves nothing" % old)
        out.append((old, new, count))
    return out


def _apply(text, edits, where):
    """Apply `edits` to `text`, asserting each one's occurrence count AND that the
    net result actually differs from the input.

    Edits apply IN ORDER against progressively-mutated text, so edit N's count is
    asserted against edit N-1's output, not against the original. That is
    deliberate (it lets a battery narrow in stages), but it means per-edit guards
    alone cannot promise a different mutant: two edits can cancel -- ("alpha",
    "beta") then ("beta", "alpha") -- and every individual guard still passes.
    Independent review caught that in the first cut of this module (2026-08-12);
    it is the module's whole failure mode arriving by the one route the per-edit
    checks do not see, so the final text is compared to the original."""
    original = text
    for old, new, count in _normalize(edits):
        found = text.count(old)
        if found != count:
            raise MutationError(
                "%s: expected %d occurrence(s) of %r, found %d. The mutation was "
                "NOT applied -- fix the snippet rather than reading the unchanged "
                "result as a passing mutation run." % (where, count, old, found))
        text = text.replace(old, new)
    if text == original:
        raise MutationError(
            "%s: the edits cancelled out -- the result is byte-identical to the "
            "source. An identical mutant cannot flip any assertion, so a green run "
            "against it proves nothing." % where)
    return text


def _read(path):
    # newline="" on BOTH sides, or the round-trip silently rewrites line endings:
    # universal-newline READ translates CRLF to LF, and the newline="" WRITE then
    # emits LF, so a CRLF source yields a mutant differing on every line. Caught by
    # dogfooding this module against config-write-guard.py (2026-08-12) -- a
    # whole-file diff is one of the things callers use a mutant FOR.
    with open(path, "r", encoding="utf-8", newline="") as fh:
        return fh.read()


def _write(path, text):
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)


def mutate_file(source, edits, suffix=None):
    """A mutated COPY of `source`; the original is untouched.

    `edits` is a list of (old, new) -- meaning exactly one occurrence -- or
    (old, new, expected_count). A count mismatch raises MutationError.

    Reads and writes with newline="" so a file's existing line endings survive
    verbatim: a mutant that differs from its source in whitespace as well as in the
    line under test muddies exactly the comparison the caller is making."""
    text = _apply(_read(source), edits, os.path.basename(source))
    _COUNTER[0] += 1
    fd, path = tempfile.mkstemp(
        prefix="mutant-%d-" % _COUNTER[0],
        suffix=suffix if suffix is not None else os.path.splitext(source)[1])
    os.close(fd)
    _write(path, text)
    return path


def load_module(path, name=None):
    """Import the module at `path` without registering it in sys.modules.

    NON-REGISTRATION is what provides isolation, and it is the only thing that
    does: spec_from_file_location + exec_module never consult sys.modules, so two
    mutants of one source are independently importable in a single process even
    under the same name. (An earlier version of this docstring claimed a shared
    name would make the second import return the first -- false, and a wrong
    causal claim in a module other harnesses will be copied from. Corrected by
    independent review, 2026-08-12.) The generated unique name is for readable
    __name__ and tracebacks in failure output, nothing more."""
    _COUNTER[0] += 1
    name = name or "mutation_under_test_%d" % _COUNTER[0]
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise MutationError("cannot import a module from %r" % path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def mutate_module(source, edits, name=None):
    """mutate_file() + load_module(): the mutated code, imported and ready to call."""
    return load_module(mutate_file(source, edits), name=name)


def mutate_tree(source_dir, edits_by_relpath, ignore=IGNORED):
    """A mutated COPY of a whole directory; the original is untouched.

    For the subprocess shape: a hook resolves its imports against its own sibling
    lib/, so a lone mutated file in %TEMP% cannot run. Copying the tree keeps
    `python <tree>/the-hook.py` working, which is the only way to mutation-test a
    gate that is exercised as a subprocess.

    `edits_by_relpath` maps a path relative to `source_dir` to that file's edit
    list. Naming a file that is not in the tree raises rather than silently
    mutating nothing."""
    _COUNTER[0] += 1
    dest = tempfile.mkdtemp(prefix="mutant-tree-%d-" % _COUNTER[0])
    dest = os.path.join(dest, os.path.basename(os.path.normpath(source_dir)))
    shutil.copytree(source_dir, dest, ignore=shutil.ignore_patterns(*ignore))
    for rel, edits in (edits_by_relpath or {}).items():
        target = os.path.join(dest, rel)
        if not os.path.isfile(target):
            raise MutationError(
                "%s is not a file in the copied tree (%s) -- check the path is "
                "relative to the tree root and is not one of the ignored dirs %r"
                % (rel, source_dir, tuple(ignore)))
        _write(target, _apply(_read(target), edits, rel))
    return dest


if __name__ == "__main__":  # pragma: no cover - convenience only
    sys.stderr.write(__doc__ + "\nRun hooks/tests/test-mutation-lib.py to verify.\n")
