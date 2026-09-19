"""Standalone test for hooks/worktree-isolation-guard.py.

WHAT THIS GUARD ENFORCES (OI-252): CLAUDE.md's single-writer rule -- "Shared-checkout =
SINGLE-WRITER before editing any shared single-instance file/repo under ~/.claude ...
isolate via a worktree". A blast-radius commit made from the MAIN checkout of a shared ORA
repo is blocked; the same commit from a linked worktree is allowed.

DESIGN HISTORY -- this replaces a session-branch-record design that an adversarial refute
pass killed on 2026-09-10. That design tried to model "a branch this session established"
and produced four HIGH defects: keyed per session rather than per (session, repo); no
notion of "established", so `git checkout -b` and `git worktree add -b` -- the guard's own
remediation -- both false-blocked; and an inversion where a session whose first commit
landed on the parked peer branch recorded THAT as canonical. The worktree signal needs no
state at all, so that entire failure class is gone.

C1 REGRESSION (the critical defect that pass found): the guard must sys.exit(2) INSIDE
main(). pretooluse-dispatcher runs guards IN-PROCESS first and reads rc only from
SystemExit -- a returned value is silently discarded, so a `return 2` guard prints
"BLOCKED" to stderr and ALLOWS the commit. Test "C1" below drives the dispatcher path
rather than spawning the script, because spawning is exactly how that escaped review.
"""
import json, os, subprocess, sys, tempfile, shutil

_GIT_LEAK_VARS = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR",
                  "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_PREFIX")
for _v in _GIT_LEAK_VARS:
    os.environ.pop(_v, None)


def _clean_env():
    env = dict(os.environ)
    for _v in _GIT_LEAK_VARS:
        env.pop(_v, None)
    return env


HOOKS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GUARD = os.path.join(HOOKS, "worktree-isolation-guard.py")
HYGIENE = os.path.join(HOOKS, "commit-hygiene-guard.py")
PY = sys.executable

FAILS = []


def check(name, cond, detail=""):
    if cond:
        print("  [PASS] %s" % name)
    else:
        print("  [FAIL] %s %s" % (name, detail))
        FAILS.append(name)


def git(repo, *a):
    return subprocess.run(("git",) + a, cwd=repo, capture_output=True, text=True,
                          env=_clean_env())


SESS_TMP = tempfile.mkdtemp(prefix="wig-sessions-")


def _env(repo_root, sessions_dir=None):
    env = _clean_env()
    # Test seam: which roots count as ORA shared checkouts (signal c).
    env["WORKTREE_ISOLATION_SHARED_ROOTS"] = repo_root
    env["ORA_OVERRIDE_SESSIONS_DIR"] = sessions_dir or SESS_TMP
    return env


def run_guard(cmd, cwd, repo_root, session="testsess", sessions_dir=None):
    payload = {"tool_name": "Bash", "tool_input": {"command": cmd},
               "cwd": cwd, "session_id": session}
    p = subprocess.run([PY, GUARD], input=json.dumps(payload), capture_output=True,
                       text=True, env=_env(repo_root, sessions_dir))
    return p.returncode, (p.stderr or "")


def make_repo(tmp, name="repo"):
    repo = os.path.join(tmp, name)
    os.makedirs(os.path.join(repo, "hooks"))
    os.makedirs(os.path.join(repo, "src", "hooks"))
    os.makedirs(os.path.join(repo, "docs"))
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "user.email", "t@t.t")
    git(repo, "config", "user.name", "t")
    for rel in ("hooks/some-guard.py", "src/hooks/useThing.ts", "docs/notes.md",
                "CLAUDE.md", "plain.txt"):
        with open(os.path.join(repo, rel), "w", encoding="utf-8") as fh:
            fh.write("v1\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "base")
    return repo


def edit(repo, rel, body="v2\n"):
    with open(os.path.join(repo, rel), "w", encoding="utf-8") as fh:
        fh.write(body)


def stage(repo, rel, body="v2\n"):
    edit(repo, rel, body)
    git(repo, "add", "--", rel)


print("== signal (b): main checkout vs linked worktree ==")
tmp = tempfile.mkdtemp()
try:
    repo = make_repo(tmp)
    stage(repo, "hooks/some-guard.py")
    rc, err = run_guard("git commit -m x", repo, repo)
    check("1 blocks blast-radius commit from MAIN checkout",
          rc == 2 and "BLOCKED (worktree-isolation-guard)" in err,
          "rc=%s err=%r" % (rc, err[:200]))

    wt = os.path.join(tmp, "wt1")
    git(repo, "worktree", "add", "-q", "-b", "feat/x", wt)
    stage(wt, "hooks/some-guard.py", "v3\n")
    rc, err = run_guard("git commit -m x", wt, repo)
    check("2 ALLOWS the same commit from a linked WORKTREE", rc == 0,
          "rc=%s err=%r" % (rc, err[:300]))
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print("== signal (a): blast-radius scoping, root-anchored ==")
tmp = tempfile.mkdtemp()
try:
    repo = make_repo(tmp)
    stage(repo, "docs/notes.md")
    rc, err = run_guard("git commit -m x", repo, repo)
    check("3 allows non-blast-radius commit from main checkout", rc == 0,
          "rc=%s err=%r" % (rc, err[:200]))

    git(repo, "reset", "-q", "--hard", "HEAD")
    stage(repo, "src/hooks/useThing.ts")
    rc, err = run_guard("git commit -m x", repo, repo)
    check("4 src/hooks/ is NOT blast radius (root-anchored)", rc == 0,
          "rc=%s err=%r" % (rc, err[:200]))

    git(repo, "reset", "-q", "--hard", "HEAD")
    stage(repo, "CLAUDE.md")
    rc, err = run_guard("git commit -m x", repo, repo)
    check("5 CLAUDE.md IS blast radius (the OI-247 shape)",
          rc == 2 and "BLOCKED" in err, "rc=%s err=%r" % (rc, err[:200]))
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print("== H4: staging forms the incident actually used ==")
tmp = tempfile.mkdtemp()
try:
    repo = make_repo(tmp)
    edit(repo, "hooks/some-guard.py")
    rc, err = run_guard("git add -A && git commit -m x", repo, repo)
    check("6 catches `git add -A && git commit` (nothing staged yet)",
          rc == 2 and "BLOCKED" in err, "rc=%s err=%r" % (rc, err[:200]))

    git(repo, "reset", "-q", "--hard", "HEAD")
    edit(repo, "hooks/some-guard.py")
    rc, err = run_guard("git add hooks/some-guard.py && git commit -m x", repo, repo)
    check("7 catches `git add <path> && git commit`",
          rc == 2 and "BLOCKED" in err, "rc=%s err=%r" % (rc, err[:200]))

    git(repo, "reset", "-q", "--hard", "HEAD")
    edit(repo, "hooks/some-guard.py")
    rc, err = run_guard("git commit -am x", repo, repo)
    check("8 catches `commit -am`", rc == 2 and "BLOCKED" in err,
          "rc=%s err=%r" % (rc, err[:200]))
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print("== signal (c): only ORA shared checkouts ==")
tmp = tempfile.mkdtemp()
try:
    repo = make_repo(tmp)
    other = make_repo(tmp, name="unrelated")
    stage(other, "hooks/some-guard.py")
    # shared-roots names only `repo`, so `other` is out of scope entirely.
    rc, err = run_guard("git commit -m x", other, repo)
    check("9 unrelated repo with a hooks/ dir is untouched", rc == 0,
          "rc=%s err=%r" % (rc, err[:200]))
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print("== fail-open contract ==")
tmp = tempfile.mkdtemp()
try:
    notrepo = os.path.join(tmp, "notarepo")
    os.makedirs(notrepo)
    rc, err = run_guard("git commit -m x", notrepo, notrepo)
    check("10 non-repo fails OPEN", rc == 0, "rc=%s err=%r" % (rc, err[:200]))

    repo = make_repo(tmp)
    stage(repo, "hooks/some-guard.py")
    rc, err = run_guard("git status", repo, repo)
    check("11 non-commit command ignored", rc == 0, "rc=%s" % rc)

    p = subprocess.run([PY, GUARD], input="not json at all", capture_output=True,
                       text=True, env=_env(repo))
    check("12 garbage stdin fails OPEN", p.returncode == 0, "rc=%s" % p.returncode)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print("== override ==")
tmp = tempfile.mkdtemp()
try:
    repo = make_repo(tmp)
    sess = tempfile.mkdtemp(prefix="wig-o-")
    stage(repo, "hooks/some-guard.py")
    rc, err = run_guard("git commit -m x", repo, repo, session="ov", sessions_dir=sess)
    check("13a blocked without override",
          rc == 2 and "BLOCKED (worktree-isolation-guard)" in err,
          "rc=%s err=%r" % (rc, err[:200]))

    od = os.path.join(sess, "ov", "overrides")
    os.makedirs(od, exist_ok=True)
    with open(os.path.join(od, "allow-shared-checkout-commit"), "w",
              encoding="utf-8") as fh:
        fh.write("scope: shared-checkout-commit\nsession: ov\nreason: test\n")
    rc, err = run_guard("git commit -m x", repo, repo, session="ov", sessions_dir=sess)
    check("13b override token permits the commit", rc == 0,
          "rc=%s err=%r" % (rc, err[:300]))
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print("== C1 REGRESSION: must block through the DISPATCHER's in-process path ==")
tmp = tempfile.mkdtemp()
try:
    import importlib.util
    repo = make_repo(tmp)
    stage(repo, "hooks/some-guard.py")
    spec = importlib.util.spec_from_file_location(
        "_disp", os.path.join(HOOKS, "pretooluse-dispatcher.py"))
    disp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(disp)

    payload = {"tool_name": "Bash", "tool_input": {"command": "git commit -m x"},
               "cwd": repo, "session_id": "dispsess"}
    saved = {k: os.environ.get(k) for k in
             ("WORKTREE_ISOLATION_SHARED_ROOTS", "ORA_OVERRIDE_SESSIONS_DIR")}
    os.environ["WORKTREE_ISOLATION_SHARED_ROOTS"] = repo
    os.environ["ORA_OVERRIDE_SESSIONS_DIR"] = SESS_TMP
    try:
        # run_guard(name, raw) takes raw payload BYTES -- the dispatcher reads
        # sys.stdin.buffer.read() and _StdinShim is typed `raw: bytes`. Passing str
        # makes the in-process shim raise TypeError and the subprocess fallback hang
        # with an unclosed stdin until the 60s timeout, which looks exactly like a
        # broken guard. Returns (rc, stdout, stderr, mode).
        rc, _out, gerr, mode = disp.run_guard("worktree-isolation-guard",
                                              json.dumps(payload).encode("utf-8"))
        check("C1 dispatcher in-process path yields rc=2 (not a discarded return)",
              rc == 2, "rc=%r mode=%r err=%r" % (rc, mode, gerr[:200]))
        # The defect was specifically that in-process dispatch discarded a returned
        # value. Assert the block came from THAT path, not a subprocess fallback.
        check("C1b block is produced by the in-process path itself",
              rc == 2 and mode == "inprocess", "rc=%r mode=%r" % (rc, mode))
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print("== M2 FIX: commit-hygiene-guard warn-only, asserted BEHAVIOURALLY ==")
tmp = tempfile.mkdtemp()
try:
    repo = make_repo(tmp)
    stage(repo, "hooks/some-guard.py")
    hsess = tempfile.mkdtemp(prefix="wig-h-")
    payload = {"tool_name": "Bash", "tool_input": {"command": "git commit -m x"},
               "cwd": repo, "session_id": "hyg"}
    env = _clean_env()
    env["COMMIT_HYGIENE_SESSIONS_DIR"] = hsess
    p = subprocess.run([PY, HYGIENE], input=json.dumps(payload), capture_output=True,
                       text=True, env=env)
    dec = ""
    if p.stdout.strip():
        try:
            dec = (json.loads(p.stdout).get("hookSpecificOutput") or {}).get(
                "permissionDecision") or ""
        except Exception:
            dec = "<unparseable>"
    # Substring inspection of the source is theatre -- a refute pass showed a real
    # sys.exit(2) inserted into hygiene's main() left such assertions green. RUN it.
    check("14 commit-hygiene-guard exits 0 and decides 'allow'",
          p.returncode == 0 and dec == "allow",
          "rc=%s dec=%r" % (p.returncode, dec))
finally:
    shutil.rmtree(tmp, ignore_errors=True)

shutil.rmtree(SESS_TMP, ignore_errors=True)

print("")
if FAILS:
    print("FAILED: %d" % len(FAILS))
    for f in FAILS:
        print("  - %s" % f)
    sys.exit(1)
print("ALL PASS")
