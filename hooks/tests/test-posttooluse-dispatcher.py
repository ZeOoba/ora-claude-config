"""Tests for hooks/posttooluse-dispatcher.py (hooks-audit 2026-09-30, Task 5).

THE LOAD-BEARING TEST is per-tool coverage equivalence: for every real tool
name below, the set of PostToolUse hooks that fire under the settings file
under test (settings entries + the dispatcher's internal per-hook matchers)
must equal the set that fired under the FROZEN pre-change PostToolUse block
(live settings.json at 1370b41), minus exactly the deliberately deleted
deploy-grep hook. It is checked under BOTH plausible harness matcher
semantics -- anchored ^(?:m)$ and unanchored re.search -- so the proof does not
depend on which one the harness actually uses.

Settings under test: the TRACKED <repo>/settings.json, judged through
hooks/tests/lib/settings_proposal.effective() -- as-is once the proposal is
applied, or with the proposal applied IN MEMORY while it is still pending. So
the test means the same thing in this worktree, a fresh clone, the live
checkout before the apply, and after it; it never reads _proposed/.

Also pinned: the catch-up prefilter is a SUPERSET of catch_up_main's own
matcher (fuzzed over its positive corpus), catch_up is not spawned for
ordinary Bash, its timeout terminates the child without costing the other
hooks, per-hook failure isolation, output merging, and exit 0 on garbage.
The inline Netlify-updater hook is DELETED (Gabriel 2026-09-30: all three
*-updater tools are permission-denied), so no Netlify tool is covered by any
hook this change adds (E1).

Stdlib only. ASCII-only. Windows (`python`).
"""
import importlib.util
import io
import json
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
import time

HOOKS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(HOOKS_DIR)
DISPATCHER = os.path.join(HOOKS_DIR, "posttooluse-dispatcher.py")

_failures = []


def check(name, cond, detail=""):
    if cond:
        print("PASS " + name)
    else:
        print("FAIL " + name + ("  " + detail if detail else ""))
        _failures.append(name)


def skip(name, reason):
    print("SKIP " + name + "  -- " + reason)


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def load_dispatcher():
    return _load(DISPATCHER, "_postdisp_%d" % random.randint(0, 10 ** 9))


sys.path.insert(0, os.path.join(HOOKS_DIR, "tests", "lib"))
import settings_proposal  # noqa: E402


def settings_under_test():
    path = os.path.join(REPO, "settings.json")
    with open(path, "r", encoding="utf-8-sig") as fh:
        live = json.load(fh)
    label = "settings.json [%s]" % settings_proposal.state(live)
    return label, settings_proposal.effective(live)


# ---------------------------------------------------------------- the baseline
NETLIFY = "mcp__a66aaa4a-ffcd-4066-b2af-79c4ce807809__.*"
DC_WRITES = ("Edit|Write|MultiEdit|mcp__Desktop_Commander__write_file|"
             "mcp__Desktop_Commander__edit_block|"
             "mcp__plugin_desktop-commander_desktop-commander__write_file|"
             "mcp__plugin_desktop-commander_desktop-commander__edit_block")
# Live settings.json PostToolUse at 1370b41, in file order: (matcher, hook id).
FROZEN_BASELINE_POST = [
    ("Bash", "catch-up-main"),
    ("Bash", "deploy-grep-curl"),
    (NETLIFY, "netlify-updater-check"),
    ("Bash|Task|TaskCreate|TaskUpdate|Edit|Write|MultiEdit", "fleet-session-hook"),
    ("Write|Edit|Skill", "eos-plan-marker"),
    ("Bash", "eos-gate-sentinel"),
    (DC_WRITES, "commit-provenance-recorder"),
    (DC_WRITES, "memory-nag-correction"),
    ("mcp__scheduled-tasks__update_scheduled_task", "scheduled-task-update-postguard"),
]
DELETED = {"deploy-grep-curl", "netlify-updater-check"}
FOLDED = {"catch-up-main", "deploy-grep-curl", "netlify-updater-check",
          "eos-gate-sentinel"}

TOOLS = [
    "Bash", "Task", "Agent", "TaskCreate", "TaskUpdate", "TaskList", "Edit", "Write",
    "MultiEdit", "NotebookEdit", "Skill", "Read", "Grep",
    "mcp__Desktop_Commander__write_file", "mcp__Desktop_Commander__edit_block",
    "mcp__plugin_desktop-commander_desktop-commander__write_file",
    "mcp__plugin_desktop-commander_desktop-commander__edit_block",
    "mcp__Desktop_Commander__start_process",
    "mcp__a66aaa4a-ffcd-4066-b2af-79c4ce807809__netlify-deploy-services-updater",
    "mcp__a66aaa4a-ffcd-4066-b2af-79c4ce807809__netlify-project-services-updater",
    "mcp__a66aaa4a-ffcd-4066-b2af-79c4ce807809__netlify-extension-services-updater",
    "mcp__a66aaa4a-ffcd-4066-b2af-79c4ce807809__netlify-deploy-services-reader",
    "mcp__a66aaa4a-ffcd-4066-b2af-79c4ce807809__get-netlify-coding-context",
    "mcp__scheduled-tasks__update_scheduled_task",
    "mcp__scheduled-tasks__create_scheduled_task",
    "mcp__c5f4869f-7d3a-4472-a66a-8e61315feb51__notion-create-pages",
    "mcp__c0ea3c01-b8f1-4371-aa06-08a1449f59fc__outlook_send_mail",
    "mcp__excel__write_data_to_excel",
    "bash", "edit", "FooBash", "BashX",
]


def hook_id_from_command(cmd):
    if "catch_up_main.py" in cmd:
        return "catch-up-main"
    if 'grep -o \\"deploy\\"' in cmd or 'grep -o "deploy"' in cmd:
        return "deploy-grep-curl"
    if "updater$" in cmd and "curl" in cmd:
        return "netlify-updater-check"
    if "posttooluse-dispatcher.py" in cmd:
        return "@dispatcher"
    m = re.search(r"([A-Za-z0-9_.-]+)\.py", cmd)
    return m.group(1) if m else "inline:" + cmd[:30]


def harness_match(matcher, tool, anchored):
    """anchored=False is the DOCUMENTED harness behavior
    (code.claude.com/docs/en/hooks: a matcher of only letters, digits, `_`, `-`,
    spaces, `,`, `|` is an exact-name list; anything else is tested with
    JavaScript RegExp.prototype.test, i.e. UNANCHORED). anchored=True is the
    stricter ^(?:m)$ model the audit also asked for."""
    if matcher in ("", "*"):
        return True
    if re.fullmatch(r"[A-Za-z0-9_\-, |]*", matcher):
        return tool in [p.strip() for p in re.split(r"[|,]", matcher) if p.strip()]
    if anchored:
        return re.fullmatch(matcher, tool) is not None
    return re.search(matcher, tool) is not None


def fired_baseline(tool, anchored):
    return sorted(h for m, h in FROZEN_BASELINE_POST if harness_match(m, tool, anchored))


def fired_settings(settings, disp, tool, anchored):
    out = []
    for e in settings.get("hooks", {}).get("PostToolUse", []):
        if not harness_match(e.get("matcher", ""), tool, anchored):
            continue
        for h in e.get("hooks", []):
            hid = hook_id_from_command(h.get("command", ""))
            if hid == "@dispatcher":
                out.extend(ph.name for ph in disp.POST_HOOKS
                           if disp.matcher_matches(ph.matcher, tool))
            else:
                out.append(hid)
    return sorted(out)


def test_frozen_baseline_matches_tracked_settings():
    with open(os.path.join(REPO, "settings.json"), "r", encoding="utf-8-sig") as fh:
        tracked = json.load(fh)
    entries = tracked["hooks"]["PostToolUse"]
    with open(os.path.join(REPO, "settings.json"), "rb") as fh:
        sha = settings_proposal.normalized_sha256(fh.read())
    if sha != settings_proposal.BASE_SHA256:
        # A snapshot comparison is only meaningful against the exact file the
        # frozen table was taken from; any later routine settings edit by
        # another session must not turn the pre-push gate red (re-review C8).
        skip("E0 frozen baseline vs tracked settings.json",
             "settings.json has moved off the 1370b41 base (state %s); the frozen "
             "table is the record -- if a re-apply is pending, re-render per "
             "APPLY.md step 4" % settings_proposal.state(tracked))
        return
    got = [(e.get("matcher", ""), hook_id_from_command(h.get("command", "")))
           for e in entries for h in e.get("hooks", [])]
    check("E0 frozen baseline == tracked (pre-change) settings.json PostToolUse",
          got == FROZEN_BASELINE_POST, "got=%r" % got)


def test_coverage_equivalence():
    path, settings = settings_under_test()
    disp = load_dispatcher()
    print("  (settings under test: %s)" % path)
    with open(os.path.join(REPO, "settings.json"), "r", encoding="utf-8-sig") as fh:
        live = json.load(fh)
    # DIRECTIONAL, never a snapshot of live state (re-review 2026-09-30, C8):
    #  E1  the FOLDED hooks fire for exactly the tools they fired for at
    #      1370b41 (minus the deleted deploy-grep) -- this branch owns them;
    #  E1b every OTHER PostToolUse hook fires identically in effective and live
    #      settings -- the proposal must not touch hooks it does not own, and
    #      whatever other sessions add to settings.json is carried through.
    for anchored in (True, False):
        sem = "anchored" if anchored else "documented-unanchored"
        for tool in TOOLS:
            want = sorted((set(fired_baseline(tool, anchored)) & FOLDED) - DELETED)
            got_all = fired_settings(settings, disp, tool, anchored)
            got = sorted(set(got_all) & FOLDED)
            check("E1[%s] %s fires the same folded PostToolUse hooks" % (sem, tool),
                  got == want, "want=%r got=%r" % (want, got))
            other_eff = sorted(h for h in got_all if h not in FOLDED)
            other_live = sorted(h for h in fired_settings(live, disp, tool, anchored)
                                if h not in FOLDED)
            check("E1b[%s] %s: non-folded hooks identical in live and effective"
                  % (sem, tool), other_eff == other_live,
                  "live=%r effective=%r" % (other_live, other_eff))
    check("E2 deploy-grep hook is gone for every tool",
          not any("deploy-grep-curl" in fired_settings(settings, disp, t, a)
                  for t in TOOLS for a in (True, False)))
    entries = [e for e in settings["hooks"]["PostToolUse"]
               if any("posttooluse-dispatcher.py" in h.get("command", "")
                      for h in e.get("hooks", []))]
    check("E3 exactly one dispatcher entry", len(entries) == 1, repr(len(entries)))
    if entries:
        e = entries[0]
        check("E4 dispatcher entry matcher == union of its hooks' matchers",
              e.get("matcher") == disp.DISPATCHER_MATCHER, repr(e.get("matcher")))
        check("E5 dispatcher entry keeps catch_up's 360s timeout",
              all(h.get("timeout", 0) >= 360 for h in e["hooks"]))
        check("E6 dispatcher timeout exceeds the child's, so the dispatcher kills it",
              disp.CATCH_UP_TIMEOUT_S < min(h.get("timeout", 0) for h in e["hooks"]))
        check("E7 dispatcher entry is synchronous (not async)",
              not any(h.get("async") for h in e["hooks"]))
    names = {ph.name for ph in disp.POST_HOOKS}
    direct = {hook_id_from_command(h.get("command", ""))
              for e in settings["hooks"]["PostToolUse"] for h in e.get("hooks", [])}
    check("E8 no folded hook is ALSO registered directly (would run twice)",
          not (names & direct), repr(names & direct))
    # The union matcher must match a tool iff at least one internal hook does
    # (anchored): otherwise the dispatcher spawns for nothing, or misses.
    for tool in TOOLS:
        outer = disp.matcher_matches(disp.DISPATCHER_MATCHER, tool)
        inner = any(disp.matcher_matches(ph.matcher, tool) for ph in disp.POST_HOOKS)
        if outer != inner:
            check("E9 union matcher agrees with internal routing for %s" % tool, False)
            break
    else:
        check("E9 union matcher agrees with internal routing for every tool", True)


# ------------------------------------------------------------- the prefilter
POSITIVE_CORPUS = [
    'gh pr merge 57 --squash -R ZeOoba/ora-skills',
    'gh pr merge 57 --repo=ZeOoba/ora-skills --merge',
    'gh pr merge 63 --repo ZeOoba/ora-skills --squash',
    'gh pr merge 63 -R https://github.com/ZeOoba/ora-skills.git',
    'gh pr merge 63 -RZeOoba/ora-skills',
    'gh pr merge https://github.com/ZeOoba/ora-skills/pull/63',
    'git status && gh pr merge 63 -R ZeOoba/ora-skills',
    'git status; gh pr merge 63 -R ZeOoba/ora-skills',
    'false || gh pr merge 63 -R ZeOoba/ora-skills',
    '(gh pr merge 63 -R ZeOoba/ora-skills)',
    '( cd x && gh pr merge 63 -R ZeOoba/ora-skills )',
    'out=$(gh pr merge 63 -R ZeOoba/ora-skills)',
    'git status | cat\ngh pr merge 63 -R ZeOoba/ora-skills',
    'GH_PROMPT_DISABLED=1 gh pr merge 63 -R ZeOoba/ora-skills',
    'X=(a b) gh pr merge 63 -R ZeOoba/ora-skills',
    'gh pr merge 63 -R=ZeOoba/ora-skills',
    'cat <<EOF\ngh pr merge 5 -R ZeOoba/other\nEOF\ngh pr merge 63 -R ZeOoba/ora-skills',
    'A=("x y" "$(echo z)"); gh pr merge 5 -R ZeOoba/ora-skills',
    'A+=(x)\ngh pr merge 5 -R ZeOoba/ora-skills',
]
EXTRA_SPELLINGS = [
    '"gh" pr merge 5 -R ZeOoba/ora-skills',
    "gh 'pr' \"merge\" 5 -R ZeOoba/ora-skills",
    'g"h" p\'r\' merge 5 -R ZeOoba/ora-skills',
    'g\\h pr merge 5 -R ZeOoba/ora-skills',
    'GH pr merge 5 -R ZeOoba/ora-skills',
    'gh.exe pr merge 5 -R ZeOoba/ora-skills',
    'C:\\Tools\\GH.EXE pr merge 5 -R ZeOoba/ora-skills',
    '/usr/bin/gh pr merge 5 -R ZeOoba/ora-skills',
    'gh\tpr\t\tmerge 5 -R ZeOoba/ora-skills',
    'gh pr \\\nmerge 5 -R ZeOoba/ora-skills',
    'gh \\\n pr merge 5 -R ZeOoba/ora-skills',
    'gh\x0bpr\x0cmerge 5 -R ZeOoba/ora-skills',
    'gh pr merge -R ZeOoba/ora-skills 5',
]


def _variants(cmd, rng):
    """Spelling-level mutations bash (and catch_up_main's scanner) treat as the
    same words: quoting pieces of a word, backslash-escaping a letter, varying
    whitespace, uppercasing gh."""
    out = [cmd]
    for _ in range(12):
        s = cmd
        choice = rng.randint(0, 5)
        if choice == 0:
            s = s.replace("gh pr", "gh" + rng.choice([" ", "  ", "\t", " \t "]) + "pr")
        elif choice == 1:
            s = s.replace("gh pr merge", '"g"h pr me"r"ge')
        elif choice == 2:
            s = s.replace("gh pr merge", "g\\h p\\r merg\\e")
        elif choice == 3:
            s = s.replace("gh pr", "Gh pr")
        elif choice == 4:
            s = s.replace("pr merge", "pr" + rng.choice([" \\\n", "\t", "   "]) + "merge")
        else:
            s = s.replace("gh pr merge", "'gh' 'pr' 'merge'")
        out.append(s)
    return out


def _load_catch_up(disp):
    path = disp.CATCH_UP_SCRIPT
    if not os.path.isfile(path):
        return None
    try:
        return _load(path, "_catch_up_main_readonly")
    except Exception:
        return None


def test_prefilter_is_superset():
    disp = load_dispatcher()
    cum = _load_catch_up(disp)
    if cum is None:
        skip("P1 prefilter superset of is_ora_skills_merge",
             "catch_up_main.py not importable at %s" % disp.CATCH_UP_SCRIPT)
        return
    rng = random.Random(20260930)
    checked = positives = 0
    misses = []
    for base in POSITIVE_CORPUS + EXTRA_SPELLINGS:
        for cmd in _variants(base, rng):
            payload = {"tool_name": "Bash", "tool_input": {"command": cmd}}
            real = cum.is_ora_skills_merge(payload)
            checked += 1
            if real:
                positives += 1
                if not disp.gh_pr_merge_prefilter(payload):
                    misses.append(cmd)
    check("P1 prefilter never rejects a payload catch_up_main would act on "
          "(%d variants, %d real positives)" % (checked, positives),
          not misses, "misses=%r" % misses[:5])
    check("P2 the corpus actually exercised positives", positives >= 40,
          "positives=%d" % positives)
    for base in POSITIVE_CORPUS[:6]:
        check("P3 base corpus entry is a real positive: %r" % base[:40],
              cum.is_ora_skills_merge({"tool_name": "Bash",
                                       "tool_input": {"command": base}}))


def test_prefilter_filters():
    disp = load_dispatcher()
    for cmd in ("ls -la", "git status", "python hooks/tests/test-x.py",
                "echo merge conflicts", "git merge origin/main",
                "gh pr view 5", "gh pr list"):
        check("P4 prefilter declines ordinary Bash: %r" % cmd,
              not disp.gh_pr_merge_prefilter(
                  {"tool_name": "Bash", "tool_input": {"command": cmd}}))
    for bad in (None, {}, {"tool_name": "Edit", "tool_input": {"command": "gh pr merge 1"}},
                {"tool_name": "Bash", "tool_input": "gh pr merge"},
                {"tool_name": "Bash", "tool_input": {"command": 7}}):
        check("P5 prefilter declines malformed/non-Bash payload %r" % (bad,),
              not disp.gh_pr_merge_prefilter(bad))
    check("P6 cwd-inferred form still passes the prefilter",
          disp.gh_pr_merge_prefilter({"tool_name": "Bash", "tool_input": {
              "command": "cd somewhere && gh pr merge 57 --squash"}}))


# --------------------------------------------------------------- behaviour
FAKE_CATCHUP = r'''
import json, os, sys, time
raw = sys.stdin.buffer.read()
with open(os.environ["FAKE_CATCHUP_MARKER"], "wb") as fh:
    fh.write(json.dumps({"argv": sys.argv[1:], "stdin": raw.decode("utf-8")}).encode("utf-8"))
if os.environ.get("FAKE_CATCHUP_SLEEP"):
    time.sleep(float(os.environ["FAKE_CATCHUP_SLEEP"]))
print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse",
      "additionalContext": "ora-skills local main catch-up: NOOP -- fake"}}))
'''


class Rig(object):
    def __init__(self):
        self.root = tempfile.mkdtemp(prefix="postdisp-")
        self.sessions = os.path.join(self.root, "sessions")
        self.marker = os.path.join(self.root, "catchup-called.json")
        self.log = os.path.join(self.root, "telemetry.jsonl")
        self.fake = os.path.join(self.root, "fake_catch_up.py")
        with open(self.fake, "w", encoding="ascii") as fh:
            fh.write(FAKE_CATCHUP)
        self._env = {}
        self.setenv(EOS_SESSIONS_DIR=self.sessions, FAKE_CATCHUP_MARKER=self.marker,
                    ORA_GUARD_TELEMETRY_PATH=self.log, ORA_GUARD_TELEMETRY=None,
                    FAKE_CATCHUP_SLEEP=None)
        self.disp = load_dispatcher()
        self.disp.CATCH_UP_SCRIPT = self.fake

    def setenv(self, **kw):
        for k, v in kw.items():
            self._env.setdefault(k, os.environ.get(k))
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def run(self, payload):
        raw = payload if isinstance(payload, bytes) else json.dumps(payload).encode("utf-8")

        class _In(object):
            buffer = io.BytesIO(raw)
        real_in, real_out, real_err = sys.stdin, sys.stdout, sys.stderr
        out, err = io.StringIO(), io.StringIO()
        sys.stdin, sys.stdout, sys.stderr = _In(), out, err
        try:
            rc = self.disp.main()
        finally:
            sys.stdin, sys.stdout, sys.stderr = real_in, real_out, real_err
        return rc, out.getvalue(), err.getvalue()

    def records(self):
        try:
            with open(self.log, "r", encoding="ascii") as fh:
                return [json.loads(x) for x in fh if x.strip()]
        except OSError:
            return []

    def cleanup(self):
        for k, v in self._env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        shutil.rmtree(self.root, ignore_errors=True)


def bash(cmd, sid="post-sess-1"):
    return {"session_id": sid, "hook_event_name": "PostToolUse", "tool_name": "Bash",
            "tool_input": {"command": cmd}, "tool_response": {"stdout": "ok"}}


def test_catch_up_only_on_merge():
    r = Rig()
    try:
        rc, out, err = r.run(bash("ls -la"))
        check("B1 ordinary Bash: exit 0, no output", rc == 0 and out == "", repr((rc, out)))
        check("B2 ordinary Bash: catch_up NOT spawned", not os.path.exists(r.marker))
        recs = {x["guard"]: x for x in r.records()}
        check("B3 telemetry marks catch-up-main skipped",
              recs.get("catch-up-main", {}).get("path_taken") == "skipped", repr(recs))

        p = bash("gh pr merge 5 --squash -R ZeOoba/ora-skills")
        rc, out, err = r.run(p)
        check("B4 merge: exit 0", rc == 0)
        check("B5 merge: catch_up spawned", os.path.exists(r.marker))
        if os.path.exists(r.marker):
            with open(r.marker, "rb") as fh:
                seen = json.loads(fh.read().decode("utf-8"))
            check("B6 catch_up got --hook", seen["argv"] == ["--hook"], repr(seen["argv"]))
            check("B7 catch_up got the payload byte-identical",
                  json.loads(seen["stdin"]) == p)
        try:
            obj = json.loads(out)
        except ValueError:
            obj = {}
        check("B8 its additionalContext is relayed as valid PostToolUse JSON",
              obj.get("hookSpecificOutput", {}).get("additionalContext", "")
              .startswith("ora-skills local main catch-up") and
              obj["hookSpecificOutput"].get("hookEventName") == "PostToolUse", out[:200])
    finally:
        r.cleanup()


def test_eos_gate_sentinel_still_fires():
    r = Rig()
    try:
        rc, out, _ = r.run(bash("python hooks/tests/test-foo.py", sid="sent-1"))
        check("G1 test command: exit 0", rc == 0)
        check("G2 eos-gate-sentinel dropped gate-green via the dispatcher",
              os.path.isfile(os.path.join(r.sessions, "sent-1", "gate-green")))
        recs = {x["guard"]: x for x in r.records()}
        check("G3 and ran IN-PROCESS",
              recs.get("eos-gate-sentinel", {}).get("path_taken") == "inprocess",
              repr(recs.get("eos-gate-sentinel")))
        r.run(bash("ls", sid="sent-2"))
        check("G4 non-test command drops no marker",
              not os.path.exists(os.path.join(r.sessions, "sent-2")))
        r.run({"session_id": "sent-3", "tool_name": "Edit",
               "tool_input": {"command": "pytest"}})
        check("G5 sentinel does not run for Edit (matcher Bash only)",
              not os.path.exists(os.path.join(r.sessions, "sent-3")))
    finally:
        r.cleanup()


def test_timeout_isolated():
    r = Rig()
    try:
        r.setenv(FAKE_CATCHUP_SLEEP="30")
        r.disp.CATCH_UP_TIMEOUT_S = 2
        t0 = time.time()
        rc, out, err = r.run(bash("pytest -q && gh pr merge 5 -R ZeOoba/ora-skills",
                                  sid="to-1"))
        dt = time.time() - t0
        check("T1 a hung catch_up is terminated at its timeout (%.1fs)" % dt,
              dt < 15, "dt=%.1f" % dt)
        check("T2 exit 0 regardless", rc == 0)
        check("T3 the timeout is reported on stderr", "terminated" in err, err[:200])
        check("T4 the hooks before it still ran (gate-green present)",
              os.path.isfile(os.path.join(r.sessions, "to-1", "gate-green")))
    finally:
        r.cleanup()


def test_failure_isolation():
    r = Rig()
    try:
        empty_hooks = os.path.join(r.root, "emptyhooks")
        os.makedirs(empty_hooks)
        r.disp.HOOKS_DIR = empty_hooks
        rc, out, err = r.run(bash("pytest && gh pr merge 5 -R ZeOoba/ora-skills"))
        check("F1 missing eos-gate-sentinel: exit 0", rc == 0)
        check("F2 missing eos-gate-sentinel: reported, and catch_up still ran",
              "missing" in err and os.path.exists(r.marker), err[:200])
        os.remove(r.marker)

        with open(os.path.join(empty_hooks, "eos-gate-sentinel.py"), "w") as fh:
            fh.write("def main():\n    raise RuntimeError('boom')\n")
        rc, out, err = r.run(bash("pytest && gh pr merge 5 -R ZeOoba/ora-skills"))
        check("F3 raising hook: exit 0 and catch_up still ran",
              rc == 0 and os.path.exists(r.marker), err[:200])
        os.remove(r.marker)

        r.disp.CATCH_UP_SCRIPT = os.path.join(r.root, "nope.py")
        rc, out, err = r.run(bash("gh pr merge 5 -R ZeOoba/ora-skills"))
        check("F4 missing catch_up script: exit 0, reported", rc == 0 and "missing" in err)
    finally:
        r.cleanup()


def test_malformed_input_exit_zero_subprocess():
    tmp = tempfile.mkdtemp(prefix="postdisp-e2e-")
    try:
        env = dict(os.environ)
        env["ORA_GUARD_TELEMETRY_PATH"] = os.path.join(tmp, "t.jsonl")
        env["EOS_SESSIONS_DIR"] = os.path.join(tmp, "s")
        for label, data in (("garbage", b"not json {"), ("empty", b""),
                            ("list", b"[1,2]"), ("no tool", b"{}"),
                            ("ordinary Bash", json.dumps(bash("ls")).encode())):
            p = subprocess.run([sys.executable, DISPATCHER], input=data,
                               capture_output=True, timeout=60, env=env)
            check("M1 real process exits 0 on %s input" % label,
                  p.returncode == 0 and p.stdout == b"", repr((p.returncode, p.stdout[:80])))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_merge_outputs():
    disp = load_dispatcher()
    a = json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse",
                                           "additionalContext": "A"}})
    b = json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse",
                                           "additionalContext": "B"},
                    "systemMessage": "S"})
    check("O1 a single emitter passes through byte-for-byte", disp.merge_outputs([a]) == a)
    merged = disp.merge_outputs([a, "chatter, not json", b])
    try:
        obj = json.loads(merged)
    except ValueError:
        obj = {}
    check("O2 two emitters merge into ONE valid JSON object",
          obj.get("hookSpecificOutput", {}).get("additionalContext") == "A\n\nB"
          and obj["hookSpecificOutput"].get("hookEventName") == "PostToolUse"
          and obj.get("systemMessage") == "S", merged)
    check("O3 nothing to say -> empty output", disp.merge_outputs(["", "  "]) == "")


if __name__ == "__main__":
    for t in (test_frozen_baseline_matches_tracked_settings, test_coverage_equivalence,
              test_prefilter_is_superset, test_prefilter_filters,
              test_catch_up_only_on_merge, test_eos_gate_sentinel_still_fires,
              test_timeout_isolated, test_failure_isolation,
              test_malformed_input_exit_zero_subprocess, test_merge_outputs):
        t()
    if _failures:
        print("\n%d FAILURE(S): %s" % (len(_failures), ", ".join(_failures[:12])))
        sys.exit(1)
    print("\nALL posttooluse-dispatcher tests passed.")
    sys.exit(0)
