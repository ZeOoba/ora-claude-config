#!/usr/bin/env python3
"""Tests for dangling-mutation-probe.py.

Covers the pure classification functions: is_mutating(), find_dangling(),
classify_findings(), parse_model_tag(), and uncollected_observations().
Nothing here touches the live registry, session store, or transcript tree --
every input is an in-memory fixture, so the suite is safe to run anywhere.

The fixtures encode REAL shapes taken from the 2026-08-03 forensic scan of
186 scheduled-task transcripts, not invented ones. In particular the
rows_after values (0 vs >0) and the specific tool names below are the actual
historical distribution -- see the docstring in dangling-mutation-probe.py.

Run: python test-dangling-mutation-probe.py   (exit 0 = all pass)
"""
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "dmp", os.path.join(HERE, "dangling-mutation-probe.py"))
dmp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dmp)

results = []


def expect(label, cond, detail=""):
    results.append((bool(cond), label))
    if not cond:
        print("  FAIL: %s %s" % (label, detail))


def _asst(tool_id, name, tool_input=None):
    return {"type": "assistant", "message": {"content": [
        {"type": "tool_use", "id": tool_id, "name": name,
         "input": tool_input or {}}]}}


def _result(tool_id):
    return {"type": "user", "message": {"content": [
        {"type": "tool_result", "tool_use_id": tool_id, "content": "ok"}]}}


def _text():
    return {"type": "assistant", "message": {"content": [
        {"type": "text", "text": "done"}]}}


# --- is_mutating: explicit tool-name patterns ------------------------------------------
expect("is_mutating: update_scheduled_task is a mutation",
       dmp.is_mutating("mcp__scheduled-tasks__update_scheduled_task", {}))
expect("is_mutating: create_scheduled_task is a mutation",
       dmp.is_mutating("mcp__scheduled-tasks__create_scheduled_task", {}))
expect("is_mutating: archive_session is a mutation",
       dmp.is_mutating("mcp__ccd_session_mgmt__archive_session", {}))
expect("is_mutating: notion-update-page is a mutation",
       dmp.is_mutating("mcp__abc__notion-update-page", {}))
expect("is_mutating: Write is a mutation", dmp.is_mutating("Write", {}))
expect("is_mutating: Edit is a mutation", dmp.is_mutating("Edit", {}))

# Reads must NOT be mutations -- these are the 7 historical false-positive candidates.
expect("is_mutating: Read is not a mutation", not dmp.is_mutating("Read", {}))
expect("is_mutating: list_scheduled_tasks is not a mutation (substring trap)",
       not dmp.is_mutating("mcp__scheduled-tasks__list_scheduled_tasks", {}))
expect("is_mutating: search_crm_objects is not a mutation",
       not dmp.is_mutating("mcp__abc__search_crm_objects", {}))
expect("is_mutating: browser computer is not a mutation",
       not dmp.is_mutating("mcp__Claude_Browser__computer", {"action": "screenshot"}))
expect("is_mutating: tabs_context is not a mutation",
       not dmp.is_mutating("mcp__claude-in-chrome__tabs_context_mcp", {}))
expect("is_mutating: Agent dispatch is not itself a mutation",
       not dmp.is_mutating("Agent", {"subagent_type": "general-purpose"}))
expect("is_mutating: AskUserQuestion is not a mutation",
       not dmp.is_mutating("AskUserQuestion", {}))

# --- is_mutating: Bash is opaque, classified by command content ------------------------
expect("is_mutating: Bash git add is a mutation",
       dmp.is_mutating("Bash", {"command": 'cd "C:/x" && git add memory/MEMORY.md'}))
expect("is_mutating: Bash git commit is a mutation",
       dmp.is_mutating("Bash", {"command": "git commit -m 'x'"}))
expect("is_mutating: Bash git push is a mutation",
       dmp.is_mutating("Bash", {"command": "git push origin main"}))
expect("is_mutating: Bash send-via-outlook is a mutation",
       dmp.is_mutating("Bash", {"command": "powershell -File _shared/send-via-outlook.ps1"}))
expect("is_mutating: Bash rm is a mutation",
       dmp.is_mutating("Bash", {"command": "rm -f /tmp/x"}))
expect("is_mutating: Bash redirect-write is a mutation",
       dmp.is_mutating("Bash", {"command": "echo hi > out.txt"}))
# The real am-brief rows_after=0 dangling Bash was a curl READ -- must stay clean,
# otherwise the probe emits a false alarm on every dangling shell read.
expect("is_mutating: Bash curl read is NOT a mutation",
       not dmp.is_mutating("Bash", {"command": 'U="https://gis.example/query"\ncurl -s --max-time 90 -H "UA: x"'}))
expect("is_mutating: Bash npm run lint is NOT a mutation",
       not dmp.is_mutating("Bash", {"command": "cd /c/x && npm run lint 2>&1 | tail -25"}))
expect("is_mutating: Bash ls is NOT a mutation",
       not dmp.is_mutating("Bash", {"command": "ls -la /c/x | head"}))
expect("is_mutating: Bash >= comparison is not a redirect-write (regression)",
       not dmp.is_mutating("Bash", {"command": "python -c 'print(1 >= 2)'"}))
# REFUTE pass 2026-08-03: arrows are everywhere in read-only format strings and
# comments; matching them promotes a dangling shell READ into a LOST_WRITE alarm.
expect("is_mutating: Bash '->' arrow is not a redirect-write",
       not dmp.is_mutating("Bash", {"command": 'git log --format="%h -> %s" | head'}))
expect("is_mutating: Bash '=>' arrow is not a redirect-write",
       not dmp.is_mutating("Bash", {"command": "echo 'a => b' | grep a"}))
expect("is_mutating: Bash '2>&1' stderr dup alone is not a write",
       not dmp.is_mutating("Bash", {"command": "pytest -q 2>&1 | tail -5"}))
expect("is_mutating: Bash '>>' append IS a write",
       dmp.is_mutating("Bash", {"command": "echo x >> log.txt"}))

# --- find_dangling ---------------------------------------------------------------------
rows = [_asst("t1", "Read"), _result("t1"), _asst("t2", "Write"), _result("t2"), _text()]
expect("find_dangling: fully-resolved transcript yields nothing",
       dmp.find_dangling(rows) == [])

rows = [_asst("t1", "Read"), _result("t1"),
        _asst("t2", "mcp__scheduled-tasks__update_scheduled_task", {"taskId": "x"})]
d = dmp.find_dangling(rows)
expect("find_dangling: finds the unresolved call", len(d) == 1)
expect("find_dangling: reports correct tool name",
       d and d[0]["name"] == "mcp__scheduled-tasks__update_scheduled_task")
expect("find_dangling: rows_after==0 when call is the final row",
       d and d[0]["rows_after"] == 0)

rows = [_asst("t1", "Write"), _text(), _text(), _text()]
d = dmp.find_dangling(rows)
expect("find_dangling: rows_after counts trailing rows", d and d[0]["rows_after"] == 3)

# Multiple tool_use blocks in ONE assistant message (parallel tool calls) must each
# be tracked independently -- a single-block assumption would miss the second.
rows = [{"type": "assistant", "message": {"content": [
            {"type": "tool_use", "id": "a", "name": "Read", "input": {}},
            {"type": "tool_use", "id": "b", "name": "Write", "input": {}}]}},
        _result("a")]
d = dmp.find_dangling(rows)
expect("find_dangling: handles parallel tool_use blocks", len(d) == 1 and d[0]["id"] == "b")

expect("find_dangling: empty transcript is safe", dmp.find_dangling([]) == [])
expect("find_dangling: malformed rows are skipped, not raised",
       dmp.find_dangling([{"type": "assistant"}, {"type": "user", "message": None}]) == [])

# --- classify_findings -----------------------------------------------------------------
# The canonical incident: mutating + rows_after 0 + not live  => ALARM
sess = {"task_id": "ora-appsec-siteexposure-canary-recheck", "session_id": "local_27ea",
        "dangling": [{"name": "mcp__scheduled-tasks__update_scheduled_task",
                      "input": {"taskId": "ora-site-exposure-probe"}, "rows_after": 0}]}
al, info = dmp.classify_findings([sess], live_session_ids=set())
expect("classify: lost mutating write at end of session ALARMS", len(al) == 1)
expect("classify: alarm names the task", al and al[0]["task_id"].endswith("canary-recheck"))

# The live session always has a dangling final call (the call doing the scanning).
# Without this exclusion the probe self-flags on every single run.
al, info = dmp.classify_findings([dict(sess, session_id="local_live")],
                                 live_session_ids={"local_live"})
expect("classify: currently-running session is excluded (no self-flag)", len(al) == 0)

# Session continued past the call => it had opportunity to recover => INFO, not alarm.
cont = {"task_id": "ora-open-sessions-board", "session_id": "local_x",
        "dangling": [{"name": "mcp__ccd_session_mgmt__archive_session",
                      "input": {}, "rows_after": 12}]}
al, info = dmp.classify_findings([cont], live_session_ids=set())
expect("classify: mutating call with rows_after>0 is INFO, not alarm",
       len(al) == 0 and len(info) == 1)

# A dangling READ at end of session is not a lost write.
readend = {"task_id": "ora-lease-snapshot-refresh", "session_id": "local_y",
           "dangling": [{"name": "Read", "input": {}, "rows_after": 0}]}
al, info = dmp.classify_findings([readend], live_session_ids=set())
expect("classify: dangling read at session end does not alarm", len(al) == 0)

expect("classify: no sessions -> no findings",
       dmp.classify_findings([], live_session_ids=set()) == ([], []))

# Acknowledged findings downgrade to info -- otherwise a correctly-reported,
# since-remediated incident re-alarms daily until it ages out of the lookback.
al, info = dmp.classify_findings([sess], live_session_ids=set(),
                                 acknowledged={"local_27ea"})
expect("classify: acknowledged lost write downgrades to info",
       len(al) == 0 and len(info) == 1)
expect("classify: acknowledgement is recorded as the reason",
       info and "acknowledged" in info[0]["why_not_alarm"])
expect("classify: acknowledging a DIFFERENT session does not suppress",
       len(dmp.classify_findings([sess], set(), acknowledged={"other"})[0]) == 1)

# --- load_acknowledged -----------------------------------------------------------------
import json as _json
import tempfile as _tf
with _tf.TemporaryDirectory() as _d:
    _p = os.path.join(_d, "ack.json")
    with open(_p, "w", encoding="utf-8") as _f:
        _json.dump([{"session_id": "local_a", "reason": "fixed"},
                    {"reason": "no session id -- ignored"}], _f)
    expect("load_acknowledged: reads session ids", dmp.load_acknowledged(_p) == {"local_a"})
    expect("load_acknowledged: missing file fails OPEN (never suppresses)",
           dmp.load_acknowledged(os.path.join(_d, "nope.json")) == set())
    _bad = os.path.join(_d, "bad.json")
    with open(_bad, "w", encoding="utf-8") as _f:
        _f.write("{not json")
    expect("load_acknowledged: malformed file fails OPEN",
           dmp.load_acknowledged(_bad) == set())

# --- parse_model_tag -------------------------------------------------------------------
expect("parse_model_tag: reads id and date",
       dmp.parse_model_tag("blah [MODEL: claude-opus-5 observed | checked 2026-08-03 via canary]")
       == ("claude-opus-5 observed", "2026-08-03"))
expect("parse_model_tag: accepts the 'set' verb",
       dmp.parse_model_tag("x [MODEL: claude-sonnet-5 | set 2026-07-24]")
       == ("claude-sonnet-5", "2026-07-24"))
# STEP 2.5's hardening rule: take the LAST bracketed MODEL match, because
# descriptions carry changelogs that may quote an earlier example tag.
expect("parse_model_tag: takes the LAST tag, not the first",
       dmp.parse_model_tag("v1 [MODEL: old-id | checked 2026-01-01] v2 [MODEL: new-id | checked 2026-08-03]")
       == ("new-id", "2026-08-03"))
expect("parse_model_tag: undated tag yields no date",
       dmp.parse_model_tag("x [MODEL: claude-sonnet-5]") == ("claude-sonnet-5", None))
expect("parse_model_tag: absent tag -> None", dmp.parse_model_tag("no tag here") is None)
expect("parse_model_tag: empty description -> None", dmp.parse_model_tag("") is None)
expect("parse_model_tag: None description -> None", dmp.parse_model_tag(None) is None)

# --- _to_datetime / _as_date: the epoch-vs-ISO split ------------------------------------
# Regression: session metadata stores epoch MILLISECONDS while the registry stores
# ISO-8601 strings. Handling only ISO does not error -- it returns None and silently
# disables the lookback filter and live-session exclusion (observed on the first live
# run, 2026-08-03: lookback degraded to all-history, live_excluded stuck at 0).
expect("_to_datetime: epoch ms int (real createdAt value)",
       dmp._to_datetime(1785351608517) is not None)
expect("_to_datetime: epoch ms decodes to the correct UTC date",
       dmp._as_date(1785351608517) == "2026-07-29",
       dmp._as_date(1785351608517))
expect("_to_datetime: epoch seconds also supported",
       dmp._as_date(1785351608) == "2026-07-29", dmp._as_date(1785351608))
expect("_to_datetime: ISO-Z string (real registry lastRunAt value)",
       dmp._as_date("2026-08-03T15:29:29.926Z") == "2026-08-03")
expect("_to_datetime: ISO without fractional seconds",
       dmp._as_date("2026-08-03T15:29:29") == "2026-08-03")
expect("_to_datetime: bare date string", dmp._as_date("2026-08-03") == "2026-08-03")
expect("_to_datetime: None -> None", dmp._to_datetime(None) is None)
expect("_to_datetime: garbage string -> None", dmp._to_datetime("not-a-date") is None)
expect("_to_datetime: bool is not a timestamp", dmp._to_datetime(True) is None)
expect("_to_datetime: zero/negative epoch -> None",
       dmp._to_datetime(0) is None and dmp._to_datetime(-5) is None)

# --- uncollected_observations ----------------------------------------------------------
ANCHOR = "2026-07-26"
# The 07-29 case: real id, tag predates anchor, fired after anchor, >=7d ago => flag.
tasks = [{"id": "ora-site-exposure-probe", "enabled": True, "cronExpression": "50 9 * * 3",
          "description": "x [MODEL: claude-opus-4-8 | checked 2026-07-22]",
          "lastRunAt": "2026-07-29T14:13:48.405Z"}]
out = dmp.uncollected_observations(tasks, ANCHOR, today="2026-08-06", grace_days=7)
expect("uncollected: stale tag + post-anchor fire past grace is flagged", len(out) == 1)

out = dmp.uncollected_observations(tasks, ANCHOR, today="2026-08-01", grace_days=7)
expect("uncollected: within the grace window is NOT flagged (fresh fire)", len(out) == 0)

# UNVERIFIABLE is its own ratified bucket -- never a re-canary candidate.
tasks_u = [{"id": "ora-pm-ledger", "enabled": True, "cronExpression": "0 18 * * *",
            "description": "x [MODEL: UNVERIFIABLE | checked 2026-07-08]",
            "lastRunAt": "2026-08-03T07:47:46.444Z"}]
expect("uncollected: UNVERIFIABLE tags are never flagged",
       dmp.uncollected_observations(tasks_u, ANCHOR, today="2026-08-20") == [])

# Already re-canaried: tag on/after anchor => settled.
tasks_ok = [{"id": "ora-aaos-expire-leases", "enabled": True, "cronExpression": "20 7 * * *",
             "description": "x [MODEL: claude-opus-5 observed | checked 2026-07-26]",
             "lastRunAt": "2026-08-03T07:47:46.476Z"}]
expect("uncollected: tag on/after the anchor is settled",
       dmp.uncollected_observations(tasks_ok, ANCHOR, today="2026-08-20") == [])

# Scope filter (STEP 2.5 v1.8): one-time and disabled tasks are exempt.
tasks_ot = [{"id": "ora-one-time", "enabled": True, "cronExpression": None,
             "fireAt": "2026-08-21T13:30:00.000Z",
             "description": "x [MODEL: claude-sonnet-5 | checked 2026-07-01]",
             "lastRunAt": "2026-07-29T00:00:00.000Z"}]
expect("uncollected: one-time tasks are exempt",
       dmp.uncollected_observations(tasks_ot, ANCHOR, today="2026-08-20") == [])
tasks_dis = [dict(tasks[0], enabled=False)]
expect("uncollected: disabled tasks are exempt",
       dmp.uncollected_observations(tasks_dis, ANCHOR, today="2026-08-20") == [])

# A task that has never run cannot have an uncollected observation.
tasks_nr = [dict(tasks[0], lastRunAt=None)]
expect("uncollected: never-run task is not flagged",
       dmp.uncollected_observations(tasks_nr, ANCHOR, today="2026-08-20") == [])

# Fired BEFORE the anchor moved => no new evidence exists to collect.
tasks_pre = [dict(tasks[0], lastRunAt="2026-07-24T00:00:00.000Z")]
expect("uncollected: pre-anchor fire yields nothing to collect",
       dmp.uncollected_observations(tasks_pre, ANCHOR, today="2026-08-20") == [])

# Undated tag is unassertable freshness -> treated as stale, flagged once fired.
tasks_und = [dict(tasks[0], description="x [MODEL: claude-sonnet-5]")]
expect("uncollected: undated real-id tag is flagged",
       len(dmp.uncollected_observations(tasks_und, ANCHOR, today="2026-08-20")) == 1)

expect("uncollected: malformed lastRunAt is skipped, not raised",
       dmp.uncollected_observations([dict(tasks[0], lastRunAt="not-a-date")],
                                    ANCHOR, today="2026-08-20") == [])
expect("uncollected: empty task list is safe",
       dmp.uncollected_observations([], ANCHOR, today="2026-08-20") == [])

# --- summary ---------------------------------------------------------------------------
passed = sum(1 for ok, _ in results if ok)
print("\ndangling-mutation-probe tests: %d/%d passed" % (passed, len(results)))
sys.exit(0 if passed == len(results) else 1)
