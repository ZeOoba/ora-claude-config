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
    check("staged generic-retry spec -> blocked", rc == 10 and "BLOCKED" in out and "ora-bad-task" in out, (rc, out))

    # 3. the index is what counts: fix the working copy without staging -> still blocked
    write(repo, "ora-bad-task", GOOD)
    rc, out = run_hook(repo)
    check("good working copy, bad staged copy -> still blocked", rc == 10, (rc, out))
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

    # 7. deletes and renames count as staged specs (both names of a rename)
    rows = [("D", "scheduled-tasks/ora-gone/SKILL.md"),
            ("R", "scheduled-tasks/ora-old/SKILL.md", "scheduled-tasks/ora-new/SKILL.md"),
            ("M", "scheduled-tasks/ora-case/Skill.md"), ("M", "notes.md")]
    check("deleted, renamed (both names) and case-variant specs are staged tasks",
          hook.staged_tasks(rows) == {"ora-gone", "ora-old", "ora-new", "ora-case"}, hook.staged_tasks(rows))

    # 8. through REAL `git commit` with the shim installed (review finding 8)
    SHIM = os.path.join(REPO, "hooks", "precommit-shim.sh")
    repo = make_repo(); repos.append(repo)
    hooks_dir = os.path.join(repo, ".nohooks")
    with open(SHIM, encoding="utf-8") as f:
        shim = f.read().replace("\r\n", "\n")
    with open(os.path.join(hooks_dir, "pre-commit"), "w", encoding="utf-8", newline="\n") as f:
        f.write(shim)
    os.chmod(os.path.join(hooks_dir, "pre-commit"), 0o755)

    def commit(*a):
        return git(repo, "commit", "-q", *a)

    write(repo, "ora-bad-task", BAD)
    git(repo, "add", "-A")
    r = commit("-m", "bad")
    check("real commit of a bad staged spec is blocked", r.returncode != 0 and "BLOCKED" in r.stderr,
          (r.returncode, r.stderr))
    with open(os.path.join(repo, "event_log.md"), "w") as f:
        f.write("entry\n")
    git(repo, "add", "event_log.md")
    r = commit("-m", "log", "--", "event_log.md")
    check("pathspec event_log commit is not blocked by a bad spec staged elsewhere", r.returncode == 0,
          (r.returncode, r.stderr))
    git(repo, "reset", "-q", "--", "scheduled-tasks")
    write(repo, "ora-bad-task", GOOD)
    git(repo, "add", "-A")
    commit("-m", "good")
    write(repo, "ora-bad-task", BAD)
    r = commit("-a", "-m", "regress via -a")
    check("commit -a of a bad working-tree spec is blocked", r.returncode != 0, (r.returncode, r.stderr))
    git(repo, "checkout", "-q", "--", ".")

    # 9. the shim is fail-open: a crashing or missing hook never blocks; only exit 1 does
    hook_in_repo = os.path.join(repo, "hooks", os.path.basename(HOOK))
    real = open(hook_in_repo, encoding="utf-8").read()
    with open(os.path.join(repo, "notes2.md"), "w") as f:
        f.write("y\n")
    git(repo, "add", "notes2.md")
    for label, body in (("crashing hook (exit 2)", "import sys; sys.exit(2)\n"),
                        ("raising hook (exit 1)", "raise SystemExit('boom')\n"),
                        ("syntax error in hook", "def broken(:\n")):
        with open(hook_in_repo, "w", encoding="utf-8") as f:
            f.write(body)
        r = git(repo, "commit", "-q", "--dry-run", "-m", "x")
        r = commit("-m", label, "--", "notes2.md") if os.path.exists(os.path.join(repo, "notes2.md")) else r
        check(f"shim fail-open: {label} does not block", r.returncode == 0, (r.returncode, r.stderr))
        with open(os.path.join(repo, "notes2.md"), "a") as f:
            f.write("z\n")
        git(repo, "add", "notes2.md")
    os.remove(hook_in_repo)
    r = commit("-m", "hook missing", "--", "notes2.md")
    check("shim fail-open: missing hook file does not block", r.returncode == 0, (r.returncode, r.stderr))
    with open(hook_in_repo, "w", encoding="utf-8") as f:
        f.write("import sys; sys.exit(10)\n")
    with open(os.path.join(repo, "notes2.md"), "a") as f:
        f.write("w\n")
    git(repo, "add", "notes2.md")
    r = commit("-m", "deliberate block", "--", "notes2.md")
    check("shim passes a deliberate exit 10 through as a block", r.returncode != 0, (r.returncode, r.stderr))
    with open(hook_in_repo, "w", encoding="utf-8") as f:
        f.write(real)
finally:
    for r in repos:
        shutil.rmtree(r, ignore_errors=True)

passed = sum(results)
print(f"\ngit-precommit-send-lint tests: {passed}/{len(results)} passed")
sys.exit(0 if passed == len(results) else 1)
