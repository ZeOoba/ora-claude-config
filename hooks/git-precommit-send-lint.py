#!/usr/bin/env python3
"""Pre-commit: run the send-contract spec lint on the STAGED scheduled-task specs.

WHY (2026-11-14): maintenance/_tests/test_send_contract_spec_lint.py enforces rules.md
section 2 (a send is retried only on exit 2 or 4; after any other exit the send state is
unknown and a retry can double-send). It ran only in CI and the pre-push gate, so specs
written straight onto the live branch -- which reaches main weeks later, if at all --
carried "retry once on a non-zero exit" for weeks: ora-closed-deal-variance-check,
ora-passed-deal-tracker-spec-sync-1113 and ora-portfolio-desk-refresh were found only
while landing the live branch. Running the lint at commit time catches it when written.

WHAT IT CHECKS: the index, not the working tree. Every scheduled-tasks/*/SKILL.md and the
lint itself are copied out of the index into a temporary root (the lint locates specs
relative to its own path), so a half-edited working copy can neither pass nor fail a
commit that does not contain it.

WHEN IT BLOCKS: only on a lint failure naming a spec STAGED in this commit (or on any
failure when the lint script itself is staged). A failure in some other, unstaged spec is
printed as a warning and does not block: that spec is not this commit's to fix. Commits
that stage no scheduled-task spec return at once (the event_log auto-commit and the
memory sweep take this path), so the hook costs nothing for them.

FAIL-OPEN on tooling problems (no git, no python, lint missing in the index, timeout):
prints a warning and exits 0. The pre-push gate and CI still run the lint.

OVERRIDE: `git commit --no-verify` (standard git; skips every pre-commit hook).

INSTALL (the shim is not version-controlled; .git/hooks is dropped on every clone):
  .git/hooks/pre-commit:
    #!/bin/sh
    ROOT="$(git rev-parse --show-toplevel)"
    [ -f "$ROOT/hooks/git-precommit-send-lint.py" ] || exit 0
    exec python "$ROOT/hooks/git-precommit-send-lint.py"
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

LINT = "maintenance/_tests/test_send_contract_spec_lint.py"
SPEC_RE = re.compile(r"^scheduled-tasks/([^/]+)/SKILL\.md$")
FAIL_RE = re.compile(r"^\s*FAIL\s+(.*)$")
TIMEOUT_S = 120

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def git(*args, check=True):
    r = subprocess.run(["git", *args], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if check and r.returncode != 0:
        raise RuntimeError(f"git {args[0]}: {r.stderr.strip()[:200]}")
    return r.stdout


def staged_paths():
    out = git("diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z")
    return [p for p in out.split("\0") if p]


def staged_tasks(paths):
    return {m.group(1) for p in paths for m in [SPEC_RE.match(p)] if m}


def blocking_failures(lint_output, tasks, lint_staged):
    """FAIL lines that block this commit: any FAIL when the lint itself is staged;
    otherwise only FAIL lines naming a staged task (whole-word match)."""
    fails = [m.group(1).strip() for line in lint_output.splitlines()
             for m in [FAIL_RE.match(line)] if m]
    if lint_staged:
        return fails, []
    block, other = [], []
    for f in fails:
        named = any(re.search(rf"(?<![\w-]){re.escape(t)}(?![\w-])", f) for t in tasks)
        (block if named else other).append(f)
    return block, other


def main():
    try:
        paths = staged_paths()
    except Exception as e:
        print(f"send-lint pre-commit: skipped ({e})", file=sys.stderr)
        return 0
    tasks = staged_tasks(paths)
    lint_staged = LINT in paths
    if not tasks and not lint_staged:
        return 0
    tmp = tempfile.mkdtemp(prefix="ora-send-lint-")
    try:
        try:
            files = [p for p in git("ls-files", "-z", "--", "scheduled-tasks").split("\0")
                     if p and SPEC_RE.match(p)]
            git("checkout-index", f"--prefix={tmp}/", "--", LINT, *files)
        except Exception as e:
            print(f"send-lint pre-commit: skipped, could not stage a lint root ({e})", file=sys.stderr)
            return 0
        try:
            r = subprocess.run([sys.executable, os.path.join(tmp, *LINT.split("/"))],
                               capture_output=True, text=True, encoding="utf-8",
                               errors="replace", timeout=TIMEOUT_S)
        except Exception as e:
            print(f"send-lint pre-commit: skipped, lint did not run ({e})", file=sys.stderr)
            return 0
        block, other = blocking_failures(r.stdout + r.stderr, tasks, lint_staged)
        for f in other:
            print(f"send-lint pre-commit: WARN (not in this commit): {f}", file=sys.stderr)
        if block:
            print("send-lint pre-commit: BLOCKED -- the send-contract lint fails on what this "
                  "commit stages (rules.md section 2: retry a send only on exit 2 or 4):",
                  file=sys.stderr)
            for f in block:
                print(f"  FAIL {f}", file=sys.stderr)
            print("Fix the wording (e.g. 'Retry only on exit 2 or 4, once; never resend after "
                  "any other exit') or bypass deliberately with `git commit --no-verify`.",
                  file=sys.stderr)
            return 1
        if r.returncode != 0 and not other:
            print("send-lint pre-commit: lint exited non-zero without a FAIL line; not blocking "
                  "(pre-push and CI still run it).", file=sys.stderr)
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
