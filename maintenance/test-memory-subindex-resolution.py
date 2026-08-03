#!/usr/bin/env python3
"""Tests for memory-integrity-probe.py's sub-index resolution (2026-08-03).

Covers collect_indexed_links() and _links_in() -- the change that unblocks
splitting MEMORY.md, which was recorded as BLOCKED in
reference_memory_index_size_gate_is_a_runway_marker.md because check 1
reconciled against MEMORY.md alone and reported every sub-index-listed file as
"unlisted".

Everything here runs over a real tempdir, so the live memory tree is untouched.

Run: python test-memory-subindex-resolution.py   (exit 0 = all pass)
"""
import importlib.util
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "mip", os.path.join(HERE, "memory-integrity-probe.py"))
mip = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mip)

results = []


def expect(label, cond, detail=""):
    results.append((bool(cond), label))
    if not cond:
        print("  FAIL: %s %s" % (label, detail))


def write(d, name, text):
    with open(os.path.join(d, name), "w", encoding="utf-8") as f:
        f.write(text)


# --- _links_in ---------------------------------------------------------------------
expect("_links_in: extracts markdown link targets",
       mip._links_in("- [A](a.md) and [B](b.md)") == {"a.md", "b.md"})
expect("_links_in: reduces paths to basenames",
       mip._links_in("[X](sub/dir/x.md)") == {"x.md"})
expect("_links_in: ignores non-md links",
       mip._links_in("[H](http://e.com) [P](p.png)") == set())
expect("_links_in: empty/None safe",
       mip._links_in("") == set() and mip._links_in(None) == set())

# --- collect_indexed_links ---------------------------------------------------------
with tempfile.TemporaryDirectory() as d:
    # Root index links a normal memory + a sub-index; the sub-index lists two more.
    write(d, "INDEX_reference.md", "# Ref\n- [G1](reference_g1.md)\n- [G2](reference_g2.md)\n")
    for n in ("plain.md", "reference_g1.md", "reference_g2.md"):
        write(d, n, "body")
    idx = "- [Plain](plain.md)\n- [Reference](INDEX_reference.md)\n"

    links, followed = mip.collect_indexed_links(idx, d)
    expect("collect: unions root links with sub-index links",
           links == {"plain.md", "INDEX_reference.md", "reference_g1.md", "reference_g2.md"},
           sorted(links))
    expect("collect: reports which sub-indexes were followed",
           followed == ["INDEX_reference.md"], followed)

    # The whole point: a file listed ONLY in the sub-index must not read as unlisted.
    present = {"plain.md", "INDEX_reference.md", "reference_g1.md", "reference_g2.md"}
    expect("collect: no file listed only in the sub-index is 'unlisted'",
           sorted(present - links) == [])

with tempfile.TemporaryDirectory() as d:
    # A sub-index the root index does NOT link must not grant coverage to itself
    # or its contents -- otherwise dropping a file into the directory would let it
    # smuggle in arbitrary coverage without any human reviewing the root index.
    write(d, "INDEX_rogue.md", "- [Sneaky](sneaky.md)\n")
    write(d, "sneaky.md", "body")
    links, followed = mip.collect_indexed_links("- [Plain](plain.md)\n", d)
    expect("collect: an UNLINKED sub-index is not followed", followed == [])
    expect("collect: its listed files stay uncovered (still 'unlisted')",
           "sneaky.md" not in links)
    expect("collect: the rogue sub-index itself stays uncovered",
           "INDEX_rogue.md" not in links)

with tempfile.TemporaryDirectory() as d:
    # A LINKED but MISSING sub-index must still surface as an orphan pointer,
    # not be silently swallowed by the read failure.
    links, followed = mip.collect_indexed_links("- [Gone](INDEX_gone.md)\n", d)
    expect("collect: missing sub-index is not followed", followed == [])
    expect("collect: missing sub-index remains in links (so check 1 flags it as an orphan)",
           "INDEX_gone.md" in links)

with tempfile.TemporaryDirectory() as d:
    # One level only: a sub-index linking another sub-index does not chain.
    write(d, "INDEX_a.md", "- [B](INDEX_b.md)\n")
    write(d, "INDEX_b.md", "- [Deep](deep.md)\n")
    write(d, "deep.md", "body")
    links, followed = mip.collect_indexed_links("- [A](INDEX_a.md)\n", d)
    expect("collect: follows only one level (no chaining)", followed == ["INDEX_a.md"])
    expect("collect: a second-level file is NOT covered", "deep.md" not in links)
    expect("collect: the second-level sub-index itself is linked-but-unfollowed",
           "INDEX_b.md" in links)

with tempfile.TemporaryDirectory() as d:
    expect("collect: empty index is safe", mip.collect_indexed_links("", d) == (set(), []))

with tempfile.TemporaryDirectory() as d:
    # A sub-index legitimately links back home ("Sub-index of MEMORY.md"). check 1
    # discards MEMORY.md from `present`, so without discarding it from `linked` too the
    # root index reads as an orphan pointer to a missing file. Caught by the real split.
    write(d, "INDEX_reference.md", "> Sub-index of [MEMORY.md](MEMORY.md).\n- [G](g.md)\n")
    write(d, "g.md", "body")
    links, _ = mip.collect_indexed_links("- [Ref](INDEX_reference.md)\n", d)
    expect("collect: a sub-index back-link to MEMORY.md is surfaced (check 1 discards it)",
           "MEMORY.md" in links)

with tempfile.TemporaryDirectory() as d:
    # Multiple sub-indexes, deterministic order.
    write(d, "INDEX_one.md", "- [X](x.md)\n")
    write(d, "INDEX_two.md", "- [Y](y.md)\n")
    links, followed = mip.collect_indexed_links(
        "- [1](INDEX_one.md)\n- [2](INDEX_two.md)\n", d)
    expect("collect: follows multiple sub-indexes",
           followed == ["INDEX_one.md", "INDEX_two.md"], followed)
    expect("collect: unions all their links", {"x.md", "y.md"} <= links)

# --- summary -----------------------------------------------------------------------
passed = sum(1 for ok, _ in results if ok)
print("\nmemory sub-index resolution tests: %d/%d passed" % (passed, len(results)))
sys.exit(0 if passed == len(results) else 1)
