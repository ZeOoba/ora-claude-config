#!/usr/bin/env python3
"""Tests for agent-usage-report.py. Run: python test-agent-usage-report.py (stdlib only)."""
import datetime
import importlib.util
import json
import os
import subprocess
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
            f.write(_line("t4", "alpha", ts="2026-09-10T08:00:00Z") + "\n")
            f.write("subagent_type but not json\n")
        found, scanned, oldest = m.count_dispatches(
            os.path.join(d, "projects"), ["alpha", "beta"], 0)
    assert len(found["alpha"]) == 3 and len(found["beta"]) == 0, found
    assert scanned == 1 and oldest == "2026-09-10", (scanned, oldest)
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


def _iso(days_ago):
    t = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days_ago)
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def test_window_excludes_old_files_and_old_dispatches_in_fresh_files():
    """--days must bound by the dispatch's own timestamp, not only the file mtime: an old
    dispatch inside a recently touched transcript must not mask a zero-use agent."""
    m = _load()
    now = time.time()
    since = now - 30 * 86400
    with tempfile.TemporaryDirectory() as d:
        proj = os.path.join(d, "projects", "p")
        os.makedirs(proj)
        old_file = os.path.join(proj, "old.jsonl")
        with open(old_file, "w", encoding="utf-8") as f:
            f.write(_line("o1", "alpha", ts=_iso(1)) + "\n")
        os.utime(old_file, (1e9, 1e9))                      # stale mtime -> skipped entirely
        with open(os.path.join(proj, "fresh.jsonl"), "w", encoding="utf-8") as f:
            f.write(_line("f1", "alpha", ts=_iso(90)) + "\n")   # old dispatch, fresh file
            f.write(_line("f2", "alpha", ts=_iso(2)) + "\n")    # in-window dispatch
        found, scanned, oldest = m.count_dispatches(
            os.path.join(d, "projects"), ["alpha"], since)
    assert found["alpha"] == {"f2"}, found
    assert scanned == 1, scanned
    print("  PASS test_window_excludes_old_files_and_old_dispatches_in_fresh_files")


def test_age_uses_first_git_commit_not_mtime_with_mtime_fallback_for_untracked():
    m = _load()
    env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@e.x",
               GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@e.x",
               GIT_AUTHOR_DATE="2026-01-05T12:00:00 +0000",
               GIT_COMMITTER_DATE="2026-01-05T12:00:00 +0000")
    with tempfile.TemporaryDirectory() as d:
        subprocess.run(["git", "init", "-q", d], check=True, env=env)
        tracked = os.path.join(d, "tracked.md")
        with open(tracked, "w", encoding="utf-8") as f:
            f.write("x\n")
        subprocess.run(["git", "-C", d, "add", "tracked.md"], check=True, env=env)
        subprocess.run(["git", "-C", d, "commit", "-q", "-m", "add"], check=True, env=env)
        now = time.time()
        os.utime(tracked, (now, now))                       # fresh mtime must NOT win
        untracked = os.path.join(d, "untracked.md")
        with open(untracked, "w", encoding="utf-8") as f:
            f.write("y\n")
        agents = m.list_agents(d)
    jan5 = datetime.datetime(2026, 1, 5, 12, tzinfo=datetime.timezone.utc).timestamp()
    assert abs(agents["tracked"] - jan5) < 86400, agents
    assert abs(agents["untracked"] - now) < 3600, agents    # mtime fallback
    print("  PASS test_age_uses_first_git_commit_not_mtime_with_mtime_fallback_for_untracked")


def test_min_age_boundary_is_inclusive():
    m = _load()
    now = time.time()
    agents = {"at": now - 30 * 86400 - 60, "under": now - 29 * 86400}
    found = {"at": set(), "under": set()}
    flags = {r["agent"]: r["flag"] for r in m.build_report(agents, found, 30, 30, now)}
    assert flags == {"at": "REVIEW", "under": "YOUNG"}, flags
    flags = {r["agent"]: r["flag"] for r in m.build_report(agents, found, 30, 10, now)}
    assert flags == {"at": "REVIEW", "under": "REVIEW"}, flags   # --min-age-days is honoured
    print("  PASS test_min_age_boundary_is_inclusive")


def test_malformed_lines_and_vanishing_files_do_not_abort_the_report():
    m = _load()
    with tempfile.TemporaryDirectory() as d:
        proj = os.path.join(d, "projects", "p")
        os.makedirs(proj)
        with open(os.path.join(proj, "a.jsonl"), "w", encoding="utf-8") as f:
            f.write('{"message": "a string subagent_type"}\n')        # message not a dict
            f.write('["subagent_type"]\n')                             # JSON but not an object
            f.write(_line("ok1", "alpha") + "\n")
        found, _, _ = m.count_dispatches(os.path.join(d, "projects"), ["alpha"], 0)
        assert found["alpha"] == {"ok1"}, found
        agents_dir = os.path.join(d, "agents")
        os.makedirs(agents_dir)
        gone = os.path.join(agents_dir, "gone.md")
        keep = os.path.join(agents_dir, "keep.md")
        for p in (gone, keep):
            with open(p, "w", encoding="utf-8") as f:
                f.write("x\n")
        real = m._first_commit_epoch

        def vanish(path):
            if path == gone:
                os.remove(gone)                              # moved/archived mid-run
            return None
        m._first_commit_epoch = vanish
        try:
            agents = m.list_agents(agents_dir)
        finally:
            m._first_commit_epoch = real
    assert "keep" in agents and "gone" not in agents, agents
    print("  PASS test_malformed_lines_and_vanishing_files_do_not_abort_the_report")



def main():
    test_counts_unique_ids_and_ignores_unknown_and_non_tool_lines()
    test_flags_zero_use_old_agents_review_and_young_agents_young()
    test_render_is_ascii_and_names_review_agents()
    test_missing_dirs_fail_open()
    test_window_excludes_old_files_and_old_dispatches_in_fresh_files()
    test_age_uses_first_git_commit_not_mtime_with_mtime_fallback_for_untracked()
    test_min_age_boundary_is_inclusive()
    test_malformed_lines_and_vanishing_files_do_not_abort_the_report()
    print("ALL AGENT-USAGE-REPORT TESTS PASS")


if __name__ == "__main__":
    main()
