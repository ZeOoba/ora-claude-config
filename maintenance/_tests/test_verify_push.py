#!/usr/bin/env python3
"""Tests for verify-push.py (TDD -- written before the implementation).

The defect this guards: NOTHING in this setup verified, after a push, that the
remote branch actually moved to the local HEAD. A push was reported as
"succeeded" on the strength of the push command's own exit status -- and that
status is not trustworthy: piping `git push` into `tail` reported exit 0 while
the push had in fact FAILED (memory: feedback_piped_gate_exit_masking). Only an
unpiped re-run surfaced the real exit 1.

So the contract under test is deliberately double-barrelled:
  1. The tool NEVER consults the push's exit code. It re-derives truth from the
     remote itself (ls-remote) and compares it to local HEAD.
  2. The tool's own signal survives a pipe. Its exit code is the primary signal,
     but it ALSO prints a machine-readable RESULT_JSON line, so a caller that
     pipes it (and thereby masks the exit code) can still see DIVERGED.

Every distinguishable failure mode gets its OWN exit code -- collapsing
"remote unreachable" into "diverged" would be exactly the kind of ambiguous
green/red that caused the original false claim.

Run: python maintenance/_tests/test_verify_push.py
Pure stdlib. ASCII-only output (Windows cp1252 console). Temp repos only --
never touches a real repo.
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
VERIFY = os.path.join(os.path.dirname(HERE), "verify-push.py")

# Exit-code contract (mirrored in verify-push.py; kept literal here on purpose
# so a silent renumbering in the implementation fails these tests).
EXIT_MATCH = 0
EXIT_DIVERGED = 1
EXIT_NOT_A_REPO = 2
EXIT_DETACHED_HEAD = 3
EXIT_NO_UPSTREAM = 4
EXIT_REMOTE_UNREACHABLE = 5
EXIT_REMOTE_BRANCH_MISSING = 6

results = []


def expect(label, cond, detail=""):
    results.append((bool(cond), label))
    print("  %s %s%s" % ("PASS" if cond else "FAIL:", label,
                         "" if cond else "  -- " + str(detail)))


# --------------------------------------------------------------------------
# fixtures: real (tiny, local, network-free) git repos in a temp dir
# --------------------------------------------------------------------------
def _git(repo, *args):
    return subprocess.run(["git", "-C", repo] + list(args),
                          capture_output=True, text=True)


def _commit(work, name, body):
    with open(os.path.join(work, name), "w", encoding="utf-8") as fh:
        fh.write(body)
    _git(work, "add", "-A")
    _git(work, "commit", "-m", "add " + name)


def _make_pair(td, clone_name="work"):
    """A bare 'remote' plus a clone with one pushed commit on `main`."""
    remote = os.path.join(td, "remote.git")
    subprocess.run(["git", "init", "--bare", "-b", "main", remote],
                   capture_output=True, text=True)
    work = os.path.join(td, clone_name)
    subprocess.run(["git", "clone", remote, work], capture_output=True, text=True)
    _git(work, "config", "user.email", "t@example.com")
    _git(work, "config", "user.name", "Test")
    _git(work, "config", "commit.gpgsign", "false")
    _commit(work, "a.txt", "one\n")
    _git(work, "push", "-u", "origin", "main")
    return remote, work


def run(*args, **kw):
    """Invoke the CLI. Returns (rc, stdout, stderr)."""
    proc = subprocess.run([sys.executable, VERIFY] + list(args),
                          capture_output=True, text=True, cwd=kw.get("cwd"))
    return proc.returncode, proc.stdout, proc.stderr


def result_json(out):
    for line in out.splitlines():
        if line.startswith("RESULT_JSON="):
            return json.loads(line[len("RESULT_JSON="):])
    return None


def head_sha(repo):
    return _git(repo, "rev-parse", "HEAD").stdout.strip()


# --------------------------------------------------------------------------
# tests
# --------------------------------------------------------------------------
def test_matching_shas_exit_zero_and_print_both():
    """The happy path -- and it must still print both shas, because the whole
    point is that the output is pasteable as evidence."""
    with tempfile.TemporaryDirectory() as td:
        _remote, work = _make_pair(td)
        rc, out, err = run("--repo", work)
        sha = head_sha(work)
        expect("match: exit 0", rc == EXIT_MATCH, (rc, out, err))
        expect("match: prints local sha", sha[:12] in out, out)
        expect("match: prints remote sha too (both, not just one)",
               out.count(sha[:12]) >= 2, out)
        rj = result_json(out)
        expect("match: RESULT_JSON says match",
               rj and rj.get("match") is True and rj.get("status") == "MATCH", rj)
        expect("match: RESULT_JSON carries both shas",
               rj and rj.get("local_sha") == sha and rj.get("remote_sha") == sha, rj)
        expect("match: ahead/behind both 0",
               rj and rj.get("ahead") == 0 and rj.get("behind") == 0, rj)


def test_local_ahead_is_diverged_not_success():
    """A commit that was never pushed. This is the exact shape of the false
    'push succeeded' claim -- it MUST be non-zero."""
    with tempfile.TemporaryDirectory() as td:
        _remote, work = _make_pair(td)
        remote_sha = head_sha(work)
        _commit(work, "b.txt", "two\n")   # committed, deliberately NOT pushed
        local_sha = head_sha(work)
        rc, out, err = run("--repo", work)
        expect("local-ahead: exit 1 (DIVERGED)", rc == EXIT_DIVERGED, (rc, out, err))
        expect("local-ahead: names local sha", local_sha[:12] in out, out)
        expect("local-ahead: names remote sha", remote_sha[:12] in out, out)
        rj = result_json(out)
        expect("local-ahead: RESULT_JSON ahead=1 behind=0",
               rj and rj.get("ahead") == 1 and rj.get("behind") == 0, rj)
        expect("local-ahead: status DIVERGED",
               rj and rj.get("status") == "DIVERGED" and rj.get("match") is False, rj)


def test_local_behind_is_diverged():
    """Someone else pushed. Local HEAD != origin, in the other direction."""
    with tempfile.TemporaryDirectory() as td:
        remote, work = _make_pair(td)
        other = os.path.join(td, "other")
        subprocess.run(["git", "clone", remote, other], capture_output=True, text=True)
        _git(other, "config", "user.email", "t@example.com")
        _git(other, "config", "user.name", "Test")
        _commit(other, "c.txt", "three\n")
        _git(other, "push", "origin", "main")
        rc, out, err = run("--repo", work)
        expect("local-behind: exit 1 (DIVERGED)", rc == EXIT_DIVERGED, (rc, out, err))
        rj = result_json(out)
        expect("local-behind: RESULT_JSON ahead=0 behind=1",
               rj and rj.get("ahead") == 0 and rj.get("behind") == 1, rj)


def test_detached_head_has_its_own_exit_code():
    with tempfile.TemporaryDirectory() as td:
        _remote, work = _make_pair(td)
        _git(work, "checkout", "--detach", "HEAD")
        rc, out, err = run("--repo", work)
        blob = (out + err).lower()
        expect("detached HEAD: exit 3 (its own code, not 1)",
               rc == EXIT_DETACHED_HEAD, (rc, out, err))
        expect("detached HEAD: message says detached", "detached" in blob, blob)
        rj = result_json(out)
        expect("detached HEAD: status DETACHED_HEAD",
               rj and rj.get("status") == "DETACHED_HEAD", rj)


def test_detached_head_with_explicit_branch_still_verifies():
    """Worktrees sit at detached HEAD routinely. If the caller names the branch,
    the comparison is well-defined and must run."""
    with tempfile.TemporaryDirectory() as td:
        _remote, work = _make_pair(td)
        _git(work, "checkout", "--detach", "HEAD")
        rc, out, err = run("--repo", work, "--branch", "main")
        expect("detached + explicit --branch: exit 0", rc == EXIT_MATCH, (rc, out, err))


def test_missing_upstream_has_its_own_exit_code():
    with tempfile.TemporaryDirectory() as td:
        _remote, work = _make_pair(td)
        _git(work, "checkout", "-b", "feature/no-upstream")
        rc, out, err = run("--repo", work)
        blob = (out + err).lower()
        expect("no upstream: exit 4 (its own code)", rc == EXIT_NO_UPSTREAM, (rc, out, err))
        expect("no upstream: message says upstream", "upstream" in blob, blob)
        rj = result_json(out)
        expect("no upstream: status NO_UPSTREAM",
               rj and rj.get("status") == "NO_UPSTREAM", rj)


def test_unreachable_remote_has_its_own_exit_code():
    """An unreachable remote must NEVER read as 'in sync' and must NOT be
    collapsed into DIVERGED -- 'I could not look' is not 'they differ'."""
    with tempfile.TemporaryDirectory() as td:
        _remote, work = _make_pair(td)
        _git(work, "remote", "set-url", "origin",
             os.path.join(td, "does-not-exist.git"))
        rc, out, err = run("--repo", work)
        blob = (out + err).lower()
        expect("unreachable remote: exit 5 (its own code)",
               rc == EXIT_REMOTE_UNREACHABLE, (rc, out, err))
        expect("unreachable remote: message says unreachable",
               "unreachable" in blob, blob)
        rj = result_json(out)
        expect("unreachable remote: status REMOTE_UNREACHABLE",
               rj and rj.get("status") == "REMOTE_UNREACHABLE", rj)


def test_branch_absent_on_remote_has_its_own_exit_code():
    """Upstream is configured, remote is reachable, but the branch was never
    pushed -- the single most likely real 'the push silently failed' shape."""
    with tempfile.TemporaryDirectory() as td:
        _remote, work = _make_pair(td)
        _git(work, "checkout", "-b", "feature/never-pushed")
        _git(work, "config", "branch.feature/never-pushed.remote", "origin")
        _git(work, "config", "branch.feature/never-pushed.merge",
             "refs/heads/feature/never-pushed")
        rc, out, err = run("--repo", work)
        blob = (out + err).lower()
        expect("branch absent on remote: exit 6 (its own code)",
               rc == EXIT_REMOTE_BRANCH_MISSING, (rc, out, err))
        expect("branch absent on remote: message says not on remote",
               "remote" in blob and ("does not exist" in blob or "not found" in blob
                                     or "missing" in blob), blob)
        rj = result_json(out)
        expect("branch absent on remote: status REMOTE_BRANCH_MISSING",
               rj and rj.get("status") == "REMOTE_BRANCH_MISSING", rj)


def test_output_names_the_ref_actually_compared():
    """Caught by dogfooding the tool on its own branch. A branch created with
    `-b feat origin/main` has merge=refs/heads/main, so the tool correctly
    compares against refs/heads/main -- but it LABELLED that comparison
    'origin/feat'. A label that misnames the ref it compared is exactly the
    misleading evidence this tool exists to prevent, so the actual remote ref
    must appear in both the human output and RESULT_JSON."""
    with tempfile.TemporaryDirectory() as td:
        _remote, work = _make_pair(td)
        # branch tracking a DIFFERENTLY-NAMED remote ref, as `-b x origin/main` does
        _git(work, "checkout", "-b", "feature/tracks-main")
        _git(work, "config", "branch.feature/tracks-main.remote", "origin")
        _git(work, "config", "branch.feature/tracks-main.merge", "refs/heads/main")
        rc, out, err = run("--repo", work)
        rj = result_json(out)
        expect("differing merge ref: exit 0 (HEAD does equal refs/heads/main)",
               rc == EXIT_MATCH, (rc, out, err))
        expect("differing merge ref: output names refs/heads/main",
               "refs/heads/main" in out, out)
        expect("differing merge ref: does NOT claim it compared "
               "origin/feature/tracks-main",
               "origin/feature/tracks-main" not in out, out)
        expect("differing merge ref: RESULT_JSON carries remote_ref",
               rj and rj.get("remote_ref") == "refs/heads/main", rj)


def test_not_a_git_repo():
    with tempfile.TemporaryDirectory() as td:
        plain = os.path.join(td, "plain")
        os.makedirs(plain)
        rc, out, err = run("--repo", plain)
        rj = result_json(out)
        # rc alone is NOT sufficient evidence here: python's own "can't open
        # file" exit is also 2, so an absent implementation would fake a pass.
        # Demand the tool's own verdict marker as corroboration.
        expect("not a repo: exit 2", rc == EXIT_NOT_A_REPO, (rc, out, err))
        expect("not a repo: status NOT_A_REPO (not a coincidental rc=2)",
               rj and rj.get("status") == "NOT_A_REPO", rj)


def test_defaults_to_cwd():
    with tempfile.TemporaryDirectory() as td:
        _remote, work = _make_pair(td)
        rc, out, err = run(cwd=work)
        expect("no --repo: defaults to cwd, exit 0", rc == EXIT_MATCH, (rc, out, err))


def test_signal_survives_a_pipe():
    """THE anti-regression for feedback_piped_gate_exit_masking. A pipe can eat
    the exit code; it must not be able to eat the verdict. Piped stdout still
    has to carry an unambiguous DIVERGED marker."""
    with tempfile.TemporaryDirectory() as td:
        _remote, work = _make_pair(td)
        _commit(work, "b.txt", "two\n")
        piped = subprocess.run(
            '"%s" "%s" --repo "%s" | tail -n 20' % (sys.executable, VERIFY, work),
            shell=True, capture_output=True, text=True)
        out = piped.stdout
        rj = result_json(out)
        expect("piped: DIVERGED verdict still visible in stdout",
               "DIVERGED" in out, out)
        expect("piped: RESULT_JSON still parseable with match=false",
               rj and rj.get("match") is False, rj)


def test_never_reads_the_push_exit_code():
    """Structural guard: the implementation must not run `git push` at all, nor
    branch on a push's status. It re-derives truth from the remote."""
    if not os.path.exists(VERIFY):
        expect("implementation never invokes git push", False, "verify-push.py absent")
        return
    src = open(VERIFY, encoding="utf-8").read()
    code = "\n".join(ln for ln in src.splitlines() if not ln.strip().startswith("#"))
    expect("implementation never invokes git push", '"push"' not in code
           and "'push'" not in code, "found a push invocation")


def main():
    test_matching_shas_exit_zero_and_print_both()
    test_local_ahead_is_diverged_not_success()
    test_local_behind_is_diverged()
    test_detached_head_has_its_own_exit_code()
    test_detached_head_with_explicit_branch_still_verifies()
    test_missing_upstream_has_its_own_exit_code()
    test_unreachable_remote_has_its_own_exit_code()
    test_branch_absent_on_remote_has_its_own_exit_code()
    test_output_names_the_ref_actually_compared()
    test_not_a_git_repo()
    test_defaults_to_cwd()
    test_signal_survives_a_pipe()
    test_never_reads_the_push_exit_code()
    passed = sum(1 for ok, _ in results if ok)
    print("\nverify-push tests: %d/%d passed" % (passed, len(results)))
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
