"""Shared git-subprocess plumbing for the "is this checkout in sync with a
base ref" family: maintenance/check-branch-point.py, hooks/repo-freshness.py,
maintenance/fleet-spec-git-drift-probe.py.

WHY (2026-09-07, PR #174 review finding): all three independently reimplemented
a "run git via subprocess, return (rc, stdout[, stderr]), never raise" wrapper,
and check-branch-point.py + fleet-spec-git-drift-probe.py additionally
duplicated an identical `git rev-parse --verify --quiet <base>^{commit}`
resolvability check with near-identical error text. Extracted so a future fix
to either (e.g. a timeout/encoding edge case) lands once, not N times at N
different maturity levels — see hooks/lib/git_commit_parse.py's own docstring
for the same lesson learned the hard way on a different shared contract.

hooks/repo-freshness.py's own git() closure was NOT byte-for-byte identical to
the other two (no `repo`/`strip` params, raises instead of trapping errors,
call sites wrap it in their own try/except) and, critically, that file never
had a base-resolvability check at all — it hardcodes "origin/main", takes no
--base flag, and is a SessionStart hook designed to no-op silently on ANY
failure rather than assert a base resolves. Only the genuinely shared piece
(the never-raise subprocess wrapper) moved for that file; the base_resolves()
check below is used by the two scripts that already had it, unchanged.

Stdlib only. ASCII-only. Windows (`python`).
"""
import subprocess


def git(repo, args, timeout=20, strip=True):
    """(rc, stdout, stderr) -- never raises.

    repo=None means "run in the current process's own working directory"
    (check-branch-point.py's default, cwd-relative usage) -- omits `-C`
    entirely rather than passing it a None/empty value, which would make git
    treat the literal string as a path and fail every call. Callers that
    always have a concrete repo path (fleet-spec-git-drift-probe.py,
    hooks/repo-freshness.py) are unaffected -- they never pass None.

    strip=False when comparing FILE CONTENT (e.g. `git show <ref>:<path>`):
    stripping would silently eat a trailing newline from the file's own
    content and make it compare unequal to an on-disk read that kept it
    (fleet-spec-git-drift-probe.py's own test suite caught this)."""
    cmd = ["git"] + (["-C", repo] if repo else []) + args
    try:
        p = subprocess.run(cmd, capture_output=True,
                           text=True, encoding="utf-8", errors="replace",
                           timeout=timeout)
    except Exception as e:
        return 127, "", str(e)
    out, errout = (p.stdout or ""), (p.stderr or "")
    if strip:
        out, errout = out.strip(), errout.strip()
    return p.returncode, out, errout


def base_resolves(repo, base, timeout=20):
    """(ok, stderr) -- ok is True iff `base` resolves to a commit via
    `git rev-parse --verify --quiet <base>^{commit}`. stderr is almost always
    '' (--quiet suppresses rev-parse's own message on a bad ref); present so
    a caller that wants to append whatever detail git did produce still can.
    Callers own their own final error-message wording -- this only shares the
    git invocation, not the text (check-branch-point.py and
    fleet-spec-git-drift-probe.py word theirs slightly differently, on
    purpose, predating this extraction)."""
    rc, _, err = git(repo, ["rev-parse", "--verify", "--quiet", base + "^{commit}"],
                     timeout=timeout)
    return rc == 0, err
