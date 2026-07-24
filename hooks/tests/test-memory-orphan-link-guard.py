"""Standalone test for hooks/memory-orphan-link-guard.py. Builds a throwaway git repo
that mimics the memory/ layout, then drives the guard via stdin exactly as the harness does.
"""
import json, os, shutil, subprocess, sys, tempfile

# Resolved from THIS file's location, not hardcoded to the live tree: a worktree copy must
# test the guard IT is about to land, not whatever is already deployed. (Was an absolute
# live path, so worktree runs silently exercised the deployed guard instead.)
GUARD = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "memory-orphan-link-guard.py")
PY = sys.executable

def git(repo, *a):
    return subprocess.run(("git",)+a, cwd=repo, capture_output=True, text=True)

def run_guard(cmd, index_path, tool="Bash"):
    payload = {"tool_name": tool, "tool_input": {"command": cmd}}
    env = dict(os.environ, ORA_MEMORY_INDEX=index_path)
    p = subprocess.run([PY, GUARD], input=json.dumps(payload).encode("utf-8"),
                       capture_output=True, env=env)
    out = p.stdout.decode("utf-8", "replace").strip()
    if p.returncode != 0:
        return "NONZERO_EXIT", out
    if not out:
        return "ALLOW", ""
    try:
        d = json.loads(out)
        return d["hookSpecificOutput"]["permissionDecision"].upper(), \
               d["hookSpecificOutput"]["permissionDecisionReason"]
    except Exception:
        return "UNPARSEABLE", out

def setup():
    root = tempfile.mkdtemp(prefix="orphan-guard-")
    mem = os.path.join(root, "projects", "proj", "memory")
    os.makedirs(mem)
    git(root, "init", "-q")
    git(root, "config", "user.email", "t@t.t")
    git(root, "config", "user.name", "t")
    # committed baseline: index + one body, both in HEAD
    with open(os.path.join(mem, "good.md"), "w", encoding="utf-8") as f:
        f.write("body\n")
    with open(os.path.join(mem, "MEMORY.md"), "w", encoding="utf-8") as f:
        f.write("# Index\n- [Good](good.md) - hook\n")
    git(root, "add", "-A"); git(root, "commit", "-qm", "base")
    return root, mem

results = []
def check(name, got, want):
    ok = got == want
    results.append(ok)
    print(("  PASS  " if ok else "  FAIL  ") + name + ("" if ok else f"   (got {got}, want {want})"))

root, mem = setup()
IDX = os.path.join(mem, "MEMORY.md").replace("\\", "/")

print("== baseline: clean index, MEMORY.md not staged ==")
check("plain commit, nothing staged", run_guard("git commit -m x", IDX)[0], "ALLOW")

print("== the real defect: index line staged, body untracked ==")
with open(os.path.join(mem, "MEMORY.md"), "a", encoding="utf-8") as f:
    f.write("- [Orphan](orphan.md) - hook\n")
with open(os.path.join(mem, "orphan.md"), "w", encoding="utf-8") as f:
    f.write("body\n")   # exists on disk, NOT staged
git(root, "add", "projects/proj/memory/MEMORY.md")
d, reason = run_guard("git commit -m x", IDX)
check("staged index + untracked body -> DENY", d, "DENY")
if d == "DENY":
    print("       reason mentions git add:", "git add" in reason)
    print("       names the body        :", "orphan.md" in reason)

print("== fixed by staging the body in the same commit ==")
git(root, "add", "projects/proj/memory/orphan.md")
check("body staged too -> ALLOW", run_guard("git commit -m x", IDX)[0], "ALLOW")
git(root, "commit", "-qm", "landed")

print("== link to a file that does not exist at all ==")
with open(os.path.join(mem, "MEMORY.md"), "a", encoding="utf-8") as f:
    f.write("- [Typo](nope_typo.md) - hook\n")
git(root, "add", "projects/proj/memory/MEMORY.md")
d, reason = run_guard("git commit -m x", IDX)
check("dangling link -> DENY", d, "DENY")
if d == "DENY":
    print("       flagged as absent:", "Not on disk at all" in reason)

print("== scope: must not fire on unrelated commands ==")
check("non-commit git",       run_guard("git status", IDX)[0], "ALLOW")
check("git log --grep=commit",run_guard("git log --grep=commit", IDX)[0], "ALLOW")
check("echo mentioning commit", run_guard('echo "remember to commit"', IDX)[0], "ALLOW")
check("non-Bash tool",        run_guard("git commit -m x", IDX, tool="Edit")[0], "ALLOW")
check("compound && git commit", run_guard("cd /x && git commit -m y", IDX)[0], "DENY")
check("git -c KEY=VAL commit", run_guard("git -c user.name=z commit -m y", IDX)[0], "DENY")
check("git -C path commit",   run_guard("git -C /some/repo commit -m y", IDX)[0], "DENY")
check("git --git-dir=x commit", run_guard("git --git-dir=/x commit -m y", IDX)[0], "DENY")
check("git --work-tree t commit", run_guard("git --work-tree /t commit -m y", IDX)[0], "DENY")
check("abs path to git",      run_guard("/usr/bin/git commit -m y", IDX)[0], "DENY")
check("git config commit.tmpl", run_guard("git config --get commit.template", IDX)[0], "ALLOW")
check("git -c x=y log grep",  run_guard("git -c a=b log --grep=commit", IDX)[0], "ALLOW")
check("git commit-tree (not commit)", run_guard("git commit-tree abc", IDX)[0], "ALLOW")

print("== MEMORY.md not in this commit -> silent ==")
git(root, "reset", "-q")
check("index unstaged -> ALLOW", run_guard("git commit -m x", IDX)[0], "ALLOW")

print("== fail-open on garbage ==")
p = subprocess.run([PY, GUARD], input=b"not json at all", capture_output=True)
check("garbage stdin exits 0", p.returncode, 0)
check("garbage stdin no output", p.stdout.decode().strip(), "")
p = subprocess.run([PY, GUARD], input=b"", capture_output=True)
check("empty stdin exits 0", p.returncode, 0)
env = dict(os.environ, ORA_MEMORY_INDEX="C:/nonexistent/nope/MEMORY.md")
p = subprocess.run([PY, GUARD], input=json.dumps(
    {"tool_name":"Bash","tool_input":{"command":"git commit -m x"}}).encode(),
    capture_output=True, env=env)
check("missing index file exits 0", p.returncode, 0)
check("missing index file allows", p.stdout.decode().strip(), "")

shutil.rmtree(root, ignore_errors=True)

# ===================================================================================
# PreToolUse TIMING (2026-07-24). A PreToolUse hook inspects the index BEFORE the
# command runs, so for a COMPOUND command the guard judged a state the command was
# about to change. Two opposite failure modes, verified against the live guard:
#   * FALSE NEGATIVE (the dangerous one): `git add MEMORY.md && git commit` -- at hook
#     time MEMORY.md is unstaged, the guard returns "not our business", and the orphan
#     links land unchecked. This is a straight BYPASS of the guard.
#   * FALSE POSITIVE: `git restore --staged MEMORY.md && git commit` -- at hook time it
#     IS staged, so the guard blocks a commit that would not have included it.
# Fix: derive whether MEMORY.md ends up in the commit by walking the command's segments
# in order, instead of trusting the pre-command index.
# ===================================================================================
print()
print("== PreToolUse timing: compound commands ==")
root2, mem2 = setup()
IDX2 = os.path.join(mem2, "MEMORY.md").replace("\\", "/")


def set_orphan_index():
    """Working-tree MEMORY.md links a body that is neither in HEAD nor staged."""
    with open(os.path.join(mem2, "MEMORY.md"), "w", encoding="utf-8") as f:
        f.write("# Index\n- [Good](good.md) - hook\n- [New](new.md) - orphan\n")
    with open(os.path.join(mem2, "new.md"), "w", encoding="utf-8") as f:
        f.write("body\n")


MEMREL = "projects/proj/memory/MEMORY.md"

# --- the BYPASS: stage-then-commit in one command ---
set_orphan_index()
git(root2, "reset", "-q")           # nothing staged at hook time
check("BYPASS: `git add MEMORY.md && git commit` must DENY",
      run_guard('git add "%s" && git commit -m x' % MEMREL, IDX2)[0], "DENY")
check("BYPASS: `git add -A && git commit` must DENY",
      run_guard("git add -A && git commit -m x", IDX2)[0], "DENY")
check("BYPASS: `git add . && git commit` must DENY",
      run_guard("git add . && git commit -m x", IDX2)[0], "DENY")
check("BYPASS: `git commit -am` stages tracked files, must DENY",
      run_guard("git commit -am x", IDX2)[0], "DENY")
check("BYPASS: `git add -u && git commit` must DENY",
      run_guard("git add -u && git commit -m x", IDX2)[0], "DENY")

# --- the FALSE POSITIVE: unstage-then-commit in one command ---
git(root2, "add", MEMREL)           # staged at hook time...
check("FP: `git restore --staged MEMORY.md && git commit` must ALLOW",
      run_guard('git restore --staged "%s" && git commit -m x' % MEMREL, IDX2)[0], "ALLOW")
check("FP: `git reset HEAD MEMORY.md && git commit` must ALLOW",
      run_guard('git reset HEAD "%s" && git commit -m x' % MEMREL, IDX2)[0], "ALLOW")

# --- the narrowing must NOT open a hole: -a re-stages what was just unstaged ---
check("unstage then `commit -a` still DENY (-a re-stages it)",
      run_guard('git restore --staged "%s" && git commit -am x' % MEMREL, IDX2)[0], "DENY")
check("unstage then re-add still DENY",
      run_guard('git restore --staged "%s" && git add "%s" && git commit -m x'
                % (MEMREL, MEMREL), IDX2)[0], "DENY")

# --- unrelated paths must not change the verdict ---
git(root2, "reset", "-q")
check("adding an UNRELATED path then committing stays ALLOW",
      run_guard('git add "projects/proj/memory/good.md" && git commit -m x', IDX2)[0], "ALLOW")

# --- a clean index (no orphan) must stay ALLOW through all of it ---
with open(os.path.join(mem2, "MEMORY.md"), "w", encoding="utf-8") as f:
    f.write("# Index\n- [Good](good.md) - hook\n")
check("no orphan link -> add-then-commit ALLOW",
      run_guard("git add -A && git commit -m x", IDX2)[0], "ALLOW")

shutil.rmtree(root2, ignore_errors=True)

# ===================================================================================
# PATHSPEC EXCLUSIVITY (2026-07-24). `git commit -- <pathspec>` is EXCLUSIVE: only the
# named paths land, no matter what else is staged in the index -- verified directly:
#   `git add A.md B.md; git commit -m x -- A.md` commits ONLY A.md; B.md stays staged,
#   untouched. `git commit -a -- A.md` is a hard git error ("does not make sense") and
#   never commits at all -- so -a can never smuggle an unnamed file past a pathspec.
# Bug: _commit_would_include() seeded `included` from `staged_now` (is MEMORY.md
# anywhere in the CURRENT shared index) even when a `--` pathspec was present and did
# not name MEMORY.md. In a shared checkout another session's unrelated `git add` on
# MEMORY.md left it sitting staged, and a plain `git commit -- other/file.md` -- which
# cannot possibly touch MEMORY.md -- was DENIED anyway.
# ===================================================================================
print()
print("== pathspec exclusivity: staged-elsewhere must not leak into a pathspec commit ==")
root3, mem3 = setup()
IDX3 = os.path.join(mem3, "MEMORY.md").replace("\\", "/")
MEMREL3 = "projects/proj/memory/MEMORY.md"

with open(os.path.join(mem3, "other.md"), "w", encoding="utf-8") as f:
    f.write("unrelated tracked file\n")
git(root3, "add", "projects/proj/memory/other.md")
git(root3, "commit", "-qm", "add other.md")

with open(os.path.join(mem3, "MEMORY.md"), "a", encoding="utf-8") as f:
    f.write("- [Orphan](orphan3.md) - hook\n")
with open(os.path.join(mem3, "orphan3.md"), "w", encoding="utf-8") as f:
    f.write("body, not staged\n")
with open(os.path.join(mem3, "other.md"), "w", encoding="utf-8") as f:
    f.write("unrelated edit\n")
git(root3, "add", MEMREL3)                        # MEMORY.md staged by "another session"
git(root3, "add", "projects/proj/memory/other.md")  # other.md also modified+staged

check("pathspec naming an UNRELATED file, MEMORY.md staged elsewhere -> ALLOW",
      run_guard('git commit -m x -- "projects/proj/memory/other.md"', IDX3)[0], "ALLOW")

check("pathspec explicitly naming MEMORY.md (relpath) -> still DENY",
      run_guard('git commit -m x -- "%s"' % MEMREL3, IDX3)[0], "DENY")

check("pathspec naming MEMORY.md by bare basename -> still DENY",
      run_guard('git commit -m x -- "MEMORY.md"', IDX3)[0], "DENY")

check("pathspec naming BOTH files (one is MEMORY.md) -> still DENY",
      run_guard('git commit -m x -- "%s" "projects/proj/memory/other.md"' % MEMREL3, IDX3)[0],
      "DENY")

# clean index (no orphan) behind an unrelated pathspec must stay ALLOW throughout
git(root3, "checkout", "--", MEMREL3)
git(root3, "add", MEMREL3)
check("no orphan link, pathspec unrelated -> ALLOW",
      run_guard('git commit -m x -- "projects/proj/memory/other.md"', IDX3)[0], "ALLOW")

shutil.rmtree(root3, ignore_errors=True)

# ===================================================================================
# REFUTE PASS (2026-07-24). A first version of the pathspec carve-out above trusted
# ANY "--" found via the naive .split() used elsewhere in this file, including one
# sitting INSIDE a quoted commit message ("fix -- bug", "notes -- see PR" are ordinary
# things to write). That reopened the exact bypass the 12:54 same-day fix closed, just
# behind a decoy message instead of a bare `git add && git commit`. Verified live
# before the shlex fix: all three attacks below got ALLOW. Only a shlex-tokenized
# (quote-aware) standalone `--` may now be trusted as a real pathspec separator.
# ===================================================================================
print()
print("== REFUTE: a decoy ' -- ' inside the commit message must not fake a pathspec ==")
root4, mem4 = setup()
IDX4 = os.path.join(mem4, "MEMORY.md").replace("\\", "/")
MEMREL4 = "projects/proj/memory/MEMORY.md"

with open(os.path.join(mem4, "MEMORY.md"), "a", encoding="utf-8") as f:
    f.write("- [Orphan](orphan4.md) - hook\n")
with open(os.path.join(mem4, "orphan4.md"), "w", encoding="utf-8") as f:
    f.write("body, not staged\n")

git(root4, "reset", "-q")
check('BYPASS ATTEMPT: add-then-commit, double-quoted msg has " -- " -> DENY',
      run_guard('git add "%s" && git commit -m "fix -- bug"' % MEMREL4, IDX4)[0], "DENY")

git(root4, "reset", "-q")
check('BYPASS ATTEMPT: `commit -am` with " -- " in the message -> DENY',
      run_guard('git commit -am "fix -- bug"', IDX4)[0], "DENY")

git(root4, "reset", "-q")
check("BYPASS ATTEMPT: single-quoted message containing ' -- ' -> DENY",
      run_guard("git add \"%s\" && git commit -m 'fix -- bug'" % MEMREL4, IDX4)[0], "DENY")

git(root4, "reset", "-q")
check("unbalanced quoting -> shlex fails, must not fail OPEN -> DENY",
      run_guard('git add "%s" && git commit -m "unbalanced \\"quote' % MEMREL4, IDX4)[0],
      "DENY")

# a REAL trailing pathspec must still correctly exclude, even with a decoy " -- "
# earlier in the same segment's (quoted) commit message.
with open(os.path.join(mem4, "other4.md"), "w", encoding="utf-8") as f:
    f.write("tracked\n")
git(root4, "add", "projects/proj/memory/other4.md")
git(root4, "commit", "-qm", "add other4")
with open(os.path.join(mem4, "other4.md"), "w", encoding="utf-8") as f:
    f.write("edit\n")
git(root4, "reset", "-q")
check("decoy ' -- ' in message, but a REAL trailing pathspec still wins -> ALLOW",
      run_guard('git add "%s" && git commit -m "notes -- decoy" -- '
                '"projects/proj/memory/other4.md"' % MEMREL4, IDX4)[0], "ALLOW")

shutil.rmtree(root4, ignore_errors=True)

# ===================================================================================
# CODE REVIEW FINDINGS (2026-07-24). Local review of the pathspec-exclusivity commit
# above caught two further bypasses in that commit's OWN shlex-based "--" scan, both
# verified end-to-end through this guard binary against real git before being closed
# by _commit_pathspec()'s option-aware walk:
#   * `git commit -m --`: `-m`'s value IS the literal string "--". A bare "is '--' a
#     token" scan finds it and reads an EMPTY pathspec after it, which _mentions_path
#     reports False for -- silently EXCLUDING MEMORY.md from a commit that (per real
#     git) actually commits the WHOLE staged index. Real git verified: exit 0, message
#     "--", the orphaned MEMORY.md lands.
#   * `git commit -m x --` (normal message, bare trailing "--", nothing after it): real
#     git treats an empty pathspec as NO restriction, not "matches nothing" -- it
#     commits the entire staged index. Real git verified: exit 0, full index committed.
# ===================================================================================
print()
print("== CODE REVIEW: empty-pathspec shapes must not fake an exclusion ==")
root5, mem5 = setup()
IDX5 = os.path.join(mem5, "MEMORY.md").replace("\\", "/")
MEMREL5 = "projects/proj/memory/MEMORY.md"

with open(os.path.join(mem5, "MEMORY.md"), "a", encoding="utf-8") as f:
    f.write("- [Orphan](orphan5.md) - hook\n")
with open(os.path.join(mem5, "orphan5.md"), "w", encoding="utf-8") as f:
    f.write("body, not staged\n")

git(root5, "add", MEMREL5)
check('CRITICAL #1: `git commit -m --` (message IS "--") -> DENY',
      run_guard("git commit -m --", IDX5)[0], "DENY")

git(root5, "add", MEMREL5)
check('CRITICAL #2: `git commit -m x --` (bare trailing "--", empty tail) -> DENY',
      run_guard("git commit -m x --", IDX5)[0], "DENY")

# same two shapes must still ALLOW when there is genuinely no orphan
with open(os.path.join(mem5, "MEMORY.md"), "w", encoding="utf-8") as f:
    f.write("# Index\n- [Good](good.md) - hook\n")
git(root5, "add", MEMREL5)
check("no orphan link -> `git commit -m --` stays ALLOW",
      run_guard("git commit -m --", IDX5)[0], "ALLOW")

shutil.rmtree(root5, ignore_errors=True)

# a genuine trailing pathspec after -m's value must still correctly EXCLUDE
print()
print("== value-consuming options: a REAL trailing pathspec after them still excludes ==")
root6, mem6 = setup()
IDX6 = os.path.join(mem6, "MEMORY.md").replace("\\", "/")
MEMREL6 = "projects/proj/memory/MEMORY.md"

with open(os.path.join(mem6, "other6.md"), "w", encoding="utf-8") as f:
    f.write("tracked\n")
git(root6, "add", "projects/proj/memory/other6.md")
git(root6, "commit", "-qm", "add other6")
with open(os.path.join(mem6, "MEMORY.md"), "a", encoding="utf-8") as f:
    f.write("- [Orphan](orphan6.md) - hook\n")
with open(os.path.join(mem6, "orphan6.md"), "w", encoding="utf-8") as f:
    f.write("body, not staged\n")
with open(os.path.join(mem6, "other6.md"), "w", encoding="utf-8") as f:
    f.write("edit\n")
git(root6, "add", MEMREL6, "projects/proj/memory/other6.md")
check('`git commit -m x -- other.md` (real pathspec after -m) -> ALLOW '
      "(cannot touch MEMORY.md even though it's staged)",
      run_guard('git commit -m x -- "projects/proj/memory/other6.md"', IDX6)[0], "ALLOW")

shutil.rmtree(root6, ignore_errors=True)
print()
print(f"RESULT: {sum(results)}/{len(results)} passed")
sys.exit(0 if all(results) else 1)
