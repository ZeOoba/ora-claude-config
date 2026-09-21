"""Worktree-isolation guard -- PreToolUse hook, matcher: Bash.

BLOCKS a `git commit` that lands BLAST-RADIUS paths in the MAIN checkout of a shared ORA
repo. The same commit from a linked worktree is allowed. This is CLAUDE.md's own rule --
"Shared-checkout = SINGLE-WRITER before editing any shared single-instance file/repo under
~/.claude ... isolate via a worktree" -- moved from doctrine into enforcement.

WHY IT EXISTS (OI-252): commit-hygiene-guard.py has WARNED about branch identity since
2026-08-09 and the warning is demonstrably read past -- OI-247 (2026-09-08: a CLAUDE.md
change bypassed its own claimed worktree+PR process), and the live checkout on 2026-09-10
(HEAD parked on a feature branch, 29 ahead / 84 behind origin/main, 77 dirty paths, 6
linked worktrees).

WHY A SEPARATE FILE RATHER THAN A FLAG ON commit-hygiene-guard: that guard's SAFETY
INVARIANT (:42) fixes it as "warn-only, fail-open BY CONSTRUCTION", and :70-73 records that
its detection deliberately OMITS adversarial tearing defence *because* it only prints. A
blocking gate must not rest on detection built for advisories. That invariant is asserted
behaviourally by tests/test-worktree-isolation-guard.py check 14.

DESIGN HISTORY -- REPLACES A SESSION-STATE DESIGN KILLED BY REFUTE (2026-09-10). The first
implementation blocked when the destination branch differed from one recorded on the
session's first commit. An adversarial pass found four HIGH defects, all inherent to that
premise: the record was keyed per session rather than per (session, repo); "established"
was never modelled, so `git checkout -b` and even `git worktree add -b` -- this guard's own
remediation -- false-blocked; and a session whose first commit landed on the parked peer
branch recorded THAT as canonical, inverting on the exact case the guard existed for. The
worktree signal needs NO state, so that whole failure class is structurally gone.

SAFETY INVARIANT -- fail-open BY CONSTRUCTION. Blocks only on THREE affirmative signals:
  (a) the commit candidate set contains a root-anchored blast-radius path, AND
  (b) the repo is a MAIN checkout, not a linked worktree, AND
  (c) the repo root is one of the ORA shared checkouts.
Any missing, unresolvable or unreadable signal yields "no information" -> ALLOW. No lock is
ever held. Every git call is timeout-bounded (a shared checkout with several worktrees can
contend on index.lock; peers cap at 5-8s and so does this).

BLOCKING CONTRACT: main() calls sys.exit(2) directly. It must NEVER merely `return` a
non-zero code -- pretooluse-dispatcher runs guards IN-PROCESS first and reads rc only from
SystemExit, so a returned value is silently discarded and the commit proceeds while
"BLOCKED" sits unread in stderr. That defect shipped in this guard's first draft and was
caught only by refute; test "C1" pins it via the dispatcher path.

SIGNAL (a) IS ROOT-ANCHORED, deliberately: eos-review-gate.py:271-276 records reverting a
substring `hooks/` match because it flagged idiomatic `src/hooks/useX.ts`. Same rule here.

OVERRIDE: allow-shared-checkout-commit, 60 min, multi-use -- same shape as
allow-config-write (config-write-guard.py:131).
"""
import importlib.util
import json
import os
import subprocess
import sys

HOOKS_DIR = os.path.dirname(os.path.abspath(__file__))
GUARD_NAME = "worktree-isolation-guard"
OVERRIDE_BASENAME = "allow-shared-checkout-commit"
GIT_TIMEOUT = 8

# ORA's shared single-instance checkouts (CLAUDE.md single-writer rule). The env var is a
# TEST SEAM ONLY -- it must never be set in settings.json or a scheduled-task context.
DEFAULT_SHARED_ROOTS = (
    r"C:\Users\Owner\.claude",
    r"C:\Users\Owner\ora-skills",
    r"C:\Users\Owner\website-canonical",
    r"C:\Users\Owner\oxford-command-center",
)

# Root-anchored blast-radius rules. First path segment, or an exact basename at any depth
# for the named single-instance files.
BLAST_TOP_DIRS = ("hooks",)
BLAST_BASENAMES = (
    "settings.json", "settings.local.json", "claude.md",
    "confidential-terms.json", "confidential-repos.json", "scheduled-tasks.json",
)

_parse = None
_override_tokens = None
try:
    sys.path.insert(0, os.path.join(HOOKS_DIR, "lib"))
    import git_commit_parse as _parse
except Exception:
    _parse = None
try:
    import override_tokens as _override_tokens
except Exception:
    _override_tokens = None


def _shared_roots():
    raw = os.environ.get("WORKTREE_ISOLATION_SHARED_ROOTS")
    roots = raw.split(os.pathsep) if raw else list(DEFAULT_SHARED_ROOTS)
    out = []
    for r in roots:
        r = r.strip()
        if not r:
            continue
        try:
            out.append(os.path.normcase(os.path.abspath(r)))
        except Exception:
            continue
    return out


def _git(repo, *args):
    env = dict(os.environ)
    for v in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR",
              "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_PREFIX"):
        env.pop(v, None)
    return subprocess.run(("git",) + args, cwd=repo, capture_output=True, text=True,
                          env=env, timeout=GIT_TIMEOUT)


def _repo_root(cwd):
    try:
        r = _git(cwd, "rev-parse", "--show-toplevel")
    except Exception:
        return None
    if r.returncode != 0:
        return None
    top = (r.stdout or "").strip()
    return top or None


def _is_linked_worktree(repo):
    """True when this checkout is a LINKED worktree. Unresolvable -> None (no info)."""
    try:
        a = _git(repo, "rev-parse", "--git-dir")
        b = _git(repo, "rev-parse", "--git-common-dir")
    except Exception:
        return None
    if a.returncode != 0 or b.returncode != 0:
        return None
    ga, gb = (a.stdout or "").strip(), (b.stdout or "").strip()
    if not ga or not gb:
        return None
    try:
        ga = os.path.normcase(os.path.abspath(os.path.join(repo, ga)))
        gb = os.path.normcase(os.path.abspath(os.path.join(repo, gb)))
    except Exception:
        return None
    return ga != gb


def _is_blast_radius(rel):
    p = rel.replace("\\", "/").strip("/").lower()
    if not p:
        return False
    parts = p.split("/")
    if parts[0] in BLAST_TOP_DIRS:
        return True
    base = parts[-1]
    if base in BLAST_BASENAMES:
        return True
    # `.env`, `.env.local`, `foo.env` -- but not `x.envelope.json`.
    if base == ".env" or base.startswith(".env.") or base.endswith(".env"):
        return True
    if "credentials" in base:
        return True
    return False


def _relative(repo, abs_path):
    try:
        rel = os.path.relpath(abs_path, repo)
    except Exception:
        return None
    if rel.startswith(".."):
        return None
    return rel


def _safe(text):
    """Strip control characters before putting counterparty-controlled text (branch
    names, paths) into model-visible output. Mirrors commit-hygiene-guard._safe."""
    return "".join(ch for ch in str(text) if ch == " " or ch.isprintable())[:400]


def main():
    raw = sys.stdin.read()
    payload = json.loads(raw) if raw.strip() else {}
    if payload.get("tool_name") != "Bash":
        return 0
    cmd = (payload.get("tool_input") or {}).get("command") or ""
    if not cmd or _parse is None:
        return 0

    cwd = payload.get("cwd") or os.getcwd()
    repo = _repo_root(cwd)
    if not repo:
        return 0

    # SIGNAL (c): only ORA's shared single-instance checkouts are in scope.
    try:
        repo_n = os.path.normcase(os.path.abspath(repo))
    except Exception:
        return 0
    if repo_n not in _shared_roots():
        return 0

    # SIGNAL (b): a linked worktree is exactly what we want people to use.
    linked = _is_linked_worktree(repo)
    if linked is None or linked:
        return 0

    # SIGNAL (a): what will this commit actually land?
    try:
        cands = _parse.candidate_paths(repo, cmd)
    except Exception:
        return 0
    if not cands:
        return 0
    hits = []
    for c in cands:
        rel = _relative(repo, c)
        if rel and _is_blast_radius(rel):
            hits.append(rel.replace("\\", "/"))
    if not hits:
        return 0

    session_id = payload.get("session_id") or ""
    if _override_tokens is not None:
        try:
            tier = _override_tokens.Tier(OVERRIDE_BASENAME, "shared-checkout-commit", 3600)
            if _override_tokens.token_grants(session_id, tier) is not None:
                return 0
        except Exception:
            pass

    hits = sorted(set(hits))
    shown = ", ".join(_safe(h) for h in hits[:5])
    more = "" if len(hits) <= 5 else " (+%d more)" % (len(hits) - 5)
    token = os.path.join(
        _override_tokens.sessions_root() if _override_tokens else "<sessions>",
        session_id or "<session>", "overrides", OVERRIDE_BASENAME).replace("\\", "/")
    reason = (
        "this commit lands BLAST-RADIUS paths in the MAIN checkout of a shared repo.\n"
        "  repo:  %s\n  paths: %s%s\n"
        "  CLAUDE.md: shared checkouts are SINGLE-WRITER -- isolate via a worktree.\n"
        "  Other sessions commit here concurrently; landing blast-radius changes in the\n"
        "  main checkout is how OI-247 happened.\n"
        "  Do this instead:\n"
        "    git worktree add .claude/worktrees/<name> -b <branch> origin/main\n"
        "    (make the change there, then open a PR)\n"
        "  If Gabriel has approved committing directly here, write this override and retry:\n"
        "    path: %s\n    valid: 60 min, multi-use\n"
        "    content:\n      scope: shared-checkout-commit\n      session: %s\n"
        "      reason: <why Gabriel approved this>"
        % (_safe(repo), shown, more, token, session_id or "<session>")
    )
    sys.stderr.write("BLOCKED (%s): %s\n" % (GUARD_NAME, reason))
    # MUST exit, not return: the dispatcher's in-process path discards return values.
    sys.exit(2)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception:
        # Fail open on ANY internal error. A bug here must never block a commit.
        sys.exit(0)
