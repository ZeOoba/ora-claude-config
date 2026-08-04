#!/usr/bin/env python3
"""Tests for isolated_commit.py -- staging an exact text-replacement hunk into
the git index without touching other uncommitted changes to the same file.

The core scenario this exists to prove (see the module's docstring for the
real incident): file has an OTHER session's uncommitted edit sitting in the
working tree; stage_isolated_replacement() must stage only MY hunk, leave
their edit exactly as it was, and a subsequent `git commit` must produce a
commit containing ONLY my change.

Run: python test-isolated-commit.py   (exit 0 = all pass)
"""
import os
import subprocess
import sys

for _v in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR",
           "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_PREFIX"):
    os.environ.pop(_v, None)

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "lib"))
import gitfixture  # noqa: E402

sys.path.insert(0, os.path.join(HERE, "..", "lib"))
import isolated_commit as ic  # noqa: E402

results = []


def check(label, cond, detail=""):
    results.append((bool(cond), label))
    if not cond:
        print("  FAIL: %s %s" % (label, detail))


def git(repo, *args):
    return subprocess.run(["git", "-C", repo] + list(args),
                          capture_output=True, text=True)


DOC = "line one\nold middle line\nline three\n"

# --- scenario 1: the core case -- my isolated hunk coexists with an OTHER
# session's unrelated uncommitted edit to the SAME file ---
repo = gitfixture.repo_with_commit(files={"doc.md": DOC})

with open(os.path.join(repo, "doc.md"), "a", encoding="utf-8") as f:
    f.write("an unrelated line another session added, uncommitted\n")
with open(os.path.join(repo, "doc.md"), encoding="utf-8") as f:
    other_session_working_copy = f.read()

ic.stage_isolated_replacement(repo, "doc.md", "old middle line", "NEW middle line")

staged = git(repo, "show", ":doc.md").stdout
check("staged content has my replacement", "NEW middle line" in staged, staged)
check("staged content does NOT include the other session's uncommitted line",
      "an unrelated line" not in staged, staged)

with open(os.path.join(repo, "doc.md"), encoding="utf-8") as f:
    working_copy_after = f.read()
check("working tree UNCHANGED by staging (still has both edits, uncommitted)",
      working_copy_after == other_session_working_copy, working_copy_after)

r = git(repo, "-c", "user.email=t@t.t", "-c", "user.name=t", "commit", "-qm", "my isolated hunk")
check("commit succeeded", r.returncode == 0, r.stderr)

committed = git(repo, "show", "HEAD:doc.md").stdout
check("commit contains my replacement", "NEW middle line" in committed, committed)
check("commit does NOT contain the other session's line (never swept in)",
      "an unrelated line" not in committed, committed)

status_after_commit = git(repo, "status", "--porcelain").stdout
check("the other session's edit is STILL uncommitted after my commit",
      "doc.md" in status_after_commit, status_after_commit)
with open(os.path.join(repo, "doc.md"), encoding="utf-8") as f:
    working_copy_final = f.read()
check("the other session's exact uncommitted content is intact",
      "an unrelated line another session added, uncommitted" in working_copy_final,
      working_copy_final)

# --- scenario 2: old_text not found -> raises ValueError, nothing staged ---
repo2 = gitfixture.repo_with_commit(files={"doc.md": DOC})
threw = False
try:
    ic.stage_isolated_replacement(repo2, "doc.md", "text that does not exist anywhere", "x")
except ValueError:
    threw = True
check("not-found old_text raises ValueError", threw)
check("nothing staged after a failed replacement",
      git(repo2, "diff", "--cached", "--stat").stdout.strip() == "")

# --- scenario 3: old_text found MORE than once -> raises ValueError (ambiguous) ---
repo3 = gitfixture.repo_with_commit(files={"doc.md": "dup\ndup\n"})
threw = False
try:
    ic.stage_isolated_replacement(repo3, "doc.md", "dup", "unique")
except ValueError:
    threw = True
check("ambiguous (2x) old_text raises ValueError", threw)
check("nothing staged after an ambiguous-match failure",
      git(repo3, "diff", "--cached", "--stat").stdout.strip() == "")

# --- scenario 4: `ref` is genuinely plumbed through, not hardcoded to HEAD ---
repo4 = gitfixture.repo_with_commit(files={"doc.md": DOC})
first_commit = git(repo4, "rev-parse", "HEAD").stdout.strip()
with open(os.path.join(repo4, "doc.md"), "w", encoding="utf-8") as f:
    f.write(DOC.replace("line three", "line THREE (second commit)"))
git(repo4, "add", "-A")
git(repo4, "-c", "user.email=t@t.t", "-c", "user.name=t", "commit", "-qm", "second commit")

content_at_first = ic._show(repo4, first_commit, "doc.md")
content_at_head = ic._show(repo4, "HEAD", "doc.md")
check("_show() reads the FIRST commit's content when given its sha",
      "line three\n" in content_at_first and "THREE (second" not in content_at_first,
      content_at_first)
check("_show() reads HEAD's (different) content when given 'HEAD'",
      "THREE (second commit)" in content_at_head, content_at_head)

# A stale ref whose content has since drifted from the current index must
# fail LOUDLY (RuntimeError from the git-apply --check step below), never
# silently misapply a patch built from outdated context -- that would be
# exactly the "looks right but committed the wrong thing" failure mode this
# whole module exists to prevent.
threw = False
try:
    ic.stage_isolated_replacement(repo4, "doc.md", "old middle line",
                                  "NEW (from a now-stale ref)", ref=first_commit)
except RuntimeError:
    threw = True
check("a stale ref's patch fails loudly instead of silently misapplying", threw)
check("nothing staged after a stale-ref failure",
      git(repo4, "diff", "--cached", "--stat").stdout.strip() == "")

# The SAME replacement, against the CURRENT ref (HEAD, explicitly passed),
# must succeed -- proving `ref` is a real, honored parameter rather than a
# no-op, using the one combination that is actually expected to apply.
ic.stage_isolated_replacement(repo4, "doc.md", "old middle line",
                              "NEW (explicit HEAD ref)", ref="HEAD")
staged4 = git(repo4, "show", ":doc.md").stdout
check("explicit ref='HEAD' works identically to the default", "NEW (explicit HEAD ref)" in staged4, staged4)

# --- regression for independent-review finding C1: calling with `repo_root`
# pointed at a SUBDIRECTORY, not the toplevel, must still stage correctly
# (not silently no-op while reporting success -- `git apply` resolves patch
# paths relative to cwd and drops out-of-tree paths without erroring) ---
repo5 = gitfixture.repo_with_commit(files={"doc.md": DOC, "subdir/placeholder.txt": "x\n"})
subdir = os.path.join(repo5, "subdir")
check("setup: subdir exists", os.path.isdir(subdir))

ic.stage_isolated_replacement(subdir, "doc.md", "old middle line", "NEW (via subdir repo_root)")
staged5 = git(repo5, "show", ":doc.md").stdout
check("C1 regression: staging via a non-toplevel repo_root actually staged "
      "the change (not a silent no-op)",
      "NEW (via subdir repo_root)" in staged5, staged5)

# --- regression for independent-review finding C2: another session's edit
# ALREADY STAGED (via `git add`, not just working-tree-dirty) for the SAME
# file must block the isolated replacement, not silently absorb it ---
repo6 = gitfixture.repo_with_commit(files={"doc.md": DOC})
with open(os.path.join(repo6, "doc.md"), "w", encoding="utf-8") as f:
    f.write(DOC.replace("line one", "line ONE (staged by another session)"))
git(repo6, "add", "-A")
staged_before = git(repo6, "diff", "--cached").stdout
check("setup: the other session's edit is staged before my call",
      staged_before.strip() != "", staged_before)

threw = False
try:
    ic.stage_isolated_replacement(repo6, "doc.md", "old middle line", "NEW (must be refused)")
except RuntimeError:
    threw = True
check("C2 regression: an already-staged collision is refused loudly", threw)
staged_after = git(repo6, "diff", "--cached").stdout
check("C2 regression: the other session's staged content is UNCHANGED by the refusal",
      staged_after == staged_before, staged_after)
check("C2 regression: my replacement text was never merged in",
      "NEW (must be refused)" not in git(repo6, "show", ":doc.md").stdout)

# --- regression for DELTA-review finding C3: another session's edit staged
# on a DIFFERENT path (not the one being isolated) must also block, since
# the documented finish step (`git commit`) would sweep it in regardless of
# which file it touched ---
repo6b = gitfixture.repo_with_commit(files={"doc.md": DOC, "other.md": "untouched\n"})
with open(os.path.join(repo6b, "other.md"), "w", encoding="utf-8") as f:
    f.write("staged by another session, different file entirely\n")
git(repo6b, "add", "-A")
other_staged_before = git(repo6b, "diff", "--cached").stdout
check("setup: other.md is staged before my call (different path than doc.md)",
      "other.md" in git(repo6b, "diff", "--cached", "--name-only").stdout,
      other_staged_before)

threw = False
try:
    ic.stage_isolated_replacement(repo6b, "doc.md", "old middle line", "NEW (must be refused)")
except RuntimeError:
    threw = True
check("C3 regression: a foreign staged file on a DIFFERENT path is refused loudly", threw)
check("C3 regression: other.md's staged content is UNCHANGED by the refusal",
      git(repo6b, "diff", "--cached").stdout == other_staged_before)
check("C3 regression: doc.md was never touched either (index still matches ref)",
      "NEW (must be refused)" not in git(repo6b, "show", ":doc.md").stdout)

# The explicit opt-out must still work for a caller that deliberately owns
# the whole staged set.
ic.stage_isolated_replacement(repo6b, "doc.md", "old middle line",
                              "NEW (explicit opt-out)", allow_other_staged_paths=True)
check("C3 regression: allow_other_staged_paths=True proceeds as intended",
      "NEW (explicit opt-out)" in git(repo6b, "show", ":doc.md").stdout)
check("C3 regression: opting out did not disturb the other staged file",
      "other.md" in git(repo6b, "diff", "--cached", "--name-only").stdout
      and "staged by another session" in git(repo6b, "show", ":other.md").stdout)

# --- regression for FINAL delta review, minor note 1: an older `ref` whose
# content differs from HEAD only in an UNRELATED file must NOT falsely
# trigger the "other path is staged" refusal -- "staged" means index-vs-HEAD,
# not index-vs-ref. Nothing here is actually staged (clean tree, index ==
# HEAD); only history moved. ---
repo9 = gitfixture.repo_with_commit(files={"doc.md": DOC, "other.md": "v1\n"})
first_commit_9 = git(repo9, "rev-parse", "HEAD").stdout.strip()
with open(os.path.join(repo9, "other.md"), "w", encoding="utf-8") as f:
    f.write("v2 -- unrelated history, doc.md untouched\n")
git(repo9, "add", "-A")
git(repo9, "-c", "user.email=t@t.t", "-c", "user.name=t", "commit", "-qm", "unrelated change")
check("setup: tree is clean (nothing actually staged) before my call",
      git(repo9, "status", "--porcelain").stdout.strip() == "")

ic.stage_isolated_replacement(repo9, "doc.md", "old middle line",
                              "NEW (old ref, unrelated history)", ref=first_commit_9)
staged9 = git(repo9, "show", ":doc.md").stdout
check("minor-note-1 regression: an older ref with unrelated intervening "
      "history does NOT falsely refuse", "NEW (old ref, unrelated history)" in staged9,
      staged9)

# --- regression for independent-review finding I1: a CRLF-committed file's
# UNCHANGED lines must keep their CRLF endings, not get silently rewritten
# to LF by the isolate/patch/apply round-trip ---
# NOTE: cannot use gitfixture.repo_with_commit(newline="\r\n") here -- this
# machine has core.autocrlf=true globally, so gitfixture's own `git add`
# (inside _build_template) silently normalizes CRLF -> LF before the commit
# even happens, same as it would for any real caller's `git add`. To get a
# GENUINELY CRLF-committed blob for this test, disable autocrlf on this one
# throwaway repo before adding -- exactly what a repo with a committed
# `.gitattributes` override, or a session on a differently-configured
# machine, would produce for real.
repo7 = gitfixture.blank_repo()
subprocess.run(["git", "-C", repo7, "config", "core.autocrlf", "false"],
               capture_output=True)
with open(os.path.join(repo7, "doc.md"), "wb") as f:
    f.write(DOC.replace("\n", "\r\n").encode("utf-8"))
subprocess.run(["git", "-C", repo7, "add", "-A"], capture_output=True)
subprocess.run(["git", "-C", repo7, "-c", "user.email=t@t.t", "-c", "user.name=t",
               "commit", "-qm", "crlf init"], capture_output=True)

committed_bytes = subprocess.run(["git", "-C", repo7, "show", "HEAD:doc.md"],
                                 capture_output=True).stdout
check("setup: doc.md was actually committed with CRLF", b"\r\n" in committed_bytes,
      committed_bytes)

ic.stage_isolated_replacement(repo7, "doc.md", "old middle line", "NEW middle line")
staged_bytes = subprocess.run(["git", "-C", repo7, "show", ":doc.md"],
                              capture_output=True).stdout
check("I1 regression: staged content still has CRLF on unchanged lines",
      b"line one\r\n" in staged_bytes and b"line three\r\n" in staged_bytes,
      staged_bytes)
check("I1 regression: no bare LF was introduced (no \\r stripped)",
      b"\n" not in staged_bytes.replace(b"\r\n", b""), staged_bytes)


passed = sum(1 for ok, _ in results if ok)
print("\nisolated-commit tests: %d/%d passed" % (passed, len(results)))
sys.exit(0 if passed == len(results) else 1)
