#!/usr/bin/env python3
"""run-gate-stages.py -- run the oxford-command-center gate one stage at a time, keep the FULL
output of every stage on disk, parse the pass/fail summary out of it, and build the alert email
from the parsed result.

WHY (insights report, week of 2026-10-21): the weekly full gate (ora-full-gate-weekly) was run by
an LLM improvising `npm run gate 2>&1 | tail -40`. The last 40 lines of a 600-line log are the
bottom of the stack trace, not the summary, so the pass/fail count never reached the alert email
and the full log was gone. Three properties this script exists to guarantee:

  1. The FULL stdout+stderr of each stage is written to <log-dir>/<stage>.log. Nothing is tailed
     on the way to disk; excerpts are only ever taken FROM those files, for the email.
  2. The summary (stage exit codes + test/error counts) is PARSED from the output by
     parse_counts(), not read off the end of it. A count that cannot be parsed is reported as
     "unparsed", never guessed (house rule: never fabricate a count or a pass).
  3. The email body and subject are built from that parsed result and written to files, so the
     send step is `send-via-outlook.ps1 -SubjectFile <subject> -BodyFile <body>` and cannot lose
     the summary to a shell pipe.

It also keeps the double-fire claim alive: the gate can run longer than the 30-minute claim TTL
(2026-10-19: 23 min; a hung stage is longer), after which a second fire reclaims the block and
runs the gate concurrently. While stages run, a heartbeat thread calls
`block-sentinel.py renew --min-age-min 25` every --renew-every-sec. A REFUSED renew (exit 12) means
the claim was lost to another run: it is recorded in the summary (claimLost) and the email.

READ-ONLY toward the repo: it runs the commands it is given in --cwd and writes only under
--log-dir. It never sends mail, never touches a registry, never calls Notion.

Usage:
  python run-gate-stages.py --cwd <worktree> --log-dir <dir>
        [--stages governance,typecheck,...] [--cmd-template "npm run {stage}"]
        [--package-json <path>] [--stage-timeout-min 20]
        [--sentinel-task T --sentinel-block B --sentinel-run-id R [--sentinel-period day|week|month]
         [--sentinel-script PATH] [--renew-every-sec 60] [--renew-min-age-min 25]]
        [--run-date "Monday 2026-10-26"] [--origin-sha SHA] [--workbook-mtime TEXT]

Writes <log-dir>/summary.json, <log-dir>/email-body.txt, <log-dir>/email-subject.txt and prints
the summary JSON on stdout. Exit 0 = every stage passed; 1 = at least one stage did not pass
(failed, timed out, or missing); 2 = bad arguments.

Stdlib only. ASCII-only. Paths are printed with forward slashes (Git Bash eats backslashes).
"""
import argparse
import json
import os
import re
import subprocess
import sys
import threading
import time

DEFAULT_STAGES = ["governance", "typecheck", "lint", "check:dev-css", "check:schema-drift", "test",
                  "reconcile:snapshot", "reconcile", "reconcile:noi-crosscheck",
                  "warehouse:verify", "warehouse:drift"]
HEAD_LINES = 25
TAIL_LINES = 10
HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_SENTINEL = os.path.normpath(os.path.join(HERE, "..", "scheduled-tasks", "_shared", "block-sentinel.py"))


def fwd(path):
    return str(path).replace("\\", "/")


def safe_name(stage):
    return re.sub(r"[^A-Za-z0-9._-]+", "_", stage)


# ---------------------------------------------------------------- parsing

_ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def parse_counts(text):
    """Pull pass/fail counts out of a stage's full output. Returns a dict (possibly empty).

    Recognises (the LAST match wins, because summaries print at the end):
      vitest    'Tests  3 failed | 41 passed (44)'
      jest      'Tests:       1 failed, 41 passed, 42 total'
      node:test '# pass 41' / '# fail 3'
      tsc       'Found 3 errors in 2 files.'
      eslint    '12 problems (3 errors, 9 warnings)'
    Anything else -> {} (the caller reports "unparsed"; it never invents a number)."""
    text = _ANSI.sub("", text or "")
    out = {}

    def last(rx):
        found = list(re.finditer(rx, text, re.M))
        return found[-1] if found else None

    m = last(r"^\s*Tests\s+(?P<body>.*\((?P<total>\d+)\)\s*)$")
    if m:
        body = m.group("body")
        f = re.search(r"(\d+)\s+failed", body)
        p = re.search(r"(\d+)\s+passed", body)
        s = re.search(r"(\d+)\s+(?:skipped|todo)", body)
        out.update(runner="vitest", passed=int(p.group(1)) if p else 0, failed=int(f.group(1)) if f else 0,
                   total=int(m.group("total")))
        if s:
            out["skipped"] = int(s.group(1))
    if not out:
        m = last(r"^\s*Tests:\s+(?P<body>.*?(?P<total>\d+)\s+total)\s*$")
        if m:
            body = m.group("body")
            f = re.search(r"(\d+)\s+failed", body)
            p = re.search(r"(\d+)\s+passed", body)
            out.update(runner="jest", passed=int(p.group(1)) if p else 0, failed=int(f.group(1)) if f else 0,
                       total=int(m.group("total")))
    if not out:
        p = last(r"^#\s*pass\s+(\d+)\s*$")
        f = last(r"^#\s*fail\s+(\d+)\s*$")
        if p or f:
            out.update(runner="node:test", passed=int(p.group(1)) if p else 0, failed=int(f.group(1)) if f else 0)
            out["total"] = out["passed"] + out["failed"]
    m = last(r"Found\s+(\d+)\s+errors?\b")
    if m:
        out.setdefault("runner", "tsc")
        out["errors"] = int(m.group(1))
    m = last(r"(\d+)\s+problems?\s+\((\d+)\s+errors?,\s+(\d+)\s+warnings?\)")
    if m:
        out.setdefault("runner", "eslint")
        out["errors"], out["warnings"] = int(m.group(2)), int(m.group(3))
    return out


def fmt_counts(c):
    if not c:
        return "counts unparsed"
    bits = []
    if "total" in c:
        bits.append("%d passed / %d failed of %d" % (c.get("passed", 0), c.get("failed", 0), c["total"]))
    if "errors" in c:
        bits.append("%d errors" % c["errors"])
    if "warnings" in c:
        bits.append("%d warnings" % c["warnings"])
    if c.get("skipped"):
        bits.append("%d skipped" % c["skipped"])
    return ", ".join(bits) if bits else "counts unparsed"


# ---------------------------------------------------------------- running

def kill_tree(proc):
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True, timeout=30)
        else:
            proc.kill()
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


def run_stage(stage, cmd_template, cwd, log_path, timeout_s):
    """Run one stage with stdin closed, all output to log_path. Returns a result dict."""
    cmd = cmd_template.format(stage=stage)
    t0 = time.time()
    timed_out = False
    with open(log_path, "wb") as fh:
        proc = subprocess.Popen(cmd, shell=True, cwd=cwd, stdin=subprocess.DEVNULL, stdout=fh,
                                stderr=subprocess.STDOUT)
        try:
            rc = proc.wait(timeout=timeout_s)
        except subprocess.TimeoutExpired:
            timed_out = True
            kill_tree(proc)
            try:
                proc.wait(timeout=30)
            except Exception:
                pass
            rc = None
    dur = round(time.time() - t0, 1)
    with open(log_path, "rb") as fh:
        text = fh.read().decode("utf-8", "replace")
    lines = text.splitlines()
    counts = parse_counts(text)
    status = "TIMEOUT" if timed_out else ("PASS" if rc == 0 else "FAIL")
    # Exit 0 while the output itself reports failed tests / errors is not a pass: never
    # let a swallowed exit code produce a silent CLEAN.
    reports_failures = bool(counts.get("failed") or counts.get("errors"))
    if status == "PASS" and reports_failures:
        status = "FAIL"
    return {"stage": stage, "command": cmd, "exit": rc, "timedOut": timed_out, "durationSec": dur,
            "status": status, "exitZeroButReportsFailures": status == "FAIL" and rc == 0,
            "counts": counts, "logPath": fwd(log_path), "logLines": len(lines),
            "logBytes": len(text.encode("utf-8")),
            "head": lines[:HEAD_LINES], "tail": lines[-TAIL_LINES:] if len(lines) > HEAD_LINES else []}


class Heartbeat(threading.Thread):
    """Keeps the block-sentinel claim alive while stages run."""

    def __init__(self, python, script, args, every_s, min_age):
        super().__init__(daemon=True)
        self.cmd = [python, script, "renew", "--task", args["task"], "--block", args["block"],
                    "--run-id", args["run_id"], "--min-age-min", str(min_age)]
        if args.get("period"):
            self.cmd += ["--period", args["period"]]
        if args.get("state"):
            self.cmd += ["--state", args["state"]]
        self.every_s = every_s
        self.stop_evt = threading.Event()
        self.renewals = 0
        self.claim_lost = None
        self.errors = []

    def tick(self):
        try:
            p = subprocess.run(self.cmd, capture_output=True, text=True, timeout=60, stdin=subprocess.DEVNULL)
        except Exception as exc:
            self.errors.append("renew call failed: %s" % exc)
            return
        try:
            payload = json.loads(p.stdout)
        except Exception:
            payload = {}
        decision = payload.get("decision")
        if decision == "RENEWED":
            self.renewals += 1
        elif decision == "RENEW_NOT_NEEDED":
            pass
        elif decision in ("REFUSED_NOT_OWNER", "REFUSED_NOT_IN_PROGRESS") and not payload.get("stateFileError"):
            # A readable state file that says the claim is not ours. An unreadable one
            # (OneDrive hiccup) also answers REFUSED_NO_CLAIM; that is an error, not a lost claim.
            self.claim_lost = decision
        else:
            self.errors.append("renew exit %s decision %s%s" % (
                p.returncode, decision,
                " (%s)" % payload["stateFileError"] if payload.get("stateFileError") else ""))

    def run(self):
        while not self.stop_evt.wait(self.every_s):
            self.tick()

    def finish(self):
        self.stop_evt.set()
        self.join(timeout=5)
        self.tick()   # one last look so a lost claim is reported even if the run was shorter than a tick


# ---------------------------------------------------------------- report

def verdict_of(results):
    bad = [r for r in results if r["status"] != "PASS"]
    return ("CLEAN" if not bad else "FAILING"), (bad[0]["stage"] if bad else None)


def build_probe_subject(run_date, first_bad):
    """The text outlook-sent-probe.ps1 must be given. The probe matches the SENT subject against
    the probe text and only strips [tags] from the sent side, so the "[ACTION] ... -- <stage>"
    subject cannot be fed to it; the stem "full gate FAILING - <date>" can."""
    return None if first_bad is None else "full gate FAILING - %s" % run_date


def build_subject(run_date, first_bad):
    if first_bad is None:
        return "full gate CLEAN - %s" % run_date
    return "[ACTION] full gate FAILING - %s -- %s" % (run_date, first_bad)


def build_body(summary):
    res = summary["stages"]
    t = summary["totals"]
    L = ["FULL GATE %s -- %s" % (summary["verdict"], summary.get("runDate") or ""),
         "Stages: %d passed, %d failed, %d missing, of %d run." % (t["passed"], t["failed"], t["missing"], t["run"]),
         ""]
    if summary.get("originSha"):
        L.append("origin/main: %s" % summary["originSha"])
    if summary.get("workbookMtime"):
        L.append("Workbook mtime: %s" % summary["workbookMtime"])
    L.append("Full per-stage logs (untruncated): %s" % summary["logDir"])
    hb = summary.get("heartbeat") or {}
    if hb.get("claimLost"):
        L.append("!! CLAIM LOST: block-sentinel refused a renewal (%s). Another fire may have run the gate "
                 "concurrently; treat this report as possibly duplicated." % hb["claimLost"])
    elif hb.get("renewals"):
        L.append("Claim renewed %d time(s) (run outlived the claim TTL)." % hb["renewals"])
    if hb.get("errors"):
        L.append("!! CLAIM HEARTBEAT ERRORS (%d): the claim was NOT being kept alive reliably; if the run "
                 "exceeded the claim TTL a second fire may have run concurrently. First: %s"
                 % (len(hb["errors"]), hb["errors"][0]))
    L += ["", "STAGE RESULTS", "-------------"]
    for r in res:
        ex = "n/a" if r["exit"] is None else str(r["exit"])
        L.append("%-28s %-8s exit=%-4s %6.1fs  %s" % (r["stage"], r["status"], ex, r["durationSec"], fmt_counts(r["counts"])))
    for r in res:
        if r["status"] == "PASS":
            continue
        L += ["", "=== %s: %s (exit %s) ===" % (r["stage"], r["status"], "n/a" if r["exit"] is None else r["exit"])]
        if r["status"] == "MISSING":
            L.append("No npm script named %r in package.json -- itself a finding." % r["stage"])
            continue
        if r.get("exitZeroButReportsFailures"):
            L.append("Exit code was 0 but the output reports failures: treated as FAIL.")
        L.append("Parsed: %s" % fmt_counts(r["counts"]))
        L.append("Full log: %s (%d lines)" % (r["logPath"], r["logLines"]))
        L.append("--- first %d lines ---" % len(r["head"]))
        L += r["head"]
        if r["tail"]:
            L.append("--- last %d lines ---" % len(r["tail"]))
            L += r["tail"]
    return "\n".join(L) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--cwd", required=True)
    ap.add_argument("--log-dir", required=True)
    ap.add_argument("--stages", default=",".join(DEFAULT_STAGES))
    ap.add_argument("--cmd-template", default="npm run {stage}")
    ap.add_argument("--package-json", default=None, help="if given, a stage with no script there is MISSING")
    ap.add_argument("--stage-timeout-min", type=float, default=20.0)
    ap.add_argument("--sentinel-task")
    ap.add_argument("--sentinel-block")
    ap.add_argument("--sentinel-run-id")
    ap.add_argument("--sentinel-period", default=None)
    ap.add_argument("--sentinel-state", default=None)
    ap.add_argument("--sentinel-script", default=DEFAULT_SENTINEL)
    ap.add_argument("--renew-every-sec", type=float, default=60.0)
    ap.add_argument("--renew-min-age-min", type=int, default=25)
    ap.add_argument("--run-date", default="")
    ap.add_argument("--origin-sha", default="")
    ap.add_argument("--workbook-mtime", default="")
    a = ap.parse_args(argv)

    if not os.path.isdir(a.cwd):
        print("cwd not found: %s" % fwd(a.cwd), file=sys.stderr)
        return 2
    os.makedirs(a.log_dir, exist_ok=True)
    stages = [s.strip() for s in a.stages.split(",") if s.strip()]
    scripts = None
    if a.package_json:
        try:
            with open(a.package_json, encoding="utf-8") as fh:
                scripts = set((json.load(fh).get("scripts") or {}).keys())
        except Exception as exc:
            print("cannot read package.json (%s): %s" % (fwd(a.package_json), exc), file=sys.stderr)
            return 2

    hb = None
    if a.sentinel_task and a.sentinel_block and a.sentinel_run_id:
        hb = Heartbeat(sys.executable, a.sentinel_script,
                       {"task": a.sentinel_task, "block": a.sentinel_block, "run_id": a.sentinel_run_id,
                        "period": a.sentinel_period, "state": a.sentinel_state},
                       a.renew_every_sec, a.renew_min_age_min)
        hb.start()

    results = []
    try:
        for stage in stages:
            if scripts is not None and stage not in scripts:
                results.append({"stage": stage, "command": a.cmd_template.format(stage=stage), "exit": None,
                                "timedOut": False, "durationSec": 0.0, "status": "MISSING", "counts": {},
                                "logPath": None, "logLines": 0, "logBytes": 0, "head": [], "tail": []})
                continue
            log_path = os.path.join(a.log_dir, safe_name(stage) + ".log")
            results.append(run_stage(stage, a.cmd_template, a.cwd, log_path, a.stage_timeout_min * 60))
    finally:
        if hb:
            hb.finish()

    verdict, first_bad = verdict_of(results)
    summary = {"verdict": verdict, "firstFailingStage": first_bad, "runDate": a.run_date,
               "originSha": a.origin_sha, "workbookMtime": a.workbook_mtime, "logDir": fwd(a.log_dir),
               "stages": results,
               "totals": {"passed": sum(r["status"] == "PASS" for r in results),
                          "failed": sum(r["status"] in ("FAIL", "TIMEOUT") for r in results),
                          "missing": sum(r["status"] == "MISSING" for r in results), "run": len(results)},
               "heartbeat": ({"renewals": hb.renewals, "claimLost": hb.claim_lost, "errors": hb.errors}
                             if hb else None)}
    subject = build_subject(a.run_date, first_bad)
    body = build_body(summary)
    summary["subject"] = subject
    probe = build_probe_subject(a.run_date, first_bad)
    summary["probeSubjectFile"] = fwd(os.path.join(a.log_dir, "probe-subject.txt")) if probe else None
    if probe:
        with open(os.path.join(a.log_dir, "probe-subject.txt"), "w", encoding="utf-8", newline="") as fh:
            fh.write(probe)
    summary["subjectFile"] = fwd(os.path.join(a.log_dir, "email-subject.txt"))
    summary["bodyFile"] = fwd(os.path.join(a.log_dir, "email-body.txt"))
    summary["summaryFile"] = fwd(os.path.join(a.log_dir, "summary.json"))
    with open(os.path.join(a.log_dir, "email-subject.txt"), "w", encoding="utf-8", newline="") as fh:
        fh.write(subject)
    with open(os.path.join(a.log_dir, "email-body.txt"), "w", encoding="utf-8", newline="") as fh:
        fh.write(body)
    with open(os.path.join(a.log_dir, "summary.json"), "w", encoding="utf-8", newline="") as fh:
        json.dump(summary, fh, indent=2, sort_keys=True)
    keys = ("verdict", "firstFailingStage", "totals", "subject", "subjectFile", "probeSubjectFile", "bodyFile",
            "summaryFile",
            "logDir", "heartbeat")
    sys.stdout.write(json.dumps({k: summary[k] for k in keys}, indent=2, sort_keys=True) + "\n")
    return 0 if verdict == "CLEAN" else 1


if __name__ == "__main__":
    sys.exit(main())
