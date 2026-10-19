"""Tests for hooks/lib/session_kind.py (R-06).

Run: python test-session-kind.py
Every case passes explicit dirs= and env=, so ambient machine state cannot flip a
result. Stdlib only. ASCII-only. Windows (`python`).
"""
import json
import os
import subprocess
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
CLI = {"CLAUDE_CODE_ENTRYPOINT": "cli"}
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
    check("K4 another session's record, non-Desktop -> UNKNOWN",
          sk.classify(SID, env=CLI, dirs=[d])[0] == sk.UNKNOWN)
    check("K4b another session's record, Desktop -> SCHEDULED (fail closed)",
          sk.classify(SID, env=DESKTOP, dirs=[d])[0] == sk.SCHEDULED)
    # C3: key PRESENT means scheduled, whatever the value; task id only from a valid str.
    for label, val in (("None", None), ("0", 0), ("empty str", ""), ("list", ["x"]),
                       ("dict", {}), ("True", True)):
        d = store([{"cliSessionId": SID, "scheduledTaskId": val}])
        k, tid, ev = sk.classify(SID, env=DESKTOP, dirs=[d])
        check("K5 scheduledTaskId=%s present -> SCHEDULED, no task id" % label,
              k == sk.SCHEDULED and tid is None, "%s %r" % (k, tid))
    d = store([{"cliSessionId": SID, "scheduledTaskId": "ora-ok"}])
    check("K5b valid str value still yields the task id",
          sk.classify(SID, env=DESKTOP, dirs=[d])[1] == "ora-ok")


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
    k, tid, ev = sk.classify(SID, env=DESKTOP, dirs=[d])
    check("K9 a stale scheduled record (long-running session) still counts -> SCHEDULED",
          k == sk.SCHEDULED and tid == "ora-x", "%s %r" % (k, tid))
    check("K9b stale scheduled record, non-Desktop, still counts as evidence -> SCHEDULED",
          sk.classify(SID, env=CLI, dirs=[d])[0] == sk.SCHEDULED)
    d = store([{"cliSessionId": SID}], ages=[8 * 86400])
    check("K9c a stale plain record is not proof of interactive: Desktop -> SCHEDULED",
          sk.classify(SID, env=DESKTOP, dirs=[d])[0] == sk.SCHEDULED)
    check("K9d a stale plain record, non-Desktop -> UNKNOWN",
          sk.classify(SID, env=CLI, dirs=[d])[0] == sk.UNKNOWN)
    # Malformed file is the NEWEST, so it is read first; a bad parse must not stop the scan.
    d = store(["{not json", {"cliSessionId": SID, "scheduledTaskId": "ora-x"}],
              ages=[10, 100])
    check("K10 a malformed (newest) record is skipped, the older good one still found",
          sk.classify(SID, env=DESKTOP, dirs=[d])[0] == sk.SCHEDULED)
    d = store([{"cliSessionId": SID, "scheduledTaskId": "ora-x"}, "{not json"],
              ages=[10, 100])
    check("K10b same result when the malformed file is the oldest",
          sk.classify(SID, env=DESKTOP, dirs=[d])[0] == sk.SCHEDULED)
    saved = sk.MAX_RECORD_BYTES
    try:
        sk.MAX_RECORD_BYTES = 10
        d = store([{"cliSessionId": SID, "scheduledTaskId": "ora-x"}])
        check("K11 an oversized record is skipped (non-Desktop -> UNKNOWN)",
              sk.classify(SID, env=CLI, dirs=[d])[0] == sk.UNKNOWN)
    finally:
        sk.MAX_RECORD_BYTES = saved
    d = store([{"cliSessionId": SID, "scheduledTaskId": "../../evil"}])
    k, tid, ev = sk.classify(SID, env=DESKTOP, dirs=[d])
    check("K12 an unsafe task id still means SCHEDULED but yields no task id",
          k == sk.SCHEDULED and tid is None, "%s %r" % (k, tid))
    check("K13 empty session id -> UNKNOWN", sk.classify("", env=DESKTOP, dirs=[d])[0] == sk.UNKNOWN)
    check("K14 non-str session id -> UNKNOWN", sk.classify(None, env=DESKTOP, dirs=[d])[0] == sk.UNKNOWN)
    check("K15 missing directory under Desktop -> SCHEDULED (fail closed, store-independent)",
          sk.classify(SID, env=DESKTOP, dirs=["Z:/no/such/dir"])[0] == sk.SCHEDULED)
    check("K15b empty dirs list under Desktop -> SCHEDULED (fail closed)",
          sk.classify(SID, env=DESKTOP, dirs=[])[0] == sk.SCHEDULED)
    check("K15c missing directory under cli -> UNKNOWN",
          sk.classify(SID, env=CLI, dirs=["Z:/no/such/dir"])[0] == sk.UNKNOWN)
    check("K15d empty dirs list, no entrypoint -> UNKNOWN",
          sk.classify(SID, env={}, dirs=[])[0] == sk.UNKNOWN)


def test_duplicates():
    # C1: scheduled wins over any number of same-session records, in either order.
    sched = {"cliSessionId": SID, "scheduledTaskId": "ora-pm-ledger"}
    plain = {"cliSessionId": SID}
    d = store([plain, sched], ages=[10, 100])
    k, tid, ev = sk.classify(SID, env=DESKTOP, dirs=[d])
    check("K19 newer record lacks the key, older has it -> SCHEDULED",
          k == sk.SCHEDULED and tid == "ora-pm-ledger", "%s %r" % (k, tid))
    d = store([sched, plain], ages=[10, 100])
    k, tid, ev = sk.classify(SID, env=DESKTOP, dirs=[d])
    check("K20 older record lacks the key, newer has it -> SCHEDULED",
          k == sk.SCHEDULED and tid == "ora-pm-ledger", "%s %r" % (k, tid))
    d = store([plain, plain], ages=[10, 100])
    check("K21 all duplicates lack the key -> INTERACTIVE",
          sk.classify(SID, env=DESKTOP, dirs=[d])[0] == sk.INTERACTIVE)
    d = store([plain, {"cliSessionId": SID, "scheduledTaskId": None}], ages=[10, 100])
    check("K22 older record with key=None beats newer plain record -> SCHEDULED",
          sk.classify(SID, env=DESKTOP, dirs=[d])[0] == sk.SCHEDULED)
    d = store([plain, sched], ages=[10, 8 * 86400])
    check("K23 a stale scheduled duplicate still counts -> SCHEDULED",
          sk.classify(SID, env=DESKTOP, dirs=[d])[0] == sk.SCHEDULED)
    # Two directories: newer plain record in B, older scheduled in A.
    da = store([sched], ages=[100])
    db = store([plain], ages=[10])
    check("K24 two dirs, newer plain in B, older scheduled in A -> SCHEDULED",
          sk.classify(SID, env=DESKTOP, dirs=[da, db])[0] == sk.SCHEDULED)
    check("K24b same with dirs reversed -> SCHEDULED",
          sk.classify(SID, env=DESKTOP, dirs=[db, da])[0] == sk.SCHEDULED)


def test_tampering():
    sched = {"cliSessionId": SID, "scheduledTaskId": "ora-pm-ledger"}
    tampered = {}
    d = store([sched], ages=[30 * 86400])
    tampered["backdate"] = d
    d = store([json.dumps(sched) + " " * (sk.MAX_RECORD_BYTES + 10)])
    tampered["pad past cap"] = d
    d = store(["\ufeff" + json.dumps(sched)])
    tampered["BOM"] = d
    d = store([json.dumps([sched])])
    tampered["list-wrap"] = d
    d = store([{"cliSessionIdX": SID, "scheduledTaskId": "ora-pm-ledger"}])
    tampered["cliSessionId key rename"] = d
    for label, d in tampered.items():
        k, tid, ev = sk.classify(SID, env=DESKTOP, dirs=[d])
        check("T1 %s under claude-desktop -> SCHEDULED" % label, k == sk.SCHEDULED, k)
        if label in ("backdate", "BOM"):
            continue
        k = sk.classify(SID, env=CLI, dirs=[d])[0]
        check("T2 %s under cli -> UNKNOWN" % label, k == sk.UNKNOWN, k)
    k, tid, ev = sk.classify(SID, env={"CLAUDE_CODE_ENTRYPOINT": "Claude-Desktop"},
                             dirs=[tampered["list-wrap"]])
    check("T3 entrypoint match is case-insensitive", k == sk.SCHEDULED and tid is None, k)
    check("T4 desktop with no record: reason names fail closed",
          "fail closed" in sk.classify(SID, env=DESKTOP, dirs=[tampered["list-wrap"]])[2])
    check("T5 desktop, empty session id -> UNKNOWN",
          sk.classify("", env=DESKTOP, dirs=[tampered["list-wrap"]])[0] == sk.UNKNOWN)
    check("T6 no entrypoint at all, no record -> UNKNOWN",
          sk.classify(SID, env={}, dirs=[tampered["list-wrap"]])[0] == sk.UNKNOWN)
    # BOM record is now readable and yields the task id.
    check("T7 BOM record is parsed, task id kept",
          sk.classify(SID, env=CLI, dirs=[store(["\ufeff" + json.dumps(sched)])])[1]
          == "ora-pm-ledger")
    # Backdated under cli: stale evidence still counts.
    check("T8 backdated scheduled record under cli -> SCHEDULED",
          sk.classify(SID, env=CLI, dirs=[tampered["backdate"]])[0] == sk.SCHEDULED)


def test_blanked_registry():
    # Finding 1: a scheduled session blanks/corrupts scheduled-tasks.json so
    # discover_store() skips it; the records must still be found by globbing the roots.
    sched = {"cliSessionId": SID, "scheduledTaskId": "ora-pm-ledger"}
    saved = {k: os.environ.get(k) for k in ("APPDATA", "LOCALAPPDATA", sk.ENV_STORE_DIRS)}
    try:
        for label, content in (("blank", ""), ("corrupt", "{not json"),
                               ("empty tasks", '{"scheduledTasks": []}')):
            root = tempfile.mkdtemp(prefix="sk-appdata-")
            rd = os.path.join(root, "Claude", "claude-code-sessions", "g1", "g2")
            os.makedirs(rd)
            with open(os.path.join(rd, "scheduled-tasks.json"), "w", encoding="utf-8") as fh:
                fh.write(content)
            with open(os.path.join(rd, "local_aa.json"), "w", encoding="utf-8") as fh:
                json.dump(sched, fh)
            os.environ["APPDATA"] = root
            os.environ["LOCALAPPDATA"] = os.path.join(root, "nolocal")
            os.environ.pop(sk.ENV_STORE_DIRS, None)
            k, tid, ev = sk.classify(SID, env=CLI)
            check("B1 registry %s, record present, cli -> SCHEDULED via root glob" % label,
                  k == sk.SCHEDULED and tid == "ora-pm-ledger", "%s %r" % (k, tid))
            check("B2 registry %s, store_dirs includes the record dir" % label,
                  os.path.normcase(rd) in [os.path.normcase(x) for x in sk.store_dirs()])
        # No records at all under the scratch root: Desktop still fails closed.
        root = tempfile.mkdtemp(prefix="sk-appdata-")
        os.environ["APPDATA"] = root
        check("B3 no store at all, Desktop -> SCHEDULED",
              sk.classify(SID, env=DESKTOP)[0] == sk.SCHEDULED)
        check("B4 no store at all, cli -> UNKNOWN", sk.classify(SID, env=CLI)[0] == sk.UNKNOWN)
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def _scratch_root(sched, rd_parts=("g1", "g2")):
    root = tempfile.mkdtemp(prefix="sk-appdata-")
    base = os.path.join(root, "Claude", "claude-code-sessions")
    rd = os.path.join(base, *rd_parts)
    os.makedirs(rd)
    with open(os.path.join(rd, "local_aa.json"), "w", encoding="utf-8") as fh:
        json.dump(sched, fh)
    return root, base, rd


def _with_appdata(root, fn):
    saved = {k: os.environ.get(k) for k in ("APPDATA", "LOCALAPPDATA", sk.ENV_STORE_DIRS)}
    try:
        os.environ["APPDATA"] = root
        os.environ["LOCALAPPDATA"] = os.path.join(root, "nolocal")
        os.environ.pop(sk.ENV_STORE_DIRS, None)
        return fn()
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def _mk_loop(link, target):
    """Directory junction (Windows) or symlink link -> target. True on success."""
    r = subprocess.run(["cmd", "/c", "mklink", "/J", link, target],
                       capture_output=True, text=True)
    if r.returncode == 0 and os.path.exists(link):
        return True
    try:
        os.symlink(target, link, target_is_directory=True)
        return True
    except (OSError, NotImplementedError, AttributeError):
        return False


def _rm_loop(link):
    """Remove the junction/symlink itself, never recursing through it."""
    if not os.path.lexists(link):
        return
    if os.path.islink(link):
        os.unlink(link)
    else:
        subprocess.run(["cmd", "/c", "rmdir", link], capture_output=True, text=True)


def test_junction_loop_and_dot_dirs():
    sched = {"cliSessionId": SID, "scheduledTaskId": "ora-pm-ledger"}
    # C4: a junction loop under claude-code-sessions must not hang classify().
    root, base, rd = _scratch_root(sched)
    links = [os.path.join(base, "g1", "loop"), os.path.join(rd, "loop2")]
    made = [_mk_loop(links[0], base), _mk_loop(links[1], os.path.join(base, "g1"))]
    try:
        if not all(made):
            check("J0 could create junction/symlink loops (else J1-J3 not exercised)", False)
        else:
            def run():
                t0 = time.time()
                r = sk.classify(SID, env=DESKTOP)
                return r, time.time() - t0
            (k, tid, ev), dt = _with_appdata(root, run)
            check("J1 junction loop: classify returns within 5 s", dt < 5.0, "%.2fs" % dt)
            check("J2 junction loop: record still found -> SCHEDULED with task id",
                  k == sk.SCHEDULED and tid == "ora-pm-ledger", "%s %r" % (k, tid))
            dirs = _with_appdata(root, lambda: sk.store_dirs())
            real = set(os.path.normcase(os.path.realpath(d)) for d in dirs)
            check("J3 store_dirs has no duplicate realpaths (links not followed)",
                  len(real) == len(dirs), repr(dirs))
    finally:
        for l in links:
            _rm_loop(l)
    # Depth bound: a record dir deeper than MAX_DEPTH is not enumerated.
    root, base, rd = _scratch_root(sched, ("a", "b", "c", "d", "e"))
    dirs = _with_appdata(root, lambda: sk.store_dirs())
    check("J4 dir at depth 5 not enumerated (bounded)", os.path.normcase(rd)
          not in [os.path.normcase(x) for x in dirs])
    # C3: dot-prefixed record dir is still enumerated.
    root, base, rd = _scratch_root(sched, (".grp", ".grp2"))
    k, tid, ev = _with_appdata(root, lambda: sk.classify(SID, env=CLI))
    check("D1 record in dot-prefixed dir, cli -> SCHEDULED", k == sk.SCHEDULED
          and tid == "ora-pm-ledger", "%s %r" % (k, tid))
    # Budget: exhausted budget under Desktop fails closed with a budget reason; cli is UNKNOWN.
    root, base, rd = _scratch_root({"cliSessionId": SID})
    saved = sk.BUDGET_SECONDS
    try:
        sk.BUDGET_SECONDS = -1.0
        k, tid, ev = _with_appdata(root, lambda: sk.classify(SID, env=DESKTOP))
        check("D2 budget spent, Desktop -> SCHEDULED, reason mentions budget",
              k == sk.SCHEDULED and "budget" in ev, "%s %s" % (k, ev))
        check("D3 budget spent, cli -> UNKNOWN",
              _with_appdata(root, lambda: sk.classify(SID, env=CLI))[0] == sk.UNKNOWN)
    finally:
        sk.BUDGET_SECONDS = saved


def test_mmap_fallback():
    # C9: if mmap fails, the fh.read fallback must still parse a matching record.
    sched = {"cliSessionId": SID, "scheduledTaskId": "ora-mm"}
    d = store([sched])
    real = sk.mmap.mmap
    for exc in (OSError, ValueError):
        def boom(*a, **kw):
            raise exc("mmap failed")
        sk.mmap.mmap = boom
        try:
            k, tid, ev = sk.classify(SID, env=CLI, dirs=[d])
        finally:
            sk.mmap.mmap = real
        check("M1 mmap raises %s: record still parsed -> SCHEDULED" % exc.__name__,
              k == sk.SCHEDULED and tid == "ora-mm", "%s %r" % (k, tid))


def test_prefilter():
    # Finding 2: files not containing the session id are never JSON-parsed.
    real = sk._parse_record
    calls = []

    def spy(raw):
        calls.append(len(raw))
        return real(raw)
    sk._parse_record = spy
    try:
        d = store(["{not json at all", {"cliSessionId": OTHER, "scheduledTaskId": "ora-x"},
                   {"cliSessionId": SID, "scheduledTaskId": "ora-y"}], ages=[1, 2, 3])
        k, tid, ev = sk.classify(SID, env=CLI, dirs=[d])
        check("P1 matching file still found through the prefilter",
              k == sk.SCHEDULED and tid == "ora-y", "%s %r" % (k, tid))
        check("P2 only the matching file was parsed", len(calls) == 1, repr(calls))
        calls[:] = []
        bom = chr(0xFEFF)
        d = store([bom + json.dumps({"cliSessionId": SID, "scheduledTaskId": "ora-b"})])
        check("P3 BOM file with matching id found",
              sk.classify(SID, env=CLI, dirs=[d])[1] == "ora-b" and len(calls) == 1)
        calls[:] = []
        # Documented residual: a JSON-escaped id evades the plain substring prefilter, but a
        # Desktop session still fails closed.
        esc = ('{"cliSessionId": "' + chr(92) + 'u0061aaaaaaa-1111-2222-3333-444444444444", '
               '"scheduledTaskId": "ora-esc"}')
        d = store([esc])
        check("P4 unicode-escaped id: not parsed (cli -> UNKNOWN), Desktop -> SCHEDULED",
              sk.classify(SID, env=CLI, dirs=[d])[0] == sk.UNKNOWN and not calls
              and sk.classify(SID, env=DESKTOP, dirs=[d])[0] == sk.SCHEDULED, repr(calls))
        calls[:] = []
        weird = 'sid"with' + chr(92) + 'escapes'
        d = store([{"cliSessionId": weird, "scheduledTaskId": "ora-w"}])
        sk.classify(weird, env=CLI, dirs=[d])
        check("P5 id with JSON-escapable chars skips the prefilter", len(calls) == 1, repr(calls))
    finally:
        sk._parse_record = real


def test_list_wrapped_decoy():
    # Finding 3: guards the isinstance(rec, dict) check.
    sched = {"cliSessionId": SID, "scheduledTaskId": "ora-pm-ledger"}
    d = store([json.dumps([{"cliSessionId": SID}]), sched], ages=[1, 5])
    k, tid, ev = sk.classify(SID, env=CLI, dirs=[d])
    check("L1 list-wrapped decoy + real scheduled record, cli -> SCHEDULED",
          k == sk.SCHEDULED and tid == "ora-pm-ledger", "%s %r" % (k, tid))


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
    test_duplicates()
    test_tampering()
    test_blanked_registry()
    test_junction_loop_and_dot_dirs()
    test_mmap_fallback()
    test_prefilter()
    test_list_wrapped_decoy()
    test_seam_and_hygiene()
    if _failures:
        print("\n%d FAILURE(S): %s" % (len(_failures), ", ".join(_failures[:12])))
        sys.exit(1)
    print("\nALL session-kind tests passed.")
    sys.exit(0)
