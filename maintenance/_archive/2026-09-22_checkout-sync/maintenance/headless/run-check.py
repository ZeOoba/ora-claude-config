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

    payload = None
    for line in reversed([l for l in out.splitlines() if l.strip()]):
        try:
            payload = json.loads(line)
            break
        except ValueError:
            continue
    if payload is None:
        try:
            payload = json.loads(out)
        except ValueError:
            result.error("mirror classifier emitted no parseable JSON", evidence=_tail(out))
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


CHECKS = {
    "stranded-spec": check_stranded_spec,
    "mirror-drift": check_mirror_drift,
    "integrity-guard": check_integrity_guard,
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
