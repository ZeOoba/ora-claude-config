#!/usr/bin/env python3
"""Tests for skill-override-efficacy-probe.py.

Each test is anchored to one of the failure classes found in the live
2026-08-05 audit, where 17 of 35 `off` keys were still in the session
skill listing. Pure-function tests only -- no settings.json or disk I/O.

Run: python test-skill-override-efficacy-probe.py   (exit 0 = all pass)
"""
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "soep", os.path.join(HERE, "skill-override-efficacy-probe.py"))
soep = importlib.util.module_from_spec(spec)
spec.loader.exec_module(soep)

results = []


def expect(label, cond, detail=""):
    results.append((bool(cond), label))
    if not cond:
        print("  FAIL: %s %s" % (label, detail))


# ---- classify_key: the core rule ----
# A plugin skill's qualified name is always `<plugin>:<skill>`, so any key with a
# colon targets a plugin skill by construction -> the override is short-circuited.
for key in ("fa0fa64bdc96:docx", "anthropic-skills:skill-creator",
            "ora-operations-extensions:annual-cycle",
            "cowork-plugin-management:create-cowork-plugin",
            "superpowers:systematic-debugging"):
    v, _ = soep.classify_key(key, "off", set())
    expect("qualified key %r -> INERT-PLUGIN" % key, v == "INERT-PLUGIN", v)

# The verdict is about the KEY's namespace, not the value: `user-invocable-only`
# on a plugin skill is short-circuited by the same branch.
v, _ = soep.classify_key("superpowers:test-driven-development",
                         "user-invocable-only", set())
expect("qualified + user-invocable-only -> INERT-PLUGIN", v == "INERT-PLUGIN", v)

# An unqualified key naming a real user skill (~/.claude/skills/<name>/) is honored:
# source is "user", not "plugin", so the short-circuit does not fire.
v, _ = soep.classify_key("my-local-skill", "off", {"my-local-skill"})
expect("unqualified + user skill exists -> EFFECTIVE", v == "EFFECTIVE", v)

# Unqualified and not a user skill: could be a builtin (where `off` works) or a
# dead key. Disk cannot tell them apart -- must NOT be reported as either.
# This is the verified-null-vs-inferred-null rule: no evidence != evidence of none.
v, r = soep.classify_key("keybindings-help", "user-invocable-only", set())
expect("unqualified + unknown -> UNVERIFIED", v == "UNVERIFIED", v)
expect("UNVERIFIED reason mentions builtin", "builtin" in r.lower(), r)

# ---- summarize ----
overrides = {
    "fa0fa64bdc96:docx": "off",                    # inert
    "anthropic-skills:skill-creator": "off",       # inert
    "superpowers:systematic-debugging": "user-invocable-only",  # inert
    "my-local-skill": "off",                       # effective
    "wrangler": "off",                             # unverified
    "always-on": "on",                             # ignored: not a suppression
}
s = soep.summarize(overrides, {"my-local-skill"})
expect("summarize counts inert", s["counts"]["INERT-PLUGIN"] == 3, s["counts"])
expect("summarize counts effective", s["counts"]["EFFECTIVE"] == 1, s["counts"])
expect("summarize counts unverified", s["counts"]["UNVERIFIED"] == 1, s["counts"])
expect("value 'on' is not a suppression -> excluded",
       "always-on" not in {i["key"] for i in s["findings"]}, s["findings"])
expect("summarize status CRIT when inert present", s["status"] == "CRIT", s["status"])

# Clean case: nothing inert -> OK, and the probe must not invent findings.
s_ok = soep.summarize({"my-local-skill": "off"}, {"my-local-skill"})
expect("no inert keys -> OK", s_ok["status"] == "OK", s_ok["status"])
expect("no inert keys -> zero inert findings",
       s_ok["counts"]["INERT-PLUGIN"] == 0, s_ok["counts"])

# Empty override map is OK, not a crash and not a false alarm.
s_empty = soep.summarize({}, set())
expect("empty overrides -> OK", s_empty["status"] == "OK", s_empty["status"])

# UNVERIFIED alone must not escalate to CRIT -- it is an unknown, not a defect.
s_unv = soep.summarize({"wrangler": "off"}, set())
expect("unverified-only -> WARN not CRIT", s_unv["status"] == "WARN", s_unv["status"])

# ---- exit code contract ----
expect("CRIT -> exit 1", soep.exit_code(s) == 1)
expect("OK -> exit 0", soep.exit_code(s_ok) == 0)
expect("WARN -> exit 0 (advisory, not a gate)", soep.exit_code(s_unv) == 0)

npass = sum(1 for ok, _ in results if ok)
print(f"skill-override-efficacy-probe tests: {npass}/{len(results)} pass")
sys.exit(0 if npass == len(results) else 1)
