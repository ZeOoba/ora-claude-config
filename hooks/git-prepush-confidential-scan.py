#!/usr/bin/env python3
"""Native git pre-push gate for ~/.claude — scans the FULL HISTORY being pushed.

Lesson 2026-06-11 (incident, same-day remediation): the first push of this repo
carried pre-scrub commits with confidential deal terms in their diffs. A clean HEAD
does not mean a clean push. This hook runs `git log -p` over every ref range being
pushed and BLOCKS if any active always-term from hooks/confidential-terms.json
appears anywhere in that history. Terms are never echoed — only deal-relative
indices are reported.

FAIL-CLOSED: terms file unreadable -> block; git log fails (e.g. unknown remote
sha — run `git fetch` first) -> block. No active terms (all deals closed) -> allow.

Linked worktrees: hooks/confidential-terms.json is gitignored, so `git worktree
add` never checks it out into a fresh linked worktree. load_terms() falls back to
the MAIN worktree's copy (resolved via `git rev-parse --git-common-dir`, shared by
every worktree of the same repo) when this checkout's own copy is missing or
unreadable. Still fail-closed if the file is unreadable in BOTH places (2026-07-12).

Install (done 2026-06-11; re-do after any fresh clone — see docs/MIGRATION_RUNBOOK.md).
The .git/hooks/pre-push shim is NOT version-controlled, so it must be recreated on every
fresh clone. It runs BOTH tracked checks — the doctrine-drift gate FIRST, then this
fail-closed confidentiality scan (the doctrine gate takes </dev/null so it never consumes
git's ref stdin; the exec hands that stdin to this scan unchanged):
  .git/hooks/pre-push  ->  #!/bin/sh
                           ROOT="$(git rev-parse --show-toplevel)"
                           python "$ROOT/hooks/git-prepush-doctrine-gate.py" "$@" </dev/null || exit $?
                           exec python "$ROOT/hooks/git-prepush-confidential-scan.py" "$@"
  (The doctrine-drift check lives in hooks/git-prepush-doctrine-gate.py; THIS scan's own
   logic is unchanged — the doctrine gate was added ahead of it, not merged into it.)

Exit 0 = allow push. Exit 1 = block (git pre-push convention).
"""
import json
import os
import subprocess
import sys

HOOK_DIR = os.path.dirname(os.path.abspath(__file__))
TERMS_FILE = os.path.join(HOOK_DIR, "confidential-terms.json")
ZERO_RE = "0"


def _read_json(path):
    """Parsed JSON from path, or None on any read/parse error."""
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _git_common_dir(start_dir):
    """Absolute path to the repo's shared .git dir (same for every worktree of
    the same repo), or None on any failure -- not a git repo, git missing, etc."""
    try:
        p = subprocess.run(
            ["git", "-C", start_dir, "rev-parse", "--git-common-dir"],
            capture_output=True, text=True, timeout=5,
        )
    except Exception:
        return None
    if p.returncode != 0:
        return None
    out = p.stdout.strip()
    if not out:
        return None
    if not os.path.isabs(out):
        out = os.path.normpath(os.path.join(start_dir, out))
    return out


def _main_worktree_terms_file():
    """confidential-terms.json in the MAIN worktree, or None if it can't be
    resolved or doesn't exist there. hooks/confidential-terms.json is gitignored
    (see .gitignore), so `git worktree add` never checks it out into a linked
    worktree -- this lets a linked worktree fall back to the main checkout's
    copy instead of failing closed on every push from a fresh worktree."""
    common_dir = _git_common_dir(HOOK_DIR)
    if common_dir is None:
        return None
    # Assumes the terms file lives at <repo-root>/hooks/confidential-terms.json --
    # same layout TERMS_FILE itself relies on (HOOK_DIR is this script's own dir).
    candidate = os.path.join(os.path.dirname(common_dir), "hooks", "confidential-terms.json")
    if os.path.normcase(os.path.abspath(candidate)) == os.path.normcase(os.path.abspath(TERMS_FILE)):
        return None  # already the file we just tried
    return candidate


def load_terms():
    """Lowercased active always-terms, or None if unreadable both in this
    checkout and (falling back) in the main worktree's copy (fail-closed)."""
    d = _read_json(TERMS_FILE)
    if d is None:
        fallback = _main_worktree_terms_file()
        if fallback is not None:
            d = _read_json(fallback)
    if d is None:
        return None
    out = []
    for key, deal in d.items():
        if key.startswith("_") or not isinstance(deal, dict) or not deal.get("active", True):
            continue
        out.extend(t.lower() for t in deal.get("always", [])
                   if isinstance(t, str) and t.strip())
    return out


def _is_sha(s):
    return len(s) == 40 and all(c in "0123456789abcdef" for c in s.lower())


def parse_pushrefs(text):
    """Pre-push stdin lines: '<local_ref> <local_sha> <remote_ref> <remote_sha>'.
    Both sha fields must be 40-hex — anything else is noise, not a ref line."""
    refs = []
    for line in text.splitlines():
        parts = line.split()
        if len(parts) == 4 and _is_sha(parts[1]) and _is_sha(parts[3]):
            refs.append(tuple(parts))
    return refs


def rev_range(local_sha, remote_sha):
    """Full local history for a new remote ref; otherwise just the delta."""
    if set(remote_sha) == {ZERO_RE}:
        return local_sha
    return "%s..%s" % (remote_sha, local_sha)


def scan_text(text, terms):
    """Sorted indices of terms present in text (never the terms themselves)."""
    low = text.lower()
    return sorted(i for i, t in enumerate(terms) if t in low)


def main():
    terms = load_terms()
    if terms is None:
        sys.stderr.write("pre-push BLOCKED (fail-closed): confidential-terms.json "
                         "unreadable — cannot prove the push is clean.\n")
        return 1
    if not terms:
        return 0  # no active deals
    bad = False
    for local_ref, local_sha, remote_ref, remote_sha in parse_pushrefs(sys.stdin.read()):
        if set(local_sha) == {ZERO_RE}:
            continue  # ref deletion — nothing new is pushed
        rng = rev_range(local_sha, remote_sha)
        p = subprocess.run(["git", "log", "-p", "--no-color", rng],
                           capture_output=True)
        if p.returncode != 0:
            sys.stderr.write("pre-push BLOCKED (fail-closed): `git log -p %s` failed "
                             "for %s (unknown remote sha? run `git fetch` first).\n"
                             % (rng, local_ref))
            bad = True
            continue
        hits = scan_text(p.stdout.decode("utf-8", "ignore"), terms)
        if hits:
            sys.stderr.write("pre-push BLOCKED: %d confidential term(s) (indices %s) "
                             "found in the HISTORY being pushed on %s (range %s). A "
                             "clean HEAD does not mean a clean push — purge or rebase "
                             "the history first (see docs/MIGRATION_RUNBOOK.md).\n"
                             % (len(hits), hits, local_ref, rng))
            bad = True
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
