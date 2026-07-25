#!/usr/bin/env python3
"""Native git pre-push gate for ~/.claude — scans every commit genuinely NEW to the
remote, across the full diff of each (not just the tree at HEAD).

Lesson 2026-06-11 (incident, same-day remediation): the first push of this repo
carried pre-scrub commits with confidential deal terms in their diffs. A clean HEAD
does not mean a clean push. This hook runs `git log -p` over every ref range being
pushed and BLOCKS if any active always-term from hooks/confidential-terms.json
appears anywhere in that range. Terms are never echoed — only deal-relative
indices are reported.

Range computation (fixed 2026-07-25 — see rev_range()/_resolve_default_baseline()):
an EXISTING remote ref scans remote_sha..local_sha (the delta), same as always. A
BRAND-NEW remote ref (the normal case for a new branch's first push) scans
origin/<default-branch>..local_sha — commits not yet reachable from the repo's
default/trunk branch — NOT the unbounded `git log -p local_sha` this gate used
before that date, which dumped the ENTIRE history reachable from local_sha and
re-flagged commits already public on origin/main on every single first push of any
new branch (confirmed repro: a6f0689, an origin/main ancestor, re-flagged forever on
a documented placeholder API-key value in server/secrets.env.example -- not spelled
out here verbatim, since this gate scans its own source too). An
orphan branch (no merge-base with the default branch) is scanned in FULL by this same
range, because none of its history is reachable from a baseline it shares no ancestry
with — intentional, not a gap, since none of that history was ever public.

FAIL-CLOSED: terms file unreadable -> block; git log fails (e.g. unknown remote
sha — run `git fetch` first) -> block; a brand-new ref whose default-branch baseline
can't be resolved (no origin remote, nothing fetched) -> block, not a silent
full-history rescan and not a silent skip. No active terms (all deals closed) plus
no credential hits -> allow.

Linked worktrees: hooks/confidential-terms.json is gitignored, so `git worktree
add` never checks it out into a fresh linked worktree. load_terms() falls back to
the MAIN worktree's copy (resolved via `git rev-parse --git-common-dir`, shared by
every worktree of the same repo) when this checkout's own copy is missing or
unreadable. Still fail-closed if the file is unreadable in BOTH places (2026-07-12).

Install (done 2026-06-11, extended 2026-07-24; re-do after any fresh clone — see
docs/MIGRATION_RUNBOOK.md). The .git/hooks/pre-push shim is NOT version-controlled, so
it must be recreated on every fresh clone. It runs THREE tracked checks in order — the
doctrine-drift gate, then the hook-test-suite gate, then this fail-closed
confidentiality scan LAST (the first two take </dev/null so neither consumes git's ref
stdin; the final exec hands that stdin to this scan unchanged):
  .git/hooks/pre-push  ->  #!/bin/sh
                           ROOT="$(git rev-parse --show-toplevel)"
                           python "$ROOT/hooks/git-prepush-doctrine-gate.py" "$@" </dev/null || exit $?
                           python "$ROOT/hooks/git-prepush-hook-tests-gate.py" "$@" </dev/null || exit $?
                           exec python "$ROOT/hooks/git-prepush-confidential-scan.py" "$@"
  (The doctrine-drift check lives in hooks/git-prepush-doctrine-gate.py, the hook-test
   check in hooks/git-prepush-hook-tests-gate.py; THIS scan's own logic is unchanged —
   the other two gates were added ahead of it, not merged into it.)

Exit 0 = allow push. Exit 1 = block (git pre-push convention).
"""
import json
import os
import subprocess
import sys

HOOK_DIR = os.path.dirname(os.path.abspath(__file__))
TERMS_FILE = os.path.join(HOOK_DIR, "confidential-terms.json")
ZERO_RE = "0"

# CREDENTIAL SCAN (Gabriel ruling, 2026-07-24). Until now this gate blocked confidential
# DEAL TERMS only -- it carried zero credential patterns, so nothing stopped an API key
# reaching ZeOoba/ora-claude-config. The detection logic existed in
# maintenance/scrub-before-optin.py but only ran when a human remembered to invoke it; its
# own docstring records that the FRED key hardcoded in a retired SKILL.md was caught "only
# because that grep happened to be written that day".
#
# FAIL-CLOSED like the terms check: if the pattern module cannot be imported we block,
# because we cannot prove the push is clean. (The terms scan already fails closed on an
# unreadable terms file -- same principle, same reason.)
sys.path.insert(0, os.path.join(HOOK_DIR, "lib"))
try:
    import secret_patterns as _sp
except Exception as _e:  # pragma: no cover - exercised via the import-failure test
    _sp = None
    _SP_ERR = str(_e)


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


_DEFAULT_BRANCH_CANDIDATES = ("refs/remotes/origin/main", "refs/remotes/origin/master")


def _resolve_default_baseline(start_dir="."):
    """Best-effort commit-ish for the remote's default/trunk branch (e.g.
    'refs/remotes/origin/main'), used to bound the history scan on a brand-new remote
    ref. Prefers the tracked refs/remotes/origin/HEAD symref (set by a real `git
    clone` or `git remote set-head`); falls back to the common trunk names since a
    plain `git fetch` alone does not set that symref. Returns None if nothing
    resolves -- no `origin` remote, nothing fetched yet, or not a git repo at all --
    so the caller can fail closed instead of silently rescanning full history or
    silently skipping the scan.

    start_dir defaults to "." (the process's own cwd) DELIBERATELY, not HOOK_DIR --
    it must resolve against the SAME repo the `git log -p` scan itself operates on
    (which also relies on inherited cwd, not `-C`). git invokes pre-push hooks with
    cwd already at the top of the repo being pushed, so in real installs this and
    HOOK_DIR's parent are the same directory anyway -- but conflating the two is a
    live bug the moment they diverge (caught in review: it silently baselined
    against the wrong repo and produced a tautologically-passing test).

    ALWAYS fully-qualified (refs/remotes/origin/... , never the short 'origin/main').
    A short name is subject to git's ref-disambiguation order, which checks
    refs/heads/ before refs/remotes/ -- a LOCAL branch literally named 'origin/main'
    would silently shadow the real remote-tracking ref and could exclude genuinely
    new, unpushed commits from the scan (a demonstrated false negative caught in
    review). Fully-qualified refs cannot be shadowed."""
    candidates = []
    try:
        p = subprocess.run(
            ["git", "-C", start_dir, "symbolic-ref", "-q", "refs/remotes/origin/HEAD"],
            capture_output=True, text=True, timeout=5,
        )
    except Exception:
        p = None
    if p is not None and p.returncode == 0 and p.stdout.strip():
        symref_target = p.stdout.strip()
        # `git remote set-head` always yields a refs/remotes/... target, but the
        # lower-level `git symbolic-ref refs/remotes/origin/HEAD <anything>` doesn't
        # enforce that -- it would happily point this at a refs/heads/... branch,
        # which reopens exactly the shadowing class the fully-qualified-refs fix
        # above closes (caught in review). Only trust it if it's actually still
        # under refs/remotes/; otherwise fall through to the default candidates.
        if symref_target.startswith("refs/remotes/"):
            candidates.append(symref_target)
    for c in _DEFAULT_BRANCH_CANDIDATES:
        if c not in candidates:
            candidates.append(c)
    for ref in candidates:
        try:
            v = subprocess.run(
                ["git", "-C", start_dir, "rev-parse", "-q", "--verify", ref + "^{commit}"],
                capture_output=True, text=True, timeout=5,
            )
        except Exception:
            continue
        if v.returncode == 0 and v.stdout.strip():
            return ref
    return None


def rev_range(local_sha, remote_sha, baseline):
    """Range of commits to scan for one pushed ref.

    - Existing remote ref (remote_sha not all-zero): unchanged -- the delta,
      remote_sha..local_sha.
    - Brand-new remote ref (remote_sha all-zero, the normal case for a new branch's
      first push): bounded to baseline..local_sha, i.e. only commits NOT already
      reachable from the repo's default/trunk branch (baseline, e.g. origin/main).
      This is the 2026-07-25 fix: the old behavior returned local_sha alone (no range
      at all), which makes `git log -p` dump the ENTIRE history reachable from
      local_sha -- re-scanning commits already public on origin/main on every first
      push of any new branch.
    - Orphan branch (no merge-base with baseline at all): baseline..local_sha then
      naturally covers the branch's FULL history, because none of it is excluded by
      a baseline it shares no ancestry with. This is intentional, not a gap: an
      orphan branch's history was never reachable from the trunk, so none of it is
      "already public" and all of it must be scanned.
    - baseline is None (can't resolve the repo's default branch -- no origin remote,
      nothing fetched, not a repo): returns None to signal the caller must fail
      closed rather than silently falling back to a full-history rescan or silently
      skipping the scan.
    """
    if set(remote_sha) != {ZERO_RE}:
        return "%s..%s" % (remote_sha, local_sha)
    if baseline is None:
        return None
    return "%s..%s" % (baseline, local_sha)


def scan_text(text, terms):
    """Sorted indices of terms present in text (never the terms themselves)."""
    low = text.lower()
    return sorted(i for i, t in enumerate(terms) if t in low)


def main():
    # Fail closed on a broken pattern module, exactly as for an unreadable terms file:
    # an unprovable push is a blocked push.
    if _sp is None:
        sys.stderr.write("pre-push BLOCKED (fail-closed): hooks/lib/secret_patterns.py "
                         "could not be imported (%s) -- cannot scan for credentials.\n"
                         % _SP_ERR)
        return 1
    terms = load_terms()
    if terms is None:
        sys.stderr.write("pre-push BLOCKED (fail-closed): confidential-terms.json "
                         "unreadable — cannot prove the push is clean.\n")
        return 1
    # NOTE: there is deliberately NO `if not terms: return 0` early exit any more. It used
    # to short-circuit the whole hook whenever no deal was active -- which is the state
    # TODAY -- so a credential scan placed after it would have been dead on arrival. The
    # two scans are independent: an empty terms list disables the TERMS check only.
    # No start_dir arg -- resolves against THIS PROCESS's cwd, same as the `git log -p`
    # scan below (which also has no explicit -C/cwd). git invokes pre-push hooks with
    # cwd at the top of the repo being pushed, so this is the repo actually being
    # scanned -- deliberately NOT HOOK_DIR, which is fixed to wherever this script
    # file happens to live and would silently diverge from the repo being pushed.
    # Always resolved against the "origin" remote -- matches every other assumption
    # in this file (confidential-terms.json fallback, install docs) that ~/.claude
    # has exactly one remote; a push to a second remote would still be scanned, just
    # bounded against origin/main rather than that remote's own trunk.
    baseline = _resolve_default_baseline()
    bad = False
    for local_ref, local_sha, remote_ref, remote_sha in parse_pushrefs(sys.stdin.read()):
        if set(local_sha) == {ZERO_RE}:
            continue  # ref deletion — nothing new is pushed
        rng = rev_range(local_sha, remote_sha, baseline)
        if rng is None:
            sys.stderr.write("pre-push BLOCKED (fail-closed): %s is a brand-new remote "
                             "ref and the repo's default branch (origin/main) could not "
                             "be resolved to bound the history scan -- run `git fetch` "
                             "first.\n" % local_ref)
            bad = True
            continue
        p = subprocess.run(["git", "log", "-p", "--no-color", rng],
                           capture_output=True)
        if p.returncode != 0:
            sys.stderr.write("pre-push BLOCKED (fail-closed): `git log -p %s` failed "
                             "for %s (unknown remote sha? run `git fetch` first).\n"
                             % (rng, local_ref))
            bad = True
            continue
        body = p.stdout.decode("utf-8", "ignore")
        if terms:
            hits = scan_text(body, terms)
            if hits:
                sys.stderr.write("pre-push BLOCKED: %d confidential term(s) (indices %s) "
                                 "found in the HISTORY being pushed on %s (range %s). A "
                                 "clean HEAD does not mean a clean push — purge or rebase "
                                 "the history first (see docs/MIGRATION_RUNBOOK.md).\n"
                                 % (len(hits), hits, local_ref, rng))
                bad = True
        # Credential scan over the SAME body -- per file, so a test fixture in the history
        # cannot block every push (see secret_patterns.scan_diff). Reports path + label
        # only; the matched value is never echoed into the terminal or a CI log.
        leaks = _sp.scan_diff(body)
        if leaks:
            detail = "; ".join("%s -> %s" % (path, ", ".join(labels))
                               for path, labels in leaks)
            sys.stderr.write("pre-push BLOCKED: credential-shaped string(s) in the HISTORY "
                             "being pushed on %s (range %s): %s. Values are not echoed. "
                             "Rotate the credential FIRST, then purge or rebase the "
                             "history -- a force-push alone does not un-leak it.\n"
                             % (local_ref, rng, detail))
            bad = True
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
