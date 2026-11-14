"""Tests for hooks/git-precommit-send-lint.py (pre-commit send-contract lint on staged specs).

Run: python hooks/tests/test-git-precommit-send-lint.py   (exit 0 = all pass)
Builds a throwaway git repo holding the real lint and the hook, with its own empty
core.hooksPath so no real ORA hook fires inside it.
"""
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
HOOK = os.path.join(REPO, "hooks", "git-precommit-send-lint.py")
LINT = os.path.join(REPO, "maintenance", "_tests", "test_send_contract_spec_lint.py")

results = []


def check(name, cond, detail=""):
    results.append(bool(cond))
    print(("  PASS  " if cond else "  FAIL  ") + name + ("" if cond else " -- " + str(detail)[:300]))


BAD = ("---\nname: {t}\n---\nEmail via `C:\\Users\\Owner\\.claude\\scheduled-tasks\\_shared\\send-via-outlook.ps1` "
       "to ggoldberg@oxfordra.net ONLY. On a non-zero exit, retry once; if it fails again, say so.\n")
GOOD = ("---\nname: {t}\n---\nEmail via `C:\\Users\\Owner\\.claude\\scheduled-tasks\\_shared\\send-via-outlook.ps1` "
        "to ggoldberg@oxfordra.net ONLY. Retry only on exit 2 or 4, once; never resend after any other exit.\n")


def git(repo, *a):
    return subprocess.run(["git", "-C", repo, *a], capture_output=True, text=True, encoding="utf-8",
                          errors="replace")


def make_repo():
    repo = tempfile.mkdtemp(prefix="precommit_send_lint_")
    os.makedirs(os.path.join(repo, ".nohooks"))
    git(repo, "init", "-q", "-b", "main")
    for k, v in (("user.name", "t"), ("user.email", "t@example.invalid"), ("commit.gpgsign", "false"),
                 ("core.hooksPath", os.path.join(repo, ".nohooks")), ("core.autocrlf", "false")):
        git(repo, "config", k, v)
    os.makedirs(os.path.join(repo, "maintenance", "_tests"))
    shutil.copy(LINT, os.path.join(repo, "maintenance", "_tests", os.path.basename(LINT)))
    os.makedirs(os.path.join(repo, "hooks"))
    shutil.copy(HOOK, os.path.join(repo, "hooks", os.path.basename(HOOK)))
    write(repo, "ora-seed-task", GOOD)
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "seed")
    return repo


def write(repo, task, text):
    d = os.path.join(repo, "scheduled-tasks", task)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "SKILL.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write(text.format(t=task))


def run_hook(repo):
    r = subprocess.run([sys.executable, os.path.join(repo, "hooks", os.path.basename(HOOK))], cwd=repo,
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
    return r.returncode, r.stdout + r.stderr


repos = []
try:
    # 1. nothing scheduled staged: passes at once, lint never runs
    repo = make_repo(); repos.append(repo)
    with open(os.path.join(repo, "notes.md"), "w") as f:
        f.write("x\n")
    git(repo, "add", "notes.md")
    rc, out = run_hook(repo)
    check("no spec staged -> exit 0, silent", rc == 0 and out.strip() == "", (rc, out))

    # 2. a staged spec with generic send retry is blocked, naming the task
    write(repo, "ora-bad-task", BAD)
    git(repo, "add", "-A")
    rc, out = run_hook(repo)
    check("staged generic-retry spec -> blocked", rc == 1 and "BLOCKED" in out and "ora-bad-task" in out, (rc, out))

    # 3. the index is what counts: fix the working copy without staging -> still blocked
    write(repo, "ora-bad-task", GOOD)
    rc, out = run_hook(repo)
    check("good working copy, bad staged copy -> still blocked", rc == 1, (rc, out))
    git(repo, "add", "-A")
    rc, out = run_hook(repo)
    check("fixed and staged -> passes", rc == 0, (rc, out))
    git(repo, "commit", "-q", "-m", "good")

    # 4. a bad working copy that is NOT staged cannot block an unrelated staged spec
    write(repo, "ora-other-task", GOOD)
    git(repo, "add", "-A")
    write(repo, "ora-other-task", BAD)
    rc, out = run_hook(repo)
    check("bad unstaged working copy does not block", rc == 0, (rc, out))
    git(repo, "checkout", "-q", "--", ".")
    git(repo, "commit", "-q", "-m", "other")

    # 5. a failure already committed in another spec only warns
    write(repo, "ora-legacy-task", BAD)
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "--no-verify", "-m", "legacy (bypassed)")
    write(repo, "ora-new-task", GOOD)
    git(repo, "add", "-A")
    rc, out = run_hook(repo)
    check("pre-existing failure elsewhere -> warns, does not block",
          rc == 0 and "WARN (not in this commit)" in out and "ora-legacy-task" in out, (rc, out))

    # 6. whole-word task matching: staging ora-x must not be blamed for ora-x-2
    spec = importlib.util.spec_from_file_location("hook", HOOK)
    hook = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(hook)
    block, other = hook.blocking_failures("  FAIL  L2 ora-x-2 does not retry\n", {"ora-x"}, False)
    check("whole-word task match", block == [] and len(other) == 1, (block, other))
    block, other = hook.blocking_failures("  FAIL  anything\n", set(), True)
    check("lint script staged -> every FAIL blocks", len(block) == 1, (block, other))
finally:
    for r in repos:
        shutil.rmtree(r, ignore_errors=True)

passed = sum(results)
print(f"\ngit-precommit-send-lint tests: {passed}/{len(results)} passed")
sys.exit(0 if passed == len(results) else 1)
