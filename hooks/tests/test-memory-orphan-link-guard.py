"""Standalone test for hooks/memory-orphan-link-guard.py. Builds a throwaway git repo
that mimics the memory/ layout, then drives the guard via stdin exactly as the harness does.
"""
import json, os, shutil, subprocess, sys, tempfile

GUARD = r"C:\Users\Owner\.claude\hooks\memory-orphan-link-guard.py"
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
print()
print(f"RESULT: {sum(results)}/{len(results)} passed")
sys.exit(0 if all(results) else 1)
