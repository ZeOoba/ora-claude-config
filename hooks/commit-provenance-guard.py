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

LIB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib")
sys.path.insert(0, LIB_DIR)
from commit_provenance import norm, sessions_dir, ttl_h, TOUCHED_BASENAME  # noqa: E402

# `git ... commit` within one shell segment (no |, ;, & between them).
GIT_COMMIT_RE = re.compile(r"\bgit\b[^|;&]*\bcommit\b")
GIT_C_RE = re.compile(r"""\bgit\b\s+-C\s+(?:"([^"]+)"|'([^']+)'|([^\s&|;]+))""")
CD_RE = re.compile(r"""\bcd\s+(?:"([^"]+)"|'([^']+)'|([^\s&|;]+))\s*&&""")


def _first_group(m):
    return next((g for g in m.groups() if g), None) if m else None


def is_git_commit(cmd):
    if not isinstance(cmd, str) or not cmd:
        return False
    if "--dry-run" in cmd:
        return False  # fixes no provenance
    return bool(GIT_COMMIT_RE.search(cmd))


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
    m = re.search(r"\s--\s+(.+)$", cmd)
    if m:
        try:
            given = shlex.split(m.group(1))
        except Exception:
            given = m.group(1).split()
        return {norm(os.path.join(repo, p)) for p in given if p}

    staged = _git_lines(repo, ["diff", "--cached", "--name-only"])
    if staged is None:
        return None
    rel = set(staged)
    if _has_all_flag(cmd):
        tracked = _git_lines(repo, ["diff", "--name-only"]) or []
        rel |= set(tracked)
    return {norm(os.path.join(repo, p)) for p in rel}


def main():
    payload = json.loads(sys.stdin.read())
    if not isinstance(payload, dict):
        return
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
    # Task 3 adds the foreign-hit check here.
    return


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise  # a real block (exit 2) must propagate
    except Exception:
        pass  # fail open: any internal error must never block a tool call
    sys.exit(0)
