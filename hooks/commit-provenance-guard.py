"""Commit-provenance guard -- PreToolUse hook, matcher: Bash.

BLOCKS a `git commit` that would sweep up ANOTHER LIVE SESSION's uncommitted
work. Companion to commit-provenance-recorder.py (PostToolUse), which supplies
the per-session touched-file provenance this guard reads.

WHY: on 2026-07-16 one session hit four concurrency events in an hour; THREE were
Bash git operations, invisible to any Edit|Write hook. The worst: a staged
MEMORY.md edit was swept into another session's commit inside the ~30s window
between this session's `git add` and its `git commit`. shared-checkout-guard.py
warns at EDIT time and is advisory; this guard enforces at COMMIT time, the one
chokepoint where provenance is fixed. Full rationale + rejected alternatives:
docs/superpowers/specs/2026-07-16-commit-provenance-guard-design.md

SAFETY INVARIANT -- fail-open BY CONSTRUCTION, not by exception handling. It
blocks only on THREE affirmative signals: (a) a candidate file appears in
another session's touched-set, AND (b) session_liveness affirmatively reports
that session open, AND that set is within TTL, AND (c) the path has NOT
already been committed since that recorded touch. Missing/stale/unreadable
data yields "no information" -> ALLOW. This honours session_liveness.py's
explicit contract ("ENRICHMENT ONLY, never a hard gate ... treat a read
failure, or a stale/empty result, the same as 'no information'"). NO LOCK IS
EVER HELD, so a crashed session cannot wedge the fleet -- the deadlock class
does not exist here.
The same invariant now covers an IMPORT-time failure of either sibling module too
(2026-07-17): guarded at load, main() returns immediately if either failed to load.

RECENCY-HEURISTIC FIX (2026-07-17): the original design blocked on touched-set
membership + liveness + a whole-file TTL alone, with no check for whether the
flagged edit had since been safely committed -- by the other session, or by
anyone. That produced 3 false positives in one session the same day: another
session's edit to the same file had already landed in HEAD by the time this
guard ran, but the touched-set entry (and the live-session signal) persisted
for the full TTL regardless. `already_committed_since()` closes this: given the
per-path touch timestamp now recorded by the recorder (see commit_provenance.py's
touch_line()/read_touched()), a hit is suppressed if the path's last commit is
NEWER than (or equal to) that touch time -- the content is provably already
safe, not just probably. An unknown touch time (old-format line, or the path
was never committed) keeps the ORIGINAL conservative behaviour: still a hit.

Deliberately narrow (precision over recall, same philosophy as
registry-write-guard.py): it does NOT catch foreign files written by a script
rather than the Edit tool. That accepted false negative is what makes the guard
survivable -- the naive "block anything I did not touch" design would have
blocked 31ac61d, a legitimate script-generated commit.

CASE-SENSITIVITY + PER-ENTRY TTL FIX (2026-07-20): two compounding bugs made
the guard permanently block a still-open session's every past touch. (1)
last_commit_time() ran `git log -- <pathspec>` against the norm()-ed path,
which os.path.normcase lowercases wholesale on Windows; git's pathspec match
against history is literal regardless of core.ignorecase, so a lowercased
pathspec silently matched nothing for any real path with an uppercase
character anywhere in it -- already_committed_since() always read "never
committed" and the 2026-07-17 fix above was dead code in practice. Fixed by
wrapping the pathspec as `:(literal,icase)<path>`. (2) foreign_hits() gated
each session's touched-set entries on touched-files.txt's WHOLE-FILE mtime,
not the per-entry touch_ts read() already returns -- so a live session that
kept touching OTHER paths kept the file's mtime fresh, and a days-stale entry
for an unrelated path never aged out via TTL. Fixed by checking each entry's
own touch_ts against the TTL cutoff instead (unknown touch_ts still never
ages out, per commit_provenance.py's documented "just touched" contract).
ACCEPTED TRADEOFF: per-entry TTL narrows the block window for one shape the
old (buggy) whole-file gate happened to also catch -- a still-live session
that touched a path >TTL_H ago and left it uncommitted while staying active
elsewhere now ages out and is allowed through. This is the intended effect of
keying TTL to SESSION_PRUNE_H per-touch rather than per-file; already_committed_since()
is the correctness backstop for genuinely-landed content, not TTL.

REMEDIATION-TEXT PATHSPEC GOTCHA (2026-07-22): the "commit only your own
files with an explicit pathspec" advice this guard prints on block is safe
for genuinely separate files, but was being followed for a co-mingled
single file (a hash-object + update-index surgical splice, per
reference_event_log_partial_commit_splice.md) where it is NOT safe:
`git commit -- <path>` re-reads the WORKING TREE for that path at commit
time regardless of what is staged in the index, silently discarding the
splice and re-sweeping the foreign hunks back in. Confirmed by a real
incident: a MEMORY.md single-line edit, staged correctly via
update-index --cacheinfo, was re-swept with another live session's four
unrelated hunks when committed via `git commit -m "..." -- MEMORY.md`
(commit 61facf4, amended to 62e5a35 once discovered). The remediation
text now carries this caveat inline; the correct sequence for a partial
same-file splice is update-index to stage only your content, then a BARE
`git commit -m "..."` with NO pathspec at all.

Stdlib only. ASCII-only. Windows (`python`).
"""

import json
import os
import re
import shlex
import subprocess
import sys
import time

LIB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib")
sys.path.insert(0, LIB_DIR)
# Guarded import (adversarial review, 2026-07-17): this guard's own SAFETY INVARIANT is
# "no information -> ALLOW" for missing/stale/unreadable DATA -- but an unguarded import
# is a different failure mode entirely. It crashes at MODULE LOAD, before main()'s first
# line runs, so it fires on EVERY Bash call in EVERY session -- not just git commits,
# since the traceback happens before is_git_commit()'s fast-path check is even reached.
# Reproduced: with commit_provenance.py absent, a plain `ls -la` (not a commit at all)
# tracebacks and exits 1. Degrading to an immediate allow on import failure keeps the
# guard's own documented invariant (missing information -> allow) without the system-wide
# traceback noise, and without silently blocking commits it was never meant to touch.
try:
    from commit_provenance import norm, sessions_dir, ttl_h, read_touched, TOUCHED_BASENAME  # noqa: E402,F401
    from session_liveness import other_active_sessions  # noqa: E402,F401
    PROVENANCE_CONTRACT_LOADED = True
except Exception:
    PROVENANCE_CONTRACT_LOADED = False

OVERRIDE_BASENAME = "allow-foreign-commit"

GIT_C_RE = re.compile(r"""\bgit\b\s+-C\s+(?:"([^"]+)"|'([^']+)'|([^\s&|;]+))""")
CD_RE = re.compile(r"""\bcd\s+(?:"([^"]+)"|'([^']+)'|([^\s&|;]+))\s*&&""")

# git global options that consume the NEXT token as a value (when not given
# as `--opt=value`), so that value must not be mistaken for the subcommand.
GIT_ARG_OPTS_WITH_VALUE = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path"}


def _first_group(m):
    return next((g for g in m.groups() if g), None) if m else None


def is_git_commit(cmd):
    """True iff `cmd` invokes git with `commit` as the SUBCOMMAND (tokenized,
    not a substring match -- `git add commit-provenance-guard.py` is not a
    commit)."""
    if not isinstance(cmd, str) or not cmd:
        return False
    if "--dry-run" in cmd:
        return False  # fixes no provenance
    try:
        tokens = shlex.split(cmd)
    except ValueError:
        tokens = cmd.split()
    n = len(tokens)
    i = 0
    while i < n:
        if tokens[i] != "git":
            i += 1
            continue
        j = i + 1
        while j < n:
            t = tokens[j]
            if t.startswith("-"):
                if t in GIT_ARG_OPTS_WITH_VALUE:
                    j += 2  # skip this option AND its value token
                else:
                    j += 1  # boolean flag or `--opt=value`
                continue
            # first non-option token after `git` is the subcommand
            if t == "commit":
                return True
            break
        i = j if j > i else i + 1
    return False


def _git_lines(repo, args):
    try:
        proc = subprocess.run(["git", "-C", repo] + args,
                              capture_output=True, text=True, timeout=5)
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
    out = _git_lines(d, ["rev-parse", "--show-toplevel"])
    return out[0] if out else None


def last_commit_time(repo, abs_path):
    """Epoch seconds of the most recent commit touching `abs_path` in `repo`,
    or None if it has never been committed (or git could not answer).

    BUG FIX (2026-07-20): `abs_path` is norm()-ed -- os.path.normcase'd, which
    lowercases the ENTIRE path on Windows. `git log -- <pathspec>` matches
    pathspecs literally against tree entries regardless of core.ignorecase
    (that setting governs index/worktree stat lookups, not history pathspec
    matching) -- so a lowercased pathspec silently fails (empty stdout, rc 0,
    no error) against any real path whose true on-disk casing has an uppercase
    character anywhere, in the filename OR any parent directory. Wrapping the
    pathspec in `:(literal,icase)` makes the match case-insensitive (and
    `literal` keeps any glob-metacharacters in the path from being
    reinterpreted). Verified: an unwrapped lowercased pathspec against
    C:\\Users\\...\\open-items-tracker.md returned nothing; the same path
    wrapped in `:(literal,icase)` returned the correct commit timestamp.
    """
    pathspec = ":(literal,icase)" + abs_path
    out = _git_lines(repo, ["log", "-1", "--format=%ct", "--", pathspec])
    if not out:
        return None
    try:
        return float(out[0])
    except ValueError:
        return None


def already_committed_since(repo, abs_path, touch_ts):
    """True iff `abs_path` was committed at or after `touch_ts` -- i.e. the
    content that was touched at `touch_ts` is provably already safe in HEAD.

    `touch_ts is None` means "unknown touch time" (old-format touched-files.txt
    line, or a hand-written entry): the conservative original behaviour, so
    this always returns False for it, matching the pre-fix "always a hit"
    outcome. A file that has NEVER been committed also returns False -- there
    is nothing in git history that could make it safe.

    ACCEPTED LIMITATION: trusts git's own commit timestamp (`%ct`), which
    `--date`/`GIT_COMMITTER_DATE` can set arbitrarily. A deliberately
    forward-dated commit could make an unsafe path look already-committed.
    Same threat model as the rest of this guard (single-operator cooperative
    fleet, not an adversarial boundary -- see the override sentinel, which is
    an even more direct bypass by design) -- not hardened against."""
    if touch_ts is None:
        return False
    ct = last_commit_time(repo, abs_path)
    if ct is None:
        return False
    return ct >= touch_ts


def _has_all_flag(cmd):
    """True for `-a`, `-am`, `--all`. False for `-m` and `--amend`
    (`^-[a-zA-Z]+$` cannot match a double-dash flag)."""
    try:
        tokens = shlex.split(cmd)
    except Exception:
        tokens = cmd.split()
    for t in tokens:
        if t == "--all":
            return True
        if re.match(r"^-[a-zA-Z]+$", t) and "a" in t:
            return True
    return False


SHELL_SEGMENT_OPERATORS = {"&&", "||", ";", "|"}

# A leading `NAME=value` token (env-var-prefixed invocation, e.g.
# `GIT_AUTHOR_NAME=x git add foo`) must not stop `git` from being recognized
# as the segment's actual command. REFUTE finding, 2026-07-24: without this,
# an env-var-prefixed `git add` was silently invisible to the detector below,
# reproducing the exact incident this fix exists to close.
_ENV_ASSIGN_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")


def _split_segments(tokens):
    """Split a flat token stream into sub-command segments at top-level shell
    control operators. shlex.split does not treat `&&`/`;`/`||`/`|` as syntax
    -- when whitespace-separated they simply come through as their own plain
    tokens (verified: is_git_commit() above already relies on exactly this to
    find `git` anywhere in a `cd /x && git commit ...` chain). This does not
    handle subshells, command substitution, or operators glued to a token
    with no surrounding whitespace -- accepted, same precision-over-recall
    scope as the rest of this file."""
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


def _tokenize_cmd_segments(cmd):
    """Tokenize `cmd` LINE BY LINE, not as one shlex.split() call, so a bare
    newline (bash's statement separator, same semantics as `;`) also acts as
    a segment boundary. REFUTE finding, 2026-07-24: shlex.split() treats a
    newline as ordinary whitespace, so a multi-line script with `git add` on
    one physical line and `git commit` on the next -- no `&&`/`;` between
    them -- was silently merged into one token stream, hiding the add behind
    whatever preceded it. Each line is independently run through
    _split_segments() too, since operators can still appear within a line.
    A line that fails to tokenize (e.g. an unterminated quote spanning
    physical lines) falls back to a plain whitespace split for that line only
    -- consistent with every other shlex-fallback in this file.

    ACCEPTED GAP (2nd-round REFUTE finding, 2026-07-24, LOW, fails SAFE):
    per-line tokenization loses quote context across lines, so a multi-line
    `-m "$(cat <<'EOF' ...)"` heredoc commit-message BODY whose own prose
    happens to start a line with the literal words "git add ..." can be
    mistaken for a real add segment (whole-command single-shlex.split(), as
    is_git_commit() and the `--`-pathspec branch below still use, would keep
    that heredoc body as one opaque quoted token and never see this). Verified
    this can only ever ADD a spurious candidate, never hide a real one -- and
    per _git_add_segments()'s "needs a commit segment strictly after it" rule,
    it only bites when 2+ `git commit` invocations are chained in one Bash
    call with the phantom line inside a MIDDLE commit's heredoc body and a
    real commit after it. This fleet's convention is one commit per Bash
    call (every commit in this repo's own history is issued that way) --
    accepted rather than fixed; fixing precisely would need re-tokenizing the
    whole command with quote context preserved and then splitting the
    resulting stream on segment operators/newlines, which bash's real
    heredoc/quote grammar cannot be fully represented by shlex.split() alone
    anyway. Same "single-operator cooperative fleet, not an adversarial
    boundary" threat model already used for the alias-blindness gap above."""
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
    (subcommand, args-after-subcommand). Else None. Skips global git options
    that consume a value, same table as is_git_commit()."""
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


def _git_add_segments(cmd):
    """arg-lists for every `git add ...` invocation in `cmd` that has AT
    LEAST ONE `git commit` invocation somewhere after it (positionally, left
    to right across segments -- matches execution order for &&/;/||/newline).

    NOT simply "before the FIRST commit": a multi-commit sequence in one
    command (`git commit -m first; git add sandwiched.txt; git commit -m
    second`) has an add that a "stop at the first commit" rule would drop
    entirely, even though it plainly gets staged for the SECOND commit
    (REFUTE finding, 2026-07-24, PoC 3). Conversely an add with NO commit
    anywhere after it (`git commit -m x && git add later.txt`) is correctly
    excluded -- nothing in this command ever commits it.

    ACCEPTED GAP (REFUTE finding, 2026-07-24, LOW): a user-defined git ALIAS
    for `add` or `commit` (e.g. `git config alias.a add`) is invisible here
    -- this matches only the literal subcommand text `add`/`commit`, same as
    is_git_commit()'s own alias blindness elsewhere in this file. Fixing one
    without the other would be inconsistent and misleading; same threat
    model as already_committed_since()'s documented stance: single-operator
    cooperative fleet, not an adversarial boundary, not hardened against."""
    segs = _tokenize_cmd_segments(cmd)
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
    running `git add` -- PreToolUse fires before the real command executes,
    so at hook-fire time the index is still whatever it was before this add.
    We instead query the pre-add working-tree state (git diff / ls-files)
    that the pending add is about to consume.

    THE BUG THIS CLOSES (2026-07-24): candidate_paths() previously read only
    `git diff --cached`, which is empty for a `git add X && git commit`
    one-liner at hook-fire time -- `if not cands: return` then allowed the
    commit before foreign_hits() was ever consulted. Confirmed as the
    mechanism behind a real incident: 4 janitor commits of exactly this shape
    swept 41 files, including two other live sessions' uncommitted edits,
    with commit-provenance-guard never firing despite every OTHER
    precondition for a block being met. See event_log.md 2026-07-24.

    Degrades toward FEWER candidates on any git-query failure (an unreadable
    dir, a repo mid-something) -- consistent with this guard's fail-open
    safety invariant: missing information biases toward allow, never block.
    `-u`/`--update` is treated as an alias for `-A` here -- it actually stages
    a narrower set (modified+deleted TRACKED files only, no untracked) but
    over-inclusion in a candidate SET can only ever widen who gets flagged as
    possibly-foreign, never cause a false allow; a caller who hits a false
    block from this over-approximation has the pathspec/override remediation
    the guard already prints."""
    add_arglists = _git_add_segments(cmd)
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
        modified = _git_lines(repo, ["diff", "--name-only"]) or []
        untracked = _git_lines(repo, ["ls-files", "--others", "--exclude-standard"]) or []
        paths |= {norm(os.path.join(repo, p)) for p in modified}
        paths |= {norm(os.path.join(repo, p)) for p in untracked}

    for p in explicit:
        abs_p = os.path.join(repo, p)
        if os.path.isdir(abs_p):
            scoped_mod = _git_lines(repo, ["diff", "--name-only", "--", p]) or []
            scoped_unt = _git_lines(
                repo, ["ls-files", "--others", "--exclude-standard", "--", p]) or []
            paths |= {norm(os.path.join(repo, x)) for x in scoped_mod}
            paths |= {norm(os.path.join(repo, x)) for x in scoped_unt}
        else:
            paths.add(norm(abs_p))

    return paths


def candidate_paths(repo, cmd):
    """Absolute normcase paths this commit would capture, or None if unknown."""
    # Explicit `-- <pathspec>` narrows the commit. This branch is load-bearing:
    # the block message tells the user to use a pathspec, so it MUST work.
    # Tokenize rather than regex-search for " -- " -- a `-- ` sequence inside
    # a quoted `-m` commit message (e.g. -m "foo -- bar") is NOT a standalone
    # `--` token and must not be mistaken for the pathspec separator.
    try:
        tokens = shlex.split(cmd)
    except ValueError:
        tokens = cmd.split()
    if "--" in tokens:
        idx = tokens.index("--")
        given = tokens[idx + 1:]
        return {norm(os.path.join(repo, p)) for p in given if p}

    staged = _git_lines(repo, ["diff", "--cached", "--name-only"])
    if staged is None:
        return None
    rel = set(staged)
    if _has_all_flag(cmd):
        tracked = _git_lines(repo, ["diff", "--name-only"]) or []
        rel |= set(tracked)
    cands = {norm(os.path.join(repo, p)) for p in rel}
    # Compound-command blind spot fix (2026-07-24): a `git add` PRECEDING this
    # commit in the same command hasn't run yet at hook-fire time, so it can't
    # show up in `git diff --cached` -- union in what it's about to stage.
    cands |= pending_add_paths(repo, cmd)
    return cands


def foreign_hits(candidates, my_sid, repo):
    """[(path, other_sid, status)] for candidates owned by ANOTHER LIVE session
    whose recorded touch has NOT already been safely committed.

    Requires THREE affirmative signals per hit: the other session is
    affirmatively reported open by session_liveness, AND its touched-set is
    within TTL, AND the path's last commit is not already at-or-after that
    session's recorded touch time for it (see already_committed_since()). Any
    read failure, missing file, or stale set is treated as NO INFORMATION and
    yields no hit -- never a block. This is session_liveness.py's documented
    contract, and it is what makes this guard fail-open by construction.
    """
    try:
        live = other_active_sessions(my_sid) or []
    except Exception:
        return []  # no information -> allow
    if not live:
        return []
    cutoff = time.time() - ttl_h() * 3600.0
    base = sessions_dir()
    hits = []
    for entry in live:
        sid = (entry or {}).get("sid")
        if not sid or sid == my_sid:
            continue
        path = os.path.join(base, sid, TOUCHED_BASENAME)
        try:
            if not os.path.exists(path):
                continue
            with open(path, encoding="utf-8") as fh:
                touched = read_touched(fh)  # {norm_path: last_touch_ts | None}
        except Exception:
            continue  # unreadable -> no information -> no hit
        for p in sorted(candidates & set(touched)):
            # BUG FIX (2026-07-20): TTL must be evaluated per-entry, off this
            # path's OWN touch_ts, not off touched-files.txt's whole-file
            # mtime. A live session that keeps touching OTHER paths keeps
            # rewriting (and re-mtime-ing) the same file, which kept THIS
            # entry looking fresh indefinitely even when its own touch was
            # days stale -- the file mtime and an individual entry's recency
            # are different things. An unknown touch_ts (old-format line) has
            # no per-path timestamp to age -- per commit_provenance.py's own
            # documented contract, it stays "just touched" (never ages out),
            # the same conservative default already_committed_since() uses.
            ts = touched[p]
            if ts is not None and ts < cutoff:
                continue  # this specific touch aged out -- not a hit
            if already_committed_since(repo, p, ts):
                continue  # provably already safe -- not a hit
            hits.append((p, sid, (entry.get("status") or "")))
    return hits


def main():
    payload = json.loads(sys.stdin.read())
    if not isinstance(payload, dict):
        return
    if not PROVENANCE_CONTRACT_LOADED:
        return  # no information -> allow (see the import guard above)
    tool_input = payload.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        return
    cmd = tool_input.get("command")
    if not is_git_commit(cmd):
        return  # fast path: not a commit -> no git calls at all

    repo = repo_root(cmd, payload.get("cwd") or "")
    if not repo:
        return  # not a repo we can resolve -> allow
    cands = candidate_paths(repo, cmd)
    if not cands:
        return  # nothing to commit, or unknown -> allow

    session_id = payload.get("session_id")
    if not isinstance(session_id, str) or not session_id:
        session_id = "nosession"

    # Deliberate backlog-landing (the c0272bb janitor workflow) stays possible.
    if os.path.exists(os.path.join(sessions_dir(), session_id, OVERRIDE_BASENAME)):
        return

    hits = foreign_hits(cands, session_id, repo)
    if not hits:
        return

    shown = hits[:5]
    detail = "\n".join(
        "  - %s  (edited by session %s%s)"
        % (os.path.basename(p), sid[:8], (" -- " + st) if st else "")
        for p, sid, st in shown
    )
    more = "" if len(hits) <= 5 else "\n  ... and %d more" % (len(hits) - 5)
    reason = (
        "This `git commit` would capture %d file(s) that ANOTHER LIVE SESSION "
        "edited:\n%s%s\n\n"
        "Committing them here attributes their work to you and can strand or "
        "clobber it (2026-07-16: a staged edit was swept into another session's "
        "commit inside a 30s window). Two ways forward:\n"
        "  1. Commit only your own SEPARATE files with an explicit pathspec:\n"
        "     git commit -m \"...\" -- <your/file> <your/other-file>\n"
        "     CAVEAT (confirmed 2026-07-22): if a flagged file itself is\n"
        "     co-mingled with your own partial edit (you want only SOME of\n"
        "     its content), this pathspec form does NOT help -- `git commit\n"
        "     -- <path>` re-reads the WORKING TREE for that path at commit\n"
        "     time and silently discards any surgical index stage, sweeping\n"
        "     the foreign hunks back in. For that case use hash-object +\n"
        "     update-index to stage just your content, then a BARE `git\n"
        "     commit -m \"...\"` with NO pathspec (see\n"
        "     reference_event_log_partial_commit_splice.md).\n"
        "  2. If you are DELIBERATELY landing another session's orphaned work, "
        "declare it:\n"
        "     touch \"%s\"\n"
        % (len(hits), detail, more,
           os.path.join(sessions_dir(), session_id, OVERRIDE_BASENAME).replace("\\", "/"))
    )
    sys.stderr.write("BLOCKED (commit-provenance-guard): " + reason + "\n")
    sys.exit(2)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise  # a real block (exit 2) must propagate
    except Exception:
        pass  # fail open: any internal error must never block a tool call
    sys.exit(0)
