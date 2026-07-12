#!/usr/bin/env python3
"""Tests for git-prepush-confidential-scan.py (pure functions only, synthetic terms).

The scanner is the 2026-06-11 incident lesson made executable: a pre-push gate must
scan the FULL HISTORY being pushed (git log -p over each pushed range), not the tree.
Run: python test-git-prepush-scan.py   (exit 0 = all pass)
"""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile

HOOKS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location(
    "pps", os.path.join(HOOKS, "git-prepush-confidential-scan.py"))
pps = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pps)

results = []


def expect(label, cond, detail=""):
    results.append((bool(cond), label))
    if not cond:
        print("  FAIL: %s %s" % (label, detail))


ZERO = "0" * 40
SHA_A = "a" * 40
SHA_B = "b" * 40
TERMS = ["zephyr corp", "9999 example ave"]  # synthetic — never real deal terms here

# --- parse_pushrefs ---------------------------------------------------------------
refs = pps.parse_pushrefs(
    "refs/heads/main %s refs/heads/main %s\nnot a ref line\n" % (SHA_A, SHA_B))
expect("parse: one valid line", len(refs) == 1 and refs[0][1] == SHA_A and refs[0][3] == SHA_B)
expect("parse: empty input", pps.parse_pushrefs("") == [])

# --- rev_range --------------------------------------------------------------------
expect("range: new remote ref -> full local history", pps.rev_range(SHA_A, ZERO) == SHA_A)
expect("range: existing remote -> delta range", pps.rev_range(SHA_A, SHA_B) == "%s..%s" % (SHA_B, SHA_A))

# --- scan_text --------------------------------------------------------------------
expect("scan: clean text", pps.scan_text("quarterly portfolio summary", TERMS) == [])
expect("scan: hit, case-insensitive", pps.scan_text("re: ZePHyR CoRp teaser", TERMS) == [0])
expect("scan: multiple hits, indices not strings",
       pps.scan_text("zephyr corp at 9999 example ave", TERMS) == [0, 1])
expect("scan: term never echoed", all(
    t not in repr(pps.scan_text("zephyr corp", TERMS)) for t in TERMS))

# --- load_terms shape -------------------------------------------------------------
expect("load_terms: returns list or None (fail-closed contract)",
       pps.load_terms() is None or isinstance(pps.load_terms(), list))

# --- load_terms(): linked-worktree fallback to the main checkout's terms file -----
# 2026-07-12 incident: hooks/confidential-terms.json is gitignored, so `git worktree
# add` never materializes it in a fresh linked worktree -- load_terms() must fall
# back to the MAIN worktree's copy (resolved via `git rev-parse --git-common-dir`,
# which always points at the shared .git dir regardless of which worktree asks).
with tempfile.TemporaryDirectory() as td:
    main_repo = os.path.join(td, "main-repo")
    os.makedirs(os.path.join(main_repo, "hooks"))
    subprocess.run(["git", "init", "-q", main_repo], check=True)
    subprocess.run(["git", "-C", main_repo, "config", "user.email", "t@example.com"], check=True)
    subprocess.run(["git", "-C", main_repo, "config", "user.name", "t"], check=True)
    with open(os.path.join(main_repo, "README.md"), "w") as f:
        f.write("seed\n")
    # A tracked file under hooks/ so the directory itself is materialized into a
    # linked worktree's checkout -- mirrors the real repo, where hooks/ holds many
    # tracked files and only confidential-terms.json is gitignored out of it.
    with open(os.path.join(main_repo, "hooks", "placeholder.py"), "w") as f:
        f.write("# tracked placeholder\n")
    subprocess.run(["git", "-C", main_repo, "add", "README.md", "hooks/placeholder.py"], check=True)
    subprocess.run(["git", "-C", main_repo, "commit", "-q", "-m", "seed"], check=True)

    # Never committed -- mirrors the real file being gitignored (present in the
    # main checkout's working tree, absent from anything `git worktree add` creates).
    terms_path = os.path.join(main_repo, "hooks", "confidential-terms.json")
    with open(terms_path, "w", encoding="utf-8") as f:
        json.dump({"synthetic_deal": {"active": True, "always": ["zephyr corp"]}}, f)

    linked_wt = os.path.join(td, "linked-wt")
    subprocess.run(["git", "-C", main_repo, "worktree", "add", linked_wt, "-b", "wt-branch"],
                    check=True, capture_output=True)

    expect("setup: linked worktree genuinely lacks a local terms file (proves the repro)",
           not os.path.isfile(os.path.join(linked_wt, "hooks", "confidential-terms.json")))

    saved_hook_dir, saved_terms_file = pps.HOOK_DIR, pps.TERMS_FILE

    def _point_at(worktree):
        pps.HOOK_DIR = os.path.join(worktree, "hooks")
        pps.TERMS_FILE = os.path.join(pps.HOOK_DIR, "confidential-terms.json")

    try:
        _point_at(linked_wt)
        expect("load_terms: falls back to main worktree's terms file",
               pps.load_terms() == ["zephyr corp"])

        # Truly missing everywhere (main copy removed too) must still fail closed.
        os.remove(terms_path)
        _point_at(linked_wt)
        expect("load_terms: missing everywhere -> None (fail-closed preserved)",
               pps.load_terms() is None)
    finally:
        pps.HOOK_DIR, pps.TERMS_FILE = saved_hook_dir, saved_terms_file

passed = sum(1 for ok, _ in results if ok)
print("\ngit-prepush-scan tests: %d/%d passed" % (passed, len(results)))
sys.exit(0 if passed == len(results) else 1)
