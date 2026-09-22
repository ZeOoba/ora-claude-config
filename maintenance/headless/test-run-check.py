#!/usr/bin/env python3
"""Tests for the stranded-spec and mirror-drift check bodies.

Every case here is a regression guard for a defect found in independent review on
2026-09-10 -- all of them in the same class: a check reporting CLEAN when it had
not actually verified anything, or an alarm being lost on the way to the pager.

Run: python test-run-check.py
"""
import importlib.util
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("runcheck", os.path.join(HERE, "run-check.py"))
rc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rc)
lib = rc.lib


def stub_sh(rc_code, out):
    return lambda cmd, cwd=None: (rc_code, out)


class StrandedSpec(unittest.TestCase):
    def setUp(self):
        self._sh, self._exists = rc._sh, os.path.exists
        rc.os.path.exists = lambda p: True

    def tearDown(self):
        rc._sh = self._sh
        rc.os.path.exists = self._exists

    def check(self):
        r = lib.CheckResult("stranded-spec")
        rc.check_stranded_spec(r)
        return r

    def test_clean_run_is_silent(self):
        rc._sh = stub_sh(0, "  OK -- cc folders and registry reconcile cleanly.")
        self.assertEqual(self.check().exit_code(), lib.EXIT_CLEAN)

    def test_rc1_is_a_finding(self):
        rc._sh = stub_sh(1, "  UNREGISTERED cc: ora-something")
        self.assertEqual(self.check().exit_code(), lib.EXIT_FINDINGS)

    def test_fail_open_rc0_is_cant_verify_not_clean(self):
        """The probe returns 0 when its shared helper is broken. That is NOT clean.

        Without this, a permanently broken store_discovery would make stranded-spec
        silent forever while freshness saw a healthy heartbeat -- both watchdogs
        green, nothing actually checked.
        """
        rc._sh = stub_sh(0, "  WARN store_discovery unavailable -- probe cannot run.")
        r = self.check()
        self.assertEqual(r.exit_code(), lib.EXIT_CANT_VERIFY)
        self.assertIn("NOT actually verified", r.errors[0]["summary"])

    def test_unexpected_rc_is_cant_verify(self):
        rc._sh = stub_sh(7, "boom")
        self.assertEqual(self.check().exit_code(), lib.EXIT_CANT_VERIFY)


class MirrorDrift(unittest.TestCase):
    def setUp(self):
        self._sh, self._exists = rc._sh, os.path.exists
        rc.os.path.exists = lambda p: True

    def tearDown(self):
        rc._sh = self._sh
        rc.os.path.exists = self._exists

    def check(self):
        r = lib.CheckResult("mirror-drift")
        rc.check_mirror_drift(r)
        return r

    def test_healthy_is_silent(self):
        rc._sh = stub_sh(0, '{"verdict":"HEALTHY","reason":"ok","gitAhead":0}')
        self.assertEqual(self.check().exit_code(), lib.EXIT_CLEAN)

    def test_alarm_is_a_finding(self):
        rc._sh = stub_sh(0, '{"verdict":"ALARM_SILENT_INCOMPLETE","reason":"no beacon"}')
        self.assertEqual(self.check().exit_code(), lib.EXIT_FINDINGS)

    def test_alarm_survives_a_populated_errors_array(self):
        """Regression: a bare string inside `errors` is itself valid JSON.

        The old reversed per-line scan bound `payload` to that string, so
        payload.get() raised -- turning a real ALARM into an AttributeError page
        with no verdict, exactly when the classifier was reporting trouble.
        """
        pretty = (
            '{\n'
            '  "verdict": "ALARM_SCRIPT_FAILED",\n'
            '  "reason": "wrangler timeout",\n'
            '  "errors": [\n'
            '    "beacon parse failed"\n'
            '  ]\n'
            '}'
        )
        rc._sh = stub_sh(0, pretty)
        r = self.check()
        self.assertEqual(r.exit_code(), lib.EXIT_FINDINGS)
        self.assertIn("ALARM_SCRIPT_FAILED", r.findings[0]["summary"])
        self.assertIn("wrangler timeout", r.findings[0]["summary"])

    def test_pretty_printed_json_parses(self):
        rc._sh = stub_sh(0, '{\n  "verdict": "HEALTHY",\n  "reason": "fine"\n}')
        self.assertEqual(self.check().exit_code(), lib.EXIT_CLEAN)

    def test_indeterminate_is_cant_verify_with_its_own_message(self):
        """INDETERMINATE is a real classifier verdict, not an unknown one."""
        rc._sh = stub_sh(0, '{"verdict":"INDETERMINATE","reason":"no beacon"}')
        r = self.check()
        self.assertEqual(r.exit_code(), lib.EXIT_CANT_VERIFY)
        self.assertIn("INDETERMINATE", r.errors[0]["summary"])
        self.assertNotIn("unrecognised", r.errors[0]["summary"])

    def test_unknown_verdict_is_cant_verify(self):
        rc._sh = stub_sh(0, '{"verdict":"BRAND_NEW_STATE","reason":"x"}')
        r = self.check()
        self.assertEqual(r.exit_code(), lib.EXIT_CANT_VERIFY)
        self.assertIn("unrecognised", r.errors[0]["summary"])

    def test_classifier_nonzero_is_cant_verify(self):
        rc._sh = stub_sh(1, "explosion")
        self.assertEqual(self.check().exit_code(), lib.EXIT_CANT_VERIFY)

    def test_unparseable_output_is_cant_verify(self):
        rc._sh = stub_sh(0, "not json at all")
        self.assertEqual(self.check().exit_code(), lib.EXIT_CANT_VERIFY)


class TaskInfoProbe(unittest.TestCase):
    def tearDown(self):
        rc._sh = rc._sh

    def test_empty_output_is_unknown_not_deleted(self):
        """SilentlyContinue means a failed query exits 0 with no stdout.

        Reading that as "task deleted" would page 're-register it' about tasks
        that are present and fine.
        """
        rc._sh = stub_sh(0, "")
        found, info = rc._task_info("whatever")
        self.assertIsNone(found)

    def test_missing_sentinel_is_deleted(self):
        rc._sh = stub_sh(0, "MISSING")
        found, info = rc._task_info("whatever")
        self.assertIs(found, False)


class NegativeEpoch(unittest.TestCase):
    def test_pre_1970_sentinel_keeps_its_real_year(self):
        """split('-')[0] used to strip the sign and silently yield 1970."""
        parsed = rc._parse_ps_date("/Date(-2208988800000)/")
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.year, 1900)
        self.assertLess(parsed.year, rc.NEVER_RUN_BEFORE_YEAR)

    def test_windows_never_run_sentinel(self):
        self.assertLess(rc._parse_ps_date("/Date(943938000000)/").year,
                        rc.NEVER_RUN_BEFORE_YEAR)

    def test_offset_suffix_is_stripped_not_the_sign(self):
        self.assertIsNotNone(rc._parse_ps_date("/Date(1757500800000+0000)/"))

    def test_iso_with_offset(self):
        self.assertEqual(rc._parse_ps_date("2026-09-10T14:00:00-04:00").hour, 14)


if __name__ == "__main__":
    unittest.main(verbosity=2)
