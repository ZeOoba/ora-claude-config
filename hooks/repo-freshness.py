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
        return subprocess.run(
            ["git", "-C", cwd] + args,
            capture_output=True, text=True, timeout=timeout,
        )

    # Refresh remote-tracking refs only (safe; never touches HEAD/branches/worktree).
    try:
        git(["fetch", "--quiet", "origin"], timeout=20)
    except Exception:
        pass  # offline/slow: fall back to last-known origin ref rather than failing

    try:
        log = git(["log", "--oneline", "-8", "origin/main"]).stdout.strip()
        counts = git(["rev-list", "--left-right", "--count", "HEAD...origin/main"]).stdout.strip()
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
