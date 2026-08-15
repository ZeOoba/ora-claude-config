"""Cross-session claim/broadcast primitive for ad-hoc work on shared ~/.claude
subsystems that have no per-path single-writer rule (unlike ora-skills,
scheduled-task registries, workflows/).

SLUGS ARE FREE-FORM (2026-08-15 clarification, prompted by an ora-skills-scoped
maintenance task defaulting to the generic 'repo-housekeeping' slug for lack of a
narrower one on record): `claim <slug>` accepts ANY string -- there is no fixed
enum anywhere in this module. The four names printed in --help
(hooks-override-auth, open-items-tracker, oxford-command-center-data,
repo-housekeeping) are a DOCUMENTED VOCABULARY that has grown by precedent (see
active-work-broadcast.py's docstring for the 2026-07-26 repo-housekeeping
addition), not a closed set enforced anywhere. When a task's scope is a distinct
repo or subsystem repo-housekeeping doesn't already cover -- e.g. ora-skills --
coin a new slug (ora-skills-housekeeping) rather than reusing repo-housekeeping
for everything ~/.claude-side; a distinct slug keeps BOTH claims independently
visible (see paths_conflict()'s "prefer a distinct slug" guidance, printed on a
provably-disjoint collision), where reusing one slug for unrelated work would
make the second claim silently overwrite the first's broadcast.

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
multi-hour session's timestamp sit unchanged.

REFUSAL (added 2026-08-09, superseding the 2026-08-04 warn-only behaviour): `claim`
used to overwrite a different session's still-live claim unconditionally, printing its
WARNING only AFTER the decision was made -- so the warning could only ever document a
clobber, never prevent one. It destroyed live claims twice (open-items-tracker OI-075;
and 2026-08-09, a two-minute-old claim destroyed while its owner was actively removing
worktrees, restored only by hand-rewriting the JSON). `claim` now exits
EXIT_CLAIM_REFUSED and writes NOTHING in that case, unless `--force`/`--steal`; a forced
takeover preserves the displaced claim in `prior_claim`, and `restore` puts it back.
This does not weaken the fail-open posture above, which is about the READ path: no hook
invokes this CLI, so no exit code here can reach the Edit/Write hot path; `--force` is
unconditional, so a crashed session can never lock anyone out; and a claim that cannot
be attributed to a session at all (missing/placeholder `session_id`) still fails OPEN,
so a malformed file can never deny a slug.

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
# Exit-code registry for this CLI, since 3 only makes sense against the others:
#   0 = did what you asked          2 = argparse usage error (argparse's own choice)
#   1 = nothing to act on (`renew` with no claim of yours, `restore` with nothing
#       superseded)                 3 = below
EXIT_CLAIM_REFUSED = 3   # `claim`/`restore` declined to clobber another session's live
                          # claim. Distinct from 1 so a caller can tell "you asked for
                          # something impossible" from "someone else is already here"
                          # without parsing stdout.
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
    """This session's identity for ownership matching -- guaranteed ATTRIBUTABLE.

    Normalized at the source (adversarial REFUTE, 2026-08-09) so no live session can
    ever write an id that attributable_session() rejects. The env var was previously
    used verbatim: `CLAUDE_CODE_SESSION_ID="  "` is truthy, so it survived the `or`
    chain and was stored as `"  "` -- which strips to empty and reads as
    unattributable. That session then had NO collision protection at all, with no
    symptom it could observe (its own `renew` still succeeded), while any other
    session's plain `claim` took the slug at exit 0. An empty string already fell
    through to "unknown"; whitespace and the "?" placeholder did not."""
    sid = (os.environ.get("CLAUDE_CODE_SESSION_ID") or
           os.environ.get("CLAUDE_CODE_HOST_SESSION_ID") or "unknown").strip()
    return sid if (sid and sid != "?") else "unknown"


def own_host_session_id():
    """The CCD HOST session id ("local_<uuid>") -- a DIFFERENT namespace from
    own_session_id()'s CLAUDE_CODE_SESSION_ID agent id, not a fallback for it.

    WHY BOTH (2026-08-09): list_scheduled_tasks' sibling tools -- list_sessions and
    send_message -- only ever speak the host id, while claim files, the
    fleet-session-hook mirror (its `_sid`) and session_liveness.py all speak the agent
    id. No artifact carried both, so a live claim could be READ but its owner could not
    be CONTACTED: two claim ids this session tried to resolve against list_sessions
    ("1d24d6a4", "b09003a0") looked like phantom sessions when both were in fact live
    and present in the mirror under the agent-id namespace.

    Recorded ALONGSIDE the agent id, never instead of it -- own_session_id() stays the
    identity used for ownership matching (renew/release/collision), so claims remain
    joinable to the agent-id-keyed mirror. Returns "" when unset (an unattended or
    scheduled session may not carry it) so callers never branch on absence, matching the
    `paths` present-but-possibly-empty precedent. Deliberately NOT defaulted to
    "unknown": that string is a legal agent id here, and a host-id field carrying it
    would read as a real target and be pasted into send_message.
    """
    return (os.environ.get("CLAUDE_CODE_HOST_SESSION_ID") or "").strip()


# A host id is a machine-generated handle ("local_<uuid>"): printable ASCII, no
# whitespace, short. Anything else in that field did not come from the runtime.
# Checked with a plain scan rather than `re`: this module is imported by
# shared-checkout-guard.py on EVERY Edit/Write, and the header note above is explicit
# about not paying import cost on that hot path for something the check does not need.
_HOST_ID_MAX = 128


def _clean_host_session_id(value):
    """Normalize the host id ON READ to 'a usable target, or nothing'.

    Claim JSON is world-writable by design, and this field is rendered into
    model-visible SessionStart context AND printed by `list` for an agent to copy into
    send_message. Normalizing at this single choke point (rather than at each display
    site) means every consumer receives either a clean id or "", so no caller has to
    re-derive "is this empty?" -- an earlier version of the broadcast tested raw
    truthiness, and a whitespace-only value sailed through it into the sanitizer, which
    renders "" as the placeholder "(no description)". The result was the absurd
    "(message it at (no description))".

    Degrades to "" (never raises, never truncates): a truncated or control-char-bearing
    host id is unresolvable anyway, so surfacing a mangled one would advertise a target
    that cannot be messaged. Same fail-open posture as _clean_paths().
    """
    if not isinstance(value, str):
        return ""
    v = value.strip()
    if not v or len(v) > _HOST_ID_MAX:
        return ""
    # Printable ASCII, no spaces (0x21..0x7e). Excludes every control character,
    # newline and tab -- i.e. everything that could break a rendered line.
    for ch in v:
        if not ("\x21" <= ch <= "\x7e"):
            return ""
    return v


_PRIOR_CLAIM_FIELDS = ("session_id", "host_session_id", "title", "description",
                        "claimed_at", "cwd", "paths")


def _strip_prior(claim):
    """The restorable subset of a claim, ONE LEVEL DEEP.

    Dropping any nested `prior_claim` is the load-bearing part, not tidiness: a
    takeover chain A -> B -> C would otherwise embed B's copy of A inside C, and so on
    without bound. Claim files are size-gated at MAX_CLAIM_BYTES on a path that runs on
    every Edit/Write, so an unbounded nest degrades into "this claim is silently skipped
    as corrupt" -- the read side fails open, meaning a long chain would quietly turn
    into no claim at all. Only the IMMEDIATELY superseded claim is restorable, which is
    also the only one a `--force` operator can meaningfully be said to have displaced.

    Returns None -- never an empty dict -- for anything that is not a dict or that
    carries none of the restorable fields, so a hand-edited or hostile `prior_claim`
    degrades to "nothing to restore" instead of raising. The `or None` is load-bearing
    (independent review, 2026-08-09): `restore` tests `is None` while write_claim tests
    truthiness, and a `{}` return made those two guards disagree -- a claim file with
    `"prior_claim": {"unrelated_key": 1}` passed `is None` and installed a live,
    broadcasting claim owned by the literal string "unknown" over a real one."""
    if not isinstance(claim, dict):
        return None
    return {k: claim.get(k) for k in _PRIOR_CLAIM_FIELDS if k in claim} or None


def attributable_session(claim):
    """The session id `claim` can actually be attributed to, or None.

    read_active_claims() substitutes the placeholder "?" for a MISSING `session_id`,
    and a hand-written file may carry null or a non-string. Such a claim names no
    session, so no other session can be "different from" it -- and treating it as a
    collision would let one malformed file in a world-writable directory DENY a slug to
    every session until its TTL expired. That is a fail-CLOSED inversion the pre-refusal
    code did not have (caught by the old-vs-new differential battery, 2026-08-09), so
    unattributable claims are overwritten as before, with a note.

    The literal "unknown" is deliberately NOT treated as unattributable: own_session_id()
    returns it for an unattended or scheduled session with no id in the environment, and
    that session's work is real. Two such sessions already read as each other -- a
    pre-existing blind spot in the id namespace, not something this check can fix."""
    sid = (claim or {}).get("session_id")
    if not isinstance(sid, str):
        return None
    sid = sid.strip()
    return sid if (sid and sid != "?") else None


def read_prior_claim(slug, base_dir=None):
    """The claim metadata a `--force` takeover superseded on `slug`, or None.

    Reads the claim file directly rather than going through read_active_claims():
    that function's output shape is consumed on the Edit/Write hot path and rendered
    into model-visible `additionalContext` by active-work-broadcast.py, and
    `prior_claim` carries a second set of free-form, un-sanitized `title`/`description`
    text. Keeping it off that shape means no broadcast site can start interpolating it
    by accident -- the spec's own Phase 2 constraint ("any new field interpolated there
    needs the same [sanitization]"), satisfied by not putting it there at all.

    Deliberately NOT TTL-filtered: a superseded claim is history, not a live claim, and
    is restorable regardless of how old it is (`restore` warns about the age instead).
    Fail-open like every other reader here."""
    path = claim_path(slug, base_dir or CLAIMS_DIR)
    try:
        if os.path.getsize(path) > MAX_CLAIM_BYTES:
            return None
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
    except Exception:
        return None
    if not isinstance(d, dict):
        return None
    return _strip_prior(d.get("prior_claim"))


def paths_conflict(mine, theirs):
    """TRI-STATE overlap verdict between two claims' declared paths:
    True = they overlap, False = provably disjoint, None = undeterminable.

    The third state is the whole point. `paths` is optional (defect D1) and most
    claims never declare it, so "no declared paths" must read as "cannot prove these
    are disjoint" -- NEVER as "disjoint". Collapsing None into False would invert the
    safe default and hand a confident all-clear to precisely the pathless banner claims
    that carry the least information.

    Checked in BOTH directions because _path_overlap() is asymmetric: it expands
    DIRECTORIES on the `declared` side only. Whichever claim happened to name the
    directory, a file underneath it is the same contended file, so a one-way check
    would miss the collision exactly half the time."""
    mine = _clean_paths(mine)
    theirs = _clean_paths(theirs)
    if not mine or not theirs:
        return None
    if _path_overlap(mine, theirs) or _path_overlap(theirs, mine):
        return True
    return False


def write_claim(slug, session_id, description, title=None, cwd=None, base_dir=None,
                 now=None, paths=None, host_session_id=None, prior_claim=None):
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
        # ADDED 2026-08-09. The CCD host id ("local_<uuid>") that list_sessions and
        # send_message speak -- see own_host_session_id(). Present-but-possibly-empty
        # (same contract as `paths`) so readers never branch on absence. ADDITIVE:
        # `session_id` above remains the ownership identity for renew/release/collision.
        "host_session_id": host_session_id or "",
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
    # ADDED 2026-08-09. Written when a claim displaces another session's -- a `--force`
    # takeover, a displacing `restore`, or the no-force fail-open overwrite of an
    # unattributable claim -- and carried forward by `renew` and by a plain re-claim so
    # it is not silently dropped. An UNCONTESTED claim's on-disk shape is still
    # byte-identical to before. Readers must treat it as optional; read_active_claims()
    # deliberately does not surface it (see read_prior_claim()).
    prior = _strip_prior(prior_claim)
    if prior:
        data["prior_claim"] = prior
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
            # Defaulted AND normalized, not trusted as written -- same posture as
            # `paths` below. Absent key (pre-2026-08-09 file), null, a non-string, a
            # whitespace-only value, an over-long one, or one carrying control
            # characters all degrade to "" rather than reaching a display site.
            "host_session_id": _clean_host_session_id(d.get("host_session_id")),
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
    else's slug (that is what `claim --force` is for -- since 2026-08-09 a bare
    `claim` refuses the takeover outright rather than warning after the fact).

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
               base_dir=base_dir, now=now, paths=existing.get("paths"),
               # Carried forward from the existing claim, NOT re-read from the
               # environment: renew is a rewrite, and anything not passed through here
               # is silently dropped from the file.
               host_session_id=existing.get("host_session_id"),
               # Same hazard, second instance (2026-08-09): `prior_claim` is written by
               # a --force takeover and is the ONLY record of the displaced session.
               # shared-checkout-guard.py self-renews a session's own claims roughly
               # every 20 minutes, so without this the restore data would evaporate on
               # its own within one renewal cycle -- long before the operator who forced
               # the takeover noticed they had destroyed the thing they meant to
               # preserve. Re-read from disk because read_active_claims() (which
               # produced `existing`) deliberately omits the field.
               prior_claim=read_prior_claim(slug, base_dir=base_dir))
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


_DISPLAY_MAX = 300


def _one_line(value):
    """Collapse an agent-supplied claim field to a single printable ASCII line.

    Claim JSON is world-writable by design and its free text is read back by a MODEL
    (this CLI's stdout lands in an agent's tool result), so the same treatment
    active-work-broadcast.py already applies before rendering a description into
    `additionalContext` applies here: a crafted description carrying newlines could
    otherwise forge extra output lines -- e.g. a fake 'Claimed ... -> ...' success
    line under a REFUSED header. Collapse, strip control characters, truncate."""
    if not isinstance(value, str):
        return ""
    flat = "".join(ch if ("\x20" <= ch <= "\x7e") else " " for ch in value)
    flat = " ".join(flat.split())
    return flat[:_DISPLAY_MAX - 3] + "..." if len(flat) > _DISPLAY_MAX else flat


def _fmt_paths(paths):
    """Render a claim's declared paths for display -- EACH ONE sanitized.

    _clean_paths() only normcase/abspath's them, which preserves newlines, and paths
    come off the same world-writable claim file the descriptions do. Printing them raw
    (introduced with the collision report, caught in review 2026-08-09) let a hostile
    `paths` entry forge whole output lines -- a fake 'Claimed ... -> ...' success line
    underneath a REFUSED header, which is precisely the forgery _one_line() exists to
    prevent. Every field interpolated into operator/model-visible output goes through
    it; there are no exceptions, and a new one must not be added."""
    paths = _clean_paths(paths)
    return ", ".join(_one_line(p) for p in paths) if paths else "(none declared)"


def _collision_report(slug, existing, my_paths, overlap, refused=True):
    """The lines describing a slug collision, shared by the REFUSED and --force
    branches so a takeover shows exactly what it is displacing.

    `overlap` is paths_conflict()'s tri-state verdict; each state gets its own
    closing recommendation, because the right next move genuinely differs: provably
    disjoint work wants a distinct slug, provably overlapping work wants a
    conversation, and undeterminable wants the conservative assumption."""
    sid8 = _one_line(str(existing.get("session_id", "?")))[:8]
    lines = ["%s: '%s' has a LIVE claim held by session %s (%.0fm ago)." % (
        "REFUSED" if refused else "FORCED TAKEOVER", slug, sid8,
        existing.get("age_minutes", 0.0))]
    lines.append("  Their work:  %s" % _one_line(existing.get("description", "")))
    host = existing.get("host_session_id") or ""
    if host:
        # The reason host_session_id was recorded at all (2026-08-09): a claim you
        # can read but whose owner you cannot contact leaves no move except clobbering.
        lines.append("  Contact:     send_message to %s" % host)
    lines.append("  Their paths: %s" % _fmt_paths(existing.get("paths")))
    lines.append("  Your paths:  %s" % _fmt_paths(my_paths))
    if overlap is True:
        mine, theirs = _clean_paths(my_paths), _clean_paths(existing.get("paths"))
        # Union of both directions, mirroring paths_conflict()'s bidirectional test:
        # reporting only `mine & theirs` would print an empty parenthetical whenever
        # the sole reason they conflict is a DIRECTORY on one side covering a file on
        # the other -- an overlap verdict with no visible evidence for it.
        matched = _path_overlap(mine, theirs) | _path_overlap(theirs, mine)
        lines.append("  -> These OVERLAP (%s). You are about to collide with, or "
                     "duplicate, live work." % _fmt_paths(sorted(matched)))
    elif overlap is False:
        lines.append("  -> These do NOT overlap. Prefer a distinct slug (e.g. "
                     "'%s-<scope>') so BOTH claims stay visible -- one claim file "
                     "per slug means taking this one hides theirs." % slug)
    else:
        lines.append("  -> Overlap cannot be determined (one or both claims declare "
                     "no --paths). Assume conflict.")
    return lines


def main():
    import argparse  # lazy: CLI-only, see the import block at the top of this module
    p = argparse.ArgumentParser(
        description="Claim or release a shared ~/.claude subsystem for ad-hoc work, "
                     "so other sessions' SessionStart hook broadcasts it automatically. "
                     "See docs/superpowers/specs/2026-07-25-cross-session-claim-broadcast-design.md")
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("claim", help="Register a claim on a subsystem slug")
    c.add_argument("slug", help="e.g. hooks-override-auth, open-items-tracker, "
                                 "oxford-command-center-data, repo-housekeeping, "
                                 "ora-skills-housekeeping. Free-form -- coin a new, "
                                 "narrower slug for a distinct repo/subsystem rather "
                                 "than reusing repo-housekeeping for everything ~/.claude"
                                 "-side (that slug's own scope is the ~/.claude checkout "
                                 "itself, not ora-skills or other repos beneath it); see "
                                 "active-work-broadcast.py's docstring for how the "
                                 "vocabulary has grown before.")
    c.add_argument("description", help="One line: what you're doing and why")
    c.add_argument("--title")
    # action="extend" (not the former bare nargs="*"): with plain nargs, argparse
    # OVERWRITES on a repeated flag, so `--paths a --paths b` silently recorded only
    # ["b"] -- observed live 2026-08-09, a two-path claim covering one path, with the
    # dropped one being the file actually being edited. Silently under-covering defeats
    # the file-level cover that defect D1 added. extend accumulates across repeats and
    # still accepts the space-separated form.
    c.add_argument("--paths", nargs="*", action="extend", default=None,
                   help="Files and/or DIRECTORIES this claim covers (a directory "
                        "covers everything beneath it). Slugs are work-TYPE scoped, so "
                        "two honest slugs can collide on one file (observed 2026-07-26: "
                        "three sessions, one SKILL.md, zero warnings). Declaring paths "
                        "makes shared-checkout-guard.py warn any other session that "
                        "edits them -- BEFORE it has written anything.")
    # --steal is a synonym, not a second mode: both the incident reports and the
    # original defect write-up reached for either word, and having one of them be a
    # usage error at the exact moment an operator is trying to break a deadlock is a
    # gratuitous failure.
    c.add_argument("--force", "--steal", action="store_true", dest="force",
                   help="Take the slug over even though another session holds a live "
                        "claim on it. Without this, that case REFUSES (exit %d) and "
                        "writes nothing. The displaced claim is preserved in the new "
                        "claim's `prior_claim` field -- 'claim_work.py restore <slug>' "
                        "puts it back." % EXIT_CLAIM_REFUSED)

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
    r.add_argument("--force", "--steal", action="store_true", dest="force",
                   help="Release a claim that is NOT yours, or one that still carries "
                        "a '--force' takeover's undo record. Both refuse (exit %d) "
                        "without this." % EXIT_CLAIM_REFUSED)

    rt = sub.add_parser("restore", help="Put back the claim a '--force' takeover "
                                        "displaced on this slug, from the metadata "
                                        "that takeover preserved.")
    rt.add_argument("slug")
    rt.add_argument("--force", "--steal", action="store_true", dest="force",
                    help="Restore even though a DIFFERENT session has claimed the slug "
                         "since your takeover. Without this, that case refuses (exit "
                         "%d) rather than clobbering them -- the same gate `claim` "
                         "applies." % EXIT_CLAIM_REFUSED)

    sub.add_parser("list", help="List all currently live (non-expired) claims")

    args = p.parse_args()

    if args.cmd == "claim":
        sid = own_session_id()
        existing = find_claim(args.slug)
        holder = attributable_session(existing) if existing is not None else None
        if existing is not None and holder is None:
            # Fail OPEN, loudly: a claim naming no session cannot be collided with,
            # and must never be able to deny the slug (see attributable_session()).
            print("NOTE: '%s' has a live claim file naming no session -- it cannot be "
                  "attributed, so it is being overwritten rather than allowed to block "
                  "you. Its metadata is kept in this claim's `prior_claim` field for "
                  "manual recovery -- NOT via 'restore', which refuses an entry naming "
                  "no session (putting it back would install a claim owned by nobody)."
                  % args.slug)
        colliding = holder is not None and holder != sid
        if colliding:
            overlap = paths_conflict(args.paths, existing.get("paths"))
            for line in _collision_report(args.slug, existing, args.paths, overlap,
                                          refused=not args.force):
                print(line)
            if not args.force:
                # THE FIX (2026-08-09). This used to overwrite unconditionally and
                # print the warning AFTERWARDS, so the warning could only ever
                # document a clobber, never prevent one -- recorded twice, most
                # recently when a claim two minutes old was destroyed while its owner
                # was actively removing worktrees, and had to be restored by hand.
                #
                # Refusing here does NOT contradict this module's fail-open doctrine,
                # which is about the READ path: no hook calls this CLI (hooks import
                # read_active_claims / claims_touching / renew_claim), so nothing on
                # the Edit/Write hot path can be wedged by an exit code here. And
                # --force is unconditional, so a crashed session's claim can never
                # lock anyone out -- the property tech.md Sec3d actually ratified.
                print("Nothing was written. Re-run with --force (alias --steal) to "
                      "take the slug over anyway; the displaced claim is preserved "
                      "and restorable.")
                return EXIT_CLAIM_REFUSED
            print("--force given: proceeding with the TAKEOVER. The displaced claim "
                  "is preserved in this claim's `prior_claim` -- restore it with:")
            print("    python claim_work.py restore %s" % args.slug)
        path = write_claim(args.slug, sid, args.description, title=args.title,
                           paths=args.paths, host_session_id=own_host_session_id(),
                           # `holder != sid` deliberately, NOT `colliding`. It covers
                           # the unattributable case too (holder None): fail-open must
                           # mean "does not BLOCK you", never "does not PRESERVE what
                           # it overwrote". The narrower `colliding` test discarded a
                           # live-but-unattributable claim irretrievably at exit 0 --
                           # re-opening, through the fail-open branch, the exact
                           # unrecoverable clobber the refusal exists to prevent
                           # (adversarial REFUTE, 2026-08-09).
                           prior_claim=(existing
                                        if (existing is not None and holder != sid)
                                        # NOT None (final review, 2026-08-11): the
                                        # else-branch used to drop the undo record on
                                        # the floor, destroying at exit 0 the one
                                        # artifact --force's own output promises is
                                        # "preserved and restorable". Two live
                                        # sequences: (a) the forcing session re-claims
                                        # its OWN slug to update the description --
                                        # holder == sid, so the record vanished; (b) the
                                        # takeover claim ages past the TTL, find_claim
                                        # returns None, and the next plain claim
                                        # overwrites the file -- while `release` in that
                                        # identical state REFUSES, because
                                        # read_prior_claim is deliberately not
                                        # TTL-filtered. Two write paths disagreeing
                                        # about one invariant is the bug. Same
                                        # carry-forward pattern renew_claim already
                                        # uses; a real takeover still replaces it,
                                        # preserving one-step-undo semantics.
                                        else read_prior_claim(args.slug)))
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
                      "'claim' will REFUSE it too; use 'claim --force' if you truly "
                      "intend to take it over." % (
                          args.slug, _one_line(str(existing.get("session_id", "?")))[:8]))
            return 1
        print("Renewed '%s' (was %.0fm old) -- session %s" % (
            args.slug, result["age_minutes"], sid))
        return 0

    if args.cmd == "release":
        # `release` is the FOURTH write path, and the refusal gate is worthless
        # without it (adversarial REFUTE, 2026-08-09): `release <slug>` followed by
        # `claim <slug>` achieved at exit 0, with no REFUSED line and nothing
        # restorable, exactly what `claim` alone now refuses. The unconditional
        # os.remove predates this change; leaving it unguarded while gating `claim`
        # would have shipped a lock with the door next to it propped open.
        sid = own_session_id()
        existing = find_claim(args.slug)
        holder = attributable_session(existing) if existing is not None else None
        if existing is not None and holder != sid and not args.force:
            if holder is not None:
                overlap = paths_conflict(None, existing.get("paths"))
                for line in _collision_report(args.slug, existing, None, overlap):
                    print(line)
            else:
                print("REFUSED: '%s' has a live claim file naming no session. It is "
                      "not yours to release, and deleting it discards whatever it "
                      "records." % args.slug)
            print("Nothing was deleted. 'release' clears a claim; it does not take "
                  "one over. Re-run with --force if you really mean to delete it.")
            return EXIT_CLAIM_REFUSED
        # Second half of the same finding, and this one IS introduced here: the undo
        # record for a `--force` takeover lives INSIDE the claim file, so the forcing
        # session releasing its own claim silently destroys the only copy of the
        # displaced session's claim -- after being told it was "restorable".
        if read_prior_claim(args.slug) is not None and not args.force:
            print("REFUSED: '%s' still carries the claim your '--force' takeover "
                  "displaced. Releasing it deletes that record permanently -- the "
                  "displaced session would have nothing to come back to." % args.slug)
            print("  Put it back instead:  python claim_work.py restore %s" % args.slug)
            print("  Or, if that claim is genuinely finished, re-run with --force.")
            return EXIT_CLAIM_REFUSED
        ok = release_claim(args.slug)
        print(("Released '%s'" % args.slug) if ok else
              ("No claim found for '%s' (already released or expired)" % args.slug))
        return 0

    if args.cmd == "restore":
        prior = read_prior_claim(args.slug)
        if prior is None or attributable_session(prior) is None:
            print("No superseded claim recorded on '%s' -- nothing to restore. "
                  "(Only a '--force' takeover records one, and only the claim it "
                  "displaced. A recorded entry naming no session is not restorable: "
                  "putting it back would install a claim owned by nobody.)" % args.slug)
            return 1
        # RESTORE IS A WRITE, so it gets the SAME gate `claim` does (independent
        # review, 2026-08-09). The first cut wrote unconditionally, without even
        # looking at who currently held the slug -- which reintroduced the exact
        # unconditional clobber this whole change exists to remove, and made it
        # strictly worse: it was one-way, recording no `prior_claim`, so an unrelated
        # third session could destroy a live claim with exit 0 and nothing to undo it.
        # Demonstrated: A claims -> A2 forces -> an unrelated C runs `restore` and A2's
        # live claim is gone. Symmetry is the invariant to hold onto -- every path that
        # can displace a live claim refuses by default, reports what it would displace,
        # and preserves it.
        sid = own_session_id()
        current = find_claim(args.slug)
        holder = attributable_session(current) if current is not None else None
        displacing = holder is not None and holder != sid
        if displacing:
            overlap = paths_conflict(prior.get("paths"), current.get("paths"))
            for line in _collision_report(args.slug, current, prior.get("paths"),
                                          overlap, refused=not args.force):
                print(line)
            if not args.force:
                print("Nothing was written. That claim is NOT the one your restore "
                      "would put back -- someone has taken the slug since. Re-run "
                      "with --force to displace them anyway (their claim is then "
                      "preserved in turn, and restorable).")
                return EXIT_CLAIM_REFUSED
        # `claimed_at` is restored VERBATIM, not re-stamped to now. This is a
        # restoration, not a fresh claim: the displaced session's age is a fact about
        # when IT started, and re-stamping would silently hand it a full new TTL it
        # never asked for. The consequence is that a long-delayed restore can put back
        # an already-expired claim, so say so rather than let it look successful.
        # An UNPARSEABLE claimed_at falls back to "already expired", not to now (final
        # review, 2026-08-11): re-stamping it would hand the restored claim exactly the
        # full fresh TTL the paragraph above says restore must never grant, and would do
        # so precisely for the hand-edited/corrupt files least entitled to it. Expired
        # is the honest reading of "we do not know when this was claimed", and the age
        # NOTE below then fires and says so.
        when = _parse_iso(prior.get("claimed_at", "")) or (
            datetime.datetime.now() - datetime.timedelta(minutes=DEFAULT_TTL_MINUTES + 1))
        write_claim(args.slug, attributable_session(prior),
                    prior.get("description") or "", title=prior.get("title"),
                    cwd=prior.get("cwd"), now=when, paths=prior.get("paths"),
                    host_session_id=prior.get("host_session_id"),
                    # Symmetry again: if this restore displaced someone, THEY are now
                    # the restorable party. Without this, `restore --force` would be
                    # the one write in this module that destroys a claim irretrievably.
                    # Same `holder != sid` widening as the claim branch above -- an
                    # unattributable current holder is still a live claim being
                    # overwritten, and still has to be preserved.
                    prior_claim=current if (current is not None and
                                            holder != sid) else None)
        print("Restored '%s' to session %s (originally claimed %s)." % (
            args.slug, _one_line(attributable_session(prior))[:8],
            _one_line(str(prior.get("claimed_at", "?")))))
        age = (datetime.datetime.now() - when).total_seconds() / 60.0
        if age > DEFAULT_TTL_MINUTES:
            print("  NOTE: that timestamp is %.0fm old, past the %dm TTL -- the "
                  "restored claim is already expired and will not broadcast. Ask "
                  "that session to re-claim if it is still working." % (
                      age, DEFAULT_TTL_MINUTES))
        return 0

    if args.cmd == "list":
        claims = read_active_claims()
        if not claims:
            print("No active claims.")
        for cl in claims:
            # The host id is printed IN FULL and unabbreviated -- unlike the 8-char
            # agent id, it is meant to be copied straight into send_message, and a
            # truncated one would not resolve.
            host = cl.get("host_session_id") or ""
            print("%s: session %s%s, %.0fm ago -- %s" % (
                cl["slug"], cl["session_id"][:8],
                (" (host %s)" % host) if host else "",
                cl["age_minutes"], cl["description"]))
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
