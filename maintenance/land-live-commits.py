#!/usr/bin/env python3
"""Land the primary checkout's own memory commits on main through ONE standing PR.

    python maintenance/land-live-commits.py [--json] [--dry-run] [--repo DIR] [--include-path PATH ...]

WHY (2026-11-02): ora-memory-commit-sweep commits settled memory/ changes (event_log.md
included) on the primary checkout's CURRENT branch and never pushes. Those commits never
reached main: event_log backlogs grew to 30+ entries, the live branch diverged (15
unique commits, 2026-10-30), and each time a session had to land them by hand (#381,
#386) or with the isolated-hunk technique. A PR cut from main with the live event_log
copied in is the WRONG fix: the next sweep commits a superset on the live branch, and
merging main forward then conflicts on the newest-first log head.

This script ships the live branch ITSELF: it pushes the checked SHA to the fixed branch
`land/live-memory` and opens (or reuses) one PR to main. Merged with a MERGE COMMIT
(never squash), the live commits become reachable from main, so ora-checkout-merge-forward's
next `merge --no-ff` is conflict-free and this script then reports NOTHING. If the PR is
squash-merged instead, the content is on main but the commits are not: the next run sees
that (two-dot diff of the changed paths is empty) and reports ALREADY_LANDED rather than
re-opening a PR that would conflict on the newest-first event_log head.

It never merges (merge-ready owns merges, on Gabriel's yes), never force-pushes, never
switches branches, never touches the working tree or the index.

Gate: every path changed on the live branch since its merge-base with origin/main
(`git diff --no-renames origin/main...HEAD`, so a rename out of hooks/ shows as a deletion
there) must be under memory/ or an --include-path. Anything else means unreviewed
non-memory work is riding on the live branch: STOP (BLOCKED_NON_MEMORY).

Status (exit code):
  NOTHING (0)            live branch has no commits that main lacks
  ALREADY_LANDED (0)     commits exist but their content is already on main (a squash
                         merge); merge-forward will reconcile, nothing to push
  OPENED / UPDATED (0)   pushed; PR opened or an open PR updated (url in output)
  DRY_RUN (0)            what would be pushed, nothing done
  BLOCKED_NON_MEMORY (3) paths outside the allowlist (listed)
  BLOCKED_LAND_DIVERGED (3) origin/land/live-memory is not an ancestor of the checked SHA
                         (someone pushed to it, e.g. GitHub "Update branch"); a human
                         resolves it, this script never force-pushes
  ERROR (2)              git/gh failure (detail)
"""
import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MEMORY = "projects/C--Users-Owner-OneDrive---Oxford-Capital-Partners/memory/"
LAND_BRANCH = "land/live-memory"
BASE = "main"


def git(*args, check=True):
    r = subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=True)
    if check and r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {r.stderr.strip() or r.stdout.strip()}")
    return r.stdout.strip()


def gh(*args):
    r = subprocess.run(["gh", *args], cwd=str(REPO), capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args)}: {r.stderr.strip() or r.stdout.strip()}")
    return r.stdout.strip()


def allowed(path, includes):
    return path.startswith(MEMORY) or any(path == p or path.startswith(p.rstrip("/") + "/") for p in includes)


def plan(includes=()):
    """Read-only: what would land. Returns dict with status in {NOTHING, READY, BLOCKED_NON_MEMORY}."""
    git("fetch", "-q", "origin", BASE)
    git("fetch", "-q", "origin", f"+refs/heads/{LAND_BRANCH}:refs/remotes/origin/{LAND_BRANCH}",
        check=False)  # absent on the first run
    head = git("rev-parse", "HEAD")
    commits = [c for c in git("rev-list", "--no-merges", f"origin/{BASE}..HEAD").splitlines() if c]
    if not commits:
        return {"status": "NOTHING", "head": head, "commits": []}
    changed = [p for p in git("-c", "core.quotepath=off", "diff", "--no-renames", "--name-only",
                              f"origin/{BASE}...{head}").splitlines() if p]
    subjects = git("log", "--no-merges", "--format=%h %s", f"origin/{BASE}..{head}").splitlines()
    out = {"head": head, "commits": subjects, "paths": changed}
    bad = [p for p in changed if not allowed(p, includes)]
    if bad:
        out.update(status="BLOCKED_NON_MEMORY", blocked_paths=bad)
        return out
    if not changed or not git("diff", "--no-renames", "--name-only", f"origin/{BASE}", head,
                               "--", *changed):
        out["status"] = "ALREADY_LANDED"
        return out
    remote_land = git("rev-parse", "--verify", "-q", f"refs/remotes/origin/{LAND_BRANCH}", check=False)
    if remote_land and subprocess.run(["git", "-C", str(REPO), "merge-base", "--is-ancestor",
                                       remote_land, head]).returncode != 0:
        out.update(status="BLOCKED_LAND_DIVERGED", remote_land=remote_land)
        return out
    out["status"] = "READY"
    return out


def _body(p):
    return "\n".join([
        "Automated by `maintenance/land-live-commits.py` (weekly, after ora-memory-commit-sweep).",
        "",
        "Ships the primary checkout's own memory commits. **Merge with a MERGE COMMIT, not squash,**",
        "so the live branch becomes an ancestor of main and the next merge-forward fast-forwards.",
        "",
        f"Paths (all under memory/ or an explicit --include-path): {len(p['paths'])}",
        "", "Commits:", *[f"- {s}" for s in p["commits"]],
    ])


def land(p):
    # push the SHA plan() checked, never HEAD: another session may commit in between
    git("push", "-q", "origin", f"{p['head']}:refs/heads/{LAND_BRANCH}")
    existing = json.loads(gh("pr", "list", "--head", LAND_BRANCH, "--base", BASE, "--state", "open",
                             "--json", "number,url"))
    if existing:
        gh("pr", "edit", str(existing[0]["number"]), "--body", _body(p))
        p.update(status="UPDATED", pr=existing[0]["url"])
        return p
    today = datetime.now().strftime("%Y-%m-%d")
    url = gh("pr", "create", "--base", BASE, "--head", LAND_BRANCH,
             "--title", f"memory: land live-checkout memory commits ({today})", "--body", _body(p))
    p.update(status="OPENED", pr=url)
    return p


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--repo", help="checkout to operate on (default: the one this script lives in)")
    ap.add_argument("--include-path", action="append", default=[],
                    help="extra repo-relative path or dir allowed to ride along (manual runs only)")
    a = ap.parse_args(argv)
    global REPO
    if a.repo:
        REPO = Path(a.repo).resolve()
    try:
        p = plan(a.include_path)
        if p["status"] == "READY":
            if a.dry_run:
                p["status"] = "DRY_RUN"
            else:
                p = land(p)
    except Exception as e:  # RuntimeError from git/gh, plus a missing gh or bad JSON: always emit a status
        p = {"status": "ERROR", "detail": f"{type(e).__name__}: {e}"}
    code = {"BLOCKED_NON_MEMORY": 3, "BLOCKED_LAND_DIVERGED": 3, "ERROR": 2}.get(p["status"], 0)
    if a.json:
        print(json.dumps(p, indent=2))
    else:
        print(p["status"], p.get("pr", ""), p.get("detail", ""))
        for k in ("commits", "blocked_paths"):
            for line in p.get(k, []):
                print(f"  {k[:-1]}: {line}")
    return code


if __name__ == "__main__":
    sys.exit(main())
