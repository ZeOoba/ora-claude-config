#!/usr/bin/env python3
"""Tests for OI-id reservation ENFORCEMENT (TDD -- written before the code).

Enforcement has one hard constraint that shapes everything: at switch-on the
ledger held 0 reservations and the tracker held 69 ids. A naive "every id must
be reserved" rule fails the entire existing file on day one. So enforcement is
BASELINE-SCOPED -- ids at or below the recorded baseline are grandfathered, and
only ids ABOVE it must carry a reservation.

The escape hatch is not optional. Hand-edits, historical backfills and merge
resolutions all introduce ids that were never allocated; without `--backfill`
enforcement wedges honest work, and a wedged gate gets bypassed, which is worse
than no gate.

Run: python maintenance/_tests/test_oi_id_enforcement.py
"""
import importlib.util
import io
import os
import subprocess
import sys
import tempfile

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


def tracker_with(ids):
    rows = "".join("| [OI-%03d](#OI-%03d) | 2026-01-01 | x | y |\n" % (i, i)
                   for i in ids)
    return "## Open\n\n| ID | Opened | Source | Detail |\n|---|---|---|---|\n" + rows


def fx(td, ids):
    p = os.path.join(td, "open-items-tracker.md")
    io.open(p, "w", encoding="utf-8", newline="").write(tracker_with(ids))
    return p


def test_grandfathered_ids_pass():
    """69 pre-existing ids, 0 reservations, baseline 69 -> clean. Without this
    the very first run blocks every push."""
    m = load()
    with tempfile.TemporaryDirectory() as td:
        t, led = fx(td, range(1, 70)), os.path.join(td, "r.log")
        r = m.enforce(t, led, baseline=69)
        expect("69 grandfathered ids, empty ledger -> no violations",
               r["violations"] == [], r["violations"])


def test_new_id_without_reservation_is_a_violation():
    m = load()
    with tempfile.TemporaryDirectory() as td:
        t, led = fx(td, list(range(1, 70)) + [70]), os.path.join(td, "r.log")
        r = m.enforce(t, led, baseline=69)
        expect("OI-070 above baseline, unreserved -> violation",
               [v["id"] for v in r["violations"]] == ["OI-070"], r["violations"])


def test_new_id_with_reservation_passes():
    m = load()
    with tempfile.TemporaryDirectory() as td:
        t, led = fx(td, range(1, 70)), os.path.join(td, "r.log")
        got = m.allocate(t, led, session="s", note="proper")   # reserves OI-070
        io.open(t, "w", encoding="utf-8", newline="").write(
            tracker_with(list(range(1, 70)) + [70]))
        r = m.enforce(t, led, baseline=69)
        expect("allocated id passes enforcement",
               got == "OI-070" and r["violations"] == [], (got, r["violations"]))


def test_backfill_clears_a_violation():
    """The escape hatch: a hand-edited or merged-in id can be regularised."""
    m = load()
    with tempfile.TemporaryDirectory() as td:
        t, led = fx(td, list(range(1, 70)) + [70]), os.path.join(td, "r.log")
        before = m.enforce(t, led, baseline=69)["violations"]
        m.backfill("OI-070", led, session="s", note="merged in from branch X")
        after = m.enforce(t, led, baseline=69)["violations"]
        expect("backfill clears the violation",
               len(before) == 1 and after == [], (before, after))


def test_backfill_is_recorded_distinguishably():
    """A backfill must not look like a clean allocation in the ledger -- the
    whole point is that a human can later see which ids bypassed the allocator."""
    m = load()
    with tempfile.TemporaryDirectory() as td:
        led = os.path.join(td, "r.log")
        m.backfill("OI-070", led, session="s", note="hand-edit")
        body = io.open(led, encoding="utf-8").read()
        expect("ledger marks the entry BACKFILL", "BACKFILL" in body, body)


def test_backfill_refuses_a_duplicate():
    m = load()
    with tempfile.TemporaryDirectory() as td:
        led = os.path.join(td, "r.log")
        m.backfill("OI-070", led, session="s", note="first")
        try:
            m.backfill("OI-070", led, session="s", note="again")
            expect("duplicate backfill refused", False, "no exception")
        except Exception as e:  # noqa: BLE001
            expect("duplicate backfill refused", "already" in str(e).lower(), repr(e))


def test_violation_message_names_the_remedy():
    """A blocking check that does not say how to unblock gets bypassed."""
    m = load()
    with tempfile.TemporaryDirectory() as td:
        t, led = fx(td, list(range(1, 70)) + [70]), os.path.join(td, "r.log")
        text = m.format_enforcement(m.enforce(t, led, baseline=69))
        expect("message names allocate-oi-id.py", "allocate-oi-id.py" in text, text)
        expect("message names --backfill as the escape hatch",
               "--backfill" in text, text)


def test_missing_baseline_file_does_not_block_everything():
    """Fail OPEN on a missing baseline. A baseline that cannot be read must not
    turn every id into a violation -- that is a self-inflicted outage."""
    m = load()
    with tempfile.TemporaryDirectory() as td:
        t, led = fx(td, range(1, 75)), os.path.join(td, "r.log")
        r = m.enforce(t, led, baseline=None)
        expect("unreadable baseline -> no violations, explicit skip",
               r["violations"] == [] and r.get("skipped"), r)


def test_section_only_new_id_also_enforced():
    m = load()
    with tempfile.TemporaryDirectory() as td:
        t = os.path.join(td, "open-items-tracker.md")
        io.open(t, "w", encoding="utf-8", newline="").write(
            tracker_with(range(1, 70)) + "\n### OI-071\nbody\n")
        led = os.path.join(td, "r.log")
        r = m.enforce(t, led, baseline=69)
        expect("section-only OI-071 above baseline is enforced",
               [v["id"] for v in r["violations"]] == ["OI-071"], r["violations"])


def test_mode_defaults_to_warn_when_unreadable():
    """Fails TOWARD warn. A gate that cannot read its own config must not
    spontaneously start blocking pushes."""
    m = load()
    with tempfile.TemporaryDirectory() as td:
        expect("missing mode file -> WARN",
               m.read_mode(os.path.join(td, "nope.txt")) == "WARN")
        p = os.path.join(td, "mode.txt")
        io.open(p, "w", encoding="utf-8").write("# comment\nBLOCK\n")
        expect("BLOCK is read", m.read_mode(p) == "BLOCK")
        io.open(p, "w", encoding="utf-8").write("garbage\n")
        expect("unparseable mode -> WARN", m.read_mode(p) == "WARN")


def test_warn_mode_exits_zero_but_still_reports():
    """The whole point of WARN: visible, not silent, and not blocking. A silent
    warn is just a disabled check."""
    m = load()
    with tempfile.TemporaryDirectory() as td:
        t, led = fx(td, list(range(1, 70)) + [70]), os.path.join(td, "r.log")
        bl = os.path.join(td, "b.txt"); io.open(bl, "w", encoding="utf-8").write("69\n")
        p = subprocess.run(
            [sys.executable, ALLOC, "--enforce", "--tracker", t, "--ledger", led,
             "--baseline", bl, "--mode", "WARN"], capture_output=True, text=True)
        expect("WARN mode exits 0", p.returncode == 0, p.returncode)
        expect("WARN mode still names the violating id", "OI-070" in p.stdout, p.stdout)
        expect("WARN mode still names the remedy", "--backfill" in p.stdout, p.stdout)
        expect("WARN mode says it is not blocking", "not blocking" in p.stdout, p.stdout)


def test_block_mode_still_blocks():
    """WARN must not have quietly disarmed enforcement."""
    m = load()
    with tempfile.TemporaryDirectory() as td:
        t, led = fx(td, list(range(1, 70)) + [70]), os.path.join(td, "r.log")
        bl = os.path.join(td, "b.txt"); io.open(bl, "w", encoding="utf-8").write("69\n")
        p = subprocess.run(
            [sys.executable, ALLOC, "--enforce", "--tracker", t, "--ledger", led,
             "--baseline", bl, "--mode", "BLOCK"], capture_output=True, text=True)
        expect("BLOCK mode exits 1", p.returncode == 1, p.returncode)


def main():
    test_mode_defaults_to_warn_when_unreadable()
    test_warn_mode_exits_zero_but_still_reports()
    test_block_mode_still_blocks()
    test_grandfathered_ids_pass()
    test_new_id_without_reservation_is_a_violation()
    test_new_id_with_reservation_passes()
    test_backfill_clears_a_violation()
    test_backfill_is_recorded_distinguishably()
    test_backfill_refuses_a_duplicate()
    test_violation_message_names_the_remedy()
    test_missing_baseline_file_does_not_block_everything()
    test_section_only_new_id_also_enforced()
    passed = sum(1 for ok, _ in results if ok)
    print("\noi-id enforcement tests: %d/%d passed" % (passed, len(results)))
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
