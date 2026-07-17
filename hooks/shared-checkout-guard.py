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

DELIVERY (fixed 2026-07-16 -- this hook was silently useless to the agent for 7
days). v1 emitted ONLY `systemMessage` + stderr. Per the PreToolUse contract,
`systemMessage` is "shown to the USER" and is NEVER injected into the model's
context; and stderr is fed to Claude ONLY on exit 2 (a block), while this hook
exits 0 by design. Net: from 2026-07-09 it fired correctly ~168 times across
sessions while the agent it exists to steer received nothing. Found 2026-07-16
when a session hit two shared-file collisions in one hour, caught BOTH by manual
mtime inspection, and got no hook warning -- then reproduced it directly (marker
written 20:08:43, zero warning surfaced). Fix: also emit
`hookSpecificOutput.additionalContext`, the only PreToolUse field that is both
model-visible and non-blocking. Verified end-to-end: the warning landed in the
agent's context on the very Edit that applied this fix. Do NOT "simplify" this
back to systemMessage-only.

Why `permissionDecision: "allow"` is SAFE here and does NOT weaken anything
(verified 2026-07-16 against the docs AND empirically -- do not "harden" it away):
  * It cannot grant permission. Per permissions.md: "Hook decisions don't bypass
    permission rules. Claude Code evaluates deny and ask rules regardless of what
    a PreToolUse hook returns: a matching deny rule blocks the call, and a
    matching ask rule still prompts even when the hook returned 'allow'."
  * It does not short-circuit later hooks. All matching PreToolUse hooks run and
    deny wins. Proven live: with this hook (#6 in settings.json) returning "allow",
    registry-write-guard (#7) still blocked a registry write.
  * `permissionDecision` is REQUIRED in hookSpecificOutput -- it cannot be omitted.
    "defer" would be the semantic no-op, but whether additionalContext is still
    delivered under "defer" is UNDOCUMENTED, so "allow" is the supported shape.

SAFETY INVARIANT: warn-only. It NEVER denies a tool call (permissionDecision is
always "allow" -- never "deny"/"ask"), and the whole body is wrapped in
try/except -- on ANY error it prints nothing and exits 0 (ALLOW). A bug here must
never block or slow an edit.

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
    # Delivery (fixed 2026-07-16 -- see DELIVERY note in the module docstring):
    #   systemMessage     -> the USER (transcript warning). Never reaches the model.
    #   additionalContext -> CLAUDE. The ONLY PreToolUse field that is both
    #                        model-visible AND decoupled from blocking.
    #   permissionDecision "allow" -> explicit non-block, preserving the warn-only
    #                        SAFETY INVARIANT above (never deny, never ask).
    #   stderr            -> debug log only on exit 0 (PreToolUse feeds stderr to
    #                        Claude ONLY on exit 2, which would block). Kept as a
    #                        breadcrumb, NOT relied on as the delivery channel.
    sys.stdout.write(json.dumps({
        "systemMessage": msg,
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "additionalContext": msg,
        },
    }))
    sys.stderr.write(msg + "\n")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass  # fail open: warn-only must never block a tool call
    sys.exit(0)
