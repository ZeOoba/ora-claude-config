"""Shared-checkout hygiene guard -- PreToolUse hook for Edit|Write|MultiEdit.

WARNS (never blocks) when you edit a file in a shared-checkout repo's MAIN
checkout while that tree is dirty -- i.e., it holds uncommitted/untracked work
that may be another session's WIP. The nudge: claim an isolated worktree and
verify `git status` before committing, so you don't co-mingle another writer's
hunks (the contaminated-checkout hazard). Silent when you are already in a
linked worktree, when the tree is clean, or when the file is outside the shared
repos. Warns once per session per repo -- a nudge, not spam.

SAFETY INVARIANT: warn-only. It NEVER denies a tool call, and the whole body is
wrapped in try/except -- on ANY error it prints nothing and exits 0 (ALLOW).
A bug here must never block or slow an edit.

SHARED_CHECKOUT_REPOS override is split on os.pathsep: ';' on Windows,
':' on Linux (e.g. SHARED_CHECKOUT_REPOS=~/repoA:~/repoB).

Stdlib only. ASCII-only. Cross-platform (`python3`/`python`).
"""

import json
import os
import subprocess
import sys

if os.name == "nt":
    DEFAULT_REPOS = [
        "C:/Users/Owner/oxford-command-center",
        "C:/Users/Owner/ora-skills",
    ]
else:
    DEFAULT_REPOS = [
        os.path.expanduser("~/oxford-command-center"),
        os.path.expanduser("~/ora-skills"),
    ]
DEFAULT_SESSIONS_DIR = os.path.expanduser("~/.claude/hooks/sessions")


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


def dirty_count(repo):
    # Number of `git status --porcelain` lines, or 0 on ANY error (fail-open -> no warn).
    try:
        proc = subprocess.run(
            ["git", "-C", repo, "status", "--porcelain"],
            capture_output=True, text=True, timeout=5,
        )
    except Exception:
        return 0
    if proc.returncode != 0:
        return 0
    return len([ln for ln in proc.stdout.splitlines() if ln.strip()])


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

    # Dedupe: warn at most once per session per repo.
    sessions_dir = os.environ.get("SHARED_CHECKOUT_SESSIONS_DIR") or DEFAULT_SESSIONS_DIR
    sess_dir = os.path.join(sessions_dir, session_id)
    repo_key = os.path.basename(repo.rstrip("/\\")) or "repo"
    marker = os.path.join(sess_dir, "shared-checkout-warned-" + repo_key)
    if os.path.exists(marker):
        return

    n = dirty_count(repo)
    if n <= 0:
        return  # clean -- nothing to nudge about

    try:
        os.makedirs(sess_dir, exist_ok=True)
        with open(marker, "w", encoding="ascii") as fh:
            fh.write("warned")
    except Exception:
        pass  # marker is best-effort; still warn

    msg = (
        "Shared-checkout hygiene: the " + repo_key + " MAIN checkout has " + str(n) +
        " uncommitted change(s) that may be another session's WIP. Editing here risks "
        "co-mingling their hunks. Consider an isolated worktree (npm run worktree / "
        "EnterWorktree) and verify `git status` before committing. (warn once/session)"
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
