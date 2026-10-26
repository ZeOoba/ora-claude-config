"""Standalone test for hooks/pipe-mask-guard.py and the dispatcher plumbing it
relies on.

WHAT IT ENFORCES (2026-10-23, /insights friction F1a): an EVIDENCE command
(push, commit, gate, test run) in a non-last pipeline stage has its exit status
discarded by bash. The guard rewrites such a command, via PreToolUse
updatedInput, to start with `set -o pipefail; ` -- never blocks, never sets a
permissionDecision (that would auto-approve the command).

Every rewrite check drives BOTH the script and the dispatcher's in-process path.
Run: python hooks/tests/test-pipe-mask-guard.py
"""
import io
import importlib.util
import json
import os
import subprocess
import sys
import tempfile

HOOKS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GUARD = os.path.join(HOOKS, "pipe-mask-guard.py")
DISPATCHER = os.path.join(HOOKS, "pretooluse-dispatcher.py")
PY = sys.executable
PREFIX = "set -o pipefail; "
FAILS = []
PASSES = [0]

_FIXTURE_DIR = tempfile.mkdtemp(prefix="pmg-")
_SETTINGS = os.path.join(_FIXTURE_DIR, "settings.json")
with open(_SETTINGS, "w", encoding="utf-8") as _fh:
    json.dump({"permissions": {"deny": [
        "Bash(git push --force*)", "Bash(git reset --hard*)", "Read(./.env)"]}}, _fh)
ENV = dict(os.environ)
ENV["ORA_PIPEMASK_SETTINGS"] = _SETTINGS


def payload(cmd, tool="Bash", extra=None):
    ti = {"command": cmd, "description": "d", "timeout": 120000}
    if extra:
        ti.update(extra)
    return json.dumps({"tool_name": tool, "tool_input": ti, "cwd": _FIXTURE_DIR,
                       "session_id": "pmg-test", "hook_event_name": "PreToolUse"})


def run(raw, via="script", env=None):
    if via == "script":
        argv = [PY, GUARD]
    else:
        argv = [PY, "-c", (
            "import sys, importlib.util as u; s=u.spec_from_file_location('d', %r); "
            "m=u.module_from_spec(s); s.loader.exec_module(m); "
            "rc,o,e,mode=m.run_guard('pipe-mask-guard', sys.stdin.buffer.read()); "
            "sys.stdout.write(o); sys.stderr.write(e+'|mode='+mode); sys.exit(rc)")
            % DISPATCHER]
    r = subprocess.run(argv, input=raw.encode("utf-8"), capture_output=True,
                       env=env or ENV, timeout=60)
    out = r.stdout.decode("utf-8", "replace")
    err = r.stderr.decode("utf-8", "replace")
    if via == "dispatcher" and "|mode=inprocess" not in err:
        FAILS.append("dispatcher did not run pipe-mask-guard in-process: " + err[-200:])
    return r.returncode, out, err


def ok(name, cond, detail=""):
    if cond:
        PASSES[0] += 1
    else:
        FAILS.append("%s %s" % (name, detail))


def expect_rewrite(name, cmd, vias=("script", "dispatcher")):
    for via in vias:
        rc, out, err = run(payload(cmd), via)
        try:
            hso = json.loads(out)["hookSpecificOutput"]
        except Exception:  # noqa: BLE001
            FAILS.append("%s [%s]: no JSON output (rc=%s out=%r err=%r)"
                         % (name, via, rc, out[:200], err[-200:]))
            continue
        ui = hso.get("updatedInput") or {}
        ok("%s [%s] rc 0" % (name, via), rc == 0, "rc=%s" % rc)
        ok("%s [%s] prefixed" % (name, via), ui.get("command") == PREFIX + cmd,
           repr(ui.get("command")))
        ok("%s [%s] keeps other input fields" % (name, via),
           ui.get("description") == "d" and ui.get("timeout") == 120000, repr(ui))
        ok("%s [%s] never sets permissionDecision" % (name, via),
           "permissionDecision" not in hso, repr(hso))
        ok("%s [%s] event name" % (name, via),
           hso.get("hookEventName") == "PreToolUse", repr(hso))


def expect_untouched(name, cmd, tool="Bash", raw=None):
    rc, out, err = run(raw if raw is not None else payload(cmd, tool))
    ok("%s rc 0" % name, rc == 0, "rc=%s err=%r" % (rc, err[-200:]))
    ok("%s no output" % name, out.strip() == "", repr(out[:200]))


def test_rewrites():
    expect_rewrite("push|tail", "git push origin main 2>&1 | tail -3")
    # A leading pure `cd <dir> &&` is allowed: pipefail does not change cd.
    expect_rewrite("cd && gate|tail", "cd /c/x && npm run gate:ci 2>&1 | tail -25")
    expect_rewrite("prepush gate|tail",
                   "python hooks/git-prepush-hook-tests-gate.py < NUL | tail -40")
    expect_rewrite("refute|grep",
                   "npx tsx scripts/check-refute-required.ts --strict | grep FAIL")
    expect_rewrite("pytest -m|tail", "python -m pytest -q | tail -1")
    expect_rewrite("gh merge|cat", "gh pr merge 12 --squash | cat")
    expect_rewrite("git -C commit|tail", "git -C C:/x commit -m 'a b' | tail -2")
    expect_rewrite("env push|tail", "GIT_TRACE=0 git push | tail")
    expect_rewrite("pytest|tee", "pytest | tee log.txt")
    expect_rewrite("verify-push|grep",
                   "python maintenance/verify-push.py --repo x | grep RESULT")
    expect_rewrite("npm test|tail", "npm test 2>&1 | tail")
    expect_rewrite("hook test file|tail",
                   "python C:/Users/Owner/.claude/hooks/tests/test-winpath-guard.py | tail -3")
    expect_rewrite("pipe-stderr", "git push |& tail -3")
    expect_rewrite("python -X utf8 test file|tail",
                   "python -X utf8 hooks/tests/test-x.py | tail")
    expect_rewrite("python -W error test file|tail",
                   "python -W error hooks/tests/test_x.py | tail -3")
    expect_rewrite("uv run pytest|tail", "uv run pytest -q | tail -2")
    expect_rewrite("make test|tail", "make test 2>&1 | tail -20")
    expect_rewrite("gh -R o/r pr merge|cat", "gh -R o/r pr merge 12 --squash | cat")
    expect_rewrite("timeout -k push|tail", "timeout -k 5 60 git push origin main | tail")
    expect_rewrite("cd && trailing semicolon", "cd /c/x && git push | tail -2;")
    expect_rewrite("full python path",
                   "C:/Users/Owner/AppData/Local/Programs/Python/Python313/python.exe "
                   "-m pytest | tail -2")


def test_untouched():
    expect_untouched("look-only pipe", "git log --oneline | head -5")
    expect_untouched("no pipe", "git push origin main")
    expect_untouched("redirect to file", 'npm run gate:ci > out.txt 2>&1; echo "EXIT: $?"')
    expect_untouched("already pipefail", "set -o pipefail; git push | tail")
    expect_untouched("PIPESTATUS", "git push | tail; echo ${PIPESTATUS[0]}")
    expect_untouched("quoted pipe text", "echo 'git push | tail'")
    expect_untouched("evidence LAST stage", "cat msg.txt | git commit -F -")
    expect_untouched("or-operator", "git push || echo failed")
    expect_untouched("deny rule match", "git push --force origin x | tail")
    # F-I: deny rules are also checked against the stage with env assignments
    # and transparent wrappers stripped (the harness matches the bare command)
    expect_untouched("deny rule via env prefix", "GIT_TRACE=0 git push --force o x | tail")
    expect_untouched("deny rule via time wrapper", "time git push --force o x | tail")
    expect_untouched("deny rule via timeout wrapper",
                     "timeout 60 git push --force o x | tail")
    expect_untouched("unparseable", "git push | tail 'unterminated")
    expect_untouched("non-Bash tool", "git push | tail", tool="PowerShell")
    expect_untouched("malformed json", "", raw="{not json")
    expect_untouched("empty command", "")
    expect_untouched("test word not a script", "echo test-run | tail")
    # F-E: the prefix is command-wide, so only a SINGLE statement is rewritten
    expect_untouched("multi-line", "cd x\ngit push 2>&1 | tail -3")
    expect_untouched("push then a look-only pipe",
                     "git push 2>&1 | tail -2; git log --oneline | head -1")
    expect_untouched("two statements with &&",
                     "git push 2>&1 | tail -2 && git log --oneline | head -1")
    expect_untouched("evidence pipe then echo status",
                     'npm run gate:ci 2>&1 | tail -3; echo "done"')
    expect_untouched("background", "git push 2>&1 | tail -2 &")
    expect_untouched("subshell", "(git push 2>&1 | tail -2)")
    expect_untouched("grep in the middle of a pipe",
                     "git push 2>&1 | grep -v hint | tail -1")
    expect_untouched("leading look-only pipe", "echo ok | grep -v ok | tail -1")
    expect_untouched("cd hop with a look-only pipe after", "cd x && git log | head -1")
    # F-E: look-only flags are not evidence
    expect_untouched("pytest --collect-only", "pytest --collect-only | tail -5")
    expect_untouched("python -m pytest --collect-only",
                     "python -m pytest --collect-only -q | tail")
    expect_untouched("jest --listTests", "npx jest --listTests | tail")
    expect_untouched("tsc --version", "npx tsc --version | cat")
    expect_untouched("pytest --help", "pytest --help | head -20")
    expect_untouched("pytest -h", "pytest -h | tail")
    # F-J: inline code is not a script
    expect_untouched("python -c", 'python -c "print(1)" | tail')
    # F-F support: the word pipefail in a message is not a pipefail setting
    expect_rewrite_msg = "git commit -m 'document pipefail' 2>&1 | tail -2"
    rc, out, _ = run(payload(expect_rewrite_msg))
    ok("pipefail word in a message still gets the rewrite",
       PREFIX in out, repr(out[:200]))
    rc, out, _ = run(payload("git commit -m \"set pipefail note\" | tail"))
    ok("`set pipefail` inside a quoted message still gets the rewrite",
       PREFIX in out, repr(out[:200]))


def test_early_exit_last_stage():
    """/insights review 2026-10-26 (C3): a LAST stage that quits before EOF
    (`head -N`, `grep -q/-m/-l`, `sed 1q`, `read`, `less`, `more`) SIGPIPEs the
    evidence command, so under pipefail a PASSING run reports rc 120/141, and
    `cmd | grep -q x` inverts to 1 when cmd fails. Those commands are left as
    written (status quo); consumers that read to EOF are still rewritten."""
    for name, cmd in (
            ("head -2", "python -m pytest -v tests/test_many.py | head -2"),
            ("head -n 5", "npm run gate 2>&1 | head -n 5"),
            ("head -c", "pytest -q | head -c 200"),
            ("grep -q", "git push origin main 2>&1 | grep -q rejected"),
            ("grep --quiet", "git push 2>&1 | grep --quiet rejected"),
            ("grep -m1", "npm run gate 2>&1 | grep -m1 FAIL"),
            ("grep -m 1", "npm run gate 2>&1 | grep -m 1 FAIL"),
            ("grep --max-count", "npm run gate 2>&1 | grep --max-count=1 FAIL"),
            ("grep -l", "npm test 2>&1 | grep -l FAIL"),
            ("grep -ql combined", "npm test 2>&1 | grep -ql FAIL"),
            ("egrep -q", "pytest | egrep -q 'passed'"),
            ("rg -q", "pytest | rg -q passed"),
            ("sed 1q", "pytest | sed 1q"),
            ("sed -n 5q", "pytest | sed -n '5q'"),
            ("sed /re/q", "pytest | sed '/passed/q'"),
            ("read", "pytest | read first"),
            ("less", "pytest | less"),
            ("more", "pytest | more"),
            ("full path head", "pytest | /usr/bin/head -3"),
            ("cd hop head", "cd /c/x && npm run gate:ci 2>&1 | head -25"),
            ("tee then head", "pytest | tee log.txt | head -3"),
            ("env/wrapper head", "pytest | env LC_ALL=C head -2"),
            ("sed -e1q attached", "pytest | sed -e1q"),
            ("sed --expression=1q", "pytest | sed --expression=1q"),
            ("sed /re/!q", "pytest | sed '/1/!q'"),
            ("sed /re/Iq", "pytest | sed '/x/Iq'"),
            ("grep --max=1 abbreviated", "pytest | grep --max=1 FAIL"),
            ("grep --quie abbreviated", "pytest | grep --quie FAIL"),
    ):
        expect_untouched("early-exit last stage: " + name, cmd)
    # Consumers that read to EOF keep the protection.
    expect_rewrite("grep without -q", "npm run gate 2>&1 | grep FAIL")
    expect_rewrite("grep -v", "npm run gate 2>&1 | grep -v hint")
    expect_rewrite("grep -c counts to EOF", "pytest | grep -c passed")
    expect_rewrite("sed s///", "pytest | sed 's/a/b/'")
    expect_rewrite("sed -n 1p reads to EOF", "pytest | sed -n 1p")
    expect_rewrite("sed -e with q inside the replacement text",
                   "pytest | sed 's/quit/exit/'")
    expect_rewrite("tail", "pytest | tail -5")
    expect_rewrite("wc", "pytest | wc -l")
    expect_rewrite("cat", "pytest | cat")


def test_unreadable_settings_does_not_rewrite():
    """Rewriting changes the string permission rules are matched against. With
    the deny list unreadable we cannot prove the prefix does not dodge a deny
    rule, so the command is left exactly as written (status quo)."""
    env = dict(ENV)
    env["ORA_PIPEMASK_SETTINGS"] = os.path.join(_FIXTURE_DIR, "missing.json")
    rc, out, _ = run(payload("git push | tail"), env=env)
    ok("unreadable settings: rc 0", rc == 0)
    ok("unreadable settings: untouched", out.strip() == "", repr(out[:200]))


def _load_dispatcher():
    spec = importlib.util.spec_from_file_location("_pmg_disp", DISPATCHER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _emit(disp, chunks):
    real_out, real_err = sys.stdout, sys.stderr
    out, err = io.StringIO(), io.StringIO()
    try:
        sys.stdout, sys.stderr = out, err
        disp.emit_stdout(chunks)
    finally:
        sys.stdout, sys.stderr = real_out, real_err
    return out.getvalue(), err.getvalue()


def test_dispatcher_merge_carries_updated_input():
    disp = _load_dispatcher()
    rewrite = json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "updatedInput": {"command": PREFIX + "git push | tail"}}})
    other = json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse", "additionalContext": "note"}})
    out, _ = _emit(disp, [other, rewrite])
    hso = json.loads(out)["hookSpecificOutput"]
    ok("merge keeps updatedInput", hso.get("updatedInput", {}).get("command")
       == PREFIX + "git push | tail", repr(hso))
    ok("merge keeps additionalContext", hso.get("additionalContext") == "note")

    second = json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse", "updatedInput": {"command": "other"}}})
    out, err = _emit(disp, [rewrite, second])
    hso = json.loads(out)["hookSpecificOutput"]
    ok("conflict: first rewrite wins", hso["updatedInput"]["command"]
       == PREFIX + "git push | tail", repr(hso))
    ok("conflict: announced on stderr", "conflicting updatedInput" in err, repr(err))


def test_chain_position():
    disp = _load_dispatcher()
    chain = disp.BASH_GUARD_CHAIN
    ok("pipe-mask-guard is LAST in the Bash chain (a blocking guard must "
       "short-circuit before any rewrite is emitted)",
       chain and chain[-1] == "pipe-mask-guard", repr(chain))
    ok("pipe-mask-guard only in the Bash chain",
       "pipe-mask-guard" not in disp.GUARD_CHAIN)


def main():
    for t in (test_rewrites, test_untouched, test_early_exit_last_stage,
              test_unreadable_settings_does_not_rewrite,
              test_dispatcher_merge_carries_updated_input, test_chain_position):
        try:
            t()
        except Exception as e:  # noqa: BLE001
            FAILS.append("%s raised %s: %s" % (t.__name__, type(e).__name__, e))
    for f in FAILS:
        print("FAIL " + f)
    print("test-pipe-mask-guard: %d pass, %d fail" % (PASSES[0], len(FAILS)))
    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    main()
