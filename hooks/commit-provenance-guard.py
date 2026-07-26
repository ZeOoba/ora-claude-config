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

COMMAND PARSING EXTRACTED (2026-07-24): the shell-tokenizing and candidate-path
half of this file now lives in lib/git_commit_parse.py, unchanged, so that
eos-review-gate.py -- a second PreToolUse(Bash) gate that must answer the same
two questions before a commit runs -- inherits every fix catalogued above instead
of re-learning them from a divergent copy. The incident history for each fix
stays here, where it happened; the code is shared. hooks/tests/test-commit-provenance-guard.py
is the regression proof that the move changed no behaviour.

Stdlib only. ASCII-only. Windows (`python`).
"""

import json
import os
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
    # Re-exported deliberately: hooks/tests/test-commit-provenance-guard.py loads
    # this module by path and calls is_git_commit/candidate_paths/repo_root/
    # find_commit_segment on it directly, so they must remain attributes of THIS
    # module after the extraction.
    from git_commit_parse import (  # noqa: E402,F401
        candidate_paths, find_commit_segment, git_lines, has_all_flag, is_git_commit,
        pending_add_paths, repo_root,
    )
    PROVENANCE_CONTRACT_LOADED = True
except Exception:
    PROVENANCE_CONTRACT_LOADED = False

OVERRIDE_BASENAME = "allow-foreign-commit"

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
    out = git_lines(repo, ["log", "-1", "--format=%ct", "--", pathspec])
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
