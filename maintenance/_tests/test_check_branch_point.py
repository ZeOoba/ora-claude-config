#!/usr/bin/env python3
"""Tests for check-branch-point.py -- built on real throwaway git repos, because
the whole point of the tool is ancestry, and a mocked git would only prove the
mock agrees with itself."""
import importlib.util
import os
import subprocess
import sys
import tempfile
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(os.path.dirname(HERE), "check-branch-point.py")

_spec = importlib.util.spec_from_file_location("cbp", SCRIPT)
cbp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cbp)

_results = []


def check(name, cond, detail=""):
    _results.append((bool(cond), name))
    if not cond:
        print("FAIL %s  %s" % (name, detail))
    else:
        print("PASS %s" % name)


def run(repo, *args):
    subprocess.run(["git"] + list(args), cwd=repo, check=True,
                   capture_output=True, text=True)


def commit(repo, msg, fname=None):
    fname = fname or (msg.replace(" ", "_") + ".txt")
    with open(os.path.join(repo, fname), "w", encoding="utf-8") as fh:
        fh.write(msg)
    run(repo, "add", fname)
    run(repo, "commit", "-m", msg, "--no-verify")


def make_repo():
    d = tempfile.mkdtemp(prefix="cbp-")
    run(d, "init", "-b", "main")
    run(d, "config", "user.email", "t@example.com")
    run(d, "config", "user.name", "T")
    commit(d, "base commit")
    return d


def main():
    # --- the clean shape: branch cut directly from the base -------------------
    r1 = make_repo()
    try:
        run(r1, "checkout", "-q", "-b", "feature")
        commit(r1, "my work one")
        commit(r1, "my work two")
        a = cbp.analyze("main", r1)
        check("clean branch: base IS an ancestor", a["base_is_ancestor"] is True, repr(a))
        check("clean branch: exactly the 2 authored commits", len(a["commits"]) == 2,
              repr(a["commits"]))
        # NOT ok without --expect, even here: intent is unanswerable, so the tool
        # declines to certify. Returning 0 anyway was a false green in the very
        # shape this tool exists for (see M1 in the 2026-08-16 review).
        check("clean branch, no --expect: NOT ok -- unverified is not clean",
              a["ok"] is False, repr(a))
        check("clean branch, no --expect: exit code is 1, not 0",
              cbp.main(["--base", "main", "--repo", r1]) == 1)
        check("clean branch: --expect matching passes",
              cbp.analyze("main", r1, expect=2)["ok"] is True)
        check("clean branch: --expect mismatch fails",
              cbp.analyze("main", r1, expect=1)["ok"] is False)
        # Without a declared intent there is nothing to certify AGAINST, so even a
        # genuinely clean branch gets the commit list rather than a bare "OK" --
        # the ancestry-only pass is exactly what missed PR #130's extra commits.
        check("clean branch, no --expect: lists commits instead of a bare OK",
              "does NOT mean these are all yours" in cbp.format_report(a),
              cbp.format_report(a))
        check("clean branch, --expect 2: certifies with an explicit OK",
              "OK" in cbp.format_report(cbp.analyze("main", r1, expect=2)))
    finally:
        shutil.rmtree(r1, ignore_errors=True)

    # --- THE PR #130 SHAPE: branch cut from an integration branch that is ahead
    # of the base. The PR targets the base and silently carries the integration
    # branch's commits too.
    r2 = make_repo()
    try:
        run(r2, "checkout", "-q", "-b", "integration")
        commit(r2, "someone elses WIP")
        commit(r2, "someone elses merge fix")
        run(r2, "checkout", "-q", "-b", "feature")
        commit(r2, "my work one")
        a = cbp.analyze("main", r2)
        # THE TRAP THIS TEST EXISTS FOR: `main` never moved, so it IS still an
        # ancestor -- yet the branch carries integration's 2 commits on top of the
        # 1 authored here. An ancestry-only check calls this clean. It is not.
        check("integration-cut branch: ancestry is True and therefore proves nothing",
              a["base_is_ancestor"] is True, repr(a))
        check("integration-cut branch: reports ALL 3 commits, not just the authored 1",
              len(a["commits"]) == 3, repr(a["commits"]))
        check("integration-cut branch: NOT certified without a declared intent",
              a["certified"] is False, repr(a))
        rep = cbp.format_report(a)
        check("integration-cut branch: report refuses to say a bare OK",
              "does NOT mean these are all yours" in rep, rep)
        check("integration-cut branch: report lists the foreign subjects",
              "someone elses WIP" in rep, rep)
        check("integration-cut branch: --expect 1 (what the author meant) FAILS",
              cbp.analyze("main", r2, expect=1)["ok"] is False)
        check("integration-cut branch: --expect 3 (the truth) certifies",
              cbp.analyze("main", r2, expect=3)["certified"] is True)

        # And the shape where the base HAS moved on -- ancestry genuinely False.
        run(r2, "checkout", "-q", "main")
        commit(r2, "base moved on")
        run(r2, "checkout", "-q", "feature")
        b = cbp.analyze("main", r2)
        check("moved-base branch: base is NOT an ancestor",
              b["base_is_ancestor"] is False, repr(b))
        check("moved-base branch: not ok", b["ok"] is False)
        brep = cbp.format_report(b)
        check("moved-base branch: report is [ACTION]",
              "[ACTION] BRANCH_POINT" in brep, brep)
        check("moved-base branch: report names the remedy",
              "rebase" in brep or "cherry-pick" in brep, brep)
    finally:
        shutil.rmtree(r2, ignore_errors=True)

    # --- undetermined must never read as clean --------------------------------
    r3 = make_repo()
    try:
        a = cbp.analyze("origin/does-not-exist", r3)
        check("unresolvable base: error set", bool(a["error"]), repr(a))
        check("unresolvable base: NOT ok (a typo must not read as a pass)",
              a["ok"] is False)
        check("unresolvable base: report says UNDETERMINED",
              "UNDETERMINED" in cbp.format_report(a))
        check("unresolvable base: exit code 2, distinct from findings(1)/clean(0)",
              cbp.main(["--base", "origin/does-not-exist", "--repo", r3]) == 2)
    finally:
        shutil.rmtree(r3, ignore_errors=True)

    a = cbp.analyze("main", tempfile.gettempdir())
    check("non-repo: errors rather than raising", bool(a["error"]) and a["ok"] is False,
          repr(a))

    # --- added 2026-09-07 alongside the hooks/lib/git_probe_common.py
    # extraction: repo=None must mean "run against cwd" (a naive shared git()
    # that always passes `-C <repo>` breaks this, since `-C None` is not a
    # valid path -- caught before it shipped). ---------------------------------
    r4 = make_repo()
    try:
        run(r4, "checkout", "-q", "-b", "feature")
        commit(r4, "my work one")
        prev_cwd = os.getcwd()
        try:
            os.chdir(r4)
            a = cbp.analyze("main", None, expect=1)
            check("repo=None resolves against cwd (not a broken -C None)",
                  a["ok"] is True, repr(a))
            check("repo=None: cbp.main() with no --repo also works",
                  cbp.main(["--base", "main", "--expect", "1"]) == 0)
        finally:
            os.chdir(prev_cwd)
    finally:
        shutil.rmtree(r4, ignore_errors=True)

    # --- repo="" (explicit-but-empty -- what argparse yields for `--repo ""`,
    # distinct from the None default) must FAIL, never silently fall back to
    # cwd. `git -C ""` is a documented no-op that resolves against the CURRENT
    # directory, so a naive `-C repo` translation would let a caller's
    # `--repo "$UNSET_VAR"` silently certify whatever repo the process
    # happens to be sitting in -- the exact false-green this tool exists to
    # prevent. cwd is deliberately set to a VALID repo here, so a pass would
    # prove the empty string fell back to cwd, not merely "found no repo". ---
    r5 = make_repo()
    try:
        prev_cwd = os.getcwd()
        try:
            os.chdir(r5)
            a = cbp.analyze("main", "", expect=0)
            check("repo='' does not silently fall back to cwd",
                  a["ok"] is False and bool(a["error"]), repr(a))
        finally:
            os.chdir(prev_cwd)
    finally:
        shutil.rmtree(r5, ignore_errors=True)

    # --- the repo= argument is actually USED, not silently ignored in favor
    # of cwd -- mutation-tested: dropping the repo argument from the git()
    # call site made this check (and only this check) fail. ------------------
    r6a = make_repo()
    r6b = make_repo()
    try:
        run(r6b, "checkout", "-q", "-b", "other-feature")
        commit(r6b, "work only in r6b")
        prev_cwd = os.getcwd()
        try:
            os.chdir(r6a)  # cwd points at r6a...
            a = cbp.analyze("main", r6b, expect=1)  # ...--repo explicitly says r6b
            check("explicit --repo overrides cwd, not silently ignored",
                  a["ok"] is True and len(a["commits"]) == 1, repr(a))
        finally:
            os.chdir(prev_cwd)
    finally:
        shutil.rmtree(r6a, ignore_errors=True)
        shutil.rmtree(r6b, ignore_errors=True)

    # --- white-box: force the very first git() call (rev-parse HEAD) to fail
    # -- real git essentially never fails this on a valid repo, so failure-
    # path coverage needs a monkeypatch. --------------------------------------
    r7 = make_repo()
    try:
        orig_git = cbp.git

        def fake_git(args, repo=None):
            if args and args[0] == "rev-parse" and args[1:2] == ["HEAD"]:
                return 128, "simulated HEAD resolve failure"
            return orig_git(args, repo)

        cbp.git = fake_git
        try:
            a = cbp.analyze("main", r7)
            check("HEAD resolve failure is undetermined, not a crash",
                  a["error"] is not None and "cannot resolve HEAD" in a["error"], repr(a))
        finally:
            cbp.git = orig_git
    finally:
        shutil.rmtree(r7, ignore_errors=True)

    passed = sum(1 for ok, _ in _results if ok)
    print("\ncheck-branch-point tests: %d/%d passed" % (passed, len(_results)))
    return 0 if passed == len(_results) else 1


if __name__ == "__main__":
    sys.exit(main())
