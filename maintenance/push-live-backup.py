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
      * GATE PRECONDITION, three layers, all must pass before any push:
          1. the pre-push in the hooks dir git will actually use (`git rev-parse
             --git-path hooks`, honours core.hooksPath) is, by EXACT normalized content,
             one of KNOWN_GOOD_SHIMS (v2 / v1) -- pinned, not parsed: shell is not safely
             parseable here (REFUTE rounds 1-2 defeated a substring and a line-parse check);
          2. AST lint: this checkout's scan defines scan_compressed() and main() calls it
             (fast, readable refusal; NOT proof -- dead code would pass it);
          3. BEHAVIOURAL CANARY: that scan, run against a throwaway TEMP repo whose commit
             adds a .gz carrying a credential-shaped string, must exit non-zero with a
             COMPRESSED finding (canary_scan). This is the proof the #427 compressed-blob
             scan is live. A checkout whose gate predates #427 -- the live branch's state
             when this was written -- fails layer 2 and is refused.
      * Pushes HEAD only while HEAD is on live/primary-checkout (a constant). A
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
BRANCH = "live/primary-checkout"   # constant, like TARGET_REF (REFUTE round 2 nit)
# Fixed, not an option (REFUTE 2026-11-08: a --target flag let a typo force-rewrite any origin
# branch, main included, and shared one beacon pair across targets).
TARGET_REF = "refs/heads/backup/live-primary"
OK_STAMP = "live-backup-push-ok.json"
FAILED_MARKER = "live-backup-push-failed.json"
SCAN_REL = os.path.join("hooks", "git-prepush-confidential-scan.py")
SCAN_NAME = "git-prepush-confidential-scan.py"
REQUIRE_REFS_ENV = "ORA_PREPUSH_REQUIRE_REFS"
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


# Known-good pre-push shims, compared by EXACT normalized content (REFUTE rounds 1-2,
# 2026-11-08: substring and then line-parse checks were each defeated -- a comment naming the
# scan, `if false; then ...`, a backgrounded scan. Shell cannot be safely parsed here; it is
# pinned instead). Normalization drops only inert text: CRLF, trailing whitespace, blank
# lines and comment lines after the shebang. A new shim version must be added here, in
# review, before the backup will push through it.
KNOWN_GOOD_SHIMS = {
    "v2 (installed 2026-11-08)": (
        '#!/bin/sh\n'
        'ROOT="$(git rev-parse --show-toplevel)"\n'
        'REFS="$(mktemp)" || exit 1\n'
        'trap \'rm -f "$REFS"\' EXIT\n'
        'cat > "$REFS"\n'
        'python "$ROOT/hooks/git-prepush-doctrine-gate.py" "$@" </dev/null || exit $?\n'
        'python "$ROOT/hooks/git-prepush-hook-tests-gate.py" "$@" <"$REFS" || exit $?\n'
        'python "$ROOT/hooks/git-prepush-confidential-scan.py" "$@" <"$REFS"\n'),
    "v1 (archived 2026-11-08)": (
        '#!/bin/sh\n'
        'ROOT="$(git rev-parse --show-toplevel)"\n'
        'python "$ROOT/hooks/git-prepush-doctrine-gate.py" "$@" </dev/null || exit $?\n'
        'python "$ROOT/hooks/git-prepush-hook-tests-gate.py" "$@" </dev/null || exit $?\n'
        'exec python "$ROOT/hooks/git-prepush-confidential-scan.py" "$@"\n'),
}


_COMMENT_LINE = re.compile(r"^[ \t]*#")


def shim_text_is_clean(text):
    """REFUTE round 3 (2026-11-09): a single stray \\r or Unicode space survived str.rstrip()
    and line normalization, compared equal, and starved the scan's stdin -- an end-to-end
    unscanned push. Rules (text is the file's bytes decoded latin-1):
      * no \\r ANYWHERE -- not even as CRLF: one CRLF line in an LF shim IS that bypass
        (`cat > "$REFS"\\r` writes a different file), and both installed shims are LF-only;
      * no control character anywhere except \\n and \\t;
      * executable lines are printable ASCII only. Bytes > 126 are tolerated only on
        comment lines (^[ \\t]*#, never executed by sh) because both installed shims carry
        UTF-8 em-dashes in their header comments."""
    if "\r" in text:
        return False
    for i, line in enumerate(text.split("\n")):
        comment = _COMMENT_LINE.match(line) is not None and not (i == 0 and line.startswith("#!"))
        for ch in line:
            o = ord(ch)
            if (o < 32 and ch != "\t") or o == 127:
                return False
            if o > 126 and not comment:
                return False
    return True


def normalize_shim(text):
    """Only inert text is dropped: trailing SPACE/TAB, blank lines, and comment lines
    matching ^[ \\t]*# after the shebang. Callers must check shim_text_is_clean() first;
    this never strips or translates any other character."""
    lines = text.split("\n")
    out = []
    for i, line in enumerate(lines):
        t = line.rstrip(" \t")
        if not t.strip(" \t"):
            continue
        if i == 0 and t.startswith("#!"):
            out.append(t)
            continue
        if re.match(r"^[ \t]*#", t):
            continue
        out.append(t)
    return "\n".join(out) + "\n"


def known_shim(hook_text):
    """Name of the allowlisted shim this hook is, or None."""
    if not shim_text_is_clean(hook_text):
        return None
    norm = normalize_shim(hook_text)
    for name, good in KNOWN_GOOD_SHIMS.items():
        if norm == normalize_shim(good):
            return name
    return None


def scan_main_calls_compressed(src):
    """AST LINT ONLY -- a fast, readable pre-check, not the proof. (REFUTE 2026-11-08: the
    scan's own docstring mention of 'scan_compressed()' satisfied a regex count.) True only
    when the module defines scan_compressed at top level AND main() contains a call whose
    callee is the bare name scan_compressed. Dead code inside main() would still pass this;
    canary_scan() is what proves the scan actually blocks a compressed credential."""
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


def gate_precondition(worktree_root, hooks_dir, canary=True):
    """(ok, reason). The pre-push hook git will run must be an allowlisted shim (each of
    which runs $ROOT/hooks/<scan> with git's ref lines), this checkout's scan must pass the
    AST lint, and -- the actual proof -- it must block the canary (canary_scan)."""
    pre_push = os.path.join(hooks_dir, "pre-push")
    try:
        # Bytes, decoded latin-1: text mode would translate a lone \r and hide it, and
        # latin-1 keeps every byte >127 visible to shim_text_is_clean().
        with open(pre_push, "rb") as fh:
            hook = fh.read().decode("latin-1")
    except OSError:
        return False, "no pre-push hook at %s -- the push would run ungated" % pre_push
    if known_shim(hook) is None:
        return False, ("pre-push hook at %s is not a known-good shim (KNOWN_GOOD_SHIMS); a changed "
                       "shim must be reviewed and allowlisted before the backup pushes through it" % pre_push)
    scan = os.path.join(worktree_root, SCAN_REL)
    try:
        with open(scan, encoding="utf-8", errors="replace") as fh:
            src = fh.read()
    except OSError:
        return False, "confidential scan missing at %s" % scan
    if not scan_main_calls_compressed(src):
        return False, ("this checkout's %s lacks scan_compressed() (#427 compressed-blob scan); "
                       "merge origin/main into the live branch first" % SCAN_REL.replace(os.sep, "/"))
    if canary:
        ok, why = canary_scan(scan)
        if not ok:
            return False, why
    return True, "ok"


def _canary_secret():
    # Built at runtime so no credential-shaped literal sits in this file (the scan reads
    # this repo's own history). AWS-access-key shape: AKIA + 16 of [0-9A-Z], from a fixed
    # digest so it carries digits (the placeholder suppressor ignores digit-free values).
    import hashlib
    body = hashlib.sha256(b"ora-push-live-backup-canary").hexdigest().upper()[:16]
    return "AKIA" + body


def canary_scan(scan_path, timeout=120):
    """BEHAVIOURAL proof that the scan the shim will run blocks a credential inside a .gz.
    Builds a throwaway repo in TEMP (never the live checkout) with one commit adding
    canary.jsonl.gz whose decompressed text carries a credential-shaped string, then runs
    THIS checkout's scan against that commit as a brand-new remote ref, exactly as git's
    pre-push would feed it. Passes only on a non-zero exit whose output names a COMPRESSED
    finding -- a fail-closed block for another reason (unreadable terms, import failure)
    does not prove the compressed path works, so it fails the canary too. (ok, reason)."""
    import gzip
    import shutil
    import tempfile
    tmp = tempfile.mkdtemp(prefix="plb-canary-")
    try:
        nohooks = os.path.join(tmp, "nohooks")
        repo = os.path.join(tmp, "repo")
        os.makedirs(nohooks)
        env = _env()
        # Hermetic: no global/system git config (hooks paths, templates, aliases) reaches the
        # throwaway repo or the scan's git calls.
        env["GIT_CONFIG_GLOBAL"] = os.devnull
        env["GIT_CONFIG_NOSYSTEM"] = "1"

        def g(*args):
            p = subprocess.run(["git", "-C", repo, "-c", "core.hooksPath=" + nohooks.replace("\\", "/"),
                                "-c", "commit.gpgsign=false", "-c", "user.name=canary",
                                "-c", "user.email=canary@localhost"] + list(args),
                               capture_output=True, text=True, env=env, timeout=60)
            if p.returncode != 0:
                raise RuntimeError("canary git %s: %s" % (args[0], (p.stdout + p.stderr).strip()[-300:]))
            return p.stdout.strip()

        subprocess.run(["git", "init", "-q", repo], check=True, capture_output=True, env=env, timeout=60)
        with open(os.path.join(repo, "README"), "w") as fh:
            fh.write("canary base\n")
        g("add", "-A")
        g("commit", "-q", "-m", "base")
        g("update-ref", "refs/remotes/origin/main", "HEAD")
        with gzip.open(os.path.join(repo, "canary.jsonl.gz"), "wt") as fh:
            fh.write('{"tool":"canary","aws_key_id":"%s"}\n' % _canary_secret())
        g("add", "-A")
        g("commit", "-q", "-m", "canary")
        sha = g("rev-parse", "HEAD")
        stdin = "refs/heads/canary %s %s %s\n" % (sha, TARGET_REF, "0" * 40)
        def scan(stdin_text):
            p = subprocess.run([sys.executable, scan_path, "origin", "canary"], input=stdin_text, cwd=repo,
                               capture_output=True, text=True, env=env, timeout=timeout,
                               encoding="utf-8", errors="replace")
            return p.returncode, (p.stdout or "") + (p.stderr or "")

        # (b) starved stdin: with the opt-in set, zero ref lines must block too (REFUTE r3)
        rc0, out0 = scan("")
        if rc0 == 0:
            return False, ("confidential-scan CANARY FAILED: %s allowed a push with ZERO ref lines under "
                           "%s=1 (exit 0) -- this scan predates the starved-stdin guard: %s"
                           % (scan_path, REQUIRE_REFS_ENV, out0.strip()[-300:]))
        if "zero ref lines" not in out0:
            # Blocked, but for another reason (e.g. terms file unreadable, pattern import
            # failed): fail-closed, yet it proves nothing about the starved-stdin guard.
            return False, ("confidential-scan CANARY FAILED: %s blocked the ZERO-ref-line probe for "
                           "another reason (exit %s), so the starved-stdin guard is unproven: %s"
                           % (scan_path, rc0, out0.strip()[-300:]))
        # (a) a credential inside a .gz on a brand-new remote ref
        rc, out = scan(stdin)
        if rc != 0 and "COMPRESSED" in out:
            return True, "canary blocked"
        return False, ("confidential-scan CANARY FAILED: %s did not block a credential inside a .gz "
                       "(exit %s): %s" % (scan_path, rc, out.strip()[-400:]))
    except subprocess.TimeoutExpired:
        return False, "confidential-scan canary timed out after %ss" % timeout
    except Exception as exc:
        return False, "confidential-scan canary could not run: %s: %s" % (type(exc).__name__, exc)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


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
    # The confidential scan fails closed on ZERO ref lines when this is set (a starved stdin
    # from a malformed shim). Safe here because run_push never invokes `git push` when the
    # remote already holds HEAD, so every push this tool makes carries >=1 ref line.
    env[REQUIRE_REFS_ENV] = "1"
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
    res = {"mode": "push", "repo": a.repo, "remote": a.remote, "branch": BRANCH,
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
            return done("PRECONDITION", "HEAD is detached; refusing to back up an unnamed state as %s" % BRANCH)
        if head_ref != "refs/heads/" + BRANCH:
            return done("PRECONDITION", "HEAD is on %s, not %s; refusing to overwrite the live backup with another branch"
                        % (head_ref, BRANCH))
        sha = _git_ok(a.repo, ["rev-parse", "--verify", "HEAD^{commit}"])
        res["sha"] = sha
        hooks_dir = _git_ok(a.repo, ["rev-parse", "--path-format=absolute", "--git-path", "hooks"])
        ok, why = gate_precondition(top, hooks_dir)
        if not ok:
            return done("PRECONDITION", why)
        expected = remote_ref_sha(a.repo, a.remote, target_ref)
        res["remote_before"] = expected
        if expected == sha:
            # Nothing to push: do NOT invoke git push (git would run pre-push with empty stdin,
            # which the REQUIRE_REFS opt-in deliberately blocks). The ls-remote read IS the
            # verification here.
            return done("UP_TO_DATE")
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
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("allow_abbrev", False)   # no --rep / --che prefix matching
        super().__init__(*args, **kwargs)

    def error(self, message):
        raise _UsageError(message)


def _usage_state_dir(argv):
    """Where a push-mode usage error may write its marker: the --state-dir / --repo this
    argv names (lenient pre-parse), else the default. None for check mode or when even the
    pre-parse fails."""
    pre = _Parser(add_help=False)
    pre.add_argument("--check", action="store_true")
    pre.add_argument("--repo", default=DEFAULT_REPO)
    pre.add_argument("--state-dir", default=None)
    try:
        known, _ = pre.parse_known_args(argv)
    except _UsageError:
        return None
    if known.check:
        return None
    if known.state_dir:
        return os.path.abspath(known.state_dir)
    return os.path.join(os.path.abspath(known.repo), "maintenance", "_state")


def main(argv=None):
    _safe_stdout()
    p = _Parser(description=__doc__.split("\n")[0])
    p.add_argument("--check", action="store_true", help="report whether the live HEAD is off-box")
    p.add_argument("--repo", default=DEFAULT_REPO)
    p.add_argument("--remote", default="origin")
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
        # A mis-typed scheduler prompt must fail loud, not silently: push mode writes the
        # failure marker into the state dir THIS invocation names (pre-parsed --repo /
        # --state-dir), so a usage error under --repo <elsewhere> can never land a marker in
        # the live ~/.claude state. Check mode only reads the marker, so it writes nothing;
        # if even the pre-parse fails, nothing is written (location unknown).
        res = {"verdict": "ERROR", "detail": "usage: %s" % exc}
        where = _usage_state_dir(argv if argv is not None else sys.argv[1:])
        if where:
            res["beacon_written"] = write_beacon(where, False, res)
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
