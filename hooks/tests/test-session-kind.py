"""Tests for hooks/lib/session_kind.py (R-06).

Run: python test-session-kind.py
Every case passes explicit dirs= and env=, so ambient machine state cannot flip a
result. Stdlib only. ASCII-only. Windows (`python`).
"""
import atexit
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
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


_TMP_DIRS = []


def _mkdtemp(prefix):
    """tempfile.mkdtemp that registers the dir for removal at exit (no fixture leaks)."""
    d = tempfile.mkdtemp(prefix=prefix)
    _TMP_DIRS.append(d)
    return d


def _rmtree(d):
    """Remove a fixture dir. Junctions/symlinks inside are removed as links first, never
    followed (the loop tests also rmdir their links in their own finally blocks)."""
    if not os.path.lexists(d):
        return
    for top, subdirs, _files in os.walk(d, topdown=True, followlinks=False):
        for name in list(subdirs):
            p = os.path.join(top, name)
            if os.path.islink(p) or (getattr(os.path, "isjunction", None)
                                     and os.path.isjunction(p)):
                _rm_loop(p)
                subdirs.remove(name)
    shutil.rmtree(d, ignore_errors=True)


def _cleanup_tmp():
    while _TMP_DIRS:
        _rmtree(_TMP_DIRS.pop())


atexit.register(_cleanup_tmp)


def store(records, ages=None):
    d = _mkdtemp("sk-store-")
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
        # C5: oversized + names this session + carries the key = evidence (no parse).
        check("K11 an oversized scheduled record is still evidence (cli -> SCHEDULED)",
              sk.classify(SID, env=CLI, dirs=[d])[0] == sk.SCHEDULED)
    finally:
        sk.MAX_RECORD_BYTES = saved
    d = store([{"cliSessionId": SID, "scheduledTaskId": "../../evil"}])
    k, tid, ev = sk.classify(SID, env=DESKTOP, dirs=[d])
    check("K12 an unsafe task id still means SCHEDULED but yields no task id",
          k == sk.SCHEDULED and tid is None, "%s %r" % (k, tid))
    # C4: UNKNOWN only for open (cli/vscode/unset) entrypoints.
    check("K13 empty session id, Desktop -> SCHEDULED",
          sk.classify("", env=DESKTOP, dirs=[d])[0] == sk.SCHEDULED)
    check("K14 non-str session id, Desktop -> SCHEDULED",
          sk.classify(None, env=DESKTOP, dirs=[d])[0] == sk.SCHEDULED)
    check("K14b empty / non-str session id, cli -> UNKNOWN",
          sk.classify("", env=CLI, dirs=[d])[0] == sk.UNKNOWN
          and sk.classify(None, env=CLI, dirs=[d])[0] == sk.UNKNOWN)
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
        # C5: padded / list-wrapped records naming this session with the key are evidence
        # under any entrypoint; a renamed cliSessionId key is the documented residual (a).
        want = sk.UNKNOWN if label == "cliSessionId key rename" else sk.SCHEDULED
        k = sk.classify(SID, env=CLI, dirs=[d])[0]
        check("T2 %s under cli -> %s" % (label, want), k == want, k)
    k, tid, ev = sk.classify(SID, env={"CLAUDE_CODE_ENTRYPOINT": "Claude-Desktop"},
                             dirs=[tampered["list-wrap"]])
    check("T3 entrypoint match is case-insensitive", k == sk.SCHEDULED and tid is None, k)
    no_rec = tampered["cliSessionId key rename"]
    check("T4 desktop with no record: reason names fail closed",
          "fail closed" in sk.classify(SID, env=DESKTOP, dirs=[no_rec])[2])
    check("T5 desktop, empty session id -> SCHEDULED (C4: closed entrypoint)",
          sk.classify("", env=DESKTOP, dirs=[no_rec])[0] == sk.SCHEDULED)
    check("T6 no entrypoint at all, no record -> UNKNOWN",
          sk.classify(SID, env={}, dirs=[no_rec])[0] == sk.UNKNOWN)
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
            root = _mkdtemp("sk-appdata-")
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
        root = _mkdtemp("sk-appdata-")
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
    root = _mkdtemp("sk-appdata-")
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


def test_no_mmap():
    # C13: an ACCESS_READ mmap blocked the app's writeFileSync of the record; plain reads only.
    check("M1 session_kind does not use mmap", not hasattr(sk, "mmap"))
    sched = {"cliSessionId": SID, "scheduledTaskId": "ora-mm"}
    d = store([sched])
    k, tid, ev = sk.classify(SID, env=CLI, dirs=[d])
    check("M1b record read with plain open() -> SCHEDULED with task id",
          k == sk.SCHEDULED and tid == "ora-mm", "%s %r" % (k, tid))


def _write_padded(path, rec_head, pad_bytes, chunk=1 << 20):
    """JSON record {...rec_head, "pad": "aaa..."} with pad_bytes of padding, chunked."""
    head = json.dumps(rec_head)[:-1] + ', "pad": "'
    with open(path, "wb") as fh:
        fh.write(head.encode("ascii"))
        left = pad_bytes
        block = b"a" * chunk
        while left > 0:
            n = min(left, chunk)
            fh.write(block[:n])
            left -= n
        fh.write(b'"}')


class _CountingFile(object):
    """File wrapper that counts the bytes session_kind reads through it."""

    def __init__(self, fh, owner):
        self._fh = fh
        self._owner = owner

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self._fh.close()
        return False

    def read(self, *a):
        b = self._fh.read(*a)
        self._owner.total += len(b)
        return b

    def fileno(self):
        return self._fh.fileno()

    def close(self):
        self._fh.close()


class _CountingOpen(object):
    """Stands in for builtins.open inside session_kind: counts opens and bytes read."""

    def __init__(self):
        self.total = 0
        self.opens = 0

    def __call__(self, path, *a, **kw):
        self.opens += 1
        return _CountingFile(open(path, *a, **kw), self)


def test_prefix_byte_count():
    # C7: deterministic replacement for the old timing tests. Every non-candidate file is
    # read only to PREFIX_BYTES + 1, whatever its size, so the total bytes read are bounded
    # by files * (PREFIX_BYTES + 1) + the own record. Any whole-file scan reads ~3.2 MB of
    # the 64 KB records alone and fails the bound; no timing dependence.
    check("PB1 PREFIX_BYTES is pinned at 16384", sk.PREFIX_BYTES == 16384, repr(sk.PREFIX_BYTES))
    d = _mkdtemp("sk-bytes-")
    counter = _CountingOpen()
    try:
        for i in range(50):
            rec = {"cliSessionId": "cccccccc-0000-0000-0000-%012d" % i, "title": "x"}
            if i % 7 == 0:
                rec["scheduledTaskId"] = "ora-other-%d" % i
            _write_padded(os.path.join(d, "local_%03d.json" % i), rec, 64 * 1024)
        # One large decoy of another session (4 MB; non-candidate: never read past the prefix).
        _write_padded(os.path.join(d, "local_decoy.json"),
                      {"cliSessionId": OTHER, "scheduledTaskId": "ora-x"}, 4 * 1024 * 1024)
        mine = os.path.join(d, "local_mine.json")
        with open(mine, "w", encoding="utf-8") as fh:
            json.dump({"cliSessionId": SID, "title": "me"}, fh)
        files = 52
        own = os.path.getsize(mine)
        sk.open = counter
        try:
            k, tid, ev = sk.classify(SID, env=DESKTOP, dirs=[d])
        finally:
            del sk.open
        bound = files * (sk.PREFIX_BYTES + 1) + own
        check("BC1 51 other-session records + own record, Desktop -> INTERACTIVE",
              k == sk.INTERACTIVE, "%s %s" % (k, ev))
        check("BC2 bytes read <= files*(PREFIX_BYTES+1) + own size (%d <= %d)"
              % (counter.total, bound), 0 < counter.total <= bound)
        check("BC3 each file opened exactly once (complete first attempt, no retry)",
              counter.opens == files, repr(counter.opens))
    finally:
        try:
            del sk.open
        except AttributeError:
            pass
        _rmtree(d)


def test_hard_max():
    # C2: a CANDIDATE file larger than HARD_MAX_BYTES is not read: incomplete scan.
    check("HM0 HARD_MAX_BYTES is set and >= MAX_RECORD_BYTES",
          getattr(sk, "HARD_MAX_BYTES", 0) >= sk.MAX_RECORD_BYTES)
    saved = sk.HARD_MAX_BYTES
    try:
        sk.HARD_MAX_BYTES = 2 * sk.PREFIX_BYTES
        big = 3 * sk.PREFIX_BYTES
        with tempfile.TemporaryDirectory(prefix="sk-hm-") as d:
            _write_padded(os.path.join(d, "local_big.json"), {"cliSessionId": SID}, big)
            with open(os.path.join(d, "local_mine.json"), "w", encoding="utf-8") as fh:
                json.dump({"cliSessionId": SID}, fh)
            k, tid, ev = sk.classify(SID, env=DESKTOP, dirs=[d])
            check("HM1 candidate over HARD_MAX_BYTES, Desktop -> SCHEDULED (incomplete)",
                  k == sk.SCHEDULED and "incomplete" in ev, "%s %s" % (k, ev))
            check("HM2 candidate over HARD_MAX_BYTES, cli -> UNKNOWN",
                  sk.classify(SID, env=CLI, dirs=[d])[0] == sk.UNKNOWN)
        with tempfile.TemporaryDirectory(prefix="sk-hm-") as d:
            # Non-candidate (other session, id in prefix) over the cap: never read, no effect.
            _write_padded(os.path.join(d, "local_big.json"), {"cliSessionId": OTHER}, big)
            with open(os.path.join(d, "local_mine.json"), "w", encoding="utf-8") as fh:
                json.dump({"cliSessionId": SID}, fh)
            check("HM3 non-candidate over HARD_MAX_BYTES, Desktop -> INTERACTIVE",
                  sk.classify(SID, env=DESKTOP, dirs=[d])[0] == sk.INTERACTIVE)
    finally:
        sk.HARD_MAX_BYTES = saved


def test_prefix_candidates():
    # Candidate rules: id beyond the prefix in a file whose prefix names another session
    # is the documented residual; these cases must still be candidates.
    pb = sk.PREFIX_BYTES
    sched = {"cliSessionId": SID, "scheduledTaskId": "ora-late"}
    forged = {"cliSessionId": SID}
    # (a) no cliSessionId key in the prefix: candidate, full read finds the late key.
    late = '{"pad": "' + "a" * (pb + 100) + '", ' + json.dumps(sched)[1:]
    d = store([late, forged], ages=[100, 5])
    check("PC1 cliSessionId past the prefix, no key in prefix -> candidate -> SCHEDULED",
          sk.classify(SID, env=DESKTOP, dirs=[d])[0] == sk.SCHEDULED)
    # (b) escape marker only past... in prefix: candidate.
    bs = chr(92)
    esc = ('{"cliSessionId": "' + bs + 'u0061' + SID[1:] + '", "pad": "'
           + "a" * (pb + 100) + '", "scheduledTaskId": "ora-e"}')
    d = store([esc, forged], ages=[100, 5])
    check("PC2 escaped id in prefix, key past the prefix -> SCHEDULED",
          sk.classify(SID, env=DESKTOP, dirs=[d])[0] == sk.SCHEDULED)
    # (c) id in prefix, scheduledTaskId far past the prefix (live: up to ~1.2 MB in).
    far = json.dumps(forged)[:-1] + ', "pad": "' + "a" * (pb * 4) + '", "scheduledTaskId": "f"}'
    d = store([far, forged], ages=[100, 5])
    check("PC3 id in prefix, scheduledTaskId deep in the file -> SCHEDULED",
          sk.classify(SID, env=DESKTOP, dirs=[d])[0] == sk.SCHEDULED)
    # (d) prefix cut mid multi-byte UTF-8 char is not "undecodable".
    head = '{"cliSessionId": "' + OTHER + '", "t": "'
    fill = "a" * (pb - len(head) - 1) + chr(0xe9) * 10
    raw = (head + fill + '"}').encode("utf-8")[:pb]
    needle = SID.encode("ascii")
    check("PC4 prefix ending mid UTF-8 char, other session -> NOT a candidate",
          sk._is_candidate(raw, needle, False) is False)
    check("PC4b same bytes as a complete (short) file -> candidate (undecodable)",
          sk._is_candidate(raw, needle, True) is True)
    plain_other = json.dumps({"cliSessionId": OTHER, "x": 1}).encode()
    check("PC5 clean other-session prefix -> not a candidate",
          sk._is_candidate(plain_other, needle, True) is False)
    check("PC6 list-wrapped -> candidate",
          sk._is_candidate(b"[" + plain_other + b"]", needle, True) is True)
    check("PC7 BOM + whitespace before '{' is still a normal object start",
          sk._is_candidate(b"\xef\xbb\xbf \n" + plain_other, needle, True) is False)
    check("PC8 UTF-16 (NUL in first 4 bytes) -> candidate",
          sk._is_candidate(json.dumps({"cliSessionId": OTHER}).encode("utf-16"), needle, True))
    check("PC9 needle None (escapable id) -> every file is a candidate",
          sk._is_candidate(plain_other, None, True) is True)
    check("PC10 own id in prefix -> candidate", sk._is_candidate(
        json.dumps({"cliSessionId": SID}).encode(), needle, True) is True)


def test_c11_unlistable_dir():
    # C11: a record dir that exists but cannot be listed leaves the scan incomplete.
    good = store([{"cliSessionId": SID}])
    bad = store([{"cliSessionId": SID, "scheduledTaskId": "ora-hidden"}])
    real = sk.os.scandir

    def deny(path, *a, **kw):
        if os.path.normcase(os.path.abspath(path)) == os.path.normcase(os.path.abspath(bad)):
            raise PermissionError("denied")
        return real(path, *a, **kw)
    sk.os.scandir = deny
    try:
        k, tid, ev = sk.classify(SID, env=DESKTOP, dirs=[good, bad])
        check("C11 unlistable record dir under claude-desktop -> SCHEDULED",
              k == sk.SCHEDULED and "incomplete" in ev, "%s %s" % (k, ev))
        check("C11b unlistable record dir under cli -> UNKNOWN",
              sk.classify(SID, env=CLI, dirs=[good, bad])[0] == sk.UNKNOWN)
    finally:
        sk.os.scandir = real


def test_budget_inside_judge():
    # C2: the budget is checked inside _judge too (between parse and later steps).
    d = store([{"cliSessionId": SID}])
    real = sk._parse_record
    saved = sk.BUDGET_SECONDS

    def slow(raw):
        time.sleep(0.25)
        return real(raw)
    sk._parse_record = slow
    try:
        sk.BUDGET_SECONDS = 0.1
        k, tid, ev = sk.classify(SID, env=DESKTOP, dirs=[d])
        check("BJ1 budget expires inside the judge, Desktop -> SCHEDULED (budget)",
              k == sk.SCHEDULED and "budget" in ev, "%s %s" % (k, ev))
    finally:
        sk._parse_record = real
        sk.BUDGET_SECONDS = saved
    # BJ2: a slow PRE-parse step (candidate check) spends the budget; the in-judge
    # pre-parse check must stop before the parse (mutation nojudgebudget).
    real_cand = sk._is_candidate
    calls = []

    def slow_cand(*a, **kw):
        time.sleep(0.3)
        return real_cand(*a, **kw)

    def spy(raw):
        calls.append(len(raw))
        return real(raw)
    sk._is_candidate = slow_cand
    sk._parse_record = spy
    try:
        sk.BUDGET_SECONDS = 0.1
        k, tid, ev = sk.classify(SID, env=DESKTOP, dirs=[d])
        check("BJ2 budget spent before the parse, Desktop -> SCHEDULED (budget), no parse",
              k == sk.SCHEDULED and "budget" in ev and not calls,
              "%s %s %r" % (k, ev, calls))
    finally:
        sk._is_candidate = real_cand
        sk._parse_record = real
        sk.BUDGET_SECONDS = saved


class _Gate(object):
    """Stands in for builtins.open inside session_kind. For `victim` it can block on an
    Event (block=True), sleep (delay), or raise PermissionError, either on every open or
    only on the first `times` opens. Counts victim opens."""

    def __init__(self, victim, block=False, delay=0.0, error=False, times=None):
        self.victim = os.path.normcase(victim)
        self.block, self.delay, self.error, self.times = block, delay, error, times
        self.release = threading.Event()
        self.hits = 0

    def __call__(self, path, *a, **kw):
        if os.path.normcase(path) == self.victim:
            self.hits += 1
            if self.times is None or self.hits <= self.times:
                if self.block:
                    self.release.wait(30.0)
                if self.delay:
                    time.sleep(self.delay)
                if self.error:
                    raise PermissionError("transient")
        return open(path, *a, **kw)


def test_hard_join_and_retry():
    # C5: one blocking open()/read() cannot be interrupted by the between-operations
    # budget; classify runs the scan in a daemon thread joined with HARD_JOIN_SECONDS.
    check("HJ0 HARD_JOIN_SECONDS > BUDGET_SECONDS and well under the 60 s guard timeout",
          sk.BUDGET_SECONDS < getattr(sk, "HARD_JOIN_SECONDS", 0) <= 30.0,
          repr(getattr(sk, "HARD_JOIN_SECONDS", None)))
    saved = (sk.BUDGET_SECONDS, getattr(sk, "HARD_JOIN_SECONDS", None))
    d = store([{"cliSessionId": SID}, {"cliSessionId": OTHER, "note": SID}], ages=[5, 10])
    mine = os.path.join(d, "local_00.json")
    gates = []
    try:
        # HJ1-2: persistent block (Event never set during the call) on our own record.
        sk.BUDGET_SECONDS, sk.HARD_JOIN_SECONDS = 0.3, 0.6
        for label, env, want in (("Desktop", DESKTOP, sk.SCHEDULED), ("cli", CLI, sk.UNKNOWN)):
            g = _Gate(mine, block=True)
            gates.append(g)
            sk.open = g
            t0 = time.time()
            k, tid, ev = sk.classify(SID, env=env, dirs=[d])
            dt = time.time() - t0
            check("HJ1 blocking open past HARD_JOIN, %s -> %s" % (label, want),
                  k == want, "%s %s" % (k, ev))
            check("HJ2 blocking open: %s returns within HARD_JOIN + 1 s (%.2fs)" % (label, dt),
                  dt < sk.HARD_JOIN_SECONDS + 1.0)
        # HJ3: a transient one-time stall longer than the budget, then success on retry.
        sk.BUDGET_SECONDS, sk.HARD_JOIN_SECONDS = 0.2, 5.0
        g = _Gate(mine, delay=0.5, times=1)
        sk.open = g
        k, tid, ev = sk.classify(SID, env=DESKTOP, dirs=[d])
        check("HJ3 transient first-open stall, retry succeeds -> INTERACTIVE",
              k == sk.INTERACTIVE and g.hits == 2, "%s %s hits=%d" % (k, ev, g.hits))
        # HJ4: a transient one-time read error, then success on retry.
        g = _Gate(mine, error=True, times=1)
        sk.open = g
        k, tid, ev = sk.classify(SID, env=DESKTOP, dirs=[d])
        check("HJ4 transient read error, retry succeeds -> INTERACTIVE",
              k == sk.INTERACTIVE and g.hits == 2, "%s %s hits=%d" % (k, ev, g.hits))
        # HJ5-6: a stall that persists across attempts (longer than the budget every time):
        # never INTERACTIVE, and the retry is bounded (two attempts).
        for label, env, want in (("Desktop", DESKTOP, sk.SCHEDULED), ("cli", CLI, sk.UNKNOWN)):
            g = _Gate(mine, delay=0.3)
            sk.open = g
            k, tid, ev = sk.classify(SID, env=env, dirs=[d])
            check("HJ5 persistent stall, %s -> %s (never INTERACTIVE)" % (label, want),
                  k == want, "%s %s" % (k, ev))
            check("HJ6 persistent stall, %s: exactly 2 attempts" % label, g.hits == 2,
                  repr(g.hits))
        # HJ7: a persistent read error: never INTERACTIVE, two attempts.
        g = _Gate(mine, error=True)
        sk.open = g
        k, tid, ev = sk.classify(SID, env=CLI, dirs=[d])
        check("HJ7 persistent read error, cli -> UNKNOWN after 2 attempts",
              k == sk.UNKNOWN and g.hits == 2, "%s %s hits=%d" % (k, ev, g.hits))
        # HJ8: scheduled evidence ends the call at once: no retry even though an unreadable
        # (newer) file made the first attempt incomplete.
        ds = store([{"cliSessionId": OTHER, "x": SID}, {"cliSessionId": SID,
                    "scheduledTaskId": "ora-early"}], ages=[5, 10])
        g = _Gate(os.path.join(ds, "local_00.json"), error=True)
        sk.open = g
        real_scan = sk.scan
        scans = []

        def spy_scan(*a, **kw):
            scans.append(1)
            return real_scan(*a, **kw)
        sk.scan = spy_scan
        try:
            k, tid, ev = sk.classify(SID, env=CLI, dirs=[ds])
        finally:
            sk.scan = real_scan
        check("HJ8 scheduled evidence -> SCHEDULED with task id, one attempt (no retry)",
              k == sk.SCHEDULED and tid == "ora-early" and len(scans) == 1,
              "%s %r scans=%d" % (k, tid, len(scans)))
        # HJ9: after the abandoned threads are released, a fresh call is unaffected.
        for g in gates:
            g.release.set()
        time.sleep(0.2)
        del sk.open
        sk.BUDGET_SECONDS, sk.HARD_JOIN_SECONDS = saved
        check("HJ9 after released stalls, a normal call -> INTERACTIVE",
              sk.classify(SID, env=DESKTOP, dirs=[d])[0] == sk.INTERACTIVE)
    finally:
        for g in gates:
            g.release.set()
        try:
            del sk.open
        except AttributeError:
            pass
        sk.BUDGET_SECONDS = saved[0]
        if saved[1] is not None:
            sk.HARD_JOIN_SECONDS = saved[1]


def test_c6_other_session_oversized():
    # C6: an oversized candidate whose prefix cleanly names ANOTHER session is skipped, so
    # one large other-session record cannot make every session falsely SCHEDULED.
    saved = sk.HARD_MAX_BYTES
    big = 3 * sk.PREFIX_BYTES
    bs = chr(92)
    try:
        sk.HARD_MAX_BYTES = 2 * sk.PREFIX_BYTES
        cases = (
            # (label, head dict or raw head str, want Desktop verdict)
            ("HM4 other session's oversized record mentioning our id -> skipped",
             {"cliSessionId": OTHER, "note": SID}, sk.INTERACTIVE),
            ("HM5 attack: oversized record naming OUR id -> incomplete",
             {"cliSessionId": SID, "note": "x"}, sk.SCHEDULED),
            ("HM6 oversized, duplicate cliSessionId keys (other, ours) -> incomplete",
             '{"cliSessionId": "%s", "cliSessionId": "%s", "note": "%s"' % (OTHER, SID, SID),
             sk.SCHEDULED),
            ("HM7 oversized, escape marker in the prefix -> incomplete",
             '{"cliSessionId": "%s", "note": "%su0061 %s"' % (OTHER, bs, SID), sk.SCHEDULED),
            ("HM8 oversized, empty cliSessionId value -> incomplete",
             '{"cliSessionId": "", "note": "%s"' % SID, sk.SCHEDULED),
            ("HM9 oversized, list-wrapped -> incomplete",
             '[{"cliSessionId": "%s", "note": "%s"' % (OTHER, SID), sk.SCHEDULED),
        )
        for label, head, want in cases:
            d = _mkdtemp("sk-c6-")
            p = os.path.join(d, "local_big.json")
            if isinstance(head, dict):
                _write_padded(p, head, big)
            else:
                with open(p, "wb") as fh:
                    fh.write(head.encode("ascii") + b', "pad": "' + b"a" * big + b'"}')
            with open(os.path.join(d, "local_mine.json"), "w", encoding="utf-8") as fh:
                json.dump({"cliSessionId": SID}, fh)
            k, tid, ev = sk.classify(SID, env=DESKTOP, dirs=[d])
            check(label + " (Desktop -> %s)" % want, k == want, "%s %s" % (k, ev))
            if want == sk.SCHEDULED:
                kc = sk.classify(SID, env=CLI, dirs=[d])[0]
                check(label + " (cli -> unknown)", kc == sk.UNKNOWN, kc)
    finally:
        sk.HARD_MAX_BYTES = saved
    # Unit: _names_other on prefixes.
    no = getattr(sk, "_names_other", None)
    check("HM10 _names_other exists", no is not None)
    if no is not None:
        p1 = ('{"cliSessionId": "%s", "x": "%s"' % (OTHER, SID)).encode()
        check("HM10b clean other-session prefix -> True", no(p1, SID) is True)
        p2 = ('{"cliSessionId": "%s"' % SID).encode()
        check("HM10c own-id prefix -> False", no(p2, SID) is False)
        p3 = b"\xef\xbb\xbf " + p1
        check("HM10d BOM + whitespace still clean -> True", no(p3, SID) is True)
        p4 = p1 + b"\xff"
        check("HM10e invalid UTF-8 -> False", no(p4, SID) is False)


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
        # C5: a JSON-escaped id is caught by the escape marker and parsed (residual closed).
        esc = ('{"cliSessionId": "' + chr(92) + 'u0061aaaaaaa-1111-2222-3333-444444444444", '
               '"scheduledTaskId": "ora-esc"}')
        d = store([esc])
        k, tid, ev = sk.classify(SID, env=CLI, dirs=[d])
        check("P4 unicode-escaped id: parsed once, cli -> SCHEDULED with the task id",
              k == sk.SCHEDULED and tid == "ora-esc" and len(calls) == 1,
              "%s %r %r" % (k, tid, calls))
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


def _bstore(blobs, ages=None):
    """Like store() but writes raw bytes (for undecodable / non-UTF-8 records)."""
    d = _mkdtemp("sk-store-")
    for i, b in enumerate(blobs):
        p = os.path.join(d, "local_%02d.json" % i)
        with open(p, "wb") as fh:
            fh.write(b)
        if ages and ages[i]:
            old = time.time() - ages[i]
            os.utime(p, (old, old))
    return d


def test_c5_tamper_holes():
    # Reviewer probes atk.py / atk3.py: a REAL scheduled record plus a FORGED fresh plain
    # record (newest). Before the fix each returned INTERACTIVE.
    real = {"cliSessionId": SID, "scheduledTaskId": "nightly-x"}
    forged = json.dumps({"cliSessionId": SID}).encode()
    base = json.dumps(real).encode()
    bs = chr(92).encode()
    esc_id = (b'{"cliSessionId": "' + bs + b'u0061' + SID[1:].encode()
              + b'", "scheduledTaskId": "nightly-x"}')
    esc_key = (b'{"cliSessionId": "' + SID.encode() + b'", "scheduled' + bs
               + b'u0054askId": "nightly-x"}')
    cases = (("A1 padded past the cap", base + b" " * (sk.MAX_RECORD_BYTES + 10)),
             ("A2 wrapped in a list", b"[" + base + b"]"),
             ("A3 id written with a unicode escape", esc_id),
             ("A3b scheduledTaskId key written with a unicode escape", esc_key),
             ("A5 UTF-16 encoded record", json.dumps(real).encode("utf-16")))
    for label, blob in cases:
        d = _bstore([blob, forged], ages=[100, 5])
        for env_name, env in (("desktop", DESKTOP), ("cli", CLI)):
            k = sk.classify(SID, env=env, dirs=[d])[0]
            check("C5 %s + forged fresh plain record, %s -> SCHEDULED" % (label, env_name),
                  k == sk.SCHEDULED, k)
    d = _bstore([esc_id])
    k, tid, ev = sk.classify(SID, env=CLI, dirs=[d])
    check("C5 escaped-id record alone is parsed and yields the task id",
          k == sk.SCHEDULED and tid == "nightly-x", "%s %r" % (k, tid))
    # Undecodable bytes plus scheduledTaskId, fresh: fail closed under Desktop only.
    undec = b'{"x": "\xff\xfe\xfd", "scheduledTaskId": "nightly-x"}'
    d = _bstore([undec, forged], ages=[100, 5])
    check("C5 fresh undecodable file with scheduledTaskId, Desktop -> SCHEDULED",
          sk.classify(SID, env=DESKTOP, dirs=[d])[0] == sk.SCHEDULED)
    check("C5 fresh undecodable file with scheduledTaskId, cli -> INTERACTIVE",
          sk.classify(SID, env=CLI, dirs=[d])[0] == sk.INTERACTIVE)
    d = _bstore([undec, forged], ages=[8 * 86400, 5])
    check("C5 stale undecodable file with scheduledTaskId does not flip Desktop",
          sk.classify(SID, env=DESKTOP, dirs=[d])[0] == sk.INTERACTIVE)
    # Undecodable file that names this session and carries the key: evidence anywhere.
    undec_own = (b'{"cliSessionId": "' + SID.encode()
                 + b'", "x": "\xff", "scheduledTaskId": "nightly-x"}')
    d = _bstore([undec_own, forged], ages=[8 * 86400, 5])
    check("C5 undecodable stale file naming this session with the key -> SCHEDULED (cli)",
          sk.classify(SID, env=CLI, dirs=[d])[0] == sk.SCHEDULED)


def test_c5_negatives():
    # Another session's records must NOT flip this session.
    other_sched = {"cliSessionId": OTHER, "scheduledTaskId": "ora-other"}
    mine = {"cliSessionId": SID}
    d = store([other_sched, mine], ages=[10, 5])
    check("N1 other session's clean scheduled record does not flip this one (Desktop)",
          sk.classify(SID, env=DESKTOP, dirs=[d])[0] == sk.INTERACTIVE)
    big_other = json.dumps(other_sched) + " " * (sk.MAX_RECORD_BYTES + 10)
    d = store([big_other, mine], ages=[10, 5])
    check("N2 other session's oversized scheduled record does not flip this one",
          sk.classify(SID, env=DESKTOP, dirs=[d])[0] == sk.INTERACTIVE)
    d = store([json.dumps([other_sched]), "{broken " + json.dumps(other_sched), mine],
              ages=[10, 11, 5])
    check("N3 other session's list-wrapped / broken scheduled records do not flip this one",
          sk.classify(SID, env=DESKTOP, dirs=[d])[0] == sk.INTERACTIVE)
    bs = chr(92)
    esc_other = ('{"cliSessionId": "' + bs + 'u0062' + OTHER[1:]
                 + '", "scheduledTaskId": "ora-other"}')
    d = store([esc_other, mine], ages=[10, 5])
    check("N4 other session's escaped-id scheduled record does not flip this one",
          sk.classify(SID, env=DESKTOP, dirs=[d])[0] == sk.INTERACTIVE)


def test_c4_entrypoints():
    empty = store([])
    for ep in ("local-agent", "github-action", "remote", "bench", "claude-desktop-3p",
               "mcp", "something-new", "LOCAL-AGENT"):
        k = sk.classify(SID, env={"CLAUDE_CODE_ENTRYPOINT": ep}, dirs=[empty])[0]
        check("C4 entrypoint %r, no record -> SCHEDULED (fail closed)" % ep,
              k == sk.SCHEDULED, k)
    for ep in ("cli", "CLI", "vscode", "claude-vscode", "", "  "):
        k = sk.classify(SID, env={"CLAUDE_CODE_ENTRYPOINT": ep}, dirs=[empty])[0]
        check("C4 entrypoint %r, no record -> UNKNOWN" % ep, k == sk.UNKNOWN, k)
    check("C4 unset entrypoint, no record -> UNKNOWN",
          sk.classify(SID, env={}, dirs=[empty])[0] == sk.UNKNOWN)
    check("C4 local-agent, empty session id -> SCHEDULED",
          sk.classify("", env={"CLAUDE_CODE_ENTRYPOINT": "local-agent"}, dirs=[empty])[0]
          == sk.SCHEDULED)
    check("C4 cli, empty session id -> UNKNOWN",
          sk.classify("", env=CLI, dirs=[empty])[0] == sk.UNKNOWN)
    d = store([{"cliSessionId": SID}])
    check("C4 local-agent with a fresh plain record -> INTERACTIVE",
          sk.classify(SID, env={"CLAUDE_CODE_ENTRYPOINT": "local-agent"}, dirs=[d])[0]
          == sk.INTERACTIVE)


def _lams_root(rec):
    root = _mkdtemp("sk-appdata-")
    rd = os.path.join(root, "Claude", "local-agent-mode-sessions", "g1", "g2")
    os.makedirs(rd)
    with open(os.path.join(rd, "local_cw.json"), "w", encoding="utf-8") as fh:
        json.dump(rec, fh)
    return root, rd


def test_c4_lams_store():
    root, rd = _lams_root({"sessionId": "local_x", "processName": "p", "cliSessionId": SID,
                           "scheduledTaskId": "cowork-task"})
    k, tid, ev = _with_appdata(root, lambda: sk.classify(SID, env=CLI))
    check("W1 Cowork (local-agent-mode-sessions) scheduled record, cli -> SCHEDULED",
          k == sk.SCHEDULED and tid == "cowork-task", "%s %r" % (k, tid))
    dirs = _with_appdata(root, lambda: sk.store_dirs())
    check("W2 store_dirs includes the local-agent-mode-sessions record dir",
          os.path.normcase(rd) in [os.path.normcase(x) for x in dirs], repr(dirs))
    root, rd = _lams_root({"cliSessionId": SID})
    k = _with_appdata(root, lambda: sk.classify(
        SID, env={"CLAUDE_CODE_ENTRYPOINT": "local-agent"}))[0]
    check("W3 Cowork plain record, local-agent -> INTERACTIVE", k == sk.INTERACTIVE, k)


class _SlowOpen(object):
    """Stands in for builtins.open inside session_kind: sleeps per open, counts opens."""

    def __init__(self, delay):
        self.delay = delay
        self.paths = []

    def __call__(self, path, *a, **kw):
        self.paths.append(path)
        time.sleep(self.delay)
        return open(path, *a, **kw)


def test_c3_slow_store():
    # Reviewer finding C3: on a slow (cold) store the 3 s budget ran out and a session was
    # misclassified. Monkeypatched slow reader; the budget is shrunk to keep the test fast.
    saved = sk.BUDGET_SECONDS
    slow = _SlowOpen(0.02)
    try:
        sk.BUDGET_SECONDS = 0.2
        sk.open = slow
        # 30 files; the scheduled record is the NEWEST but sorts last by name.
        recs = [{"cliSessionId": "cccccccc-0000-0000-0000-%012d" % i} for i in range(29)]
        recs.append({"cliSessionId": SID, "scheduledTaskId": "ora-slow"})
        ages = [1000 + i for i in range(29)] + [1]
        d = store(recs, ages)
        k, tid, ev = sk.classify(SID, env=DESKTOP, dirs=[d])
        check("S1 slow store: newest scheduled record found before the budget, task id kept",
              k == sk.SCHEDULED and tid == "ora-slow", "%s %r %s" % (k, tid, ev))
        check("S2 slow store: scan stops at the scheduled record (1 file opened)",
              len(slow.paths) == 1, repr(len(slow.paths)))
        # Our plain record is newest; the rest cannot all be read inside the budget.
        recs = [{"cliSessionId": SID}] + [
            {"cliSessionId": "cccccccc-0000-0000-0000-%012d" % i, "pad": SID} for i in range(29)]
        ages = [1] + [1000 + i for i in range(29)]
        d = store(recs, ages)
        slow.paths[:] = []
        k, tid, ev = sk.classify(SID, env=CLI, dirs=[d])
        check("S3 partial scan with a plain match, cli -> UNKNOWN, never INTERACTIVE",
              k == sk.UNKNOWN, "%s %s" % (k, ev))
        k, tid, ev = sk.classify(SID, env=DESKTOP, dirs=[d])
        check("S4 partial scan with a plain match, Desktop -> SCHEDULED (budget)",
              k == sk.SCHEDULED and "budget" in ev, "%s %s" % (k, ev))
        sk.BUDGET_SECONDS = 30.0
        check("S5 same store with enough budget -> INTERACTIVE",
              sk.classify(SID, env=DESKTOP, dirs=[d])[0] == sk.INTERACTIVE)
    finally:
        sk.BUDGET_SECONDS = saved
        try:
            del sk.open
        except AttributeError:
            pass
    check("S6 budget is generous for a cold live store but under the 60 s guard timeout",
          8.0 <= sk.BUDGET_SECONDS <= 30.0, repr(sk.BUDGET_SECONDS))


def test_unreadable_file():
    # A candidate file that cannot be opened (not merely gone) leaves coverage incomplete.
    d = store([{"cliSessionId": SID}, {"cliSessionId": OTHER}], ages=[5, 10])
    victim = os.path.join(d, "local_01.json")

    def deny(path, *a, **kw):
        if os.path.normcase(path) == os.path.normcase(victim):
            raise PermissionError("denied")
        return open(path, *a, **kw)
    sk.open = deny
    try:
        check("U1 unreadable candidate, Desktop -> SCHEDULED (incomplete scan)",
              sk.classify(SID, env=DESKTOP, dirs=[d])[0] == sk.SCHEDULED)
        check("U2 unreadable candidate, cli -> UNKNOWN (never INTERACTIVE)",
              sk.classify(SID, env=CLI, dirs=[d])[0] == sk.UNKNOWN)
    finally:
        del sk.open


class _Script(object):
    """open() stand-in for session_kind driven by a per-path script: path -> list of
    actions, one per open of that path (last action repeats). An action is "ok", "error"
    (PermissionError), "gone" (FileNotFoundError), "block" (Event.wait, bounded by `cap`),
    or ("sleep_error", seconds). `on_error` is called when an "error" action fires."""

    def __init__(self, scripts, cap=8.0, on_error=None):
        self.scripts = dict((os.path.normcase(k), v) for k, v in scripts.items())
        self.counts = {}
        self.cap = cap
        self.on_error = on_error
        self.release = threading.Event()

    def __call__(self, path, *a, **kw):
        key = os.path.normcase(path)
        acts = self.scripts.get(key)
        if acts:
            n = self.counts.get(key, 0)
            self.counts[key] = n + 1
            act = acts[min(n, len(acts) - 1)]
            if act == "error":
                if self.on_error:
                    self.on_error()
                raise PermissionError("scripted")
            if act == "gone":
                raise FileNotFoundError("scripted")
            if act == "block":
                self.release.wait(self.cap)
            if isinstance(act, tuple) and act[0] == "sleep_error":
                time.sleep(act[1])
                raise PermissionError("scripted")
        return open(path, *a, **kw)


def test_clock_step_back():
    # A wall-clock step backwards (NTP/manual/VM resume) must not stretch the deadlines:
    # they run on time.monotonic(). Attempt 1 ends with a read error and the wall clock
    # then jumps back 30 s; attempt 2 blocks. With time.time() deadlines the join would wait
    # ~HARD_JOIN + 30 s; with monotonic it ends at ~HARD_JOIN.
    saved = (sk.BUDGET_SECONDS, sk.HARD_JOIN_SECONDS)
    real_time = time.time
    off = [0.0]
    d = store([{"cliSessionId": SID}, {"cliSessionId": OTHER}], ages=[5, 10])
    mine = os.path.join(d, "local_00.json")
    sc = _Script({mine: ["error", "block"]}, cap=8.0,
                 on_error=lambda: off.__setitem__(0, -30.0))
    try:
        sk.BUDGET_SECONDS, sk.HARD_JOIN_SECONDS = 1.0, 2.0
        sk.open = sc
        sk.time.time = lambda: real_time() + off[0]
        t0 = time.monotonic()
        k, tid, ev = sk.classify(SID, env=DESKTOP, dirs=[d])
        dt = time.monotonic() - t0
    finally:
        sk.time.time = real_time
        sc.release.set()
        del sk.open
        sk.BUDGET_SECONDS, sk.HARD_JOIN_SECONDS = saved
    check("CS1 wall clock steps back 30 s mid-call: Desktop -> SCHEDULED",
          k == sk.SCHEDULED, "%s %s" % (k, ev))
    check("CS2 wall clock steps back: classify returns within HARD_JOIN + 1 s (%.2fs)" % dt,
          dt < 2.0 + 1.0)
    check("CS3 both attempts ran (error, then block)", sc.counts.get(
        os.path.normcase(mine)) == 2, repr(sc.counts))


def test_total_wall():
    # Both attempts share ONE HARD_JOIN wall. Attempt 1 ends incomplete just before the
    # wall; attempt 2 blocks. A fresh wall per attempt would run to ~2 x HARD_JOIN.
    saved = (sk.BUDGET_SECONDS, sk.HARD_JOIN_SECONDS)
    d = store([{"cliSessionId": SID}, {"cliSessionId": OTHER}], ages=[5, 10])
    mine = os.path.join(d, "local_00.json")
    sc = _Script({mine: [("sleep_error", 1.7), "block"]}, cap=8.0)
    try:
        sk.BUDGET_SECONDS, sk.HARD_JOIN_SECONDS = 5.0, 2.0
        sk.open = sc
        t0 = time.monotonic()
        k, tid, ev = sk.classify(SID, env=DESKTOP, dirs=[d])
        dt = time.monotonic() - t0
    finally:
        sc.release.set()
        del sk.open
        sk.BUDGET_SECONDS, sk.HARD_JOIN_SECONDS = saved
    check("TW1 attempt 1 ends just before the wall, attempt 2 blocks: SCHEDULED",
          k == sk.SCHEDULED, "%s %s" % (k, ev))
    check("TW2 whole classify wall <= HARD_JOIN + 1 s (%.2fs)" % dt, dt <= 2.0 + 1.0)
    check("TW3 a second attempt did start", sc.counts.get(os.path.normcase(mine)) == 2,
          repr(sc.counts))


def test_undecodable_or_across_attempts():
    # Fresh undecodable evidence naming scheduledTaskId (owner unreadable) seen in attempt 1
    # must be OR-ed into the final verdict even if attempt 2 (complete) no longer sees it.
    d = _mkdtemp("sk-undec-")
    bad = os.path.join(d, "local_00.json")
    with open(bad, "wb") as fh:
        fh.write(b'\xff\xfe\xfa{"scheduledTaskId": "ora-x"} \xff')
    mine = os.path.join(d, "local_01.json")
    with open(mine, "w") as fh:
        json.dump({"cliSessionId": SID}, fh)
    flaky = os.path.join(d, "local_02.json")
    with open(flaky, "w") as fh:
        json.dump({"cliSessionId": OTHER}, fh)
    now = time.time()
    for p, age in ((bad, 5), (mine, 10), (flaky, 15)):
        os.utime(p, (now - age, now - age))
    # Control: with a stable store the undecodable record alone already yields SCHEDULED.
    check("UO0 control: undecodable-with-key fresh record, Desktop -> SCHEDULED",
          sk.classify(SID, env=DESKTOP, dirs=[d])[0] == sk.SCHEDULED)
    sc = _Script({bad: ["ok", "gone"], flaky: ["error", "ok"]})
    sk.open = sc
    try:
        k, tid, ev = sk.classify(SID, env=DESKTOP, dirs=[d])
    finally:
        del sk.open
    check("UO1 attempt 1 sees undecodable evidence, attempt 2 (complete) does not: SCHEDULED",
          k == sk.SCHEDULED and "undecodable" in ev, "%s %s" % (k, ev))
    check("UO2 two attempts ran", sc.counts.get(os.path.normcase(flaky)) == 2, repr(sc.counts))


_CHILD = r"""
import sys, threading
sys.path.insert(0, sys.argv[1])
import session_kind as sk
sk.HARD_JOIN_SECONDS = float(sys.argv[2])
sk.BUDGET_SECONDS = 1.0
never = threading.Event()
def blocked_open(path, *a, **kw):
    never.wait()
sk.open = blocked_open
k, tid, ev = sk.classify("%s", env={"CLAUDE_CODE_ENTRYPOINT": "claude-desktop"}, dirs=[sys.argv[3]])
print(k)
sys.stdout.flush()
"""


def test_process_exit_with_blocked_worker():
    # The worker thread must be a daemon: with a read blocked forever, the process must still
    # exit on its own right after classify returns. Run in a child with a hard subprocess
    # timeout so this test cannot hang.
    lib = os.path.dirname(os.path.abspath(sk.__file__))
    d = store([{"cliSessionId": SID}], ages=[5])
    hard = 2.0
    t0 = time.monotonic()
    timed_out, out = False, ""
    try:
        r = subprocess.run([sys.executable, "-I", "-c", _CHILD % SID, lib, str(hard), d],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           timeout=hard + 3.0)
        out = r.stdout.decode("ascii", "replace").strip()
    except subprocess.TimeoutExpired:
        timed_out = True
    dt = time.monotonic() - t0
    check("PX1 child exits on its own within HARD_JOIN + 3 s despite a forever-blocked read "
          "(%.2fs)" % dt, not timed_out)
    check("PX2 child classified the blocked store as SCHEDULED", out == sk.SCHEDULED, repr(out))


def _run_all():
    test_record_join()
    test_entrypoint()
    test_staleness_and_damage()
    test_duplicates()
    test_tampering()
    test_blanked_registry()
    test_junction_loop_and_dot_dirs()
    test_no_mmap()
    test_prefilter()
    test_list_wrapped_decoy()
    test_seam_and_hygiene()
    test_c5_tamper_holes()
    test_c5_negatives()
    test_c4_entrypoints()
    test_c4_lams_store()
    test_c3_slow_store()
    test_unreadable_file()
    test_hard_max()
    test_prefix_candidates()
    test_c11_unlistable_dir()
    test_budget_inside_judge()
    test_prefix_byte_count()
    test_hard_join_and_retry()
    test_clock_step_back()
    test_total_wall()
    test_undecodable_or_across_attempts()
    test_process_exit_with_blocked_worker()
    test_c6_other_session_oversized()


if __name__ == "__main__":
    try:
        _run_all()
    finally:
        _cleanup_tmp()
    if _failures:
        print("\n%d FAILURE(S): %s" % (len(_failures), ", ".join(_failures[:12])))
        sys.exit(1)
    print("\nALL session-kind tests passed.")
    sys.exit(0)
