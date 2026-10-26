"""winpath-guard -- PreToolUse hook for Bash. BLOCKING (exit 2), fail-open.

WHAT. Blocks the two Bash command shapes that silently corrupt a Windows path:
  1. an UNQUOTED drive path with single backslashes: `python C:\\Users\\x.py`
     reaches python as `C:Usersx.py` (an unquoted backslash is an escape). The
     interpreter word is affected too: `C:\\Windows\\...\\powershell.exe -File
     "..."` fails although its argument is quoted.
  2. `\\$` or `\\`` inside a DOUBLE-quoted string that holds a drive path:
     "C:\\a\\$SID\\b" keeps a literal `$SID` (bash's own `\\$` escape) -- the
     write lands in a bogus directory and a same-command readback hides it.
  The `\\$` / `\\`` is flagged only when the backslash directly follows a
  path-name character (alphanumeric, `_`, `-`, `.`, `~`): then it is plausibly the
  separator. After `]`, `+`, `;`, `{`, `|` or a `\\` pair it is a deliberate escape
  (PowerShell -Command one-liners: `[ref]\\$null`, `'C:\\x\\'+\\$d`,
  `C:\\\\\\$w`), which bash renders correctly -- 6 of 6 hits in 35,164 real
  Bash calls were such correct commands.
Everything else passes: single-quoted, double-quoted without `\\$`, doubled
backslashes, forward slashes, heredoc bodies, comments.

KNOWN ACCEPTED FALSE POSITIVE: a contrived `"C:\\x\\file\\$1.txt"` (a literal
dollar-digit filename after a name char) is still blocked; the fix (forward
slashes or single quotes) is mechanical.

WHY A BLOCK. Doctrine since 2026-07-24 (feedback_bash_unquoted_windows_paths_
collapse, feedback_bash_backslash_dollar_escape_windows_path); still recurring
in the 2026-10-22 /insights window, and 24 of 67 scheduled-task specs carried
the shape. The corruption is SILENT (a wrong-but-valid path, or "No such file"
that agents hand-correct and move on), so a warning arrives after the damage.
A block is cheap here: the fix is always mechanical (forward slashes or
quotes) and never needs an override.

FAIL-OPEN. Any internal error -> exit 0, nothing printed. The scanner is a
small quote-state machine over the raw text, not shlex (shlex discards the
quoting this decision depends on).

Stdlib only. ASCII-only.
"""
import json
import re
import sys

_BOUNDARY = set(" \t\n;&|()<>=`")
_WORD_END = set(" \t\n;&|()<>")
_DQ_WS = " \t\n\r"
# `<<EOF`, `<<-EOF`, `<<` + backslash + `EOF`, `<<'END-PS'`, `<<"E_1"`: the delimiter is any run
# of non-space, non-quote, non-operator characters (hyphens and dots included).
_HEREDOC = re.compile(r"<<(-?)[ \t]*\\?(['\"]?)([^\s'\"<>;&|()]+)\2")


def _skip_heredocs(cmd, i, pending):
    """`i` is just past the newline that ends a line carrying heredoc
    operators. Skip each pending body (in order) up to its delimiter line."""
    n = len(cmd)
    for delim, strip_tabs in pending:
        while i < n:
            j = cmd.find("\n", i)
            line = cmd[i:] if j < 0 else cmd[i:j]
            i = n if j < 0 else j + 1
            if (line.lstrip("\t") if strip_tabs else line).rstrip("\r") == delim:
                break
    return i


class _Dq(object):
    """Double-quote frame. The drive-path / escaped-backtick facts are kept per
    WHITESPACE-FREE WORD and updated incrementally, so the scan stays linear
    (a look-back per backslash-dollar was quadratic: 200k took 662 s)."""
    __slots__ = ("start", "drive", "bt_before_drive", "bt")

    def __init__(self, start):
        self.start = start
        self.reset()

    def reset(self):
        self.drive = False
        self.bt_before_drive = False
        self.bt = False


def find_violation(cmd):
    """(kind, excerpt) for the first corrupting path shape, else None.

    Context stack: a double-quoted string is a frame; `$(` opened inside one
    (or in plain shell) is its own UNQUOTED frame until its matching `)`, so a
    `"` inside a command substitution does not flip the outer quote state and a
    heredoc inside `"$(cat <<'EOF' ... EOF)"` is recognised."""
    i, n = 0, len(cmd)
    stack = []  # frames: _Dq | "'" | ["sub", paren_depth]
    pending = []
    while i < n:
        c = cmd[i]
        top = stack[-1] if stack else None
        if top == "'":
            if c == "'":
                stack.pop()
            i += 1
            continue
        if isinstance(top, _Dq):
            if c == "\\" and i + 1 < n:
                nxt = cmd[i + 1]
                if nxt in "$`":
                    # Corruption only when this backslash is plausibly the path
                    # separator, i.e. it directly follows a path-name character.
                    # After a consumed backslash pair, `]`, `+`, `;`, `{` etc. it
                    # is a deliberate escape (PowerShell `$` pass-through).
                    sep = i > 0 and (cmd[i - 1].isalnum() or cmd[i - 1] in "_-.~")
                    if nxt == "`":
                        if top.drive and sep and not top.bt_before_drive:
                            return ("backslash-dollar", cmd[top.start:i + 2])
                        top.bt = True
                    elif top.drive and sep:
                        return ("backslash-dollar", cmd[top.start:i + 2])
                i += 2
                continue
            if c == '"':
                stack.pop()
                i += 1
                continue
            if c == "$" and i + 1 < n and cmd[i + 1] == "(":
                stack.append(["sub", 0])
                i += 2
                continue
            if c in _DQ_WS:
                top.reset()
            elif (c.isalpha() and i + 2 < n and cmd[i + 1] == ":"
                  and cmd[i + 2] == "\\" and (i == 0 or not cmd[i - 1].isalnum())):
                if not top.drive:
                    top.drive = True
                    top.bt_before_drive = top.bt
            i += 1
            continue
        # ---- unquoted (base shell, or inside a $( ) frame)
        if c == "'":
            stack.append("'")
            i += 1
            continue
        if c == "$" and i + 1 < n and cmd[i + 1] == "'":
            stack.append("'")  # ANSI-C $'...': out of scope, treat as single-quoted
            i += 2
            continue
        if c == '"':
            stack.append(_Dq(i + 1))
            i += 1
            continue
        if c == "$" and i + 1 < n and cmd[i + 1] == "(":
            stack.append(["sub", 0])
            i += 2
            continue
        if top is not None:  # inside $( )
            if c == "(":
                top[1] += 1
            elif c == ")":
                if top[1] == 0:
                    stack.pop()
                else:
                    top[1] -= 1
                i += 1
                continue
        if c == "#" and (i == 0 or cmd[i - 1] in " \t\n;&|("):
            j = cmd.find("\n", i)
            i = n if j < 0 else j
            continue
        if c == "<" and cmd.startswith("<<", i) and not cmd.startswith("<<<", i):
            m = _HEREDOC.match(cmd, i)
            if m and not m.group(3).isdigit():  # `$((1 << 5))` is arithmetic
                pending.append((m.group(3), m.group(1) == "-"))
                i = m.end()
                continue
        if c == "\n":
            i += 1
            if pending:
                i = _skip_heredocs(cmd, i, pending)
                pending = []
            continue
        if (c.isalpha() and i + 2 < n and cmd[i + 1] == ":" and cmd[i + 2] == "\\"
                and (i == 0 or cmd[i - 1] in _BOUNDARY)):
            j = i + 2
            while j < n and cmd[j] not in _WORD_END and cmd[j] not in "'\"":
                if cmd[j] == "\\":
                    nxt = cmd[j + 1] if j + 1 < n else ""
                    if nxt in ("\\", " ", "\n", ""):
                        j += 2
                        continue
                    end = j
                    while end < n and cmd[end] not in _WORD_END:
                        end += 1
                    return ("unquoted", cmd[i:end])
                j += 1
            i = j
            continue
        if c == "\\":
            i += 2
            continue
        i += 1
    return None


MESSAGE = (
    "BLOCKED (winpath-guard): this Bash command contains a Windows path that bash "
    "will silently corrupt:\n    %s\n%s\n"
    "Fix: write the path with forward slashes (C:/Users/Owner/...), which every "
    "Windows program here accepts. Single quotes also work. "
    "(memory: feedback_bash_unquoted_windows_paths_collapse)\n"
)
WHY = {
    "unquoted": "An unquoted backslash is an escape character in bash, so "
                "C:\\Users\\x becomes C:Usersx before the program sees it.",
    "backslash-dollar": "Inside double quotes, \\$ is bash's own escape: the "
                        "$variable is NOT expanded and the separator backslash is "
                        "dropped, so the path points somewhere else.",
}


def main():
    try:
        payload = json.loads(sys.stdin.buffer.read().decode("utf-8", "replace"))
        if payload.get("tool_name") not in (None, "Bash"):
            return
        command = (payload.get("tool_input") or {}).get("command")
        if not isinstance(command, str):
            return
        hit = find_violation(command)
    except Exception:  # noqa: BLE001 -- fail open
        return
    if hit is None:
        return
    kind, excerpt = hit
    sys.stderr.write(MESSAGE % (excerpt[:200], WHY.get(kind, "")))
    sys.exit(2)


if __name__ == "__main__":
    main()
    sys.exit(0)
