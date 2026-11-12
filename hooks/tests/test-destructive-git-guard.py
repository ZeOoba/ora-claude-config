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


def run(cmd, cwd, via="script", session="dgg-test-session", env=None):
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
                       env=env or dict(os.environ), timeout=60)
    err = r.stderr.decode("utf-8", "replace")
    if via == "dispatcher" and "|mode=inprocess" not in err:
        FAILS.append("dispatcher did not run guard in-process: " + err[-200:])
    return r.returncode, err


def check(name, cmd, cwd, expect_block, vias=("script",), env=None):
    for via in vias:
        rc, err = run(cmd, cwd, via, env=env)
        blocked = rc == 2 and "destructive-git-guard" in err
        if blocked != expect_block:
            FAILS.append("%s [%s]: expected %s, rc=%s err=%s" % (
                name, via, "BLOCK" if expect_block else "ALLOW", rc, err[-300:]))


def claude_home_checks():
    """AUDIT M01 (2026-11-12): ~/.claude is a DEFAULT-DENY repo -- its ignored files are the
    live untracked state (the confidential roster, .credentials.json, session state), not
    build output. `git clean -fdX/-fdx` there must block on ANY ignored path, however it is
    named, and however the repo is addressed (cwd, `cd`, `git -C`)."""
    home = tempfile.mkdtemp(prefix="dgg-home-")
    ch = os.path.join(home, ".claude")
    os.makedirs(os.path.join(ch, "hooks"))
    git(ch, "init", "-q")
    git(ch, "config", "user.email", "t@t")
    git(ch, "config", "user.name", "t")
    git(ch, "config", "core.autocrlf", "false")
    with open(os.path.join(ch, ".gitignore"), "w") as f:
        f.write("/*\n!/.gitignore\n!/hooks/\nhooks/confidential-terms.json\n")
    with open(os.path.join(ch, "hooks", "guard.py"), "w") as f:
        f.write("x = 1\n")
    git(ch, "add", "-A")
    git(ch, "commit", "-qm", "init")
    # Synthetic stand-ins only -- no real roster or credential content.
    with open(os.path.join(ch, "hooks", "confidential-terms.json"), "w") as f:
        f.write('{"_meta": {"purpose": "synthetic fixture"}}\n')
    with open(os.path.join(ch, "session-state.json"), "w") as f:
        f.write("{}\n")
    env = dict(os.environ, USERPROFILE=home, HOME=home)
    fwd = ch.replace("\\", "/")
    try:
        check("claude-home clean -fdX (roster ignored)", "git clean -fdX", ch, True,
              ("script", "dispatcher"), env=env)
        check("claude-home clean -fdx", "git clean -fdx", ch, True, env=env)
        # cwd = the (non-repo) home dir: probing must follow -C / cd, not the session cwd.
        # (Not %TEMP%: the dispatcher's `python -c` puts cwd on sys.path, and a large TEMP
        # makes every import crawl.)
        check("claude-home git -C clean -fdX", "git -C %s clean -fdX" % fwd,
              home, True, ("script", "dispatcher"), env=env)
        check("claude-home cd && clean -fdX", "cd %s && git clean -fdX" % fwd,
              home, True, env=env)
        os.remove(os.path.join(ch, "hooks", "confidential-terms.json"))
        check("claude-home clean -fdX of a non-sensitive ignored file still blocks",
              "git clean -fdX", ch, True, env=env)
        os.remove(os.path.join(ch, "session-state.json"))
        check("claude-home clean -fdX with nothing to remove", "git clean -fdX", ch, False,
              env=env)
    finally:
        shutil.rmtree(home, ignore_errors=True)


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

        # AUDIT M01 (2026-11-12): an ignored file whose NAME is sensitive (.env, credentials,
        # password, confidential-terms.json) is never "just build output" -- in ANY repo.
        os.remove(os.path.join(d, "new.txt"))
        with open(os.path.join(d, ".gitignore"), "w") as f:
            f.write("*.log\n.env\n")
        git(d, "add", ".gitignore")
        git(d, "commit", "-qm", "ignore env")
        with open(os.path.join(d, ".env"), "w") as f:
            f.write("SYNTHETIC=1\n")
        check("clean -fdX ignored .env (sensitive name)", "git clean -fdX", d, True,
              ("script", "dispatcher"))
        check("clean -fdx ignored .env (sensitive name)", "git clean -fdx", d, True)
        os.remove(os.path.join(d, ".env"))
        check("clean -fdX ignored build output still allowed", "git clean -fdX", d, False)
        claude_home_checks()

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
