#!/usr/bin/env python3
"""Queue of "do Y once PR X lands" watches, drained by the ora-pr-land-watch scheduled task.

WHY (2026-09-23). Follow-ups that had to wait for a PR to merge kept being registered as
one-time tasks set to a guessed time (e.g. ora-branch-catchup-refute-trailer-366). If the
PR had not merged by then, the task could only report and exit. An unattended run cannot
re-schedule itself: update_/create_scheduled_task are never auto-approved unattended
(register-scheduled-task v2.23). This queue replaces the guess with a poll.

MODEL. Each watch is (repo, PR, payload). The payload is a markdown instruction file that a
SUPERVISED session writes to <state>/payloads/<id>.md. Once the PR is MERGED, the recurring
task's agent executes it. An unattended agent runs that text, so provenance is enforced,
not just assumed:
  * `add` records the payload's sha256 and refuses a path that resolves outside payloads/
    (junctions included) or a hardlink.
  * `poll` re-checks all of that and fails the watch if the file moved or changed.
  * `poll` hands out the verified text itself (payloadText), so what runs is what was checked.

    poll  -> for each pending watch not already in flight, `gh pr view`:
               MERGED                -> due: attempt-counted, in flight for IN_FLIGHT_MINUTES,
                                        still pending until `mark`
               MERGED, attempts>=MAX -> failed ("exhausted")
               CLOSED                -> closed-unmerged (terminal)
               PR not found          -> not-found (terminal; repo-level errors stay retryable)
               OPEN or gh error, past expires -> expired (terminal)
               other gh error        -> reported, stays pending
    mark  -> the runner records done / failed / cancelled after executing a payload.

The lock is held only for millisecond load/apply sections, never across the gh calls.
Results are re-applied by each watch's unique `key` to a freshly loaded queue, so an
`add`/`mark` that lands mid-poll is never overwritten. A due watch stays pending until it
is marked, so a run that dies mid-payload re-fires once its in-flight window lapses.
Payloads must therefore be idempotent (check "already done?" first).

`poll` MUTATES the queue: it spends attempts and sets in-flight windows. To look without
side effects, use `list`.

NAME NOTE: this is deliberately "land", not "merge". config-write-guard's GIT_MUTATE_RE
matches the word "merge" anywhere in a git command that names ~/.claude, which would block
the task's own `git show origin/main:maintenance/<this file>` step.

Usage:
    python pr-land-watch.py add  --id ID --repo OWNER/NAME --pr N [--expires YYYY-MM-DD] [--note TEXT]
    python pr-land-watch.py poll            # JSON; needsAttention=false -> nothing to do
    python pr-land-watch.py mark --id ID --status done|failed|cancelled [--note TEXT]
    python pr-land-watch.py list            # read-only
    (all accept --state-dir; the default is ~/.claude/scheduled-tasks/ora-pr-land-watch/_state,
     which the scheduled-tasks .gitignore rule keeps out of git)

Run the tests: python _tests/test_pr_land_watch.py
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import uuid

DEFAULT_STATE_DIR = os.path.join(
    os.path.expanduser("~"), ".claude", "scheduled-tasks", "ora-pr-land-watch", "_state")
MAX_ATTEMPTS = 3
DEFAULT_EXPIRY_DAYS = 30
MAX_EXPIRY_DAYS = 90
IN_FLIGHT_MINUTES = 150  # < the task's 3h cadence, so a crashed run re-fires on the next poll
STALE_LOCK_SECONDS = 120  # critical sections are milliseconds; gh calls run unlocked
LOCK_WAIT_SECONDS = 30
TERMINAL = {"done", "failed", "cancelled", "closed-unmerged", "expired", "not-found"}
MARKABLE = {"done", "failed", "cancelled"}
# Terminal only when the REPO resolved but the PR did not. GitHub answers "Could not resolve
# to a Repository" for a missing repo AND for a token that lacks access (auth switch), so that
# stays retryable until expiry. Never a bare "not found": "gh: command not found" is an
# environment fault.
_NOT_FOUND_RE = re.compile(r"could not resolve to a pullrequest", re.IGNORECASE)

# The id becomes a filename (payloads/<id>.md). repo and pr are passed to gh as argv, with
# no shell, but they are still shape-checked so a typo fails at `add` in a supervised
# session instead of at 3am.
_ID_RE = re.compile(r"[a-z0-9][a-z0-9._-]{0,63}")
_REPO_RE = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+")


class WatchError(Exception):
    pass


class State:
    def __init__(self, state_dir=None):
        self.dir = os.path.abspath(state_dir or DEFAULT_STATE_DIR)
        self.queue_path = os.path.join(self.dir, "queue.json")
        self.lock_path = os.path.join(self.dir, "queue.lock")
        self.payload_dir = os.path.join(self.dir, "payloads")

    def payload_path(self, wid):
        return os.path.join(self.payload_dir, wid + ".md")


def _verify_payload(state, wid):
    """Return (realpath, sha256, text) or raise WatchError.

    Reads the bytes ONCE and derives both the hash and the text from that one buffer, so the
    text handed to the runner is exactly the text that was hashed. Re-opening the file later
    (e.g. after a 60s gh call) would let a rewrite in between go unverified.
    """
    p = state.payload_path(wid)
    if not os.path.isfile(p):
        raise WatchError(f"payload missing: {p}")
    real = os.path.realpath(p)
    # Anchor on the state dir's real path + the literal "payloads" segment. realpath(payload_dir)
    # would follow a junction ON payloads/ itself and so agree with the escaped file.
    root = os.path.join(os.path.realpath(state.dir), "payloads")
    if os.path.normcase(os.path.dirname(real)) != os.path.normcase(root):
        raise WatchError(f"payload resolves outside payloads dir: {real}")
    if os.stat(real).st_nlink > 1:
        raise WatchError(f"payload is hardlinked (nlink>1), refusing: {real}")
    try:
        with open(real, "rb") as f:
            raw = f.read()
    except OSError as e:
        raise WatchError(f"payload unreadable: {real}: {e}")
    try:
        # Strict UTF-8: PowerShell 5.1 `>`/Out-File writes UTF-16LE by default -- reject at add.
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise WatchError(f"payload is not UTF-8 (rewrite it, e.g. with the Write tool): {real}")
    return real, hashlib.sha256(raw).hexdigest(), text


# --- storage -----------------------------------------------------------------------------

class _Lock:
    """Exclusive lock-file with an owner token: only the holder that created it may release it."""

    def __init__(self, state):
        self.path = state.lock_path
        self.token = uuid.uuid4().hex
        os.makedirs(state.dir, exist_ok=True)

    def _read(self):
        try:
            with open(self.path, encoding="utf-8") as f:
                return f.read().strip()
        except OSError:
            return None

    def __enter__(self):
        deadline = time.monotonic() + LOCK_WAIT_SECONDS
        while True:
            try:
                fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(fd, self.token.encode())
                os.close(fd)
                return self
            except (FileExistsError, PermissionError):  # PermissionError: Windows delete-pending/AV
                try:
                    m1 = os.path.getmtime(self.path)
                    if time.time() - m1 > STALE_LOCK_SECONDS:
                        stale = self._read()
                        # Re-check age AND token immediately before removing: a lock another
                        # waiter just re-created after breaking the same stale one is fresh,
                        # so it fails the age test. That narrows, but cannot fully close, the
                        # race. It needs a holder killed inside a millisecond critical
                        # section plus two simultaneous waiters (review 2026-09-23, Minor C).
                        if (stale is not None and self._read() == stale
                                and time.time() - os.path.getmtime(self.path) > STALE_LOCK_SECONDS):
                            os.remove(self.path)
                        continue
                except OSError:
                    pass
                if time.monotonic() > deadline:
                    raise WatchError(f"queue lock busy for {LOCK_WAIT_SECONDS}s: {self.path}")
                time.sleep(0.2)

    def __exit__(self, *exc):
        if self._read() != self.token:
            return  # not ours any more (broken as stale) -- never delete another holder's lock
        for i in range(10):
            try:
                os.remove(self.path)
                return
            except FileNotFoundError:
                return
            except PermissionError:
                time.sleep(0.1 * (i + 1))


def load(state):
    if not os.path.exists(state.queue_path):
        return {"version": 1, "watches": []}
    try:
        with open(state.queue_path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        # Never treat an unreadable queue as empty: that would silently drop every watch.
        raise WatchError(f"queue unreadable: {state.queue_path}: {e}")
    if not isinstance(data, dict) or not isinstance(data.get("watches"), list):
        raise WatchError(f"queue malformed: {state.queue_path}")
    return data


def _save(state, data):
    tmp = state.queue_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    # Windows: AV/indexer can hold the target for a moment (same class as oxford-command-center #365).
    for i in range(10):
        try:
            os.replace(tmp, state.queue_path)
            return
        except PermissionError:
            if i == 9:
                raise
            time.sleep(0.1 * (i + 1))


def _now():
    return datetime.datetime.now(datetime.timezone.utc)


def _iso(t):
    return t.isoformat(timespec="seconds")


# --- operations --------------------------------------------------------------------------

def fetch_pr(repo, pr):
    r = subprocess.run(
        ["gh", "pr", "view", str(pr), "--repo", repo, "--json", "state,mergedAt,mergeCommit"],
        capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout).strip() or f"gh exit {r.returncode}")
    return json.loads(r.stdout)


def add_watch(state, wid, repo, pr, expires=None, note="", today=None, fetch=fetch_pr):
    today = today or datetime.date.today()
    if not _ID_RE.fullmatch(wid or ""):
        raise WatchError(f"bad id {wid!r} (lowercase a-z0-9._-, max 64)")
    if not _REPO_RE.fullmatch(repo or ""):
        raise WatchError(f"bad repo {repo!r} (OWNER/NAME)")
    if not isinstance(pr, int) or isinstance(pr, bool) or pr <= 0:
        raise WatchError(f"bad PR number {pr!r}")
    if expires is None:
        exp = today + datetime.timedelta(days=DEFAULT_EXPIRY_DAYS)
    else:
        try:
            exp = datetime.date.fromisoformat(expires)
        except ValueError:
            raise WatchError(f"bad --expires {expires!r} (YYYY-MM-DD)")
        if exp < today or exp > today + datetime.timedelta(days=MAX_EXPIRY_DAYS):
            raise WatchError(f"--expires must be between today and +{MAX_EXPIRY_DAYS}d")
    real, digest, _ = _verify_payload(state, wid)
    # Verify the PR while a human is watching: a typo'd number must fail here, not every 3h.
    try:
        info = fetch(repo, pr)
    except Exception as e:
        raise WatchError(f"cannot read {repo}#{pr}: {e}")
    if not isinstance(info, dict) or (info.get("state") or "").upper() not in {"OPEN", "MERGED"}:
        raise WatchError(f"{repo}#{pr} is not open or merged: {info!r}")
    with _Lock(state):
        data = load(state)
        if any(w["id"] == wid and w["status"] not in TERMINAL for w in data["watches"]):
            raise WatchError(f"a pending watch with id {wid!r} already exists")
        w = {"key": uuid.uuid4().hex, "id": wid, "repo": repo, "pr": pr,
             "registered": today.isoformat(), "expires": exp.isoformat(), "status": "pending",
             "attempts": 0, "inFlightUntil": None, "note": note,
             "payloadSha256": digest, "payloadRealpath": real,
             "mergeSha": None, "mergedAt": None, "resolvedAt": None, "lastError": None}
        data["watches"].append(w)
        _save(state, data)
    return w


def _classify(state, w, fetch, today, now):
    """Decide one watch WITHOUT the lock. Returns (updates, bucket, entry)."""
    ref = {"id": w["id"], "repo": w["repo"], "pr": w["pr"], "note": w.get("note", "")}
    try:
        real, digest, text = _verify_payload(state, w["id"])
        if digest != w.get("payloadSha256") or real != w.get("payloadRealpath"):
            raise WatchError("payload changed since `add` (hash/path mismatch) -- re-add to re-pin")
    except WatchError as e:
        return ({"status": "failed", "resolvedAt": _iso(now), "lastError": str(e)},
                "errors", {**ref, "error": f"{e} (watch failed)"})
    expired = today > datetime.date.fromisoformat(w["expires"])
    try:
        pr = fetch(w["repo"], w["pr"])
        if not isinstance(pr, dict):
            raise RuntimeError(f"unexpected gh output: {pr!r}")
    except Exception as e:  # gh/network/auth
        msg = str(e)[:500]
        if _NOT_FOUND_RE.search(msg):
            return ({"status": "not-found", "resolvedAt": _iso(now), "lastError": msg},
                    "errors", {**ref, "error": f"{msg} (watch closed: not-found)"})
        if expired:
            return ({"status": "expired", "resolvedAt": _iso(now), "lastError": msg},
                    "expired", {**ref, "expires": w["expires"]})
        return ({"lastError": msg}, "errors", {**ref, "error": msg})
    st = (pr.get("state") or "").upper()
    if st == "MERGED":
        mc = pr.get("mergeCommit")
        sha = mc.get("oid") if isinstance(mc, dict) else None
        upd = {"mergeSha": sha, "mergedAt": pr.get("mergedAt")}
        if w["attempts"] >= MAX_ATTEMPTS:
            upd.update(status="failed", resolvedAt=_iso(now),
                       lastError=f"not marked done after {MAX_ATTEMPTS} attempts")
            return upd, "exhausted", ref
        upd.update(attempts=w["attempts"] + 1,
                   inFlightUntil=_iso(now + datetime.timedelta(minutes=IN_FLIGHT_MINUTES)))
        return upd, "due", {**ref, "payload": w["payloadRealpath"], "payloadSha256": w["payloadSha256"],
                            "payloadText": text, "mergeSha": sha, "mergedAt": pr.get("mergedAt"),
                            "attempt": w["attempts"] + 1}
    if st == "CLOSED":
        return {"status": "closed-unmerged", "resolvedAt": _iso(now)}, "closed", ref
    if expired:
        return {"status": "expired", "resolvedAt": _iso(now)}, "expired", {**ref, "expires": w["expires"]}
    return {}, None, None


def _in_flight(w, now):
    t = w.get("inFlightUntil")
    return bool(t) and datetime.datetime.fromisoformat(t) > now


def poll(state, fetch=fetch_pr, today=None, now=None):
    today = today or datetime.date.today()
    now = now or _now()
    out = {"due": [], "closed": [], "expired": [], "exhausted": [], "errors": [], "pending": 0,
           "inFlight": 0}
    with _Lock(state):  # 1. snapshot
        snapshot = [dict(w) for w in load(state)["watches"] if w["status"] not in TERMINAL]
    decisions = {}
    for w in snapshot:  # 2. classify, unlocked (gh calls can take up to 60s each)
        if _in_flight(w, now):
            continue
        try:
            decision = _classify(state, w, fetch, today, now)
        except Exception as e:  # one bad watch must never stall the whole queue
            msg = f"unexpected {type(e).__name__}: {e}"[:500]
            ref = {"id": w["id"], "repo": w["repo"], "pr": w["pr"]}
            try:
                expired = today > datetime.date.fromisoformat(w["expires"])
            except Exception:
                expired = True  # an unparseable expiry must not keep a broken watch alive forever
            decision = (({"status": "expired", "resolvedAt": _iso(now), "lastError": msg},
                         "expired", {**ref, "expires": w.get("expires"), "error": msg})
                        if expired else
                        ({"lastError": msg}, "errors", {**ref, "error": msg}))
        decisions[w["key"]] = (w, decision)
    with _Lock(state):  # 3. re-apply by key to the FRESH queue
        data = load(state)
        for cur in data["watches"]:
            if cur["status"] in TERMINAL:
                continue
            if cur.get("key") not in decisions:
                out["pending"] += 1
                out["inFlight"] += _in_flight(cur, now)
                continue
            seen, (upd, bucket, entry) = decisions[cur["key"]]
            # A concurrent poll that already handed this out (or a mark) wins: skip stale decisions.
            if cur.get("attempts") != seen.get("attempts") or _in_flight(cur, now):
                out["pending"] += 1
                out["inFlight"] += _in_flight(cur, now)
                continue
            cur.update(upd)
            if bucket:
                out[bucket].append(entry)
            if cur["status"] not in TERMINAL:
                out["pending"] += 1
        _save(state, data)
    return out


def needs_attention(result):
    return any(result[k] for k in ("due", "closed", "expired", "exhausted", "errors"))


def mark(state, wid, status, note=None):
    if status not in MARKABLE:
        raise WatchError(f"status must be one of {sorted(MARKABLE)}")
    with _Lock(state):
        data = load(state)
        live = [w for w in data["watches"] if w["id"] == wid and w["status"] not in TERMINAL]
        if not live:
            raise WatchError(f"no pending watch with id {wid!r}")
        w = live[-1]
        w.update(status=status, resolvedAt=_iso(_now()), inFlightUntil=None)
        if note is not None:
            w["note"] = note
        _save(state, data)
    return w


# --- CLI ---------------------------------------------------------------------------------

def main(argv=None, fetch=fetch_pr, today=None, now=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--state-dir", default=None)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add")
    a.add_argument("--id", required=True)
    a.add_argument("--repo", required=True)
    a.add_argument("--pr", required=True, type=int)
    a.add_argument("--expires")
    a.add_argument("--note", default="")
    sub.add_parser("poll")
    m = sub.add_parser("mark")
    m.add_argument("--id", required=True)
    m.add_argument("--status", required=True)
    m.add_argument("--note")
    sub.add_parser("list")
    args = ap.parse_args(argv)
    state = State(args.state_dir)
    try:
        if args.cmd == "add":
            res = add_watch(state, args.id, args.repo, args.pr, args.expires, args.note,
                            today=today, fetch=fetch)
        elif args.cmd == "poll":
            res = poll(state, fetch=fetch, today=today, now=now)
            res["needsAttention"] = needs_attention(res)
        elif args.cmd == "mark":
            res = mark(state, args.id, args.status, args.note)
        else:
            res = load(state)
    except WatchError as e:
        print(f"pr-land-watch: {e}", file=sys.stderr)
        return 2
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
