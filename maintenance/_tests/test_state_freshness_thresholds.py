"""Thresholds in state-freshness-probe.py must track the fleet's real cadence.

Since 2026-09-17 every routine except ora-am-brief and the dead-man chain runs at most
once a week, so a 48h default flags every weekly producer as [STALE] on days 3-7 of its
cycle. The default must cover one weekly cycle plus grace. The daily-or-faster producers
must stay tight, or a dead heartbeat/watchdog would go unreported for a week.
"""
import importlib.util
import os

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "sfp", os.path.join(HERE, "..", "state-freshness-probe.py"))
sfp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sfp)

FAST_PRODUCERS = (
    "fleet-deadman.log",            # ORA Fleet Dead-Man, daily
    "push-fleet-heartbeat.log",     # ORA Fleet Heartbeat Push, daily
    "heartbeat-publish-ok.json",    # ORA Fleet Heartbeat Push, daily
    "stuck-session-watchdog.log",   # ORA Stuck-Session Watchdog, every 30 min
    "fleet-pause-windows.json",     # ORA Fleet Pause-Resume Guard, every 6h
    "fleet-heartbeat.json",         # emit-fleet-heartbeat.py, sub-daily
)


def test_default_covers_one_weekly_cycle_plus_grace():
    assert sfp.DEFAULT_MAX_AGE_H >= 7 * 24 + 12
    assert sfp.DEFAULT_MAX_AGE_H <= 8 * 24


def test_fast_producers_stay_tight():
    for name in FAST_PRODUCERS:
        assert sfp.MAX_AGE_OVERRIDES.get(name, sfp.DEFAULT_MAX_AGE_H) <= 48, name


def test_no_override_is_looser_than_default():
    for name, hours in sfp.MAX_AGE_OVERRIDES.items():
        assert hours <= sfp.DEFAULT_MAX_AGE_H, name
