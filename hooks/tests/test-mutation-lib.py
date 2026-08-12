"""Tests for hooks/tests/lib/mutation.py -- the shared mutation-testing harness.

Written FIRST (TDD). Same posture as test-gitfixture.py: this module is the
verification layer FOR the verification layer, so every invariant it promises is
asserted here rather than trusted. A mutation harness that silently no-ops is worse
than none at all -- the suite stays green, and the reader concludes the assertions
under test are vacuous when in fact the mutation never happened.

Run: python test-mutation-lib.py
Stdlib only. ASCII-only. Windows (`python`).
"""
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"))
import mutation  # noqa: E402

_failures = []


def check(name, cond, detail=""):
    if cond:
        print("PASS " + name)
    else:
        print("FAIL " + name + ("  " + detail if detail else ""))
        _failures.append(name)


def write(text):
    fd, path = tempfile.mkstemp(prefix="mut-src-", suffix=".py")
    os.close(fd)
    with open(path, "w", encoding="ascii", newline="\n") as fh:
        fh.write(text)
    return path


def read(path):
    with open(path, encoding="ascii") as fh:
        return fh.read()


SAMPLE = (
    "VALUE = 1\n"
    "\n"
    "def order(items):\n"
    "    out = list(items)\n"
    "    out.sort(key=lambda c: c[\"age\"])\n"
    "    return out\n"
)
SORT_LINE = "    out.sort(key=lambda c: c[\"age\"])\n"


# ------------------------------------------------------------ the core guarantee
def test_missing_snippet_raises_rather_than_no_opping():
    # THE reason this module exists. A silent no-op mutation leaves the suite green,
    # which reads as "the assertions under test are vacuous" -- the exact wrong
    # conclusion, and one that gets good assertions deleted instead of kept.
    src = write(SAMPLE)
    try:
        mutation.mutate_file(src, [("out.sort(key=lambda c: c['age'])", "")])
    except mutation.MutationError as exc:
        check("a snippet that does not occur raises MutationError", True)
        check("...and the message says what it looked for", "out.sort" in str(exc),
              "exc=%r" % str(exc))
    else:
        check("a snippet that does not occur raises MutationError", False,
              "no exception raised")


def test_wrong_occurrence_count_raises():
    src = write("x = 1\nx = 1\n")
    try:
        mutation.mutate_file(src, [("x = 1", "x = 2")])
    except mutation.MutationError as exc:
        check("2 occurrences against an implied count of 1 raises", True)
        check("...and the message reports both counts",
              "2" in str(exc) and "1" in str(exc), "exc=%r" % str(exc))
    else:
        check("2 occurrences against an implied count of 1 raises", False,
              "no exception raised")

    path = mutation.mutate_file(src, [("x = 1", "x = 2", 2)])
    check("...while an EXPLICIT count of 2 is accepted",
          read(path) == "x = 2\nx = 2\n", "body=%r" % read(path))


def test_zero_expected_count_is_rejected_as_a_useless_mutation():
    # Asking for 0 replacements is always a mistake: it yields a byte-identical
    # "mutant" that cannot flip anything, and a green run then reads as proof.
    #
    # THE SNIPPET MUST BE ABSENT FROM THE SOURCE (independent review, 2026-08-12).
    # The first version of this test used a snippet that EXISTS, so the generic
    # count-mismatch check (found=1 != 0) fired and the test passed with the
    # `count < 1` guard deleted -- proven by mutating the harness. It therefore
    # certified nothing, and the case the guard exists for -- count 0 on an ABSENT
    # snippet, where no other check fires -- slipped straight through. That is this
    # repo's recurring defect class, inside the module built to catch it.
    #
    # ASSERT ON THIS GUARD'S OWN MESSAGE, not merely on "something raised". Once
    # the cancelled-out identity check exists, an absent-snippet 0-count edit
    # reaches it too (nothing replaced -> identical result), so a bare
    # `except MutationError` passes with the `count < 1` guard deleted -- proven by
    # the self-mutation battery, which is how this second-order vacuity was found.
    # The two guards must stay independently pinned; this one produces the message
    # that actually tells the caller what they did wrong.
    src = write(SAMPLE)
    try:
        mutation.mutate_file(src, [("NOT-IN-THIS-FILE", "x", 0)])
    except mutation.MutationError as exc:
        check("an expected count of 0 is refused (on an ABSENT snippet)",
              "count must be" in str(exc), "exc=%r" % str(exc))
    else:
        check("an expected count of 0 is refused (on an ABSENT snippet)", False,
              "no exception raised")


def test_identical_replacement_is_rejected():
    # new == old is the same hazard by another route -- and, like the 0-count case,
    # it would ALSO be caught by the cancelled-out identity check, so this asserts
    # this guard's own message to keep the two independently pinned.
    src = write(SAMPLE)
    try:
        mutation.mutate_file(src, [("VALUE = 1", "VALUE = 1")])
    except mutation.MutationError as exc:
        check("a replacement identical to the original is refused",
              "identical to the original" in str(exc), "exc=%r" % str(exc))
    else:
        check("a replacement identical to the original is refused", False,
              "no exception raised")


# ------------------------------------------------------------ file mutation
def test_edits_that_cancel_out_are_refused():
    # THE LYING PATH the per-edit guards cannot see (independent review, 2026-08-12).
    # Each edit individually is legal -- present, count 1, new != old -- but they
    # apply IN ORDER against progressively-mutated text, so the second can undo the
    # first and hand back a byte-identical "mutant". Reachable in ordinary use: a
    # swap-style rename battery (A->B here, B->A there) nets to identity whenever
    # the counts line up.
    src = write(SAMPLE)
    try:
        mutation.mutate_file(src, [("VALUE = 1", "VALUE = 2"),
                                   ("VALUE = 2", "VALUE = 1")])
    except mutation.MutationError as exc:
        check("mutually-cancelling edits are refused", True)
        # "cancelled out", not "identical": the latter also appears in the
        # identical-replacement guard's message, so it would not discriminate
        # which guard fired if control flow ever reached both.
        check("...and the message says the edits cancelled out",
              "cancelled out" in str(exc), "exc=%r" % str(exc))
    else:
        check("mutually-cancelling edits are refused", False, "no exception raised")

    # ...while chained edits that genuinely land are still allowed: the ordering
    # semantic itself is deliberate, and edit 2 counting against edit 1's OUTPUT is
    # the documented behaviour, not an accident.
    src2 = write("return ALLOW\n")
    path = mutation.mutate_file(src2, [("ALLOW", "DENY"), ("DENY", "BLOCK")])
    check("chained edits apply in order against mutated text",
          read(path) == "return BLOCK\n", "body=%r" % read(path))


def test_mutant_differs_and_the_source_is_untouched():
    src = write(SAMPLE)
    before = read(src)
    path = mutation.mutate_file(src, [(SORT_LINE, "")])
    check("the SOURCE file is never modified", read(src) == before)
    check("the mutant lives somewhere else",
          os.path.abspath(path) != os.path.abspath(src), "path=%r" % path)
    body = read(path)
    check("the mutation was applied", "out.sort" not in body, "body=%r" % body)
    check("...and the rest of the file survived", "VALUE = 1" in body)


def test_line_endings_survive_the_round_trip():
    # Found by dogfooding against a real CRLF hook (2026-08-12): a universal-newline
    # READ plus a newline="" WRITE silently converts CRLF to LF, so the mutant
    # differs from its source on EVERY line and a whole-file diff -- one of the main
    # things a mutant is for -- becomes unreadable. Both directions asserted, since
    # the naive fix (newline="" on write only) breaks the LF case instead.
    for label, text in (("CRLF", "a = 1\r\nb = 2\r\n"), ("LF", "a = 1\nb = 2\n")):
        fd, src = tempfile.mkstemp(prefix="mut-eol-", suffix=".py")
        os.close(fd)
        with open(src, "w", encoding="ascii", newline="") as fh:
            fh.write(text)
        path = mutation.mutate_file(src, [("a = 1", "a = 9")])
        with open(path, encoding="ascii", newline="") as fh:
            body = fh.read()
        check("%s line endings are preserved verbatim" % label,
              body == text.replace("a = 1", "a = 9"), "body=%r" % body)


def test_multiple_edits_apply_in_one_pass():
    src = write(SAMPLE)
    path = mutation.mutate_file(src, [("VALUE = 1", "VALUE = 99"),
                                      ("return out", "return None")])
    body = read(path)
    check("first edit applied", "VALUE = 99" in body, "body=%r" % body)
    check("second edit applied", "return None" in body, "body=%r" % body)


# ------------------------------------------------------------ module mutation
def test_mutate_module_imports_the_mutated_code():
    src = write(SAMPLE)
    good = mutation.load_module(src)
    check("the unmutated module behaves as written",
          [d["age"] for d in good.order([{"age": 5}, {"age": 1}])] == [1, 5])

    bad = mutation.mutate_module(src, [(SORT_LINE, "")])
    check("the mutated module drops the sort",
          [d["age"] for d in bad.order([{"age": 5}, {"age": 1}])] == [5, 1])


def test_two_mutants_of_one_source_do_not_collide():
    # Both mutants must be independently importable in ONE process, or a battery
    # silently tests one mutant twice while reporting two.
    #
    # WHAT PROVIDES THAT is non-registration in sys.modules, NOT the generated
    # unique name: spec_from_file_location + exec_module never consult sys.modules,
    # so even a fixed name stays independent. The unique name only makes __name__
    # and tracebacks readable. (An earlier comment here claimed the name was
    # load-bearing; independent review disproved it by loading two mutants under one
    # fixed name and getting independent modules. Stated correctly so the next
    # harness copied from this one does not inherit the wrong mechanism.)
    src = write(SAMPLE)
    a = mutation.mutate_module(src, [("VALUE = 1", "VALUE = 11")])
    b = mutation.mutate_module(src, [("VALUE = 1", "VALUE = 22")])
    check("a mutant is not registered in sys.modules",
          a.__name__ not in sys.modules, "name=%r" % a.__name__)
    check("first mutant has its own VALUE", a.VALUE == 11, "a.VALUE=%r" % a.VALUE)
    check("second mutant has its own VALUE", b.VALUE == 22, "b.VALUE=%r" % b.VALUE)
    check("...and they are distinct module objects", a is not b)


# ------------------------------------------------------------ tree mutation
def _sample_tree():
    root = tempfile.mkdtemp(prefix="mut-tree-src-")
    os.makedirs(os.path.join(root, "lib"))
    os.makedirs(os.path.join(root, "__pycache__"))
    with open(os.path.join(root, "lib", "helper.py"), "w", encoding="ascii",
              newline="\n") as fh:
        fh.write("def answer():\n    return 'live'\n")
    with open(os.path.join(root, "hook.py"), "w", encoding="ascii",
              newline="\n") as fh:
        fh.write("import os, sys\n"
                 "sys.path.insert(0, os.path.join(os.path.dirname(\n"
                 "    os.path.abspath(__file__)), 'lib'))\n"
                 "import helper\n"
                 "print('VERDICT: ' + helper.answer())\n")
    with open(os.path.join(root, "__pycache__", "junk.pyc"), "wb") as fh:
        fh.write(b"\x00")
    # NESTED artifact dir too: IGNORED is matched by shutil.ignore_patterns, which
    # matches basenames at EVERY depth. The module's comment promises that; without
    # a nested case no test pinned it, and a stale nested .pyc is exactly what makes
    # a mutant silently run UN-mutated code.
    os.makedirs(os.path.join(root, "lib", "__pycache__"))
    with open(os.path.join(root, "lib", "__pycache__", "helper.pyc"), "wb") as fh:
        fh.write(b"\x00")
    return root


def test_mutate_tree_keeps_siblings_so_subprocess_imports_still_resolve():
    # The subprocess shape: a hook imports from its sibling lib/, so mutating the
    # hook alone in a temp file is not runnable. The tree copy is what makes
    # `python <tree>/hook.py` work at all -- that is the whole point of this call.
    root = _sample_tree()
    tree = mutation.mutate_tree(root, {"hook.py": [("VERDICT: ", "MUTANT: ")]})
    check("the mutated tree is not the source tree",
          os.path.abspath(tree) != os.path.abspath(root))
    # A no-edit copy is EXPLICITLY allowed, and is the documented way to baseline:
    # a mutant tree drops sessions/ and state/, so comparing a mutant against the
    # LIVE tree can differ for reasons unrelated to the edit.
    baseline = mutation.mutate_tree(root, {})
    check("a no-edit tree copy is allowed as a baseline",
          os.path.isfile(os.path.join(baseline, "hook.py")))
    check("the sibling lib/ came along",
          os.path.isfile(os.path.join(tree, "lib", "helper.py")))
    check("__pycache__ is not copied",
          not os.path.isdir(os.path.join(tree, "__pycache__")))
    check("...and NESTED __pycache__ is dropped too (every-depth semantics)",
          not os.path.isdir(os.path.join(tree, "lib", "__pycache__")))

    proc = subprocess.run([sys.executable, os.path.join(tree, "hook.py")],
                          capture_output=True, text=True)
    check("the mutated copy actually RUNS (sibling import resolved)",
          proc.returncode == 0, "rc=%s stderr=%r" % (proc.returncode, proc.stderr))
    check("...and it is the MUTATED code that ran", "MUTANT: live" in proc.stdout,
          "stdout=%r" % proc.stdout)

    orig = subprocess.run([sys.executable, os.path.join(root, "hook.py")],
                          capture_output=True, text=True)
    check("...while the ORIGINAL tree still runs unmutated",
          "VERDICT: live" in orig.stdout, "stdout=%r" % orig.stdout)


def test_mutate_tree_propagates_the_asserted_count_guarantee():
    # The count guarantee must survive the tree shape -- the one most likely to
    # drift, since the caller is not looking at the file it names.
    root = _sample_tree()
    try:
        mutation.mutate_tree(root, {"hook.py": [("nope", "yep")]})
    except mutation.MutationError as exc:
        check("a missing snippet inside a tree still raises", True)
        check("...naming the file it was looking in", "hook.py" in str(exc),
              "exc=%r" % str(exc))
    else:
        check("a missing snippet inside a tree still raises", False,
              "no exception raised")

    # Catch Exception, then assert the TYPE: without the isfile() guard this path
    # still fails, but as a raw FileNotFoundError from the write -- which escapes a
    # `except MutationError` clause and crashes the run instead of reporting a named
    # failure. Callers are told to catch MutationError, so the type is part of the
    # contract, and the self-mutation battery should get a legible FAIL here rather
    # than a traceback (2026-08-12).
    try:
        mutation.mutate_tree(root, {"absent.py": [("x", "y")]})
    except Exception as exc:
        check("naming a file that is not in the tree raises MutationError, "
              "not a raw OSError", isinstance(exc, mutation.MutationError),
              "exc=%r" % exc)
    else:
        check("naming a file that is not in the tree raises MutationError, "
              "not a raw OSError", False, "no exception raised")


if __name__ == "__main__":
    test_missing_snippet_raises_rather_than_no_opping()
    test_wrong_occurrence_count_raises()
    test_zero_expected_count_is_rejected_as_a_useless_mutation()
    test_identical_replacement_is_rejected()
    test_edits_that_cancel_out_are_refused()
    test_mutant_differs_and_the_source_is_untouched()
    test_line_endings_survive_the_round_trip()
    test_multiple_edits_apply_in_one_pass()
    test_mutate_module_imports_the_mutated_code()
    test_two_mutants_of_one_source_do_not_collide()
    test_mutate_tree_keeps_siblings_so_subprocess_imports_still_resolve()
    test_mutate_tree_propagates_the_asserted_count_guarantee()
    if _failures:
        print("\n%d FAILURE(S): %s" % (len(_failures), ", ".join(_failures)))
        sys.exit(1)
    print("\nALL mutation-lib tests passed.")
    sys.exit(0)
