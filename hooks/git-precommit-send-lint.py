#!/usr/bin/env python3
"""Pre-commit: run the send-contract spec lint on the STAGED scheduled-task specs.

WHY (2026-11-14): maintenance/_tests/test_send_contract_spec_lint.py enforces rules.md
section 2 (a send is retried only on exit 2 or 4; after any other exit the send state is
unknown and a retry can double-send). It ran only in CI and the pre-push gate, so specs
written straight onto the live branch -- which reaches main weeks later, if at all --
carried "retry once on a non-zero exit" for weeks: ora-closed-deal-variance-check,
ora-passed-deal-tracker-spec-sync-1113 and ora-portfolio-desk-refresh were found only
while landing the live branch. Running the lint at commit time catches it when written.

WHAT IT CHECKS: the index git is committing (git sets GIT_INDEX_FILE for -a, -i, --only
and pathspec commits; diff --cached, ls-files and checkout-index all honor it). Every
scheduled-tasks/*/SKILL.md and the lint itself are copied out of that index into a temp
root (the lint locates specs relative to its own path), so the working tree never decides.

WHEN IT BLOCKS (exit BLOCK = 10, the only blocking code. Python itself exits 1 on an
uncaught exception and 2 on a usage error, so neither can be mistaken for a block;
the shim turns every other code into 0):
  - a lint FAIL line naming a spec this commit adds, modifies, deletes or renames (both
    names of a rename), whole-word;
  - any FAIL, or a lint crash/timeout, when the lint script itself is staged.
A failure naming some other spec only warns: that spec is not this commit's to fix.
Commits staging no spec return at once (the event_log auto-commit and memory sweep).

FAIL-OPEN on every tooling problem (no git, broken TEMP, lint missing, crash, timeout):
warns and exits 0. The pre-push gate and CI still run the lint.

LOCK TIME: commits made with -a / -i / --only / pathspecs hold .git/index.lock while
pre-commit runs, so the lint is kept short: LAMS (OneDrive) specs are skipped here by
pointing HOME/USERPROFILE at the temp root, and TIMEOUT_S is 20. A concurrent event_log
auto-commit or memory sweep that meets the lock does not lose anything: both already
leave the change for their next run (append-event-log.py autocommit_log, sweep exit 1).

OVERRIDE: `git commit --no-verify`.

INSTALL: copy hooks/precommit-shim.sh to .git/hooks/pre-commit (not version-controlled;
.git/hooks is dropped on every clone). The shim is fail-open by construction.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

LINT = "maintenance/_tests/test_send_contract_spec_lint.py"
SPEC_RE = re.compile(r"^scheduled-tasks/([^/]+)/skill\.md$", re.I)
FAIL_RE = re.compile(r"^\s*FAIL\s+(.*)$")
TIMEOUT_S = 20
BLOCK = 10   # the only exit code the shim treats as a block

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def warn(msg):
    try:
        print(f"send-lint pre-commit: {msg}", file=sys.stderr)
    except Exception:
        pass


def git(*args, stdin=None):
    r = subprocess.run(["git", *args], input=stdin, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise RuntimeError(f"git {args[0]}: {r.stderr.strip()[:200]}")
    return r.stdout


def staged_changes():
    """[(status, path, ...)] for the index being committed; renames carry both paths."""
    out = git("diff", "--cached", "--name-status", "-M", "-z")
    parts = [p for p in out.split("\0") if p != ""]
    rows, i = [], 0
    while i < len(parts):
        st = parts[i]
        n = 2 if st[:1] in ("R", "C") else 1
        rows.append((st[:1], *parts[i + 1:i + 1 + n]))
        i += 1 + n
    return rows


def staged_tasks(rows):
    tasks = set()
    for _st, *paths in rows:
        for p in paths:
            m = SPEC_RE.match(p)
            if m:
                tasks.add(m.group(1))
    return tasks


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


def run():
    try:
        rows = staged_changes()
    except Exception as e:
        warn(f"skipped ({e})")
        return 0
    tasks = staged_tasks(rows)
    lint_staged = any(LINT in paths for _st, *paths in rows)
    if not tasks and not lint_staged:
        return 0
    if any(st == "D" and LINT in paths for st, *paths in rows):
        warn("the lint itself is being deleted; not run here (pre-push and CI decide)")
        return 0
    tmp = tempfile.mkdtemp(prefix="ora-send-lint-")
    try:
        files = [p for p in git("ls-files", "-z", "--", "scheduled-tasks").split("\0")
                 if p and SPEC_RE.match(p)]
        git("checkout-index", f"--prefix={tmp}/", "--stdin", "-z",
            stdin="\0".join([LINT, *files]) + "\0")
        env = dict(os.environ, HOME=tmp, USERPROFILE=tmp, PYTHONIOENCODING="utf-8")
        try:
            r = subprocess.run([sys.executable, "-I", os.path.join(tmp, *LINT.split("/"))],
                               capture_output=True, text=True, encoding="utf-8",
                               errors="replace", timeout=TIMEOUT_S, env=env, cwd=tmp)
            out, crashed = r.stdout + r.stderr, r.returncode not in (0, 1)
        except subprocess.TimeoutExpired:
            out, crashed = "", True
        if crashed and lint_staged:
            print("send-lint pre-commit: BLOCKED -- the staged lint script crashed or timed "
                  f"out (limit {TIMEOUT_S}s); a broken lint must not land.", file=sys.stderr)
            return BLOCK
        if crashed:
            warn(f"lint crashed or timed out (limit {TIMEOUT_S}s); not blocking "
                 "(pre-push and CI still run it)")
            return 0
        block, other = blocking_failures(out, tasks, lint_staged)
        for f in other:
            warn(f"WARN (not in this commit): {f}")
        if block:
            print("send-lint pre-commit: BLOCKED -- the send-contract lint fails on what this "
                  "commit stages (rules.md section 2: retry a send only on exit 2 or 4):",
                  file=sys.stderr)
            for f in block:
                print(f"  FAIL {f}", file=sys.stderr)
            print("Fix the wording (e.g. 'Retry only on exit 2 or 4, once; never resend after "
                  "any other exit') or bypass deliberately with `git commit --no-verify`.",
                  file=sys.stderr)
            return BLOCK
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    """Exit BLOCK only for a deliberate block; any unexpected error is fail-open."""
    try:
        return run()
    except Exception as e:
        warn(f"skipped after an unexpected error ({type(e).__name__}: {str(e)[:160]})")
        return 0


if __name__ == "__main__":
    sys.exit(main())
