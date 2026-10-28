#!/usr/bin/env python3
"""Tests for maintenance/run-gate-stages.py (full-gate output capture + claim heartbeat).

Regression target: ora-full-gate-weekly improvised `npm run gate 2>&1 | tail -40`, so the
pass/fail count (printed far above the last 40 lines) never reached the alert email and the full
log was lost; and a gate longer than the 30-minute claim TTL let a second fire reclaim the block.

Run: python _tests/test_run_gate_stages.py   (exit 0 = pass)
"""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
MAINT = os.path.dirname(HERE)
RUNNER = os.path.join(MAINT, "run-gate-stages.py")
SENTINEL = os.path.join(os.path.dirname(MAINT), "scheduled-tasks", "_shared", "block-sentinel.py")

results = []


def check(name, cond, detail=""):
    results.append(bool(cond))
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else "  " + str(detail)[:600]))


spec = importlib.util.spec_from_file_location("run_gate_stages", RUNNER)
rgs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rgs)

FAKE_STAGE = r'''
import sys, time
stage = sys.argv[1]
if stage == "ok":
    print("all good")
elif stage == "noisy_fail":
    # summary FIRST, then 600 lines of stack-trace noise: `| tail -40` would never see the counts
    print("Test Files  1 failed | 9 passed (10)")
    print("      Tests  3 failed | 41 passed (44)")
    for i in range(600):
        print("    at frame %d (file.ts:%d)" % (i, i))
    sys.exit(1)
elif stage == "hang":
    print("starting"); sys.stdout.flush()
    time.sleep(60)
elif stage == "sleepy":
    time.sleep(2.2)
    print("done sleeping")
elif stage == "swallowed":
    print("      Tests  2 failed | 5 passed (7)")
elif stage == "tscfail":
    print("src/a.ts(1,1): error TS2322")
    print("Found 3 errors in 2 files.")
    sys.exit(2)
'''


def run_runner(tmp, stages, extra=None, package_json=None, timeout=180):
    fake = os.path.join(tmp, "fake_stage.py")
    if not os.path.exists(fake):
        with open(fake, "w", encoding="ascii") as fh:
            fh.write(FAKE_STAGE)
    logd = os.path.join(tmp, "logs-" + str(len(os.listdir(tmp))))
    tmpl = '"%s" "%s" {stage}' % (sys.executable.replace("\\", "/"), fake.replace("\\", "/"))
    cmd = [sys.executable, RUNNER, "--cwd", tmp, "--log-dir", logd, "--stages", ",".join(stages),
           "--cmd-template", tmpl, "--run-date", "Monday 2026-10-26", "--origin-sha", "abc1234"]
    if package_json:
        cmd += ["--package-json", package_json]
    cmd += extra or []
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    summ = {}
    sp = os.path.join(logd, "summary.json")
    if os.path.exists(sp):
        with open(sp, encoding="utf-8") as fh:
            summ = json.load(fh)
    return p, summ, logd


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


# ---------------------------------------------------------------- parse_counts
c = rgs.parse_counts("noise\n Test Files  1 failed | 9 passed (10)\n      Tests  3 failed | 41 passed | 2 skipped (46)\n")
check("parse: vitest", c.get("runner") == "vitest" and c["failed"] == 3 and c["passed"] == 41 and c["total"] == 46 and c["skipped"] == 2, c)
c = rgs.parse_counts("Tests:       1 failed, 41 passed, 42 total\nSnapshots: 0 total")
check("parse: jest", c.get("runner") == "jest" and c["failed"] == 1 and c["passed"] == 41 and c["total"] == 42, c)
c = rgs.parse_counts("# tests 44\n# pass 41\n# fail 3\n# skipped 0\n")
check("parse: node:test", c.get("runner") == "node:test" and c["passed"] == 41 and c["failed"] == 3 and c["total"] == 44, c)
c = rgs.parse_counts("Found 3 errors in 2 files.\n")
check("parse: tsc", c.get("errors") == 3 and c.get("runner") == "tsc", c)
c = rgs.parse_counts("\x1b[31m✖\x1b[0m 12 problems (3 errors, 9 warnings)\n")
check("parse: eslint (ANSI stripped)", c.get("errors") == 3 and c.get("warnings") == 9, c)
check("parse: unrecognised output -> {} (never invent a count)", rgs.parse_counts("hello\nworld\n") == {} and rgs.parse_counts("") == {})
c = rgs.parse_counts("Tests  1 failed | 1 passed (2)\n...rerun...\nTests  0 failed | 2 passed (2)\n")
check("parse: LAST summary wins", c["failed"] == 0 and c["passed"] == 2, c)
check("fmt_counts: unparsed is explicit", rgs.fmt_counts({}) == "counts unparsed")

with tempfile.TemporaryDirectory() as tmp:
    # ---------------------------------------------------------------- clean run
    p, s, logd = run_runner(tmp, ["ok"])
    check("clean run -> exit 0, verdict CLEAN", p.returncode == 0 and s.get("verdict") == "CLEAN", p.stdout + p.stderr)
    check("clean subject is not an [ACTION] subject", read(s["subjectFile"]) == "full gate CLEAN - Monday 2026-10-26", s.get("subject"))

    # ---------------------------------------------------------------- the tail -40 regression
    p, s, logd = run_runner(tmp, ["ok", "noisy_fail", "tscfail"])
    check("failing run -> exit 1, verdict FAILING, first failing stage named",
          p.returncode == 1 and s["verdict"] == "FAILING" and s["firstFailingStage"] == "noisy_fail", p.stdout + p.stderr)
    nf = [r for r in s["stages"] if r["stage"] == "noisy_fail"][0]
    full = read(nf["logPath"])
    check("FULL log kept on disk (not tailed): 602 lines incl. the summary at the top",
          len(full.splitlines()) == 602 and "Tests  3 failed | 41 passed (44)" in full and "frame 599" in full, len(full.splitlines()))
    check("counts parsed from the whole log even though the summary is >40 lines from the end",
          nf["counts"].get("failed") == 3 and nf["counts"].get("passed") == 41, nf["counts"])
    body = read(s["bodyFile"])
    check("email body carries the parsed pass/fail count", "41 passed / 3 failed of 44" in body, body[:900])
    check("email body carries the stage table with exit codes", "noisy_fail" in body and "exit=1" in body and "exit=2" in body, body[:900])
    check("email body points at the untruncated log", nf["logPath"] in body and "602 lines" in body, body[:1200])
    check("email body: totals line", "Stages: 1 passed, 2 failed, 0 missing, of 3 run." in body, body[:300])
    check("later stage still ran after an earlier failure (one failure does not mask another)",
          [r["stage"] for r in s["stages"]] == ["ok", "noisy_fail", "tscfail"] and s["stages"][2]["counts"].get("errors") == 3, s["stages"][2])
    check("subject names the FIRST failing stage, date before the tag, ASCII only",
          s["subject"] == "[ACTION] full gate FAILING - Monday 2026-10-26 -- noisy_fail" and s["subject"].isascii(), s["subject"])
    check("body excerpt is bounded (head 25 + tail 10), not the whole 600-line log", body.count("at frame") < 60, body.count("at frame"))
    check("every reported path is forward-slash", "\\" not in json.dumps({k: s[k] for k in ("logDir", "subjectFile", "bodyFile", "summaryFile")}) and all("\\" not in (r["logPath"] or "") for r in s["stages"]))

    # ---------------------------------------------------------------- exit 0 but reports failures
    p, s, logd = run_runner(tmp, ["swallowed"])
    check("exit 0 with 'failed' counts in the output is FAIL, never a silent CLEAN",
          s["stages"][0]["status"] == "FAIL" and s["verdict"] == "FAILING" and p.returncode == 1, p.stdout)
    check("body explains the exit-0 override", "Exit code was 0 but the output reports failures" in read(s["bodyFile"]))

    # ---------------------------------------------------------------- probe subject
    p, s, logd = run_runner(tmp, ["noisy_fail"])
    check("probe-subject.txt holds the stem the probe can match",
          read(s["probeSubjectFile"]) == "full gate FAILING - Monday 2026-10-26", s.get("probeSubjectFile"))
    check("probe subject is NOT the [ACTION] email subject", read(s["probeSubjectFile"]) != read(s["subjectFile"]))
    p, s, logd = run_runner(tmp, ["ok"])
    check("clean run writes no probe subject", s["probeSubjectFile"] is None)

    # ---------------------------------------------------------------- MISSING stage
    pj = os.path.join(tmp, "package.json")
    with open(pj, "w", encoding="ascii") as fh:
        json.dump({"scripts": {"ok": "x"}}, fh)
    p, s, logd = run_runner(tmp, ["ok", "reconcile:noi-crosscheck"], package_json=pj)
    miss = s["stages"][1]
    check("script absent from package.json -> MISSING (never a pass), run fails",
          miss["status"] == "MISSING" and p.returncode == 1 and s["totals"]["missing"] == 1, p.stdout)
    check("MISSING shows in the body as a finding", "itself a finding" in read(s["bodyFile"]))

    # ---------------------------------------------------------------- timeout
    t0 = time.time()
    p, s, logd = run_runner(tmp, ["hang", "ok"], extra=["--stage-timeout-min", "0.04"])
    check("hung stage is killed at the stage timeout and reported TIMEOUT, run continues",
          s["stages"][0]["status"] == "TIMEOUT" and s["stages"][1]["status"] == "PASS" and (time.time() - t0) < 40,
          "%s %.0fs" % (s["stages"][0]["status"], time.time() - t0))
    check("partial output of the killed stage is still on disk", "starting" in read(s["stages"][0]["logPath"]))

    # ---------------------------------------------------------------- heartbeat
    state = os.path.join(tmp, "sentinel-state.json")
    today = datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=-4))).strftime("%Y-%m-%d")
    cl = subprocess.run([sys.executable, SENTINEL, "claim", "--task", "t", "--block", "main", "--run-id", "g1",
                         "--ttl-min", "30", "--state", state], capture_output=True, text=True)
    with open(state, encoding="utf-8") as fh:
        data = json.load(fh)
    day = list(data.keys())[0]
    data[day]["main"]["claimedAt"] = (datetime.now(timezone.utc) - timedelta(minutes=28)).strftime("%Y-%m-%dT%H:%M:%SZ")
    with open(state, "w", encoding="utf-8") as fh:
        json.dump(data, fh)
    hb_args = ["--sentinel-task", "t", "--sentinel-block", "main", "--sentinel-run-id", "g1",
               "--sentinel-state", state, "--sentinel-script", SENTINEL, "--renew-every-sec", "0.5"]
    p, s, logd = run_runner(tmp, ["sleepy"], extra=hb_args)
    with open(state, encoding="utf-8") as fh:
        rec = json.load(fh)[day]["main"]
    check("heartbeat renewed the 28-minute-old claim during the run",
          (s["heartbeat"] or {}).get("renewals", 0) >= 1 and rec.get("renewals", 0) >= 1 and not s["heartbeat"]["claimLost"],
          "%s %s" % (s.get("heartbeat"), rec))
    check("claim is young again afterwards (a second fire would stand down)",
          datetime.strptime(rec["claimedAt"], "%Y-%m-%dT%H:%M:%SZ") > datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=2), rec)
    check("renewal is mentioned in the email body", "renewed" in read(s["bodyFile"]).lower(), read(s["bodyFile"])[:300])

    # claim lost to another run -> reported loudly, run still completes
    data[day]["main"]["runId"] = "someone-else"
    with open(state, "w", encoding="utf-8") as fh:
        json.dump(data, fh)
    p, s, logd = run_runner(tmp, ["sleepy"], extra=hb_args)
    check("lost claim -> claimLost recorded, stage results still produced",
          (s["heartbeat"] or {}).get("claimLost") == "REFUSED_NOT_OWNER" and s["stages"][0]["status"] == "PASS", s.get("heartbeat"))
    check("lost claim is flagged in the email body", "CLAIM LOST" in read(s["bodyFile"]))

    # unreadable state file is an ERROR, not a lost claim
    with open(state, "w", encoding="utf-8") as fh:
        fh.write("{bad")
    p, s, logd = run_runner(tmp, ["sleepy"], extra=hb_args)
    hbs = s["heartbeat"] or {}
    check("unreadable state -> not reported as claimLost", not hbs.get("claimLost"), hbs)
    check("unreadable state -> recorded in heartbeat.errors", len(hbs.get("errors", [])) >= 1, hbs)
    check("heartbeat errors are printed in the email body", "CLAIM HEARTBEAT ERRORS" in read(s["bodyFile"]), read(s["bodyFile"])[:400])

    # heartbeat that cannot run at all (bad sentinel path) must be visible
    p, s, logd = run_runner(tmp, ["ok"], extra=["--sentinel-task", "t", "--sentinel-block", "main",
                                                "--sentinel-run-id", "g1", "--sentinel-script",
                                                os.path.join(tmp, "no-such-sentinel.py")])
    check("nonexistent sentinel script -> heartbeat errors surfaced in body",
          "CLAIM HEARTBEAT ERRORS" in read(s["bodyFile"]) or s["verdict"] == "CLEAN" and (s["heartbeat"] or {}).get("errors"),
          s.get("heartbeat"))

    # no sentinel args -> no heartbeat object
    p, s, logd = run_runner(tmp, ["ok"])
    check("no sentinel args -> heartbeat null", s["heartbeat"] is None)

    # bad cwd
    bad = subprocess.run([sys.executable, RUNNER, "--cwd", os.path.join(tmp, "nope"), "--log-dir", os.path.join(tmp, "x")],
                         capture_output=True, text=True)
    check("missing --cwd -> exit 2", bad.returncode == 2, bad.stderr)

# ---------------------------------------------------------------- spec conformance
SPEC = os.path.join(os.path.dirname(MAINT), "scheduled-tasks", "ora-full-gate-weekly", "SKILL.md")
with open(SPEC, encoding="utf-8") as fh:
    spec_text = fh.read()
check("spec: gate is run through run-gate-stages.py", "maintenance/run-gate-stages.py" in spec_text)
check("spec: forbids piping the gate through tail/head", "tail" in spec_text and "NEVER with `npm run gate`" in spec_text)
check("spec: the alert email is sent with -SubjectFile/-BodyFile from the runner",
      "-SubjectFile <log-dir>/email-subject.txt" in spec_text and "-BodyFile <log-dir>/email-body.txt" in spec_text)
check("spec: claim line records the scheduled time", "claim --task ora-full-gate-weekly" in spec_text and "--scheduled-et 11:30" in spec_text)
check("spec: probe is fed probe-subject.txt, never the email subject",
      "-SubjectFile <log-dir>/probe-subject.txt" in spec_text and "ONE subject file feeds both" not in spec_text)
check("spec: recipients unchanged (ggoldberg only, no cc)", "ggoldberg@oxfordra.net ONLY (no cc, never ze@)" in spec_text)

n_fail = results.count(False)
print("\nrun-gate-stages: %d pass, %d fail" % (results.count(True), n_fail))
sys.exit(1 if n_fail else 0)
