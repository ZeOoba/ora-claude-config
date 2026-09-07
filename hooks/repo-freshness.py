#!/usr/bin/env python3
"""SessionStart hook — surface oxford-command-center git freshness (HEAD vs origin/main).

WHY: this repo lands multiple PRs/day across concurrent worktrees, so a local checkout
goes stale within hours. Reasoning from a stale `main` produced confidently-wrong claims
and a plan that told a builder to wait for already-merged work (2026-06-20). This injects
the live origin/main delta at session start so observation beats memory.

Read-only git ONLY (fetch + log + rev-list). Never touches the working tree, branches, or
HEAD. No-ops silently for any other repo or on ANY error — must never block session start.
"""
import sys
import os
import json
import subprocess

LIB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib")
sys.path.insert(0, LIB_DIR)
# Guarded import (same reliability posture as active-work-broadcast.py's own
# guarded claim_work.py import): a broken/missing git_probe_common.py must
# degrade to this file's ORIGINAL inline subprocess call, never crash a
# SessionStart hook.
try:
    from git_probe_common import git as _shared_git
except Exception:
    _shared_git = None


def emit(ctx: str) -> None:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": ctx,
        }
    }))


def main() -> None:
    raw = ""
    try:
        raw = sys.stdin.read()
    except Exception:
        pass

    cwd = ""
    try:
        if raw.strip():
            cwd = (json.loads(raw) or {}).get("cwd", "") or ""
    except Exception:
        cwd = ""
    if not cwd:
        cwd = os.getcwd()

    # Scope: this repo only (matches main checkout AND its .claude/worktrees/*).
    if "oxford-command-center" not in cwd.replace("\\", "/").lower():
        return  # silent no-op for every other repo — no network, no output

    def git(args, timeout=15):
        """stdout string. Uses the shared never-raise helper when it loaded;
        falls back to this file's original raising subprocess.run call
        otherwise -- both call sites below already wrap this in try/except,
        matching the original contract (raise on failure, caller swallows)."""
        if _shared_git is not None:
            _, out, _err = _shared_git(cwd, args, timeout=timeout)
            return out
        return subprocess.run(
            ["git", "-C", cwd] + args,
            capture_output=True, text=True, timeout=timeout,
        ).stdout

    # Refresh remote-tracking refs only (safe; never touches HEAD/branches/worktree).
    try:
        git(["fetch", "--quiet", "origin"], timeout=20)
    except Exception:
        pass  # offline/slow: fall back to last-known origin ref rather than failing

    try:
        log = git(["log", "--oneline", "-8", "origin/main"]).strip()
        counts = git(["rev-list", "--left-right", "--count", "HEAD...origin/main"]).strip()
    except Exception:
        return

    if not counts:
        return
    parts = counts.split()
    ahead = parts[0] if len(parts) > 0 else "?"
    behind = parts[1] if len(parts) > 1 else "?"

    stale = ""
    try:
        if int(behind) > 0:
            stale = (f"  WARNING: local checkout is {behind} commit(s) BEHIND origin/main — "
                     f"pull/rebase and trust origin/main + file contents before any repo-grounded "
                     f"claim or plan sequencing (this repo lands multiple PRs/day).")
    except Exception:
        pass

    ctx = (
        f"[oxford-command-center freshness] HEAD vs origin/main: "
        f"{ahead} ahead (local-only), {behind} behind (origin-only).{stale}\n"
        f"origin/main — last 8 commits:\n{log}"
    )
    emit(ctx)


if __name__ == "__main__":
    main()
