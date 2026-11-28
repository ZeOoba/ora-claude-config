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

print("== B5: PowerShell SYNTAX (not bash syntax under a PowerShell name) ==")
# Review 2026-11-27 (Important x2): the parser read every shell tool's command with BASH rules.
# A PowerShell backtick is an ESCAPE, not command substitution, so `"a`nb"; git reset --hard`
# hid the reset inside one segment; POSIX shlex also dropped the backslashes in `git -C C:\x`,
# so the directory never resolved and the guard allowed; `Set-Location` was not a cd.
import importlib.util as _ilu  # noqa: E402
import git_commit_parse as gcp  # noqa: E402
_dspec = _ilu.spec_from_file_location("dgg", os.path.join(HOOKS, "destructive-git-guard.py"))
dgg = _ilu.module_from_spec(_dspec)
_dspec.loader.exec_module(dgg)
DGG = os.path.join(HOOKS, "destructive-git-guard.py")
PS_FORMS = [f for f in FORMS if f[0] != "Bash"]
other = make_repo({"b.txt": "v1\n"})  # a CLEAN session cwd, so only the targeted repo can block
other2 = make_repo({"c.txt": "v1\n"})  # a second clean repo: moving clean -> clean must stay allowed
win_dirty = dirty.replace("/", "\\")


def guard(tool, builder, cmd, cwd):
    return run([PY, DGG], payload(tool, builder, cmd, cwd), cwd, env)


def segs(cmd, dialect):
    try:
        return gcp.tokenize_cmd_segments(cmd, dialect=dialect)
    except Exception as e:  # noqa: BLE001 -- a missing/raising API is a failed check, not a crash
        return [["<error %r>" % e]]


def subs(cmd, dialect):
    out = []
    for seg in segs(cmd, dialect):
        sa = gcp._segment_git_subcommand_and_args(seg)
        if sa:
            out.append([sa[0]] + list(sa[1]))
    return out


def dialects(tool):
    fn = getattr(gcp, "shell_dialects", None)
    return tuple(fn(tool)) if fn else None


PS = "powershell"
WINP = r"C:\Users\Owner\.claude"
# --- parser level: PowerShell quoting rules
c1 = 'git commit -m "a`nb"; git reset --hard HEAD~1'
check("B5 ps: backtick escape in a double-quoted -m does not swallow `; git reset --hard`",
      ["reset", "--hard", "HEAD~1"] in subs(c1, PS), repr(subs(c1, PS)))
c2 = 'git commit -m "say `"hi`""; git push --force'
check("B5 ps: an escaped quote inside -m does not swallow `; git push --force`",
      ["push", "--force"] in subs(c2, PS), repr(subs(c2, PS)))
check("B5 ps: the -m value decodes backtick escapes",
      subs('git commit -m "a`nb"', PS) == [["commit", "-m", "a\nb"]], repr(subs('git commit -m "a`nb"', PS)))
c3 = "git -C %s reset --hard" % WINP
check("B5 ps: a Windows backslash path survives -C",
      subs(c3, PS) == [["reset", "--hard"]] and dgg._git_c_dir(segs(c3, PS)[0]) == WINP, repr(segs(c3, PS)))
c4 = r"git -C 'C:\it''s dir' reset --hard"
check("B5 ps: single quotes keep backslashes and '' escapes",
      segs(c4, PS) == [["git", "-C", r"C:\it's dir", "reset", "--hard"]], repr(segs(c4, PS)))
c5 = 'git commit -m @"\nline; git reset --hard\n"@; git status'
check("B5 ps: a here-string body is opaque (its `; git reset --hard` text is not a command)",
      subs(c5, PS) == [["commit", "-m", "line; git reset --hard"], ["status"]], repr(subs(c5, PS)))
c6 = "1 | ForEach-Object { git reset --hard }"
check("B5 ps: a command inside $(...) and inside a script block is still seen",
      ["reset", "--hard"] in subs('Write-Output "$(git reset --hard)"', PS)
      and ["reset", "--hard"] in subs(c6, PS), repr(subs(c6, PS)))
check("B5 ps: call operator and git.exe still read as git",
      subs("& git.exe reset --hard", PS) == [["reset", "--hard"]], repr(subs("& git.exe reset --hard", PS)))
check("B5 ps: backtick-newline line continuation joins one command",
      subs("git reset `\n  --hard", PS) == [["reset", "--hard"]], repr(subs("git reset `\n  --hard", PS)))
check("B5 ps: a # comment with an apostrophe hides nothing after the newline",
      subs("# don't\ngit reset --hard", PS) == [["reset", "--hard"]], repr(subs("# don't\ngit reset --hard", PS)))
check("B5 bash dialect is the default and unchanged",
      gcp.tokenize_cmd_segments("git add -A; git commit -m x") == segs("git add -A; git commit -m x", "bash"))
check("B5 dialects: Bash->bash, every other shell tool->both (superset of the old bash reading)",
      dialects("Bash") == ("bash",) and set(dialects("PowerShell") or ()) == {"bash", PS}
      and set(dialects("mcp__local_Windows-MCP__PowerShell") or ()) == {"bash", PS}
      and set(dialects("mcp__Desktop_Commander__start_process") or ()) == {"bash", PS}
      and set(dialects("mcp__Desktop_Commander__interact_with_process") or ()) == {"bash", PS}
      and set(dialects("mcp__terminal__run_in_terminal") or ()) == {"bash", PS},
      repr([dialects(t) for t, _ in FORMS]))

# --- guard level, every PowerShell-capable form
win_other = other.replace("/", "\\")
for tool, builder in PS_FORMS:
    rc, err = guard(tool, builder, 'git commit -m "a`nb"; git reset --hard', dirty)
    check("B5 %s: backtick-escaped -m then `; git reset --hard` over dirty work is BLOCKED" % tool,
          rc == 2 and "destructive-git-guard" in err, "rc=%s err=%r" % (rc, err[-240:]))
    rc, err = guard(tool, builder, "git -C %s reset --hard" % win_dirty, other)
    check("B5 %s: `git -C <C:\\dirty> reset --hard` is BLOCKED" % tool,
          rc == 2 and "destructive-git-guard" in err, "rc=%s err=%r" % (rc, err[-240:]))
    for cdw in ("Set-Location", "Set-Location -Path", "set-location -LiteralPath", "sl", "cd",
                "Push-Location", "pushd", "chdir"):
        rc, err = guard(tool, builder, "%s %s; git reset --hard" % (cdw, win_dirty), other)
        check("B5 %s: `%s <C:\\dirty>; git reset --hard` is BLOCKED" % (tool, cdw),
              rc == 2 and "destructive-git-guard" in err, "rc=%s err=%r" % (rc, err[-240:]))
    rc, err = guard(tool, builder, "Set-Location %s; git reset --hard" % win_other, other2)
    check("B5 %s: control -- clean cwd, Set-Location into another CLEAN repo, reset is allowed" % tool,
          rc == 0, "rc=%s err=%r" % (rc, err[-240:]))
    rc, err = guard(tool, builder, "Set-Location %s; git reset --hard" % win_other, dirty)
    check("B5 %s: by design -- from a DIRTY cwd, Set-Location <clean>; reset still BLOCKS (as at HEAD)"
          % tool, rc == 2, "rc=%s err=%r" % (rc, err[-240:]))
    rc, err = guard(tool, builder, "git -C %s reset --hard" % win_other, dirty)
    check("B5 %s: control -- `git -C <C:\\clean> reset --hard` is allowed" % tool, rc == 0,
          "rc=%s err=%r" % (rc, err[-240:]))

# through the real dispatcher, once per PowerShell-capable form
for tool, builder in PS_FORMS:
    rc, err = run([PY, DISPATCHER, "--chain", "shell"],
                  payload(tool, builder, 'Write-Output "a`nb"; git reset --hard', dirty), dirty, env)
    check("B5 dispatcher %s: backtick-escaped echo then reset is BLOCKED" % tool,
          rc == 2 and "destructive-git-guard" in err, "rc=%s err=%r" % (rc, err[-240:]))

# Bash keeps bash rules.
fs_dirty, fs_other = dirty.replace("\\", "/"), other.replace("\\", "/")
rc, err = guard("Bash", FORMS[0][1], "git -C %s reset --hard" % fs_other, dirty)
check("B5 Bash control: -C to a clean repo is allowed", rc == 0, "rc=%s err=%r" % (rc, err[-240:]))
rc, err = guard("Bash", FORMS[0][1], "cd %s && git reset --hard" % fs_dirty, other)
check("B5 Bash control: cd into dirty then reset is still BLOCKED", rc == 2, "rc=%s err=%r" % (rc, err[-240:]))


print("== B6: REFUTE round-1 regressions (each was a false ALLOW) ==")
MIXED = ("mcp__Desktop_Commander__start_process", FORMS[2][1])
PSTOOL = ("PowerShell", FORMS[1][1])
for tool, builder in (PSTOOL, MIXED):
    for cmd, why in (
            ("git reset --hard; echo user@", "a line ending in `@` (was IndexError -> allow)"),
            ('git commit -m "a`nb"; git reset --hard; echo x@', "backtick escape + trailing @"),
            ("echo --% x | git reset --hard", "`--%` ends at a pipe"),
            ("function f { cd nonexist }; git reset --hard", "cd inside a never-called function"),
            ("if ($false) { Set-Location %s }; git reset --hard" % win_other, "cd inside a never-run if body"),
            ("$sb = { Set-Location %s }; git reset --hard" % win_other, "cd inside an uninvoked script block"),
            (". git reset --hard", "dot-sourced git"),
            ("[string]$o = git reset --hard", "typed assignment"),
            ("git.cmd reset --hard", "git.cmd")):
        rc, err = guard(tool, builder, cmd, dirty)
        check("B6 %s: %s is BLOCKED" % (tool, why), rc == 2 and "destructive-git-guard" in err,
              "cmd=%r rc=%s err=%r" % (cmd, rc, err[-200:]))
rc, err = guard(MIXED[0], MIXED[1], 'pushd .; echo "x\\`"; git reset --hard', dirty)
check("B6 mixed: bash pushd is followed by the bash reading (bash-only quoting after it)",
      rc == 2, "rc=%s err=%r" % (rc, err[-200:]))
rc, err = guard(MIXED[0], MIXED[1], "sl .; echo --% x | git reset --hard", dirty)
check("B6 mixed: `sl .; echo --% x | git reset --hard` is BLOCKED", rc == 2, "rc=%s" % rc)
for cdw in ("Set-Location BSu2013Path", "Set-Location -Path:"):
    cdw = cdw.replace("BSu2013", chr(0x2013))  # en dash
    rc, err = guard(PSTOOL[0], PSTOOL[1], "%s %s; git reset --hard" % (cdw, win_dirty), other)
    check("B6 PowerShell: `%s <dirty>` is followed" % cdw.encode("ascii", "replace").decode(),
          rc == 2, "rc=%s err=%r" % (rc, err[-200:]))
check("B6 ps: no input raises (trailing @, lone @, @\" at EOF)",
      all(isinstance(gcp.tokenize_cmd_segments(c, dialect=PS), list)
          for c in ("@", "x@", "@\"", "@'", "git --%", "`", "\"`", "<#", "${")))


print("== B7: REFUTE round-2 regressions ==")
WIN = ("mcp__local_Windows-MCP__PowerShell", FORMS[5][1])
block_cases = [
    # N1: an absolute -C after a location change the guard cannot follow
    (PSTOOL, "Pop-Location; git -C %s reset --hard" % win_dirty, other),
    (MIXED, "popd; git -C %s reset --hard" % win_dirty, other),
    (WIN, "Push-Location; git -C %s reset --hard" % win_dirty, other),
    (PSTOOL, "Set-Location; git -C %s reset --hard" % win_dirty, other),
    (MIXED, "sl x; git -C %s reset --hard" % win_dirty, other),
    (PSTOOL, "Push-Location %s; git status; Pop-Location; git -C %s checkout -- ." % (win_other, win_dirty), other),
    # N2: pop returns to the dirty cwd
    (PSTOOL, "Push-Location %s; Pop-Location; git reset --hard" % win_other, dirty),
    (WIN, "Push-Location %s; git status; Pop-Location; git reset --hard" % win_other, dirty),
    (PSTOOL, "pushd %s; popd; git reset --hard" % win_other, dirty),
    (MIXED, "pushd %s; popd; git reset --hard" % win_other, dirty),
    (PSTOOL, "Push-Location -StackName s %s; Pop-Location -StackName s; git reset --hard" % win_other, dirty),
    # N3: --% with a quoted |
    (PSTOOL, 'echo --% "a|b" | git reset --hard', dirty),
    (WIN, 'cmd /c --% "x|y" | git reset --hard', dirty),
    (PSTOOL, 'echo --% a"|"b | git reset --hard', dirty),
    # N4: location commands that do not move
    (WIN, "Push-Location; git reset --hard", dirty),
    (PSTOOL, "Push-Location -n %s; git reset --hard" % win_other, dirty),
    (MIXED, "pushd -n %s; git reset --hard" % win_other, dirty),
    (MIXED, "pushd +1; git reset --hard", dirty),
    # N6: a body that runs, judged at its own location too
    (PSTOOL, "& { cd %s; git reset --hard }" % win_dirty, other),
    (PSTOOL, "if ($true) { Set-Location %s; git reset --hard }" % win_dirty, other),
    (PSTOOL, "foreach ($i in 1) { cd %s; git reset --hard }" % win_dirty, other),
]
for (tool, builder), cmd, cwd in block_cases:
    rc, err = guard(tool, builder, cmd, cwd)
    check("B7 %s: `%s` is BLOCKED" % (tool, cmd.replace(win_dirty, "<dirty>").replace(win_other, "<clean>")),
          rc == 2 and "destructive-git-guard" in err, "rc=%s err=%r" % (rc, err[-200:]))
allow_cases = [
    (PSTOOL, "Push-Location %s; git reset --hard; Pop-Location" % win_other, other2),
    (PSTOOL, 'echo --% "a|b"; git status', dirty),
]
for (tool, builder), cmd, cwd in allow_cases:
    rc, err = guard(tool, builder, cmd, cwd)
    check("B7 %s: control `%s` is allowed" % (tool, cmd.replace(win_dirty, "<dirty>").replace(win_other, "<clean>")),
          rc == 0, "rc=%s err=%r" % (rc, err[-200:]))


print("== B8: REFUTE round-3 regressions (location tracking never probes less than HEAD) ==")
D, C_ = win_dirty, win_other
b8_block = [
    # I1: pop with nothing saved stays put
    (PSTOOL, "Pop-Location; git reset --hard", dirty),
    (PSTOOL, "popd; git reset --hard", dirty),
    (WIN, "Pop-Location; git reset --hard", dirty),
    (MIXED, "popd && git reset --hard", dirty),
    (PSTOOL, "Push-Location %s; Pop-Location; Pop-Location; git reset --hard" % C_, dirty),
    (PSTOOL, "Pop-Location; git -C . reset --hard", dirty),
    # I2: a body that runs can move the caller; a pop inside a body returns it
    (PSTOOL, "Set-Location %s; & { Set-Location %s }; git reset --hard" % (C_, D), dirty),
    (PSTOOL, "Set-Location %s; if ($true) { Set-Location %s }; git reset --hard" % (C_, D), dirty),
    (WIN, "Set-Location %s; . { cd %s }; git reset --hard" % (C_, D), dirty),
    (MIXED, "Set-Location %s; & { cd %s }; git reset --hard" % (C_, D), dirty),
    (PSTOOL, "Push-Location %s; if (1) { Pop-Location }; git reset --hard" % C_, dirty),
    (PSTOOL, "& { Push-Location %s }; Pop-Location; git reset --hard" % C_, dirty),
    (PSTOOL, "Push-Location %s; & { Pop-Location; git reset --hard }" % C_, dirty),
    # I3: common parameters, -L, and -- are real moves
    (PSTOOL, "Set-Location %s; Set-Location -ErrorAction Stop %s; git reset --hard" % (C_, D), dirty),
    (WIN, "Set-Location %s; Set-Location %s -ErrorAction Stop; git reset --hard" % (C_, D), dirty),
    (PSTOOL, "Set-Location -L %s; git reset --hard" % D, other),
    (MIXED, "Set-Location -L %s; git reset --hard" % D, other),
    (PSTOOL, "Set-Location -- %s; git reset --hard" % D, other),
    (PSTOOL, "Push-Location -Verbose %s; git reset --hard" % D, other),
    (PSTOOL, "Set-Location %s -ErrorAction Stop; git reset --hard" % D, other),
    (PSTOOL, "Set-Location -EA Stop %s; git reset --hard" % D, other),
    # M1: PowerShell reads /c/... as <current drive>/c/..., not a Git Bash drive path: a
    # non-existent one fails and stays (no bash /c/ -> C:/ conversion in this reading)
    (PSTOOL, "cd /qq_no_such_root_9f2/Users; git reset --hard", dirty),
    # uncertain targets keep the old candidates
    (PSTOOL, "Set-Location $repo; git reset --hard", dirty),
    (PSTOOL, "Set-Location -Pa %s; git reset --hard" % C_, dirty),
]
for (tool, builder), cmd, cwd in b8_block:
    rc, err = guard(tool, builder, cmd, cwd)
    check("B8 %s: `%s` is BLOCKED" % (tool, cmd.replace(D, "<dirty>").replace(C_, "<clean>")),
          rc == 2 and "destructive-git-guard" in err, "rc=%s err=%r" % (rc, err[-200:]))
b8_allow = [
    (PSTOOL, "Set-Location -ErrorAction Stop %s; git reset --hard" % C_, other2),
    (PSTOOL, "Set-Location -LiteralPath %s; git reset --hard" % C_, other2),
    (MIXED, "Set-Location %s; git reset --hard" % C_, other2),
    (PSTOOL, "git -C %s reset --hard" % C_, dirty),  # the way through: -C is exact
]
for (tool, builder), cmd, cwd in b8_allow:
    rc, err = guard(tool, builder, cmd, cwd)
    check("B8 %s: control `%s` is allowed" % (tool, cmd.replace(D, "<dirty>").replace(C_, "<clean>")),
          rc == 0, "rc=%s err=%r" % (rc, err[-200:]))


print("== B9: REFUTE round-4 regressions (union-only PowerShell location tracking) ==")
b9_block = [
    # N1: untracked pushes
    (PSTOOL, "Push-Location; Set-Location %s; Pop-Location; git reset --hard" % C_, dirty),
    (WIN, "Push-Location -PassThru; Set-Location %s; Pop-Location; git reset --hard" % C_, dirty),
    (MIXED, "Push-Location; Set-Location %s; Pop-Location; git reset --hard" % C_, dirty),
    (PSTOOL, "& { Push-Location %s }; Set-Location %s; Pop-Location; git reset --hard" % (C_, C_), dirty),
    (PSTOOL, "function f { Push-Location %s }; f; Set-Location %s; Pop-Location; git reset --hard" % (C_, C_), dirty),
    # N2: a conditional move
    (PSTOOL, "git rev-parse --verify nope 2>$null && Set-Location %s; git reset --hard" % C_, dirty),
    (MIXED, "git rev-parse --verify HEAD >$null || Set-Location %s; git reset --hard" % C_, dirty),
    # N3: parameter-binding errors
    (PSTOOL, "Set-Location -WhatIf %s; git reset --hard" % C_, dirty),
    (WIN, "Set-Location -ErrorAction Bogus %s; git reset --hard" % C_, dirty),
    (PSTOOL, "Set-Location -StackName s %s; git reset --hard" % C_, dirty),
    (PSTOOL, "Set-Location -Path %s -LiteralPath %s; git reset --hard" % (C_, C_), dirty),
    # N4: `$` targets
    (PSTOOL, "Set-Location '$env:TEMP'; git reset --hard", dirty),
    (PSTOOL, "$env:TEMP = '.'; Set-Location $env:TEMP; git reset --hard", dirty),
    # N5: Win32 vs provider normalisation
    (PSTOOL, "Set-Location %s.; git reset --hard" % C_, dirty),
    (PSTOOL, 'Set-Location "%s "; git reset --hard' % C_, dirty),
    # never-run body, and the earlier `cd <clean>; pop` case: the cwd stays a candidate
    (PSTOOL, "function f { cd %s }; Set-Location %s; git reset --hard" % (D, C_), dirty),
    (PSTOOL, "Set-Location %s; Pop-Location; git reset --hard" % C_, dirty),
]
for (tool, builder), cmd, cwd in b9_block:
    rc, err = guard(tool, builder, cmd, cwd)
    check("B9 %s: `%s` is BLOCKED" % (tool, cmd.replace(D, "<dirty>").replace(C_, "<clean>")),
          rc == 2 and "destructive-git-guard" in err, "rc=%s err=%r" % (rc, err[-200:]))
# Bash-tool parity: only `cd` moves, exactly as at HEAD.
fs_other2 = other2.replace("\\", "/")
rc, err = guard("Bash", FORMS[0][1], "cd %s && git reset --hard" % fs_other2, dirty)
check("B9 Bash: `cd <clean> && git reset --hard` from a dirty cwd is still allowed (HEAD parity)",
      rc == 0, "rc=%s err=%r" % (rc, err[-200:]))


print("== B10: REFUTE round-5 tokenizer regressions (lone CR, Unicode blanks) ==")
CR, LS, PSEP, NEL = chr(13), chr(0x2028), chr(0x2029), chr(0x85)
b10 = [
    "# c" + CR + "git reset --hard",
    "echo a # c" + CR + "git reset --hard",
    "git commit -m x # note" + CR + "git reset --hard",
    "$x = @'" + CR + "\nhi" + CR + "'@" + CR + "git reset --hard",
    '$x = @"' + CR + "hi" + CR + '"@' + CR + "git reset --hard",
    "$x = @'\nhi" + CR + "'@; git reset --hard",
    "echo a;" + LS + "git reset --hard",
    NEL + "git reset --hard",
    PSEP + "git reset --hard",
    "git reset `" + CR + "--hard",
]
for cmd in b10:
    for tool, builder in (PSTOOL, WIN, MIXED):
        rc, err = guard(tool, builder, cmd, dirty)
        check("B10 %s: %r is BLOCKED" % (tool, cmd), rc == 2 and "destructive-git-guard" in err,
              "rc=%s err=%r" % (rc, err[-200:]))
check("B10 ps: U+2028 separates words, a CR ends a comment",
      subs("git" + LS + "reset --hard", PS) == [["reset", "--hard"]]
      and subs("# x" + CR + "git status", PS) == [["status"]],
      repr((subs("git" + LS + "reset --hard", PS), subs("# x" + CR + "git status", PS))))
check("B10 ps: a CRLF here-string body still decodes and stays opaque",
      subs("git commit -m @'\r\nline; git reset --hard\r\n'@; git status", PS)
      == [["commit", "-m", "line; git reset --hard"], ["status"]],
      repr(subs("git commit -m @'\r\nline; git reset --hard\r\n'@; git status", PS)))


print("== B11: REFUTE round-6 regressions (bash reading always kept; control chars) ==")
b11 = [
    "if ($true) { echo a }# don't\ngit reset --hard",
    "foreach ($f in 1..2) { echo $f }# it's done\ngit reset --hard",
    'Write-Host "Done"# it' + "'" + 's ok\ngit reset --hard',
    "$n = 5# don't touch\ngit reset --hard",
    "(Get-Date)# it's\ngit reset --hard",
    "$h=@{a=1}# it's\ngit reset --hard",
    "echo a " + chr(0x1d) + "# ; git reset --hard",
    "echo " + chr(0x1f) + "<#x; git reset --hard #>",
    "echo " + chr(0x1c) + "--% x; git reset --hard",
    "echo --%" + chr(0x1c) + "a; git reset --hard",
]
for cmd in b11:
    for tool, builder in (PSTOOL, WIN):
        rc, err = guard(tool, builder, cmd, dirty)
        check("B11 %s: %r is BLOCKED" % (tool, cmd), rc == 2 and "destructive-git-guard" in err,
              "rc=%s err=%r" % (rc, err[-200:]))
check("B11 ps: U+001C-001F are not word separators",
      not gcp._ps_is_blank(chr(0x1c)) and not gcp._ps_is_blank(chr(0x1f)) and gcp._ps_is_blank(chr(0x2028)))


print("== B12: REFUTE round-7 (bash reading first, stop at first hit; mid-word @') ==")
import time  # noqa: E402
long_cmd = "; ".join(["Set-Location %s" % win_other] * 120 + ["Set-Location %s" % win_dirty]
                     + ["git reset --hard"] * 4)
t0 = time.time()
rc, err = guard(PSTOOL[0], PSTOOL[1], long_cmd, dirty)
took = time.time() - t0
check("B12 PowerShell: a 120-cd script ending in a dirty reset is BLOCKED quickly (%.1fs)" % took,
      rc == 2 and took < 30, "rc=%s took=%.1fs" % (rc, took))
check("B12 findings(): pass 0 is the exact old reading and a hit there ends the scan",
      bool(dgg.findings.__doc__) and "PASS 0" in dgg.findings.__doc__)
check("B12 ps: `@'` in the middle of a word is not a here-string",
      subs("echo a@'\n'; git reset --hard\n'@ '", PS) == [["reset", "--hard"]]
      or ["reset", "--hard"] in subs("echo a@'\n'; git reset --hard\n'@ '", PS),
      repr(subs("echo a@'\n'; git reset --hard\n'@ '", PS)))


print("== B13: REFUTE round-8 (pass 0 = the exact old reading, at the old cost) ==")
pushd_cmd = "\n".join(["pushd %s" % fs_other, "git pull --ff-only"] * 40 + ["git reset --hard"])
for tool, builder in (PSTOOL, MIXED):
    t0 = time.time()
    rc, err = guard(tool, builder, pushd_cmd, dirty)
    took = time.time() - t0
    check("B13 %s: 40x `pushd <fwd-slash clean>; git pull` then a dirty reset is BLOCKED quickly (%.1fs)"
          % (tool, took), rc == 2 and took < 30, "rc=%s took=%.1fs" % (rc, took))


print("== B14: REFUTE round-9 (pass 0 keeps the old guard's sticky unknown directory) ==")
fs_dirty_ = dirty.replace("\\", "/")
many = "git reset --hard; cd /c/nonexistent_b14_q; git -C %s checkout %s" % (
    fs_dirty_, " ".join("zz%d" % i for i in range(1500)))
for tool, builder in (FORMS[0], PSTOOL):
    t0 = time.time()
    rc, err = guard(tool, builder, many, dirty)
    took = time.time() - t0
    check("B14 %s: a hit, a bad cd, then 1500 absolute -C probes is BLOCKED quickly (%.1fs)"
          % (tool, took), rc == 2 and took < 20, "rc=%s took=%.1fs" % (rc, took))
rc, err = guard(PSTOOL[0], PSTOOL[1], "popd; git -C %s reset --hard" % win_dirty, other)
check("B14 PowerShell: the wider readings still resolve an absolute -C after an unknown cd",
      rc == 2, "rc=%s err=%r" % (rc, err[-200:]))


print("== B15: REFUTE round-10 (pass 0 does not record a pull whose directory is unknown) ==")
_seen_fetches = []
_orig_mh = dgg.memory_hazard
try:
    dgg.memory_hazard = lambda where, sub, args, fetches, cfg: (_seen_fetches.append(list(fetches)) or [])
    dgg._findings_one("git -C /nonexist_b15 pull; git reset --hard", dirty, "bash", mixed=False, legacy=True)
finally:
    dgg.memory_hazard = _orig_mh
check("B15 pass 0: the later reset's memory probe sees NO recorded pull (as at HEAD)",
      _seen_fetches == [[]], repr(_seen_fetches))

print()
if FAILS:
    print("test-shell-chain-git-guards: %d FAILED: %s" % (len(FAILS), ", ".join(FAILS)))
    sys.exit(1)
print("test-shell-chain-git-guards: ALL PASS")
sys.exit(0)
