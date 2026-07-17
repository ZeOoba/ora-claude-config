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
blocks only on TWO affirmative signals: (a) a candidate file appears in another
session's touched-set, AND (b) session_liveness affirmatively reports that
session open, AND that set is within TTL. Missing/stale/unreadable data yields
"no information" -> ALLOW. This honours session_liveness.py's explicit contract
("ENRICHMENT ONLY, never a hard gate ... treat a read failure, or a stale/empty
result, the same as 'no information'"). NO LOCK IS EVER HELD, so a crashed
session cannot wedge the fleet -- the deadlock class does not exist here.
The same invariant now covers an IMPORT-time failure of either sibling module too
(2026-07-17): guarded at load, main() returns immediately if either failed to load.

Deliberately narrow (precision over recall, same philosophy as
registry-write-guard.py): it does NOT catch foreign files written by a script
rather than the Edit tool. That accepted false negative is what makes the guard
survivable -- the naive "block anything I did not touch" design would have
blocked 31ac61d, a legitimate script-generated commit.

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
    from commit_provenance import norm, sessions_dir, ttl_h, TOUCHED_BASENAME  # noqa: E402,F401
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
    return {norm(os.path.join(repo, p)) for p in rel}


def foreign_hits(candidates, my_sid):
    """[(path, other_sid, status)] for candidates owned by ANOTHER LIVE session.

    Requires TWO affirmative signals per hit: the other session is affirmatively
    reported open by session_liveness, AND its touched-set is within TTL. Any
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
            if not os.path.exists(path) or os.path.getmtime(path) < cutoff:
                continue
            with open(path, encoding="utf-8") as fh:
                touched = {ln.strip() for ln in fh if ln.strip()}  # dedupe on read
        except Exception:
            continue  # unreadable -> no information -> no hit
        for p in sorted(candidates & touched):
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

    hits = foreign_hits(cands, session_id)
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
        "  1. Commit only your own files with an explicit pathspec:\n"
        "     git commit -m \"...\" -- <your/file> <your/other-file>\n"
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
