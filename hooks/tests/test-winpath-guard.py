"""Standalone test for hooks/winpath-guard.py.

WHAT IT ENFORCES (2026-10-23, /insights friction F1b): in the Bash tool an
UNQUOTED backslash is an escape character, so `C:\\Users\\x` reaches the program
as `C:Usersx`; inside double quotes `\\$` is bash's own escape, so
"C:\\a\\$SID" keeps a literal `$SID`. Both corrupt the path silently. The guard
BLOCKS exactly those two shapes and nothing else (memory:
feedback_bash_unquoted_windows_paths_collapse, feedback_bash_backslash_dollar_
escape_windows_path).

Every check drives BOTH the script and the dispatcher's in-process path.
Run: python hooks/tests/test-winpath-guard.py
"""
import json
import os
import subprocess
import sys
import time

HOOKS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GUARD = os.path.join(HOOKS, "winpath-guard.py")
DISPATCHER = os.path.join(HOOKS, "pretooluse-dispatcher.py")
PY = sys.executable
FAILS = []
PASSES = [0]
BS = "\\"
NL = chr(10)


def run(raw, via):
    if via == "script":
        argv = [PY, GUARD]
    else:
        argv = [PY, "-c", (
            "import sys, importlib.util as u; s=u.spec_from_file_location('d', %r); "
            "m=u.module_from_spec(s); s.loader.exec_module(m); "
            "rc,o,e,mode=m.run_guard('winpath-guard', sys.stdin.buffer.read()); "
            "sys.stderr.write(e+'|mode='+mode); sys.exit(rc)") % DISPATCHER]
    r = subprocess.run(argv, input=raw.encode("utf-8"), capture_output=True, timeout=60)
    err = r.stderr.decode("utf-8", "replace")
    if via == "dispatcher" and "|mode=inprocess" not in err:
        FAILS.append("dispatcher did not run winpath-guard in-process: " + err[-200:])
    return r.returncode, err


def payload(cmd, tool="Bash"):
    return json.dumps({"tool_name": tool, "tool_input": {"command": cmd},
                       "session_id": "wpg-test"})


def check(name, cmd, expect_block, tool="Bash", raw=None):
    for via in ("script", "dispatcher"):
        rc, err = run(raw if raw is not None else payload(cmd, tool), via)
        blocked = rc == 2 and "winpath-guard" in err
        if blocked != expect_block:
            FAILS.append("%s [%s]: expected %s, rc=%s err=%s" % (
                name, via, "BLOCK" if expect_block else "ALLOW", rc, err[-300:]))
        else:
            PASSES[0] += 1
        if blocked and "forward slashes" not in err:
            FAILS.append("%s [%s]: block message must name the fix" % (name, via))


def p(*parts):
    """Join with single backslashes -- keeps the fixtures readable."""
    return BS.join(parts)


def test_blocks():
    check("unquoted script path", "python " + p("C:", "Users", "Owner", "x.py"), True)
    check("unquoted interpreter word",
          p("C:", "Windows", "System32", "WindowsPowerShell", "v1.0", "powershell.exe")
          + ' -File "' + p("C:", "a.ps1") + '"', True)
    check("unquoted ls arg", "ls " + p("C:", "Users"), True)
    check("dq backslash-dollar", 'DIR="' + p("C:", "Users", "Owner", ".claude", "hooks",
                                               "sessions", "$SID", "overrides") + '"', True)
    check("dq backslash-dollar 2", 'cat "' + p("D:", "data", "$f") + '"', True)
    check("unquoted cd", "cd " + p("C:", "x") + " && ls", True)
    check("unquoted assignment", "x=" + p("C:", "foo"), True)
    check("second statement", "ls; python " + p("C:", "y", "z.py"), True)
    check("dq backslash-backtick", 'echo "' + p("C:", "a") + BS + '`date`"', True)


def test_allows():
    check("dq path", 'python "' + p("C:", "Users", "Owner", "x.py") + '"', False)
    check("sq path", "python '" + p("C:", "Users", "Owner", "x.py") + "'", False)
    check("forward slashes", "python C:/Users/Owner/x.py", False)
    check("doubled backslashes", "echo C:" + BS * 2 + "Users" + BS * 2 + "Owner", False)
    check("dq regex", 'grep -E "C:' + BS * 4 + 'Users" f', False)
    check("heredoc body",
          "python - <<'EOF'\nprint(r\"" + p("C:", "Users", "$x") + "\")\nEOF", False)
    check("heredoc body unquoted delim",
          "cat <<EOF > f.txt\nrun " + p("C:", "x", "y.py") + "\nEOF\necho done", False)
    check("comment", "ls # see " + p("C:", "x"), False)
    check("dq dollar without drive", 'echo "price is ' + BS + '$5"', False)
    check("commit message mentions path",
          'git commit -m "fix ' + p("C:", "path") + ' handling"', False)
    check("powershell sq inside dq",
          "powershell -Command \"Get-Item '" + p("C:", "x") + "'\"", False)
    check("ansi-c quoting", "printf $'" + p("C:", "x") + "'", False)
    check("PowerShell tool is out of scope", "ls " + p("C:", "Users"), False,
          tool="PowerShell")
    check("malformed payload fails open", "", False, raw="{not json")
    check("url is not a drive", "curl https://example.com/a" + BS + "b", False)
    check("escaped space after doubled", "ls C:" + BS * 2 + "Program" + BS + " Files",
          False)


def test_f_b_false_positives():
    """Review F-B: correct commands that must NOT be blocked."""
    check("powershell escaped-dollar is the correct way to pass $_",
          'powershell -NoProfile -Command "Get-ChildItem ' + p("C:", "Users", "Owner", "x")
          + ' | ForEach-Object { ' + BS + '$_.Name }"', False)
    check("commit message with escaped backticks around a path",
          'git commit -m "fix: handle ' + BS + '`' + p("C:", "Users", "x") + BS
          + '` paths"', False)
    check("standard commit heredoc inside $(...) with quoted path in body",
          "git commit -m \"$(cat <<'EOF'\nfix thing\n\nbody says \"path "
          + p("C:", "Users", "x") + "\" here\nEOF\n)\"", False)
    check("heredoc delimiter backslash-EOF",
          "cat <<" + BS + "EOF > f\nrun " + p("C:", "x", "y.py") + "\nEOF\necho ok", False)
    check("heredoc delimiter with hyphen",
          "powershell -Command - <<'END-PS'\nGet-Item " + p("C:", "x") + "\nEND-PS\n",
          False)
    check("heredoc <<- tab-stripped hyphen delimiter",
          "cat <<-'E-1'\n\trun " + p("C:", "x") + "\n\tE-1\n", False)
    # still blocked after the heredoc, i.e. the scanner resumed correctly
    check("block after $(...) heredoc",
          "git commit -m \"$(cat <<'EOF'\nx\nEOF\n)\" && ls " + p("C:", "bad"), True)
    check("block inside $( ) in dq", 'echo "$(ls ' + p("C:", "bad") + ')"', True)
    check("one-word dq backslash-dollar still blocked",
          'echo "' + p("C:", "a", "$SID", "b") + '"', True)
    check("backslash-backtick not closing a pair still blocked",
          'echo "' + p("C:", "a") + BS + '`date`"', True)


def test_real_powershell_oneliners():
    """Review round 2, finding 1: 6 of 6 real-transcript backslash-dollar hits were
    CORRECT PowerShell -Command one-liners (bash passes the dollar through). Only one that
    directly follows a path-name character eats a separator and is corruption."""
    b = BS
    ps = "powershell -NoProfile -Command "
    pc = "'" + p("C:", "Users", "Owner", "ora-pm-cron", "ping-crons.ps1") + "'"
    check("real: ParseFile syntax check",
          ps + '"' + b + "$e=" + b + "$null; [void][System.Management.Automation.Language"
          ".Parser]::ParseFile(" + pc + ",[ref]" + b + "$null,[ref]" + b + "$e); "
          + b + '$e.Count"', False)
    check("real: ParseFile heartbeat after git chain",
          "cd ~/.claude && git worktree remove .claude/worktrees/oi-353-fix; "
          "git push -q origin --delete fix/x 2>&1 | tail -1; " + ps + '"' + b + "$e="
          + b + "$null; [void][System.Management.Automation.Language.Parser]::ParseFile('"
          + p("C:", "Users", "Owner", ".claude", "maintenance", "push-fleet-heartbeat.ps1")
          + "',[ref]" + b + "$null,[ref]" + b + '$e)"', False)
    check("real: ParseFile send-via-outlook",
          ps + '"' + b + "$e=" + b + "$null; [void][System.Management.Automation.Language"
          ".Parser]::ParseFile('" + p("C:", "Users", "Owner", ".claude", ".claude",
          "worktrees", "slim-landing", "scheduled-tasks", "_shared", "send-via-outlook.ps1")
          + "',[ref]" + b + "$null,[ref]" + b + '$e)"', False)
    check("real: foreach with path concat plus",
          ps + '"foreach(' + b + "$d in 'devmain','sweep'){ " + b + "$j='"
          + p("C:", "Users", "Owner", "rwt", "") + "'+" + b + "$d+'" + b + "node_modules'; "
          "if(Test-Path " + b + '$j){ 1 } }"', False)
    check("real: escaped-quote path then triple-backslash dollar",
          ps + '"foreach(' + b + "$w in 'a','b'){ " + b + "$p=" + b + '"'
          + p("C:", "Users", "Owner", "ora-pm-worktrees") + b * 3 + "$w" + b + '"; 1 }"',
          False)
    check("real: doubled backslashes then triple-backslash dollar",
          ps + '"foreach (' + b + "$w in 'x','y') { " + b + "$p = " + b + '"'
          + (b * 2).join(["C:", "Users", "Owner", "ora-worktrees"]) + b * 3 + "$w"
          + b * 2 + "node_modules" + b + '"; 1 }"', False)
    # synthetic: bash renders each of these correctly
    check("backslash-backslash-backslash-dollar is literal backslash + dollar",
          'ls "C:' + b * 3 + '$Recycle.Bin"', False)
    check("semicolon then escaped dollar",
          'powershell -Command "Test-Path ' + "'" + p("C:", "x", "y") + "';" + b + '$?"', False)
    check("pipe then escaped dollar",
          'powershell -Command "gci ' + p("C:", "Temp") + b + "|%{" + b + '$_.Name}"', False)


def test_backslash_dollar_still_blocked():
    """The corruption cases the narrowed rule must keep catching."""
    b = BS
    check("name char then backslash-dollar (SID)",
          'echo "' + p("C:", "a", "$SID", "b") + '"', True)
    check("echo path USER", 'echo "' + p("C:", "Users", "$USER") + '"', True)
    check("path then env:TEMP", 'echo "echo ' + p("C:", "x", "y", "$env:TEMP") + '"', True)
    check("digit before backslash-dollar", 'cat "' + p("D:", "d1", "$f") + '"', True)
    check("dot before backslash-dollar", 'cat "' + p("D:", "d.", "$f") + '"', True)
    check("dash before backslash-dollar", 'cat "' + p("D:", "d-", "$f") + '"', True)
    check("underscore before backslash-dollar", 'cat "' + p("D:", "d_", "$f") + '"', True)
    check("tilde before backslash-dollar", 'cat "' + p("D:", "PROGRA~1", "$f") + '"', True)
    check("known accepted false positive: dollar-digit filename",
          'cat "' + p("C:", "x", "file", "$1.txt") + '"', True)


def test_arith_not_heredoc():
    """Review round 2, finding 2: `$((1 << 5))` must not be read as a heredoc
    operator (kills the mutant that drops the digit-delimiter exception)."""
    check("arith shift then corrupting path next line",
          "echo $((1 << 5))" + NL + "python " + p("C:", "a", "b.py"), True)
    check("arith shift same line chain",
          "x=$((2 << 3)); python " + p("C:", "a", "b.py"), True)


def test_mutation_survivors():
    """Mutation review round 3: pins the double-quote backslash-dollar rule's per-word
    drive flag (reset at whitespace), the alphanumeric guard on the drive letter, the
    `~` path-name char, heredoc recognition (backslash delimiter, <<- tab strip) and
    double-quote backslash-pair handling. Each ALLOW is a command bash renders
    correctly; each BLOCK is real corruption."""
    b = BS
    # M6: drive path seen earlier in the same dq string but in another word.
    check("M6: drive path, whitespace, then escaped PowerShell dollar",
          'powershell -Command "gci ' + p("C:", "x") + ' | % { ' + b + "$s=(Get-Date)-"
          + b + '$_.LastWriteTime }"', False)
    check("M6: drive path, three words, then escaped dollar",
          'powershell -Command "gci ' + p("C:", "x") + " one two three-" + b
          + '$name"', False)
    # M11: `x:` right after a letter/digit is not a drive letter.
    check("M11: regex id-colon then escaped dollar in the same word",
          'grep -E "id:' + b + "s*foo" + b + '$" f', False)
    check("M11: letter-pair colon is not a drive",
          'echo "ab:' + b + "x" + b + '$y"', False)
    check("M11: digit-letter colon is not a drive",
          'echo "1a:' + b + "x" + b + '$y"', False)
    # `~` is a path-name char (8.3 short names): corruption.
    check("tilde directly before backslash-dollar",
          'echo "' + p("C:", "x~", "$f") + '"', True)
    # heredoc recognition: a corrupting path AFTER the body must still be seen.
    check("block after backslash-delimiter heredoc",
          "cat <<" + b + "EOF > f\nrun " + p("C:", "x", "y.py") + "\nEOF\npython "
          + p("C:", "bad", "z.py"), True)
    check("block after <<- heredoc with tab-indented terminator",
          "cat <<-EOF > f\n\trun " + p("C:", "x", "y.py") + "\n\tEOF\npython "
          + p("C:", "bad", "z.py"), True)
    # double-quote backslash pairs: literal backslash, then (a) literal dollar or
    # (b) an ordinary expansion; neither corrupts the path.
    check("dq backslash pair then escaped dollar",
          'echo "C:' + b + "x" + b * 3 + '$w"', False)
    check("dq backslash pair then plain dollar",
          'echo "C:' + b + "x" + b * 2 + '$w"', False)
    # an escaped quote does not close the string: the path stays inside the dq frame
    # (a scanner that ends the string at the escaped quote would see it unquoted).
    check("dq escaped quotes keep the string open",
          'echo "a ' + b + '" ' + p("C:", "x") + " " + b + '" ' + b + '$f"', False)


def _timed(name, cmd):
    t0 = time.time()
    rc, _err = run(payload(cmd), "script")
    dt = time.time() - t0
    if rc != 0 or dt >= 2.0:
        FAILS.append("%s: rc=%s dt=%.1fs (want rc 0 in <2s)" % (name, rc, dt))
    else:
        PASSES[0] += 1


def test_f_c_perf():
    """Review F-C: no quadratic behavior; PreToolUse Bash has no timeout."""
    _timed("50k escaped-dollar in one dq string", 'echo "' + (BS + "$") * 50000 + '"')
    _timed("50k escaped-dollar, drive path in another word",
           'echo "' + (BS + "$") * 50000 + " " + p("C:", "x") + '"')
    realistic = ("git commit -m \"$(cat <<'EOF'\n"
                 + ("line of prose with a path " + p("C:", "Users", "x")
                    + " and more text\n") * 400 + "EOF\n)\"")
    if len(realistic) < 20000:
        FAILS.append("realistic fixture too short: %d" % len(realistic))
    _timed("20k realistic commit command", realistic)
    _timed("20k dq words", 'echo "' + "word " * 5000 + '"')


def main():
    for t in (test_blocks, test_allows, test_f_b_false_positives,
              test_real_powershell_oneliners, test_backslash_dollar_still_blocked,
              test_arith_not_heredoc, test_mutation_survivors, test_f_c_perf):
        try:
            t()
        except Exception as e:  # noqa: BLE001
            FAILS.append("%s raised %s: %s" % (t.__name__, type(e).__name__, e))
    for f in FAILS:
        print("FAIL " + f)
    print("test-winpath-guard: %d pass, %d fail" % (PASSES[0], len(FAILS)))
    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    main()
