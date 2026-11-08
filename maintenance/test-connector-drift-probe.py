#!/usr/bin/env python3
"""Tests for connector-drift-probe.py (TDD).

Runs the probe as a subprocess against synthetic fixtures (a roster markdown file,
a .claude.json, and a settings.json) via the --roster/--claude-json/--settings
overrides, and asserts the exit-code contract (0 clean / 1 drift / 2 probe error)
and the finding content.

Run: python test-connector-drift-probe.py
Pure stdlib. ASCII-only output.
"""
import os
import sys
import json
import tempfile
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
PROBE = os.path.join(HERE, "connector-drift-probe.py")

_failures = []


def _write(text, suffix):
    fd, path = tempfile.mkstemp(prefix="cdp-", suffix=suffix)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(text)
    return path


def roster(lines):
    return ("intro prose\n\n<!--BEGIN-CONNECTOR-ROSTER-->\n"
            "<!-- machine-readable; the probe parses `- name | state=.. | verify=..` lines -->\n"
            + "\n".join(lines) + "\n<!--END-CONNECTOR-ROSTER-->\n\ntrailing prose\n")


def claude_json(keys):
    return json.dumps({"mcpServers": {k: {"command": "x"} for k in keys}})


def settings_json(prefixes):
    allow = ["mcp__%s__sometool" % p for p in prefixes]
    return json.dumps({"permissions": {"allow": allow + ["Bash", "Read"]}})


def run(roster_lines, json_keys, allow_prefixes):
    rp = _write(roster(roster_lines), "-roster.md")
    cj = _write(claude_json(json_keys), "-claude.json")
    sj = _write(settings_json(allow_prefixes), "-settings.json")
    proc = subprocess.run(
        [sys.executable, PROBE, "--roster=" + rp, "--claude-json=" + cj, "--settings=" + sj],
        capture_output=True, text=True,
    )
    return proc.returncode, proc.stdout + proc.stderr


def check(name, cond, detail=""):
    if cond:
        print("  PASS " + name)
    else:
        print("  FAIL " + name + "  " + detail)
        _failures.append(name)


def test_all_consistent_clean():
    rc, out = run(
        ["- fred | state=active | verify=json:fred",
         "- excel | state=active | verify=json:excel",
         "- Notion | state=active | verify=allow:c5f4869f",
         "- computer-use | state=active | verify=cloud",
         "- Grain | state=retired | verify=allow:468d2dad"],
        json_keys=["fred", "excel"],
        allow_prefixes=["c5f4869f"],
    )
    check("test_all_consistent_clean", rc == 0, "expected exit 0, got %s\n%s" % (rc, out))


def test_active_but_dead_json_flags():
    # documented active, but the json key is absent -> drift (the Grain/Windows-MCP class).
    rc, out = run(
        ["- fred | state=active | verify=json:fred"],
        json_keys=[],           # fred NOT registered
        allow_prefixes=[],
    )
    check("test_active_but_dead_json_flags", rc == 1 and "fred" in out,
          "expected exit 1 naming fred, got %s\n%s" % (rc, out))


def test_active_but_dead_allow_flags():
    rc, out = run(
        ["- Notion | state=active | verify=allow:c5f4869f"],
        json_keys=[],
        allow_prefixes=[],      # no notion prefix
    )
    check("test_active_but_dead_allow_flags", rc == 1 and "Notion" in out,
          "expected exit 1 naming Notion, got %s\n%s" % (rc, out))


def test_retired_but_live_json_flags():
    # The exact FRED failure: documented retired, but actually registered in .claude.json.
    rc, out = run(
        ["- fred | state=retired | verify=json:fred"],
        json_keys=["fred"],     # fred IS live
        allow_prefixes=[],
    )
    check("test_retired_but_live_json_flags", rc == 1 and "fred" in out,
          "expected exit 1 naming fred, got %s\n%s" % (rc, out))


def test_retired_but_live_allow_flags():
    rc, out = run(
        ["- Grain | state=retired | verify=allow:468d2dad"],
        json_keys=[],
        allow_prefixes=["468d2dad"],   # Grain came back
    )
    check("test_retired_but_live_allow_flags", rc == 1 and "Grain" in out,
          "expected exit 1 naming Grain, got %s\n%s" % (rc, out))


def test_orphan_json_key_flags():
    # A live mcpServers key with NO json: roster line -> undocumented live connector.
    rc, out = run(
        ["- fred | state=active | verify=json:fred"],
        json_keys=["fred", "context7"],   # context7 live but not in roster
        allow_prefixes=[],
    )
    check("test_orphan_json_key_flags", rc == 1 and "context7" in out,
          "expected exit 1 naming context7 orphan, got %s\n%s" % (rc, out))


def test_cloud_never_flags():
    # cloud entries are informational -- neither active nor retired cloud entries drift.
    rc, out = run(
        ["- computer-use | state=active | verify=cloud",
         "- Rube | state=retired | verify=cloud"],
        json_keys=[],
        allow_prefixes=[],
    )
    check("test_cloud_never_flags", rc == 0, "expected exit 0, got %s\n%s" % (rc, out))


def test_missing_markers_is_probe_error():
    rp = _write("no markers here at all\n", "-roster.md")
    cj = _write(claude_json(["fred"]), "-claude.json")
    sj = _write(settings_json([]), "-settings.json")
    proc = subprocess.run(
        [sys.executable, PROBE, "--roster=" + rp, "--claude-json=" + cj, "--settings=" + sj],
        capture_output=True, text=True)
    check("test_missing_markers_is_probe_error", proc.returncode == 2,
          "expected exit 2, got %s\n%s" % (proc.returncode, proc.stdout + proc.stderr))


def test_unreadable_claude_json_is_probe_error():
    rp = _write(roster(["- fred | state=active | verify=json:fred"]), "-roster.md")
    sj = _write(settings_json([]), "-settings.json")
    proc = subprocess.run(
        [sys.executable, PROBE, "--roster=" + rp,
         "--claude-json=" + os.path.join(tempfile.gettempdir(), "does-not-exist-cdp.json"),
         "--settings=" + sj],
        capture_output=True, text=True)
    check("test_unreadable_claude_json_is_probe_error", proc.returncode == 2,
          "expected exit 2, got %s\n%s" % (proc.returncode, proc.stdout + proc.stderr))


def test_malformed_roster_line_flags():
    # A roster line with an unknown verify scheme is a probe error (fail loud, not silent).
    rc, out = run(
        ["- weird | state=active | verify=banana:xyz"],
        json_keys=[],
        allow_prefixes=[],
    )
    check("test_malformed_roster_line_flags", rc == 2,
          "expected exit 2 on unknown verify scheme, got %s\n%s" % (rc, out))


_env_skips = []


def test_live_probe_smoke():
    # The probe with NO overrides runs against the real tree; it must not crash (exit 0/1,
    # never 2). If the real roster block is absent yet, this is skipped by the caller.
    # ~/.claude.json is the live per-machine Claude Code config (outside the repo, never
    # committed): a clean checkout (CI, 2026-11-06) has none, and the probe then exits 2
    # BY DESIGN (test_unreadable_claude_json_is_probe_error pins that). Only its absence
    # skips this case; a present-but-broken file still fails here.
    live_cj = os.path.join(os.path.expanduser("~"), ".claude.json")
    if not os.path.exists(live_cj):
        _env_skips.append("test_live_probe_smoke (no live %s)" % live_cj)
        return
    proc = subprocess.run([sys.executable, PROBE], capture_output=True, text=True)
    check("test_live_probe_smoke", proc.returncode in (0, 1),
          "live probe should exit 0 or 1, got %s\n%s" % (proc.returncode, proc.stdout + proc.stderr))


if __name__ == "__main__":
    test_all_consistent_clean()
    test_active_but_dead_json_flags()
    test_active_but_dead_allow_flags()
    test_retired_but_live_json_flags()
    test_retired_but_live_allow_flags()
    test_orphan_json_key_flags()
    test_cloud_never_flags()
    test_missing_markers_is_probe_error()
    test_unreadable_claude_json_is_probe_error()
    test_malformed_roster_line_flags()
    test_live_probe_smoke()
    if _failures:
        print("\n%d FAILURE(S): %s" % (len(_failures), ", ".join(_failures)))
        sys.exit(1)
    if _env_skips:
        # Only after every other case passed: the sentinel never masks a failure.
        print("CANNOT RUN: %s; all other connector-drift-probe tests passed."
              % "; ".join(_env_skips))
        sys.exit(1)
    print("\nALL connector-drift-probe tests passed.")
    sys.exit(0)
