#!/usr/bin/env python3
"""Regression tests for .github/workflows/fleet-deadman.yml (OI-323) -- the only OFF-machine
monitor, so a silent break here disables the whole dead-man.

Three layers:
  1. Wiring: the heartbeat is read from the `deadman-heartbeat` branch checked out at hb/, that
     checkout tolerates a missing branch (continue-on-error) so it surfaces as check (d)
     instead of crashing before an issue can open, and HB_PATH points at hb/.
  2. Behaviour: the embedded evaluator is extracted and executed with a FROZEN clock against
     fixture heartbeats: healthy, late (f), stale (a), below floor (b/c), registry flag (e),
     missing/unparseable (d), floors config unreadable (g).
  3. Floor parity + issue dedupe (2026-11-05): the floors are READ from
     maintenance/_shared/scheduler-stores.json (the single source of truth), never hardcoded --
     a hardcoded {"cc":10,"lams":18} drifted from the SSOT (cc 13 / lams 4) and failed every run
     from 2026-09-22. And each failure CLASS gets its own issue, so a new class is never
     swallowed into one stale open issue (the old title-prefix dedupe collapsed everything
     into issue #19, opened 2026-07-19 for a stale heartbeat).

Run: python test-fleet-deadman-workflow.py [path/to/fleet-deadman.yml]   (exit 0 = all pass)
"""
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, ".."))
WF = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    REPO, ".github", "workflows", "fleet-deadman.yml")
SSOT_REL = "maintenance/_shared/scheduler-stores.json"
SSOT = os.path.join(REPO, *SSOT_REL.split("/"))

results = []


def expect(label, cond, detail=""):
    results.append((bool(cond), label))
    if not cond:
        print("  FAIL: %s %s" % (label, detail))


with open(WF, encoding="utf-8") as f:
    doc = yaml.safe_load(f)
steps = doc["jobs"]["deadman"]["steps"]
with open(SSOT, encoding="utf-8") as f:
    SSOT_FLOORS = {k: v for k, v in json.load(f)["fleetFloors"].items() if not k.startswith("_")}


def heredoc(step):
    m = re.search(r"python3 - <<'PY'\n(.*?)\nPY\s*$", step.get("run", ""), re.S)
    return m.group(1) if m else ""


# --- wiring ------------------------------------------------------------------------------------------
hb_steps = [s for s in steps if str(s.get("uses", "")).startswith("actions/checkout")
            and (s.get("with") or {}).get("ref") == "deadman-heartbeat"]
expect("wiring: a checkout step reads ref deadman-heartbeat", len(hb_steps) == 1, repr(hb_steps))
if hb_steps:
    expect("wiring: heartbeat checkout lands at hb/", hb_steps[0]["with"].get("path") == "hb")
    expect("wiring: heartbeat checkout tolerates a missing branch",
           hb_steps[0].get("continue-on-error") is True)
repo_steps = [s for s in steps if str(s.get("uses", "")).startswith("actions/checkout")
              and not (s.get("with") or {}).get("path")]
expect("wiring: repo itself is checked out at the workspace root (floors SSOT readable)",
       len(repo_steps) == 1, repr(repo_steps))
check = [s for s in steps if s.get("id") == "check"]
expect("wiring: evaluator step present", len(check) == 1)
script = heredoc(check[0]) if check else ""
expect("wiring: evaluator heredoc extractable", bool(script))
expect("wiring: evaluator reads hb/fleet-heartbeat.json", 'HB_PATH = "hb/fleet-heartbeat.json"' in script)
order = [i for i, s in enumerate(steps) if s in hb_steps or s in repo_steps or s.get("id") == "check"]
expect("wiring: both checkouts run before the evaluator",
       len(order) == 3 and steps[order[-1]].get("id") == "check")
expect("wiring: 08:00 ET (f) deadline pinned", "AM_DEADLINE_LOCAL_H, AM_DEADLINE_LOCAL_M = 8, 0" in script)
on = doc.get("on") or doc.get(True) or {}
expect("wiring: runs daily at 14:00 UTC", any(c.get("cron") == "0 14 * * *" for c in on.get("schedule", [])), repr(on))
expect("wiring: permissions unchanged (issues write, contents read)",
       doc.get("permissions") == {"issues": "write", "contents": "read"}, repr(doc.get("permissions")))

# --- floor parity (static) ---------------------------------------------------------------------------
expect("parity: evaluator reads floors from the SSOT path",
       'FLOORS_PATH = "%s"' % SSOT_REL in script, "")
expect("parity: no hardcoded floor dict literal in the evaluator",
       not re.search(r"""FLOORS\s*=\s*\{\s*["'](cc|lams)["']\s*:\s*\d""", script), "")
expect("parity: no stale hardcoded floor numbers (10/18) anywhere in the workflow",
       '"cc": 10' not in open(WF, encoding="utf-8").read()
       and '"lams": 18' not in open(WF, encoding="utf-8").read())
expect("parity: SSOT floors are non-negative ints for cc and lams",
       all(isinstance(SSOT_FLOORS.get(k), int) and not isinstance(SSOT_FLOORS.get(k), bool)
           and SSOT_FLOORS[k] >= 0 for k in ("cc", "lams")), repr(SSOT_FLOORS))
expect("parity: LAMS floor is 0 -- fleet deliberately dark (Gabriel ruling 2026-10-30)",
       SSOT_FLOORS.get("lams") == 0, repr(SSOT_FLOORS))


# --- behaviour with a frozen clock -----------------------------------------------------------------------
class Frozen(datetime.datetime):
    _now = None

    @classmethod
    def now(cls, tz=None):
        base = cls._now
        return base.astimezone(tz) if tz else base.replace(tzinfo=None)


def evaluate(hb, now_utc, write_file=True, ssot="copy"):
    """Run the extracted evaluator in a temp dir; return (alert, body_text, outputs, classes).

    ssot: "copy" = the real SSOT at its repo-relative path (as on the runner); None = absent;
    any other str = written verbatim as the SSOT file."""
    cwd = os.getcwd()
    d = tempfile.mkdtemp()
    os.makedirs(os.path.join(d, "hb"))
    if write_file:
        with open(os.path.join(d, "hb", "fleet-heartbeat.json"), "w", encoding="utf-8") as f:
            f.write(hb if isinstance(hb, str) else json.dumps(hb))
    if ssot is not None:
        dst = os.path.join(d, *SSOT_REL.split("/"))
        os.makedirs(os.path.dirname(dst))
        if ssot == "copy":
            shutil.copy(SSOT, dst)
        else:
            with open(dst, "w", encoding="utf-8") as f:
                f.write(ssot)
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
    cpath = os.path.join(d, "deadman-classes.json")
    classes = json.load(open(cpath, encoding="utf-8")) if os.path.exists(cpath) else None
    return kv["alert"] == "true", body, kv, classes


def hbfile(ts, cc=43, lams=0, cc_exists=True, lams_exists=True):
    return {"ts": ts, "probe_version": "t", "fleets": {"cc": cc, "lams": lams},
            "registries": {"cc": {"path": "p", "exists": cc_exists, "sha256": "a"},
                           "lams": {"path": "q", "exists": lams_exists, "sha256": "b"}}}


def cls_of(classes):
    return [c["class"] for c in (classes or [])]


UTC = datetime.timezone.utc
NOW = datetime.datetime(2026, 9, 21, 14, 0, 0, tzinfo=UTC)  # 10:00 EDT, the workflow's run time
OK_TS = "2026-09-21T11:30:00Z"  # 07:30 EDT
CCF, LMF = SSOT_FLOORS.get("cc"), SSOT_FLOORS.get("lams")

if script:
    alert, body, kv, classes = evaluate(hbfile(OK_TS), NOW)
    expect("healthy: today's real shape (cc 43, lams 0 dark) -> no alert", not alert, body)
    expect("healthy: classes file is an empty list", classes == [], repr(classes))
    expect("healthy: parsed values name the floors source", SSOT_REL in body, body)

    # parity (behavioural): exactly-at-floor passes, one-below alarms, for the SSOT values
    alert, body, _, classes = evaluate(hbfile(OK_TS, cc=CCF), NOW)
    expect("parity: cc exactly at SSOT floor %s -> no alert" % CCF, not alert, body)
    alert, body, _, classes = evaluate(hbfile(OK_TS, cc=CCF - 1), NOW)
    expect("parity: cc one below SSOT floor -> alert naming the SSOT floor",
           alert and ("cc enabled count %d below ratified floor %d" % (CCF - 1, CCF)) in body
           and cls_of(classes) == ["floor-cc"], body)
    alert, body, _, classes = evaluate(hbfile(OK_TS, lams=LMF), NOW)
    expect("parity: lams exactly at SSOT floor %s -> no alert" % LMF, not alert, body)
    # a recalibrated SSOT is honoured without touching the workflow
    alert, body, _, classes = evaluate(
        hbfile(OK_TS, cc=43, lams=2), NOW,
        ssot=json.dumps({"fleetFloors": {"cc": 50, "lams": 3}}))
    expect("parity: workflow follows a recalibrated SSOT (cc 50, lams 3)",
           alert and "cc enabled count 43 below ratified floor 50" in body
           and "lams enabled count 2 below ratified floor 3" in body
           and cls_of(classes) == ["floor-cc", "floor-lams"], body)

    alert, body, _, classes = evaluate(hbfile("2026-09-21T12:30:00Z"), NOW)  # 08:30 EDT
    expect("late (f): heartbeat after the 08:00 ET deadline -> alert",
           alert and "completed LATE" in body and cls_of(classes) == ["am-late"], body)
    alert, body, _, classes = evaluate(hbfile("2026-09-19T11:30:00Z"), NOW)
    expect("stale (a): 50h old -> alert", alert and "heartbeat stale" in body
           and set(cls_of(classes)) == {"stale", "am-not-run"}, body)
    alert, body, _, classes = evaluate(hbfile(OK_TS, cc=None), NOW)
    expect("floor: unreadable registry (count None) -> alert",
           alert and "below ratified floor" in body and cls_of(classes) == ["floor-cc"], body)
    alert, body, _, classes = evaluate(hbfile(OK_TS, lams=None), NOW)
    expect("floor: dark LAMS still alarms when its count is unreadable (None)",
           alert and cls_of(classes) == ["floor-lams"], body)
    alert, body, _, classes = evaluate(hbfile(OK_TS, lams_exists=False), NOW)
    expect("(e): registry existence false -> alert (LAMS existence still guarded while dark)",
           alert and "existence flag is false" in body and cls_of(classes) == ["registry-lams"], body)
    alert, body, _, classes = evaluate("{not json", NOW)
    expect("(d): unparseable heartbeat -> alert",
           alert and "missing or unparseable" in body and cls_of(classes) == ["heartbeat-missing"], body)
    alert, body, _, classes = evaluate(None, NOW, write_file=False)
    expect("(d): branch missing (no hb file) -> alert", alert and "missing or unparseable" in body, body)
    expect("(d): branch missing names the branch and the publisher, not a generic error",
           "deadman-heartbeat" in body and "publish-fleet-heartbeat.py" in body, body)
    expect("issue body: first checks point at the publish log and --status",
           "--status" in body and "`publish:`" in body, body)

    # (g) floors SSOT unreadable -> fail CLOSED with its own class; other checks still run
    alert, body, _, classes = evaluate(hbfile(OK_TS), NOW, ssot=None)
    expect("(g): floors SSOT missing -> alert, class floors-config",
           alert and SSOT_REL in body and cls_of(classes) == ["floors-config"], body)
    alert, body, _, classes = evaluate(hbfile(OK_TS, lams_exists=False), NOW, ssot="{bad")
    expect("(g): floors SSOT unparseable -> alert, and (e) still evaluated",
           alert and set(cls_of(classes)) == {"floors-config", "registry-lams"}, body)
    alert, body, _, classes = evaluate(hbfile(OK_TS), NOW,
                                       ssot=json.dumps({"fleetFloors": {"cc": "13", "lams": 0}}))
    expect("(g): non-int floor in SSOT -> alert, never silently skipped",
           alert and cls_of(classes) == ["floors-config"], body)
    alert, body, _, classes = evaluate(hbfile(OK_TS), NOW,
                                       ssot=json.dumps({"fleetFloors": {"cc": True, "lams": 0}}))
    expect("(g): bool floor in SSOT -> alert", alert and cls_of(classes) == ["floors-config"], body)

    # every class entry carries a non-empty human reason (used in the issue title)
    alert, body, _, classes = evaluate(hbfile("2026-09-19T11:30:00Z", cc=1, cc_exists=False), NOW)
    expect("classes: each entry has class + reason, deduped by class",
           bool(classes) and all(c.get("class") and c.get("reason") for c in classes)
           and len(cls_of(classes)) == len(set(cls_of(classes))), repr(classes))

# --- issue dedupe: one issue per failure class ---------------------------------------------------------
issue_steps = [s for s in steps if "issue" in str(s.get("name", "")).lower()]
expect("dedupe: exactly one issue step", len(issue_steps) == 1, repr([s.get("name") for s in issue_steps]))
issue_script = heredoc(issue_steps[0]) if issue_steps else ""
expect("dedupe: issue step is an extractable python heredoc", bool(issue_script))
expect("dedupe: issue step only runs on alert",
       bool(issue_steps) and "steps.check.outputs.alert == 'true'" in str(issue_steps[0].get("if")))


def run_issue_step(open_issues, classes, run_date="2026-11-05"):
    """Execute the issue step against a fake `gh`; return the list of mutating gh calls."""
    calls = []
    real_run = subprocess.run

    def fake_run(argv, *a, **kw):
        argv = list(argv)
        assert argv[0] == "gh", argv
        if argv[1:3] == ["issue", "list"]:
            calls.append(("list", argv))
            return subprocess.CompletedProcess(argv, 0, stdout=json.dumps(open_issues), stderr="")
        if argv[1:3] == ["issue", "comment"]:
            calls.append(("comment", argv[3]))
        elif argv[1:3] == ["issue", "create"]:
            calls.append(("create", argv[argv.index("--title") + 1]))
        else:
            raise AssertionError("unexpected gh call %r" % argv)
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    cwd = os.getcwd()
    d = tempfile.mkdtemp()
    with open(os.path.join(d, "deadman-classes.json"), "w", encoding="utf-8") as f:
        json.dump(classes, f)
    with open(os.path.join(d, "deadman-body.md"), "w", encoding="utf-8") as f:
        f.write("body\n")
    os.environ.update({"GITHUB_REPOSITORY": "o/r", "RUN_DATE": run_date})
    subprocess.run = fake_run
    try:
        os.chdir(d)
        exec(compile(issue_script, "workflow-issue-step", "exec"), {"__name__": "__main__"})
    finally:
        subprocess.run = real_run
        os.chdir(cwd)
    return calls


if issue_script:
    LEGACY = {"number": 19, "title": "FLEET DEAD-MAN: heartbeat stale (45.4h > 24h) — 2026-07-19"}
    FL = {"class": "floor-lams", "reason": "lams enabled count 0 below ratified floor 4"}
    ST = {"class": "stale", "reason": "heartbeat stale (30.0h > 24h)"}

    calls = run_issue_step([LEGACY], [FL])
    muts = [c for c in calls if c[0] != "list"]
    expect("dedupe: a class with no open issue opens a NEW one, even with the legacy #19 open",
           len(muts) == 1 and muts[0][0] == "create"
           and muts[0][1].startswith("FLEET DEAD-MAN [floor-lams]: ")
           and "2026-11-05" in muts[0][1], repr(calls))
    expect("dedupe: never comments on the legacy catch-all issue",
           not any(c == ("comment", "19") for c in calls), repr(calls))
    expect("dedupe: issue list asks for enough rows (not gh's default 30)",
           any(k == "list" and "--limit" in a for k, a in calls), repr(calls))

    open_fl = {"number": 31, "title": "FLEET DEAD-MAN [floor-lams]: lams ... — 2026-11-04"}
    calls = run_issue_step([LEGACY, open_fl], [FL])
    muts = [c for c in calls if c[0] != "list"]
    expect("dedupe: same class again -> comments on its own open issue, no duplicate",
           muts == [("comment", "31")], repr(calls))

    calls = run_issue_step([LEGACY, open_fl], [FL, ST])
    muts = [c for c in calls if c[0] != "list"]
    expect("dedupe: a NEW class alongside an ongoing one gets its own distinct issue",
           ("comment", "31") in muts
           and any(k == "create" and t.startswith("FLEET DEAD-MAN [stale]: ") for k, t in muts)
           and len(muts) == 2, repr(calls))

    lookalike = {"number": 40, "title": "FLEET DEAD-MAN [floor-lams-extra]: x"}
    calls = run_issue_step([lookalike], [FL])
    muts = [c for c in calls if c[0] != "list"]
    expect("dedupe: class match is exact (floor-lams does not match floor-lams-extra)",
           len(muts) == 1 and muts[0][0] == "create", repr(calls))

failed = [l for ok, l in results if not ok]
print("%d/%d passed" % (len(results) - len(failed), len(results)))
sys.exit(1 if failed else 0)
