#!/usr/bin/env python3
"""ORA cross-repo WIP-aging scan -- reports how long uncommitted work has been
sitting in each of the small set of local git repos Gabriel/sessions touch
regularly, so a backlog surfaces on its own schedule instead of needing to be
asked about.

WHY (found 2026-07-26): a repo-housekeeping session found ~21 uncommitted
items in the shared `~/.claude` checkout, left there by several idle sessions
that had deliberately deferred committing "for Gabriel to sequence" rather
than risk co-mingling each other's hunks (see event_log.md, same date). That
sequencing pass only happened because Gabriel happened to ask. Nothing had
been watching the backlog age. This is a lightweight, read-only, periodic
check-in for that gap -- NOT a committer, NOT a scheduler of its own: it
reports, and a human (or a future directed session) decides what to do.

WHAT IT CHECKS: for each known repo, `git status --short` (uncommitted count)
and the OLDEST uncommitted path's on-disk mtime (best-effort -- a path git
reports as deleted has no file left to stat and is excluded from the age
calculation, though it still counts toward uncommitted_count). A repo is
STALE when it has 1+ uncommitted items AND the oldest is older than
STALE_THRESHOLD_HOURS (default 48h, matching the freshness window several
other probes in this tree already use for "worth a look" staleness).

Detection only -- never commits, stages, or touches repo content. A repo
whose configured path no longer has a `.git` directory (e.g. archived/moved)
is reported as MISSING rather than silently skipped, so a stale repo list
doesn't quietly go stale itself.

Exit 0 = no repo is STALE or MISSING. Exit 1 = at least one is. Prints one
line per repo plus a final RESULT_JSON={...} summary line.
"""
import json
import os
import subprocess
import sys
import time

STALE_THRESHOLD_HOURS = 48

# The small, known set of local repos sessions/Gabriel actually touch. Kept as
# an explicit list (not a filesystem walk) -- same reasoning as
# ora-task-integrity-guard's KNOWN_GIT_REPOS: a walk would drag in unrelated
# throwaway/fixture repos, and this set changes rarely enough that a manual
# update when a new one is added is the right tradeoff. Verified present
# (has a .git dir) 2026-07-26; oxford-realty deliberately excluded -- archived
# same day (see open-items-tracker.md OI-029), confirmed no longer a git repo.
DEFAULT_KNOWN_REPOS = (
    r"C:\Users\Owner\.claude",
    r"C:\Users\Owner\AAOS",
    r"C:\Users\Owner\ora-pm",
    r"C:\Users\Owner\ora-skills",
    r"C:\Users\Owner\oxford-command-center",
    r"C:\Users\Owner\website-canonical",
)

# Test seam only (mirrors the other probes' *_OVERRIDE pattern): when set,
# scan THIS list instead of the canonical one. None -> canonical.
KNOWN_REPOS_OVERRIDE = None


def known_repos():
    return list(KNOWN_REPOS_OVERRIDE) if KNOWN_REPOS_OVERRIDE else list(DEFAULT_KNOWN_REPOS)


def _git_status_short(repo_path):
    """[(status_code, path), ...] from `git status --short`, or None if the
    command itself failed (repo corrupt/locked -- distinct from 'no .git' at
    all, which is checked before this is ever called)."""
    try:
        proc = subprocess.run(
            ["git", "status", "--short"], cwd=repo_path,
            capture_output=True, text=True, timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    out = []
    for line in proc.stdout.splitlines():
        if not line:
            continue
        # Porcelain short format: 2-char status code, space, path (renames
        # carry "old -> new"; take the new/current path for mtime purposes).
        code = line[:2]
        path = line[3:]
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        out.append((code, path.strip('"')))
    return out


def scan_repo(repo_path, now=None):
    """One repo's finding dict. `now` is injectable for deterministic tests.

    An unmeasurable oldest-age (e.g. every uncommitted entry is a deletion, so
    nothing is left on disk to stat) is treated as STALE, not clean -- an
    inferred null ("we couldn't measure it") is not the same as a verified one
    ("we measured it and it's fine"), same distinction as
    feedback_verified_null_vs_inferred_null.md. Silently passing an
    unmeasurable repo as clean would be exactly the kind of check whose
    "nothing to report" can't be trusted."""
    now = now if now is not None else time.time()
    if not os.path.isdir(os.path.join(repo_path, ".git")):
        return {
            "path": repo_path, "git_repo": False, "uncommitted_count": 0,
            "oldest_age_hours": None, "stale": True, "missing": True,
        }
    entries = _git_status_short(repo_path)
    if entries is None:
        return {
            "path": repo_path, "git_repo": True, "uncommitted_count": 0,
            "oldest_age_hours": None, "stale": True, "missing": False,
            "error": "git status failed or timed out",
        }
    ages_hours = []
    for code, rel_path in entries:
        if code.strip() == "D" or code[1] == "D":
            continue  # deleted -- nothing on disk left to stat.
        full = os.path.join(repo_path, rel_path)
        try:
            mtime = os.path.getmtime(full)
        except OSError:
            continue  # e.g. a directory entry from an untracked subfolder.
        ages_hours.append((now - mtime) / 3600.0)
    oldest = max(ages_hours) if ages_hours else None
    stale = bool(entries) and (oldest is None or oldest >= STALE_THRESHOLD_HOURS)
    return {
        "path": repo_path, "git_repo": True,
        "uncommitted_count": len(entries),
        "oldest_age_hours": round(oldest, 1) if oldest is not None else None,
        "stale": stale, "missing": False,
    }


def scan_all(repos=None):
    return [scan_repo(r) for r in (repos if repos is not None else known_repos())]


def any_stale(results):
    return any(r["stale"] for r in results)


def format_report(results):
    lines = []
    for r in results:
        if r.get("missing"):
            lines.append("[ACTION] MISSING %s -- configured as a known repo but has no "
                          ".git directory (archived/moved without updating this scan's "
                          "list, or a real problem)." % r["path"])
        elif r.get("error"):
            lines.append("[ACTION] ERROR %s -- %s" % (r["path"], r["error"]))
        elif r["uncommitted_count"] == 0:
            lines.append("clean    %s" % r["path"])
        elif r["stale"]:
            lines.append("[ACTION] STALE %s -- %d uncommitted item(s), oldest %.1fh "
                          "(>= %dh threshold)" % (
                              r["path"], r["uncommitted_count"],
                              r["oldest_age_hours"], STALE_THRESHOLD_HOURS))
        else:
            lines.append("wip      %s -- %d uncommitted item(s), oldest %.1fh "
                          "(under threshold, not flagged)" % (
                              r["path"], r["uncommitted_count"], r["oldest_age_hours"]))
    return "\n".join(lines)


def main():
    results = scan_all()
    print(format_report(results))
    print("RESULT_JSON=%s" % json.dumps(results))
    return 1 if any_stale(results) else 0


if __name__ == "__main__":
    sys.exit(main())
