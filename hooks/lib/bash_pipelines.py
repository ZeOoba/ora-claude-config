"""Pipeline view of a Bash command, and the EVIDENCE-command test, used by
pipe-mask-guard.py (PreToolUse).

WHY A SHARED MODULE. "Which command shapes are evidence (a push, a commit, a
gate, a test run)" and "when is such a command's exit status masked by a pipe"
are one definition that a second consumer (a PostToolUse landing check, planned
as a follow-up) must be able to reuse verbatim rather than re-derive.

THE MASKING RULE. Bash (no pipefail; Claude's Bash tool does not set it)
reports the exit status of the LAST stage of a pipeline. So an evidence command
in ANY non-last stage has its status discarded, whatever follows it --
`| tail`, `| grep`, `| tee log`, `| cat` alike. rules.md s26.

FAILURE DIRECTION. Every parse problem returns "no evidence pipe found". The
pre hook then leaves the command untouched (status quo). A false negative costs what we had before this module; a false
positive costs one harmless `set -o pipefail;` prefix. Never the reverse.

KNOWN FALSE NEGATIVES (accepted; status quo for these shapes):
  * a subshell or group piped as a unit: `(git push) | tail`
  * a pipe operator glued to other punctuation without spaces: `)|`
  * command substitution: `x=$(git push | tail)`

Stdlib only. ASCII-only.
"""
import os
import re
import shlex

try:
    from linear_shlex import shlex_class
except Exception:  # noqa: BLE001 -- degrade to stdlib (correct, just quadratic)
    def shlex_class(text):
        return shlex.shlex

PIPEFAIL_PREFIX = "set -o pipefail; "

# "\n" is a punctuation char so that a bare newline ends a statement exactly as
# `;` does: with whitespace_split on, a newline in `whitespace` would be glued
# into the neighbouring words instead (`x\ngit`).
_PUNCT_CHARS = "();<>|&\n"
_PUNCT = set(_PUNCT_CHARS)
_PIPES = {"|", "|&"}
_BREAKS = {";", "&&", "||", "&", "\n", "(", ")", ";;", ";&", ";;&"}

_ENV_ASSIGN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
_WRAPPERS = {"time", "command", "builtin", "exec", "nohup", "env"}
_TIMEOUT_OPTS_WITH_ARG = {"-k", "-s", "--kill-after", "--signal"}
# A run that only LISTS or DESCRIBES (pytest --collect-only, tsc --version ...)
# produces no pass/fail evidence worth protecting.
_LOOK_FLAGS = {"--collect-only", "--co", "--listTests", "--list-tests", "--help",
               "-h", "--version", "-V"}
_GH_GLOBAL_OPTS_WITH_ARG = {"-R", "--repo"}

GIT_EVIDENCE_SUBCOMMANDS = {"push", "commit", "merge", "rebase", "pull",
                            "cherry-pick"}
# git global options that consume the NEXT word.
_GIT_OPTS_WITH_ARG = {"-C", "-c", "--git-dir", "--work-tree", "--namespace",
                      "--exec-path", "--super-prefix", "--config-env"}

_NPM_LIKE = {"npm", "pnpm", "yarn", "bun"}
_NPM_SCRIPT = re.compile(r"^(gate|verify|test|typecheck|type-check|lint|check|ci)"
                         r"(\b|[:_-])", re.IGNORECASE)
_DIRECT_TOOLS = {"pytest", "py.test", "vitest", "jest", "tsc", "playwright"}
_NPX_LIKE = {"npx", "bunx", "pnpx"}
_INTERPRETERS = {"python", "python3", "py", "node", "tsx", "ts-node", "deno"}
EVIDENCE_SCRIPT = re.compile(
    r"^(git-prepush-.*|verify-push|safe-push|preflight-shared-checkout|"
    r"check-refute-required|repo_first_check|test[-_].*|.*[-_]test|.*\.test)"
    r"\.(py|ts|js|mjs|cjs)$", re.IGNORECASE)


def _base(word):
    """`C:/x/python.exe` -> `python`; `GH.EXE` -> `gh`."""
    b = os.path.basename(word.replace("\\", "/")).lower()
    for ext in (".exe", ".cmd", ".bat"):
        if b.endswith(ext):
            b = b[:-len(ext)]
    return b


def _classify(tok):
    if tok in _PIPES:
        return "pipe"
    if tok in _BREAKS:
        return "break"
    if tok and set(tok) <= _PUNCT:
        if any(s in tok for s in ("||", "&&", ";", "(", ")", "\n")):
            return "break"
        if "|" in tok and ">|" not in tok:
            return "pipe"
        return "redir"
    return "word"


class Pipe(object):
    """One pipeline: `stages` (a list of word lists) and `term`, the statement
    separator token that ended it (`;`, `&&`, `||`, `&`, newline, a token
    containing `(`/`)`), or None at the end of the command."""
    __slots__ = ("stages", "term")

    def __init__(self, stages, term):
        self.stages = stages
        self.term = term


OPEN = "("    # scope markers yielded by items(): a subshell opens / closes
CLOSE = ")"


def items(command):
    """The command as an ordered list of Pipe objects and OPEN / CLOSE scope
    markers (a `(` or `)` in the source). Empty pipelines are dropped. None when
    the command cannot be tokenized. pipelines() is the marker-free view."""
    if not isinstance(command, str) or not command.strip():
        return None
    try:
        lex = shlex_class(command)(command, posix=True,
                                   punctuation_chars=_PUNCT_CHARS)
        lex.whitespace = " \t\r"
        lex.whitespace_split = True
        tokens = list(lex)
    except Exception:  # noqa: BLE001 -- unbalanced quotes, heredoc prose, ...
        return None
    out, pipe, stage = [], [], []
    skip_target = False

    def flush(term):
        pipe.append(stage[:])
        stages = [s for s in pipe if s]
        if stages:
            out.append(Pipe(stages, term))
        del pipe[:]
        del stage[:]

    for tok in tokens:
        kind = _classify(tok)
        if kind == "redir":
            # `2>&1` arrives as '2', '>&', '1' and `> out.txt` as '>', 'out.txt':
            # neither the fd number nor the target is an argument of the
            # command (a stray '2' / '1' would read as extra git refspecs).
            if stage and stage[-1].isdigit():
                stage.pop()
            skip_target = True
            continue
        if kind == "word" and skip_target:
            skip_target = False
            continue
        skip_target = False
        if kind == "word":
            stage.append(tok)
        elif kind == "pipe":
            pipe.append(stage[:])
            del stage[:]
        elif kind == "break":
            flush(tok)
            for ch in tok:
                if ch == "(":
                    out.append(OPEN)
                elif ch == ")":
                    out.append(CLOSE)
    flush(None)
    return out


def pipelines(command):
    """[[stage_words, ...], ...] -- one entry per pipeline, one list of words per
    stage. Redirection operators, the fd number glued before one and the
    word after one are dropped. None when the command cannot be tokenized."""
    its = items(command)
    if its is None:
        return None
    return [it.stages for it in its if isinstance(it, Pipe)]


_REWRITE_MIDDLE = {"tee", "cat"}


def rewrite_shape(command):
    """The single pipeline a `set -o pipefail;` prefix may safely be applied to,
    or None. The prefix is command-wide, so it is only safe when the command is
    ONE statement: a lone pipeline, optionally behind pure `cd <dir> &&` hops
    (pipefail does not change cd's status). Anything else -- `;`, `||`, `&`,
    several lines, a subshell -- is left alone, because pipefail would also
    flip the exit status of the other statements' pipes (`git log | head -1`
    dies of SIGPIPE, `grep | tail` reports grep's no-match)."""
    its = items(command)
    if not its or any(not isinstance(it, Pipe) for it in its):
        return None
    for hop in its[:-1]:
        if hop.term != "&&" or len(hop.stages) != 1:
            return None
        w = command_words(hop.stages[0])
        if not w or w[0] != "cd":
            return None
    last = its[-1]
    if last.term not in (None, ";", "\n"):
        return None
    return last.stages


_QUIT_ALWAYS = {"head", "read", "less", "more"}
_GREPS = {"grep", "egrep", "fgrep", "rg", "ag"}
# GNU grep accepts any unique abbreviation of a long option (`--max=1`, `--qui`).
_GREP_LONG_EARLY = ("--qui", "--sil", "--max", "--files-with")
_GREP_LONG_PREDICATE = ("--qui", "--sil", "--files-with")
_GREP_SHORT_PREDICATE = set("qlL")
_SED_QUIT = re.compile(r"(?:^|[;{}\s/\d$!IM])[qQ]\d*\s*(?:$|[;}])")
_SED_E_ATTACHED = re.compile(r"^(?:-[a-zA-Z]*e|--expression=)(.+)$")


PREDICATE = "predicate"   # grep -q/-l/-L: answers a yes/no, pipefail INVERTS it
LIMIT = "limit"           # head -N, sed q, grep -m, read ...: cuts the output short


def early_exit_kind(stage):
    """How this stage can stop reading before EOF, or None when it reads to EOF.
    PREDICATE (grep -q/-l/-L): `cmd | grep -q x` inverts to 1 under pipefail
    when cmd fails, whatever cmd is. LIMIT (head, grep -m, sed '...q', read,
    less, more, awk 'exit'): upstream dies of SIGPIPE only if it is still
    writing, so a CHATTY command reports rc 120/141 when it passed, while a
    short-output command finishes first and keeps its real status. Conservative:
    a false positive only means no rewrite (status quo)."""
    w = command_words(stage)
    if not w:
        return None
    name, args = _base(w[0]), w[1:]
    if name in _QUIT_ALWAYS:
        return LIMIT
    if name in _GREPS:
        kind = None
        for a in args:
            if a == "--":
                break
            if a.startswith("--"):
                if a.startswith(_GREP_LONG_EARLY):
                    if a.startswith(_GREP_LONG_PREDICATE):
                        return PREDICATE
                    kind = LIMIT
            elif a.startswith("-") and len(a) > 1:
                letters = set(a[1:])
                if _GREP_SHORT_PREDICATE & letters:
                    return PREDICATE
                if "m" in letters:
                    kind = LIMIT
        return kind
    if name == "sed":
        for a in args:
            m = _SED_E_ATTACHED.match(a)  # `-e1q`, `--expression=1q`
            if _SED_QUIT.search(m.group(1) if m else a) and (m or not a.startswith("-")):
                return LIMIT
        return None
    if name in ("awk", "gawk", "mawk"):
        return LIMIT if any(re.search(r"\bexit\b", a) for a in args) else None
    return None


def quits_early(stage):
    """True when this stage can stop reading before EOF (see early_exit_kind)."""
    return early_exit_kind(stage) is not None


def short_output(label):
    """True for evidence kinds that print a few lines and finish before a
    limiter quits: git push/commit/merge/..., `gh pr merge`. Their failure is the
    one a bare pipe masks (a rejected push reported as landed), so a limiter
    after them must not switch the pipefail rewrite off."""
    return label.startswith("git ") or label == "gh pr merge"


def pipefail_targets(command):
    """Labels of the evidence commands a pipefail rewrite would protect, or []
    when the command is not eligible: single-statement shape (rewrite_shape),
    every non-last stage is an evidence command, `tee` or `cat`, AND the last
    stage does not defeat the rewrite: a PREDICATE consumer (grep -q/-l/-L)
    always does; a LIMIT consumer (head, sed q, grep -m ...) does only when no
    evidence stage is short-output (git push/commit/merge, gh pr merge)."""
    stages = rewrite_shape(command)
    if not stages or len(stages) < 2:
        return []
    kind = early_exit_kind(stages[-1])
    if kind == PREDICATE:
        return []
    found = []
    for stage in stages[:-1]:
        k = evidence_kind(stage)
        if k:
            found.append(k)
            continue
        w = command_words(stage)
        if not w or _base(w[0]) not in _REWRITE_MIDDLE:
            return []
    if kind == LIMIT and not any(short_output(k) for k in found):
        return []
    return found


def command_words(stage):
    """The stage's words from the command name on: leading NAME=value
    assignments and transparent wrappers (`time`, `env`, `timeout 60`) skipped."""
    i, n = 0, len(stage)
    while i < n:
        w = stage[i]
        if _ENV_ASSIGN.match(w):
            i += 1
        elif _base(w) in _WRAPPERS:
            i += 1
        elif _base(w) == "timeout":
            i += 1
            while i < n and stage[i].startswith("-"):
                # `-k 5` / `-s TERM` (and long forms without `=`) take a value
                i += 2 if stage[i] in _TIMEOUT_OPTS_WITH_ARG else 1
            i += 1  # the duration
        else:
            break
    return stage[i:]


def git_subcommand(words):
    """(subcommand, args_after_it, dash_C_dir) for a `git ...` word list, else
    (None, [], None)."""
    if not words or _base(words[0]) != "git":
        return None, [], None
    i, cdir = 1, None
    while i < len(words):
        w = words[i]
        if w in _GIT_OPTS_WITH_ARG:
            if w == "-C" and i + 1 < len(words):
                cdir = words[i + 1]
            i += 2
            continue
        if w.startswith("-"):
            i += 1
            continue
        return w, words[i + 1:], cdir
    return None, [], cdir


_INTERP_OPTS_WITH_ARG = {"-X", "-W", "-r", "--require", "--loader", "--import"}


def _script_arg(args):
    i = 0
    while i < len(args):
        a = args[i]
        if a == "-c" or a == "-e" or a == "--eval":
            return None  # inline code, not a script file
        if a in _INTERP_OPTS_WITH_ARG:
            i += 2
            continue
        if a.startswith("-"):
            i += 1
            continue
        return a
    return None


def gh_pr_merge_args(words):
    """Args after `pr merge` for a `gh [-R o/r] pr merge ...` word list (global
    -R/--repo may precede `pr`), else None. Second value: the global repo."""
    if not words or _base(words[0]) != "gh":
        return None, None
    i, repo = 1, None
    while i < len(words):
        w = words[i]
        if w in _GH_GLOBAL_OPTS_WITH_ARG and i + 1 < len(words):
            repo = words[i + 1]
            i += 2
        elif w.startswith("--repo="):
            repo = w.split("=", 1)[1]
            i += 1
        else:
            break
    if words[i:i + 2] == ["pr", "merge"]:
        return words[i + 2:], repo
    return None, None


def evidence_kind(stage):
    """A short label ("git push", "npm run gate:ci", "pytest", ...) when the
    stage runs an evidence command, else None."""
    w = command_words(stage)
    if not w:
        return None
    if any(a in _LOOK_FLAGS for a in w[1:]):
        return None
    b = _base(w[0])
    if b == "git":
        sub, _args, _c = git_subcommand(w)
        return ("git " + sub) if sub in GIT_EVIDENCE_SUBCOMMANDS else None
    if b == "gh":
        return "gh pr merge" if gh_pr_merge_args(w)[0] is not None else None
    if b == "uv":
        rest = [x for x in w[1:] if not x.startswith("-")]
        if rest and rest[0] == "run" and len(rest) > 1:
            return evidence_kind(rest[1:])
        return None
    if b == "make":
        targets = [x for x in w[1:] if not x.startswith("-") and "=" not in x]
        for t in targets:
            if _NPM_SCRIPT.match(t):
                return "make " + t
        return None
    if b in _DIRECT_TOOLS:
        return b
    if b in _NPM_LIKE:
        rest = [x for x in w[1:] if not x.startswith("-")]
        if not rest:
            return None
        if rest[0] in ("test", "t"):
            return b + " test"
        if rest[0] in ("run", "run-script") and len(rest) > 1 \
                and _NPM_SCRIPT.match(rest[1]):
            return "%s run %s" % (b, rest[1])
        if b in ("yarn", "pnpm", "bun") and _NPM_SCRIPT.match(rest[0]):
            return "%s %s" % (b, rest[0])
        if b == "pnpm" and rest[0] == "exec" and len(rest) > 1:
            return evidence_kind(rest[1:])
        return None
    if b in _NPX_LIKE:
        rest = [x for x in w[1:] if not x.startswith("-")]
        return evidence_kind(rest) if rest else None
    if b in _INTERPRETERS or re.match(r"^python3?(\.\d+)?$", b):
        args = w[1:]
        if "-m" in args:
            i = args.index("-m")
            mod = args[i + 1] if i + 1 < len(args) else ""
            return ("python -m " + mod) if mod in ("pytest", "unittest") else None
        script = _script_arg(args)
        if script and EVIDENCE_SCRIPT.match(os.path.basename(script.replace("\\", "/"))):
            return os.path.basename(script.replace("\\", "/"))
        return None
    return None


def masked_evidence(command):
    """Labels of evidence commands sitting in a NON-LAST pipeline stage (their
    exit status is discarded). [] when none, or when the command cannot be
    parsed."""
    found = []
    for pipe in pipelines(command) or []:
        for stage in pipe[:-1]:
            k = evidence_kind(stage)
            if k:
                found.append(k)
    return found


def evidence_stages(command):
    """Every evidence stage in the command, masked or not, as
    (kind, command_words) in order."""
    found = []
    for pipe in pipelines(command) or []:
        for stage in pipe:
            k = evidence_kind(stage)
            if k:
                found.append((k, command_words(stage)))
    return found


_SET_PIPEFAIL = re.compile(r"\bset\s+[^;&|\n]*pipefail|\bshopt\s+-s\s+[^;&|\n]*pipefail")


_PIPESTATUS_READ = re.compile(r"\$\{?PIPESTATUS")


def reads_pipestatus(command):
    """True when a real shell word reads `$PIPESTATUS` / `${PIPESTATUS[..]}`.
    The bare word in a commit message does not count; only a command that cannot
    be tokenized falls back to the raw substring."""
    pipes = pipelines(command)
    if pipes is None:
        return "PIPESTATUS" in command
    return any(_PIPESTATUS_READ.search(w)
               for pipe in pipes for stage in pipe for w in stage)


def has_pipefail(command):
    """True when the command itself enables pipefail (`set -o pipefail`,
    `set -eo pipefail`, `shopt -s pipefail`) BEFORE its first masked evidence
    pipeline, or reads PIPESTATUS. The bare word in a commit message or a path
    does not count: real shell words are inspected, and only a command that
    cannot be tokenized falls back to the raw-text regex."""
    if reads_pipestatus(command):
        return True
    pipes = pipelines(command)
    if pipes is None:
        return bool(_SET_PIPEFAIL.search(command))
    masked_at = None
    for i, pipe in enumerate(pipes):
        if any(evidence_kind(stage) for stage in pipe[:-1]):
            masked_at = i
            break
    for i, pipe in enumerate(pipes):
        if masked_at is not None and i >= masked_at:
            break  # a setter AFTER the masked pipe does not protect it
        for stage in pipe:
            w = command_words(stage)
            if not w:
                continue
            if w[0] == "set" and "pipefail" in w[1:] and any(
                    a.startswith("-") and "o" in a[1:] for a in w[1:]):
                return True
            if w[0] == "shopt" and "pipefail" in w[1:] and "-s" in w[1:]:
                return True
    return False
