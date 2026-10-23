"""Tests for hooks/sensitive-file-guard.py (R-06 / audit M65).

Run: python test-sensitive-file-guard.py
Parity with the inline settings.json blocker on Edit/Write, plus the shapes it missed.
Stdlib only. ASCII-only. Windows (`python`).
"""
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HOOKS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOK = os.path.join(HOOKS_DIR, "sensitive-file-guard.py")
INLINE_RE = re.compile(r"(credentials|\.env|password)", re.IGNORECASE)
DC = "mcp__Desktop_Commander__"
_failures = []


def check(name, cond, detail=""):
    if cond:
        print("PASS " + name)
    else:
        print("FAIL " + name + ("  " + detail if detail else ""))
        _failures.append(name)


def run(tool, tool_input, raw=None):
    payload = raw if raw is not None else json.dumps({"tool_name": tool, "tool_input": tool_input})
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    p = subprocess.run([sys.executable, "-I", HOOK], input=payload.encode("utf-8"),
                       capture_output=True, env=env, timeout=60)
    return p.returncode, p.stderr.decode("utf-8", "replace")


def test_new_shapes():
    rc, err = run("MultiEdit", {"file_path": "C:/x/.env", "edits": []})
    check("S1 MultiEdit to .env is blocked with the inline message",
          rc == 2 and "BLOCKED: Cannot edit sensitive file: C:/x/.env" in err, err[-160:])
    check("S2 NotebookEdit to credentials.ipynb is blocked",
          run("NotebookEdit", {"notebook_path": "C:/x/credentials.ipynb"})[0] == 2)
    check("S3 DC write_file (path field) to password.txt is blocked",
          run(DC + "write_file", {"path": "C:/x/password.txt", "content": "x"})[0] == 2)
    check("S4 DC move_file onto .env.local is blocked",
          run(DC + "move_file", {"source": "C:/x/a.txt", "destination": "C:/x/.env.local"})[0] == 2)
    check("S5 DC decoy: path=.env with an innocent file_path is blocked",
          run(DC + "write_file", {"path": "C:/x/.env", "file_path": "C:/x/ok.md",
                                  "content": "x"})[0] == 2)


def test_parity_and_passes():
    paths = ["C:/x/readme.md", "C:/x/.env", "C:/x/.ENV", "C:/x/aws_credentials.json",
             "C:/x/Password-list.txt", "C:/x/environment.md", "C:/x/app.envrc",
             "C:/x/src/index.html"]
    for p in paths:
        want = 2 if INLINE_RE.search(p) else 0
        for tool in ("Edit", "Write"):
            got = run(tool, {"file_path": p, "content": "x", "old_string": "a",
                             "new_string": "b"})[0]
            check("S6 parity %s %s -> %d" % (tool, p, want), got == want, "got=%d" % got)
    check("S7 garbage stdin fails open", run(None, None, raw="{bad")[0] == 0)
    check("S8 Bash is out of scope", run("Bash", {"command": "echo x > .env"})[0] == 0)


def test_chain_membership():
    spec = importlib.util.spec_from_file_location(
        "_sfg_disp", os.path.join(HOOKS_DIR, "pretooluse-dispatcher.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    check("S9 sensitive-file-guard is in GUARD_CHAIN",
          "sensitive-file-guard" in mod.GUARD_CHAIN)
    check("S10 sensitive-file-guard is NOT in BASH_GUARD_CHAIN",
          "sensitive-file-guard" not in mod.BASH_GUARD_CHAIN)


def test_lib_missing_fails_open():
    """C7: with lib/tool_call_paths.py absent the guard must exit 0 (fail open)."""
    tmp = tempfile.mkdtemp(prefix="sfg_scratch_")
    try:
        shutil.copy2(HOOK, os.path.join(tmp, "sensitive-file-guard.py"))
        shutil.copytree(os.path.join(HOOKS_DIR, "lib"), os.path.join(tmp, "lib"),
                        ignore=shutil.ignore_patterns("__pycache__"))
        os.remove(os.path.join(tmp, "lib", "tool_call_paths.py"))
        payload = json.dumps({"tool_name": "Write",
                              "tool_input": {"file_path": "C:/x/.env", "content": "x"}})
        env = dict(os.environ)
        env.pop("PYTHONPATH", None)
        p = subprocess.run([sys.executable, "-I", os.path.join(tmp, "sensitive-file-guard.py")],
                           input=payload.encode("utf-8"), capture_output=True, env=env,
                           timeout=60)
        check("S11 missing lib/tool_call_paths.py fails open (exit 0)", p.returncode == 0,
              "rc=%d %s" % (p.returncode, p.stderr.decode("utf-8", "replace")[-160:]))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    test_new_shapes()
    test_parity_and_passes()
    test_chain_membership()
    test_lib_missing_fails_open()
    if _failures:
        print("\n%d FAILURE(S): %s" % (len(_failures), ", ".join(_failures[:12])))
        sys.exit(1)
    print("\nALL sensitive-file-guard tests passed.")
    sys.exit(0)
