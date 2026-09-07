#!/usr/bin/env python3
"""Would opening a PR from this branch land commits you did not intend?

THE INCIDENT (2026-08-16). A worktree was branched off the primary checkout,
which sat on the long-running integration branch `feat/model-canary-probe-step25`
-- 18 commits ahead of `main`. The PR was then opened against `main`. It looked
right: 2 commits authored, 4 files touched, five independent review rounds, gate
green. GitHub reported MERGEABLE.

It carried SEVEN commits. Five of them were another session's rescued
open-items/MEMORY WIP, two merge reconciliations, and a settings.json change --
none reviewed, none related, all about to land on `main` under a title that said
"wire recursive_delete". Nothing in the workflow surfaced this: `git log` on the
branch looks normal, the diff you authored looks normal, and the PR page shows a
commit count nobody reads. It was caught by chance, after the work was declared
ready to merge.

THE OBVIOUS CHECK IS NOT ENOUGH, and this tool's own tests caught that. "Is the
base an ancestor of HEAD?" only detects the case where the BASE MOVED ON. If you
branch off an integration branch that is ahead of an otherwise-idle `main`, main
is still a perfectly good ancestor -- and you still ship its extra commits. So
ancestry is reported, but the load-bearing check is COMMIT COUNT AGAINST STATED
INTENT (`--expect N`), because that is the only signal that survives both shapes.

Authorship cannot substitute for it here: every session on this machine commits
as the same git author, so "not mine" is not computable. You have to say how many
commits you meant to ship.

  python maintenance/check-branch-point.py                 # vs origin/main
  python maintenance/check-branch-point.py --base origin/dev
  python maintenance/check-branch-point.py --expect 2      # also assert the count
  python maintenance/check-branch-point.py --json

Exit 0 clean, 1 findings, 2 could not determine (never a silent pass -- an
unanswerable check is not a clean one).
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LIB_DIR = os.path.join(os.path.dirname(HERE), "hooks", "lib")
sys.path.insert(0, LIB_DIR)
from git_probe_common import git as _git, base_resolves  # noqa: E402


def git(args, repo=None):
    """(rc, stdout) -- stdout stripped. Never raises on a non-zero git.

    Thin 2-tuple shim over the shared 3-tuple git_probe_common.git() (repo
    positional first there; this module's own call sites all predate that
    signature) so every call site below stays unchanged. timeout=None
    preserves this script's original unbounded subprocess.run() call --
    the shared helper's own 20s default is not adopted here, to keep this
    extraction a pure move rather than a new behavior."""
    rc, out, _ = _git(repo, args, timeout=None)
    return rc, out


def analyze(base="origin/main", repo=None, expect=None):
    """Findings dict. Pure-ish: all git access goes through git()."""
    out = {"base": base, "ok": False, "error": None, "head": None,
           "base_is_ancestor": None, "commits": [], "expect": expect}

    rc, head = git(["rev-parse", "HEAD"], repo)
    if rc != 0:
        out["error"] = "cannot resolve HEAD (not a git repo?): %s" % head
        return out
    out["head"] = head

    ok, _ = base_resolves(repo, base, timeout=None)
    if not ok:
        # A base that does not resolve is UNDETERMINED, not clean. Returning ok
        # here would make a typo'd --base read as a pass, which is the exact
        # false-green this tool exists to prevent.
        out["error"] = "base %r does not resolve -- fetch it first" % base
        return out

    rc, _ = git(["merge-base", "--is-ancestor", base, "HEAD"], repo)
    out["base_is_ancestor"] = (rc == 0)

    rc, log = git(["log", "--format=%h\t%an\t%s", base + "..HEAD"], repo)
    if rc != 0:
        out["error"] = "cannot list commits vs %s" % base
        return out
    for line in [l for l in log.splitlines() if l.strip()]:
        parts = line.split("\t", 2)
        if len(parts) == 3:
            out["commits"].append({"sha": parts[0], "author": parts[1],
                                   "subject": parts[2]})

    out["expect_matched"] = (expect is not None and len(out["commits"]) == expect)
    # ok == certified, deliberately. Without --expect the tool cannot know intent,
    # the report explicitly declines to certify -- and returning 0 anyway was a
    # FALSE GREEN in exactly the incident shape (base idle, branch cut from an
    # integration branch: ancestry True, foreign commits ride along, exit 0).
    # A scripted caller would have been told "clean". Unverified is not clean.
    out["certified"] = bool(out["base_is_ancestor"]) and out["expect_matched"]
    out["ok"] = out["certified"]
    return out


def format_report(r):
    lines = []
    if r["error"]:
        lines.append("[UNDETERMINED] branch-point check could not run: %s" % r["error"])
        lines.append("  Treat this as unverified, NOT as clean.")
        return "\n".join(lines)

    n = len(r["commits"])
    if r["base_is_ancestor"]:
        if r.get("certified"):
            lines.append("branch-point: OK -- %s is an ancestor of HEAD and this "
                         "branch adds exactly the %d commit(s) you declared."
                         % (r["base"], n))
        else:
            # Ancestry alone proves nothing about EXTRA commits: branch off an
            # integration branch while the base sits idle and the base is still an
            # ancestor, yet its commits ship with yours. Caught by this tool's own
            # tests; do not weaken this back into an unconditional OK.
            lines.append("branch-point: %s is an ancestor of HEAD, but that alone "
                         "does NOT mean these are all yours -- a branch cut from an "
                         "integration branch keeps ancestry and still carries its "
                         "commits. %d commit(s) would land:" % (r["base"], n))
            for c in r["commits"]:
                lines.append("    %s  %s" % (c["sha"], c["subject"][:96]))
            # NOT "--expect %d" with the observed count filled in: an operator
            # following that verbatim certifies whatever is already there, which
            # defeats the entire point of declaring intent independently.
            lines.append("  Re-run with --expect <the number of commits you MEANT "
                         "to ship> to certify. Do not paste the count above.")
    else:
        lines.append("[ACTION] BRANCH_POINT %s is NOT an ancestor of HEAD -- this "
                     "branch was cut from somewhere else, so a PR against it would "
                     "land %d commit(s), not just the ones you authored."
                     % (r["base"], n))
        lines.append("  Every commit below lands if this merges. Read the list; do "
                     "not assume the ones you recognise are the only ones.")
        for c in r["commits"]:
            lines.append("    %s  %s" % (c["sha"], c["subject"][:96]))
        lines.append("  Fix: rebase or cherry-pick your commits onto %s and open the "
                     "PR from that, or retarget the PR's base to the branch you "
                     "actually cut from." % r["base"])
    if r["expect"] is not None and n != r["expect"]:
        lines.append("[ACTION] COMMIT_COUNT expected %d commit(s), found %d -- the "
                     "branch carries work beyond what you intended to ship."
                     % (r["expect"], n))
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--base", default="origin/main")
    ap.add_argument("--repo", default=None)
    ap.add_argument("--expect", type=int, default=None)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    r = analyze(args.base, args.repo, args.expect)
    if args.json:
        print(json.dumps(r, indent=2))
    else:
        print(format_report(r))
    if r["error"]:
        return 2
    return 0 if r["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
