#!/usr/bin/env python3
"""Unit tests for fleet-contract-check.py's pure staleness logic."""
import datetime
import importlib.util
import os
import sys
import tempfile
import unittest

MODULE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fleet-contract-check.py")
spec = importlib.util.spec_from_file_location("fleet_contract_check", MODULE_PATH)
fcc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fcc)


class TestCheckContract(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.now = datetime.datetime.now()

    def _make_contract(self, filename, max_age_hours=36):
        return {
            "name": "test-contract",
            "producer": "test-producer",
            "output_file": os.path.join(self.tmpdir, filename),
            "consumer": "test-consumer",
            "max_age_hours": max_age_hours,
        }

    def test_missing_file_is_missing(self):
        c = self._make_contract("does-not-exist.json")
        status, age = fcc.check_contract(c, self.now)
        self.assertEqual(status, "MISSING")
        self.assertIsNone(age)

    def test_fresh_file_is_ok(self):
        path = os.path.join(self.tmpdir, "fresh.json")
        with open(path, "w") as f:
            f.write("{}")
        c = self._make_contract("fresh.json", max_age_hours=36)
        status, age = fcc.check_contract(c, self.now)
        self.assertEqual(status, "OK")
        self.assertLess(age, 1.0)

    def test_stale_file_is_stale(self):
        path = os.path.join(self.tmpdir, "stale.json")
        with open(path, "w") as f:
            f.write("{}")
        old_time = (self.now - datetime.timedelta(hours=50)).timestamp()
        os.utime(path, (old_time, old_time))
        c = self._make_contract("stale.json", max_age_hours=36)
        status, age = fcc.check_contract(c, self.now)
        self.assertEqual(status, "STALE")
        self.assertGreater(age, 36)

    def test_file_just_under_threshold_is_ok(self):
        path = os.path.join(self.tmpdir, "borderline.json")
        with open(path, "w") as f:
            f.write("{}")
        just_under = (self.now - datetime.timedelta(hours=35)).timestamp()
        os.utime(path, (just_under, just_under))
        c = self._make_contract("borderline.json", max_age_hours=36)
        status, age = fcc.check_contract(c, self.now)
        self.assertEqual(status, "OK")


class TestMainExitCode(unittest.TestCase):
    def test_seeded_contracts_are_well_formed(self):
        """Every seeded contract has the required keys and a plausible threshold."""
        for c in fcc.CONTRACTS:
            for key in ("name", "producer", "output_file", "consumer", "max_age_hours"):
                self.assertIn(key, c, f"contract {c.get('name')} missing key {key}")
            self.assertGreater(c["max_age_hours"], 0)
            self.assertTrue(c["output_file"].endswith(".json"))


if __name__ == "__main__":
    unittest.main()
