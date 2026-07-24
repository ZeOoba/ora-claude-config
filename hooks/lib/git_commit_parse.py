"""Shared `git commit` command parsing for the ORA commit-time gates.

One tokenizer, one candidate-path resolver, for every PreToolUse(Bash) gate that
has to answer the same two questions before a commit runs:

  1. Does this Bash command actually invoke `git commit` as a SUBCOMMAND?
  2. Which files would that commit capture -- given that PreToolUse fires BEFORE
     the command runs, so a `git add X && git commit` one-liner has staged
     NOTHING yet at hook-fire time?

Consumers:
  - commit-provenance-guard.py  -- blocks a commit that would sweep up another
                                   live session's uncommitted work
  - eos-review-gate.py          -- blocks a blast-radius commit with no
                                   independent review artifact tied to its diff

WHY A SHARED MODULE, NOT A SECOND COPY. This is the same lesson override_tokens.py
records in its own adoption history: ora-autonomy-gate.py and the doctrine gate
carried two inline copies of one security contract, written hours apart by two
sessions, and had already begun to diverge before either was reviewed. Question 2
above is ~150 lines of shell-tokenization and git-state resolution whose FAILURE
MODE IS SILENT: a parser that misses a command shape does not error, it returns an
empty candidate set, and the gate allows. A second copy is a second place for that
silence to appear -- and the copy nobody is currently editing is the one that rots.
So the logic lives here once, and eos-review-gate.py inherits every hard-won fix
listed below rather than re-learning them.

EXTRACTION PROVENANCE (2026-07-24): every function here was lifted VERBATIM from
commit-provenance-guard.py, which retains the full incident history for each in its
own module docstring. Behaviour is deliberately unchanged -- this was a move, not a
rewrite, and hooks/tests/test-commit-provenance-guard.py is the regression proof.
The accumulated fixes now shared by both gates:

  - tokenized subcommand detection, so `git add commit-provenance-guard.py` is not
    mistaken for a commit (substring matching is not enough)
  - `--` pathspec handling that survives a `--` inside a quoted -m message
  - per-LINE tokenization, so a bare newline separates statements like `;` does
  - leading `NAME=value` env-assignment tokens skipped, so `GIT_AUTHOR_NAME=x git
    add foo` is still seen as an add (2026-07-24 REFUTE finding)
  - `git add` counted only when a `git commit` follows it positionally, and counted
    even in multi-commit chains where the add sits between two commits
  - pending-add resolution via pre-add working-tree state (2026-07-24: the missing
    piece behind 4 janitor commits that swept 41 files past the provenance guard)

ACCEPTED GAPS (unchanged from the origin file, documented there in full): git
aliases are invisible; subshells, command substitution, and operators glued to a
token without surrounding whitespace are not parsed; a multi-line heredoc commit
message whose prose starts a line with `git add` can add a spurious candidate.
Threat model throughout is a single-operator cooperative fleet, not an adversarial
boundary.

DIRECTIONAL SAFETY. Every degradation here biases toward FEWER candidates on any
git-query failure. Callers must therefore treat an empty/None candidate set as "no
information", never as "nothing is at stake" -- what that means differs per gate
(provenance guard: allow; review gate: allow, since it can only gate what it can
see).

Stdlib only. ASCII-only. Windows (`python`).
"""
import os
import re
import shlex
import subprocess

from commit_provenance import norm

GIT_C_RE = re.compile(r"""\bgit\b\s+-C\s+(?:"([^"]+)"|'([^']+)'|([^\s&|;]+))""")
CD_RE = re.compile(r"""\bcd\s+(?:"([^"]+)"|'([^']+)'|([^\s&|;]+))\s*&&""")

# git global options that consume the NEXT token as a value (when not given
# as `--opt=value`), so that value must not be mistaken for the subcommand.
GIT_ARG_OPTS_WITH_VALUE = {"-C", "-c", "--git-dir", "--work-tree", "--namespace",
                           "--exec-path"}

SHELL_SEGMENT_OPERATORS = {"&&", "||", ";", "|"}

# A leading `NAME=value` token (env-var-prefixed invocation, e.g.
# `GIT_AUTHOR_NAME=x git add foo`) must not stop `git` from being recognized
# as the segment's actual command.
_ENV_ASSIGN_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")


def _first_group(m):
    return next((g for g in m.groups() if g), None) if m else None


def find_commit_segment(cmd):
    """The arg-list of the LAST `git commit ...` segment in `cmd`, or None if
    there is none. "Last" matches this fleet's one-commit-per-Bash-call
    convention (documented in git_add_segments) -- for a genuine multi-commit
    chain it is the commit actually being gated (PreToolUse fires once per
    Bash call, evaluating the whole string, and a later commit's flags/pathspec
    are the ones in effect for what that call ultimately lands).

    SEGMENT-SCOPED BY CONSTRUCTION (2026-07-24 fix): built on
    tokenize_cmd_segments + _segment_git_subcommand_and_args, the same
    segment-aware machinery git_add_segments already uses -- NOT a whole-string
    shlex.split(). This closes two real bypasses found by independent review of
    eos-review-gate.py, which reuses this module: (1) a trailing chained
    command's own `--` (e.g. `git commit -m x && git log -1 -- hooks/`) was
    previously read as the COMMIT's pathspec, discarding the real staged file
    set entirely; (2) `--dry-run` was detected as a raw substring of the WHOLE
    command, so a commit MESSAGE merely mentioning "--dry-run" (plausible in
    this very hooks/ repo) silently zeroed out gating for a real, non-dry-run
    commit. Both PoCs reproduced against the pre-fix code."""
    result = None
    for seg in tokenize_cmd_segments(cmd):
        parsed = _segment_git_subcommand_and_args(seg)
        if parsed and parsed[0] == "commit":
            result = parsed[1]
    return result


def is_git_commit(cmd):
    """True iff `cmd` invokes git with `commit` as the SUBCOMMAND (tokenized,
    not a substring match -- `git add commit-provenance-guard.py` is not a
    commit), and that commit segment does not itself carry `--dry-run`."""
    if not isinstance(cmd, str) or not cmd:
        return False
    args = find_commit_segment(cmd)
    if args is None:
        return False
    return "--dry-run" not in args


def git_lines(repo, args, timeout=5):
    """Stripped non-empty stdout lines of `git -C repo <args>`, or None if the
    command could not be run or exited non-zero."""
    try:
        proc = subprocess.run(["git", "-C", repo] + args,
                              capture_output=True, text=True, timeout=timeout)
    except Exception:
        return None
    if proc.returncode != 0:
        return None
    return [ln.strip() for ln in proc.stdout.splitlines() if ln.strip()]


def repo_root(cmd, cwd):
    """`git -C <p>` wins, else a leading `cd <p> &&`, else the payload cwd."""
    d = _first_group(GIT_C_RE.search(cmd)) or _first_group(CD_RE.search(cmd)) or cwd
    if not d:
        return None
    out = git_lines(d, ["rev-parse", "--show-toplevel"])
    return out[0] if out else None


def has_all_flag(tokens_or_cmd):
    """True for `-a`, `-am`, `--all`. False for `-m` and `--amend`
    (`^-[a-zA-Z]+$` cannot match a double-dash flag).

    Accepts EITHER a pre-tokenized arg list (the commit segment's own args --
    the scoped, correct call site, used by candidate_paths) OR a raw command
    string (re-tokenized here, kept for backward compatibility). Scoping to the
    commit's own segment matters for the same reason find_commit_segment's `--`
    handling does: a flag belonging to a DIFFERENT chained command must not be
    read as this commit's own `-a`."""
    if isinstance(tokens_or_cmd, str):
        try:
            tokens = shlex.split(tokens_or_cmd)
        except Exception:
            tokens = tokens_or_cmd.split()
    else:
        tokens = tokens_or_cmd
    for t in tokens:
        if t == "--all":
            return True
        if re.match(r"^-[a-zA-Z]+$", t) and "a" in t:
            return True
    return False


def _split_segments(tokens):
    """Split a flat token stream into sub-command segments at top-level shell
    control operators. shlex.split does not treat `&&`/`;`/`||`/`|` as syntax --
    when whitespace-separated they simply come through as their own plain tokens."""
    segs = []
    cur = []
    for t in tokens:
        if t in SHELL_SEGMENT_OPERATORS:
            if cur:
                segs.append(cur)
            cur = []
        else:
            cur.append(t)
    if cur:
        segs.append(cur)
    return segs


def tokenize_cmd_segments(cmd):
    """Tokenize `cmd` LINE BY LINE, not as one shlex.split() call, so a bare
    newline (bash's statement separator, same semantics as `;`) also acts as a
    segment boundary. A line that fails to tokenize falls back to a plain
    whitespace split for that line only."""
    segs = []
    for line in cmd.splitlines():
        if not line.strip():
            continue
        try:
            tokens = shlex.split(line)
        except ValueError:
            tokens = line.split()
        segs.extend(_split_segments(tokens))
    return segs


def _segment_git_subcommand_and_args(seg):
    """If `seg` is (after skipping any leading `NAME=value` env-assignment
    tokens) a `git <subcommand> ...` invocation, return
    (subcommand, args-after-subcommand). Else None."""
    if not seg:
        return None
    i = 0
    n = len(seg)
    while i < n and _ENV_ASSIGN_RE.match(seg[i]):
        i += 1
    if i >= n or seg[i] != "git":
        return None
    j = i + 1
    while j < n:
        t = seg[j]
        if t.startswith("-"):
            j += 2 if t in GIT_ARG_OPTS_WITH_VALUE else 1
            continue
        return (t, seg[j + 1:])
    return None


def git_add_segments(cmd):
    """arg-lists for every `git add ...` invocation in `cmd` that has AT LEAST
    ONE `git commit` invocation somewhere after it (positionally, left to right
    across segments -- matches execution order for &&/;/||/newline).

    NOT simply "before the FIRST commit": a multi-commit sequence in one command
    has an add that a "stop at the first commit" rule would drop entirely, even
    though it plainly gets staged for the SECOND commit. Conversely an add with
    NO commit anywhere after it is correctly excluded."""
    segs = tokenize_cmd_segments(cmd)
    parsed = [_segment_git_subcommand_and_args(seg) for seg in segs]
    commit_idx = [i for i, p in enumerate(parsed) if p and p[0] == "commit"]
    if not commit_idx:
        return []
    add_arglists = []
    for i, p in enumerate(parsed):
        if p and p[0] == "add" and any(ci > i for ci in commit_idx):
            add_arglists.append(p[1])
    return add_arglists


def pending_add_paths(repo, cmd):
    """Absolute normcase paths that `git add` invocation(s) PRECEDING a `git
    commit` in the same compound command would stage, resolved WITHOUT ever
    running `git add` -- PreToolUse fires before the real command executes, so at
    hook-fire time the index is still whatever it was before this add. We instead
    query the pre-add working-tree state (git diff / ls-files) that the pending
    add is about to consume.

    `-u`/`--update` is treated as an alias for `-A` here -- it actually stages a
    narrower set, but over-inclusion in a candidate SET can only widen who gets
    flagged, never cause a false allow."""
    add_arglists = git_add_segments(cmd)
    if not add_arglists:
        return set()

    paths = set()
    wants_all = False
    explicit = []
    for args in add_arglists:
        for a in args:
            if a in ("-A", "--all", "--no-ignore-removal", "-u", "--update", "."):
                wants_all = True
            elif a.startswith("-"):
                continue  # unrecognized flag (-v, -f, -p, -N, --dry-run, ...): skip
            else:
                explicit.append(a)

    if wants_all:
        modified = git_lines(repo, ["diff", "--name-only"]) or []
        untracked = git_lines(repo, ["ls-files", "--others", "--exclude-standard"]) or []
        paths |= {norm(os.path.join(repo, p)) for p in modified}
        paths |= {norm(os.path.join(repo, p)) for p in untracked}

    for p in explicit:
        abs_p = os.path.join(repo, p)
        if os.path.isdir(abs_p):
            scoped_mod = git_lines(repo, ["diff", "--name-only", "--", p]) or []
            scoped_unt = git_lines(
                repo, ["ls-files", "--others", "--exclude-standard", "--", p]) or []
            paths |= {norm(os.path.join(repo, x)) for x in scoped_mod}
            paths |= {norm(os.path.join(repo, x)) for x in scoped_unt}
        else:
            paths.add(norm(abs_p))

    return paths


def candidate_paths(repo, cmd):
    """Absolute normcase paths this commit would capture, or None if unknown."""
    commit_args = find_commit_segment(cmd)
    if commit_args is None:
        return None  # not a commit call -- nothing to resolve

    # Explicit `-- <pathspec>` narrows the commit. SCOPED TO THE COMMIT'S OWN
    # SEGMENT (2026-07-24 fix, see find_commit_segment) -- a `--` belonging to
    # a DIFFERENT chained command must not be mistaken for this commit's
    # pathspec. Tokenize rather than regex-search for " -- " within the
    # segment -- a `-- ` sequence inside a quoted `-m` commit message is NOT a
    # standalone `--` token (shlex already kept it as one quoted token).
    if "--" in commit_args:
        idx = commit_args.index("--")
        given = commit_args[idx + 1:]
        return {norm(os.path.join(repo, p)) for p in given if p}

    staged = git_lines(repo, ["diff", "--cached", "--name-only"])
    if staged is None:
        return None
    rel = set(staged)
    if has_all_flag(commit_args):
        tracked = git_lines(repo, ["diff", "--name-only"]) or []
        rel |= set(tracked)
    cands = {norm(os.path.join(repo, p)) for p in rel}
    # A `git add` PRECEDING this commit in the same command hasn't run yet at
    # hook-fire time, so it can't show up in `git diff --cached`.
    cands |= pending_add_paths(repo, cmd)
    return cands
