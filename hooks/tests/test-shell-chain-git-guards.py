"""The git-discipline guards judge EVERY shell tool, not only Bash.

Cross-repo audit 2026-11-23 (HIGH): PowerShell, Desktop Commander start_process /
interact_with_process and the terminal panel's run_in_terminal ran git with none of the
git-discipline guards, so `git reset --hard`, an unreviewed commit or a commit from the
shared checkout skipped them by choosing another tool. The dispatcher now has a "shell"
chain wired for those tools (hooks/wiring/settings-wiring.toml row pre.dispatcher-shell),
and each guard reads its command through tool_call_paths.shell_text.

  S1-S4  static: the chain, its wiring matcher, and every guard's scope/command source.
  B1     destructive-git-guard through the REAL dispatcher --chain shell, four tool forms.
  B2     worktree-isolation-guard blocks a blast-radius commit from a "shared" main checkout
         in every shell form, exactly as for Bash (WORKTREE_ISOLATION_SHARED_ROOTS seam).
  B3     eos-review-gate blocks an unreviewed hooks/** commit in every shell form.
Run: python hooks/tests/test-shell-chain-git-guards.py   (exit 0 = all pass)
"""
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
HOOKS = os.path.dirname(HERE)
REPO = os.path.dirname(HOOKS)
DISPATCHER = os.path.join(HOOKS, "pretooluse-dispatcher.py")
PY = sys.executable
sys.path.insert(0, os.path.join(HOOKS, "lib"))
import tool_call_paths  # noqa: E402

FAILS = []

SHELL_CHAIN = ["eos-evidence-gate", "eos-review-gate", "commit-provenance-guard",
               "worktree-isolation-guard", "destructive-git-guard",
               "memory-orphan-link-guard", "commit-hygiene-guard"]

# (tool_name, tool_input builder) -- the four non-Bash shell forms, plus Bash as the control.
FORMS = [
    ("Bash", lambda c: {"command": c}),
    ("PowerShell", lambda c: {"command": c}),
    ("mcp__Desktop_Commander__start_process", lambda c: {"command": c, "timeout_ms": 5000}),
    ("mcp__Desktop_Commander__interact_with_process", lambda c: {"pid": 1, "input": c}),
    ("mcp__terminal__run_in_terminal", lambda c: {"command": c}),
    # Review 2026-11-23 (C1): Windows-MCP PowerShell runs a real command line too.
    ("mcp__local_Windows-MCP__PowerShell", lambda c: {"command": c}),
]


def check(name, cond, detail=""):
    print("  [%s] %s%s" % ("PASS" if cond else "FAIL", name, "" if cond else " " + detail))
    if not cond:
        FAILS.append(name)


def clean_env(extra=None):
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    if extra:
        env.update(extra)
    return env


def git(repo, *a):
    return subprocess.run(("git",) + a, cwd=repo, capture_output=True, text=True, env=clean_env())


def make_repo(files):
    d = tempfile.mkdtemp(prefix="shellchain-")
    git(d, "init", "-q", "-b", "main")
    git(d, "config", "user.email", "t@t.t")
    git(d, "config", "user.name", "t")
    git(d, "config", "core.autocrlf", "false")
    for rel, body in files.items():
        p = os.path.join(d, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="ascii", newline="\n") as fh:
            fh.write(body)
    git(d, "add", "-A")
    git(d, "commit", "-q", "-m", "base")
    return d


def payload(tool, builder, cmd, cwd, session="shellchain-sess"):
    return json.dumps({"tool_name": tool, "tool_input": builder(cmd), "cwd": cwd,
                       "session_id": session}).encode("utf-8")


def run(argv, data, cwd, env):
    p = subprocess.run(argv, input=data, capture_output=True, cwd=cwd, env=env, timeout=120)
    return p.returncode, p.stderr.decode("utf-8", "replace")


# ---------------------------------------------------------------- static
print("== S1: the dispatcher's shell chain ==")
spec = __import__("importlib.util").util.spec_from_file_location("disp", DISPATCHER)
disp = __import__("importlib.util").util.module_from_spec(spec)
spec.loader.exec_module(disp)
check("S1 CHAINS['shell'] is exactly the git-discipline guards, in bash-chain order",
      disp.CHAINS.get("shell") == SHELL_CHAIN, repr(disp.CHAINS.get("shell")))
bash_order = [g for g in disp.CHAINS["bash"] if g in SHELL_CHAIN]
check("S1 the shell chain keeps the bash chain's relative order", bash_order == SHELL_CHAIN, repr(bash_order))

print("== S2: the wiring row covers every non-Bash shell tool and NOT Bash ==")
with open(os.path.join(HOOKS, "wiring", "settings-wiring.toml"), encoding="utf-8") as fh:
    toml = fh.read()
m = re.search(r"id = 'pre\.dispatcher-shell'.*?matcher = '([^']+)'.*?args = '--chain shell'", toml, re.S)
check("S2 row pre.dispatcher-shell exists with --chain shell", m is not None)
if m:
    rx = re.compile("^(?:%s)$" % m.group(1))
    for tool, _ in FORMS[1:]:
        check("S2 matcher fully covers %s" % tool, bool(rx.match(tool)))
    check("S2 matcher does NOT cover Bash (the bash chain already runs these guards)", not rx.match("Bash"))
    for tool, _ in FORMS:
        check("S2 %s is a git shell tool per tool_call_paths" % tool, tool_call_paths.is_git_shell_tool(tool))
    check("S2 is_shell_tool itself is NOT widened (the egress guards rely on its exact scope)",
          not tool_call_paths.is_shell_tool("mcp__local_Windows-MCP__PowerShell"))

print("== S3: no shell-chain guard filters on Bash except its import fallback ==")
for g in SHELL_CHAIN:
    with open(os.path.join(HOOKS, g + ".py"), encoding="utf-8") as fh:
        src = fh.read()
    filters = re.findall(r'tool_name"\)\s*(?:!=|not in)\s*\(?(?:None, )?"Bash"', src)
    check("S3 %s has no Bash-only tool_name filter" % g, not filters, repr(filters))
    # The CALL SITE, not the fallback's own `def _shell_text(` (review 2026-11-23, C5: the old
    # `"_shell_text(" in src` check could never fail).
    check("S3 %s reads its command via _shell_text at the call site" % g,
          '_shell_text(payload.get("tool_name")' in src)
    check("S3 %s still has no direct tool_input .get(\"command\") read outside the fallback" % g,
          len(re.findall(r'\.get\("command"\)', src)) == 1, repr(re.findall(r'.{30}\.get\("command"\)', src)))
    check("S3 %s imports is_git_shell_tool/shell_text from tool_call_paths" % g,
          "from tool_call_paths import is_git_shell_tool as _is_shell_tool, shell_text as _shell_text" in src)

# ---------------------------------------------------------------- behaviour
print("== B1: destructive-git-guard through the real dispatcher --chain shell ==")
dirty = make_repo({"a.txt": "v1\n"})
with open(os.path.join(dirty, "a.txt"), "w") as fh:
    fh.write("uncommitted\n")
clean = make_repo({"a.txt": "v1\n"})
sess = tempfile.mkdtemp(prefix="shellchain-tok-")
env = clean_env({"ORA_OVERRIDE_SESSIONS_DIR": sess, "EOS_SESSIONS_DIR": sess})
for tool, builder in FORMS[1:]:
    rc, err = run([PY, DISPATCHER, "--chain", "shell"], payload(tool, builder, "git reset --hard", dirty), dirty, env)
    check("B1 %s: `git reset --hard` over uncommitted work is BLOCKED" % tool,
          rc == 2 and "destructive-git-guard" in err, "rc=%s err=%r" % (rc, err[-240:]))
    rc, err = run([PY, DISPATCHER, "--chain", "shell"], payload(tool, builder, "git reset --hard", clean), clean, env)
    check("B1 %s: the same command on a clean tree is allowed" % tool, rc == 0, "rc=%s err=%r" % (rc, err[-240:]))

print("== B2: worktree-isolation-guard, every shell form = the Bash verdict ==")
shared = make_repo({"hooks/some-guard.py": "v1\n", "plain.txt": "v1\n"})
with open(os.path.join(shared, "hooks", "some-guard.py"), "w") as fh:
    fh.write("v2\n")
git(shared, "add", "--", "hooks/some-guard.py")
wig = os.path.join(HOOKS, "worktree-isolation-guard.py")
wenv = clean_env({"WORKTREE_ISOLATION_SHARED_ROOTS": shared, "ORA_OVERRIDE_SESSIONS_DIR": sess})
verdicts = {}
for tool, builder in FORMS:
    rc, err = run([PY, wig], payload(tool, builder, "git commit -m x", shared), shared, wenv)
    verdicts[tool] = (rc, "BLOCKED (worktree-isolation-guard)" in err)
check("B2 control: Bash blocks a blast-radius commit from the shared main checkout",
      verdicts["Bash"] == (2, True), repr(verdicts["Bash"]))
for tool, _ in FORMS[1:]:
    check("B2 %s blocks it too" % tool, verdicts[tool] == (2, True), repr(verdicts[tool]))

print("== B3: eos-review-gate, every shell form = the Bash verdict ==")
rg_repo = make_repo({"README.md": "hello\n"})
os.makedirs(os.path.join(rg_repo, "hooks"), exist_ok=True)
with open(os.path.join(rg_repo, "hooks", "g.py"), "w", encoding="ascii", newline="\n") as fh:
    fh.write("x = 1\n")
git(rg_repo, "add", "--", "hooks/g.py")
rg = os.path.join(HOOKS, "eos-review-gate.py")
renv = clean_env({"EOS_SESSIONS_DIR": tempfile.mkdtemp(prefix="shellchain-rg-"),
                  "ORA_OVERRIDE_SESSIONS_DIR": tempfile.mkdtemp(prefix="shellchain-rgtok-")})
renv.pop("EOS_REVIEW_MODELS", None)
rverdicts = {}
for tool, builder in FORMS:
    rc, err = run([PY, rg], payload(tool, builder, "git commit -m x", rg_repo, "sess1"), rg_repo, renv)
    rverdicts[tool] = rc
check("B3 control: Bash blocks an unreviewed hooks/** commit", rverdicts["Bash"] == 2, repr(rverdicts))
for tool, _ in FORMS[1:]:
    check("B3 %s blocks it too" % tool, rverdicts[tool] == 2, repr(rverdicts[tool]))

print("== B4: eos-evidence-gate reminds on a commit in every shell form (incl. interact_with_process) ==")
ev = os.path.join(HOOKS, "eos-evidence-gate.py")
eenv = clean_env({"EOS_SESSIONS_DIR": tempfile.mkdtemp(prefix="shellchain-ev-")})
for tool, builder in FORMS:
    p = subprocess.run([PY, ev], input=payload(tool, builder, "git commit -m x", rg_repo, "ev-sess"),
                       capture_output=True, cwd=rg_repo, env=eenv, timeout=60)
    check("B4 %s: no gate-green marker -> the evidence reminder is emitted" % tool,
          p.returncode == 0 and p.stdout.strip() != b"", "rc=%s out=%r" % (p.returncode, p.stdout[:120]))

print()
if FAILS:
    print("test-shell-chain-git-guards: %d FAILED: %s" % (len(FAILS), ", ".join(FAILS)))
    sys.exit(1)
print("test-shell-chain-git-guards: ALL PASS")
sys.exit(0)
