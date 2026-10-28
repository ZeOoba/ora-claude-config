"""rewrite-advisory-guard -- PreToolUse hook for Bash. ADVISORY ONLY: NEVER BLOCKS.

WHAT. When a Bash command rewrites a file in place with `sed -i` / `sed
--in-place`, `perl -i`, or `python -c "<code that writes a file>"`, this guard
adds one short model-visible note (hookSpecificOutput.additionalContext)
pointing at the Edit/Write tools. Nothing else changes: the command still runs
exactly as written.

WHY ADVISORY. /insights (2026-07-28..10-28) found sed / inline-Python edits
expanding escape sequences, eating backslashes and breaking newlines, with
rework each time. But `sed -i` is also a legitimate, common one-liner, so a
block would fire on good commands and teach override habits (the same reasoning
pipe-mask-guard and winpath-guard recorded). A nudge costs the author nothing
and still removes the habit.

NEVER BLOCKS, NEVER REWRITES. Exit code is always 0. This guard never emits a
permissionDecision (that would widen permissions) and never emits updatedInput
(only pipe-mask-guard may rewrite, and it must stay last in the chain). The
dispatcher's emit_stdout merges additionalContext from several guards.

SCOPE (detection is by tokenised command position, not substring, so
`git commit -m "avoid sed -i"` and `echo "sed -i"` stay silent; heredoc bodies
are text and are skipped):
  - sed: option clusters walked letter by letter (-i, -i.bak, -ni, -Ei; e/f/l
    take the rest of the cluster or the next word as their argument, so
    `sed -finsert.sed` and `sed -e'i x'` are NOT in-place) and --in-place[=SUF]
    or an unambiguous abbreviation (--in...).
  - perl: option clusters walked per perl's switch grammar (-i, -pi, -0pi,
    -wpi; -M/-I/-m/-x/-e/-E/... take their argument), stopping at the first
    non-option word (the script name) so `perl script.pl -input x` is silent.
  - python / python3.N / py / pythonw with -c (also bundled, -Bc) whose code
    text opens a file for writing (open(..., 'w'/'a'/'x'/'+')), or calls
    .write_text( / .write_bytes( / os.replace|rename|remove|unlink /
    shutil.move|copy*. A bare `.write(` is NOT a signal: it is also StringIO,
    sys.stdout and sockets. Only the first 8 KB of code is scanned.
  - the same tools behind compound heads (then/do/else/{/!), `bash|sh -c`,
    `uv run`, `xargs` (its command word) and `find -exec`.
BOUNDED WORK. One global budget (_WORK_LIMIT words visited, plus re-tokenised
nested `sh -c` text) covers every recursion; when spent the guard goes silent.
`open(` calls are parsed (2nd positional / mode=; `Path(..).open(` 1st
positional), never matched through a character window. Review history: round 1
(heredoc/option-walker/regex-backtracking) and round 2 (find -exec stall,
open() window false positives) both BLOCKed; the budget is the structural fix.
Known residual (silent, status quo): a `<<WORD` inside quotes/comment/`$((1<<n))`
blinds the rest of the command (heredoc stripping is textual); `bash <<EOF` and
`python <<EOF` bodies; `sudo|nice|stdbuf|env -i|function|coproc` heads; a
backslash-semicolon-separated second `-exec`; a mid-word `#` (`echo a#b && sed -i ...`,
the shared tokeniser treats it as a comment), `python -` stdin scripts,
`sed -i` hidden in `eval`/`source`, and anything the tokeniser rejects.

FAIL-OPEN. Any error -> no output, exit 0. Stdlib only. ASCII-only.
"""
import collections
import json
import os
import re
import sys

HOOKS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HOOKS_DIR, "lib"))

MESSAGE = (
    "rewrite-advisory-guard (advisory, command NOT blocked): this command rewrites "
    "a file with %s. In-place sed/perl and inline `python -c` writes expand escape "
    "sequences, eat backslashes and break newlines; prefer the Edit or Write tool "
    "for file changes. Ignore this if the in-place rewrite is deliberate."
)

_PY_NAME = re.compile(r"^(?:python[0-9.]*|pythonw|py)$")
_PY_CODE_CAP = 8192
_OPEN_CALL = re.compile(r"\bopen\(")
_MODE_LIT = re.compile(r"""^\s*['"]([rwaxbt+]{1,4})['"]\s*$""")
_MODE_KW = re.compile(r"""^\s*mode\s*=\s*['"]([rwaxbt+]{1,4})['"]\s*$""")
_ARG_SCAN_CAP = 400

# GLOBAL WORK BUDGET. Every scan below is bounded by one counter, so no input shape
# (nested find -exec, xargs chains, bash -c towers) can stall the in-process Bash
# chain: when the budget is spent the guard goes SILENT (fail open). Cost is counted
# in words visited per _tool_hit call (which includes the slice/command_words cost of
# every recursion) and in characters re-tokenised for nested `sh -c` strings.
_WORK_LIMIT = 40000
_work = [0]


class _OutOfBudget(Exception):
    pass


def _spend(n):
    _work[0] += n
    if _work[0] > _WORK_LIMIT:
        raise _OutOfBudget()
_PY_WRITE_CALL = re.compile(
    r"\.write_text\(|\.write_bytes\("
    r"|\bos\.(?:replace|rename|remove|unlink)\("
    r"|\bshutil\.(?:move|copy|copyfile|copy2)\(")
_HEAD_WORDS = {"then", "do", "else", "elif", "if", "while", "until", "{", "!", "time"}
_SHELLS = {"bash", "sh", "zsh", "dash"}
_XARGS_ARG_OPTS = {"-I", "-n", "-P", "-d", "-L", "-s", "-E", "-a"}
_HEREDOC = re.compile(r"<<(-?)[ \t]*\\?(['\"]?)([^\s'\"<>;&|()]+)\2")
_MAX_DEPTH = 3
_MAX_PENDING_HEREDOCS = 64


def _strip_heredocs(command):
    """Drop heredoc BODIES (keep the line carrying the operator). A body line is
    text, not a command; the tokeniser would otherwise split it into statements."""
    if "<<" not in command:
        return command
    out, pending = [], collections.deque()
    for line in command.split("\n"):
        if pending:
            delim = pending[0]
            if line.strip().rstrip(")\"'; ") == delim:
                pending.popleft()
                out.append(line)
            continue
        out.append(line)
        for m in _HEREDOC.finditer(line):
            if len(pending) >= _MAX_PENDING_HEREDOCS:
                break  # absurd operator count: stop recording (linear, bounded)
            if m.start() > 0 and line[m.start() - 1] == "<":
                continue  # <<< here-string
            if m.group(3).isdigit():
                continue  # $((1<<5)) is arithmetic
            pending.append(m.group(3))
    return "\n".join(out)


def _sed_in_place(words):
    i, n = 0, len(words)
    while i < n:
        w = words[i]
        i += 1
        if w.startswith("--"):
            name = w.split("=", 1)[0]
            if len(name) >= 4 and "--in-place".startswith(name):
                return True
            if name in ("--expression", "--file", "--line-length") and "=" not in w:
                i += 1
            continue
        if len(w) < 2 or w[0] != "-":
            continue
        for k in range(1, len(w)):
            ch = w[k]
            if ch == "i":
                return True
            if ch in "efl":
                if k == len(w) - 1:
                    i += 1  # argument is the next word
                break  # rest of the cluster is the argument
    return False


_PERL_REST_ARG = set("IMmxdDFVC")  # attached argument ends the cluster


def _perl_in_place(words):
    i, n = 0, len(words)
    while i < n:
        w = words[i]
        i += 1
        if len(w) < 2 or w[0] != "-" or w.startswith("--"):
            return False  # first non-option word is the script / file: options end
        k = 1
        while k < len(w):
            ch = w[k]
            if ch == "i":
                return True
            if ch in "eE":
                if k == len(w) - 1:
                    i += 1
                break
            if ch == "I":
                if k == len(w) - 1:
                    i += 1
                break
            if ch in _PERL_REST_ARG:
                break
            if ch in "0lC":  # numeric attachments: -0777, -l, -C7
                k += 1
                while k < len(w) and w[k].isdigit():
                    k += 1
                continue
            k += 1
    return False


def _split_args(code, i):
    """Top-level comma-separated argument strings of the call whose '(' ends at
    code[i-1], scanning at most _ARG_SCAN_CAP chars; quotes and brackets nest."""
    end = min(len(code), i + _ARG_SCAN_CAP)
    depth, quote, cur, args = 0, None, [], []
    while i < end:
        ch = code[i]
        if quote:
            cur.append(ch)
            if ch == "\\" and i + 1 < end:
                cur.append(code[i + 1])
                i += 2
                continue
            if ch == quote:
                quote = None
        elif ch in "'\"":
            quote = ch
            cur.append(ch)
        elif ch in "([{":
            depth += 1
            cur.append(ch)
        elif ch in ")]}":
            if depth == 0:
                args.append("".join(cur))
                return args
            depth -= 1
            cur.append(ch)
        elif ch == "," and depth == 0:
            args.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
        i += 1
    args.append("".join(cur))
    return args


def _writes_mode(mode):
    return any(c in mode for c in "wax+")


def _open_call_writes(code, m):
    """True when the open( call at match m passes a WRITE mode. Builtin open():
    2nd positional or mode=. `Path(..).open(`: 1st positional or mode=. Other
    `.open(` receivers (os.open, webbrowser.open) are ignored."""
    start = m.start()
    first_pos = 1
    if start > 0 and code[start - 1] == ".":
        if start < 2 or code[start - 2] != ")":
            return False
        first_pos = 0
    args = _split_args(code, m.end())
    for idx, a in enumerate(args):
        km = _MODE_KW.match(a)
        if km and _writes_mode(km.group(1)):
            return True
        if idx == first_pos:
            lm = _MODE_LIT.match(a)
            if lm and _writes_mode(lm.group(1)):
                return True
    return False


def _py_code_writes(code):
    code = code[:_PY_CODE_CAP]
    _spend(len(code) // 16 + 1)
    if _PY_WRITE_CALL.search(code):
        return True
    for m in _OPEN_CALL.finditer(code):
        _spend(_ARG_SCAN_CAP // 16)  # each open( may scan up to _ARG_SCAN_CAP chars
        if _open_call_writes(code, m):
            return True
    return False


def _python_writes(words):
    i, n = 0, len(words)
    while i < n:
        w = words[i]
        if len(w) < 2 or w[0] != "-" or w.startswith("--"):
            return False  # first non-option word is a script / module: -c is its own
        if w[1:].isalpha() and w.endswith("c"):
            return _py_code_writes(words[i + 1]) if i + 1 < n else False
        i += 2 if w in ("-X", "-W") else 1
    return False


def _strip_heads(words):
    i = 0
    while i < len(words) and words[i] in _HEAD_WORDS:
        i += 1
        if i and words[i - 1] == "time" and i < len(words) and words[i] == "-p":
            i += 1
    return words[i:]


def _tool_hit(words, bp, depth=0):
    """Label of the in-place tool this stage runs, or None."""
    if depth > _MAX_DEPTH:
        return None
    _spend(len(words) + 1)
    words = bp.command_words(_strip_heads(words))
    words = _strip_heads(words)
    if not words:
        return None
    name = bp._base(words[0])
    rest = words[1:]
    if name == "sed":
        return "sed -i" if _sed_in_place(rest) else None
    if name == "perl":
        return "perl -i" if _perl_in_place(rest) else None
    if _PY_NAME.match(name):
        return "python -c (file write)" if _python_writes(rest) else None
    if name == "uv":
        for j, w in enumerate(rest):
            if _PY_NAME.match(bp._base(w)):
                return _tool_hit(rest[j:], bp, depth + 1)
        return None
    if name in _SHELLS:
        for j, w in enumerate(rest):
            if len(w) < 2 or w[0] != "-" or w.startswith("--"):
                return None  # first non-option word is a script: later -c is its own
            if w[1:].isalpha() and w.endswith("c") and j + 1 < len(rest):
                return _command_hit(rest[j + 1], bp, depth + 1)
        return None
    if name == "xargs":
        j = 0
        while j < len(rest):
            if rest[j].startswith("-"):
                j += 2 if rest[j] in _XARGS_ARG_OPTS else 1
                continue
            return _tool_hit(rest[j:], bp, depth + 1)
        return None
    if name == "find":
        for j, w in enumerate(rest):
            if w in ("-exec", "-execdir", "-ok", "-okdir") and j + 1 < len(rest):
                hit = _tool_hit(rest[j + 1:], bp, depth + 1)
                if hit:
                    return hit
    return None


def _command_hit(command, bp, depth=0):
    if depth:
        _spend(len(command) // 16 + 1)  # nested sh -c strings are re-tokenised
    pipes = bp.pipelines(_strip_heredocs(command))
    if not pipes:
        return None
    for pipe in pipes:
        for stage in pipe:
            label = _tool_hit(stage, bp, depth)
            if label:
                return label
    return None


def decide(payload):
    """The advisory string, or None to stay silent."""
    import bash_pipelines as bp
    if not isinstance(payload, dict):
        return None
    if payload.get("tool_name") not in (None, "Bash"):
        return None
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return None
    command = tool_input.get("command")
    if not isinstance(command, str) or not command.strip():
        return None
    _work[0] = 0
    try:
        label = _command_hit(command, bp)
    except _OutOfBudget:
        return None  # fail open: too much to inspect, stay silent
    return MESSAGE % label if label else None


def main():
    try:
        raw = sys.stdin.buffer.read()
        payload = json.loads(raw.decode("utf-8", "replace"))
        advice = decide(payload)
    except Exception:  # noqa: BLE001 -- fail open: no advice, command runs as written
        return
    if not advice:
        return
    sys.stdout.write(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "additionalContext": advice,
    }}))


if __name__ == "__main__":
    main()
    sys.exit(0)
