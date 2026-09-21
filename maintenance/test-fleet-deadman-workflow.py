#!/usr/bin/env python3
"""Regression tests for .github/workflows/fleet-deadman.yml (OI-323) -- the only OFF-machine
monitor, so a silent break here disables the whole dead-man.

Two layers:
  1. Wiring: the heartbeat is read from the `deadman-heartbeat` branch checked out at hb/, that
     checkout tolerates a missing branch (continue-on-error) so it surfaces as check (d)
     instead of crashing before an issue can open, and HB_PATH points at hb/.
  2. Behaviour: the embedded evaluator is extracted and executed with a FROZEN clock against
     fixture heartbeats: healthy, late (f), stale (a), below floor (b/c), registry flag (e),
     missing/unparseable (d).

Run: python test-fleet-deadman-workflow.py [path/to/fleet-deadman.yml]   (exit 0 = all pass)
"""
import datetime
import json
import os
import re
import sys
import tempfile

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
WF = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    HERE, "..", ".github", "workflows", "fleet-deadman.yml")

results = []


def expect(label, cond, detail=""):
    results.append((bool(cond), label))
    if not cond:
        print("  FAIL: %s %s" % (label, detail))


with open(WF, encoding="utf-8") as f:
    doc = yaml.safe_load(f)
steps = doc["jobs"]["deadman"]["steps"]

# --- wiring ------------------------------------------------------------------------------------------
hb_steps = [s for s in steps if str(s.get("uses", "")).startswith("actions/checkout")
            and (s.get("with") or {}).get("ref") == "deadman-heartbeat"]
expect("wiring: a checkout step reads ref deadman-heartbeat", len(hb_steps) == 1, repr(hb_steps))
if hb_steps:
    expect("wiring: heartbeat checkout lands at hb/", hb_steps[0]["with"].get("path") == "hb")
    expect("wiring: heartbeat checkout tolerates a missing branch",
           hb_steps[0].get("continue-on-error") is True)
check = [s for s in steps if s.get("id") == "check"]
expect("wiring: evaluator step present", len(check) == 1)
script = ""
if check:
    m = re.search(r"python3 - <<'PY'\n(.*?)\nPY\s*$", check[0]["run"], re.S)
    expect("wiring: evaluator heredoc extractable", bool(m))
    script = m.group(1) if m else ""
expect("wiring: evaluator reads hb/fleet-heartbeat.json", 'HB_PATH = "hb/fleet-heartbeat.json"' in script)
expect("wiring: floors unchanged (cc>=10, lams>=18)", '{"cc": 10, "lams": 18}' in script)
order = [i for i, s in enumerate(steps) if s in hb_steps or s.get("id") == "check"]
expect("wiring: branch checkout runs before the evaluator", order == sorted(order) and len(order) == 2)
expect("wiring: 08:00 ET (f) deadline pinned", "AM_DEADLINE_LOCAL_H, AM_DEADLINE_LOCAL_M = 8, 0" in script)
on = doc.get("on") or doc.get(True) or {}
expect("wiring: runs daily at 14:00 UTC", any(c.get("cron") == "0 14 * * *" for c in on.get("schedule", [])), repr(on))
expect("wiring: permissions unchanged (issues write, contents read)",
       doc.get("permissions") == {"issues": "write", "contents": "read"}, repr(doc.get("permissions")))


# --- behaviour with a frozen clock -----------------------------------------------------------------------
class Frozen(datetime.datetime):
    _now = None

    @classmethod
    def now(cls, tz=None):
        base = cls._now
        return base.astimezone(tz) if tz else base.replace(tzinfo=None)


def evaluate(hb, now_utc, write_file=True):
    """Run the extracted evaluator in a temp dir; return (alert, body_text)."""
    cwd = os.getcwd()
    d = tempfile.mkdtemp()
    os.makedirs(os.path.join(d, "hb"))
    if write_file:
        with open(os.path.join(d, "hb", "fleet-heartbeat.json"), "w", encoding="utf-8") as f:
            f.write(hb if isinstance(hb, str) else json.dumps(hb))
    out = os.path.join(d, "gh_out")
    os.environ["GITHUB_OUTPUT"] = out
    real = datetime.datetime
    Frozen._now = now_utc
    datetime.datetime = Frozen
    try:
        os.chdir(d)
        exec(compile(script, "workflow-evaluator", "exec"), {"__name__": "__main__"})
    finally:
        datetime.datetime = real
        os.chdir(cwd)
    kv = dict(l.split("=", 1) for l in open(out, encoding="utf-8").read().splitlines() if "=" in l)
    body = open(os.path.join(d, "deadman-body.md"), encoding="utf-8").read()
    return kv["alert"] == "true", body


def hbfile(ts, cc=38, lams=27, cc_exists=True, lams_exists=True):
    return {"ts": ts, "probe_version": "t", "fleets": {"cc": cc, "lams": lams},
            "registries": {"cc": {"path": "p", "exists": cc_exists, "sha256": "a"},
                           "lams": {"path": "q", "exists": lams_exists, "sha256": "b"}}}


UTC = datetime.timezone.utc
NOW = datetime.datetime(2026, 9, 21, 14, 0, 0, tzinfo=UTC)  # 10:00 EDT, the workflow's run time

if script:
    alert, body = evaluate(hbfile("2026-09-21T11:30:00Z"), NOW)  # 07:30 EDT
    expect("healthy: 07:30 ET heartbeat, counts at ratified level -> no alert", not alert, body)
    alert, body = evaluate(hbfile("2026-09-21T12:30:00Z"), NOW)  # 08:30 EDT
    expect("late (f): heartbeat after the 08:00 ET deadline -> alert", alert and "completed LATE" in body, body)
    alert, body = evaluate(hbfile("2026-09-19T11:30:00Z"), NOW)
    expect("stale (a): 50h old -> alert", alert and "heartbeat stale" in body, body)
    alert, body = evaluate(hbfile("2026-09-21T11:30:00Z", cc=5), NOW)
    expect("floor (b): cc below 10 -> alert", alert and "cc enabled count 5 below ratified floor 10" in body, body)
    alert, body = evaluate(hbfile("2026-09-21T11:30:00Z", lams=1), NOW)
    expect("floor (c): lams below 18 -> alert", alert and "lams enabled count 1 below ratified floor 18" in body, body)
    alert, body = evaluate(hbfile("2026-09-21T11:30:00Z", cc=None), NOW)
    expect("floor: unreadable registry (count None) -> alert", alert and "below ratified floor" in body, body)
    alert, body = evaluate(hbfile("2026-09-21T11:30:00Z", lams_exists=False), NOW)
    expect("(e): registry existence false -> alert", alert and "existence flag is false" in body, body)
    alert, body = evaluate("{not json", NOW)
    expect("(d): unparseable heartbeat -> alert", alert and "missing or unparseable" in body, body)
    alert, body = evaluate(None, NOW, write_file=False)
    expect("(d): branch missing (no hb file) -> alert", alert and "missing or unparseable" in body, body)
    expect("(d): branch missing names the branch and the publisher, not a generic error",
           "deadman-heartbeat" in body and "publish-fleet-heartbeat.py" in body, body)
    expect("issue body: first checks point at the publish log and --status",
           "--status" in body and "`publish:`" in body, body)

failed = [l for ok, l in results if not ok]
print("%d/%d passed" % (len(results) - len(failed), len(results)))
sys.exit(1 if failed else 0)
