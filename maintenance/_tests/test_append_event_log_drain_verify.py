#!/usr/bin/env python3
"""Tests for append-event-log.py's drain_spool() verify-before-delete contract.

THE DEFECT THIS GUARDS (2026-11-05, surfaced by the adversarial review of the
rollover-holds-the-append-lock change): drain_spool replayed each `.pending/`
entry and then deleted its spool file with no check that the entry was actually
in the log. _log_lock() fails OPEN after LOCK_ACQUIRE_TIMEOUT_S, and
rollover-event-log.py holds that lock across its snapshot-read -> swap. A drain
that timed out on the lock wrote unlocked into rollover's window; rollover's swap
then landed on top (it was built from the pre-drain snapshot), the drained entry
vanished from the log, its spool file was already deleted, and both processes
exited 0. Silent loss from the canonical append-only record.

The fix has two halves, both exercised here:
  * drain never writes without the lock -- if it cannot take it, it refuses and
    leaves every spool file in place (the spool is already durable; replay is
    never urgent, so failing open buys nothing and opens the race above);
  * under the same lock hold, it re-reads the log and deletes the spool file only
    once a content-identical block for that entry is present.

Real OS subprocesses for every lock holder (byte-range locks are per-handle; an
in-process holder would not model a separate Claude Code session).

Run: python maintenance/_tests/test_append_event_log_drain_verify.py
Pure stdlib. ASCII-only output (Windows cp1252 console). Temp copies only --
never touches the real event_log.md.
"""
import importlib.util
import os
import shutil
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
    content = "---\nname: event-log\nmodified: 2026-01-01T00:00:00.000Z\n---\n\n"
    for e in entries:
        content += e.strip() + "\n\n"
    with open(p, "w", encoding="utf-8") as f:
        f.write(content)
    return p


def read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def spool_files(log):
    d = log + ".pending"
    if not os.path.isdir(d):
        return []
    return sorted(n for n in os.listdir(d) if n.endswith(".md"))


OLD = "## 2026-11-01 — Pre-existing entry\n\nOld body."
SPOOLED = "## 2026-11-02 — Spooled entry SPOOLMARK\n\nBody parked by a locked run."
NEW = "## 2026-11-03 — Fresh entry NEWMARK\n\nBody of the CLI's own append."


# A stand-in for rollover-event-log.py: takes append-event-log's _log_lock, signals
# ready, snapshots the log, then -- if a drained entry shows up while it still
# holds the lock (i.e. someone wrote UNLOCKED into its window) -- writes the
# snapshot back, exactly as rollover's swap from its pre-drain read would. Holds
# the lock until `hold_s` from acquisition, then releases.
_ROLLOVER_SIM = """
import importlib.util, sys, time
spec = importlib.util.spec_from_file_location("ael", %(append)r)
ael = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ael)
log, hold_s, ready, marker, clobbered = (sys.argv[1], float(sys.argv[2]),
                                         sys.argv[3], sys.argv[4], sys.argv[5])
with ael._log_lock(log) as locked:
    assert locked, "simulator failed to take the lock"
    t0 = time.monotonic()
    with open(log, encoding="utf-8") as f:
        snapshot = f.read()
    open(ready, "w").close()
    import os
    m0 = os.stat(log).st_mtime_ns
    # Poll with os.stat, not open(): a read handle held at the wrong instant makes the
    # intruder's os.replace fail (WinError 5) and changes its path, which made the
    # old-code repro miss ~1 run in 5 (REFUTE C6).
    while time.monotonic() - t0 < hold_s:
        try:
            changed = os.stat(log).st_mtime_ns != m0
        except OSError:
            changed = False
        if changed and not os.path.exists(clobbered):
            time.sleep(0.3)  # let the intruder finish its write
            with open(log, encoding="utf-8") as f:
                now = f.read()
            if marker in now:
                with open(log, "w", encoding="utf-8") as f:
                    f.write(snapshot)
                open(clobbered, "w").close()
            m0 = os.stat(log).st_mtime_ns
        time.sleep(0.02)
"""

# Plain holder: takes the lock, signals ready, holds for hold_s.
_HOLDER = """
import importlib.util, sys, time
spec = importlib.util.spec_from_file_location("ael", %(append)r)
ael = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ael)
log, hold_s, ready = sys.argv[1], float(sys.argv[2]), sys.argv[3]
with ael._log_lock(log) as locked:
    assert locked
    open(ready, "w").close()
    time.sleep(hold_s)
"""


def start(tmp, body, args):
    drv = os.path.join(tmp, "driver_%d.py" % time.time_ns())
    with open(drv, "w", encoding="utf-8") as f:
        f.write(body % {"append": APPEND})
    return subprocess.Popen([sys.executable, drv] + args,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def wait_ready(ready, proc):
    deadline = time.time() + 30
    while not os.path.exists(ready) and time.time() < deadline:
        if proc.poll() is not None:
            break
        time.sleep(0.02)
    return os.path.exists(ready)


def main():
    m = load()
    print("append-event-log.py drain_spool verify-before-delete tests")

    # --- 1. THE REPRO. Rollover (simulated) holds the lock past the appender's
    # timeout; the CLI drains a spooled entry. Before the fix, drain wrote it
    # unlocked, rollover's snapshot write erased it, and the spool file was
    # already deleted -> entry gone from both places, every process exit 0.
    tmp = tempfile.mkdtemp(prefix="ael-drainv-")
    log = make_log(tmp, [OLD])
    m.spool_entry(log, SPOOLED, time.time_ns())
    ef = os.path.join(tmp, "new.md")
    with open(ef, "w", encoding="utf-8") as f:
        f.write(NEW)
    ready = os.path.join(tmp, "sim.ready")
    clob = os.path.join(tmp, "sim.clobbered")
    hold = m.LOCK_ACQUIRE_TIMEOUT_S + 3.0
    sim = start(tmp, _ROLLOVER_SIM, [log, str(hold), ready, "SPOOLMARK", clob])
    expect("rollover simulator holds the lock before the appender runs",
           wait_ready(ready, sim), sim.poll())
    cli = subprocess.run([sys.executable, APPEND, "--entry-file", ef, "--log", log],
                         capture_output=True, text=True, encoding="utf-8", timeout=120)
    sim_out = sim.communicate(timeout=60)
    expect("simulator exits 0", sim.returncode == 0, sim_out)
    expect("appender CLI exits 0", cli.returncode == 0, (cli.stdout, cli.stderr))
    final = read(log)
    in_log = "SPOOLMARK" in final
    still_spooled = any("SPOOLMARK" in read(os.path.join(log + ".pending", n))
                        for n in spool_files(log))
    expect("spooled entry is NOT lost (in the log, or still parked in .pending/)",
           in_log or still_spooled,
           "in_log=%s spool=%s clobbered=%s stderr=%r"
           % (in_log, spool_files(log), os.path.exists(clob), cli.stderr))
    expect("drain never wrote into the lock holder's window (no clobber needed)",
           not os.path.exists(clob), cli.stderr)
    # Once the lock is free, the next run lands it exactly once and clears the spool.
    n = m.drain_spool(log)
    final = read(log)
    expect("after the holder releases, the next drain lands the parked entry",
           n == 1 and final.count("SPOOLMARK") == 1, (n, final))
    expect("...and only then removes its spool file", spool_files(log) == [],
           spool_files(log))
    shutil.rmtree(tmp, ignore_errors=True)

    # --- 2. Refuse, don't fail open: with the lock held by another process for
    # longer than the timeout, drain_spool writes nothing and keeps every file.
    tmp = tempfile.mkdtemp(prefix="ael-drainv-")
    log = make_log(tmp, [OLD])
    before = read(log)
    m.spool_entry(log, SPOOLED, time.time_ns())
    ready = os.path.join(tmp, "h.ready")
    h = start(tmp, _HOLDER, [log, "3.0", ready])
    expect("holder has the lock", wait_ready(ready, h), h.poll())
    t0 = time.time()
    n = m.drain_spool(log, lock_timeout=0.5)
    waited = time.time() - t0
    expect("drain under a held lock drains 0", n == 0, n)
    expect("drain under a held lock leaves the log byte-identical", read(log) == before)
    expect("drain under a held lock keeps the spool file", len(spool_files(log)) == 1,
           spool_files(log))
    expect("drain refuses after ONE lock timeout, not attempts x timeout",
           waited < 1.5, waited)
    h.communicate(timeout=30)
    shutil.rmtree(tmp, ignore_errors=True)

    # --- 3. Verify-before-delete in isolation: if the insert reports success but
    # the entry is not actually in the log on re-read, the spool file stays.
    tmp = tempfile.mkdtemp(prefix="ael-drainv-")
    log = make_log(tmp, [OLD])
    m.spool_entry(log, SPOOLED, time.time_ns())
    real = m._insert_or_inplace
    m._insert_or_inplace = lambda *a, **k: True  # "wrote" -- but nothing landed
    try:
        n = m.drain_spool(log)
    finally:
        m._insert_or_inplace = real
    expect("unverified drain reports 0 drained", n == 0, n)
    expect("unverified drain keeps the spool file", len(spool_files(log)) == 1,
           spool_files(log))
    shutil.rmtree(tmp, ignore_errors=True)

    # --- 4. Happy path + duplicate path still clear the spool.
    tmp = tempfile.mkdtemp(prefix="ael-drainv-")
    log = make_log(tmp, [OLD, SPOOLED])  # SPOOLED already present -> dedup
    m.spool_entry(log, SPOOLED, time.time_ns())
    m.spool_entry(log, NEW, time.time_ns() + 1)
    t0 = time.time()
    n = m.drain_spool(log)
    took = time.time() - t0
    final = read(log)
    expect("drain resolves a duplicate and a fresh entry (2 drained)", n == 2, n)
    # Guards against a nested-lock regression: a second byte-range lock from this
    # process times out after LOCK_ACQUIRE_TIMEOUT_S and then writes anyway, which
    # would otherwise pass every content assertion here (REFUTE C4, mutation m3).
    expect("uncontended drain never waits on its own lock",
           took < m.LOCK_ACQUIRE_TIMEOUT_S / 2, took)
    expect("duplicate not re-written, fresh entry landed once",
           final.count("SPOOLMARK") == 1 and final.count("NEWMARK") == 1, final)
    expect("both spool files removed after verification", spool_files(log) == [],
           spool_files(log))
    shutil.rmtree(tmp, ignore_errors=True)

    # --- 4b. An entry whose BODY contains a dated '## YYYY-MM-DD' line splits into two
    # blocks under entry_blocks(); it must still verify (and so be removed), and a
    # second drain of the same content must not write it again.
    tmp = tempfile.mkdtemp(prefix="ael-drainv-")
    log = make_log(tmp, [OLD])
    multi = ("## 2026-11-04 — Quoting entry MULTIMARK\n\nQuoted below:\n\n"
             "## 2026-10-01 — quoted header inside the body\n\nquoted body.")
    m.spool_entry(log, multi, time.time_ns())
    n = m.drain_spool(log)
    expect("entry with a dated '##' line in its body verifies and drains",
           n == 1 and spool_files(log) == [], (n, spool_files(log)))
    m.spool_entry(log, multi, time.time_ns())
    m.drain_spool(log)
    expect("re-spooled copy of it does not wedge the queue",
           spool_files(log) == [], spool_files(log))
    expect("...and is not written a second time",
           read(log).count("MULTIMARK") == 1, read(log).count("MULTIMARK"))
    shutil.rmtree(tmp, ignore_errors=True)

    # --- 4c. _entry_present must not accept a prefix of a longer entry, or a copy
    # quoted mid-body inside another entry (REFUTE C3).
    tmp = tempfile.mkdtemp(prefix="ael-drainv-")
    short = "## 2026-11-04 — Prefix case PFX\n\nFirst paragraph."
    longer = short + "\n\nSecond paragraph only in the longer entry."
    quoting = ("## 2026-11-04 — Quoter\n\nQuoting:\n\n" + short
               + "\n\nMore text after the quote.")
    log = make_log(tmp, [longer, OLD])
    expect("prefix of a longer entry is NOT present", not m._entry_present(log, short))
    log2 = os.path.join(tmp, "q.md")
    with open(log2, "w", encoding="utf-8") as f:
        f.write("---\nname: x\n---\n\n" + quoting + "\n\n" + OLD + "\n")
    expect("copy quoted mid-body is NOT present", not m._entry_present(log2, short))
    log3 = make_log(tmp, [short, OLD])
    expect("a real whole entry IS present", m._entry_present(log3, short))
    log4 = make_log(tmp, [short])
    expect("a whole entry at end of file IS present", m._entry_present(log4, short))
    shutil.rmtree(tmp, ignore_errors=True)

    # --- 4e. The log's FIRST '## ' line is undated or malformed. insert_newest anchors
    # above it, so the drained entry is followed by that line, not a dated header.
    # Verify must accept it, or attempt 2 writes a second copy (merge-gate C3 on #420).
    for first in ("## Conventions", "## 2026-11-1 — hand-typed"):
        tmp = tempfile.mkdtemp(prefix="ael-drainv-")
        p = os.path.join(tmp, "event_log.md")
        with open(p, "w", encoding="utf-8") as f:
            f.write("---\nname: event-log\n---\n\n# ORA Event Log\n\nIntro.\n\n"
                    + first + "\n\n- rule\n\n" + OLD + "\n")
        m.spool_entry(p, SPOOLED, time.time_ns())
        n = m.drain_spool(p)
        expect("undated first '## ' (%s): exactly one copy written" % first,
               read(p).count("SPOOLMARK") == 1, read(p).count("SPOOLMARK"))
        expect("undated first '## ' (%s): drained and spool file removed" % first,
               n == 1 and spool_files(p) == [], (n, spool_files(p)))
        shutil.rmtree(tmp, ignore_errors=True)

    # --- 4f. '---' counts as an entry boundary only when it is rollover's pointer rule
    # (the '*Entries at and before' line follows), not any horizontal rule mid-entry.
    tmp = tempfile.mkdtemp(prefix="ael-drainv-")
    p = os.path.join(tmp, "event_log.md")
    with open(p, "w", encoding="utf-8") as f:
        f.write("---\nname: x\n---\n\n" + SPOOLED + "\n\n---\n\n- more of a longer entry\n\n"
                + OLD + "\n")
    expect("prefix followed by a plain '---' rule is NOT present",
           not m._entry_present(p, SPOOLED))
    with open(p, "w", encoding="utf-8") as f:
        f.write("---\nname: x\n---\n\n" + SPOOLED + "\n\n---\n\n*Entries at and before "
                "\"x\" rolled over 2026-11-05 to [_archive/event_log_2026-11-05.md]"
                "(_archive/event_log_2026-11-05.md) per memory-policy.md's rollover rule.*\n")
    expect("entry followed by rollover's pointer IS present", m._entry_present(p, SPOOLED))
    shutil.rmtree(tmp, ignore_errors=True)

    # --- 4d. spool_entry stages under a non-.md name (drain never sees a half file).
    tmp = tempfile.mkdtemp(prefix="ael-drainv-")
    log = make_log(tmp, [OLD])
    p = m.spool_entry(log, NEW, 42)
    expect("spool_entry lands the final .md and leaves no .partial",
           os.path.basename(p) == "42.md" and read(p) == NEW
           and os.listdir(log + ".pending") == ["42.md"], os.listdir(log + ".pending"))
    shutil.rmtree(tmp, ignore_errors=True)

    # --- 5. A spooled entry with an undated header can never verify; it must not
    # wedge the queue behind it, and must not be deleted (left for a human).
    tmp = tempfile.mkdtemp(prefix="ael-drainv-")
    log = make_log(tmp, [OLD])
    m.spool_entry(log, "## Undated heading\n\nbody", time.time_ns())
    m.spool_entry(log, NEW, time.time_ns() + 1)
    n = m.drain_spool(log)
    final = read(log)
    expect("undated spool entry skipped, later valid entry still drains",
           n == 1 and "NEWMARK" in final and "Undated heading" not in final, (n, final))
    left = spool_files(log)
    expect("undated spool entry left parked (not deleted)",
           len(left) == 1 and "Undated" in read(os.path.join(log + ".pending", left[0])),
           left)
    shutil.rmtree(tmp, ignore_errors=True)

    passed = sum(1 for ok, _ in results if ok)
    print("\n%d/%d passed" % (passed, len(results)))
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
