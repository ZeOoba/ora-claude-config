"""Standalone test for hooks/rewrite-advisory-guard.py.

WHAT IT ENFORCES (2026-10-28, /insights friction F1c): rewriting a file with
`sed -i`, `perl -i` or `python -c "...write..."` through Bash expands escape
sequences, eats backslashes and breaks newlines; the Edit/Write tools do not.
The guard is ADVISORY ONLY: it adds model-visible `additionalContext` and
nothing else. It never blocks (rc is always 0), never emits a permissionDecision
and never emits updatedInput. Every check drives BOTH the script and the
dispatcher's in-process path.

Run: python hooks/tests/test-rewrite-advisory-guard.py
"""
import json
import os
import subprocess
import sys

HOOKS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GUARD = os.path.join(HOOKS, "rewrite-advisory-guard.py")
DISPATCHER = os.path.join(HOOKS, "pretooluse-dispatcher.py")
PY = sys.executable
FAILS = []
PASSES = [0]


def run(raw, via):
    if via == "script":
        argv = [PY, GUARD]
    else:
        argv = [PY, "-c", (
            "import sys, importlib.util as u; s=u.spec_from_file_location('d', %r); "
            "m=u.module_from_spec(s); s.loader.exec_module(m); "
            "rc,o,e,mode=m.run_guard('rewrite-advisory-guard', sys.stdin.buffer.read()); "
            "sys.stdout.write(o); sys.stderr.write(e+'|mode='+mode); sys.exit(rc)") % DISPATCHER]
    r = subprocess.run(argv, input=raw.encode("utf-8"), capture_output=True, timeout=60)
    err = r.stderr.decode("utf-8", "replace")
    if via == "dispatcher" and "|mode=inprocess" not in err:
        FAILS.append("dispatcher did not run rewrite-advisory-guard in-process: " + err[-200:])
    return r.returncode, r.stdout.decode("utf-8", "replace"), err


def payload(cmd, tool="Bash"):
    return json.dumps({"tool_name": tool, "tool_input": {"command": cmd},
                       "session_id": "rag-test"})


def check(name, cmd, expect_advice, tool="Bash", raw=None):
    for via in ("script", "dispatcher"):
        rc, out, err = run(raw if raw is not None else payload(cmd, tool), via)
        if rc != 0:
            FAILS.append("%s [%s]: guard must NEVER block, rc=%s" % (name, via, rc))
            continue
        advised = False
        if out.strip():
            try:
                obj = json.loads(out)
            except ValueError:
                FAILS.append("%s [%s]: stdout is not JSON: %r" % (name, via, out[:200]))
                continue
            hso = obj.get("hookSpecificOutput") or {}
            extra = set(obj) - {"hookSpecificOutput"}
            extra |= set(hso) - {"hookEventName", "additionalContext"}
            if extra:
                FAILS.append("%s [%s]: advisory may only emit additionalContext, got %s"
                             % (name, via, sorted(extra)))
                continue
            ctx = hso.get("additionalContext") or ""
            advised = "Edit" in ctx and "rewrite-advisory-guard" in ctx
            if not advised:
                FAILS.append("%s [%s]: advice must name the tool and the Edit fix: %r"
                             % (name, via, ctx[:200]))
                continue
        if advised != expect_advice:
            FAILS.append("%s [%s]: expected %s, out=%r" % (
                name, via, "ADVICE" if expect_advice else "SILENCE", out[:200]))
        else:
            PASSES[0] += 1


def test_sed():
    check("sed -i", "sed -i 's/a/b/' f.txt", True)
    check("sed -i with suffix", "sed -i.bak 's/a/b/' f.txt", True)
    check("sed --in-place", "sed --in-place 's/a/b/' f.txt", True)
    check("sed --in-place=SUF", "sed --in-place=.bak 's/a/b/' f.txt", True)
    check("sed -ni cluster", "sed -ni 's/a/b/p' f.txt", True)
    check("sed -Ei cluster", "sed -Ei 's/a+/b/' f.txt", True)
    check("sed after cd", "cd /tmp && sed -i 's/a/b/' f.txt", True)
    check("sed with env assignment", "LC_ALL=C sed -i 's/a/b/' f.txt", True)
    check("sed behind time", "time sed -i 's/a/b/' f.txt", True)
    check("sed full path exe", "C:/Git/usr/bin/sed.exe -i 's/a/b/' f.txt", True)
    check("xargs sed -i", "ls *.txt | xargs sed -i 's/a/b/'", True)
    check("find -exec sed -i", "find . -name '*.py' -exec sed -i 's/a/b/' {} +", True)
    check("sed in subshell", "(sed -i 's/a/b/' f.txt)", True)
    check("perl -pi", "perl -pi -e 's/a/b/' f.txt", True)
    check("perl -i.bak", "perl -i.bak -pe 's/a/b/' f.txt", True)


def test_python():
    check("python -c open w", "python -c \"open('f','w').write('x')\"", True)
    check("python3 -c write_text",
          "python3 -c 'from pathlib import Path; Path(\"f\").write_text(\"x\")'", True)
    check("py -c write_bytes", "py -c \"import pathlib; pathlib.Path('f').write_bytes(b'x')\"", True)
    check("python -c open a", "python -c \"open('f', 'a').write('x')\"", True)
    check("python -c os.replace", "python -c \"import os; os.replace('a','b')\"", True)
    check("python exe path", "C:/Python313/python.exe -c \"open('f','w').write('x')\"", True)
    check("python -c handle write",
          "python -c \"f=open('f','w'); f.write('x'); f.close()\"", True)


def test_silent():
    check("sed read only", "sed 's/a/b/' f.txt", False)
    check("sed -n print", "sed -n 1,5p f.txt", False)
    check("sed -e script text with -i", "sed -e 's/-i/x/' f.txt", False)
    check("sed -s no in-place", "sed -s -n '$p' a.txt b.txt", False)
    check("sed in a pipe reading", "cat f | sed 's/a/b/' | head -3", False)
    check("commit message naming sed -i", "git commit -m 'avoid sed -i here'", False)
    check("echo naming sed -i", "echo \"sed -i is bad\"", False)
    check("grep -i", "grep -i foo f.txt", False)
    check("python -c print", "python -c \"print(1)\"", False)
    check("python -c read json", "python -c \"import json;print(json.load(open('f')))\"", False)
    check("python -c open r", "python -c \"print(open('f','r').read())\"", False)
    check("python -c stdout write", "python -c \"import sys; sys.stdout.write('x')\"", False)
    check("python script", "python tool.py --write", False)
    check("perl no -i", "perl -ne 'print if /a/' f.txt", False)
    check("non-Bash tool", "sed -i 's/a/b/' f.txt", False, tool="Edit")
    check("empty command", "", False)
    check("unbalanced quotes fail open", "sed -i 's/a/b f.txt", False)
    check("garbage stdin fails open", "", False, raw="not json at all")
    check("missing tool_input", "", False, raw=json.dumps({"tool_name": "Bash"}))


def test_review_round1():
    """Regressions from adversarial review round 1 (2026-10-28)."""
    import time
    # D2/D6 -- option arguments / module switches are not in-place flags
    for c in ("perl -Mstrict -e 'print 1'", "perl -Mwarnings -ne 'print' f",
              "perl -Mlib=lib t.pl", "perl -MList::Util=sum -le 'print 1'",
              "perl -Ilib script.pl", "perl script.pl -input x",
              "sed -finsert.sed f.txt", "sed -e'i hello' f.txt"):
        check("no false positive: " + c, c, False)
    # perl/sed in-place still fires with digits, bundles, ordering
    for c in ("perl -0pi -e 's/a/b/' f", "perl -0777 -pi -e 's/a/b/' f",
              "perl -wpi -e 's/a/b/' f", "sed -n -i 's/a/b/p' f",
              "sed --in 's/a/b/' f"):
        check("still fires: " + c, c, True)
    # D3 -- heredoc bodies are text, not commands
    check("heredoc commit body", "git commit -F - <<'EOF'\nfix: x\n\nsed -i usage replaced by Edit\nEOF", False)
    check("heredoc file body", "cat > fix.md <<'EOF'\nsed -i is discouraged here\nEOF", False)
    check("command after heredoc still seen",
          "cat > f <<'EOF'\ntext\nEOF\nsed -i 's/a/b/' f", True)
    check("arithmetic shift is not a heredoc", "echo $((1<<5)); sed -i 's/a/b/' f", True)
    # D4 -- compound-command heads
    for c in ("if true; then sed -i s/a/b/ f; fi",
              "for f in *; do sed -i s/a/b/ $f; done",
              "while read l; do sed -i s/a/b/ f; done",
              "{ sed -i s/a/b/ f; }", "! sed -i s/a/b/ f",
              "bash -c \"sed -i 's/a/b/' f\"",
              "time -p sed -i s/a/b/ f"):
        check("compound fires: " + c, c, True)
    # D7 -- python: handles, non-file .write, launchers
    check("StringIO write is not a file", "python -c \"import io; b=io.StringIO(); b.write('x')\"", False)
    check("stdout alias write", "python -c \"import sys; o=sys.stdout; o.write('x')\"", False)
    check("open(a) read", "python -c \"print(open('a').read())\"", False)
    check("nested parens write", "python -c \"import os,json; json.dump({}, open(os.path.join('d','f'),'w'))\"", True)
    check("rb+ mode", "python -c \"open('f','rb+').write(b'x')\"", True)
    check("python3.12 launcher", "python3.12 -c \"open('f','w').write('x')\"", True)
    check("-Bc cluster", "python -Bc \"open('f','w').write('x')\"", True)
    check("uv run python", "uv run python -c \"open('f','w').write('x')\"", True)
    # D8 -- xargs hop looks at the command word only
    check("xargs grep pattern", "git ls-files | xargs grep -l sed -i", False)
    check("xargs -I sed", "ls | xargs -I{} sed -i 's/a/b/' {}", True)
    # D1 -- no quadratic scan; bounded wall time on a 126KB hostile body
    big = "python -c \"" + "open('" * 21000 + "\""  # closed quote: tokeniser must accept it
    t0 = time.time()
    rc, out, err = run(payload(big), "script")
    el = time.time() - t0
    if rc == 0 and el < 4.0:
        PASSES[0] += 1
    else:
        FAILS.append("126KB open( payload took %.1fs rc=%s (budget 4s)" % (el, rc))
    big2 = "open(" * 26000
    t0 = time.time()
    rc, out, err = run(payload("python -c \"" + big2 + "\""), "script")
    el = time.time() - t0
    if rc == 0 and el < 4.0:
        PASSES[0] += 1
    else:
        FAILS.append("open( x26000 took %.1fs rc=%s (budget 4s)" % (el, rc))


def _timed(name, cmd, budget=4.0):
    import time
    t0 = time.time()
    try:
        rc, out, err = run(payload(cmd), "script")
    except subprocess.TimeoutExpired:
        FAILS.append("%s: guard run exceeded the 60s harness timeout" % name)
        return
    el = time.time() - t0
    if rc == 0 and el < budget:
        PASSES[0] += 1
    else:
        FAILS.append("%s took %.1fs rc=%s (budget %.0fs)" % (name, el, rc, budget))


def test_review_round2():
    """Regressions from adversarial review round 2 (2026-10-28)."""
    # D1 -- global work budget: nested / flat find -exec chains must not stall
    _timed("nested find -exec x220", "find . " + "-exec find " * 220)
    _timed("flat find -exec 880KB", "find . " + "-exec echo " * 80000, budget=8.0)
    _timed("nested bash -c", "bash -c \"" * 40 + "sed -i s/a/b/ f")
    _timed("xargs chain", "xargs " * 50000, budget=8.0)
    # round 3: the python -c scan and heredoc stripping are inside the budget too.
    # BALANCED quotes (an unbalanced quote is rejected by the tokeniser and tests nothing)
    stage = 'python -c "' + "open(" * 1638 + '"'
    _timed("60 python -c stages (492KB)", ";".join([stage] * 60), budget=3.0)
    _timed("120 python -c stages (985KB)", ";".join([stage] * 120), budget=3.0)
    _timed("bash -c around 70 python stages", "bash -c '" + ";".join(
        ['python -c "' + "open(" * 1638 + '"'] * 70) + "'", budget=3.0)
    _timed("200k heredoc operators", "cat " + "<<A" * 200000 + "\n" + "A\n" * 200000,
           budget=3.0)
    # D2 -- open( arguments are parsed, not windowed
    for c in ("python -c \"print(open('f').read().replace('foo', 'bar'))\"",
              "python -c \"import json; d=json.load(open('f')); print(d.get('name', 'x'))\"",
              "python -c \"print(open('a').read(), 'a')\"",
              "python -c \"x = open('log.txt').readlines(); print(len(x), 'w')\"",
              "python script.py -c \"open('f','w')\""):
        check("read-only python stays silent: " + c[:50], c, False)
    check("Path.open w", "python -c \"from pathlib import Path; Path('f').open('w').write('x')\"", True)
    check("open with mode kwarg", "python -c \"open('f', mode='w').write('x')\"", True)
    check("open with encoding then mode",
          "python -c \"open('f', 'w', encoding='utf-8').write('x')\"", True)
    check("bash -lc", "bash -lc \"sed -i 's/a/b/' f\"", True)
    check("bash script -c arg is not a command", "bash script.sh -c \"sed -i s/a/b/ f\"", False)


def test_chain():
    sys.path.insert(0, HOOKS)
    import importlib.util as u
    s = u.spec_from_file_location("disp", DISPATCHER)
    m = u.module_from_spec(s)
    s.loader.exec_module(m)
    chain = m.BASH_GUARD_CHAIN
    ok = ("rewrite-advisory-guard" in chain and chain[-1] == "pipe-mask-guard"
          and chain.index("rewrite-advisory-guard") > chain.index("winpath-guard"))
    if ok:
        PASSES[0] += 1
    else:
        FAILS.append("rewrite-advisory-guard must sit after winpath-guard and before the "
                     "LAST pipe-mask-guard: %r" % (chain,))
    if "rewrite-advisory-guard" in m.GUARD_CHAIN:
        FAILS.append("rewrite-advisory-guard must be Bash-chain only")
    else:
        PASSES[0] += 1


def test_coexists_with_pipe_mask():
    """A rewrite-advisory emission and a pipe-mask rewrite must merge into one
    valid object carrying BOTH additionalContext and updatedInput."""
    import contextlib
    import importlib.util as u
    import io
    s = u.spec_from_file_location("disp2", DISPATCHER)
    m = u.module_from_spec(s)
    s.loader.exec_module(m)
    rc, out, err = run(payload("sed -i 's/a/b/' f.txt"), "script")
    advisory = out
    rewrite = json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "updatedInput": {"command": "set -o pipefail; git push | tail -3"}}})
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        m.emit_stdout([advisory, rewrite])
    try:
        hso = json.loads(buf.getvalue()).get("hookSpecificOutput") or {}
    except ValueError:
        FAILS.append("merged output is not one JSON object: %r" % buf.getvalue()[:300])
        return
    if "additionalContext" in hso and "updatedInput" in hso:
        PASSES[0] += 1
    else:
        FAILS.append("merge dropped the advisory or the rewrite: %r" % buf.getvalue()[:300])


def main():
    test_sed()
    test_python()
    test_silent()
    test_review_round1()
    test_review_round2()
    test_chain()
    test_coexists_with_pipe_mask()
    print("test-rewrite-advisory-guard: %d pass, %d fail" % (PASSES[0], len(FAILS)))
    for f in FAILS:
        print("FAIL: " + f)
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
