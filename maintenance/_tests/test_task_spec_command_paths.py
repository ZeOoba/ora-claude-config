#!/usr/bin/env python3
"""Conformance + unit tests: scheduled-task spec commands use forward-slash paths.

WHY
---
In the Bash tool an UNQUOTED backslash is an escape character, so a spec line such as

    python C:\\Users\\Owner\\.claude\\scheduled-tasks\\_shared\\block-sentinel.py claim ...

reaches python as `C:UsersOwner.claude...` and fails. The agent running the task
silently hand-corrects it, which hides the defect. The fix is UNQUOTED FORWARD slashes:

    python C:/Users/Owner/.claude/scheduled-tasks/_shared/block-sentinel.py claim ...

DO NOT quote the script path. test_scheduled_task_run_guard.py discovers block-sentinel
lines with `block-sentinel(?:\\.py)?\\s+claim\\b`; a quoted path ("...block-sentinel.py" claim)
stops matching and silently drops the spec out of the guarded set. Test (e) below pins this.

WHAT IS A VIOLATION (one scanner, `violations()`, shared by the rewrite and this test)
--------------------------------------------------------------------------------------
Rule A (separators): a drive-path WORD (`X:\\` + path chars, any case of X) that is UNQUOTED
(outside '..', "..", $'..'), carries a SINGLE backslash separator (`\\\\` doubled and `\\ `
escaped-space are valid bash and are not separators; one trailing backslash at end of line is a
line continuation, not a separator), inside a COMMAND CONTEXT. Fix: unquoted forward slashes.
Rule B (spaces): an UNQUOTED drive word of either slash style directly followed by ' - <word>'
(e.g. `C:/Users/Owner/OneDrive - Oxford ...`) is a path containing spaces that Bash splits. It is
listed but NEVER auto-rewritten (a human quotes it; `quote_spaced_path_to_eol` is the explicit,
separately tested helper the one-off rewrite uses for the two known lines). That helper quotes
EVERYTHING from the anchor to the end of the line as ONE argument, so it must only be used on a line
whose spaced path is the LAST argument. Inside a command fence the Rule B exemption is decided solely
by the line's FIRST word: a line whose first word is a bare data path (a drive path that is not an
executable) is documentation of a path, so its spaces are not flagged; any other fence line is a
command and its spaced arguments are flagged.

COMMAND CONTEXT is exactly:
  1. any line inside a fenced block whose info string is empty/bash/sh/shell/console/zsh
     (inside such a fence a line that is only a bare data path is not checked for Rule B);
  2. a non-fence line whose first word (after indent, any list markers, optional env
     assignments), compared case-insensitively, is python/python3/py/node/powershell/
     powershell.exe/pwsh/cd/git/bash/sh/npx/npm, or set/export/setenv/env followed by NAME=,
     or is itself a drive path to an executable (.exe/.cmd/.bat/.com), or a drive-path .ps1
     followed by a -Flag or another drive path; or an interpreter or a drive-path executable
     (.exe/.cmd/.bat/.com, and .ps1 under the same follow rule) invoked mid-sentence and followed
     directly by a drive path or a -flag ("... email sent: python C:/x.py ...",
     "via C:/.../python.exe C:\\x.py", "Send the report via C:\\x\\send.ps1 -To ...");
  3. an inline `backtick span` that starts with a command word (as in 2) or with a drive-path
     executable that has at least one argument (a .ps1 counts only with a -Flag / drive-path argument).
A drive-path .ps1 that stands alone ("see C:\\x\\send.ps1", "the script C:\\x\\x.ps1 handles X") is a
mention, not a command, and is not flagged.
INTENTIONALLY EXCLUDED (not violations, by design): quoted paths; doubled backslashes; heredoc
bodies and `#` comments; PowerShell/js/json/python/etc. fences; prose that merely names a path
(a bare data path alone on a line or in a span, incl. `OneDrive - Oxford ...` state-file paths);
a span that is only an executable path with no arguments; `<tmp>\\...` placeholders and
`%VAR%\\...` cmd-isms (not drive paths); and mixed-style words that START with a forward-slash
drive (`C:/x\\y`), which the scanner does not look into.
KNOWN LIMITATION: command words match case-insensitively, so capitalised prose that happens to
start a line or follow a marker with such a word AND a drive path (e.g. "Git C:\\x\\y was cloned",
"Node C:\\x\\y is the path") is flagged as a command. The remedy is to reword or use forward slashes.

Standalone script: prints PASS/FAIL lines and a final `task-spec-command-paths: N pass, M fail`
summary; exit 1 on failure. No network, no writes to the repo.
"""

import contextlib
import glob
import importlib.util
import io
import os
import random
import re
import shlex
import shutil
import sys
import tempfile
import time

for _s in (sys.stdout, sys.stderr):  # UTF-8 safe output on Windows cp1252 pipes
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SCHED = os.path.join(ROOT, "scheduled-tasks")

# Genuine exceptions: {spec_id: [(line_number_or_substring, reason)]}. Keep EMPTY unless
# an entry is justified; a listed entry suppresses matching violations in the conformance test.
ALLOWLIST = {}

# --------------------------------------------------------------------------
# Scanner
# --------------------------------------------------------------------------

BASH_INFOS = {"", "bash", "sh", "shell", "console", "zsh"}
CMD_WORDS = {"python", "python3", "py", "node", "powershell", "powershell.exe", "pwsh",
             "cd", "git", "bash", "sh", "npx", "npm"}

_FENCE = re.compile(r"^\s*(`{3,}|~{3,})(.*)$")
# Env-assignment commands: a command only when followed by NAME= ("Set up the file" is prose).
ENV_CMDS = {"set", "export", "setenv", "env"}
_ENV_CMD_TAIL = re.compile(r"\s+[A-Za-z_][A-Za-z0-9_]*=")
_LIST_MARKER = re.compile(r"^\s*(?:(?:[-*+]|\d+[.)])\s+)*")
_ENV_ASSIGN = re.compile(r"(?:[A-Za-z_][A-Za-z0-9_]*=\S*\s+)*")
_FIRST_WORD = re.compile(r"\S+")
_DRIVE_EXE = re.compile(r"^[A-Za-z]:[\\/].*\.(?:exe|cmd|bat|com)$", re.I)
# A drive-path .ps1 is an executable ONLY when an argument follows (a -Flag or another drive path);
# a .ps1 path on its own is a mention ("see C:\x\send.ps1", "the script C:\x\x.ps1 handles X").
_DRIVE_PS1 = re.compile(r"^[A-Za-z]:[\\/].*\.ps1$", re.I)
_EXE_ARG = re.compile(r"\s+(?:-\S|[A-Za-z]:[\\/])")
_SPAN = re.compile(r"(?<!`)`([^`\n]+)`(?!`)")
# An interpreter word (case-insensitive) or a drive-path executable, mid-sentence, followed
# directly by a drive path or a -flag.
_MID_INTERP = re.compile(
    r"(?<![^\s(])(?:python3?|py|node|powershell(?:\.exe)?|pwsh"
    r"|[A-Za-z]:[\\/]\S*\.(?:exe|cmd|bat|com|ps1))(?=\s+(?:-\S|[A-Za-z]:[\\/]))", re.I)
_HEREDOC = re.compile(r"(?<!<)<<(?!<)(-?)\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\2")
_TERM = frozenset(" \t\r\n\f\v'\"`;|&<>()")


def _live_mask(s):
    """Per-char bool: True if the char is unquoted (bash rules) and before any comment.

    Quote delimiters themselves are not live. An unquoted backslash and the char it
    escapes are live (that backslash is exactly what we are looking for)."""
    n = len(s)
    live = [False] * n
    i = 0
    state = None
    while i < n:
        c = s[i]
        if state is None:
            if c == "\\":
                live[i] = True
                if i + 1 < n:
                    live[i + 1] = True
                i += 2
                continue
            if c == "'":
                state = "'"
            elif c == '"':
                state = '"'
            elif c == "$" and i + 1 < n and s[i + 1] == "'":
                state = "$"
                i += 1
            elif c == "#" and (i == 0 or s[i - 1].isspace()):
                break
            else:
                live[i] = True
            i += 1
        elif state == "'":
            if c == "'":
                state = None
            i += 1
        else:  # '"' or "$" (ANSI-C): backslash escapes the next char
            if c == "\\":
                i += 2
                continue
            if (state == '"' and c == '"') or (state == "$" and c == "'"):
                state = None
            i += 1
    return live


def _drive_words(s, live):
    """[(start, end, [sep_indexes])] for unquoted drive-path words with single-backslash seps."""
    out = []
    n = len(s)
    i = 0
    while i < n - 2:
        c = s[i]
        if (c.isascii() and c.isalpha() and s[i + 1] == ":" and s[i + 2] == "\\"
                and live[i] and live[i + 1] and live[i + 2]
                and (i == 0 or not (s[i - 1].isalnum() or s[i - 1] == "_"))):
            j = i + 2
            seps = []
            while j < n and live[j]:
                ch = s[j]
                if ch == "\\":
                    nx = s[j + 1] if j + 1 < n else ""
                    if nx == "":
                        j += 1
                        break
                    if nx in ("\\", " "):      # doubled backslash / escaped space
                        j += 2
                        continue
                    seps.append(j)
                    j += 1
                    continue
                if ch in _TERM:
                    break
                j += 1
            if seps:
                out.append((i, j, seps))
            i = max(j, i + 1)
        else:
            i += 1
    return out


def _cmd_start(s):
    """(offset_of_command_word, word) after list marker + env assignments, or (None, None)."""
    m = _LIST_MARKER.match(s)
    off = m.end()
    m2 = _ENV_ASSIGN.match(s, off)
    off = m2.end()
    w = _FIRST_WORD.match(s, off)
    if not w:
        return None, None
    return off, w.group(0)


def _spaced_words(s, live):
    """[(start, end)] for unquoted drive-path words (either slash style) directly followed by
    ' - <alnum>' (e.g. 'C:/Users/Owner/OneDrive - Oxford'): the path contains spaces, so Bash splits it."""
    out = []
    n = len(s)
    i = 0
    while i < n - 2:
        if (s[i].isascii() and s[i].isalpha() and s[i + 1] == ":" and s[i + 2] in "\\/"
                and live[i] and live[i + 1] and live[i + 2]
                and (i == 0 or not (s[i - 1].isalnum() or s[i - 1] == "_"))):
            j = i + 3
            while j < n and live[j] and s[j] not in _TERM:
                j += 1
            if s[j:j + 3] == " - " and j + 3 < n and s[j + 3].isalnum():
                out.append((i, j))
            i = max(j, i + 1)
        else:
            i += 1
    return out


def _analyze_cmd(text, base, spaced=True):
    """Hits for one command text: (start, end, [sep indexes]). A word whose path contains spaces
    (`spaced`) is reported with NO separators: it is listed but never auto-rewritten."""
    live = _live_mask(text)
    hits = {a: (a, b, seps) for a, b, seps in _drive_words(text, live)}
    if spaced:
        for a, b in _spaced_words(text, live):
            hits[a] = (a, b, [])
    return [(base + a, base + b, [base + k for k in seps]) for a, b, seps in
            (hits[k] for k in sorted(hits))], live


def _is_command(text):
    """True if `text` (after list marker + env assignments) starts a command: a command word
    (case-insensitive), a drive-path executable, or set/export/setenv/env followed by NAME=."""
    off, w = _cmd_start(text)
    if w is None:
        return False
    lw = w.lower()
    if lw in CMD_WORDS or _DRIVE_EXE.match(w):
        return True
    if _DRIVE_PS1.match(w) and _EXE_ARG.match(text, off + len(w)):
        return True
    return lw in ENV_CMDS and bool(_ENV_CMD_TAIL.match(text, off + len(w)))


def _is_bare_data_path(text):
    """First word is a drive path that is not an executable: a data path, not a command."""
    off, w = _cmd_start(text)
    return (w is not None and bool(re.match(r"[A-Za-z]:[\\/]", w)) and not _DRIVE_EXE.match(w)
            and not (_DRIVE_PS1.match(w) and _EXE_ARG.match(text, off + len(w))))


def _analyze_fence_line(line):
    # a bare data path inside a command fence still has its backslash separators flagged, but its
    # spaces are not (it is documentation of a path, not an argument that Bash would split)
    return _analyze_cmd(line, 0, spaced=not _is_bare_data_path(line))


def _analyze_prose(line):
    if _is_command(line):
        return _analyze_cmd(line, 0)[0]
    found = {}
    for m in _SPAN.finditer(line):
        content = m.group(1)
        # a span that is JUST an executable path is a path mention, not a command: it needs arguments
        if _is_command(content) and (_cmd_start(content)[1].lower() in CMD_WORDS
                                     or len(content.split()) > 1):
            for h in _analyze_cmd(content, m.start(1))[0]:
                found[h[0]] = h
    # (2b) an interpreter invoked mid-sentence ("... sent: python C:\x.py ...",
    # "via powershell -File C:\x.ps1"). Only when the interpreter word is immediately followed
    # by a drive path or a -flag, so prose that merely says "python" is not swept in. The tail
    # is lexed from the interpreter word onward: an apostrophe earlier in the sentence
    # ("the run's email") must not hide the command.
    for m in _MID_INTERP.finditer(line):
        for h in _analyze_cmd(line[m.start():], m.start())[0]:
            found.setdefault(h[0], h)
    return [found[k] for k in sorted(found)]


def _scan_lines(lines):
    """lines: list of str WITHOUT line endings. Returns [(idx, [(start, end, seps)])]."""
    out = []
    fence = None          # (char, length, is_command_fence)
    heredoc = None        # (delimiter, dash)
    for idx, line in enumerate(lines):
        fm = _FENCE.match(line)
        if fence is None:
            if fm and not (fm.group(1)[0] == "`" and "`" in fm.group(2)):
                info = fm.group(2).strip().split()
                info = info[0].lower() if info else ""
                fence = (fm.group(1)[0], len(fm.group(1)), info in BASH_INFOS)
                heredoc = None
                continue
            hits = _analyze_prose(line)
        else:
            if (fm and fm.group(1)[0] == fence[0] and len(fm.group(1)) >= fence[1]
                    and not fm.group(2).strip()):
                fence = None
                heredoc = None
                continue
            if not fence[2]:
                continue
            if heredoc is not None:
                body = line.lstrip("\t") if heredoc[1] else line
                if body == heredoc[0]:
                    heredoc = None
                continue
            hits, live = _analyze_fence_line(line)
            hm = _HEREDOC.search(line)
            while hm and not live[hm.start()]:
                hm = _HEREDOC.search(line, hm.end())
            if hm:
                heredoc = (hm.group(3), hm.group(1) == "-")
        if hits:
            out.append((idx, hits))
    return out


def _split_eol(raw):
    """(content, ending) for one line obtained by splitting on '\\n' with keepends."""
    if raw.endswith("\r\n"):
        return raw[:-2], "\r\n"
    if raw.endswith("\n"):
        return raw[:-1], "\n"
    if raw.endswith("\r"):
        return raw[:-1], "\r"
    return raw, ""


def violations(text):
    """[(line_no, word, line)] -- 1-based line numbers; one entry per offending word."""
    lines = [_split_eol(l)[0] for l in text.split("\n")]
    res = []
    for idx, hits in _scan_lines(lines):
        for a, b, _ in hits:
            res.append((idx + 1, lines[idx][a:b], lines[idx]))
    return res


def _apply(content, hits):
    chars = list(content)
    for _, _, seps in hits:
        for k in seps:
            chars[k] = "/"
    return "".join(chars)


def rewrite_line(line, fenced=False):
    """Replace single-backslash separators inside flagged drive-path words with '/'.

    `fenced=True` treats the line as inside a bash/unlabeled fence. Nothing else changes;
    the line's own ending (LF / CRLF / none) is preserved."""
    content, eol = _split_eol(line)
    hits = _analyze_fence_line(content)[0] if fenced else _analyze_prose(content)
    return _apply(content, hits) + eol


def rewrite_lines(raw_lines):
    """raw_lines: list of str each WITH its ending (split on '\\n', keepends). Returns the new list;
    lines the scanner does not flag are returned as the identical objects."""
    parts = [_split_eol(l) for l in raw_lines]
    contents = [p[0] for p in parts]
    out = list(raw_lines)
    for idx, hits in _scan_lines(contents):
        out[idx] = _apply(contents[idx], hits) + parts[idx][1]
    return out


def quote_spaced_path_to_eol(content, anchor):
    """Explicit (NOT automatic) fix for a spaced path argument that runs to end of line.

    `content` is one line WITHOUT or WITH its ending. Finds `anchor` (e.g. "--out "), takes the
    drive path after it up to the end of the line, converts every backslash to '/', and wraps it
    in DOUBLE quotes. Returns None if the anchor/drive path is absent or the path already holds a quote."""
    body, eol = _split_eol(content)
    k = body.find(anchor)
    if k < 0:
        return None
    start = k + len(anchor)
    path = body[start:]
    if not re.match(r"[A-Za-z]:[\\/]", path) or '"' in path:
        return None
    return body[:start] + '"' + path.replace("\\", "/") + '"' + eol


def split_keepends(text):
    pieces = text.split("\n")
    return [p + "\n" for p in pieces[:-1]] + ([pieces[-1]] if pieces[-1] != "" else [])


def rewrite_text(text):
    return "".join(rewrite_lines(split_keepends(text)))


# --------------------------------------------------------------------------
# Harness
# --------------------------------------------------------------------------

_pass = 0
_failures = []


def check(name, cond, detail=""):
    global _pass
    if cond:
        _pass += 1
        print("  PASS  %s" % name)
    else:
        print("  FAIL  %s  %s" % (name, detail))
        _failures.append(name)


def spec_files(sched=None):
    out = []
    for p in sorted(glob.glob(os.path.join(sched or SCHED, "*", "SKILL.md"))):
        d = os.path.basename(os.path.dirname(p))
        if d.startswith("_archive") or d.startswith("_draft"):
            continue
        out.append((d, p))
    return out


def read_text(path):
    with open(path, "rb") as f:
        return f.read().decode("utf-8")


def nviol(text):
    return len(violations(text))


# --------------------------------------------------------------------------
# (b) scanner unit tests
# --------------------------------------------------------------------------

BS = "\\"


def test_scanner_unit():
    P = r"C:\Users\Owner\x.py"
    check("unit: unquoted python violation", nviol("python %s a" % P) == 1)
    check("unit: forward slashes OK", nviol("python C:/Users/Owner/x.py a") == 0)
    check("unit: double-quoted OK", nviol('python "%s" a' % P) == 0)
    check("unit: single-quoted OK", nviol("python '%s' a" % P) == 0)
    check("unit: ANSI-C quoted OK", nviol("python $'%s' a" % r"C:\\Users\\x") == 0)
    check("unit: doubled backslashes OK", nviol(r"python C:\\Users\\Owner\\x.py a") == 0)
    check("unit: escaped space is not a separator",
          nviol(r"python C:\\Program\ Files\\x.py") == 0)
    check("unit: escaped space word with a real single sep flags",
          nviol(r"python C:\Program\ Files\x.py") == 1)
    check("unit: powershell fence OK", nviol("```powershell\npython %s\n```" % P) == 0)
    check("unit: pwsh fence OK", nviol("```pwsh\npython %s\n```" % P) == 0)
    check("unit: js fence OK", nviol('```js\nWorkflow({ scriptPath: C:\\Users\\x })\n```') == 0)
    check("unit: json fence OK", nviol('```json\n{"p": "C:\\\\Users\\\\x"}\npython %s\n```' % P) == 0)
    check("unit: bash fence violation", nviol("```bash\npython %s\n```" % P) == 1)
    check("unit: unlabeled fence violation", nviol("```\npython %s\n```" % P) == 1)
    check("unit: console fence violation", nviol("```console\nC:\\Python\\python.exe x\n```") == 1)
    check("unit: fence closes (line after fence is prose)",
          nviol("```bash\necho hi\n```\nthe file %s here" % P) == 0)
    check("unit: tilde fence", nviol("~~~sh\npython %s\n~~~" % P) == 1)
    check("unit: prose mention OK", nviol("the file %s is read" % P) == 0)
    check("unit: prose with quote OK", nviol("Read %s now" % P) == 0)
    check("unit: inline backtick command span violation",
          nviol("Run `python %s a` now" % P) == 1)
    check("unit: backtick prose path OK", nviol("the script `%s` does x" % P) == 0)
    check("unit: backtick span not starting with command OK",
          nviol("see `use %s` here" % P) == 0)
    check("unit: line-start backtick span violation", nviol("`python %s`" % P) == 1)
    check("unit: bare data path alone on a line is prose, not a command",
          nviol("  C:\\Users\\Owner\\state\\x.json") == 0 and nviol("- C:\\Users\\Owner\\x.ps1") == 0)
    check("unit: mid-sentence interpreter + drive path is a violation",
          nviol("When the run's email has been sent: python %s complete" % P) == 1)
    check("unit: mid-sentence interpreter + -flag is a violation",
          nviol("send via powershell -NoProfile -File %s -To x" % P) == 1)
    check("unit: mid-sentence 'python' prose then path is not a command",
          nviol("the python script lives at %s" % P) == 0)
    check("unit: list marker dash", nviol("- python %s a" % P) == 1)
    check("unit: list marker star", nviol("* python %s a" % P) == 1)
    check("unit: list marker numbered", nviol("1. python %s a" % P) == 1)
    check("unit: indented", nviol("      python %s a" % P) == 1)
    check("unit: env assignment prefix", nviol("PYTHONUTF8=1 python %s a" % P) == 1)
    check("unit: env assignment then prose first word OK", nviol("FOO=1 hello %s" % P) == 0)
    check("unit: cd", nviol(r"cd C:\Users\Owner\AAOS") == 1)
    check("unit: git -C", nviol(r"git -C C:\Users\Owner\repo status") == 1)
    check("unit: node", nviol(r"node C:\Users\Owner\x.js") == 1)
    check("unit: py", nviol(r"py C:\Users\Owner\x.py") == 1)
    check("unit: python3 / npx / npm / bash / sh",
          all(nviol("%s %s" % (c, P)) == 1 for c in ("python3", "npx", "npm", "bash", "sh", "pwsh")))
    interp = r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe -File "C:\a.ps1"'
    v = violations(interp)
    check("unit: interpreter path itself is a violation (quoted arg is not)",
          len(v) == 1 and v[0][1].endswith("powershell.exe"), repr(v))
    v = violations(r"C:/Python/python.exe C:\x\y.py")
    check("unit: mixed style flags only the second word",
          len(v) == 1 and v[0][1] == r"C:\x\y.py", repr(v))
    check("unit: forward-slash interpreter + forward script OK",
          nviol("C:/Python/python.exe C:/x/y.py") == 0)
    check("unit: heredoc body ignored",
          nviol("```bash\ncat <<'EOF'\npython %s\nEOF\npython %s\n```" % (P, P)) == 1)
    check("unit: heredoc unquoted delimiter and <<- body ignored",
          nviol("```bash\ncat <<-EOF\n\tpython %s\n\tEOF\n```" % P) == 0)
    check("unit: here-string <<< is not a heredoc",
          nviol("```bash\ncat <<< x\npython %s\n```" % P) == 1)
    check("unit: full-line comment ignored", nviol("```bash\n# python %s\n```" % P) == 0)
    check("unit: trailing comment ignored", nviol("python C:/ok/x.py # was %s" % P) == 0)
    check("unit: # inside a word is not a comment", nviol(r"python C:\a#b\c.py") == 1)
    check("unit: quoted then unquoted word on one line",
          nviol(r'python "C:\a\b.py" C:\c\d.py') == 1)
    check("unit: JS doubled-backslash literal OK",
          nviol('Workflow({ scriptPath: "C:\\\\Users\\\\Owner\\\\x.js" })') == 0)
    check("unit: escaped quote does not open a quote",
          nviol(r"python \"C:\a\b.py") == 1)
    check("unit: trailing line-continuation backslash is not a separator",
          nviol("python C:/a/b.py --x C:\\\\y \\") == 0)
    check("unit: lowercase-colon text (url, 'ab:\\x') not a drive",
          nviol(r"python http:\\x ab:\y") == 0)
    check("unit: line numbers 1-based and word returned",
          violations("a\nb\npython C:\\q\\r.py\n") == [(3, r"C:\q\r.py", r"python C:\q\r.py")])
    check("unit: two violating words on one line -> two entries",
          nviol(r"python C:\a\b.py C:\c\d.py") == 2)
    check("unit: LF and CRLF endings both scanned",
          nviol("python %s\n" % P) == 1 and nviol("python %s\r\n" % P) == 1
          and violations("python %s\r\n" % P)[0][1] == P)
    check("unit: CRLF fence close recognised",
          nviol("```bash\r\necho hi\r\n```\r\nthe file %s\r\n" % P) == 0)
    check("unit: unterminated fence stays a command fence (fail closed)",
          nviol("```bash\npython %s\n" % P) == 1)
    check("unit: nested longer fence not closed by shorter",
          nviol("````bash\n```\npython %s\n````\n" % P) == 1)
    check("unit: python/other-language fence OK", nviol("```python\nopen(r'%s')\n```" % P) == 0)

    t0 = time.time()
    big = "python " + "x" * 100000 + " " + ("C:/a/b " * 14000)
    nviol(big)
    big2 = "python " + (r"C:\a\b " * 30000)
    n2 = nviol(big2)
    big3 = "`" * 3 + "a`" * 90000
    nviol(big3)
    dt = time.time() - t0
    check("unit: 200k-char lines complete < 2 s (%.2fs, %d hits)" % (dt, n2), dt < 2.0 and n2 == 30000)


# --------------------------------------------------------------------------
# (b2) round-2 scanner tests (review notes N1-N4)
# --------------------------------------------------------------------------


def test_scanner_round2():
    P = r"C:\Users\Owner\x.py"
    PX = "C:/Users/Owner/AppData/Local/Programs/Python/Python313/python.exe"

    # N1 (a): backtick span whose first word is a drive-path executable
    check("n1a: span starting with a forward-slash python.exe + backslash script is a violation",
          nviol("1. Run exactly: `%s C:\\Users\\Owner\\.claude\\maintenance\\a.py --apply`" % PX) == 1)
    check("n1a: span starting with a backslash .exe path is a violation (exe and script)",
          nviol(r"Run `C:\Python\python.exe C:\a\b.py`") == 2)
    check("n1a: span with .cmd / .bat / .com / .EXE drive executables",
          all(nviol("Run `C:/t/x.%s C:\\a\\b.py`" % e) == 1 for e in ("cmd", "bat", "com", "EXE")))
    check("n1a: span with a drive exe and forward-slash script is clean",
          nviol("Run `%s C:/a/b.py --apply`" % PX) == 0)
    check("n1a: span starting with a non-exe drive path stays prose",
          nviol(r"the file `C:\a\b.py --apply` is read") == 0)
    check("n1a: span that is only an executable path (no arguments) is a path mention, not a command",
          nviol(r"Claude (`C:\Users\Owner\.local\bin\claude.exe`): ok") == 0
          and nviol(r"collapses `C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe` to x") == 0)
    check("n1a: quoted script after a drive exe in a span is clean",
          nviol('Run `%s "C:\\a\\b.py" --x`' % PX) == 0)

    # N1 (b): mid-sentence drive-path executable followed by a drive path or a flag
    check("n1b: mid-sentence forward-slash exe + backslash script is a violation",
          nviol("append one entry via %s C:\\Users\\Owner\\.claude\\maintenance\\a.py --entry-file <f>" % PX) == 1)
    check("n1b: mid-sentence exe + -flag + backslash script is a violation",
          nviol("then (%s -X utf8 C:\\a\\b.py)" % PX) == 1)
    check("n1b: mid-sentence exe followed by prose is not a command",
          nviol("the interpreter %s lives beside C:\\a\\b.py" % PX) == 0)
    check("n1b: mid-sentence exe + forward-slash script is clean",
          nviol("via %s C:/a/b.py --x" % PX) == 0)
    check("n1b: mid-sentence backslash exe path itself is flagged",
          nviol(r"via C:\Python\python.exe -m x") == 1)

    # N1 (c): case-insensitive command words
    check("n1c: PYTHON / Python / PowerShell / NODE / Git / CD / Pwsh / NPM at line start",
          all(nviol("%s C:\\a\\b.py" % c) == 1
              for c in ("PYTHON", "Python", "PowerShell", "NODE", "Git", "CD", "Pwsh", "NPM")))
    check("n1c: mixed-case powershell.exe in a span", nviol(r"Run `PowerShell.EXE -File C:\a\b.ps1`") == 1)
    check("n1c: mid-sentence Python / PowerShell",
          nviol(r"sent: Python C:\a\b.py ok") == 1 and nviol(r"via PowerShell -File C:\a\b.ps1") == 1)
    check("n1c: mid-sentence capitalised word not followed by path/flag is prose",
          nviol(r"see Python docs in C:\a\b") == 0)

    # N3: env-assignment commands
    check("n3: 'Set NAME=C:\\x' (sentence case) is a violation",
          nviol(r"  Set WAREHOUSE_DB=C:\Users\Owner\db.sqlite (the live warehouse)") == 1)
    check("n3: set / export / setenv / env prefixes, any case",
          all(nviol("%s WAREHOUSE_DB=C:\\x\\y.sqlite" % c) == 1
              for c in ("set", "SET", "export", "Export", "setenv", "env", "ENV")))
    check("n3: export in a bash fence", nviol("```bash\nexport WAREHOUSE_DB=C:\\x\\y.sqlite\n```") == 1)
    check("n3: forward-slash value is clean", nviol("Set WAREHOUSE_DB=C:/x/y.sqlite") == 0)
    check("n3: quoted value is clean", nviol('export WAREHOUSE_DB="C:\\x\\y.sqlite"') == 0)
    check("n3: 'Set up' prose (no NAME=) is not a command", nviol(r"Set up the file C:\x\y now") == 0)
    check("n3: bare NAME=C:\\x\\y in a command fence is a violation",
          nviol("```\nWAREHOUSE_DB=C:\\x\\y.sqlite python C:/a.py\n```") == 1)
    check("n3: <tmp>\\placeholder and %TEMP%\\ cmd-isms are intentionally not drive paths",
          nviol(r"git worktree add --detach <tmp>\ora-full-gate-<run_id> origin/main") == 0
          and nviol(r"Set FOO=%TEMP%\x\y") == 0)
    v = rewrite_line(r"  Set WAREHOUSE_DB=C:\Users\Owner\db.sqlite (the live warehouse)")
    check("n3: rewrite converts only the drive path",
          v == "  Set WAREHOUSE_DB=C:/Users/Owner/db.sqlite (the live warehouse)", v)

    # N2: paths with spaces
    sp = "C:/Users/Owner/OneDrive - Oxford Capital Partners/Claude_Workspace/02_Outputs/x.md"
    check("n2: unquoted forward-slash drive word + ' - ' in a command arg is a violation",
          nviol("python C:/a/r.py --out %s" % sp) == 1)
    check("n2: unquoted backslash drive word + ' - ' is a violation",
          nviol(r"python C:\a\r.py --out C:\Users\Owner\OneDrive - Oxford Capital Partners\x.md") == 2)
    check("n2: half-rewritten (forward then backslash) form is a violation",
          nviol(r"python C:/a/r.py --out C:/Users/Owner/OneDrive - Oxford Capital Partners\Claude_Workspace\x.md") == 1)
    check("n2: double-quoted spaced path is clean", nviol('python C:/a/r.py --out "%s"' % sp) == 0)
    check("n2: single-quoted spaced path is clean", nviol("python C:/a/r.py --out '%s'" % sp) == 0)
    check("n2: spaced path flagged as an argument in a bash fence", nviol("```bash\ncat %s\n```" % sp) == 1)
    check("n2: spaced path flagged in a command span", nviol("Run `python C:/a/r.py --out %s`" % sp) == 1)
    check("n2: prose data paths with spaces are NOT commands",
          nviol("Write the state to %s now" % sp) == 0
          and nviol(r"  C:\Users\Owner\OneDrive - Oxford Capital Partners\Claude_Workspace\_state\x.json") == 0
          and nviol("- %s" % sp) == 0 and nviol("`%s`" % sp) == 0)
    check("n2: bare data path alone inside an unlabeled fence is not a spaced-path violation",
          nviol("```\n%s\n```" % sp) == 0)
    check("n2: bare backslash data path in an unlabeled fence is still a separator violation",
          nviol("```\nC:\\Users\\Owner\\x.json\n```") == 1)
    check("n2: ' - ' not followed by a word (stdin dash) is not a path with spaces",
          nviol("python C:/a/r.py - < in.txt") == 0)
    check("n2: spaced path has NO automatic rewrite",
          rewrite_line("python C:/a/r.py --out %s\n" % sp) == "python C:/a/r.py --out %s\n" % sp
          and rewrite_line(r"python C:\a\r.py --out C:\Users\Owner\OneDrive - Oxford Capital Partners\x.md")
          == r"python C:/a/r.py --out C:\Users\Owner\OneDrive - Oxford Capital Partners\x.md")
    check("n2: rewrite_text leaves a spaced-path command line byte-identical",
          rewrite_text("python C:/a/r.py --out %s\r\n" % sp) == "python C:/a/r.py --out %s\r\n" % sp)
    cur = ("   %s C:/Users/Owner/.claude/maintenance/u.py --days 30 --out C:/Users/Owner/OneDrive - Oxford Capital "
           "Partners\\Claude_Workspace\\02_Outputs\\<YYYY-MM-DD>_R_v01.md" % PX)
    want = ("   %s C:/Users/Owner/.claude/maintenance/u.py --days 30 --out \"C:/Users/Owner/OneDrive - Oxford Capital "
            "Partners/Claude_Workspace/02_Outputs/<YYYY-MM-DD>_R_v01.md\"" % PX)
    got = quote_spaced_path_to_eol(cur, "--out ")
    check("n2: quote_spaced_path_to_eol converts the whole path to / and wraps it in double quotes",
          got == want and nviol(got) == 0, repr(got))
    check("n2: quote_spaced_path_to_eol keeps CRLF and <placeholder> text",
          quote_spaced_path_to_eol(cur + "\r\n", "--out ") == want + "\r\n")
    check("n2: quote_spaced_path_to_eol refuses a line without the anchor or drive path",
          quote_spaced_path_to_eol("python x.py", "--out ") is None
          and quote_spaced_path_to_eol("python x.py --out rel/p", "--out ") is None)

    # N4 / M6: list markers
    for mk in ("-", "*", "+", "1.", "12.", "3)"):
        check("m6: marker %r + git (not an interpreter) is a violation by itself" % mk,
              nviol(r"%s git -C C:\Users\repo status" % mk) == 1)
    check("m6: marker + cd / npx / npm", all(nviol("- %s C:\\Users\\r" % c) == 1 for c in ("cd", "npx", "npm")))
    check("m6: indented nested markers",
          nviol(r"    - cd C:\x") == 1 and nviol(r"      * git -C C:\x\y s") == 1
          and nviol(r"   2. npm --prefix C:\x run a") == 1)
    check("m6: stacked markers ('1. - git')", nviol(r"1. - git -C C:\Users\r s") == 1)
    check("m6: marker + prose first word stays prose", nviol(r"- see C:\Users\r now") == 0)

    # N4 / M7: env-assignment prefixes
    check("m7: FOO=1 cd C:\\x", nviol(r"FOO=1 cd C:\x") == 1)
    check("m7: FOO=1 python C:\\x\\y.py", nviol(r"FOO=1 python C:\x\y.py") == 1)
    check("m7: two env prefixes then git", nviol(r"A=1 B=2 git -C C:\x\y status") == 1)
    check("m7: export WAREHOUSE_DB=C:\\x", nviol(r"export WAREHOUSE_DB=C:\x") == 1)
    check("m7: marker + env prefix + cd", nviol(r"- FOO=1 cd C:\x") == 1)

    # N4 / M8: trailing backslash (Bash: backslash-newline is a line continuation, not a separator)
    check("m8: trailing lone backslash is not a separator but earlier seps still flag",
          nviol("cd C:\\a\\b\\") == 1 and rewrite_line("cd C:\\a\\b\\") == "cd C:/a/b\\")
    check("m8: 'cd C:\\' alone has no separator", nviol("cd C:\\") == 0)
    check("m8: 'cd C:\\a\\' flags once and keeps the continuation backslash",
          nviol("cd C:\\a\\") == 1 and rewrite_line("cd C:\\a\\") == "cd C:/a\\")
    check("m8: CRLF + trailing backslash", rewrite_line("cd C:\\a\\b\\\r\n") == "cd C:/a/b\\\r\n")

    # N4 / M9: '#' inside quotes never starts a comment
    check("m9: # inside single quotes does not hide a later violation", nviol(r"python 'a #b' C:\x\y.py") == 1)
    check("m9: # inside double quotes does not hide a later violation", nviol(r'python "a #b" C:\x\y.py') == 1)
    check("m9: # inside ANSI-C quotes does not hide a later violation", nviol(r"python $'a #b' C:\x\y.py") == 1)
    check("m9: a real comment still hides", nviol(r"python C:/ok/y.py # C:\x\y.py") == 0)

    # N4 / M23: ANSI-C quoting uses SINGLE backslashes
    check("m23: $'C:\\Users\\x' (single backslashes) is a quoted, clean word", nviol(r"python $'C:\Users\x' a") == 0)
    check("m23: escaped quote inside $'..' does not close it", nviol(r"python $'it\'s' C:\a\b.py") == 1)
    check("m23: text after the real close is scanned", nviol(r"python $'x' C:\a\b.py") == 1)
    check("m23: plain '..' has no escapes (backslash before the closing quote)",
          nviol(r"python 'C:\a\' C:\b\c.py") == 1)

    # N4 / M24: lowercase drive letters
    check("m24: lowercase drive letter is a violation",
          nviol(r"python c:\x\y.py") == 1 and nviol(r"cd d:\x") == 1
          and rewrite_line(r"python c:\x\y.py") == "python c:/x/y.py")

    # N4 / M26: fence-close semantics
    PP = r"C:\Users\Owner\x.py"
    check("m26: longer closing fence closes a shorter opener",
          nviol("```powershell\n`````\npython %s\n" % PP) == 1)
    check("m26: equal-length closer closes", nviol("```powershell\n```\npython %s\n" % PP) == 1)
    check("m26: shorter fence inside a longer one does not close",
          nviol("````powershell\n```\npython %s\n````\n" % PP) == 0)
    check("m26: fence with an info string never closes",
          nviol("```powershell\n```bash\npython %s\n```\n" % PP) == 0)
    check("m26: different fence char never closes", nviol("```powershell\n~~~\npython %s\n```\n" % PP) == 0)
    check("m26: tilde fence needs a tilde closer", nviol("~~~powershell\n```\npython %s\n~~~\n" % PP) == 0)
    check("m26: bash fence reopened after close", nviol("```bash\n```\n```bash\npython %s\n```\n" % PP) == 1)


# --------------------------------------------------------------------------
# (b3) round-3 scanner tests (review M1 + L1)
# --------------------------------------------------------------------------


def test_scanner_round3():
    # M1: an unquoted drive-path .ps1 followed by a -Flag or another drive path is a command
    check("m1: mid-sentence .ps1 + -flag is a violation", nviol(r"via C:\x\send.ps1 -To xx") == 1)
    check("m1: real loan-balance-check shape (prose sentence, .ps1 + flags) is a violation",
          nviol(r'Send the HTML report via C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1 '
                r'-To me -Subject "S" -BodyFile <f>. On exit 2: retry') == 1)
    check("m1: backticked .ps1 + -flag span is a violation", nviol(r"Run `C:\x\s.ps1 -To xx` now") == 1)
    check("m1: .ps1 + drive path mid-sentence flags both words", nviol(r"then run C:\x\s.ps1 C:\y\z") == 2)
    check("m1: command-initial .ps1 + -flag is a violation",
          nviol(r"C:\x\s.ps1 -To xx") == 1 and nviol(r"- C:\x\s.ps1 -To xx") == 1
          and nviol(r"  C:\x\s.ps1 C:\y\z") == 2)
    check("m1: .ps1 extension is case-insensitive", nviol(r"via C:\x\Send.PS1 -To xx") == 1)
    check("m1: .ps1 command in a bash fence is a violation", nviol("```bash\nC:\\x\\s.ps1 -To xx\n```") == 1)
    check("m1: mention-only .ps1 forms are NOT violations",
          nviol(r"see C:\x\send-via-outlook.ps1") == 0
          and nviol(r"the script C:\x\x.ps1 handles X") == 0
          and nviol(r"C:\x\x.ps1 handles X") == 0
          and nviol(r"using C:\x\s.ps1 (see rules)") == 0
          and nviol(r"- C:\x\s.ps1") == 0
          and nviol(r"the sender C:\x\s.ps1.") == 0)
    check("m1: backticked mention-only .ps1 forms are NOT violations (the aaos-expire-leases shape)",
          nviol(r"names `C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1` as the sender") == 0
          and nviol(r"`C:\x\s.ps1` does x") == 0 and nviol(r"see `C:\x\s.ps1 handles` x") == 0)
    check("m1: quoted .ps1 forms are NOT violations",
          nviol(r'via "C:\x\send.ps1" -To xx') == 0 and nviol(r"via 'C:\x\send.ps1' -To xx") == 0
          and nviol(r'Run `powershell -File "C:\x\s.ps1" -To xx`') == 0
          and nviol(r'"C:\x\s.ps1" -To xx') == 0)
    check("m1: forward-slash .ps1 command is clean",
          nviol("via C:/x/send.ps1 -To xx") == 0 and nviol("Run `C:/x/s.ps1 -To xx`") == 0)
    v = rewrite_line(r"Per rules.md \u00a72 and C:\keep\me send via C:\Users\Owner\x\s.ps1 -To xx -BodyFile <h>." + "\r\n")
    check("m1: rewrite changes only the flagged .ps1 word (prose backslash path kept, CRLF kept)",
          v == r"Per rules.md \u00a72 and C:\keep\me send via C:/Users/Owner/x/s.ps1 -To xx -BodyFile <h>." + "\r\n",
          repr(v))

    v = violations("```bash\nC:/x/s.ps1 -To xx -BodyFile C:/Users/Owner/OneDrive - Oxford Capital/x.md\n```")
    check("m1: .ps1-first fence line with a flag is a command: its spaced path argument is flagged",
          len(v) == 1 and v[0][1] == "C:/Users/Owner/OneDrive", repr(v))
    check("m1: .ps1-first fence line with no argument stays a bare data path (spaces not flagged)",
          nviol("```bash\nC:/Users/Owner/OneDrive - Oxford Capital/s.ps1\n```") == 0)
    check("l3: known limitation - capitalised prose with a command word + drive path is flagged",
          nviol(r"Git C:\x\y was cloned") == 1)

    # L1: mid-sentence .cmd / .bat executables
    check("l1: mid-sentence .cmd / .bat executable + drive path is a violation",
          all(nviol("then run C:/t/x.%s C:\\a\\b.py now" % e) == 1 for e in ("cmd", "bat")))
    # L1: exe-first fence line with a spaced path
    sp = "C:/Users/Owner/OneDrive - Oxford Capital/x.md"
    v = violations("```bash\nC:/py/python.exe C:/a.py --out %s\n```" % sp)
    check("l1: exe-first fence line flags the spaced path argument",
          len(v) == 1 and v[0][1] == "C:/Users/Owner/OneDrive", repr(v))
    # L1: two-space Set
    check("l1: 'Set  NAME=C:\\x' (two spaces) is a violation", nviol(r"Set  NAME=C:\x") == 1)


def test_main_missing_tree():
    tmp = tempfile.mkdtemp(prefix="tsp_")
    try:
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                rc = main(os.path.join(tmp, "nonexistent"))
        except Exception as e:
            rc = "raised %r" % (e,)
        out = buf.getvalue()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    check("l2: main() with no scheduled-tasks tree returns non-zero and prints CANNOT RUN",
          isinstance(rc, int) and rc != 0 and "CANNOT RUN" in out, "rc=%r out=%r" % (rc, out))


# --------------------------------------------------------------------------
# (d) rewrite properties
# --------------------------------------------------------------------------

# 15 real lines frozen from the specs BEFORE the fix (spec:line in the trailing comment): (line, in_bash_fence)
FROZEN_SAMPLE = [
    ('python C:\\Users\\Owner\\.claude\\scheduled-tasks\\_shared\\block-sentinel.py claim --task ora-am-brief --block blockB --run-id <session run_id> --ttl-min 30', False),  # ora-am-brief:59
    ('C:/Users/Owner/AppData/Local/Programs/Python/Python313/python.exe C:\\Users\\Owner\\.claude\\maintenance\\open_sessions_probe.py --days 14', False),  # ora-am-brief:289
    ('C:/Users/Owner/AppData/Local/Programs/Python/Python313/python.exe C:\\Users\\Owner\\.claude\\scheduled-tasks\\_shared\\block-sentinel.py claim --task ora-ground-truth-auditor --block main --run-id <guard_run_id> --ttl-min 240', False),  # ora-ground-truth-auditor:39
    ('  python C:\\Users\\Owner\\.claude\\scheduled-tasks\\_shared\\block-sentinel.py claim --task ora-forward-calendar-digest --block main --run-id <run_id> --period week --ttl-min 30', False),  # ora-forward-calendar-digest:18
    ("When the run's email has been sent: python C:\\Users\\Owner\\.claude\\scheduled-tasks\\_shared\\block-sentinel.py complete --task ora-loan-balance-check --block main --run-id <run_id> --period month --email-sent-at <ISO8601>", False),  # ora-loan-balance-check:14
    ('If the run aborts: python C:\\Users\\Owner\\.claude\\scheduled-tasks\\_shared\\block-sentinel.py fail --task ora-loan-balance-check --block main --run-id <run_id> --period month --error "<what broke>"', False),  # ora-loan-balance-check:15
    ('`python C:\\Users\\Owner\\.claude\\scheduled-tasks\\_shared\\block-sentinel.py claim --task ora-renewal-hubspot-reconcile --block main --run-id <run_id> --ttl-min 45`', False),  # ora-renewal-hubspot-reconcile:13
    ('    cd C:\\Users\\Owner\\AAOS', False),  # ora-aaos-publish-contracts:8
    ('   - `python C:\\Users\\Owner\\.claude\\maintenance\\fleet-status.py` (dual-fleet health \u2014 this is the canonical health check per memory/00_system_of_record.md; never hand-count fleet numbers). Recalibrated 2026-07-14 (tech.md \xa73a): the VERDICT line now only reflects real anomalies (overdue never-ran by cadence, missed/stuck one-time fires, throttle skips in the last 24h, collisions) \u2014 a healthy fleet can and should show "VERDICT: OK". Don\'t editorialize a clean OK verdict as if something\'s still wrong; conversely, treat any non-OK verdict as a genuine finding worth a full sentence in the Live Health Check section, not boilerplate.', False),  # ora-cc-schematic-refresh:28
    ('cd C:\\Users\\Owner\\oxford-command-center', False),  # ora-cc-snapshot-refresh:77
    ('  C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\\Users\\Owner\\.claude\\scheduled-tasks\\_shared\\send-via-outlook.ps1" -To "ggoldberg@oxfordra.net" -Subject "ORA Checkout Merge-Forward \u2014 [status] [YYYY-MM-DD]" -BodyFile "<temp html>" -BodyFormat html', False),  # ora-checkout-merge-forward:32
    ('powershell -ExecutionPolicy Bypass -File C:\\Users\\Owner\\.claude\\scheduled-tasks\\_shared\\outlook-sent-probe.ps1 -SubjectFile "<temp .txt containing exactly: Deal Aging SLA - {YYYY-MM-DD}>"', False),  # ora-deal-aging-sla:248
    ('    Send ONE email to ggoldberg@oxfordra.net ONLY (no cc, never ze@) via: powershell -NoProfile -File C:\\Users\\Owner\\.claude\\scheduled-tasks\\_shared\\send-via-outlook.ps1', False),  # ora-full-gate-weekly:33
    ('5. EMAIL (internal): use Outlook COM, the sole send path: `powershell -NoProfile -File C:\\Users\\Owner\\.claude\\scheduled-tasks\\_shared\\send-via-outlook.ps1 -To ggoldberg@oxfordra.net -Subject "Edge mfg announcements - <RUN DATE> - N new" -BodyFile <path to a plain-text body you write in the scratchpad> -BodyFormat text`. TO ggoldberg@oxfordra.net ONLY, no cc. Body: the one-line count summary, then a plain table of rows (company, city/state, announced $, announced jobs, Edge market + confidence, source URL, NEW/UPDATE), then unreachable feeds, markets with no coverage, and the pending file path. Label every figure "announced". On exit 2 or 4 retry once, then note the failure in your final message and continue; do not halt. On exit 5 or 6 (or any code other than 2 or 4) do NOT retry: flag it loudly in the run summary and in your final message and the guard close-out, and never resend (exit 6 = send state unknown \u2014 the message MAY have gone out), per rules.md \xa72. Close the guard `fail` on exit 5, but on exit 6 close it `complete` with no `--email-sent-at` (never `fail`: a same-day re-fire would send the message again).', False),  # ora-edge-mfg-scout-weekly:25
    ('  C:/Users/Owner/AppData/Local/Programs/Python/Python313/python.exe C:\\Users\\Owner\\.claude\\maintenance\\open_sessions_probe.py --days 14 --json', False),  # ora-open-sessions-board:21
]


def _changed_positions(old, new):
    return [i for i, (a, b) in enumerate(zip(old, new)) if a != b]


def _word_spans(content, fenced):
    hits = _analyze_fence_line(content)[0] if fenced else _analyze_prose(content)
    return hits


def _rewrite_props(line, fenced):
    """True if rewrite_line obeys every property on this line."""
    content, eol = _split_eol(line)
    new = rewrite_line(line, fenced)
    nc, neol = _split_eol(new)
    if neol != eol or len(nc) != len(content):
        return False
    hits = _word_spans(content, fenced)
    allowed = {k for _, _, seps in hits for k in seps}
    pos = _changed_positions(content, nc)
    if set(pos) != allowed:
        return False
    if any(content[i] != "\\" or nc[i] != "/" for i in pos):
        return False
    if rewrite_line(new, fenced) != new:
        return False                       # idempotent
    if any(seps for _, _, seps in _word_spans(nc, fenced)):
        return False                       # no separator left to flag (spaced-path hits stay listed)
    return True


def test_rewrite():
    ok = True
    bad = []
    for line, fenced in FROZEN_SAMPLE:
        vio_before = bool(_word_spans(line, fenced))
        if not (vio_before and _rewrite_props(line, fenced)):
            ok = False
            bad.append(line[:60])
    check("rewrite: frozen sample of 15 real lines is flagged, minimal, idempotent, clean after",
          ok and len(FROZEN_SAMPLE) == 15, repr(bad))

    new = rewrite_line("python C:\\a\\b.py\r\n")
    check("rewrite: CRLF preserved", new == "python C:/a/b.py\r\n", repr(new))
    new = rewrite_line("python C:\\a\\b.py\n")
    check("rewrite: LF preserved", new == "python C:/a/b.py\n", repr(new))
    new = rewrite_line("python C:\\a\\b.py")
    check("rewrite: no ending preserved", new == "python C:/a/b.py", repr(new))
    new = rewrite_line(r'python C:\a\b.py "C:\keep\me" C:\\d\\e C:\f\ g\h')
    check("rewrite: touches only flagged single seps (quoted, doubled and escaped space kept)",
          new == r'python C:/a/b.py "C:\keep\me" C:\\d\\e C:/f\ g/h', new)
    new = rewrite_line(r"the file C:\a\b.py stays")
    check("rewrite: prose untouched", new == r"the file C:\a\b.py stays", new)
    new = rewrite_line(r"python C:\a\b.py # C:\c\d")
    check("rewrite: comment text untouched", new == r"python C:/a/b.py # C:\c\d", new)
    new = rewrite_line(r"Run `python C:\a\b.py x` and `C:\p\q.py`")
    check("rewrite: span rewritten, prose span untouched",
          new == r"Run `python C:/a/b.py x` and `C:\p\q.py`", new)

    doc = "```bash\ncat <<'EOF'\npython C:\\a\\b.py\nEOF\npython C:\\c\\d.py\n```\n```powershell\npython C:\\e\\f.py\n```\r\n"
    out = rewrite_text(doc)
    exp = "```bash\ncat <<'EOF'\npython C:\\a\\b.py\nEOF\npython C:/c/d.py\n```\n```powershell\npython C:\\e\\f.py\n```\r\n"
    check("rewrite: document-level (heredoc body + powershell fence left alone)", out == exp, repr(out))
    check("rewrite: document rewrite is idempotent and leaves zero violations",
          rewrite_text(out) == out and nviol(out) == 0)
    check("rewrite: zero-violation text is returned byte-identical",
          rewrite_text("hello\r\nC:\\x\\y prose\r\n") == "hello\r\nC:\\x\\y prose\r\n")

    # property check over seeded synthetic lines
    rnd = random.Random(20261022)
    atoms = [r"C:\Users\Owner\.claude\x.py", r"C:\\a\\b", "C:/ok/p.py", r'"C:\q\r"', r"'C:\s\t'",
             r"C:\P\ F\x", "--flag", "val", "# C:\\c\\d", "`", "'", '"', "$'", "&&", "|", ";",
             "python", "cd", "git", "-", "1.", "FOO=1", "word", "(", ")", "<<EOF", "\\"]
    nbad = 0
    nflag = 0
    for _ in range(4000):
        n = rnd.randint(1, 9)
        body = " ".join(rnd.choice(atoms) for _ in range(n))
        for fenced in (False, True):
            for eol in ("", "\n", "\r\n"):
                line = body + eol
                if _word_spans(body, fenced):
                    nflag += 1
                if not _rewrite_props(line, fenced):
                    nbad += 1
    check("rewrite: 24000 synthetic cases keep every rewrite property (%d flagged)" % nflag,
          nbad == 0 and nflag > 1000, "bad=%d flagged=%d" % (nbad, nflag))


# --------------------------------------------------------------------------
# (c) conformance
# --------------------------------------------------------------------------


def _allowed(spec, line_no, line):
    for key, _reason in ALLOWLIST.get(spec, []):
        if (isinstance(key, int) and key == line_no) or (isinstance(key, str) and key in line):
            return True
    return False


def test_allowlist_semantics():
    global ALLOWLIST
    saved = ALLOWLIST
    try:
        ALLOWLIST = {}
        ok_empty = not _allowed("ora-x", 3, "python C:\\a\\b.py")
        ALLOWLIST = {"ora-x": [(3, "reason"), ("needle", "reason")]}
        ok_line = _allowed("ora-x", 3, "anything")
        ok_sub = _allowed("ora-x", 9, "has needle in it")
        ok_other = not _allowed("ora-x", 4, "other") and not _allowed("ora-y", 3, "needle")
    finally:
        ALLOWLIST = saved
    check("allowlist: empty suppresses nothing; entries match only their spec by line or substring",
          ok_empty and ok_line and ok_sub and ok_other,
          "empty=%s line=%s sub=%s other=%s" % (ok_empty, ok_line, ok_sub, ok_other))


def conformance_violations(name, text):
    """["name:line  word"] for every non-allowlisted violation in one spec's text."""
    return ["%s:%d  %s" % (name, ln, word) for ln, word, line in violations(text)
            if not _allowed(name, ln, line)]


def scan_tree(sched):
    """(n_specs, [violation strings], n_block_sentinel_verb_lines) over one scheduled-tasks tree."""
    specs = spec_files(sched)
    bad = []
    nsent = 0
    for d, p in specs:
        text = read_text(p)
        bad.extend(conformance_violations(d, text))
        nsent += sum(1 for l in text.split("\n") if _LOOSE_VERB.search(l))
    return len(specs), bad, nsent


MIN_SPECS = 60
MIN_VERB_LINES = 50


def tree_guard_problems(n_specs, bad, n_verb_lines):
    """[(kind, message)] for one scan_tree() result; empty means the real-tree guard passes.
    kind is 'specs' (tree too small / not discovered), 'verbs' (non-vacuity) or 'violations'."""
    probs = []
    if n_specs < MIN_SPECS:
        probs.append(("specs", "only %d specs discovered (need >= %d)" % (n_specs, MIN_SPECS)))
    if n_verb_lines < MIN_VERB_LINES:
        probs.append(("verbs", "only %d block-sentinel verb lines (need >= %d)" % (n_verb_lines, MIN_VERB_LINES)))
    if bad:
        probs.append(("violations", "%d violation(s)" % len(bad)))
    return probs


def test_conformance_selftest():
    """The conformance machinery must be able to FAIL: a fixture violation is flagged."""
    viol = "intro\n```bash\npython C:\\a\\b.py\n```\n"
    bad = conformance_violations("ora-x", viol)
    check("selftest: fixture spec text with a known violation is flagged",
          bad == ["ora-x:3  C:\\a\\b.py"], repr(bad))
    check("selftest: fixture spec text without a violation is clean",
          not conformance_violations("ora-x", "intro\n```bash\npython C:/a/b.py\n```\n"))
    tmp = tempfile.mkdtemp(prefix="tsp_")
    try:
        clean = ("python C:/a/b.py\n"
                 "python C:/Users/Owner/.claude/scheduled-tasks/_shared/block-sentinel.py claim --task t\n")
        for name, body in (("ora-clean", clean), ("ora-bad", viol),
                           ("_archive_old", viol), ("_draft_new", viol)):
            os.makedirs(os.path.join(tmp, name))
            with open(os.path.join(tmp, name, "SKILL.md"), "wb") as f:
                f.write(body.encode("utf-8"))
        n, bad, nsent = scan_tree(tmp)
        check("selftest: temp fixture tree -> 2 specs (archive/draft skipped), exactly the bad one flagged",
              n == 2 and len(bad) == 1 and bad[0].startswith("ora-bad:3"), "n=%d bad=%r" % (n, bad))
        check("selftest: temp fixture tree counts its block-sentinel verb lines", nsent == 1, "nsent=%d" % nsent)
        n, bad, _ = scan_tree(os.path.join(tmp, "nonexistent"))
        check("selftest: empty tree -> 0 specs (the real-tree >= 60 guard would fail)", n == 0 and not bad)
        n, bad, nsent = scan_tree(tmp)
        kinds = {k for k, _ in tree_guard_problems(n, bad, nsent)}
        check("selftest: the real-tree guard FAILS a deliberately tiny fixture tree (specs + verb + violation)",
              {"specs", "verbs", "violations"} <= kinds, repr(kinds))
        check("selftest: guard thresholds are exactly 60 specs / 50 verb lines",
              bool(tree_guard_problems(59, [], 50)) and bool(tree_guard_problems(60, [], 49))
              and not tree_guard_problems(60, [], 50) and bool(tree_guard_problems(60, ["x"], 50)))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_specs_conform():
    n, bad, nsent = scan_tree(SCHED)
    probs = dict(tree_guard_problems(n, bad, nsent))
    check("conformance: spec tree discovered (>= %d specs)" % MIN_SPECS, "specs" not in probs, "n=%d" % n)
    check("conformance: non-vacuous - found >= %d block-sentinel verb lines (%d)" % (MIN_VERB_LINES, nsent),
          "verbs" not in probs, "nsent=%d" % nsent)
    check("conformance: no unquoted backslash drive path (or unquoted spaced drive path) in a command "
          "context (%d specs)" % n,
          "violations" not in probs,
          "%d violation(s):\n      %s\n      FIX: use unquoted forward slashes "
          "(C:/Users/Owner/...); do NOT quote the block-sentinel path; quote paths that contain spaces"
          % (len(bad), "\n      ".join(bad[:40])))
    check("conformance: allowlist is empty", all(not v for v in ALLOWLIST.values()), repr(ALLOWLIST))


# --------------------------------------------------------------------------
# (e) block-sentinel lines remain visible to test_scheduled_task_run_guard.py
# --------------------------------------------------------------------------


def _load_guard():
    path = os.path.join(HERE, "test_scheduled_task_run_guard.py")
    try:
        spec = importlib.util.spec_from_file_location("_tstrg_for_paths", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.CLAIM_LINE, mod.FINALIZE_LINE
    except Exception:
        # Re-declared from maintenance/_tests/test_scheduled_task_run_guard.py (CLAIM_LINE / FINALIZE_LINE).
        return (re.compile(r"block-sentinel(?:\.py)?\s+claim\b", re.I),
                re.compile(r"block-sentinel(?:\.py)?\s+(complete|fail)\b", re.I))


# Loose discovery: also catches a QUOTED script path, which the guard's own regexes miss.
_LOOSE_VERB = re.compile(r"block-sentinel(?:\.py)?[\"']?\s+(?:claim|complete|fail)\b", re.I)
_TOKEN = re.compile(r"(\S*?block-sentinel(?:\.py)?[\"']?)(?=\s+(?:claim|complete|fail)\b)", re.I)


def sentinel_line_problems(spec, lines, claim_rx, final_rx):
    """[(line_no, problem)] for every block-sentinel verb line in one spec."""
    probs = []
    for i, raw in enumerate(lines, 1):
        line = _split_eol(raw)[0]
        if not _LOOSE_VERB.search(line):
            continue
        if not (claim_rx.search(line) or final_rx.search(line)):
            probs.append((i, "not matched by the run-guard CLAIM/FINALIZE regexes (quoted path?)"))
            continue
        m = _TOKEN.search(line)
        if not m:
            probs.append((i, "no script token found"))
            continue
        tok = m.group(1).lstrip("`")
        if "\\" in tok or '"' in tok or "'" in tok:
            probs.append((i, "script token has a backslash or quote: %r" % tok))
            continue
        if "/" in tok:
            try:
                argv = shlex.split(line[m.start(1):].lstrip("`").split("`")[0])
            except ValueError as e:
                probs.append((i, "shlex failed: %s" % e))
                continue
            if not argv or "\\" in argv[0] or not argv[0].endswith("block-sentinel.py"):
                probs.append((i, "argv[0] is not a forward-slash path ending in block-sentinel.py: %r"
                              % (argv[:1],)))
    return probs


def test_block_sentinel_lines():
    claim_rx, final_rx = _load_guard()
    total = 0
    bad = []
    for d, p in spec_files():
        lines = read_text(p).split("\n")
        total += sum(1 for l in lines if _LOOSE_VERB.search(l))
        for ln, pr in sentinel_line_problems(d, lines, claim_rx, final_rx):
            bad.append("%s:%d  %s" % (d, ln, pr))
    check("sentinel: found block-sentinel verb lines (%d)" % total, total >= 80, "total=%d" % total)
    check("sentinel: every verb line matches the run-guard regexes and has a forward-slash, unquoted script path",
          not bad, "\n      " + "\n      ".join(bad[:30]))

    P = "python C:/Users/Owner/.claude/scheduled-tasks/_shared/block-sentinel.py claim --task t --block main\n"
    good = sentinel_line_problems("t", [P], claim_rx, final_rx)
    quoted = sentinel_line_problems("t", [P.replace("C:/", '"C:/').replace(".py ", '.py" ')], claim_rx, final_rx)
    back = sentinel_line_problems("t", [P.replace("/", "\\")], claim_rx, final_rx)
    check("sentinel: unit - forward slash accepted, quoted path and backslash path rejected",
          not good and quoted and back, "good=%r quoted=%r back=%r" % (good, quoted, back))


# --------------------------------------------------------------------------


def main(sched=None):
    sched = sched or SCHED
    if not os.path.isdir(sched):
        print("CANNOT RUN: no scheduled-tasks tree at %s" % sched)
        return 2
    test_scanner_unit()
    test_scanner_round2()
    test_scanner_round3()
    test_rewrite()
    test_allowlist_semantics()
    test_conformance_selftest()
    test_specs_conform()
    test_block_sentinel_lines()
    test_main_missing_tree()
    print("\ntask-spec-command-paths: %d pass, %d fail" % (_pass, len(_failures)))
    return 1 if _failures else 0


if __name__ == "__main__":
    sys.exit(main())
