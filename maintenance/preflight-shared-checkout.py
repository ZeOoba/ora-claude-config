#!/usr/bin/env python3
"""preflight-shared-checkout.py -- read-only SINGLE-WRITER gate: "is it safe
for ME to start editing these paths, in this shared checkout, right now?"

WHY (found 2026-09-10, by scanning the last 20 sessions' Bash usage): CLAUDE.md
and the session-context block both mandate a preflight before touching a shared
checkout (~/.claude, ora-skills, website-canonical, oxford-command-center) --
"run `git log --oneline -1` + `git status`; if HEAD is newer than session-start
or uncommitted changes are not yours, STOP". That trio was typed by hand 181
times across 13 of the last 20 sessions, never twice the same way. Three
problems, all structural rather than anybody's carelessness:

  * The "is HEAD newer than session-start?" half was compared BY EYE against a
    sha nobody had written down. An eyeballed gate is not a gate.
  * `git status` in ~/.claude routinely returns 70-100 dirty files belonging to
    a dozen other sessions. Scanning that by hand for the two that overlap MY
    paths is exactly the reading task a person skips at 4pm.
  * The claims side (hooks/lib/claim_work.py) was a SEPARATE command that the
    hand-typed versions usually just left out, so a live claim on the very
    paths being edited went unseen.

This composes the three into one verdict with one exit code. It is the
pre-EDIT gate; the existing tools answer neighbouring questions and are
deliberately not duplicated here:

  * dirty-file-owner-report.py -- "whose WIP is this dirty file?" (attribution,
    after the fact, whole-repo).
  * cross-repo-wip-scan.py     -- "how long has the backlog been aging?"
                                  (periodic, whole-repo, unattended).
  * checkout-merge-forward.py  -- "fix the branch drift" (a corrector).
  * verify-push.py             -- "did the push actually land?" (post-push).

DESIGN STANCES carried over from those tools, each earned by a past failure:

  1. Every distinguishable finding gets its OWN exit code. A moved HEAD, an
     overlapping dirty file and a competing claim have different remedies;
     collapsing them into one generic "STOP" is how a session talks itself past
     the one that mattered.
  2. Not-requested is NOT unmeasurable. Omitting --since means the caller
     declined the HEAD check -- reported, still CLEAR. A claims directory we
     TRIED and failed to read is INDETERMINATE, and never green.
  3. Overlap is decided on PATH SEGMENTS, not string prefixes, in BOTH
     directions: a claim on `agents/` covers a request for `agents/foo.md`, and
     `agents/` never contests `agents-archive/`.
  4. The verdict survives a pipe. Piping a gate into `tail` masks its exit code
     -- the defect behind a past false "push succeeded" claim (memory:
     feedback_piped_gate_exit_masking) -- so a RESULT_JSON= line is printed on
     every outcome.
  5. READ-ONLY. It runs `rev-parse` and `status` and reads claim JSON. It never
     claims, commits, stashes, checks out or resets. It reports; you decide.

ACCEPTED LIMITATION: "mine" means mine among RECORDED touches. Provenance is
written by the Edit/Write tool hook, so another session's edit made through
Bash (sed, a redirect, a script) never appears, and a file I once touched can
read as mine alone. The same applies to two spelling cases provenance cannot
reconcile: a foreign touch recorded through a FILE symlink (different
basename, and creating one needs a privilege sessions do not hold), and one
recorded under a directory that was later renamed or removed. Junction and
8.3 directory/file spellings ARE reconciled (see _owners). Same
precision-over-recall tradeoff as
commit-provenance-guard.py; the claims check and HEAD check are the backstops.

LOCAL-ONLY ADVISORY (added 2026-09-12): when the checkout is NOT on its
canonical branch, report which scope paths are committed on this branch but
absent from `origin/<canonical>` (falling back to local `<canonical>`), plus how
many commits are unpushed to the upstream. Found when a CLEAR preflight let a
session edit the OI-249 merge-forward scripts assuming they would ship with
main -- they existed only on the checkout's never-pushed feature branch.
Advisory only: it never changes the exit code (the contract below is
test-pinned), and an unresolvable canonical ref is reported as "could not
check" with local_only_paths=null, never as an empty (clean) list. No fetch --
a stale origin ref can under-report, same limitation as cross-repo-wip-scan.

Usage:
    python maintenance/preflight-shared-checkout.py --paths P [P ...]
        [--repo PATH]        checkout to inspect (default: cwd)
        [--since SHA]        session-start sha; full or short. Omit to skip
                             the HEAD check (it is then reported "not checked")
        [--session ID]       my session id (default: $CLAUDE_CODE_SESSION_ID)
        [--claims-dir DIR]   default: <repo>/hooks/active-work, else
                             ~/.claude/hooks/active-work
        [--ttl-minutes N]    claim TTL, default 120 (matches claim_work.py)
        [--canonical BRANCH] branch the checkout should track, default main
                             (local-only advisory only)
        [--json]             machine-readable only, nothing else on stdout

    --paths accepts files or directories, absolute or relative to --repo.

Exit codes:
    0  CLEAR          nothing contests these paths -- go ahead
    1  CONTESTED      an overlapping dirty file, or another session's live claim
    2  NOT_A_REPO     --repo is not a git checkout, or git is unavailable
    3  HEAD_MOVED     --since given and HEAD is not that commit
    4  INDETERMINATE  a fact could not be established (claims unreadable) --
                      uncertain, never treated as clean

Precedence when several apply: NOT_A_REPO > HEAD_MOVED > CONTESTED >
INDETERMINATE > CLEAR. All findings are reported regardless of which one sets
the exit code.
"""
import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta

EXIT_CLEAR = 0
EXIT_CONTESTED = 1
EXIT_NOT_A_REPO = 2
EXIT_HEAD_MOVED = 3
EXIT_INDETERMINATE = 4

DEFAULT_TTL_MINUTES = 120  # matches claim_work.py's 2h window


# --------------------------------------------------------------------------
# path overlap -- segment-wise, both directions
# --------------------------------------------------------------------------
def _norm(p):
    """Absolute, case-folded, forward-slashed, no trailing separator.

    Case-folding is correct on Windows (the only host this runs on) and is also
    what claim_work.py already writes into its `paths`, so the two agree.
    """
    # realpath: a junction or an 8.3 short name (C:\Users\OWNER~1\...) is a
    # different spelling of the same directory. git reports the long real
    # path, so comparing spellings as strings made every overlap miss.
    p = os.path.realpath(os.path.abspath(p)).replace("\\", "/").rstrip("/")
    return p.lower()


def _overlaps(a, b):
    """True when a and b name the same path, or one CONTAINS the other.

    Segment-wise on purpose: `.../agents` must not match `.../agents-archive`,
    which a bare startswith() would.
    """
    a, b = _norm(a), _norm(b)
    if a == b:
        return True
    return a.startswith(b + "/") or b.startswith(a + "/")


def _any_overlap(path, scope):
    return any(_overlaps(path, s) for s in scope)


# --------------------------------------------------------------------------
# git facts
# --------------------------------------------------------------------------
def _git(repo, *args, **kw):
    """Never raises: a missing git binary or a timeout comes back as a failed
    call (rc 127), so NOT_A_REPO / the advisory's error paths handle it instead
    of a traceback exiting 1 -- which reads as CONTESTED and prints no
    RESULT_JSON. --no-optional-locks keeps `git status` from taking index.lock
    under a concurrent session's add/commit (this tool must stay read-only)."""
    try:
        return subprocess.run(["git", "--no-optional-locks", "-C", repo] + list(args),
                              capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=kw.get("timeout", 30))
    except (OSError, subprocess.TimeoutExpired) as exc:
        return subprocess.CompletedProcess(["git"] + list(args), 127, "", str(exc))


def _head_sha(repo):
    proc = _git(repo, "rev-parse", "HEAD")
    if proc.returncode != 0:
        return None
    return proc.stdout.strip()


def _dirty_paths(repo):
    """Absolute paths of everything `git status --porcelain` reports.

    Includes untracked files -- a stranger's brand-new file in my scope is
    exactly as much of a co-mingling hazard as a modified one. For a rename
    ("R  old -> new") both sides are returned: either may be in my scope.

    NUL-delimited (-z) on purpose: plain porcelain C-quotes non-ASCII names
    ("agents/caf\\303\\251.md"), and a quote-strip left the octal escapes in
    place, so such a file never matched its scope and the gate read CLEAR.
    Under -z paths are verbatim, and a rename entry is followed by its
    source path as a separate NUL field.
    """
    proc = _git(repo, "status", "--porcelain", "-z", "--untracked-files=all")
    if proc.returncode != 0:
        return None
    out = []
    fields = proc.stdout.split("\0")
    i = 0
    while i < len(fields):
        entry = fields[i]
        i += 1
        if len(entry) < 4:
            continue
        code, path = entry[:2], entry[3:]
        paths = [path]
        if "R" in code or "C" in code:
            if i < len(fields) and fields[i]:
                paths.append(fields[i])
            i += 1
        for part in paths:
            out.append(os.path.join(repo, part.replace("/", os.sep)))
    return out


def _local_only(repo, scope, canonical):
    """Advisory branch-identity facts. Returns a dict:
    current_branch, off_canonical, canonical_ref, canonical_ref_error,
    local_only_paths (None when unmeasurable), unpushed_commits (None when
    there is no upstream)."""
    info = {"current_branch": None, "off_canonical": None, "canonical_ref": None,
            "canonical_ref_error": None, "local_only_paths": None,
            "unpushed_commits": None}
    proc = _git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    if proc.returncode != 0:
        info["canonical_ref_error"] = "cannot resolve current branch"
        return info
    current = proc.stdout.strip()
    info["current_branch"] = current
    info["off_canonical"] = current != canonical

    proc = _git(repo, "rev-list", "--count", "@{u}..HEAD")
    if proc.returncode == 0 and proc.stdout.strip().isdigit():
        info["unpushed_commits"] = int(proc.stdout.strip())

    if not info["off_canonical"]:
        info["local_only_paths"] = []
        return info

    for ref in ("origin/%s" % canonical, canonical):
        if _git(repo, "rev-parse", "--verify", "--quiet", ref + "^{commit}").returncode == 0:
            info["canonical_ref"] = ref
            break
    else:
        info["canonical_ref_error"] = ("neither origin/%s nor %s resolves locally"
                                       % (canonical, canonical))
        return info

    rels = []
    for p in scope:
        if not _norm(p).startswith(_norm(repo) + "/") and _norm(p) != _norm(repo):
            continue  # outside this checkout
        rel = os.path.relpath(p, repo).replace("\\", "/")
        rels.append("" if rel == "." else rel)
    if not rels:
        info["local_only_paths"] = []
        return info

    def _tree_files(ref):
        proc = _git(repo, "ls-tree", "-r", "--name-only", ref, "--", *[r or "." for r in rels])
        return None if proc.returncode != 0 else set(proc.stdout.splitlines())

    here = _tree_files("HEAD")
    there = _tree_files(info["canonical_ref"])
    if here is None or there is None:
        info["canonical_ref_error"] = "git ls-tree failed"
        return info
    info["local_only_paths"] = sorted(here - there)
    return info


# --------------------------------------------------------------------------
# claims -- read the on-disk JSON contract directly
# --------------------------------------------------------------------------
def _default_sessions_dir():
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                        os.pardir, "hooks", "lib"))
        from commit_provenance import sessions_dir  # noqa: E402
        return sessions_dir()
    except Exception:
        return os.path.join(os.path.expanduser("~"), ".claude", "hooks",
                            "sessions")


def _scan_provenance(sessions_dir):
    """{normcase(abspath): set(session_id)} from every session's
    touched-files.txt, or (None) when the directory itself cannot be listed.

    Same source commit-provenance-recorder.py writes and
    dirty-file-owner-report.py reads -- deliberately not a second tracking
    mechanism. Read directly (one tab-separated line per touch) rather than
    importing read_touched(), so a mid-write hooks/lib does not take the
    preflight down with it.
    """
    if not os.path.isdir(sessions_dir):
        return None
    index = {}
    try:
        names = os.listdir(sessions_dir)
    except OSError:
        return None
    # Keys are stored raw, as the Edit hook saw them (possibly a junction or
    # 8.3 spelling); _owners() reconciles spellings at lookup time.
    for sid in names:
        tf = os.path.join(sessions_dir, sid, "touched-files.txt")
        if not os.path.isfile(tf):
            continue
        try:
            with open(tf, "r", encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    path = line.split("\t", 1)[0].strip()
                    if path:
                        index.setdefault(os.path.normcase(path), set()).add(sid)
        except OSError:
            continue  # one unreadable session is not a reason to fail the scan
    return index


def _owners(path, prov_index):
    """Session ids known to have touched `path`. Empty set == nobody recorded
    it, which is NOT the same as 'nobody touched it'."""
    if prov_index is None:
        return set()
    # A foreign touch recorded under a junction/8.3 spelling never equals the
    # realpath key, so the file read as mine alone (CLEAR). Match every
    # recorded key with the same basename by resolving ITS directory. Only a
    # handful of dirty-in-scope files are looked up, so resolving at lookup
    # time is cheap, where resolving all ~20k recorded lines at index time
    # took minutes.
    target = os.path.normcase(os.path.realpath(path))
    base = os.path.basename(target)
    owners = set(prov_index.get(target, set()))
    for key, sids in prov_index.items():
        if key == target:
            continue
        kbase = os.path.basename(key)
        if kbase != base:
            # An 8.3 FILE name (AVERYV~1.TXT) never shares the basename;
            # resolve the whole key, but only for '~' names that still exist.
            if "~" in kbase and os.path.exists(key):
                try:
                    if os.path.normcase(os.path.realpath(key)) == target:
                        owners |= sids
                except (OSError, ValueError):
                    pass
            continue
        d = os.path.dirname(key)
        if d not in _DIR_REAL:
            # A directory that no longer exists cannot be another spelling of
            # a live file's directory, and realpath on it is the slow case.
            try:
                _DIR_REAL[d] = (os.path.normcase(os.path.realpath(d))
                                if os.path.isdir(d) else None)
            except (OSError, ValueError):
                _DIR_REAL[d] = None
        if _DIR_REAL[d] and os.path.join(_DIR_REAL[d], base) == target:
            owners |= sids
    return owners


_DIR_REAL = {}  # per-run cache for _owners(): recorded dir -> normcase(realpath) | None


def _default_claims_dir(repo):
    # Same override claim_work.py honors -- otherwise the two can read
    # different directories and a live claim goes unseen.
    env = os.environ.get("ORA_ACTIVE_WORK_DIR")
    if env:
        return env
    local = os.path.join(repo, "hooks", "active-work")
    if os.path.isdir(local):
        return local
    return os.path.join(os.path.expanduser("~"), ".claude", "hooks",
                        "active-work")


def _read_claims(claims_dir, ttl_minutes):
    """Returns (claims, unreadable). Never raises on a bad file -- a claim we
    cannot parse is an UNKNOWN we must surface, not one we may skip.

    Reads the JSON files directly rather than importing claim_work.py: that
    module is itself frequently under concurrent edit in this checkout, and a
    preflight must not fail because the thing it inspects is mid-write.
    """
    claims, unreadable = [], []
    if not os.path.isdir(claims_dir):
        return None, [claims_dir]
    cutoff = datetime.now() - timedelta(minutes=ttl_minutes)
    try:
        names = sorted(os.listdir(claims_dir))
    except OSError as exc:
        return None, ["%s (%s)" % (claims_dir, exc)]
    for name in names:
        if not name.endswith(".json"):
            continue
        full = os.path.join(claims_dir, name)
        try:
            with open(full, "r", encoding="utf-8") as fh:
                rec = json.load(fh)
        except (OSError, ValueError) as exc:
            unreadable.append("%s (%s)" % (name, exc))
            continue
        if not isinstance(rec, dict):
            unreadable.append("%s (not a JSON object)" % name)
            continue
        raw = rec.get("claimed_at") or ""
        try:
            when = datetime.strptime(raw[:19], "%Y-%m-%dT%H:%M:%S")
        except ValueError:
            unreadable.append("%s (unparseable claimed_at %r)" % (name, raw))
            continue
        claims.append({
            "slug": rec.get("title") or name[:-5],
            "session_id": rec.get("session_id") or "",
            "description": rec.get("description") or "",
            "claimed_at": when.strftime("%Y-%m-%dT%H:%M:%S"),
            "expired": when < cutoff,
            "paths": [p for p in (rec.get("paths") or []) if isinstance(p, str)],
        })
    return claims, unreadable


# --------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(
        description="Single-writer preflight for a shared git checkout.")
    ap.add_argument("--paths", nargs="+", required=True,
                    help="files/dirs you are about to edit (abs or rel to --repo)")
    ap.add_argument("--repo", default=os.getcwd())
    ap.add_argument("--since", default=None,
                    help="session-start sha; omit to skip the HEAD check")
    ap.add_argument("--session", default=os.environ.get("CLAUDE_CODE_SESSION_ID", ""))
    ap.add_argument("--claims-dir", default=None)
    ap.add_argument("--sessions-dir", default=None,
                    help="commit-provenance sessions dir (attribution)")
    ap.add_argument("--ttl-minutes", type=int, default=DEFAULT_TTL_MINUTES)
    ap.add_argument("--canonical", default="main",
                    help="branch this checkout should track (local-only advisory)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    repo = os.path.abspath(args.repo)
    out = []          # human-readable lines, suppressed under --json
    def say(line=""):
        out.append(line)

    # --- fact 0: is this even a checkout? -------------------------------
    head = _head_sha(repo) if os.path.isdir(repo) else None
    if head is None:
        report = {"verdict": "NOT_A_REPO", "repo": repo,
                  "detail": "not a git checkout, or git unavailable"}
        _emit(report, ["NOT A GIT CHECKOUT: %s" % repo], args.json)
        return EXIT_NOT_A_REPO

    # Relative --paths resolve against the directory the caller named, but
    # every git-reported path is relative to the TOPLEVEL. Joining porcelain
    # output onto a subdirectory --repo (the cwd default when run from
    # maintenance/) matched nothing and read CLEAR -- so after scope is
    # resolved, `repo` becomes the toplevel for every other fact.
    # Both scope and repo go through realpath so every later relpath/overlap
    # compares one spelling (see _norm).
    scope = [os.path.realpath(os.path.join(repo, p) if not os.path.isabs(p) else p)
             for p in args.paths]
    top = _git(repo, "rev-parse", "--show-toplevel")
    if top.returncode == 0 and top.stdout.strip():
        repo = os.path.realpath(top.stdout.strip())
    else:
        repo = os.path.realpath(repo)

    # --- fact 1: has HEAD moved since session start? --------------------
    # A blank or very short --since prefix-matches almost any HEAD and would
    # report "unchanged". Under 7 hex chars the fact cannot be established.
    head_moved, since_error = None, None
    if args.since is not None:
        since = args.since.strip().lower()
        if len(since) < 7 or any(ch not in "0123456789abcdef" for ch in since):
            since_error = "--since %r is not a sha of at least 7 hex chars" % args.since
        else:
            head_moved = not (head.lower().startswith(since)
                              or since.startswith(head.lower()))

    # --- fact 2: dirty files overlapping my scope -----------------------
    dirty = _dirty_paths(repo)
    if dirty is None:
        report = {"verdict": "NOT_A_REPO", "repo": repo,
                  "detail": "git status failed"}
        _emit(report, ["git status failed in %s" % repo], args.json)
        return EXIT_NOT_A_REPO
    # Attribute each overlapping dirty file. "Not yours" is the doctrine's
    # actual test -- flagging my OWN in-progress edit would make the gate fire
    # on every re-run, which is how gates get bypassed. A file with no recorded
    # owner, or one ALSO touched by someone else, stays foreign: unknown and
    # shared are both hazards, only "provably mine alone" is exempt.
    sessions_dir = args.sessions_dir or _default_sessions_dir()
    prov_index = _scan_provenance(sessions_dir)
    mine = (args.session or "").lower()

    dirty_overlap_mine, dirty_overlap_foreign = [], []
    for p in dirty:
        if not _any_overlap(p, scope):
            continue
        rel = os.path.relpath(p, repo).replace("\\", "/")
        owners = _owners(p, prov_index)
        # Exact id match: an 8-char prefix of a SHORT --session ('b') made
        # every 'b...' session's file read as mine.
        only_mine = bool(owners) and bool(mine) and all(
            o.lower() == mine for o in owners)
        if only_mine:
            dirty_overlap_mine.append({"path": rel,
                                       "owners": sorted(owners)})
        else:
            dirty_overlap_foreign.append({"path": rel,
                                          "owners": sorted(owners)})
    dirty_overlap_mine.sort(key=lambda d: d["path"])
    dirty_overlap_foreign.sort(key=lambda d: d["path"])

    # --- fact 3: other sessions' live claims overlapping my scope -------
    claims_dir = args.claims_dir or _default_claims_dir(repo)
    claims, unreadable = _read_claims(claims_dir, args.ttl_minutes)

    competing, expired_overlap = [], []
    if claims is not None:
        for c in claims:
            if not any(_any_overlap(p, scope) for p in c["paths"]):
                continue
            if c["session_id"] and mine and c["session_id"].lower() == mine:
                continue  # my own claim (exact id; see ownership note above)
            (expired_overlap if c["expired"] else competing).append(c)

    # --- advisory: is this work landing only on a non-canonical branch? ---
    branch_info = _local_only(repo, scope, args.canonical)

    # --- verdict --------------------------------------------------------
    indeterminate = claims is None or bool(unreadable) or bool(since_error)
    contested = bool(dirty_overlap_foreign) or bool(competing)

    if head_moved:
        verdict, code = "HEAD_MOVED", EXIT_HEAD_MOVED
    elif contested:
        verdict, code = "CONTESTED", EXIT_CONTESTED
    elif indeterminate:
        verdict, code = "INDETERMINATE", EXIT_INDETERMINATE
    else:
        verdict, code = "CLEAR", EXIT_CLEAR

    report = {
        "verdict": verdict,
        "repo": repo,
        "head": head,
        "since": args.since,
        "head_moved": head_moved,          # null == not checked / uncheckable
        "since_error": since_error,
        "scope": [os.path.relpath(p, repo).replace("\\", "/")
                  if _norm(p).startswith(_norm(repo)) else p for p in scope],
        "dirty_overlap_foreign": dirty_overlap_foreign,
        "dirty_overlap_mine": dirty_overlap_mine,
        "dirty_total": len(dirty),
        "sessions_dir": sessions_dir,
        "provenance_available": prov_index is not None,
        "competing_claims": competing,
        "expired_claims_overlapping": expired_overlap,
        "claims_dir": claims_dir,
        "claims_unreadable": unreadable,
        "canonical": args.canonical,
    }
    report.update(branch_info)

    # --- human-readable ------------------------------------------------
    say("PREFLIGHT %s -- %s" % (verdict, repo))
    say("  scope        : %s" % ", ".join(report["scope"]))
    if since_error:
        say("  HEAD         : %s  NOT CHECKED -- %s" % (head[:12], since_error))
    elif head_moved is None:
        say("  HEAD         : %s  (--since not given: not checked)" % head[:12])
    elif head_moved:
        say("  HEAD         : %s  MOVED since %s" % (head[:12], args.since))
    else:
        say("  HEAD         : %s  unchanged since session start" % head[:12])
    if dirty_overlap_foreign:
        say("  NOT-YOURS dirty in scope (%d of %d dirty in repo):"
            % (len(dirty_overlap_foreign), len(dirty)))
        for d in dirty_overlap_foreign[:20]:
            who = ", ".join(o[:8] for o in d["owners"]) or "no recorded owner"
            say("      %s   [%s]" % (d["path"], who))
        if len(dirty_overlap_foreign) > 20:
            say("      ... and %d more" % (len(dirty_overlap_foreign) - 20))
    else:
        say("  not-yours dirty in scope: none (%d dirty elsewhere in repo)"
            % len(dirty))
    if dirty_overlap_mine:
        say("  (your own uncommitted edits in scope, not contesting: %s)"
            % ", ".join(d["path"] for d in dirty_overlap_mine[:10]))
    if prov_index is None:
        say("  CAVEAT: provenance unavailable (%s) -- nothing can be proven"
            " yours, so every overlap is treated as not-yours." % sessions_dir)
    if competing:
        say("  COMPETING CLAIMS:")
        for c in competing:
            say("      %s  session %s  (%s)  -- %s"
                % (c["slug"], (c["session_id"] or "?")[:8], c["claimed_at"],
                   c["description"][:70]))
    else:
        say("  competing claims: none")
    for c in expired_overlap:
        say("  (expired claim ignored: %s  session %s  %s)"
            % (c["slug"], (c["session_id"] or "?")[:8], c["claimed_at"]))
    for u in unreadable:
        say("  UNREADABLE claim: %s" % u)
    if claims is None:
        say("  claims could not be read at all -- verdict is INDETERMINATE")
    if branch_info["off_canonical"]:
        unpushed = branch_info["unpushed_commits"]
        push_note = ("no upstream" if unpushed is None
                     else "%d unpushed commit(s)" % unpushed)
        if branch_info["local_only_paths"] is None:
            say("  LOCAL-ONLY ?  : on '%s', not '%s' -- could not check what exists on"
                " %s: %s (%s)" % (branch_info["current_branch"], args.canonical,
                                  args.canonical, branch_info["canonical_ref_error"],
                                  push_note))
        elif branch_info["local_only_paths"]:
            lop = branch_info["local_only_paths"]
            say("  LOCAL-ONLY   : on '%s', not '%s' (%s). %d scope path(s) exist on this"
                " branch but NOT on %s -- edits here land only on this branch:"
                % (branch_info["current_branch"], args.canonical, push_note, len(lop),
                   branch_info["canonical_ref"]))
            for p in lop[:20]:
                say("      %s" % p)
            if len(lop) > 20:
                say("      ... and %d more" % (len(lop) - 20))
        else:
            say("  branch       : on '%s', not '%s' (%s); no scope path is committed only"
                " on this branch vs %s"
                % (branch_info["current_branch"], args.canonical, push_note,
                   branch_info["canonical_ref"]))
    say()
    say({
        "CLEAR": "  -> go ahead.",
        "CONTESTED": "  -> STOP. Reconcile with the other session, or scope"
                     " into an isolated worktree.",
        "HEAD_MOVED": "  -> STOP. Re-read the files you are about to edit;"
                      " the checkout advanced under you.",
        "INDETERMINATE": "  -> uncertain, not clean. Establish the missing"
                         " fact before editing.",
        "NOT_A_REPO": "  -> not a checkout.",
    }[verdict])

    _emit(report, out, args.json)
    return code


def _emit(report, lines, as_json):
    if as_json:
        sys.stdout.write(json.dumps(report, indent=1) + "\n")
        return
    for line in lines:
        sys.stdout.write(line + "\n")
    # Always last, always one line: survives being piped into `tail`.
    sys.stdout.write("RESULT_JSON=" + json.dumps(report) + "\n")


def _utf8_stdout():
    """A piped Windows stdout is cp1252: an emoji file name in the human lines
    raised UnicodeEncodeError, exiting 1 with no RESULT_JSON. json.dumps is
    ASCII-escaped already; only the human lines need this."""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass


if __name__ == "__main__":
    _utf8_stdout()
    sys.exit(main())
