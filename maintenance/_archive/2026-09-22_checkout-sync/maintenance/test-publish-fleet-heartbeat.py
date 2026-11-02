#!/usr/bin/env python3
"""Tests for publish-fleet-heartbeat.py -- the dead-man's heartbeat publish leg (OI-323).

The publish must not depend on the wide gated `git push`: it writes ONLY the heartbeat JSON
to a dedicated branch through the GitHub API, as a fresh orphan commit each run. Covered
against a fake GitHub (refs, blobs, trees, commits) that RECORDS any write outside the
deadman-heartbeat ref: first-run branch creation, update by force-move, transient 5xx, a
ref-create race, persistent network failure, non-retryable auth failure, the wall-clock cap,
marker + ok-stamp semantics (a missing marker is NOT success), an unwritable state dir, the
real payload builder, and the --status / exit-code contract Task Scheduler and the local
watchdog depend on.

Run: python test-publish-fleet-heartbeat.py   (exit 0 = all pass)
"""
import base64
import contextlib
import datetime
import importlib.util
import io
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "pfh", os.path.join(HERE, "publish-fleet-heartbeat.py"))
pfh = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pfh)

results = []


def expect(label, cond, detail=""):
    results.append((bool(cond), label))
    if not cond:
        print("  FAIL: %s %s" % (label, detail))


REPO, BRANCH, PATH = pfh.REPO, pfh.BRANCH, pfh.PATH
API = "repos/%s/" % REPO
REF = "refs/heads/%s" % BRANCH
UTC = datetime.timezone.utc
NOW = datetime.datetime(2026, 9, 21, 11, 30, 0, tzinfo=UTC)
PAYLOAD = {"ts": "2026-09-21T11:30:00Z", "probe_version": "t",
           "fleets": {"cc": 38, "lams": 27},
           "registries": {"cc": {"path": "p", "exists": True, "sha256": "a"},
                          "lams": {"path": "q", "exists": True, "sha256": "b"}}}


class FakeGitHub:
    """Enough of the GitHub git-data API for the publish flow. `faults` is consumed one entry per
    call: None = behave, int = that HTTP status, 'net' = network failure. Any write to a ref other
    than deadman-heartbeat, and any use of the contents API, is recorded in `violations`."""

    def __init__(self, branch_exists=False, faults=None, race_on_create=False):
        self.refs = {"refs/heads/main": "main0"}
        self.blobs, self.trees, self.commits = {}, {}, {}
        if branch_exists:
            self.blobs["oldblob"] = b"old\n"
            self.trees["oldtree"] = "oldblob"
            self.commits["c0"] = {"tree": "oldtree", "parents": []}
            self.refs[REF] = "c0"
        self.faults = list(faults or [])
        self.race_on_create = race_on_create
        self.calls, self.bodies, self.violations = [], [], []
        self.n = 0

    def _resp(self, status, body):
        line = {200: "OK", 201: "Created", 404: "Not Found", 409: "Conflict", 422: "Unprocessable",
                401: "Unauthorized", 502: "Bad Gateway"}.get(status, "X")
        rc = 0 if status < 400 else 1
        err = "" if rc == 0 else "gh: %s (HTTP %d)" % (line, status)
        return rc, "HTTP/2.0 %d %s\nContent-Type: application/json\n\n%s" % (status, line, json.dumps(body)), err

    def branch_content(self):
        c = self.refs.get(REF)
        return self.blobs[self.trees[self.commits[c]["tree"]]] if c else None

    def __call__(self, argv, input_text=None):
        self.calls.append(argv)
        if self.faults:
            f = self.faults.pop(0)
            if f == "net":
                return 1, "", "error connecting to api.github.com"
            if f is not None:
                return self._resp(f, {"message": "injected"})
        method = argv[argv.index("-X") + 1]
        if method in ("POST", "PATCH") and not (
                "--input" in argv and argv[argv.index("--input") + 1] == "-"
                and not any(a in argv for a in ("-f", "-F", "--field", "--raw-field"))):
            self.violations.append("body not sent as JSON on stdin (--input -): %r" % (argv,))
        rel = [a for a in argv if a.startswith("repos/")][0][len(API):]
        body = json.loads(input_text) if input_text else {}
        self.bodies.append((method, rel, body))
        self.n += 1
        if rel.startswith("contents/"):
            self.violations.append("contents API used: %s %s" % (method, rel))
            return self._resp(404, {})
        if rel.startswith("git/ref/heads/") and method == "GET":
            name = "refs/heads/" + rel[len("git/ref/heads/"):]
            r = self._resp(200, {"object": {"sha": self.refs[name]}}) if name in self.refs else self._resp(404, {})
            if self.race_on_create and name == REF and name not in self.refs:
                self.blobs["raceblob"] = b"other\n"
                self.trees["racetree"] = "raceblob"
                self.commits["race"] = {"tree": "racetree", "parents": []}
                self.refs[REF] = "race"  # someone else creates it right after our GET
                self.race_on_create = False
            return r
        if rel == "git/blobs":
            sha = "blob%d" % self.n
            self.blobs[sha] = base64.b64decode(body["content"])
            return self._resp(201, {"sha": sha})
        if rel == "git/trees":
            assert body["tree"][0]["path"] == PATH, body
            sha = "tree%d" % self.n
            self.trees[sha] = body["tree"][0]["sha"]
            return self._resp(201, {"sha": sha})
        if rel == "git/commits":
            sha = "commit%d" % self.n
            self.commits[sha] = {"tree": body["tree"], "parents": body["parents"]}
            return self._resp(201, {"sha": sha})
        if rel == "git/refs" and method == "POST":
            if body["ref"] != REF:
                self.violations.append("POST ref %s" % body["ref"])
            if body["ref"] in self.refs:
                return self._resp(422, {"message": "Reference already exists"})
            self.refs[body["ref"]] = body["sha"]
            return self._resp(201, {})
        if rel.startswith("git/refs/heads/") and method == "PATCH":
            name = "refs/heads/" + rel[len("git/refs/heads/"):]
            if name != REF:
                self.violations.append("PATCH ref %s" % name)
            if name not in self.refs:
                return self._resp(404, {})
            if not body.get("force"):
                return self._resp(422, {"message": "not a fast-forward"})
            self.refs[name] = body["sha"]
            return self._resp(200, {})
        self.violations.append("unrouted %s %s" % (method, rel))
        return self._resp(404, {})


def tmp(name="m.json"):
    return os.path.join(tempfile.mkdtemp(), name)


def run(gh, marker=None, stamp=None, attempts=4, clock=None):
    sleeps = []
    m, s = marker or tmp("marker.json"), stamp or tmp("stamp.json")
    kw = {"clock": clock} if clock else {}
    res = pfh.publish(PAYLOAD, runner=gh, sleep=sleeps.append, attempts=attempts,
                      delays=(2, 8, 20), marker_path=m, stamp_path=s, now=NOW, **kw)
    return res, sleeps, m, s


def clean(gh, label):
    expect("%s: nothing written outside deadman-heartbeat, contents API unused" % label,
           gh.violations == [] and gh.refs["refs/heads/main"] == "main0", repr(gh.violations))


# --- response parsing -----------------------------------------------------------------------
st, body = pfh.parse_response(0, "HTTP/2.0 200 OK\nX: y\n\n{\"a\": 1}", "")
expect("parse: 200 status + body", st == 200 and body == {"a": 1}, repr((st, body)))
st, body = pfh.parse_response(1, "HTTP/2.0 404 Not Found\nX: y\n\n{\"message\": \"Not Found\"}", "gh: Not Found (HTTP 404)")
expect("parse: 404 status", st == 404, repr(st))
st, body = pfh.parse_response(1, "", "error connecting to api.github.com")
expect("parse: network failure -> status None", st is None and body == {}, repr((st, body)))
st, body = pfh.parse_response(0, "HTTP/2.0 200 OK\r\nX: y\r\n\r\n{\"a\": 2}", "")
expect("parse: CRLF headers", st == 200 and body == {"a": 2}, repr((st, body)))

# --- first run: branch missing ----------------------------------------------------------------
gh = FakeGitHub(branch_exists=False)
res, sleeps, m, s = run(gh)
expect("first run: ok, branch created with payload", res.ok and json.loads(gh.branch_content()) == PAYLOAD, repr(res))
expect("first run: orphan commit (no parents)", gh.commits[gh.refs[REF]]["parents"] == [])
expect("first run: no sleeps", sleeps == [])
expect("first run: ref created by POST to refs/heads/deadman-heartbeat",
       ("POST", "git/refs", {"ref": REF, "sha": gh.refs[REF]}) in gh.bodies)
clean(gh, "first run")

# --- update: branch exists -> force-move to a fresh orphan commit -----------------------------------
gh = FakeGitHub(branch_exists=True)
res, sleeps, m, s = run(gh)
expect("update: ok, content replaced", res.ok and json.loads(gh.branch_content()) == PAYLOAD, repr(res))
expect("update: new orphan commit, history does not grow", gh.commits[gh.refs[REF]]["parents"] == [])
expect("update: ref moved with force via PATCH",
       ("PATCH", "git/refs/heads/%s" % BRANCH, {"sha": gh.refs[REF], "force": True}) in gh.bodies)
clean(gh, "update")

# --- transient 5xx then success ---------------------------------------------------------------
gh = FakeGitHub(branch_exists=True, faults=[502])
res, sleeps, m, s = run(gh)
expect("transient 502: recovers", res.ok and res.attempts == 2, repr(res))
expect("transient 502: backoff used", sleeps == [2], repr(sleeps))
clean(gh, "transient")

# --- ref-create race: someone creates the branch between our GET and POST -----------------------------
gh = FakeGitHub(branch_exists=False, race_on_create=True)
res, sleeps, m, s = run(gh)
expect("create race (422 already exists): recovers via the update path",
       res.ok and res.attempts == 2 and json.loads(gh.branch_content()) == PAYLOAD, repr(res))
clean(gh, "race")

# --- persistent network failure ----------------------------------------------------------------
gh = FakeGitHub(branch_exists=True, faults=["net"] * 40)
res, sleeps, m, s = run(gh)
expect("net down: fails after all attempts", (not res.ok) and res.attempts == 4, repr(res))
expect("net down: backed off between attempts only", sleeps == [2, 8, 20], repr(sleeps))
expect("net down: marker written, no ok-stamp", os.path.exists(m) and not os.path.exists(s))
mk = json.load(open(m, encoding="utf-8"))
expect("marker: ts/reason/attempts/last_error",
       all(k in mk for k in ("ts", "reason", "attempts", "last_error")) and mk["attempts"] == 4, repr(mk))
clean(gh, "net down")

# --- non-retryable auth failure ------------------------------------------------------------------
gh = FakeGitHub(branch_exists=True, faults=[401] * 10)
res, sleeps, m, s = run(gh)
expect("401: fails fast, no retry", (not res.ok) and res.attempts == 1 and sleeps == [], repr((res, sleeps)))
expect("401: reason names the status", "401" in res.reason, res.reason)

# --- wall-clock cap ------------------------------------------------------------------------------------
gh = FakeGitHub(branch_exists=True, faults=["net"] * 40)
ticks = iter([0, 200, 400, 600])
res, sleeps, m, s = run(gh, clock=lambda: next(ticks))
expect("deadline: stops retrying past the wall-clock cap", (not res.ok) and res.attempts == 1 and sleeps == [], repr((res, sleeps)))
expect("deadline: reason says so", "wall-clock" in res.reason, res.reason)

# --- success clears a stale marker and writes the ok-stamp ------------------------------------------------
m, s = tmp("marker.json"), tmp("stamp.json")
json.dump({"ts": "old", "reason": "old"}, open(m, "w"))
gh = FakeGitHub(branch_exists=True)
res, sleeps, m, s = run(gh, marker=m, stamp=s)
expect("success: stale marker cleared", res.ok and not os.path.exists(m))
expect("success: ok-stamp written with this run's time",
       json.load(open(s, encoding="utf-8"))["ts"] == "2026-09-21T11:30:00Z")

# --- --status: a missing marker is NOT success ---------------------------------------------------------------
m, s = tmp("marker.json"), tmp("stamp.json")
st_code = lambda **kw: pfh.main(["--status"], marker_path=m, stamp_path=s, now=NOW, **kw)
expect("status: no marker AND no stamp (never ran) -> 1", st_code() == 1)
json.dump({"ts": "2026-09-21T10:00:00Z"}, open(s, "w"))
expect("status: fresh stamp, no marker -> 0", st_code() == 0)
json.dump({"ts": "2026-09-20T01:00:00Z"}, open(s, "w"))
expect("status: stamp 34.5h old (publish not running) -> 1", st_code() == 1)
json.dump({"ts": "2026-09-21T10:00:00Z"}, open(s, "w"))
json.dump({"ts": "2026-09-21T09:00:00Z", "reason": "boom", "attempts": 4, "last_error": "x"}, open(m, "w"))
expect("status: marker present -> 1 even with a fresh stamp", st_code() == 1)
open(m, "w").write("{corrupt")
expect("status: corrupt marker -> 1", st_code() == 1)
os.remove(m)
open(s, "w").write("{corrupt")
expect("status: corrupt stamp -> 1", st_code() == 1)

# --- main(): exit codes -----------------------------------------------------------------------------------------
m, s = tmp("m.json"), tmp("s.json")
gh = FakeGitHub(branch_exists=True)
rc = pfh.main([], runner=gh, build_fn=lambda: PAYLOAD, sleep=lambda x: None, marker_path=m, stamp_path=s, now=NOW)
expect("main: success -> exit 0", rc == 0, repr(rc))
gh = FakeGitHub(branch_exists=True, faults=["net"] * 40)
rc = pfh.main([], runner=gh, build_fn=lambda: PAYLOAD, sleep=lambda x: None, marker_path=m, stamp_path=s, now=NOW)
expect("main: publish failure -> exit 2 + marker", rc == 2 and os.path.exists(m), repr(rc))


def boom():
    raise RuntimeError("emitter exploded")


gh = FakeGitHub(branch_exists=True)
m3 = tmp("m.json")
rc = pfh.main([], runner=gh, build_fn=boom, sleep=lambda x: None, marker_path=m3, stamp_path=tmp("s.json"), now=NOW)
expect("main: build failure -> exit 2, marker, no gh calls", rc == 2 and os.path.exists(m3) and gh.calls == [], repr((rc, gh.calls)))
expect("main: build failure marker names the cause", "emitter exploded" in json.load(open(m3, encoding="utf-8"))["reason"])

# --- unwritable state dir: still exit 2, loudly ------------------------------------------------------------------------
blocker = tmp("afile")
open(blocker, "w").write("x")
gh = FakeGitHub(branch_exists=True, faults=["net"] * 40)
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    rc = pfh.main([], runner=gh, build_fn=lambda: PAYLOAD, sleep=lambda x: None,
                  marker_path=os.path.join(blocker, "sub", "m.json"), stamp_path=tmp("s.json"), now=NOW)
expect("unwritable marker dir: publish failure still exits 2 (never swallowed)", rc == 2, repr(rc))
expect("unwritable marker dir: says so out loud", "could not write" in buf.getvalue(), buf.getvalue())

# --- run_gh: stdin is UTF-8 bytes with no CR translation; timeouts map to status None -------------------------------------------
captured = {}


class FakeProc:
    returncode, stdout, stderr = 0, b"HTTP/2.0 200 OK\n\n{}", b""


def fake_run(cmd, input=None, capture_output=None, timeout=None):
    captured.update(cmd=cmd, input=input, timeout=timeout)
    return FakeProc


real_run, real_which = pfh.subprocess.run, pfh.shutil.which
pfh.subprocess.run, pfh.shutil.which = fake_run, (lambda n: "gh")
try:
    pfh.run_gh(["api"], '{"a":\n"café"}')
    expect("run_gh: stdin is bytes, UTF-8, no CR added",
           isinstance(captured["input"], bytes) and b"\r" not in captured["input"]
           and captured["input"] == '{"a":\n"café"}'.encode("utf-8"), repr(captured["input"]))
    expect("run_gh: per-call timeout is set", captured["timeout"] == pfh.GH_TIMEOUT_S, repr(captured["timeout"]))

    def boom_timeout(cmd, **kw):
        raise pfh.subprocess.TimeoutExpired(cmd, 30)

    pfh.subprocess.run = boom_timeout
    rc_, out_, err_ = pfh.run_gh(["api"])
    expect("run_gh: timeout -> rc 124, retryable (no HTTP status)",
           rc_ == 124 and pfh.parse_response(rc_, out_, err_)[0] is None, repr((rc_, out_, err_)))
finally:
    pfh.subprocess.run, pfh.shutil.which = real_run, real_which

# --- unexpected failures must still leave a marker (was: traceback, exit 1, no marker, --status OK for 26h) ------------------
def spawn_fails(argv, input_text=None):
    raise OSError("cannot spawn gh")


res, sleeps, m, s = run(spawn_fails)
expect("spawn failure: fails, reason says unexpected", (not res.ok) and "unexpected" in res.reason, repr(res))
expect("spawn failure: marker written, no ok-stamp", os.path.exists(m) and not os.path.exists(s))

gh_ok = FakeGitHub(branch_exists=True)


def blob_without_sha(argv, input_text=None):
    if "repos/%sgit/blobs" % REPO.split("/")[0] in " ".join(argv) or any(a.endswith("git/blobs") for a in argv):
        return 0, "HTTP/2.0 201 Created\n\n{}", ""
    return gh_ok(argv, input_text)


res, sleeps, m, s = run(blob_without_sha)
expect("201 without sha: treated as a failed publish, marker names it",
       (not res.ok) and os.path.exists(m) and "no sha" in json.load(open(m, encoding="utf-8"))["last_error"], repr(res))

real_publish = pfh.publish
pfh.publish = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("publish blew up"))
try:
    mp_crash = tmp("m.json")
    rc = pfh.main([], runner=FakeGitHub(branch_exists=True), build_fn=lambda: PAYLOAD,
                  marker_path=mp_crash, stamp_path=tmp("s.json"), now=NOW)
    expect("publish crash: main exits 2 and leaves a marker", rc == 2 and os.path.exists(mp_crash), repr(rc))
finally:
    pfh.publish = real_publish

gh = FakeGitHub(branch_exists=True, faults=[422] * 40)
res, sleeps, m, s = run(gh)
expect("persistent 422 (e.g. a ruleset rejecting the ref): retried, then fails with a marker",
       (not res.ok) and res.attempts == 4 and sleeps == [2, 8, 20] and os.path.exists(m), repr((res, sleeps)))

m, s = tmp("marker.json"), tmp("stamp.json")
json.dump({"ts": "2026-09-21T14:30:00Z"}, open(s, "w"))
expect("status: stamp dated hours in the future (clock skew) -> 1",
       pfh.main(["--status"], marker_path=m, stamp_path=s, now=NOW) == 1)

# --- payload published verbatim ---------------------------------------------------------------------------------------------
gh = FakeGitHub(branch_exists=True)
pfh.main([], runner=gh, build_fn=lambda: PAYLOAD, sleep=lambda x: None, marker_path=tmp(), stamp_path=tmp(), now=NOW)
expect("published bytes: valid JSON equal to payload, newline-terminated",
       json.loads(gh.branch_content()) == PAYLOAD and gh.branch_content().endswith(b"\n"))
expect("published bytes carry no CR (Windows stdin translation)", b"\r" not in gh.branch_content())

# --- the REAL payload builder (was untested): exact keys, counts/hashes only -----------------------------------------------------
real = pfh.build_payload()
expect("real payload: exactly ts/probe_version/fleets/registries",
       set(real) == {"ts", "probe_version", "fleets", "registries"}, repr(sorted(real)))
expect("real payload: both fleets present", set(real["fleets"]) == {"cc", "lams"})
expect("real payload: registries carry only path/exists/sha256",
       all(set(v) == {"path", "exists", "sha256"} for v in real["registries"].values()))
blob = json.dumps(real)
expect("real payload: no task ids / cron strings leak", "scheduledTasks" not in blob and "cronExpression" not in blob)

# --- summary --------------------------------------------------------------------------------------------------------------------------
failed = [l for ok, l in results if not ok]
print("%d/%d passed" % (len(results) - len(failed), len(results)))
sys.exit(1 if failed else 0)
