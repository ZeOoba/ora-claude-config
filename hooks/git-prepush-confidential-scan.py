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


def load_terms():
    """Lowercased active always-terms, or None if the file is unreadable (fail-closed)."""
    try:
        with open(TERMS_FILE, encoding="utf-8") as f:
            d = json.load(f)
    except Exception:
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
