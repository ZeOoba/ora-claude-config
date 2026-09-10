#!/usr/bin/env python3
"""Contract tests for ora_headless_lib. Run: python test-ora-headless-lib.py"""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ora_headless_lib as lib


class ExitContract(unittest.TestCase):
    def test_clean_is_zero(self):
        r = lib.CheckResult("t")
        self.assertEqual(r.exit_code(), lib.EXIT_CLEAN)
        self.assertEqual(r.status(), "CLEAN")

    def test_findings_is_one(self):
        r = lib.CheckResult("t")
        r.finding("something drifted")
        self.assertEqual(r.exit_code(), lib.EXIT_FINDINGS)

    def test_error_is_two(self):
        r = lib.CheckResult("t")
        r.error("probe would not run")
        self.assertEqual(r.exit_code(), lib.EXIT_CANT_VERIFY)

    def test_error_outranks_finding(self):
        """A partial finding set must not be presented as authoritative."""
        r = lib.CheckResult("t")
        r.finding("drift")
        r.error("could not read the other fleet")
        self.assertEqual(r.exit_code(), lib.EXIT_CANT_VERIFY)

    def test_notes_alone_stay_clean(self):
        r = lib.CheckResult("t")
        r.note("verdict HEALTHY")
        self.assertEqual(r.exit_code(), lib.EXIT_CLEAN)


class FindingsFile(unittest.TestCase):
    def test_clean_writes_heartbeat_only(self):
        r = lib.CheckResult("demo")
        with tempfile.TemporaryDirectory() as d:
            written = lib.write_findings(r, state_dir=d)
            self.assertEqual(len(written), 1)
            self.assertTrue(written[0].endswith("demo-latest.json"))
            payload = json.load(open(written[0], encoding="utf-8"))
            self.assertEqual(payload["status"], "CLEAN")
            self.assertEqual(payload["findingCount"], 0)

    def test_findings_also_archived(self):
        r = lib.CheckResult("demo")
        r.finding("bad")
        with tempfile.TemporaryDirectory() as d:
            written = lib.write_findings(r, state_dir=d)
            self.assertEqual(len(written), 2)
            self.assertEqual(json.load(open(written[1], encoding="utf-8"))["findingCount"], 1)


class Rendering(unittest.TestCase):
    def test_non_cp1252_glyphs_do_not_raise(self):
        """SKILL.mds carry these freely; printing one unmodified killed a probe."""
        r = lib.CheckResult("demo")
        r.finding("spec says ⚠ drift — see ⇒ here ✓")
        body = lib.render_body(r)
        body.encode("ascii")  # must not raise

    def test_body_names_status_and_counts(self):
        r = lib.CheckResult("demo")
        r.error("classifier down")
        body = lib.render_body(r)
        self.assertIn("CANT_VERIFY", body)
        self.assertIn("COULD NOT VERIFY", body)


class Paging(unittest.TestCase):
    def test_falls_back_to_desktop_file_when_send_script_absent(self):
        r = lib.CheckResult("demo")
        r.finding("bad")
        with tempfile.TemporaryDirectory() as d:
            alert = os.path.join(d, "ORA-CHECK-FAILED.txt")
            how = lib.page(r, send_script=os.path.join(d, "nope.ps1"), desktop_alert=alert)
            self.assertEqual(how, "desktop-file")
            self.assertIn("bad", open(alert, encoding="utf-8").read())

    def test_routing_is_ggoldberg_only(self):
        """Routing canon: automated output goes to ggoldberg ONLY, never cc Eric."""
        self.assertEqual(lib.PAGE_TO, "ggoldberg@oxfordra.net")
        self.assertNotIn("egoldberg", lib.PAGE_TO)


class RunOrchestration(unittest.TestCase):
    def test_crashing_check_is_cant_verify_not_clean(self):
        def boom(result):
            raise RuntimeError("probe exploded")
        with tempfile.TemporaryDirectory() as d:
            code = lib.run("demo-crash", boom, argv=["--dry-run"], state_dir=d)
        self.assertEqual(code, lib.EXIT_CANT_VERIFY)

    def test_clean_check_returns_zero(self):
        with tempfile.TemporaryDirectory() as d:
            code = lib.run("demo-clean", lambda r: r.note("fine"),
                           argv=["--dry-run"], state_dir=d)
        self.assertEqual(code, lib.EXIT_CLEAN)

    def test_run_does_not_touch_the_live_state_dir(self):
        """Regression: these tests twice wrote demo-* heartbeats into production."""
        with tempfile.TemporaryDirectory() as d:
            lib.run("demo-isolated", lambda r: r.note("x"),
                    argv=["--dry-run"], state_dir=d)
            self.assertTrue(os.path.exists(os.path.join(d, "demo-isolated-latest.json")))
        self.assertFalse(
            os.path.exists(os.path.join(lib.STATE_DIR, "demo-isolated-latest.json")))


if __name__ == "__main__":
    unittest.main(verbosity=2)
