"""Repo-hygiene invariant: an override token must NEVER be reachable via git.

Run: python test-override-token-hygiene.py
Stdlib only. ASCII-only. Self-contained.

WHY (2026-07-16): every override sentinel in this repo (ora-autonomy-gate.py's
allow-external-send / allow-website-change, git-prepush-doctrine-gate.py's
allow-doctrine-drift) is validated by mtime age alone. git sets a checked-out
file's mtime to CHECKOUT time, so any tracked token is materialized by a clone /
checkout / pull with age ~0 -- self-granting a live 60-minute override with no
human in the loop. That is not theoretical: `hooks/overrides/allow-website-change`
was swept into the repo by 668f9d4 (a broad "land the backlog" add), and a fresh
clone of ~/.claude was empirically shown to make ora-autonomy-gate.py return
exit 0 for `netlify deploy --build --prod` -- a live invariant-2 bypass on the
MIGRATION_RUNBOOK restore path -- where an empty-dir control returned exit 2.

The root cause is REACHABILITY, not gate logic: `hooks/overrides/` had no
.gitignore rule, so one `git add -A` was enough. `hooks/sessions/` (the
eos-plan-gate token home) was already ignored and never had this problem.

These tests are the durable regression: they fail if a token is ever tracked
again, or if the ignore rule is dropped. They assert the invariant for ANY
overrides directory, so relocating tokens to a new home does not silently lose
the coverage.
"""

import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def git(*args):
    proc = subprocess.run(
        ["git"] + list(args), cwd=REPO, capture_output=True, text=True
    )
    return proc.returncode, proc.stdout.strip()


def test_no_override_token_is_tracked():
    """No file under any overrides/ directory may be tracked by git. A tracked
    token is a clone-mintable override -- the exact 2026-07-16 finding."""
    rc, out = git("ls-files")
    assert rc == 0, "git ls-files failed"
    tracked = [
        line
        for line in out.splitlines()
        if "/overrides/" in line.replace("\\", "/")
        or line.replace("\\", "/").startswith("overrides/")
    ]
    assert not tracked, (
        "override token(s) tracked by git -- a clone/checkout mints these with a\n"
        "fresh mtime and self-grants a live override. Untrack with\n"
        "  git rm --cached <path>\n"
        "Tracked: %s" % tracked
    )
    print("PASS test_no_override_token_is_tracked")


def test_overrides_dir_is_gitignored():
    """The flat legacy token home must be ignored so a future `git add -A`
    cannot re-track a token (that is exactly how 668f9d4 happened)."""
    rc, out = git("check-ignore", "-v", "hooks/overrides/allow-doctrine-drift")
    assert rc == 0, (
        "hooks/overrides/ is NOT gitignored -- a `git add -A` can re-track a live\n"
        "override token. Add an ignore rule for it."
    )
    print("PASS test_overrides_dir_is_gitignored (rule: %s)" % out.split("\t")[0])


def test_session_override_home_is_gitignored():
    """The session-scoped token home must be ignored too -- this is the property
    that makes session-scoping clone-immune rather than merely tidier."""
    rc, out = git(
        "check-ignore", "-v", "hooks/sessions/some-session-id/overrides/allow-doctrine-drift"
    )
    assert rc == 0, (
        "hooks/sessions/ is NOT gitignored -- session-scoped override tokens would\n"
        "be clone-mintable, defeating the point of relocating them."
    )
    print("PASS test_session_override_home_is_gitignored (rule: %s)" % out.split("\t")[0])


if __name__ == "__main__":
    test_no_override_token_is_tracked()
    test_overrides_dir_is_gitignored()
    test_session_override_home_is_gitignored()
    print("ALL OVERRIDE-TOKEN-HYGIENE TESTS PASS")
