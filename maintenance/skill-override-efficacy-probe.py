#!/usr/bin/env python3
"""skill-override-efficacy-probe.py -- assert every skillOverrides entry actually does something.

ROOT CAUSE this probe exists for (found 2026-08-05, verified against the CLI bundle):

    function resolveSkillOverride(e){
      if ((e.type==="local-jsx"||e.type==="local") && BUILTIN_CMDS.has(e.name))
        return settings().skillOverrides?.[e.name]==="off" ? "off" : "on";
      if (e.type!=="prompt" || e.source==="plugin") return "on";   // <-- short-circuit
      let r = settings().skillOverrides;
      let n = r?.[e.name] ?? r?.[e.unqualifiedName] ?? "on";
      ...
    }

The override map is consulted only AFTER `e.source==="plugin"` returns early, so an
override on a PLUGIN-SOURCED skill is silently ignored: the skill stays fully listed
and model-invocable. The /skills UI resolver agrees --
`if (e.source==="plugin") return {value:"on", source:"plugin"}` -- which is why this
never showed up as a visible contradiction in the UI either.

A plugin skill's qualified name is always `<plugin>:<skill>`, so ANY override key
containing ':' targets a plugin skill BY CONSTRUCTION and is therefore inert. That
makes the primary verdict deterministic and disk-independent -- it does not depend on
enumerating server-managed plugin bundles, which are not resolvable from local disk.

Live reading at authorship (2026-08-05): 35 `off` keys, of which 17 were still present
in the session skill listing, 12 named uninstalled/disabled plugins, and 6 were dead
keys. Zero were doing any work.

To actually suppress a plugin skill, disable the PLUGIN (or its marketplace) --
`enabledPlugins` / `blockedMarketplaces` -- not the skill.

Read-only. Exit 1 when an inert key is found (SCREEN), 0 otherwise.
Run: python skill-override-efficacy-probe.py [--json]
"""
import glob
import io
import json
import os
import sys

# ~/.claude -- derived from this file's location (maintenance/ sibling of settings.json)
# rather than by string-replacing "maintenance" out of the path, which would corrupt any
# path containing that word twice.
CLAUDE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Values that express an intent to hide or restrict a skill. `on` is the default
# and asserts nothing, so an `on` entry can never be "inert" in a meaningful sense.
SUPPRESSING = ("off", "name-only", "user-invocable-only")


def classify_key(key, value, user_skills):
    """Return (verdict, reason) for one skillOverrides entry.

    verdict is one of:
      INERT-PLUGIN -- key is plugin-namespaced; the override is short-circuited.
      EFFECTIVE    -- key names a real user skill (~/.claude/skills/<name>/).
      UNVERIFIED   -- unqualified and not a user skill: a builtin (where only
                      `off` is honored) or a dead key. Disk cannot distinguish
                      the two, so this probe reports the unknown rather than
                      guessing -- a zero that could mean "couldn't look" is a
                      failure, not a pass.
    """
    if ":" in key:
        plugin = key.split(":", 1)[0]
        return ("INERT-PLUGIN",
                "plugin-namespaced (%s) -- skillOverrides is short-circuited for "
                "source==\"plugin\"; disable the plugin instead" % plugin)
    if key in user_skills:
        return ("EFFECTIVE", "resolves to user skill ~/.claude/skills/%s/" % key)
    return ("UNVERIFIED",
            "unqualified and not a user skill -- either a builtin (only `off` is "
            "honored there; `name-only`/`user-invocable-only` are not) or a dead key")


def summarize(overrides, user_skills):
    """Classify every suppressing override entry. Pure; no I/O."""
    findings = []
    counts = {"INERT-PLUGIN": 0, "EFFECTIVE": 0, "UNVERIFIED": 0}
    for key, value in sorted(overrides.items()):
        if value not in SUPPRESSING:
            continue
        verdict, reason = classify_key(key, value, user_skills)
        counts[verdict] += 1
        findings.append({"key": key, "value": value,
                         "verdict": verdict, "reason": reason})
    if counts["INERT-PLUGIN"]:
        status = "CRIT"
        detail = ("%d skillOverrides entr%s silently ignored -- the skill(s) stay "
                  "fully listed and model-invocable. Plugin skills cannot be "
                  "suppressed via skillOverrides; disable the plugin instead."
                  % (counts["INERT-PLUGIN"],
                     "y is" if counts["INERT-PLUGIN"] == 1 else "ies are"))
    elif counts["UNVERIFIED"]:
        status = "WARN"
        detail = ("%d unqualified override(s) could not be resolved to a user skill "
                  "-- builtin or dead key; confirm against a live /skills listing."
                  % counts["UNVERIFIED"])
    else:
        status = "OK"
        detail = "%d suppressing override(s), all resolve to real user skills" % (
            counts["EFFECTIVE"])
    return {"status": status, "detail": detail,
            "counts": counts, "findings": findings}


def exit_code(summary):
    """CRIT gates; WARN is advisory and must not break the fail-open audit chain."""
    return 1 if summary["status"] == "CRIT" else 0


def load_overrides(settings_path=None):
    path = settings_path or os.path.join(CLAUDE, "settings.json")
    with io.open(path, encoding="utf-8") as fh:
        return json.load(fh).get("skillOverrides") or {}


def load_user_skills():
    return {os.path.basename(os.path.dirname(p))
            for p in glob.glob(os.path.join(CLAUDE, "skills", "*", "SKILL.md"))}


def main():
    try:
        summary = summarize(load_overrides(), load_user_skills())
    except Exception as e:                                  # fail-open, like siblings
        out = {"check": "skill-override-efficacy", "status": "SKIP",
               "detail": "error: %s" % e, "counts": {}, "findings": []}
        print(json.dumps(out, indent=2) if "--json" in sys.argv else out["detail"])
        return 0
    summary["check"] = "skill-override-efficacy"
    if "--json" in sys.argv:
        print(json.dumps(summary, indent=2))
    else:
        print("[%s] %s" % (summary["status"], summary["detail"]))
        for f in summary["findings"]:
            if f["verdict"] != "EFFECTIVE":
                print("  %-12s %-46s (%s) %s" % (
                    f["verdict"], f["key"], f["value"], f["reason"]))
    return exit_code(summary)


if __name__ == "__main__":
    sys.exit(main())
