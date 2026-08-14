"""Fail-closed guard against silent edits to EXISTING lint/format/typecheck config
files in oxford-command-center -- PreToolUse hook. (OI-148)

WHY (2026-08-13, ECC repo intake, ratified by Gabriel). The Engineering OS quality
bar (spec Sec 7 item 2: "Static clean -- typecheck 0, lint 0") has no gate of its
own kind: nothing stops a session from silently loosening eslint.config.js or a
tsconfig.json's strict flags to make that bar pass without actually fixing
anything. Pattern borrowed from the external ECC repo's config-protection.js
(evaluated via external-artifact-intake, see event_log.md 2026-08-13) -- adapted to
this codebase's own override-token contract (hooks/lib/override_tokens.py) rather
than ported verbatim; ECC's implementation is JS and untested against this
codebase's tool-call shapes.

SCOPE (ratified 2026-08-13: oxford-command-center only, not ora-pm or the brain
mirror -- narrower first version, widen later on request):
    eslint.config.js, tsconfig.json, tsconfig.node.json, functions/tsconfig.json,
    vitest.config.ts, .prettierrc.json
relative to C:/Users/Owner/oxford-command-center. Worktree copies under that
root's own .claude/worktrees/** are exempt, mirroring config-write-guard.py's
exemption for ~/.claude worktrees -- isolated-worktree dev is the sanctioned path,
and a worktree copy is inert until merged, at which point ordinary code review
(requesting-code-review / receiving-code-review) is the backstop.

EXISTING-FILE ONLY, FAIL-CLOSED ON STAT ERRORS -- the actual "config-protection.js"
technique, not just its target list: this guards an EXISTING config against being
loosened, not the one-time creation of a new one (that is not the threat model).
os.stat() success -> exists -> gated. FileNotFoundError -> absent -> allowed
(first-time create). Any OTHER OSError (permission denied, a path component that
is not a directory, etc.) -> UNKNOWN -> gated anyway, same fail-closed direction as
the rest of this hook family: a false positive costs a retry, a false negative lets
a quality-bar loophole through unreviewed.

SHELL COVERAGE, honestly stated (same documented ceiling as every shell-text
marker in this codebase, see tool_call_paths.py's shell_may_write docstring):
best-effort text match on a write-shaped shell command naming both the repo
("oxford-command-center") and a protected basename. Value indirection ($var, a
prior `cd` that leaves the repo name out of the command text entirely) is not
resolvable statically -- allow in that case, same honest limit as ora-autonomy-
gate.py and config-write-guard.py.

QUOTE-SPLIT DEFENSE (added after independent review, 2026-08-13): a bare
substring check on the raw command text is defeated by two apostrophes --
`sed -i '...' ts''config.json` is ONE contiguous shell argument (the shell
concatenates adjacent quoted/unquoted fragments with no separator) but does
not contain the literal substring "tsconfig.json". Empirically confirmed
live: this rewrote a real file in a sandbox before the fix. Reuses
config-write-guard.py's _dequote/_decaret/_shell_variants technique (2026-08-05,
same rationale there: a variant can only ADD a hit, never remove one, so this
cannot make a previously-caught command pass). Heredoc bodies are also
stripped before matching, same as config-write-guard.py, so a heredoc that
merely NAMES a config file in its body text (not a real write target) does not
false-block the verification commands (npm run typecheck/lint) this guard
exists to protect.

KNOWN, DOCUMENTED, LOWER-PRIORITY GAPS (independent review, 2026-08-13; not
fixed here -- flagged for a follow-up decision, not silently expanded scope):
  - package.json's own `lint`/`typecheck` script definitions (e.g.
    `--max-warnings 0`) are OUT OF SCOPE -- loosening those achieves the same
    threat model with a smaller, less conspicuous diff than editing the 6
    protected files. Gabriel ratified exactly 6 files; widening to cover
    package.json's script strings needs its own scoping decision (that file
    changes far more often for legitimate reasons).
  - The structured-path worktree exemption (classify_path, below) is
    reachable only if a future protected path is ever added under
    <root>/.claude/worktrees/ itself, which none of the current 6 are --
    today it is defensive, not load-bearing. The SHELL-text worktree
    exemption below (new, this pass) IS load-bearing: it is the only one
    that can actually fire given the current protected-path list, since a
    worktree copy's absolute path always differs from the live root.

EXIT CODES (reference_pretooluse_vs_git_hook_exit_codes.md -- PreToolUse family):
exit 0 = allow; exit 2 + stderr = block. NEVER exit 1 (non-blocking error: the tool
call would PROCEED, silently disabling this gate).

Whole body wrapped, exit 0 on any internal error -- a bug here must never brick a
tool call (same posture as every guard in this family).

TEST SEAMS (env vars -- TEST ONLY, never set in settings.json/scheduled tasks):
  ORA_LINT_CONFIG_GUARD_ROOT, and the lib's ORA_OVERRIDE_SESSIONS_DIR.

Stdlib only. ASCII-only. Windows (`python`).
"""
import json
import os
import re as _re
import sys

HOOKS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HOOKS_DIR, "lib"))

# The token contract is the SHARED one (override_tokens.py) -- do not reinvent.
# Same degrade posture as config-write-guard.py: an ImportError must never
# propagate to exit 1 (non-blocking) or a bare sys.exit(2) at import time
# (would brick every tool call) -- degrade to "no override exists".
try:
    from override_tokens import Tier, describe_token, token_grants  # noqa: E402
    TOKEN_CONTRACT_LOADED = True
except Exception:
    TOKEN_CONTRACT_LOADED = False

    class Tier(object):
        def __init__(self, name, scope, ttl, single_use=False,
                     requires_extra_check=False):
            self.name = name
            self.scope = scope
            self.ttl = ttl
            self.single_use = single_use
            self.requires_extra_check = requires_extra_check

    def token_grants(session_id, tier, extra_check=None):
        return None  # no validator -> no grant, ever

    def describe_token(session_id, tier):
        return ("  <hooks/lib/override_tokens.py could not be imported -- no "
                "override can be honored; fix the module, do not mint a token>\n")

# Tool-call shape knowledge is the shared normalization layer's job -- same
# degrade logic; without it we cannot see write targets, so nothing matches and
# the gate is inert (identical to this hook not existing, never a NEW hole).
try:
    from tool_call_paths import (  # noqa: E402
        is_shell_tool, normalize_text, resolve_path, shell_analysis, write_targets)
    TOOL_PATHS_LOADED = True
except Exception:
    TOOL_PATHS_LOADED = False

LINT_CONFIG_WRITE = Tier("allow-lint-config-write", "lint-config-write", 3600)

DEFAULT_ROOT = r"C:\Users\Owner\oxford-command-center"

PROTECTED_RELATIVE_PATHS = (
    "eslint.config.js",
    "tsconfig.json",
    "tsconfig.node.json",
    "functions/tsconfig.json",
    "vitest.config.ts",
    ".prettierrc.json",
)

PROTECTED_BASENAMES = tuple(sorted(
    {rel.rsplit("/", 1)[-1].lower() for rel in PROTECTED_RELATIVE_PATHS}))

REPO_MARKER = "oxford-command-center"


def guard_root():
    return os.environ.get("ORA_LINT_CONFIG_GUARD_ROOT") or DEFAULT_ROOT


def protected_paths():
    """{resolved absolute path: relative label} for the CURRENT guard_root(),
    computed fresh each call so the ORA_LINT_CONFIG_GUARD_ROOT test seam is
    honored (mirrors config-write-guard.py's guard_root() pattern)."""
    root = guard_root()
    return {resolve_path(os.path.join(root, *rel.split("/"))): rel
            for rel in PROTECTED_RELATIVE_PATHS}


def worktree_root():
    return resolve_path(os.path.join(guard_root(), ".claude", "worktrees"))


def _file_state(path):
    """'exists' | 'absent' | 'unknown' (fail-closed direction).

    PLATFORM NOTE (empirically confirmed, not assumed): on Windows, os.stat()
    through a path whose parent component is not a directory raises
    FileNotFoundError (WinError 3) -- the same exception as a genuinely
    missing file, unlike POSIX's distinct NotADirectoryError. That collapse is
    harmless here: in both cases there is no real config file at the resolved
    path, so 'absent' -> allow is the correct outcome either way. The 'unknown'
    branch still exists for a real non-ENOENT OSError this platform CAN raise
    (e.g. PermissionError from a restrictive ACL) -- fail-closed, not reached
    by ordinary first-time-create."""
    try:
        os.stat(path)
        return "exists"
    except FileNotFoundError:
        return "absent"
    except OSError:
        return "unknown"


def classify_path(raw_path):
    """label if raw_path is a protected, existing-or-unknown-state config file
    outside any worktree copy -- else None."""
    if not isinstance(raw_path, str) or not raw_path:
        return None
    resolved = resolve_path(raw_path)
    wt_root = worktree_root()
    if resolved == wt_root or resolved.startswith(wt_root + os.sep):
        return None  # worktree copy -- exempt, sanctioned dev path
    label = protected_paths().get(resolved)
    if label is None:
        return None
    if _file_state(resolved) == "absent":
        return None  # first-time create -- not the threat model
    return label


# --- quoting/escaping normalization (ported from config-write-guard.py, 2026-08-05
# there / 2026-08-13 here) -- see the module docstring's QUOTE-SPLIT DEFENSE note.
_CARET_ESCAPE_RE = _re.compile(r"\^(.)", _re.DOTALL)
_HEREDOC_RE = _re.compile(
    r"<<-?\s*['\"]?([a-zA-Z0-9_]+)['\"]?[^\n]*\n"  # opening line, through \n
    r".*?\n"                                        # body (non-greedy)
    r"[ \t]*\1(?=[ \t\r\n]|$)",                     # closing delimiter line
    _re.DOTALL,
)


def _strip_heredoc_bodies(text):
    def _blank(m):
        opening_line = m.group(0).split("\n", 1)[0] + "\n"
        return opening_line + " <heredoc-body> \n" + m.group(1)
    return _HEREDOC_RE.sub(_blank, text)


def _decaret(text):
    """cmd.exe caret-escape removal: `^X` -> `X`."""
    return _CARET_ESCAPE_RE.sub(r"\1", text)


def _dequote(text):
    """Drop quote CHARACTERS only, preserving every other character including
    whitespace -- adjacent quoted/unquoted fragments the shell concatenates
    into ONE argument (e.g. ts''config.json) become the contiguous text a
    plain substring check expects, without gluing two genuinely SEPARATE
    arguments together."""
    return text.replace('"', "").replace("'", "")


def _shell_variants(text):
    """Deduped normalization variants of a shell command, each defeating one
    quoting/escaping trick. A variant can only ever ADD a hit, never remove
    one, so this cannot make a previously-caught command pass."""
    variants = []
    for candidate in (text, _dequote(text), _decaret(text),
                      _decaret(_dequote(text))):
        if candidate not in variants:
            variants.append(candidate)
    return variants


def _blank_exempt(text, marker):
    """Blank the ENTIRE whitespace-delimited token containing `marker`, so an
    exempted path (a worktree copy) contributes NOTHING to later marker/
    basename matching -- ported from config-write-guard.py's _blank_exempt,
    2026-08-13 review fix. Unlike an early return on ANY mention of the
    marker anywhere in the command, this only silences the SPECIFIC token
    that names a worktree path; an unrelated write elsewhere in the same
    command (a different argument, a later chained command) still matches."""
    return _re.sub(r"\S*" + _re.escape(marker) + r"\S*", " <exempt> ", text)


def classify_shell_text(command):
    """Protected basename if `command` names both the repo and one of the
    protected files -- else None. Best-effort text match, honest ceiling.

    Worktree exemption (load-bearing on this path, unlike the structured one
    in classify_path -- see the module docstring's KNOWN GAPS note): via
    _blank_exempt, TOKEN-SCOPED, not whole-command -- only the specific
    whitespace-delimited token containing .claude/worktrees is blanked before
    matching, so an unrelated real write elsewhere in the same command still
    blocks (2026-08-13 review fix; an earlier version returned None on ANY
    mention anywhere in the command, silencing the whole thing -- do not
    revert to that shape). Still coarser than the structured resolve_path
    check in classify_path (this cannot confirm the blanked token is a real,
    resolvable worktree path rather than adjacent unrelated text sharing the
    same substring), and a `..`-traversal INSIDE the exempted token can evade
    it (documented shell-text ceiling, same class as value indirection) --
    but it no longer silences text outside that one token, and a worktree
    copy is inert until merged regardless."""
    if not isinstance(command, str):
        return None
    base = normalize_text(command).lower().replace("\\", "/")
    base = _blank_exempt(base, ".claude/worktrees")
    base = _strip_heredoc_bodies(base)
    for variant in _shell_variants(base):
        if REPO_MARKER not in variant:
            continue
        for basename in PROTECTED_BASENAMES:
            if basename in variant:
                return basename
    return None


def _block(label, session_id):
    sys.stderr.write(
        "BLOCKED (lint-config-guard): edit to an existing lint/format/typecheck "
        "config in oxford-command-center -- %s\n"
        "Nothing else enforces that the Engineering OS 'lint 0' / 'typecheck 0' "
        "quality bar is met by actually fixing errors rather than loosening the "
        "config that reports them (OI-148).\n"
        "IF THIS WAS A READ, NOT A WRITE (a verification command whose text merely "
        "NAMES a protected file, e.g. `npx tsc -p tsconfig.json`): do NOT mint a "
        "token. The shell-text matcher is breadth-over-precision by design (see "
        "the module docstring) -- use the Read/Grep/Glob tools instead, or drop "
        "the repo/file name from the shell command text. Minting a token to "
        "satisfy a read grants 60 minutes of multi-use WRITE access to every "
        "protected config, strictly worse than the read you wanted.\n"
        "If this is a genuine, reviewed config change -- not a workaround to pass "
        "a failing gate -- write this override token and retry:\n%s"
        % (label, describe_token(session_id, LINT_CONFIG_WRITE))
    )
    sys.exit(2)


def main():
    payload = json.loads(sys.stdin.buffer.read().decode("utf-8"))
    if not isinstance(payload, dict):
        return
    tool_name = payload.get("tool_name") or ""
    tool_input = payload.get("tool_input")
    session_id = payload.get("session_id")
    if not isinstance(session_id, str):
        session_id = ""
    if not isinstance(tool_input, dict) or not TOOL_PATHS_LOADED:
        return  # nothing inspectable / no shape knowledge -> status quo, allow

    hit_label = None
    for target in write_targets(tool_name, tool_input):
        cls = classify_path(target.raw_path)
        if cls:
            hit_label = cls
            break

    if hit_label is None and is_shell_tool(tool_name):
        analysis = shell_analysis(tool_name, tool_input)
        if analysis is not None and analysis.may_write:
            hit_label = classify_shell_text(analysis.command)

    if hit_label is None:
        return

    if token_grants(session_id, LINT_CONFIG_WRITE) is None:
        _block(hit_label, session_id)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise  # a real block (exit 2) must propagate
    except Exception:
        pass  # FAIL OPEN: an internal bug must never block a tool call
