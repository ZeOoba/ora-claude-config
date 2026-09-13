#!/usr/bin/env python3
"""Tests for live-branch-drift-probe.py (TDD -- written before the code).

The defect this guards (observed 2026-09-13): the primary checkout ~/.claude
sat on a long-lived feature branch well behind origin/main. Three push
blockers in one day were fixes already merged to main but absent from the
live branch -- a stale hook test, a stale UNTRACKED copy of a SKILL.md that
main tracks, and a test synced to main whose module under test was not (and
whose main version imports a module the branch does not have at all). Every
one was knowable in advance from three trees: working tree, HEAD, base.

The contract under test:

  1. Classes: BEHIND_BASE, DIVERGED, BASE_ONLY (+UNTRACKED_STALE sub-flag,
     with historical-blob match), LOCAL_DIRTY_OVER_BEHIND. Paths identical to
     base, local-only work, and out-of-scope paths are never drift.
  2. Dependency hint: a behind .py whose BASE version imports a sibling module
     (hooks/lib, maintenance/_shared) that is BASE_ONLY reports sync_requires.
  3. Test-coupling hint: a behind module whose test is already synced (or the
     reverse) is called out.
  4. Fetch is default, timeout-bounded and FAIL-OPEN (warning, probe still
     runs); --no-fetch skips it.
  5. Exit 0 no drift / 1 drift / 2 probe error, and RESULT_JSON= always last.
  6. READ-ONLY: HEAD, branch, index bytes and status are unchanged by a run.

Run: python maintenance/_tests/test_live_branch_drift_probe.py
Pure stdlib. ASCII-only. Temp fixture repos only -- never the real ~/.claude.
"""
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
MAINT = os.path.dirname(HERE)
PROBE = os.path.join(MAINT, "live-branch-drift-probe.py")
sys.path.insert(0, os.path.abspath(os.path.join(MAINT, "..", "hooks", "tests", "lib")))
import gitfixture  # noqa: E402  (shared repo fixture -- open-items-tracker.md#OI-061)

# Exit-code contract, literal on purpose so a silent renumbering fails here.
EXIT_NO_DRIFT = 0
EXIT_DRIFT = 1
EXIT_ERROR = 2

results = []


def expect(label, cond, detail=""):
    results.append((bool(cond), label))
    print("  %s %s%s" % ("PASS" if cond else "FAIL:", label,
                         "" if cond else "  -- " + str(detail)[:600]))


# --------------------------------------------------------------------------
# fixture helpers
# --------------------------------------------------------------------------
def g(repo, *args):
    proc = gitfixture.git(repo, *args)
    if proc.returncode != 0:
        raise RuntimeError("git %s failed: %s" % (" ".join(args), proc.stderr))
    return proc.stdout


def write(repo, rel, text):
    path = os.path.join(repo, rel)
    os.makedirs(os.path.dirname(path) or repo, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def commit(repo, files=None, deletes=(), msg="c"):
    for rel, text in (files or {}).items():
        write(repo, rel, text)
    for rel in deletes:
        g(repo, "rm", "-q", rel)
    g(repo, "add", "-A")
    g(repo, "commit", "-q", "-m", msg)


BASE_FILES = {
    "README.md": "root\n",
    "docs/notes.md": "notes v1\n",
    "hooks/a.py": "A = 1\n",
    "hooks/b.py": "B = 1\n",
    "hooks/c.py": "C = 1\n",
    "hooks/gone.py": "G = 1\n",
    "hooks/lib/parse.py": "import os\n\ndef parse():\n    return 1\n",
    "hooks/lib/present.py": "P = 1\n",
    "hooks/tests/test-parse.py": "T = 1\n",
    "maintenance/tool.py": "X = 1\n",
    "maintenance/sub/deep.py": "D = 1\n",
    "maintenance/_tests/test_tool.py": "TT = 1\n",
    "settings.json": "{}\n",
    "CLAUDE.md": "doc v1\n",
    "agents/x.md": "agent v1\n",
}


def make_repo(files=None):
    """A repo on branch `feature`, with `main` at the same commit (merge-base)."""
    repo = gitfixture.repo_with_commit(files=dict(BASE_FILES if files is None else files),
                                       prefix="drift-probe-")
    g(repo, "branch", "-M", "main")
    g(repo, "branch", "feature")
    return repo


def to_feature(repo):
    g(repo, "checkout", "-q", "feature")


def run_probe(repo, *extra, base="main", fetch=False):
    args = [sys.executable, PROBE, "--repo", repo]
    if base is not None:
        args += ["--base", base]
    if not fetch:
        args.append("--no-fetch")
    args += list(extra)
    env = dict(os.environ)
    for k in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"):
        env.pop(k, None)
    proc = subprocess.run(args, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=120, env=env)
    report = None
    lines = proc.stdout.strip().splitlines()
    if "--json" in extra:
        try:
            report = json.loads(proc.stdout)
        except ValueError:
            report = None
    elif lines and lines[-1].startswith("RESULT_JSON="):
        report = json.loads(lines[-1][len("RESULT_JSON="):])
    return proc, report


def by_path(report):
    return {d["path"]: d for d in (report or {}).get("drift", [])}


# --------------------------------------------------------------------------
# tests
# --------------------------------------------------------------------------
def test_no_drift_when_identical_or_out_of_scope_or_local_ahead():
    print("no drift: identical / out-of-scope / local-ahead")
    repo = make_repo()
    commit(repo, {"docs/notes.md": "notes v2\n",           # out of scope
                  "maintenance/sub/deep.py": "D = 2\n"},    # not maintenance/*.py
           msg="main out-of-scope")
    to_feature(repo)
    commit(repo, {"hooks/a.py": "A = 'local'\n"}, msg="feature ahead")  # local-only work
    proc, rep = run_probe(repo)
    expect("exit 0", proc.returncode == EXIT_NO_DRIFT, proc.stdout + proc.stderr)
    expect("verdict NO_DRIFT", rep and rep.get("verdict") == "NO_DRIFT", rep)
    expect("drift list empty", rep and rep.get("drift") == [], rep and rep.get("drift"))
    expect("local-ahead counted, not drift", rep and rep.get("local_ahead_count") == 1, rep)
    expect("RESULT_JSON is the last line", proc.stdout.strip().splitlines()[-1]
           .startswith("RESULT_JSON="))


def test_behind_base_classification_and_scope_globs():
    print("BEHIND_BASE across every scope glob")
    repo = make_repo()
    commit(repo, {"hooks/a.py": "A = 2\n",
                  "maintenance/tool.py": "X = 2\n",
                  "maintenance/_tests/test_tool.py": "TT = 2\n",
                  "settings.json": "{\"a\": 1}\n",
                  "CLAUDE.md": "doc v2\n",
                  "agents/x.md": "agent v2\n"},
           deletes=["hooks/gone.py"], msg="main moves")
    to_feature(repo)
    proc, rep = run_probe(repo)
    d = by_path(rep)
    expect("exit 1 on drift", proc.returncode == EXIT_DRIFT, proc.stdout + proc.stderr)
    for p in ("hooks/a.py", "maintenance/tool.py", "maintenance/_tests/test_tool.py",
              "settings.json", "CLAUDE.md", "agents/x.md"):
        expect("%s BEHIND_BASE" % p, d.get(p, {}).get("class") == "BEHIND_BASE", d.get(p))
    expect("deletion on base is BEHIND_BASE with deleted_on_base flag",
           d.get("hooks/gone.py", {}).get("class") == "BEHIND_BASE"
           and "DELETED_ON_BASE" in d.get("hooks/gone.py", {}).get("flags", []),
           d.get("hooks/gone.py"))
    expect("counts grouped by class", rep["counts"].get("BEHIND_BASE") == 7, rep["counts"])
    expect("human summary names the class", "BEHIND_BASE" in proc.stdout)


def test_diverged():
    print("DIVERGED")
    repo = make_repo()
    commit(repo, {"hooks/b.py": "B = 'main'\n"}, msg="main")
    to_feature(repo)
    commit(repo, {"hooks/b.py": "B = 'feature'\n"}, msg="feature")
    proc, rep = run_probe(repo)
    d = by_path(rep)
    expect("hooks/b.py DIVERGED", d.get("hooks/b.py", {}).get("class") == "DIVERGED", d)
    expect("exit 1", proc.returncode == EXIT_DRIFT)


def test_base_only_and_untracked_stale_with_history_match():
    print("BASE_ONLY + UNTRACKED_STALE (historical blob match)")
    repo = make_repo()
    commit(repo, {"scheduled-tasks/auditor/SKILL.md": "skill v1\n"}, msg="add v1")
    commit(repo, {"scheduled-tasks/auditor/SKILL.md": "skill v2 guarded\n"}, msg="v2")
    commit(repo, {"scheduled-tasks/other/SKILL.md": "other v1\n",
                  "hooks/lib/newmod.py": "N = 1\n"}, msg="more")
    to_feature(repo)
    # stale untracked copy == an old main version; another untracked copy == nothing known
    write(repo, "scheduled-tasks/auditor/SKILL.md", "skill v1\n")
    write(repo, "scheduled-tasks/other/SKILL.md", "hand-made local copy\n")
    proc, rep = run_probe(repo)
    d = by_path(rep)
    a = d.get("scheduled-tasks/auditor/SKILL.md", {})
    o = d.get("scheduled-tasks/other/SKILL.md", {})
    n = d.get("hooks/lib/newmod.py", {})
    expect("auditor SKILL.md BASE_ONLY", a.get("class") == "BASE_ONLY", a)
    expect("auditor UNTRACKED_STALE", "UNTRACKED_STALE" in a.get("flags", []), a)
    expect("auditor untracked blob matches a historical blob",
           a.get("untracked", {}).get("matches_historical_blob") is True, a)
    expect("auditor untracked blob does not match base",
           a.get("untracked", {}).get("matches_base") is False, a)
    expect("other SKILL.md UNTRACKED_STALE, no historical match",
           "UNTRACKED_STALE" in o.get("flags", [])
           and o.get("untracked", {}).get("matches_historical_blob") is False, o)
    expect("module absent locally is BASE_ONLY without UNTRACKED_STALE",
           n.get("class") == "BASE_ONLY" and "UNTRACKED_STALE" not in n.get("flags", []), n)


def test_local_dirty_over_behind():
    print("LOCAL_DIRTY_OVER_BEHIND")
    repo = make_repo()
    commit(repo, {"hooks/c.py": "C = 2\n", "hooks/a.py": "A = 2\n"}, msg="main")
    to_feature(repo)
    write(repo, "hooks/c.py", "C = 'someone elses wip'\n")
    write(repo, "hooks/a.py", "A = 2\n")   # hand-synced to base in the working tree only
    proc, rep = run_probe(repo)
    d = by_path(rep)
    c = d.get("hooks/c.py", {})
    a = d.get("hooks/a.py", {})
    expect("hooks/c.py LOCAL_DIRTY_OVER_BEHIND", c.get("class") == "LOCAL_DIRTY_OVER_BEHIND", c)
    expect("dirty wip does not match base", c.get("worktree_matches_base") is False, c)
    expect("hand-synced dirty file flagged worktree_matches_base",
           a.get("class") == "LOCAL_DIRTY_OVER_BEHIND"
           and a.get("worktree_matches_base") is True, a)
    expect("wip file untouched by the probe",
           open(os.path.join(repo, "hooks/c.py"), encoding="utf-8").read()
           == "C = 'someone elses wip'\n")


def test_dependency_hint_sync_requires():
    print("dependency hint: sync requires BASE_ONLY sibling modules")
    repo = make_repo()
    commit(repo, {
        "hooks/lib/probe_common.py": "def git():\n    return 0\n",
        "maintenance/_shared/shared_util.py": "S = 1\n",
        "hooks/lib/parse.py": ("import os\n"
                               "import present\n"
                               "from probe_common import git\n"
                               "try:\n    import shared_util\nexcept ImportError:\n"
                               "    shared_util = None\n"
                               "def parse():\n    return git()\n"),
    }, msg="main refactor")
    to_feature(repo)
    proc, rep = run_probe(repo)
    d = by_path(rep)
    p = d.get("hooks/lib/parse.py", {})
    req = p.get("sync_requires", [])
    expect("parse.py BEHIND_BASE", p.get("class") == "BEHIND_BASE", p)
    expect("sync_requires names hooks/lib/probe_common.py",
           "hooks/lib/probe_common.py" in req, p)
    expect("sync_requires names maintenance/_shared/shared_util.py (guarded import)",
           "maintenance/_shared/shared_util.py" in req, p)
    expect("stdlib and already-present siblings not required",
           not any("os" == os.path.splitext(os.path.basename(r))[0] or "present" in r
                   for r in req), req)
    expect("human output says 'sync requires'", "sync requires" in proc.stdout, proc.stdout)


def test_dependency_hint_ignores_unparseable_base_source():
    print("dependency hint: unparseable base source is noted, never crashes")
    repo = make_repo()
    commit(repo, {"hooks/a.py": "def broken(:\n"}, msg="main syntax error")
    to_feature(repo)
    proc, rep = run_probe(repo)
    a = by_path(rep).get("hooks/a.py", {})
    expect("exit 1 (drift), not 2", proc.returncode == EXIT_DRIFT, proc.stdout + proc.stderr)
    expect("sync_requires empty, parse error noted",
           a.get("sync_requires") == [] and a.get("import_parse_error"), a)


def test_coupling_module_behind_test_synced():
    print("test-coupling: module behind, its test already synced")
    repo = make_repo()
    commit(repo, {"hooks/lib/parse.py": "def parse():\n    return 2\n",
                  "hooks/tests/test-parse.py": "T = 2\n",
                  "hooks/tests/test-gate.py": ("def t():\n    from parse import parse\n"
                                               "    return parse()\n")},
           msg="main: module + tests")
    to_feature(repo)
    # the tests were synced onto the branch; the module was not
    g(repo, "checkout", "main", "--", "hooks/tests/test-parse.py", "hooks/tests/test-gate.py")
    g(repo, "commit", "-q", "-m", "sync tests only")
    proc, rep = run_probe(repo)
    d = by_path(rep)
    m = d.get("hooks/lib/parse.py", {})
    coup = m.get("coupling", [])
    paths = {c.get("counterpart"): c for c in coup}
    expect("module BEHIND_BASE", m.get("class") == "BEHIND_BASE", m)
    expect("name-derived test counterpart reported as SYNCED",
           paths.get("hooks/tests/test-parse.py", {}).get("state") == "SYNCED", coup)
    expect("importing test (function-level import) reported as SYNCED",
           paths.get("hooks/tests/test-gate.py", {}).get("state") == "SYNCED", coup)
    expect("synced tests themselves are not drift",
           "hooks/tests/test-parse.py" not in d and "hooks/tests/test-gate.py" not in d, d.keys())
    expect("human output mentions coupling", "test synced but module" in proc.stdout,
           proc.stdout)


def test_coupling_test_behind_module_synced():
    print("test-coupling: test behind, module synced (maintenance naming)")
    repo = make_repo()
    commit(repo, {"maintenance/tool.py": "X = 2\n",
                  "maintenance/_tests/test_tool.py": "TT = 2\n"}, msg="main")
    to_feature(repo)
    g(repo, "checkout", "main", "--", "maintenance/tool.py")
    g(repo, "commit", "-q", "-m", "sync module only")
    proc, rep = run_probe(repo)
    t = by_path(rep).get("maintenance/_tests/test_tool.py", {})
    coup = {c.get("counterpart"): c for c in t.get("coupling", [])}
    expect("test BEHIND_BASE", t.get("class") == "BEHIND_BASE", t)
    expect("module counterpart SYNCED", coup.get("maintenance/tool.py", {}).get("state")
           == "SYNCED", t)


def test_no_fetch_skips_fetch():
    print("--no-fetch skips fetch")
    repo = make_repo()
    to_feature(repo)
    proc, rep = run_probe(repo)
    expect("fetch not attempted", rep and rep["fetch"]["attempted"] is False, rep and rep["fetch"])


def test_fetch_default_updates_base_and_offline_fails_open():
    print("fetch: default fetch picks up origin; offline fails open")
    td = tempfile.mkdtemp(prefix="drift-probe-origin-")
    origin = os.path.join(td, "origin.git")
    subprocess.run(["git", "init", "-q", "--bare", origin], capture_output=True)
    repo = make_repo()
    g(repo, "remote", "add", "origin", origin)
    g(repo, "push", "-q", "origin", "main")
    g(repo, "fetch", "-q", "origin")
    to_feature(repo)
    # another clone lands a fix on origin/main that the live repo has not fetched
    other = os.path.join(td, "other")
    subprocess.run(["git", "clone", "-q", origin, other], capture_output=True)
    g(other, "config", "user.email", "t@t.t")
    g(other, "config", "user.name", "t")
    g(other, "checkout", "-q", "main")
    commit(other, {"hooks/a.py": "A = 'remote fix'\n"}, msg="remote fix")
    g(other, "push", "-q", "origin", "main")

    proc, rep = run_probe(repo, base="origin/main", fetch=True)
    expect("fetch attempted and ok", rep and rep["fetch"]["attempted"] and rep["fetch"]["ok"],
           rep and rep["fetch"])
    expect("fetched fix surfaces as BEHIND_BASE",
           by_path(rep).get("hooks/a.py", {}).get("class") == "BEHIND_BASE", rep)

    proc2, rep2 = run_probe(repo, base="origin/main", fetch=False)
    expect("--no-fetch after fetch still sees fetched ref", proc2.returncode == EXIT_DRIFT)

    g(repo, "remote", "set-url", "origin", os.path.join(td, "does-not-exist.git"))
    proc3, rep3 = run_probe(repo, base="origin/main", fetch=True)
    expect("offline fetch fails open: probe still exits 1 on drift",
           proc3.returncode == EXIT_DRIFT, proc3.stdout + proc3.stderr)
    expect("offline fetch reported ok=false", rep3 and rep3["fetch"]["ok"] is False,
           rep3 and rep3["fetch"])
    expect("offline fetch prints a WARNING", "WARNING" in proc3.stdout, proc3.stdout)
    expect("offline fetch adds a warnings entry", rep3 and rep3.get("warnings"), rep3)


def test_errors_exit_2():
    print("probe errors exit 2 with RESULT_JSON")
    td = tempfile.mkdtemp(prefix="drift-probe-notrepo-")
    proc, rep = run_probe(td)
    expect("not a repo -> exit 2", proc.returncode == EXIT_ERROR, proc.stdout + proc.stderr)
    expect("not a repo -> verdict ERROR", rep and rep.get("verdict") == "ERROR", rep)
    repo = make_repo()
    proc, rep = run_probe(repo, base="nope/nothing")
    expect("unresolvable base -> exit 2", proc.returncode == EXIT_ERROR, proc.stdout)
    expect("unresolvable base -> RESULT_JSON present", rep and rep.get("verdict") == "ERROR")


def test_json_mode_is_pure_json():
    print("--json prints only JSON")
    repo = make_repo()
    commit(repo, {"hooks/a.py": "A = 2\n"}, msg="main")
    to_feature(repo)
    proc, rep = run_probe(repo, "--json")
    expect("--json parses", rep is not None, proc.stdout[:300])
    expect("--json exit code preserved", proc.returncode == EXIT_DRIFT)
    expect("scope globs exposed", rep and "hooks/**" in rep.get("scope_globs", []), rep)


def _snapshot(repo):
    with open(os.path.join(repo, ".git", "index"), "rb") as fh:
        idx = hashlib.sha256(fh.read()).hexdigest()
    return (g(repo, "rev-parse", "HEAD"), g(repo, "rev-parse", "--abbrev-ref", "HEAD"),
            g(repo, "status", "--porcelain", "--untracked-files=all"), idx,
            sorted(g(repo, "for-each-ref", "--format=%(refname) %(objectname)").splitlines()))


def test_read_only():
    print("read-only: HEAD, branch, index, status, refs unchanged")
    repo = make_repo()
    commit(repo, {"hooks/a.py": "A = 2\n", "hooks/lib/newmod.py": "N = 1\n"}, msg="main")
    to_feature(repo)
    write(repo, "hooks/lib/newmod.py", "stale\n")
    write(repo, "hooks/b.py", "B = 'wip'\n")
    before = _snapshot(repo)
    run_probe(repo)
    run_probe(repo, "--json")
    expect("repository state unchanged", _snapshot(repo) == before)


def test_scope_matcher_unit():
    print("scope matcher unit")
    spec = importlib.util.spec_from_file_location("drift_probe", PROBE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    m = mod.in_scope
    expect("hooks/** deep", m("hooks/lib/x/y.py"))
    expect("maintenance/*.py direct", m("maintenance/tool.py"))
    expect("maintenance/*.py not nested", not m("maintenance/sub/deep.py"))
    expect("maintenance/_tests/** nested", m("maintenance/_tests/a/b.py"))
    expect("scheduled-tasks/*/SKILL.md", m("scheduled-tasks/foo/SKILL.md"))
    expect("scheduled-tasks other file excluded", not m("scheduled-tasks/foo/notes.md"))
    expect("settings.json root only", m("settings.json") and not m("x/settings.json"))
    expect("CLAUDE.md root only", m("CLAUDE.md") and not m("docs/CLAUDE.md"))
    expect("agents/**", m("agents/a.md"))
    expect("hooks-archive not hooks/**", not m("hooks-archive/a.py"))


def main():
    test_scope_matcher_unit()
    test_no_drift_when_identical_or_out_of_scope_or_local_ahead()
    test_behind_base_classification_and_scope_globs()
    test_diverged()
    test_base_only_and_untracked_stale_with_history_match()
    test_local_dirty_over_behind()
    test_dependency_hint_sync_requires()
    test_dependency_hint_ignores_unparseable_base_source()
    test_coupling_module_behind_test_synced()
    test_coupling_test_behind_module_synced()
    test_no_fetch_skips_fetch()
    test_fetch_default_updates_base_and_offline_fails_open()
    test_errors_exit_2()
    test_json_mode_is_pure_json()
    test_read_only()
    passed = sum(1 for ok, _ in results if ok)
    print("\nlive-branch-drift-probe tests: %d/%d passed" % (passed, len(results)))
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
