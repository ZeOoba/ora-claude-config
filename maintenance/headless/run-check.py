#!/usr/bin/env python3
"""ORA headless check runner -- one entry point, three checks.

    python run-check.py stranded-spec     # spec folders never wired into a registry
    python run-check.py mirror-drift      # Command Center mirror deploy health
    python run-check.py integrity-guard   # fleet registry presence + phantom dispatch

Exit 0 clean / 1 findings / 2 can't-verify. See ora_headless_lib.py for the full
contract and for why these run the underlying scripts directly instead of
`claude -p` (short version: OAuth is expired outside the Desktop app, verified
live, and all three checks are already deterministic).

Add `--dry-run` to print the verdict and skip paging.
"""
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ora_headless_lib as lib  # noqa: E402

MAINT = os.path.join(lib.CLAUDE, "maintenance")
OCC = os.path.join(lib.HOME, "oxford-command-center")
CLASSIFIER = os.path.join(OCC, "scripts", "mirror-run-classify.ps1")
TIMEOUT = 300


def _sh(cmd, cwd=None):
    """Run a child check. Returns (rc, stdout+stderr). rc None on launch failure."""
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=TIMEOUT, cwd=cwd,
            encoding="utf-8", errors="replace",
        )
        return proc.returncode, (proc.stdout or "") + (proc.stderr or "")
    except subprocess.TimeoutExpired:
        return None, "timed out after %ds" % TIMEOUT
    except Exception as exc:  # noqa: BLE001
        return None, "%s: %s" % (type(exc).__name__, exc)


def _tail(text, n=2500):
    text = (text or "").strip()
    return text if len(text) <= n else "..." + text[-n:]


# task-folder-registration-probe.py:406 prints this and then returns 0 when its
# store_discovery helper is unavailable. rc 0 therefore means "clean OR never ran";
# only the text separates them.
PROBE_CANNOT_RUN = "probe cannot run"


# --------------------------------------------------------------------------
# 1. stranded-spec
# --------------------------------------------------------------------------
def check_stranded_spec(result):
    """A SKILL.md folder authored on disk but never wired into a live registry.

    Delegates to task-folder-registration-probe.py, which reconciles CURRENT
    folder inventory against CURRENT registry membership (UNREGISTERED /
    ORPHANED_REGISTRATION / ARCHIVED_BUT_REGISTERED). Its contract is
    `return 1 if bad else 0`, and it fails OPEN (returns 0) if a shared helper
    breaks -- so a 1 here is a real reconciliation failure, not a probe bug.
    """
    probe = os.path.join(MAINT, "task-folder-registration-probe.py")
    if not os.path.exists(probe):
        result.error("registration probe missing", evidence=probe)
        return
    rc, out = _sh([sys.executable, probe])
    if rc is None:
        result.error("registration probe did not run", evidence=_tail(out))
    elif rc == 1:
        result.finding(
            "Stranded spec folder(s): folder inventory and registry membership "
            "do not reconcile.",
            severity="HIGH", evidence=_tail(out),
        )
    elif rc != 0:
        result.error("registration probe exited %s" % rc, evidence=_tail(out))
    elif PROBE_CANNOT_RUN in (out or ""):
        # rc 0 does NOT mean clean here. The probe fails OPEN -- if its shared
        # store_discovery helper is unavailable it prints this WARN and returns 0
        # anyway ("a broken shared helper must never false-alarm"). Reporting that
        # as "reconcile cleanly" would assert a fact we never checked, and would
        # make a permanently-broken probe indistinguishable from a passing one --
        # the precise failure this wrapper's exit contract exists to prevent.
        result.error(
            "registration probe returned 0 without running (fails open on a broken "
            "shared helper) -- reconciliation was NOT actually verified",
            evidence=_tail(out),
        )
    else:
        result.note("folders and registries reconcile cleanly (both fleets)")


# --------------------------------------------------------------------------
# 2. mirror-drift
# --------------------------------------------------------------------------
# From the SKILL.md: "run the classifier, do not hand-reason this ... Use its
# verdict -- do not re-derive your own." Classification lives in tested code
# (deploy-beacon.ps1, replayed against all four real 2026-08 incidents), so this
# wrapper reads the verdict and does nothing clever with the raw fields.
ALARM_PREFIX = "ALARM_"
# mirror-run-classify.ps1:71 initialises this and deploy-beacon.ps1:475 returns it
# when no beacon is readable. Not an alarm, not benign -- can't-verify.
INDETERMINATE = "INDETERMINATE"
KNOWN_BENIGN = {
    "HEALTHY",
    "RUN_IN_PROGRESS",              # in flight; nothing can be said until it ends
    "BENIGN_INTERRUPTED",           # power/session event explains the kill
    "BENIGN_KILLED_AFTER_COMPLETION",  # deploy published, only teardown was lost
}


def check_mirror_drift(result):
    if not os.path.exists(CLASSIFIER):
        result.error("mirror classifier missing", evidence=CLASSIFIER)
        return
    rc, out = _sh(
        ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
         "-File", CLASSIFIER],
        cwd=OCC,
    )
    # "If the classifier itself fails to run, that is an ALARM (can't-verify is
    # not healthy)" -- SKILL.md step 4.
    if rc is None or rc != 0:
        result.error("mirror classifier failed to run (rc=%s)" % rc, evidence=_tail(out))
        return

    # Parse the WHOLE blob first. The classifier pretty-prints, and its `errors`
    # array holds bare strings -- each of which is itself a valid JSON document on
    # its own line. A reversed per-line scan therefore matched an error string and
    # bound `payload` to a str, so `payload.get("verdict")` raised exactly when the
    # classifier was reporting trouble. Insist on a dict on both paths.
    payload = None
    try:
        candidate = json.loads(out)
        if isinstance(candidate, dict):
            payload = candidate
    except ValueError:
        pass
    if payload is None:
        for line in reversed([l for l in out.splitlines() if l.strip()]):
            try:
                candidate = json.loads(line)
            except ValueError:
                continue
            if isinstance(candidate, dict):
                payload = candidate
                break
    if payload is None:
        result.error("mirror classifier emitted no parseable JSON object", evidence=_tail(out))
        return

    verdict = payload.get("verdict")
    reason = payload.get("reason") or ""
    if not verdict:
        result.error("mirror classifier JSON carried no verdict", evidence=_tail(out))
        return

    if str(verdict).startswith(ALARM_PREFIX):
        result.finding(
            "Mirror deploy %s -- %s" % (verdict, reason),
            severity="HIGH",
            evidence=json.dumps(payload, indent=2)[:2000],
        )
        return

    if verdict == INDETERMINATE:
        # A first-class classifier verdict, not an unknown one: deploy-beacon.ps1
        # returns it when there is no readable beacon ("Never fabricate HEALTHY
        # from this"). Can't-verify, and named as such so it does not read as the
        # classifier having grown a state we failed to keep up with.
        result.error(
            "mirror classifier returned INDETERMINATE -- no readable beacon, so this "
            "run's outcome is unknown (not healthy)", evidence=reason or _tail(out),
        )
        return

    if verdict not in KNOWN_BENIGN:
        # A verdict this wrapper has never heard of is can't-verify, not healthy:
        # the classifier may have grown a state we are silently swallowing.
        result.error("unrecognised mirror verdict %r" % verdict, evidence=_tail(out))
        return

    result.note("mirror verdict %s -- %s" % (verdict, reason))
    # Reported, never alarmed on (SKILL.md): ahead-of-origin is a FLAG carrying
    # stranded-work risk, behind is informational only.
    ahead = payload.get("gitAhead")
    if ahead:
        result.note("shared checkout is %s commit(s) ahead of origin -- unpushed work "
                    "is stranded, not deployed; push or PR it (do not push it "
                    "automatically)" % ahead)


# --------------------------------------------------------------------------
# 3. integrity-guard
# --------------------------------------------------------------------------
def check_integrity_guard(result):
    """Deterministic slice of ora-task-integrity-guard: is the fleet readable,
    and are dispatches actually starting?

    DELIBERATELY EXCLUDES registry-membership-probe.py. That probe takes no
    flags and unconditionally regenerates `session-context.md` and
    `fleet-roster.md` on every run -- shared state that every session loads at
    startup. Running it unattended several times a day would mean an automated
    job continuously rewriting a shared context file, and during a bounded fleet
    pause it writes a `0 live recurring` summary that reads like a destroyed
    fleet. Keep membership drift in the supervised in-fleet guard, which can
    interpret what it wrote.

    ALSO EXCLUDED: SKILL.md self-healing (content-hash restore). That is
    judgement work, not a check, and it stays in the in-fleet task.
    """
    status = os.path.join(MAINT, "fleet-status.py")
    if os.path.exists(status):
        rc, out = _sh([sys.executable, status, "--summary"])
        if rc is None or rc == 3:
            result.error("fleet-status could not read the registries", evidence=_tail(out))
        elif rc not in (0, 1):
            result.error("fleet-status exited %s" % rc, evidence=_tail(out))
        else:
            result.note("fleet-status: %s" % _tail(out, 600))
    else:
        result.error("fleet-status.py missing", evidence=status)

    phantom = os.path.join(MAINT, "phantom-dispatch-probe.py")
    if not os.path.exists(phantom):
        result.error("phantom-dispatch probe missing", evidence=phantom)
        return
    rc, out = _sh([sys.executable, phantom, "--quiet"])
    if rc is None:
        result.error("phantom-dispatch probe did not run", evidence=_tail(out))
    elif rc == 1:
        result.finding(
            "Phantom dispatch(es) detected -- task(s) were dispatched but never "
            "started, so lastRunAt looks identical to a real run.",
            severity="HIGH", evidence=_tail(out),
        )
    elif rc != 0:
        result.error("phantom-dispatch probe exited %s" % rc, evidence=_tail(out))
    else:
        result.note("no phantom dispatches in window")


# --------------------------------------------------------------------------
# 4. freshness -- who watches these three
# --------------------------------------------------------------------------
# A check that silently stops running is indistinguishable from a check that
# keeps passing: both are silence, and silence is what "clean" looks like by
# design. This closes that loop by ageing each check's `-latest.json` heartbeat
# against its own cadence AND cross-checking the Windows task's own LastRunTime.
#
# Thresholds are cadence-aware. 30h for a daily check matches fleet-deadman.ps1's
# ThresholdHours. mirror-drift is WEEKDAY-only, so a Friday run is still the most
# recent one on Monday morning -- 96h, not 30h, or it would page every weekend.
WATCHED = {
    "integrity-guard": {"task": "ORA Headless - integrity-guard", "max_age_h": 30},
    "stranded-spec": {"task": "ORA Headless - stranded-spec", "max_age_h": 30},
    "mirror-drift": {"task": "ORA Headless - mirror-drift", "max_age_h": 96},
}
# Windows stamps a never-run task with an ancient date (11/30/1999 on this box)
# rather than null. This is a THRESHOLD, not a sentinel value: any LastRunTime
# before this year is read as "has never actually fired".
NEVER_RUN_BEFORE_YEAR = 2000


def _task_info(task_name):
    """(found, lastRunTime, lastTaskResult, nextRunTime) from Windows Task Scheduler."""
    ps = (
        "$ErrorActionPreference='SilentlyContinue';"
        "$t = Get-ScheduledTask -TaskName '%s';"
        "if (-not $t) { 'MISSING' } else {"
        " $i = $t | Get-ScheduledTaskInfo;"
        " $i | Select-Object LastRunTime,LastTaskResult,NextRunTime | ConvertTo-Json -Compress }"
    ) % task_name.replace("'", "''")
    rc, out = _sh(["powershell.exe", "-NoProfile", "-Command", ps])
    if rc is None:
        return None, None
    out = (out or "").strip()
    if "MISSING" in out:
        return False, None
    if not out:
        # EMPTY IS NOT ABSENT. $ErrorActionPreference='SilentlyContinue' means a
        # failing Get-ScheduledTask still exits 0 with no stdout, so treating empty
        # as "deleted" would page "your task no longer exists -- re-register it" on
        # what is really a can't-verify. Three of those at once is the kind of false
        # alarm that costs trust in the pager.
        return None, None
    try:
        return True, json.loads(out)
    except ValueError:
        return None, None


def _parse_ps_date(value):
    """PowerShell ConvertTo-Json emits /Date(ms)/ or an ISO-ish string.

    Returns None when the value cannot be parsed. Callers MUST distinguish that
    from a genuine never-run stamp -- conflating the two turns an unreadable date
    into permanent silence.
    """
    import datetime as _dt
    if not value:
        return None
    text = str(value).strip()
    if text.startswith("/Date("):
        inner = text[6:].split(")")[0].strip()
        # Strip a trailing timezone offset only -- NOT a leading minus sign. The
        # old split("-")[0] turned the negative epoch of a pre-1970 sentinel into
        # an empty string, i.e. 1970, which merely happened to still land under
        # the never-run threshold. Match the offset explicitly instead.
        match = re.match(r"^(-?\d+)(?:[+-]\d{4})?$", inner)
        if not match:
            return None
        ms = int(match.group(1))
        try:
            return _dt.datetime.fromtimestamp(ms / 1000.0)
        except (ValueError, OSError, OverflowError):
            # Pre-epoch values are not representable via fromtimestamp on Windows.
            # Compute them from the epoch instead, so a 1900-style never-run
            # sentinel stays a real (very old) date and never becomes None --
            # None means "unparseable", which callers escalate.
            try:
                return _dt.datetime(1970, 1, 1) + _dt.timedelta(milliseconds=ms)
            except (OverflowError, OSError):
                return None
    # Strip fractional seconds, then a trailing timezone offset. The offset cannot
    # be removed by splitting on "-": an ISO date is full of hyphens, so
    # "2026-09-10T14:00:00-04:00".split("-")[0] is "2026". Anchor it to the end.
    cleaned = re.sub(r"\.\d+", "", text)
    cleaned = re.sub(r"(?:Z|[+-]\d{2}:?\d{2})$", "", cleaned).strip()
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%m/%d/%Y %I:%M:%S %p", "%m/%d/%Y %H:%M:%S"):
        try:
            return _dt.datetime.strptime(cleaned, fmt)
        except ValueError:
            continue
    return None


def check_freshness(result, watched=None, state_dir=None, now=None):
    import datetime as _dt
    watched = watched if watched is not None else WATCHED
    state_dir = state_dir or lib.STATE_DIR
    now = now or _dt.datetime.now()

    for name, cfg in sorted(watched.items()):
        heartbeat = os.path.join(state_dir, "%s-latest.json" % name)
        found, info = _task_info(cfg["task"])

        if found is False:
            result.finding(
                "Scheduled task %r no longer exists -- the %s check cannot run at all."
                % (cfg["task"], name),
                severity="HIGH",
                evidence="re-register with maintenance/headless/register-headless-checks.ps1",
            )
            continue
        if found is None:
            result.error("could not query scheduled task %r" % cfg["task"])
            continue

        raw_last_run = info.get("LastRunTime")
        last_run = _parse_ps_date(raw_last_run)
        if last_run is None and raw_last_run:
            # Unparseable is NOT never-run. Folding the two together would send an
            # unreadable timestamp down the "registered, not yet fired" path and
            # buy permanent silence -- the failure this check exists to close.
            result.error("could not parse LastRunTime for %s" % name,
                         evidence=repr(raw_last_run))
            continue
        never_run = last_run is None or last_run.year < NEVER_RUN_BEFORE_YEAR

        if not os.path.exists(heartbeat):
            if never_run:
                # Registered but not yet due -- correct during the window between
                # registration and first fire. Not a finding.
                result.note("%s registered, not yet fired (next %s)"
                            % (name, info.get("NextRunTime")))
            else:
                result.finding(
                    "%s task has run but wrote no findings file -- the wrapper is "
                    "firing and failing before it can report." % name,
                    severity="HIGH", evidence="expected %s" % heartbeat,
                )
            continue

        age_h = (now - _dt.datetime.fromtimestamp(os.path.getmtime(heartbeat))).total_seconds() / 3600.0
        if age_h > cfg["max_age_h"]:
            result.finding(
                "%s has not reported in %.1fh (threshold %dh) -- it has gone silent, "
                "and silence is what a clean run looks like." % (name, age_h, cfg["max_age_h"]),
                severity="HIGH",
                evidence="heartbeat %s; task LastRunTime %s" % (heartbeat, info.get("LastRunTime")),
            )
        else:
            result.note("%s fresh (%.1fh old, threshold %dh)" % (name, age_h, cfg["max_age_h"]))

    # Known gap, stated rather than papered over: this check cannot alarm on its
    # OWN disappearance -- the same structural limit ora-task-integrity-guard
    # names about itself. fleet-deadman.ps1 remains the out-of-band backstop.
    result.note("freshness cannot detect its own loss; fleet-deadman.ps1 is the backstop")


CHECKS = {
    "stranded-spec": check_stranded_spec,
    "mirror-drift": check_mirror_drift,
    "integrity-guard": check_integrity_guard,
    "freshness": check_freshness,
}


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        print("checks: %s" % ", ".join(sorted(CHECKS)))
        return 0
    name = argv[0]
    if name not in CHECKS:
        print("unknown check %r; expected one of %s" % (name, ", ".join(sorted(CHECKS))))
        return 2
    return lib.run(name, CHECKS[name], argv=argv[1:])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
