#!/usr/bin/env python3
"""Tests for doctrine-integrity-probe.py's agent-definition validation.

Written against real fixture directories rather than mocks, because the defect
being fixed is that the probe only ever looked at FILENAMES -- a mock that hands
back parsed frontmatter would assume away the entire bug.

Origin: PR #179 (2026-09-10) shipped two agent definitions whose frontmatter
failed strict yaml.safe_load, which silently unregisters the agent. An adversarial
merge-gate pass mutated five agent definitions to be obviously broken and the
pre-push doctrine gate exited 0 on all five, while correctly exiting 1 when a
referenced agent file was DELETED -- i.e. the gate checked presence and nothing
else. These tests pin each of those five mutation classes.
"""
import importlib.util
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(os.path.dirname(HERE), "doctrine-integrity-probe.py")

_spec = importlib.util.spec_from_file_location("dip", SCRIPT)
dip = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dip)

_results = []


def check(name, cond, detail=""):
    _results.append((bool(cond), name))
    print(("PASS %s" % name) if cond else ("FAIL %s  %s" % (name, detail)))


GOOD = """---
name: %s
description: 'Use when something specific happens: and a colon appears.'
tools: Read, Grep, Glob
model: opus
---

Body text for %s.
"""


def make_agents(tmp, files):
    """files: {filename: full file text}. Returns the agents dir path."""
    d = os.path.join(tmp, "agents")
    os.makedirs(d, exist_ok=True)
    for fn, text in files.items():
        with open(os.path.join(d, fn), "w", encoding="utf-8") as fh:
            fh.write(text)
    return d


def hard(agents_dir):
    """Hard (blocking) failure strings only."""
    failures, _warnings = dip.check_agent_definitions(agents_dir)
    return failures


def warns(agents_dir):
    _failures, warnings = dip.check_agent_definitions(agents_dir)
    return warnings


def main():
    check("check_agent_definitions is exported",
          hasattr(dip, "check_agent_definitions"),
          "probe has no agent-definition validator at all")
    if not hasattr(dip, "check_agent_definitions"):
        print("\nagent-frontmatter tests: 0/1 passed (validator absent)")
        return 1

    tmp = tempfile.mkdtemp(prefix="agentfm-")
    try:
        # --- clean baseline: must not produce false positives ---
        d = make_agents(tmp + "/clean", {
            "alpha-agent.md": GOOD % ("alpha-agent", "alpha"),
            "beta-agent.md": GOOD % ("beta-agent", "beta"),
        })
        check("clean tree yields no hard failures", hard(d) == [], repr(hard(d)))
        check("clean tree yields no warnings", warns(d) == [], repr(warns(d)))

        # --- M1: broken YAML (the exact PR #179 defect: ': ' in a plain scalar) ---
        d = make_agents(tmp + "/m1", {
            "alpha-agent.md": "---\nname: alpha-agent\n"
                              "description: Trigger when the user says: do a thing\n"
                              "tools: Read\n---\n\nBody.\n",
        })
        f = hard(d)
        check("M1 broken YAML is a hard failure", len(f) == 1, repr(f))
        check("M1 names the offending file",
              f and "alpha-agent.md" in f[0], repr(f))

        # --- M2: name != filename stem ---
        d = make_agents(tmp + "/m2", {
            "alpha-agent.md": GOOD % ("alpha-agentX", "alpha"),
        })
        f = hard(d)
        check("M2 name/stem mismatch is a hard failure", len(f) == 1, repr(f))

        # --- M3: unresolvable tool name -> WARN, not a push blocker ---
        d = make_agents(tmp + "/m3", {
            "alpha-agent.md": "---\nname: alpha-agent\ndescription: 'x'\n"
                              "tools: Read, TotallyFakeTool\n---\n\nBody.\n",
        })
        check("M3 unknown tool does NOT hard-fail (stale allowlist must not "
              "block a legitimate push)", hard(d) == [], repr(hard(d)))
        w = warns(d)
        check("M3 unknown tool warns", len(w) == 1 and "TotallyFakeTool" in w[0], repr(w))

        # --- M3b: mcp__-prefixed tools are legitimate and must not warn ---
        d = make_agents(tmp + "/m3b", {
            "alpha-agent.md": "---\nname: alpha-agent\ndescription: 'x'\n"
                              "tools: Read, mcp__excel__read_data_from_excel\n---\n\nBody.\n",
        })
        check("M3b mcp__ tools do not warn", warns(d) == [], repr(warns(d)))

        # --- M4: duplicate name across two files ---
        d = make_agents(tmp + "/m4", {
            "alpha-agent.md": GOOD % ("alpha-agent", "alpha"),
            "beta-agent.md": GOOD % ("alpha-agent", "beta"),
        })
        f = hard(d)
        check("M4 duplicate name is a hard failure", len(f) >= 1, repr(f))
        check("M4 failure mentions the duplicated name",
              any("alpha-agent" in x for x in f), repr(f))

        # --- M5: frontmatter block absent entirely ---
        d = make_agents(tmp + "/m5", {
            "alpha-agent.md": "No frontmatter here at all.\n",
        })
        f = hard(d)
        check("M5 missing frontmatter is a hard failure", len(f) == 1, repr(f))

        # --- all five together: every one is reported, not just the first ---
        d = make_agents(tmp + "/all", {
            "a-one.md": "---\nname: a-one\ndescription: bad: scalar\n---\n\nB.\n",
            "a-two.md": GOOD % ("a-twoX", "two"),
            "a-three.md": GOOD % ("a-three", "three"),
            "a-four.md": GOOD % ("a-three", "four"),
            "a-five.md": "no frontmatter\n",
        })
        f = hard(d)
        check("all five mutation classes reported together", len(f) >= 4, repr(f))

        # --- fail-open: absent directory is not a failure ---
        check("absent agents dir yields no failures",
              hard(os.path.join(tmp, "does-not-exist")) == [], "should fail open")

        # --- non-.md files are ignored ---
        d = make_agents(tmp + "/skip", {
            "alpha-agent.md": GOOD % ("alpha-agent", "alpha"),
            "README.txt": "not an agent",
        })
        check("non-.md files ignored", hard(d) == [], repr(hard(d)))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    passed = sum(1 for ok, _ in _results if ok)
    print("\nagent-frontmatter tests: %d/%d passed" % (passed, len(_results)))
    return 0 if passed == len(_results) else 1


if __name__ == "__main__":
    sys.exit(main())
