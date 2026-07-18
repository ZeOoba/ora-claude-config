"""Write-guard coverage meta-test (2026-07-18, write-guard architecture hardening).

THE POINT: memory-index-guard.py and registry-write-guard.py EACH shipped with the
same Desktop Commander blind spot (2026-07-14) because nothing forced a guard to
enumerate every write-capable tool-call shape. This meta-test closes that class of
gap structurally: it iterates tool_call_paths.SHAPES (the single source of shape
truth) x every write-guard hook, builds a payload that writes to each guard's OWN
protected path through each contracted shape, and asserts the guard actually fires.
Add a new write-capable shape to tool_call_paths.SHAPES and every guard is
re-audited automatically; ship a guard that forgets a shape and this test goes red
(falsification-proven during the 2026-07-18 build: commenting out the DC handling in
registry-write-guard.py flipped 4 cases to FAIL).

It ALSO cross-checks settings.json: a guard that handles a shape in code but whose
PreToolUse matcher never routes that tool name to it is exactly as bypassed as one
with no code at all.

Run: python test-write-guard-coverage.py
Stdlib only. ASCII-only. Windows (`python`).
"""
import json
import os
import re
import subprocess
import sys
import tempfile

HOOKS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLAUDE_ROOT = os.path.dirname(HOOKS_DIR)
sys.path.insert(0, os.path.join(HOOKS_DIR, "lib"))

import tool_call_paths as tcp  # noqa: E402

_failures = []


def check(name, cond, detail=""):
    if cond:
        print("PASS " + name)
    else:
        print("FAIL " + name + ("  " + detail if detail else ""))
        _failures.append(name)


def run_hook(hook, payload, env_extra):
    env = dict(os.environ)
    env.update(env_extra)
    proc = subprocess.run(
        [sys.executable, os.path.join(HOOKS_DIR, hook)],
        input=json.dumps(payload).encode("utf-8"),
        capture_output=True, env=env)
    return proc.returncode, proc.stdout.decode("utf-8", "replace"), \
        proc.stderr.decode("utf-8", "replace")


def blocked_exit2(rc, out, err):
    return rc == 2


def blocked_deny_json(rc, out, err):
    try:
        return json.loads(out).get("hookSpecificOutput", {}) \
            .get("permissionDecision") == "deny"
    except ValueError:
        return False


# --------------------------------------------------------------- guard contracts
# Each guard declares WHICH shapes it is contracted to cover. The two legacy guards
# are contracted to the shapes their settings.json matcher routes (file-tool shapes
# only -- widening them is out of scope for the behavior-preserving refactor); the
# new hard gate is contracted to EVERY shape in the registry.
LEGACY_TOOLS = frozenset(("Write", "Edit", "MultiEdit")) \
    | tcp.DC_WRITE_FILE_NAMES | tcp.DC_EDIT_BLOCK_NAMES

SHORT = "- [A](a.md) - short hook\n"
LONG = "- [B](b.md) - " + ("x" * 200) + "\n"

CC_REG = ("C:/Users/Owner/AppData/Roaming/Claude/claude-code-sessions/"
          "aaaa-1111/bbbb-2222/scheduled-tasks.json")


class GuardSpec(object):
    def __init__(self, hook, shape_filter, make_case, blocked, matcher_key):
        self.hook = hook
        self.shape_filter = shape_filter    # shape -> bool (contracted?)
        self.make_case = make_case          # shape -> (payload, env) or None
        self.blocked = blocked
        self.matcher_key = matcher_key      # substring identifying its settings entry


def registry_case(shape):
    payload = {"session_id": "meta-s1", "tool_name": shape.tool_name,
               "tool_input": shape.build(CC_REG)}
    return payload, {}


def memory_case(shape):
    d = tempfile.mkdtemp(prefix="wgc-mem-")
    idx = os.path.join(d, "MEMORY.md")
    with open(idx, "w", encoding="utf-8") as fh:
        fh.write(SHORT)
    tool_input = shape.build(idx, content=SHORT + LONG, old=SHORT, new=LONG)
    payload = {"session_id": "meta-s1", "tool_name": shape.tool_name,
               "tool_input": tool_input}
    return payload, {"ORA_MEMORY_INDEX": idx}


_CONFIG_ROOT = tempfile.mkdtemp(prefix="wgc-cfg-root-")
_CONFIG_SESS = tempfile.mkdtemp(prefix="wgc-cfg-sess-")
_CONFIG_LOG = os.path.join(tempfile.mkdtemp(prefix="wgc-cfg-log-"),
                           "chip-claims.log")


def config_case(shape):
    target = os.path.join(_CONFIG_ROOT, "hooks", "meta-target.py") \
        .replace("\\", "/")
    payload = {"session_id": "meta-s1", "tool_name": shape.tool_name,
               "tool_input": shape.build(target)}
    return payload, {"ORA_CONFIG_GUARD_ROOT": _CONFIG_ROOT,
                     "ORA_OVERRIDE_SESSIONS_DIR": _CONFIG_SESS,
                     "ORA_CHIP_CLAIMS_LOG": _CONFIG_LOG}


GUARDS = [
    GuardSpec("registry-write-guard.py",
              lambda s: s.kind == "file" and s.tool_name in LEGACY_TOOLS,
              registry_case, blocked_exit2, "registry-write-guard.py"),
    GuardSpec("memory-index-guard.py",
              lambda s: s.kind == "file" and s.tool_name in LEGACY_TOOLS,
              memory_case, blocked_deny_json, "memory-index-guard.py"),
    GuardSpec("config-write-guard.py",
              lambda s: True,
              config_case, blocked_exit2, "config-write-guard.py"),
]


def test_guard_shape_matrix():
    for spec in GUARDS:
        contracted = [s for s in tcp.SHAPES if spec.shape_filter(s)]
        check("%s: contracted to at least 6 shapes" % spec.hook,
              len(contracted) >= 6, "got %d" % len(contracted))
        for shape in contracted:
            payload, env = spec.make_case(shape)
            rc, out, err = run_hook(spec.hook, payload, env)
            check("%s fires for shape %s" % (spec.hook, shape.name),
                  spec.blocked(rc, out, err),
                  "rc=%s out=%r err=%r" % (rc, out[:120], err[:200]))


def test_new_hard_gate_is_contracted_to_every_shape():
    spec = GUARDS[2]
    uncovered = [s.name for s in tcp.SHAPES if not spec.shape_filter(s)]
    check("config-write-guard is contracted to EVERY registry shape",
          uncovered == [], "uncovered: %s" % uncovered)


def test_settings_matchers_route_every_contracted_shape():
    settings_path = os.path.join(CLAUDE_ROOT, "settings.json")
    with open(settings_path, "r", encoding="utf-8-sig") as fh:
        settings = json.load(fh)
    entries = settings.get("hooks", {}).get("PreToolUse", [])
    for spec in GUARDS:
        matchers = [e.get("matcher", "") for e in entries
                    if any(spec.matcher_key in (h.get("command") or "")
                           for h in e.get("hooks", []))]
        check("%s is registered in settings.json PreToolUse" % spec.hook,
              len(matchers) >= 1)
        for shape in tcp.SHAPES:
            if not spec.shape_filter(shape):
                continue
            routed = any(re.fullmatch(m, shape.tool_name) for m in matchers if m)
            check("settings.json routes %s to %s" % (shape.tool_name, spec.hook),
                  routed, "matchers=%r" % matchers)


if __name__ == "__main__":
    test_guard_shape_matrix()
    test_new_hard_gate_is_contracted_to_every_shape()
    test_settings_matchers_route_every_contracted_shape()
    if _failures:
        print("\n%d FAILURE(S): %s" % (len(_failures), ", ".join(sorted(set(_failures))[:12])))
        sys.exit(1)
    print("\nALL write-guard coverage meta-tests passed.")
    sys.exit(0)
