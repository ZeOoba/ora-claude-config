#!/usr/bin/env python3
"""Invariants for hooks/tests/lib/gitfixture.py (open-items-tracker.md#OI-061).

This fixture is depended on by security-gate test files, so a silent difference between
a copied repo and a freshly-inited one would let those suites pass while no longer
exercising what they claim. Every property they rely on is asserted here explicitly,
including the one that is the whole point: spawn count must NOT scale with call count.
"""
import os
import subprocess
import sys

# Strip git's leaked hook environment BEFORE any fixture call. Same scrub the two
# converted suites carry, and it is load-bearing here for the same reason: gitfixture's
# `git init` inherits os.environ, so running this file by hand from a shell where
# GIT_DIR/GIT_WORK_TREE point at a real repo would re-init THAT repo, overwrite its
# user.email/user.name to the fixture's t@t.t/t, and `git add -A && git commit` pending
# work under a bogus identity. The pre-push runner scrubs these at spawn time, so the
# automated path was never exposed -- a manual run was.
for _v in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR",
           "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_PREFIX"):
    os.environ.pop(_v, None)

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"))
import gitfixture  # noqa: E402

FAILS = []


def check(name, cond, detail=""):
    if cond:
        print("PASS %s" % name)
    else:
        FAILS.append(name)
        print("FAIL %s  %s" % (name, detail))


def git_out(repo, *args):
    r = subprocess.run(["git", "-C", repo] + list(args), capture_output=True, text=True)
    return r.returncode, (r.stdout or "").strip()


# --- repo_with_commit: shape correctness -----------------------------------
r1 = gitfixture.repo_with_commit()
check("repo_with_commit: .git exists", os.path.isdir(os.path.join(r1, ".git")))
rc, out = git_out(r1, "rev-list", "--count", "HEAD")
check("repo_with_commit: exactly one commit", rc == 0 and out == "1", "rc=%s out=%r" % (rc, out))
rc, out = git_out(r1, "config", "user.email")
check("repo_with_commit: user.email set", out == "t@t.t", "got %r" % out)
rc, out = git_out(r1, "config", "user.name")
check("repo_with_commit: user.name set", out == "t", "got %r" % out)
check("repo_with_commit: README.md present", os.path.isfile(os.path.join(r1, "README.md")))
with open(os.path.join(r1, "README.md"), encoding="utf-8") as fh:
    check("repo_with_commit: README content", fh.read() == "hello\n")
rc, out = git_out(r1, "status", "--porcelain")
check("repo_with_commit: clean tree", rc == 0 and out == "", "got %r" % out)

# --- a copied repo is a WORKING repo, not just a directory -----------------
with open(os.path.join(r1, "new.txt"), "w", encoding="utf-8") as fh:
    fh.write("x\n")
rc, _ = git_out(r1, "add", "-A")
rc2, _ = git_out(r1, "commit", "-q", "-m", "second")
rc3, out = git_out(r1, "rev-list", "--count", "HEAD")
check("copied repo accepts add+commit", rc == 0 and rc2 == 0 and out == "2", "count=%r" % out)

# --- independence: copies must not share state -----------------------------
r2 = gitfixture.repo_with_commit()
rc, out = git_out(r2, "rev-list", "--count", "HEAD")
check("second repo unaffected by first's commit", out == "1", "count=%r" % out)
check("second repo is a distinct path", os.path.abspath(r1) != os.path.abspath(r2))
check("second repo has no new.txt", not os.path.isfile(os.path.join(r2, "new.txt")))

# --- blank_repo ------------------------------------------------------------
b = gitfixture.blank_repo()
check("blank_repo: .git exists", os.path.isdir(os.path.join(b, ".git")))
rc, out = git_out(b, "rev-list", "--count", "HEAD")
check("blank_repo: zero commits", rc != 0 or out == "0", "rc=%s out=%r" % (rc, out))
rc, out = git_out(b, "config", "user.name")
check("blank_repo: user.name set", out == "t", "got %r" % out)

# --- custom shape gets its own template ------------------------------------
c = gitfixture.repo_with_commit(files={"a.txt": "A\n", "sub/b.txt": "B\n"}, message="custom")
check("custom shape: nested file committed", os.path.isfile(os.path.join(c, "sub", "b.txt")))
rc, out = git_out(c, "log", "-1", "--format=%s")
check("custom shape: commit message honoured", out == "custom", "got %r" % out)
rc, out = git_out(c, "status", "--porcelain")
check("custom shape: clean tree", out == "", "got %r" % out)

# --- newline fidelity: must reproduce the caller's original bytes ----------
lf = gitfixture.repo_with_commit(files={"n.txt": "a\nb\n"}, message="lf", newline="\n")
with open(os.path.join(lf, "n.txt"), "rb") as fh:
    check("newline='\\n' writes literal LF", fh.read() == b"a\nb\n")
crlf = gitfixture.repo_with_commit(files={"n.txt": "a\nb\n"}, message="crlf", newline=None)
with open(os.path.join(crlf, "n.txt"), "rb") as fh:
    raw = fh.read()
check("newline=None applies platform translation",
      raw == (b"a\r\nb\r\n" if os.linesep == "\r\n" else b"a\nb\n"), "got %r" % raw)
check("newline variants are NOT the same cached template",
      os.path.abspath(lf) != os.path.abspath(crlf))

# --- THE POINT: spawns must not scale with call count ----------------------
gitfixture.reset_cache()
before = gitfixture.spawn_count()
first = gitfixture.repo_with_commit(prefix="scale-a-")
after_first = gitfixture.spawn_count()
built = after_first - before
check("first call builds the template", built >= 4, "spawns=%d" % built)
for _ in range(20):
    gitfixture.repo_with_commit(prefix="scale-b-")
after_twenty = gitfixture.spawn_count()
check("20 further calls spawn NOTHING",
      after_twenty == after_first,
      "expected %d, got %d" % (after_first, after_twenty))
check("21 repos cost fewer spawns than 21x5 hand-rolled",
      (after_twenty - before) < 21 * 5,
      "spawns=%d" % (after_twenty - before))

print()
if FAILS:
    print("FAILED (%d): %s" % (len(FAILS), ", ".join(FAILS)))
    sys.exit(1)
print("ALL GITFIXTURE TESTS PASS")
