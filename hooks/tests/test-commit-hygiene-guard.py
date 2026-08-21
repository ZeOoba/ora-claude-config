"""Standalone test for hooks/commit-hygiene-guard.py.

Builds throwaway git repos and drives the guard via stdin exactly as the harness does.
Covers the two 2026-08-09 process gaps:
  A) BRANCH IDENTITY at commit time -- a session committed to another session's feature
     branch because the shared checkout's branch changed between its pre-commit check and
     the commit itself. Dirty-file checks cannot see that; only branch identity can.
  B) MEMORY `modified:` STAMP -- the harness stamps `modified:` when IT writes a
     node_type: memory file via Edit/Write, but a script/Bash write bypasses that, so a
     spliced memory edit commits with a stale timestamp.

SAFETY: the guard is warn-only. Every test asserts exit 0 and a non-"deny" decision --
a regression that makes this thing block must fail loudly here.
"""
import json, os, subprocess, sys, tempfile, shutil

# Same env-leak defence as the sibling tests: when run inside the real pre-push hook
# chain, git exports GIT_DIR/GIT_INDEX_FILE etc. into this process, and they would
# silently redirect every subprocess git call below at the OUTER repo.
_GIT_LEAK_VARS = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR",
                  "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_PREFIX")
for _v in _GIT_LEAK_VARS:
    os.environ.pop(_v, None)


def _clean_env():
    env = dict(os.environ)
    for _v in _GIT_LEAK_VARS:
        env.pop(_v, None)
    return env


# Resolved from THIS file, not the live tree: a worktree run must test the guard it is
# about to land, not whatever is already deployed.
GUARD = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "commit-hygiene-guard.py")
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


SESS_TMP = tempfile.mkdtemp(prefix="chg-sessions-")


def run_guard(cmd, cwd, session="testsess", sessions_dir=None):
    """Drives the guard exactly as the harness does.

    COMMIT_HYGIENE_SESSIONS_DIR is ALWAYS set (review finding m5): without it the tests
    wrote branch markers into the REAL C:/Users/Owner/.claude/hooks/sessions/testsess/,
    which both polluted live session state and made the branch assertions
    order-dependent across runs -- a test that passes because of a marker a previous run
    left behind is not a test.
    """
    payload = {"tool_name": "Bash", "tool_input": {"command": cmd},
               "cwd": cwd, "session_id": session}
    env = _clean_env()
    env["COMMIT_HYGIENE_SESSIONS_DIR"] = sessions_dir or SESS_TMP
    p = subprocess.run([PY, GUARD], input=json.dumps(payload), capture_output=True,
                       text=True, env=env)
    ctx = ""
    decision = ""
    if p.stdout.strip():
        try:
            out = json.loads(p.stdout)
            ctx = (out.get("hookSpecificOutput") or {}).get("additionalContext") or ""
            decision = (out.get("hookSpecificOutput") or {}).get("permissionDecision") or ""
        except Exception:
            ctx = p.stdout
    return p.returncode, ctx, decision


def make_repo(tmp, memory_rel="projects/p/memory"):
    repo = os.path.join(tmp, "repo")
    os.makedirs(os.path.join(repo, memory_rel))
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "user.email", "t@t.t")
    git(repo, "config", "user.name", "t")
    mem = os.path.join(repo, memory_rel, "note.md")
    with open(mem, "w", encoding="utf-8") as fh:
        fh.write("---\nname: note\nmetadata:\n  node_type: memory\n"
                 "  modified: 2026-01-01T00:00:00.000Z\n---\n\nbody v1\n")
    with open(os.path.join(repo, "plain.txt"), "w", encoding="utf-8") as fh:
        fh.write("hello\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "base")
    return repo, mem


def write_mem(path, body, modified):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("---\nname: note\nmetadata:\n  node_type: memory\n"
                 "  modified: %s\n---\n\n%s\n" % (modified, body))


print("== A. branch identity ==")
tmp = tempfile.mkdtemp()
try:
    repo, mem = make_repo(tmp)
    rc, ctx, dec = run_guard("git commit -m x", repo)
    check("A1 names the current branch on a commit", "main" in ctx and "BRANCH" in ctx.upper(),
          "ctx=%r" % ctx[:200])
    check("A1b warn-only (never deny)", rc == 0 and dec != "deny", "rc=%s dec=%s" % (rc, dec))

    git(repo, "checkout", "-q", "-b", "feat/other")
    rc, ctx, dec = run_guard("git commit -m x", repo)
    check("A2 names the new branch after a switch", "feat/other" in ctx, "ctx=%r" % ctx[:200])

    rc, ctx, dec = run_guard("ls -la", repo)
    check("A3 silent on a non-commit command", ctx == "" and rc == 0, "ctx=%r" % ctx[:120])

    rc, ctx, dec = run_guard("git status", repo)
    check("A4 silent on non-commit git", ctx == "" and rc == 0, "ctx=%r" % ctx[:120])
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print("== B. memory modified: stamp ==")
tmp = tempfile.mkdtemp()
try:
    repo, mem = make_repo(tmp)
    # body changed, stamp NOT updated -> must warn
    write_mem(mem, "body v2", "2026-01-01T00:00:00.000Z")
    git(repo, "add", "-A")
    rc, ctx, dec = run_guard("git commit -m x", repo)
    check("B1 warns when body changed but modified: did not",
          "modified:" in ctx and "note.md" in ctx, "ctx=%r" % ctx[:300])
    check("B1b still warn-only", rc == 0 and dec != "deny", "rc=%s dec=%s" % (rc, dec))
finally:
    shutil.rmtree(tmp, ignore_errors=True)

tmp = tempfile.mkdtemp()
try:
    repo, mem = make_repo(tmp)
    # body changed AND stamp updated -> silent about stamps
    write_mem(mem, "body v2", "2026-08-09T00:00:00.000Z")
    git(repo, "add", "-A")
    rc, ctx, dec = run_guard("git commit -m x", repo)
    check("B2 silent when modified: was updated", "modified:" not in ctx, "ctx=%r" % ctx[:300])
finally:
    shutil.rmtree(tmp, ignore_errors=True)

tmp = tempfile.mkdtemp()
try:
    repo, mem = make_repo(tmp)
    # non-memory file changed -> no stamp complaint
    with open(os.path.join(repo, "plain.txt"), "w", encoding="utf-8") as fh:
        fh.write("changed\n")
    git(repo, "add", "-A")
    rc, ctx, dec = run_guard("git commit -m x", repo)
    check("B3 ignores non-memory files", "modified:" not in ctx, "ctx=%r" % ctx[:300])
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print("== B'. REFUTE regressions (false negatives found by adversarial review) ==")
tmp = tempfile.mkdtemp()
try:
    repo, mem = make_repo(tmp)
    # PATHSPEC commit re-reads the WORKING TREE, not the index. A stale stamp sitting
    # unstaged in the working tree is exactly what `git commit -- <path>` will land, and
    # a --cached-only check cannot see it.
    write_mem(mem, "body v2", "2026-01-01T00:00:00.000Z")  # modified, NOT staged
    rel = "projects/p/memory/note.md"
    rc, ctx, dec = run_guard("git commit -m x -- " + rel, repo)
    check("B4 pathspec commit: warns on working-tree stale stamp",
          "modified:" in ctx and "note.md" in ctx, "ctx=%r" % ctx[:300])
    check("B4b still warn-only", rc == 0 and dec != "deny", "rc=%s dec=%s" % (rc, dec))
finally:
    shutil.rmtree(tmp, ignore_errors=True)

tmp = tempfile.mkdtemp()
try:
    repo, _ = make_repo(tmp)
    # core.quotePath: git double-quotes+escapes non-ASCII paths by default, which fails a
    # naive `.md$` match and silently drops the file.
    # MUST be a real non-ASCII name. A previous edit flattened this to "na00efve.md"
    # (pure ASCII), which made the test VACUOUS -- it passed even with core.quotePath=false
    # and the utf-8 subprocess decoding both removed, i.e. the two regressions it exists to
    # pin. Escape keeps the SOURCE ascii-only while the FILENAME is genuinely non-ASCII.
    nonascii = os.path.join(repo, "projects/p/memory", "naïve.md")
    assert not nonascii.isascii(), "B5 fixture must be non-ASCII or the test is vacuous"
    write_mem(nonascii, "v1", "2026-01-01T00:00:00.000Z")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "add nonascii")
    write_mem(nonascii, "v2 changed", "2026-01-01T00:00:00.000Z")  # stale stamp
    git(repo, "add", "-A")
    rc, ctx, dec = run_guard("git commit -m x", repo)
    check("B5 non-ASCII filename still detected (core.quotePath=false)",
          "modified:" in ctx, "ctx=%r" % ctx[:300])
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print("== D. independent-review regressions (2026-08-09, VERDICT changes-requested) ==")

# M1 -- `cd <repo> && git commit` was completely silent: repo came from payload cwd only.
tmp = tempfile.mkdtemp()
try:
    repo, mem = make_repo(tmp)
    outside = tempfile.mkdtemp()
    try:
        rc, ctx, dec = run_guard('cd "%s" && git commit -m x' % repo, outside)
        check("D-M1 cd-compound resolves the repo", "main" in ctx and "BRANCH" in ctx.upper(),
              "ctx=%r" % ctx[:200])
    finally:
        shutil.rmtree(outside, ignore_errors=True)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# M2 -- `git -C repoA commit` run from repoB reported repoB's branch (confidently WRONG).
tmpA, tmpB = tempfile.mkdtemp(), tempfile.mkdtemp()
try:
    repoA, _ = make_repo(tmpA)
    repoB, _ = make_repo(tmpB)
    git(repoB, "checkout", "-q", "-b", "feat/decoy")
    rc, ctx, dec = run_guard('git -C "%s" commit -m x' % repoA, repoB)
    check("D-M2 -C targets the right repo's branch",
          "main" in ctx and "feat/decoy" not in ctx, "ctx=%r" % ctx[:200])
finally:
    shutil.rmtree(tmpA, ignore_errors=True)
    shutil.rmtree(tmpB, ignore_errors=True)

# M3a -- `git add -A && git commit`: add has NOT run at PreToolUse time, index is empty.
tmp = tempfile.mkdtemp()
try:
    repo, mem = make_repo(tmp)
    write_mem(mem, "body v2", "2026-01-01T00:00:00.000Z")  # stale stamp, unstaged
    rc, ctx, dec = run_guard("git add -A && git commit -m x", repo)
    check("D-M3a add&&commit sees the working tree", "modified:" in ctx, "ctx=%r" % ctx[:250])
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# M3b -- `git commit -am` stages tracked files itself.
tmp = tempfile.mkdtemp()
try:
    repo, mem = make_repo(tmp)
    write_mem(mem, "body v2", "2026-01-01T00:00:00.000Z")
    rc, ctx, dec = run_guard("git commit -am x", repo)
    check("D-M3b commit -am sees the working tree", "modified:" in ctx, "ctx=%r" % ctx[:250])
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# m4 -- glued operators must still segment.
tmp = tempfile.mkdtemp()
try:
    repo, mem = make_repo(tmp)
    write_mem(mem, "body v2", "2026-01-01T00:00:00.000Z")
    rc, ctx, dec = run_guard("git add -A&&git commit -m x", repo)
    check("D-m4 glued && still detected", "BRANCH" in ctx.upper() and "modified:" in ctx,
          "ctx=%r" % ctx[:250])
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# m3 -- `echo git commit ...` must NOT fire (git not at a segment head).
tmp = tempfile.mkdtemp()
try:
    repo, _ = make_repo(tmp)
    rc, ctx, dec = run_guard("echo git commit is dangerous", repo)
    check("D-m3 prose mentioning git commit does not fire", ctx == "", "ctx=%r" % ctx[:200])
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# m2 -- pathspec commit must not warn about memory files outside the pathspec.
tmp = tempfile.mkdtemp()
try:
    repo, mem = make_repo(tmp)
    write_mem(mem, "body v2", "2026-01-01T00:00:00.000Z")  # dirty, stale, NOT in pathspec
    with open(os.path.join(repo, "plain.txt"), "w", encoding="utf-8") as fh:
        fh.write("changed\n")
    rc, ctx, dec = run_guard("git commit -m x -- plain.txt", repo)
    check("D-m2 pathspec excludes unrelated memory file", "modified:" not in ctx,
          "ctx=%r" % ctx[:250])
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# GAP A headline feature had NO coverage at all (m5): BRANCH CHANGED + marker persistence.
tmp = tempfile.mkdtemp()
try:
    repo, _ = make_repo(tmp)
    sdir = tempfile.mkdtemp()
    try:
        rc, ctx, _ = run_guard("git commit -m x", repo, sessions_dir=sdir)
        check("D-A5a first commit: plain BRANCH line", "BRANCH CHANGED" not in ctx,
              "ctx=%r" % ctx[:160])
        git(repo, "checkout", "-q", "-b", "feat/switched")
        rc, ctx, _ = run_guard("git commit -m x", repo, sessions_dir=sdir)
        check("D-A5b after a switch: BRANCH CHANGED fires",
              "BRANCH CHANGED" in ctx and "feat/switched" in ctx and "main" in ctx,
              "ctx=%r" % ctx[:250])
        rc, ctx, _ = run_guard("git commit -m x", repo, sessions_dir=sdir)
        check("D-A5c same branch again: no repeat CHANGED", "BRANCH CHANGED" not in ctx,
              "ctx=%r" % ctx[:160])
    finally:
        shutil.rmtree(sdir, ignore_errors=True)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# m7 -- marker keyed on full path, not basename: same-named repos must not cross-talk.
tmp = tempfile.mkdtemp()
try:
    a = os.path.join(tmp, "a"); b = os.path.join(tmp, "b")
    os.makedirs(a); os.makedirs(b)
    repoA, _ = make_repo(a)   # both end up named "repo"
    repoB, _ = make_repo(b)
    git(repoB, "checkout", "-q", "-b", "feat/bee")
    sdir = tempfile.mkdtemp()
    try:
        run_guard("git commit -m x", repoA, sessions_dir=sdir)
        rc, ctx, _ = run_guard("git commit -m x", repoB, sessions_dir=sdir)
        check("D-m7 same-basename repos keep separate markers",
              "BRANCH CHANGED" not in ctx, "ctx=%r" % ctx[:200])
    finally:
        shutil.rmtree(sdir, ignore_errors=True)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print("== E. round-2 review regressions (incl. one the rewrite INTRODUCED) ==")

# M4 -- bare newline as a statement separator. The rewrite REGRESSED this vs draft 1.
tmp = tempfile.mkdtemp()
try:
    repo, mem = make_repo(tmp)
    write_mem(mem, "body v2", "2026-01-01T00:00:00.000Z")
    rc, ctx, dec = run_guard("git add -A\ngit commit -m x", repo)
    check("E-M4a newline-separated add/commit detected",
          "BRANCH" in ctx.upper() and "modified:" in ctx, "ctx=%r" % ctx[:250])
    rc, ctx, dec = run_guard('cd "%s"\ngit commit -m x' % repo, tempfile.gettempdir())
    check("E-M4b newline after cd resolves the repo", "BRANCH" in ctx.upper(),
          "ctx=%r" % ctx[:200])
    rc, ctx, dec = run_guard("echo staging done # note\ngit commit -m x", repo)
    check("E-M4c comment does not eat the newline", "BRANCH" in ctx.upper(),
          "ctx=%r" % ctx[:200])
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# M4-guard: the heredoc idiom must SURVIVE the newline change (quoted newlines stay inside
# their token). This is the case the newline fix could plausibly have broken.
tmp = tempfile.mkdtemp()
try:
    repo, _ = make_repo(tmp)
    rc, ctx, dec = run_guard('git commit -m "$(cat <<EOF\nline one\nline two\nEOF\n)"', repo)
    check("E-M4d heredoc commit message still detected", "BRANCH" in ctx.upper(),
          "ctx=%r" % ctx[:200])
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# m8 -- glued -m value containing "a" must NOT be read as -a (false worktree read).
tmp = tempfile.mkdtemp()
try:
    repo, mem = make_repo(tmp)
    write_mem(mem, "body v2", "2026-01-01T00:00:00.000Z")  # dirty, NOT staged
    rc, ctx, dec = run_guard('git commit -m"add feature X"', repo)
    check("E-m8a glued -m value is not mistaken for -a", "modified:" not in ctx,
          "ctx=%r" % ctx[:250])
    rc, ctx, dec = run_guard("git commit -am x", repo)
    check("E-m8b real -am still stages-all", "modified:" in ctx, "ctx=%r" % ctx[:250])
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# m9 -- relative -C resolves against the SHELL cwd, not the hook process's.
tmp = tempfile.mkdtemp()
try:
    repo, _ = make_repo(tmp)
    parent = os.path.dirname(repo)
    rc, ctx, dec = run_guard("git -C repo commit -m x", parent)
    check("E-m9 relative -C resolves", "BRANCH" in ctx.upper(), "ctx=%r" % ctx[:200])
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# m11 -- `git add <unrelated> && git commit` must not warn about untouched memory files.
tmp = tempfile.mkdtemp()
try:
    repo, mem = make_repo(tmp)
    write_mem(mem, "body v2", "2026-01-01T00:00:00.000Z")  # dirty stale, NOT added
    # NOTE (round 3): the add-path restriction was REVERTED. `git add plain.txt && git
    # commit` now warns again -- a tolerated false positive. That is deliberate: inferring
    # what an unrun command will stage produced four silent misses (M5), and this hook's
    # cost asymmetry says noise beats silence. Asserting the FP explicitly so a future
    # "improvement" that re-suppresses it has to argue with this test first.
    rc, ctx, dec = run_guard("git add plain.txt && git commit -m x", repo)
    check("E-m11a narrow add: warns anyway (accepted FP, not suppressed)",
          "modified:" in ctx, "ctx=%r" % ctx[:250])
    rc, ctx, dec = run_guard("git add -A && git commit -m x", repo)
    check("E-m11b whole-tree add still warns", "modified:" in ctx, "ctx=%r" % ctx[:250])
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# subshell (nit): `(git commit -m x)` should now be visible.
tmp = tempfile.mkdtemp()
try:
    repo, _ = make_repo(tmp)
    rc, ctx, dec = run_guard("(git commit -m x)", repo)
    check("E-n1 subshell commit detected", "BRANCH" in ctx.upper(), "ctx=%r" % ctx[:200])
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print("== F. round-3: the four M5 false negatives (must all FIRE) ==")


def _stale_repo(tmp):
    repo, mem = make_repo(tmp)
    write_mem(mem, "body v2", "2026-01-01T00:00:00.000Z")  # dirty + stale stamp
    return repo, mem


for label, cmd, stage_first in [
    ("F-M5a glob add (shell-expanded) still warns", "git add memory/*.md && git commit -m x", False),
    ("F-M5b add + commit -am still warns", "git add plain.txt && git commit -am x", False),
    ("F-M5c -A then narrow add still warns", "git add -A && git add plain.txt && git commit -m x", False),
    ("F-M5d trailing '# ... -- ...' comment does not suppress",
     'git commit -m "fix thing" # cleanup -- see notes', True),
]:
    tmp = tempfile.mkdtemp()
    try:
        repo, mem = _stale_repo(tmp)
        if stage_first:
            git(repo, "add", "-A")
        rc, ctx, dec = run_guard(cmd, repo)
        check(label, "modified:" in ctx, "ctx=%r" % ctx[:250])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

# m12 -- shell keyword wrappers must not hide the segment head.
tmp = tempfile.mkdtemp()
try:
    repo, _ = make_repo(tmp)
    rc, ctx, dec = run_guard("if true; then git commit -m x; fi", repo)
    check("F-m12 if/then wrapper detected", "BRANCH" in ctx.upper(), "ctx=%r" % ctx[:200])
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# Guard against over-reverting: a REAL pathspec must still restrict.
tmp = tempfile.mkdtemp()
try:
    repo, mem = _stale_repo(tmp)
    with open(os.path.join(repo, "plain.txt"), "w", encoding="utf-8") as fh:
        fh.write("changed\n")
    rc, ctx, dec = run_guard("git commit -m x -- plain.txt", repo)
    check("F-p1 explicit pathspec still restricts", "modified:" not in ctx,
          "ctx=%r" % ctx[:250])
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print("== G. round-4: quote-blind '#' truncation (M6, both directions) ==")

# FN direction: a quoted message STARTING with '#' must not eat the trailing -a.
tmp = tempfile.mkdtemp()
try:
    repo, mem = make_repo(tmp)
    write_mem(mem, "body v2", "2026-01-01T00:00:00.000Z")  # stale, UNSTAGED
    rc, ctx, dec = run_guard('git commit -m "#123 fix" -a', repo)
    check("G-M6a quoted '#'-leading message keeps -a (warns)", "modified:" in ctx,
          "ctx=%r" % ctx[:250])
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# FP direction: the same message must not eat a REAL pathspec.
tmp = tempfile.mkdtemp()
try:
    repo, mem = make_repo(tmp)
    write_mem(mem, "body v2", "2026-01-01T00:00:00.000Z")
    with open(os.path.join(repo, "plain.txt"), "w", encoding="utf-8") as fh:
        fh.write("changed\n")
    git(repo, "add", "-A")
    rc, ctx, dec = run_guard('git commit -m "#123 fix" -- plain.txt', repo)
    check("G-M6b quoted '#'-leading message keeps the real pathspec (silent)",
          "modified:" not in ctx, "ctx=%r" % ctx[:250])
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# The genuine comment shape must STILL be truncated (guard against over-correcting M6).
tmp = tempfile.mkdtemp()
try:
    repo, mem = make_repo(tmp)
    write_mem(mem, "body v2", "2026-01-01T00:00:00.000Z")
    git(repo, "add", "-A")
    rc, ctx, dec = run_guard('git commit -m "fix thing" # cleanup -- see notes', repo)
    check("G-M6c real trailing comment still truncated (warns)", "modified:" in ctx,
          "ctx=%r" % ctx[:250])
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print("== C. fail-open ==")
p = subprocess.run([PY, GUARD], input="not json at all", capture_output=True, text=True,
                   env=_clean_env())
check("C1 garbage stdin -> exit 0, no crash", p.returncode == 0, "rc=%s" % p.returncode)

tmp = tempfile.mkdtemp()
try:
    rc, ctx, dec = run_guard("git commit -m x", tmp)  # not a git repo
    check("C2 non-repo cwd -> exit 0, silent", rc == 0 and ctx == "",
          "rc=%s ctx=%r" % (rc, ctx[:120]))
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print("== H. unscoped-stage advisory (GAP C, 2026-08-21) ==")

tmp = tempfile.mkdtemp()
try:
    repo, _ = make_repo(tmp)
    with open(os.path.join(repo, "plain.txt"), "w", encoding="utf-8") as fh:
        fh.write("changed\n")
    git(repo, "add", "-A")
    rc, ctx, dec = run_guard("git commit -m x", repo)
    check("H1 plain commit of pre-staged files: no unscoped warning",
          "UNSCOPED" not in ctx, "ctx=%r" % ctx[:250])
finally:
    shutil.rmtree(tmp, ignore_errors=True)

for label, cmd in [
    ("H2 add -A && commit: warns UNSCOPED", "git add -A && git commit -m x"),
    ("H3 commit -am: warns UNSCOPED", "git commit -am x"),
    ("H4 add . && commit: warns UNSCOPED", "git add . && git commit -m x"),
    ("H5 commit --all: warns UNSCOPED", "git commit --all -m x"),
]:
    tmp = tempfile.mkdtemp()
    try:
        repo, _ = make_repo(tmp)
        with open(os.path.join(repo, "plain.txt"), "w", encoding="utf-8") as fh:
            fh.write("changed\n")
        rc, ctx, dec = run_guard(cmd, repo)
        check(label, "UNSCOPED" in ctx, "ctx=%r" % ctx[:300])
        check(label + " (still warn-only)", rc == 0 and dec != "deny",
              "rc=%s dec=%s" % (rc, dec))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

tmp = tempfile.mkdtemp()
try:
    repo, _ = make_repo(tmp)
    with open(os.path.join(repo, "plain.txt"), "w", encoding="utf-8") as fh:
        fh.write("changed\n")
    git(repo, "add", "-A")
    rc, ctx, dec = run_guard("git commit -m x -- plain.txt", repo)
    check("H6 add -A but commit itself has an explicit pathspec: silent",
          "UNSCOPED" not in ctx, "ctx=%r" % ctx[:300])
finally:
    shutil.rmtree(tmp, ignore_errors=True)

tmp = tempfile.mkdtemp()
try:
    repo, _ = make_repo(tmp)
    with open(os.path.join(repo, "plain.txt"), "w", encoding="utf-8") as fh:
        fh.write("changed\n")
    rc, ctx, dec = run_guard("git add plain.txt && git commit -m x", repo)
    check("H7 explicit named-file add (no sweep flag): silent",
          "UNSCOPED" not in ctx, "ctx=%r" % ctx[:300])
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# H8 -- independent-review finding (2026-08-21): a sweep `add` AFTER the commit it
# follows in the same compound command must NOT taint that earlier commit. sweep_add
# is snapshotted into `found` at the moment each commit segment is parsed, matching the
# existing "later commit wins" ordering rule -- not accumulated blindly across the whole
# command the way the pre-fix version did.
tmp = tempfile.mkdtemp()
try:
    repo, _ = make_repo(tmp)
    rc, ctx, dec = run_guard("git commit -m x && git add -A", repo)
    check("H8 sweep add AFTER the commit: no false UNSCOPED warning",
          "UNSCOPED" not in ctx, "ctx=%r" % ctx[:300])
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# H9 -- the three sweep tokens not covered by H2-H5 (-u, --update, --no-ignore-removal).
for label, cmd in [
    ("H9a add -u && commit: warns UNSCOPED", "git add -u && git commit -m x"),
    ("H9b add --update && commit: warns UNSCOPED", "git add --update && git commit -m x"),
    ("H9c add --no-ignore-removal && commit: warns UNSCOPED",
     "git add --no-ignore-removal && git commit -m x"),
]:
    tmp = tempfile.mkdtemp()
    try:
        repo, _ = make_repo(tmp)
        with open(os.path.join(repo, "plain.txt"), "w", encoding="utf-8") as fh:
            fh.write("changed\n")
        rc, ctx, dec = run_guard(cmd, repo)
        check(label, "UNSCOPED" in ctx, "ctx=%r" % ctx[:300])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

# H10 -- newline-separated form (matches the existing E-M4 newline coverage pattern).
tmp = tempfile.mkdtemp()
try:
    repo, _ = make_repo(tmp)
    with open(os.path.join(repo, "plain.txt"), "w", encoding="utf-8") as fh:
        fh.write("changed\n")
    rc, ctx, dec = run_guard("git add -A\ngit commit -m x", repo)
    check("H10 newline-separated add -A / commit: warns UNSCOPED",
          "UNSCOPED" in ctx, "ctx=%r" % ctx[:300])
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# H11 -- independent-review finding (PR #142, Qodo): `add -A -- <pathspec>` is SCOPED by
# its own pathspec in real git -- -A only means "the whole tree" absent a pathspec on the
# add itself. Must NOT be read as a sweep.
tmp = tempfile.mkdtemp()
try:
    repo, _ = make_repo(tmp)
    with open(os.path.join(repo, "plain.txt"), "w", encoding="utf-8") as fh:
        fh.write("changed\n")
    rc, ctx, dec = run_guard("git add -A -- plain.txt && git commit -m x", repo)
    check("H11 add -A scoped by its OWN pathspec: silent",
          "UNSCOPED" not in ctx, "ctx=%r" % ctx[:300])
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# H12 -- independent-review finding (PR #142, Qodo): a sweep add in ONE repo must not
# taint a commit in a DIFFERENT repo reached via `-C`.
tmpA, tmpB = tempfile.mkdtemp(), tempfile.mkdtemp()
try:
    repoA, _ = make_repo(tmpA)
    repoB, _ = make_repo(tmpB)
    with open(os.path.join(repoB, "plain.txt"), "w", encoding="utf-8") as fh:
        fh.write("changed\n")
    cmd = 'git -C "%s" add -A && git -C "%s" commit -m x' % (repoA, repoB)
    rc, ctx, dec = run_guard(cmd, repoA)
    check("H12 cross-repo sweep add does not taint a different repo's commit",
          "UNSCOPED" not in ctx, "ctx=%r" % ctx[:300])
finally:
    shutil.rmtree(tmpA, ignore_errors=True)
    shutil.rmtree(tmpB, ignore_errors=True)

# H13 -- guard against over-correcting H11/H12: a SAME-repo sweep add must still warn.
tmp = tempfile.mkdtemp()
try:
    repo, _ = make_repo(tmp)
    with open(os.path.join(repo, "plain.txt"), "w", encoding="utf-8") as fh:
        fh.write("changed\n")
    rc, ctx, dec = run_guard('git -C "%s" add -A && git -C "%s" commit -m x' % (repo, repo),
                             repo)
    check("H13 same-repo -C add/commit still warns UNSCOPED",
          "UNSCOPED" in ctx, "ctx=%r" % ctx[:300])
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print("")
if FAILS:
    print("FAILED: %d" % len(FAILS))
    sys.exit(1)
print("all commit-hygiene-guard tests passed")
