#!/usr/bin/env python3
"""Tests for fleet-token-footprint.py (pure functions only; no live state)."""
import importlib.util
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("ftf", os.path.join(HERE, "fleet-token-footprint.py"))
ftf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ftf)

FAILS = []


def check(name, cond):
    print(("PASS  " if cond else "FAIL  ") + name)
    if not cond:
        FAILS.append(name)


# --- runs_per_week -------------------------------------------------------
check("daily", ftf.runs_per_week("45 16 * * *") == 7)
check("weekly Monday", ftf.runs_per_week("15 5 * * 1") == 1)
check("weekdays", ftf.runs_per_week("0 9 * * 1-5") == 5)
check("hourly", ftf.runs_per_week("17 * * * *") == 168)
check("one-time is zero", ftf.runs_per_week("@2026-09-29") == 0)
check("expired is zero", ftf.runs_per_week("EXPIRED@2026-09-11") == 0)
check("monthly ~ 12/52", abs(ftf.runs_per_week("0 10 1 * *") - 12 / 52.0) < 1e-9)
check("quarterly ~ 4/52", abs(ftf.runs_per_week("30 15 1 1,4,7,10 *") - 4 / 52.0) < 1e-9)
check("blank cron is zero", ftf.runs_per_week("") == 0)
check("step */15 minutes", ftf.runs_per_week("*/15 * * * *") == 672)
check("step */2 hours", ftf.runs_per_week("0 */2 * * *") == 84)
check("dom range with step", abs(ftf.runs_per_week("0 0 1-31/7 * *") - 5 * 12 / 52.0) < 1e-9)
check("dow 1-7 is every day", ftf.runs_per_week("0 9 * * 1-7") == 7)
check("dow 0-7 is every day", ftf.runs_per_week("0 9 * * 0-7") == 7)
check("dow bare 7 is Sunday (1/wk)", ftf.runs_per_week("0 9 * * 7") == 1)
check("dow */7 does not crash, Sunday only", ftf.runs_per_week("0 9 * * */7") == 1)
check("named dow range MON-FRI", ftf.runs_per_week("0 9 * * MON-FRI") == 5)
check("named dow lowercase", ftf.runs_per_week("0 9 * * mon") == 1)
check("named month", abs(ftf.runs_per_week("0 0 1 JAN *") - 1 / 52.0) < 1e-9)
check("6-field cron is zero, no crash", ftf.runs_per_week("0 0 9 * * *") == 0)
check("garbage cron is zero, no crash", ftf.runs_per_week("not a cron at all x") == 0)
check("zero step is zero, no crash", ftf.runs_per_week("*/0 * * * *") == 0)
check("non-string cron is zero, no crash", ftf.runs_per_week(None) == 0 and ftf.runs_per_week(5) == 0)


# --- scan_lines: unique API calls, first turn, ToolSearch, MCP ------------
def asst(mid, usage, blocks):
    return json.dumps({"type": "assistant", "message": {"id": mid, "usage": usage, "content": blocks}})


u1 = {"input_tokens": 2, "cache_creation_input_tokens": 60000, "cache_read_input_tokens": 30000}
u2 = {"input_tokens": 1, "cache_creation_input_tokens": 100, "cache_read_input_tokens": 90000}
lines = [
    json.dumps({"type": "user", "message": {"content": "x"}}),
    asst("m1", u1, [{"type": "text", "text": "a"}]),
    asst("m1", u1, [{"type": "tool_use", "name": "ToolSearch", "input": {}}]),   # same API call, 2nd block
    asst("m2", u2, [{"type": "tool_use", "name": "mcp__c5f4869f-7d3a__notion-fetch", "input": {}}]),
    "not json at all",
]
first, calls, ts, mcp = ftf.scan_lines(lines)
check("first turn = input+creation+read of first assistant", first == 90002)
check("calls counts unique message ids, not records", calls == 2)
check("ToolSearch detected", ts is True)
check("mcp prefix captured", mcp == {"c5f4869f-7"})

first, calls, ts, mcp = ftf.scan_lines([json.dumps({"type": "user", "message": {"content": "x"}})])
check("no assistant records -> None/0/False/empty", (first, calls, ts, mcp) == (None, 0, False, set()))


# --- task_header: only a FIRST user message counts, stream is left positioned ---
def user(text, **kw):
    rec = {"type": "user", "message": {"content": text}}
    rec.update(kw)
    return json.dumps(rec)


fh = io.StringIO("\n".join([
    json.dumps({"type": "queue-operation"}),
    user("meta", isMeta=True),
    user('<scheduled-task name="ora-x" file="f"> body', timestamp="2026-09-14T13:56:24.305Z"),
    asst("m1", u1, []),
]) + "\n")
name, epoch, _ = ftf.task_header(fh)
check("header name from first real user message", name == "ora-x")
check("header epoch parsed from record timestamp", epoch is not None and abs(epoch - 1789394184.305) < 1e-3)
check("stream left positioned after header (assistant still readable)", ftf.scan_lines(fh)[1] == 1)

name, _, _ = ftf.task_header(io.StringIO(user("please review: <scheduled-task name=\"ora-y\">") + "\n"))
check("quoted tag mid-message is NOT a scheduled run", name is None)
name, _, _ = ftf.task_header(io.StringIO(user([{"type": "text", "text": '<scheduled-task name="ora-z" file="f">'}]) + "\n"))
check("list-shaped content handled", name == "ora-z")
check("empty stream -> no header", ftf.task_header(io.StringIO("")) == (None, None, None))
check("bad timestamp -> None epoch, no crash", ftf._epoch("garbage") is None and ftf._epoch(None) is None)

# --- sort_rows: enabled first, then weekly footprint -----------------------
rows = [
    {"task": "off-heavy", "enabled": False, "first": 100000, "runs_per_week": 168},
    {"task": "on-light", "enabled": True, "first": 90000, "runs_per_week": 1},
    {"task": "on-heavy", "enabled": True, "first": 120000, "runs_per_week": 7},
]
check("sort: enabled before disabled, heaviest first", [r["task"] for r in ftf.sort_rows(rows)] == ["on-heavy", "on-light", "off-heavy"])

# --- parse_args: a malformed --days must not exit non-zero -----------------
check("parse_args default days", ftf.parse_args([]).days == 30)
check("parse_args explicit days", ftf.parse_args(["--days", "7"]).days == 7)
check("parse_args malformed --days falls back to 30", ftf.parse_args(["--days", "notanint"]).days == 30)
check("parse_args tolerates unknown flag", ftf.parse_args(["--bogus"]).days == 30)

print("\n%d failure(s)" % len(FAILS))
sys.exit(1 if FAILS else 0)
