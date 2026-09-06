#!/usr/bin/env python3
"""Tests for fleet-status.py's host_clock_status() (2026-09-06, PR #158 review).

The check must compare the host offset against Eastern's offset AT THAT INSTANT:
-05:00 in July (Eastern is -04:00) and -04:00 in January (Eastern is -05:00) are both
SHIFTED, even though each is a valid Eastern offset in the other season.

Run: python test_fleet_status_host_clock.py
"""
import datetime
import importlib.util
import os
import unittest

MODULE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fleet-status.py")
spec = importlib.util.spec_from_file_location("fleet_status", MODULE_PATH)
fs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fs)

try:
    from zoneinfo import ZoneInfo
    ZoneInfo("America/New_York")
    HAVE_TZDATA = True
except Exception:
    HAVE_TZDATA = False


def at(month, offset_hours, name):
    tz = datetime.timezone(datetime.timedelta(hours=offset_hours), name)
    return datetime.datetime(2026, month, 15, 12, 0, tzinfo=tz)


class TestHostClock(unittest.TestCase):
    @unittest.skipUnless(HAVE_TZDATA, "tzdata unavailable")
    def test_winter_minus5_is_eastern(self):
        r = fs.host_clock_status(at(1, -5, "EST"))
        self.assertFalse(r["host_clock_shifted"], r)
        self.assertEqual(r["eastern_offset_now"], "-05:00")

    @unittest.skipUnless(HAVE_TZDATA, "tzdata unavailable")
    def test_winter_minus4_is_shifted(self):
        r = fs.host_clock_status(at(1, -4, "AST"))
        self.assertTrue(r["host_clock_shifted"], r)

    @unittest.skipUnless(HAVE_TZDATA, "tzdata unavailable")
    def test_summer_minus4_is_eastern(self):
        r = fs.host_clock_status(at(7, -4, "EDT"))
        self.assertFalse(r["host_clock_shifted"], r)
        self.assertEqual(r["eastern_offset_now"], "-04:00")

    @unittest.skipUnless(HAVE_TZDATA, "tzdata unavailable")
    def test_summer_minus5_is_shifted(self):
        r = fs.host_clock_status(at(7, -5, "CDT"))
        self.assertTrue(r["host_clock_shifted"], r)

    @unittest.skipUnless(HAVE_TZDATA, "tzdata unavailable")
    def test_summer_plus2_is_shifted_and_formatted(self):
        r = fs.host_clock_status(at(7, 2, "Romance Daylight Time"))
        self.assertTrue(r["host_clock_shifted"], r)
        self.assertEqual(r["host_clock_offset"], "+02:00")
        self.assertEqual(r["host_clock"], "Romance Daylight Time (UTC+02:00)")

    def test_offset_formatting_handles_half_hours_and_sign(self):
        self.assertEqual(fs._fmt_offset(datetime.timedelta(hours=5, minutes=30)), "+05:30")
        self.assertEqual(fs._fmt_offset(datetime.timedelta(hours=-3, minutes=-30)), "-03:30")
        self.assertEqual(fs._fmt_offset(datetime.timedelta(0)), "+00:00")


if __name__ == "__main__":
    unittest.main(verbosity=1)
