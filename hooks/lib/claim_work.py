"""Cross-session claim/broadcast primitive for ad-hoc work on shared ~/.claude
subsystems that have no per-path single-writer rule (unlike ora-skills,
scheduled-task registries, workflows/).

WHY (2026-07-25, task_17998414): reference_concurrent_session_duplicate_hardening_work.md
logs 6 recorded collisions where two sessions independently duplicated work on the same
shared subsystem without knowing about each other -- most severely, two sessions each
hardening the same override-token defect in different gate files on 2026-07-16, found
only by chance via `git worktree list`. The existing mitigation (manually run
`git worktree list` + check `list_sessions` before starting hook/security work) already
failed to catch that exact collision. This module is the "touch a marker file naming the
subsystem you're about to fix" convention the same reference file predicted, generalized
to a small free-form vocabulary of subsystem slugs (see docs/superpowers/specs/
2026-07-25-cross-session-claim-broadcast-design.md for the full design and why each
choice below matches an already-ratified pattern elsewhere in this codebase).

DESIGN, one line each:
  * One JSON file per claim (hooks/active-work/<slug>.json), never a shared file --
    same no-lock-needed argument fleet-session-hook.py's 2026-07-24 per-session-file
    rewrite already proved out (it moved OFF a shared session-state.json + mutex after
    that measurably lost data under concurrency).
  * Fail-open, TTL-expired (2 hours), NOT a hard lock -- matches tech.md Sec3d's ratified
    Master Workbook doctrine ("a crashed session holding a hard claim would wedge every
    other session -- a worse failure than an occasional missed collision").
  * Written by hand (via this module's CLI), not auto-detected by a PreToolUse hook --
    classifying "non-trivial hook work" from a single tool call has too high a false
    positive/negative rate; stays a documented convention, like the two existing named
    single-writer rules.

NOT a security boundary: any session can release or overwrite any claim file (no
ownership enforcement). It is a courtesy broadcast, not an access-control mechanism --
matching the existing single-writer rules, which are also conventions, not gates.

RENEWAL (added 2026-08-04, open-items-tracker.md OI-072 handoff near-miss): `claimed_at`
was originally set once, at initial `claim`, and nothing prompted a session doing
continued multi-step work under one slug to touch it again. A claim's reported age then
drifts from "time since this session was last active" to "time since one single past
event" -- a reader (this module's own `list` output, or another session via
active-work-broadcast.py's SessionStart context) can misjudge a still-live, still-being-
worked claim as abandoned purely because the timestamp is old and the frozen description
reads as already finished. `renew_claim()` / `claim_work.py renew <slug>` bumps
`claimed_at` to now on a claim the calling session already holds (refuses -- returns
None / exits 1 -- if the slug has no live claim, or a DIFFERENT session holds it, so it
can never be used to quietly take over someone else's slug). Convention: run it
periodically ("I'm still here, still on this") rather than claiming once and letting a
multi-hour session's timestamp sit unchanged. Separately, `claim` now WARNS (does not
block -- still fail-open) when it is about to overwrite a different session's still-live
claim, closing the matching gap where that overwrite previously happened silently.

Stdlib only. ASCII-only. Windows (`python`).
"""
import datetime
import json
import os
import sys
# NOTE: `argparse` is imported lazily inside main(), NOT here. Measured 2026-07-26:
# importing it costs ~46 ms, and this module is imported by two hooks that run on the
# hot path -- shared-checkout-guard.py on EVERY Edit/Write, active-work-broadcast.py on
# every session start -- neither of which ever touches the CLI. That was ~46 ms of pure
# waste per edit for a dependency only the `python claim_work.py ...` entry point uses.

CLAIMS_DIR = os.environ.get("ORA_ACTIVE_WORK_DIR") or \
    r"C:\Users\Owner\.claude\hooks\active-work"
MAX_CLAIM_FILES = 512    # see read_active_claims(): hot-path scan bound
MAX_CLAIM_BYTES = 64 * 1024
DEFAULT_TTL_MINUTES = 120  # headroom above the 90-min stuck-session-watchdog kill
                            # threshold, so a legitimately long task's claim survives
                            # while a genuinely stuck session's claim goes stale before
                            # it can mislead anyone for long


def _safe_filename(slug):
    """Filesystem-safe encoding of a subsystem slug, mirroring
    fleet-session-hook.py's _safe_filename() for session ids -- defense-in-depth,
    not a format assumption (slugs are free-form, agent-supplied strings)."""
    safe = "".join(c if (c.isalnum() or c in "-_") else "_" for c in (slug or "unknown"))
    return safe + ".json"


def claim_path(slug, base_dir=None):
    return os.path.join(base_dir or CLAIMS_DIR, _safe_filename(slug))


def norm_path(p):
    """Canonical on-disk form for path comparison. Deliberately IDENTICAL to
    commit_provenance.norm() (normcase + abspath) so a claim-declared path and a
    provenance-recorded touched path compare equal on Windows, where the same file
    is reachable as `C:\\x\\Y.md`, `c:/x/y.md`, and a relative path from any cwd.
    Not imported from commit_provenance: this module is stdlib-only and must keep
    working if that module is missing/broken (same fail-open posture as the rest of
    it), and the two definitions are asserted equal by the test suite."""
    return os.path.normcase(os.path.abspath(p))


def _clean_paths(paths):
    """Normalize an agent-supplied path list. Fail-soft: a non-list, or any member
    that is not a usable string, is dropped rather than raised -- `paths` is
    free-form agent input on a courtesy mechanism, and a bad value must never cost
    a caller its claim (or, worse, crash the PreToolUse guard that reads it)."""
    if not isinstance(paths, (list, tuple)):
        return []
    out = []
    for p in paths:
        if not isinstance(p, str) or not p.strip():
            continue
        try:
            out.append(norm_path(p.strip()))
        except Exception:
            continue
    return sorted(set(out))


def _now_iso(now=None):
    return (now or datetime.datetime.now()).strftime("%Y-%m-%dT%H:%M:%S")


def _parse_iso(s):
    try:
        return datetime.datetime.strptime(s, "%Y-%m-%dT%H:%M:%S")
    except Exception:
        return None


def own_session_id():
    return (os.environ.get("CLAUDE_CODE_SESSION_ID") or
            os.environ.get("CLAUDE_CODE_HOST_SESSION_ID") or "unknown")


def write_claim(slug, session_id, description, title=None, cwd=None, base_dir=None,
                 now=None, paths=None):
    """Write (or overwrite) this session's claim on `slug`. Atomic rename + a
    pid-unique tmp name, same pattern as fleet-session-hook.py's save_session() --
    closes the exact same "two writers share one tmp path" hazard that pattern was
    built to avoid, even though here only one process should ever be claiming a
    given slug at a time (two sessions racing to claim the SAME slug at the SAME
    instant is the collision this module exists to make visible after the fact,
    not something it needs to prevent at write time)."""
    base_dir = base_dir or CLAIMS_DIR
    os.makedirs(base_dir, exist_ok=True)
    data = {
        "session_id": session_id,
        "title": title or slug,
        "description": description,
        "claimed_at": _now_iso(now),
        "cwd": cwd or os.getcwd(),
        # ADDED 2026-07-26 (defect D1). Optional and always present-but-possibly-empty
        # so readers never branch on absence. Slugs are work-TYPE scoped, so two
        # sessions editing one file under two honest slugs
        # ("ora-weekly-hygiene-spec" and "repo-housekeeping", observed same-day)
        # were indistinguishable from two sessions on unrelated subsystems. Paths are
        # what make a same-FILE collision expressible at all.
        "paths": _clean_paths(paths),
    }
    path = claim_path(slug, base_dir)
    tmp = "%s.tmp.%d" % (path, os.getpid())
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f)
    os.replace(tmp, path)
    return path


def release_claim(slug, base_dir=None):
    """Best-effort delete. Not required for correctness -- an unreleased claim
    simply ages out past DEFAULT_TTL_MINUTES -- but keeps the broadcast quiet
    sooner when a session remembers to call it.

    WEAKER GUARANTEE while shared-checkout-guard.py's self-renewal is active
    (added 2026-08-04, independent review finding): that hook bumps `claimed_at`
    on ALL of a session's live claims on every edit inside a claim-relevant repo,
    keyed only on session_id -- not on whether the edit relates to the specific
    slug being renewed. A finished-but-unreleased claim therefore keeps looking
    fresh for as long as the session keeps editing ANYWHERE in that repo, not
    just DEFAULT_TTL_MINUTES past when the work actually stopped. Calling
    `release` once a task is actually done matters MORE now than the "not
    required for correctness" framing above suggests on its own."""
    path = claim_path(slug, base_dir or CLAIMS_DIR)
    try:
        os.remove(path)
        return True
    except Exception:
        return False


def read_active_claims(base_dir=None, ttl_minutes=DEFAULT_TTL_MINUTES, now=None):
    """Every non-expired claim currently on disk. Fail-open throughout: a missing
    directory, an unreadable/malformed individual file, or a non-dict payload are
    all skipped rather than raised -- mirrors session_liveness.py's
    other_active_sessions() contract (never raise, degrade to "no information").
    A claim with an unparseable or future `claimed_at` is also dropped rather than
    trusted, since a caller cannot age-order a claim it can't parse."""
    base_dir = base_dir or CLAIMS_DIR
    now = now or datetime.datetime.now()
    out = []
    try:
        names = os.listdir(base_dir)
    except Exception:
        return out
    # HARD CAPS (2026-07-26, adversarial review). This directory is world-writable
    # by design and nothing ever deletes from it -- release_claim is opt-in and
    # best-effort, so it only grows. Since this module is now read on the Edit/Write
    # hot path (not just at SessionStart), an unbounded scan is a self-DoS: measured
    # 100 files -> 2.5x hook latency, 2,000 -> 17x, 20,000 -> 217x (~33 s per edit,
    # under the 60 s hook timeout, so it degrades silently rather than erroring).
    # Sorted for determinism: which claims survive the cap must not depend on
    # filesystem enumeration order.
    names = sorted(n for n in names if n.endswith(".json"))
    if len(names) > MAX_CLAIM_FILES:
        names = names[:MAX_CLAIM_FILES]
    for name in names:
        # ".json" filter applied above; that also excludes "<slug>.json.tmp.<pid>"
        # leftovers, which do not end in ".json".
        path = os.path.join(base_dir, name)
        try:
            # Size gate BEFORE open(): a claim is a handful of short fields, so
            # anything large is either corrupt or hostile. Cheap stat beats reading
            # a 200 MB "claim" into memory on every edit.
            if os.path.getsize(path) > MAX_CLAIM_BYTES:
                continue
            with open(path, "r", encoding="utf-8") as f:
                d = json.load(f)
        except Exception:
            continue
        if not isinstance(d, dict):
            continue
        claimed_at = _parse_iso(d.get("claimed_at", ""))
        if claimed_at is None:
            continue
        age_minutes = (now - claimed_at).total_seconds() / 60.0
        if age_minutes > ttl_minutes or age_minutes < 0:
            continue
        out.append({
            "slug": name[:-5],
            "session_id": d.get("session_id", "?"),
            "title": d.get("title", "?"),
            "description": d.get("description", ""),
            "claimed_at": d.get("claimed_at", ""),
            "cwd": d.get("cwd", ""),
            # Re-normalized on READ, not trusted as written: claim files are
            # world-writable by design ("NOT a security boundary", above), so a
            # hand-edited or older-format file may carry raw/relative paths. Running
            # them back through _clean_paths() means a malformed `paths` value
            # degrades to [] (no match) instead of raising inside a PreToolUse hook.
            "paths": _clean_paths(d.get("paths")),
            "age_minutes": age_minutes,
        })
    out.sort(key=lambda c: c["age_minutes"])
    return out


def find_claim(slug, base_dir=None, ttl_minutes=DEFAULT_TTL_MINUTES, now=None):
    """The single live (non-expired) claim on `slug`, or None. Thin convenience
    wrapper over read_active_claims() for the single-slug lookups renew_claim()
    and the CLI's collision warning both need -- neither has to know
    read_active_claims()'s list-of-all-slugs shape.

    Compares against `_safe_filename(slug)`, NOT the raw `slug` -- read_active_claims()
    reports `"slug"` as the on-disk filename stem, which is already the SANITIZED form
    (`_safe_filename` maps any char outside [A-Za-z0-9-_] to "_"). Every documented slug
    (repo-housekeeping, hooks-override-auth, ...) happens to already be filename-safe, so
    comparing against the raw slug looked correct under every existing test -- but slugs
    are documented as free-form agent-supplied strings, and a raw comparison silently
    never matches the moment one contains a space or other sanitized character, making
    both renew_claim() and the CLI's collision warning dead code for that slug without
    ever raising (caught 2026-08-04 independent review)."""
    target = _safe_filename(slug)[:-5]
    for c in read_active_claims(base_dir=base_dir, ttl_minutes=ttl_minutes, now=now):
        if c["slug"] == target:
            return c
    return None


def renew_claim(slug, session_id, description=None, base_dir=None, now=None,
                ttl_minutes=DEFAULT_TTL_MINUTES):
    """Bump `claimed_at` to `now` on a claim `session_id` ALREADY holds, without
    needing to re-supply title/cwd/paths. Returns the pre-renewal claim dict on
    success, or None if there is nothing of this session's to renew (no live
    claim on `slug`, or it is held by a different session_id) -- callers should
    treat None as a reportable error, never fall back to silently creating a
    fresh claim, so `renew` can never be used to quietly take over someone
    else's slug (that is what `claim` is for, and `claim` now warns when it
    happens).

    WHY (2026-08-04, open-items-tracker.md's OI-072 handoff near-miss):
    `claimed_at` was previously set once, at initial `claim`, with nothing
    prompting a session doing continued multi-step work under one slug to
    touch it again. A claim's age then drifts from "time since this session
    was last active" to "time since one single past event," and a reader
    (human or another session, via active-work-broadcast.py's %.0fm-ago
    display) can misjudge a still-live claim as abandoned/completed purely
    because the timestamp is old and the frozen description reads as already
    finished -- exactly what happened when a session read a 28-minute-old
    "convert test_cross_repo_wip_scan.py" claim as stale (that specific task
    WAS done) and reclaimed the slug for unrelated work, not realizing the
    claiming session had simply moved on to a second task under the same
    banner claim without renewing it. See reference_concurrent_session_
    duplicate_hardening_work.md's 2026-08-04 entry for the full incident.

    `description`, if given, replaces the stored description (use this to keep
    the broadcast text current as work moves between sub-tasks); if omitted,
    the existing description is kept as-is so a "just extend my TTL, nothing
    changed" renewal doesn't require re-typing it.
    """
    existing = find_claim(slug, base_dir=base_dir, ttl_minutes=ttl_minutes, now=now)
    if existing is None or existing.get("session_id") != session_id:
        return None
    write_claim(slug, session_id,
               description if description is not None else existing.get("description", ""),
               title=existing.get("title"), cwd=existing.get("cwd"),
               base_dir=base_dir, now=now, paths=existing.get("paths"))
    return existing


def _path_overlap(wanted, declared):
    """Paths in `wanted` covered by `declared` -- exact match OR inside a declared
    DIRECTORY.

    WHY prefix matching (2026-07-26, found by both reviewers): the CLI advertises
    "Files/dirs this claim covers", but the first cut did a plain set intersection,
    so `--paths scheduled-tasks/ora-weekly-hygiene` (the natural granularity for
    directory-scoped work, and exactly the shape of the incident that motivated all
    of this) matched the directory itself and NOTHING inside it -- while still
    printing "covering 1 path(s) -- other sessions editing them will be warned".
    A silent no-op behind an affirmative confirmation is worse than no feature.

    Prefix comparison is on a separator-terminated string so `/foo/bar` never
    matches the sibling `/foo/barbecue`."""
    declared = set(declared or [])
    if not declared:
        return set()
    out = set(wanted) & declared
    for d in declared:
        pref = d.rstrip("\\/") + os.sep
        for w in wanted:
            if w.startswith(pref):
                out.add(w)
    return out


def claims_touching(paths, base_dir=None, ttl_minutes=DEFAULT_TTL_MINUTES, now=None,
                    exclude_session=None):
    """Live claims whose declared `paths` intersect `paths`.

    The pre-edit half of the file-collision signal: it fires on a claim alone, before
    the claiming session has written anything, so it covers the window that
    provenance (touched-files.txt, necessarily written only AFTER a first edit)
    structurally cannot. Fail-open like everything else here -- an unreadable claims
    dir yields [], never an exception, because the caller is a PreToolUse hook and an
    exception there would surface as a tool failure on an unrelated edit.

    `exclude_session` drops the caller's own claims: a session being warned about
    itself is noise that trains the reader to ignore the signal."""
    wanted = set(_clean_paths(list(paths or [])))
    if not wanted:
        return []
    hits = []
    for c in read_active_claims(base_dir=base_dir, ttl_minutes=ttl_minutes, now=now):
        if exclude_session and c.get("session_id") == exclude_session:
            continue
        overlap = _path_overlap(wanted, c.get("paths") or [])
        if overlap:
            c = dict(c)
            c["matched_paths"] = sorted(overlap)
            hits.append(c)
    return hits


def main():
    import argparse  # lazy: CLI-only, see the import block at the top of this module
    p = argparse.ArgumentParser(
        description="Claim or release a shared ~/.claude subsystem for ad-hoc work, "
                     "so other sessions' SessionStart hook broadcasts it automatically. "
                     "See docs/superpowers/specs/2026-07-25-cross-session-claim-broadcast-design.md")
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("claim", help="Register a claim on a subsystem slug")
    c.add_argument("slug", help="e.g. hooks-override-auth, open-items-tracker, "
                                 "oxford-command-center-data, repo-housekeeping")
    c.add_argument("description", help="One line: what you're doing and why")
    c.add_argument("--title")
    c.add_argument("--paths", nargs="*", default=None,
                   help="Files and/or DIRECTORIES this claim covers (a directory "
                        "covers everything beneath it). Slugs are work-TYPE scoped, so "
                        "two honest slugs can collide on one file (observed 2026-07-26: "
                        "three sessions, one SKILL.md, zero warnings). Declaring paths "
                        "makes shared-checkout-guard.py warn any other session that "
                        "edits them -- BEFORE it has written anything.")

    rn = sub.add_parser("renew", help="Bump claimed_at on a claim THIS session already "
                                      "holds, without re-supplying title/paths. Run this "
                                      "periodically during continued multi-step work "
                                      "under one slug -- a claim's age is otherwise time "
                                      "since the ORIGINAL claim, not time since this "
                                      "session was last active, and an old timestamp "
                                      "reads to other sessions as abandoned/done.")
    rn.add_argument("slug")
    rn.add_argument("--description", help="Replace the stored description (e.g. moving "
                                          "to a new sub-task under the same slug). Omit "
                                          "to keep the existing one and just extend the TTL.")

    r = sub.add_parser("release", help="Clear a claim you previously made")
    r.add_argument("slug")

    sub.add_parser("list", help="List all currently live (non-expired) claims")

    args = p.parse_args()

    if args.cmd == "claim":
        sid = own_session_id()
        existing = find_claim(args.slug)
        if existing is not None and existing.get("session_id") != sid:
            print("WARNING: '%s' has a LIVE claim held by a different session "
                  "(%s, %.0fm ago -- %s). Overwriting it now -- if that session is "
                  "still working, its broadcast context is replaced with yours and "
                  "other sessions will no longer see its claim." % (
                      args.slug, str(existing.get("session_id", "?"))[:8],
                      existing.get("age_minutes", 0.0), existing.get("description", "")))
        path = write_claim(args.slug, sid, args.description, title=args.title,
                           paths=args.paths)
        n = len(_clean_paths(args.paths))
        print("Claimed '%s' as session %s -> %s" % (args.slug, sid, path))
        if n:
            print("  covering %d path(s) -- other sessions editing them will be warned" % n)
        else:
            print("  NOTE: no --paths given. This claim broadcasts the slug only, so a "
                  "session editing the same FILE under a different slug will NOT be "
                  "warned (defect D1, 2026-07-26). Pass --paths for file-level cover.")
        print("  For continued work under this slug, run 'claim_work.py renew %s' "
              "periodically rather than letting this timestamp age -- see 'renew -h'."
              % args.slug)
        return 0

    if args.cmd == "renew":
        sid = own_session_id()
        result = renew_claim(args.slug, sid, description=args.description)
        if result is None:
            existing = find_claim(args.slug)
            if existing is None:
                print("No live claim found for '%s' to renew -- use 'claim' to start "
                      "one." % args.slug)
            else:
                print("Claim on '%s' is held by a different session (%s), not this "
                      "one -- 'renew' only extends a claim THIS session already holds. "
                      "Use 'claim' if you intend to take it over (this will warn, not "
                      "block)." % (args.slug, str(existing.get("session_id", "?"))[:8]))
            return 1
        print("Renewed '%s' (was %.0fm old) -- session %s" % (
            args.slug, result["age_minutes"], sid))
        return 0

    if args.cmd == "release":
        ok = release_claim(args.slug)
        print(("Released '%s'" % args.slug) if ok else
              ("No claim found for '%s' (already released or expired)" % args.slug))
        return 0

    if args.cmd == "list":
        claims = read_active_claims()
        if not claims:
            print("No active claims.")
        for cl in claims:
            print("%s: session %s, %.0fm ago -- %s" % (
                cl["slug"], cl["session_id"][:8], cl["age_minutes"], cl["description"]))
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
