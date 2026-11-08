#!/usr/bin/env python3
"""Tests for git-prepush-confidential-scan.py (pure functions only, synthetic terms).

The scanner is the 2026-06-11 incident lesson made executable: a pre-push gate must
scan the FULL HISTORY being pushed (git log -p over each pushed range), not the tree.
Run: python test-git-prepush-scan.py   (exit 0 = all pass)
"""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"))
import gitfixture  # noqa: E402  (shared repo fixture -- open-items-tracker.md#OI-061)

# This test spins up its own throwaway git repos in temp dirs. When invoked as part of
# the real pre-push hook chain, git sets GIT_DIR/GIT_WORK_TREE/GIT_INDEX_FILE (etc.) in
# this process's environment so IT can operate on the outer repo -- but those same vars
# leak into every subprocess git call below and silently redirect them at the outer repo
# instead of the temp one, breaking `git -C <tempdir> add/commit` with pathspec/128 errors.
_GIT_LEAK_VARS = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR",
                   "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_PREFIX")
for _v in _GIT_LEAK_VARS:
    os.environ.pop(_v, None)


def _clean_env():
    """A fresh env dict with the leak vars stripped, built PER CALL rather than relying
    on the one-time os.environ mutation above -- so a git call stays hermetic even if
    something re-populates one of these vars in this process later."""
    env = dict(os.environ)
    for _v in _GIT_LEAK_VARS:
        env.pop(_v, None)
    return env


def _unique_branch_name(prefix="wt-branch"):
    """A hardcoded branch name is a real repo-level collision risk: `git worktree add -b
    <name>` registers the branch + worktree admin entry in the repo's SHARED common dir,
    not scoped to the throwaway tempdir. If GIT_DIR/GIT_COMMON_DIR ever leaks into this
    process, the branch lands in the shared real repo and PERSISTS there across runs --
    live-verified 2026-07-25: a leaked run left a real `wt-branch` ref sitting in
    ~/.claude's own .git for hours, colliding with later unrelated test runs. A unique
    suffix per call means even a leaked run can never collide with another."""
    return "%s-%s" % (prefix, uuid.uuid4().hex[:12])


# --- Whole-directory-pair template cache (2026-08-12) ------------------------------
# This file measured at 179 git spawns / 189 total (94% of wall time), the worst
# offender not already covered by shared lib/gitfixture.py, because it hand-rolls
# (bare-origin, local-clone) repo PAIRS and rebuilds each from scratch on every use.
# Two of the three such shapes are genuinely REPEATED with the same content -- the ones
# templated here: _mk_bare_origin_with_seed's origin (x3 via _mk_repo) and
# _mk_repo_with_history's pair (x5, the single biggest cost -- ~50 of the 179 spawns).
# _mk_origin_and_clone_state's pair is called only twice, once per trunk_name ("main",
# "master") -- two DIFFERENT cache keys, never a repeat -- so it is deliberately left
# hand-rolled; caching it would add indirection for zero measured savings.
#
# gitfixture.py's public API (blank_repo/repo_with_commit) only templates a SINGLE
# repo, not an origin+local PAIR with the local already fetched from the origin -- so
# this is a locally-scoped extension of the same technique (build once, `shutil.
# copytree` per call), not a change to the shared module. Kept local deliberately:
# gitfixture is depended on by 13+ files, and this shape is specific to a scanner test
# that needs a REACHABLE-history origin, not a general-purpose fixture.
#
# SAFETY ARGUMENT for why copying the pair together is correct despite `origin`'s
# absolute path going stale after the copy (a fresh local repo's .git/config still
# names the OLD origin.git location): every call site using this cache fetches from
# origin during INITIAL SETUP ONLY, then works purely against already-fetched refs
# (refs/remotes/origin/main, local objects) for the rest of that test case -- verified
# by reading every call site AND git-prepush-confidential-scan.py's own baseline-
# resolution code before writing this cache, not assumed. If a future test needs to
# push/fetch AGAIN after setup, it must NOT use this cache; build fresh instead.
_PAIR_TEMPLATES = {}


def _build_pair_template(key, builder):
    """Build directory-pair shape `key` once via `builder(root) -> None` (writes into
    a fresh `root`), cache the resulting root, return it. `builder` does the real git
    spawns; every LATER call for the same key costs zero spawns."""
    root = _PAIR_TEMPLATES.get(key)
    if root is not None:
        return root
    root = tempfile.mkdtemp(prefix="pps-tpl-")
    builder(root)
    _PAIR_TEMPLATES[key] = root
    return root


def _clone_pair(key, builder):
    """Materialise a fresh, independent copy of directory-pair shape `key` (building
    the template on first use) and return its root. Every file under the template is
    duplicated -- the caller owns a real, mutable directory tree, indistinguishable
    from one built fresh, at zero subprocess cost after the first call."""
    template = _build_pair_template(key, builder)
    dest = tempfile.mkdtemp(prefix="pps-repo-")
    shutil.copytree(template, dest, dirs_exist_ok=True)  # matches gitfixture._clone_template
    return dest


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


# END-TO-END cases spawn the real git-prepush-confidential-scan.py, which reads the
# LIVE, gitignored hooks/confidential-terms.json (falling back to the main worktree's
# copy) and fails CLOSED when neither is readable. Without the roster every such case
# is meaningless: "expect allowed" cases fail, and "expect blocked" cases pass for the
# WRONG reason (blocked by the fail-closed branch, not by the credential scan). So when
# the roster is unreadable -- a clean CI checkout by design (2026-11-06, PR #423) --
# those cases are SKIPPED, not counted; every pure/fixture assertion still runs and
# still fails the file. Resolved with the module's OWN load_terms(), the exact
# resolution the subprocess uses, BEFORE any test below monkeypatches pps.TERMS_FILE.
LIVE_ROSTER = pps.load_terms() is not None
gate_skipped = []


def expect_gate(label, cond, detail=""):
    """expect() for an end-to-end assertion that needs the live roster (see above)."""
    if not LIVE_ROSTER:
        gate_skipped.append(label)
        return
    expect(label, cond, detail)


ZERO = "0" * 40
SHA_A = "a" * 40
SHA_B = "b" * 40
TERMS = ["zephyr corp", "9999 example ave"]  # synthetic — never real deal terms here

# --- parse_pushrefs ---------------------------------------------------------------
refs = pps.parse_pushrefs(
    "refs/heads/main %s refs/heads/main %s\nnot a ref line\n" % (SHA_A, SHA_B))
expect("parse: one valid line", len(refs) == 1 and refs[0][1] == SHA_A and refs[0][3] == SHA_B)
expect("parse: empty input", pps.parse_pushrefs("") == [])

# --- rev_range ----------------------------------------------------------------------
# 2026-07-25 false-positive fix: a brand-new remote ref (remote_sha all-zero) must be
# bounded to baseline..local_sha -- NOT local_sha alone, which made `git log -p` dump the
# entire history reachable from local_sha and re-flag commits already public on
# origin/main on every first push of any new branch (repro: a6f0689).
expect("range: existing remote -> delta range (unchanged, baseline irrelevant)",
       pps.rev_range(SHA_A, SHA_B, "origin/main") == "%s..%s" % (SHA_B, SHA_A))
expect("range: new remote ref + resolvable baseline -> bounded to baseline..local",
       pps.rev_range(SHA_A, ZERO, "origin/main") == "origin/main..%s" % SHA_A)
expect("range: new remote ref + NO resolvable baseline -> None (fail-closed signal, "
       "not a silent full-history rescan)",
       pps.rev_range(SHA_A, ZERO, None) is None)

# --- _resolve_default_baseline -------------------------------------------------------
def _git(*args, cwd, check=True):
    return subprocess.run(["git", "-C", cwd] + list(args), capture_output=True, text=True, check=check)


def _mk_origin_and_clone_state(trunk_name):
    """A local repo with an `origin` remote (a real bare repo) that has fetched a
    `trunk_name` branch -- mirrors a real clone/fetch. Returns (local_dir, origin_dir).

    DELIBERATELY NOT templated via _clone_pair, unlike the two shapes below: this is
    called exactly twice, once each for "main" and "master" -- two DIFFERENT cache
    keys, so a template cache would build fresh both times and save nothing while
    adding indirection to a security-gate test file for no measured benefit. Left as
    the plain hand-rolled form on purpose."""
    root = tempfile.mkdtemp()
    origin_dir = os.path.join(root, "origin.git")
    local_dir = os.path.join(root, "local")
    subprocess.run(["git", "init", "-q", "--bare", origin_dir], check=True)
    subprocess.run(["git", "init", "-q", local_dir], check=True)
    _git("config", "user.email", "t@example.invalid", cwd=local_dir)
    _git("config", "user.name", "t", cwd=local_dir)
    with open(os.path.join(local_dir, "f.txt"), "w", encoding="utf-8") as f:
        f.write("seed\n")
    _git("add", "-A", cwd=local_dir)
    _git("commit", "-q", "-m", "seed", cwd=local_dir)
    _git("branch", "-M", trunk_name, cwd=local_dir)
    _git("remote", "add", "origin", origin_dir, cwd=local_dir)
    _git("push", "-q", "origin", trunk_name, cwd=local_dir)
    _git("fetch", "-q", "origin", cwd=local_dir)
    return local_dir, origin_dir


_local, _origin = _mk_origin_and_clone_state("main")
try:
    expect("_resolve_default_baseline: falls back to origin/main when the HEAD symref "
           "was never set (a plain `git fetch` doesn't set it) -- fully-qualified, "
           "never the shadowable short name",
           pps._resolve_default_baseline(_local) == "refs/remotes/origin/main")
    _git("remote", "set-head", "origin", "main", cwd=_local)
    expect("_resolve_default_baseline: prefers the tracked origin/HEAD symref once set",
           pps._resolve_default_baseline(_local) == "refs/remotes/origin/main")
finally:
    shutil.rmtree(os.path.dirname(_local), ignore_errors=True)

_local2, _origin2 = _mk_origin_and_clone_state("master")
try:
    expect("_resolve_default_baseline: falls back to origin/master when origin/main "
           "doesn't exist",
           pps._resolve_default_baseline(_local2) == "refs/remotes/origin/master")
finally:
    shutil.rmtree(os.path.dirname(_local2), ignore_errors=True)

with tempfile.TemporaryDirectory() as td:
    subprocess.run(["git", "init", "-q", td], check=True)
    expect("_resolve_default_baseline: no `origin` remote at all -> None "
           "(fail-closed signal)",
           pps._resolve_default_baseline(td) is None)

with tempfile.TemporaryDirectory() as td:
    expect("_resolve_default_baseline: not a git repo at all -> None",
           pps._resolve_default_baseline(td) is None)

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
    subprocess.run(["git", "init", "-q", main_repo], check=True, env=_clean_env())
    subprocess.run(["git", "-C", main_repo, "config", "user.email", "t@example.com"],
                    check=True, env=_clean_env())
    subprocess.run(["git", "-C", main_repo, "config", "user.name", "t"], check=True, env=_clean_env())
    with open(os.path.join(main_repo, "README.md"), "w") as f:
        f.write("seed\n")
    # A tracked file under hooks/ so the directory itself is materialized into a
    # linked worktree's checkout -- mirrors the real repo, where hooks/ holds many
    # tracked files and only confidential-terms.json is gitignored out of it.
    with open(os.path.join(main_repo, "hooks", "placeholder.py"), "w") as f:
        f.write("# tracked placeholder\n")
    subprocess.run(["git", "-C", main_repo, "add", "README.md", "hooks/placeholder.py"],
                    check=True, env=_clean_env())
    subprocess.run(["git", "-C", main_repo, "commit", "-q", "-m", "seed"], check=True, env=_clean_env())

    # Never committed -- mirrors the real file being gitignored (present in the
    # main checkout's working tree, absent from anything `git worktree add` creates).
    terms_path = os.path.join(main_repo, "hooks", "confidential-terms.json")
    with open(terms_path, "w", encoding="utf-8") as f:
        json.dump({"synthetic_deal": {"active": True, "always": ["zephyr corp"]}}, f)

    linked_wt = os.path.join(td, "linked-wt")
    subprocess.run(["git", "-C", main_repo, "worktree", "add", linked_wt, "-b", _unique_branch_name()],
                    check=True, capture_output=True, env=_clean_env())

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


def _mk_bare_origin_with_seed():
    """A bare repo with one commit on `main`, unrelated to anything a caller later
    commits -- used as an `origin` remote so the fixed gate's default-branch baseline
    resolves (mirrors a real clone having fetched), the same way it always must for a
    genuine push. Callers built on top of this share no history with it, so their
    own commits have no merge-base with origin/main -- the orphan-branch case -- and
    are scanned in FULL, preserving this file's original "one commit, fully scanned"
    fixture semantics under the new bounded-range logic.

    TEMPLATED (2026-08-12): the seed content is fixed, so origin.git is byte-identical
    on every call -- 3 callers via _mk_repo. The scratch "seed" working tree that
    builds it is discarded immediately after the push (never returned, never reused),
    so it lives OUTSIDE the cached template and is not copied on later calls."""
    def _build(root):
        origin_dir = os.path.join(root, "origin.git")
        seed = tempfile.mkdtemp(prefix="pps-seed-scratch-")
        try:
            subprocess.run(["git", "init", "-q", "--bare", origin_dir], check=True)
            subprocess.run(["git", "init", "-q", seed], check=True)
            _git("config", "user.email", "t@example.invalid", cwd=seed)
            _git("config", "user.name", "t", cwd=seed)
            with open(os.path.join(seed, "SEED.md"), "w", encoding="utf-8") as f:
                f.write("unrelated origin seed\n")
            _git("add", "-A", cwd=seed)
            _git("commit", "-q", "-m", "seed", cwd=seed)
            _git("branch", "-M", "main", cwd=seed)
            _git("remote", "add", "origin", origin_dir, cwd=seed)
            _git("push", "-q", "origin", "main", cwd=seed)
        finally:
            shutil.rmtree(seed, ignore_errors=True)

    root = _clone_pair(("bare_origin_with_seed",), _build)
    return os.path.join(root, "origin.git")


def _mk_repo(filename, content):
    origin_dir = _mk_bare_origin_with_seed()
    # The local half's init+config is a fixed shape (same identity every call) --
    # gitfixture already templates exactly this, so use it directly rather than
    # duplicating the technique. remote add + fetch stay live: they need this call's
    # actual origin_dir path and genuinely talk to it, so they cannot be cached.
    repo = gitfixture.blank_repo(prefix="pps-repo-", identity=("t@example.invalid", "t"))
    for cmd in (["git", "-C", repo, "remote", "add", "origin", origin_dir],
                ["git", "-C", repo, "fetch", "-q", "origin"]):
        subprocess.run(cmd, capture_output=True)
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
expect_gate("credential blocks the push even with NO active deal terms", r.returncode == 1,
       "exit=%s err=%s" % (r.returncode, r.stderr[:200]))
expect_gate("the block message names the file", "notes.md" in r.stderr, r.stderr[:200])
expect_gate("the block message never echoes the value", "sk-ant-api03" not in r.stderr,
       r.stderr[:200])

# Clean repo -> allow.
repo2, stdin2 = _mk_repo("notes.md", "DSCR 1.25x, LTV 40%, nothing secret here\n")
r2 = _run_gate_on(repo2, stdin2)
expect_gate("a clean push is still allowed", r2.returncode == 0,
       "exit=%s err=%s" % (r2.returncode, r2.stderr[:200]))

# A test fixture carrying fake keys -> allow (else every push blocks forever).
repo3, stdin3 = _mk_repo("test-thing.py", '("AWS", "AKIAIOSFODNN7EXAMPLE")\n')
r3 = _run_gate_on(repo3, stdin3)
expect_gate("a test fixture with fake keys does NOT block the push", r3.returncode == 0,
       "exit=%s err=%s" % (r3.returncode, r3.stderr[:200]))

# Values must never be echoed -- a gate that prints the secret has leaked it into the
# terminal transcript and any CI log capturing stderr.
expect("scan_diff returns labels, never the matched value",
       all("sk-ant" not in lab
           for _, labels in pps._sp.scan_diff(LEAK_DIFF) for lab in labels))

# --- End-to-end: new branch, clean commits on top of already-public history --------
# The core repro this fix addresses: a base branch has an OLD commit with a
# placeholder-shaped credential string, already pushed/fetched as origin/main. A NEW
# branch built on top adds only clean commits. The fixed gate must NOT re-flag the old,
# already-public commit -- only genuinely new history should ever be scanned.
def _mk_repo_with_history():
    """(local_dir, origin_dir) -- origin/main has one commit with a placeholder-shaped
    credential string (mirrors the real a6f0689/secrets.env.example repro), already
    fetched into the local clone.

    TEMPLATED (2026-08-12): this is the file's single biggest spawn cost -- 5 call
    sites (cases 1/2/3/5/6 below), each rebuilding a byte-identical origin+local pair
    from scratch before adding its OWN further commits on top. Verified every caller
    before converting this: none re-fetches or re-pushes against origin_dir after this
    function returns (see the safety-argument comment above _PAIR_TEMPLATES), and
    _resolve_default_baseline / the scan itself both operate on local refs and objects
    only -- confirmed by reading git-prepush-confidential-scan.py directly, not
    assumed.

    After copying, this repoints `local`'s origin remote at its OWN copy's origin.git,
    not the shared template's (caught in independent review). Without this the copied
    local repo's config still names the template's path -- harmless for every current
    caller since none touches origin again, but only by convention, and a future test
    that DID push/fetch post-setup would silently mutate the shared template and poison
    every later copy in the same run, with no error to signal it. One extra spawn per
    call turns that from a documentation-enforced invariant into a structural one."""
    def _build(root):
        origin_dir = os.path.join(root, "origin.git")
        local_dir = os.path.join(root, "local")
        subprocess.run(["git", "init", "-q", "--bare", origin_dir], check=True)
        subprocess.run(["git", "init", "-q", local_dir], check=True)
        _git("config", "user.email", "t@example.invalid", cwd=local_dir)
        _git("config", "user.name", "t", cwd=local_dir)
        with open(os.path.join(local_dir, "secrets.env.example"), "w", encoding="utf-8") as f:
            f.write('# ANTHROPIC_API_KEY="sk-ant-REPLACE_ME"\n')
        _git("add", "-A", cwd=local_dir)
        _git("commit", "-q", "-m", "old placeholder commit (already public)", cwd=local_dir)
        _git("branch", "-M", "main", cwd=local_dir)
        _git("remote", "add", "origin", origin_dir, cwd=local_dir)
        _git("push", "-q", "origin", "main", cwd=local_dir)
        _git("fetch", "-q", "origin", cwd=local_dir)

    root = _clone_pair(("repo_with_history",), _build)
    local_dir = os.path.join(root, "local")
    origin_dir = os.path.join(root, "origin.git")
    _git("remote", "set-url", "origin", origin_dir, cwd=local_dir)
    return local_dir, origin_dir


# 1) New branch, only clean new commits -> ALLOWED (must not re-flag the old commit).
_local3, _origin3 = _mk_repo_with_history()
try:
    _git("checkout", "-q", "-b", "feature-clean", cwd=_local3)
    with open(os.path.join(_local3, "clean.py"), "w", encoding="utf-8") as f:
        f.write("DSCR 1.25x, LTV 40 pct -- nothing secret\n")
    _git("add", "-A", cwd=_local3)
    _git("commit", "-q", "-m", "clean new commit", cwd=_local3)
    _feature_sha = _git("rev-parse", "HEAD", cwd=_local3).stdout.strip()
    _stdin = "refs/heads/feature-clean %s refs/heads/feature-clean %s\n" % (_feature_sha, ZERO)
    _r = _run_gate_on(_local3, _stdin)
    expect_gate("new branch with only clean commits on old placeholder history -> ALLOWED "
           "(the 2026-07-25 false positive this fix addresses)",
           _r.returncode == 0, "exit=%s err=%s" % (_r.returncode, _r.stderr[:300]))
finally:
    shutil.rmtree(os.path.dirname(_local3), ignore_errors=True)

# 2) New branch whose OWN new commit carries a genuine leak -> still BLOCKED (the fix
#    must not weaken detection of genuinely new secrets, only stop re-flagging old ones).
_local4, _origin4 = _mk_repo_with_history()
try:
    _git("checkout", "-q", "-b", "feature-leak", cwd=_local4)
    with open(os.path.join(_local4, "oops.py"), "w", encoding="utf-8") as f:
        f.write("REAL_KEY = \"sk-ant-api03-" + "z" * 20 + "\"\n")
    _git("add", "-A", cwd=_local4)
    _git("commit", "-q", "-m", "oops, real key", cwd=_local4)
    _leak_sha = _git("rev-parse", "HEAD", cwd=_local4).stdout.strip()
    _stdin = "refs/heads/feature-leak %s refs/heads/feature-leak %s\n" % (_leak_sha, ZERO)
    _r = _run_gate_on(_local4, _stdin)
    expect_gate("new branch whose OWN new commit leaks a real key -> still BLOCKED "
           "(bounded range does not weaken detection of genuinely new secrets)",
           _r.returncode == 1, "exit=%s err=%s" % (_r.returncode, _r.stderr[:300]))
    expect_gate("the block names the NEW file, not the old already-public commit's file",
           "oops.py" in _r.stderr and "secrets.env.example" not in _r.stderr,
           _r.stderr[:300])
finally:
    shutil.rmtree(os.path.dirname(_local4), ignore_errors=True)

# 3) Orphan branch (no merge-base with the default branch at all) -> scanned in FULL.
#    Decision, documented in rev_range()'s docstring: an orphan branch's history was
#    never reachable from the trunk, so none of it is "already public" -- it must all
#    be scanned, same as the (pre-fix) behavior for this specific case.
_local5, _origin5 = _mk_repo_with_history()
try:
    _git("checkout", "-q", "--orphan", "orphan-branch", cwd=_local5)
    subprocess.run(["git", "-C", _local5, "rm", "-rf", "-q", "."], capture_output=True)
    with open(os.path.join(_local5, "orphan-secret.py"), "w", encoding="utf-8") as f:
        f.write("REAL_KEY = \"sk-ant-api03-" + "y" * 20 + "\"\n")
    _git("add", "-A", cwd=_local5)
    _git("commit", "-q", "-m", "orphan history, never public", cwd=_local5)
    _orphan_sha = _git("rev-parse", "HEAD", cwd=_local5).stdout.strip()
    _stdin = "refs/heads/orphan-branch %s refs/heads/orphan-branch %s\n" % (_orphan_sha, ZERO)
    _r = _run_gate_on(_local5, _stdin)
    expect_gate("orphan branch (no merge-base with origin/main) is scanned in FULL -> BLOCKED",
           _r.returncode == 1, "exit=%s err=%s" % (_r.returncode, _r.stderr[:300]))
finally:
    shutil.rmtree(os.path.dirname(_local5), ignore_errors=True)

# 4) No resolvable default-branch baseline (no `origin` remote at all) -> fail closed
#    with a clear message, not a silent full-history rescan and not a silent allow.
with tempfile.TemporaryDirectory() as td:
    for cmd in (["git", "init", "-q", td],
                ["git", "-C", td, "config", "user.email", "t@example.invalid"],
                ["git", "-C", td, "config", "user.name", "t"]):
        subprocess.run(cmd, capture_output=True, check=True)
    with open(os.path.join(td, "notes.md"), "w", encoding="utf-8") as f:
        f.write("clean\n")
    subprocess.run(["git", "-C", td, "add", "-A"], check=True)
    subprocess.run(["git", "-C", td, "commit", "-q", "-m", "x"], check=True)
    _sha = _git("rev-parse", "HEAD", cwd=td).stdout.strip()
    _stdin = "refs/heads/main %s refs/heads/main %s\n" % (_sha, ZERO)
    _r = _run_gate_on(td, _stdin)
    # Assert the DISTINCTIVE "baseline could not be resolved" message, not just
    # "fetch" + exit 1 -- a `git log -p` failure for an unrelated reason (e.g. a
    # dangling/foreign sha) also says "run `git fetch` first" and exits 1, which
    # would make this pass for the wrong reason (caught in review).
    expect_gate("brand-new ref + no `origin` remote at all -> fail closed, not silently "
           "rescanned or silently allowed",
           _r.returncode == 1
           and "could not be resolved to bound the history scan" in _r.stderr,
           "exit=%s err=%s" % (_r.returncode, _r.stderr[:300]))

# 5) A LOCAL branch literally named "origin/main" must NOT shadow the real
#    refs/remotes/origin/main baseline. git's ref-disambiguation checks refs/heads/
#    before refs/remotes/, so an unqualified short name ("origin/main") could resolve
#    to this local branch instead of the real remote-tracking ref, silently EXCLUDING
#    a genuine secret from the scan -- a demonstrated false negative caught in review.
_local7, _origin7 = _mk_repo_with_history()
try:
    _git("checkout", "-q", "-b", "origin/main", cwd=_local7)  # legal branch name, never pushed
    with open(os.path.join(_local7, "shadow-secret.py"), "w", encoding="utf-8") as f:
        f.write("REAL_KEY = \"sk-ant-api03-" + "w" * 20 + "\"\n")
    _git("add", "-A", cwd=_local7)
    _git("commit", "-q", "-m", "secret sitting on a branch named origin/main", cwd=_local7)
    _shadow_sha = _git("rev-parse", "HEAD", cwd=_local7).stdout.strip()
    _stdin = "refs/heads/feature-x %s refs/heads/feature-x %s\n" % (_shadow_sha, ZERO)
    _r = _run_gate_on(_local7, _stdin)
    expect_gate("a local branch literally named 'origin/main' cannot shadow the real "
           "baseline -- the secret it carries is still BLOCKED",
           _r.returncode == 1, "exit=%s err=%s" % (_r.returncode, _r.stderr[:300]))
finally:
    shutil.rmtree(os.path.dirname(_local7), ignore_errors=True)

# 6) A poisoned refs/remotes/origin/HEAD symref pointing at a refs/heads/... branch
#    (reachable only via the low-level plumbing `git symbolic-ref`, not the normal
#    `git remote set-head`, which rejects a refs/heads/ target) must NOT be trusted --
#    caught in the second review round for the same reason as case 5: only a
#    refs/remotes/... target may ever become the baseline.
_local8, _origin8 = _mk_repo_with_history()
try:
    _git("checkout", "-q", "-b", "poison", cwd=_local8)
    with open(os.path.join(_local8, "poisoned-secret.py"), "w", encoding="utf-8") as f:
        f.write("REAL_KEY = \"sk-ant-api03-" + "v" * 20 + "\"\n")
    _git("add", "-A", cwd=_local8)
    _git("commit", "-q", "-m", "secret on the branch the poisoned symref points at", cwd=_local8)
    # Low-level plumbing: points refs/remotes/origin/HEAD at a refs/heads/ branch.
    # `git remote set-head` refuses this; `git symbolic-ref` does not enforce it.
    _git("symbolic-ref", "refs/remotes/origin/HEAD", "refs/heads/poison", cwd=_local8)
    _poison_sha = _git("rev-parse", "HEAD", cwd=_local8).stdout.strip()
    _stdin = "refs/heads/feature-y %s refs/heads/feature-y %s\n" % (_poison_sha, ZERO)
    _r = _run_gate_on(_local8, _stdin)
    expect_gate("a refs/remotes/origin/HEAD symref poisoned to point at a refs/heads/ "
           "branch is ignored -- the secret it carries is still BLOCKED",
           _r.returncode == 1, "exit=%s err=%s" % (_r.returncode, _r.stderr[:300]))
finally:
    shutil.rmtree(os.path.dirname(_local8), ignore_errors=True)

# --- Meta: the gate's own source stays scan-clean ----------------------------------
# A credential-shaped literal anywhere in this file's own source (e.g. a placeholder
# spelled out verbatim in a docstring, as this fix itself did before review caught it)
# would block every future push that touches this file -- since it's the one path
# secret_patterns.is_exempt_path() cannot mark exempt without also exempting the
# thing it's supposed to guard.
with open(os.path.join(HOOKS, "git-prepush-confidential-scan.py"), encoding="utf-8") as _f:
    _own_source = _f.read()
expect("the gate's own source contains no credential-shaped strings",
       pps._sp.scan_text(_own_source) == [], pps._sp.scan_text(_own_source))

# --- Real-repo regression test (2026-07-25 false positive) -------------------------
# This repo's OWN history genuinely reproduces the bug: a6f0689 is an already-public
# ancestor of origin/main whose diff carries a documented placeholder
# ("sk-ant-REPLACE_ME" in server/secrets.env.example) that the OLD, unbounded
# rev_range(local_sha, ZERO) == local_sha behavior would re-scan (and block on) on
# every first push of ANY new branch. Skips gracefully (not a failure) if this
# checkout can't resolve origin/main or if a6f0689 is no longer part of its history --
# the assertion needs real repo state, not a synthetic fixture.
REPO_ROOT = os.path.dirname(HOOKS)
A6F0689 = "a6f0689abd55f98fda916bb7f09a64a92b42a5b9"
_om = subprocess.run(["git", "-C", REPO_ROOT, "rev-parse", "-q", "--verify", "origin/main"],
                     capture_output=True, text=True)
if _om.returncode != 0:
    print("SKIP: real-repo regression test -- origin/main not resolvable in this checkout")
else:
    _anc = subprocess.run(["git", "-C", REPO_ROOT, "merge-base", "--is-ancestor", A6F0689, "origin/main"])
    if _anc.returncode != 0:
        print("SKIP: real-repo regression test -- %s is no longer an ancestor of "
              "origin/main (history rewritten?)" % A6F0689)
    else:
        # Prove the bug was real: the OLD unbounded `git log -p local_sha` behavior
        # (no range at all) genuinely trips the credential scan on a6f0689's own diff.
        _old_log = subprocess.run(["git", "-C", REPO_ROOT, "log", "-p", "--no-color", A6F0689],
                                  capture_output=True)
        _old_body = _old_log.stdout.decode("utf-8", "ignore")
        _old_labels = [lab for _, labs in pps._sp.scan_diff(_old_body) for lab in labs]
        expect("real repo: the OLD unbounded range genuinely reproduces the false "
               "positive (a6f0689's own diff trips the credential scan)",
               "Anthropic API key" in _old_labels, _old_labels)

        # NEW behavior: pushing a6f0689 as a brand-new ref, with origin/main resolvable
        # as baseline, bounds the range to origin/main..a6f0689 -- empty, since a6f0689
        # is already an ancestor of origin/main -- so nothing is scanned and it's allowed.
        _stdin = "refs/heads/x %s refs/heads/x %s\n" % (A6F0689, ZERO)
        _r = subprocess.run(
            [sys.executable, os.path.join(HOOKS, "git-prepush-confidential-scan.py"),
             "origin", "https://example.invalid/x.git"],
            input=_stdin, capture_output=True, text=True, cwd=REPO_ROOT)
        expect_gate("real repo: fixed gate allows a brand-new ref pointing at an "
               "already-public commit (2026-07-25 false positive, resolved)",
               _r.returncode == 0, "exit=%s err=%s" % (_r.returncode, _r.stderr[:500]))

passed = sum(1 for ok, _ in results if ok)
print("\ngit-prepush-scan tests: %d/%d passed" % (passed, len(results)))
if passed != len(results):
    # A real failure is a FAIL even when end-to-end cases were also skipped: the
    # ENV-SKIP sentinel below must never mask a fixture regression.
    sys.exit(1)
if gate_skipped:
    print("CANNOT RUN: %d end-to-end case(s) need the live hooks/confidential-terms.json "
          "(unreadable here and in the main worktree); all %d other assertions passed. "
          "Skipped: %s" % (len(gate_skipped), len(results), "; ".join(gate_skipped)))
    sys.exit(1)
sys.exit(0)
