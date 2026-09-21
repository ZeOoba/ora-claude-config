#!/usr/bin/env python3
"""Tests for append-event-log.py's _log_lock() -- the cross-process byte-range
lock added 2026-09-07 to close a WinError-5 race between concurrent writers.

THE DEFECT THIS GUARDS: _atomic_insert staged its write through a FIXED path,
`log + ".tmp-append"`, shared by every process. Two sessions appending within
the same instant could both touch that same staging name, and Windows would
refuse the loser's os.replace with WinError 5 ("Access is denied") -- observed
live this session (two retries before the append landed). The pre-existing
mtime-guard/retry loop already self-healed it (nothing was ever lost), but the
race itself was real and unguarded. _log_lock() serializes the read-modify-
write critical section across processes so they queue instead of colliding.

Real OS subprocesses throughout, not threads -- same rationale as
test_append_event_log_duplicate_guard.py's race test (#10 there): threads
share a process and the GIL serializes their file I/O in ways real sessions
(separate Claude Code processes) never experience.

Run: python maintenance/_tests/test_append_event_log_lock.py
Pure stdlib. ASCII-only output (Windows cp1252 console).
"""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
APPEND = os.path.join(os.path.dirname(HERE), "append-event-log.py")

results = []


def expect(label, cond, detail=""):
    results.append((bool(cond), label))
    print("  %s %s%s" % ("PASS" if cond else "FAIL:", label,
                         "" if cond else "  -- " + str(detail)))


def load():
    spec = importlib.util.spec_from_file_location("append_event_log", APPEND)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def make_log(tmp, entries=()):
    p = os.path.join(tmp, "event_log.md")
    content = "---\nname: event-log\n---\n\n"
    for e in entries:
        content += e.strip() + "\n\n"
    with open(p, "w", encoding="utf-8") as f:
        f.write(content)
    return p


# --- helper script bodies, run as separate `python -c`-style subprocesses via a
# small driver file so each gets a genuinely independent process/interpreter,
# matching this repo's established subprocess-race testing style.

_HOLD_INTERVAL_DRIVER = """
import importlib.util, json, sys, time
spec = importlib.util.spec_from_file_location("ael", %(append)r)
ael = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ael)
log, hold_s, out_path = sys.argv[1], float(sys.argv[2]), sys.argv[3]
with ael._log_lock(log):
    start = time.time()
    time.sleep(hold_s)
    end = time.time()
with open(out_path, "w", encoding="utf-8") as f:
    json.dump({"start": start, "end": end}, f)
"""


def main():
    m = load()
    print("append-event-log.py _log_lock tests")

    # --- 1. TWO REAL PROCESSES holding _log_lock() on the SAME log concurrently
    # must never overlap their held interval -- direct proof of mutual exclusion,
    # independent of the append logic built on top of it.
    tmp = tempfile.mkdtemp(prefix="ael-lock-")
    log = make_log(tmp, [])
    driver = os.path.join(tmp, "hold_driver.py")
    with open(driver, "w", encoding="utf-8") as f:
        f.write(_HOLD_INTERVAL_DRIVER % {"append": APPEND})
    out_a = os.path.join(tmp, "a.json")
    out_b = os.path.join(tmp, "b.json")
    procs = [
        subprocess.Popen([sys.executable, driver, log, "0.5", out_a],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True),
        subprocess.Popen([sys.executable, driver, log, "0.5", out_b],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True),
    ]
    outs = [p.communicate(timeout=30) for p in procs]
    rcs = [p.returncode for p in procs]
    expect("both holder processes exit 0", all(rc == 0 for rc in rcs),
           (rcs, outs))
    with open(out_a, encoding="utf-8") as f:
        ia = json.load(f)
    with open(out_b, encoding="utf-8") as f:
        ib = json.load(f)
    overlap = ia["start"] < ib["end"] and ib["start"] < ia["end"]
    expect("two processes' _log_lock holds never overlap in real wall-clock time",
           not overlap, (ia, ib))
    # they DID both run and take a measurable amount of wall time in total, so a
    # trivially-broken lock (e.g. a no-op) that let them run fully in parallel
    # would show total wall time close to 0.5s, not ~1.0s -- guard against that
    # degenerate "pass by doing nothing" case explicitly.
    span = max(ia["end"], ib["end"]) - min(ia["start"], ib["start"])
    expect("serialized holds take ~2x a single hold (not run in parallel)",
           span >= 0.9, span)
    for p in (log, out_a, out_b, driver, log + ".lock"):
        if os.path.exists(p):
            os.remove(p)
    os.rmdir(tmp)

    # --- 2. _log_lock times out gracefully rather than hanging forever when the
    # lock is held by ANOTHER process past its timeout -- this script's whole
    # design is "the append must always succeed," so the lock must never be a
    # new way to get stuck.
    tmp = tempfile.mkdtemp(prefix="ael-lock-")
    log = make_log(tmp, [])
    driver = os.path.join(tmp, "hold_driver.py")
    with open(driver, "w", encoding="utf-8") as f:
        f.write(_HOLD_INTERVAL_DRIVER % {"append": APPEND})
    out_holder = os.path.join(tmp, "holder.json")
    holder = subprocess.Popen([sys.executable, driver, log, "2.0", out_holder],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    time.sleep(0.3)  # let the holder actually acquire before we contend
    t0 = time.time()
    with m._log_lock(log, timeout=0.5):
        waited = time.time() - t0
    expect("contended _log_lock returns instead of hanging (bounded by timeout)",
           waited < 1.5, waited)
    expect("timeout is actually respected (waited close to the 0.5s budget, not 0)",
           waited >= 0.4, waited)
    holder.communicate(timeout=30)
    expect("holder process exits 0", holder.returncode == 0, holder.returncode)
    for p in (log, out_holder, driver, log + ".lock"):
        if os.path.exists(p):
            os.remove(p)
    os.rmdir(tmp)

    # --- 3. the actual production scenario: N processes appending DISTINCT
    # (non-duplicate) entries concurrently must all land, exactly once each, with
    # no corruption -- the friction this fix targets was two sessions appending
    # DIFFERENT content within the same instant, unlike the pre-existing
    # duplicate-guard race test (#10 there) which races IDENTICAL content and so
    # can short-circuit through the dedup path without ever contending for the
    # tmp-file write itself.
    tmp = tempfile.mkdtemp(prefix="ael-lock-")
    log = make_log(tmp, [])
    N = 6
    entry_files = []
    for i in range(N):
        p = os.path.join(tmp, "entry_%d.md" % i)
        with open(p, "w", encoding="utf-8", newline="") as f:
            f.write("## 2026-09-07 - Distinct entry %d\n\nBody text unique to entry %d.\n"
                    % (i, i))
        entry_files.append(p)

    procs = [subprocess.Popen(
        [sys.executable, APPEND, "--entry-file", ef, "--log", log],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        for ef in entry_files]
    outs = [p.communicate(timeout=60) for p in procs]
    rcs = [p.returncode for p in procs]

    with open(log, encoding="utf-8") as f:
        final = f.read()
    landed = sum(1 for i in range(N)
                 if final.count("Distinct entry %d" % i) == 1)
    expect("%d processes appending DISTINCT content -> all %d land exactly once" % (N, N),
           landed == N, "landed=%d final=%r" % (landed, final))
    expect("every process exits 0", all(rc == 0 for rc in rcs), rcs)
    any_retry = any("retrying" in (o[1] or "") for o in outs)
    expect("no attempt needed a retry (the lock removed the tmp-file race)",
           not any_retry, [o[1] for o in outs if "retrying" in (o[1] or "")])
    for p in [log, log + ".lock"] + entry_files:
        if os.path.exists(p):
            os.remove(p)
    pending_dir = log + ".pending"
    if os.path.isdir(pending_dir):
        for n in os.listdir(pending_dir):
            os.remove(os.path.join(pending_dir, n))
        os.rmdir(pending_dir)
    os.rmdir(tmp)

    # --- 4. uncontended single-process use is not a one-shot -- the same lock
    # path can be acquired again immediately afterward (it must always release).
    tmp = tempfile.mkdtemp(prefix="ael-lock-")
    log = make_log(tmp, [])
    acquired_twice = False
    with m._log_lock(log):
        pass
    with m._log_lock(log):
        acquired_twice = True
    expect("the same lock can be re-acquired sequentially in one process",
           acquired_twice)
    expect("the .lock sidecar is a permanent file, not cleaned up between holds",
           os.path.exists(log + ".lock"))
    for p in (log, log + ".lock"):
        if os.path.exists(p):
            os.remove(p)
    os.rmdir(tmp)

    passed = sum(1 for ok, _ in results if ok)
    print("\n%d/%d passed" % (passed, len(results)))
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
