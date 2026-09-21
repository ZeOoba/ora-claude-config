"""Linear-time drop-in for stdlib shlex.shlex -- shared by every guard that tokenizes a whole
Bash command (config-write-guard, commit-hygiene-guard, memory-orphan-link-guard).

WHY (measured 2026-09-21). stdlib `shlex.read_token` builds each token with
`self.token += ch`: one full string copy per character, so ONE long token (a base64 blob,
a minified one-liner) is O(len^2) memcpy -- 256KB ~1.5s, 512KB ~6-12s per pass, and each
guard makes 2-4 passes. The guards run in the dispatcher's in-process Bash chain with no
per-guard timeout, so one slow tokenizer stalls every guard behind it. commit-hygiene-guard
and memory-orphan-link-guard reach shlex on ANY command whose text contains "commit", not
only `git commit`.

WHAT. `LinearShlex` swaps the token accumulator for a list-backed buffer (`TokenBuf`) and
changes NOTHING else: the state machine is still the stdlib's own `read_token` (no copied
logic to drift), so tokens AND exceptions (type + message) are identical by construction,
and pinned against stdlib shlex by differential fuzz + exhaustive enumeration in
hooks/tests/test-linear-shlex-commit-guards.py and test-always-on-linear-redirect-exempt.py.
It is used only past SHLEX_LINEAR_MIN_CHARS; shorter text keeps the stdlib class untouched
(below ~12KB the stdlib class is the faster one).

The one observable difference: after a parse `lex.token` is a TokenBuf, not a str. Nothing
in the guards reads it.

DEGRADATION. Consumers import this in their OWN try/except and fall back to stdlib shlex
(correct, just quadratic on a giant single token) -- a partial deploy of the guards ahead
of this file must never make a guard inert or crash it. Stdlib only. ASCII-only.
"""
import shlex

SHLEX_LINEAR_MIN_CHARS = 12288  # below ~12KB the stdlib class is the faster one


class TokenBuf(object):
    """Append-only token accumulator supporting exactly what shlex.read_token does to
    `self.token`: `+= str`, truthiness, `== ''`, and being read out once. (After a
    parse `lex.token` is a TokenBuf, not a str as in stdlib; nothing reads it.)"""
    __slots__ = ("_parts",)

    def __init__(self, first=""):
        self._parts = [first] if first else []

    def __iadd__(self, piece):
        if piece:
            self._parts.append(piece)
        return self

    def __bool__(self):
        return bool(self._parts)

    def __eq__(self, other):
        return "".join(self._parts) == other

    __hash__ = None

    def __str__(self):
        return "".join(self._parts)


class LinearShlex(shlex.shlex):
    @property
    def token(self):
        return self._tokbuf

    @token.setter
    def token(self, value):
        self._tokbuf = value if isinstance(value, TokenBuf) else TokenBuf(value)

    def read_token(self):
        result = shlex.shlex.read_token(self)
        return str(result) if isinstance(result, TokenBuf) else result


def shlex_class(text):
    """The shlex class to tokenize `text` with: the linear one past the threshold, else the
    stdlib class. Call as `shlex_class(text)(text, posix=True, ...)`."""
    return LinearShlex if len(text) > SHLEX_LINEAR_MIN_CHARS else shlex.shlex


def split(s, comments=False, posix=True):
    """Drop-in for shlex.split(s, comments=comments, posix=posix) that is linear on a
    single giant token. Mirrors the stdlib body exactly (whitespace_split, commenters
    cleared unless `comments`); a non-str `s` is delegated to the stdlib so its own
    None/stream handling and errors are unchanged."""
    if not isinstance(s, str):
        return shlex.split(s, comments=comments, posix=posix)
    lex = shlex_class(s)(s, posix=posix)
    lex.whitespace_split = True
    if not comments:
        lex.commenters = ""
    return list(lex)
