"""Shared-checkout hygiene guard -- PreToolUse hook for Edit|Write|MultiEdit.

WARNS (never blocks) when you edit a file in a shared-checkout repo's MAIN
checkout while that tree is dirty -- i.e., it holds uncommitted/untracked work
that may be another session's WIP. The nudge: claim an isolated worktree and
verify `git status` before committing, so you don't co-mingle another writer's
hunks (the contaminated-checkout hazard). Silent when you are already in a
linked worktree, when the tree is clean, or when the file is outside the shared
repos. Re-arms per repo whenever the repo-wide dirty-file set CHANGES (a
fingerprint of `git status --porcelain`, not just once-ever per session) --
so a second collision after the first warning is no longer silently swallowed.
When another Claude Code session is currently open (per
hooks/lib/session_liveness.py, itself a fail-open enrichment signal), the
warning names it specifically.

SAFETY INVARIANT: warn-only. It NEVER denies a tool call, and the whole body is
wrapped in try/except -- on ANY error it prints nothing and exits 0 (ALLOW).
A bug here must never block or slow an edit.

Stdlib only. ASCII-only. Windows (`python`).
"""

import hashlib
import json
import os
import subprocess
import sys

LIB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib")
sys.path.insert(0, LIB_DIR)
from session_liveness import other_active_sessions  # noqa: E402

DEFAULT_REPOS = [
    "C:/Users/Owner/oxford-command-center",
    "C:/Users/Owner/ora-skills",
    "C:/Users/Owner/.claude",
]
DEFAULT_SESSIONS_DIR = "C:/Users/Owner/.claude/hooks/sessions"


def _norm(p):
    return os.path.normcase(os.path.abspath(p))


def shared_repos():
    raw = os.environ.get("SHARED_CHECKOUT_REPOS")
    if raw:
        return [r for r in raw.split(os.pathsep) if r.strip()]
    return DEFAULT_REPOS


def find_repo(file_path, repos):
    fp = _norm(file_path)
    for r in repos:
        rn = _norm(r)
        if fp == rn or fp.startswith(rn + os.sep):
            return r
    return None


def is_linked_worktree(repo):
    # A linked worktree's .git is a FILE (gitdir pointer); a main checkout's is a DIR.
    return os.path.isfile(os.path.join(repo, ".git"))


def is_main_checkout(repo):
    return os.path.isdir(os.path.join(repo, ".git"))


def git_status_lines(repo):
    # Non-empty `git status --porcelain` lines for repo, or None on ANY
    # error (fail-open -> caller treats None as "nothing to warn about").
    try:
        proc = subprocess.run(
            ["git", "-C", repo, "status", "--porcelain"],
            capture_output=True, text=True, timeout=5,
        )
    except Exception:
        return None
    if proc.returncode != 0:
        return None
    return [ln for ln in proc.stdout.splitlines() if ln.strip()]


def status_fingerprint(lines):
    # Stable hash of the repo-wide dirty-file set, used to re-arm the
    # per-session warning when the dirty set changes (not just once-ever).
    joined = "\n".join(sorted(lines))
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:16]


def main():
    payload = json.loads(sys.stdin.read())
    if not isinstance(payload, dict):
        return

    tool_input = payload.get("tool_input") or {}
    file_path = tool_input.get("file_path")
    if not isinstance(file_path, str) or not file_path:
        return
    session_id = payload.get("session_id")
    if not isinstance(session_id, str) or not session_id:
        session_id = "nosession"

    repo = find_repo(file_path, shared_repos())
    if repo is None:
        return  # fast path: not a shared-checkout repo -> no git call at all

    if is_linked_worktree(repo):
        return  # already isolated -- good, stay silent
    if not is_main_checkout(repo):
        return  # not a git checkout we recognize -- fail-open

    lines = git_status_lines(repo)
    if not lines:
        return  # clean, or git error -- nothing to nudge about

    fp = status_fingerprint(lines)

    sessions_dir = os.environ.get("SHARED_CHECKOUT_SESSIONS_DIR") or DEFAULT_SESSIONS_DIR
    sess_dir = os.path.join(sessions_dir, session_id)
    repo_key = os.path.basename(repo.rstrip("/\\")) or "repo"
    marker = os.path.join(sess_dir, "shared-checkout-warned-" + repo_key)

    prev_fp = None
    if os.path.exists(marker):
        try:
            with open(marker, "r", encoding="ascii") as fh:
                prev_fp = fh.read().strip()
        except Exception:
            prev_fp = None
    if prev_fp == fp:
        return  # same dirty-set already warned about this session -- stay silent

    try:
        os.makedirs(sess_dir, exist_ok=True)
        with open(marker, "w", encoding="ascii") as fh:
            fh.write(fp)
    except Exception:
        pass  # marker is best-effort; still warn

    n = len(lines)
    others = other_active_sessions(session_id)
    if others:
        who = others[0]["sid"][:8]
        status = others[0].get("status") or ""
        collision_note = (" Session `" + who + "` is open right now" +
                          (" (" + status + ")" if status else "") +
                          " -- likely the source of this WIP.")
    else:
        collision_note = ""

    msg = (
        "Shared-checkout hygiene: the " + repo_key + " MAIN checkout has " + str(n) +
        " uncommitted change(s) that may be another session's WIP." + collision_note +
        " Editing here risks co-mingling their hunks. Consider an isolated worktree "
        "(npm run worktree / EnterWorktree) and verify `git status` before committing."
    )
    # Non-blocking warning: `systemMessage` surfaces to the user; stderr is a fallback.
    sys.stdout.write(json.dumps({"systemMessage": msg}))
    sys.stderr.write(msg + "\n")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass  # fail open: warn-only must never block a tool call
    sys.exit(0)
