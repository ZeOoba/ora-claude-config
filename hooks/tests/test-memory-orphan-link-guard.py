"""Standalone test for hooks/memory-orphan-link-guard.py. Builds a throwaway git repo
that mimics the memory/ layout, then drives the guard via stdin exactly as the harness does.
"""
import json, os, shutil, subprocess, sys, tempfile

# This test spins up its own throwaway git repos in temp dirs. When invoked as part of
# the real pre-push hook chain, git sets GIT_DIR/GIT_WORK_TREE/GIT_INDEX_FILE (etc.) in
# this process's environment so IT can operate on the outer repo -- but those same vars
# leak into every subprocess git call below and silently redirect them at the outer repo
# instead of the temp one, breaking git operations against the temp fixtures.
for _v in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR",
           "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_PREFIX"):
    os.environ.pop(_v, None)

# Resolved from THIS file's location, not hardcoded to the live tree: a worktree copy must
# test the guard IT is about to land, not whatever is already deployed. (Was an absolute
# live path, so worktree runs silently exercised the deployed guard instead.)
GUARD = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "memory-orphan-link-guard.py")
PY = sys.executable

def git(repo, *a):
    return subprocess.run(("git",)+a, cwd=repo, capture_output=True, text=True)

def run_guard(cmd, index_path, tool="Bash", cwd=None):
    # Real harness usage ALWAYS populates payload["cwd"] with wherever the Bash command
    # actually runs. Default it here to the directory holding `index_path` itself (i.e.
    # THIS test's own throwaway repo) -- matching the implicit assumption nearly every
    # test below relies on ("this commit runs in the same repo as its target MEMORY.md").
    # Callers that need to simulate a DIFFERENT target repo (cross-repo / worktree
    # tests) pass cwd explicitly and override this.
    if cwd is None:
        cwd = os.path.dirname(index_path)
    payload = {"tool_name": tool, "tool_input": {"command": cmd}, "cwd": cwd}
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
check("compound && git commit",
      run_guard('cd "%s" && git commit -m y' % root, IDX)[0], "DENY")
check("git -c KEY=VAL commit", run_guard("git -c user.name=z commit -m y", IDX)[0], "DENY")
check("git -C path commit",
      run_guard('git -C "%s" commit -m y' % root, IDX)[0], "DENY")
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
# CONTRACT CHANGE (2026-07-24, torn-segment fix -- see the REPO RESOLUTION REFUTE
# section below for the vulnerability this closed). This used to expect DENY: the OLD
# per-segment-tolerant design let the well-formed `add` segment parse successfully even
# though the LATER `commit` segment's quoting was broken, so it still caught the real
# stage. That per-piece tolerance is EXACTLY the property the torn-segment attack
# exploited (a crafted quoted value can tear across the raw split into fragments that
# EACH parse "successfully" alone, fabricating segments that never existed). The fix
# tokenizes the WHOLE command with shlex ONCE; if ANY of it fails to parse, the ENTIRE
# command is untrustworthy and the guard falls back to staged_now unchanged (here:
# nothing was staged before this command ran, so ALLOW) -- consistent with this file's
# own stated SAFETY INVARIANT ("exits 0 (ALLOW) on ANY error"). Not a new hole: text a
# real shell also cannot parse (an unterminated quote) cannot execute as a real command
# either, so there is no actual commit for the guard to have missed.
check("unbalanced quoting -> whole command untrustworthy -> falls back to ALLOW",
      run_guard('git add "%s" && git commit -m "unbalanced \\"quote' % MEMREL4, IDX4)[0],
      "ALLOW")

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

# ===================================================================================
# SECOND REVIEW ROUND (2026-07-24). _has_pathspec(cmd) -- a SEPARATE naive
# `re.search(r"\s--\s", cmd)` scan used by main() to pick working-tree-vs-index content
# -- was never touched by the _commit_pathspec fix above, and had the IDENTICAL
# decoy-quote weakness. Live-verified bypass: stage an orphaned MEMORY.md, then revert
# ONLY the working-tree copy back to clean (index still holds the orphan -- an ordinary
# shared-checkout divergence), then `git commit -m "fix -- bug"` (a PLAIN staged
# commit, no real pathspec). The decoy " -- " made _has_pathspec wrongly return True,
# so main() read the CLEAN working-tree copy instead of the ORPHANED index content real
# git was about to commit -- ALLOW, and the orphan landed for real. Fixed by deleting
# _has_pathspec entirely: `from_worktree`, returned by the already-quote-aware
# _commit_would_include, is the single correct source of truth for this decision.
# ===================================================================================
print()
print("== SECOND REVIEW: disk/index divergence must not hide behind a decoy ' -- ' ==")
root7, mem7 = setup()
IDX7 = os.path.join(mem7, "MEMORY.md").replace("\\", "/")
MEMREL7 = "projects/proj/memory/MEMORY.md"

clean_content = "# Index\n- [Good](good.md) - hook\n"
orphan_content = clean_content + "- [Orphan](orphan7.md) - hook\n"
with open(os.path.join(mem7, "orphan7.md"), "w", encoding="utf-8") as f:
    f.write("body, not staged\n")

# stage the ORPHANED version...
with open(os.path.join(mem7, "MEMORY.md"), "w", encoding="utf-8") as f:
    f.write(orphan_content)
git(root7, "add", MEMREL7)
# ...then revert ONLY the working tree back to clean -- index still holds the orphan.
with open(os.path.join(mem7, "MEMORY.md"), "w", encoding="utf-8") as f:
    f.write(clean_content)

check("staged=orphan, worktree=clean, decoy ' -- ' in message, plain commit -> DENY",
      run_guard('git commit -m "fix -- bug"', IDX7)[0], "DENY")

shutil.rmtree(root7, ignore_errors=True)

# `-am --` previously DENY'd only by luck (an unrelated -a-substring heuristic catching
# it, not by design) -- lock the behavior in explicitly.
print()
print("== lock in `-am --` (combined short flags) behavior explicitly ==")
root8, mem8 = setup()
IDX8 = os.path.join(mem8, "MEMORY.md").replace("\\", "/")
with open(os.path.join(mem8, "MEMORY.md"), "a", encoding="utf-8") as f:
    f.write("- [Orphan](orphan8.md) - hook\n")
with open(os.path.join(mem8, "orphan8.md"), "w", encoding="utf-8") as f:
    f.write("body, not staged\n")
git(root8, "reset", "-q")
check("`git commit -am --` (message is '--', -a stages tracked mods incl. MEMORY.md) -> DENY",
      run_guard("git commit -am --", IDX8)[0], "DENY")
shutil.rmtree(root8, ignore_errors=True)

# extended _COMMIT_VALUE_OPTS: --cleanup and --pathspec-from-file also consume a value.
print()
print("== extended _COMMIT_VALUE_OPTS: --cleanup / --pathspec-from-file swallow their value ==")
root9, mem9 = setup()
IDX9 = os.path.join(mem9, "MEMORY.md").replace("\\", "/")
MEMREL9 = "projects/proj/memory/MEMORY.md"
with open(os.path.join(mem9, "MEMORY.md"), "a", encoding="utf-8") as f:
    f.write("- [Orphan](orphan9.md) - hook\n")
with open(os.path.join(mem9, "orphan9.md"), "w", encoding="utf-8") as f:
    f.write("body, not staged\n")

git(root9, "add", MEMREL9)
check("`git commit -m x --cleanup --` (bare trailing tail after swallowed value) -> DENY",
      run_guard("git commit -m x --cleanup --", IDX9)[0], "DENY")

git(root9, "add", MEMREL9)
check("`git commit -m x --pathspec-from-file --` (same, other flag) -> DENY",
      run_guard("git commit -m x --pathspec-from-file --", IDX9)[0], "DENY")

shutil.rmtree(root9, ignore_errors=True)

# ===================================================================================
# REPO RESOLUTION (2026-07-24). main() resolved `repo` by walking UP from the
# hardcoded ORA_MEMORY_INDEX/DEFAULT_MEMORY_INDEX path -- NEVER from the command's
# actual cwd or target -- so a `git commit` running in a totally different repo (a
# worktree of the SAME repo, or an entirely UNRELATED one) was judged against the
# hardcoded repo's shared index. Live-verified during real use: a commit in an
# isolated worktree (its own clean index) was DENIED because the MAIN checkout had an
# unrelated orphaned MEMORY.md staged by another concurrent session, and separately a
# `git commit` in a scratch repo with no memory/ directory at all triggered the SAME
# guard. Fixed by resolving `repo` via the shared `repo_root(cmd, cwd)` helper (already
# used by commit-provenance-guard.py / eos-review-gate.py from hooks/lib/
# git_commit_parse.py: `git -C <p>` wins, else a leading `cd <p> &&`, else the
# PreToolUse payload's own `cwd` field) -- then bailing out if the RESOLVED repo does
# not even contain the canonical relative memory path, rather than assuming it must.
# ===================================================================================
print()
print("== REPO RESOLUTION: an unrelated repo must not be judged against the shared index ==")

# Repo A: simulates the "main checkout" -- ORA_MEMORY_INDEX points here, and it has a
# staged, ORPHANED MEMORY.md (another session's in-flight, unrelated work).
rootA, memA = setup()
IDXA = os.path.join(memA, "MEMORY.md").replace("\\", "/")
with open(os.path.join(memA, "MEMORY.md"), "a", encoding="utf-8") as f:
    f.write("- [Orphan](orphanA.md) - hook\n")
with open(os.path.join(memA, "orphanA.md"), "w", encoding="utf-8") as f:
    f.write("body, not staged\n")
git(rootA, "add", "projects/proj/memory/MEMORY.md")

# Repo B: a completely SEPARATE, unrelated repo (no memory/ directory at all).
rootB = tempfile.mkdtemp(prefix="unrelated-repo-")
git(rootB, "init", "-q")
git(rootB, "config", "user.email", "t@t.t")
git(rootB, "config", "user.name", "t")
with open(os.path.join(rootB, "readme.txt"), "w", encoding="utf-8") as f:
    f.write("unrelated project\n")
git(rootB, "add", "readme.txt")

check("commit in an UNRELATED repo (cwd=B) while repo A has an orphan staged -> ALLOW",
      run_guard("git commit -m x", IDXA, cwd=rootB)[0], "ALLOW")

check("sanity: the SAME orphaned staging, committed IN repo A itself -> still DENY",
      run_guard("git commit -m x", IDXA, cwd=rootA)[0], "DENY")

shutil.rmtree(rootA, ignore_errors=True)
shutil.rmtree(rootB, ignore_errors=True)

# ===================================================================================
# REPO RESOLUTION REFUTE (2026-07-24). A first version of _resolve_target_repo() used
# a raw `re.search` for `git -C <path>` / a leading `cd <path> &&` over the WHOLE
# command string -- the identical failure class already closed twice elsewhere in this
# file (_commit_pathspec, the removed _has_pathspec). A decoy inside an ordinary quoted
# commit message resolved to a nonexistent path, making the guard fail open. Verified
# live before the fix: `git commit -m "cd /nonexistent-decoy-path &&"` and `git commit
# -m "run: git -C /nonexistent-decoy commit"` both got ALLOW while genuinely staging an
# orphaned MEMORY.md. Closed with quote-aware (shlex), segment-scoped detection.
# ===================================================================================
print()
print("== REPO RESOLUTION REFUTE: decoys must not hijack repo resolution ==")
rootD, memD = setup()
IDXD = os.path.join(memD, "MEMORY.md").replace("\\", "/")
with open(os.path.join(memD, "MEMORY.md"), "a", encoding="utf-8") as f:
    f.write("- [OrphanD](orphanD.md) - hook\n")
with open(os.path.join(memD, "orphanD.md"), "w", encoding="utf-8") as f:
    f.write("body, not staged\n")
git(rootD, "add", "projects/proj/memory/MEMORY.md")

check('decoy "cd /nonexistent &&" inside a quoted message -> DENY',
      run_guard('git commit -m "cd /nonexistent-decoy-path &&"', IDXD, cwd=rootD)[0], "DENY")

check('decoy "git -C /nonexistent" inside a quoted message -> DENY',
      run_guard('git commit -m "run: git -C /nonexistent-decoy commit"', IDXD, cwd=rootD)[0],
      "DENY")

# CORRECTED EXPECTATION: with the whole command correctly tokenized as ONE clean
# segment (the "&&" stays part of the quoted -m token, never a real operator), this
# command carries a GENUINE trailing pathspec `-- nonexistent.md` that does not name
# MEMORY.md. Verified directly against real git: `git commit -- nonexistent.md` (a
# pathspec matching no tracked/staged file) FAILS OUTRIGHT -- exit 1, "error: pathspec
# 'nonexistent.md' did not match any file(s) known to git", nothing committed. So ALLOW
# is the objectively correct answer here, not a bypass: there is no real commit for
# this shape to ever land.
check('decoy "&&" inside a quoted message, with a real (non-matching) pathspec -> ALLOW',
      run_guard('git commit -m "cd /decoy &&" -- nonexistent.md', IDXD, cwd=rootD)[0], "ALLOW")

check("'cd' text sitting in a LATER segment (not the command's OWN first segment) -> DENY",
      run_guard('git commit -m x && echo "cd /decoy &&"', IDXD, cwd=rootD)[0], "DENY")

# commit's OWN -C flag (git commit -C <ref>: reuse that commit's message) is a
# COMPLETELY different, real flag from the global `git -C <path>` directory override --
# it lives AFTER the subcommand and must never be misread as a directory.
git(rootD, "commit", "-qm", "landed, so -C HEAD below actually points at something")
with open(os.path.join(memD, "MEMORY.md"), "a", encoding="utf-8") as f:
    f.write("- [OrphanD2](orphanD2.md) - hook\n")
with open(os.path.join(memD, "orphanD2.md"), "w", encoding="utf-8") as f:
    f.write("body, not staged\n")
git(rootD, "add", "projects/proj/memory/MEMORY.md")
check("commit's OWN `-C HEAD` (reuse-message flag, not a dir override) -> still DENY",
      run_guard("git commit -C HEAD", IDXD, cwd=rootD)[0], "DENY")

shutil.rmtree(rootD, ignore_errors=True)

# ===================================================================================
# TORN-SEGMENT ATTACK (2026-07-24). Found by local code review, live-verified
# end-to-end (real git, exit 0, orphan actually landed in HEAD) against the version of
# _resolve_target_repo BEFORE this fix. Every raw-string `re.split(r"(?:&&|\|\||;|\|)",
# cmd)` in this file was quote-BLIND: a crafted quoted argument containing an EMBEDDED
# ';'/'&&'/'|' can TEAR across what the split treats as two "segments", and each torn
# fragment can independently happen to shlex-parse cleanly on its own (unbalanced
# quotes canceling out coincidentally across the tear) -- fabricating a fake
# segment/subcommand that never existed as a standalone shell command.
#   git -c core.foo="a;git -C <decoy-repo> commit -m y;b" commit -m "real msg"
# tore into a segment containing a FABRICATED `git -C <decoy-repo> commit`, found
# BEFORE the real commit later in the string; the decoy repo had no memory/ directory,
# so the guard ALLOWED -- while real git actually landed the orphan (verified: exit 0,
# "Orphan" present in HEAD's MEMORY.md). Closed by _tokenize_segments(): shlex-tokenize
# the WHOLE command ONCE, then derive segments from the resulting flat TOKEN list by
# looking for literal &&/||/;/| TOKENS -- a ';' living inside a quoted token is never a
# standalone token, so it can never masquerade as a separator.
# ===================================================================================
print()
print("== TORN-SEGMENT ATTACK: a decoy embedded in a quoted -c value must not fabricate a segment ==")
rootT, memT = setup()
IDXT = os.path.join(memT, "MEMORY.md").replace("\\", "/")
with open(os.path.join(memT, "MEMORY.md"), "a", encoding="utf-8") as f:
    f.write("- [OrphanT](orphanT.md) - hook\n")
with open(os.path.join(memT, "orphanT.md"), "w", encoding="utf-8") as f:
    f.write("body, not staged\n")
git(rootT, "add", "projects/proj/memory/MEMORY.md")

decoyT = tempfile.mkdtemp(prefix="torn-decoy-")
git(decoyT, "init", "-q")

check("torn-segment decoy `-C <decoy>` fabricated via ';' inside a quoted -c value -> DENY",
      run_guard('git -c core.foo="a;git -C %s commit -m y;b" commit -m "real msg"' % decoyT,
                IDXT, cwd=rootT)[0], "DENY")

shutil.rmtree(rootT, ignore_errors=True)
shutil.rmtree(decoyT, ignore_errors=True)

# ===================================================================================
# SECOND CODE REVIEW ROUND on the torn-segment fix itself (2026-07-24). The first
# _tokenize_segments closed the torn-segment attack above but introduced two of its OWN
# regressions, both live-verified end-to-end (real bash, real git, orphan actually
# landed in HEAD) before being closed by the CURRENT design (shlex.shlex + posix +
# punctuation_chars over the WHOLE command, never pre-split by line -- see the module
# comment above _tokenize_segments for the full account):
#   1. Multi-line (heredoc-style) commit messages -- THIS ENVIRONMENT'S OWN standard
#      commit idiom -- fully disabled the guard (pre-splitting by line tore an open
#      quote apart before shlex ever saw it as one string).
#   2. A shell operator glued to a neighboring word with no whitespace (e.g.
#      `path&&git`) was invisible to whitespace-based tokenization -- a REGRESSION
#      even versus the pre-torn-segment-fix code, which (being raw-regex-based) did
#      NOT require whitespace around an operator.
# A third, related gap found in the SAME pass (not from external review -- self-caught
# by tracing what "no longer splitting on bare newlines" implied): two REAL, separate
# statements joined ONLY by a bare newline (no ';'/'&&' at all -- valid bash) would
# otherwise silently merge into one segment, letting a real `git add MEMORY.md` get
# swallowed as trailing "arguments" of an unrelated subcommand and never seen as its
# own action -- the exact bypass shape Round 1 (12:54 same-day fix) closed for `&&`,
# reopened here for a bare newline until the lineno-delta-vs-embedded-newlines check
# was added.
# ===================================================================================
print()
print("== SECOND REVIEW ROUND on tokenization itself: heredocs, glued operators, bare newlines ==")


def _new_orphan_repo(prefix):
    r, m = setup()
    with open(os.path.join(m, "MEMORY.md"), "a", encoding="utf-8") as f:
        f.write("- [Orphan](orphan_%s.md) - hook\n" % prefix)
    with open(os.path.join(m, "orphan_%s.md" % prefix), "w", encoding="utf-8") as f:
        f.write("body, not staged\n")
    git(r, "add", "projects/proj/memory/MEMORY.md")
    return r, os.path.join(m, "MEMORY.md").replace("\\", "/")

rootHD, idxHD = _new_orphan_repo("hd")
heredoc_cmd = ('git commit -m "$(cat <<\'EOF\'\n'
               'Routine memory update.\n\n'
               'Co-Authored-By: Claude <noreply@anthropic.com>\n'
               'EOF\n)"')
check("heredoc-style multi-line -m (this repo's own commit idiom) -> DENY",
      run_guard(heredoc_cmd, idxHD, cwd=rootHD)[0], "DENY")
shutil.rmtree(rootHD, ignore_errors=True)

rootNS, idxNS = _new_orphan_repo("ns")
check("`&&` glued to a word with no surrounding whitespace -> DENY",
      run_guard('git add "projects/proj/memory/MEMORY.md"&&git commit -m y',
                idxNS, cwd=rootNS)[0], "DENY")
shutil.rmtree(rootNS, ignore_errors=True)

rootBN, idxBN = _new_orphan_repo("bn")
check("bare newline (no ';'/'&&' at all) separating a real add from a real commit -> DENY",
      run_guard("git add MEMORY.md\ngit commit -m x", idxBN, cwd=rootBN)[0], "DENY")
shutil.rmtree(rootBN, ignore_errors=True)

rootBN3, idxBN3 = _new_orphan_repo("bn3")
check("THREE statements via bare newlines, real add mid-sequence -> DENY",
      run_guard("git add other.txt\ngit add MEMORY.md\ngit commit -m x", idxBN3, cwd=rootBN3)[0],
      "DENY")
shutil.rmtree(rootBN3, ignore_errors=True)

# sanity: a newline living INSIDE a quoted argument OTHER than the first one (-m) must
# not be mistaken for a real separator, regardless of its position in the token stream.
rootQN, idxQN = _new_orphan_repo("qn")
check("newline INSIDE a quoted argument that is NOT the message -> stays one segment -> DENY",
      run_guard('git commit -m x --author="A\nB <a@b.c>"', idxQN, cwd=rootQN)[0], "DENY")
shutil.rmtree(rootQN, ignore_errors=True)

# ===================================================================================
# THIRD REVIEW ROUND on tokenization (2026-07-24, self-caught while stress-testing the
# second round's own fix, not from external review). The lineno-delta heuristic from
# round 2 turned out to be UNRELIABLE: `echo hi # comment\ngit commit -m x` split at
# the WRONG token boundary (verified: 'git' ended up glued to the wrong segment)
# because a `#` comment's terminating newline is consumed by a DIFFERENT internal shlex
# code path than plain whitespace, and the lineno increase gets mis-attributed. A
# second, related gap: shlex groups REPEATED punctuation characters into one token
# (same rule that correctly groups `&&`), so `'\n\n\n'` (blank lines between
# statements -- an ordinary thing to paste) didn't match an exact `token in {"\n"}`
# check and silently passed through as content. Both closed by making `\n` a REAL
# punctuation character (not inferred after the fact), disabling comment-handling
# entirely (a comment's own terminator is then free to be seen normally), and checking
# whether a token consists ENTIRELY of operator characters rather than exact string
# matching a short fixed list -- see _tokenize_segments' module comment for the full
# account of all three rounds.
# ===================================================================================
print()
print("== THIRD REVIEW ROUND (self-caught): comment lines and blank-line separators ==")

rootCM, idxCM = _new_orphan_repo("cm")
check("a '#' comment on the line BEFORE a real commit must not swallow it -> DENY",
      run_guard("echo hi # this is a comment\ngit commit -m x", idxCM, cwd=rootCM)[0], "DENY")
shutil.rmtree(rootCM, ignore_errors=True)

rootBL, idxBL = _new_orphan_repo("bl")
check("blank lines (multiple consecutive bare newlines) between two real statements -> DENY",
      run_guard("git add MEMORY.md\n\n\ngit commit -m x", idxBL, cwd=rootBL)[0], "DENY")
shutil.rmtree(rootBL, ignore_errors=True)

# ===================================================================================
# FOURTH REVIEW ROUND on tokenization (2026-07-24). `punctuation_chars` inherited
# `();<>` from the default set. shlex groups ANY run of adjacent punctuation_chars
# characters into ONE token regardless of which specific characters they are (the same
# rule that correctly groups `&&`) -- so a real separator glued directly to one of
# these inert characters with no whitespace (`;(`, `&(`, `);`) merged into ONE token
# like `';('`. Requiring EVERY character in a token to be a real operator
# (_SEGMENT_OP_CHARS) failed on that mixed token and silently treated it as ordinary
# content -- hiding a real `git commit` behind an earlier subcommand. Live-verified,
# zero deny output: `git add MEMORY.md;(git commit -m x)` -- an ordinary subshell
# idiom, not exotic. A first attempted fix (dropping `();<>` from punctuation_chars
# entirely) was self-caught before shipping: without them as their own tokens, `(`
# glues onto the NEXT word instead (`(git`), so `_segment_git_parts`'s exact
# `token == "git"` match stops recognizing the git executable at all -- same bypass,
# different mechanism. Correct fix: keep `();<>` in punctuation_chars (so they stay
# cleanly separated from "git"), and broaden the separator test to "pure punctuation
# AND contains at least one real operator character" rather than "every character is
# an operator" -- see _tokenize_segments' module comment for the full account.
# ===================================================================================
print()
print("== FOURTH REVIEW ROUND: an operator glued to an inert punctuation char (subshell idiom) ==")

rootPG1, idxPG1 = _new_orphan_repo("pg1")
check("`;(` glued with no whitespace (subshell after ';') -> DENY",
      run_guard('git add MEMORY.md;(git commit -m x)', idxPG1, cwd=rootPG1)[0], "DENY")
shutil.rmtree(rootPG1, ignore_errors=True)

rootPG2, idxPG2 = _new_orphan_repo("pg2")
check("leading `(` before the FIRST statement, `);` before the second -> DENY",
      run_guard('(git add MEMORY.md);git commit -m x', idxPG2, cwd=rootPG2)[0], "DENY")
shutil.rmtree(rootPG2, ignore_errors=True)

rootPG3, idxPG3 = _new_orphan_repo("pg3")
check("repeated ';;;' glued directly to '(' -> DENY",
      run_guard('git add MEMORY.md;;;(git commit -m x)', idxPG3, cwd=rootPG3)[0], "DENY")
shutil.rmtree(rootPG3, ignore_errors=True)

rootPG4, idxPG4 = _new_orphan_repo("pg4")
check("`&(` glued with no whitespace (backgrounding + subshell) -> DENY",
      run_guard('git add MEMORY.md&(git commit -m x)', idxPG4, cwd=rootPG4)[0], "DENY")
shutil.rmtree(rootPG4, ignore_errors=True)

# sanity: a purely-inert merged punctuation blob (no real operator character present)
# must NOT be treated as a separator.
rootPG5, idxPG5 = _new_orphan_repo("pg5")
check("purely inert punctuation ('()' -- no real operator char) stays ordinary content -> DENY",
      run_guard('git commit -m x ()', idxPG5, cwd=rootPG5)[0], "DENY")
shutil.rmtree(rootPG5, ignore_errors=True)

print()
print("== REPO RESOLUTION: a REAL worktree of the SAME repo has its OWN independent index ==")
rootM, memM = setup()
IDXM = os.path.join(memM, "MEMORY.md").replace("\\", "/")

wt_dir = tempfile.mkdtemp(prefix="orphan-guard-wt-")
shutil.rmtree(wt_dir, ignore_errors=True)  # `git worktree add` must create this itself
r = git(rootM, "worktree", "add", "-b", "wt-branch", wt_dir, "HEAD")
if r.returncode != 0:
    check("(worktree setup failed -- skipping worktree-specific cases: %s)"
          % r.stderr.strip()[:200], "SKIPPED", "SKIPPED")
else:
    mem_wt = os.path.join(wt_dir, "projects", "proj", "memory")

    # Case 1: orphan staged ONLY in the MAIN checkout; the WORKTREE's own index is
    # clean. A plain commit run FROM the worktree (cwd=worktree, no pathspec) must not
    # be judged against the main checkout's unrelated staged state.
    with open(os.path.join(memM, "MEMORY.md"), "a", encoding="utf-8") as f:
        f.write("- [OrphanM](orphanM.md) - hook\n")
    with open(os.path.join(memM, "orphanM.md"), "w", encoding="utf-8") as f:
        f.write("body, not staged\n")
    git(rootM, "add", "projects/proj/memory/MEMORY.md")
    with open(os.path.join(wt_dir, "scratch.txt"), "w", encoding="utf-8") as f:
        f.write("wt work\n")
    git(wt_dir, "add", "scratch.txt")

    check("orphan staged in MAIN only, plain commit run FROM the worktree -> ALLOW "
          "(THE bug that blocked real work today)",
          run_guard("git commit -m x", IDXM, cwd=wt_dir)[0], "ALLOW")

    git(rootM, "reset", "-q")  # clean up the main checkout's staged orphan

    # Case 2: the WORKTREE's own MEMORY.md has a real orphan, staged in the
    # worktree's OWN index (main checkout stays clean). A commit run from the
    # worktree must still correctly DENY -- the fix must not blanket-disable the
    # guard, only correctly SCOPE it to the actual target repo.
    with open(os.path.join(mem_wt, "MEMORY.md"), "a", encoding="utf-8") as f:
        f.write("- [OrphanWT](orphanWT.md) - hook\n")
    with open(os.path.join(mem_wt, "orphanWT.md"), "w", encoding="utf-8") as f:
        f.write("body, not staged\n")
    git(wt_dir, "add", "projects/proj/memory/MEMORY.md")

    check("orphan staged in the WORKTREE's own index, committed from the worktree -> DENY",
          run_guard("git commit -m x", IDXM, cwd=wt_dir)[0], "DENY")

    git(rootM, "worktree", "remove", "--force", wt_dir)

shutil.rmtree(rootM, ignore_errors=True)
print()
print(f"RESULT: {sum(results)}/{len(results)} passed")
sys.exit(0 if all(results) else 1)
