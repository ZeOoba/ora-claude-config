#!/usr/bin/env python3
"""dirty-file-owner-report.py -- read-only "who owns each dirty file" reporter
for a shared ~/.claude-style checkout.

WHY (2026-08-12 close-out automation candidate; see project_primary_checkout_
main_move_blocked_2026-08-12.md): a relayed handoff asked to force-move the
primary ~/.claude checkout onto main. Its git-state facts (branch, ahead/
behind counts) were correct, but it never flagged that the checkout's 117
uncommitted files were live WIP spanning 15+ concurrent sessions, not stale
clutter -- that breadth surfaced only as an incidental side effect of a
config-write-guard block on an unrelated write, not because any existing tool
answered "whose work is this?" directly. This script answers that question on
demand by composing primitives that already exist for other purposes:
  * `git status --porcelain` -- the dirty/untracked file set itself.
  * hooks/lib/commit_provenance.py -- each session's own touched-files.txt
    (written by commit-provenance-recorder.py's PostToolUse hook), read for
    EVERY session directory found on disk, not just currently-live ones --
    the WIP this tool exists to surface is exactly the kind that outlives
    its session.
  * hooks/lib/claim_work.py -- claims whose declared --paths cover a dirty
    file, for the pre-first-edit window provenance structurally cannot see.
  * hooks/lib/session_liveness.py -- enrichment only, to mark an attributed
    session as still open vs. already ended.

NOT a gate. NOT a hook. Never blocks, never writes anything. Composition
only -- no new tracking infrastructure. See reference_concurrent_session_
duplicate_hardening_work.md and feedback_verify_before_repeating_session_
claims.md for the incident history this closes a visibility gap in.

Usage:
  python dirty-file-owner-report.py                  # human-readable report
  python dirty-file-owner-report.py --json            # machine-readable
  python dirty-file-owner-report.py --repo PATH       # a different checkout
  python dirty-file-owner-report.py --sessions-dir P --claims-dir P \\
      --ttl-minutes N                                 # test/fixture overrides

Exit 0: report produced (regardless of findings -- this is a report, not a
gate). Exit 2: could not run `git status` against --repo (bad path, not a
git checkout, git itself unavailable).

Stdlib only. ASCII-only. Windows (`python`).
"""
import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LIB_DIR = os.path.join(os.path.dirname(HERE), "hooks", "lib")
sys.path.insert(0, LIB_DIR)

# Guarded imports (same reliability posture as shared-checkout-guard.py /
# active-work-broadcast.py): a missing or broken hooks/lib module must
# degrade this report's ATTRIBUTION PRECISION, never crash the whole tool.
# Each availability flag below feeds straight into the report's own caveat
# lines, so a degraded source reads as "could not look" rather than a silent
# "0 sessions touched anything" -- see feedback_verified_null_vs_inferred_
# null.md ("a zero that could mean couldn't look is a FAILURE").
try:
    from commit_provenance import TOUCHED_BASENAME, read_touched  # noqa: E402
    PROVENANCE_LOADED = True
except Exception:
    PROVENANCE_LOADED = False
    TOUCHED_BASENAME = "touched-files.txt"

    def read_touched(_fh):
        return {}

try:
    from session_liveness import other_active_sessions  # noqa: E402
    LIVENESS_LOADED = True
except Exception:
    LIVENESS_LOADED = False

    def other_active_sessions(_own_sid, **_kwargs):
        return []

try:
    from claim_work import claims_touching  # noqa: E402
    CLAIMS_LOADED = True
except Exception:
    CLAIMS_LOADED = False

    def claims_touching(*_a, **_kw):
        return []

DEFAULT_REPO = "C:/Users/Owner/.claude"
DEFAULT_SESSIONS_DIR = "C:/Users/Owner/.claude/hooks/sessions"
# Report-scope claims window: deliberately NOT claim_work's own 120-minute
# live-collision TTL. That default exists to keep a PreToolUse hook's
# warning relevant to work happening RIGHT NOW; this report's whole purpose
# is historical breadth across a dirty set that can be days old, so a claim
# filed hours ago and since expired is still meaningful ownership context
# here. One year is "effectively unbounded" without disabling
# read_active_claims()'s existing malformed/future-timestamp rejection.
REPORT_CLAIMS_TTL_MINUTES = 525600.0

# Sentinel own-session-id for the liveness lookup below: this report has no
# "own session" to exclude from other_active_sessions() (unlike the hooks
# that module was written for), and a real session id could theoretically
# collide with it, so use a value the liveness store's format can never
# produce (a session-state filename stem is a UUID or "local_<uuid>").
_NOT_A_SESSION_ID = "__dirty-file-owner-report__"


def _norm(p):
    return os.path.normcase(os.path.abspath(p))


def git_status_porcelain(repo):
    """[(code, raw_abs_path), ...] for repo, sorted by path; or (None, err) on
    any git failure.

    `raw_abs_path` keeps its ORIGINAL case (abspath only, no normcase) -- it
    is what the report displays. Callers that need to match it against
    provenance/claim data (both keyed by commit_provenance.norm(), which
    DOES normcase) must call _norm() on it themselves at the lookup site;
    normcasing here would silently lowercase every displayed path on
    Windows (observed: a real 'RENAMED.md' rendered as 'renamed.md'),
    correct for matching but misleading for a human-facing report.

    Mirrors shared-checkout-guard.py's _status_paths() parsing (rename ->
    attribute the NEW path, core.quotePath unquoting) but keeps the 2-char
    status code that hook discards and this report displays. Deliberately
    duplicated rather than imported -- that hook's own module docstring
    already explains why: two independent fail-open tools should not couple
    over a few lines of porcelain parsing."""
    try:
        proc = subprocess.run(
            ["git", "-C", repo, "status", "--porcelain"],
            capture_output=True, text=True, timeout=15,
        )
    except Exception as exc:
        return None, str(exc)
    if proc.returncode != 0:
        return None, (proc.stderr or proc.stdout or "git status failed").strip()
    out = []
    for ln in proc.stdout.splitlines():
        if len(ln) < 4 or not ln.strip():
            continue
        code = ln[:2]
        rest = ln[3:].strip()
        if " -> " in rest:
            rest = rest.split(" -> ", 1)[1].strip()
        if len(rest) >= 2 and rest.startswith('"') and rest.endswith('"'):
            try:
                rest = json.loads(rest)
            except Exception:
                rest = rest[1:-1]
        if rest:
            out.append((code, os.path.abspath(os.path.join(repo, rest))))
    out.sort(key=lambda t: t[1])
    return out, None


def scan_provenance(sessions_dir):
    """({norm_path: [(sid, last_touch_ts_or_None), ...]}, ok) across EVERY
    session directory under sessions_dir that has a touched-files.txt --
    live or long-ended alike. Per-path hit list sorted most-recent-first
    (an unknown touch time sorts as "most recent", matching commit_
    provenance.read_touched()'s own documented "treat as just touched"
    contract).

    Deliberately NOT scoped to session_liveness's "currently live" set: the
    WIP this report exists to surface is exactly the kind that outlives its
    session (see module docstring). Fail-open per-session-dir: an
    unreadable individual touched-files.txt is skipped, not raised. `ok` is
    False only when the whole sessions_dir itself could not be listed (or
    the module never loaded) -- that is the "could not look" signal the
    report's caveat line needs; a skipped individual file is not."""
    index = {}
    if not PROVENANCE_LOADED:
        return index, False
    try:
        names = os.listdir(sessions_dir)
    except Exception:
        return index, False
    for sid in names:
        tf = os.path.join(sessions_dir, sid, TOUCHED_BASENAME)
        if not os.path.isfile(tf):
            continue
        try:
            with open(tf, encoding="utf-8") as fh:
                touched = read_touched(fh)
        except Exception:
            continue
        for path, ts in touched.items():
            index.setdefault(path, []).append((sid, ts))
    for hits in index.values():
        hits.sort(key=lambda h: (h[1] if h[1] is not None else float("inf")), reverse=True)
    return index, True


def live_session_ids():
    """({sid: status}, ok) for every session session_liveness.py currently
    reports live. Enrichment only -- marks an attributed session '(LIVE)' in
    the report -- never the attribution source itself. Resolution (sessions
    dir / legacy state file) is left entirely to session_liveness.py's own
    env-var-driven fallback, same as every other consumer of this module."""
    if not LIVENESS_LOADED:
        return {}, False
    try:
        entries = other_active_sessions(_NOT_A_SESSION_ID)
    except Exception:
        return {}, False
    return {e.get("sid"): e.get("status", "?") for e in entries if e.get("sid")}, True


def claims_for_paths(paths, claims_dir, ttl_minutes):
    """({norm_path: [claim_dict, ...]}, ok) for every claim within
    ttl_minutes whose declared --paths cover it. One claims_touching() call
    per path -- the claims directory is small in practice (a handful of
    live JSON files) and this is an occasional report, not a hot-path hook,
    so the O(files x claims) re-read cost is not worth optimizing away by
    reaching into claim_work's private path-matching helpers."""
    out = {}
    if not CLAIMS_LOADED:
        return out, False
    for p in paths:
        hits = claims_touching([p], base_dir=claims_dir, ttl_minutes=ttl_minutes)
        if hits:
            out[p] = hits
    return out, True


def build_report(repo, sessions_dir, claims_dir, ttl_minutes):
    status, err = git_status_porcelain(repo)
    if status is None:
        return None, err

    prov_index, prov_ok = scan_provenance(sessions_dir)
    live, live_ok = live_session_ids()
    claim_index, claims_ok = claims_for_paths(
        [p for _, p in status], claims_dir, ttl_minutes)

    repo_abs = _norm(repo)
    files = []
    for code, path in status:
        # prov_index is keyed by commit_provenance.norm() (normcase'd) --
        # `path` here is the RAW-case display path (see git_status_
        # porcelain's docstring), so the lookup key must be normcased too or
        # every match silently misses on a case-insensitive filesystem.
        # claim_index is keyed by this same raw `path` (see
        # claims_for_paths), so no normcasing is needed for that lookup.
        prov_hits = prov_index.get(_norm(path), [])
        claim_hits = claim_index.get(path, [])
        if prov_hits:
            owner = prov_hits[0][0]
        elif claim_hits:
            owner = claim_hits[0].get("session_id")
        else:
            owner = None
        try:
            rel = os.path.relpath(path, repo_abs)
        except Exception:
            rel = path
        files.append({
            "path": rel,
            "status": code,
            "owner": owner,
            "owner_live": bool(owner and owner in live),
            "provenance": [{"session_id": sid, "touched_at": ts} for sid, ts in prov_hits],
            "claims": [{"slug": c.get("slug"), "session_id": c.get("session_id"),
                        "host_session_id": c.get("host_session_id") or ""}
                       for c in claim_hits],
        })

    return {
        "repo": repo,
        "total_dirty": len(files),
        "sources": {
            "provenance_available": prov_ok,
            "liveness_available": live_ok,
            "claims_available": claims_ok,
        },
        "files": files,
    }, None


def group_owners(files):
    """(groups, unattributed): groups is {session_id: [file, ...]}, ordered
    by insertion but callers should sort for display; unattributed is the
    list of files with no provenance hit and no covering claim."""
    groups = {}
    unattributed = []
    for f in files:
        if f["owner"]:
            groups.setdefault(f["owner"], []).append(f)
        else:
            unattributed.append(f)
    return groups, unattributed


_MAX_FILES_SHOWN_PER_SESSION = 10


def render_text(report):
    lines = []
    lines.append("DIRTY FILE OWNERSHIP REPORT -- %s" % report["repo"])
    lines.append("=" * 78)

    src = report["sources"]
    caveats = []
    if not src["provenance_available"]:
        caveats.append("provenance UNAVAILABLE (commit_provenance.py missing, or the "
                        "sessions directory could not be listed) -- attribution below "
                        "is INCOMPLETE, not exhaustive.")
    if not src["claims_available"]:
        caveats.append("claim data UNAVAILABLE (claim_work.py missing) -- the "
                        "pre-first-edit claim signal is not included below.")
    if not src["liveness_available"]:
        caveats.append("liveness UNAVAILABLE (session_liveness.py missing) -- cannot "
                        "mark an attributed session as still open.")
    for c in caveats:
        lines.append("CAVEAT: " + c)
    if caveats:
        lines.append("-" * 78)

    files = report["files"]
    groups, unattributed = group_owners(files)
    lines.append("total dirty files: %d" % report["total_dirty"])
    lines.append("attributed to %d session(s); %d file(s) unattributed"
                  % (len(groups), len(unattributed)))
    lines.append("")

    if groups:
        lines.append("BY SESSION (most files first):")
        for sid, fl in sorted(groups.items(), key=lambda kv: (-len(kv[1]), kv[0])):
            live_tag = " (LIVE)" if fl[0]["owner_live"] else ""
            lines.append("  %s%s  %d file(s)" % (sid[:12], live_tag, len(fl)))
            for f in fl[:_MAX_FILES_SHOWN_PER_SESSION]:
                lines.append("      %s  [%s]" % (f["path"], f["status"]))
            if len(fl) > _MAX_FILES_SHOWN_PER_SESSION:
                lines.append("      ... and %d more"
                              % (len(fl) - _MAX_FILES_SHOWN_PER_SESSION))
        lines.append("")

    if unattributed:
        lines.append("UNATTRIBUTED (%d file(s)) -- no provenance record, no "
                      "covering claim; check `git log -1`/`git blame` yourself "
                      "before assuming these are safe to touch:" % len(unattributed))
        for f in unattributed:
            lines.append("  %s  [%s]" % (f["path"], f["status"]))

    if not files:
        lines.append("(clean checkout -- nothing to report)")

    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(
        description="Read-only 'who owns each dirty file' reporter for a "
                     "shared ~/.claude-style checkout. Never writes, never blocks.")
    ap.add_argument("--repo", default=os.environ.get("DIRTY_OWNER_REPORT_REPO")
                     or DEFAULT_REPO)
    ap.add_argument("--sessions-dir",
                     default=os.environ.get("SHARED_CHECKOUT_SESSIONS_DIR")
                     or DEFAULT_SESSIONS_DIR)
    ap.add_argument("--claims-dir", default=None,
                     help="Defaults to claim_work.py's own CLAIMS_DIR / "
                          "ORA_ACTIVE_WORK_DIR resolution.")
    ap.add_argument("--ttl-minutes", type=float, default=REPORT_CLAIMS_TTL_MINUTES)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    report, err = build_report(args.repo, args.sessions_dir, args.claims_dir,
                                args.ttl_minutes)
    if report is None:
        sys.stderr.write("[ACTION] dirty-file-owner-report: `git status` failed "
                          "for %s: %s\n" % (args.repo, err))
        sys.exit(2)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(render_text(report))
    sys.exit(0)


if __name__ == "__main__":
    main()
