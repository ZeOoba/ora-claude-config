"""Shared git-subprocess plumbing for the "is this checkout in sync with a
base ref" family: maintenance/check-branch-point.py, hooks/repo-freshness.py,
maintenance/fleet-spec-git-drift-probe.py.

WHY (2026-09-07, PR #174 review finding): all three independently reimplemented
a "run git via subprocess, return (rc, stdout[, stderr]), never raise" wrapper,
and check-branch-point.py + fleet-spec-git-drift-probe.py additionally
duplicated an identical `git rev-parse --verify --quiet <base>^{commit}`
resolvability check with near-identical error text. Extracted so a future fix
to either (e.g. a timeout/encoding edge case) lands once, not N times at N
different maturity levels -- see hooks/lib/git_commit_parse.py's own docstring
for the same lesson learned the hard way on a different shared contract.

hooks/repo-freshness.py's own git() closure was NOT byte-for-byte identical to
the other two (no `repo`/`strip` params, raises instead of trapping errors,
call sites wrap it in their own try/except) and, critically, that file never
had a base-resolvability check at all -- it hardcodes "origin/main", takes no
--base flag, and is a SessionStart hook designed to no-op silently on ANY
failure rather than assert a base resolves. Adding one there would be
redundant, not merely out of scope: with no `origin` remote configured,
`git rev-list --left-right --count HEAD...origin/main` itself exits non-zero
with empty stdout, which already lands on that file's own
`if not counts: return` -- the exact silent no-op a resolvability check would
also produce. Only the genuinely shared piece (the never-raise subprocess
wrapper) moved for that file.

verify_ref_args() below is deliberately NOT a function that calls git: an
earlier draft had a base_resolves() that did, and independent review (two
angles, same finding) caught that it broke check-branch-point.py's and
fleet-spec-git-drift-probe.py's own test suites' house convention of
monkeypatching `mod.git` to force a git call to fail -- a base_resolves()
living here would call THIS module's git, invisibly to that monkeypatch,
so a future "make every git call fail" test would silently let the base
check through against the real repo. Keeping the resolvability check
itself inline at each call site (through each module's own patchable `git`
name) and sharing only the exact, easy-to-typo args list closes that gap.

Stdlib only. ASCII-only. Windows (`python`).
"""
import subprocess


def git(repo, args, timeout=20, strip=True):
    """(rc, stdout, stderr) -- never raises.

    repo=None means "run in the current process's own working directory"
    (check-branch-point.py's default, cwd-relative usage) -- omits `-C`
    entirely. repo="" (an explicit-but-empty value, distinct from None -- as
    argparse yields for `--repo ""`) is rejected outright rather than passed
    to `-C`: `git -C ""` is a documented no-op that resolves against the
    CURRENT directory, which would silently retarget a check at the wrong
    repo instead of failing -- caught before this shipped by testing
    check-branch-point.py's original `cwd=""` behavior (raises OSError,
    UNDETERMINED) against the naive `-C` translation (silently certifies
    whatever repo the process happens to be sitting in, exit 0).

    strip=False when comparing FILE CONTENT (e.g. `git show <ref>:<path>`):
    stripping would silently eat a trailing newline from the file's own
    content and make it compare unequal to an on-disk read that kept it
    (fleet-spec-git-drift-probe.py's own test suite caught this)."""
    if repo == "":
        return 127, "", "empty repo path"
    cmd = ["git"] + (["-C", repo] if repo is not None else []) + args
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


def verify_ref_args(ref):
    """Args for `git rev-parse --verify --quiet <ref>^{commit}` -- the
    resolvability check duplicated word-for-word across
    check-branch-point.py and fleet-spec-git-drift-probe.py. See the module
    docstring for why this stays a pure arg-builder rather than a function
    that calls git itself."""
    return ["rev-parse", "--verify", "--quiet", ref + "^{commit}"]
