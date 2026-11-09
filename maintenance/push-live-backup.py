#!/usr/bin/env python3
"""Off-box backup of the LIVE ~/.claude branch, plus the check that alarms when it is not
off-box.

WHY (decision 2026-11-08, Gabriel): the primary checkout ~/.claude sits on
live/primary-checkout, which carries commits no remote ref holds (41 on 2026-11-08, the
oldest from 2026-11-04: memory sync checkpoints, triage commits, archive records). The
only routes to GitHub were a session happening to push, or push-fleet-heartbeat.ps1's
backup step, which pushes MAIN-checkout work to origin/main and never this branch. A disk
loss would have taken that history with it, and nothing alarmed.

PUSH MODE (default)
    Pushes the live checkout's HEAD to refs/heads/backup/live-primary on <remote> with an
    EXPLICIT lease: the backup ref's current remote value is read with ls-remote and passed
    as --force-with-lease=<ref>:<that sha> (empty = "must not exist yet"). The backup
    tracks the live branch even across a non-fast-forward rewrite, but a concurrent writer
    that moved the backup ref between the read and the push makes the push fail
    (LEASE_REJECTED) instead of being clobbered.

    Rules (each is a refusal, never a workaround):
      * NEVER skips hooks. The push runs the checkout's normal pre-push shim (doctrine
        gate, hook-tests gate, confidentiality scan). There is no flag to bypass it.
      * GATE PRECONDITION: refuses to push unless the hooks dir git will actually use
        (`git rev-parse --git-path hooks`, honours core.hooksPath) has a pre-push that
        invokes git-prepush-confidential-scan.py, AND this checkout's copy of that scan
        defines and calls scan_compressed() (#427, 2026-11-08). A checkout whose gate
        predates the compressed-blob scan would push .gz/.tgz contents unscanned -- the
        live branch was in exactly that state when this was written.
      * Pushes HEAD only while HEAD is on --branch (default live/primary-checkout). A
        detached HEAD or another branch checked out is a refusal: backing up whatever
        happens to be checked out under the live backup name would overwrite the backup
        with the wrong history.
      * Every non-success writes the failure marker and exits non-zero; success writes the
        ok stamp and clears the marker. Only a verified remote tip (ls-remote re-read
        equals the pushed sha) counts as success -- a push's exit status is not evidence
        (verify-push.py's rule).

CHECK MODE (--check) -- wired into fleet-deadman.ps1 (check 6)
    Fetches <remote> (--prune, so a deleted remote branch cannot vouch for anything) and
    asks: which commits reachable from the live HEAD are on NO <remote> ref? Alarms when
    the oldest of them (committer time) is older than --grace-hours (default 26: one daily
    backup cycle plus slack, so a commit made after the morning backup is not a false
    alarm), or when the failure marker from the last push is present. A fetch that fails
    is COULD_NOT_LOOK (exit 2), never a pass.

BEACONS (maintenance/_state/, gitignored -- a tracked outage marker would be committed)
    live-backup-push-ok.json      every success (verdict, sha, ts); age = last success
    live-backup-push-failed.json  every failure; removed on the next success. Read by
                                  --check and therefore by fleet-deadman.ps1.

Exit codes
  push:  0 PUSHED / UP_TO_DATE   1 BLOCKED_OR_FAILED (gate block, auth, network)
         2 LEASE_REJECTED   3 REJECTED (other remote/client rejection)
         4 PRECONDITION (wrong branch, detached, gate lacks compressed scan, no pre-push)
         5 PUSHED_UNVERIFIED   6 ERROR (git error, timeout, usage)
  check: 0 CONTAINED / PENDING_WITHIN_GRACE   1 NOT_OFFBOX or BACKUP_PUSH_FAILED
         2 COULD_NOT_LOOK
A RESULT_JSON= line is always the last line printed, so a piped caller still sees it.

Usage
    python maintenance/push-live-backup.py [--repo PATH] [--remote origin]
        [--branch live/primary-checkout]
        [--state-dir PATH] [--push-timeout 2700]
    python maintenance/push-live-backup.py --check [--grace-hours 26] [--repo PATH] ...

Stdlib only. ASCII-only.
"""
import argparse
import datetime
import json
import os
import re
import subprocess
import sys
import time

DEFAULT_REPO = os.path.join(os.path.expanduser("~"), ".claude")
DEFAULT_BRANCH = "live/primary-checkout"
# Fixed, not an option (REFUTE 2026-11-08: a --target flag let a typo force-rewrite any origin
# branch, main included, and shared one beacon pair across targets).
TARGET_REF = "refs/heads/backup/live-primary"
OK_STAMP = "live-backup-push-ok.json"
FAILED_MARKER = "live-backup-push-failed.json"
SCAN_REL = os.path.join("hooks", "git-prepush-confidential-scan.py")
SCAN_NAME = "git-prepush-confidential-scan.py"
DETAIL_MAX = 4000

EXIT_PUSH = {
    "PUSHED": 0, "UP_TO_DATE": 0, "BLOCKED_OR_FAILED": 1, "LEASE_REJECTED": 2,
    "REJECTED": 3, "PRECONDITION": 4, "PUSHED_UNVERIFIED": 5, "ERROR": 6,
}

_STATUS_LINE = re.compile(r"^([ +\-*=!])\t([^\t]*):([^\t]+)\t(.*)$")


# ---------------------------------------------------------------- pure helpers

def classify_push(rc, out, target_ref):
    """Verdict from `git push --porcelain` output. Only the status block AFTER git's
    'To <url>' header counts -- a gate's own log (printed before git reaches its status)
    can contain status-shaped lines. No status line for target_ref => the push never got
    that far (pre-push hook block, auth, network): BLOCKED_OR_FAILED."""
    seen_header = False
    for line in (out or "").splitlines():
        if line.startswith("To "):
            seen_header = True
            continue
        if not seen_header:
            continue
        m = _STATUS_LINE.match(line)
        if not m or m.group(3) != target_ref:
            continue
        flag, summary = m.group(1), m.group(4)
        if flag == "!":
            return "LEASE_REJECTED" if "stale info" in summary else "REJECTED"
        if flag == "=":
            return "UP_TO_DATE" if rc == 0 else "BLOCKED_OR_FAILED"
        return "PUSHED" if rc == 0 else "BLOCKED_OR_FAILED"
    return "BLOCKED_OR_FAILED"


def push_argv(remote, sha, target_ref, expected_remote_sha):
    """The ONE push command this tool issues. Explicit lease value: the remote sha read by
    ls-remote just before, or empty (= the ref must not exist yet). Never a bare --force,
    never a hook skip."""
    lease = "--force-with-lease=%s:%s" % (target_ref, expected_remote_sha or "")
    return ["push", "--porcelain", lease, remote, "%s:%s" % (sha, target_ref)]


def hook_runs_scan(hook_text):
    """Structural, not substring (REFUTE 2026-11-08: a hook of `exit 0` plus a COMMENT naming
    the scan passed). True only when a non-comment line runs hooks/<scan> and no earlier
    non-comment line is an unconditional `exit` or an `exec` (which would end the shim
    before the scan)."""
    for line in hook_text.splitlines():
        t = line.strip()
        if not t or t.startswith("#"):
            continue
        if ("hooks/" + SCAN_NAME) in t.replace("\\", "/"):
            return True
        if re.match(r"(exit|exec)\b", t):
            return False
    return False


def scan_main_calls_compressed(src):
    """Structural, not regex (REFUTE 2026-11-08: the scan's own docstring mention of
    'scan_compressed()' satisfied a count of 2). True only when the module defines
    scan_compressed at top level AND main() contains a real call to it."""
    import ast
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return False
    top = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    if "scan_compressed" not in top or "main" not in top:
        return False
    return any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "scan_compressed"
               for n in ast.walk(top["main"]))


def gate_precondition(worktree_root, hooks_dir):
    """(ok, reason). The pre-push hook git will run must invoke the confidentiality scan,
    and this checkout's scan must define AND call scan_compressed()."""
    pre_push = os.path.join(hooks_dir, "pre-push")
    try:
        with open(pre_push, encoding="utf-8", errors="replace") as fh:
            hook = fh.read()
    except OSError:
        return False, "no pre-push hook at %s -- the push would run ungated" % pre_push
    if not hook_runs_scan(hook):
        return False, ("pre-push hook at %s does not run the confidential scan (%s) on an executable "
                       "line ahead of any unconditional exit/exec" % (pre_push, SCAN_NAME))
    scan = os.path.join(worktree_root, SCAN_REL)
    try:
        with open(scan, encoding="utf-8", errors="replace") as fh:
            src = fh.read()
    except OSError:
        return False, "confidential scan missing at %s" % scan
    if not scan_main_calls_compressed(src):
        return False, ("this checkout's %s lacks scan_compressed() (#427 compressed-blob scan); "
                       "merge origin/main into the live branch first" % SCAN_REL.replace(os.sep, "/"))
    return True, "ok"


def _utc_now_iso():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _atomic_write_json(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2, sort_keys=True)
        fh.write("\n")
    os.replace(tmp, path)


def write_beacon(state_dir, ok, payload):
    """Success: write the ok stamp, remove the failure marker. Failure: write the marker,
    leave the ok stamp alone (its age is the time since the last success). Never raises;
    returns False when the write failed."""
    try:
        os.makedirs(state_dir, exist_ok=True)
        body = dict(payload)
        body.setdefault("ts", _utc_now_iso())
        if ok:
            _atomic_write_json(os.path.join(state_dir, OK_STAMP), body)
            failed = os.path.join(state_dir, FAILED_MARKER)
            if os.path.exists(failed):
                os.remove(failed)
        else:
            _atomic_write_json(os.path.join(state_dir, FAILED_MARKER), body)
        return True
    except Exception:
        return False


def read_failed_marker(state_dir):
    """None when absent; the parsed marker; or {'_unreadable': True} when present but not
    parseable (a marker that exists is evidence of a failure even if it is corrupt)."""
    path = os.path.join(state_dir, FAILED_MARKER)
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {"_unreadable": True}
    except Exception:
        return {"_unreadable": True}


def _ok_stamp_age_hours(state_dir):
    try:
        return round((time.time() - os.path.getmtime(os.path.join(state_dir, OK_STAMP))) / 3600.0, 2)
    except OSError:
        return None


def offbox_verdict(pending_times, now, grace_hours, failed_marker,
                   ok_stamp_age_hours=None, stamp_max_hours=48.0):
    """pending_times: committer epoch of each commit reachable from the live HEAD that is
    on no remote ref. A future-dated commit never masks an old one (we key on the min, and
    a future date is clamped to now). A rebase resets committer time, so with commits
    pending a stale or absent ok stamp is ALSO a finding: the backup has not succeeded in
    stamp_max_hours, whatever the commit dates say."""
    problems = []
    res = {"pending_count": len(pending_times), "grace_hours": grace_hours,
           "oldest_pending_hours": None, "ok_stamp_age_hours": ok_stamp_age_hours}
    if pending_times:
        oldest_h = round(max(0.0, now - min(min(pending_times), now)) / 3600.0, 2)
        res["oldest_pending_hours"] = oldest_h
        if oldest_h > grace_hours:
            problems.append("NOT_OFFBOX: %d live commit(s) on no remote ref, oldest %.1fh old (grace %sh)"
                            % (len(pending_times), oldest_h, grace_hours))
        elif ok_stamp_age_hours is None or ok_stamp_age_hours > stamp_max_hours:
            problems.append("NOT_OFFBOX: %d live commit(s) on no remote ref and no successful backup in %s"
                            % (len(pending_times), "recorded history" if ok_stamp_age_hours is None
                               else "%.1fh (max %sh)" % (ok_stamp_age_hours, stamp_max_hours)))
    if failed_marker is not None:
        if failed_marker.get("_unreadable"):
            problems.append("BACKUP_PUSH_FAILED: failure marker %s present but unreadable" % FAILED_MARKER)
        else:
            problems.append("BACKUP_PUSH_FAILED: last live backup push %s at %s"
                            % (failed_marker.get("verdict", "?"), failed_marker.get("ts", "?")))
    if problems:
        verdict = "NOT_OFFBOX" if problems[0].startswith("NOT_OFFBOX") else "BACKUP_PUSH_FAILED"
        res.update(verdict=verdict, rc=1, problems=problems)
    elif pending_times:
        res.update(verdict="PENDING_WITHIN_GRACE", rc=0, problems=[])
    else:
        res.update(verdict="CONTAINED", rc=0, problems=[])
    return res


# ---------------------------------------------------------------- git plumbing

def _env():
    env = dict(os.environ)
    for k in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY",
              "GIT_ALTERNATE_OBJECT_DIRECTORIES"):
        env.pop(k, None)
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GCM_INTERACTIVE"] = "never"   # a Git Credential Manager GUI prompt would hang the run
    return env


def _kill_tree(proc):
    if os.name == "nt":
        try:
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)],
                           capture_output=True, timeout=30)
        except Exception:
            pass
    try:
        proc.kill()
    except Exception:
        pass


def git(repo, args, timeout=120):
    """(rc, combined output). rc None = timed out (child tree killed)."""
    proc = subprocess.Popen(["git", "-C", repo] + list(args), stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, env=_env())
    try:
        out, _ = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        _kill_tree(proc)
        try:
            proc.communicate(timeout=10)
        except Exception:
            pass
        return None, "timed out after %ss" % timeout
    return proc.returncode, out.decode("utf-8", "replace")


def _git_ok(repo, args, timeout=120):
    rc, out = git(repo, args, timeout)
    if rc != 0:
        raise RuntimeError("git %s failed (rc=%s): %s" % (" ".join(args), rc, out.strip()[-500:]))
    return out.strip()


def remote_ref_sha(repo, remote, ref, timeout=120):
    out = _git_ok(repo, ["ls-remote", "--refs", remote, ref], timeout)
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) == 2 and parts[1] == ref:
            return parts[0]
    return None


# ---------------------------------------------------------------- modes

def run_push(a):
    target_ref = TARGET_REF
    res = {"mode": "push", "repo": a.repo, "remote": a.remote, "branch": a.branch,
           "target": target_ref, "sha": None}

    def done(verdict, detail=""):
        res["verdict"] = verdict
        if detail:
            res["detail"] = detail[-DETAIL_MAX:]
        ok = EXIT_PUSH[verdict] == 0
        res["beacon_written"] = write_beacon(a.state_dir, ok, res)
        return EXIT_PUSH[verdict], res

    try:
        top = _git_ok(a.repo, ["rev-parse", "--show-toplevel"])
        rc, head_ref = git(a.repo, ["symbolic-ref", "-q", "HEAD"])
        head_ref = (head_ref or "").strip()
        if rc != 0 or not head_ref:
            return done("PRECONDITION", "HEAD is detached; refusing to back up an unnamed state as %s" % a.branch)
        if head_ref != "refs/heads/" + a.branch:
            return done("PRECONDITION", "HEAD is on %s, not %s; refusing to overwrite the live backup with another branch"
                        % (head_ref, a.branch))
        sha = _git_ok(a.repo, ["rev-parse", "--verify", "HEAD^{commit}"])
        res["sha"] = sha
        hooks_dir = _git_ok(a.repo, ["rev-parse", "--path-format=absolute", "--git-path", "hooks"])
        ok, why = gate_precondition(top, hooks_dir)
        if not ok:
            return done("PRECONDITION", why)
        expected = remote_ref_sha(a.repo, a.remote, target_ref)
        res["remote_before"] = expected
        rc, out = git(a.repo, push_argv(a.remote, sha, target_ref, expected), timeout=a.push_timeout)
        if rc is None:
            return done("ERROR", "push " + out)
        verdict = classify_push(rc, out, target_ref)
        if verdict not in ("PUSHED", "UP_TO_DATE"):
            return done(verdict, out)
        after = remote_ref_sha(a.repo, a.remote, target_ref)
        res["remote_after"] = after
        if after != sha:
            return done("PUSHED_UNVERIFIED", "remote %s reads %s after push, expected %s" % (target_ref, after, sha))
        return done(verdict)
    except Exception as exc:
        return done("ERROR", "%s: %s" % (type(exc).__name__, exc))


def run_check(a):
    res = {"mode": "check", "repo": a.repo, "remote": a.remote}
    try:
        rc, out = git(a.repo, ["fetch", "--prune", "--no-write-fetch-head", a.remote], timeout=a.fetch_timeout)
        if rc != 0:
            res.update(verdict="COULD_NOT_LOOK", rc=2,
                       problems=["fetch %s failed (rc=%s): %s -- off-box state UNKNOWN, not clean"
                                 % (a.remote, rc, (out or "").strip()[-300:])])
            return 2, res
        res["sha"] = _git_ok(a.repo, ["rev-parse", "--verify", "HEAD^{commit}"], 20)
        rc, b = git(a.repo, ["symbolic-ref", "-q", "--short", "HEAD"], 20)
        res["head_branch"] = b.strip() if rc == 0 else "(detached)"
        out = _git_ok(a.repo, ["log", "--format=%ct", "HEAD", "--not", "--remotes=" + a.remote], 20)
        times = [int(t) for t in out.split() if t.strip().isdigit()]
        v = offbox_verdict(times, time.time(), a.grace_hours, read_failed_marker(a.state_dir),
                           ok_stamp_age_hours=_ok_stamp_age_hours(a.state_dir),
                           stamp_max_hours=a.stamp_max_hours)
        res.update(v)
        return v["rc"], res
    except Exception as exc:
        res.update(verdict="COULD_NOT_LOOK", rc=2, problems=["%s: %s" % (type(exc).__name__, exc)])
        return 2, res


def _safe_stdout():
    # The gate's stderr (captured into `detail`) carries non-ASCII (em-dashes); a cp1252
    # stdout under the scheduler crashed print() after the marker was written, so the exit
    # code and RESULT_JSON were lost (REFUTE 2026-11-08). Output encoding must never fail.
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(errors="backslashreplace")
        except Exception:
            pass


class _UsageError(Exception):
    pass


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise _UsageError(message)


def main(argv=None):
    _safe_stdout()
    p = _Parser(description=__doc__.split("\n")[0])
    p.add_argument("--check", action="store_true", help="report whether the live HEAD is off-box")
    p.add_argument("--repo", default=DEFAULT_REPO)
    p.add_argument("--remote", default="origin")
    p.add_argument("--branch", default=DEFAULT_BRANCH)
    p.add_argument("--state-dir", default=None, help="default: <repo>/maintenance/_state")
    p.add_argument("--grace-hours", type=float, default=26.0)
    p.add_argument("--stamp-max-hours", type=float, default=48.0,
                   help="with commits pending, an ok stamp older than this (or absent) alarms even inside grace")
    p.add_argument("--push-timeout", type=int, default=2700, help="seconds; the pre-push gate alone runs ~11 min")
    # check mode must finish inside fleet-deadman.ps1's 240s bound: fetch 120 + 3 small git
    # calls x 20 = 180 worst case, so the dead-man does not kill a fetch mid-ref-update
    p.add_argument("--fetch-timeout", type=int, default=120)
    try:
        a = p.parse_args(argv)
    except _UsageError as exc:
        # A mis-typed scheduler prompt must fail loud, not silently: the push-mode marker is
        # written to the default state dir (check mode only reads it, so it writes nothing).
        res = {"verdict": "ERROR", "detail": "usage: %s" % exc}
        if "--check" not in (argv if argv is not None else sys.argv[1:]):
            write_beacon(os.path.join(DEFAULT_REPO, "maintenance", "_state"), False, res)
        print("usage error: %s" % exc)
        print("RESULT_JSON=" + json.dumps(res, sort_keys=True))
        return 6
    a.repo = os.path.abspath(a.repo)
    if a.state_dir is None:
        a.state_dir = os.path.join(a.repo, "maintenance", "_state")
    rc, res = run_check(a) if a.check else run_push(a)
    if a.check:
        print("[%s] %s" % (res.get("verdict"), "; ".join(res.get("problems") or [])
                            or "%s pending commit(s)" % res.get("pending_count", 0)))
    else:
        print("[%s] %s -> %s %s" % (res.get("verdict"), res.get("sha"), res.get("target"),
                                    (res.get("detail") or "")[-600:]))
    print("RESULT_JSON=" + json.dumps(res, sort_keys=True))
    return rc


if __name__ == "__main__":
    sys.exit(main())
