#!/usr/bin/env python3
"""Shared contract for ORA headless checks (out-of-band, Windows Task Scheduler).

WHY THIS EXISTS (2026-09-10). Gabriel asked for the integrity guard, the mirror
drift check and the stranded-spec probe to run headless via
`claude -p "<prompt>" --allowedTools ...`. That mechanism is NOT AVAILABLE on this
machine and these wrappers deliberately do not use it:

  * `~/.claude/.credentials.json` is dated 2026-08-13 and its OAuth session is
    expired with no refresh path outside the authenticated Desktop app. Verified
    live 2026-09-10 with a CLEANED environment (CLAUDE_CODE_CHILD_SESSION and
    friends unset, so this was NOT merely the nested-subprocess case):
        $ claude -p "Reply with exactly: HEADLESS_OK" --allowedTools "Read"
        Failed to authenticate: OAuth session expired and could not be refreshed
        EXIT=1
  * Independently corroborated by `reference_skill_eval_harness_gap_2026-08-14.md`
    ("Headless `claude -p` CLI re-run path is a dead end in this environment,
    confirmed by direct test ... Don't re-attempt it").

It also turned out not to be needed. All three checks are DETERMINISTIC underneath
-- `task-folder-registration-probe.py`, `registry-membership-probe.py` and
`mirror-run-classify.ps1` are tested scripts, and the mirror SKILL.md explicitly
says "run the classifier, do not hand-reason this ... Use its verdict -- do not
re-derive your own". Routing them through an LLM would add cost and
nondeterminism to checks that already emit machine-readable verdicts. If a
headless LLM path is ever wanted it needs an ANTHROPIC_API_KEY provisioned by
Gabriel (a billing + credential decision), not a code change here.

EXIT CODE CONTRACT:
    0  CLEAN        -- no findings. Silent. No page. (A heartbeat file is still
                       written; a file on disk is evidence, not a notification.)
    1  FINDINGS     -- real findings. Writes findings file, pages.
    2  CANT_VERIFY  -- the check could not run or could not read ground truth.
                       Writes findings file, pages, labelled distinctly.

DELIBERATE DEVIATION FROM THE FAIL-OPEN CONVENTION. Every probe under
`maintenance/` fails OPEN (`fleet-deadman.ps1`: "any internal error -> exit 0
(never nag on a bug)"). These wrappers fail LOUD on CANT_VERIFY instead, for two
reasons: Gabriel's requirement is that failures page, and the mirror check's own
doctrine already states "If the classifier itself fails to run, that is an ALARM
(can't-verify is not healthy)". A monitoring wrapper that silently exits 0 when
its own check is broken is indistinguishable from a healthy run -- the exact
phantom-dispatch failure class this fleet has been bitten by before. CANT_VERIFY
is kept as its own code so a broken check never masquerades as a real finding,
and so its noise can be tuned independently.
"""
import datetime
import json
import os
import subprocess
import sys

EXIT_CLEAN = 0
EXIT_FINDINGS = 1
EXIT_CANT_VERIFY = 2

HOME = os.path.expanduser("~")
CLAUDE = os.path.join(HOME, ".claude")
STATE_DIR = os.path.join(CLAUDE, "maintenance", "_state", "headless-findings")
SEND_SCRIPT = os.path.join(CLAUDE, "scheduled-tasks", "_shared", "send-via-outlook.ps1")
# Routing canon (CLAUDE.md): all scheduled/automated output goes to ggoldberg ONLY.
# The single cc-Eric exception is ora-am-brief's Daily Brief and does not apply here.
PAGE_TO = "ggoldberg@oxfordra.net"
DESKTOP_ALERT = os.path.join(HOME, "Desktop", "ORA-CHECK-FAILED.txt")
# send-via-outlook.ps1 exit codes worth a second attempt (CLAUDE.md): 2 = COM
# failure, 4 = timeout. 1 (usage error) and 3 (stuck wizard) are terminal.
RETRYABLE_SEND_CODES = (2, 4)


def _ascii(text):
    """Findings quote spec text, and ORA SKILL.mds carry non-cp1252 glyphs freely.

    Printing one unmodified raised UnicodeEncodeError and took down the probe that
    was doing the reporting (see spec-liveness-probe.py's note on the same bug).
    Degrade the characters, never the run.
    """
    return str(text).encode("ascii", "replace").decode("ascii")


class CheckResult(object):
    def __init__(self, name):
        self.name = name
        self.findings = []
        self.errors = []
        self.notes = []

    def finding(self, summary, severity="HIGH", evidence=None):
        self.findings.append(
            {"severity": severity, "summary": summary, "evidence": evidence}
        )

    def error(self, summary, evidence=None):
        """Record a can't-verify condition -- NOT a finding about the system."""
        self.errors.append({"summary": summary, "evidence": evidence})

    def note(self, text):
        self.notes.append(text)

    def exit_code(self):
        # Errors outrank findings: if the check could not fully read ground truth,
        # say so rather than presenting a partial finding set as authoritative.
        if self.errors:
            return EXIT_CANT_VERIFY
        if self.findings:
            return EXIT_FINDINGS
        return EXIT_CLEAN

    def status(self):
        return {
            EXIT_CLEAN: "CLEAN",
            EXIT_FINDINGS: "FINDINGS",
            EXIT_CANT_VERIFY: "CANT_VERIFY",
        }[self.exit_code()]

    def to_dict(self):
        return {
            "check": self.name,
            "ranAt": datetime.datetime.now().isoformat(timespec="seconds"),
            "host": os.environ.get("COMPUTERNAME", "unknown"),
            "status": self.status(),
            "exitCode": self.exit_code(),
            "findingCount": len(self.findings),
            "findings": self.findings,
            "errors": self.errors,
            "notes": self.notes,
        }


def write_findings(result, state_dir=None):
    """Always write `<check>-latest.json`; keep a timestamped copy only when not clean.

    The heartbeat matters: a check that silently stops running is the failure mode
    this fleet has actually suffered (phantom dispatch, 44% of dispatches over four
    days in 2026-08). `-latest.json` gives an mtime anything can age-check.
    """
    state_dir = state_dir or STATE_DIR
    os.makedirs(state_dir, exist_ok=True)
    payload = result.to_dict()
    latest = os.path.join(state_dir, "%s-latest.json" % result.name)
    with open(latest, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
    written = [latest]
    if result.exit_code() != EXIT_CLEAN:
        stamp = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
        archived = os.path.join(state_dir, "%s-%s.json" % (result.name, stamp))
        with open(archived, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
        written.append(archived)
    return written


def render_body(result):
    d = result.to_dict()
    lines = [
        "ORA headless check: %s" % d["check"],
        "Status: %s (exit %d)" % (d["status"], d["exitCode"]),
        "Ran: %s on %s" % (d["ranAt"], d["host"]),
        "",
    ]
    if d["errors"]:
        lines.append("COULD NOT VERIFY (%d):" % len(d["errors"]))
        for e in d["errors"]:
            lines.append("  - %s" % _ascii(e["summary"]))
            if e.get("evidence"):
                lines.append("      %s" % _ascii(e["evidence"])[:900])
        lines.append("")
    if d["findings"]:
        lines.append("FINDINGS (%d):" % len(d["findings"]))
        for f in d["findings"]:
            lines.append("  [%s] %s" % (f["severity"], _ascii(f["summary"])))
            if f.get("evidence"):
                lines.append("      %s" % _ascii(f["evidence"])[:900])
        lines.append("")
    if d["notes"]:
        lines.append("Notes:")
        lines.extend("  - %s" % _ascii(n) for n in d["notes"])
    return "\n".join(lines)


def page(result, findings_paths=None, send_script=None, desktop_alert=None):
    """Page Gabriel. Outlook COM first (canonical), desktop file as the fallback.

    fleet-deadman.ps1 pages file-only precisely because an out-of-band run cannot
    assume Outlook is up. We try COM because Gabriel asked to be paged, and fall
    back rather than losing the alarm outright. Per CLAUDE.md's send-path doctrine
    a COM failure is retried ONCE, then flagged loudly rather than halting.
    """
    send_script = send_script or SEND_SCRIPT
    desktop_alert = desktop_alert or DESKTOP_ALERT
    body = render_body(result)
    if findings_paths:
        body += "\n\nFindings file: %s" % findings_paths[0]
    subject = "[ORA CHECK %s] %s -- %d finding(s), %d error(s)" % (
        result.status(), result.name, len(result.findings), len(result.errors),
    )

    if os.path.exists(send_script):
        for attempt in (1, 2):
            try:
                proc = subprocess.run(
                    ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
                     "-File", send_script, "-To", PAGE_TO,
                     "-Subject", subject, "-Body", body, "-BodyFormat", "text"],
                    capture_output=True, text=True, timeout=180,
                )
                if proc.returncode == 0:
                    return "email"
                # CLAUDE.md send-path doctrine distinguishes these: exit 2 (COM
                # failure) and 4 (timeout) are retried once; exit 1 (usage error)
                # and 3 (stuck wizard) must NOT be retried -- a second identical
                # call cannot fix a malformed invocation, it just burns another
                # timeout before the fallback.
                if proc.returncode not in RETRYABLE_SEND_CODES:
                    body += "\n\n[Outlook COM send failed rc=%d (not retryable): %s]" % (
                        proc.returncode, _ascii(proc.stderr)[:500])
                    break
                if attempt == 2:
                    body += "\n\n[Outlook COM send failed rc=%d after 2 attempts: %s]" % (
                        proc.returncode, _ascii(proc.stderr)[:500])
            except Exception as exc:  # noqa: BLE001 -- the fallback must survive anything
                if attempt == 2:
                    body += "\n\n[Outlook COM send raised: %s]" % _ascii(exc)[:500]
    else:
        body += "\n\n[Send script not found at %s]" % send_script

    try:
        with open(desktop_alert, "w", encoding="utf-8") as fh:
            fh.write(body)
        return "desktop-file"
    except Exception:  # noqa: BLE001
        return "none"


def run(name, fn, argv=None, state_dir=None):
    """Entry point for a wrapper: build a result, persist it, page only if not clean.

    `state_dir` exists so the test suite can exercise this end to end without
    writing into the live findings directory -- the tests are what surfaced it,
    having twice left `demo-*` heartbeats sitting next to the real ones.
    """
    argv = argv if argv is not None else sys.argv[1:]
    dry_run = "--dry-run" in argv
    result = CheckResult(name)
    try:
        fn(result)
    except Exception as exc:  # noqa: BLE001 -- a crashed check is CANT_VERIFY, never clean
        result.error("check raised %s" % type(exc).__name__, evidence=str(exc))

    paths = write_findings(result, state_dir=state_dir)
    code = result.exit_code()

    if code == EXIT_CLEAN:
        # Silent by contract. One line to the log/console, no page.
        print("[OK] %s -- clean." % name)
        return EXIT_CLEAN

    print(_ascii(render_body(result)))
    if dry_run:
        print("[DRY-RUN] would page %s" % PAGE_TO)
    else:
        print("[PAGED via %s]" % page(result, paths))
    return code
