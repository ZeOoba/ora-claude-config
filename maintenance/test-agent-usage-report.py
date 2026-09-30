#!/usr/bin/env python3
"""Tests for agent-usage-report.py. Run: python test-agent-usage-report.py (stdlib only)."""
import importlib.util
import json
import os
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))


def _load():
    spec = importlib.util.spec_from_file_location(
        "agent_usage_report", os.path.join(HERE, "agent-usage-report.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _line(tool_id, subagent, name="Agent", ts="2026-09-20T10:00:00Z"):
    return json.dumps({"timestamp": ts, "message": {"content": [
        {"type": "tool_use", "id": tool_id, "name": name,
         "input": {"subagent_type": subagent, "description": "d"}}]}})


def test_counts_unique_ids_and_ignores_unknown_and_non_tool_lines():
    m = _load()
    with tempfile.TemporaryDirectory() as d:
        proj = os.path.join(d, "projects", "p")
        os.makedirs(proj)
        with open(os.path.join(proj, "a.jsonl"), "w", encoding="utf-8") as f:
            f.write(_line("t1", "alpha") + "\n")
            f.write(_line("t1", "alpha") + "\n")      # duplicate id (per-block lines)
            f.write(_line("t2", "alpha", name="Task") + "\n")
            f.write(_line("t3", "not-an-agent") + "\n")
            f.write("subagent_type but not json\n")
        found, scanned, oldest = m.count_dispatches(
            os.path.join(d, "projects"), ["alpha", "beta"], 0)
    assert len(found["alpha"]) == 2 and len(found["beta"]) == 0, found
    assert scanned == 1 and oldest == "2026-09-20", (scanned, oldest)
    print("  PASS test_counts_unique_ids_and_ignores_unknown_and_non_tool_lines")


def test_flags_zero_use_old_agents_review_and_young_agents_young():
    m = _load()
    now = time.time()
    agents = {"used": now - 90 * 86400, "old-zero": now - 90 * 86400, "young-zero": now - 5 * 86400}
    found = {"used": {"x"}, "old-zero": set(), "young-zero": set()}
    rows = {r["agent"]: r["flag"] for r in m.build_report(agents, found, 30, 30, now)}
    assert rows == {"used": "ok", "old-zero": "REVIEW", "young-zero": "YOUNG"}, rows
    print("  PASS test_flags_zero_use_old_agents_review_and_young_agents_young")


def test_render_is_ascii_and_names_review_agents():
    m = _load()
    rows = [{"agent": "a", "dispatches": 0, "def_age_days": 60, "flag": "REVIEW"}]
    out = m.render(rows, 30, 10, None, "2026-10-01")
    out.encode("ascii")
    assert "REVIEW: a" in out
    print("  PASS test_render_is_ascii_and_names_review_agents")


def test_missing_dirs_fail_open():
    m = _load()
    assert m.list_agents(os.path.join(HERE, "zz-nope")) == {}
    found, scanned, oldest = m.count_dispatches(os.path.join(HERE, "zz-nope"), ["a"], 0)
    assert found == {"a": set()} and scanned == 0 and oldest is None
    print("  PASS test_missing_dirs_fail_open")


def main():
    test_counts_unique_ids_and_ignores_unknown_and_non_tool_lines()
    test_flags_zero_use_old_agents_review_and_young_agents_young()
    test_render_is_ascii_and_names_review_agents()
    test_missing_dirs_fail_open()
    print("ALL AGENT-USAGE-REPORT TESTS PASS")


if __name__ == "__main__":
    main()
