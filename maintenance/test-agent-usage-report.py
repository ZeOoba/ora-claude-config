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


def _hermetic_git_env(date):
    """Env that ignores the machine's git config (hooks, templates, signing, identity)."""
    return dict(os.environ, GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
                GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@e.x",
                GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@e.x",
                GIT_AUTHOR_DATE=date, GIT_COMMITTER_DATE=date)


def _git(d, env, *args):
    base = ["git", "-C", d, "-c", "commit.gpgsign=false", "-c", "core.hooksPath=" + os.devnull]
    if args[0] == "init":
        subprocess.run(["git", "init", "--template=", "-q", d], check=True, env=env)
        return
    if args[0] == "commit":
        args = args + ("--no-verify",)
    subprocess.run(base + list(args), check=True, env=env)


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
    env = _hermetic_git_env("2026-01-05T12:00:00 +0000")
    with tempfile.TemporaryDirectory() as d:
        _git(d, env, "init", "-q")
        tracked = os.path.join(d, "tracked.md")
        with open(tracked, "w", encoding="utf-8") as f:
            f.write("x\n")
        _git(d, env, "add", "tracked.md")
        _git(d, env, "commit", "-q", "-m", "add")
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



def test_first_commit_age_is_the_earliest_add_even_after_delete_and_readd():
    m = _load()
    with tempfile.TemporaryDirectory() as d:
        f = os.path.join(d, "a.md")
        _git(d, _hermetic_git_env("2026-01-05T12:00:00 +0000"), "init")
        for date, action in (("2026-01-05T12:00:00 +0000", "add"),
                             ("2026-02-05T12:00:00 +0000", "rm"),
                             ("2026-03-05T12:00:00 +0000", "add")):
            env = _hermetic_git_env(date)
            if action == "add":
                with open(f, "w", encoding="utf-8") as fh:
                    fh.write(date + "\n")
                _git(d, env, "add", "a.md")
            else:
                _git(d, env, "rm", "-q", "a.md")
            _git(d, env, "commit", "-q", "-m", action)
        epoch = m._first_commit_epoch(f)
    jan5 = datetime.datetime(2026, 1, 5, 12, tzinfo=datetime.timezone.utc).timestamp()
    assert epoch is not None and abs(epoch - jan5) < 86400, epoch
    print("  PASS test_first_commit_age_is_the_earliest_add_even_after_delete_and_readd")


def test_main_honours_days_window_and_timestampless_dispatch_fails_open():
    m = _load()
    with tempfile.TemporaryDirectory() as d:
        agents = os.path.join(d, "agents")
        proj = os.path.join(d, "projects", "p")
        os.makedirs(agents)
        os.makedirs(proj)
        for name in ("alpha", "beta"):
            with open(os.path.join(agents, name + ".md"), "w", encoding="utf-8") as f:
                f.write("x\n")
        with open(os.path.join(proj, "s.jsonl"), "w", encoding="utf-8") as f:
            f.write(_line("old1", "alpha", ts=_iso(200)) + "\n")      # out of a 30-day window
            nots = json.loads(_line("nots1", "beta"))
            del nots["timestamp"]                                      # absent -> keep (fail open)
            f.write(json.dumps(nots) + "\n")
        out = os.path.join(d, "out.json")
        rc = m.main(["--days", "30", "--agents-dir", agents,
                     "--projects-dir", os.path.join(d, "projects"), "--json", "--out", out])
        rows = {r["agent"]: r for r in json.load(open(out, encoding="utf-8"))}
    assert rc == 0
    assert rows["alpha"]["dispatches"] == 0, rows       # --days reached count_dispatches
    assert rows["beta"]["dispatches"] == 1, rows        # timestamp-less line still counted
    print("  PASS test_main_honours_days_window_and_timestampless_dispatch_fails_open")


def test_ts_epoch_parses_z_offsets_and_treats_naive_as_utc():
    m = _load()
    z = m._ts_epoch("2026-09-20T10:00:00Z")
    assert z == m._ts_epoch("2026-09-20T10:00:00+00:00") == m._ts_epoch("2026-09-20T10:00:00")
    assert m._ts_epoch("2026-09-20T10:00:00-05:00") == z + 5 * 3600
    for bad in ("", "garbage", None, 1727000000):
        assert m._ts_epoch(bad) is None, bad
    print("  PASS test_ts_epoch_parses_z_offsets_and_treats_naive_as_utc")


def test_wrongly_typed_fields_in_a_line_do_not_lose_the_valid_dispatches():
    m = _load()
    with tempfile.TemporaryDirectory() as d:
        proj = os.path.join(d, "projects", "p")
        os.makedirs(proj)
        good = _line("good", "alpha")
        bad_lines = []
        for mut in (lambda o: o.update(timestamp=1727000000),
                    lambda o: o["message"]["content"][0].update(input="subagent_type"),
                    lambda o: o["message"]["content"][0]["input"].update(subagent_type=["alpha"]),
                    lambda o: o["message"]["content"][0].update(id={"x": 1})):
            o = json.loads(_line("bad", "alpha"))
            mut(o)
            bad_lines.append(json.dumps(o))
        with open(os.path.join(proj, "a.jsonl"), "w", encoding="utf-8") as f:
            f.write("\n".join(bad_lines + [good]) + "\n")
        found, _, _ = m.count_dispatches(os.path.join(d, "projects"), ["alpha"], 0)
    assert "good" in found["alpha"], found
    print("  PASS test_wrongly_typed_fields_in_a_line_do_not_lose_the_valid_dispatches")



def _wf_file(projects, session, run_id, script, days_ago, fname=None):
    d = os.path.join(projects, "p", session, "workflows")
    os.makedirs(d, exist_ok=True)
    body = {"runId": run_id, "timestamp": _iso(days_ago), "script": script,
            "status": "completed", "workflowProgress": []}
    with open(os.path.join(d, fname or (run_id + ".json")), "w", encoding="utf-8") as f:
        json.dump(body, f)


def test_workflow_runs_are_counted_by_script_reference_within_window():
    """Workflow scripts dispatch with agent(prompt, {agentType: 'name'}); the run JSON keeps
    the script, so a run that references an agent is evidence the agent is in use."""
    m = _load()
    since = time.time() - 30 * 86400
    with tempfile.TemporaryDirectory() as d:
        pr = os.path.join(d, "projects")
        _wf_file(pr, "s1", "wf_a", "await agent('x', { agentType:'alpha', label:'a' })", 2)
        _wf_file(pr, "s1", "wf_b", 'agent(p, {agentType: "alpha"}); agent(q,{agentType:"beta"})', 3)
        _wf_file(pr, "s1", "wf_old", "agent(p, {agentType:'alpha'})", 90)        # out of window
        _wf_file(pr, "s2", "wf_a", "agent(p, {agentType:'alpha'})", 2, "copy.json")  # same runId
        _wf_file(pr, "s1", "wf_c", "agent(p, {agentType:'alpha-extra'})", 2)     # not 'alpha'
        _wf_file(pr, "s1", "wf_none", "agent(p, {label:'no type'})", 2)
        runs = m.count_workflow_runs(pr, ["alpha", "beta"], since)
    assert runs["alpha"] == {"wf_a", "wf_b"}, runs
    assert runs["beta"] == {"wf_b"}, runs
    print("  PASS test_workflow_runs_are_counted_by_script_reference_within_window")


def test_workflow_counter_fails_open_on_bad_files_and_missing_dirs():
    m = _load()
    with tempfile.TemporaryDirectory() as d:
        pr = os.path.join(d, "projects")
        wd = os.path.join(pr, "p", "s", "workflows")
        os.makedirs(wd)
        with open(os.path.join(wd, "wf_bad.json"), "w", encoding="utf-8") as f:
            f.write("{not json")
        with open(os.path.join(wd, "wf_list.json"), "w", encoding="utf-8") as f:
            f.write("[1, 2]")
        _wf_file(pr, "s", "wf_ok", "agent(p, {agentType:'alpha'})", 1)
        runs = m.count_workflow_runs(pr, ["alpha"], 0)
    assert runs == {"alpha": {"wf_ok"}}, runs
    assert m.count_workflow_runs(os.path.join(HERE, "zz-nope"), ["a"], 0) == {"a": set()}
    print("  PASS test_workflow_counter_fails_open_on_bad_files_and_missing_dirs")


def test_workflow_use_clears_the_review_flag_and_is_shown_in_the_report():
    m = _load()
    now = time.time()
    agents = {"wfonly": now - 90 * 86400, "idle": now - 90 * 86400}
    found = {"wfonly": set(), "idle": set()}
    wf = {"wfonly": {"wf_1", "wf_2"}, "idle": set()}
    rows = {r["agent"]: r for r in m.build_report(agents, found, 30, 30, now, wf)}
    assert rows["wfonly"]["flag"] == "ok" and rows["wfonly"]["workflow_runs"] == 2, rows
    assert rows["idle"]["flag"] == "REVIEW" and rows["idle"]["workflow_runs"] == 0, rows
    out = m.render(list(rows.values()), 30, 10, None, "2026-10-01")
    assert "Workflow runs" in out and "runs, not dispatches" in out, out
    print("  PASS test_workflow_use_clears_the_review_flag_and_is_shown_in_the_report")


def test_main_counts_workflow_runs_end_to_end():
    m = _load()
    with tempfile.TemporaryDirectory() as d:
        agents = os.path.join(d, "agents")
        os.makedirs(agents)
        for name in ("alpha", "beta"):
            with open(os.path.join(agents, name + ".md"), "w", encoding="utf-8") as f:
                f.write("x\n")
        pr = os.path.join(d, "projects")
        _wf_file(pr, "s", "wf_1", "agent(p, {agentType:'alpha'})", 2)
        out = os.path.join(d, "out.json")
        rc = m.main(["--days", "30", "--agents-dir", agents, "--projects-dir", pr,
                     "--json", "--out", out])
        rows = {r["agent"]: r for r in json.load(open(out, encoding="utf-8"))}
    assert rc == 0
    assert rows["alpha"]["workflow_runs"] == 1 and rows["alpha"]["flag"] == "ok", rows
    assert rows["beta"]["workflow_runs"] == 0, rows
    print("  PASS test_main_counts_workflow_runs_end_to_end")



def main():
    test_counts_unique_ids_and_ignores_unknown_and_non_tool_lines()
    test_flags_zero_use_old_agents_review_and_young_agents_young()
    test_render_is_ascii_and_names_review_agents()
    test_missing_dirs_fail_open()
    test_window_excludes_old_files_and_old_dispatches_in_fresh_files()
    test_age_uses_first_git_commit_not_mtime_with_mtime_fallback_for_untracked()
    test_min_age_boundary_is_inclusive()
    test_malformed_lines_and_vanishing_files_do_not_abort_the_report()
    test_first_commit_age_is_the_earliest_add_even_after_delete_and_readd()
    test_main_honours_days_window_and_timestampless_dispatch_fails_open()
    test_ts_epoch_parses_z_offsets_and_treats_naive_as_utc()
    test_wrongly_typed_fields_in_a_line_do_not_lose_the_valid_dispatches()
    test_workflow_runs_are_counted_by_script_reference_within_window()
    test_workflow_counter_fails_open_on_bad_files_and_missing_dirs()
    test_workflow_use_clears_the_review_flag_and_is_shown_in_the_report()
    test_main_counts_workflow_runs_end_to_end()
    print("ALL AGENT-USAGE-REPORT TESTS PASS")


if __name__ == "__main__":
    main()
