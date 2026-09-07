#!/usr/bin/env python3
"""fleet-spec-git-drift-probe.py -- detects a scheduled-task fleet spec
(scheduled-tasks/*/SKILL.md) that origin/main carries newer commits for than
the live checkout reflects: a fix MERGED upstream but not SERVED here.

WHY (2026-09-07, Gabriel "fix this" on a same-day workflow-optimization
bullet: "the guard spec is merged-but-not-served; nothing detects that
class of gap"). The 2026-08-23 event_log entry for the
feat/model-canary-probe-step25 -> main merge names the exact shape: done in
an isolated worktree, and explicitly "this merge doesn't retroactively
update the shared ~/.claude checkout's branch ... untouched by design."
That is fine when it is a deliberate, known state -- but nothing WALKS
scheduled-tasks/*/SKILL.md and asks "does origin/main have a commit for
this file that HEAD lacks?", so an accidental case (a session forgets to
pull, or a fix genuinely never reaches the primary checkout) looks
identical to the deliberate one from the outside: the file sits there,
looking normal, quietly stale.

NOT A DUPLICATE OF EXISTING GUARDS (verified before writing this one):
  * check-branch-point.py checks the OPPOSITE direction -- would MY branch
    ship extra commits if merged -- and is repo-wide, not per served file.
  * hooks/repo-freshness.py checks HEAD-vs-origin/main staleness, but only
    for oxford-command-center, as a whole-repo SessionStart summary, never
    per file.
  * maintenance/spec-liveness-probe.py compares spec CLAIMS (severity
    assertions) against a live runtime snapshot -- a completely different
    axis (spec-vs-data, not checkout-vs-origin).
None of the three reaches "is this exact served file behind origin/main."
This probe is that missing edge, and only that edge.

SCOPE: CC/MCP fleet only (scheduled-tasks/ under THIS ~/.claude checkout,
which is the git working tree actually served). LAMS/Cowork specs live on
OneDrive with no origin/main equivalent to drift against -- out of scope,
not a false negative.

READ-ONLY git: rev-parse, fetch (remote-tracking refs only), log, show,
ls-tree. Never touches the working tree, branches, index, or HEAD.

FAIL-OPEN on anything it cannot determine (unresolvable base, not a git
repo, OR a single git call failing mid-run -- see base_task_specs()/
commits_ahead()) -- reports [UNDETERMINED] / exit 2, never invents a clean
verdict. A fetch failure alone does NOT abort the run -- it falls back to
the last-known ref and says so, matching hooks/repo-freshness.py's own
posture (fetch failing is routine/offline; a plumbing read failing mid-walk
is not, and must not be swallowed the same way).

Exit 0 = clean. Exit 1 = at least one fleet spec is merged-but-not-served.
Exit 2 = could not determine (never a silent pass).

Usage:
  python fleet-spec-git-drift-probe.py
  python fleet-spec-git-drift-probe.py --repo <path> --base origin/main
  python fleet-spec-git-drift-probe.py --no-fetch     # skip the network refresh (tests, offline)
  python fleet-spec-git-drift-probe.py --json
"""
import argparse
import json
import os
import subprocess
import sys

CLAUDE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TASKS_SUBDIR = "scheduled-tasks"
SPEC_BASENAME = "SKILL.md"


def git(repo, args, timeout=20, strip=True):
    """(rc, stdout, stderr) -- never raises. Every call site here is a read
    (rev-parse/fetch/log/show/ls-tree); this helper does not enforce that,
    but nothing in this module calls it with a mutating verb.

    strip=False for `show` (file content): stripping would silently eat a
    trailing newline from the FILE'S OWN CONTENT and make it compare unequal
    to an on-disk read that kept it -- found by this module's own test suite
    (test_identical_content_despite_extra_commits_is_clean failed on exactly
    this before strip=False was added here)."""
    try:
        p = subprocess.run(["git", "-C", repo] + args, capture_output=True,
                           text=True, encoding="utf-8", errors="replace",
                           timeout=timeout)
    except Exception as e:
        return 127, "", str(e)
    out, errout = (p.stdout or ""), (p.stderr or "")
    if strip:
        out, errout = out.strip(), errout.strip()
    return p.returncode, out, errout


def _is_archived(entry):
    # Matches spec-liveness-probe.py's collect_spec_sources() convention: a
    # retired/staging task folder's drift is history, not a live gap.
    return entry.startswith("_")


def live_task_specs(repo):
    """{relpath} for every non-archived scheduled-tasks/<id>/SKILL.md present
    on disk right now. relpath uses forward slashes (git's own convention)
    so it compares directly against git ls-tree/show output."""
    out = set()
    root = os.path.join(repo, TASKS_SUBDIR)
    if not os.path.isdir(root):
        return out
    try:
        entries = sorted(os.listdir(root))
    except Exception:
        return out
    for entry in entries:
        if _is_archived(entry):
            continue
        p = os.path.join(root, entry, SPEC_BASENAME)
        if os.path.isfile(p):
            out.add("%s/%s/%s" % (TASKS_SUBDIR, entry, SPEC_BASENAME))
    return out


def base_task_specs(repo, base):
    """{relpath} for every non-archived scheduled-tasks/<id>/SKILL.md that
    `base` (e.g. origin/main) carries, via git ls-tree -- no checkout, no
    working-tree touch. Returns None (never an empty set) if the ls-tree
    call itself fails: this is ONE call covering the entire tree, so a
    failure here silently drops every upstream spec from the comparison
    rather than just one -- caught by review, since returning {} on failure
    looks identical to 'origin/main genuinely has no fleet specs' and
    reports a false [OK] instead of the documented [UNDETERMINED]."""
    out = set()
    rc, listing, _ = git(repo, ["ls-tree", "-r", "--name-only", base, "--",
                                TASKS_SUBDIR])
    if rc != 0:
        return None
    for line in listing.splitlines():
        line = line.strip()
        if not line.endswith("/" + SPEC_BASENAME):
            continue
        parts = line.split("/")
        if len(parts) != 3:  # scheduled-tasks/<id>/SKILL.md, exactly
            continue
        if _is_archived(parts[1]):
            continue
        out.add(line)
    return out


def read_live(repo, relpath):
    """On-disk content at relpath, or None if absent/unreadable."""
    p = os.path.join(repo, *relpath.split("/"))
    try:
        with open(p, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except Exception:
        return None


def read_at_ref(repo, ref, relpath):
    """Content at ref:relpath, or None if it does not exist there -- 'the
    file was added/removed at this ref' is a legitimate silent None, not an
    error."""
    rc, out, _ = git(repo, ["show", "%s:%s" % (ref, relpath)], strip=False)
    if rc != 0:
        return None
    return out


def commits_ahead(repo, head, base, relpath):
    """[(sha, subject), ...] on base but not on head, touching relpath.
    Empty list means base carries nothing for this path that head lacks.
    None (distinct from []) means the git call itself failed -- a caller
    must not treat that as 'not ahead', which would silently skip checking
    a path and still report [OK] for it (caught by review).

    `:(literal)` prefixes relpath so a task-folder name containing pathspec
    magic (`*`, `?`, `[...]`, a leading `:`) is matched as a literal string,
    not interpreted as a glob -- without it, a folder named e.g.
    `[deprecated]-old-task` either matches an unintended set of paths or
    makes git exit non-zero (which, pre-fix, silently read as 'clean')."""
    rc, out, _ = git(repo, ["log", "--format=%H\t%s",
                            "%s..%s" % (head, base), "--",
                            ":(literal)" + relpath])
    if rc != 0:
        return None
    commits = []
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split("\t", 1)
        commits.append((parts[0], parts[1] if len(parts) > 1 else ""))
    return commits


def analyze(repo, base="origin/main", do_fetch=True):
    """Findings dict. Pure-ish: all git access goes through git()."""
    out = {"repo": repo, "base": base, "head": None, "error": None,
          "fetch_error": None, "findings": [], "specs_checked": 0,
          "undetermined_paths": []}

    rc, head, err = git(repo, ["rev-parse", "HEAD"])
    if rc != 0:
        out["error"] = "cannot resolve HEAD (not a git repo?): %s" % (err or head)
        return out
    out["head"] = head

    if do_fetch:
        rc, _, err = git(repo, ["fetch", "--quiet", "origin"], timeout=60)
        if rc != 0:
            # Fail-open: proceed against the last-known ref rather than
            # refusing to check anything -- matches repo-freshness.py.
            out["fetch_error"] = err or "fetch failed"

    rc, _, err = git(repo, ["rev-parse", "--verify", "--quiet",
                            base + "^{commit}"])
    if rc != 0:
        out["error"] = "base %r does not resolve -- fetch it first: %s" % (
            base, err)
        return out

    base_specs = base_task_specs(repo, base)
    if base_specs is None:
        # ONE call covers the whole tree; its failure means "could not
        # enumerate", never "origin/main has no fleet specs" -- reporting
        # [OK] here would be the exact false-clean verdict this probe's
        # fail-open contract forbids.
        out["error"] = ("cannot list %s's %s tree (git ls-tree failed) -- "
                        "cannot certify any spec against it" % (base, TASKS_SUBDIR))
        return out

    paths = live_task_specs(repo) | base_specs
    out["specs_checked"] = len(paths)
    for relpath in sorted(paths):
        ahead = commits_ahead(repo, head, base, relpath)
        if ahead is None:
            # This one path's git log call failed -- record it as
            # unverifiable rather than silently treating it as "not ahead"
            # (which would report [OK] for a path that was never actually
            # checked).
            out["undetermined_paths"].append(relpath)
            continue
        if not ahead:
            continue
        live = read_live(repo, relpath)
        upstream = read_at_ref(repo, base, relpath)
        if live == upstream:
            # Byte-identical despite differing lineage (e.g. a later commit
            # reverted to the same content another way) -- nothing is
            # actually stranded. A probe that cries wolf on a fixed state is
            # worse than no probe (see spec-liveness-probe.py's own rule).
            continue
        out["findings"].append({
            "path": relpath,
            "commits_ahead": len(ahead),
            "sample_commit": ahead[0][0][:12] + " " + ahead[0][1][:96],
            "live_missing": live is None,
            "upstream_missing": upstream is None,
        })
    return out


def format_report(r):
    if r["error"]:
        return ("[UNDETERMINED] fleet-spec-git-drift-probe could not run: %s\n"
                "  Treat this as unverified, NOT as clean." % r["error"])
    lines = []
    if r["fetch_error"]:
        lines.append("[NOTE] could not refresh %s from origin (%s) -- checking "
                     "against the last-known ref." % (r["base"], r["fetch_error"]))
    if r["undetermined_paths"]:
        lines.append("[UNDETERMINED] %d path(s) could not be checked (git log "
                     "failed) -- NOT certified clean, not a finding either: %s"
                     % (len(r["undetermined_paths"]),
                        ", ".join(r["undetermined_paths"])))
    if not r["findings"]:
        if r["undetermined_paths"]:
            return "\n".join(lines)
        lines.append("[OK] %d fleet spec(s) checked against %s -- none stranded."
                     % (r["specs_checked"], r["base"]))
        return "\n".join(lines)
    lines.append("[ACTION] %d fleet spec(s) are MERGED but NOT SERVED -- %s "
                 "carries commit(s) this checkout's live copy does not reflect:"
                 % (len(r["findings"]), r["base"]))
    for f in r["findings"]:
        detail = "%d commit(s) ahead, e.g. %s" % (f["commits_ahead"], f["sample_commit"])
        if f["live_missing"]:
            detail += " -- MISSING from the live checkout entirely"
        elif f["upstream_missing"]:
            detail += " -- removed at %s but still live here" % r["base"]
        lines.append("  - %s (%s)" % (f["path"], detail))
    lines.append("\nFix: pull/merge %s into this checkout (or onto whatever "
                 "branch it is actually on) before trusting this spec as the "
                 "one the fleet runs -- a merged PR is not a served file. See "
                 "the 2026-08-23 model-canary-probe-step25 event_log entry "
                 "for the incident shape this catches." % r["base"])
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Flags a scheduled-tasks/*/SKILL.md fleet spec that "
                    "origin/main has newer commits for than this checkout's "
                    "live copy reflects (merged upstream, not served here).")
    ap.add_argument("--repo", default=CLAUDE)
    ap.add_argument("--base", default="origin/main")
    ap.add_argument("--no-fetch", action="store_true",
                    help="Skip refreshing remote-tracking refs first (tests, offline runs)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    r = analyze(args.repo, base=args.base, do_fetch=not args.no_fetch)
    if args.json:
        print(json.dumps(r, indent=2))
    else:
        print(format_report(r))
    if r["error"]:
        return 2
    if r["findings"]:
        return 1
    # Undetermined paths with zero findings still cannot be called clean --
    # some path was never actually checked, and reporting 0 here would be
    # the exact false-[OK] verdict the fail-open fix above exists to avoid.
    return 2 if r["undetermined_paths"] else 0


if __name__ == "__main__":
    sys.exit(main())
