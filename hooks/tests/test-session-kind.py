"""Tests for hooks/lib/session_kind.py (R-06).

Run: python test-session-kind.py
Every case passes explicit dirs= and env=, so ambient machine state cannot flip a
result. Stdlib only. ASCII-only. Windows (`python`).
"""
import json
import os
import sys
import tempfile
import time

HOOKS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(HOOKS_DIR)
sys.path.insert(0, os.path.join(HOOKS_DIR, "lib"))
import session_kind as sk  # noqa: E402

SID = "aaaaaaaa-1111-2222-3333-444444444444"
OTHER = "bbbbbbbb-5555-6666-7777-888888888888"
DESKTOP = {"CLAUDE_CODE_ENTRYPOINT": "claude-desktop"}
_failures = []


def check(name, cond, detail=""):
    if cond:
        print("PASS " + name)
    else:
        print("FAIL " + name + ("  " + detail if detail else ""))
        _failures.append(name)


def store(records, ages=None):
    d = tempfile.mkdtemp(prefix="sk-store-")
    for i, rec in enumerate(records):
        p = os.path.join(d, "local_%02d.json" % i)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(rec if isinstance(rec, str) else json.dumps(rec))
        if ages and ages[i]:
            old = time.time() - ages[i]
            os.utime(p, (old, old))
    return d


def test_record_join():
    d = store([{"cliSessionId": SID, "scheduledTaskId": "ora-pm-ledger"}])
    k, tid, ev = sk.classify(SID, env=DESKTOP, dirs=[d])
    check("K1 record with scheduledTaskId -> SCHEDULED", k == sk.SCHEDULED, k)
    check("K2 task id comes from the record", tid == "ora-pm-ledger", repr(tid))
    d = store([{"cliSessionId": SID}])
    check("K3 record without scheduledTaskId -> INTERACTIVE",
          sk.classify(SID, env=DESKTOP, dirs=[d])[0] == sk.INTERACTIVE)
    d = store([{"cliSessionId": OTHER, "scheduledTaskId": "ora-x"}])
    check("K4 another session's record -> UNKNOWN",
          sk.classify(SID, env=DESKTOP, dirs=[d])[0] == sk.UNKNOWN)
    d = store([{"cliSessionId": SID, "scheduledTaskId": ""}])
    check("K5 empty scheduledTaskId -> INTERACTIVE",
          sk.classify(SID, env=DESKTOP, dirs=[d])[0] == sk.INTERACTIVE)


def test_entrypoint():
    d = store([])
    k, tid, ev = sk.classify(SID, env={"CLAUDE_CODE_ENTRYPOINT": "sdk-cli"}, dirs=[d])
    check("K6 headless sdk entrypoint without a record -> SCHEDULED, no task id",
          k == sk.SCHEDULED and tid is None, "%s %r" % (k, tid))
    check("K7 cli entrypoint without a record -> UNKNOWN",
          sk.classify(SID, env={"CLAUDE_CODE_ENTRYPOINT": "cli"}, dirs=[d])[0] == sk.UNKNOWN)
    d = store([{"cliSessionId": SID}])
    check("K8 sdk entrypoint beats an interactive record",
          sk.classify(SID, env={"CLAUDE_CODE_ENTRYPOINT": "sdk-ts"}, dirs=[d])[0]
          == sk.SCHEDULED)


def test_staleness_and_damage():
    d = store([{"cliSessionId": SID, "scheduledTaskId": "ora-x"}], ages=[8 * 86400])
    check("K9 a record older than 7 days is ignored",
          sk.classify(SID, env=DESKTOP, dirs=[d])[0] == sk.UNKNOWN)
    d = store(["{not json", {"cliSessionId": SID, "scheduledTaskId": "ora-x"}])
    check("K10 a malformed record is skipped, the good one still found",
          sk.classify(SID, env=DESKTOP, dirs=[d])[0] == sk.SCHEDULED)
    saved = sk.MAX_RECORD_BYTES
    try:
        sk.MAX_RECORD_BYTES = 10
        d = store([{"cliSessionId": SID, "scheduledTaskId": "ora-x"}])
        check("K11 an oversized record is skipped",
              sk.classify(SID, env=DESKTOP, dirs=[d])[0] == sk.UNKNOWN)
    finally:
        sk.MAX_RECORD_BYTES = saved
    d = store([{"cliSessionId": SID, "scheduledTaskId": "../../evil"}])
    k, tid, ev = sk.classify(SID, env=DESKTOP, dirs=[d])
    check("K12 an unsafe task id still means SCHEDULED but yields no task id",
          k == sk.SCHEDULED and tid is None, "%s %r" % (k, tid))
    check("K13 empty session id -> UNKNOWN", sk.classify("", env=DESKTOP, dirs=[d])[0] == sk.UNKNOWN)
    check("K14 non-str session id -> UNKNOWN", sk.classify(None, env=DESKTOP, dirs=[d])[0] == sk.UNKNOWN)
    check("K15 missing directory -> UNKNOWN",
          sk.classify(SID, env=DESKTOP, dirs=["Z:/no/such/dir"])[0] == sk.UNKNOWN)


def test_seam_and_hygiene():
    d = store([])
    os.environ[sk.ENV_STORE_DIRS] = d
    try:
        check("K16 test seam is honored", sk.store_dirs() == [d])
    finally:
        del os.environ[sk.ENV_STORE_DIRS]
    try:
        dirs = sk.store_dirs()
        ok = isinstance(dirs, list)
    except Exception:
        ok = False
    check("K17 live store discovery returns a list and never raises", ok)
    with open(os.path.join(REPO, "settings.json"), "r", encoding="utf-8-sig") as fh:
        env = json.load(fh).get("env", {})
    for seam in ("ORA_SESSION_STORE_DIRS", "ORA_MCP_DELETE_ALLOWLIST", "ORA_MCP_DELETE_LOG",
                 "ORA_OVERRIDE_SESSIONS_DIR"):
        check("K18 settings.json env does not set test seam %s" % seam, seam not in env)


if __name__ == "__main__":
    test_record_join()
    test_entrypoint()
    test_staleness_and_damage()
    test_seam_and_hygiene()
    if _failures:
        print("\n%d FAILURE(S): %s" % (len(_failures), ", ".join(_failures[:12])))
        sys.exit(1)
    print("\nALL session-kind tests passed.")
    sys.exit(0)
