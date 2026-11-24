#!/usr/bin/env python3
"""Tests for append-event-log.py's automatic rollover trigger (2026-11-23).

Why this exists: Automation Audit R34-8 found the live event_log.md at 375,496B,
about three days from the 400,000B size WARN, with the previous rollover 46 days
earlier. The WARN only ever printed; maintenance/rollover-event-log.py ran only
when someone remembered it. auto_rollover_if_oversized() closes that gap: after a
confirmed append, an oversized log is rolled over by running the existing
rollover script, whose own guards (append lock, (mtime, size) stamp, same-day
archive refusal, unwind) stay authoritative.

Contract under test:
  - fires only at or above the size threshold, read at CALL time;
  - runs rollover OUTSIDE append's _log_lock (rollover takes that lock itself);
  - fail-open: a missing script, a refusal, a timeout or any exception returns
    False and never raises, so the append's own exit code is untouched;
  - ORA_EVENT_LOG_NO_AUTO_ROLLOVER=1 turns it off.

Run: python -m unittest maintenance/_tests/test_append_event_log_auto_rollover.py
"""
import contextlib
import datetime
import importlib.util
import io
import os
import re
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
MODULE_PATH = os.path.join(HERE, "..", "append-event-log.py")
spec = importlib.util.spec_from_file_location("append_event_log_autoroll", MODULE_PATH)
ael = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ael)

DATED = re.compile(r"^## \d{4}-\d{2}-\d{2}\b", re.M)
TODAY = datetime.date.today().isoformat()


def _make_log(n_entries=300):
    """A log shaped like the real one: frontmatter, H1, then dated entries
    (newest first), each 3 lines, so n_entries=300 is ~900 body lines -- enough
    for rollover's default --keep-min 600 to find a cut."""
    head = ("---\nname: event_log\nmetadata:\n  type: log\n"
            "  modified: 2026-11-01T00:00:00.000Z\n---\n\n"
            "# ORA Event Log (append-only, newest first)\n\n")
    body = []
    for i in range(n_entries):
        day = datetime.date(2026, 11, 1) - datetime.timedelta(days=i)
        body.append("## %s — entry %d\n- detail line for entry %d\n\n" % (day.isoformat(), i, i))
    d = tempfile.mkdtemp(prefix="ael-autoroll-")
    log = os.path.join(d, "event_log.md")
    with open(log, "w", encoding="utf-8", newline="\n") as f:
        f.write(head + "".join(body))
    return d, log


def _blocks(text):
    """Every dated entry as its full text (header through the line before the next
    dated header or the rollover pointer rule), whitespace-trimmed."""
    out, cur = [], None
    for ln in text.splitlines():
        if DATED.match(ln):
            if cur is not None:
                out.append("\n".join(cur).strip())
            cur = [ln]
        elif cur is not None:
            if ln.strip() == "---":
                out.append("\n".join(cur).strip())
                cur = None
            else:
                cur.append(ln)
    if cur is not None:
        out.append("\n".join(cur).strip())
    return out


def _read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


@contextlib.contextmanager
def _env(**kv):
    saved = {k: os.environ.get(k) for k in kv}
    try:
        for k, v in kv.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        yield
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def _quiet(fn, *a, **kw):
    err, out = io.StringIO(), io.StringIO()
    with contextlib.redirect_stderr(err), contextlib.redirect_stdout(out):
        r = fn(*a, **kw)
    return r, out.getvalue(), err.getvalue()


class AutoRolloverTest(unittest.TestCase):
    def setUp(self):
        self.dir, self.log = _make_log()
        self.before = _read(self.log)
        self.archive = os.path.join(self.dir, "_archive", "event_log_%s.md" % TODAY)
        self._envcm = _env(ORA_EVENT_LOG_NO_AUTO_ROLLOVER=None, ORA_EVENT_LOG_NO_AUTOCOMMIT="1")
        self._envcm.__enter__()

    def tearDown(self):
        self._envcm.__exit__(None, None, None)
        shutil.rmtree(self.dir, ignore_errors=True)

    # --- threshold ---------------------------------------------------------
    def test_below_threshold_does_nothing(self):
        size = os.path.getsize(self.log)
        r, _, _ = _quiet(ael.auto_rollover_if_oversized, self.log, size_threshold=size + 1)
        self.assertFalse(r)
        self.assertEqual(_read(self.log), self.before)
        self.assertFalse(os.path.exists(self.archive))

    def test_at_threshold_rolls_over_and_loses_nothing(self):
        size = os.path.getsize(self.log)
        r, out, err = _quiet(ael.auto_rollover_if_oversized, self.log, size_threshold=size)
        self.assertTrue(r, err)
        self.assertTrue(os.path.exists(self.archive))
        live, arc = _read(self.log), _read(self.archive)
        self.assertLess(len(live), len(self.before))
        self.assertIn("rolled over %s" % TODAY, live)
        # Exact, not a count: every original entry block appears exactly once across
        # live + archive, so one loss plus one duplicate cannot cancel out.
        self.assertEqual(sorted(_blocks(live) + _blocks(arc)), sorted(_blocks(self.before)))
        self.assertFalse(os.path.exists(self.log + ".rollover-backup"))
        self.assertIn("auto-rollover", out + err)

    def test_default_threshold_is_read_at_call_time(self):
        """Patching LOG_SIZE_WARN_AT must take effect (no def-time default bound)."""
        saved = ael.LOG_SIZE_WARN_AT
        try:
            ael.LOG_SIZE_WARN_AT = 1
            r, _, err = _quiet(ael.auto_rollover_if_oversized, self.log)
        finally:
            ael.LOG_SIZE_WARN_AT = saved
        self.assertTrue(r, err)

    def test_oversized_but_short_log_is_not_reported_as_rolled_over(self):
        """REFUTE C1: rollover exits 0 with 'nothing to roll over' when the log is at
        or under --keep-min lines. That is a no-op, not a success."""
        shutil.rmtree(self.dir, ignore_errors=True)
        self.dir, self.log = _make_log(n_entries=50)   # ~150 lines, under keep-min 600
        self.archive = os.path.join(self.dir, "_archive", "event_log_%s.md" % TODAY)
        before = _read(self.log)
        r, out, err = _quiet(ael.auto_rollover_if_oversized, self.log, size_threshold=1)
        self.assertFalse(r)
        self.assertEqual(_read(self.log), before)
        self.assertFalse(os.path.exists(self.archive))
        self.assertIn("auto-rollover made no cut", err)
        self.assertNotIn("rollover complete", out)

    # --- opt-out -----------------------------------------------------------
    def test_env_opt_out(self):
        with _env(ORA_EVENT_LOG_NO_AUTO_ROLLOVER="1"):
            r, _, _ = _quiet(ael.auto_rollover_if_oversized, self.log, size_threshold=1)
        self.assertFalse(r)
        self.assertEqual(_read(self.log), self.before)

    # --- fail-open ---------------------------------------------------------
    def test_missing_script_fails_open(self):
        r, _, err = _quiet(ael.auto_rollover_if_oversized, self.log, size_threshold=1,
                           script=os.path.join(self.dir, "nope.py"))
        self.assertFalse(r)
        self.assertEqual(_read(self.log), self.before)
        self.assertIn("auto-rollover", err)

    def test_missing_log_fails_open(self):
        r, _, _ = _quiet(ael.auto_rollover_if_oversized,
                         os.path.join(self.dir, "absent.md"), size_threshold=1)
        self.assertFalse(r)

    def test_refusal_when_todays_archive_exists_fails_open(self):
        os.makedirs(os.path.dirname(self.archive))
        with open(self.archive, "w", encoding="utf-8") as f:
            f.write("prior same-day archive\n")
        r, _, err = _quiet(ael.auto_rollover_if_oversized, self.log, size_threshold=1)
        self.assertFalse(r)
        self.assertEqual(_read(self.log), self.before)
        self.assertEqual(_read(self.archive), "prior same-day archive\n")
        self.assertIn("auto-rollover", err)

    def test_timeout_fails_open_and_never_kills_the_rollover(self):
        """A slow rollover must be left to finish: killing it mid-swap would skip its
        own unwind. The stand-in script writes a marker only AFTER outliving the
        caller's timeout; the marker appearing proves it was not killed."""
        marker = os.path.join(self.dir, "finished.txt")
        slow = os.path.join(self.dir, "slow.py")
        with open(slow, "w") as f:
            f.write("import time\ntime.sleep(2.5)\nopen(%r, 'w').write('done')\n" % marker)
        r, _, err = _quiet(ael.auto_rollover_if_oversized, self.log, size_threshold=1,
                           script=slow, timeout=0.5)
        self.assertFalse(r)
        self.assertEqual(_read(self.log), self.before)
        self.assertIn("auto-rollover still running", err)
        self.assertFalse(os.path.exists(marker))
        import time
        deadline = time.monotonic() + 15
        while not os.path.exists(marker) and time.monotonic() < deadline:
            time.sleep(0.1)
        self.assertTrue(os.path.exists(marker), "timed-out rollover was killed")

    def test_held_append_lock_makes_rollover_refuse_and_fail_open(self):
        if not ael._HAVE_MSVCRT:
            self.skipTest("msvcrt byte-range lock is Windows-only")
        with ael._log_lock(self.log) as held:
            self.assertTrue(held)
            r, _, err = _quiet(ael.auto_rollover_if_oversized, self.log, size_threshold=1)
        self.assertFalse(r)
        self.assertEqual(_read(self.log), self.before)
        self.assertFalse(os.path.exists(self.archive))

    # --- wired into main() -------------------------------------------------
    def _entry_file(self, title):
        p = os.path.join(self.dir, "entry.md")
        with open(p, "w", encoding="utf-8") as f:
            f.write("## %s — %s\n- body\n" % (TODAY, title))
        return p

    def test_main_rolls_over_an_oversized_log_after_appending(self):
        saved = ael.LOG_SIZE_WARN_AT
        try:
            ael.LOG_SIZE_WARN_AT = 1
            rc, _, err = _quiet(ael.main, ["--entry-file", self._entry_file("new top entry"),
                                           "--log", self.log, "--no-commit"])
        finally:
            ael.LOG_SIZE_WARN_AT = saved
        self.assertEqual(rc, 0, err)
        live = _read(self.log)
        self.assertTrue(os.path.exists(self.archive), err)
        first = DATED.search(live)
        self.assertIn("new top entry", live[first.start():first.start() + 200])
        arc = _read(self.archive)
        expected = _blocks(self.before) + ["## %s — new top entry\n- body" % TODAY]
        self.assertEqual(sorted(_blocks(live) + _blocks(arc)), sorted(expected))

    def test_main_exit_code_unaffected_when_rollover_fails(self):
        os.makedirs(os.path.dirname(self.archive))
        with open(self.archive, "w", encoding="utf-8") as f:
            f.write("prior same-day archive\n")
        saved = ael.LOG_SIZE_WARN_AT
        try:
            ael.LOG_SIZE_WARN_AT = 1
            rc, _, err = _quiet(ael.main, ["--entry-file", self._entry_file("still lands"),
                                           "--log", self.log, "--no-commit"])
        finally:
            ael.LOG_SIZE_WARN_AT = saved
        self.assertEqual(rc, 0, err)
        self.assertIn("still lands", _read(self.log))
        self.assertIn("auto-rollover", err)

    def test_main_below_threshold_never_invokes_rollover(self):
        rc, _, err = _quiet(ael.main, ["--entry-file", self._entry_file("small log"),
                                       "--log", self.log, "--no-commit"])
        self.assertEqual(rc, 0, err)
        self.assertFalse(os.path.exists(self.archive))
        self.assertNotIn("auto-rollover", err)


if __name__ == "__main__":
    unittest.main()
