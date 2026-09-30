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
import importlib.util
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

DISPATCHER = "pretooluse-dispatcher.py"

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


def _dispatcher_guard_chain():
    """GUARD_CHAIN from pretooluse-dispatcher.py, loaded without running main()
    (module-level import only; main() is __name__-guarded -- see that file's
    own _load() docstring for the same pattern)."""
    path = os.path.join(HOOKS_DIR, DISPATCHER)
    spec = importlib.util.spec_from_file_location("_dispatcher_under_test", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.GUARD_CHAIN


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


# lint-config-guard.py (OI-148, 2026-08-13) -- pre-create the protected target
# so _file_state sees 'exists' (the guard is EXISTING-FILE-ONLY by design; a
# non-existent target is a deliberate first-time-create pass-through, not a
# guard gap -- see that file's own module docstring).
_LINT_ROOT = tempfile.mkdtemp(prefix="wgc-lint-root-")
_LINT_SESS = tempfile.mkdtemp(prefix="wgc-lint-sess-")
with open(os.path.join(_LINT_ROOT, "eslint.config.js"), "w", encoding="utf-8") as _f:
    _f.write("export default []")


def lint_config_case(shape):
    target = os.path.join(_LINT_ROOT, "eslint.config.js").replace("\\", "/")
    payload = {"session_id": "meta-s1", "tool_name": shape.tool_name,
               "tool_input": shape.build(target)}
    return payload, {"ORA_LINT_CONFIG_GUARD_ROOT": _LINT_ROOT,
                     "ORA_OVERRIDE_SESSIONS_DIR": _LINT_SESS}


# ascii-only-guard.py (wired 2026-09-30, hooks-audit). Contracted to exactly the
# shapes its introduced_text() reads: Write / Edit and the Desktop Commander
# write_file / edit_block twins (both path fields, both DC prefixes). MultiEdit
# and NotebookEdit are deliberately NOT contracted -- 0 real calls each over the
# 1628 transcripts its docstring measured, so a branch there would be dead code.
ASCII_TOOLS = frozenset(("Write", "Edit")) \
    | tcp.DC_WRITE_FILE_NAMES | tcp.DC_EDIT_BLOCK_NAMES
_ASCII_ROOT = tempfile.mkdtemp(prefix="wgc-ascii-root-")
_ASCII_SESS = tempfile.mkdtemp(prefix="wgc-ascii-sess-")
_ASCII_MODULE = '"""Fixture.\n\nStdlib only. ASCII-only. Windows (`python`).\n"""\nX = 1\n'
_EM_DASH = "\u2014"


def ascii_case(shape):
    target = os.path.join(_ASCII_ROOT, "declared_%s.py" % shape.name
                          .replace("-", "_")).replace("\\", "/")
    with open(target, "w", encoding="ascii") as fh:
        fh.write(_ASCII_MODULE)
    bad = "Y = 'a %s b'\n" % _EM_DASH
    payload = {"session_id": "meta-s1", "tool_name": shape.tool_name,
               "tool_input": shape.build(target, content=_ASCII_MODULE + bad,
                                         old="X = 1\n", new=bad)}
    return payload, {"ORA_OVERRIDE_SESSIONS_DIR": _ASCII_SESS}


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
    # lint-config-guard.py is contracted to every FILE and MOVE shape (it
    # resolves real write_targets() for those, same as config-write-guard.py)
    # but NOT shell shapes here -- its shell-text matcher requires the LITERAL
    # "oxford-command-center" marker (a fixed constant, not derived from the
    # ORA_LINT_CONFIG_GUARD_ROOT test seam), so a shell Shape built against
    # this meta-test's temp root would never match; that path is already
    # covered directly in hooks/tests/test-lint-config-guard.py's own shell
    # cases instead.
    GuardSpec("lint-config-guard.py",
              lambda s: s.kind in ("file", "move"),
              lint_config_case, blocked_exit2, "lint-config-guard.py"),
    GuardSpec("ascii-only-guard.py",
              lambda s: s.kind == "file" and s.tool_name in ASCII_TOOLS,
              ascii_case, blocked_exit2, "ascii-only-guard.py"),
]


sys.path.insert(0, os.path.join(HOOKS_DIR, "tests", "lib"))
import settings_proposal  # noqa: E402


def settings_views():
    """[(label, settings, guard specs to check)] -- ALWAYS the tracked
    settings.json, never an untracked side file (adversarial review
    2026-09-30, finding 1).

      * "live"      -- the file exactly as tracked. Every guard EXCEPT
                       ascii-only-guard must already be routed here: the
                       hooks-audit proposal does not touch them, so a live gap
                       is a real gap before and after the apply.
      * "effective" -- settings_proposal.effective(live): as-is once the
                       proposal is applied, else with it applied in memory.
                       EVERY guard, ascii-only-guard's Desktop Commander entry
                       included, must be routed here.
    Post-apply both views are the same file, so the ascii guard is then
    asserted against the real tracked settings with no code change."""
    with open(os.path.join(CLAUDE_ROOT, "settings.json"), "r",
              encoding="utf-8-sig") as fh:
        live = json.load(fh)
    st = settings_proposal.state(live)
    legacy = [g for g in GUARDS if g.hook != "ascii-only-guard.py"]
    return [("live[%s]" % st, live, legacy),
            ("effective[%s]" % st, settings_proposal.effective(live), GUARDS)]


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
    """A guard is 'routed' for a shape either (a) directly -- some settings.json
    PreToolUse entry names the guard's own script and its matcher covers the
    shape's tool_name -- or (b) via the dispatcher -- pretooluse-dispatcher.py's
    matcher covers the tool_name AND the guard is a GUARD_CHAIN member, since
    the dispatcher runs every chain member in-process for anything its matcher
    catches (2026-08-05 wiring). Recognizing (b) is what keeps this test able
    to go red on a REAL gap (guard dropped from GUARD_CHAIN, or the dispatcher's
    own matcher narrowed) instead of alarming on the dispatcher refactor itself."""
    guard_chain = _dispatcher_guard_chain()
    for view, settings, specs in settings_views():
        _route_checks(view, settings, specs, guard_chain)


def _route_checks(view, settings, specs, guard_chain):
    entries = settings.get("hooks", {}).get("PreToolUse", [])
    dispatcher_matchers = [e.get("matcher", "") for e in entries
                            if any(DISPATCHER in (h.get("command") or "")
                                   for h in e.get("hooks", []))]
    for spec in specs:
        matchers = [e.get("matcher", "") for e in entries
                    if any(spec.matcher_key in (h.get("command") or "")
                           for h in e.get("hooks", []))]
        in_chain = spec.hook[:-len(".py")] in guard_chain
        check("[%s] %s is registered in settings.json PreToolUse" % (view, spec.hook),
              len(matchers) >= 1 or in_chain)
        for shape in tcp.SHAPES:
            if not spec.shape_filter(shape):
                continue
            direct = any(re.fullmatch(m, shape.tool_name) for m in matchers if m)
            via_dispatcher = in_chain and any(
                re.fullmatch(m, shape.tool_name) for m in dispatcher_matchers if m)
            check("[%s] settings.json routes %s to %s" % (view, shape.tool_name, spec.hook),
                  direct or via_dispatcher,
                  "matchers=%r dispatcher_matchers=%r in_chain=%s" %
                  (matchers, dispatcher_matchers, in_chain))
            # A guard both directly matched AND dispatcher-chained for the same
            # shape runs TWICE per tool call -- silent for stateless guards but
            # a real bug for anything with single-use state (e.g.
            # ora-autonomy-gate.py consumes its override token on the first
            # pass, then blocks on the second). GUARD_CHAIN's own docstring
            # names this exact trap: "add it to GUARD_CHAIN -- NOT as a new
            # settings.json PreToolUse entry -- or it will run twice."
            check("[%s] %s is not double-routed for %s (direct + dispatcher)"
                  % (view, spec.hook, shape.tool_name),
                  not (direct and via_dispatcher))


if __name__ == "__main__":
    test_guard_shape_matrix()
    test_new_hard_gate_is_contracted_to_every_shape()
    test_settings_matchers_route_every_contracted_shape()
    if _failures:
        print("\n%d FAILURE(S): %s" % (len(_failures), ", ".join(sorted(set(_failures))[:12])))
        sys.exit(1)
    print("\nALL write-guard coverage meta-tests passed.")
    sys.exit(0)
