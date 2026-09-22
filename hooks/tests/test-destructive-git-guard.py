"""Standalone test for hooks/destructive-git-guard.py.

WHAT IT ENFORCES (2026-09-22, /insights remediation): a Bash command that would
DISCARD uncommitted work -- `git checkout -- <p>`, `git checkout .`, `checkout -f`,
`git restore <p>` (worktree), `git switch -f/--discard-changes`, `git reset --hard`,
`git clean -f` -- is BLOCKED when it would actually lose something. A stray
`git checkout --` silently reverted reviewed correctness fixes in a live session.

Every check drives BOTH the script and the dispatcher's in-process path (the C1 lesson
from test-worktree-isolation-guard.py: a guard that `return`s 2 instead of
sys.exit(2) prints BLOCKED and allows).
"""
import json, os, subprocess, sys, tempfile, shutil

for _v in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR",
           "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_PREFIX"):
    os.environ.pop(_v, None)

HOOKS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GUARD = os.path.join(HOOKS, "destructive-git-guard.py")
DISPATCHER = os.path.join(HOOKS, "pretooluse-dispatcher.py")
PY = sys.executable
FAILS = []


def git(repo, *a):
    subprocess.run(("git",) + a, cwd=repo, check=True, capture_output=True)


def make_repo():
    d = tempfile.mkdtemp(prefix="dgg-")
    git(d, "init", "-q")
    git(d, "config", "user.email", "t@t")
    git(d, "config", "user.name", "t")
    git(d, "config", "core.autocrlf", "false")
    for n in ("a.txt", "b.txt"):
        with open(os.path.join(d, n), "w") as f:
            f.write("v1\n")
    git(d, "add", "-A")
    git(d, "commit", "-qm", "init")
    return d


def dirty(d, name="a.txt"):
    with open(os.path.join(d, name), "w") as f:
        f.write("v2\n")


def untracked(d, name="new.txt"):
    with open(os.path.join(d, name), "w") as f:
        f.write("x\n")


def run(cmd, cwd, via="script", session="dgg-test-session"):
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd},
                          "cwd": cwd, "session_id": session})
    if via == "script":
        argv = [PY, GUARD]
    else:
        # The dispatcher's IN-PROCESS path for this one guard -- the path on which a
        # `return 2` (instead of sys.exit(2)) is silently discarded.
        argv = [PY, "-c", (
            "import sys, importlib.util as u; s=u.spec_from_file_location('d', %r); "
            "m=u.module_from_spec(s); s.loader.exec_module(m); "
            "rc,o,e,mode=m.run_guard('destructive-git-guard', sys.stdin.buffer.read()); "
            "sys.stderr.write(e+'|mode='+mode); sys.exit(rc)") % DISPATCHER]
    r = subprocess.run(argv, input=payload.encode(), capture_output=True, cwd=cwd,
                       env=dict(os.environ), timeout=60)
    err = r.stderr.decode("utf-8", "replace")
    if via == "dispatcher" and "|mode=inprocess" not in err:
        FAILS.append("dispatcher did not run guard in-process: " + err[-200:])
    return r.returncode, err


def check(name, cmd, cwd, expect_block, vias=("script",)):
    for via in vias:
        rc, err = run(cmd, cwd, via)
        blocked = rc == 2 and "destructive-git-guard" in err
        if blocked != expect_block:
            FAILS.append("%s [%s]: expected %s, rc=%s err=%s" % (
                name, via, "BLOCK" if expect_block else "ALLOW", rc, err[-300:]))


def main():
    d = make_repo()
    try:
        # --- clean tree: nothing to lose -> ALLOW everything
        check("clean checkout --", "git checkout -- a.txt", d, False)
        check("clean reset --hard", "git reset --hard", d, False)
        check("clean clean -fd", "git clean -fd", d, False)

        dirty(d)
        # --- dirty tracked file
        check("checkout -- dirty", "git checkout -- a.txt", d, True, ("script", "dispatcher"))
        check("checkout -- other clean path", "git checkout -- b.txt", d, False)
        check("checkout .", "git checkout .", d, True)
        check("checkout HEAD -- p", "git checkout HEAD -- a.txt", d, True)
        check("checkout -f", "git checkout -f main", d, True)
        check("restore worktree", "git restore a.txt", d, True)
        check("restore --staged only", "git restore --staged a.txt", d, False)
        check("restore clean path", "git restore b.txt", d, False)
        check("switch --discard-changes", "git switch --discard-changes main", d, True)
        check("reset --hard", "git reset --hard", d, True, ("script", "dispatcher"))
        check("reset --soft", "git reset --soft HEAD", d, False)
        check("chained after cd", "cd %s && git reset --hard HEAD" % d.replace("\\", "/"),
              tempfile.gettempdir(), True)
        check("git -C", "git -C %s checkout -- a.txt" % d.replace("\\", "/"),
              tempfile.gettempdir(), True)
        check("newline segment", "git status\ngit checkout -- a.txt", d, True)
        # --- non-destructive / look-alikes
        check("plain branch switch", "git checkout -b feat/x", d, False)
        check("echo mention", "echo 'git reset --hard'", d, False)
        check("status", "git status --short", d, False)
        check("stash push (keeps work)", "git stash push -m t -- a.txt", d, False)

        # --- REFUTE regressions (2026-09-22)
        # HIGH: an unresolvable/msys/~ cd must NOT fall back to probing the old cwd.
        check("cd msys path, dirty cwd", "cd /c/Windows && git reset --hard", d, False)
        check("cd ~ nonexistent", "cd ~/definitely-not-here-xyz && git checkout -- a.txt", d, False)
        msys = "/" + d[0].lower() + d[2:].replace("\\", "/")
        check("cd msys INTO dirty repo", "cd %s && git reset --hard" % msys,
              tempfile.gettempdir(), True)
        check("git -C msys path", "git -C %s checkout -- a.txt" % msys, tempfile.gettempdir(), True)
        # MED: checkout <file> / checkout <treeish> <file> without `--`
        check("checkout <file>", "git checkout a.txt", d, True)
        check("checkout HEAD <file>", "git checkout HEAD a.txt", d, True)
        check("checkout clean <file>", "git checkout b.txt", d, False)

        git(d, "checkout", "--", "a.txt")
        # MED: staged-only change -- index->worktree restore loses nothing
        dirty(d)
        git(d, "add", "a.txt")
        check("staged-only restore", "git restore a.txt", d, False)
        check("staged-only checkout --", "git checkout -- a.txt", d, False)
        check("staged-only checkout HEAD --", "git checkout HEAD -- a.txt", d, True)
        check("staged-only reset --hard", "git reset --hard", d, True)
        git(d, "reset", "-q", "--hard")

        untracked(d)
        # --- untracked only: reset --hard keeps untracked files; clean -f deletes them
        check("reset --hard w/ only untracked", "git reset --hard", d, False)
        check("clean -f untracked", "git clean -f", d, True)
        check("clean -fd untracked", "git clean -fd", d, True)
        check("clean -n dry run", "git clean -n", d, False)
        # REVIEW MED-2: ignored build artifacts are not uncommitted work.
        os.remove(os.path.join(d, "new.txt"))
        with open(os.path.join(d, ".gitignore"), "w") as f:
            f.write("*.log\n")
        git(d, "add", ".gitignore")
        git(d, "commit", "-qm", "ignore")
        with open(os.path.join(d, "build.log"), "w") as f:
            f.write("x\n")
        check("clean -fdX ignored only", "git clean -fdX", d, False)
        check("clean -fdx ignored only", "git clean -fdx", d, False)
        untracked(d)
        check("clean -fdx ignored + untracked", "git clean -fdx", d, True)

        # --- override token (60 min, multi-use) lets it through
        tokdir = tempfile.mkdtemp(prefix="dgg-sess-")
        os.environ["ORA_OVERRIDE_SESSIONS_DIR"] = tokdir
        od = os.path.join(tokdir, "dgg-test-session", "overrides")
        os.makedirs(od)
        with open(os.path.join(od, "allow-destructive-git"), "w") as f:
            f.write("scope: destructive-git\nsession: dgg-test-session\nreason: test\n")
        check("override grants", "git clean -f", d, False)
        os.environ.pop("ORA_OVERRIDE_SESSIONS_DIR", None)
        shutil.rmtree(tokdir, ignore_errors=True)

        # --- not a repo: no information -> ALLOW
        nd = tempfile.mkdtemp(prefix="dgg-norepo-")
        check("non-repo", "git reset --hard", nd, False)
        shutil.rmtree(nd, ignore_errors=True)
    finally:
        shutil.rmtree(d, ignore_errors=True)

    if FAILS:
        print("FAIL (%d):" % len(FAILS))
        for f in FAILS:
            print("  - " + f)
        sys.exit(1)
    print("destructive-git-guard: all checks passed")


if __name__ == "__main__":
    main()
