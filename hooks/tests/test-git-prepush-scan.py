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

# This test spins up its own throwaway git repos in temp dirs. When invoked as part of
# the real pre-push hook chain, git sets GIT_DIR/GIT_WORK_TREE/GIT_INDEX_FILE (etc.) in
# this process's environment so IT can operate on the outer repo -- but those same vars
# leak into every subprocess git call below and silently redirect them at the outer repo
# instead of the temp one, breaking `git -C <tempdir> add/commit` with pathspec/128 errors.
for _v in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR",
           "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_PREFIX"):
    os.environ.pop(_v, None)

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

        # Local copy present but malformed must ALSO fall back, not just an absent one.
        local_terms = os.path.join(linked_wt, "hooks", "confidential-terms.json")
        with open(local_terms, "w", encoding="utf-8") as f:
            f.write("{not valid json")
        _point_at(linked_wt)
        expect("load_terms: falls back on a corrupt local file, not just a missing one",
               pps.load_terms() == ["zephyr corp"])
        os.remove(local_terms)

        # Truly missing everywhere (main copy removed too) must still fail closed.
        os.remove(terms_path)
        _point_at(linked_wt)
        expect("load_terms: missing everywhere -> None (fail-closed preserved)",
               pps.load_terms() is None)
    finally:
        pps.HOOK_DIR, pps.TERMS_FILE = saved_hook_dir, saved_terms_file

# --- load_terms(): no git repo at all (git rev-parse fails) -> still fail-closed --
# Covers _git_common_dir's own failure path (not a repo / git unavailable), distinct
# from the "resolves fine but file absent" case above.
with tempfile.TemporaryDirectory() as td:
    orphan_hooks = os.path.join(td, "not-a-repo", "hooks")
    os.makedirs(orphan_hooks)
    saved_hook_dir, saved_terms_file = pps.HOOK_DIR, pps.TERMS_FILE
    pps.HOOK_DIR = orphan_hooks
    pps.TERMS_FILE = os.path.join(orphan_hooks, "confidential-terms.json")
    try:
        expect("load_terms: HOOK_DIR outside any git repo -> None (fail-closed preserved)",
               pps.load_terms() is None)
    finally:
        pps.HOOK_DIR, pps.TERMS_FILE = saved_hook_dir, saved_terms_file

# --- credential scan (Gabriel ruling, 2026-07-24) ----------------------------------
# The gate previously carried ZERO credential patterns: it blocked confidential deal terms
# only, so nothing stopped an API key reaching ZeOoba/ora-claude-config.
expect("credential module is wired in", pps._sp is not None)

LEAK_DIFF = ("diff --git a/memory/notes.md b/memory/notes.md\n"
             "+++ b/memory/notes.md\n"
             "+the key is sk-ant-api03-" + "z" * 20 + "\n")
FIXTURE_DIFF = ("diff --git a/maintenance/test-scrub-before-optin.py "
                "b/maintenance/test-scrub-before-optin.py\n"
                "+++ b/maintenance/test-scrub-before-optin.py\n"
                "+    (\"AWS\", \"AKIAIOSFODNN7EXAMPLE\"),\n")

expect("a real credential in the pushed history is detected",
       [p for p, _ in pps._sp.scan_diff(LEAK_DIFF)] == ["memory/notes.md"],
       pps._sp.scan_diff(LEAK_DIFF))
expect("the scanner's OWN test fixture does not trip the gate (else every push blocks)",
       pps._sp.scan_diff(FIXTURE_DIFF) == [], pps._sp.scan_diff(FIXTURE_DIFF))

# BEHAVIOURAL REGRESSION GUARD -- the one that matters most, and it must be behavioural:
# main() used to `return 0` immediately when no deal was active, which is the state TODAY,
# so a credential scan placed after that early exit would have been DEAD ON ARRIVAL. Prove
# the gate actually blocks against a real repo rather than asserting on source text.
def _run_gate_on(repo, stdin_text):
    return subprocess.run(
        [sys.executable, os.path.join(HOOKS, "git-prepush-confidential-scan.py"),
         "origin", "https://example.invalid/x.git"],
        input=stdin_text, capture_output=True, text=True, cwd=repo)


def _mk_repo(filename, content):
    repo = tempfile.mkdtemp()
    for cmd in (["git", "init", "-q"],
                ["git", "config", "user.email", "t@example.invalid"],
                ["git", "config", "user.name", "t"]):
        subprocess.run(cmd, cwd=repo, capture_output=True)
    with open(os.path.join(repo, filename), "w", encoding="utf-8") as fh:
        fh.write(content)
    subprocess.run(["git", "add", "-A"], cwd=repo, capture_output=True)
    subprocess.run(["git", "commit", "-qm", "x"], cwd=repo, capture_output=True)
    sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo,
                         capture_output=True, text=True).stdout.strip()
    return repo, "refs/heads/main %s refs/heads/main %s\n" % (sha, ZERO)


# Real credential, no active deal terms -> MUST block (the dead-on-arrival case).
repo, stdin_text = _mk_repo("notes.md", "the key is sk-ant-api03-" + "z" * 20 + "\n")
r = _run_gate_on(repo, stdin_text)
expect("credential blocks the push even with NO active deal terms", r.returncode == 1,
       "exit=%s err=%s" % (r.returncode, r.stderr[:200]))
expect("the block message names the file", "notes.md" in r.stderr, r.stderr[:200])
expect("the block message never echoes the value", "sk-ant-api03" not in r.stderr,
       r.stderr[:200])

# Clean repo -> allow.
repo2, stdin2 = _mk_repo("notes.md", "DSCR 1.25x, LTV 40%, nothing secret here\n")
r2 = _run_gate_on(repo2, stdin2)
expect("a clean push is still allowed", r2.returncode == 0,
       "exit=%s err=%s" % (r2.returncode, r2.stderr[:200]))

# A test fixture carrying fake keys -> allow (else every push blocks forever).
repo3, stdin3 = _mk_repo("test-thing.py", '("AWS", "AKIAIOSFODNN7EXAMPLE")\n')
r3 = _run_gate_on(repo3, stdin3)
expect("a test fixture with fake keys does NOT block the push", r3.returncode == 0,
       "exit=%s err=%s" % (r3.returncode, r3.stderr[:200]))

# Values must never be echoed -- a gate that prints the secret has leaked it into the
# terminal transcript and any CI log capturing stderr.
expect("scan_diff returns labels, never the matched value",
       all("sk-ant" not in lab
           for _, labels in pps._sp.scan_diff(LEAK_DIFF) for lab in labels))

passed = sum(1 for ok, _ in results if ok)
print("\ngit-prepush-scan tests: %d/%d passed" % (passed, len(results)))
sys.exit(0 if passed == len(results) else 1)
