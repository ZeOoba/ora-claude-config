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
# Guarded import (adversarial review, 2026-07-17). This hook is warn-only -- it never
# blocks either way, so an unguarded import crashing here is not a security regression the
# way it was for ora-autonomy-gate.py. But it IS a reliability one: the crash happens at
# MODULE LOAD, before main()'s own try/except (below) or any Edit/Write-specific logic runs,
# so a broken session_liveness.py would traceback on EVERY Edit/Write/MultiEdit/Desktop
# Commander write across every session, not just ones this hook actually has something to
# say about. Same bug class, same fix, applied for reliability rather than security here.
try:
    from session_liveness import other_active_sessions  # noqa: E402,F401
except Exception:
    def other_active_sessions(_session_id):
        return []

# Provenance is what turns "a session is open" into "a session touched THESE files".
# Same guarded-import posture and same reason as above (warn-only hook: a missing
# module must degrade, never traceback on every write). Degrading here costs only
# attribution PRECISION -- _attribute_wip() then reports the WIP as unattributed,
# which is the honest answer when there is no evidence to attribute it with.
try:
    from commit_provenance import TOUCHED_BASENAME, read_touched  # noqa: E402,F401
    from commit_provenance import norm as prov_norm  # noqa: E402,F401
    PROVENANCE_LOADED = True
except Exception:
    PROVENANCE_LOADED = False
    TOUCHED_BASENAME = "touched-files.txt"

    def prov_norm(p):
        return _norm(p)  # resolved at call time; _norm is defined below

    def read_touched(_fh):
        return {}

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


def nearest_git_root(file_path):
    """The actual checkout that owns `file_path`: the nearest ancestor directory
    (walking upward from its parent) containing a `.git` entry, file or dir.

    BUG FIX (2026-07-24): find_repo() matches a file against a configured shared-repo
    ROOT by plain path-prefix, so a file living inside a LINKED WORKTREE NESTED under
    that root (e.g. a session isolation workspace at
    `<repo>/.claude/worktrees/<name>/...` -- exactly where EnterWorktree/`git worktree
    add` puts one for this very repo) still resolves `repo` to the OUTER shared root.
    The guard then asked "is the OUTER root a linked worktree?" (no -- it's the main
    checkout) and proceeded to warn about the outer checkout's dirty status, even
    though the file being edited sits in an already-isolated nested worktree. Observed
    live: every edit inside `.claude/worktrees/scg-attribution-test/` warned about
    `.claude`'s ~30 unrelated uncommitted changes -- noise at the exact moment the
    advice ("use an isolated worktree") had already been followed.

    Callers check is_linked_worktree()/is_main_checkout() against THIS return value,
    not against find_repo()'s match, so the isolation check reflects the file's real
    checkout rather than whichever configured root happened to prefix-match first.

    Returns None if no `.git` entry is found walking up to the filesystem root (should
    not happen for a path find_repo() already matched, but degrades to None -- callers
    then fall back to the outer repo match, preserving prior behavior instead of
    raising).
    """
    d = os.path.dirname(os.path.abspath(file_path))
    seen = set()
    while d and d not in seen:
        seen.add(d)
        if os.path.exists(os.path.join(d, ".git")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    return None


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


def _status_paths(repo, lines):
    """Absolute, provenance-normalized paths named by `git status --porcelain`.

    Porcelain v1 shape: 2 status chars + space + path. A rename/copy is
    `R  old -> new`; attribute the NEW path, since that is what exists on disk
    now. core.quotePath double-quotes non-ASCII paths, so unquote best-effort.
    Any unparseable line is skipped -- attribution is enrichment and is never
    worth raising inside a warn-only hook.
    """
    out = set()
    for ln in lines:
        if len(ln) < 4:
            continue
        rest = ln[3:].strip()
        if " -> " in rest:
            rest = rest.split(" -> ", 1)[1].strip()
        if len(rest) >= 2 and rest.startswith('"') and rest.endswith('"'):
            try:
                rest = json.loads(rest)
            except Exception:
                rest = rest[1:-1]
        if rest:
            out.add(prov_norm(os.path.join(repo, rest)))
    return out


def _sessions_touching(paths, others, sessions_dir):
    """[(sid, status)] for live sessions whose RECORDED touched-set intersects
    `paths`. Returns [] when provenance is unavailable or unreadable -- absence
    of evidence, which the caller reports as unattributed rather than guessing.
    """
    if not PROVENANCE_LOADED or not paths:
        return []
    found = []
    for entry in others:
        sid = (entry or {}).get("sid")
        if not sid:
            continue
        tf = os.path.join(sessions_dir, sid, TOUCHED_BASENAME)
        try:
            if not os.path.isfile(tf):
                continue
            with open(tf, encoding="utf-8") as fh:
                touched = read_touched(fh)
        except Exception:
            continue  # unreadable -> no evidence from this session
        if paths & set(touched):
            found.append((sid, entry.get("status") or ""))
    return found


def _attribute_wip(repo, lines, others, sessions_dir):
    """Evidence-based attribution clause, or an honest unattributed one.

    BUG FIX (2026-07-24): this used to name `others[0]` -- an ARBITRARY index
    into the liveness dict -- and assert it was "likely the source of this
    WIP", with nothing whatsoever tying that session to the dirty files.
    Observed live during the ora-deal-aging-sla run with ELEVEN sessions
    concurrently registered: it named the same session across ~8 consecutive
    warnings when that session had been idle for 16 minutes and had no
    provenance dir at all, while the session that actually made the commits
    went unnamed. A confidently WRONG name is worse than no name -- it sends
    the reader to reconcile with an uninvolved session and, worse, invites
    "that WIP is not mine" reasoning about files that are. See
    feedback_shared_checkout_guard_session_attribution_unreliable.md.

    Now a session is named ONLY when its own recorded touched-set intersects
    the dirty paths. With no such evidence the clause states how many other
    sessions are open and calls the WIP unattributed.
    """
    if not others:
        return ""
    hits = _sessions_touching(_status_paths(repo, lines), others, sessions_dir)
    if hits:
        who = ", ".join(
            "`%s`%s" % (sid[:8], (" (" + st + ")") if st else "")
            for sid, st in hits[:3])
        more = "" if len(hits) <= 3 else " and %d more" % (len(hits) - 3)
        verb = " has" if len(hits) == 1 else " have"
        return (" Session " + who + more + verb + " recorded edit(s) to file(s)"
                " in this dirty set -- reconcile with it before committing.")
    return (" " + str(len(others)) + " other session(s) are open, but none has"
            " a recorded edit to these files -- this WIP is UNATTRIBUTED."
            " Do not assume a specific session; check `git log -1` and"
            " `git status` yourself before committing.")


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

    # Check isolation against the file's OWN checkout, not the matched shared-repo
    # root -- see nearest_git_root()'s docstring. Falls back to `repo` if no `.git`
    # entry is found at all (preserves prior behavior instead of raising).
    own_root = nearest_git_root(file_path) or repo
    if is_linked_worktree(own_root):
        return  # already isolated -- good, stay silent (nested or top-level worktree)
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
    collision_note = _attribute_wip(repo, lines, others, sessions_dir)

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
