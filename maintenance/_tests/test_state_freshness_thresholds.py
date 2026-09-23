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
    "backup-push-ok.json",          # ORA Fleet Heartbeat Push backup step, daily (OI-331)
    "stuck-session-watchdog.log",   # ORA Stuck-Session Watchdog, every 30 min
    "phantom-dispatch.log",         # phantom-dispatch-probe.py, run daily by ORA Fleet Dead-Man (R6)
    "phantom-dispatch.json",        # same
    "ensure-claude-renderer.log",   # ORA Claude Desktop Wake-and-Launch, daily (R6)
    "pause-resume-guard-state.json",  # ORA Fleet Pause-Resume Guard, save_state() every 6h run (R7)
)

# Every watched file a Windows Task Scheduler job writes (enumerated from the live ORA*
# tasks and their scripts, merge-gate R6, 2026-09-22). All must be pause-independent;
# only the daily-or-faster ones get the tight 48h override (ora-nightly-disk is weekly).
WINDOWS_PRODUCED = FAST_PRODUCERS + (
    "fleet-deadman.start.log",
    "push-fleet-heartbeat.start.log",
    "ora-nightly-disk.log",         # ORA Nightly Disk Clean, WEEKLY since 2026-09-17
    "task-folder-registration.log", # ORA Headless - stranded-spec, WEEKLY (merge-gate R8)
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
    # R4: the stated reason must be the true one -- these files were written AFTER the
    # pause began; they are stale because they run outside the fleets, not "already stale".
    dm_line = "\n".join(l for l in out.splitlines() if "fleet-deadman.log" in l)
    assert "outside the scheduled-task fleets" in dm_line and "ALREADY stale" not in dm_line, dm_line
    assert rc == 1


def test_pause_windows_is_event_driven_not_periodic():
    """Merge-gate R5: pause_windows.capture() saves only when a hold starts or ends, so
    fleet-pause-windows.json is untouched for as long as the fleet is live. A 48h (or any)
    age limit false-alarms 48h after every pause ends."""
    assert "fleet-pause-windows.json" in sfp.NOT_PERIODIC
    assert "fleet-pause-windows.json" not in sfp.MAX_AGE_OVERRIDES
    assert "fleet-pause-windows.json" not in sfp.PAUSE_INDEPENDENT


def test_every_windows_produced_file_is_pause_independent():
    """Merge-gate R6: two daily Windows producers (phantom-dispatch via the dead-man,
    ensure-claude-renderer via Wake-and-Launch) and the weekly disk-clean log were
    missing, so a CC pause could 'explain' them going dead."""
    missing = [n for n in WINDOWS_PRODUCED if n not in sfp.PAUSE_INDEPENDENT]
    assert not missing, missing
    extra = sorted(set(sfp.PAUSE_INDEPENDENT) - set(WINDOWS_PRODUCED))
    assert not extra, ("PAUSE_INDEPENDENT lists files no Windows job writes", extra)


def test_watched_fleet_heartbeat_copy_is_a_weekly_cc_output():
    """Merge-gate R9: the WATCHED ~/.claude copy of fleet-heartbeat.json is written by the
    weekly CC ora-task-integrity-guard (STEP 1.5). The daily Windows Heartbeat Push runs the
    emitter from the main-checkout worktree, so it writes THAT worktree's copy. Pinning the
    watched copy at 48h / pause-independent false-alarmed on every manual probe run."""
    assert "fleet-heartbeat.json" not in sfp.MAX_AGE_OVERRIDES
    assert "fleet-heartbeat.json" not in sfp.PAUSE_INDEPENDENT


def test_weekly_windows_producer_keeps_the_weekly_limit():
    assert "ora-nightly-disk.log" not in sfp.MAX_AGE_OVERRIDES


def test_event_driven_windows_files_are_not_periodic():
    """Merge-gate R7: failure markers and on-change records are skipped, not aged. The
    pause-resume guard's own state file is NOT one of them: it is saved on every run."""
    assert "heartbeat-publish-failed.json" in sfp.NOT_PERIODIC
    assert "pause-resume-guard-state.json" not in sfp.NOT_PERIODIC


def test_start_logs_are_never_pause_explained():
    """Merge-gate R5: the *.start.log breadcrumbs are written by the same Windows tasks as
    the verdict logs, which keep running through a fleet pause."""
    assert {"fleet-deadman.start.log", "push-fleet-heartbeat.start.log"} <= sfp.PAUSE_INDEPENDENT


def test_weekly_producer_frozen_by_a_long_pause_is_pause_explained(tmp_path, monkeypatch, capsys):
    """Merge-gate R7: a weekly CC producer last written 72h BEFORE the pause began was
    not stale then (72h < 192h); the pause stopped its next run. It must read [PAUSED],
    not a false '[STALE] ALREADY stale before the pause began'. The old test used a flat
    6h grace instead of the file's own limit."""
    import time as _t
    now = _t.time()
    pause_start = now - 5 * 86400
    (tmp_path / "_state").mkdir()
    weekly = tmp_path / "_state" / "weekly-detector.json"
    weekly.write_text("x")
    os.utime(weekly, (pause_start - 72 * 3600, pause_start - 72 * 3600))   # 192h old now
    really_stale = tmp_path / "_state" / "dead-detector.json"
    really_stale.write_text("x")
    os.utime(really_stale, (pause_start - 200 * 3600, pause_start - 200 * 3600))  # > limit at pause start
    monkeypatch.setattr(sfp, "HERE", str(tmp_path))
    monkeypatch.setattr(sfp.fleet_pause, "pause_state", lambda f: (
        {"paused": True, "paused_since": pause_start, "resume_epoch": now + 86400, "error": None}
        if f == "cc" else {"paused": False, "paused_since": None, "resume_epoch": None, "error": None}))
    rc = sfp.main()
    out = capsys.readouterr().out
    wl = "\n".join(l for l in out.splitlines() if "weekly-detector.json" in l)
    dl = "\n".join(l for l in out.splitlines() if "dead-detector.json" in l)
    assert "[PAUSED]" in wl, wl
    # R8: the stated reason must be true -- this file was written BEFORE the pause began
    assert "within its limit when the pause began" in wl and "written after the pause began" not in wl, wl
    # the genuinely stale one is still a finding, with the true (CC-branch) reason
    assert "[STALE]" in dl and "ALREADY stale before the pause began" in dl, dl
    assert rc == 1


def test_no_override_is_looser_than_default():
    for name, hours in sfp.MAX_AGE_OVERRIDES.items():
        assert hours <= sfp.DEFAULT_MAX_AGE_H, name


if __name__ == "__main__":
    # The pre-push hook-tests gate runs every _tests file as `python <file>` (merge-gate R4:
    # without this block the file ran zero assertions under the gate and always exited 0).
    import sys
    sys.exit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))
