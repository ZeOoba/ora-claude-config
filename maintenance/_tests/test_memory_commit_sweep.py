#!/usr/bin/env python3
"""Tests for memory-commit-sweep.py -- the memory/ commit-cadence script.

Built alongside the script (not strictly test-first, but every claim below is verified
against a real temp git repo, not asserted from reading the code) to prove: the quiet-
window filter actually excludes fresh writes, deletions/renames are never auto-swept, a
clean tree is a true no-op, and the commit that does land only contains what was intended.

Run: python _tests/test_memory_commit_sweep.py   (exit 0 = pass)
"""
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import time

MAINT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location(
    "mcs", os.path.join(MAINT, "memory-commit-sweep.py"))
mcs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mcs)

results = []


def expect(label, cond, detail=""):
    results.append((bool(cond), label))
    if not cond:
        print("  FAIL: %s %s" % (label, detail))


def sh(cwd, *args):
    r = subprocess.run(["git"] + list(args), cwd=cwd, capture_output=True, text=True)
    return r.stdout, r.returncode


def make_repo():
    d = tempfile.mkdtemp(prefix="mcs_test_")
    sh(d, "init", "-q")
    sh(d, "config", "user.email", "test@example.com")
    sh(d, "config", "user.name", "Test")
    # seed one committed file so HEAD exists
    with open(os.path.join(d, "seed.md"), "w") as f:
        f.write("seed\n")
    sh(d, "add", "seed.md")
    sh(d, "commit", "-q", "-m", "seed")
    return d


def write(d, name, content, backdate_seconds=None):
    p = os.path.join(d, name)
    with open(p, "w") as f:
        f.write(content)
    if backdate_seconds is not None:
        t = time.time() - backdate_seconds
        os.utime(p, (t, t))
    return p


# --- classify(): pure bucketing logic (repo_root == mem_dir in these cases) ----------

now = time.time()
d0 = make_repo()

expect("classify puts a delete-coded entry in review, never settled",
       mcs.classify([("D ", "gone.md")], d0, d0, now, 120)["review"] == ["gone.md"])

expect("classify puts a rename-coded entry in review",
       mcs.classify([("R ", "old.md -> new.md")], d0, d0, now, 120)["review"]
       == ["old.md -> new.md"])

write(d0, "old_enough.md", "x", backdate_seconds=300)
expect("classify settles a path whose mtime is well past the quiet window",
       mcs.classify([("??", "old_enough.md")], d0, d0, now, 120)["settled"]
       == [os.path.join(d0, "old_enough.md")])

write(d0, "fresh.md", "x", backdate_seconds=5)
expect("classify holds back a path whose mtime is inside the quiet window",
       mcs.classify([("??", "fresh.md")], d0, d0, now, 120)["recent"]
       == [os.path.join(d0, "fresh.md")])

shutil.rmtree(d0, ignore_errors=True)

# --- _resolve(): the actual bug this suite exists to catch ---------------------------
# Found live 2026-08-16 running memory-commit-sweep.py against the real ~/.claude repo:
# `git -C <mem_dir> status --porcelain -- .` returns REPO-ROOT-relative paths even with
# cwd=mem_dir (confirmed on git 2.55.0/Windows) -- e.g. "sub/dir/file.md", not
# "file.md". Every fixture above nests memory_dir AT the repo root (make_repo() inits
# git directly in the temp dir), so cwd-relative == root-relative there and this class
# of bug is invisible to them. These cases nest memory_dir one level below repo root,
# replicating the real layout, and assert against BOTH path conventions to prove
# _resolve() doesn't silently depend on which one git happens to emit.

dnest = make_repo()  # repo root
subdir = os.path.join(dnest, "projects", "memory")
os.makedirs(subdir)
write(subdir, "nested.md", "x", backdate_seconds=300)

expect("_resolve finds a file via a repo-root-relative path string",
       mcs._resolve("projects/memory/nested.md", subdir, dnest)
       == os.path.normpath(os.path.join(subdir, "nested.md")))
expect("_resolve finds a file via a cwd(mem_dir)-relative path string",
       mcs._resolve("nested.md", subdir, dnest)
       == os.path.normpath(os.path.join(subdir, "nested.md")))

# real git status call against the nested layout -- proves the resolver survives contact
# with whatever convention THIS git binary actually uses, not just a hand-built string.
out, rc = sh(subdir, "status", "--porcelain", "--untracked-files=all", "--", ".")
entries = mcs._parse_status(out)
expect("nested repo: git status reports the new file at all", len(entries) == 1, out)
buckets = mcs.classify(entries, subdir, dnest, time.time(), 120)
expect("nested repo: classify resolves it to the real absolute path, settled",
       buckets["settled"] == [os.path.normpath(os.path.join(subdir, "nested.md"))],
       buckets)

shutil.rmtree(dnest, ignore_errors=True)

# --- build_message(): pure formatting -------------------------------------------------

d_bm = make_repo()
msg = mcs.build_message("A\tnew_file.md\nM\tchanged_file.md\n", d_bm, d_bm)
expect("build_message lists a new file under 'new:'", "new: new_file.md" in msg, msg)
expect("build_message lists a modified file under 'mod:'", "mod: changed_file.md" in msg, msg)
expect("build_message states counts in the summary line",
       "(1 new, 1 modified)" in msg, msg)
shutil.rmtree(d_bm, ignore_errors=True)

# --- run_sweep(): end-to-end against a real repo --------------------------------------

# 1. clean tree -> true no-op, nothing committed
d1 = make_repo()
r = mcs.run_sweep(mem_dir=d1, quiet_seconds=120)
expect("clean repo: exit 0", r["exit_code"] == 0, r)
expect("clean repo: nothing committed", r["committed"] is False, r)
shutil.rmtree(d1, ignore_errors=True)

# 2. one settled untracked file -> gets committed; staged set matches exactly
d2 = make_repo()
write(d2, "settled_new.md", "content\n", backdate_seconds=300)
r = mcs.run_sweep(mem_dir=d2, quiet_seconds=120)
expect("settled untracked file: committed", r["committed"] is True, r)
expect("settled untracked file: correct file list", r["committed_files"] == ["settled_new.md"], r)
log, rc = sh(d2, "log", "-1", "--format=%s")
expect("commit message carries the sync-checkpoint marker",
       "automated sync checkpoint" in log, log)
status, rc = sh(d2, "status", "--porcelain")
expect("repo is clean after the sweep commits", status.strip() == "", status)
shutil.rmtree(d2, ignore_errors=True)

# 3. one settled + one too-fresh -> only the settled one is committed, fresh one untouched
d3 = make_repo()
write(d3, "settled.md", "a\n", backdate_seconds=300)
write(d3, "toofresh.md", "b\n", backdate_seconds=1)
r = mcs.run_sweep(mem_dir=d3, quiet_seconds=120)
expect("mixed ages: only the settled file is committed", r["committed_files"] == ["settled.md"], r)
expect("mixed ages: the fresh file is reported, not swept", r["skipped_recent"] == ["toofresh.md"], r)
status, rc = sh(d3, "status", "--porcelain")
expect("mixed ages: the fresh file is still dirty on disk after the sweep",
       "toofresh.md" in status, status)
shutil.rmtree(d3, ignore_errors=True)

# 4. a deleted tracked file -> never auto-swept, reported under review, nothing committed
d4 = make_repo()
p = write(d4, "to_delete.md", "x\n", backdate_seconds=300)
sh(d4, "add", "to_delete.md")
sh(d4, "commit", "-q", "-m", "add to_delete")
os.remove(p)
r = mcs.run_sweep(mem_dir=d4, quiet_seconds=120)
expect("deletion: nothing committed", r["committed"] is False, r)
expect("deletion: surfaced under skipped_review", r["skipped_review"] == ["to_delete.md"], r)
shutil.rmtree(d4, ignore_errors=True)

# 5. index.lock present -> sweep skips the whole cycle, exit 1, nothing touched
d5 = make_repo()
write(d5, "would_be_settled.md", "x\n", backdate_seconds=300)
open(os.path.join(d5, ".git", "index.lock"), "w").close()
r = mcs.run_sweep(mem_dir=d5, quiet_seconds=120)
expect("index.lock present: exit 1", r["exit_code"] == 1, r)
expect("index.lock present: nothing committed", r["committed"] is False, r)
os.remove(os.path.join(d5, ".git", "index.lock"))
status, rc = sh(d5, "status", "--porcelain")
expect("index.lock present: the pending file is still untouched/dirty",
       "would_be_settled.md" in status, status)
shutil.rmtree(d5, ignore_errors=True)

# 6. not a git repo at all -> exit 2, no exception
d6 = tempfile.mkdtemp(prefix="mcs_test_notgit_")
r = mcs.run_sweep(mem_dir=d6, quiet_seconds=120)
expect("non-repo dir: exit 2", r["exit_code"] == 2, r)
shutil.rmtree(d6, ignore_errors=True)

# 7. modified TRACKED file (not just untracked) also gets swept once settled
d7 = make_repo()
write(d7, "seed.md", "changed content\n", backdate_seconds=300)
r = mcs.run_sweep(mem_dir=d7, quiet_seconds=120)
expect("modified tracked file: committed", r["committed_files"] == ["seed.md"], r)
shutil.rmtree(d7, ignore_errors=True)

passed = sum(1 for ok, _ in results if ok)
print("memory-commit-sweep tests: %d/%d passed" % (passed, len(results)))
sys.exit(0 if passed == len(results) else 1)
