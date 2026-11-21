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


def memory_checkout_checks():
    """PR 476 (2026-11-20): memory is local-only in claude-home but every older commit
    still TRACKS it. Moving the live checkout onto such a commit overwrites the ignored
    local memory (git treats ignored files as expendable) and leaving it deletes them --
    nothing is "dirty", so only a tree check can see it. Synthetic fixture only."""
    home = tempfile.mkdtemp(prefix="dgg-mem-")
    ch = os.path.join(home, ".claude")
    mem_rel = "projects/C--Users-Owner-OneDrive---Oxford-Capital-Partners/memory"
    mem = os.path.join(ch, *mem_rel.split("/"))
    os.makedirs(mem)
    git(ch, "init", "-q", "-b", "main")
    git(ch, "config", "user.email", "t@t")
    git(ch, "config", "user.name", "t")
    git(ch, "config", "core.autocrlf", "false")
    with open(os.path.join(mem, "note.md"), "w") as f:
        f.write("old\n")
    with open(os.path.join(ch, "README"), "w") as f:
        f.write("r\n")
    git(ch, "add", "-A")
    git(ch, "commit", "-qm", "tracks memory")
    git(ch, "branch", "old")
    git(ch, "rm", "-q", "--cached", "-r", mem_rel)
    with open(os.path.join(ch, ".gitignore"), "w") as f:
        f.write("/%s/**\n" % mem_rel)
    git(ch, "add", ".gitignore")
    git(ch, "commit", "-qm", "untrack memory")
    git(ch, "branch", "new")
    # `stale`: a pre-untrack branch that EDITS memory (merge/pull/cherry-pick write it in).
    git(ch, "checkout", "-q", "-b", "stale", "old")
    with open(os.path.join(mem, "note.md"), "w") as f:
        f.write("stale edit\n")
    git(ch, "commit", "-qam", "stale memory edit")
    # `side`: a pre-untrack branch that changes only README (merging it writes no memory).
    git(ch, "checkout", "-q", "-b", "side", "old")
    with open(os.path.join(ch, "README"), "w") as f:
        f.write("side\n")
    git(ch, "commit", "-qam", "side readme")
    # OI-409 fixtures. `mrg`: a merge commit whose first-parent diff edits memory.
    git(ch, "checkout", "-q", "-b", "mrg", "side")
    git(ch, "merge", "-q", "--no-ff", "--no-edit", "stale")
    # `er`: a range whose net diff is zero -- an edit to memory, then its revert.
    git(ch, "checkout", "-q", "-b", "er", "old")
    with open(os.path.join(mem, "note.md"), "w") as f:
        f.write("er edit\n")
    git(ch, "commit", "-qam", "er memory edit")
    git(ch, "revert", "--no-edit", "HEAD")
    # `er2`: `er` plus a README-only tip, so `cherry-pick ^old er2` writes memory only
    # through the walk (the tip alone does not).
    git(ch, "checkout", "-q", "-b", "er2", "er")
    with open(os.path.join(ch, "README"), "w") as f:
        f.write("er2\n")
    git(ch, "commit", "-qam", "er2 readme")
    # `del`: a pre-untrack branch that only DELETES memory (merging it writes nothing).
    git(ch, "checkout", "-q", "-b", "del", "old")
    git(ch, "rm", "-q", "--cached", "-r", mem_rel)
    git(ch, "commit", "-qm", "delete memory")
    git(ch, "tag", "tstale", "stale")
    git(ch, "tag", "tside", "side")
    git(ch, "checkout", "-q", "-f", "main")
    git(ch, "branch", "tmp", "side")  # an EXISTING ref a later fetch re-points
    # `self`: a LOCAL remote (any old history). `gh`: a network remote; its tracking refs
    # are set by hand (no fetch ever reaches it). R1-01: `oldfeat` exists only remotely.
    git(ch, "remote", "add", "self", ch)
    git(ch, "fetch", "-q", "self")
    git(ch, "remote", "add", "gh", "https://example.invalid/ora.git")
    for b in ("stale", "side", "oldfeat", "new"):
        git(ch, "update-ref", "refs/remotes/gh/" + b, "old" if b == "oldfeat" else b)
    os.makedirs(os.path.join(ch, "docs"))  # a subdirectory that holds no memory
    # `loc`: a second LOCAL remote whose `lfeat` (at old) has never been fetched here.
    loc = os.path.join(home, "loc.git")
    git(home, "clone", "-q", "--bare", ch, loc)
    git(loc, "branch", "lfeat", "old")
    git(ch, "remote", "add", "loc", loc)
    # Leave @{-1} = old for the `checkout -` / `switch -` cases, then restore local memory
    # (switching away from a memory-tracking commit deletes it -- the hazard itself).
    git(ch, "checkout", "-q", "old")
    git(ch, "checkout", "-q", "main")
    os.makedirs(mem, exist_ok=True)
    with open(os.path.join(mem, "note.md"), "w") as f:
        f.write("local only\n")
    git(ch, "config", "branch.main.remote", ".")
    git(ch, "config", "branch.main.merge", "refs/heads/stale")  # @{u} = stale
    env = dict(os.environ, USERPROFILE=home, HOME=home)
    try:
        both = ("script", "dispatcher")
        # Round-6 findings: every command that writes an old tree, path or diff into the
        # worktree, not only checkout/switch/reset.
        check("memory: checkout - (previous branch)", "git checkout -", ch, True, both, env)
        check("memory: switch - (previous branch)", "git switch -", ch, True, env=env)
        check("memory: checkout old -- . (paths)", "git checkout old -- .", ch, True, env=env)
        check("memory: checkout old -- projects", "git checkout old -- projects", ch, True,
              env=env)
        check("memory: restore --source=old -- .", "git restore --source=old -- .", ch, True,
              both, env)
        check("memory: restore -s old -W projects", "git restore -s old -W projects", ch,
              True, env=env)
        check("memory: merge stale (edits memory)", "git merge stale", ch, True, both, env)
        check("memory: pull (upstream edits memory)", "git pull", ch, True, env=env)
        check("memory: pull . stale (local branch)", "git pull . stale", ch, True, env=env)
        check("memory: pull --rebase . stale", "git pull --rebase . stale", ch, True, env=env)
        check("memory: rebase stale", "git rebase stale", ch, True, env=env)
        check("memory: rebase --onto old new", "git rebase --onto old new", ch, True, env=env)
        check("memory: cherry-pick stale", "git cherry-pick stale", ch, True, env=env)
        check("memory: cherry-pick range", "git cherry-pick old..stale", ch, True, env=env)
        check("memory: revert the untrack commit", "git revert new", ch, True, env=env)
        check("memory: read-tree -u --reset old", "git read-tree -u --reset old", ch, True,
              env=env)
        # ALLOW: forms that write no memory.
        check("memory: checkout old README (path, no --)", "git checkout old README", ch,
              False, env=env)
        check("memory: restore --source=old README", "git restore --source=old README", ch,
              False, env=env)
        check("memory: restore --staged --source=old .", "git restore --staged --source=old .",
              ch, False, env=env)
        check("memory: merge side (no memory change)", "git merge side", ch, False, env=env)
        check("memory: merge --abort", "git merge --abort", ch, False, env=env)
        check("memory: cherry-pick side", "git cherry-pick side", ch, False, env=env)
        check("memory: read-tree without -u", "git read-tree old", ch, False, env=env)
        both = ("script", "dispatcher")
        check("memory: checkout old branch", "git checkout old", ch, True, both, env)
        check("memory: checkout old sha", "git checkout HEAD~1", ch, True, env=env)
        check("memory: switch old", "git switch old", ch, True, both, env)
        check("memory: switch --detach old", "git switch --detach old", ch, True, env=env)
        check("memory: reset --hard old", "git reset --hard HEAD~1", ch, True, env=env)
        check("memory: reset --keep old", "git reset --keep old", ch, True, env=env)
        check("memory: checkout -b x old", "git checkout -b x old", ch, True, env=env)
        check("memory: git -C from elsewhere", "git -C %s checkout old"
              % ch.replace("\\", "/"), home, True, env=env)
        # ALLOW: targets that do not track memory, index-only resets, path checkouts.
        check("memory: checkout new branch", "git checkout new", ch, False, both, env)
        check("memory: switch -c fresh (from HEAD)", "git switch -c fresh", ch, False, env=env)
        check("memory: reset --soft old (index/HEAD only)", "git reset --soft HEAD~1", ch,
              False, env=env)
        check("memory: checkout old -- README (paths only)", "git checkout old -- README",
              ch, False, env=env)
        check("memory: log old (not a move)", "git log -1 old", ch, False, env=env)
        oi409_checks(ch, home, env)
        # No local memory folder -> nothing to protect -> ALLOW.
        shutil.rmtree(os.path.join(ch, "projects"))
        check("memory: no local memory -> allow", "git checkout old", ch, False, env=env)
        # Not claude-home: an ordinary repo with the same layout is not protected.
        os.makedirs(mem)
        other_env = dict(os.environ, USERPROFILE=tempfile.gettempdir(),
                         HOME=tempfile.gettempdir())
        check("memory: not claude-home -> allow", "git checkout old", ch, False,
              env=other_env)
    finally:
        shutil.rmtree(home, ignore_errors=True)


def oi409_checks(ch, home, env):
    """OI-409 (PR 476 merge gate round 7): the forms the first memory check missed."""
    both = ("script", "dispatcher")
    # Short-flag clusters hiding an option value.
    check("oi409: checkout -qb x old", "git checkout -qb x old", ch, True, both, env)
    check("oi409: restore -qs old -- .", "git restore -qs old -- .", ch, True, env=env)
    check("oi409: restore -Ws old projects", "git restore -Ws old projects", ch, True, env=env)
    check("oi409: restore -qWsold projects", "git restore -qWsold projects", ch, True, env=env)
    # Glob / magic pathspecs (ls-tree matched literal prefixes only).
    check("oi409: checkout old -- '*.md'", "git checkout old -- '*.md'", ch, True, both, env)
    check("oi409: checkout old -- ':(glob)**'", "git checkout old -- ':(glob)**'", ch, True,
          env=env)
    check("oi409: checkout old '*.md' (no --)", "git checkout old '*.md'", ch, True, env=env)
    check("oi409: restore --source=old ':/projects' (top magic)", "git restore --source=old ':/projects'",
          ch, True, env=env)
    check("oi409: checkout old -- '*.txt' (no memory match)", "git checkout old -- '*.txt'",
          ch, False, env=env)
    # From a subdirectory, a relative pathspec only covers that subdirectory.
    sub = os.path.join(ch, "projects")
    check("oi409: subdir checkout old -- . (covers memory)", "git checkout old -- .", sub,
          True, env=env)
    check("oi409: subdir with no memory: checkout old -- . (pathspec is cwd-relative)",
          "git checkout old -- .", os.path.join(ch, "docs"), False, env=env)
    check("oi409: restore --pathspec-from-file --source=old",
          "git restore --pathspec-from-file=list.txt --source=old", ch, True, env=env)
    # cherry-pick / revert of a merge commit with -m N, and X^! single-commit ranges.
    check("oi409: cherry-pick -m 1 mrg", "git cherry-pick -m 1 mrg", ch, True, both, env)
    check("oi409: cherry-pick -m1 mrg", "git cherry-pick -m1 mrg", ch, True, env=env)
    check("oi409: revert -m 1 mrg", "git revert -m 1 mrg", ch, True, env=env)
    check("oi409: cherry-pick stale^!", "git cherry-pick stale^!", ch, True, env=env)
    check("oi409: cherry-pick stale ^old", "git cherry-pick stale ^old", ch, True, env=env)
    check("oi409: cherry-pick ^old er2 (memory only inside the walk)",
          "git cherry-pick ^old er2", ch, True, env=env)
    check("oi409: cherry-pick er2 alone (README-only tip)", "git cherry-pick er2", ch, False,
          env=env)
    # `side` carries no memory of its own: only the walk over side..er2 reaches the edit.
    check("oi409: cherry-pick ^side er2 (walk is the only path to memory)",
          "git cherry-pick ^side er2", ch, True, env=env)
    check("oi409: cherry-pick side^!", "git cherry-pick side^!", ch, False, env=env)
    # A range whose net diff is zero still writes memory commit by commit.
    check("oi409: cherry-pick old..er (edit + revert)", "git cherry-pick old..er", ch, True,
          env=env)
    # Bare merge / rebase act on @{u} (= stale here).
    check("oi409: bare merge (@{u})", "git merge", ch, True, both, env)
    check("oi409: bare rebase (@{u})", "git rebase", ch, True, env=env)
    check("oi409: bare merge --ff-only (@{u})", "git merge --ff-only", ch, True, env=env)
    # pull.rebase / branch.<b>.rebase config turns a pull into a rebase. `side` is not an
    # ancestor of HEAD: merging it writes no memory, rebasing onto it checks out its tree.
    check("oi409: pull . side (merge: no memory)", "git pull . side", ch, False, env=env)
    git(ch, "config", "pull.rebase", "true")
    check("oi409: pull . side with pull.rebase=true", "git pull . side", ch, True, env=env)
    check("oi409: pull --no-rebase . side overrides config", "git pull --no-rebase . side", ch,
          False, env=env)
    check("oi409: pull --rebase=false . side", "git pull --rebase=false . side", ch, False,
          env=env)
    git(ch, "config", "pull.rebase", "false")
    git(ch, "config", "branch.main.rebase", "true")
    check("oi409: pull . side with branch.main.rebase=true", "git pull . side", ch, True,
          env=env)
    git(ch, "config", "--unset", "branch.main.rebase")
    git(ch, "config", "--unset", "pull.rebase")
    # R1-03: config given on the command line or through the environment.
    check("oi409: git -c pull.rebase=true pull . side", "git -c pull.rebase=true pull . side",
          ch, True, both, env)
    check("oi409: git -c pull.rebase pull . side (valueless = true)",
          "git -c pull.rebase pull . side", ch, True, env=env)
    check("oi409: git -c pull.rebase=false pull . side", "git -c pull.rebase=false pull . side",
          ch, False, env=env)
    check("oi409: GIT_CONFIG_PARAMETERS pull . side (unknown config: assume rebase)",
          "GIT_CONFIG_PARAMETERS=\"'pull.rebase=true'\" git pull . side", ch, True, env=env)
    # R1-06: no-op forms write nothing.
    # R2-09: rebasing onto an ancestor of HEAD is usually a no-op but is NOT exempted: HEAD
    # can move between the hook and the command, and options can force a real rebase.
    check("oi409: pull --rebase . old (ancestor: still checked)", "git pull --rebase . old", ch,
          True, env=env)
    check("oi409: rebase old (ancestor: still checked)", "git rebase old", ch, True, env=env)
    check("oi409: rebase -i old (not a no-op)", "git rebase -i old", ch, True, env=env)
    check("oi409: rebase -q old (ancestor: still checked)", "git rebase -q old", ch, True,
          env=env)
    check("oi409: rebase --signoff old (forces a rebase)", "git rebase --signoff old", ch,
          True, env=env)
    check("oi409: rebase --whitespace=fix old", "git rebase --whitespace=fix old", ch, True,
          env=env)
    check("oi409: rebase --ignore-date old", "git rebase --ignore-date old", ch, True, env=env)
    check("oi409: pull --rebase --signoff . old", "git pull --rebase --signoff . old", ch,
          True, env=env)
    check("oi409: rebase --force-rebase old", "git rebase --force-rebase old", ch, True,
          env=env)
    check("oi409: pull --rebase=interactive . old", "git pull --rebase=interactive . old", ch,
          True, env=env)
    check("oi409: merge -s ours stale (keeps HEAD tree)", "git merge -s ours stale", ch, False,
          env=env)
    check("oi409: merge --strategy=ours stale", "git merge --strategy=ours stale", ch, False,
          env=env)
    check("oi409: merge -X ours stale (still merges memory)", "git merge -X ours stale", ch,
          True, env=env)
    check("oi409: merge -s recursive -s ours stale (not only ours)",
          "git merge -s recursive -s ours stale", ch, True, env=env)
    check("oi409: merge -s ours -s ours stale", "git merge -s ours -s ours stale", ch, False,
          env=env)
    # refs/heads/, refs/tags/ and `tag` pull specs, on a NETWORK remote (judged by its
    # remote-tracking ref before the fetch). `tside`/`side` carry no memory: an ALLOW
    # proves the spec was stripped to a real ref rather than blocked as unresolvable.
    check("oi409: pull gh refs/heads/stale", "git pull gh refs/heads/stale", ch, True, env=env)
    check("oi409: pull gh refs/heads/side", "git pull gh refs/heads/side", ch, False, env=env)
    check("oi409: pull gh +refs/heads/stale:refs/remotes/gh/stale",
          "git pull gh +refs/heads/stale:refs/remotes/gh/stale", ch, True, env=env)
    check("oi409: pull . refs/tags/tstale", "git pull . refs/tags/tstale", ch, True, env=env)
    check("oi409: pull gh refs/tags/tside", "git pull gh refs/tags/tside", ch, False, env=env)
    check("oi409: pull gh tag tside", "git pull gh tag tside", ch, False, env=env)
    check("oi409: pull gh tag tstale", "git pull gh tag tstale", ch, True, env=env)
    check("oi409: pull gh unfetched branch", "git pull gh nosuch", ch, True, env=env)
    # R1-02: a LOCAL remote can serve any old branch -- its pulls are unknowable.
    check("oi409: pull self refs/heads/side (local remote)", "git pull self refs/heads/side",
          ch, True, env=env)
    check("oi409: pull path remote", "git pull ../elsewhere main", ch, True, env=env)
    # Upstream on a remote: bare pull follows its locality.
    git(ch, "config", "branch.main.remote", "gh")
    git(ch, "config", "branch.main.merge", "refs/heads/side")
    check("oi409: bare pull, upstream gh/side", "git pull", ch, False, env=env)
    check("oi409: fetch gh && merge --ff-only FETCH_HEAD (= @{u})",
          "git fetch gh && git merge --ff-only FETCH_HEAD", ch, False, env=env)
    git(ch, "config", "branch.main.remote", "self")
    check("oi409: bare pull, upstream on local remote", "git pull", ch, True, env=env)
    check("oi409: fetch && bare merge, upstream on local remote", "git fetch && git merge", ch,
          True, env=env)
    git(ch, "config", "branch.main.remote", ".")
    git(ch, "config", "branch.main.merge", "refs/heads/stale")
    # Fetch earlier in the same command.
    check("oi409: fetch self && merge FETCH_HEAD [local-fetch rule]", "git fetch self stale && git merge FETCH_HEAD",
          ch, True, both, env)
    check("oi409: fetch self src:dst && merge dst (dst already exists) [local-fetch rule]",
          "git fetch self stale:tmp && git merge tmp", ch, True, env=env)
    check("oi409: fetch self && merge self/side (local remote re-points it) [local-fetch rule]",
          "git fetch self && git merge self/side", ch, True, env=env)
    check("oi409: fetch self && merge unresolvable [local-fetch rule]", "git fetch self && git merge self/nosuch",
          ch, True, env=env)
    check("oi409: fetch self && reset --hard FETCH_HEAD [local-fetch rule]",
          "git fetch self stale && git reset --hard FETCH_HEAD", ch, True, env=env)
    check("oi409: fetch self && merge side (any write after a LOCAL fetch blocks) [local-fetch rule]",
          "git fetch self && git merge side", ch, True, env=env)
    check("oi409: fetch gh && merge side (after a network fetch: judged normally)",
          "git fetch gh && git merge side", ch, False, env=env)
    check("oi409: fetch gh side && merge FETCH_HEAD", "git fetch gh side && git merge FETCH_HEAD",
          ch, False, env=env)
    check("oi409: fetch gh stale && merge FETCH_HEAD",
          "git fetch gh stale && git merge FETCH_HEAD", ch, True, env=env)
    check("oi409: fetch gh && merge gh/side", "git fetch gh && git merge gh/side", ch, False,
          env=env)
    check("oi409: fetch gh side:tmp && merge tmp (network: = gh/side)",
          "git fetch gh side:tmp && git merge tmp", ch, False, env=env)
    check("oi409: fetch gh +stale:tmp && merge tmp (network: = gh/stale; tmp is at side now)",
          "git fetch gh +stale:tmp && git merge tmp", ch, True, env=env)
    check("oi409: fetch gh new && reset --hard FETCH_HEAD~1 (suffix kept: new~1 tracks memory)",
          "git fetch gh new && git reset --hard FETCH_HEAD~1", ch, True, env=env)
    check("oi409: fetch gh new && reset --hard FETCH_HEAD (no memory)",
          "git fetch gh new && git reset --hard FETCH_HEAD", ch, False, env=env)
    check("oi409: fetch unconfigured URL && merge FETCH_HEAD",
          "git fetch https://example.invalid/x.git side && git merge FETCH_HEAD", ch, True,
          env=env)
    check("oi409: merge of a nonexistent ref with no fetch", "git merge nosuch", ch, False,
          env=env)
    # R1-01: checkout/switch of a branch that exists only as refs/remotes/*/<name>.
    check("oi409: checkout oldfeat (remote-only, DWIM)", "git checkout oldfeat", ch, True, both,
          env)
    check("oi409: switch oldfeat (remote-only, DWIM)", "git switch oldfeat", ch, True, env=env)
    check("oi409: checkout --no-guess oldfeat", "git checkout --no-guess oldfeat", ch, False,
          env=env)
    # A branch that only a LOCAL remote's fetch earlier in the command creates.
    check("oi409: fetch loc && checkout lfeat (DWIM after a local fetch) [local-fetch rule]",
          "git fetch loc && git checkout lfeat", ch, True, both, env)
    check("oi409: fetch loc && switch lfeat [local-fetch rule]", "git fetch loc && git switch lfeat", ch, True,
          env=env)
    check("oi409: fetch <local path> src:refs/remotes/gh/x && checkout x (DWIM) [local-fetch rule]",
          "git fetch %s lfeat:refs/remotes/gh/lfeat && git checkout lfeat"
          % os.path.join(home, "loc.git").replace("\\", "/"), ch, True, env=env)
    locp = os.path.join(home, "loc.git").replace("\\", "/")
    check("oi409: fetch <local path> glob into gh/lf* && switch lfeat [local-fetch rule]",
          "git fetch %s '+refs/heads/lf*:refs/remotes/gh/lf*' && git switch lfeat" % locp, ch,
          True, env=env)
    check("oi409: fetch <local path> glob into gh/* && merge gh/side [local-fetch rule]",
          "git fetch %s '+refs/heads/*:refs/remotes/gh/*' && git merge gh/side" % locp, ch,
          True, env=env)
    check("oi409: fetch <local path> glob into refs/heads/imp/* && checkout imp/lfeat [local-fetch rule]",
          "git fetch %s '+refs/heads/*:refs/heads/imp/*' && git checkout imp/lfeat" % locp,
          ch, True, env=env)
    # Every spelling of a re-pointed ref (N3): heads/, tags/, an existing destination.
    git(ch, "branch", "imp/side", "side")
    git(ch, "tag", "tgx", "side")
    check("oi409: fetch <local path> glob && merge heads/imp/side [local-fetch rule]",
          "git fetch %s '+refs/heads/*:refs/heads/imp/*' && git merge heads/imp/side" % locp,
          ch, True, env=env)
    check("oi409: fetch <local path> side:refs/heads/imp/side && merge heads/imp/side [local-fetch rule]",
          "git fetch %s +side:refs/heads/imp/side && git merge heads/imp/side" % locp, ch,
          True, env=env)
    check("oi409: fetch <local path> side:refs/tags/tgx && merge tags/tgx [local-fetch rule]",
          "git fetch %s +refs/heads/side:refs/tags/tgx && git merge tags/tgx" % locp, ch,
          True, env=env)
    check("oi409: merge heads/imp/side with no fetch (no memory)", "git merge heads/imp/side",
          ch, False, env=env)
    # Revision suffixes name the same re-pointed ref (N4); after a LOCAL fetch every later
    # write target in the command blocks, whatever its spelling.
    check("oi409: fetch loc side && merge FETCH_HEAD^0 [local-fetch rule]", "git fetch loc side && git merge "
          "FETCH_HEAD^0", ch, True, both, env)
    check("oi409: fetch loc side && merge FETCH_HEAD~0 [local-fetch rule]", "git fetch loc side && git merge "
          "FETCH_HEAD~0", ch, True, env=env)
    check("oi409: fetch <local path> side:imp/side && merge imp/side~0 [local-fetch rule]",
          "git fetch %s +side:refs/heads/imp/side && git merge imp/side~0" % locp, ch, True,
          env=env)
    check("oi409: fetch <local path> side:tags/tgx && merge tgx^{commit} [local-fetch rule]",
          "git fetch %s +refs/heads/side:refs/tags/tgx && git merge 'tgx^{commit}'" % locp,
          ch, True, env=env)
    check("oi409: fetch gh stale && merge FETCH_HEAD^0 (network alias, suffix kept)",
          "git fetch gh stale && git merge FETCH_HEAD^0", ch, True, env=env)
    check("oi409: fetch gh side && merge FETCH_HEAD^0 (network alias, no memory)",
          "git fetch gh side && git merge FETCH_HEAD^0", ch, False, env=env)
    # Other fetch carriers (N5, N6).
    check("oi409: remote update loc && checkout lfeat [local-fetch rule]", "git remote update loc && git "
          "checkout lfeat", ch, True, both, env)
    check("oi409: remote update && merge loc/side [local-fetch rule]", "git remote update && git merge loc/side",
          ch, True, env=env)
    check("oi409: remote update <unconfigured group> && merge side [local-fetch rule]",
          "git remote update grp && git merge side", ch, True, env=env)
    git(ch, "config", "branch.main.remote", "gh")
    git(ch, "config", "branch.main.merge", "refs/heads/side")
    check("oi409: fetch -- loc side && merge FETCH_HEAD (network upstream)",
          "git fetch -- loc side && git merge FETCH_HEAD", ch, True, env=env)
    check("oi409: pull -- loc side (network upstream)", "git pull -- loc side", ch, True,
          env=env)
    git(ch, "config", "branch.main.remote", ".")
    git(ch, "config", "branch.main.merge", "refs/heads/stale")
    check("oi409: remote -v (not a fetch)", "git remote -v && git merge side", ch, False,
          env=env)
    check("oi409: remote -v update loc && merge loc/side [local-fetch rule]", "git remote -v update loc && git "
          "merge loc/side", ch, True, env=env)
    check("oi409: remote --verbose update loc && checkout lfeat", "git remote --verbose "
          "update loc && git checkout lfeat", ch, True, env=env)
    git(ch, "config", "branch.main.remote", "gh")
    git(ch, "config", "branch.main.merge", "refs/heads/side")
    check("oi409: fetch --all && checkout lfeat (network upstream)",
          "git fetch --all && git checkout lfeat", ch, True, env=env)
    git(ch, "config", "branch.main.remote", ".")
    git(ch, "config", "branch.main.merge", "refs/heads/stale")
    check("oi409: checkout lfeat with no fetch (git fails: no such ref)",
          "git checkout lfeat", ch, False, env=env)
    check("oi409: fetch loc && merge remotes/loc/side [local-fetch rule]",
          "git fetch loc && git merge remotes/loc/side", ch, True, env=env)
    check("oi409: switch -c oldfeat2 (new branch from HEAD)", "git switch -c oldfeat2", ch,
          False, env=env)
    # R1-04: tree-ish sources.
    tree = subprocess.run(["git", "rev-parse", "old^{tree}"], cwd=ch, capture_output=True,
                          text=True).stdout.strip()
    check("oi409: checkout old^{tree} -- .", "git checkout 'old^{tree}' -- .", ch, True,
          both, env)
    check("oi409: checkout <tree sha> -- .", "git checkout %s -- ." % tree, ch, True, env=env)
    check("oi409: restore --source=old^{tree} .", "git restore '--source=old^{tree}' .", ch,
          True, env=env)
    check("oi409: read-tree -u --reset old^{tree}", "git read-tree -u --reset 'old^{tree}'",
          ch, True, env=env)
    # --diff-filter=d: a ref that only DELETES memory writes nothing when HEAD lacks it.
    check("oi409: merge del (deletes memory only)", "git merge del", ch, False, env=env)
    check("oi409: cherry-pick del (deletes memory only)", "git cherry-pick del", ch, False,
          env=env)
    check("oi409: revert del (re-adds memory)", "git revert del", ch, True, env=env)
    # read-tree two-tree merge with -u.
    check("oi409: read-tree -u -m HEAD old", "git read-tree -u -m HEAD old", ch, True, both,
          env)


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
        memory_checkout_checks()

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
