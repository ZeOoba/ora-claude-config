#!/usr/bin/env python3
"""Tests for hooks/lib/rct_leak_check.py and its wiring into git-prepush-confidential-scan.py.

Run: python hooks/tests/test-rct-leak-check.py   (exit 0 = all pass)
Pure stdlib. ASCII-only output (Windows cp1252 console).

Every value here is SYNTHETIC (111.11, 222.22 ...). The real RCT figures live only in the
private file on Gabriel's machine and must never appear in this public repo, test fixtures
included. The tests point the module at temp files through its env overrides, so they run
the same on the dev box (where the real private file exists) and in CI (where it does not).
"""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
HOOKS = os.path.dirname(HERE)
LIB = os.path.join(HOOKS, "lib", "rct_leak_check.py")
SCAN = os.path.join(HOOKS, "git-prepush-confidential-scan.py")

spec = importlib.util.spec_from_file_location("rct_leak_check", LIB)
rlc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rlc)

results = []


def expect(label, cond, detail=""):
    results.append((bool(cond), label))
    if not cond:
        print("  FAIL: %s %s" % (label, detail))


TABLE = {
    "rctVersion": "synthetic-test",
    "psf": {"low": 211.11, "mid": 233.33, "high": 255.55},
    "markets": {
        "Alpha OH": {"low": 222.22, "point": 244.44, "high": 266.66, "cwHardPsf": 133.33, "proxy": False},
        "Beta KS": {"low": 200.00, "point": 230.00, "high": 260.00, "proxy": True},
    },
    "vintageFloor": {"oldYear": 1990, "oldPct": 0.70, "newYear": 2000, "newPct": 0.60},
    "_comment": "free text with 999.99 is not a value",
}

tmp = tempfile.mkdtemp(prefix="rct-leak-test-")
try:
    table_path = os.path.join(tmp, "replacement-cost.json")
    deny_path = os.path.join(tmp, "leak-denylist.json")
    missing = os.path.join(tmp, "nope.json")
    with open(table_path, "w", encoding="utf-8") as f:
        json.dump(TABLE, f)
    with open(deny_path, "w", encoding="utf-8") as f:
        json.dump({"values": [177.77], "strings": ["SYNTH-MARKER-XYZ"]}, f)

    # --- loading -------------------------------------------------------------------------
    needles, srcs = rlc.load_needles(table_path=missing, denylist_path=missing)
    expect("no private source on this machine -> None (skip cleanly)", needles is None)
    expect("skip reports no sources", srcs == [])

    needles, srcs = rlc.load_needles(table_path=table_path, denylist_path=missing)
    expect("table values become needles", "222.22" in needles and "266.66" in needles)
    expect("psf block values become needles", "233.33" in needles)
    expect("cwHardPsf becomes a needle", "133.33" in needles)
    expect("whole-dollar value keeps 2 decimals", "230.00" in needles)
    expect("trailing-zero short form also a needle", "230.0" in needles)
    expect("old-vintage floor derived (222.22 x 0.30)", "66.67" in needles, sorted(needles)[:20])
    expect("new-vintage floor derived (222.22 x 0.40)", "88.89" in needles)
    expect("mid-ramp floor derived (1995: 65%% -> 222.22 x 0.35)", "77.78" in needles)
    expect("underscore keys are not values", "999.99" not in needles)
    expect("booleans are not values", "1.00" not in needles and "0.00" not in needles)
    expect("ramp percentages themselves are not needles (too generic)", "0.70" not in needles)
    expect("sources listed", srcs == [table_path])

    needles, srcs = rlc.load_needles(table_path=table_path, denylist_path=deny_path)
    expect("denylist values join", "177.77" in needles)
    expect("denylist values get floors too", "53.33" in needles)
    expect("denylist strings join verbatim", "SYNTH-MARKER-XYZ" in needles)
    expect("both sources listed", srcs == [table_path, deny_path])

    needles, _ = rlc.load_needles(table_path=missing, denylist_path=deny_path)
    expect("denylist alone is enough to arm the check", needles and "177.77" in needles)

    # env overrides are what the pre-push hook uses
    os.environ["ORA_RCT_TABLE_PATH"] = table_path
    os.environ["ORA_RCT_LEAK_DENYLIST"] = missing
    needles, srcs = rlc.load_needles()
    expect("env override ORA_RCT_TABLE_PATH honoured", srcs == [table_path])

    # --- fail closed on a PRESENT but broken source --------------------------------------
    bad = os.path.join(tmp, "bad.json")
    with open(bad, "w", encoding="utf-8") as f:
        f.write("{not json")
    try:
        rlc.load_needles(table_path=bad, denylist_path=missing)
        expect("malformed table raises (fail closed)", False)
    except rlc.RctSourceError:
        expect("malformed table raises (fail closed)", True)
    empty = os.path.join(tmp, "empty.json")
    with open(empty, "w", encoding="utf-8") as f:
        json.dump({"markets": {}}, f)
    try:
        rlc.load_needles(table_path=empty, denylist_path=missing)
        expect("table with no values raises (an empty check proves nothing)", False)
    except rlc.RctSourceError:
        expect("table with no values raises (an empty check proves nothing)", True)
    os.mkdir(os.path.join(tmp, "dirpath"))
    try:
        rlc.load_needles(table_path=os.path.join(tmp, "dirpath"), denylist_path=missing)
        expect("unreadable (directory) table raises", False)
    except rlc.RctSourceError:
        expect("unreadable (directory) table raises", True)

    needles, _ = rlc.load_needles(table_path=table_path, denylist_path=deny_path)

    # --- text matching -------------------------------------------------------------------
    expect("dollar form matches", rlc.text_hits("LOW $222.22/SF", needles))
    expect("bare form matches", rlc.text_hits("low = 222.22", needles))
    expect("longer number does not match (1222.22)", not rlc.text_hits("1222.22", needles))
    expect("more decimals do not match (222.221)", not rlc.text_hits("222.221", needles))
    expect("version-like prefix does not match (3.222.22)", not rlc.text_hits("v3.222.22", needles))
    expect("unrelated number does not match", not rlc.text_hits("$123.45", needles))

    # --- diff scanning: only ADDED lines -------------------------------------------------
    diff = "\n".join([
        "commit 1111111111111111111111111111111111111111",
        "Author: t <t@example.com>",
        "",
        "    clean message",
        "",
        "diff --git a/old.md b/old.md",
        "index 1..2 100644",
        "--- a/old.md",
        "+++ b/old.md",
        "@@ -1,2 +1,2 @@",
        "-row Alpha $222.22",
        "+row Alpha (private file)",
        " context 244.44 unchanged",
        "diff --git a/new.md b/new.md",
        "new file mode 100644",
        "--- /dev/null",
        "+++ b/new.md",
        "@@ -0,0 +1 @@",
        "+leaked $266.66 here",
    ])
    hits = rlc.scan_diff(diff, needles)
    expect("added line with a figure is reported by path", hits == ["new.md"], hits)
    expect("removed line is NOT a leak (removal is the fix)", "old.md" not in hits)

    merge = "\n".join([
        "commit 2222222222222222222222222222222222222222",
        "Merge: a b",
        "",
        "    merge",
        "",
        "diff --cc merged.md",
        "index 1,2..3",
        "--- a/merged.md",
        "+++ b/merged.md",
        "@@@ -1,1 -1,1 +1,1 @@@",
        "- old 222.22",
        " -old 244.44",
        "++resolved $255.55",
    ])
    expect("combined-diff added line is reported", rlc.scan_diff(merge, needles) == ["merged.md"])
    merge_removed_only = merge.replace("++resolved $255.55", "++resolved clean")
    expect("combined-diff removed lines are not leaks",
           rlc.scan_diff(merge_removed_only, needles) == [])

    msg = "\n".join([
        "commit 3333333333333333333333333333333333333333",
        "Author: t <t@example.com>",
        "",
        "    fix: Alpha LOW is 222.22",
        "",
    ])
    hits = rlc.scan_diff(msg, needles)
    expect("figure in a commit message is reported", hits == ["<commit message 33333333>"], hits)

    header_trap = "\n".join([
        "commit 4444444444444444444444444444444444444444",
        "",
        "    ok",
        "",
        "diff --git a/x.md b/x.md",
        "--- a/x.md",
        "+++ b/x.md",
        "@@ -1 +1 @@",
        "-a",
        "+b",
    ])
    expect("+++ header line is not content", rlc.scan_diff(header_trap, needles) == [])

    # --- wiring: the real pre-push scan blocks on it --------------------------------------
    def sh(args, cwd, env=None):
        return subprocess.run(args, cwd=cwd, capture_output=True, text=True, env=env)

    origin = os.path.join(tmp, "origin.git")
    repo = os.path.join(tmp, "repo")
    sh(["git", "init", "-q", "--bare", origin], tmp)
    sh(["git", "init", "-q", "-b", "main", repo], tmp)
    for k, v in (("user.email", "t@example.com"), ("user.name", "t")):
        sh(["git", "config", k, v], repo)
    with open(os.path.join(repo, "a.md"), "w") as f:
        f.write("seed with $244.44\n")
    sh(["git", "add", "-A"], repo)
    sh(["git", "commit", "-qm", "seed"], repo)
    sh(["git", "remote", "add", "origin", origin], repo)
    sh(["git", "push", "-q", "--no-verify", "origin", "main"], repo)
    sh(["git", "fetch", "-q", "origin"], repo)
    base = sh(["git", "rev-parse", "HEAD"], repo).stdout.strip()

    # the scan reads confidential-terms.json next to itself; give it an empty roster
    hooks_copy = os.path.join(tmp, "hooks")
    shutil.copytree(HOOKS, hooks_copy, ignore=shutil.ignore_patterns("tests", "_state", "sessions",
                                                                      "active-work", "*.jsonl*"))
    with open(os.path.join(hooks_copy, "confidential-terms.json"), "w") as f:
        json.dump({}, f)
    scan_copy = os.path.join(hooks_copy, "git-prepush-confidential-scan.py")

    def push_scan(env_table, env_deny):
        head = sh(["git", "rev-parse", "HEAD"], repo).stdout.strip()
        env = dict(os.environ, ORA_RCT_TABLE_PATH=env_table, ORA_RCT_LEAK_DENYLIST=env_deny)
        return subprocess.run([sys.executable, scan_copy, "origin", origin], cwd=repo,
                              input="refs/heads/main %s refs/heads/main %s\n" % (head, base),
                              capture_output=True, text=True, env=env)

    # removal of a figure: allowed
    with open(os.path.join(repo, "a.md"), "w") as f:
        f.write("seed with a pointer\n")
    sh(["git", "commit", "-qam", "remove"], repo)
    r = push_scan(table_path, missing)
    expect("push that only REMOVES a figure passes", r.returncode == 0, r.stderr[:300])

    with open(os.path.join(repo, "b.md"), "w") as f:
        f.write("new $222.22\n")
    sh(["git", "add", "-A"], repo)
    sh(["git", "commit", "-qm", "add"], repo)
    r = push_scan(table_path, missing)
    expect("push that ADDS a figure is blocked", r.returncode == 1, r.stderr[:300])
    expect("block names the file", "b.md" in r.stderr, r.stderr[:300])
    expect("block never echoes the figure", "222.22" not in r.stderr, r.stderr[:300])

    r = push_scan(missing, missing)
    expect("no private source -> scan skips the RCT check and allows", r.returncode == 0,
           r.stderr[:300])
    expect("skip is announced, not silent", "RCT leak check skipped" in r.stderr, r.stderr[:300])

    r = push_scan(bad, missing)
    expect("present-but-broken private source blocks (fail closed)", r.returncode == 1,
           r.stderr[:300])
finally:
    shutil.rmtree(tmp, ignore_errors=True)

failed = [l for ok, l in results if not ok]
print("%d/%d passed" % (len(results) - len(failed), len(results)))
sys.exit(1 if failed else 0)
