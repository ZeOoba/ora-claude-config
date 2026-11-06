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
STALE_THRESHOLD_HOURS (default 48h: uncommitted work sitting two days is "worth a
look". This is independent of any fleet cadence, so it did not move when the scheduled
routines went weekly on 2026-09-17 and state-freshness-probe's default became 192h).

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

CORRECTOR STREAK (added 2026-09-12): for a repo with a paired corrector (weekly since 2026-09-22)
(currently only `~/.claude` -> checkout-merge-forward.py), this also reads the
corrector's last-run state file and flags CORRECTOR_STUCK when its
`consecutiveUnsynced` streak reaches CORRECTOR_UNSYNCED_ESCALATE_RUNS (1 since the
corrector went weekly on 2026-09-22, and 7 while it was daily: either way, a week of
runs that never ended MERGED/NOOP_CLEAN, counted from the last successful sync). On the
daily cadence a single BLOCKED_* day was routine; on the weekly cadence one unsynced run
already IS a week, so it escalates, while the corrector itself still stays silent on
BLOCKED_* by design. A
week-long streak means the WIP backlog is pinning the checkout and drift is
compounding with nothing correcting it. A missing, corrupt, or pre-counter
state file is flagged too (unmeasurable, not clean). The corrector is the
sole writer of that file; this only reads it. A `lastRun` older than
CORRECTOR_STALE_HOURS (192h: one weekly cycle + 24h grace), or one that cannot be parsed, is also flagged:
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

OCC SHARED-CHECKOUT FRESHNESS (added 2026-11-05, business-loops review F-9): the
shared `oxford-command-center` checkout sat on `data/snapshot-2026-10-06` for ~4
weeks, 103 commits behind origin/main. Every reader of its on-disk
`data/snapshots/portfolio.json` (ora-am-brief, ora-recovery-billing-monthly,
ora-noi-opportunity-digest, ora-renewal-hubspot-reconcile, the local app) read
2026-10-06 data while main held three newer snapshots, and nothing alarmed. Two
additions close that:
  * OCC joins CANONICAL_BRANCH (-> main) with its OWN behind threshold
    (BEHIND_THRESHOLD_BY_REPO, 25): OCC main took 101 commits in the 30 days to
    2026-11-05 (~24/week), so the global 10 would alarm on routine code churn
    inside a week. 25 ~= one week of merges -- the code side alarms once the
    checkout has missed about a week. Data staleness does NOT wait for that
    count: the snapshot check below catches it at the first newer snapshot.
  * SNAPSHOT_STALE, for repos in SNAPSHOT_FRESHNESS: reads the WORKING-TREE copy
    of the snapshot (what readers actually open) and compares `meta.generatedAt`
    against `origin/<canonical>`'s committed copy. Stale when the local stamp is
    older, or when the stamps are equal but the content differs (a commit that
    edits the snapshot without re-extracting, e.g. OCC #511's PII redaction on
    2026-10-30, keeps the stamp). A local copy NEWER than origin (an uncommitted
    local extract) is reported, not flagged. Any unmeasurable side (file missing,
    unparseable JSON, no or naive generatedAt, origin ref or blob absent) is
    flagged with snapshot_error -- unmeasurable is uncertain, not clean.

CLI (added with the above, for ora-health-guard's daily probe):
  --repo PATH       restrict the scan to configured repo(s); repeatable. Paths
                    are matched spelling-insensitively (slashes, case, trailing
                    separator); an unconfigured path exits 2, never a silent pass.
  --freshness-only  report and exit only on MISSING / BRANCH_DRIFT /
                    SNAPSHOT_STALE / FETCH_FAILED (WIP aging and the corrector
                    streak stay weekly-hygiene business). A selected repo with
                    neither a canonical branch nor a snapshot declared exits 2.
  --fetch           first `git fetch origin <canonical>` (no tags, no FETCH_HEAD,
                    no auto-maintenance, no prompt, 45s cap) for each selected
                    repo that has either check declared. The fetch writes ONLY the
                    remote-tracking ref; HEAD, branches, index and working tree are
                    never touched. A failed fetch is [ACTION] FETCH_FAILED (the
                    comparison then ran on a stale ref: unverified, not clean).
                    Without --fetch the stance above holds: no network, and a
                    stale origin ref under-reports.
Never switches, resets, pulls or merges anything -- the OCC checkout is shared
single-writer with nested worktrees under .claude/worktrees/; advancing it is a
supervised, in-session action.

Exit 0 = no repo is STALE, MISSING, BRANCH_DRIFT, CORRECTOR_STUCK, SNAPSHOT_STALE or
FETCH_FAILED (with --freshness-only: none of MISSING, BRANCH_DRIFT, SNAPSHOT_STALE,
FETCH_FAILED). Exit 1 = at least one is. Exit 2 = usage error (unknown --repo, or
--freshness-only over a repo with nothing to check). Prints one line per repo plus
a final RESULT_JSON={...} summary line.
"""
import argparse
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
    # Shared read-only consumer checkout (F-9): readers expect it to BE main.
    r"C:\Users\Owner\oxford-command-center": "main",
}

# Test seam (mirrors KNOWN_REPOS_OVERRIDE). None -> canonical map above.
CANONICAL_BRANCH_OVERRIDE = None

BRANCH_BEHIND_THRESHOLD = 10

# Per-repo override of BRANCH_BEHIND_THRESHOLD (see module docstring for the OCC
# derivation: 101 commits/30d on OCC main -> 25 ~= one week of merges).
DEFAULT_BEHIND_THRESHOLD_BY_REPO = {
    r"C:\Users\Owner\oxford-command-center": 25,
}

# Test seam. None -> map above.
BEHIND_THRESHOLD_OVERRIDE = None

# Repos whose readers consume a committed snapshot from the working tree ->
# that snapshot's repo-relative path (must carry meta.generatedAt).
DEFAULT_SNAPSHOT_FRESHNESS = {
    r"C:\Users\Owner\oxford-command-center": "data/snapshots/portfolio.json",
}

# Test seam. None -> map above.
SNAPSHOT_FRESHNESS_OVERRIDE = None

FETCH_TIMEOUT_S = 45

# Repos with a paired corrector -> that corrector's last-run state file
# (written solely by checkout-merge-forward.py --state-file).
DEFAULT_CORRECTOR_STATE = {
    r"C:\Users\Owner\.claude":
        r"C:\Users\Owner\.claude\maintenance\_state\checkout-merge-forward-last-run.json",
}

# Test seam (mirrors KNOWN_REPOS_OVERRIDE). None -> canonical map above.
CORRECTOR_STATE_OVERRIDE = None

# Elapsed-time thresholds expressed in corrector runs. The corrector went weekly (Fri)
# on 2026-09-22, so 1 run = the old 7 daily runs (a week unsynced). Re-derive if the
# cadence changes again.
CORRECTOR_UNSYNCED_ESCALATE_RUNS = 1

# One weekly cycle + 24h grace. The daily-era 72h tolerated a missed day or a weekend
# with the Desktop app closed; on a weekly cadence it would read "has not run" 4 days
# in 7. This still catches a task that has genuinely stopped, one cycle late.
CORRECTOR_STALE_HOURS = 192


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


def _norm(path):
    """Spelling-insensitive key: a probe line written with forward slashes or a
    different case must still find the repo's declared checks, never fall
    through to "nothing declared" and pass silently."""
    return os.path.normcase(os.path.normpath(os.path.abspath(path)))


def _lookup(mapping, repo_path, default=None):
    want = _norm(repo_path)
    for key, value in mapping.items():
        if _norm(key) == want:
            return value
    return default


def canonical_branch_for(repo_path):
    return _lookup(canonical_branch_map(), repo_path)


def behind_threshold_for(repo_path):
    m = BEHIND_THRESHOLD_OVERRIDE if BEHIND_THRESHOLD_OVERRIDE is not None \
        else DEFAULT_BEHIND_THRESHOLD_BY_REPO
    return _lookup(m, repo_path, BRANCH_BEHIND_THRESHOLD)


def snapshot_path_for(repo_path):
    m = SNAPSHOT_FRESHNESS_OVERRIDE if SNAPSHOT_FRESHNESS_OVERRIDE is not None \
        else DEFAULT_SNAPSHOT_FRESHNESS
    return _lookup(m, repo_path)


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
    threshold = behind_threshold_for(repo_path)
    out["commits_behind_canonical"] = behind
    out["behind_threshold"] = threshold
    out["branch_drift"] = (current != canonical) or (behind >= threshold)
    return out


def _fetch(repo_path, branch):
    """`git fetch origin <branch>`: writes only refs/remotes/origin/<branch>.
    Returns None on success, else an error string. Never raises."""
    env = dict(os.environ)
    env["GIT_TERMINAL_PROMPT"] = "0"          # an auth prompt must never hang a probe
    env.setdefault("GCM_INTERACTIVE", "never")
    try:
        proc = subprocess.run(
            ["git", "fetch", "--quiet", "--no-tags", "--no-write-fetch-head",
             "--no-auto-maintenance", "origin", branch],
            cwd=repo_path, capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=FETCH_TIMEOUT_S, env=env)
    except (OSError, subprocess.TimeoutExpired) as e:
        return "git fetch origin %s did not complete: %s" % (branch, e)
    if proc.returncode != 0:
        return "git fetch origin %s failed (rc %d): %s" % (
            branch, proc.returncode, (proc.stderr or "").strip()[:200])
    return None


def _parse_generated_at(raw, where):
    """(aware datetime, None) or (None, error)."""
    if not isinstance(raw, dict):
        return None, "%s snapshot is not a JSON object" % where
    meta = raw.get("meta")
    stamp = meta.get("generatedAt") if isinstance(meta, dict) else None
    if not isinstance(stamp, str) or not stamp:
        return None, "%s snapshot has no meta.generatedAt" % where
    try:
        dt = datetime.datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    except ValueError:
        return None, "%s snapshot has unparseable meta.generatedAt %r" % (where, stamp)
    if dt.tzinfo is None:
        return None, "%s snapshot meta.generatedAt %r has no timezone" % (where, stamp)
    return dt, None


HISTORY_COMMIT_CAP = 1000


def _committed_blobs(repo_path, ref, rel_path):
    """Every blob `rel_path` has had in `ref`'s history (last HISTORY_COMMIT_CAP
    commits touching it), or None when git cannot answer. One `git log --raw`."""
    # -m --full-history: without them a blob that only ever existed as a MERGE result
    # (never on either parent) emits no --raw line and would read as a local patch.
    rc, out = _git(["--no-optional-locks", "log", "-m", "--full-history", "--format=",
                    "--raw", "--no-abbrev", "--no-renames", "-n", str(HISTORY_COMMIT_CAP),
                    ref, "--", rel_path],
                   repo_path)
    if rc != 0:
        return None
    blobs = set()
    for line in out.splitlines():
        parts = line.split()
        if line.startswith(":") and len(parts) >= 4:
            for sha in (parts[2], parts[3]):
                if sha.strip("0"):
                    blobs.add(sha)
    return blobs


def _snapshot_freshness(repo_path, rel_path, canonical):
    """Compare the working-tree snapshot readers open against origin/<canonical>'s
    committed copy. Read-only; never raises."""
    ref = "origin/%s" % canonical
    out = {"snapshot_path": rel_path, "snapshot_ref": ref, "snapshot_stale": True,
           "snapshot_local_generated_at": None, "snapshot_origin_generated_at": None,
           "snapshot_lag_hours": None, "snapshot_content_matches_origin": None,
           "snapshot_local_newer": False, "snapshot_error": None}

    local_file = os.path.join(repo_path, *rel_path.split("/"))
    try:
        with open(local_file, encoding="utf-8-sig") as fh:
            local_doc = json.load(fh)
    except OSError as e:
        out["snapshot_error"] = "local %s unreadable: %s" % (rel_path, e)
        return out
    except ValueError as e:
        out["snapshot_error"] = "local %s is not valid JSON: %s" % (rel_path, e)
        return out
    local_dt, err = _parse_generated_at(local_doc, "local")
    if err:
        out["snapshot_error"] = err
        return out
    out["snapshot_local_generated_at"] = local_doc["meta"]["generatedAt"]

    rc, origin_blob = _git(["--no-optional-locks", "rev-parse", "--verify", "--quiet",
                            "%s:%s" % (ref, rel_path)], repo_path)
    if rc != 0 or not origin_blob:
        out["snapshot_error"] = "%s:%s does not resolve (ref unfetched, or file absent on %s)" % (
            ref, rel_path, ref)
        return out
    rc, origin_text = _git(["--no-optional-locks", "cat-file", "blob", origin_blob], repo_path)
    if rc != 0:
        out["snapshot_error"] = "cannot read %s:%s" % (ref, rel_path)
        return out
    try:
        origin_doc = json.loads(origin_text.lstrip("﻿"))
    except ValueError as e:
        out["snapshot_error"] = "%s:%s is not valid JSON: %s" % (ref, rel_path, e)
        return out
    origin_dt, err = _parse_generated_at(origin_doc, ref)
    if err:
        out["snapshot_error"] = err
        return out
    out["snapshot_origin_generated_at"] = origin_doc["meta"]["generatedAt"]

    # hash-object with a path applies the repo's clean filters (autocrlf/eol), so a
    # CRLF checkout of an LF blob still hashes equal. No -w: never writes.
    rc, local_blob = _git(["--no-optional-locks", "hash-object", "--", rel_path], repo_path)
    matches = (local_blob == origin_blob) if (rc == 0 and local_blob) else None
    out["snapshot_content_matches_origin"] = matches

    if local_dt < origin_dt:
        out["snapshot_lag_hours"] = round((origin_dt - local_dt).total_seconds() / 3600.0, 1)
        return out                                   # stale: readers see older data
    if local_dt > origin_dt:
        out["snapshot_local_newer"] = True
        out["snapshot_stale"] = False
        return out
    if matches is None:
        out["snapshot_error"] = "cannot hash local %s" % rel_path
        return out
    out["snapshot_lag_hours"] = 0.0
    if matches:
        out["snapshot_stale"] = False
        return out
    # Same stamp, different bytes. If the checkout's own HEAD copy already equals
    # origin's, the difference is a LOCAL in-place edit (e.g. ar-import-headless.ts
    # patchSnapshot, which rewrites the file without touching generatedAt) -- readers
    # see main's data plus that patch, not data main has replaced. Report, don't flag.
    # Otherwise main's committed bytes moved past this checkout: stale.
    rc, head_blob = _git(["--no-optional-locks", "rev-parse", "--verify", "--quiet",
                          "HEAD:%s" % rel_path], repo_path)
    if rc == 0 and head_blob and head_blob == origin_blob:
        # ...but only for bytes main never committed. A working tree holding an OLDER
        # committed version (stash/checkout of the old file, a dev server persisting a
        # stale in-memory copy) is exactly the stale case and must not pass as a patch.
        history = _committed_blobs(repo_path, ref, rel_path)
        if history is None:
            out["snapshot_error"] = ("cannot read %s history of %s to tell a local patch from "
                                     "a reverted copy" % (ref, rel_path))
            return out
        if local_blob in history:
            out["snapshot_reverted_to_older"] = True
            return out                                # stale: an old committed copy
        out["snapshot_locally_modified"] = True
        out["snapshot_stale"] = False
        return out
    out["snapshot_stale"] = True
    return out


def _git_status_short(repo_path):
    """[(status_code, path), ...] from `git status --short`, or None if the
    command itself failed (repo corrupt/locked -- distinct from 'no .git' at
    all, which is checked before this is ever called)."""
    try:
        proc = subprocess.run(
            # --no-optional-locks: no index.lock / stat-cache rewrite on a shared checkout.
            ["git", "--no-optional-locks", "status", "--short"], cwd=repo_path,
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


def scan_repo(repo_path, now=None, fetch=False, wip=True):
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

    canonical = canonical_branch_for(repo_path)
    snap_rel = snapshot_path_for(repo_path)
    branch_info = {}
    if fetch and (canonical or snap_rel):
        branch_info["fetch_error"] = _fetch(repo_path, canonical or "main")
    if canonical:
        branch_info.update(_branch_drift(repo_path, canonical))
    if snap_rel:
        branch_info.update(_snapshot_freshness(repo_path, snap_rel, canonical or "main"))
    corrector_path = _lookup(corrector_state_map(), repo_path)
    if corrector_path:
        branch_info.update(_corrector_streak(corrector_path))

    if not wip:
        # --freshness-only: WIP aging is not consulted, so do not run `git status`
        # on the shared checkout at all (daily probe; REFUTE finding C3).
        out = {"path": repo_path, "git_repo": True, "uncommitted_count": None,
               "oldest_age_hours": None, "stale": False, "missing": False,
               "wip_skipped": True}
        out.update(branch_info)
        return out
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


def scan_all(repos=None, fetch=False, wip=True):
    return [scan_repo(r, fetch=fetch, wip=wip) for r in (repos if repos is not None else known_repos())]


def any_snapshot_stale(results):
    return any(r.get("snapshot_stale") for r in results)


def any_fetch_failed(results):
    return any(r.get("fetch_error") for r in results)


def any_missing(results):
    return any(r.get("missing") for r in results)


def any_stale(results):
    return any(r["stale"] for r in results)


def any_branch_drift(results):
    return any(r.get("branch_drift") for r in results)


def any_corrector_stuck(results):
    return any(r.get("corrector_stuck") for r in results)


def format_report(results, freshness_only=False):
    lines = []
    for r in results:
        if freshness_only and not r.get("missing"):
            if not (r.get("branch_drift") or r.get("snapshot_stale") or r.get("fetch_error")):
                parts = []
                if r.get("current_branch"):
                    parts.append("on '%s', %s commit(s) behind origin/%s" % (
                        r["current_branch"], r.get("commits_behind_canonical"),
                        r.get("canonical_branch")))
                if r.get("snapshot_path"):
                    parts.append("%s generatedAt %s %s %s" % (
                        r["snapshot_path"], r.get("snapshot_local_generated_at"),
                        "newer than" if r.get("snapshot_local_newer") else
                        "locally modified, HEAD copy matches" if r.get("snapshot_locally_modified")
                        else "matches",
                        r.get("snapshot_ref")))
                lines.append("fresh    %s -- %s" % (r["path"], "; ".join(parts) or "nothing declared"))
        elif r.get("missing"):
            lines.append("[ACTION] MISSING %s -- configured as a known repo but has no "
                          ".git directory (archived/moved without updating this scan's "
                          "list, or a real problem)." % r["path"])
        elif r.get("error"):
            lines.append("[ACTION] ERROR %s -- %s" % (r["path"], r["error"]))
        elif r["uncommitted_count"] == 0:
            lines.append("clean    %s" % r["path"])
        elif r["stale"]:
            age = r["oldest_age_hours"]
            # None = every entry is a deletion (nothing to stat): stale-by-uncertainty.
            lines.append("[ACTION] STALE %s -- %d uncommitted item(s), oldest %s "
                          "(>= %dh threshold)" % (
                              r["path"], r["uncommitted_count"],
                              "unmeasurable" if age is None else "%.1fh" % age,
                              STALE_THRESHOLD_HOURS))
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
                                  r.get("behind_threshold", BRANCH_BEHIND_THRESHOLD)))
        if r.get("fetch_error"):
            lines.append("[ACTION] FETCH_FAILED %s -- %s; branch/snapshot comparison ran on the "
                         "last-fetched ref (unverified, not clean)" % (r["path"], r["fetch_error"]))
        if r.get("snapshot_stale"):
            if r.get("snapshot_error"):
                lines.append("[ACTION] SNAPSHOT_STALE %s -- cannot determine snapshot freshness: "
                             "%s" % (r["path"], r["snapshot_error"]))
            elif r.get("snapshot_content_matches_origin") is False and not r.get("snapshot_lag_hours"):
                lines.append("[ACTION] SNAPSHOT_STALE %s -- %s content differs from %s at the same "
                             "generatedAt %s; readers see bytes main has replaced" % (
                                 r["path"], r["snapshot_path"], r["snapshot_ref"],
                                 r["snapshot_local_generated_at"]))
                if r.get("snapshot_reverted_to_older"):
                    lines[-1] += " (working tree holds an OLDER committed version of the file)"
            else:
                lines.append("[ACTION] SNAPSHOT_STALE %s -- %s generatedAt %s trails %s's %s by "
                             "%.1fh; every reader of the on-disk copy sees older data. Advance the "
                             "checkout to %s (supervised, in-session -- shared single-writer "
                             "checkout)" % (
                                 r["path"], r["snapshot_path"], r["snapshot_local_generated_at"],
                                 r["snapshot_ref"], r["snapshot_origin_generated_at"],
                                 r["snapshot_lag_hours"], r["snapshot_ref"]))
        if freshness_only:
            continue
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


def main(argv=None):
    ap = argparse.ArgumentParser(description="Read-only WIP-aging / branch-drift / "
                                 "snapshot-freshness scan over the known local repos.")
    ap.add_argument("--repo", action="append", default=None,
                    help="scan only this configured repo (repeatable)")
    ap.add_argument("--freshness-only", action="store_true",
                    help="report/exit on MISSING, BRANCH_DRIFT, SNAPSHOT_STALE, FETCH_FAILED only")
    ap.add_argument("--fetch", action="store_true",
                    help="git fetch origin <canonical> first (remote-tracking ref only)")
    args = ap.parse_args(sys.argv[1:] if argv is None else argv)

    repos = known_repos()
    if args.repo:
        by_key = {_norm(r): r for r in repos}
        picked = []
        for want in args.repo:
            hit = by_key.get(_norm(want))
            if hit is None:
                print("ERROR --repo %s is not a configured repo (%s)" % (want, ", ".join(repos)))
                print("RESULT_JSON=%s" % json.dumps({"error": "unknown --repo", "repo": want}))
                return 2
            picked.append(hit)
        repos = picked
    if args.freshness_only:
        bare = [r for r in repos if not (canonical_branch_for(r) or snapshot_path_for(r))]
        if bare:
            print("ERROR --freshness-only: nothing declared to check for %s" % ", ".join(bare))
            print("RESULT_JSON=%s" % json.dumps({"error": "nothing to check", "repos": bare}))
            return 2

    results = scan_all(repos, fetch=args.fetch, wip=not args.freshness_only)
    print(format_report(results, freshness_only=args.freshness_only))
    print("RESULT_JSON=%s" % json.dumps(results))
    fresh_fail = (any_missing(results) or any_branch_drift(results)
                  or any_snapshot_stale(results) or any_fetch_failed(results))
    if args.freshness_only:
        return 1 if fresh_fail else 0
    return 1 if (fresh_fail or any_stale(results) or any_corrector_stuck(results)) else 0


if __name__ == "__main__":
    sys.exit(main())
