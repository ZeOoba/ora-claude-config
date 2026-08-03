"""Sub-index awareness for the two MEMORY.md guards (2026-08-03).

The MEMORY.md split moved 108 of ~190 pointers into INDEX_reference.md. Both guards
keyed on the single filename MEMORY.md, so after the split the MAJORITY of the corpus
would have been unguarded at commit time and unlinted at write time -- while both
guards still reported healthy. That is worse than an obvious break.

Covers:
  * memory-index-guard.is_memory_index() -- recognises a sibling INDEX_*.md
  * memory-orphan-link-guard -- BLOCKS a commit landing a sub-index whose linked body
    is neither staged nor in HEAD, and still allows the clean case

Builds throwaway git repos in temp dirs; the live memory tree is never touched.
Run: python test-memory-subindex-guards.py   (exit 0 = all pass)
"""
import importlib.util, json, os, subprocess, sys, tempfile

_GIT_LEAK_VARS = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR",
                  "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_PREFIX")
for _v in _GIT_LEAK_VARS:
    os.environ.pop(_v, None)


def _clean_env(**extra):
    env = {k: v for k, v in os.environ.items() if k not in _GIT_LEAK_VARS}
    env.update(extra)
    return env


HOOKS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORPHAN_GUARD = os.path.join(HOOKS, "memory-orphan-link-guard.py")
PY = sys.executable

spec = importlib.util.spec_from_file_location(
    "mig", os.path.join(HOOKS, "memory-index-guard.py"))
mig = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mig)

results = []


def check(name, got, want):
    ok = got == want
    results.append(ok)
    print(("  PASS  " if ok else "  FAIL  ") + name +
          ("" if ok else "   (got %r, want %r)" % (got, want)))


def git(repo, *a):
    return subprocess.run(("git",) + a, cwd=repo, capture_output=True,
                          text=True, env=_clean_env())


def run_guard(cmd, index_path, cwd=None):
    payload = {"tool_name": "Bash", "tool_input": {"command": cmd},
               "cwd": cwd or os.path.dirname(index_path)}
    p = subprocess.run([PY, ORPHAN_GUARD], input=json.dumps(payload).encode("utf-8"),
                       capture_output=True, env=_clean_env(ORA_MEMORY_INDEX=index_path))
    out = p.stdout.decode("utf-8", "replace").strip()
    if p.returncode != 0:
        return "NONZERO_EXIT"
    if not out:
        return "ALLOW"
    try:
        return json.loads(out)["hookSpecificOutput"]["permissionDecision"].upper()
    except Exception:
        return "UNPARSEABLE"


# ---------------------------------------------------------------- index-guard
print("== memory-index-guard: which files count as an index ==")
MEM = "C:/x/projects/proj/memory"
os.environ["ORA_MEMORY_INDEX"] = MEM + "/MEMORY.md"
check("root MEMORY.md is an index", mig.is_memory_index(MEM + "/MEMORY.md"), True)
check("sibling INDEX_reference.md is an index",
      mig.is_memory_index(MEM + "/INDEX_reference.md"), True)
check("sibling INDEX_markets.md is an index",
      mig.is_memory_index(MEM + "/INDEX_markets.md"), True)
check("an ordinary memory file is NOT an index",
      mig.is_memory_index(MEM + "/reference_foo.md"), False)
check("a file merely CONTAINING 'index' is NOT an index",
      mig.is_memory_index(MEM + "/my_index_notes.md"), False)
check("INDEX_*.md in a DIFFERENT directory is NOT an index",
      mig.is_memory_index("C:/x/other/INDEX_reference.md"), False)
check("INDEX_ prefix but not .md is NOT an index",
      mig.is_memory_index(MEM + "/INDEX_reference.txt"), False)

# ------------------------------------------------------- orphan-link-guard
print("== memory-orphan-link-guard: sub-index links are guarded too ==")
root = tempfile.mkdtemp(prefix="subidx-guard-")
mem = os.path.join(root, "projects", "proj", "memory")
os.makedirs(mem)
git(root, "init", "-q")
git(root, "config", "user.email", "t@t.t")
git(root, "config", "user.name", "t")


def w(name, text):
    with open(os.path.join(mem, name), "w", encoding="utf-8") as f:
        f.write(text)


# Committed baseline: root index links a body and a sub-index; both exist in HEAD.
w("good.md", "body\n")
w("INDEX_reference.md", "# Ref\n- [Good](good.md) - hook\n")
w("MEMORY.md", "# Index\n- [Good](good.md) - hook\n- [Ref](INDEX_reference.md) - hook\n")
git(root, "add", "-A")
git(root, "commit", "-qm", "base")
IDX = os.path.join(mem, "MEMORY.md").replace("\\", "/")

check("baseline: nothing modified -> allow",
      run_guard('git commit -m "x"', IDX), "ALLOW")

# THE REGRESSION THIS EXISTS FOR: a dangling pointer added to the SUB-index.
# Pre-change the guard only read MEMORY.md, so this committed clean.
w("INDEX_reference.md", "# Ref\n- [Good](good.md) - hook\n- [Ghost](ghost.md) - hook\n")
git(root, "add", os.path.join("projects", "proj", "memory", "INDEX_reference.md"))
check("sub-index with a link to a NONEXISTENT body -> DENY",
      run_guard('git commit -m "x"', IDX), "DENY")

# Same, but the body exists on disk and is staged in the same commit -> fine.
w("ghost.md", "body\n")
git(root, "add", os.path.join("projects", "proj", "memory", "ghost.md"))
check("...body staged in the SAME commit -> allow",
      run_guard('git commit -m "x"', IDX), "ALLOW")
git(root, "commit", "-qm", "land ghost")

# Root index must still be guarded exactly as before -- no regression.
w("MEMORY.md", "# Index\n- [Good](good.md) - hook\n- [Ref](INDEX_reference.md) - hook\n"
               "- [Missing](nope.md) - hook\n")
git(root, "add", os.path.join("projects", "proj", "memory", "MEMORY.md"))
check("root MEMORY.md dangling link still -> DENY (no regression)",
      run_guard('git commit -m "x"', IDX), "DENY")
git(root, "checkout", "--", ".")

# A commit that touches neither index is none of the guard's business.
w("unrelated.md", "hi\n")
git(root, "add", os.path.join("projects", "proj", "memory", "unrelated.md"))
check("commit touching neither index -> allow",
      run_guard('git commit -m "x" -- projects/proj/memory/unrelated.md', IDX), "ALLOW")

passed = sum(1 for r in results if r)
print("\nRESULT: %d/%d passed" % (passed, len(results)))
sys.exit(0 if passed == len(results) else 1)
