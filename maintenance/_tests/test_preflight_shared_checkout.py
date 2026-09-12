#!/usr/bin/env python3
"""Tests for preflight-shared-checkout.py (TDD -- written before the code).

The defect this guards: CLAUDE.md and the session-context block both mandate a
SINGLE-WRITER preflight before editing anything in a shared checkout (~/.claude,
ora-skills, website-canonical, oxford-command-center) -- "run `git log --oneline
-1` + `git status`; if HEAD is newer than session-start or uncommitted changes
are not yours, STOP". A scan of the last 20 sessions found that trio typed by
hand 181 times across 13 sessions, never twice the same way, and the
"is HEAD newer than session-start?" half compared BY EYE against a sha nobody
had written down. An eyeballed gate is not a gate.

The contract under test is therefore:

  1. The three facts are established SEPARATELY and reported separately -- a
     dirty overlap, a competing claim, and a moved HEAD are different findings
     with different remedies, so each gets its own exit code. Collapsing them
     into one generic "STOP" is how a session talks itself past the one that
     mattered.
  2. Not-requested is NOT the same as unmeasurable. Omitting --since means the
     caller declined the HEAD check (reported, still CLEAR); a claims directory
     we tried and failed to read is INDETERMINATE and never green.
  3. Overlap is decided on PATH SEGMENTS, not string prefixes. `agents/` must
     contest `agents/foo.md`, and must NOT contest `agents-archive/foo.md`.
  4. The verdict survives a pipe (RESULT_JSON=), because piping a gate into
     `tail` masks its exit code -- the exact defect that produced a false
     "push succeeded" claim (memory: feedback_piped_gate_exit_masking).
  5. It is READ-ONLY. It reports; it never claims, commits, stashes or resets.

Run: python maintenance/_tests/test_preflight_shared_checkout.py
Pure stdlib. ASCII-only output (Windows cp1252 console). Temp repos and temp
claim dirs only -- never touches a real checkout or the live claims directory.
"""
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
PREFLIGHT = os.path.join(os.path.dirname(HERE), "preflight-shared-checkout.py")

# Exit-code contract (mirrored in the implementation; kept literal here on
# purpose so a silent renumbering there fails these tests).
EXIT_CLEAR = 0
EXIT_CONTESTED = 1
EXIT_NOT_A_REPO = 2
EXIT_HEAD_MOVED = 3
EXIT_INDETERMINATE = 4

MY_SESSION = "aaaaaaaa-1111-2222-3333-444444444444"
OTHER_SESSION = "bbbbbbbb-5555-6666-7777-888888888888"

results = []


def expect(label, cond, detail=""):
    results.append((bool(cond), label))
    print("  %s %s%s" % ("PASS" if cond else "FAIL:", label,
                         "" if cond else "  -- " + str(detail)))


# --------------------------------------------------------------------------
# fixtures: a real (tiny, local, network-free) git repo + a fake claims dir
# --------------------------------------------------------------------------
def _git(repo, *args):
    return subprocess.run(["git", "-C", repo] + list(args),
                          capture_output=True, text=True)


def _make_repo(td):
    """A git repo with one commit and a couple of committed, clean files."""
    work = os.path.join(td, "repo")
    os.makedirs(os.path.join(work, "agents"))
    os.makedirs(os.path.join(work, "agents-archive"))
    os.makedirs(os.path.join(work, "maintenance"))
    subprocess.run(["git", "init", "-b", "main", work],
                   capture_output=True, text=True)
    _git(work, "config", "user.email", "t@example.com")
    _git(work, "config", "user.name", "Test")
    _git(work, "config", "commit.gpgsign", "false")
    for rel in ("agents/one.md", "agents-archive/old.md", "maintenance/p.py"):
        with open(os.path.join(work, rel), "w", encoding="utf-8") as fh:
            fh.write("seed\n")
    _git(work, "add", "-A")
    _git(work, "commit", "-m", "seed")
    return work


def _dirty(work, rel, body="changed\n"):
    full = os.path.join(work, rel)
    d = os.path.dirname(full)
    if d and not os.path.isdir(d):
        os.makedirs(d)
    with open(full, "w", encoding="utf-8") as fh:
        fh.write(body)


def _claims_dir(td, name="claims"):
    p = os.path.join(td, name)
    os.makedirs(p)
    return p


def _write_claim(claims_dir, slug, session, paths, age_minutes=5,
                 description="doing a thing"):
    when = datetime.now() - timedelta(minutes=age_minutes)
    rec = {
        "session_id": session,
        "host_session_id": "local_test",
        "title": slug,
        "description": description,
        "claimed_at": when.strftime("%Y-%m-%dT%H:%M:%S"),
        "cwd": "irrelevant",
        "paths": [os.path.abspath(p).lower() for p in paths],
    }
    with open(os.path.join(claims_dir, slug + ".json"), "w",
              encoding="utf-8") as fh:
        json.dump(rec, fh)


def run(*args, **kw):
    """Invoke the CLI. Returns (rc, stdout, stderr)."""
    proc = subprocess.run([sys.executable, PREFLIGHT] + list(args),
                          capture_output=True, text=True, cwd=kw.get("cwd"),
                          env=kw.get("env"), encoding="utf-8", errors="replace")
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
def test_clean_repo_no_claims_is_clear():
    """Nothing dirty, nothing claimed -- the whole point is that this is a
    fast, quiet green. A gate that is noisy when clear gets ignored."""
    with tempfile.TemporaryDirectory() as td:
        work = _make_repo(td)
        rc, out, _ = run("--repo", work, "--claims-dir", _claims_dir(td),
                         "--session", MY_SESSION,
                         "--paths", os.path.join(work, "agents"))
        expect("clean repo + no claims -> exit 0", rc == EXIT_CLEAR, (rc, out))
        expect("clean verdict is CLEAR",
               (result_json(out) or {}).get("verdict") == "CLEAR", out)


def test_dirty_file_inside_requested_path_contests():
    with tempfile.TemporaryDirectory() as td:
        work = _make_repo(td)
        _dirty(work, "agents/one.md")
        rc, out, _ = run("--repo", work, "--claims-dir", _claims_dir(td),
                         "--session", MY_SESSION,
                         "--paths", os.path.join(work, "agents"))
        expect("dirty file inside requested path -> exit 1",
               rc == EXIT_CONTESTED, (rc, out))
        expect("output names the contesting file",
               "agents/one.md" in out.replace("\\", "/"), out)


def test_dirty_file_outside_requested_path_does_not_contest():
    """The 74-dirty-file ~/.claude checkout is the normal case. A preflight
    that reports every stranger's WIP regardless of scope is unusable."""
    with tempfile.TemporaryDirectory() as td:
        work = _make_repo(td)
        _dirty(work, "maintenance/p.py")
        rc, out, _ = run("--repo", work, "--claims-dir", _claims_dir(td),
                         "--session", MY_SESSION,
                         "--paths", os.path.join(work, "agents"))
        expect("dirty file outside scope -> still exit 0", rc == EXIT_CLEAR,
               (rc, out))


def test_untracked_file_counts_as_dirty():
    with tempfile.TemporaryDirectory() as td:
        work = _make_repo(td)
        _dirty(work, "agents/brand-new.md")
        rc, out, _ = run("--repo", work, "--claims-dir", _claims_dir(td),
                         "--session", MY_SESSION,
                         "--paths", os.path.join(work, "agents"))
        expect("untracked file inside scope contests", rc == EXIT_CONTESTED,
               (rc, out))


def test_overlap_is_segment_wise_not_string_prefix():
    """`agents` must not contest `agents-archive`. A naive startswith() would."""
    with tempfile.TemporaryDirectory() as td:
        work = _make_repo(td)
        _dirty(work, "agents-archive/old.md")
        rc, out, _ = run("--repo", work, "--claims-dir", _claims_dir(td),
                         "--session", MY_SESSION,
                         "--paths", os.path.join(work, "agents"))
        expect("agents/ does not contest agents-archive/", rc == EXIT_CLEAR,
               (rc, out))


def test_requesting_a_file_is_contested_by_a_claim_on_its_directory():
    """Overlap is symmetric: a claim on `agents/` covers a request for one
    file inside it, and vice versa."""
    with tempfile.TemporaryDirectory() as td:
        work = _make_repo(td)
        cd = _claims_dir(td)
        _write_claim(cd, "repo-housekeeping", OTHER_SESSION,
                     [os.path.join(work, "agents")])
        rc, out, _ = run("--repo", work, "--claims-dir", cd,
                         "--session", MY_SESSION,
                         "--paths", os.path.join(work, "agents", "one.md"))
        expect("dir claim contests a file request", rc == EXIT_CONTESTED,
               (rc, out))
        expect("output names the claiming session",
               OTHER_SESSION[:8] in out, out)


def test_my_own_claim_does_not_contest():
    """Re-running the preflight after claiming must not flag my own claim --
    otherwise the gate fires forever and gets bypassed."""
    with tempfile.TemporaryDirectory() as td:
        work = _make_repo(td)
        cd = _claims_dir(td)
        _write_claim(cd, "mine", MY_SESSION, [os.path.join(work, "agents")])
        rc, out, _ = run("--repo", work, "--claims-dir", cd,
                         "--session", MY_SESSION,
                         "--paths", os.path.join(work, "agents"))
        expect("own claim does not contest", rc == EXIT_CLEAR, (rc, out))


def test_expired_claim_does_not_contest():
    """Claims have a 2h TTL. A stale file from a session that died three days
    ago must not block work forever."""
    with tempfile.TemporaryDirectory() as td:
        work = _make_repo(td)
        cd = _claims_dir(td)
        _write_claim(cd, "ancient", OTHER_SESSION,
                     [os.path.join(work, "agents")], age_minutes=4000)
        rc, out, _ = run("--repo", work, "--claims-dir", cd,
                         "--session", MY_SESSION, "--ttl-minutes", "120",
                         "--paths", os.path.join(work, "agents"))
        expect("expired claim does not contest", rc == EXIT_CLEAR, (rc, out))
        expect("expired claim is still reported as expired",
               "expired" in out.lower(), out)


def test_head_moved_when_since_sha_differs():
    with tempfile.TemporaryDirectory() as td:
        work = _make_repo(td)
        rc, out, _ = run("--repo", work, "--claims-dir", _claims_dir(td),
                         "--session", MY_SESSION,
                         "--since", "0" * 40,
                         "--paths", os.path.join(work, "agents"))
        expect("HEAD != --since -> exit 3", rc == EXIT_HEAD_MOVED, (rc, out))


def test_head_moved_outranks_contested():
    """If the repo advanced under me AND something is dirty, the moved HEAD is
    the finding that changes what I do next (rebase/re-read before editing)."""
    with tempfile.TemporaryDirectory() as td:
        work = _make_repo(td)
        _dirty(work, "agents/one.md")
        rc, out, _ = run("--repo", work, "--claims-dir", _claims_dir(td),
                         "--session", MY_SESSION, "--since", "0" * 40,
                         "--paths", os.path.join(work, "agents"))
        expect("HEAD_MOVED outranks CONTESTED", rc == EXIT_HEAD_MOVED,
               (rc, out))
        j = result_json(out) or {}
        expect("both findings still reported in JSON",
               j.get("head_moved") is True
               and bool(j.get("dirty_overlap_foreign")), j)


def test_matching_since_sha_is_clear():
    with tempfile.TemporaryDirectory() as td:
        work = _make_repo(td)
        rc, out, _ = run("--repo", work, "--claims-dir", _claims_dir(td),
                         "--session", MY_SESSION,
                         "--since", head_sha(work),
                         "--paths", os.path.join(work, "agents"))
        expect("HEAD == --since -> exit 0", rc == EXIT_CLEAR, (rc, out))


def test_short_since_sha_is_accepted():
    """Sessions copy short shas out of `git log --oneline`. Requiring 40 chars
    would just push people back to eyeballing it."""
    with tempfile.TemporaryDirectory() as td:
        work = _make_repo(td)
        rc, out, _ = run("--repo", work, "--claims-dir", _claims_dir(td),
                         "--session", MY_SESSION,
                         "--since", head_sha(work)[:7],
                         "--paths", os.path.join(work, "agents"))
        expect("short --since sha matches", rc == EXIT_CLEAR, (rc, out))


def test_omitting_since_is_clear_but_reported_as_not_checked():
    """Declining a check is not the same as failing it -- but it must be
    visible, not silently absent."""
    with tempfile.TemporaryDirectory() as td:
        work = _make_repo(td)
        rc, out, _ = run("--repo", work, "--claims-dir", _claims_dir(td),
                         "--session", MY_SESSION,
                         "--paths", os.path.join(work, "agents"))
        expect("no --since -> exit 0", rc == EXIT_CLEAR, (rc, out))
        j = result_json(out) or {}
        expect("no --since -> head_moved is null, not false",
               j.get("head_moved") is None, j)
        expect("no --since is visible in the text output",
               "not checked" in out.lower(), out)


def test_not_a_git_repo():
    with tempfile.TemporaryDirectory() as td:
        plain = os.path.join(td, "plain")
        os.makedirs(plain)
        rc, out, _ = run("--repo", plain, "--claims-dir", _claims_dir(td),
                         "--session", MY_SESSION, "--paths", plain)
        expect("not a git repo -> exit 2", rc == EXIT_NOT_A_REPO, (rc, out))


def test_unreadable_claims_dir_is_indeterminate_not_clear():
    """Unmeasurable is uncertain, never clean. A missing claims directory is
    the single most likely way this gate would silently stop working."""
    with tempfile.TemporaryDirectory() as td:
        work = _make_repo(td)
        rc, out, _ = run("--repo", work,
                         "--claims-dir", os.path.join(td, "does-not-exist"),
                         "--session", MY_SESSION,
                         "--paths", os.path.join(work, "agents"))
        expect("missing claims dir -> exit 4 (not 0)", rc == EXIT_INDETERMINATE,
               (rc, out))


def test_malformed_claim_file_is_indeterminate_not_ignored():
    with tempfile.TemporaryDirectory() as td:
        work = _make_repo(td)
        cd = _claims_dir(td)
        with open(os.path.join(cd, "broken.json"), "w", encoding="utf-8") as fh:
            fh.write("{not json")
        rc, out, _ = run("--repo", work, "--claims-dir", cd,
                         "--session", MY_SESSION,
                         "--paths", os.path.join(work, "agents"))
        expect("malformed claim -> exit 4", rc == EXIT_INDETERMINATE, (rc, out))
        expect("malformed claim names the file", "broken" in out, out)


def test_contested_outranks_indeterminate():
    """A definite finding beats an unknown -- both are non-zero, but the
    actionable one should be what the exit code says."""
    with tempfile.TemporaryDirectory() as td:
        work = _make_repo(td)
        cd = _claims_dir(td)
        _dirty(work, "agents/one.md")
        with open(os.path.join(cd, "broken.json"), "w", encoding="utf-8") as fh:
            fh.write("{not json")
        rc, out, _ = run("--repo", work, "--claims-dir", cd,
                         "--session", MY_SESSION,
                         "--paths", os.path.join(work, "agents"))
        expect("CONTESTED outranks INDETERMINATE", rc == EXIT_CONTESTED,
               (rc, out))


def test_relative_paths_resolve_against_repo():
    """Callers type `--paths agents/` far more often than an absolute path."""
    with tempfile.TemporaryDirectory() as td:
        work = _make_repo(td)
        _dirty(work, "agents/one.md")
        rc, out, _ = run("--repo", work, "--claims-dir", _claims_dir(td),
                         "--session", MY_SESSION, "--paths", "agents")
        expect("relative --paths resolve against --repo", rc == EXIT_CONTESTED,
               (rc, out))


def test_session_falls_back_to_env():
    with tempfile.TemporaryDirectory() as td:
        work = _make_repo(td)
        cd = _claims_dir(td)
        _write_claim(cd, "mine", MY_SESSION, [os.path.join(work, "agents")])
        env = dict(os.environ, CLAUDE_CODE_SESSION_ID=MY_SESSION)
        proc = subprocess.run(
            [sys.executable, PREFLIGHT, "--repo", work, "--claims-dir", cd,
             "--paths", os.path.join(work, "agents")],
            capture_output=True, text=True, env=env)
        expect("own session read from CLAUDE_CODE_SESSION_ID",
               proc.returncode == EXIT_CLEAR, (proc.returncode, proc.stdout))


def test_signal_survives_a_pipe():
    """Piping masks the exit code. RESULT_JSON= must carry the verdict anyway."""
    with tempfile.TemporaryDirectory() as td:
        work = _make_repo(td)
        _dirty(work, "agents/one.md")
        rc, out, _ = run("--repo", work, "--claims-dir", _claims_dir(td),
                         "--session", MY_SESSION,
                         "--paths", os.path.join(work, "agents"))
        j = result_json(out)
        expect("RESULT_JSON present", j is not None, out)
        expect("RESULT_JSON verdict is CONTESTED",
               (j or {}).get("verdict") == "CONTESTED", j)


def test_json_flag_emits_only_json():
    with tempfile.TemporaryDirectory() as td:
        work = _make_repo(td)
        rc, out, _ = run("--repo", work, "--claims-dir", _claims_dir(td),
                         "--session", MY_SESSION, "--json",
                         "--paths", os.path.join(work, "agents"))
        try:
            parsed = json.loads(out)
        except Exception as exc:
            parsed = None
            expect("--json emits parseable JSON on stdout", False, exc)
        if parsed is not None:
            expect("--json emits parseable JSON on stdout", True)
            expect("--json carries the verdict",
                   parsed.get("verdict") == "CLEAR", parsed)


def _sessions_dir(td, name="sessions"):
    p = os.path.join(td, name)
    os.makedirs(p)
    return p


def _touched(sessions_dir, session, paths):
    """Write a session's touched-files.txt in commit_provenance's line format:
    `<normcase(abspath)>\\t<epoch>`."""
    import time
    d = os.path.join(sessions_dir, session)
    if not os.path.isdir(d):
        os.makedirs(d)
    with open(os.path.join(d, "touched-files.txt"), "w", encoding="utf-8") as fh:
        for p in paths:
            fh.write("%s\t%.6f\n" % (os.path.normcase(os.path.abspath(p)),
                                     time.time()))


def test_my_own_dirty_edit_does_not_contest():
    """The doctrine is 'uncommitted changes that are NOT YOURS'. A preflight
    that flags my own in-progress edit fires on every re-run and gets bypassed
    -- the same failure mode already guarded for claims."""
    with tempfile.TemporaryDirectory() as td:
        work = _make_repo(td)
        sd = _sessions_dir(td)
        _dirty(work, "agents/one.md")
        _touched(sd, MY_SESSION, [os.path.join(work, "agents", "one.md")])
        rc, out, _ = run("--repo", work, "--claims-dir", _claims_dir(td),
                         "--sessions-dir", sd, "--session", MY_SESSION,
                         "--paths", os.path.join(work, "agents"))
        expect("my own dirty edit -> exit 0", rc == EXIT_CLEAR, (rc, out))
        j = result_json(out) or {}
        expect("my own dirty edit is reported as mine",
               j.get("dirty_overlap_mine") and not j.get("dirty_overlap_foreign"),
               j)


def test_another_sessions_dirty_edit_contests():
    with tempfile.TemporaryDirectory() as td:
        work = _make_repo(td)
        sd = _sessions_dir(td)
        _dirty(work, "agents/one.md")
        _touched(sd, OTHER_SESSION, [os.path.join(work, "agents", "one.md")])
        rc, out, _ = run("--repo", work, "--claims-dir", _claims_dir(td),
                         "--sessions-dir", sd, "--session", MY_SESSION,
                         "--paths", os.path.join(work, "agents"))
        expect("another session's dirty edit -> exit 1", rc == EXIT_CONTESTED,
               (rc, out))
        expect("output names the owning session", OTHER_SESSION[:8] in out, out)


def test_dirty_file_touched_by_both_still_contests():
    """Co-mingling is the hazard being prevented; a file I touched that someone
    else ALSO touched is the worst case, not an exemption."""
    with tempfile.TemporaryDirectory() as td:
        work = _make_repo(td)
        sd = _sessions_dir(td)
        _dirty(work, "agents/one.md")
        _touched(sd, MY_SESSION, [os.path.join(work, "agents", "one.md")])
        _touched(sd, OTHER_SESSION, [os.path.join(work, "agents", "one.md")])
        rc, out, _ = run("--repo", work, "--claims-dir", _claims_dir(td),
                         "--sessions-dir", sd, "--session", MY_SESSION,
                         "--paths", os.path.join(work, "agents"))
        expect("shared dirty file still contests", rc == EXIT_CONTESTED,
               (rc, out))


def test_unattributed_dirty_file_contests():
    """Unknown owner is not 'mine'. Provenance only starts recording at a
    session's first edit, so absence proves nothing -- stay conservative."""
    with tempfile.TemporaryDirectory() as td:
        work = _make_repo(td)
        sd = _sessions_dir(td)
        _dirty(work, "agents/one.md")
        rc, out, _ = run("--repo", work, "--claims-dir", _claims_dir(td),
                         "--sessions-dir", sd, "--session", MY_SESSION,
                         "--paths", os.path.join(work, "agents"))
        expect("unattributed dirty file contests", rc == EXIT_CONTESTED,
               (rc, out))


def test_missing_sessions_dir_stays_conservative():
    """If provenance is unavailable we cannot prove anything is mine, so every
    overlap contests -- and the caveat is stated, not hidden."""
    with tempfile.TemporaryDirectory() as td:
        work = _make_repo(td)
        _dirty(work, "agents/one.md")
        rc, out, _ = run("--repo", work, "--claims-dir", _claims_dir(td),
                         "--sessions-dir", os.path.join(td, "nope"),
                         "--session", MY_SESSION,
                         "--paths", os.path.join(work, "agents"))
        expect("no provenance -> still contests", rc == EXIT_CONTESTED,
               (rc, out))
        expect("no provenance -> caveat is visible",
               "provenance" in out.lower(), out)


def test_is_read_only():
    """It reports. It must never claim, commit, stash, checkout or reset --
    a preflight that mutates the thing it is inspecting is not a preflight."""
    with open(PREFLIGHT, "r", encoding="utf-8") as fh:
        code = fh.read()
    for verb in ("commit", "stash", "reset", "checkout", "push", "add"):
        expect("never invokes git %s" % verb,
               '"%s"' % verb not in code and "'%s'" % verb not in code,
               "found a git %s invocation" % verb)


# --------------------------------------------------------------------------
# local-only advisory (added 2026-09-12): the OI-249 merge-forward scripts
# lived ONLY on the checkout's feature branch -- never on origin/main -- and a
# CLEAR preflight let a session edit them assuming they would ship with main.
# Advisory by design: the exit-code contract above is unchanged.
# --------------------------------------------------------------------------
def _branch_with_local_only_file(td):
    work = _make_repo(td)
    _git(work, "checkout", "-q", "-b", "feat/x")
    _dirty(work, "maintenance/branch_only.py", "only on the branch\n")
    _git(work, "add", "maintenance/branch_only.py")
    _git(work, "commit", "-q", "-m", "branch-only file")
    return work


def test_local_only_path_reported_off_canonical():
    with tempfile.TemporaryDirectory() as td:
        work = _branch_with_local_only_file(td)
        rc, out, _ = run("--repo", work, "--claims-dir", _claims_dir(td),
                         "--session", MY_SESSION,
                         "--paths", "maintenance/branch_only.py", "agents/one.md")
        rj = result_json(out) or {}
        expect("local-only: exit code unchanged (still CLEAR)", rc == EXIT_CLEAR, (rc, out))
        expect("local-only: current_branch reported", rj.get("current_branch") == "feat/x", rj)
        expect("local-only: off_canonical true", rj.get("off_canonical") is True, rj)
        expect("local-only: branch-only file listed, file also on main not listed",
               rj.get("local_only_paths") == ["maintenance/branch_only.py"], rj)
        expect("local-only: compared against local 'main' when no origin",
               rj.get("canonical_ref") == "main", rj)
        expect("local-only: human line names the branch and the path",
               "LOCAL-ONLY" in out and "feat/x" in out and "branch_only.py" in out, out)


def test_local_only_directory_scope_lists_branch_only_files():
    with tempfile.TemporaryDirectory() as td:
        work = _branch_with_local_only_file(td)
        rc, out, _ = run("--repo", work, "--claims-dir", _claims_dir(td),
                         "--session", MY_SESSION, "--paths", "maintenance")
        rj = result_json(out) or {}
        expect("local-only: directory scope expands to its branch-only files",
               rj.get("local_only_paths") == ["maintenance/branch_only.py"], rj)


def test_on_canonical_branch_no_local_only_noise():
    with tempfile.TemporaryDirectory() as td:
        work = _make_repo(td)
        rc, out, _ = run("--repo", work, "--claims-dir", _claims_dir(td),
                         "--session", MY_SESSION, "--paths", "agents")
        rj = result_json(out) or {}
        expect("on-canonical: off_canonical false", rj.get("off_canonical") is False, rj)
        expect("on-canonical: no local-only paths", rj.get("local_only_paths") == [], rj)
        expect("on-canonical: no LOCAL-ONLY line", "LOCAL-ONLY" not in out, out)


def test_origin_canonical_preferred_and_unpushed_counted():
    with tempfile.TemporaryDirectory() as td:
        seed = _make_repo(td)
        bare = os.path.join(td, "origin.git")
        subprocess.run(["git", "clone", "-q", "--bare", seed, bare], capture_output=True)
        work = os.path.join(td, "clone")
        subprocess.run(["git", "clone", "-q", bare, work], capture_output=True)
        _git(work, "config", "user.email", "t@example.com")
        _git(work, "config", "user.name", "Test")
        _git(work, "checkout", "-q", "-b", "feat/y")
        _git(work, "push", "-q", "-u", "origin", "feat/y")
        _dirty(work, "maintenance/new.py", "new\n")
        _git(work, "add", "maintenance/new.py")
        _git(work, "commit", "-q", "-m", "unpushed")
        rc, out, _ = run("--repo", work, "--claims-dir", _claims_dir(td),
                         "--session", MY_SESSION, "--paths", "maintenance/new.py")
        rj = result_json(out) or {}
        expect("origin: canonical_ref is origin/main", rj.get("canonical_ref") == "origin/main", rj)
        expect("origin: unpushed_commits counted vs upstream", rj.get("unpushed_commits") == 1, rj)
        expect("origin: new file is local-only", rj.get("local_only_paths") == ["maintenance/new.py"], rj)


# --------------------------------------------------------------------------
# review hardening (2026-09-12 independent review found false-CLEAR paths)
# --------------------------------------------------------------------------
def test_non_ascii_dirty_path_still_contests():
    """git quotes non-ASCII names in porcelain ("agents/caf\\303\\251.md");
    stripping quotes left the escapes, so the overlap was missed -> CLEAR."""
    with tempfile.TemporaryDirectory() as td:
        work = _make_repo(td)
        _dirty(work, "agents/caf\u00e9.md")
        rc, out, _ = run("--repo", work, "--claims-dir", _claims_dir(td),
                         "--session", MY_SESSION, "--paths", os.path.join(work, "agents"))
        rj = result_json(out) or {}
        expect("non-ascii: dirty file in scope -> CONTESTED", rc == EXIT_CONTESTED, (rc, out))
        expect("non-ascii: path reported decoded",
               any(d["path"] == "agents/caf\u00e9.md" for d in rj.get("dirty_overlap_foreign", [])),
               rj)


def test_git_unavailable_is_not_a_repo_with_json():
    with tempfile.TemporaryDirectory() as td:
        work = _make_repo(td)
        env = {"PATH": os.path.dirname(sys.executable),
               "SYSTEMROOT": os.environ.get("SYSTEMROOT", r"C:\Windows")}
        rc, out, err = run("--repo", work, "--claims-dir", _claims_dir(td),
                           "--session", MY_SESSION, "--paths", "agents", env=env)
        expect("no-git: exit 2, not a traceback", rc == EXIT_NOT_A_REPO, (rc, out, err[-300:]))
        expect("no-git: RESULT_JSON still printed",
               (result_json(out) or {}).get("verdict") == "NOT_A_REPO", out)


def test_short_session_prefix_cannot_claim_foreign_file():
    """Ownership used startswith(mine[:8]); --session 'b' made any 'b...' owner mine."""
    with tempfile.TemporaryDirectory() as td:
        work = _make_repo(td)
        sd = _sessions_dir(td)
        _dirty(work, "agents/one.md")
        _touched(sd, OTHER_SESSION, [os.path.join(work, "agents", "one.md")])
        rc, out, _ = run("--repo", work, "--claims-dir", _claims_dir(td),
                         "--sessions-dir", sd, "--session", OTHER_SESSION[:1],
                         "--paths", os.path.join(work, "agents"))
        expect("short-session: foreign dirty file still CONTESTED", rc == EXIT_CONTESTED, (rc, out))


def test_short_session_prefix_cannot_dismiss_competing_claim():
    with tempfile.TemporaryDirectory() as td:
        work = _make_repo(td)
        cd = _claims_dir(td)
        _write_claim(cd, "theirs", OTHER_SESSION, [os.path.join(work, "agents")])
        rc, out, _ = run("--repo", work, "--claims-dir", cd,
                         "--session", OTHER_SESSION[:1], "--paths", os.path.join(work, "agents"))
        expect("short-session: competing claim still CONTESTED", rc == EXIT_CONTESTED, (rc, out))


def test_ora_active_work_dir_env_honored():
    with tempfile.TemporaryDirectory() as td:
        work = _make_repo(td)
        cd = _claims_dir(td, "env-claims")
        _write_claim(cd, "theirs", OTHER_SESSION, [os.path.join(work, "agents")])
        env = dict(os.environ, ORA_ACTIVE_WORK_DIR=cd)
        rc, out, _ = run("--repo", work, "--session", MY_SESSION,
                         "--paths", os.path.join(work, "agents"), env=env)
        rj = result_json(out) or {}
        expect("env-claims: ORA_ACTIVE_WORK_DIR used when --claims-dir omitted",
               rc == EXIT_CONTESTED and os.path.normcase(rj.get("claims_dir") or "") == os.path.normcase(cd),
               (rc, rj.get("claims_dir")))


def test_off_canonical_clean_message_does_not_overclaim():
    """ls-tree is case-sensitive and silent on not-yet-existing paths, so the
    tool can only say none are branch-only -- not that all exist on main."""
    with tempfile.TemporaryDirectory() as td:
        work = _make_repo(td)
        _git(work, "checkout", "-q", "-b", "feat/z")
        rc, out, _ = run("--repo", work, "--claims-dir", _claims_dir(td),
                         "--session", MY_SESSION, "--paths", "agents/one.md", "agents/not-yet.md")
        expect("message: says no branch-only paths", "no scope path is committed only" in out, out)
        expect("message: no 'every scope path also exists' overclaim",
               "every scope path also exists" not in out, out)


def test_repo_given_as_subdirectory_still_sees_dirty_files():
    """porcelain paths are relative to the TOPLEVEL; joining them onto a
    subdirectory --repo (the cwd default when run from maintenance/) missed
    every overlap -> CLEAR."""
    with tempfile.TemporaryDirectory() as td:
        work = _make_repo(td)
        _dirty(work, "agents/one.md")
        _dirty(work, "maintenance/p.py")
        sub = os.path.join(work, "maintenance")
        rc, out, _ = run("--repo", sub, "--claims-dir", _claims_dir(td),
                         "--session", MY_SESSION,
                         "--paths", os.path.join(work, "agents", "one.md"))
        expect("subdir-repo: absolute scope dirty file -> CONTESTED", rc == EXIT_CONTESTED, (rc, out))
        rc, out, _ = run("--repo", sub, "--claims-dir", _claims_dir(td, "c2"),
                         "--session", MY_SESSION, "--paths", "p.py")
        expect("subdir-repo: path relative to --repo dir still resolves -> CONTESTED",
               rc == EXIT_CONTESTED, (rc, out))
        rc, out, _ = run("--repo", sub, "--claims-dir", _claims_dir(td, "c3"),
                         "--session", MY_SESSION, "--paths", "p.py", cwd=sub)
        rj = result_json(out) or {}
        expect("subdir-repo: report repo is the toplevel",
               os.path.normcase(rj.get("repo") or "") == os.path.normcase(os.path.abspath(work)), rj)


def _short_path(p):
    try:
        import ctypes
        buf = ctypes.create_unicode_buffer(1024)
        n = ctypes.windll.kernel32.GetShortPathNameW(p, buf, 1024)
        return buf.value if n else p
    except Exception:
        return p


def test_repo_via_junction_or_short_name_still_contests():
    """--show-toplevel returns the real long path; scope built on a junction or
    8.3 spelling never overlapped it -> CLEAR."""
    with tempfile.TemporaryDirectory() as td:
        work = _make_repo(td)
        _dirty(work, "agents/one.md")
        spellings = []
        link = os.path.join(td, "linked")
        mk = subprocess.run(["cmd", "/c", "mklink", "/J", link, work],
                            capture_output=True, text=True)
        if mk.returncode == 0:
            spellings.append(("junction", link))
        else:
            print("  (skip junction: mklink /J unavailable: %s)" % mk.stderr.strip()[:80])
        short = _short_path(work)
        if short.lower() != work.lower():
            spellings.append(("8.3", short))
        else:
            print("  (skip 8.3: no short name generated for %s)" % work)
        for i, (label, spelled) in enumerate(spellings):
            rc, out, _ = run("--repo", spelled, "--claims-dir", _claims_dir(td, "j%d" % i),
                             "--session", MY_SESSION, "--paths", "agents")
            expect("%s repo, relative scope -> CONTESTED" % label, rc == EXIT_CONTESTED, (rc, out[-400:]))
            rc, out, _ = run("--repo", spelled, "--claims-dir", _claims_dir(td, "k%d" % i),
                             "--session", MY_SESSION,
                             "--paths", os.path.join(spelled, "agents", "one.md"))
            expect("%s repo, absolute scope in same spelling -> CONTESTED" % label,
                   rc == EXIT_CONTESTED, (rc, out[-400:]))
        expect("junction/8.3: at least one alternate spelling exercised", spellings, "none available")


def test_foreign_touch_recorded_via_junction_spelling_still_contests():
    """Provenance keys are stored as the Edit hook saw them. A foreign edit
    recorded through a junction never matched a realpath lookup, so the file
    read as 'mine alone' -> CLEAR."""
    with tempfile.TemporaryDirectory() as td:
        work = _make_repo(td)
        link = os.path.join(td, "linked")
        mk = subprocess.run(["cmd", "/c", "mklink", "/J", link, work],
                            capture_output=True, text=True)
        if mk.returncode != 0:
            print("  (skip: mklink /J unavailable)")
            return
        _dirty(work, "agents/one.md")
        sd = _sessions_dir(td)
        _touched(sd, MY_SESSION, [os.path.join(work, "agents", "one.md")])
        _touched(sd, OTHER_SESSION, [os.path.join(link, "agents", "one.md")])
        for label, repo_arg in (("real repo", work), ("junction repo", link)):
            rc, out, _ = run("--repo", repo_arg, "--claims-dir", _claims_dir(td, label.replace(" ", "")),
                             "--sessions-dir", sd, "--session", MY_SESSION, "--paths", "agents")
            expect("junction-provenance (%s): foreign touch via other spelling -> CONTESTED" % label,
                   rc == EXIT_CONTESTED, (rc, out[-400:]))


def test_foreign_touch_recorded_via_short_file_name_still_contests():
    with tempfile.TemporaryDirectory() as td:
        work = _make_repo(td)
        long_rel = "agents/averyverylongname.txt"
        _dirty(work, long_rel)
        real = os.path.join(work, "agents", "averyverylongname.txt")
        short = _short_path(real)
        if os.path.basename(short).lower() == os.path.basename(real).lower():
            print("  (skip: no 8.3 file name generated)")
            return
        sd = _sessions_dir(td)
        _touched(sd, MY_SESSION, [real])
        _touched(sd, OTHER_SESSION, [short])
        rc, out, _ = run("--repo", work, "--claims-dir", _claims_dir(td),
                         "--sessions-dir", sd, "--session", MY_SESSION, "--paths", "agents")
        expect("8.3-file-provenance: foreign touch via short file name -> CONTESTED",
               rc == EXIT_CONTESTED, (rc, out[-400:]))


def test_unencodable_filename_still_prints_result_json():
    with tempfile.TemporaryDirectory() as td:
        work = _make_repo(td)
        _dirty(work, "agents/e\U0001F600.md")
        env = dict(os.environ)
        env.pop("PYTHONIOENCODING", None)
        env.pop("PYTHONUTF8", None)
        rc, out, err = run("--repo", work, "--claims-dir", _claims_dir(td),
                           "--session", MY_SESSION, "--paths", "agents", env=env)
        expect("emoji: CONTESTED without a traceback", rc == EXIT_CONTESTED and "Traceback" not in err,
               (rc, err[-300:]))
        expect("emoji: RESULT_JSON printed", (result_json(out) or {}).get("verdict") == "CONTESTED", out[-300:])


def test_blank_or_too_short_since_is_indeterminate_not_unchanged():
    with tempfile.TemporaryDirectory() as td:
        work = _make_repo(td)
        for i, bad in enumerate((" ", "a", "12345")):
            rc, out, _ = run("--repo", work, "--claims-dir", _claims_dir(td, "c%d" % i),
                             "--session", MY_SESSION, "--since", bad, "--paths", "agents")
            rj = result_json(out) or {}
            expect("since %r: INDETERMINATE, head_moved not reported false" % bad,
                   rc == EXIT_INDETERMINATE and rj.get("head_moved") is None and rj.get("since_error"),
                   (rc, rj.get("head_moved"), rj.get("since_error")))
        rc, out, _ = run("--repo", work, "--claims-dir", _claims_dir(td, "cok"),
                         "--session", MY_SESSION, "--since", head_sha(work)[:7], "--paths", "agents")
        expect("since 7-char sha still CLEAR", rc == EXIT_CLEAR, (rc, out))


def test_unresolvable_canonical_is_reported_not_silent():
    with tempfile.TemporaryDirectory() as td:
        work = _branch_with_local_only_file(td)
        rc, out, _ = run("--repo", work, "--claims-dir", _claims_dir(td),
                         "--session", MY_SESSION, "--canonical", "trunk",
                         "--paths", "maintenance/branch_only.py")
        rj = result_json(out) or {}
        expect("no-canonical: exit code unchanged", rc == EXIT_CLEAR, (rc, out))
        expect("no-canonical: local_only_paths is None (unmeasured, not empty)",
               rj.get("local_only_paths") is None and rj.get("canonical_ref_error"), rj)
        expect("no-canonical: human line says it could not check", "could not" in out, out)


def main():
    test_clean_repo_no_claims_is_clear()
    test_dirty_file_inside_requested_path_contests()
    test_dirty_file_outside_requested_path_does_not_contest()
    test_untracked_file_counts_as_dirty()
    test_overlap_is_segment_wise_not_string_prefix()
    test_requesting_a_file_is_contested_by_a_claim_on_its_directory()
    test_my_own_claim_does_not_contest()
    test_expired_claim_does_not_contest()
    test_head_moved_when_since_sha_differs()
    test_head_moved_outranks_contested()
    test_matching_since_sha_is_clear()
    test_short_since_sha_is_accepted()
    test_omitting_since_is_clear_but_reported_as_not_checked()
    test_not_a_git_repo()
    test_unreadable_claims_dir_is_indeterminate_not_clear()
    test_malformed_claim_file_is_indeterminate_not_ignored()
    test_contested_outranks_indeterminate()
    test_relative_paths_resolve_against_repo()
    test_session_falls_back_to_env()
    test_signal_survives_a_pipe()
    test_json_flag_emits_only_json()
    test_my_own_dirty_edit_does_not_contest()
    test_another_sessions_dirty_edit_contests()
    test_dirty_file_touched_by_both_still_contests()
    test_unattributed_dirty_file_contests()
    test_missing_sessions_dir_stays_conservative()
    test_is_read_only()
    test_local_only_path_reported_off_canonical()
    test_local_only_directory_scope_lists_branch_only_files()
    test_on_canonical_branch_no_local_only_noise()
    test_origin_canonical_preferred_and_unpushed_counted()
    test_unresolvable_canonical_is_reported_not_silent()
    test_non_ascii_dirty_path_still_contests()
    test_git_unavailable_is_not_a_repo_with_json()
    test_short_session_prefix_cannot_claim_foreign_file()
    test_short_session_prefix_cannot_dismiss_competing_claim()
    test_ora_active_work_dir_env_honored()
    test_off_canonical_clean_message_does_not_overclaim()
    test_repo_given_as_subdirectory_still_sees_dirty_files()
    test_repo_via_junction_or_short_name_still_contests()
    test_foreign_touch_recorded_via_junction_spelling_still_contests()
    test_foreign_touch_recorded_via_short_file_name_still_contests()
    test_unencodable_filename_still_prints_result_json()
    test_blank_or_too_short_since_is_indeterminate_not_unchanged()
    passed = sum(1 for ok, _ in results if ok)
    print("\npreflight-shared-checkout tests: %d/%d passed"
          % (passed, len(results)))
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
