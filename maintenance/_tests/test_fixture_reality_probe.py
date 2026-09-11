#!/usr/bin/env python3
"""Tests for fixture-reality-probe.py -- the guard against fixture-shaped tests
that certify dead branches (memory: feedback_fixture_shaped_tests_certify_dead_
branches.md, 2026-07-24: hooks/eos-telemetry.py matched tool name "Task" while
the harness only ever emits "Agent"; the hand-authored fixture encoded the same
wrong name, so the test passed green for months while the branch never fired).

Real files on disk -- real .py sources parsed by the real ast extractor, real
.jsonl corpora streamed by the real corpus scanner, real telemetry lines. No
mocks and no monkeypatching, same convention as test_checkout_merge_forward.py
(28/28 against real local-remote git fixtures) and test_check_branch_point.py.

Run: python _tests/test_fixture_reality_probe.py   (exit 0 = pass)
"""
import contextlib
import importlib.util
import io
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(os.path.dirname(HERE), "fixture-reality-probe.py")

_spec = importlib.util.spec_from_file_location("frp", SCRIPT)
frp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(frp)

_results = []


def check(name, cond, detail=""):
    _results.append((bool(cond), name))
    if not cond:
        print("FAIL %s  %s" % (name, detail))
    else:
        print("PASS %s" % name)


# --------------------------------------------------------------------------
# fixture builders
# --------------------------------------------------------------------------

def write(path, text):
    d = os.path.dirname(path)
    if d and not os.path.isdir(d):
        os.makedirs(d)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return path


# A dozen distinct tool names, so a synthetic corpus clears the probe's
# MIN_SLOT_VOCAB floor the same way the real corpus does. Without this the
# slot would read UNMEASURED (the probe's own thin-corpus guard) and every
# assertion below would pass for the wrong reason.
FILLER_TOOLS = {
    "Bash": 40, "Read": 35, "Edit": 30, "Write": 20, "Glob": 15,
    "Grep": 25, "TodoWrite": 10, "WebFetch": 5, "WebSearch": 4,
    "NotebookEdit": 3, "Skill": 6, "SlashCommand": 2,
}


def corpus_line(tool_name):
    """One assistant tool_use record, shaped like a real transcript line."""
    return json.dumps({
        "parentUuid": "00000000-0000-0000-0000-000000000000",
        "isSidechain": False,
        "message": {
            "model": "claude-opus-5",
            "type": "message",
            "role": "assistant",
            "content": [{
                "type": "tool_use",
                "id": "toolu_01AAAAAAAAAAAAAAAAAAAAAA",
                "name": tool_name,
                "input": {"x": 1},
            }],
        },
    })


def make_corpus(root, counts, filler=True, extra_lines=()):
    """Write a .jsonl corpus emitting each name in `counts` that many times."""
    if not os.path.isdir(root):
        os.makedirs(root)
    emit = dict(FILLER_TOOLS) if filler else {}
    emit.update(counts)
    lines = []
    for name, n in sorted(emit.items()):
        for _ in range(n):
            lines.append(corpus_line(name))
    lines.extend(extra_lines)
    sub = os.path.join(root, "C--Users-Owner-project")
    os.makedirs(sub, exist_ok=True)
    write(os.path.join(sub, "session.jsonl"), "\n".join(lines) + "\n")
    return root


def make_telemetry(path, records):
    write(path, "\n".join(json.dumps(r) for r in records) + "\n")
    return path


def run_probe(code_root=None, test_root=None, corpus=None, telemetry=None,
              extra=()):
    """Invoke the probe exactly as a caller would; return (rc, report)."""
    argv = ["--json"]
    if code_root is not None:
        argv.append("--code-roots=" + code_root)
    if test_root is not None:
        argv.append("--test-roots=" + test_root)
    if corpus is not None:
        argv.append("--corpus=" + corpus)
    if telemetry is not None:
        argv.append("--telemetry=" + telemetry)
    argv.extend(extra)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = frp.main(argv)
    raw = buf.getvalue()
    try:
        report = json.loads(raw)
    except ValueError:
        report = {"_unparseable": raw}
    return rc, report


def findings_for(report, literal):
    return [f for f in report.get("findings", []) if f.get("literal") == literal]


def confirmed(report):
    return [f for f in report.get("findings", [])
            if f.get("confidence") == "CONFIRMED"]


# An "empty" pair of roots that exist but hold nothing, so a test exercising
# only the telemetry leg is not also asserting on stray code findings.
def empty_roots(td):
    code = os.path.join(td, "nocode")
    tests = os.path.join(td, "notests")
    os.makedirs(code)
    os.makedirs(tests)
    return code, tests


# --------------------------------------------------------------------------
# 1. code+test pair agreeing on a literal the corpus never emitted
# --------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as td:
    code = os.path.join(td, "hooks")
    tests = os.path.join(td, "hooks", "tests")
    write(os.path.join(code, "counter.py"),
          "def handle(payload):\n"
          "    tool_name = payload.get('tool_name')\n"
          "    if tool_name == \"Phantom\":\n"
          "        return 'dispatched'\n"
          "    return None\n")
    write(os.path.join(tests, "test-counter.py"),
          "EVENT = {\"hook_event_name\": \"PostToolUse\", "
          "\"tool_name\": \"Phantom\"}\n"
          "def test_dispatch():\n"
          "    assert handle(EVENT) == 'dispatched'\n")
    corpus = make_corpus(os.path.join(td, "projects"), {})
    rc, rep = run_probe(code, tests, corpus)
    hits = findings_for(rep, "Phantom")
    check("1 code+test pair on an absent literal is CONFIRMED",
          hits and hits[0].get("confidence") == "CONFIRMED",
          "findings=%r" % rep.get("findings"))
    check("1 CONFIRMED finding exits 1", rc == 1, "rc=%r" % rc)
    check("1 finding names the asserting code file+line",
          hits and any(s.get("file", "").endswith("counter.py") and s.get("line") == 3
                       for s in hits[0].get("code", [])),
          "code=%r" % (hits[0].get("code") if hits else None))
    check("1 finding names the fixture that agrees with it",
          hits and any(s.get("file", "").endswith("test-counter.py")
                       for s in hits[0].get("fixtures", [])),
          "fixtures=%r" % (hits[0].get("fixtures") if hits else None))

# --------------------------------------------------------------------------
# 2. a literal that DOES occur in the corpus is never flagged
# --------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as td:
    code = os.path.join(td, "hooks")
    tests = os.path.join(td, "hooks", "tests")
    write(os.path.join(code, "counter.py"),
          "def handle(payload):\n"
          "    tool_name = payload.get('tool_name')\n"
          "    if tool_name == \"Bash\":\n"
          "        return 'ran'\n")
    write(os.path.join(tests, "test-counter.py"),
          "EVENT = {\"tool_name\": \"Bash\"}\n")
    corpus = make_corpus(os.path.join(td, "projects"), {})
    rc, rep = run_probe(code, tests, corpus)
    check("2 present literal not flagged", not findings_for(rep, "Bash"),
          "findings=%r" % rep.get("findings"))
    check("2 no CONFIRMED finding exits 0", rc == 0, "rc=%r" % rc)

# --------------------------------------------------------------------------
# 3. matching is EXACT -- never prefix, never substring
#    (memory: TaskCreate/TaskUpdate/TaskList/TaskGet/TaskOutput/TaskStop are
#     todo tools, not dispatch; widening "Task" to match them is the exact
#     mistake the founding incident's write-up warns against)
# --------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as td:
    code = os.path.join(td, "hooks")
    tests = os.path.join(td, "hooks", "tests")
    write(os.path.join(code, "counter.py"),
          "def handle(t):\n"
          "    tool_name = t\n"
          "    if tool_name == \"Task\":\n"
          "        return 'a'\n"
          "    if tool_name == \"TaskCreate\":\n"
          "        return 'b'\n")
    write(os.path.join(tests, "test-counter.py"), "EVENT = {}\n")
    corpus = make_corpus(os.path.join(td, "projects"),
                         {"TaskCreate": 12, "TaskUpdate": 9, "TaskStop": 4})
    rc, rep = run_probe(code, tests, corpus)
    check("3a exact hit not flagged (TaskCreate occurs)",
          not findings_for(rep, "TaskCreate"),
          "findings=%r" % rep.get("findings"))
    check("3b prefix of a present name is still absent (Task flagged)",
          bool(findings_for(rep, "Task")),
          "findings=%r" % rep.get("findings"))
    hits = findings_for(rep, "Task")
    check("3c near-miss siblings are advisory only, not a suppression",
          hits and hits[0].get("confidence") != "SUPPRESSED"
          and "TaskCreate" in (hits[0].get("near_misses") or []),
          "finding=%r" % (hits[0] if hits else None))
    check("3d no fixture agreeing -> not CONFIRMED -> exit 0",
          rc == 0 and not confirmed(rep), "rc=%r" % rc)

# --------------------------------------------------------------------------
# 4/5/6. the 0%/100% tell -- a perfectly absolute boolean signal is a
#        suspected broken emitter, not a behavior finding
# --------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as td:
    code, tests = empty_roots(td)
    corpus = make_corpus(os.path.join(td, "projects"), {})
    tel = os.path.join(td, "lane-telemetry.jsonl")
    recs = []
    for i in range(120):
        recs.append({
            "session_id": "s%d" % i,
            "dead_signal": False,                 # exactly 0.0%
            "always_signal": True,                # exactly 100.0%
            "mixed_signal": (i % 4 == 0),         # 25.0%
        })
    make_telemetry(tel, recs)
    rc, rep = run_probe(code, tests, corpus, telemetry=tel)
    sigs = {s["signal"]: s for s in rep.get("telemetry", {}).get("signals", [])}
    check("4 boolean signal at exactly 0.0%% is flagged",
          sigs.get("dead_signal", {}).get("flagged") is True, "sigs=%r" % sigs)
    check("5 boolean signal at exactly 100.0%% is flagged",
          sigs.get("always_signal", {}).get("flagged") is True, "sigs=%r" % sigs)
    check("6 intermediate signal is not flagged",
          sigs.get("mixed_signal", {}).get("flagged") is False, "sigs=%r" % sigs)
    check("6b a suspected emitter is report-only, never a non-zero exit",
          rc == 0, "rc=%r" % rc)

with tempfile.TemporaryDirectory() as td:
    code, tests = empty_roots(td)
    corpus = make_corpus(os.path.join(td, "projects"), {})
    tel = os.path.join(td, "lane-telemetry.jsonl")
    make_telemetry(tel, [{"session_id": "s%d" % i, "dead_signal": False}
                         for i in range(5)])
    rc, rep = run_probe(code, tests, corpus, telemetry=tel)
    sigs = {s["signal"]: s for s in rep.get("telemetry", {}).get("signals", [])}
    check("6c 0.0%% over too small a sample is NOT flagged",
          sigs.get("dead_signal", {}).get("flagged") is False, "sigs=%r" % sigs)

# --------------------------------------------------------------------------
# 7. missing / unreadable corpus -> exit 0 with a stated caveat (fail open)
# --------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as td:
    code = os.path.join(td, "hooks")
    tests = os.path.join(td, "hooks", "tests")
    write(os.path.join(code, "counter.py"),
          "def handle(t):\n"
          "    tool_name = t\n"
          "    if tool_name == \"Phantom\":\n"
          "        return 'x'\n")
    write(os.path.join(tests, "test-counter.py"),
          "EVENT = {\"tool_name\": \"Phantom\"}\n")
    missing = os.path.join(td, "does-not-exist")
    rc, rep = run_probe(code, tests, missing)
    check("7 missing corpus exits 0", rc == 0, "rc=%r" % rc)
    check("7 missing corpus states a caveat",
          any("corpus" in c.lower() for c in rep.get("caveats", [])),
          "caveats=%r" % rep.get("caveats"))
    check("7 missing corpus asserts nothing (no findings)",
          not rep.get("findings"), "findings=%r" % rep.get("findings"))
    check("7 report marks the corpus unmeasured",
          rep.get("corpus", {}).get("measured") is False,
          "corpus=%r" % rep.get("corpus"))

# --------------------------------------------------------------------------
# 8. malformed JSONL -> skipped, counted, never a crash
# --------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as td:
    code = os.path.join(td, "hooks")
    tests = os.path.join(td, "hooks", "tests")
    write(os.path.join(code, "counter.py"),
          "def handle(t):\n"
          "    tool_name = t\n"
          "    if tool_name == \"Bash\":\n"
          "        return 'x'\n")
    write(os.path.join(tests, "test-counter.py"), "EVENT = {}\n")
    corpus = make_corpus(
        os.path.join(td, "projects"), {},
        extra_lines=["{not json at all", "", "   ", "[1,2,3]", "null",
                     '{"message": {"content": "a string not a list"}}'])
    ok = True
    detail = ""
    try:
        rc, rep = run_probe(code, tests, corpus)
    except Exception as exc:                      # noqa: BLE001 -- the point
        ok, rc, rep, detail = False, None, {}, repr(exc)
    check("8 malformed JSONL does not crash the probe", ok, detail)
    check("8 malformed JSONL still exits 0", rc == 0, "rc=%r" % rc)
    check("8 good lines in the same file are still measured",
          rep.get("corpus", {}).get("measured") is True
          and not findings_for(rep, "Bash"),
          "corpus=%r findings=%r" % (rep.get("corpus"), rep.get("findings")))

# --------------------------------------------------------------------------
# 9. END-TO-END REGRESSION against the REAL historical bug (2026-07-24).
#    hooks/eos-telemetry.py counted subagent dispatch with tname == "Task";
#    hooks/tests/test-eos-telemetry.py built its fixture with "Task" and
#    asserted task_dispatched is True. Reality emits "Agent" -- 672 times
#    across the local transcripts, "Task" zero times. If the probe cannot
#    catch its own founding incident it is not worth landing.
# --------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as td:
    code = os.path.join(td, "hooks")
    tests = os.path.join(td, "hooks", "tests")
    write(os.path.join(code, "eos-telemetry.py"),
          "import json, sys\n"
          "\n"
          "def record(payload, state):\n"
          "    tname = payload.get(\"tool_name\") or \"\"\n"
          "    if tname == \"Task\":\n"
          "        state[\"task_dispatched\"] = True\n"
          "    if tname == \"Bash\":\n"
          "        state[\"bash_test_ran\"] = True\n"
          "    return state\n")
    write(os.path.join(tests, "test-eos-telemetry.py"),
          "EVENT = {\n"
          "    \"hook_event_name\": \"PostToolUse\",\n"
          "    \"tool_name\": \"Task\",\n"
          "    \"tool_input\": {},\n"
          "}\n"
          "\n"
          "def test_task_dispatched():\n"
          "    state = record(EVENT, {})\n"
          "    assert state[\"task_dispatched\"] is True\n")
    corpus = make_corpus(os.path.join(td, "projects"), {"Agent": 672})
    rc, rep = run_probe(code, tests, corpus)
    hits = findings_for(rep, "Task")
    check("9 founding incident is caught", bool(hits),
          "findings=%r" % rep.get("findings"))
    check("9 founding incident is CONFIRMED (code and fixture agree)",
          hits and hits[0].get("confidence") == "CONFIRMED",
          "finding=%r" % (hits[0] if hits else None))
    check("9 founding incident exits non-zero", rc == 1, "rc=%r" % rc)
    top = dict(hits[0].get("observed_slot_top") or []) if hits else {}
    check("9 report surfaces what the slot really emits (Agent x672)",
          top.get("Agent") == 672, "observed_slot_top=%r" % (top or None))
    check("9 the live sibling branch (Bash) is NOT flagged",
          not findings_for(rep, "Bash"), "findings=%r" % rep.get("findings"))
    check("9 the fixture's own event name is not a false finding",
          not findings_for(rep, "PostToolUse"),
          "findings=%r" % rep.get("findings"))

# --------------------------------------------------------------------------
# 10. false-positive guards that must hold, or the probe is unusable
# --------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as td:
    code = os.path.join(td, "hooks")
    tests = os.path.join(td, "hooks", "tests")
    # thin corpus: a slot the corpus cannot speak to must read UNMEASURED,
    # never "absent". Two distinct names is not a vocabulary.
    write(os.path.join(code, "counter.py"),
          "def handle(t):\n"
          "    tool_name = t\n"
          "    if tool_name == \"Phantom\":\n"
          "        return 'x'\n")
    write(os.path.join(tests, "test-counter.py"),
          "EVENT = {\"tool_name\": \"Phantom\"}\n")
    corpus = make_corpus(os.path.join(td, "projects"), {"Bash": 3},
                         filler=False)
    rc, rep = run_probe(code, tests, corpus)
    check("10a thin slot vocabulary suppresses the finding",
          not findings_for(rep, "Phantom") and rc == 0,
          "rc=%r findings=%r" % (rc, rep.get("findings")))
    check("10a thin slot is disclosed as a caveat, not silently dropped",
          any("unmeasured" in c.lower() or "thin" in c.lower()
              for c in rep.get("caveats", [])),
          "caveats=%r" % rep.get("caveats"))

with tempfile.TemporaryDirectory() as td:
    code = os.path.join(td, "hooks")
    tests = os.path.join(td, "hooks", "tests")
    write(os.path.join(code, "counter.py"),
          "def handle(t):\n"
          "    tool_name = t\n"
          "    # fixture-reality-probe: expected-absent deprecated pre-2026 name\n"
          "    if tool_name == \"Phantom\":\n"
          "        return 'x'\n")
    write(os.path.join(tests, "test-counter.py"),
          "EVENT = {\"tool_name\": \"Phantom\"}\n")
    corpus = make_corpus(os.path.join(td, "projects"), {})
    rc, rep = run_probe(code, tests, corpus)
    check("10b an explicit expected-absent marker suppresses with a reason",
          not findings_for(rep, "Phantom") and rc == 0
          and any("Phantom" in s.get("literal", "")
                  for s in rep.get("suppressed", [])),
          "rc=%r suppressed=%r" % (rc, rep.get("suppressed")))

with tempfile.TemporaryDirectory() as td:
    code = os.path.join(td, "hooks")
    tests = os.path.join(td, "hooks", "tests")
    # startswith() is a prefix predicate BY DESIGN -- extracting its argument
    # as an exact name would flag every legitimate prefix match.
    write(os.path.join(code, "counter.py"),
          "def handle(t):\n"
          "    tool_name = t\n"
          "    if tool_name.startswith(\"mcp__ora\"):\n"
          "        return 'x'\n")
    write(os.path.join(tests, "test-counter.py"), "EVENT = {}\n")
    corpus = make_corpus(os.path.join(td, "projects"), {})
    rc, rep = run_probe(code, tests, corpus)
    check("10c startswith() arguments are never extracted as exact names",
          not findings_for(rep, "mcp__ora") and rc == 0,
          "findings=%r" % rep.get("findings"))

with tempfile.TemporaryDirectory() as td:
    code = os.path.join(td, "hooks")
    tests = os.path.join(td, "hooks", "tests")
    # membership in a name set, including one bound to a module constant
    write(os.path.join(code, "counter.py"),
          "WRITE_TOOLS = {\"Edit\", \"Write\", \"Phantom\"}\n"
          "\n"
          "def handle(t):\n"
          "    tool_name = t\n"
          "    if tool_name in WRITE_TOOLS:\n"
          "        return 'x'\n"
          "    if tool_name in (\"Read\", \"Ghost\"):\n"
          "        return 'y'\n")
    write(os.path.join(tests, "test-counter.py"), "EVENT = {}\n")
    corpus = make_corpus(os.path.join(td, "projects"), {})
    rc, rep = run_probe(code, tests, corpus)
    check("10d membership in a module-level name set is extracted",
          bool(findings_for(rep, "Phantom")),
          "findings=%r" % rep.get("findings"))
    check("10d membership in an inline tuple is extracted",
          bool(findings_for(rep, "Ghost")),
          "findings=%r" % rep.get("findings"))
    check("10d live members of the same set are not flagged",
          not findings_for(rep, "Edit") and not findings_for(rep, "Read"),
          "findings=%r" % rep.get("findings"))
    hits = findings_for(rep, "Phantom")
    check("10d a dead member beside live siblings ranks HIGH",
          hits and hits[0].get("confidence") == "HIGH",
          "finding=%r" % (hits[0] if hits else None))

with tempfile.TemporaryDirectory() as td:
    code, tests = empty_roots(td)
    corpus = make_corpus(os.path.join(td, "projects"), {})
    tel = os.path.join(td, "lane-telemetry.jsonl")
    write(tel, "{broken\n" + json.dumps(
        {"session_id": "a", "s": False}) + "\n")
    rc, rep = run_probe(code, tests, corpus, telemetry=tel)
    check("10e malformed telemetry lines do not crash the probe", rc == 0,
          "rc=%r" % rc)
    rc, rep = run_probe(code, tests, corpus,
                        telemetry=os.path.join(td, "no-such-telemetry.jsonl"))
    check("10f missing telemetry file is a caveat, not a failure",
          rc == 0 and any("telemetry" in c.lower()
                          for c in rep.get("caveats", [])),
          "rc=%r caveats=%r" % (rc, rep.get("caveats")))

with tempfile.TemporaryDirectory() as td:
    code = os.path.join(td, "hooks")
    tests = os.path.join(td, "hooks", "tests")
    write(os.path.join(code, "broken.py"), "def handle(:\n    pass\n")
    write(os.path.join(code, "counter.py"),
          "def handle(t):\n"
          "    tool_name = t\n"
          "    if tool_name == \"Bash\":\n"
          "        return 'x'\n")
    write(os.path.join(tests, "test-counter.py"), "EVENT = {}\n")
    corpus = make_corpus(os.path.join(td, "projects"), {})
    rc, rep = run_probe(code, tests, corpus)
    check("10g an unparseable source file is a caveat, not a crash",
          rc == 0 and any("broken.py" in c for c in rep.get("caveats", [])),
          "rc=%r caveats=%r" % (rc, rep.get("caveats")))

# --------------------------------------------------------------------------
# 12. the generic "name" slot is NOT assertable from code.
#     `name` is the most overloaded key in this repo -- git refs, file names,
#     scheduled-task ids, skill names -- while the corpus's "name" vocabulary
#     is only the tool/agent/MCP name space. Asserting one against the other
#     produced 7 false positives on the first live run (HEAD, MEMORY.md,
#     SKILL.md, event_log.md, open-items-tracker.md, ora-mcp-liveness-probe,
#     project_*.md). Precision over recall, as in the sibling probes.
# --------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as td:
    code = os.path.join(td, "hooks")
    tests = os.path.join(td, "hooks", "tests")
    write(os.path.join(code, "probe.py"),
          "def check(sized):\n"
          "    for name, n in sized:\n"
          "        if name == \"MEMORY.md\":\n"
          "            return n\n"
          "        if name == \"HEAD\":\n"
          "            return 0\n")
    write(os.path.join(tests, "test-probe.py"), "EVENT = {}\n")
    corpus = make_corpus(os.path.join(td, "projects"), {})
    rc, rep = run_probe(code, tests, corpus)
    check("12a a filename compared against a generic `name` var is not flagged",
          not findings_for(rep, "MEMORY.md") and not findings_for(rep, "HEAD"),
          "findings=%r" % rep.get("findings"))
    check("12a the unassertable generic slot is disclosed as a caveat",
          any("generic" in c.lower() and "name" in c.lower()
              for c in rep.get("caveats", [])),
          "caveats=%r" % rep.get("caveats"))

with tempfile.TemporaryDirectory() as td:
    # The founding incident's fixture keyed the tool name as "name", not
    # "tool_name" (memory: 'built its fixture with "name": "Task"'). A fixture
    # in the generic slot must still confirm a tool-slot code predicate --
    # narrowing the CODE side must not narrow the FIXTURE side.
    code = os.path.join(td, "hooks")
    tests = os.path.join(td, "hooks", "tests")
    write(os.path.join(code, "eos-telemetry.py"),
          "def record(payload, state):\n"
          "    tname = payload.get(\"tool_name\") or \"\"\n"
          "    if tname == \"Task\":\n"
          "        state[\"task_dispatched\"] = True\n"
          "    return state\n")
    write(os.path.join(tests, "test-eos-telemetry.py"),
          "TOOL_USE = {\"type\": \"tool_use\", \"name\": \"Task\", "
          "\"input\": {}}\n")
    corpus = make_corpus(os.path.join(td, "projects"), {"Agent": 672})
    rc, rep = run_probe(code, tests, corpus)
    hits = findings_for(rep, "Task")
    check("12b a fixture keyed \"name\" still confirms a tool-slot predicate",
          rc == 1 and hits and hits[0].get("confidence") == "CONFIRMED",
          "rc=%r finding=%r" % (rc, hits[0] if hits else None))

# --------------------------------------------------------------------------
# 13. the shipped ALLOWLIST really suppresses, with its reason on record
#     (exercised against the real table, not a monkeypatched one)
# --------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as td:
    code = os.path.join(td, "hooks")
    tests = os.path.join(td, "hooks", "tests")
    allowed = sorted(frp.ALLOWLIST) or [None]
    lit = allowed[0]
    write(os.path.join(code, "guard.py"),
          "EDIT_TOOLS = (\"Edit\", \"Write\", \"%s\")\n"
          "\n"
          "def handle(t):\n"
          "    tool_name = t\n"
          "    if tool_name in EDIT_TOOLS:\n"
          "        return 'x'\n" % lit)
    write(os.path.join(tests, "test-guard.py"),
          "EVENT = {\"tool_name\": \"%s\"}\n" % lit)
    corpus = make_corpus(os.path.join(td, "projects"), {})
    rc, rep = run_probe(code, tests, corpus)
    check("13 allowlisted literal is suppressed, not CONFIRMED",
          bool(lit) and rc == 0 and not findings_for(rep, lit),
          "literal=%r rc=%r findings=%r" % (lit, rc, rep.get("findings")))
    check("13 suppression carries the allowlist reason",
          any(s.get("literal") == lit and "allowlist" in s.get("reason", "")
              for s in rep.get("suppressed", [])),
          "suppressed=%r" % rep.get("suppressed"))

# --------------------------------------------------------------------------
# 11. report-only: the probe must never write to the trees it scans
# --------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as td:
    code = os.path.join(td, "hooks")
    tests = os.path.join(td, "hooks", "tests")
    write(os.path.join(code, "counter.py"),
          "def handle(t):\n"
          "    tool_name = t\n"
          "    if tool_name == \"Phantom\":\n"
          "        return 'x'\n")
    write(os.path.join(tests, "test-counter.py"),
          "EVENT = {\"tool_name\": \"Phantom\"}\n")
    corpus = make_corpus(os.path.join(td, "projects"), {})

    def snapshot(root):
        out = {}
        for dirpath, _dirs, files in os.walk(root):
            for f in files:
                p = os.path.join(dirpath, f)
                with open(p, "rb") as fh:
                    out[os.path.relpath(p, root)] = fh.read()
        return out

    before = snapshot(td)
    run_probe(code, tests, corpus)
    after = snapshot(td)
    check("11 probe is report-only (scanned trees byte-identical after run)",
          before == after,
          "changed=%r" % sorted(set(before) ^ set(after)))

passed = sum(1 for ok, _ in _results if ok)
print("\nfixture-reality-probe tests: %d/%d passed" % (passed, len(_results)))
sys.exit(0 if passed == len(_results) else 1)
