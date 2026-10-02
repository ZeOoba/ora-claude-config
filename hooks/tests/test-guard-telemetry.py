"""Tests for per-guard dispatcher telemetry (hooks/lib/guard_telemetry.py, wired
into hooks/pretooluse-dispatcher.py) and hooks/guard-telemetry-summary.py.

Pins the four properties the hooks-audit (2026-09-30) required:
  1. logging works -- one schema-exact record per guard execution;
  2. confidentiality -- a confidential-looking term placed in the command, the
     file path, the content, the session_id and the tool_name NEVER appears in
     the log bytes;
  3. decision-neutral -- a telemetry failure (unwritable path, flush raising,
     make_record raising) never changes the dispatcher's exit code, in either
     the allow or the block direction;
  4. bounded -- rotation at the threshold to .1, keeping exactly one generation.
Plus the ORA_GUARD_TELEMETRY=0 kill switch and the summary's arithmetic.

Stdlib only. ASCII-only. Windows (`python`).
"""
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

HOOKS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DISPATCHER = os.path.join(HOOKS_DIR, "pretooluse-dispatcher.py")
SUMMARY = os.path.join(HOOKS_DIR, "guard-telemetry-summary.py")

SECRET = "ZZQX-CONFIDENTIAL-DEAL-TERM-4417"
SCHEMA = {"ts", "chain", "guard", "tool_name", "session_id", "exit_code", "ms",
          "path_taken"}

_failures = []


def check(name, cond, detail=""):
    if cond:
        print("PASS " + name)
    else:
        print("FAIL " + name + ("  " + (detail if isinstance(detail, str)
                                        else repr(detail)) if detail else ""))
        _failures.append(name)


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


FAKE_ALLOW = "import sys\ndef main():\n    sys.stdin.read()\n"
FAKE_BLOCK = ("import sys\ndef main():\n    sys.stdin.read()\n"
              "    sys.stderr.write('BLOCKED (fake)\\n')\n    sys.exit(2)\n")


class Rig(object):
    """A throwaway hooks dir holding fake guards, driven through the REAL
    dispatcher module in-process (its HOOKS_DIR is repointed)."""

    def __init__(self):
        self.root = tempfile.mkdtemp(prefix="gtel-")
        self.hooks = os.path.join(self.root, "hooks")
        os.makedirs(self.hooks)
        for name, body in (("fake-allow", FAKE_ALLOW), ("fake-block", FAKE_BLOCK)):
            with open(os.path.join(self.hooks, name + ".py"), "w",
                      encoding="ascii") as fh:
                fh.write(body)
        self.log = os.path.join(self.root, "state", "guard-telemetry.jsonl")
        self._env = {}
        self.disp = _load(DISPATCHER, "_disp_%d" % id(self))
        self.disp.HOOKS_DIR = self.hooks

    def setenv(self, **kw):
        for k, v in kw.items():
            self._env.setdefault(k, os.environ.get(k))
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def run(self, chain, payload):
        raw = json.dumps(payload).encode("utf-8")

        class _In(object):
            buffer = io.BytesIO(raw)
        real_in, real_err = sys.stdin, sys.stderr
        sys.stdin, sys.stderr = _In(), io.StringIO()
        try:
            return self.disp.main(chain=chain, label="test")
        except Exception as e:  # an escaping exception IS a decision change
            return "EXC:" + type(e).__name__
        finally:
            sys.stdin, sys.stderr = real_in, real_err

    def lines(self, path=None):
        try:
            with open(path or self.log, "r", encoding="utf-8") as fh:
                return [json.loads(x) for x in fh if x.strip()]
        except OSError:
            return []

    def cleanup(self):
        for k, v in self._env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        shutil.rmtree(self.root, ignore_errors=True)


def payload(**extra):
    p = {"session_id": "11111111-2222-3333-4444-555555555555", "tool_name": "Edit",
         "tool_input": {"file_path": "C:/tmp/x.py", "old_string": "a",
                        "new_string": "b"}}
    p.update(extra)
    return p


# ------------------------------------------------------------------- 1. works
def test_logging_works():
    r = Rig()
    try:
        r.setenv(ORA_GUARD_TELEMETRY_PATH=r.log, ORA_GUARD_TELEMETRY=None)
        rc = r.run(["fake-allow", "fake-allow"], payload())
        recs = r.lines()
        check("1a allow chain exits 0", rc == 0, "rc=%r" % rc)
        check("1b one record per guard execution", len(recs) == 2, "got %d" % len(recs))
        check("1c every record has EXACTLY the contracted schema",
              all(set(x) == SCHEMA for x in recs), repr(recs[:1]))
        check("1d records carry chain/guard/tool/session/rc/path_taken",
              recs and recs[0]["chain"] == "test" and recs[0]["guard"] == "fake-allow"
              and recs[0]["tool_name"] == "Edit"
              and recs[0]["session_id"] == "11111111-2222-3333-4444-555555555555"
              and recs[0]["exit_code"] == 0 and recs[0]["path_taken"] == "inprocess"
              and isinstance(recs[0]["ms"], float), repr(recs[:1]))

        rc = r.run(["fake-allow", "fake-block", "fake-allow"], payload())
        recs = r.lines()[2:]
        check("1e block chain exits 2", rc == 2, "rc=%r" % rc)
        check("1f a block short-circuits -- no record for guards that never ran",
              [x["guard"] for x in recs] == ["fake-allow", "fake-block"],
              repr([x["guard"] for x in recs]))
        check("1g the blocking record carries exit_code 2",
              recs and recs[-1]["exit_code"] == 2, repr(recs[-1:]))

        # Missing guard -> the dispatcher's fail-CLOSED configuration emergency.
        rc = r.run(["fake-allow", "no-such-guard"], payload())
        recs = r.lines()[4:]
        check("1h missing guard still fails closed (rc 2)", rc == 2, "rc=%r" % rc)
        check("1i and is recorded as path_taken=failclosed",
              [(x["guard"], x["path_taken"]) for x in recs]
              == [("no-such-guard", "failclosed")], repr(recs))
    finally:
        r.cleanup()


# ----------------------------------------------------------- 2. confidentiality
def test_confidential_term_never_logged_in_process():
    r = Rig()
    try:
        r.setenv(ORA_GUARD_TELEMETRY_PATH=r.log, ORA_GUARD_TELEMETRY=None)
        p = payload(session_id="sess " + SECRET,
                    tool_name="Edit " + SECRET,
                    tool_input={"file_path": "C:/deals/%s/model.py" % SECRET,
                                "command": "echo %s" % SECRET,
                                "old_string": SECRET, "new_string": SECRET})
        r.run(["fake-allow", "fake-block"], p)
        with open(r.log, "rb") as fh:
            blob = fh.read()
        check("2a the confidential term is absent from the log bytes",
              SECRET.encode("ascii") not in blob, blob[:300])
        recs = r.lines()
        check("2b a non-identifier tool_name / session_id is written as <invalid>",
              recs and recs[0]["tool_name"] == "<invalid>"
              and recs[0]["session_id"] == "<invalid>", repr(recs[:1]))
    finally:
        r.cleanup()


def test_each_sanitizing_layer_holds_alone():
    """The dispatcher sanitizes twice (payload_ids() then make_record()), so an
    end-to-end test cannot see one layer regress while the other holds. Pin
    each layer on its own."""
    tel = _load(os.path.join(HOOKS_DIR, "lib", "guard_telemetry.py"), "_gt_layers")
    rec = tel.make_record("chain " + SECRET, "guard/" + SECRET, "Edit " + SECRET,
                          "sid " + SECRET, 0, 1.0, "inprocess; " + SECRET)
    check("2g make_record alone rejects free text in every string field",
          SECRET not in json.dumps(rec) and rec["tool_name"] == "<invalid>"
          and rec["session_id"] == "<invalid>" and rec["path_taken"] == "<invalid>",
          json.dumps(rec)[:200])
    ids = tel.payload_ids(json.dumps({"tool_name": "Bash " + SECRET,
                                      "session_id": "x/" + SECRET}).encode("utf-8"))
    check("2h payload_ids alone rejects free text",
          ids == ("<invalid>", "<invalid>"), repr(ids))
    check("2i payload_ids tolerates non-JSON / non-dict payloads",
          tel.payload_ids(b"\xff\xfe junk") == ("", "") and
          tel.payload_ids(b"[1]") == ("", ""))


def test_confidential_term_never_logged_real_chain_subprocess():
    """End to end through the REAL dispatcher and REAL guard chains, as the
    harness spawns it. The term rides in the Bash command and in an Edit's
    path/content; neither may reach the log."""
    tmp = tempfile.mkdtemp(prefix="gtel-e2e-")
    try:
        log = os.path.join(tmp, "t.jsonl")
        env = dict(os.environ)
        env["ORA_GUARD_TELEMETRY_PATH"] = log
        env.pop("ORA_GUARD_TELEMETRY", None)
        target = os.path.join(tmp, SECRET + ".txt").replace("\\", "/")
        cases = [
            ([], {"session_id": "e2e-0001", "tool_name": "Edit",
                  "tool_input": {"file_path": target, "old_string": "x",
                                 "new_string": "deal " + SECRET}}),
            (["--chain", "bash"], {"session_id": "e2e-0001", "tool_name": "Bash",
                                   "tool_input": {"command": "echo %s > %s"
                                                  % (SECRET, target)}}),
        ]
        rcs = []
        for argv, p in cases:
            proc = subprocess.run([sys.executable, DISPATCHER] + argv,
                                  input=json.dumps(p).encode("utf-8"),
                                  capture_output=True, env=env, timeout=120)
            rcs.append(proc.returncode)
        with open(log, "rb") as fh:
            blob = fh.read()
        recs = [json.loads(x) for x in blob.decode("ascii").splitlines() if x]
        check("2c real chains produced records (%d)" % len(recs), len(recs) >= 2,
              "rcs=%r" % rcs)
        check("2d real-chain log never contains the confidential term",
              SECRET.encode("ascii") not in blob, blob[:300])
        check("2e real-chain log contains no path separators from the payload",
              b"/" not in blob and b"\\" not in blob,
              blob[:300])
        check("2f both chains labelled", {x["chain"] for x in recs} >= {"editwrite", "bash"},
              repr({x["chain"] for x in recs}))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------- 3. decision-neutral
def test_logging_failure_never_changes_exit_code():
    r = Rig()
    try:
        # (a) unwritable: the log's parent is a FILE, so makedirs/open both fail.
        blocker = os.path.join(r.root, "not-a-dir")
        with open(blocker, "w") as fh:
            fh.write("x")
        r.setenv(ORA_GUARD_TELEMETRY_PATH=os.path.join(blocker, "t.jsonl"),
                 ORA_GUARD_TELEMETRY=None)
        check("3a unwritable log: allow chain still exits 0",
              r.run(["fake-allow"], payload()) == 0)
        check("3b unwritable log: block chain still exits 2",
              r.run(["fake-allow", "fake-block"], payload()) == 2)

        # (b) flush itself raising.
        r.setenv(ORA_GUARD_TELEMETRY_PATH=r.log)
        tel = r.disp._telemetry
        orig_flush, orig_make = tel.flush, tel.make_record

        def boom(*a, **k):
            raise RuntimeError("telemetry exploded")
        try:
            tel.flush = boom
            check("3c flush raising: allow chain still exits 0",
                  r.run(["fake-allow"], payload()) == 0)
            check("3d flush raising: block chain still exits 2",
                  r.run(["fake-block"], payload()) == 2)
            tel.flush = orig_flush
            tel.make_record = boom
            check("3e make_record raising: allow chain still exits 0",
                  r.run(["fake-allow"], payload()) == 0)
            check("3f make_record raising: block chain still exits 2",
                  r.run(["fake-block"], payload()) == 2)
        finally:
            tel.flush, tel.make_record = orig_flush, orig_make

        # (c) the telemetry module missing entirely.
        saved = r.disp._telemetry
        r.disp._telemetry = None
        try:
            check("3g telemetry absent: allow 0 / block 2 unchanged",
                  r.run(["fake-allow"], payload()) == 0
                  and r.run(["fake-block"], payload()) == 2)
        finally:
            r.disp._telemetry = saved
    finally:
        r.cleanup()


# ------------------------------------------------------------ kill switch
def test_kill_switch():
    r = Rig()
    try:
        r.setenv(ORA_GUARD_TELEMETRY_PATH=r.log, ORA_GUARD_TELEMETRY="0")
        rc = r.run(["fake-allow", "fake-block"], payload())
        check("K1 kill switch: decision unchanged", rc == 2, "rc=%r" % rc)
        check("K2 kill switch: no log file written", not os.path.exists(r.log))
    finally:
        r.cleanup()


# ---------------------------------------------------------------- 4. rotation
def test_rotation_keeps_one_generation():
    r = Rig()
    try:
        r.setenv(ORA_GUARD_TELEMETRY_PATH=r.log, ORA_GUARD_TELEMETRY=None,
                 ORA_GUARD_TELEMETRY_MAX_BYTES="200")
        os.makedirs(os.path.dirname(r.log), exist_ok=True)
        with open(r.log + ".1", "w", encoding="ascii") as fh:
            fh.write("OLDEST-GENERATION\n")
        with open(r.log, "w", encoding="ascii") as fh:
            fh.write("X" * 250 + "\n")
        r.run(["fake-allow"], payload())
        with open(r.log + ".1", "r", encoding="ascii") as fh:
            rotated = fh.read()
        check("4a the over-threshold file was rotated to .1", rotated.startswith("X" * 250),
              rotated[:40])
        check("4b the previous .1 was replaced (one generation kept)",
              "OLDEST-GENERATION" not in rotated)
        check("4c the live file restarted with only the new record",
              len(r.lines()) == 1, repr(r.lines()))
        check("4d no .2 generation is ever created", not os.path.exists(r.log + ".2"))
        r.run(["fake-allow"], payload())
        check("4e under the threshold, appends continue without rotating",
              len(r.lines()) == 2, repr(r.lines()))
    finally:
        r.cleanup()


def test_rotation_race_and_lock():
    """Adversarial review 2026-09-30 finding 4: two sessions crossing the
    threshold together must rotate ONCE. Pinned three ways."""
    tmp = tempfile.mkdtemp(prefix="gtel-race-")
    try:
        tel = _load(os.path.join(HOOKS_DIR, "lib", "guard_telemetry.py"), "_gt_race")
        log = os.path.join(tmp, "t.jsonl")
        saved = {k: os.environ.get(k) for k in (
            "ORA_GUARD_TELEMETRY_MAX_BYTES", "ORA_GUARD_TELEMETRY_PATH",
            "ORA_GUARD_TELEMETRY")}
        os.environ["ORA_GUARD_TELEMETRY_MAX_BYTES"] = "100"
        os.environ["ORA_GUARD_TELEMETRY_PATH"] = log
        os.environ.pop("ORA_GUARD_TELEMETRY", None)
        try:
            # (a) the loser of the race: its first (unlocked) size read was
            # stale-big, but under the lock the file is already the winner's
            # fresh small one -> it must NOT rotate again.
            with open(log + ".1", "w") as fh:
                fh.write("WINNERS-ROTATED-5MB\n")
            with open(log, "w") as fh:
                fh.write("fresh\n")
            reads = iter([10 ** 9, 6])
            tel._size = lambda p: next(reads)
            tel._rotate_if_needed(log)
            tel._size = os.path.getsize
            with open(log + ".1") as fh:
                check("R1 a stale-size loser does not clobber the winner's .1",
                      fh.read() == "WINNERS-ROTATED-5MB\n")
            # (b) a FRESH lock held by another session -> skip rotation, keep
            # appending to the current file.
            with open(log, "w") as fh:
                fh.write("X" * 200 + "\n")
            with open(log + ".rotate.lock", "w") as fh:
                fh.write("")
            tel.flush([tel.make_record("c", "g", "Edit", "s", 0, 1.0, "inprocess")])
            with open(log) as fh:
                body = fh.read()
            check("R2 a held lock skips rotation and the append still lands",
                  body.startswith("X" * 200) and body.count("\n") == 2, body[-80:])
            # (c) a STALE lock (crashed holder) is cleared, then the next call
            # rotates -- rotation cannot wedge permanently.
            old = time.time() - 3600
            os.utime(log + ".rotate.lock", (old, old))
            tel._rotate_if_needed(log)
            check("R3 a stale lock is removed", not os.path.exists(log + ".rotate.lock"))
            tel._rotate_if_needed(log)
            check("R4 and the following call rotates",
                  not os.path.exists(log) and os.path.exists(log + ".1"))
            check("R5 the lock never outlives a rotation",
                  not os.path.exists(log + ".rotate.lock"))
        finally:
            for k, v in saved.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_large_payload_ids():
    tel = _load(os.path.join(HOOKS_DIR, "lib", "guard_telemetry.py"), "_gt_large")
    big = json.dumps({"session_id": "big-sess-1", "tool_name": "Write",
                      "tool_input": {"file_path": "C:/x/" + SECRET,
                                     "content": SECRET + ("y" * (2 * 1024 * 1024))}}
                     ).encode("utf-8")
    t0 = time.time()
    ids = tel.payload_ids(big)
    dt = time.time() - t0
    check("L1 a >256KB payload still yields the ids (head scan, no full parse)",
          ids == ("Write", "big-sess-1"), repr(ids))
    check("L2 and cheaply (%.1f ms)" % (dt * 1000), dt < 0.05)
    evil = json.dumps({"session_id": "x " + SECRET, "tool_name": "W " + SECRET,
                       "tool_input": {"content": "z" * (300 * 1024)}}).encode("utf-8")
    check("L3 the head-scan path applies the same allowlist",
          tel.payload_ids(evil) == ("<invalid>", "<invalid>"),
          repr(tel.payload_ids(evil)))


# ----------------------------------------------------------------- summary
def test_summary():
    tmp = tempfile.mkdtemp(prefix="gtel-sum-")
    try:
        log = os.path.join(tmp, "t.jsonl")
        with open(log, "w", encoding="ascii") as fh:
            for i in range(1, 21):
                fh.write(json.dumps({"ts": 1.0, "chain": "bash", "guard": "g1",
                                     "tool_name": "Bash", "session_id": "s",
                                     "exit_code": 2 if i == 20 else 0,
                                     "ms": float(i), "path_taken":
                                     "subprocess" if i == 1 else "inprocess"}) + "\n")
            fh.write("not json\n")
        proc = subprocess.run([sys.executable, SUMMARY, "--path", log, "--json"],
                              capture_output=True, timeout=60)
        data = json.loads(proc.stdout.decode("utf-8"))
        g = data["groups"][0]
        check("S1 summary counts fires/blocks/subprocess",
              (g["fires"], g["blocks"], g["subprocess"]) == (20, 1, 1), repr(g))
        check("S2 nearest-rank p50=10 p95=19 max=20",
              (g["p50_ms"], g["p95_ms"], g["max_ms"]) == (10.0, 19.0, 20.0), repr(g))
        check("S3 malformed lines are counted, not fatal", data["malformed"] == 1)
        with open(log, "rb") as fh:
            before = fh.read()
        subprocess.run([sys.executable, SUMMARY, "--path", log],
                       capture_output=True, timeout=60)
        with open(log, "rb") as fh:
            check("S4 summary is read-only", fh.read() == before)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    for t in (test_logging_works, test_confidential_term_never_logged_in_process,
              test_each_sanitizing_layer_holds_alone,
              test_confidential_term_never_logged_real_chain_subprocess,
              test_logging_failure_never_changes_exit_code, test_kill_switch,
              test_rotation_keeps_one_generation, test_rotation_race_and_lock,
              test_large_payload_ids, test_summary):
        t()
    if _failures:
        print("\n%d FAILURE(S): %s" % (len(_failures), ", ".join(_failures)))
        sys.exit(1)
    print("\nALL guard-telemetry tests passed.")
    sys.exit(0)
