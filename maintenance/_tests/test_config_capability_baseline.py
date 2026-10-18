#!/usr/bin/env python3
"""Tests for config-capability-baseline.py. Run: python _tests/test_config_capability_baseline.py"""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(os.path.dirname(HERE), "config-capability-baseline.py")
spec = importlib.util.spec_from_file_location("ccb", SCRIPT)
ccb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ccb)
_ok = []


def check(name, cond, detail=""):
    _ok.append(bool(cond))
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else "  " + detail))


check("parse_version", ccb.parse_version("2.1.295") == (2, 1, 295) and ccb.parse_version("claude 2.1.278 (x)") == (2, 1, 278))
check("parse_version junk", ccb.parse_version("nope") is None)
check("lowest_binary", ccb.lowest_binary(["2.1.295", "2.1.278", "2.1.293"]) == "2.1.278")
check("lowest_binary empty", ccb.lowest_binary([]) is None)
check("extract_refs", ccb.extract_refs('"mcp__census__x" mcp__notion__* mcp__a1b2c3d4-0000-4000-8000-000000000000__tool')
      == {"census", "notion", "a1b2c3d4-0000-4000-8000-000000000000"})
check("extract_refs real-world ids (single underscores, hyphens, bare server)",
      ccb.extract_refs("mcp__Desktop_Commander__read_file mcp__claude_ai_Notion__fetch mcp__scheduled-tasks__list "
                       "mcp__plugin_desktop-commander_desktop-commander__edit_block mcp__excel__ mcp__claude-in-chrome__*")
      == {"Desktop_Commander", "claude_ai_Notion", "scheduled-tasks",
          "plugin_desktop-commander_desktop-commander", "excel", "claude-in-chrome"})

with tempfile.TemporaryDirectory() as root:
    os.makedirs(os.path.join(root, "agents"))
    os.makedirs(os.path.join(root, "hooks"))
    os.makedirs(os.path.join(root, "_confidential-staging"))
    with open(os.path.join(root, "settings.json"), "w", encoding="utf-8") as fh:
        json.dump({"permissions": {"allow": ["mcp__notion__*", "mcp__context7__query-docs"]}}, fh)
    with open(os.path.join(root, "agents", "deal-recon.md"), "w", encoding="utf-8") as fh:
        fh.write("---\nname: deal-recon\ntools: Read, mcp__census__census_market_profile\n---\n")
    with open(os.path.join(root, "hooks", "g.py"), "w", encoding="utf-8") as fh:
        fh.write('MATCH = "mcp__notion__.*"\n')
    with open(os.path.join(root, "hooks", "confidential-terms.json"), "w", encoding="utf-8") as fh:
        fh.write('{"x": "mcp__SHOULD_NOT_BE_READ__a"}')
    with open(os.path.join(root, "_confidential-staging", "s.py"), "w", encoding="utf-8") as fh:
        fh.write('X = "mcp__SHOULD_NOT_BE_READ__b"')
    live = os.path.join(root, "live.txt")
    with open(live, "w", encoding="utf-8") as fh:
        fh.write("notion\ncontext7\n")

    refs = ccb.collect_refs(root)
    check("collect settings", refs["settings"] == {"notion", "context7"}, repr(refs))
    check("collect agents", refs["agents"] == {"census"}, repr(refs))
    check("collect hooks", refs["hooks"] == {"notion"}, repr(refs))
    check("confidential files never read", all("SHOULD_NOT" not in r for s in refs.values() for r in s))
    dead = ccb.dead_refs(refs, {"notion", "context7"})
    check("dead ref census in agents", [(d["ref"], d["where"]) for d in dead] == [("census", "agents")], repr(dead))

    p = subprocess.run([sys.executable, SCRIPT, "--root", root, "--live-servers", live,
                        "--version-override", "2.1.278,2.1.295", "--json"], capture_output=True, text=True)
    check("cli exits 0 by default", p.returncode == 0, p.stderr)
    d = json.loads(p.stdout)
    check("cli lowest_binary", d["lowest_binary"] == "2.1.278", repr(d))
    check("cli dead_refs", [r["ref"] for r in d["dead_refs"]] == ["census"], repr(d))
    check("cli onFailure:block not usable under 2.1.278",
          [c for c in d["capabilities"] if c["name"] == "onFailure:block"][0]["usable_on_lowest"] is False)
    p2 = subprocess.run([sys.executable, SCRIPT, "--root", root, "--live-servers", live,
                         "--version-override", "2.1.295", "--strict"], capture_output=True, text=True)
    check("strict exits 3 with a dead ref", p2.returncode == 3, str(p2.returncode))
    check("probe wrote nothing", sorted(os.listdir(root)) == sorted(["agents", "hooks", "_confidential-staging", "settings.json", "live.txt"]))

print("\ncapability-baseline tests: %d/%d passed" % (sum(_ok), len(_ok)))
sys.exit(0 if all(_ok) else 1)
