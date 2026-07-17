#!/usr/bin/env python3
"""Tests for memory-integrity-probe.py's index/git reconciliation (check 1, git side).

Runs the real probe against throwaway git-repo fixtures via ORA_MEMORY_DIR, so the live
memory set is never touched. Stdlib only; Windows (`python`).

ORIGIN (2026-07-17): commit 32f3065 committed the MEMORY.md pointer to
reference_autonomy_gate_override_mechanism.md but NOT the file itself -- `git commit -am`
stages tracked files only and silently skips new ones. HEAD was left self-inconsistent: the
index linked a memory that git did not have, so every clone got a broken pointer.

Check 1 ("every MEMORY.md link resolves to a file") did not catch it, and could not: it
globs the FILESYSTEM (`glob(MEM/*.md)`), where the file was sitting happily untracked. A
check that asks the working tree a question only git can answer. The probe passed while HEAD
was broken -- verified by cloning the fixture and finding the file absent.

THE RULE THIS LOCKS: what matters is HEAD's SELF-CONSISTENCY -- exactly what a clone sees.
Every link in HEAD's MEMORY.md must resolve to a file in HEAD's tree. Deliberately NOT
"every memory file must be committed": a session that writes a memory and has not committed
it yet is normal, and failing on that would make the probe cry wolf on every new note.
Working-tree-only state is fine; a COMMITTED pointer to an UNCOMMITTED file is not.
"""
import os
import subprocess
import sys
import tempfile

PROBE = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "maintenance",
    "memory-integrity-probe.py"))

failures = []


def check(label, cond, detail=""):
    print(("PASS  " if cond else "FAIL  ") + label)
    if not cond:
        failures.append(label + (" :: " + detail if detail else ""))


def git(repo, *args):
    return subprocess.run(["git"] + list(args), cwd=repo, capture_output=True, text=True)


def run_probe(memdir):
    env = dict(os.environ, ORA_MEMORY_DIR=memdir)
    r = subprocess.run([sys.executable, PROBE], capture_output=True, text=True, env=env)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def make_repo(d):
    """A git repo with memory/ inside it (mirrors the real layout: memory is a subdir)."""
    mem = os.path.join(d, "memory")
    os.makedirs(mem)
    git(d, "init", "-q", ".")
    git(d, "config", "user.email", "t@t")
    git(d, "config", "user.name", "t")
    return mem


def write_index(mem, entries):
    with open(os.path.join(mem, "MEMORY.md"), "w", encoding="utf-8") as fh:
        fh.write("# ORA Memory Index\n\n" + "".join(
            "- [%s](%s) - hook\n" % (n, n) for n in entries))


# --- 1. Consistent HEAD (index + file both committed) -> clean --------------------
with tempfile.TemporaryDirectory() as d:
    mem = make_repo(d)
    write_index(mem, ["reference_good.md"])
    open(os.path.join(mem, "reference_good.md"), "w").write("# good\n")
    git(d, "add", "-A")
    git(d, "commit", "-qm", "seed")
    rc, out = run_probe(mem)
    check("consistent HEAD (index + file both committed) -> clean", rc == 0,
          "rc=%s\n%s" % (rc, out))

# --- 2. THE BUG: pointer committed, file untracked -> MUST FAIL -------------------
with tempfile.TemporaryDirectory() as d:
    mem = make_repo(d)
    write_index(mem, ["reference_good.md"])
    open(os.path.join(mem, "reference_good.md"), "w").write("# good\n")
    git(d, "add", "-A")
    git(d, "commit", "-qm", "seed")

    # Reproduce 32f3065 exactly: add a memory + its index line, then commit ONLY the index
    # (what `git commit -am` does -- tracked files only, new file silently skipped).
    write_index(mem, ["reference_good.md", "reference_dangling.md"])
    open(os.path.join(mem, "reference_dangling.md"), "w").write("# dangling\n")
    git(d, "add", "memory/MEMORY.md")
    git(d, "commit", "-qm", "index the new memory (file left untracked)")

    rc, out = run_probe(mem)
    check("committed pointer -> untracked file: FAILS (rc=1)", rc == 1,
          "the probe passed while HEAD was self-inconsistent; a clone gets a broken "
          "pointer. rc=%s\n%s" % (rc, out))
    check("...and names the offending file", "reference_dangling.md" in out, out[:300])

    # The fixture proves the consequence rather than asserting it: clone and look.
    clone = os.path.join(d, "cloned")
    subprocess.run(["git", "clone", "-q", d, clone], capture_output=True)
    cloned_files = os.listdir(os.path.join(clone, "memory"))
    check("...and the clone genuinely lacks the linked file (the real-world harm)",
          "reference_dangling.md" not in cloned_files, str(cloned_files))

# --- 3. NO FALSE POSITIVE: brand-new memory, nothing committed yet -> clean -------
with tempfile.TemporaryDirectory() as d:
    mem = make_repo(d)
    write_index(mem, ["reference_good.md"])
    open(os.path.join(mem, "reference_good.md"), "w").write("# good\n")
    git(d, "add", "-A")
    git(d, "commit", "-qm", "seed")

    # A session just wrote a memory + indexed it, and has not committed either. Normal.
    write_index(mem, ["reference_good.md", "reference_fresh.md"])
    open(os.path.join(mem, "reference_fresh.md"), "w").write("# fresh\n")

    rc, out = run_probe(mem)
    check("uncommitted memory + uncommitted index entry -> clean (no cry-wolf)", rc == 0,
          "failing here would flag every new note before it is committed. rc=%s\n%s"
          % (rc, out))

# --- 4. Non-git dir -> check SKIPS, does not crash --------------------------------
#     The pre-existing suite (test-memory-retired-doc-links.py) runs the probe over a
#     plain temp dir with no repo. A git check that errored there would break it.
with tempfile.TemporaryDirectory() as d:
    mem = os.path.join(d, "memory")
    os.makedirs(mem)
    write_index(mem, ["reference_good.md"])
    open(os.path.join(mem, "reference_good.md"), "w").write("# good\n")
    rc, out = run_probe(mem)
    check("non-git memory dir -> skips cleanly (rc=0, no crash)", rc == 0,
          "rc=%s\n%s" % (rc, out))
    check("...and does not report a bogus git orphan", "reference_good.md" not in out
          or "orphan" not in out.lower(), out[:200])

# --- 5. File committed, index entry only in the working tree -> clean -------------
with tempfile.TemporaryDirectory() as d:
    mem = make_repo(d)
    write_index(mem, ["reference_good.md"])
    open(os.path.join(mem, "reference_good.md"), "w").write("# good\n")
    open(os.path.join(mem, "reference_later.md"), "w").write("# later\n")
    git(d, "add", "-A")
    git(d, "commit", "-qm", "seed: both files committed, index lists only one")
    # Now index the second file but do not commit the index. HEAD stays consistent.
    write_index(mem, ["reference_good.md", "reference_later.md"])
    rc, out = run_probe(mem)
    check("file committed, index entry uncommitted -> clean", rc == 0, "rc=%s\n%s" % (rc, out))

# --- 6. Basename collision: a same-named file in a SUBDIR must not satisfy a root link --
#     HEAD holds _archive/reference_x.md but not root reference_x.md; the index links the
#     root name. A recursive tree flattened by basename would call it satisfied while a
#     clone's root link is broken (adversarial review, 2026-07-17).
with tempfile.TemporaryDirectory() as d:
    mem = make_repo(d)
    os.makedirs(os.path.join(mem, "_archive"))
    write_index(mem, ["reference_x.md"])
    open(os.path.join(mem, "_archive", "reference_x.md"), "w").write("# archived only\n")
    git(d, "add", "-A")
    git(d, "commit", "-qm", "index links root name; only the _archive namesake is committed")
    rc, out = run_probe(mem)
    check("subdir namesake does NOT satisfy a root index link (git check catches it)",
          "IN GIT" in out and "reference_x.md" in out,
          "the _archive/ copy masked a clone-broken root link. rc=%s\n%s" % (rc, out))

print()
if failures:
    print("%d FAILED:" % len(failures))
    for f in failures:
        print("  - " + f)
    sys.exit(1)
print("ALL PASS - HEAD's MEMORY.md index reconciles against HEAD's tree")
sys.exit(0)
