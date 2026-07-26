#!/usr/bin/env python3
"""SessionStart hook -- broadcast any live cross-session claims on shared ~/.claude
subsystems (hooks-override-auth, open-items-tracker, oxford-command-center-data, and
any other slug a session chooses to claim -- see hooks/lib/claim_work.py).

WHY: reference_concurrent_session_duplicate_hardening_work.md logs 6 recorded
collisions where two sessions independently duplicated work on the same shared
subsystem, discovered only by chance (git worktree list) or not at all until both had
sunk real work. The existing mitigation was a MANUAL pre-check the agent has to
remember to run. This makes the signal automatic: if another session has claimed a
subsystem within the last 2 hours, the starting session sees it immediately, the same
way hooks/repo-freshness.py (this hook's template) auto-surfaces oxford-command-center
git staleness instead of relying on the agent to remember `git fetch`.

DELIVERY: emits ONLY via hookSpecificOutput.additionalContext, never systemMessage --
per reference_hook_systemmessage_not_model_visible.md, systemMessage is user-visible
but INVISIBLE to the model, so a hook meant to steer agent behavior that used
systemMessage alone would silently do nothing useful (measured elsewhere in this
codebase: shared-checkout-guard.py fired 168 times over 7 days with zero effect before
that exact defect was found and fixed 2026-07-16). Do not "simplify" this to
systemMessage.

SAFETY: read-only, warn-only. Never blocks session start. Excludes the starting
session's own claims (a session re-reading its own prior claim is not a collision).
No-ops silently (prints nothing) when there are no other live claims, when the claims
directory doesn't exist yet, or on any error -- must never fail session start.

Stdlib only. ASCII-only. Windows (`python`).
"""
import json
import os
import sys

LIB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib")
sys.path.insert(0, LIB_DIR)
# Guarded import (same reliability rationale as shared-checkout-guard.py's guarded
# import of session_liveness: a broken claim_work.py must not crash this hook at
# MODULE LOAD, before main()'s own try/except runs, on every single session start).
try:
    from claim_work import read_active_claims  # noqa: E402
except Exception:
    def read_active_claims(**_kwargs):
        return []


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

    own_sid = ""
    try:
        if raw.strip():
            own_sid = (json.loads(raw) or {}).get("session_id", "") or ""
    except Exception:
        own_sid = ""

    try:
        claims = read_active_claims()
    except Exception:
        return

    others = [c for c in claims if c.get("session_id") != own_sid]
    if not others:
        return  # nothing live, or the only live claim(s) are this session's own

    lines = [
        "[cross-session claims] other session(s) have active claims on shared "
        "~/.claude subsystems -- check before independently duplicating this work "
        "(see reference_concurrent_session_duplicate_hardening_work.md):",
    ]
    for c in others:
        lines.append("- %s: session %s claimed %.0fm ago -- %s" % (
            c.get("slug", "?"),
            str(c.get("session_id", "?"))[:8],
            c.get("age_minutes", 0.0),
            c.get("description") or c.get("title") or "(no description)",
        ))
    emit("\n".join(lines))


if __name__ == "__main__":
    main()
