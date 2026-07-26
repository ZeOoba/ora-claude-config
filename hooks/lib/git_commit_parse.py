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
  - a recognized heredoc's body (matched by its own literal terminator line, bash's
    lexically distinct rule) is excised as opaque content before any tokenization,
    so a stray quote/comment/`git add`/`--dry-run`/`-- path` inside a commit
    message's heredoc body can never be misread as real command structure
    (2026-07-26, three-round incident -- see tokenize_cmd_segments' own docstring
    for the full history; this also closes the "spurious candidate" gap this note
    used to accept below)

ACCEPTED GAPS (unchanged from the origin file, documented there in full): git
aliases are invisible; subshells and command substitution OTHER than a recognized
heredoc are not parsed (e.g. arbitrary `$(...)` content can still affect quote
parity outside a heredoc); operators glued to a token without surrounding
whitespace are not parsed. Threat model throughout is a single-operator
cooperative fleet, not an adversarial boundary.

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
    commit. Both PoCs reproduced against the pre-fix code.

    KNOWN INTERACTION (2026-07-24, review finding m2, informational, not a
    regression): "last commit wins" means `git commit -m real && git commit
    --dry-run` reads as dry-run overall, suppressing gating of the earlier
    REAL commit -- unchanged from the old whole-string substring check's
    behavior for this exact shape, and multi-commit-per-Bash-call is already
    an accepted gap elsewhere in this module (git_add_segments). The reverse
    order (`--dry-run && real`) is now correctly gated, which the old check
    could not do."""
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


_HEREDOC_MARKER_RE = re.compile(
    r"(?<!<)<<(-)?\s*(['\"]?)([^\s'\"\\<>|&;()`]+)\2")


def _scan_quote_state(text, state):
    """Incremental, O(len(text)) scan of one line's worth of shell-level text
    (never a heredoc BODY -- see tokenize_cmd_segments), given the quote
    `state` carried in from a prior line (None = unquoted, "'" or '"' = a
    still-open quote of that kind). Returns the ending state after this line.

    Deliberately has NO `#`-comment handling (see tokenize_cmd_segments'
    ROUND 3 note for why removing it, rather than trying to get it exactly
    bash-correct, is what actually closes that finding) and no `$(...)`
    awareness (the heredoc-recognition in tokenize_cmd_segments exists
    precisely so this function is only ever asked to track quotes across
    the small, simple shell fragments immediately before/after a heredoc,
    never across a heredoc's own opaque body content)."""
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        if state == "'":
            if c == "'":
                state = None
            i += 1
            continue
        if state == '"':
            if c == "\\" and i + 1 < n and text[i + 1] in ("$", "`", '"', "\\"):
                i += 2
                continue
            if c == '"':
                state = None
            i += 1
            continue
        # state is None (unquoted)
        if c == "\\":
            i += 2  # unquoted backslash escapes the next character
            continue
        if c == "'":
            state = "'"
            i += 1
            continue
        if c == '"':
            state = '"'
            i += 1
            continue
        i += 1
    return state


def _in_open_subshell_or_backtick(text):
    """Round-5 fix (was a bare `"$(" in before` substring check): a `$(` or
    backtick command substitution re-enters a fresh, independently-parsed
    command context where `<<` is a real operator again despite an
    enclosing quote -- exactly this fleet's own `-m "$(cat <<'EOF'`
    pattern. The substring check alone was foolable: `echo "$(date +%Y)
    note <<EOF here"` has a `$(` earlier on the line, but it is ALREADY
    CLOSED by its own `)` before the `<<` -- bash-verified the marker there
    is still just quoted text, not a real heredoc. This depth-counts
    `$(`/`)` pairs and unescaped backticks instead of checking mere
    presence, so an already-closed substitution no longer counts. Does NOT
    track quotes INSIDE the substitution itself (good enough for this
    narrow purpose: deciding whether a following `<<` sits in a live
    substitution) -- full shell-grammar matching is the same accepted gap
    the rest of this module already documents."""
    depth = 0
    backticks = 0
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        if c == "\\":
            i += 2
            continue
        if c == "$" and i + 1 < n and text[i + 1] == "(":
            depth += 1
            i += 2
            continue
        if c == ")" and depth > 0:
            depth -= 1
            i += 1
            continue
        if c == "`":
            backticks += 1
            i += 1
            continue
        i += 1
    return depth > 0 or (backticks % 2 == 1)


def _fallback_tokenize_lines(lines, lo, hi, segs):
    """The ORIGINAL (pre-2026-07-26) per-line-independent tokenization,
    applied to lines[lo:hi]: each line tried through shlex.split() alone,
    falling back to a naive whitespace split on failure, each becoming its
    own segment -- exactly the long-proven-safe behaviour for anything that
    isn't a recognized heredoc (see tokenize_cmd_segments)."""
    for k in range(lo, hi):
        line = lines[k]
        if not line.strip():
            continue
        try:
            tokens = shlex.split(line)
        except ValueError:
            tokens = line.split()
        segs.extend(_split_segments(tokens))


def tokenize_cmd_segments(cmd):
    """Tokenize `cmd` LINE BY LINE, not as one whole-string shlex.split() call,
    so a bare newline (bash's statement separator, same semantics as `;`) acts
    as a segment boundary for ordinary lines. The ONE exception is a
    recognized heredoc (`<<[-]DELIM` or `<<[-]'DELIM'`/`<<[-]"DELIM"`): bash
    reads everything from the line after the marker through the first line
    that is EXACTLY `DELIM` as opaque body content, a lexically distinct rule
    from quote-nesting and independent of it -- so that span is located by
    matching the literal terminator line, NEVER by scanning its content for
    quote/comment characters, and is excised before any tokenization is
    attempted. Everything else in this function is the ORIGINAL, long-proven
    per-line-independent behaviour, UNCHANGED.

    THREE ROUNDS TO GET HERE (2026-07-26, all on real-incident reproductions
    caught by independent review before landing -- see
    test-commit-provenance-guard.py for every PoC below as a regression test):

    ROUND 1 (the original bug): the very first version of this function
    called shlex.split() on EACH line in total isolation, treating any
    ValueError (unterminated quote) as "this line alone doesn't tokenize,
    naive-split JUST this line" and moving on -- silently discarding every
    following line as unrelated, disconnected segments. A heredoc-fed `-m`
    value (the pattern this fleet's own commit instructions REQUIRE for
    every commit message) opens a `"` on its first line that isn't closed
    for several lines; a trailing `-- <pathspec>` on the line after the
    heredoc closes landed in one of those disconnected segments and was
    invisible to find_commit_segment(). candidate_paths() then fell back to
    "no pathspec -> the whole staged index" -- a confirmed false BLOCK on a
    real, correctly-scoped commit, on both gates that share this module.

    ROUND 2 (first fix attempt, itself wrong): accumulating lines on a
    ValueError and, on end-of-input, naive-splitting the WHOLE merged buffer
    as one token stream converted the bug into a false ALLOW. An apostrophe
    inside a `#` shell comment (`# don't add theirs`) reads to plain shlex as
    an unterminated quote; the merged-buffer fallback then swallowed a REAL,
    later `git commit` line into that one meaningless token stream instead of
    recognizing it as its own segment, silently disabling both gates for a
    command that unambiguously does commit. A second PoC showed a LATER
    line's own comment apostrophe could spuriously "close" an EARLIER one,
    burying a real commit in between inside what shlex then read as
    valid-but-wrong quoted content. Also independently measured at O(n^2) in
    input size (repeated full shlex re-tokenization of the ever-growing
    buffer on every accumulated line) -- 13s at 500 lines, 55s at 1000,
    against a hook budget other gates in this codebase treat as ~5s.

    ROUND 3 (second fix attempt -- incremental quote-state scanning instead
    of repeated re-tokenization, closing round 2's false-allow and its O(n^2)
    cost -- STILL had two gaps, both from trying to generally emulate bash
    quoting for arbitrary content instead of narrowly recognizing the one
    construct this fleet actually needs): (a) the scanner had no `$(...)`
    awareness (an accepted, pre-existing gap for this whole module), so a
    stray `"` inside a heredoc BODY could flip the OUTER quote-state parity,
    ending the segment early and exposing later body prose as commit
    args -- confirmed to leak a decoy `-- <path>` as the real pathspec, and
    separately confirmed to leak a decoy `--dry-run` into args, hiding a real
    commit; this diff's own docstring at the time falsely claimed degradation
    could only ever produce MORE candidates, never fewer -- it could. (b) the
    scanner (and shlex's own `comments=True`) treated ANY unquoted `#` as a
    comment, not just one at the START of a word as bash actually requires --
    `${#arr[@]}` and `sed s/#/x/` both hid a real, same-line-following commit,
    and `git commit -m x -- readme#old.md` had its pathspec truncated to
    `readme`.

    ACTUAL FIX (this version): stop trying to track quotes/comments through
    arbitrary content at all. Recognize the ONE construct that actually needs
    multi-line handling -- a heredoc -- via its own unambiguous, quote-
    independent terminator-line rule, and treat its body as fully opaque:
    never quote-scanned, never comment-scanned, never tokenized, so nothing
    inside it (a stray `"`, a `#`, a decoy `-- path` or `--dry-run`) can ever
    affect anything outside it. `_scan_quote_state` is still used, but only
    to track quotes across the small, simple shell-level fragments
    immediately before a heredoc marker and immediately after its terminator
    (e.g. the `"` opened by `-m "` and closed by the `)"` on the line right
    after `EOF`) -- text that, in every real pattern this fleet uses, never
    itself contains a `#` or a `$(...)`. EVERY other line (no heredoc marker
    present) goes through `_fallback_tokenize_lines`, which is byte-for-byte
    the ORIGINAL, pre-2026-07-26, already-proven-safe per-line-independent
    logic -- restoring exactly the behaviour that made round 2's PoCs
    impossible in the first place, since there is no cross-line accumulation
    at all for anything that isn't a recognized heredoc.
    ROUND 4 (the excise-the-body architecture was correct; three edges of
    the RECOGNITION logic itself still diverged from real bash, each with a
    reproduced false-allow): (a) the terminator was matched via
    `line.strip() == delim`, tolerating surrounding whitespace bash does not
    -- a body line that is merely an INDENTED or trailing-whitespace variant
    of the delimiter (not an exact match) ended the heredoc early to this
    parser while bash keeps reading it as body, re-exposing the remaining
    body as shell-level text (bash-verified); `<<-` only strips LEADING TABS
    before comparing, not arbitrary whitespace, and the old code didn't
    distinguish `<<` from `<<-` at all. (b) the marker regex had no quote
    awareness, so a `<<WORD` appearing INSIDE a quote (`echo "see <<EOF
    docs"`) was read as a real marker; if some later line coincidentally
    equalled that fake delimiter, a real intervening `git commit` got excised
    as "body" (bash-verified the quoted `<<EOF` is plain text to bash, not a
    marker). (c) the `not closed` fallback re-tokenized the ENTIRE consumed
    range including the heredoc BODY and its terminator, contradicting the
    "never over-collects" claim right above it -- body prose could still
    surface as a fabricated final segment whenever the trailing quote-close
    check never closed (e.g. a stray comment apostrophe after the pathspec).
    Fixed by: (a) exact-match terminator comparison, tab-stripped only when
    the marker was `<<-`; (b) rejecting a marker match when
    `_scan_quote_state` says the text before it on that line is not
    currently unquoted; (c) the fallback now only re-tokenizes the marker
    line and whatever trailing lines were pulled in AFTER the terminator --
    never the excised body+terminator range itself, regardless of path.

    ROUND 5 (the recognition logic itself, not the architecture, again --
    all four reproduced against real bash): (a) the delimiter regex only
    matched a plain word character class ([A-Za-z0-9_]+), but bash's
    delimiter is a full shell WORD (`END-OF-MSG`, `EOF.txt` are both legal)
    -- a delimiter outside that narrow class never matched its own real
    terminator, degrading the ENTIRE heredoc to the per-line fallback
    (round-1's original false-block, still live for any such delimiter) --
    and if the truncated prefix (`END`, `EOF`) coincidentally appeared as a
    body line, THAT ended the heredoc early instead, re-exposing later body
    prose as shell text (a false-allow, the same class round 4 (a) fixed
    for indentation). (b) the marker-acceptance check used a bare `"$(" in
    before` substring test, foolable by an ALREADY-CLOSED substitution
    earlier on the line (`echo "$(date +%Y) note <<EOF here"` -- the `$(`
    is there, but its own `)` closed before the `<<`) and structurally blind
    to a quote opened on an EARLIER line (the check always started
    scanning from state=None). Both bash-verified to excise a real,
    intervening `git commit` as fake heredoc "body" when a coincidental
    bare-delimiter line followed. Fixed by: (a) widening the delimiter
    character class to bash's actual word syntax (anything but whitespace,
    quotes, backslash, and shell metacharacters); (b) replacing the
    substring check with `_in_open_subshell_or_backtick`, which depth-counts
    `$(`/`)` pairs and backticks instead of checking mere presence, AND
    threading a `carry_state` across every non-heredoc line (updated via
    the same `_scan_quote_state` already used elsewhere) so a quote left
    open by an earlier line is not forgotten by the time a `<<` is seen on
    a later one. carry_state is used ONLY to gate marker acceptance --
    every non-heredoc line is still tokenized completely independently via
    `_fallback_tokenize_lines`, so this does not reintroduce round 2's
    cross-line-accumulation regression (verified: both round-2 PoCs still
    pass). (c) `<<<WORD` (bash's here-STRING operator -- an entirely
    different, single-line construct with no body/terminator at all) was
    matched by the marker regex via its middle `<<`, and if some later,
    unrelated line coincidentally equalled the "delimiter" (really just the
    here-string's own word), everything in between -- including a real
    `git commit` -- was excised as fake body. Fixed with a negative
    lookbehind (`(?<!<)`) rejecting a `<<` immediately preceded by another
    `<`; a genuine `cat<<EOF` (no space, immediately preceded by a
    non-`<` character) is unaffected.

    ACCEPTED GAP, documented honestly rather than claimed safe-direction
    (round-5 reviewer finding): `_in_open_subshell_or_backtick` and
    carry_state are heuristics, not full shell-grammar matching. A
    sufficiently adversarial input (quotes and substitutions deliberately
    interleaved across several lines specifically to fool the depth-count,
    or multiple heredoc markers chained on one line via `<<A ... <<B`, which
    bash reads back-to-back but this parser only recognizes the first of)
    can still misidentify a marker. Round-6 verification also surfaced a
    narrower, concrete instance of the same class: a SPURIOUS carried-open
    quote (e.g. an ordinary comment apostrophe, `# don't forget`, on some
    earlier line with no heredoc involved at all) can cause a genuine,
    non-`$(`-wrapped heredoc marker on a LATER line to be wrongly rejected
    -- degrading that heredoc to the per-line fallback and exposing its
    body as shell text, a false-ALLOW if the body happens to contain
    decoy commit-shaped prose. This module's threat model has always been
    a single-operator COOPERATIVE fleet, not an adversarial boundary (see
    ACCEPTED GAPS above) -- these residual holes are real, are a
    false-ALLOW risk if hit, and are recorded here rather than glossed
    over, but closing them fully would mean implementing real bash
    parsing, which is out of scope for a PreToolUse heuristic gate. The
    fleet's actual, single-line `-m "$(cat <<'EOF'` commit-message pattern
    is immune to all of the above via the `$(` escape hatch.

    Verified against: the original heredoc bug, both round-2 false-allow
    PoCs, both round-3 `$(...)`-body-parity PoCs, all three round-3
    `#`-word-start PoCs, all three round-4 recognition-edge PoCs (indented
    fake terminator, quoted fake marker, fallback body re-exposure), a
    2000-line heredoc body (effectively instant, since the body is now
    excised before tokenization rather than being part of it -- versus
    round 2's multi-second-to-minute blowup at a fraction of that size), a
    3000-line never-closing-quote input with no heredoc at all (still fast,
    still finds the real trailing commit via the per-line
    fallback), and every pre-existing regression test in this module's two
    consumer test suites (test-commit-provenance-guard.py,
    test-eos-review-gate.py), all green."""
    segs = []
    lines = cmd.splitlines()
    i = 0
    n = len(lines)
    # ROUND 5 fix: quote state now carries across lines that have NO
    # recognized heredoc marker, purely to gate heredoc-marker acceptance --
    # see the marker-rejection check below. This does NOT reintroduce
    # round 2's regression: non-heredoc lines are still tokenized
    # completely independently, one at a time, via _fallback_tokenize_lines;
    # carry_state is consulted ONLY when a `<<` is actually found on a line,
    # never used to merge lines for tokenization.
    carry_state = None
    while i < n:
        start = i
        line = lines[i]
        i += 1
        if not line.strip():
            continue

        m = _HEREDOC_MARKER_RE.search(line)
        # A `<<WORD` appearing INSIDE a quote (e.g. `echo "see <<EOF docs"`,
        # or a quote left open by an EARLIER line -- carry_state) is not a
        # real heredoc marker to bash -- quotes suppress operator meaning
        # for everything except `$`/backtick/`\`. Reject it using the quote
        # scanner (seeded with carry_state, so a quote opened on a PRIOR
        # line is not forgotten), UNLESS the text is currently inside a live
        # `$(...)` or backtick substitution: bash re-enters a fresh,
        # independently-parsed command context there, where `<<` IS a real
        # operator again despite an enclosing quote -- exactly this fleet's
        # own `-m "$(cat <<'EOF'` pattern. `_in_open_subshell_or_backtick`
        # depth-counts rather than just checking substring presence, so an
        # ALREADY-CLOSED `$(...)` earlier on the line no longer counts
        # (round-5 finding: `echo "$(date +%Y) note <<EOF here"` used to
        # pass the old bare `"$(" in before` check even though its `$(...)`
        # had already closed before the `<<`). A rejected match here just
        # means "no marker on this line" (falls through to ordinary
        # per-line handling below), the same safe degradation as never
        # matching.
        if m is not None:
            before = line[:m.start()]
            if (not _in_open_subshell_or_backtick(before)
                    and _scan_quote_state(before, carry_state) is not None):
                m = None
        if m is None:
            carry_state = _scan_quote_state(line, carry_state)
            _fallback_tokenize_lines(lines, start, i, segs)
            continue

        # Locate the terminator: bash requires a line that IS the delimiter
        # -- no surrounding whitespace tolerated -- except that `<<-` (the
        # dash captured in group 1) strips LEADING TABS ONLY before
        # comparing, not arbitrary whitespace. Getting this exact match
        # matters: a body line that merely LOOKS like the delimiter under a
        # looser rule (indented, trailing spaces) would end the heredoc
        # early to this parser while bash keeps reading it as body --
        # re-exposing the rest of the body as shell-level text, exactly the
        # false-allow/false-block class this function exists to prevent.
        # Deliberately NOT found by scanning for quote characters, so
        # nothing inside the body can spoof it via quote content.
        strip_tabs_only = m.group(1) is not None
        delim = m.group(3)
        term = None
        j = i
        while j < n:
            candidate = lines[j].lstrip("\t") if strip_tabs_only else lines[j]
            if candidate == delim:
                term = j
                break
            j += 1

        if term is None:
            # No terminator within what this Bash call actually included
            # (truncated heredoc, or not really a heredoc) -- do not guess
            # at where an absent terminator would have been; fall back to
            # the safe, original per-line handling for just this one line.
            carry_state = _scan_quote_state(line, carry_state)
            _fallback_tokenize_lines(lines, start, i, segs)
            continue

        # The body (lines[i:term], EXCLUSIVE of the terminator) is opaque --
        # excised entirely, never scanned or tokenized. Track quote-balance
        # only for the marker line (starting FRESH at None here, not
        # carry_state -- this fleet's real pattern always opens its `-m "`
        # quote fresh on the marker line itself, and tracking a quote that
        # spans from an earlier line THROUGH a recognized heredoc marker is
        # an accepted, narrower gap than the one this carry_state exists to
        # close), then (jumping past the body+terminator) whatever
        # shell-level text follows, until it balances -- e.g. the `"`
        # opened by `-m "` on the marker line, closed by a `)"` on the line
        # right after the terminator.
        state = _scan_quote_state(line, None)
        i = term + 1
        shell_lines = [line]
        while state is not None and i < n:
            nxt = lines[i]
            state = _scan_quote_state(nxt, state)
            shell_lines.append(nxt)
            i += 1

        closed = False
        if state is None:
            try:
                tokens = shlex.split("\n".join(shell_lines))
                segs.extend(_split_segments(tokens))
                closed = True
            except ValueError:
                pass
        if not closed:
            # Quote never balanced by end-of-input, or somehow still failed
            # to tokenize -- fall back to the original per-line handling,
            # but EXCLUDING the heredoc body and its terminator line
            # (lines[start+1:term+1]): those were already committed to being
            # opaque the moment a real heredoc was recognized, and must
            # never be re-tokenized as shell syntax even on this path --
            # doing so would let body prose (a decoy `--dry-run` sitting
            # next to a stray apostrophe that keeps this whole branch from
            # ever closing) surface as if it were real commit args, exactly
            # the false-allow this function exists to prevent. Only the
            # marker line itself and whatever trailing lines were pulled in
            # AFTER the terminator get the per-line fallback.
            _fallback_tokenize_lines(lines, start, start + 1, segs)
            _fallback_tokenize_lines(lines, term + 1, i, segs)
        # Propagate the ending quote-parity forward regardless of path --
        # if it never closed, subsequent lines correctly keep seeing an
        # open quote, rejecting more heredoc markers rather than fewer --
        # USUALLY the safe direction (degrading toward the per-line
        # fallback), but see the ROUND 5 accepted-gap paragraph above: a
        # SPURIOUS carried-open state (e.g. a comment apostrophe on an
        # earlier line) can also reject a genuine, non-`$(`-wrapped
        # heredoc, which is a false-allow, not a false-block, if that
        # heredoc's body happens to contain decoy commit-shaped text.
        carry_state = state
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


# A directory / repo-root / glob / pathspec-magic ARGUMENT matches MANY files,
# not one. Treating it as a single literal candidate collapses risk_files()/
# candidate_paths() to a degenerate set: _content_digest() on a DIRECTORY path
# hits OSError and returns the constant "DELETED", so review_key() becomes
# content-independent -- confirmed by adversarial review (2026-07-26, REFUTE
# F1/F2): a review recorded once for `git commit -- hooks/` validated FOREVER,
# regardless of what any file under hooks/ actually contained, in ANY repo
# (the key is not even repo-specific). `git commit -- .` similarly emptied
# candidate_paths()/risk_files() entirely (_rel(repo, repo) == "." ->
# risk_reason(".") == None) and bypassed eos-review-gate.py with no review
# recorded at all.
#
# ROUND 2 (same day, follow-up REFUTE pass): the first fix's predicate --
# "expand only if currently a directory or one of five hardcoded repo-root
# strings" -- still left the literal-path fast path reachable for `-- '*'`,
# `-- ':(top)'`, `-- ':(glob)hooks/**'`, `-- ':(icase)HOOKS'`, and a DELETED
# directory (`os.path.isdir` is False for a path with no working-tree entry
# left, even though `git diff --cached -- <it>` still correctly resolves the
# files being removed) -- every one of these confirmed to reproduce F1/F2
# verbatim, `'*'` being a one-character bypass of a BLOCKING gate. The fix
# inverts the predicate: take the fast (unexpanded, no extra git calls) path
# ONLY for an unambiguous, currently-existing REGULAR FILE with no leading
# `:` (git's pathspec-magic prefix) and no shell-glob metacharacter -- every
# other shape, including one git can find nothing for, goes through git
# resolution. Also added `ls-files --others --exclude-standard` to the union
# (round-2 finding R3): a directory pathspec that also matches a brand-new
# UNTRACKED file was under-counted, missing exactly the compound
# `git add <paths> && git commit -- <dir>` shape this fleet actually uses.
_PATHSPEC_MAGIC_CHARS = frozenset("*?[]")


def pathspec_arg_paths(repo, p):
    """Absolute normcase file paths a single commit `-- <p>` pathspec argument
    resolves to right now. The common, unambiguous case (an existing regular
    file, no glob/magic syntax) is returned unchanged, unexpanded -- no extra
    git calls, no behaviour change from before this fix existed. Every other
    shape -- a directory, a repo-root form, a glob, git pathspec magic
    (':(top)', ':(icase)', ':(glob)', ...), or a path git can find nothing
    for on disk right now (e.g. a just-deleted directory whose removal is
    itself what would be committed) -- is resolved through git instead of
    trusted as a literal. Errs toward OVER-inclusion on any ambiguity (more
    candidates flagged), the safe direction for both consumer gates -- never
    toward silently narrowing what a pathspec actually covers.
    ACCEPTED GAP: does not fully PARSE git's pathspec-magic grammar (it
    detects the presence of magic via a leading ':' and defers to git's own
    resolution rather than interpreting the magic itself) -- same single-
    operator-cooperative threat model as the rest of this module. A form git
    itself resolves to nothing real falls back to the literal path rather
    than being dropped."""
    abs_p = os.path.join(repo, p)
    if (os.path.isfile(abs_p) and not p.startswith(":")
            and not (_PATHSPEC_MAGIC_CHARS & set(p))):
        return {abs_p}
    staged = git_lines(repo, ["diff", "--cached", "--name-only", "--", p]) or []
    modified = git_lines(repo, ["diff", "--name-only", "--", p]) or []
    tracked = git_lines(repo, ["ls-files", "--", p]) or []
    untracked = git_lines(
        repo, ["ls-files", "--others", "--exclude-standard", "--", p]) or []
    rels = set(staged) | set(modified) | set(tracked) | set(untracked)
    if not rels:
        return {abs_p}  # nothing git can resolve this to -- fall back, don't drop it
    return {os.path.join(repo, r) for r in rels}


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
        out = set()
        for p in given:
            if not p:
                continue
            out |= pathspec_arg_paths(repo, p)
        return {norm(p) for p in out}

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
