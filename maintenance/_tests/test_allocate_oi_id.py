#!/usr/bin/env python3
"""Tests for allocate-oi-id.py (TDD -- written before the implementation).

The defect this guards: two sessions each read the tracker's max OI-NNN, both
compute max+1, and both write it. The window is NOT the read -- it is the
MINUTES between reading and committing the row, during which the tracker still
shows the old max. So a correct allocator must record a durable reservation at
allocation time and honour reservations on every later allocation.

Run: python maintenance/_tests/test_allocate_oi_id.py
Pure stdlib. ASCII-only output (Windows cp1252 console).
"""
import importlib.util
import io
import os
import subprocess
import sys
import tempfile
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
ALLOC = os.path.join(os.path.dirname(HERE), "allocate-oi-id.py")

results = []


def expect(label, cond, detail=""):
    results.append((bool(cond), label))
    print("  %s %s%s" % ("PASS" if cond else "FAIL:", label,
                         "" if cond else "  -- " + str(detail)))


def load():
    spec = importlib.util.spec_from_file_location("allocate_oi_id", ALLOC)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


TRACKER = """# Open Items

| ID | Opened | Source | Detail |
|---|---|---|---|
| [OI-001](#OI-001) | 2026-01-01 | x | y |
| [OI-007](#OI-007) | 2026-01-02 | x | y |

### OI-001
body

### OI-007
body
"""


def _fixture(tmp, text=TRACKER):
    p = os.path.join(tmp, "open-items-tracker.md")
    io.open(p, "w", encoding="utf-8", newline="").write(text)
    return p


def test_next_id_is_max_plus_one():
    m = load()
    with tempfile.TemporaryDirectory() as td:
        t, led = _fixture(td), os.path.join(td, "res.log")
        got = m.allocate(t, led, session="s1", note="first")
        expect("allocate: max row id 7 -> OI-008", got == "OI-008", got)


def test_reservation_is_honoured_before_the_row_exists():
    """THE core case. Session A allocates but has not written its row yet --
    the tracker still shows max 7. Session B must NOT get the same id."""
    m = load()
    with tempfile.TemporaryDirectory() as td:
        t, led = _fixture(td), os.path.join(td, "res.log")
        a = m.allocate(t, led, session="A", note="in flight")
        b = m.allocate(t, led, session="B", note="second")
        expect("reservation honoured across the read-to-write window",
               (a, b) == ("OI-008", "OI-009"), (a, b))


def test_ids_never_reused_even_after_the_row_lands():
    m = load()
    with tempfile.TemporaryDirectory() as td:
        t, led = _fixture(td), os.path.join(td, "res.log")
        a = m.allocate(t, led, session="A", note="x")
        # A now writes its row into the tracker.
        txt = io.open(t, encoding="utf-8").read().replace(
            "| [OI-007](#OI-007) | 2026-01-02 | x | y |",
            "| [OI-007](#OI-007) | 2026-01-02 | x | y |\n"
            "| [%s](#%s) | 2026-01-03 | x | y |" % (a, a))
        io.open(t, "w", encoding="utf-8", newline="").write(txt)
        b = m.allocate(t, led, session="B", note="y")
        expect("id not reused once the reserved row lands",
               (a, b) == ("OI-008", "OI-009"), (a, b))


def test_section_only_id_still_counts():
    """A detail section with no row yet is still a taken id."""
    m = load()
    with tempfile.TemporaryDirectory() as td:
        t = _fixture(td, TRACKER + "\n### OI-042\nbody\n")
        led = os.path.join(td, "res.log")
        got = m.allocate(t, led, session="s", note="x")
        expect("section-only OI-042 counts as taken -> OI-043",
               got == "OI-043", got)


def test_concurrent_allocations_are_unique():
    """12 threads racing the allocator must produce 12 distinct ids. This is
    the property the whole file exists for; without locking it fails."""
    m = load()
    with tempfile.TemporaryDirectory() as td:
        t, led = _fixture(td), os.path.join(td, "res.log")
        out, errs = [], []
        lock = threading.Lock()

        def worker(i):
            try:
                got = m.allocate(t, led, session="s%d" % i, note="race")
                with lock:
                    out.append(got)
            except Exception as e:  # noqa: BLE001
                with lock:
                    errs.append(repr(e))

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(12)]
        for th in threads:
            th.start()
        for th in threads:
            th.join()
        expect("12 concurrent allocations: no exceptions", not errs, errs[:2])
        expect("12 concurrent allocations: all distinct",
               len(set(out)) == 12, sorted(out))
        expect("12 concurrent allocations: contiguous 008..019",
               sorted(out) == ["OI-%03d" % n for n in range(8, 20)], sorted(out))


def test_separate_processes_are_unique():
    """Threads share a process; real sessions do not. Race the CLI itself."""
    with tempfile.TemporaryDirectory() as td:
        t, led = _fixture(td), os.path.join(td, "res.log")
        procs = [subprocess.Popen(
            [sys.executable, ALLOC, "--tracker", t, "--ledger", led,
             "--session", "p%d" % i, "--note", "race"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            for i in range(8)]
        got = []
        for p in procs:
            so, _ = p.communicate()
            got.append(so.strip())
        expect("8 concurrent PROCESSES: all distinct",
               len(set(got)) == 8, sorted(got))


def test_stale_lock_is_broken_not_deadlocked():
    """A crashed session must not wedge the allocator forever."""
    m = load()
    with tempfile.TemporaryDirectory() as td:
        t, led = _fixture(td), os.path.join(td, "res.log")
        lockp = led + ".lock"
        io.open(lockp, "w", encoding="utf-8").write("stale")
        os.utime(lockp, (0, 0))          # ancient -> stale
        got = m.allocate(t, led, session="s", note="x", stale_lock_secs=1)
        expect("stale lock broken, allocation proceeds", got == "OI-008", got)
        expect("lock released after allocation", not os.path.exists(lockp))


def test_missing_tracker_refuses_rather_than_guessing():
    """Allocating from an unreadable tracker would hand out OI-001 and collide
    with everything. Fail loudly instead."""
    m = load()
    with tempfile.TemporaryDirectory() as td:
        led = os.path.join(td, "res.log")
        try:
            m.allocate(os.path.join(td, "nope.md"), led, session="s", note="x")
            expect("missing tracker refuses", False, "no exception raised")
        except Exception as e:  # noqa: BLE001
            expect("missing tracker refuses (loud, not OI-001)",
                   "tracker" in str(e).lower(), repr(e))


def test_ledger_records_who_and_why():
    m = load()
    with tempfile.TemporaryDirectory() as td:
        t, led = _fixture(td), os.path.join(td, "res.log")
        m.allocate(t, led, session="sess-xyz", note="filing the thing")
        body = io.open(led, encoding="utf-8").read()
        expect("ledger records id, session and note",
               "OI-008" in body and "sess-xyz" in body
               and "filing the thing" in body, body[:160])


def main():
    test_next_id_is_max_plus_one()
    test_reservation_is_honoured_before_the_row_exists()
    test_ids_never_reused_even_after_the_row_lands()
    test_section_only_id_still_counts()
    test_concurrent_allocations_are_unique()
    test_separate_processes_are_unique()
    test_stale_lock_is_broken_not_deadlocked()
    test_missing_tracker_refuses_rather_than_guessing()
    test_ledger_records_who_and_why()
    passed = sum(1 for ok, _ in results if ok)
    print("\nallocate-oi-id tests: %d/%d passed" % (passed, len(results)))
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
