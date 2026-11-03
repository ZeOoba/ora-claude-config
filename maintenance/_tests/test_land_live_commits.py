#!/usr/bin/env python3
"""Tests for land-live-commits.py (plan() gate: NOTHING / READY / BLOCKED_NON_MEMORY).
Real throwaway git repos with a file-path "origin", no mocked git (same convention as
test_checkout_merge_forward.py). land() needs gh and the network, so it is not run here;
plan() is the whole decision.

Run: python _tests/test_land_live_commits.py   (exit 0 = pass)
"""
import importlib.util
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(os.path.dirname(HERE), "land-live-commits.py")
_spec = importlib.util.spec_from_file_location("llc", SCRIPT)
llc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(llc)

_results = []


def check(name, cond, detail=""):
    _results.append((bool(cond), name))
    print(("PASS %s" if cond else "FAIL %s  " + str(detail)) % name)


def git(cwd, *args):
    return subprocess.run(["git", "-C", cwd, *args], check=True, capture_output=True, text=True).stdout.strip()


def fixture():
    root = tempfile.mkdtemp(prefix="llc-")
    origin, live = os.path.join(root, "origin.git"), os.path.join(root, "live")
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", origin], check=True)
    subprocess.run(["git", "clone", "-q", origin, live], check=True, capture_output=True)
    for k, v in (("user.email", "t@t"), ("user.name", "t"), ("core.autocrlf", "false")):
        git(live, "config", k, v)
    os.makedirs(os.path.join(live, llc.MEMORY), exist_ok=True)
    write(live, llc.MEMORY + "event_log.md", "# log\n")
    write(live, "hooks/x.py", "x = 1\n")
    git(live, "add", "-A")
    git(live, "commit", "-q", "-m", "base")
    git(live, "branch", "-M", "main")
    git(live, "push", "-q", "origin", "main")
    git(live, "switch", "-q", "-c", "live/primary-checkout")
    return live


def write(repo, rel, text):
    p = os.path.join(repo, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def use(repo):
    llc.REPO = llc.Path(repo)


def main():
    live = fixture()
    use(live)
    p = llc.plan()
    check("no live-only commits -> NOTHING", p["status"] == "NOTHING", p)

    write(live, llc.MEMORY + "event_log.md", "# log\n## new entry\n")
    git(live, "commit", "-q", "-am", "memory: sweep")
    p = llc.plan()
    check("memory-only commit -> READY", p["status"] == "READY", p)
    check("READY lists the commit", any("memory: sweep" in c for c in p["commits"]), p)

    # main moves on in a non-memory file: must not count against the live branch
    other = tempfile.mkdtemp(prefix="llc-other-")
    subprocess.run(["git", "clone", "-q", git(live, "remote", "get-url", "origin"), other],
                   check=True, capture_output=True)
    for k, v in (("user.email", "t@t"), ("user.name", "t")):
        git(other, "config", k, v)
    write(other, "hooks/x.py", "x = 2\n")
    git(other, "commit", "-q", "-am", "main: hook change")
    git(other, "push", "-q", "origin", "main")
    p = llc.plan()
    check("main-side change is not a live path (three-dot diff)", p["status"] == "READY"
          and "hooks/x.py" not in p["paths"], p)

    write(live, "hooks/x.py", "x = 3\n")
    git(live, "commit", "-q", "-am", "live: unreviewed hook edit")
    p = llc.plan()
    check("non-memory live commit -> BLOCKED_NON_MEMORY", p["status"] == "BLOCKED_NON_MEMORY"
          and p.get("blocked_paths") == ["hooks/x.py"], p)
    p = llc.plan(includes=["hooks/x.py"])
    check("--include-path admits that exact path", p["status"] == "READY", p)
    p = llc.plan(includes=["hooks/x"])
    check("--include-path is not a string prefix", p["status"] == "BLOCKED_NON_MEMORY", p)

    # a rename out of hooks/ into memory/ must still block (the deletion is non-memory)
    live2 = fixture()
    use(live2)
    git(live2, "mv", "hooks/x.py", llc.MEMORY + "x.py")
    git(live2, "commit", "-q", "-m", "sneaky rename")
    p = llc.plan()
    check("rename out of hooks/ -> BLOCKED_NON_MEMORY", p["status"] == "BLOCKED_NON_MEMORY"
          and "hooks/x.py" in p.get("blocked_paths", []), p)

    # squash-merged earlier: content on main, commits not -> ALREADY_LANDED
    live3 = fixture()
    use(live3)
    write(live3, llc.MEMORY + "event_log.md", "# log\n## e1\n")
    git(live3, "commit", "-q", "-am", "memory: sweep 1")
    sq = tempfile.mkdtemp(prefix="llc-sq-")
    subprocess.run(["git", "clone", "-q", git(live3, "remote", "get-url", "origin"), sq],
                   check=True, capture_output=True)
    for k, v in (("user.email", "t@t"), ("user.name", "t")):
        git(sq, "config", k, v)
    write(sq, llc.MEMORY + "event_log.md", "# log\n## e1\n")
    git(sq, "commit", "-q", "-am", "squash of sweep 1")
    git(sq, "push", "-q", "origin", "main")
    p = llc.plan()
    check("squash-landed content -> ALREADY_LANDED", p["status"] == "ALREADY_LANDED", p)

    # someone pushed to the land branch -> BLOCKED_LAND_DIVERGED, never a force-push
    write(live3, llc.MEMORY + "event_log.md", "# log\n## e2\n## e1\n")
    git(live3, "commit", "-q", "-am", "memory: sweep 2")
    git(sq, "switch", "-q", "-c", "tmp")
    write(sq, llc.MEMORY + "other.md", "x\n")
    git(sq, "add", "-A")
    git(sq, "commit", "-q", "-m", "foreign push")
    git(sq, "push", "-q", "origin", "tmp:refs/heads/" + llc.LAND_BRANCH)
    p = llc.plan()
    check("foreign commit on land branch -> BLOCKED_LAND_DIVERGED",
          p["status"] == "BLOCKED_LAND_DIVERGED", p)
    use(live)

    rc = llc.main(["--repo", live, "--dry-run"])
    check("main() exit 3 on BLOCKED_NON_MEMORY", rc == 3, rc)
    rc = llc.main(["--repo", live, "--dry-run", "--include-path", "hooks"])
    check("main() --dry-run READY -> exit 0, nothing pushed", rc == 0
          and not git(live, "ls-remote", "origin", llc.LAND_BRANCH), rc)

    failed = [n for ok, n in _results if not ok]
    print("land-live-commits: %d pass, %d fail" % (len(_results) - len(failed), len(failed)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
