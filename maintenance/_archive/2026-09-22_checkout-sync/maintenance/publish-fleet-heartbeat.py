#!/usr/bin/env python3
"""Publish the fleet heartbeat to GitHub for the external dead-man (OI-323).

WHY THIS EXISTS: the dead-man workflow (.github/workflows/fleet-deadman.yml) can only see
what is on GitHub. push-fleet-heartbeat.ps1 used to get the heartbeat there by running
`git push origin main`, which carries every pending commit and so runs the full pre-push
gate (about 12 minutes). Unrelated failing hook tests and a remote `main` that moved during
the gate kept the one-line heartbeat off GitHub for days, and the script exited 0 anyway.

This writes ONLY the heartbeat JSON, to a dedicated `deadman-heartbeat` branch, through the
GitHub API. No git push, no gate, no race with `main`. Each run builds a fresh ORPHAN commit
and points the branch at it (force), so there is no sha race and the branch never grows.

Two local state files, both next to the other maintenance state (NOT next to this script, so a
run from a worktree cannot write state the watchdog never reads):
  heartbeat-publish-failed.json  written on a failed publish, removed on the next success
  heartbeat-publish-ok.json      written on every success
--status exits 1 when the marker exists OR the ok-stamp is missing/older than STAMP_MAX_AGE_H.
A missing marker alone is NOT success: a task that never ran leaves no marker either.

Usage:
  publish-fleet-heartbeat.py            build the payload, publish it (exit 0 ok / 2 failed)
  publish-fleet-heartbeat.py --status   exit 1 if the last publish failed or none is recent

ASCII-only output (Task Scheduler / PS 5.1).
"""
import base64
import datetime
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import time
from collections import namedtuple

HERE = os.path.dirname(os.path.abspath(__file__))
STATE_DIR = os.path.join(os.path.expanduser("~"), ".claude", "maintenance", "_state")
MARKER = os.path.join(STATE_DIR, "heartbeat-publish-failed.json")
STAMP = os.path.join(STATE_DIR, "heartbeat-publish-ok.json")
REPO = "ZeOoba/ora-claude-config"
BRANCH = "deadman-heartbeat"
PATH = "fleet-heartbeat.json"
GH_FALLBACK = r"C:\Program Files\GitHub CLI\gh.exe"
DELAYS = (2, 8, 20)
GH_TIMEOUT_S = 30
DEADLINE_S = 150  # no NEW attempt starts past this; one attempt can still take up to 5 calls x GH_TIMEOUT_S
STAMP_MAX_AGE_H = 26
Result = namedtuple("Result", "ok attempts reason")


class GhMissing(Exception):
    pass


def run_gh(argv, input_text=None):
    gh = shutil.which("gh") or (GH_FALLBACK if os.path.exists(GH_FALLBACK) else None)
    if not gh:
        raise GhMissing("gh CLI not found on PATH or at %s" % GH_FALLBACK)
    try:
        p = subprocess.run([gh] + argv, input=input_text.encode("utf-8") if input_text else None,
                           capture_output=True, timeout=GH_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        return 124, "", "gh timed out after %ds" % GH_TIMEOUT_S
    return (p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace"))


def parse_response(rc, out, err):
    """(status, body) from `gh api -i` output. status None = no HTTP response (network)."""
    m = re.match(r"HTTP/\S+\s+(\d{3})", out or "")
    if not m:
        return None, {}
    parts = re.split(r"\r?\n\r?\n", out, maxsplit=1)
    text = parts[1] if len(parts) > 1 else ""
    try:
        body = json.loads(text) if text.strip() else {}
    except ValueError:
        body = {}
    return int(m.group(1)), body


def _call(runner, method, rel, body=None):
    argv = ["api", "-i", "-X", method, "repos/%s/%s" % (REPO, rel)]
    text = None
    if body is not None:
        argv += ["--input", "-"]
        text = json.dumps(body)
    rc, out, err = runner(argv, text)
    status, data = parse_response(rc, out, err)
    return status, data, err


def _retryable(status):
    return status is None or status >= 500 or status in (409, 422, 429)


def _attempt(runner, b64, message):
    """One full publish: orphan commit, then create or force-move the branch ref to it."""
    status, data, err = _call(runner, "GET", "git/ref/heads/%s" % BRANCH)
    if status not in (200, 404):
        return False, status, err
    exists = status == 200
    status, data, err = _call(runner, "POST", "git/blobs", {"content": b64, "encoding": "base64"})
    if status != 201 or not data.get("sha"):
        return False, status, err or "blob response carried no sha"
    status, data, err = _call(runner, "POST", "git/trees", {
        "tree": [{"path": PATH, "mode": "100644", "type": "blob", "sha": data["sha"]}]})
    if status != 201 or not data.get("sha"):
        return False, status, err or "tree response carried no sha"
    status, data, err = _call(runner, "POST", "git/commits", {
        "message": message, "tree": data["sha"], "parents": []})
    if status != 201 or not data.get("sha"):
        return False, status, err or "commit response carried no sha"
    commit = data["sha"]
    if exists:
        status, data, err = _call(runner, "PATCH", "git/refs/heads/%s" % BRANCH,
                                  {"sha": commit, "force": True})
        return status == 200, status, err
    status, data, err = _call(runner, "POST", "git/refs",
                              {"ref": "refs/heads/%s" % BRANCH, "sha": commit})
    return status == 201, status, err


def _write_json(path, obj):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=1)
            f.write("\n")
        os.replace(tmp, path)
        return True
    except OSError as e:
        print("heartbeat publish WARNING: could not write %s (%s)" % (path, e))
        return False


def _utc(now=None):
    return (now or datetime.datetime.now(datetime.timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ")


def write_marker(reason, attempts, last_error, marker_path=MARKER, now=None):
    return _write_json(marker_path, {"ts": _utc(now), "reason": reason,
                                     "attempts": attempts, "last_error": last_error})


def clear_marker(marker_path=MARKER):
    try:
        os.remove(marker_path)
    except OSError:
        pass


def publish(payload, runner=run_gh, sleep=time.sleep, attempts=4, delays=DELAYS,
            marker_path=MARKER, stamp_path=STAMP, clock=time.monotonic, deadline=DEADLINE_S, now=None):
    data = (json.dumps(payload, indent=1) + "\n").encode("utf-8")
    b64 = base64.b64encode(data).decode("ascii")
    message = "chore(deadman): heartbeat %s" % payload.get("ts")
    reason, last_error, i, start = "", "", 0, clock()
    for i in range(1, attempts + 1):
        unexpected = False
        try:
            ok, status, err = _attempt(runner, b64, message)
        except GhMissing as e:
            reason, last_error = str(e), str(e)
            break
        except Exception as e:  # anything else (spawn failure, malformed response) must still leave a marker
            ok, status, err, unexpected = False, None, "unexpected error: %r" % (e,), True
        if ok:
            clear_marker(marker_path)
            _write_json(stamp_path, {"ts": _utc(now), "attempts": i, "payload_ts": payload.get("ts")})
            return Result(True, i, "")
        last_error = (err or "").strip()[:300]
        if status:
            reason = "HTTP %d from GitHub API" % status
        else:
            reason = "unexpected error" if unexpected else "network error (no HTTP response)"
        if not _retryable(status) or i == attempts:
            break
        if clock() - start > deadline:
            reason += " (gave up after %ds wall-clock)" % deadline
            break
        sleep(delays[min(i - 1, len(delays) - 1)])
    write_marker(reason, i, last_error, marker_path, now)
    return Result(False, i, reason)


def build_payload():
    spec = importlib.util.spec_from_file_location(
        "efh", os.path.join(HERE, "emit-fleet-heartbeat.py"))
    efh = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(efh)
    return efh.build_heartbeat({label: efh.discover(store) for label, store in efh.FLEET_STORES})


def status(marker_path=MARKER, stamp_path=STAMP, now=None):
    """(exit_code, message). 1 = marker present, or no recent successful publish on record."""
    now = now or datetime.datetime.now(datetime.timezone.utc)
    if os.path.exists(marker_path):
        try:
            with open(marker_path, encoding="utf-8") as f:
                mk = json.load(f)
        except (OSError, ValueError):
            mk = {}
        return 1, "heartbeat publish FAILED since %s: %s" % (mk.get("ts", "?"), mk.get("reason", "?"))
    try:
        with open(stamp_path, encoding="utf-8") as f:
            ts = datetime.datetime.strptime(json.load(f)["ts"], "%Y-%m-%dT%H:%M:%SZ").replace(
                tzinfo=datetime.timezone.utc)
    except (OSError, ValueError, KeyError, TypeError):
        return 1, "heartbeat publish: NO successful publish on record (never ran, or state unreadable)"
    age_h = (now - ts).total_seconds() / 3600
    if age_h < -1:
        return 1, "heartbeat publish: last success is dated %.1fh in the FUTURE (clock skew?)" % -age_h
    if age_h > STAMP_MAX_AGE_H:
        return 1, "heartbeat publish: last SUCCESS was %.1fh ago (max %dh) - the publish is not running" % (
            age_h, STAMP_MAX_AGE_H)
    return 0, "heartbeat publish: OK (last success %.1fh ago)" % age_h


def main(argv=None, runner=run_gh, build_fn=build_payload, sleep=time.sleep,
         marker_path=MARKER, stamp_path=STAMP, clock=time.monotonic, now=None):
    argv = sys.argv[1:] if argv is None else argv
    if "--status" in argv:
        code, msg = status(marker_path, stamp_path, now)
        print(msg)
        return code
    try:
        payload = build_fn()
    except Exception as e:  # the emitter must never take the publish path down silently
        reason = "payload build failed: %r" % (e,)
        write_marker(reason, 0, reason, marker_path, now)
        print("heartbeat publish FAILED: %s" % reason)
        return 2
    try:
        res = publish(payload, runner=runner, sleep=sleep, marker_path=marker_path,
                      stamp_path=stamp_path, clock=clock, now=now)
    except Exception as e:  # last resort: never exit with a traceback and no marker
        reason = "publish crashed: %r" % (e,)
        write_marker(reason, 0, reason, marker_path, now)
        print("heartbeat publish FAILED: %s" % reason)
        return 2
    if res.ok:
        print("heartbeat publish OK: %s -> %s:%s (attempt %d)" % (payload.get("ts"), REPO, BRANCH, res.attempts))
        return 0
    print("heartbeat publish FAILED after %d attempt(s): %s" % (res.attempts, res.reason))
    return 2


if __name__ == "__main__":
    sys.exit(main())
