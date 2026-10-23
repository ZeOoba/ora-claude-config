"""Tests for hooks/override-mint-guard.py (R-06).

Run: python test-override-mint-guard.py
Stdlib only. ASCII-only. Windows (`python`).
"""
import json
import os
import subprocess
import sys
import tempfile

HOOKS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOK = os.path.join(HOOKS_DIR, "override-mint-guard.py")
SESSION_A = "aaaaaaaa-1111-2222-3333-444444444444"
SESSION_S = "cccccccc-1111-2222-3333-444444444444"
SESSION_C = "dddddddd-1111-2222-3333-444444444444"
TOKEN = "C:/Users/Owner/.claude/hooks/sessions/%s/overrides/allow-mcp-delete"
_failures = []


def check(name, cond, detail=""):
    if cond:
        print("PASS " + name)
    else:
        print("FAIL " + name + ("  " + detail if detail else ""))
        _failures.append(name)


def make_env(entrypoint="claude-desktop"):
    store = tempfile.mkdtemp(prefix="omg-store-")
    for name, rec in (("local_a.json", {"cliSessionId": SESSION_A}),
                      ("local_s.json", {"cliSessionId": SESSION_S,
                                        "scheduledTaskId": "ora-test-task"})):
        with open(os.path.join(store, name), "w", encoding="utf-8") as fh:
            json.dump(rec, fh)
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    env.update({"ORA_SESSION_STORE_DIRS": store, "CLAUDE_CODE_ENTRYPOINT": entrypoint,
                "ORA_GUARD_TELEMETRY": "0"})
    return env


def run(env, tool, tool_input, sid, raw=None, cwd=None, hook=None):
    body = {"tool_name": tool, "tool_input": tool_input, "session_id": sid}
    if cwd is not None:
        body["cwd"] = cwd
    payload = raw if raw is not None else json.dumps(body)
    p = subprocess.run([sys.executable, "-I", hook or HOOK], input=payload.encode("utf-8"),
                       capture_output=True, env=env, timeout=60)
    return p.returncode, p.stderr.decode("utf-8", "replace")


def test_blocks_scheduled_mints():
    env = make_env()
    rc, err = run(env, "Write", {"file_path": TOKEN % SESSION_S, "content": "scope: x"},
                  SESSION_S)
    check("M1 scheduled Write into overrides/ is blocked",
          rc == 2 and "override-mint-guard" in err, err[-200:])
    rc, _ = run(env, "MultiEdit", {"file_path": TOKEN % SESSION_A, "edits": []}, SESSION_S)
    check("M2 scheduled MultiEdit into ANOTHER session's overrides/ is blocked", rc == 2)
    cmd = ("echo scope: mcp-delete > C:\\Users\\Owner\\.claude\\hooks\\sessions\\%s"
           "\\overrides\\allow-mcp-delete" % SESSION_S)
    check("M3 scheduled Bash naming an overrides path (backslashes) is blocked",
          run(env, "Bash", {"command": cmd}, SESSION_S)[0] == 2)
    env2 = make_env(entrypoint="sdk-cli")
    check("M4 headless entrypoint without a record is blocked",
          run(env2, "Write", {"file_path": TOKEN % SESSION_C, "content": "x"}, SESSION_C)[0] == 2)


def test_allows_everything_else():
    env = make_env()
    check("M5 interactive Write into overrides/ is allowed (Gabriel-approved mint)",
          run(env, "Write", {"file_path": TOKEN % SESSION_A, "content": "x"}, SESSION_A)[0] == 0)
    check("M6 plain CLI (no record, cli entrypoint) is allowed",
          run(make_env("cli"), "Write", {"file_path": TOKEN % SESSION_C, "content": "x"},
              SESSION_C)[0] == 0)
    check("M7 scheduled ordinary Write is allowed",
          run(env, "Write", {"file_path": "C:/Users/Owner/x/report.md", "content": "x"},
              SESSION_S)[0] == 0)
    check("M8 scheduled ordinary Bash is allowed",
          run(env, "Bash", {"command": "git status"}, SESSION_S)[0] == 0)
    check("M9 garbage stdin fails open", run(env, None, None, SESSION_S, raw="{bad")[0] == 0)
    check("M10 non-dict tool_input fails open",
          run(env, "Write", ["x"], SESSION_S)[0] == 0)


def test_dispatcher_membership():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "_omg_disp", os.path.join(HOOKS_DIR, "pretooluse-dispatcher.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    # TEMPORARY UNWIRING: override-mint-guard is deliberately OUT of both dispatcher
    # chains pending the session_kind scan-budget fix (follow-up PR). Re-enable these
    # to assert membership (is in) once that fix lands and the guard is re-wired.
    check("M11 override-mint-guard is NOT in GUARD_CHAIN (temporarily unwired)",
          "override-mint-guard" not in mod.GUARD_CHAIN)
    check("M12 override-mint-guard is NOT in BASH_GUARD_CHAIN (temporarily unwired)",
          "override-mint-guard" not in mod.BASH_GUARD_CHAIN)
    check("M13 ascii-only-guard is still last in GUARD_CHAIN",
          mod.GUARD_CHAIN[-1] == "ascii-only-guard")


def BS(text):
    return text.replace("/", chr(92))


def test_scope_extension():
    env = make_env()
    env_i = make_env()
    sdir = "C:/Users/Owner/AppData/Roaming/Claude/claude-code-sessions/x/y/local_s.json"
    sched = (
        ("S1 Write fwd slash", "Write", {"file_path": sdir, "content": "{}"}),
        ("S2 Edit upper-case backslash", "Edit",
         {"file_path": BS(sdir).upper(), "old_string": "a", "new_string": "b"}),
        ("S3 MultiEdit path field", "MultiEdit", {"path": sdir, "edits": []}),
        ("S4 NotebookEdit notebook_path", "NotebookEdit",
         {"notebook_path": sdir, "new_source": "x"}),
        ("S5 Bash mklink", "Bash",
         {"command": BS("cmd /c mklink /J C:/tmp/h C:/Users/Owner/AppData/Roaming/Claude/claude-code-sessions")}),
        ("S6 Bash mv", "Bash",
         {"command": "mv /c/Users/Owner/AppData/Roaming/Claude/claude-code-sessions /c/tmp/x"}),
        ("S7 Bash Rename-Item", "Bash",
         {"command": BS("powershell -c Rename-Item $env:APPDATA/Claude/Claude-Code-Sessions old")}),
        ("S8 Bash robocopy", "Bash",
         {"command": BS("robocopy C:/a/claude-code-sessions C:/b /MOVE")}),
        ("S9 Bash python -c", "Bash",
         {"command": "python -c \"import shutil;shutil.move('x/claude-code-sessions','y')\""}),
        ("S10 Bash ORA_SESSION_STORE_DIRS", "Bash",
         {"command": "ORA_SESSION_STORE_DIRS=/tmp/fake claude -p hi"}),
        ("S11 Bash lower-case store dirs var", "Bash",
         {"command": BS("set ora_session_store_dirs=C:/fake")}),
        ("S12 Bash CLAUDE_CODE_ENTRYPOINT", "Bash",
         {"command": "export CLAUDE_CODE_ENTRYPOINT=cli; python x.py"}),
    )
    for name, tool, inp in sched:
        rc, err = run(env, tool, inp, SESSION_S)
        check(name + " blocked when scheduled", rc == 2 and "override-mint-guard" in err, err[-160:])
    for name, tool, inp in (
            ("S13 interactive Write", "Write", {"file_path": sdir, "content": "{}"}),
            ("S14 interactive Bash mklink", "Bash",
             {"command": BS("cmd /c mklink /J C:/tmp/h C:/x/claude-code-sessions")}),
            ("S15 interactive Bash store dirs var", "Bash",
             {"command": "ORA_SESSION_STORE_DIRS=/tmp/fake python t.py"}),
            ("S16 interactive Bash entrypoint", "Bash",
             {"command": "echo $CLAUDE_CODE_ENTRYPOINT"})):
        check(name + " allowed", run(env_i, tool, inp, SESSION_A)[0] == 0)
    check("S17 plain CLI (unknown, cli entrypoint) Bash naming it is allowed",
          run(make_env("cli"), "Bash", {"command": "ls claude-code-sessions"}, SESSION_C)[0] == 0)
    check("S18 desktop with no record (fail-closed scheduled) is blocked",
          run(env, "Bash", {"command": "ls claude-code-sessions"}, SESSION_C)[0] == 2)
    check("S19 scheduled ordinary Bash mentioning sessions generically allowed",
          run(env, "Bash", {"command": "echo sessions code claude"}, SESSION_S)[0] == 0)
    check("S20 scheduled Write to unrelated path allowed",
          run(env, "Write", {"file_path": "C:/x/notes.md", "content": "x"}, SESSION_S)[0] == 0)


SDIR = "C:/Users/Owner/.claude/hooks/sessions/%s" % SESSION_S


def test_path_evasions():
    env = make_env()
    env_i = make_env()
    blocked = (
        ("E1 persistent cwd under sessions/<sid>, relative overrides/ in a later call", "Bash",
         {"command": "mkdir -p overrides && printf 'scope: x' > overrides/allow-x"}, SDIR),
        ("E1b persistent cwd (backslash, upper-case)", "Bash",
         {"command": "echo x > overrides/allow-x"}, BS(SDIR).upper()),
        ("E2 one-liner cd sessions/<sid> && write X/overrides/", "Bash",
         {"command": "cd %s && printf x > ./a/overrides/allow-x" % SDIR}, "C:/tmp"),
        ("E3 doubled slashes hooks//sessions", "Bash",
         {"command": "echo x > C:/Users/Owner/.claude/hooks//sessions/%s//overrides/allow-x"
                     % SESSION_S}, None),
        ("E3b mixed doubled backslashes", "Bash",
         {"command": "echo x > " + BS("C:/Users/Owner/.claude/hooks/sessions/%s/overrides/a" % SESSION_S).replace(chr(92), chr(92) * 2)}, None),
        ("E4 dot segment hooks/./sessions", "Bash",
         {"command": "echo x > C:/Users/Owner/.claude/hooks/./sessions/%s/overrides/allow-x"
                     % SESSION_S}, None),
        ("E5 8.3 short name OVERRI~1", "Bash",
         {"command": "echo x > C:/Users/Owner/.claude/hooks/sessions/%s/OVERRI~1/allow-x"
                     % SESSION_S}, None),
        ("E5b 8.3 short name via cwd", "Bash",
         {"command": "echo x > OVERRI~1/allow-x"}, SDIR),
        ("E6 upper-case OVERRIDES path (kills removed-lower mutant)", "Write",
         {"file_path": "C:/USERS/OWNER/.CLAUDE/HOOKS/SESSIONS/%s/OVERRIDES/ALLOW-X"
                       % SESSION_S.upper(), "content": "x"}, None),
        ("E6b upper-case OVERRIDES Bash", "Bash",
         {"command": "echo x > C:/Users/Owner/.claude/Hooks/Sessions/%s/OVERRIDES/a"
                     % SESSION_S}, None),
        ("E7 relative Write overrides/ with cwd under sessions", "Write",
         {"file_path": "overrides/allow-x", "content": "x"}, SDIR),
    )
    for name, tool, inp, cwd in blocked:
        rc, err = run(env, tool, inp, SESSION_S, cwd=cwd)
        check(name + " blocked when scheduled", rc == 2 and "override-mint-guard" in err, err[-160:])
        check(name + " allowed when interactive", run(env_i, tool, inp, SESSION_A, cwd=cwd)[0] == 0)
    check("E8 scheduled ls hooks/sessions, no overrides token, other cwd, allowed",
          run(env, "Bash", {"command": "ls C:/Users/Owner/.claude/hooks/sessions"}, SESSION_S,
              cwd="C:/tmp")[0] == 0)
    check("E9 scheduled ordinary Bash with cwd under sessions (no token) allowed",
          run(env, "Bash", {"command": "ls -la"}, SESSION_S, cwd=SDIR)[0] == 0)
    check("E10 scheduled overrides token with unrelated cwd allowed",
          run(env, "Bash", {"command": "ls overrides/"}, SESSION_S, cwd="C:/tmp")[0] == 0)
    check("E11 interactive: persistent-cwd overrides write never blocked",
          run(env_i, "Bash", {"command": "printf x > overrides/allow-x"}, SESSION_A,
              cwd=SDIR.replace(SESSION_S, SESSION_A))[0] == 0)


def _poisoned_hook_dir(poison_tcp, poison_sk):
    """Copy of the hook with a lib/ whose modules are poisoned. Returns (hook, marker)."""
    import shutil
    root = tempfile.mkdtemp(prefix="omg-poison-")
    os.makedirs(os.path.join(root, "lib"))
    shutil.copy(HOOK, os.path.join(root, "override-mint-guard.py"))
    marker = os.path.join(root, "marker.txt")
    real_tcp = os.path.join(HOOKS_DIR, "lib", "tool_call_paths.py")
    real_sk = os.path.join(HOOKS_DIR, "lib", "session_kind.py")
    if poison_tcp:
        with open(os.path.join(root, "lib", "tool_call_paths.py"), "w", encoding="utf-8") as fh:
            fh.write("raise RuntimeError('poisoned tool_call_paths')\n")
    else:
        shutil.copy(real_tcp, os.path.join(root, "lib", "tool_call_paths.py"))
    if poison_sk:
        with open(os.path.join(root, "lib", "session_kind.py"), "w", encoding="utf-8") as fh:
            fh.write("open(%r, 'w').write('imported')\nraise RuntimeError('poisoned session_kind')\n"
                     % marker)
    else:
        shutil.copy(real_sk, os.path.join(root, "lib", "session_kind.py"))
    return os.path.join(root, "override-mint-guard.py"), marker


def test_fail_open_and_lazy_import():
    env = make_env()
    hook, _m = _poisoned_hook_dir(True, False)
    check("F1 broken tool_call_paths import fails open (ordinary Bash)",
          run(env, "Bash", {"command": "git status"}, SESSION_S, hook=hook)[0] == 0)
    check("F2 broken tool_call_paths import fails open (override path Write)",
          run(env, "Write", {"file_path": TOKEN % SESSION_S, "content": "x"}, SESSION_S,
              hook=hook)[0] == 0)
    hook, marker = _poisoned_hook_dir(False, True)
    rc = run(env, "Bash", {"command": "git status"}, SESSION_S, hook=hook)[0]
    check("F3 ordinary Bash: rc 0 and session_kind NOT imported on a miss",
          rc == 0 and not os.path.exists(marker))
    rc = run(env, "Write", {"file_path": "C:/x/notes.md", "content": "x"}, SESSION_S,
             hook=hook)[0]
    check("F4 ordinary Write: session_kind NOT imported on a miss",
          rc == 0 and not os.path.exists(marker))
    run(env, "Write", {"file_path": TOKEN % SESSION_S, "content": "x"}, SESSION_S, hook=hook)
    check("F5 control: session_kind IS imported on a hit (poison works)", os.path.exists(marker))


if __name__ == "__main__":
    test_blocks_scheduled_mints()
    test_allows_everything_else()
    test_scope_extension()
    test_path_evasions()
    test_fail_open_and_lazy_import()
    test_dispatcher_membership()
    if _failures:
        print("\n%d FAILURE(S): %s" % (len(_failures), ", ".join(_failures[:12])))
        sys.exit(1)
    print("\nALL override-mint-guard tests passed.")
    sys.exit(0)
