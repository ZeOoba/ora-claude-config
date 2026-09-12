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

BRANCH DRIFT (added 2026-09-09, open-items-tracker.md#OI-249): a handful of
repos have a declared CANONICAL_BRANCH -- currently only `~/.claude`, which
is expected to track `main` directly rather than live on a feature branch,
unlike the others (ora-pm, website-canonical, etc.), where cutting and
sitting on a feature branch for a while is normal, expected work and would
be noise to flag. For a repo with a canonical branch declared, this checks
the current branch name AND how many commits `origin/<canonical>` is ahead
of HEAD (via `git rev-list --count HEAD..origin/<canonical>`) and flags
BRANCH_DRIFT when the current branch isn't the canonical one, or the repo
is BRANCH_BEHIND_THRESHOLD (default 10) or more commits behind it, or the
count can't be determined at all (e.g. `origin/<canonical>` doesn't resolve
locally) -- same "unmeasurable is uncertain, not clean" stance as the
WIP-aging check below, never silently passed as fine. Root cause this
exists for: the primary `~/.claude` checkout sat on `feat/model-canary-probe-
step25` for weeks, merged into `main` once (2026-08-23) without its own HEAD
ever moving back, and re-diverged to 40 commits behind with 97 dirty files --
found three separate times by accident during unrelated triage/audit passes,
because nothing was watching branch identity or behind-count as a standing
signal (dirty-file staleness above catches a different dimension and did not
catch this one). Repos with no CANONICAL_BRANCH entry are never flagged on
this dimension, by design -- their feature-branch churn is expected.

CORRECTOR STREAK (added 2026-09-12): for a repo with a paired daily corrector
(currently only `~/.claude` -> checkout-merge-forward.py), this also reads the
corrector's last-run state file and flags CORRECTOR_STUCK when its
`consecutiveUnsynced` streak reaches CORRECTOR_UNSYNCED_ESCALATE_RUNS (default
7 -- a week of daily runs that never ended MERGED/NOOP_CLEAN). Any single
BLOCKED_* day is routine and the corrector stays silent on it by design; a
week-long streak means the WIP backlog is pinning the checkout and drift is
compounding with nothing correcting it. A missing, corrupt, or pre-counter
state file is flagged too (unmeasurable, not clean). The corrector is the
sole writer of that file; this only reads it. A `lastRun` older than
CORRECTOR_STALE_HOURS (72h), or one that cannot be parsed, is also flagged:
a disabled task, a run that keeps failing its claim step, or one that dies
before invoking the script leaves the streak frozen below threshold, and
without this check that frozen value would read as clean indefinitely.

Detection only -- never commits, stages, touches repo content, or fetches
(a fetch is a network/state-mutating action this script deliberately leaves
to whatever already keeps `origin/*` current; a stale local `origin/<branch>`
ref under-reports drift, which is a known limitation, not silently hidden --
see the `behind` `None`/error handling above). A repo whose configured path
no longer has a `.git` directory (e.g. archived/moved) is reported as MISSING
rather than silently skipped, so a stale repo list doesn't quietly go stale
itself.

Exit 0 = no repo is STALE, MISSING, BRANCH_DRIFT, or CORRECTOR_STUCK. Exit 1 = at least one
is. Prints one line per repo plus a final RESULT_JSON={...} summary line.
"""
import datetime
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

# Repos where sitting off the named branch (or far behind it) is itself the
# anomaly -- see the BRANCH DRIFT module docstring section. Deliberately a
# small explicit map, same reasoning as DEFAULT_KNOWN_REPOS: extend it by
# hand when another repo develops a comparable "should always track this
# branch" expectation, don't infer it from current branch name at scan time.
DEFAULT_CANONICAL_BRANCH = {
    r"C:\Users\Owner\.claude": "main",
}

# Test seam (mirrors KNOWN_REPOS_OVERRIDE). None -> canonical map above.
CANONICAL_BRANCH_OVERRIDE = None

BRANCH_BEHIND_THRESHOLD = 10

# Repos with a paired daily corrector -> that corrector's last-run state file
# (written solely by checkout-merge-forward.py --state-file).
DEFAULT_CORRECTOR_STATE = {
    r"C:\Users\Owner\.claude":
        r"C:\Users\Owner\.claude\maintenance\_state\checkout-merge-forward-last-run.json",
}

# Test seam (mirrors KNOWN_REPOS_OVERRIDE). None -> canonical map above.
CORRECTOR_STATE_OVERRIDE = None

CORRECTOR_UNSYNCED_ESCALATE_RUNS = 7

# The corrector is daily; 72h tolerates a missed day or a weekend with the
# Desktop app closed (the fleet only fires while it is open) without masking
# a task that has genuinely stopped.
CORRECTOR_STALE_HOURS = 72


def corrector_state_map():
    return dict(CORRECTOR_STATE_OVERRIDE) if CORRECTOR_STATE_OVERRIDE is not None \
        else dict(DEFAULT_CORRECTOR_STATE)


def _corrector_streak(state_path, now=None):
    """Corrector-streak finding merged into a repo's scan_repo() result.
    `now` (aware or naive local datetime) is injectable for tests."""
    out = {"corrector_state_path": state_path, "corrector_stuck": True,
           "corrector_consecutive_unsynced": None, "corrector_last_status": None,
           "corrector_last_run": None, "corrector_unsynced_since": None,
           "corrector_blocked_paths_count": None, "corrector_error": None}
    try:
        with open(state_path, encoding="utf-8") as fh:
            state = json.load(fh)
    except OSError:
        out["corrector_error"] = "no corrector state file at %s" % state_path
        return out
    except ValueError as e:
        out["corrector_error"] = "corrector state unparseable: %s" % e
        return out
    if not isinstance(state, dict):
        out["corrector_error"] = "corrector state is not a JSON object"
        return out
    out["corrector_last_status"] = state.get("status")
    out["corrector_last_run"] = state.get("lastRun")
    out["corrector_unsynced_since"] = state.get("unsyncedSince")
    paths = state.get("blockedPaths")
    out["corrector_blocked_paths_count"] = len(paths) if isinstance(paths, list) else None
    streak = state.get("consecutiveUnsynced")
    if not isinstance(streak, int) or isinstance(streak, bool) or streak < 0:
        out["corrector_error"] = ("corrector state has no valid consecutiveUnsynced "
                                  "(pre-2026-09-12 writer, or the task is not passing --state-file)")
        return out
    out["corrector_consecutive_unsynced"] = streak

    try:
        last = datetime.datetime.fromisoformat(str(state.get("lastRun")))
    except ValueError:
        out["corrector_error"] = "corrector state has unparseable lastRun %r" % state.get("lastRun")
        return out
    now = now or datetime.datetime.now().astimezone()
    # Compare in local time; a naive stamp is taken as local, same as the writer.
    if last.tzinfo is None:
        last = last.astimezone()
    if now.tzinfo is None:
        now = now.astimezone()
    age_hours = (now - last).total_seconds() / 3600.0
    if age_hours > CORRECTOR_STALE_HOURS:
        out["corrector_error"] = ("corrector has not run since %s (%.0fh ago, > %dh) -- "
                                  "task disabled, repeatedly BLOCKED_CLAIMED, or dying "
                                  "before STEP 1" % (state.get("lastRun"), age_hours,
                                                     CORRECTOR_STALE_HOURS))
        return out

    out["corrector_stuck"] = streak >= CORRECTOR_UNSYNCED_ESCALATE_RUNS
    return out


def canonical_branch_map():
    return dict(CANONICAL_BRANCH_OVERRIDE) if CANONICAL_BRANCH_OVERRIDE is not None \
        else dict(DEFAULT_CANONICAL_BRANCH)


def known_repos():
    return list(KNOWN_REPOS_OVERRIDE) if KNOWN_REPOS_OVERRIDE else list(DEFAULT_KNOWN_REPOS)


def _git(args, repo_path):
    """(rc, stdout) -- stdout stripped. Never raises on a non-zero/missing git,
    mirroring check-branch-point.py's git() helper (same tree, same contract)."""
    try:
        proc = subprocess.run(
            ["git"] + args, cwd=repo_path, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        return 127, str(e)
    return proc.returncode, (proc.stdout or "").strip()


def _branch_drift(repo_path, canonical):
    """Branch-identity + behind-count finding for a repo with a declared
    canonical branch. Returns a dict merged into that repo's scan_repo()
    result. `canonical` is e.g. "main"; the comparison target is always
    `origin/<canonical>` -- this never fetches, so a stale local
    remote-tracking ref under-reports (documented module-level limitation).
    """
    out = {"canonical_branch": canonical, "current_branch": None,
           "commits_behind_canonical": None, "branch_drift": True,
           "branch_drift_error": None}
    rc, current = _git(["rev-parse", "--abbrev-ref", "HEAD"], repo_path)
    if rc != 0 or not current:
        out["branch_drift_error"] = "cannot resolve current branch: %s" % current
        return out  # unmeasurable -- stays drift=True, never a silent clean.
    out["current_branch"] = current

    target = "origin/%s" % canonical
    rc, _ = _git(["rev-parse", "--verify", "--quiet", target + "^{commit}"], repo_path)
    if rc != 0:
        out["branch_drift_error"] = "%s does not resolve locally -- fetch it first" % target
        return out  # same: cannot determine is treated as drift, not clean.

    rc, count_out = _git(["rev-list", "--count", "HEAD..%s" % target], repo_path)
    if rc != 0 or not count_out.isdigit():
        out["branch_drift_error"] = "cannot count commits behind %s" % target
        return out
    behind = int(count_out)
    out["commits_behind_canonical"] = behind
    out["branch_drift"] = (current != canonical) or (behind >= BRANCH_BEHIND_THRESHOLD)
    return out


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

    canonical = canonical_branch_map().get(repo_path)
    branch_info = _branch_drift(repo_path, canonical) if canonical else {}
    corrector_path = corrector_state_map().get(repo_path)
    if corrector_path:
        branch_info.update(_corrector_streak(corrector_path))

    entries = _git_status_short(repo_path)
    if entries is None:
        out = {
            "path": repo_path, "git_repo": True, "uncommitted_count": 0,
            "oldest_age_hours": None, "stale": True, "missing": False,
            "error": "git status failed or timed out",
        }
        out.update(branch_info)
        return out
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
    out = {
        "path": repo_path, "git_repo": True,
        "uncommitted_count": len(entries),
        "oldest_age_hours": round(oldest, 1) if oldest is not None else None,
        "stale": stale, "missing": False,
    }
    out.update(branch_info)
    return out


def scan_all(repos=None):
    return [scan_repo(r) for r in (repos if repos is not None else known_repos())]


def any_stale(results):
    return any(r["stale"] for r in results)


def any_branch_drift(results):
    return any(r.get("branch_drift") for r in results)


def any_corrector_stuck(results):
    return any(r.get("corrector_stuck") for r in results)


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
        if r.get("branch_drift"):
            if r.get("branch_drift_error"):
                lines.append("[ACTION] BRANCH_DRIFT %s -- cannot determine drift vs "
                              "'%s': %s" % (r["path"], r["canonical_branch"],
                                            r["branch_drift_error"]))
            elif r.get("current_branch") != r.get("canonical_branch"):
                lines.append("[ACTION] BRANCH_DRIFT %s -- on '%s', expected '%s'; "
                              "%d commit(s) behind origin/%s" % (
                                  r["path"], r["current_branch"], r["canonical_branch"],
                                  r["commits_behind_canonical"], r["canonical_branch"]))
            else:
                lines.append("[ACTION] BRANCH_DRIFT %s -- on '%s' as expected, but %d "
                              "commit(s) behind origin/%s (>= %d threshold)" % (
                                  r["path"], r["canonical_branch"],
                                  r["commits_behind_canonical"], r["canonical_branch"],
                                  BRANCH_BEHIND_THRESHOLD))
        if r.get("corrector_stuck"):
            if r.get("corrector_error"):
                lines.append("[ACTION] CORRECTOR_STUCK %s -- cannot determine merge-forward "
                              "streak: %s" % (r["path"], r["corrector_error"]))
            else:
                n_paths = r.get("corrector_blocked_paths_count")
                paths_note = "" if n_paths is None else ", %d blocked path(s)" % n_paths
                lines.append("[ACTION] CORRECTOR_STUCK %s -- merge-forward has not synced for "
                              "%d consecutive run(s) since %s (last status %s%s) "
                              "-- triage the overlapping WIP (dirty-tree-triage)" % (
                                  r["path"], r["corrector_consecutive_unsynced"],
                                  r.get("corrector_unsynced_since") or "unknown",
                                  r.get("corrector_last_status"), paths_note))
    return "\n".join(lines)


def main():
    results = scan_all()
    print(format_report(results))
    print("RESULT_JSON=%s" % json.dumps(results))
    return 1 if (any_stale(results) or any_branch_drift(results)
                 or any_corrector_stuck(results)) else 0


if __name__ == "__main__":
    sys.exit(main())
