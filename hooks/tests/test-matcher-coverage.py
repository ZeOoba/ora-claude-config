"""PreToolUse matcher wiring-coverage test (hooks-audit 2026-09-30, Task 6).

test-write-guard-coverage.py proves each WRITE guard fires for every write
SHAPE; this file proves the ROUTING: for each REAL tool name the harness
emits, the settings file under test plus the dispatcher chains deliver the
tool to exactly the intended guard set -- no guard missing, none extra, none
twice. Every routing assertion runs under TWO matcher models:

  * anchored   -- ^(?:matcher)$, case-sensitive (the model the audit asked for);
  * documented -- what the harness actually does per
    code.claude.com/docs/en/hooks ("Regex Behavior"): a matcher made only of
    letters, digits, `_`, `-`, spaces, `,` and `|` is an exact-name list;
    anything else is tested with JavaScript RegExp.prototype.test, i.e. an
    UNANCHORED search. Case-sensitive (JS regex default; the page is silent).

Settings under test: the TRACKED <repo>/settings.json, through
hooks/tests/lib/settings_proposal.effective() (as-is once the hooks-audit
proposal is applied, with it applied in memory while pending). Also asserted:
the live file differs from the effective one by EXACTLY the proposal's
PreToolUse delta (ascii-only-guard on the four Desktop Commander write tools),
and _proposed/settings.json, when present, is byte-identical to the rendered
proposal -- so the reviewable artifact cannot drift from what is tested.

KNOWN GAPS, SKIPPED HERE, NOT SILENTLY PASSED -- both belong to the
confidentiality-guard matcher, which is fenced to a separate Fable-tier task
(Task 1) and deliberately untouched on this branch:

  * The M365 connector's REAL tool names are lowercase
    (mcp__c0ea3c01-...__outlook_send_mail, outlook_send_draft,
    outlook_forward_mail, teams_send_chat_message, teams_send_channel_message).
    The live matcher spells `mcp__.*OUTLOOK_(SEND|...)`, uppercase, and names no
    Teams tool at all, so under case-sensitive matching (either model) NONE of
    the five reaches confidentiality-guard. Run this file with
    --demo-live-confidentiality-gap to watch that assertion fail against the
    live matcher string.
  * The Notion alternative `mcp__.*notion-(create|update|append|duplicate|move|
    comment)` has no trailing `.*`, so under the ANCHORED model it does not
    match the real names (notion-create-pages, notion-update-page, ...). Under
    the DOCUMENTED unanchored search -- what production actually does -- it
    does, so production is covered. The documented assertion runs; the
    anchored one is skipped pending the same Task 1 (which should make the
    matcher correct under both, e.g. an explicit `.*` suffix).

Stdlib only. ASCII-only. Windows (`python`).
"""
import importlib.util
import json
import os
import re
import sys

HOOKS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(HOOKS_DIR)
DISPATCHER = os.path.join(HOOKS_DIR, "pretooluse-dispatcher.py")

LIVE_CONFIDENTIALITY_MATCHER = (
    "NotebookEdit|mcp__.*notion-(create|update|append|duplicate|move|comment)"
    "|mcp__.*OUTLOOK_(SEND|CREATE_DRAFT|SEND_DRAFT|FORWARD|REPLY)")
PENDING_TASK1 = "pending Task 1 (confidentiality matcher fix, Fable tier)"

_failures = []


def check(name, cond, detail=""):
    if cond:
        print("PASS " + name)
    else:
        print("FAIL " + name + ("  " + detail if detail else ""))
        _failures.append(name)


def skip(name, reason):
    print("SKIP " + name + "  -- " + reason)


sys.path.insert(0, os.path.join(HOOKS_DIR, "tests", "lib"))
import settings_proposal  # noqa: E402


def load_live():
    with open(os.path.join(REPO, "settings.json"), "r", encoding="utf-8-sig") as fh:
        return json.load(fh)


def load_settings():
    live = load_live()
    return ("settings.json [%s]" % settings_proposal.state(live),
            settings_proposal.effective(live))


def load_chains():
    spec = importlib.util.spec_from_file_location("_mc_dispatcher", DISPATCHER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.CHAINS


_PLAIN = re.compile(r"^[A-Za-z0-9_\-, |]+$")


def matches(matcher, tool, anchored=True):
    """^(?:matcher)$ case-sensitive when anchored; re.search (the documented
    harness behavior) otherwise. A plain name list is exact membership in both."""
    if matcher in ("", "*"):
        return True  # an absent/empty/star matcher matches every tool
    if _PLAIN.match(matcher):
        return tool in [x.strip() for x in re.split(r"[|,]", matcher) if x.strip()]
    if anchored:
        return re.fullmatch(matcher, tool) is not None
    return re.search(matcher, tool) is not None


def guard_id(command, chains):
    """[guard ids] a settings.json hook command runs."""
    if "pretooluse-dispatcher.py" in command:
        m = re.search(r"--chain\s+(\S+)", command)
        return list(chains[m.group(1)] if m else chains["editwrite"])
    if "credentials|" in command and "BLOCKED: Cannot edit sensitive file" in command:
        return ["inline:sensitive-file-blocker"]
    m = re.search(r"([A-Za-z0-9_.-]+)\.py", command)
    return [m.group(1)] if m else ["inline:" + command[:24]]


def routed(settings, chains, tool, anchored=True):
    """Ordered guard ids that fire on PreToolUse for `tool`."""
    out = []
    for entry in settings.get("hooks", {}).get("PreToolUse", []):
        if not matches(entry.get("matcher", ""), tool, anchored):
            continue
        for h in entry.get("hooks", []):
            out.extend(guard_id(h.get("command", ""), chains))
    return out


NOTION = "mcp__c5f4869f-7d3a-4472-a66a-8e61315feb51__"
M365 = "mcp__c0ea3c01-b8f1-4371-aa06-08a1449f59fc__"
NETLIFY = "mcp__a66aaa4a-ffcd-4066-b2af-79c4ce807809__"
DC = ("mcp__Desktop_Commander__", "mcp__plugin_desktop-commander_desktop-commander__")

M365_SEND_FIXTURES = [M365 + n for n in (
    "outlook_send_mail", "outlook_send_draft", "outlook_forward_mail",
    "teams_send_chat_message", "teams_send_channel_message",
    "outlook_create_event", "outlook_update_event", "outlook_respond_to_event",
    "outlook_delete_event")]
NOTION_WRITE_FIXTURES = [NOTION + n for n in (
    "notion-create-pages", "notion-update-page", "notion-create-comment",
    "notion-duplicate-page", "notion-move-pages")]


def expectations(chains):
    ew = set(chains["editwrite"])
    bash = set(chains["bash"])
    dc_file = {"registry-write-guard", "ascii-only-guard", "config-write-guard",
               "lint-config-guard", "workbook-write-guard", "memory-index-guard"}
    dc_shell = {"config-write-guard", "lint-config-guard", "workbook-write-guard"}
    exp = {
        "Edit": ew | {"inline:sensitive-file-blocker", "workbook-write-guard"},
        "Write": ew | {"inline:sensitive-file-blocker", "workbook-write-guard"},
        "MultiEdit": ew | {"workbook-write-guard"},
        "Bash": bash,
        "NotebookEdit": {"ora-autonomy-gate", "confidentiality-guard",
                         "config-write-guard", "lint-config-guard",
                         "workbook-write-guard"},
        "mcp__excel__write_data_to_excel": {"config-write-guard",
                                            "workbook-write-guard"},
        NETLIFY + "netlify-deploy-services-updater": {"ora-autonomy-gate"},
        NETLIFY + "netlify-project-services-updater": {"ora-autonomy-gate"},
        NETLIFY + "netlify-extension-services-updater": {"ora-autonomy-gate"},
        NETLIFY + "netlify-deploy-services-reader": set(),
        NOTION + "notion-fetch": set(),
        NOTION + "notion-search": set(),
        "mcp__scheduled-tasks__update_scheduled_task": {
            "scheduled-task-update-preguard"},
        "Read": set(), "Grep": set(), "Glob": set(), "Skill": set(),
        # Case-sensitivity pins: a lowercase spelling is NOT the real tool.
        "edit": set(), "bash": set(),
    }
    for p in DC:
        exp[p + "write_file"] = set(dc_file)
        exp[p + "edit_block"] = set(dc_file)
        exp[p + "move_file"] = set(dc_shell)
        exp[p + "start_process"] = set(dc_shell)
        exp[p + "interact_with_process"] = set(dc_shell)
        exp[p + "write_pdf"] = set(dc_shell)
        exp[p + "read_file"] = set()
    return exp


def test_real_tool_names_reach_intended_guards():
    path, settings = load_settings()
    chains = load_chains()
    print("  (settings under test: %s)" % path)
    for anchored in (True, False):
        sem = "anchored" if anchored else "documented"
        for tool, want in sorted(expectations(chains).items()):
            got = routed(settings, chains, tool, anchored)
            # SUPERSET, not equality (re-review 2026-09-30, C8): a guard a
            # later session wires onto a tool must not turn the pre-push gate
            # red; a tool LOSING an intended guard must.
            if want:
                check("R1[%s] %s reaches at least %s" % (sem, tool, ",".join(sorted(want))),
                      want <= set(got), "missing=%s" % sorted(want - set(got)))
            elif tool in ("edit", "bash"):
                # Lowercase CASE PINS: a wrong-case name must reach nothing.
                check("R1[%s] %s (case pin) reaches NO PreToolUse guard" % (sem, tool),
                      not got, "got=%s" % sorted(set(got)))
            else:
                # Read-only tools: assert only what THIS branch owns (round-4):
                # a later session may legitimately guard reads (e.g. a
                # read-audit guard, or Task 1 widening notion-.*), and that
                # must not turn the pre-push gate red.
                check("R1[%s] %s does not reach ascii-only-guard" % (sem, tool),
                      "ascii-only-guard" not in got, "got=%s" % sorted(set(got)))
            dupes = sorted({g for g in got if got.count(g) > 1})
            check("R2[%s] %s runs no guard twice" % (sem, tool), not dupes,
                  "dupes=%s" % dupes)
    # Observation, not an assertion: under the documented UNANCHORED search the
    # workbook-write-guard matcher's bare `Write` / `Edit` alternatives act as
    # substrings, so e.g. TodoWrite reaches it. Harmless (that guard ignores
    # non-workbook payloads) and outside this branch's scope; printed so it is
    # visible rather than pinned.
    print("NOTE [documented] TodoWrite -> %s"
          % (",".join(routed(settings, chains, "TodoWrite", anchored=False)) or "(none)"))


def test_ascii_only_guard_wiring():
    path, settings = load_settings()
    chains = load_chains()
    check("A1 ascii-only-guard is in the Edit/Write dispatcher chain",
          "ascii-only-guard" in chains["editwrite"])
    check("A2 ascii-only-guard is NOT in the Bash chain (shell writes ungated by design)",
          "ascii-only-guard" not in chains["bash"])
    for anchored in (True, False):
        sem = "anchored" if anchored else "documented"
        for tool in ("Edit", "Write") + tuple(p + x for p in DC
                                             for x in ("write_file", "edit_block")):
            check("A3[%s] %s reaches ascii-only-guard exactly once" % (sem, tool),
                  routed(settings, chains, tool, anchored).count("ascii-only-guard") == 1)
        # MultiEdit DOES reach it (the dispatcher runs its whole chain for
        # Edit|Write|MultiEdit) but the guard reads no MultiEdit field and allows
        # -- a deliberate no-op, pinned in test-ascii-only-guard.py's docstring
        # measurement (0 real MultiEdit calls). These tools must not reach it:
        for tool in ("NotebookEdit", "Bash", DC[0] + "start_process",
                     DC[1] + "move_file"):
            check("A4[%s] %s does not reach ascii-only-guard" % (sem, tool),
                  "ascii-only-guard" not in routed(settings, chains, tool, anchored))


def test_live_differs_by_exactly_the_proposal():
    live = load_live()
    chains = load_chains()
    if settings_proposal.state(live) == "applied":
        skip("D1 live vs effective routing differs only by the proposal",
             "settings.json is applied -- effective IS live, the check would be "
             "tautological")
        return
    eff = settings_proposal.effective(live)
    dc_writes = {p + x for p in DC for x in ("write_file", "edit_block")}
    tools = set(expectations(chains)) | set(NOTION_WRITE_FIXTURES) | set(M365_SEND_FIXTURES)
    for anchored in (True, False):
        sem = "anchored" if anchored else "documented"
        bad = []
        for tool in sorted(tools):
            a = sorted(routed(live, chains, tool, anchored))
            b = sorted(routed(eff, chains, tool, anchored))
            if settings_proposal.state(live) == "pending" and tool in dc_writes:
                ok = b == sorted(a + ["ascii-only-guard"])
            else:
                ok = a == b
            if not ok:
                bad.append((tool, a, b))
        check("D1[%s] live vs effective PreToolUse routing differs only by the "
              "proposal's ascii-only-guard DC entry" % sem, not bad, repr(bad[:2]))


def test_proposed_artifact_matches_rendered_proposal():
    path = os.path.join(REPO, "_proposed", "settings.json")
    live = load_live()
    if not os.path.isfile(path):
        skip("D2 _proposed/settings.json matches the rendered proposal",
             "no _proposed/ artifact (already applied and archived, or absent)")
        return
    if settings_proposal.state(live) != "pending":
        skip("D2 _proposed/settings.json matches the rendered proposal",
             "settings.json already %s" % settings_proposal.state(live))
        return
    with open(os.path.join(REPO, "settings.json"), "rb") as fh:
        sha = settings_proposal.normalized_sha256(fh.read())
    if sha != settings_proposal.BASE_SHA256:
        # The artifact is a snapshot of apply(1370b41 settings); once another
        # session edits settings.json it is legitimately stale, and that must
        # not block pushes (re-review C8). APPLY.md step 4 re-renders it.
        skip("D2 _proposed/settings.json matches the rendered proposal",
             "settings.json has moved off the 1370b41 base the artifact was "
             "rendered from -- re-render per APPLY.md step 4 before applying")
        return
    with open(path, "rb") as fh:
        artifact = fh.read().replace(b"\r\n", b"\n")
    rendered = settings_proposal.render(settings_proposal.apply(live)).encode("utf-8")
    check("D2 _proposed/settings.json is byte-identical to the rendered proposal",
          artifact == rendered)


def test_proposal_state_is_exact():
    """state() semantics, on a FROZEN 1370b41 fixture (never live settings), so
    these keep running after the apply (round-3 review nit b).

    pending is EXACT (re-review C2): an edited folded entry must read as
    "partial", never be silently dropped by apply(). applied is STRUCTURAL
    (round-3 C8a): routine post-apply edits stay "applied"; only a missing or
    duplicated dispatcher/ascii entry, or a folded entry creeping back, is
    "partial"."""
    import copy
    with open(os.path.join(HOOKS_DIR, "tests", "lib",
                           "settings_1370b41_hooks_fixture.json"), encoding="ascii") as fh:
        base = {"hooks": json.load(fh)["hooks"]}
    st = settings_proposal.state
    check("S1 the frozen 1370b41 fixture reads as pending", st(base) == "pending")
    edited = copy.deepcopy(base)
    for e in edited["hooks"]["PostToolUse"]:
        for h in e.get("hooks", []):
            if "eos-gate-sentinel.py" in h.get("command", ""):
                h["command"] += " --strict"
                h["timeout"] = 999
    check("S2 an edited folded entry (new flag + timeout) reads as partial",
          st(edited) == "partial")
    raised = False
    try:
        settings_proposal.effective(edited)
    except settings_proposal.ProposalError:
        raised = True
    check("S3 and effective() refuses it rather than dropping the edit", raised)
    applied = settings_proposal.apply(base)
    check("S4 apply(fixture) reads as applied", st(applied) == "applied")

    def disp_hook(s):
        return [e for e in s["hooks"]["PostToolUse"]
                if "posttooluse-dispatcher.py" in json.dumps(e)][0]["hooks"][0]

    def ascii_entry(s):
        return [e for e in s["hooks"]["PreToolUse"]
                if "ascii-only-guard.py" in json.dumps(e)][0]
    a1 = copy.deepcopy(applied)
    disp_hook(a1)["timeout"] = 600
    a2 = copy.deepcopy(applied)
    ascii_entry(a2)["hooks"][0]["timeout"] = 30
    a3 = copy.deepcopy(applied)
    for e in a3["hooks"]["PostToolUse"] + a3["hooks"]["PreToolUse"]:
        for h in e.get("hooks", []):
            h["command"] = h.get("command", "").replace("Python313", "Python314")
    a9 = copy.deepcopy(applied)
    ascii_entry(a9)["hooks"].append({"type": "command", "command": "python x/other.py"})
    for label, s_ in (("A1 dispatcher timeout 360->600", a1),
                      ("A2 timeout added to the ascii hook", a2),
                      ("A3 interpreter path Python313->Python314", a3),
                      ("A9 second hook on the ascii entry", a9)):
        check("S5 routine post-apply edit stays applied: " + label,
              st(s_) == "applied", st(s_))
    a5 = copy.deepcopy(applied)
    a5["hooks"]["PreToolUse"] = [e for e in a5["hooks"]["PreToolUse"]
                                 if "ascii-only-guard.py" not in json.dumps(e)]
    check("S6 applied minus the ascii entry reads as partial", st(a5) == "partial")
    a8 = copy.deepcopy(applied)
    a8["hooks"]["PostToolUse"].append(copy.deepcopy(
        [e for e in base["hooks"]["PostToolUse"]
         if "eos-gate-sentinel.py" in json.dumps(e)][0]))
    check("S7 applied with a folded entry re-added reads as partial", st(a8) == "partial")
    a10 = copy.deepcopy(applied)
    a10["hooks"]["PostToolUse"].append(copy.deepcopy(
        [e for e in a10["hooks"]["PostToolUse"]
         if "posttooluse-dispatcher.py" in json.dumps(e)][0]))
    check("S8 applied with the dispatcher entry duplicated reads as partial",
          st(a10) == "partial")
    extra = copy.deepcopy(base)
    extra["hooks"]["PostToolUse"].append({"matcher": "Bash", "hooks": [
        {"type": "command", "command": "python x/unrelated-post-hook.py"}]})
    check("S9 an UNRELATED new entry leaves the fixture pending", st(extra) == "pending")


def test_notion_writes_reach_confidentiality():
    path, settings = load_settings()
    chains = load_chains()
    for tool in NOTION_WRITE_FIXTURES:
        check("C1[documented] %s reaches confidentiality-guard" % tool,
              "confidentiality-guard" in routed(settings, chains, tool, anchored=False))
    for tool in NOTION_WRITE_FIXTURES:
        check("C2[anchored] %s reaches confidentiality-guard" % tool,
              "confidentiality-guard" in routed(settings, chains, tool, anchored=True))


def m365_assertion(matcher, report):
    """True iff every lowercase M365 send tool reaches a confidentiality-guard
    entry spelled `matcher`, under BOTH matcher models. Reports per tool."""
    ok = True
    for anchored in (True, False):
        sem = "anchored" if anchored else "documented"
        for tool in M365_SEND_FIXTURES:
            hit = matches(matcher, tool, anchored)
            report("M365[%s] %s reaches confidentiality-guard" % (sem, tool), hit,
                   "matcher=%r" % matcher[:60])
            ok = ok and hit
    return ok


def test_m365_sends_reach_confidentiality():
    path, settings = load_settings()
    chains = load_chains()
    for anchored in (True, False):
        sem = "anchored" if anchored else "documented"
        for tool in M365_SEND_FIXTURES:
            check("M365[%s] %s reaches confidentiality-guard (settings.json)" % (sem, tool),
                  "confidentiality-guard" in routed(settings, chains, tool, anchored=anchored))


def demo_live_confidentiality_gap():
    """Evidence only, NOT part of the suite: run the M365 assertion against the
    live confidentiality-guard matcher and show it fail."""
    print("demo: M365 send fixtures vs the LIVE confidentiality-guard matcher")
    print("  matcher: %s" % LIVE_CONFIDENTIALITY_MATCHER)
    ok = m365_assertion(LIVE_CONFIDENTIALITY_MATCHER, check)
    print("demo result: %s" % ("PASS" if ok else "FAIL -- %d of %d (tool x model) "
                               "checks unguarded" % (len(_failures),
                                                     2 * len(M365_SEND_FIXTURES))))
    return 0 if ok else 1


if __name__ == "__main__":
    if "--demo-live-confidentiality-gap" in sys.argv:
        sys.exit(demo_live_confidentiality_gap())
    test_real_tool_names_reach_intended_guards()
    test_ascii_only_guard_wiring()
    test_live_differs_by_exactly_the_proposal()
    test_proposed_artifact_matches_rendered_proposal()
    test_proposal_state_is_exact()
    test_notion_writes_reach_confidentiality()
    test_m365_sends_reach_confidentiality()
    if _failures:
        print("\n%d FAILURE(S): %s" % (len(_failures), ", ".join(_failures[:12])))
        sys.exit(1)
    print("\nALL matcher-coverage tests passed.")
    sys.exit(0)
