"""Thresholds in state-freshness-probe.py must track the fleet's real cadence.

Since 2026-09-17 every routine except ora-am-brief and the dead-man chain runs at most
once a week, so a 48h default flags every weekly producer as [STALE] on days 3-7 of its
cycle. The default must cover one weekly cycle plus grace. The daily-or-faster producers
must stay tight, or a dead heartbeat/watchdog would go unreported for a week.
"""
import importlib.util
import pytest  # noqa: F401  (tmp_path / monkeypatch / capsys fixtures)
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


def test_windows_producers_are_never_pause_suppressed(tmp_path, monkeypatch, capsys):
    """Merge-gate R3 finding (2026-09-22): a CC fleet pause does not pause the Windows
    Task Scheduler producers. Once the ora-am-brief carve-out made CC pauses visible, a
    dead dead-man written 72h ago, after the pause began, was being reported [PAUSED]
    instead of [STALE]. The fleet-independent producers must alarm regardless."""
    import time as _t
    now = _t.time()
    pause_start = now - 5 * 86400          # pause began 5 days ago
    stale_mtime = now - 72 * 3600          # written AFTER the pause began, 72h ago (> 48h)
    (tmp_path / "_state").mkdir()
    for name in FAST_PRODUCERS:
        rel = ("_state/" + name) if name.endswith(".json") else name
        p = tmp_path / rel
        p.write_text("x")
        os.utime(p, (stale_mtime, stale_mtime))
    # and one ordinary CC-produced file, which SHOULD still be pause-explained
    cc = tmp_path / "_state" / "registry-membership.log"
    cc.write_text("x")
    os.utime(cc, (pause_start + 3600, pause_start + 3600))
    monkeypatch.setattr(sfp, "HERE", str(tmp_path))
    monkeypatch.setattr(sfp, "DEFAULT_MAX_AGE_H", 24.0)  # make the CC file stale too
    monkeypatch.setattr(sfp.fleet_pause, "pause_state", lambda f: (
        {"paused": True, "paused_since": pause_start, "resume_epoch": now + 86400, "error": None}
        if f == "cc" else {"paused": False, "paused_since": None, "resume_epoch": None, "error": None}))
    rc = sfp.main()
    out = capsys.readouterr().out
    for name in FAST_PRODUCERS:
        assert "[STALE] " in "\n".join(l for l in out.splitlines() if name in l), (name, out)
    assert "[PAUSED]" in "\n".join(l for l in out.splitlines() if "registry-membership.log" in l), out
    assert rc == 1


def test_no_override_is_looser_than_default():
    for name, hours in sfp.MAX_AGE_OVERRIDES.items():
        assert hours <= sfp.DEFAULT_MAX_AGE_H, name
