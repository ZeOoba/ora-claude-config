"""MEMORY.md orphan-index-link COMMIT-time guard -- PreToolUse hook for Bash.

THE DEFECT THIS PREVENTS. memory-integrity-probe.py reports "orphan index link IN GIT":
HEAD's MEMORY.md links a memory file that HEAD's TREE does not contain, so anyone cloning
the repo gets a broken pointer. It fired with 5 such links on 2026-07-24 (probe exit 1),
and the root cause is structural, not careless: MEMORY.md is a single shared file that many
sessions append to, while each session's memory BODY file is its own new untracked file.
Whoever commits MEMORY.md sweeps up everyone's index lines -- including lines whose bodies
that committer never had staged. See reference_event_log_uncommitted_backlog.md (no single
committer) and shared-checkout-cofile-patch-hazard.md.

WHY COMMIT TIME AND NOT WRITE TIME. At write time the body file is sitting right there on
disk, so a write-time check sees nothing wrong -- the orphan only comes into existence when
MEMORY.md is committed WITHOUT the body. hooks/memory-index-guard.py already owns the
write-time rule (the 150-char hook cap) and is deliberately left alone here; this guard owns
the distinct commit-time rule. Same file, two different failure modes, two separate guards.

WHAT IT CHECKS. When a Bash command is a `git commit` that would include MEMORY.md, every
relative markdown link in the version of MEMORY.md that git is about to commit must resolve
to a path that is either already in HEAD or staged in this same commit. If any does not, the
commit is denied with the exact `git add` line that fixes it.

Reads the version git will ACTUALLY commit:
  * `git commit -- <pathspec>` re-reads the WORKING TREE (see
    feedback_pathspec_commit_discards_index_splice.md), so we read the working tree.
  * a plain staged `git commit` commits the INDEX, so we read `git show :<path>`.
Getting this wrong in the lenient direction only ever means missing a block, never a false
one -- but it is cheap to get right, so we do.

DELIBERATELY NOT AN AUTO-COMMITTER. The obvious framing is "auto-commit the body when
MEMORY.md is written." That would be actively dangerous in this checkout: HEAD moved six
times during the 2026-07-24 session from concurrent sessions, and an unattended `git add`
would sweep another session's in-flight work into a commit it never reviewed -- the exact
hazard recorded in the backlog-janitor note. Blocking is safe; committing on someone's
behalf is not.

SAFETY INVARIANT: the entire body is wrapped in try/except and exits 0 (ALLOW) on ANY error
-- unparseable stdin, no git, detached repo, unreadable file, weird command shape. A bug here
must never block a commit and must never lock Gabriel out of his own memory index
(cf. feedback_confidentiality_guard_selfdeadlock.md, where a fail-CLOSED guard bricked
Write/Edit/Bash machine-wide). Fail-open is also the ratified default for cross-session
coordination guards -- feedback_fail_open_over_mutex_for_fleet_gates.md.

Stdlib only. ASCII-only. Windows.
"""

import json
import os
import re
import shlex
import subprocess
import sys

# Linear-time shlex (see hooks/lib/linear_shlex.py): stdlib shlex is O(len^2) on ONE long
# token, and this guard tokenizes the WHOLE command whenever its text contains "commit"
# (not only `git commit`). Imported in its own try/except so a partial deploy -- this guard
# landing before the lib on the shared checkout -- degrades to stdlib shlex, never inert.
_LIB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib")
if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)
try:
    from linear_shlex import shlex_class as _shlex_class
except Exception:
    def _shlex_class(text):
        return shlex.shlex

# SHARED SAFE SEGMENTATION (2026-07-24, two rounds). Round A (local review): every
# raw-string `re.split(r"(?:&&|\|\||;|\|)", cmd)` in this file (three call sites) was
# quote-BLIND. A crafted quoted argument with an embedded ';'/'&&'/'|' could TEAR across
# what the split treats as two "segments", and each torn fragment could independently
# happen to shlex-parse cleanly alone (unbalanced quotes canceling out coincidentally
# across the tear) -- fabricating a fake segment/subcommand. Live-verified: `git -c
# core.foo="a;git -C <decoy-repo> commit -m y;b" commit -m "real msg"` fabricated a
# decoy `git -C <decoy-repo> commit` segment, trusted over the REAL commit later in the
# string; the decoy repo lacked a memory/ directory, so the guard ALLOWED while real git
# genuinely landed the orphan.
#
# Round B (a SECOND local review, on Round A's own fix): a first fix tokenized PER LINE
# (`for line in cmd.splitlines(): shlex.split(line)`) specifically to treat a bare
# newline as a statement separator, the same semantics as ';'. That pre-split throws
# away the very quote-context shlex needs before it ever sees a newline -- an OPEN
# double-quote spanning multiple lines (a heredoc-style `-m "$(cat <<'EOF' ... EOF)"`,
# THIS ENVIRONMENT'S OWN standard multi-line commit-message idiom) has its embedded
# newlines torn apart into separate "lines" fed to shlex ONE AT A TIME, each missing the
# other half of the still-open quote -- so `shlex.split` on the FIRST fragment alone
# either raises (undoing the whole command, per-command None -> guard fully disabled)
# or, worse, silently tokenizes something unintended. Live-verified: the exact heredoc
# idiom above got ALLOW while real bash committed the orphan for real. A second, SEPARATE
# defect in that same fix: `shlex.split()` in default whitespace-token mode does not
# treat `&`, `|`, `;` as metacharacters at all -- `"MEMORY.md&&git"` (no space around the
# operator, ordinary shell style) tokenizes as ONE token, so `&&` glued to a neighboring
# word was invisible to the operator scan. Live-verified regression vs. even the
# PRE-Round-A code: `git add "path/MEMORY.md"&&git commit -m y` got ALLOW.
#
# THE FIX: tokenize the WHOLE command ONCE with `shlex.shlex(cmd, posix=True,
# punctuation_chars=True)` (NOT `shlex.split`, and NOT pre-split by line) --
# `punctuation_chars=True` makes `&`/`|`/`;` real metacharacters exactly like a POSIX
# shell (so `&&`/`||`/`;`/`|` are recognized as their own tokens REGARDLESS of adjacent
# whitespace, verified: `'x&&y'` -> `['x','&&','y']`), while remaining fully quote-aware
# (an operator INSIDE a quoted argument, or a `;` embedded in a quoted `-c key=value`,
# stays part of that ONE token -- verified against both the Round A and Round B attack
# strings). Because the WHOLE command is tokenized as one string, an open quote
# correctly spans embedded newlines (the heredoc case collapses to ONE token, matching
# real bash semantics for what a double-quoted argument is -- no heredoc-specific logic
# needed, just not destroying the quote context by pre-splitting).
#
# A genuine BARE newline between two REAL, separate statements (no ';'/'&&' at all --
# valid bash, and a real bypass path: `git add MEMORY.md\ngit commit -m x` would
# otherwise get silently swallowed into `add`'s own argument list, and _is_git_commit
# would never see a `commit` subcommand at all) is distinguished from a newline living
# INSIDE a token's own text via the shlex.shlex `lineno` counter: for each token, if
# `(lineno_after - lineno_before) > tok.count("\n")`, more newlines were crossed than
# the token's own text accounts for -- a real separator newline sits immediately after
# it. Verified against: two/three bare-newline-separated statements (correctly split),
# a newline INSIDE a quoted arg at any position, and the heredoc case (both correctly
# stay as one token/segment, no false split).
# Round C (a THIRD local review, on Round B's own fix). Round B correctly closed the
# heredoc/glued-operator regressions using `shlex.shlex(cmd, posix=True,
# punctuation_chars=True)` over the WHOLE command, but its bare-newline detection
# (comparing `lex.lineno` before/after each returned token) turned out to be
# UNRELIABLE: whether a newline crossed while skipping to the NEXT token gets
# attributed to the token that just finished or the token about to start depends on
# WHICH internal shlex code path consumed it -- and a `#` comment uses a DIFFERENT path
# than plain whitespace-skipping. Traced live: `echo hi # comment\ngit commit -m x`
# split at the wrong token boundary entirely (`'git'` ended up glued to segment 1
# instead of starting segment 2) -- not merely imprecise, actively wrong. Separately,
# self-caught while stress-testing: comparing to the WRONG reference also let ONE
# `_SEGMENT_OPERATORS`-exact-match check silently pass through a token like `'\n\n\n'`
# (shlex groups REPEATED punctuation characters of the same kind into ONE token, same
# as it correctly groups `&&`/`||`) as ordinary content instead of a separator --
# `git add MEMORY.md\n\n\ngit commit -m x` (blank lines between statements, an entirely
# ordinary thing to paste) would have reopened the exact same swallowed-add bypass.
#
# THE FIX: stop inferring newline-crossing after the fact. Make `\n` a REAL punctuation
# character itself (added to `punctuation_chars`, removed from `whitespace` so that
# classification doesn't silently win instead) -- shlex's OWN quote-tracking then
# handles it exactly like `&`/`|`/`;` already are: a bare newline outside any quote
# becomes its own token (grouped with adjacent bare newlines, same grouping rule as the
# other operators -- closing the blank-line gap too, since the segment check now tests
# whether a token consists ENTIRELY of operator characters, not an exact string match
# against a fixed short list), while one living inside a quoted argument (a heredoc
# body, a multi-line message) stays part of that ONE token, unaffected. This ALSO
# requires disabling shlex's built-in `#`-comment handling (`lex.commenters = ""`):
# by default a comment's own terminating newline is consumed internally as part of
# discarding the comment, before punctuation-detection ever sees it -- so a real
# `git commit` on the line AFTER a comment was silently swallowed into the PRECEDING
# segment. With comments disabled, `#...text` simply becomes ordinary (harmless, inert)
# extra tokens attached to whatever segment it's in, and the newline that follows is
# free to be recognized as a real separator like any other -- the safe direction: more
# noise in a segment's own token list, never a hidden/merged segment.
#
# Round D (a FOURTH local review, on Round C's own fix). `punctuation_chars` also
# inherited `();<>` from the default set (harmless-seeming -- this file never treats
# them as separators). But shlex groups ANY run of adjacent punctuation_chars
# characters into ONE token regardless of which specific characters they are (the same
# rule that correctly groups `&&`) -- so a real separator glued directly to one of these
# inert characters with no whitespace (`;(`, `&(`, `);`) merged into ONE token like
# `';('`. A check requiring EVERY character in a token to be a real operator
# (`_SEGMENT_OP_CHARS`) fails on that mixed token, silently treating it as ordinary
# content -- hiding a real `git commit` behind an earlier subcommand. Live-verified
# full, silent bypass (zero deny output): `git add MEMORY.md;(git commit -m x)` --
# an ordinary subshell idiom, not an exotic construct. The FIRST attempted fix for
# THIS (dropping `();<>` from punctuation_chars entirely) traded this for a WORSE,
# related bug: without them as their own punctuation tokens, `(` glues directly onto
# the next word (`(git` instead of `(` + `git`), so `_segment_git_parts`'s exact
# `token == "git"` match no longer recognizes the git executable at all -- same
# bypass, different mechanism, self-caught by tracing through BEFORE it was ever
# ported into this file. Correct fix: KEEP `();<>` in `punctuation_chars` (so they
# stay their OWN clean tokens, never glued to "git"), and instead broaden the
# separator test -- a token counts as a real separator if it is composed ENTIRELY of
# punctuation_chars characters AND contains at least one character FROM the actual
# operator set. A merged blob like `';('` then correctly splits (it is pure
# punctuation and contains a real `;`); a purely-inert merged blob like `'()'` does
# not (pure punctuation, but no real operator character present).
_FULL_PUNCTUATION_CHARS = frozenset("();<>|&\n")
_SEGMENT_OP_CHARS = frozenset("&|;\n")


def _tokenize_segments(cmd):
    """`cmd` as a list of segments, each a token list (shlex-tokenized, quote-aware,
    metacharacter-aware regardless of whitespace, correctly split on a genuine bare
    newline between two statements). Returns None if `cmd` cannot be tokenized at all
    (unbalanced quoting) -- see the module comment above for the FOUR live-verified
    bypasses this closes and why each of the three prior, simpler attempts failed."""
    lex = _shlex_class(cmd)(cmd, posix=True,
                            punctuation_chars="".join(_FULL_PUNCTUATION_CHARS))
    lex.whitespace_split = True
    lex.whitespace = lex.whitespace.replace("\n", "")
    lex.commenters = ""
    try:
        toks = list(lex)
    except ValueError:
        return None
    segs = []
    cur = []
    for tok in toks:
        is_pure_punctuation = tok and all(c in _FULL_PUNCTUATION_CHARS for c in tok)
        is_separator = is_pure_punctuation and any(c in _SEGMENT_OP_CHARS for c in tok)
        if is_separator:
            if cur:
                segs.append(cur)
            cur = []
        else:
            cur.append(tok)
    if cur:
        segs.append(cur)
    return segs


# `git -C <path>` / a leading `cd <path> &&` inside the command being judged, which the
# ACTUAL command will honor for its own repo resolution. Conceptually the same shape as
# commit-provenance-guard.py / eos-review-gate.py's shared hooks/lib/git_commit_parse.py
# (repo_root()) -- but INLINED, not imported: at the time of this fix, that module is
# only committed on the still-in-progress feat/eos-review-gate branch, not yet on main
# (verified: `git show main:hooks/lib/git_commit_parse.py` fails -- what a plain
# filesystem read finds in the live checkout is another session's UNCOMMITTED staged
# merge of that branch, not landed history). Taking a hard import dependency on an
# unmerged, still-changing branch would trade one fragility for a worse one. This is a
# deliberately small, self-contained port of just the resolution algorithm this guard
# needs -- not the whole shared library -- with the same directional-safety property
# (fewer/no candidates on any resolution failure, never a false exclude).
#
# NOT a raw regex over the whole command string (an earlier version of this function
# was exactly that, and was self-caught before shipping): a decoy `cd /x &&` or
# `git -C /x` sitting inside an ORDINARY quoted commit message -- the same failure
# class already closed twice elsewhere in this file (_commit_pathspec, the removed
# _has_pathspec) -- resolved to a nonexistent path, which made the guard fail open and
# silently ALLOW a commit that genuinely staged an orphaned MEMORY.md. Verified live
# before this fix: `git commit -m "cd /nonexistent-decoy-path &&"` and `git commit -m
# "run: git -C /nonexistent-decoy commit"` both got ALLOW. Quote-aware + segment-scoped
# detection below closes both.


def _global_dash_c(toks):
    """The value of a GLOBAL `git -C <path>` override on this segment's ALREADY
    tokenized (via _tokenize_segments) token list -- i.e. `-C` appearing BEFORE the
    subcommand -- or None. Deliberately stops scanning at the subcommand token: `git
    commit -C <ref>` is a DIFFERENT, real git-commit flag (reuse another commit's
    message -- already in _COMMIT_VALUE_OPTS) with nothing to do with directories, and
    must never be misread as this override."""
    gi = None
    for i, t in enumerate(toks):
        base = t.rsplit("/", 1)[-1].rsplit("\\", 1)[-1].lower()
        if base in ("git", "git.exe"):
            gi = i
            break
    if gi is None:
        return None
    i = gi + 1
    dash_c = None
    while i < len(toks):
        t = toks[i]
        if t == "-C" and i + 1 < len(toks):
            dash_c = toks[i + 1]
            i += 2
            continue
        if t in GIT_VALUE_OPTS and i + 1 < len(toks):
            i += 2
            continue
        if t.startswith("-"):
            i += 1
            continue
        break  # reached the subcommand -- stop, never scan ITS OWN args for this
    return dash_c


def _resolve_target_repo(cmd, cwd):
    """The git toplevel of the repo the command being judged will ACTUALLY run in:
    a GLOBAL `git -C <path>` on the segment that actually invokes `git commit` wins,
    else a leading `cd <path> &&` (only the command's OWN first segment, and only when
    it is EXACTLY `cd <path>` -- 2 tokens, no more, no less), else the PreToolUse
    payload's own `cwd`. None if none of those resolve to a real git repo, OR if `cmd`
    cannot be safely segmented at all (see _tokenize_segments).

    KNOWN DESIGN BOUNDARY (flagged by the formal review gate, 2026-07-24, not merge-
    blocking): the exact-2-token requirement deliberately does not recognize `cd --
    <path> && ...` (3 tokens). A contrived compound command using that shape falls
    through to the payload `cwd` instead of the real target -- narrower than a bare
    `cd <path>`, and only reachable via a construction nobody has an ordinary reason to
    type. Widening the match is a reasonable future enhancement, not a fix."""
    d = None
    segs = _tokenize_segments(cmd)
    if segs is None:
        segs = []

    for seg_toks in segs:
        sub, _ = _segment_git_parts(seg_toks)
        if sub == "commit":
            d = _global_dash_c(seg_toks)
            break

    if not d and len(segs) > 1 and len(segs[0]) == 2 and segs[0][0] == "cd":
        d = segs[0][1]

    if not d:
        d = cwd
    if not d:
        return None
    toplevel = _git(d, "rev-parse", "--show-toplevel")
    return toplevel.strip() if toplevel else None


DEFAULT_MEMORY_INDEX = (
    "C:/Users/Owner/.claude/projects/"
    "C--Users-Owner-OneDrive---Oxford-Capital-Partners/memory/MEMORY.md")

# Markdown link whose target is a relative .md path: [Title](some_file.md) or (some_file.md#anchor).
# Skips absolute URLs (http:, https:, mailto:) and wiki-style [[links]], which are not paths.
LINK_RE = re.compile(r"\[[^\]]*\]\(\s*(?!\w+:)([^)\s#]+\.md)(?:#[^)\s]*)?\s*\)")

# Git global options that take their value as a SEPARATE following token. These must be
# skipped WITH their value when looking for the subcommand, or `git -c user.name=x commit`
# reads as subcommand "user.name=x" and the guard silently never fires.
GIT_VALUE_OPTS = frozenset((
    "-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path", "--config-env",
))


def target_index():
    return os.environ.get("ORA_MEMORY_INDEX") or DEFAULT_MEMORY_INDEX


def _git(repo, *args):
    """Run git, returning stdout or None. Never raises."""
    try:
        p = subprocess.run(
            ("git",) + args, cwd=repo, capture_output=True, timeout=15)
    except Exception:
        return None
    if p.returncode != 0:
        return None
    return p.stdout.decode("utf-8", "replace")


def _segment_git_parts(toks):
    """(subcommand, [args after it]) if this ALREADY-tokenized segment (a token list
    from _tokenize_segments) invokes git, else (None, []).

    Positional, not regexed, on purpose: the subcommand is the first token after `git`
    that is not an option (or an option's separate value). A substring match would
    wrongly fire on `git log --grep=commit`, because `commit` sits on a word boundary
    inside that token.
    """
    # Find the git executable token (allows `/usr/bin/git`, `git.exe`, and a leading
    # `sudo`/`env`-style prefix that we simply scan past).
    gi = None
    for i, t in enumerate(toks):
        base = t.rsplit("/", 1)[-1].rsplit("\\", 1)[-1].lower()
        if base in ("git", "git.exe"):
            gi = i
            break
    if gi is None:
        return None, []
    i = gi + 1
    while i < len(toks):
        t = toks[i]
        if t in GIT_VALUE_OPTS:
            i += 2          # skip the option AND its separate value
            continue
        if t.startswith("-"):
            i += 1          # `--foo`, `--foo=bar`, `-p` -- self-contained
            continue
        return t, toks[i + 1:]  # first non-option token IS the subcommand
    return None, []


def _segment_is_git_commit(toks):
    """True if this single ALREADY-tokenized segment invokes `git commit`."""
    return _segment_git_parts(toks)[0] == "commit"


# ---------------------------------------------------------------------------------
# PreToolUse TIMING (2026-07-24). This hook runs BEFORE the command does, so reading
# the index alone judges a state the command is about to change. For a COMPOUND
# command that produced two opposite failures, both verified against the live guard:
#   * FALSE NEGATIVE -- `git add MEMORY.md && git commit`: unstaged at hook time, so the
#     guard returned "not our business" and the orphan links landed. A straight BYPASS.
#   * FALSE POSITIVE -- `git restore --staged MEMORY.md && git commit`: staged at hook
#     time, so a commit that would NOT have included it was blocked.
# Same class as the config-write-guard compound-add blind spot. Fix: walk the command's
# segments in order and simulate whether MEMORY.md ends up in the commit.
# ---------------------------------------------------------------------------------
_STAGE_ALL_FLAGS = {"-A", "--all", "-u", "--update"}

# `git commit` options that consume the FOLLOWING token as their own value. A value of
# exactly `--` (e.g. `git commit -m --`, a literal message of "--") must be consumed as
# THAT option's value, never misread as the pathspec separator -- verified directly:
# `git commit -m --` commits the message "--" and the WHOLE staged index, same as any
# other `-m` value.
_COMMIT_VALUE_OPTS = frozenset((
    "-m", "--message", "-c", "--reedit-message", "-C", "--reuse-message",
    "-F", "--file", "--author", "--date", "-t", "--template",
    "--fixup", "--squash", "--trailer", "--cleanup", "--pathspec-from-file",
))


def _commit_pathspec(toks):
    """The trailing pathspec token list for a `git commit ...` ALREADY-tokenized
    segment (from _tokenize_segments), or None if there is no TRUSTWORTHY pathspec (no
    real `--` found, or the pathspec would be empty).

    Two failure modes found in an earlier version of this scan, both verified live
    against the deployed guard before being closed here:
      * `git commit -m --`: `-m`'s value is the literal string "--". A naive scan that
        just looks for a "--" TOKEN finds this one and reads an EMPTY pathspec after
        it, which `_mentions_path([], rel)` reports as False for any rel -- silently
        excluding MEMORY.md from a commit that (per real git) actually includes the
        whole staged index. Closed by walking `_COMMIT_VALUE_OPTS` and skipping the
        option's value token unconditionally, whatever it is.
      * `git commit -m x --` (a normal message, then a bare trailing `--` with nothing
        after it): real git commits the ENTIRE staged index in this shape -- an empty
        pathspec means "no restriction", not "matches nothing". Closed by treating an
        empty tail as untrustworthy (returns None) rather than as an exclusion.
    Falling through to None in both cases is intentionally the SAFE direction: the
    caller's normal staged_now/-a handling can only ever set `included=True`, never
    fabricate a False -- so an unrecognized shape over-blocks rather than bypasses.

    KNOWN RESIDUAL LIMITATION (documented, not fixed here -- see docstring above this
    function's caller): git also accepts a BARE positional pathspec with no `--` at all
    when it isn't revision-like, e.g. `git commit -m -- real.md` (where `-m` consumes
    the `--`, and `real.md` becomes a genuine restricting pathspec -- verified: only
    real.md lands). This scanner does not attempt to recognize that shape and returns
    None for it, which -- per the safe-direction guarantee above -- can only cause a
    spurious over-block on that rare construction, never a bypass.
    """
    gi = None
    for i, t in enumerate(toks):
        base = t.rsplit("/", 1)[-1].rsplit("\\", 1)[-1].lower()
        if base in ("git", "git.exe"):
            gi = i
            break
    if gi is None:
        return None
    i = gi + 1
    while i < len(toks) and toks[i] != "commit":
        if toks[i] in GIT_VALUE_OPTS:
            i += 2
        else:
            i += 1
    if i >= len(toks) or toks[i] != "commit":
        return None
    i += 1
    while i < len(toks):
        t = toks[i]
        if t == "--":
            pathspec = toks[i + 1:]
            return pathspec if pathspec else None
        if t in _COMMIT_VALUE_OPTS:
            i += 2      # skip the option AND its value, whatever that value is
            continue
        i += 1
    return None


def _mentions_path(args, rel):
    """True if any arg names MEMORY.md -- repo-relative, absolute, or bare basename.

    `args` now always arrives pre-tokenized (shlex, quote-aware) via
    _tokenize_segments, so the `.strip("\"'")` below is redundant on the common path
    (shlex already strips surrounding quote characters) -- kept intentionally as cheap
    defense-in-depth against any FUTURE caller that passes raw, un-tokenized text."""
    base = rel.rsplit("/", 1)[-1]
    for a in args:
        a2 = a.strip("\"'").replace("\\", "/")
        if a2 == rel or a2.endswith("/" + rel) or a2 == base or a2.endswith("/" + base):
            return True
    return False


def _commit_would_include(cmd, rel, staged_now):
    """(included, from_worktree) -- does MEMORY.md end up in this commit, and does its
    content come from the working tree (because the command stages it) or the index?

    Deliberately errs toward INCLUDED: a wrong 'included' costs a spurious block that a
    human can inspect, while a wrong 'excluded' silently lands the orphan this guard
    exists to stop.

    PATHSPEC EXCLUSIVITY (2026-07-24). `git commit -- <pathspec>` is EXCLUSIVE by git's
    own semantics -- verified directly: `git add A.md B.md; git commit -- A.md` commits
    ONLY A.md, leaving B.md staged and untouched even though it WAS staged at commit
    time; `git commit -a -- A.md` is a hard git error ("fatal: paths ... with -a does
    not make sense") and never commits at all. So once a `commit` segment carries a
    `--` pathspec, whether `rel` is one of the named paths is the ONLY question -- any
    staged_now state or earlier add/-a in this same command is moot, because the
    pathspec is what git actually honors. Concretely: in a shared checkout, another
    session's unrelated `git add` can leave MEMORY.md sitting staged in the index;
    without this carve-out a plain `git commit -- unrelated/file.md`, which cannot
    possibly touch MEMORY.md, was DENIED anyway.

    QUOTE-AWARE `--` DETECTION (2026-07-24, REFUTE pass on the carve-out above; the
    calling convention referenced below has since changed -- see _tokenize_segments'
    module comment, this file no longer tokenizes ANYTHING with a naive `.split()`).
    Segments now arrive here pre-tokenized (quote-aware) via _tokenize_segments, so an
    ORDINARY commit message containing a standalone " -- " (e.g. "fix -- bug", "notes
    -- see PR") can never be mistaken for a real pathspec separator -- reopening the
    exact bypass the 2026-07-24 12:54 fix closed, just behind different bait, is what a
    FIRST version of this carve-out did before that convention change. Verified live at
    the time: `git add MEMORY.md && git commit -m "fix -- bug"` and `git commit -am
    "fix -- bug"` both got ALLOW under that version. Only a standalone `--` TOKEN is
    trusted here; one embedded inside a quoted argument is invisible to the tokenizer
    and correctly ignored.
    See _commit_pathspec() for the option-aware scan that replaced a still-too-naive
    first shlex pass, which was itself caught misreading `git commit -m --` (an EMPTY
    pathspec, since `-m`'s value IS the `--`) as "excludes everything" -- via LOCAL code
    review before landing, not a second self-caught defect.

    COMPOUND-COMMAND ORDERING (known limitation, documented not fixed -- flagged by
    local code review). This function returns one CUMULATIVE (staged, from_worktree)
    after walking every segment, not "what did the actual `git commit` segment itself
    include". A `commit` segment carrying a pathspec can now set `staged=False` on its
    own -- previously a `commit` segment could only ever push `staged` UP (via `-a`) --
    so a LATER segment in the same compound command can flip a pathspec-exclusive
    commit's verdict back after that commit already ran, e.g.
    `git commit -m x -- other.md && git add MEMORY.md` reports included=True even though
    the commit itself (per verified pathspec exclusivity) could not have touched
    MEMORY.md; the trailing `add` only affects the WORKING directory's next commit, not
    this one. This errs toward over-blocking (safe), not a bypass, and is a pre-existing
    consequence of tracking one cumulative verdict rather than one per `commit`
    invocation -- correctly fixing it means restructuring the return value to be keyed
    per commit segment, out of scope for a minimal fix.
    """
    staged, from_worktree = staged_now, False
    segs = _tokenize_segments(cmd)
    if segs is None:
        return staged, from_worktree  # can't safely segment -- fall back unchanged
    for seg_toks in segs:
        sub, args = _segment_git_parts(seg_toks)
        if sub is None:
            continue
        if sub == "add":
            bulk = any(a in _STAGE_ALL_FLAGS for a in args) or \
                any(a.strip("\"'") == "." for a in args)
            if bulk or _mentions_path(args, rel):
                staged, from_worktree = True, True
        elif sub == "restore" and "--staged" in args:
            paths = [a for a in args if not a.startswith("-")]
            if not paths or _mentions_path(args, rel):
                staged, from_worktree = False, False
        elif sub == "reset":
            paths = [a for a in args if not a.startswith("-") and a != "HEAD"]
            if not paths or _mentions_path(args, rel):
                staged, from_worktree = False, False
        elif sub == "commit":
            pathspec = _commit_pathspec(seg_toks)
            if pathspec is not None:
                included_here = _mentions_path(pathspec, rel)
                staged, from_worktree = included_here, included_here
                continue
            # `-a` / `--all` stages every tracked modified file, including MEMORY.md --
            # so it re-includes a file an earlier segment just unstaged.
            if any(a in ("-a", "--all") or
                   (a.startswith("-") and not a.startswith("--") and "a" in a[1:])
                   for a in args):
                staged, from_worktree = True, True
    return staged, from_worktree


def _is_git_commit(cmd):
    """True if the command line invokes `git commit`. Ignores commands that merely
    MENTION it -- e.g. an echo of advice text, or `git log --grep=commit`."""
    if not isinstance(cmd, str) or "commit" not in cmd:
        return False
    segs = _tokenize_segments(cmd)
    if segs is None:
        return False  # can't safely segment -- fail OPEN (allow), same as elsewhere
    return any(_segment_is_git_commit(seg_toks) for seg_toks in segs)


def _staged_paths(repo):
    out = _git(repo, "diff", "--cached", "--name-only")
    if out is None:
        return None
    return {ln.strip() for ln in out.splitlines() if ln.strip()}


def _in_head(repo, relpath):
    return _git(repo, "cat-file", "-e", "HEAD:" + relpath) is not None


def main():
    payload = json.loads(sys.stdin.buffer.read().decode("utf-8"))
    if not isinstance(payload, dict):
        return
    if payload.get("tool_name") != "Bash":
        return
    cmd = (payload.get("tool_input") or {}).get("command")
    if not _is_git_commit(cmd):
        return

    index_abs = os.path.abspath(target_index())
    if not os.path.isfile(index_abs):
        return

    # REPO RESOLUTION (2026-07-24). `repo` is the ACTUAL target of the command being
    # judged -- resolved via _resolve_target_repo(cmd, cwd) above (`git -C <p>` wins,
    # else a leading `cd <p> &&`, else the PreToolUse payload's own `cwd` field) -- NOT
    # walked up from the hardcoded ORA_MEMORY_INDEX/DEFAULT_MEMORY_INDEX path as before.
    # That old approach always resolved to whichever repo the memory index physically
    # lives in (the main checkout), regardless of where the command actually runs, so a
    # `git commit` in an isolated worktree (its own independent index) was judged
    # against the MAIN checkout's unrelated staged state -- live-verified to both
    # over-block (a clean worktree commit denied over another session's staged
    # main-checkout orphan) and under-block (a REAL orphan staged only in a worktree's
    # own index was invisible, since the guard never looked at that index at all). A
    # totally unrelated repo (no memory/ directory whatsoever) triggered the same
    # over-block for the same reason.
    repo = _resolve_target_repo(cmd, payload.get("cwd") or "")
    if not repo:
        return  # can't resolve the target repo -- nothing to guard

    # The canonical memory index's OWN repo-relative path -- derived from where
    # DEFAULT_MEMORY_INDEX/ORA_MEMORY_INDEX physically lives, which identifies WHICH
    # file this guard protects, independent of which working copy (main checkout or a
    # worktree of the SAME underlying repo) the command being judged actually targets.
    canon_repo = _git(os.path.dirname(index_abs), "rev-parse", "--show-toplevel")
    if not canon_repo:
        return
    rel_index = os.path.relpath(index_abs, canon_repo.strip()).replace(os.sep, "/")

    # Does the RESOLVED target repo even have this path on disk? A worktree of the
    # SAME repo checks out the full tracked tree, so it does; an unrelated repo does
    # not -- in which case this command cannot possibly touch the file we protect.
    if not os.path.isfile(os.path.join(repo, rel_index)):
        return

    staged = _staged_paths(repo)
    if staged is None:
        return

    # Would this commit include MEMORY.md at all? Simulated from the command's segments,
    # NOT read straight off the pre-command index -- see _commit_would_include.
    # EVERY index this commit might land: the root MEMORY.md plus any sub-index
    # (INDEX_*.md) beside it. The 2026-08-03 split moved 108 of ~190 pointers into
    # INDEX_reference.md, so guarding MEMORY.md alone would leave the MAJORITY of the
    # corpus's pointers unguarded at commit time -- this hook's own hole, relocated.
    # Iterated, never duplicated: this file already records how two independent
    # scanners for one fact drifted apart, and that lesson applies to itself.
    mem_dir = os.path.dirname(rel_index)
    index_rels = [rel_index]
    try:
        for name in sorted(os.listdir(os.path.join(repo, mem_dir) if mem_dir else repo)):
            if name.upper().startswith("INDEX_") and name.lower().endswith(".md"):
                index_rels.append((mem_dir + "/" + name) if mem_dir else name)
    except Exception:
        pass  # fail-open: an unreadable directory must never block a commit

    missing = []          # [(index_rel, rel_target)] -- which index carried the bad link
    for idx_rel in index_rels:
        # Would this commit include THIS index at all? Simulated from the command's
        # segments, NOT read straight off the pre-command index -- see
        # _commit_would_include.
        included, from_worktree = _commit_would_include(cmd, idx_rel, idx_rel in staged)
        if not included:
            continue  # this index is not part of the commit -- not our business

        # `from_worktree` (from _commit_would_include, above) is the single source of
        # truth for whether THIS commit reads the index from the working tree or from
        # git's index -- it is already quote-aware via _commit_pathspec(). A second,
        # independent raw-string `_has_pathspec(cmd)` check used to live here
        # (`re.search(r"\s--\s", cmd)`) and was REMOVED (2026-07-24, second local-review
        # round): it could fire on a decoy " -- " inside an ordinary quoted commit
        # message even when `_commit_pathspec` correctly found no real pathspec, forcing
        # a working-tree read for what is actually a plain staged commit. If the working
        # tree had since been reverted to a clean index while the ORPHANED version stayed
        # staged (real git commits the index here, not the working tree), the guard
        # scanned the wrong, clean content and ALLOWED -- verified live: the orphaned
        # index content landed. Two independent quote-aware scanners for the same fact is
        # itself a hazard (this is exactly how they drifted); there is still only one.
        #
        # A pathspec commit takes the WORKING TREE, and so does anything the command
        # stages itself -- read the RESOLVED repo's own copy (os.path.join(repo,
        # idx_rel)), NOT a hardcoded canonical path: for a command targeting a worktree
        # that is a DIFFERENT file on disk from the main checkout's copy, even though
        # both sit at the same relative path.
        if from_worktree:
            try:
                with open(os.path.join(repo, idx_rel), "r", encoding="utf-8") as fh:
                    content = fh.read()
            except Exception:
                continue
        else:
            content = _git(repo, "show", ":" + idx_rel)
            if content is None:
                continue

        # If the version being committed is byte-identical to HEAD's, this commit lands
        # no new index lines -- any orphan in it is pre-existing, and blocking here would
        # be a permanent deadlock rather than a guard.
        head_content = _git(repo, "show", "HEAD:" + idx_rel)
        if head_content is not None and head_content == content:
            continue

        seen = set()
        for target in LINK_RE.findall(content):
            if target in seen:
                continue
            seen.add(target)
            rel_target = (mem_dir + "/" + target) if mem_dir else target
            rel_target = os.path.normpath(rel_target).replace(os.sep, "/")
            if rel_target in staged:
                continue
            if _in_head(repo, rel_target):
                continue
            missing.append((idx_rel, rel_target))

    if not missing:
        return

    # De-duplicate by body path, preserving order: the same body can be linked from more
    # than one index, and the fix (stage the body) is identical either way.
    miss_paths = []
    for _idx_rel, m in missing:
        if m not in miss_paths:
            miss_paths.append(m)
    carriers = sorted({i for i, _m in missing})
    on_disk = [m for m in miss_paths if os.path.isfile(os.path.join(repo, m))]
    absent = [m for m in miss_paths if m not in on_disk]

    parts = [
        "MEMORY.md orphan-index-link guard: this commit would land %d index link(s) whose "
        "body file is neither in HEAD nor staged. A clone would get a broken pointer, and "
        "memory-integrity-probe.py would exit 1 on the next run.%s" % (
            len(miss_paths),
            "" if carriers == [rel_index] else
            "  Carried by: " + ", ".join(os.path.basename(c) for c in carriers))
    ]
    if on_disk:
        parts.append(
            "\nPresent on disk but NOT staged -- stage the bodies in the SAME commit:\n"
            "  git add %s" % " ".join('"%s"' % m for m in on_disk))
    if absent:
        parts.append(
            "\nNot on disk at all (typo, rename, or a body never written):\n" +
            "\n".join("  - " + m for m in absent))
    parts.append(
        "\nBody before index, always. If these bodies belong to ANOTHER session, do not "
        "stage them -- commit your own body files first and leave that session's index "
        "line uncommitted for it to land.")

    out = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": "".join(parts),
        }
    }
    sys.stdout.write(json.dumps(out))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass  # fail open: a bug must never block a commit
    sys.exit(0)
